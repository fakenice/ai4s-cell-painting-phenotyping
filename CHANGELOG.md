# Changelog

All notable changes are documented here. Dates are git commit dates on the
published branch (`git log` maps 1:1); small same-day cleanup commits are folded
into the phase entry. Work done after 2026-11-03 is still being prepared for the
next release and is not described here.

## [Unreleased]

- Planned: external-baseline comparison table (published JUMP-CP phenotypic
  profiling results, e.g. the You et al. 2023 baseline accuracies), each row with
  source, protocol, and caveat about what is and is not comparable

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
