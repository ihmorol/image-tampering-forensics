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
