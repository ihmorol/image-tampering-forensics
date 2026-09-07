# Project Requirements

## Project goal

Build a classical image-forensics system that identifies suspicious images and
localizes altered regions. The project must demonstrate measurable,
reproducible performance under controlled conditions. It must not claim that
the method proves whether any arbitrary image is authentic.

## Research questions

The project is framed as a cue-selection and fusion study rather than as a
fixed three-detector implementation:

1. Does fusing complementary classical forensic cues improve tampering
   detection and localization over the strongest individual cue?
2. Which smallest cue subset gives a reliable gain across manipulation types
   and image conditions?

The study must answer these questions with ablation experiments. A cue is
retained only when it adds measurable validation-set value without an
unacceptable cost or scope restriction. No claim of universal superiority is
permitted.

## Required forensic pipeline

The planned pipeline must:

1. Load and standardize an input image.
2. Produce a suspicion map from a duplicated-content detector based on SIFT
   keypoint matching and geometric verification.
3. Produce a suspicion map from a compression-history detector based on JPEG
   ghost or double-compression analysis when the input supports that cue.
4. Produce a suspicion map from a geometric-edit detector based on classical
   resampling traces.
5. Evaluate JPEG 8x8 block-grid inconsistency as an additional ablation cue;
   retain it in the final subset only if it adds validation-set value beyond
   the compression-history cue.
6. Normalize the available maps and combine them using nonnegative weights
   selected on the validation split only. If a cue is unavailable for an input,
   record that fact and renormalize the available weights.
7. Convert the fused map into a binary localization mask using thresholding and
   morphological cleanup.
8. Save the evidence maps, fused map, final mask, timing, cue availability,
   and summary report.

## Dataset requirements

- Use 30 to 50 source images with a consistent maximum image dimension.
- Generate approximately 120 to 200 altered images.
- Include copy-move, splicing, object removal, geometric-edit, and
  recompression cases where the selected cue domains are meaningful.
- Generate a ground-truth binary mask for every localized alteration.
- Separate validation data used for parameter choices from held-out test data.

## Evaluation requirements

- Report pixel precision, recall, F1, IoU, and Dice scores.
- Report results by manipulation type and overall.
- Compare every candidate cue, every pair, the selected subset, and the full
  candidate pool. Report the incremental gain from adding each cue.
- Measure processing time for each detector and the complete pipeline.
- Repeat evaluation after JPEG recompression, resizing, Gaussian blur, and
  additive Gaussian noise.
- State known failure cases, including degradation after uniform recompression,
  missing JPEG history, weak texture for keypoint matching, and edits without
  measurable resampling traces.

## Deliverables

- Proposal presentation following the instructor's required eight sections.
- Controlled dataset generator and generated image-mask pairs.
- Modular analysis pipeline and single-image command-line entry point.
- Evaluation workflow and summarized results.
- Self-contained static HTML reports for representative images.
- Lightweight automated tests for core numerical behavior and detector smoke
  checks.
- AI-usage log recording the date, assistant, purpose, whether output was used,
  and how it was verified.
- Final report and viva preparation material.

## Constraints

- Use classical digital image processing methods only. Do not use deep learning
  or machine-learning classifiers.
- Keep each detector independently replaceable and testable.
- Tune fusion weights on validation data only. Never tune on the test set.
- Treat normalized detector scores as comparable scales, not calibrated
  probabilities.
- Use a command-line workflow and static reports. Do not build a web app,
  backend, frontend, or API.
- Do not add restoration or inpainting as an output feature, CFA analysis, ELA,
  PRNU, Benford analysis, or a learned fusion model. Classical resampling
  analysis is in scope as a candidate because it supplies a distinct
  geometric-edit cue.

## Planned technology

Python, OpenCV, NumPy, scikit-image, Pillow, and Matplotlib are the planned core
tools. Dependency versions and development setup will be selected when
implementation begins.

## Completion criteria

The project is complete when the held-out evaluation runs reproducibly, the
fused system is compared fairly with every candidate cue and subset,
representative reports are generated, limitations are documented, and every
team member can explain the full pipeline and their assigned contribution.

## Approval gate

The candidate-pool requirements are approved for a bounded prototype on the
implementation branch. The prototype must remain classical, validation-driven,
and explicit about provisional detector heuristics. Public benchmark claims or
new cue families require a new decision record.
