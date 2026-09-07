# Copy-move forgery detection - literature notes

Scope: sourcing a replacement for our SIFT + ratio-test + RANSAC + convex-hull
copy-move detector. Emphasis throughout on (a) how the final binary mask is
produced from matches, (b) source-vs-destination labelling conventions, and
(c) cost at 1920x1080.

Rules used while writing this file: every number carries the place it was read.
Anything not seen in retrieved text is written as `not verified from retrieved text`.
My own reasoning is prefixed `INFERENCE:`.

---

## wen2016

**Full citation:** Bihan Wen, Ye Zhu, Ramanathan Subramanian, Tian-Tsong Ng, Xuanjing Shen, Stefan Winkler, "COVERAGE - A Novel Database for Copy-Move Forgery Detection", IEEE International Conference on Image Processing (ICIP), 2016. DOI not printed in the retrieved PDF.
**Retrieval:** Local PDF `references/papers/wen2016_coverage.pdf` (5 pp), extraction clean.

**What the method computes:** This is a *database* paper, not a detector. Contributions, all from Sections 2-3:
- 100 original-forged image pairs (Sec. 1 and Table 1). Originals shot on an "Iphone 6 front camera" (Sec. 2), a region of interest containing at least two similar-but-genuine objects (SGOs) cropped from each, stored lossless TIFF; forgeries made in Photoshop CS4, also lossless TIFF (Sec. 2).
- Average image size given in Table 1 as 400 x 486 for COVERAGE, versus CoMoFoD 512 x 512, Manipulation 2305 x 3020, GRIP 1024 x 768. INFERENCE: the two-line layout of the "Average Image Size" row means the first line is width and second is height; the pairing itself is unambiguous but which of the two is width is my reading, not stated.
- Six tampering types (Sec. 2): translation; scaling by factor phi; rotation clockwise by theta; free-form (free transform); illumination change; combination. Types i-iii are labelled Simple, iv-vi Complex.
- Three forgery-quality metrics (Sec. 3): SSIM and PSNR as global similarity; fPSNR (Eq. 1), a PSNR restricted to the forged-region pixel set C_f, described as "invariant to forged region size" (Sec. 3.2); and FEA (Forgery Edge Abnormality), Eq. 2-3, the difference E_f - E_o of normalised union-of-transforms sparse-modelling errors computed on patches centred on the boundary B between C_f and its complement, with two learned unitary sparsifying transforms W_f (forged region) and W_o (background), each patch choosing whichever transform gives the smaller error (Sec. 3.3, problem P1).

**How the final mask is built:** Not applicable - no detector is proposed. The masks here are hand annotations made in Photoshop, not algorithm output (Sec. 2: "Masks corresponding to the duplicated and forged regions are annotated for all image pairs").

**Source vs destination convention:** This is the single most useful thing in the paper for us, and it is stated explicitly. COVERAGE ships **two separate masks per pair**: the duplicated (source) region and the forged (pasted) region, "respectively highlighted in green and red" (Fig. 1 caption). Sec. 1 contrasts this with the others: "CoMoFod and GRIP combine the duplicated and forged region masks in a single image without demarcation. COVERAGE explicitly specifies the duplicated and forged region masks". Table 1's "Mask" row confirms: CoMoFoD = comb, GRIP = comb, COVERAGE = both forged and duplicated ticked; the Manipulation dataset's row reads as forged-mask ticked. INFERENCE: reading Table 1's column alignment from the mangled text extraction, Manipulation appears to have a forged mask but no separate duplicated mask; treat that one cell as low-confidence. Terminology used consistently in Sec. 1: "copying an object from the duplicated region of the original ... and pasting it onto the forged region within the same image" - so *duplicated = source*, *forged = destination*.

**Computational cost:** not verified from retrieved text.

**Reported performance:** Detection here is per-image *pair discrimination* accuracy, not localisation. Methodology: "We follow the original/forged image identification methodology in [1]" (Fridrich et al. 2003), Sec. 3.1; Sec. 4 says one image was randomly selected from each pair for testing.
- Table 3, COVERAGE, All (100): SIFT 50.5%, SURF 58.6%, Dense-Field (Cozzolino 2015) 71.8%, average 60.3%.
- Table 3, other datasets: CoMoFoD (200) SIFT 77.0 / SURF 51.5 / Dense-Field 72.0 / avg 66.8; Manipulate (48) 75.0 / 58.3 / 95.8 / 76.4; GRIP (100) 71.0 / 52.0 / 82.0 / 68.3.
- Worst COVERAGE cell for dense-field is Combination tampering at 50.0% (Table 3), i.e. chance.
- Table 2: overall COVERAGE SSIM 0.94, PSNR 24.8, fPSNR 14.0, FEA 26.2%, human (VP) 69.9%, CV 60.3%. FEA correlates with human accuracy at rho = 0.89, p < 0.01 (Sec. 4); fPSNR correlates rho = -0.33 (Sec. 4).

**Relevance to replacing our SIFT+convex-hull detector:** Two things. First, it independently ranks the candidate replacement above SIFT on every dataset in Table 3 - dense-field beats SIFT on COVERAGE (71.8 vs 50.5), Manipulate (95.8 vs 75.0) and GRIP (82.0 vs 71.0), and only loses on CoMoFoD (72.0 vs 77.0). Second, it forces us to decide the source/destination question before we score anything: if a dataset's ground truth is a *combined* mask (CoMoFoD, GRIP per Sec. 1) then a detector that outputs only the pasted region is penalised on half the ground-truth area, and vice versa. Fig. 3 also shows the exact failure our detector has: on a COVERAGE original with SGOs, both SIFT and dense-field produce *more* matches between the two genuine objects than between the real duplicated/forged pair (Sec. 4), so match count alone is not evidence.

**Limitations the authors themselves state:** Sec. 3 states that the quality metrics "are intended to serve as a guide for tamper detection difficulty, and not for CMFD performance evaluation per se". Sec. 3 also calls forgery quality estimation "an open question". Sec. 5 concludes that automated CMFD methods perform poorly on COVERAGE. Dataset size is small (100 pairs) and the images are small (Table 1, 400 x 486 average) relative to our 1920x1080 benchmark.
