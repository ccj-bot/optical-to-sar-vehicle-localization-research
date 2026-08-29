from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import cv2
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference"
V1_ROOT = WORKSPACE / "output" / "person_terg_d0r_set_valued_graph_representation_repair_20260829"
R0_ROOT = WORKSPACE / "output" / "person_terg_r0_set_valued_explanation_constraint_propagation_20260829"
EXPECTED_ROUTE = "RELATIONAL_INFORMATION_REAL_BUT_ABSOLUTE_ANCHOR_REQUIRED"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, checks: list[dict[str, Any]]) -> None:
    checks.append({"check": message, "passed": bool(condition)})
    if not condition:
        raise AssertionError(message)


def current_frozen_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(WORKSPACE)).replace("\\", "/"): sha256_file(path)
        for root in [V1_ROOT, R0_ROOT]
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def main() -> None:
    checks: list[dict[str, Any]] = []
    required = [
        PRE / "excluded_pair_visual_case_registry_pre_reference.parquet",
        PRE / "selected_excluded_pair_family_memberships_pre_reference.parquet",
        PRE / "excluded_pair_frame_relation_audit_pre_reference.parquet",
        PRE / "episode_assignment_pre_reference.parquet",
        PRE / "underlying_temporal_episode_registry_pre_reference.parquet",
        PRE / "evidence_availability_map_pre_reference.parquet",
        PRE / "evidence_role_registry_pre_reference.parquet",
        PRE / "global_partial_order_audit_pre_reference.parquet",
        PRE / "response_component_family_diagnosis_pre_reference.parquet",
        PRE / "frozen_terg_v1_r0_input_hashes.json",
        PRE / "pre_reference_hash_manifest.csv",
        PRE / "pre_reference_freeze_summary.json",
        POST / "excluded_pair_likely_vs_alternative_case_registry_post_reference.parquet",
        POST / "direct_visual_verification_verdict_post_reference.parquet",
        POST / "one_track_one_family_diagnosis_post_reference.parquet",
        POST / "shared_transition_diagnostic_post_reference.parquet",
        POST / "zero_anchor_baseline_post_reference.parquet",
        POST / "one_anchor_propagation_capacity_post_reference.parquet",
        POST / "two_anchor_propagation_capacity_post_reference.parquet",
        POST / "anchor_source_registry_post_reference.parquet",
        OUTPUT / "phase_a_direct_visual_verification_summary.json",
        OUTPUT / "terg_r1_summary.json",
        OUTPUT / "TERG_R1_SCIENTIFIC_REPORT.md",
        OUTPUT / "TERG_R1_FROZEN_DIAGNOSTIC_SPECIFICATION.md",
        OUTPUT / "TERG_R1_ISSUE_COUNTEREXAMPLE_ROOT_CAUSE_LEDGER.md",
    ]
    for path in required:
        require(path.is_file() and path.stat().st_size > 0, f"required artifact exists: {path.name}", checks)

    freeze = load_json(PRE / "pre_reference_freeze_summary.json")
    require(freeze["manual_reference_loaded_before_freeze"] is False, "pre-reference freeze precedes reference load", checks)
    require(freeze["post_reference_grounding_loaded_before_freeze"] is False, "grounding not loaded before freeze", checks)
    require(freeze["r04zf_accessed"] is False, "R04ZF not accessed", checks)
    require(freeze["weighted_score_used"] is False, "weighted score absent", checks)
    require(freeze["support_threshold_tuned"] is False, "support threshold not tuned", checks)
    frozen = load_json(PRE / "frozen_terg_v1_r0_input_hashes.json")
    require(current_frozen_hashes() == frozen, "TERG-v1 and TERG-R0 are byte-identical", checks)

    manifest = pd.read_csv(PRE / "pre_reference_hash_manifest.csv")
    for row in manifest.itertuples(index=False):
        path = OUTPUT / str(row.relative_path)
        require(path.is_file(), f"pre-reference artifact exists: {row.relative_path}", checks)
        require(path.stat().st_size == int(row.bytes), f"pre-reference bytes match: {row.relative_path}", checks)
        require(sha256_file(path) == str(row.sha256), f"pre-reference sha256 matches: {row.relative_path}", checks)

    pre_cases = pd.read_parquet(PRE / "excluded_pair_visual_case_registry_pre_reference.parquet")
    post_cases = pd.read_parquet(POST / "excluded_pair_likely_vs_alternative_case_registry_post_reference.parquet")
    verdict = pd.read_parquet(POST / "direct_visual_verification_verdict_post_reference.parquet")
    require(len(pre_cases) == 8, "eight pre-reference mechanical visual cases", checks)
    require(len(post_cases) == 2, "two post-reference likely-versus-alternative cases", checks)
    require(len(verdict) == 10, "ten total direct visual verdicts", checks)
    require(int(verdict["relational_evidence_support_extent"].eq("PERSISTENT_RELATIONAL_EVIDENCE").sum()) == 5, "five persistent relational cases", checks)
    require(verdict["inspection_state"].eq("CODEX_PERSONALLY_INSPECTED").all(), "all visual cases inspected", checks)
    require(~verdict["outcome_tuned_support_threshold_created"].any(), "no outcome-tuned support threshold", checks)

    episodes = pd.read_parquet(PRE / "underlying_temporal_episode_registry_pre_reference.parquet")
    assignments = pd.read_parquet(PRE / "episode_assignment_pre_reference.parquet")
    require(len(episodes) == 3, "three underlying temporal episodes", checks)
    require(int(episodes["episode_has_relational_contraction"].sum()) == 1, "one contracted episode", checks)
    require(int(episodes["contracted_segment_view_count"].sum()) == 15, "fifteen contracted repeated segment views", checks)
    require(len(assignments) == 38, "all 38 segments assigned to episodes", checks)

    availability = pd.read_parquet(PRE / "evidence_availability_map_pre_reference.parquet")
    roles = pd.read_parquet(PRE / "evidence_role_registry_pre_reference.parquet")
    require(len(availability) == 38 * 9, "complete evidence availability denominator", checks)
    require(set(availability["availability_state"]).issubset({"OBSERVABLE", "PARTIALLY_OBSERVABLE", "AMBIGUOUS", "CENSORED", "UNAVAILABLE"}), "availability vocabulary exact", checks)
    require(~availability["weighted_score_used"].any(), "availability has no weighted score", checks)
    relative = roles[roles["evidence_family"].eq("RELATIVE_ANGULAR_ORDER")].iloc[0]
    require(bool(relative.new_hard_constraint_authorized), "relative order remains authorized primitive", checks)
    require(int(roles["new_hard_constraint_authorized"].sum()) == 1, "no second hard evidence family invented", checks)

    partial = pd.read_parquet(PRE / "global_partial_order_audit_pre_reference.parquet")
    require(int(partial["direct_definite_edge_count"].sum()) == 69, "69 direct definite optical edges", checks)
    require(int(partial["transitive_edge_added_count"].sum()) == 0, "global closure adds zero new edges", checks)
    require(int(partial["redundant_direct_edge_count"].sum()) == 21, "21 redundant pair facts", checks)
    require(int(partial["cycle_count"].sum()) == 0, "partial-order graphs are acyclic", checks)

    representation = pd.read_parquet(POST / "one_track_one_family_diagnosis_post_reference.parquet")
    require(len(representation) == 79, "79 likely-supported family diagnoses", checks)
    require(representation["family_is_internally_set_valued"].all(), "79/79 likely families internally set-valued", checks)
    require(int(representation["multi_region_frame_count"].gt(0).sum()) == 26, "26 likely families have multi-region frames", checks)
    require(~representation["cross_family_bundle_required_by_available_reference_support"].any(), "cross-family bundle requirement not established", checks)
    require((representation["likely_family_reference_frame_coverage_fraction"] == 1.0).all(), "available target frames fully covered by likely family", checks)
    require((representation["likely_family_reference_region_coverage_fraction"] == 1.0).all(), "available target regions fully covered by likely family", checks)
    require(int(representation["reference_frame_without_candidate_region_count"].gt(0).sum()) == 4, "four grounding/observability gaps", checks)

    shared = pd.read_parquet(POST / "shared_transition_diagnostic_post_reference.parquet")
    require(~shared["shared_to_separated_observed"].any(), "no shared-to-separated likely sequence", checks)
    require(~shared["separated_to_shared_observed"].any(), "no separated-to-shared likely sequence", checks)
    require(~shared["new_shared_transition_constraint_authorized"].any(), "shared transition not hardened", checks)

    zero = pd.read_parquet(POST / "zero_anchor_baseline_post_reference.parquet")
    one = pd.read_parquet(POST / "one_anchor_propagation_capacity_post_reference.parquet")
    two = pd.read_parquet(POST / "two_anchor_propagation_capacity_post_reference.parquet")
    sources = pd.read_parquet(POST / "anchor_source_registry_post_reference.parquet")
    require(len(zero) == 38 and int(zero["other_track_family_deleted_count"].sum()) == 0, "zero-anchor baseline deletes no family", checks)
    require(len(one) == 79, "all 79 one-anchor scenarios reported", checks)
    require(int(one["other_track_family_deleted_count"].gt(0).sum()) == 9, "nine one-anchor scenarios propagate", checks)
    require(one[one["other_track_family_deleted_count"].gt(0)]["segment_id"].nunique() == 7, "one-anchor propagation covers seven segment views", checks)
    require(one[one["other_track_family_deleted_count"].gt(0)]["episode_id"].nunique() == 1, "one-anchor propagation remains one episode", checks)
    require(int(one["other_track_family_deleted_count"].max()) == 4, "one-anchor maximum deletion exact", checks)
    require(len(two) == 65, "all 65 two-anchor scenarios reported", checks)
    require(int(two["other_track_family_deleted_count"].gt(0).sum()) == 13, "thirteen two-anchor scenarios propagate", checks)
    require(two[two["other_track_family_deleted_count"].gt(0)]["segment_id"].nunique() == 6, "two-anchor propagation covers six segment views", checks)
    require(two[two["other_track_family_deleted_count"].gt(0)]["episode_id"].nunique() == 1, "two-anchor propagation remains one episode", checks)
    require(int(two["other_track_family_deleted_count"].max()) == 7, "two-anchor maximum deletion exact", checks)
    require(one["all_available_other_likely_families_retained"].all(), "one-anchor likely retention complete", checks)
    require(two["all_available_other_likely_families_retained"].all(), "two-anchor likely retention complete", checks)
    runtime_anchor = sources[sources["anchor_source_class"].eq("RUNTIME_LEGAL_PHYSICAL_OR_GEOMETRY_ANCHOR")].iloc[0]
    require(int(runtime_anchor.available_anchor_count) == 0, "runtime-legal anchor remains unavailable", checks)
    require(~one["runtime_result"].any() and ~two["runtime_result"].any(), "post-reference anchors never reported as runtime", checks)

    summary = load_json(OUTPUT / "terg_r1_summary.json")
    require(summary["final_route"] == EXPECTED_ROUTE, "final route exact", checks)
    require(summary["terg_v1_modified"] is False and summary["terg_r0_modified"] is False, "frozen mechanisms unmodified", checks)
    require(summary["r04zf_accessed"] is False, "summary records no R04ZF access", checks)
    require(summary["independent_confirmation_entered"] is False, "independent confirmation not entered", checks)
    require(summary["new_unary_discrimination_established"] is False, "no unary discrimination overclaim", checks)
    require(summary["cross_family_response_bundle_requirement_established"] is False, "no response bundle overclaim", checks)

    figure_paths = list(verdict["figure_path"].astype(str)) + [
        "output/person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829/figures/mechanism_diagnostics/01_phase_a_relational_support_extent.png",
        "output/person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829/figures/mechanism_diagnostics/02_episode_aware_r0_timeline.png",
        "output/person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829/figures/mechanism_diagnostics/03_evidence_availability_state_map.png",
        "output/person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829/figures/mechanism_diagnostics/04_anchor_conditioned_domain_propagation.png",
        "output/person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829/figures/mechanism_diagnostics/05_response_component_representation_diagnosis.png",
        "output/person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829/figures/mechanism_diagnostics/06_five_track_global_partial_order.png",
    ]
    for relative in sorted(set(figure_paths)):
        path = WORKSPACE / relative
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        require(image is not None and image.shape[0] >= 600 and image.shape[1] >= 900, f"figure decodes at review resolution: {relative}", checks)

    report = {
        "validator": "PERSON_TERG_R1_INDEPENDENT_VALIDATION_V1",
        "status": "PASS",
        "check_count": len(checks),
        "passed_count": sum(int(item["passed"]) for item in checks),
        "route_decision": EXPECTED_ROUTE,
        "underlying_temporal_episode_count": 3,
        "contracted_episode_count": 1,
        "one_anchor_propagating_scenario_count": 9,
        "two_anchor_propagating_scenario_count": 13,
        "runtime_legal_anchor_count": 0,
        "checks": checks,
    }
    (OUTPUT / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest_rows = []
    for path in sorted(OUTPUT.rglob("*")):
        if (
            not path.is_file()
            or path.name == "ARTIFACT_MANIFEST.csv"
            or (
                path.parent.name == "excluded_pair_direct_verification"
                and path.suffix.lower() == ".png"
            )
        ):
            continue
        manifest_rows.append({
            "relative_path": str(path.relative_to(OUTPUT)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    pd.DataFrame(manifest_rows).to_csv(OUTPUT / "ARTIFACT_MANIFEST.csv", index=False, encoding="utf-8-sig")
    print(json.dumps({key: value for key, value in report.items() if key != "checks"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
