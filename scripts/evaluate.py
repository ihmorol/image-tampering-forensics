from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from PIL import Image
from tamper_fusion.fusion import evaluate_subsets, fuse_maps, tune_fusion
from tamper_fusion.metrics import mask_metrics
from tamper_fusion.report import write_static_report

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path); parser.add_argument("maps", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.dataset / "manifest.json").read_text(encoding="utf-8"))
    cues = sorted({p.stem.rsplit("_", 1)[-1] for p in args.maps.glob("*.npy")})
    records = []
    for row in manifest:
        stem = Path(row["image"]).stem
        maps = {cue: np.load(args.maps / f"{stem}_{cue}.npy") for cue in cues if (args.maps / f"{stem}_{cue}.npy").exists()}
        truth = np.asarray(Image.open(args.dataset / row["mask"]).convert("L")) > 127
        records.append((row, maps, truth))
    validation = [(maps, truth) for row, maps, truth in records if row["split"] == "validation"]
    test = [(maps, truth) for row, maps, truth in records if row["split"] == "test"]
    config = tune_fusion(validation, cues)
    per_image = [mask_metrics(fuse_maps(maps, weights=config.weights, threshold=config.threshold, normalization=config.normalization).mask, truth) for maps, truth in test]
    summary = {"selected_cues": list(config.cues), "weights": config.weights, "threshold": config.threshold,
               "validation_dice": config.validation_dice, "normalization": config.normalization, "test_mean": {k: float(np.mean([r[k] for r in per_image])) for k in ["precision","recall","f1","iou","dice"]},
               "validation_subsets": evaluate_subsets(validation, cues)}
    write_static_report(args.output, summary)
    return 0

if __name__ == "__main__": raise SystemExit(main())
