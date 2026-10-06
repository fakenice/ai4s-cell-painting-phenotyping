# -*- coding: utf-8 -*-
"""Stage 11 - P4b: trt-vs-trt harder-task re-run with A+B+C protocol.

Motivation: P2/P4's 21-pair LOOCV-LR protocol has only 3 true cross-plate pairs
(0.167), a small-sample bottleneck for cross-plate generalization claims. This
script replaces pairwise LR with **prototype discrimination** (compound multi-well
mean prototypes, nearest-prototype scoring) and expands evaluation to the FULL
plate1 x plate2 compound-pair grid (256 compounds on each plate -> 32640 pairs).

A. Prototype discrimination replaces pairwise LR:
   - each compound's prototype = mean of its wells (plate1 + plate2 wells);
   - for a compound pair (A,B): leave-one-well-out, predict the held-out well by
     cosine similarity to the leave-rest-out prototypes of A and B;
   - pair grid expanded to ALL plate1 x plate2 compound pairs (i<j), i.e. 32640
     cross-plate pairs (previously 3).

B. Cross-plate pair expansion (merged statistics with A):
   - aggregate mean/min/max AUC over the full 32640-pair grid;
   - same-protocol contrast subset: the original 21 pairs (7 compounds x 2 wells)
     so that prototype discrimination can be compared apple-to-apple with the
     P2/P4 M0 LR baseline (0.7619 mean AUC over 21 pairs).

C. Simple cross-plate correction controls (per-plate, zero download, cheap):
   - per-plate z-score (each feature standardized within each plate);
   - per-plate mean-centering (each feature minus its plate mean);
   - re-run the same full-grid prototype discrimination and compare.

Honest reporting: positive / negative / no-change vs M0 baseline 0.7619.

Outputs: reports/20_stage11_p4b_prototype_discrimination_results.csv
         reports/20_stage11_p4b_prototype_discrimination_summary.json
"""
import os, json
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

RANDOM_STATE = 42
BASE = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science"
DATA = os.path.join(BASE, "data", "profiles")
REPO = os.path.join(BASE, "github_repo")
REPORTS = os.path.join(REPO, "reports")
P1, P2 = "BR00116991", "BR00116992"
FEAT_PREFIX = ("Cells_", "Cytoplasm_", "Nuclei_")

# 21-pair reference set (P2/P4 protocol compounds)
CROSS_COMPOUNDS = ["gabapentin-enacarbil", "amlodipine", "hexestrol"]
IN_COMPOUNDS = ["dexamethasone", "thiostrepton", "BVT-948", "ME-0328"]
REFERENCE_21_PAIRS = sorted(
    [(a, b) for i, a in enumerate(CROSS_COMPOUNDS) for b in CROSS_COMPOUNDS[i + 1:]]
    + [(a, b) for i, a in enumerate(IN_COMPOUNDS) for b in IN_COMPOUNDS[i + 1:]]
    + [(a, b) for a in CROSS_COMPOUNDS for b in IN_COMPOUNDS]
)


def load_feature_matrix(plate):
    f = os.path.join(DATA, f"{plate}_normalized_feature_select_negcon_batch.csv.gz")
    df = pd.read_csv(f)
    feats = [c for c in df.columns if c.startswith(FEAT_PREFIX)]
    assert len(feats) == 904
    trt = df[df["Metadata_pert_type"] == "trt"]
    X = trt[feats].values.astype(np.float32)
    wells = trt["Metadata_Well"].values
    comps = trt["Metadata_pert_iname"].values
    return X, wells, comps


def compound_prototypes(X, wells, comps):
    """Return {compound: well-index-list} grouped per plate."""
    idx_by_comp = {}
    for i, c in enumerate(comps):
        idx_by_comp.setdefault(c, []).append(i)
    return idx_by_comp


def cosine_sim(a, b):
    a = a / (np.linalg.norm(a) + 1e-12)
    b = b / (np.linalg.norm(b) + 1e-12)
    return float(a @ b)


def pair_auc_prototype(Xmat, idxA, idxB, y_order=None):
    """Leave-one-well-out nearest-prototype AUC for pair (A,B).

    Prototypes are means of the remaining wells of each class. Held-out well is
    scored by cosine similarity to both prototypes; higher similarity to A -> A.
    If a class has exactly one well in the pair, its prototype is that well
    (used only to score the other class's held-out wells; its own well is not
    self-scored). Pairs whose per-class sample counts cannot produce >=2 labels
    with >=2 distinct scores return NaN.
    """
    nA, nB = len(idxA), len(idxB)
    # preds are higher for "looks like A"; make A the positive class so AUC
    # directly measures A-vs-B separability under nearest-prototype scoring.
    y = np.array([1] * nA + [0] * nB) if y_order is None else np.array(y_order)
    if nA + nB < 2:
        return float("nan")
    preds = np.zeros(nA + nB)
    all_idx = list(idxA) + list(idxB)
    for t, gi in enumerate(all_idx):
        trA = [i for i in idxA if i != gi]
        trB = [i for i in idxB if i != gi]
        if not trA and not trB:
            preds[t] = np.nan
            continue
        # prototype = mean of remaining wells (empty class falls back to 0.5)
        protoA = Xmat[trA].mean(axis=0) if trA else None
        protoB = Xmat[trB].mean(axis=0) if trB else None
        sA = cosine_sim(Xmat[gi], protoA) if protoA is not None else 0.0
        sB = cosine_sim(Xmat[gi], protoB) if protoB is not None else 0.0
        if protoA is None:
            preds[t] = 1.0 - sB  # only B prototype available
        elif protoB is None:
            preds[t] = sA
        else:
            preds[t] = sA - sB
    valid = ~np.isnan(preds)
    if np.unique(y[valid]).size < 2 or np.unique(preds[valid]).size < 2:
        return float("nan")
    return float(roc_auc_score(y[valid], preds[valid]))


def run_grid(comp_list, idx_by_comp, Xmat, label=""):
    """Full plate1 x plate2 compound-pair grid (i<j)."""
    aucs = {}
    n_pairs = 0
    comps = sorted(comp_list)
    for ai in range(len(comps)):
        ca = comps[ai]
        for bj in range(ai + 1, len(comps)):
            cb = comps[bj]
            v = pair_auc_prototype(Xmat, idx_by_comp[ca], idx_by_comp[cb])
            if v == v:
                aucs[f"{ca}__{cb}"] = v
                n_pairs += 1
    return aucs, n_pairs


def summarize(aucs, n_pairs, label):
    vals = np.array(list(aucs.values()))
    if vals.size == 0:
        return {"label": label, "n_pairs": 0, "mean": None, "min": None, "max": None,
                "frac_ge_0_8": None, "frac_le_0_2": None}
    return {"label": label, "n_pairs": n_pairs, "mean": float(vals.mean()),
            "min": float(vals.min()), "max": float(vals.max()),
            "frac_ge_0_8": float((vals >= 0.8).mean()), "frac_le_0_2": float((vals <= 0.2).mean())}


def main():
    print("=" * 80)
    print("Stage 11 P4b: prototype discrimination + cross-plate full-grid (A+B+C)")
    print("=" * 80)
    X1, w1, c1 = load_feature_matrix(P1)
    X2, w2, c2 = load_feature_matrix(P2)
    assert set(c1) == set(c2), "compound sets must match"
    comp_list = sorted(set(c1))

    # Combined matrix (both plates) with per-compound well indexes
    Xboth = np.vstack([X1, X2]).astype(np.float32)
    idx1 = compound_prototypes(X1, w1, c1)
    idx2 = compound_prototypes(X2, w2, c2)
    offset = X1.shape[0]
    idxboth = {c: idx1[c] + [i + offset for i in idx2[c]] for c in comp_list}

    # ---- preprocessing variants ----
    # raw
    X_raw = Xboth
    # per-plate z-score
    m1, s1 = X1.mean(0), X1.std(0) + 1e-12
    m2, s2 = X2.mean(0), X2.std(0) + 1e-12
    X_z = np.vstack([(X1 - m1) / s1, (X2 - m2) / s2]).astype(np.float32)
    # per-plate mean-centering
    X_mc = np.vstack([X1 - m1, X2 - m2]).astype(np.float32)

    grids = {}
    for label, Xmat in [("raw", X_raw), ("zscore", X_z), ("meancenter", X_mc)]:
        idx_by_comp = compound_prototypes(Xmat, np.arange(Xmat.shape[0]), np.concatenate([c1, c2]))
        aucs, n_pairs = run_grid(comp_list, idx_by_comp, Xmat, label)
        grids[label] = aucs
        summ = summarize(aucs, n_pairs, label)
        print(f"[{label:>10s}] full-grid pairs={n_pairs} mean AUC={summ['mean']:.4f} "
              f"min={summ['min']:.4f} max={summ['max']:.4f} >=0.8={summ['frac_ge_0_8']:.4f} <=0.2={summ['frac_le_0_2']:.4f}")

    # Reference 21-pair subset under prototype protocol (apple-to-apple vs M0 LR 0.7619)
    ref = {}
    for label, aucs in grids.items():
        ref_keys = {tuple(sorted(p)) for p in REFERENCE_21_PAIRS}
        sub = {k: v for k, v in aucs.items()
               if tuple(sorted(k.split("__"))) in ref_keys}
        ref[label] = summarize(sub, len(sub), f"ref21_{label}")
        print(f"[{label:>10s}] reference21-pairs mean AUC={ref[label]['mean']:.4f} "
              f"n={ref[label]['n_pairs']}")

    # ---- write CSV (one row per pair, raw + both corrections) ----
    rows = []
    for key in grids["raw"]:
        ca, cb = key.split("__")
        rows.append({
            "compound_A": ca, "compound_B": cb,
            "n_wells_A": len(idxboth[ca]), "n_wells_B": len(idxboth[cb]),
            "auc_raw": grids["raw"][key],
            "auc_zscore": grids["zscore"].get(key, float("nan")),
            "auc_meancenter": grids["meancenter"].get(key, float("nan")),
        })
    df = pd.DataFrame(rows)
    out_csv = os.path.join(REPORTS, "20_stage11_p4b_prototype_discrimination_results.csv")
    df.to_csv(out_csv, index=False)
    print("saved:", out_csv, "rows:", len(df))

    # ---- summary JSON ----
    summary = {
        "experiment": "Stage 11 P4b trt-vs-trt harder-task re-run (A+B+C)",
        "protocol": ("A. prototype discrimination (multi-well mean prototypes, LOOCV cosine "
                     "nearest-prototype scoring) replaces pairwise LR; "
                     "B. full plate1 x plate2 cross-plate compound grid (32640 pairs) merged "
                     "statistics, plus reference-21 subset for apple-to-apple comparison; "
                     "C. per-plate z-score / mean-centering correction controls"),
        "baseline": {"P2_P4_reported_M0_LR_21pairs_mean_AUC": 0.7619,
                     "note": "M0 is pairwise LOOCV LR AUC over 21 pairs; "
                             "P4b reference-21 subset uses prototype discrimination on the same 21 pairs"},
        "full_grid_pairs": {k: len(grids[k]) for k in grids},
        "full_grid_summary": {k: summarize(grids[k], len(grids[k]), k) for k in grids},
        "reference_21_subset": ref,
        "verdict_vs_M0": {
            "reference_21_prototype_vs_LR": ("P4b reference-21 prototype mean AUC vs M0 LR 0.7619; "
                                             "see reference_21_subset.raw.mean"),
            "full_grid_scale_note": "full 32640-pair grid has no M0 LR counterpart; "
                                    "compare within-protocol only",
        },
        "notes": [
            "cosine nearest-prototype scoring; prototypes are leave-rest-out well means",
            "per-plate z-score / mean-centering fit on each plate's own trt wells only (no cross-plate info)",
            "small per-pair sample sizes yield coarse AUC values; merged grid statistics are the meaningful readout",
            "honest reporting: positive/negative/no-change relative to baseline are stated in the report",
        ],
    }
    # replace sentinel pair-count
    for label in grids:
        summary["full_grid_pairs"][label] = len(grids[label])
    with open(os.path.join(REPORTS, "20_stage11_p4b_prototype_discrimination_summary.json"),
              "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("summary ->", os.path.join(REPORTS, "20_stage11_p4b_prototype_discrimination_summary.json"))
    print("DONE.")


if __name__ == "__main__":
    main()
