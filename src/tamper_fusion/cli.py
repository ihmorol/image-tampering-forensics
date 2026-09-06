from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .detectors import run_candidate_detectors
from .fusion import fuse_maps
from .metrics import summarize_mask
from .report import write_static_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one-image forensic analysis")
    parser.add_argument("image", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mask", type=Path)
    parser.add_argument("--max-dimension", type=int, default=1024)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--cues",
        nargs="+",
        default=["copy_move", "jpeg_history", "resampling", "block_grid"],
        choices=["copy_move", "jpeg_history", "resampling", "block_grid"],
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = run_candidate_detectors(args.image, args.max_dimension, args.cues)
    fused = fuse_maps(result.maps, result.availability, threshold=args.threshold)
    summary: dict = {
        "image": str(args.image),
        "cues": args.cues,
        "availability": result.availability,
        "threshold": args.threshold,
        "timing_seconds": result.timing_seconds,
    }
    if args.mask:
        truth, resized = _load_mask(args.mask, fused.mask.shape)
        summary["metrics"] = summarize_mask(fused.mask, truth)
        summary["mask_geometry"] = {"source_shape": list(truth.shape), "prediction_shape": list(fused.mask.shape), "resized": resized}
    for name, score_map in result.maps.items():
        _write_npy(args.output_dir / f"{name}.npy", score_map)
    _write_npy(args.output_dir / "fused.npy", fused.score_map)
    _write_npy(args.output_dir / "mask.npy", fused.mask.astype("uint8"))
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    write_static_report(args.output_dir, summary)
    return 0


def _write_npy(path: Path, value) -> None:
    np.save(path, value)


def _load_mask(path: Path, target_shape: tuple[int, int]) -> tuple[np.ndarray, bool]:
    with Image.open(path) as opened:
        source = np.asarray(opened.convert("L")) > 127
    if source.shape == target_shape:
        return source, False
    image = Image.fromarray(source.astype(np.uint8) * 255)
    resized = image.resize((target_shape[1], target_shape[0]), Image.Resampling.NEAREST)
    return np.asarray(resized) > 127, True


if __name__ == "__main__":
    raise SystemExit(main())
