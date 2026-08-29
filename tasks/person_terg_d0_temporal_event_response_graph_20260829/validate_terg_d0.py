from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
from PIL import Image


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "terg_d0_temporal_event_response_graph_mechanism_exploration"
)
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
        PRE / "pre_reference_manifest.json",
        PRE / "temporal_segment_atlas_pre_reference.parquet",
        PRE / "sar_response_graph_nodes_pre_reference.parquet",
        PRE / "sar_response_graph_edges_pre_reference.parquet",
        PRE / "terg_explanation_sets_pre_reference.parquet",
        PRE / "terg_explanation_components_pre_reference.parquet",
        PRE / "relative_order_compatibility_pre_reference.parquet",
        PRE / "representation_change_ledger_pre_reference.csv",
        POST / "temporal_segment_evaluation_grounding.parquet",
        POST / "explanation_component_grounding.parquet",
        POST / "temporal_review_case_registry.csv",
        POST / "TERG_D0_TEMPORAL_REVIEW_CONTACT_SHEET.jpg",
        POST / "TERG_D0_MULTIMODAL_VISUAL_REVIEW_LEDGER.md",
        POST / "TERG_D0_DEVELOPMENT_REPORT.md",
        POST / "TERG_V0_MECHANISM_SPECIFICATION_FROZEN.md",
        POST / "TERG_V0_FUTURE_CONFIRMATION_PROTOCOL_DRAFT.md",
        POST / "terg_d0_development_summary.json",
        OUTPUT / "terg_d0_final_manifest.json",
    ]
    for path in required:
        check(path.exists(), f"exists::{path.name}")

    manifest = json.loads((PRE / "pre_reference_manifest.json").read_text(encoding="utf-8"))
    final_manifest = json.loads((OUTPUT / "terg_d0_final_manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((POST / "terg_d0_development_summary.json").read_text(encoding="utf-8"))
    segments = pd.read_parquet(PRE / "temporal_segment_atlas_pre_reference.parquet")
    nodes = pd.read_parquet(PRE / "sar_response_graph_nodes_pre_reference.parquet")
    edges = pd.read_parquet(PRE / "sar_response_graph_edges_pre_reference.parquet")
    sets = pd.read_parquet(PRE / "terg_explanation_sets_pre_reference.parquet")
    components = pd.read_parquet(PRE / "terg_explanation_components_pre_reference.parquet")
    order = pd.read_parquet(PRE / "relative_order_compatibility_pre_reference.parquet")
    profiles = pd.read_parquet(PRE / "cross_modal_compatibility_profiles_pre_reference.parquet")
    event_relations = pd.read_parquet(PRE / "cross_modal_event_relations_pre_reference.parquet")
    segment_grounding = pd.read_parquet(POST / "temporal_segment_evaluation_grounding.parquet")
    component_grounding = pd.read_parquet(POST / "explanation_component_grounding.parquet")
    cases = pd.read_csv(POST / "temporal_review_case_registry.csv")

    check(manifest["reference_loaded"] is False, "pre_reference_reference_false")
    check(manifest["assignment_loaded"] is False, "pre_reference_assignment_false")
    check(manifest["confirmation_run_accessed"] is False, "pre_reference_confirmation_false")
    check(set(segments["run_id"]) == {"R01ZF", "R02ZF", "R03ZF"}, "development_runs_only")
    check("R04ZF" not in set(nodes["run_id"]), "r04_excluded_from_nodes")
    check("R04ZF" not in set(edges["run_id"]), "r04_excluded_from_edges")

    check(len(segments) == summary["temporal_segments"] == 38, "segment_accounting")
    check(len(nodes) == summary["graph_nodes"] == 4328, "node_accounting")
    check(len(edges) == summary["graph_edge_hypotheses"] == 52460, "edge_accounting")
    check(int(edges["p0_supported_continuation"].sum()) == summary["p0_supported_edges"] == 3702, "p0_edge_accounting")
    check(len(sets) == summary["explanation_sets"] == 88, "explanation_set_accounting")
    check(len(components) == summary["explanation_components"] == 3414, "component_accounting")
    check(int(sets["potential_disambiguation_gt_blind"].sum()) == 87, "potential_disambiguation_accounting")

    check(not bool(nodes["reference_used"].any()), "nodes_reference_free")
    check(not bool(edges["reference_used"].any()), "edges_reference_free")
    check(not bool(edges["identity_assignment_performed"].any()), "no_identity_assignment")
    check(not bool(edges["edge_used_for_unique_tracking"].any()), "no_unique_tracking")
    check(not bool(components["unique_path_claimed"].any()), "no_unique_path_claim")
    check(not bool(components["identity_claimed"].any()), "no_component_identity_claim")
    check(not bool(sets["unique_component_selected"].any()), "no_unique_component_selected")
    check(not bool(profiles["weighted_score_used"].any()), "no_weighted_score")
    check(not bool(profiles["pruning_performed"].any()), "no_pruning")
    check(not bool(order["weighted_score_used"].any()), "order_no_weighted_score")
    check(not bool(event_relations["manual_reference_used"].any()), "event_relations_reference_free")
    check(set(event_relations["timing_uncertainty_ms"]) == {250}, "timing_uncertainty_recorded")

    check(segment_grounding["grounding_state"].value_counts().to_dict() == {"LIKELY": 81, "UNRESOLVED": 7}, "segment_grounding_accounting")
    check(not bool(segment_grounding["runtime_use_allowed"].any()), "grounding_offline_only")
    check(int((component_grounding["component_grounding_state"] == "LIKELY_SUPPORTED_EXPLORATORY").sum()) == 79, "grounded_component_accounting")
    check(not bool(component_grounding["strict_identity_claimed"].any()), "grounding_no_identity_claim")
    check(summary["direct_visual_review_status"] == "COMPLETE_DIRECT_MULTIMODAL_REVIEW", "visual_review_complete")
    check(summary["terg_v0_freeze_status"] == "FROZEN_FOR_FUTURE_CONFIRMATION_NOT_CONFIRMED", "freeze_status")
    check(summary["future_confirmation_executed"] is False, "confirmation_not_executed")

    check(int((cases["status"] == "OBSERVED").sum()) == 14, "review_observed_count")
    check(int((cases["status"] == "CATEGORY_NOT_OBSERVED").sum()) == 2, "review_not_observed_count")
    image_failures = []
    for path_text in cases.loc[cases["status"] == "OBSERVED", "path"]:
        path = WORKSPACE / str(path_text)
        try:
            with Image.open(path) as image:
                image.verify()
        except Exception as exc:  # validator must retain exact failing path
            image_failures.append(f"{path}: {exc}")
    check(not image_failures, "review_images_readable", image_failures)

    final_failures = []
    for item in final_manifest["files"]:
        path = WORKSPACE / item["path"]
        if not path.exists() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != str(item["sha256"]):
            final_failures.append(item["path"])
    check(not final_failures, "final_manifest_hash_match", final_failures)

    failed = [item for item in checks if not item["pass"]]
    payload = {
        "schema": "PERSON_TERG_D0_INDEPENDENT_VALIDATION_V1",
        "status": "PASS" if not failed else "FAIL",
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "failed_checks": failed,
        "checks": checks,
    }
    (OUTPUT / "terg_d0_independent_validation.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
