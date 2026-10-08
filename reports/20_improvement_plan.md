---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 1b7b0544872f18baedbb33526952b8c3_ac3d3bf4c27411f18019525400248c00
    ReservedCode1: 7CCEk1X6BcoopWuc6vH1raKsq/vLww0ySs/vAnkaDTQu8dBCwhUfEtFKGFd3JyitQbCq8WhmitzHySAM6W5cX5mr2QOwwXSJ1Gcm45cGINsiI6SngTlGFnarPXbOl00v0L0aNL9OiyLNQBe9IsFfExgw7rD0T6lenlcKyZHYQppZ3B23fOw8mFRBCTA=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 1b7b0544872f18baedbb33526952b8c3_ac3d3bf4c27411f18019525400248c00
    ReservedCode2: 7CCEk1X6BcoopWuc6vH1raKsq/vLww0ySs/vAnkaDTQu8dBCwhUfEtFKGFd3JyitQbCq8WhmitzHySAM6W5cX5mr2QOwwXSJ1Gcm45cGINsiI6SngTlGFnarPXbOl00v0L0aNL9OiyLNQBe9IsFfExgw7rD0T6lenlcKyZHYQppZ3B23fOw8mFRBCTA=
---





---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 1b7b0544872f18baedbb33526952b8c3_572e4f88bbab11f1b172525400248c00
    ReservedCode1: mqJ7ZdR8T4T6+MajMU+lbZxKtBAuUGwIhQ4U9Npi+FIwEFZRKHdtQBBTeUwOzwX6/Ck5C8HL3HqXAyvkLkx9Hrq04cED+D8DCSXeVyPbFwtEYHDRvVDNazcoNSY6zzsnaou2ts2bQtzr4VaG7RP/F2C6PdVI2Wsm5I1F7IyWC+w9QYofUHzl495Oa6c=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 1b7b0544872f18baedbb33526952b8c3_572e4f88bbab11f1b172525400248c00
    ReservedCode2: mqJ7ZdR8T4T6+MajMU+lbZxKtBAuUGwIhQ4U9Npi+FIwEFZRKHdtQBBTeUwOzwX6/Ck5C8HL3HqXAyvkLkx9Hrq04cED+D8DCSXeVyPbFwtEYHDRvVDNazcoNSY6zzsnaou2ts2bQtzr4VaG7RP/F2C6PdVI2Wsm5I1F7IyWC+w9QYofUHzl495Oa6c=
---



# AI4S Submission — Optimization Plan (v1)

> **Report restructure note (2026-10-07):** `12_technical_report_draft_v7.md` has been restructured along the scientific storyline (task definition → evaluation protocol → main results → exploration and boundaries) and compressed from 65–69 pages to **17 pages**. Former versioned sections (§12–§27, Stage / P0–P4 labels) no longer exist in the current report; numbered references to §12–§27 in this document point to previous report versions (v4/v5/v6/v7-pre-restructure) and are kept verbatim as execution records. Current report map: §1 Introduction and Task Definition, §2 Data & Materials, §3 Methods, §4 Results, §5 Discussion, §6 Reliability Analysis, §7 Impact, §8 Conclusion, §9 Future Work, §10 Reproduction Instructions, §11 External Resources and Licenses, Appendix A (exploratory and negative-result details), Appendix B (figure and asset inventory), References. Kaggle writeup `21_kaggle_writeup_draft.md` has been rewritten along the same storyline.

**Competition:** AI4S Open Innovation: AI for Life Science (Kaggle Hackathon)
**Project:** Morphological Phenotypic Profiling of Chemical Perturbations with JUMP-Cell Painting Data
**Plan file:** `reports/20_improvement_plan.md`
**Date:** 2026-10-01
**Status:** Work in progress — statuses updated as each item is executed (see `22_optimization_log.md` for per-item detail)

---

## 1. Hard Requirements (Hard Items)

### H1. Team placeholder handling

| Field | Detail |
|---|---|
| Target | Check report v3 (`reports/12_technical_report_draft_v3.md`) and README for `ShapeToTarget` / `Member N` placeholders; keep them visible and flag as "user must fill in"; never fabricate real names |
| Approach | grep-style scan of report v3 + README for placeholder tokens; record exact locations; keep placeholders intact; note in checklist |
| Status | **需用户填写** |
| Evidence | Placeholders kept in v3 L33/39-41, README L18, checklist L126; team name not fabricated; user must fill before submission |

### H2. Kaggle Writeup draft

| Field | Detail |
|---|---|
| Target | Create `reports/21_kaggle_writeup_draft.md` — top category declaration (Model & Algorithm), demo video link, public repo link, technical report link, abstract, methods, key results (AUC=0.768, 36 enriched pairs, microtubule MWU p=0.00145), negative results, reproduction steps; **written in English** |
| Approach | Draft from report v3 front matter / abstract / §3–§4 / §10; add Kaggle-specific structure and submission links |
| Status | **完成** |
| Evidence | reports/21_kaggle_writeup_draft.md written (8.2 KB, English): Model & Algorithm declaration, demo/repo/report links, abstract, methods, AUC=0.768/36 pairs/p=0.00145, negative results, reproduction |

### H3. Technical report PDF

| Field | Detail |
|---|---|
| Target | Convert report v3 or new v4 to PDF → `reports/12_technical_report_draft_v4.pdf` (or v3.pdf) |
| Approach | Check pandoc / wkhtmltopdf / LaTeX availability; pandoc + xelatex confirmed available on this machine; fallback weasyprint/reportlab via pip; record blocker if all fail |
| Status | **完成** |
| Evidence | reports/12_technical_report_draft_v4.pdf (554 KB). Route: pandoc->standalone HTML + Edge headless --print-to-pdf (xelatex/pdflatex blocked by "elevated privileges" guard) |

### H4. GitHub Pages landing page

| Field | Detail |
|---|---|
| Target | Create `github_repo/docs/index.html` — project name, description, embedded key figures, demo video, repo/report links, reproduction note, MIT license |
| Approach | Self-contained single HTML referencing `figures/*.png` + `demo_video.mp4` relative links; note "enable Pages → docs/ in GitHub Settings after push" |
| Status | **完成** |
| Evidence | github_repo/docs/index.html written (7.0 KB): hero KPIs, embedded demo_video.mp4 + 7 figures, links, reproduction block, MIT note; Pages enable: Settings->Pages->Deploy from branch->docs/ after push |

---

## 2. Enhancement Items (A–E)

### A. Alignment with published work

| Field | Detail |
|---|---|
| Target | Add "Comparison with Published Work" section to report v4; cite JUMP-CP paper (Nat Methods 2024, 21:1114–1121) and official MoA classification SOTA (Source S8 CellProfiler 99.1% Accuracy; Source S3 94.9%); discuss why our AUC 0.768 differs (feature granularity / classification granularity / cell lines / time points); state incremental contribution |
| Approach | Text work in v4; references appended |
| Status | **完成** |
| Evidence | v4 adds §13 Comparison with Published Work: JUMP-CP Nat Methods 2024 21:1114-1121; SOTA Source S8 99.1% / S3 94.9%; 5 reasons for AUC 0.768 gap; incremental contribution |

### B. Target–phenotype triangular validation

| Field | Detail |
|---|---|
| Target | Ground-truth similarity matrix from shared-target compound pairs (metadata target annotations) vs phenotypic fingerprint similarity (Pearson/Euclidean on 904-feature compound fingerprints); report Spearman correlation + AUC of retrieval; output `reports/figures/13_target_phenotype_correlation.png`; write results into v4 |
| Approach | Load metadata targets (`JUMP-Target-1_compound_metadata_targets.tsv`) + compound fingerprints from `data/profiles/` (mean over replicate wells); compute pairwise similarities; Spearman + retrieval AUC |
| Status | **完成** |
| Evidence | 45,451 pairs / 768 shared-target (1.69%); Spearman=0.0313 (p=2.4e-11); retrieval AUC=0.5702; quintile share 1.19%->2.44%; figure 13_target_phenotype_correlation.png; written to v4 §14 |

### C. Baseline comparison

| Field | Detail |
|---|---|
| Target | Train Logistic Regression / Linear SVM / RandomForest vs XGBoost on same features+labels; 5-fold CV AUC; output `reports/figures/14_baseline_comparison.png` + `reports/14_baseline_comparison.csv`; write into v4 |
| Approach | Well-level 904 features (treated vs DMSO wells) from `data/profiles/BR0011699*.gz`; stratified 5-fold CV; consistent seed |
| Status | **完成** |
| Evidence | 5-fold CV AUC: XGBoost 0.7564 > LR 0.7313 > RF 0.7280 > LinearSVM 0.6802; figure 14 + reports/14_baseline_comparison.csv; v4 §15 |

### D. Structural fingerprint vs phenotypic fingerprint

| Field | Detail |
|---|---|
| Target | RDKit (pip install rdkit if missing) ECFP4 Tanimoto from SMILES vs phenotypic fingerprint similarity; analyze relationship (correlation or conditional probability); output `reports/figures/15_structure_phenotype_correlation.png`; write results into v4; if rdkit installation fails, record blocker and skip |
| Approach | SMILES from metadata; RDKit Morgan fingerprint (ECFP4, radius 2, 2048 bits); Tanimoto matrix vs fingerprint Pearson matrix; Spearman + stratified analysis |
| Status | **完成** |
| Evidence | RDKit parsed 302/302 SMILES; Spearman(Tanimoto,Pheno)=0.0063 (p=0.18); Tanimoto>=0.3->44.2%, >=0.5->72.7% shared-target (baseline 1.7%); figure 15; v4 §16 |

### E. Interactive Dashboard

| Field | Detail |
|---|---|
| Target | `github_repo/docs/interactive_report.html` — self-contained static Plotly HTML: UMAP scatter, ROC curve, enrichment bubble chart, target-strength bar chart; data from local CSVs; single file opens offline |
| Approach | pip install plotly; build charts from `02_phenotype_results.csv`, ROC data from classifier predictions, `04_enrichment_significant.csv`, `12_target_class_strength.csv`; write to_html(include_plotlyjs='inline', full_html=True) |
| Status | **完成** |
| Evidence | github_repo/docs/interactive_report.html (4.8 MB self-contained Plotly; UMAP/ROC/bubble/bar; opens offline) |

---

## 3. Status Legend

- **未开始** — not yet executed
- **完成** — executed, outputs verified on disk
- **阻塞** — cannot proceed; reason recorded in `22_optimization_log.md`
- **需用户填写** — blocked on user-provided information (e.g., team names)

---

## 4. Output Layout

| Product | Path |
|---|---|
| Optimization plan | `reports/20_improvement_plan.md` |
| Kaggle Writeup draft | `reports/21_kaggle_writeup_draft.md` |
| Optimization log | `reports/22_optimization_log.md` |
| Technical report v4 | `reports/12_technical_report_draft_v4.md` |
| Technical report v4 PDF | `reports/12_technical_report_draft_v4.pdf` |
| Technical report v5 (Stage 6) | `reports/12_technical_report_draft_v5.md` |
| Technical report v6 (Stage 7) | `reports/12_technical_report_draft_v6.md` |
| Technical report v7 (Stage 8) | `reports/12_technical_report_draft_v7.md` |
| Stage 6 results CSV | `reports/16_structure_uncertainty_results.csv` |
| Stage 6 figures | `reports/figures/16_structure_enhanced_performance.png`, `17_reliability_calibration.png`, `18_conformal_coverage.png`, `19_low_confidence_review.png`, `20_sider_toxicity.png` |
| Stage 6 pipeline script | `github_repo/05_structure_uncertainty_pipeline.py` |
| Stage 7/8 results CSV (final) | `reports/17_deep_representation_results.csv`, `reports/17_stage8_summary.json` |
| Stage 7 figures | `reports/figures/22_mlp_training_curves.png`, `23_mlp_confusion.png` |
| Stage 8 figures | `reports/figures/24_embedding_comparison.png`, `25_cnn_training_curves.png`, `26_cnn_confusion.png` |
| Stage 7/8 pipeline script | `github_repo/06_deep_representation_pipeline.py` |
| Target–phenotype correlation figure | `reports/figures/13_target_phenotype_correlation.png` |
| Baseline comparison figure + CSV | `reports/figures/14_baseline_comparison.png`, `reports/14_baseline_comparison.csv` |
| Structure–phenotype correlation figure | `reports/figures/15_structure_phenotype_correlation.png` |
| GitHub Pages landing | `github_repo/docs/index.html` |
| Interactive dashboard | `github_repo/docs/interactive_report.html` |

---

## Official Requirements & Implications (re-checked 2026-10-01)

### Official requirement check summary (Kaggle page, verified 2026-10-01)

| Item | Official value (verified 2026-10-01) | Note |
|---|---|---|
| Submission deadline | **2026-10-10 23:59 (GMT+8)** | Original 2026-10-13 was incorrect; folder renamed accordingly (R4) |
| Competition theme | **AI + Organ-on-a-Chip** | Submission narrative updated with OoC relevance (R1) |
| Registration | **Official Google Form registration is mandatory** — without it the submission is **not eligible for judging** | Added as user to-do U3 |
| Evaluation weights | Problem Importance 30% / Technical Approach 30% / Results 20% / Reproducibility 10% / Presentation 10% | Writeup/report emphasize these dimensions |
| Bonus | Cross-disciplinary teams (AI + biology): **+0.5 on Interpretability dimension** | Highlight interdisciplinary composition |

### Four implications (R1–R4) and execution status

| # | Implication | Action taken | Status |
|---|---|---|---|
| R1 | Add Organ-on-a-Chip relevance narrative | New English section "Relevance to Organ-on-a-Chip" added to `21_kaggle_writeup_draft.md` (Cell Painting as OoC core readout; pipeline transferable to chip imaging; official-recommended JUMP-CP dataset) | **已完成** |
| R2 | Confirm official registration form | Must fill the official Google Form before deadline, otherwise not eligible | **待用户** (see U3) |
| R3 | Re-order Writeup to official recommended structure | `21_kaggle_writeup_draft.md` re-ordered: category declaration → demo video → code repository → project summary (200–300 words) → technical report link → optional demo link | **已完成** |
| R4 | Rename competition folder to correct deadline | `2026-10-13 AI4S Open Innovation：AI for Life Science` → `2026-10-10 AI4S Open Innovation：AI for Life Science` | **已完成** |

---

## User To-Do Items (Pending User Action)

### U1. Fill in team information

| Field | Detail |
|---|---|
| Status | **待处理** |
| Detail | Report `12_technical_report_draft_v3.md` (L33 Category Declaration / L39-41 Team Information) and `12_technical_report_draft_v4.md`, plus `github_repo/README.md`, contain the placeholders `ShapeToTarget` and `Member N` (N = 1..3). Submission requires the real team name and member list (1–5 people). Provide the real values to the main Agent, which will update all files and re-push the repository. |
| Steps | 1. Decide the official team name and the list of 1–5 member names. 2. Send the values to the main Agent in chat. 3. Main Agent replaces `ShapeToTarget` / `Member 1`–`Member 3` in `12_technical_report_draft_v3.md`, `12_technical_report_draft_v4.md`, `README.md` (and the checklist row) — no fabricated names are inserted automatically. 4. Main Agent commits and pushes `github_repo` (and reports as needed). 5. Verify on GitHub that the files no longer contain placeholders. |

### U2. Enable GitHub Pages (docs/ folder)

| Field | Detail |
|---|---|
| Status | **待处理** |
| Detail | The project landing page was created at `github_repo/docs/index.html` and the interactive dashboard at `github_repo/docs/interactive_report.html`, but GitHub Pages is not enabled yet (requires a post-push browser action). |
| Steps | 1. Push `github_repo` to GitHub first (network pending; local commit already ready). 2. Open `https://github.com/fakenice/ai4s-cell-painting-phenotyping/settings/pages` in a browser. 3. Under "Build and deployment" → "Source", select **Deploy from a branch**. 4. Choose branch **master** and folder **/docs**, then click **Save**. 5. Wait 1–2 minutes for the first build; the project homepage becomes accessible at `https://fakenice.github.io/ai4s-cell-painting-phenotyping/`. 6. Optionally check the Actions tab for the Pages workflow status. |

### U3. Confirm official Google Form registration (deadline-critical)

| Field | Detail |
|---|---|
| Status | **待处理** |
| Detail | Verified on the official Kaggle page (2026-10-01): besides the Writeup, the team **must submit the official Google Form registration**; without it the submission is **not eligible for judging**. Check whether the team has already filled the form; if not, fill it **before the 2026-10-10 23:59 (GMT+8) deadline**. |
| Steps | 1. Locate the official Google Form link on the Kaggle competition page (Overview/Resources or the competition rules). 2. Confirm with team members whether it has been filled. 3. If not filled, complete and submit the form before 2026-10-10 23:59 (GMT+8). 4. Keep a screenshot/confirmation of the submission as evidence. |

---

## Stage 6 — Structure-aware & Uncertainty-aware Increment (2026-10-01)

Motivated by the official clarification post (scaffold-aware + uncertainty-aware transfer learning are recognized as reasonable **Model & Algorithm** contributions) and to differentiate from sample works (pure classification + UMAP). New items F–H:

### F. Structure-aware (scaffold-aware) modeling

| Field | Detail |
|---|---|
| Target | Generate RDKit ECFP4 fingerprints from the 303 JUMP-CP SMILES, fuse them into the existing phenotype classifier (XGBoost), compare against morphology-only baseline (AUC/AP + feature importance); reproducible script |
| Approach | `github_repo/05_structure_uncertainty_pipeline.py` part 1: RDKit Morgan r=2 / 1024 bits; three XGBoost models (pheno-only / fp-only / pheno+fp) on identical stratified 5-fold CV; scaffold grouping (single-linkage Tanimoto > 0.5) → 5-fold GroupKFold new-scaffold generalization |
| Status | **完成** |
| Evidence | trt-vs-DMSO AUC 0.7682 → **1.0000** (AP 0.9359 → 1.0000) on pheno+fp; fingerprint importance **87.7%**; scaffold GroupKFold on trt-vs-all-controls: pheno+fp **0.4679** > fp 0.3593 > pheno 0.2809. See report v5 §18.1, figure 16, results CSV. **Stage 11 P1 update:** the trt-vs-DMSO AUC 1.0 is labeled a *structural control* (ECFP4 distance evidence, P0-3; report v7 §18.1/§24.3), and the default generalization protocol is now the soft scaffold-grouped CV τ = 0.6: pheno+fp AUC **0.5222** / AP 0.6545, pheno-only AUC **0.3349** / AP 0.5559 (report v7 §24.2; the 0.4679 hard-scaffold number is superseded as headline) |

### G. Uncertainty-aware modeling

| Field | Detail |
|---|---|
| Target | Probability calibration (Platt + isotonic) + split conformal prediction (calibration quantile); reliability diagram; empirical coverage; low-confidence → human-review OoC workflow figure and sample list |
| Approach | `05_structure_uncertainty_pipeline.py` part 2: stratified 70/15/15 split on pheno-only model; Platt/isotonic calibration; split conformal α=0.1; low-confidence margin |p−0.5| < 0.15 → review queue |
| Status | **完成** |
| Evidence | ECE 0.1461 → 0.1160 (Platt) → **0.0930** (isotonic); Brier 0.1833 → **0.1623**; conformal q_hat 0.5600, empirical coverage **0.847** (nominal 90%, mean width 0.7809); **27/98 (27.6%)** test wells flagged for human review. Figures 17–19, report v5 §18.2 |

### H. Exploratory SIDER toxicity prediction

| Field | Detail |
|---|---|
| Target | Predict SIDER toxicity classes from phenotype features; honest reporting of class imbalance, tiny sample size, weak/strong AUC/AP |
| Approach | `05_structure_uncertainty_pipeline.py` part 3: merge SIDER on 256 compounds (only 46 annotated, 17.7% coverage); has_sider 5-fold CV; burden high-vs-low within annotated set, repeated 3×3-fold CV |
| Status | **完成** |
| Evidence | has_sider AUC **0.6359** / AP 0.3673 vs baseline 0.180 — weak signal, reported as exploratory with limitations; burden AUC 0.4537±0.0310 — **null**. Figure 20, report v5 §19 |

---

## Stage 7 — Deep Representation Learning & Transfer Learning Increment (2026-10-02)

Motivated by the need to strengthen the "AI / deep learning" algorithmic content of the submission (in-house trained deep model + transfer-learning embedding check). New items I–J:

### I. In-house deep model on handcrafted features (small MLP)

| Field | Detail |
|---|---|
| Target | Train an in-house deep model (small MLP) on the same 904-feature morphology matrix under the same task/CV as the XGBoost baseline (trt vs DMSO, 5-fold stratified OOF); add compound-grouped GroupKFold leakage analysis | 
| Approach | `github_repo/06_deep_representation_pipeline.py` part 1: MLP `904→256→64→1`, ReLU + dropout 0.3, Adam lr 1e-3 / wd 1e-4, 20 epochs, batch 64, seed 42; GroupKFold grouped by `pert_iname + plate` on trt-vs-all-controls (768 wells) |
| Status | **完成** |
| Evidence | trt-vs-DMSO OOF **AUC 0.7746 / AP 0.9361 / ACC 0.7855** (vs XGBoost 0.768 — matches/edges); compound-grouped GroupKFold **AUC 0.5944 / AP 0.7513 / ACC 0.6510** (leak-free estimate). See report v6 §21.2, figures 22–23, results CSV |

### J. Transfer learning embeddings & self-trained CNN

| Field | Detail |
|---|---|
| Target | Verify ImageNet-pretrained deep embeddings can be extracted from local JUMP-CP raw images (transfer learning); attempt self-trained single-cell CNN on Cellpose crops with leak-free grouping; honestly skip anything not executable on local assets |
| Approach | `06_deep_representation_pipeline.py` part 2: torchvision ResNet18 (ImageNet) 512-d embedding extraction from the 8 local TIFFs; asset-gated skip of deep-embedding-vs-handcrafted classifier (needs trt + DMSO images) and single-cell CNN (no DMSO crops) |
| Status | **完成（含如实跳过）** |
| Evidence | ResNet18 embeddings OK (512-d, n=2, 0.36 s, seed fixed); fig. 21 **not produced** (superseded by fig. 24). Deep-embedding comparison and single-cell CNN were **deferred to Stage 8** (original local subset treated-only; no fabricated numbers). See report v6 §21.3–21.4 / v7 §21.3–21.4 |


## Stage 8 — DMSO Control Images & Image-Level Deep Learning (2026-10-02)

Resolves the Stage 7 data gap (treated-only images) by downloading matched-plate DMSO control images from the public JUMP-CP registry, then lands both previously skipped image-level experiments with leak-free splits. New items K–L:

### K. Deep-embedding vs handcrafted vs concatenation classifier comparison

| Field | Detail |
|---|---|
| Target | Compare handcrafted 904-d profiles vs ImageNet-pretrained ResNet18 512-d embeddings vs 1416-d concat for trt-vs-DMSO image classification on matched plates |
| Approach | Downloaded 6 DMSO sites (same plate `BR00116991`, source_4, AWS public bucket) to pair with 6 treated sites; torchvision ResNet18 embeddings from ch1/ch4/ch2 RGB composites; LogisticRegression with standardized features; well-grouped LOO primary + site-level GroupKFold stability check; `06_deep_representation_pipeline.py` part 3 |
| Status | **完成** |
| Evidence | well-grouped LOO: deep 512-d **AUC 0.7778 / AP 0.8056 / ACC 0.5000**; handcrafted 904 AUC 0.5556 / AP 0.5889 / ACC 0.5000; concat 1416 AUC 0.6667 / AP 0.6389 / ACC 0.6667; site-level GroupKFold AUC 0.2500 (n=12 sites — unstable, reported as limitation). See report v7 §21.3, figure 24, results CSV |

### L. Self-trained single-cell CNN (Cellpose crops)

| Field | Detail |
|---|---|
| Target | Self-trained small CNN for trt-vs-DMSO single-cell classification with leak-free well-grouped splits (test must contain DMSO wells) |
| Approach | Cellpose `cpsam_v2` on all 12 sites → 2,564 crops (6 wells: 3 trt / 3 DMSO); small 64×64 CNN (conv blocks → pooling → dense); well-grouped GroupKFold(4), seed 42, 20 epochs; `06_deep_representation_pipeline.py` part 4 |
| Status | **完成（如实报告负面结果）** |
| Evidence | test **AUC 0.0955 / AP 0.2698 / ACC 0.3292** (below chance — small-sample negative reported honestly). See report v7 §21.4, figures 25–26, results CSV |

---

## Stage 9 — Ablation, Generalization & OoC Decision Chain (2026-10-05)

Final optimization pass before the 2026-10-10 deadline: real ablation numbers for
the four feature sets, 5-fold CV of the main model, an explicit compound-level
class-overlap (leakage) analysis, a mechanistic discussion of the single-cell CNN
negative, an Organ-on-a-Chip decision-chain figure, pinned dependency versions and
a regenerated PDF. New items M–O:

### M. Ablation study & 5-fold CV of the main model

| Field | Detail |
|---|---|
| Target | Real, reproducible ablation table (pheno-only / fp-only / pheno+fp / deep embedding) and 5-fold CV mean±std of the main pheno+fp model |
| Approach | `scripts/ablation_cv_repro.py` mirrors 05 hyperparameters/splits (seed 42, XGB n_est 200, depth 3, lr 0.05, subsample 0.8, colsample 0.6) on trt-vs-DMSO (648 wells / 257 compounds); deep-embedding and CNN rows reuse existing Stage 7/8 outputs |
| Status | **完成** |
| Evidence | pheno-only OOF AUC 0.7682 (reused 05 CSV; per-fold rerun 0.7688 ± 0.0261), fp-only AUC 1.0000, pheno+fp AUC 1.0000, deep 512-d (well-grouped LOO) AUC 0.7778 (reused Stage 8); pheno+fp 5-fold 1.0000 ± 0.0000. See report v7 §22.1–22.2. **Stage 11 P1 update:** the well-level 5-fold OOF is retained as an in-fold sanity check only; the default evaluation protocol is the soft scaffold-grouped CV τ = 0.6 (pheno+fp AUC 0.5222 / AP 0.6545; pheno-only 0.3349 / AP 0.5559; report v7 §22.2/§24.2) |

### N. Class-overlap (leakage) analysis

| Field | Detail |
|---|---|
| Target | Quantify compound sharing across folds of the well-level CV; re-evaluate the main model under a compound-level split |
| Approach | Per-fold compound overlap computed on the 05-scheme folds; compound-split control (trt by compound GroupKFold, DMSO 80/20 per fold) rerun this stage |
| Status | **完成** |
| Evidence | well-level folds share 84.6–91.4% of test compounds with training (78.5–87.6% of wells); compound-split pheno+fp OOF AUC **1.0000** (zero trt sharing across folds) — DMSO's structural uniqueness drives trt-vs-DMSO; the generalization bottleneck is quantified at soft scaffold-grouped CV τ = 0.6: pheno+fp AUC **0.5222** / pheno-only 0.3349 (hard scaffold 0.5258, fp-cluster 0.4775; report v7 §22.3/§24.2). See report v7 §22.3 |

### O. OoC decision chain, dependency pinning & PDF regeneration

| Field | Detail |
|---|---|
| Target | Add the Organ-on-a-Chip drug-screening decision-chain section + figure; pin requirements.txt to verified versions; regenerate PDF; sync writeup/plan/log |
| Approach | New figure 27 (phenotype → target/toxicity → OoC validation → drug decision, with confidence gate + human-review loop); requirements.txt pinned to the environment that produced the submitted results (2026-10-05); PDF rebuilt from the v7 md (pandoc → HTML → Chrome headless) |
| Status | **完成** |
| Evidence | `reports/figures/27_ooc_decision_chain.png` + `figures/27_ooc_decision_chain.png`; report v7 §22.5; PDF 20 pages, MD5 in optimization log |

## Stage 10 — Self-Supervised Representations, Well-Position Batch Correction & Retrieval Validation (2026-10-05)

Three complementary validation experiments before the 2026-10-10 deadline:
contrastive self-supervised representations (DINOv2 / OpenPhenom) vs the
ResNet18 baseline, harmonypy well-position batch correction, and phenotypic
retrieval / known-target enrichment. New items P–R:

### P. Self-supervised representation comparison (DINOv2 / OpenPhenom)

| Field | Detail |
|---|---|
| Target | Benchmark DINOv2 and OpenPhenom embeddings vs the ResNet18 deep embedding (AUC 0.7778) on the 12-site treated/DMSO image set, well-grouped LOO (6 wells) |
| Approach | timm DINOv2 vit_small/base (lvd142m weights) + HuggingFace OpenPhenom vit_small16 (RGB-3 and 8-channel Cell Painting), LR C=1.0 standardized, LeaveOneGroupOut by well; OpenPhenom loaded via hf-mirror (official endpoint unreachable) |
| Status | **完成** |
| Evidence | ResNet18 0.7778/0.8056/0.5000; DINOv2 vit_small 0.3333/0.5000/0.3333; vit_base 0.4444/0.5333/0.5000; OpenPhenom RGB 0.3333/0.4778/0.1667; OpenPhenom 8-ch 0.6667/0.6389/0.6667. No self-supervised embedding beats the baseline; OpenPhenom 8-ch closest. Report v7 §23.1, fig. 28a |

### Q. Harmony well-position batch correction

| Field | Detail |
|---|---|
| Target | Correct 904-feature profiles for plate / well-position covariates with harmonypy; re-run main pheno+fp (5-fold OOF) and scaffold-grouped CV; compare before/after AUC |
| Approach | harmonypy 0.0.9 (categorical Plate + Row/Col covariates; pandas 2.x describe patch); maskA (trt vs DMSO, 648 wells) OOF + maskB (trt vs ctrl, 768 wells) scaffold GroupKFold (Tanimoto > 0.5) |
| Status | **完成** |
| Evidence | maskA before/after AUC **1.0000/1.0000** (no change; fp dominates); maskB scaffold-group CV (hard scaffold, Tanimoto > 0.5) AUC 0.4679 → **0.4136** (Δ −0.054; correction removes informative plate/position structure). Negative result recorded; Harmony not recommended by default. Report v7 §23.2, fig. 28b. **Stage 11 P1 note:** the maskB Harmony reference uses the *hard* scaffold grouping; the default protocol is the soft τ = 0.6 CV (pre-Harmony pheno+fp AUC 0.5222, Table 24.2) |

### R. Phenotype retrieval & known-target enrichment

| Field | Detail |
|---|---|
| Target | Validate the 904-feature profiles as a retrieval/enrichment substrate: replicate-retrieval AP (same-compound wells) and known-target enrichment (Fisher / AUROC) |
| Approach | Well-level cosine-similarity retrieval AP on maskA (648 wells / 257 compounds) before/after Harmony; compound-level pair cosine similarity vs shared-target annotation (JUMP-Target-1 compound_metadata_targets.tsv); per-target AUROC + Fisher on top-10% similar pairs, BH-corrected |
| Status | **完成** |
| Evidence | Replicate-retrieval mean AP 0.2451 vs chance 0.0401 (pair AUC 0.6335); after Harmony 0.0766. Shared-target pair AUROC 0.5611 (p = 2.76e-07, 569/32,640 pairs); 162 targets tested → 12 BH-significant by per-target AUROC (TUBB/TUBB4B 0.9998, TUBA family 0.9997, CACNA2D3 0.9843, CFTR 0.8528), 90 by Fisher on top-10% pairs. Report v7 §23.3, figs. 28c–28d. **Stage 11 P1 update (full-scope):** 648-well 904 rank metrics — MRR 0.3004, median rank 10, R@1 0.202 / R@5 0.406 / R@10 0.503; deep-image embeddings limited to 6 wells (coverage limitation): on the shared scope ResNet18 512-d AP 0.7333 / MRR 1.0 vs 904 AP 0.5083 (report v7 §24.1, fig. 29d) |

---

## Stage 11 — P0 Shortboard Closure & P1 Protocol Fixes (2026-10-06)

Shortboard plan `reports/23_shortboard_plan_p0-p2.md` closed P0 (4/4) in commit
`418f726` and P1 operationalizes the recommendations:

| Item | P1 result | Evidence / report |
|---|---|---|
| P1-1 Full-scope retrieval validation | 648-well 904 baseline AP 0.2451 (chance 0.0401), MRR 0.3004, median rank 10, R@1/5/10 = 0.202/0.406/0.503; deep embeddings only verifiable on 6 wells (ResNet18 AP 0.7333 vs 904 0.5083) | report v7 §24.1, `19_stage11_p1_retrieval_full_results.csv`, `19_stage11_p1_retrieval_summary.json` |
| P1-2 Soft scaffold-grouped CV (τ = 0.6) as default | pheno+fp AUC **0.5222** / AP 0.6545; pheno-only AUC **0.3349** / AP 0.5559 (hard 0.5258 / fp-cluster 0.4775) | report v7 §22.1–22.3, §24.2, fig. 29b |
| P1-3 trt-vs-DMSO AUC 1.0 → structural control | Label added with P0-3 ECFP4 distance evidence (DMSO–compound mean 0.9683, MWU p = 5.95e-148; nearest neighbor sim 0.15) | report v7 §18.1, §22.1, §24.3, fig. 29c |
| P1-4 Descaffolded ECFP4 → ablation control | maskA descaffolded fp 0.9302 / pheno+fp 0.9237; maskB soft-CV descaffolded pheno+fp 0.3166 (vs 0.4775 intact) | report v7 §24.4, `19_stage11_p0_summary.json` |

---

## Stage 11 — P2 Deep-Coverage Extension, Harder-Task Evaluation & Retrieval-Feature Upgrade (2026-10-06)

P2 closes the deep-embedding coverage gap and replaces the saturated
trt-vs-DMSO headline with harder tasks:

| Item | P2 result | Evidence / report |
|---|---|---|
| P2-A Coverage extension | **18 treated wells of BR00116992 downloaded** (8 channels each, 144 TIFFs, 351.1 MB, public AWS cellpainting-gallery bucket, zero failures; plate map verified trt 18/18) → 24 wells / 30 sites embedded (ResNet18 512-d, `19_stage11_p2_embeddings.npz`) | report v7 §25.1, `data/raw/BR00116992/` |
| P2-B Extended replicate retrieval (24 wells, 17 queries) | manual 904 **AP 0.3945** / MRR 0.4085 / R@1 0.235; deep **AP 0.1418** / MRR 0.1788 / R@1 0.059. 6-well P0-4 numbers reproduce exactly (deep 0.7333, 904 0.5083) | report v7 §25.2, `19_stage11_p2_retrieval_summary.json` |
| P2-C Harder task: trt-vs-trt pairwise AUC | 7 compounds × 2 wells, LOOCV LR over 21 pairs: 904 mean **0.7619** (min 0, max 1); deep mean **0.2738** | report v7 §25.3, `19_stage11_p2_retrieval_extended_results.csv` |
| P2-D Harder task: compound-identity top-k | identity top-1/top-5 (14 wells): 904 **0.429 / 0.929**; deep **0.000 / 0.571**; full-scope 260-treated-well 904 identity top-1 0.000 / top-5 0.0115 (256 compounds) — limitation reported | report v7 §25.3 |
| P2-E Deep embedding → retrieval feature | Deep embedding promoted from classification branch to evaluated **retrieval feature**; single-plate advantage (6-well) does not transfer across plates (cross-plate AP 0.096 vs 904 0.128; in-plate 0.108 vs 0.669; DMSO 0.324 vs 0.196); 904 cosine baseline remains default retrieval substrate | report v7 §25.4, `19_stage11_p2_retrieval_breakdown.json` |
| P2-F Protocol unification | Soft-group CV (τ=0.6) default, trt-vs-DMSO AUC 1.0 structural control, descaffolded fp ablation control — carried over from P1 across all docs | report v7 §25.5, §24.2–24.4 |

---

## Stage 11 — P3 Cross-Plate Generalization & P4 Harder-Task Boost (2026-10-06)

P3 validates cross-plate generalization (train BR00116991 → test BR00116992,
zero new downloads); P4 tests model-side upgrades on the P2 harder task
(21-pair LOOCV). Honest results — positives and negatives both reported:

| Item | P3/P4 result | Evidence / report |
|---|---|---|
| P3-A Cross-plate trt-vs-DMSO | strict DMSO cross AUC/AP **0.6825 / 0.9107** (within P1 0.6794/0.9080, P2 0.6892/0.9074); broad control **0.6404 / 0.7933** (within P1 0.6163/0.7714, P2 0.5563/0.7269) — parity (positive) | report v7 §26.2, `20_stage11_p3_cross_plate_results.csv` |
| P3-B Cross-plate same-compound retrieval (904, 260 wells) | p2→p1 AP **0.4157** / R@1 0.331; p1→p2 AP **0.4457** / R@1 0.369; in-plate reference AP **0.9583** / R@1 1.0 — above chance (positive), far below in-plate (negative gap) | report v7 §26.3 |
| P3-C Cross-plate identity & prototype | identity LR/kNN top-1 **0.331 / 0.331**, top-5 0.512 / 0.508 (vs 14-well LOOCV 0.429/0.929; full-scope baseline 0.000/0.0115); prototype 100 pairs mean AUC **0.985**, sign acc **0.927** | report v7 §26.4 |
| P3-D Deep embedding cross-plate | 24-well full-lib 6 queries: 904 AP **0.1101** vs deep **0.0841** — deep generalizes worse across plates | report v7 §26.3 |
| P4-A Boost protocol parity | P2-identical 21 pairs, LOOCV LR AUC, fold-internal fitting; M0 reproduces **0.7619** exactly | report v7 §27.1 |
| P4-B Model-side upgrades | M1 bagging **0.7619** (tie); M2 k=50/100/200 0.7262/0.7619/0.7500; M3 XGB+LR **0.5714** (−0.19); M4 comb **0.4762** (−0.29); M5 904+deep **0.5952** (−0.17) — honest negative: no upgrade beats baseline | report v7 §27.2, `20_stage11_p4_trt_trt_boost_results.csv` |
*（内容由AI生成，仅供参考）*
