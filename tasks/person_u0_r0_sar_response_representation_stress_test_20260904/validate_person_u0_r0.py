from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_u0_r0_sar_response_representation_stress_test_20260904"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference_diagnostic_only"
RESULT = OUTPUT / "validation_results.json"
LEVELS = {"Q090", "Q095", "Q0975"}
WINDOWS = {
    "W1_R01_SINGLE_AZIMUTH_SWEEP_F097_F112",
    "W3_R02_TWO_TARGET_ENTRY_F469_F480",
    "W4_R02_MULTI_TARGET_COMPETITION_F487_F494",
    "W5_R01_HIGH_BACKGROUND_TOPOLOGY_F048_F055",
}
KEY_CASE_IDS = {
    "U0CASE_D7C710E130CD7A3CA037",
    "U0CASE_6E10D1D1881E0A528FAE",
    "U0CASE_6048382E9235CB1545A2",
    "U0CASE_242E18D87BA861477E68",
    "U0CASE_DDBC0423FA50F610B363",
    "U0CASE_ECF5E7ACB76A2B099E3D",
    "U0CASE_E42B7C88968837DDE15A",
    "U0CASE_4788D129AFE42D7EC7B0",
}
W15_REVIEW_IDS = {
    "U0W15INV_04228D38A1AFB61C3371",
    "U0W15INV_FB6CF934D553A1133A39",
    "U0W15OVER_FAF55E86F49103CFFACE",
    "U0W15INV_9C68CDE1DB2D9CD2B813",
    "U0W15INV_B3ABF153B88E74060ACD",
    "U0W15OVER_5B7016A7009D63B42E26",
}
ATLAS_IDS = {
    "W1_ALL_ENDPOINT_INVARIANTS",
    "W5_SHARED_COMPACT_RADIAL_LADDER",
    "W5_PERSON003_RADIAL_STRUCTURES",
}


def parse_json_list(value: object) -> list[object]:
    parsed = json.loads(str(value))
    if not isinstance(parsed, list):
        raise TypeError(f"expected JSON list, got {type(parsed).__name__}")
    return parsed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


class Validator:
    def __init__(self) -> None:
        self.checks: list[dict[str, object]] = []

    def check(self, name: str, passed: bool, detail: object) -> None:
        self.checks.append({"name": name, "pass": bool(passed), "detail": detail})

    def run(self) -> dict[str, object]:
        self.check("workspace", WORKSPACE.resolve() == Path(r"D:\profile\research\workspace").resolve(), str(WORKSPACE))
        required = [
            PRE / "window_registry.csv",
            PRE / "input_manifest.csv",
            PRE / "frame_representation_summary.csv",
            PRE / "threshold_component_regions.parquet",
            PRE / "sampled_component_hierarchy.parquet",
            PRE / "threshold_specific_p0_edges.parquet",
            PRE / "threshold_specific_window_family_membership.parquet",
            PRE / "track_threshold_region_incidence.parquet",
            PRE / "track_window_ambiguity_summary.csv",
            PRE / "semantic_reverse_audit_candidates.csv",
            PRE / "selected_semantic_reverse_audit_cases.csv",
            PRE / "selected_w1_w5_representation_reviews.csv",
            PRE / "fixed_coordinate_invariant_atlas_manifest.csv",
            PRE / "operation_semantics.csv",
            PRE / "pre_reference_freeze_manifest.csv",
            PRE / "pre_reference_freeze_summary.json",
            OUTPUT / "REPORT_PRE_REFERENCE.md",
            OUTPUT / "HISTORICAL_OVERLAP.md",
        ]
        missing = [str(path) for path in required if not path.exists()]
        self.check("required_pre_files", not missing, missing)
        if missing:
            return self.finish()

        windows = pd.read_csv(PRE / "window_registry.csv")
        self.check("exact_windows", set(windows.window_id) == WINDOWS, sorted(set(windows.window_id)))
        self.check("selected_frame_count", int((windows.end_frame - windows.start_frame + 1).sum()) == 44, int((windows.end_frame - windows.start_frame + 1).sum()))
        self.check("no_forbidden_run_window", not windows.run_id.astype(str).str.upper().str.contains("R04").any(), sorted(set(windows.run_id)))

        manifest = pd.read_csv(PRE / "input_manifest.csv")
        self.check("input_manifest_no_forbidden_run", not manifest.path.astype(str).str.upper().str.contains("R04ZF").any(), int(len(manifest)))
        self.check("input_manifest_reference_flags_false", not manifest.reference_used.astype(bool).any(), int(manifest.reference_used.astype(bool).sum()))
        self.check("archive_only_not_used", not manifest.path.astype(str).str.lower().str.contains("old_work").any(), [])

        frame = pd.read_csv(PRE / "frame_representation_summary.csv")
        self.check("frame_rows_44", len(frame) == 44, len(frame))
        self.check("q95_mask_parity", frame.q95_label_mask_pixel_exact_to_r2.astype(bool).all(), int(frame.q95_label_mask_pixel_exact_to_r2.astype(bool).sum()))
        self.check("q95_descriptor_count_parity", frame.q95_descriptor_row_count_matches_r2.astype(bool).all(), int(frame.q95_descriptor_row_count_matches_r2.astype(bool).sum()))
        self.check("sensor_raw_not_claimed", frame.sar_input_semantics.eq("UNMODIFIED_8BIT_PSEUDOCOLOR_DISPLAY_FRAME_NOT_SENSOR_RAW_AMPLITUDE").all(), sorted(frame.sar_input_semantics.unique()))

        regions = pd.read_parquet(PRE / "threshold_component_regions.parquet")
        self.check("three_levels", set(regions.percentile_tag) == LEVELS, sorted(set(regions.percentile_tag)))
        self.check("region_reference_flags_false", not regions.reference_used_for_region_generation.astype(bool).any(), int(regions.reference_used_for_region_generation.astype(bool).sum()))
        self.check("no_final_boxes", not regions.region_is_final_person_box.astype(bool).any(), int(regions.region_is_final_person_box.astype(bool).sum()))

        hierarchy = pd.read_parquet(PRE / "sampled_component_hierarchy.parquet")
        self.check("hierarchy_child_containment_exact", np.allclose(hierarchy.child_containment_fraction, 1.0), float(hierarchy.child_containment_fraction.min()))
        expected_relations = {("Q095", "Q090"), ("Q0975", "Q095"), ("Q0975", "Q090")}
        actual_relations = set(zip(hierarchy.child_tag, hierarchy.parent_tag))
        self.check("hierarchy_relation_types", actual_relations == expected_relations, sorted(actual_relations))
        self.check("hierarchy_reference_false", not hierarchy.reference_used.astype(bool).any(), int(hierarchy.reference_used.astype(bool).sum()))

        edges = pd.read_parquet(PRE / "threshold_specific_p0_edges.parquet")
        self.check("edge_levels", set(edges.percentile_tag) == LEVELS, sorted(set(edges.percentile_tag)))
        self.check("edges_reference_false", not edges.reference_used.astype(bool).any(), int(edges.reference_used.astype(bool).sum()))
        exact_semantic = "SAME_FROZEN_P0_WARP_AND_MUTUAL_DOMINANCE_OPERATION_APPLIED_PER_THRESHOLD"
        self.check("same_temporal_operation", edges.family_authority_semantics.eq(exact_semantic).all(), sorted(edges.family_authority_semantics.unique()))

        families = pd.read_parquet(PRE / "threshold_specific_window_family_membership.parquet")
        self.check("family_levels", set(families.percentile_tag) == LEVELS, sorted(set(families.percentile_tag)))
        self.check("families_reference_false", not families.reference_used.astype(bool).any(), int(families.reference_used.astype(bool).sum()))

        incidence = pd.read_parquet(PRE / "track_threshold_region_incidence.parquet")
        self.check("incidence_levels", set(incidence.percentile_tag) == LEVELS, sorted(set(incidence.percentile_tag)))
        self.check("incidence_reference_false", not incidence.reference_used.astype(bool).any(), int(incidence.reference_used.astype(bool).sum()))

        cases = pd.read_csv(PRE / "semantic_reverse_audit_candidates.csv")
        self.check("w3_w4_cases_exist", set(cases.window_id).issubset({w for w in WINDOWS if w.startswith(("W3_", "W4_"))}) and len(cases) > 0, {k: int(v) for k, v in cases.window_id.value_counts().to_dict().items()})
        selected = cases[cases.selected_for_direct_review.astype(bool)].copy()
        unselected = cases[~cases.selected_for_direct_review.astype(bool)].copy()
        pending = int(selected.manual_visual_class.eq("PENDING_DIRECT_REVIEW").sum())
        self.check("selected_manual_visual_review_complete", pending == 0, pending)
        allowed = {"ALGORITHM_INDUCED_SPLIT", "ALGORITHM_INDUCED_MERGE", "GENUINE_UNRESOLVED_STRUCTURE", "UNCERTAIN"}
        self.check("selected_manual_class_vocabulary", set(selected.manual_visual_class).issubset(allowed), sorted(set(selected.manual_visual_class)))
        self.check("unselected_manual_class_sentinel", unselected.manual_visual_class.eq("NOT_SELECTED_FOR_DIRECT_REVIEW").all(), sorted(set(unselected.manual_visual_class)))
        selected_table = pd.read_csv(PRE / "selected_semantic_reverse_audit_cases.csv")
        self.check("selected_case_allowlist_exact", set(selected.case_id.astype(str)) == KEY_CASE_IDS, sorted(set(selected.case_id.astype(str)) ^ KEY_CASE_IDS))
        self.check("selected_case_id_parity", set(selected.case_id.astype(str)) == set(selected_table.case_id.astype(str)), sorted(set(selected.case_id.astype(str)) ^ set(selected_table.case_id.astype(str))))
        case_fields = {
            "q95_source_edge_participating_count", "q95_destination_edge_participating_count",
            "q95_source_exact_parent_total_count", "q95_destination_exact_parent_total_count",
            "q975_source_exact_parent_total_count", "q975_destination_exact_parent_total_count",
            "q95_source_edge_region_ids_json", "q95_destination_edge_region_ids_json",
            "q95_source_exact_parent_region_ids_json", "q95_destination_exact_parent_region_ids_json",
            "q975_source_exact_parent_region_ids_json", "q975_destination_exact_parent_region_ids_json",
            "q90_outgoing_optional_destination_ids_json", "q90_outgoing_lower_mutual_destination_ids_json",
            "q90_incoming_optional_source_ids_json", "q90_incoming_lower_mutual_source_ids_json",
            "q90_selected_edge_optional_compatible", "q90_selected_edge_lower_mutual_dominant",
            "q90_selected_edge_soft_iou", "q90_source_window_family_id", "q90_destination_window_family_id",
            "q95_source_strict_family_ids_json", "q95_destination_strict_family_ids_json",
            "q95_source_window_family_ids_json", "q95_destination_window_family_ids_json",
            "q975_source_window_family_ids_json", "q975_destination_window_family_ids_json",
        }
        self.check("selected_case_evidence_fields", case_fields.issubset(selected.columns), sorted(case_fields - set(selected.columns)))
        if case_fields.issubset(selected.columns):
            json_fields = [field for field in case_fields if field.endswith("_json")]
            json_errors = []
            for row in selected.itertuples(index=False):
                for field in json_fields:
                    try:
                        parse_json_list(getattr(row, field))
                    except (TypeError, ValueError, json.JSONDecodeError) as exc:
                        json_errors.append(f"{row.case_id}:{field}:{exc}")
            self.check("selected_case_json_fields_parse", not json_errors, json_errors)
            count_pairs = [
                ("q95_source_edge_participating_count", "q95_source_edge_region_ids_json"),
                ("q95_destination_edge_participating_count", "q95_destination_edge_region_ids_json"),
                ("q95_source_exact_parent_total_count", "q95_source_exact_parent_region_ids_json"),
                ("q95_destination_exact_parent_total_count", "q95_destination_exact_parent_region_ids_json"),
                ("q975_source_exact_parent_total_count", "q975_source_exact_parent_region_ids_json"),
                ("q975_destination_exact_parent_total_count", "q975_destination_exact_parent_region_ids_json"),
            ]
            count_mismatches = []
            for row in selected.itertuples(index=False):
                for count_field, ids_field in count_pairs:
                    if int(getattr(row, count_field)) != len(parse_json_list(getattr(row, ids_field))):
                        count_mismatches.append(f"{row.case_id}:{count_field}")
            self.check("selected_case_count_id_parity", not count_mismatches, count_mismatches)
            mapping_missing = selected[["q90_source_window_family_id", "q90_destination_window_family_id"]].isna().any(axis=1)
            self.check("selected_case_family_mapping_present", not mapping_missing.any(), selected.loc[mapping_missing, "case_id"].astype(str).tolist())
        w15 = pd.read_csv(PRE / "selected_w1_w5_representation_reviews.csv")
        w15_allowed = {"VISIBLE_CROSS_LEVEL_LONG_TERM_STRUCTURE", "LOWER_THRESHOLD_OVERMERGE_PRESSURE", "UNCERTAIN"}
        self.check("w1_w5_review_rows_exist", len(w15) >= 6 and set(w15.window_id.astype(str).str[:2]) == {"W1", "W5"}, len(w15))
        self.check("w1_w5_review_allowlist_exact", set(w15.review_id.astype(str)) == W15_REVIEW_IDS, sorted(set(w15.review_id.astype(str)) ^ W15_REVIEW_IDS))
        self.check("w1_w5_manual_review_complete", not w15.manual_visual_class.eq("PENDING_DIRECT_REVIEW").any(), int(w15.manual_visual_class.eq("PENDING_DIRECT_REVIEW").sum()))
        self.check("w1_w5_manual_class_vocabulary", set(w15.manual_visual_class).issubset(w15_allowed), sorted(set(w15.manual_visual_class)))

        semantics = pd.read_csv(PRE / "operation_semantics.csv")
        required_columns = {"code_operation", "program_computation", "intended_semantic", "verified_semantic"}
        self.check("operation_semantics_columns", required_columns.issubset(semantics.columns), sorted(semantics.columns))
        self.check("operation_semantics_rows", len(semantics) >= 6, len(semantics))
        self.check("optional_topology_semantics_present", "optional_branch_topology_probe" in set(semantics.code_operation.astype(str)), sorted(set(semantics.code_operation.astype(str))))

        figures = sorted((PRE / "figures").glob("*.png"))
        window_atlases = [p for p in figures if p.name.endswith("_sequence_representation_atlas.png")]
        compact_sheets = [p for p in figures if p.name.endswith("_compact_review_sheet.png")]
        case_sheets = [p for p in figures if p.name.startswith("case_targeted_")]
        invariant_sheets = [p for p in figures if p.name.startswith("invariant_targeted_")]
        overmerge_sheets = [p for p in figures if p.name.startswith("overmerge_targeted_")]
        fixed_atlases = [p for p in figures if p.name.startswith("invariant_atlas_")]
        self.check("four_sequence_atlases", len(window_atlases) == 4, [p.name for p in window_atlases])
        self.check("four_compact_sheets", len(compact_sheets) == 4, [p.name for p in compact_sheets])
        self.check("case_sheets_exact", {p.stem.removeprefix("case_targeted_") for p in case_sheets} == KEY_CASE_IDS, [p.name for p in case_sheets])
        self.check("w1_w5_targeted_sheets_exist", len(invariant_sheets) >= 4 and len(overmerge_sheets) >= 2, {"invariant": len(invariant_sheets), "overmerge": len(overmerge_sheets)})
        atlas_manifest = pd.read_csv(PRE / "fixed_coordinate_invariant_atlas_manifest.csv")
        self.check("fixed_atlas_manifest_exact", set(atlas_manifest.atlas_id.astype(str)) == ATLAS_IDS, sorted(set(atlas_manifest.atlas_id.astype(str)) ^ ATLAS_IDS))
        self.check("fixed_atlas_figures_exact", {p.stem.removeprefix("invariant_atlas_") for p in fixed_atlases} == ATLAS_IDS, [p.name for p in fixed_atlases])
        atlas_errors = []
        for row in atlas_manifest.itertuples(index=False):
            try:
                if len(parse_json_list(row.family_ids_json)) < 4:
                    atlas_errors.append(f"{row.atlas_id}:family_ids")
                if len(parse_json_list(row.frames_json)) != 3:
                    atlas_errors.append(f"{row.atlas_id}:frames")
                if len(parse_json_list(row.fixed_crop_xyxy_json)) != 4:
                    atlas_errors.append(f"{row.atlas_id}:crop")
                if bool(row.reference_used):
                    atlas_errors.append(f"{row.atlas_id}:reference")
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                atlas_errors.append(f"{row.atlas_id}:{exc}")
        self.check("fixed_atlas_manifest_semantics", not atlas_errors, atlas_errors)

        freeze_manifest = pd.read_csv(PRE / "pre_reference_freeze_manifest.csv")
        expected_paths = set(freeze_manifest.relative_path.astype(str))
        actual_paths = {
            path.relative_to(PRE).as_posix()
            for path in PRE.rglob("*")
            if path.is_file() and path.name not in {"pre_reference_freeze_manifest.csv", "pre_reference_freeze_summary.json"}
        }
        self.check("freeze_file_set_exact", expected_paths == actual_paths, {"missing": sorted(expected_paths - actual_paths), "unexpected": sorted(actual_paths - expected_paths)})
        mismatches = []
        digest = hashlib.sha256()
        for row in freeze_manifest.itertuples(index=False):
            path = PRE / row.relative_path
            actual = sha256_file(path) if path.exists() else None
            if not path.exists() or path.stat().st_size != int(row.bytes) or actual != str(row.sha256):
                mismatches.append(str(row.relative_path))
            digest.update(f"{row.relative_path}|{row.bytes}|{row.sha256}\n".encode("utf-8"))
        freeze = json.loads((PRE / "pre_reference_freeze_summary.json").read_text(encoding="utf-8"))
        self.check("freeze_files_match", not mismatches, mismatches)
        self.check("freeze_tree_digest", digest.hexdigest().upper() == freeze["tree_sha256"], freeze["tree_sha256"])
        self.check("freeze_no_reference", freeze.get("reference_used") is False, freeze.get("reference_used"))
        self.check("freeze_no_forbidden_run", freeze.get("r04_used") is False, freeze.get("r04_used"))
        self.check("freeze_phase_isolation_disclosure", freeze.get("preconstruction_reference_codepath_used") is False and freeze.get("analyst_naive_reveal_order_preserved") is False, {"codepath": freeze.get("preconstruction_reference_codepath_used"), "analyst_naive": freeze.get("analyst_naive_reveal_order_preserved")})

        if POST.exists():
            state_path = POST / "post_reference_state.json"
            self.check("post_state_exists", state_path.exists(), str(state_path))
            if state_path.exists():
                state = json.loads(state_path.read_text(encoding="utf-8"))
                self.check("post_uses_frozen_tree", state.get("pre_reference_tree_sha256") == freeze["tree_sha256"], state.get("pre_reference_tree_sha256"))
                self.check("post_did_not_change_construction", state.get("construction_changed_after_reference") is False, state.get("construction_changed_after_reference"))
                self.check("post_no_threshold_tuning", state.get("reference_used_for_parameter_choice") is False, state.get("reference_used_for_parameter_choice"))
                self.check("post_no_forbidden_run", state.get("r04_used") is False, state.get("r04_used"))
                self.check("final_report_exists", (OUTPUT / "REPORT.md").exists(), str(OUTPUT / "REPORT.md"))

        return self.finish()

    def finish(self) -> dict[str, object]:
        passed = sum(bool(row["pass"]) for row in self.checks)
        result = {
            "schema": "PERSON_U0_R0_INDEPENDENT_VALIDATION_V1",
            "status": "PASS" if passed == len(self.checks) else "FAIL",
            "check_count": len(self.checks),
            "pass_count": passed,
            "fail_count": len(self.checks) - passed,
            "checks": self.checks,
            "scientific_claim_limit": "artifact integrity and phase isolation only; not physical truth, PERSON discrimination, or localization improvement",
        }
        OUTPUT.mkdir(parents=True, exist_ok=True)
        RESULT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return result


if __name__ == "__main__":
    result = Validator().run()
    print(json.dumps({k: result[k] for k in ("status", "check_count", "pass_count", "fail_count")}, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
