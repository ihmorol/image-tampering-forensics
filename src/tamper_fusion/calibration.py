"""Per-image calibration of cue maps into log-likelihood ratios.

Methodology Section 3. Every cue emits a map on its own arbitrary scale. The
pilot rescaled each map by fixed percentiles and summed them with fixed weights,
which has two consequences: the scaling is not relative to the image's own
background, so an uninformative cue contributes its full share of noise, and a
weighted sum of uncalibrated scores has no probabilistic meaning.

The fix generalises what the Ferrara CFA method already does internally. It fits
a two-component Gaussian mixture to its block statistic per image, with one
component's mean forced to zero, and emits the log-likelihood ratio between the
components. Traced from the authors' released MATLAB in
``references/notes/noise-cfa.md`` (``MoGEstimationZM.m``, ``EMGaussianZM.m``,
``loglikelihood.m``).

A cue that cannot produce a usable fit abstains. Abstention is zero evidence, not
a zero score to be averaged (audit finding D6).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["MixtureFit", "fit_zero_mean_mixture", "log_likelihood_ratio", "calibrate"]

# Numeric guards mirroring the reference implementation's use of 1e-320 / 1e304
# when taking logs of a ratio statistic (loglikelihood.m lines 25-31).
_TINY = 1e-300
_HUGE = 1e300


@dataclass(frozen=True)
class MixtureFit:
    """Two-component fit ``alpha*N(0, v_null) + (1-alpha)*N(mu_alt, v_alt)``.

    ``alpha`` is the weight of the zero-mean (null) component.
    """

    alpha: float
    variance_null: float
    mean_alt: float
    variance_alt: float
    iterations: int
    converged: bool

    @property
    def separation(self) -> float:
        """Distance between component means in units of the null's own scale."""
        scale = np.sqrt(self.variance_null)
        return abs(self.mean_alt) / scale if scale > 0 else 0.0


def fit_zero_mean_mixture(
    values: np.ndarray,
    *,
    tolerance: float = 1e-3,
    max_iterations: int = 500,
) -> MixtureFit:
    """EM for a two-component Gaussian mixture with one mean fixed at zero.

    Follows ``EMGaussianZM.m``: initialise ``alpha=0.5``, ``mu_alt=mean(x)``,
    ``v_alt=var(x)``, ``v_null=v_alt/10``. Non-finite values are dropped, as in
    ``MoGEstimationZM.m`` lines 31-34.

    One deliberate deviation from the reference. ``EMGaussianZM.m`` stops when
    ``|alpha - alpha_old| <= tol``, testing a single parameter. That can fire on
    the first iteration whenever the initial step in ``alpha`` happens to be
    small, stopping the fit while the other parameters are still far from their
    solution; it was observed to stop after one iteration on a mixture whose
    true null weight was 0.75, reporting 0.50. We instead require the maximum
    relative change across all four parameters to fall below ``tolerance``.
    """
    data = np.asarray(values, dtype=np.float64).ravel()
    data = data[np.isfinite(data)]
    if data.size < 8:
        raise ValueError("at least 8 finite values are required to fit a mixture")

    variance_alt = float(np.var(data))
    if variance_alt <= 0:
        raise ValueError("cannot fit a mixture to constant data")

    alpha = 0.5
    mean_alt = float(np.mean(data))
    variance_null = variance_alt / 10.0

    converged = False
    iteration = 0
    for iteration in range(1, max_iterations + 1):
        null_density = _gaussian(data, 0.0, variance_null)
        alt_density = _gaussian(data, mean_alt, variance_alt)
        weighted_null = alpha * null_density
        weighted_alt = (1.0 - alpha) * alt_density
        total = weighted_null + weighted_alt
        total = np.where(total > 0, total, _TINY)

        responsibility_null = weighted_null / total
        responsibility_alt = 1.0 - responsibility_null

        previous = (alpha, variance_null, mean_alt, variance_alt)
        mass_null = float(responsibility_null.sum())
        mass_alt = float(responsibility_alt.sum())
        if mass_null <= 0 or mass_alt <= 0:
            break

        alpha = mass_null / data.size
        # Null component: second moment about zero, its mean is fixed.
        variance_null = float((responsibility_null * data**2).sum() / mass_null)
        mean_alt = float((responsibility_alt * data).sum() / mass_alt)
        variance_alt = float((responsibility_alt * (data - mean_alt) ** 2).sum() / mass_alt)

        variance_null = max(variance_null, _TINY)
        variance_alt = max(variance_alt, _TINY)

        current = (alpha, variance_null, mean_alt, variance_alt)
        if _max_relative_change(previous, current) <= tolerance:
            converged = True
            break

    return MixtureFit(
        alpha=float(alpha),
        variance_null=float(variance_null),
        mean_alt=float(mean_alt),
        variance_alt=float(variance_alt),
        iterations=iteration,
        converged=converged,
    )


def _max_relative_change(
    previous: tuple[float, ...], current: tuple[float, ...]
) -> float:
    """Largest relative parameter change, using absolute change near zero."""
    worst = 0.0
    for before, after in zip(previous, current, strict=True):
        scale = max(abs(before), abs(after), 1e-12)
        worst = max(worst, abs(after - before) / scale)
    return worst


def _gaussian(x: np.ndarray, mean: float, variance: float) -> np.ndarray:
    variance = max(float(variance), _TINY)
    return np.exp(-0.5 * (x - mean) ** 2 / variance) / np.sqrt(2.0 * np.pi * variance)


def log_likelihood_ratio(values: np.ndarray, fit: MixtureFit) -> np.ndarray:
    """Per-element ``log N(x; mu_alt, v_alt) - log N(x; 0, v_null)``.

    Positive means the alternative (tampered) component explains the value
    better. This matches ``loglikelihood.m`` lines 33-42 up to sign convention:
    the reference emits the same quantity and then applies ``1/(1+exp(L))``, so
    its final map is high where our ratio is low.
    """
    data = np.asarray(values, dtype=np.float64)
    null_variance = max(fit.variance_null, _TINY)
    alt_variance = max(fit.variance_alt, _TINY)
    return (
        0.5 * np.log(null_variance / alt_variance)
        - 0.5 * ((data - fit.mean_alt) ** 2 / alt_variance - data**2 / null_variance)
    )


def calibrate(
    score_map: np.ndarray,
    *,
    log_domain: bool = False,
    minimum_separation: float = 0.5,
    tolerance: float = 1e-3,
    max_iterations: int = 500,
) -> tuple[np.ndarray | None, MixtureFit | None, str | None]:
    """Calibrate one cue map into a log-likelihood-ratio map.

    Returns ``(llr_map, fit, reason)``. On abstention the map is ``None`` and
    ``reason`` says why; the caller must then contribute zero evidence rather
    than a zero score (methodology Section 3).

    ``log_domain`` applies ``log`` first, for ratio-type statistics whose null
    hypothesis is a ratio of one. ``minimum_separation`` is the degeneracy guard:
    if the two fitted components are not separated by at least this many null
    standard deviations, the fit carries no usable discrimination and the cue
    abstains. The reference implementation warns and proceeds; we abstain and
    count it.
    """
    values = np.asarray(score_map, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("cue maps must be two-dimensional")

    finite = np.isfinite(values)
    if not finite.any():
        return None, None, "cue map contains no finite values"

    working = values.copy()
    if log_domain:
        working = np.where(working > 0, working, _TINY)
        working = np.clip(working, _TINY, _HUGE)
        working = np.log(working)
        finite = np.isfinite(working)
        if not finite.any():
            return None, None, "log-domain transform left no finite values"

    sample = working[finite]
    if sample.size < 8:
        return None, None, "too few finite values to fit a mixture"
    if float(np.var(sample)) <= 0:
        return None, None, "cue map is constant, so it carries no evidence"

    try:
        fit = fit_zero_mean_mixture(sample, tolerance=tolerance, max_iterations=max_iterations)
    except ValueError as error:
        return None, None, f"mixture fit failed: {error}"

    if not fit.converged:
        return None, fit, f"mixture did not converge within {max_iterations} iterations"
    if fit.separation < minimum_separation:
        return None, fit, (
            f"fitted components are not separated "
            f"({fit.separation:.3f} < {minimum_separation})"
        )

    llr = log_likelihood_ratio(np.where(finite, working, 0.0), fit)
    llr = np.where(finite, llr, 0.0)
    return llr.astype(np.float64, copy=False), fit, None
