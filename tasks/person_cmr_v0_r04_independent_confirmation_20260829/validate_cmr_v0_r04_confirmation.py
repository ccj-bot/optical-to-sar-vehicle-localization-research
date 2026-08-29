from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
from PIL import Image


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824" / "cmr_v0_r04_independent_confirmation"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    checks: list[dict[str, object]] = []

    def check(value: bool, name: str, details: object = "") -> None:
        checks.append({"check": name, "pass": bool(value), "details": details})

    required = [
        OUTPUT / "confirmation_protocol_and_evaluator_freeze.json",
        PRE / "control_bank_freeze.json",
        PRE / "pre_reference_output_hash_freeze.json",
        PRE / "r04_static_hypothesis_bank_pre_reference.parquet",
        PRE / "r04_structurally_matched_control_bank_pre_reference.parquet",
        PRE / "r04_cmr_v0_evidence_profiles_pre_reference.parquet",
        POST / "REFERENCE_REVEAL_MARKER.json",
        POST / "r04_reference_supported_sar_edges.csv",
        POST / "r04_supported_vs_matched_wrong_pairwise_evaluation.parquet",
        POST / "r04_reference_free_structurally_matched_controls.parquet",
        POST / "r04_candidate_separation_by_window.csv",
        POST / "r04_cluster_aware_summary.csv",
        POST / "r04_offline_likely_supported_branch_evaluation.csv",
        POST / "r04_unresolved_branch_evidence_profiles.csv",
        POST / "r04_visual_case_registry.csv",
        POST / "R04_CONFIRMATION_CASE_CONTACT_SHEET.jpg",
        POST / "CMR_V0_R04_MULTIMODAL_VISUAL_REVIEW_LEDGER.md",
        POST / "cmr_v0_r04_confirmation_summary.json",
        POST / "CMR_V0_R04_FINAL_CONFIRMATION_REPORT.md",
        OUTPUT / "cmr_v0_r04_final_manifest.json",
    ]
    for path in required:
        check(path.exists(), f"exists::{path.name}")

    if any(not path.exists() for path in required):
        payload = {"schema": "PERSON_CMR_V0_R04_INDEPENDENT_VALIDATION_V1", "status": "FAIL", "checks": checks}
        (OUTPUT / "cmr_v0_r04_independent_validation.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(1)

    protocol = json.loads((OUTPUT / "confirmation_protocol_and_evaluator_freeze.json").read_text(encoding="utf-8"))
    control_freeze = json.loads((PRE / "control_bank_freeze.json").read_text(encoding="utf-8"))
    pre_manifest = json.loads((PRE / "pre_reference_output_hash_freeze.json").read_text(encoding="utf-8"))
    reveal = json.loads((POST / "REFERENCE_REVEAL_MARKER.json").read_text(encoding="utf-8"))
    summary = json.loads((POST / "cmr_v0_r04_confirmation_summary.json").read_text(encoding="utf-8"))
    final_manifest = json.loads((OUTPUT / "cmr_v0_r04_final_manifest.json").read_text(encoding="utf-8"))
    static = pd.read_parquet(PRE / "r04_static_hypothesis_bank_pre_reference.parquet")
    controls = pd.read_parquet(PRE / "r04_structurally_matched_control_bank_pre_reference.parquet")
    profiles = pd.read_parquet(PRE / "r04_cmr_v0_evidence_profiles_pre_reference.parquet")
    evaluation = pd.read_parquet(POST / "r04_supported_vs_matched_wrong_pairwise_evaluation.parquet")
    cases = pd.read_csv(POST / "r04_visual_case_registry.csv")

    check(protocol["reference_loaded"] is False and protocol["outcome_accessed"] is False, "protocol_frozen_pre_reveal")
    check(control_freeze["reference_loaded"] is False and control_freeze["cmr_outcome_used"] is False, "controls_frozen_pre_outcome")
    check(pre_manifest["reference_loaded"] is False and pre_manifest["outcome_accessed"] is False, "pre_reference_closed_without_outcome")
    check(reveal["status"] == "REFERENCE_REVEAL_STARTED_AFTER_PRE_REFERENCE_HASH_FREEZE", "reveal_after_pre_freeze")
    check(reveal["pre_reference_manifest_sha256"] == sha256_file(PRE / "pre_reference_output_hash_freeze.json"), "reveal_links_frozen_pre_manifest")

    frozen_failures = []
    for item in protocol["files"].values():
        path = WORKSPACE / item["path"]
        if not path.exists() or sha256_file(path) != item["sha256"]:
            frozen_failures.append(item["path"])
    check(not frozen_failures, "protocol_evaluator_mechanism_hashes_match", frozen_failures)

    pre_failures = []
    for item in pre_manifest["files"]:
        path = WORKSPACE / item["path"]
        if not path.exists() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != item["sha256"]:
            pre_failures.append(item["path"])
    check(not pre_failures, "pre_reference_files_hash_match", pre_failures)

    forbidden = {
        "target_id",
        "physical_target_id",
        "reference_supported",
        "supported_target_id",
        "cross_modal_residual_relation",
        "soft_iou",
    }
    check(not (forbidden & set(controls.columns)), "control_bank_forbidden_fields_absent", sorted(forbidden & set(controls.columns)))
    check(not bool(controls["selection_used_reference"].any()), "control_selection_reference_free")
    check(not bool(controls["selection_used_cmr_outcome"].any()), "control_selection_cmr_outcome_free")
    check(int(controls.groupby("primary_hypothesis_id").size().max()) <= 5, "control_count_max_five")
    check(set(controls["primary_hypothesis_id"]).issubset(set(static["hypothesis_id"])), "control_primaries_in_static_bank")
    check(set(controls["control_hypothesis_id"]).issubset(set(static["hypothesis_id"])), "controls_in_static_bank")

    check(set(profiles["run_id"]) == {"R04ZF"}, "pre_reference_profiles_r04_only")
    check(pre_manifest["eligible_windows"] == 98, "eligible_windows_98")
    check(pre_manifest["eligible_branch_instances"] == 166, "eligible_branches_166")
    check(pre_manifest["common_window_count"] == 98, "common_observability_complete")
    check(pre_manifest["optical_branch_count"] == 166, "optical_branch_observability_complete")
    check(len(profiles) == pre_manifest["cross_modal_hypothesis_count"], "profile_count_matches_manifest")
    check(profiles["residual_mid_descriptor_deg"].notna().all(), "optical_continuous_residual_retained")
    check(profiles["sar_residual_mid_descriptor_deg"].notna().all(), "sar_continuous_residual_retained")
    check(profiles["common_uncertainty_deg"].notna().all(), "common_uncertainty_retained")
    check(profiles["p0_angular_uncertainty_deg"].notna().all(), "p0_uncertainty_retained")
    check(profiles["optical_tendency_state"].notna().all(), "optical_tendency_retained")
    check(profiles["sar_tendency_state"].notna().all(), "sar_tendency_retained")
    check(profiles["cross_modal_leaning_relation"].notna().all(), "cross_modal_tendency_retained")
    check(not bool(profiles["residual_direction_used_for_pruning"].any()), "no_pruning")
    check(not bool(profiles["identity_assignment_performed"].any()), "no_identity_assignment")
    check(not bool(profiles["final_localization_performed"].any()), "no_final_localization")

    allowed_separation = {"STRONG_SEPARATION", "ASYMMETRIC_SEPARATION", "TENDENCY_SEPARATION", "NO_SEPARATION", "REVERSED_SEPARATION"}
    allowed_outcomes = {"SAR_EDGE_RESCUE", "CONFIRMATION", "HARM", "CONFLICT", "NO_INFORMATION"}
    check(set(evaluation["candidate_separation"]).issubset(allowed_separation), "candidate_separation_states_frozen")
    check(set(evaluation["strict_outcome"]).issubset(allowed_outcomes), "strict_outcome_states_frozen")
    check(evaluation["sar_only_preference"].eq("SAR_ONLY_NO_PREFERENCE_STATIC_FEASIBLE").all(), "sar_only_no_hidden_ranker")
    check(evaluation["strict_branch_specific_evaluation"].eq("STRICT_BRANCH_SPECIFIC_EVALUATION_UNAVAILABLE").all(), "strict_branch_claim_unavailable")
    check(not bool(evaluation["mechanism_recomputed_after_reveal"].any()), "mechanism_not_recomputed_after_reveal")
    check(summary["mechanism_modified_after_reveal"] is False, "summary_mechanism_unmodified")
    check(summary["strict_branch_specific_evaluation"] == "STRICT_BRANCH_SPECIFIC_EVALUATION_UNAVAILABLE", "summary_branch_specificity_layered")
    check(sum(summary["candidate_separation_counts"].values()) == len(evaluation), "separation_denominator_complete")
    check(sum(summary["strict_outcome_counts"].values()) == len(evaluation), "strict_outcome_denominator_complete")

    check(len(cases) == 16, "sixteen_visual_case_slots")
    check(cases["status"].isin(["OBSERVED", "CATEGORY_NOT_OBSERVED"]).all(), "visual_case_status_allowed")
    missing_images = []
    dimensions = []
    for path_text in cases.loc[cases["status"] == "OBSERVED", "path"]:
        path = WORKSPACE / path_text
        if not path.exists():
            missing_images.append(path_text)
        else:
            with Image.open(path) as image:
                dimensions.append(image.size)
    check(not missing_images, "visual_case_images_exist", missing_images)
    check(all(width >= 2000 and height >= 1000 for width, height in dimensions), "visual_pair_render_dimensions", dimensions[:5])

    prohibited = summary["prohibited_outputs"]
    check(not any(bool(value) for value in prohibited.values()), "prohibited_outputs_false", prohibited)

    final_failures = []
    for item in final_manifest["files"]:
        path = WORKSPACE / item["path"]
        if not path.exists() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != item["sha256"]:
            final_failures.append(item["path"])
    check(not final_failures, "final_manifest_files_hash_match", final_failures)

    failed = [item for item in checks if not item["pass"]]
    payload = {
        "schema": "PERSON_CMR_V0_R04_INDEPENDENT_VALIDATION_V1",
        "status": "PASS" if not failed else "FAIL",
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "failed_checks": failed,
        "checks": checks,
    }
    (OUTPUT / "cmr_v0_r04_independent_validation.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
