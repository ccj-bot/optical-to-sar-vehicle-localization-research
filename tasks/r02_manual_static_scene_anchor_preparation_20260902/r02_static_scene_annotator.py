from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "r02_manual_static_scene_anchor_preparation_20260902"
OUT = WORKSPACE / "output" / "r02_manual_static_scene_anchor_preparation_20260902"
DEFAULT_BATCH = OUT / "R02_STATIC_SCENE_ANNOTATION_BATCH_V1.csv"
DEFAULT_USER_DIR = OUT / "user_annotations"

CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 920
HEADER_HEIGHT = 105
PANEL_TOP = 120
PANEL_HEIGHT = 545
PANEL_WIDTH = 775
LEFT_X = 15
RIGHT_X = 810


@dataclass(frozen=True)
class LabelSpec:
    key: str
    modality: str
    object_id: str
    object_type: str
    geometry_type: str
    short_name: str
    color: tuple[int, int, int]


LABELS = {
    "1": LabelSpec("1", "OPTICAL", "R02_CURB_NEAR", "OPT_BOUNDARY_NEAR", "polyline", "OPT NEAR", (255, 255, 0)),
    "2": LabelSpec("2", "OPTICAL", "R02_CURB_FAR", "OPT_BOUNDARY_FAR", "polyline", "OPT FAR", (0, 165, 255)),
    "3": LabelSpec("3", "OPTICAL", "R02_TREE_A", "OPT_STATIC_TREE_A", "point", "OPT TREE A", (0, 255, 0)),
    "4": LabelSpec("4", "OPTICAL", "R02_TREE_B", "OPT_STATIC_TREE_B", "point", "OPT TREE B", (255, 100, 0)),
    "5": LabelSpec("5", "OPTICAL", "R02_TREE_C", "OPT_STATIC_TREE_C", "point", "OPT TREE C", (255, 0, 255)),
    "6": LabelSpec("6", "SAR", "R02_CURB_NEAR", "SAR_BOUNDARY_NEAR", "polyline", "SAR NEAR", (255, 255, 0)),
    "7": LabelSpec("7", "SAR", "R02_CURB_FAR", "SAR_BOUNDARY_FAR", "polyline", "SAR FAR", (0, 165, 255)),
    "8": LabelSpec("8", "SAR", "R02_TREE_A", "SAR_STATIC_POINT_TREE_A", "point", "SAR TREE A", (0, 255, 0)),
    "9": LabelSpec("9", "SAR", "R02_TREE_B", "SAR_STATIC_POINT_TREE_B", "point", "SAR TREE B", (255, 100, 0)),
    "0": LabelSpec("0", "SAR", "R02_TREE_C", "SAR_STATIC_POINT_TREE_C", "point", "SAR TREE C", (255, 0, 255)),
}

CONFIDENCE_STATES = {"CONFIDENT", "LIKELY", "UNCERTAIN", "NOT_VISIBLE"}


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_batch(path: Path) -> list[dict[str, object]]:
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    numeric = {
        "batch_index",
        "optical_frame_index",
        "optical_timestamp_ms",
        "sar_frame_index",
        "sar_timestamp_ms",
        "nominal_timestamp_residual_ms",
    }
    for row in rows:
        for key in numeric:
            row[key] = int(row[key])
        for key in {"nearest_optical_frame", "nearest_optical_timestamp_ms", "sync_residual_ms"}:
            if key in row and row[key] != "":
                row[key] = int(row[key])
    return rows


def read_bgr(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


class AnnotationStore:
    def __init__(self, output_dir: Path, batch: list[dict[str, object]]) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = output_dir / "manual_static_scene_annotations.jsonl"
        self.summary_path = output_dir / "manual_static_scene_annotation_summary.csv"
        self.progress_path = output_dir / "manual_static_scene_batch_progress.csv"
        self.coverage_path = output_dir / "ANNOTATION_COVERAGE_REPORT.json"
        self.state_path = output_dir / "annotation_session_state.json"
        self.batch = batch
        self.latest: dict[tuple[int, str, str], dict[str, object]] = {}
        self.revisions: dict[tuple[int, str, str], int] = {}
        self.events_path.touch(exist_ok=True)
        self._load_events()

    @staticmethod
    def key(record: dict[str, object]) -> tuple[int, str, str]:
        return int(record["batch_index"]), str(record["modality"]), str(record["object_id"])

    def _load_events(self) -> None:
        for line in self.events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            key = self.key(record)
            self.revisions[key] = max(self.revisions.get(key, 0), int(record.get("revision", 0)))
            if record.get("event_type") == "DELETE":
                self.latest.pop(key, None)
            else:
                self.latest[key] = record

    def append_event(self, record: dict[str, object]) -> None:
        payload = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with self.events_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(payload + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        key = self.key(record)
        self.revisions[key] = int(record["revision"])
        if record["event_type"] == "DELETE":
            self.latest.pop(key, None)
        else:
            self.latest[key] = record

    def upsert(
        self,
        batch_row: dict[str, object],
        label: LabelSpec,
        points: list[list[float]],
        confidence_state: str,
        geometry_status: str,
        visibility_state: str = "VISIBLE_OR_GEOMETRY_PROVIDED",
        user_comment: str = "",
    ) -> dict[str, object]:
        if confidence_state not in CONFIDENCE_STATES:
            raise ValueError(confidence_state)
        key = (int(batch_row["batch_index"]), label.modality, label.object_id)
        revision = self.revisions.get(key, 0) + 1
        created_at = utc_now()
        record = {
            "annotation_schema": "R02_MANUAL_STATIC_SCENE_ANNOTATION_V1",
            "event_id": str(uuid.uuid4()),
            "annotation_id": f"R02ZF_B{int(batch_row['batch_index']):02d}_{label.modality}_{label.object_id}",
            "revision": revision,
            "event_type": "UPSERT",
            "batch_index": int(batch_row["batch_index"]),
            "run_id": str(batch_row["run_id"]),
            "optical_frame_index": int(batch_row["optical_frame_index"]),
            "optical_timestamp_ms": int(batch_row["optical_timestamp_ms"]),
            "sar_frame_index": int(batch_row["sar_frame_index"]),
            "sar_timestamp_ms": int(batch_row["sar_timestamp_ms"]),
            "nominal_timestamp_residual_ms": int(batch_row["nominal_timestamp_residual_ms"]),
            "sync_status": str(batch_row["sync_status"]),
            "bracket_id": str(batch_row.get("bracket_id", "")),
            "seed_role": str(batch_row.get("seed_role", "")),
            "annotation_scope": str(batch_row.get("annotation_scope", "FULL_STATIC_SCENE")),
            "modality": label.modality,
            "object_id": label.object_id,
            "object_type": label.object_type,
            "geometry_type": label.geometry_type,
            "points": [[round(float(x), 3), round(float(y), 3)] for x, y in points],
            "geometry_status": geometry_status,
            "confidence_state": confidence_state,
            "visibility_state": visibility_state,
            "user_comment": user_comment,
            "source": "MANUAL_USER",
            "automatic_hint_used_as_identity_authority": False,
            "person_gt": False,
            "created_at": created_at,
        }
        self.append_event(record)
        return record

    def delete(self, batch_row: dict[str, object], label: LabelSpec) -> None:
        key = (int(batch_row["batch_index"]), label.modality, label.object_id)
        revision = self.revisions.get(key, 0) + 1
        record = {
            "annotation_schema": "R02_MANUAL_STATIC_SCENE_ANNOTATION_V1",
            "event_id": str(uuid.uuid4()),
            "annotation_id": f"R02ZF_B{int(batch_row['batch_index']):02d}_{label.modality}_{label.object_id}",
            "revision": revision,
            "event_type": "DELETE",
            "batch_index": int(batch_row["batch_index"]),
            "run_id": str(batch_row["run_id"]),
            "optical_frame_index": int(batch_row["optical_frame_index"]),
            "optical_timestamp_ms": int(batch_row["optical_timestamp_ms"]),
            "sar_frame_index": int(batch_row["sar_frame_index"]),
            "sar_timestamp_ms": int(batch_row["sar_timestamp_ms"]),
            "nominal_timestamp_residual_ms": int(batch_row["nominal_timestamp_residual_ms"]),
            "sync_status": str(batch_row["sync_status"]),
            "bracket_id": str(batch_row.get("bracket_id", "")),
            "seed_role": str(batch_row.get("seed_role", "")),
            "annotation_scope": str(batch_row.get("annotation_scope", "FULL_STATIC_SCENE")),
            "modality": label.modality,
            "object_id": label.object_id,
            "object_type": label.object_type,
            "geometry_type": label.geometry_type,
            "points": [],
            "geometry_status": "DELETED",
            "confidence_state": "UNCERTAIN",
            "visibility_state": "DELETED_BY_USER",
            "user_comment": "",
            "source": "MANUAL_USER",
            "automatic_hint_used_as_identity_authority": False,
            "person_gt": False,
            "created_at": utc_now(),
        }
        self.append_event(record)

    def get(self, batch_index: int, label: LabelSpec) -> dict[str, object] | None:
        return self.latest.get((batch_index, label.modality, label.object_id))

    def current_for_batch(self, batch_index: int) -> list[dict[str, object]]:
        return sorted(
            [record for key, record in self.latest.items() if key[0] == batch_index],
            key=lambda item: (str(item["modality"]), str(item["object_type"])),
        )

    def write_views(self, skipped: set[int]) -> None:
        fields = [
            "run_id",
            "batch_index",
            "bracket_id",
            "seed_role",
            "annotation_scope",
            "optical_frame_index",
            "optical_timestamp_ms",
            "sar_frame_index",
            "sar_timestamp_ms",
            "nominal_timestamp_residual_ms",
            "modality",
            "object_id",
            "object_type",
            "geometry_type",
            "points",
            "point_count",
            "geometry_status",
            "confidence_state",
            "visibility_state",
            "user_comment",
            "created_at",
        ]
        lines: list[str] = []
        temporary_summary = self.summary_path.with_suffix(".csv.tmp")
        with temporary_summary.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for record in sorted(self.latest.values(), key=lambda item: (int(item["batch_index"]), str(item["modality"]), str(item["object_type"]))):
                row = {key: record.get(key, "") for key in fields}
                row["points"] = json.dumps(record.get("points", []), ensure_ascii=False)
                row["point_count"] = len(record.get("points", []))
                writer.writerow(row)
        temporary_summary.replace(self.summary_path)

        progress_fields = [
            "batch_index",
            "run_id",
            "bracket_id",
            "seed_role",
            "annotation_scope",
            "optical_frame_index",
            "optical_timestamp_ms",
            "sar_frame_index",
            "sar_timestamp_ms",
            "nominal_timestamp_residual_ms",
            "frame_status",
            "annotation_count",
            "completed_annotation_count",
            "draft_annotation_count",
        ]
        temporary_progress = self.progress_path.with_suffix(".csv.tmp")
        with temporary_progress.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=progress_fields)
            writer.writeheader()
            for batch_row in self.batch:
                batch_index = int(batch_row["batch_index"])
                records = self.current_for_batch(batch_index)
                completed = sum(record.get("geometry_status") == "COMPLETE" for record in records)
                drafts = sum(record.get("geometry_status") == "DRAFT" for record in records)
                if batch_index in skipped:
                    frame_status = "SKIPPED"
                elif completed:
                    frame_status = "ANNOTATED"
                elif drafts:
                    frame_status = "IN_PROGRESS"
                else:
                    frame_status = "PENDING"
                writer.writerow(
                    {
                        "batch_index": batch_index,
                        "run_id": batch_row["run_id"],
                        "bracket_id": batch_row.get("bracket_id", ""),
                        "seed_role": batch_row.get("seed_role", ""),
                        "annotation_scope": batch_row.get("annotation_scope", "FULL_STATIC_SCENE"),
                        "optical_frame_index": batch_row["optical_frame_index"],
                        "optical_timestamp_ms": batch_row["optical_timestamp_ms"],
                        "sar_frame_index": batch_row["sar_frame_index"],
                        "sar_timestamp_ms": batch_row["sar_timestamp_ms"],
                        "nominal_timestamp_residual_ms": batch_row["nominal_timestamp_residual_ms"],
                        "frame_status": frame_status,
                        "annotation_count": len(records),
                        "completed_annotation_count": completed,
                        "draft_annotation_count": drafts,
                    }
                )
        temporary_progress.replace(self.progress_path)

        records = list(self.latest.values())
        accepted_states = {"CONFIDENT", "LIKELY"}

        def accepted(record: dict[str, object] | None) -> bool:
            return bool(
                record
                and record.get("geometry_status") == "COMPLETE"
                and record.get("confidence_state") in accepted_states
                and record.get("visibility_state") == "VISIBLE_OR_GEOMETRY_PROVIDED"
                and record.get("points")
            )

        object_type_counts: dict[str, dict[str, int]] = {}
        for object_type in sorted({label.object_type for label in LABELS.values()}):
            typed = [record for record in records if record.get("object_type") == object_type]
            object_type_counts[object_type] = {
                "annotated_frames": len({int(record["batch_index"]) for record in typed}),
                "confident_frames": len({int(record["batch_index"]) for record in typed if record.get("confidence_state") == "CONFIDENT"}),
                "likely_frames": len({int(record["batch_index"]) for record in typed if record.get("confidence_state") == "LIKELY"}),
                "uncertain_frames": len({int(record["batch_index"]) for record in typed if record.get("confidence_state") == "UNCERTAIN"}),
                "not_visible_frames": len({int(record["batch_index"]) for record in typed if record.get("confidence_state") == "NOT_VISIBLE"}),
            }

        stable_identity_pairs: list[int] = []
        full_static_identity_pairs: list[int] = []
        unresolved_pairs: list[int] = []
        for batch_row in self.batch:
            batch_index = int(batch_row["batch_index"])
            current = self.current_for_batch(batch_index)
            by_type = {str(record["object_type"]): record for record in current}
            if batch_row.get("annotation_scope") == "SAR_BOUNDARY_ONLY":
                required_boundary_types = {"SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"}
            else:
                required_boundary_types = {
                    "OPT_BOUNDARY_NEAR",
                    "OPT_BOUNDARY_FAR",
                    "SAR_BOUNDARY_NEAR",
                    "SAR_BOUNDARY_FAR",
                }
            if all(accepted(by_type.get(object_type)) for object_type in required_boundary_types):
                stable_identity_pairs.append(batch_index)
                if batch_row.get("annotation_scope") != "SAR_BOUNDARY_ONLY":
                    full_static_identity_pairs.append(batch_index)
            if batch_index in skipped or not all(object_type in by_type for object_type in required_boundary_types) or any(
                record.get("confidence_state") in {"UNCERTAIN", "NOT_VISIBLE"}
                or record.get("visibility_state") == "TREE_UNKNOWN"
                for record in current
            ):
                unresolved_pairs.append(batch_index)

        sar_tree_confident = [
            record
            for record in records
            if str(record.get("object_type", "")).startswith("SAR_STATIC_POINT_TREE_")
            and record.get("confidence_state") == "CONFIDENT"
            and record.get("geometry_status") == "COMPLETE"
            and record.get("points")
        ]
        coverage = {
            "schema": "R02_MANUAL_STATIC_SCENE_ANNOTATION_COVERAGE_V1",
            "generated_at": utc_now(),
            "batch_pair_count": len(self.batch),
            "annotation_scopes": sorted({str(row.get("annotation_scope", "FULL_STATIC_SCENE")) for row in self.batch}),
            "object_type_counts": object_type_counts,
            "required_boundary_identity_supported_batch_indices": stable_identity_pairs,
            "both_optical_and_sar_boundary_identity_supported_batch_indices": full_static_identity_pairs,
            "unable_to_judge_or_incomplete_batch_indices": sorted(set(unresolved_pairs)),
            "sar_tree_confident_correspondence_count": len(sar_tree_confident),
            "skipped_batch_indices": sorted(skipped),
            "analysis_note": "Coverage only; no propagation, fitting, or PERSON experiment was run.",
        }
        atomic_write_text(self.coverage_path, json.dumps(coverage, ensure_ascii=False, indent=2))


class Annotator:
    def __init__(self, batch_path: Path, output_dir: Path) -> None:
        self.batch_path = batch_path
        self.batch = read_batch(batch_path)
        if not self.batch:
            raise RuntimeError("Annotation batch is empty")
        self.store = AnnotationStore(output_dir, self.batch)
        self.index = 0
        self.active_key = "1"
        self.confidence_state = "CONFIDENT"
        self.hints_enabled = False
        self.skipped: set[int] = set()
        self.status_message = "Ready. Hints are OFF; the user is identity authority."
        self.transforms: dict[str, tuple[int, int, int, int, int, int]] = {}
        self.drawing_key: tuple[int, str] | None = None
        self.draft_points: list[list[float]] = []
        self.image_cache: dict[str, np.ndarray] = {}
        self._load_state()
        self._autosave_views()

    @property
    def row(self) -> dict[str, object]:
        return self.batch[self.index]

    @property
    def active_label(self) -> LabelSpec:
        return LABELS[self.active_key]

    def _load_state(self) -> None:
        if not self.store.state_path.exists():
            return
        try:
            state = json.loads(self.store.state_path.read_text(encoding="utf-8"))
            self.index = min(max(int(state.get("current_index", 0)), 0), len(self.batch) - 1)
            active_key = str(state.get("active_key", "1"))
            self.active_key = active_key if active_key in LABELS else "1"
            confidence = str(state.get("confidence_state", "CONFIDENT"))
            self.confidence_state = confidence if confidence in CONFIDENCE_STATES else "CONFIDENT"
            self.hints_enabled = bool(state.get("hints_enabled", False))
            self.skipped = {int(value) for value in state.get("skipped_batch_indices", [])}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.status_message = "Session state could not be loaded; annotations remain intact."

    def _save_state(self) -> None:
        state = {
            "schema": "R02_STATIC_SCENE_ANNOTATION_SESSION_V1",
            "current_index": self.index,
            "current_batch_index": int(self.row["batch_index"]),
            "active_key": self.active_key,
            "confidence_state": self.confidence_state,
            "hints_enabled": self.hints_enabled,
            "skipped_batch_indices": sorted(self.skipped),
            "last_saved_at": utc_now(),
        }
        atomic_write_text(self.store.state_path, json.dumps(state, ensure_ascii=False, indent=2))

    def _autosave_views(self) -> None:
        self.store.write_views(self.skipped)
        self._save_state()

    def load_image(self, path: str) -> np.ndarray:
        if path not in self.image_cache:
            self.image_cache[path] = read_bgr(Path(path))
        return self.image_cache[path].copy()

    def draw_automatic_hints(self, image: np.ndarray, modality: str) -> None:
        if not self.hints_enabled:
            return
        if modality == "OPTICAL":
            slope = 0.02666536443690682
            intercept = -45.502258572693094
            for theta in (-30.0, 0.0, 30.0):
                x = int(round((theta - intercept) / slope))
                if 0 <= x < image.shape[1]:
                    cv2.line(image, (x, 0), (x, image.shape[0] - 1), (90, 90, 90), 5, cv2.LINE_AA)
                    cv2.putText(image, f"AUTOMATIC_HINT theta={theta:+.0f}", (x + 12, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (240, 240, 240), 3, cv2.LINE_AA)
        else:
            cx, cy = 511.745326, 590.776351
            px_per_m = 591.340317 / 20.0
            for theta in (-30.0, 0.0, 30.0):
                points = []
                for distance in np.linspace(2.0, 20.0, 80):
                    x = int(round(cx + distance * px_per_m * np.tan(np.deg2rad(theta))))
                    y = int(round(cy - distance * px_per_m))
                    if 0 <= x < image.shape[1] and 0 <= y < image.shape[0]:
                        points.append((x, y))
                if len(points) > 1:
                    cv2.polylines(image, [np.asarray(points, np.int32)], False, (80, 80, 80), 1, cv2.LINE_AA)
            for distance, color in [(4.9, (255, 255, 0)), (7.1, (0, 165, 255)), (12.4, (255, 0, 255))]:
                y = int(round(cy - distance * px_per_m))
                x0 = int(round(cx + distance * px_per_m * np.tan(np.deg2rad(-48.0))))
                x1 = int(round(cx + distance * px_per_m * np.tan(np.deg2rad(48.0))))
                cv2.line(image, (max(0, x0), y), (min(image.shape[1] - 1, x1), y), color, 2, cv2.LINE_AA)
                cv2.putText(image, f"AUTOMATIC_HINT {distance:.1f}m", (max(4, x0 + 5), max(18, y - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    def draw_saved_annotations(self, image: np.ndarray, modality: str) -> None:
        batch_index = int(self.row["batch_index"])
        for label in LABELS.values():
            if label.modality != modality:
                continue
            record = self.store.get(batch_index, label)
            if record is None:
                continue
            points = np.asarray(record.get("points", []), dtype=np.float32)
            if len(points):
                points_int = np.round(points).astype(np.int32)
                thickness = max(2, int(round(image.shape[1] / 900)))
                if label.geometry_type == "polyline":
                    cv2.polylines(image, [points_int], False, label.color, thickness, cv2.LINE_AA)
                    for point in points_int:
                        cv2.circle(image, tuple(point), thickness + 2, label.color, -1, cv2.LINE_AA)
                else:
                    cv2.circle(image, tuple(points_int[0]), thickness * 4 + 4, label.color, thickness, cv2.LINE_AA)
                origin = tuple(points_int[0])
                cv2.putText(
                    image,
                    f"{label.short_name} {record['confidence_state']} {record['geometry_status']}",
                    (origin[0] + 10, max(25, origin[1] - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    max(0.5, image.shape[1] / 3800),
                    label.color,
                    thickness,
                    cv2.LINE_AA,
                )

    def prepare_panel_image(self, modality: str) -> np.ndarray:
        path_key = "optical_image_path" if modality == "OPTICAL" else "sar_image_path"
        image = self.load_image(str(self.row[path_key]))
        self.draw_automatic_hints(image, modality)
        self.draw_saved_annotations(image, modality)
        return image

    def fit_panel(self, image: np.ndarray, x: int, y: int, modality: str) -> np.ndarray:
        scale = min(PANEL_WIDTH / image.shape[1], PANEL_HEIGHT / image.shape[0])
        width = max(1, int(round(image.shape[1] * scale)))
        height = max(1, int(round(image.shape[0] * scale)))
        resized = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        x0 = x + (PANEL_WIDTH - width) // 2
        y0 = y + (PANEL_HEIGHT - height) // 2
        self.transforms[modality] = (x0, y0, width, height, image.shape[1], image.shape[0])
        return resized

    def render(self) -> np.ndarray:
        canvas = np.full((CANVAS_HEIGHT, CANVAS_WIDTH, 3), (24, 27, 31), np.uint8)
        optical = self.prepare_panel_image("OPTICAL")
        sar = self.prepare_panel_image("SAR")
        optical_view = self.fit_panel(optical, LEFT_X, PANEL_TOP, "OPTICAL")
        sar_view = self.fit_panel(sar, RIGHT_X, PANEL_TOP, "SAR")
        for modality, view in [("OPTICAL", optical_view), ("SAR", sar_view)]:
            x0, y0, width, height, _, _ = self.transforms[modality]
            canvas[y0 : y0 + height, x0 : x0 + width] = view
            cv2.rectangle(canvas, (x0 - 1, y0 - 1), (x0 + width, y0 + height), (180, 180, 180), 1)

        row = self.row
        cv2.putText(canvas, f"R02 MANUAL STATIC-SCENE ANCHOR | pair {self.index + 1}/{len(self.batch)} | batch B{int(row['batch_index']):02d}", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (245, 245, 245), 2, cv2.LINE_AA)
        cv2.putText(canvas, f"OPT F{int(row['optical_frame_index']):03d} t={int(row['optical_timestamp_ms']):06d}ms   |   SAR F{int(row['sar_frame_index']):03d} t={int(row['sar_timestamp_ms']):06d}ms   |   nominal residual={int(row['nominal_timestamp_residual_ms']):+d}ms", (18, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.66, (220, 220, 220), 2, cv2.LINE_AA)
        hint_text = "ON (AUTOMATIC_HINT only)" if self.hints_enabled else "OFF (recommended for identity judgment)"
        cv2.putText(canvas, f"ACTIVE: [{self.active_key}] {self.active_label.short_name} | confidence={self.confidence_state} | hints={hint_text}", (18, 91), cv2.FONT_HERSHEY_SIMPLEX, 0.62, self.active_label.color, 2, cv2.LINE_AA)
        cv2.putText(canvas, "LEFT: synchronized optical", (LEFT_X + 8, PANEL_TOP - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (210, 210, 210), 1, cv2.LINE_AA)
        cv2.putText(canvas, "RIGHT: synchronized SAR", (RIGHT_X + 8, PANEL_TOP - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (210, 210, 210), 1, cv2.LINE_AA)

        current = self.store.current_for_batch(int(row["batch_index"]))
        complete_count = sum(item.get("geometry_status") == "COMPLETE" for item in current)
        cv2.putText(canvas, f"Current pair: {len(current)} saved objects, {complete_count} complete.  Append-only JSONL autosaves every click.", (18, 700), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (200, 220, 200), 1, cv2.LINE_AA)
        saved_text = " | ".join(f"{item['object_type']}:{item['confidence_state']}" for item in current[:6]) or "none"
        cv2.putText(canvas, f"Saved: {saved_text}", (18, 728), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (185, 185, 185), 1, cv2.LINE_AA)
        cv2.putText(canvas, "Labels  1 OPT_NEAR  2 OPT_FAR  3/4/5 OPT_TREE_A/B/C  |  6 SAR_NEAR  7 SAR_FAR  8/9/0 SAR_TREE_A/B/C", (18, 770), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (235, 235, 235), 1, cv2.LINE_AA)
        cv2.putText(canvas, "Draw  Left click add point  Enter finish line  Backspace undo point  Delete remove active  |  C/L/U/V confidence", (18, 802), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (235, 235, 235), 1, cv2.LINE_AA)
        cv2.putText(canvas, "Browse  D/Right next  A/Left previous  S skip  |  X SAR tree unknown  H hints  Q/Esc save+quit", (18, 834), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (235, 235, 235), 1, cv2.LINE_AA)
        cv2.rectangle(canvas, (12, 856), (1588, 906), (55, 60, 68), -1)
        cv2.putText(canvas, self.status_message[:150], (24, 888), cv2.FONT_HERSHEY_SIMPLEX, 0.57, (255, 220, 120), 1, cv2.LINE_AA)
        return canvas

    def map_click(self, x: int, y: int) -> tuple[str, list[float]] | None:
        for modality, transform in self.transforms.items():
            x0, y0, width, height, source_width, source_height = transform
            if x0 <= x < x0 + width and y0 <= y < y0 + height:
                source_x = (x - x0) / width * source_width
                source_y = (y - y0) / height * source_height
                return modality, [source_x, source_y]
        return None

    def on_mouse(self, event: int, x: int, y: int, flags: int, parameter: object) -> None:
        del flags, parameter
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        mapped = self.map_click(x, y)
        if mapped is None:
            self.status_message = "Click inside the optical or SAR image."
            return
        modality, point = mapped
        label = self.active_label
        if modality != label.modality:
            self.status_message = f"Active label is {label.modality}; click the matching panel or select another label."
            return
        batch_index = int(self.row["batch_index"])
        if label.geometry_type == "point":
            self.store.upsert(self.row, label, [point], self.confidence_state, "COMPLETE")
            self.drawing_key = None
            self.draft_points = []
            self.status_message = f"Autosaved {label.short_name} point."
        else:
            drawing_key = (batch_index, label.key)
            if self.drawing_key != drawing_key:
                self.drawing_key = drawing_key
                existing = self.store.get(batch_index, label)
                if existing and existing.get("geometry_status") == "DRAFT":
                    self.draft_points = [list(item) for item in existing.get("points", [])]
                else:
                    self.draft_points = []
            self.draft_points.append(point)
            self.store.upsert(self.row, label, self.draft_points, self.confidence_state, "DRAFT")
            self.status_message = f"Autosaved {label.short_name} draft point {len(self.draft_points)}; press Enter to finish."
        self.skipped.discard(batch_index)
        self._autosave_views()

    def select_label(self, key: str) -> None:
        self.active_key = key
        self.drawing_key = None
        self.draft_points = []
        self.status_message = f"Selected [{key}] {self.active_label.short_name}."
        self._save_state()

    def update_confidence(self, confidence: str) -> None:
        self.confidence_state = confidence
        existing = self.store.get(int(self.row["batch_index"]), self.active_label)
        if existing is not None:
            self.store.upsert(
                self.row,
                self.active_label,
                [list(item) for item in existing.get("points", [])],
                confidence,
                str(existing.get("geometry_status", "COMPLETE")),
                str(existing.get("visibility_state", "VISIBLE_OR_GEOMETRY_PROVIDED")),
                str(existing.get("user_comment", "")),
            )
            self._autosave_views()
        else:
            self._save_state()
        self.status_message = f"Confidence set to {confidence}."

    def mark_not_visible(self) -> None:
        self.confidence_state = "NOT_VISIBLE"
        self.store.upsert(
            self.row,
            self.active_label,
            [],
            "NOT_VISIBLE",
            "COMPLETE",
            "NOT_VISIBLE",
        )
        self.drawing_key = None
        self.draft_points = []
        self.status_message = f"Autosaved {self.active_label.short_name} as NOT_VISIBLE."
        self._autosave_views()

    def mark_tree_unknown(self) -> None:
        label = self.active_label
        if label.modality != "SAR" or "TREE" not in label.object_type:
            self.status_message = "TREE_UNKNOWN is only valid for active SAR TREE A/B/C."
            return
        self.confidence_state = "UNCERTAIN"
        self.store.upsert(
            self.row,
            label,
            [],
            "UNCERTAIN",
            "COMPLETE",
            "TREE_UNKNOWN",
        )
        self.status_message = f"Autosaved {label.short_name} as TREE_UNKNOWN; no SAR point was forced."
        self._autosave_views()

    def finish_polyline(self) -> None:
        label = self.active_label
        if label.geometry_type != "polyline":
            self.status_message = "The active label is a point; one click already completes it."
            return
        existing = self.store.get(int(self.row["batch_index"]), label)
        points = self.draft_points or ([list(item) for item in existing.get("points", [])] if existing else [])
        if len(points) < 2:
            self.status_message = "A polyline needs at least 2 points; 3-8 points is recommended."
            return
        self.store.upsert(self.row, label, points, self.confidence_state, "COMPLETE")
        self.drawing_key = None
        self.draft_points = []
        self.status_message = f"Autosaved completed {label.short_name} polyline with {len(points)} points."
        self._autosave_views()

    def undo_last_point(self) -> None:
        label = self.active_label
        existing = self.store.get(int(self.row["batch_index"]), label)
        if existing is None or not existing.get("points"):
            self.status_message = "No point to undo for the active label."
            return
        points = [list(item) for item in existing["points"]][:-1]
        if not points:
            self.store.delete(self.row, label)
            self.drawing_key = None
            self.draft_points = []
            self.status_message = f"Removed the last point and cleared {label.short_name}."
        else:
            geometry_status = "DRAFT" if label.geometry_type == "polyline" else "COMPLETE"
            self.store.upsert(self.row, label, points, self.confidence_state, geometry_status)
            self.drawing_key = (int(self.row["batch_index"]), label.key) if label.geometry_type == "polyline" else None
            self.draft_points = points if label.geometry_type == "polyline" else []
            self.status_message = f"Autosaved undo; {len(points)} point(s) remain."
        self._autosave_views()

    def delete_active(self) -> None:
        self.store.delete(self.row, self.active_label)
        self.drawing_key = None
        self.draft_points = []
        self.status_message = f"Deleted active {self.active_label.short_name}; delete event was preserved."
        self._autosave_views()

    def move(self, delta: int) -> None:
        self.index = min(max(self.index + delta, 0), len(self.batch) - 1)
        self.drawing_key = None
        self.draft_points = []
        self.image_cache.clear()
        self.status_message = f"Moved to pair {self.index + 1}/{len(self.batch)}."
        self._save_state()

    def skip_current(self) -> None:
        self.skipped.add(int(self.row["batch_index"]))
        self.status_message = f"Marked batch B{int(self.row['batch_index']):02d} SKIPPED; you can return later."
        self._autosave_views()
        if self.index < len(self.batch) - 1:
            self.move(1)

    def handle_key(self, key: int) -> bool:
        low = key & 0xFF
        if 0 <= low < 128 and chr(low) in LABELS:
            self.select_label(chr(low))
        elif low in (ord("c"), ord("C")):
            self.update_confidence("CONFIDENT")
        elif low in (ord("l"), ord("L")):
            self.update_confidence("LIKELY")
        elif low in (ord("u"), ord("U")):
            self.update_confidence("UNCERTAIN")
        elif low in (ord("v"), ord("V")):
            self.mark_not_visible()
        elif low in (ord("x"), ord("X")):
            self.mark_tree_unknown()
        elif low in (ord("h"), ord("H")):
            self.hints_enabled = not self.hints_enabled
            self.status_message = f"AUTOMATIC_HINT {'ON' if self.hints_enabled else 'OFF'}; hints are never truth."
            self._save_state()
        elif low in (ord("s"), ord("S")):
            self.skip_current()
        elif low in (ord("d"), ord("D")) or key == 2555904:
            self.move(1)
        elif low in (ord("a"), ord("A")) or key == 2424832:
            self.move(-1)
        elif low in (13, 10):
            self.finish_polyline()
        elif low == 8:
            self.undo_last_point()
        elif low in (46, 127) or key == 3014656:
            self.delete_active()
        elif low in (27, ord("q"), ord("Q")):
            self._autosave_views()
            return False
        return True

    def run(self) -> None:
        window_name = "R02 Manual Static Scene Annotation"
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(window_name, self.on_mouse)
        running = True
        while running:
            cv2.imshow(window_name, self.render())
            key = cv2.waitKeyEx(40)
            if key != -1:
                running = self.handle_key(key)
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
        self._autosave_views()
        cv2.destroyAllWindows()


def smoke_test(batch_path: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="r02_static_annotation_smoke_") as temporary:
        output_dir = Path(temporary)
        batch = read_batch(batch_path)
        store = AnnotationStore(output_dir, batch)
        row = batch[0]
        near = LABELS["1"]
        tree = LABELS["8"]
        store.upsert(row, near, [[100.0, 200.0]], "CONFIDENT", "DRAFT")
        store.upsert(row, near, [[100.0, 200.0], [300.0, 205.0], [500.0, 210.0]], "CONFIDENT", "COMPLETE")
        store.upsert(row, tree, [], "UNCERTAIN", "COMPLETE", "TREE_UNKNOWN")
        store.write_views(set())
        reloaded = AnnotationStore(output_dir, batch)
        near_record = reloaded.get(int(row["batch_index"]), near)
        tree_record = reloaded.get(int(row["batch_index"]), tree)
        if near_record is None or len(near_record["points"]) != 3 or near_record["geometry_status"] != "COMPLETE":
            raise AssertionError("Polyline autosave/reload failed")
        if tree_record is None or tree_record["visibility_state"] != "TREE_UNKNOWN":
            raise AssertionError("TREE_UNKNOWN autosave/reload failed")
        return {
            "status": "PASS",
            "event_count": len(reloaded.events_path.read_text(encoding="utf-8").splitlines()),
            "current_annotation_count": len(reloaded.latest),
            "summary_exists": reloaded.summary_path.exists(),
            "progress_exists": reloaded.progress_path.exists(),
            "coverage_exists": reloaded.coverage_path.exists(),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual R02ZF static-scene annotation tool")
    parser.add_argument("--batch", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_USER_DIR)
    parser.add_argument("--render-preview", type=Path)
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    if args.smoke_test:
        print(json.dumps(smoke_test(args.batch), ensure_ascii=False, indent=2))
        return
    annotator = Annotator(args.batch, args.output_dir)
    if args.render_preview:
        args.render_preview.parent.mkdir(parents=True, exist_ok=True)
        ok, encoded = cv2.imencode(".png", annotator.render())
        if not ok:
            raise RuntimeError("Preview encoding failed")
        encoded.tofile(args.render_preview)
        print(args.render_preview)
        return
    annotator.run()


if __name__ == "__main__":
    main()
