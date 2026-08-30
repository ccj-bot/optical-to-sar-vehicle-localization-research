from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import cv2
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "person_range_temporal_decision_study_20260830"
OUTPUT = WORKSPACE / "output" / "person_range_temporal_decision_study_20260830"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference_diagnostic_only"
FIG = OUTPUT / "figures"
PACK = WORKSPACE / "review_packs" / "PERSON_RANGE_TEMPORAL_DECISION_REVIEW_PACK_20260830"
PACK_ZIP = WORKSPACE / "review_packs" / "PERSON_RANGE_TEMPORAL_DECISION_REVIEW_PACK_20260830.zip"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-pack", action="store_true")
    args = parser.parse_args()
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: object) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": str(detail)})

    required = [
        TASK / "README.md", TASK / "run_person_range_temporal.py", TASK / "validate_person_range_temporal.py",
        OUTPUT / "REPORT.md", OUTPUT / "VISUAL_REVIEW.md", POST / "decision_summary.json",
        PRE / "pre_reference_freeze_manifest.csv", PRE / "pre_reference_freeze_summary.json",
        PRE / "r03_matched_null_control_ledger.csv", PRE / "r03_source_and_matched_null_top_family_records.parquet",
        POST / "range_width_candidate_contraction_summary.csv", POST / "visual_review_ledger.csv",
    ]
    for path in required:
        check(f"required::{path.name}", path.exists(), path)

    manifest = pd.read_csv(PRE / "pre_reference_freeze_manifest.csv", encoding="utf-8-sig")
    freeze_failures = []
    for row in manifest.itertuples(index=False):
        path = PRE / str(row.relative_path)
        if not path.exists() or path.stat().st_size != int(row.bytes) or sha256_file(path) != str(row.sha256):
            freeze_failures.append(str(row.relative_path))
    check("pre_reference_hashes", not freeze_failures, freeze_failures)
    freeze = json.loads((PRE / "pre_reference_freeze_summary.json").read_text(encoding="utf-8"))
    check("pre_reference_manual_reference_false", freeze["manual_reference_loaded"] is False, freeze)

    controls = pd.read_csv(PRE / "r03_matched_null_control_ledger.csv", encoding="utf-8-sig")
    check("matched_null_count", len(controls) == 6, len(controls))
    check("matched_null_zero_detected_person", controls["detected_optical_person_frames"].eq(0).all(), controls["detected_optical_person_frames"].tolist())
    check("matched_null_selection_outcome_blind", controls["selection_outcome_used"].eq(False).all(), controls["selection_outcome_used"].tolist())
    check("matched_null_reference_blind", controls["manual_reference_used"].eq(False).all(), controls["manual_reference_used"].tolist())
    check("matched_null_duration_exact", controls["duration_frames"].eq(48).all(), controls["duration_frames"].tolist())

    top = pd.read_parquet(PRE / "r03_source_and_matched_null_top_family_records.parquet")
    source = top[top["trajectory_kind"] == "SOURCE_MOVING_PERSON_CORRIDOR"].iloc[0]
    null = top[top["trajectory_kind"] == "MATCHED_NO_PERSON_TIME_SHIFT"]
    check("source_recurrence_exact", int(source.admissible_frame_count) == 48 and int(source.unique_frame_count) == 5, source.to_dict())
    check("null_can_exceed_source_unique", int(null.unique_frame_count.max()) >= int(source.unique_frame_count), null.unique_frame_count.tolist())
    check("background_full_occupancy_exists", float(null.temporal_occupancy.max()) == 1.0, null.temporal_occupancy.tolist())

    geometry = pd.read_parquet(PRE / "r03_source_and_matched_null_trajectory_geometry.parquet")
    sg = geometry[geometry["trajectory_kind"] == "SOURCE_MOVING_PERSON_CORRIDOR"].iloc[0]
    ng = geometry[geometry["trajectory_kind"] == "MATCHED_NO_PERSON_TIME_SHIFT"]
    check("trajectory_absolute_depth_not_claimed", geometry["absolute_depth_observable_from_this_relation"].eq(False).all(), geometry.absolute_depth_observable_from_this_relation.tolist())
    check("null_smoother_than_source_exists", float(ng.theta_from_corridor_median_abs_residual_deg.min()) < float(sg.theta_from_corridor_median_abs_residual_deg), [float(ng.theta_from_corridor_median_abs_residual_deg.min()), float(sg.theta_from_corridor_median_abs_residual_deg)])

    calibration = pd.read_csv(PRE / "runtime_coarse_range_calibration_inventory.csv", encoding="utf-8-sig")
    missing = set(calibration[calibration["status"].str.startswith("MISSING")]["interface"])
    expected_missing = {"camera_K", "camera_height", "camera_pitch_roll", "camera_radar_extrinsic_R_t", "ground_plane", "platform_pose_velocity"}
    check("required_geometry_missing", missing == expected_missing, sorted(missing))

    decision = json.loads((POST / "decision_summary.json").read_text(encoding="utf-8"))
    check("decision_pm2", decision["range_width_decision"]["recommended_target"] == "CONSERVATIVE_HALF_WIDTH_ABOUT_2M", decision["range_width_decision"])
    check("decision_no_near_exact_counterexample", decision["near_exact_range_still_multiple_family_counterexample_exists"] is False, decision["near_exact_range_still_multiple_family_counterexample_exists"])
    check("decision_r04_false", decision["r04_accessed"] is False, decision["r04_accessed"])
    check("source_reference_radial_support", decision["source_reference_radial_support_retained_fraction"] == 1.0, decision["source_reference_radial_support_retained_fraction"])

    range_summary = pd.read_csv(POST / "range_width_candidate_contraction_summary.csv", encoding="utf-8-sig")
    medians = range_summary.set_index("range_tolerance_m")["N_family_after_median"].to_dict()
    check("range_medians", medians[3.0] == 2.0 and medians[2.0] == 1.0 and medians[1.0] == 1.0, medians)
    check("range_reference_retained", range_summary["reference_radial_support_retained_fraction"].eq(1.0).all(), range_summary.reference_radial_support_retained_fraction.tolist())

    visual = pd.read_csv(POST / "visual_review_ledger.csv", encoding="utf-8-sig")
    check("visual_ledger_case_count", len(visual) >= 9, len(visual))
    check("visual_computed_separate", {"computed_verdict", "visual_verdict", "authority_scope"}.issubset(visual.columns), visual.columns.tolist())
    check("visual_has_null_counterexample", visual["case_id"].str.startswith("R03_NULL").any(), visual.case_id.tolist())
    check("visual_has_range_success_failure", {"R01_PM3_SUCCESS", "R01_PM3_FAILURE", "R01_PM2_FAILURE"}.issubset(set(visual.case_id)), visual.case_id.tolist())

    figures = sorted(FIG.glob("*.png"))
    check("figure_count", len(figures) >= 10, len(figures))
    unreadable = [str(path) for path in figures if cv2.imread(str(path), cv2.IMREAD_COLOR) is None]
    check("figures_readable", not unreadable, unreadable)
    check("core_mechanism_figure", (FIG / "04_core_candidate_support_contraction_mechanism.png").exists(), FIG)

    report = (OUTPUT / "REPORT.md").read_text(encoding="utf-8")
    for phrase in ["±2 m", "matched", "footpoint", "R04 accessed: `false`", "not a final PERSON box"]:
        check(f"report_phrase::{phrase}", phrase in report, phrase)

    if args.require_pack:
        check("pack_directory", PACK.exists(), PACK)
        check("pack_zip", PACK_ZIP.exists(), PACK_ZIP)
        pack_manifest = pd.read_csv(PACK / "PACK_MANIFEST.csv", encoding="utf-8-sig")
        pack_failures = []
        for row in pack_manifest.itertuples(index=False):
            path = PACK / str(row.relative_path)
            if not path.exists() or path.stat().st_size != int(row.bytes) or sha256_file(path) != str(row.sha256):
                pack_failures.append(str(row.relative_path))
        check("pack_manifest_hashes", not pack_failures, pack_failures)
        with zipfile.ZipFile(PACK_ZIP) as archive:
            bad = archive.testzip()
            names = archive.namelist()
        check("zip_integrity", bad is None, bad)
        check("zip_contains_pack", len(names) > 100 and all(name.startswith(PACK.name + "/") for name in names), len(names))
        pack_summary = json.loads((PACK / "PACK_SUMMARY.json").read_text(encoding="utf-8"))
        check("pack_raw_counts", pack_summary["raw_sar_count"] >= 70 and pack_summary["raw_optical_count"] >= 50 and pack_summary["selected_q95_npz_count"] >= 70, pack_summary)

    failures = [item for item in checks if not item["passed"]]
    result = {"validator": "PERSON_RANGE_TEMPORAL_INDEPENDENT_VALIDATOR_V1", "status": "PASS" if not failures else "FAIL", "passed": len(checks) - len(failures), "total": len(checks), "failures": failures, "checks": checks}
    (OUTPUT / "validation_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("validator", "status", "passed", "total", "failures")}, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
