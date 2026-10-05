# -*- coding: utf-8 -*-
"""Stage 10 - Experiment 2: Harmony batch correction (well position / plate) on 904 morphological features
Re-runs the Stage 5 main model (pheno+fp XGBoost) under the exact Stage 5 protocol:
  - maskA (trt vs DMSO, 648 wells): 5-fold stratified OOF (run_cv)
  - maskB (trt vs all controls, 768 wells): scaffold-grouped CV (Tanimoto>0.5, run_group_cv)
Compares AUC/AP/ACC before vs after Harmony correction (covariates: Metadata_Plate + well Row/Col).
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import StratifiedKFold, GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score, accuracy_score
from sklearn.decomposition import PCA
from rdkit import Chem
from rdkit.Chem import AllChem
import xgboost as xgb

RANDOM_STATE = 42
N_SPLITS = 5
N_ESTIMATORS = 200
MAX_DEPTH = 3
LEARNING_RATE = 0.05
SUBSAMPLE = 0.8
COLSAMPLE_BYTREE = 0.6
N_JOBS = 4
FP_RADIUS = 2
FP_NBITS = 1024
DPI = 150

BASE = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science"
DATA = os.path.join(BASE, "data")
REPO = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science\github_repo"
FIG = os.path.join(REPO, "reports", "figures")
os.makedirs(FIG, exist_ok=True)
REPORTS = os.path.join(REPO, "reports")
os.makedirs(REPORTS, exist_ok=True)


def load_profiles():
    plate_files = sorted(f for f in os.listdir(os.path.join(DATA, "profiles")) if f.endswith(".csv.gz"))
    frames = [pd.read_csv(os.path.join(DATA, "profiles", f)) for f in plate_files]
    return pd.concat(frames, ignore_index=True)


def xgb_clf():
    return xgb.XGBClassifier(
        n_estimators=N_ESTIMATORS, max_depth=MAX_DEPTH, learning_rate=LEARNING_RATE,
        subsample=SUBSAMPLE, colsample_bytree=COLSAMPLE_BYTREE, eval_metric="logloss",
        random_state=RANDOM_STATE, n_jobs=N_JOBS,
    )


def run_cv(X, y, name):
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    y = y.astype(int)
    y_prob = np.zeros(len(y))
    for tr, te in skf.split(X, y):
        clf = xgb_clf()
        clf.fit(X[tr], y[tr])
        y_prob[te] = clf.predict_proba(X[te])[:, 1]
    auc = roc_auc_score(y, y_prob); ap = average_precision_score(y, y_prob)
    acc = accuracy_score(y, (y_prob >= 0.5).astype(int))
    print(f"[{name}] AUC={auc:.4f} AP={ap:.4f} ACC={acc:.4f} (n_pos={y.sum()}, n={len(y)})")
    return {"name": name, "auc": float(auc), "ap": float(ap), "acc": float(acc),
            "n_pos": int(y.sum()), "n": int(len(y))}


def run_group_cv(X, y, groups, name):
    gkf = GroupKFold(n_splits=5)
    y_prob = np.full(len(y), np.nan); skipped = 0
    for tr, te in gkf.split(X, y, groups=groups):
        if len(np.unique(y[te])) < 2 or len(np.unique(y[tr])) < 2:
            skipped += 1; continue
        clf = xgb_clf(); clf.fit(X[tr], y[tr])
        y_prob[te] = clf.predict_proba(X[te])[:, 1]
    valid = ~np.isnan(y_prob)
    if valid.sum() == 0:
        print(f"[{name}] no evaluable folds"); return None
    auc = roc_auc_score(y[valid], y_prob[valid]); ap = average_precision_score(y[valid], y_prob[valid])
    acc = accuracy_score(y[valid], (y_prob[valid] >= 0.5).astype(int))
    print(f"[{name}] GROUP-CV AUC={auc:.4f} AP={ap:.4f} ACC={acc:.4f} (folds_skipped={skipped}, valid_n={valid.sum()})")
    return {"name": name, "auc": float(auc), "ap": float(ap), "acc": float(acc),
            "folds_skipped": skipped, "valid_n": int(valid.sum())}


def main():
    prof = load_profiles()
    feat_cols = [c for c in prof.columns if not c.startswith("Metadata")]
    compound = prof.dropna(subset=["Metadata_pert_iname"]).copy()
    fp_features = compound.groupby("Metadata_pert_iname")[feat_cols].mean()
    scaler = StandardScaler().fit(fp_features.values)
    X_pheno_well = scaler.transform(compound[feat_cols].values)

    # ECFP4 fingerprints
    meta = pd.read_csv(os.path.join(DATA, "metadata", "JUMP-Target-1_compound_metadata.tsv"), sep="\t")
    meta_dedup = meta.drop_duplicates(subset=["pert_iname"]).set_index("pert_iname")
    smiles_map = meta_dedup["smiles"].to_dict()
    gen = AllChem.GetMorganGenerator(radius=FP_RADIUS, fpSize=FP_NBITS)
    rows_fp = []
    for name in fp_features.index:
        smi = smiles_map.get(name, None)
        mol = Chem.MolFromSmiles(smi) if smi else None
        if mol is None:
            rows_fp.append(np.zeros(FP_NBITS, dtype=np.float32))
        else:
            bits = gen.GetFingerprint(mol).ToBitString()
            rows_fp.append(np.fromiter((int(b) for b in bits), dtype=np.float32, count=FP_NBITS))
    X_fp = np.vstack(rows_fp)
    name2idx = {n: i for i, n in enumerate(fp_features.index)}
    X_fp_well = np.zeros((len(compound), FP_NBITS), dtype=np.float32)
    for i, nm in enumerate(compound["Metadata_pert_iname"].values):
        j = name2idx.get(nm, -1)
        if j >= 0:
            X_fp_well[i] = X_fp[j]

    trt_mask = (compound["Metadata_pert_type"].values == "trt")
    dmso_mask = (compound["Metadata_pert_iname"].values == "DMSO")
    ctrl_mask = (compound["Metadata_pert_type"].values == "control")
    maskA = trt_mask | dmso_mask
    maskB = trt_mask | ctrl_mask
    print(f"maskA trt_vs_DMSO wells={maskA.sum()} (trt={trt_mask[maskA].sum()}, dmso={dmso_mask[maskA].sum()})")
    print(f"maskB trt_vs_ctrl wells={maskB.sum()}")

    # Harmony covariates: plate + well position (categorical Row/Col; harmonypy only supports categorical covariates)
    def well_pos(df_well):
        row = df_well["Metadata_Well"].str[0]
        col = df_well["Metadata_Well"].str[1:].astype(int).astype(str).str.zfill(2)
        return pd.DataFrame({"Row": row.values, "Col": col.values}, index=df_well.index)

    def harmony_correct(X, mask, tag):
        from harmonypy import run_harmony
        import pandas as pd
        df_well = compound.loc[mask].copy()
        cov = pd.concat([df_well[["Metadata_Plate"]], well_pos(df_well)], axis=1)
        cov["Metadata_Plate"] = cov["Metadata_Plate"].astype(str)
        # harmonypy 0.0.9 relies on DataFrame.describe()['unique'] which pandas>=2.0 no longer emits
        _orig_describe = pd.DataFrame.describe
        def _patched_describe(self, *a, **k):
            res = _orig_describe(self, *a, **k)
            uniq = self.nunique(dropna=True)
            res.loc["unique"] = uniq.reindex(res.columns)
            return res
        pd.DataFrame.describe = _patched_describe
        try:
            ho = run_harmony(X[mask], cov, vars_use=["Metadata_Plate", "Row", "Col"], random_state=RANDOM_STATE)
        finally:
            pd.DataFrame.describe = _orig_describe
        Xm = np.asarray(ho.result()).T  # result is (d, N); transpose back to (N, d)
        print(f"harmony {tag}: {Xm.shape[0]} cells x {Xm.shape[1]} features")
        return Xm

    results = []

    # ---- maskA: trt vs DMSO, 5-fold OOF, pheno+fp ----
    yA = trt_mask[maskA].astype(int)
    XbA = np.hstack([X_pheno_well[maskA], X_fp_well[maskA]])
    r0 = run_cv(XbA, yA, "A_before_harmony_pheno+fp")
    results.append(r0)
    XA_harm = harmony_correct(X_pheno_well, maskA, "maskA")
    XbA_h = np.hstack([XA_harm, X_fp_well[maskA]])
    r1 = run_cv(XbA_h, yA, "A_after_harmony_pheno+fp")
    results.append(r1)

    # ---- maskB: trt vs all controls, scaffold-grouped CV ----
    uniq_names = list(dict.fromkeys(compound.loc[maskB, "Metadata_pert_iname"].values))
    uniq_fp = np.vstack([X_fp[name2idx[n]] for n in uniq_names])
    from scipy.cluster.hierarchy import linkage, fcluster
    from scipy.spatial.distance import pdist
    dist = pdist(uniq_fp, metric="jaccard")
    Z = linkage(dist, method="single")
    grp = fcluster(Z, t=0.5, criterion="distance")
    uniq2grp = {n: int(g) for n, g in zip(uniq_names, grp)}
    well_grp = np.array([uniq2grp[n] for n in compound.loc[maskB, "Metadata_pert_iname"].values])
    yB = trt_mask[maskB].astype(int)
    print(f"scaffold groups: {len(set(well_grp))} from {len(uniq_names)} compounds")
    XbB = np.hstack([X_pheno_well[maskB], X_fp_well[maskB]])
    g0 = run_group_cv(XbB, yB, well_grp, "B_before_harmony_pheno+fp_groupCV")
    results.append(g0)
    XB_harm = harmony_correct(X_pheno_well, maskB, "maskB")
    XbB_h = np.hstack([XB_harm, X_fp_well[maskB]])
    g1 = run_group_cv(XbB_h, yB, well_grp, "B_after_harmony_pheno+fp_groupCV")
    results.append(g1)

    df = pd.DataFrame(results)
    df.to_csv(os.path.join(REPORTS, "18_stage10_harmony_results.csv"), index=False)
    print(df.to_string(index=False))

    # ---- Figure 28b: PCA of 904 features before/after, colored by plate & well position ----
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    ax = axes.flatten()
    for ai, Xmat, tag in zip([0, 1], [X_pheno_well[maskA], XA_harm], ["Before Harmony", "After Harmony"]):
        pca = PCA(n_components=2, random_state=RANDOM_STATE).fit(Xmat)
        C = pca.transform(Xmat)
        well_meta = compound.loc[maskA]
        for plate in sorted(well_meta["Metadata_Plate"].unique()):
            m = well_meta["Metadata_Plate"].values == plate
            ax[ai].scatter(C[m, 0], C[m, 1], s=14, alpha=0.75, label=plate)
        ax[ai].set_title(f"{tag} (colored by plate)")
        ax[ai].legend(fontsize=7, loc="best")
        ax[ai].set_xlabel("PC1"); ax[ai].set_ylabel("PC2")
    for ai, Xmat, tag in zip([2, 3], [X_pheno_well[maskA], XA_harm], ["Before Harmony", "After Harmony"]):
        pca = PCA(n_components=2, random_state=RANDOM_STATE).fit(Xmat)
        C = pca.transform(Xmat)
        well_meta = compound.loc[maskA]
        rows = well_pos(well_meta)["Row"].astype(str).str[0].map({c: i + 1 for i, c in enumerate("ABCDEFGH")}).values
        sc = ax[ai].scatter(C[:, 0], C[:, 1], c=rows, s=14, alpha=0.8, cmap="viridis")
        ax[ai].set_title(f"{tag} (colored by well row)")
        plt.colorbar(sc, ax=ax[ai], label="row index")
        ax[ai].set_xlabel("PC1"); ax[ai].set_ylabel("PC2")
    fig.suptitle("Stage 10 - Harmony batch correction on 904 features (trt vs DMSO, 648 wells)", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "28b_harmony_batch_correction.png"), dpi=DPI)
    plt.close(fig)
    print("saved:", os.path.join(FIG, "28b_harmony_batch_correction.png"))


if __name__ == "__main__":
    main()
