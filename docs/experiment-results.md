# Controlled experiment record

## Pilot scope

This record reports the first reproducible controlled run after the candidate
pool and source-disjoint protocol were implemented. It is a pilot, not a claim
of benchmark superiority. The images were generated from 40 independent seeds,
encoded as JPEG at quality 88, and assigned to validation and test by a fixed
source identity rule. The pilot contains 10 images per manipulation type:
copy-move, splicing, object replacement, and geometric editing. Four images per
type were used for validation and eight per type for the held-out test.

All fusion weights, normalization percentiles, and the threshold were selected
from validation data. The test images were not used during selection.

## Validation subset selection

The selected subset was `jpeg_history + resampling + block_grid` with weights
`0.25, 0.25, 0.50`. Its validation Dice was `0.1875`. The full four-cue pool
had the same validation score but was rejected by the predefined minimum-size
rule. The next best evaluated subsets were:

| Subset | Validation Dice |
|---|---:|
| JPEG history + resampling + block-grid | 0.1875 |
| Full candidate pool | 0.1875 |
| Resampling + block-grid + copy-move | 0.1822 |
| Resampling + block-grid | 0.1787 |
| Block-grid | 0.1761 |

## Held-out pilot result

The selected subset obtained mean Dice `0.2062` on the held-out pilot test.
Per-manipulation results were:

| Manipulation | Mean Dice |
|---|---:|
| Copy-move | 0.1355 |
| Splicing | 0.2890 |
| Object replacement | 0.1218 |
| Geometric edit | 0.2785 |

Mean detector runtimes were 4.3 ms for SIFT copy-move, 11.4 ms for the JPEG
history cue, 98.4 ms for resampling, and 7.7 ms for the block-grid cue on the
recorded workstation. These are implementation timings for 128 x 128 pilot
images and are not hardware-independent performance claims.

## Public benchmark sanity check

Ten original/forged example pairs were downloaded from the official CoMoFoD
website. The examples demonstrate that the SIFT detector receives materially
more geometrically consistent matches on several forged images than on their
corresponding originals. The example page does not expose the binary masks for
these files, so they are used only for detector sanity checks, not for Dice,
IoU, or localization claims. Quantitative CoMoFoD evaluation must use the
official archive and its binary masks after a local licensed download.

## Interpretation

The pilot does not establish that the selected subset is generally superior.
Its scores are modest and vary by manipulation type. The result supports the
planned evaluation protocol: cue selection must be measured, compression cues
must be tested for redundancy, and the final paper must report failure cases.
The publication-scale experiment still requires a complete public benchmark
run, paired uncertainty intervals, and stress-condition results.
