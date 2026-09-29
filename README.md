---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 1b7b0544872f18baedbb33526952b8c3_0011f813bba411f189c8525400393706
    ReservedCode1: CqvlcRU/0P2wzu905Mhf28mpKVYxRwwPFeb/zW59ri/tzF/kPHPZXf3sBK7s1KG7JdVkWtDZP3+41l+xMF9+a+ZPSsVWrOxB6IDvAyMpV07xDW0mozgmWP0+jSfIY2/ZX6C/k70MYkghPatZSpHemewuTAFodWXmx1Q7AdoBTkBhXzRsMRrRSbr12Sw=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 1b7b0544872f18baedbb33526952b8c3_0011f813bba411f189c8525400393706
    ReservedCode2: CqvlcRU/0P2wzu905Mhf28mpKVYxRwwPFeb/zW59ri/tzF/kPHPZXf3sBK7s1KG7JdVkWtDZP3+41l+xMF9+a+ZPSsVWrOxB6IDvAyMpV07xDW0mozgmWP0+jSfIY2/ZX6C/k70MYkghPatZSpHemewuTAFodWXmx1Q7AdoBTkBhXzRsMRrRSbr12Sw=
---

# Morphological Phenotypic Profiling of Chemical Perturbations with JUMP-Cell Painting Data

**Competition:** AI4S Open Innovation: AI for Life Science (Hackathon — Kaggle Writeup)
**Direction:** Single-cell phenotypic analysis (Cell Painting morphology)
**Team:** AI4S Hackathon Team

A compact, end-to-end pipeline that turns Cell Painting morphology into biologically
interpretable knowledge about chemical perturbations: separation of treated vs control
wells, compound phenotypic fingerprints, target enrichment, per-compound phenotypic
strength scoring, and a single-cell segmentation demo.

---

## 1. Project Overview

Phenotypic profiling with Cell Painting provides an unbiased, image-based readout of
cellular state. On the **JUMP-Cell Painting pilot (JUMP-CP) `source_4`** dataset we
built a pipeline covering **303 compounds measured in 1,536 wells** with **904
precomputed morphological features**. The pipeline (i) reduces and clusters
compound-level fingerprints (UMAP + KMeans), (ii) trains a gradient-boosted baseline
to separate treated wells from DMSO controls, (iii) runs cluster × target Fisher
enrichment with BH correction, (iv) derives a per-compound phenotypic-strength score,
and (v) demonstrates single-cell segmentation with Cellpose on raw 8-channel images.

## 2. Pipeline (scripts run in order)

| # | Script | Stage | Key outputs |
|---|--------|-------|-------------|
| 1 | `01_phenotypic_profiling.py` | Fingerprints & clustering | `reports/figures/01_umap_overview.png`, `02_compound_fingerprint_clusters.png`, `reports/02_phenotype_results.csv` |
| 2 | `02_classification_target.py` | Classification baseline + target consistency | `reports/figures/03_classification_roc_pr.png`, `reports/03_target_validation.csv`, `reports/03_pred_*.csv` |
| 3 | `03_enrichment_strength.py` | Refined clusters, Fisher enrichment, strength score | `reports/figures/04_enrichment_bubble.png`, `04_refined_clusters_umap.png`, `reports/04_enrichment*.csv`, `04_phenotypic_strength.csv` |
| 4 | `04_cellpose_demo.py` | Cellpose single-cell segmentation demo | `reports/figures/05_cellpose_segmentation.png`, `reports/05_cellpose_summary.csv` |

Method flow: well-level CellProfiler profiles → standardize (z-score) → compound
fingerprint = mean over replicate wells → UMAP visualization → KMeans / Ward
hierarchical clustering → XGBoost 5-fold CV classification → Fisher exact enrichment
(BH FDR) → phenotypic-strength score = mean P(treated) over replicate wells →
Cellpose (cyto2) segmentation of the DNA channel.

## 3. Reproduction Steps

1. Clone this repository.
2. Create a virtual environment and install dependencies:

   ```bash
   pip install -r requirements.txt
   # optional (only for script 04):
   pip install cellpose torch
   ```

3. Download the data and place it as follows:

   ```
   data/
     profiles/        # *_normalized_feature_select_negcon_batch.csv.gz from JUMP-CP source_4
     metadata/        # JUMP-Target-1_compound_metadata_targets.tsv and plate metadata
     raw/BR00116991/  # 8-channel TIFFs (only needed for the Cellpose demo)
   ```

4. Run the scripts in order (from the repository root):

   ```bash
   python 01_phenotypic_profiling.py
   python 02_classification_target.py
   python 03_enrichment_strength.py
   python 04_cellpose_demo.py   # optional; requires cellpose + torch
   ```

   Scripts read/write relative to the repository root and will create
   `reports/figures/` and result CSVs automatically.

5. (Optional) Rebuild the demo video from the seven figure PNGs:

   ```bash
   python scripts/make_demo_video.py
   ```

   → outputs `demo_video.mp4` (1280×720, 42 s, 30 fps, English titles,
   cross-fade transitions). Requires `pip install pillow imageio-ffmpeg`.

## 4. Data Sources

- **Primary imaging data:** JUMP-CP pilot dataset (`cpg0000-jump-pilot`, `source_4`)
  from the public `cellpainting-gallery` S3 bucket (no authentication required).
  We used the four plates of this source: two compound plates (`BR00116991`,
  `BR00116992`, 303 unique compounds, 4 replicates each) and two ORF/CRISPR plates
  (excluded from chemical analysis).
- **Compound metadata:** names, target genes, SMILES, barcode–platemap mapping
  (JUMP-Target-1 compound metadata, `data/metadata/`).
- **External annotations (optional downstream analyses):** ChEMBL MOA and SIDER
  side-effect annotations are used in the extended technical report.

## 5. Results Summary

- **UMAP + KMeans (k = 12, silhouette = 0.166):** DMSO negative controls separate
  clearly from treated compounds; clusters are uneven in size (cluster 0 = 143
  compounds, mostly weak/near-control phenotypes).
- **Classification (XGBoost, 5-fold CV):** treated vs DMSO — **AUC = 0.768,
  AP = 0.936, ACC = 0.792** (648 wells); treated vs all controls — AUC = 0.687,
  AP = 0.816, ACC = 0.697 (768 wells). Top features are classical morphological
  indicators (cytoplasmic intensity MAD, nuclear Zernike, AGP texture).
- **Target enrichment:** **36 significant cluster–target pairs** at BH-adjusted
  p < 0.05, dominated by a microtubule module (cluster 13, 15 tubulin genes),
  HSP90 (cluster 1), and CDK/Aurora cell-cycle kinases (cluster 4) — recovering
  known Cell Painting pharmacology.
- **Target-class strength (Mann–Whitney U):** microtubule/tubulin compounds show
  significantly stronger phenotypic responses than the rest (median 0.9958 vs
  0.9368, Cliff's delta = 0.827, p = 0.00145), as do Src-family kinase
  (p = 0.0019) and CDK (p = 0.018) families.
- **Negative results (reported transparently in the technical report):** MOA
  cluster-level enrichment and strength–toxicity association were not significant
  after multiple-testing correction, consistent with sparse annotation coverage.

## 6. Figures

All figures are generated under `reports/figures/` by the scripts above
(they live outside this repository folder but are referenced here for the
Hackathon submission):

- [01_umap_overview.png](../reports/figures/01_umap_overview.png) — UMAP of wells, DMSO vs treatments
- [02_compound_fingerprint_clusters.png](../reports/figures/02_compound_fingerprint_clusters.png) — compound fingerprints, KMeans k=12
- [03_classification_roc_pr.png](../reports/figures/03_classification_roc_pr.png) — ROC / PR curves
- [04_enrichment_bubble.png](../reports/figures/04_enrichment_bubble.png) — cluster × target enrichment bubble chart
- [04_refined_clusters_umap.png](../reports/figures/04_refined_clusters_umap.png) — refined cluster UMAP
- [05_cellpose_segmentation.png](../reports/figures/05_cellpose_segmentation.png) — Cellpose segmentation demo
- [12_target_class_strength.png](../reports/figures/12_target_class_strength.png) — target-class phenotypic strength

A narrated demo video is included:

- [demo_video.mp4](demo_video.mp4) — 7-slide overview (1280×720, 42 s, 30 fps)

## 7. License

MIT — see [LICENSE](LICENSE).
*（内容由AI生成，仅供参考）*
