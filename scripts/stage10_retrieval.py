# -*- coding: utf-8 -*-
"""Stage 10 - Experiment 3: Phenotypic retrieval (replicate AP) and known target enrichment.
(a) Replicate retrieval: 904-feature well-level cosine similarity, query-well -> same-compound wells AP
    computed on maskA (trt vs DMSO, 648 wells), before vs after Harmony correction.
(b) Known target enrichment: compound-level profiles, pair cosine similarity; per-target AUROC
    (Mann-Whitney) + Fisher on top-10% similar pairs, BH-corrected.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler, normalize
from sklearn.metrics import average_precision_score, roc_auc_score
from scipy.stats import mannwhitneyu, fisher_exact
from statsmodels.stats.multitest import multipletests

RANDOM_STATE = 42
DPI = 150

BASE = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science"
DATA = os.path.join(BASE, "data")
REPO = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science\github_repo"
FIG = os.path.join(REPO, "reports", "figures")
os.makedirs(FIG, exist_ok=True)
REPORTS = os.path.join(REPO, "reports")


def load_profiles():
    plate_files = sorted(f for f in os.listdir(os.path.join(DATA, "profiles")) if f.endswith(".csv.gz"))
    frames = [pd.read_csv(os.path.join(DATA, "profiles", f)) for f in plate_files]
    return pd.concat(frames, ignore_index=True)


def well_ap_metrics(X, names):
    """well-level replicate retrieval AP (query well vs all other wells)."""
    Xn = normalize(X, norm="l2", axis=1)
    S = Xn @ Xn.T  # cosine similarity
    n = len(names)
    aps = np.zeros(n)
    npos = np.zeros(n)
    for i in range(n):
        scores = S[i].copy()
        scores[i] = -1e9  # exclude self (sklearn rejects inf)
        y = (names == names[i]).astype(int)
        y[i] = 0
        aps[i] = average_precision_score(y, scores)
        npos[i] = y.sum()
    mean_ap = float(aps.mean())
    mean_chance = float((npos / (n - 1)).mean())  # expected AP under random ordering
    # pair-level AUC: same compound vs different compound
    y_all = (names[:, None] == names[None, :]).astype(int)
    triu = np.triu_indices(n, k=1)
    pair_auc = roc_auc_score(y_all[triu], S[triu])
    return mean_ap, mean_chance, pair_auc, aps, npos


def main():
    prof = load_profiles()
    feat_cols = [c for c in prof.columns if not c.startswith("Metadata")]
    compound = prof.dropna(subset=["Metadata_pert_iname"]).copy()
    fp_features = compound.groupby("Metadata_pert_iname")[feat_cols].mean()
    scaler = StandardScaler().fit(fp_features.values)
    X_pheno_well = scaler.transform(compound[feat_cols].values)

    trt_mask = (compound["Metadata_pert_type"].values == "trt")
    dmso_mask = (compound["Metadata_pert_iname"].values == "DMSO")
    maskA = trt_mask | dmso_mask
    print(f"maskA wells={maskA.sum()} unique compounds={compound.loc[maskA,'Metadata_pert_iname'].nunique()}")

    # Harmony-corrected (same covariates/protocol as Experiment 2, maskA)
    import pandas as _pd
    from harmonypy import run_harmony
    df_well = compound.loc[maskA].copy()
    row = df_well["Metadata_Well"].str[0]
    col = df_well["Metadata_Well"].str[1:].astype(int).astype(str).str.zfill(2)
    cov = pd.concat([df_well[["Metadata_Plate"]], pd.DataFrame({"Row": row.values, "Col": col.values}, index=df_well.index)], axis=1)
    cov["Metadata_Plate"] = cov["Metadata_Plate"].astype(str)
    _orig_describe = _pd.DataFrame.describe
    def _patched_describe(self, *a, **k):
        res = _orig_describe(self, *a, **k)
        res.loc["unique"] = self.nunique(dropna=True).reindex(res.columns)
        return res
    _pd.DataFrame.describe = _patched_describe
    try:
        ho = run_harmony(X_pheno_well[maskA], cov, vars_use=["Metadata_Plate", "Row", "Col"], random_state=RANDOM_STATE)
    finally:
        _pd.DataFrame.describe = _orig_describe
    XA_harm = np.asarray(ho.result()).T

    namesA = compound.loc[maskA, "Metadata_pert_iname"].values
    before = well_ap_metrics(X_pheno_well[maskA], namesA)
    after = well_ap_metrics(XA_harm, namesA)
    print(f"RETRIEVAL before: meanAP={before[0]:.4f} chance={before[1]:.4f} pairAUC={before[2]:.4f}")
    print(f"RETRIEVAL after:  meanAP={after[0]:.4f} chance={after[1]:.4f} pairAUC={after[2]:.4f}")

    rows = [
        {"feature_set": "904 raw (before harmony)", "mean_replicate_AP": before[0], "chance_AP": before[1], "pair_AUC": before[2], "n_wells": int(maskA.sum())},
        {"feature_set": "904 harmony-corrected", "mean_replicate_AP": after[0], "chance_AP": after[1], "pair_AUC": after[2], "n_wells": int(maskA.sum())},
    ]
    pd.DataFrame(rows).to_csv(os.path.join(REPORTS, "18_stage10_retrieval_results.csv"), index=False)

    # ---- Figure 28c: replicate AP distribution before/after ----
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    axes[0].boxplot([before[3], after[3]], tick_labels=["Before", "After"], showmeans=True)
    axes[0].set_title("Replicate-retrieval AP per well"); axes[0].set_ylabel("AP")
    axes[0].axhline(before[1], color="gray", ls="--", lw=1, label=f"chance={before[1]:.3f}")
    axes[0].legend(fontsize=8)
    # similarity distributions: same compound pairs vs different compound pairs
    Xn = normalize(X_pheno_well[maskA], norm="l2", axis=1); S = Xn @ Xn.T
    n = len(namesA); triu = np.triu_indices(n, k=1)
    y_all = (namesA[:, None] == namesA[None, :]).astype(int)[triu]
    same = S[triu][y_all == 1]; diff = S[triu][y_all == 0]
    axes[1].hist(same, bins=40, alpha=0.6, label=f"same compound (n={len(same)})")
    axes[1].hist(diff, bins=40, alpha=0.5, label=f"different (n={len(diff)})")
    axes[1].set_title("Cosine similarity (raw 904 features)"); axes[1].legend(fontsize=8)
    Xn2 = normalize(XA_harm, norm="l2", axis=1); S2 = Xn2 @ Xn2.T
    same2 = S2[triu][y_all == 1]; diff2 = S2[triu][y_all == 0]
    axes[2].hist(same2, bins=40, alpha=0.6, label=f"same compound (n={len(same2)})")
    axes[2].hist(diff2, bins=40, alpha=0.5, label=f"different (n={len(diff2)})")
    axes[2].set_title("Cosine similarity (harmony-corrected)"); axes[2].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "28c_retrieval_replicate_ap.png"), dpi=DPI)
    plt.close(fig)
    print("saved:", os.path.join(FIG, "28c_retrieval_replicate_ap.png"))

    # ---- (b) known target enrichment (compound level, trt only) ----
    tgt = pd.read_csv(os.path.join(DATA, "metadata", "JUMP-Target-1_compound_metadata_targets.tsv"), sep="\t")
    tgt_map = dict(zip(tgt["pert_iname"], tgt["target_list"].fillna("")))
    trt_names = sorted(compound.loc[trt_mask, "Metadata_pert_iname"].unique())
    # compound-level profiles for trt
    Xc = scaler.transform(fp_features.loc[trt_names].values)
    Xcn = normalize(Xc, norm="l2", axis=1)
    Sc = Xcn @ Xcn.T
    m = len(trt_names)
    triu = np.triu_indices(m, k=1)
    sim_pairs = Sc[triu]
    n_pairs = len(sim_pairs)

    # shared-target labels per pair
    def targets_of(name):
        tl = tgt_map.get(name, "")
        return set(tl.split("|")) if tl else set()
    tgts = [targets_of(nm) for nm in trt_names]
    pair_shared = np.array([len(tgts[i] & tgts[j]) > 0 for i, j in zip(*triu)])
    auc_all = roc_auc_score(pair_shared, sim_pairs)
    u, p_all = mannwhitneyu(sim_pairs[pair_shared], sim_pairs[~pair_shared], alternative="greater")
    print(f"TARGET-ENRICH pair AUROC(shared>=1 target)={auc_all:.4f} p={p_all:.3e} shared_pairs={pair_shared.sum()}/{n_pairs}")

    # per-target enrichment
    target_sets = {}
    for i, nm in enumerate(trt_names):
        for t in tgts[i]:
            target_sets.setdefault(t, []).append(i)
    target_sets = {t: idx for t, idx in target_sets.items() if len(idx) >= 2}
    print(f"targets with >=2 compounds: {len(target_sets)}")

    rec = []
    topk = max(10, int(0.10 * n_pairs))
    top_idx = np.argsort(sim_pairs)[::-1][:topk]
    top_shared = pair_shared[top_idx]
    for t, idx in target_sets.items():
        idx = np.array(idx)
        in_mask = np.zeros(m, dtype=bool); in_mask[idx] = True
        pair_in = in_mask[triu[0]] & in_mask[triu[1]]
        if pair_in.sum() < 2:
            continue
        auc_t = roc_auc_score(pair_in, sim_pairs)
        u_t, p_t = mannwhitneyu(sim_pairs[pair_in], sim_pairs[~pair_in], alternative="greater")
        # Fisher: top-10% similar pairs contain target t?
        a = int((top_shared & pair_in[top_idx]).sum())
        b = int((pair_in[top_idx]).sum()) - a
        c = int(top_shared.sum()) - a
        d = n_pairs - topk - c - b
        odd, p_fish = fisher_exact([[a, b], [c, d]], alternative="greater")
        rec.append({"target": t, "n_compounds": int(len(idx)), "n_pairs_in": int(pair_in.sum()),
                    "pair_AUROC": float(auc_t), "mw_p": float(p_t), "fisher_top10_p": float(p_fish),
                    "top10_shared_pairs": int(a), "top10_in_pairs": int(b)})
    rec_df = pd.DataFrame(rec)
    if len(rec_df):
        rec_df["mw_p_bh"] = multipletests(rec_df["mw_p"].values, method="fdr_bh")[1]
        rec_df["fisher_p_bh"] = multipletests(rec_df["fisher_top10_p"].values, method="fdr_bh")[1]
        rec_df = rec_df.sort_values("pair_AUROC", ascending=False)
        rec_df.to_csv(os.path.join(REPORTS, "18_stage10_target_enrichment.csv"), index=False)
        n_sig_mw = int((rec_df["mw_p_bh"] < 0.05).sum())
        n_sig_fish = int((rec_df["fisher_p_bh"] < 0.05).sum())
        print(f"enrichment targets tested={len(rec_df)} significant(BH<0.05): MW={n_sig_mw} Fisher-top10={n_sig_fish}")
        print(rec_df.head(12).to_string(index=False))
    else:
        n_sig_mw = n_sig_fish = 0

    # ---- Figure 28d: per-target AUROC bar (top 25) ----
    if len(rec_df):
        top = rec_df.head(25)
        fig, ax = plt.subplots(figsize=(9, 6))
        colors = ["#55A868" if s else "#C44E52" for s in (top["mw_p_bh"] < 0.05)]
        ax.barh(np.arange(len(top)), top["pair_AUROC"].values[::-1], color=colors[::-1], alpha=0.85)
        ax.set_yticks(np.arange(len(top))); ax.set_yticklabels(top["target"].values[::-1], fontsize=8)
        ax.axvline(0.5, color="k", ls="--", lw=0.8)
        ax.set_xlabel("per-target pair AUROC (same-target pairs vs others, 904 features)")
        ax.set_title("Known-target enrichment (green = BH-significant, red = n.s.)")
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, "28d_target_enrichment.png"), dpi=DPI)
        plt.close(fig)
        print("saved:", os.path.join(FIG, "28d_target_enrichment.png"))

    # summary json
    import json
    summ = {
        "retrieval_before": {"mean_replicate_AP": before[0], "chance_AP": before[1], "pair_AUC": before[2]},
        "retrieval_after": {"mean_replicate_AP": after[0], "chance_AP": after[1], "pair_AUC": after[2]},
        "target_pair_AUROC_shared_any": auc_all, "target_pair_mw_p": p_all,
        "targets_tested": int(len(rec_df)), "targets_sig_mw_bh": n_sig_mw, "targets_sig_fisher_bh": n_sig_fish,
    }
    with open(os.path.join(REPORTS, "18_stage10_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=2)
    print(json.dumps(summ, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
