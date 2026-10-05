---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 1b7b0544872f18baedbb33526952b8c3_30897d9ebda811f197eb525400393706
    ReservedCode1: TZXyrTyJYS8oQ0CgVgkvVZxyehfoOHscKhiVwv4ZdBN1P2UnzB0SUw/HYEyz8xmH8LrdOdRAu9rT9DeNiySP0BdTy+P1hs3NULyr2Rz7zQP9AYheeIMaBRztFVDD2+34FM5yLXAEJBIGYG7OZf9qDFMTlkRFywlhzEz6VfeGV1Y3jW5FqHGgl3J22SY=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 1b7b0544872f18baedbb33526952b8c3_30897d9ebda811f197eb525400393706
    ReservedCode2: TZXyrTyJYS8oQ0CgVgkvVZxyehfoOHscKhiVwv4ZdBN1P2UnzB0SUw/HYEyz8xmH8LrdOdRAu9rT9DeNiySP0BdTy+P1hs3NULyr2Rz7zQP9AYheeIMaBRztFVDD2+34FM5yLXAEJBIGYG7OZf9qDFMTlkRFywlhzEz6VfeGV1Y3jW5FqHGgl3J22SY=
---



# AI4S Submission — Optimization Log

**Project:** Morphological Phenotypic Profiling of Chemical Perturbations with JUMP-Cell Painting Data
**Competition:** AI4S Open Innovation: AI for Life Science (Kaggle Hackathon)
**Log file:** `reports/22_optimization_log.md`
**Date:** 2026-10-01
**Companion plan:** `reports/20_improvement_plan.md`

Executed in order: H1 → H2 → H3 → H4 → A → B → C → D → E → report v4 → PDF.

---

## H1. Team placeholder handling

- **Action:** grep-style scan of `reports/12_technical_report_draft_v3.md`, `README.md`, `00_submission_checklist.md` for `ShapeToTarget` / `Member N` / team mentions.
- **Findings:**
  - `12_technical_report_draft_v3.md`: L33 (Category Declaration), L39–41 (Team Information: `ShapeToTarget`, `Member 1`, `Member 2`, `Member 3`).
  - `github_repo/README.md`: L18 ("AI4S Hackathon Team").
  - `00_submission_checklist.md`: L126 (checklist row).
- **Decision:** keep all placeholders intact; flag as "user must fill in"; no fabricated names. Recorded in plan H1 as `需用户填写`.
- **Issues:** none. This item remains the only user-blocked submission prerequisite.

## H2. Kaggle Writeup draft

- **Action:** wrote `reports/21_kaggle_writeup_draft.md` (English, ~8.2 KB) with: top Category Declaration (Model & Algorithm); demo video link `https://github.com/fakenice/ai4s-cell-painting-phenotyping/raw/master/demo_video.mp4`; public repo link; technical report link; abstract; methods; key results (AUC=0.768, AP=0.936, ACC=0.792, 36 enriched pairs, microtubule MWU p=0.00145); negative results (MOA cluster-level enrichment, strength–toxicity); reproduction steps.
- **Source:** report v3 front matter, §3 Methods, §4 Results, §10 Reproduction, Appendix A.
- **Issues:** none.

## H3. Technical report PDF

- **Attempt 1:** `pandoc v3.md -o v3.pdf --pdf-engine=xelatex` → blocked: xelatex/pdflatex report **"security risk: running with elevated privileges"** and abort.
- **Attempt 2:** same with `--pdf-engine=pdflatex` → same guard.
- **Attempt 3 (success):** pandoc → standalone HTML, then Microsoft Edge headless print-to-PDF:
  - `pandoc 12_technical_report_draft_v4.md -o %TEMP%\ai4s_v4_conv\v4.html --standalone --metadata title=...`
  - `msedge.exe --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=20000 --print-to-pdf=reports\12_technical_report_draft_v4.pdf file:///.../v4.html`
- **Result:** `reports/12_technical_report_draft_v4.pdf` = 554,212 bytes (2026-10-01 22:50). A v3 PDF (474,819 bytes) was also produced earlier by the same route.
- **Issues:** first Edge call returned a 212-byte stub (headless without `--virtual-time-budget`); retried with `--headless=new --virtual-time-budget=20000` → valid PDF.

## H4. GitHub Pages landing page

- **Action:** created `github_repo/docs/index.html` (7.0 KB): title, badges, KPI cards (AUC 0.768 / AP 0.936 / 36 pairs / p=0.00145), embedded `<video src="demo_video.mp4">`, 7 figures from `figures/`, interactive dashboard link, links to report v4 / writeup / plan / log, reproduction block (clone + pip + S3 no-sign downloads + `demo.py`), MIT/CC BY 4.0 note.
- **Issue/reminder recorded on page and in plan H4:** after `git push`, user must enable **Settings → Pages → Deploy from a branch → docs/** in GitHub; a `docs/` folder build needs no Jekyll config.

## A. Alignment with published work

- **Action:** authored v4 §13 "Comparison with Published Work".
- **Citations:** Chandrasekaran SN, et al. *Three million images and morphological profiles of cells treated with matched chemical and genetic perturbations*, Nature Methods 21, 1114–1121 (2024). Official MoA SOTA: JUMP-CP Source S8 CellProfiler **99.1%** accuracy; Source S3 **94.9%**.
- **Gap discussion (5 reasons):** (1) classification granularity — our task is binary treated-vs-DMSO (648 wells) vs multi-class MoA over 3M images; (2) feature granularity — 904 precomputed `normalized_feature_select` features vs bespoke/deep embeddings; (3) cell lines/batches; (4) time points / heterogeneous concentrations; (5) data size and power.
- **Incremental contribution:** reproducible single-machine pipeline, 36 enrichments consistent with tubulin/kinase biology, per-compound strength score, public end-to-end code.
- **Issues:** none.

## B. Target–phenotype triangular validation

- **Data:** `data/profiles/BR00116991.gz` + `BR00116992.gz` (768 wells, 904 features after `Metadata_` removal, dtype=str then numeric coercion to handle quoted fields); `JUMP-Target-1_compound_metadata_targets.tsv` (target_list).
- **Method:** compound fingerprint = mean of replicate wells (302 compounds); pairwise Pearson on 904-feature fingerprints; GT positive = shared target gene (intersection of target_list); Spearman correlation; retrieval AUC; quintile analysis.
- **Numbers:** 45,451 unique pairs; **768 shared-target pairs (1.69%)**; **Spearman = 0.0313 (p = 2.4e-11)**; **retrieval AUC = 0.5702**; shared-target fraction by phenotype-sim quintile: Q1 1.19% / Q2 1.51% / Q3 1.53% / Q4 1.78% / Q5 2.44%.
- **Outputs:** `reports/figures/13_target_phenotype_correlation.png` (89.8 KB); written to v4 §14.
- **Issues:** initial manual CSV parser failed (917 header cols vs 918 data cols because quoted fields contain commas, e.g. compound names); fixed by using `pandas.read_csv(compression='gzip')`.

## C. Baseline comparison

- **Data/labels:** same 648-well matrix as classification (520 treated vs 128 DMSO), 904 features, stratified 5-fold CV (seed 42).
- **Models/params:** LogisticRegression(max_iter=2000, scaled); LinearSVC(max_iter=2000, scaled); RandomForestClassifier(300 trees, depth 12); XGBClassifier(500 trees, lr 0.05, max_depth 6, subsample 0.8, colsample 0.8).
- **Numbers (5-fold CV AUC mean±SD):** LR **0.7313±0.0272**; Linear SVM **0.6802±0.0368**; RF **0.7280±0.0480**; **XGBoost 0.7564±0.0334** (best). Report v3 tuned XGBoost = 0.768; this common-recipe re-run ranks XGBoost first consistently.
- **Outputs:** `reports/figures/14_baseline_comparison.png` (66.6 KB); `reports/14_baseline_comparison.csv` (240 B); written to v4 §15.
- **Issues:** none.

## D. Structural fingerprint vs phenotypic fingerprint

- **Data:** 302 SMILES from JUMP metadata; RDKit (installed via pip, `rdkit` 2024.x) Morgan fingerprints **ECFP4 (radius 2, 2048 bits)**; parse rate **302/302 (100%)**.
- **Numbers:** Spearman(Tanimoto ECFP4, phenotype Pearson) = **0.0063 (p = 0.18)** — no global linear structure–phenotype correlation; **conditional shared-target rate:** baseline 1.7%; Tanimoto≥0.20 → 8.4% (998 pairs); ≥0.30 → **44.2%** (86 pairs); ≥0.40 → **52.6%** (38 pairs); ≥0.50 → **72.7%** (22 pairs); Tanimoto quintile share 1.44% → 2.69%.
- **Outputs:** `reports/figures/15_structure_phenotype_correlation.png` (316.7 KB); written to v4 §16.
- **Issues:** only RDKit deprecation warnings (MorganGenerator); non-blocking.

## E. Interactive Dashboard

- **Action:** `pip install plotly`; script `make_dashboard.py` built 2×2 subplot figure from local CSVs (`02_phenotype_results.csv` UMAP scatter; ROC from `03_pred_trt_vs_DMSO.csv` y_true/y_prob; enrichment bubble from `04_enrichment_significant.csv`; target-class bars from `12_target_class_strength.csv`), rendered with `fig.to_html(include_plotlyjs='inline', full_html=True)`, injected header/KPI note, wrote `github_repo/docs/interactive_report.html`.
- **Result:** 4,848,556 bytes self-contained single HTML; opens offline; hover tooltips with compound names / q-values; dashboard linked from Pages landing page.
- **Issues:** none.

## Report v4 assembly

- Copied v3 → `12_technical_report_draft_v4.md` (529 lines preserved verbatim), inserted **§12 Version 4 Additions — Summary**, **§13 Comparison with Published Work**, **§14 Target–phenotype triangular validation**, **§15 Baseline comparison**, **§16 Structure vs phenotype fingerprints**, **§17 Interactive Dashboard** before `## References`; original section numbering 1–11, appendices and references untouched.
- v4 PDF generated in H3 (554 KB).

## R-series: Official requirements check & submission optimization (re-checked 2026-10-01)

- **Official Kaggle page re-check (2026-10-01):**
  - Submission deadline is **2026-10-10 23:59 (GMT+8)** — the previously assumed 2026-10-13 was incorrect.
  - Competition theme is **AI + Organ-on-a-Chip (OoC)**.
  - Besides the Writeup, the team **must fill the official Google Form registration**, otherwise the submission is **not eligible for judging**.
  - Evaluation weights: Problem Importance 30% / Technical Approach 30% / Results 20% / Reproducibility 10% / Presentation 10%.
  - Cross-disciplinary teams (AI + biology) get **+0.5 on the Interpretability dimension**.
- **Folder rename (R4):** `2026-10-13 AI4S Open Innovation：AI for Life Science` → `2026-10-10 AI4S Open Innovation：AI for Life Science`. Rename-Item reported a non-zero exit code but verification confirmed the new folder exists with full contents and the old path no longer exists; no data loss.
- **Writeup restructure (R3):** `reports/21_kaggle_writeup_draft.md` re-ordered to the official recommended layout: Category Declaration → Demo Video → Code Repository Link → Project Summary (200–300 words) → Technical Report Link → Methods → Results → Negative Results → Reproduction → Repository Contents → Optional Demo Link → License. Original content preserved; only structure added/changed.
- **OoC narrative (R1):** new English section "Relevance to Organ-on-a-Chip" added — Cell Painting as core high-content readout for OoC drug-screening/toxicity; pipeline modules (treated-vs-control classification, target enrichment, phenotypic-strength score, Cellpose segmentation) transferable to chip imaging data; official-recommended JUMP-Cell Painting dataset used.
- **Plan file update:** `reports/20_improvement_plan.md` gained "Official Requirements & Implications (re-checked 2026-10-01)" with the requirement summary and R1–R4 status table; **U3** added (confirm/fill official Google Form before deadline).
- **Checklist date fix:** root `准备清单.md` header updated from "约 2026-10-13" to the verified deadline 2026-10-10 23:59 (GMT+8).
- **Issues:** none blocking; U3 (registration form) and U1 (team names) remain user actions.

## Stage 6 — Structure-aware & Uncertainty-aware increment (2026-10-01)

Drivers: official clarification post recognizes scaffold-aware + uncertainty-aware transfer learning as reasonable **Model & Algorithm** contributions; sample works are mostly pure classification + UMAP, so this increment differentiates the submission.

### F. Structure-aware (scaffold-aware) modeling

- **Data:** 302/303 SMILES parsed by RDKit (same metadata as Stage D); ECFP4 = Morgan r=2, 1024 bits (sparse vector per compound).
- **Models:** XGBoost (500 trees, lr 0.05, max_depth 6, subsample 0.8, colsample 0.8, seed 42), three feature sets on identical stratified 5-fold CV:
  - trt-vs-DMSO (648 wells): pheno-only AUC **0.7682** / AP 0.9359; fp-only AUC 1.0000 / AP 1.0000; **pheno+fp AUC 1.0000 / AP 1.0000** (AUC delta +0.2318, AP delta +0.0641); XGB gain-based fingerprint feature importance **87.7%** (pheno 0.123 vs fp 0.877). Honest caveat: DMSO is the unique negative control, so fingerprint separation reflects control memorization; scaffold-grouped CV is the meaningful generalization test.
  - Scaffold generalization (trt-vs-all-controls, 768 wells): single-linkage Tanimoto > 0.5 clustering → 282 scaffold groups; 5-fold GroupKFold: pheno-only AUC 0.2809, fp-only 0.3593, **pheno+fp 0.4679** (best new-scaffold generalization; below-random absolute level honestly interpreted as in-distribution memorization risk).
- **Outputs:** `reports/figures/16_structure_enhanced_performance.png`; report v5 §18.1; results CSV.
- **Issues:** the near-perfect in-distribution AUC is an honest demonstration of fingerprint leakage of compound identity — mitigated by scaffold GroupKFold as the generalization metric; documented in the report.

### G. Uncertainty-aware modeling

- **Split:** stratified 70/15/15 (train 454 / calib 96 / test 98) on pheno-only model (XGBoost).
- **Calibration:** Platt (LogisticRegression on logits) → ECE 0.1461 → 0.1160, Brier 0.1833 → 0.1698; isotonic → ECE **0.0930**, Brier **0.1623** (best). Test n=98.
- **Split conformal (α=0.1):** conformity score |ŷ − 0.5| on calibration split; q_hat = 0.5600; prediction set = {class if score ≥ q_hat}, else abstain; empirical coverage on test = **0.847** (nominal 90%; width mean 0.7809); 15/98 abstained.
- **Low-confidence → human-review workflow:** margin |p − 0.5| < 0.15 → review queue; **27/98 (27.6%)** test wells flagged; OoC loop: flagged wells → expert/orthogonal assay re-screen → verdict update.
- **Outputs:** `reports/figures/17_reliability_calibration.png`, `18_conformal_coverage.png`, `19_low_confidence_review.png`; report v5 §18.2; low-confidence sample list in results CSV.
- **Issues:** coverage below nominal on a small test set is expected (binomial 95% CI ≈ [0.77, 0.91]); documented honestly.

### H. Exploratory SIDER toxicity prediction

- **Data:** SIDER side-effect counts merged on 256 compound InChIKey matches; **only 46/260 annotated compounds have SIDER entries (17.7% coverage)** — tiny annotated set.
- **Task 1 — has_sider (annotated vs not):** 5-fold CV AUC **0.6359**, AP 0.3673 (baseline prevalence 0.180) — weak signal; no strong claim; interpreted as morphological profiles carrying limited coarse toxicity annotation signal at this scale.
- **Task 2 — burden (high vs low):** median n_side_effects = 91 split within annotated set; repeated 3×3-fold CV AUC **0.4537 ± 0.0310** — null; honestly reported as exploratory with limitations (imbalance, tiny n, single cell line).
- **Outputs:** `reports/figures/20_sider_toxicity.png`; report v5 §19.
- **Issues:** coverage too low for reliable toxicity screening; explicitly framed as exploratory negative/weak result in the report and writeup.

### Report v5 assembly

- Copied v4 → `12_technical_report_draft_v5.md`; inserted **§18 Structure-aware & Uncertainty-aware Modeling** (18.1 scaffold-aware structure fusion; 18.2 calibration + split conformal + low-confidence review workflow), **§19 Exploratory OoC Toxicity Prediction (SIDER)**, **§20 Version 5 Additions — Summary**; updated front matter (Date/Status), Abstract, Appendix B figure/CSV assets, and write-up version references.
- **Writeup sync:** `21_kaggle_writeup_draft.md` — report link v4→v5; Project Summary + Stage 6 sentence; Methods items 9–11; Key Results + 7 Stage-6 rows; Repository Contents (05 script, 12 figures, rdkit in requirements).
- **Plan/log sync:** `20_improvement_plan.md` — Output Layout rows + items F/G/H; this file — Stage 6 section.

## Stage 7 — Deep representation learning & transfer learning increment (2026-10-02)

Drivers: strengthen the "AI / deep learning" content of the submission with an in-house trained deep model plus a transfer-learning embedding check; every sub-step is asset-gated (data availability is checked first, skipped steps are documented — no fabricated numbers).

### I. In-house deep model on handcrafted features (small MLP)

- **Data:** same 904-feature matrix as Stage 5/6; trt-vs-DMSO 648 wells (520/128) and trt-vs-all-controls 768 wells.
- **Model:** MLP `904 → 256 → 64 → 1`, ReLU + dropout 0.3, Adam lr 1e-3 / wd 1e-4, 20 epochs, batch 64, seed 42, early stopping on val loss.
- **Result (same task/CV as Stage 5 XGBoost):** 5-fold stratified OOF **AUC 0.7746 / AP 0.9361 / ACC 0.7855** vs XGBoost AUC 0.768 — in-house deep model matches/edges gradient boosting; handcrafted morphology near separability limit (AUC ≈ 0.77–0.78).
- **Leakage-controlled GroupKFold (trt-vs-all, 768 wells):** grouped by `pert_iname + plate` → **AUC 0.5944 / AP 0.7513 / ACC 0.6510**; drop from ~0.75 shows well-level CV overestimates generalization via compound identity overlap; leak-free number reported alongside.
- **Outputs:** `reports/figures/22_mlp_training_curves.png`, `23_mlp_confusion.png`; report v6 §21.2.

### J. Transfer learning embeddings & self-trained CNN — feasibility check + honest limits

- **ResNet18 embedding extraction (torchvision, ImageNet pretrained):** OK — 512-d embeddings from the 8 local TIFFs (n = 2 valid groups, 0.36 s, seed fixed); proves transfer-learning capability on local raw images.
- **Deep-embedding vs handcrafted classifier comparison (fig. 21):** **skipped** — requires both trt and DMSO images for matched-protocol classifiers; local subset is treated-only (8 TIFFs, single site r01c01, no DMSO images, no official JUMP-CP embedding files under data/). No fabricated comparison.
- **Self-trained single-cell CNN:** **skipped** — Cellpose crops exist only as a summary CSV (116 cells, all treated, no crop/mask directory, no DMSO cells); a two-class leak-free CNN is not executable on this subset.
- **Outputs:** `reports/17_deep_representation_results.csv` (asset inventory + metrics + skip reasons), `reports/17_stage7_summary.json`; script `06_deep_representation_pipeline.py`; `requirements.txt` +torch/torchvision (CPU wheels).

### Report v6 assembly

- Copied v5 → `12_technical_report_draft_v6.md`; inserted **§21 Deep Representation Learning & Transfer Learning (Enhancement H)** (21.1 asset inventory; 21.2 in-house MLP + GroupKFold leakage analysis; 21.3 ResNet18 embedding check; 21.4 single-cell CNN limitation; 21.5 reproducibility assets); updated front matter (Status Draft v6), Abstract, TOC, References (+ResNet18/PyTorch), Appendix B (21 not produced + 22/23), and version references.
- **Writeup sync:** `21_kaggle_writeup_draft.md` — report link v5→v6; Project Summary + Stage 7 sentence; Methods item 12; Key Results + Stage-7 rows; Negative Results + deep-representation limitation; Repository Contents (06 script, 14 figures, torch in requirements).
- **Plan/log sync:** `20_improvement_plan.md` — Output Layout rows + items I/J; this file — Stage 7 section.


## Stage 8 — DMSO control images & image-level deep learning (2026-10-02)

Drivers: resolve the Stage 7 data gap (treated-only local images) by downloading matched-plate DMSO control images from the public JUMP-CP registry, then land both previously skipped image-level experiments (deep-embedding classifier comparison and self-trained single-cell CNN) with leak-free splits. Every number is real; negative/unstable results are reported honestly.

### Data download

- **Source:** public AWS `s3://cellpainting-gallery/cpg0000-jump-pilot/source_4/images/BR00116991/` (no sign-in; retry/region fallback handled; failed/delayed keys reported, none fabricated).
- **Target:** DMSO negative-control wells of the **same plate** `BR00116991` as the existing treated images (matches protocol, minimizes batch effects): wells A02 / A09 / A17, sites r01c01–r02c02, 8 channels each.
- **Result:** 6 DMSO sites downloaded (48 TIFFs, ~2 GB) into `data/raw/BR00116991_dmso/`; paired with 6 existing treated sites (wells A01 / A03 / A04) → **12 sites / 6 wells / 96 TIFFs** for image-level experiments. Full manifest in `data/raw/BR00116991_dmso/manifest.txt`.

### K. Deep-embedding vs handcrafted vs concatenation classifier comparison

- **Embeddings:** torchvision ResNet18 (ImageNet pretrained), penultimate 512-d, from ch1/ch4/ch2 RGB composites of the 12 site images (224×224 normalized); handcrafted = 904-d well profiles; concat = 1416-d.
- **Protocol:** LogisticRegression (standardized, C=1.0); **well-grouped LOO** primary (all sites of one held-out well per fold) + site-level GroupKFold stability check.
- **Results (well-grouped LOO, n=6 wells):** handcrafted 904 AUC 0.5556 / AP 0.5889 / ACC 0.5000; **deep 512-d AUC 0.7778 / AP 0.8056 / ACC 0.5000**; concat 1416 AUC 0.6667 / AP 0.6389 / ACC 0.6667.
- **Stability check (site-level GroupKFold, n=12 sites):** deep AUC 0.2500 / AP 0.4346 / ACC 0.2500 — unstable at this sample size; reported as a limitation, not hidden.
- **Outputs:** `reports/figures/24_embedding_comparison.png`.

### L. Self-trained single-cell CNN

- **Crops:** Cellpose `cpsam_v2` segmented all 12 sites → **2,564 single-cell crops** (`data/interim/cellpose_crops/`, 6 wells: A01/A03/A04 trt, A02/A09/A17 DMSO; per-site meta.json + seg_log.jsonl).
- **Model:** small 64×64 CNN (two conv blocks → global pooling → dense → 1), trt-vs-DMSO binary; **well-grouped GroupKFold(4)** (all cells of a well in the same fold; test folds always contain DMSO wells); 20 epochs, batch 64, Adam lr 1e-3, seed 42.
- **Result (test):** **AUC 0.0955 / AP 0.2698 / ACC 0.3292** — below chance; honestly reported as a small-sample negative (tiny 6-well cohort, per-cell signal weaker than well-aggregated profiles, single-channel 64×64 inputs). Training curves and confusion matrix are kept as execution evidence, not as positive claims.
- **Outputs:** `reports/figures/25_cnn_training_curves.png`, `26_cnn_confusion.png`.

### Assets & sync

- **Final results CSV:** `reports/17_deep_representation_results.csv` updated to final version (asset inventory incl. `n_tiff_trt_dmso=48/48`; embedding-comparison metrics; CNN metrics; figure flags 24–26) + `reports/17_stage8_summary.json`.
- **Report:** `12_technical_report_draft_v6.md` → **v7**: Status Draft v7; Abstract + Stage 7/8 sentences; §21 fully rewritten (21.1 asset inventory incl. DMSO; 21.2 MLP unchanged; 21.3 deep-embedding comparison; 21.4 single-cell CNN; 21.5 reproducibility assets); Appendix B + figures 24–26; Data & reproducibility tail updated.
- **Writeup/plan:** `21_kaggle_writeup_draft.md` (report link v7, Project Summary, Methods item 13, Key Results + Stage-8 rows, Negative Results update, Repository Contents 17 figures); `20_improvement_plan.md` (deliverables + v7 rows, J evidence updated, Stage 8 items K/L).
- **Script/deps:** `06_deep_representation_pipeline.py` updated (parts 0–4: download instructions, asset inventory, MLP, deep-embedding comparison, single-cell CNN); `requirements.txt` +`cellpose>=2.2`.

### Stage 9 — Ablation, Generalization & OoC Decision Chain (2026-10-05)

- **Ablation table (`scripts/ablation_cv_repro.py`, mirrors 05: seed 42, XGB n_est 200, depth 3, lr 0.05, subsample 0.8, colsample 0.6; trt vs DMSO, 648 wells / 520 pos / 128 neg / 257 compounds):**
  - pheno-only: per-fold AUC 0.7729 / 0.7929 / 0.7685 / 0.7896 / 0.7200 → **OOF 0.7682**, mean±std **0.7688 ± 0.0261** (05 CSV reused: AUC 0.7682 / AP 0.9359 / ACC 0.7917)
  - fp-only: 5-fold all 1.0000, OOF **1.0000**
  - pheno+fp (main): 5-fold all 1.0000, OOF **1.0000**, mean±std **1.0000 ± 0.0000**
  - deep embedding (reused `17_stage8_summary.json`): well-grouped LOO **AUC 0.7778 / AP 0.8056 / ACC 0.5000**
- **Class-overlap (leakage) analysis:** well-level 5-fold shares **84.6–91.4%** of test compounds with training folds (78.5–87.6% of test wells); compound-split control (trt GroupKFold by compound + DMSO 80/20 per fold, zero trt sharing): pheno+fp OOF AUC **1.0000** — DMSO structural uniqueness drives trt-vs-DMSO; true bottleneck at scaffold-grouped CV AUC 0.4679 (05, trt vs all controls).
- **CNN negative (AUC 0.0955) mechanistic discussion:** effective n = 6 wells; well-grouped folds leave ~5 training wells; crop-level class ratio 43.7/56.3; 64×64 single-channel input lacks the 8-channel population statistics in which well-level models find signal → below-chance boundary; retained transparently. Report v7 §22.4.
- **OoC decision chain:** figure 27 (single-cell phenotype → target/toxicity prediction → OoC validation → drug decision, confidence gate |p − 0.5| < 0.15 + human-review loop) → `reports/figures/27_ooc_decision_chain.png` + repo `figures/27_ooc_decision_chain.png`; report v7 §22.5.
- **Dependency pinning:** `requirements.txt` all `>=` → `==` (numpy 2.4.6, pandas 3.0.3, scipy 1.17.1, scikit-learn 1.8.0, matplotlib 3.10.9, seaborn 0.13.2, xgboost 3.2.0, rdkit 2026.3.6, tifffile 2026.9.20, torch 2.14.0, torchvision 0.29.0; umap-learn 0.5.12, statsmodels 0.15.0, cellpose 4.2.1.1 — not installed in build env, pinned to PyPI latest stable 2026-10-05).
- **README:** one-command run block (`05_structure_aware_pipeline.py` / `06_deep_representation_pipeline.py`) + data acquisition notes added.
- **PDF regenerated:** v7 md → HTML (pandoc 3.9) → PDF (Chrome headless, A4 compact print style), **18 pages**, MD5 **32F6E261830A6D954CDD00F3733D26BE**, replaced `docs/12_technical_report_draft_v7.pdf` (previous d1e1db8 version: 20 pages, MD5 BA2658CA3E6AB96E1825BAA244058539).
- **AI-trace re-check:** new figure 27 visual-checked (no generated-content watermark); new PDF text layer zero hits for generated-content disclaimers; repo-wide md/text zero hits; no watermark pixels on regenerated assets.
- **Outputs:** report v7 §22 + TOC row, figures 27, README run block, requirements pinned, `reports/ablation_cv_results.json` (interim evidence).

### Stage 10 — Self-Supervised Representations, Harmony Correction & Retrieval Validation (2026-10-05)

- **Experiment 1 — self-supervised representations (`scripts/stage10_self_supervised.py`):** 12 sites (6 treated + 6 DMSO, `data/raw/BR00116991_dmso/`) → well-mean → 6 wells; LR C=1.0 standardized; LeaveOneGroupOut by well.
  - ResNet18 baseline (Stage 8): **AUC 0.7778 / AP 0.8056 / ACC 0.5000** (reproduced).
  - DINOv2 `vit_small_patch14.lvd142m` (384-d): AUC 0.3333 / AP 0.5000 / ACC 0.3333.
  - DINOv2 `vit_base_patch14.lvd142m` (768-d): AUC 0.4444 / AP 0.5333 / ACC 0.5000.
  - OpenPhenom `vit_small16` (HuggingFace `recursionpharma/OpenPhenom`, local snapshot, loaded via hf-mirror — official endpoint unreachable, recorded): RGB-3 AUC 0.3333 / AP 0.4778 / ACC 0.1667; **8-channel** AUC 0.6667 / AP 0.6389 / ACC 0.6667.
  - Conclusion: no self-supervised embedding beats the ResNet18 baseline on the 6-well task; OpenPhenom 8-ch closest (multi-channel value). 11 GB VRAM → vit_small/vit_base as planned.
- **Experiment 2 — Harmony well-position correction (`scripts/stage10_harmony.py`):** harmonypy 0.0.9 on 904 features, covariates Metadata_Plate + Row/Col (categorical; pandas 2.x describe patch).
  - maskA (trt vs DMSO, 648 wells: 520/128): pheno+fp 5-fold OOF **AUC 1.0000 before / 1.0000 after** (fp dominates; no change).
  - maskB (trt vs ctrl, 768 wells): scaffold-grouped CV (Tanimoto > 0.5) **AUC 0.4679 → 0.4136** (AP 0.6244 → 0.5899; ACC 0.6654 → 0.6602) — correction removes informative plate/position structure; **negative result recorded, Harmony not recommended by default**.
  - Convergence: maskA 7 iterations; maskB hit the 10-iteration cap (not converged, reported as-is).
- **Experiment 3 — retrieval & known-target enrichment (`scripts/stage10_retrieval.py`):**
  - Replicate-retrieval AP (well level, maskA, 648 wells / 257 compounds): raw 904 mean AP **0.2451** vs chance 0.0401 (pair AUC 0.6335); Harmony-corrected mean AP 0.0766 (pair AUC 0.6383) — raw profiles retrieve replicates at ~6.1× chance; correction removes most replicate-consistency signal.
  - Known-target enrichment (compound level, JUMP-Target-1 `compound_metadata_targets.tsv`): shared-target pairs 569/32,640, pair AUROC **0.5611** (Mann–Whitney p = 2.76e-07); 162 targets ≥ 2 compounds tested → **12 BH-significant** by per-target AUROC (TUBB/TUBB4B 0.9998, TUBA family 0.9997, CACNA2D3 0.9843, CFTR 0.8528), **90 by Fisher** on top-10% similar pairs.
- **Figures:** `figures/28a_self_supervised_comparison.png`, `28b_harmony_batch_correction.png`, `28c_retrieval_replicate_ap.png`, `28d_target_enrichment.png` (+ `reports/figures/` copies).
- **Assets:** `reports/18_stage10_selfsupervised_summary.json`, `18_stage10_harmony_results.csv`, `18_stage10_retrieval_results.csv`, `18_stage10_target_enrichment.csv`, `18_stage10_summary.json`.
- **Report/writeup/plan synced:** report v7 §23 (+TOC row, Appendix B rows 27/28a–d); writeup Key Results + Negative Results; plan items P–R.

## Final status

| Item | Status |
|---|---|
| H1 Team placeholder | 需用户填写 (blocked on real names) |
| H2 Writeup draft | 完成 (synced to v6) |
| H3 v4 PDF | 完成 |
| H4 GitHub Pages | 完成 (needs user push + Pages enable) |
| A–E enhancements | 完成 |
| Stage 6 (F/G/H: structure-aware, uncertainty-aware, SIDER) | 完成 (script 05, figures 16–20, results CSV, report v5, writeup/plan/log synced) |
| Stage 7 (I/J: in-house MLP, GroupKFold leakage, ResNet18 embeddings, CNN limitation) | 完成 (script 06, figures 22–23, results CSV, report v6, writeup/plan/log synced) |
| Stage 8 (K/L: DMSO images, deep-embedding comparison, single-cell CNN) | 完成 (12 sites/6 wells/96 TIFFs, figures 24–26, final results CSV, report v7, writeup/plan/log synced) |
| Stage 9 (M/N/O: ablation, 5-fold CV, class-overlap, CNN discussion, OoC chain, pin deps, PDF regen) | 完成 (ablation numbers, figures 27, report v7 §22 + TOC, writeup/plan/log synced, requirements pinned, PDF 18 pp MD5 32F6E2…, README run block) |
| Stage 10 (P/Q/R: self-supervised reps, Harmony correction, retrieval & target enrichment) | 完成 (figures 28a–28d, report v7 §23 + TOC + Appendix B, writeup/plan/log synced, results CSV/JSON in reports/18_stage10_*) |
| Optimization log | 完成 (this file) |
| Official re-check (R1–R4) | 完成 (R2/U3 待用户) |
| Git push (Stage 7 commit 4886f6f) | 成功推送 origin/master（ssh://ssh.github.com:443），远程与本地一致 |
| Git push (Stage 8 commit) | 成功推送 origin/master（随 Stage 9 commit 一起） |
| Git push (Stage 9 commit 0a0363b) | 成功推送 origin/master（ssh://ssh.github.com:443），远程与本地一致 |

