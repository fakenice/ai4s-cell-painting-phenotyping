# -*- coding: utf-8 -*-
"""Stage 11 - P4: trt-vs-trt harder-task improvement on the 14-well / 7-compound set.

Evaluation protocol identical to P2 (Stage 11 Part C): leave-one-well-out (LOOCV)
logistic-regression pairwise AUC over all 21 compound pairs (7 compounds x 2 wells).
Fold-internal fitting only (no leakage): scaler / selector / models are re-fit on
train folds.

Methods compared (all on the same 21-pair protocol):
  M0  LR(C=1) on 904                     (baseline, P2 mean 0.7619)
  M1  Bagging-LR: 10-seed LR probability average
  M2  Feature selection + LR: fold-internal SelectKBest (ANOVA F), k in {50,100,200}
  M3  XGB + LR soft-voting ensemble
  M4  Combined: SelectKBest(k=100) + bagging-LR + XGB soft vote
  M5  LR on 904 + deep ResNet18 512-d concatenation (1416 features)

Grouped means: all 21 pairs, in-plate subset (4 compounds, 6 pairs) and
cross-plate subset (3 compounds, 3 pairs).

Outputs: reports/20_stage11_p4_trt_trt_boost_results.csv
         reports/20_stage11_p4_trt_trt_boost_summary.json
"""
import os, json
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

RANDOM_STATE = 42
BASE = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science"
DATA = os.path.join(BASE, "data")
REPO = os.path.join(BASE, "github_repo")
REPORTS = os.path.join(REPO, "reports")
NPZ = os.path.join(REPORTS, "19_stage11_p2_embeddings.npz")
P1, P2 = "BR00116991", "BR00116992"
FEAT_PREFIX = ("Cells_", "Cytoplasm_", "Nuclei_")

# 14 wells / 7 compounds (P2 hard task set)
WELLS = [("BR00116991", "A01", "gabapentin-enacarbil"), ("BR00116992", "A01", "gabapentin-enacarbil"),
         ("BR00116991", "A03", "amlodipine"), ("BR00116992", "A03", "amlodipine"),
         ("BR00116991", "A04", "hexestrol"), ("BR00116992", "A04", "hexestrol"),
         ("BR00116992", "A21", "dexamethasone"), ("BR00116992", "O02", "dexamethasone"),
         ("BR00116992", "B02", "thiostrepton"), ("BR00116992", "L23", "thiostrepton"),
         ("BR00116992", "B12", "BVT-948"), ("BR00116992", "O16", "BVT-948"),
         ("BR00116992", "G05", "ME-0328"), ("BR00116992", "J11", "ME-0328")]
CROSS_COMPOUNDS = ["gabapentin-enacarbil", "amlodipine", "hexestrol"]
IN_COMPOUNDS = ["dexamethasone", "thiostrepton", "BVT-948", "ME-0328"]
CROSS_PAIRS = sorted((a, b) for i, a in enumerate(CROSS_COMPOUNDS) for b in CROSS_COMPOUNDS[i + 1:])
IN_PAIRS = sorted((a, b) for i, a in enumerate(IN_COMPOUNDS) for b in IN_COMPOUNDS[i + 1:])
MIXED_PAIRS = sorted((a, b) for a in CROSS_COMPOUNDS for b in IN_COMPOUNDS)
ALL_PAIRS = sorted(CROSS_PAIRS + IN_PAIRS + MIXED_PAIRS)
assert len(CROSS_PAIRS) == 3 and len(IN_PAIRS) == 6 and len(MIXED_PAIRS) == 12
assert len(ALL_PAIRS) == 21


def well_to_site(w):
    return f"r{ord(w[0]) - ord('A') + 1:02d}c{int(w[1:]):02d}"


def load_data():
    feats = None
    mats = {}
    for plate in (P1, P2):
        f = os.path.join(DATA, "profiles", f"{plate}_normalized_feature_select_negcon_batch.csv.gz")
        df = pd.read_csv(f)
        feats = [c for c in df.columns if c.startswith(FEAT_PREFIX)]
        mats[plate] = df
    assert len(feats) == 904
    z = np.load(NPZ, allow_pickle=True)
    emb_site = dict(z["emb_site"].item())
    X904, Xdeep, comps = [], [], []
    for plate, well, comp in WELLS:
        sub = mats[plate][(mats[plate]["Metadata_Plate"] == plate) & (mats[plate]["Metadata_Well"] == well)]
        X904.append(sub[feats].mean(axis=0).values)
        site = f"{well_to_site(well)}f01p01"
        ks = [k for k in emb_site if k.split("|")[1] == plate and k.split("|")[2] == site]
        assert ks, (plate, well)
        Xdeep.append(np.mean([emb_site[k] for k in ks], axis=0))
        comps.append(comp)
    X904 = np.vstack(X904).astype(np.float32)
    Xdeep = np.vstack(Xdeep).astype(np.float32)
    return X904, Xdeep, np.array(comps, dtype=object)


def pair_auc_loocv(X, comps, ci, cj, method, seeds=(RANDOM_STATE,)):
    """Leave-one-well-out LR-type discriminator for a single pair."""
    idx = np.where((comps == ci) | (comps == cj))[0]
    Xp = X[idx]
    y = np.array([1 if comps[i] == ci else 0 for i in idx])
    preds = np.zeros(len(idx))
    for test_i in range(len(idx)):
        tr = np.delete(np.arange(len(idx)), test_i)
        Xtr, ytr = Xp[tr], y[tr]
        Xte = Xp[test_i:test_i + 1]
        if method.startswith("M5"):
            pass  # handled by caller via X passed in
        if method == "M0":
            sc = StandardScaler().fit(Xtr)
            clf = LogisticRegression(max_iter=2000, C=1.0, random_state=0)
            clf.fit(sc.transform(Xtr), ytr)
            preds[test_i] = clf.predict_proba(sc.transform(Xte))[:, 1][0]
        elif method == "M1":
            ps = []
            for s in seeds:
                sc = StandardScaler().fit(Xtr)
                clf = LogisticRegression(max_iter=2000, C=1.0, random_state=s)
                clf.fit(sc.transform(Xtr), ytr)
                ps.append(clf.predict_proba(sc.transform(Xte))[:, 1][0])
            preds[test_i] = float(np.mean(ps))
        elif method.startswith("M2"):
            k = int(method.split("_")[1])
            sc = StandardScaler().fit(Xtr)
            Xtrs = sc.transform(Xtr)
            sel = SelectKBest(f_classif, k=min(k, Xtr.shape[1])).fit(Xtrs, ytr)
            Xtrs = sel.transform(Xtrs)
            clf = LogisticRegression(max_iter=2000, C=1.0, random_state=0)
            clf.fit(Xtrs, ytr)
            preds[test_i] = clf.predict_proba(sel.transform(sc.transform(Xte)))[:, 1][0]
        elif method == "M3":
            sc = StandardScaler().fit(Xtr)
            Xtrs = sc.transform(Xtr)
            lr = LogisticRegression(max_iter=2000, C=1.0, random_state=0)
            lr.fit(Xtrs, ytr)
            xgb = XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.1,
                                eval_metric="logloss", n_jobs=1, random_state=0)
            xgb.fit(Xtrs, ytr)
            p_lr = lr.predict_proba(sc.transform(Xte))[:, 1][0]
            p_xgb = xgb.predict_proba(sc.transform(Xte))[:, 1][0]
            preds[test_i] = 0.5 * (p_lr + p_xgb)
        elif method == "M4":
            sc = StandardScaler().fit(Xtr)
            Xtrs = sc.transform(Xtr)
            sel = SelectKBest(f_classif, k=min(100, Xtr.shape[1])).fit(Xtrs, ytr)
            Xtrs = sel.transform(Xtrs)
            ps = []
            for s in seeds:
                clf = LogisticRegression(max_iter=2000, C=1.0, random_state=s)
                clf.fit(Xtrs, ytr)
                ps.append(clf.predict_proba(sel.transform(sc.transform(Xte)))[:, 1][0])
            xgb = XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.1,
                                eval_metric="logloss", n_jobs=1, random_state=0)
            xgb.fit(Xtrs, ytr)
            p_lr = float(np.mean(ps))
            p_xgb = xgb.predict_proba(sel.transform(sc.transform(Xte)))[:, 1][0]
            preds[test_i] = 0.5 * (p_lr + p_xgb)
        else:
            raise ValueError(method)
    if np.unique(y).size < 2 or np.unique(preds).size < 2:
        return float("nan")
    return float(roc_auc_score(y, preds))


def run_block(X, comps, method, label=""):
    aucs = {}
    for ci, cj in ALL_PAIRS:
        aucs[f"{ci}__{cj}"] = pair_auc_loocv(X, comps, ci, cj, method)
    vals = np.array([v for v in aucs.values() if not np.isnan(v)])
    grouped = {}
    for gname, gpairs in [("all_21", ALL_PAIRS), ("in_plate_6", IN_PAIRS),
                          ("cross_plate_3", CROSS_PAIRS), ("mixed_12", MIXED_PAIRS)]:
        gv = [aucs[f"{ci}__{cj}"] for ci, cj in gpairs]
        gv = [v for v in gv if not np.isnan(v)]
        grouped[gname] = {"mean": float(np.mean(gv)) if gv else None,
                          "min": float(np.min(gv)) if gv else None,
                          "max": float(np.max(gv)) if gv else None}
    ge0_8 = float(np.mean(vals >= 0.8)) if len(vals) else None
    print(f"{label:>10s} {method:>12s} mean {np.mean(vals):.4f} min {np.min(vals):.4f} "
          f"max {np.max(vals):.4f} >=0.8 {ge0_8:.2f} | in {grouped['in_plate_6']['mean']:.4f} "
          f"cross {grouped['cross_plate_3']['mean']:.4f}")
    return {"method": method, "label": label, **grouped, "pairs_frac_ge_0_8": ge0_8,
            "pair_aucs": {k: (float(v) if v == v else None) for k, v in aucs.items()}}


def main():
    print("=" * 70)
    print("Stage 11 P4: trt-vs-trt harder-task improvement (21 pairs, LOOCV LR AUC)")
    print("=" * 70)
    X904, Xdeep, comps = load_data()
    results = []
    results.append(run_block(X904, comps, "M0", "baseline"))
    results.append(run_block(X904, comps, "M1", "bagging"))
    for k in (50, 100, 200):
        results.append(run_block(X904, comps, f"M2_{k}", "sel"))
    results.append(run_block(X904, comps, "M3", "xgb+lr"))
    results.append(run_block(X904, comps, "M4", "comb"))
    Xcat = np.hstack([X904, Xdeep]).astype(np.float32)
    results.append(run_block(Xcat, comps, "M0", "904+deep"))

    out_csv = os.path.join(REPORTS, "20_stage11_p4_trt_trt_boost_results.csv")
    flat = []
    for r in results:
        row = {"method": r["method"], "label": r["label"],
               "all_21_mean": r["all_21"]["mean"], "all_21_min": r["all_21"]["min"],
               "all_21_max": r["all_21"]["max"],
               "in_plate_6_mean": r["in_plate_6"]["mean"], "in_plate_6_min": r["in_plate_6"]["min"],
               "in_plate_6_max": r["in_plate_6"]["max"],
               "cross_plate_3_mean": r["cross_plate_3"]["mean"], "cross_plate_3_min": r["cross_plate_3"]["min"],
               "cross_plate_3_max": r["cross_plate_3"]["max"],
               "mixed_12_mean": r["mixed_12"]["mean"], "mixed_12_min": r["mixed_12"]["min"],
               "mixed_12_max": r["mixed_12"]["max"],
               "pairs_frac_ge_0_8": r["pairs_frac_ge_0_8"]}
        flat.append(row)
    pd.DataFrame(flat).to_csv(out_csv, index=False)
    print("saved:", out_csv)

    summary = {"experiment": "Stage 11 P4 trt-vs-trt harder-task improvement",
               "protocol": "LOOCV LR pairwise AUC, 7 compounds x 2 wells = 21 pairs (P2-identical)",
               "baseline": {"P2_reported_904_LR_mean_AUC": 0.7619},
               "results": results,
               "notes": ["all models fit fold-internally (scaler/selector/models on train folds only)",
                         "in-plate subset: dexamethasone/thiostrepton/BVT-948/ME-0328 (6 pairs); "
                         "cross-plate subset: gabapentin-enacarbil/amlodipine/hexestrol (3 pairs)"]}
    with open(os.path.join(REPORTS, "20_stage11_p4_trt_trt_boost_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("summary ->", os.path.join(REPORTS, "20_stage11_p4_trt_trt_boost_summary.json"))
    print("DONE.")


if __name__ == "__main__":
    main()
