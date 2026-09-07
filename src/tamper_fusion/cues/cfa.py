"""CFA demosaicing-inconsistency cue.

Methodology Section 4.1. Reimplemented in Python from the algorithm traced step
by step in ``references/notes/noise-cfa.md``, which was read from the authors'
released MATLAB (GPLv3, LESC / University of Florence, 2011) accompanying:

    P. Ferrara, T. Bianchi, A. De Rosa, A. Piva, "Image Forgery Localization via
    Fine-Grained Analysis of CFA Artifacts", IEEE TIFS 7(5):1566-1577, 2012.
    DOI 10.1109/TIFS.2012.2202227.

The paper's own text was not reachable during this work (the sole open-access
host serves a bot-check interstitial), so none of its reported numbers or stated
limitations are quoted anywhere in this project. The algorithm below comes from
the released code; the mapping of each step to its source file is in the notes.

Principle: a camera samples one colour per pixel through a colour filter array
and interpolates the rest. In an untouched image the demosaicing residual is
therefore systematically smaller at interpolated positions than at acquired
ones. Tampering that breaks the CFA periodicity drives that ratio toward one.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import correlate, median_filter

__all__ = ["CFAResult", "cfa_map", "detect_bayer_phase", "GREEN_PREDICTOR"]

# prediction.m lines 23-27: a fixed discrete Laplacian applied uniformly to the
# whole green channel. The acquired/interpolated asymmetry is extracted later,
# not by using a different predictor per phase.
GREEN_PREDICTOR = np.array(
    [[0.00, 0.25, 0.00],
     [0.25, -1.00, 0.25],
     [0.00, 0.25, 0.00]],
    dtype=np.float64,
)

# The four candidate green sub-lattice phases (GetCFASimple.m line 8).
BAYER_PHASES: tuple[np.ndarray, ...] = (
    np.array([[1, 0], [0, 1]], dtype=bool),
    np.array([[0, 1], [1, 0]], dtype=bool),
)


@dataclass(frozen=True)
class CFAResult:
    """``statistic`` is the per-block acquired/interpolated variance ratio."""

    statistic: np.ndarray
    block_size: int
    bayer_phase: np.ndarray
    available: bool
    reason: str | None = None


def _gaussian_window(size: int = 7, sigma: float = 1.0) -> np.ndarray:
    """gaussian_window.m lines 24-29: 7x7, sigma=1, sampled on [-2, 2]."""
    axis = np.linspace(-2.0, 2.0, size)
    xx, yy = np.meshgrid(axis, axis)
    return np.exp(-0.5 * (xx**2 + yy**2) / sigma**2) / (2.0 * np.pi * sigma**2)


def _phase_pattern(shape: tuple[int, int], bayer: np.ndarray) -> np.ndarray:
    """getVarianceMap.m line 22: tile the 2x2 phase mask over the image."""
    height, width = shape
    return np.tile(bayer, (height // 2 + 1, width // 2 + 1))[:height, :width]


def _variance_map(residual: np.ndarray, pattern: np.ndarray) -> np.ndarray:
    """Local residual variance computed separately on each CFA phase.

    getVarianceMap.m lines 25-52. A 7x7 checkerboard mask restricts the window to
    taps on the same two-pixel-period sub-lattice as the centre, so the two
    phases never mix. ``vc`` is the bias correction computed from the
    unnormalised weights.
    """
    size = 7
    checkerboard = np.zeros((size, size), dtype=np.float64)
    checkerboard[::2, ::2] = 1.0
    checkerboard[1::2, 1::2] = 1.0

    window = _gaussian_window(size) * checkerboard
    mass = window.sum()
    correction = 1.0 - (window**2).sum() / (mass**2)
    if correction <= 0:
        raise ValueError("degenerate variance window")
    window_mean = window / mass

    total = np.zeros(residual.shape, dtype=np.float64)
    for phase_mask in (pattern, ~pattern):
        selected = residual * phase_mask
        local_mean = correlate(selected, window_mean, mode="nearest")
        local_square = correlate(selected**2, window_mean, mode="nearest")
        variance = (local_square - local_mean**2) / correction
        total += np.where(phase_mask, np.maximum(variance, 0.0), 0.0)
    return total


def _block_statistic(variance: np.ndarray, bayer: np.ndarray, block_size: int) -> np.ndarray:
    """getFeature.m lines 24-31: product over acquired / product over interpolated.

    Computed in the log domain to avoid overflow: for ``block_size`` of 8 the
    product runs over 32 values, which overflows float64 for realistic
    variances. The log of the ratio is what the mixture is fitted on anyway
    (MoGEstimationZM.m line 34), so no information is lost. The value returned
    is the ratio itself, to keep this function's contract identical to the
    reference; the caller takes its log.
    """
    height, width = variance.shape
    rows, columns = height // block_size, width // block_size
    if rows < 1 or columns < 1:
        raise ValueError("image is smaller than one block")

    trimmed = variance[: rows * block_size, : columns * block_size]
    pattern = _phase_pattern((block_size, block_size), bayer)
    blocks = trimmed.reshape(rows, block_size, columns, block_size).swapaxes(1, 2)

    floor = np.finfo(np.float64).tiny
    log_blocks = np.log(np.maximum(blocks, floor))
    acquired = log_blocks[..., pattern].sum(axis=-1)
    interpolated = log_blocks[..., ~pattern].sum(axis=-1)
    return np.exp(np.clip(acquired - interpolated, -700.0, 700.0))


def detect_bayer_phase(green: np.ndarray) -> np.ndarray:
    """Choose the green sub-lattice phase without camera knowledge.

    GetCFASimple.m selects among candidate patterns by bilinear-CFA
    reconstruction error over non-smooth blocks. We use the equivalent and
    cheaper criterion available from quantities already computed here: the phase
    whose interpolated positions carry the smaller residual variance is the one
    the camera interpolated. Ties and near-ties are resolved toward the first
    candidate, and the caller can always supply the phase explicitly.
    """
    residual = correlate(green, GREEN_PREDICTOR, mode="nearest")
    best_phase, best_ratio = BAYER_PHASES[0], np.inf
    for candidate in BAYER_PHASES:
        pattern = _phase_pattern(green.shape, candidate)
        acquired = residual[pattern]
        interpolated = residual[~pattern]
        if acquired.size == 0 or interpolated.size == 0:
            continue
        ratio = float(np.var(interpolated)) / max(float(np.var(acquired)), 1e-12)
        if ratio < best_ratio:
            best_phase, best_ratio = candidate, ratio
    return best_phase


def cfa_map(
    image: np.ndarray,
    *,
    block_size: int = 2,
    bayer_phase: np.ndarray | None = None,
    median_size: int = 5,
) -> CFAResult:
    """Compute the CFA block statistic for one RGB image.

    Returns the per-block ratio of acquired-phase to interpolated-phase local
    residual variance. Values near one indicate the CFA structure is absent,
    which is the tampering hypothesis. Calibration into a log-likelihood ratio
    is the caller's job (``tamper_fusion.calibration.calibrate`` with
    ``log_domain=True``), matching the reference's fit on ``log(statistic)``.
    """
    array = np.asarray(image)
    if array.ndim != 3 or array.shape[2] < 3:
        raise ValueError("CFA analysis requires an RGB image")
    if block_size < 2 or block_size % 2:
        raise ValueError("block_size must be an even integer of at least 2")

    green = array[..., 1].astype(np.float64)
    if min(green.shape) < 4 * block_size:
        return CFAResult(
            np.zeros((1, 1)), block_size, BAYER_PHASES[0], False,
            "image is too small for CFA block analysis",
        )

    phase = BAYER_PHASES[0] if bayer_phase is None else np.asarray(bayer_phase, dtype=bool)
    if bayer_phase is None:
        phase = detect_bayer_phase(green)

    residual = correlate(green, GREEN_PREDICTOR, mode="nearest")
    pattern = _phase_pattern(green.shape, phase)
    variance = _variance_map(residual, pattern)
    statistic = _block_statistic(variance, phase, block_size)

    if median_size > 1:
        statistic = median_filter(statistic, size=median_size, mode="nearest")

    if not np.isfinite(statistic).any():
        return CFAResult(statistic, block_size, phase, False,
                         "CFA statistic is entirely non-finite")
    return CFAResult(statistic, block_size, phase, True, None)
