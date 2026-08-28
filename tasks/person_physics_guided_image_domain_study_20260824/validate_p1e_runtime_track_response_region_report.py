#!/usr/bin/env python3
"""Independent audit for the runtime-track / response-region HTML report."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
OUTPUT_DIR = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "p1e_sar_only_response_interface"
    / "runtime_track_response_region_minimal_v1"
)
ANALYSIS_SCRIPT = TASK_DIR / "run_p1e_runtime_track_response_region_minimal.py"
REPORT_SCRIPT = TASK_DIR / "render_p1e_runtime_track_response_region_report.py"
REPORT_PATH = OUTPUT_DIR / "P1E_RUNTIME_TRACK_RESPONSE_REGION_MINIMAL_REPORT.html"
VALIDATION_PATH = OUTPUT_DIR / "report_validation.json"
SUMMARY_PATH = OUTPUT_DIR / "diagnostic_summary.json"
DERIVED_PATH = OUTPUT_DIR / "report_derived_metrics.json"
SHELL_PATH = OUTPUT_DIR / "track_shell_definition_table.csv"
REGION_PATH = OUTPUT_DIR / "response_region_table.csv"
REFERENCE_REGION_PATH = OUTPUT_DIR / "offline_reference_response_region_evaluation.csv"
ENTITY_REGION_PATH = OUTPUT_DIR / "offline_observation_entity_response_region_evaluation.csv"
TRACK_SUMMARY_PATH = OUTPUT_DIR / "offline_reference_track_summary.csv"
ASSIGNMENT_PATH = OUTPUT_DIR / "offline_one_to_one_track_reference_assignment.csv"
INTERSECTION_PATH = OUTPUT_DIR / "response_region_track_shell_intersection.csv"
PARITY_PATH = OUTPUT_DIR / "candidate_recomputation_parity.csv"
CASE_PATH = OUTPUT_DIR / "case_registry.csv"
MASK_DIR = OUTPUT_DIR / "response_region_masks"

RAW_INTERFACE = "RAW_DETECTED_FRAGMENT_ALL"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def close(left: Any, right: float, tolerance: float = 1e-12) -> bool:
    try:
        return math.isfinite(float(left)) and abs(float(left) - right) <= tolerance
    except (TypeError, ValueError):
        return False


def validate() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    required = [
        ANALYSIS_SCRIPT,
        REPORT_SCRIPT,
        REPORT_PATH,
        SUMMARY_PATH,
        DERIVED_PATH,
        SHELL_PATH,
        REGION_PATH,
        REFERENCE_REGION_PATH,
        ENTITY_REGION_PATH,
        TRACK_SUMMARY_PATH,
        ASSIGNMENT_PATH,
        INTERSECTION_PATH,
        PARITY_PATH,
        CASE_PATH,
    ]
    add(
        "required_inputs_and_report_exist",
        all(path.is_file() for path in required),
        [str(path) for path in required if not path.is_file()],
    )
    if not all(path.is_file() for path in required):
        status = "FAIL"
        return {
            "schema": "PERSON_P1E_RUNTIME_TRACK_RESPONSE_REGION_REPORT_VALIDATION_V1",
            "created_at": now_iso(),
            "status": status,
            "checks_passed": sum(check["pass"] for check in checks),
            "checks_total": len(checks),
            "checks": checks,
        }

    summary = load_json(SUMMARY_PATH)
    derived = load_json(DERIVED_PATH)
    html_text = REPORT_PATH.read_text(encoding="utf-8")
    shells = pd.read_csv(SHELL_PATH, low_memory=False)
    regions = pd.read_csv(REGION_PATH, low_memory=False)
    reference_region = pd.read_csv(REFERENCE_REGION_PATH, low_memory=False)
    entity_region = pd.read_csv(ENTITY_REGION_PATH, low_memory=False)
    track_summary = pd.read_csv(TRACK_SUMMARY_PATH, low_memory=False)
    assignments = pd.read_csv(ASSIGNMENT_PATH, low_memory=False)
    intersections = pd.read_csv(INTERSECTION_PATH, low_memory=False)
    parity = pd.read_csv(PARITY_PATH, low_memory=False)
    cases = pd.read_csv(CASE_PATH, low_memory=False)

    add(
        "analysis_and_contract_input_hashes_match",
        all(bool(row.get("match")) for row in summary["input_hash_checks"])
        and all(bool(row.get("match")) for row in summary["contract_input_checks"]),
        {
            "input_hash_checks": summary["input_hash_checks"],
            "contract_input_checks": summary["contract_input_checks"],
        },
    )
    add(
        "analysis_script_hash_matches_frozen_summary",
        summary["analysis_script_sha256"] == sha256_file(ANALYSIS_SCRIPT)
        and derived["analysis_script_sha256"] == sha256_file(ANALYSIS_SCRIPT),
        {
            "summary": summary["analysis_script_sha256"],
            "derived": derived["analysis_script_sha256"],
            "actual": sha256_file(ANALYSIS_SCRIPT),
        },
    )
    add(
        "report_script_hash_matches_derived_record",
        derived["report_script_sha256"] == sha256_file(REPORT_SCRIPT),
        {"derived": derived["report_script_sha256"], "actual": sha256_file(REPORT_SCRIPT)},
    )

    counts = summary["counts"]
    add(
        "key_row_counts_match_summary",
        len(shells) == counts["track_shell_definition_rows"]
        and len(regions) == counts["response_region_rows"]
        and len(reference_region) == counts["reference_region_rows"]
        and len(entity_region) == counts["observation_entity_region_rows"]
        and len(track_summary) == counts["complete_one_to_one_assignment_rows"]
        and len(assignments) == counts["complete_one_to_one_assignment_rows"]
        and len(cases) == counts["case_count"]
        and len(intersections) == 26034,
        {
            "shells": len(shells),
            "regions": len(regions),
            "reference_region": len(reference_region),
            "entity_region": len(entity_region),
            "track_summary": len(track_summary),
            "assignments": len(assignments),
            "intersections": len(intersections),
            "cases": len(cases),
        },
    )

    mask_paths = sorted(MASK_DIR.glob("*.npz"))
    frame_uids = set(parity["frame_uid"].astype(str))
    add(
        "all_398_region_masks_present",
        len(mask_paths) == 398 and {path.stem for path in mask_paths} == frame_uids,
        {"mask_count": len(mask_paths), "frame_uid_count": len(frame_uids)},
    )

    covered = parity[as_bool(parity["candidate_artifact_frame_covered"])]
    uncovered = parity[~as_bool(parity["candidate_artifact_frame_covered"])]
    add(
        "candidate_parity_and_uncovered_semantics_are_exact",
        len(covered) == 126
        and len(uncovered) == 272
        and as_bool(covered["all_candidate_fields_match"]).all()
        and set(covered["parity_status"]) == {"COVERED_FRAME_EXACT_MATCH"}
        and set(uncovered["parity_status"]) == {"NO_LEGACY_CANDIDATE_ARTIFACT_FOR_FRAME"}
        and close(covered["max_coordinate_error_px"].max(), 0.0)
        and float(covered["max_score_abs_error"].max()) <= 1.2e-16
        and float(covered["max_support_fraction_abs_error"].max()) <= 1.2e-16,
        {
            "covered": len(covered),
            "uncovered": len(uncovered),
            "covered_statuses": sorted(set(covered["parity_status"])),
            "uncovered_statuses": sorted(set(uncovered["parity_status"])),
            "max_coordinate_error_px": float(covered["max_coordinate_error_px"].max()),
            "max_score_abs_error": float(covered["max_score_abs_error"].max()),
            "max_support_fraction_abs_error": float(covered["max_support_fraction_abs_error"].max()),
        },
    )

    add(
        "runtime_shell_generation_boundaries_hold",
        not as_bool(shells["physical_target_id_used_for_shell_generation"]).any()
        and not as_bool(shells["reference_used_for_shell_generation"]).any()
        and not as_bool(shells["sar_range_assigned_by_optical"]).any()
        and not as_bool(shells["strict_runtime_identity_claimed"]).any(),
        {
            "physical_target_id_used": int(as_bool(shells["physical_target_id_used_for_shell_generation"]).sum()),
            "reference_used": int(as_bool(shells["reference_used_for_shell_generation"]).sum()),
            "sar_range_assigned": int(as_bool(shells["sar_range_assigned_by_optical"]).sum()),
            "strict_runtime_identity_claimed": int(as_bool(shells["strict_runtime_identity_claimed"]).sum()),
        },
    )
    add(
        "response_region_generation_boundaries_hold",
        not as_bool(regions["reference_used_for_region_generation"]).any()
        and not as_bool(regions["region_is_final_person_box"]).any(),
        {
            "reference_used": int(as_bool(regions["reference_used_for_region_generation"]).sum()),
            "final_person_box": int(as_bool(regions["region_is_final_person_box"]).sum()),
        },
    )

    q95 = reference_region[reference_region["percentile_tag"] == "Q095"]
    add(
        "headline_response_region_metrics_recompute",
        len(q95) == 251
        and close(as_bool(q95["reference_center_directly_inside_region"]).mean(), 0.9800796812749004)
        and close(as_bool(q95["region_near_reference_0p30m"]).mean(), 0.9920318725099602)
        and int((q95["representation_state"] == "PEAK_MISSING_REGION_PRESENT").sum()) == 2
        and int((q95["superlevel_presence_state"] == "Q090_ONLY_REGION_PRESENT").sum()) == 2
        and close(as_bool(q95["shared_region_flag"]).mean(), 0.3745019920318725),
        {
            "rows": len(q95),
            "direct_inside": float(as_bool(q95["reference_center_directly_inside_region"]).mean()),
            "near_0p30m": float(as_bool(q95["region_near_reference_0p30m"]).mean()),
            "peak_missing_region_present": int((q95["representation_state"] == "PEAK_MISSING_REGION_PRESENT").sum()),
            "q090_only": int((q95["superlevel_presence_state"] == "Q090_ONLY_REGION_PRESENT").sum()),
            "shared": float(as_bool(q95["shared_region_flag"]).mean()),
        },
    )

    q95_entities = entity_region[entity_region["percentile_tag"] == "Q095"]
    direct_by_kind = {
        kind: float(as_bool(group["entity_directly_inside_region"]).mean())
        for kind, group in q95_entities.groupby("entity_kind")
    }
    add(
        "q95_reference_and_control_direction_is_preserved",
        direct_by_kind["PERSON_REFERENCE"] > direct_by_kind["LOCAL_COMPETING_CONTROL"]
        > direct_by_kind["GEOMETRY_MATCHED_CONTROL"]
        and direct_by_kind["PERSON_REFERENCE"] > direct_by_kind["FIXED_OFFSET_CONTROL"],
        direct_by_kind,
    )

    r02 = track_summary[
        (track_summary["run_id"] == "R02ZF")
        & (track_summary["interface_kind"] == RAW_INTERFACE)
        & (track_summary["time_window_half_width_ms"] == 250)
    ]
    expected_ranks = {
        "01": (11.0, 3.0, 2.0),
        "02": (18.0, 6.0, 4.0),
        "03": (1.0, 1.0, 1.0),
        "04": (1.0, 1.0, 1.0),
    }
    actual_ranks: dict[str, tuple[float, float, float]] = {}
    rank_ok = True
    for suffix, expected in expected_ranks.items():
        group = r02[r02["target_id"].astype(str).str.endswith(suffix)]
        actual = (
            float(pd.to_numeric(group["best_track_global_rank_0p8m_offline_eval"], errors="coerce").median()),
            float(pd.to_numeric(group["union_local_rank_0p8m"], errors="coerce").median()),
            float(pd.to_numeric(group["best_track_local_rank_0p8m_offline_eval"], errors="coerce").median()),
        )
        actual_ranks[suffix] = actual
        rank_ok = rank_ok and all(close(left, right) for left, right in zip(actual, expected))
    add("r02_global_union_track_ranks_recompute", rank_ok, actual_ranks)

    image_paths = [Path(item["local_visualization_path"]) for item in derived["local_cases"]]
    image_paths += [Path(item["full_visualization_path"]) for item in derived["local_cases"]]
    image_paths += [Path(path) for path in derived["summary_figures"]]
    unreadable: list[dict[str, Any]] = []
    dimensions: dict[str, list[int]] = {}
    for path in sorted(set(image_paths)):
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                dimensions[str(path)] = list(image.size)
        except Exception as exc:  # pragma: no cover
            unreadable.append({"path": str(path), "error": repr(exc)})
    add(
        "all_summary_and_case_visualizations_are_readable",
        not unreadable
        and len(derived["local_cases"]) == 7
        and len(derived["summary_figures"]) == 5
        and len(set(image_paths)) == 19,
        {"image_count": len(set(image_paths)), "unreadable": unreadable, "dimensions": dimensions},
    )

    local_refs = re.findall(r'(?:src|href)="([^"#]+)"', html_text)
    missing_refs: list[dict[str, str]] = []
    for ref in local_refs:
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", ref):
            continue
        resolved = (OUTPUT_DIR / Path(ref)).resolve()
        if not resolved.exists():
            missing_refs.append({"ref": ref, "resolved": str(resolved)})
    add(
        "html_local_references_resolve",
        not missing_refs,
        {"reference_count": len(local_refs), "missing": missing_refs},
    )

    required_phrases = [
        "没有进入 P2",
        "SAR 保留 range 与最终定位权",
        "不是 PERSON 框",
        "不是人体固有 RCS",
        "不声称盲验证",
        "不能直接声称物理散射融合",
        "NO_LEGACY_CANDIDATE_ARTIFACT_FOR_FRAME",
        "可能包含未来光学观测",
        "reference 只在最后离线评价",
    ]
    forbidden_positive_claims = [
        "P2 已经成立",
        "P2已经成立",
        "P2_PASS 已成立",
        "生成了最终 PERSON 框",
        "确定了人体固有 RCS",
        "严格 runtime identity 已建立",
        "盲验证通过",
    ]
    add(
        "semantic_boundaries_are_explicit",
        all(phrase in html_text for phrase in required_phrases)
        and not any(phrase in html_text for phrase in forbidden_positive_claims),
        {
            "required": {phrase: phrase in html_text for phrase in required_phrases},
            "forbidden": {phrase: phrase in html_text for phrase in forbidden_positive_claims},
        },
    )
    add(
        "all_six_direct_answers_present",
        all(f'id="q{index}"' in html_text for index in range(1, 7)),
        {"question_ids": [f"q{index}" for index in range(1, 7)]},
    )
    add(
        "status_and_fixed_boundaries_are_preserved",
        summary["status"] == "COMPLETE_NO_NEW_PASS_FAIL_NO_P2_CLAIM"
        and not summary["fixed_boundaries"]["C2_modified"]
        and not summary["fixed_boundaries"]["new_feature_added"]
        and not summary["fixed_boundaries"]["SAR_box_generated"]
        and not summary["fixed_boundaries"]["optical_assigned_SAR_range"]
        and not summary["fixed_boundaries"]["response_region_is_final_box"]
        and not summary["fixed_boundaries"]["shared_region_is_physical_fusion"]
        and not summary["fixed_boundaries"]["P2_pass_claimed"]
        and not summary["fixed_boundaries"]["blind_validation_claimed"],
        summary["fixed_boundaries"],
    )
    add(
        "report_paths_stay_in_active_workspace",
        str(REPORT_PATH.resolve()).lower().startswith(str(WORKSPACE.resolve()).lower())
        and "old_work" not in str(REPORT_PATH).lower()
        and all("old_work" not in ref.lower() for ref in local_refs),
        {"workspace": str(WORKSPACE.resolve()), "report": str(REPORT_PATH.resolve())},
    )

    status = "PASS" if all(check["pass"] for check in checks) else "FAIL"
    return {
        "schema": "PERSON_P1E_RUNTIME_TRACK_RESPONSE_REGION_REPORT_VALIDATION_V1",
        "created_at": now_iso(),
        "status": status,
        "checks_passed": sum(check["pass"] for check in checks),
        "checks_total": len(checks),
        "report_path": str(REPORT_PATH),
        "report_sha256": sha256_file(REPORT_PATH),
        "analysis_script_sha256": sha256_file(ANALYSIS_SCRIPT),
        "report_script_sha256": sha256_file(REPORT_SCRIPT),
        "validation_script_sha256": sha256_file(SCRIPT_PATH),
        "checks": checks,
    }


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    result = validate()
    VALIDATION_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
