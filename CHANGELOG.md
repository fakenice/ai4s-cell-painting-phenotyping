# Changelog

All notable changes are documented here. Dates are git commit dates on the
published branch (`git log` maps 1:1); small same-day cleanup commits are folded
into the phase entry. Work done after 2026-11-03 is still being prepared for the
next release and is not described here.

## [Unreleased]

- 2026-11-18 Added `docs/external_baselines.md`: published Cell Painting numbers
  re-checked against the primary sources (Gustafsdóttir 2013 13 %-active distance
  threshold; Bray 2016 protocol; Chandrasekaran 2024 — the formal publication of
  this repo's own 303-compound dataset — with its 5–25 % sister-matching range,
  permutation/BH metric definitions and plate-layout admission; Way 2022 and
  Wolff 2025 replication/matching norms; Rohban 2017 gene-level enrichment;
  CP4All/SSL/MorphDiff representation gains; Wong only as preprint caliber), the
  seven caliber rules that say which of them this repo's AUC/AP may be quoted
  next to, and the do-not-cite register (three widely-mis-cited anchors verified
  not to exist; the report's 99.1 %/94.9 % S8/S3 lead logged as unverified).
  README gained section 7, pushing License and How-to-cite to §8/§9
  (docs/DECISIONS.md cross-reference updated)
- 2026-11-18 Added `docs/DECISIONS.md`: leakage-controlled headline, grouping
  protocol comparison, structural-control reframing, cross-site negative result
  and figure-provenance decisions, each grounded only in written in-repo evidence
  (dates = published-branch commit dates)

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
