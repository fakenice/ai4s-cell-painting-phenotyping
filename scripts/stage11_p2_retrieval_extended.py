# -*- coding: utf-8 -*-
"""Stage 11 - P2: Deep-embedding coverage extension (BR00116992) + harder-task evaluation.

Part A  Deep coverage extension
  - 18 treated wells of plate BR00116992 downloaded from public S3 (f01 x 8 channels),
    merged with the existing 12 sites (6 wells) of BR00116991 -> 30 sites / 24 wells.
  - ResNet18-512 embeddings recomputed for all 30 sites with the Stage-8 protocol
    (ImageNet pretrained, ch1/ch4/ch2 RGB composite, well = mean of its sites).

Part B  Replicate retrieval on the extended shared well set (24 wells)
  - Same cosine protocol as P1: mean replicate AP / chance AP / pair AUC / MRR /
    median rank / recall@1/5/10, deep-512 vs manual-904 on the SAME wells.

Part C  Harder task 1 - trt-vs-trt pairwise compound discrimination
  - For the 7 compounds with 2 wells each (14 wells: 3 cross-plate + 4 in-plate pairs),
    pairwise leave-one-well-out logistic-regression AUC for each of the 21 compound
    pairs; report mean/min/max over pairs, deep-512 vs manual-904.

Part D  Harder task 2 - compound identity top-k
  - Multi-class compound identification on the same 14 wells (7 compounds): LOOCV
    top-1/top-5 accuracy, deep-512 vs manual-904.
  - Full-scope 904 reference: kNN compound identity on the 260 trt wells of BR00116992
    (top-1/5 accuracy over 256 compounds).
"""
import os, json
import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize, StandardScaler
from sklearn.metrics import average_precision_score, roc_auc_score, accuracy_score
from sklearn.linear_model import LogisticRegression

RANDOM_STATE = 42
BASE = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science"
DATA = os.path.join(BASE, "data")
REPO = os.path.join(BASE, "github_repo")
REPORTS = os.path.join(REPO, "reports")
NPZ = os.path.join(REPORTS, "19_stage11_p2_embeddings.npz")

WELL_COMPOUND_91 = {"A01": "gabapentin-enacarbil", "A02": "DMSO", "A03": "amlodipine",
                    "A04": "hexestrol", "A09": "DMSO", "A17": "DMSO"}
WELL_COMPOUND_92 = {"A01": "gabapentin-enacarbil", "A03": "amlodipine", "A04": "hexestrol",
                    "A05": "quinine", "A06": "LOXO-101", "A07": "brinzolamide",
                    "A08": "NS-11021", "A10": "GNF-5837", "A11": "apatinib",
                    "A12": "ethoxzolamide", "A21": "dexamethasone", "B02": "thiostrepton",
                    "B12": "BVT-948", "G05": "ME-0328", "J11": "ME-0328",
                    "L23": "thiostrepton", "O02": "dexamethasone", "O16": "BVT-948"}

FEAT_PREFIX = ("Cells_", "Cytoplasm_", "Nuclei_")


def well_to_site(w):
    return f"r{ord(w[0])-ord('A')+1:02d}c{int(w[1:]):02d}"


def load_profiles():
    plate_files = sorted(f for f in os.listdir(os.path.join(DATA, "profiles")) if f.endswith(".csv.gz"))
    return pd.concat([pd.read_csv(os.path.join(DATA, "profiles", f)) for f in plate_files], ignore_index=True)


def retrieval_metrics(X, groups):
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
            r1 = int(hits[0]) + 1
            rr_first.append(1.0 / r1)
            rank_first.append(r1)
        else:
            rr_first.append(0.0)
            rank_first.append(n)
        hit1.append(1 if y[order[0]] == 1 else 0)
        hit5.append(1 if y[order[:5]].sum() >= 1 else 0)
        hit10.append(1 if y[order[:10]].sum() >= 1 else 0)
    y_all = (groups[:, None] == groups[None, :]).astype(int)
    triu = np.triu_indices(n, k=1)
    pair_auc = roc_auc_score(y_all[triu], S[triu]) if np.unique(y_all[triu]).size > 1 else float("nan")
    return {"n": int(n), "n_queries_valid": int(valid.sum()),
            "mean_replicate_AP": float(np.mean(aps)) if aps else float("nan"),
            "chance_AP": float(np.mean(np.array(npos) / (n - 1))) if npos else float("nan"),
            "pair_AUC": float(pair_auc),
            "MRR": float(np.mean(rr_first)) if rr_first else float("nan"),
            "median_rank_first_hit": float(np.median(rank_first)) if rank_first else float("nan"),
            "recall_at_1": float(np.mean(hit1)) if hit1 else float("nan"),
            "recall_at_5": float(np.mean(hit5)) if hit5 else float("nan"),
            "recall_at_10": float(np.mean(hit10)) if hit10 else float("nan")}


def build_extended_well_table():
    rows = []
    for w, comp in WELL_COMPOUND_91.items():
        rows.append({"plate": "BR00116991", "well": w, "site": f"{well_to_site(w)}f01p01", "compound": comp})
    for w, comp in WELL_COMPOUND_92.items():
        rows.append({"plate": "BR00116992", "well": w, "site": f"{well_to_site(w)}f01p01", "compound": comp})
    return pd.DataFrame(rows)


def main():
    print("=" * 70)
    print("Stage 11 P2: deep coverage extension + harder-task evaluation")
    print("=" * 70)

    z = np.load(NPZ, allow_pickle=True)
    emb_site = dict(z["emb_site"].item())
    # key: deep_resnet18_512|<plate>|<site>
    site_keys = sorted(emb_site)
    meta = np.array([tuple(k.split("|")) for k in site_keys])
    plates, sites = meta[:, 1], meta[:, 2]
    print("total sites:", len(site_keys), "plates:", sorted(set(plates)))

    tbl = build_extended_well_table()
    well_id = [f"{r['plate']}|{r['well']}" for _, r in tbl.iterrows()]
    comps = tbl["compound"].values

    # --- deep well matrix (well = mean over its sites) ---
    def deep_well_matrix():
        Xw = []
        for _, r in tbl.iterrows():
            site = r["site"]
            ks = [k for k in site_keys if k.split("|")[1] == r["plate"] and k.split("|")[2] == site]
            assert ks, f"no embedding for {r['plate']}|{site}"
            Xw.append(np.mean([emb_site[k] for k in ks], axis=0))
        return np.vstack(Xw).astype(np.float32)

    Xdeep = deep_well_matrix()
    print("deep well matrix:", Xdeep.shape)

    # --- manual 904 well matrix (raw well means, mirror P0-4/P1 6-well protocol) ---
    prof = load_profiles()
    feat_cols = [c for c in prof.columns if c.startswith(FEAT_PREFIX)]
    assert len(feat_cols) == 904, f"unexpected feat count {len(feat_cols)}"
    X904w = []
    for _, r in tbl.iterrows():
        sub = prof[(prof["Metadata_Plate"] == r["plate"]) & (prof["Metadata_Well"] == r["well"])]
        assert len(sub) > 0, f"missing profile {r['plate']}|{r['well']}"
        X904w.append(sub[feat_cols].mean(0).values)
    X904 = np.vstack(X904w).astype(np.float32)
    print("904 well matrix:", X904.shape)

    rows = []
    for name, X in (("manual_904_features", X904), ("deep_resnet18_512", Xdeep)):
        r = retrieval_metrics(X, comps)
        rows.append({"task": "replicate_retrieval_24wells", "feature": name,
                     "mean_replicate_AP": r["mean_replicate_AP"], "chance_AP": r["chance_AP"],
                     "pair_AUC": r["pair_AUC"], "MRR": r["MRR"],
                     "median_rank_first_hit": r["median_rank_first_hit"],
                     "recall_at_1": r["recall_at_1"], "recall_at_5": r["recall_at_5"],
                     "recall_at_10": r["recall_at_10"],
                     "n_queries_valid": r["n_queries_valid"], "n": r["n"]})
        print(name, "24-well retrieval:", {k: v for k, v in r.items() if k not in ("n",)})

    # ---------- Part C: trt-vs-trt pairwise compound discrimination ----------
    pair_df = tbl[tbl["compound"] != "DMSO"].copy()
    cnt = pair_df["compound"].value_counts()
    multi = cnt[cnt >= 2].index.tolist()
    print("compounds with >=2 wells:", multi)
    p14 = pair_df[pair_df["compound"].isin(multi)].copy()
    Xd14 = Xdeep[p14.index.values]
    X904_14 = X904[p14.index.values]
    comp14 = p14["compound"].values

    def pairwise_auc(X, comps_, name):
        aucs, details = [], []
        uniq = sorted(set(comps_))
        for ai in range(len(uniq)):
            for bi in range(ai + 1, len(uniq)):
                idx = np.where((comps_ == uniq[ai]) | (comps_ == uniq[bi]))[0]
                y = (comps_[idx] == uniq[ai]).astype(int)
                Xp = X[idx]
                if len(idx) < 4 or np.unique(y).size < 2:
                    continue
                # LOOCV logistic regression
                prob = np.zeros(len(idx))
                for lo in range(len(idx)):
                    tr = np.ones(len(idx), dtype=bool); tr[lo] = False
                    clf = LogisticRegression(max_iter=2000, C=1.0, random_state=RANDOM_STATE)
                    try:
                        sc = StandardScaler().fit(Xp[tr])
                        clf.fit(sc.transform(Xp[tr]), y[tr])
                        prob[lo] = clf.predict_proba(sc.transform(Xp[lo:lo + 1]))[:, 1][0]
                    except Exception:
                        prob[lo] = 0.5
                auc = roc_auc_score(y, prob) if np.unique(y).size == 2 and np.unique(prob).size > 1 else float("nan")
                aucs.append(auc)
                details.append({"pair": f"{uniq[ai]}_vs_{uniq[bi]}", "auc": float(auc) if auc == auc else None})
        return {"feature": name, "n_pairs": len(aucs),
                "pairwise_trt_trt_auc_mean": float(np.nanmean(aucs)),
                "pairwise_trt_trt_auc_min": float(np.nanmin(aucs)),
                "pairwise_trt_trt_auc_max": float(np.nanmax(aucs))}, details

    for name, X in (("manual_904_features", X904_14), ("deep_resnet18_512", Xd14)):
        res, det = pairwise_auc(X, comp14, name)
        rows.append({"task": "harder_pairwise_trt_trt", **res})
        print(name, "pairwise:", res)

    # ---------- Part D: compound identity top-k (14 wells, 7 compounds, LOOCV) ----------
    def identity_topk(X, comps_, name, k=(1, 5)):
        comps_ = np.asarray(comps_)
        uniq = sorted(set(comps_))
        hits = {kk: 0 for kk in k}
        for lo in range(len(comps_)):
            tr = np.ones(len(comps_), dtype=bool); tr[lo] = False
            clf = LogisticRegression(max_iter=3000, C=1.0, random_state=RANDOM_STATE)
            sc = StandardScaler().fit(X[tr])
            clf.fit(sc.transform(X[tr]), comps_[tr])
            probs = clf.predict_proba(sc.transform(X[lo:lo + 1]))[0]
            order = np.argsort(probs)[::-1]
            top = [clf.classes_[i] for i in order]
            for kk in k:
                if comps_[lo] in top[:kk]:
                    hits[kk] += 1
        return {"feature": name, "n": len(comps_), "n_compounds": len(uniq),
                "identity_top1_acc": hits[1] / len(comps_),
                "identity_top5_acc": hits[5] / len(comps_)}

    for name, X in (("manual_904_features", X904_14), ("deep_resnet18_512", Xd14)):
        res = identity_topk(X, comp14, name)
        rows.append({"task": "harder_compound_identity_topk", **res})
        print(name, "identity:", res)

    # Full-scope 904 kNN compound identity on 260 trt wells of BR00116992
    sub92 = prof[(prof["Metadata_Plate"] == "BR00116992") & (prof["Metadata_pert_type"] == "trt")].copy()
    X92 = sub92[feat_cols].values.astype(np.float32)
    comp92 = sub92["Metadata_pert_iname"].values
    Xn = normalize(X92, norm="l2", axis=1)
    S = Xn @ Xn.T
    hit1 = hit5 = 0
    for i in range(len(comp92)):
        scores = S[i].copy(); scores[i] = -1e9
        order = np.argsort(scores)[::-1]
        if comp92[order[0]] == comp92[i]:
            hit1 += 1
        if comp92[i] in comp92[order[:5]]:
            hit5 += 1
    rows.append({"task": "full904_knn_compound_identity_260trt", "feature": "manual_904_features",
                 "n": len(comp92), "n_compounds": len(set(comp92)),
                 "identity_top1_acc": hit1 / len(comp92), "identity_top5_acc": hit5 / len(comp92)})
    print("full 260-trt 904 kNN identity:", hit1 / len(comp92), hit5 / len(comp92))

    out_csv = os.path.join(REPORTS, "19_stage11_p2_retrieval_extended_results.csv")
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print("saved:", out_csv)

    summary = {
        "p2_1_coverage": {"plate": "BR00116992", "new_wells_downloaded": 18,
                          "new_sites": 18, "total_sites": 30, "total_wells": 24,
                          "image_dir": os.path.join(DATA, "raw", "BR00116992"),
                          "n_tiff": len(os.listdir(os.path.join(DATA, "raw", "BR00116992"))),
                          "embedding_npz": NPZ},
        "p2_2_retrieval_extended": rows,
        "p1_6well_reference": "deep_resnet18_512 well6 mean_replicate_AP 0.7333 (P0-4); 904 well6 0.5083 (recomputed P1)",
        "harder_task_definition": "trt-vs-trt pairwise compound discrimination (LOOCV LR AUC over 7 compounds x 2 wells) + compound identity top-1/5 (same wells) + full-scope 904 kNN identity",
    }
    with open(os.path.join(REPORTS, "19_stage11_p2_retrieval_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("summary ->", os.path.join(REPORTS, "19_stage11_p2_retrieval_summary.json"))
    print("DONE.")


if __name__ == "__main__":
    main()
