# -*- coding: utf-8 -*-
"""
AI4S Single-cell Phenotypic Profiling - Stage 3: Classification Baseline & Target Consistency

1) Treatment vs DMSO binary classification (XGBoost + 5-fold CV, reports AUC / PR)
2) Treatment vs all controls (negcon + poscon)
3) Hierarchical clustering of compound fingerprints + intra-cluster target-gene consistency

Output : reports/figures/03_classification_roc_pr.png
         reports/03_classification_results.csv
         reports/03_target_validation.csv
         reports/03_pred_trt_vs_DMSO.csv, reports/03_pred_trt_vs_all_ctrl.csv
"""
import os
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    roc_curve,
    precision_recall_curve,
    accuracy_score,
)
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist
import xgboost as xgb

# ---------- Configuration ----------
RANDOM_STATE = 42
N_SPLITS = 5
N_ESTIMATORS = 200
N_ESTIMATORS_FULL = 300
MAX_DEPTH = 3
LEARNING_RATE = 0.05
SUBSAMPLE = 0.8
COLSAMPLE_BYTREE = 0.6
N_JOBS = 4
N_CLUSTERS = 12
TOP_FEATURES = 20
DPI = 150

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
FIG = os.path.join(BASE, "reports", "figures")
os.makedirs(FIG, exist_ok=True)


def load_profiles():
    """Load and concatenate all per-plate profile CSV.GZ files."""
    plate_files = sorted(
        f for f in os.listdir(os.path.join(DATA, "profiles")) if f.endswith(".csv.gz")
    )
    frames = [pd.read_csv(os.path.join(DATA, "profiles", f)) for f in plate_files]
    return pd.concat(frames, ignore_index=True)


# ---------- 1. Load ----------
prof = load_profiles()
meta_cols = [c for c in prof.columns if c.startswith("Metadata")]
feat_cols = [c for c in prof.columns if not c.startswith("Metadata")]
compound = prof.dropna(subset=["Metadata_pert_iname"]).copy()

X = compound[feat_cols].values.astype(np.float64)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

gene_map = dict(zip(compound["Metadata_pert_iname"], compound["Metadata_gene"]))


# ---------- 2. Classification tasks ----------
def run_cv(X, y, name):
    """5-fold stratified CV with XGBoost; returns metrics + full out-of-fold probabilities."""
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    y = y.astype(int)
    y_prob = np.zeros(len(y))
    for tr, te in skf.split(X, y):
        clf = xgb.XGBClassifier(
            n_estimators=N_ESTIMATORS,
            max_depth=MAX_DEPTH,
            learning_rate=LEARNING_RATE,
            subsample=SUBSAMPLE,
            colsample_bytree=COLSAMPLE_BYTREE,
            eval_metric="logloss",
            random_state=RANDOM_STATE,
            n_jobs=N_JOBS,
        )
        clf.fit(X[tr], y[tr])
        y_prob[te] = clf.predict_proba(X[te])[:, 1]
    auc = roc_auc_score(y, y_prob)
    ap = average_precision_score(y, y_prob)
    acc = accuracy_score(y, (y_prob >= 0.5).astype(int))
    fpr, tpr, _ = roc_curve(y, y_prob)
    prec, rec, _ = precision_recall_curve(y, y_prob)
    print(f"[{name}] AUC={auc:.4f} AP={ap:.4f} ACC={acc:.4f} (n_pos={y.sum()}, n={len(y)})")
    return {
        "name": name, "auc": auc, "ap": ap, "acc": acc,
        "fpr": fpr, "tpr": tpr, "prec": prec, "rec": rec,
        "y_prob": y_prob, "y": y,
    }


results = {}
# Task A: treatment vs DMSO (negative-control vehicle)
trt_mask = (compound["Metadata_pert_type"] == "trt").values
dmso_mask = (compound["Metadata_pert_iname"] == "DMSO").values
maskA = trt_mask | dmso_mask
results["trt_vs_DMSO"] = run_cv(X_scaled[maskA], trt_mask[maskA], "trt vs DMSO")

# Task B: treatment vs all controls
ctrl_mask = (compound["Metadata_pert_type"] == "control").values
maskB = trt_mask | ctrl_mask
results["trt_vs_all_ctrl"] = run_cv(X_scaled[maskB], trt_mask[maskB], "trt vs all_ctrl")

# ---------- 3. ROC / PR plot ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
for name, r in results.items():
    axes[0].plot(r["fpr"], r["tpr"], label=f"{name} (AUC={r['auc']:.3f})")
    axes[1].plot(r["rec"], r["prec"], label=f"{name} (AP={r['ap']:.3f})")
axes[0].plot([0, 1], [0, 1], "k--", alpha=0.4)
axes[0].set(xlabel="FPR", ylabel="TPR", title="ROC")
axes[1].set(xlabel="Recall", ylabel="Precision", title="PR")
for ax in axes:
    ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIG, "03_classification_roc_pr.png"), dpi=DPI)
plt.close()
print("Saved: reports/figures/03_classification_roc_pr.png")

# ---------- 4. Feature importance (Task A model) ----------
clf_full = xgb.XGBClassifier(
    n_estimators=N_ESTIMATORS_FULL,
    max_depth=MAX_DEPTH,
    learning_rate=LEARNING_RATE,
    subsample=SUBSAMPLE,
    colsample_bytree=COLSAMPLE_BYTREE,
    eval_metric="logloss",
    random_state=RANDOM_STATE,
    n_jobs=N_JOBS,
)
clf_full.fit(X_scaled[maskA], trt_mask[maskA].astype(int))
imp = pd.DataFrame({"feature": feat_cols, "importance": clf_full.feature_importances_})
imp = imp.sort_values("importance", ascending=False).head(TOP_FEATURES)
print("Top features:")
print(imp.to_string(index=False))

# ---------- 5. Target consistency validation ----------
fp_df = pd.read_csv(os.path.join(BASE, "reports", "02_phenotype_results.csv"))
fp_features = compound.groupby("Metadata_pert_iname")[feat_cols].mean()
fp_scaled = scaler.transform(fp_features.values)

# Ward hierarchical clustering
Z = linkage(pdist(fp_scaled, metric="euclidean"), method="ward")
labels = fcluster(Z, t=N_CLUSTERS, criterion="maxclust")
fp_df2 = pd.DataFrame({"pert_iname": fp_features.index, "cluster": labels})
fp_df2["gene"] = fp_df2["pert_iname"].map(gene_map)

# Intra-cluster target-gene consistency: dominant-gene fraction per cluster
rows = []
for cl in sorted(fp_df2["cluster"].unique()):
    sub = fp_df2[fp_df2["cluster"] == cl]
    with_gene = sub.dropna(subset=["gene"])
    n = len(sub)
    if len(with_gene) >= 3:
        top_gene, top_cnt = Counter(with_gene["gene"]).most_common(1)[0]
        frac = top_cnt / len(with_gene)
        rows.append(
            {"cluster": cl, "n_compounds": n, "n_with_gene": len(with_gene),
             "top_gene": top_gene, "top_gene_count": top_cnt,
             "top_gene_frac": round(frac, 2)}
        )
    else:
        rows.append(
            {"cluster": cl, "n_compounds": n, "n_with_gene": len(with_gene),
             "top_gene": None, "top_gene_count": 0, "top_gene_frac": 0}
        )
target_df = pd.DataFrame(rows)
print("\nIntra-cluster target consistency:")
print(target_df.to_string(index=False))
target_df.to_csv(os.path.join(BASE, "reports", "03_target_validation.csv"), index=False)

# Save out-of-fold prediction probabilities
for name, r in results.items():
    out = compound[maskA if name == "trt_vs_DMSO" else maskB][
        ["Metadata_pert_iname", "Metadata_pert_type"]
    ].copy()
    out["y_true"] = r["y"]
    out["y_prob"] = r["y_prob"]
    out.to_csv(os.path.join(BASE, "reports", f"03_pred_{name}.csv"), index=False)
print("\nSaved: 03_target_validation.csv + 03_pred_*.csv")
