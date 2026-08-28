from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK_DIR = SCRIPT.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OUTPUT = STUDY / "m0b1_v2_cross_modal_direction_discrimination"
FREEZE = OUTPUT / "protocol_freeze.json"
PRE_MANIFEST = OUTPUT / "pre_reference_manifest.json"
PRE_BANK = OUTPUT / "direction_hypothesis_bank_pre_reference.parquet"
PRE_OPTICAL = OUTPUT / "optical_descriptors_unique_pre_reference.csv"
PRE_SCENE = OUTPUT / "scene_common_direction_audit_pre_reference.csv"
PRE_ATLAS_CANDIDATES = OUTPUT / "optical_direction_diversity_atlas_future_candidate_windows_pre_reference.csv"
OLD_PROTOCOL = STUDY / "m0b1_r02_raw_fragment_angular_direction_diagnostic" / "M0B1_R02_RAW_FRAGMENT_ANGULAR_DIRECTION_PROTOCOL_FROZEN_BEFORE_RUN.md"
OLD_SUMMARY = STUDY / "m0b1_r02_raw_fragment_angular_direction_diagnostic" / "post_reference_summary.json"
FINAL_SUMMARY = OUTPUT / "final_summary.json"
FINAL_MANIFEST = OUTPUT / "final_output_manifest.json"
PRE_VALIDATION = OUTPUT / "pre_reference_independent_validation.json"
FINAL_VALIDATION = OUTPUT / "final_independent_validation.json"
TOL = 1e-12


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


def check(condition: bool, name: str, checks: list[dict[str, Any]], details: Any = "") -> None:
    checks.append({"check": name, "pass": bool(condition), "details": details})


def validate_freeze(checks: list[dict[str, Any]]) -> dict[str, Any]:
    freeze = read_json(FREEZE)
    check(not freeze["reference_loaded"], "freeze_reference_false", checks)
    check(freeze["prohibited_actions_executed"] == [], "freeze_no_prohibited_actions", checks)
    for item in freeze["files"]:
        path = WORKSPACE / item["path"]
        check(path.is_file(), f"frozen_exists::{path.name}", checks)
        if path.is_file():
            check(path.stat().st_size == item["bytes"], f"frozen_size::{path.name}", checks)
            check(sha256_file(path) == item["sha256"], f"frozen_hash::{path.name}", checks)
    return freeze


def finish(checks: list[dict[str, Any]], schema: str, path: Path) -> dict[str, Any]:
    failed = [item for item in checks if not item["pass"]]
    payload = {
        "schema": schema,
        "status": "PASS" if not failed else "FAIL",
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "failed_checks": [item["check"] for item in failed],
        "checks": checks,
    }
    write_json(path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)
    return payload


def validate_pre() -> None:
    checks: list[dict[str, Any]] = []
    freeze = validate_freeze(checks)
    manifest = read_json(PRE_MANIFEST)
    check(not manifest["reference_loaded"], "pre_manifest_reference_false", checks)
    check(not manifest["reference_sources_opened"], "pre_manifest_reference_sources_closed", checks)
    check(sha256_file(FREEZE) == manifest["protocol_freeze_sha256"], "pre_manifest_freeze_hash", checks)
    for item in manifest["files"]:
        path = WORKSPACE / item["path"]
        check(path.is_file(), f"pre_exists::{path.name}", checks)
        if path.is_file():
            check(path.stat().st_size == item["bytes"], f"pre_size::{path.name}", checks)
            check(sha256_file(path) == item["sha256"], f"pre_hash::{path.name}", checks)

    bank = pd.read_parquet(PRE_BANK)
    available = bank["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE")
    recomputed_left = bank["destination_raw_theta_low_deg"] - bank["source_raw_theta_low_deg"]
    recomputed_right = bank["destination_raw_theta_high_deg"] - bank["source_raw_theta_high_deg"]
    recomputed_mid = (
        bank["destination_raw_theta_low_deg"]
        + bank["destination_raw_theta_high_deg"]
        - bank["source_raw_theta_low_deg"]
        - bank["source_raw_theta_high_deg"]
    ) / 2.0
    recomputed_width = (
        bank["destination_raw_theta_high_deg"]
        - bank["destination_raw_theta_low_deg"]
        - bank["source_raw_theta_high_deg"]
        + bank["source_raw_theta_low_deg"]
    )
    check(np.nanmax(np.abs(bank.loc[available, "d_left_o_deg_v2"] - recomputed_left[available])) <= TOL, "optical_d_left_formula", checks)
    check(np.nanmax(np.abs(bank.loc[available, "d_right_o_deg_v2"] - recomputed_right[available])) <= TOL, "optical_d_right_formula", checks)
    check(np.nanmax(np.abs(bank.loc[available, "d_mid_o_deg_v2"] - recomputed_mid[available])) <= TOL, "optical_d_mid_formula", checks)
    check(np.nanmax(np.abs(bank.loc[available, "d_width_o_deg_v2"] - recomputed_width[available])) <= TOL, "optical_d_width_formula", checks)
    check(bank.loc[~available, "d_left_o_deg_v2"].isna().all(), "unavailable_not_zero_left", checks)
    check(bank.loc[~available, "cross_modal_direction_state_v2"].eq("DIRECTION_UNAVAILABLE").all(), "unavailable_cross_direction", checks)
    check(not bank["hypothesis_pruned"].astype(bool).any(), "no_hypothesis_pruning", checks)
    check(not bank["reference_used"].astype(bool).any(), "pre_bank_reference_false", checks)
    prohibited = {"physical_target_id", "manual_target_id", "supported_target_ids", "evaluation_group"}.intersection(bank.columns)
    check(not prohibited, "pre_bank_no_post_reference_columns", checks, sorted(prohibited))

    optical = pd.read_csv(PRE_OPTICAL)
    check(len(optical) == 183, "deduplicated_optical_pair_count", checks, len(optical))
    nominal = optical[optical["timing_condition"].eq("NOMINAL")]
    check(len(nominal) > 0 and nominal["optical_dynamic_state_v2"].eq("OPTICAL_COHERENT_POSITIVE_SHIFT").all(), "r02_nominal_all_positive", checks)
    check(
        optical.groupby("timing_condition")["optical_dynamic_state_v2"].apply(lambda x: x.eq("OPTICAL_COHERENT_POSITIVE_SHIFT").all()).all(),
        "all_fixed_timing_optical_sign_positive",
        checks,
    )
    scene = pd.read_csv(PRE_SCENE)
    check(scene["reference_used"].astype(bool).eq(False).all(), "scene_audit_reference_false", checks)
    check(scene["active_raw_fragment_count"].ge(1).all(), "scene_active_fragment_denominator", checks)
    check(scene["global_optical_direction_state"].eq("OPTICAL_COHERENT_POSITIVE_SHIFT").all(), "scene_global_baseline_positive", checks)
    check(bank.loc[available, "branch_vs_global_direction_relation"].eq("BRANCH_DIRECTION_EQUALS_GLOBAL_BASELINE").all(), "branch_equals_global_all_available", checks)

    atlas = pd.read_csv(PRE_ATLAS_CANDIDATES)
    check(len(atlas) > 0, "atlas_future_windows_found", checks, len(atlas))
    check((atlas["active_raw_fragment_count"].ge(2) & atlas["positive_count"].ge(1) & atlas["negative_count"].ge(1)).all(), "atlas_candidate_eligibility", checks)
    check(atlas["reference_used"].astype(bool).eq(False).all(), "atlas_reference_false", checks)

    old_state = read_json(OLD_SUMMARY)["state"]
    check(old_state == "M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT", "frozen_predecessor_state_unchanged", checks, old_state)
    old_hash = next(item["sha256"] for item in freeze["files"] if item["path"].endswith(OLD_PROTOCOL.name))
    check(sha256_file(OLD_PROTOCOL) == old_hash, "frozen_predecessor_protocol_unchanged", checks)
    finish(checks, "PERSON_M0B1_V2_PRE_REFERENCE_VALIDATION_V1", PRE_VALIDATION)


def validate_post() -> None:
    checks: list[dict[str, Any]] = []
    validate_freeze(checks)
    pre_manifest = read_json(PRE_MANIFEST)
    for item in pre_manifest["files"]:
        path = WORKSPACE / item["path"]
        check(path.is_file() and sha256_file(path) == item["sha256"], f"pre_unchanged_after_reveal::{path.name}", checks)
    pre_validation = read_json(PRE_VALIDATION)
    check(pre_validation["status"] == "PASS", "pre_validation_still_passes", checks)

    summary = read_json(FINAL_SUMMARY)
    check(summary["primary_state"] in {
        "M0B1_V2_DIRECTION_SIGNAL_SCENE_COMMON_NOT_BRANCH_SPECIFIC",
        "M0B1_V2_DIRECTION_DISCRIMINATION_NOT_ESTABLISHED",
    }, "allowed_primary_state", checks, summary["primary_state"])
    check("M0B1_V2_RAW_BRANCH_EVALUATION_UNRESOLVED" in summary["secondary_states"], "raw_branch_unresolved_state", checks)
    check(not summary["person_or_branch_specificity_established"], "no_branch_specific_claim", checks)
    check(not summary["branch_specific_increment_over_global_observed"], "no_branch_increment_over_global", checks)
    check(summary["branch_decisions_different_from_global"] == 0, "branch_global_decision_parity", checks)
    check(summary["raw_fragment_target_evaluator_status"] == "UNRESOLVED", "raw_evaluator_honest", checks)
    check(summary["offline_review_state_counts"].get("UNRESOLVED", 0) == summary["offline_review_pack_count"], "all_review_packs_unresolved", checks)
    check(not summary["counterfactual_admissibility_executed"], "counterfactual_not_executed", checks)
    check(not summary["recommend_magnitude_next"], "magnitude_not_recommended", checks)
    check(summary["recommend_common_apparent_motion_next"], "common_motion_recommended", checks)
    check(not any(summary["prohibited_claims"].values()), "prohibited_claims_false", checks, summary["prohibited_claims"])

    pairwise = pd.read_csv(OUTPUT / "supported_vs_matched_null_cluster_decisions.csv")
    nominal = pairwise[pairwise["timing_condition"].eq("NOMINAL")]
    check(len(nominal) == 30, "nominal_matched_cluster_denominator", checks, len(nominal))
    check(not nominal["branch_decision_differs_from_global"].astype(bool).any(), "nominal_branch_global_parity", checks)
    check(nominal["direction_pairwise_decision"].eq("DIRECTION_FAVORS_NULL").sum() == 0, "nominal_no_favors_null", checks)
    check(nominal["joint_category"].eq("DIRECTION_RESCUE").sum() == 0, "nominal_no_sar_only_rescue", checks)

    evaluator = read_json(OUTPUT / "raw_fragment_target_evaluator_audit.json")
    check(not evaluator["direct_raw_fragment_to_manual_target_source_found"], "no_direct_raw_target_source", checks)
    check(not evaluator["optical_person_id_used_as_truth"], "optical_person_id_not_truth", checks)
    check(not evaluator["runtime_branch_relabelled"], "runtime_branch_not_relabelled", checks)
    cases = pd.read_csv(OUTPUT / "real_case_registry.csv")
    check(len(cases) == 17, "seventeen_case_slots", checks, len(cases))
    check(cases["selection_status"].isin(["CATEGORY_OBSERVED", "CATEGORY_NOT_OBSERVED"]).all(), "case_status_explicit", checks)
    for path_text in cases.loc[cases["selection_status"].eq("CATEGORY_OBSERVED"), "figure"]:
        path = WORKSPACE / path_text
        image = cv2.imread(str(path))
        check(image is not None and image.size > 0, f"case_readable::{path.name}", checks)
    contact = cv2.imread(str(OUTPUT / "figures" / "POST_REFERENCE_CASE_CONTACT_SHEET.png"))
    check(contact is not None and contact.size > 0, "contact_sheet_readable", checks)

    manifest = read_json(FINAL_MANIFEST)
    check(manifest["reference_loaded"], "final_manifest_reference_true", checks)
    check(not manifest["hypotheses_pruned"], "final_manifest_no_pruning", checks)
    check(not manifest["magnitude_fit"], "final_manifest_no_magnitude_fit", checks)
    check(not manifest["timing_shift_selected"], "final_manifest_no_timing_selection", checks)
    check(not manifest["identity_assignment_performed"], "final_manifest_no_identity_assignment", checks)
    for item in manifest["files"]:
        path = WORKSPACE / item["path"]
        check(path.is_file(), f"final_exists::{path.name}", checks)
        if path.is_file():
            check(sha256_file(path) == item["sha256"], f"final_hash::{path.name}", checks)
    finish(checks, "PERSON_M0B1_V2_FINAL_VALIDATION_V1", FINAL_VALIDATION)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pre", action="store_true")
    group.add_argument("--post", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_pre() if args.pre else validate_post()


if __name__ == "__main__":
    main()
