import numpy as np

from tamper_fusion.dataset import generate_sample


def test_copy_move_has_textured_duplicate_and_target_only_mask():
    sample = generate_sample(seed=4, size=(128, 128), kind="copy_move")
    assert sample.image.shape == (128, 128, 3)
    assert sample.mask.shape == (128, 128)
    assert sample.mask.dtype == bool
    assert sample.mask.any()
    assert np.unique(sample.image).size > 64
    assert sample.mask.sum() < sample.mask.size // 2


def test_all_kinds_have_valid_target_masks():
    for kind in ("copy_move", "splicing", "object_removal", "geometric_edit"):
        sample = generate_sample(seed=2, size=(96, 112), kind=kind)
        assert sample.mask.any()
        assert np.isfinite(sample.image).all()
        assert sample.mask.sum() < sample.mask.size
