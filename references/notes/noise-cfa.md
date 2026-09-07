# Noise and CFA cues - retrieval notes

Session date: 2026-09-07. Every claim below was read this session from the stated
local PDF or fetched page. Anything not seen is written as
`not verified from retrieved text`. Own reasoning is prefixed `INFERENCE:`.

---

## popescu2005cfa

**Full citation:** Alin C. Popescu and Hany Farid, "Exposing Digital Forgeries in Color Filter Array Interpolated Images", 2005. Venue string and DOI are not printed on the retrieved preprint pages - `not verified from retrieved text`.
**Retrieval:** Local PDF `references/papers/popescu2005_cfa.pdf` (20 pp), extraction clean (pypdf, 50417 chars, all 20 pages; math flattens but is readable).

**What the method computes:**

1. *Model.* Section III: assume each interpolated pixel is a weighted sum of its neighbours within a single colour channel. Inter-channel correlations are explicitly ignored - "we ignore these inter-channel correlations and treat each color channel independently" (Section III). Section III also gives the exact bilinear identities for the red channel of a Bayer array (Eq. 44-46): `R(2x+1,2y) = R(2x+1,2y-1)/2 + R(2x+1,2y+1)/2` (horizontal), `R(2x,2y+1)` from the two vertical neighbours, `R(2x,2y)` = mean of the four diagonal neighbours.
2. *Two-component mixture.* Section III-A. Each sample of a channel `f(x,y)` belongs to M1 (linearly correlated with its neighbours, Eq. 47: `f(x,y) = sum_{u,v=-N..N} alpha_{u,v} f(x+u,y+v) + n(x,y)`, with `alpha_{0,0}=0` and `n` iid zero-mean Gaussian of unknown variance sigma^2) or to M2, an outlier process modelled by a **uniform** density equal to the inverse of the range of `f` (Section III-A).
3. *E-step.* Eq. 48, Bayes rule with **equal priors 1/2** for the two models. The M1 likelihood is Eq. 49, a Gaussian in the prediction residual. Appendix A gives the runnable form: residual `r(x,y) = |f(x,y) - sum alpha^{(n)}_{u,v} f(x+u,y+v)|`; conditional `P(x,y) = 1/(sigma_n sqrt(2 pi)) exp[-r^2(x,y)/(2 sigma_n^2)]`; posterior `w(x,y) = P(x,y) / (P(x,y) + p0)`.
4. *M-step.* Weighted least squares, Eq. 50, weights `w(x,y)` = the E-step posteriors. Differentiating (Eq. 51-54) gives the normal equations `sum_{u,v} alpha_{u,v} ( sum_{x,y} w(x,y) f(x+s,y+t) f(x+u,y+v) ) = sum_{x,y} w(x,y) f(x+s,y+t) f(x,y)` - one equation per coefficient `alpha_{s,t}`, solved as a linear system. Variance update (Appendix A): `sigma_{n+1} = ( sum_{x,y} w(x,y) r^2(x,y) / sum_{x,y} w(x,y) )^{1/2}`.
5. *Initialisation and stopping.* Appendix A: `alpha^{(0)}` chosen randomly; `N` and `sigma_0` chosen by hand; `p0` = 1 over the size of the range of `f`. Iterate until `sum_{u,v} |alpha^{(n)}_{u,v} - alpha^{(n-1)}_{u,v}| < epsilon`.
6. *Parameters actually used.* Section IV: "The parameters of the EM algorithm were: N = 1, sigma_0 = 0.0075, and p0 = 1/256." N=1 is a 3x3 neighbourhood, so 8 free coefficients per channel and 24 across three channels (Section IV).
7. *Decision statistic.* Section IV-B. Build a **synthetic** binary map per channel from the known CFA lattice (Eq. 55: `s_g(x,y) = 0` where `S(x,y)` is a green sample, 1 otherwise; analogous for red and blue). Fourier transform both the estimated posterior map `p_g` and the synthetic map `s_g`, then score `M(p_g,s_g) = sum_{wx,wy} |P_g(wx,wy)| * |S_g(wx,wy)|` (Eq. 56, phase-insensitive). Threshold per channel, set empirically for 0% false positives. An image or window is called CFA-interpolated if **at least one** of the three channels scores above threshold, tampered if all three fall below (Section IV-B).
8. *Localisation.* Sections IV-A and IV-C: the posterior map `p(x,y)` is computed for the whole image, then windows are cut out of the *map* and Fourier transformed - localisation comes from presence or absence of the periodic peaks inside a window, not from a per-pixel score. Window sizes used: 256x256 and 512x512 with 50% overlap (Section IV-C). Footnote 4: probability maps were up-sampled x2 before the FFT, which shifts the corner peaks into mid-frequencies (a display convenience, but it also explains where the peaks live).

Steps I could not see: the exact epsilon, and whether the linear system is regularised - `not verified from retrieved text`.

**Assumptions and preconditions:**
- Needs the periodic CFA correlation still present, i.e. near-camera-native output. Sections IV-A and IV-B: to *simulate* tampering the authors blur with a 3x3 binomial filter and downsample by 2 "in order to destroy the CFA periodic correlations" - so resampling/downsampling kills the cue outright.
- Assumes a known periodic CFA lattice for the synthetic reference map (Eq. 55). Their own Nikon Coolpix 950 uses a four-filter CMYG CFA (Section IV) rather than RGB Bayer.
- No reference camera and no training for the EM itself. The *thresholds* are fitted empirically on non-CFA images (Section IV-B), and the CFA-algorithm-identification experiment uses PCA/LDA training (Section IV) - but that is a separate task from tamper detection.
- JPEG: survives only at very high quality. Section IV-B: accuracies "close to 100% for quality factors greater than 96 (out of 100)", degrading gracefully below; at quality 70 smooth hue is 56% and adaptive colour plane drops to 6%.

**Reported performance:**
- Section IV-B, CFA vs non-CFA classification averaged over 100 images at 0% false positives: bilinear 100%, bicubic 100%, smooth hue 100%, median 3x3 99%, median 5x5 97%, gradient-based 100%, adaptive colour plane 97%, variable number of gradients 100%.
- Section IV-B, additive white Gaussian noise: at SNR 18 dB, 76% for adaptive colour plane and 86% for variable number of gradients.
- Section IV-B, gamma correction with exponents 0.5 to 1.5 in steps of 0.1: accuracies "either 100% or 98%".
- Section IV, CFA-algorithm identification by LDA on the 24-D alpha vector, all 28 algorithm pairs, 90/10 split over 10 random splits: average testing accuracy 97%, minimum 88% (5x5 median vs adaptive colour plane).
- Section IV-C, commercial cameras (Canon Powershot A80 JPEG, Nikon D100 TIFF, Kodak DCS 14N TIFF, three images each): with 256x256 windows all windows correct except 2 of 748 in one Kodak image; with 512x512 windows all windows correct.
- Dataset for the main experiments (Section IV): 100 images, 50 at 512x512 and 50 at 1024x1024, cropped from twenty 1600x1200 Nikon Coolpix 950 TIFFs and twenty 3034x2024 Nikon D100 RAW files.

**Relevance to our training-free localizer on Korus:** This is the right foundation for the CFA cue - the EM is fully unsupervised and CPU-only, with no classifier trained on tampering. Korus is camera-native uncompressed TIFF at 1920x1080 from four consumer DSLRs, so demosaicing traces should be intact, which is exactly the regime where Section IV-C reported near-perfect window classification on real cameras. The catch is granularity: localisation here is by FFT of 256x256 or 512x512 windows of the posterior map (Sections IV-A, IV-C), far coarser than a per-pixel suspicion map, so a finer-grained variant (Ferrara 2012) is needed on top. For the recompression stress condition this cue is close to useless below JPEG quality ~96 (Section IV-B).

**Limitations the authors themselves state:** Section V: the approach is "vulnerable to counter-attack" - a tampered image can be resampled onto a CFA and re-interpolated, though this needs knowledge of the camera's CFA pattern and interpolation algorithm. Section III: the linear model is "perhaps overly simplistic when compared to the highly non-linear nature of most CFA interpolation algorithms", and inter-channel correlations are ignored. Section IV-B: accuracy decreases with JPEG quality because compression noise destroys the correlations.

