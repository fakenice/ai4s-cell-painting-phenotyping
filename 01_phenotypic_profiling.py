# -*- coding: utf-8 -*-
"""
AI4S Single-cell Phenotypic Profiling - Stage 2: Phenotypic Fingerprints & Compound Clustering

Dataset : JUMP-CP (cpg0000-jump-pilot, source_4) precomputed CellProfiler profiles
Input   : data/profiles/*.csv.gz + data/metadata (Metadata columns)
Output  : reports/figures/01_umap_overview.png
          reports/figures/02_compound_fingerprint_clusters.png
          reports/02_phenotype_results.csv
"""
import os

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import umap

# ---------- Configuration ----------
RANDOM_STATE = 42
N_NEIGHBORS = 15
MIN_DIST = 0.1
K_CANDIDATES = [8, 12]  # silhouette scan candidates
K_FINAL = 12            # final number of KMeans clusters
N_INIT = 10
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


# ---------- 1. Load data ----------
prof = load_profiles()
meta_cols = [c for c in prof.columns if c.startswith("Metadata")]
feat_cols = [c for c in prof.columns if not c.startswith("Metadata")]
X_all = prof[feat_cols].values.astype(np.float64)

# Keep compound-treated wells only (drop wells without a perturbagen name)
compound = prof.dropna(subset=["Metadata_pert_iname"]).copy()
print(f"Compound wells: {len(compound)} (from {len(prof)} wells)")

# ---------- 2. Well-level feature standardization ----------
X = compound[feat_cols].values.astype(np.float64)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ---------- 3. UMAP overview (DMSO control vs treatments) ----------
print(f"Running UMAP (n_neighbors={N_NEIGHBORS}, min_dist={MIN_DIST}) ...")
reducer = umap.UMAP(
    n_neighbors=N_NEIGHBORS, min_dist=MIN_DIST, random_state=RANDOM_STATE, n_jobs=1
)
X_umap = reducer.fit_transform(X_scaled)

compound["UMAP1"] = X_umap[:, 0]
compound["UMAP2"] = X_umap[:, 1]
compound["is_DMSO"] = compound["Metadata_pert_iname"] == "DMSO"
compound["is_poscon"] = compound["Metadata_control_type"].notna() & (
    compound["Metadata_control_type"] != "negcon"
)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
sns.scatterplot(
    data=compound, x="UMAP1", y="UMAP2", hue="is_DMSO",
    palette={True: "#d62728", False: "#b0b0b0"}, s=8, alpha=0.7, ax=axes[0], legend="full",
)
axes[0].set_title("DMSO (negcon) vs Treatments")
sns.scatterplot(
    data=compound, x="UMAP1", y="UMAP2", hue="is_poscon",
    palette={True: "#2ca02c", False: "#b0b0b0"}, s=8, alpha=0.7, ax=axes[1], legend="full",
)
axes[1].set_title("Positive Controls (poscon) vs Others")
plt.tight_layout()
plt.savefig(os.path.join(FIG, "01_umap_overview.png"), dpi=DPI)
plt.close()
print("Saved: reports/figures/01_umap_overview.png")

# ---------- 4. Compound phenotypic fingerprints (average across wells) ----------
fingerprint = compound.groupby("Metadata_pert_iname")[feat_cols].mean()
fp_scaled = scaler.transform(fingerprint.values)  # reuse the same scaler

# UMAP of compound fingerprints
fp_umap = reducer.transform(fp_scaled)
fp_df = pd.DataFrame(
    {"pert_iname": fingerprint.index, "UMAP1": fp_umap[:, 0], "UMAP2": fp_umap[:, 1]}
)

# KMeans clustering with silhouette scan
for k in K_CANDIDATES:
    km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=N_INIT)
    labels = km.fit_predict(fp_scaled)
    sil = silhouette_score(fp_scaled, labels)
    print(f"KMeans k={k}: silhouette={sil:.3f}")

km = KMeans(n_clusters=K_FINAL, random_state=RANDOM_STATE, n_init=N_INIT)
fp_df["cluster"] = km.fit_predict(fp_scaled)

fig, ax = plt.subplots(figsize=(10, 8))
sns.scatterplot(
    data=fp_df, x="UMAP1", y="UMAP2", hue="cluster", palette="tab20", s=40, ax=ax, legend="full",
)
ax.set_title(f"Compound Phenotypic Fingerprints (KMeans k={K_FINAL})")
plt.tight_layout()
plt.savefig(os.path.join(FIG, "02_compound_fingerprint_clusters.png"), dpi=DPI)
plt.close()
print("Saved: reports/figures/02_compound_fingerprint_clusters.png")

# ---------- 5. Save results ----------
out_csv = os.path.join(BASE, "reports", "02_phenotype_results.csv")
fp_df.to_csv(out_csv, index=False)
print(f"Saved: reports/02_phenotype_results.csv ({len(fp_df)} compounds)")
print("\nCluster members (first 3 per cluster):")
print(
    fp_df.groupby("cluster")
    .head(3)
    .sort_values(["cluster", "pert_iname"])[["cluster", "pert_iname"]]
    .to_string(index=False)
)
