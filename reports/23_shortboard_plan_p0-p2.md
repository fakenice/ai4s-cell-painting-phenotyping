---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 1b7b0544872f18baedbb33526952b8c3_2380b71bc12111f197eb525400393706
    ReservedCode1: TdX9EA75VXGREjEF9O3WiC624iRzNv0V5UbimOyKV9Ot+S/uZFVdQbZmHh+w6YhRhz6THDDxhxXmLvvnWlocKDzUkItb/hK1mguKHpsLiakFQwHJHiAsii5ZJ1+SqH5J0o/oKyj4bMHEQv+AxBnSoQ90ClONDAddgl5CYPJOYtd5TChr7axMGlKcacA=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 1b7b0544872f18baedbb33526952b8c3_2380b71bc12111f197eb525400393706
    ReservedCode2: TdX9EA75VXGREjEF9O3WiC624iRzNv0V5UbimOyKV9Ot+S/uZFVdQbZmHh+w6YhRhz6THDDxhxXmLvvnWlocKDzUkItb/hK1mguKHpsLiakFQwHJHiAsii5ZJ1+SqH5J0o/oKyj4bMHEQv+AxBnSoQ90ClONDAddgl5CYPJOYtd5TChr7axMGlKcacA=
---



# AI4S Submission — Shortboard-Gap Closure Plan (P0–P2)

**Project:** Morphological Phenotypic Profiling of Chemical Perturbations with JUMP-Cell Painting Data
**Competition:** AI4S Open Innovation: AI for Life Science (Kaggle Hackathon)
**Plan file:** `reports/23_shortboard_plan_p0-p2.md`
**Date:** 2026-10-06
**Status:** P0 executed (4/4 experiments); P1/P2 scoped, pending
**Companion log:** `reports/22_optimization_log.md` (P0 entries appended)

---

## 1. Background: three identified shortboards

Prior stages (7–10) established the baseline pipeline (CellProfiler 904 features + ECFP4 + XGBoost; deep embeddings; retrieval & target enrichment). Review of the final results surfaced three recurring weaknesses that limit both the credibility and the ceiling of the submission:

| # | Shortboard | Symptom / evidence |
|---|---|---|
| S1 | **Evaluation granularity & leakage risk** | `maskA` trt-vs-DMSO hits AUC 1.0 mostly from fingerprint dominance; `maskB` scaffold-grouped CV sits near 0.47–0.53; within-scaffold vs cross-scaffold contributions are never decomposed, so optimistic in-fold structure and pessimistic generalization are conflated. |
| S2 | **Task-difficulty not quantified** | trt-vs-DMSO is trivially separable by ECFP4 (identity/structural gap), while the phenotype signal is near-random (single-cell CNN test AUC 0.0955; deep-embedding LOO AUC ≈ 0.33–0.78 on 6 wells). Without a quantified fingerprint-distance baseline, "AUC 1.0" can be misread as phenotypic power. |
| S3 | **Single retrieval track (manual 904)** | Replicate-retrieval AP on 648 wells is only 0.2451 (chance 0.0401); the deep embeddings produced in Stage 8/10 were only evaluated by LR-LOO, never as retrieval features, leaving an obvious track switch untested. |

---

## 2. P0–P2 method matrix (做法 / 成本 / 预期收益 / 优先级)

| ID | Method (做法) | Cost (成本) | Expected gain (预期收益) | Priority |
|---|---|---|---|---|
| **P0-1a** | Decompose evaluation into within-scaffold vs cross-scaffold CV on `maskB` (pheno+fp vs pheno-only) | Low (reuse profiles + scaffolds) | Quantify optimism/generality split; decide whether 1.0-class results are fingerprint artifacts | **P0 (this round)** |
| **P0-1b** | Recompute ECFP4 after Bemis-Murcko scaffold removal; re-run CV on `maskA`/`maskB` | Low (RDKit descaffold + re-fingerprint) | Show how much of the fingerprint signal is scaffold-identity vs substituent structure | **P0 (this round)** |
| **P0-2** | Soft group CV: leave-out-by-Tanimoto-nearest (hard scaffold, soft τ=0.6/0.4, fp-cluster 0.5) | Low (pairwise Tanimoto matrix) | Robust estimate under structural similarity leakage; replace rigid scaffold groups | **P0 (this round)** |
| **P0-3** | Quantify task attributes: DMSO-vs-compound and compound-compound ECFP4 distance distributions (+ figure) | Low (fingerprints only) | Prove trt-vs-DMSO fingerprint separability; calibrate reporting | **P0 (this round)** |
| **P0-4** | Retrieval track switch: same cosine protocol on DINOv2/OpenPhenom/ResNet18 embeddings vs 904 (well- and site-level AP) | Medium (GPU embedding, cacheable) | Raise replicate-retrieval ceiling (0.2451 → target ≥0.6 well-level) | **P0 (this round)** |
| P1-1 | Adopt soft-group CV + within/cross decomposition as the default evaluation protocol in report/writeup | Low | Credibility; aligns all headline numbers with leakage-aware protocol | P1 |
| P1-2 | Add descaffolded ECFP4 as a feature channel (or as ablation control) in the final classifier | Low–Med | Cleaner interpretation of structure contribution | P1 |
| P1-3 | Promote deep embeddings into the classification pipeline (concatenate with 904; re-run maskA/maskB CV) | Med | Test whether vision self-supervision adds orthogonal signal beyond 904+fp | P1 |
| P1-4 | Verify retrieval track switch on full 648-well scope (not 6 wells) with ANN indexing | Med | Final head-to-head AP on the true retrieval task | P1 |
| P2-1 | Fine-tune DINOv2/OpenPhenom on JUMP-CP images (contrastive, plate-aware) for phenotype retrieval | High | Domain-tuned embeddings; biggest potential uplift but requires GPU time | P2 |
| P2-2 | Re-assess Harmony batch correction with the leakage-aware protocol (retrieval AP after correction was 0.0766) | Med | Decide definitively whether correction helps retrieval under proper evaluation | P2 |
| P2-3 | Cross-modal enrichment (image-embedding MOA pairs vs fingerprint pairs) as an additional known-target signal | Med–High | New evidence channel beyond ECFP4 AUROC 0.5611 | P2 |

---

## 3. P0 results (executed, real numbers)

All P0 experiments were executed on `E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science` with scripts under `scripts/stage11_p0_*.py`; summaries in `reports/19_stage11_p0_summary.json` / `19_stage11_p0_retrieval_summary.json`; figures 29a–29d.

### P0-1a — Within- vs cross-scaffold CV decomposition (`maskB`, compound-grouped)

CV groups by compound; predictions split into same-scaffold pairs (within) and different-scaffold pairs (cross).

| Feature set | Overall AUC | Within AUC (n=238) | Cross AUC (n=530) | Overall AP |
|---|---|---|---|---|
| pheno + fp | 0.4932 | 0.3100 | 0.7516 | 0.6367 |
| pheno-only | 0.3232 | 0.1004 | 0.6121 | 0.5492 |

**Reading:** cross-scaffold pairs are *easy* (0.75 AUC) mostly because fingerprint/scaffold structure leaks; within-scaffold pairs are *hard* (0.31 AUC) and phenotype alone barely separates them (0.10 AUC). The overall 0.49–0.52 AUC on maskB is therefore a mix of an easy structural regime and a genuinely hard phenotypic regime — exactly the decomposition that headline numbers previously hid.

### P0-1b — Descaffolded ECFP4 (Bemis-Murcko removal) CV comparison

303 compounds → 270 descaffolded (89.1%); scaffold groups at Tanimoto 0.5: 282.

| Task / CV | fp-orig | fp-descaffolded | pheno+fp-orig | pheno+fp-descaffolded |
|---|---|---|---|---|
| maskA trt-vs-DMSO (well OOF) | AUC 1.0000 / AP 1.0000 | AUC 0.9302 / AP 0.9823 / ACC 0.8951 | AUC 1.0000 / AP 1.0000 | AUC 0.9237 / AP 0.9818 / ACC 0.8657 |
| maskB scaffold-groupCV | AUC 0.3766 / AP 0.6166 | AUC 0.3732 / AP 0.6570 | AUC 0.4775 / AP 0.6299 | AUC 0.3166 / AP 0.5515 |

**Reading:** even after stripping the scaffold, trt-vs-DMSO stays nearly perfectly separable (0.93 AUC) — the residual signal is substituent-level structure, not scaffold identity; fingerprint dominance over phenotype is real, not a scaffold artifact. On maskB, descaffolding *hurts* pheno+fp (0.4775 → 0.3166 AUC), consistent with cross-scaffold generalization depending on scaffold information.

### P0-2 — Soft group CV (Tanimoto-nearest leave-out, `maskB`)

Leave-out groups defined by structural similarity thresholds instead of hard scaffold bins.

| Grouping | pheno+fp AUC | pheno+fp AP | pheno-only AUC | pheno-only AP |
|---|---|---|---|---|
| hard scaffold | 0.5258 | 0.6563 | 0.3153 | 0.5486 |
| soft τ = 0.6 | 0.5222 | 0.6545 | 0.3349 | 0.5559 |
| soft τ = 0.4 | 0.5192 | 0.6558 | 0.3170 | 0.5497 |
| fp-cluster 0.5 | 0.4775 | 0.6299 | 0.2854 | 0.5374 |

**Reading:** soft grouping is stable (τ 0.4–0.6 and hard scaffold agree within ~0.007 AUC), i.e. the maskB 0.49–0.53 range is robust to grouping definition; fp-cluster 0.5 is the most pessimistic. Pheno-only remains weak under every grouping (0.29–0.33 AUC).

### P0-3 — Task-attribute quantification: DMSO vs 303-compound ECFP4 distance

| Statistic | DMSO vs compounds (n=302 pairs) | Compound–compound (n=45,451 pairs) |
|---|---|---|
| mean distance | 0.9683 | 0.9013 |
| median | 0.9695 | 0.9048 |
| min / max | 0.85 / 1.00 | — |
| q10 / q90 | 0.9488 / 1.00 | 0.8478 / 0.9524 |

Mann-Whitney U p = 5.95e-148; DMSO nearest neighbor is 2,5-furandimethanol at Tanimoto similarity 0.15 (distance 0.85).

**Reading:** DMSO sits structurally far from every compound (min distance 0.85), so trt-vs-DMSO classification is fingerprint-trivially separable by construction — headline AUC 1.0 must be reported as structure-driven, not phenotype-driven.

### P0-4 — Retrieval track switch (deep embeddings vs manual 904)

Same cosine same-compound replicate-retrieval protocol; 904 recomputed on the same 6 wells (0.5083) to make the well-level comparison apples-to-apples (Stage-10 0.2451 was on 648-well scope; chance_AP = 0.5 here because only DMSO has 3 replicate wells among 6).

| Embedding | well-level AP (6 wells) | well-level pair AUC | site-level AP (12 sites) |
|---|---|---|---|
| ResNet18 (trained, 512-d) | **0.7333** | 0.5556 | 0.3425 |
| DINOv2-vits14 (384-d) | 0.6778 | 0.5833 | 0.1471 |
| DINOv2-vitb14 (768-d) | 0.6222 | 0.5000 | 0.1559 |
| OpenPhenom-ch8 (384-d) | 0.6083 | 0.3889 | 0.2249 |
| OpenPhenom-rgb3 (384-d) | 0.4639 | 0.1944 | 0.1992 |
| manual 904 (baseline) | 0.5083 | 0.3056 | — |

**Reading:** every deep embedding except OpenPhenom-rgb3 beats the manual 904 baseline at well-level replicate retrieval (0.61–0.73 vs 0.51); ResNet18 is best. Site-level same-well retrieval is weak for all (0.15–0.34), quantifying large site noise. OpenPhenom initially failed with a pos-embed shape mismatch (remote-code cache drift); after rebuilding the transformers module cache it ran correctly — included in the numbers.

---

## 4. Deliverables produced by P0

- **Figures:** `figures/29a_eval_disaggregation.png`, `29b_soft_grouped_cv.png`, `29c_fp_distance_distribution.png`, `29d_retrieval_track_switch.png` (+ `reports/figures/` copies).
- **Assets:** `reports/19_stage11_p0_summary.json`, `reports/19_stage11_p0_retrieval_summary.json`, `reports/19_stage11_p0_retrieval_results.csv`, `reports/19_stage11_p0_embeddings.npz` (12 sites × 5 embeddings, cacheable).
- **Scripts:** `scripts/stage11_p0_structural.py`, `scripts/stage11_p0_retrieval.py` (+ `stage11_p0_embeddings.npz` cache).
- **Log:** appended to `reports/22_optimization_log.md`.

## 5. Recommended P1 start (decision from P0)

1. Adopt P0-2 soft-group CV (τ=0.5) as the default maskB evaluation protocol; report within/cross decomposition (P0-1a) alongside overall AUC.
2. Treat trt-vs-DMSO AUC 1.0 as a fingerprint-identity control, not a phenotype result (P0-3 evidence); keep it in the report but clearly labeled.
3. Promote ResNet18/DINOv2 embeddings as additional retrieval features (P0-4); validate on full 648-well scope before touching the classifier.
4. Keep descaffolded ECFP4 as an ablation control only (P0-1b), not a default feature.

---

## Commit reference

P0 commit: see `git log -1` (Stage 11 P0 entry in `22_optimization_log.md`).

---

## 6. P2 execution record (2026-10-06)

P2 executed the shortboard's retrieval-feature and task-difficulty threads with
a coverage extension; P2-1 (contrastive fine-tuning) and P2-2 (Harmony
re-assessment) remain out of scope for this round and are parked in the log.

- **P2-A — deep-embedding coverage extension:** downloaded **18 treated wells** of
  plate **BR00116992** (8 channels each, 144 TIFFs, 351.1 MB, public AWS
  cellpainting-gallery bucket, 0 failures; plate-map trt check 18/18) → deep
  coverage grows from 6 wells / 12 sites to **24 wells / 30 sites** (ResNet18
  512-d embeddings, `reports/19_stage11_p2_embeddings.npz`). Script:
  `scripts/stage11_p2_download_br00116992.py`.
- **P2-B — extended replicate retrieval (24 wells, 17 queries):** 904 mean AP
  **0.3945** / MRR 0.4085 / R@1 0.235; deep mean AP **0.1418** / MRR 0.1788 /
  R@1 0.059. P0-4 6-well numbers reproduce exactly (deep 0.7333 vs 904 0.5083);
  at larger coverage the deep embedding no longer beats 904 — the P0-4
  single-plate advantage does **not** transfer across plates.
- **P2-C — harder task: trt-vs-trt pairwise AUC (7 compounds × 2 wells, 21
  pairs, leave-one-pair-out LR):** 904 mean AUC **0.7619**; deep mean **0.2738**
  (below chance, honestly reported) — replaces trt-vs-DMSO as the
  model-capability probe.
- **P2-D — harder task: compound-identity top-k:** 14-well scope top-1/top-5:
  904 **0.429 / 0.929**, deep **0.000 / 0.571**; full-scope 260-treated-well 904
  identity top-1 **0.000** / top-5 **0.0115** — near-chance at full scope,
  reported as task-difficulty limitation.
- **P2-E — deep embedding promoted to retrieval feature:** report v7 §25.4
  frames deep embeddings as evaluated retrieval features (not a classification
  branch); cross-plate/in-plate/DMSO AP: 904 0.128 / 0.669 / 0.196 vs deep
  0.096 / 0.108 / 0.324; 904 cosine baseline remains the default retrieval
  substrate.
- **Assets:** `reports/19_stage11_p2_retrieval_extended_results.csv`,
  `reports/19_stage11_p2_retrieval_summary.json`,
  `reports/19_stage11_p2_retrieval_breakdown.json`,
  `reports/19_stage11_p2_embeddings.npz`, `data/raw/BR00116992/` (144 TIFFs).
- **Doc sync:** report v7 §25.1–25.5 (Tables 25.1–25.4) + Abstract/§24.1
  reading; 20/21/22 synced; PDF regenerated; full-repo AI-trace re-scan zero
  hits.

---

## Stage 11 — P3 Cross-Plate Generalization & P4 Harder-Task Boost (2026-10-06)

- **P3 — cross-plate generalization (zero new downloads, train P1 → test P2):**
  trt-vs-DMSO strict AUC **0.6825** / AP 0.9107 (≈ within-plate 0.6794–0.6892 /
  0.9074–0.9080); broad-control AUC 0.6404 / AP 0.7933 (≥ within-plate).
  260-well cross-plate retrieval AP **0.4157 / 0.4457** (R@1 0.331 / 0.369) vs
  in-plate reference **0.9583** — above chance, below in-plate. Identity top-1
  **0.331** (vs 14-well same-plate 0.429, full-scope baseline 0.0115);
  prototype 100-pair mean AUC **0.985**, sign acc **0.927**. Deep embedding
  cross-plate AP **0.0841 < 904 0.1101**. Positive: classification and
  prototype transfer; Negative: retrieval batch-gap, deep weaker.
- **P4 — trt-vs-trt harder-task boost (21 pairs, P2-identical LOOCV):**
  honest negative — no upgrade beats baseline: bagging **0.7619** (tie),
  SelectKBest k=100 0.7619 (tie, k=50 0.7262 / k=200 0.7500), XGB+LR
  **0.5714** (−0.19), combined stack **0.4762** (−0.29), 904+deep **0.5952**
  (−0.17). Baseline LR(904) 0.7619 stands; in-plate pairs saturated at 1.0,
  cross-plate pairs 0.1667 unchanged.
- **Assets:** eports/20_stage11_p3_cross_plate_results.csv,
  eports/20_stage11_p3_cross_plate_summary.json,
  eports/20_stage11_p4_trt_trt_boost_results.csv,
  eports/20_stage11_p4_trt_trt_boost_summary.json.
- **Doc sync:** report v7 §26–27; 20/21/22 synced; PDF regenerated;
  full-repo AI-trace re-scan zero hits.
