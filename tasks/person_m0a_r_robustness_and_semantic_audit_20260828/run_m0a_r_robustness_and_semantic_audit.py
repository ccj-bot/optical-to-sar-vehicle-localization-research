#!/usr/bin/env python3
"""Read-only robustness and semantic audit over frozen PERSON M0A artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
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
STUDY_OUTPUT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
M0A_ROOT = STUDY_OUTPUT / "m0a_r02_lag1_q95_region_support_transport_pilot"
OUTPUT_DIR = STUDY_OUTPUT / "m0a_r_robustness_and_semantic_audit"
FIGURE_DIR = OUTPUT_DIR / "figures"
PROTOCOL_PATH = OUTPUT_DIR / "M0A_R_ROBUSTNESS_AND_SEMANTIC_AUDIT_PROTOCOL_FROZEN_BEFORE_RUN.md"
FREEZE_PATH = OUTPUT_DIR / "protocol_freeze.json"

NODE_PATH = M0A_ROOT / "pre_reference_region_nodes.csv"
MATRIX_PATH = M0A_ROOT / "pre_reference_compatibility_matrix.csv"
MATCHED_PATH = M0A_ROOT / "pre_reference_matched_alternative_sets.csv"
PRE_CASE_PATH = M0A_ROOT / "pre_reference_case_registry.csv"
SUPPORTED_PATH = M0A_ROOT / "post_reference_supported_explanations.csv"
COMPARISON_PATH = M0A_ROOT / "post_reference_matched_alternative_evaluation.csv"
POST_CASE_PATH = M0A_ROOT / "post_reference_case_registry.csv"
M0A_SUMMARY_PATH = M0A_ROOT / "post_reference_summary.json"
M0A_VALIDATION_PATH = M0A_ROOT / "final_validation.json"
M0A_PROTOCOL_PATH = M0A_ROOT / "M0A_R02_LAG1_Q95_REGION_SUPPORT_TRANSPORT_PROTOCOL_FROZEN_BEFORE_RUN.md"

REGION_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface" / "runtime_track_response_region_minimal_v1"
MASK_DIR = REGION_ROOT / "response_region_masks"
REFERENCE_REGION_PATH = REGION_ROOT / "offline_reference_response_region_evaluation.csv"
REFERENCE_CENTER_PATH = (
    STUDY_OUTPUT
    / "p1e_sar_only_response_interface"
    / "candidate_recall_semantic_split_v1"
    / "single_frame_candidate_recall"
    / "manual_reference_candidate_interpretation_v2.csv"
)
IMAGE_DIR = (
    WORKSPACE
    / "output"
    / "pseudocolor_labelstudio_prep_20260722"
    / "frames"
    / "sar_pseudocolor"
    / "R02ZF"
)

STRATA_PATH = OUTPUT_DIR / "support_size_strata.csv"
SUPPORTED_AUDIT_PATH = OUTPUT_DIR / "supported_edge_audit.csv"
CLUSTER_PATH = OUTPUT_DIR / "cluster_aware_summary.csv"
LOO_PATH = OUTPUT_DIR / "leave_one_frame_pair_out.csv"
MATCHED_CLUSTER_PATH = OUTPUT_DIR / "matched_alternative_cluster_audit.csv"
CONTROL_PATH = OUTPUT_DIR / "background_high_response_controls.csv"
MATCHED_CONTROL_PATH = OUTPUT_DIR / "supported_matched_background_controls.csv"
FAMILY_PATH = OUTPUT_DIR / "p0_gain_family_comparison.csv"
FAMILY_PAIR_PATH = OUTPUT_DIR / "p0_gain_family_by_frame_pair.csv"
Q95_PATH = OUTPUT_DIR / "q95_relative_percentile_semantic_audit.csv"
SHARED_PATH = OUTPUT_DIR / "shared_unresolved_positive_audit.csv"
DEPENDENCY_PATH = OUTPUT_DIR / "correlated_descriptor_audit.csv"
CASE_PATH = OUTPUT_DIR / "real_case_registry.csv"
SUMMARY_PATH = OUTPUT_DIR / "audit_summary.json"
MANIFEST_PATH = OUTPUT_DIR / "output_manifest.json"
LEDGER_PATH = OUTPUT_DIR / "execution_ledger.json"
REPORT_PATH = OUTPUT_DIR / "M0A_R_ROBUSTNESS_AND_SEMANTIC_AUDIT_REPORT.md"

RUN_ID = "R02ZF"
TIE_TOL = 1e-9
EXPECTED_PROTOCOL_SHA256 = "0A2116AD3FCBF7C77751B365BFE0063C7FD91A6C77AE64346FAE80D52281E025"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True, encoding="utf-8"
    ).strip()


def bool_series(series: pd.Series, name: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        if series.isna().any():
            raise ValueError(f"null boolean in {name}")
        return series.astype(bool)
    normalized = series.astype("string").str.strip().str.lower()
    parsed = normalized.map({"true": True, "false": False, "1": True, "0": False})
    if parsed.isna().any():
        raise ValueError(f"invalid boolean in {name}: {series[parsed.isna()].unique().tolist()}")
    return parsed.astype(bool)


def bool_value(value: Any) -> bool:
    return bool(bool_series(pd.Series([value]), "scalar_boolean").iloc[0])


def finite(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def verify_freeze() -> dict[str, Any]:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(SCRIPT_PATH).lower() or "old_work" in str(OUTPUT_DIR).lower():
        raise RuntimeError("forbidden old_work dependency")
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN_BEFORE_RUN":
        raise RuntimeError("audit protocol is not frozen")
    if git_head() != freeze["starting_head"]:
        raise RuntimeError("HEAD changed after audit protocol freeze")
    if sha256_file(PROTOCOL_PATH) != freeze["protocol_sha256"]:
        raise RuntimeError("audit protocol hash mismatch")
    if sha256_file(M0A_PROTOCOL_PATH) != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError("frozen M0A protocol hash mismatch")
    for section in ("implementation_hashes", "input_hashes"):
        for item in freeze[section]:
            path = WORKSPACE / item["path"]
            if sha256_file(path) != item["sha256"]:
                raise RuntimeError(f"hash mismatch: {path}")
    return freeze


def load_tables() -> dict[str, Any]:
    nodes = pd.read_csv(NODE_PATH)
    matrix = pd.read_csv(MATRIX_PATH, low_memory=False)
    matched = pd.read_csv(MATCHED_PATH)
    supported = pd.read_csv(SUPPORTED_PATH, low_memory=False)
    comparisons = pd.read_csv(COMPARISON_PATH)
    references = pd.read_csv(REFERENCE_REGION_PATH)
    if len(nodes) != 1117 or len(matrix) != 102996 or len(matched) != 257490:
        raise RuntimeError("frozen M0A cardinality mismatch")
    if len(supported) != 12 or supported["base_edge_id"].nunique() != 6:
        raise RuntimeError("frozen supported-edge cardinality mismatch")
    if json.loads(M0A_VALIDATION_PATH.read_text(encoding="utf-8"))["status"] != "PASS":
        raise RuntimeError("frozen M0A validation is not PASS")
    return {
        "nodes": nodes,
        "matrix": matrix,
        "matched": matched,
        "supported": supported,
        "comparisons": comparisons,
        "references": references,
    }


def derive_strata(nodes: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    source_nodes = nodes[nodes["frame_index"].between(472, 493)].copy()
    values = pd.to_numeric(source_nodes["q95_pixel_count"], errors="raise").astype(int)
    quantiles = values.quantile([0.25, 0.50, 0.75], interpolation="linear")
    cuts = {
        "q25_floor_px": int(math.floor(float(quantiles.loc[0.25]))),
        "q50_floor_px": int(math.floor(float(quantiles.loc[0.50]))),
        "q75_floor_px": int(math.floor(float(quantiles.loc[0.75]))),
    }

    def label(pixels: int) -> str:
        if pixels <= cuts["q25_floor_px"]:
            return "TINY_Q1"
        if pixels <= cuts["q50_floor_px"]:
            return "SMALL_Q2"
        if pixels <= cuts["q75_floor_px"]:
            return "MEDIUM_Q3"
        return "LARGE_Q4"

    source_nodes["support_size_stratum"] = values.map(label)
    order = ["TINY_Q1", "SMALL_Q2", "MEDIUM_Q3", "LARGE_Q4"]
    rows = []
    for stratum in order:
        group = source_nodes[source_nodes["support_size_stratum"].eq(stratum)]
        rows.append(
            {
                "stratum": stratum,
                "source_region_count": int(len(group)),
                "pixel_count_min": int(group["q95_pixel_count"].min()),
                "pixel_count_max": int(group["q95_pixel_count"].max()),
                "derivation": "FLOOR_OF_LINEAR_Q25_Q50_Q75_FROM_ALL_1064_PRE_REFERENCE_SOURCE_REGIONS",
                **cuts,
                "contains_1px": bool((group["q95_pixel_count"] == 1).any()),
                "contains_6px": bool((group["q95_pixel_count"] == 6).any()),
                "contains_19px": bool((group["q95_pixel_count"] == 19).any()),
            }
        )
    return pd.DataFrame(rows), cuts


def add_node_metadata(paired: pd.DataFrame, nodes: pd.DataFrame, cuts: dict[str, int]) -> pd.DataFrame:
    def stratum(pixels: Any) -> str:
        value = int(float(pixels))
        if value <= cuts["q25_floor_px"]:
            return "TINY_Q1"
        if value <= cuts["q50_floor_px"]:
            return "SMALL_Q2"
        if value <= cuts["q75_floor_px"]:
            return "MEDIUM_Q3"
        return "LARGE_Q4"

    fields = [
        "frame_uid",
        "region_id",
        "q95_pixel_count",
        "area_m2",
        "touches_observable_boundary",
        "has_truncated_support",
        "region_degree_shell_count",
        "region_degree_bin",
        "component_shell_count",
        "component_shell_count_bin",
        "component_region_count",
        "static_topology_state",
        "structure_state",
    ]
    source = nodes[fields].rename(columns={column: f"source_node_{column}" for column in fields})
    destination = nodes[fields].rename(columns={column: f"destination_node_{column}" for column in fields})
    paired = paired.merge(
        source,
        left_on=["from_frame_uid", "source_region_id"],
        right_on=["source_node_frame_uid", "source_node_region_id"],
        how="left",
        validate="many_to_one",
    ).merge(
        destination,
        left_on=["to_frame_uid", "destination_region_id"],
        right_on=["destination_node_frame_uid", "destination_node_region_id"],
        how="left",
        validate="many_to_one",
    )
    if paired[["source_node_q95_pixel_count", "destination_node_q95_pixel_count"]].isna().any().any():
        raise RuntimeError("node metadata join failed")
    paired["support_size_stratum"] = paired["source_node_q95_pixel_count"].map(stratum)
    return paired


def build_paired_matrix(matrix: pd.DataFrame, nodes: pd.DataFrame, cuts: dict[str, int]) -> pd.DataFrame:
    p0 = matrix[matrix["condition"].eq("P0")].copy()
    zero = matrix[matrix["condition"].eq("ZERO")][
        [
            "base_edge_id",
            "q95_source_total_retention",
            "q95_conditional_valid_retention",
            "q95_destination_explained_fraction",
            "q95_soft_iou",
        ]
    ].rename(
        columns={
            "q95_source_total_retention": "zero_q95_source_total_retention",
            "q95_conditional_valid_retention": "zero_q95_conditional_valid_retention",
            "q95_destination_explained_fraction": "zero_q95_destination_explained_fraction",
            "q95_soft_iou": "zero_q95_soft_iou",
        }
    )
    paired = p0.merge(zero, on="base_edge_id", how="inner", validate="one_to_one")
    paired["delta_p0_source_total_retention"] = (
        paired["q95_source_total_retention"] - paired["zero_q95_source_total_retention"]
    )
    paired["p0_destination_rank"] = (
        paired.sort_values(
            ["pair_index", "source_region_id", "q95_source_total_retention", "destination_region_id"],
            ascending=[True, True, False, True],
        )
        .groupby(["pair_index", "source_region_id"], sort=False)
        .cumcount()
        .add(1)
        .sort_index()
        .astype(int)
    )
    pool = paired.groupby(["pair_index", "source_region_id"])["destination_region_id"].transform("count")
    paired["p0_destination_pool_count"] = pool.astype(int)
    paired["p0_destination_rank_percentile"] = np.where(
        pool <= 1, 1.0, 1.0 - (paired["p0_destination_rank"] - 1) / (pool - 1)
    )
    return add_node_metadata(paired, nodes, cuts)


def reference_region_keys(references: pd.DataFrame) -> set[tuple[str, str]]:
    near = bool_series(references["region_near_reference_0p30m"], "region_near_reference_0p30m")
    frame = references[
        references["run_id"].eq(RUN_ID)
        & references["percentile_tag"].eq("Q095")
        & near
        & references["nearest_region_id"].notna()
        & pd.to_numeric(references["frame_index"], errors="raise").between(472, 494)
    ]
    return {(str(row.frame_uid), str(row.nearest_region_id)) for row in frame.itertuples(index=False)}


def structural_control_cost(frame: pd.DataFrame) -> pd.Series:
    source_area = np.maximum(pd.to_numeric(frame["source_area_m2"], errors="raise"), 1e-12)
    destination_area = np.maximum(pd.to_numeric(frame["destination_area_m2"], errors="raise"), 1e-12)
    return (
        4.0
        * (
            frame["source_node_touches_observable_boundary"].map(bool_value)
            != frame["destination_node_touches_observable_boundary"].map(bool_value)
        ).astype(float)
        + 4.0
        * (
            frame["source_node_has_truncated_support"].map(bool_value)
            != frame["destination_node_has_truncated_support"].map(bool_value)
        ).astype(float)
        + (
            frame["source_node_region_degree_bin"].astype(int)
            - frame["destination_node_region_degree_bin"].astype(int)
        ).abs()
        + (
            frame["source_node_component_shell_count_bin"].astype(int)
            - frame["destination_node_component_shell_count_bin"].astype(int)
        ).abs()
        + np.abs(np.log(destination_area / source_area))
        + frame["theta_midpoint_change_deg"].abs() / 5.0
        + frame["range_midpoint_change_m"].abs()
    )


def build_background_controls(
    paired: pd.DataFrame,
    supported: pd.DataFrame,
    reference_keys: set[tuple[str, str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pool = paired.copy()
    pool["pre_reference_structural_control_cost"] = structural_control_cost(pool)
    controls = (
        pool.sort_values(
            ["pair_index", "source_region_id", "pre_reference_structural_control_cost", "destination_region_id"]
        )
        .groupby(["pair_index", "source_region_id"], sort=False)
        .head(1)
        .copy()
    )
    controls["source_is_reference_mapped"] = [
        (str(a), str(b)) in reference_keys
        for a, b in zip(controls["from_frame_uid"], controls["source_region_id"])
    ]
    controls["destination_is_reference_mapped"] = [
        (str(a), str(b)) in reference_keys
        for a, b in zip(controls["to_frame_uid"], controls["destination_region_id"])
    ]
    controls["reference_free_endpoint_pair"] = ~(
        controls["source_is_reference_mapped"] | controls["destination_is_reference_mapped"]
    )
    controls["selection_semantics"] = (
        "ONE_EDGE_PER_SOURCE_MIN_PRE_REFERENCE_STRUCTURAL_CHANGE_COST_NO_TRANSPORT_METRIC"
    )
    background = controls[controls["reference_free_endpoint_pair"]].copy()

    supported_p0 = supported[supported["condition"].eq("P0")].copy()
    supported_full = supported_p0.merge(
        paired,
        on="base_edge_id",
        how="left",
        validate="one_to_one",
        suffixes=("_supported", ""),
    )
    matched_rows: list[dict[str, Any]] = []
    for support in supported_full.itertuples(index=False):
        candidates = background[
            background["pair_index"].eq(int(support.pair_index))
            & background["support_size_stratum"].eq(str(support.support_size_stratum))
        ].copy()
        candidates = candidates[~candidates["base_edge_id"].eq(str(support.base_edge_id))]
        if candidates.empty:
            continue
        cost = (
            np.abs(
                np.log(
                    np.maximum(candidates["source_support_total"].astype(float), 1.0)
                    / max(float(support.source_support_total), 1.0)
                )
            )
            + np.abs(
                np.log(
                    np.maximum(candidates["destination_area_m2"].astype(float), 1e-12)
                    / max(float(support.destination_area_m2), 1e-12)
                )
            )
            + np.abs(candidates["theta_midpoint_change_deg"] - float(support.theta_midpoint_change_deg)) / 5.0
            + np.abs(candidates["range_midpoint_change_m"] - float(support.range_midpoint_change_m))
            + 4.0
            * (
                candidates["source_node_touches_observable_boundary"].map(bool_value)
                != bool_value(support.source_node_touches_observable_boundary)
            ).astype(float)
            + 4.0
            * (
                candidates["destination_node_touches_observable_boundary"].map(bool_value)
                != bool_value(support.destination_node_touches_observable_boundary)
            ).astype(float)
            + (
                candidates["source_node_region_degree_bin"].astype(int)
                - int(support.source_node_region_degree_bin)
            ).abs()
            + (
                candidates["destination_node_region_degree_bin"].astype(int)
                - int(support.destination_node_region_degree_bin)
            ).abs()
        )
        candidates["supported_match_cost"] = cost
        selected = candidates.sort_values(["supported_match_cost", "base_edge_id"]).head(5)
        for rank, row in enumerate(selected.to_dict("records"), start=1):
            matched_rows.append(
                {
                    "supported_base_edge_id": str(support.base_edge_id),
                    "supported_target_ids": str(support.supported_target_ids),
                    "supported_from_frame": int(support.from_frame),
                    "supported_to_frame": int(support.to_frame),
                    "control_rank": rank,
                    "supported_match_cost": float(row["supported_match_cost"]),
                    **row,
                }
            )
    return controls, pd.DataFrame(matched_rows)


def describe_family(name: str, frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "evidence_family": name,
        "row_count": int(len(frame)),
        "frame_pair_cluster_count": int(frame[["from_frame", "to_frame"]].drop_duplicates().shape[0]),
        "source_region_cluster_count": int(frame["source_region_id"].nunique()),
        "base_edge_cluster_count": int(frame["base_edge_id"].nunique()),
        "p0_retention_median": finite(frame["q95_source_total_retention"].median()),
        "zero_retention_median": finite(frame["zero_q95_source_total_retention"].median()),
        "delta_p0_median": finite(frame["delta_p0_source_total_retention"].median()),
        "delta_p0_mean": finite(frame["delta_p0_source_total_retention"].mean()),
        "p0_better_fraction": finite((frame["delta_p0_source_total_retention"] > TIE_TOL).mean()),
        "p0_rank_percentile_median": finite(frame["p0_destination_rank_percentile"].median()),
        "interpretation": "DESCRIPTIVE_EVIDENCE_NOT_INDEPENDENT_ROW_LEVEL_INFERENCE",
    }


def cluster_and_family_tables(
    paired: pd.DataFrame,
    supported: pd.DataFrame,
    comparisons: pd.DataFrame,
    controls: pd.DataFrame,
    matched_controls: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    supported_ids = supported[supported["condition"].eq("P0")]["base_edge_id"].astype(str)
    supported_frame = paired[paired["base_edge_id"].isin(supported_ids)].copy()
    supported_meta = supported[supported["condition"].eq("P0")][
        ["base_edge_id", "supported_target_ids", "supported_target_count", "shared_or_unresolved"]
    ]
    supported_frame = supported_frame.merge(supported_meta, on="base_edge_id", validate="one_to_one")

    alt_ids = comparisons[
        comparisons["condition"].eq("P0")
        & comparisons["alternative_reference_state"].eq("REFERENCE_UNSUPPORTED")
    ]["alternative_base_edge_id"].astype(str)
    alternatives = paired[paired["base_edge_id"].isin(alt_ids)].copy()
    background = controls[controls["reference_free_endpoint_pair"]].copy()

    family_frames = {
        "REFERENCE_SUPPORTED_EDGES": supported_frame,
        "REFERENCE_UNSUPPORTED_MATCHED_ALTERNATIVES": alternatives,
        "REFERENCE_FREE_STRUCTURAL_HIGH_RESPONSE_CONTROLS": background,
        "SUPPORTED_MATCHED_REFERENCE_FREE_CONTROLS": matched_controls,
    }
    family = pd.DataFrame([describe_family(name, frame) for name, frame in family_frames.items()])
    pair_rows = []
    for name, frame in family_frames.items():
        for (from_frame, to_frame), group in frame.groupby(["from_frame", "to_frame"], sort=True):
            row = describe_family(name, group)
            row.update({"from_frame": int(from_frame), "to_frame": int(to_frame)})
            pair_rows.append(row)
    family_pair = pd.DataFrame(pair_rows)

    cluster_rows = []
    for (from_frame, to_frame), group in supported_frame.groupby(["from_frame", "to_frame"], sort=True):
        cluster_rows.append(
            {
                "cluster_level": "FRAME_PAIR",
                "cluster_id": f"F{int(from_frame)}_TO_F{int(to_frame)}",
                "from_frame": int(from_frame),
                "to_frame": int(to_frame),
                "supported_edge_count": int(len(group)),
                "unique_source_region_count": int(group["source_region_id"].nunique()),
                "unique_base_edge_count": int(group["base_edge_id"].nunique()),
                "target_group_count": int(group["supported_target_ids"].nunique()),
                "p0_retention_median": float(group["q95_source_total_retention"].median()),
                "zero_retention_median": float(group["zero_q95_source_total_retention"].median()),
                "delta_p0_median": float(group["delta_p0_source_total_retention"].median()),
                "p0_better_fraction": float((group["delta_p0_source_total_retention"] > TIE_TOL).mean()),
                "all_shared_or_unresolved": bool(group["shared_or_unresolved"].map(bool_value).all()),
            }
        )
    for row in supported_frame.itertuples(index=False):
        cluster_rows.append(
            {
                "cluster_level": "SUPPORTED_BASE_EDGE",
                "cluster_id": str(row.base_edge_id),
                "from_frame": int(row.from_frame),
                "to_frame": int(row.to_frame),
                "supported_edge_count": 1,
                "unique_source_region_count": 1,
                "unique_base_edge_count": 1,
                "target_group_count": 1,
                "p0_retention_median": float(row.q95_source_total_retention),
                "zero_retention_median": float(row.zero_q95_source_total_retention),
                "delta_p0_median": float(row.delta_p0_source_total_retention),
                "p0_better_fraction": float(row.delta_p0_source_total_retention > TIE_TOL),
                "all_shared_or_unresolved": bool_value(row.shared_or_unresolved),
            }
        )
    cluster = pd.DataFrame(cluster_rows)

    cmp = comparisons[
        comparisons["alternative_reference_state"].eq("REFERENCE_UNSUPPORTED")
    ].copy()
    matched_rows = []
    for (condition, primary), group in cmp.groupby(["condition", "primary_base_edge_id"], sort=True):
        matched_rows.append(
            {
                "condition": condition,
                "primary_base_edge_id": primary,
                "comparison_row_count": int(len(group)),
                "supported_win_fraction": float(group["pairwise_outcome"].eq("SUPPORTED_WIN").mean()),
                "tie_fraction": float(group["pairwise_outcome"].eq("TIE").mean()),
                "alternative_win_fraction": float(group["pairwise_outcome"].eq("ALTERNATIVE_WIN").mean()),
                "supported_minus_alternative_median": float(group["supported_minus_alternative"].median()),
                "raw_rows_are_not_independent": True,
            }
        )
    matched_cluster = pd.DataFrame(matched_rows)

    supported_pairs = sorted(
        supported_frame[["from_frame", "to_frame"]].drop_duplicates().itertuples(index=False, name=None)
    )
    loo_rows = []
    drop_sets: list[tuple[int | None, int | None]] = [(None, None)] + supported_pairs
    for drop_from, drop_to in drop_sets:
        keep = supported_frame.copy()
        cmp_keep = cmp[cmp["condition"].eq("P0")].copy()
        control_keep = matched_controls.copy()
        if drop_from is not None:
            keep = keep[~(keep["from_frame"].eq(drop_from) & keep["to_frame"].eq(drop_to))]
            removed_ids = supported_frame[
                supported_frame["from_frame"].eq(drop_from)
                & supported_frame["to_frame"].eq(drop_to)
            ]["base_edge_id"]
            cmp_keep = cmp_keep[~cmp_keep["primary_base_edge_id"].isin(removed_ids)]
            control_keep = control_keep[
                ~(control_keep["supported_from_frame"].eq(drop_from) & control_keep["supported_to_frame"].eq(drop_to))
            ]
        per_edge_win = cmp_keep.groupby("primary_base_edge_id")["pairwise_outcome"].apply(
            lambda values: float(values.eq("SUPPORTED_WIN").mean())
        )
        loo_rows.append(
            {
                "analysis": "FULL" if drop_from is None else "LEAVE_ONE_FRAME_PAIR_OUT",
                "dropped_frame_pair": "NONE" if drop_from is None else f"F{drop_from}_TO_F{drop_to}",
                "remaining_frame_pair_clusters": int(keep[["from_frame", "to_frame"]].drop_duplicates().shape[0]),
                "remaining_supported_edges": int(len(keep)),
                "p0_retention_median": finite(keep["q95_source_total_retention"].median()),
                "zero_retention_median": finite(keep["zero_q95_source_total_retention"].median()),
                "delta_p0_median": finite(keep["delta_p0_source_total_retention"].median()),
                "p0_better_fraction": finite((keep["delta_p0_source_total_retention"] > TIE_TOL).mean()),
                "matched_raw_comparison_count": int(len(cmp_keep)),
                "matched_raw_supported_win_fraction": finite(cmp_keep["pairwise_outcome"].eq("SUPPORTED_WIN").mean()),
                "matched_supported_edge_cluster_count": int(len(per_edge_win)),
                "matched_per_edge_win_fraction_median": finite(per_edge_win.median()),
                "matched_background_control_delta_median": finite(control_keep["delta_p0_source_total_retention"].median()),
                "inference": "DESCRIPTIVE_INSUFFICIENT_INDEPENDENT_FRAME_PAIR_CLUSTERS",
            }
        )
    return supported_frame, family, family_pair, cluster, matched_cluster, pd.DataFrame(loo_rows)


def build_shared_audit(supported_frame: pd.DataFrame) -> pd.DataFrame:
    fields = [
        "from_frame",
        "to_frame",
        "base_edge_id",
        "source_region_id",
        "destination_region_id",
        "supported_target_ids",
        "supported_target_count",
        "shared_or_unresolved",
        "source_node_region_degree_shell_count",
        "destination_node_region_degree_shell_count",
        "source_node_component_shell_count",
        "destination_node_component_shell_count",
        "source_node_component_region_count",
        "destination_node_component_region_count",
        "source_node_static_topology_state",
        "destination_node_static_topology_state",
        "q95_source_total_retention",
        "zero_q95_source_total_retention",
        "delta_p0_source_total_retention",
    ]
    output = supported_frame[fields].copy()
    output["positive_semantics"] = "REFERENCE_SUPPORTED_DYNAMIC_EXPLANATION"
    output["person_exclusive_positive"] = False
    output["person_region_continuation_claim_allowed"] = False
    return output


def build_q95_semantic_audit(
    nodes: pd.DataFrame,
    paired: pd.DataFrame,
    supported_frame: pd.DataFrame,
    controls: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    counts = nodes.groupby("frame_index").size()
    rows.append(
        {
            "analysis_item": "Q95_REGION_EXISTENCE_PER_FRAME",
            "population": "ALL_23_R02_FRAMES",
            "count": int(len(counts)),
            "median": float(counts.median()),
            "minimum": int(counts.min()),
            "maximum": int(counts.max()),
            "semantic_result": "EXPECTED_BY_FRAME_RELATIVE_PERCENTILE_NOT_PERSON_EVIDENCE",
        }
    )
    p0_best = (
        paired.sort_values(
            ["pair_index", "source_region_id", "q95_source_total_retention", "destination_region_id"],
            ascending=[True, True, False, True],
        )
        .groupby(["pair_index", "source_region_id"], sort=False)
        .head(1)
    )
    populations = {
        "REFERENCE_SUPPORTED": supported_frame,
        "REFERENCE_FREE_STRUCTURAL_CONTROL": controls[controls["reference_free_endpoint_pair"]],
        "PRE_REFERENCE_P0_BEST_DESTINATION_UPPER_BOUND": p0_best,
    }
    for name, frame in populations.items():
        rows.append(
            {
                "analysis_item": "Q95_TEMPORAL_PERSISTENCE",
                "population": name,
                "count": int(len(frame)),
                "median": finite(frame["q95_source_total_retention"].median()),
                "minimum": finite(frame["q95_source_total_retention"].min()),
                "maximum": finite(frame["q95_source_total_retention"].max()),
                "fraction_retention_ge_0p5": finite((frame["q95_source_total_retention"] >= 0.5).mean()),
                "fraction_retention_ge_0p8": finite((frame["q95_source_total_retention"] >= 0.8).mean()),
                "semantic_result": "PERSISTENCE_REQUIRES_MATCHED_CONTROL_REGION_EXISTENCE_ALONE_IS_UNINFORMATIVE",
            }
        )
    return pd.DataFrame(rows)


def build_dependency_audit(paired: pd.DataFrame, supported_frame: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "evidence_family": "SAR_TEMPORAL_TRANSPORT",
            "descriptor_a": "q95_source_total_retention",
            "descriptor_b": "q95_destination_explained_fraction",
            "shared_primitive": "warped_source_intersection_destination",
            "relationship": "SAME_NUMERATOR_DIFFERENT_DENOMINATOR",
            "independent_evidence_claim_allowed": False,
        },
        {
            "evidence_family": "SAR_TEMPORAL_TRANSPORT",
            "descriptor_a": "q95_source_total_retention",
            "descriptor_b": "q95_soft_iou",
            "shared_primitive": "warped_source_intersection_destination",
            "relationship": "SAME_INTERSECTION_IN_NUMERATOR_AND_UNION",
            "independent_evidence_claim_allowed": False,
        },
        {
            "evidence_family": "SAR_RESPONSE_MORPHOLOGY",
            "descriptor_a": "q90_envelope",
            "descriptor_b": "q95_region_and_q97p5_core",
            "shared_primitive": "same_frozen_S_x_percentile_superlevel_family",
            "relationship": "NESTED_RELATIVE_PERCENTILE_LAYERS",
            "independent_evidence_claim_allowed": False,
        },
    ]
    positive = paired[paired["q95_support_intersection_soft"] > 0].copy()
    metrics = [
        "q95_source_total_retention",
        "q95_conditional_valid_retention",
        "q95_destination_explained_fraction",
        "q95_soft_iou",
        "q975_to_q975_core_retention",
        "q90_weak_envelope_retention",
    ]
    for population, frame in (("ALL_POSITIVE_INTERSECTION_P0_EDGES", positive), ("SUPPORTED_P0_EDGES", supported_frame)):
        corr = frame[metrics].corr(method="spearman", min_periods=3)
        for index, first in enumerate(metrics):
            for second in metrics[index + 1 :]:
                rows.append(
                    {
                        "evidence_family": "EMPIRICAL_DESCRIPTOR_DEPENDENCE",
                        "descriptor_a": first,
                        "descriptor_b": second,
                        "shared_primitive": population,
                        "relationship": "SPEARMAN_DESCRIPTION_NOT_INDEPENDENCE_TEST",
                        "spearman_rho": finite(corr.loc[first, second]),
                        "population_row_count": int(len(frame)),
                        "independent_evidence_claim_allowed": False,
                    }
                )
    return pd.DataFrame(rows)


def choose_cases(
    paired: pd.DataFrame,
    supported_frame: pd.DataFrame,
    controls: pd.DataFrame,
) -> pd.DataFrame:
    pre_cases = pd.read_csv(PRE_CASE_PATH)
    post_cases = pd.read_csv(POST_CASE_PATH)
    cases: list[dict[str, Any]] = []

    def add(case_type: str, row: pd.Series, rule: str, related: list[str] | None = None) -> None:
        cases.append(
            {
                "case_type": case_type,
                "selection_rule": rule,
                "base_edge_id": str(row["base_edge_id"]),
                "from_frame": int(row["from_frame"]),
                "to_frame": int(row["to_frame"]),
                "source_region_id": str(row["source_region_id"]),
                "destination_region_id": str(row["destination_region_id"]),
                "related_destination_region_ids_json": json.dumps(related or []),
                "source_support_total": int(float(row["source_support_total"])),
                "support_size_stratum": str(row["support_size_stratum"]),
                "p0_retention": float(row["q95_source_total_retention"]),
                "zero_retention": float(row["zero_q95_source_total_retention"]),
                "delta_p0": float(row["delta_p0_source_total_retention"]),
                "is_reference_supported": bool(row["base_edge_id"] in set(supported_frame["base_edge_id"])),
            }
        )

    boundary_mask = (
        paired["source_node_touches_observable_boundary"].map(bool_value)
        | paired["destination_node_touches_observable_boundary"].map(bool_value)
        | paired["source_node_has_truncated_support"].map(bool_value)
        | paired["destination_node_has_truncated_support"].map(bool_value)
    )
    one = paired[paired["source_support_total"].eq(1) & boundary_mask].sort_values(
        ["q95_source_total_retention", "base_edge_id"], ascending=[False, True]
    ).iloc[0]
    add("ONE_PIXEL_BOUNDARY_CASE", one, "1PX_BOUNDARY_MAX_P0_RETENTION")

    six = paired[paired["source_support_total"].eq(6)].sort_values(
        ["delta_p0_source_total_retention", "base_edge_id"], ascending=[False, True]
    ).iloc[0]
    add("SIX_PIXEL_P0_GAIN_CASE", six, "6PX_MAX_P0_MINUS_ZERO")

    nineteen = paired[paired["source_support_total"].eq(19)].sort_values(
        ["delta_p0_source_total_retention", "base_edge_id"], ascending=[True, True]
    ).iloc[0]
    add("NINETEEN_PIXEL_ZERO_BETTER_CASE", nineteen, "19PX_MIN_P0_MINUS_ZERO")

    for case_type in ("SPLIT_LIKE", "MERGE_LIKE"):
        registry = pre_cases[pre_cases["case_type"].eq(case_type)].iloc[0]
        row = paired[paired["base_edge_id"].eq(registry["base_edge_id"])].iloc[0]
        related = json.loads(registry["related_destination_region_ids_json"])
        add(case_type, row, f"REUSE_FROZEN_M0A_{case_type}_SELECTION", related)

    deceptive_registry = post_cases[
        post_cases["case_type"].isin(
            ["MATCHED_ALTERNATIVE_DECEPTIVELY_STRONG", "NO_DECEPTIVE_ALTERNATIVE_FOUND_STRONGEST_AVAILABLE"]
        )
    ].iloc[0]
    deceptive_row = paired[paired["base_edge_id"].eq(deceptive_registry["base_edge_id"])].iloc[0]
    related = json.loads(deceptive_registry["related_destination_region_ids_json"])
    add("SUPPORTED_VS_DECEPTIVE_MATCHED_ALTERNATIVE", deceptive_row, "REUSE_FROZEN_M0A_POST_REFERENCE_DECEPTIVE_CASE", related)

    high = supported_frame.sort_values(
        ["q95_source_total_retention", "base_edge_id"], ascending=[False, True]
    ).iloc[0]
    low = supported_frame.sort_values(
        ["q95_source_total_retention", "base_edge_id"], ascending=[True, True]
    ).iloc[0]
    add("SUPPORTED_SHARED_HIGH_RETENTION", high, "SUPPORTED_MAX_P0_RETENTION")
    add("SUPPORTED_SHARED_LOW_RETENTION", low, "SUPPORTED_MIN_P0_RETENTION")

    background = controls[controls["reference_free_endpoint_pair"]].copy()
    bg_persistence = background.sort_values(
        ["q95_source_total_retention", "base_edge_id"], ascending=[False, True]
    ).iloc[0]
    bg_gain = background.sort_values(
        ["delta_p0_source_total_retention", "base_edge_id"], ascending=[False, True]
    ).iloc[0]
    add("REFERENCE_FREE_HIGH_PERSISTENCE", bg_persistence, "REFERENCE_FREE_STRUCTURAL_CONTROL_MAX_P0_RETENTION")
    add("REFERENCE_FREE_MAX_P0_GAIN", bg_gain, "REFERENCE_FREE_STRUCTURAL_CONTROL_MAX_P0_MINUS_ZERO")
    return pd.DataFrame(cases)


def find_image(frame_index: int) -> Path:
    paths = sorted(IMAGE_DIR.glob(f"frame_{frame_index:06d}_t*ms.jpg"))
    if len(paths) != 1:
        raise RuntimeError(f"expected one image for frame {frame_index}: {paths}")
    return paths[0]


def load_masks(frame_uid: str) -> dict[str, np.ndarray]:
    with np.load(MASK_DIR / f"{frame_uid}.npz") as archive:
        return {tag: archive[tag].astype(np.int32) for tag in ("Q090", "Q095", "Q0975")}


def warp(mask: np.ndarray, dx: float, dy: float) -> np.ndarray:
    height, width = mask.shape
    matrix = np.asarray([[1.0, 0.0, dx], [0.0, 1.0, dy]], np.float32)
    return np.clip(
        cv2.warpAffine(
            mask.astype(np.float32),
            matrix,
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0.0,
        ),
        0.0,
        1.0,
    )


def draw_contour(axis: plt.Axes, mask: np.ndarray, color: str, linewidth: float) -> None:
    if np.any(mask):
        axis.contour(mask.astype(float), levels=[0.5], colors=[color], linewidths=[linewidth])


def crop_bounds(masks: list[np.ndarray], width: int, height: int, margin: int = 70) -> tuple[int, int, int, int]:
    union = np.zeros((height, width), bool)
    for mask in masks:
        union |= np.asarray(mask) > 0
    yy, xx = np.where(union)
    if not len(xx):
        return 0, width, 0, height
    x0, x1 = max(0, int(xx.min()) - margin), min(width, int(xx.max()) + margin + 1)
    y0, y1 = max(0, int(yy.min()) - margin), min(height, int(yy.max()) + margin + 1)
    return x0, x1, y0, y1


def render_cases(cases: pd.DataFrame, paired: pd.DataFrame, nodes: pd.DataFrame) -> list[Path]:
    centers = pd.read_csv(
        REFERENCE_CENTER_PATH,
        usecols=["run_id", "frame_uid", "target_id", "reference_x_px", "reference_y_px"],
    )
    centers = centers[centers["run_id"].eq(RUN_ID)].drop_duplicates(["frame_uid", "target_id"])
    node_labels = nodes.set_index(["frame_uid", "region_id"])["region_label"].astype(int)
    outputs = []
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for index, case in cases.iterrows():
        row = paired[paired["base_edge_id"].eq(case["base_edge_id"])].iloc[0]
        source_masks = load_masks(str(row["from_frame_uid"]))
        destination_masks = load_masks(str(row["to_frame_uid"]))
        source_label = int(node_labels.loc[(str(row["from_frame_uid"]), str(row["source_region_id"]))])
        destination_label = int(
            node_labels.loc[(str(row["to_frame_uid"]), str(row["destination_region_id"]))]
        )
        source_q95 = source_masks["Q095"] == source_label
        destination_q95 = destination_masks["Q095"] == destination_label
        source_q975 = source_q95 & (source_masks["Q0975"] > 0)
        source_q90_labels = [int(v) for v in np.unique(source_masks["Q090"][source_q95]) if int(v) > 0]
        source_q90 = np.isin(source_masks["Q090"], source_q90_labels)
        related_source_masks = []
        related_destination_masks = []
        for region_id in json.loads(case["related_destination_region_ids_json"]):
            if str(case["case_type"]) == "MERGE_LIKE":
                label = int(node_labels.loc[(str(row["from_frame_uid"]), str(region_id))])
                related_source_masks.append(source_masks["Q095"] == label)
            else:
                label = int(node_labels.loc[(str(row["to_frame_uid"]), str(region_id))])
                related_destination_masks.append(destination_masks["Q095"] == label)
        p0_warp = warp(source_q95, float(row["p0_dx_px"]), float(row["p0_dy_px"]))
        zero_warp = source_q95.astype(np.float32)
        source_image = cv2.cvtColor(cv2.imread(str(find_image(int(row["from_frame"])))), cv2.COLOR_BGR2RGB)
        destination_image = cv2.cvtColor(
            cv2.imread(str(find_image(int(row["to_frame"])))), cv2.COLOR_BGR2RGB
        )
        height, width = source_q95.shape
        x0, x1, y0, y1 = crop_bounds(
            [
                source_q90,
                source_q95,
                destination_q95,
                p0_warp,
                *related_source_masks,
                *related_destination_masks,
            ],
            width,
            height,
        )
        fig, axes = plt.subplots(2, 3, figsize=(16.5, 9.5), constrained_layout=True)
        for axis in axes.ravel():
            axis.set_xlim(x0, x1)
            axis.set_ylim(y1, y0)
            axis.set_xticks([])
            axis.set_yticks([])
        axes[0, 0].imshow(source_image)
        draw_contour(axes[0, 0], source_q90, "#39d98a", 1.0)
        draw_contour(axes[0, 0], source_q95, "#ffd43b", 2.0)
        draw_contour(axes[0, 0], source_q975, "#ff6b6b", 1.2)
        for related in related_source_masks:
            draw_contour(axes[0, 0], related, "#00d5ff", 1.5)
        axes[0, 0].set_title(f"Source F{int(row['from_frame'])}: q90/q95/q97.5")
        axes[0, 1].imshow(destination_image)
        draw_contour(axes[0, 1], destination_masks["Q095"] > 0, "#777777", 0.35)
        draw_contour(axes[0, 1], destination_q95, "#ff3b30", 2.0)
        for related in related_destination_masks:
            draw_contour(axes[0, 1], related, "#00d5ff", 1.5)
        axes[0, 1].set_title(f"Destination F{int(row['to_frame'])}: q95 regions")
        axes[0, 2].imshow(destination_image)
        axes[0, 2].imshow(np.ma.masked_less_equal(p0_warp, 0), cmap="magma", alpha=0.72, vmin=0, vmax=1)
        draw_contour(axes[0, 2], destination_q95, "#00ffff", 1.6)
        axes[0, 2].set_title("Frozen P0 soft occupancy")
        axes[1, 0].imshow(destination_image)
        draw_contour(axes[1, 0], p0_warp >= 0.5, "#ffd43b", 1.6)
        draw_contour(axes[1, 0], destination_q95, "#ff3b30", 2.0)
        axes[1, 0].set_title(f"P0 retention={row['q95_source_total_retention']:.4f}")
        axes[1, 1].imshow(destination_image)
        draw_contour(axes[1, 1], zero_warp >= 0.5, "#8ec5ff", 1.6)
        draw_contour(axes[1, 1], destination_q95, "#ff3b30", 2.0)
        axes[1, 1].set_title(f"ZERO retention={row['zero_q95_source_total_retention']:.4f}")
        if bool(case["is_reference_supported"]):
            for axis, frame_uid in ((axes[0, 0], row["from_frame_uid"]), (axes[0, 1], row["to_frame_uid"]), (axes[0, 2], row["to_frame_uid"]), (axes[1, 0], row["to_frame_uid"]), (axes[1, 1], row["to_frame_uid"])):
                for center in centers[centers["frame_uid"].eq(frame_uid)].itertuples(index=False):
                    axis.scatter(center.reference_x_px, center.reference_y_px, marker="*", s=75, c="#ff2bd6", edgecolors="white", linewidths=0.6)
        axes[1, 2].axis("off")
        text = "\n".join(
            [
                f"Case: {case['case_type']}",
                f"Rule: {case['selection_rule']}",
                f"Size: {int(case['source_support_total'])} px ({case['support_size_stratum']})",
                f"P0 - ZERO: {case['delta_p0']:+.4f}",
                f"P0 rank percentile: {row['p0_destination_rank_percentile']:.4f}",
                f"q95 explained fraction: {row['q95_destination_explained_fraction']:.4f}",
                f"q95 soft IoU: {row['q95_soft_iou']:.4f}",
                f"q97.5 core retention: {row['q975_to_q975_core_retention']:.4f}" if pd.notna(row["q975_to_q975_core_retention"]) else "q97.5 core retention: unavailable",
                f"q90 envelope retention: {row['q90_weak_envelope_retention']:.4f}",
                "Magenta reference stars: post-reference supported cases only.",
            ]
        )
        axes[1, 2].text(0, 1, text, va="top", family="monospace", fontsize=9.5)
        fig.suptitle("M0A-R deterministic real-case audit", fontsize=15, weight="bold")
        path = FIGURE_DIR / f"{index + 1:02d}_{str(case['case_type']).lower()}.png"
        fig.savefig(path, dpi=135)
        plt.close(fig)
        outputs.append(path)
    return outputs


def support_size_sensitivity(
    strata: pd.DataFrame,
    supported_frame: pd.DataFrame,
    controls: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    background = controls[controls["reference_free_endpoint_pair"]]
    for stratum in strata["stratum"]:
        supported_group = supported_frame[supported_frame["support_size_stratum"].eq(stratum)]
        control_group = background[background["support_size_stratum"].eq(stratum)]
        rows.append(
            {
                "stratum": stratum,
                "all_pre_reference_source_region_count": int(
                    strata.loc[strata["stratum"].eq(stratum), "source_region_count"].iloc[0]
                ),
                "supported_edge_count": int(len(supported_group)),
                "supported_p0_retention_median": finite(supported_group["q95_source_total_retention"].median()),
                "supported_delta_p0_median": finite(supported_group["delta_p0_source_total_retention"].median()),
                "reference_free_structural_control_count": int(len(control_group)),
                "control_p0_retention_median": finite(control_group["q95_source_total_retention"].median()),
                "control_zero_retention_median": finite(control_group["zero_q95_source_total_retention"].median()),
                "control_delta_p0_median": finite(control_group["delta_p0_source_total_retention"].median()),
                "tiny_cases_deleted": False,
            }
        )
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame) -> str:
    """Render a small deterministic Markdown table without optional tabulate."""
    display = frame.copy()
    for column in display.columns:
        display[column] = display[column].map(
            lambda value: ""
            if pd.isna(value)
            else f"{value:.4f}"
            if isinstance(value, (float, np.floating))
            else str(value)
        )
    headers = [str(column).replace("|", "\\|") for column in display.columns]
    rows = [
        [str(value).replace("|", "\\|") for value in record]
        for record in display.itertuples(index=False, name=None)
    ]
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
            *("| " + " | ".join(row) + " |" for row in rows),
        ]
    )


def make_report(summary: dict[str, Any], paths: dict[str, Path], figures: list[Path]) -> None:
    family = pd.read_csv(FAMILY_PATH)
    loo = pd.read_csv(LOO_PATH)
    size = pd.read_csv(paths["support_size_sensitivity"])
    shared = pd.read_csv(SHARED_PATH)
    supported_row = family[family["evidence_family"].eq("REFERENCE_SUPPORTED_EDGES")].iloc[0]
    bg_row = family[
        family["evidence_family"].eq("SUPPORTED_MATCHED_REFERENCE_FREE_CONTROLS")
    ].iloc[0]
    lines = [
        "# M0A-R robustness and semantic audit report",
        "",
        f"- Audit state: `{summary['final_audit_state']}`",
        f"- Frozen M0A state retained unchanged: `{summary['frozen_m0a_state']}`",
        f"- Starting HEAD: `{summary['starting_head']}`",
        "- Scientific status: descriptive evidence; insufficient independent frame-pair clusters for confirmatory inference.",
        "",
        "## Conclusion",
        "",
        "The frozen M0A result remains a valid description of short-term q95 SAR image-domain support transport in the exposed R02 slice. The audit does not find a basis to promote it to PERSON-specific continuation. Only three frame-pair clusters contribute supported edges, all six base edges are shared by two manual target references, and strong q95 persistence also occurs in deterministic reference-free high-response controls. P0 remains a useful common registration mechanism; its gain is not a PERSON identity mechanism.",
        "",
        "## Cluster dependence",
        "",
        f"- Effective frame-pair clusters: `{summary['effective_clusters']['frame_pair']}`.",
        f"- Supported source-region clusters: `{summary['effective_clusters']['source_region']}`.",
        f"- Supported base-edge clusters: `{summary['effective_clusters']['base_edge']}`.",
        f"- Repeated shared target/reference groups: `{summary['effective_clusters']['target_group']}`.",
        "- The historical `29/30` matched result is retained as 30 clustered comparisons, not 30 independent observations.",
        "- Leave-one-frame-pair-out results are in `leave_one_frame_pair_out.csv`; no p-value is manufactured from three clusters.",
        "",
        "## Support-size sensitivity",
        "",
        "GT-blind cutpoints were derived from all 1,064 pre-reference source regions: `<=70`, `71-209`, `210-587`, `>=588` pixels. The 1/6/19-pixel cases remain in the audit and figures. All six reference-supported edges are in `LARGE_Q4`, so the nominal supported P0 gain is not driven by tiny source regions. Tiny cases are still unstable and are retained as observability/boundary evidence rather than deleted.",
        "",
        markdown_table(size),
        "",
        "## P0 gain families",
        "",
        f"Supported median P0/ZERO/delta: `{supported_row.p0_retention_median:.4f} / {supported_row.zero_retention_median:.4f} / {supported_row.delta_p0_median:+.4f}`.",
        f"Size/topology-matched reference-free controls median P0/ZERO/delta: `{bg_row.p0_retention_median:.4f} / {bg_row.zero_retention_median:.4f} / {bg_row.delta_p0_median:+.4f}`.",
        "The comparison is descriptive and cluster-aware. A positive background-control delta supports general image registration, not PERSON specificity.",
        "",
        markdown_table(family),
        "",
        "## q95 relative-percentile semantics",
        "",
        "q95 is a frame-relative superlevel set, so every frame contains q95 regions by construction. Region existence is therefore not PERSON-presence evidence. The audit compares supported continuity with deterministic non-reference high-response controls and a P0-best-destination upper bound; these controls show that high temporal persistence is a general image-domain property in this scene slice.",
        "",
        "## Shared/unresolved positives",
        "",
        f"All `{len(shared)}` supported base edges have `supported_target_count=2` and remain `REFERENCE_SUPPORTED_DYNAMIC_EXPLANATION`. PERSON-exclusive positives: `0`. Source/destination local degree and full component topology are retained separately in `{SHARED_PATH.name}`.",
        "",
        "## Correlated descriptors and evidence families",
        "",
        "`retention`, `destination_explained_fraction`, and `soft_iou` reuse the same warped-source/destination intersection and are not independent evidence. q90/q95/q97.5 are nested superlevel layers of the same frozen `S(x)`. They remain useful morphology descriptors but must not be double-counted as separate physical factors.",
        "",
        "Independent evidence-family organization for future work:",
        "",
        "1. SAR response morphology",
        "2. SAR temporal transport",
        "3. shell-region topology",
        "4. optical angular dynamics",
        "5. timing/phase consistency",
        "6. observability/boundary/availability",
        "",
        "Only the first three and the last are present in M0A-R. Optical angular dynamics and timing/phase consistency are not executed here.",
        "",
        "## Ten deterministic real cases",
        "",
    ]
    for path in figures:
        lines.append(f"- `{path.name}`")
    lines += [
        "",
        "## State and scope",
        "",
        f"The evidence-faithful audit state is `{summary['final_audit_state']}`. It does not overwrite `{summary['frozen_m0a_state']}`; it qualifies its interpretation. M0A still means short-term q95 support continuity plus limited P0 gain in the frozen R02 slice. It does not establish Optical-SAR motion consistency, PERSON-specific region continuation, identity, ambiguity reduction, runtime optical identity, or final SAR localization.",
        "",
        "## Recommendation for M0B",
        "",
        "Proceed only with a minimal development diagnostic that asks whether raw-fragment optical angular dynamics adds incremental discrimination beyond the frozen SAR-only evidence. Do not execute M0B as part of this task, do not fit timing offsets, and do not construct a tracker or unique path.",
        "",
        "## Authoritative audit artifacts",
        "",
    ]
    for label, path in paths.items():
        lines.append(f"- {label}: `{path.name}`")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", required=True)
    parser.parse_args()
    freeze = verify_freeze()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started = now_iso()
    tables = load_tables()
    strata, cuts = derive_strata(tables["nodes"])
    paired = build_paired_matrix(tables["matrix"], tables["nodes"], cuts)
    ref_keys = reference_region_keys(tables["references"])
    controls, matched_controls = build_background_controls(
        paired, tables["supported"], ref_keys
    )
    (
        supported_frame,
        family,
        family_pair,
        cluster,
        matched_cluster,
        loo,
    ) = cluster_and_family_tables(
        paired,
        tables["supported"],
        tables["comparisons"],
        controls,
        matched_controls,
    )
    shared = build_shared_audit(supported_frame)
    q95 = build_q95_semantic_audit(tables["nodes"], paired, supported_frame, controls)
    dependency = build_dependency_audit(paired, supported_frame)
    size_sensitivity = support_size_sensitivity(strata, supported_frame, controls)
    cases = choose_cases(paired, supported_frame, controls)

    strata.to_csv(STRATA_PATH, index=False, encoding="utf-8-sig")
    supported_frame.to_csv(SUPPORTED_AUDIT_PATH, index=False, encoding="utf-8-sig")
    cluster.to_csv(CLUSTER_PATH, index=False, encoding="utf-8-sig")
    loo.to_csv(LOO_PATH, index=False, encoding="utf-8-sig")
    matched_cluster.to_csv(MATCHED_CLUSTER_PATH, index=False, encoding="utf-8-sig")
    controls.to_csv(CONTROL_PATH, index=False, encoding="utf-8-sig")
    matched_controls.to_csv(MATCHED_CONTROL_PATH, index=False, encoding="utf-8-sig")
    family.to_csv(FAMILY_PATH, index=False, encoding="utf-8-sig")
    family_pair.to_csv(FAMILY_PAIR_PATH, index=False, encoding="utf-8-sig")
    q95.to_csv(Q95_PATH, index=False, encoding="utf-8-sig")
    shared.to_csv(SHARED_PATH, index=False, encoding="utf-8-sig")
    dependency.to_csv(DEPENDENCY_PATH, index=False, encoding="utf-8-sig")
    cases.to_csv(CASE_PATH, index=False, encoding="utf-8-sig")
    size_path = OUTPUT_DIR / "support_size_sensitivity.csv"
    size_sensitivity.to_csv(size_path, index=False, encoding="utf-8-sig")
    figures = render_cases(cases, paired, tables["nodes"])

    full_loo = loo[loo["analysis"].eq("FULL")].iloc[0]
    loo_stable = bool(
        (loo["p0_retention_median"] > 0.5).all()
        and (loo["delta_p0_median"] > 0).all()
    )
    all_shared = bool(shared["shared_or_unresolved"].map(bool_value).all())
    final_state = (
        "M0A_R_TRANSPORT_VALID_BUT_PERSON_SPECIFICITY_NOT_ESTABLISHED"
        if loo_stable and all_shared
        else "M0A_R_EFFECT_CLUSTER_SENSITIVE_AND_PERSON_SPECIFICITY_NOT_ESTABLISHED"
    )
    m0a_summary = json.loads(M0A_SUMMARY_PATH.read_text(encoding="utf-8"))
    summary = {
        "schema": "PERSON_M0A_R_ROBUSTNESS_AND_SEMANTIC_AUDIT_V1",
        "created_at": now_iso(),
        "starting_head": freeze["starting_head"],
        "frozen_m0a_state": m0a_summary["final_m0a_state"],
        "final_audit_state": final_state,
        "audit_changes_frozen_m0a_state": False,
        "m0a_protocol_sha256": sha256_file(M0A_PROTOCOL_PATH),
        "effective_clusters": {
            "frame_pair": int(supported_frame[["from_frame", "to_frame"]].drop_duplicates().shape[0]),
            "source_region": int(supported_frame["source_region_id"].nunique()),
            "base_edge": int(supported_frame["base_edge_id"].nunique()),
            "target_group": int(supported_frame["supported_target_ids"].nunique()),
            "target_specific_rows_if_expanded": int(supported_frame["supported_target_count"].sum()),
        },
        "supported_edges": {
            "count": int(len(supported_frame)),
            "all_large_q4": bool(supported_frame["support_size_stratum"].eq("LARGE_Q4").all()),
            "all_shared_or_unresolved": all_shared,
            "person_exclusive_count": 0,
            "p0_retention_median": finite(supported_frame["q95_source_total_retention"].median()),
            "zero_retention_median": finite(supported_frame["zero_q95_source_total_retention"].median()),
            "delta_p0_median": finite(supported_frame["delta_p0_source_total_retention"].median()),
        },
        "leave_one_frame_pair_out": {
            "all_remaining_median_p0_retention_above_0p5": bool((loo["p0_retention_median"] > 0.5).all()),
            "all_remaining_median_delta_positive": bool((loo["delta_p0_median"] > 0).all()),
            "minimum_remaining_frame_pair_clusters": int(loo["remaining_frame_pair_clusters"].min()),
            "full_matched_raw_win_fraction": finite(full_loo["matched_raw_supported_win_fraction"]),
            "inference": "DESCRIPTIVE_INSUFFICIENT_INDEPENDENT_CLUSTERS",
        },
        "support_size_cutpoints_px": cuts,
        "tiny_cases_deleted": False,
        "q95_region_existence_is_person_evidence": False,
        "p0_general_registration_is_valid": True,
        "p0_person_specific_mechanism_established": False,
        "positive_semantics": "REFERENCE_SUPPORTED_DYNAMIC_EXPLANATION",
        "optical_angular_dynamics_executed": False,
        "m0b_executed": False,
        "prohibited_claims": {
            "optical_sar_motion_consistency": False,
            "person_specific_region_continuation": False,
            "identity_or_assignment": False,
            "ambiguity_reduction": False,
            "runtime_optical_identity": False,
            "final_sar_localization": False,
        },
    }
    write_json(SUMMARY_PATH, summary)
    paths = {
        "support_size_strata": STRATA_PATH,
        "support_size_sensitivity": size_path,
        "supported_edge_audit": SUPPORTED_AUDIT_PATH,
        "cluster_aware_summary": CLUSTER_PATH,
        "leave_one_frame_pair_out": LOO_PATH,
        "matched_alternative_cluster_audit": MATCHED_CLUSTER_PATH,
        "background_high_response_controls": CONTROL_PATH,
        "supported_matched_background_controls": MATCHED_CONTROL_PATH,
        "p0_gain_family_comparison": FAMILY_PATH,
        "p0_gain_family_by_frame_pair": FAMILY_PAIR_PATH,
        "q95_relative_percentile_semantic_audit": Q95_PATH,
        "shared_unresolved_positive_audit": SHARED_PATH,
        "correlated_descriptor_audit": DEPENDENCY_PATH,
        "real_case_registry": CASE_PATH,
        "audit_summary": SUMMARY_PATH,
    }
    make_report(summary, paths, figures)
    completed = now_iso()
    ledger = {
        "schema": "PERSON_M0A_R_EXECUTION_LEDGER_V1",
        "events": [
            {"stage": "AUDIT_PROTOCOL_AND_HASHES_VERIFIED", "completed_at": started},
            {"stage": "FROZEN_M0A_ARTIFACTS_LOADED_READ_ONLY", "completed_at": started},
            {"stage": "GT_BLIND_SUPPORT_SIZE_STRATA_DERIVED", "completed_at": completed},
            {"stage": "CLUSTER_AND_CONTROL_AUDITS_MATERIALIZED", "completed_at": completed},
            {"stage": "TEN_DETERMINISTIC_REAL_CASES_RENDERED", "completed_at": completed},
            {"stage": "M0A_R_REPORT_COMPLETE_M0B_NOT_EXECUTED", "completed_at": completed},
        ],
    }
    write_json(LEDGER_PATH, ledger)
    output_files = [*paths.values(), REPORT_PATH, LEDGER_PATH, *figures]
    manifest = {
        "schema": "PERSON_M0A_R_OUTPUT_MANIFEST_V1",
        "created_at": completed,
        "starting_head": freeze["starting_head"],
        "protocol_sha256": freeze["protocol_sha256"],
        "m0a_inputs_modified": False,
        "m0b_executed": False,
        "outputs": [
            {
                "path": str(path.relative_to(WORKSPACE)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in output_files
        ],
    }
    write_json(MANIFEST_PATH, manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
