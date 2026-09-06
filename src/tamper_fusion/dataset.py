from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from PIL import Image

@dataclass(frozen=True)
class TamperedSample:
    image: np.ndarray
    mask: np.ndarray
    kind: str

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
