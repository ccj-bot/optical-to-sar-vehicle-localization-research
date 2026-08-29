from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pandas as pd
from PIL import Image


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824" / "cmr_d0_common_residual_motion_mechanism_development"


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
        "CMR_RUN_SPLIT_FROZEN_BEFORE_DEVELOPMENT.md",
        "cmr_eligible_window_atlas.parquet",
        "optical_common_motion_development.parquet",
        "optical_branch_residual_development.parquet",
        "sar_p0_relative_residual_development.parquet",
        "cross_modal_residual_hypotheses_development.parquet",
        "optical_branch_offline_grounding_interface.csv",
        "CMR_D0_DEVELOPMENT_LOG.md",
        "CMR_V0_MECHANISM_SPECIFICATION_FROZEN.md",
        "CMR_V0_CONFIRMATION_PROTOCOL_DRAFT.md",
        "CMR_D0_FINAL_DEVELOPMENT_REPORT.md",
        "CMR_D0_MULTIMODAL_VISUAL_REVIEW_LEDGER.md",
        "cmr_d0_final_summary.json",
        "cmr_d0_output_manifest.json",
        "development_real_case_registry.csv",
    ]
    for name in required:
        check((OUTPUT / name).exists(), f"exists::{name}")

    atlas = pd.read_parquet(OUTPUT / "cmr_eligible_window_atlas.parquet")
    common = pd.read_parquet(OUTPUT / "optical_common_motion_development.parquet")
    optical = pd.read_parquet(OUTPUT / "optical_branch_residual_development.parquet")
    sar = pd.read_parquet(OUTPUT / "sar_p0_relative_residual_development.parquet")
    cross = pd.read_parquet(OUTPUT / "cross_modal_residual_hypotheses_development.parquet")
    grounding = pd.read_csv(OUTPUT / "optical_branch_offline_grounding_interface.csv")
    summary = json.loads((OUTPUT / "cmr_d0_final_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((OUTPUT / "cmr_d0_output_manifest.json").read_text(encoding="utf-8"))
    cases = pd.read_csv(OUTPUT / "development_real_case_registry.csv")

    check(set(common["run_id"]).issubset({"R01ZF", "R02ZF", "R03ZF"}), "confirmation_not_in_common")
    check(set(optical["run_id"]).issubset({"R01ZF", "R02ZF", "R03ZF"}), "confirmation_not_in_optical_residual")
    check(set(sar["run_id"]).issubset({"R01ZF", "R02ZF", "R03ZF"}), "confirmation_not_in_sar_residual")
    check(set(cross["run_id"]).issubset({"R01ZF", "R02ZF", "R03ZF"}), "confirmation_not_in_cross_modal")
    check(summary["confirmation_mechanism_executed"] is False, "confirmation_not_executed")
    check(manifest["confirmation_executed"] is False, "manifest_confirmation_false")
    check(int(atlas[(atlas.pool == "CONFIRMATION_POOL") & atlas.cross_modal_eligible].shape[0]) > 0, "confirmation_inputs_available")
    check(not bool(cross["residual_direction_used_for_pruning"].any()), "no_pruning")
    check(not bool(cross["identity_assignment_performed"].any()), "no_identity_assignment")
    check(not bool(cross["final_localization_performed"].any()), "no_final_localization")
    check(not bool(optical["reference_used"].any()), "optical_reference_free")
    check(not bool(sar["reference_used"].any()), "sar_reference_free")
    check(not bool(grounding["runtime_use_allowed"].any()), "grounding_offline_only")
    check(summary["magnitude_fit"] is False, "no_magnitude_fit")
    check(summary["weighted_score"] is False, "no_weighted_score")
    check(summary["p0_modified"] is False, "p0_unmodified")
    check(summary["confirmation_readiness"] in {"READY_FOR_CMR_V0_CONFIRMATION", "NOT_READY_FOR_CMR_V0_CONFIRMATION"}, "readiness_state_allowed")
    check(len(common) > 0 and len(optical) > 0 and len(sar) > 0 and len(cross) > 0, "nonempty_mechanism_outputs")
    check(optical["optical_residual_state"].nunique() >= 2, "optical_residual_not_collapsed")
    check(sar["sar_p0_residual_state"].nunique() >= 2, "sar_residual_not_collapsed")
    check(cross["cross_modal_residual_relation"].nunique() >= 2, "cross_modal_not_collapsed")
    check(len(atlas) == summary["scheduled_lag1_windows_all_cross_modal_runs"] == 394, "scheduled_window_accounting")
    check(int(atlas["cross_modal_eligible"].sum()) == summary["cross_modal_eligible_windows_all_pools"] == 205, "eligible_window_accounting")
    definite_below = int(((optical["residual_left_high_deg"] < 0) & (optical["residual_right_high_deg"] < 0)).sum())
    check(definite_below == summary["optical_definite_below_common_count"] == 0, "below_common_absence_audited")

    paired = cases[cases["case_name"].isin(["23_possible_rescue_candidate", "24_deceptive_candidate"])]
    check(len(paired) == 2 and paired["window_id"].nunique() == 1, "paired_rescue_deceptive_same_window")
    cross_case_paths = [OUTPUT / "figures" / "development_cases" / f"{name}.png" for name in ["11_sar_p0_compatible", "23_possible_rescue_candidate", "24_deceptive_candidate"]]
    dimensions = []
    for path in cross_case_paths:
        if path.exists():
            with Image.open(path) as image:
                dimensions.append(image.size)
    check(len(dimensions) == len(cross_case_paths) and all(width >= 2000 and height >= 1800 for width, height in dimensions), "cross_modal_overlay_render_dimensions", dimensions)

    manifest_failures = []
    for item in manifest["files"]:
        path = WORKSPACE / item["path"]
        if not path.exists() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != str(item["sha256"]):
            manifest_failures.append(item["path"])
    check(not manifest_failures, "manifest_files_hash_match", manifest_failures)

    failed = [x for x in checks if not x["pass"]]
    payload = {
        "schema": "PERSON_CMR_D0_INDEPENDENT_VALIDATION_V1",
        "status": "PASS" if not failed else "FAIL",
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "failed_checks": failed,
        "checks": checks,
    }
    (OUTPUT / "cmr_d0_independent_validation.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
