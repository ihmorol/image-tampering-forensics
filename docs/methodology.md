# Methodology

This document specifies the system and the experimental protocol. It is written
before the experiments are run. Every design choice cites either a finding in
`docs/audit-prior-work.md` or a source in `references/notes/`.

Terminology used throughout: a **cue** is one forensic statistic producing a
spatial evidence map; **calibration** converts a cue's arbitrary output scale
into a log-likelihood ratio; **fusion** combines calibrated maps; the **decision
layer** turns a fused map into a binary mask.

---

## 1. Scope and pre-registration

**Constraint.** Training-free only. No deep learning, no classifier trained on
tampering labels, CPU only. Every parameter is either fixed by a documented rule
or selected on validation data.

**Two configurations, reported separately** (`docs/decisions.md`):

| Configuration | Cues | Applicability claim |
|---|---|---|
| **Blind** (primary) | CFA, noise level, copy-move, resampling | Any image. No camera knowledge. |
| **PRNU-augmented** (comparison) | Blind cues + PRNU | Requires reference images from the source camera. |

A fifth cue, residual co-occurrence anomaly, was planned and then dropped
because it could not be specified from a source we had read; see Section 4.4.

**Pre-registered target.** Max F1 of 0.67 to 0.69 on the Korus realistic
tampering dataset, matching the published grid-CRF result
(`korus2016_random-fields.pdf` Fig. 2, verified against the PDF).

**Pre-registered failure clause.** The target is aspirational and the blind
configuration starts from a weaker cue set than the published one: CFA alone is
0.44 and the published fusion leans on PRNU. If either configuration falls short,
the shortfall is reported as a shortfall, with the measured number, in the
abstract and the results section. The target is not adjusted afterwards, the
baseline is not moved, and the claim is not softened into a vaguer one.

**Published reference points on this exact benchmark**
(`korus2016_random-fields.pdf` Fig. 2, max F1):

| Method | max F1 |
|---|---:|
| CFA alone | 0.44 |
| PRNU alone | 0.49 |
| Naive pixel-wise fusion: sum 0.57, product 0.61, disjunction 0.57 / 0.60, empirical 0.61 | 0.57 – 0.61 |
| Grid CRF | 0.69 |
| Dense CRF | 0.68 |

The naive-fusion row is the family the pilot system belongs to. The gap between
that row and the CRF row, about 0.08 F1, is the specific quantity this work
targets.

---

## 2. Benchmark and protocol

### 2.1 Dataset

Korus realistic tampering dataset: 220 hand-made forgeries, four camera models
(Sony alpha57, Canon 60D, Nikon D7000, Nikon D90), 1920x1080, RGB uint8 TIFF,
with PNG ground-truth maps and per-camera PRNU signatures. Acquired and verified
by `scripts/fetch_korus.py`, which records the archive SHA-256 so an upstream
change is detected rather than silently absorbed.

The dataset ships official image lists (`image_lists/tifs2017.txt`, 136 images;
`wifs2016.txt`, 120 images) identifying the subsets used in the two published
papers. These are retained so that a comparison restricted to a published subset
is possible.

**Why this dataset replaces the synthetic pilot.** Audit findings A1, A2 and A7:
the pilot's masks occupied two fixed positions, a constant mask outscored the
full pipeline 0.6667 to 0.2537, and the imagery had no camera pipeline at all.
Korus is camera-native and uncompressed, so CFA and noise structure are intact —
the regime where the cues in Section 4 are defined.

### 2.2 Splits

The system is training-free, so splits exist only to select hyperparameters and
the operating threshold, never to fit a model.

**Leave-one-camera-out.** Four folds. In each fold, one camera's images are the
validation set used to choose every free parameter, and the other three cameras
are the test set. Results are reported per fold and pooled. This is stronger than
a random split: it tests whether parameters transfer across sensors, which is the
relevant generalization question for camera-pipeline cues.

Rationale from the literature: `korus2017_multiscale-prnu.pdf` Table IV reports
per-camera results and distinguishes a per-camera-tuned column from a single
universal parameter set, showing that the distinction matters (average F1 0.57 to
0.68 for the universal set). We adopt the harder, universal-parameter reading.

**Authentic negatives.** Audit finding A6: the pilot never evaluated
false-positive behaviour. Every pristine source image that has a forged
counterpart is evaluated as an authentic negative, scored with
`false_positive_rate` and the fraction of authentic images on which the system
fires at all. F1, IoU and MCC are undefined on an empty ground truth and are
reported as undefined rather than as 1.0 (`src/tamper_fusion/evaluation.py`,
audit finding E1).

### 2.3 Ground-truth convention

The copy-move source/destination question must be settled before scoring, not
after. `references/notes/copy-move.md` records that different datasets adopt
different conventions and that a detector marking only the pasted region is
penalised on half the ground-truth area when the ground truth is a combined mask.
The convention actually used by the Korus ground truth is read from the data and
recorded in the dataset manifest; the copy-move cue's output convention is then
matched to it, and the choice is stated in the manuscript.

Audit finding A3 is the cautionary case: the pilot's ground truth marked only the
destination while its detector marked both regions, so correct detections were
scored as false positives.

---

## 3. Evidence model: per-image calibration

Every cue produces a map on its own arbitrary scale. The pilot rescaled each map
by fixed percentiles and summed them with fixed weights (audit findings E6, and
the fusion described in `docs/audit-prior-work.md` Section C). Two things break
there: the scaling is not relative to the image's own background, so an
uninformative cue contributes its full share of noise; and a weighted sum of
uncalibrated scores has no probabilistic meaning.

**The fix, and its precedent.** The Ferrara CFA method already solves exactly
this problem internally: it fits a two-component Gaussian mixture to its block
statistic *per image*, with one component's mean forced to zero, and outputs the
log-likelihood ratio between the two components
(`references/notes/noise-cfa.md`, CFA reference implementation steps 5 and 6,
traced to `MoGEstimationZM.m`, `EMGaussianZM.m`, `loglikelihood.m`). We
generalise that pattern to every cue.

For cue *k* with raw map *S_k* on image *I*:

1. Transform to a domain where the two hypotheses are approximately Gaussian
   (per-cue; for ratio-type statistics this is the log, as in the CFA code).
2. Fit a two-component Gaussian mixture by EM on that image's own values, with
   the null component's mean fixed at the value the null hypothesis predicts.
3. Emit the per-pixel log-likelihood ratio
   `L_k = log N(s; mu_tampered, sigma_tampered) - log N(s; mu_null, sigma_null)`.

This makes maps commensurable across cues and across images without any fitted
global constants, and an uninformative cue yields `L_k` near zero everywhere
rather than a full-weight noise contribution.

**Reliability and abstention.** A cue that cannot be computed abstains, and
abstention is represented as `L_k = 0` (no evidence either way), not as a zero
score to be averaged. Audit finding D6 records the pilot's opposite behaviour.
Audit finding E2 records that the pilot's evaluator discarded availability
entirely.

**EM degeneracy guard.** If the mixture fit does not converge, or the two fitted
components are not separated by a documented minimum, the cue abstains on that
image. The reference implementation warns but proceeds
(`EMGaussianZM.m` lines 48-50); we abstain instead, and count abstentions in the
results.

---

## 4. Candidate cues

Each cue is independently testable and independently replaceable. Cue-level
ablation is part of the experiment (Section 8).

### 4.1 CFA demosaicing inconsistency (primary blind cue)

Reimplemented from the algorithm traced in `references/notes/noise-cfa.md`
(section "CFA reference implementation, step by step"), which was read from the
authors' GPLv3 MATLAB release. Steps, with the source file each was traced from:

1. Green channel only (`CFAloc.m:49`).
2. Fixed 3x3 Laplacian prediction residual, `[[0,.25,0],[.25,-1,.25],[0,.25,0]]`,
   applied uniformly with replicate borders (`prediction.m:23-27`).
3. Local variance of the residual computed separately at CFA-acquired and
   CFA-interpolated positions, using a 7x7 Gaussian window (sigma=1) multiplied by
   a checkerboard mask so only same-phase taps contribute, with the bias
   correction `vc = 1 - sum(w^2)` (`getVarianceMap.m:22-52`).
4. Per-block statistic: product of acquired-phase variances over product of
   interpolated-phase variances on `Nb x Nb` blocks (`getFeature.m:24-31`).
5. Two-component Gaussian mixture on `log(statistic)`, one mean fixed at zero,
   EM with `tol=1e-3`, `max_iter=500` (`MoGEstimationZM.m:26-46`,
   `EMGaussianZM.m:19-50`).
6. Log-likelihood-ratio map (`loglikelihood.m:33-42`), optional cumulation over
   `Ns x Ns` block groups, 5x5 median filter (`getMap.m:27-31`).
7. Bayer phase auto-detected per image by testing the four candidate patterns and
   picking the lowest bilinear-reconstruction error over non-smooth 16x16 blocks
   (`GetCFASimple.m`), so no camera-specific calibration is required.

**Multi-scale.** Run at `Nb=2` (one CFA period, finest possible) and `Nb=8`, the
two settings the authors' own demos use. Fusing across block sizes is the
adaptive-window idea from `korus2017_multiscale-prnu.pdf`.

**Provenance and licensing.** The algorithm is reimplemented in Python from the
documented steps; the reference code is GPLv3 and is cited in the source file and
the manuscript. This repository currently declares no license, so no conflict
arises today. If a license is added later, GPLv3 compatibility must be considered
explicitly.

**Honest caveat.** The paper's own text was not reachable (Cloudflare
interstitial on the only Green-OA host; the agent correctly did not bypass it).
Its reported numbers and its stated limitations are therefore
`not verified from retrieved text`. We cite the paper for the method and the code
for the algorithm, and we do not quote its results.

### 4.2 Noise-level inconsistency (primary blind cue)

Reimplemented from `lyu2014` as recorded in `references/notes/noise-cfa.md`:

1. Project 8x8 patches onto `K` band-pass filters of unit L2 norm (DCT AC basis
   or random symmetric-orthogonalised filters; 63 filters in the authors' main
   experiments).
2. Per channel, measure response kurtosis and variance.
3. Solve for the noise variance in closed form using the kurtosis-concentration
   relation (IJCV Eq. 9-11), with the harmonic-mean structure that gives
   robustness to per-channel outliers.
4. For localization, compute the required 1st-to-4th raw moments in a sliding
   window using **integral images** (IJCV Eq. 17), which makes the cost
   independent of window size. This is what makes the cue affordable at
   1920x1080: the authors report a 600x800 image dropping from over 600 s to 8 s.

The output is a per-pixel noise standard deviation. The evidence map is its
deviation from the image's own robust centre, calibrated as in Section 3.

`mahdian2009` is implemented as a cheaper secondary variant (wavelet HH1 MAD
estimator, `sigma = median(|HH1|)/0.6745`, per block) and used as a cue-level
baseline, not as the primary noise cue: its published output is a noise-level
segmentation requiring human interpretation, and its authors explicitly recommend
it "as a supplement to other forgery detection methods rather then a standalone
forgery detector" (Section 5).

**Known false-positive mode, to be measured not hidden.** Authentic images
genuinely contain regions of differing noise variance from exposure and scene
content (`mahdian2009` Section 5). This is precisely why authentic negatives are
in the evaluation.

### 4.3 Copy-move (blind cue)

The pilot's detector fails for a structural reason (audit finding D5): it paints
the convex hull of RANSAC inlier points, so scattered inliers produce a hull far
larger than the duplicated region.

The strongest published method, Cozzolino et al. 2015 dense-field PatchMatch, is
**closed access** and was only described to us through a secondary source
(`references/notes/copy-move.md`). We therefore implement from a paper we could
read in full: **Ryu et al. 2013**, rotation-invariant duplicated-region
localization based on Zernike moments. Implementing from a source we have read
end to end is preferred over reconstructing a closed paper from a recap.

The dense-field structure is retained: per-pixel descriptors, approximate nearest
neighbour matching, then a **dense** region mask from the matched field rather
than a hull over sparse keypoints.

`christlein2012` (read in full) supplies the comparative evidence for which
descriptor families hold up under which manipulations and is cited for that.

### 4.4 Residual co-occurrence anomaly: DROPPED

This cue was planned as a Splicebuster-style detector: high-pass residual,
quantised co-occurrence features per block, a two-component model fitted on the
image itself, and an anomaly map. Section 4.4 of the first draft of this document
committed in advance to dropping it if it could not be specified from a source we
had actually read. **It could not be, so it is dropped.**

What was established (`references/notes/noise-cfa.md`, `cozzolino2015` entry):
the WIFS 2015 paper is closed access at every location checked (Unpaywall, IEEE,
ACM, ResearchGate), and the GRIP lab's own code download links return 404 and are
not archived. The nearest readable source by the same authors, arXiv:1703.04615,
describes the same residual co-occurrence feature family but has an SVM back-end,
not Splicebuster's unsupervised EM, so it does not supply the mechanism we need.
Its own title confirms the mismatch: it recasts these descriptors as
convolutional neural networks, which our training-free constraint excludes
outright.

Reconstructing the EM decision stage from recollection is exactly the failure
mode this project's rules forbid. The cue is therefore absent from the pool, and
its absence is stated in the manuscript rather than papered over. The blind
configuration proceeds with four cues: CFA, noise level, copy-move, resampling.

INFERENCE, recorded as a limitation and not acted on: an anomaly cue over residual
co-occurrence features is plausibly complementary to the four retained cues, so
its absence probably costs us some performance against the pre-registered target.
That is a cost of the evidence standard, and it is reported as such.

### 4.5 Resampling (blind cue, repaired)

The pilot's resampling cue is retained but repaired. Audit finding D1: it wrote
one score per tile at a single pixel, left every other pixel at zero, then
Gaussian-blurred the resulting impulse field, and its `counts` array was computed
but never used to normalise. The repair assigns the score across the tile and
normalises by the accumulation count.

This cue is relevant here because Korus forgeries involve resampled inserted
objects, and because `iakovidou2018` Table 7 shows rescaling destroys the JPEG
grid cue, implying the resampling signature is present.

### 4.6 JPEG cues: excluded from the main pool, retained for the stress condition

`references/notes/jpeg-compression.md` establishes that **none of the six JPEG
methods applies to Korus as shipped**. Lin 2009, Bianchi–Piva block-grained and
Bianchi–Piva integer-periodicity need a genuine double-JPEG history and
quantization headers; Ye 2007 needs an estimable quantization table; Farid's
ghost needs the spliced content to carry its own lower-quality prior compression.
CAGI is the only bitmap-only method among them.

Korus is uncompressed TIFF. The pilot's two JPEG cues are therefore not merely
weak on this benchmark, they are inapplicable, and they will abstain on every
image. They move to the JPEG recompression stress condition (Section 9), where
they are meaningful.

### 4.7 PRNU (comparison configuration only)

Uses the per-camera signatures shipped with the dataset. Present solely to enable
a like-for-like comparison with the published 0.69. Never reported without the
configuration label, and its narrower applicability claim is stated wherever it
appears.

---

## 5. Fusion

Under conditional independence of cues given the label, the correct combination
of calibrated log-likelihood ratios is their **sum**. That is the default:

`L_fused(x, y) = sum_k r_k * L_k(x, y)`

where `r_k` is a reliability weight in [0, 1], and an abstaining cue contributes
exactly zero. Reliability weights are selected on validation data only, per fold.

Conditional independence is an approximation, and the ablation in Section 8 tests
it directly by measuring whether cue pairs are redundant.

**Comparison: Dempster–Shafer.** `fontani2013` provides a fusion framework built
specifically to model tool reliability and to represent a tool that cannot answer,
which is our abstention problem. It is implemented as an alternative fusion rule
and compared against the summed-LLR rule on validation data. Note that Fontani's
reported result is image-level classification (AUC 0.745, Fig. 7a), not per-pixel
localization, so it is cited for the fusion mechanism and not as a localization
baseline.

---

## 6. Decision layer

The pilot applied a single global threshold plus morphology. Audit finding: no
spatial prior. This is the largest identified gap, worth about 0.08 F1 on this
benchmark (Section 1 table).

**Grid CRF.** Label field `y` over pixels or blocks, energy

`E(y) = sum_i U_i(y_i) + lambda * sum_(i,j in N) V(y_i, y_j)`

with the unary term from the fused log-likelihood ratio and a contrast-sensitive
Potts pairwise term on a 4-connected grid. Minimised by graph cut, which is exact
for this two-label submodular energy. `lambda` is selected on validation data per
fold.

Grid CRF is chosen over dense CRF because on this benchmark the published grid
result is marginally the better of the two (0.69 versus 0.68) and it is the
cheaper and more reproducible of the two on CPU.

**Ablation.** The decision layer is ablated against global threshold plus
morphology on identical fused maps, so the contribution of the spatial prior is
measured rather than assumed.

---

## 7. Evaluation

Implemented in `src/tamper_fusion/evaluation.py`, already committed and tested.

**Primary measures.**

- **Max F1** over thresholds. This is the measure the published Korus results
  report, so it is what makes our numbers comparable. It is an **oracle**: it
  uses the best threshold for each image. It bounds what any threshold rule could
  achieve and must never be presented as an achievable operating point.
- **Operating-point F1** at a single threshold selected on validation data only.
  This is the honest deployable number. Both are always reported together, and
  the gap between them is itself a reported result.
- **ROC-AUC** and **MCC**, which are threshold-free and defined without reference
  to an operating point.
- **False-positive rate** on authentic images.

Reporting both an oracle and a selected-threshold number is a direct response to
audit finding E4: the pilot reported a single fitted-threshold Dice, so "the cue
carries no signal" and "the threshold is wrong" were indistinguishable.

**Uncertainty.** Percentile bootstrap confidence intervals over images, 10 000
resamples, fixed seed. Any claim that one configuration beats another is stated
with a bootstrap interval on the paired difference, never on the two means
separately. Audit finding E5.

**Aggregation.** Per-image scores averaged, with undefined measures excluded and
counted explicitly, never coerced to zero or one.

**Polarity.** Some forensic statistics are sign-ambiguous. The evaluation module
supports scoring both polarities, but this is an oracle choice; it is disabled by
default and, if ever enabled for a cue, is disclosed for that cue.

---

## 8. Baselines and ablations

Everything is run under one protocol, on identical splits.

**Baselines.**

1. **Constant-mask baseline.** The predictor that ignores the image, fitted on
   validation mask frequency. This is the baseline that exposed the pilot's
   benchmark (audit A2), and it is reported on Korus too. If any configuration
   fails to beat it, that is the headline result.
2. **The pilot system**, unchanged, on Korus. `fusion.py` and `metrics.py` are
   frozen for exactly this purpose.
3. **Each single cue**, calibrated, thresholded the same way.
4. **Published numbers** from `korus2016_random-fields.pdf` Fig. 2, quoted as
   published and clearly marked as not re-run by us.

**Ablations.**

- Each cue removed from the full pool, one at a time.
- Calibration on versus off (percentile scaling as in the pilot).
- Fusion rule: summed LLR versus Dempster–Shafer versus naive weighted sum.
- Decision layer: CRF versus global threshold plus morphology.
- CFA block size: `Nb=2`, `Nb=8`, and the two fused.

Each ablation reports the paired difference with a bootstrap interval.

---

## 9. Stress conditions

Applied to the test split only, after the configuration is frozen:

- JPEG recompression at quality 95, 90, 80, 70. This is the condition where the
  JPEG cues of Section 4.6 become applicable, and where the CFA cue is expected
  to degrade sharply — `popescu2005cfa` Section IV-B reports the CFA cue is close
  to useless below JPEG quality about 96.
- Rescaling. Expected to damage both CFA and the JPEG grid cue
  (`iakovidou2018` Table 7).
- Gaussian blur and additive noise, which directly attack the noise cue.

The expectation that these degrade performance is stated in advance. Degradation
is a result to report, not a failure to conceal.

---

## 10. Compute budget

The agreed budget is a few hours total. At 1920x1080 the measured cost of the
pilot's repaired resampling cue is about 15 s per image single-threaded, which is
55 minutes for 220 images on one core and about 5 minutes across 12. The noise
cue is affordable only because of the integral-image formulation (Section 4.2).

Cue maps are computed once per image and cached to disk, so the many ablation and
fusion configurations reuse them instead of recomputing. Selection and fusion
experiments then cost seconds.

If the full protocol does not fit the budget, images are subsampled with a fixed
seed and the subsampling is stated in the results, per the agreed constraint.
Resolution is not reduced: reducing it is what produced the pilot's degenerate
regime.

---

## 11. Threats to validity

- **Single dataset.** All results are on one benchmark. Parameters that transfer
  across its four cameras may not transfer to other sources. The leave-one-camera-out
  protocol partially addresses this; it does not remove the limitation, which is
  stated in the manuscript.
- **Reimplementation fidelity.** CFA is reimplemented from the authors' code and
  copy-move from Ryu et al.; neither is the original binary. Our numbers are
  "our implementation of X", never "X". Where our reimplementation underperforms
  a published number, that is reported as a possible fidelity gap rather than as
  a finding about the method.
- **Closed sources.** Ferrara 2012 and Cozzolino 2015 were not readable in full.
  Their reported results are not quoted anywhere.
- **Oracle measures.** Max F1 is an oracle and is always paired with a
  validation-selected operating point.
- **The pre-registered target may not be met.** See the failure clause in
  Section 1.

---

## 12. What would falsify the claims

Stated in advance so the result cannot be reinterpreted afterwards:

1. If the constant-mask baseline is not clearly beaten, the system does not work
   and nothing else in the results matters.
2. If calibrated fusion does not beat the best single cue, with a bootstrap
   interval on the paired difference excluding zero, then the fusion contributes
   nothing and must be reported as contributing nothing.
3. If the CRF decision layer does not beat global thresholding on identical fused
   maps, the central methodological claim of this work fails.
4. If the blind configuration does not beat the frozen pilot system on the same
   data and splits, the rebuild was not worth doing and the paper says so.
