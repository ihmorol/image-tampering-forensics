import json
from pathlib import Path

import numpy as np
from PIL import Image

from tamper_fusion import cli
from tamper_fusion.detectors import CandidateDetectorResult


def test_cli_resizes_ground_truth_mask_to_detector_geometry(tmp_path, monkeypatch):
    image_path = tmp_path / "image.png"
    mask_path = tmp_path / "mask.png"
    output_dir = tmp_path / "out"
    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(image_path)
    Image.fromarray(np.pad(np.ones((2, 2), dtype=np.uint8) * 255, ((1, 1), (1, 1)))).save(mask_path)
    score_map = np.zeros((8, 8), dtype=np.float32)
    score_map[2:6, 2:6] = 1.0
    fake = CandidateDetectorResult({"copy_move": score_map}, {"copy_move": True}, {"copy_move": None}, {"copy_move": {}}, {"copy_move": 0.01})
    monkeypatch.setattr(cli, "run_candidate_detectors", lambda *args, **kwargs: fake)
    assert cli.main([str(image_path), "--output-dir", str(output_dir), "--mask", str(mask_path), "--cues", "copy_move"]) == 0
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["mask_geometry"]["resized"] is True
    assert summary["mask_geometry"]["prediction_shape"] == [8, 8]
    assert summary["metrics"]["iou"] > 0
