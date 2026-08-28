#!/usr/bin/env python3
"""P0: image-only common apparent motion observability at PERSON scale.

The implementation deliberately separates R01 discovery/freeze from R04 held-out
validation.  It estimates image-domain transport from background features only;
it does not estimate platform trajectory, RCS, identity, or final SAR boxes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
OUTPUT_STUDY_DIR = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OUTPUT_DIR = OUTPUT_STUDY_DIR / "p0_common_apparent_motion"
INTERMEDIATE_DIR = OUTPUT_DIR / "intermediate"
VIS_DIR = OUTPUT_DIR / "visualizations"
CONTRACT_PATH = OUTPUT_STUDY_DIR / "research_contract_v1.json"
EXPLORER_PATH = (
    WORKSPACE
    / "output"
    / "person_multidimensional_response_explorer_20260823"
    / "explorer_data.js"
)
MODEL_SELECTION_PATH = OUTPUT_DIR / "model_selection_R01.json"
QUANT_VALIDATION_PATH = OUTPUT_DIR / "frozen_validation_R04_quantitative.json"
FINAL_VALIDATION_PATH = OUTPUT_DIR / "frozen_validation_R04.json"
MANUAL_REVIEW_PATH = OUTPUT_DIR / "MULTIMODAL_WORST_FRAME_REVIEW.md"

DISCOVERY_RUN = "R01ZF"
HELDOUT_RUN = "R04ZF"
MODELS = ("M0", "M1", "M2", "M3")


ALGORITHM_CONFIG: dict[str, Any] = {
    "schema": "PERSON_P0_COMMON_APPARENT_MOTION_ALGORITHM_V1",
    "lags": [1, 3, 5],
    "representation": "RGB_SCHARR_LOG_PERCENTILE_CLAHE",
    "outer_boundary_margin_m": 1.0,
    "side_boundary_margin_deg": 1.5,
    "inner_range_exclusion_m": 0.75,
    "person_exclusion_margin_px": 24.0,
    "person_exclusion_box_scale": 1.25,
    "mask_min_valid_fraction": 0.98,
    "gftt_max_corners": 360,
    "gftt_quality_level": 0.006,
    "gftt_min_distance_px": 10.0,
    "gftt_block_size": 7,
    "lk_window_px": 41,
    "lk_max_level": 3,
    "lk_max_iterations": 40,
    "lk_epsilon": 0.01,
    "forward_backward_max_px": 1.75,
    "track_ncc_min": 0.05,
    "track_ncc_patch_px": 17,
    "max_track_displacement_px": 35.0,
    "split_cell_px": 48.0,
    "split_modulus": 4,
    "split_holdout_remainder": 0,
    "min_fit_anchors": 24,
    "min_holdout_anchors": 8,
    "min_fit_spatial_cells": 10,
    "m1_huber_delta_px": 1.5,
    "m1_irls_iterations": 8,
    "m2_ransac_threshold_px": 2.0,
    "m2_max_iterations": 4000,
    "m2_confidence": 0.995,
    "m3_basis": ["1", "r", "theta", "r_theta", "r2", "theta2"],
    "m3_min_fit_anchors": 48,
    "m3_min_radial_bins": 4,
    "m3_radial_bin_count": 6,
    "m3_min_azimuth_bins": 5,
    "m3_azimuth_bin_count": 8,
    "m3_ridge": 0.001,
    "m3_huber_delta_px": 1.5,
    "m3_irls_iterations": 10,
    "display_histogram_bins": 64,
    "display_elevated_quantile_R01": 0.90,
    "display_high_quantile_R01": 0.975,
    "selection_required_availability": 0.90,
    "selection_required_improvement_fraction": 0.50,
    "selection_complexity_relative_tolerance": 0.05,
    "selection_complexity_absolute_tolerance_px": 0.05,
    "validation_min_comparable_fraction": 0.75,
    "validation_background_improvement_fraction": 0.75,
    "validation_min_manual_person_pairs": 10,
    "worst_pair_count": 6,
    "visual_vector_scale": 8.0,
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def sha256_object(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest().upper()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    text = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)
    atomic_write_text(path, text)


def assert_workspace_scope() -> None:
    expected = Path(r"D:\profile\research\workspace").resolve()
    if WORKSPACE.resolve() != expected:
        raise RuntimeError(f"workspace mismatch: {WORKSPACE} != {expected}")
    for path in (TASK_DIR, OUTPUT_DIR, CONTRACT_PATH, EXPLORER_PATH):
        if "old_work" in str(path).lower():
            raise RuntimeError(f"forbidden old_work dependency: {path}")


def load_contract_and_verify() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []
    for item in contract["input_snapshot"]:
        path = Path(item["path"])
        actual = sha256_file(path) if path.is_file() else "MISSING"
        checks.append(
            {
                "kind": "input_snapshot",
                "path": str(path),
                "expected_sha256": item["sha256"].upper(),
                "actual_sha256": actual,
                "match": actual == item["sha256"].upper(),
            }
        )
    probe = contract["invalidated_probe"]
    probe_path = Path(probe["path"])
    probe_actual = sha256_file(probe_path) if probe_path.is_file() else "MISSING"
    checks.append(
        {
            "kind": "invalidated_probe_reference",
            "path": str(probe_path),
            "expected_sha256": probe["sha256"].upper(),
            "actual_sha256": probe_actual,
            "match": probe_actual == probe["sha256"].upper(),
            "allowed_use": probe["allowed_use"],
        }
    )
    failures = [row for row in checks if not row["match"]]
    if failures:
        raise RuntimeError("frozen input SHA256 mismatch: " + json.dumps(failures, ensure_ascii=False))
    return contract, checks


def load_explorer() -> dict[str, Any]:
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    payload = text[text.index("=") + 1 :].strip().rstrip(";")
    return json.loads(payload)


def file_url_to_path(url: str) -> Path:
    if not url.startswith("file:///"):
        raise ValueError(f"expected read-only local file URL, got {url}")
    return Path(url[len("file:///") :])


def js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    p = np.asarray(p, dtype=np.float64)
    q = np.asarray(q, dtype=np.float64)
    p = p / max(float(p.sum()), 1e-12)
    q = q / max(float(q.sum()), 1e-12)
    m = 0.5 * (p + q)

    def kl(a: np.ndarray, b: np.ndarray) -> float:
        nz = a > 0
        return float(np.sum(a[nz] * np.log2(a[nz] / np.maximum(b[nz], 1e-12))))

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def robust_percentile_scale(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    sample = values[mask]
    if sample.size == 0:
        return np.zeros(values.shape, dtype=np.uint8)
    lo, hi = np.percentile(sample, [1.0, 99.5])
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo + 1e-6:
        return np.zeros(values.shape, dtype=np.uint8)
    scaled = np.clip((values - lo) * (255.0 / (hi - lo)), 0, 255).astype(np.uint8)
    return scaled


def build_base_mask(frame: dict[str, Any], image: np.ndarray, config: dict[str, Any]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    height, width = image.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    geometry = frame["geometry"]
    cx = float(geometry["center_x_px"])
    cy = float(geometry["center_y_px"])
    radius = float(geometry["radius_px"])
    outer_range_m = float(geometry["outer_range_m"])
    px_per_m = radius / outer_range_m
    radial = np.hypot(xx - cx, yy - cy)
    theta = np.degrees(np.arctan2(xx - cx, cy - yy))
    outer_limit = radius - float(config["outer_boundary_margin_m"]) * px_per_m
    inner_limit = float(config["inner_range_exclusion_m"]) * px_per_m
    theta_low = float(frame["theta_low_deg"]) + float(config["side_boundary_margin_deg"])
    theta_high = float(frame["theta_high_deg"]) - float(config["side_boundary_margin_deg"])
    nonwhite = np.any(image < 248, axis=2)
    mask = (
        (radial >= inner_limit)
        & (radial <= outer_limit)
        & (theta >= theta_low)
        & (theta <= theta_high)
        & nonwhite
    )
    mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    fields = {"radial": radial, "theta": theta}
    return mask, fields


def build_person_mask(frame: dict[str, Any], shape: tuple[int, int], config: dict[str, Any]) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    margin = float(config["person_exclusion_margin_px"])
    scale = float(config["person_exclusion_box_scale"])
    for ann in frame.get("annotations", []):
        width = float(ann["width"]) * scale + 2.0 * margin
        height = float(ann["height"]) * scale + 2.0 * margin
        rect = (
            (float(ann["cx"]), float(ann["cy"])),
            (max(width, 1.0), max(height, 1.0)),
            float(ann.get("rotation_deg", 0.0)),
        )
        polygon = np.rint(cv2.boxPoints(rect)).astype(np.int32)
        cv2.fillConvexPoly(mask, polygon, 1)
    return mask.astype(bool)


def build_representation(image: np.ndarray, base_mask: np.ndarray) -> np.ndarray:
    image_f = image.astype(np.float32) / 255.0
    magnitude_sq = np.zeros(image.shape[:2], dtype=np.float32)
    for channel in range(3):
        gx = cv2.Scharr(image_f[:, :, channel], cv2.CV_32F, 1, 0)
        gy = cv2.Scharr(image_f[:, :, channel], cv2.CV_32F, 0, 1)
        magnitude_sq += gx * gx + gy * gy
    magnitude = np.log1p(np.sqrt(magnitude_sq))
    scaled = robust_percentile_scale(magnitude, base_mask)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(scaled)


@dataclass
class CachedFrame:
    metadata: dict[str, Any]
    image_path: Path
    representation: np.ndarray
    display_gray: np.ndarray
    base_mask: np.ndarray
    radial: np.ndarray
    theta: np.ndarray
    person_mask: np.ndarray


def load_run_cache(explorer: dict[str, Any], run_id: str, config: dict[str, Any]) -> list[CachedFrame]:
    frames = sorted(
        (frame for frame in explorer["frames"] if frame["run_id"] == run_id),
        key=lambda frame: int(frame["sar_frame_index"]),
    )
    cache: list[CachedFrame] = []
    for index, frame in enumerate(frames):
        image_path = file_url_to_path(frame["sar_image_url"])
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(f"cannot read SAR image: {image_path}")
        if image.shape[1] != int(frame["sar_width_px"]) or image.shape[0] != int(frame["sar_height_px"]):
            raise RuntimeError(f"image dimension mismatch: {image_path}")
        base_mask, fields = build_base_mask(frame, image, config)
        person_mask = build_person_mask(frame, image.shape[:2], config)
        representation = build_representation(image, base_mask)
        display_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        cache.append(
            CachedFrame(
                metadata=frame,
                image_path=image_path,
                representation=representation,
                display_gray=display_gray,
                base_mask=base_mask,
                radial=fields["radial"],
                theta=fields["theta"],
                person_mask=person_mask,
            )
        )
        if (index + 1) % 50 == 0 or index + 1 == len(frames):
            print(f"loaded {run_id} frames {index + 1}/{len(frames)}", flush=True)
    return cache


def patch_ncc(image_a: np.ndarray, point_a: np.ndarray, image_b: np.ndarray, point_b: np.ndarray, size: int) -> float:
    patch_a = cv2.getRectSubPix(image_a, (size, size), (float(point_a[0]), float(point_a[1]))).astype(np.float32)
    patch_b = cv2.getRectSubPix(image_b, (size, size), (float(point_b[0]), float(point_b[1]))).astype(np.float32)
    patch_a -= float(patch_a.mean())
    patch_b -= float(patch_b.mean())
    denom = float(np.linalg.norm(patch_a) * np.linalg.norm(patch_b))
    if denom <= 1e-8:
        return -1.0
    return float(np.sum(patch_a * patch_b) / denom)


def anchor_holdout_mask(points: np.ndarray, config: dict[str, Any]) -> np.ndarray:
    cell = float(config["split_cell_px"])
    cx = np.floor(points[:, 0] / cell).astype(np.int64)
    cy = np.floor(points[:, 1] / cell).astype(np.int64)
    code = (cx * 3 + cy * 5) % int(config["split_modulus"])
    return code == int(config["split_holdout_remainder"])


def spatial_cell_count(points: np.ndarray, cell_px: float) -> int:
    if len(points) == 0:
        return 0
    cells = np.stack([np.floor(points[:, 0] / cell_px), np.floor(points[:, 1] / cell_px)], axis=1).astype(np.int64)
    return int(len(np.unique(cells, axis=0)))


def track_background_anchors(a: CachedFrame, b: CachedFrame, config: dict[str, Any]) -> dict[str, Any]:
    pair_mask = a.base_mask & b.base_mask & ~a.person_mask & ~b.person_mask
    pair_mask_u8 = pair_mask.astype(np.uint8)
    distance = cv2.distanceTransform(pair_mask_u8, cv2.DIST_L2, 3)
    window_radius = (int(config["lk_window_px"]) - 1) / 2.0
    detection_mask = (distance >= window_radius + 3.0).astype(np.uint8) * 255
    valid_fraction = float(pair_mask.mean())
    if valid_fraction <= 0.01:
        return {
            "pair_mask": pair_mask,
            "valid_fraction": valid_fraction,
            "points": np.empty((0, 2), np.float32),
            "tracked": np.empty((0, 2), np.float32),
            "fb_error": np.empty((0,), np.float32),
            "ncc": np.empty((0,), np.float32),
            "holdout": np.empty((0,), bool),
            "reason": "LOW_VALID_PIXEL_FRACTION",
        }
    p0 = cv2.goodFeaturesToTrack(
        a.representation,
        maxCorners=int(config["gftt_max_corners"]),
        qualityLevel=float(config["gftt_quality_level"]),
        minDistance=float(config["gftt_min_distance_px"]),
        mask=detection_mask,
        blockSize=int(config["gftt_block_size"]),
        useHarrisDetector=False,
    )
    if p0 is None or len(p0) == 0:
        return {
            "pair_mask": pair_mask,
            "valid_fraction": valid_fraction,
            "points": np.empty((0, 2), np.float32),
            "tracked": np.empty((0, 2), np.float32),
            "fb_error": np.empty((0,), np.float32),
            "ncc": np.empty((0,), np.float32),
            "holdout": np.empty((0,), bool),
            "reason": "NO_BACKGROUND_FEATURES",
        }
    lk_params = {
        "winSize": (int(config["lk_window_px"]), int(config["lk_window_px"])),
        "maxLevel": int(config["lk_max_level"]),
        "criteria": (
            cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
            int(config["lk_max_iterations"]),
            float(config["lk_epsilon"]),
        ),
    }
    p1, status_forward, _ = cv2.calcOpticalFlowPyrLK(a.representation, b.representation, p0, None, **lk_params)
    if p1 is None:
        status_forward = np.zeros((len(p0), 1), dtype=np.uint8)
        p1 = np.zeros_like(p0)
    p0_back, status_backward, _ = cv2.calcOpticalFlowPyrLK(b.representation, a.representation, p1, None, **lk_params)
    if p0_back is None:
        status_backward = np.zeros((len(p0), 1), dtype=np.uint8)
        p0_back = np.zeros_like(p0)
    points = p0.reshape(-1, 2)
    tracked = p1.reshape(-1, 2)
    back = p0_back.reshape(-1, 2)
    status = status_forward.reshape(-1).astype(bool) & status_backward.reshape(-1).astype(bool)
    finite = np.isfinite(points).all(axis=1) & np.isfinite(tracked).all(axis=1) & np.isfinite(back).all(axis=1)
    height, width = pair_mask.shape
    rounded_start = np.rint(points).astype(np.int32)
    rounded_end = np.rint(tracked).astype(np.int32)
    inside = (
        (rounded_start[:, 0] >= 0)
        & (rounded_start[:, 0] < width)
        & (rounded_start[:, 1] >= 0)
        & (rounded_start[:, 1] < height)
        & (rounded_end[:, 0] >= 0)
        & (rounded_end[:, 0] < width)
        & (rounded_end[:, 1] >= 0)
        & (rounded_end[:, 1] < height)
    )
    mask_ok = np.zeros(len(points), dtype=bool)
    valid_indices = np.flatnonzero(inside)
    mask_ok[valid_indices] = pair_mask[
        rounded_start[valid_indices, 1], rounded_start[valid_indices, 0]
    ] & pair_mask[rounded_end[valid_indices, 1], rounded_end[valid_indices, 0]]
    fb_error = np.linalg.norm(back - points, axis=1)
    displacement = np.linalg.norm(tracked - points, axis=1)
    preliminary = (
        status
        & finite
        & inside
        & mask_ok
        & (fb_error <= float(config["forward_backward_max_px"]))
        & (displacement <= float(config["max_track_displacement_px"]))
    )
    ncc = np.full(len(points), -1.0, dtype=np.float32)
    patch_size = int(config["track_ncc_patch_px"])
    for idx in np.flatnonzero(preliminary):
        ncc[idx] = patch_ncc(a.representation, points[idx], b.representation, tracked[idx], patch_size)
    keep = preliminary & (ncc >= float(config["track_ncc_min"]))
    points = points[keep].astype(np.float64)
    tracked = tracked[keep].astype(np.float64)
    fb_error = fb_error[keep].astype(np.float64)
    ncc = ncc[keep].astype(np.float64)
    holdout = anchor_holdout_mask(points, config) if len(points) else np.empty((0,), bool)
    return {
        "pair_mask": pair_mask,
        "valid_fraction": valid_fraction,
        "points": points,
        "tracked": tracked,
        "fb_error": fb_error,
        "ncc": ncc,
        "holdout": holdout,
        "reason": "OK",
    }


def robust_translation(displacements: np.ndarray, delta: float, iterations: int) -> np.ndarray:
    location = np.median(displacements, axis=0)
    for _ in range(iterations):
        residual = np.linalg.norm(displacements - location, axis=1)
        weights = np.ones_like(residual)
        high = residual > delta
        weights[high] = delta / np.maximum(residual[high], 1e-9)
        new_location = np.sum(displacements * weights[:, None], axis=0) / max(float(weights.sum()), 1e-9)
        if float(np.linalg.norm(new_location - location)) < 1e-5:
            location = new_location
            break
        location = new_location
    return location


def polar_basis(points: np.ndarray, geometry: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cx = float(geometry["center_x_px"])
    cy = float(geometry["center_y_px"])
    radius = float(geometry["radius_px"])
    vx = points[:, 0] - cx
    vy = points[:, 1] - cy
    radial_px = np.hypot(vx, vy)
    safe = np.maximum(radial_px, 1e-6)
    radial_unit = np.stack([vx / safe, vy / safe], axis=1)
    tangential_unit = np.stack([radial_unit[:, 1], -radial_unit[:, 0]], axis=1)
    r = radial_px / radius
    theta_deg = np.degrees(np.arctan2(vx, cy - points[:, 1]))
    theta = theta_deg / 60.0
    design = np.stack([np.ones_like(r), r, theta, r * theta, r * r, theta * theta], axis=1)
    return design, radial_unit, tangential_unit


def robust_ridge_multivariate(
    design: np.ndarray,
    target: np.ndarray,
    ridge: float,
    delta: float,
    iterations: int,
) -> np.ndarray:
    weights = np.ones(len(design), dtype=np.float64)
    coefficients = np.zeros((design.shape[1], target.shape[1]), dtype=np.float64)
    penalty = np.eye(design.shape[1], dtype=np.float64) * ridge
    penalty[0, 0] = ridge * 0.01
    for _ in range(iterations):
        sqrt_w = np.sqrt(weights)[:, None]
        weighted_design = design * sqrt_w
        weighted_target = target * sqrt_w
        lhs = weighted_design.T @ weighted_design + penalty
        rhs = weighted_design.T @ weighted_target
        coefficients = np.linalg.solve(lhs, rhs)
        residual = np.linalg.norm(target - design @ coefficients, axis=1)
        new_weights = np.ones_like(residual)
        high = residual > delta
        new_weights[high] = delta / np.maximum(residual[high], 1e-9)
        if float(np.max(np.abs(new_weights - weights))) < 1e-4:
            weights = new_weights
            break
        weights = new_weights
    return coefficients


def fit_models(
    points: np.ndarray,
    tracked: np.ndarray,
    holdout: np.ndarray,
    geometry: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    fit_points = points[~holdout]
    fit_tracked = tracked[~holdout]
    fit_disp = fit_tracked - fit_points
    models: dict[str, dict[str, Any]] = {
        "M0": {"model": "M0", "available": True, "parameters": {}},
        "M1": {"model": "M1", "available": False, "reason": "INSUFFICIENT_FIT_ANCHORS"},
        "M2": {"model": "M2", "available": False, "reason": "INSUFFICIENT_FIT_ANCHORS"},
        "M3": {"model": "M3", "available": False, "reason": "INSUFFICIENT_OR_POOR_COVERAGE"},
    }
    if len(fit_points) >= int(config["min_fit_anchors"]):
        translation = robust_translation(
            fit_disp,
            float(config["m1_huber_delta_px"]),
            int(config["m1_irls_iterations"]),
        )
        models["M1"] = {
            "model": "M1",
            "available": True,
            "parameters": {"translation_xy": translation.tolist()},
        }
        affine, inliers = cv2.estimateAffine2D(
            fit_points.astype(np.float32),
            fit_tracked.astype(np.float32),
            method=cv2.RANSAC,
            ransacReprojThreshold=float(config["m2_ransac_threshold_px"]),
            maxIters=int(config["m2_max_iterations"]),
            confidence=float(config["m2_confidence"]),
            refineIters=10,
        )
        if affine is not None and np.isfinite(affine).all():
            models["M2"] = {
                "model": "M2",
                "available": True,
                "parameters": {"affine_2x3": affine.astype(float).tolist()},
                "fit_inlier_count": int(inliers.sum()) if inliers is not None else None,
            }
    if len(fit_points) >= int(config["m3_min_fit_anchors"]):
        design, radial_unit, tangential_unit = polar_basis(fit_points, geometry)
        radial = design[:, 1]
        theta = design[:, 2]
        radial_bins = np.clip(
            np.floor(radial * int(config["m3_radial_bin_count"])).astype(int),
            0,
            int(config["m3_radial_bin_count"]) - 1,
        )
        theta_unit = np.clip((theta + 1.0) / 2.0, 0.0, 0.999999)
        theta_bins = np.floor(theta_unit * int(config["m3_azimuth_bin_count"])).astype(int)
        radial_bin_count = int(len(np.unique(radial_bins)))
        theta_bin_count = int(len(np.unique(theta_bins)))
        if (
            radial_bin_count >= int(config["m3_min_radial_bins"])
            and theta_bin_count >= int(config["m3_min_azimuth_bins"])
        ):
            polar_target = np.stack(
                [np.sum(fit_disp * radial_unit, axis=1), np.sum(fit_disp * tangential_unit, axis=1)],
                axis=1,
            )
            coefficients = robust_ridge_multivariate(
                design,
                polar_target,
                float(config["m3_ridge"]),
                float(config["m3_huber_delta_px"]),
                int(config["m3_irls_iterations"]),
            )
            models["M3"] = {
                "model": "M3",
                "available": True,
                "parameters": {
                    "polar_coefficients_6x2": coefficients.tolist(),
                    "basis": list(config["m3_basis"]),
                },
                "fit_radial_bin_count": radial_bin_count,
                "fit_azimuth_bin_count": theta_bin_count,
            }
    return models


def predict_displacement(model: dict[str, Any], points: np.ndarray, geometry: dict[str, Any]) -> np.ndarray:
    points = np.atleast_2d(points).astype(np.float64)
    name = model["model"]
    if name == "M0":
        return np.zeros_like(points)
    if name == "M1":
        translation = np.asarray(model["parameters"]["translation_xy"], dtype=np.float64)
        return np.repeat(translation[None, :], len(points), axis=0)
    if name == "M2":
        affine = np.asarray(model["parameters"]["affine_2x3"], dtype=np.float64)
        destination = points @ affine[:, :2].T + affine[:, 2]
        return destination - points
    if name == "M3":
        design, radial_unit, tangential_unit = polar_basis(points, geometry)
        coefficients = np.asarray(model["parameters"]["polar_coefficients_6x2"], dtype=np.float64)
        polar_disp = design @ coefficients
        return polar_disp[:, 0, None] * radial_unit + polar_disp[:, 1, None] * tangential_unit
    raise ValueError(f"unknown model {name}")


def display_histogram(gray: np.ndarray, mask: np.ndarray, bins: int) -> np.ndarray:
    pixels = gray[mask]
    if pixels.size == 0:
        return np.zeros(bins, dtype=np.float64)
    hist, _ = np.histogram(pixels, bins=bins, range=(0, 256))
    return hist.astype(np.float64)


def annotation_map(frame: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {ann["instance_id"]: ann for ann in frame.get("annotations", [])}


def manual_source(source: str) -> bool:
    return source.startswith("MANUAL")


def pair_identity(a: CachedFrame, b: CachedFrame, lag: int) -> dict[str, Any]:
    return {
        "run_id": a.metadata["run_id"],
        "from_frame": int(a.metadata["sar_frame_index"]),
        "to_frame": int(b.metadata["sar_frame_index"]),
        "from_frame_uid": a.metadata["sar_frame_uid"],
        "to_frame_uid": b.metadata["sar_frame_uid"],
        "lag": int(lag),
    }


def process_run(explorer: dict[str, Any], run_id: str, config: dict[str, Any]) -> dict[str, Any]:
    cache = load_run_cache(explorer, run_id, config)
    pair_rows: list[dict[str, Any]] = []
    anchor_rows: list[dict[str, Any]] = []
    person_rows: list[dict[str, Any]] = []
    comparability_rows: list[dict[str, Any]] = []
    parameter_rows: list[dict[str, Any]] = []
    scheduled = sum(max(0, len(cache) - int(lag)) for lag in config["lags"])
    completed = 0
    for lag in config["lags"]:
        lag = int(lag)
        for index in range(len(cache) - lag):
            a = cache[index]
            b = cache[index + lag]
            identity = pair_identity(a, b, lag)
            tracks = track_background_anchors(a, b, config)
            points = tracks["points"]
            tracked = tracks["tracked"]
            holdout = tracks["holdout"]
            n_fit = int((~holdout).sum())
            n_holdout = int(holdout.sum())
            fit_cells = spatial_cell_count(points[~holdout], float(config["split_cell_px"]))
            comparable = (
                tracks["reason"] == "OK"
                and n_fit >= int(config["min_fit_anchors"])
                and n_holdout >= int(config["min_holdout_anchors"])
                and fit_cells >= int(config["min_fit_spatial_cells"])
            )
            if tracks["reason"] != "OK":
                reason = tracks["reason"]
            elif n_fit < int(config["min_fit_anchors"]):
                reason = "INSUFFICIENT_FIT_ANCHORS"
            elif n_holdout < int(config["min_holdout_anchors"]):
                reason = "INSUFFICIENT_HOLDOUT_ANCHORS"
            elif fit_cells < int(config["min_fit_spatial_cells"]):
                reason = "INSUFFICIENT_SPATIAL_COVERAGE"
            else:
                reason = "COMPARABLE"
            bins = int(config["display_histogram_bins"])
            hist_a = display_histogram(a.display_gray, tracks["pair_mask"], bins)
            hist_b = display_histogram(b.display_gray, tracks["pair_mask"], bins)
            display_js = js_divergence(hist_a, hist_b) if hist_a.sum() > 0 and hist_b.sum() > 0 else math.nan
            rounded = np.rint(points).astype(np.int32) if len(points) else np.empty((0, 2), np.int32)
            person_violations = (
                int(np.count_nonzero(a.person_mask[rounded[:, 1], rounded[:, 0]] | b.person_mask[rounded[:, 1], rounded[:, 0]]))
                if len(rounded)
                else 0
            )
            boundary_violations = (
                int(np.count_nonzero(~a.base_mask[rounded[:, 1], rounded[:, 0]] | ~b.base_mask[rounded[:, 1], rounded[:, 0]]))
                if len(rounded)
                else 0
            )
            comparability_rows.append(
                {
                    **identity,
                    "scheduled": True,
                    "comparable": bool(comparable),
                    "comparability_reason": reason,
                    "pair_valid_fraction": tracks["valid_fraction"],
                    "tracked_anchor_count": int(len(points)),
                    "fit_anchor_count": n_fit,
                    "holdout_anchor_count": n_holdout,
                    "fit_spatial_cell_count": fit_cells,
                    "display_js_divergence": display_js,
                    "display_stratum": "PENDING_R01_FREEZE",
                    "person_mask_anchor_violations": person_violations,
                    "boundary_mask_anchor_violations": boundary_violations,
                    "target_pixels_used_for_fitting": 0,
                    "difficult_pair_deleted": False,
                }
            )
            if comparable:
                models = fit_models(points, tracked, holdout, a.metadata["geometry"], config)
            else:
                models = {
                    name: {"model": name, "available": False, "reason": reason, "parameters": {}}
                    for name in MODELS
                }
            observed = tracked - points if len(points) else np.empty((0, 2), np.float64)
            prediction_by_model: dict[str, np.ndarray] = {}
            residual_by_model: dict[str, np.ndarray] = {}
            for name in MODELS:
                model = models[name]
                available = bool(comparable and model.get("available", False))
                if available:
                    prediction = predict_displacement(model, points, a.metadata["geometry"])
                    residual = np.linalg.norm(observed - prediction, axis=1)
                    prediction_by_model[name] = prediction
                    residual_by_model[name] = residual
                    fit_residual = residual[~holdout]
                    holdout_residual = residual[holdout]
                    pair_rows.append(
                        {
                            **identity,
                            "model": name,
                            "model_available": True,
                            "comparable": True,
                            "fit_anchor_count": n_fit,
                            "holdout_anchor_count": n_holdout,
                            "fit_residual_median_px": float(np.median(fit_residual)),
                            "fit_residual_p90_px": float(np.percentile(fit_residual, 90)),
                            "holdout_residual_median_px": float(np.median(holdout_residual)),
                            "holdout_residual_p90_px": float(np.percentile(holdout_residual, 90)),
                            "display_js_divergence": display_js,
                            "display_stratum": "PENDING_R01_FREEZE",
                        }
                    )
                else:
                    pair_rows.append(
                        {
                            **identity,
                            "model": name,
                            "model_available": False,
                            "comparable": bool(comparable),
                            "fit_anchor_count": n_fit,
                            "holdout_anchor_count": n_holdout,
                            "fit_residual_median_px": math.nan,
                            "fit_residual_p90_px": math.nan,
                            "holdout_residual_median_px": math.nan,
                            "holdout_residual_p90_px": math.nan,
                            "display_js_divergence": display_js,
                            "display_stratum": "PENDING_R01_FREEZE",
                        }
                    )
                parameter_rows.append(
                    {
                        **identity,
                        "model": name,
                        "model_available": available,
                        "model_state": model,
                    }
                )
            for anchor_index in range(len(points)):
                row: dict[str, Any] = {
                    **identity,
                    "anchor_id": f"{identity['from_frame_uid']}__L{lag}__A{anchor_index:04d}",
                    "anchor_split": "HOLDOUT" if bool(holdout[anchor_index]) else "FIT",
                    "x_px": float(points[anchor_index, 0]),
                    "y_px": float(points[anchor_index, 1]),
                    "observed_dx_px": float(observed[anchor_index, 0]),
                    "observed_dy_px": float(observed[anchor_index, 1]),
                    "forward_backward_error_px": float(tracks["fb_error"][anchor_index]),
                    "local_gradient_ncc": float(tracks["ncc"][anchor_index]),
                    "inside_person_exclusion": False,
                    "inside_boundary_exclusion": False,
                }
                for name in MODELS:
                    if name in prediction_by_model:
                        row[f"{name}_available"] = True
                        row[f"{name}_predicted_dx_px"] = float(prediction_by_model[name][anchor_index, 0])
                        row[f"{name}_predicted_dy_px"] = float(prediction_by_model[name][anchor_index, 1])
                        row[f"{name}_residual_px"] = float(residual_by_model[name][anchor_index])
                    else:
                        row[f"{name}_available"] = False
                        row[f"{name}_predicted_dx_px"] = math.nan
                        row[f"{name}_predicted_dy_px"] = math.nan
                        row[f"{name}_residual_px"] = math.nan
                anchor_rows.append(row)
            anns_a = annotation_map(a.metadata)
            anns_b = annotation_map(b.metadata)
            common_ids = sorted(set(anns_a) & set(anns_b))
            for target_id in common_ids:
                ann_a = anns_a[target_id]
                ann_b = anns_b[target_id]
                start = np.array([[float(ann_a["cx"]), float(ann_a["cy"])]], dtype=np.float64)
                observed_person = np.array(
                    [float(ann_b["cx"]) - float(ann_a["cx"]), float(ann_b["cy"]) - float(ann_a["cy"])],
                    dtype=np.float64,
                )
                for name in MODELS:
                    model = models[name]
                    available = bool(comparable and model.get("available", False))
                    if available:
                        predicted = predict_displacement(model, start, a.metadata["geometry"])[0]
                        residual_vector = observed_person - predicted
                        residual_norm = float(np.linalg.norm(residual_vector))
                    else:
                        predicted = np.array([math.nan, math.nan])
                        residual_vector = np.array([math.nan, math.nan])
                        residual_norm = math.nan
                    person_rows.append(
                        {
                            **identity,
                            "target_id": target_id,
                            "model": name,
                            "model_available": available,
                            "comparable": bool(comparable),
                            "from_source": ann_a["source"],
                            "to_source": ann_b["source"],
                            "both_manual_endpoints": manual_source(ann_a["source"]) and manual_source(ann_b["source"]),
                            "from_cx_px": float(ann_a["cx"]),
                            "from_cy_px": float(ann_a["cy"]),
                            "to_cx_px": float(ann_b["cx"]),
                            "to_cy_px": float(ann_b["cy"]),
                            "observed_dx_px": float(observed_person[0]),
                            "observed_dy_px": float(observed_person[1]),
                            "uncompensated_residual_px": float(np.linalg.norm(observed_person)),
                            "predicted_common_dx_px": float(predicted[0]),
                            "predicted_common_dy_px": float(predicted[1]),
                            "compensated_residual_dx_px": float(residual_vector[0]),
                            "compensated_residual_dy_px": float(residual_vector[1]),
                            "compensated_residual_px": residual_norm,
                            "from_short_axis_px": float(min(ann_a["width"], ann_a["height"])),
                            "to_short_axis_px": float(min(ann_b["width"], ann_b["height"])),
                            "display_js_divergence": display_js,
                            "display_stratum": "PENDING_R01_FREEZE",
                        }
                    )
            completed += 1
            if completed % 25 == 0 or completed == scheduled:
                print(f"processed {run_id} pairs {completed}/{scheduled}", flush=True)
    return {
        "pair_metrics": pd.DataFrame(pair_rows),
        "anchor_metrics": pd.DataFrame(anchor_rows),
        "person_residuals": pd.DataFrame(person_rows),
        "comparability": pd.DataFrame(comparability_rows),
        "model_parameters": parameter_rows,
        "frame_count": len(cache),
        "scheduled_pair_count": scheduled,
    }


def freeze_display_thresholds(comparability: pd.DataFrame, config: dict[str, Any]) -> dict[str, dict[str, float]]:
    thresholds: dict[str, dict[str, float]] = {}
    for lag in config["lags"]:
        values = comparability.loc[
            (comparability["lag"] == int(lag)) & comparability["display_js_divergence"].notna(),
            "display_js_divergence",
        ].to_numpy(dtype=float)
        if len(values) == 0:
            raise RuntimeError(f"no R01 display distribution values for lag {lag}")
        thresholds[str(lag)] = {
            "elevated_threshold": float(np.quantile(values, float(config["display_elevated_quantile_R01"]))),
            "high_threshold": float(np.quantile(values, float(config["display_high_quantile_R01"]))),
            "source": "R01_EMPIRICAL_QUANTILES_FROZEN_BEFORE_R04",
        }
    return thresholds


def apply_display_strata(frame: pd.DataFrame, thresholds: dict[str, dict[str, float]]) -> pd.DataFrame:
    frame = frame.copy()
    strata: list[str] = []
    for row in frame.itertuples(index=False):
        value = float(getattr(row, "display_js_divergence"))
        threshold = thresholds[str(int(getattr(row, "lag")))]
        if not np.isfinite(value):
            strata.append("UNAVAILABLE")
        elif value > float(threshold["high_threshold"]):
            strata.append("HIGH_GLOBAL_DISPLAY_DISTRIBUTION_CHANGE")
        elif value > float(threshold["elevated_threshold"]):
            strata.append("ELEVATED_GLOBAL_DISPLAY_DISTRIBUTION_CHANGE")
        else:
            strata.append("BASELINE_GLOBAL_DISPLAY_DISTRIBUTION")
    frame["display_stratum"] = strata
    return frame


def model_selection_table(pair_metrics: pd.DataFrame, config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    table: list[dict[str, Any]] = []
    selected: dict[str, str] = {}
    complexity = {"M0": 0, "M1": 1, "M2": 2, "M3": 3}
    for lag in config["lags"]:
        lag = int(lag)
        lag_rows = pair_metrics[pair_metrics["lag"] == lag]
        baseline = lag_rows[(lag_rows["model"] == "M0") & lag_rows["model_available"]].copy()
        baseline_map = baseline.set_index(["from_frame_uid", "to_frame_uid"])["holdout_residual_median_px"]
        metrics_by_model: dict[str, dict[str, Any]] = {}
        for model in MODELS:
            rows = lag_rows[(lag_rows["model"] == model) & lag_rows["model_available"]].copy()
            available_fraction = float(len(rows) / max(len(baseline), 1))
            paired_base = [
                float(baseline_map.loc[(row.from_frame_uid, row.to_frame_uid)])
                for row in rows.itertuples(index=False)
                if (row.from_frame_uid, row.to_frame_uid) in baseline_map.index
            ]
            values = rows["holdout_residual_median_px"].to_numpy(dtype=float)
            if len(values):
                base_array = np.asarray(paired_base, dtype=float)
                improvement_fraction = float(np.mean(values < base_array)) if len(base_array) == len(values) else math.nan
                median_residual = float(np.median(values))
                p90_residual = float(np.percentile(values, 90))
                median_relative_change = float(np.median((values - base_array) / np.maximum(base_array, 1e-9)))
            else:
                improvement_fraction = math.nan
                median_residual = math.nan
                p90_residual = math.nan
                median_relative_change = math.nan
            eligible = bool(
                model != "M0"
                and available_fraction >= float(config["selection_required_availability"])
                and np.isfinite(improvement_fraction)
                and improvement_fraction > float(config["selection_required_improvement_fraction"])
                and len(values) > 0
                and median_residual < float(np.median(baseline["holdout_residual_median_px"]))
            )
            metrics = {
                "lag": lag,
                "model": model,
                "available_pair_count": int(len(rows)),
                "baseline_comparable_pair_count": int(len(baseline)),
                "availability_fraction": available_fraction,
                "holdout_pair_median_residual_px": median_residual,
                "holdout_pair_p90_residual_px": p90_residual,
                "paired_improvement_fraction_vs_M0": improvement_fraction,
                "paired_median_relative_change_vs_M0": median_relative_change,
                "eligible_for_selection": eligible,
            }
            metrics_by_model[model] = metrics
            table.append(metrics)
        candidates = [metrics_by_model[name] for name in ("M1", "M2", "M3") if metrics_by_model[name]["eligible_for_selection"]]
        if not candidates:
            selected[str(lag)] = "M0"
            continue
        best = min(candidates, key=lambda row: row["holdout_pair_median_residual_px"])
        tolerance = max(
            float(config["selection_complexity_absolute_tolerance_px"]),
            float(config["selection_complexity_relative_tolerance"]) * float(best["holdout_pair_median_residual_px"]),
        )
        near_best = [
            row
            for row in candidates
            if float(row["holdout_pair_median_residual_px"])
            <= float(best["holdout_pair_median_residual_px"]) + tolerance
        ]
        chosen = min(near_best, key=lambda row: complexity[row["model"]])
        selected[str(lag)] = str(chosen["model"])
    return table, selected


def add_selected_pair_fields(pair_metrics: pd.DataFrame, selected: dict[str, str]) -> pd.DataFrame:
    pair_metrics = pair_metrics.copy()
    pair_metrics["selected_frozen_model"] = [selected[str(int(lag))] for lag in pair_metrics["lag"]]
    pair_metrics["is_selected_frozen_model"] = pair_metrics["model"] == pair_metrics["selected_frozen_model"]
    baseline = pair_metrics[pair_metrics["model"] == "M0"].set_index(
        ["run_id", "from_frame_uid", "to_frame_uid", "lag"]
    )["holdout_residual_median_px"]
    m0_values: list[float] = []
    improved: list[Any] = []
    relative_reduction: list[float] = []
    for row in pair_metrics.itertuples(index=False):
        key = (row.run_id, row.from_frame_uid, row.to_frame_uid, int(row.lag))
        m0 = float(baseline.loc[key]) if key in baseline.index and np.isfinite(baseline.loc[key]) else math.nan
        m0_values.append(m0)
        current = float(row.holdout_residual_median_px)
        if bool(row.model_available) and np.isfinite(current) and np.isfinite(m0):
            improved.append(bool(current < m0))
            relative_reduction.append(float((m0 - current) / max(m0, 1e-9)))
        else:
            improved.append(pd.NA)
            relative_reduction.append(math.nan)
    pair_metrics["M0_holdout_residual_median_px"] = m0_values
    pair_metrics["holdout_improved_vs_M0"] = pd.array(improved, dtype="boolean")
    pair_metrics["holdout_relative_reduction_vs_M0"] = relative_reduction
    return pair_metrics


def write_discovery_outputs(result: dict[str, Any], input_checks: list[dict[str, Any]]) -> dict[str, Any]:
    display_thresholds = freeze_display_thresholds(result["comparability"], ALGORITHM_CONFIG)
    pair_metrics = apply_display_strata(result["pair_metrics"], display_thresholds)
    person_residuals = apply_display_strata(result["person_residuals"], display_thresholds)
    comparability = apply_display_strata(result["comparability"], display_thresholds)
    selection_table, selected = model_selection_table(pair_metrics, ALGORITHM_CONFIG)
    pair_metrics = add_selected_pair_fields(pair_metrics, selected)
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    pair_metrics.to_csv(INTERMEDIATE_DIR / "R01_common_motion_pair_metrics.csv", index=False, encoding="utf-8-sig")
    result["anchor_metrics"].to_csv(
        INTERMEDIATE_DIR / "R01_background_anchor_metrics.csv", index=False, encoding="utf-8-sig"
    )
    person_residuals.to_csv(
        INTERMEDIATE_DIR / "R01_stationary_person_residuals.csv", index=False, encoding="utf-8-sig"
    )
    comparability.to_csv(INTERMEDIATE_DIR / "R01_comparability_registry.csv", index=False, encoding="utf-8-sig")
    write_jsonl(INTERMEDIATE_DIR / "R01_model_parameters_per_pair.jsonl", result["model_parameters"])
    freeze_core = {
        "algorithm_config": ALGORITHM_CONFIG,
        "selected_model_by_lag": selected,
        "display_change_thresholds_by_lag": display_thresholds,
        "input_hash_checks": input_checks,
        "script_sha256": sha256_file(SCRIPT_PATH),
        "discovery_run": DISCOVERY_RUN,
        "heldout_run": HELDOUT_RUN,
        "runs_used_for_model_selection": [DISCOVERY_RUN],
        "R04_used_for_tuning": False,
        "target_regions_used_for_model_selection": False,
    }
    freeze_hash = sha256_object(freeze_core)
    output = {
        "schema": "PERSON_P0_R01_MODEL_SELECTION_AND_FREEZE_V1",
        "created_at": now_iso(),
        "stage_status": "R01_COMPLETE_PARAMETERS_FROZEN_BEFORE_R04",
        "scientific_scope": "IMAGE_DOMAIN_COMMON_APPARENT_MOTION_NOT_PLATFORM_TRAJECTORY",
        "semantic_guards": {
            "person_response": "CONDITIONAL_IMAGE_DOMAIN_RESPONSE_NOT_INTRINSIC_RCS_TEMPLATE",
            "sar_box_track": "NOT_TARGET_INDEPENDENT_MOTION",
            "same_sensor_pixel": "NOT_FIXED_PHYSICAL_BACKGROUND",
            "similarity": "DISPLAY_REPEATABILITY_SOFT_EVIDENCE_ONLY",
            "invalidated_probe_used_for_motion_interpretation": False,
        },
        "frame_count": result["frame_count"],
        "scheduled_pair_count": result["scheduled_pair_count"],
        "comparable_pair_count": int(result["comparability"]["comparable"].sum()),
        "model_comparison": selection_table,
        "selection_rule": {
            "criterion": "R01_BACKGROUND_HOLDOUT_ONLY",
            "target_residual_used_for_selection": False,
            "complexity_guard": "CHOOSE_SIMPLER_MODEL_WITHIN_FROZEN_TOLERANCE_OF_BEST_MEDIAN",
        },
        "frozen": freeze_core,
        "freeze_payload_sha256": freeze_hash,
    }
    write_json(MODEL_SELECTION_PATH, output)
    return output


def load_and_verify_freeze() -> dict[str, Any]:
    freeze = json.loads(MODEL_SELECTION_PATH.read_text(encoding="utf-8"))
    if freeze.get("stage_status") != "R01_COMPLETE_PARAMETERS_FROZEN_BEFORE_R04":
        raise RuntimeError("R01 freeze status is not valid")
    core = freeze["frozen"]
    if sha256_object(core) != freeze["freeze_payload_sha256"]:
        raise RuntimeError("R01 freeze payload hash mismatch")
    current_script_hash = sha256_file(SCRIPT_PATH)
    if core["script_sha256"] != current_script_hash:
        raise RuntimeError(
            "script changed after R01 freeze; rerun discovery before any R04 validation "
            f"({core['script_sha256']} != {current_script_hash})"
        )
    if core.get("R04_used_for_tuning") is not False:
        raise RuntimeError("freeze does not prove R04 isolation")
    if core.get("target_regions_used_for_model_selection") is not False:
        raise RuntimeError("freeze does not prove target exclusion")
    return freeze


def dataframe_bool_sum(series: pd.Series) -> int:
    return int(series.fillna(False).astype(bool).sum())


def person_subset_statistics(person_selected: pd.DataFrame, manual_only: bool) -> dict[str, Any]:
    subset = person_selected[person_selected["both_manual_endpoints"]] if manual_only else person_selected
    subset = subset[subset["model_available"] & subset["compensated_residual_px"].notna()].copy()
    if len(subset) == 0:
        return {
            "subset": "MANUAL_ENDPOINTS" if manual_only else "ALL_ACCEPTED",
            "count": 0,
            "uncompensated_median_px": math.nan,
            "uncompensated_p90_px": math.nan,
            "compensated_median_px": math.nan,
            "compensated_p90_px": math.nan,
            "median_direction": "UNAVAILABLE",
            "p90_direction": "UNAVAILABLE",
        }
    before = subset["uncompensated_residual_px"].to_numpy(dtype=float)
    after = subset["compensated_residual_px"].to_numpy(dtype=float)
    before_median = float(np.median(before))
    before_p90 = float(np.percentile(before, 90))
    after_median = float(np.median(after))
    after_p90 = float(np.percentile(after, 90))
    return {
        "subset": "MANUAL_ENDPOINTS" if manual_only else "ALL_ACCEPTED",
        "count": int(len(subset)),
        "uncompensated_median_px": before_median,
        "uncompensated_p90_px": before_p90,
        "compensated_median_px": after_median,
        "compensated_p90_px": after_p90,
        "median_direction": "LOWER_AFTER_COMPENSATION" if after_median < before_median else "NOT_LOWER_AFTER_COMPENSATION",
        "p90_direction": "LOWER_AFTER_COMPENSATION" if after_p90 < before_p90 else "NOT_LOWER_AFTER_COMPENSATION",
    }


def unique_short_axis_median(explorer: dict[str, Any], run_id: str) -> float:
    values = [
        float(min(ann["width"], ann["height"]))
        for frame in explorer["frames"]
        if frame["run_id"] == run_id
        for ann in frame.get("annotations", [])
    ]
    if not values:
        return math.nan
    return float(np.median(values))


def render_summary_plots(pair_metrics: pd.DataFrame, person_residuals: pd.DataFrame, selected: dict[str, str]) -> None:
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    heldout_selected = pair_metrics[
        (pair_metrics["run_id"] == HELDOUT_RUN)
        & pair_metrics["is_selected_frozen_model"]
        & pair_metrics["model_available"]
    ].copy()
    fig, axes = plt.subplots(1, len(ALGORITHM_CONFIG["lags"]), figsize=(12, 4), constrained_layout=True)
    for axis, lag in zip(axes, ALGORITHM_CONFIG["lags"]):
        rows = heldout_selected[heldout_selected["lag"] == int(lag)]
        axis.boxplot(
            [rows["M0_holdout_residual_median_px"].dropna(), rows["holdout_residual_median_px"].dropna()],
            tick_labels=["M0", selected[str(int(lag))]],
            showfliers=True,
        )
        axis.set_title(f"R04 lag {lag}")
        axis.set_ylabel("背景留出锚点残差 / px")
        axis.grid(alpha=0.25)
    fig.suptitle("R04 冻结模型与无补偿背景残差（困难帧未删除）")
    fig.savefig(VIS_DIR / "R04_background_holdout_residual_by_lag.png", dpi=160)
    plt.close(fig)

    person_selected = person_residuals[
        (person_residuals["run_id"] == HELDOUT_RUN)
        & person_residuals["model_available"]
        & person_residuals.apply(lambda row: row["model"] == selected[str(int(row["lag"]))], axis=1)
    ].copy()
    fig, axis = plt.subplots(figsize=(7, 5), constrained_layout=True)
    axis.boxplot(
        [person_selected["uncompensated_residual_px"], person_selected["compensated_residual_px"]],
        tick_labels=["补偿前", "冻结模型补偿后"],
        showfliers=True,
    )
    axis.set_ylabel("静止 PERSON 框中心残差 / px")
    axis.set_title("R04 静止 PERSON 补偿前后直接残差")
    axis.grid(alpha=0.25)
    fig.savefig(VIS_DIR / "R04_stationary_person_before_after.png", dpi=160)
    plt.close(fig)


def draw_rotated_box(image: np.ndarray, ann: dict[str, Any], color: tuple[int, int, int], thickness: int = 2) -> None:
    rect = (
        (float(ann["cx"]), float(ann["cy"])),
        (float(ann["width"]), float(ann["height"])),
        float(ann.get("rotation_deg", 0.0)),
    )
    polygon = np.rint(cv2.boxPoints(rect)).astype(np.int32)
    cv2.polylines(image, [polygon], True, color, thickness, cv2.LINE_AA)


def draw_expanded_person_regions(image: np.ndarray, frame: dict[str, Any], config: dict[str, Any]) -> None:
    overlay = image.copy()
    margin = float(config["person_exclusion_margin_px"])
    scale = float(config["person_exclusion_box_scale"])
    for ann in frame.get("annotations", []):
        expanded = (
            (float(ann["cx"]), float(ann["cy"])),
            (float(ann["width"]) * scale + 2 * margin, float(ann["height"]) * scale + 2 * margin),
            float(ann.get("rotation_deg", 0.0)),
        )
        polygon = np.rint(cv2.boxPoints(expanded)).astype(np.int32)
        cv2.fillConvexPoly(overlay, polygon, (0, 165, 255))
        cv2.polylines(image, [polygon], True, (0, 165, 255), 1, cv2.LINE_AA)
        draw_rotated_box(image, ann, (0, 0, 255), 2)
    cv2.addWeighted(overlay, 0.18, image, 0.82, 0, image)


def draw_valid_boundaries(image: np.ndarray, frame: dict[str, Any], config: dict[str, Any]) -> None:
    geometry = frame["geometry"]
    cx = float(geometry["center_x_px"])
    cy = float(geometry["center_y_px"])
    radius = float(geometry["radius_px"])
    px_per_m = radius / float(geometry["outer_range_m"])
    valid_radius = radius - float(config["outer_boundary_margin_m"]) * px_per_m
    low = float(frame["theta_low_deg"]) + float(config["side_boundary_margin_deg"])
    high = float(frame["theta_high_deg"]) - float(config["side_boundary_margin_deg"])
    angles = np.linspace(low, high, 200)
    xs = cx + valid_radius * np.sin(np.radians(angles))
    ys = cy - valid_radius * np.cos(np.radians(angles))
    arc = np.rint(np.stack([xs, ys], axis=1)).astype(np.int32)
    cv2.polylines(image, [arc], False, (255, 255, 0), 2, cv2.LINE_AA)
    for angle in (low, high):
        end = (
            int(round(cx + valid_radius * math.sin(math.radians(angle)))),
            int(round(cy - valid_radius * math.cos(math.radians(angle)))),
        )
        cv2.line(image, (int(round(cx)), int(round(cy))), end, (255, 255, 0), 2, cv2.LINE_AA)


def put_title_band(image: np.ndarray, lines: list[str]) -> np.ndarray:
    band_height = 28 + 24 * len(lines)
    output = np.full((image.shape[0] + band_height, image.shape[1], 3), 245, dtype=np.uint8)
    output[band_height:] = image
    for idx, line in enumerate(lines):
        cv2.putText(output, line, (12, 28 + idx * 24), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (20, 20, 20), 1, cv2.LINE_AA)
    return output


def render_worst_pair_sheets(
    explorer: dict[str, Any],
    pair_metrics: pd.DataFrame,
    anchor_metrics: pd.DataFrame,
    selected: dict[str, str],
) -> list[dict[str, Any]]:
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    heldout = pair_metrics[
        (pair_metrics["run_id"] == HELDOUT_RUN)
        & pair_metrics["is_selected_frozen_model"]
        & pair_metrics["model_available"]
    ].copy()
    heldout = heldout.sort_values(
        ["holdout_residual_median_px", "display_js_divergence"], ascending=[False, False]
    )
    worst = heldout.head(int(ALGORITHM_CONFIG["worst_pair_count"]))
    frame_map = {frame["sar_frame_uid"]: frame for frame in explorer["frames"] if frame["run_id"] == HELDOUT_RUN}
    registry: list[dict[str, Any]] = []
    rendered_paths: list[Path] = []
    for rank, row in enumerate(worst.itertuples(index=False), start=1):
        frame_a = frame_map[row.from_frame_uid]
        frame_b = frame_map[row.to_frame_uid]
        image_a = cv2.imread(str(file_url_to_path(frame_a["sar_image_url"])), cv2.IMREAD_COLOR)
        image_b = cv2.imread(str(file_url_to_path(frame_b["sar_image_url"])), cv2.IMREAD_COLOR)
        draw_valid_boundaries(image_a, frame_a, ALGORITHM_CONFIG)
        draw_valid_boundaries(image_b, frame_b, ALGORITHM_CONFIG)
        draw_expanded_person_regions(image_a, frame_a, ALGORITHM_CONFIG)
        draw_expanded_person_regions(image_b, frame_b, ALGORITHM_CONFIG)
        anchors = anchor_metrics[
            (anchor_metrics["run_id"] == HELDOUT_RUN)
            & (anchor_metrics["from_frame_uid"] == row.from_frame_uid)
            & (anchor_metrics["to_frame_uid"] == row.to_frame_uid)
            & (anchor_metrics["lag"] == int(row.lag))
        ].copy()
        if len(anchors) > 120:
            anchors = anchors.iloc[np.linspace(0, len(anchors) - 1, 120).round().astype(int)]
        model = selected[str(int(row.lag))]
        vector_scale = float(ALGORITHM_CONFIG["visual_vector_scale"])
        for anchor in anchors.itertuples(index=False):
            start = np.array([float(anchor.x_px), float(anchor.y_px)])
            observed = np.array([float(anchor.observed_dx_px), float(anchor.observed_dy_px)])
            predicted = np.array(
                [float(getattr(anchor, f"{model}_predicted_dx_px")), float(getattr(anchor, f"{model}_predicted_dy_px"))]
            )
            start_i = tuple(np.rint(start).astype(int))
            observed_i = tuple(np.rint(start + observed * vector_scale).astype(int))
            predicted_i = tuple(np.rint(start + predicted * vector_scale).astype(int))
            split_color = (0, 255, 255) if anchor.anchor_split == "FIT" else (255, 255, 255)
            cv2.circle(image_a, start_i, 2, split_color, -1, cv2.LINE_AA)
            if anchor.anchor_split == "HOLDOUT":
                cv2.arrowedLine(image_b, start_i, observed_i, (255, 255, 255), 1, cv2.LINE_AA, tipLength=0.25)
                cv2.arrowedLine(image_b, start_i, predicted_i, (255, 0, 255), 1, cv2.LINE_AA, tipLength=0.25)
        left = put_title_band(
            image_a,
            [
                f"source {row.from_frame_uid} | yellow=fit white=holdout",
                "red=PERSON box orange=expanded exclusion cyan=valid fan boundary",
            ],
        )
        right = put_title_band(
            image_b,
            [
                f"target {row.to_frame_uid} | white=observed magenta={model} prediction (vectors x{vector_scale:g})",
                f"lag={row.lag} holdout median={row.holdout_residual_median_px:.3f}px M0={row.M0_holdout_residual_median_px:.3f}px JS={row.display_js_divergence:.4f}",
            ],
        )
        sheet = np.concatenate([left, right], axis=1)
        filename = f"worst_{rank:02d}_{HELDOUT_RUN}_{int(row.from_frame):06d}_{int(row.to_frame):06d}_lag{int(row.lag)}.jpg"
        path = VIS_DIR / filename
        cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94])
        rendered_paths.append(path)
        registry.append(
            {
                "rank": rank,
                "run_id": HELDOUT_RUN,
                "from_frame": int(row.from_frame),
                "to_frame": int(row.to_frame),
                "lag": int(row.lag),
                "selected_model": model,
                "holdout_residual_median_px": float(row.holdout_residual_median_px),
                "M0_holdout_residual_median_px": float(row.M0_holdout_residual_median_px),
                "display_js_divergence": float(row.display_js_divergence),
                "display_stratum": row.display_stratum,
                "fit_anchor_count": int(row.fit_anchor_count),
                "holdout_anchor_count": int(row.holdout_anchor_count),
                "visual_path": str(path),
                "manual_multimodal_review": "PENDING",
            }
        )
    if rendered_paths:
        thumbs: list[np.ndarray] = []
        for path in rendered_paths:
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            scale = min(1.0, 1200.0 / image.shape[1])
            image = cv2.resize(image, (int(round(image.shape[1] * scale)), int(round(image.shape[0] * scale))))
            thumbs.append(image)
        width = max(image.shape[1] for image in thumbs)
        padded: list[np.ndarray] = []
        for image in thumbs:
            if image.shape[1] < width:
                pad = np.full((image.shape[0], width - image.shape[1], 3), 255, dtype=np.uint8)
                image = np.concatenate([image, pad], axis=1)
            padded.append(image)
        montage = np.concatenate(padded, axis=0)
        cv2.imwrite(str(VIS_DIR / "R04_worst_pairs_montage.jpg"), montage, [cv2.IMWRITE_JPEG_QUALITY, 92])
    pd.DataFrame(registry).to_csv(OUTPUT_DIR / "worst_case_registry.csv", index=False, encoding="utf-8-sig")
    return registry


def build_quantitative_validation(
    explorer: dict[str, Any],
    freeze: dict[str, Any],
    validation_result: dict[str, Any],
    input_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    selected = freeze["frozen"]["selected_model_by_lag"]
    thresholds = freeze["frozen"]["display_change_thresholds_by_lag"]
    r01_pair = pd.read_csv(INTERMEDIATE_DIR / "R01_common_motion_pair_metrics.csv")
    r01_anchor = pd.read_csv(INTERMEDIATE_DIR / "R01_background_anchor_metrics.csv")
    r01_person = pd.read_csv(INTERMEDIATE_DIR / "R01_stationary_person_residuals.csv")
    r01_comparability = pd.read_csv(INTERMEDIATE_DIR / "R01_comparability_registry.csv")
    r04_pair = apply_display_strata(validation_result["pair_metrics"], thresholds)
    r04_person = apply_display_strata(validation_result["person_residuals"], thresholds)
    r04_comparability = apply_display_strata(validation_result["comparability"], thresholds)
    pair_metrics = pd.concat([r01_pair, r04_pair], ignore_index=True, sort=False)
    pair_metrics = add_selected_pair_fields(pair_metrics, selected)
    anchor_metrics = pd.concat([r01_anchor, validation_result["anchor_metrics"]], ignore_index=True, sort=False)
    person_residuals = pd.concat([r01_person, r04_person], ignore_index=True, sort=False)
    comparability = pd.concat([r01_comparability, r04_comparability], ignore_index=True, sort=False)
    pair_metrics.to_csv(OUTPUT_DIR / "common_motion_pair_metrics.csv", index=False, encoding="utf-8-sig")
    anchor_metrics.to_csv(OUTPUT_DIR / "background_anchor_holdout_metrics.csv", index=False, encoding="utf-8-sig")
    person_residuals.to_csv(OUTPUT_DIR / "stationary_person_residuals.csv", index=False, encoding="utf-8-sig")
    comparability.to_csv(OUTPUT_DIR / "comparability_registry.csv", index=False, encoding="utf-8-sig")
    r01_params = [json.loads(line) for line in (INTERMEDIATE_DIR / "R01_model_parameters_per_pair.jsonl").read_text(encoding="utf-8").splitlines() if line]
    write_jsonl(OUTPUT_DIR / "model_parameters_per_pair.jsonl", [*r01_params, *validation_result["model_parameters"]])

    selected_rows = pair_metrics[
        (pair_metrics["run_id"] == HELDOUT_RUN)
        & pair_metrics["is_selected_frozen_model"]
        & pair_metrics["model_available"]
    ].copy()
    scheduled_pair_count = int(validation_result["scheduled_pair_count"])
    comparable_pair_count = int(r04_comparability["comparable"].sum())
    selected_available_count = int(len(selected_rows))
    comparable_fraction = float(selected_available_count / max(scheduled_pair_count, 1))
    background_improvement_fraction = (
        float(selected_rows["holdout_improved_vs_M0"].fillna(False).astype(bool).mean()) if len(selected_rows) else 0.0
    )
    background_by_lag: list[dict[str, Any]] = []
    for lag in ALGORITHM_CONFIG["lags"]:
        rows = selected_rows[selected_rows["lag"] == int(lag)]
        background_by_lag.append(
            {
                "lag": int(lag),
                "selected_model": selected[str(int(lag))],
                "valid_pair_count": int(len(rows)),
                "scheduled_pair_count": int(len(r04_comparability[r04_comparability["lag"] == int(lag)])),
                "improvement_fraction_vs_M0": float(rows["holdout_improved_vs_M0"].fillna(False).astype(bool).mean())
                if len(rows)
                else 0.0,
                "M0_holdout_pair_median_px": float(np.median(rows["M0_holdout_residual_median_px"])) if len(rows) else math.nan,
                "selected_holdout_pair_median_px": float(np.median(rows["holdout_residual_median_px"])) if len(rows) else math.nan,
                "selected_holdout_pair_p90_px": float(np.percentile(rows["holdout_residual_median_px"], 90)) if len(rows) else math.nan,
            }
        )

    person_selected = person_residuals[
        (person_residuals["run_id"] == HELDOUT_RUN)
        & person_residuals["model_available"]
        & person_residuals.apply(lambda row: row["model"] == selected[str(int(row["lag"]))], axis=1)
    ].copy()
    all_stats = person_subset_statistics(person_selected, manual_only=False)
    manual_stats = person_subset_statistics(person_selected, manual_only=True)
    short_axis_median = unique_short_axis_median(explorer, HELDOUT_RUN)
    mask_violations = int(
        r04_comparability["person_mask_anchor_violations"].sum()
        + r04_comparability["boundary_mask_anchor_violations"].sum()
    )
    display_counts = r04_comparability["display_stratum"].value_counts().to_dict()

    gates = {
        "R04_comparable_fraction_at_least_frozen_minimum": comparable_fraction
        >= float(ALGORITHM_CONFIG["validation_min_comparable_fraction"]),
        "R04_background_improvement_fraction_at_least_0_75": background_improvement_fraction
        >= float(ALGORITHM_CONFIG["validation_background_improvement_fraction"]),
        "R04_person_all_accepted_P90_below_short_axis_median": bool(
            np.isfinite(all_stats["compensated_p90_px"])
            and all_stats["compensated_p90_px"] < short_axis_median
        ),
        "R04_person_all_accepted_P90_lower_than_uncompensated": bool(
            np.isfinite(all_stats["compensated_p90_px"])
            and all_stats["compensated_p90_px"] < all_stats["uncompensated_p90_px"]
        ),
        "manual_and_all_accepted_direction_consistent": bool(
            all_stats["median_direction"] == "LOWER_AFTER_COMPENSATION"
            and all_stats["p90_direction"] == "LOWER_AFTER_COMPENSATION"
            and manual_stats["median_direction"] == "LOWER_AFTER_COMPENSATION"
            and manual_stats["p90_direction"] == "LOWER_AFTER_COMPENSATION"
        ),
        "manual_person_pair_count_sufficient": int(manual_stats["count"])
        >= int(ALGORITHM_CONFIG["validation_min_manual_person_pairs"]),
        "no_PERSON_or_fan_boundary_anchors_used": mask_violations == 0,
        "R04_not_used_for_tuning": freeze["frozen"]["R04_used_for_tuning"] is False,
        "target_regions_not_used_for_fitting_or_selection": bool(
            freeze["frozen"]["target_regions_used_for_model_selection"] is False
            and int(r04_comparability["target_pixels_used_for_fitting"].sum()) == 0
        ),
        "difficult_pairs_not_deleted": not bool(r04_comparability["difficult_pair_deleted"].astype(bool).any()),
    }
    quantitative_pass = all(bool(value) for value in gates.values())
    render_summary_plots(pair_metrics, person_residuals, selected)
    worst_registry = render_worst_pair_sheets(explorer, pair_metrics, anchor_metrics, selected)
    validation = {
        "schema": "PERSON_P0_FROZEN_R04_QUANTITATIVE_VALIDATION_V1",
        "created_at": now_iso(),
        "stage_status": "R04_COMPLETE_AWAITING_MULTIMODAL_WORST_FRAME_REVIEW",
        "R01_freeze_payload_sha256": freeze["freeze_payload_sha256"],
        "script_sha256": sha256_file(SCRIPT_PATH),
        "input_hash_checks": input_checks,
        "R04_used_for_tuning": False,
        "selected_model_by_lag": selected,
        "display_change_thresholds_by_lag": thresholds,
        "scheduled_pair_count": scheduled_pair_count,
        "pair_comparability": {
            "comparable_pair_count": comparable_pair_count,
            "selected_model_available_pair_count": selected_available_count,
            "selected_model_available_fraction": comparable_fraction,
            "unavailable_reason_counts": r04_comparability.loc[
                ~r04_comparability["comparable"], "comparability_reason"
            ].value_counts().to_dict(),
        },
        "background_holdout": {
            "overall_improvement_fraction_vs_M0": background_improvement_fraction,
            "by_lag": background_by_lag,
        },
        "stationary_PERSON": {
            "short_axis_median_px_unique_R04_boxes": short_axis_median,
            "all_accepted": all_stats,
            "manual_endpoints": manual_stats,
            "semantic_note": "BOX_CENTER_RESIDUAL_IS_IMAGE_COORDINATE_OBSERVATION_NOT_TARGET_INDEPENDENT_MOTION",
        },
        "display_change_strata_pair_counts": display_counts,
        "mask_integrity": {
            "person_mask_anchor_violations": int(r04_comparability["person_mask_anchor_violations"].sum()),
            "boundary_mask_anchor_violations": int(r04_comparability["boundary_mask_anchor_violations"].sum()),
            "target_pixels_used_for_fitting": int(r04_comparability["target_pixels_used_for_fitting"].sum()),
        },
        "quantitative_gates": gates,
        "quantitative_pass": quantitative_pass,
        "worst_case_registry": worst_registry,
        "manual_multimodal_review": "PENDING",
        "final_decision": "PENDING_MULTIMODAL_REVIEW",
        "P1_eligibility": "BLOCKED_PENDING_P0_FINALIZATION",
    }
    write_json(QUANT_VALIDATION_PATH, validation)
    return validation


def make_conclusion_markdown(final: dict[str, Any]) -> str:
    decision = final["final_decision"]
    validation = final["quantitative_validation"]
    selected = validation["selected_model_by_lag"]
    bg = validation["background_holdout"]
    person = validation["stationary_PERSON"]
    status_line = (
        "IMAGE_ONLY_COMMON_MOTION_NOT_OBSERVABLE_AT_PERSON_SCALE"
        if decision == "P0_FAIL"
        else "IMAGE_ONLY_COMMON_MOTION_OBSERVABLE_AT_PERSON_SCALE_UNDER_FROZEN_DISPLAY_DOMAIN_PROTOCOL"
    )
    lines = [
        "# P0 公共表观运动可观测性结论",
        "",
        f"**{decision}**",
        "",
        f"- 状态：`{status_line}`",
        f"- P1：`{final['P1_eligibility']}`（本任务在 P0 停止，没有启动 P1）",
        "- 解释边界：这里的量仅是 SAR 伪彩图像域公共表观运动与框中心残差，不是真实载体轨迹、人体固有 RCS 或目标独立运动。",
        "",
        "## R01 模型选择与冻结",
        "",
    ]
    for lag in ALGORITHM_CONFIG["lags"]:
        lines.append(f"- lag {lag}：冻结 `{selected[str(int(lag))]}`；选择只使用 R01 背景留出锚点。")
    lines.extend(
        [
            "",
            "## R04 完全留出验证",
            "",
            f"- 有效冻结模型帧对：{validation['pair_comparability']['selected_model_available_pair_count']} / {validation['scheduled_pair_count']}（{validation['pair_comparability']['selected_model_available_fraction']:.3f}）。",
            f"- 相对 M0 降低背景留出残差的有效帧对比例：{bg['overall_improvement_fraction_vs_M0']:.3f}；门槛 0.750。",
        ]
    )
    for row in bg["by_lag"]:
        lines.append(
            f"- lag {row['lag']} / {row['selected_model']}：改善比例 {row['improvement_fraction_vs_M0']:.3f}，"
            f"M0 中位 {row['M0_holdout_pair_median_px']:.3f}px，补偿后中位 {row['selected_holdout_pair_median_px']:.3f}px。"
        )
    all_stats = person["all_accepted"]
    manual_stats = person["manual_endpoints"]
    lines.extend(
        [
            "",
            "## 静止 PERSON 残差",
            "",
            f"- R04 PERSON 框短轴中位数：{person['short_axis_median_px_unique_R04_boxes']:.3f}px。",
            f"- 全部接受框：补偿前 P90 {all_stats['uncompensated_p90_px']:.3f}px，补偿后 P90 {all_stats['compensated_p90_px']:.3f}px；样本 {all_stats['count']}。",
            f"- 两端均为人工锚点：补偿前 P90 {manual_stats['uncompensated_p90_px']:.3f}px，补偿后 P90 {manual_stats['compensated_p90_px']:.3f}px；样本 {manual_stats['count']}。",
            "",
            "## 失败帧与完整性",
            "",
            f"- 最差帧对复核：`{final['manual_multimodal_review']['status']}`。详见 `MULTIMODAL_WORST_FRAME_REVIEW.md` 和 `visualizations/R04_worst_pairs_montage.jpg`。",
            f"- PERSON 排除区锚点违规：{validation['mask_integrity']['person_mask_anchor_violations']}；扇面/20 m 边界违规：{validation['mask_integrity']['boundary_mask_anchor_violations']}。",
            f"- 不可比较原因：{json.dumps(validation['pair_comparability']['unavailable_reason_counts'], ensure_ascii=False)}。困难帧没有按残差删除。",
            "",
            "## 门槛",
            "",
        ]
    )
    for key, value in final["final_gates"].items():
        lines.append(f"- {'PASS' if value else 'FAIL'}：{key}")
    lines.extend(
        [
            "",
            "旧 `person_sar_motion_evidence_20260824` 仍是失败探针，只能说明框条件下的伪彩显示重复性，未用于本结论的物理运动解释。",
            "",
        ]
    )
    return "\n".join(lines)


def finalize_after_manual_review(review_status: str) -> dict[str, Any]:
    if review_status not in {"PASS", "FAIL"}:
        raise ValueError("review status must be PASS or FAIL")
    if not MANUAL_REVIEW_PATH.is_file():
        raise FileNotFoundError(f"manual multimodal review file missing: {MANUAL_REVIEW_PATH}")
    quantitative = json.loads(QUANT_VALIDATION_PATH.read_text(encoding="utf-8"))
    freeze = load_and_verify_freeze()
    final_gates = dict(quantitative["quantitative_gates"])
    final_gates["manual_multimodal_worst_frame_review_pass"] = review_status == "PASS"
    final_pass = all(bool(value) for value in final_gates.values())
    decision = "P0_PASS" if final_pass else "P0_FAIL"
    final = {
        "schema": "PERSON_P0_FROZEN_R04_FINAL_VALIDATION_V1",
        "created_at": now_iso(),
        "stage_status": "P0_COMPLETE_STOPPED_BEFORE_P1",
        "final_decision": decision,
        "failure_status": None if final_pass else "IMAGE_ONLY_COMMON_MOTION_NOT_OBSERVABLE_AT_PERSON_SCALE",
        "P1_eligibility": "ELIGIBLE_BUT_NOT_STARTED" if final_pass else "BLOCKED",
        "R01_freeze_payload_sha256": freeze["freeze_payload_sha256"],
        "quantitative_validation_sha256": sha256_file(QUANT_VALIDATION_PATH),
        "manual_multimodal_review": {
            "status": review_status,
            "path": str(MANUAL_REVIEW_PATH),
            "sha256": sha256_file(MANUAL_REVIEW_PATH),
        },
        "final_gates": final_gates,
        "quantitative_validation": quantitative,
        "semantic_stop": {
            "P1_started": False,
            "P2_started": False,
            "sar_boxes_created_or_moved": 0,
            "physical_platform_trajectory_claimed": False,
            "target_independent_motion_claimed": False,
        },
    }
    write_json(FINAL_VALIDATION_PATH, final)
    atomic_write_text(OUTPUT_DIR / "P0_CONCLUSION.md", make_conclusion_markdown(final))
    return final


def run_selfcheck() -> None:
    geometry = {"center_x_px": 500.0, "center_y_px": 600.0, "radius_px": 600.0}
    rng = np.random.default_rng(20260824)
    points = rng.uniform([100, 80], [900, 550], size=(120, 2))
    holdout = np.zeros(len(points), dtype=bool)
    holdout[::4] = True
    translation = np.array([2.5, -1.25])
    tracked = points + translation
    models = fit_models(points, tracked, holdout, geometry, ALGORITHM_CONFIG)
    assert models["M1"]["available"]
    pred = predict_displacement(models["M1"], points[holdout], geometry)
    assert float(np.max(np.abs(pred - translation))) < 1e-6
    affine = np.array([[1.002, -0.004, 1.5], [0.003, 0.998, -0.7]])
    tracked_affine = points @ affine[:, :2].T + affine[:, 2]
    models_affine = fit_models(points, tracked_affine, holdout, geometry, ALGORITHM_CONFIG)
    assert models_affine["M2"]["available"]
    pred_affine = predict_displacement(models_affine["M2"], points[holdout], geometry)
    truth_affine = tracked_affine[holdout] - points[holdout]
    assert float(np.median(np.linalg.norm(pred_affine - truth_affine, axis=1))) < 0.05
    assert WORKSPACE.resolve() == Path(r"D:\profile\research\workspace").resolve()
    print("SELF_CHECK_PASS", flush=True)


def discover() -> None:
    assert_workspace_scope()
    _, input_checks = load_contract_and_verify()
    explorer = load_explorer()
    print("discovery computation is restricted to R01ZF", flush=True)
    result = process_run(explorer, DISCOVERY_RUN, ALGORITHM_CONFIG)
    output = write_discovery_outputs(result, input_checks)
    print(json.dumps({"stage_status": output["stage_status"], "selected": output["frozen"]["selected_model_by_lag"], "freeze_sha256": output["freeze_payload_sha256"]}, ensure_ascii=False), flush=True)


def validate() -> None:
    assert_workspace_scope()
    _, input_checks = load_contract_and_verify()
    freeze = load_and_verify_freeze()
    explorer = load_explorer()
    print("R01 freeze verified; held-out R04ZF validation begins without tuning", flush=True)
    result = process_run(explorer, HELDOUT_RUN, freeze["frozen"]["algorithm_config"])
    output = build_quantitative_validation(explorer, freeze, result, input_checks)
    print(json.dumps({"stage_status": output["stage_status"], "quantitative_pass": output["quantitative_pass"], "background_improvement_fraction": output["background_holdout"]["overall_improvement_fraction_vs_M0"]}, ensure_ascii=False), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("selfcheck")
    subparsers.add_parser("discover")
    subparsers.add_parser("validate")
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--visual-review", required=True, choices=["PASS", "FAIL"])
    args = parser.parse_args()
    if args.command == "selfcheck":
        run_selfcheck()
    elif args.command == "discover":
        discover()
    elif args.command == "validate":
        validate()
    elif args.command == "finalize":
        final = finalize_after_manual_review(args.visual_review)
        print(json.dumps({"final_decision": final["final_decision"], "P1_eligibility": final["P1_eligibility"]}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise
