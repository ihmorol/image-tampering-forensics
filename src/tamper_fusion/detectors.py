from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, uniform_filter

from .preprocess import PreprocessedImage, from_array, load_image, robust_normalize


@dataclass(frozen=True)
class CueResult:
    name: str
    map: np.ndarray
    available: bool
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateDetectorResult:
    maps: dict[str, np.ndarray]
    availability: dict[str, bool]
    reasons: dict[str, str | None]
    metadata: dict[str, dict[str, Any]]
    timing_seconds: dict[str, float]


def run_candidate_detectors(
    path: str | Path,
    max_dimension: int | None = 1024,
    cues: Iterable[str] = ("copy_move", "jpeg_history", "resampling", "block_grid"),
) -> CandidateDetectorResult:
    prepared = load_image(path, max_dimension=max_dimension)
    aliases = {
        "copy_move": sift_copy_move,
        "jpeg_history": jpeg_ghost,
        "resampling": resampling_trace,
        "block_grid": jpeg_block_grid,
    }
    maps: dict[str, np.ndarray] = {}
    availability: dict[str, bool] = {}
    reasons: dict[str, str | None] = {}
    metadata: dict[str, dict[str, Any]] = {}
    timing_seconds: dict[str, float] = {}
    for name in cues:
        if name not in aliases:
            raise ValueError(f"unknown cue: {name}")
        started = perf_counter()
        result = aliases[name](prepared)
        timing_seconds[name] = perf_counter() - started
        maps[name] = result.map
        availability[name] = result.available
        reasons[name] = result.reason
        metadata[name] = result.metadata
    return CandidateDetectorResult(maps, availability, reasons, metadata, timing_seconds)


def sift_copy_move(
    image: PreprocessedImage | np.ndarray,
    *,
    ratio_threshold: float = 0.75,
    minimum_separation: float = 12.0,
    ransac_threshold: float = 4.0,
    minimum_inliers: int = 4,
) -> CueResult:
    prepared = _prepare(image)
    gray_u8 = np.rint(prepared.gray * 255.0).astype(np.uint8)
    sift = cv2.SIFT_create()
    keypoints, descriptors = sift.detectAndCompute(gray_u8, None)
    empty = _empty(prepared)
    if descriptors is None or len(keypoints) < minimum_inliers * 2:
        return CueResult(
            "sift_copy_move",
            empty,
            True,
            "insufficient SIFT features for geometric verification",
            {"keypoints": len(keypoints), "candidate_matches": 0, "inliers": 0},
        )

    matcher = cv2.BFMatcher(cv2.NORM_L2)
    raw_matches = matcher.knnMatch(descriptors, descriptors, k=min(4, len(descriptors)))
    candidates: list[cv2.DMatch] = []
    for neighbors in raw_matches:
        viable = [
            match
            for match in neighbors
            if match.queryIdx != match.trainIdx
            and np.linalg.norm(
                np.subtract(keypoints[match.queryIdx].pt, keypoints[match.trainIdx].pt)
            )
            >= minimum_separation
        ]
        if len(viable) >= 2 and viable[0].distance < ratio_threshold * viable[1].distance:
            candidates.append(viable[0])

    candidates = _deduplicate_matches(candidates)
    if len(candidates) < minimum_inliers:
        return CueResult(
            "sift_copy_move",
            empty,
            True,
            "insufficient descriptor matches for geometric verification",
            {
                "keypoints": len(keypoints),
                "candidate_matches": len(candidates),
                "inliers": 0,
            },
        )

    source = np.float32([keypoints[match.queryIdx].pt for match in candidates])
    target = np.float32([keypoints[match.trainIdx].pt for match in candidates])
    affine, inlier_mask = cv2.estimateAffinePartial2D(
        source, target, method=cv2.RANSAC, ransacReprojThreshold=ransac_threshold,
        maxIters=2000, confidence=0.995,
    )
    inliers = inlier_mask.ravel().astype(bool) if inlier_mask is not None else np.zeros(len(candidates), bool)
    inlier_count = int(inliers.sum())
    inlier_source = source[inliers]
    inlier_target = target[inliers]
    source_extent = _point_extent(inlier_source)
    target_extent = _point_extent(inlier_target)
    if affine is None or inlier_count < max(minimum_inliers, 6) or min(source_extent, target_extent) < 8.0:
        return CueResult(
            "sift_copy_move",
            empty,
            True,
            "descriptor matches did not form a reliable geometric transform",
            {
                "keypoints": len(keypoints),
                "candidate_matches": len(candidates),
                "inliers": inlier_count,
                "source_extent": source_extent,
                "target_extent": target_extent,
            },
        )

    evidence = np.zeros(prepared.shape, dtype=np.float32)
    radius = max(3, round(min(prepared.shape) / 100))
    hulls = []
    for match, is_inlier in zip(candidates, inliers, strict=True):
        if not is_inlier:
            continue
        for point in (keypoints[match.queryIdx].pt, keypoints[match.trainIdx].pt):
            cv2.circle(evidence, tuple(np.rint(point).astype(int)), radius, 1.0, -1)
    for points in (inlier_source, inlier_target):
        hull = cv2.convexHull(np.rint(points).astype(np.float32))
        hulls.append(hull)
        cv2.fillConvexPoly(evidence, np.rint(hull).astype(np.int32), 1.0)
    evidence = gaussian_filter(evidence, sigma=max(2.0, radius * 1.5))
    return CueResult(
        "sift_copy_move",
        robust_normalize(evidence),
        True,
        metadata={
            "keypoints": len(keypoints),
            "candidate_matches": len(candidates),
            "inliers": inlier_count,
            "ransac_threshold": ransac_threshold,
            "transform": "affine_partial_2d",
            "cluster_extents": [source_extent, target_extent],
            "evidence_geometry": "inlier convex hulls and keypoint support",
        },
    )


def jpeg_ghost(
    image: PreprocessedImage | np.ndarray,
    *,
    qualities: Iterable[int] = range(50, 96, 5),
    window_size: int = 16,
) -> CueResult:
    prepared = _prepare(image)
    quality_values = tuple(int(quality) for quality in qualities)
    if not prepared.is_jpeg:
        return CueResult(
            "jpeg_ghost",
            _empty(prepared),
            False,
            "JPEG compression history is unavailable for a non-JPEG or array input",
            {"tested_qualities": quality_values},
        )
    if prepared.metadata and prepared.metadata.get("resized", False):
        return CueResult(
            "jpeg_ghost",
            _empty(prepared),
            False,
            "JPEG cue disabled because preprocessing resized the source image",
            {
                "tested_qualities": quality_values,
                "original_size": prepared.metadata.get("original_size"),
                "processed_size": prepared.metadata.get("processed_size"),
            },
        )
    if not quality_values or any(quality < 1 or quality > 100 for quality in quality_values):
        raise ValueError("qualities must contain JPEG quality values from 1 to 100")
    if window_size < 3:
        raise ValueError("window_size must be at least 3")

    original = prepared.rgb.astype(np.float32) / 255.0
    local_errors = []
    for quality in quality_values:
        buffer = BytesIO()
        Image.fromarray(prepared.rgb).save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        with Image.open(buffer) as recompressed:
            candidate = np.asarray(recompressed.convert("RGB"), dtype=np.float32) / 255.0
        squared_error = np.mean(np.square(original - candidate), axis=2)
        local_errors.append(uniform_filter(squared_error, size=window_size, mode="reflect"))

    error_stack = np.stack(local_errors)
    profile_scale = np.median(error_stack, axis=(1, 2), keepdims=True) + 1e-8
    response = error_stack / profile_scale
    best_index = np.argmin(response, axis=0)
    best_response = np.take_along_axis(response, best_index[None, ...], axis=0)[0]
    quality_map = np.asarray(quality_values, dtype=np.float32)[best_index]
    neighborhood_quality = uniform_filter(quality_map, size=window_size, mode="reflect")
    disagreement = np.abs(quality_map - neighborhood_quality)
    confidence = robust_normalize(np.max(response, axis=0) - np.min(response, axis=0))
    suspicion = disagreement * (0.25 + confidence)
    dominant_quality = quality_values[int(np.bincount(best_index.ravel()).argmax())]
    return CueResult(
        "jpeg_ghost",
        robust_normalize(suspicion),
        True,
        metadata={
            "tested_qualities": quality_values,
            "dominant_quality": dominant_quality,
            "window_size": window_size,
            "measure": "local best-quality disagreement weighted by quality-response contrast",
            "interpretation": "compression-history inconsistency; not an authenticity proof",
        },
    )


def resampling_trace(
    image: PreprocessedImage | np.ndarray,
    *,
    window_size: int = 15,
) -> CueResult:
    prepared = _prepare(image)
    if window_size < 5 or window_size % 2 == 0:
        raise ValueError("window_size must be an odd integer of at least 5")

    gray = prepared.gray
    second_difference = cv2.filter2D(
        gray, cv2.CV_32F, np.array([[1, -2, 1]], dtype=np.float32), borderType=cv2.BORDER_REFLECT,
    )
    half = window_size // 2
    tile = max(3, window_size // 3)
    periodicity = np.zeros_like(gray, dtype=np.float32)
    counts = np.zeros_like(gray, dtype=np.float32)
    for y in range(half, gray.shape[0] - half, tile):
        for x in range(half, gray.shape[1] - half, tile):
            patch = second_difference[y - half : y + half + 1, x - half : x + half + 1]
            window = np.hanning(patch.shape[0])[:, None] * np.hanning(patch.shape[1])[None, :]
            spectrum = np.abs(np.fft.fftshift(np.fft.fft2(patch * window)))
            cy, cx = np.array(spectrum.shape) // 2
            spectrum[max(0, cy - 2) : cy + 3, max(0, cx - 2) : cx + 3] = 0.0
            peak = float(np.percentile(spectrum, 99.5))
            background = float(np.median(spectrum)) + 1e-8
            score = np.log1p(peak / background)
            periodicity[y, x] = score
            counts[y, x] = 1.0
    periodicity = gaussian_filter(periodicity, sigma=max(1.0, tile))
    available = bool(np.count_nonzero(counts))
    return CueResult(
        "resampling_trace",
        robust_normalize(periodicity),
        True,
        metadata={
            "window_size": window_size,
            "method": "local FFT periodic-correlation response of second-difference residual",
            "periodicity_windows": int(np.count_nonzero(counts)),
            "interpretation": "resampling periodicity evidence; not a general smoothness score",
        },
    )


def jpeg_block_grid(
    image: PreprocessedImage | np.ndarray,
    *,
    block_size: int = 8,
) -> CueResult:
    prepared = _prepare(image)
    if not prepared.is_jpeg:
        return CueResult(
            "jpeg_block_grid",
            _empty(prepared),
            False,
            "JPEG block-grid evidence is unavailable for a non-JPEG or array input",
            {"block_size": block_size},
        )
    if prepared.metadata and prepared.metadata.get("resized", False):
        return CueResult(
            "jpeg_block_grid",
            _empty(prepared),
            False,
            "JPEG block cue disabled because preprocessing resized the source image",
            {
                "block_size": block_size,
                "original_size": prepared.metadata.get("original_size"),
                "processed_size": prepared.metadata.get("processed_size"),
                "interpretation": "heuristic block anomaly; not double-JPEG proof",
            },
        )
    if block_size < 4:
        raise ValueError("block_size must be at least 4")

    gray = prepared.gray
    height, width = gray.shape
    rows, columns = height // block_size, width // block_size
    if rows < 2 or columns < 2:
        return CueResult(
            "jpeg_block_grid",
            _empty(prepared),
            True,
            "image is too small for block-grid comparison",
            {"block_size": block_size, "blocks": rows * columns},
        )

    features = np.zeros((rows, columns, 2), dtype=np.float32)
    for row in range(rows):
        for column in range(columns):
            y0, x0 = row * block_size, column * block_size
            block = gray[y0 : y0 + block_size, x0 : x0 + block_size]
            dct = cv2.dct(block)
            high_frequency = dct.copy()
            high_frequency[:2, :2] = 0.0
            spectral_energy = float(np.mean(np.abs(high_frequency)))
            boundary = 0.0
            count = 0
            if row > 0:
                boundary += float(np.mean(np.abs(block[0] - gray[y0 - 1, x0 : x0 + block_size])))
                count += 1
            if column > 0:
                boundary += float(np.mean(np.abs(block[:, 0] - gray[y0 : y0 + block_size, x0 - 1])))
                count += 1
            features[row, column] = (spectral_energy, boundary / max(count, 1))

    anomaly = np.zeros((rows, columns), dtype=np.float32)
    for channel in range(features.shape[2]):
        plane = features[..., channel]
        median = float(np.median(plane))
        mad = float(np.median(np.abs(plane - median))) + 1e-8
        anomaly += np.abs(plane - median) / (1.4826 * mad)
    block_map = robust_normalize(anomaly)
    expanded = cv2.resize(block_map, (columns * block_size, rows * block_size), interpolation=cv2.INTER_NEAREST)
    output = np.zeros(prepared.shape, dtype=np.float32)
    output[: expanded.shape[0], : expanded.shape[1]] = expanded
    if expanded.shape[0] < height:
        output[expanded.shape[0] :, : expanded.shape[1]] = expanded[-1:, :]
    if expanded.shape[1] < width:
        output[:, expanded.shape[1] :] = output[:, expanded.shape[1] - 1 : expanded.shape[1]]
    return CueResult(
        "jpeg_block_grid",
        output,
        True,
        metadata={
            "block_size": block_size,
            "blocks": rows * columns,
            "method": "DCT energy and block-boundary anomaly heuristic",
            "interpretation": "JPEG block-grid inconsistency; not double-JPEG proof",
        },
    )


def _prepare(image: PreprocessedImage | np.ndarray) -> PreprocessedImage:
    return image if isinstance(image, PreprocessedImage) else from_array(image)


def _empty(image: PreprocessedImage) -> np.ndarray:
    return np.zeros(image.shape, dtype=np.float32)


def _deduplicate_matches(matches: list[cv2.DMatch]) -> list[cv2.DMatch]:
    unique: dict[tuple[int, int], cv2.DMatch] = {}
    for match in matches:
        pair = tuple(sorted((match.queryIdx, match.trainIdx)))
        if pair not in unique or match.distance < unique[pair].distance:
            unique[pair] = match
    return list(unique.values())


def _point_extent(points: np.ndarray) -> float:
    if len(points) < 2:
        return 0.0
    return float(np.linalg.norm(np.ptp(points, axis=0)))
