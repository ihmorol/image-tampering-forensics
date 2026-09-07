# JPEG compression forensics — reading notes

Scope: six JPEG-artifact papers read directly from the local PDFs in `references/papers/`
via `pypdf` text extraction. Everything below is taken from the extracted text of those
PDFs only. Where a figure/number was not present in the extracted text it is marked
`not verified from retrieved text`. Any statement of mine that is not in a paper is
prefixed `INFERENCE:`.

Project context for the relevance sections: training-free, CPU-only, per-pixel tampering
localization; primary benchmark is the Korus realistic tampering dataset (uncompressed
camera-native TIFF).

---

## lin2009

**Full citation:** Zhouchen Lin, Junfeng He, Xiaoou Tang, Chi-Keung Tang, "Fast, automatic
and fine-grained tampered JPEG image detection via DCT coefficient analysis", *Pattern
Recognition*, 2009. DOI stated on the PDF's first page: `10.1016/j.patcog.2009.03.019`.
The local copy is an "ARTICLE IN PRESS" proof, so volume/issue/pages are blank on the
proof itself; the reference lists of both Bianchi PDFs in this same folder cite it as
vol. 42, no. 11, pp. 2492–2501, Nov. 2009. A preliminary version appeared at ECCV'06
(stated in the title footnote).

**Local file:** `references/papers/lin2009_dct.pdf` (10 pages), text extraction: clean
(math glyphs are substituted in places — σ appears as `/afii9846`, ρ as `/afii9825`; the
inequalities in Section 2.2 are readable but ceiling/floor symbols are mangled).

**What the method computes:**
1. Input handling (Section 1.3 + Section 2.1 footnote 4): dump quantized DCT coefficients
   and the quantization matrices for the Y, U, V channels directly from the JPEG file
   (no full decompression). If the input is in a lossless format, it is first re-saved as
   JPEG at compression quality 100.
2. Histograms (Section 1.3, Fig. 4): build one histogram of DCT coefficients per
   (frequency, channel) pair — "at most 64 × 3 = 192 histograms". Only low-frequency
   histograms are useful because high frequencies are mostly quantized to zero.
3. Double-quantization (DQ) theory (Section 2.2): with first step q1 and second step q2,
   the number of original histogram bins mapping into double-quantized bin u2 is
   `n(u2) = q1 ( floor((q2/q1)(u2 + 1/2)) − ceil((q2/q1)(u2 − 1/2)) + 1 )` (Eq. 1).
   `n(u2)` is periodic with period `p = q1 / gcd(q1, q2)`. If q2 < q1 the histogram has
   periodically *missing* bins; if q2 > q1 it shows periodic peaks and valleys.
4. Period estimation (Section 2.3): let s0 be the index of the largest histogram bin. For
   each candidate p from 1 to smax/20 compute
   `H(p) = (1/(imax − imin + 1)) Σ_i [h(i·p + s0)]^ρ`, with
   `imax = floor((smax − s0)/p)`, `imin = ceil((smin − s0)/p)`, and ρ "can be simply
   chosen as 1". Then `p_hist = argmax_p H(p)`. Independently take `p_FFT` from the peak
   of the FFT spectrum of the histogram with the DC component removed. Final estimate
   `p = min(p_hist, p_FFT)`. If p = 1 the image is treated as singly compressed at that
   frequency and the histogram is discarded.
5. Key polarity claim (Section 3.1): **the unchanged region exhibits the DQ effect and
   the tampered region does not** — the exact opposite of the reading in [13]/[27]. Three
   reasons are given: absence of the first compression in the pasted content; DCT-grid
   mismatch of the pasted region; and boundary blocks mixing tampered and unchanged
   pixels.
6. Bayesian per-block probability (Section 3.2): for a period starting at bin s0,
   `Pu(s0+i) = h(s0+i) / Σ_{k=0}^{p−1} h(s0+k)` (Eq. 2) is the probability an *unchanged*
   block lands in that bin, and `Pt(s0+i) = 1/p` (Eq. 3) for a *tampered* block (assumed
   uniform). Then `P(tampered | s0+i) = Pt/(Pt+Pu)` (Eq. 4) and
   `P(unchanged | s0+i) = Pu/(Pt+Pu)` (Eq. 5). Each usable histogram (p > 1) votes for
   every block that contributed to it; accumulating these posteriors over all histograms
   gives the **Block Posterior Probability Map (BPPM)**, one value per 8×8 DCT block
   (Fig. 4, Fig. 1(b)).
7. Segmentation and image-level decision (Section 3.3): threshold the BPPM with an
   Otsu-style criterion `T_opt = argmax_T ( σ / (σ0 + σ1) )` (Eq. 6), where σ0, σ1 are the
   within-class variances of the two classes C0, C1 and σ is the squared difference of
   class means. Blocks in C0 (below T_opt) are the candidate tampered blocks. Four
   features are then extracted — `T_opt`, `σ`, `σ0 + σ1`, and a connectivity measure `K0`.
   K0 is computed after median-filtering the BPPM: for each pixel i in C0 count the number
   e_i of C1 pixels in its 4-neighborhood, then `K0 = Σ_i max(e_i − 2, 0) / |C0|` (the
   `max(e_i − 2, 0)` instead of e_i is deliberate, to allow narrow rather than only round
   tampered shapes). The 4-D vector is fed to a **trained SVM** for the image-level
   tampered/authentic decision; if positive, C0 is output as the tampered region.
8. Suggested refinement (Section 5): replace Eq. (2) with
   `Pu(s0+i) = n(s0+i) / Σ_k n(s0+k)`, which needs both q1 and q2; q2 is in the file
   header but q1 must be estimated, which the authors call unreliable at the time.

**Assumptions and preconditions:** input must be JPEG (or be re-saved to JPEG at quality
100 first); the unchanged region must have been JPEG compressed *before* the forgery and
the whole image re-compressed with an **aligned** DCT grid; q1 ≠ q2 in effect — "As the
DQ effect breaks down when Q1 = Q2, the image level detection becomes random guess at
Q2 = Q1" (Section 4). Section 5 lists the two explicit failure cases: (1) the image
contributing the unchanged region was not JPEG in the first place, so there is no DQ
effect anywhere; (2) the whole image was resized, rotated or cropped so the DCT grid
changed. An SVM has to be trained in advance (Fig. 3 work flow).

**Reported performance:** Section 4 — database of 10,000 images built by students from 50
"raw" BMP base images, with Q1 and Q2 each swept over {50, 55, …, 95}; half authentic,
half tampered (tampering by lazy snapping, Poisson matting, image completion or
inpainting). 20 sets of derived images used to train the SVM. "The average detection rates
(averaged on Q2) are about 60% (Fig. 10(k))"; "most of the curves have a peak between
Q2 = 80 and 90". Region-level detection rate is defined as the proportion of DCT blocks
correctly classified (Section 4). Speed: "Analyzing an image of a size 500 × 500 only
requires about 4 s on our Pentium 1.9 GHz PC, with unoptimized Matlab codes"; 4.1 s versus
610 s for blind gamma estimation on the same image (Section 4). Per-(Q1,Q2) numbers exist
only as curves in Fig. 10, not as a table — individual values `not verified from retrieved
text`.

**Applicability to uncompressed TIFF input:** **Inapplicable** to Korus camera-native
TIFF. The whole statistic is the DQ periodicity left by two *successive aligned* JPEG
quantizations; the paper's own fallback for lossless input (re-save at quality 100) yields
a *single* quantization, so every histogram estimates p = 1 and is discarded, leaving an
empty BPPM. Section 5 failure case (1) states this directly. Under a JPEG stress
condition it is still only meaningful if the *forged* content and the *host* content have
different compression histories; simply re-compressing a Korus TIFF once gives both
regions an identical single history and no DQ contrast. INFERENCE: it would become
relevant only for a stress condition built as "JPEG-compress the authentic image, splice
uncompressed content in, re-save as JPEG with an aligned grid" — i.e. a synthetic
condition we would have to construct, not the Korus data as shipped.

**Relevance to our training-free localizer:** The BPPM construction is the piece worth
stealing conceptually even though the cue itself does not apply to our benchmark: it is a
genuine per-block *likelihood accumulation* over many independent 1-D statistics
(64×3 histograms), which is exactly the aggregation structure our per-pixel suspicion map
needs, and steps 1–6 are training-free. Only step 7's SVM is trained, and it is used for
the image-level yes/no, not for localization, so it can be dropped. Note the paper's own
warning that its statistics are the *opposite* polarity to naive intuition (unchanged =
periodic, tampered = flat) — our current "high-frequency DCT energy deviates from the
median" cue has no such grounding and is, as suspected, a texture detector rather than a
compression-history detector.

**Limitations the authors themselves state:** Section 5 — accuracy needs improvement,
detected regions are not 100% correct; Eq. (2) is a crude proxy for the true `n(·)`, which
would require estimating q1 and existing q1 estimators are "too restrictive and may not be
reliable"; fails when the source of the unchanged region was not JPEG; fails when the
whole image is resized/rotated/cropped so the DCT grid moves; the authors could not test
on web-downloaded images because the history was unknown, forcing them to build their own
database; and passive forensic techniques in general admit counter-measures.

---

## bianchi2012_blockgrained

**Full citation:** Tiziano Bianchi, Alessandro Piva, "Image Forgery Localization via
Block-Grained Analysis of JPEG Artifacts", *IEEE Transactions on Information Forensics and
Security*, vol. 7, no. 3, pp. 1003–1017, 2012. DOI stated on the Porto repository cover
page of this PDF: `10.1109/TIFS.2012.2187516`. ISSN 1556-6013.

**Local file:** `references/papers/bianchi2012_blockgrained.pdf` (16 pages), text
extraction: clean (the PDF is the Politecnico di Torino repository version; page 1 is the
repository cover sheet, article starts on page 2).

**What the method computes:** a per-8×8-block *likelihood map* that a block is doubly
compressed, for both aligned (A-DJPG) and non-aligned (NA-DJPG) double compression, with
no manual region selection.

*Models (Section III).* JPEG chain model `I1 = D⁻¹₀₀ D(Q(D₀₀ I)) + E1 = I + R1` (Eq. 1),
where `D_rc` is the 8×8 block DCT with grid aligned at pixel (r,c), and E1 the
rounding/truncation (R/T) error.
- A-DJPG: doubly quantized coefficients `C2 = Q2(D1(Q1(U)) + D₀₀E1)` (Eq. 2); their
  distribution `p_DQ(x; Q1, Q2)` (Eq. 3) is the sum of `p1(v;Q1)` (Eq. 4) convolved with
  a Gaussian R/T-error density `g_DQ(v)` with mean μe, variance σe² (Eq. 5). The
  single-compression hypothesis is `p_NDQ(x; Q2)` (Eq. 6).
- NA-DJPG: applying a DCT with the *primary* grid alignment (r,c) to the doubly
  compressed image gives `D_rc I2 = D1(Q1(D_rc I)) + D_rc(E1 + R2)` (Eq. 8), so the
  unquantized-coefficient density is `p_Q(x;Q1) = p1(x;Q1) * g_Q(x)` (Eq. 9) with `g_Q`
  Gaussian of mean μe and variance `σe² + Q2²/12` (Eq. 10). The single-compression
  hypothesis is `p_NQ(x) = p0(x)` (Eq. 11), justified because a grid misalignment
  destroys quantization traces.
- Simplified models (Section III-D): for A-DJPG, `p_DQ(x) ≈ n_DQ(x) · p_NDQ(x; Q2)` for
  x ≠ 0 (Eq. 14), where `n_DQ(x) = (R(x) − L(x))/Q2` with
  `L(x) = Q1( ceil((Q2/Q1)(x − 1/2)) − 1/2 )` and `R(x) = Q1( floor((Q2/Q1)(x + 1/2)) + 1/2 )`
  (Eq. 12, attributed to [7] = Lin et al.). R/T error is folded in by convolving `n_DQ`
  with a Gaussian of standard deviation `σe/Q2`. For DC coefficients the R/T bias μe is
  absorbed by redefining L(x), R(x) with `(x − μe/Q2 ∓ 1/2)`. For NA-DJPG,
  `p_Q(x;Q1) ≈ n_Q(x) · p_NQ(x)` (Eq. 16) with `n_Q = n_Q,0 * g_Q` and
  `n_Q,0(x) = Q1` when `x = kQ1`, 0 elsewhere (Eq. 17). The x = 0 bin is corrected
  empirically using RZ, the percentage of zero DCT coefficients — the extracted text reads
  "n′_Q(0) = nQ(0)1−RZ", which I read as `n_Q(0)^(1−RZ)` but the exponent/subscript
  formatting is ambiguous in the extraction, so treat the exact form as
  `not verified from retrieved text`.

*Likelihood map (Section IV-A).* Per-coefficient likelihood ratio
`L(x) = p(x|H1) / p(x|H0)` (Eq. 18); per-block, assuming independence across the DCT
frequencies used, `L(i,j) = Π_k L(x_k(i,j))` (Eq. 19). With the simplified models this
collapses to `L(i,j) ≈ Π_k n(x_k(i,j))` (Eq. 20), which depends only on the compression
parameters and not on the image content p0(u). In Section V-A the *logarithm* of the
likelihood map is filtered with a 3×3 mean filter to pool neighbouring blocks.

*Parameter estimation (Section IV-B).* Q2 comes from the JPEG header. Q1 is estimated by
modelling the image as a two-component mixture
`p(x; Q1, α) = α·p(x|H0) + (1−α)·p(x|H1;Q1)` (Eq. 21) and maximizing (Eq. 22) over a
discrete candidate set, running **EM** (Algorithm 1) in parallel for each candidate Q1 and
keeping the one with the highest likelihood — separately for each of the 64 frequencies.
The NA-DJPG grid shift (r,c) is estimated the same way: run the EM over every shift except
(0,0) using **DC coefficients only**, and keep the globally best (Algorithm 3). p0(u) is
estimated non-parametrically from the histogram of DCT coefficients computed on a
*deliberately shifted* grid — shift (1,1) for the A-DJPG case, shift ±1 relative to the
estimated (r,c) for the NA-DJPG case — with Laplace's rule of succession
`p0(u) = (h(u) + 1)/(N + N_bin)` (Eq. 23). μe and σe are measured on the image under test
by reconstructing it in floating point and differencing against the 8-bit rounded version
(Eq. 24, Eq. 25); μe is computed only for the DC coefficient since μe = 0 for AC.

*Parameters actually used (Section V-A):* α0 = 0.95; candidate Q1 values per frequency
drawn from `{1, …, Q(50)}` where Q(50) is that frequency's step at QF1 = 50; 3×3 mean
filter on the log-likelihood map.

**Assumptions and preconditions:** the tampered image must exhibit double JPEG
compression, aligned or non-aligned; Q2 is assumed available from the JPEG header
(Section IV-B); A-DJPG works on quantized DCT coefficients read from the file, NA-DJPG on
unquantized coefficients recomputed from the decompressed bitmap on the estimated shifted
grid. It does *not* require the analyst to pre-select a suspect region. Section VI notes
the approach is invalid if operations such as resizing are applied between the two
compressions, and that it cannot work when both parts are doubly compressed with the same
grid shift.

**Reported performance:** Section V-A — dataset of 100 uncompressed TIFF images from Nikon
D90, Canon EOS 450D, Canon EOS 5D, cropped to 1024×1024; QF1 ∈ {50,55,…,95},
QF2 ∈ {50,55,…,100} = 110 combinations; three scenarios with 15/16, 1/2 and 1/16 of the
image doubly compressed. Metric is AUC of the per-block ROC.
- A-DJPG, 1/2 scenario, first 6 DCT coefficients (Tables II–IV): proposed standard map
  reaches 0.995 at (QF1 50, QF2 70), 0.999 at (50, 80/90/100), 0.976 at (90, 100), and
  ≈0.50 on the QF1 = QF2 diagonal; the simplified map is very similar (0.987 at (90,100)).
  The method of [7] (Lin et al.) on the same cells gives 0.709 at (50,70), 0.978 at
  (50,90), 0.948 at (90,100). The authors state their AUC values are higher than [7]
  "especially for lower QF2 and in the 1/2 and 1/16 scenarios", and that [7] "is almost
  useless in the 1/16 scenario" (Section V-B).
- Number of coefficients: "6 coefficients are usually enough to obtain the best
  performance" for the proposed method, whereas [7] degrades beyond 6 (Section V-B).
- Q1 estimation error rates, A-DJPG 1/2 scenario (Table V): 100% wrong on the QF1 = QF2
  diagonal, 8% at (QF1 50, QF2 60), 1–2% for QF2 ≥ 90 with QF1 ≤ 80, 98–99% for QF1 = 90.
- NA-DJPG, 1/2 scenario, 6 coefficients (Tables VI–VII): standard map 0.910 at (50,70),
  0.992 at (50,80), 0.954 at (90,100); ≈0.50 whenever QF2 < QF1. Section V-C: "for
  QF2 > 80, the proposed algorithm detects more than 85% of the regions presenting NA-DJPG
  artifacts"; in the 1/16 scenario, localization works "only when QF2 is very high (> 90)".
  Grid-shift error rates in Tables VIII–IX (e.g. 0% wrong shift at (QF1 50, QF2 80) in the
  1/2 scenario, but 93% wrong in the 1/16 scenario at the same setting).
- Realistic examples (Section V-D, Fig. 11): two forgeries with QF1 = 60, QF2 = 95 (left)
  and QF1 = 90, QF2 = 95 (right); false alarms noted in low-intensity-variance regions
  (sky) and saturated regions (car hood).

**Applicability to uncompressed TIFF input:** **Inapplicable** to Korus camera-native
TIFF. Both branches need a *double* JPEG history: the A-DJPG branch needs quantized
coefficients and Q2 from a JPEG file, and both branches score H1 = "doubly compressed"
against H0 = "singly compressed". On a never-compressed TIFF neither hypothesis holds and
the likelihood ratio is meaningless. Under a JPEG stress condition it becomes usable only
if the two regions end up with *different* compression histories; a single global JPEG
re-save of a Korus TIFF gives one uniform single compression and, per the paper's own
model, no discriminative signal. INFERENCE: the realistic stress condition for us is
"host region carries a JPEG history, spliced region does not (or carries a shifted one),
then the composite is re-saved as JPEG" — which is a condition we would have to synthesize.

**Relevance to our training-free localizer:** This is the strongest reimplementation
target of the six for any JPEG stress condition we add, and it is fully training-free —
EM plus closed-form densities, no classifier anywhere. Two ideas transfer regardless of
input format: (a) the explicit two-hypothesis likelihood ratio per block with an
independence product over a *small* number of low-frequency coefficients (6 is their
sweet spot) is a far more principled aggregation than our current "deviation from the
image median"; (b) estimating the content-only reference distribution p0(u) from a
*deliberately misaligned* grid is a cheap and reusable trick for building a content
null-model from the same image. Their per-block map at 8×8 resolution followed by a 3×3
mean filter is also directly the shape of output we want before upsampling to per-pixel.

**Limitations the authors themselves state:** Section VI — cannot separate single from
double compression when QF2 < QF1 ("very difficult to separate the distributions … when
QF2 < QF1"); NA-DJPG needs both QF2 > QF1 and a sufficient percentage of doubly compressed
blocks; the whole approach breaks if image processing operations such as resizing occur
between the two compressions; it does not work when both parts present double JPEG
compression with the same grid shift; Section V-B/V-C note detection quality is dominated
by the accuracy of the Q1 and (r,c) estimates, which degrade badly in the 1/16 scenario;
Section V-D notes false alarms in low-variance and saturated regions.

---

## bianchi2012_ipm

**Full citation:** Tiziano Bianchi, Alessandro Piva, "Detection of Nonaligned Double JPEG
Compression Based on Integer Periodicity Maps", *IEEE Transactions on Information
Forensics and Security*, vol. 7, no. 2, pp. 842–848, 2012. DOI stated on the Porto
repository cover page of this PDF: `10.1109/TIFS.2011.2170836`. ISSN 1556-6013.

**Local file:** `references/papers/bianchi2012_ipm.pdf` (7 pages), text extraction: clean
(page 1 is the repository cover sheet).

**What the method computes:** a single scalar feature per candidate quantization step that
detects whether an image has been non-aligned doubly JPEG compressed, plus estimates of
the primary grid shift and the primary DC quantization step. It is a **whole-image
detector, not a localizer.**

1. Three-case DCT model (Eq. 4): applying an 8×8 DCT with grid alignment (i,j) to the
   doubly compressed image yields quantized-lattice clustering when (i,j) = (0,0) (the
   last compression), clustering on the *primary* lattice when (i,j) = (y,x) (the first
   compression's shift), and no lattice clustering for any other shift.
2. Only the **DC coefficient** of each block is used — the effect "is more evident in the
   case of the DC coefficient, when most of the analyzed DCT coefficients are different
   from zero" (Section III).
3. For every one of the 64 shifts (i,j), build the DC histogram `h_ij` and evaluate its
   Fourier transform at reciprocal-integer frequencies:
   `f_ij(Q) = Σ_k h_ij(k) e^{−j2πk/Q}`, Q ∈ ℕ (Eq. 5).
4. **Integer Periodicity Map (IPM)**: `M_ij(Q) = |f_ij(Q)| / Σ_{i'j'} |f_{i'j'}(Q)|`,
   0 ≤ i, j ≤ 7 (Eq. 6). In the presence of NA-JPEG, M(Q1) has one entry much larger than
   the rest at the primary shift (y,x); with no NA-JPEG, M(Q) is nearly uniform for every
   Q ≠ Q2.
5. Uniformity is scored by the **min-entropy** `H∞(Q) = min_ij ( −log M_ij(Q) )` (Eq. 7);
   a strong peak gives low min-entropy.
6. Decision (Section III-B, Algorithm 1): test all Q from `Qmin = 2` to `Qmax = 16`.
   Classify as NA-JPEG if some Q ≠ Q2 gives `H∞(Q) < T1` and
   `(y,x) = argmax_(i,j) M_ij(Q) ≠ (0,0)`. If several Q qualify, the one with lowest
   min-entropy is taken as Q1.
7. Q1 = Q2 case (Section III-A): the (0,0) peak from the last compression masks the
   primary peak, so a **differential IPM (DIPM)** is used:
   `M'_ij(Q) = K⁻¹ · max( M_ij(Q) − P(M_ij(Q)), 0 )` (Eq. 8), with K normalizing the DIPM
   to sum to one, and `P(·)` a symmetry-based prediction about the (4,4) axes (Eq. 9):
   the mean of the three symmetric counterparts in region RS = {i ≠ 0,4 and j ≠ 0,4};
   the single horizontal or vertical counterpart in RH = {i = 0,4; j ≠ 0,4} and
   RV = {i ≠ 0,4; j = 4 or 0}; neighbour averages for (0,4), (4,0) and (4,4); and 0 for
   (0,0). Its min-entropy is `H'∞(Q) = min_ij ( −log M'_ij(Q) )` (Eq. 10), compared with a
   second threshold T2.
   The symmetry rationale (Section III-A): with no NA-JPEG, M(Q2) is approximately
   symmetric about shift (4,4), because shifts symmetric about (4,4) mix pixels from
   adjacent original blocks in the same proportion.

**Assumptions and preconditions:** input is a JPEG image; Q2 (the DC quantization step of
the last compression) is known; the primary compression must have used a **non-zero grid
shift** — the method is by construction blind to aligned double compression ("by 'non
NA-JPEG' we mean either a singly compressed image or a doubly compressed image with
aligned grid: concerning the proposed algorithm, the two cases are indistinguishable",
footnote 1). Detection is hard when Q1 < Q2: "the presence of NA-JPEG is usually difficult
to detect when Q1 < Q2" (Section III), because the error term's standard deviation must be
small relative to Q1. The case Q1 = 1 is explicitly stated to be undetectable
(Section IV). The threshold pair (T1, T2) is set per QF2 and per image size from training
statistics — i.e. it is *threshold-calibrated*, though the paper stresses no classifier is
trained on features.

**Reported performance:** Section IV — 1000 uncompressed TIFF images from Nikon D90,
Canon EOS 450D and Canon EOS 5D, tested on central crops of 128×128, 256×256, 512×512 and
1024×1024. Q1 swept 2–16, Q2 swept 1–16 → 240 (QF1,QF2) combinations, giving 240,000
tampered and 16,000 original images per image size. 5-fold cross-validation with 800
training / 200 test images.
- Table I (accuracy %, 1024×1024): 88.5 at (QF1 50-57, QF2 50-57); 95.7 at (QF1 50-57,
  QF2 86-95); 98.0 at (QF1 68-76, QF2 86-95); 98.9 at (QF1 86-95, QF2 96); 85.4 at
  (QF1 86-95, QF2 86-95); and ≈50 (chance) in the lower-left cells where QF1 ≫ QF2
  (e.g. 49.8 at (QF1 86-95, QF2 68-76)).
- Text summary (Section IV): "when QF2 − QF1 > 10 NA-JPEG is detected with very high
  accuracy (> 95% in most cases), while it is still detected with about 90% accuracy when
  QF2 is similar to QF1 and with about 80% accuracy when QF1 − QF2 < 10 and QF1 < 76."
- Comparisons: "Compared to [6], our detector is from 5% to 15% more accurate for similar
  image sizes … our detector needs only a 256×256 image to achieve the best performance of
  [6]. Compared to [9], our detector is from 10% to 25% more accurate."
- Table IV: probability of detection at a forced 1% false-alarm rate, 1024×1024 — e.g.
  97.1% at (QF1 68-76, QF2 86-95), 98.6% at (QF1 77-85, QF2 96), but 1.3–1.5% in the
  QF1 ≫ QF2 cells.
- Parameter estimation (Fig. 8, Section IV): "For QF2 > 75, the proposed method identifies
  the correct Q1 and (y,x) in over 98% of the images recognized as NA-JPEG irrespective of
  the image size, while for 1024×1024 images the correct identification rate is always
  greater than 96% irrespective of QF2."

**Applicability to uncompressed TIFF input:** **Inapplicable** as a localizer to Korus
TIFF, on two independent grounds. First, it needs a JPEG image with a known Q2 and a
*prior* shifted JPEG compression; on never-compressed TIFF every IPM is near-uniform by
construction and H∞ never drops below T1. Second, even given a JPEG history, this paper
produces one global decision per image, not a map — the authors say localization is future
work in the Conclusions ("we are currently studying the possibility of using the estimated
parameters … for the automatic localization of tampered regions"). That follow-up is
`bianchi2012_blockgrained` in this same folder.

**Relevance to our training-free localizer:** Its value to us is as a *primitive*, not as
a detector: the IPM idea — evaluate the DC histogram's Fourier magnitude at
reciprocal-integer frequencies `e^{−j2πk/Q}` across all 64 grid shifts, normalize into a
map, and score its peakiness with min-entropy — is a clean, cheap, entirely training-free
way to ask "does this image (or this window) sit on a quantization lattice, and at what
shift?". Computed on sliding windows rather than the whole image it becomes a localization
cue, which is exactly the extension the block-grained paper pursued. It also supplies the
grid-shift and Q1 estimates that the block-grained likelihood map needs as inputs. If we
add a JPEG stress condition, implementing IPM first gives us grid-shift estimation almost
for free.

**Limitations the authors themselves state:** cannot distinguish a singly compressed image
from an aligned doubly compressed one (footnote 1); NA-JPEG is difficult to detect when
Q1 < Q2 (Section III); the case Q1 = 1 is undetectable and was excluded from the
experiments (Section IV); the Q1 = Q2 case requires the separate DIPM machinery and even
then relies on an empirical symmetry assumption; it produces no tampering localization
(Conclusions).

---

## iakovidou2018

**Full citation:** Chryssanthi Iakovidou, Markos Zampoglou, Symeon Papadopoulos, Yiannis
Kompatsiaris (Information Technologies Institute, CERTH, Thessaloniki), "Content-aware
Detection of JPEG Grid Inconsistencies for Intuitive Image Forensics". The local PDF is
the author preprint: its footer reads "Preprint submitted to journal of visual
communication and image representation May 14, 2018". No DOI appears in the PDF —
`not verified from retrieved text`. Code is stated to be released in the MKLab Image
Forensics Toolbox (`https://github.com/MKLab-ITI/image-forensics`, Section 1).

**Local file:** `references/papers/iakovidou2018_cagi.pdf` (41 pages), text extraction:
clean (figure-embedded text from the Fig. 5 pipeline diagram is interleaved awkwardly on
pages 13–14, and the Fig. 15 summary table extracts as a flat row list, but all of it is
legible).

**What the method computes:** CAGI = Content-Aware detection of Grid Inconsistencies. It
extends the Fan & de Queiroz blocking-grid detector with (a) a more robust grid-position
confidence measure K″ and (b) a content-aware filtering stage.

*Base measure (Section 3.1, from Fan & de Queiroz [3]).* Split the image into
non-overlapping 8×8 blocks; for each block compute
`Z′(i,j) = |A − B − C + D|` and `Z″(i,j) = |E − F − G + H|` (Eq. 1), where A–D are pixels
sampled from the block interior and E–H straddle the block boundary (Fig. 1). Form the two
normalized histograms HI (of Z′) and HII (of Z″) over the image and compute
`K = Σ_{m=1}^{M} |HI(m) − HII(m)|` (Eq. 2), K ∈ [0,2]. Fan et al. "empirically found that
for pixel values ranging from 0 to 1, K > 0.25 is an indicator of successful grid
detection". Grid position (GP) is named by the coordinates of pixel A in block(1,1); the
default for an untouched JPEG is GP(4,4) (Section 3.1). (Note: Section 3.2 says the
alignment "will in most cases be located at position (8,8)" — the paper is internally
inconsistent about this convention; flagging rather than resolving it.)

*Robust grid position (Section 3.1).* Instead of taking argmax K, exploit the expected
spatial pattern of K over shifts: if K is high at (i,j) it must also be high at
(i+4, j+4) and low at (i+4, j) and (i, j+4). This gives
`K′(i,j) = [ K(i,j) + K(i+4,j+4) − K(i+4,j) − K(i,j+4) ] / 4` (Eq. 3), K′ ∈ [0,1], and
reduces the search from 64 to 16 candidate positions. Separately, retain a binary "sign"
per position: 1 if Z′ has more low values than Z″ (A interior, E on the boundary), 0
otherwise. `S ∈ [0,1]` is the fraction of the 16 positions whose sign matches the expected
pattern for a candidate grid. Final confidence `K″ = ½(K′ + S) ∈ [0,1]` (Eq. 4).
Per-block: `K_block(n) = Z′(n) − Z″(n)` (Eq. 5) substitutes for Eq. (2), and the same K′/S
machinery yields `K″_block(n)`.

*Localization maps (Section 3.2).* For each block, over the 16 candidate grid positions,
`fit(x) = H[K″_block(i_x, j_x)] · K″_block(i_x, j_x)` (Eq. 6, H = Heaviside step) and
`fitBLK(n) = (1/16) Σ_{x=1}^{16} fit(x)` (Eq. 7). Two maps are formed: the mean response
over all 16 alignments, and the response of the best-fitting alignment.
- **Heat Map A** = (best-grid response) − (mean-over-all-grids response). Rationale: a
  region with low response for *all* alignments is content-driven, not misaligned, so
  subtracting the mean suppresses it. High values in Heat Map A = candidate tampering.
- **Heat Map B** = inverted best-fitting-grid map, used later as a weighting factor.
Both are mean-filtered with a small window.

*Content-aware filtering (Section 3.3).* Four content classes are handled:
- **Help Map 1** (homogeneous): blocks scoring consistently near-zero over all 16 GPs.
- **Help Map 3** (exposure): convert to HSV; blocks with mean V above 95% of the channel
  maximum are over-exposed, below 5% under-exposed ("we empirically found").
- **Help Map 2** (soft vs strong edges): resize the image so the largest dimension is 960
  px (the smaller scaled near-proportionately to a multiple of 8), tile into 8×8 blocks,
  and convolve each with 58 binary edge kernels adapted from [33] — 12 orientations at 15°
  increments, with instances covering all 2-pixel shifts of the edge within the block.
  Confidence `Cz = | Σ_i Σ_j B(i,j) · k̄_z(i,j) [ 1/Mw − 1/Mb ] | ∈ [0,1]` (Eq. 8), where
  Mw, Mb are the counts of white and black kernel pixels and k̄_z the bitwise NOR of the
  kernel. Keep the highest Cz per block. Thresholding is *adaptive and hierarchical*: the
  image is split into 6 first-level regions A–F, each into 6 sub-regions; the threshold for
  a sub-region is `T′_a1 = max(T_a1, T_A, T_img)`, i.e. the largest of its own mean
  confidence, its parent region's mean, and the whole-image mean (Fig. 6).

*Final output (Section 3.4).* In Heat Map A, mark every block below the map mean as
untampered; also mark homogeneous (Help Map 1) and over/under-exposed (Help Map 3) blocks
as untampered. Weight the result by Heat Map B. Then replace all marked blocks with the
*mean value of the soft-edge blocks that are not homogeneous* — chosen so the map stays
readable rather than near-binary — and mean-filter to get the output.

*inv-CAGI (Section 3.5).* When the splice is the only region carrying a grid (e.g. a JPEG
splice into a lossless host saved losslessly, or QFf > QFh > QFs), discontinuities appear
as *high* rather than low K″. The complementary branch filters the blocks *above* the Heat
Map A mean instead of below, and is presented to the user alongside the normal output.

**Assumptions and preconditions:** the image must have a JPEG compression somewhere in its
past, but need not be delivered as a JPEG file — "The algorithm does not require metadata,
JPEG compression parameters, or prior knowledge on the history of the image, nor does it
require that the image is in raw format taken directly from the camera. It can operate on
any file format, provided it has been compressed as JPEG in its past" (Section 2). It
targets splices that **break grid alignment**, either by placement or by resampling of the
spliced region (Section 1). The base direction of the effect (low response = tampered) is
assumed by default; the QF ordering cases that invert it need inv-CAGI, and the analyst
must pick between the two outputs by visual inspection (Section 3.5). No training and no
parameter selection is claimed to be needed (Section 5.4).

**Reported performance:** Section 5, three datasets (Table 2): Fontani et al. synthetic
(4,800 fake / 4,800 authentic, JPEG); First IFS-TC Forensics Challenge training set (442
fake / 1,050 authentic, PNG with likely JPEG history); Wild Web (10,646 fake / 0
authentic). Metrics (Section 4.2): KS statistic between value distributions inside and
outside the mask, `KS = max_u |C1(u) − C2(u)|` (Eq. 9) for detection; per-pixel F1 after
normalizing maps to [0,1] and sweeping the binarization threshold in 0.05 steps for
localization; "readability" = the width of the threshold range yielding at least 70% of
the method's own maximum F1.
- Summary table (Fig. 15). Fontani et al.: CAGI KS 0.70 / F1 0.40 / usable threshold range
  0.3–0.7; BLK 0.69 / 0.21 / 0.35–0.65; ADQ1 0.48 / 0.43 / 0.05–0.95; NOI3 0.45 / 0.28;
  DCT 0.53 / 0.33; inv-CAGI 0.31 / 0.19; CFA1 0.05 / 0.13.
  Challenge: CAGI 0.17 / 0.16 / 0–0.8; NOI3 0.28 / 0.18; BLK 0.21 / 0.10; DCT 0.25 / 0.11;
  ADQ1 0.13 / 0.10. Wild Web (F1 only): CAGI 0.234, inv-CAGI 0.272, DCT 0.246, NOI1 0.249,
  NOI3 0.230, BLK 0.227, ADQ1 0.209.
- Section 5.1: on the Fontani set "CAGI is overall one of the best performing methods
  together with BLK, achieving approximately 70% true positive rate at a 5% false positive
  rate".
- Detections at F1 ≥ 0.7 with unique-case counts (Table 4, Fontani): ADQ1 1810 (246
  unique), CAGI 1711 (433 unique), DCT 1114 (6), NOI3 1112 (259), BLK 578 (29). At
  F1 ≥ 0.8: ADQ1 1561 (342), CAGI 1264 (279), NOI3 849 (201).
- Challenge (Table 5, F1 ≥ 0.7): NOI3 38 (28 unique), CAGI 16 (6), BLK 8, NOI1 7, DCT 5,
  ADQ1 4.
- Wild Web cases out of 78 (Table 6, F1 ≥ 0.7): inv-CAGI 22 (3 unique), CAGI 19 (4),
  NOI3 15 (1), NOI1 12, DCT 10, ADQ1 8, BLK 7; PENS (perfect ensemble) 33. At F1 ≥ 0.8:
  inv-CAGI 13 (7 unique), CAGI 6, NOI3 6.
- Robustness (Table 7, images that scored F1 ≥ 0.7 before the transform): on Fontani,
  CAGI 1711 originally → 1616 after re-compression at QF90, 918 at QF70, but only 51 after
  95% rescale, 19 at 75%, 17 at 50%. BLK 578 → 335 → 102 → 0/0/0; ADQ1 1810 → 989 → 629 →
  0/0/0; NOI3 1112 → 946 → 551 → 15/6/1. Section 5.4: "CAGI is very robust with respect to
  recompressions. On the other hand, rescaling has a clear negative impact for all methods
  and datasets."

**Applicability to uncompressed TIFF input:** **Inapplicable** to Korus camera-native
TIFF as shipped — the entire signal is the 8-pixel-periodic weak-edge pattern left by JPEG
block quantization, and a never-compressed image has none, so K never exceeds Fan's 0.25
gate and all 16 grid responses are content noise. It is, however, the **most applicable of
the six under a JPEG stress condition**, because unlike the Bianchi and Lin methods it
needs no JPEG file, no header, no quantization matrix, and no double compression: it works
off the bitmap. INFERENCE: if our stress condition is "JPEG-compress the Korus forgeries
at some QF and re-save", CAGI-style analysis would only fire where the *spliced* content's
own grid differs from the host's — so the stress condition has to introduce that
asymmetry (e.g. compress the donor region separately, or apply a sub-8-pixel shift/rescale
to the spliced region) or there will be nothing to find. Note also Table 7: rescaling
destroys the cue, and Korus forgeries involve resampled objects.

**Relevance to our training-free localizer:** Several transferable, training-free
mechanics regardless of whether we adopt the JPEG cue itself. (1) The K′/S pattern check
(Eq. 3–4) is a good template for "don't trust an argmax over shifts; check that the whole
response pattern has the shape the physics predicts" — our current arg-min-over-qualities
cue does exactly the naive argmax thing it warns against. (2) Heat Map A — subtracting the
mean response over *all* hypotheses from the best-hypothesis response — is a cheap,
general content-normalization we can reuse in any hypothesis-sweep cue. (3) The Help Maps
(homogeneous, over/under-exposed, strong-edge suppression) are a directly reusable
suspicion-map post-processing stage: these three content classes produce false positives
in essentially every low-level forensic cue, not just this one. (4) Their evaluation
protocol — F1 swept over binarization thresholds, plus the width of the high-F1 threshold
range as a "readability" measure — is a better fit for our per-pixel map than a single
fixed-threshold F1.

**Limitations the authors themselves state:** Section 3.5 — the default output direction
is wrong for certain QF orderings (QFf > QFh > QFs, and lossless-host cases), which is why
inv-CAGI exists, and the analyst must choose between the two outputs by inspection.
Section 5.1 — Class 3 (splice aligned to the final grid) is "the most challenging for
CAGI", and Class 1 detection degrades as the final compression QF rises because the host's
artifacts become too light. Section 5.4 and Table 7 — rescaling has a clear negative
impact; also the authors note that on the Challenge dataset KS success rates are near
chance, so "analysis on the detection robustness can unfortunately not be reliable" there.
Section 6 positions the method as a component of an ensemble rather than a standalone
answer.

---

## ye2007

**Full citation:** Shuiming Ye, Qibin Sun, Ee-Chien Chang, "Detecting Digital Image
Forgeries by Measuring Inconsistencies of Blocking Artifact", ICME 2007 (the page footer
reads "1-4244-1017-7/07/$25.00 ©2007 IEEE  ICME 2007"; page numbers 12–15). No DOI in the
PDF — `not verified from retrieved text`.

**Local file:** `references/papers/ye2007_blocking.pdf` (4 pages), text extraction:
partial — the prose is clean but the two displayed equations come out glyph-scrambled
(Eq. 1 extracts as `64 1 ()() | ( ) ( ) ( )| ()k DkBi Dk Qkr o u n d Qk ¦`). I reconstructed
Eq. (1) from the surrounding definitions in the same paragraph, which name every symbol;
treat my reconstruction as *inferred formatting of a scrambled line*, not verbatim text.

**What the method computes:**
1. **Blocking artifact measure per block** (Section 2.1, Eq. 1). Reconstructed form:
   `B(i) = Σ_{k=1}^{64} | D(k) − Q(k) · round( D(k)/Q(k) ) |`
   where D(k) is the DCT coefficient at position k of test block i and Q(1:64) is the
   estimated quantization table. In words (verbatim from the text): B(i) is "the estimated
   blocking artifact for the testing block i", D(k) "the DCT coefficient at position k",
   and Q "the estimated DCT quantization table". So B(i) is the total L1 distance of the
   block's DCT coefficients from the quantization lattice.
2. **Image-level measure** (Eq. 2): `BAM = (1/N) Σ_i B(i)`, N the number of blocks.
3. **Fast quantization table estimation** (Section 2.2), the paper's speed contribution.
   Procedure as listed verbatim: "(1) Calculating DCT coefficients of each 8×8 image
   block; (2) Calculating the power spectrum (P) of the histogram of DCT coefficients for
   each of the 64 frequencies; (3) Calculating the second derivative of P, and then
   low-pass filtering it; (4) Calculating the local minimum number (Num) of the filtered
   second derivative of P; (4) [sic] the estimated quantization step of the DCT frequency
   is estimated as Num+1." The justification: at a local maximum f′(x)=0, f″(x)<0 and f″
   is a local minimum; the number of negative local minima of the filtered second
   derivative "is found to be equal to (Q(i)−1)". Positive values of the second derivative
   are eliminated before counting. Only the **first 32 DCT frequencies** are used in the
   blocking artifact estimation, because high-frequency coefficients are all quantized to
   zero at large steps (Section 2.2).
4. **Forensic use** (Section 2.3): "we first segment it into areas and then check the
   blocking artifact consistency of these segments. Suspicious area is selected for
   evaluation, the other areas are used to estimate the quantization table, and the BAM of
   the image is calculated based on the estimated table." Inconsistency across segments →
   suspicious.
5. If the tampered image was further JPEG compressed, the primary quantization table is
   first estimated with Lukáš & Fridrich's method [11] and used for the BAM (Section 3).

**Assumptions and preconditions:** input must be a JPEG-compressed image whose
quantization table can be recovered from DCT histogram periodicity; the analyst must
supply a segmentation into a suspect area and a clean area, since the clean area is what
estimates Q (Section 2.3). Grid alignment is assumed to be the standard 8×8 lattice from
the image origin — no shift search is described. The claimed inconsistency sources are
different quantization tables between sources, but also block mismatching, resampling and
local filtering (Section 3).

**Reported performance:** no ROC, accuracy or detection rate is reported anywhere in the
extracted text — only timings and per-image BAM values.
- Timing (Table 2), Lena 512×512, Visual C++ 6.0 on a Dell Dimension 8250 (3060 MHz CPU,
  512 MB, Windows XP), quality factors 100/90/80/70/60/50: proposed 241/227/228/225/222/228
  ms versus the MLE-based method's 15091/14957/14893/14950/14828/14737 ms.
- Table 1 shows correctly estimated quantization tables for the finest-quality default of
  a Nikon Coolpix5400 and a Sony P10.
- Section 3: "We created 500 forgeries randomly spliced from 500 untouched photos", with
  results shown only as a scatter of measures in Fig. 3 — the separation is asserted
  visually, no numeric accuracy. Individual examples: Fig. 4(a) BAM = 2136.5, "much larger
  than the maximum of the untouched images shown in Fig. 3"; its JPEG-recompressed version
  (quality factor 75) BAM = 97.1; Fig. 5 (splice between two photos from the same Nikon
  Coolpix5400) BAM = 45.4; Fig. 6 face-skin-optimization forgery BAM = 46.6 versus 5.9 for
  the original.
Detection accuracy on the 500-forgery set: `not verified from retrieved text`.

**Applicability to uncompressed TIFF input:** **Inapplicable** to Korus camera-native
TIFF. The statistic is literally the residual to the quantization lattice, so it needs a
quantization table to exist. INFERENCE: on a never-compressed image the histogram-power-
spectrum estimator would return Q(i) = 1 for every frequency (no periodicity → no negative
local minima → Num = 0 → Q = 1), and with Q(k) = 1 the residual
`|D(k) − round(D(k))|` is only the fractional part of the DCT coefficients — a
content-driven quantity with no forensic meaning. Under a JPEG stress condition it becomes
usable in principle, but note that Farid's paper (also in this folder) criticizes exactly
this dependency: "our approach does not require an estimate of the DCT quantization from
an assumed original part of the image. Estimating the quantization from only the
underlying DCT coefficients is both computationally non-trivial, and prone to some
estimation error" (farid2009, Section I). Lin et al. add that Ye's method "needs user
assistance to segment an image into correct regions" (lin2009, Section 1.1).

**Relevance to our training-free localizer:** This is the honest ancestor of our current
"8×8 blocks whose high-frequency DCT energy deviates from the image median" cue, and the
comparison is instructive: Ye's B(i) measures distance from a *quantization lattice*
estimated from the image, which is a compression-history statistic; ours measures raw
high-frequency energy against a global median, which is a texture statistic and carries no
compression information at all. If we keep a per-block DCT cue for a JPEG stress
condition, B(i) with a properly estimated Q — and restricted to the first 32 frequencies
as the paper does — is the minimum viable honest replacement. The histogram-power-spectrum
Q estimator (second derivative, low-pass, count negative minima, add one) is cheap,
training-free and CPU-friendly, and is worth having as a standalone utility even if only
to decide whether an input has a JPEG history at all. The requirement for a manual
clean/suspect segmentation is the part we cannot adopt as-is.

**Limitations the authors themselves state:** the paper is short and largely
self-congratulatory; Section 4 only says "Further work could be done on discovery of other
image quality inconsistency measure." A limitation is acknowledged indirectly in
Section 2.2 — "the estimation errors of 64 quantization steps grow when quantization
factor decreases … high frequency DCT coefficients would be all zero when quantized by
large step", which is why only the first 32 frequencies are used. No explicit statement of
failure modes otherwise: `not verified from retrieved text`.

---

## farid2009

**Full citation:** Hany Farid, "Exposing Digital Forgeries from JPEG Ghosts". The PDF is
an author manuscript: the byline is "Hany Farid, Member, IEEE" with a Dartmouth College
affiliation footnote, and **no venue, volume, pages or DOI are printed in this PDF** —
`not verified from retrieved text`. Both Bianchi PDFs in this folder cite it as *IEEE
Trans. Inf. Forensics and Security*, vol. 4, no. 1, pp. 154–160, Mar. 2009.

**Local file:** `references/papers/farid2009_jpeg_ghosts.pdf` (9 pages), text extraction:
clean.

**What the method computes:**
1. Theory (Section II). JPEG quantization is `ĉ = round(c/q)` (Eq. 1). If coefficients c1
   were quantized by q1 and are re-quantized by q2, the difference between c1 and c2 is
   minimal at q2 = q1 and grows for both q2 > q1 (increasing sparsity) and q2 < q1 (value
   shifts). If the coefficients were quantized by q0 first and then by q1 < q0, a **second
   local minimum appears at q2 = q0** — this is the JPEG ghost, evidence of an earlier,
   lower-quality compression. Fig. 1 illustrates with q0 = 23, q1 = 17, q2 swept over
   [1,30]. Caveat noted in the same section: if q1 is not prime, spurious minima appear at
   integer multiples of q1.
2. Pixel-domain difference rather than per-frequency (Section II) — precisely to avoid the
   integer-multiple ambiguity, since it would require all 192 quantization values to be
   integer multiples of each other, "an unlikely scenario":
   `d(x,y,q) = (1/3) Σ_{i=1}^{3} [ f(x,y,i) − f_q(x,y,i) ]²` (Eq. 2), where f is the RGB
   image and f_q is f re-compressed at quality q. Trivially adapted to grayscale by using a
   single channel (footnote 2).
3. Spatial averaging over a b × b region (Eq. 3):
   `δ(x,y,q) = (1/3) Σ_i (1/b²) Σ_{bx=0}^{b−1} Σ_{by=0}^{b−1} [ f(x+bx, y+by, i) − f_q(x+bx, y+by, i) ]²`.
4. Normalization **across q** into [0,1] (Eq. 4):
   `d(x,y,q) = ( δ(x,y,q) − min_q δ(x,y,q) ) / ( max_q δ(x,y,q) − min_q δ(x,y,q) )`.
   This step is explicitly there to cancel content dependence: without it, "a region with
   small amounts of high spatial frequency content (e.g., a mostly uniform sky) will have
   a lower difference as compared to a highly textured region (e.g., grass)" (Section II).
5. Statistical test (Eq. 5): the two-sample Kolmogorov–Smirnov statistic
   `k = max_u | C1(u) − C2(u) |`, where C1 and C2 are the cumulative distributions of
   d(x,y,q) inside and outside a specified region, **computed separately for each q**. If
   k exceeds a threshold for any q, the image is flagged.
6. Grid alignment (Section II): because a misaligned splice destroys the ghost, the image
   is shifted to each of the 64 possible offsets (0–7 pixels horizontally and vertically)
   before re-saving at each quality. In the real-forgery examples the shift yielding the
   largest KS statistic is selected (Section III).
7. Practical exclusion (Section III): b × b regions with average intensity variance below
   2.5 gray values are dropped from the KS computation, because saturated and uniform
   regions barely change with q; these are rendered mid-level gray in the figures.

**Assumptions and preconditions:** the tampered region must have been compressed at a
**lower** quality than the rest of the image (stated as *the* disadvantage in Section IV);
some JPEG history must exist. It does **not** need the quantization table to be estimated,
does not need the image cropped, and detects local rather than global tampering (Section I
comparisons). The quality scale used for re-saving must roughly match the one that created
the image; Section II argues small mismatches matter little because the difference is
averaged over all spatial frequencies. The block lattice must be aligned, which is what the
64-offset search handles. The paper notes MPEG-style quantization tables that are scaled
multiples of one another may confound ghost detection (footnote 1).

**Reported performance:** Section III — 1,000 uncompressed TIFF images from the
Uncompressed Colour Image Database (UCID), each 512×384. A central region (50×50 to
200×200) was cut, saved at quality Q0, re-inserted, and the whole image saved at Q1; Q1
random in [40,90], Q1 − Q0 in [0,25] with Q0 ≤ Q1. Testing re-saved at Q2 from 30 to 90 in
steps of 1, with **b = 16**, and the threshold set for under 1% false positives.
- Table I (detection accuracy %, rows = tampered region size, columns = Q1 − Q0 of
  0/5/10/15/20/25):
  200×200 → 99.2 / 14.8 / 52.6 / 88.1 / 93.8 / 99.9;
  150×150 → 99.2 / 14.1 / 48.5 / 83.9 / 91.9 / 99.8;
  100×100 → 99.1 / 12.6 / 44.1 / 79.5 / 91.1 / 99.8;
  50×50 → 99.3 / 5.4 / 27.9 / 58.8 / 77.8 / 97.7.
  (The Q1 − Q0 = 0 column is the untampered case, so ≥99% there is the <1% false-positive
  rate, not a detection rate.)
- Section III: "the detection accuracy is above 90% for quality differences larger than 20
  and for tampered regions larger than 100 × 100 pixels."
- Post-processing robustness (Section III): after blurring, sharpening or histogram
  equalizing the inserted region, "For tampered regions of size 100 × 100, the detection
  improved slightly (with the same false positive rate of 1%)."
- Real forgeries created in Photoshop CS3 (12-point quality scale) and re-compressed with
  MatLab's 100-point scale: maximal KS 0.92 for the flying car (splice quality 4/12, final
  10/12), 0.84 for the dolphin (5/12, final 8/12), 0.94 for the jet (6/12, final 10/12).
  Fig. 7 demonstrates the ghost "largely vanishes when the alignment is incorrect".
- ROC curves are in Fig. 4 for (150×150, Δ15) and (100×100, Δ10) with false-positive
  markers at 10%, 5% and 1%; the numeric points on those curves are
  `not verified from retrieved text`.

**Applicability to uncompressed TIFF input:** **Only under a JPEG stress condition, and
even then only a specific one.** Worth being precise here, because the UCID protocol
superficially looks like ours: Farid also starts from uncompressed TIFF, but the
*manipulation itself* inserts a region that was separately JPEG-compressed at Q0 — the
ghost is that region's own prior compression. Korus forgeries are camera-native TIFF
throughout, so both regions have identical (null) compression history and there is no
lower-quality region to ghost. Re-compressing a whole Korus image once does not help
either: every pixel then shares one history, the d(x,y,q) surface has one global minimum
at the saved quality, and there is nothing spatially distinct to find. INFERENCE: the only
stress condition under which JPEG ghosts can fire on Korus-style data is one where we
compress the *donor* content at a lower quality before splicing (or, equivalently, build a
new synthetic condition), which is a change to the data, not to the detector.

**Relevance to our training-free localizer:** This is the paper that our first weak cue is
a corrupted version of, and the differences are the fix list. Farid does **not** take an
arg-min over qualities and score its spatial variance; he (a) keeps the whole difference
*surface* d(x,y,q) rather than collapsing it to an argmin, (b) spatially averages over
b × b with b = 16 before anything else (Eq. 3), (c) normalizes per-pixel *across q* into
[0,1] (Eq. 4) — which is the actual content-normalization step, and the one our cue is
missing — and (d) tests each q separately with a two-sample KS statistic between regions
rather than using a variance heuristic. He also (e) excludes low-variance blocks
(variance < 2.5 gray levels) and (f) searches all 64 lattice offsets. Points (a)–(c) and
(e) are cheap, training-free, and would apply almost unchanged to any recompression-sweep
cue we keep. The KS test (Eq. 5) is also the same statistic CAGI adopts for its detection
evaluation, so implementing it once serves both.

**Limitations the authors themselves state:** Section IV — "The disadvantage of this
approach is that it is only effective when the tampered region is of lower quality than
the image into which it was inserted." Section II — different cameras and editors use
different quality scales and quantization tables, which cannot always be matched;
misalignment of the tampered region relative to the original 8×8 lattice can destroy the
ghost (mitigated by the 64-offset search); multiple minima arise when quantization values
are integer multiples (and MPEG tables, being scaled multiples, may confound detection,
footnote 1). Section III — saturated and near-uniform regions give unreliable statistics
and must be excluded. Section IV — no automatic detection algorithm was implemented, since
the ghosts were judged visually salient.

---

## Reading ledger

| Paper | Pages | Extraction quality | Notes |
|---|---|---|---|
| lin2009 (`lin2009_dct.pdf`) | 10 | clean | "ARTICLE IN PRESS" proof; DOI on p.1, volume/pages blank. Math glyphs substituted (σ → `/afii9846`, ρ → `/afii9825`); Eq. 1 and Sections 2.2–3.3 legible. Per-(Q1,Q2) rates exist only as Fig. 10 curves, not tables. |
| bianchi2012_blockgrained | 16 | clean | Politecnico di Torino repository copy; p.1 is a cover sheet, article on pp. 2–16. All equations, algorithms and Tables II–IX readable. One ambiguity: the `n′_Q(0)` correction using RZ (Section III-D) extracts without clear super/subscript. |
| bianchi2012_ipm | 7 | clean | Same repository format; p.1 cover sheet. Equations 5–10, Algorithm 1 and Tables I–IV all readable. Whole-image detector, not a localizer. |
| iakovidou2018 (CAGI) | 41 | clean | Author preprint dated May 14 2018, submitted to J. Vis. Commun. Image Represent.; no DOI in the file. Fig. 5 pipeline text interleaves awkwardly on pp. 13–14 and Fig. 15's summary table extracts as a flat row list, but all values were recoverable. Internal inconsistency noted: default grid position given as (4,4) in Section 3.1 and as (8,8) in Section 3.2. |
| ye2007 | 4 | partial | Prose clean; both displayed equations glyph-scrambled. Eq. (1) reconstructed from the symbol definitions in the same paragraph and flagged as such. No detection-accuracy figures are reported anywhere in the paper — only timings and individual BAM values. |
| farid2009 | 9 | clean | Author manuscript: no venue, volume, pages or DOI printed in the file (other PDFs in this folder cite it as IEEE TIFS 4(1):154–160, 2009). Equations 1–5, Table I and all parameters (b = 16, variance floor 2.5, 64 offsets) recovered. Fig. 4 ROC values not extractable. |

### Cross-cutting conclusion for the Korus benchmark

All six methods are JPEG-artifact methods, and **none of them applies to Korus
camera-native uncompressed TIFF as shipped.** Three of them (lin2009,
bianchi2012_blockgrained, bianchi2012_ipm) additionally require a *double* JPEG history
and read quantization parameters from the JPEG file itself, so they are the furthest from
usable. ye2007 needs an estimable quantization table. farid2009 needs the spliced region
to carry its own lower-quality prior compression. iakovidou2018 (CAGI) is the only one
that runs off the bitmap alone with no header, no quantization matrix and no double
compression — so it is the cheapest to add if we introduce a JPEG stress condition, though
it still needs a *grid* to exist and its own Table 7 shows rescaling destroys the cue.

INFERENCE: for the Korus benchmark proper, the honest position is that the JPEG family
contributes nothing and the existing two weak cues should be removed rather than replaced;
they currently fire on texture, not on compression history. If a JPEG stress condition is
added, the reimplementation order that maximizes value per line of code is:
CAGI's K″ grid-consistency map (bitmap-only, no metadata), then Farid's normalized ghost
surface with the KS test (simple, and it repairs our existing arg-min cue), then the
Bianchi block-grained likelihood map (most accurate, most work, needs a JPEG file).
