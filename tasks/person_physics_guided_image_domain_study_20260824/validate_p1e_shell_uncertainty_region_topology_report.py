#!/usr/bin/env python3
"""Independent audit for the shell-uncertainty / response-region topology report.

The audit deliberately reads the materialized tables instead of importing the
analysis module.  It verifies the frozen inputs, causal-window semantics,
pre-reference ordering, GT-blind runtime boundary, pixel-edge/node/component
consistency, legacy centered-window parity, headline metrics, and report assets.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
P1E_ROOT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "p1e_sar_only_response_interface"
)
OUTPUT_DIR = P1E_ROOT / "shell_uncertainty_region_topology_v1"
PREVIOUS_ROOT = P1E_ROOT / "runtime_track_response_region_minimal_v1"

ANALYSIS_SCRIPT = TASK_DIR / "run_p1e_shell_uncertainty_region_topology.py"
REPORT_SCRIPT = TASK_DIR / "render_p1e_shell_uncertainty_region_topology_report.py"
REPORT_PATH = OUTPUT_DIR / "P1E_SHELL_UNCERTAINTY_REGION_TOPOLOGY_REPORT.html"
VALIDATION_PATH = OUTPUT_DIR / "report_validation.json"
SUMMARY_PATH = OUTPUT_DIR / "diagnostic_summary.json"
DERIVED_PATH = OUTPUT_DIR / "report_derived_metrics.json"
LEDGER_PATH = OUTPUT_DIR / "execution_ledger.json"
MANIFEST_PATH = OUTPUT_DIR / "pre_reference_manifest.json"
CASE_PATH = OUTPUT_DIR / "case_registry.csv"

DECOMPOSITION_PATH = OUTPUT_DIR / "optical_shell_uncertainty_decomposition_pre_reference.csv"
FRAME_SHELL_PATH = OUTPUT_DIR / "frame_shell_uncertainty_summary_pre_reference.csv"
PAIR_OVERLAP_PATH = OUTPUT_DIR / "gt_blind_shell_pair_overlap_pre_reference.csv"
SHELL_NODE_PATH = OUTPUT_DIR / "gt_blind_shell_nodes_pre_reference.csv"
REGION_NODE_PATH = OUTPUT_DIR / "gt_blind_region_nodes_pre_reference.csv"
EDGE_PATH = OUTPUT_DIR / "gt_blind_shell_region_pixel_edges_pre_reference.csv"
COMPONENT_PATH = OUTPUT_DIR / "gt_blind_bipartite_components_pre_reference.csv"
FRAME_TOPOLOGY_PATH = OUTPUT_DIR / "gt_blind_frame_topology_summary_pre_reference.csv"
SHELL_CONDITION_PATH = OUTPUT_DIR / "gt_blind_shell_nodes_with_conditions.csv"
REGION_CONDITION_PATH = OUTPUT_DIR / "gt_blind_region_nodes_with_conditions.csv"
LEGACY_PARITY_PATH = OUTPUT_DIR / "legacy_centered250_raw_shell_parity.csv"
REFERENCE_RETENTION_PATH = OUTPUT_DIR / "offline_reference_shell_retention.csv"
REFERENCE_TOPOLOGY_PATH = OUTPUT_DIR / "offline_reference_region_topology_interpretation.csv"
R02_PAIR_PATH = OUTPUT_DIR / "offline_r02_associated_shell_separability.csv"

PREVIOUS_SHELL_PATH = PREVIOUS_ROOT / "track_shell_definition_table.csv"
MASK_DIR = PREVIOUS_ROOT / "response_region_masks"

EXPECTED_MASK_COUNT = 398
EXPECTED_MASK_AGGREGATE = "0D9E10C41DB2EE02E060E9AF789AC59C6CD80591B11DC591222CA2B400656CB1"
EXPECTED_COUNTS = {
    "shell_rows": 14607,
    "frame_shell_summary_rows": 7164,
    "pixel_edge_rows": 97219,
    "shell_node_rows": 6927,
    "region_node_rows": 207603,
    "component_rows": 136391,
    "frame_topology_rows": 3582,
    "reference_evaluation_rows": 4518,
    "r02_pair_rows": 324,
}

EXPECTED_INPUT_HASHES = {
    TASK_DIR / "run_p1e_runtime_track_response_region_minimal.py": "051B414753B73118CF77712A35DF86EC5FB05C12B2C00217EB14BFE81DFDCBBA",
    TASK_DIR / "run_p1e_candidate_recall_audit.py": "84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8",
    TASK_DIR / "run_p1e_optical_shell_information_gain.py": "2C71440DF9C22FDCE17A3C4050E4E0054F6B7CA4542C44C134E2DEA3478A2203",
    PREVIOUS_SHELL_PATH: "B6C58404F54F542133EE5678EBB93B97758BE85EFE71CA252C41FD3018C061C5",
    PREVIOUS_ROOT / "response_region_table_pre_reference.csv": "A2BB425C366EA0DE461C427113E8E836A556F65250677146B6F26129E853C339",
    PREVIOUS_ROOT / "candidate_recomputation_parity.csv": "21FA3270E268EEC460E603C07F1D840182780E0FB671B0ABFC04E12256C35329",
    PREVIOUS_ROOT / "offline_reference_response_region_evaluation.csv": "4522FE9B65249180B073EA16E87BF11A528DC079B3831348CD7610E3685B7353",
    P1E_ROOT / "observation_model_diagnostic_v1" / "observation_condition_table.csv": "DE65B9705A353F0DF783E0D4A59D0274FD05547362ABE463C50C9C5469D80C21",
    WORKSPACE / "output" / "person_optical_guided_sar_annotation_full_20260823" / "optical_person_frame_hypotheses.parquet": "15D65A299762E87BFD6F21E811C754D1DF062AC6AFC1840A1C1A9B162AB8B478",
    WORKSPACE / "output" / "r01_person_azimuth_pilot_20260819" / "model_summary.json": "3463FFF0A8D1507ECA383356E0FB108BD60E1226A19890B62EA8C8FD5090BA42",
    WORKSPACE / "output" / "r04_person_crossrun_validation_20260820" / "validation_report.json": "24D0CEE627B272EA76A64BC245C0779DA2F6ED428E885C77490A177DBE470A14",
    WORKSPACE / "output" / "person_multidimensional_response_explorer_20260823" / "explorer_data.js": "C39E60EB478FF7D815EFE6984D3BCF36600737E2EC3D1FF76D04020DED54EF7D",
}

CORE_PRE_REFERENCE_PATHS = [
    DECOMPOSITION_PATH,
    FRAME_SHELL_PATH,
    PAIR_OVERLAP_PATH,
    SHELL_NODE_PATH,
    REGION_NODE_PATH,
    EDGE_PATH,
    COMPONENT_PATH,
    FRAME_TOPOLOGY_PATH,
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def mask_manifest_aggregate(mask_dir: Path) -> tuple[int, str]:
    rows = [f"{path.name}:{sha256_file(path)}" for path in sorted(mask_dir.glob("*.npz"))]
    return len(rows), hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest().upper()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def close(left: Any, right: Any, tolerance: float = 1e-12) -> bool:
    try:
        return math.isfinite(float(left)) and math.isfinite(float(right)) and abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return False


def json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def validate() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    required = [
        ANALYSIS_SCRIPT,
        REPORT_SCRIPT,
        REPORT_PATH,
        SUMMARY_PATH,
        DERIVED_PATH,
        LEDGER_PATH,
        MANIFEST_PATH,
        CASE_PATH,
        SHELL_CONDITION_PATH,
        REGION_CONDITION_PATH,
        LEGACY_PARITY_PATH,
        REFERENCE_RETENTION_PATH,
        REFERENCE_TOPOLOGY_PATH,
        R02_PAIR_PATH,
        PREVIOUS_SHELL_PATH,
        *CORE_PRE_REFERENCE_PATHS,
        *EXPECTED_INPUT_HASHES.keys(),
    ]
    missing = sorted({str(path) for path in required if not path.is_file()})
    add("required_inputs_tables_scripts_and_report_exist", not missing, missing)
    if missing:
        return {
            "schema": "PERSON_P1E_SHELL_UNCERTAINTY_REGION_TOPOLOGY_REPORT_VALIDATION_V1",
            "created_at": now_iso(),
            "status": "FAIL",
            "checks_passed": sum(check["pass"] for check in checks),
            "checks_total": len(checks),
            "checks": checks,
        }

    summary = load_json(SUMMARY_PATH)
    derived = load_json(DERIVED_PATH)
    ledger = load_json(LEDGER_PATH)
    manifest = load_json(MANIFEST_PATH)
    html_text = REPORT_PATH.read_text(encoding="utf-8")

    input_hash_rows = []
    for path, expected in EXPECTED_INPUT_HASHES.items():
        actual = sha256_file(path)
        input_hash_rows.append(
            {"path": str(path), "expected_sha256": expected, "actual_sha256": actual, "match": actual == expected}
        )
    add(
        "all_frozen_input_sha256_values_match",
        all(row["match"] for row in input_hash_rows)
        and all(bool(row.get("match")) for row in summary["input_hash_checks"]),
        input_hash_rows,
    )

    mask_count, mask_aggregate = mask_manifest_aggregate(MASK_DIR)
    add(
        "all_398_frozen_region_masks_match_aggregate_sha256",
        mask_count == EXPECTED_MASK_COUNT
        and mask_aggregate == EXPECTED_MASK_AGGREGATE
        and bool(summary["mask_manifest_check"]["match"]),
        {
            "mask_count": mask_count,
            "expected_mask_count": EXPECTED_MASK_COUNT,
            "aggregate_sha256": mask_aggregate,
            "expected_aggregate_sha256": EXPECTED_MASK_AGGREGATE,
        },
    )

    decomposition = pd.read_csv(DECOMPOSITION_PATH, low_memory=False)
    frame_shells = pd.read_csv(FRAME_SHELL_PATH, low_memory=False)
    shell_nodes = pd.read_csv(SHELL_NODE_PATH, low_memory=False)
    region_nodes = pd.read_csv(REGION_NODE_PATH, low_memory=False)
    edges = pd.read_csv(EDGE_PATH, low_memory=False)
    components = pd.read_csv(COMPONENT_PATH, low_memory=False)
    frame_topology = pd.read_csv(FRAME_TOPOLOGY_PATH, low_memory=False)
    retention = pd.read_csv(REFERENCE_RETENTION_PATH, low_memory=False)
    reference_topology = pd.read_csv(REFERENCE_TOPOLOGY_PATH, low_memory=False)
    r02_pairs = pd.read_csv(R02_PAIR_PATH, low_memory=False)
    legacy_parity = pd.read_csv(LEGACY_PARITY_PATH, low_memory=False)
    cases = pd.read_csv(CASE_PATH, low_memory=False)

    actual_counts = {
        "shell_rows": len(decomposition),
        "frame_shell_summary_rows": len(frame_shells),
        "pixel_edge_rows": len(edges),
        "shell_node_rows": len(shell_nodes),
        "region_node_rows": len(region_nodes),
        "component_rows": len(components),
        "frame_topology_rows": len(frame_topology),
        "reference_evaluation_rows": len(retention),
        "r02_pair_rows": len(r02_pairs),
    }
    add(
        "all_materialized_row_counts_match_frozen_summary",
        actual_counts == EXPECTED_COUNTS and actual_counts == summary["counts"],
        {"actual": actual_counts, "expected": EXPECTED_COUNTS, "summary": summary["counts"]},
    )

    reconstructed = (
        pd.to_numeric(decomposition["single_detection_box_width_median_deg"], errors="coerce")
        + pd.to_numeric(decomposition["temporal_or_view_union_increment_deg"], errors="coerce")
        + pd.to_numeric(decomposition["guard_union_increment_deg"], errors="coerce")
        - pd.to_numeric(decomposition["fan_clip_loss_deg"], errors="coerce")
    )
    direct_error = reconstructed - pd.to_numeric(decomposition["effective_width_deg"], errors="coerce")
    recorded_error = pd.to_numeric(decomposition["decomposition_reconstruction_error_deg"], errors="coerce")
    max_direct_error = float(direct_error.abs().max())
    max_recorded_error = float(recorded_error.abs().max())
    max_recorded_difference = float((direct_error.abs() - recorded_error.abs()).abs().max())
    add(
        "shell_width_decomposition_closes_to_machine_precision",
        max_direct_error <= 1e-12 and max_recorded_error <= 1e-12 and max_recorded_difference <= 1e-12,
        {
            "max_abs_direct_reconstruction_error_deg": max_direct_error,
            "max_abs_recorded_reconstruction_error_deg": max_recorded_error,
            "max_abs_difference_from_recorded_error_deg": max_recorded_difference,
        },
    )

    source_min = pd.to_numeric(decomposition["source_timestamp_min_ms"], errors="coerce")
    source_max = pd.to_numeric(decomposition["source_timestamp_max_ms"], errors="coerce")
    nominal = pd.to_numeric(decomposition["nominal_optical_timestamp_ms"], errors="coerce")
    low = pd.to_numeric(decomposition["window_low_offset_ms"], errors="coerce")
    high = pd.to_numeric(decomposition["window_high_offset_ms"], errors="coerce")
    future_flag = as_bool(decomposition["source_has_future_observation"])
    timestamp_bounds_ok = bool(((source_min >= nominal + low - 1e-9) & (source_max <= nominal + high + 1e-9)).all())
    future_flag_ok = bool((future_flag == (source_max > nominal + 1e-9)).all())
    causal = decomposition[decomposition["temporal_policy"].isin(["SAME_FRAME", "PAST_ONLY_250MS"])]
    causal_no_future = (
        not as_bool(causal["source_has_future_observation"]).any()
        and int(pd.to_numeric(causal["source_future_observation_count"], errors="coerce").fillna(0).max()) == 0
        and bool((pd.to_numeric(causal["source_timestamp_max_ms"], errors="coerce") <= pd.to_numeric(causal["nominal_optical_timestamp_ms"], errors="coerce") + 1e-9).all())
        and set(pd.to_numeric(causal["allowed_future_latency_ms"], errors="coerce").dropna().astype(int)) == {0}
    )
    add(
        "temporal_windows_obey_registered_bounds_and_causal_policies_use_no_future",
        timestamp_bounds_ok and future_flag_ok and causal_no_future,
        {
            "all_source_timestamps_within_policy_bounds": timestamp_bounds_ok,
            "future_flag_matches_source_timestamps": future_flag_ok,
            "same_frame_and_past_only_have_no_future": causal_no_future,
            "future_rows_by_policy": {
                str(policy): int(as_bool(group["source_has_future_observation"]).sum())
                for policy, group in decomposition.groupby("temporal_policy")
            },
        },
    )

    stage_names = [row["stage"] for row in ledger]
    expected_stage_order = [
        "FROZEN_DEPENDENCY_AND_MASK_HASH_CHECK",
        "OPTICAL_RAW_FRAGMENT_PROVENANCE_LOADED_WITHOUT_SAR_REFERENCE",
        "ALL_SHELL_UNCERTAINTY_VARIANTS_GENERATED_WITHOUT_SAR_REFERENCE",
        "ALL_PIXEL_EDGES_AND_BIPARTITE_TOPOLOGY_GENERATED_WITHOUT_SAR_REFERENCE",
        "GT_BLIND_CANDIDATE_SAMPLED_P0_AND_FRAME_DISPLAY_CONDITIONS_ATTACHED",
        "MANUAL_REFERENCE_MATERIALIZED_ONLY_FOR_OFFLINE_INTERPRETATION",
    ]
    stage_times = [parse_iso(row["completed_at"]) for row in ledger]
    manual_time = stage_times[-1]
    core_pre_mtime = max(path.stat().st_mtime for path in CORE_PRE_REFERENCE_PATHS)
    offline_mtime = min(path.stat().st_mtime for path in [REFERENCE_RETENTION_PATH, REFERENCE_TOPOLOGY_PATH, R02_PAIR_PATH])
    manifest_hashes_match = (
        manifest["shell_table_sha256"] == sha256_file(DECOMPOSITION_PATH)
        and manifest["edge_table_sha256"] == sha256_file(EDGE_PATH)
        and manifest["component_table_sha256"] == sha256_file(COMPONENT_PATH)
    )
    add(
        "pre_reference_products_precede_manual_reference_materialization",
        stage_names == expected_stage_order
        and stage_times == sorted(stage_times)
        and parse_iso(manifest["generated_at"]) < manual_time
        and manifest["reference_loaded"] is False
        and manifest_hashes_match
        and core_pre_mtime <= offline_mtime,
        {
            "stage_order": stage_names,
            "manifest_generated_at": manifest["generated_at"],
            "manual_reference_stage_at": ledger[-1]["completed_at"],
            "manifest_reference_loaded": manifest["reference_loaded"],
            "manifest_hashes_match_current_tables": manifest_hashes_match,
            "latest_core_pre_reference_mtime": datetime.fromtimestamp(core_pre_mtime, timezone.utc).isoformat(),
            "earliest_offline_reference_mtime": datetime.fromtimestamp(offline_mtime, timezone.utc).isoformat(),
            "strict_sealed_process_isolation_claimed": manifest["process_note"]["strict_sealed_process_isolation_claimed"],
        },
    )

    runtime_tables = {
        "decomposition": DECOMPOSITION_PATH,
        "frame_shell": FRAME_SHELL_PATH,
        "pair_overlap": PAIR_OVERLAP_PATH,
        "shell_nodes": SHELL_NODE_PATH,
        "region_nodes": REGION_NODE_PATH,
        "edges": EDGE_PATH,
        "components": COMPONENT_PATH,
        "frame_topology": FRAME_TOPOLOGY_PATH,
        "shell_conditions": SHELL_CONDITION_PATH,
        "region_conditions": REGION_CONDITION_PATH,
    }
    forbidden_exact_columns = {"physical_target_id", "target_id", "reference_x_px", "reference_y_px"}
    forbidden_columns: dict[str, list[str]] = {}
    for name, path in runtime_tables.items():
        columns = set(pd.read_csv(path, nrows=0).columns)
        bad = sorted(columns & forbidden_exact_columns)
        if bad:
            forbidden_columns[name] = bad
    runtime_boundary_ok = (
        not as_bool(decomposition["physical_target_id_used"]).any()
        and not as_bool(decomposition["sar_reference_used"]).any()
        and not as_bool(decomposition["sar_range_assigned_by_optical"]).any()
        and not as_bool(decomposition["strict_runtime_identity_claimed"]).any()
        and not as_bool(frame_shells["physical_target_id_used"]).any()
        and not as_bool(frame_shells["sar_reference_used"]).any()
        and not as_bool(edges["physical_target_id_used"]).any()
        and not as_bool(edges["sar_reference_used"]).any()
        and as_bool(shell_nodes["gt_blind"]).all()
        and as_bool(region_nodes["gt_blind"]).all()
        and as_bool(components["gt_blind"]).all()
        and as_bool(frame_topology["gt_blind"]).all()
        and not forbidden_columns
    )
    add(
        "runtime_shell_region_edge_topology_products_remain_gt_blind",
        runtime_boundary_ok,
        {
            "forbidden_columns": forbidden_columns,
            "physical_target_id_used_shell_rows": int(as_bool(decomposition["physical_target_id_used"]).sum()),
            "sar_reference_used_shell_rows": int(as_bool(decomposition["sar_reference_used"]).sum()),
            "sar_range_assigned_by_optical_rows": int(as_bool(decomposition["sar_range_assigned_by_optical"]).sum()),
            "strict_runtime_identity_claimed_rows": int(as_bool(decomposition["strict_runtime_identity_claimed"]).sum()),
            "physical_target_id_used_edge_rows": int(as_bool(edges["physical_target_id_used"]).sum()),
            "sar_reference_used_edge_rows": int(as_bool(edges["sar_reference_used"]).sum()),
        },
    )

    base_keys = ["run_id", "frame_uid", "frame_index", "temporal_policy", "guard_variant", "percentile_tag"]
    shell_keys = [*base_keys, "shell_id"]
    region_keys = [*base_keys, "region_id"]
    shell_degree = edges.groupby(shell_keys, dropna=False)["region_id"].nunique().rename("degree_from_edges").reset_index()
    region_degree = edges.groupby(region_keys, dropna=False)["shell_id"].nunique().rename("degree_from_edges").reset_index()
    shell_degree_check = shell_nodes.merge(shell_degree, on=shell_keys, how="left")
    region_degree_check = region_nodes.merge(region_degree, on=region_keys, how="left")
    shell_degree_check["degree_from_edges"] = shell_degree_check["degree_from_edges"].fillna(0).astype(int)
    region_degree_check["degree_from_edges"] = region_degree_check["degree_from_edges"].fillna(0).astype(int)
    shell_degree_mismatch = int(
        (pd.to_numeric(shell_degree_check["shell_degree_region_count"], errors="coerce").fillna(-1).astype(int) != shell_degree_check["degree_from_edges"]).sum()
    )
    region_degree_mismatch = int(
        (pd.to_numeric(region_degree_check["region_degree_shell_count"], errors="coerce").fillna(-1).astype(int) != region_degree_check["degree_from_edges"]).sum()
    )
    add(
        "all_shell_and_region_local_degrees_equal_unique_pixel_edge_counts",
        shell_degree_mismatch == 0 and region_degree_mismatch == 0,
        {
            "shell_nodes": len(shell_degree_check),
            "shell_degree_mismatches": shell_degree_mismatch,
            "region_nodes": len(region_degree_check),
            "region_degree_mismatches": region_degree_mismatch,
        },
    )

    shell_component_map = shell_nodes[shell_keys + ["component_id"]].rename(columns={"component_id": "shell_component_id"})
    region_component_map = region_nodes[region_keys + ["component_id"]].rename(columns={"component_id": "region_component_id"})
    edge_components = edges.merge(shell_component_map, on=shell_keys, how="left", validate="many_to_one")
    edge_components = edge_components.merge(region_component_map, on=region_keys, how="left", validate="many_to_one")
    edge_component_mismatch = int(
        edge_components["shell_component_id"].isna().sum()
        + edge_components["region_component_id"].isna().sum()
        + (edge_components["shell_component_id"] != edge_components["region_component_id"]).sum()
    )
    component_keys = [*base_keys, "component_id"]
    shell_component_counts = shell_nodes.groupby(component_keys, dropna=False)["shell_id"].nunique().rename("shell_count_recomputed")
    region_component_counts = region_nodes.groupby(component_keys, dropna=False)["region_id"].nunique().rename("region_count_recomputed")
    edge_components = edge_components.assign(component_id=edge_components["shell_component_id"])
    edge_component_counts = edge_components.groupby(component_keys, dropna=False).agg(
        edge_count_recomputed=("region_id", "size"),
        intersection_pixel_count_sum_recomputed=("intersection_pixel_count", "sum"),
    )
    component_check = components.merge(shell_component_counts.reset_index(), on=component_keys, how="left")
    component_check = component_check.merge(region_component_counts.reset_index(), on=component_keys, how="left")
    component_check = component_check.merge(edge_component_counts.reset_index(), on=component_keys, how="left")
    for column in [
        "shell_count_recomputed",
        "region_count_recomputed",
        "edge_count_recomputed",
        "intersection_pixel_count_sum_recomputed",
    ]:
        component_check[column] = component_check[column].fillna(0).astype(int)
    count_mismatch = (
        (pd.to_numeric(component_check["shell_count"], errors="coerce").astype(int) != component_check["shell_count_recomputed"])
        | (pd.to_numeric(component_check["region_count"], errors="coerce").astype(int) != component_check["region_count_recomputed"])
        | (pd.to_numeric(component_check["edge_count"], errors="coerce").astype(int) != component_check["edge_count_recomputed"])
        | (
            pd.to_numeric(component_check["intersection_pixel_count_sum"], errors="coerce").astype(int)
            != component_check["intersection_pixel_count_sum_recomputed"]
        )
    )

    def topology_from_counts(shell_count: int, region_count: int) -> str:
        if shell_count == 1 and region_count == 1:
            return "ONE_SHELL_ONE_REGION"
        if shell_count == 1 and region_count > 1:
            return "ONE_SHELL_MULTIPLE_REGIONS"
        if shell_count > 1 and region_count == 1:
            return "MULTIPLE_SHELLS_ONE_REGION"
        if shell_count > 1 and region_count > 1:
            return "MULTIPLE_SHELLS_MULTIPLE_REGIONS"
        if shell_count == 1 and region_count == 0:
            return "SHELL_NO_REGION"
        if shell_count == 0 and region_count == 1:
            return "REGION_NO_SHELL"
        return "INVALID_COMPONENT"

    topology_recomputed = component_check.apply(
        lambda row: topology_from_counts(int(row["shell_count_recomputed"]), int(row["region_count_recomputed"])), axis=1
    )
    topology_mismatch = int((component_check["topology_state"].astype(str) != topology_recomputed).sum())
    add(
        "all_edges_join_one_component_and_component_counts_topology_recompute",
        edge_component_mismatch == 0 and int(count_mismatch.sum()) == 0 and topology_mismatch == 0,
        {
            "edge_rows": len(edge_components),
            "edge_component_mismatches": edge_component_mismatch,
            "component_rows": len(component_check),
            "component_count_mismatches": int(count_mismatch.sum()),
            "component_topology_mismatches": topology_mismatch,
        },
    )

    previous_shells = pd.read_csv(PREVIOUS_SHELL_PATH, low_memory=False)
    previous_centered = previous_shells[
        (previous_shells["interface_kind"] == "RAW_DETECTED_FRAGMENT_ALL")
        & (pd.to_numeric(previous_shells["time_window_half_width_ms"], errors="coerce") == 250)
        & (previous_shells["shell_scope"] == "TRACK")
    ][
        ["run_id", "frame_uid", "frame_index", "track_id", "effective_width_deg", "effective_area_px", "effective_intervals_json"]
    ].copy()
    current_centered = decomposition[
        (decomposition["temporal_policy"] == "CENTERED_250MS")
        & (decomposition["guard_variant"] == "CURRENT_G6")
    ][
        ["run_id", "frame_uid", "frame_index", "track_id", "effective_width_deg", "effective_area_px", "effective_intervals_json"]
    ].copy()
    parity_keys = ["run_id", "frame_uid", "frame_index", "track_id"]
    direct_parity = previous_centered.merge(
        current_centered,
        on=parity_keys,
        how="outer",
        suffixes=("_legacy", "_current"),
        indicator=True,
        validate="one_to_one",
    )
    direct_width_error = pd.to_numeric(
        direct_parity["effective_width_deg_legacy"], errors="coerce"
    ) - pd.to_numeric(direct_parity["effective_width_deg_current"], errors="coerce")
    direct_area_error = pd.to_numeric(
        direct_parity["effective_area_px_legacy"], errors="coerce"
    ) - pd.to_numeric(direct_parity["effective_area_px_current"], errors="coerce")
    direct_intervals_exact = (
        direct_parity["effective_intervals_json_legacy"].astype(str)
        == direct_parity["effective_intervals_json_current"].astype(str)
    )
    stored_parity_ok = (
        len(legacy_parity) == 854
        and set(legacy_parity["_merge"].astype(str)) == {"both"}
        and close(pd.to_numeric(legacy_parity["effective_width_abs_diff"], errors="coerce").max(), 0.0)
        and close(pd.to_numeric(legacy_parity["effective_area_px_diff"], errors="coerce").abs().max(), 0.0)
        and as_bool(legacy_parity["effective_intervals_exact"]).all()
    )
    direct_parity_ok = (
        len(previous_centered) == 854
        and len(current_centered) == 854
        and len(direct_parity) == 854
        and set(direct_parity["_merge"].astype(str)) == {"both"}
        and close(direct_width_error.abs().max(), 0.0)
        and close(direct_area_error.abs().max(), 0.0)
        and direct_intervals_exact.all()
    )
    add(
        "all_854_centered_250ms_raw_shells_match_previous_frozen_interface_exactly",
        stored_parity_ok and direct_parity_ok,
        {
            "legacy_rows": len(previous_centered),
            "current_rows": len(current_centered),
            "merged_rows": len(direct_parity),
            "merge_states": sorted(set(direct_parity["_merge"].astype(str))),
            "max_width_abs_error_deg": float(direct_width_error.abs().max()),
            "max_area_abs_error_px": float(direct_area_error.abs().max()),
            "intervals_exact": bool(direct_intervals_exact.all()),
            "stored_parity_table_exact": stored_parity_ok,
        },
    )

    r02_frame = frame_shells[
        (frame_shells["run_id"] == "R02ZF")
        & (frame_shells["guard_variant"] == "CURRENT_G6")
    ]
    r02_retention = retention[
        (retention["run_id"] == "R02ZF")
        & (retention["guard_variant"] == "CURRENT_G6")
    ]
    expected_policy_metrics = {
        "SAME_FRAME": (0.8333333333333334, 28.3),
        "PAST_ONLY_250MS": (0.9166666666666666, 29.0),
        "BUFFERED_100MS": (0.9444444444444444, 29.8),
        "CENTERED_250MS": (0.9444444444444444, 31.9),
    }
    actual_policy_metrics: dict[str, dict[str, float]] = {}
    headline_ok = True
    for policy, (expected_retention, expected_burden_percent) in expected_policy_metrics.items():
        retention_value = float(as_bool(r02_retention[r02_retention["temporal_policy"] == policy]["any_shell_reference_retained"]).mean())
        burden_value = float(
            pd.to_numeric(
                r02_frame[r02_frame["temporal_policy"] == policy]["all_track_union_effective_area_fraction_of_omega"],
                errors="coerce",
            ).median()
        )
        actual_policy_metrics[policy] = {
            "reference_retention": retention_value,
            "union_burden_median": burden_value,
            "union_burden_display_percent": round(burden_value * 100.0, 1),
        }
        headline_ok = (
            headline_ok
            and close(retention_value, expected_retention)
            and round(burden_value * 100.0, 1) == expected_burden_percent
        )
    r02_same = r02_frame[r02_frame["temporal_policy"] == "SAME_FRAME"]
    r02_centered = r02_frame[r02_frame["temporal_policy"] == "CENTERED_250MS"]
    width_metrics = {
        "same_frame_single_box_median_deg": float(pd.to_numeric(r02_same["single_box_width_median_deg"], errors="coerce").median()),
        "same_frame_guard_increment_median_deg": float(pd.to_numeric(r02_same["guard_increment_median_deg"], errors="coerce").median()),
        "same_frame_effective_width_median_deg": float(pd.to_numeric(r02_same["single_track_width_median_deg"], errors="coerce").median()),
        "centered_time_union_increment_median_deg": float(pd.to_numeric(r02_centered["temporal_union_increment_median_deg"], errors="coerce").median()),
        "centered_effective_width_median_deg": float(pd.to_numeric(r02_centered["single_track_width_median_deg"], errors="coerce").median()),
    }
    width_ok = (
        round(width_metrics["same_frame_single_box_median_deg"], 2) == 2.69
        and round(width_metrics["same_frame_guard_increment_median_deg"], 2) == 12.00
        and round(width_metrics["same_frame_effective_width_median_deg"], 2) == 14.69
        and round(width_metrics["centered_time_union_increment_median_deg"], 2) == 6.91
        and round(width_metrics["centered_effective_width_median_deg"], 2) == 21.62
        and close(derived["r02_same_frame_current"]["single_box_width_median_deg"], 2.69)
        and close(derived["r02_same_frame_current"]["guard_increment_median_deg"], 12.0)
        and close(derived["r02_same_frame_current"]["retention"], 0.8333333333333334)
    )
    add(
        "r02_shell_width_retention_and_burden_headlines_recompute",
        headline_ok and width_ok,
        {"width_metrics": width_metrics, "policy_metrics": actual_policy_metrics},
    )

    degree_expected = {
        "SAME_FRAME": (257, 46, 161, 50),
        "PAST_ONLY_250MS": (273, 40, 151, 82),
        "CENTERED_250MS": (307, 39, 108, 160),
    }
    degree_actual: dict[str, tuple[int, int, int, int]] = {}
    degree_ok = True
    for policy, expected in degree_expected.items():
        group = region_nodes[
            (region_nodes["run_id"] == "R02ZF")
            & (region_nodes["percentile_tag"] == "Q095")
            & (region_nodes["temporal_policy"] == policy)
            & (pd.to_numeric(region_nodes["region_degree_shell_count"], errors="coerce") > 0)
        ]
        degree = pd.to_numeric(group["region_degree_shell_count"], errors="coerce")
        actual = (len(group), int((degree == 1).sum()), int((degree == 2).sum()), int((degree >= 3).sum()))
        degree_actual[policy] = actual
        degree_ok = degree_ok and actual == expected
    add("r02_q95_local_region_degree_headlines_recompute", degree_ok, degree_actual)

    f_cases = reference_topology[
        (reference_topology["run_id"] == "R02ZF")
        & (reference_topology["frame_index"].isin([482, 490]))
        & (reference_topology["target_id"].astype(str).str.endswith("02"))
        & (reference_topology["percentile_tag"] == "Q095")
    ]
    f_case_ok = (
        len(f_cases) == 6
        and set(f_cases["temporal_policy"]) == {"SAME_FRAME", "PAST_ONLY_250MS", "CENTERED_250MS"}
        and set(f_cases["representation_state"]) == {"PEAK_MISSING_REGION_PRESENT"}
        and as_bool(f_cases["shared_region_flag"]).all()
        and set(f_cases["topology_state"]) == {"MULTIPLE_SHELLS_MULTIPLE_REGIONS"}
        and set(f_cases["nearest_region_id"].astype(str))
        == {"R02ZF_SARF000482__Q095__R0012", "R02ZF_SARF000490__Q095__R0012"}
    )
    add(
        "f482_f490_peak_missing_region_present_semantics_are_preserved",
        f_case_ok,
        f_cases[
            [
                "frame_index",
                "target_id",
                "temporal_policy",
                "representation_state",
                "nearest_region_id",
                "region_degree_shell_count",
                "topology_state",
            ]
        ].to_dict("records"),
    )

    local_refs = re.findall(r"(?:src|href)\s*=\s*['\"]([^'\"]+)['\"]", html_text)
    image_refs = [ref for ref in local_refs if Path(ref).suffix.lower() in {".png", ".jpg", ".jpeg"}]
    missing_refs: list[dict[str, str]] = []
    unreadable_images: list[dict[str, str]] = []
    image_dimensions: dict[str, list[int]] = {}
    for ref in local_refs:
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", ref):
            continue
        resolved = (OUTPUT_DIR / Path(ref)).resolve()
        if not resolved.exists():
            missing_refs.append({"ref": ref, "resolved": str(resolved)})
    for ref in image_refs:
        path = (OUTPUT_DIR / Path(ref)).resolve()
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                image_dimensions[ref] = list(image.size)
        except Exception as exc:  # pragma: no cover
            unreadable_images.append({"ref": ref, "error": repr(exc)})
    case_refs = set(cases["image"].astype(str))
    add(
        "html_links_and_all_12_formal_visualizations_are_readable",
        not missing_refs
        and not unreadable_images
        and len(local_refs) == 19
        and len(image_refs) == 12
        and len(cases) == 7
        and case_refs.issubset(set(image_refs)),
        {
            "local_reference_count": len(local_refs),
            "formal_image_count": len(image_refs),
            "case_count": len(cases),
            "missing_references": missing_refs,
            "unreadable_images": unreadable_images,
            "image_dimensions": image_dimensions,
        },
    )

    required_phrases = [
        "这轮没有建立 P2",
        "q95 region 不是 PERSON box",
        "不进入 P2",
        "不生成 SAR range/box",
        "SAR 保留 range 与最终定位权",
        "不是 PERSON identity 或最终定位",
        "GT-blind 可计算",
        "只能 reference-conditioned 离线解释",
        "0° 并不是可部署壳",
        "不是最优窗口选择",
    ]
    forbidden_positive_claims = [
        "P2 已经成立",
        "P2_PASS",
        "生成了最终 PERSON 框",
        "严格 runtime identity 已建立",
        "盲验证通过",
        "证明物理散射融合",
    ]
    add(
        "report_keeps_semantic_boundaries_and_answers_both_registered_questions",
        all(phrase in html_text for phrase in required_phrases)
        and not any(phrase in html_text for phrase in forbidden_positive_claims)
        and "光学方位不确定度由什么组成？" in html_text
        and "不看 GT 时已经形成什么结构？" in html_text,
        {
            "required_phrases": {phrase: phrase in html_text for phrase in required_phrases},
            "forbidden_positive_claims": {phrase: phrase in html_text for phrase in forbidden_positive_claims},
        },
    )

    boundaries = summary["boundaries"]
    add(
        "machine_summary_status_and_fixed_boundaries_are_preserved",
        summary["status"] == "COMPLETE_NO_NEW_PASS_FAIL_NO_P2_CLAIM"
        and boundaries["main_optical_interface"] == "RAW_DETECTED_FRAGMENT_ALL"
        and not boundaries["runtime_optical_identity_established"]
        and not boundaries["physical_target_id_used_for_runtime_products"]
        and not boundaries["sar_reference_used_for_shell_region_edge_or_topology"]
        and boundaries["reference_materialized_after_topology"]
        and not boundaries["response_region_is_person_box"]
        and not boundaries["sar_range_generated"]
        and not boundaries["new_total_score_or_classifier"]
        and not boundaries["p2_claim"],
        boundaries,
    )

    analysis_hash = sha256_file(ANALYSIS_SCRIPT)
    report_script_hash = sha256_file(REPORT_SCRIPT)
    report_hash = sha256_file(REPORT_PATH)
    add(
        "analysis_hash_matches_report_record_and_artifacts_stay_in_active_workspace",
        derived["analysis_script_sha256"] == analysis_hash
        and str(OUTPUT_DIR.resolve()).lower().startswith(str(WORKSPACE.resolve()).lower())
        and "old_work" not in str(OUTPUT_DIR).lower()
        and all("old_work" not in ref.lower() for ref in local_refs),
        {
            "derived_analysis_sha256": derived["analysis_script_sha256"],
            "actual_analysis_sha256": analysis_hash,
            "report_script_sha256": report_script_hash,
            "report_sha256": report_hash,
            "workspace": str(WORKSPACE.resolve()),
            "output_dir": str(OUTPUT_DIR.resolve()),
        },
    )

    status = "PASS" if all(check["pass"] for check in checks) else "FAIL"
    return {
        "schema": "PERSON_P1E_SHELL_UNCERTAINTY_REGION_TOPOLOGY_REPORT_VALIDATION_V1",
        "created_at": now_iso(),
        "status": status,
        "checks_passed": sum(check["pass"] for check in checks),
        "checks_total": len(checks),
        "report_path": str(REPORT_PATH),
        "report_sha256": report_hash,
        "analysis_script_sha256": analysis_hash,
        "report_script_sha256": report_script_hash,
        "validation_script_sha256": sha256_file(SCRIPT_PATH),
        "checks": checks,
    }


def main() -> None:
    expected_workspace = Path(r"D:\profile\research\workspace").resolve()
    if WORKSPACE.resolve() != expected_workspace:
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    result = validate()
    VALIDATION_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=json_default),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=json_default))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
