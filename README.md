---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 1b7b0544872f18baedbb33526952b8c3_58d2727abbab11f189c8525400393706
    ReservedCode1: ownNAWLP0eWVo/dlUfOk3PAPUSguIUG2R0GPF+nkPbae3Bt8qUitJQvOdxLVH5CYsfS1Wk36XDjthsexRD5fJ5EjiAwhx/KMYB4EYwxTMCHm+QQiQ4XrN+GyDmARkpS6u1F6H9tC0sZGklRtWYoLxoPPhzqq+7iajXszYq4vmgqhUkNp58iAkcQEKIY=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 1b7b0544872f18baedbb33526952b8c3_58d2727abbab11f189c8525400393706
    ReservedCode2: ownNAWLP0eWVo/dlUfOk3PAPUSguIUG2R0GPF+nkPbae3Bt8qUitJQvOdxLVH5CYsfS1Wk36XDjthsexRD5fJ5EjiAwhx/KMYB4EYwxTMCHm+QQiQ4XrN+GyDmARkpS6u1F6H9tC0sZGklRtWYoLxoPPhzqq+7iajXszYq4vmgqhUkNp58iAkcQEKIY=
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
| — | `demo.py` | **Entry script** — one-command demo / full pipeline runner | summary on stdout; runs 01–04 with `--full` |

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

   ```bash
   # The data are public in the cellpainting-gallery S3 bucket (AWS Open Data,
   # no sign-in required). S3 prefix: cpg0000-jump-pilot/source_4
   # Bucket browser: https://registry.opendata.aws/cellpainting-gallery/

   # 3a. Morphological profiles (normalized, feature-selected, per plate):
   aws s3 cp --no-sign-request --recursive \
     s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/workspace/profiles/ \
     data/profiles/

   # 3b. Metadata (compound metadata, targets, barcode–platemap):
   aws s3 cp --no-sign-request --recursive \
     s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/workspace/metadata/ \
     data/metadata/

   # 3c. Raw 8-channel TIFFs for the Cellpose demo (one plate is enough):
   aws s3 cp --no-sign-request --recursive \
     s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/images/BR00116991/ \
     data/raw/BR00116991/
   ```

   Expected layout:

   ```
   data/
     profiles/        # *_normalized_feature_select_negcon_batch.csv.gz from JUMP-CP source_4
     metadata/        # JUMP-Target-1_compound_metadata_targets.tsv and plate metadata
     raw/BR00116991/  # 8-channel TIFFs (only needed for the Cellpose demo)
   ```

   > If a path component differs on the live bucket, list the parent prefix and
   > adjust: `aws s3 ls --no-sign-request s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/`

4. Run the pipeline. **Recommended entry point (one command):**

   ```bash
   python demo.py          # lightweight demo: prints a summary of existing results
   python demo.py --full   # runs stages 01 → 04 in order
   python demo.py --stage 3  # run a single stage (1..4)
   ```

   Or run the stage scripts directly, in order:

   ```bash
   python 01_phenotypic_profiling.py
   python 02_classification_target.py
   python 03_enrichment_strength.py
   python 04_cellpose_demo.py   # optional; requires cellpose + torch
   ```

   Scripts read/write relative to the repository root and will create
   `reports/figures/` and result CSVs automatically.

   Stage 5–6 extension scripts (structure-aware modeling, uncertainty-aware
   modeling, exploratory SIDER screen, in-house deep model, deep-embedding
   comparison, single-cell CNN) run on the same data and are asset-gated
   (each sub-step checks data availability first and prints a download hint
   if a file is missing):

   ```bash
   python 05_structure_uncertainty_pipeline.py   # Stage 6: ECFP4 fusion, calibration, conformal, SIDER
   python 06_deep_representation_pipeline.py     # Stage 7/8: in-house MLP, DMSO images, deep embeddings, CNN
   ```

   `06_deep_representation_pipeline.py` additionally needs the matched-plate
   DMSO control images; the script contains the exact public S3 download
   instructions and will print them when the assets are absent.

5. (Optional) Rebuild the **live run** demo video — it actually executes the
   stage scripts, runs a real Cellpose inference and renders charts from the
   result CSVs (no fictional footage; every frame comes from real execution):

   ```bash
   python scripts/make_demo_video_live.py
   ```

   → outputs `demo_video.mp4` (1280×720, 72 s, 30 fps, H.264, English titles,
   cross-fade transitions). Requires
   `pip install pillow imageio-ffmpeg pandas numpy scipy scikit-learn matplotlib seaborn umap-learn xgboost statsmodels tifffile cellpose`.

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

All figures are included in this repository under `figures/` (copied from
`reports/figures/` of the analysis workspace) and linked relative to the
repository root:

- [01_umap_overview.png](figures/01_umap_overview.png) — UMAP of wells, DMSO vs treatments
- [02_compound_fingerprint_clusters.png](figures/02_compound_fingerprint_clusters.png) — compound fingerprints, KMeans k=12
- [03_classification_roc_pr.png](figures/03_classification_roc_pr.png) — ROC / PR curves
- [04_enrichment_bubble.png](figures/04_enrichment_bubble.png) — cluster × target enrichment bubble chart
- [04_refined_clusters_umap.png](figures/04_refined_clusters_umap.png) — refined cluster UMAP
- [05_cellpose_segmentation.png](figures/05_cellpose_segmentation.png) — Cellpose segmentation demo
- [12_target_class_strength.png](figures/12_target_class_strength.png) — target-class phenotypic strength

A narrated demo video is included:

- [demo_video.mp4](demo_video.mp4) — **live run screen-capture** (1280×720,
  72 s, 30 fps, H.264, ≤ 5 min requirement satisfied, no login required).
  Content structure: (1) pipeline overview title → (2–4) real terminal runs of
  `src/01_phenotypic_profiling.py`, `src/02_classification_target.py`,
  `src/03_enrichment_strength.py` with scrolling stdout → (5) live Cellpose
  (cpsam_v2) inference on a real 1080×1080 DNA-channel image (model loading,
  masks, contour overlay; 115 cells, ~98 s CPU) → (6) charts rendered
  progressively from the result CSVs: UMAP points appearing, ROC curve growing,
  target-class strength bars appearing → (7) closing summary. Rebuild with:
  `pip install pillow imageio-ffmpeg pandas numpy scipy scikit-learn matplotlib seaborn umap-learn xgboost statsmodels tifffile cellpose && python scripts/make_demo_video_live.py`.

## 7. License

MIT — see [LICENSE](LICENSE).
