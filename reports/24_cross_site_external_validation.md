# 24. Cross-site external validation — JUMP-CP pilot → `cpg0016-jump` (independent site)

**Date:** 2026-11-06
**Script:** `scripts/stage12_external_site.py` (stages `fetch`, `controls`, `position`, `retrieval`, `evaluate`, `diagnose`, `trainsize`)
**Artifacts:** `reports/21_stage12_external_site_summary_{negcon_z,rank,zclip5,posresid}.json`,
`reports/21_stage12_external_per_plate_*.csv`, `reports/21_stage12_external_controls.csv`,
`reports/21_stage12_position_audit.csv`, `reports/21_stage12_retrieval_position_split.{csv,json}`,
`reports/21_stage12_external_diagnose.{csv,json}`, `reports/21_stage12_train_size_curve_*.json`,
`reports/21_stage12_replicate_structure.csv`, `reports/21_stage12_replicate_sharing.json`
(written by `--stage controls`; the retrieval JSON additionally carries `arm_summaries_by_plate_pair`
and `paired_strict_by_plate_pair`)
**External data:** `<workspace>/data/external/cpg0016/` — one level **above** `github_repo/`
(`scripts/stage12_external_site.py` derives it from its own location: repo root = the parent of
`scripts/`, workspace = the parent of that; override with `AI4S_REPO` / `AI4S_WORKSPACE`).
Gitignored, 159,914,604 bytes on disk; every object carries a SHA256 in
`data/external/cpg0016/manifest_sha256.csv` — 17 rows, 159,909,495 bytes of fetched objects,
all `status = ok`)

## Verdict, by layer

| Layer | Status | Evidence |
|---|---|---|
| Data layer (download, checksum, schema join) | 完成 | 17/17 objects verified before modelling; 10 plates, 3,673 feature columns, `Metadata_InChIKey` join reachable through `well → JCP2022 → compound` |
| Replication layer (trt-vs-DMSO, pilot → independent site) | **未通过** | Pooled cross-site AUC 0.5155–0.6436 across four arms; the only plate whose vehicle layout follows the pilot convention gives 0.4248–0.5543, i.e. chance |
| Confound layer (well position ≡ label) | 完成 (measured, not asserted) | 8 of 9 usable external plates put every DMSO well in columns 02/23; position-only CV AUC = 1.0000, permutation p = 0.0000 |
| Committed-claim layer (in-site cross-plate 0.6825 is a morphology-transfer number) | **需要限定** | The pilot's two plates are the same array (384/384 identical compound, 64/64 identical vehicle positions); a coordinate-only model transfers p1→p2 at AUC **0.7450**, above 0.6825 |
| Retrieval layer (same-compound identity, position-decoupled) | 通过 | External site. Strict arm — queries whose compound has **no** well at the query's coordinate, so the layout cannot be read: R@1 **0.5971 [0.5488, 0.6403]**, R@10 0.700, n = 350 over 16 plate pairs, applicable null 0.0061 (~98×). Broad different-coordinate arm: R@1 0.4514, R@10 0.8445 (n = 2,142). Paired against the position-matched arm: +0.0541, one-sided Wilcoxon p = 0.0057 |
| Train-size layer (does a smaller pilot train transfer better?) | 未定 | Direction flips between arms (+0.031 / −0.055 / +0.016 AUC), no arm reaches significance |

The honest summary sentence: **cross-site *classification* transfer was not reproduced, and the
in-site cross-plate number that the report treats as evidence of transfer is partly a well-layout
readout; cross-site *retrieval* transfer was reproduced and survives removal of the layout.**

---

## 1. Question

The repository's committed headline for control separation is a cross-plate result: train
treated-vs-DMSO on pilot plate `BR00116991`, test on `BR00116992`, strict-DMSO AUC 0.6825
(`reports/20_stage11_p3_cross_plate_summary.json`, report v7 §4.3 Table 5). Both plates come
from one source, one protocol, one derivation batch, and — as measured here — one array layout.
The question this document answers is whether the same trained model separates treated wells
from vehicle wells on plates that another lab acquired and another derivation batch processed.

## 2. Design

**Train side.** `cpg0000-jump-pilot/source_4`, plate `BR00116991`: 260 treated wells, 64 DMSO
wells, 904 `Cells_/Cytoplasm_/Nuclei_` features.

**Test side.** `cpg0016-jump/source_2`, batch `20210614_Batch_1` (2021 acquisition, independent
of the pilot source), 10 plates × ~384 wells × 3,673 feature columns.

**Label rule, identical on both sides.** DMSO = `Metadata_InChIKey == IAZDPXIOMUYVGZ-UHFFFAOYSA-N`;
everything else that is annotated is treated. This is the only label definition that exists on
both sides: the external compound plates carry no positive-control annotation, so the external
negative class is pure vehicle. `JCP2022_UNKNOWN` wells (18 in total across the 9 usable plates)
are dropped from the primary analysis and re-added as treated in a sensitivity arm.

**Feature space.** The intersection of the pilot's 904 features with the external 3,673 columns
is **601 features**, used for every arm. Where a plate has no finite value for an intersecting
feature, the same columns are dropped from the training matrix as well (symmetric alignment);
all nine plates ended up using the full 601.

**Four normalisation arms, applied identically to both sides:**

| Arm | What it does |
|---|---|
| `negcon_z` | Robust z against the vehicle wells of each plate (the CPG publication normalisation) |
| `rank` | Per-column rank within plate |
| `zclip5` | Robust z clipped at ±5 |
| `posresid` | Two-way additive row + column residualisation of every feature, i.e. the layout-stripped arm |

**Statistics.** Plate-level (cluster) bootstrap, 2,000 resamples over the 9 usable plates — wells
inside a plate are not independent, so resampling wells would understate the interval. AP is
reported as **lift over the prevalence floor**: external DMSO is 321/3,436 = 9.3 % of the pooled
negative-class mass, so a constant predictor scores AP 0.9066 and raw AP is meaningless on its own.
The negative control re-runs the whole pipeline with the pilot labels shuffled.

**Plate excluded.** `1053600681` has 384 vehicle wells and 0 treated wells (< 8 per class):
it is that batch's vehicle plate, not a compound plate. 9 of 10 requested plates are used.

## 3. Result: the classification replication does not hold

Pooled cross-site performance, pilot → external site:

| Arm | AUC | 95 % CI (plate bootstrap) | P(AUC > 0.5) | AP lift over 0.9066 floor | Negative control (shuffled labels) | In-site, same protocol (p1 → p2) |
|---|---|---|---|---|---|---|
| `negcon_z` | 0.5695 | 0.5386 – 0.5999 | 1.000 | +0.0284 | 0.4923 | 0.7100 |
| `rank` | 0.6436 | 0.6005 – 0.7009 | 1.000 | +0.0393 | 0.4581 | 0.6947 |
| `zclip5` | 0.6011 | 0.5647 – 0.6395 | 1.000 | +0.0329 | 0.4823 | 0.6932 |
| `posresid` | **0.5155** | **0.4601 – 0.5670** | **0.747** | +0.0106 | 0.4823 | 0.6718 |

The three first arms have bootstrap intervals above 0.5, so "something transfers" is not
refuted outright — but §4 shows that for eight of the nine plates the label contrast *is* a
column contrast, and the layout-stripped arm collapses to chance. The committed in-site
reference is 0.6825 / AP 0.9107; re-run under this protocol (601 features, L2 logistic
regression, strict DMSO) it is 0.6718–0.7100, so the in-site number itself is stable and the
loss is specific to the site change.

Sensitivity to the 18 dropped `JCP2022_UNKNOWN` wells (counting them as treated) moves
per-plate AUC by at most 0.0039 and changes 7 of 9 plates in the third decimal. It is not the
explanation for anything below.

## 4. Why: the vehicle layout is the label, on 8 of 9 plates

`--stage position` measures the layout instead of assuming it (`reports/21_stage12_position_audit.csv`):

| Site | Wells | Treated | DMSO | Columns holding DMSO | Max share of DMSO in one column (perm p) | Position-only CV AUC |
|---|---|---|---|---|---|---|
| pilot `BR00116991` | 324 | 260 | 64 | 22 columns | 0.078 (p = 0.979) | 0.5361 |
| pilot `BR00116992` | 324 | 260 | 64 | 22 columns | 0.078 (p = 0.979) | 0.5361 |
| external `1053600674` | 383 | 318 | 65 | 24 columns | 0.077 (p = 0.981) | **0.3556** |
| external `1053600704/711/728/735/742/759/766/773` (8 plates) | 380–384 | 348–352 | 32 | **columns 02 and 23 only** | 0.500 (p = 0.000) | **1.0000** |

Reading: on those eight plates, a classifier that is handed nothing but the well barcode —
row letter and column number as dummy variables — separates treated from vehicle perfectly
(AUC 1.0000, and the permutation test says the concentration of vehicle in two columns cannot
arise by chance, p = 0.0000 / 2,000 permutations). Their cross-site AUCs of 0.55–0.81 are
therefore **not readable as morphology transfer**: a random-feature model trained on the same
coordinates would score the same. Plate `1053600674` is the one external plate whose layout
follows the pilot convention (vehicle spread over all 24 columns, position-only AUC 0.356),
and it is exactly where the cross-site scores fall to chance:

| Arm | `1053600674` cross-site AUC | `1053600674` within-plate 5-fold AUC |
|---|---|---|
| `negcon_z` | 0.5041 | 0.7301 |
| `rank` | 0.5543 | 0.7163 |
| `zclip5` | 0.5086 | 0.7124 |
| `posresid` | 0.4248 | 0.6791 |

The stratified pooled view (also in each summary JSON under
`cross_site_pooled_by_vehicle_layout`):

| Stratum | n plates | `negcon_z` | `rank` | `zclip5` | `posresid` |
|---|---|---|---|---|---|
| Vehicle in fixed columns (confounded; not usable as transfer evidence) | 8 | 0.5837 [0.557, 0.608] | 0.6660 [0.627, 0.717] | 0.6173 [0.591, 0.652] | 0.5532 [0.535, 0.574] |
| Vehicle scattered like the pilot (`1053600674`) | 1 | 0.5041 | 0.5543 | 0.5086 | 0.4248 |

The layout-transfer arm closes the argument from the other side: a coordinate model trained on
pilot plate 1 scores **0.414–0.421** on each of the eight compound plates (and the reverse
transfers score 0.433–0.495), i.e. the two sites' layouts are not merely different but
anti-aligned — the pilot's "vehicle-looking" coordinates are treated coordinates there.

## 5. Independent evidence of a site change (not a layout artefact)

`--stage diagnose` compares the two fitted models directly rather than inferring from AUC
(`reports/21_stage12_external_diagnose.csv`):

| Arm | Pilot → external AUC | External → pilot AUC | Coefficient cosine | Coefficient Spearman | Sign agreement, pilot top-50 features | Share of external DMSO wells called treated |
|---|---|---|---|---|---|---|
| `negcon_z` | 0.5695 | 0.5624 | −0.0007 | 0.022 | 0.48 | 0.411 |
| `rank` | 0.6436 | 0.5569 | +0.0639 | 0.060 | 0.54 | 0.296 |
| `zclip5` | 0.6011 | 0.5656 | −0.0044 | 0.002 | 0.46 | 0.327 |
| `posresid` | 0.5155 | 0.5992 | +0.0420 | 0.039 | 0.46 | 0.492 |

The direction that features matter is essentially uncorrelated between sites (|cosine| ≤ 0.064,
sign agreement on the 50 strongest pilot features is at coin-flip 0.46–0.54), and the pilot-trained
model calls 30–49 % of the external vehicle wells "treated". So even where the pooled AUC stays
above chance on the layout-confounded plates, the two sites are not using the same morphology.

## 6. What this says about the committed in-site number (0.6825)

This is the part that changes existing text rather than adding new claims.

Measured, not assumed:

- pilot `BR00116991` and `BR00116992` are the **same array**: 384/384 wells carry the identical
  InChIKey in both plates, and the 64 DMSO wells occupy an identical 64-coordinate set
  (`dmso_positions_identical_across_plates = True`, |p1 ∩ p2| = 64).
- A coordinate-only model (well row + column dummies, no morphology) trained on plate 1 and
  tested on plate 2 scores **AUC 0.7450**
  (`21_stage12_position_audit.csv`, row `pilot in-site layout transfer`).

0.7450 is above the committed strict cross-plate AUC 0.6825, and above the re-run of the same
protocol in this pipeline (0.6718–0.7100 depending on arm). So the cross-plate experiment as
run **does not hold the layout out**; a well-position readout is sufficient to match or beat it,
and the number cannot be attributed to morphology transfer on its own.

What is *not* taken away: within the pilot, position is a weak predictor (position-only CV AUC
0.5361, permutation p 0.979 — vehicle is spread over 22 columns), and after residualising row
and column effects the in-site cross-plate AUC is still 0.6718 (vs 0.5). Morphology does carry
non-positional signal in site; what the 0.6825 loses is its interpretation as *layout-free*
generalisation. The same applies to the committed cross-plate retrieval number: because each
pilot compound occupies exactly one well per plate, **100 % of the 260 cross-plate retrieval
positives are same-coordinate wells** (position-decoupled arm is empty; see
`21_stage12_retrieval_position_split.csv`, `pilot in-site cross-plate` rows).

## 7. Positive result: identity retrieval that does not depend on position

The layout that makes this test possible was measured (`--stage controls` now writes
`21_stage12_replicate_structure.csv` and `21_stage12_replicate_sharing.json`), and it is
narrower than a "replicated compound library":

- **Within a plate** only a handful of compounds are replicated: each of the eight
  column-vehicle plates puts 8 of its 324–328 distinct InChIKeys in 4 wells and the other
  316–320 in 1 well; plate 1053600674 has 19 of 299 in 2 wells and 280 in 1.
- **Between plates** a usable pair shares just 8–10 compounds (36 pairs, 291
  compound × pair cells), and the coordinate relation splits those cells into
  224 × (4 wells here, the *same* 4 coordinates there), 40 × (1 well here, 4 different
  coordinates there), 24 × (2 wells here, 4 different there) and 3 × (1 and 1, different).
  So recurrence is mostly *layout-repeating*; the 67 zero-overlap cells are the only place
  where the layout cannot be read.
- The pilot gives neither: 260 treated wells = 260 distinct InChIKeys (1 well per compound per
  plate), and its two plates are the same array, so all 260 of its cross-plate retrieval
  positives are same-coordinate wells.

Same-compound retrieval, cosine on L2-normalised per-plate `negcon_z` profiles of the shared
601 features, query plate → library plate. A query can have both a same-coordinate and a
different-coordinate true match (the 4-replicate compounds), so the arms are per query, and the
strict arm is the case where no same-coordinate match exists at all:

| Arm | Plate pairs | Queries | R@1 [plate-pair bootstrap] | R@10 | Median rank | Chance R@1 (single match / any accepted replicate) |
|---|---|---|---|---|---|---|
| External, **decoupled-only** (layout cannot help) | 16 | 350 | **0.5971 [0.5488, 0.6403]** | 0.700 | 1 | 0.00300 / 0.00609 |
| External, position-decoupled (≥1 match elsewhere) | 72 | 2,142 | 0.4514 [0.4280, 0.4751] | 0.8445 | 2 | 0.00289 / 0.00817 |
| External, position-matched (same-coordinate match exists) | 56 | 1,792 | 0.3689 [0.3443, 0.3940] | 0.8181 | 2 | 0.00286 / 0.00286 |
| Pilot in-site cross-plate (all position-matched by construction) | 1 | 260 | 0.3692 (904 feats) / 0.3423 (601 feats) | 0.6038 / 0.6269 | 4 | 0.00385 |

The null matters here: when 4 replicate wells all count as correct, random ranking gives R@1
4/n, not 1/n, so the lift over the *applicable* null is ~98× (strict), ~55× (broad decoupled)
and ~129× (matched) — the earlier "~156× chance" phrasing used 1/n for every arm and is
withdrawn.

Paired contrast on the 56 plate pairs where the broad decoupled and matched arms both exist
(`paired_by_plate_pair`): decoupled **0.4230 [0.4001, 0.4442]** vs matched **0.3689**; mean
paired difference **+0.0541**, one-sided Wilcoxon **p = 0.0057**, 31 pairs better / 19 worse.
The strict arm cannot be paired against matched (its 16 pairs have no same-coordinate arm by
construction — `paired_strict_by_plate_pair` is `null` in the JSON for that reason), so it is
compared at the level of the arm means above.

Three things follow. First, compound identity is recoverable across plates at an independent
site even on queries where the compound has **no** well at the query's coordinate — the case
where a layout readout is impossible, and it is the *highest* arm (0.5971 vs 0.3689 matched).
Second, its 16 pairs are exactly `1053600674` ↔ the eight column-vehicle plates, i.e. the same
layout-clean plate whose classification result sits at chance, so the positive and the negative
come from the same plate pair set and cannot be artefacts of different data. Third, the scope
is bounded: 350 strict queries drawn from 8–10 shared compounds per pair, and the metric is
identity retrieval, not a treated-vs-vehicle decision.

## 8. Open: does pilot training-set size help cross-site transfer?

`--stage trainsize` subsamples pilot compounds (32/65/130/260 from one plate; 130/260 across
both plates), 5 repeats, paired against the full-train per-plate AUCs
(`21_stage12_train_size_curve_*.json`):

| Arm | Fewer (32) − full (260), 1 plate | Wilcoxon p (fewer > full) | Fewer (130) − full (260), 2 plates | Wilcoxon p |
|---|---|---|---|---|
| `negcon_z` | +0.0306 [0.0003, 0.0637] | 0.150 | +0.0028 [−0.0094, 0.0144] | 0.326 |
| `rank` | −0.0552 [−0.0880, −0.0168] | 0.973 | −0.0121 [−0.0243, −0.0003] | 0.898 |
| `zclip5` | +0.0157 [−0.0220, 0.0583] | 0.367 | −0.0081 [−0.0230, 0.0064] | 0.875 |

The sign of "less training data transfers better" flips with the normalisation choice, and no
contrast is significant with the paired statistic. **Unresolved** — and it should stay unresolved
until it is tested on plates that are not layout-confounded, because on those eight plates any
train-size effect is partly an effect on how well the model reads the column code.

## 9. Interpretation and limits of this own analysis

- The conclusion is about *this* pair of sources. `cpg0016-jump/source_2` batch
  `20210614_Batch_1` is the JUMP pilot-consortium data; a different external source with a
  scattered vehicle layout could in principle be transfer-testable, and the CPG has other
  sources. Nothing here shows cross-site transfer is impossible; it shows the claim is not
  supported by the data tested.
- Only 1 plate out of 9 in the usable set has a pilot-compatible layout. The chance-free
  estimate of cross-site transfer therefore rests on n = 1 plate (0.5041 / 0.5543 / 0.5086 /
  0.4248), which is why the verdict is "not reproduced" rather than "shown to be zero".
- Feature intersection is 601/904; the 303 dropped pilot features are not a bias in either
  direction but they do mean the external side is a smaller morphological description than the
  one the pilot numbers use.
- `posresid` within-site 5-fold AUCs (0.008–0.040 on the column-vehicle plates) are a
  construction artefact: after residualising columns on a plate where the label *is* the column,
  the class signal has been removed by design, so those cells are not effect sizes and are not
  used as evidence anywhere above. The interpretable `posresid` numbers are the cross-site AUC
  (0.5155 pooled, 0.4248 on the layout-clean plate) and the in-site AUC (0.6718).
- **Documentation discrepancy found and corrected.**
  `reports/12_technical_report_draft_v7.md` §2.1 and `README.md` §4 described the compound
  plates as "303 unique compounds, **4 technical replicates** per compound". Both counts were
  re-derived from the local files this line reads
  (`data/profiles/BR0011699{1,2}_normalized_feature_select_negcon_batch.csv.gz`,
  `load_pilot`). The 303 reproduces exactly as *distinct `Metadata_pert_iname` over the two
  compound plates (768 wells)*. The replicate statement does not: each plate has 384 wells =
  260 treated at 260 distinct InChIKeys (**1 well per compound per plate**) + 64 DMSO wells
  + 60 positive-control wells over 46 keys (14 keys × 2), and the two plates are the same
  array, so a treated compound has **2** wells in the analysed set, not 4. The replicate
  wording was corrected in place (`reports/12` §2.1 and §3.1, `README.md` §4,
  `reports/21_kaggle_writeup_draft.md` methods item 1); §2.1's "1,040 treated / 488 control /
  128 DMSO / 240 poscon" line was also relabelled, because those are the counts for **all four
  plates** (measured from `Metadata_pert_type`), not for the two analysed compound plates,
  whose composition is 520 treated / 128 DMSO / 120 positive-control wells. The scaffold
  arithmetic (282 groups from 303 compounds) uses the 303 that does reproduce and was left
  unchanged, as were all derived metrics. The archived drafts `reports/12_technical_report_draft_v5.md`
  and `v6.md` still carry the original "4 technical replicates" sentence — they are historical
  versions and were not rewritten; each now opens with a banner stating the measured layout and
  pointing here.
- Hypotheses closed by measurement in this line: (i) "the pooled above-chance AUC is a
  normalisation asymmetry" — closed: every arm here scales both sides with the same rule, and
  the earlier raw-vs-symmetric single-plate pair (0.5039 / 0.5041 on `1053600674`, read off the
  pre-4-arm run; those six superseded artifacts were deleted before commit, the pair is quoted
  here from that measurement record) is reproduced by the current `negcon_z` arm (0.5041), so
  the scaling choice was never the driver; (ii) "the vehicle layout is confounded with the
  label" — now measured, and it
  is, on 8/9 plates; (iii) "cross-plate retrieval is a layout readout" — partly true in site
  (100 % position-matched) and now tested at the external site where it holds up without layout,
  and after the arm definitions were tightened it holds up *best* when the layout is unavailable
  (strict arm 0.5971 vs matched 0.3689).
- **Self-correction recorded.** Two of this report's own first drafts asserted an external
  replicate structure ("each compound in 4 replicate wells per plate", later "compounds recur
  across plates at different coordinates — only 5.7 % share the well") that a direct
  measurement of the fetched plates contradicted: pairs share 8–10 compounds, and 224 of the
  291 shared cells repeat the *same* 4 coordinates. Both statements were replaced with the
  measured breakdown, which is now produced by `--stage controls` rather than by hand, and the
  "~156× chance" retrieval lift (which compared against a 1/n null for arms that accept several
  replicate matches) was replaced by lift against the applicable null.

## 10. Reproduce

```bash
cd "E:/Desktop/Kaggle_2026/2026-10-10 AI4S Open Innovation：AI for Life Science/github_repo"

# 1. fetch (idempotent; writes/verifies data/external/cpg0016/manifest_sha256.csv)
python scripts/stage12_external_site.py --stage fetch --sets meta,profiles

# 2. schema + identity controls per plate
python scripts/stage12_external_site.py --stage controls

# 3. well-position / vehicle-layout audit (the confound measurement)
python scripts/stage12_external_site.py --stage position

# 4. position-split retrieval (the positive result)
python scripts/stage12_external_site.py --stage retrieval

# 5. cross-site classification, one arm at a time
for ARM in negcon_z rank zclip5 posresid; do
  python scripts/stage12_external_site.py --stage evaluate --scaling $ARM
done

# 6. model-comparison diagnostics, and the train-size curve
python scripts/stage12_external_site.py --stage diagnose
for ARM in negcon_z rank zclip5; do
  python scripts/stage12_external_site.py --stage trainsize --scaling $ARM
done
```

Steps 2–6 need no path edits from a checkout at any location: the script derives the workspace
from its own file path (`<…>/data` for the fetched objects) and only `--stage fetch` writes
outside `reports/`. The 2026-11-06 refactor was checked by re-running `--stage controls` before
and after — the four controls artifacts are byte-identical.

The report PDF is rebuilt, and verified, by:

```bash
python scripts/build_report_pdf.py            # pandoc -> HTML -> Chrome print-to-PDF, then anchor checks
python scripts/build_report_pdf.py --check-only
```

Current build: `docs/12_technical_report_draft_v7.pdf`, 15 pages, MD5
`726cc35711211e062bf50074ea09602e` (the pre-Stage-12 committed build was 20 pages, MD5
`664ae12b…`, and its text layer contains none of the §4.7 anchors). The page-count change is
style, not content: 10,321 words vs 7,734 and the same 6 distinct figures, with the tighter
`docs/print_style.css` now committed instead of the unrecorded ad-hoc style.
