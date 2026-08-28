#!/usr/bin/env python3
"""Observation-model diagnostic for the existing PERSON SAR-only evidence.

This is an additive exploratory analysis.  It does not modify or refit frozen
P0, C0-C3, B0R, candidate semantic split, or dynamic-evidence outputs.  It
builds one condition table for references, GT-blind C2 candidates, and frozen
controls; then diagnoses display state, spatial P0 reliability, lag-dependent
transport separability, C2 response retention, and provisional optical shells.

Manual references and target IDs are offline labels only.  They are never used
to generate response maps, candidates, P0 motion, or optical shells.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
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
STUDY_OUTPUT = (
    WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
)
P1E_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface"
OUTPUT_DIR = P1E_ROOT / "observation_model_diagnostic_v1"
VIS_DIR = OUTPUT_DIR / "visualizations"
PROTOCOL_PATH = OUTPUT_DIR / "00_OBSERVATION_MODEL_DIAGNOSTIC_PROTOCOL_FROZEN_BEFORE_RUN.md"

P0_SCRIPT = TASK_DIR / "run_p0_common_apparent_motion.py"
P1E_SCRIPT = TASK_DIR / "run_p1e_single_frame_position_specificity.py"
CANDIDATE_AUDIT_SCRIPT = TASK_DIR / "run_p1e_candidate_recall_audit.py"

P0_ROOT = STUDY_OUTPUT / "p0_common_apparent_motion"
B0R_ROOT = P1E_ROOT / "b0r_minimal"
CANDIDATE_ROOT = (
    P1E_ROOT
    / "candidate_recall_semantic_split_v1"
    / "single_frame_candidate_recall"
)
OLD_P1E_ROOT = P1E_ROOT / "single_frame" / "manual_v4_physical_scale_p0_mask"

EXPLORER_PATH = (
    WORKSPACE
    / "output"
    / "person_multidimensional_response_explorer_20260823"
    / "explorer_data.js"
)
CANDIDATES_CSV = CANDIDATE_ROOT / "gt_blind_candidates_all_processed_frames.csv"
REFERENCES_CSV = CANDIDATE_ROOT / "manual_reference_candidate_interpretation_v2.csv"
FIXED_OFFSETS_CSV = CANDIDATE_ROOT / "fixed_offset_candidate_coverage.csv"
OLD_METRICS_CSV = OLD_P1E_ROOT / "p1e_single_frame_metrics_manual.csv"

P0_ANCHORS_CSV = P0_ROOT / "background_anchor_holdout_metrics.csv"
P0_PAIR_METRICS_CSV = P0_ROOT / "common_motion_pair_metrics.csv"
P0_COMPARABILITY_CSV = P0_ROOT / "comparability_registry.csv"
P0_MODELS_JSONL = P0_ROOT / "model_parameters_per_pair.jsonl"
B0R_ANCHORS_CSV = B0R_ROOT / "b0r_background_anchor_metrics_R02_R03.csv"
B0R_PAIR_METRICS_CSV = B0R_ROOT / "b0r_pair_metrics_R02_R03.csv"
B0R_COMPARABILITY_CSV = B0R_ROOT / "b0r_pair_comparability_R02_R03.csv"
B0R_MODELS_JSONL = B0R_ROOT / "b0r_model_parameters_R02_R03.jsonl"

R01_OPTICAL_MODEL = (
    WORKSPACE / "output" / "r01_person_azimuth_pilot_20260819" / "model_summary.json"
)
R04_OPTICAL_AUDIT = (
    WORKSPACE
    / "output"
    / "r04_person_crossrun_validation_20260820"
    / "validation_report.json"
)

PRIMARY = "C2_COMPACT_JET_GRADIENT_CONSENSUS"
DIAGNOSTIC = "C3_ISOTROPIC_BLOB_RIDGE_SUPPRESSED"
RUNS = ("R01ZF", "R02ZF", "R03ZF", "R04ZF")
LAGS = (1, 3, 5)

LOCAL_ANCHOR_RADIUS_PX = 144.0
LOCAL_ANCHOR_MIN_COUNT = 8
UNCERTAINTY_FLOOR_PX = 0.5
MODEL_SUPPORT_RADIUS_M = 0.30
STRUCTURE_RADIUS_M = 0.90
LOCAL_COMPETITOR_RADIUS_M = 1.25
DENSITY_RADII_M = (1.0, 2.0)
FIELD_GRID_STRIDE_PX = 4
SIGMA_GRID_STRIDE_PX = 24

DISPLAY_HIGH_CENSOR_FRACTION = 0.01
DISPLAY_COMPRESSED_RANGE = 0.15
DISPLAY_COMPRESSED_EFFECTIVE_LEVELS = 24.0
DISPLAY_ROBUST_Z = 3.0

OPTICAL_TIME_WINDOW_MS = 250
OPTICAL_SHELL_SHIFT_DEG = 18.0
OPTICAL_WIDTH_PX = 3840.0
OPTICAL_SLOPE_DEG_PER_PX = 0.02666536443690682
OPTICAL_INTERCEPT_DEG = -45.502258572693094

EXPECTED_HASHES = {
    P0_SCRIPT: "0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8",
    P1E_SCRIPT: "98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1",
    CANDIDATE_AUDIT_SCRIPT: "84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8",
    CANDIDATES_CSV: "D2F1673A247FDB3AB1DD884F989ADC0ABE4E33A86AEFE45B5DFB4BE286FD6EC0",
    REFERENCES_CSV: "796F20EB3080C5B45CDEBBCC71584CC95C65691F056D46C4A31704A3D86E8EC7",
    FIXED_OFFSETS_CSV: "914417E3D08758E0BAFEA2955FD11EE368E70043D4D2731C59FB8DC6B63077A3",
    OLD_METRICS_CSV: "51670C306A8BA6E920738E80FFD86A197E04C3BDEE3CBB851496B8C0E27A2821",
    P0_ANCHORS_CSV: "9964E1E90CD8DCA46C228E0330D043E5C47A92BFD5C51548E8D91DC5A8EC49C4",
    P0_PAIR_METRICS_CSV: "67309821F0FC4646E510EBB0D806A76B6EAB0642B7BC7C3F617A255FF6A33BF4",
    P0_COMPARABILITY_CSV: "F16BD0722F18B24CA57BA38EC783ACC4085CB947764D0F1812E42E2235999F60",
    P0_MODELS_JSONL: "C0E74F1E790C75607FFFE3CE60AD0B3086BAA8880E8ADCD8FFCDB0D9B2AE5745",
    B0R_ANCHORS_CSV: "CFEFB6D4239CDB290F0689A5E79437986FCD744FCE7F023B8F2CCBCAA8367385",
    B0R_PAIR_METRICS_CSV: "862BA1FEEE5A4A540DA03230F8A15192DE117BA002AB6FE67C2E8C2EFF0D042C",
    B0R_COMPARABILITY_CSV: "4D0B454A7131212221AD3911B8A9652B93BF0BECDC35F1B9E54B19B4F5735D13",
    B0R_MODELS_JSONL: "265ADC67D62C466F2D9523FDD06F0503BC9B4AE1343D1A63CCCC3D5FE8FF5E2D",
    R01_OPTICAL_MODEL: "3463FFF0A8D1507ECA383356E0FB108BD60E1226A19890B62EA8C8FD5090BA42",
    R04_OPTICAL_AUDIT: "24D0CEE627B272EA76A64BC245C0779DA2F6ED428E885C77490A177DBE470A14",
}


@dataclass
class FrameContext:
    frame: dict[str, Any]
    image_bgr: np.ndarray
    omega_single: np.ndarray
    frozen_p0_mask: np.ndarray
    radial_px: np.ndarray
    theta_deg: np.ndarray
    px_per_m: float
    c2_map: np.ndarray
    c3_map: np.ndarray
    support_fraction: np.ndarray
    c2_percentile_map: np.ndarray
    jet_proxy: np.ndarray
    lut_distance: np.ndarray


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    if pd.isna(value) if not isinstance(value, (str, bool)) else False:
        return None
    return value


def load_explorer() -> dict[str, Any]:
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


def sample_nearest(field: np.ndarray, points: np.ndarray, default: float = math.nan) -> np.ndarray:
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] < 2:
        raise ValueError("points must be an N x 2 array")
    output = np.full(len(points), default, dtype=float)
    finite = np.isfinite(points[:, 0]) & np.isfinite(points[:, 1])
    if not finite.any():
        return output
    xi = np.zeros(len(points), dtype=np.intp)
    yi = np.zeros(len(points), dtype=np.intp)
    xi[finite] = np.rint(points[finite, 0]).astype(np.intp)
    yi[finite] = np.rint(points[finite, 1]).astype(np.intp)
    inside = (
        finite
        & (xi >= 0)
        & (xi < field.shape[1])
        & (yi >= 0)
        & (yi < field.shape[0])
    )
    output[inside] = field[yi[inside], xi[inside]]
    return output


def sample_bool(field: np.ndarray, points: np.ndarray) -> np.ndarray:
    return sample_nearest(field.astype(np.float32), points, default=0.0) >= 0.5


def percentile_field(values: np.ndarray, mask: np.ndarray, bins: int = 4096) -> np.ndarray:
    output = np.zeros(values.shape, dtype=np.float32)
    finite = mask & np.isfinite(values)
    sample = np.clip(values[finite], 0.0, 1.0)
    if sample.size < 2:
        return output
    quant = np.clip(np.floor(np.clip(values, 0.0, 1.0) * (bins - 1)), 0, bins - 1).astype(int)
    hist = np.bincount(quant[finite], minlength=bins)
    cdf = np.cumsum(hist).astype(np.float64) / max(float(hist.sum()), 1.0)
    output[finite] = cdf[quant[finite]].astype(np.float32)
    return output


def union_intervals(intervals: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    ordered = sorted((min(float(a), float(b)), max(float(a), float(b))) for a, b in intervals)
    merged: list[list[float]] = []
    for low, high in ordered:
        if not merged or low > merged[-1][1]:
            merged.append([low, high])
        else:
            merged[-1][1] = max(merged[-1][1], high)
    return [(item[0], item[1]) for item in merged]


def interval_width_in_fan(
    intervals: Iterable[tuple[float, float]], theta_low: float, theta_high: float
) -> float:
    clipped = []
    for low, high in intervals:
        low_clip = max(min(low, high), theta_low)
        high_clip = min(max(low, high), theta_high)
        if high_clip > low_clip:
            clipped.append((low_clip, high_clip))
    return float(sum(high - low for low, high in union_intervals(clipped)))


def inside_intervals(theta: np.ndarray, intervals: Iterable[tuple[float, float]]) -> np.ndarray:
    output = np.zeros(len(theta), dtype=bool)
    for low, high in union_intervals(intervals):
        output |= (theta >= low) & (theta <= high)
    return output


def distance_to_intervals(theta: np.ndarray, intervals: Iterable[tuple[float, float]]) -> np.ndarray:
    merged = union_intervals(intervals)
    if not merged:
        return np.full(len(theta), math.nan)
    result = np.full(len(theta), np.inf, dtype=float)
    for low, high in merged:
        result = np.minimum(result, np.maximum(np.maximum(low - theta, theta - high), 0.0))
    return result


def point_polar(points: np.ndarray, geometry: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    center = np.array(
        [float(geometry["center_x_px"]), float(geometry["center_y_px"])], dtype=float
    )
    delta = np.asarray(points, dtype=float) - center[None, :]
    radial = np.linalg.norm(delta, axis=1)
    theta = np.degrees(np.arctan2(delta[:, 0], -delta[:, 1]))
    return radial, theta


def robust_z(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    median = float(numeric.median())
    mad = float((numeric - median).abs().median())
    if not np.isfinite(mad) or mad <= 1e-12:
        return pd.Series(np.zeros(len(numeric)), index=numeric.index, dtype=float)
    return 0.6744897501960817 * (numeric - median) / mad


def pearson_finite(first: np.ndarray, second: np.ndarray) -> float:
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    valid = np.isfinite(first) & np.isfinite(second)
    if int(valid.sum()) < 20:
        return math.nan
    a = first[valid]
    b = second[valid]
    a = a - float(a.mean())
    b = b - float(b.mean())
    denominator = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
    if denominator <= 1e-12:
        return math.nan
    return float(np.dot(a, b) / denominator)


def build_frame_context(
    p0: Any,
    p1e: Any,
    audit: Any,
    frame: dict[str, Any],
    need_c3: bool = False,
) -> FrameContext:
    image_path = p0.file_url_to_path(frame["sar_image_url"])
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(image_path)
    omega_single, radial, theta, px_per_m = audit.single_frame_observation_mask(frame, image)
    jet, lut_distance = p1e.jet_proxy(image)
    jet[~omega_single] = 0.0
    diameters = sorted(
        {p1e.odd(px_per_m * diameter_m) for diameter_m in p1e.PHYSICAL_RESPONSE_DIAMETERS_M}
    )
    jet_u8 = np.clip(jet * 255.0, 0, 255).astype(np.uint8)
    jet_range_rank = p1e.radial_histogram_rank(
        jet_u8,
        radial,
        omega_single,
        bin_px=px_per_m * p1e.RANGE_NORMALIZATION_BIN_M,
    )
    c1_raw = p1e.multiscale_tophat(jet_range_rank, omega_single, diameters)
    c1 = p1e.robust_positive_scale(c1_raw, omega_single)
    gradient = p1e.gradient_field(image, omega_single)
    gradient_u8 = np.clip(gradient * 255.0, 0, 255).astype(np.uint8)
    gradient_range_rank = p1e.radial_histogram_rank(
        gradient_u8,
        radial,
        omega_single,
        bin_px=px_per_m * p1e.RANGE_NORMALIZATION_BIN_M,
    )
    gradient_compact_raw = p1e.center_ring_response(
        gradient_range_rank, omega_single, diameters
    )
    gradient_compact = p1e.robust_positive_scale(gradient_compact_raw, omega_single)
    consensus_raw = np.sqrt(
        np.clip(c1, 0.0, 1.0) * np.clip(gradient_compact, 0.0, 1.0)
    )
    c2 = p1e.robust_positive_scale(consensus_raw, omega_single)
    c3 = (
        p1e.isotropic_blob_ridge_suppressed(jet_range_rank, omega_single, diameters)
        if need_c3
        else np.full(c2.shape, np.nan, dtype=np.float32)
    )
    maps = {PRIMARY: c2}
    if need_c3:
        maps[DIAGNOSTIC] = c3
    support_radius_px = max(1, int(round(p1e.PHYSICAL_SUPPORT_RADIUS_M * px_per_m)))
    evaluation = p1e.build_evaluation_maps(
        maps, omega_single, support_radius_px, "fixed_support_mean_v2"
    )
    support = audit.support_fraction_map(p1e, omega_single, support_radius_px)
    center_valid = omega_single & (support >= audit.SUPPORT_TRUNCATED_MIN)
    percentiles = percentile_field(evaluation[PRIMARY], center_valid)
    frozen_mask, _ = p0.build_base_mask(frame, image, p0.ALGORITHM_CONFIG)
    return FrameContext(
        frame=frame,
        image_bgr=image,
        omega_single=omega_single,
        frozen_p0_mask=frozen_mask,
        radial_px=radial,
        theta_deg=theta,
        px_per_m=float(px_per_m),
        c2_map=evaluation[PRIMARY].astype(np.float32),
        c3_map=(
            evaluation[DIAGNOSTIC].astype(np.float32)
            if need_c3
            else np.full(c2.shape, np.nan, dtype=np.float32)
        ),
        support_fraction=support.astype(np.float32),
        c2_percentile_map=percentiles,
        jet_proxy=jet.astype(np.float32),
        lut_distance=lut_distance.astype(np.float32),
    )


def frame_display_stats(context: FrameContext) -> dict[str, Any]:
    mask = context.omega_single
    values = context.jet_proxy[mask & np.isfinite(context.jet_proxy)]
    distances = context.lut_distance[mask & np.isfinite(context.lut_distance)]
    quantiles = np.percentile(values, [1, 5, 50, 95, 99]) if values.size else [math.nan] * 5
    bins = np.clip(np.floor(values * 32.0), 0, 31).astype(int) if values.size else np.array([], int)
    hist = np.bincount(bins, minlength=32).astype(float) if values.size else np.zeros(32)
    probabilities = hist[hist > 0] / max(float(hist.sum()), 1.0)
    entropy = float(-np.sum(probabilities * np.log2(probabilities))) if probabilities.size else math.nan
    effective_levels = float(2.0**entropy) if np.isfinite(entropy) else math.nan
    height, width = mask.shape
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    geometry = context.frame["geometry"]
    radial = np.hypot(xx - float(geometry["center_x_px"]), yy - float(geometry["center_y_px"]))
    theta = np.degrees(
        np.arctan2(xx - float(geometry["center_x_px"]), float(geometry["center_y_px"]) - yy)
    )
    geometric_fan = (
        (radial <= float(geometry["radius_px"]))
        & (theta >= float(context.frame["theta_low_deg"]))
        & (theta <= float(context.frame["theta_high_deg"]))
    )
    nonwhite = np.any(context.image_bgr < 248, axis=2)
    return {
        "run_id": context.frame["run_id"],
        "frame_uid": context.frame["sar_frame_uid"],
        "frame_index": int(context.frame["sar_frame_index"]),
        "sar_timestamp_ms": int(context.frame["sar_timestamp_ms"]),
        "sync_status": context.frame.get("sync_status", ""),
        "omega_single_pixel_count": int(mask.sum()),
        "geometric_fan_pixel_count": int(geometric_fan.sum()),
        "nonwhite_fraction_in_geometric_fan": float(
            np.mean(nonwhite[geometric_fan]) if np.any(geometric_fan) else math.nan
        ),
        "jet_p01": float(quantiles[0]),
        "jet_p05": float(quantiles[1]),
        "jet_p50": float(quantiles[2]),
        "jet_p95": float(quantiles[3]),
        "jet_p99": float(quantiles[4]),
        "jet_p95_minus_p05": float(quantiles[3] - quantiles[1]),
        "jet_high_plateau_fraction": float(np.mean(values >= 250.0 / 255.0)) if values.size else math.nan,
        "jet_low_plateau_fraction": float(np.mean(values <= 5.0 / 255.0)) if values.size else math.nan,
        "jet_entropy_32bin_bits": entropy,
        "jet_effective_levels_32bin": effective_levels,
        "jet_lut_distance_p50": float(np.percentile(distances, 50)) if distances.size else math.nan,
        "jet_lut_distance_p95": float(np.percentile(distances, 95)) if distances.size else math.nan,
    }


def weighted_structure_maps(
    field: np.ndarray, mask: np.ndarray, radius_px: int, px_per_m: float
) -> dict[str, np.ndarray]:
    height, width = field.shape
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    kernel_y, kernel_x = np.mgrid[-radius_px : radius_px + 1, -radius_px : radius_px + 1]
    kernel = ((kernel_x * kernel_x + kernel_y * kernel_y) <= radius_px * radius_px).astype(
        np.float32
    )
    weight = np.clip(field, 0.0, None).astype(np.float32) * mask.astype(np.float32)
    sum_w = cv2.filter2D(weight, cv2.CV_32F, kernel)
    sum_w2 = cv2.filter2D(weight * weight, cv2.CV_32F, kernel)
    sum_x = cv2.filter2D(weight * xx, cv2.CV_32F, kernel)
    sum_y = cv2.filter2D(weight * yy, cv2.CV_32F, kernel)
    sum_xx = cv2.filter2D(weight * xx * xx, cv2.CV_32F, kernel)
    sum_yy = cv2.filter2D(weight * yy * yy, cv2.CV_32F, kernel)
    sum_xy = cv2.filter2D(weight * xx * yy, cv2.CV_32F, kernel)
    denominator = np.maximum(sum_w, 1e-9)
    mean_x = sum_x / denominator
    mean_y = sum_y / denominator
    cov_xx = np.maximum(sum_xx / denominator - mean_x * mean_x, 0.0)
    cov_yy = np.maximum(sum_yy / denominator - mean_y * mean_y, 0.0)
    cov_xy = sum_xy / denominator - mean_x * mean_y
    trace = np.maximum(cov_xx + cov_yy, 0.0)
    discriminant = np.sqrt(np.maximum((cov_xx - cov_yy) ** 2 + 4.0 * cov_xy * cov_xy, 0.0))
    anisotropy = discriminant / np.maximum(trace, 1e-9)
    orientation = 0.5 * np.degrees(np.arctan2(2.0 * cov_xy, cov_xx - cov_yy))
    spread_m = np.sqrt(trace) / px_per_m
    effective_count = sum_w * sum_w / np.maximum(sum_w2, 1e-12)
    invalid = sum_w <= 1e-9
    for output in (anisotropy, orientation, spread_m, effective_count):
        output[invalid] = np.nan
    return {
        "structure_anisotropy": anisotropy.astype(np.float32),
        "structure_orientation_deg": orientation.astype(np.float32),
        "structure_spread_m": spread_m.astype(np.float32),
        "structure_effective_pixel_count": effective_count.astype(np.float32),
    }


def local_weighted_structure_points(
    field: np.ndarray,
    mask: np.ndarray,
    points: np.ndarray,
    radius_px: int,
    px_per_m: float,
) -> dict[str, np.ndarray]:
    outputs: dict[str, list[float]] = defaultdict(list)
    for x, y in np.asarray(points, dtype=float):
        x0 = max(0, int(math.floor(x - radius_px)))
        x1 = min(field.shape[1], int(math.ceil(x + radius_px + 1)))
        y0 = max(0, int(math.floor(y - radius_px)))
        y1 = min(field.shape[0], int(math.ceil(y + radius_px + 1)))
        yy, xx = np.mgrid[y0:y1, x0:x1]
        select = (
            ((xx - x) ** 2 + (yy - y) ** 2 <= radius_px * radius_px)
            & mask[y0:y1, x0:x1]
            & np.isfinite(field[y0:y1, x0:x1])
        )
        if not np.any(select):
            values = (math.nan, math.nan, math.nan, math.nan)
        else:
            weight = np.clip(field[y0:y1, x0:x1][select].astype(float), 0.0, None)
            total = float(weight.sum())
            if total <= 1e-12:
                values = (math.nan, math.nan, math.nan, math.nan)
            else:
                coordinates = np.column_stack((xx[select] - x, yy[select] - y)).astype(float)
                normalized = weight / total
                mean = np.sum(coordinates * normalized[:, None], axis=0)
                centered = coordinates - mean[None, :]
                covariance = (centered * normalized[:, None]).T @ centered
                eigenvalues, eigenvectors = np.linalg.eigh(covariance)
                small = max(float(eigenvalues[0]), 0.0)
                large = max(float(eigenvalues[1]), 0.0)
                anisotropy = (large - small) / max(large + small, 1e-9)
                principal = eigenvectors[:, 1]
                orientation = math.degrees(math.atan2(float(principal[1]), float(principal[0])))
                spread = math.sqrt(large + small) / px_per_m
                effective = 1.0 / max(float(np.sum(normalized * normalized)), 1e-12)
                values = (anisotropy, orientation, spread, effective)
        outputs["structure_anisotropy"].append(values[0])
        outputs["structure_orientation_deg"].append(values[1])
        outputs["structure_spread_m"].append(values[2])
        outputs["structure_effective_pixel_count"].append(values[3])
    return {key: np.asarray(value, dtype=float) for key, value in outputs.items()}


def reference_primary_state(row: pd.Series) -> str:
    support = str(row.get("reference_support_status", ""))
    if support == "INVALID":
        return "EDGE_OR_SUPPORT_INVALID"
    if support == "TRUNCATED" or bool(row.get("boundary_or_truncation_flag_v2", False)):
        return "EDGE_CENSORED_OR_TRUNCATED"
    if bool(row.get("response_merging_suspected_any_rank", False)):
        return "SHARED_IMAGE_RESPONSE"
    presence = str(row.get("candidate_presence_class_v2", ""))
    if "MISSING" in presence or "REPRESENTATION_FAILURE" in presence:
        return "CANDIDATE_MISSING"
    rank = pd.to_numeric(row.get("nearest_candidate_rank"), errors="coerce")
    if np.isfinite(rank) and float(rank) > 5:
        return "LOW_RANK_BEYOND_TOP5"
    if np.isfinite(rank) and float(rank) > 1:
        return "RANK_COMPETITION_TOP5"
    if np.isfinite(rank) and float(rank) == 1:
        return "TOP1_PRESENT"
    return "UNRESOLVED"


def build_entity_registry() -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates = pd.read_csv(CANDIDATES_CSV)
    candidates = candidates[candidates["candidate"] == PRIMARY].copy()
    candidate_rows = pd.DataFrame(
        {
            "entity_id": candidates.apply(
                lambda row: f"{row['frame_uid']}__C2R{int(row['rank']):04d}", axis=1
            ),
            "entity_kind": "SAR_ONLY_C2_CANDIDATE",
            "run_id": candidates["run_id"],
            "frame_uid": candidates["frame_uid"],
            "frame_index": candidates["frame_index"].astype(int),
            "x_px": candidates["x_px"].astype(float),
            "y_px": candidates["y_px"].astype(float),
            "target_id": "",
            "control_kind": "",
            "candidate_rank_existing": candidates["rank"].astype(int),
            "candidate_pool_count_existing": candidates.groupby("frame_uid")["rank"].transform("max"),
            "candidate_score_existing": candidates["score"].astype(float),
            "candidate_support_status_existing": candidates["support_status"].astype(str),
            "offline_response_state": "UNLABELED_CANDIDATE",
            "offline_shared_flag": False,
            "offline_candidate_presence_class": "",
            "source_provenance": "EXISTING_GT_BLIND_C2_CANDIDATE_CSV",
        }
    )

    references = pd.read_csv(REFERENCES_CSV)
    references = references[references["candidate"] == PRIMARY].copy()
    references["offline_response_state"] = references.apply(reference_primary_state, axis=1)
    reference_rows = pd.DataFrame(
        {
            "entity_id": references.apply(
                lambda row: f"{row['frame_uid']}__REF__{row['target_id']}", axis=1
            ),
            "entity_kind": "PERSON_REFERENCE",
            "run_id": references["run_id"],
            "frame_uid": references["frame_uid"],
            "frame_index": references["frame_index"].astype(int),
            "x_px": references["reference_x_px"].astype(float),
            "y_px": references["reference_y_px"].astype(float),
            "target_id": references["target_id"].astype(str),
            "control_kind": "",
            "candidate_rank_existing": pd.to_numeric(
                references["nearest_candidate_rank"], errors="coerce"
            ),
            "candidate_pool_count_existing": references["candidate_count_frame"].astype(int),
            "candidate_score_existing": pd.to_numeric(
                references["nearest_candidate_score"], errors="coerce"
            ),
            "candidate_support_status_existing": references["reference_support_status"].astype(str),
            "offline_response_state": references["offline_response_state"],
            "offline_shared_flag": references["response_merging_suspected_any_rank"].astype(bool),
            "offline_candidate_presence_class": references["candidate_presence_class_v2"].astype(str),
            "source_provenance": "MANUAL_REFERENCE_OFFLINE_EVALUATION_ONLY",
        }
    )

    fixed = pd.read_csv(FIXED_OFFSETS_CSV)
    fixed = fixed[fixed["candidate"] == PRIMARY].copy()
    fixed_rows = pd.DataFrame(
        {
            "entity_id": fixed.apply(
                lambda row: (
                    f"{row['frame_uid']}__FIXED__{row['target_id']}__{row['control_direction']}"
                ),
                axis=1,
            ),
            "entity_kind": "FIXED_OFFSET_CONTROL",
            "run_id": fixed["run_id"],
            "frame_uid": fixed["frame_uid"],
            "frame_index": fixed["frame_index"].astype(int),
            "x_px": fixed["control_x_px"].astype(float),
            "y_px": fixed["control_y_px"].astype(float),
            "target_id": fixed["target_id"].astype(str),
            "control_kind": fixed["control_direction"].astype(str),
            "candidate_rank_existing": pd.to_numeric(fixed["nearest_candidate_rank"], errors="coerce"),
            "candidate_pool_count_existing": np.nan,
            "candidate_score_existing": pd.to_numeric(fixed["nearest_candidate_score"], errors="coerce"),
            "candidate_support_status_existing": fixed["control_support_status"].astype(str),
            "offline_response_state": "FIXED_OFFSET_CONTROL",
            "offline_shared_flag": False,
            "offline_candidate_presence_class": "",
            "source_provenance": "EXISTING_FIXED_1P25M_CONTROL",
        }
    )

    old = pd.read_csv(OLD_METRICS_CSV)
    old = old[old["candidate"] == PRIMARY].copy()
    matched_records: list[dict[str, Any]] = []
    hard_records: list[dict[str, Any]] = []
    for row in old.to_dict("records"):
        controls = json.loads(row["controls_json"])
        for index, item in enumerate(controls.get("matched", []), start=1):
            matched_records.append(
                {
                    "entity_id": f"{row['frame_uid']}__MATCHED__{row['target_id']}__{index:02d}",
                    "entity_kind": "GEOMETRY_MATCHED_CONTROL",
                    "run_id": row["run_id"],
                    "frame_uid": row["frame_uid"],
                    "frame_index": int(row["frame_index"]),
                    "x_px": float(item["x"]),
                    "y_px": float(item["y"]),
                    "target_id": str(row["target_id"]),
                    "control_kind": str(item["kind"]),
                    "candidate_rank_existing": math.nan,
                    "candidate_pool_count_existing": math.nan,
                    "candidate_score_existing": float(item["score"]),
                    "candidate_support_status_existing": "",
                    "offline_response_state": "GEOMETRY_MATCHED_CONTROL",
                    "offline_shared_flag": False,
                    "offline_candidate_presence_class": "",
                    "source_provenance": "EXISTING_SAME_RANGE_TANGENTIAL_CONTROL",
                }
            )
        hard = controls.get("hard")
        if hard is not None:
            hard_records.append(
                {
                    "entity_id": f"{row['frame_uid']}__LOCAL_COMPETING__{row['target_id']}",
                    "entity_kind": "LOCAL_COMPETING_CONTROL",
                    "run_id": row["run_id"],
                    "frame_uid": row["frame_uid"],
                    "frame_index": int(row["frame_index"]),
                    "x_px": float(hard["x"]),
                    "y_px": float(hard["y"]),
                    "target_id": str(row["target_id"]),
                    "control_kind": "LOCAL_MAX_COMPETING_RESPONSE",
                    "candidate_rank_existing": math.nan,
                    "candidate_pool_count_existing": math.nan,
                    "candidate_score_existing": float(hard["score"]),
                    "candidate_support_status_existing": "",
                    "offline_response_state": "LOCAL_COMPETING_CONTROL",
                    "offline_shared_flag": False,
                    "offline_candidate_presence_class": "",
                    "source_provenance": "EXISTING_LOCAL_COMPETING_RESPONSE_CONTROL",
                }
            )
    matched_rows = pd.DataFrame(matched_records)
    hard_rows = pd.DataFrame(hard_records)
    entities = pd.concat(
        [candidate_rows, reference_rows, fixed_rows, matched_rows, hard_rows],
        ignore_index=True,
        sort=False,
    )
    if entities["entity_id"].duplicated().any():
        duplicates = entities.loc[entities["entity_id"].duplicated(), "entity_id"].head().tolist()
        raise RuntimeError(f"duplicate entity IDs: {duplicates}")
    return entities, references


def build_optical_shell_registry(
    explorer: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, tuple[float, float]]]:
    frame_registry: dict[str, dict[str, Any]] = {}
    common_fov_by_run: dict[str, tuple[float, float]] = {}
    by_run = defaultdict(list)
    for frame in explorer["frames"]:
        if frame["run_id"] in RUNS:
            by_run[frame["run_id"]].append(frame)
    for run_id, frames in by_run.items():
        frames = sorted(frames, key=lambda item: int(item["sar_timestamp_ms"]))
        common_low = max(
            float(frames[0]["theta_low_deg"]),
            OPTICAL_INTERCEPT_DEG,
        )
        common_high = min(
            float(frames[0]["theta_high_deg"]),
            OPTICAL_SLOPE_DEG_PER_PX * OPTICAL_WIDTH_PX + OPTICAL_INTERCEPT_DEG,
        )
        common_fov_by_run[run_id] = (common_low, common_high)
        timestamps = np.asarray([int(item["sar_timestamp_ms"]) for item in frames], dtype=int)
        for index, frame in enumerate(frames):
            nominal = [
                (float(item["theta_shell_low_deg"]), float(item["theta_shell_high_deg"]))
                for item in frame.get("optical_persons", [])
            ]
            select = np.flatnonzero(np.abs(timestamps - int(frame["sar_timestamp_ms"])) <= OPTICAL_TIME_WINDOW_MS)
            window: list[tuple[float, float]] = []
            for selected in select:
                window.extend(
                    (
                        float(item["theta_shell_low_deg"]),
                        float(item["theta_shell_high_deg"]),
                    )
                    for item in frames[int(selected)].get("optical_persons", [])
                )
            nominal = union_intervals(nominal)
            window = union_intervals(window)
            negative = [(low - OPTICAL_SHELL_SHIFT_DEG, high - OPTICAL_SHELL_SHIFT_DEG) for low, high in window]
            positive = [(low + OPTICAL_SHELL_SHIFT_DEG, high + OPTICAL_SHELL_SHIFT_DEG) for low, high in window]
            fan_low = float(frame["theta_low_deg"])
            fan_high = float(frame["theta_high_deg"])
            fan_width = fan_high - fan_low
            frame_registry[frame["sar_frame_uid"]] = {
                "nominal_intervals": nominal,
                "window_intervals": window,
                "shift_negative_intervals": negative,
                "shift_positive_intervals": positive,
                "nominal_shell_count": len(frame.get("optical_persons", [])),
                "window_source_frame_count": int(len(select)),
                "window_shell_count_raw": int(
                    sum(len(frames[int(selected)].get("optical_persons", [])) for selected in select)
                ),
                "nominal_union_width_in_fan_deg": interval_width_in_fan(nominal, fan_low, fan_high),
                "window_union_width_in_fan_deg": interval_width_in_fan(window, fan_low, fan_high),
                "shift_negative_union_width_in_fan_deg": interval_width_in_fan(negative, fan_low, fan_high),
                "shift_positive_union_width_in_fan_deg": interval_width_in_fan(positive, fan_low, fan_high),
                "fan_width_deg": fan_width,
                "sync_status": frame.get("sync_status", ""),
                "guidance_statuses": sorted(
                    {str(item.get("azimuth_guidance_status", "")) for item in frame.get("optical_persons", [])}
                ),
            }
    return frame_registry, common_fov_by_run


def load_pair_registry(
    freeze: dict[str, Any], frame_map: dict[str, dict[str, Any]]
) -> tuple[dict[tuple[str, str, str, int], dict[str, Any]], pd.DataFrame]:
    selected_by_lag = {int(key): value for key, value in freeze["frozen"]["selected_model_by_lag"].items()}
    pair_metrics = pd.concat(
        [pd.read_csv(P0_PAIR_METRICS_CSV), pd.read_csv(B0R_PAIR_METRICS_CSV)],
        ignore_index=True,
    )
    comparability = pd.concat(
        [pd.read_csv(P0_COMPARABILITY_CSV), pd.read_csv(B0R_COMPARABILITY_CSV)],
        ignore_index=True,
    )
    anchors = pd.concat(
        [pd.read_csv(P0_ANCHORS_CSV), pd.read_csv(B0R_ANCHORS_CSV)],
        ignore_index=True,
    )
    anchor_groups = {
        (str(run_id), str(from_uid), str(to_uid), int(lag)): group.copy()
        for (run_id, from_uid, to_uid, lag), group in anchors[
            anchors["anchor_split"] == "HOLDOUT"
        ].groupby(["run_id", "from_frame_uid", "to_frame_uid", "lag"], sort=False)
    }
    model_records: dict[tuple[str, str, str, int, str], dict[str, Any]] = {}
    for path in (P0_MODELS_JSONL, B0R_MODELS_JSONL):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            record = json.loads(line)
            key = (
                str(record["run_id"]),
                str(record["from_frame_uid"]),
                str(record["to_frame_uid"]),
                int(record["lag"]),
                str(record["model"]),
            )
            model_records[key] = record
    selected_metrics = pair_metrics[
        pair_metrics.apply(
            lambda row: str(row["model"]) == selected_by_lag[int(row["lag"])], axis=1
        )
    ].copy()
    comp_index = comparability.set_index(["run_id", "from_frame_uid", "to_frame_uid", "lag"])
    registry: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for row in selected_metrics.to_dict("records"):
        key = (
            str(row["run_id"]),
            str(row["from_frame_uid"]),
            str(row["to_frame_uid"]),
            int(row["lag"]),
        )
        model_key = (*key, str(row["model"]))
        comp = comp_index.loc[key]
        pair_anchors = anchor_groups.get(key, pd.DataFrame()).copy()
        registry[key] = {
            "run_id": key[0],
            "from_frame_uid": key[1],
            "to_frame_uid": key[2],
            "lag": key[3],
            "from_frame": int(row["from_frame"]),
            "to_frame": int(row["to_frame"]),
            "selected_model": str(row["model"]),
            "model_available": bool(row["model_available"]),
            "model_state": model_records[model_key]["model_state"],
            "pair_comparable": bool(comp["comparable"]),
            "comparability_reason": str(comp["comparability_reason"]),
            "pair_valid_fraction": float(comp["pair_valid_fraction"]),
            "fit_anchor_count": int(comp["fit_anchor_count"]),
            "holdout_anchor_count": int(comp["holdout_anchor_count"]),
            "holdout_residual_median_px": float(row["holdout_residual_median_px"]),
            "holdout_residual_p90_px": float(row["holdout_residual_p90_px"]),
            "display_js_divergence": float(row["display_js_divergence"]),
            "display_stratum": str(row["display_stratum"]),
            "holdout_improved_vs_M0": bool(row["holdout_improved_vs_M0"]),
            "holdout_relative_reduction_vs_M0": float(row["holdout_relative_reduction_vs_M0"]),
            "anchors": pair_anchors,
            "from_geometry": frame_map[key[1]]["geometry"],
            "to_geometry": frame_map[key[2]]["geometry"],
        }
    return registry, selected_metrics


def support_label(fraction: float, center_valid: bool) -> str:
    if not center_valid or not np.isfinite(fraction) or fraction < 0.50:
        return "INVALID"
    if fraction < 0.80:
        return "TRUNCATED"
    return "FULL"


def compute_frame_observations(
    context: FrameContext,
    entities: pd.DataFrame,
    frame_candidates: pd.DataFrame,
    optical: dict[str, Any],
    common_fov: tuple[float, float],
) -> pd.DataFrame:
    if entities.empty:
        return pd.DataFrame()
    records = entities.copy().reset_index(drop=True)
    points = records[["x_px", "y_px"]].to_numpy(float)
    geometry = context.frame["geometry"]
    radial_px, theta = point_polar(points, geometry)
    range_m = radial_px / context.px_per_m
    left_margin = theta - float(context.frame["theta_low_deg"])
    right_margin = float(context.frame["theta_high_deg"]) - theta
    side_margin = np.minimum(left_margin, right_margin)
    outer_margin = float(geometry["outer_range_m"]) - range_m
    support = sample_nearest(context.support_fraction, points, default=0.0)
    center_valid = sample_bool(context.omega_single, points)
    frozen_valid = sample_bool(context.frozen_p0_mask, points)
    c2_score = sample_nearest(context.c2_map, points)
    c3_score = sample_nearest(context.c3_map, points)
    c2_percentile = sample_nearest(context.c2_percentile_map, points)

    candidate_xy = frame_candidates[["x_px", "y_px"]].to_numpy(float)
    candidate_score = frame_candidates["score"].to_numpy(float)
    candidate_rank = frame_candidates["rank"].to_numpy(int)
    pool_count = len(frame_candidates)
    if pool_count:
        distances_m = np.linalg.norm(
            points[:, None, :] - candidate_xy[None, :, :], axis=2
        ) / context.px_per_m
        nearest_index = np.argmin(distances_m, axis=1)
        nearest_distance = distances_m[np.arange(len(points)), nearest_index]
        nearest_rank = candidate_rank[nearest_index]
        nearest_score = candidate_score[nearest_index]
        density_1 = np.sum(distances_m <= DENSITY_RADII_M[0], axis=1)
        density_2 = np.sum(distances_m <= DENSITY_RADII_M[1], axis=1)
        local_max = np.full(len(points), np.nan, dtype=float)
        for index in range(len(points)):
            select = distances_m[index] <= LOCAL_COMPETITOR_RADIUS_M
            if records.at[index, "entity_kind"] == "SAR_ONLY_C2_CANDIDATE":
                self_rank = pd.to_numeric(records.at[index, "candidate_rank_existing"], errors="coerce")
                if np.isfinite(self_rank):
                    select &= candidate_rank != int(self_rank)
                density_1[index] = max(int(density_1[index]) - 1, 0)
                density_2[index] = max(int(density_2[index]) - 1, 0)
            if np.any(select):
                local_max[index] = float(np.max(candidate_score[select]))
    else:
        nearest_distance = np.full(len(points), math.nan)
        nearest_rank = np.full(len(points), math.nan)
        nearest_score = np.full(len(points), math.nan)
        density_1 = np.zeros(len(points), dtype=int)
        density_2 = np.zeros(len(points), dtype=int)
        local_max = np.full(len(points), math.nan)

    structure_radius_px = max(1, int(round(STRUCTURE_RADIUS_M * context.px_per_m)))
    structure_sample = local_weighted_structure_points(
        context.c2_map,
        context.omega_single,
        points,
        structure_radius_px,
        context.px_per_m,
    )

    nominal_intervals = optical["nominal_intervals"]
    window_intervals = optical["window_intervals"]
    negative_intervals = optical["shift_negative_intervals"]
    positive_intervals = optical["shift_positive_intervals"]
    common_low, common_high = common_fov

    records["range_m"] = range_m
    records["azimuth_deg"] = theta
    records["left_fan_boundary_distance_deg"] = left_margin
    records["right_fan_boundary_distance_deg"] = right_margin
    records["nearest_side_boundary_distance_deg"] = side_margin
    records["nearest_side_boundary_arc_distance_m"] = range_m * np.radians(
        np.maximum(side_margin, 0.0)
    )
    records["outer_range_boundary_distance_m"] = outer_margin
    records["support_valid_fraction"] = support
    records["support_status"] = [
        support_label(float(value), bool(valid)) for value, valid in zip(support, center_valid)
    ]
    records["inside_omega_single_center"] = center_valid
    records["inside_frozen_p0_base_mask"] = frozen_valid
    records["C2_score_at_position"] = c2_score
    records["C2_percentile_in_frame_valid_region"] = c2_percentile
    records["C3_score_at_position"] = c3_score
    records["nearest_C2_candidate_distance_m"] = nearest_distance
    records["nearest_C2_candidate_rank"] = nearest_rank
    records["nearest_C2_candidate_score"] = nearest_score
    records["nearest_C2_candidate_rank_fraction"] = (
        nearest_rank.astype(float) / float(pool_count) if pool_count else math.nan
    )
    records["C2_candidate_pool_count"] = int(pool_count)
    records["other_C2_candidate_count_1m"] = density_1
    records["other_C2_candidate_count_2m"] = density_2
    records["local_competing_C2_max_1p25m"] = local_max
    records["C2_minus_local_competing_max_1p25m"] = c2_score - local_max
    for name, values in structure_sample.items():
        records[name] = values

    records["multimodal_common_fov_status"] = np.where(
        (theta >= common_low) & (theta <= common_high),
        "MULTIMODAL_COMMON_FOV_PROVISIONAL",
        "OUTSIDE_PROVISIONAL_COMMON_FOV",
    )
    records["common_fov_theta_low_deg"] = common_low
    records["common_fov_theta_high_deg"] = common_high
    records["optical_nominal_shell_count"] = int(optical["nominal_shell_count"])
    records["optical_window_source_frame_count"] = int(optical["window_source_frame_count"])
    records["optical_window_shell_count_raw"] = int(optical["window_shell_count_raw"])
    records["inside_optical_nominal_shell_union"] = inside_intervals(theta, nominal_intervals)
    records["inside_optical_window_250ms_shell_union"] = inside_intervals(theta, window_intervals)
    records["inside_shifted_shell_minus18deg_union"] = inside_intervals(theta, negative_intervals)
    records["inside_shifted_shell_plus18deg_union"] = inside_intervals(theta, positive_intervals)
    records["angular_distance_to_optical_nominal_shell_deg"] = distance_to_intervals(
        theta, nominal_intervals
    )
    records["angular_distance_to_optical_window_shell_deg"] = distance_to_intervals(
        theta, window_intervals
    )
    records["optical_nominal_union_width_in_fan_deg"] = float(
        optical["nominal_union_width_in_fan_deg"]
    )
    records["optical_window_union_width_in_fan_deg"] = float(
        optical["window_union_width_in_fan_deg"]
    )
    records["shifted_minus_union_width_in_fan_deg"] = float(
        optical["shift_negative_union_width_in_fan_deg"]
    )
    records["shifted_plus_union_width_in_fan_deg"] = float(
        optical["shift_positive_union_width_in_fan_deg"]
    )
    records["optical_shell_provenance"] = (
        "PROVISIONAL_R01_R04_CENTERLINE_PLUS_6DEG_GUARD_SYNC_UNVERIFIED"
    )
    records["optical_shell_used_target_id_for_selection"] = False
    return records


def local_anchor_metrics(
    pair: dict[str, Any], points: np.ndarray, px_per_m: float
) -> dict[str, np.ndarray]:
    anchors = pair["anchors"]
    residual_column = f"{pair['selected_model']}_residual_px"
    if anchors.empty or residual_column not in anchors:
        count = len(points)
        return {
            "anchor_mode": np.array(["NO_HOLDOUT_ANCHORS"] * count, dtype=object),
            "anchor_count": np.zeros(count, dtype=int),
            "local_p50_px": np.full(count, math.nan),
            "local_p90_px": np.full(count, math.nan),
            "local_max_distance_px": np.full(count, math.nan),
            "radial_bracket": np.zeros(count, dtype=bool),
            "theta_bracket": np.zeros(count, dtype=bool),
            "radial_span_m": np.full(count, math.nan),
            "theta_span_deg": np.full(count, math.nan),
            "epsilon_px": np.full(count, math.nan),
            "sigma_px": np.full(count, math.nan),
            "sigma_m": np.full(count, math.nan),
        }
    finite = anchors[
        pd.to_numeric(anchors[residual_column], errors="coerce").notna()
    ].copy()
    anchor_xy = finite[["x_px", "y_px"]].to_numpy(float)
    residual = finite[residual_column].to_numpy(float)
    anchor_radial, anchor_theta = point_polar(anchor_xy, pair["from_geometry"])
    point_radial, point_theta = point_polar(points, pair["from_geometry"])
    distances = np.linalg.norm(points[:, None, :] - anchor_xy[None, :, :], axis=2)
    outputs: dict[str, list[Any]] = defaultdict(list)
    for index in range(len(points)):
        selected = np.flatnonzero(distances[index] <= LOCAL_ANCHOR_RADIUS_PX)
        mode = "RADIUS_144PX"
        if len(selected) < LOCAL_ANCHOR_MIN_COUNT:
            selected = np.argsort(distances[index])[: min(LOCAL_ANCHOR_MIN_COUNT, len(anchor_xy))]
            mode = "NEAREST8_FALLBACK"
        if not len(selected):
            local_p50 = local_p90 = max_distance = radial_span = theta_span = math.nan
            radial_bracket = theta_bracket = False
        else:
            selected_residual = residual[selected]
            local_p50 = float(np.quantile(selected_residual, 0.50))
            local_p90 = float(np.quantile(selected_residual, 0.90))
            max_distance = float(np.max(distances[index, selected]))
            radial_min = float(np.min(anchor_radial[selected]))
            radial_max = float(np.max(anchor_radial[selected]))
            theta_min = float(np.min(anchor_theta[selected]))
            theta_max = float(np.max(anchor_theta[selected]))
            radial_bracket = radial_min <= point_radial[index] <= radial_max
            theta_bracket = theta_min <= point_theta[index] <= theta_max
            radial_span = (radial_max - radial_min) / px_per_m
            theta_span = theta_max - theta_min
        epsilon = (
            max(local_p90, float(pair["holdout_residual_p90_px"]), UNCERTAINTY_FLOOR_PX)
            if np.isfinite(local_p90)
            else math.nan
        )
        sigma = (
            math.sqrt(epsilon * epsilon + (MODEL_SUPPORT_RADIUS_M * px_per_m) ** 2)
            if np.isfinite(epsilon)
            else math.nan
        )
        outputs["anchor_mode"].append(mode)
        outputs["anchor_count"].append(int(len(selected)))
        outputs["local_p50_px"].append(local_p50)
        outputs["local_p90_px"].append(local_p90)
        outputs["local_max_distance_px"].append(max_distance)
        outputs["radial_bracket"].append(bool(radial_bracket))
        outputs["theta_bracket"].append(bool(theta_bracket))
        outputs["radial_span_m"].append(radial_span)
        outputs["theta_span_deg"].append(theta_span)
        outputs["epsilon_px"].append(epsilon)
        outputs["sigma_px"].append(sigma)
        outputs["sigma_m"].append(sigma / px_per_m if np.isfinite(sigma) else math.nan)
    return {key: np.asarray(value) for key, value in outputs.items()}


def remap_points(
    field: np.ndarray, points: np.ndarray, interpolation: int = cv2.INTER_LINEAR
) -> np.ndarray:
    if not len(points):
        return np.array([], dtype=float)
    map_x = points[:, 0].astype(np.float32).reshape(-1, 1)
    map_y = points[:, 1].astype(np.float32).reshape(-1, 1)
    values = cv2.remap(
        field.astype(np.float32),
        map_x,
        map_y,
        interpolation,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=np.nan if interpolation != cv2.INTER_NEAREST else 0.0,
    )
    return values.reshape(-1).astype(float)


def compute_local_p0_rows(
    p0: Any,
    pair: dict[str, Any],
    source: FrameContext,
    destination: FrameContext,
    entities: pd.DataFrame,
) -> pd.DataFrame:
    if entities.empty:
        return pd.DataFrame()
    points = entities[["x_px", "y_px"]].to_numpy(float)
    local = local_anchor_metrics(pair, points, source.px_per_m)
    if pair["model_available"]:
        displacement = p0.predict_displacement(pair["model_state"], points, pair["from_geometry"])
    else:
        displacement = np.full_like(points, np.nan)
    predicted = points + displacement
    source_single = sample_nearest(source.support_fraction, points, default=0.0) >= 0.50
    source_frozen = sample_bool(source.frozen_p0_mask, points)
    predicted_single = sample_nearest(destination.support_fraction, predicted, default=0.0) >= 0.50
    zero_single = sample_nearest(destination.support_fraction, points, default=0.0) >= 0.50
    displacement_px = np.linalg.norm(displacement, axis=1)
    displacement_m = displacement_px / source.px_per_m
    sigma_m = local["sigma_m"].astype(float)
    separability = displacement_m / np.maximum(sigma_m, 1e-12)
    source_score = sample_nearest(source.c2_map, points)
    destination_correct_score = remap_points(destination.c2_map, predicted)
    destination_zero_score = remap_points(destination.c2_map, points)
    destination_correct_percentile = remap_points(destination.c2_percentile_map, predicted)
    destination_zero_percentile = remap_points(destination.c2_percentile_map, points)

    domain: list[str] = []
    reasons: list[str] = []
    for index in range(len(points)):
        core_reasons: list[str] = []
        if not pair["pair_comparable"]:
            core_reasons.append(f"PAIR_{pair['comparability_reason']}")
        if not pair["model_available"]:
            core_reasons.append("SELECTED_MODEL_UNAVAILABLE")
        if not bool(source_frozen[index]):
            core_reasons.append("SOURCE_OUTSIDE_FROZEN_P0_BASE_MASK")
        if str(local["anchor_mode"][index]) != "RADIUS_144PX":
            core_reasons.append("NEAREST8_FALLBACK")
        if int(local["anchor_count"][index]) < LOCAL_ANCHOR_MIN_COUNT:
            core_reasons.append("LOW_LOCAL_ANCHOR_COUNT")
        if not bool(local["radial_bracket"][index]):
            core_reasons.append("NO_RADIAL_BRACKET")
        if not bool(local["theta_bracket"][index]):
            core_reasons.append("NO_AZIMUTH_BRACKET")
        if not bool(predicted_single[index]):
            core_reasons.append("PREDICTION_OUTSIDE_DESTINATION_OMEGA_SINGLE")
        if not core_reasons:
            domain.append("P0_TRANSPORT_CORE")
            reasons.append("CORE_LOCAL_HELDOUT_SUPPORT")
        elif pair["model_available"] and bool(source_single[index]) and bool(predicted_single[index]):
            domain.append("P0_TRANSPORT_EXTENDED")
            reasons.append("|".join(core_reasons))
        else:
            domain.append("P0_TRANSPORT_UNAVAILABLE")
            reasons.append("|".join(core_reasons) if core_reasons else "UNAVAILABLE")

    rows = entities[
        ["entity_id", "entity_kind", "run_id", "frame_uid", "frame_index", "target_id"]
    ].copy()
    rows["from_frame_uid"] = pair["from_frame_uid"]
    rows["to_frame_uid"] = pair["to_frame_uid"]
    rows["to_frame_index"] = pair["to_frame"]
    rows["lag"] = pair["lag"]
    rows["selected_model"] = pair["selected_model"]
    rows["pair_comparable"] = pair["pair_comparable"]
    rows["comparability_reason"] = pair["comparability_reason"]
    rows["model_available"] = pair["model_available"]
    rows["pair_valid_fraction"] = pair["pair_valid_fraction"]
    rows["global_holdout_median_px"] = pair["holdout_residual_median_px"]
    rows["global_holdout_p90_px"] = pair["holdout_residual_p90_px"]
    rows["display_js_divergence"] = pair["display_js_divergence"]
    rows["display_stratum"] = pair["display_stratum"]
    rows["holdout_improved_vs_M0"] = pair["holdout_improved_vs_M0"]
    rows["local_anchor_mode"] = local["anchor_mode"]
    rows["local_holdout_anchor_count"] = local["anchor_count"]
    rows["local_holdout_p50_px"] = local["local_p50_px"]
    rows["local_holdout_p90_px"] = local["local_p90_px"]
    rows["local_holdout_max_distance_px"] = local["local_max_distance_px"]
    rows["radial_anchor_bracket"] = local["radial_bracket"]
    rows["azimuth_anchor_bracket"] = local["theta_bracket"]
    rows["radial_anchor_coverage_span_m"] = local["radial_span_m"]
    rows["azimuth_anchor_coverage_span_deg"] = local["theta_span_deg"]
    rows["epsilon_P0_px"] = local["epsilon_px"]
    rows["sigma_region_px"] = local["sigma_px"]
    rows["sigma_region_m"] = sigma_m
    rows["source_inside_omega_single"] = source_single
    rows["source_inside_frozen_p0_base_mask"] = source_frozen
    rows["prediction_inside_destination_omega_single"] = predicted_single
    rows["zero_location_inside_destination_omega_single"] = zero_single
    rows["predicted_x_px"] = predicted[:, 0]
    rows["predicted_y_px"] = predicted[:, 1]
    rows["transport_displacement_px"] = displacement_px
    rows["transport_displacement_m"] = displacement_m
    rows["transport_separability_displacement_over_sigma"] = separability
    rows["P0_transport_domain"] = domain
    rows["P0_transport_domain_reasons"] = reasons
    rows["source_C2_score"] = source_score
    rows["destination_C2_score_correct_transport"] = destination_correct_score
    rows["destination_C2_score_zero_transport"] = destination_zero_score
    rows["destination_C2_percentile_correct_transport"] = destination_correct_percentile
    rows["destination_C2_percentile_zero_transport"] = destination_zero_percentile
    rows["destination_C2_score_correct_minus_zero"] = (
        destination_correct_score - destination_zero_score
    )
    rows["destination_C2_percentile_correct_minus_zero"] = (
        destination_correct_percentile - destination_zero_percentile
    )
    rows["target_motion_used"] = False
    rows["next_frame_reference_used"] = False
    return rows


def compute_pair_tradeoff(
    p0: Any,
    pair: dict[str, Any],
    source: FrameContext,
    destination: FrameContext,
) -> dict[str, Any]:
    yy, xx = np.mgrid[
        0 : source.omega_single.shape[0] : FIELD_GRID_STRIDE_PX,
        0 : source.omega_single.shape[1] : FIELD_GRID_STRIDE_PX,
    ]
    points = np.column_stack((xx.ravel(), yy.ravel())).astype(float)
    source_valid = sample_nearest(source.support_fraction, points, default=0.0) >= 0.80
    points = points[source_valid]
    if not len(points) or not pair["model_available"]:
        return {
            "run_id": pair["run_id"],
            "from_frame_uid": pair["from_frame_uid"],
            "to_frame_uid": pair["to_frame_uid"],
            "from_frame": pair["from_frame"],
            "to_frame": pair["to_frame"],
            "lag": pair["lag"],
            "selected_model": pair["selected_model"],
            "pair_comparable": pair["pair_comparable"],
            "comparison_grid_count": 0,
        }
    displacement = p0.predict_displacement(pair["model_state"], points, pair["from_geometry"])
    predicted = points + displacement
    correct_valid = remap_points(
        (destination.support_fraction >= 0.80).astype(np.float32), predicted, cv2.INTER_NEAREST
    ) >= 0.5
    zero_valid = remap_points(
        (destination.support_fraction >= 0.80).astype(np.float32), points, cv2.INTER_NEAREST
    ) >= 0.5
    common = correct_valid & zero_valid
    source_values = remap_points(source.c2_map, points)
    correct_values = remap_points(destination.c2_map, predicted)
    zero_values = remap_points(destination.c2_map, points)
    valid = common & np.isfinite(source_values) & np.isfinite(correct_values) & np.isfinite(zero_values)
    if np.any(valid):
        high_cutoff = float(np.quantile(source_values[valid], 0.90))
        high = valid & (source_values >= high_cutoff)
    else:
        high_cutoff = math.nan
        high = np.zeros(len(points), dtype=bool)

    sigma_yy, sigma_xx = np.mgrid[
        0 : source.omega_single.shape[0] : SIGMA_GRID_STRIDE_PX,
        0 : source.omega_single.shape[1] : SIGMA_GRID_STRIDE_PX,
    ]
    sigma_points = np.column_stack((sigma_xx.ravel(), sigma_yy.ravel())).astype(float)
    sigma_points = sigma_points[sample_bool(source.omega_single, sigma_points)]
    local = local_anchor_metrics(pair, sigma_points, source.px_per_m)
    sigma_displacement = p0.predict_displacement(
        pair["model_state"], sigma_points, pair["from_geometry"]
    )
    displacement_m = np.linalg.norm(sigma_displacement, axis=1) / source.px_per_m
    sigma_m = local["sigma_m"].astype(float)
    separability = displacement_m / np.maximum(sigma_m, 1e-12)
    predicted_sigma_points = sigma_points + sigma_displacement
    sigma_source_frozen = sample_bool(source.frozen_p0_mask, sigma_points)
    sigma_destination_valid = sample_nearest(
        destination.support_fraction, predicted_sigma_points, default=0.0
    ) >= 0.50
    sigma_core = (
        pair["pair_comparable"]
        & pair["model_available"]
        & sigma_source_frozen
        & (local["anchor_mode"] == "RADIUS_144PX")
        & (local["anchor_count"].astype(int) >= LOCAL_ANCHOR_MIN_COUNT)
        & local["radial_bracket"].astype(bool)
        & local["theta_bracket"].astype(bool)
        & sigma_destination_valid
    )

    displacement_all_m = np.linalg.norm(displacement, axis=1) / source.px_per_m
    return {
        "run_id": pair["run_id"],
        "from_frame_uid": pair["from_frame_uid"],
        "to_frame_uid": pair["to_frame_uid"],
        "from_frame": pair["from_frame"],
        "to_frame": pair["to_frame"],
        "lag": pair["lag"],
        "selected_model": pair["selected_model"],
        "pair_comparable": pair["pair_comparable"],
        "comparability_reason": pair["comparability_reason"],
        "pair_valid_fraction": pair["pair_valid_fraction"],
        "global_holdout_median_px": pair["holdout_residual_median_px"],
        "global_holdout_p90_px": pair["holdout_residual_p90_px"],
        "holdout_improved_vs_M0": pair["holdout_improved_vs_M0"],
        "display_js_divergence": pair["display_js_divergence"],
        "display_stratum": pair["display_stratum"],
        "field_grid_stride_px": FIELD_GRID_STRIDE_PX,
        "comparison_grid_count": int(valid.sum()),
        "comparison_grid_fraction_of_source": float(valid.mean()) if len(valid) else math.nan,
        "C2_field_retention_correct_pearson": pearson_finite(
            source_values[valid], correct_values[valid]
        ),
        "C2_field_retention_zero_pearson": pearson_finite(
            source_values[valid], zero_values[valid]
        ),
        "C2_field_retention_correct_minus_zero": (
            pearson_finite(source_values[valid], correct_values[valid])
            - pearson_finite(source_values[valid], zero_values[valid])
        ),
        "C2_field_mae_correct": (
            float(np.mean(np.abs(source_values[valid] - correct_values[valid])))
            if np.any(valid)
            else math.nan
        ),
        "C2_field_mae_zero": (
            float(np.mean(np.abs(source_values[valid] - zero_values[valid])))
            if np.any(valid)
            else math.nan
        ),
        "source_high_tail_cutoff_p90": high_cutoff,
        "source_high_tail_count": int(high.sum()),
        "destination_C2_mean_at_correct_for_source_high_tail": (
            float(np.mean(correct_values[high])) if np.any(high) else math.nan
        ),
        "destination_C2_mean_at_zero_for_source_high_tail": (
            float(np.mean(zero_values[high])) if np.any(high) else math.nan
        ),
        "high_tail_correct_minus_zero": (
            float(np.mean(correct_values[high]) - np.mean(zero_values[high]))
            if np.any(high)
            else math.nan
        ),
        "transport_displacement_median_m": float(np.median(displacement_all_m)),
        "transport_displacement_p90_m": float(np.quantile(displacement_all_m, 0.90)),
        "sigma_grid_stride_px": SIGMA_GRID_STRIDE_PX,
        "sigma_grid_count": int(len(sigma_points)),
        "local_sigma_median_m": float(np.nanmedian(sigma_m)),
        "local_sigma_p90_m": float(np.nanquantile(sigma_m, 0.90)),
        "transport_separability_median": float(np.nanmedian(separability)),
        "transport_separability_p10": float(np.nanquantile(separability, 0.10)),
        "transport_separability_p90": float(np.nanquantile(separability, 0.90)),
        "P0_transport_core_grid_fraction": float(np.mean(sigma_core)),
        "nearest8_fallback_grid_fraction": float(
            np.mean(local["anchor_mode"] == "NEAREST8_FALLBACK")
        ),
        "radial_bracket_grid_fraction": float(np.mean(local["radial_bracket"].astype(bool))),
        "azimuth_bracket_grid_fraction": float(np.mean(local["theta_bracket"].astype(bool))),
        "target_pixels_used_for_fit": 0,
        "reference_used_for_field_retention": False,
    }


def apply_display_flags(
    frame_display: pd.DataFrame,
    pair_registry: dict[tuple[str, str, str, int], dict[str, Any]],
) -> pd.DataFrame:
    output = frame_display.copy()
    robust_columns = [
        "jet_p50",
        "jet_p95_minus_p05",
        "jet_high_plateau_fraction",
        "jet_low_plateau_fraction",
        "jet_effective_levels_32bin",
        "jet_lut_distance_p95",
        "nonwhite_fraction_in_geometric_fan",
    ]
    for column in robust_columns:
        output[f"robust_z_{column}"] = output.groupby("run_id", group_keys=False)[column].apply(
            robust_z
        )
    output["display_proxy_robust_shift"] = output[
        [f"robust_z_{column}" for column in robust_columns]
    ].abs().max(axis=1) > DISPLAY_ROBUST_Z
    adjacent: dict[str, list[str]] = defaultdict(list)
    adjacent_js: dict[str, list[float]] = defaultdict(list)
    for pair in pair_registry.values():
        if int(pair["lag"]) != 1:
            continue
        adjacent[pair["from_frame_uid"]].append(pair["display_stratum"])
        adjacent[pair["to_frame_uid"]].append(pair["display_stratum"])
        adjacent_js[pair["from_frame_uid"]].append(float(pair["display_js_divergence"]))
        adjacent_js[pair["to_frame_uid"]].append(float(pair["display_js_divergence"]))
    rank = {
        "BASELINE_GLOBAL_DISPLAY_DISTRIBUTION": 0,
        "ELEVATED_GLOBAL_DISPLAY_DISTRIBUTION_CHANGE": 1,
        "HIGH_GLOBAL_DISPLAY_DISTRIBUTION_CHANGE": 2,
    }
    output["max_adjacent_lag1_display_stratum"] = output["frame_uid"].map(
        lambda uid: max(adjacent.get(uid, ["BASELINE_GLOBAL_DISPLAY_DISTRIBUTION"]), key=lambda item: rank.get(item, -1))
    )
    output["max_adjacent_lag1_display_js"] = output["frame_uid"].map(
        lambda uid: max(adjacent_js.get(uid, [math.nan]))
    )
    output["display_high_censor_proxy"] = (
        output["jet_high_plateau_fraction"] >= DISPLAY_HIGH_CENSOR_FRACTION
    )
    output["display_compressed_proxy"] = (
        (output["jet_p95_minus_p05"] < DISPLAY_COMPRESSED_RANGE)
        | (output["jet_effective_levels_32bin"] <= DISPLAY_COMPRESSED_EFFECTIVE_LEVELS)
    )
    output["display_shift"] = (
        output["display_proxy_robust_shift"]
        | output["max_adjacent_lag1_display_stratum"].isin(
            [
                "ELEVATED_GLOBAL_DISPLAY_DISTRIBUTION_CHANGE",
                "HIGH_GLOBAL_DISPLAY_DISTRIBUTION_CHANGE",
            ]
        )
    )
    def state(row: pd.Series) -> str:
        labels = []
        if bool(row["display_high_censor_proxy"]):
            labels.append("DISPLAY_HIGH_CENSOR_PROXY")
        if bool(row["display_compressed_proxy"]):
            labels.append("DISPLAY_COMPRESSED_PROXY")
        if bool(row["display_shift"]):
            labels.append("DISPLAY_SHIFT")
        return "|".join(labels) if labels else "DISPLAY_BASELINE_PROXY"
    output["display_observation_state"] = output.apply(state, axis=1)
    return output


def pivot_p0_conditions(observations: pd.DataFrame, p0_local: pd.DataFrame) -> pd.DataFrame:
    output = observations.copy()
    fields = {
        "P0_transport_domain": "p0_transport_domain",
        "sigma_region_m": "p0_sigma_m",
        "transport_displacement_m": "p0_displacement_m",
        "transport_separability_displacement_over_sigma": "p0_displacement_over_sigma",
        "local_holdout_anchor_count": "p0_local_anchor_count",
        "local_anchor_mode": "p0_local_anchor_mode",
        "radial_anchor_bracket": "p0_radial_bracket",
        "azimuth_anchor_bracket": "p0_azimuth_bracket",
        "display_stratum": "p0_display_stratum",
        "destination_C2_score_correct_minus_zero": "p0_destination_C2_correct_minus_zero",
        "destination_C2_percentile_correct_minus_zero": "p0_destination_C2_percentile_correct_minus_zero",
    }
    for lag in LAGS:
        subset = p0_local[p0_local["lag"] == lag].set_index("entity_id")
        for source, prefix in fields.items():
            mapping = subset[source].to_dict()
            output[f"{prefix}_lag{lag}"] = output["entity_id"].map(mapping)
        output[f"p0_transport_domain_lag{lag}"] = output[f"p0_transport_domain_lag{lag}"].fillna(
            "P0_TRANSPORT_UNAVAILABLE"
        )
    return output


def build_condition_state_summary(observations: pd.DataFrame, p0_local: pd.DataFrame) -> pd.DataFrame:
    references = observations[observations["entity_kind"] == "PERSON_REFERENCE"].copy()
    rows: list[dict[str, Any]] = []
    numeric = [
        "range_m",
        "azimuth_deg",
        "nearest_side_boundary_distance_deg",
        "outer_range_boundary_distance_m",
        "support_valid_fraction",
        "C2_score_at_position",
        "C2_percentile_in_frame_valid_region",
        "nearest_C2_candidate_rank_fraction",
        "other_C2_candidate_count_1m",
        "C2_minus_local_competing_max_1p25m",
        "structure_anisotropy",
        "structure_spread_m",
        "jet_p95_minus_p05",
        "jet_high_plateau_fraction",
        "max_adjacent_lag1_display_js",
        "p0_sigma_m_lag1",
        "p0_displacement_over_sigma_lag1",
        "p0_local_anchor_count_lag1",
    ]
    for (run_id, state), group in references.groupby(["run_id", "offline_response_state"]):
        row: dict[str, Any] = {
            "summary_type": "REFERENCE_STATE_BY_RUN",
            "run_id": run_id,
            "response_state": state,
            "count": int(len(group)),
            "display_shift_fraction": float(group["display_shift"].mean()),
            "display_high_censor_proxy_fraction": float(
                group["display_high_censor_proxy"].mean()
            ),
            "optical_window_shell_coverage": float(
                group["inside_optical_window_250ms_shell_union"].mean()
            ),
            "P0_core_lag1_fraction": float(
                (group["p0_transport_domain_lag1"] == "P0_TRANSPORT_CORE").mean()
            ),
            "P0_extended_lag1_fraction": float(
                (group["p0_transport_domain_lag1"] == "P0_TRANSPORT_EXTENDED").mean()
            ),
        }
        for column in numeric:
            row[f"median_{column}"] = float(pd.to_numeric(group[column], errors="coerce").median())
        rows.append(row)
    for state, group in references.groupby("offline_response_state"):
        row = {
            "summary_type": "REFERENCE_STATE_ALL_RUNS",
            "run_id": "ALL",
            "response_state": state,
            "count": int(len(group)),
            "display_shift_fraction": float(group["display_shift"].mean()),
            "display_high_censor_proxy_fraction": float(
                group["display_high_censor_proxy"].mean()
            ),
            "optical_window_shell_coverage": float(
                group["inside_optical_window_250ms_shell_union"].mean()
            ),
            "P0_core_lag1_fraction": float(
                (group["p0_transport_domain_lag1"] == "P0_TRANSPORT_CORE").mean()
            ),
            "P0_extended_lag1_fraction": float(
                (group["p0_transport_domain_lag1"] == "P0_TRANSPORT_EXTENDED").mean()
            ),
        }
        for column in numeric:
            row[f"median_{column}"] = float(pd.to_numeric(group[column], errors="coerce").median())
        rows.append(row)

    reference_p0 = p0_local[p0_local["entity_kind"] == "PERSON_REFERENCE"]
    for (lag, domain), group in reference_p0.groupby(["lag", "P0_transport_domain"]):
        rows.append(
            {
                "summary_type": "REFERENCE_P0_DOMAIN",
                "run_id": "ALL",
                "response_state": domain,
                "lag": int(lag),
                "count": int(len(group)),
                "median_p0_sigma_m": float(group["sigma_region_m"].median()),
                "median_p0_displacement_over_sigma": float(
                    group["transport_separability_displacement_over_sigma"].median()
                ),
                "nearest8_fallback_fraction": float(
                    (group["local_anchor_mode"] == "NEAREST8_FALLBACK").mean()
                ),
                "radial_bracket_fraction": float(group["radial_anchor_bracket"].mean()),
                "azimuth_bracket_fraction": float(group["azimuth_anchor_bracket"].mean()),
            }
        )
    return pd.DataFrame(rows)


def build_optical_shell_audit(observations: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouping = ["entity_kind", "run_id"]
    for keys, group in observations.groupby(grouping):
        entity_kind, run_id = keys
        true_coverage = float(group["inside_optical_window_250ms_shell_union"].mean())
        minus_coverage = float(group["inside_shifted_shell_minus18deg_union"].mean())
        plus_coverage = float(group["inside_shifted_shell_plus18deg_union"].mean())
        true_width = float(group["optical_window_union_width_in_fan_deg"].mean())
        minus_width = float(group["shifted_minus_union_width_in_fan_deg"].mean())
        plus_width = float(group["shifted_plus_union_width_in_fan_deg"].mean())
        rows.append(
            {
                "entity_kind": entity_kind,
                "run_id": run_id,
                "offline_response_state": "ALL",
                "count": int(len(group)),
                "nominal_shell_coverage": float(group["inside_optical_nominal_shell_union"].mean()),
                "window_250ms_shell_coverage": true_coverage,
                "shift_minus18deg_coverage": minus_coverage,
                "shift_plus18deg_coverage": plus_coverage,
                "window_minus_median_shifted_coverage": true_coverage
                - float(np.median([minus_coverage, plus_coverage])),
                "mean_true_in_fan_width_deg": true_width,
                "mean_shift_minus_in_fan_width_deg": minus_width,
                "mean_shift_plus_in_fan_width_deg": plus_width,
                "coverage_per_degree_true": true_coverage / true_width if true_width > 0 else math.nan,
                "coverage_per_degree_shift_minus": minus_coverage / minus_width if minus_width > 0 else math.nan,
                "coverage_per_degree_shift_plus": plus_coverage / plus_width if plus_width > 0 else math.nan,
                "common_fov_fraction": float(
                    (group["multimodal_common_fov_status"] == "MULTIMODAL_COMMON_FOV_PROVISIONAL").mean()
                ),
            }
        )
    references = observations[observations["entity_kind"] == "PERSON_REFERENCE"]
    for (run_id, state), group in references.groupby(["run_id", "offline_response_state"]):
        true_coverage = float(group["inside_optical_window_250ms_shell_union"].mean())
        minus_coverage = float(group["inside_shifted_shell_minus18deg_union"].mean())
        plus_coverage = float(group["inside_shifted_shell_plus18deg_union"].mean())
        rows.append(
            {
                "entity_kind": "PERSON_REFERENCE",
                "run_id": run_id,
                "offline_response_state": state,
                "count": int(len(group)),
                "nominal_shell_coverage": float(group["inside_optical_nominal_shell_union"].mean()),
                "window_250ms_shell_coverage": true_coverage,
                "shift_minus18deg_coverage": minus_coverage,
                "shift_plus18deg_coverage": plus_coverage,
                "window_minus_median_shifted_coverage": true_coverage
                - float(np.median([minus_coverage, plus_coverage])),
                "mean_true_in_fan_width_deg": float(
                    group["optical_window_union_width_in_fan_deg"].mean()
                ),
                "mean_shift_minus_in_fan_width_deg": float(
                    group["shifted_minus_union_width_in_fan_deg"].mean()
                ),
                "mean_shift_plus_in_fan_width_deg": float(
                    group["shifted_plus_union_width_in_fan_deg"].mean()
                ),
                "coverage_per_degree_true": math.nan,
                "coverage_per_degree_shift_minus": math.nan,
                "coverage_per_degree_shift_plus": math.nan,
                "common_fov_fraction": float(
                    (group["multimodal_common_fov_status"] == "MULTIMODAL_COMMON_FOV_PROVISIONAL").mean()
                ),
            }
        )
    return pd.DataFrame(rows)


STATE_COLORS = {
    "TOP1_PRESENT": "#27c46b",
    "RANK_COMPETITION_TOP5": "#f6c344",
    "LOW_RANK_BEYOND_TOP5": "#ff8b3d",
    "CANDIDATE_MISSING": "#ef4d5d",
    "SHARED_IMAGE_RESPONSE": "#b35cff",
    "EDGE_CENSORED_OR_TRUNCATED": "#46a7ff",
    "EDGE_OR_SUPPORT_INVALID": "#65758b",
    "UNRESOLVED": "#d0d4dc",
}


def plot_reference_state_map(observations: pd.DataFrame, path: Path) -> None:
    references = observations[observations["entity_kind"] == "PERSON_REFERENCE"].copy()
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), sharex=True, sharey=True)
    for axis, run_id in zip(axes.ravel(), RUNS):
        group = references[references["run_id"] == run_id]
        for state, rows in group.groupby("offline_response_state"):
            axis.scatter(
                rows["azimuth_deg"],
                rows["range_m"],
                s=42,
                alpha=0.82,
                color=STATE_COLORS.get(state, "#cccccc"),
                label=f"{state} ({len(rows)})",
                edgecolors="black",
                linewidths=0.25,
            )
        axis.axhline(19.0, color="#ff4d4d", linestyle="--", linewidth=1.2, label="P0 outer core edge 19m")
        axis.axvline(-59.9283, color="#9aa4b1", linestyle=":", linewidth=1)
        axis.axvline(59.8336, color="#9aa4b1", linestyle=":", linewidth=1)
        axis.set_title(run_id)
        axis.set_xlabel("SAR azimuth (deg)")
        axis.set_ylabel("range (m)")
        axis.set_ylim(0, 20.5)
        axis.grid(alpha=0.18)
        if len(group):
            axis.legend(fontsize=7, loc="best")
    fig.suptitle("Manual PERSON response states in SAR range-azimuth observation space", fontsize=14)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_p0_reliability(p0_local: pd.DataFrame, path: Path) -> None:
    references = p0_local[p0_local["entity_kind"] == "PERSON_REFERENCE"].copy()
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.2), sharex=True, sharey=True)
    colors = {
        "P0_TRANSPORT_CORE": "#27c46b",
        "P0_TRANSPORT_EXTENDED": "#f6c344",
        "P0_TRANSPORT_UNAVAILABLE": "#ef4d5d",
    }
    for axis, lag in zip(axes, LAGS):
        group = references[references["lag"] == lag]
        for domain, rows in group.groupby("P0_transport_domain"):
            axis.scatter(
                rows["transport_displacement_m"],
                rows["sigma_region_m"],
                c=colors.get(domain, "gray"),
                s=34,
                alpha=0.75,
                label=f"{domain} ({len(rows)})",
            )
        limit = max(
            float(group["transport_displacement_m"].quantile(0.99)) if len(group) else 1.0,
            float(group["sigma_region_m"].quantile(0.99)) if len(group) else 1.0,
        )
        axis.plot([0, limit], [0, limit], color="white", linestyle="--", linewidth=1.0, alpha=0.8)
        axis.set_title(f"lag {lag}")
        axis.set_xlabel("frozen transport displacement (m)")
        axis.set_ylabel("local P0 uncertainty sigma (m)")
        axis.grid(alpha=0.2)
        axis.legend(fontsize=7)
    fig.suptitle("P0 transport displacement versus local uncertainty at offline PERSON references")
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor="#10151d")
    plt.close(fig)


def plot_lag_tradeoff(tradeoff: pd.DataFrame, path: Path) -> None:
    grouped = tradeoff.groupby("lag").agg(
        separability=("transport_separability_median", "median"),
        separability_p25=("transport_separability_median", lambda value: value.quantile(0.25)),
        separability_p75=("transport_separability_median", lambda value: value.quantile(0.75)),
        correct=("C2_field_retention_correct_pearson", "median"),
        zero=("C2_field_retention_zero_pearson", "median"),
        delta=("C2_field_retention_correct_minus_zero", "median"),
    ).reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    axes[0].plot(grouped["lag"], grouped["separability"], marker="o", color="#f6c344", linewidth=2)
    axes[0].fill_between(
        grouped["lag"], grouped["separability_p25"], grouped["separability_p75"], color="#f6c344", alpha=0.22
    )
    axes[0].set_title("Geometric separability | displacement / local sigma")
    axes[0].set_xlabel("lag (frames)")
    axes[0].set_ylabel("median ratio")
    axes[0].grid(alpha=0.2)
    axes[1].plot(grouped["lag"], grouped["correct"], marker="o", color="#27c46b", label="correct P0")
    axes[1].plot(grouped["lag"], grouped["zero"], marker="o", color="#46a7ff", label="zero transport")
    axes[1].plot(grouped["lag"], grouped["delta"], marker="s", color="#ff8b3d", label="correct - zero")
    axes[1].axhline(0, color="#9aa4b1", linewidth=1)
    axes[1].set_title("C2 field response retention")
    axes[1].set_xlabel("lag (frames)")
    axes[1].set_ylabel("Pearson / difference")
    axes[1].grid(alpha=0.2)
    axes[1].legend()
    fig.suptitle("Lag tradeoff: geometry becomes separable while display-domain response may decorrelate")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def plot_retention_vs_display(tradeoff: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), sharex=True, sharey=True)
    palette = {
        "BASELINE_GLOBAL_DISPLAY_DISTRIBUTION": "#27c46b",
        "ELEVATED_GLOBAL_DISPLAY_DISTRIBUTION_CHANGE": "#f6c344",
        "HIGH_GLOBAL_DISPLAY_DISTRIBUTION_CHANGE": "#ef4d5d",
    }
    for axis, lag in zip(axes, LAGS):
        group = tradeoff[tradeoff["lag"] == lag]
        for stratum, rows in group.groupby("display_stratum"):
            axis.scatter(
                rows["display_js_divergence"],
                rows["C2_field_retention_correct_pearson"],
                s=18,
                alpha=0.55,
                color=palette.get(stratum, "#bbbbbb"),
                label=stratum.replace("_GLOBAL_DISPLAY_DISTRIBUTION", ""),
            )
        axis.set_title(f"lag {lag}")
        axis.set_xlabel("display JS divergence")
        axis.grid(alpha=0.2)
        if lag == 1:
            axis.set_ylabel("correct-P0 C2 field retention")
        axis.legend(fontsize=7)
    fig.suptitle("Display-chain change versus transported C2 response retention")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_display_timeline(frame_display: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(15, 11), sharex=False)
    for axis, run_id in zip(axes, RUNS):
        group = frame_display[frame_display["run_id"] == run_id].sort_values("frame_index")
        axis.plot(group["frame_index"], group["jet_p95_minus_p05"], color="#46a7ff", label="JET p95-p05")
        axis.plot(group["frame_index"], group["jet_high_plateau_fraction"], color="#ef4d5d", label="high plateau fraction")
        shifted = group[group["display_shift"]]
        axis.scatter(shifted["frame_index"], shifted["jet_p95_minus_p05"], color="#f6c344", s=18, label="DISPLAY_SHIFT")
        axis.set_title(run_id)
        axis.set_ylabel("display proxy")
        axis.grid(alpha=0.18)
        axis.legend(fontsize=8, ncol=3)
    axes[-1].set_xlabel("SAR frame index")
    fig.suptitle("Frame-level pseudocolor observation states (not physical RCS)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_optical_shell_audit(optical_audit: pd.DataFrame, path: Path) -> None:
    subset = optical_audit[
        (optical_audit["offline_response_state"] == "ALL")
        & optical_audit["entity_kind"].isin(
            ["PERSON_REFERENCE", "SAR_ONLY_C2_CANDIDATE", "FIXED_OFFSET_CONTROL"]
        )
    ].copy()
    fig, axes = plt.subplots(1, 3, figsize=(17, 5), sharey=True)
    kinds = ["PERSON_REFERENCE", "SAR_ONLY_C2_CANDIDATE", "FIXED_OFFSET_CONTROL"]
    for axis, kind in zip(axes, kinds):
        group = subset[subset["entity_kind"] == kind].set_index("run_id").reindex(RUNS)
        x = np.arange(len(RUNS))
        axis.bar(x - 0.24, group["window_250ms_shell_coverage"], width=0.24, label="true window shell", color="#27c46b")
        axis.bar(x, group["shift_minus18deg_coverage"], width=0.24, label="shift -18°", color="#46a7ff")
        axis.bar(x + 0.24, group["shift_plus18deg_coverage"], width=0.24, label="shift +18°", color="#b35cff")
        axis.set_xticks(x, RUNS, rotation=25)
        axis.set_ylim(0, 1)
        axis.set_title(kind)
        axis.grid(axis="y", alpha=0.2)
        axis.legend(fontsize=7)
    axes[0].set_ylabel("coverage fraction")
    fig.suptitle("Provisional optical azimuth shell coverage versus equal-width shifted controls")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def rotated_box_corners(annotation: dict[str, Any]) -> np.ndarray:
    width = float(annotation["width"])
    height = float(annotation["height"])
    angle = math.radians(float(annotation["rotation_deg"]))
    local = np.array(
        [
            [-width / 2.0, -height / 2.0],
            [width / 2.0, -height / 2.0],
            [width / 2.0, height / 2.0],
            [-width / 2.0, height / 2.0],
        ]
    )
    rotation = np.array(
        [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
    )
    return local @ rotation.T + np.array([float(annotation["cx"]), float(annotation["cy"])])


def select_case_specs(
    observations: pd.DataFrame, p0_local: pd.DataFrame, frame_display: pd.DataFrame
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = [
        {
            "frame_uid": "R02ZF_SARF000472",
            "target_ids": ["R02ZF_SARPERSON01", "R02ZF_SARPERSON02"],
            "reason": "R02_P01_P02_LOW_RANK_NEARBY_RESPONSE",
        },
        {
            "frame_uid": "R02ZF_SARF000482",
            "target_ids": ["R02ZF_SARPERSON02"],
            "reason": "R02_P02_CANDIDATE_MISSING_CASE",
        },
        {
            "frame_uid": "R02ZF_SARF000483",
            "target_ids": ["R02ZF_SARPERSON03", "R02ZF_SARPERSON04"],
            "reason": "R02_P03_P04_SHARED_IMAGE_RESPONSE",
        },
        {
            "frame_uid": "R03ZF_SARF000458",
            "target_ids": ["R03ZF_SARPERSON01"],
            "reason": "R03_OUTER_BOUNDARY_TRUNCATION",
        },
        {
            "frame_uid": "R03ZF_SARF000494",
            "target_ids": ["R03ZF_SARPERSON01"],
            "reason": "R03_SINGLE_FRAME_BOUNDARY_RECOVERY",
        },
        {
            "frame_uid": "R04ZF_SARF000000",
            "target_ids": ["R04ZF_SARPERSON01"],
            "reason": "R04_ISOLATED_REFERENCE_CONTROL",
        },
    ]
    references = observations[observations["entity_kind"] == "PERSON_REFERENCE"].copy()
    display_score_columns = [
        column for column in frame_display.columns if column.startswith("robust_z_")
    ]
    if display_score_columns:
        display = frame_display.copy()
        display["display_extreme_score"] = display[display_score_columns].abs().max(axis=1)
        available = display[
            display["frame_uid"].isin(references["frame_uid"].unique())
        ].sort_values("display_extreme_score", ascending=False)
        if len(available):
            frame_uid = str(available.iloc[0]["frame_uid"])
            target_ids = references[references["frame_uid"] == frame_uid]["target_id"].astype(str).tolist()
            cases.append(
                {
                    "frame_uid": frame_uid,
                    "target_ids": target_ids[:4],
                    "reason": "DISPLAY_PROXY_EXTREME_MANUAL_REFERENCE_FRAME",
                }
            )
    unreliable = p0_local[
        (p0_local["entity_kind"] == "PERSON_REFERENCE")
        & (p0_local["lag"] == 1)
        & (
            (p0_local["local_anchor_mode"] == "NEAREST8_FALLBACK")
            | ~p0_local["radial_anchor_bracket"].astype(bool)
            | ~p0_local["azimuth_anchor_bracket"].astype(bool)
        )
    ].sort_values("sigma_region_m", ascending=False)
    if len(unreliable):
        row = unreliable.iloc[0]
        cases.append(
            {
                "frame_uid": str(row["frame_uid"]),
                "target_ids": [str(row["target_id"])],
                "reason": "P0_LOCAL_ANCHOR_FALLBACK_OR_ONE_SIDED",
            }
        )
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for case in cases:
        key = (case["frame_uid"], tuple(case["target_ids"]))
        if key not in seen:
            seen.add(key)
            unique.append(case)
    return unique[:8]


def plot_case(
    p0: Any,
    p1e: Any,
    audit: Any,
    frame: dict[str, Any],
    target_ids: list[str],
    reason: str,
    observations: pd.DataFrame,
    p0_local: pd.DataFrame,
    candidates: pd.DataFrame,
    path: Path,
) -> None:
    context = build_frame_context(p0, p1e, audit, frame, need_c3=True)
    image_rgb = cv2.cvtColor(context.image_bgr, cv2.COLOR_BGR2RGB)
    frame_obs = observations[observations["frame_uid"] == frame["sar_frame_uid"]]
    refs = frame_obs[
        (frame_obs["entity_kind"] == "PERSON_REFERENCE")
        & frame_obs["target_id"].isin(target_ids)
    ]
    frame_candidates = candidates[
        (candidates["frame_uid"] == frame["sar_frame_uid"])
        & (candidates["candidate"] == PRIMARY)
    ].sort_values("rank")
    annotations = [
        item for item in frame["annotations"] if item["instance_id"] in target_ids
    ]
    if refs.empty:
        raise RuntimeError(f"no reference rows for case {frame['sar_frame_uid']} {target_ids}")
    points = refs[["x_px", "y_px"]].to_numpy(float)
    center = points.mean(axis=0)
    crop_radius = int(round(3.2 * context.px_per_m))
    x0 = max(0, int(math.floor(center[0] - crop_radius)))
    x1 = min(context.image_bgr.shape[1], int(math.ceil(center[0] + crop_radius)))
    y0 = max(0, int(math.floor(center[1] - crop_radius)))
    y1 = min(context.image_bgr.shape[0], int(math.ceil(center[1] + crop_radius)))

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    axes[0, 0].imshow(image_rgb)
    axes[0, 0].set_title("Raw SAR pseudocolor | manual references only as offline overlay")
    axes[0, 0].axis("off")
    axes[0, 1].imshow(image_rgb)
    axes[0, 1].imshow(
        np.ma.masked_where(~context.omega_single, context.c2_map),
        cmap="magma",
        vmin=0,
        vmax=1,
        alpha=0.64,
    )
    axes[0, 1].set_title("C2 S(x) over SAR_SINGLE_FRAME_OBSERVABLE")
    axes[0, 1].axis("off")
    axes[1, 0].imshow(image_rgb[y0:y1, x0:x1])
    axes[1, 0].imshow(
        np.ma.masked_where(
            ~context.omega_single[y0:y1, x0:x1], context.c2_map[y0:y1, x0:x1]
        ),
        cmap="magma",
        vmin=0,
        vmax=1,
        alpha=0.62,
    )
    axes[1, 0].set_title("Local C2 response | all local candidates, controls and references")
    axes[1, 0].axis("off")
    axes[1, 1].axis("off")

    colors = ["#00e5ff", "#ffea00", "#ff4fd8", "#7cff6b"]
    for index, annotation in enumerate(annotations):
        color = colors[index % len(colors)]
        corners = rotated_box_corners(annotation)
        for axis, offset in ((axes[0, 0], (0, 0)), (axes[0, 1], (0, 0)), (axes[1, 0], (x0, y0))):
            shifted = corners - np.array(offset)[None, :]
            closed = np.vstack([shifted, shifted[0]])
            axis.plot(closed[:, 0], closed[:, 1], color=color, linewidth=1.6)
            axis.scatter(
                [float(annotation["cx"]) - offset[0]],
                [float(annotation["cy"]) - offset[1]],
                c=color,
                marker="x",
                s=70,
                linewidths=2,
            )
            axis.text(
                float(annotation["cx"]) - offset[0] + 5,
                float(annotation["cy"]) - offset[1] - 5,
                annotation["instance_id"].split("PERSON")[-1],
                color=color,
                fontsize=8,
                weight="bold",
            )

    local_candidates = frame_candidates[
        (frame_candidates["x_px"] >= x0)
        & (frame_candidates["x_px"] < x1)
        & (frame_candidates["y_px"] >= y0)
        & (frame_candidates["y_px"] < y1)
    ]
    axes[1, 0].scatter(
        local_candidates["x_px"] - x0,
        local_candidates["y_px"] - y0,
        facecolors="none",
        edgecolors="#ffffff",
        s=22,
        linewidths=0.7,
        alpha=0.82,
    )
    for row in local_candidates.head(30).itertuples():
        axes[1, 0].text(
            float(row.x_px) - x0 + 2,
            float(row.y_px) - y0 - 2,
            str(int(row.rank)),
            color="white",
            fontsize=6,
        )
    controls = frame_obs[
        frame_obs["target_id"].isin(target_ids)
        & frame_obs["entity_kind"].isin(
            ["FIXED_OFFSET_CONTROL", "GEOMETRY_MATCHED_CONTROL", "LOCAL_COMPETING_CONTROL"]
        )
    ]
    markers = {
        "FIXED_OFFSET_CONTROL": ("s", "#ffea00"),
        "GEOMETRY_MATCHED_CONTROL": ("o", "#00e5ff"),
        "LOCAL_COMPETING_CONTROL": ("D", "#ff4fd8"),
    }
    for kind, group in controls.groupby("entity_kind"):
        marker, color = markers[kind]
        axes[1, 0].scatter(
            group["x_px"] - x0,
            group["y_px"] - y0,
            facecolors="none",
            edgecolors=color,
            marker=marker,
            s=55,
            linewidths=1.2,
            label=kind,
        )
    if len(controls):
        axes[1, 0].legend(fontsize=7, loc="best")

    text_lines = [
        f"case: {reason}",
        f"frame: {frame['sar_frame_uid']}  sync={frame.get('sync_status', '')}",
        "C2/JET are display-domain relative measures, not intrinsic RCS.",
        "shared/merge-like means candidate overlap only, not physical scattering fusion.",
        "",
    ]
    for ref in refs.itertuples():
        local = p0_local[
            (p0_local["entity_id"] == ref.entity_id) & (p0_local["lag"] == 1)
        ]
        if len(local):
            p0_row = local.iloc[0]
            p0_text = (
                f"lag1={p0_row['P0_transport_domain']} sigma={p0_row['sigma_region_m']:.3f}m "
                f"d/sigma={p0_row['transport_separability_displacement_over_sigma']:.3f} "
                f"anchors={int(p0_row['local_holdout_anchor_count'])} {p0_row['local_anchor_mode']}"
            )
        else:
            p0_text = "lag1=P0_TRANSPORT_UNAVAILABLE"
        text_lines.extend(
            [
                f"{ref.target_id}: state={ref.offline_response_state}",
                f"  range={ref.range_m:.2f}m theta={ref.azimuth_deg:.2f}° side={ref.nearest_side_boundary_distance_deg:.2f}° outer={ref.outer_range_boundary_distance_m:.2f}m",
                f"  support={ref.support_status}/{ref.support_valid_fraction:.2f} C2={ref.C2_score_at_position:.3f} pct={ref.C2_percentile_in_frame_valid_region:.3f}",
                f"  nearest candidate rank={ref.nearest_C2_candidate_rank:.0f} d={ref.nearest_C2_candidate_distance_m:.2f}m density1m={int(ref.other_C2_candidate_count_1m)}",
                f"  display={ref.display_observation_state} optical-window-shell={bool(ref.inside_optical_window_250ms_shell_union)}",
                f"  {p0_text}",
                "",
            ]
        )
    axes[1, 1].text(
        0.01,
        0.99,
        "\n".join(text_lines),
        va="top",
        ha="left",
        family="monospace",
        fontsize=8.5,
    )
    fig.suptitle(f"PERSON-SAR observation condition case | {reason}", fontsize=14)
    fig.tight_layout()
    fig.savefig(path, dpi=155)
    plt.close(fig)


def render_case_registry(
    p0: Any,
    p1e: Any,
    audit: Any,
    frame_map: dict[str, dict[str, Any]],
    observations: pd.DataFrame,
    p0_local: pd.DataFrame,
    frame_display: pd.DataFrame,
    candidates: pd.DataFrame,
) -> pd.DataFrame:
    specs = select_case_specs(observations, p0_local, frame_display)
    rows: list[dict[str, Any]] = []
    for rank, case in enumerate(specs, start=1):
        path = VIS_DIR / f"case_{rank:02d}_{case['reason']}.png"
        plot_case(
            p0,
            p1e,
            audit,
            frame_map[case["frame_uid"]],
            case["target_ids"],
            case["reason"],
            observations,
            p0_local,
            candidates,
            path,
        )
        rows.append(
            {
                "rank": rank,
                "frame_uid": case["frame_uid"],
                "target_ids": "|".join(case["target_ids"]),
                "reason": case["reason"],
                "visual_path": str(path),
            }
        )
    return pd.DataFrame(rows)


def summarize_lag_tradeoff(tradeoff: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lag, group in tradeoff.groupby("lag"):
        rows.append(
            {
                "lag": int(lag),
                "pair_count": int(len(group)),
                "comparable_pair_fraction": float(group["pair_comparable"].mean()),
                "median_transport_displacement_m": float(
                    group["transport_displacement_median_m"].median()
                ),
                "median_local_sigma_m": float(group["local_sigma_median_m"].median()),
                "median_transport_separability": float(
                    group["transport_separability_median"].median()
                ),
                "median_C2_field_retention_correct": float(
                    group["C2_field_retention_correct_pearson"].median()
                ),
                "median_C2_field_retention_zero": float(
                    group["C2_field_retention_zero_pearson"].median()
                ),
                "median_correct_minus_zero_retention": float(
                    group["C2_field_retention_correct_minus_zero"].median()
                ),
                "correct_retention_better_fraction": float(
                    (group["C2_field_retention_correct_minus_zero"] > 0).mean()
                ),
                "median_high_tail_correct_minus_zero": float(
                    group["high_tail_correct_minus_zero"].median()
                ),
                "median_display_js": float(group["display_js_divergence"].median()),
                "median_P0_core_grid_fraction": float(
                    group["P0_transport_core_grid_fraction"].median()
                ),
            }
        )
    return rows


def summarize_p0_domains(p0_local: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (run_id, lag, kind), group in p0_local.groupby(["run_id", "lag", "entity_kind"]):
        counts = Counter(group["P0_transport_domain"])
        rows.append(
            {
                "run_id": run_id,
                "lag": int(lag),
                "entity_kind": kind,
                "count": int(len(group)),
                "domain_counts": dict(sorted(counts.items())),
                "core_fraction": float((group["P0_transport_domain"] == "P0_TRANSPORT_CORE").mean()),
                "extended_fraction": float(
                    (group["P0_transport_domain"] == "P0_TRANSPORT_EXTENDED").mean()
                ),
                "unavailable_fraction": float(
                    (group["P0_transport_domain"] == "P0_TRANSPORT_UNAVAILABLE").mean()
                ),
                "median_sigma_m": float(group["sigma_region_m"].median()),
                "median_displacement_over_sigma": float(
                    group["transport_separability_displacement_over_sigma"].median()
                ),
                "nearest8_fallback_fraction": float(
                    (group["local_anchor_mode"] == "NEAREST8_FALLBACK").mean()
                ),
                "radial_bracket_fraction": float(group["radial_anchor_bracket"].mean()),
                "azimuth_bracket_fraction": float(group["azimuth_anchor_bracket"].mean()),
            }
        )
    return rows


def summarize_display_effect(tradeoff: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (lag, stratum), group in tradeoff.groupby(["lag", "display_stratum"]):
        rows.append(
            {
                "lag": int(lag),
                "display_stratum": stratum,
                "pair_count": int(len(group)),
                "median_display_js": float(group["display_js_divergence"].median()),
                "median_correct_retention": float(
                    group["C2_field_retention_correct_pearson"].median()
                ),
                "median_zero_retention": float(
                    group["C2_field_retention_zero_pearson"].median()
                ),
                "median_correct_minus_zero": float(
                    group["C2_field_retention_correct_minus_zero"].median()
                ),
                "median_C2_mae_correct": float(group["C2_field_mae_correct"].median()),
            }
        )
    return rows


def build_diagnostic_summary(
    p0: Any,
    input_checks: list[dict[str, Any]],
    observations: pd.DataFrame,
    frame_display: pd.DataFrame,
    p0_local: pd.DataFrame,
    tradeoff: pd.DataFrame,
    optical_audit: pd.DataFrame,
    condition_summary: pd.DataFrame,
    case_registry: pd.DataFrame,
) -> dict[str, Any]:
    references = observations[observations["entity_kind"] == "PERSON_REFERENCE"].copy()
    reference_state_counts = [
        {
            "run_id": run_id,
            "target_id": target_id,
            "state_counts": dict(sorted(Counter(group["offline_response_state"]).items())),
            "count": int(len(group)),
        }
        for (run_id, target_id), group in references.groupby(["run_id", "target_id"])
    ]
    r01_optical = json.loads(R01_OPTICAL_MODEL.read_text(encoding="utf-8"))
    r04_optical = json.loads(R04_OPTICAL_AUDIT.read_text(encoding="utf-8"))
    optical_reference = optical_audit[
        (optical_audit["entity_kind"] == "PERSON_REFERENCE")
        & (optical_audit["offline_response_state"] == "ALL")
    ].to_dict("records")
    lag_summary = summarize_lag_tradeoff(tradeoff)
    summary = {
        "schema": "PERSON_P1E_OBSERVATION_MODEL_DIAGNOSTIC_V1",
        "created_at": now_iso(),
        "status": "OBSERVATION_MODEL_DIAGNOSTIC_COMPLETE_NO_NEW_PASS_FAIL",
        "diagnostic_script_sha256": sha256_file(SCRIPT_PATH),
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "interpreter": r"D:\MINICONDA\envs\py311\python.exe",
        "input_hash_checks": input_checks,
        "frozen_dependency_hashes": {str(path): sha256_file(path) for path in EXPECTED_HASHES},
        "counts": {
            "observation_rows": int(len(observations)),
            "frame_display_rows": int(len(frame_display)),
            "p0_local_rows": int(len(p0_local)),
            "lag_pair_rows": int(len(tradeoff)),
            "manual_reference_rows": int(len(references)),
            "C2_candidate_rows": int(
                (observations["entity_kind"] == "SAR_ONLY_C2_CANDIDATE").sum()
            ),
            "case_count": int(len(case_registry)),
        },
        "reference_state_counts": reference_state_counts,
        "reference_state_overall": dict(
            sorted(Counter(references["offline_response_state"]).items())
        ),
        "P0_domain_summaries": summarize_p0_domains(p0_local),
        "lag_tradeoff_summaries": lag_summary,
        "display_retention_summaries": summarize_display_effect(tradeoff),
        "frame_display_state_counts_by_run": [
            {
                "run_id": run_id,
                "frame_count": int(len(group)),
                "display_state_counts": dict(
                    sorted(Counter(group["display_observation_state"]).items())
                ),
                "display_shift_fraction": float(group["display_shift"].mean()),
                "high_censor_proxy_fraction": float(
                    group["display_high_censor_proxy"].mean()
                ),
                "compressed_proxy_fraction": float(group["display_compressed_proxy"].mean()),
            }
            for run_id, group in frame_display.groupby("run_id")
        ],
        "optical_mapping_audit": {
            "R01_status": r01_optical["status"],
            "R01_leave_one_person_out_macro_mae_deg": r01_optical[
                "nominal_zero_offset_model"
            ]["leave_one_person_out_macro_mae_deg"],
            "R01_sync_decision": r01_optical["optical_query_shift_sensitivity"]["decision"],
            "R04_status": r04_optical["status"],
            "R04_nominal_zero_macro_mae_deg": r04_optical["strict_nominal_zero_held_out"][
                "macro_mae_deg"
            ],
            "R04_best_diagnostic_shift_ms_not_registered": r04_optical[
                "fixed_support_offset_diagnostic"
            ]["diagnostic_best_optical_query_shift_ms_not_registered"],
            "common_fov_formula": (
                f"theta={OPTICAL_SLOPE_DEG_PER_PX:.14f}*u{OPTICAL_INTERCEPT_DEG:+.12f}"
            ),
            "time_window_ms": OPTICAL_TIME_WINDOW_MS,
            "shifted_shell_control_deg": OPTICAL_SHELL_SHIFT_DEG,
            "reference_coverage_by_run": optical_reference,
            "runtime_status": "PROVISIONAL_SOFT_AZIMUTH_PRIOR_ONLY_NOT_FINAL_SAR_POSITION",
        },
        "condition_summary_rows": condition_summary.to_dict("records"),
        "visual_case_registry": case_registry.to_dict("records"),
        "diagnostic_questions": {
            "lag1_correct_approximately_zero_test": next(
                (item for item in lag_summary if item["lag"] == 1), None
            ),
            "lag3_geometry_response_tradeoff": next(
                (item for item in lag_summary if item["lag"] == 3), None
            ),
            "lag5_geometry_response_tradeoff": next(
                (item for item in lag_summary if item["lag"] == 5), None
            ),
        },
        "semantic_boundaries": {
            "new_PASS_or_FAIL_claimed": False,
            "P0_retuned_or_refit": False,
            "C0_C3_modified": False,
            "new_tracker_built": False,
            "reference_used_for_response_or_candidate_generation": False,
            "reference_used_for_P0_fitting": False,
            "physical_target_id_used_for_optical_shell_selection": False,
            "optical_assigned_SAR_range": False,
            "SAR_retains_final_localization_authority": True,
            "pseudocolor_brightness_interpreted_as_intrinsic_RCS": False,
            "shared_interpreted_as_physical_scattering_fusion": False,
            "all_runs_are_exposed_development_material": True,
            "SAR_boxes_created_or_moved": 0,
        },
    }
    return json_safe(summary)


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(SCRIPT_PATH).lower() or "old_work" in str(OUTPUT_DIR).lower():
        raise RuntimeError("forbidden old_work dependency")
    if not PROTOCOL_PATH.is_file():
        raise RuntimeError("missing frozen pre-run observation-model protocol")
    for path, expected in EXPECTED_HASHES.items():
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"hash mismatch {path}: expected {expected}, actual {actual}")

    p0 = load_module("person_observation_model_p0", P0_SCRIPT)
    p1e = load_module("person_observation_model_p1e", P1E_SCRIPT)
    audit = load_module("person_observation_model_candidate_audit", CANDIDATE_AUDIT_SCRIPT)
    p0.assert_workspace_scope()
    _, input_checks = p0.load_contract_and_verify()
    freeze = json.loads((P0_ROOT / "model_selection_R01.json").read_text(encoding="utf-8"))
    if sha256_file(P0_SCRIPT) != freeze["frozen"]["script_sha256"]:
        raise RuntimeError("frozen P0 script hash mismatch against R01 freeze")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    explorer = load_explorer()
    frame_map = {frame["sar_frame_uid"]: frame for frame in explorer["frames"]}
    pair_registry, _ = load_pair_registry(freeze, frame_map)
    entities, _ = build_entity_registry()
    candidates_all = pd.read_csv(CANDIDATES_CSV)
    candidates_c2 = candidates_all[candidates_all["candidate"] == PRIMARY].copy()
    optical_registry, common_fov_by_run = build_optical_shell_registry(explorer)

    entities_by_frame = {
        frame_uid: group.copy() for frame_uid, group in entities.groupby("frame_uid", sort=False)
    }
    candidates_by_frame = {
        frame_uid: group.sort_values("rank").copy()
        for frame_uid, group in candidates_c2.groupby("frame_uid", sort=False)
    }

    observation_parts: list[pd.DataFrame] = []
    p0_local_parts: list[pd.DataFrame] = []
    display_rows: list[dict[str, Any]] = []
    tradeoff_rows: list[dict[str, Any]] = []

    for run_id in RUNS:
        frames = sorted(
            [frame for frame in explorer["frames"] if frame["run_id"] == run_id],
            key=lambda item: int(item["sar_frame_index"]),
        )
        cache: dict[int, FrameContext] = {}
        for ordinal, frame in enumerate(frames, start=1):
            frame_index = int(frame["sar_frame_index"])
            context = build_frame_context(
                p0,
                p1e,
                audit,
                frame,
                need_c3=frame["sar_frame_uid"] in entities_by_frame,
            )
            display_rows.append(frame_display_stats(context))
            frame_entities = entities_by_frame.get(frame["sar_frame_uid"], pd.DataFrame())
            if not frame_entities.empty:
                frame_candidates = candidates_by_frame.get(
                    frame["sar_frame_uid"],
                    pd.DataFrame(columns=["x_px", "y_px", "score", "rank"]),
                )
                observation_parts.append(
                    compute_frame_observations(
                        context,
                        frame_entities,
                        frame_candidates,
                        optical_registry[frame["sar_frame_uid"]],
                        common_fov_by_run[run_id],
                    )
                )
            cache[frame_index] = context
            for lag in LAGS:
                source_index = frame_index - lag
                if source_index not in cache:
                    continue
                source = cache[source_index]
                key = (
                    run_id,
                    source.frame["sar_frame_uid"],
                    frame["sar_frame_uid"],
                    lag,
                )
                if key not in pair_registry:
                    continue
                pair = pair_registry[key]
                tradeoff_rows.append(compute_pair_tradeoff(p0, pair, source, context))
                source_entities = entities_by_frame.get(
                    source.frame["sar_frame_uid"], pd.DataFrame()
                )
                if not source_entities.empty:
                    p0_local_parts.append(
                        compute_local_p0_rows(
                            p0, pair, source, context, source_entities
                        )
                    )
            for old_index in list(cache):
                if old_index < frame_index - max(LAGS):
                    del cache[old_index]
            if ordinal % 20 == 0 or ordinal == len(frames):
                print(
                    f"observation diagnostic {run_id} {ordinal}/{len(frames)} {frame['sar_frame_uid']}",
                    flush=True,
                )

    observations = pd.concat(observation_parts, ignore_index=True)
    p0_local = pd.concat(p0_local_parts, ignore_index=True)
    frame_display = apply_display_flags(pd.DataFrame(display_rows), pair_registry)
    tradeoff = pd.DataFrame(tradeoff_rows)

    display_merge_columns = [
        column
        for column in frame_display.columns
        if column not in {"run_id", "frame_uid", "frame_index"}
    ]
    observations = observations.merge(
        frame_display[["frame_uid", *display_merge_columns]], on="frame_uid", how="left"
    )
    observations = pivot_p0_conditions(observations, p0_local)

    source_display = frame_display.add_prefix("source_")
    destination_display = frame_display.add_prefix("destination_")
    tradeoff = tradeoff.merge(
        source_display,
        left_on="from_frame_uid",
        right_on="source_frame_uid",
        how="left",
    ).merge(
        destination_display,
        left_on="to_frame_uid",
        right_on="destination_frame_uid",
        how="left",
    )
    tradeoff["display_jet_range_change"] = (
        tradeoff["destination_jet_p95_minus_p05"]
        - tradeoff["source_jet_p95_minus_p05"]
    )
    tradeoff["display_high_plateau_change"] = (
        tradeoff["destination_jet_high_plateau_fraction"]
        - tradeoff["source_jet_high_plateau_fraction"]
    )

    optical_audit = build_optical_shell_audit(observations)
    condition_summary = build_condition_state_summary(observations, p0_local)

    observations.to_csv(
        OUTPUT_DIR / "observation_condition_table.csv", index=False, encoding="utf-8-sig"
    )
    frame_display.to_csv(
        OUTPUT_DIR / "frame_display_condition_table.csv", index=False, encoding="utf-8-sig"
    )
    p0_local.to_csv(
        OUTPUT_DIR / "p0_local_transport_condition_table.csv",
        index=False,
        encoding="utf-8-sig",
    )
    tradeoff.to_csv(
        OUTPUT_DIR / "lag_transport_response_tradeoff.csv",
        index=False,
        encoding="utf-8-sig",
    )
    optical_audit.to_csv(
        OUTPUT_DIR / "optical_shell_audit.csv", index=False, encoding="utf-8-sig"
    )
    condition_summary.to_csv(
        OUTPUT_DIR / "condition_state_summary.csv", index=False, encoding="utf-8-sig"
    )

    plot_reference_state_map(observations, VIS_DIR / "reference_state_range_azimuth.png")
    plot_p0_reliability(p0_local, VIS_DIR / "p0_transport_displacement_vs_uncertainty.png")
    plot_lag_tradeoff(tradeoff, VIS_DIR / "lag_geometry_response_tradeoff.png")
    plot_retention_vs_display(tradeoff, VIS_DIR / "retention_vs_display_change.png")
    plot_display_timeline(frame_display, VIS_DIR / "display_condition_timeline.png")
    plot_optical_shell_audit(optical_audit, VIS_DIR / "optical_shell_shift_control.png")

    case_registry = render_case_registry(
        p0,
        p1e,
        audit,
        frame_map,
        observations,
        p0_local,
        frame_display,
        candidates_all,
    )
    case_registry.to_csv(
        OUTPUT_DIR / "case_registry.csv", index=False, encoding="utf-8-sig"
    )

    summary = build_diagnostic_summary(
        p0,
        input_checks,
        observations,
        frame_display,
        p0_local,
        tradeoff,
        optical_audit,
        condition_summary,
        case_registry,
    )
    (OUTPUT_DIR / "diagnostic_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": summary["status"],
                "counts": summary["counts"],
                "lag_tradeoff": summary["lag_tradeoff_summaries"],
                "output": str(OUTPUT_DIR),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
