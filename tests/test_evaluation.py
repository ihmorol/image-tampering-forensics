import numpy as np
import pytest

from tamper_fusion.evaluation import (
    BINARY_KEYS,
    aggregate,
    binary_metrics,
    bootstrap_ci,
    score_metrics,
)


def test_partial_overlap_matches_hand_computed_values():
    truth = np.array([[1, 1], [0, 0]], bool)
    prediction = np.array([[1, 0], [1, 0]], bool)
    result = binary_metrics(prediction, truth)
    assert result["precision"] == result["recall"] == result["f1"] == 0.5
    assert result["iou"] == pytest.approx(1 / 3)
    assert (result["tp"], result["fp"], result["fn"], result["tn"]) == (1, 1, 1, 1)
    assert result["mcc"] == pytest.approx(0.0)


def test_empty_truth_and_empty_prediction_is_undefined_not_perfect():
    """Audit finding E1: the pilot scored this pair as a perfect match."""
    empty = np.zeros((4, 4), bool)
    result = binary_metrics(empty, empty)
    for key in ("recall", "f1", "iou", "mcc"):
        assert result[key] is None
    assert result["false_positive_rate"] == 0.0


def test_authentic_image_with_false_positives_is_penalised_via_fpr():
    truth = np.zeros((4, 4), bool)
    prediction = np.zeros((4, 4), bool)
    prediction[0, :] = True
    result = binary_metrics(prediction, truth)
    assert result["f1"] is None
    assert result["false_positive_rate"] == pytest.approx(0.25)


def test_perfect_prediction_scores_one():
    truth = np.zeros((6, 6), bool)
    truth[1:4, 1:4] = True
    result = binary_metrics(truth, truth)
    assert result["precision"] == result["recall"] == result["f1"] == result["iou"] == 1.0
    assert result["mcc"] == pytest.approx(1.0)


def test_score_metrics_reward_a_perfectly_ranked_map():
    truth = np.zeros((8, 8), bool)
    truth[2:5, 2:5] = True
    scores = truth.astype(float)
    result = score_metrics(scores, truth)
    assert result["roc_auc"] == 1.0
    assert result["best_f1"] == pytest.approx(1.0)
    assert result["best_iou"] == pytest.approx(1.0)


def test_score_metrics_are_undefined_for_single_class_truth():
    truth = np.zeros((8, 8), bool)
    result = score_metrics(np.random.default_rng(0).random((8, 8)), truth)
    assert all(value is None for value in result.values())


def test_score_metrics_detect_an_inverted_map_only_when_asked():
    truth = np.zeros((8, 8), bool)
    truth[2:5, 2:5] = True
    inverted = 1.0 - truth.astype(float)
    plain = score_metrics(inverted, truth)
    flipped = score_metrics(inverted, truth, both_polarities=True)
    assert plain["roc_auc"] == 0.0
    assert flipped["roc_auc"] == 1.0


def test_aggregate_excludes_undefined_values_and_counts_them():
    rows = [
        {"f1": 0.4, "iou": None},
        {"f1": 0.6, "iou": None},
        {"f1": None, "iou": None},
    ]
    summary = aggregate(rows, ["f1", "iou"])
    assert summary["f1"]["mean"] == pytest.approx(0.5)
    assert summary["f1"]["n_defined"] == 2
    assert summary["f1"]["n_undefined"] == 1
    assert summary["iou"]["mean"] is None
    assert summary["iou"]["n_defined"] == 0


def test_bootstrap_interval_brackets_the_mean_and_is_deterministic():
    values = [0.1, 0.2, 0.3, 0.4, 0.5]
    first = bootstrap_ci(values, resamples=2000, seed=7)
    second = bootstrap_ci(values, resamples=2000, seed=7)
    assert first == second
    assert first[0] < np.mean(values) < first[1]
    assert bootstrap_ci([0.5]) is None


def test_shape_mismatch_is_rejected():
    with pytest.raises(ValueError, match="shapes differ"):
        binary_metrics(np.zeros((2, 2), bool), np.zeros((3, 3), bool))
    with pytest.raises(ValueError, match="shapes differ"):
        score_metrics(np.zeros((2, 2)), np.zeros((3, 3), bool))


def test_non_finite_scores_are_rejected():
    truth = np.zeros((4, 4), bool)
    truth[0, 0] = True
    scores = np.zeros((4, 4))
    scores[1, 1] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        score_metrics(scores, truth)


def test_binary_keys_are_all_produced():
    truth = np.zeros((4, 4), bool)
    truth[0, 0] = True
    result = binary_metrics(truth, truth)
    assert set(BINARY_KEYS) <= set(result)
