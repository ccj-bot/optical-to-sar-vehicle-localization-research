"""Decompose optical azimuth-shell uncertainty and build GT-blind shell-region topology.

This is a bounded diagnostic.  Optical raw fragments produce time/azimuth shells;
frozen C2 response-region masks remain the SAR image-domain representation.  All
shells, regions, pixel intersections, and bipartite topology are materialized
before any manual SAR reference slice is loaded.
"""

from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import math
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

import cv2
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
P1E_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface"
OUTPUT_DIR = P1E_ROOT / "shell_uncertainty_region_topology_v1"
PROTOCOL_PATH = OUTPUT_DIR / "00_SHELL_UNCERTAINTY_REGION_TOPOLOGY_PROTOCOL_FROZEN_BEFORE_RUN.md"

PREVIOUS_SCRIPT = TASK_DIR / "run_p1e_runtime_track_response_region_minimal.py"
CANDIDATE_SCRIPT = TASK_DIR / "run_p1e_candidate_recall_audit.py"
SHELL_SCRIPT = TASK_DIR / "run_p1e_optical_shell_information_gain.py"
PREVIOUS_ROOT = P1E_ROOT / "runtime_track_response_region_minimal_v1"
PREVIOUS_SHELLS = PREVIOUS_ROOT / "track_shell_definition_table.csv"
REGION_TABLE = PREVIOUS_ROOT / "response_region_table_pre_reference.csv"
CANDIDATE_PARITY = PREVIOUS_ROOT / "candidate_recomputation_parity.csv"
REFERENCE_REGION_EVAL = PREVIOUS_ROOT / "offline_reference_response_region_evaluation.csv"
REGION_MASK_DIR = PREVIOUS_ROOT / "response_region_masks"
OBSERVATION_TABLE = P1E_ROOT / "observation_model_diagnostic_v1" / "observation_condition_table.csv"
OPTICAL_HYPOTHESES = (
    WORKSPACE
    / "output"
    / "person_optical_guided_sar_annotation_full_20260823"
    / "optical_person_frame_hypotheses.parquet"
)
R01_MODEL_SUMMARY = WORKSPACE / "output" / "r01_person_azimuth_pilot_20260819" / "model_summary.json"
R04_VALIDATION = WORKSPACE / "output" / "r04_person_crossrun_validation_20260820" / "validation_report.json"
EXPLORER_PATH = WORKSPACE / "output" / "person_multidimensional_response_explorer_20260823" / "explorer_data.js"

RUNS = ("R01ZF", "R02ZF", "R03ZF", "R04ZF")
OPTICAL_SLOPE_DEG_PER_PX = 0.02666536443690682
OPTICAL_INTERCEPT_DEG = -45.502258572693094
OPTICAL_WIDTH_PX = 3840.0

TIME_POLICIES = {
    "SAME_FRAME": (0, 0),
    "CENTERED_100MS": (-100, 100),
    "CENTERED_250MS": (-250, 250),
    "CENTERED_500MS": (-500, 500),
    "PAST_ONLY_250MS": (-250, 0),
    "BUFFERED_100MS": (-250, 100),
}
TOPOLOGY_POLICIES = ("SAME_FRAME", "PAST_ONLY_250MS", "CENTERED_250MS")
GUARD_VARIANTS = {
    "CURRENT_G6": 6.0,
    "R04_MAE_PROXY_G2P652": 2.6518119892277463,
    "NO_GUARD_LOWER_BOUND_G0": 0.0,
}
PRIMARY_GUARD = "CURRENT_G6"
PERCENTILE_TAGS = ("Q090", "Q095", "Q0975")

EXPECTED_HASHES = {
    PREVIOUS_SCRIPT: "051B414753B73118CF77712A35DF86EC5FB05C12B2C00217EB14BFE81DFDCBBA",
    CANDIDATE_SCRIPT: "84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8",
    SHELL_SCRIPT: "2C71440DF9C22FDCE17A3C4050E4E0054F6B7CA4542C44C134E2DEA3478A2203",
    PREVIOUS_SHELLS: "B6C58404F54F542133EE5678EBB93B97758BE85EFE71CA252C41FD3018C061C5",
    REGION_TABLE: "A2BB425C366EA0DE461C427113E8E836A556F65250677146B6F26129E853C339",
    CANDIDATE_PARITY: "21FA3270E268EEC460E603C07F1D840182780E0FB671B0ABFC04E12256C35329",
    REFERENCE_REGION_EVAL: "4522FE9B65249180B073EA16E87BF11A528DC079B3831348CD7610E3685B7353",
    OBSERVATION_TABLE: "DE65B9705A353F0DF783E0D4A59D0274FD05547362ABE463C50C9C5469D80C21",
    OPTICAL_HYPOTHESES: "15D65A299762E87BFD6F21E811C754D1DF062AC6AFC1840A1C1A9B162AB8B478",
    R01_MODEL_SUMMARY: "3463FFF0A8D1507ECA383356E0FB108BD60E1226A19890B62EA8C8FD5090BA42",
    R04_VALIDATION: "24D0CEE627B272EA76A64BC245C0779DA2F6ED428E885C77490A177DBE470A14",
    EXPLORER_PATH: "C39E60EB478FF7D815EFE6984D3BCF36600737E2EC3D1FF76D04020DED54EF7D",
}
EXPECTED_MASK_COUNT = 398
EXPECTED_MASK_AGGREGATE = "0D9E10C41DB2EE02E060E9AF789AC59C6CD80591B11DC591222CA2B400656CB1"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def mask_manifest_aggregate(mask_dir: Path) -> tuple[int, str]:
    rows = [f"{path.name}:{sha256_file(path)}" for path in sorted(mask_dir.glob("*.npz"))]
    return len(rows), hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest().upper()


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
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def file_url_to_path(value: str) -> Path:
    parsed = urlparse(str(value))
    if parsed.scheme.lower() != "file":
        return Path(value)
    raw = unquote(parsed.path)
    if raw.startswith("/") and len(raw) > 3 and raw[2] == ":":
        raw = raw[1:]
    return Path(raw.replace("/", "\\"))


def finite_median(values: Iterable[Any]) -> float:
    array = pd.to_numeric(pd.Series(list(values)), errors="coerce").to_numpy(float)
    array = array[np.isfinite(array)]
    return float(np.median(array)) if len(array) else math.nan


def finite_quantile(values: Iterable[Any], q: float) -> float:
    array = pd.to_numeric(pd.Series(list(values)), errors="coerce").to_numpy(float)
    array = array[np.isfinite(array)]
    return float(np.quantile(array, q)) if len(array) else math.nan


def bool_fraction(values: Iterable[Any]) -> float:
    series = pd.Series(list(values))
    return float(series.astype(bool).mean()) if len(series) else math.nan


def union_intervals(intervals: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    normalized = sorted((min(float(a), float(b)), max(float(a), float(b))) for a, b in intervals)
    output: list[list[float]] = []
    for low, high in normalized:
        if not output or low > output[-1][1]:
            output.append([low, high])
        else:
            output[-1][1] = max(output[-1][1], high)
    return [(low, high) for low, high in output]


def clip_intervals(intervals: Iterable[tuple[float, float]], low: float, high: float) -> list[tuple[float, float]]:
    clipped = [(max(a, low), min(b, high)) for a, b in union_intervals(intervals)]
    return union_intervals((a, b) for a, b in clipped if b > a)


def interval_width(intervals: Iterable[tuple[float, float]]) -> float:
    return float(sum(high - low for low, high in union_intervals(intervals)))


def interval_overlap_width(first: Iterable[tuple[float, float]], second: Iterable[tuple[float, float]]) -> float:
    a = union_intervals(first)
    b = union_intervals(second)
    return float(sum(max(0.0, min(ah, bh) - max(al, bl)) for al, ah in a for bl, bh in b))


def interval_jaccard(first: Iterable[tuple[float, float]], second: Iterable[tuple[float, float]]) -> float:
    first_width = interval_width(first)
    second_width = interval_width(second)
    overlap = interval_overlap_width(first, second)
    union_width = first_width + second_width - overlap
    return overlap / union_width if union_width > 0 else math.nan


def interval_contains(theta: float, intervals: Iterable[tuple[float, float]]) -> bool:
    return any(low <= theta <= high for low, high in intervals)


def interval_distance(theta: float, intervals: Iterable[tuple[float, float]]) -> float:
    values = []
    for low, high in intervals:
        if low <= theta <= high:
            return 0.0
        values.append(min(abs(theta - low), abs(theta - high)))
    return min(values) if values else math.inf


def interval_center_distance(theta: float, intervals: Iterable[tuple[float, float]]) -> float:
    values = [abs(theta - 0.5 * (low + high)) for low, high in intervals]
    return min(values) if values else math.inf


def inside_interval_mask(theta: np.ndarray, intervals: Iterable[tuple[float, float]]) -> np.ndarray:
    output = np.zeros(theta.shape, dtype=bool)
    for low, high in union_intervals(intervals):
        output |= (theta >= low) & (theta <= high)
    return output


def polar_grids(frame: dict[str, Any], shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, float]:
    height, width = shape
    geometry = frame["geometry"]
    yy, xx = np.indices((height, width), dtype=np.float32)
    cx = float(geometry["center_x_px"])
    cy = float(geometry["center_y_px"])
    radial_px = np.hypot(xx - cx, cy - yy)
    theta = np.degrees(np.arctan2(xx - cx, cy - yy))
    px_per_m = float(geometry["radius_px"]) / float(geometry["outer_range_m"])
    return radial_px / px_per_m, theta, px_per_m


def prepare_raw_observations(hypotheses: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if "physical_target_id" in hypotheses.columns:
        raise RuntimeError("optical hypotheses unexpectedly contain physical_target_id")
    data = hypotheses[
        hypotheses["run_id"].isin(RUNS) & hypotheses["box_source"].astype(str).eq("DETECTED")
    ].copy()
    data["timestamp_ms"] = pd.to_numeric(data["timestamp_ms"], errors="raise").astype(int)
    data["track_id"] = data["raw_track_fragment_id"].astype(str)
    data["theta_box_low_deg"] = (
        OPTICAL_SLOPE_DEG_PER_PX * pd.to_numeric(data["bbox_x1"], errors="raise")
        + OPTICAL_INTERCEPT_DEG
    )
    data["theta_box_high_deg"] = (
        OPTICAL_SLOPE_DEG_PER_PX * pd.to_numeric(data["bbox_x2"], errors="raise")
        + OPTICAL_INTERCEPT_DEG
    )
    output: dict[str, pd.DataFrame] = {}
    for run_id, group in data.groupby("run_id", sort=False):
        output[str(run_id)] = group.sort_values(
            ["timestamp_ms", "track_id", "confidence"], ascending=[True, True, False]
        ).drop_duplicates(["timestamp_ms", "track_id"], keep="first")
    return output


def select_temporal_observations(observations: pd.DataFrame, query_ms: int, policy: str) -> pd.DataFrame:
    low_offset, high_offset = TIME_POLICIES[policy]
    if low_offset == 0 and high_offset == 0:
        return observations[observations["timestamp_ms"] == query_ms]
    return observations[
        (observations["timestamp_ms"] >= query_ms + low_offset)
        & (observations["timestamp_ms"] <= query_ms + high_offset)
    ]


def build_shell_products(
    frames: list[dict[str, Any]],
    raw_by_run: dict[str, pd.DataFrame],
    candidate_module: Any,
    shell_module: Any,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    shell_rows: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []
    overlap_rows: list[dict[str, Any]] = []
    for index, frame in enumerate(frames, start=1):
        image_path = file_url_to_path(frame["sar_image_url"])
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(image_path)
        omega_single, _, theta_grid, px_per_m = candidate_module.single_frame_observation_mask(frame, image)
        theta_valid_sorted = np.sort(theta_grid[omega_single].astype(float))
        omega_count = int(np.count_nonzero(omega_single))
        frame_uid = str(frame["sar_frame_uid"])
        run_id = str(frame["run_id"])
        query_ms = int(frame["nominal_optical_timestamp_ms"])
        fan_low = float(frame["theta_low_deg"])
        fan_high = float(frame["theta_high_deg"])
        common_low = max(fan_low, OPTICAL_INTERCEPT_DEG)
        common_high = min(fan_high, OPTICAL_SLOPE_DEG_PER_PX * OPTICAL_WIDTH_PX + OPTICAL_INTERCEPT_DEG)
        observations = raw_by_run.get(run_id, pd.DataFrame())
        frame_shells: list[dict[str, Any]] = []
        for policy in TIME_POLICIES:
            selected = select_temporal_observations(observations, query_ms, policy)
            track_groups = list(selected.groupby("track_id", sort=True)) if len(selected) else []
            for track_id, group in track_groups:
                raw_intervals = [
                    (float(row.theta_box_low_deg), float(row.theta_box_high_deg))
                    for row in group.itertuples(index=False)
                ]
                individual_widths = [abs(high - low) for low, high in raw_intervals]
                raw_union = union_intervals(raw_intervals)
                raw_union_width = interval_width(raw_union)
                representative_width = float(np.median(individual_widths))
                temporal_spread = raw_union_width - representative_width
                for guard_tag, guard_deg in GUARD_VARIANTS.items():
                    guarded_intervals = [(low - guard_deg, high + guard_deg) for low, high in raw_intervals]
                    metrics = shell_module.shell_geometry_metrics(
                        guarded_intervals,
                        fan_low,
                        fan_high,
                        common_low,
                        common_high,
                        theta_valid_sorted,
                        omega_count,
                        px_per_m,
                    )
                    effective = [(float(a), float(b)) for a, b in metrics["effective_intervals"]]
                    if not effective:
                        continue
                    guarded_width = interval_width(guarded_intervals)
                    guard_increment = guarded_width - raw_union_width
                    effective_width = float(metrics["effective_width_deg"])
                    fan_clip_loss = guarded_width - effective_width
                    reconstruction = representative_width + temporal_spread + guard_increment - fan_clip_loss
                    row = {
                        "run_id": run_id,
                        "frame_uid": frame_uid,
                        "frame_index": int(frame["sar_frame_index"]),
                        "sar_timestamp_ms": int(frame["sar_timestamp_ms"]),
                        "nominal_optical_timestamp_ms": query_ms,
                        "sync_status": str(frame["sync_status"]),
                        "temporal_policy": policy,
                        "window_low_offset_ms": int(TIME_POLICIES[policy][0]),
                        "window_high_offset_ms": int(TIME_POLICIES[policy][1]),
                        "allowed_future_latency_ms": max(0, int(TIME_POLICIES[policy][1])),
                        "guard_variant": guard_tag,
                        "guard_deg_each_side": float(guard_deg),
                        "shell_id": f"{frame_uid}__RAW__{policy}__{guard_tag}__{track_id}",
                        "track_id": str(track_id),
                        "source_observation_count": int(len(group)),
                        "source_timestamp_min_ms": int(group["timestamp_ms"].min()),
                        "source_timestamp_max_ms": int(group["timestamp_ms"].max()),
                        "source_has_future_observation": bool((group["timestamp_ms"] > query_ms).any()),
                        "source_future_observation_count": int((group["timestamp_ms"] > query_ms).sum()),
                        "source_tracker_statuses": ";".join(sorted(set(group["tracker_status"].astype(str)))),
                        "source_detection_passes": ";".join(sorted(set(group["detection_pass"].astype(str)))),
                        "source_parent_stitched_ids": ";".join(sorted(set(group["optical_person_id"].astype(str)))),
                        "source_parent_stitched_id_count": int(group["optical_person_id"].nunique()),
                        "source_ambiguous_stitch_count_max": int(group["ambiguous_stitch_count"].max()),
                        "source_accepted_parent_fraction": float(group["accepted_for_annotation_queue"].astype(bool).mean()),
                        "single_detection_box_width_median_deg": representative_width,
                        "single_detection_box_width_max_deg": float(np.max(individual_widths)),
                        "raw_box_union_width_deg": raw_union_width,
                        "temporal_or_view_union_increment_deg": temporal_spread,
                        "guard_union_increment_deg": guard_increment,
                        "guarded_union_width_before_fan_clip_deg": guarded_width,
                        "fan_clip_loss_deg": fan_clip_loss,
                        "effective_width_deg": effective_width,
                        "decomposition_reconstruction_error_deg": reconstruction - effective_width,
                        "effective_area_px": int(metrics["effective_area_px"]),
                        "effective_area_m2": float(metrics["effective_area_m2"]),
                        "effective_area_fraction_of_omega": float(metrics["effective_area_fraction_of_omega"]),
                        "left_clip_deg": float(metrics["left_clip_deg"]),
                        "right_clip_deg": float(metrics["right_clip_deg"]),
                        "total_clip_deg": float(metrics["total_clip_deg"]),
                        "nearest_boundary_gap_deg": float(metrics["nearest_boundary_gap_deg"]),
                        "common_fov_overlap_width_deg": float(metrics["common_fov_overlap_width_deg"]),
                        "common_fov_overlap_fraction": float(metrics["common_fov_overlap_fraction"]),
                        "effective_width_outside_common_fov_deg": max(
                            0.0, effective_width - float(metrics["common_fov_overlap_width_deg"])
                        ),
                        "fan_theta_low_deg": fan_low,
                        "fan_theta_high_deg": fan_high,
                        "common_fov_theta_low_deg": common_low,
                        "common_fov_theta_high_deg": common_high,
                        "omega_single_pixel_count": omega_count,
                        "px_per_m": float(px_per_m),
                        "raw_box_intervals_json": json.dumps(raw_union),
                        "guarded_intervals_json": json.dumps(union_intervals(guarded_intervals)),
                        "effective_intervals_json": json.dumps(effective),
                        "physical_target_id_used": False,
                        "sar_reference_used": False,
                        "sar_range_assigned_by_optical": False,
                        "strict_runtime_identity_claimed": False,
                    }
                    shell_rows.append(row)
                    frame_shells.append(row)

        frame_shell_df = pd.DataFrame(frame_shells)
        for policy in TIME_POLICIES:
            for guard_tag in GUARD_VARIANTS:
                if frame_shell_df.empty:
                    group = frame_shell_df
                else:
                    group = frame_shell_df[
                        (frame_shell_df["temporal_policy"] == policy)
                        & (frame_shell_df["guard_variant"] == guard_tag)
                    ]
                intervals_by_shell = (
                    [json.loads(value) for value in group["effective_intervals_json"]] if len(group) else []
                )
                union_effective = union_intervals(
                    interval for intervals in intervals_by_shell for interval in intervals
                )
                union_metrics = shell_module.shell_geometry_metrics(
                    union_effective,
                    fan_low,
                    fan_high,
                    common_low,
                    common_high,
                    theta_valid_sorted,
                    omega_count,
                    px_per_m,
                ) if union_effective else None
                pair_jaccards: list[float] = []
                pair_overlaps: list[float] = []
                if len(group) >= 2:
                    for first, second in itertools.combinations(group.itertuples(index=False), 2):
                        first_intervals = json.loads(first.effective_intervals_json)
                        second_intervals = json.loads(second.effective_intervals_json)
                        overlap = interval_overlap_width(first_intervals, second_intervals)
                        jaccard = interval_jaccard(first_intervals, second_intervals)
                        pair_overlaps.append(overlap)
                        pair_jaccards.append(jaccard)
                        overlap_rows.append(
                            {
                                "run_id": run_id,
                                "frame_uid": frame_uid,
                                "frame_index": int(frame["sar_frame_index"]),
                                "temporal_policy": policy,
                                "guard_variant": guard_tag,
                                "first_shell_id": first.shell_id,
                                "second_shell_id": second.shell_id,
                                "first_track_id": first.track_id,
                                "second_track_id": second.track_id,
                                "same_parent_stitched_id": bool(
                                    first.source_parent_stitched_ids == second.source_parent_stitched_ids
                                    and bool(first.source_parent_stitched_ids)
                                ),
                                "angular_overlap_deg": overlap,
                                "angular_jaccard": jaccard,
                                "gt_blind": True,
                            }
                        )
                parent_counts: Counter[str] = Counter()
                for value in group.get("source_parent_stitched_ids", pd.Series(dtype=str)).astype(str):
                    for parent in (item for item in value.split(";") if item):
                        parent_counts[parent] += 1
                sum_width = float(group["effective_width_deg"].sum()) if len(group) else 0.0
                union_width = interval_width(union_effective)
                frame_rows.append(
                    {
                        "run_id": run_id,
                        "frame_uid": frame_uid,
                        "frame_index": int(frame["sar_frame_index"]),
                        "temporal_policy": policy,
                        "guard_variant": guard_tag,
                        "track_shell_available": bool(len(group)),
                        "active_raw_fragment_shell_count": int(len(group)),
                        "active_parent_stitched_count": int(len(parent_counts)),
                        "parent_with_multiple_raw_fragments_count": int(sum(count > 1 for count in parent_counts.values())),
                        "max_raw_fragments_per_parent": int(max(parent_counts.values(), default=0)),
                        "source_observation_count_sum": int(group["source_observation_count"].sum()) if len(group) else 0,
                        "shell_with_future_observation_fraction": bool_fraction(group["source_has_future_observation"]) if len(group) else math.nan,
                        "single_box_width_median_deg": finite_median(group["single_detection_box_width_median_deg"]) if len(group) else math.nan,
                        "temporal_union_increment_median_deg": finite_median(group["temporal_or_view_union_increment_deg"]) if len(group) else math.nan,
                        "guard_increment_median_deg": finite_median(group["guard_union_increment_deg"]) if len(group) else math.nan,
                        "fan_clip_loss_median_deg": finite_median(group["fan_clip_loss_deg"]) if len(group) else math.nan,
                        "single_track_width_median_deg": finite_median(group["effective_width_deg"]) if len(group) else math.nan,
                        "sum_track_effective_width_deg": sum_width,
                        "all_track_union_effective_width_deg": union_width,
                        "angular_overlap_redundancy_deg": max(0.0, sum_width - union_width),
                        "angular_overlap_redundancy_fraction_of_sum": (
                            max(0.0, sum_width - union_width) / sum_width if sum_width > 0 else math.nan
                        ),
                        "all_track_union_effective_area_px": int(union_metrics["effective_area_px"]) if union_metrics else 0,
                        "all_track_union_effective_area_fraction_of_omega": (
                            float(union_metrics["effective_area_fraction_of_omega"]) if union_metrics else 0.0
                        ),
                        "pairwise_shell_jaccard_median": finite_median(pair_jaccards),
                        "pairwise_shell_jaccard_max": max(pair_jaccards, default=math.nan),
                        "pairwise_shell_overlap_deg_max": max(pair_overlaps, default=0.0),
                        "physical_target_id_used": False,
                        "sar_reference_used": False,
                    }
                )
        if index % 40 == 0 or index == len(frames):
            print(f"shell decomposition {index}/{len(frames)}", flush=True)
    return pd.DataFrame(shell_rows), pd.DataFrame(frame_rows), pd.DataFrame(overlap_rows)


def topology_state(shell_count: int, region_count: int) -> str:
    if shell_count == 1 and region_count == 0:
        return "SHELL_NO_REGION"
    if shell_count == 0 and region_count == 1:
        return "REGION_NO_SHELL"
    if shell_count == 1 and region_count == 1:
        return "ONE_SHELL_ONE_REGION"
    if shell_count == 1 and region_count > 1:
        return "ONE_SHELL_MULTIPLE_REGIONS"
    if shell_count > 1 and region_count == 1:
        return "MULTIPLE_SHELLS_ONE_REGION"
    if shell_count > 1 and region_count > 1:
        return "MULTIPLE_SHELLS_MULTIPLE_REGIONS"
    raise RuntimeError((shell_count, region_count))


def build_topology_products(
    frames: list[dict[str, Any]],
    shells: pd.DataFrame,
    regions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frame_map = {str(frame["sar_frame_uid"]): frame for frame in frames}
    primary_shells = shells[
        (shells["guard_variant"] == PRIMARY_GUARD)
        & shells["temporal_policy"].isin(TOPOLOGY_POLICIES)
    ].copy()
    shell_groups = {
        (str(uid), str(policy)): group.copy()
        for (uid, policy), group in primary_shells.groupby(["frame_uid", "temporal_policy"], sort=False)
    }
    region_groups = {
        (str(uid), str(tag)): group.copy()
        for (uid, tag), group in regions.groupby(["frame_uid", "percentile_tag"], sort=False)
    }
    edge_rows: list[dict[str, Any]] = []
    shell_node_rows: list[dict[str, Any]] = []
    region_node_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []

    for index, (frame_uid, frame) in enumerate(frame_map.items(), start=1):
        with np.load(REGION_MASK_DIR / f"{frame_uid}.npz") as archive:
            sample = archive[PERCENTILE_TAGS[0]]
            range_grid, theta_grid, px_per_m = polar_grids(frame, sample.shape)
            for policy in TOPOLOGY_POLICIES:
                frame_shells = shell_groups.get((frame_uid, policy), pd.DataFrame(columns=primary_shells.columns))
                for percentile_tag in PERCENTILE_TAGS:
                    labels = archive[percentile_tag]
                    frame_regions = region_groups.get(
                        (frame_uid, percentile_tag), pd.DataFrame(columns=regions.columns)
                    )
                    region_by_label = {
                        int(row.region_label): row for row in frame_regions.itertuples(index=False)
                    }
                    shell_adjacency: dict[str, set[str]] = {
                        str(row.shell_id): set() for row in frame_shells.itertuples(index=False)
                    }
                    region_adjacency: dict[str, set[str]] = {
                        str(row.region_id): set() for row in frame_regions.itertuples(index=False)
                    }
                    edge_count_lookup: Counter[tuple[str, str]] = Counter()
                    for shell in frame_shells.itertuples(index=False):
                        intervals = json.loads(shell.effective_intervals_json)
                        shell_mask = inside_interval_mask(theta_grid, intervals)
                        ys, xs = np.nonzero(shell_mask & (labels > 0))
                        if not len(xs):
                            continue
                        selected_labels = labels[ys, xs].astype(int)
                        for label in np.unique(selected_labels):
                            region = region_by_label.get(int(label))
                            if region is None:
                                continue
                            select = selected_labels == int(label)
                            count = int(np.count_nonzero(select))
                            region_id = str(region.region_id)
                            shell_id = str(shell.shell_id)
                            shell_adjacency[shell_id].add(region_id)
                            region_adjacency[region_id].add(shell_id)
                            edge_count_lookup[(shell_id, region_id)] = count
                            edge_theta = theta_grid[ys[select], xs[select]]
                            edge_range = range_grid[ys[select], xs[select]]
                            edge_rows.append(
                                {
                                    "run_id": str(frame["run_id"]),
                                    "frame_uid": frame_uid,
                                    "frame_index": int(frame["sar_frame_index"]),
                                    "temporal_policy": policy,
                                    "guard_variant": PRIMARY_GUARD,
                                    "percentile_tag": percentile_tag,
                                    "shell_id": shell_id,
                                    "track_id": str(shell.track_id),
                                    "region_id": region_id,
                                    "region_label": int(label),
                                    "intersection_pixel_count": count,
                                    "intersection_area_m2": float(count / (px_per_m * px_per_m)),
                                    "region_pixel_count": int(region.pixel_count),
                                    "region_coverage_fraction": float(count / max(int(region.pixel_count), 1)),
                                    "shell_effective_area_px": int(shell.effective_area_px),
                                    "shell_coverage_fraction": float(count / max(int(shell.effective_area_px), 1)),
                                    "intersection_theta_min_deg": float(np.min(edge_theta)),
                                    "intersection_theta_max_deg": float(np.max(edge_theta)),
                                    "intersection_range_min_m": float(np.min(edge_range)),
                                    "intersection_range_max_m": float(np.max(edge_range)),
                                    "pixel_intersection_used": True,
                                    "physical_target_id_used": False,
                                    "sar_reference_used": False,
                                    "edge_semantics": "GT_BLIND_GEOMETRIC_INTERSECTION_NOT_IDENTITY_OR_FINAL_LOCALIZATION",
                                }
                            )

                    adjacency: dict[str, set[str]] = {}
                    for shell_id, linked in shell_adjacency.items():
                        adjacency[f"S::{shell_id}"] = {f"R::{value}" for value in linked}
                    for region_id, linked in region_adjacency.items():
                        adjacency[f"R::{region_id}"] = {f"S::{value}" for value in linked}
                    node_component: dict[str, tuple[str, str, int, int, int]] = {}
                    visited: set[str] = set()
                    component_counter = 0
                    slice_component_states: list[str] = []
                    for start in adjacency:
                        if start in visited:
                            continue
                        component_counter += 1
                        queue = deque([start])
                        visited.add(start)
                        nodes: list[str] = []
                        while queue:
                            current = queue.popleft()
                            nodes.append(current)
                            for neighbor in adjacency[current]:
                                if neighbor not in visited:
                                    visited.add(neighbor)
                                    queue.append(neighbor)
                        shell_ids = [node[3:] for node in nodes if node.startswith("S::")]
                        region_ids = [node[3:] for node in nodes if node.startswith("R::")]
                        state = topology_state(len(shell_ids), len(region_ids))
                        slice_component_states.append(state)
                        component_id = f"{frame_uid}__{policy}__{percentile_tag}__C{component_counter:04d}"
                        component_edge_count = int(
                            sum(len(shell_adjacency[shell_id]) for shell_id in shell_ids)
                        )
                        component_intersection_pixels = int(
                            sum(
                                edge_count_lookup[(shell_id, region_id)]
                                for shell_id in shell_ids
                                for region_id in shell_adjacency[shell_id]
                            )
                        )
                        component_rows.append(
                            {
                                "run_id": str(frame["run_id"]),
                                "frame_uid": frame_uid,
                                "frame_index": int(frame["sar_frame_index"]),
                                "temporal_policy": policy,
                                "guard_variant": PRIMARY_GUARD,
                                "percentile_tag": percentile_tag,
                                "component_id": component_id,
                                "topology_state": state,
                                "shell_count": int(len(shell_ids)),
                                "region_count": int(len(region_ids)),
                                "edge_count": component_edge_count,
                                "intersection_pixel_count_sum": component_intersection_pixels,
                                "shell_ids": ";".join(sorted(shell_ids)),
                                "region_ids": ";".join(sorted(region_ids)),
                                "gt_blind": True,
                            }
                        )
                        for node in nodes:
                            node_component[node] = (
                                component_id,
                                state,
                                len(shell_ids),
                                len(region_ids),
                                component_edge_count,
                            )

                    for shell in frame_shells.itertuples(index=False):
                        component = node_component[f"S::{shell.shell_id}"]
                        shell_node_rows.append(
                            {
                                "run_id": str(frame["run_id"]),
                                "frame_uid": frame_uid,
                                "frame_index": int(frame["sar_frame_index"]),
                                "temporal_policy": policy,
                                "guard_variant": PRIMARY_GUARD,
                                "percentile_tag": percentile_tag,
                                "shell_id": str(shell.shell_id),
                                "track_id": str(shell.track_id),
                                "shell_degree_region_count": int(len(shell_adjacency[str(shell.shell_id)])),
                                "component_id": component[0],
                                "topology_state": component[1],
                                "component_shell_count": int(component[2]),
                                "component_region_count": int(component[3]),
                                "component_edge_count": int(component[4]),
                                "effective_width_deg": float(shell.effective_width_deg),
                                "effective_area_px": int(shell.effective_area_px),
                                "effective_area_fraction_of_omega": float(shell.effective_area_fraction_of_omega),
                                "total_clip_deg": float(shell.total_clip_deg),
                                "common_fov_overlap_fraction": float(shell.common_fov_overlap_fraction),
                                "source_observation_count": int(shell.source_observation_count),
                                "source_has_future_observation": bool(shell.source_has_future_observation),
                                "source_parent_stitched_ids": str(shell.source_parent_stitched_ids),
                                "candidate_sample_count_in_shell": math.nan,
                                "candidate_sampled_p0_state": "NOT_ATTACHED_YET",
                                "gt_blind": True,
                            }
                        )
                    for region in frame_regions.itertuples(index=False):
                        component = node_component[f"R::{region.region_id}"]
                        region_node_rows.append(
                            {
                                "run_id": str(frame["run_id"]),
                                "frame_uid": frame_uid,
                                "frame_index": int(frame["sar_frame_index"]),
                                "temporal_policy": policy,
                                "guard_variant": PRIMARY_GUARD,
                                "percentile_tag": percentile_tag,
                                "region_id": str(region.region_id),
                                "region_label": int(region.region_label),
                                "region_degree_shell_count": int(len(region_adjacency[str(region.region_id)])),
                                "component_id": component[0],
                                "topology_state": component[1],
                                "component_shell_count": int(component[2]),
                                "component_region_count": int(component[3]),
                                "component_edge_count": int(component[4]),
                                "pixel_count": int(region.pixel_count),
                                "area_m2": float(region.area_m2),
                                "major_extent_m": float(region.major_extent_m),
                                "minor_extent_m": float(region.minor_extent_m),
                                "elongation": float(region.elongation),
                                "structure_state": str(region.structure_state),
                                "range_min_m": float(region.range_min_m),
                                "range_max_m": float(region.range_max_m),
                                "theta_min_deg": float(region.theta_min_deg),
                                "theta_max_deg": float(region.theta_max_deg),
                                "touches_observable_boundary": bool(region.touches_observable_boundary),
                                "has_truncated_support": bool(region.has_truncated_support),
                                "legacy_candidate_artifact_covered": math.nan,
                                "accepted_peak_count_in_region": math.nan,
                                "gt_blind_peak_representation_state": "NOT_ATTACHED_YET",
                                "candidate_sampled_p0_state": "NOT_ATTACHED_YET",
                                "gt_blind": True,
                            }
                        )
                    state_counts = Counter(slice_component_states)
                    frame_rows.append(
                        {
                            "run_id": str(frame["run_id"]),
                            "frame_uid": frame_uid,
                            "frame_index": int(frame["sar_frame_index"]),
                            "temporal_policy": policy,
                            "guard_variant": PRIMARY_GUARD,
                            "percentile_tag": percentile_tag,
                            "shell_node_count": int(len(frame_shells)),
                            "region_node_count": int(len(frame_regions)),
                            "edge_count": int(sum(len(value) for value in shell_adjacency.values())),
                            "component_count": int(component_counter),
                            **{f"component_{state}_count": int(state_counts[state]) for state in (
                                "ONE_SHELL_ONE_REGION",
                                "ONE_SHELL_MULTIPLE_REGIONS",
                                "MULTIPLE_SHELLS_ONE_REGION",
                                "MULTIPLE_SHELLS_MULTIPLE_REGIONS",
                                "SHELL_NO_REGION",
                                "REGION_NO_SHELL",
                            )},
                            "gt_blind": True,
                        }
                    )
        if index % 40 == 0 or index == len(frame_map):
            print(f"pixel topology {index}/{len(frame_map)}", flush=True)
    return (
        pd.DataFrame(edge_rows),
        pd.DataFrame(shell_node_rows),
        pd.DataFrame(region_node_rows),
        pd.DataFrame(component_rows),
        pd.DataFrame(frame_rows),
    )


def summarize_p0_samples(group: pd.DataFrame) -> dict[str, Any]:
    if group.empty:
        return {
            "candidate_sample_count": 0,
            "candidate_sampled_p0_state": "NO_GT_BLIND_CANDIDATE_SAMPLE",
            "candidate_sampled_p0_core_fraction": math.nan,
            "candidate_sampled_p0_extended_fraction": math.nan,
            "candidate_sampled_p0_unavailable_fraction": math.nan,
            "candidate_sampled_p0_sigma_m_median": math.nan,
            "candidate_sampled_p0_fallback_fraction": math.nan,
        }
    domains = group["p0_transport_domain_lag1"].astype(str)
    modes = group["p0_local_anchor_mode_lag1"].astype(str)
    counts = Counter(domains)
    state = max(counts, key=counts.get) if counts else "P0_CONDITION_UNAVAILABLE"
    return {
        "candidate_sample_count": int(len(group)),
        "candidate_sampled_p0_state": state,
        "candidate_sampled_p0_core_fraction": float((domains == "P0_TRANSPORT_CORE").mean()),
        "candidate_sampled_p0_extended_fraction": float((domains == "P0_TRANSPORT_EXTENDED").mean()),
        "candidate_sampled_p0_unavailable_fraction": float((domains == "P0_TRANSPORT_UNAVAILABLE").mean()),
        "candidate_sampled_p0_sigma_m_median": finite_median(group["p0_sigma_m_lag1"]),
        "candidate_sampled_p0_fallback_fraction": float((modes == "NEAREST8_FALLBACK").mean()),
    }


def attach_gt_blind_conditions(
    frames: list[dict[str, Any]],
    shells: pd.DataFrame,
    shell_nodes: pd.DataFrame,
    region_nodes: pd.DataFrame,
    parity: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    usecols = [
        "entity_id", "entity_kind", "run_id", "frame_uid", "frame_index", "x_px", "y_px",
        "azimuth_deg", "display_proxy_robust_shift", "max_adjacent_lag1_display_js", "display_shift",
        "display_observation_state", "p0_transport_domain_lag1", "p0_sigma_m_lag1",
        "p0_local_anchor_mode_lag1", "p0_local_anchor_count_lag1",
    ]
    observations = pd.read_csv(OBSERVATION_TABLE, usecols=usecols)
    candidates = observations[observations["entity_kind"].astype(str).eq("SAR_ONLY_C2_CANDIDATE")].copy()
    frame_display = (
        observations.sort_values(["frame_uid", "entity_id"])
        .drop_duplicates("frame_uid")[[
            "run_id", "frame_uid", "frame_index", "display_proxy_robust_shift",
            "max_adjacent_lag1_display_js", "display_shift", "display_observation_state",
        ]]
        .copy()
    )
    parity_map = parity.set_index("frame_uid")["candidate_artifact_frame_covered"].astype(bool).to_dict()
    frame_map = {str(frame["sar_frame_uid"]): frame for frame in frames}

    region_condition: dict[tuple[str, str, int], dict[str, Any]] = {}
    for frame_uid, frame_candidates in candidates.groupby("frame_uid", sort=False):
        frame_uid = str(frame_uid)
        with np.load(REGION_MASK_DIR / f"{frame_uid}.npz") as archive:
            for tag in PERCENTILE_TAGS:
                labels = archive[tag]
                buckets: dict[int, list[int]] = defaultdict(list)
                for row_index, row in frame_candidates.iterrows():
                    x = int(round(float(row["x_px"])))
                    y = int(round(float(row["y_px"])))
                    if 0 <= x < labels.shape[1] and 0 <= y < labels.shape[0]:
                        label = int(labels[y, x])
                        if label > 0:
                            buckets[label].append(row_index)
                for label, indices in buckets.items():
                    region_condition[(frame_uid, tag, label)] = summarize_p0_samples(
                        frame_candidates.loc[indices]
                    )

    region_output = region_nodes.copy()
    peak_counts: list[float] = []
    peak_states: list[str] = []
    condition_rows: list[dict[str, Any]] = []
    for row in region_output.itertuples(index=False):
        covered = bool(parity_map.get(str(row.frame_uid), False))
        condition = region_condition.get(
            (str(row.frame_uid), str(row.percentile_tag), int(row.region_label)),
            summarize_p0_samples(pd.DataFrame()),
        )
        count = int(condition["candidate_sample_count"])
        peak_counts.append(float(count) if covered else math.nan)
        if not covered:
            peak_states.append("GT_BLIND_PEAK_ARTIFACT_UNAVAILABLE_FOR_FRAME")
        elif count > 0:
            peak_states.append("GT_BLIND_ACCEPTED_PEAK_PRESENT_IN_REGION")
        else:
            peak_states.append("GT_BLIND_ACCEPTED_PEAK_ABSENT_IN_REGION")
        condition_rows.append(condition)
    region_output["legacy_candidate_artifact_covered"] = [
        bool(parity_map.get(str(uid), False)) for uid in region_output["frame_uid"]
    ]
    region_output["accepted_peak_count_in_region"] = peak_counts
    region_output["gt_blind_peak_representation_state"] = peak_states
    for column in condition_rows[0] if condition_rows else []:
        region_output[column] = [row[column] for row in condition_rows]

    shell_lookup = shells.set_index("shell_id")
    candidate_groups = {
        str(uid): group.copy() for uid, group in candidates.groupby("frame_uid", sort=False)
    }
    shell_condition: dict[str, dict[str, Any]] = {}
    for shell_id in shell_nodes["shell_id"].astype(str).unique():
        shell = shell_lookup.loc[shell_id]
        frame_candidates = candidate_groups.get(str(shell["frame_uid"]), pd.DataFrame(columns=candidates.columns))
        if frame_candidates.empty:
            shell_condition[shell_id] = summarize_p0_samples(frame_candidates)
            continue
        intervals = json.loads(shell["effective_intervals_json"])
        inside = frame_candidates["azimuth_deg"].map(lambda theta: interval_contains(float(theta), intervals))
        shell_condition[shell_id] = summarize_p0_samples(frame_candidates[inside])
    shell_output = shell_nodes.copy()
    shell_conditions = [shell_condition[str(shell_id)] for shell_id in shell_output["shell_id"]]
    for column in shell_conditions[0] if shell_conditions else []:
        shell_output[column.replace("candidate_sample_count", "candidate_sample_count_in_shell")] = [
            row[column] for row in shell_conditions
        ]

    region_output = region_output.merge(frame_display, on=["run_id", "frame_uid", "frame_index"], how="left")
    shell_output = shell_output.merge(frame_display, on=["run_id", "frame_uid", "frame_index"], how="left")
    return shell_output, region_output, frame_display


def build_offline_reference_products(
    shells: pd.DataFrame,
    region_nodes: pd.DataFrame,
    observations: pd.DataFrame,
    reference_region: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    references = observations[observations["entity_kind"].astype(str).eq("PERSON_REFERENCE")].copy()
    references = references.drop_duplicates(["run_id", "frame_uid", "target_id"])
    shell_groups = {
        (str(uid), str(policy), str(guard)): group.copy()
        for (uid, policy, guard), group in shells.groupby(
            ["frame_uid", "temporal_policy", "guard_variant"], sort=False
        )
    }
    evaluation_rows: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []
    for frame_uid, frame_refs in references.groupby("frame_uid", sort=False):
        frame_uid = str(frame_uid)
        for policy in TIME_POLICIES:
            for guard in GUARD_VARIANTS:
                frame_shells = shell_groups.get(
                    (frame_uid, policy, guard), pd.DataFrame(columns=shells.columns)
                )
                for ref in frame_refs.itertuples(index=False):
                    theta = float(ref.azimuth_deg)
                    inside_shells: list[str] = []
                    distances: list[float] = []
                    center_distances: list[float] = []
                    for shell in frame_shells.itertuples(index=False):
                        intervals = json.loads(shell.effective_intervals_json)
                        if interval_contains(theta, intervals):
                            inside_shells.append(str(shell.shell_id))
                        distances.append(interval_distance(theta, intervals))
                        center_distances.append(interval_center_distance(theta, intervals))
                    nearest_index = int(np.argmin(distances)) if distances else -1
                    nearest_shell = frame_shells.iloc[nearest_index] if nearest_index >= 0 else None
                    evaluation_rows.append(
                        {
                            "run_id": str(ref.run_id),
                            "frame_uid": frame_uid,
                            "frame_index": int(ref.frame_index),
                            "target_id": str(ref.target_id),
                            "temporal_policy": policy,
                            "guard_variant": guard,
                            "track_shell_count": int(len(frame_shells)),
                            "any_shell_reference_retained": bool(inside_shells),
                            "covering_shell_count": int(len(inside_shells)),
                            "nearest_shell_id": str(nearest_shell.shell_id) if nearest_shell is not None else "",
                            "nearest_shell_angular_distance_deg": float(distances[nearest_index]) if nearest_index >= 0 else math.nan,
                            "nearest_shell_center_distance_deg": float(center_distances[nearest_index]) if nearest_index >= 0 else math.nan,
                            "nearest_shell_effective_area_fraction_of_omega": (
                                float(nearest_shell.effective_area_fraction_of_omega) if nearest_shell is not None else math.nan
                            ),
                            "reference_materialized_after_gt_blind_topology": True,
                            "physical_target_id_used": False,
                        }
                    )
                if len(frame_refs) and len(frame_shells):
                    cost = np.zeros((len(frame_refs), len(frame_shells)), dtype=float)
                    for i, ref in enumerate(frame_refs.itertuples(index=False)):
                        for j, shell in enumerate(frame_shells.itertuples(index=False)):
                            cost[i, j] = interval_center_distance(
                                float(ref.azimuth_deg), json.loads(shell.effective_intervals_json)
                            )
                    row_indices, column_indices = linear_sum_assignment(cost)
                    assigned_ref = set()
                    for i, j in zip(row_indices, column_indices):
                        ref = frame_refs.iloc[int(i)]
                        shell = frame_shells.iloc[int(j)]
                        intervals = json.loads(shell["effective_intervals_json"])
                        assigned_ref.add(int(i))
                        assignment_rows.append(
                            {
                                "run_id": str(ref["run_id"]),
                                "frame_uid": frame_uid,
                                "frame_index": int(ref["frame_index"]),
                                "target_id": str(ref["target_id"]),
                                "temporal_policy": policy,
                                "guard_variant": guard,
                                "associated_shell_id": str(shell["shell_id"]),
                                "associated_track_id": str(shell["track_id"]),
                                "association_cost_center_distance_deg": float(cost[i, j]),
                                "reference_inside_associated_shell": interval_contains(float(ref["azimuth_deg"]), intervals),
                                "associated_shell_effective_width_deg": float(shell["effective_width_deg"]),
                                "associated_shell_area_fraction_of_omega": float(shell["effective_area_fraction_of_omega"]),
                                "associated_shell_intervals_json": str(shell["effective_intervals_json"]),
                                "association_semantics": "OFFLINE_ONE_TO_ONE_ANGULAR_CENTER_ASSIGNMENT_NOT_RUNTIME_IDENTITY",
                            }
                        )
                    for i, ref in frame_refs.reset_index(drop=True).iterrows():
                        if i not in assigned_ref:
                            assignment_rows.append(
                                {
                                    "run_id": str(ref["run_id"]),
                                    "frame_uid": frame_uid,
                                    "frame_index": int(ref["frame_index"]),
                                    "target_id": str(ref["target_id"]),
                                    "temporal_policy": policy,
                                    "guard_variant": guard,
                                    "associated_shell_id": "",
                                    "associated_track_id": "",
                                    "association_cost_center_distance_deg": math.nan,
                                    "reference_inside_associated_shell": False,
                                    "associated_shell_effective_width_deg": math.nan,
                                    "associated_shell_area_fraction_of_omega": math.nan,
                                    "associated_shell_intervals_json": "[]",
                                    "association_semantics": "NO_SHELL_AVAILABLE_FOR_OFFLINE_ONE_TO_ONE_ASSIGNMENT",
                                }
                            )
                elif len(frame_refs):
                    for ref in frame_refs.itertuples(index=False):
                        assignment_rows.append(
                            {
                                "run_id": str(ref.run_id), "frame_uid": frame_uid,
                                "frame_index": int(ref.frame_index), "target_id": str(ref.target_id),
                                "temporal_policy": policy, "guard_variant": guard,
                                "associated_shell_id": "", "associated_track_id": "",
                                "association_cost_center_distance_deg": math.nan,
                                "reference_inside_associated_shell": False,
                                "associated_shell_effective_width_deg": math.nan,
                                "associated_shell_area_fraction_of_omega": math.nan,
                                "associated_shell_intervals_json": "[]",
                                "association_semantics": "NO_SHELL_AVAILABLE_FOR_OFFLINE_ONE_TO_ONE_ASSIGNMENT",
                            }
                        )

    assignments = pd.DataFrame(assignment_rows)
    pair_rows: list[dict[str, Any]] = []
    r02 = assignments[assignments["run_id"] == "R02ZF"]
    pair_specs = {
        "P01_P02": ("R02ZF_SARPERSON01", "R02ZF_SARPERSON02"),
        "P03_P04": ("R02ZF_SARPERSON03", "R02ZF_SARPERSON04"),
    }
    for (frame_uid, policy, guard), group in r02.groupby(
        ["frame_uid", "temporal_policy", "guard_variant"], sort=False
    ):
        by_target = group.set_index("target_id")
        ref_frame = references[references["frame_uid"].astype(str).eq(str(frame_uid))].set_index("target_id")
        for pair_name, (first_target, second_target) in pair_specs.items():
            if first_target not in by_target.index or second_target not in by_target.index:
                continue
            first = by_target.loc[first_target]
            second = by_target.loc[second_target]
            first_intervals = json.loads(first["associated_shell_intervals_json"])
            second_intervals = json.loads(second["associated_shell_intervals_json"])
            pair_rows.append(
                {
                    "run_id": "R02ZF",
                    "frame_uid": str(frame_uid),
                    "frame_index": int(first["frame_index"]),
                    "target_pair": pair_name,
                    "temporal_policy": str(policy),
                    "guard_variant": str(guard),
                    "both_associated_shells_available": bool(first_intervals and second_intervals),
                    "associated_shells_distinct": bool(
                        first["associated_shell_id"] and second["associated_shell_id"]
                        and first["associated_shell_id"] != second["associated_shell_id"]
                    ),
                    "associated_shell_angular_overlap_deg": (
                        interval_overlap_width(first_intervals, second_intervals)
                        if first_intervals and second_intervals else math.nan
                    ),
                    "associated_shell_angular_jaccard": (
                        interval_jaccard(first_intervals, second_intervals)
                        if first_intervals and second_intervals else math.nan
                    ),
                    "reference_angular_separation_deg": (
                        abs(float(ref_frame.loc[first_target, "azimuth_deg"]) - float(ref_frame.loc[second_target, "azimuth_deg"]))
                        if first_target in ref_frame.index and second_target in ref_frame.index else math.nan
                    ),
                    "offline_reference_conditioned": True,
                }
            )

    primary_region_nodes = region_nodes[
        region_nodes["guard_variant"].eq(PRIMARY_GUARD)
    ].copy()
    topology_interpretation = reference_region.merge(
        primary_region_nodes,
        left_on=["run_id", "frame_uid", "frame_index", "percentile_tag", "nearest_region_id"],
        right_on=["run_id", "frame_uid", "frame_index", "percentile_tag", "region_id"],
        how="left",
        suffixes=("_reference", "_topology"),
    )
    topology_interpretation["reference_conditioned_only"] = True
    return pd.DataFrame(evaluation_rows), assignments, pd.DataFrame(pair_rows), topology_interpretation


def build_summary(
    input_checks: list[dict[str, Any]],
    mask_check: dict[str, Any],
    shells: pd.DataFrame,
    frame_shells: pd.DataFrame,
    edges: pd.DataFrame,
    shell_nodes: pd.DataFrame,
    region_nodes: pd.DataFrame,
    components: pd.DataFrame,
    frame_topology: pd.DataFrame,
    reference_eval: pd.DataFrame,
    r02_pairs: pd.DataFrame,
    reference_topology: pd.DataFrame,
    execution_stages: list[dict[str, Any]],
) -> dict[str, Any]:
    decomposition_summary: list[dict[str, Any]] = []
    for (run_id, policy, guard), group in frame_shells.groupby(
        ["run_id", "temporal_policy", "guard_variant"], sort=False
    ):
        available = group[group["track_shell_available"].astype(bool)]
        decomposition_summary.append(
            {
                "run_id": str(run_id),
                "temporal_policy": str(policy),
                "guard_variant": str(guard),
                "frame_count": int(len(group)),
                "available_frame_fraction": bool_fraction(group["track_shell_available"]),
                "active_shell_count_median": finite_median(available["active_raw_fragment_shell_count"]),
                "single_box_width_median_deg": finite_median(available["single_box_width_median_deg"]),
                "temporal_union_increment_median_deg": finite_median(available["temporal_union_increment_median_deg"]),
                "guard_increment_median_deg": finite_median(available["guard_increment_median_deg"]),
                "fan_clip_loss_median_deg": finite_median(available["fan_clip_loss_median_deg"]),
                "single_track_width_median_deg": finite_median(available["single_track_width_median_deg"]),
                "all_track_union_width_median_deg": finite_median(available["all_track_union_effective_width_deg"]),
                "union_burden_median": finite_median(available["all_track_union_effective_area_fraction_of_omega"]),
                "overlap_redundancy_fraction_median": finite_median(available["angular_overlap_redundancy_fraction_of_sum"]),
                "pairwise_jaccard_max_median": finite_median(available["pairwise_shell_jaccard_max"]),
            }
        )

    retention_summary: list[dict[str, Any]] = []
    for (run_id, policy, guard), group in reference_eval.groupby(
        ["run_id", "temporal_policy", "guard_variant"], sort=False
    ):
        retention_summary.append(
            {
                "run_id": str(run_id),
                "temporal_policy": str(policy),
                "guard_variant": str(guard),
                "reference_count": int(len(group)),
                "any_shell_retention": bool_fraction(group["any_shell_reference_retained"]),
                "covering_shell_count_median": finite_median(group["covering_shell_count"]),
                "nearest_shell_burden_median": finite_median(group["nearest_shell_effective_area_fraction_of_omega"]),
            }
        )

    topology_summary: list[dict[str, Any]] = []
    for (run_id, policy, tag), group in components.groupby(
        ["run_id", "temporal_policy", "percentile_tag"], sort=False
    ):
        counts = Counter(group["topology_state"].astype(str))
        topology_summary.append(
            {
                "run_id": str(run_id),
                "temporal_policy": str(policy),
                "percentile_tag": str(tag),
                "component_count": int(len(group)),
                "topology_state_counts": dict(counts),
                "one_shell_multiple_region_fraction": float(
                    (group["topology_state"] == "ONE_SHELL_MULTIPLE_REGIONS").mean()
                ),
                "multiple_shell_one_region_fraction": float(
                    (group["topology_state"] == "MULTIPLE_SHELLS_ONE_REGION").mean()
                ),
                "multiple_multiple_fraction": float(
                    (group["topology_state"] == "MULTIPLE_SHELLS_MULTIPLE_REGIONS").mean()
                ),
            }
        )

    r02_pair_summary: list[dict[str, Any]] = []
    for (pair_name, policy, guard), group in r02_pairs.groupby(
        ["target_pair", "temporal_policy", "guard_variant"], sort=False
    ):
        available = group[group["both_associated_shells_available"].astype(bool)]
        r02_pair_summary.append(
            {
                "target_pair": str(pair_name),
                "temporal_policy": str(policy),
                "guard_variant": str(guard),
                "frame_count": int(len(group)),
                "both_shells_available_fraction": bool_fraction(group["both_associated_shells_available"]),
                "associated_shell_jaccard_median": finite_median(available["associated_shell_angular_jaccard"]),
                "associated_shell_jaccard_p90": finite_quantile(available["associated_shell_angular_jaccard"], 0.90),
                "associated_shell_overlap_median_deg": finite_median(available["associated_shell_angular_overlap_deg"]),
            }
        )

    q95_shared = reference_topology[
        (reference_topology["percentile_tag"] == "Q095")
        & reference_topology["shared_region_flag"].astype(bool)
    ]
    shared_topology_counts = Counter(q95_shared["topology_state"].dropna().astype(str))
    cases = reference_topology[
        (reference_topology["run_id"] == "R02ZF")
        & (reference_topology["frame_index"].isin([482, 490]))
        & (reference_topology["percentile_tag"] == "Q095")
    ][[
        "run_id", "frame_uid", "frame_index", "target_id", "representation_state",
        "shared_region_flag", "nearest_region_id", "temporal_policy", "topology_state",
        "component_shell_count", "component_region_count", "region_degree_shell_count",
    ]].to_dict("records")

    return {
        "schema": "PERSON_P1E_SHELL_UNCERTAINTY_REGION_TOPOLOGY_V1",
        "status": "COMPLETE_NO_NEW_PASS_FAIL_NO_P2_CLAIM",
        "generated_at": now_iso(),
        "python_executable": sys.executable,
        "workspace": str(WORKSPACE),
        "output_dir": str(OUTPUT_DIR),
        "input_hash_checks": input_checks,
        "mask_manifest_check": mask_check,
        "execution_stages": execution_stages,
        "counts": {
            "shell_rows": int(len(shells)),
            "frame_shell_summary_rows": int(len(frame_shells)),
            "pixel_edge_rows": int(len(edges)),
            "shell_node_rows": int(len(shell_nodes)),
            "region_node_rows": int(len(region_nodes)),
            "component_rows": int(len(components)),
            "frame_topology_rows": int(len(frame_topology)),
            "reference_evaluation_rows": int(len(reference_eval)),
            "r02_pair_rows": int(len(r02_pairs)),
        },
        "boundaries": {
            "main_optical_interface": "RAW_DETECTED_FRAGMENT_ALL",
            "runtime_optical_identity_established": False,
            "parent_stitched_id_semantics": "GT_BLIND_OFFLINE_CONTINUITY_PROVENANCE_ONLY",
            "physical_target_id_used_for_runtime_products": False,
            "sar_reference_used_for_shell_region_edge_or_topology": False,
            "reference_materialized_after_topology": True,
            "response_region_is_person_box": False,
            "sar_range_generated": False,
            "new_total_score_or_classifier": False,
            "p2_claim": False,
        },
        "shell_uncertainty_decomposition": decomposition_summary,
        "offline_reference_retention": retention_summary,
        "r02_associated_shell_separability": r02_pair_summary,
        "gt_blind_topology": topology_summary,
        "q95_shared_reference_topology_counts": dict(shared_topology_counts),
        "r02_f482_f490_reference_conditioned_topology": cases,
        "interpretation_guardrails": [
            "G2P652 and G0 are geometry-only counterfactuals, not deployable calibrated shells.",
            "A pure mapping intercept correction shifts a shell but does not shrink its optical box span.",
            "Candidate-sampled P0 condition is unavailable where the legacy GT-blind candidate artifact has no frame coverage.",
            "Topology states are ambiguity structures, not physical identity or final localization.",
            "Shared region is image-domain overlap, not physical scattering fusion proof.",
        ],
    }


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(SCRIPT_PATH).lower() or "old_work" in str(OUTPUT_DIR).lower():
        raise RuntimeError("forbidden old_work dependency")
    if not PROTOCOL_PATH.is_file():
        raise FileNotFoundError(PROTOCOL_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    input_checks: list[dict[str, Any]] = []
    for path, expected in EXPECTED_HASHES.items():
        actual = sha256_file(path)
        input_checks.append(
            {"path": str(path), "expected_sha256": expected, "actual_sha256": actual, "match": actual == expected}
        )
    if not all(row["match"] for row in input_checks):
        raise RuntimeError(f"frozen dependency hash mismatch: {[row for row in input_checks if not row['match']]}")
    mask_count, mask_aggregate = mask_manifest_aggregate(REGION_MASK_DIR)
    mask_check = {
        "mask_count": mask_count,
        "expected_mask_count": EXPECTED_MASK_COUNT,
        "aggregate_sha256": mask_aggregate,
        "expected_aggregate_sha256": EXPECTED_MASK_AGGREGATE,
        "match": mask_count == EXPECTED_MASK_COUNT and mask_aggregate == EXPECTED_MASK_AGGREGATE,
    }
    if not mask_check["match"]:
        raise RuntimeError(f"response-region mask manifest mismatch: {mask_check}")

    previous = load_module("person_previous_shell_region", PREVIOUS_SCRIPT)
    candidate_module = load_module("person_candidate_shell_uncertainty", CANDIDATE_SCRIPT)
    shell_module = load_module("person_shell_geometry_uncertainty", SHELL_SCRIPT)
    frames, process_note = previous.load_explorer_sanitized()
    frames.sort(key=lambda row: (row["run_id"], row["sar_frame_index"]))
    if len(frames) != EXPECTED_MASK_COUNT:
        raise RuntimeError(f"frame count mismatch: {len(frames)}")
    hypotheses = pd.read_parquet(OPTICAL_HYPOTHESES)
    raw_by_run = prepare_raw_observations(hypotheses)
    regions = pd.read_csv(REGION_TABLE)
    parity = pd.read_csv(CANDIDATE_PARITY)

    execution_stages = [
        {"stage": "FROZEN_DEPENDENCY_AND_MASK_HASH_CHECK", "completed_at": now_iso()},
        {"stage": "OPTICAL_RAW_FRAGMENT_PROVENANCE_LOADED_WITHOUT_SAR_REFERENCE", "completed_at": now_iso()},
    ]
    shells, frame_shells, shell_overlaps = build_shell_products(
        frames, raw_by_run, candidate_module, shell_module
    )
    shells.to_csv(OUTPUT_DIR / "optical_shell_uncertainty_decomposition_pre_reference.csv", index=False, encoding="utf-8-sig")
    frame_shells.to_csv(OUTPUT_DIR / "frame_shell_uncertainty_summary_pre_reference.csv", index=False, encoding="utf-8-sig")
    shell_overlaps.to_csv(OUTPUT_DIR / "gt_blind_shell_pair_overlap_pre_reference.csv", index=False, encoding="utf-8-sig")
    execution_stages.append(
        {"stage": "ALL_SHELL_UNCERTAINTY_VARIANTS_GENERATED_WITHOUT_SAR_REFERENCE", "completed_at": now_iso(), "rows": int(len(shells))}
    )

    edges, shell_nodes, region_nodes, components, frame_topology = build_topology_products(
        frames, shells, regions
    )
    edges.to_csv(OUTPUT_DIR / "gt_blind_shell_region_pixel_edges_pre_reference.csv", index=False, encoding="utf-8-sig")
    shell_nodes.to_csv(OUTPUT_DIR / "gt_blind_shell_nodes_pre_reference.csv", index=False, encoding="utf-8-sig")
    region_nodes.to_csv(OUTPUT_DIR / "gt_blind_region_nodes_pre_reference.csv", index=False, encoding="utf-8-sig")
    components.to_csv(OUTPUT_DIR / "gt_blind_bipartite_components_pre_reference.csv", index=False, encoding="utf-8-sig")
    frame_topology.to_csv(OUTPUT_DIR / "gt_blind_frame_topology_summary_pre_reference.csv", index=False, encoding="utf-8-sig")
    execution_stages.append(
        {"stage": "ALL_PIXEL_EDGES_AND_BIPARTITE_TOPOLOGY_GENERATED_WITHOUT_SAR_REFERENCE", "completed_at": now_iso(), "edge_rows": int(len(edges))}
    )
    pre_reference_manifest = {
        "generated_at": now_iso(),
        "shell_table_sha256": sha256_file(OUTPUT_DIR / "optical_shell_uncertainty_decomposition_pre_reference.csv"),
        "edge_table_sha256": sha256_file(OUTPUT_DIR / "gt_blind_shell_region_pixel_edges_pre_reference.csv"),
        "component_table_sha256": sha256_file(OUTPUT_DIR / "gt_blind_bipartite_components_pre_reference.csv"),
        "reference_loaded": False,
        "process_note": process_note,
    }
    (OUTPUT_DIR / "pre_reference_manifest.json").write_text(
        json.dumps(json_safe(pre_reference_manifest), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    shell_nodes, region_nodes, frame_display = attach_gt_blind_conditions(
        frames, shells, shell_nodes, region_nodes, parity
    )
    shell_nodes.to_csv(OUTPUT_DIR / "gt_blind_shell_nodes_with_conditions.csv", index=False, encoding="utf-8-sig")
    region_nodes.to_csv(OUTPUT_DIR / "gt_blind_region_nodes_with_conditions.csv", index=False, encoding="utf-8-sig")
    frame_display.to_csv(OUTPUT_DIR / "frame_display_conditions.csv", index=False, encoding="utf-8-sig")
    execution_stages.append(
        {"stage": "GT_BLIND_CANDIDATE_SAMPLED_P0_AND_FRAME_DISPLAY_CONDITIONS_ATTACHED", "completed_at": now_iso()}
    )

    observation_usecols = [
        "entity_id", "entity_kind", "run_id", "frame_uid", "frame_index", "target_id", "azimuth_deg"
    ]
    observations_for_reference = pd.read_csv(OBSERVATION_TABLE, usecols=observation_usecols)
    reference_region = pd.read_csv(REFERENCE_REGION_EVAL)
    reference_eval, assignments, r02_pairs, reference_topology = build_offline_reference_products(
        shells, region_nodes, observations_for_reference, reference_region
    )
    reference_eval.to_csv(OUTPUT_DIR / "offline_reference_shell_retention.csv", index=False, encoding="utf-8-sig")
    assignments.to_csv(OUTPUT_DIR / "offline_reference_one_to_one_shell_assignment.csv", index=False, encoding="utf-8-sig")
    r02_pairs.to_csv(OUTPUT_DIR / "offline_r02_associated_shell_separability.csv", index=False, encoding="utf-8-sig")
    reference_topology.to_csv(OUTPUT_DIR / "offline_reference_region_topology_interpretation.csv", index=False, encoding="utf-8-sig")
    execution_stages.append(
        {"stage": "MANUAL_REFERENCE_MATERIALIZED_ONLY_FOR_OFFLINE_INTERPRETATION", "completed_at": now_iso(), "reference_rows": int(len(reference_eval))}
    )

    summary = build_summary(
        input_checks, mask_check, shells, frame_shells, edges, shell_nodes, region_nodes,
        components, frame_topology, reference_eval, r02_pairs, reference_topology,
        execution_stages,
    )
    (OUTPUT_DIR / "diagnostic_summary.json").write_text(
        json.dumps(json_safe(summary), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT_DIR / "execution_ledger.json").write_text(
        json.dumps(json_safe(execution_stages), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(json_safe({"status": summary["status"], "counts": summary["counts"]}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
