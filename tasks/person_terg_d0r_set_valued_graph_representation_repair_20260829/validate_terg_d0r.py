from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
from typing import Any

import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_terg_d0r_set_valued_graph_representation_repair_20260829"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference"
PHASE_A_TASK = WORKSPACE / "tasks" / "person_terg_v0_visual_semantic_reality_check_20260829"
PHASE_A_OUTPUT = WORKSPACE / "output" / "person_terg_v0_visual_semantic_reality_check_20260829"
D0_PRE = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "terg_d0_temporal_event_response_graph_mechanism_exploration"
    / "pre_reference"
)
RUN_SCRIPT = TASK / "run_terg_d0r.py"
REPORT = OUTPUT / "validation_report.json"
MANIFEST = OUTPUT / "ARTIFACT_MANIFEST.sha256"

PHYSICAL_EDGE_KEY = [
    "run_id",
    "source_sar_frame",
    "destination_sar_frame",
    "source_region_id",
    "destination_region_id",
]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(name: str, condition: bool, detail: Any, rows: list[dict[str, Any]]) -> None:
    rows.append({"name": name, "pass": bool(condition), "detail": detail})


def table(path: Path) -> pd.DataFrame:
    if path.suffix == ".csv":
        return pd.read_csv(path)
    return pd.read_parquet(path)


def build_manifest() -> int:
    roots = [
        TASK,
        OUTPUT,
        PHASE_A_TASK,
        PHASE_A_OUTPUT,
    ]
    explicit = [
        WORKSPACE / "logs" / "20260829_person_terg_d0r_set_valued_graph_representation_repair.md",
        WORKSPACE / "logs" / "20260829_person_terg_v0_visual_semantic_reality_check.md",
    ]
    files: set[Path] = set(explicit)
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts or path == MANIFEST:
                continue
            files.add(path)
    lines = []
    for path in sorted(files, key=lambda item: item.as_posix().lower()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        relative = path.relative_to(WORKSPACE).as_posix()
        lines.append(f"{digest}  {relative}")
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def main() -> None:
    checks: list[dict[str, Any]] = []
    summary = json.loads((OUTPUT / "terg_v1_summary.json").read_text(encoding="utf-8"))
    physical = table(PRE / "physical_sar_response_regions_pre_reference.parquet")
    incidence = table(PRE / "optical_conditioned_region_incidence_pre_reference.parquet")
    set_incidence = table(PRE / "explanation_set_region_incidence_pre_reference.parquet")
    edges = table(PRE / "set_valued_physical_temporal_edges_pre_reference.parquet")
    families = table(PRE / "admissible_component_families_pre_reference.parquet")
    cores = table(PRE / "lower_core_components_pre_reference.parquet")
    memberships = table(PRE / "component_family_membership_pre_reference.parquet")
    relations = table(PRE / "possible_relation_sets_pre_reference.parquet")
    relation_support = table(PRE / "relation_temporal_support_extents_pre_reference.parquet")
    burden = table(PRE / "temporal_stratification_burden_profiles_pre_reference.parquet")
    timing_authority = table(PRE / "timing_authority_pre_reference.parquet")
    timing_relations = table(PRE / "timing_relation_sets_pre_reference.parquet")
    d0_components = table(D0_PRE / "terg_explanation_components_pre_reference.parquet")
    d0_edges = table(D0_PRE / "sar_response_graph_edges_pre_reference.parquet")

    check("final_state_ready", summary["final_state"] == "TERG_V1_READY_FOR_INDEPENDENT_CONFIRMATION", summary["final_state"], checks)
    check("physical_region_count", len(physical) == 3056, len(physical), checks)
    check("physical_key_unique", not physical.duplicated(["run_id", "frame_index", "region_id"]).any(), len(physical), checks)
    check("physical_id_unique", physical["physical_region_id"].nunique() == len(physical), physical["physical_region_id"].nunique(), checks)
    check("conditioned_incidence_count", len(incidence) == 4328, len(incidence), checks)
    check("incidence_references_physical", incidence["physical_region_id"].isin(physical["physical_region_id"]).all(), int(incidence["physical_region_id"].isin(physical["physical_region_id"]).sum()), checks)
    check("set_incidence_count", len(set_incidence) == 18937, len(set_incidence), checks)

    supported = edges[edges["p0_supported_continuation"].astype(bool)]
    lower = edges[edges["lower_core_eligible"].astype(bool)]
    optional = edges[edges["connectivity_authority"].eq("UPPER_OPTIONAL")]
    check("physical_edge_unique", not edges.duplicated(PHYSICAL_EDGE_KEY).any(), len(edges), checks)
    check("supported_physical_edges", len(supported) == 2644, len(supported), checks)
    check("threshold_free_lower_core_count", len(lower) == 111, len(lower), checks)
    check("upper_optional_edge_count", len(optional) == 2533, len(optional), checks)
    categorical_rule = (
        lower["mutual_local_dominant"].astype(bool)
        & lower["exclusive_one_to_one_topology"].astype(bool)
        & lower["p0_common_compatible"].astype(bool)
        & ~lower["deformation_evidence"].astype(bool)
        & ~lower["boundary_censoring_evidence"].astype(bool)
    )
    check("lower_core_exact_categorical_rule", categorical_rule.all(), int(categorical_rule.sum()), checks)
    check("no_numeric_threshold_repair_flag", not edges["new_numeric_threshold_used_for_repair"].astype(bool).any(), False, checks)
    raw_evidence = {
        "soft_intersection_px",
        "source_total_retention",
        "destination_explained_fraction",
        "soft_iou",
        "sar_p0_residual_state_core",
        "sar_p0_residual_state",
        "sar_topology_state",
        "source_touches_boundary",
        "destination_touches_boundary",
        "source_truncated",
        "destination_truncated",
    }
    check("raw_edge_evidence_retained", raw_evidence.issubset(edges.columns), sorted(raw_evidence - set(edges.columns)), checks)

    check("all_d0_components_preserved", len(families) == 3414 and set(families["d0_component_id"]) == set(d0_components["explanation_component_id"]), len(families), checks)
    check("membership_physical_only", memberships["physical_region_id"].isin(physical["physical_region_id"]).all(), len(memberships), checks)
    check("lower_core_component_count", len(cores) == 18314, len(cores), checks)
    check("actual_pruning_zero", int(burden["actual_pruned_node_count"].sum()) == 0 and int(burden["actual_pruned_family_count"].sum()) == 0, {"nodes": int(burden["actual_pruned_node_count"].sum()), "families": int(burden["actual_pruned_family_count"].sum())}, checks)
    check("temporal_stratification_87_of_88", int(burden["temporal_stratification_available"].sum()) == 87 and len(burden) == 88, int(burden["temporal_stratification_available"].sum()), checks)

    shared = relations[relations["possible_relation_set"].str.contains("SHARED", regex=False)]
    check("relation_profile_count", len(relations) == 85, len(relations), checks)
    check("shared_profile_count", len(shared) == 78, len(shared), checks)
    check("shared_partial_direction_27", int(relations["relation_set_classification"].eq("SHARED_PLUS_PARTIAL_DIRECTION").sum()) == 27, int(relations["relation_set_classification"].eq("SHARED_PLUS_PARTIAL_DIRECTION").sum()), checks)
    check("shared_competing_direction_51", int(relations["relation_set_classification"].eq("SHARED_PLUS_COMPETING_DIRECTIONS").sum()) == 51, int(relations["relation_set_classification"].eq("SHARED_PLUS_COMPETING_DIRECTIONS").sum()), checks)
    check("pure_shared_only_zero", int(relations["relation_set_classification"].eq("PURE_SHARED_ONLY").sum()) == 0, 0, checks)
    check("no_best_pair_or_weighted_vote", not relations["best_family_pair_selected"].astype(bool).any() and not relations["weighted_vote_used"].astype(bool).any(), len(relations), checks)
    check("per_frame_relation_support_present", len(relation_support) > 0 and relation_support["frame_index"].notna().all(), len(relation_support), checks)

    check("split_merge_hard_false", not edges["split_merge_hard_event_claimed"].astype(bool).any(), False, checks)
    split_like = edges[edges["sar_topology_state"].astype(str).str.contains("SPLIT") & edges["p0_supported_continuation"].astype(bool)]
    merge_like = edges[edges["sar_topology_state"].astype(str).str.contains("MERGE") & edges["p0_supported_continuation"].astype(bool)]
    check("split_hypotheses_set_valued", split_like["topology_hypothesis_set"].str.contains("ONE_TO_MANY_POSSIBLE", regex=False).all(), len(split_like), checks)
    check("merge_hypotheses_set_valued", merge_like["topology_hypothesis_set"].str.contains("MANY_TO_ONE_POSSIBLE", regex=False).all(), len(merge_like), checks)

    check("timing_250_column_removed", "timing_uncertainty_ms" not in timing_relations.columns, list(timing_relations.columns), checks)
    check("timing_relation_set_uncalibrated", timing_relations.loc[~timing_relations["timing_relation_state"].eq("SAR_EVENT_UNAVAILABLE"), "timing_relation_state"].eq("TIMING_RELATION_SET_UNDER_UNCALIBRATED_SYNC").all(), timing_relations["timing_relation_state"].value_counts().to_dict(), checks)
    check("sync_offset_unresolved", timing_authority["sync_offset_state"].eq("UNRESOLVED_SYNC_OFFSET_NO_BOUNDED_ACQUISITION_PROVENANCE").all(), timing_authority["sync_offset_state"].unique().tolist(), checks)
    check("no_invented_replacement_margin", timing_authority["replacement_default_margin_ms"].eq("NONE").all(), timing_authority["replacement_default_margin_ms"].unique().tolist(), checks)

    phase_bridge = pd.read_csv(PHASE_A_OUTPUT / "tables" / "bridge_criticality.csv")
    weak_old_ids = set(phase_bridge.loc[phase_bridge["audit_edge_family"].eq("WEAK_CONTINUATION"), "graph_edge_id"].astype(str))
    old_to_key = d0_edges[d0_edges["graph_edge_id"].astype(str).isin(weak_old_ids)][["graph_edge_id"] + PHYSICAL_EDGE_KEY]
    weak_new = old_to_key.merge(edges, on=PHYSICAL_EDGE_KEY, how="left", validate="many_to_one")
    check("phase_a_weak_edges_preserved_upper", weak_new["p0_supported_continuation"].astype(bool).all(), len(weak_new), checks)
    check("phase_a_weak_edges_not_lower_core", not weak_new["lower_core_eligible"].astype(bool).any(), len(weak_new), checks)

    forbidden_pre_columns = {
        "target_id",
        "physical_target_id",
        "dominant_target_id_offline",
        "offline_target_ids",
        "reference_support_status",
        "reference_support_states",
        "component_grounding_state",
        "grounding_semantics",
        "grounding_semantics_v1",
    }
    pre_files = sorted(PRE.glob("*.parquet"))
    leaked_columns: dict[str, list[str]] = {}
    false_flag_violations: dict[str, list[str]] = {}
    for path in pre_files:
        frame = table(path)
        overlap = sorted(forbidden_pre_columns & set(frame.columns))
        if overlap:
            leaked_columns[path.name] = overlap
        for column in [name for name in frame.columns if name in {"manual_reference_used", "reference_used", "reference_used_for_region_generation", "post_reference_evaluated_discrimination_used"}]:
            if frame[column].fillna(False).astype(bool).any():
                false_flag_violations.setdefault(path.name, []).append(column)
    check("pre_reference_forbidden_columns_absent", not leaked_columns, leaked_columns, checks)
    check("pre_reference_reference_flags_false", not false_flag_violations, false_flag_violations, checks)

    run_module = load_module(RUN_SCRIPT, "terg_d0r_for_validation")
    pre_loader_source = inspect.getsource(run_module.load_pre_reference_inputs)
    representation_sources = "\n".join(
        inspect.getsource(function)
        for function in [
            run_module.build_physical_layers,
            run_module.build_physical_edges,
            run_module.build_component_families,
            run_module.build_relation_sets,
            run_module.build_burden_profiles,
            run_module.build_timing_representation,
        ]
    )
    run_text = RUN_SCRIPT.read_text(encoding="utf-8")
    check("pre_loader_has_no_post_reference_input", "D0_POST" not in pre_loader_source and "offline_reference" not in pre_loader_source, pre_loader_source, checks)
    check(
        "representation_functions_have_no_post_reference_access",
        'data["component_grounding"]' not in representation_sources
        and 'data["reference"]' not in representation_sources
        and "post_data" not in representation_sources,
        "static source audit",
        checks,
    )
    check("no_half_threshold_in_run_script", "CORE_RETENTION_SEMANTIC_BOUNDARY" not in run_text and ">=0.5" not in run_text and ".ge(0.5)" not in run_text, "static source audit", checks)
    check("no_r04_input_path", "R04ZF" not in run_text, "static source audit; lowercase audit flag is metadata only", checks)

    figures = [Path(path) for path in summary["reality_alignment_checks"]["visual_before_after_packs"]]
    check("eleven_visual_packs_exist", len(figures) == 11 and all(path.is_file() and path.stat().st_size > 0 for path in figures), [path.name for path in figures], checks)
    contact = Path(summary["reality_alignment_checks"]["contact_sheet"])
    check("contact_sheet_exists", contact.is_file() and contact.stat().st_size > 0, str(contact), checks)
    freeze = OUTPUT / "TERG_V1_SET_VALUED_TEMPORAL_EXPLANATION_MECHANISM_FROZEN.md"
    scientific = OUTPUT / "TERG_V1_SCIENTIFIC_FREEZE_REPORT.md"
    ledger = OUTPUT / "TERG_V1_ISSUE_SIDE_EFFECT_LEDGER.md"
    check("freeze_documents_exist", all(path.is_file() and path.stat().st_size > 0 for path in [freeze, scientific, ledger]), [path.name for path in [freeze, scientific, ledger]], checks)

    failed = [item for item in checks if not item["pass"]]
    payload = {
        "schema": "PERSON_TERG_D0R_INDEPENDENT_VALIDATION_V1",
        "status": "PASS" if not failed else "FAIL",
        "check_count": len(checks),
        "pass_count": len(checks) - len(failed),
        "fail_count": len(failed),
        "checks": checks,
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failed:
        raise AssertionError(json.dumps(failed, ensure_ascii=False, indent=2))
    manifest_count = build_manifest()
    payload["manifest_entry_count"] = manifest_count
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_count = build_manifest()
    print(json.dumps({"status": "PASS", "checks": len(checks), "manifest_entries": manifest_count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
