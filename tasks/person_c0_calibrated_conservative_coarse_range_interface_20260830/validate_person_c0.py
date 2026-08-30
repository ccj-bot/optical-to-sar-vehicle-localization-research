from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

import cv2
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "person_c0_calibrated_conservative_coarse_range_interface_20260830"
OUTPUT = WORKSPACE / "output" / "person_c0_calibrated_conservative_coarse_range_interface_20260830"
PRE = OUTPUT / "pre_reference"
FIG = OUTPUT / "figures"
PACK = WORKSPACE / "review_packs" / "PERSON_C0_COARSE_RANGE_CALIBRATION_REVIEW_PACK_20260830.zip"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-pack", action="store_true")
    args = parser.parse_args()
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": bool(condition), "detail": detail})

    required = [
        PRE / "calibration_asset_registry.csv",
        PRE / "asset_search_hits.csv",
        PRE / "asset_search_files.csv",
        PRE / "acquisition_metadata.csv",
        PRE / "image_coordinate_chain.csv",
        PRE / "single_frame_vs_temporal_requirement_matrix.csv",
        PRE / "range_interval_runtime.csv",
        PRE / "visual_candidate_ledger.csv",
        PRE / "audit_summary.json",
        PRE / "pre_reference_freeze_manifest.csv",
        PRE / "pre_reference_freeze_summary.json",
        OUTPUT / "REPORT.md",
        OUTPUT / "VISUAL_REVIEW.md",
        OUTPUT / "PERSON_C0_MINIMUM_CALIBRATION_CHECKLIST.md",
    ]
    for path in required:
        check(f"required:{path.name}", path.exists() and path.stat().st_size > 0, str(path))

    registry = pd.read_csv(PRE / "calibration_asset_registry.csv", encoding="utf-8-sig")
    expected_columns = {"asset_name", "asset_type", "path", "source", "coordinate_frame", "resolution", "runtime_available", "verified", "semantics", "dependency", "usable_for_person_range", "reason", "status"}
    check("registry_columns", expected_columns.issubset(registry.columns), str(sorted(registry.columns)))
    allowed = {"FOUND_AND_VERIFIED", "FOUND_BUT_SEMANTICS_UNCERTAIN", "FOUND_BUT_INCOMPATIBLE", "MISSING"}
    check("registry_status_vocabulary", set(registry["status"]).issubset(allowed), str(sorted(set(registry["status"]))))
    required_missing = {"person_camera_intrinsics_K", "person_camera_height", "person_camera_pitch_roll", "person_camera_radar_R_t", "local_ground_plane", "runtime_footpoint_interval"}
    actual_missing = set(registry[registry["status"] == "MISSING"]["asset_name"])
    check("minimum_blockers_explicit", required_missing.issubset(actual_missing), str(sorted(actual_missing)))
    pose = registry[registry["asset_name"] == "global_platform_pose"].iloc[0]
    check("global_pose_not_single_frame_required", pose["usable_for_person_range"] == "NOT_REQUIRED_FOR_SINGLE_FRAME", str(pose.to_dict()))

    chain = pd.read_csv(PRE / "image_coordinate_chain.csv", encoding="utf-8-sig")
    check("coordinate_chain_three_runs", set(chain["run_id"]) == {"R01ZF", "R02ZF", "R03ZF"}, str(chain["run_id"].value_counts().to_dict()))
    check("coordinate_chain_native_resolution", set(zip(chain["width_px"], chain["height_px"])) == {(3840, 2160)}, str(set(zip(chain["width_px"], chain["height_px"]))))
    for operation in ("RESIZE", "CROP", "LETTERBOX"):
        subset = chain[chain["stage"] == operation]
        check(f"coordinate_chain_{operation.lower()}_none", len(subset) == 3 and subset["operation"].str.startswith("NONE").all(), subset.to_json(orient="records"))

    requirements = pd.read_csv(PRE / "single_frame_vs_temporal_requirement_matrix.csv", encoding="utf-8-sig")
    global_row = requirements[requirements["quantity"] == "global platform pose"].iloc[0]
    check("requirement_split", global_row["single_frame_relative_range"] == "NOT_REQUIRED" and "REQUIRED" in global_row["temporal_world_registration"], str(global_row.to_dict()))

    runtime = pd.read_csv(PRE / "range_interval_runtime.csv", encoding="utf-8-sig")
    check("runtime_denominator", len(runtime) == 823, str(len(runtime)))
    check("all_range_unavailable", (runtime["range_state"] == "RANGE_UNAVAILABLE").all(), str(runtime["range_state"].value_counts().to_dict()))
    check("no_numeric_interval", runtime[["range_min_m", "range_max_m", "range_half_width_m"]].isna().all().all(), "range columns must be blank")
    check("angle_only_fallback_full_range", (runtime["fallback_range_min_m"] == 0).all() and (runtime["fallback_range_max_m"] == 20).all(), "0..20 m render support")
    check("fallback_candidate_burden_equal", (runtime["N_region_angle_only"] == runtime["N_region_angle_plus_runtime_range"]).all(), "no invented contraction")
    check("no_person_range_rejection", (~runtime["person_rejected_due_to_range"].astype(bool)).all(), "range unavailable cannot reject")
    check("no_manual_reference_runtime", (~runtime["manual_reference_used"].astype(bool)).all(), "GT blind")

    visual = pd.read_csv(PRE / "visual_candidate_ledger.csv", encoding="utf-8-sig")
    expected_states = {"FOOTPOINT_OBSERVABLE", "FOOTPOINT_PARTIAL", "FOOTPOINT_CENSORED", "FOOTPOINT_AMBIGUOUS", "FOOTPOINT_UNAVAILABLE"}
    check("visual_states_complete", expected_states.issubset(set(visual["visual_footpoint_state"])), str(visual["visual_footpoint_state"].tolist()))
    check("bbox_bottom_not_exact", (visual["computed_verdict"] == "BBOX_BOTTOM_NOT_ACCEPTED_AS_EXACT_FOOTPOINT").all(), "all visual rows")

    figure_names = [
        "01_verified_hardware_coordinate_geometry.png",
        "02_footpoint_ray_bundle_range_interval_blocked.png",
        "03_angle_only_vs_angle_plus_range_fallback.png",
        "04_interval_width_candidate_burden_blocked.png",
        "05_clean_ambiguous_censored_footpoint_cases.png",
    ]
    for name in figure_names:
        path = FIG / name
        image = cv2.imread(str(path), cv2.IMREAD_COLOR) if path.exists() else None
        check(f"figure:{name}", image is not None and image.shape[0] >= 500 and image.shape[1] >= 900, "missing or too small" if image is None else str(image.shape))

    freeze = json.loads((PRE / "pre_reference_freeze_summary.json").read_text(encoding="utf-8"))
    manifest = pd.read_csv(PRE / "pre_reference_freeze_manifest.csv", encoding="utf-8-sig")
    bad_hashes = []
    for item in manifest.itertuples(index=False):
        path = PRE / str(item.relative_path)
        if not path.exists() or path.stat().st_size != int(item.bytes) or sha256_file(path) != str(item.sha256):
            bad_hashes.append(str(item.relative_path))
    root_hash = hashlib.sha256("\n".join(f"{row.relative_path}|{int(row.bytes)}|{row.sha256}" for row in manifest.itertuples(index=False)).encode("utf-8")).hexdigest()
    check("freeze_files_intact", not bad_hashes, str(bad_hashes))
    check("freeze_root_hash", root_hash == freeze["root_sha256"], f"{root_hash} vs {freeze['root_sha256']}")
    check("freeze_no_reference", freeze["manual_reference_loaded"] is False and freeze["r04_accessed"] is False, str(freeze))

    hits = pd.read_csv(PRE / "asset_search_hits.csv", encoding="utf-8-sig")
    path_fields = "\n".join(registry["path"].fillna("").astype(str).tolist() + hits["path"].fillna("").astype(str).tolist())
    check("no_r04_input_paths", re.search(r"R04ZF|[\\/_-]R04[\\/_-]", path_fields, re.I) is None, "registry and hit paths")
    check("no_old_work_input_paths", "old_work" not in path_fields.lower(), "registry and hit paths")

    report = (OUTPUT / "REPORT.md").read_text(encoding="utf-8")
    checklist = (OUTPUT / "PERSON_C0_MINIMUM_CALIBRATION_CHECKLIST.md").read_text(encoding="utf-8")
    check("report_direct_answer", "我们现在还不具备用几何方法产生 runtime 粗距离区间的条件" in report, "first answer")
    check("report_nonclaims", "Omega" in report and "final PERSON center/box" in report, "boundary statement")
    check("checklist_operational", all(token in checklist for token in ["Charuco", "3840x2160", "camera_to_radar_extrinsic.yaml", "FOOTPOINT_OBSERVABLE", "Integration gate"]), "minimum field protocol")

    source = (TASK / "run_person_c0.py").read_text(encoding="utf-8")
    check("no_reference_dependency_in_runner", "r01_r02_r03_manual_range_reference" not in source and "B0_POST" not in source, "runner must stay pre-reference")

    if args.require_pack:
        check("pack_exists", PACK.exists() and PACK.stat().st_size > 0, str(PACK))
        if PACK.exists():
            with zipfile.ZipFile(PACK) as archive:
                names = archive.namelist()
                bad = archive.testzip()
            check("pack_zip_integrity", bad is None, str(bad))
            check("pack_required_content", any(name.endswith("manifest.csv") for name in names) and any(name.endswith("REPORT.md") for name in names) and any("raw_optical_examples/" in name for name in names) and any("raw_sar_examples/" in name for name in names) and any("q95_masks/" in name for name in names), str(len(names)))
            tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(PACK.relative_to(WORKSPACE)).replace("\\", "/")], cwd=WORKSPACE, text=True, capture_output=True)
            check("pack_not_tracked", tracked.returncode != 0, tracked.stdout + tracked.stderr)

    passed = sum(bool(item["passed"]) for item in checks)
    result = {"status": "PASS" if passed == len(checks) else "FAIL", "passed": passed, "total": len(checks), "checks": checks}
    (OUTPUT / "validation_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "passed": passed, "total": len(checks), "failed": [item for item in checks if not item["passed"]]}, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

