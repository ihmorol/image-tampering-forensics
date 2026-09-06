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
- Implementation begins only after the team approves the requirements.
