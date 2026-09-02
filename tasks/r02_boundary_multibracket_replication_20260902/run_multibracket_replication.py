from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "r02_boundary_multibracket_replication_20260902"
OUT = WORKSPACE / "output" / "r02_boundary_multibracket_replication_20260902"
FIG = OUT / "figures"
MANUAL_EVENTS = (
    WORKSPACE
    / "output"
    / "r02_boundary_multibracket_preparation_20260902"
    / "user_annotations"
    / "manual_static_scene_annotations.jsonl"
)
BATCH = (
    WORKSPACE
    / "output"
    / "r02_boundary_multibracket_preparation_20260902"
    / "R02_BOUNDARY_MULTIBRACKET_ANNOTATION_BATCH_V1.csv"
)
FROZEN_SCRIPT = (
    WORKSPACE
    / "tasks"
    / "r02_manual_seed_temporal_propagation_20260902"
    / "run_manual_seed_temporal_propagation.py"
)
COMPARATOR_SUMMARY = (
    WORKSPACE
    / "output"
    / "r02_manual_seed_temporal_propagation_20260902"
    / "MANUAL_SEED_TEMPORAL_PROPAGATION_SUMMARY.json"
)
OPTICAL_DIR = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\optical\R02ZF"
)
FILENAME_RE = re.compile(r"frame_(\d+)_t(\d+)ms\.jpg$", re.IGNORECASE)

NORMALIZED_SEEDS = OUT / "normalized_user_confirmed_seeds.jsonl"
DIRECTIONAL_PATHS = OUT / "directional_propagation_paths.jsonl"
CLOSED_RECORDS = OUT / "closed_static_scene_annotations.jsonl"
DIAGNOSTICS = OUT / "propagation_frame_diagnostics.csv"
OVERLAP_METRICS = OUT / "overlap_closure_metrics.csv"
REVIEW = OUT / "REVIEW_REQUIRED_FRAME_LIST.csv"
REPAIR_BATCH = OUT / "R02_BOUNDARY_REPAIR_ANNOTATION_BATCH_V1.csv"
COMPARISON = OUT / "BRACKET_COMPARISON.csv"
SUMMARY = OUT / "MULTIBRACKET_REPLICATION_SUMMARY.json"
REPORT = OUT / "REPORT.md"
PARAMETERS = OUT / "FROZEN_PARAMETER_MANIFEST.json"
OUTPUT_MANIFEST = OUT / "OUTPUT_MANIFEST.csv"

BOUNDARY_TYPES = ["SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"]
EXPECTED_MANUAL_SHA256 = "2650f9ec2cbe3709475144b6905dd7e9e83d18ddab4d3876098a4877556f2f1e"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


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


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def closure_gate_label(value: object, availability: str) -> str:
    if availability != "AVAILABLE_BIDIRECTIONAL_OVERLAP":
        return availability
    return str(value)


def read_bgr(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def write_png(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError(path)
    encoded.tofile(path)


def latest_seed_events() -> tuple[list[dict[str, object]], int]:
    raw = [json.loads(line) for line in MANUAL_EVENTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest: dict[tuple[int, str], dict[str, object]] = {}
    for event in raw:
        if event.get("modality") == "SAR" and event.get("object_type") in BOUNDARY_TYPES:
            latest[(int(event["batch_index"]), str(event["object_type"]))] = event
    active = [event for event in latest.values() if event.get("event_type") != "DELETE"]
    return active, len(raw)


def normalized_seed_rows(events: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for event in sorted(events, key=lambda item: (int(item["batch_index"]), str(item["object_type"]))):
        if event.get("confidence_state") not in {"CONFIDENT", "LIKELY"} or len(event.get("points", [])) < 2:
            raise ValueError(f"Unusable user seed: {event}")
        rows.append(
            {
                "schema": "R02_USER_CONFIRMED_MULTIBRACKET_SEED_V1",
                "run_id": "R02ZF",
                "batch_index": int(event["batch_index"]),
                "bracket_id": str(event["bracket_id"]),
                "seed_role": str(event["seed_role"]),
                "sar_frame_index": int(event["sar_frame_index"]),
                "sar_timestamp_ms": int(event["sar_timestamp_ms"]),
                "object_type": str(event["object_type"]),
                "object_id": str(event["object_id"]),
                "geometry_type": "polyline",
                "points": event["points"],
                "confidence_state": str(event["confidence_state"]),
                "derived_geometry_status": "USER_CONFIRMED_COMPLETE",
                "source_geometry_status": str(event["geometry_status"]),
                "source_event_id": str(event["event_id"]),
                "source_revision": int(event["revision"]),
                "recovery_basis": (
                    "EXPLICIT_USER_COMPLETION_CURRENT_TURN_WITH_POINT_RICH_POLYLINE"
                    if event["geometry_status"] == "DRAFT"
                    else "SOURCE_EVENT_COMPLETE"
                ),
                "manual_jsonl_modified": False,
                "curved_boundary_preserved_as_d_perp_of_theta": True,
            }
        )
    if len(rows) != 12:
        raise ValueError(f"Expected 12 normalized boundary seeds, observed {len(rows)}")
    return rows


def common_theta_grid(frozen, frame_events: dict[int, dict[str, dict[str, object]]], registry: pd.DataFrame) -> np.ndarray:
    extents: list[tuple[float, float]] = []
    for frame_index, objects in frame_events.items():
        row = registry.loc[frame_index]
        for object_type in BOUNDARY_TYPES:
            values = [frozen.point_to_theta_d(point, row)[0] for point in objects[object_type]["points"]]
            extents.append((min(values), max(values)))
    common_low = max(item[0] for item in extents) + 1.0
    common_high = min(item[1] for item in extents) - 1.0
    grid_low = math.ceil(common_low / frozen.THETA_STEP_DEG) * frozen.THETA_STEP_DEG
    grid_high = math.floor(common_high / frozen.THETA_STEP_DEG) * frozen.THETA_STEP_DEG
    theta = np.arange(grid_low, grid_high + 0.001, frozen.THETA_STEP_DEG, dtype=float)
    if len(theta) < 8:
        raise ValueError(f"Common theta corridor too narrow: {common_low} to {common_high}")
    return theta


def support_mask(frozen, evidence, registry: pd.DataFrame, frame_index: int, theta: np.ndarray, curve: np.ndarray) -> np.ndarray:
    row = registry.loc[frame_index]
    jet = evidence.jet(frame_index)
    center = frozen.sample_grid(jet, row, theta, curve[None, :])[0]
    closer = frozen.sample_grid(jet, row, theta, (curve - frozen.BACKGROUND_OFFSET_M)[None, :])[0]
    farther = frozen.sample_grid(jet, row, theta, (curve + frozen.BACKGROUND_OFFSET_M)[None, :])[0]
    contrast = center - np.maximum(closer, farther)
    return np.isfinite(contrast) & (contrast >= 0.002)


def overlap_rows(
    frozen,
    bracket_id: str,
    forward: dict[int, dict[str, np.ndarray]],
    backward: dict[int, dict[str, np.ndarray]],
    seed_frames: list[int],
    theta: np.ndarray,
    registry: pd.DataFrame,
    evidence,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    overlap = sorted(set(forward) & set(backward) - set(seed_frames))
    for frame_index in overlap:
        forward_order = forward[frame_index]["SAR_BOUNDARY_FAR"] - forward[frame_index]["SAR_BOUNDARY_NEAR"]
        backward_order = backward[frame_index]["SAR_BOUNDARY_FAR"] - backward[frame_index]["SAR_BOUNDARY_NEAR"]
        for object_type in BOUNDARY_TYPES:
            f_curve = forward[frame_index][object_type]
            b_curve = backward[frame_index][object_type]
            node_abs = np.abs(f_curve - b_curve)
            f_centered = f_curve - np.median(f_curve)
            b_centered = b_curve - np.median(b_curve)
            shape = f_centered - b_centered
            f_support = support_mask(frozen, evidence, registry, frame_index, theta, f_curve)
            b_support = support_mask(frozen, evidence, registry, frame_index, theta, b_curve)
            union = f_support | b_support
            intersection = f_support & b_support
            rows.append(
                {
                    "bracket_id": bracket_id,
                    "sar_frame_index": frame_index,
                    "sar_timestamp_ms": int(registry.loc[frame_index].sar_timestamp_ms),
                    "object_type": object_type,
                    "theta_node_count": len(theta),
                    "center_disagreement_m": float(abs(np.median(f_curve) - np.median(b_curve))),
                    "node_median_abs_disagreement_m": float(np.median(node_abs)),
                    "node_max_abs_disagreement_m": float(np.max(node_abs)),
                    "curve_shape_rms_disagreement_m": float(np.sqrt(np.mean(shape**2))),
                    "curve_shape_max_disagreement_m": float(np.max(np.abs(shape))),
                    "forward_order_positive_all_nodes": bool(np.all(forward_order > 0)),
                    "backward_order_positive_all_nodes": bool(np.all(backward_order > 0)),
                    "forward_support_fraction": float(np.mean(f_support)),
                    "backward_support_fraction": float(np.mean(b_support)),
                    "response_support_intersection_fraction": float(np.mean(intersection)),
                    "response_support_jaccard": float(np.sum(intersection) / np.sum(union)) if np.any(union) else 0.0,
                    "frozen_center_threshold_m": frozen.MAX_BIDIRECTIONAL_DISAGREEMENT_M,
                    "center_pass": bool(np.median(node_abs) <= frozen.MAX_BIDIRECTIONAL_DISAGREEMENT_M),
                    "shape_pass": bool(np.sqrt(np.mean(shape**2)) <= frozen.MAX_BIDIRECTIONAL_DISAGREEMENT_M),
                    "ordering_pass": bool(np.all(forward_order > 0) and np.all(backward_order > 0)),
                }
            )
    return rows


def path_records(
    frozen,
    bracket_id: str,
    direction: str,
    curves: dict[int, dict[str, np.ndarray]],
    theta: np.ndarray,
    registry: pd.DataFrame,
    seed_frames: list[int],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for frame_index in sorted(curves):
        row = registry.loc[frame_index]
        separation_nodes = curves[frame_index]["SAR_BOUNDARY_FAR"] - curves[frame_index]["SAR_BOUNDARY_NEAR"]
        for object_type in BOUNDARY_TYPES:
            curve = curves[frame_index][object_type]
            rows.append(
                {
                    "schema": "R02_MULTIBRACKET_DIRECTIONAL_PATH_V1",
                    "run_id": "R02ZF",
                    "bracket_id": bracket_id,
                    "direction": direction,
                    "sar_frame_index": frame_index,
                    "sar_timestamp_ms": int(row.sar_timestamp_ms),
                    "object_type": object_type,
                    "points": frozen.curve_to_points(theta, curve, row),
                    "theta_grid_deg": [float(value) for value in theta],
                    "d_curve_m": [round(float(value), 6) for value in curve],
                    "d_center_m": float(np.median(curve)),
                    "pair_separation_min_m": float(np.min(separation_nodes)),
                    "pair_separation_median_m": float(np.median(separation_nodes)),
                    "pair_separation_max_m": float(np.max(separation_nodes)),
                    "pair_order_positive_all_nodes": bool(np.all(separation_nodes > 0)),
                    "manual_seed_frame": frame_index in seed_frames,
                    "curved_boundary_preserved_as_d_perp_of_theta": True,
                    "person_gt": False,
                    "final_localization": False,
                }
            )
    return rows


def draw_dashed(image: np.ndarray, points: np.ndarray, color: tuple[int, int, int], thickness: int = 2) -> None:
    for start, end in zip(points[:-1], points[1:]):
        delta = end.astype(float) - start.astype(float)
        length = float(np.linalg.norm(delta))
        if length == 0:
            continue
        unit = delta / length
        position = 0.0
        while position < length:
            a = start.astype(float) + unit * position
            b = start.astype(float) + unit * min(position + 8.0, length)
            cv2.line(image, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), color, thickness, cv2.LINE_AA)
            position += 14.0


def render_overlap_review(
    frozen,
    bracket_id: str,
    forward: dict[int, dict[str, np.ndarray]],
    backward: dict[int, dict[str, np.ndarray]],
    theta: np.ndarray,
    registry: pd.DataFrame,
) -> None:
    overlap = sorted(set(forward) & set(backward))
    if len(overlap) > 12:
        selected = sorted(set(np.linspace(overlap[0], overlap[-1], 12).round().astype(int).tolist()))
        selected = [frame for frame in selected if frame in overlap]
    else:
        selected = overlap
    if not selected:
        canvas = np.full((420, 1200, 3), 245, dtype=np.uint8)
        cv2.putText(canvas, f"{bracket_id}: NO BIDIRECTIONAL OVERLAP", (80, 215), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (30, 30, 30), 2, cv2.LINE_AA)
        write_png(FIG / f"{bracket_id}_overlap_review.png", canvas)
        return
    panels: list[np.ndarray] = []
    colors = {
        ("FORWARD", "SAR_BOUNDARY_NEAR"): (255, 255, 0),
        ("BACKWARD", "SAR_BOUNDARY_NEAR"): (80, 210, 80),
        ("FORWARD", "SAR_BOUNDARY_FAR"): (0, 165, 255),
        ("BACKWARD", "SAR_BOUNDARY_FAR"): (220, 80, 220),
    }
    for frame_index in selected:
        row = registry.loc[frame_index]
        image = read_bgr(Path(str(row.sar_image_path)))
        for direction, path, dashed in (("FORWARD", forward, False), ("BACKWARD", backward, True)):
            for object_type in BOUNDARY_TYPES:
                points = np.round(np.array(frozen.curve_to_points(theta, path[frame_index][object_type], row))).astype(np.int32)
                if dashed:
                    draw_dashed(image, points, colors[(direction, object_type)])
                else:
                    cv2.polylines(image, [points], False, colors[(direction, object_type)], 2, cv2.LINE_AA)
        cv2.rectangle(image, (0, 0), (image.shape[1], 54), (14, 18, 22), -1)
        cv2.putText(image, f"{bracket_id} F{frame_index:03d} overlap", (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(image, "solid=forward  dashed=backward  cyan/green=near  orange/magenta=far", (12, 43), cv2.FONT_HERSHEY_SIMPLEX, 0.39, (225, 225, 225), 1, cv2.LINE_AA)
        panels.append(image)
    while len(panels) % 3:
        panels.append(np.full_like(panels[0], 245))
    contact = cv2.vconcat([cv2.hconcat(panels[index : index + 3]) for index in range(0, len(panels), 3)])
    write_png(FIG / f"{bracket_id}_overlap_review.png", contact)


def render_process_review(
    frozen,
    bracket_id: str,
    start: int,
    end: int,
    forward: dict[int, dict[str, np.ndarray]],
    backward: dict[int, dict[str, np.ndarray]],
    theta: np.ndarray,
    registry: pd.DataFrame,
    forward_stop: dict[str, object] | None,
    backward_stop: dict[str, object] | None,
    review_frames: list[int],
) -> None:
    selected = set(np.linspace(start, end, 5).round().astype(int).tolist())
    selected.update([start, end])
    selected.update(review_frames)
    for stop in (forward_stop, backward_stop):
        if stop:
            selected.add(int(stop["source_frame"]))
            selected.add(int(stop["destination_frame"]))
    selected = sorted(frame for frame in selected if start <= frame <= end)
    if len(selected) > 12:
        selected = sorted(selected, key=lambda frame: (frame not in {start, end, *review_frames}, frame))[:12]
        selected.sort()
    panels: list[np.ndarray] = []
    for frame_index in selected:
        row = registry.loc[frame_index]
        image = read_bgr(Path(str(row.sar_image_path)))
        for direction, path, dashed in (("F", forward, False), ("B", backward, True)):
            if frame_index not in path:
                continue
            for object_type, color in (("SAR_BOUNDARY_NEAR", (255, 255, 0)), ("SAR_BOUNDARY_FAR", (0, 165, 255))):
                points = np.round(np.array(frozen.curve_to_points(theta, path[frame_index][object_type], row))).astype(np.int32)
                if dashed:
                    draw_dashed(image, points, (80, 210, 80) if object_type.endswith("NEAR") else (220, 80, 220))
                else:
                    cv2.polylines(image, [points], False, color, 2, cv2.LINE_AA)
        tags = []
        if frame_index == start:
            tags.append("START")
        if frame_index == end:
            tags.append("END")
        if frame_index in review_frames:
            tags.append("REVIEW")
        cv2.rectangle(image, (0, 0), (image.shape[1], 42), (14, 18, 22), -1)
        cv2.putText(image, f"{bracket_id} F{frame_index:03d} {'/'.join(tags)}", (12, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 1, cv2.LINE_AA)
        panels.append(image)
    while len(panels) % 3:
        panels.append(np.full_like(panels[0], 245))
    contact = cv2.vconcat([cv2.hconcat(panels[index : index + 3]) for index in range(0, len(panels), 3)])
    write_png(FIG / f"{bracket_id}_process_review.png", contact)


def repair_row(frame_index: int, bracket_id: str, reason: str, registry: pd.DataFrame, optical: dict[int, tuple[int, Path]]) -> dict[str, object]:
    row = registry.loc[frame_index]
    optical_index = int(row.nominal_optical_frame_index)
    optical_timestamp, optical_path = optical[optical_index]
    residual = int(row.sar_timestamp_ms) - optical_timestamp
    return {
        "batch_index": 0,
        "run_id": "R02ZF",
        "bracket_id": bracket_id,
        "seed_role": "REPAIR",
        "optical_frame_index": optical_index,
        "optical_timestamp_ms": optical_timestamp,
        "optical_image_path": str(optical_path),
        "sar_frame_index": frame_index,
        "sar_timestamp_ms": int(row.sar_timestamp_ms),
        "sar_image_path": str(row.sar_image_path),
        "nominal_timestamp_residual_ms": residual,
        "sync_status": str(row.sync_status),
        "nearest_optical_frame": optical_index,
        "nearest_optical_timestamp_ms": optical_timestamp,
        "sync_residual_ms": residual,
        "selection_reason": reason,
        "visual_difficulty": "REVIEW_REQUIRED_BY_FROZEN_BIDIRECTIONAL_REPLICATION",
        "notes": "Minimal single-frame repair candidate; no automatic line is displayed.",
        "annotation_scope": "SAR_BOUNDARY_ONLY",
        "annotation_status": "PENDING",
        "automatic_hint_is_identity_authority": False,
        "person_gt": False,
    }


def output_manifest() -> None:
    paths = [
        NORMALIZED_SEEDS, DIRECTIONAL_PATHS, CLOSED_RECORDS, DIAGNOSTICS, OVERLAP_METRICS,
        REVIEW, REPAIR_BATCH, COMPARISON, SUMMARY, REPORT, PARAMETERS,
        *sorted(FIG.glob("*.png")),
    ]
    rows = []
    for path in paths:
        if path.exists():
            rows.append(
                {
                    "workspace_relative_path": path.relative_to(WORKSPACE).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "artifact_role": "R02_MULTIBRACKET_REPLICATION_OR_REVIEW",
                    "contains_raw_manual_event_log": False,
                }
            )
    pd.DataFrame(rows).to_csv(OUTPUT_MANIFEST, index=False, encoding="utf-8-sig")


def main() -> None:
    manual_hash_before = sha256(MANUAL_EVENTS)
    if manual_hash_before != EXPECTED_MANUAL_SHA256:
        raise RuntimeError(f"Unexpected manual JSONL hash: {manual_hash_before}")
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    (OUT / "repair_user_annotations").mkdir(parents=True, exist_ok=True)
    if any((OUT / "repair_user_annotations").iterdir()):
        raise RuntimeError("Repair annotation directory must be empty before propagation")

    frozen = load_module("r02_frozen_manual_seed_propagation", FROZEN_SCRIPT)
    registry = frozen.load_registry()
    transforms = frozen.load_p0_transforms()
    p1e = frozen.load_module("r02_multibracket_p1e", frozen.P1E_SCRIPT)
    evidence = frozen.EvidenceCache(registry, p1e)
    events, event_count = latest_seed_events()
    normalized = normalized_seed_rows(events)
    write_jsonl(NORMALIZED_SEEDS, normalized)

    batch = pd.read_csv(BATCH).sort_values("batch_index")
    by_batch_object = {(int(row["batch_index"]), str(row["object_type"])): row for row in normalized}
    directional_rows: list[dict[str, object]] = []
    diagnostic_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    review_rows: list[dict[str, object]] = []
    closed_rows: list[dict[str, object]] = []
    comparison_rows: list[dict[str, object]] = []
    repair_rows: list[dict[str, object]] = []
    bracket_summaries: dict[str, dict[str, object]] = {}

    optical: dict[int, tuple[int, Path]] = {}
    for path in OPTICAL_DIR.glob("*.jpg"):
        match = FILENAME_RE.match(path.name)
        if match:
            optical[int(match.group(1))] = (int(match.group(2)), path)

    for bracket_id, group in batch.groupby("bracket_id", sort=False):
        group = group.sort_values("batch_index")
        start = int(group.iloc[0].sar_frame_index)
        end = int(group.iloc[1].sar_frame_index)
        seed_frames = [start, end]
        frame_events: dict[int, dict[str, dict[str, object]]] = {}
        for batch_row in group.itertuples(index=False):
            frame_events[int(batch_row.sar_frame_index)] = {
                object_type: by_batch_object[(int(batch_row.batch_index), object_type)]
                for object_type in BOUNDARY_TYPES
            }
        theta = common_theta_grid(frozen, frame_events, registry)
        seed_curves = {
            frame_index: {
                object_type: frozen.manual_curve(frame_events[frame_index][object_type]["points"], registry.loc[frame_index], theta)
                for object_type in BOUNDARY_TYPES
            }
            for frame_index in seed_frames
        }
        seed_separations = [
            float(np.median(seed_curves[frame]["SAR_BOUNDARY_FAR"] - seed_curves[frame]["SAR_BOUNDARY_NEAR"]))
            for frame in seed_frames
        ]
        expected_separation = float(np.mean(seed_separations))
        forward, forward_diag, forward_stop = frozen.propagate_direction(
            start, end, seed_curves[start], expected_separation, theta, registry, transforms, evidence, f"{bracket_id}_FORWARD_FROM_START"
        )
        backward, backward_diag, backward_stop = frozen.propagate_direction(
            end, start, seed_curves[end], expected_separation, theta, registry, transforms, evidence, f"{bracket_id}_BACKWARD_FROM_END"
        )
        for row in forward_diag + backward_diag:
            diagnostic_rows.append({"bracket_id": bracket_id, **row})
        directional_rows.extend(path_records(frozen, bracket_id, "FORWARD_FROM_START", forward, theta, registry, seed_frames))
        directional_rows.extend(path_records(frozen, bracket_id, "BACKWARD_FROM_END", backward, theta, registry, seed_frames))
        metrics = overlap_rows(frozen, bracket_id, forward, backward, seed_frames, theta, registry, evidence)
        metric_rows.extend(metrics)
        overlap_frames = sorted(set(forward) & set(backward) - set(seed_frames))
        overlap_availability = (
            "AVAILABLE_BIDIRECTIONAL_OVERLAP"
            if overlap_frames
            else "UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP"
        )
        center_pass = all(bool(row["center_pass"]) for row in metrics) if metrics else None
        shape_pass = all(bool(row["shape_pass"]) for row in metrics) if metrics else None
        ordering_pass = all(bool(row["ordering_pass"]) for row in metrics) if metrics else None
        directional_ordering_pass = all(
            bool(np.all(curves[frame_index]["SAR_BOUNDARY_FAR"] - curves[frame_index]["SAR_BOUNDARY_NEAR"] > 0))
            for curves in (forward, backward)
            for frame_index in curves
        )
        closure_pass = bool(overlap_frames) and center_pass and shape_pass and ordering_pass
        closure_failure_reason = (
            None
            if closure_pass
            else "NO_BIDIRECTIONAL_OVERLAP"
            if not overlap_frames
            else "OVERLAP_CLOSURE_GATE_FAILED"
        )
        interval = set(range(start, end + 1))
        directional_coverage = sorted(set(forward) | set(backward))
        missing = sorted(interval - set(directional_coverage))
        failing_overlap = sorted(
            {
                int(row["sar_frame_index"])
                for row in metrics
                if not (bool(row["center_pass"]) and bool(row["shape_pass"]) and bool(row["ordering_pass"]))
            }
        )
        bracket_review = sorted(set(missing) | set(failing_overlap))
        for frame_index in missing:
            review_rows.append(
                {
                    "bracket_id": bracket_id,
                    "sar_frame_index": frame_index,
                    "sar_timestamp_ms": int(registry.loc[frame_index].sar_timestamp_ms),
                    "status": "REVIEW_REQUIRED",
                    "reason": "BIDIRECTIONAL_PATH_INCOMPLETE",
                    "required_action": "MINIMAL_MANUAL_REPAIR_SEED",
                }
            )
        for frame_index in failing_overlap:
            reasons = sorted(
                {
                    "CENTER_DISAGREEMENT" if not bool(row["center_pass"]) else ""
                    for row in metrics if int(row["sar_frame_index"]) == frame_index
                }
                | {
                    "CURVE_SHAPE_DISAGREEMENT" if not bool(row["shape_pass"]) else ""
                    for row in metrics if int(row["sar_frame_index"]) == frame_index
                }
                | {
                    "PAIR_ORDER_FAILURE" if not bool(row["ordering_pass"]) else ""
                    for row in metrics if int(row["sar_frame_index"]) == frame_index
                }
            )
            reasons = [reason for reason in reasons if reason]
            review_rows.append(
                {
                    "bracket_id": bracket_id,
                    "sar_frame_index": frame_index,
                    "sar_timestamp_ms": int(registry.loc[frame_index].sar_timestamp_ms),
                    "status": "REVIEW_REQUIRED",
                    "reason": "|".join(reasons),
                    "required_action": "MINIMAL_MANUAL_REPAIR_SEED",
                }
            )

        repair_frame: int | None = None
        repair_reason: str | None = None
        if not closure_pass:
            candidates = failing_overlap if failing_overlap else missing
            if candidates:
                midpoint = (min(candidates) + max(candidates)) / 2
                repair_frame = min(candidates, key=lambda frame: (abs(frame - midpoint), frame))
                repair_reason = "CURVE_SHAPE_OR_CLOSURE_REPAIR" if failing_overlap else "BIDIRECTIONAL_GAP_REPAIR"
            else:
                repair_frame = int(round((max(forward) + min(backward)) / 2))
                repair_reason = "NO_NATURAL_BIDIRECTIONAL_OVERLAP_REPAIR"
            repair_rows.append(repair_row(repair_frame, bracket_id, repair_reason, registry, optical))

        if closure_pass:
            for frame_index in range(start, end + 1):
                row = registry.loc[frame_index]
                if frame_index == start:
                    curves = seed_curves[start]
                    source = "MANUAL_START_SEED"
                elif frame_index == end:
                    curves = seed_curves[end]
                    source = "MANUAL_END_SEED"
                elif frame_index in forward and frame_index in backward:
                    curves = {object_type: (forward[frame_index][object_type] + backward[frame_index][object_type]) / 2 for object_type in BOUNDARY_TYPES}
                    source = "BIDIRECTIONAL_CLOSED_CONSENSUS"
                elif frame_index in forward:
                    curves = forward[frame_index]
                    source = "SUPPORTED_FORWARD"
                elif frame_index in backward:
                    curves = backward[frame_index]
                    source = "SUPPORTED_BACKWARD"
                else:
                    continue
                separation_nodes = curves["SAR_BOUNDARY_FAR"] - curves["SAR_BOUNDARY_NEAR"]
                for object_type in BOUNDARY_TYPES:
                    closed_rows.append(
                        {
                            "schema": "R02_MULTIBRACKET_CLOSED_BOUNDARY_V1",
                            "run_id": "R02ZF",
                            "bracket_id": bracket_id,
                            "sar_frame_index": frame_index,
                            "sar_timestamp_ms": int(row.sar_timestamp_ms),
                            "object_type": object_type,
                            "points": frozen.curve_to_points(theta, curves[object_type], row),
                            "theta_grid_deg": [float(value) for value in theta],
                            "d_curve_m": [round(float(value), 6) for value in curves[object_type]],
                            "d_center_m": float(np.median(curves[object_type])),
                            "pair_separation_min_m": float(np.min(separation_nodes)),
                            "pair_separation_median_m": float(np.median(separation_nodes)),
                            "pair_separation_max_m": float(np.max(separation_nodes)),
                            "pair_order_positive_all_nodes": bool(np.all(separation_nodes > 0)),
                            "source": source,
                            "manual_identity_authority": frame_index in seed_frames,
                            "curved_boundary_preserved_as_d_perp_of_theta": True,
                            "person_gt": False,
                            "final_localization": False,
                        }
                    )

        render_overlap_review(frozen, bracket_id, forward, backward, theta, registry)
        render_process_review(
            frozen,
            bracket_id,
            start,
            end,
            forward,
            backward,
            theta,
            registry,
            forward_stop,
            backward_stop,
            [repair_frame] if repair_frame is not None else [],
        )
        span = end - start + 1
        safe_auto_frames = len(set(directional_coverage) - set(seed_frames))
        closed_auto_frames = span - 2 if closure_pass else 0
        min_support_overlap = min((float(row["response_support_intersection_fraction"]) for row in metrics), default=None)
        max_center = max((float(row["center_disagreement_m"]) for row in metrics), default=None)
        max_shape_rms = max((float(row["curve_shape_rms_disagreement_m"]) for row in metrics), default=None)
        max_shape_node = max((float(row["curve_shape_max_disagreement_m"]) for row in metrics), default=None)
        summary_row = {
            "bracket_id": bracket_id,
            "start_frame": start,
            "end_frame": end,
            "frame_count": span,
            "manual_seed_frames": 2,
            "repair_seed_frames_required": 0 if closure_pass else 1,
            "manual_anchor_density_initial": 2 / span,
            "manual_anchor_density_with_proposed_repair": (2 + (0 if closure_pass else 1)) / span,
            "directional_supported_frame_count": len(directional_coverage),
            "safe_auto_propagated_frame_fraction_before_repair": safe_auto_frames / span,
            "closed_auto_propagated_frame_fraction": closed_auto_frames / span,
            "overlap_frame_count": len(overlap_frames),
            "overlap_frames": overlap_frames,
            "overlap_closure_availability": overlap_availability,
            "center_closure_pass": center_pass,
            "curve_shape_closure_pass": shape_pass,
            "near_far_ordering_pass": ordering_pass,
            "directional_near_far_ordering_pass": directional_ordering_pass,
            "response_support_min_intersection_fraction": min_support_overlap,
            "max_center_disagreement_m": max_center,
            "max_curve_shape_rms_disagreement_m": max_shape_rms,
            "max_curve_shape_node_disagreement_m": max_shape_node,
            "closed": closure_pass,
            "status": "CLOSED" if closure_pass else "BRACKET_NOT_CLOSED",
            "closure_failure_reason": closure_failure_reason,
            "forward_stop": forward_stop,
            "backward_stop": backward_stop,
            "review_required_frames": bracket_review,
            "proposed_repair_frame": repair_frame,
            "theta_corridor_deg": [float(theta.min()), float(theta.max())],
            "theta_node_count": len(theta),
            "manual_seed_pair_separations_m": seed_separations,
            "expected_pair_separation_m": expected_separation,
            "curved_boundary_preserved": True,
        }
        bracket_summaries[bracket_id] = summary_row
        comparison_rows.append(summary_row)

    comparator = json.loads(COMPARATOR_SUMMARY.read_text(encoding="utf-8"))
    comparison_rows.insert(
        0,
        {
            "bracket_id": "B0_FROZEN_COMPARATOR",
            "start_frame": 150,
            "end_frame": 183,
            "frame_count": 34,
            "manual_seed_frames": 2,
            "repair_seed_frames_required": 0,
            "manual_anchor_density_initial": 2 / 34,
            "manual_anchor_density_with_proposed_repair": 2 / 34,
            "directional_supported_frame_count": comparator["accepted_frame_count"],
            "safe_auto_propagated_frame_fraction_before_repair": 32 / 34,
            "closed_auto_propagated_frame_fraction": 32 / 34,
            "overlap_frame_count": len(comparator["bidirectional_overlap_frames"]),
            "overlap_frames": comparator["bidirectional_overlap_frames"],
            "overlap_closure_availability": "AVAILABLE_BIDIRECTIONAL_OVERLAP",
            "center_closure_pass": comparator["bidirectional_bridge_pass"],
            "curve_shape_closure_pass": "NOT_REPORTED_IN_ORIGINAL_COMPARATOR",
            "near_far_ordering_pass": True,
            "directional_near_far_ordering_pass": True,
            "response_support_min_intersection_fraction": "NOT_REPORTED_IN_ORIGINAL_COMPARATOR",
            "max_center_disagreement_m": max(item["overlap_max_disagreement_m"] for item in comparator["anchor_closure"].values()),
            "max_curve_shape_rms_disagreement_m": "NOT_REPORTED_IN_ORIGINAL_COMPARATOR",
            "max_curve_shape_node_disagreement_m": "NOT_REPORTED_IN_ORIGINAL_COMPARATOR",
            "closed": True,
            "status": "CLOSED",
            "closure_failure_reason": None,
            "forward_stop": comparator["forward_stop"],
            "backward_stop": comparator["backward_stop"],
            "review_required_frames": comparator["review_required_frames"],
            "proposed_repair_frame": None,
            "theta_corridor_deg": comparator["theta_corridor_deg"],
            "theta_node_count": comparator["theta_node_count"],
            "manual_seed_pair_separations_m": comparator["manual_seed_pair_separations_m"],
            "expected_pair_separation_m": comparator["expected_manual_pair_separation_m"],
            "curved_boundary_preserved": "ORIGINAL_COMPARATOR_SEMANTICS",
        },
    )

    write_jsonl(DIRECTIONAL_PATHS, directional_rows)
    write_jsonl(CLOSED_RECORDS, closed_rows)
    pd.DataFrame(diagnostic_rows).to_csv(DIAGNOSTICS, index=False, encoding="utf-8-sig")
    pd.DataFrame(metric_rows).to_csv(OVERLAP_METRICS, index=False, encoding="utf-8-sig")
    pd.DataFrame(review_rows, columns=["bracket_id", "sar_frame_index", "sar_timestamp_ms", "status", "reason", "required_action"]).to_csv(REVIEW, index=False, encoding="utf-8-sig")
    repair_fields = [
        "batch_index", "run_id", "bracket_id", "seed_role", "optical_frame_index", "optical_timestamp_ms", "optical_image_path",
        "sar_frame_index", "sar_timestamp_ms", "sar_image_path", "nominal_timestamp_residual_ms", "sync_status",
        "nearest_optical_frame", "nearest_optical_timestamp_ms", "sync_residual_ms", "selection_reason", "visual_difficulty",
        "notes", "annotation_scope", "annotation_status", "automatic_hint_is_identity_authority", "person_gt",
    ]
    for index, row in enumerate(repair_rows, start=1):
        row["batch_index"] = index
    with REPAIR_BATCH.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=repair_fields)
        writer.writeheader()
        writer.writerows(repair_rows)
    comparison_serializable = []
    for row in comparison_rows:
        flat = row.copy()
        for key in ["overlap_frames", "forward_stop", "backward_stop", "review_required_frames", "theta_corridor_deg", "manual_seed_pair_separations_m"]:
            flat[key] = json.dumps(flat[key], ensure_ascii=False, allow_nan=False)
        comparison_serializable.append(flat)
    pd.DataFrame(comparison_serializable).to_csv(COMPARISON, index=False, encoding="utf-8-sig")

    parameter_manifest = {
        "schema": "R02_FROZEN_MULTIBRACKET_PARAMETER_MANIFEST_V1",
        "source_script": str(FROZEN_SCRIPT),
        "source_script_sha256": sha256(FROZEN_SCRIPT),
        "search_offsets_m": [float(frozen.SEARCH_OFFSETS_M.min()), float(frozen.SEARCH_OFFSETS_M.max()), 0.01],
        "background_offset_m": frozen.BACKGROUND_OFFSET_M,
        "min_aggregate_contrast": frozen.MIN_AGGREGATE_CONTRAST,
        "min_node_support_fraction": frozen.MIN_NODE_SUPPORT_FRACTION,
        "max_local_offset_m": frozen.MAX_LOCAL_OFFSET_M,
        "distinct_candidate_distance_m": frozen.DISTINCT_CANDIDATE_DISTANCE_M,
        "ambiguous_second_ratio": frozen.AMBIGUOUS_SECOND_RATIO,
        "max_bidirectional_disagreement_m": frozen.MAX_BIDIRECTIONAL_DISAGREEMENT_M,
        "max_pair_separation_deviation_m": frozen.MAX_PAIR_SEPARATION_DEVIATION_M,
        "theta_step_deg": frozen.THETA_STEP_DEG,
        "parameter_tuning_for_new_brackets": False,
        "curve_shape_gate_uses_existing_max_bidirectional_disagreement_m": True,
        "response_support_overlap_is_reported_not_tuned_or_used_to_force_closure": True,
    }
    PARAMETERS.write_text(json.dumps(parameter_manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    summary = {
        "schema": "R02_MANUAL_BOUNDARY_MULTIBRACKET_REPLICATION_SUMMARY_V1",
        "generated_at": now_iso(),
        "status": "COMPLETE_WITH_REPAIR_REQUIRED" if repair_rows else "COMPLETE_ALL_CLOSED",
        "manual_event_path": str(MANUAL_EVENTS),
        "manual_event_line_count": event_count,
        "manual_event_sha256_before": manual_hash_before,
        "manual_event_sha256_after": sha256(MANUAL_EVENTS),
        "manual_jsonl_preserved": manual_hash_before == sha256(MANUAL_EVENTS),
        "normalized_seed_count": len(normalized),
        "initial_manual_seed_frames": 6,
        "total_new_bracket_frames": sum(int(row["frame_count"]) for row in bracket_summaries.values()),
        "initial_manual_anchor_density": 6 / sum(int(row["frame_count"]) for row in bracket_summaries.values()),
        "repair_seed_count_proposed": len(repair_rows),
        "brackets": bracket_summaries,
        "closed_brackets": [key for key, value in bracket_summaries.items() if value["closed"]],
        "not_closed_brackets": [key for key, value in bracket_summaries.items() if not value["closed"]],
        "closed_record_count": len(closed_rows),
        "review_required_frame_count": len(review_rows),
        "repair_batch_frame_count": len(repair_rows),
        "frozen_comparator": "B0_F150_F183_UNCHANGED",
        "curved_early_boundary_preserved_as_d_perp_of_theta": True,
        "fixed_range_windows_used": False,
        "parameter_tuning_for_new_brackets": False,
        "tree_correspondence_run": False,
        "person_experiment_run": False,
        "final_localization_run": False,
        "r04_accessed": False,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    report_lines = [
        "# R02 manual-boundary multi-bracket replication report",
        "",
        "## Boundary semantics",
        "",
        "- All endpoint polylines are retained as `d_perp(theta)` curves. Bracket A is not straightened: F047 is strongly curved while F082 is much flatter.",
        "- The raw append-only manual JSONL is unchanged. Point-rich near drafts are accepted only because the user explicitly stated that annotation was complete in this turn.",
        "- Propagation parameters are byte-for-byte sourced from the frozen F150-F183 implementation; no A/B/C outcome-driven threshold changes were made.",
        "",
        "## Results",
        "",
        "| Bracket | Frames | Directional coverage | Overlap | Center | Shape | Overlap order | Directional order | Final | Repair |",
        "|---|---:|---:|---:|---|---|---|---|---|---:|",
    ]
    for bracket_id, result in bracket_summaries.items():
        report_lines.append(
            f"| {bracket_id} | {result['frame_count']} | {result['directional_supported_frame_count']} | {result['overlap_frame_count']} | {closure_gate_label(result['center_closure_pass'], result['overlap_closure_availability'])} | {closure_gate_label(result['curve_shape_closure_pass'], result['overlap_closure_availability'])} | {closure_gate_label(result['near_far_ordering_pass'], result['overlap_closure_availability'])} | {result['directional_near_far_ordering_pass']} | {result['status']} | {result['proposed_repair_frame'] or '-'} |"
        )
    report_lines.extend(
        [
            "",
            "## Manual effort",
            "",
            f"- Initial manual anchor density: 6 / {summary['total_new_bracket_frames']} = {summary['initial_manual_anchor_density']:.4f}.",
            f"- Proposed minimal repair seeds: {len(repair_rows)}.",
            "- Auto-propagated fractions are reported separately for directional support and fully closed coverage in `BRACKET_COMPARISON.csv`.",
            "- A missing bidirectional overlap is recorded as unavailable closure evidence, not as a failed center/shape/order comparison. Directional near/far ordering is reported separately.",
            "",
            "## Explicit non-claims",
            "",
            "These results concern conditional SAR image-domain maintenance of user-defined static boundaries. They do not establish physical calibration, PERSON range, PERSON grounding, identity, final boxes, or full-stream propagation.",
        ]
    )
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    output_manifest()
    if sha256(MANUAL_EVENTS) != manual_hash_before:
        raise RuntimeError("Manual JSONL changed during propagation")
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
