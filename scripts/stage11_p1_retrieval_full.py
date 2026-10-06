# -*- coding: utf-8 -*-
"""Stage 11 - P1-1: Full-scope replicate retrieval verification (deep embeddings vs manual 904).

Goal
----
Verify the P0-4 retrieval track switch on the FULL 648-well scope where possible,
and honestly report the deep-embedding coverage limitation:

  - Deep image embeddings exist ONLY for the 12 sites / 6 wells of plate BR00116991
    (treated A01/A03/A04 + DMSO A02/A09/A17); they CANNOT be extended to the full
    648-well maskA because the other 642 wells have no local images.
    => Full-scope deep-embedding retrieval is NOT feasible; reported as limitation.
  - Full-scope (648-well maskA) replicate retrieval is therefore computed with the
    manual 904-feature profiles, under the SAME cosine protocol as Stage 10, plus
    rank metrics (MRR, median rank, recall@1/5/10) that Stage 10 did not report.
  - Head-to-head deep-vs-manual comparison is done on the 6-well shared scope
    (apples-to-apples, same protocol, both with rank metrics), reusing cached
    embeddings from reports/19_stage11_p0_embeddings.npz.

Protocol (mirrors stage10_retrieval.well_ap_metrics and stage11_p0_retrieval):
  - features L2-normalized; cosine similarity; query well vs all other wells
  - AP against same-compound wells; chance AP = mean positive fraction
  - pair AUC = same-vs-different compound pairwise AUC
  - rank metrics: MRR (reciprocal rank of first hit), median rank of first hit,
    recall@1/5/10 (fraction of queries with >=1 hit in top-k)
"""
import os, json
import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize
from sklearn.metrics import average_precision_score, roc_auc_score

RANDOM_STATE = 42
BASE = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science"
DATA = os.path.join(BASE, "data")
REPO = os.path.join(BASE, "github_repo")
REPORTS = os.path.join(REPO, "reports")

WELL_COMPOUND = {"A01": "gabapentin-enacarbil", "A02": "DMSO", "A03": "amlodipine",
                 "A04": "hexestrol", "A09": "DMSO", "A17": "DMSO"}
SITE_WELL = {"r01c01": "A01", "r01c03": "A03", "r01c04": "A04",
             "r01c02": "A02", "r01c09": "A09", "r01c17": "A17"}


def load_full_profiles():
    plate_files = sorted(f for f in os.listdir(os.path.join(DATA, "profiles")) if f.endswith(".csv.gz"))
    frames = [pd.read_csv(os.path.join(DATA, "profiles", f)) for f in plate_files]
    return pd.concat(frames, ignore_index=True)


def retrieval_metrics(X, groups):
    """Cosine same-group replicate retrieval: AP + chance + pair AUC + rank metrics."""
    Xn = normalize(X, norm="l2", axis=1)
    S = Xn @ Xn.T
    n = len(groups)
    groups = np.asarray(groups)
    aps, npos, rr_first, rank_first, hit1, hit5, hit10 = [], [], [], [], [], [], []
    valid = np.zeros(n, dtype=bool)
    for i in range(n):
        scores = S[i].copy()
        scores[i] = -1e9
        y = (groups == groups[i]).astype(int)
        y[i] = 0
        if y.sum() == 0:
            continue
        valid[i] = True
        aps.append(average_precision_score(y, scores))
        npos.append(int(y.sum()))
        order = np.argsort(scores)[::-1]
        hits = np.where(y[order] == 1)[0]
        if len(hits):
            r1 = int(hits[0]) + 1  # 1-based rank of first hit
            rr_first.append(1.0 / r1)
            rank_first.append(r1)
        else:
            rr_first.append(0.0)
            rank_first.append(n)  # no hit: treat as worst rank n
        hit1.append(1 if y[order[0]] == 1 else 0)
        hit5.append(1 if y[order[:5]].sum() >= 1 else 0)
        hit10.append(1 if y[order[:10]].sum() >= 1 else 0)
    mean_ap = float(np.mean(aps)) if valid.any() else float("nan")
    mean_chance = float(np.mean(np.array(npos) / (n - 1))) if valid.any() else float("nan")
    y_all = (groups[:, None] == groups[None, :]).astype(int)
    triu = np.triu_indices(n, k=1)
    pair_auc = roc_auc_score(y_all[triu], S[triu]) if np.unique(y_all[triu]).size > 1 else float("nan")
    return {
        "n": int(n), "n_queries_valid": int(valid.sum()),
        "mean_replicate_AP": float(mean_ap), "chance_AP": float(mean_chance),
        "pair_AUC": float(pair_auc),
        "MRR": float(np.mean(rr_first)) if rr_first else float("nan"),
        "median_rank_first_hit": float(np.median(rank_first)) if rank_first else float("nan"),
        "recall_at_1": float(np.mean(hit1)) if hit1 else float("nan"),
        "recall_at_5": float(np.mean(hit5)) if hit5 else float("nan"),
        "recall_at_10": float(np.mean(hit10)) if hit10 else float("nan"),
    }


def main():
    prof = load_full_profiles()
    feat_cols = [c for c in prof.columns if not c.startswith("Metadata")]
    compound = prof.dropna(subset=["Metadata_pert_iname"]).copy()
    scaler_full = __import__("sklearn.preprocessing", fromlist=["StandardScaler"]).StandardScaler().fit(
        compound.groupby("Metadata_pert_iname")[feat_cols].mean().values)
    X_well = scaler_full.transform(compound[feat_cols].values)

    trt_mask = (compound["Metadata_pert_type"].values == "trt")
    dmso_mask = (compound["Metadata_pert_iname"].values == "DMSO")
    maskA = trt_mask | dmso_mask
    XA = X_well[maskA]
    namesA = compound.loc[maskA, "Metadata_pert_iname"].values
    print(f"maskA wells={maskA.sum()} unique compounds={compound.loc[maskA,'Metadata_pert_iname'].nunique()}")

    # --- Full-scope 904 retrieval (648 wells, maskA) ---
    full904 = retrieval_metrics(XA, namesA)
    print("FULL 648-well 904:", full904)

    # --- 6-well shared scope: deep embeddings + 904 ---
    NPZ = os.path.join(REPORTS, "19_stage11_p0_embeddings.npz")
    if not os.path.exists(NPZ):
        raise FileNotFoundError(f"missing cached embeddings: {NPZ}")
    z = np.load(NPZ, allow_pickle=True)
    emb_site = dict(z["emb_site"].item())
    ok = dict(z["ok"].item())
    SITES = sorted(set(k.split("|")[1] for k in emb_site))
    site_to_well = {s[:6]: SITE_WELL[s[:6]] for s in SITES}
    well_of = np.array([site_to_well[s[:6]] for s in SITES])
    print("sites:", len(SITES), "wells:", sorted(set(well_of)))

    prof6 = prof[(prof["Metadata_Plate"] == "BR00116991") & (prof["Metadata_Well"].isin(sorted(WELL_COMPOUND)))]
    well_feat6 = {w: prof6[prof6["Metadata_Well"] == w][feat_cols].mean(0).values for w in sorted(WELL_COMPOUND)}
    X904_6 = np.vstack([well_feat6[w] for w in sorted(WELL_COMPOUND)])  # raw means, mirror P0-4 (no standardization)
    comps6 = np.array([WELL_COMPOUND[w] for w in sorted(WELL_COMPOUND)])
    r904_6 = retrieval_metrics(X904_6, comps6)
    print("6-well 904:", r904_6)

    rows = []
    rows.append({"scope": "full_648_wells", "feature": "manual_904_features",
                 "mean_replicate_AP": full904["mean_replicate_AP"], "chance_AP": full904["chance_AP"],
                 "pair_AUC": full904["pair_AUC"], "MRR": full904["MRR"],
                 "median_rank_first_hit": full904["median_rank_first_hit"],
                 "recall_at_1": full904["recall_at_1"], "recall_at_5": full904["recall_at_5"],
                 "recall_at_10": full904["recall_at_10"],
                 "n_queries_valid": full904["n_queries_valid"], "n": full904["n"]})
    rows.append({"scope": "6_wells_shared", "feature": "manual_904_features",
                 "mean_replicate_AP": r904_6["mean_replicate_AP"], "chance_AP": r904_6["chance_AP"],
                 "pair_AUC": r904_6["pair_AUC"], "MRR": r904_6["MRR"],
                 "median_rank_first_hit": r904_6["median_rank_first_hit"],
                 "recall_at_1": r904_6["recall_at_1"], "recall_at_5": r904_6["recall_at_5"],
                 "recall_at_10": r904_6["recall_at_10"],
                 "n_queries_valid": r904_6["n_queries_valid"], "n": r904_6["n"]})

    for name in ["deep_resnet18_512", "deep_dinov2_vits14_384", "deep_dinov2_vitb14_768",
                 "deep_openphenom_vits16_384_rgb3", "deep_openphenom_vits16_384_ch8"]:
        if not ok.get(name, True):
            print("skip (unavailable):", name)
            continue
        Es = np.vstack([emb_site[f"{name}|{s}"] for s in SITES])
        Ew = np.vstack([Es[well_of == w].mean(0) for w in sorted(WELL_COMPOUND)])
        r = retrieval_metrics(Ew, comps6)
        rows.append({"scope": "6_wells_shared", "feature": name,
                     "mean_replicate_AP": r["mean_replicate_AP"], "chance_AP": r["chance_AP"],
                     "pair_AUC": r["pair_AUC"], "MRR": r["MRR"],
                     "median_rank_first_hit": r["median_rank_first_hit"],
                     "recall_at_1": r["recall_at_1"], "recall_at_5": r["recall_at_5"],
                     "recall_at_10": r["recall_at_10"],
                     "n_queries_valid": r["n_queries_valid"], "n": r["n"]})
        print(name, "6-well:", r)

    out_csv = os.path.join(REPORTS, "19_stage11_p1_retrieval_full_results.csv")
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print("saved:", out_csv)

    summary = {
        "p1_1_retrieval_full": {
            "coverage_limitation": (
                "Deep image embeddings exist for only 12 sites / 6 wells (plate BR00116991: "
                "treated A01/A03/A04, DMSO A02/A09/A17). The remaining 642 wells of maskA "
                "have no local images, so full-scope (648-well) deep-embedding retrieval is "
                "NOT feasible; reported as a limitation. Full-scope retrieval uses manual "
                "904 profiles under the same cosine protocol as Stage 10."
            ),
            "rows": rows,
            "stage10_reference": {"scope": "full_648_wells", "mean_replicate_AP": 0.2451,
                                  "chance_AP": 0.0401, "pair_AUC": 0.6335,
                                  "note": "Stage 10 retrieval (18_stage10_retrieval_results.csv), no rank metrics reported then"},
        }
    }
    with open(os.path.join(REPORTS, "19_stage11_p1_retrieval_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("DONE.")


if __name__ == "__main__":
    main()
