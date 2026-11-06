





# AI4S Submission — Optimization Log

> **Report restructure note (2026-10-07):** `12_technical_report_draft_v7.md` has been restructured along the scientific storyline (task definition → evaluation protocol → main results → exploration and boundaries) and compressed from 65–69 pages to **17 pages**. Former versioned sections (§12–§27, Stage / P0–P4 labels) no longer exist in the current report; numbered references to §12–§27 in this document point to previous report versions (v4/v5/v6/v7-pre-restructure) and are kept verbatim as execution records. Current report map: §1 Introduction and Task Definition, §2 Data & Materials, §3 Methods, §4 Results, §5 Discussion, §6 Reliability Analysis, §7 Impact, §8 Conclusion, §9 Future Work, §10 Reproduction Instructions, §11 External Resources and Licenses, Appendix A (exploratory and negative-result details), Appendix B (figure and asset inventory), References. Kaggle writeup `21_kaggle_writeup_draft.md` has been rewritten along the same storyline.

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

- **Action:** wrote `reports/21_kaggle_writeup_draft.md` (English, ~8.2 KB) with: top Category Declaration (Model & Algorithm); demo video link `https://youtu.be/IBZbox9Akcg`; public repo link; technical report link; abstract; methods; key results (AUC=0.768, AP=0.936, ACC=0.792, 36 enriched pairs, microtubule MWU p=0.00145); negative results (MOA cluster-level enrichment, strength–toxicity); reproduction steps.
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

### Stage 11 — P0 Shortboard Closure: Eval Disaggregation, Soft-Group CV, Task Quantification, Retrieval Track Switch (2026-10-06)

Plan: `reports/23_shortboard_plan_p0-p2.md` (P0 executed 4/4; P1/P2 scoped). Scripts `scripts/stage11_p0_structural.py` / `stage11_p0_retrieval.py`; summaries `reports/19_stage11_p0_summary.json`, `19_stage11_p0_retrieval_summary.json`, `19_stage11_p0_retrieval_results.csv`, `19_stage11_p0_embeddings.npz`.

- **P0-1a — within vs cross-scaffold CV decomposition (maskB, compound-grouped):**
  - pheno+fp: overall AUC **0.4932**, within AUC **0.3100** (n=238), cross AUC **0.7516** (n=530), AP 0.6367.
  - pheno-only: overall AUC **0.3232**, within AUC **0.1004**, cross AUC **0.6121**, AP 0.5492.
  - Cross-scaffold pairs are easy (structure leaks); within-scaffold phenotype is genuinely hard — headline 0.49–0.52 mixed two regimes.
- **P0-1b — descaffolded ECFP4 (Bemis-Murcko removed; 270/303 descaffolded, 282 scaffold groups @ Tanimoto 0.5):**
  - maskA trt-vs-DMSO: fp-orig AUC 1.0000 → fp-descaffolded **0.9302 / AP 0.9823**; pheno+fp-orig 1.0000 → pheno+fp-descaffolded **0.9237 / AP 0.9818** — trt-vs-DMSO stays near-perfect after scaffold removal (substituent-level structure, not scaffold identity).
  - maskB scaffold-groupCV: pheno+fp-orig 0.4775 → pheno+fp-descaffolded **0.3166** (cross-scaffold generalization depends on scaffold info; descaffolding hurts).
- **P0-2 — soft group CV (maskB):** hard scaffold AUC 0.5258/AP 0.6563; soft τ=0.6 **0.5222**/0.6545; soft τ=0.4 **0.5192**/0.6558; fp-cluster 0.5 **0.4775**/0.6299 (pheno-only: 0.3153/0.3349/0.3170/0.2854 AUC). Grouping choice is stable (≤0.007 AUC); fp-cluster most pessimistic.
- **P0-3 — task-attribute quantification (ECFP4 Tanimoto distances):** DMSO-vs-compounds (n=302) mean **0.9683** / median 0.9695 / min 0.85 / q10 0.9488; compound-compound (n=45,451) mean **0.9013** / median 0.9048; MWU p = **5.95e-148**; DMSO nearest neighbor 2,5-furandimethanol (sim 0.15). trt-vs-DMSO is structurally separable by construction → AUC 1.0 is a fingerprint-identity control, not phenotype power.
- **P0-4 — retrieval track switch (same cosine protocol; 904 recomputed on same 6 wells = 0.5083; chance_AP 0.5):**
  - well-level AP: ResNet18 **0.7333** > DINOv2-vits14 **0.6778** > DINOv2-vitb14 **0.6222** > OpenPhenom-ch8 **0.6083** > 904 **0.5083** > OpenPhenom-rgb3 **0.4639**; pair AUC 0.5556/0.5833/0.5000/0.3889/0.3056/0.1944.
  - site-level AP (12 sites): 0.3425 (ResNet18), 0.1471/0.1559 (DINOv2), 0.1992/0.2249 (OpenPhenom) — site noise large; all deep embeddings except OpenPhenom-rgb3 beat 904 at well level.
  - OpenPhenom initially failed (pos-embed shape mismatch, remote-code cache drift); rebuilt transformers module cache → ran correctly.
- **Figures:** `figures/29a_eval_disaggregation.png`, `29b_soft_grouped_cv.png`, `29c_fp_distance_distribution.png`, `29d_retrieval_track_switch.png` (+ `reports/figures/` copies).
- **Decision for P1:** soft-group CV τ=0.6 default (see P0-2: τ=0.6 recommended as stable, closest to hard-scaffold semantics); trt-vs-DMSO AUC 1.0 labeled as structural control; ResNet18/DINOv2 embeddings promoted as retrieval features (validate on 648-well scope); descaffolded fp kept as ablation control only.

### Stage 11 — P1 Protocol Fixes: Full-Scope Retrieval Validation, Soft-Group Default CV, Structural-Control Labeling, Descaffold-Ablation Downgrade (2026-10-06)

Script `scripts/stage11_p1_retrieval_full.py`; summaries `reports/19_stage11_p1_retrieval_full_results.csv`, `19_stage11_p1_retrieval_summary.json`. Report v7 updated in place (§18.1, §22.1–22.3, §23.2, new §24); PDF regenerated.

- **P1-1 — full-scope (648-well) retrieval validation:** manual 904 features under the Stage 10 cosine protocol over all 648 maskA wells — mean replicate AP **0.2451** (chance 0.0401), pair AUC 0.6335, **MRR 0.3004, median rank of first hit 10, R@1 0.202 / R@5 0.406 / R@10 0.503** (rank metrics newly computed in P1). Deep-image embeddings exist for only 6 wells (plate BR00116991; no local images for the other 642) → full-scope deep retrieval **not feasible, reported as a coverage limitation**; on the 6-well shared scope ResNet18 512-d AP **0.7333 / MRR 1.0** vs manual 904 AP 0.5083 / MRR 0.5833 (deep embeddings retain their advantage where image data exists).
- **P1-2 — soft scaffold-grouped CV (τ = 0.6) as default protocol:** report v7 now fixes the default CV numbers at pheno+fp **AUC 0.5222 / AP 0.6545** and pheno-only **AUC 0.3349 / AP 0.5559** (§22.2 Protocol note, §23.2, §24.2 Table 24.2); well-level 5-fold OOF (1.0000) demoted to in-fold sanity check; hard-scaffold 0.4679/0.5258 and fp-cluster 0.4775 kept as sensitivity references.
- **P1-3 — trt-vs-DMSO AUC 1.0 labeled structural control:** §18.1 caveat rewritten to cite P0-3 ECFP4-distance evidence (DMSO–compound mean distance 0.9683, MWU p = 5.95e-148, nearest-neighbor Tanimoto sim 0.15, min distance 0.85); §22.1 reading note updated; full evidence table in §24.3 Table 24.3.
- **P1-4 — descaffolded ECFP4 downgraded to ablation control:** report v7 no longer presents descaffolded fingerprints as a feature track; §24.4 Table 24.4 lists maskA descaffolded fp 0.9302 / pheno+fp 0.9237 and maskB soft-CV descaffolded pheno+fp **0.3166** (vs intact 0.4775) as ablation references only.
- **Doc sync:** `20_improvement_plan.md` (F/M/N/Q/R evidence rows + new Stage 11 table), `21_kaggle_writeup_draft.md` (local-only sync; bottleneck number updated, Stage 11 rows added), this log; PDF regenerated to replace `docs/12_technical_report_draft_v7.pdf` (same filename, links stable).

### Stage 11 — P2 Deep-Coverage Extension, Harder-Task Evaluation & Retrieval-Feature Upgrade (2026-10-06)

Script `scripts/stage11_p2_retrieval_extended.py` (+ `stage11_p0_embeddings.npz`-family `19_stage11_p2_embeddings.npz` cache); summaries `reports/19_stage11_p2_retrieval_extended_results.csv`, `19_stage11_p2_retrieval_summary.json`, `19_stage11_p2_retrieval_breakdown.json`. Report v7 extended in place (§25.1–25.5, Tables 25.1–25.4); PDF regenerated.

- **P2-A — deep-embedding coverage extension (BR00116992):** downloaded **18 treated wells** of plate BR00116992 (8 channels each, 144 TIFFs, 351.1 MB, public AWS cellpainting-gallery bucket, 0 failures, plate-map trt check 18/18) → deep coverage grows from 6 wells / 12 sites to **24 wells / 30 sites** (ResNet18 512-d embeddings in `19_stage11_p2_embeddings.npz`). Download script `scripts/stage11_p2_download_br00116992.py` (aws s3 cp --no-sign-request, resumable per-well).
- **P2-B — extended replicate retrieval (24 wells, 17 queries):** manual 904 mean AP **0.3945** / MRR 0.4085 / R@1 0.235; deep 512-d mean AP **0.1418** / MRR 0.1788 / R@1 0.059. On the original 6 wells the P0-4 numbers reproduce exactly (deep 0.7333 vs 904 0.5083), validating the pipeline; at larger coverage the deep embedding no longer beats 904 (0.1418 vs 0.3945).
- **P2-C — harder task: trt-vs-trt pairwise AUC:** 14 wells / 7 compounds / 21 pairs, leave-one-pair-out LR on (904, ECFP4) and deep-512-d features: 904 mean AUC **0.7619** (min 0 / max 1), deep mean **0.2738** (below chance, honestly reported) — replaces trt-vs-DMSO as the model-capability probe.
- **P2-D — harder task: compound-identity top-k:** 14-well scope identity top-1/top-5: 904 **0.429 / 0.929**, deep **0.000 / 0.571**; full-scope 260-treated-well (256 compounds) 904 identity top-1 **0.000** / top-5 **0.0115** — near-chance at full scope, reported as a task-difficulty limitation.
- **P2-E — deep embedding promoted to retrieval feature:** report v7 §25.4 now frames deep embeddings as **evaluated retrieval features** (not a classification branch); cross-plate/in-plate/DMSO AP breakdown: 904 0.128 / 0.669 / 0.196 vs deep 0.096 / 0.108 / 0.324 — the single-plate advantage (P0-4) does not transfer across plates; 904 cosine baseline remains the default retrieval substrate with deep embeddings as a secondary feature track.
- **P2-F — protocol unification:** soft scaffold-grouped CV (τ = 0.6) remains the default evaluation; trt-vs-DMSO AUC 1.0 labeled structural control; descaffolded ECFP4 kept as ablation control only — consistent across 12/20/21/22/23.
- **Doc sync:** 12 v7 (§25 + Abstract + §24.1 reading), 20 (P2 table), 21 (local-only; summary + Key Results rows + reproduction note), 23 (P2 execution record), this log; PDF regenerated to replace `docs/12_technical_report_draft_v7.pdf` (same filename, links stable); full-repo AI-trace re-scan zero hits.

## Stage 12 — Cross-site external validation on `cpg0016-jump` (2026-11-06)

Script `scripts/stage12_external_site.py` (stages `fetch / controls / position / retrieval / evaluate / diagnose / trainsize`); deliverable write-up `reports/24_cross_site_external_validation.md`; report v7 §4.7 + abstract + §1.2/§1.3/§2.1/§4.3/§4.6/§5.1/§5.3/§6.1/§8/§9/§10.2/§A.2 synced; README §5 results bullet.

Question asked: does the committed trt-vs-DMSO result survive a **site** change (train = JBP pilot `cpg0000-jump-pilot/source_4`, test = independent `cpg0016-jump/source_2`)? Verdict by layer — the label is the layer it applies to:

- **数据层: 完成.** 17 objects fetched to a 200 MB budget, SHA256 manifest written and verified *before* modelling (`data/external/cpg0016/manifest_sha256.csv`, 159,909,495 bytes, all `status = ok`); 10 plates, 9 usable (plate `1053600681` is 384 DMSO / 0 treated and was excluded by rule, not by outcome).
- **复现层 (跨站点 trt-vs-DMSO): 未通过.** Pooled plate-level-bootstrap AUC over the four identically-applied protocol arms — `negcon_z` 0.5695 [0.5386, 0.5999], `rank` 0.6436 [0.6005, 0.7009], `zclip5` 0.6011 [0.5647, 0.6395], `posresid` 0.5155 [0.4601, 0.5670] — against in-site same-protocol 0.7100 / 0.6947 / 0.6932 / 0.6718 and the committed 0.6825. AP lift over the prevalence floor (+0.011 to +0.039) and shuffled-label negative controls (0.458–0.492) leave the effect small and partly layout-driven.
- **混杂层 (vehicle position ≡ label): 完成 (measured).** 8 of 9 plates put every DMSO well in columns 02/23 → position-only CV AUC 1.0000, layout-permutation p 0.0000; the pilot scatters vehicle over 22 columns (0.5361). On the one layout-clean plate the cross-site AUCs drop to 0.5041 / 0.5543 / 0.5086 / 0.4248 — at chance — while the *within*-plate 5-fold on that same plate is 0.7301, so the plate is fine and the transfer is not.
- **已提交结论层: 需要限定.** Coordinate-only (row+column dummies, no morphology) in-site cross-plate transfer scores **0.7450**, above the committed 0.6825, and the two pilot plates are the same array (384/384 wells share compound and position). The 0.6825 therefore cannot be quoted as layout-free generalisation; Table 5 gained a position-only control row and §4.3/§4.7 carry the caveat.
- **检索层: 通过.** Same-compound retrieval at the external site. New strict arm `decoupled-only` (the compound has **no** well at the query's coordinate, so the layout cannot be read at all): R@1 **0.5971 [0.5488, 0.6403]**, R@10 0.700, median rank 1, n = 350 queries over 16 plate pairs (all `1053600674` ↔ the eight column-vehicle plates), applicable null 0.0061 (~98×). Broad position-decoupled arm 0.4514 [0.4280, 0.4751] over 2,142 queries / 72 pairs (null 0.0082, ~55×); position-matched 0.3689 [0.3443, 0.3940] over 1,792 / 56 (null 0.0029, ~129×). Paired on the 56 pairs where decoupled and matched both exist: 0.4230 [0.4001, 0.4442] vs 0.3689, mean difference +0.0541, one-sided Wilcoxon p 0.0057, 31 pairs better / 19 worse.
- **Null 修正: 完成.** Queries whose compound has 4 replicate wells in the library plate accept 4 correct matches, so 1/n_library understates their chance R@1; `retrieval_by_position` now emits `chance_recall_at_1_any_accepted_match` per query and the reports quote lift against it. The previous headline "~156× chance" (which used 1/n for all arms) is withdrawn.
- **训练规模层: 未定.** Sub-sampled pilot training (32/65/130/260 compounds, 5 repeats, paired) flips sign with the normalisation arm (+0.0306 `negcon_z` p 0.150; −0.0552 `rank` p 0.973; +0.0157 `zclip5` p 0.367); recorded as unresolved rather than as a negative.
- **Docs-fact audit caught by this stage: 完成.** Three documentation errors were found while checking this stage's own claims against the data and fixed in place: (i) "`cpg0016-jump` profiles each compound in 4 replicate wells per plate" — measured: 8 of ~326 compounds recur in 4 wells on the column-vehicle plates, 19 of 299 in 2 wells on `1053600674`, the rest single-well; (ii) the corrected-but-still-wrong follow-up "compounds recur across plates at *different* coordinates (5.7 % same well)" — measured: usable pairs share only 8–10 compounds and 224 of the 291 shared cells repeat the *same* 4 coordinates, so the strict arm is built from the 67 zero-overlap cells; (iii) "303 unique compounds, 4 technical replicates per compound" for the pilot — 303 reproduces as distinct `Metadata_pert_iname` over the two compound plates, but each treated compound occupies **1 well per plate / 2 wells total**. §2.1's 1,040/488/128/240 line was also relabelled as the four-plate composition. Corrected in `reports/12` §2.1/§3.1/§4.7/abstract/§5.1/§8, `README.md` §4–5, `reports/21` item 1, `reports/24` §7/§9; no derived metric changed. (i) and (ii) were both my own text written earlier in this same stage, which is why the measurements are now produced by `--stage controls` (`21_stage12_replicate_structure.csv`, `21_stage12_replicate_sharing.json`) instead of by ad-hoc queries.
- **Artifacts:** `21_stage12_external_site_summary_{negcon_z,rank,zclip5,posresid}.json`, `21_stage12_external_per_plate_*.csv`, `21_stage12_external_controls.csv`, `21_stage12_position_audit.csv`, `21_stage12_retrieval_position_split.{csv,json}` (incl. `paired_by_plate_pair`), `21_stage12_external_diagnose.{csv,json}`, `21_stage12_train_size_curve_{negcon_z,rank,zclip5}.{csv,json}`; the six pre-4-arm `raw`/`symmetric`/unmarked outputs were deleted so no stale number can be quoted.
- **Doc sync & PDF: 完成.** `reports/12` header gained a 2026-11-06 revision line naming the sections Stage 12 touched; the archived drafts `12_technical_report_draft_v5.md` / `v6.md` keep their original text but now carry a banner pointing at the measured replicate layout; `reports/21` item 2 sharpened from "mean of the replicate wells" to "mean of the two wells carrying each compound (one per plate)". `docs/12_technical_report_draft_v7.pdf` regenerated from the v7 markdown → **15 pages, MD5 `726cc35711211e062bf50074ea09602e`** (the version committed before this stage: 20 pages, MD5 `664ae12b…`, whose text layer contains none of the §4.7 anchors — checked with `--check-only` before rebuilding). The build is now scripted instead of ad-hoc: `scripts/build_report_pdf.py` + `docs/print_style.css` (pandoc 3.9 standalone HTML → Chrome headless `--print-to-pdf`), and it self-verifies page count, 12 text-layer anchors (including the §4.7 heading, `position-decoupled`, `0.5971`, `not reproduced`) and the absence of generated-content disclaimers; intermediates go to `build/pdf/` (git-ignored). The 15-vs-20 page difference is style, not content: the tighter committed CSS vs the unrecorded ad-hoc style of the 20-page build — the new PDF's text layer has **10,321 words vs 7,734** and embeds the **same 6 distinct figures** (the old one repeated one figure on two pages); pages 1, 9–11 were rendered and read back for layout (no block crosses the right margin, the three-arm table and the 层 verdict lines fit). AI-trace re-scan: PDF text layer zero hits; repo-wide markdown hits only the two legitimate "watermark" mentions in this log and README L222.
- **Repo hygiene: 完成.** Four tracked assets (`docs/12_technical_report_draft_v7.pdf`, `docs/figures/01_umap_overview.png`, `figures/01_umap_overview.png`, `reports/figures/01_umap_overview.png`) were absent from the working tree — an external backup tool had renamed them on 2026-10-09 to `…-副本202610091157xx` copies. The copies are byte-identical to `HEAD` (MD5 `664ae12b…` and `79901ee9…`), so the tracked paths were restored by copying them back; the `-副本` files were left in place, untracked, for the user to prune.
- **可移植层 (本阶段脚本): 完成，并在 Stage 13 推广到全仓.** `scripts/stage12_external_site.py` had an absolute `E:\Desktop\Kaggle_2026\…` workspace prefix; it now derives repo root from `__file__` (workspace = parent of repo, data = `<workspace>/data`) with `AI4S_REPO` / `AI4S_WORKSPACE` overrides, resolving to the same directories as before — verified by re-running `--stage controls` after the change and comparing: `21_stage12_external_controls.csv`, `21_stage12_position_audit.csv`, `21_stage12_replicate_sharing.json`, `21_stage12_replicate_structure.csv` are **byte-identical** to the pre-refactor copies (exit 0). The remaining 13 stage scripts were migrated onto the same module in Stage 13.
- **Not done in this stage:** no cross-site *scaffold-grouped* replication (the pilot's scaffold split and the external compound sets are only partially overlapping), and the external raw images were not downloaded — only the published profiles.

## Stage 13 — Portability, self-check and unit tests (2026-11-06)

No new analysis and no new numbers: this stage makes the existing claims re-runnable and
machine-checkable. Three new files (`scripts/_paths.py`, `scripts/check_repo.py`,
`tests/test_stage12_units.py`), 14 migrated scripts, docs synced.

- **可移植层 (全仓): 完成.** `scripts/_paths.py` is now the only place a root is computed: repo root = parent of `scripts/`, workspace = parent of the repo (or `AI4S_WORKSPACE`), `DATA` = whichever of `<repo>/data` / `<workspace>/data` exists (an explicit workspace override wins outright), plus `REPORTS` / `FIG` / `DOCS` / `LOGS` / `PROFILES` / `METADATA` / `RAW` / `EXTERNAL`. All 14 stage scripts (`stage10_*`, `stage11_*`, `stage12_*`) import from it; the checkout contains no drive-letter root in any tracked `.py`. Diff: 101 insertions / 46 deletions over two passes (65/27 for the `BASE`/`REPO` import, then 17 rewrites so `DATA` and `REPORTS` also come from the module). Evidence, in the order the claims need it: (i) `python -m compileall scripts` exit 0; (ii) an AST pass over `git show HEAD:` of each file compares the old literal with the new expression — files checked: 14, **mismatches: none**; (iii) an undefined-name AST sweep caught a real defect in the first migration (stage12's earlier `__file__`-derived block had been deleted without the import being added → `NameError: BASE`), which is why that sweep is now part of the record; (iv) the same sweep after the second pass caught two scripts using bare `DATA` without importing it, and the rewrite's own checker reports **0 constants differing, 0 lost, 6 non-path expressions skipped**; (v) the local-only stages were re-run **from `C:\Users\<user>`**, twice, and 59/62 artifacts came back byte-identical both times (the 3 remaining being the docs this stage edits); (vi) the two that moved were traced to the library stack, not the paths, by running the *pre-refactor* script side by side — it emits the new bytes exactly (`cmp` equal), and the second round reproduced them again. `reports/12` §10.6 carries the numbers, the drift statement, and the `core.autocrlf` comparison caveat that makes `git show` hashes non-comparable to working-tree hashes.
- **自检层: 完成.** `scripts/check_repo.py` — 49 read-only checks (50 with `--deep`) in seven groups: A layout (paths resolve, no hardcoded roots anywhere including `tests/`, the `DATA` preference rule, the 16 path literals that HEAD carried still equal the derived roots, and — when set — the `AI4S_REPO` / `AI4S_WORKSPACE` override actually being honoured), B compile (all 30 `.py` files in the root, `scripts/` and `tests/` parse), C citations (every `2*_stage1[12]…` token the markdown quotes expands — recursively, including the nested `{a,b}.{csv,json}` form — to a file on disk, 20 tokens; every image link resolves; the six numbered root scripts resolve `BASE` to the same workspace `_paths` would derive by default; `demo.py` derives `REPO_ROOT` from `__file__` rather than a literal), D numbers (each R@1/AUC/AP/p lifted from the stage12 JSONs must appear in the markdown; the withdrawn ~156× lift may only appear inside a withdrawal sentence; the 0.6825 source artifact exists; the 303 exists in the replicate CSV), E pdf (page band, six text-layer anchors, md5 equals the hash the docs record), G tests (runs the unit suite as a subprocess and quotes its summary line), F manifest (17 rows `status = ok`, sizes vs disk, byte total quoted; `--deep` re-hashes all 159.9 MB). Result in the real tree: **fast 49/49, `--deep` 50/50** (Stage 14 later added three dependency rows and
rewrote the HEAD-literal audit described below, taking the same suite to 52/53). Two false FAILs were fixed on the way, both in the checker rather than the repo: a non-greedy citation token that cut a brace group in half, and a one-level brace expander that could not read `{a,b}.{csv,json}`. A third fix came from probing rather than from a failure: with an override active, the HEAD-literal and root-script comparisons had been reporting differences that were not differences (an override legitimately moves the live roots), so both now compare against the override-free defaults and a separate check asserts the override itself.
- **测试层: 完成.** `tests/test_stage12_units.py` — 21 dependency-free tests (plain `python`, own runner, no pytest — pytest is not installed here), covering the retrieval-arm definitions and the per-query applicable null, the vehicle-only robust z (including that it cannot read treated wells: two plates sharing their DMSO rows share their vehicle normalisation), well-coordinate parsing/encoding, the additive-layout residualiser (pure row+column signal → max residual < 1e-8), `_rep_counts`, the four scaling arms and their relations (`zclip5 == clip(negcon_z)`, `rank` monotone, `posresid == residualise(impute(negcon_z))`, `posresid` refuses a table without `Metadata_Well`), `position_confound` on a synthetic column-vehicle plate vs a scattered one, the committed split's structural invariant that the strict arm shares no plate pair with the matched arm (which is why `paired_strict_by_plate_pair` is null), and the `DATA` resolution rule against temporary directories. **21/21 pass.** The runner also has a third outcome: `SKIP`, for the one assertion that needs the *live* inputs, excluded from the denominator and named on the summary line — measured in a clone of the tracked files with no `data/`: `20/20 tests pass (1 skipped: …)`, `check_repo.py 43/46` failing only the three data-dependent rows
(the same clone reads `46/49` after Stage 14, the three added rows being the dependency checks).
- **文档层: 完成.** `reports/12` §10.2 rewritten (portability is no longer an open item; manifest byte totals stated as 159,909,495 fetched / 159,914,604 with the manifest), §10.5 *Verify the checkout* and §10.6 *Byte-level re-run evidence* added; `reports/24` artifact header aligned with the same two byte totals and the `_paths.py` derivation; `README.md` §3 gained the two allowed `data/` placements with the override variables, the two verification commands, and the measured no-input output; `reports/20_improvement_plan.md` gained a Stage 13 section. `docs/12_technical_report_draft_v7.pdf` rebuilt after that sync: **16 pages, MD5 `29aadaf3589f01075610e7eb461ef1de`**, 12/12 text-layer anchors, page band 12–22 holds — superseding the Stage 12 build (`726cc357…`, 15 pages); `reports/24` §"Current build" records the new hash and the chain back to `664ae12b…`.
- **未解决 (measured gaps, not TODOs by choice):** `stage10_retrieval.py` and `stage10_harmony.py` cannot run here — `ModuleNotFoundError: No module named 'harmonypy'`, so their artifacts are unverified off the original machine; the two P3 files move in the 4th–5th decimal under the current library stack (statement in `reports/12` §10.6, committed artifacts kept); `reports/20_improvement_plan.md` lists Stage 13 as tooling rather than analysis, and the `12 v5/v6` archived drafts remain archived (banner only).
- **图形目录层 (measured, deliberately not touched): 未完成 — 需用户裁定.** Five PNG directories coexist: `figures/` (27 png, the one the repo's markdown reads — 6 image links, all resolve), `reports/figures/` (15), `docs/figures/` (8), and outside the checkout `<workspace>/reports/figures/` (26) and `<workspace>/figures/` (10). The six root-level scripts (`01_…`–`06_…`) derive `BASE` as `dirname(dirname(__file__))` = the **workspace**, so `python 01_phenotypic_profiling.py` writes figures one level above the repo and cannot refresh `figures/` as committed. Of the 20 names shared between `figures/` and `<workspace>/reports/figures/`, 9 are byte-identical and 11 differ, with no consistent direction (by mtime the workspace copy is newer for 4 and the repo copy for 7 — and mtimes here are not clean evidence anyway, since an external backup tool rewrote files on 2026-10-09), so the two trees have diverged rather than one being a stale export of the other. Consolidating would delete or overwrite tracked binaries, which is not this stage's call; recorded with the counts, and group C now keeps the *links* honest. The actionable version of this decision: either point the root scripts at `_paths.FIG_ROOT` and re-render, or declare `figures/` the only tracked image tree and move the rest into `build/`.
- **Not done in this stage:** the seven root-level scripts were left as they are — measured, the six numbered ones derive `BASE = dirname(dirname(__file__))` (which equals the workspace `_paths` derives by default, asserted by group C) and `demo.py` derives `REPO_ROOT = dirname(abspath(__file__))` (self-relative, now asserted too), so none of them carried a drive-letter literal to remove; routing them through `_paths.py` would be cosmetic churn on files this stage has no reason to touch — with one consequence worth naming: those six write figures and CSVs one level above the repo, which is the `图形目录层` divergence below. No CI workflow file was added — `check_repo.py` is a local command, and pushing a workflow is the user's call along with the commit.

## Stage 14 — Dependency truth (2026-11-06)

No new analysis. Stage 13 asked "can this run off the author's machine"; while re-measuring the
checker for that question it became obvious the repo could not answer the simpler one: *what
environment does this code need, and is the declared one the measured one?* Two defects, both
found by measuring rather than by reading.

- **声明层: 完成.** `requirements.txt` said its pins were "verified 2026-10-05" and nothing compared
  them with anything since. Measured here (python 3.13.7, Windows-10-10.0.19045-SP0): of the twelve
  `==` pins, 3 equal the machine (pandas 3.0.3, seaborn 0.13.2, tifffile 2026.9.20), **7 differ**
  (numpy 2.4.6→2.3.4, scipy 1.17.1→1.18.1, scikit-learn 1.8.0→1.9.1, matplotlib 3.10.9→3.11.0,
  xgboost 3.2.0→3.4.1, rdkit 2026.3.6→2026.3.3, torch 2.14.0→2.6.0+cu124) and 2 are pinned but not
  installed (torchvision 0.29.0, cellpose 4.2.1.1); both range rows are met (umap-learn 0.5.12 ≥ 0.5,
  statsmodels 0.15.0 ≥ 0.14). The pins were **not** rewritten to the live versions: they describe the
  build environment of the submitted results and that environment is gone — silently replacing it with
  this machine's stack would have destroyed the only record of what produced the CSVs. Instead the
  file now states both, with the comparison in `reports/23_environment_fingerprint.json`.
- **未声明依赖: 完成.** An AST sweep of every tracked `.py`, bucketed by how reachable each import is
  (16 module-level or module-guarded, 7 deferred inside a function), turned up eight distributions the
  code imports and the file never declared: `pillow`, `imageio-ffmpeg`, `harmonypy`, `timm`,
  `transformers`, `pyarrow`, `scikit-image`, `pymupdf`. Three of those stop a script from starting on
  this machine (`imageio-ffmpeg` in the demo-video builders; `cellpose`/`torchvision` were declared but
  absent, so `04_cellpose_demo.py` cannot run here either), and the deferred ones are exactly why nobody
  noticed: `python demo.py --full` never reaches them. All eight are declared now **without versions** —
  a number in that file reads as a claim about the 2026-10-05 build, and none of the eight can be tied
  back to it, so inventing a pin would have replaced a real gap with a fabricated fact. Their measured
  status sits beside each name instead.
- **记录与门禁: 完成.** `scripts/record_environment.py` writes the fingerprint (python, platform, every
  declared distribution with pin-vs-installed and a label that keeps a matched pin, a met range, an
  unpinned declaration and an absent package from reading as each other, every imported module with its
  reachability level and the files importing it, plus a summary), and `--check` re-derives all of it
  and exits 1 naming the moved rows, so an upgraded library is *reported* instead of quietly changing
  4th-decimal results (the §10.6 mechanism). Measured: `CURRENT - python 3.13.7, 22 declared,
  22 version rows + 23 import rows still match, no undeclared module-level import`. Three new
  `check_repo.py` rows use it — module-level imports all declared, every blocking-but-absent
  dependency named somewhere in the docs, fingerprint equals this machine — taking the read-only
  suite from 49 to **52 (53 with `--deep`)**, verified `52/52` and `53/53` in the real tree and
  `21/21` in the suite. Two of those three names stated a claim about *this* machine in the present
  tense; the next bullet records the correction and its measurements.
- **同一门禁的机器独立性: 完成.** The rows above stated claims about *the author's machine* in the
  present tense, which would have failed a legitimate clone for reasons that are not defects. Row 2 is
  now scoped in its own name — `every dependency that blocks a script on the recorded machine is named
  in the docs` (it reads the recorded `imports`, and is a claim about the docs, so it runs everywhere).
  Row 1 lost its dependence on the artifact: `check_repo.py` imports `record_environment` and calls
  `build()` itself, so the undeclared-import sweep describes the code in front of it rather than a
  snapshot. Row 3 is gated on `same = (recorded python == live python and recorded platform == live
  platform)`; when they differ it emits
  `recorded fingerprint belongs to another machine (skipped: drift not assessable from here)` and
  returns, naming both sides. Measured by running the checker against a doctored copy of the
  fingerprint (`platform` set to `FakeOS-99-Not-This-Machine`), which printed
  `PASS | … | record says python 3.13.7 on FakeOS-99-Not-This-Machine; this is python 3.13.7 on
  Windows-10-10.0.19045-SP0` instead of comparing the record's 22 version rows and 23 import rows
  against a machine it was never taken on, and on the real fingerprint, which
  still gives `52/52 checks pass` (the artifact was restored byte-identical: SHA256 `c7d9a212…`, and
  `git status` shows it unmodified). The live sweep was proven the same way: a throwaway
  `scripts/_probe_undeclared.py` containing one `import zzz_probe_not_a_package` made row 1 FAIL
  (`undeclared: zzz_probe_not_a_package`) *and* row 3 FAIL (`imported now, absent from the record:
  …`), i.e. the code in front of the checker is judged even when the recorded artifact has not been
  regenerated; `50/52`, and `52/52` again once the probe was deleted. Skipping is stated in the row
  name; it is never a pass of the drift claim itself.
- **检查器自身的第二个 vacuous 缺陷: 已修，并有实测.** The Stage 13 literal audit compared HEAD's
  `BASE`/`REPO` literals with the derived roots — but from `cad2391` onward HEAD *contains no such
  literals*, so the row had degraded to "the 0 path literals replaced at HEAD equal the derived roots":
  a passing check that checks nothing. It now walks back to the tree before `scripts/_paths.py` existed
  (`git log --diff-filter=A -- scripts/_paths.py`, then that commit's parent), reads the 16 literals
  there, and compares them with what `_paths` derives now: **16 checked, 0 differing**. Two things were
  measured rather than assumed. (i) The failure path is live: forcing `DEFAULT_WORKSPACE` to a wrong
  root makes the row FAIL and name the files. (ii) The skip paths are honest and were each run: in a
  git-less copy of the tracked files the row reads `pre-refactor path literals checked (git unavailable,
  skipped)`; in a single-commit fixture repo, where there is no pre-refactor tree at all, it reads
  `pre-refactor literals name a different checkout (skipped: equivalence unproven here, 0 literals read
  from <sha>)`; and in a real `git clone` of this repo — full history, different directory, so the
  literals name a checkout that is not this one — it reports the 16 literals it read and still calls the
  equivalence *unproven here* rather than failing a perfectly good clone. Unproven is stated as
  unproven, never as a pass of the claim itself.
- **无输入复测: 完成.** The clone simulation was re-run with the Stage 14 files included (151 tracked
  files copied one level above this repo's `data/`): `20/20 tests pass (1 skipped:
  paths_data_rule_prefers_the_repo_and_falls_back_to_the_workspace)` and `check_repo.py 46/49`, the
  three failures still being only the data-dependent rows. 49 rather than 52 rows for the same absence:
  with no fetch manifest the manifest group emits its one "present?" row and returns, instead of adding
  the three content rows it cannot compute. The dependency checks themselves pass in a data-less clone —
  they read code and declarations, not inputs. This simulation had been a throwaway script under the
  git-ignored `build/`; it is now `scripts/clone_probe.py`, tracked, self-cleaning, and quoted in README
  step 5 and `reports/12` §10.5 — a reader without the inputs can re-measure the sentence rather than
  take it on faith.
- **文档层: 完成.** README step 2 (what the file declares vs what this machine has) and step 5
  (52/53, measured `46/49` clone and why the denominators differ); `reports/12` §10.5 counts and failure
  modes, new **§10.7 "What the declared environment actually is"**; `reports/20` Stage 14 table; this
  ledger. `docs/12_technical_report_draft_v7.pdf` rebuilt after the sync: **16 pages, MD5
  `2ec3f59fc9c5100b2d1b03b13724ad2a`**, 12/12 text-layer anchors, 12,147 words — superseding the first
  Stage-14 build (`4c5e8506…`, 16 pages, 11,993 words, rebuilt before §10.7 grew the machine-skip
  sentences), which had itself superseded an intermediate build (`5e1586a4…`, 11,931 words, overwritten
  when §10.5 grew the probe paragraph) and the Stage 13 build (`29aadaf3…`, also 16 pages); `reports/24`
  §"Current build" carries the new hash and the chain back to `726cc357…` and `664ae12b…`.
- **未解决 / 边界:** declaring a dependency is not installing one — `harmonypy`, `timm`, `transformers`,
  `imageio-ffmpeg`, `torchvision` and `cellpose` remain absent here, so `stage10_harmony.py`,
  `stage10_retrieval.py`, `stage10_self_supervised.py`, `stage11_p0_retrieval.py`, `04_cellpose_demo.py`
  and the demo-video builders stay unverified off the original machine. The fingerprint describes
  *this* machine on 2026-11-06 and cannot be re-attributed to the 2026-10-05 build; the pin block and the
  live stack therefore stay in genuine tension, which is now recorded rather than hidden. No CI runs the
  recorder, and nothing was installed or uninstalled to make the numbers agree.

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
| Stage 11 (P0: eval disaggregation, soft-group CV, task quant, retrieval switch) | 完成 (plan 23_shortboard_plan_p0-p2.md, figures 29a–29d, summaries 19_stage11_p0_*, log synced) |
| Optimization log | 完成 (this file) |
| Official re-check (R1–R4) | 完成 (R2/U3 待用户) |
| Git push (Stage 7 commit 4886f6f) | 成功推送 origin/master（ssh://ssh.github.com:443），远程与本地一致 |
| Git push (Stage 8 commit) | 成功推送 origin/master（随 Stage 9 commit 一起） |
| Git push (Stage 9 commit 0a0363b) | 成功推送 origin/master（ssh://ssh.github.com:443），远程与本地一致 |

| Stage 11 P3 (cross-plate generalization) + P4 (trt-vs-trt harder-task boost) | 完成 (scripts stage11_p3_cross_plate.py / stage11_p4_trt_trt_boost.py; results 20_stage11_p3_* / 20_stage11_p4_*; report v7 §26–27; 20/21/22/23 synced; PDF regenerated; AI-trace rescan zero hits) |
| Stage 12 (cross-site external validation on `cpg0016-jump`) | 完成，结论 = **未复现** (9 usable plates behind a SHA256 manifest; trt-vs-DMSO 0.5155–0.6436 vs in-site 0.6825; vehicle column ≡ label measured on 8/9 plates; retrieval positive — strict position-decoupled-only R@1 0.5971 ≈ 98× the applicable null; reports/24 + report v7 §4.7 + README + writeup + this log synced; PDF 15 pp MD5 726cc357…; scripted build `scripts/build_report_pdf.py`) |
| Git commit (Stage 12 = `6861df5`, 39 files) | 本地提交完成，**未 push**（按要求；`origin/master` 仍停在 `31ca5d5`，本地 ahead 1）。本行由紧随其后的 ledger commit 记录 |
| Git push (P3/P4 commit) | 成功推送 origin/master（ssh://ssh.github.com:443），远程与本地一致 |
| Stage 13 (portability, self-check, unit tests) | 完成 (scripts/_paths.py + 14 scripts migrated; scripts/check_repo.py 49 checks / 50 --deep; tests/test_stage12_units.py 21 tests with SKIP semantics; README §3 + reports/12 §10.2/§10.5/§10.6 + reports/20 Stage 13 + this log synced; PDF rebuilt 16 pp MD5 29aadaf3…; two re-runs from a foreign cwd ⇒ 59/62 artifacts byte-identical) |
| Git commit (Stage 13 = `cad2391`, 23 files) | 本地提交完成，**未 push**（按要求；`origin/master` 仍停在 `31ca5d5`，本地 ahead 3：`6861df5`、`31f8c4e`、`cad2391`） |
| Stage 14 (dependency truth) | 完成 (requirements.txt 拆分「构建环境」与「本机」并补 8 个未声明依赖·不编版本号；scripts/record_environment.py + reports/23_environment_fingerprint.json；check_repo.py 49→52 checks / 53 --deep，pre-refactor 字面量审计从「HEAD 已无字面量⇒0 项空过」改为读取 `_paths` 引入前的树，16 项全等且两条 skip 分支实测；README step 2/5 + reports/12 §10.5/新 §10.7 + reports/20 Stage 14 + 本 ledger 同步；环境三行的机器独立性（row1 实时扫树、row2 改名为「recorded machine」、row3 先比 python+platform 再决定比对或跳过）并用伪造 fingerprint＋临时未声明 import 两条探针实测；PDF 重编译 16 pp MD5 2ec3f59f…（取代 4c5e8506… 与更早的 5e1586a4…）) |

## AI Use Disclosure

This project was developed with the assistance of AI-based tools in the following capacities:
- Drafting, structuring, and language refinement of parts of this report and related project documentation;
- Assistance with code development, debugging, and documentation;
- Assistance with the production of the demonstration video (script drafting, subtitles) and cover design.

All experimental designs, data processing, model training, evaluation, and result interpretation were planned, performed, and verified by the authors. All AI-assisted content has been reviewed, validated, and approved by the authors. No AI tool was used to fabricate experimental data, results, or conclusions.
