# Project Context

## Purpose

This repository holds the requirements and design record for a CSE 4883 Digital Image Processing course project titled **Consistency-Based Image Tampering Detection and Localization Using Multiple Classical Forensic Cues**.

The project will study whether several classical image-forensics signals can be combined into one interpretable tampering suspicion map and localization result.

## Current boundary

The repository is documentation-only while the project requirements are being reviewed. Source code, tests, datasets, generated reports, and runtime dependencies are intentionally out of scope until a later decision authorizes implementation.

## Domain vocabulary

- **Tampering**: an intentional modification to an image.
- **Copy-move cue**: evidence from repeated image content, proposed for SIFT-based matching.
- **JPEG ghost cue**: evidence from recompression differences.
- **Block-grid cue**: evidence from inconsistencies across 8x8 JPEG blocks.
- **Suspicion map**: a normalized per-pixel or per-region evidence map.
- **Evidence fusion**: the planned combination of the three cue maps.
- **Localization mask**: the binary output identifying suspected tampered regions.
- **Ground-truth mask**: the known tampered-region mask used for evaluation.

## Working principles

- Use classical digital image processing methods only.
- Keep the method explainable and reproducible.
- Define evaluation data and metrics before implementation.
- Record material architectural decisions in `docs/adr/`.
