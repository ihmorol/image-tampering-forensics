# Design decisions

- The project uses classical digital image processing methods only. Deep
  learning is outside the course-project scope.
- The study will select a small cue subset from distinct evidence domains.
  The initial candidate pool is SIFT-based duplicated-content matching,
  JPEG ghost or double-compression analysis, classical resampling-trace
  analysis, and JPEG block-grid inconsistency analysis.
- JPEG ghost and block-grid cues are both compression-related. The block-grid
  cue is therefore an ablation candidate rather than an assumed complementary
  component.
- The default fusion baseline is equal weighting after robust map
  normalization. Any tuned nonnegative weights, score thresholds, or
  morphology settings must use the validation split only and must be recorded.
- The final subset is chosen by incremental validation gain, robustness across
  manipulation types, and computational cost. The test split is used only once
  for final comparison.
- The manuscript will treat the cue pool as a research variable. The working
  hypothesis is that duplicated-content, compression-history, and geometric
  resampling evidence are more complementary than two compression-only cues;
  this remains a hypothesis to test, not a result.
- Results will be delivered through a command-line workflow and static HTML
  reports. A web application and backend are not planned.
- The implementation branch is approved for a bounded prototype. The prototype
  evaluates the four-cue candidate pool and selects a subset from validation
  ablations. It must not report universal superiority or treat heuristic JPEG
  responses as proof of authenticity.
- The included synthetic generator is a deterministic smoke-test fixture, not a
  substitute for a natural-image benchmark. Final claims require source-disjoint
  images, authentic JPEG controls, recompression stress tests, and held-out
  per-cue ablations.

## Amendments following the pilot audit (2026-09-07)

These decisions supersede the ones above where they conflict. The evidence is in
`docs/audit-prior-work.md`.

- **The synthetic pilot benchmark is withdrawn as an evaluation set.** A constant
  mask that never reads the image outscores the full pipeline on it (finding
  A2). It is retained only as a unit-test fixture and as the data behind the
  audit, never as evidence for a claim about cue quality.
- **Evaluation moves to the Korus realistic tampering dataset**: 220 hand-made
  forgeries, four camera models, 1920x1080, TIFF, with pixel-accurate PNG ground
  truth. It is camera-native and largely free of recompression, so
  camera-pipeline cues remain measurable on it.
- **The scope constraint forbidding resampling, CFA, ELA and PRNU analysis is
  lifted for resampling, CFA and noise cues.** The pilot already shipped a
  resampling cue in violation of the original constraint (finding F1), and the
  chosen dataset is uncompressed, which makes camera-pipeline cues the
  applicable evidence family.
- **The prohibition on deep learning and trained classifiers stands.** The target
  is the best training-free system, and every parameter must be fixed by a
  documented rule or chosen on validation data.
- **Equal-weight fusion of percentile-normalised maps is withdrawn.** Cue maps
  are calibrated per image against their own background statistics before
  fusion, so that an uninformative cue contributes near zero rather than its
  full share of noise.
- **A single global threshold is withdrawn as the decision rule.** The decision
  layer must include a spatial prior.
- **Reporting must include threshold-free measures and uncertainty intervals.**
  Mean per-image Dice at one fitted threshold is not sufficient evidence
  (findings E4, E5).
- **Authentic images must be evaluated.** Without them the false-positive
  behaviour of the system is unmeasured (finding A6).
- **No result may be reported unless a committed script reproduces it**, and the
  command must be recorded.

## PRNU and the evaluation target (2026-09-07, supersedes the PRNU exclusion above)

An earlier amendment on this page excluded PRNU on the grounds that it needs a
per-camera reference and would make the method camera-dependent. That exclusion
is withdrawn, for a reason established from the literature rather than from
preference.

The published training-free results on this exact benchmark are, from
`korus2016_random-fields.pdf` Fig. 2 (max F1, verified against the PDF):

| Method | max F1 |
|---|---:|
| CFA alone | 0.44 |
| PRNU alone | 0.49 |
| Naive pixel-wise fusion (sum / product / disjunction / empirical) | 0.57 to 0.61 |
| Grid CRF | 0.69 |
| Dense CRF | 0.68 |

The headline 0.69 fuses CFA with PRNU. Excluding PRNU while evaluating on a
dataset that ships PRNU signatures would make our numbers incomparable with the
published baseline for a reason that is ours, not the data's.

**Two configurations will therefore be built and reported separately.**

1. **Blind configuration (primary).** No camera knowledge of any kind. This is
   the system whose applicability claim is "works on any image". Its honest
   comparison point is the individual blind cues and the naive fusion row above.
2. **PRNU-augmented configuration (comparison only).** Adds the dataset's
   per-camera signatures as one further cue, solely so that a like-for-like
   comparison with the published 0.69 is possible. Its applicability claim is
   explicitly narrower: it requires reference images from the source camera.

Neither configuration's number may be reported without stating which one it is.

**Pre-registered target.** The stated success criterion, fixed before any result
is seen, is to match the published grid-CRF level of max F1 approximately 0.67
to 0.69 on the Korus realistic tampering dataset.

**Pre-registered failure clause.** This target is aspirational, and the blind
configuration begins from a weaker cue set than the published one: CFA alone is
0.44 and the published fusion leans on PRNU. If either configuration falls short
of the target, the shortfall is reported as a shortfall, in the abstract and the
results section, with the measured number. The target is not adjusted after the
fact, the comparison is not moved to a friendlier baseline, and the claim is not
softened into a vaguer one. A missed target is a result.
