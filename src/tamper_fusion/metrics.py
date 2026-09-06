from __future__ import annotations
from pathlib import Path
import numpy as np

def _mask(value):
    if isinstance(value, (str, Path)):
        from PIL import Image
        return np.asarray(Image.open(value).convert("L")) > 127
    return np.asarray(value, bool)

def mask_metrics(prediction, truth) -> dict[str, float]:
    p, t = _mask(prediction), _mask(truth)
    if p.shape != t.shape: raise ValueError(f"mask shapes differ: {p.shape} vs {t.shape}")
    tp = int(np.count_nonzero(p & t)); fp = int(np.count_nonzero(p & ~t)); fn = int(np.count_nonzero(~p & t))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    union = int(np.count_nonzero(p | t)); iou = tp / union if union else 1.0
    return {"precision": precision, "recall": recall, "f1": f1, "iou": iou, "dice": f1, "tp": tp, "fp": fp, "fn": fn}

def summarize_mask(prediction, truth) -> dict[str, float]:
    return mask_metrics(prediction, truth)
