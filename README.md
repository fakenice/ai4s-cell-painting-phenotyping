

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

   `requirements.txt` is two documents, and it now says so. The pinned block is the environment
   that produced the submitted results (claimed for 2026-10-05); it is *not* a claim about the
   machine you install on. `python scripts/record_environment.py` writes
   `reports/23_environment_fingerprint.json`, which records each declared distribution beside
   what this machine actually has — measured 2026-11-06, 3 of the 12 `==` pins equal this machine,
   7 differ and 2 are absent — and `--check` turns that file into a drift gate. The unpinned rows
   at the end are the distributions committed code imports but the original list never named;
   they carry no version because no version of theirs can be tied back to the build environment.
   `python scripts/check_repo.py` fails if either half goes stale.

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

   `data/` may sit **inside the checkout** (`<repo>/data`, as above) or **one level above it**
   (`<workspace>/data` — the layout this project grew up in, and the one `reports/24` describes
   for the gitignored `data/external/cpg0016/` tree). `scripts/_paths.py` prefers whichever of
   the two exists, so no re-download is needed either way. To force a location, set an
   environment variable instead of editing code:

   ```bash
   export AI4S_REPO=/absolute/path/to/github_repo       # the checkout with scripts/ + reports/
   export AI4S_WORKSPACE=/absolute/path/that/holds/data # implies <that>/data unconditionally
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

   Scripts resolve every path through `scripts/_paths.py`, which derives the repo, workspace and
   `data/` roots from its own file location — so a script can be invoked from any working
   directory, on any machine, and will create `reports/figures/` and result CSVs automatically.
   The seven root-level scripts (`demo.py`, `01_…`–`06_…`) still carry their own absolute-path
   derivation; see `reports/22` Stage 13 "Not done".

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

5. Check the checkout. Two entry points, both read-only (they never write into `reports/`), plus a
   third that re-measures the first two as if the inputs were gone:

   ```bash
   python tests/test_stage12_units.py                 # 30 tests, no data needed, no pytest needed
   python scripts/check_repo.py                       # 54 checks in 8 groups: paths, imports and
   python scripts/check_repo.py --deep                #     dependencies, citations, artifacts,
                                                      #     committed numbers, docs, the test suite and
                                                      #     the CI workflow; 55 with --deep, which also
                                                      #     re-hashes the 17 external objects
   python scripts/check_repo.py --allow-missing-data  # the same rows, except that the three that can
                                                      # only pass with `data/` are SKIPped, not FAILED
   python scripts/clone_probe.py                      # stand-in fresh clone: copies the tracked files
                                                      # outside the data tree, runs all three, removes
                                                      # the copy, and exits 0 only if all held
   ```

   With the inputs present, the suite reports `30/30` and the checker `54/54`
   (`55/55 --deep`); `--allow-missing-data` makes no difference while `data/` exists.
   The clone probe copies the 152 tracked working-tree files outside the data tree, clears the
   path overrides and runs all three commands. This is a file-copy simulation, not a git clone.

   Without inputs, the suite reports `29/29 tests pass (1 skipped)` and the plain checker
   `48/51`, exit 1. Exactly three rows fail: "the resolved data tree exists", "pilot profile
   tables are present", and "fetch manifest present". With `--allow-missing-data`, these become
   explicit SKIP rows, excluded from the denominator: `48/48 checks pass (3 skipped, they need
   data/)`, exit 0. Three manifest-content rows are not emitted without a manifest, explaining
   the 51 versus 54 totals. History/machine applicability rows retain their earlier conditional
   PASS convention, with `unproven` or `skipped` in the label; they do not prove historical path
   equivalence or environment equality on another checkout/machine.

   The probe requires the exact three FAIL names in the plain run and the exact three SKIP names
   in the flagged run, matching summaries, unchanged non-data PASS rows, and a successful suite
   with only its live-data assertion skipped. Missing/duplicate rows, empty output, traceback or
   extra skips fail the probe. A valid run ends `verdict: PASS` and exit 0, then removes the copy.

   `.github/workflows/verify.yml` runs the suite and flagged checker on push, pull request and
   manual dispatch, installing `numpy`, `pandas`, `scikit-learn` and `pymupdf` (scipy is a
   scikit-learn dependency). Group H checks the declared commands, files and dependency coverage;
   it ignores comments and uses a fixed package-name mapping rather than this machine's package
   metadata. Missing/commented-out workflows, missing commands and omitted runtime dependencies
   fail. It reads the current plain `run:` format, **not arbitrary YAML or shell syntax**.
   **The GitHub workflow has not run.** Local checks do not establish Linux execution, successful
   dependency installation on a clean runner, or reproducibility of the original model training.

6. (Optional) Rebuild the **live run** demo video — it actually executes the
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
  `BR00116992`, 303 unique compounds across the pair, one well per treated
  compound per plate — so 2 technical wells per compound, the two plates being
  the same array) and two ORF/CRISPR plates
  (excluded from chemical analysis).
- **Compound metadata:** names, target genes, SMILES, barcode–platemap mapping
  (JUMP-Target-1 compound metadata, `data/metadata/`).
- **External annotations (optional downstream analyses):** ChEMBL MOA and SIDER
  side-effect annotations are used in the extended technical report.

## 5. Results Summary

**Evaluation protocol first.** The default is soft scaffold-grouped CV (τ = 0.6), which keeps
all wells of a chemical scaffold in one fold; it answers "does this generalize to a new
scaffold?" rather than "can it recognize a compound it has already seen?". Well-level CV is
reported below only as an in-fold sanity check, because 84.6–91.4 % of its test compounds are
also in training. The full protocol comparison and the descaffolded-fingerprint ablation are in
the technical report (`reports/12_technical_report_draft_v7.md`, §22–§24).

- **UMAP + KMeans (k = 12, silhouette = 0.166):** DMSO negative controls separate
  clearly from treated compounds; clusters are uneven in size (cluster 0 = 143
  compounds, mostly weak/near-control phenotypes).
- **Classification — generalization protocol (default):** soft scaffold-grouped
  5-fold CV (ECFP4 Tanimoto τ = 0.6; all replicates of a scaffold stay in one fold),
  treated vs all controls: phenotype+ECFP4 **AUC = 0.5222, AP = 0.6545**;
  phenotype-only **AUC = 0.3349, AP = 0.5559** (768 wells). Hard-scaffold and
  fingerprint-cluster groupings give AUC 0.5258 and 0.4775, so the grouping choice
  moves the number by up to 0.048, not by the gap to chance.
- **Classification — well-level sanity check (NOT the headline):** XGBoost 5-fold
  CV, treated vs DMSO: AUC = 0.768, AP = 0.936, ACC = 0.792 (648 wells);
  treated vs all controls: AUC = 0.687, AP = 0.816, ACC = 0.697 (768 wells).
  **84.6–91.4 % of test compounds also occur in training under this split**, so
  the 0.768 measures replicate memorization as much as phenotype. With ECFP4
  fused in, treated-vs-DMSO reaches AUC 1.0 because DMSO is chemically isolated
  from every compound (mean ECFP4 distance 0.9683); that run is reported as a
  structural control, not a phenotype result. Top morphology features are
  cytoplasmic intensity MAD, nuclear Zernike and AGP texture.
- **Cross-site external validation (`cpg0016-jump`, independent lab + derivation batch):**
  the treated-vs-DMSO model was re-trained on the pilot and tested on 9 external JUMP plates
  (`data/external/cpg0016` at the workspace root, above this repo; SHA256-manifested, 159.9 MB). **Result: not reproduced.** Pooled
  cross-site AUC is 0.5155–0.6436 across four normalisation arms, but 8 of the 9 plates place
  every vehicle well in two fixed columns (position-only CV AUC 1.0000, permutation
  p = 0.0000), so their above-chance scores are a column readout; the single plate with a
  pilot-like layout scores 0.4248–0.5543. Measured in the same pass: the pilot's two plates are
  the same array (384/384 identical compound), and a coordinate-only model transfers between
  them at AUC 0.7450 — so the in-site 0.6825 is **not** layout-held-out. Transfer that does not
  depend on position survives: on external plate pairs where a compound has **no** well at the
  query's own coordinate — so a layout readout is impossible — same-compound retrieval still gives
  R@1 0.5971 [0.5488, 0.6403] (n = 350 queries, 16 plate pairs, applicable null 0.0061, ~98×);
  the broader different-coordinate arm gives R@1 0.4514 / R@10 0.8445 (n = 2,142) and is
  **higher** than the position-matched arm (paired +0.0541, one-sided p = 0.0057). Full
  evidence and reproduction commands: `reports/24_cross_site_external_validation.md`.
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

- [Demo video (YouTube)](https://youtu.be/IBZbox9Akcg) — v8 narrated
  walkthrough (136 s, narration-only audio, no background music, English,
  no watermark; ≤ 5 min requirement satisfied).

## 7. License

MIT — see [LICENSE](LICENSE).

## 8. How to cite

Machine-readable metadata lives in `CITATION.cff` at the repo root (GitHub renders it in the
sidebar). When citing a result, state which split it was computed under — the leakage-
controlled classification numbers and the exploratory ones are not interchangeable. The
JUMP-Cell Painting / cpg0016 data has its own upstream citation; see §4.

```bibtex
@software{wu2026cellpainting,
  author  = {Wu, Yiting},
  title   = {Morphological phenotypic profiling of chemical perturbations with JUMP-Cell Painting data (AI4S Open Innovation hackathon writeup)},
  url     = {https://github.com/fakenice/ai4s-cell-painting-phenotyping}
}
```
