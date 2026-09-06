from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from PIL import Image

@dataclass(frozen=True)
class TamperedSample:
    image: np.ndarray
    mask: np.ndarray
    kind: str

def generate_sample(seed: int = 0, size: tuple[int, int] = (256, 256), kind: str = "copy_move") -> TamperedSample:
    rng = np.random.default_rng(seed); h, w = size
    yy, xx = np.mgrid[:h, :w]
    image = np.stack([(xx / w * 255), (yy / h * 255), ((xx + yy) % 64) * 4], axis=-1).astype(np.uint8)
    mask = np.zeros((h, w), bool)
    x0, y0 = int(w * .2), int(h * .2); rw, rh = int(w * .25), int(h * .25)
    target_x, target_y = x0, y0
    if kind == "splicing":
        image[y0:y0+rh, x0:x0+rw] = rng.integers(0, 255, (rh, rw, 3), dtype=np.uint8)
    elif kind == "object_removal":
        image[y0:y0+rh, x0:x0+rw] = image[y0:y0+rh, :rw]
    elif kind in {"copy_move", "geometric_edit"}:
        dx, dy = int(w * .35), int(h * .25)
        target_x, target_y = x0 + dx, y0 + dy
        patch = Image.fromarray(image[y0:y0+rh, x0:x0+rw])
        if kind == "geometric_edit":
            patch = patch.resize((rw, rh), Image.Resampling.BICUBIC).rotate(8, resample=Image.Resampling.BICUBIC)
        image[target_y:target_y+rh, target_x:target_x+rw] = np.asarray(patch)
    else:
        raise ValueError(f"unsupported tampering kind: {kind}")
    mask[target_y:target_y+rh, target_x:target_x+rw] = True
    return TamperedSample(image, mask, kind)

def save_sample(sample: TamperedSample, image_path, mask_path) -> None:
    Image.fromarray(sample.image).save(image_path); Image.fromarray(sample.mask.astype(np.uint8)*255).save(mask_path)
