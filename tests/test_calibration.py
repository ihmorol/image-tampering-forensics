import numpy as np
import pytest

from tamper_fusion.calibration import (
    calibrate,
    fit_zero_mean_mixture,
    log_likelihood_ratio,
)


def test_em_recovers_known_mixture_parameters():
    rng = np.random.default_rng(4883)
    n_null, n_alt = 6000, 4000
    null = rng.normal(0.0, 1.0, n_null)
    alt = rng.normal(4.0, 1.5, n_alt)
    fit = fit_zero_mean_mixture(np.concatenate([null, alt]))

    assert fit.converged
    assert fit.alpha == pytest.approx(n_null / (n_null + n_alt), abs=0.05)
    assert fit.variance_null == pytest.approx(1.0, rel=0.15)
    assert fit.mean_alt == pytest.approx(4.0, rel=0.10)
    assert fit.variance_alt == pytest.approx(1.5**2, rel=0.25)


def test_null_component_mean_stays_at_zero():
    """The defining property of this EM variant: one mean is never re-estimated."""
    rng = np.random.default_rng(1)
    data = np.concatenate([rng.normal(0.0, 1.0, 3000), rng.normal(6.0, 1.0, 1000)])
    fit = fit_zero_mean_mixture(data)
    # The null component is pinned at zero, so all separation lives in mean_alt.
    assert fit.mean_alt > 4.0
    assert fit.separation > 3.0


def test_log_likelihood_ratio_favours_the_alternative_where_expected():
    rng = np.random.default_rng(2)
    data = np.concatenate([rng.normal(0.0, 1.0, 4000), rng.normal(5.0, 1.0, 2000)])
    fit = fit_zero_mean_mixture(data)
    ratio = log_likelihood_ratio(np.array([0.0, 5.0]), fit)
    assert ratio[0] < 0 < ratio[1]


def test_calibrate_returns_a_map_that_separates_a_planted_region():
    rng = np.random.default_rng(3)
    scores = rng.normal(0.0, 1.0, (64, 64))
    scores[20:40, 20:40] += 5.0
    llr, fit, reason = calibrate(scores)

    assert reason is None and llr is not None and fit is not None
    inside = llr[20:40, 20:40].mean()
    outside = np.concatenate([llr[:20].ravel(), llr[40:].ravel()]).mean()
    assert inside > outside


def test_constant_map_abstains_rather_than_returning_zeros():
    llr, fit, reason = calibrate(np.full((32, 32), 3.0))
    assert llr is None
    assert "constant" in reason


def test_unseparated_components_abstain():
    """The degeneracy guard: pure noise has no two-component structure to use."""
    rng = np.random.default_rng(5)
    llr, fit, reason = calibrate(rng.normal(0.0, 1.0, (64, 64)), minimum_separation=2.0)
    assert llr is None
    assert "not separated" in reason


def test_all_nan_map_abstains():
    llr, fit, reason = calibrate(np.full((16, 16), np.nan))
    assert llr is None
    assert "no finite values" in reason


def test_log_domain_handles_a_ratio_statistic():
    """Ratio statistics have a null of 1, which is zero in the log domain."""
    rng = np.random.default_rng(7)
    ratio = np.exp(rng.normal(0.0, 0.3, (48, 48)))
    ratio[10:25, 10:25] *= np.exp(3.0)
    llr, fit, reason = calibrate(ratio, log_domain=True)

    assert reason is None and llr is not None
    assert llr[10:25, 10:25].mean() > llr[30:, 30:].mean()


def test_non_positive_values_survive_the_log_domain_guard():
    values = np.full((32, 32), 1.0)
    values[0, 0] = -5.0
    values[16:, 16:] = np.exp(4.0)
    llr, fit, reason = calibrate(values, log_domain=True)
    assert llr is None or np.isfinite(llr).all()


def test_non_two_dimensional_input_is_rejected():
    with pytest.raises(ValueError, match="two-dimensional"):
        calibrate(np.zeros((4, 4, 3)))


def test_fit_rejects_too_few_samples():
    with pytest.raises(ValueError, match="at least 8"):
        fit_zero_mean_mixture(np.array([1.0, 2.0, 3.0]))
