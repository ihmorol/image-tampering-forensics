from __future__ import annotations
import argparse
from pathlib import Path
from tamper_fusion.dataset import assign_source_disjoint_splits, generate_sample, save_sample, write_manifest

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=24)
    parser.add_argument("--seed", type=int, default=4883)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    kinds = ["copy_move", "splicing", "object_removal", "geometric_edit"]
    manifest = []
    for index in range(args.count):
        kind = kinds[index % len(kinds)]; stem = f"{index:04d}_{kind}"
        sample = generate_sample(args.seed + index, kind=kind)
        image_path = args.output / f"{stem}.png"; mask_path = args.output / f"{stem}_mask.png"
        save_sample(sample, image_path, mask_path)
        manifest.append({"image": image_path.name, "mask": mask_path.name, "kind": kind, "source_id": f"synthetic-source-{index}", "seed": args.seed + index})
    records = assign_source_disjoint_splits(manifest, validation_fraction=0.2, test_fraction=0.2)
    write_manifest(records, args.output / "manifest.json")
    return 0

if __name__ == "__main__": raise SystemExit(main())
