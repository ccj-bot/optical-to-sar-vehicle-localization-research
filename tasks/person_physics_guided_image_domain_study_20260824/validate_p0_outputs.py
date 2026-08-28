#!/usr/bin/env python3
"""Validate the completed P0 artifact set without changing research results."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK_DIR = WORKSPACE / "tasks" / "person_physics_guided_image_domain_study_20260824"
ROOT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824" / "p0_common_apparent_motion"
CONTRACT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824" / "research_contract_v1.json"
MAIN_SCRIPT = TASK_DIR / "run_p0_common_apparent_motion.py"
REPORT = ROOT / "validation_report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def check(checks: list[dict[str, Any]], name: str, passed: bool, detail: Any) -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


def main() -> None:
    checks: list[dict[str, Any]] = []
    required = [
        "model_selection_R01.json",
        "frozen_validation_R04_quantitative.json",
        "frozen_validation_R04.json",
        "common_motion_pair_metrics.csv",
        "background_anchor_holdout_metrics.csv",
        "stationary_person_residuals.csv",
        "comparability_registry.csv",
        "worst_case_registry.csv",
        "worst_PERSON_case_registry.csv",
        "MULTIMODAL_WORST_FRAME_REVIEW.md",
        "P0_CONCLUSION.md",
    ]
    missing = [name for name in required if not (ROOT / name).is_file()]
    check(checks, "required_files_exist", not missing, {"missing": missing})

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    input_rows = []
    for item in contract["input_snapshot"]:
        path = Path(item["path"])
        actual = sha256(path) if path.is_file() else "MISSING"
        input_rows.append(
            {"path": str(path), "expected": item["sha256"].upper(), "actual": actual, "match": actual == item["sha256"].upper()}
        )
    check(checks, "frozen_input_hashes_match", all(row["match"] for row in input_rows), input_rows)

    freeze = json.loads((ROOT / "model_selection_R01.json").read_text(encoding="utf-8"))
    quantitative = json.loads((ROOT / "frozen_validation_R04_quantitative.json").read_text(encoding="utf-8"))
    final = json.loads((ROOT / "frozen_validation_R04.json").read_text(encoding="utf-8"))
    check(
        checks,
        "main_script_matches_R01_freeze",
        sha256(MAIN_SCRIPT) == freeze["frozen"]["script_sha256"],
        {"current": sha256(MAIN_SCRIPT), "frozen": freeze["frozen"]["script_sha256"]},
    )
    check(
        checks,
        "R04_links_to_R01_freeze",
        quantitative["R01_freeze_payload_sha256"] == freeze["freeze_payload_sha256"] == final["R01_freeze_payload_sha256"],
        freeze["freeze_payload_sha256"],
    )
    check(
        checks,
        "final_links_to_quantitative_file",
        sha256(ROOT / "frozen_validation_R04_quantitative.json") == final["quantitative_validation_sha256"],
        final["quantitative_validation_sha256"],
    )
    check(
        checks,
        "final_links_to_manual_review",
        sha256(ROOT / "MULTIMODAL_WORST_FRAME_REVIEW.md") == final["manual_multimodal_review"]["sha256"],
        final["manual_multimodal_review"],
    )
    check(checks, "final_decision_is_P0_PASS", final["final_decision"] == "P0_PASS", final["final_decision"])
    check(checks, "all_final_gates_pass", all(final["final_gates"].values()), final["final_gates"])
    check(
        checks,
        "stopped_before_P1",
        final["semantic_stop"]["P1_started"] is False and final["semantic_stop"]["P2_started"] is False,
        final["semantic_stop"],
    )
    check(
        checks,
        "no_SAR_boxes_created_or_moved",
        int(final["semantic_stop"]["sar_boxes_created_or_moved"]) == 0,
        final["semantic_stop"]["sar_boxes_created_or_moved"],
    )

    pair = pd.read_csv(ROOT / "common_motion_pair_metrics.csv")
    anchors = pd.read_csv(ROOT / "background_anchor_holdout_metrics.csv")
    person = pd.read_csv(ROOT / "stationary_person_residuals.csv")
    comparability = pd.read_csv(ROOT / "comparability_registry.csv")
    expected_runs = {"R01ZF", "R04ZF"}
    run_sets = {
        "pair": sorted(pair["run_id"].dropna().unique().tolist()),
        "anchors": sorted(anchors["run_id"].dropna().unique().tolist()),
        "person": sorted(person["run_id"].dropna().unique().tolist()),
        "comparability": sorted(comparability["run_id"].dropna().unique().tolist()),
    }
    check(checks, "only_R01_R04_used", all(set(values) == expected_runs for values in run_sets.values()), run_sets)
    comparable_counts = comparability.groupby("run_id")["comparable"].sum().astype(int).to_dict()
    check(
        checks,
        "comparability_counts_match_protocol_run_pairs",
        comparable_counts == {"R01ZF": 417, "R04ZF": 579},
        comparable_counts,
    )
    selected = pair[(pair["run_id"] == "R04ZF") & pair["is_selected_frozen_model"] & pair["model_available"]].copy()
    improved_count = int(selected["holdout_improved_vs_M0"].astype(bool).sum())
    check(
        checks,
        "R04_selected_pair_count_and_improvement_match",
        len(selected) == 579 and improved_count == 578,
        {"selected_pair_count": int(len(selected)), "improved_count": improved_count},
    )
    selected_models = selected.groupby("lag")["model"].unique().apply(lambda values: values.tolist()).to_dict()
    check(
        checks,
        "selected_models_match_freeze",
        selected_models == {1: ["M1"], 3: ["M2"], 5: ["M2"]},
        selected_models,
    )
    check(
        checks,
        "mask_integrity_zero_violations",
        int(comparability["person_mask_anchor_violations"].sum()) == 0
        and int(comparability["boundary_mask_anchor_violations"].sum()) == 0
        and int(comparability["target_pixels_used_for_fitting"].sum()) == 0,
        {
            "person": int(comparability["person_mask_anchor_violations"].sum()),
            "boundary": int(comparability["boundary_mask_anchor_violations"].sum()),
            "target_pixels": int(comparability["target_pixels_used_for_fitting"].sum()),
        },
    )

    selected_map = {int(key): value for key, value in quantitative["selected_model_by_lag"].items()}
    heldout_person = person[(person["run_id"] == "R04ZF") & person["model_available"]].copy()
    heldout_person = heldout_person[
        heldout_person.apply(lambda row: row["model"] == selected_map[int(row["lag"])], axis=1)
    ]
    manual_count = int(heldout_person["both_manual_endpoints"].astype(bool).sum())
    check(
        checks,
        "PERSON_selected_counts_match",
        len(heldout_person) == 1050 and manual_count == 120,
        {"all_accepted": int(len(heldout_person)), "manual_endpoints": manual_count},
    )

    image_paths = sorted([*ROOT.rglob("*.jpg"), *ROOT.rglob("*.png")])
    unreadable = [str(path) for path in image_paths if cv2.imread(str(path), cv2.IMREAD_UNCHANGED) is None]
    check(checks, "all_visual_assets_readable", not unreadable, {"image_count": len(image_paths), "unreadable": unreadable})
    old_work_mentions = []
    for path in TASK_DIR.glob("*.py"):
        if path.resolve() == Path(__file__).resolve():
            continue
        source = path.read_text(encoding="utf-8").lower()
        if r"d:\profile\research\old_work".lower() in source or "d:/profile/research/old_work" in source:
            old_work_mentions.append(str(path))
    check(checks, "no_old_work_dependency_in_task_code", not old_work_mentions, old_work_mentions)

    passed = all(row["passed"] for row in checks)
    report = {
        "schema": "PERSON_P0_OUTPUT_VALIDATION_REPORT_V1",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "PASS" if passed else "FAIL",
        "check_count": len(checks),
        "passed_check_count": sum(row["passed"] for row in checks),
        "checks": checks,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": report["check_count"]}, ensure_ascii=False))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
