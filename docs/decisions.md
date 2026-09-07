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
  applicable evidence family. PRNU remains excluded because it needs a
  per-camera reference estimated from images of that camera, which would make
  the method camera-dependent rather than training-free.
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
