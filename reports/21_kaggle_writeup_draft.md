---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 1b7b0544872f18baedbb33526952b8c3_aac63ad9c27411f18019525400248c00
    ReservedCode1: DxbQWDN9IMgNwTcaxqVW8bDWtPZsziuAKsbiFGIVQzA68SulljBD/y2V8CcaHjKAsd2cR5FTCsBJ1XeYw+IPh7ulb10uCyCGV8uqBn7YgxTWzLJHJP0Ol/4Kzris5gsULeoIHKRdASmdxWPLkHUfa5B2jgegfxQEya3FAKxDSxLQgDo/g00rVANIO20=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 1b7b0544872f18baedbb33526952b8c3_aac63ad9c27411f18019525400248c00
    ReservedCode2: DxbQWDN9IMgNwTcaxqVW8bDWtPZsziuAKsbiFGIVQzA68SulljBD/y2V8CcaHjKAsd2cR5FTCsBJ1XeYw+IPh7ulb10uCyCGV8uqBn7YgxTWzLJHJP0Ol/4Kzris5gsULeoIHKRdASmdxWPLkHUfa5B2jgegfxQEya3FAKxDSxLQgDo/g00rVANIO20=
---







# Kaggle Writeup — Draft

**Note:** This file is the **draft** of the Kaggle Writeup to be pasted/adapted on the Kaggle competition page. It must be written in English, with the category declaration **at the very top** (mirroring the technical report front matter). Before final submission, replace the team placeholders below with real information; no placeholders are auto-filled. Structure follows the official recommended layout (re-checked 2026-10-01): category declaration → demo video → code repository → project summary → technical report link → optional demo link. The technical report has been restructured along the scientific storyline (task definition → evaluation protocol → main results → exploration and boundaries) and compressed from 65–69 pages to **17 pages**; this writeup mirrors the same storyline and page-count note.

---

## Category Declaration

**Submission category: Model & Algorithm**

This submission is declared under the **Model & Algorithm** category of the AI4S Open Innovation: AI for Life Science competition. It delivers a reproducible machine-learning pipeline — dimensionality reduction, clustering, classification, enrichment, and phenotypic-strength scoring — applied to public Cell Painting morphological profiling data. The main intellectual contribution is algorithmic and methodological.

**Team:** `ShapeToTarget` *(placeholder — to be completed by the submitting team)*

---

## Demo Video

A 72-second live-run screen recording (H.264, 1280×720, no login required) demonstrating the full pipeline on real JUMP-Cell Painting data — from raw profiles to clustering, classification, enrichment, phenotypic-strength scoring, and single-cell segmentation.

**Link:** https://github.com/fakenice/ai4s-cell-painting-phenotyping/raw/master/demo_video.mp4

## Code Repository Link

Public repository with the complete reproducible pipeline (scripts `01`–`06`, one-command entry script `demo.py`, docs, figures, and demo video).

**Link:** https://github.com/fakenice/ai4s-cell-painting-phenotyping

## Technical Report Link

Full technical report (Draft v7, 17 pages) with detailed methods, results, reproduction instructions, and GitHub Pages dashboard.

**Link:** https://github.com/fakenice/ai4s-cell-painting-phenotyping/blob/master/reports/12_technical_report_draft_v7.md

---

## Project Summary (200-300 words)

Phenotypic profiling with Cell Painting provides an unbiased, image-based readout of cellular state. On the JUMP-Cell Painting pilot (`source_4`) dataset we built an end-to-end pipeline covering **303 compounds measured in 1,536 wells with 904 precomputed morphological features**. We follow a single scientific storyline: **task definition → evaluation protocol → main results → exploration and boundaries**.

**Task definition.** The treated-vs-DMSO separation is deceptively easy (well-level AUC 0.768): DMSO is chemically isolated from all 303 compounds, so we treat it as a structural control and focus on the harder **treated-vs-treated** discrimination and cross-plate generalization.

**Evaluation protocol.** We use soft scaffold-grouped CV (τ = 0.6) and compound-disjoint splits to prevent "back-answer" leakage from compound overlap across folds; AUC 1.000 under well-level CV is labeled a structural control, not a phenotypic result.

**Main results.** (i) **Cross-plate generalization**: training on plate BR00116991 and testing on BR00116992 gives trt-vs-DMSO AUC **0.6825**, at parity with within-plate performance. (ii) **Prototype discrimination**: LOOCV cosine nearest-prototype on compound-mean profiles reaches mean AUC **0.985** / sign accuracy **0.927** across the full cross-plate pair grid, with per-plate z-score corrections raising reference-21 mean AUC to **0.8274**. (iii) **Replicate retrieval**: 904-feature cosine retrieval finds same-compound replicates at **6.1× chance AP** on the full scope, and compound-identity top-1/top-5 on held-out plates reaches **0.331 / 0.929**. (iv) **Target enrichment**: shared-target compound pairs show AUROC 0.5611 (p = 2.76e-07); microtubule/tubulin, Src-family and CDK classes elicit significantly stronger phenotypes.

**Exploration and boundaries.** Self-supervised embeddings, Harmony batch correction, a self-trained single-cell CNN, and model-side integration attempts are reported as negative/exploratory results in the report appendix; ECFP4 fingerprints are kept strictly as **SAR controls and confound checks**, not as phenotypic-recognition inputs. Full details, negative results, and reproduction steps are in the technical report (17 pages).

## Relevance to Organ-on-a-Chip

Organ-on-a-Chip (OoC) platforms recapitulate human organ-level physiology in microfluidic culture, and their readouts are dominated by **high-content, image-based measurements of cellular phenotype**. Cell Painting — the morphological profiling assay used in this submission — is precisely the kind of high-content cytological readout that OoC drug-screening and toxicity-prediction workflows need: it converts raw cellular state into dense, unbiased morphological feature vectors that are directly comparable across perturbations.

Our pipeline transfers to OoC imaging data with minimal adaptation. (i) The **treated-vs-control classification** module is assay-agnostic: given OoC chip imaging features (e.g., segmented cells from microfluidic channels), the same classifier distinguishes compound-exposed from vehicle-treated states. (ii) The **target-enrichment** step (36 significant cluster–target pairs) can annotate which biological pathways are perturbed on-chip, supporting mechanism-of-action readouts for organ-level toxicity. (iii) The **phenotypic-strength score** provides a continuous potency-like readout per perturbation — directly applicable to dose–response experiments in OoC devices. (iv) The **single-cell segmentation demo** (Cellpose) mirrors the segmentation step required for any high-content chip image analysis.

Importantly, we build on the official competition-recommended dataset: the **JUMP-Cell Painting (JUMP-CP) pilot**, released under CC BY 4.0 in the public `cellpainting-gallery` S3 bucket. Building the pipeline on this canonical reference keeps the submission within the competition's intended scope while maximizing transferability to Organ-on-a-Chip data pipelines.

## Methods (summary)

1. **Data:** JUMP-CP pilot `source_4`, compound plates `BR00116991` / `BR00116992` (303 unique compounds, 4 replicate wells each); CellProfiler normalized, feature-selected profiles (904 morphological features per well); public S3 `cellpainting-gallery` bucket (CC BY 4.0).
2. **Compound fingerprints:** mean of replicate wells per compound (303 × 904).
3. **Unsupervised structure:** UMAP (n_neighbors = 15, min_dist = 0.1) + KMeans (k = 12, n_init = 10, silhouette = 0.166); refined clustering for enrichment.
4. **Classification baseline:** XGBoost with 5-fold stratified cross-validation on well-level features; tasks: treated vs DMSO (648 wells) and treated vs all controls (768 wells). Random state fixed at 42.
5. **Evaluation protocol:** soft scaffold-grouped CV (τ = 0.6) as the default generalization estimate; well-level CV demoted to an in-fold sanity check; trt-vs-DMSO AUC 1.000 labeled a structural control.
6. **Enrichment:** Fisher exact test per refined cluster × annotated target gene with Benjamini–Hochberg FDR correction (α = 0.05); known-target pair AUROC on compound pairs sharing a target.
7. **Phenotypic strength:** mean P(treated) of the treated-vs-DMSO classifier over replicate wells; target-class strength via Mann–Whitney U + Cliff's delta.
8. **Cross-plate protocol:** train on plate BR00116991, test on BR00116992 (trt-vs-DMSO, replicate retrieval, compound-identity top-k, prototype discrimination with per-plate z-score / mean-centering corrections).
9. **SAR control:** RDKit ECFP4 fingerprints (Morgan r=2, 1024 bits) used only for structure–phenotype ablations and the structural-confirmation step of the OoC decision chain — never as phenotypic-recognition inputs.
10. **Segmentation demo:** Cellpose (cyto2) on a real 8-channel JUMP-CP TIFF site.
11. **Exploratory modules (appendix):** uncertainty calibration (isotonic ECE 0.093), self-supervised embeddings (DINOv2/OpenPhenom), Harmony well-position correction, self-trained single-cell CNN, and model-side integration (XGB stacking / feature selection) — all honest negatives or cautionary results.

## Key Results

| Result | Value |
|---|---|
| Cross-plate trt-vs-DMSO (train plate 991, test plate 992) | **AUC 0.6825** (strict DMSO, at parity with within-plate 0.68–0.69) |
| Prototype discrimination, cross-plate pair grid | mean AUC **0.985** / sign accuracy **0.927** (LOOCV cosine nearest-prototype on compound-mean profiles) |
| Prototype discrimination, reference-21 pairs | mean AUC raw 0.7292; per-plate z-score **0.8274**; mean-centering 0.7768 |
| Compound-identity top-1 / top-5 (14 held-out wells) | **0.331 / 0.929** (full-scope 260-well baseline 0.0115, task-difficulty limitation) |
| Cross-plate replicate retrieval AP | 0.42–0.45 (above chance, below in-plate 0.958) |
| Replicate retrieval, full scope (cosine, 904 features) | mean AP **0.2451** vs chance 0.0401 — **6.1× chance**; MRR 0.3004; R@1/5/10 = 0.202/0.406/0.503 |
| Known-target pair enrichment | shared-target AUROC **0.5611** (p = 2.76e-07, 569/32,640 pairs); 12 targets BH-significant (TUBB/TUBB4B 0.9998, TUBA family 0.9997, CACNA2D3 0.9843, CFTR 0.8528) |
| Significant cluster–target enrichments | **36 pairs** (9 clusters; BH-adjusted p from 3.9e-06 to 4.2e-02); dominant: microtubule, HSP90, CDK/Aurora, SRC family |
| Target-class strength | microtubule median 0.9958 vs 0.9368, Cliff's delta 0.827, **p = 0.00145**; Src p = 0.0019; CDK p = 0.018 |
| Classification treated vs DMSO (well-level, in-fold sanity) | AUC = 0.768, AP = 0.936, ACC = 0.792 (648 wells) |
| Soft scaffold-grouped CV τ = 0.6 (default protocol) | pheno+fp AUC **0.5222** / AP 0.6545; pheno-only 0.3349 / AP 0.5559 |
| trt-vs-DMSO AUC 1.000 (structural control) | DMSO chemically isolated: ECFP4 Tanimoto distance mean 0.9683, MWU p = 5.95e-148, nearest-neighbor sim 0.15 — **not a phenotype result** |
| Exploratory SIDER has_sider | AUC 0.6359, AP 0.3673 vs baseline 0.180 — weak signal, appendix |
| Exploratory self-supervised / Harmony / CNN / integration | all negative or cautionary; details in report Appendix A (17-page report keeps full story in main text) |

## Negative and Exploratory Results (appendix)

All exploratory and negative-result details live in **Appendix A** of the technical report, with scripts and raw outputs preserved in `reports/`:

- **Self-supervised representations:** DINOv2 and OpenPhenom embeddings do not beat the ResNet18 baseline on the small 6-well well-grouped LOO task (best: OpenPhenom 8-ch AUC 0.6667 vs 0.7778).
- **Harmony well-position correction:** leaves trt-vs-DMSO at AUC 1.000 but **decreases** scaffold-grouped CV AUC (0.4679 → 0.4136) — removes informative plate/position structure, not recommended by default.
- **Self-trained single-cell CNN:** 2,564 Cellpose crops / 6 wells; test AUC 0.0955 / ACC 0.3292 — below chance, honestly reported as a small-sample negative.
- **Model-side integration on the harder task:** on the 21-pair LOOCV protocol, multi-seed bagging, SelectKBest feature selection and XGB+LR stacks do **not** improve the baseline LR(904) AUC 0.7619; no model-side upgrade replaces the 904 backbone.
- **Cluster-level MOA enrichment and strength–toxicity association:** zero pairs significant at q < 0.05 after FDR (sparse annotation, low power).

These negatives are methodological, not evidence of pipeline failure: positive controls (target-gene enrichment, target-class strength, cross-plate transfer) demonstrate the pipeline detects signal when present.

## Reproduction Steps

1. Clone: `git clone https://github.com/fakenice/ai4s-cell-painting-phenotyping`
2. Install: `pip install -r requirements.txt` (optional Cellpose/Torch for the deep-exploration scripts only).
3. Download data (public S3, no sign-in):
   - profiles: `aws s3 cp --no-sign-request --recursive s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/workspace/profiles/ data/profiles/`
   - metadata: `aws s3 cp --no-sign-request --recursive s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/workspace/metadata/ data/metadata/`
   - raw images (optional, deep-exploration only): `aws s3 cp --no-sign-request --recursive s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/images/BR00116991/ data/raw/BR00116991/` and `.../BR00116992/ data/raw/BR00116992/`
4. Run: `python demo.py` (lightweight summary) or `python demo.py --full` (full pipeline).
5. (Optional) Rebuild demo video: `python scripts/make_demo_video_live.py`.

Full details: `README.md` in the repository and the technical report (§10).

## Repository Contents

- `01_phenotypic_profiling.py` — fingerprints & clustering
- `02_classification_target.py` — classification baseline + target consistency
- `03_enrichment_strength.py` — refined clusters, Fisher enrichment, strength score
- `04_cellpose_demo.py` — Cellpose single-cell segmentation demo
- `05_structure_uncertainty_pipeline.py` — structure-aware (SAR control) + uncertainty-aware modeling, SIDER exploratory screen
- `06_deep_representation_pipeline.py` — deep embeddings, compound-grouped GroupKFold leakage analysis, self-trained single-cell CNN
- `demo.py` — one-command entry script
- `reports/` — result CSVs/JSONs (numbered `01_`–`23_`) and the technical report; `figures/` — result figures
- `docs/` — GitHub Pages landing page + interactive dashboard
- `LICENSE` (MIT), `requirements.txt` (incl. rdkit, torch, torchvision), `.gitignore`

## Optional Demo Link

- **Interactive dashboard / GitHub Pages:** https://fakenice.github.io/ai4s-cell-painting-phenotyping/
- **One-command entry script:** `python demo.py` (see Reproduction Steps above)
- **Single-cell segmentation demo:** `04_cellpose_demo.py` (Cellpose cyto2 on a real 8-channel JUMP-CP TIFF site)

## License

Project code: MIT. Data: JUMP-CP CC BY 4.0; ChEMBL CC BY-SA 3.0; SIDER academic use; Cellpose BSD-3-Clause. See technical report §2.5 / §11.

---

*Team placeholders must be replaced by the submitting team before posting. This draft is derived from the technical report Draft v7 (17 pages, scientific storyline); version history and raw experiment outputs are in `reports/22_optimization_log.md`.*
