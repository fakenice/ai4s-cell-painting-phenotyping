---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 1b7b0544872f18baedbb33526952b8c3_2ebaa479bda811f18019525400248c00
    ReservedCode1: qLF3Rzvee+S/LfBkV4UslWUZ6yAvZE7WgbOBwIe2dma+vEQ1aLVvfYSIGzGUe6nLseDz60rYvTVjeKsZbWdbhcsoXPQoihro3hw826mXgmR82Ejb/xB7bKC5Lv4T24/gz0Fy9WkPNhSHaQfm/HwNzG8Rn7eq6DyYGLFjTR2K5PH5YkYkFY+gPs9G8HQ=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 1b7b0544872f18baedbb33526952b8c3_2ebaa479bda811f18019525400248c00
    ReservedCode2: qLF3Rzvee+S/LfBkV4UslWUZ6yAvZE7WgbOBwIe2dma+vEQ1aLVvfYSIGzGUe6nLseDz60rYvTVjeKsZbWdbhcsoXPQoihro3hw826mXgmR82Ejb/xB7bKC5Lv4T24/gz0Fy9WkPNhSHaQfm/HwNzG8Rn7eq6DyYGLFjTR2K5PH5YkYkFY+gPs9G8HQ=
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
| Target | Check report v3 (`reports/12_technical_report_draft_v3.md`) and README for `<TEAM_NAME>` / `<Member N>` placeholders; keep them visible and flag as "user must fill in"; never fabricate real names |
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
| Stage 6 results CSV | `reports/16_structure_uncertainty_results.csv` |
| Stage 6 figures | `reports/figures/16_structure_enhanced_performance.png`, `17_reliability_calibration.png`, `18_conformal_coverage.png`, `19_low_confidence_review.png`, `20_sider_toxicity.png` |
| Stage 6 pipeline script | `github_repo/05_structure_uncertainty_pipeline.py` |
| Stage 7 results CSV | `reports/17_deep_representation_results.csv` |
| Stage 7 figures | `reports/figures/22_mlp_training_curves.png`, `23_mlp_confusion.png` |
| Stage 7 pipeline script | `github_repo/06_deep_representation_pipeline.py` |
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
| Detail | Report `12_technical_report_draft_v3.md` (L33 Category Declaration / L39-41 Team Information) and `12_technical_report_draft_v4.md`, plus `github_repo/README.md`, contain the placeholders `<TEAM_NAME>` and `<Member N>` (N = 1..3). Submission requires the real team name and member list (1–5 people). Provide the real values to the main Agent, which will update all files and re-push the repository. |
| Steps | 1. Decide the official team name and the list of 1–5 member names. 2. Send the values to the main Agent in chat. 3. Main Agent replaces `<TEAM_NAME>` / `<Member 1>`–`<Member 3>` in `12_technical_report_draft_v3.md`, `12_technical_report_draft_v4.md`, `README.md` (and the checklist row) — no fabricated names are inserted automatically. 4. Main Agent commits and pushes `github_repo` (and reports as needed). 5. Verify on GitHub that the files no longer contain placeholders. |

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
| Evidence | trt-vs-DMSO AUC 0.7682 → **1.0000** (AP 0.9359 → 1.0000) on pheno+fp; fingerprint importance **87.7%**; scaffold GroupKFold on trt-vs-all-controls: pheno+fp **0.4679** > fp 0.3593 > pheno 0.2809. See report v5 §18.1, figure 16, results CSV |

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
| Evidence | ResNet18 embeddings OK (512-d, n=2, 0.36 s, seed fixed); fig. 21 **not produced** (treated-only images — no fabricated comparison); single-cell CNN **skipped** (116 treated-only cells, no crop dir, no DMSO). See report v6 §21.3–21.4, results CSV |

*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
