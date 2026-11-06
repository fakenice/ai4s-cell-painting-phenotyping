# -*- coding: utf-8 -*-
"""Stage 12 - external *site* validation of the phenotype classifier.

What was missing before this stage
----------------------------------
Everything the project has called "external validation" so far (stage11_p3) lives inside
one derivation of one dataset: `cpg0000-jump-pilot/source_4`, plates BR00116991 and
BR00116992 - same lab, same instrument, same CellProfiler run, same normalization. That
is a cross-*plate* check, and the stage11 docstring says so itself ("Uses ONLY
already-downloaded data (zero new downloads)"). Cross-plate AUC 0.6825 / AP 0.9107.

A first attempt to find the other three pilot sites *inside* the public bucket came back
empty and that negative is now recorded, not assumed:

    cpg0000-jump-pilot/source_1  -> KeyCount 0
    cpg0000-jump-pilot/source_2  -> KeyCount 0
    cpg0000-jump-pilot/source_3  -> KeyCount 0
    cpg0000-jump-pilot/source_4  -> images/ + workspace/   (this is what we trained on)

So the pilot's own multi-lab arm is not published in this bucket, and the closest thing
to an independent source that *is* published, is `cpg0016-jump` - the JUMP Cell Painting
compendium: acquired and derived separately from pilot source_4, per-well CellProfiler
output for 384-well compound plates, and a relational metadata schema
(plate -> well -> JCP2022 compound id -> InChIKey).

Design
------
  train  pilot BR00116991 (+ optionally BR00116992), trt vs DMSO, 904-feature file,
         Columns filtered to the Cells_/Cytoplasm_/Nuclei_ vocabulary stage11_p3 uses.
  test   cpg0016 per-well profiles from N plates, restricted to the features whose names
         are common to both sides, normalised *at the external site* by a robust z against
         that plate's own DMSO wells.
  report cross-site AUC/AP, the same-site within-external 5-fold CV (what is achievable at
         that site at all), the published cross-plate number as the in-site reference, and
         the per-plate breakdown so one bad plate cannot hide inside a pooled mean.

Two things are deliberately *not* done: the classifier is not re-fitted on external data,
and no external number is quoted before the SHA256 manifest for the files behind it has
been written.

Stages
------
    python scripts/stage12_external_site.py --stage fetch --sets meta --plates 0
    python scripts/stage12_external_site.py --stage controls
    python scripts/stage12_external_site.py --stage fetch --sets meta,profiles --plates 10
    python scripts/stage12_external_site.py --stage position      # well-layout audit
    python scripts/stage12_external_site.py --stage retrieval     # position-split retrieval
    python scripts/stage12_external_site.py --stage evaluate --scaling negcon_z
    python scripts/stage12_external_site.py --stage diagnose      # all arms
    python scripts/stage12_external_site.py --stage trainsize     # pilot training-size curve

What the position and retrieval stages are for: both sites turn out to place compounds by
well coordinate, and the pilot's two plates are the same array (384/384 wells carry the
identical compound). That is a property of the data, not of this pipeline, but it changes
what the in-site cross-plate numbers can be read as, so it is measured and reported rather
than left implicit.
"""
import argparse
import collections
import csv
import hashlib
import itertools
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler, normalize

warnings.filterwarnings("ignore", message=".*highly fragmented.*")

RANDOM_STATE = 42
# Paths come from scripts/_paths.py (derived from this file's location; override with
# AI4S_REPO / AI4S_WORKSPACE). data/ lives at the workspace root, one level above this repo.
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import _paths  # noqa: E402
from _paths import BASE, REPO  # noqa: E402
DATA = _paths.DATA                  # <repo>/data if present, else <workspace>/data
REPORTS = os.path.join(REPO, "reports")
EXT = os.path.join(DATA, "external", "cpg0016")
MANIFEST = os.path.join(EXT, "manifest_sha256.csv")

S3 = "https://cellpainting-gallery.s3.amazonaws.com/"
BUDGET_BYTES = 200_000_000              # the user-approved cap, read as 200 * 10^6 bytes
FEAT_PREFIX = ("Cells_", "Cytoplasm_", "Nuclei_")
SOURCE = "cpg0016-jump/source_2"        # 2021 batches: separate acquisition + derivation
BATCH = "20210614_Batch_1"
PUB = ("cpg0016-jump/source_all/workspace/publication_data/"
       "2025_Chandrasekaran/datasets/v0.13/parquet/")

PILOT_PLATES = ["BR00116991", "BR00116992"]
# IAZDPXIOMUYVGZ-UHFFFAOYSA-N = dimethyl sulfoxide, verified against the compound table:
# the external id that carries it (JCP2022_033924) occupies 65 wells of plate 1053600674,
# i.e. it is that plate's vehicle column, and 64 pilot wells carry the same key as
# `control_type == negcon`. The molecule, not a column name, is the shared definition.
DMSO_INCHIKEY = "IAZDPXIOMUYVGZ-UHFFFAOYSA-N"
# the source's own placeholder for wells whose compound could not be assigned; they are
# neither confirmed treated nor vehicle, so both stages drop them and count how many
UNKNOWN_JCP = ["JCP2022_UNKNOWN"]


def profile_key(plate):
    return f"{SOURCE}/workspace/profiles/{BATCH}/{plate}/{plate}.parquet"


def meta_key(name):
    return PUB + name


META_SET = ["well.parquet", "compound.parquet", "plate.parquet",
            "perturbation.parquet", "compound_source.parquet"]


# --------------------------------------------------------------------------- io helpers

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def s3_list(prefix, max_keys=1000, marker=""):
    params = {"list-type": "2", "prefix": prefix, "max-keys": str(max_keys)}
    if marker:
        params["continuation-token"] = marker
    url = S3 + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as fh:
        body = fh.read().decode()
    rows = []
    for chunk in body.split("<Contents>")[1:]:
        rows.append((chunk.split("<Key>")[1].split("</Key>")[0],
                     int(chunk.split("<Size>")[1].split("</Size>")[0])))
    return rows


def s3_size(key):
    url = S3 + urllib.parse.quote(key)
    req = urllib.request.Request(url, method="HEAD",
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers["Content-Length"])


def read_manifest():
    if not os.path.exists(MANIFEST):
        return {}
    # encoding is explicit and tolerant: the project path contains a full-width "：",
    # which an earlier version of this script wrote with the Windows default codec (cp936)
    # and then could not re-read. Read either, always write utf-8.
    for enc in ("utf-8", "cp936"):
        try:
            with open(MANIFEST, newline="", encoding=enc) as f:
                return {r["s3_key"]: r for r in csv.DictReader(f)}
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"{MANIFEST} is neither valid utf-8 nor cp936 - re-run --stage fetch")


def write_manifest(rows):
    os.makedirs(EXT, exist_ok=True)
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["s3_key", "local_path", "bytes",
                                          "s3_declared_bytes", "status", "sha256"])
        w.writeheader()
        for r in sorted(rows.values(), key=lambda x: x["s3_key"]):
            w.writerow(r)


def download(key, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return key, dest, "exists", os.path.getsize(dest), sha256_of(dest)
    url = S3 + urllib.parse.quote(key)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=300) as r:
            declared = int(r.headers.get("Content-Length", "-1"))
            blob = r.read()
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".part"
        with open(tmp, "wb") as f:
            f.write(blob)
        os.replace(tmp, dest)
        if declared >= 0 and len(blob) != declared:
            return key, dest, f"TRUNCATED got={len(blob)} declared={declared}", len(blob), ""
        return key, dest, "ok", len(blob), sha256_of(dest)
    except Exception as e:
        return key, dest, f"FAIL:{type(e).__name__}:{str(e)[:140]}", 0, ""


# --------------------------------------------------------------------------- stage: fetch

def stage_fetch(args):
    os.makedirs(EXT, exist_ok=True)
    want = [s.strip() for s in args.sets.split(",") if s.strip()]
    jobs = []
    if "meta" in want:
        for name in META_SET:
            jobs.append((meta_key(name), os.path.join(EXT, name)))
    if "profiles" in want:
        plates = [k.split("/")[-2] for k, _ in s3_list(f"{SOURCE}/workspace/profiles/{BATCH}/")
                  if k.endswith(".parquet")]
        plates = sorted(plates)[:args.plates]
        for p in plates:
            jobs.append((profile_key(p), os.path.join(EXT, f"{p}.parquet")))

    rows = read_manifest()
    already = sum(int(r["bytes"]) for r in rows.values() if r["status"] in ("ok", "exists"))
    print(f"budget {BUDGET_BYTES/1e6:.0f} MB, already on disk from the manifest "
          f"{already/1e6:.1f} MB", flush=True)

    # price the plan before pulling anything
    priced = []
    for key, dest in jobs:
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            priced.append((key, dest, os.path.getsize(dest), True))
            continue
        try:
            n = s3_size(key)
        except Exception as e:
            print(f"  !! size unknown for {key}: {e}")
            n = -1
        priced.append((key, dest, n, False))
    needed = sum(n for k, d, n, have in priced if not have and n > 0)
    print(f"{len(jobs)} file(s) planned, {needed/1e6:.1f} MB of it new", flush=True)
    if already + needed > BUDGET_BYTES:
        print(f"ABORT - plan would cost {(already + needed)/1e6:.1f} MB, above the "
              f"{BUDGET_BYTES/1e6:.0f} MB cap. Lower --plates.")
        return 3

    todo = [(k, d) for k, d, n, have in priced if not have]
    results = []
    if todo:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(download, k, d): k for k, d in todo}
            for fut in as_completed(futs):
                key, dest, status, n, digest = fut.result()
                print(f"  {os.path.basename(dest):26s} {status:38s} {n/1e6:8.2f} MB", flush=True)
                results.append((key, dest, status, n, digest))
    for key, dest, status, n, digest in results:
        try:
            declared = s3_size(key)
        except Exception:
            declared = -1
        rows[key] = {"s3_key": key, "local_path": dest, "bytes": n,
                     "s3_declared_bytes": declared, "status": status, "sha256": digest}
    for key, dest, n, have in priced:
        if have and key not in rows:
            rows[key] = {"s3_key": key, "local_path": dest, "bytes": n,
                         "s3_declared_bytes": n, "status": "exists",
                         "sha256": sha256_of(dest)}
    write_manifest(rows)
    total = sum(int(r["bytes"]) for r in rows.values() if r["status"] in ("ok", "exists"))
    bad = [r for r in rows.values() if r["status"] not in ("ok", "exists")]
    print(f"\nmanifest: {len(rows)} rows, {total/1e6:.1f} MB verified -> {MANIFEST}")
    if bad:
        print(f"!! {len(bad)} object(s) NOT verified: "
              f"{[(os.path.basename(b['local_path']), b['status']) for b in bad]}")
        return 2
    return 0


# --------------------------------------------------------------------------- loading

def load_external_table(plate):
    """One cpg0016 per-well profile parquet, plus the compound join."""
    df = pd.read_parquet(os.path.join(EXT, f"{plate}.parquet"))
    well = pd.read_parquet(os.path.join(EXT, "well.parquet"))
    comp = pd.read_parquet(os.path.join(EXT, "compound.parquet"))
    well = well[well["Metadata_Plate"].astype(str) == str(plate)]
    df = df.merge(well, on=["Metadata_Source", "Metadata_Plate", "Metadata_Well"], how="left")
    df = df.merge(comp[["Metadata_JCP2022", "Metadata_InChIKey"]],
                  on="Metadata_JCP2022", how="left")
    return df


def robust_z(df, feats, dmso_mask):
    """Per-plate, per-feature robust z against that plate's own DMSO wells:
    (x - median_dmso) / (1.4826 * MAD_dmso). This is the external site's *own* negcon
    step; it never sees the pilot's normalisation, so it cannot leak into it."""
    sub = df.loc[dmso_mask, feats].to_numpy(float)
    med = np.nanmedian(sub, axis=0)
    mad = np.nanmedian(np.abs(sub - med), axis=0) * 1.4826
    scale = np.where(mad > 1e-12, mad, np.nan)
    # fall back to the DMSO std where MAD collapsed, then to 1.0 (constant feature)
    sd = np.nanstd(sub, axis=0)
    scale = np.where(np.isfinite(scale), scale, sd)
    scale = np.where(np.isfinite(scale) & (scale > 1e-12), scale, 1.0)
    X = df[feats].to_numpy(float)
    return (X - med) / scale


# ------------------------------------------------------------------- well position

WELL_ROWS = [chr(ord("A") + i) for i in range(16)]   # both sites are 16x24 = 384-well
WELL_COLS = list(range(1, 25))


def well_coords(wells):
    """'A07' / 'a7' -> ('A', 7); anything unparsable -> ('', -1)."""
    rows, cols = [], []
    for w in np.asarray(wells).astype(str):
        m = re.match(r"^\s*([A-Za-z]+)(\d+)\s*$", w)
        rows.append(m.group(1).upper() if m else "")
        cols.append(int(m.group(2)) if m else -1)
    return np.array(rows, dtype=object), np.array(cols, dtype=int)


def position_design(wells):
    """One-hot row + column matrix on a FIXED category set (A-P, 1-24, minus one level
    each so the block is full rank next to LR's intercept).

    The category set does not depend on the data, which is what lets a model fitted on
    the pilot's plate layout be evaluated on another site's layout at all.
    """
    r, c = well_coords(wells)
    R = np.column_stack([(r == x).astype(float) for x in WELL_ROWS[1:]])
    C = np.column_stack([(c == x).astype(float) for x in WELL_COLS[1:]])
    return np.hstack([R, C])


def residualize_position(X, wells):
    """Remove additive row and column effects (two-way ANOVA residual) from a per-well
    matrix. Applied per dataset, on that dataset's own wells, so it cannot import the
    other site's layout statistics."""
    r, c = well_coords(wells)
    ones = np.ones((len(r), 1))
    D = np.hstack([ones]
                  + [np.column_stack([(r == x).astype(float) for x in WELL_ROWS[1:]])]
                  + [np.column_stack([(c == x).astype(float) for x in WELL_COLS[1:]])])
    beta, *_ = np.linalg.lstsq(D, X, rcond=None)
    return X - D @ beta


def position_confound(wells, is_dmso, is_trt, n_perm=2000, seed=RANDOM_STATE):
    """How much of the treated-vs-vehicle label is available from the well coordinate?

    Why this exists: the external plates put their vehicle wells in two fixed columns
    (measured: every DMSO well on eight of the nine cpg0016 compound plates is in column
    02 or 23, position-only CV AUC 1.0000), while the pilot's 64 DMSO wells are scattered
    over 22 columns (position-only CV AUC 0.5361). Edge and meniscus effects are
    position-driven, so a within-plate CV AUC on such a plate is *not* a clean "what this
    site can achieve" bound, and a cross-site transfer has to bridge two different layout
    conventions as well as two different instruments.

    Returns the layout description plus a 5-fold CV AUC of a position-only classifier.
    """
    keep = np.asarray(is_dmso) | np.asarray(is_trt)
    kept_wells = np.asarray(wells)[keep]
    r, c = well_coords(kept_wells)
    y = np.asarray(is_trt)[keep].astype(int)
    dm = np.asarray(is_dmso)[keep]
    k = int(dm.sum())
    out = {"n_wells": int(keep.sum()), "n_dmso": k,
           "n_rows_with_dmso": int(len(set(r[dm]))),
           "n_cols_with_dmso": int(len(set(c[dm]))),
           "dmso_cols": sorted(set(int(v) for v in c[dm])),
           "position_only_cv_auc": (float("nan") if k < 8 or (y.sum() < 8 or keep.sum() - y.sum() < 8)
                                    else cv_auc_ap(position_design(kept_wells), y)[0])}
    # spatial concentration of the vehicle wells, against a permutation null
    rng = np.random.default_rng(seed)
    codes_r = np.unique(r, return_inverse=True)[1]
    codes_c = np.unique(c, return_inverse=True)[1]

    def modal_share(codes, idx):
        cnt = np.bincount(codes[idx], minlength=codes.max() + 1)
        return float(cnt.max() / max(1, k))

    obs_r, obs_c = modal_share(codes_r, np.where(dm)[0]), modal_share(codes_c, np.where(dm)[0])
    null_r = np.empty(n_perm)
    null_c = np.empty(n_perm)
    for b in range(n_perm):
        p = rng.permutation(keep.sum())[:k]
        null_r[b] = modal_share(codes_r, p)
        null_c[b] = modal_share(codes_c, p)
    out["dmso_max_share_one_row"] = obs_r
    out["dmso_max_share_one_col"] = obs_c
    out["dmso_layout_p_row_perm"] = float(np.mean(null_r >= obs_r))
    out["dmso_layout_p_col_perm"] = float(np.mean(null_c >= obs_c))
    return out


def load_pilot(plates=PILOT_PLATES):
    frames = []
    for p in plates:
        f = os.path.join(DATA, "profiles",
                         f"{p}_normalized_feature_select_negcon_batch.csv.gz")
        df = pd.read_csv(f)
        df = df.assign(plate=p)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def pilot_labels(df):
    """trt = the pilot's own treatment flag; DMSO = the vehicle's InChIKey.

    The second rule is deliberately key-based rather than `control_type == "dmso"`:
    the pilot file spells its negative controls `negcon` (64 wells, all of them this
    InChIKey), and using the molecule itself is the only definition that can be applied
    *unchanged* on the external side, where the metadata carries no control_type column.
    """
    trt = (df["Metadata_pert_type"].astype(str).str.lower() == "trt").to_numpy()
    key = df["Metadata_InChIKey"].astype(str).to_numpy()
    dmso = (key == DMSO_INCHIKEY) & ~trt
    return trt, dmso


def clean_matrix(df, feats):
    """Feature matrix as float, with all-NaN columns dropped and the rest mean-imputed.

    Imputing *after* the per-plate robust z means a missing value contributes 0, i.e.
    "no evidence of perturbation" - the conservative choice for a trt-vs-vehicle test.
    """
    X = df[feats].to_numpy(float)
    keep_col = np.isfinite(X).any(axis=0)
    X = X[:, keep_col]
    kept = [c for c, k in zip(feats, keep_col) if k]
    n_missing = int((~np.isfinite(X)).sum())
    col_mean = np.nanmean(np.where(np.isfinite(X), X, np.nan), axis=0)
    bad = np.where(~np.isfinite(X))
    if bad[0].size:
        X[bad] = np.take(col_mean, bad[1])
    return np.where(np.isfinite(X), X, 0.0), kept, n_missing


def impute_finite(X):
    """Replace non-finite cells with the column mean of the finite ones (0 where the whole
    column is empty). Needed before any least-squares step, which propagates NaN."""
    X = np.asarray(X, float)
    bad = ~np.isfinite(X)
    if not bad.any():
        return X
    col_mean = np.nanmean(np.where(np.isfinite(X), X, np.nan), axis=0)
    col_mean = np.where(np.isfinite(col_mean), col_mean, 0.0)
    X = X.copy()
    X[bad] = np.take(col_mean, np.where(bad)[1])
    return X


def retrieval_cross_site(Xe, keys_ext, Xp, keys_pilot):
    """For each external well, rank all pilot treated wells by cosine and ask where its
    own compound (same InChIKey) lands. This is the cross-site analogue of stage11_p3 B1,
    which had to settle for the same compound in a second plate of the *same* site."""
    A = normalize(Xe, norm="l2", axis=1)
    B = normalize(Xp, norm="l2", axis=1)
    S = A @ B.T
    ranks, hit1, hit5, hit10, chance1 = [], [], [], [], []
    for i in range(S.shape[0]):
        y = (keys_pilot == keys_ext[i])
        if not y.any():
            continue
        order = np.argsort(S[i])[::-1]
        r = int(np.where(y[order])[0][0]) + 1
        ranks.append(r)
        hit1.append(r <= 1)
        hit5.append(r <= 5)
        hit10.append(r <= 10)
        # random-ranking baseline for THIS query: the share of the library that would
        # already count as a hit. Without it a recall@1 of 0.025 has no reference point.
        chance1.append(float(y.sum()) / S.shape[1])
    if not ranks:
        return {}
    y_all = (keys_ext[:, None] == keys_pilot[None, :]).astype(int)
    return {"n_queries": int(len(ranks)),
            "pair_AUC": float(roc_auc_score(y_all.ravel(), S.ravel())),
            "median_rank": float(np.median(ranks)),
            "recall_at_1": float(np.mean(hit1)), "recall_at_5": float(np.mean(hit5)),
            "recall_at_10": float(np.mean(hit10)),
            "chance_recall_at_1_random_ranking": float(np.mean(chance1)),
            "chance_recall_at_10_random_ranking": float(
                np.mean([1 - (1 - c) ** 10 for c in chance1]))}


def fit_score(Xtr, ytr, Xte):
    """Protocol-consistent classifier: StandardScaler + LogisticRegression, seed 42."""
    sc = StandardScaler().fit(Xtr)
    lr = LogisticRegression(max_iter=5000, class_weight="balanced",
                            random_state=RANDOM_STATE).fit(sc.transform(Xtr), ytr)
    return lr.decision_function(sc.transform(Xte))


def cv_auc_ap(X, y, n_splits=5):
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    probs = np.zeros(len(y))
    for tr, te in skf.split(X, y):
        sc = StandardScaler().fit(X[tr])
        lr = LogisticRegression(max_iter=5000, class_weight="balanced",
                                random_state=RANDOM_STATE).fit(sc.transform(X[tr]), y[tr])
        probs[te] = lr.decision_function(sc.transform(X[te]))
    return float(roc_auc_score(y, probs)), float(average_precision_score(y, probs))


# --------------------------------------------------------------------------- stage: controls


def _rep_counts(keys):
    """(n distinct compounds, {wells per compound: n compounds}) for one well group."""
    vc = pd.Series(list(keys)).value_counts()
    return int(len(vc)), {int(k): int(v) for k, v in vc.value_counts().items()}


def replicate_structure(plates):
    """How many wells does one compound get, and does it get them at the same coordinate?

    reports/24 §7 and report §4.7 quote these counts, because the position-decoupled
    retrieval arm only exists if a compound recurs at a *different* well between plates.
    The repository documentation's "4 technical replicates per compound" was written for a
    different subset and does not hold for either side as loaded here, so the structure is
    measured per plate rather than asserted: `21_stage12_replicate_structure.csv` is the
    within-plate view and `21_stage12_replicate_sharing.json` the between-plate view.
    """
    out = []

    def add(site, plate, klass, keys):
        n, dist = _rep_counts(keys)
        out.append({"site": site, "plate": plate, "class": klass, "n_wells": len(list(keys)),
                    "n_distinct_compounds": n,
                    "compounds_in_1_well": dist.get(1, 0),
                    "compounds_in_2_wells": dist.get(2, 0),
                    "compounds_in_3_wells": dist.get(3, 0),
                    "compounds_in_4_wells": dist.get(4, 0),
                    "max_wells_per_compound": max(dist) if dist else 0})

    ext_trt = {}
    for p in plates:
        df = load_external_table(p)
        trt = df[(df["Metadata_InChIKey"].astype(str) != DMSO_INCHIKEY)
                 & (~df["Metadata_JCP2022"].astype(str).isin(UNKNOWN_JCP))]
        ext_trt[p] = trt
        add("external cpg0016", p, "treated", trt["Metadata_InChIKey"].astype(str))
    pilot = load_pilot(PILOT_PLATES)
    for p in PILOT_PLATES:
        g = pilot[pilot["Metadata_Plate"] == p]
        trt, dmso = pilot_labels(g)
        add("pilot cpg0000", p, "treated", g.loc[trt, "Metadata_InChIKey"].astype(str))
        pos = g["Metadata_control_type"].astype(str).str.startswith("poscon")
        add("pilot cpg0000", p, "positive control", g.loc[pos, "Metadata_InChIKey"].astype(str))
    t, d = pilot_labels(pilot)
    add("pilot cpg0000", "BR00116991+BR00116992", "treated", pilot.loc[t, "Metadata_InChIKey"].astype(str))
    out.append({"site": "pilot cpg0000", "plate": "BR00116991+BR00116992",
                "class": "distinct Metadata_pert_iname (all wells)", "n_wells": int(len(pilot)),
                "n_distinct_compounds": int(pilot["Metadata_pert_iname"].nunique()),
                "compounds_in_1_well": 0, "compounds_in_2_wells": 0,
                "compounds_in_3_wells": 0, "compounds_in_4_wells": 0,
                "max_wells_per_compound": 0})
    df_out = pd.DataFrame(out)
    dest_csv = os.path.join(REPORTS, "21_stage12_replicate_structure.csv")
    df_out.to_csv(dest_csv, index=False)
    print("\nreplicate structure (wells per compound):")
    print(df_out.to_string(index=False))

    # between-plate: shared compounds and how often they land on the same coordinate
    first_well = {}
    for p in plates:
        fw = {}
        for k, w in zip(ext_trt[p]["Metadata_InChIKey"].astype(str),
                        ext_trt[p]["Metadata_Well"].astype(str)):
            fw.setdefault(k, w)
        first_well[p] = fw
    for p in PILOT_PLATES:
        g = pilot[pilot["Metadata_Plate"] == p]
        g = g[pilot_labels(g)[0]]
        fw = {}
        for k, w in zip(g["Metadata_InChIKey"].astype(str), g["Metadata_Well"].astype(str)):
            fw.setdefault(k, w)
        first_well[p] = fw
    sharing = []
    cells = collections.defaultdict(collections.Counter)
    wells_by = {p: {} for p in first_well}
    for p in plates:
        d = ext_trt[p]
        for k, w in zip(d["Metadata_InChIKey"].astype(str), d["Metadata_Well"].astype(str)):
            wells_by[p].setdefault(k, set()).add(w)
    for p in PILOT_PLATES:
        g = pilot[pilot["Metadata_Plate"] == p]
        g = g[pilot_labels(g)[0]]
        for k, w in zip(g["Metadata_InChIKey"].astype(str), g["Metadata_Well"].astype(str)):
            wells_by[p].setdefault(k, set()).add(w)
    for a, b in itertools.combinations(sorted(first_well), 2):
        sh = sorted(set(first_well[a]) & set(first_well[b]))
        if not sh:
            continue
        both_ext = a not in PILOT_PLATES and b not in PILOT_PLATES
        if a in PILOT_PLATES and b in PILOT_PLATES:
            scope = "pilot pair"
        elif not both_ext:
            scope = "cross-site pair"
        elif len(ext_trt[a]) and len(ext_trt[b]):
            scope = "external pair (both plates scored)"
        else:
            scope = "external pair (all-DMSO plate included)"
        sharing.append({"scope": scope, "plate_a": a, "plate_b": b,
                        "n_shared_compounds": len(sh),
                        "n_same_coordinate": int(sum(first_well[a][k] == first_well[b][k]
                                                     for k in sh))})
        for k in sh:
            wa, wb = wells_by[a][k], wells_by[b][k]
            cells[scope][f"wells_a={len(wa)},wells_b={len(wb)},shared_wells={len(wa & wb)}"] += 1
    sp = pd.DataFrame(sharing)
    totals = {}
    for scope, sub in sp.groupby("scope"):
        totals[scope] = {"n_pairs": int(len(sub)),
                         "shared_compounds": int(sub.n_shared_compounds.sum()),
                         "same_coordinate": int(sub.n_same_coordinate.sum()),
                         "same_coordinate_fraction":
                             float(sub.n_same_coordinate.sum() / sub.n_shared_compounds.sum()),
                         "shared_per_pair_min": int(sub.n_shared_compounds.min()),
                         "shared_per_pair_max": int(sub.n_shared_compounds.max())}
    tot = {**totals,
           "coordinate_overlap_cells": {k: dict(v) for k, v in cells.items()},
           "counting": "one well per compound per plate (the compound's first well in file order)",
           "pilot_note": "the two pilot plates share every treated compound at an identical "
                         "coordinate, which is why the pilot has no position-decoupled "
                         "retrieval arm",
           "external_note": "within a plate only a minority of compounds are replicated: "
                            "8 of the ~326 distinct InChIKeys occupy 4 wells, the rest 1 well "
                            "(plate 1053600674: 19 of 299 in 2 wells)"}
    dest_json = os.path.join(REPORTS, "21_stage12_replicate_sharing.json")
    with open(dest_json, "w", encoding="utf-8") as f:
        json.dump({"totals": tot, "per_pair": sharing}, f, indent=1, ensure_ascii=False)
    print("\nbetween-plate compound sharing:")
    print(sp.to_string(index=False))
    print(json.dumps(tot, indent=1, ensure_ascii=False))
    print("wrote " + dest_csv + " and " + dest_json)
    return 0


def stage_controls(args):
    """Answer the questions the transfer test depends on, before spending the budget:
    which wells are DMSO there, does the cell line/plate type line up, and how many of
    the pilot's compounds also appear."""
    plates = sorted(f[:-8] for f in os.listdir(EXT)
                    if f.endswith(".parquet") and f[0].isdigit())
    if not plates:
        print("no profile parquet fetched yet"); return 1
    pilot = load_pilot([PILOT_PLATES[0]])
    pilot_keys = set(pilot.loc[pilot_labels(pilot)[0], "Metadata_InChIKey"].dropna().astype(str))
    print(f"pilot treated InChIKeys on {PILOT_PLATES[0]}: {len(pilot_keys)}\n")
    rows = []
    for p in plates:
        df = load_external_table(p)
        feats = [c for c in df.columns if c.startswith(FEAT_PREFIX)]
        jcp = df["Metadata_JCP2022"].astype(str)
        other = sorted({str(v)[:12] for v in df["Metadata_JCP2022"].unique()
                        if not str(v).startswith("JCP")})
        keys = set(df["Metadata_InChIKey"].dropna().astype(str))
        rows.append({"plate": p, "wells": len(df), "n_feature_cols": len(feats),
                     "n_with_jcp_id": int(jcp.str.startswith("JCP").sum()),
                     "n_blank_id": int(((jcp == "nan") | (jcp == "")).sum()),
                     "other_id_prefix": other[:6],
                     "overlap_pilot_compounds": len(keys & pilot_keys),
                     "n_distinct_inchikey": len(keys)})
        print(f"  {p}: wells={len(df)} feats={len(feats)} jcp_ids={rows[-1]['n_with_jcp_id']} "
              f"blank={rows[-1]['n_blank_id']} overlap_pilot={rows[-1]['overlap_pilot_compounds']}")
        print(f"      non-JCP id values seen: {rows[-1]['other_id_prefix']}")
    pd.DataFrame(rows).to_csv(os.path.join(REPORTS, "21_stage12_external_controls.csv"), index=False)
    replicate_structure(plates)

    # what does a "control" look like in the id column?
    df = load_external_table(plates[0])
    print("\nvalue_counts(Metadata_JCP2022) head:")
    print(df["Metadata_JCP2022"].astype(str).value_counts().head(5).to_string())
    print("\nsample non-JCP rows:")
    bad = df[~df["Metadata_JCP2022"].astype(str).str.startswith("JCP")]
    print(bad[["Metadata_Source", "Metadata_Plate", "Metadata_Well",
                "Metadata_JCP2022", "Metadata_InChIKey"]].head(10).to_string())
    plate_meta = pd.read_parquet(os.path.join(EXT, "plate.parquet"))
    pm = plate_meta[plate_meta["Metadata_Plate"].astype(str).isin(plates)]
    print("\nplate types / sources:")
    print(pm.groupby(["Metadata_Source", "Metadata_PlateType"]).size().to_string())
    return 0


# --------------------------------------------------------------------------- stage: evaluate


def stage_position(args):
    """Is the label separable from the well coordinate alone, at each site?

    The external plates keep their vehicle in two fixed columns; the pilot scatters it.
    That asymmetry matters for two claims made elsewhere in this report, so it gets
    measured rather than assumed:

      1. the "within-site 5-fold CV" column (~0.85-0.94) is only an upper bound on what
         the external site can do if position carries no signal. A position-only CV AUC
         near 1.0 means the label is *approximately a function of the coordinate*, so the
         morphology number is partly a plate-layout number;
      2. the residualised arm (scale_side mode `posresid`) subtracts additive row+column
         means per dataset. Where treatment is perfectly confounded with column, that
         subtraction cannot tell the two apart and removes the contrast with it - which is
         exactly the diagnostic: whatever survives residualisation is not position.

    It also runs the transfer probe the cross-site test needs: fit on the *pilot's* layout
    alone and score the external plates. If the cross-site classifier were reading
    position-driven batch signal, this arm would carry it; if the two sites' layout
    conventions are unrelated, it lands at 0.5.
    """
    plates = sorted(f[:-8] for f in os.listdir(EXT)
                    if f.endswith(".parquet") and f[0].isdigit())
    if not plates:
        print("no profile parquet fetched yet"); return 1
    rows = []
    for p in PILOT_PLATES:
        df = load_pilot([p])
        trt, dmso = pilot_labels(df)
        pos = position_confound(df["Metadata_Well"], dmso, trt)
        r = {"site": "pilot " + p, "n_wells": len(df), "n_trt": int(trt.sum()),
             "n_dmso": int(dmso.sum())}
        r.update(pos)
        rows.append(r)
        print(f"  pilot {p}: dmso in {r['n_cols_with_dmso']} columns "
              f"(rows occupied {r['n_rows_with_dmso']}/16) | max share of DMSO in one column "
              f"{r['dmso_max_share_one_col']:.3f} (permutation p={r['dmso_layout_p_col_perm']:.4f}) "
              f"| position-only CV AUC {r['position_only_cv_auc']:.4f}", flush=True)

    # In-site layout transfer: the same coordinate-only model, from the pilot's first plate
    # to its second. This is the control for the committed cross-plate reference (0.6825):
    # if the vehicle positions were identical AND informative, that number could be a
    # layout readout rather than a phenotype readout.
    p1 = load_pilot([PILOT_PLATES[0]])
    p2 = load_pilot([PILOT_PLATES[1]])
    a1t, a1d = pilot_labels(p1)
    a2t, a2d = pilot_labels(p2)
    w1 = set(p1.loc[a1d, "Metadata_Well"].astype(str))
    w2 = set(p2.loc[a2d, "Metadata_Well"].astype(str))
    s = fit_score(position_design(p1.loc[a1t | a1d, "Metadata_Well"]),
                  a1t[a1t | a1d].astype(int),
                  position_design(p2.loc[a2t | a2d, "Metadata_Well"]))
    in_site_layout_auc = float(roc_auc_score(a2t[a2t | a2d].astype(int), s))
    print(f"  pilot DMSO positions identical across the two plates: {w1 == w2} "
          f"(|p1|={len(w1)}, |p2|={len(w2)}, |shared|={len(w1 & w2)}) | "
          f"in-site layout transfer p1->p2 AUC {in_site_layout_auc:.4f}")
    rows.append({"site": "pilot in-site layout transfer",
                 "dmso_positions_identical_across_plates": str(w1 == w2),
                 "layout_transfer_auc_pilot1_to_pilot2": in_site_layout_auc})

    # layout transfer arm: pilot plate 1's coordinate model, scored at each external plate
    ptr, pdm = a1t, a1d
    Xpos_p = position_design(p1.loc[ptr | pdm, "Metadata_Well"])
    ytr_p = ptr[ptr | pdm].astype(int)
    for p in plates:
        df = load_external_table(p)
        key = df["Metadata_InChIKey"].astype(str).to_numpy()
        jcp = df["Metadata_JCP2022"].astype(str).to_numpy()
        dmso = (key == DMSO_INCHIKEY)
        unk = np.isin(jcp, UNKNOWN_JCP)
        trt = ~dmso & ~unk
        sel = trt | dmso
        r = {"site": "external " + p, "n_wells": len(df), "n_trt": int(trt.sum()),
             "n_dmso": int(dmso.sum())}
        r.update(position_confound(df["Metadata_Well"], dmso, trt))
        if trt.sum() >= 8 and dmso.sum() >= 8:
            Xpos_e = position_design(df.loc[sel, "Metadata_Well"])
            y_e = trt[sel].astype(int)
            s = fit_score(Xpos_p, ytr_p, Xpos_e)
            r["layout_transfer_auc_pilot1_to_here"] = float(roc_auc_score(y_e, s))
            # and the reverse: this plate's layout predicts the pilot's other plate
            q2t, q2d = pilot_labels(p2)
            s2 = fit_score(Xpos_e, y_e, position_design(p2.loc[q2t | q2d, "Metadata_Well"]))
            r["layout_transfer_auc_here_to_pilot2"] = float(
                roc_auc_score(q2t[q2t | q2d].astype(int), s2))
        rows.append(r)
        print(f"  external {p}: dmso in {r['n_cols_with_dmso']} columns "
              f"{r['dmso_cols']} | max share in one column {r['dmso_max_share_one_col']:.3f} "
              f"(p={r['dmso_layout_p_col_perm']:.4f}) | position-only CV AUC "
              f"{r['position_only_cv_auc']:.4f} | layout transfer pilot1->here "
              f"{r.get('layout_transfer_auc_pilot1_to_here', float('nan')):.4f}", flush=True)

    dest = os.path.join(REPORTS, "21_stage12_position_audit.csv")
    pd.DataFrame(rows).to_csv(dest, index=False)
    print("wrote " + dest)
    return 0


# --------------------------------------------------------------------------- retrieval split

def retrieval_by_position(Xq, keys_q, wells_q, Xlib, keys_l, wells_l):
    """Cosine retrieval of the same compound in another plate, split by well coordinate.

    Each query well looks for its own InChIKey in the library plate. On the pilot a
    compound occupies one well per plate, so every query has exactly one true match - and
    because the two pilot plates are the same array, that match is also the well in the
    same position. On the external compound plates 8 compounds occupy 4 wells each, so a
    query can have up to 4 true matches, which is why the arms are defined per query:

      position-matched   - the compound also has a well at the query's own coordinate;
      position-decoupled - the compound has at least one well at another coordinate
                           (a query can appear in both arms);
      decoupled-only     - the compound has *no* well at the query's coordinate, so the
                           task cannot be done by reading the layout at all. This is the
                           strict arm and the one the retrieval claim should rest on.

    "Same compound" and "same well" are the same statement in a layout-matched pair, so a
    good rank there does not show that morphology identified the compound.
    """
    A = normalize(np.asarray(Xq, float), norm="l2", axis=1)
    B = normalize(np.asarray(Xlib, float), norm="l2", axis=1)
    S = A @ B.T
    n_lib = S.shape[1]
    groups = {"position-matched": [], "position-decoupled": [], "decoupled-only": []}
    nulls = {k: [] for k in groups}
    for i in range(S.shape[0]):
        match = np.where(np.asarray(keys_l) == keys_q[i])[0]
        if not len(match):
            continue
        same = [j for j in match if wells_l[j] == wells_q[i]]
        diff = [j for j in match if wells_l[j] != wells_q[i]]
        order = np.argsort(S[i])[::-1]
        rank_of = {int(j): int(np.where(order == j)[0][0]) + 1 for j in match}
        if same:
            groups["position-matched"].append(min(rank_of[j] for j in same))
            nulls["position-matched"].append(len(same) / n_lib)
        if diff:
            groups["position-decoupled"].append(min(rank_of[j] for j in diff))
            nulls["position-decoupled"].append(len(diff) / n_lib)
            if not same:
                groups["decoupled-only"].append(min(rank_of[j] for j in diff))
                nulls["decoupled-only"].append(len(diff) / n_lib)
    out = {}
    for kind, ranks in groups.items():
        if not ranks:
            continue
        rr = np.array(ranks)
        n_null = float(np.mean(nulls[kind]))
        out[kind] = {"n_queries": int(len(rr)), "median_rank": float(np.median(rr)),
                     "mean_rank": float(rr.mean()),
                     "recall_at_1": float(np.mean(rr <= 1)),
                     "recall_at_5": float(np.mean(rr <= 5)),
                     "recall_at_10": float(np.mean(rr <= 10)),
                     "chance_recall_at_1": float(1.0 / n_lib),
                     "chance_recall_at_1_any_accepted_match": n_null,
                     "chance_recall_at_10": float(1 - (1 - 1.0 / n_lib) ** 10),
                     "n_library_wells": int(n_lib)}
    return out


def stage_retrieval(args):
    """Where does the committed cross-plate retrieval number actually come from?

    reports/20_stage11_p3_cross_plate_summary.json measures same-compound retrieval between
    the pilot's two plates (R@1 0.331 / 0.369, pair AUC 0.8848). This stage first
    establishes, by measurement rather than by inspection of the metadata, that those two
    plates are the same array: 384/384 wells carry the identical compound, so every one of
    those retrieval positives is also a same-position well. Then it runs the same metric on
    pairs from the external site, where plate 1053600674 shares compounds with the compound
    plates at *different* coordinates, giving the position-decoupled arm the pilot cannot.
    Measured sharing (`21_stage12_replicate_sharing.json`): each usable external pair shares
    only 8-10 compounds, of which 224 of 291 compound-pair cells are 4-well-vs-4-well at the
    identical coordinates; the 67 cells with zero coordinate overlap (1-2 wells on one side
    against 4 on the other) are what the strict `decoupled-only` arm is made of.

    Feature blocks are each plate's own negcon robust-z (external: on the features shared
    with the pilot; pilot: its published 904, and the same 601-feature subset for a
    like-for-like comparison). Cosine on L2-normalised rows, as in stage11_p3.
    """
    plates = sorted(f[:-8] for f in os.listdir(EXT)
                    if f.endswith(".parquet") and f[0].isdigit())
    if not plates:
        print("nothing to score - run --stage fetch --sets meta,profiles first")
        return 1
    p1 = load_pilot([PILOT_PLATES[0]])
    p2 = load_pilot([PILOT_PLATES[1]])
    pilot_feats = [c for c in p1.columns if c.startswith(FEAT_PREFIX)]
    ext0 = load_external_table(plates[0])
    common = [c for c in pilot_feats if c in ext0.columns and ext0[c].dtype.kind in "fi"]

    same_layout = (p1["Metadata_Well"].astype(str).to_numpy()
                   == p2["Metadata_Well"].astype(str).to_numpy())
    k1 = p1["Metadata_InChIKey"].astype(str).to_numpy()
    k2 = p2["Metadata_InChIKey"].astype(str).to_numpy()
    print(f"pilot layout check: {len(same_layout)} wells, "
          f"{int(same_layout.sum())} share their well barcode and "
          f"{int((k1 == k2).sum())} of those carry the identical InChIKey "
          f"(treated wells: {int(((k1 == k2) & (p1['Metadata_pert_type'].astype(str).str.lower() == 'trt')).sum())}"
          f"/{int((p1['Metadata_pert_type'].astype(str).str.lower() == 'trt').sum())})")

    t1, d1 = pilot_labels(p1)
    t2, d2 = pilot_labels(p2)
    w1 = p1["Metadata_Well"].astype(str).to_numpy()
    w2 = p2["Metadata_Well"].astype(str).to_numpy()
    rows = []
    for tag, cols in [("pilot_904", pilot_feats), ("pilot_common_601", common)]:
        Xa = clean_matrix(p1[cols], cols)[0][t1]
        Xb = clean_matrix(p2[cols], cols)[0][t2]
        g = retrieval_by_position(Xa, k1[t1], w1[t1], Xb, k2[t2], w2[t2])
        for kind, v in g.items():
            rows.append({"site": "pilot in-site cross-plate", "pair": f"{PILOT_PLATES[0]}->{PILOT_PLATES[1]}",
                         "features": tag, "split": kind, **v})
            print(f"  pilot {tag:17s} {kind:19s} n={v['n_queries']:4d} "
                  f"R@1 {v['recall_at_1']:.3f} (chance {v['chance_recall_at_1']:.4f}) "
                  f"R@10 {v['recall_at_10']:.3f} median rank {v['median_rank']:.0f}")

    ext = {}
    for p in plates:
        df = load_external_table(p)
        key = df["Metadata_InChIKey"].astype(str).to_numpy()
        jcp = df["Metadata_JCP2022"].astype(str).to_numpy()
        dmso = (key == DMSO_INCHIKEY)
        trt = ~dmso & ~np.isin(jcp, UNKNOWN_JCP)
        if trt.sum() < 8 or dmso.sum() < 8:
            continue
        X = clean_matrix(pd.DataFrame(scale_side(df, common, dmso, "negcon_z"),
                                      columns=common), common)[0]
        ext[p] = {"X": X, "key": key, "trt": trt,
                  "well": df["Metadata_Well"].astype(str).to_numpy()}
    print(f"\nexternal plates usable for retrieval: {len(ext)}")
    for a, b in itertools.permutations(sorted(ext), 2):
        A, B = ext[a], ext[b]
        if not set(A["key"][A["trt"]]) & set(B["key"][B["trt"]]):
            continue
        g = retrieval_by_position(A["X"][A["trt"]], A["key"][A["trt"]], A["well"][A["trt"]],
                                  B["X"][B["trt"]], B["key"][B["trt"]], B["well"][B["trt"]])
        for kind, v in g.items():
            rows.append({"site": "external cpg0016 within-site", "pair": f"{a}->{b}",
                         "features": "negcon_z_common_601", "split": kind, **v})
            print(f"  {a}->{b} {kind:19s} n={v['n_queries']:4d} "
                  f"R@1 {v['recall_at_1']:.3f} (chance {v['chance_recall_at_1']:.4f}) "
                  f"R@10 {v['recall_at_10']:.3f} median rank {v['median_rank']:.0f}", flush=True)

    df = pd.DataFrame(rows)
    dest = os.path.join(REPORTS, "21_stage12_retrieval_position_split.csv")
    df.to_csv(dest, index=False)
    pooled = {}
    for (site, split), sub in df.groupby(["site", "split"]):
        n = int(sub["n_queries"].sum())
        pooled[f"{site} | {split}"] = {
            "n_queries": n,
            "recall_at_1": float((sub["recall_at_1"] * sub["n_queries"]).sum() / n),
            "recall_at_10": float((sub["recall_at_10"] * sub["n_queries"]).sum() / n),
            "median_rank": float(sub["median_rank"].median()),
            "chance_recall_at_1": float(sub["chance_recall_at_1"].mean()),
            "chance_recall_at_1_any_accepted_match":
                float((sub["chance_recall_at_1_any_accepted_match"] * sub["n_queries"]).sum() / n)}
    # Paired contrast. The two splits are disjoint query sets by construction (a query's
    # true match is either at the same coordinate or it is not), so the unit that can be
    # paired is the plate pair: every pair that has shared compounds contributes one R@1
    # to each arm. The bootstrap below resamples plate pairs, not wells, because the
    # replicates inside a pair share the two plates' batch.
    ext_only = [r for r in rows if r["site"] == "external cpg0016 within-site"
                and r["features"] == "negcon_z_common_601"]
    by_pair = {}
    for r in ext_only:
        by_pair.setdefault(r["pair"], {})[r["split"]] = r
    from scipy.stats import wilcoxon

    def paired_arm(arm_a, arm_b):
        keys = sorted(k for k, v in by_pair.items() if arm_a in v and arm_b in v)
        if not keys:
            return None
        a = np.array([by_pair[k][arm_a]["recall_at_1"] for k in keys])
        b = np.array([by_pair[k][arm_b]["recall_at_1"] for k in keys])
        n_a = np.array([by_pair[k][arm_a]["n_queries"] for k in keys], float)
        n_b = np.array([by_pair[k][arm_b]["n_queries"] for k in keys], float)
        w_a, w_b = n_a / n_a.sum(), n_b / n_b.sum()
        diff = a - b
        rng = np.random.default_rng(12)
        boots = []
        for _ in range(2000):
            idx = rng.integers(0, len(keys), len(keys))
            ww = n_a[idx] / n_a[idx].sum()
            boots.append(float((a[idx] * ww).sum()))
        return {
            "arm_a": arm_a, "arm_b": arm_b,
            "n_plate_pairs_with_both_arms": len(keys),
            f"{arm_a}_recall_at_1_query_weighted": float((a * w_a).sum()),
            f"{arm_a}_recall_at_1_plate_pair_bootstrap_95CI":
                [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            f"{arm_b}_recall_at_1_query_weighted": float((b * w_b).sum()),
            "mean_paired_difference_a_minus_b": float(diff.mean()),
            "wilcoxon_p_a_gt_b": (float(wilcoxon(diff, alternative="greater").pvalue)
                                  if diff.any() else None),
            "n_pairs_a_gt_b": int((diff > 0).sum()),
            "n_pairs_a_lt_b": int((diff < 0).sum()),
            "n_queries_a": int(n_a.sum()), "n_queries_b": int(n_b.sum()),
            "unit": "plate pair (ordered); R@1 averaged over its shared-compound queries",
        }
    paired = paired_arm("position-decoupled", "position-matched")
    strict = paired_arm("decoupled-only", "position-matched")

    def arm_summary(arm):
        """Query-weighted R@1 for one arm with a plate-pair bootstrap, plus the null that
        applies when several library wells count as correct matches (a 4-replicate compound
        gives 4 accepted matches, so 1/n_library understates chance R@1)."""
        keys = sorted(k for k, v in by_pair.items() if arm in v)
        if not keys:
            return None
        a = np.array([by_pair[k][arm]["recall_at_1"] for k in keys])
        n_a = np.array([by_pair[k][arm]["n_queries"] for k in keys], float)
        nul = np.array([by_pair[k][arm]["chance_recall_at_1_any_accepted_match"] for k in keys])
        rng = np.random.default_rng(12)
        boots = []
        for _ in range(2000):
            idx = rng.integers(0, len(keys), len(keys))
            boots.append(float((a[idx] * n_a[idx] / n_a[idx].sum()).sum()))
        return {"arm": arm, "n_plate_pairs": len(keys), "n_queries": int(n_a.sum()),
                "recall_at_1_query_weighted": float((a * n_a / n_a.sum()).sum()),
                "recall_at_1_plate_pair_bootstrap_95CI":
                    [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
                "chance_recall_at_1_single_match":
                    float(np.mean([by_pair[k][arm]["chance_recall_at_1"] for k in keys])),
                "chance_recall_at_1_any_accepted_match_query_weighted":
                    float((nul * n_a / n_a.sum()).sum()),
                "per_pair_recall_at_1_min": float(a.min()), "per_pair_recall_at_1_max": float(a.max()),
                "n_pairs_also_having_position_matched":
                    int(sum("position-matched" in by_pair[k] for k in keys))}
    arm_summaries = {arm: arm_summary(arm) for arm in
                     ("position-matched", "position-decoupled", "decoupled-only")}
    for arm, s in arm_summaries.items():
        if s is None:
            continue
        ci = s["recall_at_1_plate_pair_bootstrap_95CI"]
        print("\narm summary [%s]: %d pairs, n=%d queries, R@1 %.4f [%.4f, %.4f]; "
              "chance R@1 %.4f (single match) / %.4f (any accepted replicate match); "
              "per-pair R@1 %.3f-%.3f; %d of these pairs also have a position-matched arm"
              % (arm, s["n_plate_pairs"], s["n_queries"],
                 s["recall_at_1_query_weighted"], ci[0], ci[1],
                 s["chance_recall_at_1_single_match"],
                 s["chance_recall_at_1_any_accepted_match_query_weighted"],
                 s["per_pair_recall_at_1_min"], s["per_pair_recall_at_1_max"],
                 s["n_pairs_also_having_position_matched"]))
    for name, p in (("decoupled vs matched", paired), ("decoupled-only vs matched", strict)):
        if p is None:
            continue
        a, b = p["arm_a"], p["arm_b"]
        ci = p[a + "_recall_at_1_plate_pair_bootstrap_95CI"]
        print("\npaired [%s] over %d plate pairs: %s R@1 %.4f [%.4f, %.4f] (n=%d) "
              "vs %s %.4f (n=%d); mean difference %+.4f, Wilcoxon p (%s>%s) = %.4f; "
              "%d pairs better / %d worse"
              % (name, p["n_plate_pairs_with_both_arms"], a,
                 p[a + "_recall_at_1_query_weighted"], ci[0], ci[1], p["n_queries_a"],
                 b, p[b + "_recall_at_1_query_weighted"], p["n_queries_b"],
                 p["mean_paired_difference_a_minus_b"], a, b, p["wilcoxon_p_a_gt_b"],
                 p["n_pairs_a_gt_b"], p["n_pairs_a_lt_b"]))
    with open(os.path.join(REPORTS, "21_stage12_retrieval_position_split.json"), "w",
              encoding="utf-8") as f:
        json.dump({"per_pair": rows, "pooled": pooled, "paired_by_plate_pair": paired,
                   "paired_strict_by_plate_pair": strict,
                   "arm_summaries_by_plate_pair": arm_summaries,
                   "pilot_layout_note": "384/384 wells carry the identical compound in "
                                       "both pilot plates"}, f, indent=1, ensure_ascii=False)
    print("\npooled:")
    for k, v in pooled.items():
        print(f"  {k:42s} n={v['n_queries']:5d} R@1 {v['recall_at_1']:.3f} "
              f"(chance {v['chance_recall_at_1']:.4f}) R@10 {v['recall_at_10']:.3f}")
    print("wrote " + dest)
    return 0


def stage_evaluate(args):
    """Train trt-vs-DMSO on the pilot plate, test it on an independent site's plates.

    The classifier and the seed are the ones stage11_p3 used, so the only thing that
    changes between the in-site reference (cross-plate AUC 0.683 / AP 0.911) and this run
    is that the test plates come from another dataset, another lab, and another batch of
    the JUMP protocol.

    Everything here is deliberately checkable against the numbers in
    reports/21_stage12_external_site_summary_*.json: which scaling was used, how many
    features survived the intersection, what the negative control scored, and what each
    individual plate scored.
    """
    plates = sorted(f[:-8] for f in os.listdir(EXT)
                    if f.endswith(".parquet") and f[0].isdigit())
    if not plates:
        print("nothing to evaluate - run --stage fetch --sets meta,profiles first")
        return 1

    pilot = load_pilot([args.train_plate])
    ptr, pdm = pilot_labels(pilot)
    pilot_feats = [c for c in pilot.columns if c.startswith(FEAT_PREFIX)]

    # build the external tables first, so the feature intersection is data-driven
    ext = []
    for p in plates:
        df = load_external_table(p)
        ext.append(df.assign(__plate=p))
    common = [c for c in pilot_feats if c in ext[0].columns
              and ext[0][c].dtype.kind in "fi"]
    print(f"pilot Cells/Cytoplasm/Nuclei features {len(pilot_feats)}  |  "
          f"present at the external site {len(common)} "
          f"({100*len(common)/max(1,len(pilot_feats)):.1f}%)")

    Xp_all, feats_kept, miss_p = clean_matrix(
        pd.DataFrame(scale_side(pilot, common, pdm, args.scaling),
                     columns=common), common)
    if not feats_kept:
        raise RuntimeError("pilot side kept zero features - scaling/arm is broken, "
                           "refusing to report a number")
    common = feats_kept
    keep = ptr | pdm                                # 1 = treated, 0 = DMSO vehicle
    ytr = ptr[keep].astype(int)
    print(f"pilot scaling={args.scaling} | training wells {int(keep.sum())} "
          f"(trt {int(ptr.sum())} / DMSO {int(pdm.sum())}), features kept {len(common)}, "
          f"imputed cells {miss_p}")

    # same-compound pool for the retrieval test: external compounds that also appear
    # among the pilot's treated wells
    pilot_trt_key = pilot.loc[ptr, "Metadata_InChIKey"].astype(str).to_numpy()

    results, per_plate, retr = [], [], []
    n_unknown_total = 0
    for df in ext:
        key = df["Metadata_InChIKey"].astype(str).to_numpy()
        jcp = df["Metadata_JCP2022"].astype(str).to_numpy()
        dmso = (key == DMSO_INCHIKEY)
        # 18 of 3838 external wells (0.47 %) carry the source's own `JCP2022_UNKNOWN`
        # placeholder, i.e. the curator could not assign them a compound. The primary
        # analysis drops them: they are neither confirmed treated nor vehicle. Counting
        # them as treated is kept as a named sensitivity arm, not hidden.
        unk = np.isin(jcp, UNKNOWN_JCP)
        n_unknown_total += int(unk.sum())
        trt = ~dmso & ~unk
        trt_with_unk = ~dmso
        if dmso.sum() < 8 or trt.sum() < 8:
            per_plate.append({"plate": df["__plate"].iloc[0], "n_trt": int(trt.sum()),
                              "n_dmso": int(dmso.sum()), "note": "skipped: <8 per class"})
            continue
        Xe, kept_e, miss_e = clean_matrix(
            pd.DataFrame(scale_side(df, common, dmso, args.scaling), columns=common), common)
        # Feature alignment is per plate and must be symmetric. `clean_matrix` drops a
        # column only when the whole plate has no finite value for it; silently feeding the
        # resulting narrower matrix into a classifier fitted on the wider pilot matrix would
        # compare feature i of one site with feature i+1 of the other. So drop the same
        # columns from the training side and record how many were used.
        Xtr = Xp_all[keep]
        if kept_e != common:
            lost = [c for c in common if c not in kept_e]
            Xtr = Xtr[:, [common.index(c) for c in kept_e]]
            print(f"  note: {df['__plate'].iloc[0]} has no finite value for "
                  f"{len(lost)} pilot feature(s) ({lost[:4]}{'...' if len(lost) > 4 else ''}) "
                  f"- dropped from both sides for this plate")
        score_all = fit_score(Xtr, ytr, Xe)
        # Vehicle LAYOUT is a property of the plate, and it decides what the cross-site
        # number can mean. Measured here: the eight compound plates put every DMSO well in
        # columns 02 and 23, so at that site the treatment contrast is *identical* to a
        # column contrast, and column-level batch effects are exactly what a classifier
        # trained on another site cannot share. Plate 1053600674 scatters its vehicle over
        # 24 columns, i.e. it is the one plate where the two are separable. Report both,
        # never pooled into a single number.
        _, dcol = well_coords(df["Metadata_Well"].to_numpy())
        n_dmso_cols = int(len(set(dcol[dmso].tolist())))
        group = ("vehicle-in-fixed-columns" if n_dmso_cols <= 4 else "vehicle-scattered")
        sel = trt | dmso                       # the 18 unknown-identity wells sit in
        y = trt[sel].astype(int)               # neither class and are removed here
        score = score_all[sel]
        auc = float(roc_auc_score(y, score))
        ap = float(average_precision_score(y, score))
        # Sensitivity arm over ALL wells of the plate, unknowns counted as treated.
        # (An earlier version subsetted by `sel` first, which made this identical to the
        # primary AUC by construction - the same labels in the same order. It has to be
        # computed on the unsubsetted arrays or it tests nothing.)
        auc_unk = (float(roc_auc_score(trt_with_unk.astype(int), score_all))
                   if unk.sum() > 0 else auc)
        loc_auc, loc_ap = cv_auc_ap(Xe[sel], y)
        row = {"plate": df["__plate"].iloc[0], "n_trt": int(trt.sum()),
               "n_dmso": int(dmso.sum()), "n_unknown_wells_dropped": int(unk.sum()),
               "n_features_used": len(kept_e),
               "dmso_n_columns": n_dmso_cols, "vehicle_layout": group,
               "cross_site_AUC": auc, "cross_site_AP": ap,
               "AP_prevalence_floor": float(y.mean()), "AP_lift_over_floor": ap - float(y.mean()),
               "cross_site_AUC_if_unknown_counted_treated": auc_unk,
               "within_site_5fold_AUC": loc_auc, "within_site_5fold_AP": loc_ap,
               "n_imputed_cells": miss_e}
        per_plate.append(row)
        results.append((y, score, Xe[sel], group))

        shared = trt & np.isin(key, pilot_trt_key)
        r = {}
        if shared.sum() >= 5:
            r = retrieval_cross_site(Xe[shared], key[shared],
                                     Xp_all[ptr], pilot_trt_key) or {}
            if r:
                r["plate"] = df["__plate"].iloc[0]
                r["n_shared_compounds"] = int(shared.sum())
                retr.append(r)
        t1 = (f"{r.get('recall_at_1', float('nan')):.3f}"
              f"(chance {r.get('chance_recall_at_1_random_ranking', float('nan')):.3f})"
              if shared.sum() >= 5 else "-")
        print(f"  {row['plate']}: trt={row['n_trt']:3d} dmso={row['n_dmso']:3d} "
              f"cross-site AUC {auc:.4f} AP {ap:.4f} | within-site "
              f"{loc_auc:.4f}/{loc_ap:.4f} | shared-with-pilot wells "
              f"{int(shared.sum())} -> top1 {t1}")

    if not results:
        print("\nno plate had a usable DMSO/trt split - external test is UNVERIFIED, "
              "not reported as a number")
        return 2

    y = np.concatenate([r[0] for r in results])
    s = np.concatenate([r[1] for r in results])
    pooled_auc = float(roc_auc_score(y, s))
    pooled_ap = float(average_precision_score(y, s))
    # Cluster bootstrap over PLATES, not wells. Wells inside one plate share a batch,
    # a microscope session and a DMSO normalisation, so a well-level CI would be far
    # narrower than the evidence supports. The plate is the independent unit here.
    rng_boot = np.random.default_rng(RANDOM_STATE)

    def plate_boot(blocks):
        boots = []
        for _ in range(2000):
            pick = [blocks[i] for i in rng_boot.integers(0, len(blocks), len(blocks))]
            by = np.concatenate([b[0] for b in pick])
            bs = np.concatenate([b[1] for b in pick])
            if by.min() == by.max():
                continue
            boots.append(roc_auc_score(by, bs))
        boots = np.array(boots)
        return {"AUC": float(roc_auc_score(np.concatenate([b[0] for b in blocks]),
                                           np.concatenate([b[1] for b in blocks]))),
                "AUC_plate_bootstrap_95CI": [float(np.quantile(boots, 0.025)),
                                             float(np.quantile(boots, 0.975))],
                "AUC_plate_bootstrap_n": int(len(boots)),
                "AUC_bootstrap_prob_above_0.5": float(np.mean(boots > 0.5))}

    plate_blocks = [(r[0], r[1]) for r in results]
    boot = plate_boot(plate_blocks)
    auc_ci = boot["AUC_plate_bootstrap_95CI"]
    auc_p_gt_half = boot["AUC_bootstrap_prob_above_0.5"]
    n_boot = boot["AUC_plate_bootstrap_n"]
    # Stratify by vehicle layout. The eight compound plates place every vehicle well in
    # columns 02 and 23, so their label contrast coincides with a column contrast; plate
    # 1053600674 scatters its vehicle across 24 columns, which makes it the only plate
    # where "treated vs vehicle" is separable from "which column you are in". A pooled
    # number is dominated by the confounded stratum, so both are reported, and the
    # single-plate stratum gets no bootstrap CI - one plate is one observation.
    strata = {}
    for g in sorted({r[3] for r in results}):
        blocks = [(r[0], r[1]) for r in results if r[3] == g]
        one = {"n_plates": len(blocks),
               "AUC": float(roc_auc_score(np.concatenate([b[0] for b in blocks]),
                                          np.concatenate([b[1] for b in blocks])))}
        if len(blocks) >= 3:
            one.update({k: v for k, v in plate_boot(blocks).items()
                        if k != "AUC"})
        strata[g] = one
        print(f"  stratum {g:24s}: {one['n_plates']} plate(s)  pooled AUC "
              f"{one['AUC']:.4f}" + (f" CI [{one['AUC_plate_bootstrap_95CI'][0]:.3f},"
                                     f"{one['AUC_plate_bootstrap_95CI'][1]:.3f}]"
                                     if "AUC_plate_bootstrap_95CI" in one else " (no CI: n=plates)"))
    plate_auc = np.array([r["cross_site_AUC"] for r in per_plate if "cross_site_AUC" in r])
    plate_ap = np.array([r["cross_site_AP"] for r in per_plate if "cross_site_AP" in r])
    w_auc = np.array([r["within_site_5fold_AUC"] for r in per_plate
                      if "within_site_5fold_AUC" in r])
    w_ap = np.array([r["within_site_5fold_AP"] for r in per_plate
                     if "within_site_5fold_AP" in r])

    # negative control: the same pipeline with the pilot's treatment labels shuffled.
    # If the cross-site AUC were an artefact of score scale or of DMSO wells being
    # systematically different in *any* way, this would still show it.
    rng = np.random.default_rng(RANDOM_STATE)
    y_shuf = ytr.copy()
    rng.shuffle(y_shuf)
    ctrl_auc = ctrl_ap = float("nan")
    if results:
        Xext_all = np.vstack([r[2] for r in results])
        y_ext_all = np.concatenate([rr[0] for rr in results])
        ns = fit_score(Xp_all[keep], y_shuf, Xext_all)
        ctrl_auc = float(roc_auc_score(y_ext_all, ns))
        ctrl_ap = float(average_precision_score(y_ext_all, ns))

    # Protocol-matched in-site reference: the same features, the same classifier, the same
    # seed, with the test plate swapped back to the pilot's own second plate. The committed
    # stage11_p3 number (0.6825 / 0.9107) is computed on all 904 pilot features, so it is NOT
    # directly comparable to the cross-site row below; this reference is. Both are reported.
    pilot2 = load_pilot([PILOT_PLATES[1]])
    ptr2, pdm2 = pilot_labels(pilot2)
    Xp2, _, _ = clean_matrix(
        pd.DataFrame(scale_side(pilot2, common, pdm2, args.scaling), columns=common), common)
    sel2 = ptr2 | pdm2
    insite_score = fit_score(Xp_all[keep], ytr, Xp2[sel2])
    insite_y = ptr2[sel2].astype(int)
    insite_auc = float(roc_auc_score(insite_y, insite_score))
    insite_ap = float(average_precision_score(insite_y, insite_score))
    print(f"in-site reference under THIS protocol (pilot p1 -> pilot p2, {len(common)} "
          f"features): AUC {insite_auc:.4f} AP {insite_ap:.4f}")

    summary = {
        "experiment": "stage12 cross-site external validation",
        "train": {"dataset": "cpg0000-jump-pilot/source_4", "plate": args.train_plate,
                  "n_trt": int(ptr.sum()), "n_dmso": int(pdm.sum())},
        "test": {"dataset": SOURCE, "batch": BATCH, "plates_used": int(len(results)),
                 "plates_requested": len(plates), "n_trt": int(y.sum()),
                 "n_dmso": int((y == 0).sum()),
                 "n_unknown_identity_wells_dropped": int(n_unknown_total)},
        "features": {"pilot_cells_cyto_nuclei": len(pilot_feats),
                     "common_with_external": len(common)},
        "cross_site_pooled": {"AUC": pooled_auc, "AP": pooled_ap,
                              "AP_prevalence_floor": float(y.mean()),
                              "AP_lift_over_floor": float(pooled_ap - y.mean()),
                              "AUC_plate_bootstrap_95CI": auc_ci,
                              "AUC_plate_bootstrap_n": n_boot,
                              "AUC_bootstrap_prob_above_0.5": auc_p_gt_half},
        "cross_site_pooled_by_vehicle_layout": strata,
        "cross_site_per_plate": {"AUC_min": float(plate_auc.min()), "AUC_median":
                                 float(np.median(plate_auc)), "AUC_max": float(plate_auc.max()),
                                 "AP_min": float(plate_ap.min()), "AP_median":
                                 float(np.median(plate_ap)), "AP_max": float(plate_ap.max())},
        "within_site_per_plate": {"AUC_median": float(np.median(w_auc)),
                                  "AP_median": float(np.median(w_ap))},
        "negative_control_shuffled_pilot_labels": {"AUC": ctrl_auc, "AP": ctrl_ap},
        "cross_site_same_compound_retrieval": retr,
        "in_site_reference_cross_plate": {"AUC": 0.6825120192307691,
                                          "AP": 0.9106727827503514,
                                          "source": "reports/20_stage11_p3_cross_plate_summary.json"},
        # The committed 0.6825 is a 904-feature protocol; this arm reruns the *same*
        # pipeline as the cross-site row above with the test plate swapped back to the
        # pilot's own plate 2 (601 common features). Only this number is comparable to
        # the cross-site AUC, so it is stored next to it instead of living in stdout.
        "in_site_reference_this_protocol": {"AUC": insite_auc, "AP": insite_ap,
                                            "train": "pilot BR00116991",
                                            "test": "pilot BR00116992",
                                            "n_features": len(common),
                                            "scaling": args.scaling},
        "normalisation": "both sides: per-plate robust z against that plate's own DMSO "
                         "wells (mode " + args.scaling + "). Note this is not something the "
                         "pipeline had to enforce on the pilot side - its published table is "
                         "already that transform, see pilot_pre_normalisation_check",
        "pilot_pre_normalisation_check": pilot_is_already_negcon_z(pilot, common, pdm),
        "label_symmetry": "both sides define DMSO by InChIKey "
                          f"({DMSO_INCHIKEY}); the external positives carry no poscon "
                          "annotation, so the external negative class is pure vehicle",
        "scaling_applied_identically_to_both_sides": args.scaling,
        "manifest_rows": len(read_manifest()),
        "manifest_bytes": int(sum(int(r["bytes"]) for r in read_manifest().values()
                                  if r["status"] in ("ok", "exists"))),
    }
    tag = args.out_tag or args.scaling
    pd.DataFrame(per_plate).to_csv(os.path.join(REPORTS, f"21_stage12_external_per_plate_{tag}.csv"), index=False)
    with open(os.path.join(REPORTS, f"21_stage12_external_site_summary_{tag}.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)
    print(json.dumps(summary, indent=1)[:2600])
    return 0


# --------------------------------------------------------------------------- stage: diagnose

SCALES = ("negcon_z", "rank", "zclip5", "posresid")


def scale_side(df, feats, dmso_mask, mode):
    """Turn one side's raw feature block into the matrix the classifier actually sees.

    `negcon_z` (cross-site AUC 0.5041 on plate 1053600674, 0.5695 pooled over the 9 usable
    plates) is the base protocol. `rank` and `zclip5` were added after the tail-weight
    diagnostic showed the external robust-z reaching |z| = 6383 where the pilot reached 451.

      negcon_z  per-side robust z against that side's own DMSO wells:
                (x - median_dmso) / (1.4826 * MAD_dmso).
                Verified (see `pilot_is_already_negcon_z`) to be what the pilot file
                already publishes - `normalized_feature_select_negcon_batch` is this
                transform, so there is no "naive asymmetric normalisation" arm left to test:
                the two sides enter the classifier in the same units by construction.
      rank      per-feature within-dataset rank -> standard normal. Monotone, so it leaves
                within-site AUC untouched but removes the tail-weight difference that lets
                a handful of near-constant features dominate a 601-feature LR.
      zclip5    negcon_z, then clipped to +-5: keeps the scale comparison, caps the extremes.
      posresid  negcon_z, then additive row and column effects removed within that
                dataset (two-way residual). Diagnostic, not a fix: at the external site
                the vehicle occupies whole columns, so column structure and treatment are
                confounded and this arm subtracts real signal along with the layout
                signal. Read it together with `--stage position`: whatever survives is not
                position, whatever dies was at least partly a plate-layout readout.

    Every mode is applied identically to both sides, so a difference between arms is a
    property of the transform, not of one dataset.
    """
    X = robust_z(df, feats, dmso_mask)
    if mode == "zclip5":
        X = np.clip(X, -5, 5)
    if mode == "rank":
        n = X.shape[0]
        ranks = np.apply_along_axis(lambda v: pd.Series(v).rank(method="average").to_numpy(),
                                    0, X)
        X = _ndtri((ranks - 0.5) / n)
    if mode == "posresid":
        if "Metadata_Well" not in df.columns:
            raise RuntimeError("posresid needs Metadata_Well on both sides - "
                               "the external join must carry the well barcode")
        # impute before the regression, or a single NaN cell poisons lstsq's coefficient for
        # the whole feature and turns one missing value into a column of NaNs.
        X = impute_finite(X)
        X = residualize_position(X, df["Metadata_Well"].to_numpy())
    return X


def _ndtri(p):
    from scipy.stats import norm
    return norm.ppf(np.clip(p, 1e-6, 1 - 1e-6))


def pilot_is_already_negcon_z(pilot, feats, dmso_mask):
    """Check whether the pilot's published table is already the DMSO robust-z it is
    labelled as, i.e. whether applying `robust_z` to it again is a no-op.

    Returns the worst-case deviation over features. If it is ~0 the "we normalised both
    sides the same way" claim is automatic rather than something the pipeline buys, and
    the asymmetric-normalisation hypothesis can be closed instead of merely tested.
    """
    X = pilot[feats].to_numpy(float)
    sub = X[dmso_mask]
    med = np.nanmedian(sub, axis=0)
    scale = np.nanmedian(np.abs(sub - med), axis=0) * 1.4826
    return {"n_pilot_dmso_wells": int(dmso_mask.sum()), "n_features_checked": len(feats),
            "max_abs_dmso_median": float(np.nanmax(np.abs(med))),
            "robust_scale_min": float(np.nanmin(scale)),
            "robust_scale_max": float(np.nanmax(scale)),
            "already_negcon_robust_z": bool(np.nanmax(np.abs(med)) < 1e-6
                                            and np.allclose(scale, 1.0, atol=1e-4))}


def fit_clf(X, y):
    sc = StandardScaler().fit(X)
    lr = LogisticRegression(max_iter=5000, class_weight="balanced",
                            random_state=RANDOM_STATE).fit(sc.transform(X), y)
    return sc, lr


def stage_diagnose(args):
    """Why is the cross-site AUC ~0.50 while the same site's within-site CV is ~0.73?

    AUC is rank-based, so a global batch offset cannot by itself produce 0.50 - the
    disagreement has to live in the *directions* the classifier uses. Two candidate
    mechanisms were checked and one of them is now closed by measurement rather than
    argued away:

      * asymmetric normalisation - CLOSED. The pilot file is already the DMSO robust-z
        (`pilot_is_already_negcon_z` below reports the worst-case deviation), so both
        sides enter the model in the same units without this script doing anything.
      * tail weight - OPEN. |z| reaches 6383 on the external side against 451 on the
        pilot side, and a 601-feature logistic regression is driven by exactly those
        columns, so `rank` and `zclip5` are the arms that isolate it.

    So this stage runs the same transfer under three scalings, each applied identically to
    both sides, and reports for every one of them:

      forward  pilot -> external            AUC / AP
      reverse  external -> pilot            AUC / AP   (same problem, labels swapped)
      coef cosine + Spearman between the two sites' own fitted weight vectors
      the 99.9th percentile of |value| on each side, which is the tail-weight diagnostic

    Whatever the report ends up claiming about the mechanism has to come from this table.
    """
    plates = sorted(f[:-8] for f in os.listdir(EXT)
                    if f.endswith(".parquet") and f[0].isdigit())
    pilot = load_pilot([args.train_plate])
    ptr, pdm = pilot_labels(pilot)
    exts = [load_external_table(p) for p in plates]
    common = [c for c in pilot.columns if c.startswith(FEAT_PREFIX)
              and c in exts[0].columns and exts[0][c].dtype.kind in "fi"]
    keep = ptr | pdm
    y_p = ptr.astype(int)
    keys, y_e, dm_e, usable = [], [], [], []
    skipped = []
    sel_e = []
    for p, df in zip(plates, exts):
        k = df["Metadata_InChIKey"].astype(str).to_numpy()
        jcp = df["Metadata_JCP2022"].astype(str).to_numpy()
        dm = (k == DMSO_INCHIKEY)
        trt = ~dm & ~np.isin(jcp, UNKNOWN_JCP)
        # same rules as stage_evaluate: a plate without both classes cannot be scored, and
        # leaving an all-DMSO control plate in the pool inflates the prevalence floor of AP
        # and moves the pooled score scale. It is excluded and named, not silently dropped.
        # Unknown-identity wells are dropped from the labels but still take part in the
        # plate's own DMSO normalisation, which is a per-plate property of all its wells.
        if dm.sum() < 8 or trt.sum() < 8:
            skipped.append({"plate": p, "n_dmso": int(dm.sum()), "n_trt": int(trt.sum())})
            continue
        usable.append(p)
        keys.append(k); dm_e.append(dm); y_e.append(trt.astype(int)); sel_e.append(dm | trt)
    y_ext = np.concatenate([yy[s] for yy, s in zip(y_e, sel_e)])
    ap_floor = float(y_ext.mean())
    from scipy.stats import spearmanr

    table = []
    for mode in SCALES:
        P = pd.DataFrame(scale_side(pilot, common, pdm, mode),
                         columns=common)
        Xp, cols, _ = clean_matrix(P, common)
        Xe_blocks = []
        for p, df, dm, sel in zip(usable, [exts[plates.index(pr)] for pr in usable],
                                  dm_e, sel_e):
            E = pd.DataFrame(scale_side(df, cols, dm, mode), columns=cols)
            b, kept_b, _ = clean_matrix(E, cols)
            if kept_b != cols:
                raise RuntimeError(
                    f"diagnose: plate {p} dropped {len(cols) - len(kept_b)} feature(s) "
                    "after scaling, which would misalign the pooled matrix - the vstack "
                    "here assumes one shared feature block for both classifiers")
            Xe_blocks.append(b[sel])
        Xe = np.vstack(Xe_blocks)

        sc_p, lr_p = fit_clf(Xp[keep], y_p[keep])
        se = lr_p.decision_function(sc_p.transform(Xe))
        sc_e, lr_e = fit_clf(Xe, y_ext)
        sr = lr_e.decision_function(sc_e.transform(Xp))
        w_p, w_e = lr_p.coef_[0], lr_e.coef_[0]
        top50 = np.argsort(-np.abs(w_p))[:50]
        q999 = lambda M: float(np.quantile(np.abs(M[np.isfinite(M)]), 0.999))
        row = {
            "scaling": mode,
            "forward_AUC": float(roc_auc_score(y_ext, se)),
            "forward_AP": float(average_precision_score(y_ext, se)),
            "reverse_AUC": float(roc_auc_score(y_p[keep], sr[keep])),
            "reverse_AP": float(average_precision_score(y_p[keep], sr[keep])),
            "coef_cosine": float(np.dot(w_p, w_e) / (np.linalg.norm(w_p) * np.linalg.norm(w_e))),
            "coef_spearman": float(spearmanr(w_p, w_e).statistic),
            "sign_agree_pilot_top50": float(np.mean(np.sign(w_p[top50]) == np.sign(w_e[top50]))),
            "abs_p999_pilot": q999(Xp), "abs_p999_external": q999(Xe),
            "forward_AP_floor": ap_floor,
            "forward_AP_lift_over_floor": float(
                average_precision_score(y_ext, se) - ap_floor),
            "ext_dmso_called_treated_rate": float(np.mean(se[y_ext == 0] > np.median(se[y_ext == 1]))),
        }
        table.append(row)
        print(f"  {mode:10s} fwd AUC {row['forward_AUC']:.4f} AP {row['forward_AP']:.4f} | "
              f"rev AUC {row['reverse_AUC']:.4f} AP {row['reverse_AP']:.4f} | "
              f"coef cos {row['coef_cosine']:+.3f} rho {row['coef_spearman']:+.3f} "
              f"sign50 {row['sign_agree_pilot_top50']:.2f} | "
              f"|z|p999 pilot {row['abs_p999_pilot']:.0f} ext {row['abs_p999_external']:.0f}")

    out = {"plates": plates, "plates_used": usable, "plates_skipped": skipped,
           "n_common_features": len(common),
           "ext_AP_prevalence_floor": ap_floor,
           "pilot_trt": int(ptr.sum()), "pilot_dmso": int(pdm.sum()),
           "ext_trt": int(y_ext.sum()), "ext_dmso": int((y_ext == 0).sum()),
           "in_site_reference_cross_plate": {"AUC": 0.6825120192307691,
                                             "AP": 0.9106727827503514},
           "table": table}
    dest = os.path.join(REPORTS, "21_stage12_external_diagnose.json")
    pd.DataFrame(table).to_csv(os.path.join(REPORTS, "21_stage12_external_diagnose.csv"),
                               index=False)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("\nwrote " + dest)
    return 0


def stage_trainsize(args):
    """Is the cross-site gap a data-size problem or a domain problem?

    If the pilot's 260 treated wells are simply too few, the cross-site AUC should climb as
    the pilot training set grows - and it should climb higher with the second pilot plate
    (same site, same batch) than with anything else. If instead the curve flattens early,
    the missing generalisation is between sites and no amount of pilot-only data buys it
    back, which changes what the next experiment should be.

    Subsets are drawn at compound level, not well level, so a fraction means "that many
    distinct compounds", which is the unit that actually carries independent information.
    """
    plates = sorted(f[:-8] for f in os.listdir(EXT)
                    if f.endswith(".parquet") and f[0].isdigit())
    exts = [(p, load_external_table(p)) for p in plates]
    blocks, labs, usable = [], [], []
    for p, df in exts:
        key = df["Metadata_InChIKey"].astype(str).to_numpy()
        jcp = df["Metadata_JCP2022"].astype(str).to_numpy()
        dm = (key == DMSO_INCHIKEY)
        trt = ~dm & ~np.isin(jcp, UNKNOWN_JCP)
        if dm.sum() < 8 or trt.sum() < 8:
            continue
        sel = dm | trt
        blocks.append((df, dm, trt, sel))
        labs.append(trt[sel].astype(int))
        usable.append(p)
    y_ext = np.concatenate(labs)
    print(f"{len(blocks)} usable external plates, {int(y_ext.sum())} treated / "
          f"{int((y_ext == 0).sum())} DMSO wells", flush=True)

    rows = []
    per_plate = {}
    # Paired in-site reference: the SAME training subsets, evaluated on the pilot's own
    # second plate. Without this, "fewer compounds transfers better" cannot be told apart
    # from "fewer compounds is just an easier classifier". If the two curves move in the
    # same direction the effect is a training-set property; if only the cross-site curve
    # falls as the pilot set grows, the extra pilot data is adding site-specific direction.
    insite = load_pilot([PILOT_PLATES[1]])
    iptr, ipdm = pilot_labels(insite)
    isel = iptr | ipdm
    iy = iptr[isel].astype(int)
    for train_plates, tag in [([args.train_plate], "1 plate"),
                              (PILOT_PLATES, "2 plates")]:
        pilot = load_pilot(train_plates)
        ptr, pdm = pilot_labels(pilot)
        feats = [c for c in pilot.columns if c.startswith(FEAT_PREFIX)
                 and c in exts[0][1].columns
                 and exts[0][1][c].dtype.kind in "fi"]
        Xp, cols, _ = clean_matrix(
            pd.DataFrame(scale_side(pilot, feats, pdm, args.scaling),
                         columns=feats), feats)
        Xe = np.vstack([clean_matrix(pd.DataFrame(
            scale_side(df, cols, dm, args.scaling), columns=cols), cols)[0][sel]
            for df, dm, trt, sel in blocks])
        Xi, _, _ = clean_matrix(
            pd.DataFrame(scale_side(insite, cols, ipdm, args.scaling),
                         columns=cols), cols)
        Xi = Xi[isel]
        keep = ptr | pdm
        compounds = pilot.loc[ptr, "Metadata_InChIKey"].astype(str).unique()
        rng = np.random.default_rng(RANDOM_STATE)
        fracs = [0.125, 0.25, 0.5, 1.0] if len(train_plates) == 1 else [0.5, 1.0]
        for fr in fracs:
            n_c = max(8, int(round(fr * len(compounds))))
            aucs = []
            aucs_in = []
            per_plate_auc = np.zeros((len(blocks), 0))
            for rep in range(5):
                take = set(rng.choice(compounds, size=n_c, replace=False).tolist())
                # subsample the TREATED class by compound; every DMSO well stays, so a
                # smaller circle is fewer compounds, not fewer controls
                pos = ptr & np.isin(pilot["Metadata_InChIKey"].astype(str).to_numpy(),
                                    list(take))
                sub = pos | pdm
                if ptr[sub].sum() < 20 or pdm[sub].sum() < 10:
                    continue
                sc = fit_score(Xp[sub], ptr[sub].astype(int), Xe)
                aucs.append(roc_auc_score(y_ext, sc))
                sc_pl, off = [], 0
                for (df, dm, trt, sel), yy in zip(blocks, labs):
                    n = len(yy)
                    sc_pl.append(roc_auc_score(yy, sc[off:off + n]))
                    off += n
                per_plate_auc = np.column_stack([per_plate_auc, np.array(sc_pl)])
                if tag == "1 plate":
                    aucs_in.append(roc_auc_score(iy, fit_score(
                        Xp[sub], ptr[sub].astype(int), Xi)))
            per_plate.setdefault(tag, {})[n_c] = per_plate_auc.mean(axis=1)
            row = {"pilot_train": tag, "pilot_compounds": n_c,
                   "pilot_wells_used": int(sub.sum()), "scaling": args.scaling,
                   "cross_site_AUC_mean": float(np.mean(aucs)),
                   "cross_site_AUC_sd": float(np.std(aucs)),
                   "in_site_plate2_AUC_mean": (float(np.mean(aucs_in)) if aucs_in else None),
                   "in_site_plate2_AUC_sd": (float(np.std(aucs_in)) if aucs_in else None),
                   "n_reps": len(aucs),
                   "in_site_reference": 0.6825120192307691}
            rows.append(row)
            ins = (f"{row['in_site_plate2_AUC_mean']:.4f} "
                   f"+- {row['in_site_plate2_AUC_sd']:.4f}"
                   if row["in_site_plate2_AUC_mean"] is not None else "n/a (plate 2 is in train)")
            print(f"  {tag:9s} {n_c:4d} compounds  cross-site AUC "
                  f"{row['cross_site_AUC_mean']:.4f} +- {row['cross_site_AUC_sd']:.4f} | "
                  f"in-site plate2 AUC {ins}  ({len(aucs)} reps)", flush=True)
    dest = os.path.join(REPORTS, f"21_stage12_train_size_curve_{args.scaling}.json")
    # Paired plate-level contrast between the smallest and the full pilot training set.
    # The plate is the unit: a rep-to-rep sd of 0.01-0.04 is not an independent sample, so
    # the trend is tested as a within-plate difference (Wilcoxon signed-rank over the 9
    # plates) plus a plate-level bootstrap CI of that difference.
    contrasts = {}
    from scipy.stats import wilcoxon
    for tag, d in per_plate.items():
        ks = sorted(d)
        if len(ks) < 2:
            continue
        diff = d[ks[0]] - d[ks[-1]]
        rb = np.random.default_rng(RANDOM_STATE)
        bs = [float(np.mean(diff[rb.integers(0, len(diff), len(diff))]))
              for _ in range(2000)]
        try:
            p = float(wilcoxon(d[ks[0]], d[ks[-1]], alternative="greater").pvalue)
        except ValueError:
            p = float("nan")
        contrasts[tag] = {"fewer_compounds": ks[0], "more_compounds": ks[-1],
                          "per_plate_AUC_fewer": [float(x) for x in d[ks[0]]],
                          "per_plate_AUC_more": [float(x) for x in d[ks[-1]]],
                          "mean_AUC_gain_from_fewer": float(np.mean(diff)),
                          "gain_95CI": [float(np.quantile(bs, 0.025)),
                                        float(np.quantile(bs, 0.975))],
                          "wilcoxon_p_fewer_gt_more": p,
                          "n_plates": int(len(diff))}
        print(f"  paired {tag}: {ks[0]} vs {ks[-1]} compounds -> "
              f"{np.mean(diff):+.4f} AUC CI [{contrasts[tag]['gain_95CI'][0]:+.4f},"
              f"{contrasts[tag]['gain_95CI'][1]:+.4f}] p={p:.4f} over {len(diff)} plates")
    pd.DataFrame(rows).to_csv(dest.replace(".json", ".csv"), index=False)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump({"scaling": args.scaling, "rows": rows, "paired_contrasts": contrasts,
                   "external_plate_ids": usable,
                   "external_AP_prevalence_floor": float(y_ext.mean())}, f, indent=1)
    print("wrote " + dest)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["fetch", "controls", "position", "retrieval",
                                     "evaluate", "diagnose", "trainsize"], default="fetch")
    ap.add_argument("--sets", default="meta,profiles")
    ap.add_argument("--plates", type=int, default=10)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--train-plate", default=PILOT_PLATES[0])
    ap.add_argument("--scaling", dest="scaling",
                    choices=list(SCALES), default="negcon_z")
    ap.add_argument("--out-tag", default="")
    a = ap.parse_args()
    {"fetch": stage_fetch, "controls": stage_controls, "position": stage_position,
     "retrieval": stage_retrieval,
     "evaluate": stage_evaluate, "diagnose": stage_diagnose,
     "trainsize": stage_trainsize}[a.stage](a)
    sys.exit(0)


if __name__ == "__main__":
    main()
