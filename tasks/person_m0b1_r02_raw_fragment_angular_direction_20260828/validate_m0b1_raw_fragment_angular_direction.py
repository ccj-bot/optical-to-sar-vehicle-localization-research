"""Independent validator for M0B1 interval angular-direction outputs."""

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
OUTPUT_DIR = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824" / "m0b1_r02_raw_fragment_angular_direction_diagnostic"
M0A_ROOT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824" / "m0a_r02_lag1_q95_region_support_transport_pilot"
TOPOLOGY_EDGES = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824" / "p1e_sar_only_response_interface" / "shell_uncertainty_region_topology_v1" / "gt_blind_shell_region_pixel_edges_pre_reference.csv"
FREEZE = OUTPUT_DIR / "protocol_freeze.json"
PROTOCOL = OUTPUT_DIR / "M0B1_R02_RAW_FRAGMENT_ANGULAR_DIRECTION_PROTOCOL_FROZEN_BEFORE_RUN.md"
TOL = 1e-12


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def check(condition: bool, name: str, details: Any, checks: list[dict[str, Any]]) -> None:
    checks.append({"name": name, "status": "PASS" if condition else "FAIL", "details": details})


def validate_pre() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    check(freeze["status"] == "FROZEN_BEFORE_RUN", "protocol_frozen", freeze["status"], checks)
    check(sha256_file(PROTOCOL) == freeze["protocol_sha256"], "protocol_hash", freeze["protocol_sha256"], checks)
    check(
        sha256_file(TASK_DIR / "run_m0b1_raw_fragment_angular_direction.py") == freeze["runner_sha256"],
        "runner_hash",
        freeze["runner_sha256"],
        checks,
    )
    check(sha256_file(SCRIPT_PATH) == freeze["validator_sha256"], "validator_hash", freeze["validator_sha256"], checks)
    input_ok = all(sha256_file(WORKSPACE / item["path"]) == item["sha256"] for item in freeze["input_hashes"])
    check(input_ok, "frozen_inputs_unchanged", None, checks)

    query = pd.read_csv(OUTPUT_DIR / "timing_query_table_pre_reference.csv")
    relations = pd.read_csv(OUTPUT_DIR / "static_endpoint_relations_pre_reference.csv")
    hypotheses = pd.read_csv(OUTPUT_DIR / "dynamic_hypotheses_pre_reference.csv")
    raw_controls = pd.read_csv(OUTPUT_DIR / "raw_fragment_alternative_controls_pre_reference.csv")
    static_controls = pd.read_csv(OUTPUT_DIR / "static_shell_matched_controls_pre_reference.csv")
    summary = json.loads((OUTPUT_DIR / "pre_reference_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((OUTPUT_DIR / "pre_reference_manifest.json").read_text(encoding="utf-8"))

    prohibited = {"physical_target_id", "target_id", "source_manual_centers_json", "destination_manual_centers_json", "optical_person_id"}
    check(not (prohibited & set(hypotheses.columns)), "pre_reference_schema_no_reference_or_stitched_identity", sorted(prohibited & set(hypotheses.columns)), checks)
    check(not hypotheses["reference_used"].astype(bool).any(), "pre_reference_reference_false", None, checks)
    check(not hypotheses["identity_assignment_performed"].astype(bool).any(), "no_identity_assignment", None, checks)
    check(not hypotheses["hypothesis_pruned"].astype(bool).any(), "no_hypothesis_pruning", None, checks)
    check(set(query["timing_condition"]) == set(freeze["timing_conditions"]), "five_timing_conditions", sorted(query["timing_condition"].unique()), checks)
    check(len(query) == 23 * 5, "complete_timing_query_denominator", len(query), checks)

    existing = pd.read_csv(TOPOLOGY_EDGES)
    existing = existing[
        existing["run_id"].eq("R02ZF")
        & existing["temporal_policy"].eq("SAME_FRAME")
        & existing["guard_variant"].eq("CURRENT_G6")
        & existing["percentile_tag"].eq("Q095")
        & existing["frame_index"].between(472, 494)
    ]
    observed = relations[relations["timing_condition"].eq("NOMINAL")]
    expected_keys = set(zip(existing["frame_uid"], existing["track_id"], existing["region_id"]))
    observed_keys = set(zip(observed["frame_uid"], observed["track_id"], observed["region_id"]))
    check(expected_keys == observed_keys, "nominal_pixel_topology_exact_key_parity", {"expected": len(expected_keys), "observed": len(observed_keys)}, checks)
    check(relations["pixel_intersection_used"].astype(bool).all(), "pixel_intersection_only", None, checks)

    feasible = hypotheses[hypotheses["static_feasible"].astype(bool)]
    categories = {
        "ANGULAR_DYNAMIC_AVAILABLE",
        "ANGULAR_DYNAMIC_UNAVAILABLE_SAME_OPTICAL_SAMPLE",
        "ANGULAR_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK",
    }
    check(set(feasible["angular_availability_state"]).issubset(categories), "feasible_availability_categories", sorted(feasible["angular_availability_state"].unique()), checks)
    same = feasible[feasible["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_SAME_OPTICAL_SAMPLE")]
    check(bool((same["source_track_id"] == same["destination_track_id"]).all()) and bool((same["source_optical_frame_index"] == same["destination_optical_frame_index"]).all()), "same_sample_not_zero_motion", len(same), checks)
    breaks = feasible[feasible["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK")]
    check(bool((breaks["source_track_id"] != breaks["destination_track_id"]).all()), "fragment_break_requires_distinct_raw_ids", len(breaks), checks)
    available = feasible[feasible["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE")]
    check(bool((available["source_track_id"] == available["destination_track_id"]).all()) and bool((available["source_optical_frame_index"] != available["destination_optical_frame_index"]).all()), "dynamic_available_distinct_sample_same_raw_fragment", len(available), checks)

    if len(available):
        optical_low_error = np.max(np.abs(available["optical_delta_interval_low_deg"] - (available["destination_raw_theta_low_deg"] - available["source_raw_theta_high_deg"])))
        optical_high_error = np.max(np.abs(available["optical_delta_interval_high_deg"] - (available["destination_raw_theta_high_deg"] - available["source_raw_theta_low_deg"])))
        sar_low_error = np.max(np.abs(available["sar_delta_interval_low_deg"] - (available["destination_theta_min_deg"] - available["source_theta_max_deg"])))
        sar_high_error = np.max(np.abs(available["sar_delta_interval_high_deg"] - (available["destination_theta_max_deg"] - available["source_theta_min_deg"])))
    else:
        optical_low_error = optical_high_error = sar_low_error = sar_high_error = 0.0
    check(max(optical_low_error, optical_high_error) <= TOL, "optical_interval_formula", max(optical_low_error, optical_high_error), checks)
    check(max(sar_low_error, sar_high_error) <= TOL, "sar_interval_formula", max(sar_low_error, sar_high_error), checks)

    expected_optical = np.where(
        available["optical_delta_interval_low_deg"] > TOL,
        "OPTICAL_POSITIVE",
        np.where(available["optical_delta_interval_high_deg"] < -TOL, "OPTICAL_NEGATIVE", "OPTICAL_DIRECTION_INDETERMINATE"),
    )
    check(bool((available["optical_direction_state"].to_numpy() == expected_optical).all()), "optical_direction_classification", None, checks)
    expected_sar = np.where(
        feasible["sar_delta_interval_low_deg"] > TOL,
        "SAR_POSITIVE",
        np.where(feasible["sar_delta_interval_high_deg"] < -TOL, "SAR_NEGATIVE", "SAR_DIRECTION_INDETERMINATE"),
    )
    check(bool((feasible["sar_direction_state"].to_numpy() == expected_sar).all()), "sar_direction_classification", None, checks)
    check(not raw_controls.get("direction_used_for_selection", pd.Series(dtype=bool)).astype(bool).any(), "raw_controls_direction_blind", len(raw_controls), checks)
    check(not static_controls.get("direction_used_for_selection", pd.Series(dtype=bool)).astype(bool).any(), "static_controls_direction_blind", len(static_controls), checks)
    check(not raw_controls.get("reference_used_for_selection", pd.Series(dtype=bool)).astype(bool).any() and not static_controls.get("reference_used_for_selection", pd.Series(dtype=bool)).astype(bool).any(), "controls_reference_blind", None, checks)
    manifest_ok = not manifest["reference_loaded"] and not manifest["reference_files_opened"] and all(sha256_file(WORKSPACE / item["path"]) == item["sha256"] for item in manifest["files"])
    check(manifest_ok, "pre_reference_manifest_and_hashes", None, checks)
    check(summary["nominal_pixel_topology_key_parity"], "summary_reports_topology_parity", summary["nominal_pixel_topology_key_parity"], checks)
    return finish(checks, "PERSON_M0B1_PRE_REFERENCE_VALIDATION_V1")


def validate_post() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    pre = validate_pre()
    check(pre["status"] == "PASS", "pre_reference_validation_still_passes", pre["status"], checks)
    evaluated = pd.read_csv(OUTPUT_DIR / "post_reference_hypothesis_evaluation.csv")
    direction = pd.read_csv(OUTPUT_DIR / "direction_state_summary.csv")
    timing = pd.read_csv(OUTPUT_DIR / "timing_sensitivity.csv")
    cases = pd.read_csv(OUTPUT_DIR / "real_case_registry.csv")
    summary = json.loads((OUTPUT_DIR / "post_reference_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((OUTPUT_DIR / "final_output_manifest.json").read_text(encoding="utf-8"))
    ledger = json.loads((OUTPUT_DIR / "execution_ledger.json").read_text(encoding="utf-8"))

    check(set(direction["timing_condition"]) == set(json.loads(FREEZE.read_text(encoding="utf-8"))["timing_conditions"]), "all_timing_conditions_reported", sorted(direction["timing_condition"].unique()), checks)
    required_counts = {"N_total_hypothesis_records", "N_dynamic_available", "N_same_optical_sample", "N_fragment_break", "N_observation_unavailable", "N_direction_indeterminate", "N_direction_concordant", "N_direction_contradictory"}
    check(required_counts.issubset(direction.columns), "full_direction_denominators", sorted(required_counts - set(direction.columns)), checks)
    check(len(cases) == 12, "twelve_deterministic_case_slots", len(cases), checks)
    pre_figures = sorted((OUTPUT_DIR / "figures" / "pre_reference_no_manual_overlay").glob("*.png"))
    post_figures = sorted((OUTPUT_DIR / "figures" / "post_reference_manual_overlay").glob("*.png"))
    readable = True
    for path in pre_figures + post_figures:
        try:
            with Image.open(path) as image:
                image.verify()
        except Exception:
            readable = False
    check(len(pre_figures) == 12 and len(post_figures) == 12 and readable, "paired_case_figures_readable", {"pre": len(pre_figures), "post": len(post_figures)}, checks)
    check(not summary["incremental_angular_signal_observed"], "no_unsupported_incremental_claim", summary["state"], checks)
    check(not summary["pareto_pruning_performed"] and not summary["hypothesis_rejection_by_direction"], "pareto_and_direction_do_not_prune", None, checks)
    check(summary["raw_fragment_target_evaluator_status"] == "NOT_ESTABLISHED", "raw_fragment_post_reference_interface_honest", summary["raw_fragment_target_evaluator_status"], checks)
    check(not summary["timing_calibrated"] and not summary["timing_shift_selected"], "timing_not_fit_or_selected", None, checks)
    check(not summary["recommend_m0b2"], "stop_before_m0b2", None, checks)
    check(not any(summary["prohibited_claims"].values()), "prohibited_claims_false", summary["prohibited_claims"], checks)
    stages = [event["stage"] for event in ledger["events"]]
    check(stages.index("PRE_REFERENCE_MANIFEST_FROZEN_REFERENCE_STILL_NOT_LOADED") < stages.index("MANUAL_REFERENCE_REVEALED_AFTER_FREEZE"), "reference_reveal_order", stages, checks)
    manifest_ok = manifest["reference_loaded"] and not manifest["m0b2_executed"] and not manifest["hypotheses_pruned"] and all(sha256_file(WORKSPACE / item["path"]) == item["sha256"] for item in manifest["files"])
    check(manifest_ok, "final_manifest_hashes_and_boundaries", None, checks)
    check(len(timing) == 5, "five_timing_summary_rows", len(timing), checks)
    supported = evaluated[evaluated["evaluation_group"].eq("REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED")]
    check(supported["base_edge_id"].nunique() == 6 and supported["pair_index"].nunique() == 3, "supported_cluster_accounting", {"edges": supported["base_edge_id"].nunique(), "pairs": supported["pair_index"].nunique()}, checks)
    return finish(checks, "PERSON_M0B1_POST_REFERENCE_VALIDATION_V1")


def finish(checks: list[dict[str, Any]], schema: str) -> dict[str, Any]:
    result = {
        "schema": schema,
        "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "checks_passed": sum(item["status"] == "PASS" for item in checks),
        "checks_total": len(checks),
        "checks": checks,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("pre-reference", "post-reference"), required=True)
    args = parser.parse_args()
    result = validate_pre() if args.phase == "pre-reference" else validate_post()
    path = OUTPUT_DIR / ("pre_reference_validation.json" if args.phase == "pre-reference" else "independent_validation.json")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
