# Literature review

This review supports the research question: **Can a small combination of
complementary classical forensic cues improve tampering detection and
localization over the strongest individual cue?**

## Candidate cue families

| Cue family | Evidence source | Main use | Main limitation | Role in this project |
|---|---|---|---|---|
| Duplicated content | Local feature correspondence and geometric consistency | Copy-move detection and localization | Weak texture, repeated patterns, and strong transforms can cause missed or false matches | Primary candidate |
| Compression history | JPEG ghost or double-compression traces | Splicing and recompression evidence | Requires suitable JPEG history and is sensitive to quality factor and later recompression | Primary candidate |
| Geometric resampling | Periodic interpolation traces | Resized, rotated, or warped inserted regions | No trace is available for every edit; natural structure can confuse the detector | Primary candidate |
| JPEG block-grid inconsistency | Local 8x8 quantization/block statistics | Block-level localization of JPEG inconsistencies | Shares assumptions with JPEG-history cues and may be redundant | Ablation candidate |
| Camera/source noise | PRNU or sensor-pattern inconsistency | Source-camera mismatch and splice evidence | Needs reference images from the camera; poor fit for a general course dataset | Excluded unless data become available |

## Reference analyses

### `fridrich2003`

**J. Fridrich, D. Soukal, and J. Lukáš, “Detection of Copy-Move Forgery in
Digital Images,” DFRWS, 2003.**

The paper establishes duplicated-content detection as a forensic problem. Its
block/keypoint matching view motivates a spatial suspicion map rather than an
image-level decision only. It also shows why repeated textures and geometric
changes create false or missed matches. We use it to define the copy-move
baseline and to require manipulation-specific evaluation.

### `amerini2011`

**I. Amerini, L. Ballan, R. Caldelli, A. Del Bimbo, and G. Serra, “A SIFT-Based
Forensic Method for Copy-Move Attack Detection and Transformation Recovery,”
IEEE TIFS, 2011. DOI: `10.1109/TIFS.2011.2129512`.**

The method combines SIFT correspondences with geometric transformation
recovery. This supports using SIFT matches only after geometric verification.
Its computational cost and dependence on detectable keypoints are important
failure cases for the proposed pipeline.

### `christlein2012`

**V. Christlein, C. Riess, J. Jordan, C. Riess, and E. Angelopoulou, “An
Evaluation of Popular Copy-Move Forgery Detection Approaches,” IEEE TIFS, 2012,
1841--1854. DOI: `10.1109/TIFS.2012.2218597`.**

This benchmark shows that copy-move performance varies with image content and
attack transformation. It directly motivates attack-stratified reporting,
paired comparisons, and ablations instead of a single aggregate score.

### `farid2009`

**H. Farid, “Exposing Digital Forgeries From JPEG Ghosts,” IEEE TIFS, 2009,
154--160. DOI: `10.1109/TIFS.2008.2012215`.**

The method searches for local recompression inconsistencies by testing candidate
JPEG quality factors. It supplies a compression-history cue that is different
from duplicated-content evidence. It is not a universal detector: the cue can
weaken after uniform recompression, and it assumes useful JPEG history.

### `bianchi2012`

**T. Bianchi and A. Piva, “Image Forgery Localization via Block-Grained Analysis
of JPEG Artifacts,” IEEE TIFS, 2012, 1003--1017. DOI:
`10.1109/TIFS.2012.2187516`.**

The paper models block-level JPEG artifact inconsistencies for localization.
It provides the rationale for the block-grid candidate. Because both this cue
and JPEG ghosts depend on compression history, we will test whether the block
cue adds error reduction beyond the JPEG-history cue.

### `popescu2005`

**A. C. Popescu and H. Farid, “Exposing Digital Forgeries by Detecting Traces of
Resampling,” IEEE TSP, 2005, 758--767. DOI: `10.1109/TSP.2004.839932`.**

The method detects periodic correlations caused by interpolation. It is a
plausible complementary cue for resized or rotated insertions because its
evidence domain is geometric rather than compression-based. It must be treated
as conditional: edits without resampling traces should not be expected to
trigger it.

### `fan2003`

**Z. Fan and R. L. de Queiroz, “Identification of Bitmap Compression History:
JPEG Detection and Quantizer Estimation,” IEEE TIP, 2003, 230--235. DOI:
`10.1109/TIP.2002.807361`.**

This work supports estimating compression history and motivates explicit input
format and quality-factor metadata in the evaluation. It helps define when a
JPEG-history cue is applicable and when the pipeline must report a missing cue.

### `wang2022`

**M. Wang, X. Fu, J. Liu, and Z.-J. Zha, “JPEG Compression-aware Image Forgery
Localization,” ACM Multimedia, 2022, 5871--5879. DOI:
`10.1145/3503161.3547749`.**

This recent work reinforces that JPEG compression changes localization behavior
and should be treated as part of the experimental condition. It motivates our
recompression stress tests and our decision not to interpret normalized scores
as calibrated probabilities.

### `verma2023`

**V. Verma, D. Singh, and N. Khanna, “Block-level Double JPEG Compression
Detection for Image Forgery Localization,” Multimedia Tools and Applications,
2023, 9949--9971. DOI: `10.1007/s11042-023-15942-5`.**

This paper is a recent block-level compression-history reference. It supports
including a block-based candidate in the ablation while also strengthening the
case that block-grid and JPEG-ghost evidence may overlap.

### `qazi2013`

**T. Qazi, K. Hayat, S. A. Khan, and S. A. Madani, “Survey on Blind Image
Forgery Detection,” IET Image Processing, 2013. DOI: `10.1049/iet-ipr.2012.0388`.**

The survey organizes passive forensic cues by the traces they exploit. It is
used for terminology, scope boundaries, and a balanced discussion of detector
assumptions.

## Methodological consequences

1. The candidate pool should span distinct evidence domains rather than add
   several similar JPEG statistics by default.
2. The primary experiment should compare every candidate, every pair, and the
   selected subset against the strongest single cue.
3. Complementarity should be defined by incremental error reduction and
   confidence intervals, not by visual overlap between heatmaps.
4. Fusion weights, map thresholds, and morphological settings must be chosen
   on validation data only.
5. The final test must be stratified by manipulation type and stress condition.
6. The paper must report failures caused by missing JPEG history, weak keypoint
   texture, absent resampling traces, and uniform recompression.
