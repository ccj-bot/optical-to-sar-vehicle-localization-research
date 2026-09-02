from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

import cv2
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "r02_boundary_multibracket_preparation_20260902"
TOOL_TASK = WORKSPACE / "tasks" / "r02_manual_static_scene_anchor_preparation_20260902"
OUT = WORKSPACE / "output" / "r02_boundary_multibracket_preparation_20260902"
BATCH = OUT / "R02_BOUNDARY_MULTIBRACKET_ANNOTATION_BATCH_V1.csv"
REPORT = OUT / "MULTIBRACKET_SELECTION_REPORT.md"
MANIFEST = OUT / "R02_BOUNDARY_MULTIBRACKET_PREPARATION_MANIFEST.json"
USER_OUTPUT = OUT / "user_annotations"
RESULTS = OUT / "VALIDATION_RESULTS.csv"
SUMMARY = OUT / "VALIDATION_SUMMARY.json"
BROWSER_PREVIEW = OUT / "BROWSER_SAR_ONLY_PREVIEW.png"
OLD_USER_EVENTS = (
    WORKSPACE
    / "output"
    / "r02_manual_static_scene_anchor_preparation_20260902"
    / "user_annotations"
    / "manual_static_scene_annotations.jsonl"
)
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
EXPECTED_OLD_MANUAL_SHA256 = "5ea5882bd764524e5fd61c1d72c7594aaa9bbf9abfcd5a1bd9fe992bde278fc9"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def main() -> None:
    old_hash_before = sha256(OLD_USER_EVENTS)
    old_count_before = len(OLD_USER_EVENTS.read_text(encoding="utf-8").splitlines())
    if any(USER_OUTPUT.iterdir()):
        raise RuntimeError(f"Real user output is not empty before validation: {USER_OUTPUT}")

    app = load_module("r02_static_scene_annotator_multibracket_validation", TOOL_TASK / "r02_static_scene_annotator.py")
    server_module = load_module("r02_static_scene_browser_server_multibracket_validation", TOOL_TASK / "r02_static_scene_browser_server.py")
    batch = pd.read_csv(BATCH)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    checks: list[dict[str, str]] = []

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

    expected_endpoints = [47, 82, 239, 278, 427, 472]
    check(
        "SIX_SAR_KEYFRAMES",
        len(batch) == 6
        and batch.batch_index.tolist() == list(range(1, 7))
        and batch.sar_frame_index.tolist() == expected_endpoints
        and batch.annotation_scope.eq("SAR_BOUNDARY_ONLY").all(),
        {"count": len(batch), "frames": batch.sar_frame_index.tolist(), "scopes": sorted(batch.annotation_scope.unique())},
        {"count": 6, "frames": expected_endpoints, "scopes": ["SAR_BOUNDARY_ONLY"]},
        BATCH.name,
    )
    bracket_rows = batch.groupby("bracket_id", sort=False).agg(start=("sar_frame_index", "min"), end=("sar_frame_index", "max"), count=("sar_frame_index", "size"))
    spans = (bracket_rows["end"] - bracket_rows["start"] + 1).tolist()
    check(
        "THREE_SEPARATED_20_TO_50_FRAME_BRACKETS",
        bracket_rows.index.tolist() == ["A_EARLY", "B_MID_LATER", "C_LATE"]
        and bracket_rows["count"].eq(2).all()
        and all(20 <= span <= 50 for span in spans)
        and not any(150 <= frame <= 183 for frame in batch.sar_frame_index),
        {"brackets": bracket_rows.reset_index().to_dict("records"), "inclusive_spans": spans},
        {"brackets": ["A_EARLY", "B_MID_LATER", "C_LATE"], "inclusive_spans": [36, 40, 46], "comparator_excluded": True},
        BATCH.name,
    )
    check(
        "START_END_ROLES_ONLY",
        all(group.seed_role.tolist() == ["START", "END"] for _, group in batch.groupby("bracket_id", sort=False)),
        batch[["bracket_id", "seed_role", "sar_frame_index"]].to_dict("records"),
        "START then END for each bracket",
        BATCH.name,
    )
    required_fields = {
        "bracket_id", "seed_role", "sar_frame_index", "sar_timestamp_ms", "nearest_optical_frame",
        "nearest_optical_timestamp_ms", "sync_residual_ms", "selection_reason", "visual_difficulty", "notes", "annotation_scope",
    }
    check(
        "REQUIRED_BATCH_FIELDS",
        required_fields.issubset(batch.columns),
        sorted(batch.columns),
        sorted(required_fields),
        BATCH.name,
    )
    missing_media = [path for column in ("optical_image_path", "sar_image_path") for path in batch[column] if not Path(path).is_file()]
    check("ALL_MEDIA_EXISTS", not missing_media, missing_media, [], BATCH.name)
    check(
        "TIMING_METADATA_CONSISTENT",
        batch.optical_frame_index.eq(batch.nearest_optical_frame).all()
        and batch.optical_timestamp_ms.eq(batch.nearest_optical_timestamp_ms).all()
        and batch.nominal_timestamp_residual_ms.eq(batch.sync_residual_ms).all()
        and batch.sync_residual_ms.abs().max() <= 33
        and batch.sync_status.eq("NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED").all(),
        batch[["sar_frame_index", "nearest_optical_frame", "sync_residual_ms", "sync_status"]].to_dict("records"),
        "nearest optical metadata retained with absolute nominal residual <=33 ms and unverified zero offset",
        BATCH.name,
    )
    figure_shapes: dict[str, list[int] | None] = {}
    for letter in "ABC":
        path = OUT / "figures" / f"bracket_{letter}_review_strip.png"
        image = cv2.imread(str(path))
        figure_shapes[path.name] = list(image.shape) if image is not None else None
    check(
        "THREE_REVIEW_STRIPS_RENDERED",
        all(shape is not None and shape[1] >= 2000 and shape[0] >= 500 for shape in figure_shapes.values()),
        figure_shapes,
        "three 10-frame review strips at least 2000x500",
        "figures/bracket_[ABC]_review_strip.png",
    )
    report_text = REPORT.read_text(encoding="utf-8")
    check(
        "REPORT_PRESERVES_NONCLAIMS",
        all(term in report_text for term in ["No propagation result", "F150-F183", "`d_perp`", "PERSON", "R04"]),
        {term: term in report_text for term in ["No propagation result", "F150-F183", "`d_perp`", "PERSON", "R04"]},
        "all boundary declarations present",
        REPORT.name,
    )
    check(
        "MANIFEST_DECLARATIONS",
        manifest["keyframe_count"] == 6
        and manifest["required_object_types"] == ["SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"]
        and manifest["propagation_run"] is False
        and manifest["r04_accessed"] is False
        and manifest["person_experiment_run"] is False,
        manifest,
        "6 keyframes; two SAR labels; no propagation, R04, or PERSON",
        MANIFEST.name,
    )

    with tempfile.TemporaryDirectory(prefix="r02_multibracket_browser_qa_") as temporary:
        temporary_path = Path(temporary)
        service = server_module.BrowserAnnotationService(BATCH, temporary_path / "annotations")
        http_server = server_module.AnnotationHTTPServer(("127.0.0.1", 0), service)
        thread = threading.Thread(target=http_server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{http_server.server_address[1]}"
        with urllib.request.urlopen(base + "/api/state", timeout=10) as response:
            state = json.loads(response.read().decode("utf-8"))
        for object_type, y in (("SAR_BOUNDARY_NEAR", 440.0), ("SAR_BOUNDARY_FAR", 390.0)):
            saved = post_json(
                base + "/api/save",
                {
                    "batch_index": 1,
                    "object_type": object_type,
                    "points": [[390.0, y], [510.0, y - 2.0], [630.0, y]],
                    "confidence_state": "CONFIDENT",
                    "geometry_status": "COMPLETE",
                    "visibility_state": "VISIBLE_OR_GEOMETRY_PROVIDED",
                },
            )
            if not saved.get("ok"):
                raise RuntimeError(saved)
        service.store.write_views(service.skipped)
        coverage = json.loads(service.store.coverage_path.read_text(encoding="utf-8"))
        records = list(service.store.latest.values())
        check(
            "SAR_ONLY_SERVER_STATE",
            state["workflow_mode"] == "SAR_BOUNDARY_ONLY"
            and state["guided_boundary_order"] == ["SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"]
            and state["batch"][0]["bracket_id"] == "A_EARLY"
            and state["batch"][0]["seed_role"] == "START",
            {"workflow_mode": state["workflow_mode"], "guided_boundary_order": state["guided_boundary_order"], "first_row": state["batch"][0]},
            {"workflow_mode": "SAR_BOUNDARY_ONLY", "guided_boundary_order": ["SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"]},
            "localhost /api/state",
        )
        check(
            "ISOLATED_SAVE_PRESERVES_BRACKET_SEED_AND_COVERAGE",
            len(records) == 2
            and {record["object_type"] for record in records} == {"SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"}
            and all(record["bracket_id"] == "A_EARLY" and record["seed_role"] == "START" for record in records)
            and coverage["required_boundary_identity_supported_batch_indices"] == [1]
            and coverage["both_optical_and_sar_boundary_identity_supported_batch_indices"] == [],
            {"records": records, "coverage": coverage},
            "two SAR-only records with bracket/seed fields and generic coverage only",
            "isolated temporary annotation output",
        )

        if not EDGE.is_file():
            check("HEADLESS_BROWSER_PREVIEW", False, str(EDGE), "Microsoft Edge executable", "local browser")
        else:
            profile = temporary_path / "edge_profile"
            command = [
                str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                f"--user-data-dir={profile}", "--window-size=1600,1000", f"--screenshot={BROWSER_PREVIEW}", base + "/",
            ]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
            preview = cv2.imread(str(BROWSER_PREVIEW)) if BROWSER_PREVIEW.exists() else None
            check(
                "HEADLESS_BROWSER_PREVIEW",
                completed.returncode == 0 and preview is not None and preview.shape[1] == 1600 and preview.shape[0] == 1000,
                {"returncode": completed.returncode, "exists": BROWSER_PREVIEW.exists(), "shape": list(preview.shape) if preview is not None else None, "stderr_tail": completed.stderr[-500:]},
                {"returncode": 0, "shape": [1000, 1600, 3]},
                BROWSER_PREVIEW.name,
            )
        post_json(base + "/api/shutdown", {})
        thread.join(timeout=10)

    old_hash_after = sha256(OLD_USER_EVENTS)
    old_count_after = len(OLD_USER_EVENTS.read_text(encoding="utf-8").splitlines())
    check(
        "OLD_MANUAL_JSONL_UNCHANGED",
        old_hash_before == old_hash_after == EXPECTED_OLD_MANUAL_SHA256 and old_count_before == old_count_after == 20,
        {"count_before": old_count_before, "count_after": old_count_after, "sha256": old_hash_after},
        {"count": 20, "sha256": EXPECTED_OLD_MANUAL_SHA256},
        str(OLD_USER_EVENTS),
    )
    check(
        "REAL_MULTIBRACKET_USER_OUTPUT_STILL_EMPTY",
        not any(USER_OUTPUT.iterdir()),
        [path.name for path in USER_OUTPUT.iterdir()],
        [],
        str(USER_OUTPUT),
    )
    check(
        "NO_PROPAGATION_OUTPUT",
        not any(OUT.glob("*propagat*")) and not any(OUT.glob("*REVIEW_REQUIRED*")),
        [path.name for path in OUT.iterdir() if "propagat" in path.name.lower() or "REVIEW_REQUIRED" in path.name],
        [],
        str(OUT),
    )

    results = pd.DataFrame(checks)
    results.to_csv(RESULTS, index=False, encoding="utf-8-sig")
    fail_count = int(results.status.eq("FAIL").sum())
    summary = {
        "status": "PASS" if fail_count == 0 else "FAIL",
        "pass_count": int(results.status.eq("PASS").sum()),
        "fail_count": fail_count,
        "total_count": len(results),
        "keyframe_count": len(batch),
        "real_user_output_empty": not any(USER_OUTPUT.iterdir()),
        "old_manual_event_count": old_count_after,
        "old_manual_sha256": old_hash_after,
        "propagation_run": False,
        "r04_accessed": False,
        "person_experiment_run": False,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
