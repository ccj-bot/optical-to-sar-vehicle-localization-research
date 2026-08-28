#!/usr/bin/env python3
"""M0A R02 lag1 q95 region-support transport pilot.

Phases are intentionally separated:
  pre-reference -> independent validation -> freeze-pre-reference -> post-reference.
The pre-reference phase never opens a manual-reference file.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OUTPUT_DIR = STUDY_OUTPUT / "m0a_r02_lag1_q95_region_support_transport_pilot"
PROTOCOL_PATH = OUTPUT_DIR / "M0A_R02_LAG1_Q95_REGION_SUPPORT_TRANSPORT_PROTOCOL_FROZEN_BEFORE_RUN.md"
FREEZE_PATH = OUTPUT_DIR / "protocol_freeze.json"

P0_SCRIPT = TASK_DIR / "run_p0_common_apparent_motion.py"
CANDIDATE_SCRIPT = TASK_DIR / "run_p1e_candidate_recall_audit.py"
B0R_DIR = STUDY_OUTPUT / "p1e_sar_only_response_interface" / "b0r_minimal"
MODEL_PATH = B0R_DIR / "b0r_model_parameters_R02_R03.jsonl"
PAIR_METRICS_PATH = B0R_DIR / "b0r_pair_metrics_R02_R03.csv"
COMPARABILITY_PATH = B0R_DIR / "b0r_pair_comparability_R02_R03.csv"
REGION_ROOT = (
    STUDY_OUTPUT
    / "p1e_sar_only_response_interface"
    / "runtime_track_response_region_minimal_v1"
)
REGION_TABLE_PATH = REGION_ROOT / "response_region_table_pre_reference.csv"
REGION_MASK_DIR = REGION_ROOT / "response_region_masks"
REFERENCE_PATH = REGION_ROOT / "offline_reference_response_region_evaluation.csv"
REFERENCE_CENTER_PATH = (
    STUDY_OUTPUT
    / "p1e_sar_only_response_interface"
    / "candidate_recall_semantic_split_v1"
    / "single_frame_candidate_recall"
    / "manual_reference_candidate_interpretation_v2.csv"
)
TOPOLOGY_ROOT = (
    STUDY_OUTPUT
    / "p1e_sar_only_response_interface"
    / "shell_uncertainty_region_topology_v1"
)
SHELL_DECOMPOSITION_PATH = TOPOLOGY_ROOT / "optical_shell_uncertainty_decomposition_pre_reference.csv"
REGION_TOPOLOGY_PATH = TOPOLOGY_ROOT / "gt_blind_region_nodes_pre_reference.csv"
GEOMETRY_PATH = WORKSPACE / "output" / "pseudocolor_azimuth_calibration_20260803" / "geometry" / "fan_geometry_report.json"
IMAGE_DIR = WORKSPACE / "output" / "pseudocolor_labelstudio_prep_20260722" / "frames" / "sar_pseudocolor" / "R02ZF"

NODE_PATH = OUTPUT_DIR / "pre_reference_region_nodes.csv"
MATRIX_PATH = OUTPUT_DIR / "pre_reference_compatibility_matrix.csv"
MATCHED_PATH = OUTPUT_DIR / "pre_reference_matched_alternative_sets.csv"
PRE_CASE_PATH = OUTPUT_DIR / "pre_reference_case_registry.csv"
PRE_MANIFEST_PATH = OUTPUT_DIR / "pre_reference_manifest.json"
PRE_LEDGER_PATH = OUTPUT_DIR / "pre_reference_execution_ledger.json"
PRE_VALIDATION_PATH = OUTPUT_DIR / "pre_reference_validation.json"
PRE_HASH_PATH = OUTPUT_DIR / "pre_reference_output_hashes.json"
SYNTHETIC_PATH = OUTPUT_DIR / "warp_synthetic_tests.json"
PRE_FIGURE_DIR = OUTPUT_DIR / "figures" / "pre_reference"

POST_SUPPORTED_PATH = OUTPUT_DIR / "post_reference_supported_explanations.csv"
POST_MATCHED_PATH = OUTPUT_DIR / "post_reference_matched_alternative_evaluation.csv"
POST_CASE_PATH = OUTPUT_DIR / "post_reference_case_registry.csv"
POST_SUMMARY_PATH = OUTPUT_DIR / "post_reference_summary.json"
EXECUTION_LEDGER_PATH = OUTPUT_DIR / "execution_ledger.json"

RUN_ID = "R02ZF"
Q90 = "Q090"
Q95 = "Q095"
Q975 = "Q0975"
EXPECTED_FRAME_START = 472
EXPECTED_FRAME_END = 494
EXPECTED_PAIR_COUNT = 22
INNER_RANGE_M = 0.75
MATCHED_ALTERNATIVE_COUNT = 5
TIE_TOLERANCE = 1e-9

PROHIBITED_PRE_REFERENCE_COLUMNS = {
    "physical_target_id",
    "target_id",
    "reference_x_px",
    "reference_y_px",
    "reference_range_m",
    "reference_theta_deg",
    "optical_person_id",
    "source_parent_stitched_ids",
    "reference_supported",
    "reference_support_state",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_object(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def json_number(value: Any) -> float | int | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def require_bool_series(series: pd.Series, column: str) -> pd.Series:
    """Parse a CSV boolean column without treating the string 'False' as truthy."""
    if pd.api.types.is_bool_dtype(series.dtype):
        if series.isna().any():
            raise ValueError(f"null boolean values in {column}")
        return series.astype(bool)
    normalized = series.astype("string").str.strip().str.lower()
    mapping = {"true": True, "false": False, "1": True, "0": False}
    parsed = normalized.map(mapping)
    invalid = series[parsed.isna()]
    if len(invalid):
        raise ValueError(f"invalid boolean values in {column}: {invalid.unique().tolist()}")
    return parsed.astype(bool)


def require_bool_value(value: Any, field: str) -> bool:
    parsed = require_bool_series(pd.Series([value]), field)
    return bool(parsed.iloc[0])


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True, encoding="utf-8"
    ).strip()


def soft_affine_translation_warp(mask: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Warp binary/float support from source to destination as soft occupancy."""
    source = np.asarray(mask, dtype=np.float32)
    if source.ndim != 2:
        raise ValueError("mask must be 2D")
    height, width = source.shape
    matrix = np.array([[1.0, 0.0, float(dx)], [0.0, 1.0, float(dy)]], dtype=np.float32)
    warped = cv2.warpAffine(
        source,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0.0,
    )
    return np.clip(warped.astype(np.float32), 0.0, 1.0)


def build_valid_mask(
    image: np.ndarray,
    geometry: dict[str, float],
    theta_low_deg: float,
    theta_high_deg: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    height, width = image.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    cx = float(geometry["center_x_px"])
    cy = float(geometry["center_y_px"])
    radius = float(geometry["radius_px"])
    px_per_m = radius / float(geometry["outer_range_m"])
    radial_px = np.hypot(xx - cx, yy - cy)
    theta_deg = np.degrees(np.arctan2(xx - cx, cy - yy))
    nonwhite = np.any(image < 248, axis=2)
    valid = (
        (radial_px >= INNER_RANGE_M * px_per_m)
        & (radial_px <= radius)
        & (theta_deg >= float(theta_low_deg))
        & (theta_deg <= float(theta_high_deg))
        & nonwhite
    )
    valid = cv2.morphologyEx(
        valid.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)
    ).astype(bool)
    return valid, radial_px / px_per_m, theta_deg, px_per_m


def verify_protocol_freeze() -> dict[str, Any]:
    if not FREEZE_PATH.exists():
        raise RuntimeError(f"missing protocol freeze: {FREEZE_PATH}")
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN_BEFORE_RUN":
        raise RuntimeError("protocol freeze is not FROZEN_BEFORE_RUN")
    if sha256_file(PROTOCOL_PATH) != freeze["protocol_sha256"]:
        raise RuntimeError("protocol hash mismatch")
    if git_head() != freeze["starting_head"]:
        raise RuntimeError("HEAD changed after protocol freeze")
    for item in freeze["implementation_hashes"]:
        path = WORKSPACE / item["path"]
        if sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"implementation hash mismatch: {path}")
    for item in freeze["dependency_hashes"]:
        path = WORKSPACE / item["path"]
        if sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"dependency hash mismatch: {path}")
    return freeze


def find_image(frame_index: int) -> Path:
    matches = sorted(IMAGE_DIR.glob(f"frame_{frame_index:06d}_t*ms.jpg"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one image for frame {frame_index}, got {matches}")
    return matches[0]


def load_geometry() -> dict[str, float]:
    report = json.loads(GEOMETRY_PATH.read_text(encoding="utf-8"))
    mode = report["modes"]["1024x592"]
    return {
        "center_x_px": float(mode["center_x_px"]),
        "center_y_px": float(mode["center_y_px"]),
        "radius_px": float(mode["radius_px"]),
        "outer_range_m": float(report["outer_range_m"]),
    }


def load_frame_metadata() -> pd.DataFrame:
    columns = [
        "run_id",
        "frame_uid",
        "frame_index",
        "sar_timestamp_ms",
        "fan_theta_low_deg",
        "fan_theta_high_deg",
        "omega_single_pixel_count",
        "px_per_m",
    ]
    rows = pd.read_csv(SHELL_DECOMPOSITION_PATH, usecols=columns)
    rows = rows[rows["run_id"].eq(RUN_ID)].drop_duplicates("frame_uid").copy()
    rows["frame_index"] = pd.to_numeric(rows["frame_index"], errors="raise").astype(int)
    rows = rows[rows["frame_index"].between(EXPECTED_FRAME_START, EXPECTED_FRAME_END)]
    rows = rows.sort_values("frame_index").reset_index(drop=True)
    if rows["frame_index"].tolist() != list(range(EXPECTED_FRAME_START, EXPECTED_FRAME_END + 1)):
        raise RuntimeError("unexpected R02 frame set")
    return rows


def load_pair_records() -> list[dict[str, Any]]:
    comparability = pd.read_csv(COMPARABILITY_PATH)
    comparable = require_bool_series(comparability["comparable"], "comparable")
    comparability = comparability[
        comparability["run_id"].eq(RUN_ID)
        & pd.to_numeric(comparability["lag"], errors="raise").eq(1)
        & comparable
    ].copy()
    metrics = pd.read_csv(PAIR_METRICS_PATH)
    model_available = require_bool_series(metrics["model_available"], "model_available")
    selected_model = require_bool_series(
        metrics["is_selected_frozen_model"], "is_selected_frozen_model"
    )
    metrics = metrics[
        metrics["run_id"].eq(RUN_ID)
        & pd.to_numeric(metrics["lag"], errors="raise").eq(1)
        & metrics["model"].eq("M1")
        & model_available
        & selected_model
    ].copy()
    model_records: dict[tuple[str, str], dict[str, Any]] = {}
    for line in MODEL_PATH.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record["run_id"] == RUN_ID and int(record["lag"]) == 1 and record["model"] == "M1":
            model_records[(record["from_frame_uid"], record["to_frame_uid"])] = record
    joined = metrics.merge(
        comparability[
            ["from_frame_uid", "to_frame_uid", "pair_valid_fraction", "comparability_reason"]
        ],
        on=["from_frame_uid", "to_frame_uid"],
        how="inner",
        validate="one_to_one",
    ).sort_values("from_frame")
    pairs: list[dict[str, Any]] = []
    for pair_index, row in enumerate(joined.itertuples(index=False)):
        key = (str(row.from_frame_uid), str(row.to_frame_uid))
        model = model_records[key]
        translation = model["model_state"]["parameters"]["translation_xy"]
        pairs.append(
            {
                "pair_index": pair_index,
                "run_id": RUN_ID,
                "from_frame": int(row.from_frame),
                "to_frame": int(row.to_frame),
                "from_frame_uid": key[0],
                "to_frame_uid": key[1],
                "dx_px": float(translation[0]),
                "dy_px": float(translation[1]),
                "pair_valid_fraction": float(row.pair_valid_fraction),
                "comparability_reason": str(row.comparability_reason),
                "p0_holdout_median_px": float(row.holdout_residual_median_px),
                "p0_holdout_p90_px": float(row.holdout_residual_p90_px),
                "display_js_divergence": float(row.display_js_divergence),
                "display_stratum": str(row.display_stratum),
            }
        )
    if len(pairs) != EXPECTED_PAIR_COUNT:
        raise RuntimeError(f"expected {EXPECTED_PAIR_COUNT} pairs, got {len(pairs)}")
    expected = list(range(EXPECTED_FRAME_START, EXPECTED_FRAME_END))
    if [pair["from_frame"] for pair in pairs] != expected:
        raise RuntimeError("pair set is not contiguous F472-F494")
    return pairs


def degree_bin(value: Any) -> int:
    number = int(float(value))
    return min(number, 3)


def load_region_metadata() -> pd.DataFrame:
    regions = pd.read_csv(REGION_TABLE_PATH)
    regions = regions[
        regions["run_id"].eq(RUN_ID)
        & regions["percentile_tag"].eq(Q95)
        & pd.to_numeric(regions["frame_index"], errors="raise").between(
            EXPECTED_FRAME_START, EXPECTED_FRAME_END
        )
    ].copy()
    topology = pd.read_csv(
        REGION_TOPOLOGY_PATH,
        usecols=[
            "run_id",
            "frame_uid",
            "temporal_policy",
            "guard_variant",
            "percentile_tag",
            "region_id",
            "region_degree_shell_count",
            "component_shell_count",
            "component_region_count",
            "component_edge_count",
            "topology_state",
        ],
    )
    topology = topology[
        topology["run_id"].eq(RUN_ID)
        & topology["temporal_policy"].eq("SAME_FRAME")
        & topology["guard_variant"].eq("CURRENT_G6")
        & topology["percentile_tag"].eq(Q95)
    ].copy()
    topology = topology.drop_duplicates(["frame_uid", "region_id"])
    regions = regions.merge(
        topology.drop(columns=["run_id", "temporal_policy", "guard_variant", "percentile_tag"]),
        on=["frame_uid", "region_id"],
        how="left",
        validate="one_to_one",
    )
    for column in (
        "region_degree_shell_count",
        "component_shell_count",
        "component_region_count",
        "component_edge_count",
    ):
        regions[column] = pd.to_numeric(regions[column], errors="coerce").fillna(0).astype(int)
    regions["region_degree_bin"] = regions["region_degree_shell_count"].map(degree_bin)
    regions["component_shell_count_bin"] = regions["component_shell_count"].map(degree_bin)
    return regions.sort_values(["frame_index", "region_label"]).reset_index(drop=True)


def mask_bundle(frame_uid: str) -> dict[str, np.ndarray]:
    with np.load(REGION_MASK_DIR / f"{frame_uid}.npz") as archive:
        return {tag: archive[tag].astype(np.int32) for tag in (Q90, Q95, Q975)}


def region_layer_masks(
    labels: dict[str, np.ndarray], q95_label: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[int], list[int]]:
    q95_mask = labels[Q95] == int(q95_label)
    q975_labels = sorted(int(value) for value in np.unique(labels[Q975][q95_mask]) if int(value) > 0)
    q975_core = q95_mask & (labels[Q975] > 0)
    q90_labels = sorted(int(value) for value in np.unique(labels[Q90][q95_mask]) if int(value) > 0)
    q90_envelope = np.isin(labels[Q90], q90_labels) if q90_labels else np.zeros_like(q95_mask)
    return q95_mask, q975_core, q90_envelope, q975_labels, q90_labels


def prepare_runtime_inputs() -> dict[str, Any]:
    geometry = load_geometry()
    frame_table = load_frame_metadata()
    region_table = load_region_metadata()
    pairs = load_pair_records()
    frames: dict[str, dict[str, Any]] = {}
    nodes: list[dict[str, Any]] = []
    for row in frame_table.itertuples(index=False):
        image_path = find_image(int(row.frame_index))
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(image_path)
        valid, range_grid, theta_grid, px_per_m = build_valid_mask(
            image, geometry, float(row.fan_theta_low_deg), float(row.fan_theta_high_deg)
        )
        if int(np.count_nonzero(valid)) != int(row.omega_single_pixel_count):
            raise RuntimeError(f"valid-mask parity failed for {row.frame_uid}")
        labels = mask_bundle(str(row.frame_uid))
        frames[str(row.frame_uid)] = {
            "frame_uid": str(row.frame_uid),
            "frame_index": int(row.frame_index),
            "image_path": image_path,
            "valid_mask": valid,
            "range_grid": range_grid,
            "theta_grid": theta_grid,
            "px_per_m": float(px_per_m),
            "labels": labels,
        }
        frame_regions = region_table[region_table["frame_uid"].eq(str(row.frame_uid))]
        for region in frame_regions.itertuples(index=False):
            q95_mask, q975_core, q90_envelope, q975_labels, q90_labels = region_layer_masks(
                labels, int(region.region_label)
            )
            node = {
                "run_id": RUN_ID,
                "frame_uid": str(region.frame_uid),
                "frame_index": int(region.frame_index),
                "region_id": str(region.region_id),
                "region_label": int(region.region_label),
                "q95_pixel_count": int(np.count_nonzero(q95_mask)),
                "q975_core_pixel_count": int(np.count_nonzero(q975_core)),
                "q90_envelope_pixel_count": int(np.count_nonzero(q90_envelope)),
                "q975_labels_json": json.dumps(q975_labels),
                "q90_labels_json": json.dumps(q90_labels),
                "area_m2": float(region.area_m2),
                "theta_min_deg": float(region.theta_min_deg),
                "theta_max_deg": float(region.theta_max_deg),
                "theta_mid_deg": 0.5 * (float(region.theta_min_deg) + float(region.theta_max_deg)),
                "range_min_m": float(region.range_min_m),
                "range_max_m": float(region.range_max_m),
                "range_mid_m": 0.5 * (float(region.range_min_m) + float(region.range_max_m)),
                "major_extent_m": float(region.major_extent_m),
                "minor_extent_m": float(region.minor_extent_m),
                "elongation": float(region.elongation),
                "structure_state": str(region.structure_state),
                "touches_observable_boundary": require_bool_value(
                    region.touches_observable_boundary, "touches_observable_boundary"
                ),
                "has_truncated_support": require_bool_value(
                    region.has_truncated_support, "has_truncated_support"
                ),
                "region_degree_shell_count": int(region.region_degree_shell_count),
                "region_degree_bin": int(region.region_degree_bin),
                "component_shell_count": int(region.component_shell_count),
                "component_shell_count_bin": int(region.component_shell_count_bin),
                "component_region_count": int(region.component_region_count),
                "component_edge_count": int(region.component_edge_count),
                "static_topology_state": str(region.topology_state),
                "single_frame_valid_pixel_count": int(np.count_nonzero(valid)),
                "reference_used": False,
                "is_person_box": False,
                "region_identity_claimed": False,
            }
            if node["q95_pixel_count"] != int(region.pixel_count):
                raise RuntimeError(f"region pixel parity failed: {region.region_id}")
            nodes.append(node)
    node_table = pd.DataFrame(nodes)
    if len(node_table) != 1117:
        raise RuntimeError(f"expected 1117 q95 nodes, got {len(node_table)}")
    return {
        "geometry": geometry,
        "frame_table": frame_table,
        "region_table": region_table,
        "pairs": pairs,
        "frames": frames,
        "node_table": node_table,
    }


def safe_ratio(numerator: float, denominator: float) -> float:
    if not math.isfinite(denominator) or denominator <= 0:
        return math.nan
    return float(numerator / denominator)


def overlap_by_labels(weights: np.ndarray, label_map: np.ndarray) -> np.ndarray:
    maximum = int(label_map.max())
    return np.bincount(
        label_map.reshape(-1), weights=weights.reshape(-1), minlength=maximum + 1
    ).astype(np.float64)


def build_matrix(inputs: dict[str, Any]) -> pd.DataFrame:
    nodes = inputs["node_table"]
    frames = inputs["frames"]
    rows: list[dict[str, Any]] = []
    for pair in inputs["pairs"]:
        source_frame = frames[pair["from_frame_uid"]]
        destination_frame = frames[pair["to_frame_uid"]]
        source_nodes = nodes[nodes["frame_uid"].eq(pair["from_frame_uid"])].sort_values("region_label")
        destination_nodes = nodes[nodes["frame_uid"].eq(pair["to_frame_uid"])].sort_values("region_label")
        destination_q95_labels = destination_frame["labels"][Q95]
        destination_q975_positive = destination_frame["labels"][Q975] > 0
        destination_q90_labels = destination_frame["labels"][Q90]
        destination_valid = destination_frame["valid_mask"].astype(np.float32)
        destination_node_records = destination_nodes.to_dict("records")

        for source in source_nodes.to_dict("records"):
            q95_source, q975_source, q90_source, _, _ = region_layer_masks(
                source_frame["labels"], int(source["region_label"])
            )
            for condition, dx, dy in (
                ("P0", pair["dx_px"], pair["dy_px"]),
                ("ZERO", 0.0, 0.0),
            ):
                q95_warp = soft_affine_translation_warp(q95_source, dx, dy)
                q975_warp = (
                    soft_affine_translation_warp(q975_source, dx, dy)
                    if np.any(q975_source)
                    else np.zeros_like(q95_warp)
                )
                q90_warp = soft_affine_translation_warp(q90_source, dx, dy)
                q95_total = float(np.count_nonzero(q95_source))
                q95_before_valid = float(q95_warp.sum())
                q95_in_valid = float((q95_warp * destination_valid).sum())
                q95_transport_loss = q95_total - q95_in_valid
                q975_total = float(np.count_nonzero(q975_source))
                q975_in_valid = float((q975_warp * destination_valid).sum())
                q90_total = float(np.count_nonzero(q90_source))
                q90_in_valid = float((q90_warp * destination_valid).sum())

                q95_intersections = overlap_by_labels(q95_warp, destination_q95_labels)
                q975_to_q95 = overlap_by_labels(q975_warp, destination_q95_labels)
                q975_to_q975 = overlap_by_labels(
                    q975_warp * destination_q975_positive.astype(np.float32),
                    destination_q95_labels,
                )
                q90_label_intersections = overlap_by_labels(q90_warp, destination_q90_labels)

                for destination in destination_node_records:
                    destination_label = int(destination["region_label"])
                    intersection = float(q95_intersections[destination_label])
                    destination_total = float(destination["q95_pixel_count"])
                    q95_conditional = safe_ratio(intersection, q95_in_valid)
                    q95_source_total = safe_ratio(intersection, q95_total)
                    q95_destination_explained = safe_ratio(intersection, destination_total)
                    q95_soft_iou = safe_ratio(
                        intersection, q95_in_valid + destination_total - intersection
                    )
                    q975_q95_intersection = float(q975_to_q95[destination_label])
                    q975_q975_intersection = float(q975_to_q975[destination_label])
                    q90_labels = json.loads(destination["q90_labels_json"])
                    q90_intersection = float(
                        sum(
                            q90_label_intersections[int(label)]
                            for label in q90_labels
                            if int(label) < len(q90_label_intersections)
                        )
                    )
                    area_ratio = safe_ratio(float(destination["area_m2"]), float(source["area_m2"]))
                    base_edge_id = f"{pair['from_frame_uid']}__{source['region_id']}__TO__{destination['region_id']}"
                    rows.append(
                        {
                            "run_id": RUN_ID,
                            "pair_index": int(pair["pair_index"]),
                            "from_frame_uid": pair["from_frame_uid"],
                            "to_frame_uid": pair["to_frame_uid"],
                            "from_frame": int(pair["from_frame"]),
                            "to_frame": int(pair["to_frame"]),
                            "condition": condition,
                            "base_edge_id": base_edge_id,
                            "edge_id": f"{condition}__{base_edge_id}",
                            "source_region_id": source["region_id"],
                            "source_region_label": int(source["region_label"]),
                            "destination_region_id": destination["region_id"],
                            "destination_region_label": destination_label,
                            "p0_dx_px": float(pair["dx_px"]),
                            "p0_dy_px": float(pair["dy_px"]),
                            "applied_dx_px": float(dx),
                            "applied_dy_px": float(dy),
                            "pair_comparable": True,
                            "p0_model": "M1_GLOBAL_TRANSLATION",
                            "p0_model_available": True,
                            "comparability_reason": pair["comparability_reason"],
                            "pair_valid_fraction": float(pair["pair_valid_fraction"]),
                            "p0_holdout_median_px": float(pair["p0_holdout_median_px"]),
                            "p0_holdout_p90_px": float(pair["p0_holdout_p90_px"]),
                            "display_js_divergence": float(pair["display_js_divergence"]),
                            "display_stratum": pair["display_stratum"],
                            "source_support_total": q95_total,
                            "warped_support_before_valid_clip": q95_before_valid,
                            "warped_support_in_destination_valid": q95_in_valid,
                            "transport_out_of_frame_or_invalid": q95_transport_loss,
                            "valid_transport_fraction": safe_ratio(q95_in_valid, q95_total),
                            "q95_support_intersection_soft": intersection,
                            "q95_conditional_valid_retention": q95_conditional,
                            "q95_source_total_retention": q95_source_total,
                            "q95_destination_explained_fraction": q95_destination_explained,
                            "q95_soft_iou": q95_soft_iou,
                            "q975_source_support_total": q975_total,
                            "q975_warped_support_in_destination_valid": q975_in_valid,
                            "q975_to_q95_intersection_soft": q975_q95_intersection,
                            "q975_to_q95_core_retention": safe_ratio(q975_q95_intersection, q975_total),
                            "q975_to_q975_intersection_soft": q975_q975_intersection,
                            "q975_to_q975_core_retention": safe_ratio(q975_q975_intersection, q975_total),
                            "q90_source_support_total": q90_total,
                            "q90_warped_support_in_destination_valid": q90_in_valid,
                            "q90_weak_envelope_intersection_soft": q90_intersection,
                            "q90_weak_envelope_retention": safe_ratio(q90_intersection, q90_total),
                            "source_area_m2": float(source["area_m2"]),
                            "destination_area_m2": float(destination["area_m2"]),
                            "destination_to_source_area_ratio": area_ratio,
                            "source_theta_min_deg": float(source["theta_min_deg"]),
                            "source_theta_max_deg": float(source["theta_max_deg"]),
                            "source_theta_mid_deg": float(source["theta_mid_deg"]),
                            "destination_theta_min_deg": float(destination["theta_min_deg"]),
                            "destination_theta_max_deg": float(destination["theta_max_deg"]),
                            "destination_theta_mid_deg": float(destination["theta_mid_deg"]),
                            "theta_midpoint_change_deg": float(destination["theta_mid_deg"] - source["theta_mid_deg"]),
                            "source_range_min_m": float(source["range_min_m"]),
                            "source_range_max_m": float(source["range_max_m"]),
                            "source_range_mid_m": float(source["range_mid_m"]),
                            "destination_range_min_m": float(destination["range_min_m"]),
                            "destination_range_max_m": float(destination["range_max_m"]),
                            "destination_range_mid_m": float(destination["range_mid_m"]),
                            "range_midpoint_change_m": float(destination["range_mid_m"] - source["range_mid_m"]),
                            "source_touches_observable_boundary": bool(source["touches_observable_boundary"]),
                            "destination_touches_observable_boundary": bool(destination["touches_observable_boundary"]),
                            "source_has_truncated_support": bool(source["has_truncated_support"]),
                            "destination_has_truncated_support": bool(destination["has_truncated_support"]),
                            "destination_region_degree_shell_count": int(destination["region_degree_shell_count"]),
                            "destination_region_degree_bin": int(destination["region_degree_bin"]),
                            "destination_component_shell_count": int(destination["component_shell_count"]),
                            "destination_component_shell_count_bin": int(destination["component_shell_count_bin"]),
                            "destination_component_region_count": int(destination["component_region_count"]),
                            "destination_static_topology_state": destination["static_topology_state"],
                            "reference_used": False,
                            "identity_assignment_performed": False,
                            "edge_selected_as_unique": False,
                        }
                    )
        print(
            f"pair {pair['from_frame']}->{pair['to_frame']} matrix rows={len(source_nodes) * len(destination_nodes) * 2}",
            flush=True,
        )
    matrix = pd.DataFrame(rows)
    prohibited = PROHIBITED_PRE_REFERENCE_COLUMNS & set(matrix.columns)
    if prohibited:
        raise RuntimeError(f"prohibited columns in matrix: {sorted(prohibited)}")
    return matrix


def structural_distance(edge: pd.Series, alternative: pd.Series) -> float:
    area_edge = max(float(edge["destination_area_m2"]), 1e-12)
    area_alt = max(float(alternative["destination_area_m2"]), 1e-12)
    return float(
        4.0
        * (
            bool(edge["destination_touches_observable_boundary"])
            != bool(alternative["destination_touches_observable_boundary"])
        )
        + 4.0
        * (
            bool(edge["destination_has_truncated_support"])
            != bool(alternative["destination_has_truncated_support"])
        )
        + abs(
            int(edge["destination_region_degree_bin"])
            - int(alternative["destination_region_degree_bin"])
        )
        + abs(
            int(edge["destination_component_shell_count_bin"])
            - int(alternative["destination_component_shell_count_bin"])
        )
        + abs(math.log(area_alt / area_edge))
        + abs(
            float(alternative["theta_midpoint_change_deg"])
            - float(edge["theta_midpoint_change_deg"])
        )
        / 5.0
        + abs(
            float(alternative["range_midpoint_change_m"])
            - float(edge["range_midpoint_change_m"])
        )
    )


def build_matched_alternatives(matrix: pd.DataFrame) -> pd.DataFrame:
    structural = matrix[matrix["condition"].eq("P0")].copy()
    rows: list[dict[str, Any]] = []
    for (_, source_region_id), group in structural.groupby(
        ["pair_index", "source_region_id"], sort=True
    ):
        group = group.sort_values("destination_region_id").reset_index(drop=True)
        records = group.to_dict("records")
        series = [pd.Series(record) for record in records]
        for edge_index, edge in enumerate(series):
            alternatives: list[tuple[float, str, pd.Series]] = []
            for alternative_index, alternative in enumerate(series):
                if alternative_index == edge_index:
                    continue
                distance = structural_distance(edge, alternative)
                alternatives.append(
                    (distance, str(alternative["destination_region_id"]), alternative)
                )
            alternatives.sort(key=lambda item: (item[0], item[1]))
            for rank, (distance, _, alternative) in enumerate(
                alternatives[:MATCHED_ALTERNATIVE_COUNT], start=1
            ):
                rows.append(
                    {
                        "run_id": RUN_ID,
                        "pair_index": int(edge["pair_index"]),
                        "from_frame_uid": edge["from_frame_uid"],
                        "to_frame_uid": edge["to_frame_uid"],
                        "source_region_id": source_region_id,
                        "primary_base_edge_id": edge["base_edge_id"],
                        "primary_destination_region_id": edge["destination_region_id"],
                        "alternative_rank": rank,
                        "alternative_base_edge_id": alternative["base_edge_id"],
                        "alternative_destination_region_id": alternative["destination_region_id"],
                        "structural_distance": distance,
                        "matching_rule": "TOP5_RUNTIME_STRUCTURAL_DISTANCE_V1",
                        "reference_used": False,
                        "alternative_removed_after_reference": False,
                    }
                )
    return pd.DataFrame(rows)


def choose_record(frame: pd.DataFrame, column: str, largest: bool = True) -> pd.Series:
    ordered = frame.sort_values(
        [column, "base_edge_id"], ascending=[not largest, True], na_position="last"
    )
    if ordered.empty:
        raise RuntimeError(f"no rows for case selection: {column}")
    return ordered.iloc[0]


def deterministic_destination_ranks(matrix: pd.DataFrame) -> pd.DataFrame:
    """Rank by retention descending; break exact ties by destination region ID."""
    ranked = matrix.copy()
    ranked = ranked.sort_values(
        [
            "pair_index",
            "condition",
            "source_region_id",
            "q95_source_total_retention",
            "destination_region_id",
        ],
        ascending=[True, True, True, False, True],
        na_position="last",
    )
    ranked["destination_rank"] = (
        ranked.groupby(["pair_index", "condition", "source_region_id"], sort=False)
        .cumcount()
        .add(1)
        .astype(int)
    )
    ranked["destination_pool_count"] = ranked.groupby(
        ["pair_index", "condition", "source_region_id"], sort=False
    )["destination_region_id"].transform("count").astype(int)
    ranked["destination_rank_percentile"] = [
        rank_percentile(int(rank), int(count))
        for rank, count in zip(ranked["destination_rank"], ranked["destination_pool_count"])
    ]
    return ranked.sort_index()


def build_pre_reference_cases(matrix: pd.DataFrame) -> pd.DataFrame:
    p0 = matrix[matrix["condition"].eq("P0")].copy()
    zero = matrix[matrix["condition"].eq("ZERO")][
        ["base_edge_id", "q95_source_total_retention"]
    ].rename(columns={"q95_source_total_retention": "zero_q95_source_total_retention"})
    paired = p0.merge(zero, on="base_edge_id", how="inner", validate="one_to_one")
    paired["p0_minus_zero"] = (
        paired["q95_source_total_retention"] - paired["zero_q95_source_total_retention"]
    )
    cases: list[dict[str, Any]] = []

    def add(case_type: str, row: pd.Series, related: list[str] | None = None) -> None:
        cases.append(
            {
                "case_type": case_type,
                "selection_phase": "PRE_REFERENCE",
                "base_edge_id": row["base_edge_id"],
                "pair_index": int(row["pair_index"]),
                "from_frame_uid": row["from_frame_uid"],
                "to_frame_uid": row["to_frame_uid"],
                "source_region_id": row["source_region_id"],
                "destination_region_id": row["destination_region_id"],
                "related_destination_region_ids_json": json.dumps(related or []),
                "p0_q95_source_total_retention": json_number(row["q95_source_total_retention"]),
                "zero_q95_source_total_retention": json_number(row["zero_q95_source_total_retention"]),
                "p0_minus_zero": json_number(row["p0_minus_zero"]),
                "selection_used_reference": False,
            }
        )

    add("P0_CLEARLY_BETTER_THAN_ZERO", choose_record(paired, "p0_minus_zero", True))
    strong = paired[
        paired["q95_source_total_retention"]
        >= paired["q95_source_total_retention"].quantile(0.75)
    ].copy()
    strong["abs_delta"] = strong["p0_minus_zero"].abs()
    add("P0_APPROX_EQUAL_ZERO", choose_record(strong, "abs_delta", False))
    add("ZERO_BETTER_THAN_P0", choose_record(paired, "p0_minus_zero", False))
    add("STRONG_Q95_CONTINUATION", choose_record(paired, "q95_source_total_retention", True))

    q90 = paired.dropna(subset=["q90_weak_envelope_retention"]).copy()
    q90["q90_minus_q95"] = q90["q90_weak_envelope_retention"] - q90["q95_source_total_retention"]
    add("Q95_WEAK_Q90_ENVELOPE_CONTINUES", choose_record(q90, "q90_minus_q95", True))

    core = paired.dropna(subset=["q975_to_q975_core_retention"]).copy()
    core = core[core["q95_source_total_retention"] >= core["q95_source_total_retention"].quantile(0.75)]
    core["q95_minus_q975"] = core["q95_source_total_retention"] - core["q975_to_q975_core_retention"]
    add("Q975_CORE_CHANGES_Q95_CONTINUES", choose_record(core, "q95_minus_q975", True))

    split_candidates: list[tuple[float, pd.Series, list[str]]] = []
    for _, group in paired.groupby(["pair_index", "source_region_id"], sort=True):
        ordered = group.sort_values(
            ["q95_source_total_retention", "destination_region_id"],
            ascending=[False, True],
        )
        if len(ordered) >= 2:
            split_candidates.append(
                (
                    float(ordered.iloc[1]["q95_source_total_retention"]),
                    ordered.iloc[0],
                    ordered.iloc[:2]["destination_region_id"].astype(str).tolist(),
                )
            )
    split_candidates.sort(key=lambda item: (-item[0], str(item[1]["base_edge_id"])))
    if not split_candidates:
        raise RuntimeError("no eligible split-like case")
    add("SPLIT_LIKE", split_candidates[0][1], split_candidates[0][2])

    merge_candidates: list[tuple[float, pd.Series, list[str]]] = []
    for _, group in paired.groupby(["pair_index", "destination_region_id"], sort=True):
        ordered = group.sort_values(
            ["q95_destination_explained_fraction", "source_region_id"],
            ascending=[False, True],
        )
        if len(ordered) >= 2:
            merge_candidates.append(
                (
                    float(ordered.iloc[1]["q95_destination_explained_fraction"]),
                    ordered.iloc[0],
                    ordered.iloc[:2]["source_region_id"].astype(str).tolist(),
                )
            )
    merge_candidates.sort(key=lambda item: (-item[0], str(item[1]["base_edge_id"])))
    if not merge_candidates:
        raise RuntimeError("no eligible merge-like case")
    add("MERGE_LIKE", merge_candidates[0][1], merge_candidates[0][2])

    boundary = paired[
        paired[
            [
                "source_touches_observable_boundary",
                "destination_touches_observable_boundary",
                "source_has_truncated_support",
                "destination_has_truncated_support",
            ]
        ].astype(bool).any(axis=1)
    ]
    add("BOUNDARY_OR_TRUNCATED", choose_record(boundary, "q95_source_total_retention", True))
    return pd.DataFrame(cases)


def pre_reference_phase() -> None:
    freeze = verify_protocol_freeze()
    if not SYNTHETIC_PATH.exists():
        raise RuntimeError("synthetic tests must run before pre-reference phase")
    synthetic = json.loads(SYNTHETIC_PATH.read_text(encoding="utf-8"))
    if synthetic.get("status") != "PASS" or synthetic.get("tests_passed") != 5:
        raise RuntimeError("synthetic tests did not pass 5/5")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started = now_iso()
    inputs = prepare_runtime_inputs()
    inputs["node_table"].to_csv(NODE_PATH, index=False, encoding="utf-8-sig")
    matrix = build_matrix(inputs)
    matrix.to_csv(MATRIX_PATH, index=False, encoding="utf-8-sig")
    matched = build_matched_alternatives(matrix)
    matched.to_csv(MATCHED_PATH, index=False, encoding="utf-8-sig")
    cases = build_pre_reference_cases(matrix)
    cases.to_csv(PRE_CASE_PATH, index=False, encoding="utf-8-sig")
    completed = now_iso()
    manifest = {
        "schema": "PERSON_M0A_PRE_REFERENCE_MANIFEST_V1",
        "status": "PRE_REFERENCE_MATERIALIZED_NOT_YET_HASH_FROZEN",
        "created_at": completed,
        "study_role": "M0_SAR_TEMPORAL_PREREQUISITE",
        "run_id": RUN_ID,
        "starting_head": freeze["starting_head"],
        "protocol_sha256": freeze["protocol_sha256"],
        "reference_loaded": False,
        "manual_fields_present_in_runtime_tables": False,
        "pair_count": len(inputs["pairs"]),
        "frame_count": len(inputs["frames"]),
        "q95_node_count": len(inputs["node_table"]),
        "matrix_row_count": len(matrix),
        "p0_matrix_row_count": int(matrix["condition"].eq("P0").sum()),
        "zero_matrix_row_count": int(matrix["condition"].eq("ZERO").sum()),
        "matched_alternative_row_count": len(matched),
        "pre_reference_case_count": len(cases),
        "valid_mask_pixel_count_by_frame": {
            uid: int(np.count_nonzero(frame["valid_mask"]))
            for uid, frame in inputs["frames"].items()
        },
        "outputs": [
            str(path.relative_to(WORKSPACE))
            for path in (NODE_PATH, MATRIX_PATH, MATCHED_PATH, PRE_CASE_PATH)
        ],
        "prohibited_operations": {
            "mutual_nearest": False,
            "hungarian": False,
            "unique_edge": False,
            "thread_or_path": False,
            "identity_assignment": False,
            "score_fusion": False,
            "optical_dynamics": False,
            "sar_localization": False,
        },
    }
    write_json(PRE_MANIFEST_PATH, manifest)
    ledger = {
        "schema": "PERSON_M0A_PRE_REFERENCE_EXECUTION_LEDGER_V1",
        "reference_loaded": False,
        "events": [
            {"stage": "PROTOCOL_AND_CODE_HASHES_VERIFIED", "completed_at": started},
            {"stage": "SYNTHETIC_WARP_TESTS_PASS_5_OF_5", "completed_at": started},
            {"stage": "RUNTIME_INPUTS_LOADED_WITHOUT_REFERENCE", "completed_at": started},
            {"stage": "Q95_NODES_MATERIALIZED", "completed_at": completed, "rows": len(inputs["node_table"])},
            {"stage": "P0_AND_ZERO_COMPLETE_PAIR_MATRICES_MATERIALIZED", "completed_at": completed, "rows": len(matrix)},
            {"stage": "MATCHED_STRUCTURAL_ALTERNATIVES_FROZEN", "completed_at": completed, "rows": len(matched)},
            {"stage": "PRE_REFERENCE_CASE_REGISTRY_FROZEN", "completed_at": completed, "rows": len(cases)},
            {"stage": "REFERENCE_NOT_LOADED_PRE_REFERENCE_PHASE_CLOSED", "completed_at": completed},
        ],
    }
    write_json(PRE_LEDGER_PATH, ledger)
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)


def freeze_pre_reference_phase() -> None:
    verify_protocol_freeze()
    if not PRE_VALIDATION_PATH.exists():
        raise RuntimeError("pre-reference validation is missing")
    validation = json.loads(PRE_VALIDATION_PATH.read_text(encoding="utf-8"))
    if validation.get("status") != "PASS":
        raise RuntimeError("pre-reference validation did not pass")
    pre_figures = sorted(PRE_FIGURE_DIR.glob("*.png"))
    if len(pre_figures) != 9:
        raise RuntimeError(f"expected 9 pre-reference case figures, got {len(pre_figures)}")
    paths = [
        SYNTHETIC_PATH,
        NODE_PATH,
        MATRIX_PATH,
        MATCHED_PATH,
        PRE_CASE_PATH,
        PRE_MANIFEST_PATH,
        PRE_LEDGER_PATH,
        PRE_VALIDATION_PATH,
    ] + pre_figures
    record = {
        "schema": "PERSON_M0A_PRE_REFERENCE_OUTPUT_HASH_FREEZE_V1",
        "status": "FROZEN_BEFORE_REFERENCE_REVEAL",
        "created_at": now_iso(),
        "reference_loaded": False,
        "files": [
            {
                "path": str(path.relative_to(WORKSPACE)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in paths
        ],
    }
    record["freeze_payload_sha256"] = sha256_object(record)
    write_json(PRE_HASH_PATH, record)
    print(json.dumps(record, ensure_ascii=False, indent=2), flush=True)


def verify_pre_reference_hash_freeze() -> dict[str, Any]:
    if not PRE_HASH_PATH.exists():
        raise RuntimeError("pre-reference output hash freeze missing")
    record = json.loads(PRE_HASH_PATH.read_text(encoding="utf-8"))
    if record.get("status") != "FROZEN_BEFORE_REFERENCE_REVEAL":
        raise RuntimeError("pre-reference outputs are not frozen")
    expected_payload = record.pop("freeze_payload_sha256")
    if sha256_object(record) != expected_payload:
        raise RuntimeError("pre-reference freeze payload hash mismatch")
    record["freeze_payload_sha256"] = expected_payload
    for item in record["files"]:
        path = WORKSPACE / item["path"]
        if sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"pre-reference output changed: {path}")
    return record


def rank_percentile(rank: int, pool_count: int) -> float:
    if pool_count <= 1:
        return 1.0
    return 1.0 - (rank - 1) / float(pool_count - 1)


def post_reference_phase() -> None:
    freeze = verify_protocol_freeze()
    pre_freeze = verify_pre_reference_hash_freeze()
    matrix = pd.read_csv(MATRIX_PATH, low_memory=False)
    matched = pd.read_csv(MATCHED_PATH, low_memory=False)

    # Reference reveal begins here and nowhere earlier in this script.
    reference_sha256 = sha256_file(REFERENCE_PATH)
    reference_center_sha256 = sha256_file(REFERENCE_CENTER_PATH)
    references = pd.read_csv(REFERENCE_PATH)
    near_reference = require_bool_series(
        references["region_near_reference_0p30m"], "region_near_reference_0p30m"
    )
    references = references[
        references["run_id"].eq(RUN_ID)
        & references["percentile_tag"].eq(Q95)
        & near_reference
        & references["nearest_region_id"].notna()
        & pd.to_numeric(references["frame_index"], errors="raise").between(
            EXPECTED_FRAME_START, EXPECTED_FRAME_END
        )
    ].copy()
    mapping: dict[tuple[str, str], str] = {
        (str(row.frame_uid), str(row.target_id)): str(row.nearest_region_id)
        for row in references.itertuples(index=False)
    }
    reference_centers = pd.read_csv(
        REFERENCE_CENTER_PATH,
        usecols=[
            "run_id",
            "frame_uid",
            "frame_index",
            "target_id",
            "reference_x_px",
            "reference_y_px",
        ],
    )
    reference_centers = reference_centers[
        reference_centers["run_id"].eq(RUN_ID)
        & pd.to_numeric(reference_centers["frame_index"], errors="raise").between(
            EXPECTED_FRAME_START, EXPECTED_FRAME_END
        )
    ].drop_duplicates(["frame_uid", "target_id"])
    center_map: dict[tuple[str, str], tuple[float, float]] = {
        (str(row.frame_uid), str(row.target_id)): (
            float(row.reference_x_px),
            float(row.reference_y_px),
        )
        for row in reference_centers.itertuples(index=False)
    }
    targets_by_edge: dict[str, list[str]] = {}
    supported_rows: list[dict[str, Any]] = []
    pairs = load_pair_records()
    for pair in pairs:
        source_targets = {
            target: region
            for (frame_uid, target), region in mapping.items()
            if frame_uid == pair["from_frame_uid"]
        }
        destination_targets = {
            target: region
            for (frame_uid, target), region in mapping.items()
            if frame_uid == pair["to_frame_uid"]
        }
        for target_id in sorted(set(source_targets) & set(destination_targets)):
            source_region_id = source_targets[target_id]
            destination_region_id = destination_targets[target_id]
            base_edge_id = f"{pair['from_frame_uid']}__{source_region_id}__TO__{destination_region_id}"
            targets_by_edge.setdefault(base_edge_id, []).append(target_id)

    matrix = deterministic_destination_ranks(matrix)
    supported_matrix = matrix[matrix["base_edge_id"].isin(targets_by_edge)].copy()
    for row in supported_matrix.to_dict("records"):
        target_ids = sorted(targets_by_edge[row["base_edge_id"]])
        source_centers = [
            {"target_id": target_id, "x_px": center_map[(row["from_frame_uid"], target_id)][0],
             "y_px": center_map[(row["from_frame_uid"], target_id)][1]}
            for target_id in target_ids
        ]
        destination_centers = [
            {"target_id": target_id, "x_px": center_map[(row["to_frame_uid"], target_id)][0],
             "y_px": center_map[(row["to_frame_uid"], target_id)][1]}
            for target_id in target_ids
        ]
        supported_rows.append(
            {
                **row,
                "reference_support_state": "REFERENCE_SUPPORTED_DYNAMIC_EXPLANATION",
                "supported_target_ids": ";".join(target_ids),
                "supported_target_count": len(target_ids),
                "shared_or_unresolved": len(target_ids) > 1,
                "source_manual_centers_json": json.dumps(source_centers, sort_keys=True),
                "destination_manual_centers_json": json.dumps(destination_centers, sort_keys=True),
            }
        )
    supported = pd.DataFrame(supported_rows)
    supported.to_csv(POST_SUPPORTED_PATH, index=False, encoding="utf-8-sig")

    matrix_index = matrix.set_index(["condition", "base_edge_id"])
    comparison_rows: list[dict[str, Any]] = []
    for supported_row in supported.to_dict("records"):
        base_edge_id = supported_row["base_edge_id"]
        condition = supported_row["condition"]
        alternatives = matched[matched["primary_base_edge_id"].eq(base_edge_id)]
        supported_value = float(supported_row["q95_source_total_retention"])
        for alternative in alternatives.to_dict("records"):
            key = (condition, alternative["alternative_base_edge_id"])
            if key not in matrix_index.index:
                raise RuntimeError(f"missing matched alternative matrix row: {key}")
            alt = matrix_index.loc[key]
            if isinstance(alt, pd.DataFrame):
                alt = alt.iloc[0]
            alternative_value = float(alt["q95_source_total_retention"])
            difference = supported_value - alternative_value
            if difference > TIE_TOLERANCE:
                outcome = "SUPPORTED_WIN"
            elif difference < -TIE_TOLERANCE:
                outcome = "ALTERNATIVE_WIN"
            else:
                outcome = "TIE"
            alt_targets = targets_by_edge.get(alternative["alternative_base_edge_id"], [])
            alternative_state = (
                "ALSO_REFERENCE_SUPPORTED_OR_SHARED" if alt_targets else "REFERENCE_UNSUPPORTED"
            )
            comparison_rows.append(
                {
                    "condition": condition,
                    "primary_base_edge_id": base_edge_id,
                    "supported_target_ids": supported_row["supported_target_ids"],
                    "alternative_rank": int(alternative["alternative_rank"]),
                    "alternative_base_edge_id": alternative["alternative_base_edge_id"],
                    "alternative_destination_region_id": alternative["alternative_destination_region_id"],
                    "structural_distance": float(alternative["structural_distance"]),
                    "alternative_reference_state": alternative_state,
                    "alternative_supported_target_ids": ";".join(sorted(alt_targets)),
                    "supported_q95_source_total_retention": supported_value,
                    "alternative_q95_source_total_retention": alternative_value,
                    "supported_minus_alternative": difference,
                    "pairwise_outcome": outcome,
                    "frozen_alternative_preserved": True,
                }
            )
    comparisons = pd.DataFrame(comparison_rows)
    comparisons.to_csv(POST_MATCHED_PATH, index=False, encoding="utf-8-sig")

    p0_supported = supported[supported["condition"].eq("P0")].copy()
    zero_supported = supported[supported["condition"].eq("ZERO")][
        ["base_edge_id", "q95_source_total_retention", "destination_rank", "destination_rank_percentile"]
    ].rename(
        columns={
            "q95_source_total_retention": "zero_q95_source_total_retention",
            "destination_rank": "zero_destination_rank",
            "destination_rank_percentile": "zero_destination_rank_percentile",
        }
    )
    p0_zero = p0_supported.merge(zero_supported, on="base_edge_id", how="inner", validate="one_to_one")
    p0_zero["p0_minus_zero"] = (
        p0_zero["q95_source_total_retention"] - p0_zero["zero_q95_source_total_retention"]
    )
    unsupported_comparisons = comparisons[
        comparisons["alternative_reference_state"].eq("REFERENCE_UNSUPPORTED")
    ]
    p0_unsupported = unsupported_comparisons[unsupported_comparisons["condition"].eq("P0")]
    zero_unsupported = unsupported_comparisons[unsupported_comparisons["condition"].eq("ZERO")]

    p0_win_rate = float(p0_unsupported["pairwise_outcome"].eq("SUPPORTED_WIN").mean()) if len(p0_unsupported) else math.nan
    zero_win_rate = float(zero_unsupported["pairwise_outcome"].eq("SUPPORTED_WIN").mean()) if len(zero_unsupported) else math.nan
    rank_percentile_median = float(p0_supported["destination_rank_percentile"].median())
    p0_better_fraction = float((p0_zero["p0_minus_zero"] > TIE_TOLERANCE).mean())
    p0_minus_zero_median = float(p0_zero["p0_minus_zero"].median())
    discrimination = p0_win_rate > 0.5 and rank_percentile_median > 0.5
    p0_gain = p0_better_fraction > 0.60 and p0_minus_zero_median > 0.01
    if discrimination and p0_gain:
        state = "M0A_REGION_SUPPORT_TRANSPORT_WITH_P0_GAIN"
    elif discrimination:
        state = "M0A_REGION_SUPPORT_TEMPORAL_PERSISTENCE_WITHOUT_CLEAR_P0_SPECIFIC_GAIN"
    else:
        state = "M0A_REGION_SUPPORT_TEMPORAL_DISCRIMINATION_WEAK"

    post_cases: list[dict[str, Any]] = []
    best = p0_supported.sort_values(
        ["destination_rank_percentile", "base_edge_id"], ascending=[False, True]
    ).iloc[0]
    worst = p0_supported.sort_values(
        ["destination_rank_percentile", "base_edge_id"], ascending=[True, True]
    ).iloc[0]
    deceptive_pool = comparisons[
        comparisons["condition"].eq("P0")
        & comparisons["pairwise_outcome"].eq("ALTERNATIVE_WIN")
    ].copy()
    deceptive_pool["alternative_margin"] = -deceptive_pool["supported_minus_alternative"]
    deceptive = (
        deceptive_pool.sort_values(
            ["alternative_margin", "primary_base_edge_id"], ascending=[False, True]
        ).iloc[0]
        if len(deceptive_pool)
        else None
    )
    strongest_available = None
    if deceptive is None and len(comparisons):
        available = comparisons[comparisons["condition"].eq("P0")].copy()
        if len(available):
            available["alternative_margin"] = -available["supported_minus_alternative"]
            strongest_available = available.sort_values(
                ["alternative_margin", "primary_base_edge_id"], ascending=[False, True]
            ).iloc[0]
    for case_type, row in (
        ("REFERENCE_SUPPORTED_RANKS_WELL", best),
        ("REFERENCE_SUPPORTED_RANKS_POORLY", worst),
    ):
        post_cases.append(
            {
                "case_type": case_type,
                "selection_phase": "POST_REFERENCE",
                "base_edge_id": row["base_edge_id"],
                "condition": "P0",
                "source_region_id": row["source_region_id"],
                "destination_region_id": row["destination_region_id"],
                "supported_target_ids": row["supported_target_ids"],
                "destination_rank": int(row["destination_rank"]),
                "destination_pool_count": int(row["destination_pool_count"]),
                "destination_rank_percentile": float(row["destination_rank_percentile"]),
                "selection_used_reference": True,
            }
        )
    if deceptive is not None:
        supported_row = p0_supported[
            p0_supported["base_edge_id"].eq(deceptive["primary_base_edge_id"])
        ].iloc[0]
        post_cases.append(
            {
                "case_type": "MATCHED_ALTERNATIVE_DECEPTIVELY_STRONG",
                "selection_phase": "POST_REFERENCE",
                "base_edge_id": deceptive["primary_base_edge_id"],
                "condition": "P0",
                "source_region_id": supported_row["source_region_id"],
                "destination_region_id": supported_row["destination_region_id"],
                "related_destination_region_ids_json": json.dumps(
                    [deceptive["alternative_destination_region_id"]]
                ),
                "supported_target_ids": supported_row["supported_target_ids"],
                "destination_rank": int(supported_row["destination_rank"]),
                "destination_pool_count": int(supported_row["destination_pool_count"]),
                "destination_rank_percentile": float(supported_row["destination_rank_percentile"]),
                "alternative_margin": float(deceptive["alternative_margin"]),
                "selection_used_reference": True,
            }
        )
    elif strongest_available is not None:
        supported_row = p0_supported[
            p0_supported["base_edge_id"].eq(strongest_available["primary_base_edge_id"])
        ].iloc[0]
        post_cases.append(
            {
                "case_type": "NO_DECEPTIVE_ALTERNATIVE_FOUND_STRONGEST_AVAILABLE",
                "selection_phase": "POST_REFERENCE",
                "base_edge_id": strongest_available["primary_base_edge_id"],
                "condition": "P0",
                "source_region_id": supported_row["source_region_id"],
                "destination_region_id": supported_row["destination_region_id"],
                "related_destination_region_ids_json": json.dumps(
                    [strongest_available["alternative_destination_region_id"]]
                ),
                "supported_target_ids": supported_row["supported_target_ids"],
                "destination_rank": int(supported_row["destination_rank"]),
                "destination_pool_count": int(supported_row["destination_pool_count"]),
                "destination_rank_percentile": float(supported_row["destination_rank_percentile"]),
                "alternative_margin": float(strongest_available["alternative_margin"]),
                "selection_used_reference": True,
            }
        )
    pd.DataFrame(post_cases).to_csv(POST_CASE_PATH, index=False, encoding="utf-8-sig")

    def describe(frame: pd.DataFrame, column: str) -> dict[str, Any]:
        values = pd.to_numeric(frame[column], errors="coerce").dropna()
        return {
            "count": int(len(values)),
            "median": float(values.median()) if len(values) else None,
            "p25": float(values.quantile(0.25)) if len(values) else None,
            "p75": float(values.quantile(0.75)) if len(values) else None,
            "mean": float(values.mean()) if len(values) else None,
        }

    summary = {
        "schema": "PERSON_M0A_POST_REFERENCE_SUMMARY_V1",
        "created_at": now_iso(),
        "study_role": "M0_SAR_TEMPORAL_PREREQUISITE",
        "final_m0a_state": state,
        "not_optical_sar_motion_consistency": True,
        "reference_sha256": reference_sha256,
        "reference_center_sha256": reference_center_sha256,
        "pre_reference_freeze_payload_sha256": pre_freeze["freeze_payload_sha256"],
        "reference_supported_explanation_rows": int(len(supported)),
        "reference_supported_unique_base_edges": int(supported["base_edge_id"].nunique()),
        "reference_supported_target_transitions": int(len(p0_supported)),
        "shared_supported_edge_fraction": float(
            require_bool_series(
                p0_supported["shared_or_unresolved"], "shared_or_unresolved"
            ).mean()
        ),
        "p0_supported_q95_source_total_retention": describe(p0_supported, "q95_source_total_retention"),
        "zero_supported_q95_source_total_retention": describe(
            supported[supported["condition"].eq("ZERO")], "q95_source_total_retention"
        ),
        "p0_supported_q95_conditional_valid_retention": describe(
            p0_supported, "q95_conditional_valid_retention"
        ),
        "p0_valid_transport_fraction": describe(p0_supported, "valid_transport_fraction"),
        "p0_supported_rank": describe(p0_supported, "destination_rank"),
        "p0_supported_rank_percentile": describe(p0_supported, "destination_rank_percentile"),
        "p0_vs_zero": {
            "paired_count": int(len(p0_zero)),
            "p0_better_fraction": p0_better_fraction,
            "tie_fraction": float((p0_zero["p0_minus_zero"].abs() <= TIE_TOLERANCE).mean()),
            "zero_better_fraction": float((p0_zero["p0_minus_zero"] < -TIE_TOLERANCE).mean()),
            "median_source_total_retention_delta": p0_minus_zero_median,
            "mean_source_total_retention_delta": float(p0_zero["p0_minus_zero"].mean()),
        },
        "matched_reference_unsupported": {
            "p0_comparison_count": int(len(p0_unsupported)),
            "p0_supported_win_rate": p0_win_rate,
            "p0_tie_rate": float(p0_unsupported["pairwise_outcome"].eq("TIE").mean()) if len(p0_unsupported) else None,
            "p0_alternative_win_rate": float(p0_unsupported["pairwise_outcome"].eq("ALTERNATIVE_WIN").mean()) if len(p0_unsupported) else None,
            "zero_comparison_count": int(len(zero_unsupported)),
            "zero_supported_win_rate": zero_win_rate,
        },
        "q975_and_q90": {
            "p0_q975_to_q95_core_retention": describe(p0_supported, "q975_to_q95_core_retention"),
            "p0_q975_to_q975_core_retention": describe(p0_supported, "q975_to_q975_core_retention"),
            "p0_q90_weak_envelope_retention": describe(p0_supported, "q90_weak_envelope_retention"),
            "q95_minus_q975_median": float(
                (p0_supported["q95_source_total_retention"] - p0_supported["q975_to_q975_core_retention"]).median()
            ),
            "q90_minus_q95_median": float(
                (p0_supported["q90_weak_envelope_retention"] - p0_supported["q95_source_total_retention"]).median()
            ),
        },
        "outcome_rule_inputs": {
            "discrimination": discrimination,
            "p0_gain": p0_gain,
            "p0_supported_win_rate_vs_reference_unsupported": p0_win_rate,
            "supported_rank_percentile_median": rank_percentile_median,
            "p0_better_fraction": p0_better_fraction,
            "p0_minus_zero_median": p0_minus_zero_median,
        },
        "prohibited_claims": {
            "optical_sar_motion_consistency_established": False,
            "cross_modal_ambiguity_reduced": False,
            "person_dynamic_association_established": False,
            "runtime_identity_established": False,
            "final_sar_localization_established": False,
        },
    }
    write_json(POST_SUMMARY_PATH, summary)
    pre_ledger = json.loads(PRE_LEDGER_PATH.read_text(encoding="utf-8"))
    ledger = {
        "schema": "PERSON_M0A_EXECUTION_LEDGER_V1",
        "events": pre_ledger["events"]
        + [
            {
                "stage": "PRE_REFERENCE_OUTPUTS_HASH_FROZEN",
                "completed_at": pre_freeze["created_at"],
                "reference_loaded": False,
            },
            {
                "stage": "MANUAL_REFERENCE_REVEALED_AFTER_FREEZE",
                "completed_at": now_iso(),
                "reference_sha256": reference_sha256,
                "reference_center_sha256": reference_center_sha256,
            },
            {
                "stage": "POST_REFERENCE_EVALUATION_COMPLETE",
                "completed_at": now_iso(),
                "final_m0a_state": state,
            },
        ],
    }
    write_json(EXECUTION_LEDGER_PATH, ledger)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        required=True,
        choices=("pre-reference", "freeze-pre-reference", "post-reference"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.phase == "pre-reference":
        pre_reference_phase()
    elif args.phase == "freeze-pre-reference":
        freeze_pre_reference_phase()
    elif args.phase == "post-reference":
        post_reference_phase()


if __name__ == "__main__":
    main()
