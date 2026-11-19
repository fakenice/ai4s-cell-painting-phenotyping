# Changelog

All notable changes are documented here. Dates are git commit dates on the
published branch (`git log` maps 1:1); small same-day cleanup commits are folded
into the phase entry. Work done after 2026-11-06 is described below but is still
unreleased.

## [Unreleased]

- Planned: external-baseline comparison table (published JUMP-CP phenotypic
  profiling results, e.g. the You et al. 2023 baseline accuracies), each row with
  source, protocol, and caveat about what is and is not comparable
- Planned: `reports/23_environment_fingerprint.json` re-record. `check_repo.py`
  reports 53/54 on this machine; the single FAIL is that the recorded fingerprint
  has `transformers = None` (not importable when it was recorded) while the live
  environment has 5.22.2. Pre-existing, not introduced by the commits below; the
  fix rewrites a tracked artifact, so it is left as a separate decision.
- 2026-11-19 `4ab6b91` merged `origin/master` (CITATION.cff, this changelog,
  `docs/DECISIONS.md`) into the 11 unpushed local commits instead of rebasing
  them: `reports/22_optimization_log.md` hard-codes those commits' own hashes, so
  a rewrite would invalidate the ledger. The merge is conflict-free, and the two
  untracked local copies of `CHANGELOG.md` / `docs/DECISIONS.md` were verified to
  be identical-or-subset of the published versions before being set aside.
- 2026-11-18 Added `docs/DECISIONS.md`: leakage-controlled headline, grouping
  protocol comparison, structural-control reframing, cross-site negative result
  and figure-provenance decisions, each grounded only in written in-repo evidence
  (dates = published-branch commit dates)

## 2026-11-06 (published 2026-11-19)

- `6861df5` Stage 12 cross-site external validation on `cpg0016-jump`: negative
  result — classification does not transfer (trt-vs-DMSO 0.5155–0.6436 vs 0.6825
  in-site; 9 usable plates behind a SHA256 manifest; vehicle column ≡ label
  measured on 8/9 plates), retrieval does (position-decoupled-only R@1 0.5971,
  ≈98× the applicable null); `reports/24`, PDF build scripted via
  `scripts/build_report_pdf.py`
- `cad2391` Stage 13 portability + self-check: `scripts/_paths.py` with 14
  scripts de-hard-coded, `scripts/check_repo.py` (49 checks / 50 deep),
  `tests/test_stage12_units.py` (21 tests with SKIP semantics), README §3
- `23b8a04` + `2b45eff` Stage 14 dependency truth: `requirements.txt` split into
  build vs local environment with 8 undeclared dependencies added (no invented
  version pins), `scripts/record_environment.py` +
  `reports/23_environment_fingerprint.json`, checks 49→52/53, and the three
  environment-table rows made machine-independent
- `de7a85a` Stage 15: `status_label` extracted from `build()` as a pure function
  and put under test (21→24 tests — seven label situations plus numeric
  `_meets` comparison), mutation-checked
- `11c5e4d` Stage 16 offline checks: three explicit data SKIPs, strict clone
  verification, CI citation check, 30 tests in total,
  `.github/workflows/verify.yml`
- `31f8c4e` `83d658e` `ad7ae8f` `2d4c9af` `23cfe53` ledger rows recording each
  stage's commit hash and the no-push state as of that moment

## 2026-11-18

- `29120d5` `CITATION.cff` + How-to-cite section

## 2026-11-03

- `31ca5d5` lead with the leakage-controlled classification result: scaffold-grouped
  CV becomes the headline; well-level CV demoted to an explicitly labelled
  in-fold sanity check after measuring 84.6–91.4 % test-train compound overlap

## 2026-10-08/09

- `8eb89d0`..`ea5ec59` competition freeze: v8 narrated demo video, watermark-free
  figure redraws (independent Python + draw.io vector sources), 17-page report and
  docs PDF sync

## 2026-10-06/07

- `5ec4c10`..`eb60bdf` Stage 11 protocol hardening: soft scaffold-grouped CV
  (tau = 0.6) as default, AUC-1.0 relabelled as a structural control,
  descaffolded-fingerprint ablation, cross-plate generalization runs, and
  prototype-discrimination over the full 32,640-pair grid (honest negatives kept)
- `2114111` technical report restructured to a scientific storyline, compressed
  65 pp -> 17 pp

## 2026-10-01..05

- `a674e39`..`a9add6d` Stages 6–10: structure-aware + uncertainty-aware modeling
  (ECFP4 fusion, conformal coverage), deep representation learning (in-house MLP,
  ResNet18 embeddings, single-cell CNN), matched-plate DMSO controls, ablation +
  5-fold CV + class-overlap analysis, self-supervised representation comparison
  (OpenPhenom/DINOv2) with Harmony batch correction
- `298a859` GitHub Pages homepage and interactive report dashboard

## 2026-09-29

- `f983f59` initial release: JUMP-CP `source_4` phenotypic profiling pipeline
  (stages 01–04: fingerprints/clustering, classification baseline, Fisher
  enrichment + strength score, Cellpose demo), `demo.py` entry, S3 download
  instructions, live-run demo video
