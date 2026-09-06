from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


@dataclass(frozen=True)
class PreprocessedImage:
    rgb: np.ndarray
    gray: np.ndarray
    source_path: Path | None = None
    source_format: str | None = None
    metadata: dict[str, Any] | None = None

    @property
    def shape(self) -> tuple[int, int]:
        return self.gray.shape

    @property
    def is_jpeg(self) -> bool:
        return self.source_format in {"JPEG", "JPG"}


def load_image(path: str | Path, *, max_dimension: int | None = None) -> PreprocessedImage:
    source_path = Path(path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Image file does not exist: {source_path}")
    if max_dimension is not None and max_dimension < 8:
        raise ValueError("max_dimension must be at least 8 pixels")

    try:
        with Image.open(source_path) as opened:
            source_format = opened.format.upper() if opened.format else None
            metadata = {
                "mode": opened.mode,
                "size": opened.size,
                "original_size": opened.size,
                "format": source_format,
            }
            image = ImageOps.exif_transpose(opened).convert("RGB")
            oriented_size = image.size
            if max_dimension and max(image.size) > max_dimension:
                scale = max_dimension / max(image.size)
                resized = tuple(max(1, round(value * scale)) for value in image.size)
                image = image.resize(resized, Image.Resampling.LANCZOS)
                metadata["resized"] = True
                metadata["processed_size"] = image.size
            else:
                metadata["resized"] = False
                metadata["processed_size"] = image.size
            metadata["oriented_size"] = oriented_size
            metadata["scale_xy"] = (
                image.size[0] / oriented_size[0],
                image.size[1] / oriented_size[1],
            )
            rgb = np.asarray(image, dtype=np.uint8).copy()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Unsupported or unreadable image: {source_path}") from exc

    return from_array(
        rgb,
        source_path=source_path,
        source_format=source_format,
        metadata=metadata,
    )


def from_array(
    image: np.ndarray,
    *,
    source_path: str | Path | None = None,
    source_format: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> PreprocessedImage:
    array = np.asarray(image)
    if array.ndim == 2:
        gray_u8 = _to_uint8(array)
        rgb = cv2.cvtColor(gray_u8, cv2.COLOR_GRAY2RGB)
    elif array.ndim == 3 and array.shape[2] in {3, 4}:
        rgb = _to_uint8(array[..., :3])
    else:
        raise ValueError("image must have shape (H, W), (H, W, 3), or (H, W, 4)")
    if min(rgb.shape[:2]) < 8:
        raise ValueError("image dimensions must each be at least 8 pixels")
    if not np.isfinite(rgb).all():
        raise ValueError("image contains non-finite values")

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    normalized_format = source_format.upper() if source_format else None
    return PreprocessedImage(
        rgb=np.ascontiguousarray(rgb),
        gray=np.ascontiguousarray(gray),
        source_path=Path(source_path) if source_path is not None else None,
        source_format=normalized_format,
        metadata=dict(metadata) if metadata else {},
    )


def robust_normalize(
    values: np.ndarray,
    *,
    lower_percentile: float = 2.0,
    upper_percentile: float = 98.0,
) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    if array.ndim != 2:
        raise ValueError("suspicion maps must be two-dimensional")
    if not 0 <= lower_percentile < upper_percentile <= 100:
        raise ValueError("normalization percentiles must satisfy 0 <= low < high <= 100")

    finite = np.isfinite(array)
    if not finite.any():
        return np.zeros(array.shape, dtype=np.float32)
    cleaned = np.where(finite, array, 0.0)
    low, high = np.percentile(cleaned[finite], [lower_percentile, upper_percentile])
    if high - low <= np.finfo(np.float32).eps:
        return np.zeros(array.shape, dtype=np.float32)
    normalized = np.clip((cleaned - low) / (high - low), 0.0, 1.0)
    return normalized.astype(np.float32, copy=False)


def _to_uint8(array: np.ndarray) -> np.ndarray:
    if np.issubdtype(array.dtype, np.floating):
        if not np.isfinite(array).all():
            raise ValueError("image contains non-finite values")
        minimum = float(array.min())
        maximum = float(array.max())
        if minimum >= 0.0 and maximum <= 1.0:
            array = array * 255.0
    return np.clip(array, 0, 255).astype(np.uint8)
