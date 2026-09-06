import json
import numpy as np
import pytest
from tamper_fusion.dataset import (
    apply_perturbation,
    assign_source_disjoint_splits,
    generate_sample,
    read_manifest,
    write_manifest,
)


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


def test_manifest_rejects_source_leakage(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps([
        {"image": "a.png", "mask": "a_m.png", "kind": "splicing", "source_id": "s1", "split": "train"},
        {"image": "b.png", "mask": "b_m.png", "kind": "splicing", "source_id": "s1", "split": "test"},
    ]), encoding="utf-8")
    with pytest.raises(ValueError, match="source-disjoint"):
        read_manifest(path)


def test_manifest_round_trip_and_deterministic_source_split(tmp_path):
    rows = [
        {"image": "a.png", "mask": "a_m.png", "kind": "splicing", "source_id": "s1"},
        {"image": "b.png", "mask": "b_m.png", "kind": "copy_move", "source_id": "s1"},
        {"image": "c.png", "mask": "c_m.png", "kind": "splicing", "source_id": "s2"},
        {"image": "d.png", "mask": "d_m.png", "kind": "copy_move", "source_id": "s3"},
    ]
    records = assign_source_disjoint_splits(rows, validation_fraction=0.25, test_fraction=0.25)
    assert [r.split for r in records] == [r.split for r in assign_source_disjoint_splits(rows, validation_fraction=0.25, test_fraction=0.25)]
    path = tmp_path / "manifest.json"
    write_manifest(records, path)
    assert read_manifest(path) == records


def test_manifest_rejects_remote_assets(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps([{"image": "https://example.invalid/a.png", "mask": "m.png", "kind": "splicing", "source_id": "s1", "split": "test"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="remote"):
        read_manifest(path)


def test_perturbations_are_deterministic_and_preserve_expected_geometry():
    image = np.full((32, 40, 3), 128, dtype=np.uint8)
    assert apply_perturbation(image, "none").shape == image.shape
    assert apply_perturbation(image, "resize", scale=0.5).shape == (16, 20, 3)
    assert apply_perturbation(image, "blur").shape == image.shape
    assert apply_perturbation(image, "jpeg").shape == image.shape
    first = apply_perturbation(image, "noise", seed=9)
    second = apply_perturbation(image, "noise", seed=9)
    assert np.array_equal(first, second)
