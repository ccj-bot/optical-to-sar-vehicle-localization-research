"""M0B1 R02 raw-fragment interval angular-direction diagnostic.

Optical observations provide time/azimuth branch hypotheses only. SAR q95
regions and frozen P0 transport remain the image-domain evidence. This script
does not select a track, delete a hypothesis, fit timing, or localize a PERSON.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict, deque
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
STUDY_OUTPUT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OUTPUT_DIR = STUDY_OUTPUT / "m0b1_r02_raw_fragment_angular_direction_diagnostic"
PROTOCOL_PATH = OUTPUT_DIR / "M0B1_R02_RAW_FRAGMENT_ANGULAR_DIRECTION_PROTOCOL_FROZEN_BEFORE_RUN.md"
FREEZE_PATH = OUTPUT_DIR / "protocol_freeze.json"
LEDGER_PATH = OUTPUT_DIR / "execution_ledger.json"

M0A_ROOT = STUDY_OUTPUT / "m0a_r02_lag1_q95_region_support_transport_pilot"
M0AR_ROOT = STUDY_OUTPUT / "m0a_r_robustness_and_semantic_audit"
TOPOLOGY_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface" / "shell_uncertainty_region_topology_v1"
REGION_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface" / "runtime_track_response_region_minimal_v1"

M0A_PROTOCOL = M0A_ROOT / "M0A_R02_LAG1_Q95_REGION_SUPPORT_TRANSPORT_PROTOCOL_FROZEN_BEFORE_RUN.md"
M0A_MATRIX = M0A_ROOT / "pre_reference_compatibility_matrix.csv"
M0A_NODES = M0A_ROOT / "pre_reference_region_nodes.csv"
M0A_MATCHED = M0A_ROOT / "pre_reference_matched_alternative_sets.csv"
M0A_PRE_CASES = M0A_ROOT / "pre_reference_case_registry.csv"
M0A_SUPPORTED = M0A_ROOT / "post_reference_supported_explanations.csv"
M0A_MATCHED_EVAL = M0A_ROOT / "post_reference_matched_alternative_evaluation.csv"
M0AR_PROTOCOL = M0AR_ROOT / "M0A_R_ROBUSTNESS_AND_SEMANTIC_AUDIT_PROTOCOL_FROZEN_BEFORE_RUN.md"
M0AR_SUMMARY = M0AR_ROOT / "audit_summary.json"

TOPOLOGY_PROTOCOL = TOPOLOGY_ROOT / "00_SHELL_UNCERTAINTY_REGION_TOPOLOGY_PROTOCOL_FROZEN_BEFORE_RUN.md"
TOPOLOGY_EDGES = TOPOLOGY_ROOT / "gt_blind_shell_region_pixel_edges_pre_reference.csv"
REGION_MASK_DIR = REGION_ROOT / "response_region_masks"
OPTICAL_HYPOTHESES = (
    WORKSPACE
    / "output"
    / "person_optical_guided_sar_annotation_full_20260823"
    / "optical_person_frame_hypotheses.parquet"
)
EXPLORER_PATH = WORKSPACE / "output" / "person_multidimensional_response_explorer_20260823" / "explorer_data.js"
IMAGE_DIR = WORKSPACE / "output" / "pseudocolor_labelstudio_prep_20260722" / "frames" / "sar_pseudocolor" / "R02ZF"

RUN_ID = "R02ZF"
FRAME_START = 472
FRAME_END = 494
PAIR_COUNT = 22
OPTICAL_SLOPE = 0.02666536443690682
OPTICAL_INTERCEPT = -45.502258572693094
OPTICAL_GUARD_DEG = 6.0
NUMERICAL_TOLERANCE_DEG = 1e-12
AREA_CUTS = (70, 209, 587)

TIMING_CONDITIONS = (
    "NOMINAL",
    "SAR_SHIFT_MINUS_1",
    "SAR_SHIFT_PLUS_1",
    "OPTICAL_SHIFT_MINUS_1_NOMINAL_STEP",
    "OPTICAL_SHIFT_PLUS_1_NOMINAL_STEP",
)

PRE_FILES = {
    "query_table": "timing_query_table_pre_reference.csv",
    "relations": "static_endpoint_relations_pre_reference.csv",
    "hypotheses": "dynamic_hypotheses_pre_reference.csv",
    "raw_controls": "raw_fragment_alternative_controls_pre_reference.csv",
    "static_controls": "static_shell_matched_controls_pre_reference.csv",
    "summary": "pre_reference_summary.json",
    "manifest": "pre_reference_manifest.json",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def stable_id(prefix: str, *parts: Any) -> str:
    text = "||".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(text.encode('utf-8')).hexdigest()[:20].upper()}"


def finite_median(values: Iterable[Any]) -> float:
    array = pd.to_numeric(pd.Series(list(values)), errors="coerce").to_numpy(float)
    array = array[np.isfinite(array)]
    return float(np.median(array)) if len(array) else math.nan


def fraction(mask: Iterable[Any]) -> float:
    series = pd.Series(list(mask))
    return float(series.astype(bool).mean()) if len(series) else math.nan


def area_stratum(pixels: Any) -> str:
    numeric = float(pixels)
    if not np.isfinite(numeric):
        return "UNAVAILABLE"
    value = int(numeric)
    if value <= AREA_CUTS[0]:
        return "TINY_Q1"
    if value <= AREA_CUTS[1]:
        return "SMALL_Q2"
    if value <= AREA_CUTS[2]:
        return "MEDIUM_Q3"
    return "LARGE_Q4"


def direction_state(low: float, high: float, prefix: str) -> str:
    if low > NUMERICAL_TOLERANCE_DEG:
        return f"{prefix}_POSITIVE"
    if high < -NUMERICAL_TOLERANCE_DEG:
        return f"{prefix}_NEGATIVE"
    return f"{prefix}_DIRECTION_INDETERMINATE"


def cross_direction(optical: str, sar: str, availability: str) -> str:
    if availability != "ANGULAR_DYNAMIC_AVAILABLE":
        return "DIRECTION_UNAVAILABLE"
    if optical.endswith("INDETERMINATE") or sar.endswith("INDETERMINATE"):
        return "DIRECTION_INDETERMINATE"
    if optical.replace("OPTICAL_", "") == sar.replace("SAR_", ""):
        return "DIRECTION_CONCORDANT"
    return "DIRECTION_CONTRADICTORY"


def load_frames() -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    text = EXPLORER_PATH.read_text(encoding="utf-8")
    payload = json.loads(text[text.index("{") : text.rindex("}") + 1])
    frames: dict[int, dict[str, Any]] = {}
    for source in payload["frames"]:
        if source["run_id"] != RUN_ID:
            continue
        index = int(source["sar_frame_index"])
        if FRAME_START <= index <= FRAME_END:
            frames[index] = {
                "run_id": RUN_ID,
                "frame_uid": str(source["sar_frame_uid"]),
                "frame_index": index,
                "sar_timestamp_ms": int(source["sar_timestamp_ms"]),
                "nominal_optical_frame_index": int(source["nominal_optical_frame_index"]),
                "nominal_optical_timestamp_ms": int(source["nominal_optical_timestamp_ms"]),
                "sync_status": str(source.get("sync_status", "UNVERIFIED")),
                "theta_low_deg": float(source["theta_low_deg"]),
                "theta_high_deg": float(source["theta_high_deg"]),
                "geometry": dict(source["geometry"]),
            }
    if sorted(frames) != list(range(FRAME_START, FRAME_END + 1)):
        raise RuntimeError("unexpected R02 frame registry")
    note = {
        "explorer_container_loaded": True,
        "annotation_content_used": False,
        "strict_process_isolation_claimed": False,
        "sanitized_keys": sorted(next(iter(frames.values()))),
    }
    return frames, note


def load_optical() -> tuple[pd.DataFrame, dict[int, pd.DataFrame]]:
    data = pd.read_parquet(OPTICAL_HYPOTHESES)
    if "physical_target_id" in data.columns:
        raise RuntimeError("optical runtime input contains physical_target_id")
    data = data[
        data["run_id"].eq(RUN_ID) & data["box_source"].astype(str).eq("DETECTED")
    ].copy()
    for column in ("frame_index", "timestamp_ms"):
        data[column] = pd.to_numeric(data[column], errors="raise").astype(int)
    data = data.sort_values(
        ["frame_index", "raw_track_fragment_id", "confidence"],
        ascending=[True, True, False],
    ).drop_duplicates(["frame_index", "raw_track_fragment_id"], keep="first")
    data["track_id"] = data["raw_track_fragment_id"].astype(str)
    data["theta_box_low_deg"] = OPTICAL_SLOPE * pd.to_numeric(data["bbox_x1"], errors="raise") + OPTICAL_INTERCEPT
    data["theta_box_high_deg"] = OPTICAL_SLOPE * pd.to_numeric(data["bbox_x2"], errors="raise") + OPTICAL_INTERCEPT
    counts = data.groupby("track_id")["frame_index"].transform("count")
    data["fragment_observation_count_full_run"] = counts.astype(int)
    return data, {int(index): group.copy() for index, group in data.groupby("frame_index", sort=False)}


def timing_query(condition: str, sar_frame: int, frames: dict[int, dict[str, Any]]) -> tuple[Any, Any, str]:
    if condition == "NOMINAL":
        frame = frames.get(sar_frame)
        return (
            frame["nominal_optical_frame_index"],
            frame["nominal_optical_timestamp_ms"],
            "NOMINAL_EXACT_DECODED_OPTICAL_FRAME",
        ) if frame else (math.nan, math.nan, "SAR_FRAME_OUTSIDE_EXPOSED_REGISTRY")
    if condition in {"SAR_SHIFT_MINUS_1", "SAR_SHIFT_PLUS_1"}:
        shifted = sar_frame + (-1 if condition.endswith("MINUS_1") else 1)
        frame = frames.get(shifted)
        return (
            frame["nominal_optical_frame_index"],
            frame["nominal_optical_timestamp_ms"],
            "QUERY_FROM_FIXED_SHIFTED_SAR_FRAME",
        ) if frame else (math.nan, math.nan, "SHIFTED_SAR_FRAME_OUTSIDE_EXPOSED_REGISTRY")
    frame = frames.get(sar_frame)
    if frame is None:
        return math.nan, math.nan, "SAR_FRAME_OUTSIDE_EXPOSED_REGISTRY"
    shift = -1 if condition == "OPTICAL_SHIFT_MINUS_1_NOMINAL_STEP" else 1
    optical_index = int(frame["nominal_optical_frame_index"]) + shift
    timestamp = int(round(1000.0 * optical_index / 18.0))
    return optical_index, timestamp, "FIXED_DECODED_OPTICAL_FRAME_INDEX_SHIFT"


def polar_theta(frame: dict[str, Any], shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    yy, xx = np.indices((height, width), dtype=np.float32)
    geometry = frame["geometry"]
    cx = float(geometry["center_x_px"])
    cy = float(geometry["center_y_px"])
    return np.degrees(np.arctan2(xx - cx, cy - yy))


def clip_interval(low: float, high: float, fan_low: float, fan_high: float) -> tuple[float, float] | None:
    clipped = (max(float(low), fan_low), min(float(high), fan_high))
    return clipped if clipped[1] > clipped[0] else None


def topology_state(shells: int, regions: int) -> str:
    if shells == 1 and regions == 0:
        return "SHELL_NO_REGION"
    if shells == 0 and regions == 1:
        return "REGION_NO_SHELL"
    if shells == 1 and regions == 1:
        return "ONE_SHELL_ONE_REGION"
    if shells == 1 and regions > 1:
        return "ONE_SHELL_MULTIPLE_REGIONS"
    if shells > 1 and regions == 1:
        return "MULTIPLE_SHELLS_ONE_REGION"
    return "MULTIPLE_SHELLS_MULTIPLE_REGIONS"


def build_queries_and_relations(
    frames: dict[int, dict[str, Any]], optical_by_frame: dict[int, pd.DataFrame], nodes: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    node_lookup = {
        (str(row.frame_uid), int(row.region_label)): row for row in nodes.itertuples(index=False)
    }
    query_rows: list[dict[str, Any]] = []
    relation_rows: list[dict[str, Any]] = []
    for condition in TIMING_CONDITIONS:
        for sar_index, frame in frames.items():
            optical_index, query_ms, query_semantics = timing_query(condition, sar_index, frames)
            available = np.isfinite(float(optical_index))
            observations = optical_by_frame.get(int(optical_index), pd.DataFrame()) if available else pd.DataFrame()
            timestamp_match = bool(
                len(observations) == 0
                or (pd.to_numeric(observations["timestamp_ms"], errors="raise").astype(int) == int(query_ms)).all()
            ) if available else False
            query_rows.append(
                {
                    "run_id": RUN_ID,
                    "timing_condition": condition,
                    "sar_frame_uid": frame["frame_uid"],
                    "sar_frame_index": sar_index,
                    "sar_timestamp_ms": frame["sar_timestamp_ms"],
                    "optical_query_frame_index": optical_index,
                    "optical_query_timestamp_ms": query_ms,
                    "query_semantics": query_semantics,
                    "query_available": available,
                    "raw_observation_count": int(len(observations)),
                    "query_timestamp_matches_decoded_frame": timestamp_match,
                    "sync_status": frame["sync_status"],
                    "reference_used": False,
                }
            )
            if not available or observations.empty:
                continue
            mask_path = REGION_MASK_DIR / f"{frame['frame_uid']}.npz"
            with np.load(mask_path) as archive:
                labels = archive["Q095"]
            theta = polar_theta(frame, labels.shape)
            shell_to_regions: dict[str, set[str]] = defaultdict(set)
            region_to_shells: dict[str, set[str]] = defaultdict(set)
            raw_rows: list[dict[str, Any]] = []
            for obs in observations.itertuples(index=False):
                track_id = str(obs.track_id)
                raw_low = float(obs.theta_box_low_deg)
                raw_high = float(obs.theta_box_high_deg)
                effective = clip_interval(
                    raw_low - OPTICAL_GUARD_DEG,
                    raw_high + OPTICAL_GUARD_DEG,
                    float(frame["theta_low_deg"]),
                    float(frame["theta_high_deg"]),
                )
                if effective is None:
                    continue
                shell_mask = (theta >= effective[0]) & (theta <= effective[1])
                selected_labels = labels[shell_mask & (labels > 0)].astype(int)
                for label in np.unique(selected_labels):
                    node = node_lookup.get((frame["frame_uid"], int(label)))
                    if node is None:
                        continue
                    count = int(np.count_nonzero(selected_labels == int(label)))
                    region_id = str(node.region_id)
                    shell_to_regions[track_id].add(region_id)
                    region_to_shells[region_id].add(track_id)
                    raw_rows.append(
                        {
                            "run_id": RUN_ID,
                            "timing_condition": condition,
                            "frame_uid": frame["frame_uid"],
                            "frame_index": sar_index,
                            "optical_query_frame_index": int(optical_index),
                            "optical_query_timestamp_ms": int(query_ms),
                            "optical_observation_frame_index": int(obs.frame_index),
                            "optical_observation_timestamp_ms": int(obs.timestamp_ms),
                            "track_id": track_id,
                            "region_id": region_id,
                            "region_label": int(label),
                            "raw_theta_low_deg": raw_low,
                            "raw_theta_high_deg": raw_high,
                            "guarded_theta_low_deg": float(effective[0]),
                            "guarded_theta_high_deg": float(effective[1]),
                            "raw_width_deg": raw_high - raw_low,
                            "effective_shell_width_deg": effective[1] - effective[0],
                            "intersection_pixel_count": count,
                            "region_pixel_count": int(node.q95_pixel_count),
                            "region_coverage_fraction": count / max(int(node.q95_pixel_count), 1),
                            "region_area_stratum": area_stratum(node.q95_pixel_count),
                            "region_theta_min_deg": float(node.theta_min_deg),
                            "region_theta_max_deg": float(node.theta_max_deg),
                            "region_theta_mid_deg": float(node.theta_mid_deg),
                            "initial_theta_midpoint_gap_abs_deg": abs(
                                0.5 * (raw_low + raw_high) - float(node.theta_mid_deg)
                            ),
                            "touches_observable_boundary": bool_value(node.touches_observable_boundary),
                            "has_truncated_support": bool_value(node.has_truncated_support),
                            "fragment_observation_count_full_run": int(obs.fragment_observation_count_full_run),
                            "pixel_intersection_used": True,
                            "reference_used": False,
                            "physical_target_id_used": False,
                            "optical_person_id_used": False,
                        }
                    )

            adjacency: dict[str, set[str]] = {}
            for shell, linked in shell_to_regions.items():
                adjacency[f"S::{shell}"] = {f"R::{item}" for item in linked}
            for region, linked in region_to_shells.items():
                adjacency[f"R::{region}"] = {f"S::{item}" for item in linked}
            node_component: dict[str, tuple[str, int, int, int, str]] = {}
            visited: set[str] = set()
            component_index = 0
            for start in sorted(adjacency):
                if start in visited:
                    continue
                component_index += 1
                queue = deque([start])
                visited.add(start)
                members: list[str] = []
                while queue:
                    current = queue.popleft()
                    members.append(current)
                    for neighbor in sorted(adjacency[current]):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                shell_count = sum(item.startswith("S::") for item in members)
                region_count = sum(item.startswith("R::") for item in members)
                edge_count = sum(len(shell_to_regions[item[3:]]) for item in members if item.startswith("S::"))
                state = topology_state(shell_count, region_count)
                component_id = f"{frame['frame_uid']}__{condition}__Q095__C{component_index:04d}"
                for member in members:
                    node_component[member] = (component_id, shell_count, region_count, edge_count, state)
            for row in raw_rows:
                component = node_component[f"R::{row['region_id']}"]
                row.update(
                    {
                        "shell_degree_region_count": len(shell_to_regions[row["track_id"]]),
                        "region_degree_shell_count": len(region_to_shells[row["region_id"]]),
                        "component_id": component[0],
                        "component_shell_count": component[1],
                        "component_region_count": component[2],
                        "component_edge_count": component[3],
                        "static_topology_state": component[4],
                    }
                )
                relation_rows.append(row)
    queries = pd.DataFrame(query_rows)
    relations = pd.DataFrame(relation_rows)
    return queries, relations


def feature_bin(series: pd.Series, bins: int = 4) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    ranked = numeric.rank(method="first", pct=True)
    return np.minimum((ranked * bins).fillna(0).astype(int), bins - 1)


def build_hypotheses(
    matrix: pd.DataFrame,
    relations: pd.DataFrame,
    queries: pd.DataFrame,
) -> pd.DataFrame:
    relation_groups = {
        (str(frame_uid), str(timing_condition), str(region_id)): group.copy()
        for (frame_uid, timing_condition, region_id), group in relations.groupby(
            ["frame_uid", "timing_condition", "region_id"], sort=False
        )
    }
    query_lookup = {
        (str(row.sar_frame_uid), str(row.timing_condition)): row
        for row in queries.itertuples(index=False)
    }
    rows: list[dict[str, Any]] = []
    for condition in TIMING_CONDITIONS:
        for edge in matrix.itertuples(index=False):
            source = relation_groups.get((str(edge.from_frame_uid), condition, str(edge.source_region_id)))
            destination = relation_groups.get((str(edge.to_frame_uid), condition, str(edge.destination_region_id)))
            destination_region_pixels = (
                int(destination.iloc[0]["region_pixel_count"])
                if destination is not None and not destination.empty
                else math.nan
            )
            source_query = query_lookup[(str(edge.from_frame_uid), condition)]
            destination_query = query_lookup[(str(edge.to_frame_uid), condition)]
            base = {
                "run_id": RUN_ID,
                "timing_condition": condition,
                "pair_index": int(edge.pair_index),
                "from_frame_uid": str(edge.from_frame_uid),
                "to_frame_uid": str(edge.to_frame_uid),
                "from_frame": int(edge.from_frame),
                "to_frame": int(edge.to_frame),
                "base_edge_id": str(edge.base_edge_id),
                "source_region_id": str(edge.source_region_id),
                "destination_region_id": str(edge.destination_region_id),
                "p0_q95_retention": float(edge.q95_source_total_retention),
                "p0_rank_percentile": float(getattr(edge, "destination_rank_percentile", math.nan)),
                "source_region_area_stratum": area_stratum(edge.source_support_total),
                "destination_region_area_stratum": area_stratum(destination_region_pixels),
                "source_theta_min_deg": float(edge.source_theta_min_deg),
                "source_theta_max_deg": float(edge.source_theta_max_deg),
                "destination_theta_min_deg": float(edge.destination_theta_min_deg),
                "destination_theta_max_deg": float(edge.destination_theta_max_deg),
                "sar_delta_interval_low_deg": float(edge.destination_theta_min_deg - edge.source_theta_max_deg),
                "sar_delta_interval_high_deg": float(edge.destination_theta_max_deg - edge.source_theta_min_deg),
                "source_touches_boundary": bool_value(edge.source_touches_observable_boundary),
                "destination_touches_boundary": bool_value(edge.destination_touches_observable_boundary),
                "source_truncated": bool_value(edge.source_has_truncated_support),
                "destination_truncated": bool_value(edge.destination_has_truncated_support),
                "p0_available": bool_value(edge.p0_model_available) and bool_value(edge.pair_comparable),
                "reference_used": False,
                "identity_assignment_performed": False,
                "hypothesis_pruned": False,
            }
            sar_state = direction_state(
                base["sar_delta_interval_low_deg"], base["sar_delta_interval_high_deg"], "SAR"
            )
            if source is None or destination is None or source.empty or destination.empty:
                reason = "STATIC_SHELL_REGION_INTERSECTION_MISSING"
                if not bool(source_query.query_available) or not bool(destination_query.query_available):
                    reason = "ANGULAR_DYNAMIC_UNAVAILABLE_OBSERVATION"
                elif int(source_query.raw_observation_count) == 0 or int(destination_query.raw_observation_count) == 0:
                    reason = "ANGULAR_DYNAMIC_UNAVAILABLE_OBSERVATION"
                hypothesis_id = stable_id("H", condition, edge.base_edge_id, "NO_STATIC_PAIR")
                rows.append(
                    {
                        **base,
                        "hypothesis_id": hypothesis_id,
                        "source_track_id": "UNAVAILABLE",
                        "destination_track_id": "UNAVAILABLE",
                        "static_feasible": False,
                        "hard_infeasible_reason": reason,
                        "angular_availability_state": reason,
                        "source_optical_frame_index": source_query.optical_query_frame_index,
                        "destination_optical_frame_index": destination_query.optical_query_frame_index,
                        "source_optical_timestamp_ms": source_query.optical_query_timestamp_ms,
                        "destination_optical_timestamp_ms": destination_query.optical_query_timestamp_ms,
                        "optical_delta_interval_low_deg": math.nan,
                        "optical_delta_interval_high_deg": math.nan,
                        "optical_direction_state": "OPTICAL_DIRECTION_UNAVAILABLE",
                        "sar_direction_state": sar_state,
                        "cross_modal_direction_state": "DIRECTION_UNAVAILABLE",
                    }
                )
                continue
            for source_rel, destination_rel in itertools.product(
                source.itertuples(index=False), destination.itertuples(index=False)
            ):
                same_fragment = str(source_rel.track_id) == str(destination_rel.track_id)
                same_sample = (
                    int(source_rel.optical_observation_frame_index)
                    == int(destination_rel.optical_observation_frame_index)
                )
                if not same_fragment:
                    availability = "ANGULAR_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK"
                elif same_sample:
                    availability = "ANGULAR_DYNAMIC_UNAVAILABLE_SAME_OPTICAL_SAMPLE"
                else:
                    availability = "ANGULAR_DYNAMIC_AVAILABLE"
                optical_low = float(destination_rel.raw_theta_low_deg - source_rel.raw_theta_high_deg)
                optical_high = float(destination_rel.raw_theta_high_deg - source_rel.raw_theta_low_deg)
                optical_state = (
                    direction_state(optical_low, optical_high, "OPTICAL")
                    if availability == "ANGULAR_DYNAMIC_AVAILABLE"
                    else "OPTICAL_DIRECTION_UNAVAILABLE"
                )
                hypothesis_id = stable_id(
                    "H",
                    condition,
                    edge.base_edge_id,
                    source_rel.track_id,
                    destination_rel.track_id,
                )
                rows.append(
                    {
                        **base,
                        "hypothesis_id": hypothesis_id,
                        "source_track_id": str(source_rel.track_id),
                        "destination_track_id": str(destination_rel.track_id),
                        "static_feasible": True,
                        "hard_infeasible_reason": "",
                        "angular_availability_state": availability,
                        "source_optical_frame_index": int(source_rel.optical_observation_frame_index),
                        "destination_optical_frame_index": int(destination_rel.optical_observation_frame_index),
                        "source_optical_timestamp_ms": int(source_rel.optical_observation_timestamp_ms),
                        "destination_optical_timestamp_ms": int(destination_rel.optical_observation_timestamp_ms),
                        "source_raw_theta_low_deg": float(source_rel.raw_theta_low_deg),
                        "source_raw_theta_high_deg": float(source_rel.raw_theta_high_deg),
                        "destination_raw_theta_low_deg": float(destination_rel.raw_theta_low_deg),
                        "destination_raw_theta_high_deg": float(destination_rel.raw_theta_high_deg),
                        "source_shell_width_deg": float(source_rel.effective_shell_width_deg),
                        "destination_shell_width_deg": float(destination_rel.effective_shell_width_deg),
                        "source_intersection_pixel_count": int(source_rel.intersection_pixel_count),
                        "destination_intersection_pixel_count": int(destination_rel.intersection_pixel_count),
                        "source_region_coverage_fraction": float(source_rel.region_coverage_fraction),
                        "destination_region_coverage_fraction": float(destination_rel.region_coverage_fraction),
                        "source_region_degree": int(source_rel.region_degree_shell_count),
                        "destination_region_degree": int(destination_rel.region_degree_shell_count),
                        "source_component_shell_count": int(source_rel.component_shell_count),
                        "destination_component_shell_count": int(destination_rel.component_shell_count),
                        "source_component_region_count": int(source_rel.component_region_count),
                        "destination_component_region_count": int(destination_rel.component_region_count),
                        "source_topology_state": str(source_rel.static_topology_state),
                        "destination_topology_state": str(destination_rel.static_topology_state),
                        "source_initial_theta_gap_abs_deg": float(source_rel.initial_theta_midpoint_gap_abs_deg),
                        "destination_initial_theta_gap_abs_deg": float(destination_rel.initial_theta_midpoint_gap_abs_deg),
                        "source_fragment_observation_count": int(source_rel.fragment_observation_count_full_run),
                        "destination_fragment_observation_count": int(destination_rel.fragment_observation_count_full_run),
                        "optical_delta_interval_low_deg": optical_low,
                        "optical_delta_interval_high_deg": optical_high,
                        "optical_delta_interval_width_deg": optical_high - optical_low,
                        "optical_midpoint_change_deg": 0.5 * (
                            destination_rel.raw_theta_low_deg
                            + destination_rel.raw_theta_high_deg
                            - source_rel.raw_theta_low_deg
                            - source_rel.raw_theta_high_deg
                        ),
                        "optical_direction_state": optical_state,
                        "sar_direction_state": sar_state,
                        "cross_modal_direction_state": cross_direction(optical_state, sar_state, availability),
                    }
                )
    hypotheses = pd.DataFrame(rows)
    feasible = hypotheses["static_feasible"].astype(bool)
    for column in (
        "source_shell_width_deg",
        "destination_shell_width_deg",
        "source_initial_theta_gap_abs_deg",
        "destination_initial_theta_gap_abs_deg",
        "source_region_coverage_fraction",
        "destination_region_coverage_fraction",
    ):
        hypotheses[f"{column}_bin"] = -1
        hypotheses.loc[feasible, f"{column}_bin"] = feature_bin(hypotheses.loc[feasible, column]).to_numpy()
    return hypotheses


def static_distance(first: pd.Series, second: pd.Series) -> float:
    columns = (
        "source_shell_width_deg",
        "destination_shell_width_deg",
        "source_initial_theta_gap_abs_deg",
        "destination_initial_theta_gap_abs_deg",
        "source_region_coverage_fraction",
        "destination_region_coverage_fraction",
        "source_fragment_observation_count",
        "destination_fragment_observation_count",
    )
    total = 0.0
    for column in columns:
        a = float(first[column])
        b = float(second[column])
        scale = max(abs(a), abs(b), 1.0)
        total += abs(a - b) / scale
    return total


def choose_controls(hypotheses: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    available = hypotheses[
        hypotheses["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE")
    ].copy()
    raw_rows: list[dict[str, Any]] = []
    static_rows: list[dict[str, Any]] = []
    for _, group in available.groupby(["timing_condition", "base_edge_id"], sort=False):
        ordered = group.sort_values("hypothesis_id")
        for _, primary in ordered.iterrows():
            candidates = ordered[
                ordered["hypothesis_id"].ne(primary["hypothesis_id"])
                & ordered["source_track_id"].ne(primary["source_track_id"])
            ]
            if len(candidates):
                scored = [
                    (static_distance(primary, row), str(row["hypothesis_id"]))
                    for _, row in candidates.iterrows()
                ]
                distance, control_id = min(scored, key=lambda item: (item[0], item[1]))
                raw_rows.append(
                    {
                        "primary_hypothesis_id": primary["hypothesis_id"],
                        "control_hypothesis_id": control_id,
                        "control_family": "GT_BLIND_ALTERNATIVE_RAW_FRAGMENT_NOT_KNOWN_WRONG",
                        "static_distance": distance,
                        "direction_used_for_selection": False,
                        "reference_used_for_selection": False,
                    }
                )

    exact_columns = [
        "timing_condition",
        "pair_index",
        "source_region_area_stratum",
        "destination_region_area_stratum",
        "source_region_degree",
        "destination_region_degree",
        "source_component_shell_count",
        "destination_component_shell_count",
        "source_touches_boundary",
        "destination_touches_boundary",
        "source_shell_width_deg_bin",
        "destination_shell_width_deg_bin",
        "source_initial_theta_gap_abs_deg_bin",
        "destination_initial_theta_gap_abs_deg_bin",
    ]
    relaxed_columns = exact_columns[:10] + exact_columns[10:12]
    selected: set[str] = set()
    for tier, columns in (("EXACT_STATIC_BIN_MATCH", exact_columns), ("RELAXED_STATIC_BIN_MATCH", relaxed_columns)):
        remaining = available[~available["hypothesis_id"].isin(selected)]
        for _, group in remaining.groupby(columns, dropna=False, sort=False):
            if len(group) < 2 or group["base_edge_id"].nunique() < 2:
                continue
            ordered = group.sort_values("hypothesis_id")
            records = list(ordered.iterrows())
            for _, primary in records:
                candidates = [row for _, row in records if row["base_edge_id"] != primary["base_edge_id"]]
                if not candidates:
                    continue
                control = min(
                    candidates,
                    key=lambda row: (static_distance(primary, row), str(row["hypothesis_id"])),
                )
                static_rows.append(
                    {
                        "primary_hypothesis_id": primary["hypothesis_id"],
                        "control_hypothesis_id": control["hypothesis_id"],
                        "control_family": "STATIC_SHELL_MATCHED_COMPOSITE_NULL",
                        "match_tier": tier,
                        "static_distance": static_distance(primary, control),
                        "direction_used_for_selection": False,
                        "reference_used_for_selection": False,
                    }
                )
                selected.add(str(primary["hypothesis_id"]))
    raw_columns = [
        "primary_hypothesis_id",
        "control_hypothesis_id",
        "control_family",
        "static_distance",
        "direction_used_for_selection",
        "reference_used_for_selection",
    ]
    static_columns = [
        "primary_hypothesis_id",
        "control_hypothesis_id",
        "control_family",
        "match_tier",
        "static_distance",
        "direction_used_for_selection",
        "reference_used_for_selection",
    ]
    return pd.DataFrame(raw_rows, columns=raw_columns), pd.DataFrame(static_rows, columns=static_columns)


def manifest_payload(paths: Iterable[Path], schema: str, reference_loaded: bool) -> dict[str, Any]:
    return {
        "schema": schema,
        "created_at": now_iso(),
        "reference_loaded": reference_loaded,
        "files": [
            {
                "path": str(path.relative_to(WORKSPACE)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in paths
        ],
    }


def run_freeze() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not PROTOCOL_PATH.is_file():
        raise FileNotFoundError("frozen protocol must exist before freeze phase")
    inputs = [
        M0A_PROTOCOL,
        M0A_MATRIX,
        M0A_NODES,
        M0A_MATCHED,
        M0A_PRE_CASES,
        M0AR_PROTOCOL,
        M0AR_SUMMARY,
        TOPOLOGY_PROTOCOL,
        TOPOLOGY_EDGES,
        OPTICAL_HYPOTHESES,
        EXPLORER_PATH,
    ]
    payload = {
        "schema": "PERSON_M0B1_PROTOCOL_FREEZE_V1",
        "status": "FROZEN_BEFORE_RUN",
        "frozen_at": now_iso(),
        "starting_head": "69d7b5c97f391a37f8f986c66739dc982f4a1fb5",
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "runner_sha256": sha256_file(SCRIPT_PATH),
        "validator_sha256": sha256_file(TASK_DIR / "validate_m0b1_raw_fragment_angular_direction.py"),
        "input_hashes": [
            {"path": str(path.relative_to(WORKSPACE)), "sha256": sha256_file(path)} for path in inputs
        ],
        "timing_conditions": list(TIMING_CONDITIONS),
        "numerical_tolerance_deg": NUMERICAL_TOLERANCE_DEG,
        "optical_guard_static_feasibility_deg_each_side": OPTICAL_GUARD_DEG,
        "direction_uses_guard": False,
        "pareto_role": "NOT_EXECUTED_DESCRIPTIVE_ONLY_NO_PRUNING",
        "m0b2_executed": False,
    }
    write_json(FREEZE_PATH, payload)
    write_json(
        LEDGER_PATH,
        {
            "schema": "PERSON_M0B1_EXECUTION_LEDGER_V1",
            "events": [
                {"stage": "PROTOCOL_CODE_INPUT_HASHES_FROZEN", "completed_at": now_iso()},
                {"stage": "REFERENCE_NOT_LOADED", "completed_at": now_iso()},
            ],
        },
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def verify_freeze(include_reference: bool = False) -> dict[str, Any]:
    freeze = read_json(FREEZE_PATH)
    if freeze["status"] != "FROZEN_BEFORE_RUN":
        raise RuntimeError("protocol is not frozen")
    if sha256_file(PROTOCOL_PATH) != freeze["protocol_sha256"]:
        raise RuntimeError("protocol changed after freeze")
    if sha256_file(SCRIPT_PATH) != freeze["runner_sha256"]:
        raise RuntimeError("runner changed after freeze")
    validator = TASK_DIR / "validate_m0b1_raw_fragment_angular_direction.py"
    if sha256_file(validator) != freeze["validator_sha256"]:
        raise RuntimeError("validator changed after freeze")
    for item in freeze["input_hashes"]:
        path = WORKSPACE / item["path"]
        if sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"input changed after freeze: {path}")
    if include_reference:
        for path in (M0A_SUPPORTED, M0A_MATCHED_EVAL):
            if not path.is_file():
                raise FileNotFoundError(path)
    return freeze


def run_pre_reference() -> None:
    verify_freeze(False)
    frames, process_note = load_frames()
    _, optical_by_frame = load_optical()
    nodes = pd.read_csv(M0A_NODES)
    nodes = nodes[nodes["run_id"].eq(RUN_ID)].copy()
    matrix = pd.read_csv(M0A_MATRIX)
    matrix = matrix[matrix["condition"].eq("P0")].copy()
    queries, relations = build_queries_and_relations(frames, optical_by_frame, nodes)
    hypotheses = build_hypotheses(matrix, relations, queries)
    raw_controls, static_controls = choose_controls(hypotheses)

    query_path = OUTPUT_DIR / PRE_FILES["query_table"]
    relation_path = OUTPUT_DIR / PRE_FILES["relations"]
    hypothesis_path = OUTPUT_DIR / PRE_FILES["hypotheses"]
    raw_control_path = OUTPUT_DIR / PRE_FILES["raw_controls"]
    static_control_path = OUTPUT_DIR / PRE_FILES["static_controls"]
    queries.to_csv(query_path, index=False, encoding="utf-8-sig")
    relations.to_csv(relation_path, index=False, encoding="utf-8-sig")
    hypotheses.to_csv(hypothesis_path, index=False, encoding="utf-8-sig")
    raw_controls.to_csv(raw_control_path, index=False, encoding="utf-8-sig")
    static_controls.to_csv(static_control_path, index=False, encoding="utf-8-sig")

    nominal_existing = pd.read_csv(TOPOLOGY_EDGES)
    nominal_existing = nominal_existing[
        nominal_existing["run_id"].eq(RUN_ID)
        & nominal_existing["temporal_policy"].eq("SAME_FRAME")
        & nominal_existing["guard_variant"].eq("CURRENT_G6")
        & nominal_existing["percentile_tag"].eq("Q095")
        & nominal_existing["frame_index"].between(FRAME_START, FRAME_END)
    ]
    expected_keys = set(zip(nominal_existing["frame_uid"], nominal_existing["track_id"], nominal_existing["region_id"]))
    nominal = relations[relations["timing_condition"].eq("NOMINAL")]
    observed_keys = set(zip(nominal["frame_uid"], nominal["track_id"], nominal["region_id"]))
    summary = {
        "schema": "PERSON_M0B1_PRE_REFERENCE_SUMMARY_V1",
        "created_at": now_iso(),
        "reference_loaded": False,
        "process_note": process_note,
        "query_rows": int(len(queries)),
        "static_relation_rows": int(len(relations)),
        "hypothesis_rows": int(len(hypotheses)),
        "hard_feasible_rows": int(hypotheses["static_feasible"].astype(bool).sum()),
        "dynamic_available_rows": int(hypotheses["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE").sum()),
        "same_optical_sample_rows": int(hypotheses["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_SAME_OPTICAL_SAMPLE").sum()),
        "fragment_break_rows": int(hypotheses["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK").sum()),
        "observation_unavailable_rows": int(hypotheses["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_OBSERVATION").sum()),
        "static_infeasible_rows": int((~hypotheses["static_feasible"].astype(bool)).sum()),
        "optical_determinate_rows": int(hypotheses["optical_direction_state"].isin(["OPTICAL_POSITIVE", "OPTICAL_NEGATIVE"]).sum()),
        "nominal_pixel_topology_key_parity": bool(expected_keys == observed_keys),
        "nominal_expected_key_count": len(expected_keys),
        "nominal_observed_key_count": len(observed_keys),
        "raw_fragment_control_rows": int(len(raw_controls)),
        "static_shell_matched_control_rows": int(len(static_controls)),
        "pareto_pruning_performed": False,
        "hypotheses_deleted": False,
        "prohibited_pre_reference_fields_used": False,
    }
    summary_path = OUTPUT_DIR / PRE_FILES["summary"]
    write_json(summary_path, summary)
    manifest_paths = [
        query_path,
        relation_path,
        hypothesis_path,
        raw_control_path,
        static_control_path,
        summary_path,
    ]
    manifest = manifest_payload(manifest_paths, "PERSON_M0B1_PRE_REFERENCE_MANIFEST_V1", False)
    manifest["protocol_sha256"] = sha256_file(PROTOCOL_PATH)
    manifest["reference_files_opened"] = False
    write_json(OUTPUT_DIR / PRE_FILES["manifest"], manifest)
    ledger = read_json(LEDGER_PATH)
    ledger["events"].extend(
        [
            {"stage": "TIMING_QUERIES_MATERIALIZED_PRE_REFERENCE", "completed_at": now_iso()},
            {"stage": "PIXEL_LEVEL_STATIC_RELATIONS_MATERIALIZED_PRE_REFERENCE", "completed_at": now_iso()},
            {"stage": "ALL_DIRECTION_HYPOTHESIS_RECORDS_MATERIALIZED_PRE_REFERENCE", "completed_at": now_iso()},
            {"stage": "DIRECTION_FREE_CONTROLS_FROZEN_PRE_REFERENCE", "completed_at": now_iso()},
            {"stage": "PRE_REFERENCE_MANIFEST_FROZEN_REFERENCE_STILL_NOT_LOADED", "completed_at": now_iso()},
        ]
    )
    write_json(LEDGER_PATH, ledger)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def check_pre_manifest() -> None:
    manifest = read_json(OUTPUT_DIR / PRE_FILES["manifest"])
    if manifest["reference_loaded"] or manifest["reference_files_opened"]:
        raise RuntimeError("pre-reference manifest boundary violated")
    for item in manifest["files"]:
        if sha256_file(WORKSPACE / item["path"]) != item["sha256"]:
            raise RuntimeError(f"pre-reference output changed: {item['path']}")


def state_summary(frame: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    rows = []
    for key, group in frame.groupby(group_columns, dropna=False, sort=False):
        keys = key if isinstance(key, tuple) else (key,)
        payload = dict(zip(group_columns, keys))
        feasible = group["static_feasible"].astype(bool)
        rows.append(
            {
                **payload,
                "N_total_hypothesis_records": int(len(group)),
                "N_hard_feasible": int(feasible.sum()),
                "N_dynamic_available": int(group["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE").sum()),
                "N_same_optical_sample": int(group["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_SAME_OPTICAL_SAMPLE").sum()),
                "N_fragment_break": int(group["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK").sum()),
                "N_observation_unavailable": int(group["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_OBSERVATION").sum()),
                "N_static_shell_infeasible": int((~feasible).sum()),
                "N_direction_indeterminate": int(group["cross_modal_direction_state"].eq("DIRECTION_INDETERMINATE").sum()),
                "N_direction_concordant": int(group["cross_modal_direction_state"].eq("DIRECTION_CONCORDANT").sum()),
                "N_direction_contradictory": int(group["cross_modal_direction_state"].eq("DIRECTION_CONTRADICTORY").sum()),
                "N_direction_unavailable": int(group["cross_modal_direction_state"].eq("DIRECTION_UNAVAILABLE").sum()),
                "dynamic_availability_rate_of_total": float(group["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE").mean()),
                "determinate_direction_rate_of_dynamic_available": (
                    float(group["cross_modal_direction_state"].isin(["DIRECTION_CONCORDANT", "DIRECTION_CONTRADICTORY"]).sum())
                    / max(int(group["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE").sum()), 1)
                ),
            }
        )
    return pd.DataFrame(rows)


def add_evaluation_groups(hypotheses: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    supported = pd.read_csv(M0A_SUPPORTED)
    supported = supported[supported["condition"].eq("P0")].drop_duplicates("base_edge_id")
    matched = pd.read_csv(M0A_MATCHED_EVAL)
    matched = matched[
        matched["condition"].eq("P0")
        & matched["alternative_reference_state"].eq("REFERENCE_UNSUPPORTED")
    ].copy()
    supported_ids = set(supported["base_edge_id"].astype(str))
    matched_ids = set(matched["alternative_base_edge_id"].astype(str))
    output = hypotheses.copy()
    output["evaluation_group"] = "PRE_REFERENCE_OTHER"
    output.loc[output["base_edge_id"].isin(matched_ids), "evaluation_group"] = "FROZEN_MATCHED_SAR_NULL"
    output.loc[output["base_edge_id"].isin(supported_ids), "evaluation_group"] = "REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED"
    output["raw_fragment_manual_target_evaluation_available"] = False
    output["post_reference_raw_fragment_interface_status"] = "M0B1_POST_REFERENCE_RAW_FRAGMENT_EVALUATION_INTERFACE_NOT_ESTABLISHED"
    output["reference_relabels_raw_branch"] = False
    return output, supported, matched


def choose_case_rows(
    evaluated: pd.DataFrame,
    static_controls: pd.DataFrame,
    pre_cases: pd.DataFrame,
) -> pd.DataFrame:
    slots: list[tuple[str, pd.Series | None, str, str]] = []
    stable = evaluated[evaluated["static_feasible"].astype(bool)].copy()

    def select(name: str, mask: pd.Series, fallback: pd.Series, rule: str) -> None:
        subset = stable[mask].sort_values(["pair_index", "hypothesis_id"])
        status = "REQUESTED_CATEGORY_AVAILABLE"
        if subset.empty:
            subset = stable[fallback].sort_values(
                ["optical_delta_interval_width_deg", "pair_index", "hypothesis_id"],
                na_position="last",
            )
            status = "REQUESTED_CATEGORY_UNAVAILABLE_DETERMINISTIC_FALLBACK"
        slots.append((name, subset.iloc[0] if len(subset) else None, rule, status))

    supported = stable["evaluation_group"].eq("REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED")
    matched = stable["evaluation_group"].eq("FROZEN_MATCHED_SAR_NULL")
    select("01_supported_concordant", supported & stable["cross_modal_direction_state"].eq("DIRECTION_CONCORDANT"), supported & stable["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE"), "SUPPORTED_CONCORDANT_THEN_NARROWEST_AVAILABLE")
    select("02_supported_contradictory", supported & stable["cross_modal_direction_state"].eq("DIRECTION_CONTRADICTORY"), supported & stable["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE"), "SUPPORTED_CONTRADICTORY_THEN_NARROWEST_AVAILABLE")
    select("03_supported_indeterminate", supported & stable["cross_modal_direction_state"].eq("DIRECTION_INDETERMINATE"), supported, "SUPPORTED_INDETERMINATE")
    select("04_same_optical_sample", stable["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_SAME_OPTICAL_SAMPLE"), pd.Series(True, index=stable.index), "SAME_SAMPLE_LOWEST_PAIR")
    select("05_raw_fragment_break", stable["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK"), pd.Series(True, index=stable.index), "FRAGMENT_BREAK_LOWEST_PAIR")
    select("06_matched_wrong_concordant", matched & stable["cross_modal_direction_state"].eq("DIRECTION_CONCORDANT"), matched, "MATCHED_CONCORDANT_THEN_FIRST_MATCHED")
    select("07_matched_wrong_contradictory", matched & stable["cross_modal_direction_state"].eq("DIRECTION_CONTRADICTORY"), matched, "MATCHED_CONTRADICTORY_THEN_FIRST_MATCHED")

    split_ids = set(pre_cases.loc[pre_cases["case_type"].astype(str).str.contains("SPLIT"), "base_edge_id"].astype(str))
    merge_ids = set(pre_cases.loc[pre_cases["case_type"].astype(str).str.contains("MERGE"), "base_edge_id"].astype(str))
    select("08_split_like_sar", stable["base_edge_id"].isin(split_ids), stable["source_topology_state"].astype(str).str.contains("MULTIPLE") | stable["destination_topology_state"].astype(str).str.contains("MULTIPLE"), "FROZEN_SPLIT_CASE_THEN_MULTI_TOPOLOGY")
    select("09_merge_or_shared_sar", stable["base_edge_id"].isin(merge_ids) | supported, supported, "FROZEN_MERGE_OR_SHARED_SUPPORTED")

    key_cols = ["base_edge_id", "source_track_id", "destination_track_id"]
    changed_ids: set[str] = set()
    for _, group in stable.groupby(key_cols, sort=False):
        if group["cross_modal_direction_state"].nunique() > 1 or group["angular_availability_state"].nunique() > 1:
            changed_ids.update(group["hypothesis_id"].astype(str))
    select("10_timing_state_change", stable["hypothesis_id"].isin(changed_ids), pd.Series(True, index=stable.index), "TIMING_STATE_CHANGE_THEN_FIRST")

    control_map = dict(zip(static_controls.get("primary_hypothesis_id", []), static_controls.get("control_hypothesis_id", [])))
    static_primary = stable["hypothesis_id"].isin(control_map)
    select(
        "11_static_shell_tautology",
        supported & static_primary,
        supported & stable["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE"),
        "SUPPORTED_STATIC_MATCHED_PRIMARY",
    )
    determinate = stable["cross_modal_direction_state"].isin(["DIRECTION_CONCORDANT", "DIRECTION_CONTRADICTORY"])
    select("12_best_incremental_direction", determinate, stable["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE"), "DETERMINATE_THEN_NARROWEST_AVAILABLE")

    rows = []
    for name, row, rule, status in slots:
        if row is None:
            rows.append({"case_name": name, "selection_rule": rule, "selection_status": "NO_REAL_CASE_AVAILABLE"})
        else:
            payload = row.to_dict()
            payload.update({"case_name": name, "selection_rule": rule, "selection_status": status})
            rows.append(payload)
    return pd.DataFrame(rows)


def image_path(frame_index: int, timestamp_ms: int) -> Path:
    return IMAGE_DIR / f"frame_{frame_index:06d}_t{timestamp_ms:06d}ms.jpg"


def draw_interval_mask(ax: Any, theta: np.ndarray, low: float, high: float, color: str, alpha: float) -> None:
    mask = (theta >= low) & (theta <= high)
    overlay = np.zeros((*theta.shape, 4), dtype=float)
    rgba = matplotlib.colors.to_rgba(color, alpha)
    overlay[mask] = rgba
    ax.imshow(overlay)


def render_case(
    case: pd.Series,
    frames: dict[int, dict[str, Any]],
    supported_map: dict[str, pd.Series],
    matched_primary: dict[str, str],
    include_reference: bool,
    output_path: Path,
) -> None:
    source_frame = frames[int(case.from_frame)]
    destination_frame = frames[int(case["to_frame"])]
    source_img = cv2.cvtColor(cv2.imread(str(image_path(int(case.from_frame), source_frame["sar_timestamp_ms"]))), cv2.COLOR_BGR2RGB)
    destination_img = cv2.cvtColor(
        cv2.imread(str(image_path(int(case["to_frame"]), destination_frame["sar_timestamp_ms"]))),
        cv2.COLOR_BGR2RGB,
    )
    with np.load(REGION_MASK_DIR / f"{case.from_frame_uid}.npz") as archive:
        source_labels = archive["Q095"]
    with np.load(REGION_MASK_DIR / f"{case.to_frame_uid}.npz") as archive:
        destination_labels = archive["Q095"]
    source_theta = polar_theta(source_frame, source_labels.shape)
    destination_theta = polar_theta(destination_frame, destination_labels.shape)
    source_label = int(str(case.source_region_id).split("R")[-1])
    destination_label = int(str(case.destination_region_id).split("R")[-1])

    fig, axes = plt.subplots(1, 3, figsize=(18, 6), dpi=130, gridspec_kw={"width_ratios": [1, 1, 0.9]})
    for ax, image, labels, label, theta, prefix in (
        (axes[0], source_img, source_labels, source_label, source_theta, "source"),
        (axes[1], destination_img, destination_labels, destination_label, destination_theta, "destination"),
    ):
        ax.imshow(image)
        ax.contour(labels == label, levels=[0.5], colors=["lime"], linewidths=2)
        low = case.get(f"{prefix}_raw_theta_low_deg", math.nan)
        high = case.get(f"{prefix}_raw_theta_high_deg", math.nan)
        if np.isfinite(float(low)) and np.isfinite(float(high)):
            draw_interval_mask(ax, theta, float(low) - OPTICAL_GUARD_DEG, float(high) + OPTICAL_GUARD_DEG, "cyan", 0.15)
            draw_interval_mask(ax, theta, float(low), float(high), "yellow", 0.20)
        ax.set_title(f"{prefix.title()} {int(case[f'{prefix}_optical_frame_index']) if np.isfinite(float(case.get(f'{prefix}_optical_frame_index', math.nan))) else 'NA'} optical / SAR {int(case['from_frame'] if prefix=='source' else case['to_frame'])}")
        ax.axis("off")

    if include_reference:
        primary_id = str(case.base_edge_id)
        if primary_id not in supported_map and primary_id in matched_primary:
            primary_id = matched_primary[primary_id]
        supported = supported_map.get(primary_id)
        if supported is not None:
            for ax, field in ((axes[0], "source_manual_centers_json"), (axes[1], "destination_manual_centers_json")):
                for point in json.loads(supported[field]):
                    ax.plot(float(point["x_px"]), float(point["y_px"]), marker="*", color="magenta", markersize=12)

    text = [
        f"Case: {case.case_name}",
        f"Selection: {case.selection_status}",
        f"Timing: {case.timing_condition}",
        f"Group: {case.evaluation_group}",
        f"Raw branch: {case.source_track_id} -> {case.destination_track_id}",
        f"Availability: {case.angular_availability_state}",
        f"Optical ΔI: [{case.get('optical_delta_interval_low_deg', math.nan):.4f}, {case.get('optical_delta_interval_high_deg', math.nan):.4f}] deg",
        f"Optical direction: {case.optical_direction_state}",
        f"SAR ΔI: [{case.sar_delta_interval_low_deg:.4f}, {case.sar_delta_interval_high_deg:.4f}] deg",
        f"SAR direction: {case.sar_direction_state}",
        f"Cross state: {case.cross_modal_direction_state}",
        f"P0 retention: {case.p0_q95_retention:.4f}",
        "Cyan = guarded static shell; yellow = guard-free optical interval.",
        "No path, assignment, pruning, or localization is shown.",
    ]
    if include_reference:
        text.append("Magenta stars are post-reference overlays only.")
    axes[2].axis("off")
    axes[2].text(0.0, 0.98, "\n".join(text), va="top", family="monospace", fontsize=10)
    fig.suptitle("M0B1 interval angular-direction diagnostic", fontsize=16, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def markdown_table(frame: pd.DataFrame, max_rows: int = 30) -> str:
    view = frame.head(max_rows).copy()
    if view.empty:
        return "(no rows)"
    columns = list(view.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in view.itertuples(index=False, name=None):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append("" if not np.isfinite(value) else f"{value:.4f}")
            else:
                values.append(str(value).replace("|", "/"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def run_post_reference() -> None:
    verify_freeze(True)
    check_pre_manifest()
    hypotheses = pd.read_csv(OUTPUT_DIR / PRE_FILES["hypotheses"])
    static_controls = pd.read_csv(OUTPUT_DIR / PRE_FILES["static_controls"])
    evaluated, supported, matched = add_evaluation_groups(hypotheses)
    evaluated_path = OUTPUT_DIR / "post_reference_hypothesis_evaluation.csv"
    evaluated.to_csv(evaluated_path, index=False, encoding="utf-8-sig")

    groups = evaluated[evaluated["evaluation_group"].ne("PRE_REFERENCE_OTHER")].copy()
    direction_summary = state_summary(groups, ["timing_condition", "evaluation_group"])
    pair_summary = state_summary(groups, ["timing_condition", "evaluation_group", "pair_index", "from_frame", "to_frame"])
    fragment_frame = groups.copy()
    fragment_frame["raw_fragment_cluster"] = np.where(
        fragment_frame["source_track_id"].eq(fragment_frame["destination_track_id"]),
        fragment_frame["source_track_id"],
        fragment_frame["source_track_id"].astype(str) + "__BREAK_TO__" + fragment_frame["destination_track_id"].astype(str),
    )
    fragment_summary = state_summary(fragment_frame, ["timing_condition", "evaluation_group", "raw_fragment_cluster"])
    direction_summary.to_csv(OUTPUT_DIR / "direction_state_summary.csv", index=False, encoding="utf-8-sig")
    pair_summary.to_csv(OUTPUT_DIR / "per_frame_pair_cluster.csv", index=False, encoding="utf-8-sig")
    fragment_summary.to_csv(OUTPUT_DIR / "per_raw_fragment_cluster.csv", index=False, encoding="utf-8-sig")

    timing_summary = state_summary(evaluated, ["timing_condition"])
    timing_summary.to_csv(OUTPUT_DIR / "timing_sensitivity.csv", index=False, encoding="utf-8-sig")

    available = groups[groups["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE")].copy()
    available["sar_only_retention_quartile"] = pd.qcut(
        available["p0_q95_retention"].rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"]
    ) if len(available) >= 4 else "UNAVAILABLE"
    cross_tab = (
        available.groupby(
            ["timing_condition", "evaluation_group", "sar_only_retention_quartile", "cross_modal_direction_state"],
            observed=True,
        ).size().reset_index(name="hypothesis_count")
    )
    cross_tab.to_csv(OUTPUT_DIR / "sar_only_angular_cross_tab.csv", index=False, encoding="utf-8-sig")

    lookup = evaluated.set_index("hypothesis_id", drop=False)
    tautology_rows = []
    for row in static_controls.itertuples(index=False):
        if row.primary_hypothesis_id not in lookup.index or row.control_hypothesis_id not in lookup.index:
            continue
        primary = lookup.loc[row.primary_hypothesis_id]
        if primary["evaluation_group"] != "REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED":
            continue
        control = lookup.loc[row.control_hypothesis_id]
        tautology_rows.append(
            {
                "primary_hypothesis_id": row.primary_hypothesis_id,
                "control_hypothesis_id": row.control_hypothesis_id,
                "timing_condition": primary["timing_condition"],
                "primary_direction_state": primary["cross_modal_direction_state"],
                "control_direction_state": control["cross_modal_direction_state"],
                "same_direction_state": primary["cross_modal_direction_state"] == control["cross_modal_direction_state"],
                "static_distance": row.static_distance,
                "match_tier": row.match_tier,
                "direction_used_for_selection": False,
                "reference_used_for_selection": False,
            }
        )
    tautology = pd.DataFrame(
        tautology_rows,
        columns=[
            "primary_hypothesis_id",
            "control_hypothesis_id",
            "timing_condition",
            "primary_direction_state",
            "control_direction_state",
            "same_direction_state",
            "static_distance",
            "match_tier",
            "direction_used_for_selection",
            "reference_used_for_selection",
        ],
    )
    tautology.to_csv(OUTPUT_DIR / "static_shell_tautology_control.csv", index=False, encoding="utf-8-sig")

    pre_cases = pd.read_csv(M0A_PRE_CASES)
    cases = choose_case_rows(evaluated, static_controls, pre_cases)
    cases.to_csv(OUTPUT_DIR / "real_case_registry.csv", index=False, encoding="utf-8-sig")
    frames, _ = load_frames()
    supported_map = {str(row.base_edge_id): pd.Series(row._asdict()) for row in supported.itertuples(index=False)}
    matched_primary = dict(zip(matched["alternative_base_edge_id"].astype(str), matched["primary_base_edge_id"].astype(str)))
    pre_dir = OUTPUT_DIR / "figures" / "pre_reference_no_manual_overlay"
    post_dir = OUTPUT_DIR / "figures" / "post_reference_manual_overlay"
    pre_dir.mkdir(parents=True, exist_ok=True)
    post_dir.mkdir(parents=True, exist_ok=True)
    for case in cases.itertuples(index=False):
        if not hasattr(case, "hypothesis_id") or pd.isna(case.hypothesis_id):
            continue
        series = pd.Series(case._asdict())
        render_case(series, frames, supported_map, matched_primary, False, pre_dir / f"{case.case_name}.png")
        render_case(series, frames, supported_map, matched_primary, True, post_dir / f"{case.case_name}.png")

    nominal_supported = groups[
        groups["timing_condition"].eq("NOMINAL")
        & groups["evaluation_group"].eq("REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED")
    ]
    nominal_available = nominal_supported[
        nominal_supported["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE")
    ]
    determinate = nominal_available[
        nominal_available["cross_modal_direction_state"].isin(["DIRECTION_CONCORDANT", "DIRECTION_CONTRADICTORY"])
    ]
    determinate_pair_count = int(determinate["pair_index"].nunique())
    determinate_fragment_count = int(determinate["source_track_id"].nunique())
    unavailable_sampling = nominal_supported["angular_availability_state"].isin(
        ["ANGULAR_DYNAMIC_UNAVAILABLE_SAME_OPTICAL_SAMPLE", "ANGULAR_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK"]
    )
    sampling_block_fraction = float(unavailable_sampling.mean()) if len(nominal_supported) else math.nan

    if len(determinate) < 4 or determinate_pair_count < 2 or determinate_fragment_count < 2:
        state = "M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT"
    else:
        state = "M0B1_ANGULAR_DIRECTION_DISCRIMINATION_WEAK"
    secondary = []
    if np.isfinite(sampling_block_fraction) and sampling_block_fraction > 0.5:
        secondary.append("M0B1_RUNTIME_OPTICAL_TEMPORAL_SAMPLING_BLOCKED")
    secondary.append("M0B1_POST_REFERENCE_RAW_FRAGMENT_EVALUATION_INTERFACE_NOT_ESTABLISHED")

    summary = {
        "schema": "PERSON_M0B1_POST_REFERENCE_SUMMARY_V1",
        "created_at": now_iso(),
        "state": state,
        "secondary_states": secondary,
        "frozen_m0a_state": "M0A_REGION_SUPPORT_TRANSPORT_WITH_P0_GAIN",
        "frozen_m0ar_state": "M0A_R_TRANSPORT_VALID_BUT_PERSON_SPECIFICITY_NOT_ESTABLISHED",
        "reference_supported_base_edge_count": int(len(supported)),
        "reference_supported_frame_pair_cluster_count": int(supported["pair_index"].nunique()),
        "nominal_supported_hypothesis_records": int(len(nominal_supported)),
        "nominal_supported_dynamic_available": int(len(nominal_available)),
        "nominal_supported_determinate_direction": int(len(determinate)),
        "nominal_supported_determinate_frame_pair_clusters": determinate_pair_count,
        "nominal_supported_determinate_raw_fragment_clusters": determinate_fragment_count,
        "nominal_supported_sampling_block_fraction": sampling_block_fraction,
        "incremental_angular_signal_observed": False,
        "static_geometry_reexpression_assessment": "NOT_IDENTIFIABLE_BECAUSE_INTERVAL_DIRECTION_IS_NOT_DETERMINATE",
        "timing_calibrated": False,
        "timing_shift_selected": False,
        "pareto_pruning_performed": False,
        "hypothesis_rejection_by_direction": False,
        "raw_fragment_target_evaluator_status": "NOT_ESTABLISHED",
        "recommend_m0b2": False,
        "recommended_next_action": "DIAGNOSE_INTERVAL_WIDTH_OPTICAL_SAMPLING_RAW_FRAGMENT_CONTINUITY_SYNC_AND_MAPPING_SLOPE_BEFORE_MAGNITUDE_OR_ADMISSIBILITY",
        "prohibited_claims": {
            "optical_sar_motion_consistency_established": False,
            "person_specific_region_continuation": False,
            "runtime_identity": False,
            "ambiguity_reduction": False,
            "dynamic_pruning": False,
            "timing_calibration": False,
            "final_sar_localization": False,
        },
    }
    write_json(OUTPUT_DIR / "post_reference_summary.json", summary)

    report = "\n".join(
        [
            "# M0B1 R02 raw-fragment angular-direction diagnostic",
            "",
            f"- State: `{state}`",
            "- Study role: interval angular-direction observability and discrimination diagnostic",
            "- Pareto role: descriptive only; no pruning was performed",
            "- M0B2, magnitude, monotonicity, tracker, assignment, timing fit, and localization: not executed",
            "",
            "## Conclusion",
            "",
            "The interval representation does not provide enough determinate optical angular direction to establish incremental cross-modal direction information. Same-sample and raw-fragment-break states remain unavailable rather than zero or contradictory. Because the post-reference interface cannot identify a correct raw fragment for a manual target without introducing a new assignment layer, positive labels remain SAR-edge-supported with unresolved raw branches.",
            "",
            "## Timing implementation",
            "",
            "`NOMINAL` uses the exact decoded optical frame index stored for each SAR frame. SAR shifts query the fixed neighboring SAR frame's nominal optical index; boundary shifts are unavailable. Optical shifts add exactly one decoded optical frame to each endpoint query. No best shift is selected or written back.",
            "",
            "## Direction-state summary",
            "",
            markdown_table(direction_summary),
            "",
            "## Timing sensitivity",
            "",
            markdown_table(timing_summary),
            "",
            "## Static-shell tautology control",
            "",
            f"Matched pairs: `{len(tautology)}`. Direction was not used to select controls. With insufficient determinate interval directions, static-containment re-expression cannot be separated from new dynamic information in this slice.",
            "",
            "## Cluster structure",
            "",
            f"Supported SAR edges: `{len(supported)}` from `{supported['pair_index'].nunique()}` frame-pair clusters. Row-level hypothesis counts are not independent observations. Per-pair and per-fragment tables are materialized separately.",
            "",
            "## Real cases",
            "",
            "Twelve deterministic slots are stored with paired no-manual-overlay and post-reference-overlay figures. If a requested direction category is absent, the registry explicitly records the deterministic fallback instead of fabricating a concordant or contradictory case.",
            "",
            "## Non-claims and stop",
            "",
            "This diagnostic does not establish synchronization, physical PERSON angular velocity, PERSON-specific SAR continuation, raw-fragment identity, ambiguity reduction, pruning validity, a unique path, or final SAR localization. Stop after M0B1; do not enter magnitude or M0B2 automatically.",
        ]
    ) + "\n"
    report_path = OUTPUT_DIR / "M0B1_R02_RAW_FRAGMENT_ANGULAR_DIRECTION_REPORT.md"
    report_path.write_text(report, encoding="utf-8")

    output_paths = [
        evaluated_path,
        OUTPUT_DIR / "direction_state_summary.csv",
        OUTPUT_DIR / "per_frame_pair_cluster.csv",
        OUTPUT_DIR / "per_raw_fragment_cluster.csv",
        OUTPUT_DIR / "timing_sensitivity.csv",
        OUTPUT_DIR / "sar_only_angular_cross_tab.csv",
        OUTPUT_DIR / "static_shell_tautology_control.csv",
        OUTPUT_DIR / "real_case_registry.csv",
        OUTPUT_DIR / "post_reference_summary.json",
        report_path,
        *sorted(pre_dir.glob("*.png")),
        *sorted(post_dir.glob("*.png")),
    ]
    manifest = manifest_payload(output_paths, "PERSON_M0B1_FINAL_OUTPUT_MANIFEST_V1", True)
    manifest.update(
        {
            "protocol_sha256": sha256_file(PROTOCOL_PATH),
            "pre_reference_manifest_sha256": sha256_file(OUTPUT_DIR / PRE_FILES["manifest"]),
            "m0b2_executed": False,
            "hypotheses_pruned": False,
        }
    )
    write_json(OUTPUT_DIR / "final_output_manifest.json", manifest)
    ledger = read_json(LEDGER_PATH)
    ledger["events"].extend(
        [
            {"stage": "PRE_REFERENCE_HASHES_VERIFIED", "completed_at": now_iso()},
            {"stage": "MANUAL_REFERENCE_REVEALED_AFTER_FREEZE", "completed_at": now_iso()},
            {"stage": "POST_REFERENCE_SAR_EDGE_EVALUATION_COMPLETE_RAW_BRANCH_UNRESOLVED", "completed_at": now_iso()},
            {"stage": "TWELVE_DETERMINISTIC_CASE_SLOTS_RENDERED_PAIRED", "completed_at": now_iso()},
            {"stage": "M0B1_COMPLETE_STOP_NO_M0B2", "completed_at": now_iso()},
        ]
    )
    write_json(LEDGER_PATH, ledger)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("freeze", "pre-reference", "post-reference"), required=True)
    args = parser.parse_args()
    if args.phase == "freeze":
        run_freeze()
    elif args.phase == "pre-reference":
        run_pre_reference()
    else:
        run_post_reference()


if __name__ == "__main__":
    main()
