#!/usr/bin/env python3
"""Matched-cost optical azimuth-shell information-gain diagnostic.

TRUE and NULL shells are generated before any manual reference is read.  NULL
selection uses only the fixed optical shell, SAR geometry, the existing
single-frame observable mask, and provisional common-FoV geometry.  Existing
GT-blind C2 candidates are then restricted to each shell.  Manual references
are used only in a final offline evaluation pass.

This additive development experiment does not modify frozen P0, B0R, C0-C3,
candidate generation, existing observation diagnostics, or SAR boxes.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
P1E_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface"
OUTPUT_DIR = P1E_ROOT / "optical_shell_information_gain_v1"
VIS_DIR = OUTPUT_DIR / "visualizations"
PROTOCOL_PATH = OUTPUT_DIR / "00_MATCHED_OPTICAL_SHELL_INFORMATION_GAIN_PROTOCOL_FROZEN_BEFORE_RUN.md"

P0_SCRIPT = TASK_DIR / "run_p0_common_apparent_motion.py"
P1E_SCRIPT = TASK_DIR / "run_p1e_single_frame_position_specificity.py"
CANDIDATE_AUDIT_SCRIPT = TASK_DIR / "run_p1e_candidate_recall_audit.py"
EXPLORER_PATH = (
    WORKSPACE / "output" / "person_multidimensional_response_explorer_20260823" / "explorer_data.js"
)
CANDIDATE_ROOT = P1E_ROOT / "candidate_recall_semantic_split_v1" / "single_frame_candidate_recall"
CANDIDATES_CSV = CANDIDATE_ROOT / "gt_blind_candidates_all_processed_frames.csv"
REFERENCES_CSV = CANDIDATE_ROOT / "manual_reference_candidate_interpretation_v2.csv"
OBS_DIAG_ROOT = P1E_ROOT / "observation_model_diagnostic_v1"
OBSERVATIONS_CSV = OBS_DIAG_ROOT / "observation_condition_table.csv"
FRAME_DISPLAY_CSV = OBS_DIAG_ROOT / "frame_display_condition_table.csv"

RUNS = ("R01ZF", "R02ZF", "R03ZF", "R04ZF")
PRIMARY_CANDIDATE = "C2_COMPACT_JET_GRADIENT_CONSENSUS"
TIME_WINDOW_MS = 250
OPTICAL_WIDTH_PX = 3840.0
OPTICAL_SLOPE_DEG_PER_PX = 0.02666536443690682
OPTICAL_INTERCEPT_DEG = -45.502258572693094
INNER_RANGE_M = 0.75
REFERENCE_RADII_M = (0.30, 0.50, 0.80)
TOP_K = (1, 2, 3, 5)
MATCH_RADIUS_M = 0.80
NULL_SHIFT_MIN_DEG = 12.0
NULL_SHIFT_MAX_DEG = 100.0
NULL_SHIFT_STEP_DEG = 0.5
NULL_SHIFT_SEPARATION_DEG = 8.0
NULL_COUNT = 3
NULL_MAX_ANGULAR_JACCARD = 0.80

EXPECTED_HASHES = {
    P0_SCRIPT: "0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8",
    P1E_SCRIPT: "98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1",
    CANDIDATE_AUDIT_SCRIPT: "84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8",
    CANDIDATES_CSV: "D2F1673A247FDB3AB1DD884F989ADC0ABE4E33A86AEFE45B5DFB4BE286FD6EC0",
    REFERENCES_CSV: "796F20EB3080C5B45CDEBBCC71584CC95C65691F056D46C4A31704A3D86E8EC7",
    OBSERVATIONS_CSV: "DE65B9705A353F0DF783E0D4A59D0274FD05547362ABE463C50C9C5469D80C21",
    FRAME_DISPLAY_CSV: "8997701F7FC34D1B52502F11B44FCEF64EC700A0FD2D734EA1AB6090A9DBAD8A",
    EXPLORER_PATH: "C39E60EB478FF7D815EFE6984D3BCF36600737E2EC3D1FF76D04020DED54EF7D",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


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


def finite_median(values: Any) -> float:
    numeric = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(float)
    numeric = numeric[np.isfinite(numeric)]
    return float(np.median(numeric)) if len(numeric) else math.nan


def bool_fraction(values: Any) -> float:
    series = pd.Series(values)
    if series.empty:
        return math.nan
    mapped = series.map(
        lambda value: (
            True
            if value is True or str(value).strip().lower() == "true"
            else False
            if value is False or str(value).strip().lower() == "false" or pd.isna(value)
            else bool(value)
        )
    )
    return float(mapped.mean())


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


def union_intervals(intervals: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    ordered = sorted((min(float(a), float(b)), max(float(a), float(b))) for a, b in intervals)
    merged: list[list[float]] = []
    for low, high in ordered:
        if not merged or low > merged[-1][1]:
            merged.append([low, high])
        else:
            merged[-1][1] = max(merged[-1][1], high)
    return [(row[0], row[1]) for row in merged]


def clip_intervals(
    intervals: Iterable[tuple[float, float]], low_bound: float, high_bound: float
) -> list[tuple[float, float]]:
    clipped = []
    for low, high in union_intervals(intervals):
        a = max(low, low_bound)
        b = min(high, high_bound)
        if b > a:
            clipped.append((a, b))
    return union_intervals(clipped)


def interval_width(intervals: Iterable[tuple[float, float]]) -> float:
    return float(sum(high - low for low, high in union_intervals(intervals)))


def interval_overlap_width(
    first: Iterable[tuple[float, float]], second: Iterable[tuple[float, float]]
) -> float:
    total = 0.0
    for low_a, high_a in union_intervals(first):
        for low_b, high_b in union_intervals(second):
            total += max(0.0, min(high_a, high_b) - max(low_a, low_b))
    return float(total)


def angular_jaccard(
    first: Iterable[tuple[float, float]], second: Iterable[tuple[float, float]]
) -> float:
    width_a = interval_width(first)
    width_b = interval_width(second)
    overlap = interval_overlap_width(first, second)
    return overlap / max(width_a + width_b - overlap, 1e-12)


def inside_intervals(theta: np.ndarray, intervals: Iterable[tuple[float, float]]) -> np.ndarray:
    output = np.zeros(len(theta), dtype=bool)
    for low, high in union_intervals(intervals):
        output |= (theta >= low) & (theta <= high)
    return output


def count_sorted_angles(sorted_theta: np.ndarray, intervals: Iterable[tuple[float, float]]) -> int:
    return int(
        sum(
            np.searchsorted(sorted_theta, high, side="right")
            - np.searchsorted(sorted_theta, low, side="left")
            for low, high in union_intervals(intervals)
        )
    )


def clipping_amounts(
    intervals: Iterable[tuple[float, float]], fan_low: float, fan_high: float
) -> tuple[float, float]:
    left = 0.0
    right = 0.0
    for low, high in union_intervals(intervals):
        if low < fan_low:
            left += max(0.0, min(high, fan_low) - low)
        if high > fan_high:
            right += max(0.0, high - max(low, fan_high))
    return float(left), float(right)


def shell_geometry_metrics(
    raw_intervals: list[tuple[float, float]],
    fan_low: float,
    fan_high: float,
    common_low: float,
    common_high: float,
    theta_valid_sorted: np.ndarray,
    omega_pixel_count: int,
    px_per_m: float,
) -> dict[str, Any]:
    effective = clip_intervals(raw_intervals, fan_low, fan_high)
    raw_width = interval_width(raw_intervals)
    width = interval_width(effective)
    area_px = count_sorted_angles(theta_valid_sorted, effective) if effective else 0
    left_clip, right_clip = clipping_amounts(raw_intervals, fan_low, fan_high)
    common_width = interval_width(clip_intervals(effective, common_low, common_high))
    if effective:
        left_gap = float(effective[0][0] - fan_low)
        right_gap = float(fan_high - effective[-1][1])
        nearest_gap = min(left_gap, right_gap)
    else:
        left_gap = right_gap = nearest_gap = math.nan
    return {
        "raw_intervals": union_intervals(raw_intervals),
        "effective_intervals": effective,
        "raw_width_deg": raw_width,
        "effective_width_deg": width,
        "effective_area_px": area_px,
        "effective_area_m2": area_px / max(px_per_m * px_per_m, 1e-12),
        "effective_area_fraction_of_omega": area_px / max(float(omega_pixel_count), 1.0),
        "left_clip_deg": left_clip,
        "right_clip_deg": right_clip,
        "total_clip_deg": left_clip + right_clip,
        "left_boundary_gap_deg": left_gap,
        "right_boundary_gap_deg": right_gap,
        "nearest_boundary_gap_deg": nearest_gap,
        "common_fov_overlap_width_deg": common_width,
        "common_fov_overlap_fraction": common_width / max(width, 1e-12) if width else math.nan,
    }


def build_optical_registry(explorer: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, tuple[float, float]]]:
    by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for frame in explorer["frames"]:
        if frame["run_id"] in RUNS:
            by_run[frame["run_id"]].append(frame)
    registry: dict[str, dict[str, Any]] = {}
    common_fov: dict[str, tuple[float, float]] = {}
    for run_id, frames in by_run.items():
        frames.sort(key=lambda row: int(row["sar_timestamp_ms"]))
        common_low = max(float(frames[0]["theta_low_deg"]), OPTICAL_INTERCEPT_DEG)
        common_high = min(
            float(frames[0]["theta_high_deg"]),
            OPTICAL_SLOPE_DEG_PER_PX * OPTICAL_WIDTH_PX + OPTICAL_INTERCEPT_DEG,
        )
        common_fov[run_id] = (common_low, common_high)
        timestamps = np.asarray([int(row["sar_timestamp_ms"]) for row in frames], dtype=int)
        for frame in frames:
            selected = np.flatnonzero(
                np.abs(timestamps - int(frame["sar_timestamp_ms"])) <= TIME_WINDOW_MS
            )
            raw: list[tuple[float, float]] = []
            raw_count = 0
            for index in selected:
                people = frames[int(index)].get("optical_persons", [])
                raw_count += len(people)
                raw.extend(
                    (float(person["theta_shell_low_deg"]), float(person["theta_shell_high_deg"]))
                    for person in people
                )
            registry[frame["sar_frame_uid"]] = {
                "window_intervals": union_intervals(raw),
                "window_source_frame_count": int(len(selected)),
                "window_shell_count_raw": int(raw_count),
                "physical_target_id_used_for_selection": False,
            }
    return registry, common_fov


def select_matched_nulls(
    true_effective: list[tuple[float, float]],
    true_metrics: dict[str, Any],
    fan_low: float,
    fan_high: float,
    common_low: float,
    common_high: float,
    theta_valid_sorted: np.ndarray,
    omega_pixel_count: int,
    px_per_m: float,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    shifts = np.arange(
        -NULL_SHIFT_MAX_DEG,
        NULL_SHIFT_MAX_DEG + 0.5 * NULL_SHIFT_STEP_DEG,
        NULL_SHIFT_STEP_DEG,
    )
    for shift in shifts:
        if abs(float(shift)) < NULL_SHIFT_MIN_DEG:
            continue
        raw = [(low + float(shift), high + float(shift)) for low, high in true_effective]
        metrics = shell_geometry_metrics(
            raw,
            fan_low,
            fan_high,
            common_low,
            common_high,
            theta_valid_sorted,
            omega_pixel_count,
            px_per_m,
        )
        if metrics["effective_width_deg"] <= 0.0 or metrics["effective_area_px"] <= 0:
            continue
        jaccard = angular_jaccard(true_effective, metrics["effective_intervals"])
        if jaccard > NULL_MAX_ANGULAR_JACCARD:
            continue
        width_error = abs(metrics["effective_width_deg"] - true_metrics["effective_width_deg"]) / max(
            true_metrics["effective_width_deg"], 1e-12
        )
        area_error = abs(metrics["effective_area_px"] - true_metrics["effective_area_px"]) / max(
            float(true_metrics["effective_area_px"]), 1.0
        )
        common_diff = abs(
            metrics["common_fov_overlap_fraction"] - true_metrics["common_fov_overlap_fraction"]
        )
        boundary_diff = abs(
            metrics["nearest_boundary_gap_deg"] - true_metrics["nearest_boundary_gap_deg"]
        ) / max(fan_high - fan_low, 1e-12)
        cost = (
            width_error
            + area_error
            + 0.5 * common_diff
            + 0.25 * boundary_diff
            + 0.05 * jaccard
        )
        candidates.append(
            {
                "shift_deg": float(shift),
                "geometry_match_cost": float(cost),
                "width_relative_error": float(width_error),
                "area_relative_error": float(area_error),
                "common_fov_overlap_fraction_diff": float(common_diff),
                "boundary_gap_normalized_diff": float(boundary_diff),
                "angular_jaccard_with_true": float(jaccard),
                **metrics,
            }
        )
    candidates.sort(key=lambda row: (row["geometry_match_cost"], abs(row["shift_deg"]), row["shift_deg"]))
    chosen: list[dict[str, Any]] = []
    for row in candidates:
        if all(abs(row["shift_deg"] - old["shift_deg"]) >= NULL_SHIFT_SEPARATION_DEG for old in chosen):
            chosen.append(row)
        if len(chosen) == NULL_COUNT:
            break
    if len(chosen) != NULL_COUNT:
        raise RuntimeError(f"could not construct {NULL_COUNT} matched nulls; found {len(chosen)}")
    for index, row in enumerate(chosen, 1):
        row["null_index"] = index
        row["geometry_match_tier"] = (
            "A_LE_5PCT"
            if row["width_relative_error"] <= 0.05
            and row["area_relative_error"] <= 0.05
            and row["common_fov_overlap_fraction_diff"] <= 0.10
            else "B_LE_10PCT"
            if row["width_relative_error"] <= 0.10
            and row["area_relative_error"] <= 0.10
            and row["common_fov_overlap_fraction_diff"] <= 0.20
            else "C_RETAINED_WITH_CONTINUOUS_MISMATCH"
        )
    return chosen


def verify_candidate_parity(candidates: pd.DataFrame, observations: pd.DataFrame) -> pd.DataFrame:
    obs = observations[observations["entity_kind"] == "SAR_ONLY_C2_CANDIDATE"].copy()
    obs["rank"] = pd.to_numeric(obs["candidate_rank_existing"], errors="raise").astype(int)
    keep = [
        "run_id",
        "frame_uid",
        "rank",
        "x_px",
        "y_px",
        "candidate_score_existing",
        "p0_transport_domain_lag1",
        "p0_sigma_m_lag1",
        "p0_local_anchor_count_lag1",
        "p0_local_anchor_mode_lag1",
        "p0_radial_bracket_lag1",
        "p0_azimuth_bracket_lag1",
        "support_status",
        "nearest_side_boundary_distance_deg",
        "outer_range_boundary_distance_m",
        "display_shift",
        "display_observation_state",
    ]
    merged = candidates.merge(obs[keep], on=["run_id", "frame_uid", "rank"], how="left", suffixes=("", "_obs"))
    if len(merged) != len(candidates) or merged["candidate_score_existing"].isna().any():
        raise RuntimeError("candidate/observation parity merge failed")
    for first, second, tol in (
        ("x_px", "x_px_obs", 1e-6),
        ("y_px", "y_px_obs", 1e-6),
        ("score", "candidate_score_existing", 1e-7),
    ):
        if float(np.max(np.abs(merged[first].to_numpy(float) - merged[second].to_numpy(float)))) > tol:
            raise RuntimeError(f"candidate parity mismatch: {first}")
    merged["candidate_id"] = merged.apply(
        lambda row: f"{row['frame_uid']}__C2R{int(row['rank']):04d}", axis=1
    )
    return merged


def verify_reference_parity(references: pd.DataFrame, manual_references: pd.DataFrame) -> None:
    manual = manual_references[manual_references["candidate"] == PRIMARY_CANDIDATE].copy()
    keys = ["run_id", "frame_uid", "frame_index", "target_id"]
    if len(manual) != len(references):
        raise RuntimeError(
            f"reference parity row mismatch: observation={len(references)} manual_C2={len(manual)}"
        )
    merged = references.merge(
        manual[
            keys
            + [
                "reference_x_px",
                "reference_y_px",
                "reference_range_m",
                "reference_theta_deg",
            ]
        ],
        on=keys,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        raise RuntimeError("reference parity key mismatch")
    for first, second, tolerance in (
        ("x_px", "reference_x_px", 1e-6),
        ("y_px", "reference_y_px", 1e-6),
        ("range_m", "reference_range_m", 1e-6),
        ("azimuth_deg", "reference_theta_deg", 1e-6),
    ):
        difference = np.abs(merged[first].to_numpy(float) - merged[second].to_numpy(float))
        if len(difference) and float(np.nanmax(difference)) > tolerance:
            raise RuntimeError(f"reference parity mismatch: {first}")


def build_shell_candidates(
    shell_definitions: pd.DataFrame, candidates: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidate_parts: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []
    full_counts = candidates.groupby("frame_uid").size().to_dict()
    candidate_groups = {uid: group.copy() for uid, group in candidates.groupby("frame_uid", sort=False)}
    for shell in shell_definitions.itertuples(index=False):
        frame_candidates = candidate_groups.get(shell.frame_uid, pd.DataFrame(columns=candidates.columns))
        intervals = json.loads(shell.effective_intervals_json)
        intervals = [(float(low), float(high)) for low, high in intervals]
        if len(frame_candidates):
            selected = inside_intervals(frame_candidates["theta_deg"].to_numpy(float), intervals)
            subset = frame_candidates.loc[selected].copy()
            subset = subset.sort_values(["score", "rank"], ascending=[False, True]).reset_index(drop=True)
            subset["shell_local_rank"] = np.arange(1, len(subset) + 1, dtype=int)
            subset["shell_local_percentile"] = (
                1.0
                if len(subset) <= 1
                else 1.0 - (subset["shell_local_rank"] - 1) / float(len(subset) - 1)
            )
            subset["shell_id"] = shell.shell_id
            subset["shell_kind"] = shell.shell_kind
            subset["null_index"] = shell.null_index
            subset["shift_deg"] = shell.shift_deg
            candidate_parts.append(subset)
        else:
            subset = pd.DataFrame(columns=candidates.columns)
        count = int(len(subset))
        domain_counts = Counter(subset.get("p0_transport_domain_lag1", pd.Series(dtype=str)).fillna("P0_UNAVAILABLE_NOT_RECORDED"))
        metric_rows.append(
            {
                "shell_id": shell.shell_id,
                "shell_kind": shell.shell_kind,
                "null_index": shell.null_index,
                "shift_deg": shell.shift_deg,
                "run_id": shell.run_id,
                "frame_uid": shell.frame_uid,
                "frame_index": shell.frame_index,
                "candidate_count_shell": count,
                "candidate_count_full_fan": int(full_counts.get(shell.frame_uid, 0)),
                "candidate_burden_ratio": count / max(float(full_counts.get(shell.frame_uid, 0)), 1.0),
                "candidate_density_per_m2": count / max(float(shell.effective_area_m2), 1e-12),
                "candidate_density_per_degree": count / max(float(shell.effective_width_deg), 1e-12),
                "candidate_score_median": float(subset["score"].median()) if count else math.nan,
                "candidate_score_max": float(subset["score"].max()) if count else math.nan,
                "p0_core_fraction": domain_counts["P0_TRANSPORT_CORE"] / max(float(count), 1.0),
                "p0_extended_fraction": domain_counts["P0_TRANSPORT_EXTENDED"] / max(float(count), 1.0),
                "p0_unavailable_fraction": (
                    count
                    - domain_counts["P0_TRANSPORT_CORE"]
                    - domain_counts["P0_TRANSPORT_EXTENDED"]
                )
                / max(float(count), 1.0),
                "p0_sigma_median_m": finite_median(subset.get("p0_sigma_m_lag1")) if count else math.nan,
                "p0_nearest8_fallback_fraction": bool_fraction(
                    subset.get("p0_local_anchor_mode_lag1", pd.Series(dtype=str)) == "NEAREST8_FALLBACK"
                )
                if count
                else math.nan,
                "p0_radial_bracket_fraction": bool_fraction(
                    subset.get("p0_radial_bracket_lag1", pd.Series(dtype=bool))
                )
                if count
                else math.nan,
                "p0_azimuth_bracket_fraction": bool_fraction(
                    subset.get("p0_azimuth_bracket_lag1", pd.Series(dtype=bool))
                )
                if count
                else math.nan,
                "display_shift": bool(shell.display_shift),
                "display_observation_state": shell.display_observation_state,
                "geometry_match_tier": shell.geometry_match_tier,
                "geometry_match_cost": shell.geometry_match_cost,
            }
        )
    shell_candidates = pd.concat(candidate_parts, ignore_index=True) if candidate_parts else pd.DataFrame()
    return shell_candidates, pd.DataFrame(metric_rows)


def offline_reference_evaluation(
    shell_definitions: pd.DataFrame,
    shell_candidates: pd.DataFrame,
    full_candidates: pd.DataFrame,
    references: pd.DataFrame,
    px_per_m_by_frame: dict[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    shell_groups = {
        shell_id: group.sort_values("shell_local_rank").copy()
        for shell_id, group in shell_candidates.groupby("shell_id", sort=False)
    }
    full_groups = {uid: group.sort_values("rank").copy() for uid, group in full_candidates.groupby("frame_uid", sort=False)}
    ref_groups = {uid: group.copy() for uid, group in references.groupby("frame_uid", sort=False)}
    evaluation_rows: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []

    for frame_uid, frame_shells in shell_definitions.groupby("frame_uid", sort=False):
        refs = ref_groups.get(frame_uid)
        if refs is None or refs.empty:
            continue
        refs = refs.reset_index(drop=True)
        ref_xy = refs[["x_px", "y_px"]].to_numpy(float)
        full = full_groups.get(frame_uid, pd.DataFrame(columns=full_candidates.columns)).reset_index(drop=True)
        full_xy = full[["x_px", "y_px"]].to_numpy(float) if len(full) else np.empty((0, 2))
        ppm = float(px_per_m_by_frame[frame_uid])
        full_dist = (
            np.linalg.norm(ref_xy[:, None, :] - full_xy[None, :, :], axis=2) / ppm
            if len(full)
            else np.empty((len(refs), 0))
        )
        for shell in frame_shells.itertuples(index=False):
            candidates = shell_groups.get(shell.shell_id, pd.DataFrame(columns=shell_candidates.columns)).reset_index(drop=True)
            cand_xy = candidates[["x_px", "y_px"]].to_numpy(float) if len(candidates) else np.empty((0, 2))
            distances = (
                np.linalg.norm(ref_xy[:, None, :] - cand_xy[None, :, :], axis=2) / ppm
                if len(candidates)
                else np.empty((len(refs), 0))
            )
            assignment: dict[int, tuple[int, float]] = {}
            if len(candidates):
                assignment_cost = np.where(distances <= MATCH_RADIUS_M, distances, 1e6)
                rows, cols = linear_sum_assignment(assignment_cost)
                for row_index, col_index in zip(rows, cols):
                    if distances[row_index, col_index] <= MATCH_RADIUS_M:
                        assignment[int(row_index)] = (int(col_index), float(distances[row_index, col_index]))
                candidate_reference_count = np.sum(distances <= MATCH_RADIUS_M, axis=0)
            else:
                candidate_reference_count = np.array([], dtype=int)
            intervals = [(float(a), float(b)) for a, b in json.loads(shell.effective_intervals_json)]
            state_counts: Counter[str] = Counter()
            for index, ref in refs.iterrows():
                theta = float(ref["azimuth_deg"])
                reference_inside = bool(inside_intervals(np.asarray([theta]), intervals)[0])
                if len(candidates):
                    nearest_index = int(np.argmin(distances[index]))
                    nearest_distance = float(distances[index, nearest_index])
                    nearest = candidates.iloc[nearest_index]
                    within = np.flatnonzero(distances[index] <= MATCH_RADIUS_M)
                else:
                    nearest_index = -1
                    nearest_distance = math.nan
                    nearest = None
                    within = np.array([], dtype=int)
                if len(within):
                    best_index = int(within[np.argmin(candidates.iloc[within]["shell_local_rank"].to_numpy(int))])
                    best = candidates.iloc[best_index]
                    best_reference_count = int(candidate_reference_count[best_index])
                    shared_any = bool(np.any(candidate_reference_count[within] > 1))
                else:
                    best_index = -1
                    best = None
                    best_reference_count = 0
                    shared_any = False

                full_within = np.flatnonzero(full_dist[index] <= MATCH_RADIUS_M) if len(full) else np.array([], dtype=int)
                if len(full_within):
                    full_best_index = int(full_within[np.argmin(full.iloc[full_within]["rank"].to_numpy(int))])
                    full_best = full.iloc[full_best_index]
                    full_best_id = str(full_best["candidate_id"])
                    retained_rows = candidates[candidates["candidate_id"] == full_best_id]
                    full_best_retained = bool(len(retained_rows))
                    retained_local_rank = int(retained_rows.iloc[0]["shell_local_rank"]) if full_best_retained else math.nan
                else:
                    full_best = None
                    full_best_id = ""
                    full_best_retained = False
                    retained_local_rank = math.nan

                if not reference_inside:
                    state = "REFERENCE_OUTSIDE_SHELL"
                elif best is None:
                    state = "CANDIDATE_MISSING_WITHIN_0P8M"
                elif shared_any:
                    state = "SHARED_IMAGE_RESPONSE"
                elif int(best["shell_local_rank"]) == 1:
                    state = "TOP1_PRESENT"
                elif int(best["shell_local_rank"]) <= 5:
                    state = "RANK_COMPETITION_TOP5"
                else:
                    state = "LOW_RANK_BEYOND_TOP5"
                state_counts[state] += 1

                row = {
                    "shell_id": shell.shell_id,
                    "shell_kind": shell.shell_kind,
                    "null_index": shell.null_index,
                    "shift_deg": shell.shift_deg,
                    "run_id": shell.run_id,
                    "frame_uid": frame_uid,
                    "frame_index": shell.frame_index,
                    "target_id": ref["target_id"],
                    "reference_entity_id": ref["entity_id"],
                    "reference_inside_shell": reference_inside,
                    "reference_C2_score": ref["C2_score_at_position"],
                    "reference_C2_percentile": ref["C2_percentile_in_frame_valid_region"],
                    "reference_nearest_C2_candidate_distance_m_full_fan": ref[
                        "nearest_C2_candidate_distance_m"
                    ],
                    "reference_nearest_C2_candidate_rank_full_fan": ref["nearest_C2_candidate_rank"],
                    "reference_C2_candidate_pool_count_full_fan": ref["C2_candidate_pool_count"],
                    "reference_support_status": ref["support_status"],
                    "reference_support_valid_fraction": ref["support_valid_fraction"],
                    "reference_inside_omega_single_center": bool(ref["inside_omega_single_center"]),
                    "reference_nearest_side_boundary_distance_deg": ref[
                        "nearest_side_boundary_distance_deg"
                    ],
                    "reference_outer_range_boundary_distance_m": ref[
                        "outer_range_boundary_distance_m"
                    ],
                    "reference_multimodal_common_fov_status": ref["multimodal_common_fov_status"],
                    "reference_global_offline_state": ref["offline_response_state"],
                    "candidate_count_shell": int(len(candidates)),
                    "candidate_count_full_fan": int(len(full)),
                    "candidate_burden_ratio": len(candidates) / max(float(len(full)), 1.0),
                    "nearest_candidate_distance_m": nearest_distance,
                    "nearest_candidate_global_rank": int(nearest["rank"]) if nearest is not None else math.nan,
                    "nearest_candidate_local_rank": int(nearest["shell_local_rank"]) if nearest is not None else math.nan,
                    "candidate_present_within_0p8m": bool(best is not None),
                    "best_candidate_id_within_0p8m": str(best["candidate_id"]) if best is not None else "",
                    "best_candidate_global_rank_within_0p8m": int(best["rank"]) if best is not None else math.nan,
                    "best_candidate_shell_local_rank_within_0p8m": int(best["shell_local_rank"]) if best is not None else math.nan,
                    "best_candidate_shell_local_percentile_within_0p8m": float(best["shell_local_percentile"]) if best is not None else math.nan,
                    "full_fan_best_candidate_id_within_0p8m": full_best_id,
                    "full_fan_best_candidate_global_rank_within_0p8m": int(full_best["rank"]) if full_best is not None else math.nan,
                    "full_fan_best_candidate_retained": full_best_retained,
                    "full_fan_best_candidate_shell_local_rank": retained_local_rank,
                    "rank_reduction_global_to_shell": (
                        int(best["rank"]) - int(best["shell_local_rank"]) if best is not None else math.nan
                    ),
                    "same_candidate_rank_reduction_global_to_shell": (
                        int(full_best["rank"]) - int(retained_local_rank)
                        if full_best is not None and full_best_retained
                        else math.nan
                    ),
                    "one_to_one_matched_0p8m": index in assignment,
                    "one_to_one_matched_0p8m_and_reference_inside_shell": bool(
                        reference_inside and index in assignment
                    ),
                    "one_to_one_matched_candidate_id": (
                        str(candidates.iloc[assignment[index][0]]["candidate_id"]) if index in assignment else ""
                    ),
                    "one_to_one_distance_m": assignment[index][1] if index in assignment else math.nan,
                    "shared_any_candidate_within_0p8m": shared_any,
                    "shared_best_candidate_reference_count": best_reference_count,
                    "shell_offline_state": state,
                    "p0_transport_domain_lag1": ref["p0_transport_domain_lag1"],
                    "p0_sigma_m_lag1": ref["p0_sigma_m_lag1"],
                    "p0_local_anchor_count_lag1": ref["p0_local_anchor_count_lag1"],
                    "p0_local_anchor_mode_lag1": ref["p0_local_anchor_mode_lag1"],
                    "p0_radial_bracket_lag1": ref["p0_radial_bracket_lag1"],
                    "p0_azimuth_bracket_lag1": ref["p0_azimuth_bracket_lag1"],
                    "display_shift": bool(ref["display_shift"]),
                    "display_observation_state": ref["display_observation_state"],
                    "max_adjacent_lag1_display_js": ref["max_adjacent_lag1_display_js"],
                    "geometry_match_tier": shell.geometry_match_tier,
                    "geometry_match_cost": shell.geometry_match_cost,
                }
                for k in TOP_K:
                    for radius in REFERENCE_RADII_M:
                        key = f"recall_at_{k}_r_{int(round(radius * 100)):02d}cm"
                        row[key] = bool(
                            len(candidates)
                            and np.any(distances[index, : min(k, len(candidates))] <= radius)
                        )
                evaluation_rows.append(row)
            frame_rows.append(
                {
                    "shell_id": shell.shell_id,
                    "shell_kind": shell.shell_kind,
                    "null_index": shell.null_index,
                    "run_id": shell.run_id,
                    "frame_uid": frame_uid,
                    "frame_index": shell.frame_index,
                    "reference_count": int(len(refs)),
                    "reference_inside_fraction": float(
                        np.mean(
                            [
                                inside_intervals(np.asarray([float(theta)]), intervals)[0]
                                for theta in refs["azimuth_deg"]
                            ]
                        )
                    ),
                    "one_to_one_matched_count_0p8m": int(len(assignment)),
                    "one_to_one_coverage_0p8m": len(assignment) / max(float(len(refs)), 1.0),
                    "one_to_one_inside_shell_count_0p8m": int(
                        sum(
                            int(index in assignment)
                            and bool(
                                inside_intervals(
                                    np.asarray([float(refs.iloc[index]["azimuth_deg"])]), intervals
                                )[0]
                            )
                            for index in range(len(refs))
                        )
                    ),
                    "state_counts_json": json.dumps(dict(state_counts), ensure_ascii=False, sort_keys=True),
                }
            )
    return pd.DataFrame(evaluation_rows), pd.DataFrame(frame_rows)


def build_true_vs_null_comparison(evaluation: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, group in evaluation.groupby(["run_id", "frame_uid", "frame_index", "target_id"], sort=False):
        true_rows = group[group["shell_kind"] == "TRUE"]
        null_rows = group[group["shell_kind"] == "MATCHED_NULL"]
        if len(true_rows) != 1 or len(null_rows) != NULL_COUNT:
            continue
        true = true_rows.iloc[0]
        null_rank = pd.to_numeric(null_rows["best_candidate_shell_local_rank_within_0p8m"], errors="coerce")
        true_rank = float(true["best_candidate_shell_local_rank_within_0p8m"])
        finite_null_rank = null_rank[np.isfinite(null_rank)]
        null_state_counts = Counter(null_rows["shell_offline_state"])
        row = {
            "run_id": keys[0],
            "frame_uid": keys[1],
            "frame_index": keys[2],
            "target_id": keys[3],
            "true_reference_inside": bool(true["reference_inside_shell"]),
            "null_reference_inside_mean": bool_fraction(null_rows["reference_inside_shell"]),
            "true_candidate_present_0p8m": bool(true["candidate_present_within_0p8m"]),
            "null_candidate_present_0p8m_mean": bool_fraction(
                null_rows["candidate_present_within_0p8m"]
            ),
            "true_full_best_candidate_retained": bool(true["full_fan_best_candidate_retained"]),
            "null_full_best_candidate_retained_mean": bool_fraction(
                null_rows["full_fan_best_candidate_retained"]
            ),
            "global_best_rank_0p8m": true["full_fan_best_candidate_global_rank_within_0p8m"],
            "true_shell_local_rank_0p8m": true_rank,
            "null_shell_local_rank_median_0p8m": finite_median(finite_null_rank),
            "null_shell_local_rank_available_fraction": len(finite_null_rank) / float(NULL_COUNT),
            "rank_advantage_true_vs_null_median": (
                finite_median(finite_null_rank) - true_rank
                if np.isfinite(true_rank) and len(finite_null_rank)
                else math.nan
            ),
            "true_rank_better_than_null_fraction": (
                float(np.mean(true_rank < finite_null_rank.to_numpy(float)))
                if np.isfinite(true_rank) and len(finite_null_rank)
                else math.nan
            ),
            "true_candidate_burden": float(true["candidate_burden_ratio"]),
            "null_candidate_burden_median": finite_median(null_rows["candidate_burden_ratio"]),
            "true_one_to_one_matched": bool(true["one_to_one_matched_0p8m"]),
            "null_one_to_one_matched_mean": bool_fraction(null_rows["one_to_one_matched_0p8m"]),
            "true_one_to_one_matched_and_inside": bool(
                true["one_to_one_matched_0p8m_and_reference_inside_shell"]
            ),
            "null_one_to_one_matched_and_inside_mean": bool_fraction(
                null_rows["one_to_one_matched_0p8m_and_reference_inside_shell"]
            ),
            "true_shared": bool(true["shared_any_candidate_within_0p8m"]),
            "null_shared_mean": bool_fraction(null_rows["shared_any_candidate_within_0p8m"]),
            "true_shell_state": true["shell_offline_state"],
            "null_state_counts_json": json.dumps(dict(null_state_counts), ensure_ascii=False, sort_keys=True),
            "reference_C2_percentile": true["reference_C2_percentile"],
            "reference_support_status": true["reference_support_status"],
            "reference_support_valid_fraction": true["reference_support_valid_fraction"],
            "reference_nearest_side_boundary_distance_deg": true[
                "reference_nearest_side_boundary_distance_deg"
            ],
            "reference_outer_range_boundary_distance_m": true[
                "reference_outer_range_boundary_distance_m"
            ],
            "reference_multimodal_common_fov_status": true[
                "reference_multimodal_common_fov_status"
            ],
            "p0_transport_domain_lag1": true["p0_transport_domain_lag1"],
            "p0_sigma_m_lag1": true["p0_sigma_m_lag1"],
            "p0_local_anchor_count_lag1": true["p0_local_anchor_count_lag1"],
            "p0_local_anchor_mode_lag1": true["p0_local_anchor_mode_lag1"],
            "p0_radial_bracket_lag1": true["p0_radial_bracket_lag1"],
            "p0_azimuth_bracket_lag1": true["p0_azimuth_bracket_lag1"],
            "display_shift": bool(true["display_shift"]),
            "display_observation_state": true["display_observation_state"],
            "max_adjacent_lag1_display_js": true["max_adjacent_lag1_display_js"],
        }
        for k in TOP_K:
            for radius in REFERENCE_RADII_M:
                name = f"recall_at_{k}_r_{int(round(radius * 100)):02d}cm"
                row[f"true_{name}"] = bool(true[name])
                row[f"null_{name}_mean"] = bool_fraction(null_rows[name])
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_by_run_target(comparison: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (run_id, target_id), group in comparison.groupby(["run_id", "target_id"], sort=False):
        true_rank = pd.to_numeric(group["true_shell_local_rank_0p8m"], errors="coerce")
        null_rank = pd.to_numeric(group["null_shell_local_rank_median_0p8m"], errors="coerce")
        rows.append(
            {
                "run_id": run_id,
                "target_id": target_id,
                "reference_rows": int(len(group)),
                "true_reference_coverage": bool_fraction(group["true_reference_inside"]),
                "null_reference_coverage_mean": float(group["null_reference_inside_mean"].mean()),
                "true_candidate_presence_0p8m": bool_fraction(group["true_candidate_present_0p8m"]),
                "null_candidate_presence_0p8m_mean": float(
                    group["null_candidate_present_0p8m_mean"].mean()
                ),
                "true_full_best_retention": bool_fraction(group["true_full_best_candidate_retained"]),
                "null_full_best_retention_mean": float(
                    group["null_full_best_candidate_retained_mean"].mean()
                ),
                "global_best_rank_median": finite_median(group["global_best_rank_0p8m"]),
                "true_shell_local_rank_median": finite_median(true_rank),
                "null_shell_local_rank_median": finite_median(null_rank),
                "rank_advantage_true_vs_null_median": finite_median(
                    group["rank_advantage_true_vs_null_median"]
                ),
                "true_candidate_burden_mean": float(group["true_candidate_burden"].mean()),
                "null_candidate_burden_median_mean": float(group["null_candidate_burden_median"].mean()),
                "true_one_to_one_coverage": bool_fraction(group["true_one_to_one_matched"]),
                "null_one_to_one_coverage_mean": float(group["null_one_to_one_matched_mean"].mean()),
                "true_shared_fraction": bool_fraction(group["true_shared"]),
                "null_shared_mean": float(group["null_shared_mean"].mean()),
            }
        )
    return pd.DataFrame(rows)


def paired_shell_frame_metrics(shell_metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (run_id, frame_uid, frame_index), group in shell_metrics.groupby(
        ["run_id", "frame_uid", "frame_index"], sort=False
    ):
        true_rows = group[group["shell_kind"] == "TRUE"]
        null_rows = group[group["shell_kind"] == "MATCHED_NULL"]
        if len(true_rows) != 1 or len(null_rows) != NULL_COUNT:
            continue
        true = true_rows.iloc[0]
        rows.append(
            {
                "run_id": run_id,
                "frame_uid": frame_uid,
                "frame_index": frame_index,
                "candidate_count_full_fan": int(true["candidate_count_full_fan"]),
                "true_candidate_count": int(true["candidate_count_shell"]),
                "null_candidate_count_median": finite_median(null_rows["candidate_count_shell"]),
                "true_candidate_burden": float(true["candidate_burden_ratio"]),
                "null_candidate_burden_median": finite_median(null_rows["candidate_burden_ratio"]),
                "true_candidate_density_per_m2": float(true["candidate_density_per_m2"]),
                "null_candidate_density_per_m2_median": finite_median(
                    null_rows["candidate_density_per_m2"]
                ),
                "true_p0_core_fraction": float(true["p0_core_fraction"]),
                "null_p0_core_fraction_median": finite_median(null_rows["p0_core_fraction"]),
                "true_p0_fallback_fraction": float(true["p0_nearest8_fallback_fraction"]),
                "null_p0_fallback_fraction_median": finite_median(
                    null_rows["p0_nearest8_fallback_fraction"]
                ),
                "display_shift": bool(true["display_shift"]),
                "display_observation_state": true["display_observation_state"],
            }
        )
    return pd.DataFrame(rows)


def scoped_groups(data: pd.DataFrame) -> Iterable[tuple[str, str, pd.DataFrame]]:
    yield "OVERALL", "ALL", data
    for run_id, group in data.groupby("run_id", sort=False):
        yield "RUN", str(run_id), group
    if "target_id" in data.columns:
        for (run_id, target_id), group in data.groupby(["run_id", "target_id"], sort=False):
            yield "RUN_TARGET", f"{run_id}/{target_id}", group


def build_reference_optical_prior_applicability(
    references: pd.DataFrame,
    shell_definitions: pd.DataFrame,
    no_shell: pd.DataFrame,
    evaluation: pd.DataFrame,
) -> pd.DataFrame:
    true_definitions = {
        str(row.frame_uid): row
        for row in shell_definitions[shell_definitions["shell_kind"] == "TRUE"].itertuples(index=False)
    }
    true_evaluation = {
        (str(row.frame_uid), str(row.reference_entity_id)): row
        for row in evaluation[evaluation["shell_kind"] == "TRUE"].itertuples(index=False)
    }
    no_shell_reason = {
        str(row.frame_uid): str(row.reason) for row in no_shell.itertuples(index=False)
    }
    rows: list[dict[str, Any]] = []
    for ref in references.itertuples(index=False):
        frame_uid = str(ref.frame_uid)
        reference_id = str(ref.entity_id)
        shell = true_definitions.get(frame_uid)
        result = true_evaluation.get((frame_uid, reference_id))
        available = shell is not None and result is not None
        inside = bool(result.reference_inside_shell) if available else False
        if not available:
            status = "OPTICAL_PRIOR_UNAVAILABLE"
        elif inside:
            status = "OPTICAL_PRIOR_AVAILABLE_REFERENCE_INSIDE_TRUE_SHELL"
        else:
            status = "OPTICAL_PRIOR_AVAILABLE_REFERENCE_OUTSIDE_TRUE_SHELL"
        row: dict[str, Any] = {
            "run_id": ref.run_id,
            "frame_uid": frame_uid,
            "frame_index": int(ref.frame_index),
            "target_id": ref.target_id,
            "reference_entity_id": reference_id,
            "optical_prior_status": status,
            "optical_prior_available": available,
            "optical_prior_unavailable": not available,
            "optical_prior_unavailable_reason": "" if available else no_shell_reason.get(frame_uid, "NO_TRUE_SHELL"),
            "reference_inside_true_shell": inside,
            "candidate_present_within_0p8m": bool(result.candidate_present_within_0p8m)
            if available
            else False,
            "full_fan_best_candidate_retained": bool(result.full_fan_best_candidate_retained)
            if available
            else False,
            "one_to_one_matched_0p8m": bool(result.one_to_one_matched_0p8m)
            if available
            else False,
            "one_to_one_matched_0p8m_and_reference_inside_shell": bool(
                result.one_to_one_matched_0p8m_and_reference_inside_shell
            )
            if available
            else False,
            "shell_offline_state": result.shell_offline_state if available else "OPTICAL_PRIOR_UNAVAILABLE",
            "reference_C2_score": float(ref.C2_score_at_position),
            "reference_C2_percentile": float(ref.C2_percentile_in_frame_valid_region),
            "reference_global_offline_state": ref.offline_response_state,
            "reference_support_status": ref.support_status,
            "reference_support_valid_fraction": float(ref.support_valid_fraction),
            "p0_transport_domain_lag1": ref.p0_transport_domain_lag1,
            "p0_sigma_m_lag1": ref.p0_sigma_m_lag1,
            "display_shift": bool(ref.display_shift),
            "display_observation_state": ref.display_observation_state,
            "true_shell_effective_width_deg": float(shell.effective_width_deg) if available else math.nan,
            "true_shell_effective_area_m2": float(shell.effective_area_m2) if available else math.nan,
            "true_shell_total_clip_deg": float(shell.total_clip_deg) if available else math.nan,
            "true_shell_common_fov_overlap_fraction": float(shell.common_fov_overlap_fraction)
            if available
            else math.nan,
            "candidate_count_shell": int(result.candidate_count_shell) if available else 0,
            "candidate_count_full_fan": int(result.candidate_count_full_fan) if available else 0,
            "candidate_burden_ratio": float(result.candidate_burden_ratio) if available else math.nan,
            "global_best_rank_0p8m": result.full_fan_best_candidate_global_rank_within_0p8m
            if available
            else math.nan,
            "true_shell_local_rank_0p8m": result.best_candidate_shell_local_rank_within_0p8m
            if available
            else math.nan,
            "same_candidate_rank_reduction_global_to_shell": result.same_candidate_rank_reduction_global_to_shell
            if available
            else math.nan,
        }
        for k in TOP_K:
            for radius in REFERENCE_RADII_M:
                name = f"recall_at_{k}_r_{int(round(radius * 100)):02d}cm"
                row[f"true_{name}"] = bool(getattr(result, name)) if available else False
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_reference_applicability(applicability: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scope_type, scope_value, group in scoped_groups(applicability):
        available = group[group["optical_prior_available"].astype(bool)]
        inside = available[available["reference_inside_true_shell"].astype(bool)]
        rows.append(
            {
                "scope_type": scope_type,
                "scope_value": scope_value,
                "reference_count_total": int(len(group)),
                "optical_prior_available_count": int(len(available)),
                "optical_prior_unavailable_count": int(len(group) - len(available)),
                "optical_prior_available_fraction": bool_fraction(group["optical_prior_available"]),
                "reference_inside_true_shell_unconditional": bool_fraction(
                    group["reference_inside_true_shell"]
                ),
                "candidate_present_0p8m_unconditional": bool_fraction(
                    group["candidate_present_within_0p8m"]
                ),
                "full_best_candidate_retained_unconditional": bool_fraction(
                    group["full_fan_best_candidate_retained"]
                ),
                "one_to_one_inside_shell_unconditional": bool_fraction(
                    group["one_to_one_matched_0p8m_and_reference_inside_shell"]
                ),
                "reference_inside_given_prior_available": bool_fraction(
                    available["reference_inside_true_shell"]
                ),
                "candidate_present_given_prior_available": bool_fraction(
                    available["candidate_present_within_0p8m"]
                ),
                "candidate_present_given_reference_inside": bool_fraction(
                    inside["candidate_present_within_0p8m"]
                ),
                "full_best_retained_given_reference_inside": bool_fraction(
                    inside["full_fan_best_candidate_retained"]
                ),
                "one_to_one_given_reference_inside": bool_fraction(inside["one_to_one_matched_0p8m"]),
                "candidate_burden_median_available": finite_median(available["candidate_burden_ratio"]),
                "global_best_rank_median_available": finite_median(available["global_best_rank_0p8m"]),
                "true_shell_local_rank_median_available": finite_median(
                    available["true_shell_local_rank_0p8m"]
                ),
                "same_candidate_rank_reduction_median_available": finite_median(
                    available["same_candidate_rank_reduction_global_to_shell"]
                ),
            }
        )
    return pd.DataFrame(rows)


def summarize_topk_shell_recall(
    evaluation: pd.DataFrame, applicability: pd.DataFrame
) -> pd.DataFrame:
    true_evaluation = evaluation[evaluation["shell_kind"] == "TRUE"]
    null_evaluation = evaluation[evaluation["shell_kind"] == "MATCHED_NULL"]
    rows: list[dict[str, Any]] = []
    for scope_type, scope_value, app_group in scoped_groups(applicability):
        reference_ids = set(app_group["reference_entity_id"].astype(str))
        true_group = true_evaluation[
            true_evaluation["reference_entity_id"].astype(str).isin(reference_ids)
        ]
        null_group = null_evaluation[
            null_evaluation["reference_entity_id"].astype(str).isin(reference_ids)
        ]
        for k in TOP_K:
            for radius in REFERENCE_RADII_M:
                name = f"recall_at_{k}_r_{int(round(radius * 100)):02d}cm"
                true_rate = bool_fraction(true_group[name])
                null_rate = bool_fraction(null_group[name])
                true_inside = true_group[true_group["reference_inside_shell"].astype(bool)]
                null_inside = null_group[null_group["reference_inside_shell"].astype(bool)]
                rows.append(
                    {
                        "scope_type": scope_type,
                        "scope_value": scope_value,
                        "K": int(k),
                        "radius_m": float(radius),
                        "reference_count_unconditional": int(len(app_group)),
                        "reference_count_with_prior": int(len(true_group)),
                        "matched_null_evaluation_rows": int(len(null_group)),
                        "true_recall_unconditional_all_references": bool_fraction(
                            app_group[f"true_{name}"]
                        ),
                        "true_recall_available_references": true_rate,
                        "matched_null_recall_available_references": null_rate,
                        "true_minus_matched_null_available": true_rate - null_rate,
                        "true_recall_given_reference_inside_shell": bool_fraction(true_inside[name]),
                        "matched_null_recall_given_reference_inside_shell": bool_fraction(null_inside[name]),
                    }
                )
    return pd.DataFrame(rows)


def summarize_conditioned_shell_information_gain(comparison: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def emit(dimension: str, value: str, group: pd.DataFrame) -> None:
        rows.append(
            {
                "condition_dimension": dimension,
                "condition_value": value,
                "reference_rows": int(len(group)),
                "true_reference_coverage": bool_fraction(group["true_reference_inside"]),
                "null_reference_coverage_mean": float(group["null_reference_inside_mean"].mean()),
                "true_candidate_presence_0p8m": bool_fraction(group["true_candidate_present_0p8m"]),
                "null_candidate_presence_0p8m_mean": float(
                    group["null_candidate_present_0p8m_mean"].mean()
                ),
                "true_minus_null_candidate_presence": bool_fraction(
                    group["true_candidate_present_0p8m"]
                )
                - float(group["null_candidate_present_0p8m_mean"].mean()),
                "true_full_best_retention": bool_fraction(group["true_full_best_candidate_retained"]),
                "null_full_best_retention_mean": float(
                    group["null_full_best_candidate_retained_mean"].mean()
                ),
                "true_one_to_one_inside_coverage": bool_fraction(
                    group["true_one_to_one_matched_and_inside"]
                ),
                "null_one_to_one_inside_coverage_mean": float(
                    group["null_one_to_one_matched_and_inside_mean"].mean()
                ),
                "true_top5_0p8m": bool_fraction(group["true_recall_at_5_r_80cm"]),
                "null_top5_0p8m_mean": float(group["null_recall_at_5_r_80cm_mean"].mean()),
                "true_candidate_burden_median": finite_median(group["true_candidate_burden"]),
                "null_candidate_burden_median": finite_median(group["null_candidate_burden_median"]),
                "global_best_rank_median": finite_median(group["global_best_rank_0p8m"]),
                "true_shell_local_rank_median": finite_median(group["true_shell_local_rank_0p8m"]),
                "rank_advantage_true_vs_null_median": finite_median(
                    group["rank_advantage_true_vs_null_median"]
                ),
                "true_shared_fraction": bool_fraction(group["true_shared"]),
                "null_shared_mean": float(group["null_shared_mean"].mean()),
            }
        )

    emit("OVERALL", "ALL", comparison)
    dimensions = [
        ("RUN", "run_id"),
        ("RUN_TARGET", ["run_id", "target_id"]),
        ("P0_DOMAIN", "p0_transport_domain_lag1"),
        ("P0_ANCHOR_MODE", "p0_local_anchor_mode_lag1"),
        ("DISPLAY_STATE", "display_observation_state"),
        ("DISPLAY_SHIFT", "display_shift"),
        ("REFERENCE_SUPPORT", "reference_support_status"),
        ("COMMON_FOV", "reference_multimodal_common_fov_status"),
    ]
    for dimension, columns in dimensions:
        if isinstance(columns, list):
            grouped = comparison.groupby(columns, dropna=False, sort=False)
            for keys, group in grouped:
                emit(dimension, "/".join(str(key) for key in keys), group)
        else:
            for key, group in comparison.groupby(columns, dropna=False, sort=False):
                emit(dimension, "MISSING" if pd.isna(key) else str(key), group)
    return pd.DataFrame(rows)


def summarize_both_shells_retain_rank(comparison: pd.DataFrame) -> pd.DataFrame:
    conditioned = comparison[
        comparison["true_candidate_present_0p8m"].astype(bool)
        & (pd.to_numeric(comparison["null_candidate_present_0p8m_mean"], errors="coerce") > 0)
        & np.isfinite(pd.to_numeric(comparison["true_shell_local_rank_0p8m"], errors="coerce"))
        & np.isfinite(pd.to_numeric(comparison["null_shell_local_rank_median_0p8m"], errors="coerce"))
    ].copy()
    rows: list[dict[str, Any]] = []
    for scope_type, scope_value, group in scoped_groups(conditioned):
        advantage = pd.to_numeric(group["rank_advantage_true_vs_null_median"], errors="coerce")
        rows.append(
            {
                "scope_type": scope_type,
                "scope_value": scope_value,
                "both_shells_retain_reference_neighbor_rows": int(len(group)),
                "true_shell_local_rank_median": finite_median(group["true_shell_local_rank_0p8m"]),
                "matched_null_local_rank_median": finite_median(
                    group["null_shell_local_rank_median_0p8m"]
                ),
                "rank_advantage_true_vs_null_median": finite_median(advantage),
                "true_rank_better_fraction": bool_fraction(advantage > 0),
                "rank_tie_fraction": bool_fraction(advantage == 0),
                "true_rank_worse_fraction": bool_fraction(advantage < 0),
            }
        )
    return pd.DataFrame(rows)


def summarize_candidate_frame_search_cost(frame_comparison: pd.DataFrame) -> pd.DataFrame:
    candidate_frames = frame_comparison[frame_comparison["candidate_count_full_fan"] > 0].copy()
    rows: list[dict[str, Any]] = []

    def emit(dimension: str, value: str, group: pd.DataFrame) -> None:
        rows.append(
            {
                "condition_dimension": dimension,
                "condition_value": value,
                "frame_count": int(len(group)),
                "true_candidate_count_median": finite_median(group["true_candidate_count"]),
                "null_candidate_count_median": finite_median(group["null_candidate_count_median"]),
                "true_candidate_burden_median": finite_median(group["true_candidate_burden"]),
                "null_candidate_burden_median": finite_median(group["null_candidate_burden_median"]),
                "true_candidate_density_per_m2_median": finite_median(
                    group["true_candidate_density_per_m2"]
                ),
                "null_candidate_density_per_m2_median": finite_median(
                    group["null_candidate_density_per_m2_median"]
                ),
                "true_p0_core_fraction_median": finite_median(group["true_p0_core_fraction"]),
                "null_p0_core_fraction_median": finite_median(
                    group["null_p0_core_fraction_median"]
                ),
                "true_p0_fallback_fraction_median": finite_median(
                    group["true_p0_fallback_fraction"]
                ),
                "null_p0_fallback_fraction_median": finite_median(
                    group["null_p0_fallback_fraction_median"]
                ),
            }
        )

    emit("OVERALL", "ALL", candidate_frames)
    for run_id, group in candidate_frames.groupby("run_id", sort=False):
        emit("RUN", str(run_id), group)
    for display_shift, group in candidate_frames.groupby("display_shift", sort=False):
        emit("DISPLAY_SHIFT", str(bool(display_shift)), group)
    return pd.DataFrame(rows)


def choose_case_registry(comparison: pd.DataFrame) -> pd.DataFrame:
    specs: list[dict[str, Any]] = [
        {
            "frame_uid": "R02ZF_SARF000482",
            "target_id": "R02ZF_SARPERSON02",
            "case_slug": "R02_P02_F482_RESPONSE_PRESENT_PEAK_MISSING",
            "selection_reason": "FIXED_PROTOCOL_CASE_CONTINUOUS_RESPONSE_BUT_NO_0P8M_LOCAL_MAX_CANDIDATE",
        },
        {
            "frame_uid": "R02ZF_SARF000483",
            "target_id": "R02ZF_SARPERSON03",
            "case_slug": "R02_P03_P04_SHARED_AFTER_TRUE_SHELL",
            "selection_reason": "FIXED_SHARED_MULTIPERSON_CASE",
        },
        {
            "frame_uid": "R03ZF_SARF000458",
            "target_id": "R03ZF_SARPERSON01",
            "case_slug": "R03_F458_OUTER_BOUNDARY_COMMON_FOV",
            "selection_reason": "FIXED_NEAR_OUTER_BOUNDARY_CASE",
        },
        {
            "frame_uid": "R03ZF_SARF000494",
            "target_id": "R03ZF_SARPERSON01",
            "case_slug": "R03_F494_SINGLE_FRAME_VISIBLE_P0_UNAVAILABLE",
            "selection_reason": "FIXED_SINGLE_FRAME_OBSERVABLE_P0_UNAVAILABLE_CASE",
        },
    ]

    def add_extreme(run_id: str, target_suffix: str, label: str, best: bool) -> None:
        subset = comparison[
            (comparison["run_id"] == run_id)
            & comparison["target_id"].astype(str).str.endswith(target_suffix)
        ].copy()
        if subset.empty:
            return
        rank = pd.to_numeric(subset["rank_advantage_true_vs_null_median"], errors="coerce")
        presence = (
            subset["true_candidate_present_0p8m"].astype(float)
            - subset["null_candidate_present_0p8m_mean"].astype(float)
        )
        subset["case_score"] = rank.fillna(0.0) + 20.0 * presence
        row = subset.sort_values("case_score", ascending=not best).iloc[0]
        specs.append(
            {
                "frame_uid": row["frame_uid"],
                "target_id": row["target_id"],
                "case_slug": label,
                "selection_reason": "PREDECLARED_OUTCOME_EXTREME_FOR_VISUALIZATION_ONLY",
            }
        )

    add_extreme("R02ZF", "PERSON01", "R02_P01_TRUE_SHELL_BEST_INFORMATION_GAIN", True)
    add_extreme("R02ZF", "PERSON02", "R02_P02_TRUE_SHELL_BEST_INFORMATION_GAIN", True)
    add_extreme("R04ZF", "PERSON01", "R04_TRUE_SHELL_BEST_INFORMATION_GAIN", True)
    add_extreme("R04ZF", "PERSON03", "R04_TRUE_SHELL_WORST_OR_NULL_LIKE_CASE", False)
    specs.append(
        {
            "frame_uid": "R02ZF_SARF000490",
            "target_id": "R02ZF_SARPERSON02",
            "case_slug": "R02_P02_F490_HIGH_RESPONSE_JUST_OUTSIDE_CANDIDATE_RADIUS",
            "selection_reason": "POST_RUN_REPEATED_REPRESENTATION_CASE_NOT_USED_FOR_STATISTICS",
        }
    )
    registry = pd.DataFrame(specs).drop_duplicates(["frame_uid", "target_id"], keep="first")
    registry.insert(0, "case_id", [f"case_{index:02d}" for index in range(1, len(registry) + 1)])
    return registry


def draw_shell(
    axis: Any,
    intervals: list[tuple[float, float]],
    geometry: dict[str, Any],
    px_per_m: float,
    color: str,
    alpha: float,
    linestyle: str = "-",
) -> None:
    cx = float(geometry["center_x_px"])
    cy = float(geometry["center_y_px"])
    outer = float(geometry["radius_px"])
    inner = INNER_RANGE_M * px_per_m
    for low, high in intervals:
        theta = np.linspace(low, high, 90)
        radians = np.radians(theta)
        outer_x = cx + outer * np.sin(radians)
        outer_y = cy - outer * np.cos(radians)
        inner_x = cx + inner * np.sin(radians[::-1])
        inner_y = cy - inner * np.cos(radians[::-1])
        axis.fill(
            np.concatenate([outer_x, inner_x]),
            np.concatenate([outer_y, inner_y]),
            color=color,
            alpha=alpha,
            linewidth=0,
        )
        axis.plot(outer_x, outer_y, color=color, linewidth=1.5, linestyle=linestyle)
        for angle in (low, high):
            rad = math.radians(angle)
            axis.plot(
                [cx + inner * math.sin(rad), cx + outer * math.sin(rad)],
                [cy - inner * math.cos(rad), cy - outer * math.cos(rad)],
                color=color,
                linewidth=1.3,
                linestyle=linestyle,
            )


def render_case_visualizations(
    p0: Any,
    p1e: Any,
    audit: Any,
    frame_map: dict[str, dict[str, Any]],
    case_registry: pd.DataFrame,
    shell_definitions: pd.DataFrame,
    shell_candidates: pd.DataFrame,
    candidates: pd.DataFrame,
    references: pd.DataFrame,
    evaluation: pd.DataFrame,
) -> pd.DataFrame:
    output_rows = []
    shell_map = {row.shell_id: row for row in shell_definitions.itertuples(index=False)}
    for case in case_registry.itertuples(index=False):
        frame = frame_map[case.frame_uid]
        image = cv2.imread(str(p0.file_url_to_path(frame["sar_image_url"])), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(frame["sar_image_url"])
        mask, radial, theta, px_per_m = audit.single_frame_observation_mask(frame, image)
        maps, _ = audit.compute_existing_candidate_maps_for_mask(p1e, frame, image, mask, radial, theta, px_per_m)
        c2 = maps["C2_COMPACT_JET_GRADIENT_CONSENSUS"]
        true_row = shell_definitions[
            (shell_definitions["frame_uid"] == case.frame_uid)
            & (shell_definitions["shell_kind"] == "TRUE")
        ].iloc[0]
        null_row = shell_definitions[
            (shell_definitions["frame_uid"] == case.frame_uid)
            & (shell_definitions["shell_kind"] == "MATCHED_NULL")
        ].sort_values("null_index").iloc[0]
        true_intervals = [(float(a), float(b)) for a, b in json.loads(true_row["effective_intervals_json"])]
        null_intervals = [(float(a), float(b)) for a, b in json.loads(null_row["effective_intervals_json"])]
        frame_candidates = candidates[candidates["frame_uid"] == case.frame_uid]
        true_candidates = shell_candidates[shell_candidates["shell_id"] == true_row["shell_id"]]
        null_candidates = shell_candidates[shell_candidates["shell_id"] == null_row["shell_id"]]
        frame_refs = references[references["frame_uid"] == case.frame_uid]
        target_ref = frame_refs[frame_refs["target_id"] == case.target_id].iloc[0]
        true_eval = evaluation[
            (evaluation["shell_id"] == true_row["shell_id"])
            & (evaluation["target_id"] == case.target_id)
        ].iloc[0]
        null_eval = evaluation[
            (evaluation["shell_id"] == null_row["shell_id"])
            & (evaluation["target_id"] == case.target_id)
        ].iloc[0]

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        fig, axes = plt.subplots(2, 2, figsize=(16, 10), constrained_layout=True)
        panels = [
            (axes[0, 0], frame_candidates, "Full SAR fan · all existing GT-blind C2 candidates"),
            (axes[0, 1], true_candidates, "TRUE optical shell · SAR candidates retained"),
            (axes[1, 0], null_candidates, "Matched NULL shell 1 · equal-cost wrong azimuth"),
        ]
        for axis, points, title in panels:
            axis.imshow(rgb)
            if len(frame_candidates) and axis is axes[0, 0]:
                axis.scatter(frame_candidates["x_px"], frame_candidates["y_px"], s=5, c="#d8e4f2", alpha=0.42)
                draw_shell(axis, true_intervals, frame["geometry"], px_per_m, "#25d07f", 0.09)
                draw_shell(axis, null_intervals, frame["geometry"], px_per_m, "#ff9b42", 0.04, "--")
            else:
                intervals = true_intervals if axis is axes[0, 1] else null_intervals
                color = "#25d07f" if axis is axes[0, 1] else "#ff9b42"
                draw_shell(axis, intervals, frame["geometry"], px_per_m, color, 0.13)
                if len(points):
                    axis.scatter(
                        points["x_px"],
                        points["y_px"],
                        s=np.clip(34 - 2 * points["shell_local_rank"].to_numpy(float), 8, 28),
                        c=points["shell_local_rank"],
                        cmap="viridis_r",
                        alpha=0.78,
                        edgecolors="white",
                        linewidths=0.25,
                    )
            axis.scatter(frame_refs["x_px"], frame_refs["y_px"], marker="x", s=60, c="#ff4fa3", linewidths=1.5)
            axis.scatter([target_ref["x_px"]], [target_ref["y_px"]], marker="*", s=180, c="#ffe34f", edgecolors="#101b2d", linewidths=0.8)
            axis.set_title(title, fontsize=11)
            axis.set_axis_off()

        axes[1, 1].imshow(np.ma.masked_where(~mask, c2), cmap="magma", vmin=0, vmax=1)
        draw_shell(axes[1, 1], true_intervals, frame["geometry"], px_per_m, "#25d07f", 0.05)
        draw_shell(axes[1, 1], null_intervals, frame["geometry"], px_per_m, "#ff9b42", 0.02, "--")
        axes[1, 1].scatter(frame_candidates["x_px"], frame_candidates["y_px"], s=5, c="white", alpha=0.45)
        axes[1, 1].scatter([target_ref["x_px"]], [target_ref["y_px"]], marker="*", s=180, c="#41d9ff", edgecolors="#101b2d", linewidths=0.8)
        axes[1, 1].set_title("Frozen C2 response field · reference is offline only", fontsize=11)
        axes[1, 1].set_axis_off()

        def fmt(value: Any) -> str:
            return "NA" if pd.isna(value) else f"{float(value):.1f}"

        fig.suptitle(
            f"{case.case_id} · {case.case_slug}\n"
            f"{case.frame_uid} · {case.target_id} | global rank={fmt(true_eval['full_fan_best_candidate_global_rank_within_0p8m'])} "
            f"→ TRUE local={fmt(true_eval['best_candidate_shell_local_rank_within_0p8m'])}, "
            f"NULL1 local={fmt(null_eval['best_candidate_shell_local_rank_within_0p8m'])} | "
            f"burden TRUE={true_eval['candidate_burden_ratio']:.3f}, NULL1={null_eval['candidate_burden_ratio']:.3f}\n"
            f"TRUE state={true_eval['shell_offline_state']} | NULL1 state={null_eval['shell_offline_state']} | "
            f"reference C2 percentile={true_eval['reference_C2_percentile']:.3f}",
            fontsize=13,
        )
        path = VIS_DIR / f"{case.case_id}_{case.case_slug}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        output_rows.append(
            {
                **case._asdict(),
                "visualization_path": str(path),
                "true_shell_state": true_eval["shell_offline_state"],
                "null1_shell_state": null_eval["shell_offline_state"],
                "true_candidate_burden": true_eval["candidate_burden_ratio"],
                "null1_candidate_burden": null_eval["candidate_burden_ratio"],
                "global_rank": true_eval["full_fan_best_candidate_global_rank_within_0p8m"],
                "true_local_rank": true_eval["best_candidate_shell_local_rank_within_0p8m"],
                "null1_local_rank": null_eval["best_candidate_shell_local_rank_within_0p8m"],
                "reference_C2_percentile": true_eval["reference_C2_percentile"],
            }
        )
    return pd.DataFrame(output_rows)


def plot_geometry_fairness(shell_definitions: pd.DataFrame, path: Path) -> None:
    nulls = shell_definitions[shell_definitions["shell_kind"] == "MATCHED_NULL"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)
    axes[0].hist(nulls["width_relative_error"], bins=30, alpha=0.75, label="angle width", color="#3978ff")
    axes[0].hist(nulls["area_relative_error"], bins=30, alpha=0.55, label="observable area", color="#22b573")
    axes[0].set_xlabel("relative mismatch")
    axes[0].set_ylabel("matched null count")
    axes[0].legend()
    axes[1].hist(nulls["common_fov_overlap_fraction_diff"], bins=30, color="#8e64d6")
    axes[1].set_xlabel("common-FoV overlap fraction difference")
    axes[2].scatter(
        nulls["angular_jaccard_with_true"],
        nulls["geometry_match_cost"],
        s=10,
        alpha=0.45,
        c=nulls["area_relative_error"],
        cmap="magma",
    )
    axes[2].set_xlabel("TRUE/NULL angular Jaccard")
    axes[2].set_ylabel("geometry-only match cost")
    fig.suptitle("Matched-null fairness is measured continuously; no difficult frame was deleted")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_run_information_gain(run_target: pd.DataFrame, path: Path) -> None:
    rows = []
    for run_id, group in run_target.groupby("run_id", sort=False):
        weights = pd.to_numeric(group["reference_rows"], errors="raise").to_numpy(float)

        def weighted(column: str) -> float:
            values = pd.to_numeric(group[column], errors="coerce").to_numpy(float)
            valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
            return float(np.average(values[valid], weights=weights[valid])) if np.any(valid) else math.nan

        rows.append(
            {
                "run_id": run_id,
                "true_reference_coverage": weighted("true_reference_coverage"),
                "null_reference_coverage": weighted("null_reference_coverage_mean"),
                "true_candidate_presence": weighted("true_candidate_presence_0p8m"),
                "null_candidate_presence": weighted("null_candidate_presence_0p8m_mean"),
                "true_one_to_one": weighted("true_one_to_one_coverage"),
                "null_one_to_one": weighted("null_one_to_one_coverage_mean"),
            }
        )
    run = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)
    x = np.arange(len(run))
    for axis, true_col, null_col, title in (
        (axes[0], "true_reference_coverage", "null_reference_coverage", "Reference geometry coverage"),
        (axes[1], "true_candidate_presence", "null_candidate_presence", "Candidate within 0.8 m"),
        (axes[2], "true_one_to_one", "null_one_to_one", "One-to-one coverage within 0.8 m"),
    ):
        axis.bar(x - 0.18, run[true_col], 0.36, label="TRUE", color="#22b573")
        axis.bar(x + 0.18, run[null_col], 0.36, label="matched NULL mean", color="#ff9b42")
        axis.set_xticks(x, run["run_id"])
        axis.set_ylim(0, 1.02)
        axis.set_title(title)
    axes[0].legend()
    fig.suptitle("Correct optical shell versus geometry-matched wrong shells")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_r02_rank_change(run_target: pd.DataFrame, path: Path) -> None:
    r02 = run_target[run_target["run_id"] == "R02ZF"].copy()
    r02["short"] = r02["target_id"].astype(str).str.extract(r"(PERSON\d+)$", expand=False)
    fig, axis = plt.subplots(figsize=(10, 5.5), constrained_layout=True)
    x = np.arange(len(r02))
    width = 0.25
    axis.bar(x - width, r02["global_best_rank_median"], width, label="full-fan global rank", color="#71819a")
    axis.bar(x, r02["true_shell_local_rank_median"], width, label="TRUE shell-local rank", color="#22b573")
    axis.bar(x + width, r02["null_shell_local_rank_median"], width, label="matched NULL median", color="#ff9b42")
    axis.set_xticks(x, r02["short"])
    axis.set_ylabel("median rank; lower is better")
    axis.set_title("R02: whether the optical shell converts global competition into a simpler local problem")
    axis.legend()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_conditioned_gain(frame_comparison: pd.DataFrame, path: Path) -> None:
    frame_comparison = frame_comparison[frame_comparison["candidate_count_full_fan"] > 0].copy()
    rows = []
    for display_shift, group in frame_comparison.groupby("display_shift", sort=False):
        rows.append(
            {
                "condition": "DISPLAY_SHIFT" if display_shift else "DISPLAY_BASELINE",
                "burden_true_minus_null": finite_median(
                    group["true_candidate_burden"] - group["null_candidate_burden_median"]
                ),
                "p0_core_true_minus_null": finite_median(
                    group["true_p0_core_fraction"] - group["null_p0_core_fraction_median"]
                ),
                "count": int(len(group)),
            }
        )
    summary = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), constrained_layout=True)
    axes[0].bar(summary["condition"], summary["burden_true_minus_null"], color=["#3978ff", "#8e64d6"])
    axes[0].axhline(0, color="#222", linewidth=0.8)
    axes[0].set_title("TRUE − NULL median candidate burden")
    axes[1].bar(summary["condition"], summary["p0_core_true_minus_null"], color=["#22b573", "#ff9b42"])
    axes[1].axhline(0, color="#222", linewidth=0.8)
    axes[1].set_title("TRUE − NULL P0 CORE fraction")
    for axis in axes:
        axis.tick_params(axis="x", rotation=15)
    fig.suptitle("P0/display remain paired observation conditions, not a new weighted score")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    if not PROTOCOL_PATH.exists():
        raise FileNotFoundError(PROTOCOL_PATH)
    input_hash_checks = []
    for path, expected in EXPECTED_HASHES.items():
        actual = sha256_file(path)
        input_hash_checks.append(
            {"path": str(path), "expected_sha256": expected, "actual_sha256": actual, "match": actual == expected}
        )
    if not all(row["match"] for row in input_hash_checks):
        raise RuntimeError("frozen dependency hash mismatch")
    execution_stages = [{"stage": "FROZEN_DEPENDENCY_HASH_CHECK", "completed_at": now_iso()}]

    p0 = load_module("person_p0_for_shell_gain", P0_SCRIPT)
    p1e = load_module("person_p1e_for_shell_gain", P1E_SCRIPT)
    audit = load_module("person_candidate_audit_for_shell_gain", CANDIDATE_AUDIT_SCRIPT)
    explorer = load_explorer()
    frame_map = {
        frame["sar_frame_uid"]: frame for frame in explorer["frames"] if frame["run_id"] in RUNS
    }
    optical_registry, common_fov_by_run = build_optical_registry(explorer)
    frame_display = pd.read_csv(FRAME_DISPLAY_CSV)
    display_map = frame_display.set_index("frame_uid").to_dict(orient="index")

    shell_rows: list[dict[str, Any]] = []
    no_shell_rows: list[dict[str, Any]] = []
    px_per_m_by_frame: dict[str, float] = {}
    for number, frame in enumerate(
        sorted(frame_map.values(), key=lambda row: (row["run_id"], row["sar_frame_index"])), 1
    ):
        frame_uid = frame["sar_frame_uid"]
        image = cv2.imread(str(p0.file_url_to_path(frame["sar_image_url"])), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(frame["sar_image_url"])
        omega, radial, theta, px_per_m = audit.single_frame_observation_mask(frame, image)
        px_per_m_by_frame[frame_uid] = float(px_per_m)
        theta_valid_sorted = np.sort(theta[omega].astype(float))
        fan_low = float(frame["theta_low_deg"])
        fan_high = float(frame["theta_high_deg"])
        common_low, common_high = common_fov_by_run[frame["run_id"]]
        optical = optical_registry[frame_uid]
        raw_intervals = optical["window_intervals"]
        if not raw_intervals:
            no_shell_rows.append(
                {
                    "run_id": frame["run_id"],
                    "frame_uid": frame_uid,
                    "frame_index": int(frame["sar_frame_index"]),
                    "reason": "NO_OPTICAL_PERSON_SHELL_IN_PLUS_MINUS_250MS_WINDOW",
                    "window_source_frame_count": optical["window_source_frame_count"],
                    "window_shell_count_raw": optical["window_shell_count_raw"],
                }
            )
            continue
        true_metrics = shell_geometry_metrics(
            raw_intervals,
            fan_low,
            fan_high,
            common_low,
            common_high,
            theta_valid_sorted,
            int(omega.sum()),
            px_per_m,
        )
        if not true_metrics["effective_intervals"]:
            no_shell_rows.append(
                {
                    "run_id": frame["run_id"],
                    "frame_uid": frame_uid,
                    "frame_index": int(frame["sar_frame_index"]),
                    "reason": "OPTICAL_SHELL_OUTSIDE_ACTUAL_SAR_FAN",
                    "window_source_frame_count": optical["window_source_frame_count"],
                    "window_shell_count_raw": optical["window_shell_count_raw"],
                }
            )
            continue
        base = {
            "run_id": frame["run_id"],
            "frame_uid": frame_uid,
            "frame_index": int(frame["sar_frame_index"]),
            "sar_timestamp_ms": int(frame["sar_timestamp_ms"]),
            "sync_status": frame.get("sync_status", ""),
            "fan_theta_low_deg": fan_low,
            "fan_theta_high_deg": fan_high,
            "fan_width_deg": fan_high - fan_low,
            "common_fov_theta_low_deg": common_low,
            "common_fov_theta_high_deg": common_high,
            "omega_single_pixel_count": int(omega.sum()),
            "px_per_m": float(px_per_m),
            "search_range_min_m": INNER_RANGE_M,
            "search_range_max_m": float(frame["geometry"]["outer_range_m"]),
            "window_source_frame_count": optical["window_source_frame_count"],
            "window_shell_count_raw": optical["window_shell_count_raw"],
            "time_window_ms": TIME_WINDOW_MS,
            "physical_target_id_used_for_shell_selection": False,
            "reference_used_for_shell_generation": False,
            "candidate_used_for_null_selection": False,
            "display_shift": bool(display_map[frame_uid]["display_shift"]),
            "display_observation_state": display_map[frame_uid]["display_observation_state"],
            "max_adjacent_lag1_display_js": display_map[frame_uid]["max_adjacent_lag1_display_js"],
        }
        shell_rows.append(
            {
                **base,
                "shell_id": f"{frame_uid}__TRUE",
                "shell_kind": "TRUE",
                "null_index": 0,
                "shift_deg": 0.0,
                "geometry_match_cost": 0.0,
                "geometry_match_tier": "TRUE_REFERENCE_COST",
                "width_relative_error": 0.0,
                "area_relative_error": 0.0,
                "common_fov_overlap_fraction_diff": 0.0,
                "boundary_gap_normalized_diff": 0.0,
                "angular_jaccard_with_true": 1.0,
                **{key: value for key, value in true_metrics.items() if key not in {"raw_intervals", "effective_intervals"}},
                "raw_intervals_json": json.dumps(true_metrics["raw_intervals"]),
                "effective_intervals_json": json.dumps(true_metrics["effective_intervals"]),
            }
        )
        nulls = select_matched_nulls(
            true_metrics["effective_intervals"],
            true_metrics,
            fan_low,
            fan_high,
            common_low,
            common_high,
            theta_valid_sorted,
            int(omega.sum()),
            px_per_m,
        )
        for null in nulls:
            shell_rows.append(
                {
                    **base,
                    "shell_id": f"{frame_uid}__NULL{int(null['null_index']):02d}",
                    "shell_kind": "MATCHED_NULL",
                    **{key: value for key, value in null.items() if key not in {"raw_intervals", "effective_intervals"}},
                    "raw_intervals_json": json.dumps(null["raw_intervals"]),
                    "effective_intervals_json": json.dumps(null["effective_intervals"]),
                }
            )
        if number % 75 == 0:
            print(f"geometry {number}/{len(frame_map)}")

    shell_definitions = pd.DataFrame(shell_rows)
    no_shell = pd.DataFrame(no_shell_rows)
    execution_stages.append(
        {
            "stage": "TRUE_AND_MATCHED_NULL_SHELLS_GENERATED_WITHOUT_CANDIDATES_OR_REFERENCES",
            "completed_at": now_iso(),
            "shell_definition_rows": int(len(shell_definitions)),
        }
    )

    candidates_raw = pd.read_csv(CANDIDATES_CSV)
    candidates_raw = candidates_raw[
        candidates_raw["candidate"] == PRIMARY_CANDIDATE
    ].copy()
    candidate_observations_all = pd.read_csv(OBSERVATIONS_CSV, low_memory=False)
    candidate_observations = candidate_observations_all[
        candidate_observations_all["entity_kind"] == "SAR_ONLY_C2_CANDIDATE"
    ].copy()
    del candidate_observations_all
    candidates = verify_candidate_parity(candidates_raw, candidate_observations)
    shell_candidates, shell_metrics = build_shell_candidates(shell_definitions, candidates)
    execution_stages.append(
        {
            "stage": "EXISTING_GT_BLIND_C2_CANDIDATES_RESTRICTED_TO_FROZEN_SHELLS",
            "completed_at": now_iso(),
            "shell_candidate_rows": int(len(shell_candidates)),
        }
    )

    observations_for_reference = pd.read_csv(OBSERVATIONS_CSV, low_memory=False)
    references = observations_for_reference[
        observations_for_reference["entity_kind"] == "PERSON_REFERENCE"
    ].copy()
    manual_references = pd.read_csv(REFERENCES_CSV, low_memory=False)
    verify_reference_parity(references, manual_references)
    execution_stages.append(
        {
            "stage": "MANUAL_REFERENCE_CONTENT_MATERIALIZED_FOR_OFFLINE_EVALUATION",
            "completed_at": now_iso(),
            "reference_rows": int(len(references)),
        }
    )
    evaluation, frame_reference_metrics = offline_reference_evaluation(
        shell_definitions,
        shell_candidates,
        candidates,
        references,
        px_per_m_by_frame,
    )
    comparison = build_true_vs_null_comparison(evaluation)
    run_target_summary = summarize_by_run_target(comparison)
    frame_comparison = paired_shell_frame_metrics(shell_metrics)
    applicability = build_reference_optical_prior_applicability(
        references, shell_definitions, no_shell, evaluation
    )
    unconditional_summary = summarize_reference_applicability(applicability)
    topk_summary = summarize_topk_shell_recall(evaluation, applicability)
    conditioned_summary = summarize_conditioned_shell_information_gain(comparison)
    both_retain_rank_summary = summarize_both_shells_retain_rank(comparison)
    candidate_frame_summary = summarize_candidate_frame_search_cost(frame_comparison)
    true_missing_audit = evaluation[
        (evaluation["shell_kind"] == "TRUE")
        & evaluation["reference_inside_shell"].astype(bool)
        & ~evaluation["candidate_present_within_0p8m"].astype(bool)
    ].copy()
    case_registry = choose_case_registry(comparison)
    rendered_cases = render_case_visualizations(
        p0,
        p1e,
        audit,
        frame_map,
        case_registry,
        shell_definitions,
        shell_candidates,
        candidates,
        references,
        evaluation,
    )

    plot_geometry_fairness(shell_definitions, VIS_DIR / "matched_null_geometry_fairness.png")
    plot_run_information_gain(run_target_summary, VIS_DIR / "true_vs_null_information_gain_by_run.png")
    plot_r02_rank_change(run_target_summary, VIS_DIR / "r02_global_to_shell_local_rank.png")
    plot_conditioned_gain(frame_comparison, VIS_DIR / "p0_display_conditioned_shell_gain.png")

    shell_definitions.to_csv(OUTPUT_DIR / "shell_definition_table.csv", index=False, encoding="utf-8-sig")
    no_shell.to_csv(OUTPUT_DIR / "no_optical_shell_frames.csv", index=False, encoding="utf-8-sig")
    shell_candidates.to_csv(OUTPUT_DIR / "shell_candidate_table.csv", index=False, encoding="utf-8-sig")
    shell_metrics.to_csv(OUTPUT_DIR / "shell_candidate_metrics.csv", index=False, encoding="utf-8-sig")
    evaluation.to_csv(OUTPUT_DIR / "offline_reference_shell_evaluation.csv", index=False, encoding="utf-8-sig")
    frame_reference_metrics.to_csv(
        OUTPUT_DIR / "frame_shell_one_to_one_metrics.csv", index=False, encoding="utf-8-sig"
    )
    comparison.to_csv(OUTPUT_DIR / "reference_true_vs_matched_null.csv", index=False, encoding="utf-8-sig")
    run_target_summary.to_csv(OUTPUT_DIR / "run_target_shell_information_gain.csv", index=False, encoding="utf-8-sig")
    frame_comparison.to_csv(OUTPUT_DIR / "frame_true_vs_matched_null_conditions.csv", index=False, encoding="utf-8-sig")
    applicability.to_csv(
        OUTPUT_DIR / "reference_optical_prior_applicability.csv", index=False, encoding="utf-8-sig"
    )
    unconditional_summary.to_csv(
        OUTPUT_DIR / "unconditional_reference_summary.csv", index=False, encoding="utf-8-sig"
    )
    topk_summary.to_csv(OUTPUT_DIR / "topk_shell_recall_summary.csv", index=False, encoding="utf-8-sig")
    conditioned_summary.to_csv(
        OUTPUT_DIR / "conditioned_shell_information_gain.csv", index=False, encoding="utf-8-sig"
    )
    both_retain_rank_summary.to_csv(
        OUTPUT_DIR / "conditional_both_shells_retain_rank_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    candidate_frame_summary.to_csv(
        OUTPUT_DIR / "candidate_frame_search_cost_p0_summary.csv", index=False, encoding="utf-8-sig"
    )
    true_missing_audit.to_csv(
        OUTPUT_DIR / "true_shell_candidate_missing_audit.csv", index=False, encoding="utf-8-sig"
    )
    rendered_cases.to_csv(OUTPUT_DIR / "case_registry.csv", index=False, encoding="utf-8-sig")

    nulls = shell_definitions[shell_definitions["shell_kind"] == "MATCHED_NULL"]
    true_eval = evaluation[evaluation["shell_kind"] == "TRUE"]
    null_eval = evaluation[evaluation["shell_kind"] == "MATCHED_NULL"]
    f482 = comparison[
        (comparison["frame_uid"] == "R02ZF_SARF000482")
        & (comparison["target_id"] == "R02ZF_SARPERSON02")
    ]
    summary = {
        "schema": "PERSON_P1E_MATCHED_OPTICAL_SHELL_INFORMATION_GAIN_V1",
        "created_at": now_iso(),
        "status": "MATCHED_OPTICAL_SHELL_DIAGNOSTIC_COMPLETE_NO_NEW_PASS_FAIL",
        "interpreter": sys.executable,
        "analysis_script_sha256": sha256_file(SCRIPT_PATH),
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "input_hash_checks": input_hash_checks,
        "counts": {
            "frames_total": len(frame_map),
            "frames_with_true_shell": int((shell_definitions["shell_kind"] == "TRUE").sum()),
            "frames_without_true_shell": int(len(no_shell)),
            "matched_null_shells": int(len(nulls)),
            "shell_definition_rows": int(len(shell_definitions)),
            "shell_candidate_rows": int(len(shell_candidates)),
            "offline_reference_shell_rows": int(len(evaluation)),
            "reference_true_vs_null_rows": int(len(comparison)),
            "reference_rows_total_unconditional": int(len(applicability)),
            "optical_prior_unavailable_reference_rows": int(
                applicability["optical_prior_unavailable"].astype(bool).sum()
            ),
            "candidate_frames_with_true_shell": int(
                (frame_comparison["candidate_count_full_fan"] > 0).sum()
            ),
            "both_shells_retain_rank_rows": int(
                both_retain_rank_summary.loc[
                    (both_retain_rank_summary["scope_type"] == "OVERALL")
                    & (both_retain_rank_summary["scope_value"] == "ALL"),
                    "both_shells_retain_reference_neighbor_rows",
                ].iloc[0]
            ),
            "true_shell_candidate_missing_inside_rows": int(len(true_missing_audit)),
            "case_count": int(len(rendered_cases)),
        },
        "execution_order": execution_stages,
        "geometry_fairness": {
            "null_count_per_frame": NULL_COUNT,
            "width_relative_error_median": float(nulls["width_relative_error"].median()),
            "width_relative_error_p90": float(nulls["width_relative_error"].quantile(0.90)),
            "area_relative_error_median": float(nulls["area_relative_error"].median()),
            "area_relative_error_p90": float(nulls["area_relative_error"].quantile(0.90)),
            "common_fov_overlap_diff_median": float(nulls["common_fov_overlap_fraction_diff"].median()),
            "geometry_match_tier_counts": nulls["geometry_match_tier"].value_counts().to_dict(),
            "shift_abs_median_deg": float(nulls["shift_deg"].abs().median()),
            "angular_jaccard_median": float(nulls["angular_jaccard_with_true"].median()),
        },
        "overall_reference_comparison": {
            "true_reference_geometry_coverage": bool_fraction(true_eval["reference_inside_shell"]),
            "matched_null_reference_geometry_coverage": bool_fraction(null_eval["reference_inside_shell"]),
            "true_candidate_presence_0p8m": bool_fraction(true_eval["candidate_present_within_0p8m"]),
            "matched_null_candidate_presence_0p8m": bool_fraction(
                null_eval["candidate_present_within_0p8m"]
            ),
            "true_full_best_candidate_retention": bool_fraction(
                true_eval["full_fan_best_candidate_retained"]
            ),
            "matched_null_full_best_candidate_retention": bool_fraction(
                null_eval["full_fan_best_candidate_retained"]
            ),
            "true_one_to_one_coverage_0p8m": bool_fraction(true_eval["one_to_one_matched_0p8m"]),
            "matched_null_one_to_one_coverage_0p8m": bool_fraction(
                null_eval["one_to_one_matched_0p8m"]
            ),
            "true_one_to_one_inside_coverage_0p8m": bool_fraction(
                true_eval["one_to_one_matched_0p8m_and_reference_inside_shell"]
            ),
            "matched_null_one_to_one_inside_coverage_0p8m": bool_fraction(
                null_eval["one_to_one_matched_0p8m_and_reference_inside_shell"]
            ),
            "true_candidate_burden_median": finite_median(true_eval["candidate_burden_ratio"]),
            "matched_null_candidate_burden_median": finite_median(
                null_eval["candidate_burden_ratio"]
            ),
            "true_shared_fraction": bool_fraction(true_eval["shared_any_candidate_within_0p8m"]),
            "matched_null_shared_fraction": bool_fraction(
                null_eval["shared_any_candidate_within_0p8m"]
            ),
            "true_candidate_presence_given_reference_inside": bool_fraction(
                true_eval.loc[
                    true_eval["reference_inside_shell"].astype(bool),
                    "candidate_present_within_0p8m",
                ]
            ),
            "matched_null_candidate_presence_given_reference_inside": bool_fraction(
                null_eval.loc[
                    null_eval["reference_inside_shell"].astype(bool),
                    "candidate_present_within_0p8m",
                ]
            ),
            "true_top5_0p8m_given_reference_inside": bool_fraction(
                true_eval.loc[
                    true_eval["reference_inside_shell"].astype(bool), "recall_at_5_r_80cm"
                ]
            ),
            "matched_null_top5_0p8m_given_reference_inside": bool_fraction(
                null_eval.loc[
                    null_eval["reference_inside_shell"].astype(bool), "recall_at_5_r_80cm"
                ]
            ),
        },
        "run_target_summaries": run_target_summary.to_dict(orient="records"),
        "R02_P02_F482": f482.iloc[0].to_dict() if len(f482) else {},
        "semantic_boundaries": {
            "reference_used_for_true_or_null_shell_generation": False,
            "candidate_or_score_used_for_null_selection": False,
            "reference_slice_materialized_after_shell_and_candidate_generation": True,
            "monolithic_observation_table_read_for_candidate_parity_before_reference_slice": True,
            "strict_sealed_reference_process_isolation_claimed": False,
            "reference_file_bytes_hashed_before_run_without_content_based_selection": True,
            "physical_target_id_used_for_optical_shell_selection": False,
            "optical_assigned_SAR_range": False,
            "SAR_boxes_created_or_moved": 0,
            "P0_retuned_or_refit": False,
            "C0_C3_modified": False,
            "new_weighted_score_classifier_or_tracker": False,
            "all_runs_are_exposed_development_material": True,
            "shared_is_physical_scattering_fusion": False,
            "candidate_missing_equals_physical_response_absence": False,
            "SAR_retains_final_localization_authority": True,
            "new_PASS_or_FAIL_claimed": False,
        },
    }
    (OUTPUT_DIR / "diagnostic_summary.json").write_text(
        json.dumps(json_safe(summary), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": summary["status"],
                "frames_with_true_shell": summary["counts"]["frames_with_true_shell"],
                "matched_null_shells": summary["counts"]["matched_null_shells"],
                "reference_rows": summary["counts"]["reference_true_vs_null_rows"],
                "output": str(OUTPUT_DIR),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
