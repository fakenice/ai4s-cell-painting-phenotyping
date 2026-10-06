# -*- coding: utf-8 -*-
"""Stage 11 - P0 Shortboard experiments (structural part): evaluation disaggregation,
descaffolded fingerprints, soft-grouped CV, and task-attribute quantification.

P0-1  Evaluation disaggregation (maskB, trt vs all controls, 768 wells / 303 cpds)
  (a) within-scaffold vs cross-scaffold CV decomposition (Murcko scaffold key in train?)
  (b) original ECFP4 vs descaffolded ECFP4 (Bemis-Murcko scaffold atoms removed)
      under (i) maskA stratified 5-fold CV and (ii) maskB scaffold-grouped CV (Tanimoto>0.5)
P0-2  Soft-grouped CV (maskB): hard Murcko-scaffold groups vs Tanimoto-threshold soft
      connected-component groups (tau=0.6 / 0.4) vs Stage-6 fingerprint clustering (0.5)
P0-3  Task-attribute quantification: ECFP4 Tanimoto distance of DMSO vs all 303 compounds,
      compounds-vs-compounds reference distribution, statistical summary + figure.
Outputs: reports/19_stage11_p0_summary.json, reports/19_stage11_p0_cv_results.csv,
         reports/19_stage11_p0_fp_distance_stats.csv,
         reports/figures/29a_eval_disaggregation.png, 29b_soft_grouped_cv.png,
         29c_fp_distance_distribution.png (+ github_repo/figures copies)
"""
import os, json, glob, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist, squareform
from sklearn.model_selection import StratifiedKFold, GroupKFold
from sklearn.metrics import roc_auc_score, average_precision_score, accuracy_score
from scipy.stats import mannwhitneyu
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem.Scaffolds import MurckoScaffold

RANDOM_STATE = 42
N_SPLITS = 5
N_EST = 200
MAX_DEPTH = 3
LR = 0.05
SUB = 0.8
COL = 0.6
FP_RADIUS = 2
FP_NBITS = 1024
FP_NBITS_TASK = 2048
N_JOBS = 4

BASE = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science"
DATA = os.path.join(BASE, "data")
REPO = os.path.join(BASE, "github_repo")
FIG = os.path.join(REPO, "reports", "figures")
FIG_ROOT = os.path.join(REPO, "figures")
REPORTS = os.path.join(REPO, "reports")
os.makedirs(FIG, exist_ok=True)
os.makedirs(FIG_ROOT, exist_ok=True)
os.makedirs(REPORTS, exist_ok=True)

FEATURE_PREFIXES = ("Cells_", "Cytoplasm_", "Nuclei_")
MASKB_PLATES = ["BR00116991", "BR00116992"]


def xgb_clf():
    import xgboost as xgb
    return xgb.XGBClassifier(
        n_estimators=N_EST, max_depth=MAX_DEPTH, learning_rate=LR,
        subsample=SUB, colsample_bytree=COL, eval_metric="logloss",
        random_state=RANDOM_STATE, n_jobs=N_JOBS,
    )


def load_profiles():
    files = [f for f in glob.glob(os.path.join(DATA, "profiles", "*.csv.gz"))
             if any(p in os.path.basename(f) for p in MASKB_PLATES)]
    frames = [pd.read_csv(f) for f in sorted(files)]
    return pd.concat(frames, ignore_index=True)


def morgan_fp(mol, nbits=FP_NBITS):
    gen = AllChem.GetMorganGenerator(radius=FP_RADIUS, fpSize=nbits)
    return np.fromiter((int(b) for b in gen.GetFingerprint(mol).ToBitString()),
                       dtype=np.float32, count=nbits)


def descaffold_smiles(smiles):
    """Remove Bemis-Murcko scaffold atoms, return SMILES of largest remaining fragment
    (side chains / substituents), or None when nothing separable remains."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    scaff = MurckoScaffold.GetScaffoldForMol(mol)
    scaff_atoms = set()
    for m in mol.GetSubstructMatches(scaff, uniquify=True, useChirality=False):
        scaff_atoms.update(m)
    if not scaff_atoms or len(scaff_atoms) >= mol.GetNumAtoms():
        return None
    rw = Chem.RWMol(mol)
    for idx in sorted(scaff_atoms, reverse=True):
        rw.RemoveAtom(idx)
    frag = rw.GetMol()
    try:
        Chem.SanitizeMol(frag)
    except Exception:
        return None
    frags = Chem.GetMolFrags(frag, asMols=True)
    if not frags:
        return None
    largest = max(frags, key=lambda m: m.GetNumAtoms())
    if largest.GetNumAtoms() == 0:
        return None
    return Chem.MolToSmiles(largest)


def scaffold_key(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    sc = MurckoScaffold.GetScaffoldForMol(mol)
    return Chem.MolToSmiles(sc)


def safe_auc(y, p):
    if len(y) < 2 or np.unique(y).size < 2:
        return float("nan")
    return float(roc_auc_score(y, p))


def run_skf(X, y, name, feature_name="pheno+fp"):
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    y = y.astype(int)
    yp = np.zeros(len(y))
    for tr, te in skf.split(X, y):
        clf = xgb_clf()
        clf.fit(X[tr], y[tr])
        yp[te] = clf.predict_proba(X[te])[:, 1]
    return {"name": name, "feature": feature_name, "auc": safe_auc(y, yp),
            "ap": float(average_precision_score(y, yp)),
            "acc": float(accuracy_score(y, (yp >= 0.5).astype(int))), "n": int(len(y))}


def run_group_cv(X, y, groups, name, feature_name="pheno+fp"):
    gkf = GroupKFold(n_splits=N_SPLITS)
    y = y.astype(int)
    yp = np.zeros(len(y))
    skipped = 0
    for tr, te in gkf.split(X, y, groups):
        clf = xgb_clf()
        clf.fit(X[tr], y[tr])
        yp[te] = clf.predict_proba(X[te])[:, 1]
    return {"name": name, "feature": feature_name, "auc": safe_auc(y, yp),
            "ap": float(average_precision_score(y, yp)),
            "acc": float(accuracy_score(y, (yp >= 0.5).astype(int))), "n": int(len(y)),
            "folds_skipped": skipped}


def connected_components(sim_mat, tau, labels):
    """Union-find connected components where Tanimoto >= tau."""
    n = sim_mat.shape[0]
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for i in range(n):
        for j in range(i + 1, n):
            if sim_mat[i, j] >= tau:
                union(i, j)
    comp = {}
    for i in range(n):
        r = find(i)
        comp.setdefault(r, []).append(i)
    groups = np.zeros(n, dtype=int)
    for gi, idxs in enumerate(comp.values()):
        for i in idxs:
            groups[i] = gi
    return groups


def main():
    print("load profiles ...")
    prof = load_profiles()
    feat_cols = [c for c in prof.columns if c.startswith(FEATURE_PREFIXES)]
    print("wells:", len(prof), "features:", len(feat_cols))

    # ---- compound-level structures ----
    trt_mask = prof["Metadata_pert_type"].values == "trt"
    dmso_mask = prof["Metadata_pert_iname"].values == "DMSO"
    ctrl_mask = prof["Metadata_pert_type"].values == "control"
    maskA = trt_mask | dmso_mask
    maskB = trt_mask | ctrl_mask
    print("maskA:", maskA.sum(), "maskB:", maskB.sum())

    uniq = prof.drop_duplicates("Metadata_pert_iname")
    name2row = {r.Metadata_pert_iname: r for r in uniq.itertuples()}

    fp_cache, scaff_cache, desfp_cache = {}, {}, {}
    for name in sorted(name2row):
        smi = getattr(name2row[name], "Metadata_smiles", None)
        if not smi or (isinstance(smi, float) and math.isnan(smi)):
            fp_cache[name] = None
            continue
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            fp_cache[name] = None
            continue
        fp_cache[name] = morgan_fp(mol, FP_NBITS)
        scaff_cache[name] = scaffold_key(smi)
        dsm = descaffold_smiles(smi)
        desfp_cache[name] = morgan_fp(Chem.MolFromSmiles(dsm)) if dsm else None
    n_fp = sum(1 for v in fp_cache.values() if v is not None)
    n_scaff = sum(1 for v in scaff_cache.values() if v is not None)
    n_desfp = sum(1 for v in desfp_cache.values() if v is not None)
    print(f"ECFP4 ok {n_fp}/{len(name2row)}, scaffold ok {n_scaff}, descaffolded ok {n_desfp}")

    # ---- well-level matrices (maskB universe for group CV, maskA for stratified CV) ----
    def build_well_X(mask, feat, fp_src, include_fp=True):
        Xp = prof.loc[mask, feat_cols].values.astype(np.float64)
        Xp = (Xp - Xp.mean(0)) / (Xp.std(0) + 1e-8)
        Xf = np.zeros((mask.sum(), FP_NBITS), dtype=np.float32)
        names = prof.loc[mask, "Metadata_pert_iname"].values
        for i, nm in enumerate(names):
            v = fp_src.get(nm)
            Xf[i] = v if v is not None else np.zeros(FP_NBITS, dtype=np.float32)
        if include_fp:
            return np.hstack([Xp, Xf]), names
        return Xp, names

    # ---- P0-1a within vs cross scaffold decomposition (maskB, compound-grouped CV) ----
    print("\n[P0-1a] within/cross scaffold decomposition (maskB, compound-grouped CV)")
    X_both, names_b = build_well_X(maskB, feat_cols, fp_cache, include_fp=True)
    X_pheno_b, _ = build_well_X(maskB, feat_cols, fp_cache, include_fp=False)
    yB = trt_mask[maskB].astype(int)
    uniq_b = sorted(set(names_b))
    grp_by_compound = {nm: i for i, nm in enumerate(uniq_b)}
    groups_b = np.array([grp_by_compound[nm] for nm in names_b])

    disag = {}
    for fname, X in (("pheno+fp", X_both), ("pheno-only", X_pheno_b)):
        gkf = GroupKFold(n_splits=5)
        yp = np.zeros(len(yB))
        within_idx, cross_idx = [], []
        for tr, te in gkf.split(X, yB, groups_b):
            clf = xgb_clf()
            clf.fit(X[tr], yB[tr])
            yp[te] = clf.predict_proba(X[te])[:, 1]
            train_names = set(names_b[tr])
            train_scaffs = {scaff_cache.get(t) for t in train_names}
            for i in te:
                nm = names_b[i]
                sk = scaff_cache.get(nm)
                if sk is not None and sk in train_scaffs:
                    within_idx.append(i)
                else:
                    cross_idx.append(i)
        disag[fname] = {
            "overall_auc": safe_auc(yB, yp),
            "within_auc": safe_auc(yB[within_idx], yp[within_idx]),
            "cross_auc": safe_auc(yB[cross_idx], yp[cross_idx]),
            "n_within": int(len(within_idx)),
            "n_cross": int(len(cross_idx)),
            "overall_ap": float(average_precision_score(yB, yp)),
        }
        print(f"  {fname}: overall AUC={disag[fname]['overall_auc']:.4f} "
              f"within={disag[fname]['within_auc']:.4f} (n={len(within_idx)}) "
              f"cross={disag[fname]['cross_auc']:.4f} (n={len(cross_idx)})")

    # ---- P0-1b descaffolded fingerprint CV ----
    print("\n[P0-1b] original vs descaffolded ECFP4")
    # maskA stratified 5-fold (reproduces Stage-6 setup)
    X_pheno_a, names_a = build_well_X(maskA, feat_cols, fp_cache, include_fp=False)
    X_fp_orig_a = np.zeros((maskA.sum(), FP_NBITS), dtype=np.float32)
    X_fp_des_a = np.zeros((maskA.sum(), FP_NBITS), dtype=np.float32)
    for i, nm in enumerate(names_a):
        v_o = fp_cache.get(nm)
        v_d = desfp_cache.get(nm)
        X_fp_orig_a[i] = v_o if v_o is not None else np.zeros(FP_NBITS, dtype=np.float32)
        X_fp_des_a[i] = v_d if v_d is not None else np.zeros(FP_NBITS, dtype=np.float32)
    yA = trt_mask[maskA].astype(int)
    cv_a = []
    for fname, X in (("fp-orig", X_fp_orig_a), ("fp-descaffolded", X_fp_des_a)):
        cv_a.append(run_skf(X, yA, "maskA_trt_vs_DMSO", fname))
        print("  maskA", fname, "AUC=%.4f AP=%.4f" % (cv_a[-1]["auc"], cv_a[-1]["ap"]))
    for fname, Xf in (("fp-orig", X_fp_orig_a), ("fp-descaffolded", X_fp_des_a)):
        cv_a.append(run_skf(np.hstack([X_pheno_a, Xf]), yA, "maskA_trt_vs_DMSO", "pheno+" + fname))
        print("  maskA pheno+" + fname, "AUC=%.4f AP=%.4f" % (cv_a[-1]["auc"], cv_a[-1]["ap"]))

    # maskB scaffold-grouped CV (Tanimoto>0.5 clustering as Stage 6)
    X_fp_orig_b = np.zeros((maskB.sum(), FP_NBITS), dtype=np.float32)
    X_fp_des_b = np.zeros((maskB.sum(), FP_NBITS), dtype=np.float32)
    for i, nm in enumerate(names_b):
        v_o = fp_cache.get(nm)
        v_d = desfp_cache.get(nm)
        X_fp_orig_b[i] = v_o if v_o is not None else np.zeros(FP_NBITS, dtype=np.float32)
        X_fp_des_b[i] = v_d if v_d is not None else np.zeros(FP_NBITS, dtype=np.float32)
    # cluster groups on original fp (reuse 05: Tanimoto>0.5)
    ufp = np.vstack([fp_cache[nm] for nm in uniq_b if fp_cache.get(nm) is not None])
    unames = [nm for nm in uniq_b if fp_cache.get(nm) is not None]
    dist = pdist(ufp, metric="jaccard")
    Z = linkage(dist, method="single")
    grp = fcluster(Z, t=0.5, criterion="distance")
    uniq2grp = {nm: gi for nm, gi in zip(unames, grp)}
    well_grp05 = np.array([uniq2grp[nm] for nm in names_b])
    n_g05 = len(set(well_grp05))
    print("  maskB Tanimoto>0.5 scaffold groups:", n_g05)
    for fname, Xf in (("fp-orig", X_fp_orig_b), ("fp-descaffolded", X_fp_des_b)):
        cv_a.append(run_group_cv(Xf, yB, well_grp05, "maskB_scaffold_groupCV", fname))
        print("  maskB scaffold-groupCV", fname, "AUC=%.4f AP=%.4f" % (cv_a[-1]["auc"], cv_a[-1]["ap"]))
    for fname, Xf in (("fp-orig", X_fp_orig_b), ("fp-descaffolded", X_fp_des_b)):
        cv_a.append(run_group_cv(np.hstack([X_pheno_b, Xf]), yB, well_grp05, "maskB_scaffold_groupCV", "pheno+" + fname))
        print("  maskB scaffold-groupCV pheno+" + fname, "AUC=%.4f AP=%.4f" % (cv_a[-1]["auc"], cv_a[-1]["ap"]))

    # ---- P0-2 soft-grouped CV ----
    print("\n[P0-2] soft-grouped CV (Murcko scaffold Tanimoto)")
    scaffold_smiles = {nm: scaff_cache.get(nm) for nm in uniq_b}
    valid_sc = {nm: s for nm, s in scaffold_smiles.items() if s is not None}
    sc_names = sorted(valid_sc)
    sc_fp = np.vstack([morgan_fp(Chem.MolFromSmiles(valid_sc[nm]), FP_NBITS) for nm in sc_names])
    sc_sim = 1.0 - squareform(pdist(sc_fp, metric="jaccard"))
    sc_idx = {nm: i for i, nm in enumerate(sc_names)}

    hard_grp = np.zeros(len(names_b), dtype=int)
    seen = {}
    for i, nm in enumerate(names_b):
        s = valid_sc.get(nm)
        if s is None:
            hard_grp[i] = -1
            continue
        if s not in seen:
            seen[s] = len(seen)
        hard_grp[i] = seen[s]
    soft_grp = {}
    for tau in (0.6, 0.4):
        g = connected_components(sc_sim, tau, sc_names)
        soft_grp[tau] = np.array([g[sc_idx[nm]] if nm in sc_idx else -1 for nm in names_b])
        print(f"  tau={tau}: components={len(set(g))} (valid {sum(1 for x in g if x>=0)})")

    soft_rows = []
    for fname, X in (("pheno+fp", X_both), ("pheno-only", X_pheno_b)):
        for gname, glab in (("hard_scaffold", hard_grp), ("soft_tau0.6", soft_grp[0.6]),
                            ("soft_tau0.4", soft_grp[0.4]), ("fpcluster_0.5", well_grp05)):
            r = run_group_cv(X, yB, glab, "maskB_groupCV_" + gname, fname)
            soft_rows.append(r)
            print("  [%s] %s AUC=%.4f AP=%.4f" % (gname, fname, r["auc"], r["ap"]))
    cv_a.extend(soft_rows)

    # ---- P0-3 task attribute quantification ----
    print("\n[P0-3] DMSO vs compounds ECFP4 distance distribution")
    dmso_name = "DMSO"
    dmso_smi = name2row.get(dmso_name)
    dmso_mol = Chem.MolFromSmiles(dmso_smi.Metadata_smiles) if dmso_smi is not None else None
    fp_dmso = morgan_fp(dmso_mol, FP_NBITS_TASK) if dmso_mol is not None else None
    comp_names = [nm for nm in uniq_b if nm != dmso_name and fp_cache.get(nm) is not None]
    # recompute 2048-bit for task quantification
    fp_2048 = {}
    for nm in uniq_b:
        r = name2row.get(nm)
        smi = getattr(r, "Metadata_smiles", None) if r is not None else None
        mol = Chem.MolFromSmiles(smi) if smi else None
        fp_2048[nm] = morgan_fp(mol, FP_NBITS_TASK) if mol is not None else None
    dmso_sim = {}
    for nm in comp_names:
        v = fp_2048.get(nm)
        if v is None or fp_dmso is None:
            continue
        inter = float(np.dot(v, fp_dmso)); union = float(np.count_nonzero(v) + np.count_nonzero(fp_dmso) - inter)
        dmso_sim[nm] = inter / union if union > 0 else 0.0
    dmso_dists = np.array([1.0 - s for s in dmso_sim.values()])
    # compound-compound reference: sample all pairs among 302 compounds (excluding DMSO)
    cvec = np.vstack([fp_2048[nm] for nm in comp_names])
    cnames = comp_names
    n_c = len(cnames)
    # pair Tanimoto via bit dot products (sparse-ish but 302x302 fine)
    bit_dot = cvec @ cvec.T
    pops = cvec.sum(1)
    union = pops[:, None] + pops[None, :] - bit_dot
    with np.errstate(divide="ignore", invalid="ignore"):
        pair_sim = bit_dot / np.where(union > 0, union, 1)
    np.fill_diagonal(pair_sim, 0.0)
    iu = np.triu_indices(n_c, k=1)
    cc_dists = 1.0 - pair_sim[iu]
    u_stat, p_val = mannwhitneyu(dmso_dists, cc_dists, alternative="two-sided")
    stats_p3 = {
        "n_dmso_vs_comp": int(len(dmso_dists)),
        "dmso_dist_mean": float(dmso_dists.mean()),
        "dmso_dist_median": float(np.median(dmso_dists)),
        "dmso_dist_min": float(dmso_dists.min()),
        "dmso_dist_max": float(dmso_dists.max()),
        "dmso_dist_q10": float(np.percentile(dmso_dists, 10)),
        "dmso_dist_q90": float(np.percentile(dmso_dists, 90)),
        "cc_dist_mean": float(cc_dists.mean()),
        "cc_dist_median": float(np.median(cc_dists)),
        "cc_dist_q10": float(np.percentile(cc_dists, 10)),
        "cc_dist_q90": float(np.percentile(cc_dists, 90)),
        "mannwhitney_u_p": float(p_val),
        "dmso_nearest_neighbor": min(dmso_sim, key=dmso_sim.get),
        "dmso_nearest_sim": float(max(dmso_sim.values())),
        "n_pairs_cc": int(len(cc_dists)),
    }
    print("  DMSO dist: mean=%.3f median=%.3f [%.3f, %.3f] | cc dist mean=%.3f median=%.3f | MW p=%.2e" % (
        stats_p3["dmso_dist_mean"], stats_p3["dmso_dist_median"],
        stats_p3["dmso_dist_min"], stats_p3["dmso_dist_max"],
        stats_p3["cc_dist_mean"], stats_p3["cc_dist_median"], stats_p3["mannwhitney_u_p"]))

    # ---- figures ----
    # 29a: evaluation disaggregation + descaffolded CV
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    labels = ["pheno+fp\noverall", "pheno+fp\nwithin", "pheno+fp\ncross", "pheno-only\noverall", "pheno-only\nwithin", "pheno-only\ncross"]
    vals = [disag["pheno+fp"]["overall_auc"], disag["pheno+fp"]["within_auc"], disag["pheno+fp"]["cross_auc"],
            disag["pheno-only"]["overall_auc"], disag["pheno-only"]["within_auc"], disag["pheno-only"]["cross_auc"]]
    colors = ["#4C72B0", "#55A868", "#C44E52", "#4C72B0", "#55A868", "#C44E52"]
    ax = axes[0]
    ax.bar(range(len(vals)), vals, color=colors)
    ax.set_xticks(range(len(vals))); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("OOF AUC"); ax.set_ylim(0, 1.05)
    ax.axhline(0.5, ls="--", color="grey", lw=0.8)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.02, f"{v:.3f}", ha="center", fontsize=8)
    ax.set_title("P0-1a within/cross-scaffold decomposition (maskB)\ncompound-grouped CV, OOF")
    names_cv = [r["name"] + "|" + r["feature"] for r in cv_a]
    ax2 = axes[1]
    sel = [r for r in cv_a if r["name"] == "maskA_trt_vs_DMSO" and r["feature"] in ("fp-orig", "fp-descaffolded", "pheno+fp-orig", "pheno+fp-descaffolded")]
    x = np.arange(len(sel)); aucs = [r["auc"] for r in sel]
    ax2.bar(x, aucs, color=["#4C72B0", "#C44E52", "#4C72B0", "#C44E52"])
    ax2.set_xticks(x); ax2.set_xticklabels([r["feature"] for r in sel], fontsize=9)
    ax2.set_ylabel("CV AUC"); ax2.set_ylim(0, 1.05)
    ax2.axhline(0.5, ls="--", color="grey", lw=0.8)
    for i, v in enumerate(aucs):
        ax2.text(i, v + 0.02, f"{v:.3f}", ha="center", fontsize=9)
    ax2.set_title("P0-1b ECFP4 vs descaffolded ECFP4 (maskA 5-fold)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "29a_eval_disaggregation.png"), dpi=150)
    fig.savefig(os.path.join(FIG_ROOT, "29a_eval_disaggregation.png"), dpi=150)
    plt.close(fig)

    # 29b: soft-grouped CV
    fig, ax = plt.subplots(figsize=(8, 5))
    gnames = ["hard_scaffold", "soft_tau0.6", "soft_tau0.4", "fpcluster_0.5"]
    gdisplay = ["hard\n(Murcko)", "soft tau=0.6", "soft tau=0.4", "fp-cluster\n(Tanimoto>0.5)"]
    for j, fn in enumerate(("pheno+fp", "pheno-only")):
        vals = [next(r["auc"] for r in soft_rows if r["name"] == "maskB_groupCV_" + g and r["feature"] == fn) for g in gnames]
        ax.plot(range(len(gnames)), vals, marker="o", label=fn)
        for i, v in enumerate(vals):
            ax.text(i + (0.06 if j else -0.06), v + 0.01, f"{v:.3f}", fontsize=8, ha="center")
    ax.set_xticks(range(len(gnames))); ax.set_xticklabels(gdisplay)
    ax.set_ylabel("GroupKFold(5) OOF AUC (maskB)")
    ax.set_ylim(0.2, 0.9); ax.axhline(0.5, ls="--", color="grey", lw=0.8)
    ax.legend(); ax.set_title("P0-2 soft-grouped CV: scaffold Tanimoto thresholds")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "29b_soft_grouped_cv.png"), dpi=150)
    fig.savefig(os.path.join(FIG_ROOT, "29b_soft_grouped_cv.png"), dpi=150)
    plt.close(fig)

    # 29c: fingerprint distance distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(dmso_dists, bins=40, alpha=0.6, color="#C44E52", label=f"DMSO vs {len(dmso_dists)} compounds")
    ax.hist(cc_dists, bins=60, alpha=0.4, color="#4C72B0", label=f"compound-compound pairs (n={len(cc_dists)})")
    ax.axvline(stats_p3["dmso_dist_mean"], color="#C44E52", ls="--", lw=1.2, label="DMSO mean")
    ax.axvline(stats_p3["cc_dist_mean"], color="#4C72B0", ls="--", lw=1.2, label="cc mean")
    ax.set_xlabel("1 - Tanimoto (ECFP4, r=2, 2048 bits)")
    ax.set_ylabel("count"); ax.legend()
    ax.set_title("P0-3 trt-vs-DMSO fingerprint distance is naturally separable\n(DMSO mean=%.3f vs cc mean=%.3f, MW p=%.1e)" % (
        stats_p3["dmso_dist_mean"], stats_p3["cc_dist_mean"], stats_p3["mannwhitney_u_p"]))
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "29c_fp_distance_distribution.png"), dpi=150)
    fig.savefig(os.path.join(FIG_ROOT, "29c_fp_distance_distribution.png"), dpi=150)
    plt.close(fig)

    # ---- outputs ----
    rows = []
    for r in cv_a:
        rows.append({"name": r["name"], "feature": r["feature"], "auc": r["auc"],
                     "ap": r["ap"], "acc": r["acc"], "n": r["n"]})
    pd.DataFrame(rows).to_csv(os.path.join(REPORTS, "19_stage11_p0_cv_results.csv"), index=False)
    pd.DataFrame([{"metric": k, "value": v} for k, v in stats_p3.items()]).to_csv(
        os.path.join(REPORTS, "19_stage11_p0_fp_distance_stats.csv"), index=False)

    summary = {
        "p0_1a_within_cross": disag,
        "p0_1b_cv": {f"{r['name']}|{r['feature']}": {"auc": r["auc"], "ap": r["ap"], "acc": r["acc"]} for r in cv_a},
        "p0_2_soft_group_cv": {f"{r['name']}|{r['feature']}": {"auc": r["auc"], "ap": r["ap"]} for r in soft_rows},
        "p0_3_fp_distance": stats_p3,
        "descaffold_coverage": {"n_total": len(name2row), "n_fp": n_fp, "n_scaffold": n_scaff,
                                "n_descaffolded": n_desfp},
        "scaffold_groups_Tanimoto0.5": int(n_g05),
    }
    with open(os.path.join(REPORTS, "19_stage11_p0_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\nDONE. summary -> reports/19_stage11_p0_summary.json")


if __name__ == "__main__":
    main()
