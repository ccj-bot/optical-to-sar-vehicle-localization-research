from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "r02_local_boundary_observability_20260902"
OUT = WORKSPACE / "output" / "r02_local_boundary_observability_20260902"
PRE = OUT / "pre_reference"
POST = OUT / "post_freeze_audit"
FREEZE = OUT / "PRE_REFERENCE_FREEZE_MANIFEST.json"
FROZEN_SOURCE = (
    WORKSPACE
    / "tasks"
    / "r02_manual_seed_temporal_propagation_20260902"
    / "run_manual_seed_temporal_propagation.py"
)
EXPECTED_FROZEN_SHA256 = "e80bd4ae8ff808c290340a1452c35f3fe72099051b7742178ad85ea902a90967"
EXPECTED_FREEZE_SHA256 = "351d791efe4734e1b315486e16a842b7a1d48067eb0afb0745d3fb580b2a9ad2"
PRIMARY_SEEDS = [62, 150, 183, 264, 454]
BOUNDARIES = {"SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"}
MANUAL_SOURCES = [
    (
        WORKSPACE
        / "output"
        / "r02_manual_static_scene_anchor_preparation_20260902"
        / "user_annotations"
        / "manual_static_scene_annotations.jsonl",
        20,
        "5ea5882bd764524e5fd61c1d72c7594aaa9bbf9abfcd5a1bd9fe992bde278fc9",
    ),
    (
        WORKSPACE
        / "output"
        / "r02_boundary_multibracket_preparation_20260902"
        / "user_annotations"
        / "manual_static_scene_annotations.jsonl",
        86,
        "2650f9ec2cbe3709475144b6905dd7e9e83d18ddab4d3876098a4877556f2f1e",
    ),
    (
        WORKSPACE
        / "output"
        / "r02_boundary_multibracket_replication_20260902"
        / "repair_user_annotations"
        / "manual_static_scene_annotations.jsonl",
        44,
        "00c795d6f1997324aa087537ef19a9ac9566400a2cc36ff24c40d9ed63c84feb",
    ),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strict_loads(text: str) -> object:
    return json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def load_json(path: Path) -> dict[str, object]:
    value = strict_loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected JSON object: {path}")
    return value


def check(condition: bool, name: str, detail: object, checks: list[dict[str, object]]) -> None:
    checks.append({"check": name, "pass": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def main() -> None:
    checks: list[dict[str, object]] = []

    observed_manual = []
    for path, expected_count, expected_hash in MANUAL_SOURCES:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for line in lines:
            strict_loads(line)
        observed = {"path": str(path), "event_count": len(lines), "sha256": sha256(path)}
        observed_manual.append(observed)
        check(len(lines) == expected_count, "manual_event_count", observed, checks)
        check(observed["sha256"] == expected_hash, "manual_sha256", observed, checks)

    seed_manifest = load_json(PRE / "SEED_INPUT_MANIFEST.json")
    check(seed_manifest["primary_seed_frames"] == PRIMARY_SEEDS, "primary_seed_frames", PRIMARY_SEEDS, checks)
    isolated = seed_manifest["isolated_seed_files"]
    check(len(isolated) == 5, "isolated_seed_file_count", len(isolated), checks)
    for item in isolated:
        seed = int(item["seed_frame"])
        seed_path = Path(item["seed_file"])
        seed_data = load_json(seed_path)
        boundaries = seed_data["boundaries"]
        frames = {int(row["sar_frame_index"]) for row in boundaries}
        kinds = {str(row["object_type"]) for row in boundaries}
        check(len(boundaries) == 2, f"F{seed:03d}_boundary_count", len(boundaries), checks)
        check(frames == {seed}, f"F{seed:03d}_single_frame_only", sorted(frames), checks)
        check(kinds == BOUNDARIES, f"F{seed:03d}_near_far_only", sorted(kinds), checks)
        check(sha256(seed_path) == item["seed_file_sha256"], f"F{seed:03d}_seed_hash", str(seed_path), checks)

    freeze = load_json(FREEZE)
    check(sha256(FREEZE) == EXPECTED_FREEZE_SHA256, "freeze_manifest_sha256", sha256(FREEZE), checks)
    check(freeze["file_count"] == 38, "freeze_file_count", freeze["file_count"], checks)
    for item in freeze["files"]:
        path = WORKSPACE / item["workspace_relative_path"]
        check(path.is_file(), "freeze_file_exists", item["workspace_relative_path"], checks)
        check(sha256(path) == item["sha256"], "freeze_file_hash", item["workspace_relative_path"], checks)

    with (PRE / "FULL_R02_LOCAL_OBSERVABILITY_TIMELINE.csv").open(encoding="utf-8-sig", newline="") as stream:
        timeline = list(csv.DictReader(stream))
    frame_values = [int(row["sar_frame_index"]) for row in timeline]
    check(len(timeline) == 495, "timeline_row_count", len(timeline), checks)
    check(frame_values == list(range(495)), "timeline_complete_frame_sequence", [frame_values[0], frame_values[-1]], checks)

    check(sha256(FROZEN_SOURCE) == EXPECTED_FROZEN_SHA256, "frozen_source_sha256", sha256(FROZEN_SOURCE), checks)
    check(seed_manifest["frozen_source_sha256"] == EXPECTED_FROZEN_SHA256, "seed_manifest_frozen_source", seed_manifest["frozen_source_sha256"], checks)
    for seed in PRIMARY_SEEDS:
        summary = load_json(PRE / "runs" / f"F{seed:03d}" / "RUN_SUMMARY.json")
        check(summary["frozen_source_sha256"] == EXPECTED_FROZEN_SHA256, f"F{seed:03d}_frozen_source", summary["frozen_source_sha256"], checks)
        check(summary["parameter_tuning"] is False, f"F{seed:03d}_parameter_tuning_false", summary["parameter_tuning"], checks)
        check(summary["input_disclosure"]["other_checkpoint_geometry_read"] is False, f"F{seed:03d}_checkpoint_hidden", summary["input_disclosure"], checks)

    computed = load_json(POST / "COMPUTED_AUDIT_SUMMARY.json")
    check(
        computed["pre_reference_freeze_manifest_sha256"] == EXPECTED_FREEZE_SHA256,
        "post_audit_references_freeze",
        computed["pre_reference_freeze_manifest_sha256"],
        checks,
    )
    check(
        (POST / "COMPUTED_AUDIT_SUMMARY.json").stat().st_mtime_ns > FREEZE.stat().st_mtime_ns,
        "post_audit_created_after_freeze",
        {
            "freeze_mtime_ns": FREEZE.stat().st_mtime_ns,
            "audit_mtime_ns": (POST / "COMPUTED_AUDIT_SUMMARY.json").stat().st_mtime_ns,
        },
        checks,
    )

    verdict_path = POST / "MANUAL_VISUAL_VERDICTS.csv"
    with verdict_path.open(encoding="utf-8", newline="") as stream:
        verdicts = list(csv.DictReader(stream))
    f66 = [row for row in verdicts if row["case_id"] == "F66_NATURAL_OVERLAP_CONFLICT"]
    check(len(f66) == 1, "f66_conflict_recorded", f66, checks)
    check(f66[0]["visual_verdict"] == "FALSE_SUPPORT_CURVE_STATE", "f66_conflict_verdict", f66[0], checks)
    check(all(row["visual_verdict"] != "PENDING" for row in verdicts), "manual_visual_review_complete", len(verdicts), checks)

    expected_figures = [
        "R02_LOCAL_BOUNDARY_OBSERVABILITY_TIMELINE.png",
        "ENTRANCE_F057_F068_CURVE_EVOLUTION.png",
        "F066_NATURAL_OVERLAP_SHAPE_CONFLICT.png",
        "CHECKPOINT_COMPARISON_ATLAS.png",
        "STOP_REASON_ATLAS.png",
        "F062_process_review.png",
        "F150_process_review.png",
        "F183_process_review.png",
        "F264_process_review.png",
        "F454_process_review.png",
    ]
    for name in expected_figures:
        path = OUT / "figures" / name
        check(path.is_file() and path.stat().st_size > 0, "figure_exists", name, checks)

    final = load_json(OUT / "FINAL_SUMMARY.json")
    check(final["post_freeze_audit"]["confirmed_false_support_curve_state_count"] >= 1, "final_records_false_support", final["post_freeze_audit"], checks)
    check(final["research_questions"]["optional_scene_geometry_context_qualified"] == "NO_NOT_YET", "optional_context_not_overclaimed", final["research_questions"], checks)
    check((OUT / "REPORT.md").is_file(), "report_exists", str(OUT / "REPORT.md"), checks)

    scope_sources = [
        load_json(PRE / "PRE_REFERENCE_SUMMARY.json"),
        computed,
        final["scientific_non_claims"],
    ]
    for source in scope_sources:
        for field in ["r04_accessed", "person_experiment_run", "tree_experiment_run", "final_localization_run"]:
            check(source[field] is False, f"scope_{field}_false", source[field], checks)

    json_files = sorted(path for path in OUT.rglob("*.json") if path.name != "VALIDATION_REPORT.json")
    jsonl_files = sorted(OUT.rglob("*.jsonl"))
    for path in json_files:
        strict_loads(path.read_text(encoding="utf-8"))
    for path in jsonl_files:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip():
                try:
                    strict_loads(line)
                except Exception as exc:
                    raise ValueError(f"{path}:{line_number}: {exc}") from exc
    check(True, "strict_json_and_jsonl", {"json": len(json_files), "jsonl": len(jsonl_files)}, checks)

    source_hashes = {expected_hash for _, _, expected_hash in MANUAL_SOURCES}
    copied_names = [str(path) for path in OUT.rglob("manual_static_scene_annotations.jsonl")]
    copied_hashes = []
    for path in OUT.rglob("*"):
        if path.is_file() and path.suffix.lower() != ".zip" and sha256(path) in source_hashes:
            copied_hashes.append(str(path))
    check(not copied_names, "no_raw_manual_filename_copied", copied_names, checks)
    check(not copied_hashes, "no_raw_manual_file_hash_copied", copied_hashes, checks)

    report = {
        "schema": "R02_LOCAL_BOUNDARY_OBSERVABILITY_VALIDATION_V1",
        "status": "PASS",
        "check_count": len(checks),
        "manual_sources": observed_manual,
        "checks": checks,
    }
    (OUT / "VALIDATION_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"PASS {len(checks)} checks")
    print(OUT / "VALIDATION_REPORT.json")


if __name__ == "__main__":
    main()
