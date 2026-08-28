"""Independent validator for the frozen M0B1-R representation audit."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK_DIR = SCRIPT.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OLD_ROOT = STUDY / "m0b1_r02_raw_fragment_angular_direction_diagnostic"
OUTPUT = STUDY / "m0b1_r_angular_dynamic_representation_audit"
FREEZE = OUTPUT / "protocol_freeze.json"
SUMMARY = OUTPUT / "audit_summary_pre_reference.json"
MANIFEST = OUTPUT / "final_output_manifest.json"
TOL = 1e-12


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def check(condition: bool, name: str, checks: list[dict[str, Any]], detail: str = "") -> None:
    checks.append({"check": name, "pass": bool(condition), "detail": detail})
    if not condition:
        raise RuntimeError(f"Validation failed: {name}: {detail}")


def main() -> None:
    checks: list[dict[str, Any]] = []
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    for record in [freeze["protocol"], freeze["runner"], freeze["validator"], *freeze["sources"]]:
        path = Path(record["path"])
        check(path.exists(), f"frozen_file_exists::{path.name}", checks, str(path))
        check(path.stat().st_size == record["size_bytes"], f"frozen_size::{path.name}", checks)
        check(sha256_file(path) == record["sha256"], f"frozen_hash::{path.name}", checks)
    check(not freeze["reference_loaded"], "freeze_reference_false", checks)
    check(not freeze["manual_reference_used_in_optical_representation_audit"], "freeze_optical_audit_manual_reference_false", checks)
    check(not freeze["manual_reference_used_to_select_representation"], "freeze_manual_reference_not_used_for_representation_selection", checks)
    check(not freeze["representation_selected_from_post_reference_outcome"], "freeze_no_post_reference_selection", checks)
    check(all("post_reference" not in record["path"].lower() for record in freeze["sources"]), "no_post_reference_source_paths", checks)
    check(all("old_work" not in record["path"].lower() for record in freeze["sources"]), "no_old_work_source_paths", checks)

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    check(summary["frozen_predecessor_state"] == "M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT", "predecessor_state_unchanged", checks)
    check(not summary["frozen_predecessor_modified"], "predecessor_not_modified_claim", checks)
    check(not summary["reference_loaded"] and not summary["manual_reference_used_in_optical_representation_audit"], "summary_optical_audit_pre_reference", checks)
    check(not summary["manual_reference_used_to_select_representation"], "summary_no_reference_representation_selection", checks)
    check(not summary["cross_modal_discrimination_executed"], "no_cross_modal_discrimination", checks)
    check(not summary["M0B2_executed"], "no_m0b2", checks)
    check(summary["prohibited_actions_executed"] == [], "no_prohibited_actions", checks)

    bank = pd.read_parquet(OUTPUT / "optical_dynamic_bank_records_pre_reference.parquet")
    unique = pd.read_parquet(OUTPUT / "optical_dynamic_unique_pairs_pre_reference.parquet")
    check(len(bank) == summary["dynamic_available_bank_rows"], "bank_count_matches_summary", checks)
    check(len(unique) == summary["deduplicated_optical_pair_signatures"], "unique_count_matches_summary", checks)
    check(bank["source_track_id"].eq(bank["destination_track_id"]).all(), "same_raw_fragment_gate", checks)
    check(bank["source_optical_frame_index"].ne(bank["destination_optical_frame_index"]).all(), "distinct_sample_gate", checks)
    check(np.allclose(bank["all_pairs_low_recomputed_deg"], bank["L2_deg"] - bank["U1_deg"], atol=1e-10, rtol=0), "old_low_formula", checks)
    check(np.allclose(bank["all_pairs_high_recomputed_deg"], bank["U2_deg"] - bank["L1_deg"], atol=1e-10, rtol=0), "old_high_formula", checks)
    check(np.allclose(bank["all_pairs_low_recomputed_deg"], bank["delta_c_deg"] - bank["h1_deg"] - bank["h2_deg"], atol=1e-10, rtol=0), "center_halfwidth_low_identity", checks)
    check(np.allclose(bank["all_pairs_high_recomputed_deg"], bank["delta_c_deg"] + bank["h1_deg"] + bank["h2_deg"], atol=1e-10, rtol=0), "center_halfwidth_high_identity", checks)
    check(np.allclose(bank["d_left_deg"], bank["L2_deg"] - bank["L1_deg"], atol=1e-10, rtol=0), "d_left_formula", checks)
    check(np.allclose(bank["d_right_deg"], bank["U2_deg"] - bank["U1_deg"], atol=1e-10, rtol=0), "d_right_formula", checks)
    check(np.allclose(bank["d_mid_deg"], 0.5 * (bank["L2_deg"] + bank["U2_deg"] - bank["L1_deg"] - bank["U1_deg"]), atol=1e-10, rtol=0), "d_mid_formula", checks)
    check(np.allclose(bank["d_width_deg"], (bank["U2_deg"] - bank["L2_deg"]) - (bank["U1_deg"] - bank["L1_deg"]), atol=1e-10, rtol=0), "d_width_formula", checks)
    denominator = bank["h1_deg"] + bank["h2_deg"]
    check(np.allclose(bank["eta"], bank["delta_c_deg"].abs() / denominator, atol=1e-10, rtol=0), "eta_formula", checks)
    check((bank["eta_gt_1_old_observability_condition"] == (bank["eta"] > 1)).all(), "eta_gt_1_semantics", checks)
    check(int(bank["frozen_all_pairs_direction_state_recomputed"].isin(["OPTICAL_POSITIVE", "OPTICAL_NEGATIVE"]).sum()) == summary["old_determinate_bank_rows"], "old_determinate_count", checks)
    coherent = bank["corresponding_boundary_state"].isin(["COHERENT_POSITIVE_SHIFT", "COHERENT_NEGATIVE_SHIFT"])
    check(int(coherent.sum()) == summary["boundary_coherent_bank_rows"], "boundary_coherent_count", checks)
    no_resolved = bank["corresponding_boundary_state"].eq("NO_RESOLVED_SHIFT")
    check(((bank.loc[no_resolved, "d_left_deg"].abs() <= TOL) & (bank.loc[no_resolved, "d_right_deg"].abs() <= TOL)).all(), "no_resolved_is_numerical_zero_only", checks)

    required_tables = [
        "eta_summary_overall_pre_reference",
        "eta_by_fragment_pre_reference",
        "eta_by_exact_frame_separation_pre_reference",
        "eta_by_frame_separation_stratum_pre_reference",
        "eta_by_exact_time_separation_pre_reference",
        "eta_by_time_separation_stratum_pre_reference",
        "eta_by_optical_interval_width_stratum_pre_reference",
        "representation_state_summary_pre_reference",
        "mapping_slope_sign_audit_pre_reference",
        "bottleneck_hierarchy_pre_reference",
    ]
    for stem in required_tables:
        check((OUTPUT / f"{stem}.csv").exists() and (OUTPUT / f"{stem}.parquet").exists(), f"required_table::{stem}", checks)
    eta_overall = pd.read_csv(OUTPUT / "eta_summary_overall_pre_reference.csv", encoding="utf-8-sig")
    check(set(eta_overall["scope"]) == {"M0B1_BANK_ROWS", "DEDUPLICATED_OPTICAL_PAIR_SIGNATURES"}, "eta_scopes_complete", checks)
    representation = pd.read_csv(OUTPUT / "representation_state_summary_pre_reference.csv", encoding="utf-8-sig")
    check(set(representation["operator"]) == {"FROZEN_ALL_PAIRS_SUPPORT_DIFFERENCE", "CORRESPONDING_BOUNDARY_SHIFT", "GEOMETRIC_INTERVAL_MIDPOINT_DESCRIPTOR", "SUPPORT_WIDTH_DEFORMATION_DESCRIPTOR"}, "four_operators_present", checks)
    mapping = json.loads((OUTPUT / "mapping_direction_semantics_pre_reference.json").read_text(encoding="utf-8"))
    check(mapping["frozen_nominal_slope_sign"] == "POSITIVE", "mapping_nominal_slope_positive", checks)
    check(mapping["all_reviewed_table_slopes_positive"], "mapping_reviewed_slopes_positive", checks)
    check(not mapping["new_mapping_fit_performed"], "no_new_mapping_fit", checks)

    if summary["optical_recovery_gate"] == "PASS":
        sar = pd.read_parquet(OUTPUT / "sar_q95_corresponding_boundary_structural_diagnostic_pre_reference.parquet")
        check(summary["sar_diagnostic_materialized"], "sar_gate_materialized", checks)
        check(len(sar) == summary["unique_sar_base_edges"], "sar_edge_count", checks)
        check(np.allclose(sar["d_width_s_deg"], (sar["destination_theta_max_deg"] - sar["destination_theta_min_deg"]) - (sar["source_theta_max_deg"] - sar["source_theta_min_deg"]), atol=1e-10, rtol=0), "sar_d_width_formula", checks)
        check(set(sar["sar_relation_topology"]).issubset({"ONE_TO_ONE", "SPLIT_LIKE", "MERGE_OR_SHARED_LIKE", "SPLIT_AND_MERGE_LIKE"}), "sar_topology_states", checks)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for record in manifest["outputs"]:
        path = Path(record["path"])
        check(path.exists(), f"manifest_exists::{path.name}", checks)
        check(path.stat().st_size == record["size_bytes"] and sha256_file(path) == record["sha256"], f"manifest_hash::{path.name}", checks)

    old_paths = [
        "tasks/person_m0b1_r02_raw_fragment_angular_direction_20260828",
        "output/person_physics_guided_image_domain_study_20260824/m0b1_r02_raw_fragment_angular_direction_diagnostic",
        "logs/20260828_person_m0b1_raw_fragment_angular_direction.md",
    ]
    result = subprocess.run(
        ["git", "-C", str(WORKSPACE), "diff", "--quiet", "HEAD", "--", *old_paths],
        check=False,
    )
    check(result.returncode == 0, "frozen_m0b1_git_tree_unchanged", checks, f"returncode={result.returncode}")

    report = {
        "schema": "PERSON_M0B1_R_INDEPENDENT_VALIDATION_V1",
        "status": "PASS",
        "passed_checks": len(checks),
        "failed_checks": 0,
        "primary_state": summary["primary_state"],
        "frozen_predecessor_state": summary["frozen_predecessor_state"],
        "checks": checks,
    }
    (OUTPUT / "independent_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
