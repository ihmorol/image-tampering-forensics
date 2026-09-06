import numpy as np
from tamper_fusion.fusion import evaluate_subsets, fuse_maps, tune_fusion
from tamper_fusion.metrics import mask_metrics

def test_metrics_for_partial_overlap():
    truth = np.array([[1, 1], [0, 0]], bool); pred = np.array([[1, 0], [1, 0]], bool)
    result = mask_metrics(pred, truth)
    assert result["precision"] == result["recall"] == result["f1"] == 0.5
    assert result["iou"] == 1 / 3

def test_missing_cue_weights_are_renormalized():
    maps = {"a": np.array([[0, 1]], float), "b": np.array([[1, 0]], float)}
    result = fuse_maps(maps, {"a": True, "b": False}, weights={"a": .2, "b": .8})
    assert result.weights == {"a": 1.0}

def test_tuning_and_ablation_use_all_candidate_subsets():
    truth = np.array([[0, 1], [0, 1]], bool)
    good = truth.astype(float); bad = 1 - good
    samples = [({"good": good, "bad": bad}, truth)]
    config = tune_fusion(samples, ["good", "bad"], thresholds=[.5], weight_step=.5)
    assert config.weights["good"] == 1.0
    assert len(evaluate_subsets(samples, ["good", "bad"])) == 3

def test_unavailable_cue_is_excluded_from_fitted_normalization():
    truth = np.array([[0, 1]], bool)
    samples = [({"good": truth.astype(float), "jpeg": np.array([[99., 99.]])}, truth, {"good": True, "jpeg": False})]
    config = tune_fusion(samples, ["good", "jpeg"], thresholds=[.5], weight_step=.5)
    assert "jpeg" not in config.normalization
    assert config.weights["good"] == 1.0

def test_invalid_fusion_parameters_are_rejected():
    with np.testing.assert_raises(ValueError):
        fuse_maps({"a": np.ones((1, 1))}, weights={"a": 0})
    with np.testing.assert_raises(ValueError):
        fuse_maps({"a": np.ones((1, 1))}, threshold=np.nan)

def test_zero_weight_cue_stays_excluded():
    maps = {
        "good": np.array([[0.0, 1.0], [0.0, 1.0]]),
        "bad": np.array([[1.0, 0.0], [1.0, 0.0]]),
    }
    result = fuse_maps(maps, weights={"good": 1.0}, threshold=0.5)
    assert result.weights == {"good": 1.0, "bad": 0.0}
    assert np.array_equal(result.mask, maps["good"].astype(bool))

def test_all_unavailable_validation_is_rejected():
    truth = np.zeros((2, 2), dtype=bool)
    samples = [({"jpeg": np.zeros((2, 2))}, truth, {"jpeg": False})]
    with np.testing.assert_raises_regex(ValueError, "no candidate cue"):
        tune_fusion(samples, ["jpeg"])

def test_malformed_available_map_is_not_silently_ignored():
    truth = np.zeros((2, 2), dtype=bool)
    samples = [({"cue": np.zeros((2, 2, 1))}, truth)]
    with np.testing.assert_raises_regex(ValueError, "two-dimensional"):
        tune_fusion(samples, ["cue"])
