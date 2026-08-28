"""Minimal runtime-track shell and frozen-C2 response-region diagnostic.

The two interfaces are intentionally kept separate.  Optical tracks only form
time/azimuth shells; C2 remains the SAR-only image response.  Manual SAR
references are loaded only after all track shells, response regions, and
shell-restricted GT-blind candidates have been materialized.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from scipy.optimize import linear_sum_assignment


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
P1E_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface"
OUTPUT_DIR = P1E_ROOT / "runtime_track_response_region_minimal_v1"
VIS_DIR = OUTPUT_DIR / "visualizations"
MASK_DIR = OUTPUT_DIR / "response_region_masks"
PROTOCOL_PATH = OUTPUT_DIR / "00_RUNTIME_TRACK_RESPONSE_REGION_PROTOCOL_FROZEN_BEFORE_RUN.md"
PROVENANCE_AMENDMENT_PATH = OUTPUT_DIR / "00A_PRE_RUN_OPTICAL_IDENTITY_PROVENANCE_AMENDMENT.md"
REGION_AMENDMENT_PATH = OUTPUT_DIR / "00B_PRE_RUN_REGION_RULE_CLARIFICATION.md"

P0_SCRIPT = TASK_DIR / "run_p0_common_apparent_motion.py"
P1E_SCRIPT = TASK_DIR / "run_p1e_single_frame_position_specificity.py"
CANDIDATE_SCRIPT = TASK_DIR / "run_p1e_candidate_recall_audit.py"
SHELL_SCRIPT = TASK_DIR / "run_p1e_optical_shell_information_gain.py"
EXPLORER_PATH = (
    WORKSPACE / "output" / "person_multidimensional_response_explorer_20260823" / "explorer_data.js"
)
OPTICAL_HYPOTHESES = (
    WORKSPACE
    / "output"
    / "person_optical_guided_sar_annotation_full_20260823"
    / "optical_person_frame_hypotheses.parquet"
)
OPTICAL_TRACK_SUMMARY = (
    WORKSPACE
    / "output"
    / "person_optical_guided_sar_annotation_full_20260823"
    / "optical_person_track_summary.parquet"
)
CANDIDATE_ROOT = P1E_ROOT / "candidate_recall_semantic_split_v1" / "single_frame_candidate_recall"
CANDIDATES_CSV = CANDIDATE_ROOT / "gt_blind_candidates_all_processed_frames.csv"
REFERENCES_CSV = CANDIDATE_ROOT / "manual_reference_candidate_interpretation_v2.csv"
OBSERVATIONS_CSV = P1E_ROOT / "observation_model_diagnostic_v1" / "observation_condition_table.csv"
MATCHED_SHELL_CSV = P1E_ROOT / "optical_shell_information_gain_v1" / "shell_definition_table.csv"

RUNS = ("R01ZF", "R02ZF", "R03ZF", "R04ZF")
PRIMARY_CANDIDATE = "C2_COMPACT_JET_GRADIENT_CONSENSUS"
TIME_WINDOWS_MS = (0, 100, 250, 500)
PERCENTILE_LEVELS = (0.90, 0.95, 0.975)
PERCENTILE_TAGS = {0.90: "Q090", 0.95: "Q095", 0.975: "Q0975"}
PRIMARY_PERCENTILE = 0.95
REFERENCE_REGION_RADIUS_M = 0.30
PEAK_REFERENCE_RADIUS_M = 0.80
OPTICAL_SLOPE_DEG_PER_PX = 0.02666536443690682
OPTICAL_INTERCEPT_DEG = -45.502258572693094
OPTICAL_GUARD_DEG = 6.0
OPTICAL_WIDTH_PX = 3840.0
INNER_RANGE_M = 0.75
EXTENDED_MAJOR_AXIS_M = 1.80
EXTENDED_ELONGATION = 3.0

INTERFACE_RAW = "RAW_DETECTED_FRAGMENT_ALL"
INTERFACE_STITCHED = "STITCHED_ACCEPTED_GT_BLIND_OFFLINE_PROXY"

EXPECTED_HASHES = {
    P0_SCRIPT: "0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8",
    P1E_SCRIPT: "98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1",
    CANDIDATE_SCRIPT: "84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8",
    SHELL_SCRIPT: "2C71440DF9C22FDCE17A3C4050E4E0054F6B7CA4542C44C134E2DEA3478A2203",
    EXPLORER_PATH: "C39E60EB478FF7D815EFE6984D3BCF36600737E2EC3D1FF76D04020DED54EF7D",
    OPTICAL_HYPOTHESES: "15D65A299762E87BFD6F21E811C754D1DF062AC6AFC1840A1C1A9B162AB8B478",
    OPTICAL_TRACK_SUMMARY: "1EB79D239A2CE4733A1D55317A552FE929ACFC473F2C364BEDAF9CC38787DEA0",
    CANDIDATES_CSV: "D2F1673A247FDB3AB1DD884F989ADC0ABE4E33A86AEFE45B5DFB4BE286FD6EC0",
    REFERENCES_CSV: "796F20EB3080C5B45CDEBBCC71584CC95C65691F056D46C4A31704A3D86E8EC7",
    OBSERVATIONS_CSV: "DE65B9705A353F0DF783E0D4A59D0274FD05547362ABE463C50C9C5469D80C21",
    MATCHED_SHELL_CSV: "8A5EDD07DB9AB452A79C9AEC95469BB42A88CA23AF6EFFA7FBA8EA26D0F39C16",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
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


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_explorer_sanitized() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    payload = json.loads(text[text.index("{") : text.rindex("}") + 1])
    frames: list[dict[str, Any]] = []
    for source in payload["frames"]:
        if source["run_id"] not in RUNS:
            continue
        frames.append(
            {
                "sar_frame_uid": source["sar_frame_uid"],
                "run_id": source["run_id"],
                "sar_frame_index": int(source["sar_frame_index"]),
                "sar_timestamp_ms": int(source["sar_timestamp_ms"]),
                "sar_image_url": source["sar_image_url"],
                "sar_width_px": int(source["sar_width_px"]),
                "sar_height_px": int(source["sar_height_px"]),
                "geometry": dict(source["geometry"]),
                "theta_low_deg": float(source["theta_low_deg"]),
                "theta_high_deg": float(source["theta_high_deg"]),
                "nominal_optical_frame_index": int(source["nominal_optical_frame_index"]),
                "nominal_optical_timestamp_ms": int(source["nominal_optical_timestamp_ms"]),
                "sync_status": source.get("sync_status", "UNVERIFIED"),
            }
        )
    process_note = {
        "explorer_container_loaded": True,
        "explorer_annotation_content_used": False,
        "sanitized_frame_keys": sorted(frames[0]) if frames else [],
        "strict_sealed_process_isolation_claimed": False,
        "reason": "The existing explorer container includes annotations, but this function drops them before shell/region computation.",
    }
    return frames, process_note


def percentile_field(values: np.ndarray, mask: np.ndarray, bins: int = 4096) -> np.ndarray:
    output = np.zeros(values.shape, dtype=np.float32)
    finite = mask & np.isfinite(values)
    sample = np.clip(values[finite], 0.0, 1.0)
    if sample.size < 2:
        return output
    quant = np.clip(
        np.floor(np.clip(values, 0.0, 1.0) * (bins - 1)), 0, bins - 1
    ).astype(int)
    hist = np.bincount(quant[finite], minlength=bins)
    cdf = np.cumsum(hist).astype(np.float64) / max(float(hist.sum()), 1.0)
    output[finite] = cdf[quant[finite]].astype(np.float32)
    return output


def finite_median(values: Any) -> float:
    numeric = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(float)
    numeric = numeric[np.isfinite(numeric)]
    return float(np.median(numeric)) if len(numeric) else math.nan


def bool_fraction(values: Any) -> float:
    series = pd.Series(values)
    return float(series.astype(bool).mean()) if len(series) else math.nan


def interval_distance(theta: float, intervals: Iterable[tuple[float, float]]) -> float:
    distances = []
    for low, high in intervals:
        if low <= theta <= high:
            return 0.0
        distances.append(min(abs(theta - low), abs(theta - high)))
    return min(distances) if distances else math.inf


def intervals_close(
    left: Iterable[tuple[float, float]],
    right: Iterable[tuple[float, float]],
    atol: float = 1e-9,
) -> bool:
    left_rows = [(float(low), float(high)) for low, high in left]
    right_rows = [(float(low), float(high)) for low, high in right]
    if len(left_rows) != len(right_rows):
        return False
    return all(
        abs(left_low - right_low) <= atol and abs(left_high - right_high) <= atol
        for (left_low, left_high), (right_low, right_high) in zip(left_rows, right_rows)
    )


def prepare_track_observations(hypotheses: pd.DataFrame) -> dict[str, dict[str, pd.DataFrame]]:
    if "physical_target_id" in hypotheses.columns:
        raise RuntimeError("optical runtime-proxy input unexpectedly contains physical_target_id")
    hypotheses = hypotheses[hypotheses["run_id"].isin(RUNS)].copy()
    hypotheses["timestamp_ms"] = pd.to_numeric(hypotheses["timestamp_ms"], errors="raise").astype(int)
    for column in ("bbox_x1", "bbox_x2"):
        hypotheses[column] = pd.to_numeric(hypotheses[column], errors="raise")
    hypotheses["theta_shell_low_deg"] = (
        OPTICAL_SLOPE_DEG_PER_PX * hypotheses["bbox_x1"]
        + OPTICAL_INTERCEPT_DEG
        - OPTICAL_GUARD_DEG
    )
    hypotheses["theta_shell_high_deg"] = (
        OPTICAL_SLOPE_DEG_PER_PX * hypotheses["bbox_x2"]
        + OPTICAL_INTERCEPT_DEG
        + OPTICAL_GUARD_DEG
    )

    raw = hypotheses[hypotheses["box_source"].astype(str).eq("DETECTED")].copy()
    raw["interface_kind"] = INTERFACE_RAW
    raw["track_id"] = raw["raw_track_fragment_id"].astype(str)
    raw["strict_runtime_identity_claimed"] = False
    raw["runtime_availability_semantics"] = "AUTOMATIC_OPTICAL_TRACKLET_REPLAY_CLOSEST_AVAILABLE_RUNTIME_PROXY"

    stitched = hypotheses[hypotheses["accepted_for_annotation_queue"].astype(bool)].copy()
    stitched["interface_kind"] = INTERFACE_STITCHED
    stitched["track_id"] = stitched["optical_person_id"].astype(str)
    stitched["strict_runtime_identity_claimed"] = False
    stitched["runtime_availability_semantics"] = "GT_BLIND_FULL_RUN_STITCH_AND_SHORT_GAP_INTERPOLATION_OFFLINE_PROXY"

    output: dict[str, dict[str, pd.DataFrame]] = {INTERFACE_RAW: {}, INTERFACE_STITCHED: {}}
    for interface, frame in ((INTERFACE_RAW, raw), (INTERFACE_STITCHED, stitched)):
        for run_id, group in frame.groupby("run_id", sort=False):
            output[interface][str(run_id)] = group.sort_values(
                ["timestamp_ms", "track_id", "confidence"], ascending=[True, True, False]
            ).drop_duplicates(["timestamp_ms", "track_id"], keep="first")
    return output


def build_provenance_table(hypotheses: pd.DataFrame, track_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    hypotheses = hypotheses[hypotheses["run_id"].isin(RUNS)].copy()
    detected = hypotheses[hypotheses["box_source"].astype(str).eq("DETECTED")].copy()
    for run_id in RUNS:
        run_det = detected[detected["run_id"] == run_id]
        run_hyp = hypotheses[hypotheses["run_id"] == run_id]
        run_tracks = track_summary[track_summary["run_id"] == run_id]
        accepted = run_tracks[run_tracks["accepted_for_annotation_queue"].astype(bool)]
        raw_group = run_det.groupby("raw_track_fragment_id", sort=False)
        rows.append(
            {
                "run_id": run_id,
                "detected_row_count": int(len(run_det)),
                "posthoc_interpolated_row_count": int((run_hyp["box_source"] != "DETECTED").sum()),
                "raw_fragment_count": int(run_det["raw_track_fragment_id"].nunique()),
                "raw_botsort_fragment_count": int(
                    run_det.loc[run_det["tracker_status"].astype(str).eq("BOTSORT_TRACK_ID"), "raw_track_fragment_id"].nunique()
                ),
                "raw_anonymous_fragment_count": int(
                    run_det.loc[~run_det["tracker_status"].astype(str).eq("BOTSORT_TRACK_ID"), "raw_track_fragment_id"].nunique()
                ),
                "stitched_track_count": int(len(run_tracks)),
                "stitched_accepted_track_count": int(len(accepted)),
                "accepted_raw_fragment_count": int(
                    run_det.loc[run_det["accepted_for_annotation_queue"].astype(bool), "raw_track_fragment_id"].nunique()
                ),
                "ambiguous_stitch_count_sum_accepted": int(accepted["ambiguous_stitch_count"].sum()),
                "multi_fragment_accepted_track_count": int((accepted["raw_fragment_count"] > 1).sum()),
                "accepted_coverage_median": finite_median(accepted["coverage_ratio"]),
                "accepted_coverage_min": float(accepted["coverage_ratio"].min()) if len(accepted) else math.nan,
                "raw_fragment_span_median_frames": finite_median(
                    raw_group["frame_index"].agg(lambda s: int(s.max() - s.min() + 1))
                ) if len(run_det) else math.nan,
                "physical_target_id_column_present": False,
                "raw_interface_semantics": "AUTOMATIC_OPTICAL_TRACKLET_NOT_PHYSICAL_IDENTITY_TRUTH",
                "stitched_interface_semantics": "GT_BLIND_OFFLINE_CONTINUITY_PROXY_NOT_STRICT_RUNTIME_ID",
            }
        )
    return pd.DataFrame(rows)


def build_track_interface_provenance_table(
    track_observations: dict[str, dict[str, pd.DataFrame]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for interface, by_run in track_observations.items():
        for run_id, observations in by_run.items():
            for track_id, group in observations.groupby("track_id", sort=True):
                rows.append(
                    {
                        "run_id": run_id,
                        "interface_kind": interface,
                        "track_id": str(track_id),
                        "row_count": int(len(group)),
                        "unique_timestamp_count": int(group["timestamp_ms"].nunique()),
                        "frame_index_min": int(group["frame_index"].min()),
                        "frame_index_max": int(group["frame_index"].max()),
                        "timestamp_min_ms": int(group["timestamp_ms"].min()),
                        "timestamp_max_ms": int(group["timestamp_ms"].max()),
                        "confidence_median": finite_median(group["confidence"]),
                        "box_sources": ";".join(
                            sorted(set(group["box_source"].astype(str)))
                        ),
                        "tracker_statuses": ";".join(
                            sorted(set(group["tracker_status"].astype(str)))
                        ),
                        "track_tiers": ";".join(
                            sorted(set(group["track_tier"].astype(str)))
                        ),
                        "raw_fragment_ids": ";".join(
                            sorted(set(group["raw_track_fragment_id"].astype(str)))
                        ),
                        "raw_fragment_count": int(
                            group["raw_track_fragment_id"].nunique()
                        ),
                        "parent_stitched_ids": ";".join(
                            sorted(set(group["optical_person_id"].astype(str)))
                        ),
                        "parent_stitched_id_count": int(
                            group["optical_person_id"].nunique()
                        ),
                        "ambiguous_stitch_count_max": int(
                            group["ambiguous_stitch_count"].max()
                        ),
                        "accepted_parent_fraction": float(
                            group["accepted_for_annotation_queue"].astype(bool).mean()
                        ),
                        "contains_posthoc_interpolation": bool(
                            group["box_source"].astype(str).ne("DETECTED").any()
                        ),
                        "physical_target_id_used": False,
                        "strict_runtime_identity_claimed": False,
                        "interface_semantics": str(
                            group["runtime_availability_semantics"].iloc[0]
                        ),
                    }
                )
    return pd.DataFrame(rows)


def component_descriptors(
    frame: dict[str, Any],
    score_field: np.ndarray,
    percentile: np.ndarray,
    eligible: np.ndarray,
    support_fraction: np.ndarray,
    radial: np.ndarray,
    theta: np.ndarray,
    px_per_m: float,
    level: float,
) -> tuple[np.ndarray, list[dict[str, Any]], float]:
    tag = PERCENTILE_TAGS[level]
    binary = eligible & (percentile >= level)
    count, labels_raw, _, _ = cv2.connectedComponentsWithStats(binary.astype(np.uint8), 8)
    components: list[dict[str, Any]] = []
    for old_label in range(1, count):
        ys, xs = np.where(labels_raw == old_label)
        if not len(xs):
            continue
        values = score_field[ys, xs]
        components.append(
            {
                "old_label": old_label,
                "sort_max": float(np.max(values)),
                "sort_y": int(np.min(ys)),
                "sort_x": int(np.min(xs)),
                "xs": xs,
                "ys": ys,
            }
        )
    components.sort(key=lambda row: (-row["sort_max"], row["sort_y"], row["sort_x"]))
    labels = np.zeros_like(labels_raw, dtype=np.int32)
    rows: list[dict[str, Any]] = []
    numeric_threshold = float(np.min(score_field[binary])) if np.any(binary) else math.nan
    for new_label, component in enumerate(components, start=1):
        xs = component.pop("xs")
        ys = component.pop("ys")
        labels[ys, xs] = new_label
        coords = np.column_stack((xs.astype(float), ys.astype(float))) / px_per_m
        center = coords.mean(axis=0)
        centered = coords - center
        if len(coords) >= 2:
            covariance = centered.T @ centered / max(len(coords) - 1, 1)
            eigenvalues, eigenvectors = np.linalg.eigh(covariance)
            order = np.argsort(eigenvalues)[::-1]
            basis = eigenvectors[:, order]
            projected = centered @ basis
            major_extent = float(projected[:, 0].max() - projected[:, 0].min())
            minor_extent = float(projected[:, 1].max() - projected[:, 1].min())
        else:
            major_extent = minor_extent = 0.0
        elongation = major_extent / max(minor_extent, 1.0 / px_per_m)
        component_mask = labels == new_label
        ring = cv2.dilate(component_mask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~component_mask
        touches_boundary = bool(np.any(ring & ~eligible))
        has_truncated_support = bool(np.any(support_fraction[ys, xs] < 0.80))
        structure_state = (
            "EXTENDED_OR_RIDGE_RESPONSE"
            if major_extent > EXTENDED_MAJOR_AXIS_M or elongation >= EXTENDED_ELONGATION
            else "COMPACT_OR_UNRESOLVED_SHAPE"
        )
        values = score_field[ys, xs]
        region_id = f"{frame['sar_frame_uid']}__{tag}__R{new_label:04d}"
        rows.append(
            {
                "run_id": frame["run_id"],
                "frame_uid": frame["sar_frame_uid"],
                "frame_index": int(frame["sar_frame_index"]),
                "percentile_level": level,
                "percentile_tag": tag,
                "region_label": new_label,
                "region_id": region_id,
                "numeric_score_threshold": numeric_threshold,
                "pixel_count": int(len(xs)),
                "area_m2": float(len(xs) / (px_per_m * px_per_m)),
                "score_max": float(np.max(values)),
                "score_mean": float(np.mean(values)),
                "score_median": float(np.median(values)),
                "centroid_x_px_shape_descriptor": float(np.mean(xs)),
                "centroid_y_px_shape_descriptor": float(np.mean(ys)),
                "major_extent_m": major_extent,
                "minor_extent_m": minor_extent,
                "elongation": elongation,
                "structure_state": structure_state,
                "range_min_m": float(np.min(radial[ys, xs]) / px_per_m),
                "range_max_m": float(np.max(radial[ys, xs]) / px_per_m),
                "theta_min_deg": float(np.min(theta[ys, xs])),
                "theta_max_deg": float(np.max(theta[ys, xs])),
                "support_fraction_min": float(np.min(support_fraction[ys, xs])),
                "support_fraction_median": float(np.median(support_fraction[ys, xs])),
                "touches_observable_boundary": touches_boundary,
                "has_truncated_support": has_truncated_support,
                "reference_used_for_region_generation": False,
                "region_is_final_person_box": False,
            }
        )
    return labels, rows, numeric_threshold


def build_shell_rows_for_frame(
    frame: dict[str, Any],
    interface: str,
    observations: pd.DataFrame,
    window_ms: int,
    shell_module: Any,
    theta_valid_sorted: np.ndarray,
    omega_count: int,
    px_per_m: float,
) -> list[dict[str, Any]]:
    query_ms = int(frame["nominal_optical_timestamp_ms"])
    if observations.empty:
        selected = observations
    elif window_ms == 0:
        selected = observations[observations["timestamp_ms"] == query_ms]
    else:
        selected = observations[np.abs(observations["timestamp_ms"] - query_ms) <= window_ms]
    if selected.empty:
        return []
    fan_low = float(frame["theta_low_deg"])
    fan_high = float(frame["theta_high_deg"])
    common_low = max(fan_low, OPTICAL_INTERCEPT_DEG)
    common_high = min(fan_high, OPTICAL_SLOPE_DEG_PER_PX * OPTICAL_WIDTH_PX + OPTICAL_INTERCEPT_DEG)
    base = {
        "run_id": frame["run_id"],
        "frame_uid": frame["sar_frame_uid"],
        "frame_index": int(frame["sar_frame_index"]),
        "sar_timestamp_ms": int(frame["sar_timestamp_ms"]),
        "nominal_optical_timestamp_ms": query_ms,
        "sync_status": frame["sync_status"],
        "interface_kind": interface,
        "time_window_half_width_ms": int(window_ms),
        "fan_theta_low_deg": fan_low,
        "fan_theta_high_deg": fan_high,
        "common_fov_theta_low_deg": common_low,
        "common_fov_theta_high_deg": common_high,
        "omega_single_pixel_count": int(omega_count),
        "px_per_m": float(px_per_m),
        "physical_target_id_used_for_shell_generation": False,
        "reference_used_for_shell_generation": False,
        "sar_range_assigned_by_optical": False,
        "strict_runtime_identity_claimed": False,
        "centered_window_may_use_future_optical_observations": bool(window_ms > 0),
    }
    rows: list[dict[str, Any]] = []
    track_intervals: list[tuple[float, float]] = []
    track_groups = list(selected.groupby("track_id", sort=True))
    for track_id, group in track_groups:
        raw_intervals = [
            (float(row.theta_shell_low_deg), float(row.theta_shell_high_deg))
            for row in group.itertuples(index=False)
        ]
        metrics = shell_module.shell_geometry_metrics(
            raw_intervals,
            fan_low,
            fan_high,
            common_low,
            common_high,
            theta_valid_sorted,
            omega_count,
            px_per_m,
        )
        if not metrics["effective_intervals"]:
            continue
        track_intervals.extend(raw_intervals)
        rows.append(
            {
                **base,
                "shell_id": f"{frame['sar_frame_uid']}__{interface}__W{window_ms:03d}__{track_id}",
                "shell_scope": "TRACK",
                "track_id": str(track_id),
                "source_observation_count": int(len(group)),
                "source_timestamp_min_ms": int(group["timestamp_ms"].min()),
                "source_timestamp_max_ms": int(group["timestamp_ms"].max()),
                "source_has_future_observation": bool((group["timestamp_ms"] > query_ms).any()),
                "source_box_sources": ";".join(sorted(set(group["box_source"].astype(str)))),
                "source_tracker_statuses": ";".join(sorted(set(group["tracker_status"].astype(str)))),
                "source_track_tiers": ";".join(sorted(set(group["track_tier"].astype(str)))),
                "source_raw_fragment_ids": ";".join(sorted(set(group["raw_track_fragment_id"].astype(str)))),
                "source_parent_stitched_ids": ";".join(sorted(set(group["optical_person_id"].astype(str)))),
                "source_ambiguous_stitch_count_max": int(group["ambiguous_stitch_count"].max()),
                "source_accepted_parent_fraction": float(group["accepted_for_annotation_queue"].astype(bool).mean()),
                **{key: value for key, value in metrics.items() if key not in {"raw_intervals", "effective_intervals"}},
                "raw_intervals_json": json.dumps(metrics["raw_intervals"]),
                "effective_intervals_json": json.dumps(metrics["effective_intervals"]),
            }
        )
    if track_intervals:
        metrics = shell_module.shell_geometry_metrics(
            track_intervals,
            fan_low,
            fan_high,
            common_low,
            common_high,
            theta_valid_sorted,
            omega_count,
            px_per_m,
        )
        rows.append(
            {
                **base,
                "shell_id": f"{frame['sar_frame_uid']}__{interface}__W{window_ms:03d}__ALL_TRACK_UNION",
                "shell_scope": "ALL_TRACK_UNION",
                "track_id": "__ALL_TRACK_UNION__",
                "source_observation_count": int(len(selected)),
                "source_timestamp_min_ms": int(selected["timestamp_ms"].min()),
                "source_timestamp_max_ms": int(selected["timestamp_ms"].max()),
                "source_has_future_observation": bool((selected["timestamp_ms"] > query_ms).any()),
                "source_box_sources": ";".join(sorted(set(selected["box_source"].astype(str)))),
                "source_tracker_statuses": ";".join(sorted(set(selected["tracker_status"].astype(str)))),
                "source_track_tiers": ";".join(sorted(set(selected["track_tier"].astype(str)))),
                "source_raw_fragment_ids": ";".join(sorted(set(selected["raw_track_fragment_id"].astype(str)))),
                "source_parent_stitched_ids": ";".join(sorted(set(selected["optical_person_id"].astype(str)))),
                "source_ambiguous_stitch_count_max": int(selected["ambiguous_stitch_count"].max()),
                "source_accepted_parent_fraction": float(selected["accepted_for_annotation_queue"].astype(bool).mean()),
                "track_count_in_union": int(len(track_groups)),
                **{key: value for key, value in metrics.items() if key not in {"raw_intervals", "effective_intervals"}},
                "raw_intervals_json": json.dumps(metrics["raw_intervals"]),
                "effective_intervals_json": json.dumps(metrics["effective_intervals"]),
            }
        )
    return rows


def materialize_shell_candidates(
    shell_definitions: pd.DataFrame, candidates: pd.DataFrame, shell_module: Any
) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidate_groups = {uid: group.sort_values("rank").copy() for uid, group in candidates.groupby("frame_uid", sort=False)}
    candidate_parts: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []
    for shell in shell_definitions.itertuples(index=False):
        artifact_covered = shell.frame_uid in candidate_groups
        full = candidate_groups.get(shell.frame_uid, pd.DataFrame(columns=candidates.columns))
        intervals = json.loads(shell.effective_intervals_json)
        if artifact_covered:
            selected = shell_module.inside_intervals(full["theta_deg"].to_numpy(float), intervals)
            subset = full.loc[selected].copy().sort_values(["rank", "x_px", "y_px"])
            subset["shell_local_rank"] = np.arange(1, len(subset) + 1)
            subset["shell_local_percentile"] = 1.0 - (subset["shell_local_rank"] - 1) / max(len(subset), 1)
            subset["shell_id"] = shell.shell_id
            subset["shell_scope"] = shell.shell_scope
            subset["track_id"] = shell.track_id
            subset["interface_kind"] = shell.interface_kind
            subset["time_window_half_width_ms"] = shell.time_window_half_width_ms
            subset["candidate_id"] = subset.apply(lambda row: f"{row.frame_uid}__C2R{int(row['rank']):04d}", axis=1)
            candidate_parts.append(subset)
        else:
            subset = pd.DataFrame(columns=candidates.columns)
        metric_rows.append(
            {
                "run_id": shell.run_id,
                "frame_uid": shell.frame_uid,
                "frame_index": shell.frame_index,
                "interface_kind": shell.interface_kind,
                "time_window_half_width_ms": shell.time_window_half_width_ms,
                "shell_id": shell.shell_id,
                "shell_scope": shell.shell_scope,
                "track_id": shell.track_id,
                "candidate_artifact_frame_covered": bool(artifact_covered),
                "candidate_count_shell": int(len(subset)) if artifact_covered else math.nan,
                "candidate_count_full_fan": int(len(full)) if artifact_covered else math.nan,
                "candidate_burden_ratio": (
                    len(subset) / max(float(len(full)), 1.0)
                    if artifact_covered
                    else math.nan
                ),
                "effective_width_deg": shell.effective_width_deg,
                "effective_area_m2": shell.effective_area_m2,
            }
        )
    shell_candidates = pd.concat(candidate_parts, ignore_index=True) if candidate_parts else pd.DataFrame()
    return shell_candidates, pd.DataFrame(metric_rows)


def build_frame_branch_summary(shell_metrics: pd.DataFrame, shell_candidates: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, group in shell_metrics.groupby(
        ["run_id", "frame_uid", "frame_index", "interface_kind", "time_window_half_width_ms"], sort=False
    ):
        run_id, frame_uid, frame_index, interface, window_ms = keys
        tracks = group[group["shell_scope"] == "TRACK"]
        union = group[group["shell_scope"] == "ALL_TRACK_UNION"]
        artifact_covered = bool(group.iloc[0]["candidate_artifact_frame_covered"])
        union_count = (
            int(union.iloc[0]["candidate_count_shell"])
            if artifact_covered and len(union)
            else math.nan
        )
        full_count = (
            int(group.iloc[0]["candidate_count_full_fan"])
            if artifact_covered and len(group)
            else math.nan
        )
        sum_count = int(tracks["candidate_count_shell"].sum()) if artifact_covered else math.nan
        rows.append(
            {
                "run_id": run_id,
                "frame_uid": frame_uid,
                "frame_index": int(frame_index),
                "interface_kind": interface,
                "time_window_half_width_ms": int(window_ms),
                "candidate_artifact_frame_covered": artifact_covered,
                "track_shell_count": int(len(tracks)),
                "candidate_count_full_fan": full_count,
                "candidate_count_all_track_union": union_count,
                "candidate_burden_all_track_union": (
                    union_count / max(float(full_count), 1.0)
                    if artifact_covered
                    else math.nan
                ),
                "candidate_count_sum_track_branches": sum_count,
                "candidate_burden_sum_track_branches": (
                    sum_count / max(float(full_count), 1.0)
                    if artifact_covered
                    else math.nan
                ),
                "candidate_duplicate_branch_count": (
                    max(0, sum_count - union_count) if artifact_covered else math.nan
                ),
                "candidate_duplicate_fraction_of_sum": (
                    max(0, sum_count - union_count) / max(float(sum_count), 1.0)
                    if artifact_covered
                    else math.nan
                ),
                "single_track_candidate_burden_median": (
                    finite_median(tracks["candidate_burden_ratio"])
                    if artifact_covered
                    else math.nan
                ),
                "single_track_candidate_burden_min": (
                    float(tracks["candidate_burden_ratio"].min())
                    if artifact_covered and len(tracks)
                    else math.nan
                ),
                "single_track_effective_width_median_deg": finite_median(tracks["effective_width_deg"]),
                "union_effective_width_deg": float(union.iloc[0]["effective_width_deg"]) if len(union) else math.nan,
            }
        )
    return pd.DataFrame(rows)


def complete_frame_branch_summary(
    frames: list[dict[str, Any]],
    available_summary: pd.DataFrame,
    candidates: pd.DataFrame,
) -> pd.DataFrame:
    candidate_counts = candidates.groupby("frame_uid", sort=False).size().to_dict()
    universe_rows = []
    for frame in frames:
        for interface in (INTERFACE_RAW, INTERFACE_STITCHED):
            for window_ms in TIME_WINDOWS_MS:
                universe_rows.append(
                    {
                        "run_id": frame["run_id"],
                        "frame_uid": frame["sar_frame_uid"],
                        "frame_index": int(frame["sar_frame_index"]),
                        "interface_kind": interface,
                        "time_window_half_width_ms": int(window_ms),
                        "candidate_artifact_frame_covered_universe": bool(
                            frame["sar_frame_uid"] in candidate_counts
                        ),
                        "candidate_count_full_fan_universe": int(
                            candidate_counts.get(frame["sar_frame_uid"], 0)
                        ),
                    }
                )
    keys = ["run_id", "frame_uid", "frame_index", "interface_kind", "time_window_half_width_ms"]
    completed = pd.DataFrame(universe_rows).merge(available_summary, on=keys, how="left")
    completed["shell_available"] = completed["track_shell_count"].notna()
    completed["candidate_artifact_frame_covered"] = (
        completed["candidate_artifact_frame_covered"].eq(True)
        | completed["candidate_artifact_frame_covered_universe"].astype(bool)
    )
    covered = completed["candidate_artifact_frame_covered"]
    completed.loc[covered, "candidate_count_full_fan"] = completed.loc[
        covered, "candidate_count_full_fan"
    ].fillna(completed.loc[covered, "candidate_count_full_fan_universe"])
    completed.loc[~covered, "candidate_count_full_fan"] = math.nan
    completed["candidate_count_full_fan"] = completed["candidate_count_full_fan"].astype("Int64")
    completed = completed.drop(
        columns=[
            "candidate_count_full_fan_universe",
            "candidate_artifact_frame_covered_universe",
        ]
    )
    completed["track_shell_count"] = completed["track_shell_count"].fillna(0).astype(int)
    for column in (
        "candidate_count_all_track_union",
        "candidate_count_sum_track_branches",
        "candidate_duplicate_branch_count",
    ):
        completed.loc[covered, column] = completed.loc[covered, column].fillna(0)
        completed.loc[~covered, column] = math.nan
        completed[column] = completed[column].astype("Int64")
    completed["track_prior_state"] = np.where(
        completed["shell_available"], "TRACK_SHELL_AVAILABLE", "TRACK_SHELL_UNAVAILABLE"
    )
    completed["candidate_burden_all_track_union_zero_if_shell_unavailable"] = np.where(
        covered, completed["candidate_burden_all_track_union"].fillna(0.0), math.nan
    )
    completed["candidate_burden_sum_track_branches_zero_if_shell_unavailable"] = np.where(
        covered, completed["candidate_burden_sum_track_branches"].fillna(0.0), math.nan
    )
    return completed.sort_values(keys).reset_index(drop=True)


def build_shell_overlap_table(
    shell_definitions: pd.DataFrame, shell_candidates: pd.DataFrame, shell_module: Any
) -> pd.DataFrame:
    candidate_sets = {
        shell_id: set(group["candidate_id"].astype(str))
        for shell_id, group in shell_candidates.groupby("shell_id", sort=False)
    }
    rows: list[dict[str, Any]] = []
    tracks = shell_definitions[shell_definitions["shell_scope"] == "TRACK"]
    group_columns = ["run_id", "frame_uid", "frame_index", "interface_kind", "time_window_half_width_ms"]
    for keys, group in tracks.groupby(group_columns, sort=False):
        records = list(group.itertuples(index=False))
        for left_index in range(len(records) - 1):
            left = records[left_index]
            left_intervals = json.loads(left.effective_intervals_json)
            for right in records[left_index + 1 :]:
                right_intervals = json.loads(right.effective_intervals_json)
                left_set = candidate_sets.get(left.shell_id, set())
                right_set = candidate_sets.get(right.shell_id, set())
                rows.append(
                    {
                        "run_id": keys[0],
                        "frame_uid": keys[1],
                        "frame_index": int(keys[2]),
                        "interface_kind": keys[3],
                        "time_window_half_width_ms": int(keys[4]),
                        "left_track_id": left.track_id,
                        "right_track_id": right.track_id,
                        "left_shell_id": left.shell_id,
                        "right_shell_id": right.shell_id,
                        "angular_overlap_width_deg": shell_module.interval_overlap_width(left_intervals, right_intervals),
                        "angular_jaccard": shell_module.angular_jaccard(left_intervals, right_intervals),
                        "shared_candidate_count": int(len(left_set & right_set)),
                        "candidate_jaccard": len(left_set & right_set) / max(float(len(left_set | right_set)), 1.0),
                    }
                )
    return pd.DataFrame(rows)


def evaluate_references_against_shells(
    references: pd.DataFrame,
    shell_definitions: pd.DataFrame,
    shell_candidates: pd.DataFrame,
) -> pd.DataFrame:
    shell_groups = {shell_id: group.sort_values("shell_local_rank") for shell_id, group in shell_candidates.groupby("shell_id", sort=False)}
    shell_by_frame = {uid: group for uid, group in shell_definitions.groupby("frame_uid", sort=False)}
    rows: list[dict[str, Any]] = []
    for ref in references.itertuples(index=False):
        shells = shell_by_frame.get(ref.frame_uid, pd.DataFrame(columns=shell_definitions.columns))
        for shell in shells.itertuples(index=False):
            intervals = json.loads(shell.effective_intervals_json)
            inside = interval_distance(float(ref.reference_theta_deg), intervals) <= 1e-12
            candidates = shell_groups.get(shell.shell_id, pd.DataFrame(columns=shell_candidates.columns))
            if len(candidates):
                distances = np.hypot(
                    candidates["x_px"].to_numpy(float) - float(ref.reference_x_px),
                    candidates["y_px"].to_numpy(float) - float(ref.reference_y_px),
                ) / float(shell.px_per_m)
                nearest_index = int(np.argmin(distances))
                nearest = candidates.iloc[nearest_index]
                within = np.flatnonzero(distances <= PEAK_REFERENCE_RADIUS_M)
                best = candidates.iloc[int(within[np.argmin(candidates.iloc[within]["shell_local_rank"].to_numpy(int))])] if len(within) else None
            else:
                distances = np.asarray([], dtype=float)
                nearest = best = None
            rows.append(
                {
                    "run_id": ref.run_id,
                    "frame_uid": ref.frame_uid,
                    "frame_index": int(ref.frame_index),
                    "target_id": ref.target_id,
                    "interface_kind": shell.interface_kind,
                    "time_window_half_width_ms": int(shell.time_window_half_width_ms),
                    "shell_id": shell.shell_id,
                    "shell_scope": shell.shell_scope,
                    "track_id": shell.track_id,
                    "reference_inside_shell": bool(inside),
                    "reference_angular_distance_to_shell_deg": interval_distance(float(ref.reference_theta_deg), intervals),
                    "candidate_count_shell": int(len(candidates)),
                    "candidate_burden_ratio": len(candidates) / max(float(ref.candidate_count_frame), 1.0),
                    "nearest_candidate_distance_m": float(distances.min()) if len(distances) else math.nan,
                    "nearest_candidate_global_rank": int(nearest["rank"]) if nearest is not None else math.nan,
                    "nearest_candidate_local_rank": int(nearest["shell_local_rank"]) if nearest is not None else math.nan,
                    "candidate_present_within_0p8m": bool(best is not None),
                    "best_candidate_id_within_0p8m": str(best["candidate_id"]) if best is not None else "",
                    "best_candidate_global_rank_within_0p8m": int(best["rank"]) if best is not None else math.nan,
                    "best_candidate_local_rank_within_0p8m": int(best["shell_local_rank"]) if best is not None else math.nan,
                    "reference_used_for_runtime_shell": False,
                }
            )
    return pd.DataFrame(rows)


def summarize_reference_track_outputs(pair_evaluation: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_columns = ["run_id", "frame_uid", "frame_index", "target_id", "interface_kind", "time_window_half_width_ms"]
    for keys, group in pair_evaluation.groupby(group_columns, sort=False):
        tracks = group[group["shell_scope"] == "TRACK"]
        union = group[group["shell_scope"] == "ALL_TRACK_UNION"]
        covering = tracks[tracks["reference_inside_shell"].astype(bool)]
        retaining = tracks[tracks["candidate_present_within_0p8m"].astype(bool)]
        rows.append(
            {
                "run_id": keys[0],
                "frame_uid": keys[1],
                "frame_index": int(keys[2]),
                "target_id": keys[3],
                "interface_kind": keys[4],
                "time_window_half_width_ms": int(keys[5]),
                "track_shell_count": int(len(tracks)),
                "any_track_reference_coverage": bool(len(covering)),
                "reference_covering_track_count": int(len(covering)),
                "any_track_candidate_retention_0p8m": bool(len(retaining)),
                "candidate_retaining_track_count": int(len(retaining)),
                "best_track_local_rank_0p8m_offline_eval": float(retaining["best_candidate_local_rank_within_0p8m"].min()) if len(retaining) else math.nan,
                "best_track_global_rank_0p8m_offline_eval": float(retaining["best_candidate_global_rank_within_0p8m"].min()) if len(retaining) else math.nan,
                "median_covering_track_candidate_burden": finite_median(covering["candidate_burden_ratio"]),
                "union_reference_coverage": bool(union.iloc[0]["reference_inside_shell"]) if len(union) else False,
                "union_candidate_retention_0p8m": bool(union.iloc[0]["candidate_present_within_0p8m"]) if len(union) else False,
                "union_local_rank_0p8m": float(union.iloc[0]["best_candidate_local_rank_within_0p8m"]) if len(union) else math.nan,
                "union_candidate_burden": float(union.iloc[0]["candidate_burden_ratio"]) if len(union) else math.nan,
                "manual_track_identity_used_for_selection": False,
            }
        )
    return pd.DataFrame(rows)


def complete_reference_track_outputs(
    references: pd.DataFrame,
    available_summary: pd.DataFrame,
) -> pd.DataFrame:
    universe_rows = []
    reference_columns = ["run_id", "frame_uid", "frame_index", "target_id"]
    reference_universe = references[reference_columns].drop_duplicates()
    for ref in reference_universe.itertuples(index=False):
        for interface in (INTERFACE_RAW, INTERFACE_STITCHED):
            for window_ms in TIME_WINDOWS_MS:
                universe_rows.append(
                    {
                        "run_id": ref.run_id,
                        "frame_uid": ref.frame_uid,
                        "frame_index": int(ref.frame_index),
                        "target_id": ref.target_id,
                        "interface_kind": interface,
                        "time_window_half_width_ms": int(window_ms),
                    }
                )
    keys = reference_columns + ["interface_kind", "time_window_half_width_ms"]
    completed = pd.DataFrame(universe_rows).merge(available_summary, on=keys, how="left")
    completed["optical_track_prior_available"] = completed["track_shell_count"].notna()
    for column in (
        "track_shell_count",
        "reference_covering_track_count",
        "candidate_retaining_track_count",
    ):
        completed[column] = completed[column].fillna(0).astype(int)
    for column in (
        "any_track_reference_coverage",
        "any_track_candidate_retention_0p8m",
        "union_reference_coverage",
        "union_candidate_retention_0p8m",
    ):
        completed[column] = completed[column].eq(True)
    completed["manual_track_identity_used_for_selection"] = False
    completed["track_prior_state"] = np.where(
        completed["optical_track_prior_available"],
        "TRACK_SHELL_AVAILABLE",
        "TRACK_SHELL_UNAVAILABLE",
    )
    return completed.sort_values(keys).reset_index(drop=True)


def build_offline_one_to_one_assignments(pair_evaluation: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_columns = ["run_id", "frame_uid", "frame_index", "interface_kind", "time_window_half_width_ms"]
    tracks_only = pair_evaluation[pair_evaluation["shell_scope"] == "TRACK"]
    for keys, group in tracks_only.groupby(group_columns, sort=False):
        references = sorted(group["target_id"].astype(str).unique())
        tracks = sorted(group["track_id"].astype(str).unique())
        if not references or not tracks:
            continue
        cost = np.full((len(references), len(tracks)), 1e6, dtype=float)
        lookup = group.set_index(["target_id", "track_id"])
        for i, target_id in enumerate(references):
            for j, track_id in enumerate(tracks):
                row = lookup.loc[(target_id, track_id)]
                distance = float(row["reference_angular_distance_to_shell_deg"])
                cost[i, j] = distance + (0.0 if bool(row["reference_inside_shell"]) else 1000.0)
        row_indices, column_indices = linear_sum_assignment(cost)
        for i, j in zip(row_indices.tolist(), column_indices.tolist()):
            source = lookup.loc[(references[i], tracks[j])]
            rows.append(
                {
                    "run_id": keys[0],
                    "frame_uid": keys[1],
                    "frame_index": int(keys[2]),
                    "interface_kind": keys[3],
                    "time_window_half_width_ms": int(keys[4]),
                    "target_id": references[i],
                    "assigned_track_id_offline": tracks[j],
                    "assignment_reference_inside_shell": bool(source["reference_inside_shell"]),
                    "assignment_angular_distance_deg": float(source["reference_angular_distance_to_shell_deg"]),
                    "assignment_candidate_present_0p8m": bool(source["candidate_present_within_0p8m"]),
                    "assignment_candidate_local_rank_0p8m": source["best_candidate_local_rank_within_0p8m"],
                    "assignment_semantics": "OFFLINE_ONE_TO_ONE_GEOMETRIC_EVALUATION_NOT_RUNTIME_ID_SELECTION",
                }
            )
    return pd.DataFrame(rows)


def complete_offline_one_to_one_assignments(
    references: pd.DataFrame,
    assignments: pd.DataFrame,
    reference_track_summary: pd.DataFrame,
) -> pd.DataFrame:
    universe_rows = []
    for ref in references[["run_id", "frame_uid", "frame_index", "target_id"]].drop_duplicates().itertuples(index=False):
        for interface in (INTERFACE_RAW, INTERFACE_STITCHED):
            for window_ms in TIME_WINDOWS_MS:
                universe_rows.append(
                    {
                        "run_id": ref.run_id,
                        "frame_uid": ref.frame_uid,
                        "frame_index": int(ref.frame_index),
                        "target_id": ref.target_id,
                        "interface_kind": interface,
                        "time_window_half_width_ms": int(window_ms),
                    }
                )
    keys = [
        "run_id",
        "frame_uid",
        "frame_index",
        "target_id",
        "interface_kind",
        "time_window_half_width_ms",
    ]
    completed = pd.DataFrame(universe_rows).merge(assignments, on=keys, how="left")
    availability = reference_track_summary[
        keys + ["optical_track_prior_available", "track_shell_count"]
    ]
    completed = completed.merge(availability, on=keys, how="left")
    completed["optical_track_prior_available"] = completed[
        "optical_track_prior_available"
    ].eq(True)
    completed["one_to_one_assignment_available"] = completed[
        "assigned_track_id_offline"
    ].notna()
    for column in (
        "assignment_reference_inside_shell",
        "assignment_candidate_present_0p8m",
    ):
        completed[column] = completed[column].eq(True)
    completed["assignment_state"] = "UNASSIGNED_INSUFFICIENT_TRACK_BRANCHES"
    completed.loc[
        ~completed["optical_track_prior_available"], "assignment_state"
    ] = "TRACK_PRIOR_UNAVAILABLE"
    completed.loc[
        completed["one_to_one_assignment_available"]
        & ~completed["assignment_reference_inside_shell"],
        "assignment_state",
    ] = "ASSIGNED_REFERENCE_OUTSIDE_SHELL"
    completed.loc[
        completed["one_to_one_assignment_available"]
        & completed["assignment_reference_inside_shell"],
        "assignment_state",
    ] = "ASSIGNED_REFERENCE_INSIDE_SHELL"
    completed["assignment_semantics"] = (
        "OFFLINE_ONE_TO_ONE_GEOMETRIC_EVALUATION_NOT_RUNTIME_ID_SELECTION"
    )
    return completed.sort_values(keys).reset_index(drop=True)


def nearest_region_label(labels: np.ndarray, x: float, y: float, radius_px: float) -> tuple[int, float, bool]:
    xi = int(round(x))
    yi = int(round(y))
    if not (0 <= xi < labels.shape[1] and 0 <= yi < labels.shape[0]):
        return 0, math.inf, False
    direct = int(labels[yi, xi])
    if direct > 0:
        return direct, 0.0, True
    radius = int(math.ceil(radius_px))
    x0, x1 = max(0, xi - radius), min(labels.shape[1], xi + radius + 1)
    y0, y1 = max(0, yi - radius), min(labels.shape[0], yi + radius + 1)
    crop = labels[y0:y1, x0:x1]
    ys, xs = np.where(crop > 0)
    if not len(xs):
        return 0, math.inf, False
    distances = np.hypot(xs + x0 - x, ys + y0 - y)
    index = int(np.argmin(distances))
    if float(distances[index]) > radius_px:
        return 0, float(distances[index]), False
    return int(crop[ys[index], xs[index]]), float(distances[index]), False


def evaluate_references_against_regions(
    references: pd.DataFrame,
    regions: pd.DataFrame,
    frame_px_per_m: dict[str, float],
    reference_conditions: pd.DataFrame,
) -> pd.DataFrame:
    descriptor_lookup = regions.set_index(["frame_uid", "percentile_tag", "region_label"]).to_dict("index")
    condition_lookup = reference_conditions.set_index(["frame_uid", "target_id"]).to_dict("index")
    rows: list[dict[str, Any]] = []
    for frame_uid, frame_refs in references.groupby("frame_uid", sort=False):
        archive = np.load(MASK_DIR / f"{frame_uid}.npz")
        px_per_m = frame_px_per_m[frame_uid]
        for ref in frame_refs.itertuples(index=False):
            condition = condition_lookup.get((frame_uid, ref.target_id), {})
            peak_present = bool(np.isfinite(float(ref.best_rank_within_0_80m)))
            for level in PERCENTILE_LEVELS:
                tag = PERCENTILE_TAGS[level]
                labels = archive[tag]
                label, distance_px, direct = nearest_region_label(
                    labels,
                    float(ref.reference_x_px),
                    float(ref.reference_y_px),
                    REFERENCE_REGION_RADIUS_M * px_per_m,
                )
                descriptor = descriptor_lookup.get((frame_uid, tag, label), {}) if label else {}
                rows.append(
                    {
                        "run_id": ref.run_id,
                        "frame_uid": frame_uid,
                        "frame_index": int(ref.frame_index),
                        "target_id": ref.target_id,
                        "percentile_level": level,
                        "percentile_tag": tag,
                        "reference_support_status": ref.reference_support_status,
                        "reference_C2_percentile_existing": condition.get("C2_percentile_in_frame_valid_region", math.nan),
                        "peak_present_within_0p8m": peak_present,
                        "nearest_peak_distance_m_existing": ref.nearest_candidate_distance_m,
                        "nearest_peak_rank_existing": ref.nearest_candidate_rank,
                        "region_near_reference_0p30m": bool(label),
                        "reference_center_directly_inside_region": bool(direct),
                        "nearest_region_distance_m": distance_px / px_per_m if np.isfinite(distance_px) else math.nan,
                        "nearest_region_label": int(label),
                        "nearest_region_id": descriptor.get("region_id", ""),
                        "nearest_region_area_m2": descriptor.get("area_m2", math.nan),
                        "nearest_region_major_extent_m": descriptor.get("major_extent_m", math.nan),
                        "nearest_region_minor_extent_m": descriptor.get("minor_extent_m", math.nan),
                        "nearest_region_elongation": descriptor.get("elongation", math.nan),
                        "nearest_region_structure_state": descriptor.get("structure_state", "NO_NEAR_REGION"),
                        "nearest_region_touches_observable_boundary": descriptor.get("touches_observable_boundary", False),
                        "nearest_region_has_truncated_support": descriptor.get("has_truncated_support", False),
                        "manual_reference_used_for_region_generation": False,
                    }
                )
    output = pd.DataFrame(rows)
    near = output[output["nearest_region_id"].astype(str).ne("")]
    shared_counts = near.groupby(["frame_uid", "percentile_tag", "nearest_region_id"])["target_id"].nunique()
    output["shared_region_reference_count"] = output.apply(
        lambda row: int(shared_counts.get((row.frame_uid, row.percentile_tag, row.nearest_region_id), 0))
        if row.nearest_region_id
        else 0,
        axis=1,
    )
    output["shared_region_flag"] = output["shared_region_reference_count"] >= 2
    output["observability_state"] = output["reference_support_status"].map(
        {"FULL": "FULL", "TRUNCATED": "CENSORED_TRUNCATED", "INVALID": "CENSORED_OR_UNOBSERVABLE"}
    ).fillna("CENSORED_OR_UNOBSERVABLE")
    presence_level = (
        output.loc[output["region_near_reference_0p30m"].astype(bool)]
        .groupby(["frame_uid", "target_id"], sort=False)["percentile_level"]
        .max()
    )
    output["highest_near_region_percentile_level"] = output.apply(
        lambda row: presence_level.get((row.frame_uid, row.target_id), math.nan), axis=1
    )
    output["superlevel_presence_state"] = "NO_Q090_REGION_NEAR_REFERENCE"
    output.loc[
        output["highest_near_region_percentile_level"].ge(0.90),
        "superlevel_presence_state",
    ] = "Q090_ONLY_REGION_PRESENT"
    output.loc[
        output["highest_near_region_percentile_level"].ge(0.95),
        "superlevel_presence_state",
    ] = "Q095_REGION_PRESENT"
    output.loc[
        output["highest_near_region_percentile_level"].ge(0.975),
        "superlevel_presence_state",
    ] = "Q0975_REGION_PRESENT"
    primary = output["percentile_level"].eq(PRIMARY_PERCENTILE)
    output["representation_state"] = "SENSITIVITY_ONLY"
    output.loc[primary & output["peak_present_within_0p8m"].astype(bool), "representation_state"] = "PEAK_PRESENT"
    output.loc[
        primary
        & ~output["peak_present_within_0p8m"].astype(bool)
        & output["region_near_reference_0p30m"].astype(bool),
        "representation_state",
    ] = "PEAK_MISSING_REGION_PRESENT"
    output.loc[
        primary
        & ~output["peak_present_within_0p8m"].astype(bool)
        & ~output["region_near_reference_0p30m"].astype(bool),
        "representation_state",
    ] = "PEAK_MISSING_NO_Q95_REGION_NEAR"
    return output


def evaluate_observation_entities_against_regions(
    observations: pd.DataFrame,
    regions: pd.DataFrame,
    frame_px_per_m: dict[str, float],
) -> pd.DataFrame:
    allowed_kinds = {
        "PERSON_REFERENCE",
        "FIXED_OFFSET_CONTROL",
        "GEOMETRY_MATCHED_CONTROL",
        "LOCAL_COMPETING_CONTROL",
    }
    points = observations[observations["entity_kind"].isin(allowed_kinds)].copy()
    descriptor_lookup = regions.set_index(
        ["frame_uid", "percentile_tag", "region_label"]
    ).to_dict("index")
    rows: list[dict[str, Any]] = []
    for frame_uid, frame_points in points.groupby("frame_uid", sort=False):
        with np.load(MASK_DIR / f"{frame_uid}.npz") as archive:
            px_per_m = frame_px_per_m[str(frame_uid)]
            for level in PERCENTILE_LEVELS:
                tag = PERCENTILE_TAGS[level]
                labels = archive[tag]
                for point in frame_points.itertuples(index=False):
                    label, distance_px, direct = nearest_region_label(
                        labels,
                        float(point.x_px),
                        float(point.y_px),
                        REFERENCE_REGION_RADIUS_M * px_per_m,
                    )
                    descriptor = (
                        descriptor_lookup.get((frame_uid, tag, label), {})
                        if label
                        else {}
                    )
                    rows.append(
                        {
                            "run_id": point.run_id,
                            "frame_uid": frame_uid,
                            "frame_index": int(point.frame_index),
                            "entity_id": point.entity_id,
                            "entity_kind": point.entity_kind,
                            "target_id_offline_if_applicable": getattr(
                                point, "target_id", ""
                            ),
                            "control_kind": getattr(point, "control_kind", ""),
                            "percentile_level": level,
                            "percentile_tag": tag,
                            "region_near_entity_0p30m": bool(label),
                            "entity_directly_inside_region": bool(direct),
                            "nearest_region_distance_m": (
                                distance_px / px_per_m
                                if np.isfinite(distance_px)
                                else math.nan
                            ),
                            "nearest_region_id": descriptor.get("region_id", ""),
                            "nearest_region_structure_state": descriptor.get(
                                "structure_state", "NO_NEAR_REGION"
                            ),
                            "nearest_region_touches_observable_boundary": descriptor.get(
                                "touches_observable_boundary", False
                            ),
                            "nearest_region_has_truncated_support": descriptor.get(
                                "has_truncated_support", False
                            ),
                            "manual_or_gt_derived_entity_used_for_region_generation": False,
                            "evaluation_semantics": "POSTHOC_LOCATION_EVALUATION_AFTER_GT_BLIND_REGION_GENERATION",
                        }
                    )
    return pd.DataFrame(rows)


def summarize_observation_entity_region_coverage(
    evaluation: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_columns = ["percentile_level", "percentile_tag", "entity_kind", "control_kind"]
    normalized = evaluation.copy()
    normalized["control_kind"] = normalized["control_kind"].fillna("").astype(str)
    for keys, group in normalized.groupby(group_columns, dropna=False, sort=False):
        rows.append(
            {
                "percentile_level": float(keys[0]),
                "percentile_tag": keys[1],
                "entity_kind": keys[2],
                "control_kind": keys[3],
                "entity_rows": int(len(group)),
                "direct_inside_region_fraction": bool_fraction(
                    group["entity_directly_inside_region"]
                ),
                "region_near_0p30m_fraction": bool_fraction(
                    group["region_near_entity_0p30m"]
                ),
                "comparison_semantics": "DEVELOPMENT_CORPUS_POSTHOC_LOCATION_COMPARISON_NOT_BLIND_VALIDATION",
            }
        )
    return pd.DataFrame(rows)


def compare_recomputed_candidates(
    frame: dict[str, Any],
    recomputed: list[dict[str, Any]],
    expected: pd.DataFrame,
) -> dict[str, Any]:
    expected = expected.sort_values("rank").reset_index(drop=True)
    actual = pd.DataFrame(recomputed)
    if len(actual):
        actual = actual.sort_values("rank").reset_index(drop=True)
    same_count = len(actual) == len(expected)
    comparable = min(len(actual), len(expected))
    if comparable:
        actual_slice = actual.iloc[:comparable]
        expected_slice = expected.iloc[:comparable]
        coordinate_error = np.hypot(
            actual_slice["x_px"].to_numpy(float) - expected_slice["x_px"].to_numpy(float),
            actual_slice["y_px"].to_numpy(float) - expected_slice["y_px"].to_numpy(float),
        )
        score_error = np.abs(
            actual_slice["score"].to_numpy(float) - expected_slice["score"].to_numpy(float)
        )
        support_error = np.abs(
            actual_slice["support_fraction"].to_numpy(float)
            - expected_slice["support_fraction"].to_numpy(float)
        )
        rank_match = bool(
            np.array_equal(
                actual_slice["rank"].to_numpy(int), expected_slice["rank"].to_numpy(int)
            )
        )
        support_status_match = bool(
            np.array_equal(
                actual_slice["support_status"].astype(str).to_numpy(),
                expected_slice["support_status"].astype(str).to_numpy(),
            )
        )
        max_coordinate_error_px = float(np.max(coordinate_error))
        max_score_abs_error = float(np.max(score_error))
        max_support_fraction_abs_error = float(np.max(support_error))
    else:
        rank_match = support_status_match = same_count
        max_coordinate_error_px = max_score_abs_error = max_support_fraction_abs_error = 0.0
    all_match = bool(
        same_count
        and rank_match
        and support_status_match
        and max_coordinate_error_px <= 1e-12
        and max_score_abs_error <= 1e-7
        and max_support_fraction_abs_error <= 1e-7
    )
    return {
        "run_id": frame["run_id"],
        "frame_uid": frame["sar_frame_uid"],
        "frame_index": int(frame["sar_frame_index"]),
        "expected_candidate_count": int(len(expected)),
        "recomputed_candidate_count": int(len(actual)),
        "candidate_count_match": bool(same_count),
        "rank_match": rank_match,
        "support_status_match": support_status_match,
        "max_coordinate_error_px": max_coordinate_error_px,
        "max_score_abs_error": max_score_abs_error,
        "max_support_fraction_abs_error": max_support_fraction_abs_error,
        "all_candidate_fields_match": all_match,
        "manual_reference_used": False,
    }


def annotate_candidate_parity_coverage(
    parity: pd.DataFrame, covered_frame_uids: set[str]
) -> pd.DataFrame:
    output = parity.copy()
    output["candidate_artifact_frame_covered"] = output["frame_uid"].astype(str).isin(
        covered_frame_uids
    )
    output["covered_frame_candidate_fields_match"] = pd.Series(
        pd.NA, index=output.index, dtype="boolean"
    )
    covered = output["candidate_artifact_frame_covered"].astype(bool)
    output.loc[covered, "covered_frame_candidate_fields_match"] = output.loc[
        covered, "all_candidate_fields_match"
    ].astype(bool)
    output["parity_status"] = "NO_LEGACY_CANDIDATE_ARTIFACT_FOR_FRAME"
    output.loc[
        covered & output["all_candidate_fields_match"].astype(bool), "parity_status"
    ] = "COVERED_FRAME_EXACT_MATCH"
    output.loc[
        covered & ~output["all_candidate_fields_match"].astype(bool), "parity_status"
    ] = "COVERED_FRAME_MISMATCH"
    return output


def attach_peak_counts_to_regions(
    regions: pd.DataFrame, candidates: pd.DataFrame, frame_px_per_m: dict[str, float]
) -> pd.DataFrame:
    output = regions.copy()
    if output.empty:
        output["accepted_peak_count"] = pd.Series(dtype=int)
        output["accepted_peak_ranks"] = pd.Series(dtype=str)
        return output
    if set(output["frame_uid"].astype(str)) - set(frame_px_per_m):
        raise RuntimeError("region frame missing pixel-scale metadata")
    candidate_groups = {
        str(frame_uid): group.sort_values("rank")
        for frame_uid, group in candidates.groupby("frame_uid", sort=False)
    }
    peak_lookup: dict[tuple[str, str, int], list[int]] = defaultdict(list)
    for frame_uid, frame_regions in output.groupby("frame_uid", sort=False):
        frame_uid = str(frame_uid)
        frame_candidates = candidate_groups.get(
            frame_uid, pd.DataFrame(columns=candidates.columns)
        )
        with np.load(MASK_DIR / f"{frame_uid}.npz") as archive:
            for percentile_tag in frame_regions["percentile_tag"].astype(str).unique():
                labels = archive[percentile_tag]
                for candidate in frame_candidates.itertuples(index=False):
                    x = int(round(candidate.x_px))
                    y = int(round(candidate.y_px))
                    if not (0 <= x < labels.shape[1] and 0 <= y < labels.shape[0]):
                        continue
                    region_label = int(labels[y, x])
                    if region_label > 0:
                        peak_lookup[(frame_uid, percentile_tag, region_label)].append(
                            int(candidate.rank)
                        )
    region_keys = zip(
        output["frame_uid"].astype(str),
        output["percentile_tag"].astype(str),
        output["region_label"].astype(int),
    )
    region_ranks = [sorted(peak_lookup.get(key, [])) for key in region_keys]
    output["accepted_peak_count"] = [len(values) for values in region_ranks]
    output["accepted_peak_ranks"] = [";".join(map(str, values)) for values in region_ranks]
    return output


def build_region_shell_intersections(
    regions: pd.DataFrame, shell_definitions: pd.DataFrame, shell_module: Any
) -> pd.DataFrame:
    primary_regions = regions[regions["percentile_level"] == PRIMARY_PERCENTILE]
    primary_shells = shell_definitions[
        (shell_definitions["time_window_half_width_ms"] == 250)
        & (shell_definitions["shell_scope"] == "TRACK")
    ]
    shells_by_frame = {uid: group for uid, group in primary_shells.groupby("frame_uid", sort=False)}
    rows: list[dict[str, Any]] = []
    for region in primary_regions.itertuples(index=False):
        shells = shells_by_frame.get(region.frame_uid, pd.DataFrame(columns=primary_shells.columns))
        region_interval = [(float(region.theta_min_deg), float(region.theta_max_deg))]
        for shell in shells.itertuples(index=False):
            intervals = json.loads(shell.effective_intervals_json)
            overlap = shell_module.interval_overlap_width(region_interval, intervals)
            if overlap <= 0:
                continue
            rows.append(
                {
                    "run_id": region.run_id,
                    "frame_uid": region.frame_uid,
                    "frame_index": region.frame_index,
                    "region_id": region.region_id,
                    "region_structure_state": region.structure_state,
                    "interface_kind": shell.interface_kind,
                    "track_id": shell.track_id,
                    "shell_id": shell.shell_id,
                    "angular_extent_overlap_deg": overlap,
                    "region_theta_extent_deg": float(region.theta_max_deg - region.theta_min_deg),
                    "intersection_semantics": "COARSE_ANGULAR_EXTENT_INTERSECTION_NOT_IDENTITY_OR_FINAL_LOCALIZATION",
                }
            )
    return pd.DataFrame(rows)


def build_time_window_summary(
    frame_summary: pd.DataFrame, reference_summary: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for interface in (INTERFACE_RAW, INTERFACE_STITCHED):
        for window_ms in TIME_WINDOWS_MS:
            frames = frame_summary[
                (frame_summary["interface_kind"] == interface)
                & (frame_summary["time_window_half_width_ms"] == window_ms)
            ]
            refs = reference_summary[
                (reference_summary["interface_kind"] == interface)
                & (reference_summary["time_window_half_width_ms"] == window_ms)
            ]
            available_frames = frames[frames["shell_available"].astype(bool)]
            candidate_frames = frames[frames["candidate_artifact_frame_covered"].astype(bool)]
            available_candidate_frames = candidate_frames[
                candidate_frames["shell_available"].astype(bool)
            ]
            available_refs = refs[refs["optical_track_prior_available"].astype(bool)]
            rows.append(
                {
                    "interface_kind": interface,
                    "time_window_half_width_ms": window_ms,
                    "frame_count_total": int(len(frames)),
                    "frame_count_with_shell": int(len(available_frames)),
                    "frame_shell_availability_fraction": bool_fraction(frames["shell_available"]),
                    "track_shell_count_median_given_available": finite_median(available_frames["track_shell_count"]),
                    "candidate_artifact_frame_count": int(len(candidate_frames)),
                    "candidate_artifact_frame_fraction": bool_fraction(frames["candidate_artifact_frame_covered"]),
                    "candidate_artifact_frame_count_with_shell": int(len(available_candidate_frames)),
                    "candidate_artifact_shell_availability_fraction": bool_fraction(candidate_frames["shell_available"]),
                    "single_track_candidate_burden_median_given_artifact_and_shell": finite_median(available_candidate_frames["single_track_candidate_burden_median"]),
                    "all_track_union_candidate_burden_median_given_artifact_and_shell": finite_median(available_candidate_frames["candidate_burden_all_track_union"]),
                    "sum_track_branch_burden_median_given_artifact_and_shell": finite_median(available_candidate_frames["candidate_burden_sum_track_branches"]),
                    "duplicate_branch_fraction_median_given_artifact_and_shell": finite_median(available_candidate_frames["candidate_duplicate_fraction_of_sum"]),
                    "all_track_union_candidate_burden_mean_on_artifact_frames_zero_if_shell_unavailable": float(
                        candidate_frames["candidate_burden_all_track_union_zero_if_shell_unavailable"].mean()
                    ) if len(candidate_frames) else math.nan,
                    "reference_count_total": int(len(refs)),
                    "reference_count_with_track_prior": int(len(available_refs)),
                    "reference_track_prior_availability_fraction": bool_fraction(refs["optical_track_prior_available"]),
                    "reference_any_track_coverage": bool_fraction(refs["any_track_reference_coverage"]),
                    "reference_any_track_candidate_retention_0p8m": bool_fraction(refs["any_track_candidate_retention_0p8m"]),
                    "reference_any_track_coverage_given_prior_available": bool_fraction(available_refs["any_track_reference_coverage"]),
                    "reference_any_track_candidate_retention_0p8m_given_prior_available": bool_fraction(available_refs["any_track_candidate_retention_0p8m"]),
                    "reference_covering_track_count_median_given_available": finite_median(available_refs["reference_covering_track_count"]),
                    "best_track_local_rank_median_offline_eval_given_available": finite_median(available_refs["best_track_local_rank_0p8m_offline_eval"]),
                    "union_local_rank_median_given_available": finite_median(available_refs["union_local_rank_0p8m"]),
                }
            )
    return pd.DataFrame(rows)


def build_legacy_union_parity(
    explorer_frames: list[dict[str, Any]],
    shell_definitions: pd.DataFrame,
    shell_module: Any,
) -> pd.DataFrame:
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    explorer = json.loads(text[text.index("{") : text.rindex("}") + 1])
    registry, _ = shell_module.build_optical_registry(explorer)
    matched = pd.read_csv(MATCHED_SHELL_CSV)
    matched = matched[matched["shell_kind"] == "TRUE"].set_index("frame_uid")
    new_union = shell_definitions[
        (shell_definitions["interface_kind"] == INTERFACE_STITCHED)
        & (shell_definitions["time_window_half_width_ms"] == 250)
        & (shell_definitions["shell_scope"] == "ALL_TRACK_UNION")
    ].set_index("frame_uid")
    rows = []
    for frame in explorer_frames:
        uid = frame["sar_frame_uid"]
        legacy_intervals = shell_module.union_intervals(registry[uid]["window_intervals"])
        if uid not in matched.index:
            rows.append(
                {
                    "frame_uid": uid,
                    "prior_true_shell_available": False,
                    "legacy_recomputed_raw_interval_match": not legacy_intervals,
                    "new_stitched_union_available": uid in new_union.index,
                    "new_stitched_raw_interval_match": False,
                    "new_stitched_effective_interval_match": False,
                }
            )
            continue
        prior = matched.loc[uid]
        expected_raw = json.loads(prior["raw_intervals_json"])
        expected_effective = json.loads(prior["effective_intervals_json"])
        new_available = uid in new_union.index
        if new_available:
            current = new_union.loc[uid]
            current_raw = json.loads(current["raw_intervals_json"])
            current_effective = json.loads(current["effective_intervals_json"])
        else:
            current_raw = []
            current_effective = []
        rows.append(
            {
                "frame_uid": uid,
                "prior_true_shell_available": True,
                "legacy_recomputed_raw_interval_match": intervals_close(
                    legacy_intervals, expected_raw, atol=1e-4
                ),
                "new_stitched_union_available": bool(new_available),
                "new_stitched_raw_interval_match": intervals_close(
                    current_raw, expected_raw, atol=1e-4
                ),
                "new_stitched_effective_interval_match": intervals_close(
                    current_effective, expected_effective, atol=1e-4
                ),
                "prior_effective_width_deg": shell_module.interval_width(
                    expected_effective
                ),
                "new_stitched_effective_width_deg": shell_module.interval_width(
                    current_effective
                ),
                "new_vs_prior_effective_width_difference_deg": (
                    shell_module.interval_width(current_effective)
                    - shell_module.interval_width(expected_effective)
                ),
                "new_vs_prior_effective_angular_jaccard": shell_module.angular_jaccard(
                    current_effective, expected_effective
                ),
                "legacy_recomputed_raw_intervals_json": json.dumps(legacy_intervals),
                "new_stitched_raw_intervals_json": json.dumps(current_raw),
                "new_stitched_effective_intervals_json": json.dumps(current_effective),
                "prior_raw_intervals_json": json.dumps(expected_raw),
                "prior_effective_intervals_json": json.dumps(expected_effective),
                "parity_interpretation": (
                    "NEW_TRACK_WINDOW_MATCHES_LEGACY_TRUE_SHELL"
                    if new_available
                    and intervals_close(current_raw, expected_raw, atol=1e-4)
                    and intervals_close(current_effective, expected_effective, atol=1e-4)
                    else (
                        "NO_NEW_STITCHED_TRACK_UNION_FOR_FRAME"
                        if not new_available
                        else "TIME_AXIS_OR_TRACK_INPUT_SEMANTICS_DIFFER_FROM_LEGACY_TRUE_SHELL"
                    )
                ),
            }
        )
    return pd.DataFrame(rows)


def draw_shell_rays(axis: Any, frame: dict[str, Any], shell_rows: pd.DataFrame, color_map: Any) -> None:
    cx = float(frame["geometry"]["center_x_px"])
    cy = float(frame["geometry"]["center_y_px"])
    radius = float(frame["geometry"]["radius_px"])
    for index, shell in enumerate(shell_rows.itertuples(index=False)):
        color = color_map(index % 10)
        intervals = json.loads(shell.effective_intervals_json)
        for low, high in intervals:
            for theta_deg in (low, high):
                theta_rad = math.radians(theta_deg)
                x = cx + radius * math.sin(theta_rad)
                y = cy - radius * math.cos(theta_rad)
                axis.plot([cx, x], [cy, y], color=color, linewidth=1.1, alpha=0.75)
        axis.text(
            0.01,
            0.98 - 0.035 * index,
            str(shell.track_id).split("_")[-1],
            transform=axis.transAxes,
            color=color,
            fontsize=7,
            va="top",
            bbox={"facecolor": "black", "alpha": 0.35, "pad": 1, "edgecolor": "none"},
        )


def render_case(
    case_index: int,
    case: dict[str, Any],
    frame: dict[str, Any],
    p0: Any,
    p1e: Any,
    candidate_module: Any,
    candidates: pd.DataFrame,
    references: pd.DataFrame,
    shell_definitions: pd.DataFrame,
    region_evaluation: pd.DataFrame,
) -> Path:
    image_path = p0.file_url_to_path(frame["sar_image_url"])
    image_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise FileNotFoundError(image_path)
    image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    mask, radial, theta, px_per_m = candidate_module.single_frame_observation_mask(frame, image_bgr)
    maps, _ = candidate_module.compute_existing_candidate_maps_for_mask(
        p1e, frame, image_bgr, mask, radial, theta, px_per_m
    )
    support_radius_px = max(1, int(round(p1e.PHYSICAL_SUPPORT_RADIUS_M * px_per_m)))
    evaluation_maps = p1e.build_evaluation_maps(maps, mask, support_radius_px, "fixed_support_mean_v2")
    base_c2 = maps[PRIMARY_CANDIDATE]
    score = evaluation_maps[PRIMARY_CANDIDATE]
    archive = np.load(MASK_DIR / f"{frame['sar_frame_uid']}.npz")
    labels90, labels95, labels975 = archive["Q090"], archive["Q095"], archive["Q0975"]
    frame_candidates = candidates[candidates["frame_uid"] == frame["sar_frame_uid"]]
    frame_refs = references[references["frame_uid"] == frame["sar_frame_uid"]]
    raw_shells = shell_definitions[
        (shell_definitions["frame_uid"] == frame["sar_frame_uid"])
        & (shell_definitions["interface_kind"] == INTERFACE_RAW)
        & (shell_definitions["time_window_half_width_ms"] == 250)
        & (shell_definitions["shell_scope"] == "TRACK")
    ]
    stitched_shells = shell_definitions[
        (shell_definitions["frame_uid"] == frame["sar_frame_uid"])
        & (shell_definitions["interface_kind"] == INTERFACE_STITCHED)
        & (shell_definitions["time_window_half_width_ms"] == 250)
        & (shell_definitions["shell_scope"] == "TRACK")
    ]

    fig, axes = plt.subplots(2, 3, figsize=(18, 10.5), constrained_layout=True)
    axes[0, 0].imshow(image)
    axes[0, 0].set_title("Raw SAR pseudocolor · existing GT-blind peaks")
    axes[0, 1].imshow(base_c2, cmap="magma", vmin=0, vmax=1)
    axes[0, 1].set_title("Frozen base C2 · not the peak-input S(x)")
    axes[0, 2].imshow(score, cmap="magma", vmin=0, vmax=1)
    axes[0, 2].contour(labels95 > 0, levels=[0.5], colors=["#62f6ff"], linewidths=1.1)
    axes[0, 2].set_title("Actual S(x): 0.30 m fixed-support mean + q95 outline")
    axes[1, 0].imshow(image)
    draw_shell_rays(axes[1, 0], frame, raw_shells, plt.get_cmap("tab10"))
    axes[1, 0].set_title(f"RAW automatic fragments · ±250 ms · {len(raw_shells)} branches")
    axes[1, 1].imshow(image)
    draw_shell_rays(axes[1, 1], frame, stitched_shells, plt.get_cmap("tab10"))
    axes[1, 1].set_title(f"GT-blind offline stitched proxy · ±250 ms · {len(stitched_shells)} branches")
    axes[1, 2].imshow(image)
    axes[1, 2].contour(labels90 > 0, levels=[0.5], colors=["#ffd166"], linewidths=0.8)
    axes[1, 2].contour(labels95 > 0, levels=[0.5], colors=["#62f6ff"], linewidths=1.2)
    axes[1, 2].contour(labels975 > 0, levels=[0.5], colors=["#ff4da6"], linewidths=0.8)
    axes[1, 2].set_title("Response-region sensitivity: q90 / q95 / q97.5")

    for axis in axes.ravel():
        if len(frame_candidates):
            axis.scatter(
                frame_candidates["x_px"], frame_candidates["y_px"],
                s=np.clip(30 - 0.04 * frame_candidates["rank"], 4, 26),
                facecolors="none", edgecolors="white", linewidths=0.55, alpha=0.45,
            )
        for ref_index, ref in enumerate(frame_refs.itertuples(index=False)):
            color = plt.get_cmap("Set1")(ref_index % 9)
            axis.scatter(ref.reference_x_px, ref.reference_y_px, marker="x", s=70, c=[color], linewidths=2.2)
            axis.text(ref.reference_x_px + 5, ref.reference_y_px - 5, str(ref.target_id).split("SARPERSON")[-1], color=color, fontsize=8)
        axis.set_xlim(0, image.shape[1] - 1)
        axis.set_ylim(image.shape[0] - 1, 0)
        axis.set_xticks([])
        axis.set_yticks([])

    case_eval = region_evaluation[
        (region_evaluation["frame_uid"] == frame["sar_frame_uid"])
        & (region_evaluation["percentile_level"] == PRIMARY_PERCENTILE)
    ]
    state_text = "; ".join(
        f"{str(row.target_id).split('SARPERSON')[-1]}={row.representation_state}"
        f"{'/SHARED' if row.shared_region_flag else ''}"
        for row in case_eval.itertuples(index=False)
    )
    fig.suptitle(
        f"case {case_index:02d} · {case['selection_reason']}\n{frame['sar_frame_uid']} · {state_text}\n"
        "References are offline overlays only; shells/regions/peaks were generated first.",
        fontsize=13,
        weight="bold",
    )
    path = VIS_DIR / f"case_{case_index:02d}_{case['case_slug']}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def select_cases(reference_region: pd.DataFrame, references: pd.DataFrame) -> list[dict[str, Any]]:
    primary = reference_region[reference_region["percentile_level"] == PRIMARY_PERCENTILE].copy()
    cases: list[dict[str, Any]] = [
        {"frame_uid": "R02ZF_SARF000482", "case_slug": "R02_F482_PEAK_MISSING_REGION", "selection_reason": "FIXED_REQUEST_F482"},
        {"frame_uid": "R02ZF_SARF000490", "case_slug": "R02_F490_RADIUS_SENSITIVE_REGION", "selection_reason": "FIXED_REQUEST_F490"},
        {"frame_uid": "R02ZF_SARF000483", "case_slug": "R02_P03_P04_SHARED_REGION", "selection_reason": "FIXED_SHARED_P03_P04"},
        {"frame_uid": "R03ZF_SARF000458", "case_slug": "R03_OUTER_RANGE_BOUNDARY_OBSERVATION", "selection_reason": "FIXED_R03_REFERENCE_WITH_MINIMUM_OUTER_RANGE_BOUNDARY_DISTANCE"},
        {"frame_uid": "R04ZF_SARF000000", "case_slug": "R04_F0_CLEAR_PEAK_PRESENT", "selection_reason": "FIXED_CLEAR_PEAK_PRESENT_CONTROL"},
        {"frame_uid": "R04ZF_SARF000035", "case_slug": "R04_F35_Q90_ONLY_BORDERLINE", "selection_reason": "FIXED_WEAK_BORDERLINE_CONTROL"},
    ]
    p01 = primary[
        (primary["run_id"] == "R02ZF")
        & primary["target_id"].astype(str).str.endswith("01")
        & primary["region_near_reference_0p30m"].astype(bool)
    ].sort_values(["nearest_peak_rank_existing", "frame_index"], ascending=[False, True])
    if len(p01):
        row = p01.iloc[0]
        cases.append(
            {
                "frame_uid": row.frame_uid,
                "case_slug": "R02_P01_LOW_RANK_TRACK_SHELL",
                "selection_reason": "DETERMINISTIC_MAX_NEAREST_PEAK_RANK_R02_P01_WITH_Q95_REGION",
            }
        )
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for case in cases:
        if case["frame_uid"] in seen:
            continue
        seen.add(case["frame_uid"])
        unique.append(case)
    return unique


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(SCRIPT_PATH).lower() or "old_work" in str(OUTPUT_DIR).lower():
        raise RuntimeError("forbidden old_work dependency")
    for path in (PROTOCOL_PATH, PROVENANCE_AMENDMENT_PATH, REGION_AMENDMENT_PATH):
        if not path.is_file():
            raise FileNotFoundError(path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    MASK_DIR.mkdir(parents=True, exist_ok=True)

    input_hash_checks = []
    for path, expected in EXPECTED_HASHES.items():
        actual = sha256_file(path)
        input_hash_checks.append(
            {"path": str(path), "expected_sha256": expected, "actual_sha256": actual, "match": actual == expected}
        )
    if not all(row["match"] for row in input_hash_checks):
        mismatch = [row for row in input_hash_checks if not row["match"]]
        raise RuntimeError(f"frozen dependency hash mismatch: {mismatch}")

    p0 = load_module("person_p0_track_region", P0_SCRIPT)
    p1e = load_module("person_p1e_track_region", P1E_SCRIPT)
    candidate_module = load_module("person_candidate_track_region", CANDIDATE_SCRIPT)
    shell_module = load_module("person_shell_track_region", SHELL_SCRIPT)
    p0.assert_workspace_scope()
    _, contract_checks = p0.load_contract_and_verify()

    frames, process_note = load_explorer_sanitized()
    frames.sort(key=lambda row: (row["run_id"], row["sar_frame_index"]))
    frame_map = {frame["sar_frame_uid"]: frame for frame in frames}
    hypotheses = pd.read_parquet(OPTICAL_HYPOTHESES)
    track_summary = pd.read_parquet(OPTICAL_TRACK_SUMMARY)
    track_observations = prepare_track_observations(hypotheses)
    provenance = build_provenance_table(hypotheses, track_summary)
    track_interface_provenance = build_track_interface_provenance_table(
        track_observations
    )
    provenance.to_csv(OUTPUT_DIR / "optical_track_provenance_audit.csv", index=False, encoding="utf-8-sig")
    track_interface_provenance.to_csv(
        OUTPUT_DIR / "optical_track_interface_provenance.csv",
        index=False,
        encoding="utf-8-sig",
    )

    execution_stages = [
        {"stage": "FROZEN_DEPENDENCY_AND_CONTRACT_HASH_CHECK", "completed_at": now_iso()},
        {"stage": "OPTICAL_IDENTITY_PROVENANCE_AUDITED_BEFORE_SAR_REFERENCE", "completed_at": now_iso()},
    ]

    candidates_all = pd.read_csv(CANDIDATES_CSV)
    candidates = candidates_all[candidates_all["candidate"] == PRIMARY_CANDIDATE].copy()
    candidate_groups = {
        str(frame_uid): group.sort_values("rank").copy()
        for frame_uid, group in candidates.groupby("frame_uid", sort=False)
    }
    covered_frame_uids = set(candidate_groups)
    frame_px_per_m = {
        frame["sar_frame_uid"]: float(frame["geometry"]["radius_px"])
        / float(frame["geometry"]["outer_range_m"])
        for frame in frames
    }
    resume_pre_reference = "--resume-pre-reference" in sys.argv[1:]
    if resume_pre_reference:
        regions = pd.read_csv(OUTPUT_DIR / "response_region_table_pre_reference.csv")
        shell_definitions = pd.read_csv(OUTPUT_DIR / "track_shell_definition_table.csv")
        candidate_parity = pd.read_csv(OUTPUT_DIR / "candidate_recomputation_parity.csv")
        expected_frame_uids = {frame["sar_frame_uid"] for frame in frames}
        mask_frame_uids = {path.stem for path in MASK_DIR.glob("*.npz")}
        if set(regions["frame_uid"].astype(str)) != expected_frame_uids:
            raise RuntimeError("cannot resume: response-region frame coverage is incomplete")
        if set(candidate_parity["frame_uid"].astype(str)) != expected_frame_uids:
            raise RuntimeError("cannot resume: candidate parity frame coverage is incomplete")
        if mask_frame_uids != expected_frame_uids:
            raise RuntimeError("cannot resume: response-region mask coverage is incomplete")
        execution_stages.append(
            {
                "stage": "PRE_REFERENCE_PRODUCTS_RESUMED_AFTER_CANDIDATE_ARTIFACT_COVERAGE_CORRECTION",
                "completed_at": now_iso(),
                "reason": "The legacy candidate artifact covers 126 audit frames; absence of a frame is not a zero-candidate assertion.",
            }
        )
    else:
        shell_rows: list[dict[str, Any]] = []
        region_rows: list[dict[str, Any]] = []
        candidate_parity_rows: list[dict[str, Any]] = []
        for index, frame in enumerate(frames, start=1):
            image_path = p0.file_url_to_path(frame["sar_image_url"])
            image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            if image is None:
                raise FileNotFoundError(image_path)
            mask, radial, theta, px_per_m = candidate_module.single_frame_observation_mask(frame, image)
            maps, _ = candidate_module.compute_existing_candidate_maps_for_mask(
                p1e, frame, image, mask, radial, theta, px_per_m
            )
            support_radius_px = max(1, int(round(p1e.PHYSICAL_SUPPORT_RADIUS_M * px_per_m)))
            support_fraction = candidate_module.support_fraction_map(p1e, mask, support_radius_px)
            evaluation_maps = p1e.build_evaluation_maps(maps, mask, support_radius_px, "fixed_support_mean_v2")
            score_field = evaluation_maps[PRIMARY_CANDIDATE]
            eligible = mask & (support_fraction >= candidate_module.SUPPORT_TRUNCATED_MIN) & np.isfinite(score_field)
            percentiles = percentile_field(score_field, eligible)
            recomputed_candidates = candidate_module.extract_gt_blind_candidates(
                p1e, score_field, mask, support_fraction, px_per_m
            )
            candidate_parity_rows.append(
                compare_recomputed_candidates(
                    frame,
                    recomputed_candidates,
                    candidate_groups.get(
                        frame["sar_frame_uid"], pd.DataFrame(columns=candidates.columns)
                    ),
                )
            )
            archive_payload: dict[str, Any] = {}
            thresholds: list[float] = []
            for level in PERCENTILE_LEVELS:
                labels, rows, threshold = component_descriptors(
                    frame, score_field, percentiles, eligible, support_fraction, radial, theta, px_per_m, level
                )
                archive_payload[PERCENTILE_TAGS[level]] = labels
                thresholds.append(threshold)
                region_rows.extend(rows)
            archive_payload["levels"] = np.asarray(PERCENTILE_LEVELS, dtype=np.float32)
            archive_payload["numeric_score_thresholds"] = np.asarray(thresholds, dtype=np.float32)
            np.savez_compressed(MASK_DIR / f"{frame['sar_frame_uid']}.npz", **archive_payload)

            theta_valid_sorted = np.sort(theta[mask].astype(float))
            for interface in (INTERFACE_RAW, INTERFACE_STITCHED):
                observations = track_observations[interface].get(frame["run_id"], pd.DataFrame())
                for window_ms in TIME_WINDOWS_MS:
                    shell_rows.extend(
                        build_shell_rows_for_frame(
                            frame,
                            interface,
                            observations,
                            window_ms,
                            shell_module,
                            theta_valid_sorted,
                            int(mask.sum()),
                            px_per_m,
                        )
                    )
            if index % 25 == 0 or index == len(frames):
                print(f"pre-reference frame products {index}/{len(frames)} | {frame['sar_frame_uid']}", flush=True)

        regions = pd.DataFrame(region_rows)
        shell_definitions = pd.DataFrame(shell_rows)
        candidate_parity = pd.DataFrame(candidate_parity_rows)
        regions.to_csv(OUTPUT_DIR / "response_region_table_pre_reference.csv", index=False, encoding="utf-8-sig")
        shell_definitions.to_csv(OUTPUT_DIR / "track_shell_definition_table.csv", index=False, encoding="utf-8-sig")

    candidate_parity = annotate_candidate_parity_coverage(
        candidate_parity, covered_frame_uids
    )
    candidate_parity.to_csv(OUTPUT_DIR / "candidate_recomputation_parity.csv", index=False, encoding="utf-8-sig")
    failed = candidate_parity[
        candidate_parity["candidate_artifact_frame_covered"].astype(bool)
        & ~candidate_parity["all_candidate_fields_match"].astype(bool)
    ]
    if len(failed):
        raise RuntimeError(
            f"frozen C2 candidate recomputation mismatch in {len(failed)} covered frames: "
            f"{failed[['frame_uid', 'expected_candidate_count', 'recomputed_candidate_count', 'max_score_abs_error']].head(10).to_dict('records')}"
        )
    execution_stages.extend(
        [
            {"stage": "ALL_C2_RESPONSE_REGIONS_GENERATED_WITHOUT_REFERENCES", "completed_at": now_iso(), "region_rows": int(len(regions))},
            {"stage": "ALL_TRACK_SHELLS_GENERATED_WITHOUT_REFERENCES_OR_CANDIDATE_SELECTION", "completed_at": now_iso(), "shell_rows": int(len(shell_definitions))},
            {
                "stage": "FROZEN_GT_BLIND_C2_CANDIDATE_RECOMPUTATION_PARITY_VERIFIED_ON_ARTIFACT_COVERED_FRAMES",
                "completed_at": now_iso(),
                "development_frame_rows": int(len(candidate_parity)),
                "legacy_candidate_artifact_covered_frame_rows": int(
                    candidate_parity["candidate_artifact_frame_covered"].sum()
                ),
                "uncovered_frame_rows": int(
                    (~candidate_parity["candidate_artifact_frame_covered"].astype(bool)).sum()
                ),
            },
        ]
    )

    shell_candidates, shell_metrics = materialize_shell_candidates(shell_definitions, candidates, shell_module)
    regions = attach_peak_counts_to_regions(regions, candidates, frame_px_per_m)
    regions.to_csv(OUTPUT_DIR / "response_region_table.csv", index=False, encoding="utf-8-sig")
    shell_candidates.to_csv(OUTPUT_DIR / "track_shell_candidate_table.csv", index=False, encoding="utf-8-sig")
    shell_metrics.to_csv(OUTPUT_DIR / "track_shell_candidate_metrics.csv", index=False, encoding="utf-8-sig")
    frame_summary_available = build_frame_branch_summary(shell_metrics, shell_candidates)
    frame_summary = complete_frame_branch_summary(frames, frame_summary_available, candidates)
    overlap = build_shell_overlap_table(shell_definitions, shell_candidates, shell_module)
    frame_summary.to_csv(OUTPUT_DIR / "track_frame_branch_burden_summary.csv", index=False, encoding="utf-8-sig")
    overlap.to_csv(OUTPUT_DIR / "track_shell_overlap_table.csv", index=False, encoding="utf-8-sig")
    execution_stages.append(
        {"stage": "EXISTING_GT_BLIND_C2_CANDIDATES_RESTRICTED_TO_ALL_TRACK_SHELLS", "completed_at": now_iso(), "candidate_rows": int(len(shell_candidates))}
    )

    references_all = pd.read_csv(REFERENCES_CSV)
    references = references_all[references_all["candidate"] == PRIMARY_CANDIDATE].copy()
    observations = pd.read_csv(OBSERVATIONS_CSV, low_memory=False)
    reference_conditions = observations[observations["entity_kind"] == "PERSON_REFERENCE"].copy()
    pair_evaluation = evaluate_references_against_shells(references, shell_definitions, shell_candidates)
    reference_track_summary_available = summarize_reference_track_outputs(pair_evaluation)
    reference_track_summary = complete_reference_track_outputs(
        references, reference_track_summary_available
    )
    assignments_available = build_offline_one_to_one_assignments(pair_evaluation)
    assignments = complete_offline_one_to_one_assignments(
        references, assignments_available, reference_track_summary
    )
    reference_region = evaluate_references_against_regions(
        references, regions, frame_px_per_m, reference_conditions
    )
    observation_entity_region = evaluate_observation_entities_against_regions(
        observations, regions, frame_px_per_m
    )
    observation_entity_region_summary = summarize_observation_entity_region_coverage(
        observation_entity_region
    )
    region_shell_intersection = build_region_shell_intersections(regions, shell_definitions, shell_module)
    time_window_summary = build_time_window_summary(frame_summary, reference_track_summary)
    legacy_parity = build_legacy_union_parity(frames, shell_definitions, shell_module)

    pair_evaluation.to_csv(OUTPUT_DIR / "offline_reference_track_shell_pair_evaluation.csv", index=False, encoding="utf-8-sig")
    reference_track_summary.to_csv(OUTPUT_DIR / "offline_reference_track_summary.csv", index=False, encoding="utf-8-sig")
    assignments.to_csv(OUTPUT_DIR / "offline_one_to_one_track_reference_assignment.csv", index=False, encoding="utf-8-sig")
    reference_region.to_csv(OUTPUT_DIR / "offline_reference_response_region_evaluation.csv", index=False, encoding="utf-8-sig")
    observation_entity_region.to_csv(
        OUTPUT_DIR / "offline_observation_entity_response_region_evaluation.csv",
        index=False,
        encoding="utf-8-sig",
    )
    observation_entity_region_summary.to_csv(
        OUTPUT_DIR / "observation_entity_response_region_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    region_shell_intersection.to_csv(OUTPUT_DIR / "response_region_track_shell_intersection.csv", index=False, encoding="utf-8-sig")
    time_window_summary.to_csv(OUTPUT_DIR / "time_uncertainty_track_shell_tradeoff.csv", index=False, encoding="utf-8-sig")
    legacy_parity.to_csv(OUTPUT_DIR / "legacy_matched_union_parity.csv", index=False, encoding="utf-8-sig")
    execution_stages.append(
        {"stage": "MANUAL_REFERENCES_MATERIALIZED_FOR_OFFLINE_EVALUATION_ONLY", "completed_at": now_iso(), "reference_rows": int(len(references))}
    )

    cases = select_cases(reference_region, references)
    case_rows = []
    for case_index, case in enumerate(cases, start=1):
        if case["frame_uid"] not in frame_map:
            continue
        path = render_case(
            case_index,
            case,
            frame_map[case["frame_uid"]],
            p0,
            p1e,
            candidate_module,
            candidates,
            references,
            shell_definitions,
            reference_region,
        )
        case_rows.append({**case, "case_index": case_index, "visualization_path": str(path)})
    case_registry = pd.DataFrame(case_rows)
    case_registry.to_csv(OUTPUT_DIR / "case_registry.csv", index=False, encoding="utf-8-sig")

    primary_region_eval = reference_region[reference_region["percentile_level"] == PRIMARY_PERCENTILE]
    raw250 = reference_track_summary[
        (reference_track_summary["interface_kind"] == INTERFACE_RAW)
        & (reference_track_summary["time_window_half_width_ms"] == 250)
    ]
    stitched250 = reference_track_summary[
        (reference_track_summary["interface_kind"] == INTERFACE_STITCHED)
        & (reference_track_summary["time_window_half_width_ms"] == 250)
    ]
    raw250_assignments = assignments[
        (assignments["interface_kind"] == INTERFACE_RAW)
        & (assignments["time_window_half_width_ms"] == 250)
    ]
    q95_entity_summary = observation_entity_region_summary[
        observation_entity_region_summary["percentile_level"] == PRIMARY_PERCENTILE
    ]
    p03p04_intersections = region_shell_intersection[
        (region_shell_intersection["run_id"] == "R02ZF")
        & region_shell_intersection["region_id"].isin(
            primary_region_eval[
                (primary_region_eval["run_id"] == "R02ZF")
                & primary_region_eval["target_id"].astype(str).str.endswith(("03", "04"))
            ]["nearest_region_id"]
        )
    ]
    summary = {
        "schema": "PERSON_P1E_RUNTIME_TRACK_RESPONSE_REGION_MINIMAL_V1",
        "status": "COMPLETE_NO_NEW_PASS_FAIL_NO_P2_CLAIM",
        "generated_at": now_iso(),
        "python_executable": sys.executable,
        "workspace": str(WORKSPACE),
        "output_dir": str(OUTPUT_DIR),
        "input_hash_checks": input_hash_checks,
        "contract_input_checks": contract_checks,
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "provenance_amendment_sha256": sha256_file(PROVENANCE_AMENDMENT_PATH),
        "region_amendment_sha256": sha256_file(REGION_AMENDMENT_PATH),
        "analysis_script_sha256": sha256_file(SCRIPT_PATH),
        "process_isolation_note": process_note,
        "execution_stages": execution_stages,
        "counts": {
            "development_frames": len(frames),
            "optical_track_interface_rows": len(track_interface_provenance),
            "track_shell_definition_rows": len(shell_definitions),
            "track_shell_candidate_rows": len(shell_candidates),
            "response_region_rows": len(regions),
            "candidate_parity_frame_rows": len(candidate_parity),
            "manual_reference_rows": len(references),
            "reference_track_pair_rows": len(pair_evaluation),
            "reference_region_rows": len(reference_region),
            "observation_entity_region_rows": len(observation_entity_region),
            "complete_one_to_one_assignment_rows": len(assignments),
            "case_count": len(case_registry),
            "region_mask_files": len(list(MASK_DIR.glob("*.npz"))),
        },
        "optical_identity_boundary": {
            "raw_fragment_primary_interface": INTERFACE_RAW,
            "stitched_secondary_interface": INTERFACE_STITCHED,
            "strict_runtime_track_identity_established": False,
            "physical_target_id_used": False,
            "manual_track_selected": False,
            "centered_windows_ms": list(TIME_WINDOWS_MS),
        },
        "track_shell_250ms": {
            "raw_track_prior_availability": bool_fraction(raw250["optical_track_prior_available"]),
            "raw_reference_any_track_coverage": bool_fraction(raw250["any_track_reference_coverage"]),
            "raw_reference_candidate_retention_0p8m": bool_fraction(raw250["any_track_candidate_retention_0p8m"]),
            "raw_covering_track_count_median": finite_median(raw250["reference_covering_track_count"]),
            "raw_best_track_local_rank_median_offline_eval": finite_median(raw250["best_track_local_rank_0p8m_offline_eval"]),
            "stitched_track_prior_availability": bool_fraction(stitched250["optical_track_prior_available"]),
            "stitched_reference_any_track_coverage": bool_fraction(stitched250["any_track_reference_coverage"]),
            "stitched_reference_candidate_retention_0p8m": bool_fraction(stitched250["any_track_candidate_retention_0p8m"]),
            "stitched_covering_track_count_median": finite_median(stitched250["reference_covering_track_count"]),
            "stitched_best_track_local_rank_median_offline_eval": finite_median(stitched250["best_track_local_rank_0p8m_offline_eval"]),
            "raw_one_to_one_assignment_available_fraction": bool_fraction(
                raw250_assignments["one_to_one_assignment_available"]
            ),
            "raw_one_to_one_reference_inside_fraction_unconditional": bool_fraction(
                raw250_assignments["assignment_reference_inside_shell"]
            ),
            "raw_one_to_one_candidate_retention_fraction_unconditional": bool_fraction(
                raw250_assignments["assignment_candidate_present_0p8m"]
            ),
        },
        "time_uncertainty_track_shell_tradeoff": time_window_summary.to_dict("records"),
        "response_region_primary_q95": {
            "reference_region_near_0p30m_fraction": bool_fraction(primary_region_eval["region_near_reference_0p30m"]),
            "reference_direct_inside_fraction": bool_fraction(primary_region_eval["reference_center_directly_inside_region"]),
            "peak_missing_region_present_count": int((primary_region_eval["representation_state"] == "PEAK_MISSING_REGION_PRESENT").sum()),
            "peak_present_count": int((primary_region_eval["representation_state"] == "PEAK_PRESENT").sum()),
            "peak_missing_no_q95_region_near_count": int((primary_region_eval["representation_state"] == "PEAK_MISSING_NO_Q95_REGION_NEAR").sum()),
            "q090_only_reference_count": int(
                (
                    primary_region_eval["superlevel_presence_state"]
                    == "Q090_ONLY_REGION_PRESENT"
                ).sum()
            ),
            "no_q090_region_near_reference_count": int(
                (
                    primary_region_eval["superlevel_presence_state"]
                    == "NO_Q090_REGION_NEAR_REFERENCE"
                ).sum()
            ),
            "shared_region_fraction": bool_fraction(primary_region_eval["shared_region_flag"]),
            "extended_or_ridge_fraction_among_near_regions": bool_fraction(
                primary_region_eval.loc[
                    primary_region_eval["region_near_reference_0p30m"].astype(bool),
                    "nearest_region_structure_state",
                ].eq("EXTENDED_OR_RIDGE_RESPONSE")
            ),
        },
        "response_region_posthoc_location_controls_q95": q95_entity_summary.to_dict("records"),
        "legacy_matched_shell_reproduction": {
            "matched_rows": int(legacy_parity["prior_true_shell_available"].sum()),
            "legacy_self_recomputed_raw_matches": int(
                legacy_parity.loc[
                    legacy_parity["prior_true_shell_available"],
                    "legacy_recomputed_raw_interval_match",
                ].sum()
            ),
            "legacy_self_recomputed_all_expected_match": bool(
                legacy_parity.loc[
                    legacy_parity["prior_true_shell_available"],
                    "legacy_recomputed_raw_interval_match",
                ].all()
            ),
            "new_stitched_union_available_rows": int(
                legacy_parity["new_stitched_union_available"].sum()
            ),
            "new_stitched_raw_interval_matches": int(
                legacy_parity["new_stitched_raw_interval_match"].sum()
            ),
            "new_stitched_effective_interval_matches": int(
                legacy_parity["new_stitched_effective_interval_match"].sum()
            ),
        },
        "candidate_recomputation_parity": {
            "frame_rows": int(len(candidate_parity)),
            "legacy_candidate_artifact_covered_frame_rows": int(
                candidate_parity["candidate_artifact_frame_covered"].sum()
            ),
            "uncovered_frame_rows": int(
                (~candidate_parity["candidate_artifact_frame_covered"].astype(bool)).sum()
            ),
            "all_artifact_covered_frames_match": bool(
                candidate_parity.loc[
                    candidate_parity["candidate_artifact_frame_covered"].astype(bool),
                    "all_candidate_fields_match",
                ].all()
            ),
            "max_coordinate_error_px_covered": float(
                candidate_parity.loc[
                    candidate_parity["candidate_artifact_frame_covered"].astype(bool),
                    "max_coordinate_error_px",
                ].max()
            ),
            "max_score_abs_error_covered": float(
                candidate_parity.loc[
                    candidate_parity["candidate_artifact_frame_covered"].astype(bool),
                    "max_score_abs_error",
                ].max()
            ),
            "max_support_fraction_abs_error": float(
                candidate_parity.loc[
                    candidate_parity["candidate_artifact_frame_covered"].astype(bool),
                    "max_support_fraction_abs_error",
                ].max()
            ),
            "uncovered_frame_semantics": "NO_LEGACY_CANDIDATE_ARTIFACT_FOR_FRAME_NOT_ZERO_CANDIDATES",
        },
        "p03_p04_region_shell_note": {
            "intersection_rows": int(len(p03p04_intersections)),
            "unique_q95_regions": int(p03p04_intersections["region_id"].nunique()) if len(p03p04_intersections) else 0,
            "unique_raw_tracks": int(
                p03p04_intersections.loc[p03p04_intersections["interface_kind"] == INTERFACE_RAW, "track_id"].nunique()
            ) if len(p03p04_intersections) else 0,
            "unique_stitched_tracks": int(
                p03p04_intersections.loc[p03p04_intersections["interface_kind"] == INTERFACE_STITCHED, "track_id"].nunique()
            ) if len(p03p04_intersections) else 0,
        },
        "fixed_boundaries": {
            "C2_modified": False,
            "new_feature_added": False,
            "SAR_box_generated": False,
            "optical_assigned_SAR_range": False,
            "response_region_is_final_box": False,
            "shared_region_is_physical_fusion": False,
            "P2_pass_claimed": False,
            "blind_validation_claimed": False,
        },
    }
    (OUTPUT_DIR / "diagnostic_summary.json").write_text(
        json.dumps(json_safe(summary), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(json_safe(summary), ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
