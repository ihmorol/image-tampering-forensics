# Public dataset provenance

## CoMoFoD

CoMoFoD is the primary public benchmark for the duplicated-content cue. Its
official description reports original images, forged images, colored masks, and
binary masks, with translation, rotation, scaling, distortion, combination, and
post-processing variants.

- Official site: <https://www.vcl.fer.hr/comofod/>
- Download agreement: <https://www.vcl.fer.hr/comofod/download.html>
- Full archive: `comofod_small.rar` (approximately 3.2 GB; not vendored in this
  repository because the release is large and subject to the authors' terms).
- Local public examples: `comofod_examples/`, downloaded from the official VCL
  example page. These images document the public source and forged image pairs;
  they are not used as quantitative ground truth because the example page does
  not expose the corresponding binary masks.
- License/use: non-commercial research under the CoMoFoD release agreement.

The quantitative pipeline accepts the complete archive after local extraction.
The manifest must reference the supplied binary masks and must keep all variants
derived from one original source in one split.

## COVERAGE

COVERAGE is a public copy-move benchmark designed to separate genuine similar
objects from duplicated regions. It provides original/forged pairs, duplicated
and forged region masks, and similarity annotations.

- Paper: `../papers/wen2016_coverage.pdf`
- Official repository and access link: <https://github.com/wenbihan/coverage>
- Dataset access: OneDrive link provided by the authors; access may require the
  release page and its non-commercial research terms.

The repository does not redistribute the COVERAGE archive. After local download,
the files can be converted into the project manifest without changing image
content or masks.

## Reproducibility rule

Public files are never fetched silently during evaluation. A user must download
the dataset under its own terms, record the local archive or extracted-file
hash, and provide a manifest with `source_id`, `split`, and mask paths. The
loader rejects remote paths and enforces source-disjoint splits.
