# -*- coding: utf-8 -*-
"""
AI4S Single-cell Phenotypic Profiling - Stage 6: Structure-aware & Uncertainty-aware Phenotype Prediction

Part 1  Structure-aware (scaffold-aware) modeling
    - ECFP4 (Morgan, radius=2, 1024 bits) fingerprints generated from JUMP-CP SMILES via RDKit
    - Compound-level trt vs DMSO XGBoost models: pheno-only | fp-only | pheno+fp
    - Reports AUC/AP deltas and fingerprint-vs-morphology feature importance split

Part 2  Uncertainty-aware modeling
    - Probability calibration (Platt + isotonic) on the structure-enhanced model
    - Split conformal prediction (calibration quantile estimated on a held-out calibration set)
    - Reliability diagram, ECE / Brier, empirical conformal coverage
    - Low-confidence sample list -> "low-confidence -> human review" OoC screening workflow

Part 3  Exploratory SIDER toxicity prediction
    - Predict SIDER annotation (has_sider) from morphological features (46 / 268 annotated)
    - High-vs-low toxicity burden within the annotated set (median n_side_effects split)
    - Honest reporting of imbalance / small-sample limitations

Output : reports/figures/16_structure_enhanced_performance.png
         reports/figures/17_reliability_calibration.png
         reports/figures/18_conformal_coverage.png
         reports/figures/19_low_confidence_review.png
         reports/figures/20_sider_toxicity.png
         reports/16_structure_uncertainty_results.csv
         reports/16_sider_prediction.csv
         reports/16_low_confidence_samples.csv
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
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    roc_curve,
    precision_recall_curve,
    accuracy_score,
    brier_score_loss,
)
from rdkit import Chem
from rdkit.Chem import AllChem
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
FP_RADIUS = 2
FP_NBITS = 1024
CONF_ALPHA = 0.1          # nominal 90% conformal interval
LOW_CONF_MARGIN = 0.15    # |p - 0.5| < 0.15 -> low confidence / human review
CAL_BINS = 10
N_SIDER_REPEATS = 3
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


def stratified_split(idx, y, test_size, seed):
    """Stratified index split helper (returns train_idx, rest_idx)."""
    from sklearn.model_selection import train_test_split
    return train_test_split(idx, test_size=test_size, stratify=y, random_state=seed)


def xgb_clf():
    return xgb.XGBClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        learning_rate=LEARNING_RATE,
        subsample=SUBSAMPLE,
        colsample_bytree=COLSAMPLE_BYTREE,
        eval_metric="logloss",
        random_state=RANDOM_STATE,
        n_jobs=N_JOBS,
    )


def run_cv(X, y, name):
    """5-fold stratified CV; returns metrics + full out-of-fold probabilities."""
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    y = y.astype(int)
    y_prob = np.zeros(len(y))
    for tr, te in skf.split(X, y):
        clf = xgb_clf()
        clf.fit(X[tr], y[tr])
        y_prob[te] = clf.predict_proba(X[te])[:, 1]
    auc = roc_auc_score(y, y_prob)
    ap = average_precision_score(y, y_prob)
    acc = accuracy_score(y, (y_prob >= 0.5).astype(int))
    print(f"[{name}] AUC={auc:.4f} AP={ap:.4f} ACC={acc:.4f} (n_pos={y.sum()}, n={len(y)})")
    return {
        "name": name, "auc": auc, "ap": ap, "acc": acc,
        "y_prob": y_prob, "y": y,
    }


def ece(y, p, bins=CAL_BINS):
    """Expected Calibration Error."""
    edges = np.linspace(0, 1, bins + 1)
    e = 0.0
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1]) if i < bins - 1 else (p >= edges[i]) & (p <= edges[i + 1])
        if m.sum() == 0:
            continue
        e += (m.sum() / len(p)) * abs(p[m].mean() - y[m].mean())
    return e


# ---------- 1. Load data ----------
prof = load_profiles()
feat_cols = [c for c in prof.columns if not c.startswith("Metadata")]
compound = prof.dropna(subset=["Metadata_pert_iname"]).copy()
fp_features = compound.groupby("Metadata_pert_iname")[feat_cols].mean()
scaler = StandardScaler().fit(fp_features.values)
X_pheno_comp = scaler.transform(fp_features.values)   # compound-level (SIDER part)
X_pheno_well = scaler.transform(compound[feat_cols].values)  # well-level (main model)

# Structure fingerprints (ECFP4) from SMILES
meta = pd.read_csv(
    os.path.join(DATA, "metadata", "JUMP-Target-1_compound_metadata.tsv"), sep="\t"
)
meta_dedup = meta.drop_duplicates(subset=["pert_iname"]).set_index("pert_iname")
smiles_map = meta_dedup["smiles"].to_dict()

gen = AllChem.GetMorganGenerator(radius=FP_RADIUS, fpSize=FP_NBITS)
rows_fp, fail = [], 0
for name in fp_features.index:
    smi = smiles_map.get(name, None)
    mol = Chem.MolFromSmiles(smi) if smi else None
    if mol is None:
        fail += 1
        rows_fp.append(np.zeros(FP_NBITS, dtype=np.float32))
    else:
        bits = gen.GetFingerprint(mol).ToBitString()
        rows_fp.append(np.fromiter((int(b) for b in bits), dtype=np.float32, count=FP_NBITS))
X_fp = np.vstack(rows_fp)
print(f"Fingerprints generated: {len(rows_fp)} compounds ({fail} SMILES parse failures)")

# Broadcast compound fingerprints to well level (scaffold-aware well features)
name2idx = {n: i for i, n in enumerate(fp_features.index)}
X_fp_well = np.zeros((len(compound), FP_NBITS), dtype=np.float32)
for i, nm in enumerate(compound["Metadata_pert_iname"].values):
    j = name2idx.get(nm, -1)
    if j >= 0:
        X_fp_well[i] = X_fp[j]

results = {}
rows = []


def add(section, key, value, note=""):
    rows.append({"section": section, "metric": key, "value": value, "note": note})


# ---------- 2. Structure-aware modeling: trt vs DMSO (well level, same as Stage 3 baseline) ----------
trt_mask = (compound["Metadata_pert_type"].values == "trt")
dmso_mask = (compound["Metadata_pert_iname"].values == "DMSO")
maskA = trt_mask | dmso_mask

labels_A = compound.loc[maskA, "Metadata_pert_iname"].values
X_pheno_A, X_fp_A, y_A = X_pheno_well[maskA], X_fp_well[maskA], trt_mask[maskA].astype(int)
X_both_A = np.hstack([X_pheno_A, X_fp_A])

r_pheno = run_cv(X_pheno_A, y_A, "trt_vs_DMSO pheno-only")
r_fp = run_cv(X_fp_A, y_A, "trt_vs_DMSO fp-only")
r_both = run_cv(X_both_A, y_A, "trt_vs_DMSO pheno+fp")
results["structure"] = {
    "pheno_only": r_pheno, "fp_only": r_fp, "pheno_plus_fp": r_both,
    "auc_delta": r_both["auc"] - r_pheno["auc"],
    "ap_delta": r_both["ap"] - r_pheno["ap"],
}

# Feature importance split for the combined model
clf_full = xgb.XGBClassifier(
    n_estimators=N_ESTIMATORS_FULL, max_depth=MAX_DEPTH, learning_rate=LEARNING_RATE,
    subsample=SUBSAMPLE, colsample_bytree=COLSAMPLE_BYTREE, eval_metric="logloss",
    random_state=RANDOM_STATE, n_jobs=N_JOBS,
)
clf_full.fit(X_both_A, y_A)
imp = clf_full.feature_importances_
imp_pheno, imp_fp = imp[: X_pheno_A.shape[1]].sum(), imp[X_pheno_A.shape[1]:].sum()
top_pheno = np.argsort(imp[: X_pheno_A.shape[1]])[::-1][:10]
top_fp = np.argsort(imp[X_pheno_A.shape[1]:])[::-1][:10]
print(f"\nCombined-model importance: pheno={imp_pheno:.3f} fp={imp_fp:.3f} (share fp={imp_fp/(imp_pheno+imp_fp):.1%})")
results["structure"]["imp_pheno"] = float(imp_pheno)
results["structure"]["imp_fp"] = float(imp_fp)
results["structure"]["imp_fp_share"] = float(imp_fp / (imp_pheno + imp_fp))

# Figure 16: structure-enhanced performance
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
names = ["pheno-only", "fp-only", "pheno+fp"]
aucs = [r_pheno["auc"], r_fp["auc"], r_both["auc"]]
aps = [r_pheno["ap"], r_fp["ap"], r_both["ap"]]
xpos = np.arange(3)
axes[0].bar(xpos - 0.15, aucs, 0.3, label="AUC", color=["#4C72B0", "#DD8452", "#55A868"])
axes[0].bar(xpos + 0.15, aps, 0.3, label="AP", color=["#C44E52", "#8172B3", "#CCB974"])
axes[0].set_xticks(xpos); axes[0].set_xticklabels(names)
axes[0].set_ylim(0, 1); axes[0].set_ylabel("score")
axes[0].set_title("Structure-aware: trt vs DMSO (compound-level, 5-fold CV)")
axes[0].legend()
for i, (a, ap) in enumerate(zip(aucs, aps)):
    axes[0].text(i - 0.15, a + 0.01, f"{a:.3f}", ha="center", fontsize=8)
    axes[0].text(i + 0.15, ap + 0.01, f"{ap:.3f}", ha="center", fontsize=8)
axes[1].plot([0, 1], [0, 1], "k--", alpha=0.4)
for name, r in [("pheno-only", r_pheno), ("fp-only", r_fp), ("pheno+fp", r_both)]:
    fpr, tpr, _ = roc_curve(r["y"], r["y_prob"])
    axes[1].plot(fpr, tpr, label=f"{name} (AUC={r['auc']:.3f})")
axes[1].set(xlabel="FPR", ylabel="TPR", title="ROC curves")
axes[1].legend()
plt.tight_layout()
plt.savefig(os.path.join(FIG, "16_structure_enhanced_performance.png"), dpi=DPI)
plt.close()
print("Saved: reports/figures/16_structure_enhanced_performance.png")

# ---- Scaffold-aware group-CV robustness check: trt vs all controls ----
# Random CV on trt vs DMSO is easy for fingerprints (DMSO solvent is structurally unique);
# group-CV by scaffold (Tanimoto>0.5 single-linkage clusters) tests generalization to new scaffolds.
ctrl_mask = (compound["Metadata_pert_type"].values == "control")
maskB = trt_mask | ctrl_mask
Xb_pheno, Xb_fp, yB = X_pheno_well[maskB], X_fp_well[maskB], trt_mask[maskB].astype(int)

uniq_names = list(dict.fromkeys(compound.loc[maskB, "Metadata_pert_iname"].values))
uniq_fp = np.vstack([X_fp[name2idx[n]] for n in uniq_names])
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist
from sklearn.model_selection import GroupKFold

dist = pdist(uniq_fp, metric="jaccard")  # jaccard distance == 1 - Tanimoto
Z = linkage(dist, method="single")
grp = fcluster(Z, t=0.5, criterion="distance")  # Tanimoto sim > 0.5 -> same scaffold group
uniq2grp = {n: int(g) for n, g in zip(uniq_names, grp)}
well_grp = np.array([uniq2grp[n] for n in compound.loc[maskB, "Metadata_pert_iname"].values])
n_grp = len(set(well_grp))
print(f"Scaffold groups: {n_grp} groups from {len(uniq_names)} unique compounds (Tanimoto>0.5)")


def run_group_cv(X, y, groups, name):
    gkf = GroupKFold(n_splits=5)
    y_prob = np.full(len(y), np.nan)
    skipped = 0
    for tr, te in gkf.split(X, y, groups=groups):
        if len(np.unique(y[te])) < 2 or len(np.unique(y[tr])) < 2:
            skipped += 1
            continue
        clf = xgb_clf()
        clf.fit(X[tr], y[tr])
        y_prob[te] = clf.predict_proba(X[te])[:, 1]
    valid = ~np.isnan(y_prob)
    if valid.sum() == 0:
        print(f"[{name}] no evaluable folds (skipped={skipped})")
        return None
    auc = roc_auc_score(y[valid], y_prob[valid])
    ap = average_precision_score(y[valid], y_prob[valid])
    print(f"[{name}] scaffold-GROUP-CV AUC={auc:.4f} AP={ap:.4f} (folds_skipped={skipped})")
    return auc, ap


g_pheno = run_group_cv(Xb_pheno, yB, well_grp, "trt_vs_ctrl pheno-only")
g_fp = run_group_cv(Xb_fp, yB, well_grp, "trt_vs_ctrl fp-only")
g_both = run_group_cv(np.hstack([Xb_pheno, Xb_fp]), yB, well_grp, "trt_vs_ctrl pheno+fp")
if g_pheno and g_fp and g_both:
    add("structure", "AUC_groupCV_pheno", f"{g_pheno[0]:.4f}", "trt_vs_all_controls scaffold group-CV (Tanimoto>0.5)")
    add("structure", "AUC_groupCV_fp", f"{g_fp[0]:.4f}", "")
    add("structure", "AUC_groupCV_both", f"{g_both[0]:.4f}", "")
    add("structure", "AP_groupCV_pheno", f"{g_pheno[1]:.4f}", "")
    add("structure", "AP_groupCV_fp", f"{g_fp[1]:.4f}", "")
    add("structure", "AP_groupCV_both", f"{g_both[1]:.4f}", "")
    add("structure", "n_scaffold_groups", str(n_grp), f"{len(uniq_names)} unique compounds")

# ---------- 3. Uncertainty-aware: calibration + split conformal ----------
# NOTE: calibration / conformal are evaluated on the MORPHOLOGY-ONLY model (AUC=0.768).
# The structure-enhanced model is near-perfect on trt vs DMSO (AUC=1.0) and its predicted
# probabilities collapse to {0,1}, giving degenerate (zero-width) intervals; the morphology
# model reflects the realistic OoC screening uncertainty regime.
# Train/calibration/test split (stratified)
idx = np.arange(len(y_A))
tr_idx, rest = stratified_split(idx, y_A, test_size=0.3, seed=RANDOM_STATE)
ca_idx, te_idx = stratified_split(rest, y_A[rest], test_size=0.5, seed=RANDOM_STATE)

clf_main = xgb_clf()
clf_main.fit(X_pheno_A[tr_idx], y_A[tr_idx])
p_ca = clf_main.predict_proba(X_pheno_A[ca_idx])[:, 1]
p_te = clf_main.predict_proba(X_pheno_A[te_idx])[:, 1]
y_ca, y_te = y_A[ca_idx], y_A[te_idx]

# Platt calibration (logistic on logit of p)
safe_logit = np.clip(p_ca, 1e-6, 1 - 1e-6)
platt = LogisticRegression()
platt.fit(np.log(safe_logit / (1 - safe_logit)).reshape(-1, 1), y_ca)
p_te_platt = platt.predict_proba(np.log(np.clip(p_te, 1e-6, 1 - 1e-6) / (1 - np.clip(p_te, 1e-6, 1 - 1e-6))).reshape(-1, 1))[:, 1]

# Isotonic calibration
iso = IsotonicRegression(out_of_bounds="clip")
iso.fit(p_ca, y_ca)
p_te_iso = iso.predict(p_te)

brier_raw = brier_score_loss(y_te, p_te)
brier_platt = brier_score_loss(y_te, p_te_platt)
brier_iso = brier_score_loss(y_te, p_te_iso)
ece_raw = ece(y_te, p_te)
ece_platt = ece(y_te, p_te_platt)
ece_iso = ece(y_te, p_te_iso)
print(f"\nCalibration (test n={len(y_te)}): Brier raw={brier_raw:.4f} platt={brier_platt:.4f} iso={brier_iso:.4f}")
print(f"ECE raw={ece_raw:.4f} platt={ece_platt:.4f} iso={ece_iso:.4f}")
results["uncertainty"] = {
    "brier_raw": float(brier_raw), "brier_platt": float(brier_platt), "brier_iso": float(brier_iso),
    "ece_raw": float(ece_raw), "ece_platt": float(ece_platt), "ece_iso": float(ece_iso),
}

# Split conformal: quantile of |y - p| on calibration set
p_ca_cal = iso.predict(p_ca)  # calibrated probabilities used for intervals
p_te_cal = p_te_iso
resid = np.abs(y_ca - p_ca_cal)
q_hat = np.quantile(resid, 1 - CONF_ALPHA)
lo = np.clip(p_te_cal - q_hat, 0, 1)
hi = np.clip(p_te_cal + q_hat, 0, 1)
coverage = np.mean((y_te >= lo) & (y_te <= hi))
widths = hi - lo
print(f"Conformal (alpha={CONF_ALPHA}): q_hat={q_hat:.4f} coverage={coverage:.3f} mean_width={widths.mean():.4f}")
results["uncertainty"]["q_hat"] = float(q_hat)
results["uncertainty"]["coverage_0.9"] = float(coverage)
results["uncertainty"]["mean_interval_width"] = float(widths.mean())

# Coverage vs alpha scan
alphas = [0.05, 0.1, 0.2, 0.3, 0.5]
covs, widths_s = [], []
for a in alphas:
    q = np.quantile(resid, 1 - a)
    lo_a = np.clip(p_te_cal - q, 0, 1)
    hi_a = np.clip(p_te_cal + q, 0, 1)
    covs.append(np.mean((y_te >= lo_a) & (y_te <= hi_a)))
    widths_s.append((hi_a - lo_a).mean())
results["uncertainty"]["coverage_scan"] = dict(zip([f"alpha_{a}" for a in alphas], covs))

# Figure 17: reliability diagram
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
edges = np.linspace(0, 1, CAL_BINS + 1)
for ax, (pl, col, lab) in enumerate([(p_te, "#C44E52", "raw"), (p_te_iso, "#55A868", "isotonic")]):
    accs, confs = [], []
    for i in range(CAL_BINS):
        m = (pl >= edges[i]) & (pl < edges[i + 1]) if i < CAL_BINS - 1 else (pl >= edges[i]) & (pl <= edges[i + 1])
        if m.sum() == 0:
            accs.append(np.nan); confs.append(np.nan)
        else:
            confs.append(pl[m].mean()); accs.append(y_te[m].mean())
    axes[0].plot(confs, accs, "o-", color=col, label=lab)
axes[0].plot([0, 1], [0, 1], "k--", alpha=0.5)
axes[0].set(xlabel="predicted probability", ylabel="observed frequency", title="Reliability diagram")
axes[0].legend()
brier_vals = [("raw", brier_raw, ece_raw), ("platt", brier_platt, ece_platt), ("isotonic", brier_iso, ece_iso)]
axes[1].barh([b[0] for b in brier_vals], [b[1] for b in brier_vals], color=["#C44E52", "#DD8452", "#55A868"])
axes[1].set_title("Brier score (lower is better)")
for i, b in enumerate(brier_vals):
    axes[1].text(b[1] + 0.002, i, f"{b[1]:.4f}  ECE={b[2]:.4f}", va="center", fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "17_reliability_calibration.png"), dpi=DPI)
plt.close()
print("Saved: reports/figures/17_reliability_calibration.png")

# Figure 18: conformal coverage
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].plot([1 - a for a in alphas], covs, "o-", color="#4C72B0", label="empirical coverage")
axes[0].plot([0.5, 1], [0.5, 1], "k--", alpha=0.5, label="nominal")
axes[0].set(xlabel="nominal level (1-alpha)", ylabel="empirical coverage", title="Split-conformal coverage")
axes[0].legend()
axes[1].hist(widths, bins=20, color="#8172B3", alpha=0.8)
axes[1].axvline(widths.mean(), color="k", ls="--", label=f"mean={widths.mean():.3f}")
axes[1].set(xlabel="interval width", ylabel="count", title="Interval width (test set)")
axes[1].legend()
plt.tight_layout()
plt.savefig(os.path.join(FIG, "18_conformal_coverage.png"), dpi=DPI)
plt.close()
print("Saved: reports/figures/18_conformal_coverage.png")

# Low-confidence review workflow
margin = np.abs(p_te_cal - 0.5)
low_conf = margin < LOW_CONF_MARGIN
low_df = pd.DataFrame({
    "pert_iname": labels_A[te_idx],
    "y_true": y_te,
    "p_calibrated": p_te_cal,
    "interval_width": widths,
    "low_confidence": low_conf,
})
low_df.to_csv(os.path.join(BASE, "reports", "16_low_confidence_samples.csv"), index=False)
print(f"Low-confidence samples (|p-0.5|<{LOW_CONF_MARGIN}): {low_df['low_confidence'].sum()}/{len(low_df)}")

# Figure 19: low-confidence -> human review OoC workflow
fig, axes = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1.4, 1]})
sc = axes[0].scatter(p_te_cal, widths, c=y_te, cmap="coolwarm", s=40, edgecolor="k", linewidth=0.3)
axes[0].axvspan(0.5 - LOW_CONF_MARGIN, 0.5 + LOW_CONF_MARGIN, color="red", alpha=0.15, label="low-confidence -> human review")
axes[0].axvline(0.5, color="gray", ls="--", alpha=0.6)
axes[0].set(xlabel="calibrated P(treatment)", ylabel="conformal interval width", title="OoC screening: confidence vs interval")
axes[0].legend(loc="upper left")
cbar = fig.colorbar(sc, ax=axes[0]); cbar.set_label("true label (1=trt)")
ax = axes[1]; ax.axis("off")
ax.text(0.5, 0.95, "Low-confidence OoC screening workflow", ha="center", fontsize=11, weight="bold")
boxes = [
    (0.5, 0.78, "Morphology + ECFP4 model\nP(trt) + conformal interval"),
    (0.5, 0.52, "|p-0.5| >= 0.15 ?\n(confidence gate)"),
    (0.22, 0.22, "Auto route:\nhigh-confidence call", "#55A868"),
    (0.78, 0.22, "Human review:\nlow-confidence wells", "#C44E52"),
]
for x, y, t, *rest in boxes:
    color = rest[0] if rest else "#EAF2F8"
    ax.add_patch(plt.Rectangle((x - 0.28, y - 0.08), 0.56, 0.16, fc=color, ec="black", lw=0.8))
    ax.text(x, y, t, ha="center", va="center", fontsize=8)
for x0, y0, x1, y1 in [(0.5, 0.70, 0.5, 0.60), (0.5, 0.44, 0.22, 0.30), (0.5, 0.44, 0.78, 0.30)]:
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", lw=1.2))
plt.tight_layout()
plt.savefig(os.path.join(FIG, "19_low_confidence_review.png"), dpi=DPI)
plt.close()
print("Saved: reports/figures/19_low_confidence_review.png")

# ---------- 4. Exploratory SIDER toxicity prediction ----------
ann = pd.read_csv(os.path.join(BASE, "reports", "09_compound_annotations_full.csv"))
ann_sub = ann[["Metadata_pert_iname", "has_sider", "n_side_effects"]].drop_duplicates(
    subset=["Metadata_pert_iname"]
).set_index("Metadata_pert_iname")
feat_sider = fp_features.join(ann_sub, how="inner")
print(f"\nSIDER merge: {len(feat_sider)} compounds ({feat_sider['has_sider'].sum()} with SIDER annotations)")
y_sider = feat_sider["has_sider"].astype(int).values
X_sider = scaler.transform(feat_sider[feat_cols].values)
pos_frac = y_sider.mean()
print(f"SIDER positive fraction: {pos_frac:.3f} ({y_sider.sum()}/{len(y_sider)})")

sider_aucs, sider_aps = [], []
sider_y_prob = np.zeros(len(y_sider))
skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
for tr, te in skf.split(X_sider, y_sider):
    clf = xgb_clf()
    clf.fit(X_sider[tr], y_sider[tr])
    sider_y_prob[te] = clf.predict_proba(X_sider[te])[:, 1]
sider_auc = roc_auc_score(y_sider, sider_y_prob)
sider_ap = average_precision_score(y_sider, sider_y_prob)
print(f"SIDER has_sider: AUC={sider_auc:.4f} AP={sider_ap:.4f} (baseline AP={pos_frac:.3f})")

# Toxicity burden: high vs low (median n_side_effects within annotated)
sub = feat_sider[feat_sider["has_sider"] == True].copy()
med = sub["n_side_effects"].median()
sub["burden"] = (sub["n_side_effects"] > med).astype(int)
print(f"Burden split (n={len(sub)}): high={sub['burden'].sum()} low={(1 - sub['burden']).sum()} median={med}")
burden_aucs, burden_aps = [], []
skf2 = StratifiedKFold(n_splits=3, shuffle=True, random_state=RANDOM_STATE)
for rep in range(N_SIDER_REPEATS):
    skf2 = StratifiedKFold(n_splits=3, shuffle=True, random_state=RANDOM_STATE + rep)
    Xb = scaler.transform(sub[feat_cols].values)
    yb = sub["burden"].values
    prob = np.zeros(len(yb))
    for tr, te in skf2.split(Xb, yb):
        clf = xgb_clf()
        clf.fit(Xb[tr], yb[tr])
        prob[te] = clf.predict_proba(Xb[te])[:, 1]
    burden_aucs.append(roc_auc_score(yb, prob))
    burden_aps.append(average_precision_score(yb, prob))
print(f"SIDER burden high-vs-low (repeated 3x3fold): AUC={np.mean(burden_aucs):.4f}+-{np.std(burden_aucs):.4f} AP={np.mean(burden_aps):.4f}+-{np.std(burden_aps):.4f}")

sider_out = feat_sider[["has_sider", "n_side_effects"]].copy()
sider_out["y_prob"] = sider_y_prob
sider_out.to_csv(os.path.join(BASE, "reports", "16_sider_prediction.csv"), index=False)

# Figure 20: SIDER toxicity
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
axes[0].bar(["has_sider\nAUC", "has_sider\nAP", "burden\nAUC", "burden\nAP"],
            [sider_auc, sider_ap, np.mean(burden_aucs), np.mean(burden_aps)],
            color=["#4C72B0", "#DD8452", "#55A868", "#C44E52"])
axes[0].axhline(pos_frac, color="k", ls="--", lw=1, label=f"AP baseline {pos_frac:.2f}")
axes[0].set_ylim(0, 1); axes[0].set_title("SIDER predictive performance"); axes[0].legend()
prec, rec, _ = precision_recall_curve(y_sider, sider_y_prob)
axes[1].plot(rec, prec, color="#4C72B0")
axes[1].axhline(pos_frac, color="k", ls="--", alpha=0.6, label=f"baseline {pos_frac:.2f}")
axes[1].set(xlabel="Recall", ylabel="Precision", title="PR curve (has_sider)")
axes[1].legend()
axes[2].bar(["no SIDER\n(n=%d)" % (len(y_sider) - y_sider.sum()), "SIDER\n(n=%d)" % y_sider.sum()],
            [len(y_sider) - y_sider.sum(), y_sider.sum()], color=["#CBC9E2", "#4C72B0"])
axes[2].set_title("Class imbalance (46/268 annotated)")
for i, v in enumerate([len(y_sider) - y_sider.sum(), y_sider.sum()]):
    axes[2].text(i, v + 3, str(v), ha="center")
plt.tight_layout()
plt.savefig(os.path.join(FIG, "20_sider_toxicity.png"), dpi=DPI)
plt.close()
print("Saved: reports/figures/20_sider_toxicity.png")
results["sider"] = {
    "n_annotated": int(y_sider.sum()), "n_total": int(len(y_sider)),
    "pos_frac": float(pos_frac), "auc": float(sider_auc), "ap": float(sider_ap),
    "burden_auc_mean": float(np.mean(burden_aucs)), "burden_auc_std": float(np.std(burden_aucs)),
    "burden_ap_mean": float(np.mean(burden_aps)), "burden_ap_std": float(np.std(burden_aps)),
}

# ---------- 5. Summary CSV ----------
add("structure", "AUC_pheno_only", f"{r_pheno['auc']:.4f}", "trt vs DMSO, well-level, 5-fold CV")
add("structure", "AP_pheno_only", f"{r_pheno['ap']:.4f}", "")
add("structure", "AUC_fp_only", f"{r_fp['auc']:.4f}", "ECFP4 only")
add("structure", "AP_fp_only", f"{r_fp['ap']:.4f}", "")
add("structure", "AUC_pheno_plus_fp", f"{r_both['auc']:.4f}", "structure-enhanced model")
add("structure", "AP_pheno_plus_fp", f"{r_both['ap']:.4f}", "")
add("structure", "AUC_delta", f"{r_both['auc'] - r_pheno['auc']:+.4f}", "pheno+fp vs pheno-only")
add("structure", "AP_delta", f"{r_both['ap'] - r_pheno['ap']:+.4f}", "")
add("structure", "feature_importance_pheno", f"{imp_pheno:.3f}", "combined model")
add("structure", "feature_importance_fp", f"{imp_fp:.3f}", "")
add("structure", "fp_importance_share", f"{imp_fp/(imp_pheno+imp_fp):.1%}", "")
add("uncertainty", "Brier_raw", f"{brier_raw:.4f}", "test set")
add("uncertainty", "Brier_platt", f"{brier_platt:.4f}", "")
add("uncertainty", "Brier_isotonic", f"{brier_iso:.4f}", "")
add("uncertainty", "ECE_raw", f"{ece_raw:.4f}", "10 bins")
add("uncertainty", "ECE_platt", f"{ece_platt:.4f}", "")
add("uncertainty", "ECE_isotonic", f"{ece_iso:.4f}", "")
add("uncertainty", "conformal_q_hat", f"{q_hat:.4f}", f"alpha={CONF_ALPHA}")
add("uncertainty", "conformal_coverage", f"{coverage:.3f}", f"nominal 90%, test n={len(y_te)}")
add("uncertainty", "mean_interval_width", f"{widths.mean():.4f}", "")
add("uncertainty", "low_confidence_count", str(int(low_df["low_confidence"].sum())), f"margin<{LOW_CONF_MARGIN}, test n={len(y_te)}")
add("sider", "n_annotated", str(int(y_sider.sum())), f"of {len(y_sider)} compounds")
add("sider", "positive_fraction", f"{pos_frac:.3f}", "class imbalance")
add("sider", "AUC_has_sider", f"{sider_auc:.4f}", "5-fold CV")
add("sider", "AP_has_sider", f"{sider_ap:.4f}", f"baseline={pos_frac:.3f}")
add("sider", "AUC_burden_high_vs_low", f"{np.mean(burden_aucs):.4f}+-{np.std(burden_aucs):.4f}", f"repeated 3x3-fold, n={len(sub)}")
add("sider", "AP_burden_high_vs_low", f"{np.mean(burden_aps):.4f}+-{np.std(burden_aps):.4f}", "")

summary = pd.DataFrame(rows)
summary.to_csv(os.path.join(BASE, "reports", "16_structure_uncertainty_results.csv"), index=False)
print("\nSaved: reports/16_structure_uncertainty_results.csv")
print(summary.to_string(index=False))
