#!/usr/bin/env python3
"""GT-blind candidate recall audit for the existing P1E C2/C3 response maps.

This script separates candidate existence/recall from unique single-frame
localization. Candidate peaks are extracted from the whole SAR-only S(x) map
before PERSON annotations are consulted. Annotations are used only afterwards
for offline Recall@K, fixed-offset controls, merging diagnostics, and figures.

The frozen P0 implementation, existing B0R outputs, and existing P1E outputs
are read-only dependencies. No SAR box is created, moved, or corrected.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
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
P1E_SCRIPT = TASK_DIR / "run_p1e_single_frame_position_specificity.py"
P0_OUTPUT = STUDY_OUTPUT / "p0_common_apparent_motion"
B0R_OUTPUT = STUDY_OUTPUT / "p1e_sar_only_response_interface" / "b0r_minimal"
OLD_P1E_OUTPUT = (
    STUDY_OUTPUT
    / "p1e_sar_only_response_interface"
    / "single_frame"
    / "manual_v4_physical_scale_p0_mask"
)
OUTPUT_ROOT = (
    STUDY_OUTPUT
    / "p1e_sar_only_response_interface"
    / "candidate_recall_semantic_split_v1"
)
OUTPUT_DIR = OUTPUT_ROOT / "single_frame_candidate_recall"
VIS_DIR = OUTPUT_DIR / "visualizations"
EXPLORER_PATH = (
    WORKSPACE
    / "output"
    / "person_multidimensional_response_explorer_20260823"
    / "explorer_data.js"
)

EXPECTED_P0_SHA256 = "0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8"
EXPECTED_P1E_SHA256 = "98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1"
PRIMARY_CANDIDATE = "C2_COMPACT_JET_GRADIENT_CONSENSUS"
DIAGNOSTIC_CANDIDATE = "C3_ISOTROPIC_BLOB_RIDGE_SUPPRESSED"
AUDIT_CANDIDATES = (PRIMARY_CANDIDATE, DIAGNOSTIC_CANDIDATE)
RUNS = ("R01ZF", "R02ZF", "R03ZF", "R04ZF")

# Frozen before viewing candidate recall results; see 00 protocol in OUTPUT_ROOT.
SINGLE_INNER_RANGE_EXCLUSION_M = 0.75
SUPPORT_FULL_MIN = 0.80
SUPPORT_TRUNCATED_MIN = 0.50
LOCAL_MAX_RADIUS_M = 0.30
NMS_MIN_SEPARATION_M = 0.45
CANDIDATE_SCORE_FLOOR = 1e-6
RECALL_K_VALUES = (1, 2, 3, 5)
RECALL_RADII_M = (0.30, 0.50, 0.80)
FIXED_OFFSET_M = 1.25
TEMPORAL_GATE_RECALL5_MIN = 0.60
TEMPORAL_GATE_TOP5_GAIN_MIN = 0.20
TEMPORAL_GATE_OFFSET_ADVANTAGE_MIN = 0.10
TEMPORAL_GATE_P01_OR_P02_RECALL5_MIN = 0.50


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_explorer() -> dict[str, Any]:
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


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
    return value


def support_status(fraction: float) -> str:
    if not np.isfinite(fraction) or fraction < SUPPORT_TRUNCATED_MIN:
        return "INVALID"
    if fraction < SUPPORT_FULL_MIN:
        return "TRUNCATED"
    return "FULL"


def single_frame_observation_mask(
    frame: dict[str, Any], image: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
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
        (radial >= SINGLE_INNER_RANGE_EXCLUSION_M * px_per_m)
        & (radial <= radius)
        & (theta >= float(frame["theta_low_deg"]))
        & (theta <= float(frame["theta_high_deg"]))
        & nonwhite
    )
    mask = cv2.morphologyEx(
        mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)
    ).astype(bool)
    return mask, radial, theta, px_per_m


def compute_existing_candidate_maps_for_mask(
    p1e: Any,
    frame: dict[str, Any],
    image: np.ndarray,
    mask: np.ndarray,
    radial: np.ndarray,
    theta: np.ndarray,
    px_per_m: float,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Use the existing C0-C3 primitives without changing their formulas."""
    jet, lut_distance = p1e.jet_proxy(image)
    jet[~mask] = 0.0
    diameters = sorted(
        {
            p1e.odd(px_per_m * diameter_m)
            for diameter_m in p1e.PHYSICAL_RESPONSE_DIAMETERS_M
        }
    )

    c0_raw = p1e.center_ring_response(jet, mask, diameters)
    c0 = p1e.robust_positive_scale(c0_raw, mask)

    jet_u8 = np.clip(jet * 255.0, 0, 255).astype(np.uint8)
    jet_range_rank = p1e.radial_histogram_rank(
        jet_u8,
        radial,
        mask,
        bin_px=px_per_m * p1e.RANGE_NORMALIZATION_BIN_M,
    )
    c1_raw = p1e.multiscale_tophat(jet_range_rank, mask, diameters)
    c1 = p1e.robust_positive_scale(c1_raw, mask)

    gradient = p1e.gradient_field(image, mask)
    gradient_u8 = np.clip(gradient * 255.0, 0, 255).astype(np.uint8)
    gradient_range_rank = p1e.radial_histogram_rank(
        gradient_u8,
        radial,
        mask,
        bin_px=px_per_m * p1e.RANGE_NORMALIZATION_BIN_M,
    )
    gradient_compact_raw = p1e.center_ring_response(
        gradient_range_rank, mask, diameters
    )
    gradient_compact = p1e.robust_positive_scale(gradient_compact_raw, mask)
    consensus_raw = np.sqrt(
        np.clip(c1, 0.0, 1.0) * np.clip(gradient_compact, 0.0, 1.0)
    )
    c2 = p1e.robust_positive_scale(consensus_raw, mask)
    c3 = p1e.isotropic_blob_ridge_suppressed(jet_range_rank, mask, diameters)

    maps = {
        "C0_JET_CENTER_RING": c0,
        "C1_RANGE_RANK_TOPHAT": c1,
        PRIMARY_CANDIDATE: c2,
        DIAGNOSTIC_CANDIDATE: c3,
    }
    metadata = {
        "mask": mask,
        "radial": radial,
        "theta": theta,
        "jet_proxy": jet,
        "lut_distance": lut_distance,
        "gradient": gradient,
        "diameters_px": diameters,
        "diameters_m": list(p1e.PHYSICAL_RESPONSE_DIAMETERS_M),
        "px_per_m": px_per_m,
    }
    return maps, metadata


def support_fraction_map(p1e: Any, mask: np.ndarray, radius_px: int) -> np.ndarray:
    kernel = p1e.disk_kernel(2 * radius_px + 1)
    return cv2.filter2D(mask.astype(np.float32), cv2.CV_32F, kernel) / max(
        float(kernel.sum()), 1.0
    )


def candidate_min_spacing_m(candidates: list[dict[str, Any]], px_per_m: float) -> float:
    if len(candidates) < 2:
        return math.nan
    coords = np.asarray([[row["x_px"], row["y_px"]] for row in candidates], dtype=float)
    minimum = math.inf
    for index in range(len(coords) - 1):
        distances = np.linalg.norm(coords[index + 1 :] - coords[index], axis=1)
        if len(distances):
            minimum = min(minimum, float(np.min(distances)))
    return minimum / px_per_m if np.isfinite(minimum) else math.nan


def extract_gt_blind_candidates(
    p1e: Any,
    score_map: np.ndarray,
    center_mask: np.ndarray,
    support_fraction: np.ndarray,
    px_per_m: float,
) -> list[dict[str, Any]]:
    local_radius_px = max(1, int(round(LOCAL_MAX_RADIUS_M * px_per_m)))
    local_kernel = p1e.disk_kernel(2 * local_radius_px + 1).astype(np.uint8)
    local_maximum = cv2.dilate(score_map.astype(np.float32), local_kernel)
    eligible = (
        center_mask
        & (support_fraction >= SUPPORT_TRUNCATED_MIN)
        & np.isfinite(score_map)
        & (score_map > CANDIDATE_SCORE_FLOOR)
        & (score_map >= local_maximum - 1e-7)
    )
    ys, xs = np.where(eligible)
    if not len(xs):
        return []
    scores = score_map[ys, xs]
    order = np.lexsort((xs, ys, -scores))
    separation_px = NMS_MIN_SEPARATION_M * px_per_m
    cell_size = max(separation_px, 1.0)
    grid: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)
    kept: list[dict[str, Any]] = []
    for raw_index in order:
        x = float(xs[raw_index])
        y = float(ys[raw_index])
        cell_x = int(math.floor(x / cell_size))
        cell_y = int(math.floor(y / cell_size))
        reject = False
        for grid_y in range(cell_y - 1, cell_y + 2):
            for grid_x in range(cell_x - 1, cell_x + 2):
                for other_x, other_y in grid.get((grid_x, grid_y), []):
                    if math.hypot(x - other_x, y - other_y) < separation_px:
                        reject = True
                        break
                if reject:
                    break
            if reject:
                break
        if reject:
            continue
        fraction = float(support_fraction[int(round(y)), int(round(x))])
        kept.append(
            {
                "rank": len(kept) + 1,
                "x_px": x,
                "y_px": y,
                "score": float(scores[raw_index]),
                "support_fraction": fraction,
                "support_status": support_status(fraction),
            }
        )
        grid[(cell_x, cell_y)].append((x, y))
    return kept


def sample_fraction(field: np.ndarray, point: np.ndarray) -> float:
    x = int(round(float(point[0])))
    y = int(round(float(point[1])))
    if not (0 <= x < field.shape[1] and 0 <= y < field.shape[0]):
        return 0.0
    return float(field[y, x])


def fixed_offset_points(
    p1e: Any, reference: np.ndarray, geometry: dict[str, Any], px_per_m: float
) -> dict[str, np.ndarray]:
    radial_unit, tangential_unit = p1e.point_units(reference, geometry)
    distance_px = FIXED_OFFSET_M * px_per_m
    return {
        "RADIAL_IN": reference - radial_unit * distance_px,
        "RADIAL_OUT": reference + radial_unit * distance_px,
        "TANGENTIAL_NEG": reference - tangential_unit * distance_px,
        "TANGENTIAL_POS": reference + tangential_unit * distance_px,
    }


def evaluate_point_against_candidates(
    point: np.ndarray,
    candidates: list[dict[str, Any]],
    px_per_m: float,
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    if candidates:
        coords = np.asarray([[row["x_px"], row["y_px"]] for row in candidates], dtype=float)
        distances_m = np.linalg.norm(coords - point[None, :], axis=1) / px_per_m
        nearest_index = int(np.argmin(distances_m))
        output["nearest_candidate_distance_m"] = float(distances_m[nearest_index])
        output["nearest_candidate_rank"] = int(candidates[nearest_index]["rank"])
        output["nearest_candidate_score"] = float(candidates[nearest_index]["score"])
        within_08 = np.where(distances_m <= 0.80)[0]
        output["best_rank_within_0_80m"] = (
            int(candidates[int(within_08[0])]["rank"]) if len(within_08) else math.nan
        )
        for k_value in RECALL_K_VALUES:
            top_distances = distances_m[: min(k_value, len(distances_m))]
            minimum = float(np.min(top_distances)) if len(top_distances) else math.nan
            output[f"top{k_value}_nearest_distance_m"] = minimum
            for radius_m in RECALL_RADII_M:
                key = f"recall_at_{k_value}_r_{int(round(radius_m * 100)):02d}cm"
                output[key] = bool(np.isfinite(minimum) and minimum <= radius_m)
    else:
        output.update(
            {
                "nearest_candidate_distance_m": math.nan,
                "nearest_candidate_rank": math.nan,
                "nearest_candidate_score": math.nan,
                "best_rank_within_0_80m": math.nan,
            }
        )
        for k_value in RECALL_K_VALUES:
            output[f"top{k_value}_nearest_distance_m"] = math.nan
            for radius_m in RECALL_RADII_M:
                output[f"recall_at_{k_value}_r_{int(round(radius_m * 100)):02d}cm"] = False
    return output


def summarize_group(frame: pd.DataFrame, label: dict[str, Any]) -> dict[str, Any]:
    evaluable = frame[frame["reference_support_status"] != "INVALID"].copy()
    result: dict[str, Any] = {
        **label,
        "reference_count": int(len(frame)),
        "evaluable_count": int(len(evaluable)),
        "support_status_counts": dict(sorted(Counter(frame["reference_support_status"]).items())),
        "median_nearest_candidate_distance_m": (
            float(evaluable["nearest_candidate_distance_m"].median()) if len(evaluable) else math.nan
        ),
        "median_nearest_candidate_rank": (
            float(evaluable["nearest_candidate_rank"].median()) if len(evaluable) else math.nan
        ),
    }
    for k_value in RECALL_K_VALUES:
        for radius_m in RECALL_RADII_M:
            key = f"recall_at_{k_value}_r_{int(round(radius_m * 100)):02d}cm"
            result[key] = float(evaluable[key].mean()) if len(evaluable) else math.nan
    result["failure_class_counts"] = dict(
        sorted(Counter(evaluable["candidate_failure_class"]).items())
    )
    return result


def classify_rows(metrics: pd.DataFrame) -> pd.DataFrame:
    output = metrics.copy()
    output["shared_top5_candidate_count_0_80m"] = 0
    for (_, _), indices in output.groupby(["frame_uid", "candidate"]).groups.items():
        counts: Counter[int] = Counter()
        for index in indices:
            rank = output.at[index, "best_rank_within_0_80m"]
            if np.isfinite(rank) and int(rank) <= 5:
                counts[int(rank)] += 1
        for index in indices:
            rank = output.at[index, "best_rank_within_0_80m"]
            if np.isfinite(rank) and int(rank) <= 5:
                output.at[index, "shared_top5_candidate_count_0_80m"] = counts[int(rank)]

    def classify(row: pd.Series) -> str:
        if row["reference_support_status"] == "INVALID":
            return "BOUNDARY_OR_TRUNCATION_INVALID"
        if row["reference_support_status"] == "TRUNCATED":
            return "BOUNDARY_OR_TRUNCATION"
        if int(row["shared_top5_candidate_count_0_80m"]) > 1:
            return "RESPONSE_MERGING_SUSPECTED"
        if bool(row["recall_at_1_r_80cm"]):
            return "CANDIDATE_PRESENT_TOP1"
        if bool(row["recall_at_5_r_80cm"]):
            return "CANDIDATE_RANK_COMPETITION_TOP5"
        if (
            np.isfinite(row["nearest_candidate_distance_m"])
            and float(row["nearest_candidate_distance_m"]) <= 0.80
        ):
            return "CANDIDATE_RANK_COMPETITION_BEYOND_TOP5"
        return "CANDIDATE_MISSING_OR_CURRENT_REPRESENTATION_FAILURE"

    output["candidate_failure_class"] = output.apply(classify, axis=1)
    return output


def draw_candidate_markers(
    axis: plt.Axes,
    candidates: list[dict[str, Any]],
    x_offset: float = 0.0,
    y_offset: float = 0.0,
    maximum_rank: int = 5,
) -> None:
    colors = ["#ffea00", "#00e5ff", "#ff4fd8", "#7cff6b", "#ff8c42"]
    for row in candidates[:maximum_rank]:
        x = float(row["x_px"]) - x_offset
        y = float(row["y_px"]) - y_offset
        color = colors[(int(row["rank"]) - 1) % len(colors)]
        axis.scatter([x], [y], s=70, facecolors="none", edgecolors=color, linewidths=2)
        axis.text(x + 5, y - 5, str(int(row["rank"])), color=color, fontsize=9, weight="bold")


def plot_case(
    p0: Any,
    p1e: Any,
    frame: dict[str, Any],
    annotation: dict[str, Any],
    metric_rows: pd.DataFrame,
    candidate_cache: dict[tuple[str, str], list[dict[str, Any]]],
    output_path: Path,
) -> None:
    image_path = p0.file_url_to_path(frame["sar_image_url"])
    image_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise FileNotFoundError(image_path)
    mask, radial, theta, px_per_m = single_frame_observation_mask(frame, image_bgr)
    maps, metadata = compute_existing_candidate_maps_for_mask(
        p1e, frame, image_bgr, mask, radial, theta, px_per_m
    )
    support_radius_px = max(
        1, int(round(p1e.PHYSICAL_SUPPORT_RADIUS_M * px_per_m))
    )
    evaluation_maps = p1e.build_evaluation_maps(
        maps, mask, support_radius_px, "fixed_support_mean_v2"
    )
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    reference = np.array([float(annotation["cx"]), float(annotation["cy"])])
    crop_radius = int(round(2.5 * px_per_m))
    x0 = max(0, int(round(reference[0])) - crop_radius)
    x1 = min(image_rgb.shape[1], int(round(reference[0])) + crop_radius + 1)
    y0 = max(0, int(round(reference[1])) - crop_radius)
    y1 = min(image_rgb.shape[0], int(round(reference[1])) + crop_radius + 1)

    fig, axes = plt.subplots(2, 3, figsize=(18, 10), constrained_layout=True)
    for column, candidate in enumerate(AUDIT_CANDIDATES, start=1):
        score = evaluation_maps[candidate].copy()
        score[~mask] = np.nan
        axes[0, column].imshow(score, cmap="magma", vmin=0.0, vmax=1.0)
        axes[0, column].scatter(
            [reference[0]], [reference[1]], c="red", marker="x", s=100, linewidths=2
        )
        draw_candidate_markers(
            axes[0, column], candidate_cache[(frame["sar_frame_uid"], candidate)]
        )
        axes[0, column].set_title(f"{candidate.split('_')[0]} global S(x) | top-5 GT-blind peaks")
        axes[0, column].axis("off")

    axes[0, 0].imshow(image_rgb)
    axes[0, 0].scatter(
        [reference[0]], [reference[1]], c="red", marker="x", s=100, linewidths=2
    )
    draw_candidate_markers(
        axes[0, 0], candidate_cache[(frame["sar_frame_uid"], PRIMARY_CANDIDATE)]
    )
    axes[0, 0].set_title(
        f"raw full frame | {frame['run_id']} F{int(frame['sar_frame_index'])} {annotation['instance_id']}"
    )
    axes[0, 0].axis("off")

    axes[1, 0].imshow(image_rgb[y0:y1, x0:x1])
    axes[1, 0].scatter(
        [reference[0] - x0], [reference[1] - y0], c="red", marker="x", s=100, linewidths=2
    )
    draw_candidate_markers(
        axes[1, 0],
        candidate_cache[(frame["sar_frame_uid"], PRIMARY_CANDIDATE)],
        x_offset=x0,
        y_offset=y0,
        maximum_rank=20,
    )
    axes[1, 0].set_xlim(0, x1 - x0)
    axes[1, 0].set_ylim(y1 - y0, 0)
    axes[1, 0].set_title("raw local crop | red x = offline reference")
    axes[1, 0].axis("off")

    for column, candidate in enumerate(AUDIT_CANDIDATES, start=1):
        local = evaluation_maps[candidate][y0:y1, x0:x1].copy()
        local_mask = mask[y0:y1, x0:x1]
        local[~local_mask] = np.nan
        axes[1, column].imshow(local, cmap="magma", vmin=0.0, vmax=1.0)
        axes[1, column].scatter(
            [reference[0] - x0], [reference[1] - y0], c="cyan", marker="x", s=100, linewidths=2
        )
        draw_candidate_markers(
            axes[1, column],
            candidate_cache[(frame["sar_frame_uid"], candidate)],
            x_offset=x0,
            y_offset=y0,
            maximum_rank=20,
        )
        axes[1, column].set_xlim(0, x1 - x0)
        axes[1, column].set_ylim(y1 - y0, 0)
        row = metric_rows[metric_rows["candidate"] == candidate].iloc[0]
        axes[1, column].set_title(
            f"{candidate.split('_')[0]} local | class={row['candidate_failure_class']}\n"
            f"nearest rank={row['nearest_candidate_rank']:.0f} d={row['nearest_candidate_distance_m']:.2f}m "
            f"R@1/5(.8m)={int(bool(row['recall_at_1_r_80cm']))}/{int(bool(row['recall_at_5_r_80cm']))}"
        )
        axes[1, column].axis("off")

    fig.suptitle(
        "P1E candidate recall semantic split | peaks generated from whole S(x) before GT overlay",
        fontsize=15,
        weight="bold",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=170)
    plt.close(fig)


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(SCRIPT_PATH).lower() or "old_work" in str(OUTPUT_ROOT).lower():
        raise RuntimeError("forbidden old_work dependency")
    if not (OUTPUT_ROOT / "00_CANDIDATE_RECALL_PROTOCOL_FROZEN_BEFORE_RUN.md").is_file():
        raise RuntimeError("missing pre-run frozen candidate recall protocol")

    p0 = load_module("person_p0_candidate_recall", P0_SCRIPT)
    p1e = load_module("person_p1e_candidate_recall", P1E_SCRIPT)
    p0.assert_workspace_scope()
    _, input_checks = p0.load_contract_and_verify()
    actual_p0_hash = p0.sha256_file(P0_SCRIPT)
    actual_p1e_hash = p0.sha256_file(P1E_SCRIPT)
    if actual_p0_hash != EXPECTED_P0_SHA256:
        raise RuntimeError(f"frozen P0 hash mismatch: {actual_p0_hash}")
    if actual_p1e_hash != EXPECTED_P1E_SHA256:
        raise RuntimeError(f"existing P1E hash mismatch: {actual_p1e_hash}")

    explorer = load_explorer()
    frame_map = {frame["sar_frame_uid"]: frame for frame in explorer["frames"]}
    process_frames = [
        frame
        for frame in explorer["frames"]
        if frame["run_id"] == "R02ZF"
        or any(ann["source"] == "MANUAL_NATIVE_SAR" for ann in frame["annotations"])
    ]
    old_metrics = pd.read_csv(OLD_P1E_OUTPUT / "p1e_single_frame_metrics_manual.csv")
    old_index = old_metrics.set_index(["frame_uid", "target_id", "candidate"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    candidate_rows: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []
    reference_rows: list[dict[str, Any]] = []
    control_rows: list[dict[str, Any]] = []
    candidate_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
    support_cache: dict[str, np.ndarray] = {}

    for frame_index, frame in enumerate(process_frames, start=1):
        image_path = p0.file_url_to_path(frame["sar_image_url"])
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(image_path)
        mask, radial, theta, px_per_m = single_frame_observation_mask(frame, image)
        maps, metadata = compute_existing_candidate_maps_for_mask(
            p1e, frame, image, mask, radial, theta, px_per_m
        )
        support_radius_px = max(
            1, int(round(p1e.PHYSICAL_SUPPORT_RADIUS_M * px_per_m))
        )
        support_fraction = support_fraction_map(p1e, mask, support_radius_px)
        evaluation_maps = p1e.build_evaluation_maps(
            maps, mask, support_radius_px, "fixed_support_mean_v2"
        )
        support_cache[frame["sar_frame_uid"]] = support_fraction

        for candidate in AUDIT_CANDIDATES:
            extracted = extract_gt_blind_candidates(
                p1e, evaluation_maps[candidate], mask, support_fraction, px_per_m
            )
            candidate_cache[(frame["sar_frame_uid"], candidate)] = extracted
            minimum_spacing = candidate_min_spacing_m(extracted, px_per_m)
            frame_rows.append(
                {
                    "run_id": frame["run_id"],
                    "frame_uid": frame["sar_frame_uid"],
                    "frame_index": int(frame["sar_frame_index"]),
                    "candidate": candidate,
                    "candidate_count": int(len(extracted)),
                    "candidate_min_spacing_m": minimum_spacing,
                    **{
                        f"top_{rank}_score": (
                            float(extracted[rank - 1]["score"])
                            if len(extracted) >= rank
                            else math.nan
                        )
                        for rank in range(1, 6)
                    },
                }
            )
            for row in extracted:
                point = np.array([row["x_px"], row["y_px"]])
                radial_px = float(np.linalg.norm(
                    point
                    - np.array(
                        [
                            float(frame["geometry"]["center_x_px"]),
                            float(frame["geometry"]["center_y_px"]),
                        ]
                    )
                ))
                theta_deg = math.degrees(
                    math.atan2(
                        point[0] - float(frame["geometry"]["center_x_px"]),
                        float(frame["geometry"]["center_y_px"]) - point[1],
                    )
                )
                candidate_rows.append(
                    {
                        "run_id": frame["run_id"],
                        "frame_uid": frame["sar_frame_uid"],
                        "frame_index": int(frame["sar_frame_index"]),
                        "candidate": candidate,
                        **row,
                        "range_m": radial_px / px_per_m,
                        "theta_deg": theta_deg,
                        "generated_without_annotation": True,
                    }
                )

        manual_annotations = [
            ann for ann in frame["annotations"] if ann["source"] == "MANUAL_NATIVE_SAR"
        ]
        for annotation in manual_annotations:
            reference = np.array([float(annotation["cx"]), float(annotation["cy"])])
            reference_fraction = sample_fraction(support_fraction, reference)
            reference_center_valid = bool(sample_fraction(mask.astype(np.float32), reference) >= 0.5)
            reference_status = (
                support_status(reference_fraction) if reference_center_valid else "INVALID"
            )
            offsets = fixed_offset_points(p1e, reference, frame["geometry"], px_per_m)
            for candidate in AUDIT_CANDIDATES:
                extracted = candidate_cache[(frame["sar_frame_uid"], candidate)]
                evaluation = evaluate_point_against_candidates(reference, extracted, px_per_m)
                old_key = (frame["sar_frame_uid"], annotation["instance_id"], candidate)
                old_row = old_index.loc[old_key] if old_key in old_index.index else None
                row = {
                    "run_id": frame["run_id"],
                    "frame_uid": frame["sar_frame_uid"],
                    "frame_index": int(frame["sar_frame_index"]),
                    "target_id": annotation["instance_id"],
                    "annotation_source": annotation["source"],
                    "candidate": candidate,
                    "reference_x_px": float(reference[0]),
                    "reference_y_px": float(reference[1]),
                    "reference_range_m": float(annotation["range_m"]),
                    "reference_theta_deg": float(annotation["theta_deg"]),
                    "reference_support_fraction": reference_fraction,
                    "reference_support_status": reference_status,
                    "candidate_count_frame": int(len(extracted)),
                    "old_advantage_vs_local_competing_response": (
                        float(old_row["advantage_vs_hard_background"])
                        if old_row is not None and np.isfinite(old_row["advantage_vs_hard_background"])
                        else math.nan
                    ),
                    "old_advantage_vs_local_competing_pool_p95": (
                        float(old_row["advantage_vs_hard_background_p95"])
                        if old_row is not None and np.isfinite(old_row["advantage_vs_hard_background_p95"])
                        else math.nan
                    ),
                    "old_operator_peak_offset_from_reference_center_m": (
                        float(old_row["local_peak_distance_m"])
                        if old_row is not None and np.isfinite(old_row["local_peak_distance_m"])
                        else math.nan
                    ),
                    "old_peak_offset_semantics": "S_X_LOCAL_HIGH_SCORE_OFFSET_FROM_MANUAL_BOX_GEOMETRIC_CENTER_NOT_PHYSICAL_RESOLUTION",
                    **evaluation,
                }
                reference_rows.append(row)

                for direction, point in offsets.items():
                    fraction = sample_fraction(support_fraction, point)
                    center_valid = bool(sample_fraction(mask.astype(np.float32), point) >= 0.5)
                    status = support_status(fraction) if center_valid else "INVALID"
                    control_eval = evaluate_point_against_candidates(point, extracted, px_per_m)
                    control_rows.append(
                        {
                            "run_id": frame["run_id"],
                            "frame_uid": frame["sar_frame_uid"],
                            "frame_index": int(frame["sar_frame_index"]),
                            "target_id": annotation["instance_id"],
                            "candidate": candidate,
                            "control_direction": direction,
                            "control_x_px": float(point[0]),
                            "control_y_px": float(point[1]),
                            "control_support_fraction": fraction,
                            "control_support_status": status,
                            **control_eval,
                        }
                    )

        if frame_index % 10 == 0 or frame_index == len(process_frames):
            print(
                f"processed frames {frame_index}/{len(process_frames)} | {frame['sar_frame_uid']}",
                flush=True,
            )

    candidates_df = pd.DataFrame(candidate_rows)
    frames_df = pd.DataFrame(frame_rows)
    references_df = classify_rows(pd.DataFrame(reference_rows))
    controls_df = pd.DataFrame(control_rows)

    candidates_df.to_csv(
        OUTPUT_DIR / "gt_blind_candidates_all_processed_frames.csv",
        index=False,
        encoding="utf-8-sig",
    )
    frames_df.to_csv(
        OUTPUT_DIR / "candidate_count_by_frame.csv", index=False, encoding="utf-8-sig"
    )
    references_df.to_csv(
        OUTPUT_DIR / "manual_reference_candidate_recall.csv",
        index=False,
        encoding="utf-8-sig",
    )
    controls_df.to_csv(
        OUTPUT_DIR / "fixed_offset_candidate_coverage.csv",
        index=False,
        encoding="utf-8-sig",
    )

    summaries: list[dict[str, Any]] = []
    for candidate in AUDIT_CANDIDATES:
        candidate_rows_df = references_df[references_df["candidate"] == candidate]
        summaries.append(summarize_group(candidate_rows_df, {"candidate": candidate, "group": "ALL"}))
        for run_id in RUNS:
            run_rows = candidate_rows_df[candidate_rows_df["run_id"] == run_id]
            summaries.append(
                summarize_group(run_rows, {"candidate": candidate, "group": "RUN", "run_id": run_id})
            )
        r02_rows = candidate_rows_df[candidate_rows_df["run_id"] == "R02ZF"]
        for target_id, target_rows in r02_rows.groupby("target_id"):
            summaries.append(
                summarize_group(
                    target_rows,
                    {
                        "candidate": candidate,
                        "group": "R02_TARGET",
                        "run_id": "R02ZF",
                        "target_id": target_id,
                    },
                )
            )

    r02_c2 = references_df[
        (references_df["run_id"] == "R02ZF")
        & (references_df["candidate"] == PRIMARY_CANDIDATE)
        & (references_df["reference_support_status"] != "INVALID")
    ]
    recall1 = float(r02_c2["recall_at_1_r_80cm"].mean()) if len(r02_c2) else math.nan
    recall5 = float(r02_c2["recall_at_5_r_80cm"].mean()) if len(r02_c2) else math.nan
    r02_controls = controls_df[
        (controls_df["run_id"] == "R02ZF")
        & (controls_df["candidate"] == PRIMARY_CANDIDATE)
        & (controls_df["control_support_status"] != "INVALID")
    ]
    direction_coverage = {
        direction: float(rows["recall_at_5_r_80cm"].mean())
        for direction, rows in r02_controls.groupby("control_direction")
    }
    offset_median = (
        float(np.median(list(direction_coverage.values())))
        if direction_coverage
        else math.nan
    )
    target_recall5 = {
        target_id: float(rows["recall_at_5_r_80cm"].mean())
        for target_id, rows in r02_c2.groupby("target_id")
    }
    p01_p02_max = max(
        [
            value
            for target_id, value in target_recall5.items()
            if target_id.endswith("01") or target_id.endswith("02")
        ],
        default=math.nan,
    )
    gate_checks = {
        "R02_C2_recall5_0_80m_at_least_0_60": bool(recall5 >= TEMPORAL_GATE_RECALL5_MIN),
        "R02_C2_top5_minus_top1_at_least_0_20": bool(
            recall5 - recall1 >= TEMPORAL_GATE_TOP5_GAIN_MIN
        ),
        "R02_C2_reference_minus_offset_median_at_least_0_10": bool(
            recall5 - offset_median >= TEMPORAL_GATE_OFFSET_ADVANTAGE_MIN
        ),
        "R02_P01_or_P02_recall5_at_least_0_50": bool(
            p01_p02_max >= TEMPORAL_GATE_P01_OR_P02_RECALL5_MIN
        ),
    }
    temporal_gate = bool(all(gate_checks.values()))

    # Select direct cases after metrics are complete; this only selects figures,
    # never candidates or scores.
    r02_primary = references_df[
        (references_df["run_id"] == "R02ZF")
        & (references_df["candidate"] == PRIMARY_CANDIDATE)
    ]
    selected_cases: list[tuple[str, str, str]] = []
    for target_id, target_rows in r02_primary.groupby("target_id"):
        for category in (
            "CANDIDATE_PRESENT_TOP1",
            "CANDIDATE_RANK_COMPETITION_TOP5",
            "RESPONSE_MERGING_SUSPECTED",
            "CANDIDATE_RANK_COMPETITION_BEYOND_TOP5",
            "CANDIDATE_MISSING_OR_CURRENT_REPRESENTATION_FAILURE",
        ):
            matches = target_rows[target_rows["candidate_failure_class"] == category]
            if len(matches):
                row = matches.sort_values(
                    ["nearest_candidate_rank", "nearest_candidate_distance_m"],
                    na_position="last",
                ).iloc[0]
                selected_cases.append((row["frame_uid"], target_id, category))
                break
    for frame_uid in ("R03ZF_SARF000458", "R03ZF_SARF000462", "R03ZF_SARF000494"):
        rows = references_df[
            (references_df["frame_uid"] == frame_uid)
            & (references_df["candidate"] == PRIMARY_CANDIDATE)
        ]
        if len(rows):
            selected_cases.append(
                (frame_uid, rows.iloc[0]["target_id"], rows.iloc[0]["candidate_failure_class"])
            )
    for run_id in ("R01ZF", "R04ZF"):
        rows = references_df[
            (references_df["run_id"] == run_id)
            & (references_df["candidate"] == PRIMARY_CANDIDATE)
            & references_df["recall_at_1_r_50cm"].astype(bool)
        ]
        if len(rows):
            row = rows.sort_values("nearest_candidate_rank").iloc[0]
            selected_cases.append((row["frame_uid"], row["target_id"], "TOP1_SUCCESS"))

    unique_cases: list[tuple[str, str, str]] = []
    seen_cases: set[tuple[str, str]] = set()
    for item in selected_cases:
        key = (item[0], item[1])
        if key not in seen_cases:
            seen_cases.add(key)
            unique_cases.append(item)
    unique_cases = unique_cases[:10]

    visual_registry: list[dict[str, Any]] = []
    for rank, (frame_uid, target_id, reason) in enumerate(unique_cases, start=1):
        frame = frame_map[frame_uid]
        annotation = next(
            ann for ann in frame["annotations"] if ann["instance_id"] == target_id
        )
        metric_rows = references_df[
            (references_df["frame_uid"] == frame_uid)
            & (references_df["target_id"] == target_id)
        ]
        filename = (
            f"case_{rank:02d}_{frame['run_id']}_F{int(frame['sar_frame_index']):06d}_"
            f"P{target_id[-2:]}.png"
        )
        path = VIS_DIR / filename
        plot_case(p0, p1e, frame, annotation, metric_rows, candidate_cache, path)
        visual_registry.append(
            {
                "rank": rank,
                "frame_uid": frame_uid,
                "target_id": target_id,
                "selection_reason": reason,
                "path": str(path),
            }
        )

    summary = {
        "schema": "PERSON_P1E_GT_BLIND_CANDIDATE_RECALL_AUDIT_V1",
        "created_at": p0.now_iso(),
        "status": "P1E_CANDIDATE_RECALL_AUDIT_COMPLETE",
        "output_version": "candidate_recall_semantic_split_v1",
        "processed_frame_count": int(len(process_frames)),
        "manual_reference_count": int(len(references_df) / len(AUDIT_CANDIDATES)),
        "candidate_names": list(AUDIT_CANDIDATES),
        "input_hash_checks": input_checks,
        "frozen_dependencies": {
            "P0_script_sha256": actual_p0_hash,
            "existing_P1E_script_sha256": actual_p1e_hash,
            "B0R_summary_sha256": p0.sha256_file(B0R_OUTPUT / "b0r_summary.json"),
        },
        "omega_single_v1": {
            "inner_range_exclusion_m": SINGLE_INNER_RANGE_EXCLUSION_M,
            "outer_boundary_margin_m": 0.0,
            "side_boundary_margin_deg": 0.0,
            "actual_fan_and_nonwhite_required": True,
            "support_radius_m": p1e.PHYSICAL_SUPPORT_RADIUS_M,
            "full_min_fraction": SUPPORT_FULL_MIN,
            "truncated_min_fraction": SUPPORT_TRUNCATED_MIN,
            "P0_not_comparable_does_not_imply_single_frame_invalid": True,
        },
        "candidate_extraction": {
            "generated_before_GT_evaluation": True,
            "local_max_radius_m": LOCAL_MAX_RADIUS_M,
            "nms_min_separation_m": NMS_MIN_SEPARATION_M,
            "score_floor": CANDIDATE_SCORE_FLOOR,
            "candidate_count_cap": None,
            "rank_order": "DESCENDING_SCORE_THEN_Y_X",
            "K": list(RECALL_K_VALUES),
            "radii_m": list(RECALL_RADII_M),
        },
        "semantic_corrections": {
            "hard_background_new_name": "LOCAL_COMPETING_RESPONSE_POOL",
            "old_peak_distance_meaning": "S_X_LOCAL_HIGH_SCORE_OFFSET_FROM_MANUAL_BOX_GEOMETRIC_CENTER",
            "old_peak_distance_not_direct_physical_resolution_measure": True,
            "existing_P1E_results_preserved": True,
        },
        "summaries": summaries,
        "R02_C2_temporal_gate": {
            "recall_at_1_r_0_80m": recall1,
            "recall_at_5_r_0_80m": recall5,
            "top5_minus_top1": recall5 - recall1,
            "fixed_offset_direction_recall_at_5_r_0_80m": direction_coverage,
            "fixed_offset_median_recall_at_5_r_0_80m": offset_median,
            "reference_minus_offset_median": recall5 - offset_median,
            "R02_target_recall_at_5_r_0_80m": target_recall5,
            "checks": gate_checks,
            "open_minimal_lag1_temporal_experiment": temporal_gate,
        },
        "visual_case_registry": visual_registry,
        "semantic_boundaries": {
            "annotations_used_for_candidate_generation": False,
            "physical_target_id_used_for_candidate_generation": False,
            "optical_used_for_candidate_generation": False,
            "P0_retuned": False,
            "existing_P1E_outputs_modified": False,
            "SAR_boxes_created_or_moved": 0,
            "P1_PASS_claimed": False,
            "blind_validation_claimed": False,
        },
    }
    p0.write_json(OUTPUT_DIR / "candidate_recall_summary.json", json_safe(summary))
    print(json.dumps(json_safe(summary["R02_C2_temporal_gate"]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
