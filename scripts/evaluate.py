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
    subset_rows = evaluate_subsets(validation, cues)
    valid_rows = [row for row in subset_rows if row["status"] == "evaluated"]
    if not valid_rows:
        raise ValueError("no cue subset is available in validation data")
    selected = min(valid_rows, key=lambda row: (-row["mean_dice"], len(row["cues"]), row["cues"]))
    selected_cues = tuple(selected["cues"])
    per_image = []
    for maps, truth in test:
        active = {cue: selected["weights"][cue] for cue in selected_cues if cue in maps}
        if not active:
            per_image.append({"precision": 0.0, "recall": 0.0, "f1": 0.0, "iou": 0.0, "dice": 0.0})
            continue
        prediction = fuse_maps(
            maps,
            weights=active,
            threshold=selected["threshold"],
            normalization=selected["normalization"],
        ).mask
        per_image.append(mask_metrics(prediction, truth))
    summary = {"selected_cues": list(selected_cues), "weights": selected["weights"],
               "threshold": selected["threshold"], "validation_dice": selected["mean_dice"],
               "normalization": selected["normalization"],
               "test_mean": {k: float(np.mean([r[k] for r in per_image])) for k in ["precision","recall","f1","iou","dice"]},
               "validation_subsets": subset_rows}
    write_static_report(args.output, summary)
    return 0

if __name__ == "__main__": raise SystemExit(main())
