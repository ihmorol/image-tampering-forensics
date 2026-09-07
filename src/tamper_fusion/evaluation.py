"""Evaluation measures for tampering localization.

This module replaces the single-operating-point reporting used in the pilot
study. Findings E1, E4 and E5 in `docs/audit-prior-work.md` record why:

* An empty prediction against an empty ground truth was scored as a perfect
  match, so an authentic image rewarded a detector that found nothing.
* Only mean per-image Dice at one fixed threshold was reported, which cannot
  separate "this cue carries no signal" from "this threshold is wrong".
* No uncertainty interval was reported.

Here, undefined measures are reported as ``None`` and excluded from aggregation
with an explicit count, threshold-free measures are computed from the score map,
and aggregation returns a bootstrap confidence interval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

__all__ = [
    "binary_metrics",
    "score_metrics",
    "aggregate",
    "bootstrap_ci",
    "BINARY_KEYS",
    "SCORE_KEYS",
]

BINARY_KEYS = ("precision", "recall", "f1", "iou", "mcc")
SCORE_KEYS = ("roc_auc", "average_precision", "best_f1", "best_iou")


def _as_bool(value: np.ndarray) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype != bool:
        array = array > 0.5 if np.issubdtype(array.dtype, np.floating) else array.astype(bool)
    return array


def binary_metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float | int | None]:
    """Pixel metrics for one binary prediction.

    A measure is ``None`` when it is mathematically undefined for this pair
    rather than being silently reported as 0.0 or 1.0. Specifically:

    * ``precision`` is undefined when nothing is predicted positive.
    * ``recall`` is undefined when the ground truth is empty (an authentic
      image), and so are ``f1``, ``iou`` and ``mcc``.

    For authentic images use ``false_positive_rate``, which is defined there and
    undefined when the ground truth is fully positive.
    """
    predicted, actual = _as_bool(prediction), _as_bool(truth)
    if predicted.shape != actual.shape:
        raise ValueError(f"mask shapes differ: {predicted.shape} vs {actual.shape}")

    tp = int(np.count_nonzero(predicted & actual))
    fp = int(np.count_nonzero(predicted & ~actual))
    fn = int(np.count_nonzero(~predicted & actual))
    tn = int(np.count_nonzero(~predicted & ~actual))

    has_truth = (tp + fn) > 0
    has_prediction = (tp + fp) > 0

    precision = tp / (tp + fp) if has_prediction else None
    recall = tp / (tp + fn) if has_truth else None

    if not has_truth:
        f1 = iou = mcc = None
    else:
        precision_value = precision if precision is not None else 0.0
        denominator = precision_value + recall
        f1 = 2 * precision_value * recall / denominator if denominator else 0.0
        union = tp + fp + fn
        iou = tp / union if union else None
        mcc = _mcc(tp, fp, tn, fn)

    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "iou": iou,
        "mcc": mcc,
        "false_positive_rate": fp / (fp + tn) if (fp + tn) > 0 else None,
        "predicted_positive_rate": (tp + fp) / predicted.size,
        "truth_positive_rate": (tp + fn) / actual.size,
    }


def _mcc(tp: int, fp: int, tn: int, fn: int) -> float | None:
    numerator = tp * tn - fp * fn
    denominator = float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    if denominator <= 0:
        return None
    return numerator / np.sqrt(denominator)


def score_metrics(
    scores: np.ndarray,
    truth: np.ndarray,
    *,
    thresholds: int = 128,
    both_polarities: bool = False,
) -> dict[str, float | None]:
    """Threshold-free measures for one continuous suspicion map.

    ``best_f1`` and ``best_iou`` are oracle values: they report the score at the
    most favourable threshold for this image. They bound what any threshold
    selection rule could achieve, so they separate cue quality from threshold
    choice. They are not achievable operating points and must never be reported
    as the system's performance.

    ``both_polarities`` reports the more favourable of the map and its negation.
    Some forensic statistics are sign-ambiguous. Enable it only when the cue is
    documented as such, and disclose it, because it is an oracle choice.
    """
    values = np.asarray(scores, dtype=np.float64).ravel()
    actual = _as_bool(truth).ravel()
    if values.shape != actual.shape:
        raise ValueError(f"score and truth shapes differ: {values.shape} vs {actual.shape}")
    if not np.isfinite(values).all():
        raise ValueError("score map contains non-finite values")

    # ROC and PR are undefined when the ground truth has a single class.
    if actual.all() or not actual.any():
        return {key: None for key in SCORE_KEYS}

    result = _score_metrics_one_polarity(values, actual, thresholds)
    if both_polarities:
        flipped = _score_metrics_one_polarity(-values, actual, thresholds)
        result = {
            key: max(result[key], flipped[key])
            for key in result
        }
    return result


def _score_metrics_one_polarity(
    values: np.ndarray, actual: np.ndarray, thresholds: int
) -> dict[str, float]:
    roc_auc = float(roc_auc_score(actual, values))
    average_precision = float(average_precision_score(actual, values))

    # Sweep thresholds over the observed value range at fixed quantiles so the
    # sweep is invariant to the cue's arbitrary output scale.
    quantiles = np.linspace(0.0, 100.0, thresholds + 2)[1:-1]
    candidates = np.unique(np.percentile(values, quantiles))
    positive_total = int(actual.sum())

    best_f1 = 0.0
    best_iou = 0.0
    for threshold in candidates:
        predicted = values >= threshold
        tp = int(np.count_nonzero(predicted & actual))
        if tp == 0:
            continue
        predicted_total = int(predicted.sum())
        f1 = 2 * tp / (predicted_total + positive_total)
        iou = tp / (predicted_total + positive_total - tp)
        best_f1 = max(best_f1, f1)
        best_iou = max(best_iou, iou)

    return {
        "roc_auc": roc_auc,
        "average_precision": average_precision,
        "best_f1": best_f1,
        "best_iou": best_iou,
    }


def bootstrap_ci(
    values: Sequence[float],
    *,
    confidence: float = 0.95,
    resamples: int = 10000,
    seed: int = 4883,
) -> tuple[float, float] | None:
    """Percentile bootstrap interval for the mean. ``None`` if fewer than 2 values."""
    array = np.asarray([v for v in values if v is not None], dtype=float)
    if array.size < 2:
        return None
    rng = np.random.default_rng(seed)
    draws = rng.choice(array, size=(resamples, array.size), replace=True).mean(axis=1)
    alpha = (1.0 - confidence) / 2.0
    low, high = np.percentile(draws, [100 * alpha, 100 * (1 - alpha)])
    return float(low), float(high)


@dataclass(frozen=True)
class Aggregate:
    mean: float | None
    ci: tuple[float, float] | None
    n_defined: int
    n_undefined: int

    def as_dict(self) -> dict:
        return {
            "mean": self.mean,
            "ci_low": self.ci[0] if self.ci else None,
            "ci_high": self.ci[1] if self.ci else None,
            "n_defined": self.n_defined,
            "n_undefined": self.n_undefined,
        }


def aggregate(
    rows: Iterable[Mapping[str, float | None]],
    keys: Sequence[str],
    *,
    confidence: float = 0.95,
    seed: int = 4883,
) -> dict[str, dict]:
    """Mean and bootstrap interval per key, counting undefined cases explicitly.

    Undefined values are never coerced to zero. A key whose measure was
    undefined for every image reports ``mean=None`` rather than a fabricated
    number.
    """
    materialised = list(rows)
    summary: dict[str, dict] = {}
    for key in keys:
        defined = [row[key] for row in materialised if row.get(key) is not None]
        undefined = len(materialised) - len(defined)
        mean = float(np.mean(defined)) if defined else None
        ci = bootstrap_ci(defined, confidence=confidence, seed=seed) if defined else None
        summary[key] = Aggregate(mean, ci, len(defined), undefined).as_dict()
    return summary
