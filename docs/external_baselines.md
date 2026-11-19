# External baselines (published numbers, each re-checked against the source)

Every published number below was re-verified on **2026-11-18** against the
primary source (final-version XML where open access, author-manuscript HTML
where noted), with the exact sentence recorded. Nothing here is quoted from
memory or from a secondary summary. Two working-level anchors that earlier
drafts of this project mentioned by title turned out **not to exist** in any
form; they are listed in §7 as do-not-cite, with their correct counterparts.

Conventions:
- **Preprint vs final version**: recorded separately for every entry. Where the
  final version exists but its full text was not reachable, the number is
  labelled by the version it was actually read from.
- **Numbers only in figures**: not transcribed unless the body text states them
  verbatim; per-class values behind box-and-whisker figures are marked
  "figure-only, not extracted" and must not be quoted as digits.

## 1. This study's own anchors (what the README reports, and what it means)

All figures below are **self-reported in this repository** (README §5 and the
technical report §22–§24), on the JUMP-CP pilot (`cpg0000-jump-pilot`,
`source_4`, 303 compounds / 1,536 wells / 904 CellProfiler features):

- Supervised treated-vs-control classification under the leakage-controlled
  protocol (soft scaffold-grouped CV, ECFP4 Tanimoto τ = 0.6): phenotype+ECFP4
  **AUC 0.5222 / AP 0.6545**; phenotype-only **AUC 0.3349 / AP 0.5559**.
- Well-level CV (sanity check, explicitly *not* the headline): AUC 0.768 /
  AP 0.936 — with 84.6–91.4 % of test compounds also present in training.
- Cross-site (cpg0016) negative result: carrier wells concentrated in two fixed
  columns in 8/9 plates ⇒ position-only CV **AUC 1.0000**; real cross-site
  pooled AUC stays at 0.5155–0.6436.
- Retrievability: different-coordinate compound-pair **R@1 0.5971**
  [0.5488, 0.6403] over 350 candidates (16 pairs; null 0.0061).
- Enrichment: **36 significant cluster–target pairs** (BH q < 0.05);
  microtubule strength median 0.9958 vs 0.9368 (Cliff's δ = 0.827,
  p = 0.00145); MOA-level enrichment null after correction.

**Internal-caliber warning that governs everything in this file**: these are
*supervised classification* and *pair retrieval* numbers. The published
Cell-Painting literature almost universally reports *unsupervised retrieval*
statistics (average precision of replicate/sister retrieval, fraction
retrieved, percent replicating/matching) or distance-threshold activity calls.
§6 states the conversion rules; none of the published percentages below is a
drop-in comparator for 0.5222, 0.768 or 5–25 %-style figures without them.

## 2. The assay itself: feature scale and the activity-call precedent

- **Gustafsdóttir et al., PLoS ONE 2013**, doi:10.1371/journal.pone.0080999
  (OA full text verified). The multiplexed-staining assay in its original
  form: "We extracted 824 morphological features…"; validation on
  "1600 commercially available bioactive compounds"; activity call by
  distance threshold: "Of the 1600 compounds, **203 (13%) were active**",
  where the cutoff "was the 95th percentile of the distances from the
  mock-treated wells to the median mock profile".
  - Relevance: this is the closest published *denominator convention* to this
    repo's treated-vs-controls task — and it is a distance-threshold call on
    per-compound median profiles, not an AUC. It also shows the real-world
    implication: a published "active rate" is always computed over the
    screened set, while this repo's classification runs over all 303 compounds.
- **Bray et al., Nature Protocols 2016**, doi:10.1038/nprot.2016.105
  (author-manuscript HTML verified; publisher XML not open). Operation
  protocol: six dyes, five channels, eight cellular components,
  "~1,500 morphological features"; design recommendations "At least four
  biological replicates are recommended… we have used five or more
  replicates" and "~30 wells/plate designated for negative controls works
  well for a 384-well format assay".
  - Relevance: defines what a Cell Painting feature vector is. This repo's
    904 features are a CellProfiler subset of that ~1,500-feature space.

## 3. The published baseline on the *same data*: CPJUMP1

This repository runs on the JUMP-CP pilot dataset, whose formal publication is
**Chandrasekaran et al., Nature Methods 2024**,
doi:10.1038/s41592-024-02241-6 (OA full text verified; preprint
10.1101/2022.01.05.475090 not cited for numbers). Design: "a set of **160
genes and 303 compounds** with (relatively) known relationships between each
other" — the same 303 compounds this repo profiles.

Its metric machinery (Methods, "Average precision, mean average precision and
fraction retrieved"): cosine similarity ranking → per-sample AP; significance
against "a null distribution built by randomly shuffling the rank list
**100,000 times**"; BH adjustment → q; "fraction retrieved" = share of
perturbations with q < 0.05.

Headline published numbers on this data:

- Sister-compound matching (compound retrieval of same-target compounds, among
  compounds that yield a signal): "only **~5–25%** of them correctly match
  their sister compounds targeting the same protein" (Fig. 4b); the paper
  calls this "much more challenging than retrieving replicates of the same
  sample", and caps sister-perturbation retrieval "at only ~25% in the best
  scenario".
- Compounds vs genetics: "the fraction retrieved for compounds is higher than
  that of genetic perturbations, across all conditions (Fig. 4a)" (per-condition
  values are figure-only, not extracted — see §7).
- Plate-layout confounding, stated by the dataset's own authors: "the reduced
  fraction retrieved values for ORF may be attributed to plate layout effects,
  in which identical treatments in different rows or columns have dissimilar
  profiles."

Relationship to this repo (§8 item 1 of the research log): our R@1 0.5971 is a
*cross-coordinate pair-retrieval* statistic on 16 sister pairs with a stated
null (0.0061); the paper's 5–25 % is a *fraction-retrieved* over permutation-
validated AP per compound, computed after signal filtering. Same dataset,
same underlying phenomenon (sister compounds do match above chance), different
statistic — the honest joint reading is "sister-level matching is possible but
far from solved", which both support; a numerical comparison is not available.
The paper's plate-layout admission is direct external support for this repo's
cross-site negative result (§1, position-only AUC 1.0000).

## 4. Compound-level replication/matching benchmarks (assay quality norms)

- **Way et al., Cell Systems 2022**, doi:10.1016/j.cels.2022.10.001
  (author-manuscript HTML verified; publisher XML not open). Connectivity-map
  style statistics on 1,327 compounds × 6 doses: percent replicating
  "much higher … in Cell Painting (**57% to 83%**, from lowest to highest
  dose) compared to L1000 (16% to 35%…)"; MOA-level percent matching "higher
  percent matching scores for Cell Painting (ranging from **16–28%**) than for
  L1000 (7–21%)". Position warning, verbatim: "we observed plate position
  effects in the Cell Painting data, particularly in edge wells".
  - These ranges span conditions (dose/cell line), i.e. they are extrema, not
    confidence intervals — see §6 rule 5.
- **Wolff et al., iScience 2025**, doi:10.1016/j.isci.2025.112445 (OA full
  text verified). EU-OPENSCREEN Bioactives resource (2,464 compounds,
  10 µM, 4 replicates, two cell lines, four imaging sites): percent replicating
  "from **84 to 94%**", percent matching "**ranged from 12 to 41%**", and
  1–11 % non-replicating profiles after filtering. Useful as a
  same-scale-chemical-library quality norm for judging whether a pilot-sized
  dataset (303 compounds) can support matching claims at all.
- **Rohban et al., eLife 2017**, doi:10.7554/eLife.24060 (OA full text
  verified). Gene-level (CRISPRi) analogue of top-k enrichment, the correct
  citation for the "eLife Cell Painting MOA" slot: among the top-5 % correlated
  gene pairs, verified connections "9% … significantly higher than that of
  other gene pairs (5% …; Fisher's test p-value=0.04)"; same-pathway
  annotation "20% … significantly higher … (6% …; Fisher's test p-value =
  7.53 × 10−9)". Gene-level, not compound MOA — do not port its percentages to
  compound tasks.

## 5. Representation-learning gains (what "better features" buys, published)

- **Moshkov et al. (CP4All / Cell Painting CNN), Nature Communications 2024**,
  doi:10.1038/s41467-024-45999-1 (OA full text verified): "improves performance
  in downstream analysis **up to 30%** with respect to classical features";
  WSL cross-dataset: mAP "+7%, 8% and 23% relative to CellProfiler features on
  BBBC037, BBBC022 and BBBC036", folds-of-enrichment "6%, 7%, and 30%".
  Caliber: relative gain on retrieval metrics over other datasets — this
  repo's 904 handcrafted features sit on the *CellProfiler baseline side* of
  that comparison.
- **Abdelmoula et al., Nature Methods 2026**, doi:10.1038/s41592-026-03270-z
  (OA full text verified): INOv2 SSL "outperforming CellProfiler with **31–37%
  gains** in site-averaged mean average precision for mechanism-of-action
  retrieval on EU-OPENSCREEN Bioactives (2,464 compounds)".
- **MorphDiff (Wang et al.), Nature Communications 2025**,
  doi:10.1038/s41467-025-63478-z (OA full text verified; checked because
  "MorphiT" in earlier notes does not exist): generated morphologies improve
  MOA retrieval "by **16.9% and 8.0%**" over IMPA and gene-expression
  baselines (one-sided Wilcoxon signed-rank + Bonferroni, p < 0.05, 10 random
  splits). Generation-based; different question from this repo.
- **Wong et al. (MOAProfiler)** — final version exists (Digital Discovery
  2023, doi:10.1039/D3DD00060E, title-level only; publisher HTML returned
  403), but every number below was read from the **bioRxiv preprint v2**
  (10.1101/2022.11.15.516561) and must be cited as preprint-caliber: image-
  field MOA classification over 176 MOA classes "AUPRC of **0.46** (random
  AUPRC = 0.006)… accuracy of 0.52"; held-out-*compound* split: "correctly
  predict MOAs for **6.0-10.7%** of the compounds in a space of 424 possible
  MOAs. Compared to a random baseline of 0.2%, this was a 25.6-45.4x
  improvement." The held-out-compound figure is the closest published
  *spiritual* analog of this repo's scaffold-grouped protocol (both ask
  "unseen chemistry?"), but it is multi-class accuracy over 424 classes —
  again not interchangeable with a binary AUC.

## 6. Caliber rules for using any number above

1. **Task family first.** Supervised AUC/AP (this repo) ≠ retrieval
   AP/FR/percent-matching (§3–§4) ≠ distance-threshold activity call (§2).
   Quote published figures only as "the published convention for this
   question is X", never as "our number is consistent with their N %".
2. **Denominators differ.** 5–25 % (sister matching) is computed *among
   signal-yielding compounds*; this repo's metrics run over all 303. A
   comparison must state which population each fraction divides.
3. **Aggregation level.** Published multi-class figures (Wong: image-field
   level; this repo: compound level after well aggregation) sit at different
   levels of the same pipeline; deeper levels average away within-plate
   variance and are not directly comparable.
4. **Same-data ≠ same-metric.** The strongest legitimate claim from §3 is
   qualitative: on the exact 303-compound set the JUMP authors themselves
   report that sister-level matching succeeds for a minority of signal-
   yielding compounds, which is why this repo frames its R@1 0.5971 (16 pairs)
   as an existence proof, not a benchmark score.
5. **Ranges across conditions ≠ confidence intervals.** 57–83 %, 16–28 %,
   84–94 %, 31–37 % are spans over doses/sites/datasets. This repo reports
   bootstrap CIs; the two bracket types must not be visually merged in any
   summary table.
6. **Preprint labels stick.** Wong numbers are preprint-v2-caliber; the JUMP
   136k expansion (10.1101/2023.03.23.534023) is *still preprint-only* per the
   Broad Cell Painting Gallery publications page (checked 2026-11-18). Cite
   them with that tag or not at all.
7. **Position confounding has published support** (Way: edge wells; CPJUMP1:
   plate layout depresses FR; Wong: edge/non-edge accuracy check). This repo's
   cross-site position-only AUC 1.0000 is the same phenomenon quantified on
   external data — cite §3/§4 for the phenomenon, keep 1.0000 for the
   magnitude.

## 7. Negative results and do-not-cite register (2026-11-18)

Titles that do **not exist** (each searched via Europe PMC, PubMed phrase
search, CrossRef bibliographic query, and web search on 2026-11-18); any
earlier note citing them should be corrected to the stated replacement:

- "Gustafsdóttir et al. 2017, *Molecular Biology of the Cell*" — no such
  paper (author×journal search returns 0). Replace with Gustafsdóttir 2013
  PLoS ONE (assay) + Bray 2016 Nat Protoc (protocol).
- "Bray et al. 2016 eLife, *Cell-population-based drug discovery with Cell
  Painting*" — no such paper ("Cell-population" 0 hits; the only eLife
  Cell-Painting title is Rohban 2017). Replace with Rohban 2017 (gene-level)
  or Way 2022 (compound-level).
- "Chandrasekaran et al. 2023, *Cell*, *Three (3) standardized…*" — no such
  paper. The v3 protocol is Cimini 2023 Nat Protoc (JUMP's own news page says
  so verbatim); the "three million…" record is Chandrasekaran 2024 Nat
  Methods (§3).
- "deep-CP", "CP-MolNet", "Cell Painting-GPT", "MorphiT" — no primary record
  under these names; "MorphiT" is almost certainly MorphDiff (§5).
- Cimini 2023 Nat Protoc (doi:10.1038/s41596-023-00840-9): abstract-level
  citation only; full text is not open and no body numbers were verified.
- Per-condition mAP/FR values in Chandrasekaran 2024 Fig. 4 and Way 2022
  Fig. 4D–E: figure-only, not transcribed; do not quote digits. The same
  caution applies inward: the "99.1% / 94.9% MoA accuracy (Sources S8/S3)"
  attributed to Chandrasekaran 2024 in this repository's technical report
  §5.2 was **not verified against the paper body on 2026-11-18** and should
  be treated as unconfirmed until it is re-checked (the paper's compound-side
  retrieval numbers we did verify are the 5–25 % sister-matching range in §3).

## Citation register (all accessed 2026-11-18)

Citable with verified body numbers: Gustafsdóttir 2013 PLoS ONE
10.1371/journal.pone.0080999; Bray 2016 Nat Protoc 10.1038/nprot.2016.105
(manuscript version); Rohban 2017 eLife 10.7554/eLife.24060; Way 2022 Cell
Syst 10.1016/j.cels.2022.10.001 (manuscript version); Chandrasekaran 2024
Nat Methods 10.1038/s41592-024-02241-6; Moshkov 2024 Nat Commun
10.1038/s41467-024-45999-1; Wolff 2025 iScience 10.1016/j.isci.2025.112445;
MorphDiff 2025 Nat Commun 10.1038/s41467-025-63478-z; Abdelmoula 2026 Nat
Methods 10.1038/s41592-026-03270-z.

Title-level only: Bray 2017 GigaScience 10.1093/gigascience/giw014; Wawer
2014 PNAS 10.1073/pnas.1410933111 (abstract read); Cimini 2023 Nat Protoc
(abstract only); Weisbart 2024 Nat Methods, Cell Painting Gallery,
10.1038/s41592-024-02399-z (metadata only); Wong 2023 Digital Discovery
10.1039/D3DD00060E (preprint carries the numbers).

Not citable: the five do-not-cite names in §7; JUMP-136k
(10.1101/2023.03.23.534023) unless labelled preprint-only.
