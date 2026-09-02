from __future__ import annotations

import hashlib
import json
import py_compile
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


TASK = Path(__file__).resolve().parent
WORKSPACE = TASK.parents[1]
OUT = WORKSPACE / "output" / "person_r02_scene_depth_value_test_20260902"
PRE = OUT / "pre_reference"
POST = OUT / "post_reference_evaluation_only"
PACK = WORKSPACE / "review_packs" / "PERSON_R02_SCENE_DEPTH_VALUE_TEST_20260903.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower()


def array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).view(np.uint8)).hexdigest().lower()


class Validator:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def check(self, name: str, condition: bool, detail: str) -> None:
        self.rows.append({"check": name, "passed": bool(condition), "detail": detail})
        print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")

    def finish(self) -> None:
        table = pd.DataFrame(self.rows)
        table.to_csv(OUT / "VALIDATION_RESULTS.csv", index=False, encoding="utf-8-sig")
        summary = {"checks": len(table), "passed": int(table.passed.sum()), "failed": int((~table.passed).sum()), "status": "PASS" if table.passed.all() else "FAIL"}
        (OUT / "VALIDATION_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary))
        if not table.passed.all():
            raise SystemExit(1)


def main() -> None:
    v = Validator()
    required = [OUT / "REPORT.md", OUT / "SUMMARY.json", OUT / "OUTPUT_MANIFEST.csv", PRE / "PRE_REFERENCE_FREEZE_MANIFEST.json", PRE / "runtime_support_burden_pre_reference.parquet", POST / "reference_support_retention_post_reference.parquet", OUT / "figures" / "final_review" / "strongest_success.png", OUT / "figures" / "final_review" / "strongest_residual_clutter.png", OUT / "figures" / "final_review" / "reference_overlap_and_boundary_theta_gap.png", PACK]
    for path in required:
        v.check(f"exists::{path.name}", path.exists() and path.stat().st_size > 0, str(path))

    for script in ["prepare_pre_reference_review.py", "freeze_pre_reference.py", "evaluate_post_reference.py", "build_report.py", "validate_scene_depth_value.py"]:
        try:
            with tempfile.TemporaryDirectory() as directory:
                py_compile.compile(str(TASK / script), cfile=str(Path(directory) / f"{script}.pyc"), doraise=True)
            ok, detail = True, "compiled"
        except Exception as error:
            ok, detail = False, str(error)
        v.check(f"compile::{script}", ok, detail)

    freeze = json.loads((PRE / "PRE_REFERENCE_FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    root_lines, hash_ok = [], True
    for item in freeze["files"]:
        path = OUT / item["path"]
        hash_ok &= path.exists() and path.stat().st_size == int(item["bytes"]) and sha256(path) == item["sha256"]
        root_lines.append(f"{item['path']}|{item['bytes']}|{item['sha256']}")
    root = hashlib.sha256("\n".join(root_lines).encode("utf-8")).hexdigest().lower()
    v.check("freeze_file_hashes", hash_ok, f"files={len(freeze['files'])}")
    v.check("freeze_root_hash", root == freeze["pre_reference_root_sha256"], root)
    v.check("freeze_reference_closed", freeze["manual_person_sar_reference_opened"] is False, "false")
    v.check("freeze_scope_flags", freeze["r04_accessed"] is False and freeze["f66_used"] is False and freeze["boundary_propagation_modified"] is False and freeze["final_localization_run"] is False, "all false")

    labels = pd.read_parquet(PRE / "optical_person_scene_layer_visual_cases_frozen_pre_reference.parquet")
    v.check("visual_case_denominator", len(labels) == 24 and labels.optical_review_id.nunique() == 24, f"rows={len(labels)}")
    v.check("visual_layer_distribution", labels.scene_layer.value_counts().to_dict() == {"L2": 23, "UNCERTAIN": 1}, str(labels.scene_layer.value_counts().to_dict()))
    v.check("visual_no_reference", (~labels.manual_person_reference_used.astype(bool)).all(), "all false")

    boundaries = pd.read_parquet(PRE / "BOUNDARY_VALUE_ELIGIBLE_GEOMETRY_PRE_REFERENCE.parquet")
    v.check("boundary_frame_denominator", boundaries.sar_frame_index.nunique() == 31 and len(boundaries) == 62, f"frames={boundaries.sar_frame_index.nunique()}")
    v.check("known_unsafe_excluded", not set(boundaries.sar_frame_index.astype(int)) & {58, 66, 67, 165, 260, 270, 405, 482}, "unsafe intersection empty")
    v.check("boundary_only_r02", set(boundaries.run_id) == {"R02ZF"}, str(set(boundaries.run_id)))

    burden = pd.read_parquet(PRE / "runtime_support_burden_pre_reference.parquet")
    v.check("burden_rows", len(burden) == 81 and burden.shell_id.nunique() == 27, f"rows={len(burden)} shells={burden.shell_id.nunique()}")
    v.check("three_conditions", set(burden.condition) == {"ANGLE_ONLY", "ANGLE_PLUS_ONE_CURB_HALFSPACE", "ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER"}, str(set(burden.condition)))
    v.check("applied_denominators", int((burden.condition.eq("ANGLE_PLUS_ONE_CURB_HALFSPACE") & burden.condition_applied).sum()) == 19 and int((burden.condition.eq("ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER") & burden.condition_applied).sum()) == 13, "one=19 two=13")
    v.check("exact_pixel_intersection", burden.exact_q95_pixel_intersection.astype(bool).all(), "all true")
    v.check("family_assignment_complete", burden.unassigned_family_count.eq(0).all(), "zero unassigned")
    base = burden[burden.condition.eq("ANGLE_ONLY")].set_index("shell_id")
    nonincrease = True
    for condition in ["ANGLE_PLUS_ONE_CURB_HALFSPACE", "ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER"]:
        current = burden[burden.condition.eq(condition)].set_index("shell_id")
        nonincrease &= (current.N_region <= base.N_region).all() and (current.N_family <= base.N_family).all() and (current.A_candidate_px <= base.A_candidate_px).all()
    v.check("support_nonincrease", nonincrease, "region family area")

    mask_ok = True
    for row in burden.itertuples(index=False):
        path = OUT / row.support_mask_file
        key = {"ANGLE_ONLY": "angle_only_packbits", "ANGLE_PLUS_ONE_CURB_HALFSPACE": "one_curb_packbits", "ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER": "two_boundary_packbits"}[row.condition]
        with np.load(path, allow_pickle=False) as archive:
            shape = tuple(int(value) for value in archive["shape"])
            count = int(np.prod(shape))
            mask = np.unpackbits(archive[key])[:count].reshape(shape).astype(bool)
        mask_ok &= int(mask.sum()) == int(row.support_pixel_count) and array_sha256(mask) == row.support_mask_sha256
    v.check("support_mask_roundtrip_hashes", mask_ok, f"rows={len(burden)}")

    summary = json.loads((OUT / "SUMMARY.json").read_text(encoding="utf-8"))
    two = summary["two_boundary_contraction"]
    v.check("two_boundary_core_numbers", two["rows"] == 13 and two["N_family_before_median"] == 13 and two["N_family_after_median"] == 10 and abs(two["area_reduction_fraction_median"] - 0.1250691754) < 1e-9, json.dumps(two))
    common = summary["common_comparison"]
    v.check("incremental_vs_one_curb", common["rows"] == 8 and common["family_change_rows_two_vs_one"] == 0 and common["incremental_area_median"] < 0.03, json.dumps(common))
    v.check("decision_and_scope", summary["decision"] == "INSUFFICIENT_PERSON_OVERLAP" and summary["uncontaminated_two_boundary_applied_reference_rows"] == 0 and summary["worth_repairing_f66_now"] is False and summary["r04_accessed"] is False and summary["final_localization_run"] is False, summary["decision"])

    retention = pd.read_parquet(POST / "reference_support_retention_post_reference.parquet")
    v.check("reference_denominator", retention.shell_id.nunique() == 2 and len(retention) == 6, f"shells={retention.shell_id.nunique()} rows={len(retention)}")
    v.check("operator_contamination_disclosed", int(retention[retention.condition.eq("ANGLE_ONLY")].operator_contaminated_known_case.sum()) == 1, "one disclosed")
    clean_two = retention[retention.condition.eq("ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER") & retention.confirmatory_uncontaminated]
    v.check("clean_two_boundary_not_applied", len(clean_two) == 1 and int(clean_two.condition_applied.sum()) == 0, clean_two.to_json(orient="records"))
    v.check("false_prune_not_fabricated", not summary["false_scene_layer_prune_rate_estimable"] and int(retention.FALSE_SCENE_LAYER_PRUNE.sum()) == 0, "rate unavailable; count zero due no application")
    gate = json.loads((POST / "post_reference_gate_audit.json").read_text(encoding="utf-8"))
    v.check("post_gate_bound_to_freeze", gate["pre_reference_root_sha256"] == freeze["pre_reference_root_sha256"] and gate["reference_opened_only_after_freeze_validation"] is True, gate["pre_reference_root_sha256"])

    report = (OUT / "REPORT.md").read_text(encoding="utf-8")
    for phrase in ["13 to 10 regions/families", "12.5% median area contraction", "INSUFFICIENT_PERSON_OVERLAP", "zero uncontaminated applied reference rows", "does not justify repairing F66", "No identity, center, box"]:
        v.check(f"report_phrase::{phrase}", phrase in report, phrase)

    v.check("pack_hash", sha256(PACK) == summary["review_pack_sha256"], summary["review_pack_sha256"])
    v.check("pack_size", PACK.stat().st_size == int(summary["review_pack_bytes"]), str(PACK.stat().st_size))
    with zipfile.ZipFile(PACK) as archive:
        names = set(archive.namelist())
    required_names = {"README.md", "PACK_MANIFEST.csv", "artifacts/REPORT.md", "artifacts/figures/final_review/strongest_success.png", "artifacts/figures/final_review/strongest_residual_clutter.png", "artifacts/figures/final_review/reference_overlap_and_boundary_theta_gap.png", "artifacts/pre_reference/PRE_REFERENCE_FREEZE_MANIFEST.json"}
    v.check("pack_required_entries", required_names.issubset(names), str(sorted(required_names - names)))

    manifest = pd.read_csv(OUT / "OUTPUT_MANIFEST.csv")
    output_hashes = all((OUT / row.relative_path).exists() and (OUT / row.relative_path).stat().st_size == int(row.bytes) and sha256(OUT / row.relative_path) == row.sha256 for row in manifest.itertuples(index=False))
    v.check("output_manifest_hashes", output_hashes, f"rows={len(manifest)}")
    v.finish()


if __name__ == "__main__":
    main()
