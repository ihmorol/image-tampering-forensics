from io import BytesIO

import numpy as np
from PIL import Image

from tamper_fusion.detectors import (
    jpeg_block_grid,
    jpeg_ghost,
    resampling_trace,
    sift_copy_move,
)
from tamper_fusion.preprocess import from_array, load_image, robust_normalize


def _textured_image(size: int = 128) -> np.ndarray:
    rng = np.random.default_rng(7)
    image = rng.integers(0, 256, (size, size, 3), dtype=np.uint8)
    patch = max(8, size // 4)
    source = size // 10
    target = size - patch - size // 10
    image[target : target + patch, target : target + patch] = image[source : source + patch, source : source + patch]
    return image


def _jpeg_image(image: np.ndarray):
    buffer = BytesIO()
    Image.fromarray(image).save(buffer, format="JPEG", quality=82)
    buffer.seek(0)
    decoded = np.asarray(Image.open(buffer).convert("RGB"))
    return from_array(decoded, source_format="JPEG")


def test_robust_normalize_constant_map_is_zero():
    result = robust_normalize(np.full((16, 16), 3.0, dtype=np.float32))
    assert np.count_nonzero(result) == 0


def test_all_supported_detectors_return_finite_unit_maps():
    image = _textured_image()
    jpeg = _jpeg_image(image)
    results = (
        sift_copy_move(image),
        resampling_trace(image),
        jpeg_ghost(jpeg, qualities=(70, 80, 90)),
        jpeg_block_grid(jpeg),
    )
    for result in results:
        assert result.available
        assert result.map.shape == image.shape[:2]
        assert result.map.dtype == np.float32
        assert np.isfinite(result.map).all()
        assert 0.0 <= float(result.map.min()) <= float(result.map.max()) <= 1.0


def test_jpeg_cues_report_unavailable_for_array_input():
    image = _textured_image(64)
    for result in (jpeg_ghost(image), jpeg_block_grid(image)):
        assert not result.available
        assert result.reason
        assert np.count_nonzero(result.map) == 0


def test_sift_handles_featureless_image_without_crashing():
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    result = sift_copy_move(image)
    assert result.available
    assert result.reason
    assert np.count_nonzero(result.map) == 0


def test_jpeg_cues_disable_after_resize(tmp_path):
    source = tmp_path / "source.jpg"
    Image.fromarray(_textured_image(96)).save(source, format="JPEG", quality=80)
    prepared = load_image(source, max_dimension=64)
    assert prepared.metadata["resized"] is True
    assert prepared.metadata["scale_xy"] == (2 / 3, 2 / 3)
    for result in (jpeg_ghost(prepared), jpeg_block_grid(prepared)):
        assert not result.available
        assert "resized" in result.reason
        assert result.metadata["original_size"] == (96, 96)
        assert result.metadata["processed_size"] == (64, 64)
