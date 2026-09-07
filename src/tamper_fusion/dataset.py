from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import csv
import hashlib
import json
from typing import Iterable, Mapping
import numpy as np
from PIL import Image, ImageFilter

@dataclass(frozen=True)
class TamperedSample:
    image: np.ndarray
    mask: np.ndarray
    kind: str


@dataclass(frozen=True)
class ManifestRecord:
    image: str
    mask: str
    kind: str
    source_id: str
    split: str
    dataset: str = "controlled"
    perturbation: str | None = None


VALID_SPLITS = frozenset({"train", "validation", "test"})
VALID_KINDS = frozenset({"copy_move", "splicing", "object_removal", "geometric_edit", "recompression"})


def read_manifest(path: str | Path) -> list[ManifestRecord]:
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest does not exist: {manifest_path}")
    if manifest_path.suffix.lower() == ".csv":
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    elif manifest_path.suffix.lower() == ".json":
        rows = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        raise ValueError("manifest must be .json or .csv")
    if not isinstance(rows, list):
        raise ValueError("manifest must contain a list of records")
    records = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"manifest row {index} is not an object")
        required = {"image", "mask", "kind", "source_id", "split"}
        missing = sorted(required - set(row))
        if missing:
            raise ValueError(f"manifest row {index} missing fields: {', '.join(missing)}")
        if str(row["image"]).startswith(("http://", "https://")) or str(row["mask"]).startswith(("http://", "https://")):
            raise ValueError("remote image or mask URLs are not downloaded; provide verified local files")
        record = ManifestRecord(
            image=str(row["image"]), mask=str(row["mask"]), kind=str(row["kind"]),
            source_id=str(row["source_id"]), split=str(row["split"]),
            dataset=str(row.get("dataset", "public")),
            perturbation=str(row["perturbation"]) if row.get("perturbation") else None,
        )
        if record.split not in VALID_SPLITS:
            raise ValueError(f"manifest row {index} has invalid split: {record.split}")
        if not record.source_id:
            raise ValueError(f"manifest row {index} has empty source_id")
        if not record.kind:
            raise ValueError(f"manifest row {index} has empty kind")
        records.append(record)
    ensure_source_disjoint(records)
    return records


def ensure_source_disjoint(records: Iterable[ManifestRecord]) -> None:
    source_splits: dict[str, set[str]] = {}
    for record in records:
        source_splits.setdefault(record.source_id, set()).add(record.split)
    conflicts = sorted(source for source, splits in source_splits.items() if len(splits) > 1)
    if conflicts:
        raise ValueError("source-disjoint split violation for source_id: " + ", ".join(conflicts))


def assign_source_disjoint_splits(
    rows: Iterable[Mapping[str, object]], *, validation_fraction: float = 0.2, test_fraction: float = 0.2,
) -> list[ManifestRecord]:
    if validation_fraction < 0 or test_fraction < 0 or validation_fraction + test_fraction >= 1:
        raise ValueError("validation_fraction and test_fraction must be nonnegative and sum to less than one")
    rows = list(rows)
    unique = sorted({str(row["source_id"]) for row in rows})
    assignments: dict[str, str] = {}
    for source in unique:
        bucket = int(hashlib.sha256(source.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
        assignments[source] = "test" if bucket < test_fraction else "validation" if bucket < test_fraction + validation_fraction else "train"
    records = [ManifestRecord(image=str(row["image"]), mask=str(row["mask"]), kind=str(row["kind"]), source_id=str(row["source_id"]), split=assignments[str(row["source_id"])], dataset=str(row.get("dataset", "controlled")), perturbation=str(row["perturbation"]) if row.get("perturbation") else None) for row in rows]
    ensure_source_disjoint(records)
    return records


def write_manifest(records: Iterable[ManifestRecord], path: str | Path) -> None:
    records = list(records)
    ensure_source_disjoint(records)
    Path(path).write_text(json.dumps([asdict(record) for record in records], indent=2) + "\n", encoding="utf-8")


def apply_perturbation(image: np.ndarray, kind: str, *, seed: int = 0, jpeg_quality: int = 70, scale: float = 0.75, sigma: float = 1.2, noise_std: float = 8.0) -> np.ndarray:
    array = np.asarray(image)
    if array.ndim not in (2, 3) or min(array.shape[:2]) < 8:
        raise ValueError("image must be at least 8x8")
    if kind == "none":
        return array.copy()
    pil = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))
    if kind == "resize":
        if not 0 < scale <= 1:
            raise ValueError("resize scale must be in (0, 1]")
        size = (max(8, round(pil.width * scale)), max(8, round(pil.height * scale)))
        return np.asarray(pil.resize(size, Image.Resampling.LANCZOS))
    if kind == "blur":
        if sigma <= 0:
            raise ValueError("blur sigma must be positive")
        return np.asarray(pil.filter(ImageFilter.GaussianBlur(radius=sigma)))
    if kind == "jpeg":
        if not 1 <= jpeg_quality <= 95:
            raise ValueError("jpeg_quality must be between 1 and 95")
        from io import BytesIO
        buffer = BytesIO()
        pil.convert("RGB").save(buffer, format="JPEG", quality=jpeg_quality, subsampling=0)
        buffer.seek(0)
        return np.asarray(Image.open(buffer).convert("RGB")) if array.ndim == 3 else np.asarray(Image.open(buffer).convert("L"))
    if kind == "noise":
        if noise_std < 0:
            raise ValueError("noise_std must be nonnegative")
        rng = np.random.default_rng(seed)
        noisy = array.astype(np.float32) + rng.normal(0.0, noise_std, size=array.shape)
        return np.clip(noisy, 0, 255).astype(np.uint8)
    raise ValueError(f"unsupported perturbation: {kind}")

def generate_sample(seed: int = 0, size: tuple[int, int] = (256, 256), kind: str = "copy_move") -> TamperedSample:
    rng = np.random.default_rng(seed)
    h, w = size
    if h < 64 or w < 64:
        raise ValueError("synthetic samples require dimensions of at least 64 pixels")
    image = _textured_background(rng, h, w)
    mask = np.zeros((h, w), bool)
    rw, rh = max(24, int(w * .22)), max(24, int(h * .22))
    x0, y0 = int(w * .12), int(h * .15)
    target_x, target_y = x0, y0
    if kind == "splicing":
        image[y0:y0+rh, x0:x0+rw] = _textured_patch(rng, rh, rw)
    elif kind == "object_removal":
        image[y0:y0+rh, x0:x0+rw] = image[y0:y0+rh, :rw]
    elif kind in {"copy_move", "geometric_edit"}:
        target_x = min(w - rw - 1, x0 + int(w * .45))
        target_y = min(h - rh - 1, y0 + int(h * .38))
        patch = Image.fromarray(image[y0:y0+rh, x0:x0+rw])
        if kind == "geometric_edit":
            patch = patch.rotate(8, resample=Image.Resampling.BICUBIC, expand=False)
        image[target_y:target_y+rh, target_x:target_x+rw] = np.asarray(patch)
    else:
        raise ValueError(f"unsupported tampering kind: {kind}")
    mask[target_y:target_y+rh, target_x:target_x+rw] = True
    return TamperedSample(image, mask, kind)

def save_sample(sample: TamperedSample, image_path: str | Path, mask_path: str | Path) -> None:
    Image.fromarray(sample.image).save(image_path)
    Image.fromarray(sample.mask.astype(np.uint8) * 255).save(mask_path)


def _textured_background(rng: np.random.Generator, height: int, width: int) -> np.ndarray:
    coarse = rng.random((max(4, height // 12), max(4, width // 12)), dtype=np.float32)
    coarse = np.asarray(Image.fromarray((coarse * 255).astype(np.uint8)).resize((width, height), Image.Resampling.BICUBIC), dtype=np.float32) / 255.0
    fine = rng.random((height, width), dtype=np.float32)
    yy, xx = np.mgrid[:height, :width]
    waves = 0.5 + 0.5 * np.sin(xx / 7.0) * np.cos(yy / 11.0)
    channels = np.stack((coarse * .62 + fine * .18 + waves * .20, coarse * .30 + fine * .48 + waves * .22, coarse * .22 + fine * .24 + waves * .54), axis=-1)
    for _ in range(max(8, min(height, width) // 20)):
        cx, cy = int(rng.integers(8, width - 8)), int(rng.integers(8, height - 8))
        radius = int(rng.integers(3, max(4, min(height, width) // 18)))
        color = rng.uniform(.05, .95, 3)
        yy0, xx0 = np.ogrid[:height, :width]
        disk = (xx0 - cx) ** 2 + (yy0 - cy) ** 2 <= radius ** 2
        channels[disk] = color
    return np.clip(channels * 255.0, 0, 255).astype(np.uint8)


def _textured_patch(rng: np.random.Generator, height: int, width: int) -> np.ndarray:
    patch = _textured_background(rng, height, width)
    for index in range(1, min(height, width) // 10, max(1, min(height, width) // 24)):
        patch[index:index + 2, :] = 255 - patch[index:index + 2, :]
        patch[:, index:index + 2] = 255 - patch[:, index:index + 2]
    return patch
