from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "r02_boundary_multibracket_replication_20260902"
TOOL_TASK = WORKSPACE / "tasks" / "r02_manual_static_scene_anchor_preparation_20260902"
OUT = WORKSPACE / "output" / "r02_boundary_multibracket_replication_20260902"
MANUAL = (
    WORKSPACE
    / "output"
    / "r02_boundary_multibracket_preparation_20260902"
    / "user_annotations"
    / "manual_static_scene_annotations.jsonl"
)
NORMALIZED = OUT / "normalized_user_confirmed_seeds.jsonl"
DIRECTIONAL = OUT / "directional_propagation_paths.jsonl"
CLOSED = OUT / "closed_static_scene_annotations.jsonl"
REVIEW = OUT / "REVIEW_REQUIRED_FRAME_LIST.csv"
REPAIR_BATCH = OUT / "R02_BOUNDARY_REPAIR_ANNOTATION_BATCH_V1.csv"
REPAIR_USER_OUTPUT = OUT / "repair_user_annotations"
SUMMARY = OUT / "MULTIBRACKET_REPLICATION_SUMMARY.json"
PARAMETERS = OUT / "FROZEN_PARAMETER_MANIFEST.json"
RESULTS = OUT / "VALIDATION_RESULTS.csv"
VALIDATION_SUMMARY = OUT / "VALIDATION_SUMMARY.json"
BROWSER_PREVIEW = OUT / "BROWSER_REPAIR_SAR_ONLY_PREVIEW.png"
OUTPUT_MANIFEST = OUT / "OUTPUT_MANIFEST.csv"
FROZEN_SCRIPT = (
    WORKSPACE
    / "tasks"
    / "r02_manual_seed_temporal_propagation_20260902"
    / "run_manual_seed_temporal_propagation.py"
)
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

EXPECTED_MANUAL_SHA256 = "2650f9ec2cbe3709475144b6905dd7e9e83d18ddab4d3876098a4877556f2f1e"
EXPECTED_FROZEN_SCRIPT_SHA256 = "e80bd4ae8ff808c290340a1452c35f3fe72099051b7742178ad85ea902a90967"
EXPECTED_BRACKETS = {
    "A_EARLY": (47, 82, 62),
    "B_MID_LATER": (239, 278, 264),
    "C_LATE": (427, 472, 454),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reject_nonstandard_json(value: str) -> None:
    raise ValueError(f"Non-standard JSON constant: {value}")


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_nonstandard_json)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line, parse_constant=reject_nonstandard_json)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def update_manifest() -> None:
    rows = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path == OUTPUT_MANIFEST or REPAIR_USER_OUTPUT in path.parents:
            continue
        rows.append(
            {
                "workspace_relative_path": path.relative_to(WORKSPACE).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "artifact_role": "R02_MULTIBRACKET_REPLICATION_OR_VALIDATION",
                "contains_raw_manual_event_log": False,
            }
        )
    pd.DataFrame(rows).to_csv(OUTPUT_MANIFEST, index=False, encoding="utf-8-sig")


def main() -> None:
    summary = read_json(SUMMARY)
    parameters = read_json(PARAMETERS)
    normalized = read_jsonl(NORMALIZED)
    directional = read_jsonl(DIRECTIONAL)
    review = pd.read_csv(REVIEW)
    repair = pd.read_csv(REPAIR_BATCH)
    frozen = load_module("r02_frozen_replication_validator", FROZEN_SCRIPT)
    checks: list[dict[str, str]] = []

    def check(check_id: str, passed: bool, observed: object, expected: object, evidence: str) -> None:
        checks.append(
            {
                "check_id": check_id,
                "status": "PASS" if passed else "FAIL",
                "observed": json.dumps(observed, ensure_ascii=False, allow_nan=False),
                "expected": json.dumps(expected, ensure_ascii=False, allow_nan=False),
                "evidence": evidence,
            }
        )

    manual_lines = [line for line in MANUAL.read_text(encoding="utf-8").splitlines() if line.strip()]
    check(
        "MANUAL_JSONL_86_EVENTS_HASH_PRESERVED",
        len(manual_lines) == 86
        and sha256_file(MANUAL) == EXPECTED_MANUAL_SHA256
        and summary["manual_event_sha256_before"] == EXPECTED_MANUAL_SHA256
        and summary["manual_event_sha256_after"] == EXPECTED_MANUAL_SHA256
        and summary["manual_jsonl_preserved"] is True,
        {"lines": len(manual_lines), "sha256": sha256_file(MANUAL)},
        {"lines": 86, "sha256": EXPECTED_MANUAL_SHA256},
        "raw append-only manual JSONL + summary",
    )

    expected_frames = [47, 82, 239, 278, 427, 472]
    normalized_keys = [(int(row["sar_frame_index"]), str(row["object_type"])) for row in normalized]
    check(
        "TWELVE_PROVENANCE_PRESERVING_NORMALIZED_SEEDS",
        len(normalized) == 12
        and sorted(set(frame for frame, _ in normalized_keys)) == expected_frames
        and all(sum(1 for key in normalized_keys if key[0] == frame) == 2 for frame in expected_frames)
        and all(row["source_event_id"] and int(row["source_revision"]) >= 1 for row in normalized)
        and all(row["manual_jsonl_modified"] is False for row in normalized),
        {"count": len(normalized), "frames": sorted(set(frame for frame, _ in normalized_keys))},
        {"count": 12, "frames": expected_frames, "two_boundaries_per_frame": True},
        NORMALIZED.name,
    )

    a_rows = {
        (int(row["sar_frame_index"]), str(row["object_type"])): row
        for row in directional
        if row["bracket_id"] == "A_EARLY" and int(row["sar_frame_index"]) in {47, 82}
    }
    curve_stats: dict[str, dict[str, float]] = {}
    for frame in (47, 82):
        for object_type in ("SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"):
            curve = np.asarray(a_rows[(frame, object_type)]["d_curve_m"], dtype=float)
            linear = np.linspace(curve[0], curve[-1], len(curve))
            curve_stats[f"F{frame}_{object_type}"] = {
                "span_m": float(np.ptp(curve)),
                "nonlinear_max_m": float(np.max(np.abs(curve - linear))),
            }
    check(
        "EARLY_ENTRANCE_CURVES_NOT_STRAIGHTENED",
        curve_stats["F47_SAR_BOUNDARY_NEAR"]["span_m"] > 1.0
        and curve_stats["F47_SAR_BOUNDARY_FAR"]["span_m"] > 2.0
        and curve_stats["F47_SAR_BOUNDARY_NEAR"]["nonlinear_max_m"] > 0.20
        and curve_stats["F47_SAR_BOUNDARY_FAR"]["nonlinear_max_m"] > 0.60
        and curve_stats["F82_SAR_BOUNDARY_NEAR"]["span_m"] < 0.10
        and curve_stats["F82_SAR_BOUNDARY_FAR"]["span_m"] < 0.30,
        curve_stats,
        "F047 retains strong curved d_perp(theta) shape; F082 is much flatter",
        DIRECTIONAL.name,
    )

    parameter_checks = {
        "background_offset_m": bool(np.isclose(parameters["background_offset_m"], frozen.BACKGROUND_OFFSET_M)),
        "min_aggregate_contrast": parameters["min_aggregate_contrast"] == frozen.MIN_AGGREGATE_CONTRAST,
        "min_node_support_fraction": bool(np.isclose(parameters["min_node_support_fraction"], frozen.MIN_NODE_SUPPORT_FRACTION)),
        "max_local_offset_m": bool(np.isclose(parameters["max_local_offset_m"], frozen.MAX_LOCAL_OFFSET_M)),
        "distinct_candidate_distance_m": bool(np.isclose(parameters["distinct_candidate_distance_m"], frozen.DISTINCT_CANDIDATE_DISTANCE_M)),
        "ambiguous_second_ratio": bool(np.isclose(parameters["ambiguous_second_ratio"], frozen.AMBIGUOUS_SECOND_RATIO)),
        "max_bidirectional_disagreement_m": bool(np.isclose(parameters["max_bidirectional_disagreement_m"], frozen.MAX_BIDIRECTIONAL_DISAGREEMENT_M)),
        "max_pair_separation_deviation_m": bool(np.isclose(parameters["max_pair_separation_deviation_m"], frozen.MAX_PAIR_SEPARATION_DEVIATION_M)),
        "theta_step_deg": bool(np.isclose(parameters["theta_step_deg"], frozen.THETA_STEP_DEG)),
    }
    check(
        "FROZEN_IMPLEMENTATION_AND_PARAMETERS_UNCHANGED",
        sha256_file(FROZEN_SCRIPT) == EXPECTED_FROZEN_SCRIPT_SHA256
        and parameters["source_script_sha256"] == EXPECTED_FROZEN_SCRIPT_SHA256
        and all(parameter_checks.values())
        and parameters["parameter_tuning_for_new_brackets"] is False,
        {"script_sha256": sha256_file(FROZEN_SCRIPT), "parameter_matches": parameter_checks},
        {"script_sha256": EXPECTED_FROZEN_SCRIPT_SHA256, "all_parameter_matches": True, "tuning": False},
        PARAMETERS.name,
    )

    accounting: dict[str, object] = {}
    accounting_pass = True
    for bracket_id, (start, end, repair_frame) in EXPECTED_BRACKETS.items():
        path_frames = sorted({int(row["sar_frame_index"]) for row in directional if row["bracket_id"] == bracket_id})
        review_frames = sorted(review.loc[review.bracket_id.eq(bracket_id), "sar_frame_index"].astype(int).unique().tolist())
        expected_interval = list(range(start, end + 1))
        bracket = summary["brackets"][bracket_id]
        bracket_ok = (
            sorted(set(path_frames) | set(review_frames)) == expected_interval
            and not (set(path_frames) & set(review_frames))
            and len(path_frames) == int(bracket["directional_supported_frame_count"])
            and review_frames == bracket["review_required_frames"]
            and int(bracket["proposed_repair_frame"]) == repair_frame
        )
        accounting_pass = accounting_pass and bracket_ok
        accounting[bracket_id] = {"directional": path_frames, "review": review_frames, "repair": repair_frame}
    check(
        "ALL_BRACKET_FRAMES_ACCOUNTED_WITH_EXPLICIT_REVIEW_GAPS",
        accounting_pass,
        accounting,
        "each inclusive bracket equals disjoint directional coverage plus review-required gap",
        "directional paths + review list + summary",
    )

    unavailable_fields = [
        "center_closure_pass",
        "curve_shape_closure_pass",
        "near_far_ordering_pass",
        "response_support_min_intersection_fraction",
        "max_center_disagreement_m",
        "max_curve_shape_rms_disagreement_m",
        "max_curve_shape_node_disagreement_m",
    ]
    unavailable_ok = all(
        bracket["overlap_frame_count"] == 0
        and bracket["overlap_closure_availability"] == "UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP"
        and bracket["closure_failure_reason"] == "NO_BIDIRECTIONAL_OVERLAP"
        and all(bracket[field] is None for field in unavailable_fields)
        and bracket["directional_near_far_ordering_pass"] is True
        for bracket in summary["brackets"].values()
    )
    check(
        "NO_OVERLAP_RECORDED_AS_UNAVAILABLE_NOT_FAILED",
        unavailable_ok and all(row["pair_order_positive_all_nodes"] is True for row in directional),
        {key: {field: value[field] for field in ["overlap_closure_availability", "closure_failure_reason", *unavailable_fields, "directional_near_far_ordering_pass"]} for key, value in summary["brackets"].items()},
        "overlap gates null with explicit unavailable state; directional ordering remains separate and true",
        SUMMARY.name,
    )

    repair_frames = repair.sar_frame_index.astype(int).tolist()
    missing_media = [str(path) for path in repair.sar_image_path if not Path(path).is_file()]
    missing_media += [str(path) for path in repair.optical_image_path if not Path(path).is_file()]
    check(
        "MINIMAL_REPAIR_BATCH_IS_F062_F264_F454_WITH_EXISTING_MEDIA",
        repair_frames == [62, 264, 454]
        and repair.annotation_scope.eq("SAR_BOUNDARY_ONLY").all()
        and repair.annotation_status.eq("PENDING").all()
        and not repair.automatic_hint_is_identity_authority.astype(bool).any()
        and not missing_media,
        {"frames": repair_frames, "missing_media": missing_media},
        {"frames": [62, 264, 454], "missing_media": []},
        REPAIR_BATCH.name,
    )
    check(
        "REPAIR_USER_OUTPUT_REMAINS_EMPTY",
        REPAIR_USER_OUTPUT.is_dir() and not any(REPAIR_USER_OUTPUT.iterdir()),
        [path.name for path in REPAIR_USER_OUTPUT.iterdir()] if REPAIR_USER_OUTPUT.is_dir() else "MISSING",
        [],
        str(REPAIR_USER_OUTPUT),
    )
    check(
        "NO_FALSE_CLOSED_RECORDS_OR_SCOPE_EXPANSION",
        CLOSED.is_file()
        and CLOSED.stat().st_size == 0
        and summary["closed_record_count"] == 0
        and summary["closed_brackets"] == []
        and summary["not_closed_brackets"] == list(EXPECTED_BRACKETS)
        and summary["r04_accessed"] is False
        and summary["tree_correspondence_run"] is False
        and summary["person_experiment_run"] is False
        and summary["final_localization_run"] is False,
        {key: summary[key] for key in ["closed_record_count", "closed_brackets", "not_closed_brackets", "r04_accessed", "tree_correspondence_run", "person_experiment_run", "final_localization_run"]},
        "zero closed records and all excluded-scope flags false",
        SUMMARY.name,
    )

    figure_info = {}
    for bracket_id in EXPECTED_BRACKETS:
        for suffix in ("process_review", "overlap_review"):
            path = OUT / "figures" / f"{bracket_id}_{suffix}.png"
            image = cv2.imread(str(path))
            figure_info[path.name] = list(image.shape) if image is not None else None
    check(
        "PROCESS_AND_NO_OVERLAP_VISUALS_EXIST",
        all(shape is not None and shape[0] >= 400 and shape[1] >= 900 for shape in figure_info.values()),
        figure_info,
        "six readable process/overlap review figures",
        "figures",
    )

    server_module = load_module(
        "r02_static_scene_browser_server_repair_validation",
        TOOL_TASK / "r02_static_scene_browser_server.py",
    )
    with tempfile.TemporaryDirectory(prefix="r02_repair_browser_qa_", dir=OUT) as temporary:
        temporary_path = Path(temporary)
        service = server_module.BrowserAnnotationService(REPAIR_BATCH, temporary_path / "annotations")
        http_server = server_module.AnnotationHTTPServer(("127.0.0.1", 0), service)
        thread = threading.Thread(target=http_server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{http_server.server_address[1]}"
        try:
            with urllib.request.urlopen(base + "/api/state", timeout=10) as response:
                state = json.loads(response.read().decode("utf-8"))
            for object_type, y in (("SAR_BOUNDARY_NEAR", 440.0), ("SAR_BOUNDARY_FAR", 385.0)):
                saved = post_json(
                    base + "/api/save",
                    {
                        "batch_index": 1,
                        "object_type": object_type,
                        "points": [[380.0, y], [500.0, y - 4.0], [620.0, y]],
                        "confidence_state": "CONFIDENT",
                        "geometry_status": "COMPLETE",
                        "visibility_state": "VISIBLE_OR_GEOMETRY_PROVIDED",
                    },
                )
                if not saved.get("ok"):
                    raise RuntimeError(saved)
            service.store.write_views(service.skipped)
            coverage = read_json(service.store.coverage_path)
            records = list(service.store.latest.values())
            api_ok = (
                state["workflow_mode"] == "SAR_BOUNDARY_ONLY"
                and state["guided_boundary_order"] == ["SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"]
                and len(state["batch"]) == 3
                and state["batch"][0]["sar_frame_index"] == 62
                and len(records) == 2
                and coverage["required_boundary_identity_supported_batch_indices"] == [1]
            )
            browser_ok = False
            browser_observed: object = "EDGE_NOT_FOUND"
            if EDGE.is_file():
                profile = temporary_path / "edge_profile"
                screenshot = BROWSER_PREVIEW
                screenshot.unlink(missing_ok=True)
                completed = subprocess.run(
                    [
                        str(EDGE),
                        "--headless=new",
                        "--disable-gpu",
                        "--hide-scrollbars",
                        "--no-first-run",
                        f"--user-data-dir={profile}",
                        "--window-size=1600,1000",
                        f"--screenshot={screenshot}",
                        base + "/",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                preview = cv2.imread(str(screenshot)) if screenshot.exists() else None
                browser_ok = completed.returncode == 0 and preview is not None and list(preview.shape) == [1000, 1600, 3]
                browser_observed = {
                    "returncode": completed.returncode,
                    "shape": list(preview.shape) if preview is not None else None,
                    "stderr_tail": completed.stderr[-300:],
                }
                if browser_ok:
                    pass
            check(
                "ISOLATED_SAR_ONLY_REPAIR_BROWSER_QA",
                api_ok and browser_ok,
                {"api_ok": api_ok, "browser": browser_observed, "temporary_records": len(records)},
                {"api_ok": True, "browser_shape": [1000, 1600, 3], "temporary_records": 2},
                "temporary localhost server; real repair output untouched",
            )
        finally:
            try:
                post_json(base + "/api/shutdown", {})
            except Exception:
                http_server.shutdown()
            thread.join(timeout=10)

    check(
        "STRICT_STANDARD_JSON_OUTPUTS",
        all(token not in path.read_text(encoding="utf-8") for path in (SUMMARY, PARAMETERS, NORMALIZED, DIRECTIONAL) for token in ("NaN", "Infinity", "-Infinity")),
        "all JSON and JSONL parsed with non-standard constants rejected",
        "no NaN or Infinity tokens",
        "summary, parameters, normalized seeds, directional paths",
    )

    results = pd.DataFrame(checks)
    results.to_csv(RESULTS, index=False, encoding="utf-8-sig")
    pass_count = int(results.status.eq("PASS").sum())
    fail_count = int(results.status.eq("FAIL").sum())
    validation_summary = {
        "status": "PASS" if fail_count == 0 else "FAIL",
        "pass_count": pass_count,
        "fail_count": fail_count,
        "total_count": len(results),
        "manual_jsonl_sha256": sha256_file(MANUAL),
        "repair_frames": repair_frames,
        "closed_record_count": int(summary["closed_record_count"]),
    }
    VALIDATION_SUMMARY.write_text(
        json.dumps(validation_summary, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    update_manifest()
    print(json.dumps(validation_summary, ensure_ascii=False, indent=2, allow_nan=False))
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
