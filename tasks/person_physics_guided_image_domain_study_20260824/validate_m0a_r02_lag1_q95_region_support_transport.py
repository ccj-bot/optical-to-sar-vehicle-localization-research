#!/usr/bin/env python3
"""Independent materialized-output validator for the frozen M0A pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
OUTPUT_DIR = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824" / "m0a_r02_lag1_q95_region_support_transport_pilot"
NODE_PATH = OUTPUT_DIR / "pre_reference_region_nodes.csv"
MATRIX_PATH = OUTPUT_DIR / "pre_reference_compatibility_matrix.csv"
MATCHED_PATH = OUTPUT_DIR / "pre_reference_matched_alternative_sets.csv"
CASE_PATH = OUTPUT_DIR / "pre_reference_case_registry.csv"
MANIFEST_PATH = OUTPUT_DIR / "pre_reference_manifest.json"
LEDGER_PATH = OUTPUT_DIR / "pre_reference_execution_ledger.json"
SYNTHETIC_PATH = OUTPUT_DIR / "warp_synthetic_tests.json"
VALIDATION_PATH = OUTPUT_DIR / "pre_reference_validation.json"
HASH_PATH = OUTPUT_DIR / "pre_reference_output_hashes.json"
POST_SUPPORTED_PATH = OUTPUT_DIR / "post_reference_supported_explanations.csv"
POST_MATCHED_PATH = OUTPUT_DIR / "post_reference_matched_alternative_evaluation.csv"
POST_CASE_PATH = OUTPUT_DIR / "post_reference_case_registry.csv"
POST_SUMMARY_PATH = OUTPUT_DIR / "post_reference_summary.json"
EXECUTION_LEDGER_PATH = OUTPUT_DIR / "execution_ledger.json"
REPORT_PATH = OUTPUT_DIR / "M0A_R02_LAG1_Q95_REGION_SUPPORT_TRANSPORT_REPORT.html"
FINAL_VALIDATION_PATH = OUTPUT_DIR / "final_validation.json"

PROHIBITED = {
    "physical_target_id", "target_id", "reference_x_px", "reference_y_px",
    "reference_range_m", "reference_theta_deg", "optical_person_id",
    "source_parent_stitched_ids", "reference_supported", "reference_support_state",
}
TOL = 1e-8


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_object(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def check(condition: bool, name: str, details: Any, checks: list[dict[str, Any]]) -> None:
    checks.append({"name": name, "status": "PASS" if condition else "FAIL", "details": details})


def finite_max_abs(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna().to_numpy(float)
    return float(np.max(np.abs(numeric))) if len(numeric) else 0.0


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")


def structural_distance(edge: pd.Series, alternative: pd.Series) -> float:
    area_edge = max(float(edge["destination_area_m2"]), 1e-12)
    area_alt = max(float(alternative["destination_area_m2"]), 1e-12)
    return float(
        4.0 * (bool_value(edge["destination_touches_observable_boundary"]) != bool_value(alternative["destination_touches_observable_boundary"]))
        + 4.0 * (bool_value(edge["destination_has_truncated_support"]) != bool_value(alternative["destination_has_truncated_support"]))
        + abs(int(edge["destination_region_degree_bin"]) - int(alternative["destination_region_degree_bin"]))
        + abs(int(edge["destination_component_shell_count_bin"]) - int(alternative["destination_component_shell_count_bin"]))
        + abs(math.log(area_alt / area_edge))
        + abs(float(alternative["theta_midpoint_change_deg"]) - float(edge["theta_midpoint_change_deg"])) / 5.0
        + abs(float(alternative["range_midpoint_change_m"]) - float(edge["range_midpoint_change_m"]))
    )


def validate_pre_reference() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    required = [NODE_PATH, MATRIX_PATH, MATCHED_PATH, CASE_PATH, MANIFEST_PATH, LEDGER_PATH, SYNTHETIC_PATH]
    check(all(path.is_file() for path in required), "required_pre_reference_files", [str(p) for p in required if not p.is_file()], checks)
    synthetic = json.loads(SYNTHETIC_PATH.read_text(encoding="utf-8"))
    check(synthetic.get("status") == "PASS" and synthetic.get("tests_passed") == 5, "synthetic_tests_5_of_5", synthetic.get("tests_passed"), checks)
    nodes = pd.read_csv(NODE_PATH)
    matrix = pd.read_csv(MATRIX_PATH, low_memory=False)
    matched = pd.read_csv(MATCHED_PATH)
    cases = pd.read_csv(CASE_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))

    check(len(nodes) == 1117 and nodes["frame_uid"].nunique() == 23, "node_and_frame_count", {"nodes": len(nodes), "frames": nodes["frame_uid"].nunique()}, checks)
    check(set(matrix["condition"]) == {"P0", "ZERO"}, "matrix_conditions", sorted(matrix["condition"].unique()), checks)
    expected_rows = 0
    frame_counts = nodes.groupby("frame_index").size().to_dict()
    for frame in range(472, 494):
        expected_rows += int(frame_counts[frame]) * int(frame_counts[frame + 1]) * 2
    check(len(matrix) == expected_rows, "complete_all_by_all_matrix", {"actual": len(matrix), "expected": expected_rows}, checks)
    check(matrix["base_edge_id"].nunique() * 2 == len(matrix) and matrix["edge_id"].is_unique, "p0_zero_edge_parity", None, checks)
    check(not (PROHIBITED & set(nodes.columns)) and not (PROHIBITED & set(matrix.columns)) and not (PROHIBITED & set(matched.columns)), "no_manual_fields_pre_reference", sorted(PROHIBITED & (set(nodes.columns) | set(matrix.columns) | set(matched.columns))), checks)
    check(not bool(manifest.get("reference_loaded")) and not bool(ledger.get("reference_loaded")), "reference_not_loaded", None, checks)

    transport_error = finite_max_abs(matrix["transport_out_of_frame_or_invalid"] - (matrix["source_support_total"] - matrix["warped_support_in_destination_valid"]))
    valid_fraction_error = finite_max_abs(matrix["valid_transport_fraction"] - matrix["warped_support_in_destination_valid"] / matrix["source_support_total"])
    conditional_error = finite_max_abs(matrix["q95_conditional_valid_retention"] - matrix["q95_support_intersection_soft"] / matrix["warped_support_in_destination_valid"])
    source_retention_error = finite_max_abs(matrix["q95_source_total_retention"] - matrix["q95_support_intersection_soft"] / matrix["source_support_total"])
    check(max(transport_error, valid_fraction_error, conditional_error, source_retention_error) <= TOL, "denominator_formula_audit", {"transport": transport_error, "valid_fraction": valid_fraction_error, "conditional": conditional_error, "source_total": source_retention_error}, checks)
    check(bool((matrix["source_support_total"] > 0).all()) and bool((matrix["warped_support_in_destination_valid"] > 0).all()), "q95_denominators_positive", None, checks)
    check(bool((matrix["q95_support_intersection_soft"] <= matrix["warped_support_in_destination_valid"] + TOL).all()), "intersection_bounded_by_valid_support", None, checks)

    p0 = matrix[matrix["condition"].eq("P0")].set_index("base_edge_id")
    p0_groups = {
        (int(pair_index), str(source_region_id)): group
        for (pair_index, source_region_id), group in p0.groupby(
            ["pair_index", "source_region_id"], sort=False
        )
    }
    matched_ok = True
    matched_distance_error = 0.0
    for primary_id, group in matched.groupby("primary_base_edge_id", sort=False):
        primary = p0.loc[primary_id]
        source_pool = p0_groups[(int(primary["pair_index"]), str(primary["source_region_id"]))]
        expected_count = min(5, len(source_pool) - 1)
        if len(group) != expected_count or group["alternative_rank"].tolist() != list(range(1, expected_count + 1)):
            matched_ok = False
            break
        candidates: list[tuple[float, str]] = []
        for alt_id, alternative in source_pool.iterrows():
            if alt_id == primary_id:
                continue
            candidates.append((structural_distance(primary, alternative), str(alternative["destination_region_id"])))
        candidates.sort(key=lambda item: (item[0], item[1]))
        observed = list(zip(group["structural_distance"].astype(float), group["alternative_destination_region_id"].astype(str)))
        for (od, oi), (ed, ei) in zip(observed, candidates[:expected_count]):
            matched_distance_error = max(matched_distance_error, abs(od - ed))
            if oi != ei or abs(od - ed) > TOL:
                matched_ok = False
                break
        if not matched_ok:
            break
    check(matched_ok, "matched_structural_alternatives_exact", {"max_distance_error": matched_distance_error}, checks)
    selection_flags = cases["selection_used_reference"].map(bool_value)
    check(len(cases) == 9 and cases["case_type"].nunique() == 9 and not selection_flags.any(), "nine_deterministic_pre_reference_cases", cases["case_type"].tolist(), checks)
    pre_figures = sorted((OUTPUT_DIR / "figures" / "pre_reference").glob("*.png"))
    figures_readable = True
    for path in pre_figures:
        try:
            with Image.open(path) as image:
                image.verify()
        except Exception:
            figures_readable = False
            break
    check(len(pre_figures) == 9 and figures_readable, "nine_pre_reference_figures_readable", {"count": len(pre_figures)}, checks)
    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {"schema": "PERSON_M0A_PRE_REFERENCE_VALIDATION_V1", "status": status, "checks_passed": sum(c["status"] == "PASS" for c in checks), "checks_total": len(checks), "checks": checks}


def validate_post_reference() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    pre = validate_pre_reference()
    check(pre["status"] == "PASS", "pre_reference_validation_still_passes", pre["status"], checks)
    freeze = json.loads(HASH_PATH.read_text(encoding="utf-8"))
    payload_hash = freeze.pop("freeze_payload_sha256")
    check(sha256_object(freeze) == payload_hash, "pre_reference_freeze_payload_hash", None, checks)
    frozen_files_ok = all(sha256_file(WORKSPACE / item["path"]) == item["sha256"] for item in freeze["files"])
    check(frozen_files_ok, "pre_reference_files_unchanged", None, checks)
    required = [POST_SUPPORTED_PATH, POST_MATCHED_PATH, POST_CASE_PATH, POST_SUMMARY_PATH, EXECUTION_LEDGER_PATH, REPORT_PATH]
    check(all(path.is_file() for path in required), "required_post_reference_files", [str(p) for p in required if not p.is_file()], checks)
    supported = pd.read_csv(POST_SUPPORTED_PATH, low_memory=False)
    comparisons = pd.read_csv(POST_MATCHED_PATH)
    post_cases = pd.read_csv(POST_CASE_PATH)
    summary = json.loads(POST_SUMMARY_PATH.read_text(encoding="utf-8"))
    check(set(supported["condition"]) == {"P0", "ZERO"} and supported["base_edge_id"].nunique() * 2 == len(supported), "supported_p0_zero_parity", {"rows": len(supported)}, checks)
    rank_ok = True
    for _, group in supported.groupby(["pair_index", "condition", "source_region_id"]):
        ordered = group.sort_values(["q95_source_total_retention", "destination_region_id"], ascending=[False, True])
        if ordered["destination_rank"].tolist() != sorted(ordered["destination_rank"].tolist()):
            rank_ok = False
            break
    check(rank_ok and bool((supported["destination_rank"] >= 1).all()), "deterministic_supported_ranks", None, checks)
    check(bool(supported["source_manual_centers_json"].notna().all()) and bool(supported["destination_manual_centers_json"].notna().all()), "manual_centers_post_only_materialized", None, checks)
    check(bool(comparisons["frozen_alternative_preserved"].map(bool_value).all()), "matched_alternatives_preserved_after_reveal", None, checks)
    allowed_states = {"M0A_REGION_SUPPORT_TRANSPORT_WITH_P0_GAIN", "M0A_REGION_SUPPORT_TEMPORAL_PERSISTENCE_WITHOUT_CLEAR_P0_SPECIFIC_GAIN", "M0A_REGION_SUPPORT_TEMPORAL_DISCRIMINATION_WEAK", "M0A_MASK_WARP_OR_TRANSPORT_SEMANTICS_BLOCKED"}
    check(summary.get("final_m0a_state") in allowed_states and bool(summary.get("not_optical_sar_motion_consistency")), "final_state_and_semantic_boundary", summary.get("final_m0a_state"), checks)
    pre_figures = list((OUTPUT_DIR / "figures" / "pre_reference").glob("*.png"))
    post_figures = list((OUTPUT_DIR / "figures" / "post_reference").glob("*.png"))
    check(len(pre_figures) >= 9 and len(post_figures) >= 12, "real_case_figure_count", {"pre": len(pre_figures), "post": len(post_figures)}, checks)
    check(len(post_cases) >= 2, "post_reference_case_registry", post_cases["case_type"].tolist(), checks)
    ledger = json.loads(EXECUTION_LEDGER_PATH.read_text(encoding="utf-8"))
    stages = [event["stage"] for event in ledger["events"]]
    check(stages.index("REFERENCE_NOT_LOADED_PRE_REFERENCE_PHASE_CLOSED") < stages.index("MANUAL_REFERENCE_REVEALED_AFTER_FREEZE"), "reference_reveal_order", stages, checks)
    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {"schema": "PERSON_M0A_FINAL_VALIDATION_V1", "status": status, "checks_passed": sum(c["status"] == "PASS" for c in checks), "checks_total": len(checks), "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("pre-reference", "post-reference"), required=True)
    args = parser.parse_args()
    result = validate_pre_reference() if args.phase == "pre-reference" else validate_post_reference()
    destination = VALIDATION_PATH if args.phase == "pre-reference" else FINAL_VALIDATION_PATH
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
