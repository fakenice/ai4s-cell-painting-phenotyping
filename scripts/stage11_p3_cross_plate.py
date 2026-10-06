# -*- coding: utf-8 -*-
"""Stage 11 - P3: Cross-plate generalization validation (BR00116991 train / BR00116992 test).

Uses ONLY already-downloaded data (zero new downloads):
  - 904-feature well profiles: data/profiles/BR00116991_*, BR00116992_* (384 wells each)
  - deep ResNet18 512-d embeddings: reports/19_stage11_p2_embeddings.npz (30 sites / 24 wells)

Part A  trt-vs-DMSO cross-plate classification
  - Train: BR00116991 (260 trt vs 64 DMSO, strict; also vs 124 control, broad)
  - Test : BR00116992 (same label split) -> cross-plate AUC / AP
  - Same-plate baselines: 5-fold CV within BR00116991 and within BR00116992
  - Model: StandardScaler + LogisticRegression on 904 features (protocol-consistent)

Part B  trt-vs-trt cross-plate discrimination / retrieval
  - B1. Cross-plate same-compound retrieval, cosine on 904 (260x260 wells, query
        BR00116992 -> library BR00116991 and vice versa); same-plate reference:
        in-plate duplicates within BR00116992 (4 compounds x 2 wells).
  - B1-deep. 24-well subset (3 cross-plate compounds, 6 wells): 904 vs deep 512.
  - B2. Cross-plate compound identity top-1/5: LR 256-class trained on BR00116991,
        tested on BR00116992 (260 wells); kNN cosine version too.
        Same-plate LOOCV identity is not computable (1 replicate/compound), noted.
  - B3. Cross-plate prototype discrimination: 100 compound pairs (seed 42),
        BR00116991 wells as prototypes, BR00116992 wells as test -> mean AUC and
        sign-accuracy. Reference: P2 same-set LOOCV LR AUC 0.7619 (21 pairs, mixed
        plate) is reported for context but has a different protocol.

Outputs: reports/20_stage11_p3_cross_plate_results.csv
         reports/20_stage11_p3_cross_plate_summary.json
"""
import os, json
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, normalize
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, average_precision_score, accuracy_score

RANDOM_STATE = 42
BASE = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science"
DATA = os.path.join(BASE, "data")
REPO = os.path.join(BASE, "github_repo")
REPORTS = os.path.join(REPO, "reports")
NPZ = os.path.join(REPORTS, "19_stage11_p2_embeddings.npz")
P1 = "BR00116991"
P2 = "BR00116992"

FEAT_PREFIX = ("Cells_", "Cytoplasm_", "Nuclei_")


def load_plate(plate):
    f = os.path.join(DATA, "profiles", f"{plate}_normalized_feature_select_negcon_batch.csv.gz")
    df = pd.read_csv(f)
    feats = [c for c in df.columns if c.startswith(FEAT_PREFIX)]
    return df, feats


def cv_binary(X, y, n_splits=5):
    """Stratified 5-fold CV logistic regression -> mean AUC / AP."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    aucs, aps = [], []
    for tr, te in skf.split(X, y):
        sc = StandardScaler().fit(X[tr])
        clf = LogisticRegression(max_iter=2000, C=1.0, random_state=RANDOM_STATE)
        clf.fit(sc.transform(X[tr]), y[tr])
        p = clf.predict_proba(sc.transform(X[te]))[:, 1]
        if np.unique(y[te]).size > 1:
            aucs.append(roc_auc_score(y[te], p))
            aps.append(average_precision_score(y[te], p))
    return float(np.mean(aucs)), float(np.mean(aps))


def train_test_binary(Xtr, ytr, Xte, yte):
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(max_iter=2000, C=1.0, random_state=RANDOM_STATE)
    clf.fit(sc.transform(Xtr), ytr)
    p = clf.predict_proba(sc.transform(Xte))[:, 1]
    auc = roc_auc_score(yte, p) if np.unique(yte).size > 1 else float("nan")
    ap = average_precision_score(yte, p) if np.unique(yte).size > 1 else float("nan")
    return float(auc), float(ap)


def retrieval_oneway(Xq, Xlib, q_comp, lib_comp):
    """Query Xq -> library Xlib (cosine). q_comp[i] == lib_comp[j] => positive."""
    q_comp = np.asarray(q_comp, dtype=object)
    lib_comp = np.asarray(lib_comp, dtype=object)
    S = normalize(Xq, norm="l2", axis=1) @ normalize(Xlib, norm="l2", axis=1).T
    n = len(q_comp)
    aps, ranks, mrrs, hit1, hit5, hit10 = [], [], [], [], [], []
    n_valid = 0
    for i in range(n):
        scores = S[i]
        y = (lib_comp == q_comp[i]).astype(int)
        if y.sum() == 0:
            continue
        n_valid += 1
        aps.append(average_precision_score(y, scores))
        order = np.argsort(scores)[::-1]
        hits = np.where(y[order] == 1)[0]
        r1 = int(hits[0]) + 1 if len(hits) else n
        ranks.append(r1)
        mrrs.append(1.0 / r1)
        hit1.append(1 if y[order[0]] == 1 else 0)
        hit5.append(1 if y[order[:5]].sum() >= 1 else 0)
        hit10.append(1 if y[order[:10]].sum() >= 1 else 0)
    y_all = (q_comp[:, None] == lib_comp[None, :]).astype(int)
    pair_auc = roc_auc_score(y_all.ravel(), S.ravel()) if np.unique(y_all).size > 1 else float("nan")
    return {"n_queries": n, "n_valid": n_valid, "mean_AP": float(np.mean(aps)),
            "pair_AUC": float(pair_auc), "MRR": float(np.mean(mrrs)),
            "median_rank_first_hit": float(np.median(ranks)) if ranks else float("nan"),
            "recall_at_1": float(np.mean(hit1)), "recall_at_5": float(np.mean(hit5)),
            "recall_at_10": float(np.mean(hit10))}


def well_to_site(w):
    return f"r{ord(w[0])-ord('A')+1:02d}c{int(w[1:]):02d}"


def main():
    print("=" * 70)
    print("Stage 11 P3: cross-plate generalization validation")
    print("=" * 70)
    rows = []

    df1, feats = load_plate(P1)
    df2, _ = load_plate(P2)
    assert len(feats) == 904, len(feats)
    F = feats

    def trt_dmso(df, plate):
        d = df[df["Metadata_Plate"] == plate]
        trt = d[d["Metadata_pert_type"] == "trt"]
        dmso = d[d["Metadata_pert_iname"] == "DMSO"]
        ctrl = d[d["Metadata_pert_type"] == "control"]
        return trt, dmso, ctrl

    # ---------- Part A: trt-vs-DMSO cross-plate ----------
    for label, neg_fn in [("strict_DMSO", lambda trt, dmso, ctrl: dmso),
                          ("broad_control", lambda trt, dmso, ctrl: ctrl)]:
        trt1, dmso1, ctrl1 = trt_dmso(df1, P1)
        trt2, dmso2, ctrl2 = trt_dmso(df2, P2)
        neg1, neg2 = neg_fn(trt1, dmso1, ctrl1), neg_fn(trt2, dmso2, ctrl2)
        Xtr = np.vstack([trt1[F].values, neg1[F].values]).astype(np.float32)
        ytr = np.concatenate([np.ones(len(trt1)), np.zeros(len(neg1))])
        Xte = np.vstack([trt2[F].values, neg2[F].values]).astype(np.float32)
        yte = np.concatenate([np.ones(len(trt2)), np.zeros(len(neg2))])
        cross_auc, cross_ap = train_test_binary(Xtr, ytr, Xte, yte)
        auc1, ap1 = cv_binary(Xtr, ytr)
        auc2, ap2 = cv_binary(Xte, yte)
        r = {"task": "cross_plate_trt_vs_dmso", "label_split": label,
             "train_plate": P1, "test_plate": P2,
             "n_train_pos": int(ytr.sum()), "n_train_neg": int((ytr == 0).sum()),
             "n_test_pos": int(yte.sum()), "n_test_neg": int((yte == 0).sum()),
             "cross_plate_AUC": cross_auc, "cross_plate_AP": cross_ap,
             "within_p1_5fold_AUC": auc1, "within_p1_5fold_AP": ap1,
             "within_p2_5fold_AUC": auc2, "within_p2_5fold_AP": ap2}
        rows.append(r)
        print(r)

    # ---------- Part B1: cross-plate same-compound retrieval (904, full 260 wells) ----------
    trt1 = df1[(df1["Metadata_Plate"] == P1) & (df1["Metadata_pert_type"] == "trt")].copy()
    trt2 = df2[(df2["Metadata_Plate"] == P2) & (df2["Metadata_pert_type"] == "trt")].copy()
    X1 = trt1[F].values.astype(np.float32)
    X2 = trt2[F].values.astype(np.float32)
    c1 = np.asarray(trt1["Metadata_pert_iname"].values, dtype=object)
    c2 = np.asarray(trt2["Metadata_pert_iname"].values, dtype=object)
    assert len(X1) == len(X2) == 260 and set(c1) == set(c2)

    for tag, Xq, Xlib, qc, lc in [("p2_query_p1_lib", X2, X1, c2, c1),
                                  ("p1_query_p2_lib", X1, X2, c1, c2)]:
        r = retrieval_oneway(Xq, Xlib, qc, lc)
        rows.append({"task": "cross_plate_same_compound_retrieval_904_260wells", "direction": tag, **r})
        print(tag, r)

    # Same-plate reference: in-plate duplicates inside BR00116992 (4 compounds x 2 wells)
    cnt2 = pd.Series(c2).value_counts()
    dup2 = cnt2[cnt2 >= 2].index.tolist()
    sub2 = trt2[trt2["Metadata_pert_iname"].isin(dup2)]
    r_in = retrieval_oneway(sub2[F].values.astype(np.float32), sub2[F].values.astype(np.float32),
                            sub2["Metadata_pert_iname"].values, sub2["Metadata_pert_iname"].values)
    rows.append({"task": "in_plate_same_compound_retrieval_904_8wells", "direction": "p2_internal",
                 "n_compounds": len(dup2), **r_in})
    print("in-plate p2 8 wells:", r_in)

    # ---------- Part B1-deep: 24-well subset (3 cross-plate compounds) ----------
    well_comp_91 = {"A01": "gabapentin-enacarbil", "A02": "DMSO", "A03": "amlodipine",
                    "A04": "hexestrol", "A09": "DMSO", "A17": "DMSO"}
    well_comp_92 = {"A01": "gabapentin-enacarbil", "A03": "amlodipine", "A04": "hexestrol",
                    "A05": "quinine", "A06": "LOXO-101", "A07": "brinzolamide",
                    "A08": "NS-11021", "A10": "GNF-5837", "A11": "apatinib",
                    "A12": "ethoxzolamide", "A21": "dexamethasone", "B02": "thiostrepton",
                    "B12": "BVT-948", "G05": "ME-0328", "J11": "ME-0328",
                    "L23": "thiostrepton", "O02": "dexamethasone", "O16": "BVT-948"}
    cross_compounds = ["gabapentin-enacarbil", "amlodipine", "hexestrol"]

    z = np.load(NPZ, allow_pickle=True)
    emb_site = dict(z["emb_site"].item())
    site_keys = sorted(emb_site)

    def deep_well(plate, well):
        site = f"{well_to_site(well)}f01p01"
        ks = [k for k in site_keys if k.split("|")[1] == plate and k.split("|")[2] == site]
        assert ks, f"no deep embedding {plate}|{well}"
        return np.mean([emb_site[k] for k in ks], axis=0)

    def build_well_matrix(plates_wells):
        Xd, X9, cc = [], [], []
        for plate, well in plates_wells:
            comp = well_comp_91[well] if plate == P1 else well_comp_92[well]
            sub = df1[(df1["Metadata_Plate"] == P1) & (df1["Metadata_Well"] == well)] if plate == P1 \
                else df2[(df2["Metadata_Plate"] == P2) & (df2["Metadata_Well"] == well)]
            X9.append(sub[F].mean(axis=0).values)
            Xd.append(deep_well(plate, well))
            cc.append(comp)
        return np.vstack(Xd).astype(np.float32), np.vstack(X9).astype(np.float32), np.array(cc)

    cross_wells = [(P1, w) for w in well_comp_91 if well_comp_91[w] in cross_compounds] + \
                  [(P2, w) for w in well_comp_92 if well_comp_92[w] in cross_compounds]
    full_wells = [(P1, w) for w in well_comp_91] + [(P2, w) for w in well_comp_92]
    assert len(full_wells) == 24

    def retrieval_cross24(X, wells):
        """P2-consistent protocol: query the 6 cross-plate wells against the full
        24-well library, excluding the query well itself."""
        S = normalize(X, norm="l2", axis=1) @ normalize(X, norm="l2", axis=1).T
        comps = np.array([well_comp_91[w] if p == P1 else well_comp_92[w] for p, w in wells], dtype=object)
        aps, nq = [], 0
        for i in range(len(wells)):
            if wells[i] not in cross_wells:
                continue
            nq += 1
            mask = np.ones(len(wells), dtype=bool)
            mask[i] = False  # exclude self well
            y = ((comps == comps[i]) & mask).astype(int)
            if y.sum() == 0:
                aps.append(0.0)
                continue
            aps.append(average_precision_score(y, S[i]))
        return float(np.mean(aps)), nq

    Xd24, X924, c24 = build_well_matrix(full_wells)
    Xd6, X96, c6 = build_well_matrix(cross_wells)
    idx_p1 = np.array([pl == P1 for pl, _ in cross_wells])
    idx_p2 = ~idx_p1
    for tag, X in [("manual_904", X924), ("deep_resnet18_512", Xd24)]:
        ap6, nq = retrieval_cross24(X, full_wells)
        rows.append({"task": "cross_plate_same_compound_retrieval_24well_full_library",
                     "feature": tag, "direction": "6_cross_queries_vs_24well_lib",
                     "n_queries": nq, "mean_AP": ap6})
        print("24w full-lib cross-plate", tag, "mean_AP:", ap6)
    # one-way 3-query view (query plate2 -> library plate1 only)
    for tag, X in [("manual_904", X96), ("deep_resnet18_512", Xd6)]:
        r1 = retrieval_oneway(X[idx_p2], X[idx_p1], c6[idx_p2], c6[idx_p1])
        rows.append({"task": "cross_plate_same_compound_retrieval_24well_subset",
                     "feature": tag, "direction": "p2_query_p1_lib_3wells", **r1})
        print("24w subset one-way", tag, r1["mean_AP"])

    # ---------- Part B2: cross-plate compound identity top-1/5 ----------
    sc = StandardScaler().fit(X1)
    clf = LogisticRegression(max_iter=3000, C=1.0, random_state=RANDOM_STATE)
    clf.fit(sc.transform(X1), c1)
    probs = clf.predict_proba(sc.transform(X2))
    top1 = top5 = 0
    for i in range(len(c2)):
        order = np.argsort(probs[i])[::-1]
        top = [clf.classes_[j] for j in order]
        if c2[i] in top[:1]:
            top1 += 1
        if c2[i] in top[:5]:
            top5 += 1
    rows.append({"task": "cross_plate_compound_identity_topk", "method": "LR_256class",
                 "train_plate": P1, "test_plate": P2, "n_test": len(c2), "n_compounds": len(set(c1)),
                 "top1_acc": top1 / len(c2), "top5_acc": top5 / len(c2)})
    print("identity LR:", top1 / len(c2), top5 / len(c2))

    S21 = normalize(X2, norm="l2", axis=1) @ normalize(X1, norm="l2", axis=1).T
    hit1 = hit5 = 0
    for i in range(len(c2)):
        order = np.argsort(S21[i])[::-1]
        libc = c1[order]
        if c2[i] == libc[0]:
            hit1 += 1
        if c2[i] in libc[:5]:
            hit5 += 1
    rows.append({"task": "cross_plate_compound_identity_topk", "method": "kNN_cosine",
                 "train_plate": P1, "test_plate": P2, "n_test": len(c2), "n_compounds": len(set(c1)),
                 "top1_acc": hit1 / len(c2), "top5_acc": hit5 / len(c2)})
    print("identity kNN:", hit1 / len(c2), hit5 / len(c2))

    # ---------- Part B3: cross-plate prototype discrimination (100 pairs) ----------
    rng = np.random.default_rng(RANDOM_STATE)
    uniq = sorted(set(c1))
    pairs = []
    while len(pairs) < 100:
        a, b = rng.choice(uniq, size=2, replace=False)
        pairs.append((a, b))
    aucs, signs = [], []
    for a, b in pairs:
        pa1 = X1[c1 == a].mean(0)
        pb1 = X1[c1 == b].mean(0)
        pa2, pb2 = X2[c2 == a], X2[c2 == b]
        na, nb = len(pa2), len(pb2)
        test = np.vstack([pa2, pb2]).astype(np.float32)
        ytest = np.concatenate([np.ones(na), np.zeros(nb)])
        da = test @ pa1 / (np.linalg.norm(test, axis=1) * np.linalg.norm(pa1) + 1e-12)
        db = test @ pb1 / (np.linalg.norm(test, axis=1) * np.linalg.norm(pb1) + 1e-12)
        score = da - db
        if np.unique(ytest).size == 2 and np.unique(score).size > 1:
            aucs.append(roc_auc_score(ytest, score))
        signs.append(float(np.mean((score > 0) == (ytest == 1))))
    rows.append({"task": "cross_plate_prototype_discrimination", "n_pairs": len(pairs),
                 "method": "cosine_prototype_p1_to_p2", "mean_AUC": float(np.mean(aucs)),
                 "median_AUC": float(np.median(aucs)), "mean_sign_acc": float(np.mean(signs))})
    print("prototype discrimination:", np.mean(aucs), np.median(aucs), np.mean(signs))

    # ---------- save ----------
    out_csv = os.path.join(REPORTS, "20_stage11_p3_cross_plate_results.csv")
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print("saved:", out_csv)
    summary = {"experiment": "Stage 11 P3 cross-plate generalization (BR00116991 -> BR00116992)",
               "data": "existing profiles only, zero new downloads",
               "features": "904-feature well profiles + deep ResNet18 512-d (24-well subset)",
               "results": rows,
               "reference": "P2 same-set LOOCV LR trt-vs-trt pairwise AUC mean 0.7619 (21 pairs, mixed plate; different protocol)",
               "notes": ["same-plate LOOCV compound identity not computable (1 replicate per compound); "
                         "same-plate retrieval reference uses the 4 in-plate duplicate compounds of BR00116992"]}
    with open(os.path.join(REPORTS, "20_stage11_p3_cross_plate_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("summary ->", os.path.join(REPORTS, "20_stage11_p3_cross_plate_summary.json"))
    print("DONE.")


if __name__ == "__main__":
    main()
