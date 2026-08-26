# CSE 4883 — DIP Course Project: Standalone Handoff & Final Plan

This repository is for the proposed **Consistency-Based Image Tampering Detection and Localization using Multiple Classical Forensic Cues** project. It is currently documentation-only; implementation has not started.

The full approved plan is maintained in the parent course workspace at `../PROJECT_HANDOFF.md`. This copy summarizes the project direction. Detailed scope and acceptance criteria are in `docs/requirements.md`.

## Core pipeline

```text
input image
  -> preprocessing
  -> SIFT copy-move map
  -> JPEG ghost map
  -> block-grid artifact map
  -> normalized evidence fusion
  -> threshold + morphology
  -> binary localization mask
  -> metrics and HTML report
```

## Constraints

- Classical DIP methods only; no deep learning.
- No web app or backend.
- Detector weights are tuned on validation data only.
- Evaluation uses self-generated tampered images with known masks.
