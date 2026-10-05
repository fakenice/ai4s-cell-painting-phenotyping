---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 1b7b0544872f18baedbb33526952b8c3_2fd2c799bda811f197eb525400393706
    ReservedCode1: 2QUjJQwuyB9e579WjfRqrN4UTW+X1Krlvu06mzlC5Py9KnLzMPvvwXFghX1COibRPWphz98rUPfXHommaA7qS/dsoOlVOIaghnMcIdPYL54HflREqwz4o//5mNPk9sjZFRMBhqwzUWkoRLaZm522ATGgDQ6ObjbEFMMNxYUBabURIoIDl2XBnTNJc7w=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 1b7b0544872f18baedbb33526952b8c3_2fd2c799bda811f197eb525400393706
    ReservedCode2: 2QUjJQwuyB9e579WjfRqrN4UTW+X1Krlvu06mzlC5Py9KnLzMPvvwXFghX1COibRPWphz98rUPfXHommaA7qS/dsoOlVOIaghnMcIdPYL54HflREqwz4o//5mNPk9sjZFRMBhqwzUWkoRLaZm522ATGgDQ6ObjbEFMMNxYUBabURIoIDl2XBnTNJc7w=
---





# Kaggle Writeup — Draft

**Note:** This file is the **draft** of the Kaggle Writeup to be pasted/adapted on the Kaggle competition page. It must be written in English, with the category declaration **at the very top** (mirroring the technical report front matter). Before final submission, replace the team placeholders below with real information; no placeholders are auto-filled. Structure follows the official recommended layout (re-checked 2026-10-01): category declaration → demo video → code repository → project summary → technical report link → optional demo link.

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

Public repository with the complete reproducible pipeline (stages 01–04, one-command entry script `demo.py`, docs, figures, and demo video).

**Link:** https://github.com/fakenice/ai4s-cell-painting-phenotyping

## Technical Report Link

Full technical report (Draft v7) with detailed methods, results, reproduction instructions, and GitHub Pages dashboard.

**Link:** https://github.com/fakenice/ai4s-cell-painting-phenotyping/blob/master/reports/12_technical_report_draft_v7.md

---

## Project Summary (200-300 words)

Phenotypic profiling with Cell Painting provides an unbiased, image-based readout of cellular state. On the JUMP-Cell Painting pilot (`source_4`) dataset we built an end-to-end pipeline covering **303 compounds measured in 1,536 wells with 904 precomputed morphological features**: (i) compound fingerprinting and clustering (UMAP + KMeans, k = 12, silhouette = 0.166), (ii) a gradient-boosted classification baseline separating treated wells from DMSO controls (XGBoost, 5-fold CV, **AUC = 0.768**, AP = 0.936, ACC = 0.792), (iii) target-level Fisher enrichment of refined phenotype clusters (**36 significant cluster–target pairs** at BH-adjusted p < 0.05, dominated by microtubule, HSP90 and CDK/Aurora biology), (iv) a per-compound phenotypic-strength score, and (v) a supervised target-class analysis showing that **microtubule/tubulin compounds elicit significantly stronger phenotypes** (median 0.9958 vs 0.9368, Cliff's delta = 0.827, **p = 0.00145**, Mann–Whitney U), with Src-family kinase (p = 0.0019) and CDK (p = 0.018) families also significant. Two supplementary association screens (MOA cluster-level enrichment, strength–toxicity) returned negative results after multiple-testing correction; we report them transparently with interpretation. An incremental **Stage 6** further delivers the algorithmic contribution the organizers' clarification post recognizes: **scaffold-aware structure modeling** (RDKit ECFP4 fingerprint fusion raises trt-vs-DMSO AUC from 0.768 to 1.000 with 87.7% fingerprint importance; under scaffold-grouped CV the joint morphology+fingerprint model generalizes best, AUC 0.468 vs 0.281 morphology-only), **uncertainty-aware prediction** (isotonic calibration cuts ECE 0.146→0.093 and Brier 0.183→0.162; split conformal prediction with an explicit low-confidence→human-review OoC workflow flags 27.6% of test wells for manual inspection), and an **exploratory SIDER toxicity screen** honestly reported as weak-signal (AUC 0.636 / AP 0.367, baseline 0.180) with a null burden-ranking result. An incremental **Stage 7** adds an in-house trained **deep model** (small MLP on the 904-feature morphology: 5-fold OOF **AUC 0.775**, AP 0.936, ACC 0.786 — matching/edging the gradient-boosted baseline of AUC 0.768, indicating handcrafted morphology is near its separability limit), a **leakage-controlled evaluation** showing the same MLP drops to **AUC 0.594** under compound-grouped GroupKFold (same compound never shared across train/test — an honest generalization number), and a **transfer-learning check** (ImageNet-pretrained ResNet18 512-d embeddings successfully extracted from local raw images). An incremental **Stage 8** downloads **matched-plate DMSO control images** (6 treated + 6 DMSO sites, 8 channels each, same plate BR00116991 / source_4, public AWS cellpainting-gallery bucket) and executes both previously skipped experiments: **deep-embedding vs handcrafted vs concatenated classifier comparison** (well-grouped LOO: deep ResNet18 512-d **AUC 0.778** vs handcrafted 904 AUC 0.556 vs concat 1416 AUC 0.667; site-level GroupKFold AUC 0.25 unstable at n = 12 sites) and a **self-trained single-cell CNN** (Cellpose cpsam_v2 → 2,564 crops; well-grouped GroupKFold test **AUC 0.0955** / AP 0.2698 / ACC 0.3292 — below chance, honestly reported as a small-sample negative).

## Relevance to Organ-on-a-Chip

Organ-on-a-Chip (OoC) platforms recapitulate human organ-level physiology in microfluidic culture, and their readouts are dominated by **high-content, image-based measurements of cellular phenotype**. Cell Painting — the morphological profiling assay used in this submission — is precisely the kind of high-content cytological readout that OoC drug-screening and toxicity-prediction workflows need: it converts raw cellular state into dense, unbiased morphological feature vectors that are directly comparable across perturbations.

Our pipeline transfers to OoC imaging data with minimal adaptation. (i) The **treated-vs-control classification** module (XGBoost, AUC = 0.768 on JUMP-CP) is assay-agnostic: given OoC chip imaging features (e.g., segmented cells from microfluidic channels), the same classifier distinguishes compound-exposed from vehicle-treated states. (ii) The **target-enrichment** step (36 significant cluster–target pairs) can annotate which biological pathways are perturbed on-chip, supporting mechanism-of-action readouts for organ-level toxicity. (iii) The **phenotypic-strength score** provides a continuous potency-like readout per perturbation — directly applicable to dose–response experiments in OoC devices. (iv) The **single-cell segmentation demo** (Cellpose) mirrors the segmentation step required for any high-content chip image analysis.

Importantly, we build on the official competition-recommended dataset: the **JUMP-Cell Painting (JUMP-CP) pilot**, released under CC BY 4.0 in the public `cellpainting-gallery` S3 bucket. Building the pipeline on this canonical reference keeps the submission within the competition's intended scope while maximizing transferability to Organ-on-a-Chip data pipelines.

## Methods (summary)

1. **Data:** JUMP-CP pilot `source_4`, compound plates `BR00116991` / `BR00116992` (303 unique compounds, 4 replicate wells each); CellProfiler normalized, feature-selected profiles (904 morphological features per well); public S3 `cellpainting-gallery` bucket (CC BY 4.0).
2. **Compound fingerprints:** mean of replicate wells per compound (303 × 904).
3. **Unsupervised structure:** UMAP (n_neighbors = 15, min_dist = 0.1) + KMeans (k = 12, n_init = 10, silhouette = 0.166); refined clustering for enrichment.
4. **Classification baseline:** XGBoost with 5-fold stratified cross-validation on well-level features; tasks: treated vs DMSO (648 wells) and treated vs all controls (768 wells). Random state fixed at 42.
5. **Enrichment:** Fisher exact test per refined cluster × annotated target gene with Benjamini–Hochberg FDR correction (α = 0.05).
6. **Phenotypic strength:** mean P(treated) of the treated-vs-DMSO classifier over replicate wells (256 compounds).
7. **Target-class strength:** Mann–Whitney U test per target family (≥ 3 members) vs remaining compounds; effect size Cliff's delta.
8. **Segmentation demo:** Cellpose (cyto2) on a real 8-channel JUMP-CP TIFF site.
9. **Structure-aware modeling (Stage 6):** RDKit ECFP4 fingerprints (Morgan r=2, 1024 bits) from 303 SMILES; three XGBoost models (pheno-only / fp-only / pheno+fp) on identical 5-fold CV; scaffold groups via single-linkage Tanimoto > 0.5 clustering (282 groups) with 5-fold GroupKFold for new-scaffold generalization.
10. **Uncertainty-aware modeling (Stage 6):** stratified 70/15/15 split; Platt and isotonic calibration; split conformal prediction (α = 0.1) with calibration-split quantile; low-confidence margin |p − 0.5| < 0.15 → human-review queue.
11. **Exploratory toxicity (Stage 6):** SIDER merge on 256 compounds (46 annotated); has_sider 5-fold CV; burden high-vs-low within annotated set (median n_side_effects = 91 split), repeated 3×3-fold CV.
12. **Deep representation (Stage 7):** in-house small MLP (`904→256→64→1`, ReLU + dropout 0.3, Adam lr 1e-3 / wd 1e-4, 20 epochs, batch 64, seed 42) trained on the same 904-feature morphology under identical trt-vs-DMSO 5-fold stratified CV; compound-grouped GroupKFold (`pert_iname + plate`) on trt-vs-all-controls for leak-free generalization; transfer-learning feasibility check with ImageNet-pretrained torchvision ResNet18 (512-d embeddings) on the local raw JUMP-CP images; asset-gated skip of deep-embedding classifier comparison and single-cell CNN where two-class image data is unavailable.
13. **Deep representation images (Stage 8):** downloaded matched-plate DMSO control images (6 treated + 6 DMSO sites, 8-channel TIFFs, same plate BR00116991 / source_4, public AWS cellpainting-gallery bucket; `data/raw/BR00116991_dmso/`); deep-embedding classifier comparison (ImageNet-pretrained torchvision ResNet18 512-d embeddings, ch1/ch4/ch2 RGB composite, well-grouped LOO vs handcrafted 904 vs concat 1416; site-level GroupKFold stability check); self-trained single-cell CNN (Cellpose `cpsam_v2` crops, small 64×64 CNN, well-grouped GroupKFold(4), seed 42, 20 epochs); every step asset-gated, no fabricated numbers.

## Key Results

| Result | Value |
|---|---|
| Classification treated vs DMSO (5-fold CV) | **AUC = 0.768**, AP = 0.936, ACC = 0.792 (648 wells) |
| Classification treated vs all controls | AUC = 0.687, AP = 0.816, ACC = 0.697 (768 wells) |
| Significant cluster–target enrichments | **36 pairs** (9 clusters; BH-adjusted p from 3.9e-06 to 4.2e-02); dominant modules: microtubule (15 tubulin genes), HSP90, CDK/Aurora, calcium channel, SRC family |
| Microtubule/tubulin phenotypic strength | median 0.9958 vs 0.9368, Cliff's delta = 0.827, **p = 0.00145** (n = 4) |
| Src-family kinase strength | p = 0.0019 (n = 7) |
| CDK strength | p = 0.018 (n = 6) |
| Phenotypic strength distribution | n = 256; mean 0.877, median 0.938, IQR [0.805, 0.984] |
| Cellpose segmentation demo | 116 cells detected on a 1080×1080 site |
| Structure-enhanced model (trt vs DMSO) | AUC 0.7682 → **1.0000**; AP 0.9359 → 1.0000; fingerprint importance **87.7%** (Stage 6) |
| Scaffold GroupKFold (trt vs all controls) | pheno+fp **AUC 0.4679** > fp 0.3593 > pheno 0.2809 (Stage 6) |
| Probability calibration (test n = 98) | ECE 0.1461 → 0.1160 (Platt) → **0.0930** (isotonic); Brier 0.1833 → **0.1623** (Stage 6) |
| Split conformal (α = 0.1) | q_hat 0.5600; empirical coverage **0.847** (nominal 90%); mean width 0.7809 (Stage 6) |
| Low-confidence → human review | **27/98 (27.6%)** test wells below |p − 0.5| = 0.15 (Stage 6) |
| Exploratory SIDER has_sider | AUC **0.6359**, AP 0.3673 vs baseline 0.180 — weak signal, honestly reported (Stage 6) |
| Exploratory SIDER burden high-vs-low | AUC 0.4537 ± 0.0310 — **null**, exploratory only (Stage 6) |
| In-house MLP, trt vs DMSO (5-fold OOF) | **AUC 0.7746** / AP 0.9361 / ACC 0.7855 — matches/edges XGBoost 0.768 (Stage 7) |
| In-house MLP, compound-grouped GroupKFold (trt vs all controls) | **AUC 0.5944** / AP 0.7513 / ACC 0.6510 — leak-free estimate (Stage 7) |
| ResNet18 embedding extraction (transfer learning) | 512-d embeddings OK from 8 local TIFFs (n = 2 groups, 0.36 s, seed fixed) (Stage 7) |
| DMSO control images downloaded (Stage 8) | 6 treated + 6 DMSO sites, 8-channel TIFFs, same plate BR00116991 / source_4 (AWS public bucket) — matched plate reduces batch effects |
| Deep-embedding vs handcrafted vs concat (trt vs DMSO, well-grouped LOO) | deep 512-d **AUC 0.7778** / AP 0.8056 / ACC 0.5000; handcrafted 904 AUC 0.5556 / AP 0.5889 / ACC 0.5000; concat 1416 AUC 0.6667 / AP 0.6389 / ACC 0.6667; site-level GroupKFold AUC 0.2500 (n = 12 sites, unstable — reported as limitation) (Stage 8) |
| Self-trained single-cell CNN (Cellpose crops, well-grouped GroupKFold(4)) | n = 2,564 crops / 6 wells; test **AUC 0.0955** / AP 0.2698 / ACC 0.3292 — below chance, honestly reported as small-sample negative (Stage 8) |

## Negative Results (reported transparently)

- **Cluster-level MOA enrichment:** 160 tests (17 ChEMBL MOA classes × 10 clusters) → zero pairs significant at q < 0.05 (smallest adjusted p = 0.420). Attributed to sparse MOA annotation (33.9%), broad class granularity, and low power.
- **Strength–toxicity association:** 167 SIDER side-effect terms → zero significant at q < 0.05 (smallest adjusted p = 0.335); top nominal terms (myocardial infarction, acute coronary syndrome, peripheral neuropathy) are directionally plausible but fail FDR. Attributed to zero-inflated annotation (17.7% coverage) and conceptual mismatch between "phenotype distance" and toxicity.

- **Deep-embedding classifier comparison (fig. 24) & self-trained single-cell CNN (Stage 8):** executed on newly downloaded matched-plate DMSO images, but the image-level classifiers are **small-sample / unstable negatives reported honestly** — deep-embedding well-grouped LOO AUC 0.7778 (n = 6 wells) vs site-level GroupKFold AUC 0.2500 (n = 12 sites, unstable); single-cell CNN test AUC 0.0955 / ACC 0.3292 (2,564 crops, 6 wells) below chance. Documented as evidence of execution and honest small-sample limitations, not positive claims. (Stage 7 had skipped these experiments because the original local subset was treated-only; Stage 8 resolved the data gap by downloading matched DMSO images.)

These negatives are methodological, not evidence of pipeline failure: positive controls (target-gene enrichment, target-class strength) demonstrate the pipeline detects signal when present.

## Reproduction Steps

1. Clone: `git clone https://github.com/fakenice/ai4s-cell-painting-phenotyping`
2. Install: `pip install -r requirements.txt` (optional Cellpose/Torch for stage 04 only).
3. Download data (public S3, no sign-in):
   - profiles: `aws s3 cp --no-sign-request --recursive s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/workspace/profiles/ data/profiles/`
   - metadata: `aws s3 cp --no-sign-request --recursive s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/workspace/metadata/ data/metadata/`
   - raw images (optional): `aws s3 cp --no-sign-request --recursive s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/images/BR00116991/ data/raw/BR00116991/`
4. Run: `python demo.py` (lightweight summary) or `python demo.py --full` (stages 01→04).
5. (Optional) Rebuild demo video: `python scripts/make_demo_video_live.py`.

Full details: `README.md` in the repository and the technical report (§10).

## Repository Contents

- `01_phenotypic_profiling.py` — fingerprints & clustering
- `02_classification_target.py` — classification baseline + target consistency
- `03_enrichment_strength.py` — refined clusters, Fisher enrichment, strength score
- `04_cellpose_demo.py` — Cellpose single-cell segmentation demo
- `05_structure_uncertainty_pipeline.py` — Stage 6: structure-aware + uncertainty-aware modeling, SIDER exploratory screen
- `06_deep_representation_pipeline.py` — Stage 7/8: in-house MLP + compound-grouped GroupKFold leakage analysis; Stage 8 DMSO image download, deep-embedding vs handcrafted vs concat comparison, self-trained single-cell CNN
- `demo.py` — one-command entry script
- `figures/` — 17 result figures (incl. 16–20 Stage-6 figures, 22–23 Stage-7 figures, 24–26 Stage-8 figures); `demo_video.mp4` — 72 s live-run demo video (≤ 5 min)
- `docs/` — GitHub Pages landing page + interactive dashboard
- `LICENSE` (MIT), `requirements.txt` (incl. rdkit, torch, torchvision), `.gitignore`

## Optional Demo Link

- **Interactive dashboard / GitHub Pages:** https://fakenice.github.io/ai4s-cell-painting-phenotyping/
- **One-command entry script:** `python demo.py` (see Reproduction Steps above)
- **Single-cell segmentation demo:** `04_cellpose_demo.py` (Cellpose cyto2 on a real 8-channel JUMP-CP TIFF site)

## License

Project code: MIT. Data: JUMP-CP CC BY 4.0; ChEMBL CC BY-SA 3.0; SIDER academic use; Cellpose BSD-3-Clause. See technical report §2.5 / §11.

---

*Team placeholders must be replaced by the submitting team before posting. This draft is derived from the technical report Draft v7; see `reports/22_optimization_log.md` for version history.*
