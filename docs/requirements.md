# Project Requirements

## Project goal

Build a classical image-forensics system that identifies suspicious images and
localizes altered regions. The project must demonstrate measurable,
reproducible performance under controlled conditions. It must not claim that
the method proves whether any arbitrary image is authentic.

## Required forensic pipeline

The planned pipeline must:

1. Load and standardize an input image.
2. Produce a suspicion map from SIFT copy-move matching.
3. Produce a suspicion map from JPEG ghost or double-compression analysis.
4. Produce a suspicion map from JPEG 8x8 block-grid inconsistency analysis.
5. Normalize and combine the three maps using documented fixed weights.
6. Convert the fused map into a binary localization mask using thresholding and
   morphological cleanup.
7. Save the evidence maps, fused map, final mask, timing, and summary report.

## Dataset requirements

- Use 30 to 50 source images with a consistent maximum image dimension.
- Generate approximately 120 to 200 altered images.
- Include copy-move, splicing, object removal, and recompression cases.
- Generate a ground-truth binary mask for every localized alteration.
- Separate validation data used for parameter choices from held-out test data.

## Evaluation requirements

- Report pixel precision, recall, F1, IoU, and Dice scores.
- Report results by manipulation type and overall.
- Compare the fused result with each individual forensic cue.
- Measure processing time for each detector and the complete pipeline.
- Repeat evaluation after JPEG recompression, resizing, Gaussian blur, and
  additive Gaussian noise.
- State known failure cases, especially degradation after uniform recompression.

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
- Keep the three detectors independently replaceable and testable.
- Tune fusion weights on validation data only. Never tune on the test set.
- Treat normalized detector scores as comparable scales, not calibrated
  probabilities.
- Use a command-line workflow and static reports. Do not build a web app,
  backend, frontend, or API.
- Do not add restoration, inpainting as an output feature, resampling detection,
  CFA analysis, ELA, PRNU, Benford analysis, or fusion-method research.

## Planned technology

Python, OpenCV, NumPy, scikit-image, Pillow, and Matplotlib are the planned core
tools. Dependency versions and development setup will be selected when
implementation begins.

## Completion criteria

The project is complete when the held-out evaluation runs reproducibly, the
fused system is compared fairly with all three individual cues, representative
reports are generated, limitations are documented, and every team member can
explain the full pipeline and their assigned contribution.

## Approval gate

No project code should be added until the team reviews and approves this
requirements document and resolves any instructor feedback about deliverables.
