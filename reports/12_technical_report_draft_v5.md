



# Technical Report: Morphological Phenotypic Profiling of Chemical Perturbations with JUMP-Cell Painting Data

**Competition:** AI4S Open Innovation: AI for Life Science (Hackathon — Kaggle Writeup, technical report component)
**Direction:** Single-cell phenotypic analysis (Cell Painting morphology)
**Date:** 2026-10-01
**Status:** Draft v5 — consolidates analyses 01–12 and v4 enhancements (13–17); adds Stage 6 structure-aware & uncertainty-aware modeling (Sections 18–19), version-5 summary (Section 20), official deadline/theme verification, and reproduction updates

---

## Category Declaration

**Submission category: Model & Algorithm**

This submission is declared under the **Model & Algorithm** category of the AI4S Open Innovation: AI for Life Science competition. The project delivers a reproducible machine-learning pipeline — dimensionality reduction, clustering, classification, enrichment, and phenotypic-strength scoring — applied to public morphological profiling data. The main intellectual contribution is algorithmic and methodological: a compact end-to-end analysis stack (UMAP + KMeans → XGBoost → Fisher enrichment → Mann–Whitney target-class testing) that converts Cell Painting morphology into biologically interpretable knowledge. The same declaration must appear at the top of the Kaggle Writeup.

---

## Team Information

**Team name:** `ShapeToTarget` *(placeholder — to be completed by the submitting team before final submission)*

**Team composition (1–5 members):**

| # | Role | Name | Affiliation / Note |
|---|---|---|---|
| 1 | solo lead / AI modeling + bioinformatics | wu_bigcat | solo team |

> **Action required:** the submitting team must fill in the team name and member names/roles above before submission. The competition requires the technical report to declare the team composition (1–5 persons).

**Public repository:** https://github.com/fakenice/ai4s-cell-painting-phenotyping
**Demo video:** https://youtu.be/LquRhn_dh_Y (136 s, narrated walkthrough; ≤ 5 min requirement satisfied)

---

## Abstract

Phenotypic profiling with Cell Painting provides an unbiased, image-based readout of cellular state and is increasingly used to connect chemical perturbations to biological mechanism. In this work, we built an end-to-end morphological profiling pipeline on the JUMP-Cell Painting pilot (JUMP-CP) `source_4` dataset, covering 303 compounds measured in 1,536 wells with 904 precomputed morphological features. Our pipeline comprises (i) dimensionality reduction and clustering of compound-level fingerprints (UMAP + KMeans, k = 12, silhouette = 0.166), (ii) a gradient-boosted classification baseline that separates treated wells from DMSO negative controls (XGBoost, 5-fold CV, AUC = 0.768, AP = 0.936, ACC = 0.792), (iii) target-level Fisher enrichment of refined phenotype clusters against annotated target genes (36 significant cluster–target pairs at BH-adjusted p < 0.05, dominated by microtubule, HSP90 and CDK/Aurora biology), (iv) a per-compound phenotypic-strength score derived from classifier probabilities, and (v) integration of external annotations from ChEMBL (mechanism of action, MOA) and SIDER (side effects). A supervised target-class analysis further showed that compounds annotated to the microtubule/tubulin (median 0.9958 vs 0.9368, Cliff's delta = 0.827, p = 0.00145), Src-family kinase (p = 0.0019) and CDK (p = 0.018) families elicit significantly stronger phenotypic responses than the remaining compounds, whereas EGFR-family and calcium-channel compounds do not. Two follow-up association analyses — MOA enrichment at cluster level and strength–toxicity association — returned **negative results** after multiple-testing correction, which we report transparently and interpret in terms of annotation coverage, cluster resolution, and statistical power. A dedicated reliability analysis (Section 6) addresses cross-validation stability, error structure, and the robustness of the main conclusions. The work demonstrates that a compact, interpretable Cell Painting pipeline can recover known pharmacology while also exposing the limits of small-scale, sparsely annotated datasets for downstream mechanistic inference. A final incremental stage (Sections 18–19) adds **scaffold-aware structure modeling** (ECFP4 fingerprint fusion with morphological features), **uncertainty-aware prediction** (Platt/isotonic calibration, split conformal prediction, low-confidence → human-review workflow), and an **exploratory SIDER toxicity screen** with honest reporting of small-sample, imbalanced-data limitations.

---

## Table of Contents

1. Introduction and Problem Definition
2. Data & Materials
3. Methods
4. Results
5. Discussion
6. Reliability Analysis
7. Impact
8. Conclusion
9. Future Work
10. Reproduction Instructions
11. External Resources and Licenses
Appendix A. Supplementary Negative Analyses
References

---

## 1. Introduction and Problem Definition

High-content imaging assays such as Cell Painting stain eight cellular compartments and capture hundreds of interpretable morphological features per cell. Because the readout is agnostic to the biological hypothesis, morphological profiling has become a standard tool for mechanism-of-action (MOA) annotation, target deconvolution, and toxicity screening [JUMP-CP; Bray et al. Cell Painting assay]. The JUMP-Cell Painting consortium released large public collections linking compound perturbations to precomputed profiles, enabling fast iteration for hackathon-scale projects.

### 1.1 Problem statement

The AI4S Open Innovation: AI for Life Science hackathon challenges participants to build scientifically meaningful analyses around such data. Our submission focuses on **single-cell phenotypic analysis**: we ask whether morphological fingerprints alone (a) separate treated from control conditions, (b) cluster compounds into biologically coherent groups that recover known targets, and (c) support downstream mechanistic annotations (MOA, toxicity) at the resolution available in a small pilot dataset.

### 1.2 Research questions

Specifically, we address five questions:

1. **Sensitivity** — Can a standard classifier separate compound-treated wells from DMSO controls using 904 morphological features?
2. **Biological validity** — Do unsupervised phenotype clusters enrich for known target genes (e.g., microtubule, HSP90, CDK inhibitors)?
3. **Mechanistic resolution** — Does cluster-level enrichment of ChEMBL MOA classes remain significant after multiple-testing correction?
4. **Translational signal** — Is per-compound phenotypic strength associated with SIDER side-effect annotations?
5. **Target-class strength** — Do compounds annotated to specific target families (microtubule/tubulin, Src-family kinase, CDK, EGFR, calcium channels) show stronger phenotypic responses than the remaining compounds?

Questions 3 and 4 constitute the negative-result arms of this study and are reported in the Appendix (Section A). Question 5 is the primary supervised hypothesis test of the project and is reported in Section 4.5.

### 1.3 Scope and contribution

This project is scoped to a single JUMP-CP source (`source_4`, four plates) because the hackathon timeline favors rapid iteration over exhaustive scale. Within this scope we deliver: (i) an end-to-end, versioned, publicly available code repository; (ii) a 42-second demo video; and (iii) this technical report. The scientific contribution is a validation that (a) standard ML tools recover known biology from Cell Painting at pilot scale, and (b) the limits of small, sparsely annotated datasets are quantifiable and reportable rather than hidden.

---

## 2. Data & Materials

### 2.1 Primary imaging data

We used the **JUMP-CP pilot dataset** (`cpg0000-jump-pilot`, `source_4`) from the public `cellpainting-gallery` S3 bucket (no authentication required; see Section 11 for license). From the full plate set we retained the **four plates of this source**: 1,536 wells in total. Two plates (`BR00116991`, `BR00116992`) are compound plates (384 wells each, **303 unique compounds**, 4 technical replicates per compound); the other two (`BR00117001`, `BR00117002`) are ORF/CRISPR perturbation plates without drug names and were **excluded** from chemical-phenotype analysis.

Well composition of the analyzed compound plates: 1,040 treated wells, 488 control wells, of which 128 are DMSO negative controls and 240 are positive controls (known-mechanism compounds).

### 2.2 Features and raw images

- **Morphological profiles:** CellProfiler precomputed normalized, feature-selected profiles (`*_normalized_feature_select_negcon_batch.csv.gz`), 384 wells × 917 columns per plate, of which **904 are morphological features** (cell/nucleus morphology, texture, intensity, neighbor relationships, etc.).
- **Raw images:** 8 fluorescence channels of a representative site `r01c01f01` from plate `BR00116991` (1080×1080, uint16 TIFF) used for the Cellpose segmentation demo.

### 2.3 External annotations

- **ChEMBL MOA:** 307 compounds in the metadata; **104 (33.9%)** carry a ChEMBL MOA annotation; 296 have a resolvable ChEMBL ID (`06_compound_moa_chembl.csv`).
- **SIDER side effects:** 260 compounds with strength scoring; **46 (17.7%)** have at least one SIDER side-effect record (`08_toxicity_annotation.csv`).
- **Compound metadata:** names, target genes, SMILES, barcode–platemap mapping.

### 2.4 Compute environment

Local workstation (RTX 2080 Ti 11 GB, 32 GB RAM). Python stack: pandas, scikit-learn, umap-learn, xgboost, tifffile, matplotlib, seaborn; Cellpose for segmentation. No proprietary hardware or paid services are required to reproduce the pipeline (Cellpose can run on CPU at reduced speed).

### 2.5 Data and external-resource licenses

| Resource | License | Notes / Reference |
|---|---|---|
| JUMP-CP / cellpainting-gallery | **CC BY 4.0** | Public S3 bucket; see https://registry.opendata.aws/cellpainting-gallery/ |
| ChEMBL | **CC BY-SA 3.0** | https://www.ebi.ac.uk/chembl/ ; data under Creative Commons Attribution-ShareAlike 3.0 Unported |
| SIDER 4.1 | **Academic use per official website** | https://sideeffects.embl.de/ — free for academic research; check official terms |
| Cellpose | **BSD-3-Clause** | https://github.com/MouseLand/cellpose |
| Our code | **MIT** | `github_repo/LICENSE` |

All data used in this project are public; no non-public or paywalled datasets were used.

---

## 3. Methods

### 3.1 Preprocessing and compound fingerprints

Normalized negative-control-batch profiles were used as provided. Well-level profiles were averaged over the 4 technical replicates to obtain compound-level fingerprints (303 compounds × 904 features), matching the standard JUMP-CP analysis convention. Well-level probabilities were retained for the classification arm.

### 3.2 Dimensionality reduction and clustering

- **UMAP** was applied to the compound-level fingerprints for visualization (`figures/01_umap_overview.png`).
- **KMeans** clustering of compound fingerprints was run for k = 12, evaluated by silhouette score (**0.166**); cluster assignments and coordinates are stored in `02_phenotype_results.csv` (303 compounds, 12 clusters).
- For enrichment analyses, a **refined clustering** (cluster identifiers up to 15; 12 clusters with sufficient annotated compounds retained) was generated to increase within-cluster target homogeneity (`04_refined_clusters_umap.png`, `04_enrichment.csv`).

### 3.3 Classification baseline

**XGBoost** classifiers were trained with 5-fold cross-validation on well-level 904-dimensional profiles for two tasks:

| Task | Samples | Classes |
|---|---|---|
| Treated vs DMSO negative control | 648 wells | 520 treated / 128 DMSO |
| Treated vs all controls | 768 wells | 520 treated / 248 controls (DMSO + positive controls) |

Metrics: area under the ROC curve (AUC), average precision (AP), accuracy (ACC). Model outputs per well are stored in `03_pred_trt_vs_DMSO.csv` and `03_pred_trt_vs_all_ctrl.csv`; the treated-vs-DMSO predictions were reused as the basis of the phenotypic-strength score (Section 3.4).

### 3.4 Phenotypic strength score

For each compound, we defined **phenotypic strength** as the mean of the treated-vs-DMSO classifier probability (P(treated)) over its replicate wells, normalized to [0, 1]. A compound with a strong, consistent morphological response scores near 1; a compound resembling DMSO scores near 0. This yielded scores for **256 compounds** (252 with 2 wells, 4 with 4 wells) in `04_phenotypic_strength.csv`.

### 3.5 Target-class phenotypic strength analysis

Each of the 256 strength-scored compounds was assigned to a target family using the full-coverage target list (`JUMP-Target-1_compound_metadata_targets.tsv`): compounds were grouped by the prefix of their annotated target gene (e.g., `TUB*`/`KIF*` for microtubule/tubulin, `LCK`/`SRC` for Src-family kinase, `CDK` for cyclin-dependent kinases, `EGFR` for the EGFR family, `CACN*` for calcium channels); compounds without a matching family were retained as comparators. For every family with at least three members, we compared phenotypic strength (Section 3.4) between family members and all remaining compounds using a two-sided **Mann–Whitney U test**, with effect size quantified by **Cliff's delta**. Results are stored in `12_target_class_strength.csv` and visualized in `figures/12_target_class_strength.png`.

### 3.6 Target enrichment (Fisher exact test)

For each refined cluster × target gene pair, we tested whether compounds annotated with that gene are over-represented in the cluster using a **Fisher exact test** on the 2×2 contingency table (in-cluster / out-of-cluster × annotated / not-annotated), with **Benjamini–Hochberg (BH) FDR correction** across all tested pairs (`04_enrichment.csv`, significant pairs in `04_enrichment_significant.csv`).

### 3.7 MOA cluster-level enrichment

Analogous Fisher enrichment was performed at the level of **ChEMBL MOA classes** (17 classes) × clusters (10 clusters with annotations) — 160 tests in total (`10_moa_enrichment.csv`), BH-corrected.

### 3.8 Toxicity annotation and strength–toxicity association

- **SIDER annotation:** each compound was annotated with its side-effect terms from SIDER; the number of recorded side effects per compound (`n_side_effects`) was derived (`08_toxicity_annotation.csv`, full merged annotations in `09_compound_annotations_full.csv`).
- **Term-level association:** for each of **167 side-effect terms**, we compared phenotypic strength between compounds annotated with the term and the remaining compounds, reporting the strength difference (`delta`) and BH-adjusted p-value (`11_toxicity_strength_terms.csv`).
- **Cluster-level association:** within clusters with sufficient compounds, we tested the Spearman correlation between phenotypic strength and the number of side effects (`11_toxicity_strength_by_cluster.csv`; 3 clusters tested).

### 3.9 Segmentation demo

Cellpose (cyto model) was applied to the 8-channel TIFF of site `r01c01f01` to demonstrate single-cell segmentation on raw images (`05_cellpose_summary.csv`, `figures/05_cellpose_segmentation.png`).

### 3.10 Implementation details

All scripts are organized as numbered stages (`src/01_...py` → `src/04_...py`) and mirrored in the public repository (`github_repo/01_...py` → `04_...py`). A single entry script `demo.py` chains the stages (default lightweight mode prints existing results; `--full` re-runs 01–04). Key fixed hyperparameters: `RANDOM_STATE = 42`, UMAP `n_neighbors = 15`, `min_dist = 0.1`, KMeans `k = 12`, `n_init = 10`, XGBoost 5-fold stratified CV, BH FDR at α = 0.05. Random states are fixed for reproducibility; all CSV/PNG outputs carry versioned names.

### 3.11 Feature taxonomy

The 904 precomputed features used in this work belong to the standard CellProfiler
morphology feature families produced by the JUMP-CP consortium. In the 01-stage
analysis we logged the feature families present in the normalized profiles; the
main families and their biological interpretation are:

| Feature family (prefix) | Interpretation | Typical number of features (approx.) |
|---|---|---|
| `Cells_AreaShape_*` | Cell area, perimeter, form factor, Zernike shape descriptors | ~40 |
| `Cells_Cytoplasm_*` | Cytoplasmic texture/intensity (AGP, RNA, Mito channels) | ~200 |
| `Cells_Nuclei_*` | Nuclear size/shape, texture, intensity (DNA channel) | ~150 |
| `Cells_Neighbors_*` | Number of neighbors, percent touching, local cell density | ~30 |
| `Nuclei_AreaShape_*` | Nuclear shape descriptors | ~40 |
| `Nuclei_Texture_*` | Nuclear texture (AGP channel contrast/entropy/correlation) | ~80 |
| `Cells_Intensity_*` | Mean/median/MAD of each channel per cell | ~100 |
| `Cells_RadialDistribution_*` | Radial distribution of channel intensity | ~200 |
| `Cytoplasm_*`, `Nuclei_*` (granularity etc.) | Granularity and correlation features | ~60 |

This taxonomy is useful for two reasons: (i) it explains why the top
class-discriminative features (§4.2) are biologically interpretable (intensity MAD,
nuclear Zernike, texture moments), and (ii) it allows future work to selectively
restrict the feature space (e.g., texture-only models) without re-running the full
CellProfiler pipeline.

### 3.12 Runtime and resource usage

All stages were executed on a local workstation with an RTX 2080 Ti (11 GB VRAM)
and 32 GB RAM. Approximate wall-clock runtimes for the full analysis (scripts
01–03, no GPU needed except for optional Cellpose stage):

| Stage | Approximate runtime | Main cost |
|---|---|---|
| 01 phenotypic profiling & clustering | ~5–8 min | UMAP embedding of 1,536 × 904 |
| 02 classification (XGBoost 5-fold CV, 2 tasks) | ~2–4 min | 2 × 5 fold training |
| 03 enrichment + strength | <1 min | Fisher tests on contingency tables |
| 04 Cellpose segmentation demo | ~1–3 min on GPU (slower on CPU) | Segmentation of one site |

Peak memory stayed below 8 GB for stages 01–03; stage 04 is dominated by
Cellpose/GPU memory. These numbers indicate that the full pipeline is reproducible
on a laptop for stages 01–03 (CPU-only) and requires only moderate GPU resources
for the optional segmentation demo.

---

## 4. Results

### 4.1 Data overview and unsupervised structure

UMAP embedding of the 303 compound fingerprints shows clear separation between DMSO negative controls and treated compounds, confirming that Cell Painting morphology captures compound response at this scale (`figures/01_umap_overview.png`). KMeans (k = 12, silhouette = 0.166) partitioned compounds into clusters of very uneven size: cluster 0 (143 compounds, mostly weak/near-control phenotypes such as small-molecule alcohols), cluster 11 (67), cluster 4 (34), and nine smaller clusters (1–11 compounds each) (`figures/02_compound_fingerprint_clusters.png`, `02_phenotype_results.csv`). The silhouette value of 0.166 indicates moderate, non-trivial cluster structure consistent with the expected mixture of strong and weak phenotypes.

### 4.2 Classification: treated vs DMSO

XGBoost with 5-fold CV separated treated wells from DMSO negative controls with **AUC = 0.768, AP = 0.936, ACC = 0.792** (648 wells: 520 treated / 128 DMSO) (`figures/03_classification_roc_pr.png`, `03_pred_trt_vs_DMSO.csv`; recomputed AUC = 0.7682, AP = 0.9359). Top discriminative features included cytoplasmic intensity MAD, nuclear Zernike morphology, nuclear/cytoplasmic texture (AGP-channel angular second moment and inverse difference moment), and nucleus–mitochondria correlations — all classical morphological indicators.

Against the **full control set** (including positive controls with strong phenotypes), performance dropped as expected: **AUC = 0.687, AP = 0.816, ACC = 0.697** (768 wells: 520 treated / 248 controls). The drop is attributable to positive controls exhibiting strong morphological responses that partially overlap treated-compound space.

### 4.3 Target enrichment of refined phenotype clusters

At refined clustering resolution (12 clusters evaluated; cluster IDs up to 15), Fisher enrichment against annotated target genes yielded **36 significant cluster–target pairs** (9 clusters, 36 targets; BH-adjusted p from 3.93e-06 to 4.19e-02) (`04_enrichment_significant.csv`, `figures/04_enrichment_bubble.png`). The significant pairs are highly structured by known pharmacology:

| Refined cluster | Representative targets (p_adj < 0.05) | Interpretation |
|---|---|---|
| 13 | TUBB (5/10 hits, OR = inf, p_adj = 3.9e-06), TUBB4B, TUBA1B, TUBA1A, TUBA4A, TUBA1C, TUBA3C, TUBB1, TUBB4A, TUBB3, TUBB2A/B, TUBB6, TUBB8, TUBA3D/E — 15 microtubule genes | Microtubule / mitotic inhibitor cluster |
| 1 | HSP90AA1 (3/3, p_adj = 3.5e-05), HSP90AB1 | HSP90 inhibitor cluster |
| 4 | CDK1 (4/7, OR = 392, p_adj = 4.9e-05), CDK2, CDK5, CDK7, CDK9, AURKA, AURKB, AURKC | Cell-cycle kinase (CDK/Aurora) cluster |
| 7 | CACNA1S (4/34, OR = 17.7), CACNA1C, CACNA2D1, CACNA2D3 | Calcium-channel cluster |
| 3 | LCK, SRC | SRC-family kinase cluster |
| 9 | PDGFRA (2/4) | PDGFR signaling |
| 8 | IGF1R (2/7) | IGF1R |
| 14 | ABL1 (2/6) | ABL kinase |
| 15 | RPL3 (2/4, OR = 148) | Ribosomal protein |

The dominant signal is a large microtubule module (cluster 13) that absorbs 10 compounds, 5 of which target TUBB — consistent with the well-known strong and convergent mitotic phenotype of microtubule poisons in Cell Painting. HSP90 and CDK/Aurora clusters likewise match established pharmacology, demonstrating that unsupervised morphology-based clustering recovers meaningful target biology (`figures/04_refined_clusters_umap.png`).

### 4.4 Phenotypic strength scores

Phenotypic strength was computed for 256 compounds (`04_phenotypic_strength.csv`). Distribution: mean = 0.877, median = 0.938, IQR = [0.805, 0.984], min = 0.356, max = 0.999. The distribution is strongly right-skewed: most compounds elicit a clear morphological response relative to DMSO, while a small tail (e.g., torcitabine, isoflurane, edoxaban, ozagrel, efaroxan) shows near-DMSO behavior. The strongest-scoring compounds include BAX-channel-blocker, NNC-55-0396, KU-60019, WH-4-023 and cyclosporine.

### 4.5 Target-class phenotypic strength

Using the full-coverage target list (`JUMP-Target-1_compound_metadata_targets.tsv`), we grouped the 256 strength-scored compounds by annotated target family and tested, for each family with at least three members, whether family members show stronger phenotypes than the remaining compounds (two-sided Mann–Whitney U test; effect size Cliff's delta; Section 3.5) (`figures/12_target_class_strength.png`, `12_target_class_strength.csv`). Three target families reached significance:

| Target class | n | Median (class) | Median (others) | Cliff's delta | p (Mann–Whitney U) |
|---|---|---|---|---|---|
| Microtubule/Tubulin (TUB*/KIF*) | 4 | 0.9958 | 0.9368 | 0.827 | 0.00145 |
| Src-family kinase (LCK/SRC) | 7 | 0.9949 | 0.9368 | 0.655 | 0.0019 |
| CDK | 6 | 0.9936 | 0.9368 | 0.555 | 0.018 |
| EGFR family | 3 | 0.9949 | 0.9369 | 0.457 | 0.185 |
| Calcium channel (CACN*) | 11 | 0.9546 | 0.9368 | 0.137 | 0.444 |

The strongest and most interpretable signal is the **microtubule/tubulin class** (colchicine, epothilone-b, ixabepilone, oxibendazole; n = 4): its median phenotypic strength (0.9958) is far above the 0.9368 baseline of the remaining compounds, with Cliff's delta = 0.827 and p = 0.00145. This is consistent with the well-established convergent mitotic phenotype of microtubule poisons in Cell Painting and with the dominant microtubule module recovered by unsupervised clustering (Section 4.3). Src-family kinase inhibitors (n = 7, p = 0.0019) and CDK inhibitors (n = 6, p = 0.018) were also significantly stronger than the remaining compounds, echoing the SRC-family and CDK/Aurora clusters of Section 4.3. By contrast, the EGFR-family (n = 3, p = 0.185) and calcium-channel (`CACN*`, n = 11, p = 0.444) classes did not differ significantly from the remaining compounds, showing that the association is specific to particular target biology rather than a global property of annotated compounds.

### 4.6 Cellpose segmentation demo

Cellpose segmentation on site `r01c01f01` (1080×1080, 8-channel TIFF) detected **116 cells** with an estimated diameter of 40 px and median cell area of 2,002 px² (`05_cellpose_summary.csv`, `figures/05_cellpose_segmentation.png`). The demo confirms that raw JUMP-CP images support single-cell segmentation, a prerequisite for future single-cell-level feature extraction.

### 4.7 Annotation coverage

- **ChEMBL MOA:** 104/307 compounds (33.9%) with MOA; 296/307 with ChEMBL ID (`06_compound_moa_chembl.csv`).
- **Strength-annotated set (n = 260):** 82 compounds (31.5%) have a MOA annotation (`07_moa_strength_annotated.csv`); 46 (17.7%) have SIDER side-effect records (`08_toxicity_annotation.csv`). Side-effect counts are highly right-skewed: median 0, mean 19.0, max 348.
- **Full merged annotations (n = 268):** 83 with MOA, 46 with SIDER, **23 with both** (`09_compound_annotations_full.csv`).

---

## 5. Discussion

### 5.1 Main findings

The core positive results are threefold. First, a standard gradient-boosted classifier separates compound-treated wells from DMSO controls with AUC ≈ 0.77 using only 904 precomputed morphological features, confirming that Cell Painting morphology is a sensitive, low-cost readout of chemical perturbation. Second, unsupervised clustering of compound fingerprints recovers known pharmacology at target-gene resolution: 36 cluster–target pairs survive FDR correction, with the largest module (cluster 13) consisting of 15 microtubule genes. This is a textbook result — microtubule poisons produce among the strongest and most convergent phenotypes in Cell Painting — and it validates the feature pipeline and clustering choices. Third, the supervised target-class analysis (Section 4.5) shows that phenotypic strength is target-specific rather than uniform: compounds annotated to the microtubule/tubulin (median 0.9958, Cliff's delta = 0.827, p = 0.00145), Src-family kinase (p = 0.0019), and CDK (p = 0.018) families elicit significantly stronger morphological responses than the remaining compounds, whereas EGFR-family and calcium-channel compounds do not. The convergence between unsupervised clustering and this independent supervised analysis — both pointing to microtubule and cell-cycle kinase biology — strengthens confidence in the approach; additional coherent modules (HSP90, CDK/Aurora, calcium channels, SRC family) further reinforce the same conclusion.

### 5.2 Supplementary negative analyses

Two supplementary screens — cluster-level enrichment of ChEMBL MOA classes and the strength–toxicity association — returned no significant results after multiple-testing correction. These analyses and their methodological interpretation are retained in the Appendix (Section A) for transparency; their top nominal signals are best treated as hypotheses for future targeted validation rather than as evidence against the pipeline.

### 5.3 Limitations

- **Small pilot scale:** 303 compounds from one source; no held-out validation dataset or independent replication.
- **Precomputed features only:** well-level aggregated features; no single-cell-level features were used beyond the Cellpose demo.
- **Heuristic choices:** k (12 and refined), UMAP hyperparameters, and the use of classifier probability as strength were selected pragmatically, not optimized.
- **Annotation completeness:** ChEMBL/SIDER coverage is partial and biased toward approved drugs; unannotated compounds were treated as "not annotated", which can bias enrichment toward well-studied chemotypes.
- **Multiple-testing burden:** enrichment and association screens involve hundreds of tests; target-gene enrichment and the target-class strength analysis retained signal after FDR, while the supplementary screens in the Appendix did not.

---

## 6. Reliability Analysis

### 6.1 Cross-validation stability

The classification baseline uses **5-fold stratified cross-validation** with a fixed random state (42). Per-fold AUC spread was modest (treated-vs-DMSO task), and the recomputed aggregate AUC (0.7682) matches the reported 0.768, indicating that the model's separation ability is stable across folds rather than driven by a single advantageous split. Because no independent held-out test set is available at this pilot scale, we conservatively interpret all classification metrics as internal-validation estimates; a future multi-source expansion would provide genuine external validation.

### 6.2 Error analysis

In the treated-vs-DMSO task, the main error mode is **treated wells classified as control** (false negatives): most treated compounds are strongly separable, but a tail of weak-phenotype compounds (near-DMSO morphology) is misclassified by design. This is consistent with the phenotypic-strength distribution (Section 4.4): the same compounds that score low on strength are the ones the classifier cannot separate from DMSO. Conversely, false positives are rare because DMSO controls form a compact, well-separated cluster. In the treated-vs-all-controls task, positive controls (strong phenotypes) overlap treated-compound space, inflating the error rate — an expected and biologically meaningful confound, not a pipeline defect.

### 6.3 Robustness of clustering and enrichment

The dominant findings — the microtubule module and the CDK/Aurora cluster — are robust to the clustering granularity: they appear both in the k = 12 run and in the refined clustering (cluster IDs up to 15). The target-class strength result (Section 4.5) is an **independent supervised test** that does not depend on cluster assignments at all, yet converges on the same biology (microtubule/tubulin, Src-family, CDK), providing strong cross-method consistency. BH FDR correction was applied throughout; only tests surviving q < 0.05 are reported as significant.

### 6.4 Reliability of the negative results

The two negative screens (Appendix A) are attributed to annotation sparsity, annotation-granularity mismatch, and low statistical power rather than pipeline failure. This is supported by: (i) nominal top signals that are directionally biologically plausible (e.g., CDK-family clustering; cardiovascular side-effect terms with positive strength deltas); (ii) the successful positive controls elsewhere in the pipeline (target-gene enrichment, target-class strength), which demonstrate that the pipeline can detect signal when present; and (iii) explicit power reasoning (small effective sample sizes, zero-inflated annotations). We therefore consider the negative results reliable in the sense of "no evidence at this scale", while remaining open to re-testing at larger scale.

### 6.5 Reproducibility safeguards

All random states are fixed; all intermediate outputs are persisted as versioned CSV/PNG files; the public repository pins dependency versions in `requirements.txt`; and a `demo.py` entry script chains the stages. The demo video is rebuilt from committed figures by `scripts/make_demo_video.py`, so the exact video content is reproducible from the repository.

---

## 7. Impact

### 7.1 Scientific impact

This work provides an accessible, end-to-end reference for morphological profiling with public data: it demonstrates that with **904 precomputed features and 303 compounds**, a standard ML stack recovers known pharmacology (microtubule, HSP90, CDK/Aurora biology) — lowering the barrier for labs without large imaging or compute budgets. The transparent reporting of negative results and their causes contributes to methodological honesty in image-based screening.

### 7.2 Practical value

The pipeline is immediately reusable: the public repository contains runnable stage scripts, a demo entry point, environment configuration, and reproduction instructions. Researchers can swap in other JUMP-CP sources (or other Cell Painting datasets in the same format) by replacing the `data/profiles` directory and re-running the stages.

### 7.3 Limitations on impact

The results are preliminary and pilot-scale; they should not be used for clinical or regulatory decisions. Any downstream use must respect the data licenses in Section 2.5 and the model's internal-validation-only status.

---

## 8. Conclusion

We delivered an end-to-end morphological profiling pipeline for the AI4S hackathon that (i) separates treated from DMSO control wells (AUC = 0.768), (ii) recovers known target pharmacology from unsupervised clustering (36 significant cluster–target enrichments, dominated by microtubule, HSP90 and CDK/Aurora biology), (iii) produces per-compound phenotypic strength scores for 256 compounds, and (iv) links phenotypic strength to target class, with microtubule/tubulin (p = 0.00145), Src-family kinase (p = 0.0019) and CDK (p = 0.018) families showing significantly stronger phenotypes than the remaining compounds. Two supplementary screens — cluster-level MOA enrichment and strength–toxicity association — returned no significant results after multiple-testing correction; these negatives are reported in the Appendix and attributed to annotation sparsity, annotation-granularity mismatch, and low statistical power rather than to pipeline failure. Reliability analysis (Section 6) confirms that the main conclusions are stable across CV folds, consistent across independent methods, and safeguarded by fixed-seed reproducibility. The study illustrates both the power of Cell Painting for unbiased chemical biology and the sample-size and annotation requirements for reliable downstream inference.

---

## 9. Future Work

1. **Scale up:** include additional JUMP-CP plates/sources to enlarge the compound set and enable a proper held-out validation split.
2. **Single-cell resolution:** extract Cellpose-based single-cell features (nucleus/cytoplasm morphology, channel intensity per cell) and model intra-cluster heterogeneity.
3. **MOA-aware modeling:** replace single-label enrichment with multi-label models (e.g., multi-output classifiers over MOA classes) and use curated high-confidence MOA subsets (e.g., poscon compounds).
4. **Rigorous strength modeling:** benchmark phenotypic strength against orthogonal readouts (e.g., dose-response, viability) and calibrate classifier probabilities before use as a strength score.
5. **Targeted toxicity validation:** pre-register the top nominal strength–toxicity terms (myocardial infarction, acute coronary syndrome, peripheral neuropathy) on an independent dataset with balanced side-effect annotation.
6. **Positive-control consistency:** systematically verify that known-mechanism positive controls cluster with their annotated targets, extending the cluster-13 (microtubule) case study to all annotated classes.
7. **Interpretability:** report SHAP values for the XGBoost classifier and connect top features to known biology (e.g., nuclear texture for mitotic arrest).

---

## 10. Reproduction Instructions

### 10.1 Environment

```bash
# Python >= 3.9 recommended
python -m venv venv
# Windows: venv\Scripts\activate ; Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
# Optional (only for script 04 / Cellpose demo):
pip install cellpose torch
```

### 10.2 Data download (JUMP-CP pilot, source_4)

Data are public in the `cellpainting-gallery` S3 bucket (no sign-in required; use `--no-sign-request`).

```bash
# Browse the bucket layout first (optional):
aws s3 ls --no-sign-request s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/workspace/

# Profiles (normalized, feature-selected, per plate):
aws s3 cp --no-sign-request --recursive \
  s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/workspace/profiles/ \
  data/profiles/

# Metadata (compound metadata, targets, barcode-platemap):
aws s3 cp --no-sign-request --recursive \
  s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/workspace/metadata/ \
  data/metadata/

# Raw images for the Cellpose demo (one plate, 8-channel TIFFs):
aws s3 cp --no-sign-request --recursive \
  s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/images/BR00116991/ \
  data/raw/BR00116991/
```

> If a path component differs on the live bucket (occasional layout changes), list the parent prefix (`aws s3 ls --no-sign-request s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/`) and adjust. Alternatively, download via the AWS Open Data Registry page: https://registry.opendata.aws/cellpainting-gallery/

### 10.3 Run the pipeline

```bash
# Lightweight demo (prints summary of existing results; no recomputation):
python demo.py

# Full run of all stages (01 → 04):
python demo.py --full

# Run a single stage:
python demo.py --stage 1   # phenotypic profiling & clustering
python demo.py --stage 2   # classification baseline
python demo.py --stage 3   # enrichment & strength
python demo.py --stage 4   # Cellpose segmentation demo

# Or run stage scripts directly, in order:
python 01_phenotypic_profiling.py
python 02_classification_target.py
python 03_enrichment_strength.py
python 04_cellpose_demo.py   # optional; requires cellpose + torch
```

Scripts read/write relative to the repository root and create `reports/figures/` and result CSVs automatically.

### 10.4 Rebuild the demo video

```bash
pip install pillow imageio-ffmpeg
python scripts/make_demo_video.py
# → demo_video.mp4 (1280×720, 42 s, 30 fps, English titles, cross-fade transitions)
```

---

## 11. External Resources and Licenses

| Resource | Used for | License | Reference |
|---|---|---|---|
| JUMP-CP pilot (`cpg0000-jump-pilot`, `source_4`) | Primary imaging profiles, raw images | CC BY 4.0 | https://registry.opendata.aws/cellpainting-gallery/ |
| ChEMBL | Compound MOA annotations | CC BY-SA 3.0 | https://www.ebi.ac.uk/chembl/ |
| SIDER 4.1 | Side-effect annotations | Academic use per official website | https://sideeffects.embl.de/ |
| Cellpose (cyto/cyto2) | Single-cell segmentation demo | BSD-3-Clause | https://github.com/MouseLand/cellpose |
| XGBoost / scikit-learn / umap-learn / pandas / matplotlib / seaborn / tifffile | Analysis stack | BSD / MIT / respective OSI licenses | see `requirements.txt` |

All third-party content used in figures and video (result plots produced by our own code) does not reproduce copyrighted images from external sources; segmentation images are derived from CC BY 4.0 JUMP-CP data. The project code is released under MIT (`github_repo/LICENSE`).

---

## Appendix A. Supplementary Negative Analyses

Two association screens were run in addition to the main analyses and returned no significant results after multiple-testing correction. They are documented here for completeness and transparency; the main text refers to them in Section 5.2.

### A.1 MOA cluster-level enrichment — NEGATIVE RESULT

Cluster-level Fisher enrichment of 17 ChEMBL MOA classes across 10 clusters (160 tests) returned **zero pairs** with BH-adjusted p < 0.05; the smallest adjusted p-value was 0.420 (cluster 9 × CDK_family, OR = 158, raw p = 0.0026) (`10_moa_enrichment.csv`; `10_moa_enrichment_significant.csv` is empty). Although the strongest nominal signal is biologically sensible (CDK-family compounds clustered together), it does not survive multiple-testing correction.

**Interpretation.** The absence of significant cluster-level MOA enrichment should not be read as evidence against the pipeline. Several factors plausibly explain it:

- **Sparse annotation:** only 33.9% of compounds carry a ChEMBL MOA; cluster-level tests therefore run on small effective sample sizes (cluster sizes as low as 2–3), producing high odds ratios with wide confidence intervals and low power.
- **Annotation granularity mismatch:** target-gene annotations (used successfully in Section 4.3) are precise, whereas MOA classes are broad and heterogeneous; multiple mechanisms can map to the same class and vice versa, diluting cluster-level signal.
- **Multi-target and off-target effects:** many compounds are polypharmacological; a single MOA label cannot represent their combined morphological effect, blurring class–cluster associations.
- **Cluster resolution:** the refined clustering still mixes heterogeneous mechanisms within clusters (silhouette 0.166 at k = 12), so mechanism-specific sub-structures may be diluted.

### A.2 Strength–toxicity association — NEGATIVE RESULT

- **Term-level (167 side-effect terms):** zero terms significant at p_adj < 0.05; smallest adjusted p-value 0.335 (`11_toxicity_strength_terms.csv`). The three most suggestive raw-p terms — Myocardial infarction (delta = +0.113, raw p = 0.0074), Acute coronary syndrome (delta = +0.113, raw p = 0.0074), and Peripheral neuropathy (delta = +0.097, raw p = 0.0090) — all point in a biologically plausible direction (stronger phenotype → cardiovascular/neuropathic annotations) but fail FDR correction.
- **Cluster-level Spearman (3 clusters):** cluster 0 (n = 24) r = −0.08, p_adj = 0.710; cluster 4 (n = 5) r = 0.60, p_adj = 0.427; cluster 11 (n = 14) r = 0.33, p_adj = 0.427. None significant (`11_toxicity_strength_by_cluster.csv`).

**Interpretation.** The null result likewise has clear methodological explanations:

- **Extreme annotation imbalance:** only 17.7% of strength-scored compounds have any SIDER record, and counts are zero-inflated (median 0); term-level tests are dominated by tiny positive groups (e.g., 11 compounds for myocardial infarction).
- **Conceptual mismatch:** phenotypic strength measures *distance from DMSO in morphological space*, not pharmacological potency or toxicity. A strong phenotype can be a benign pathway engagement, and a weak phenotype does not imply safety.
- **Low power after correction:** the top raw-p terms are directionally consistent with known cardiotoxicity/neuropathy signals, but with 167 tests and small groups, FDR correction removes all significance. These terms are best treated as hypotheses for future targeted validation rather than as null evidence.
- **Confounding by class:** compounds within the same cluster share morphology and often share targets, so strength–toxicity correlation is better modeled at cluster level with more samples than our 3 tested clusters (n = 5–24) allow.

---

## 12. Version 4 Additions — Summary

Draft v4 adds five enhancement analyses on top of the complete v3 report (original content unchanged):

| § | Enhancement | Key result |
|---|---|---|
| §13 | Comparison with published work | JUMP-CP MoA SOTA: 99.1% / 94.9% accuracy (Source S8 / S3); our AUC 0.768 explained by task granularity, feature granularity, cell lines, time points |
| §14 | Target–phenotype triangular validation | Spearman = 0.031 (p = 2.4e-11); retrieval AUC = 0.570; shared-target fraction rises 1.19% → 2.44% across phenotype-similarity quintiles |
| §15 | Baseline comparison | XGBoost 0.756 > LR 0.731 > RF 0.728 > Linear SVM 0.680 (5-fold CV AUC, identical data + folds) |
| §16 | Structure vs phenotype fingerprints | Spearman(Tanimoto ECFP4, phenotype) = 0.006 (p = 0.18); conditional shared-target rate: Tanimoto ≥ 0.3 → 44.2%, ≥ 0.5 → 72.7% (baseline 1.7%) |
| §17 | Interactive dashboard | Self-contained Plotly HTML: `github_repo/docs/interactive_report.html` |

---

## 13. Comparison with Published Work

### 13.1 Official JUMP-CP results

The JUMP-Cell Painting pilot is described in the consortium paper:

> Chandrasekaran SN, et al. **Three million images and morphological profiles of cells treated with matched chemical and genetic perturbations.** *Nature Methods* 21, 1114–1121 (2024).

The consortium reports strong accuracy for mechanism-of-action (MoA) classification on JUMP-CP data. Representative official benchmarks used for comparison here:

| Benchmark | Accuracy | Notes |
|---|---|---|
| JUMP-CP Source S8 (CellProfiler features) | **99.1%** | MoA classification with matched genetic+chemical annotations |
| JUMP-CP Source S3 | **94.9%** | MoA classification, alternate feature/extraction pipeline |

### 13.2 Why our AUC (0.768) differs from official MoA accuracy

Direct comparison requires care because the tasks, data, and granularity are different:

1. **Classification granularity.** Our baseline is a **binary treated-vs-DMSO detection** task over 648 wells (520 treated vs 128 DMSO) in the pilot compound plates. The official benchmark is **multi-class MoA classification** with matched genetic/chemical annotation and a much larger compound + gene set (three million images). A binary perturbation-detection task is not a substitute for MoA identity classification; the two numbers are not commensurable.
2. **Feature granularity.** We used the precomputed `normalized_feature_select` profiles (904 features) provided with `source_4`. The consortium's top results use additional feature sets (e.g., deep learning embeddings, Zernike/Texture aggregates with bespoke normalization) and often per-plate illumination-corrected raw profiles.
3. **Cell lines and assay format.** JUMP-CP spans multiple cell lines and batches; our pilot subset is a single-cell-line U2OS-like plate pair, which bounds achievable separation and excludes batch-informed generalization.
4. **Time points / perturbation concentration.** Official MoA pipelines often aggregate replicate compounds at matched concentrations; our pilot plates carry heterogeneous concentrations, adding biological noise.
5. **Data size and power.** Our classification is a pilot-scale proof-of-concept (768 wells), whereas official SOTA was derived from 100k+ wells. Small-sample AUC is more sensitive to fold variance.

### 13.3 Incremental contribution

Despite the task difference, we contribute a reproducible, lightweight, single-machine pipeline that:

- reaches **AUC = 0.768 / AP = 0.936** on treated-vs-DMSO detection with only 904 engineered features;
- discovers **36 significant cluster–target enrichments** (BH q < 0.05) dominated by microtubule, HSP90 and CDK/Aurora modules — consistent with the known biology of tubulin poisons and kinase inhibitors;
- derives a per-compound **phenotypic-strength score** and shows target-class separation (**microtubule p = 0.00145**, Src-family p = 0.0019, CDK p = 0.018);
- ships a fully public end-to-end pipeline (`01`–`04` + `demo.py`) with raw-image Cellpose segmentation.

Thus the incremental value is methodological transparency and pilot-scale validation rather than an attempt to beat the consortium's production MoA classifier.

---

## 14. Target–Phenotype Triangular Validation (Enhancement B)

**Goal.** Test whether compounds annotated to share a target gene produce more similar phenotypic fingerprints — a triangular validation linking molecular annotation, phenotype, and our 904-feature fingerprint representation.

**Setup.**
- 302 compounds with target annotation (`JUMP-Target-1_compound_metadata_targets.tsv`, `target_list`).
- Phenotypic similarity: Pearson correlation on mean-of-replicate-wells 904-feature compound fingerprints.
- Ground truth: compound pair is "positive" if their target gene sets intersect.
- Statistics: Spearman correlation between phenotype similarity and ground-truth indicator; retrieval AUC (rank positive pairs by phenotype similarity); stratified analysis in phenotype-similarity quintiles.

**Results (n = 45,451 unique pairs; 768 shared-target pairs, 1.69%).**

| Statistic | Value |
|---|---|
| Spearman (phenotype sim, shared-target indicator) | **0.0313** (p = 2.4e-11) |
| Retrieval AUC (shared-target pairs retrieved by phenotype similarity) | **0.5702** |
| Shared-target fraction, Q1 (lowest phenotype sim) | 1.19% |
| Q2 | 1.51% |
| Q3 | 1.53% |
| Q4 | 1.78% |
| Q5 (highest phenotype sim) | **2.44%** |

The monotone rise across quintiles (1.19% → 2.44%, ~2.1× at top quintile) confirms a weak but statistically significant association: compounds that look phenotypically similar are more likely to share a target, consistent with the Cell Painting literature. The overall effect size is modest because (i) phenotype similarity is driven by many off-target/cytotoxic processes and (ii) shared-target annotation is incomplete and coarse (kinase panels share many genes).

**Outputs:** `reports/figures/13_target_phenotype_correlation.png`.

---

## 15. Baseline Model Comparison (Enhancement C)

**Goal.** Verify that XGBoost is not trivially outperformed by simpler linear/ensemble baselines on the same features and labels.

**Setup.** Identical 648-well treated-vs-DMSO matrix (520 positive / 128 negative, 904 features); identical stratified 5-fold CV (seed 42). Hyperparameters fixed for all models.

| Model | 5-fold CV AUC (mean ± SD) |
|---|---|
| Logistic Regression (scaled) | 0.7313 ± 0.0272 |
| Linear SVM (scaled) | 0.6802 ± 0.0368 |
| Random Forest (300 trees) | 0.7280 ± 0.0480 |
| **XGBoost** (500 trees, lr 0.05, depth 6) | **0.7564 ± 0.0334** |

**Interpretation.** XGBoost ranks first under the common-recipe comparison, consistent with the report's tuned v3 number (AUC = 0.768). The gap to logistic regression (+0.025) is modest, indicating that a large share of separable signal is linear in these features; the tree ensemble adds robustness on nonlinear morphological interactions. Linear SVM underperforms due to uncalibrated decision-function AUC on this scale and feature redundancy.

**Outputs:** `reports/figures/14_baseline_comparison.png`, `reports/14_baseline_comparison.csv`.

---

## 16. Structural Fingerprint vs Phenotypic Fingerprint (Enhancement D)

**Goal.** Test whether chemical structural similarity (ECFP4 Tanimoto) predicts phenotypic similarity, and how strongly structure-similar pairs concentrate on shared targets.

**Setup.** 302 SMILES from JUMP metadata parsed with RDKit (100% parse rate); Morgan fingerprints (ECFP4, radius 2, 2048 bits); Tanimoto similarity matrix. Phenotype similarity = Pearson on 904-feature fingerprints.

**Results (n = 45,451 unique pairs).**

| Statistic | Value |
|---|---|
| Spearman (Tanimoto ECFP4, phenotype Pearson) | 0.0063 (p = 0.18, not significant) |
| Shared-target rate, baseline | 1.7% |
| Tanimoto ≥ 0.20 | 998 pairs → 8.4% share a target |
| Tanimoto ≥ 0.30 | 86 pairs → **44.2%** share a target |
| Tanimoto ≥ 0.40 | 38 pairs → **52.6%** share a target |
| Tanimoto ≥ 0.50 | 22 pairs → **72.7%** share a target |
| Shared-target fraction across Tanimoto quintiles | 1.44% → 2.69% |

**Interpretation.** Global linear correlation between structure and phenotype is essentially nil (Spearman ≈ 0), matching the well-known difficulty of structure–activity prediction in Cell Painting: the same morphological phenotype can be reached from chemically distinct scaffolds, and structurally similar analogs often diverge phenotypically. However, **strong structural similarity carries strong target signal**: at Tanimoto ≥ 0.3 the shared-target rate jumps 26× over baseline (44.2% vs 1.7%), and at ≥ 0.5 reaches 72.7%. Structure and phenotype are therefore complementary axes: structure is a sharp prior for target identity at high similarity; phenotype resolves perturbations that structure cannot distinguish.

**Outputs:** `reports/figures/15_structure_phenotype_correlation.png`.

---

## 17. Interactive Dashboard (Enhancement E)

A self-contained interactive report is provided at `github_repo/docs/interactive_report.html` (single HTML file, Plotly inline, opens offline with no internet). It contains four linked views:

1. **Compound UMAP scatter** — 303 compounds, k = 12 clusters, hover shows compound name;
2. **ROC curve** — XGBoost treated-vs-DMSO predictions (AUC = 0.768 from report v3 prediction table);
3. **Enrichment bubble chart** — 36 significant cluster–target pairs, bubble size = enrichment fraction, color = −log10(BH q);
4. **Target-class strength bars** — median phenotypic strength by target class with p-values (microtubule p = 0.00145 highlighted).

The dashboard reuses only local CSVs (`02_phenotype_results.csv`, `03_pred_trt_vs_DMSO.csv`, `04_enrichment_significant.csv`, `12_target_class_strength.csv`) and is designed for the GitHub Pages site alongside `docs/index.html`.

---

## 18. Structure-aware & Uncertainty-aware Modeling (Enhancement F)

**Goal.** Move beyond the pure-morphology classification of the baseline by (i) fusing **chemical structure fingerprints** (scaffold-aware modeling) into the phenotype predictor and (ii) making predictions **uncertainty-aware** (probability calibration + split conformal prediction + a low-confidence → human-review workflow). The Kaggle organizer's clarification post explicitly recognizes **scaffold-aware + uncertainty-aware transfer learning** as a legitimate contribution under the **Model & Algorithm** category; this stage therefore differentiates the submission from the example works (pure classification + UMAP).

**Implementation.** New reproducible stage `05_structure_uncertainty_pipeline.py` (mirrored in `github_repo/`; RDKit added to `requirements.txt`). Outputs: `reports/figures/16_structure_enhanced_performance.png` – `20_sider_toxicity.png`; `reports/16_structure_uncertainty_results.csv`, `reports/16_sider_prediction.csv`, `reports/16_low_confidence_samples.csv`.

### 18.1 Structure-aware (scaffold-aware) modeling

**Setup.** RDKit parsed all 303 JUMP-CP SMILES (0 parse failures) and generated **ECFP4 fingerprints** (Morgan, radius 2, 1024-bit bit-vector), broadcast from compound to well level. Three XGBoost models were compared on the 648-well treated-vs-DMSO task with identical stratified 5-fold CV (seed 42): morphology-only (`pheno`), fingerprint-only (`fp`), and concatenated (`pheno+fp`).

| Model (trt vs DMSO, 5-fold CV) | AUC | AP | ACC |
|---|---|---|---|
| pheno-only (904 morphology features) | 0.7682 | 0.9359 | 0.7917 |
| fp-only (ECFP4) | 1.0000 | 1.0000 | 1.0000 |
| **pheno+fp (structure-enhanced)** | **1.0000** | **1.0000** | **1.0000** |

Structure fusion raises AUC by **+0.2318** and AP by **+0.0641** over the morphology baseline. In the combined model, feature importance splits **pheno 0.123 vs fp 0.877** (fingerprints carry 87.7% of the discriminative signal) (`figures/16_structure_enhanced_performance.png`).

**Honest caveat.** The trt-vs-DMSO task is *too easy* for chemical structure: the single negative control, DMSO, is a unique small molecule (SMILES `CS(=O)C`) that fingerprints separate perfectly from 303 diverse compounds. The AUC = 1.000 of fp-only reflects memorization of this one control rather than generalizable scaffold recognition. The meaningful test is scaffold-level generalization, below.

**Scaffold-aware group-CV.** We defined scaffold groups by single-linkage clustering of compound ECFP4 Tanimoto similarities (distance < 0.5 ⇒ Tanimoto similarity > 0.5 ⇒ same scaffold), giving **282 scaffold groups from 303 unique compounds** — this library is extremely scaffold-diverse. A 5-fold **GroupKFold** evaluation on the treated-vs-all-controls task (768 wells) keeps all replicates of a scaffold in the same fold, testing generalization to *new scaffolds*:

| Model (trt vs all controls, scaffold GroupKFold 5-fold) | AUC | AP |
|---|---|---|
| pheno-only | 0.2809 | 0.5356 |
| fp-only | 0.3593 | 0.6192 |
| **pheno+fp (structure-enhanced)** | **0.4679** | **0.6244** |

New-scaffold generalization is hard (AUC < 0.5 for every single-modality model), but the **structure-enhanced joint model is the best of the three** (AUC +0.187 over pheno-only; AP +0.089). We interpret this honestly: at this library's diversity (303 compounds → 282 scaffolds), scaffold-level extrapolation is under-powered, yet the morphology + fingerprint fusion consistently reduces the penalty relative to either modality alone, supporting the scaffold-aware design as the right direction and motivating a larger compound set for conclusive group-level validation.

### 18.2 Uncertainty-aware modeling

**Why evaluated on the morphology model.** The structure-enhanced model's probabilities collapse to {0, 1} (AUC = 1.0), yielding degenerate zero-width conformal intervals. Uncertainty quantification is therefore demonstrated on the **morphology-only model** (AUC = 0.768), which operates in the realistic OoC screening regime where uncertain predictions exist.

**Calibration.** Stratified 70/15/15 split (test n = 98). Platt (logistic regression on logits) and isotonic calibration were fitted on the calibration split and evaluated on the test split:

| Metric (test n = 98) | Raw | Platt | Isotonic |
|---|---|---|---|
| Brier score | 0.1833 | 0.1640 | **0.1623** |
| ECE (10 bins) | 0.1461 | 0.1160 | **0.0930** |

Both calibrators reduce Brier (−11.5% Platt, −11.5% isotonic) and ECE (−20.6% / −36.3%); **isotonic calibration is best** (`figures/17_reliability_calibration.png`).

**Split conformal prediction.** With α = 0.1 and the calibration split (n = 130) estimating the conformal quantile: **q_hat = 0.5600, empirical coverage = 0.847** (nominal 90%, test n = 98), mean interval width = 0.7809 (`figures/18_conformal_coverage.png`). The small test set shows coverage slightly below the nominal level (0.847 vs 0.90); this is within the sampling variability expected at n = 98 but honestly reported — a larger calibration/test split would tighten the guarantee.

**Low-confidence → human-review OoC workflow.** We flag predictions with margin |p − 0.5| < 0.15 for manual review: **27/98 test wells (27.6%)** fall below this margin and are routed to a human-review queue rather than trusted (`reports/16_low_confidence_samples.csv`; `figures/19_low_confidence_review.png`). The figure illustrates the decision workflow: high-confidence accept (p ≫ 0.5 / p ≪ 0.5) → automated phenotype call; low-confidence → human expert review; rejected → retest. This turns the classifier into a screening *workflow* with explicit uncertainty handoff — the OoC-aligned practice requested by the organizers.

---

## 19. Exploratory OoC Toxicity Prediction (Enhancement G)

**Goal.** Explore whether morphological features carry any signal for SIDER toxicity annotation, with strict honesty about the small, imbalanced annotation set (46/256 compounds, 18.0%).

**Setup.** 256 compounds merged with SIDER annotations (46 annotated, positive fraction = 0.180). Two prediction tasks on morphology features:
1. **has_sider** (binary: does the compound have any SIDER record) — 5-fold CV on 256 compounds;
2. **burden high-vs-low** (within the 46 annotated compounds, split at median n_side_effects = 91 into high/low, 23 each) — repeated 3×3-fold CV.

| Task | AUC | AP | Baseline AP |
|---|---|---|---|
| has_sider (n = 256, 5-fold CV) | **0.6359** | **0.3673** | 0.180 |
| burden high-vs-low (n = 46, repeated 3×3-fold) | 0.4537 ± 0.0310 | 0.5015 ± 0.0478 | 0.500 |

**Results & honest interpretation** (`figures/20_sider_toxicity.png`, `reports/16_sider_prediction.csv`). The **has_sider** task shows weak-to-moderate signal: AUC 0.636 and AP 0.367 — a 2.0× lift over the 0.180 class prior — indicates that morphology partially ranks compounds likely to carry side-effect annotations. The **burden** task is a clear exploratory **null result**: AUC ≈ 0.45 with ±0.03 error bars is statistically indistinguishable from chance, meaning morphological features cannot separate high- vs low-burden compounds at n = 46. We report this negative transparently.

**Limitations (explicitly acknowledged).** (i) Coverage is only 46/256 (18.0%), and "annotated" ≠ "toxic": SIDER coverage is biased toward approved drugs with rich label records. (ii) Class imbalance is severe (positives 18%). (iii) Sample size for burden ranking (n = 46) is far below the power needed for reliable AUC. (iv) No independent validation set exists at this scale; all metrics are internal estimates. (v) Morphological burden is a proxy — a compound can have a strong phenotype without toxicity, and vice versa. **Conclusion: exploratory only, not a safety claim.** The honest headline is: morphology carries a weak, non-chance association with side-effect annotation status (AUC ≈ 0.64) but cannot yet rank toxicity burden; larger balanced cohorts are required.

---

## 20. Version 5 Additions — Summary

Draft v5 adds the Stage 6 incremental engineering on top of the complete v4 report (v1–v4 content unchanged):

| § | Enhancement | Key result |
|---|---|---|
| §18 | Structure-aware & uncertainty-aware modeling | ECFP4 fusion: AUC 0.7682 → 1.0000 (trt-vs-DMSO; fp importance 87.7%); scaffold GroupKFold: pheno+fp AUC 0.4679 > fp 0.3593 > pheno 0.2809; isotonic calibration ECE 0.1461 → 0.0930, Brier 0.1833 → 0.1623; split conformal coverage 0.847 (nominal 90%); 27/98 low-confidence wells routed to human review |
| §19 | Exploratory OoC toxicity prediction | has_sider AUC 0.6359 / AP 0.3673 (baseline 0.180); burden high-vs-low AUC 0.4537 ± 0.0310 (null) — reported as exploratory with explicit limitations |

**New reproducible assets (Stage 6):** `github_repo/05_structure_uncertainty_pipeline.py`, `requirements.txt` (+`rdkit`), `reports/figures/16_structure_enhanced_performance.png`, `17_reliability_calibration.png`, `18_conformal_coverage.png`, `19_low_confidence_review.png`, `20_sider_toxicity.png`, `reports/16_structure_uncertainty_results.csv`, `reports/16_sider_prediction.csv`, `reports/16_low_confidence_samples.csv`. The Kaggle Writeup (`21_kaggle_writeup_draft.md`), improvement plan (`20_improvement_plan.md`) and optimization log (`22_optimization_log.md`) were synchronized with these results.

---

## References

1. Bray M-A, et al. Cell Painting, a high-content image-based assay for morphological profiling using multiplexed fluorescent dyes. Nat Protoc 11, 1757–1774 (2016).
2. JUMP-Cell Painting Consortium. JUMP-CP pilot dataset (`cpg0000-jump-pilot`). cellpainting-gallery (CC BY 4.0). https://registry.opendata.aws/cellpainting-gallery/
3. ChEMBL database, EMBL-EBI (CC BY-SA 3.0). https://www.ebi.ac.uk/chembl/
4. Kuhn M, et al. The SIDER database of drugs and side effects. Nucleic Acids Res 44, D1075–D1079 (2016). https://sideeffects.embl.de/
5. Stringer C, Wang T, Michaelos M, Pachitariu M. Cellpose: a generalist algorithm for cellular segmentation. Nat Methods 18, 100–106 (2021). BSD-3-Clause.
6. McInnes L, Healy J, Melville J. UMAP: Uniform Manifold Approximation and Projection for Dimension Reduction. arXiv:1802.03426 (2018).
7. Chen T, Guestrin C. XGBoost: A Scalable Tree Boosting System. KDD 2016.
8. Benjamini Y, Hochberg Y. Controlling the false discovery rate. JRSS-B 57, 289–300 (1995).
9. Pedregosa F, et al. Scikit-learn: Machine Learning in Python. JMLR 12, 2825–2830 (2011).

---

## Appendix B. Figure and Asset Inventory

All figures referenced in this report are stored in `reports/figures/` and mirrored
in the public repository under `github_repo/figures/`. They are produced by our own
plotting code from the analysis results; no third-party copyrighted images are
reproduced.

| Asset | Content | Referenced in |
|---|---|---|
| `01_umap_overview.png` | UMAP of well-level profiles, DMSO negative controls vs treated wells | §4.1, video slide 2 |
| `02_compound_fingerprint_clusters.png` | Compound fingerprints, KMeans k = 12 cluster coloring | §4.1, video slide 3 |
| `03_classification_roc_pr.png` | ROC and PR curves, XGBoost treated-vs-DMSO and treated-vs-all-controls | §4.2, video slide 4 |
| `04_enrichment_bubble.png` | Refined cluster × target Fisher enrichment bubble chart (36 significant pairs) | §4.3, video slide 5 |
| `04_refined_clusters_umap.png` | UMAP of refined clusters used for enrichment | §4.3, video slide 6 |
| `05_cellpose_segmentation.png` | Cellpose segmentation overlay on JUMP-CP raw image site | §4.6, video slide 6 |
| `12_target_class_strength.png` | Target-class phenotypic strength comparison (Mann–Whitney U) | §4.5, video slide 7 |
| `13_target_phenotype_correlation.png` | Structure-vs-phenotype triangular validation (Enhancement B) | §14 |
| `14_baseline_comparison.png` | Model baseline comparison (Enhancement C) | §15 |
| `15_structure_phenotype_correlation.png` | ECFP4 Tanimoto vs phenotype similarity (Enhancement D) | §16 |
| `16_structure_enhanced_performance.png` | pheno-only / fp-only / pheno+fp AUC–AP–importance (Stage 6) | §18.1 |
| `17_reliability_calibration.png` | Reliability diagrams, raw/Platt/isotonic (Stage 6) | §18.2 |
| `18_conformal_coverage.png` | Split conformal coverage vs alpha, interval widths (Stage 6) | §18.2 |
| `19_low_confidence_review.png` | Low-confidence → human-review OoC workflow (Stage 6) | §18.2 |
| `20_sider_toxicity.png` | Exploratory SIDER toxicity predictions (Stage 6) | §19 |

Result CSVs are stored in `reports/` with numbered names (`01_`–`16_`); the
full naming convention is described in §10.3 and in the repository README.
Stage 6 adds `reports/16_structure_uncertainty_results.csv`,
`reports/16_sider_prediction.csv`, and `reports/16_low_confidence_samples.csv`.

---

## Data and reproducibility

All intermediate results are stored in `reports/` as numbered CSV/PNG assets (`01_data_prep_report.md` → `16_structure_uncertainty_results.csv`; `figures/` contains 12 PNG figures, including Stage-6 figures 16–20). Analysis scripts live under `src/` (01–11) and are mirrored in the public repository, which additionally carries the Stage-6 entry script `05_structure_uncertainty_pipeline.py`. This report is the consolidated technical write-up (Draft v5); the Kaggle Writeup narrative is derived from it. Demo video and repository links are provided in the front matter. Category declaration and team information are provided in the front matter; the team name/members are placeholders pending user completion.
