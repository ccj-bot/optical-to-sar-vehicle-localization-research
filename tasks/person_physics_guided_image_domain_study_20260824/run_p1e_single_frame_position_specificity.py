#!/usr/bin/env python3
"""P1E single-frame SAR-only PERSON position-specificity exploration.

The response maps are generated from the SAR pseudocolor image, fan geometry,
and a fixed scale bank only. PERSON annotations are never inputs to the map;
they are used afterwards for offline evaluation and visualization against
geometry-matched, fixed-offset, and local hard-background controls.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = (
    WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
)
P0_SCRIPT = TASK_DIR / "run_p0_common_apparent_motion.py"
P0_OUTPUT = STUDY_OUTPUT / "p0_common_apparent_motion"
OUTPUT_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface" / "single_frame"
EXPLORER_PATH = (
    WORKSPACE
    / "output"
    / "person_multidimensional_response_explorer_20260823"
    / "explorer_data.js"
)

CANDIDATES = (
    "C0_JET_CENTER_RING",
    "C1_RANGE_RANK_TOPHAT",
    "C2_COMPACT_JET_GRADIENT_CONSENSUS",
    "C3_ISOTROPIC_BLOB_RIDGE_SUPPRESSED",
)
RUNS = ("R01ZF", "R02ZF", "R03ZF", "R04ZF")
EVALUATION_MODES = ("dilated_max_v1", "fixed_support_mean_v2")
MASK_MODES = ("legacy_p1e_loose", "frozen_p0")
PRIMARY_CASE_CANDIDATE = "C3_ISOTROPIC_BLOB_RIDGE_SUPPRESSED"

# Runtime scale hypotheses are fixed in physical fan coordinates and converted
# with fan geometry. They do not use any PERSON box center, width, or height.
PHYSICAL_RESPONSE_DIAMETERS_M = (0.30, 0.55, 0.90)
RANGE_NORMALIZATION_BIN_M = 0.25
PHYSICAL_SUPPORT_RADIUS_M = 0.30
PHYSICAL_PEAK_SEARCH_RADIUS_M = 0.65
PHYSICAL_OFFSET_M = 1.25
PHYSICAL_CONTROL_EXCLUSION_M = 1.00
MATCHED_TANGENTIAL_OFFSETS_M = (-4.0, -3.0, -2.0, -1.25, 1.25, 2.0, 3.0, 4.0)
HARD_BACKGROUND_DISTANCE_RANGE_M = (1.50, 4.00)
HARD_BACKGROUND_RADIAL_TOLERANCE_M = 0.80
HARD_BACKGROUND_GRID_STEP_M = 0.25
TIME_BLOCK_FRAMES = 20


def load_p0_module() -> Any:
    spec = importlib.util.spec_from_file_location("frozen_person_p0_p1e", P0_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen P0 script: {P0_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_explorer() -> dict[str, Any]:
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


def odd(value: float, minimum: int = 3) -> int:
    integer = max(minimum, int(round(value)))
    return integer if integer % 2 == 1 else integer + 1


def disk_kernel(diameter: int) -> np.ndarray:
    diameter = odd(diameter)
    radius = diameter // 2
    yy, xx = np.mgrid[-radius : radius + 1, -radius : radius + 1]
    return ((xx * xx + yy * yy) <= radius * radius).astype(np.float32)


@lru_cache(maxsize=1)
def jet_quantized_lookup() -> tuple[np.ndarray, np.ndarray]:
    values = np.arange(256, dtype=np.uint8)[:, None]
    lut = cv2.applyColorMap(values, cv2.COLORMAP_JET).reshape(256, 3).astype(np.float32)
    levels = (np.arange(32, dtype=np.float32) * 8.0 + 3.5).astype(np.float32)
    bb, gg, rr = np.meshgrid(levels, levels, levels, indexing="ij")
    colors = np.stack([bb, gg, rr], axis=-1).reshape(-1, 3)
    best_index = np.empty(len(colors), dtype=np.uint8)
    best_distance = np.empty(len(colors), dtype=np.float32)
    for start in range(0, len(colors), 1024):
        chunk = colors[start : start + 1024]
        distance = np.sum((chunk[:, None, :] - lut[None, :, :]) ** 2, axis=2)
        argmin = np.argmin(distance, axis=1)
        best_index[start : start + len(chunk)] = argmin.astype(np.uint8)
        best_distance[start : start + len(chunk)] = np.sqrt(
            distance[np.arange(len(chunk)), argmin]
        )
    return best_index, best_distance


def jet_proxy(image_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lookup_index, lookup_distance = jet_quantized_lookup()
    quant = (image_bgr.astype(np.uint16) >> 3).astype(np.int32)
    key = quant[:, :, 0] * 1024 + quant[:, :, 1] * 32 + quant[:, :, 2]
    index = lookup_index[key]
    distance = lookup_distance[key]
    return index.astype(np.float32) / 255.0, distance.astype(np.float32)


def response_valid_mask(
    frame: dict[str, Any], image: np.ndarray, p0: Any, mask_mode: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if mask_mode == "frozen_p0":
        mask, fields = p0.build_base_mask(frame, image, p0.ALGORITHM_CONFIG)
        return mask, fields["radial"], fields["theta"]
    if mask_mode != "legacy_p1e_loose":
        raise ValueError(f"unknown mask mode: {mask_mode}")
    height, width = image.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    geometry = frame["geometry"]
    cx = float(geometry["center_x_px"])
    cy = float(geometry["center_y_px"])
    radius = float(geometry["radius_px"])
    px_per_m = radius / float(geometry["outer_range_m"])
    radial = np.hypot(xx - cx, yy - cy)
    theta = np.degrees(np.arctan2(xx - cx, cy - yy))
    nonwhite = np.any(image < 248, axis=2)
    mask = (
        (radial >= 0.75 * px_per_m)
        & (radial <= radius - 0.10 * px_per_m)
        & (theta >= float(frame["theta_low_deg"]) + 0.25)
        & (theta <= float(frame["theta_high_deg"]) - 0.25)
        & nonwhite
    )
    return mask, radial, theta


def radial_histogram_rank(
    values_u8: np.ndarray,
    radial: np.ndarray,
    mask: np.ndarray,
    bin_px: float = 8.0,
) -> np.ndarray:
    bins = np.floor(radial / bin_px).astype(np.int32)
    output = np.zeros(values_u8.shape, dtype=np.float32)
    for radial_bin in np.unique(bins[mask]):
        select = mask & (bins == radial_bin)
        values = values_u8[select]
        if values.size == 0:
            continue
        hist = np.bincount(values, minlength=256)
        cdf = np.cumsum(hist).astype(np.float32) / float(values.size)
        output[select] = cdf[values]
    return output


def robust_percentile_rank(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    sample = values[mask & np.isfinite(values)]
    output = np.zeros(values.shape, dtype=np.float32)
    if sample.size < 2:
        return output
    lo, hi = np.percentile(sample, [1.0, 99.5])
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo + 1e-8:
        return output
    quant = np.clip((values - lo) * 255.0 / (hi - lo), 0, 255).astype(np.uint8)
    hist = np.bincount(quant[mask], minlength=256)
    cdf = np.cumsum(hist).astype(np.float32) / float(hist.sum())
    output[mask] = cdf[quant[mask]]
    return output


def robust_positive_scale(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Continuous positive scaling without converting the top tail to a CDF plateau."""
    output = np.zeros(values.shape, dtype=np.float32)
    sample = values[mask & np.isfinite(values) & (values > 0)]
    if sample.size < 2:
        return output
    hi = float(np.percentile(sample, 99.5))
    if not np.isfinite(hi) or hi <= 1e-8:
        return output
    output[mask] = np.clip(values[mask] / hi, 0.0, 1.0)
    return output


def normalized_disk_mean(field: np.ndarray, mask: np.ndarray, diameter: int) -> np.ndarray:
    kernel = disk_kernel(diameter)
    numerator = cv2.filter2D(field * mask.astype(np.float32), cv2.CV_32F, kernel)
    denominator = cv2.filter2D(mask.astype(np.float32), cv2.CV_32F, kernel)
    return numerator / np.maximum(denominator, 1e-6)


def center_ring_response(
    field: np.ndarray,
    mask: np.ndarray,
    diameters: list[int],
) -> np.ndarray:
    responses = []
    for diameter in diameters:
        outer_diameter = odd(2.4 * diameter)
        inner_kernel = disk_kernel(diameter)
        outer_kernel = disk_kernel(outer_diameter)
        mask_f = mask.astype(np.float32)
        inner_sum = cv2.filter2D(field * mask_f, cv2.CV_32F, inner_kernel)
        inner_count = cv2.filter2D(mask_f, cv2.CV_32F, inner_kernel)
        outer_sum = cv2.filter2D(field * mask_f, cv2.CV_32F, outer_kernel) - inner_sum
        outer_count = cv2.filter2D(mask_f, cv2.CV_32F, outer_kernel) - inner_count
        inner_mean = inner_sum / np.maximum(inner_count, 1e-6)
        outer_mean = outer_sum / np.maximum(outer_count, 1e-6)
        valid_fraction = inner_count / max(float(inner_kernel.sum()), 1.0)
        response = inner_mean - outer_mean
        response[valid_fraction < 0.80] = 0.0
        responses.append(response)
    return np.max(np.stack(responses, axis=0), axis=0)


def multiscale_tophat(
    field: np.ndarray,
    mask: np.ndarray,
    diameters: list[int],
) -> np.ndarray:
    source = np.clip(field * 255.0, 0, 255).astype(np.uint8)
    source[~mask] = 0
    responses = []
    for diameter in diameters:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (diameter, diameter))
        top_hat = cv2.morphologyEx(source, cv2.MORPH_TOPHAT, kernel).astype(np.float32) / 255.0
        sigma = max(1.0, diameter / 7.0)
        top_hat = cv2.GaussianBlur(top_hat, (0, 0), sigmaX=sigma, sigmaY=sigma)
        responses.append(top_hat)
    return np.max(np.stack(responses, axis=0), axis=0)


def gradient_field(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    image_f = image.astype(np.float32) / 255.0
    magnitude_sq = np.zeros(image.shape[:2], dtype=np.float32)
    for channel in range(3):
        gx = cv2.Scharr(image_f[:, :, channel], cv2.CV_32F, 1, 0)
        gy = cv2.Scharr(image_f[:, :, channel], cv2.CV_32F, 0, 1)
        magnitude_sq += gx * gx + gy * gy
    magnitude = np.log1p(np.sqrt(magnitude_sq))
    sample = magnitude[mask]
    lo, hi = np.percentile(sample, [1.0, 99.5]) if sample.size else (0.0, 1.0)
    scaled = np.clip((magnitude - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    scaled[~mask] = 0.0
    return scaled.astype(np.float32)


def isotropic_blob_ridge_suppressed(
    field: np.ndarray,
    mask: np.ndarray,
    diameters: list[int],
) -> np.ndarray:
    """Bright compact-core response with a local long-ridge coherence penalty."""
    responses: list[np.ndarray] = []
    source = field.astype(np.float32).copy()
    source[~mask] = 0.0
    mask_f = mask.astype(np.float32)
    for diameter in diameters:
        sigma = max(1.0, float(diameter) / 4.0)
        smooth = cv2.GaussianBlur(source, (0, 0), sigmaX=sigma, sigmaY=sigma)
        dxx = cv2.Sobel(smooth, cv2.CV_32F, 2, 0, ksize=3) * (sigma * sigma)
        dyy = cv2.Sobel(smooth, cv2.CV_32F, 0, 2, ksize=3) * (sigma * sigma)
        dxy = cv2.Sobel(smooth, cv2.CV_32F, 1, 1, ksize=3) * (sigma * sigma)
        trace = dxx + dyy
        discriminant = np.sqrt(np.maximum((dxx - dyy) ** 2 + 4.0 * dxy * dxy, 0.0))
        lambda_large = 0.5 * (trace + discriminant)
        compact_curvature = np.clip(-lambda_large, 0.0, None)

        gx = cv2.Scharr(smooth, cv2.CV_32F, 1, 0)
        gy = cv2.Scharr(smooth, cv2.CV_32F, 0, 1)
        integration_sigma = max(1.0, float(diameter) / 2.0)
        jxx = cv2.GaussianBlur(gx * gx, (0, 0), integration_sigma)
        jyy = cv2.GaussianBlur(gy * gy, (0, 0), integration_sigma)
        jxy = cv2.GaussianBlur(gx * gy, (0, 0), integration_sigma)
        coherence = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0)) / np.maximum(
            jxx + jyy, 1e-6
        )
        response = compact_curvature * np.clip(1.0 - coherence, 0.0, 1.0)
        response *= np.sqrt(np.clip(smooth, 0.0, 1.0))

        support_kernel = disk_kernel(diameter)
        support_fraction = cv2.filter2D(mask_f, cv2.CV_32F, support_kernel) / max(
            float(support_kernel.sum()), 1.0
        )
        response[support_fraction < 0.80] = 0.0
        responses.append(robust_positive_scale(response, mask))
    return np.max(np.stack(responses, axis=0), axis=0)


def compute_candidate_maps(
    frame: dict[str, Any],
    image: np.ndarray,
    p0: Any,
    mask_mode: str,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    mask, radial, theta = response_valid_mask(frame, image, p0, mask_mode)
    jet, lut_distance = jet_proxy(image)
    jet[~mask] = 0.0
    geometry = frame["geometry"]
    px_per_m = float(geometry["radius_px"]) / float(geometry["outer_range_m"])
    diameters = sorted({odd(px_per_m * diameter_m) for diameter_m in PHYSICAL_RESPONSE_DIAMETERS_M})

    c0_raw = center_ring_response(jet, mask, diameters)
    c0 = robust_positive_scale(c0_raw, mask)

    jet_u8 = np.clip(jet * 255.0, 0, 255).astype(np.uint8)
    jet_range_rank = radial_histogram_rank(
        jet_u8, radial, mask, bin_px=px_per_m * RANGE_NORMALIZATION_BIN_M
    )
    c1_raw = multiscale_tophat(jet_range_rank, mask, diameters)
    c1 = robust_positive_scale(c1_raw, mask)

    gradient = gradient_field(image, mask)
    gradient_u8 = np.clip(gradient * 255.0, 0, 255).astype(np.uint8)
    gradient_range_rank = radial_histogram_rank(
        gradient_u8, radial, mask, bin_px=px_per_m * RANGE_NORMALIZATION_BIN_M
    )
    gradient_compact_raw = center_ring_response(gradient_range_rank, mask, diameters)
    gradient_compact = robust_positive_scale(gradient_compact_raw, mask)
    consensus_raw = np.sqrt(np.clip(c1, 0.0, 1.0) * np.clip(gradient_compact, 0.0, 1.0))
    c2 = robust_positive_scale(consensus_raw, mask)

    c3 = isotropic_blob_ridge_suppressed(jet_range_rank, mask, diameters)

    maps = {
        "C0_JET_CENTER_RING": c0,
        "C1_RANGE_RANK_TOPHAT": c1,
        "C2_COMPACT_JET_GRADIENT_CONSENSUS": c2,
        "C3_ISOTROPIC_BLOB_RIDGE_SUPPRESSED": c3,
    }
    metadata = {
        "mask": mask,
        "radial": radial,
        "theta": theta,
        "jet_proxy": jet,
        "lut_distance": lut_distance,
        "gradient": gradient,
        "diameters_px": diameters,
        "diameters_m": list(PHYSICAL_RESPONSE_DIAMETERS_M),
        "px_per_m": px_per_m,
    }
    return maps, metadata


def point_from_polar(
    radial_px: float, theta_deg: float, geometry: dict[str, Any]
) -> np.ndarray:
    angle = math.radians(theta_deg)
    return np.array(
        [
            float(geometry["center_x_px"]) + radial_px * math.sin(angle),
            float(geometry["center_y_px"]) - radial_px * math.cos(angle),
        ],
        dtype=np.float64,
    )


def point_units(point: np.ndarray, geometry: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    center = np.array(
        [float(geometry["center_x_px"]), float(geometry["center_y_px"])],
        dtype=np.float64,
    )
    vector = point - center
    radial = vector / max(float(np.linalg.norm(vector)), 1e-6)
    tangential = np.array([radial[1], -radial[0]], dtype=np.float64)
    return radial, tangential


def valid_support_fraction(mask: np.ndarray, point: np.ndarray, radius: int) -> float:
    kernel = disk_kernel(2 * radius + 1)
    x = int(round(float(point[0])))
    y = int(round(float(point[1])))
    if not (0 <= x < mask.shape[1] and 0 <= y < mask.shape[0]):
        return 0.0
    local = cv2.getRectSubPix(
        mask.astype(np.float32),
        (kernel.shape[1], kernel.shape[0]),
        (float(point[0]), float(point[1])),
    )
    return float(np.sum(local * kernel) / max(float(kernel.sum()), 1.0))


def far_from_annotations(
    point: np.ndarray,
    annotations: list[dict[str, Any]],
    exclusion_px: float,
    exempt_target_id: str | None = None,
) -> bool:
    for annotation in annotations:
        if exempt_target_id is not None and annotation["instance_id"] == exempt_target_id:
            continue
        center = np.array([float(annotation["cx"]), float(annotation["cy"])])
        if float(np.linalg.norm(point - center)) < exclusion_px:
            return False
    return True


def sample_score(support_map: np.ndarray, point: np.ndarray) -> float:
    x = int(round(float(point[0])))
    y = int(round(float(point[1])))
    if not (0 <= x < support_map.shape[1] and 0 <= y < support_map.shape[0]):
        return math.nan
    return float(support_map[y, x])


def local_support_statistics(
    field: np.ndarray,
    mask: np.ndarray,
    point: np.ndarray,
    radius: int,
) -> dict[str, float]:
    diameter = 2 * radius + 1
    kernel = disk_kernel(diameter).astype(bool)
    local_field = cv2.getRectSubPix(
        field.astype(np.float32),
        (diameter, diameter),
        (float(point[0]), float(point[1])),
    )
    local_mask = cv2.getRectSubPix(
        mask.astype(np.float32),
        (diameter, diameter),
        (float(point[0]), float(point[1])),
    )
    valid = kernel & (local_mask >= 0.999)
    valid_fraction = float(np.sum(valid) / max(float(np.sum(kernel)), 1.0))
    values = local_field[valid]
    if values.size == 0:
        return {
            "valid_fraction": valid_fraction,
            "mean": math.nan,
            "top_quartile_mean": math.nan,
            "maximum": math.nan,
        }
    cutoff = float(np.quantile(values, 0.75))
    upper = values[values >= cutoff]
    return {
        "valid_fraction": valid_fraction,
        "mean": float(np.mean(values)),
        "top_quartile_mean": float(np.mean(upper)),
        "maximum": float(np.max(values)),
    }


def local_peak(
    field: np.ndarray,
    mask: np.ndarray,
    point: np.ndarray,
    radius: int,
) -> dict[str, float]:
    x0 = max(0, int(math.floor(float(point[0]) - radius)))
    x1 = min(field.shape[1], int(math.ceil(float(point[0]) + radius + 1)))
    y0 = max(0, int(math.floor(float(point[1]) - radius)))
    y1 = min(field.shape[0], int(math.ceil(float(point[1]) + radius + 1)))
    if x0 >= x1 or y0 >= y1:
        return {"score": math.nan, "x": math.nan, "y": math.nan, "distance_px": math.nan}
    yy, xx = np.mgrid[y0:y1, x0:x1]
    select = mask[y0:y1, x0:x1] & (
        (xx - float(point[0])) ** 2 + (yy - float(point[1])) ** 2 <= radius * radius
    )
    if not np.any(select):
        return {"score": math.nan, "x": math.nan, "y": math.nan, "distance_px": math.nan}
    local_values = np.where(select, field[y0:y1, x0:x1], -np.inf)
    flat_index = int(np.argmax(local_values))
    local_y, local_x = np.unravel_index(flat_index, local_values.shape)
    peak_x = float(x0 + local_x)
    peak_y = float(y0 + local_y)
    return {
        "score": float(field[int(peak_y), int(peak_x)]),
        "x": peak_x,
        "y": peak_y,
        "distance_px": float(np.hypot(peak_x - float(point[0]), peak_y - float(point[1]))),
    }


def build_evaluation_maps(
    maps: dict[str, np.ndarray],
    mask: np.ndarray,
    support_radius_px: int,
    evaluation_mode: str,
) -> dict[str, np.ndarray]:
    if evaluation_mode == "dilated_max_v1":
        support_kernel = disk_kernel(2 * support_radius_px + 1).astype(np.uint8)
        return {
            candidate: cv2.dilate(score_map.astype(np.float32), support_kernel)
            for candidate, score_map in maps.items()
        }
    if evaluation_mode == "fixed_support_mean_v2":
        diameter = 2 * support_radius_px + 1
        return {
            candidate: normalized_disk_mean(score_map, mask, diameter)
            for candidate, score_map in maps.items()
        }
    raise ValueError(f"unknown evaluation mode: {evaluation_mode}")


def build_controls(
    frame: dict[str, Any],
    annotation: dict[str, Any],
    mask: np.ndarray,
    support_map: np.ndarray,
    support_radius_px: int,
    offset_px: float,
    exclusion_px: float,
) -> dict[str, Any]:
    geometry = frame["geometry"]
    reference = np.array([float(annotation["cx"]), float(annotation["cy"])], dtype=np.float64)
    px_per_m = float(geometry["radius_px"]) / float(geometry["outer_range_m"])
    reference_range_m = float(annotation["range_m"])
    radial_px = reference_range_m * px_per_m
    theta_deg = float(annotation["theta_deg"])
    annotations = frame["annotations"]
    radial_unit, tangential_unit = point_units(reference, geometry)

    offset_points = {
        "RADIAL_IN": reference - radial_unit * offset_px,
        "RADIAL_OUT": reference + radial_unit * offset_px,
        "TANGENTIAL_NEG": reference - tangential_unit * offset_px,
        "TANGENTIAL_POS": reference + tangential_unit * offset_px,
    }
    accepted_offsets: list[dict[str, Any]] = []
    for name, point in offset_points.items():
        if valid_support_fraction(mask, point, support_radius_px) < 0.80:
            continue
        if not far_from_annotations(point, annotations, exclusion_px, annotation["instance_id"]):
            continue
        accepted_offsets.append(
            {"kind": name, "x": float(point[0]), "y": float(point[1]), "score": sample_score(support_map, point)}
        )

    matched: list[dict[str, Any]] = []
    for tangential_offset_m in MATCHED_TANGENTIAL_OFFSETS_M:
        delta_deg = math.degrees(tangential_offset_m / max(reference_range_m, 0.5))
        point = point_from_polar(radial_px, theta_deg + delta_deg, geometry)
        if valid_support_fraction(mask, point, support_radius_px) < 0.80:
            continue
        if not far_from_annotations(point, annotations, exclusion_px, annotation["instance_id"]):
            continue
        matched.append(
            {
                "kind": f"TANGENTIAL_{tangential_offset_m:+.2f}M",
                "offset_m": float(tangential_offset_m),
                "x": float(point[0]),
                "y": float(point[1]),
                "score": sample_score(support_map, point),
            }
        )

    grid_step_px = max(4, int(round(HARD_BACKGROUND_GRID_STEP_M * px_per_m)))
    yy, xx = np.mgrid[0 : mask.shape[0] : grid_step_px, 0 : mask.shape[1] : grid_step_px]
    points = np.stack([xx.ravel(), yy.ravel()], axis=1).astype(np.float64)
    distances = np.linalg.norm(points - reference[None, :], axis=1)
    point_radial = np.linalg.norm(
        points
        - np.array(
            [float(geometry["center_x_px"]), float(geometry["center_y_px"])]
        )[None, :],
        axis=1,
    )
    hard_select = (
        (distances >= HARD_BACKGROUND_DISTANCE_RANGE_M[0] * px_per_m)
        & (distances <= HARD_BACKGROUND_DISTANCE_RANGE_M[1] * px_per_m)
        & (np.abs(point_radial - radial_px) <= HARD_BACKGROUND_RADIAL_TOLERANCE_M * px_per_m)
    )
    hard_candidates: list[dict[str, Any]] = []
    for point in points[hard_select]:
        if valid_support_fraction(mask, point, support_radius_px) < 0.80:
            continue
        if not far_from_annotations(point, annotations, exclusion_px, None):
            continue
        hard_candidates.append(
            {"x": float(point[0]), "y": float(point[1]), "score": sample_score(support_map, point)}
        )
    hard = max(hard_candidates, key=lambda item: item["score"]) if hard_candidates else None
    hard_scores = np.asarray([item["score"] for item in hard_candidates], dtype=float)
    hard_pool = {
        "count": int(len(hard_scores)),
        "grid_step_px": int(grid_step_px),
        "median_score": float(np.median(hard_scores)) if len(hard_scores) else math.nan,
        "p90_score": float(np.quantile(hard_scores, 0.90)) if len(hard_scores) else math.nan,
        "p95_score": float(np.quantile(hard_scores, 0.95)) if len(hard_scores) else math.nan,
        "maximum_score": float(np.max(hard_scores)) if len(hard_scores) else math.nan,
    }
    return {
        "offsets": accepted_offsets,
        "matched": matched,
        "hard": hard,
        "hard_pool": hard_pool,
    }


def evaluate_annotation(
    frame: dict[str, Any],
    annotation: dict[str, Any],
    maps: dict[str, np.ndarray],
    evaluation_maps: dict[str, np.ndarray],
    metadata: dict[str, Any],
    evaluation_mode: str,
) -> list[dict[str, Any]]:
    px_per_m = float(metadata["px_per_m"])
    support_radius_px = max(1, int(round(PHYSICAL_SUPPORT_RADIUS_M * px_per_m)))
    offset_px = PHYSICAL_OFFSET_M * px_per_m
    exclusion_px = PHYSICAL_CONTROL_EXCLUSION_M * px_per_m
    peak_search_radius_px = max(1, int(round(PHYSICAL_PEAK_SEARCH_RADIUS_M * px_per_m)))
    reference = np.array([float(annotation["cx"]), float(annotation["cy"])])
    rows: list[dict[str, Any]] = []
    for candidate, score_map in maps.items():
        support_map = evaluation_maps[candidate]
        controls = build_controls(
            frame,
            annotation,
            metadata["mask"],
            support_map,
            support_radius_px,
            offset_px,
            exclusion_px,
        )
        reference_stats = local_support_statistics(
            score_map, metadata["mask"], reference, support_radius_px
        )
        reference_evaluable = reference_stats["valid_fraction"] >= 0.80
        ref_score = sample_score(support_map, reference) if reference_evaluable else math.nan
        for item in controls["matched"] + controls["offsets"]:
            item["support_top_quartile_mean"] = local_support_statistics(
                score_map,
                metadata["mask"],
                np.array([item["x"], item["y"]], dtype=np.float64),
                support_radius_px,
            )["top_quartile_mean"]
        if controls["hard"] is not None:
            controls["hard"]["support_top_quartile_mean"] = local_support_statistics(
                score_map,
                metadata["mask"],
                np.array([controls["hard"]["x"], controls["hard"]["y"]], dtype=np.float64),
                support_radius_px,
            )["top_quartile_mean"]
        matched_scores = np.asarray([item["score"] for item in controls["matched"]], dtype=float)
        offset_scores = np.asarray([item["score"] for item in controls["offsets"]], dtype=float)
        hard_score = float(controls["hard"]["score"]) if controls["hard"] is not None else math.nan
        matched_topq = np.asarray(
            [item["support_top_quartile_mean"] for item in controls["matched"]], dtype=float
        )
        offset_topq = np.asarray(
            [item["support_top_quartile_mean"] for item in controls["offsets"]], dtype=float
        )
        hard_topq = (
            float(controls["hard"]["support_top_quartile_mean"])
            if controls["hard"] is not None
            else math.nan
        )
        peak = local_peak(support_map, metadata["mask"], reference, peak_search_radius_px)
        matched_median = float(np.median(matched_scores)) if len(matched_scores) else math.nan
        offset_median = float(np.median(offset_scores)) if len(offset_scores) else math.nan
        matched_percentile = (
            float(np.mean(matched_scores <= ref_score)) if len(matched_scores) else math.nan
        )
        local_pool = [item["score"] for item in controls["matched"] + controls["offsets"]]
        if controls["hard"] is not None:
            local_pool.append(float(controls["hard"]["score"]))
        local_percentile = (
            float(np.mean(np.asarray(local_pool) <= ref_score)) if local_pool else math.nan
        )
        row = {
                "run_id": frame["run_id"],
                "frame_uid": frame["sar_frame_uid"],
                "frame_index": int(frame["sar_frame_index"]),
                "time_block_id": f"{frame['run_id']}_F{(int(frame['sar_frame_index']) // TIME_BLOCK_FRAMES) * TIME_BLOCK_FRAMES:06d}",
                "target_id": annotation["instance_id"],
                "annotation_source": annotation["source"],
                "manual_native": annotation["source"] == "MANUAL_NATIVE_SAR",
                "candidate": candidate,
                "reference_cx_px": float(annotation["cx"]),
                "reference_cy_px": float(annotation["cy"]),
                "reference_range_m": float(annotation["range_m"]),
                "reference_theta_deg": float(annotation["theta_deg"]),
                "reference_local_valid_fraction": float(annotation["local_valid_fraction"]),
                "evaluation_mode": evaluation_mode,
                "evaluation_status": "EVALUABLE" if reference_evaluable else "ABSTAIN_LOW_VALID_SUPPORT",
                "reference_evaluation_valid_fraction": reference_stats["valid_fraction"],
                "response_support_radius_px": support_radius_px,
                "response_support_radius_m": PHYSICAL_SUPPORT_RADIUS_M,
                "peak_search_radius_px": peak_search_radius_px,
                "peak_search_radius_m": PHYSICAL_PEAK_SEARCH_RADIUS_M,
                "fixed_offset_px": offset_px,
                "fixed_offset_m": PHYSICAL_OFFSET_M,
                "reference_score": ref_score,
                "reference_base_map_center_score": sample_score(score_map, reference),
                "reference_support_top_quartile_mean": reference_stats["top_quartile_mean"] if reference_evaluable else math.nan,
                "local_peak_score": peak["score"] if reference_evaluable else math.nan,
                "local_peak_x_px": peak["x"] if reference_evaluable else math.nan,
                "local_peak_y_px": peak["y"] if reference_evaluable else math.nan,
                "local_peak_distance_px": peak["distance_px"] if reference_evaluable else math.nan,
                "local_peak_distance_m": peak["distance_px"] / px_per_m if reference_evaluable else math.nan,
                "matched_control_count": int(len(matched_scores)),
                "matched_median_score": matched_median,
                "matched_max_score": float(np.max(matched_scores)) if len(matched_scores) else math.nan,
                "advantage_vs_matched_median": ref_score - matched_median if np.isfinite(matched_median) else math.nan,
                "reference_beats_matched_median": bool(ref_score > matched_median) if np.isfinite(ref_score) and np.isfinite(matched_median) else math.nan,
                "reference_beats_all_matched": bool(ref_score > np.max(matched_scores)) if np.isfinite(ref_score) and len(matched_scores) else math.nan,
                "matched_percentile": matched_percentile,
                "matched_median_support_top_quartile_mean": float(np.median(matched_topq)) if len(matched_topq) else math.nan,
                "advantage_topq_vs_matched_median": reference_stats["top_quartile_mean"] - float(np.median(matched_topq)) if reference_evaluable and len(matched_topq) else math.nan,
                "offset_control_count": int(len(offset_scores)),
                "offset_median_score": offset_median,
                "offset_max_score": float(np.max(offset_scores)) if len(offset_scores) else math.nan,
                "advantage_vs_offset_median": ref_score - offset_median if np.isfinite(offset_median) else math.nan,
                "reference_beats_offset_median": bool(ref_score > offset_median) if np.isfinite(ref_score) and np.isfinite(offset_median) else math.nan,
                "reference_beats_all_offsets": bool(ref_score > np.max(offset_scores)) if np.isfinite(ref_score) and len(offset_scores) else math.nan,
                "offset_median_support_top_quartile_mean": float(np.median(offset_topq)) if len(offset_topq) else math.nan,
                "advantage_topq_vs_offset_median": reference_stats["top_quartile_mean"] - float(np.median(offset_topq)) if reference_evaluable and len(offset_topq) else math.nan,
                "hard_background_score": hard_score,
                "hard_background_pool_count": int(controls["hard_pool"]["count"]),
                "hard_background_pool_median_score": controls["hard_pool"]["median_score"],
                "hard_background_pool_p90_score": controls["hard_pool"]["p90_score"],
                "hard_background_pool_p95_score": controls["hard_pool"]["p95_score"],
                "advantage_vs_hard_background": ref_score - hard_score if np.isfinite(hard_score) else math.nan,
                "advantage_vs_hard_background_p95": ref_score - controls["hard_pool"]["p95_score"] if np.isfinite(ref_score) and np.isfinite(controls["hard_pool"]["p95_score"]) else math.nan,
                "reference_beats_hard_background": bool(ref_score > hard_score) if np.isfinite(ref_score) and np.isfinite(hard_score) else math.nan,
                "hard_background_support_top_quartile_mean": hard_topq,
                "advantage_topq_vs_hard_background": reference_stats["top_quartile_mean"] - hard_topq if reference_evaluable and np.isfinite(hard_topq) else math.nan,
                "local_control_percentile": local_percentile,
                "controls_json": json.dumps(controls, ensure_ascii=False, separators=(",", ":")),
                "score_map_generated_without_annotation": True,
            }
        offset_by_kind = {item["kind"]: item for item in controls["offsets"]}
        for direction in ("RADIAL_IN", "RADIAL_OUT", "TANGENTIAL_NEG", "TANGENTIAL_POS"):
            item = offset_by_kind.get(direction)
            direction_score = float(item["score"]) if item is not None else math.nan
            row[f"offset_{direction}_score"] = direction_score
            row[f"advantage_vs_offset_{direction}"] = (
                ref_score - direction_score
                if np.isfinite(ref_score) and np.isfinite(direction_score)
                else math.nan
            )
        rows.append(row)
    return rows


def summarize_metrics(metrics: pd.DataFrame, subset_name: str) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for candidate, rows in metrics.groupby("candidate"):
        evaluable = rows[rows["reference_score"].notna()]
        valid_matched = evaluable[evaluable["matched_control_count"] > 0]
        valid_offset = evaluable[evaluable["offset_control_count"] > 0]
        valid_hard = evaluable[evaluable["hard_background_score"].notna()]
        per_run = {}
        for run_id, run_rows in rows.groupby("run_id"):
            run_evaluable = run_rows[run_rows["reference_score"].notna()]
            directional = {}
            for direction in ("RADIAL_IN", "RADIAL_OUT", "TANGENTIAL_NEG", "TANGENTIAL_POS"):
                column = f"advantage_vs_offset_{direction}"
                valid_direction = run_evaluable[column].dropna()
                directional[direction] = {
                    "count": int(len(valid_direction)),
                    "median_advantage": float(valid_direction.median()) if len(valid_direction) else math.nan,
                    "positive_fraction": float((valid_direction > 0).mean()) if len(valid_direction) else math.nan,
                }
            per_run[run_id] = {
                "box_count": int(len(run_rows)),
                "evaluable_count": int(len(run_evaluable)),
                "abstain_count": int(len(run_rows) - len(run_evaluable)),
                "median_reference_score": float(run_evaluable["reference_score"].median()),
                "reference_score_ge_0_995_fraction": float((run_evaluable["reference_score"] >= 0.995).mean()),
                "median_advantage_vs_matched": float(run_evaluable["advantage_vs_matched_median"].median()),
                "reference_beats_matched_median_fraction": float(run_evaluable["reference_beats_matched_median"].mean()),
                "median_advantage_vs_offsets": float(run_evaluable["advantage_vs_offset_median"].median()),
                "reference_beats_offset_median_fraction": float(run_evaluable["reference_beats_offset_median"].mean()),
                "reference_beats_hard_background_fraction": float(run_evaluable["reference_beats_hard_background"].mean()),
                "median_advantage_vs_hard_background_p95": float(run_evaluable["advantage_vs_hard_background_p95"].median()),
                "median_hard_background_pool_count": float(run_evaluable["hard_background_pool_count"].median()),
                "median_local_control_percentile": float(run_evaluable["local_control_percentile"].median()),
                "median_local_peak_distance_px": float(run_evaluable["local_peak_distance_px"].median()),
                "p90_local_peak_distance_px": float(run_evaluable["local_peak_distance_px"].quantile(0.90)),
                "median_local_peak_distance_m": float(run_evaluable["local_peak_distance_m"].median()),
                "p90_local_peak_distance_m": float(run_evaluable["local_peak_distance_m"].quantile(0.90)),
                "per_offset_direction": directional,
            }
        overall_directional = {}
        for direction in ("RADIAL_IN", "RADIAL_OUT", "TANGENTIAL_NEG", "TANGENTIAL_POS"):
            column = f"advantage_vs_offset_{direction}"
            valid_direction = evaluable[column].dropna()
            overall_directional[direction] = {
                "count": int(len(valid_direction)),
                "median_advantage": float(valid_direction.median()) if len(valid_direction) else math.nan,
                "positive_fraction": float((valid_direction > 0).mean()) if len(valid_direction) else math.nan,
            }
        summaries.append(
            {
                "subset": subset_name,
                "candidate": candidate,
                "box_count": int(len(rows)),
                "evaluable_count": int(len(evaluable)),
                "abstain_count": int(len(rows) - len(evaluable)),
                "valid_matched_count": int(len(valid_matched)),
                "valid_offset_count": int(len(valid_offset)),
                "valid_hard_count": int(len(valid_hard)),
                "median_reference_score": float(evaluable["reference_score"].median()),
                "reference_score_ge_0_995_fraction": float((evaluable["reference_score"] >= 0.995).mean()),
                "median_advantage_vs_matched": float(valid_matched["advantage_vs_matched_median"].median()),
                "reference_beats_matched_median_fraction": float(valid_matched["reference_beats_matched_median"].mean()),
                "reference_beats_all_matched_fraction": float(valid_matched["reference_beats_all_matched"].mean()),
                "median_advantage_vs_offsets": float(valid_offset["advantage_vs_offset_median"].median()),
                "reference_beats_offset_median_fraction": float(valid_offset["reference_beats_offset_median"].mean()),
                "reference_beats_all_offsets_fraction": float(valid_offset["reference_beats_all_offsets"].mean()),
                "median_advantage_vs_hard_background": float(valid_hard["advantage_vs_hard_background"].median()),
                "reference_beats_hard_background_fraction": float(valid_hard["reference_beats_hard_background"].mean()),
                "median_advantage_vs_hard_background_p95": float(valid_hard["advantage_vs_hard_background_p95"].median()),
                "median_hard_background_pool_count": float(valid_hard["hard_background_pool_count"].median()),
                "median_advantage_topq_vs_hard_background": float(valid_hard["advantage_topq_vs_hard_background"].median()),
                "median_local_control_percentile": float(evaluable["local_control_percentile"].median()),
                "median_local_peak_distance_px": float(evaluable["local_peak_distance_px"].median()),
                "p90_local_peak_distance_px": float(evaluable["local_peak_distance_px"].quantile(0.90)),
                "median_local_peak_distance_m": float(evaluable["local_peak_distance_m"].median()),
                "p90_local_peak_distance_m": float(evaluable["local_peak_distance_m"].quantile(0.90)),
                "per_offset_direction": overall_directional,
                "per_run": per_run,
            }
        )
    return summaries


def plot_case(
    frame: dict[str, Any],
    annotation: dict[str, Any],
    image_bgr: np.ndarray,
    evaluation_maps: dict[str, np.ndarray],
    metadata: dict[str, Any],
    metric_rows: pd.DataFrame,
    output_path: Path,
) -> None:
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    reference = np.array([float(annotation["cx"]), float(annotation["cy"])])
    crop_radius = int(round(3.0 * float(metadata["px_per_m"])))
    x0 = max(0, int(round(reference[0])) - crop_radius)
    x1 = min(image_rgb.shape[1], int(round(reference[0])) + crop_radius)
    y0 = max(0, int(round(reference[1])) - crop_radius)
    y1 = min(image_rgb.shape[0], int(round(reference[1])) + crop_radius)

    fig, axes = plt.subplots(2, 4, figsize=(22, 10), constrained_layout=True)
    ax = axes[0, 0]
    ax.imshow(image_rgb)
    ax.scatter([reference[0]], [reference[1]], c="red", marker="x", s=100, linewidths=2, label="PERSON ref")
    ax.set_title(f"raw full frame | {frame['run_id']} F{frame['sar_frame_index']} {annotation['instance_id']}")
    ax.axis("off")

    selected_name = PRIMARY_CASE_CANDIDATE
    selected_row = metric_rows[metric_rows["candidate"] == selected_name].iloc[0]
    controls = json.loads(selected_row["controls_json"])
    ax = axes[0, 1]
    ax.imshow(image_rgb)
    overlay = np.ma.masked_where(~metadata["mask"], evaluation_maps[selected_name])
    ax.imshow(overlay, cmap="magma", vmin=0.0, vmax=1.0, alpha=0.62)
    ax.scatter([reference[0]], [reference[1]], c="cyan", marker="x", s=100, linewidths=2)
    if controls["matched"]:
        ax.scatter([p["x"] for p in controls["matched"]], [p["y"] for p in controls["matched"]], facecolors="none", edgecolors="cyan", s=45)
    if controls["offsets"]:
        ax.scatter([p["x"] for p in controls["offsets"]], [p["y"] for p in controls["offsets"]], facecolors="none", edgecolors="yellow", marker="s", s=55)
    if controls["hard"] is not None:
        ax.scatter([controls["hard"]["x"]], [controls["hard"]["y"]], c="magenta", marker="D", s=55)
    ax.set_title("C3 fixed-support S(x) | cyan=matched yellow=offset magenta=hard")
    ax.axis("off")

    ax = axes[0, 2]
    ax.imshow(image_rgb[y0:y1, x0:x1])
    ax.scatter([reference[0] - x0], [reference[1] - y0], c="red", marker="x", s=100, linewidths=2)
    ax.set_title("raw local crop")
    ax.axis("off")

    ax = axes[0, 3]
    ax.axis("off")
    ax.text(
        0.02,
        0.98,
        "\n".join(
            [
                f"status: {selected_row['evaluation_status']}",
                f"support radius: {PHYSICAL_SUPPORT_RADIUS_M:.2f} m",
                f"response diameters: {', '.join(f'{v:.2f}' for v in PHYSICAL_RESPONSE_DIAMETERS_M)} m",
                f"fixed offset: {PHYSICAL_OFFSET_M:.2f} m",
                f"hard pool: {int(selected_row['hard_background_pool_count'])} points",
                f"hard p95: {selected_row['hard_background_pool_p95_score']:.3f}",
                f"peak distance: {selected_row['local_peak_distance_m']:.2f} m",
                "reference/controls use the same S(x) operator",
            ]
        ),
        va="top",
        ha="left",
        fontsize=11,
        family="monospace",
    )

    for ax, candidate in zip(axes[1], CANDIDATES):
        ax.imshow(image_rgb[y0:y1, x0:x1])
        local = evaluation_maps[candidate][y0:y1, x0:x1]
        local_mask = metadata["mask"][y0:y1, x0:x1]
        ax.imshow(np.ma.masked_where(~local_mask, local), cmap="magma", vmin=0.0, vmax=1.0, alpha=0.72)
        ax.scatter([reference[0] - x0], [reference[1] - y0], c="cyan", marker="x", s=100, linewidths=2)
        row = metric_rows[metric_rows["candidate"] == candidate].iloc[0]
        ax.set_title(
            f"{candidate}\nSref={row['reference_score']:.3f} Δmatch={row['advantage_vs_matched_median']:.3f} "
            f"Δoffset={row['advantage_vs_offset_median']:.3f} Δhard={row['advantage_vs_hard_background']:.3f} "
            f"peak_d={row['local_peak_distance_m']:.2f}m"
        )
        ax.axis("off")
    fig.suptitle(
        f"P1E fixed-support direct evidence | annotation={annotation['source']} | S(x) generated without box input",
        fontsize=14,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset", choices=("manual", "all"), default="manual")
    parser.add_argument("--evaluation-mode", choices=EVALUATION_MODES, default="fixed_support_mean_v2")
    parser.add_argument("--mask-mode", choices=MASK_MODES, default="frozen_p0")
    args = parser.parse_args()
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(SCRIPT_PATH).lower() or "old_work" in str(OUTPUT_ROOT).lower():
        raise RuntimeError("forbidden old_work dependency")

    p0 = load_p0_module()
    _, input_checks = p0.load_contract_and_verify()
    freeze = json.loads((P0_OUTPUT / "model_selection_R01.json").read_text(encoding="utf-8"))
    actual_p0_hash = p0.sha256_file(P0_SCRIPT)
    if actual_p0_hash != freeze["frozen"]["script_sha256"]:
        raise RuntimeError("frozen P0 script hash mismatch")
    explorer = load_explorer()
    if args.evaluation_mode == "dilated_max_v1" and args.mask_mode == "legacy_p1e_loose":
        output_name = args.subset
    elif args.evaluation_mode == "fixed_support_mean_v2" and args.mask_mode == "frozen_p0":
        output_name = f"{args.subset}_v4_physical_scale_p0_mask"
    else:
        output_name = f"{args.subset}_{args.evaluation_mode}_{args.mask_mode}"
    output_dir = OUTPUT_ROOT / output_name
    visual_dir = output_dir / "visualizations"
    output_dir.mkdir(parents=True, exist_ok=True)
    visual_dir.mkdir(parents=True, exist_ok=True)

    if args.subset == "manual":
        frames = [
            frame
            for frame in explorer["frames"]
            if any(annotation["source"] == "MANUAL_NATIVE_SAR" for annotation in frame["annotations"])
        ]
    else:
        frames = list(explorer["frames"])

    all_rows: list[dict[str, Any]] = []
    visual_cache: dict[str, tuple[dict[str, Any], np.ndarray, dict[str, np.ndarray], dict[str, Any]]] = {}
    for index, frame in enumerate(frames, start=1):
        image_path = p0.file_url_to_path(frame["sar_image_url"])
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(image_path)
        maps, metadata = compute_candidate_maps(frame, image, p0, args.mask_mode)
        support_radius_px = max(
            1, int(round(PHYSICAL_SUPPORT_RADIUS_M * float(metadata["px_per_m"])))
        )
        evaluation_maps = build_evaluation_maps(
            maps, metadata["mask"], support_radius_px, args.evaluation_mode
        )
        annotations = (
            [annotation for annotation in frame["annotations"] if annotation["source"] == "MANUAL_NATIVE_SAR"]
            if args.subset == "manual"
            else frame["annotations"]
        )
        for annotation in annotations:
            all_rows.extend(
                evaluate_annotation(
                    frame,
                    annotation,
                    maps,
                    evaluation_maps,
                    metadata,
                    args.evaluation_mode,
                )
            )
        visual_cache[frame["sar_frame_uid"]] = (frame, image, evaluation_maps, metadata)
        if index % 25 == 0 or index == len(frames):
            print(f"processed {args.subset} frames {index}/{len(frames)}", flush=True)

    metrics = pd.DataFrame(all_rows)
    metrics_path = output_dir / f"p1e_single_frame_metrics_{args.subset}.csv"
    metrics.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    summaries = summarize_metrics(metrics, args.subset)

    run_target = (
        metrics.groupby(["candidate", "run_id", "target_id"], as_index=False)
        .agg(
            box_count=("frame_uid", "count"),
            median_reference_score=("reference_score", "median"),
            median_advantage_vs_matched=("advantage_vs_matched_median", "median"),
            beats_matched_fraction=("reference_beats_matched_median", "mean"),
            median_advantage_vs_offsets=("advantage_vs_offset_median", "median"),
            beats_offsets_fraction=("reference_beats_offset_median", "mean"),
            median_advantage_vs_hard=("advantage_vs_hard_background", "median"),
            median_advantage_vs_hard_p95=("advantage_vs_hard_background_p95", "median"),
            beats_hard_fraction=("reference_beats_hard_background", "mean"),
            median_peak_distance_m=("local_peak_distance_m", "median"),
            median_local_control_percentile=("local_control_percentile", "median"),
        )
    )
    run_target.to_csv(
        output_dir / f"p1e_run_target_effects_{args.subset}.csv",
        index=False,
        encoding="utf-8-sig",
    )

    run_target_time_block = (
        metrics.groupby(
            ["candidate", "run_id", "target_id", "time_block_id"], as_index=False
        )
        .agg(
            box_count=("frame_uid", "count"),
            evaluable_count=("reference_score", "count"),
            median_advantage_vs_matched=("advantage_vs_matched_median", "median"),
            median_advantage_vs_offsets=("advantage_vs_offset_median", "median"),
            median_advantage_vs_hard=("advantage_vs_hard_background", "median"),
            median_advantage_vs_hard_p95=("advantage_vs_hard_background_p95", "median"),
            beats_hard_fraction=("reference_beats_hard_background", "mean"),
            median_peak_distance_m=("local_peak_distance_m", "median"),
        )
    )
    run_target_time_block.to_csv(
        output_dir / f"p1e_run_target_time_block_effects_{args.subset}.csv",
        index=False,
        encoding="utf-8-sig",
    )

    case_keys = [
        ("R04ZF_SARF000100", "R04ZF_SARPERSON03", "R04_COMPACT_RESPONSE"),
        ("R01ZF_SARF000060", "R01ZF_SARPERSON02", "R01_NEIGHBOR_FUSION_P02"),
        ("R01ZF_SARF000060", "R01ZF_SARPERSON03", "R01_NEIGHBOR_FUSION_P03"),
        ("R02ZF_SARF000472", "R02ZF_SARPERSON01", "R02_GROUP_CLUTTER_P01"),
        ("R02ZF_SARF000472", "R02ZF_SARPERSON02", "R02_GROUP_CLUTTER_P02"),
        ("R02ZF_SARF000490", "R02ZF_SARPERSON03", "R02_REFERENCE_WEAK_P03"),
        ("R03ZF_SARF000458", "R03ZF_SARPERSON01", "R03_BOUNDARY_EARLY"),
        ("R03ZF_SARF000494", "R03ZF_SARPERSON01", "R03_BOUNDARY_RECOVERY"),
        ("R04ZF_SARF000090", "R04ZF_SARPERSON03", "R04_VISIBLE_CORE_OPERATOR_MISS"),
    ]
    registry: list[dict[str, Any]] = []
    if args.subset == "manual":
        selected_metrics = metrics[metrics["candidate"] == PRIMARY_CASE_CANDIDATE]
        for run_id in RUNS:
            run_rows = selected_metrics[selected_metrics["run_id"] == run_id].dropna(
                subset=[
                    "advantage_vs_matched_median",
                    "advantage_vs_offset_median",
                    "advantage_vs_hard_background",
                ]
            )
            if len(run_rows):
                utility = np.minimum(
                    np.minimum(
                        run_rows["advantage_vs_matched_median"].to_numpy(),
                        run_rows["advantage_vs_offset_median"].to_numpy(),
                    ),
                    run_rows["advantage_vs_hard_background"].to_numpy(),
                )
                case_keys.append(
                    (
                        str(run_rows.iloc[int(np.argmax(utility))]["frame_uid"]),
                        str(run_rows.iloc[int(np.argmax(utility))]["target_id"]),
                        f"{run_id}_C3_BEST_FAIR",
                    )
                )
                case_keys.append(
                    (
                        str(run_rows.iloc[int(np.argmin(utility))]["frame_uid"]),
                        str(run_rows.iloc[int(np.argmin(utility))]["target_id"]),
                        f"{run_id}_C3_WORST_FAIR",
                    )
                )

        seen: set[tuple[str, str]] = set()
        rank = 0
        for frame_uid, target_id, reason in case_keys:
            if (frame_uid, target_id) in seen or frame_uid not in visual_cache:
                continue
            seen.add((frame_uid, target_id))
            frame, image, evaluation_maps, metadata = visual_cache[frame_uid]
            annotation = next(
                item for item in frame["annotations"] if item["instance_id"] == target_id
            )
            case_metrics = metrics[
                (metrics["frame_uid"] == frame_uid) & (metrics["target_id"] == target_id)
            ]
            if len(case_metrics) != len(CANDIDATES):
                continue
            rank += 1
            path = visual_dir / f"case_{rank:02d}_{reason}_{frame_uid}_{target_id}.png"
            plot_case(frame, annotation, image, evaluation_maps, metadata, case_metrics, path)
            registry.append(
                {
                    "rank": rank,
                    "reason": reason,
                    "run_id": frame["run_id"],
                    "frame_uid": frame_uid,
                    "target_id": target_id,
                    "annotation_source": annotation["source"],
                    "visual_path": str(path),
                }
            )

    summary = {
        "schema": "PERSON_P1E_SINGLE_FRAME_POSITION_SPECIFICITY_V3",
        "created_at": p0.now_iso(),
        "status": f"P1E_SINGLE_FRAME_{args.subset.upper()}_EXPLORATION_COMPLETE",
        "subset": args.subset,
        "runs": list(RUNS),
        "frame_count": int(len(frames)),
        "annotation_count": int(len(metrics) / len(CANDIDATES)),
        "candidate_count": len(CANDIDATES),
        "evaluation_operator": {
            "mode": args.evaluation_mode,
            "valid_mask_mode": args.mask_mode,
            "valid_mask_source": "FROZEN_P0_BUILD_BASE_MASK_AND_ALGORITHM_CONFIG" if args.mask_mode == "frozen_p0" else "LEGACY_P1E_LOOSE_MASK",
            "frozen_p0_mask_margins": {
                "inner_range_exclusion_m": float(p0.ALGORITHM_CONFIG["inner_range_exclusion_m"]),
                "outer_boundary_margin_m": float(p0.ALGORITHM_CONFIG["outer_boundary_margin_m"]),
                "side_boundary_margin_deg": float(p0.ALGORITHM_CONFIG["side_boundary_margin_deg"]),
            },
            "primary_S_x": "FIXED_DISK_MEAN_OF_FRAME_RELATIVE_BASE_RESPONSE" if args.evaluation_mode == "fixed_support_mean_v2" else "LOCAL_MAX_WITHIN_FIXED_DISK",
            "support_uses_annotation_geometry": False,
            "same_operator_for_reference_matched_offset_and_hard_background": True,
            "secondary_diagnostics": [
                "FIXED_SUPPORT_TOP_QUARTILE_MEAN",
                "LOCAL_PEAK_SCORE_AND_DISTANCE_WITHIN_FIXED_0_65_M_RADIUS",
                "HARD_BACKGROUND_POOL_MEDIAN_P90_P95_MAX",
                "FOUR_OFFSET_DIRECTIONS_REPORTED_SEPARATELY",
            ],
        },
        "candidate_definitions": {
            "C0_JET_CENTER_RING": {
                "measures": "MULTISCALE_LOCAL_JET_PROXY_CENTER_MINUS_RING_CONTRAST",
                "why_position_specific": "COMPACT_ELEVATED_DISPLAY_RESPONSE_SHOULD_EXCEED_ITS_LOCAL_RING",
            },
            "C1_RANGE_RANK_TOPHAT": {
                "measures": "MULTISCALE_COMPACT_BRIGHT_SUPPORT_AFTER_WITHIN_RANGE_RANK_NORMALIZATION",
                "why_position_specific": "SUPPRESSES_RANGE_DEPENDENCE_AND_BROAD_ARCS_WHILE_RETAINING_SMALL_BRIGHT_SUPPORT",
            },
            "C2_COMPACT_JET_GRADIENT_CONSENSUS": {
                "measures": "COINCIDENCE_OF_COMPACT_RANGE_NORMALIZED_JET_SUPPORT_AND_LOCAL_GRADIENT_CLUSTER",
                "why_position_specific": "REQUIRES_BOTH_LOCAL_ELEVATED_RESPONSE_AND_INTERNAL_EDGE_OR_RIDGE_SUPPORT",
            },
            "C3_ISOTROPIC_BLOB_RIDGE_SUPPRESSED": {
                "measures": "MULTISCALE_BRIGHT_BLOB_HESSIAN_CURVATURE_WITH_STRUCTURE_TENSOR_RIDGE_PENALTY",
                "why_position_specific": "REQUIRES_TWO_DIMENSIONAL_COMPACT_CURVATURE_AND_PENALIZES_LONG_COHERENT_ARCS_OR_RIDGES",
            },
        },
        "runtime_inputs": [
            "SAR_PSEUDOCOLOR_IMAGE",
            "FAN_GEOMETRY",
            "FIXED_PHYSICAL_SCALE_BANK",
            "VALID_PIXEL_MASK",
        ],
        "forbidden_runtime_inputs": [
            "PERSON_BOX_CENTER",
            "PERSON_BOX_WIDTH_HEIGHT",
            "PHYSICAL_TARGET_ID",
            "OPTICAL_TRACK_SELECTION",
        ],
        "fixed_scale": {
            "response_kernel_diameters_m": list(PHYSICAL_RESPONSE_DIAMETERS_M),
            "range_normalization_bin_m": RANGE_NORMALIZATION_BIN_M,
            "S_x_support_radius_m": PHYSICAL_SUPPORT_RADIUS_M,
            "peak_search_radius_m": PHYSICAL_PEAK_SEARCH_RADIUS_M,
            "fixed_offset_m": PHYSICAL_OFFSET_M,
            "control_exclusion_m": PHYSICAL_CONTROL_EXCLUSION_M,
            "matched_tangential_offsets_m": list(MATCHED_TANGENTIAL_OFFSETS_M),
            "hard_background_distance_range_m": list(HARD_BACKGROUND_DISTANCE_RANGE_M),
            "hard_background_radial_tolerance_m": HARD_BACKGROUND_RADIAL_TOLERANCE_M,
            "hard_background_grid_step_m": HARD_BACKGROUND_GRID_STEP_M,
            "pixels_per_meter_values": sorted(
                {
                    float(frame["geometry"]["radius_px"])
                    / float(frame["geometry"]["outer_range_m"])
                    for frame in frames
                }
            ),
            "scale_source": "PREDECLARED_PERSON_CLASS_PHYSICAL_SUPPORT_HYPOTHESES_CONVERTED_BY_FAN_GEOMETRY_NOT_ANNOTATION_BOX_SIZE",
        },
        "input_hash_checks": input_checks,
        "frozen_P0_script_sha256": actual_p0_hash,
        "summaries": summaries,
        "visual_case_registry": registry,
        "semantic_boundaries": {
            "all_runs_are_development_data": True,
            "P1_PASS_claimed": False,
            "score_maps_generated_without_annotations": True,
            "score_scale_derived_from_PERSON_boxes": False,
            "PERSON_box_dimensions_used_in_score_generation": False,
            "annotations_used_for_offline_evaluation_only": True,
            "SAR_boxes_created_or_moved": 0,
            "P0_retuned": False,
            "P2_started": False,
        },
    }
    p0.write_json(output_dir / f"p1e_single_frame_summary_{args.subset}.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
