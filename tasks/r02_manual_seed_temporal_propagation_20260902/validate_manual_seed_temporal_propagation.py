from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "r02_manual_seed_temporal_propagation_20260902"
OUT = WORKSPACE / "output" / "r02_manual_seed_temporal_propagation_20260902"
MANUAL = (
    WORKSPACE
    / "output"
    / "r02_manual_static_scene_anchor_preparation_20260902"
    / "user_annotations"
    / "manual_static_scene_annotations.jsonl"
)
PROPAGATED = OUT / "propagated_static_scene_annotations.jsonl"
DIAGNOSTICS = OUT / "propagation_frame_diagnostics.csv"
REVIEW = OUT / "REVIEW_REQUIRED_FRAME_LIST.csv"
SUMMARY = OUT / "MANUAL_SEED_TEMPORAL_PROPAGATION_SUMMARY.json"
SEED_MANIFEST = OUT / "USER_CONFIRMED_SEED_AUTHORITY.json"
RESULTS = OUT / "VALIDATION_RESULTS.csv"
VALIDATION_SUMMARY = OUT / "VALIDATION_SUMMARY.json"
OUTPUT_MANIFEST = OUT / "OUTPUT_MANIFEST.csv"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def update_manifest() -> None:
    files = [
        PROPAGATED,
        DIAGNOSTICS,
        REVIEW,
        SUMMARY,
        SEED_MANIFEST,
        OUT / "REPORT.md",
        OUT / "figures" / "propagation_review_strip.png",
        OUT / "figures" / "boundary_center_tracks.png",
        RESULTS,
        VALIDATION_SUMMARY,
    ]
    rows = []
    for path in files:
        if not path.exists():
            continue
        rows.append(
            {
                "workspace_relative_path": path.relative_to(WORKSPACE).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "contains_manual_user_event_log": False,
                "artifact_role": "MANUAL_SEED_PROPAGATION_OR_REVIEW",
            }
        )
    pd.DataFrame(rows).to_csv(OUTPUT_MANIFEST, index=False, encoding="utf-8-sig")


def main() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    seed = json.loads(SEED_MANIFEST.read_text(encoding="utf-8"))
    records = [json.loads(line) for line in PROPAGATED.read_text(encoding="utf-8").splitlines() if line.strip()]
    table = pd.DataFrame(records)
    diagnostics = pd.read_csv(DIAGNOSTICS)
    review = pd.read_csv(REVIEW)
    checks: list[dict[str, object]] = []

    def check(check_id: str, passed: bool, observed: object, expected: object, evidence: str) -> None:
        checks.append(
            {
                "check_id": check_id,
                "status": "PASS" if passed else "FAIL",
                "observed": json.dumps(observed, ensure_ascii=False),
                "expected": json.dumps(expected, ensure_ascii=False),
                "evidence": evidence,
            }
        )

    check(
        "MANUAL_JSONL_HASH_PRESERVED",
        sha256_file(MANUAL) == seed["manual_event_sha256"] == summary["manual_event_sha256_after"],
        {"current": sha256_file(MANUAL), "seed_manifest": seed["manual_event_sha256"], "summary": summary["manual_event_sha256_after"]},
        "all hashes equal",
        "manual JSONL + seed manifest + summary",
    )
    check(
        "EXPLICIT_DRAFT_SEED_AUTHORITY_MATERIALIZED",
        seed["draft_seed_acceptance"] == "EXPLICIT_USER_CONFIRMATION_IN_CURRENT_SESSION"
        and seed["seed_frames"] == [150, 183]
        and seed["manual_jsonl_modified"] is False,
        seed,
        {"seed_frames": [150, 183], "manual_jsonl_modified": False},
        SEED_MANIFEST.name,
    )
    expected_objects = {"SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"}
    grouped = table.groupby("sar_frame_index").object_type.agg(lambda values: set(values))
    duplicate_count = int(table.duplicated(["sar_frame_index", "object_type"]).sum())
    check(
        "TWO_BOUNDARIES_PER_ACCEPTED_FRAME",
        duplicate_count == 0 and all(value == expected_objects for value in grouped),
        {"accepted_frames": len(grouped), "duplicates": duplicate_count, "object_sets": sorted({str(sorted(value)) for value in grouped})},
        {"duplicates": 0, "object_set": sorted(expected_objects)},
        PROPAGATED.name,
    )
    accepted_frames = sorted(table.sar_frame_index.astype(int).unique().tolist())
    review_frames = sorted(review.sar_frame_index.astype(int).unique().tolist()) if len(review) else []
    expected_interval = list(range(150, 184))
    check(
        "BRACKETED_INTERVAL_ACCOUNTED_COMPLETELY",
        sorted(set(accepted_frames) | set(review_frames)) == expected_interval
        and not (set(accepted_frames) & set(review_frames)),
        {"accepted": accepted_frames, "review": review_frames},
        {"union": expected_interval, "overlap": []},
        "propagated JSONL + review list",
    )
    separation = table.groupby("sar_frame_index").pair_separation_m.first()
    expected_sep = float(summary["expected_manual_pair_separation_m"])
    check(
        "PAIR_ORDER_AND_SEPARATION_PRESERVED",
        bool((separation > 0).all()) and bool((separation - expected_sep).abs().le(0.30 + 1e-9).all()),
        {"min": float(separation.min()), "max": float(separation.max()), "expected": expected_sep},
        {"positive": True, "max_abs_deviation_m": 0.30},
        PROPAGATED.name,
    )
    propagated_only = table[table.propagation_status.eq("SUPPORTED_BIDIRECTIONAL")]
    check(
        "BIDIRECTIONAL_DISAGREEMENT_BOUNDED",
        bool(propagated_only.bidirectional_disagreement_m.le(0.12 + 1e-9).all()),
        float(propagated_only.bidirectional_disagreement_m.max()) if len(propagated_only) else None,
        "<=0.12 m",
        PROPAGATED.name,
    )
    closure = summary["anchor_closure"]
    check(
        "BOTH_BOUNDARY_ANCHOR_CLOSURES_PASS",
        all(item["closure_pass"] for item in closure.values()),
        closure,
        {"all_closure_pass": True},
        SUMMARY.name,
    )
    script_text = (TASK / "run_manual_seed_temporal_propagation.py").read_text(encoding="utf-8")
    forbidden_terms = ["4.90", "7.10", "12.40", "STATIC_BOUNDARY_A", "STATIC_BOUNDARY_B", "R04ZF"]
    found_forbidden = [term for term in forbidden_terms if term in script_text]
    check(
        "NO_FIXED_RANGE_IDENTITY_WINDOWS_OR_R04",
        not found_forbidden and summary["fixed_range_windows_used"] is False and summary["r04_accessed"] is False,
        {"forbidden_terms": found_forbidden, "fixed_range_windows_used": summary["fixed_range_windows_used"], "r04_accessed": summary["r04_accessed"]},
        {"forbidden_terms": [], "fixed_range_windows_used": False, "r04_accessed": False},
        "propagation source + summary",
    )
    check(
        "P0_AND_LOCAL_RIDGE_DIAGNOSTICS_PRESENT",
        len(diagnostics) > 0
        and diagnostics.p0_dy_px.notna().all()
        and diagnostics.best_score.notna().all()
        and "SAR_IMAGE_DOMAIN_COMMON_APPARENT_TRANSLATION" in summary["p0_semantics"],
        {"rows": len(diagnostics), "p0_dy_nonnull": int(diagnostics.p0_dy_px.notna().sum()), "best_score_nonnull": int(diagnostics.best_score.notna().sum())},
        {"rows": ">0", "all_p0_dy_nonnull": True, "all_best_score_nonnull": True},
        DIAGNOSTICS.name,
    )
    check(
        "PROPAGATED_RECORDS_ARE_NOT_MANUAL_OR_PERSON_GT",
        bool((~table.manual_identity_authority | table.propagation_status.eq("MANUAL_SEED")).all())
        and not table.person_gt.any()
        and not table.final_localization.any()
        and not table.automatic_hint_used_as_identity_authority.any(),
        {
            "person_gt_true": int(table.person_gt.sum()),
            "final_localization_true": int(table.final_localization.sum()),
            "automatic_hint_authority_true": int(table.automatic_hint_used_as_identity_authority.sum()),
        },
        {"all_false": True},
        PROPAGATED.name,
    )
    preview = cv2.imread(str(OUT / "figures" / "propagation_review_strip.png"))
    track_plot = cv2.imread(str(OUT / "figures" / "boundary_center_tracks.png"))
    check(
        "REVIEW_VISUALS_EXIST",
        preview is not None and track_plot is not None and preview.shape[1] >= 2000,
        {"review_shape": list(preview.shape) if preview is not None else None, "track_shape": list(track_plot.shape) if track_plot is not None else None},
        {"both_exist": True, "review_width": ">=2000"},
        "figures",
    )
    check(
        "NO_TREE_PERSON_OR_FINAL_LOCALIZATION_RUN",
        summary["tree_correspondence_run"] is False
        and summary["person_experiment_run"] is False
        and summary["final_localization_run"] is False,
        {key: summary[key] for key in ["tree_correspondence_run", "person_experiment_run", "final_localization_run"]},
        {"all_false": True},
        SUMMARY.name,
    )
    results = pd.DataFrame(checks)
    OUT.mkdir(parents=True, exist_ok=True)
    results.to_csv(RESULTS, index=False, encoding="utf-8-sig")
    pass_count = int(results.status.eq("PASS").sum())
    fail_count = int(results.status.eq("FAIL").sum())
    validation_summary = {
        "status": "PASS" if fail_count == 0 else "FAIL",
        "pass_count": pass_count,
        "fail_count": fail_count,
        "total_count": len(results),
        "accepted_frame_count": len(accepted_frames),
        "review_required_frame_count": len(review_frames),
        "manual_jsonl_sha256": sha256_file(MANUAL),
    }
    VALIDATION_SUMMARY.write_text(json.dumps(validation_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    update_manifest()
    print(json.dumps(validation_summary, ensure_ascii=False, indent=2))
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
