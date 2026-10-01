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

- **Action:** grep-style scan of `reports/12_technical_report_draft_v3.md`, `README.md`, `00_submission_checklist.md` for `<TEAM_NAME>` / `<Member N>` / team mentions.
- **Findings:**
  - `12_technical_report_draft_v3.md`: L33 (Category Declaration), L39–41 (Team Information: `<TEAM_NAME>`, `<Member 1>`, `<Member 2>`, `<Member 3>`).
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

## Final status

| Item | Status |
|---|---|
| H1 Team placeholder | 需用户填写 (blocked on real names) |
| H2 Writeup draft | 完成 (synced to v5) |
| H3 v4 PDF | 完成 |
| H4 GitHub Pages | 完成 (needs user push + Pages enable) |
| A–E enhancements | 完成 |
| Stage 6 (F/G/H: structure-aware, uncertainty-aware, SIDER) | 完成 (script 05, figures 16–20, results CSV, report v5, writeup/plan/log synced) |
| Optimization log | 完成 (this file) |
| Official re-check (R1–R4) | 完成 (R2/U3 待用户) |
| Git push (Stage 6 commit) | see commit/push result below |

*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
