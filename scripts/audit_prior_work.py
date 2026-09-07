"""Reproduce the quantitative findings recorded in docs/audit-prior-work.md.

Every number in that document is produced by this script. Run:

    python scripts/audit_prior_work.py --workdir <scratch dir>

The script writes nothing into the repository.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

from tamper_fusion.dataset import generate_sample
from tamper_fusion.detectors import run_candidate_detectors
from tamper_fusion.fusion import evaluate_subsets, fuse_maps
from tamper_fusion.metrics import mask_metrics


def dice(prediction: np.ndarray, truth: np.ndarray) -> float:
    denominator = int(prediction.sum()) + int(truth.sum())
    return 2 * int((prediction & truth).sum()) / denominator if denominator else 1.0


def finding_mask_geometry_is_seed_independent() -> None:
    """F1: the ground-truth mask depends only on manipulation kind and image size."""
    print("\n[F1] ground-truth mask geometry vs. seed")
    for size in [(128, 128), (256, 256), (512, 512)]:
        signatures = set()
        for kind in ("copy_move", "splicing", "object_removal", "geometric_edit"):
            for seed in range(0, 60, 7):
                mask = generate_sample(seed, size=size, kind=kind).mask
                ys, xs = np.where(mask)
                signatures.add((kind, int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())))
        positions = {s[1:] for s in signatures}
        print(f"  size={size}: 4 kinds x 9 seeds -> {len(signatures)} signatures, "
              f"{len(positions)} distinct bounding boxes")


def finding_constant_mask_baseline(dataset: Path) -> None:
    """F2: a predictor that never reads the image, fitted on train+validation only."""
    print("\n[F2] image-independent constant-mask baseline")
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    load = lambda row: np.asarray(Image.open(dataset / row["mask"]).convert("L")) > 127
    fit = [r for r in manifest if r["split"] in {"train", "validation"}]
    test = [r for r in manifest if r["split"] == "test"]

    frequency = np.mean([load(r) for r in fit], axis=0)
    constant = frequency >= 0.2  # any location tampered in >=20% of fitting masks

    scores = [dice(constant, load(r)) for r in test]
    print(f"  held-out test mean Dice = {np.mean(scores):.4f} (n={len(scores)}, "
          f"predicted area fraction={constant.mean():.4f})")
    by_kind: dict[str, list[float]] = defaultdict(list)
    for row in test:
        by_kind[row["kind"]].append(dice(constant, load(row)))
    for kind, values in sorted(by_kind.items()):
        print(f"    {kind:16s} n={len(values)} Dice={np.mean(values):.4f}")


def finding_pipeline_on_committed_generator(dataset: Path) -> None:
    """F3+F4: cue availability and end-to-end score of the committed pipeline."""
    print("\n[F3] cue availability on the committed generator output")
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    records = []
    for row in manifest:
        result = run_candidate_detectors(dataset / row["image"], 1024)
        truth = np.asarray(Image.open(dataset / row["mask"]).convert("L")) > 127
        records.append((row, result, truth))

    availability = Counter()
    for _, result, _ in records:
        for cue, is_available in result.availability.items():
            availability[(cue, is_available)] += 1
    for (cue, is_available), count in sorted(availability.items()):
        print(f"  {cue:14s} available={is_available!s:5s} {count}/{len(records)} images")

    print("\n[F4] committed pipeline, selection on validation, scored on held-out test")
    cues = ["copy_move", "jpeg_history", "resampling", "block_grid"]
    validation = [(r.maps, t, r.availability) for row, r, t in records if row["split"] == "validation"]
    test = [(r.maps, t, r.availability) for row, r, t in records if row["split"] == "test"]

    evaluated = [r for r in evaluate_subsets(validation, cues) if r["status"] == "evaluated"]
    selected = min(evaluated, key=lambda r: (-r["mean_dice"], len(r["cues"]), r["cues"]))
    print(f"  selected subset={selected['cues']} validation Dice={selected['mean_dice']:.4f} "
          f"threshold={selected['threshold']}")

    metrics = []
    for maps, truth, avail in test:
        active = {c: selected["weights"][c] for c in selected["cues"]
                  if c in maps and selected["weights"].get(c, 0.0) > 0.0}
        if not active:
            metrics.append({"precision": 0.0, "recall": 0.0, "dice": 0.0})
            continue
        prediction = fuse_maps(maps, avail, weights=active, threshold=selected["threshold"],
                               normalization=selected["normalization"]).mask
        metrics.append(mask_metrics(prediction, truth))
    for key in ("precision", "recall", "dice"):
        print(f"  held-out test mean {key}: {np.mean([m[key] for m in metrics]):.4f}")
    print(f"  n test = {len(metrics)}")


def finding_dataset_format(dataset: Path) -> None:
    """F5: what the committed generator actually writes."""
    print("\n[F5] committed generator output properties")
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    with Image.open(dataset / manifest[0]["image"]) as image:
        print(f"  size={image.size} format={image.format} mode={image.mode}")
    print(f"  split counts: {dict(Counter(r['split'] for r in manifest))}")
    print(f"  kind x split: {dict(Counter((r['kind'], r['split']) for r in manifest))}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--seed", type=int, default=4883)
    args = parser.parse_args()

    dataset = args.workdir / "pilot"
    dataset.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "scripts/generate_dataset.py", "--output", str(dataset),
         "--count", str(args.count), "--seed", str(args.seed)],
        check=True,
    )

    finding_dataset_format(dataset)
    finding_mask_geometry_is_seed_independent()
    finding_constant_mask_baseline(dataset)
    finding_pipeline_on_committed_generator(dataset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
