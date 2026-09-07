import numpy as np
import pytest

from tamper_fusion.calibration import calibrate
from tamper_fusion.cues.cfa import BAYER_PHASES, cfa_map, detect_bayer_phase


def _natural_image(rng, height=192, width=192):
    """Smooth, structured content: CFA traces are only meaningful on such data."""
    coarse = rng.random((height // 16, width // 16, 3))
    image = np.repeat(np.repeat(coarse, 16, axis=0), 16, axis=1)
    yy, xx = np.mgrid[:height, :width]
    image[..., 0] += 0.3 * np.sin(xx / 19.0)
    image[..., 1] += 0.3 * np.cos(yy / 23.0)
    image[..., 2] += 0.2 * np.sin((xx + yy) / 17.0)
    smooth = np.empty_like(image)
    for channel in range(3):
        padded = np.pad(image[..., channel], 2, mode="reflect")
        smooth[..., channel] = sum(
            padded[i:i + height, j:j + width] for i in range(5) for j in range(5)
        ) / 25.0
    return np.clip(smooth, 0, 1)


def _bayer_demosaic(rgb, phase):
    """Simulate CFA acquisition then bilinear demosaicing.

    Only the green channel matters for this cue. Green is sampled on the
    ``phase`` sub-lattice and the missing positions are filled by averaging the
    four sampled neighbours, which is what creates the acquired/interpolated
    variance asymmetry the cue detects.
    """
    height, width = rgb.shape[:2]
    pattern = np.tile(phase, (height // 2 + 1, width // 2 + 1))[:height, :width]
    green = rgb[..., 1].copy()
    sampled = np.where(pattern, green, 0.0)
    padded = np.pad(sampled, 1, mode="reflect")
    mask = np.pad(pattern.astype(float), 1, mode="reflect")
    neighbour_sum = padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]
    neighbour_count = mask[:-2, 1:-1] + mask[2:, 1:-1] + mask[1:-1, :-2] + mask[1:-1, 2:]
    interpolated = neighbour_sum / np.maximum(neighbour_count, 1.0)
    out = rgb.copy()
    out[..., 1] = np.where(pattern, green, interpolated)
    return out


def test_authentic_cfa_image_has_ratio_above_one():
    """An untouched demosaiced image has smaller residual variance where it was
    interpolated, so the acquired/interpolated ratio sits above one."""
    rng = np.random.default_rng(4883)
    demosaiced = _bayer_demosaic(_natural_image(rng), BAYER_PHASES[0])
    result = cfa_map(demosaiced, block_size=2, bayer_phase=BAYER_PHASES[0])
    assert result.available
    assert np.median(result.statistic) > 1.0


def test_cue_fires_on_a_region_whose_cfa_structure_was_destroyed():
    """The functional test: splice in content that never went through the CFA."""
    rng = np.random.default_rng(7)
    original = _natural_image(rng)
    demosaiced = _bayer_demosaic(original, BAYER_PHASES[0])

    tampered = demosaiced.copy()
    tampered[64:128, 64:128] = original[64:128, 64:128]  # no CFA correlation here

    result = cfa_map(tampered, block_size=2, bayer_phase=BAYER_PHASES[0])
    assert result.available

    scale = result.statistic.shape[0] / tampered.shape[0]
    lo, hi = int(64 * scale), int(128 * scale)
    inside = np.median(result.statistic[lo:hi, lo:hi])
    outside = np.median(np.delete(result.statistic, np.s_[lo:hi], axis=0))

    # Destroying the CFA correlation drives the ratio toward one, so the
    # tampered region's statistic is markedly lower than the authentic surround.
    assert inside < outside
    assert abs(np.log(inside)) < abs(np.log(outside))


def test_calibrated_llr_is_lower_inside_the_tampered_region():
    """Sign convention: for CFA the zero-mean component is the TAMPERED
    hypothesis, so the calibrated LLR is low where tampering is present and the
    suspicion map is its negation."""
    rng = np.random.default_rng(11)
    original = _natural_image(rng)
    demosaiced = _bayer_demosaic(original, BAYER_PHASES[0])
    tampered = demosaiced.copy()
    tampered[64:128, 64:128] = original[64:128, 64:128]

    result = cfa_map(tampered, block_size=2, bayer_phase=BAYER_PHASES[0])
    llr, fit, reason = calibrate(result.statistic, log_domain=True, minimum_separation=0.1)
    assert reason is None, reason

    scale = llr.shape[0] / tampered.shape[0]
    lo, hi = int(64 * scale), int(128 * scale)
    inside = llr[lo:hi, lo:hi].mean()
    outside = np.delete(llr, np.s_[lo:hi], axis=0).mean()
    assert inside < outside


def test_phase_detection_recovers_the_simulated_phase():
    rng = np.random.default_rng(13)
    for phase in BAYER_PHASES:
        demosaiced = _bayer_demosaic(_natural_image(rng), phase)
        detected = detect_bayer_phase(demosaiced[..., 1].astype(float))
        assert np.array_equal(detected, phase)


def test_block_size_eight_does_not_overflow():
    """The product over 32 variances overflows float64; it is computed in logs."""
    rng = np.random.default_rng(17)
    demosaiced = _bayer_demosaic(_natural_image(rng), BAYER_PHASES[0])
    result = cfa_map(demosaiced, block_size=8, bayer_phase=BAYER_PHASES[0])
    assert result.available
    assert np.isfinite(result.statistic).all()


def test_small_image_abstains():
    result = cfa_map(np.zeros((6, 6, 3)), block_size=2)
    assert not result.available
    assert "too small" in result.reason


def test_non_rgb_input_is_rejected():
    with pytest.raises(ValueError, match="RGB"):
        cfa_map(np.zeros((32, 32)))


def test_odd_block_size_is_rejected():
    with pytest.raises(ValueError, match="even integer"):
        cfa_map(np.zeros((64, 64, 3)), block_size=3)
