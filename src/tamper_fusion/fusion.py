from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class FusionResult:
    score_map: np.ndarray
    mask: np.ndarray
    weights: dict[str, float]
    threshold: float

@dataclass(frozen=True)
class FusionConfig:
    cues: tuple[str, ...]
    weights: dict[str, float]
    threshold: float
    validation_dice: float
    normalization: dict[str, tuple[float, float]]


def fit_normalization(samples, cues: Sequence[str], low: float = 1.0, high: float = 99.0):
    stats = {}
    for cue in cues:
        values = []
        for sample in samples:
            maps, _, availability = _unpack(sample)
            if not availability.get(cue, True):
                continue
            if cue in maps:
                arr = np.asarray(maps[cue], dtype=float)
                if arr.ndim != 2 or not np.isfinite(arr).any():
                    continue
                values.append(arr[np.isfinite(arr)])
        if values:
            flat = np.concatenate(values)
            stats[cue] = (float(np.percentile(flat, low)), float(np.percentile(flat, high)))
    return stats

def robust_normalize(score_map: np.ndarray, low: float = 1.0, high: float = 99.0, stats=None) -> np.ndarray:
    x = np.asarray(score_map, dtype=float)
    if x.ndim != 2 or not np.isfinite(x).any():
        return np.zeros_like(x, dtype=float)
    finite = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    lo, hi = stats if stats is not None else np.percentile(finite, [low, high])
    if hi <= lo:
        return np.zeros_like(finite)
    return np.clip((finite - lo) / (hi - lo), 0.0, 1.0)


def fuse_maps(maps: Mapping[str, np.ndarray], availability: Mapping[str, bool] | None = None,
              *, weights: Mapping[str, float] | None = None, threshold: float = 0.5,
              normalization: Mapping[str, tuple[float, float]] | None = None) -> FusionResult:
    if not np.isfinite(threshold) or not 0 <= threshold <= 1: raise ValueError("threshold must be finite in [0, 1]")
    availability = availability or {k: True for k in maps}
    active = [k for k, v in maps.items() if availability.get(k, True)]
    if not active:
        shape = next(iter(maps.values())).shape if maps else (0, 0)
        return FusionResult(np.zeros(shape), np.zeros(shape, dtype=bool), {}, threshold)
    shapes = {np.asarray(maps[k]).shape for k in active}
    if len(shapes) != 1: raise ValueError("active cue maps must have identical shapes")
    raw = {k: robust_normalize(maps[k], stats=(normalization or {}).get(k)) for k in active}
    ws = {k: float(weights.get(k, 1.0)) if weights else 1.0 for k in active}
    if any(not np.isfinite(v) for v in ws.values()): raise ValueError("weights must be finite")
    ws = {k: max(0.0, v) for k, v in ws.items()}
    total = sum(ws.values())
    if total <= 0: raise ValueError("at least one active weight must be positive")
    ws = {k: v / total for k, v in ws.items()}
    fused = sum(ws[k] * raw[k] for k in active)
    return FusionResult(fused, fused >= threshold, ws, threshold)


def tune_fusion(validation: Sequence[tuple], cues: Sequence[str],
                *, thresholds: Sequence[float] | None = None, weight_step: float = 0.25) -> FusionConfig:
    thresholds = np.linspace(0.2, 0.8, 13) if thresholds is None else tuple(thresholds)
    if not validation: raise ValueError("validation samples are required")
    normalization = fit_normalization(validation, cues)
    candidates = _simplex_weights(len(cues), weight_step)
    best = (-1.0, None, 0.5)
    for vec in candidates:
        weights = dict(zip(cues, vec))
        for threshold in thresholds:
            if not np.isfinite(threshold) or not 0 <= threshold <= 1: raise ValueError("thresholds must be finite in [0, 1]")
            scores = []
            for sample in validation:
                maps, truth, availability = _unpack(sample)
                try:
                    result = fuse_maps(maps, availability, weights=weights, threshold=float(threshold), normalization=normalization)
                except ValueError:
                    scores = []
                    break
                scores.append(_dice(result.mask, truth))
            value = float(np.mean(scores)) if scores else -1.0
            if value > best[0]:
                best = (value, weights, float(threshold))
    return FusionConfig(tuple(cues), best[1], best[2], best[0], normalization)


def evaluate_subsets(samples: Sequence[tuple], cues: Sequence[str]) -> list[dict]:
    rows: list[dict] = []
    for size in range(1, len(cues) + 1):
        for subset in combinations(cues, size):
            subset_samples = []
            for sample in samples:
                maps, truth, availability = _unpack(sample)
                subset_samples.append(({k: maps[k] for k in subset if k in maps}, truth,
                                       {k: availability.get(k, True) for k in subset}))
            config = tune_fusion(subset_samples, subset, thresholds=[0.5])
            vals = []
            for maps, truth, availability in subset_samples:
                result = fuse_maps(maps, availability, weights=config.weights, threshold=config.threshold,
                                   normalization=config.normalization)
                vals.append(_dice(result.mask, truth))
            rows.append({"cues": list(subset), "mean_dice": float(np.mean(vals)) if vals else 0.0,
                         "weights": config.weights, "threshold": config.threshold,
                         "normalization": config.normalization})
    return rows


def _dice(pred: np.ndarray, truth: np.ndarray) -> float:
    p, t = np.asarray(pred, bool), np.asarray(truth, bool)
    inter = np.count_nonzero(p & t)
    denom = np.count_nonzero(p) + np.count_nonzero(t)
    return float(2 * inter / denom) if denom else 1.0

def _unpack(sample):
    if len(sample) == 2: return sample[0], sample[1], {k: True for k in sample[0]}
    if len(sample) == 3: return sample[0], sample[1], sample[2]
    raise ValueError("samples must be (maps, truth) or (maps, truth, availability)")

def _simplex_weights(count: int, step: float) -> list[np.ndarray]:
    if count < 1 or not 0 < step <= 1:
        raise ValueError("invalid simplex dimensions")
    units = round(1 / step)
    if not np.isclose(units * step, 1.0):
        raise ValueError("weight_step must divide 1.0")
    def compositions(total: int, parts: int):
        if parts == 1:
            yield (total,)
        else:
            for head in range(total + 1):
                for tail in compositions(total - head, parts - 1):
                    yield (head, *tail)
    return [np.asarray(parts, float) / units for parts in compositions(units, count)]
