# -*- coding: utf-8 -*-
"""
AI4S Single-cell Phenotypic Profiling - Stage 4: Refined Clusters, Target Enrichment & Phenotypic Strength

1) Refine KMeans clusters via Ward hierarchical clustering (k scan by silhouette)
2) Cluster x target Fisher exact enrichment with BH (FDR) correction
3) Phenotypic strength score per compound = mean out-of-fold P(treatment) from Stage 3

Output : reports/figures/04_enrichment_bubble.png
         reports/figures/04_refined_clusters_umap.png
         reports/04_enrichment.csv, reports/04_enrichment_significant.csv
         reports/04_phenotypic_strength.csv
"""
import os

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist
from scipy.stats import fisher_exact
from statsmodels.stats.multitest import multipletests

# ---------- Configuration ----------
K_SCAN = [16, 20, 24, 30, 36]  # hierarchical clustering k scan
P_ADJ_THRESHOLD_PLOT = 0.2     # bubble plot significance cutoff
MIN_HIT = 2                    # minimum hits to test an enrichment pair
MIN_TARGET_TOTAL = 2           # minimum target frequency in the background
TOP_FRACTION_PRINT = 0.25      # print clusters whose top target covers >= 25%
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
feat_cols = [c for c in prof.columns if not c.startswith("Metadata")]
compound = prof.dropna(subset=["Metadata_pert_iname"]).copy()
X = compound[feat_cols].values.astype(np.float64)
scaler = StandardScaler().fit(X)

fp_features = compound.groupby("Metadata_pert_iname")[feat_cols].mean()
fp_scaled = scaler.transform(fp_features.values)

# Target information (JUMP Target 1 compound metadata)
tgt = pd.read_csv(
    os.path.join(DATA, "metadata", "JUMP-Target-1_compound_metadata_targets.tsv"),
    sep="\t",
)
target_map = dict(zip(tgt["pert_iname"], tgt["target_list"]))


# ---------- 2. k scan ----------
Z = linkage(pdist(fp_scaled, metric="euclidean"), method="ward")
sils = []
for k in K_SCAN:
    lab = fcluster(Z, t=k, criterion="maxclust")
    sils.append(silhouette_score(fp_scaled, lab))
    print(f"k={k}: silhouette={sils[-1]:.3f}")
k_best = K_SCAN[int(np.argmax(sils))]
print(f"Best k = {k_best}")


# ---------- 3. Clustering + enrichment ----------
labels = fcluster(Z, t=k_best, criterion="maxclust")
fp_df = pd.DataFrame({"pert_iname": fp_features.index, "cluster": labels})
fp_df["target_list"] = fp_df["pert_iname"].map(target_map)

# Build cluster x target enrichment table (Fisher exact; background = compounds with targets)
with_tgt = fp_df.dropna(subset=["target_list"]).copy()
targets = sorted({t for tl in with_tgt["target_list"] for t in str(tl).split("|")})
N = len(with_tgt)

records = []
for cl in sorted(with_tgt["cluster"].unique()):
    in_cl = with_tgt["cluster"] == cl
    cl_set = set(with_tgt.loc[in_cl, "pert_iname"])
    for t in targets:
        t_set = set(
            with_tgt.loc[with_tgt["target_list"].str.contains(t, regex=False), "pert_iname"]
        )
        a = len(cl_set & t_set)   # in cluster and has target
        b = len(cl_set) - a       # in cluster, no target
        c = len(t_set) - a        # not in cluster, has target
        d = N - a - b - c         # neither
        table = [[a, b], [c, d]]
        if a >= MIN_HIT and (a + c) >= MIN_TARGET_TOTAL:
            odds, p = fisher_exact(table, alternative="greater")
            records.append(
                {"cluster": cl, "target": t, "hit": a, "cluster_size": len(cl_set),
                 "target_total": len(t_set), "odds_ratio": odds, "p_value": p}
            )

enr = pd.DataFrame(records)
if len(enr):
    enr["p_adj"] = multipletests(enr["p_value"], method="fdr_bh")[1]
    enr["enrichment_frac"] = enr["hit"] / enr["cluster_size"]
    enr_sig = enr[enr["p_adj"] < 0.05].sort_values("p_adj")
    print(f"\nSignificant cluster-target pairs (p_adj<0.05): {len(enr_sig)}")
    print(enr_sig.head(20).to_string(index=False))
    enr.to_csv(os.path.join(BASE, "reports", "04_enrichment.csv"), index=False)
    enr_sig.to_csv(os.path.join(BASE, "reports", "04_enrichment_significant.csv"), index=False)

# Intra-cluster target sharing summary
print("\nTop target per cluster (coverage >= 0.25):")
for cl in sorted(fp_df["cluster"].unique()):
    sub = fp_df[fp_df["cluster"] == cl].dropna(subset=["target_list"])
    if len(sub) == 0:
        continue
    cnt = {}
    for tl in sub["target_list"]:
        for t in str(tl).split("|"):
            cnt[t] = cnt.get(t, 0) + 1
    top_t, top_c = max(cnt.items(), key=lambda kv: kv[1])
    frac = top_c / len(sub)
    if frac >= TOP_FRACTION_PRINT:
        print(f"  cluster{cl}: n={len(sub)}, top_target={top_t} ({top_c}/{len(sub)} = {frac:.2f})")


# ---------- 4. Phenotypic strength score ----------
pred = pd.read_csv(os.path.join(BASE, "reports", "03_pred_trt_vs_DMSO.csv"))
strength = (
    pred[pred["y_true"] == 1]
    .groupby("Metadata_pert_iname")["y_prob"]
    .agg(["mean", "std", "count"])
)
strength = strength.reset_index().rename(
    columns={"mean": "phenotypic_strength", "std": "strength_std", "count": "n_wells"}
)
strength = strength.sort_values("phenotypic_strength", ascending=False)
strength.to_csv(os.path.join(BASE, "reports", "04_phenotypic_strength.csv"), index=False)
print(f"\nPhenotypic strength saved: {len(strength)} compounds")
print("Top 10 strongest:")
print(strength.head(10).to_string(index=False))
print("Bottom 10 weakest:")
print(strength.tail(10).to_string(index=False))

# Plot: enrichment bubble chart
fig, ax = plt.subplots(figsize=(12, 7))
sig_plot = enr[enr["p_adj"] < P_ADJ_THRESHOLD_PLOT].copy() if len(enr) else pd.DataFrame()
if len(sig_plot):
    sig_plot["-log10_padj"] = -np.log10(sig_plot["p_adj"])
    sns.scatterplot(
        data=sig_plot, x="target", y="cluster", size="hit", hue="-log10_padj",
        sizes=(40, 400), palette="YlOrRd", ax=ax,
    )
    ax.set_title("Cluster-Target enrichment (p_adj<0.2)")
    plt.xticks(rotation=90, fontsize=7)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, "04_enrichment_bubble.png"), dpi=DPI)
    plt.close()
    print("Saved: reports/figures/04_enrichment_bubble.png")

# Plot: refined cluster UMAP
fp_res = pd.read_csv(os.path.join(BASE, "reports", "02_phenotype_results.csv"))
fp_res2 = fp_res.merge(
    fp_df[["pert_iname", "cluster"]], on="pert_iname", how="left",
    suffixes=("_k12", "_refined"),
)
fig, ax = plt.subplots(figsize=(10, 8))
sns.scatterplot(
    data=fp_res2, x="UMAP1", y="UMAP2", hue="cluster_refined",
    palette="tab20", s=50, ax=ax, legend="full",
)
ax.set_title(f"Compound fingerprints by refined clusters (k={k_best})")
plt.tight_layout()
plt.savefig(os.path.join(FIG, "04_refined_clusters_umap.png"), dpi=DPI)
plt.close()
print("Saved: reports/figures/04_refined_clusters_umap.png")
