from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path

import cv2
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "r02_manual_static_scene_anchor_preparation_20260902"
OUT = WORKSPACE / "output" / "r02_manual_static_scene_anchor_preparation_20260902"
BATCH = OUT / "R02_STATIC_SCENE_ANNOTATION_BATCH_V1.csv"
MANIFEST = OUT / "R02_STATIC_SCENE_ANNOTATION_BATCH_V1_MANIFEST.json"
RESULTS = OUT / "VALIDATION_RESULTS.csv"
SUMMARY = OUT / "VALIDATION_SUMMARY.json"
PREVIEW = OUT / "ANNOTATOR_PREVIEW.png"
OUTPUT_MANIFEST = OUT / "OUTPUT_MANIFEST.csv"
APP_PATH = TASK / "r02_static_scene_annotator.py"
FILENAME_RE = re.compile(r"frame_(\d+)_t(\d+)ms\.jpg$", re.IGNORECASE)

SAR_DIR = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\sar_pseudocolor\R02ZF"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_app():
    spec = importlib.util.spec_from_file_location("r02_static_scene_annotator_validation", APP_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(APP_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sar_inventory() -> list[tuple[int, int, str]]:
    rows = []
    for path in sorted(SAR_DIR.glob("*.jpg")):
        match = FILENAME_RE.match(path.name)
        if match:
            rows.append((int(match.group(1)), int(match.group(2)), str(path)))
    return rows


def write_output_manifest() -> None:
    paths = [
        BATCH,
        MANIFEST,
        RESULTS,
        SUMMARY,
        PREVIEW,
    ]
    rows = []
    for path in paths:
        if not path.exists():
            continue
        rows.append(
            {
                "workspace_relative_path": path.relative_to(WORKSPACE).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "artifact_role": "TOOL_VALIDATION_OR_EMPTY_BATCH_TEMPLATE",
                "contains_real_user_annotation": False,
            }
        )
    pd.DataFrame(rows).to_csv(OUTPUT_MANIFEST, index=False, encoding="utf-8-sig")


def main() -> None:
    app = load_app()
    batch = pd.read_csv(BATCH)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sar_rows = sar_inventory()
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

    check(
        "BATCH_HAS_18_PAIRS",
        len(batch) == 18 and batch.batch_index.tolist() == list(range(1, 19)),
        {"count": len(batch), "indices": batch.batch_index.tolist()},
        {"count": 18, "indices": list(range(1, 19))},
        BATCH.name,
    )
    core = batch[batch.optical_frame_index.eq(120)]
    check(
        "CORE_OPT_F120_INCLUDED_EXACTLY",
        len(core) == 1
        and int(core.iloc[0].optical_timestamp_ms) == 6667
        and int(core.iloc[0].sar_frame_index) == 200
        and int(core.iloc[0].sar_timestamp_ms) == 6667
        and int(core.iloc[0].nominal_timestamp_residual_ms) == 0,
        core[["optical_frame_index", "optical_timestamp_ms", "sar_frame_index", "sar_timestamp_ms", "nominal_timestamp_residual_ms"]].to_dict("records"),
        [{"optical_frame_index": 120, "optical_timestamp_ms": 6667, "sar_frame_index": 200, "sar_timestamp_ms": 6667, "nominal_timestamp_residual_ms": 0}],
        BATCH.name,
    )
    dense = batch[batch.optical_frame_index.between(110, 135)]
    check(
        "DENSE_F110_F135_CONTEXT",
        dense.optical_frame_index.tolist() == [110, 115, 120, 125, 130, 135],
        dense.optical_frame_index.tolist(),
        [110, 115, 120, 125, 130, 135],
        BATCH.name,
    )
    stable = batch[batch.optical_frame_index.isin([198, 201])]
    check(
        "STABLE_SEGMENT_CONTEXT_LIMITED_TO_TWO_PAIRS",
        len(stable) == 2 and stable.sar_frame_index.tolist() == [330, 335],
        stable[["optical_frame_index", "sar_frame_index"]].to_dict("records"),
        [{"optical_frame_index": 198, "sar_frame_index": 330}, {"optical_frame_index": 201, "sar_frame_index": 335}],
        BATCH.name,
    )
    check(
        "FULL_SEQUENCE_COVERAGE",
        int(batch.optical_frame_index.min()) == 0
        and int(batch.optical_frame_index.max()) == 297
        and batch.optical_frame_index.nunique() == 18,
        {"min": int(batch.optical_frame_index.min()), "max": int(batch.optical_frame_index.max()), "unique": int(batch.optical_frame_index.nunique())},
        {"min": 0, "max": 297, "unique": 18},
        BATCH.name,
    )

    nearest_failures = []
    for row in batch.itertuples(index=False):
        nearest = min(sar_rows, key=lambda item: (abs(item[1] - int(row.optical_timestamp_ms)), item[0]))
        if nearest[0] != int(row.sar_frame_index) or nearest[1] != int(row.sar_timestamp_ms):
            nearest_failures.append(
                {
                    "optical_frame": int(row.optical_frame_index),
                    "listed_sar": int(row.sar_frame_index),
                    "nearest_sar": nearest[0],
                }
            )
    check(
        "EVERY_PAIR_IS_TIMESTAMP_NEAREST",
        not nearest_failures
        and batch.sync_status.eq("NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED").all()
        and int(batch.nominal_timestamp_residual_ms.abs().max()) <= 33,
        {"failures": nearest_failures, "max_abs_residual_ms": int(batch.nominal_timestamp_residual_ms.abs().max())},
        {"failures": [], "max_abs_residual_ms": "<=33, including the optical end frame"},
        "raw SAR filenames + batch CSV",
    )
    missing_media = []
    for row in batch.itertuples(index=False):
        for value in (row.optical_image_path, row.sar_image_path):
            if not Path(value).is_file():
                missing_media.append(value)
    check(
        "ALL_BATCH_MEDIA_EXISTS",
        not missing_media,
        missing_media,
        [],
        "batch media paths",
    )
    expected_types = {
        "OPT_BOUNDARY_NEAR",
        "OPT_BOUNDARY_FAR",
        "OPT_STATIC_TREE_A",
        "OPT_STATIC_TREE_B",
        "OPT_STATIC_TREE_C",
        "SAR_BOUNDARY_NEAR",
        "SAR_BOUNDARY_FAR",
        "SAR_STATIC_POINT_TREE_A",
        "SAR_STATIC_POINT_TREE_B",
        "SAR_STATIC_POINT_TREE_C",
    }
    observed_types = {label.object_type for label in app.LABELS.values()}
    check(
        "REQUIRED_LABEL_CLASSES_AVAILABLE",
        observed_types == expected_types,
        sorted(observed_types),
        sorted(expected_types),
        "r02_static_scene_annotator.py LABELS",
    )
    check(
        "CONFIDENCE_STATES_AVAILABLE",
        app.CONFIDENCE_STATES == {"CONFIDENT", "LIKELY", "UNCERTAIN", "NOT_VISIBLE"},
        sorted(app.CONFIDENCE_STATES),
        ["CONFIDENT", "LIKELY", "NOT_VISIBLE", "UNCERTAIN"],
        "r02_static_scene_annotator.py",
    )

    required_record_fields = {
        "run_id",
        "optical_frame_index",
        "optical_timestamp_ms",
        "sar_frame_index",
        "sar_timestamp_ms",
        "modality",
        "object_id",
        "object_type",
        "geometry_type",
        "points",
        "confidence_state",
        "user_comment",
        "created_at",
    }
    with tempfile.TemporaryDirectory(prefix="r02_annotation_validator_") as temporary:
        temporary_path = Path(temporary)
        rows = app.read_batch(BATCH)
        store = app.AnnotationStore(temporary_path / "store", rows)
        record = store.upsert(
            rows[0], app.LABELS["1"], [[10.0, 20.0], [30.0, 40.0]], "LIKELY", "COMPLETE"
        )
        store.upsert(
            rows[0], app.LABELS["8"], [], "UNCERTAIN", "COMPLETE", "TREE_UNKNOWN"
        )
        store.write_views(set())
        reloaded = app.AnnotationStore(temporary_path / "store", rows)
        schema_ok = required_record_fields.issubset(record)
        tree_unknown = reloaded.get(1, app.LABELS["8"])
        append_only_lines = len(reloaded.events_path.read_text(encoding="utf-8").splitlines())
        check(
            "APPEND_ONLY_AUTOSAVE_AND_SCHEMA",
            schema_ok
            and append_only_lines == 2
            and reloaded.summary_path.exists()
            and reloaded.progress_path.exists()
            and reloaded.coverage_path.exists(),
            {"required_fields_present": schema_ok, "event_lines": append_only_lines, "summary": reloaded.summary_path.exists(), "progress": reloaded.progress_path.exists(), "coverage": reloaded.coverage_path.exists()},
            {"required_fields_present": True, "event_lines": 2, "summary": True, "progress": True, "coverage": True},
            "temporary AnnotationStore round trip",
        )
        check(
            "TREE_UNKNOWN_DOES_NOT_FORCE_POINT",
            tree_unknown is not None
            and tree_unknown["visibility_state"] == "TREE_UNKNOWN"
            and tree_unknown["points"] == []
            and tree_unknown["confidence_state"] == "UNCERTAIN",
            tree_unknown,
            {"visibility_state": "TREE_UNKNOWN", "points": [], "confidence_state": "UNCERTAIN"},
            "temporary AnnotationStore round trip",
        )
        smoke = app.smoke_test(BATCH)
        check(
            "APP_SMOKE_TEST",
            smoke["status"] == "PASS" and smoke["current_annotation_count"] == 2,
            smoke,
            {"status": "PASS", "current_annotation_count": 2},
            "r02_static_scene_annotator.smoke_test",
        )
        preview_output = temporary_path / "preview_store"
        annotator = app.Annotator(BATCH, preview_output)
        check(
            "AUTOMATIC_HINTS_DEFAULT_OFF",
            annotator.hints_enabled is False,
            annotator.hints_enabled,
            False,
            "fresh temporary session",
        )
        preview = annotator.render()
        ok, encoded = cv2.imencode(".png", preview)
        if not ok:
            raise RuntimeError("Preview encode failed")
        PREVIEW.parent.mkdir(parents=True, exist_ok=True)
        encoded.tofile(PREVIEW)

    launcher = (TASK / "START_R02_STATIC_ANNOTATION.bat").read_text(encoding="utf-8")
    check(
        "ONE_CLICK_LAUNCHER_FIXED_PY311",
        r"D:\MINICONDA\envs\py311\python.exe" in launcher
        and "r02_static_scene_annotator.py" in launcher,
        launcher.strip().splitlines(),
        [r"D:\MINICONDA\envs\py311\python.exe", "r02_static_scene_annotator.py"],
        "START_R02_STATIC_ANNOTATION.bat",
    )
    guide = (TASK / "HOW_TO_ANNOTATE_R02_STATIC_SCENE.md").read_text(encoding="utf-8")
    required_guide_terms = ["START_R02_STATIC_ANNOTATION.bat", "Enter", "Backspace", "Delete", "TREE_UNKNOWN", "自动保存", "跳过"]
    missing_guide_terms = [term for term in required_guide_terms if term not in guide]
    check(
        "ONE_PAGE_GUIDE_HAS_REQUIRED_ACTIONS",
        not missing_guide_terms and len(guide.splitlines()) <= 45,
        {"missing": missing_guide_terms, "line_count": len(guide.splitlines())},
        {"missing": [], "line_count": "<=45"},
        "HOW_TO_ANNOTATE_R02_STATIC_SCENE.md",
    )
    check(
        "EMPTY_TEMPLATE_CONTAINS_NO_USER_ANNOTATION",
        (TASK / "templates" / "manual_static_scene_annotations_TEMPLATE.jsonl").stat().st_size == 0,
        (TASK / "templates" / "manual_static_scene_annotations_TEMPLATE.jsonl").stat().st_size,
        0,
        "empty JSONL template",
    )
    check(
        "NO_PROPAGATION_OR_SCIENTIFIC_EXPERIMENT_OUTPUT",
        not (OUT / "propagated_static_scene_annotations.jsonl").exists()
        and not (OUT / "REVIEW_REQUIRED_FRAME_LIST.csv").exists(),
        {"propagated_exists": (OUT / "propagated_static_scene_annotations.jsonl").exists(), "review_required_exists": (OUT / "REVIEW_REQUIRED_FRAME_LIST.csv").exists()},
        {"propagated_exists": False, "review_required_exists": False},
        "output directory",
    )
    check(
        "BATCH_MANIFEST_DECLARATIONS",
        manifest["pair_count"] == 18
        and manifest["core_optical_f120_included"] is True
        and manifest["automatic_candidates_are_hints_only"] is True
        and manifest["person_gt"] is False,
        manifest,
        {"pair_count": 18, "core_optical_f120_included": True, "automatic_candidates_are_hints_only": True, "person_gt": False},
        MANIFEST.name,
    )

    results = pd.DataFrame(checks)
    pass_count = int(results.status.eq("PASS").sum())
    fail_count = int(results.status.eq("FAIL").sum())
    OUT.mkdir(parents=True, exist_ok=True)
    results.to_csv(RESULTS, index=False, encoding="utf-8-sig")
    summary = {
        "status": "PASS" if fail_count == 0 else "FAIL",
        "pass_count": pass_count,
        "fail_count": fail_count,
        "total_count": len(results),
        "batch_pair_count": len(batch),
        "core_optical_f120_included": len(core) == 1,
        "real_user_annotation_created": False,
        "seed_propagation_run": False,
        "person_experiment_run": False,
        "r04_accessed": False,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_output_manifest()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
