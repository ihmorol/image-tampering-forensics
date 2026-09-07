# Audit of the prior pilot study

This document records defects found in the state of the project at commit
`7402ecf` (the merge of `dev/implementation` and `dev/manuscript-research`).

Every quantitative claim below is reproduced by:

```
python scripts/audit_prior_work.py --workdir <scratch dir>
```

Findings are labelled by the evidence that supports them:

- **Executed** — reproduced by running the committed code.
- **Read** — established by reading the committed code, with file and line.
- **Discrepancy** — the manuscript and the repository disagree; both sources quoted.

Severity follows the project ladder: P0 blocks any published claim, P1 breaks a
stated acceptance criterion, P2 is a defect that does not by itself invalidate a
result.

---

## A. Benchmark validity

### A1 (P0, Executed) Ground-truth masks occupy two fixed positions

`generate_sample` places the tampered region at coordinates derived only from
the image dimensions (`src/tamper_fusion/dataset.py:143`-`159`). Position and
size do not depend on the seed. Across four manipulation kinds and nine seeds,
at 128x128, 256x256 and 512x512, the masks collapse to **two distinct bounding
boxes**: splicing and object removal share one, copy-move and geometric edit
share the other. Every mask covers an identical 4.79 % of the frame.

### A2 (P0, Executed) A predictor that never reads the image beats the pipeline

Because of A1, the mask can be predicted from the manipulation prior alone. A
constant mask, fitted only on the train and validation mask frequency and then
applied blind to the held-out test split, scores:

| Predictor | Held-out test Dice |
|---|---:|
| Constant mask, ignores image content entirely | **0.6667** |
| Committed forensic pipeline (`copy_move` + `resampling`) | **0.1376** |

The complete forensic system scores **4.8x worse than not looking at the image**.
No conclusion about cue quality, cue complementarity, or fusion can be drawn
from this benchmark. This invalidates the pilot's central experimental claim,
not merely its magnitude.

The manuscript reports 0.2062 for a different cue subset on a differently
configured run (see B1-B3); that run is not reproducible from the repository, so
the two numbers are not directly comparable. The constant-mask result does not
depend on which configuration was used, because A1 holds at every image size.

### A3 (P0, Read) Copy-move ground truth contradicts the copy-move detector

The generator marks only the **destination** region as tampered
(`dataset.py:159`). The SIFT detector fills the convex hulls of both the source
and the destination point sets (`detectors.py:152`-`155`). A correct copy-move
detection is therefore scored as roughly 50 % false positive by construction.
This penalty is built into the benchmark and is not disclosed in the manuscript.

### A4 (P1, Read) "Object removal" is an overlapping copy-move

`object_removal` copies a strip from the same row band of the same image
(`dataset.py:149`). With `x0 = 0.12w` and `rw = 0.22w`, the source region
`[0, 0.22w]` **overlaps** the destination `[0.12w, 0.34w]`. It is neither object
removal nor inpainting, and the source/destination semantics are incoherent. The
manuscript reports this class as "object replacement".

### A5 (P1, Read) Geometric-edit masks do not match the altered pixels

The patch is rotated with `expand=False` (`dataset.py:155`), so the pasted
content does not fill the axis-aligned rectangle, while the mask is that full
rectangle (`dataset.py:159`). Ground truth marks pixels that were not altered.

### A6 (P0, Read) Image-level detection is never evaluated

The generator emits only tampered images. There are no authentic negatives
anywhere in the manifest. The project goal in `docs/requirements.md` is to
"identify suspicious images and localize altered regions", but only localization
on known-tampered images is measured. False-positive behaviour on authentic
images is unmeasured, so no detection claim is supported.

### A7 (P0, Read) The synthetic imagery has no camera pipeline

`_textured_background` (`dataset.py:167`-`181`) composes uniform random noise,
bicubic-upsampled random noise, sinusoids and random discs. There is no colour
filter array, no demosaicing, no sensor noise model, no lens point-spread
function, and no natural image statistics. Classical forensic cues are defined
on the physics of the camera and compression pipeline. Evaluating them on
imagery that contains none of it does not test the hypothesis the study states.

---

## B. Reproducibility of the published numbers

### B1 (P0, Discrepancy) Image size and format do not match

- `docs/experiment-results.md`: images were "encoded as JPEG at quality 88"; the
  manuscript Table 4 caption reads "for 128 x 128 images".
- The committed generator writes **256x256 PNG** (`generate_dataset.py:16`-`17`;
  `generate_sample` defaults to `size=(256, 256)` at `dataset.py:136`, and the
  script exposes no size flag). There is no JPEG encoding step anywhere in the
  committed generator.

### B2 (P1, Discrepancy) Split sizes do not match and are internally inconsistent

- `docs/experiment-results.md` states 40 images, 10 per manipulation type, with
  "four images per type for validation and eight per type for the held-out
  test". Four plus eight is twelve per type, which exceeds the ten that exist,
  and implies 48 images from a 40-image set. The stated protocol is not
  self-consistent.
- The committed splitter produces **train 22 / validation 11 / test 7** with
  between one and three images per type in the test split
  (`dataset.py:82`-`95`, hash-bucketed at 20 %/20 %).

### B3 (P0, Executed) The reported cue subset cannot arise from the committed code

Both JPEG cues return `available=False` for non-JPEG input
(`detectors.py:181`-`188`, `detectors.py:292`-`299`). On the committed PNG
output, `jpeg_history` and `block_grid` are unavailable for **40 of 40 images**.
The manuscript's selected subset is `jpeg_history + resampling + block_grid` —
two of whose three members are structurally unavailable on the data the
committed generator produces.

### B4 (P1, Read) No committed script produces the layout the evaluator consumes

`scripts/evaluate.py:20` loads `maps/{stem}_{cue}.npy`. `cli.py:49` writes
`{cue}.npy` into a per-image output directory. The two are incompatible, and no
committed script bridges them. The published experiment was produced by a driver
that is not in the repository.

### B5 (P1, Read) The published run is not recorded

No command line, seed, environment capture, or run manifest is stored for the
numbers in `docs/experiment-results.md` or the manuscript.

**Consequence.** Findings B1 through B5 mean the manuscript's headline numbers
(validation Dice 0.1875, held-out Dice 0.2062, the per-manipulation table, and
the detector timings) cannot be regenerated from this repository. They should be
treated as unverified until the experiment is rebuilt.

---

## C. Manuscript describes a method the code does not implement

### C1 (P0, Discrepancy) The decision threshold is never tuned

Manuscript Section 3.1, step 4: "fit map normalization, nonnegative weights, and
**threshold** on validation data". Section 4.3 repeats "A threshold produces the
binary mask", and Section 4.4 describes selection over the candidate pool.

`scripts/evaluate.py:25` calls `evaluate_subsets`, which calls
`tune_fusion(subset_samples, subset, thresholds=[0.5])` (`fusion.py:153`). The
threshold is pinned to 0.5 for every subset and every configuration. The
threshold sweep in `tune_fusion` (`fusion.py:91`, thirteen values from 0.2 to
0.8) is dead code on this path. The reported search is weights-only.

### C2 (P1, Discrepancy) The stated tie-break rule is not the implemented one

Manuscript Section 4.4: "maximize validation Dice, prefer the smaller subset
within a tie, then prefer lower runtime".

`scripts/evaluate.py:29` sorts by `(-mean_dice, len(cues), cues)`. The third key
is the alphabetical cue-name list. Runtime is measured (`detectors.py:57`) but
never consulted in selection. The manuscript's Table 3 "tied; larger" decision is
therefore explained by a rule that the code does not contain.

### C3 (P2, Read) The reported weights come from a coarse grid at a fixed threshold

Weights 0.25 / 0.25 / 0.50 are the only resolution available from
`weight_step=0.25` (`fusion.py:90`, `fusion.py:181`-`194`), evaluated at the
pinned threshold from C1.

---

## D. Detector defects

### D1 (P0, Read) The resampling cue produces a blurred impulse field

`resampling_trace` iterates windows on a stride of `tile` pixels but assigns the
score to **one pixel** per window (`detectors.py:269`), leaving every other pixel
at zero. The result is then Gaussian-blurred with `sigma = tile`
(`detectors.py:271`), which spreads isolated impulses and attenuates them by
roughly `1 / (2*pi*sigma^2)`. The `counts` array (`detectors.py:258`, `:270`) is
populated but never used to normalise. The output is a sparse impulse field, not
a dense periodicity map, and `robust_normalize` then rescales what is mostly
zero. This is the slowest cue in the pilot (98.4 ms reported) and the most
damaged.

### D2 (P1, Read) The JPEG cue is not the JPEG ghost statistic

`jpeg_ghost` takes the per-pixel `argmin` over recompression qualities and scores
the absolute difference between that quality and its local mean
(`detectors.py:220`-`226`). Where the quality response is flat — smooth regions,
saturated regions — the `argmin` is unstable, so the disagreement term is large
in the absence of any tampering. Farid's method inspects the depth and location
of the local error minimum, not the spatial variance of the arg-minimum. The
manuscript describes the cue as "the observable pixel-domain part" of the ghost
idea, which understates the difference.

### D3 (P0, Read) Both JPEG cues self-disable on any resize

`detectors.py:189` and `detectors.py:300` mark the cue unavailable whenever
preprocessing resized the image. `run_candidate_detectors` defaults to
`max_dimension=1024` (`detectors.py:37`) and `cli.py:21` defaults the same. Any
benchmark image larger than 1024 px on its long side is resized, so both JPEG
cues become unavailable for it. On a camera-resolution corpus this silently
reduces the four-cue system to two cues.

### D4 (P1, Read) The block-grid cue is a texture detector

`jpeg_block_grid` scores each block by how far its mean absolute high-frequency
DCT magnitude and its block-boundary difference deviate from the image-wide
median, in MAD units (`detectors.py:334`-`352`). Textured blocks deviate from the
median regardless of compression history. Nothing in the statistic references
quantisation, a quantisation table, or a second compression.

### D5 (P1, Read) Convex hulls inflate the copy-move mask

`detectors.py:152`-`155` fills the convex hull of all inlier points for both the
source and the destination set. Scattered inliers produce a hull far larger than
the duplicated region, and the hull is filled at full confidence.

### D6 (P2, Read) "No evidence found" is reported as available evidence

The three early returns at `detectors.py:79`, `:105` and `:130` return
`available=True` with an all-zero map. Downstream this is fused as a confident
zero rather than as an abstention, and it enters the fitted normalisation
statistics.

### D7 (P2, Read) Copy-move matching is quadratic in keypoints

`detectors.py:88` runs `knnMatch` of the descriptor set against itself. At
camera resolution this is a scaling risk that the 128 px pilot did not expose.

---

## E. Evaluation defects

### E1 (P0, Read) Empty-versus-empty scores as a perfect match

`fusion._dice` returns `1.0` when both masks are empty (`fusion.py:174`), and
`mask_metrics` returns `iou = 1.0` for an empty union (`metrics.py:18`). The
pilot contains no authentic images so this was not triggered, but any corpus with
authentic negatives will award a perfect score for predicting nothing.

### E2 (P1, Read) The evaluator discards cue availability

`scripts/evaluate.py:23`-`24` builds two-tuples, so `_unpack` (`fusion.py:177`)
marks every cue present in the dictionary as available. The availability logic
that the detectors carefully compute is dropped at evaluation time.

### E3 (P1, Read) Normalisation fitting does not scale

`fit_normalization` concatenates every pixel of every validation image into one
array before taking percentiles (`fusion.py:41`-`43`). At 1920x1080 this is about
2 M values per image; a 200-image validation split needs roughly 3 GB.

### E4 (P0, Read) Only one operating point is measured

Every reported figure is mean per-image Dice at a single threshold. Without a
threshold-free measure — ROC-AUC, best-F1, or MCC — "this cue carries no signal"
and "this threshold is wrong" are indistinguishable. The ablation in manuscript
Table 3 spans 0.1761 to 0.1875, a range that a single threshold choice can
plausibly produce on its own, and no uncertainty interval is reported.

### E5 (P1, Read) The held-out sample is too small for the claims made

The committed configuration yields seven held-out images. The manuscript reports
per-manipulation means over eight images each with no confidence interval. The
manuscript acknowledges this; it remains a blocker for any comparative claim.

### E6 (P2, Read) Two different normalisations are applied in sequence

`preprocess.robust_normalize` clips at the 2nd and 98th percentiles
(`preprocess.py:104`) and is applied inside each detector.
`fusion.robust_normalize` clips at the 1st and 99th against dataset-fitted
statistics (`fusion.py:46`) and is applied again during fusion. Two functions
share a name, differ in defaults, and compose.

---

## F. Scope and documentation

### F1 (P1, Discrepancy) The shipped system violates the approved scope

`docs/requirements.md` constraints state: "Do not add restoration, inpainting as
an output feature, **resampling detection**, CFA analysis, ELA, PRNU, Benford
analysis, or fusion-method research." The system ships a resampling cue and the
manuscript's contribution is cue-selection research. The requirements document
was never amended.

### F2 (P2, Discrepancy) Top-level documents describe a repository that no longer exists

`README.md` states "No implementation has started yet"; `AGENTS.md` states the
repository "is documentation-only until the project requirements are approved".
Both are false on the implementation branch.

---

## Summary

| Class | P0 | P1 | P2 |
|---|---:|---:|---:|
| A. Benchmark validity | 4 | 2 | 0 |
| B. Reproducibility | 2 | 3 | 0 |
| C. Method/manuscript mismatch | 1 | 1 | 1 |
| D. Detector defects | 2 | 3 | 2 |
| E. Evaluation defects | 2 | 3 | 1 |
| F. Scope and documentation | 0 | 1 | 1 |

The controlling finding is A2. The benchmark rewards a constant mask more than it
rewards the forensic system, so the pilot measures the geometry of its own
generator rather than the quality of any forensic cue. Fixing the fusion layer or
adding cues on top of this benchmark would produce numbers that remain
uninterpretable. The dataset has to be replaced before any methodological change
can be assessed.
