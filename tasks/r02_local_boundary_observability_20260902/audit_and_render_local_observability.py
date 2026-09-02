from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "r02_local_boundary_observability_20260902"
OUT = WORKSPACE / "output" / "r02_local_boundary_observability_20260902"
PRE = OUT / "pre_reference"
POST = OUT / "post_freeze_audit"
FIG = OUT / "figures"
FREEZE = OUT / "PRE_REFERENCE_FREEZE_MANIFEST.json"
FROZEN_SCRIPT = (
    WORKSPACE
    / "tasks"
    / "r02_manual_seed_temporal_propagation_20260902"
    / "run_manual_seed_temporal_propagation.py"
)
MANUAL_SOURCES = [
    WORKSPACE
    / "output"
    / "r02_manual_static_scene_anchor_preparation_20260902"
    / "user_annotations"
    / "manual_static_scene_annotations.jsonl",
    WORKSPACE
    / "output"
    / "r02_boundary_multibracket_preparation_20260902"
    / "user_annotations"
    / "manual_static_scene_annotations.jsonl",
    WORKSPACE
    / "output"
    / "r02_boundary_multibracket_replication_20260902"
    / "repair_user_annotations"
    / "manual_static_scene_annotations.jsonl",
]
PRIMARY_SEEDS = [62, 150, 183, 264, 454]
BOUNDARIES = ["SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"]
COLORS = {
    "SAR_BOUNDARY_NEAR": (255, 255, 0),
    "SAR_BOUNDARY_FAR": (0, 165, 255),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_freeze() -> dict[str, object]:
    manifest = json.loads(FREEZE.read_text(encoding="utf-8"))
    mismatches = []
    for item in manifest["files"]:
        path = WORKSPACE / item["workspace_relative_path"]
        current = sha256(path) if path.is_file() else None
        if current != item["sha256"]:
            mismatches.append({"path": str(path), "expected": item["sha256"], "observed": current})
    if mismatches:
        raise RuntimeError(f"Pre-reference freeze mismatch: {mismatches}")
    return manifest


def manual_inventory() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    latest: dict[tuple[int, str], tuple[dict[str, object], Path]] = {}
    sources = []
    for path in MANUAL_SOURCES:
        raw = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        sources.append({"path": str(path), "event_count": len(raw), "sha256": sha256(path)})
        local_latest = {}
        for event in raw:
            if event.get("modality") == "SAR" and event.get("object_type") in BOUNDARIES:
                local_latest[(int(event["sar_frame_index"]), str(event["object_type"]))] = event
        for key, event in local_latest.items():
            if event.get("event_type") == "DELETE" or len(event.get("points", [])) < 2:
                continue
            if key in latest:
                raise RuntimeError(f"Duplicate checkpoint: {key}")
            latest[key] = (event, path)
    rows = []
    for (frame_index, object_type), (event, path) in sorted(latest.items()):
        rows.append(
            {
                "schema": "R02_POST_FREEZE_MANUAL_SEMANTIC_CHECKPOINT_V1",
                "sar_frame_index": frame_index,
                "sar_timestamp_ms": int(event["sar_timestamp_ms"]),
                "object_type": object_type,
                "points": event["points"],
                "point_count": len(event["points"]),
                "confidence_state": str(event["confidence_state"]),
                "source_geometry_status": str(event["geometry_status"]),
                "user_confirmed_semantic_checkpoint": True,
                "source_event_id": str(event["event_id"]),
                "source_revision": int(event["revision"]),
                "source_path": str(path),
                "source_sha256": sha256(path),
                "primary_seed": frame_index in PRIMARY_SEEDS,
                "revealed_after_pre_reference_freeze": True,
            }
        )
    return rows, sources


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def curve_metrics(
    frozen,
    propagated: dict[str, object],
    manual: dict[str, object],
    registry: pd.DataFrame,
) -> dict[str, object]:
    theta = np.asarray(propagated["theta_grid_deg"], dtype=float)
    curve = np.asarray(propagated["d_curve_m"], dtype=float)
    row = registry.loc[int(propagated["sar_frame_index"])]
    converted = [frozen.point_to_theta_d(point, row) for point in manual["points"]]
    manual_theta = np.asarray([item[0] for item in converted], dtype=float)
    valid = (theta >= manual_theta.min()) & (theta <= manual_theta.max())
    if valid.sum() < 3:
        return {
            "available": False,
            "reason": "LESS_THAN_THREE_COMMON_THETA_NODES",
            "common_theta_node_count": int(valid.sum()),
        }
    manual_curve = frozen.manual_curve(manual["points"], row, theta)
    auto = curve[valid]
    reference = manual_curve[valid]
    delta = auto - reference
    auto_shape = auto - np.median(auto)
    manual_shape = reference - np.median(reference)
    shape_delta = auto_shape - manual_shape
    return {
        "available": True,
        "common_theta_node_count": int(valid.sum()),
        "theta_min_deg": float(theta[valid].min()),
        "theta_max_deg": float(theta[valid].max()),
        "center_abs_disagreement_m": float(abs(np.median(auto) - np.median(reference))),
        "node_median_abs_disagreement_m": float(np.median(np.abs(delta))),
        "node_max_abs_disagreement_m": float(np.max(np.abs(delta))),
        "translation_removed_shape_rms_m": float(np.sqrt(np.mean(shape_delta**2))),
        "translation_removed_shape_max_m": float(np.max(np.abs(shape_delta))),
        "frozen_0p12_center_and_shape_pass": bool(
            np.median(np.abs(delta)) <= frozen.MAX_BIDIRECTIONAL_DISAGREEMENT_M
            and np.sqrt(np.mean(shape_delta**2)) <= frozen.MAX_BIDIRECTIONAL_DISAGREEMENT_M
        ),
    }


def pair_path_lookup(pair_rows: list[dict[str, object]]) -> dict[tuple[int, str, int, str], dict[str, object]]:
    return {
        (int(row["seed_frame"]), str(row["direction"]), int(row["sar_frame_index"]), str(row["object_type"])): row
        for row in pair_rows
    }


def draw_path(image: np.ndarray, record: dict[str, object], color: tuple[int, int, int], thickness: int, dashed: bool = False) -> None:
    points = np.round(np.asarray(record["points"], dtype=float)).astype(int)
    if not dashed:
        cv2.polylines(image, [points], False, color, thickness, cv2.LINE_AA)
        return
    for start, end in zip(points[:-1], points[1:]):
        delta = end.astype(float) - start.astype(float)
        length = float(np.linalg.norm(delta))
        if length <= 0:
            continue
        unit = delta / length
        position = 0.0
        while position < length:
            a = start.astype(float) + unit * position
            b = start.astype(float) + unit * min(position + 7.0, length)
            cv2.line(image, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), color, thickness, cv2.LINE_AA)
            position += 13.0


def label_panel(image: np.ndarray, title: str, subtitle: str = "") -> np.ndarray:
    cv2.rectangle(image, (0, 0), (image.shape[1], 54), (16, 18, 22), -1)
    cv2.putText(image, title, (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.53, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(image, subtitle, (12, 43), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (225, 225, 225), 1, cv2.LINE_AA)
    return image


def write_png(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError(path)
    encoded.tofile(path)


def render_timeline(
    pair_rows: list[dict[str, object]],
    individual_rows: list[dict[str, object]],
    segments: pd.DataFrame,
    stops: list[dict[str, object]],
    checkpoint_frames: list[int],
) -> None:
    run_rows = [(seed, direction) for seed in PRIMARY_SEEDS for direction in ("BACKWARD", "FORWARD")]
    fig, ax = plt.subplots(figsize=(18, 8.5))
    for index, (seed, direction) in enumerate(run_rows):
        y = len(run_rows) - index
        pair_frames = sorted(
            {
                int(row["sar_frame_index"])
                for row in pair_rows
                if int(row["seed_frame"]) == seed and row["direction"] == direction
            }
        )
        near_frames = sorted(
            {
                int(row["sar_frame_index"])
                for row in individual_rows
                if int(row["seed_frame"]) == seed
                and row["direction"] == direction
                and row["object_type"] == "SAR_BOUNDARY_NEAR"
            }
        )
        far_frames = sorted(
            {
                int(row["sar_frame_index"])
                for row in individual_rows
                if int(row["seed_frame"]) == seed
                and row["direction"] == direction
                and row["object_type"] == "SAR_BOUNDARY_FAR"
            }
        )
        if pair_frames:
            ax.plot([min(pair_frames), max(pair_frames)], [y, y], color="#1b9e77", lw=8, solid_capstyle="butt")
        if near_frames:
            ax.plot([min(near_frames), max(near_frames)], [y + 0.18, y + 0.18], color="#00bcd4", lw=2)
        if far_frames:
            ax.plot([min(far_frames), max(far_frames)], [y - 0.18, y - 0.18], color="#ff9800", lw=2)
        ax.scatter([seed], [y], marker="D", s=38, color="black", zorder=5)
        matching_stops = [
            item for item in stops
            if int(item["seed_frame"]) == seed
            and item["path_kind"] == "PAIR_SAFE_FROZEN"
            and direction in str(item["direction"])
        ]
        for stop in matching_stops:
            ax.scatter([int(stop["destination_frame"])], [y], marker="x", s=55, color="red", zorder=6)
    for frame in checkpoint_frames:
        ax.axvline(frame, color="#777777", lw=0.55, alpha=0.35)
        ax.text(frame, len(run_rows) + 0.8, f"F{frame}", rotation=90, va="bottom", ha="center", fontsize=7)
    labels = [f"F{seed} {direction[0]}" for seed, direction in run_rows]
    ax.set_yticks(range(1, len(run_rows) + 1), labels[::-1])
    ax.set_xlim(0, 494)
    ax.set_ylim(0.3, len(run_rows) + 1.7)
    ax.set_xlabel("R02ZF SAR frame")
    ax.set_title("R02 local boundary observability: green=pair-safe, cyan=near diagnostic, orange=far diagnostic, red x=natural stop")
    ax.grid(axis="x", alpha=0.15)
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "R02_LOCAL_BOUNDARY_OBSERVABILITY_TIMELINE.png", dpi=170)
    plt.close(fig)


def select_review_frames(seed: int, summary: dict[str, object], checkpoint_frames: list[int]) -> list[int]:
    pair_segments = [row for row in summary["segments"] if row["path_kind"] == "PAIR_SAFE_FROZEN"]
    selected = {seed}
    for segment in pair_segments:
        start = int(segment["start_frame"])
        end = int(segment["end_frame"])
        selected.update({start, end, int(round((start + end) / 2))})
        selected.update(frame for frame in checkpoint_frames if start <= frame <= end and frame != seed)
        stop = segment["natural_stop"]
        if stop:
            selected.add(int(stop["destination_frame"]))
    return sorted(frame for frame in selected if 0 <= frame <= 494)


def render_seed_reviews(
    frozen,
    registry: pd.DataFrame,
    pair_rows: list[dict[str, object]],
    manual_by_key: dict[tuple[int, str], dict[str, object]],
) -> list[dict[str, object]]:
    cases = []
    lookup = pair_path_lookup(pair_rows)
    checkpoint_frames = sorted({frame for frame, _ in manual_by_key})
    for seed in PRIMARY_SEEDS:
        summary = json.loads((PRE / "runs" / f"F{seed:03d}" / "RUN_SUMMARY.json").read_text(encoding="utf-8"))
        frames = select_review_frames(seed, summary, checkpoint_frames)
        panels = []
        for frame in frames:
            image = frozen.read_bgr(Path(str(registry.loc[frame].sar_image_path)))
            directions = [direction for direction in ("BACKWARD", "FORWARD") if (seed, direction, frame, "SAR_BOUNDARY_NEAR") in lookup]
            for direction_index, direction in enumerate(directions):
                for object_type in BOUNDARIES:
                    record = lookup[(seed, direction, frame, object_type)]
                    draw_path(image, record, COLORS[object_type], 2, dashed=direction_index > 0)
            manual_here = frame != seed and all((frame, object_type) in manual_by_key for object_type in BOUNDARIES)
            if manual_here:
                for object_type in BOUNDARIES:
                    event = manual_by_key[(frame, object_type)]
                    manual_record = {"points": event["points"]}
                    draw_path(image, manual_record, (255, 255, 255), 1, dashed=True)
            state = "PAIR_SUPPORTED" if directions else "STOP/UNKNOWN"
            subtitle = f"{state}; white dashed=post-freeze manual checkpoint" if manual_here else state
            panels.append(label_panel(image, f"Seed F{seed:03d} review F{frame:03d}", subtitle))
            cases.append({"figure": f"F{seed:03d}_process_review.png", "seed_frame": seed, "sar_frame_index": frame, "case_role": state, "visual_verdict": "PENDING"})
        width = 3
        while len(panels) % width:
            panels.append(np.zeros_like(panels[0]))
        rows = [np.hstack(panels[index:index + width]) for index in range(0, len(panels), width)]
        write_png(FIG / f"F{seed:03d}_process_review.png", np.vstack(rows))
    return cases


def render_checkpoint_comparisons(
    frozen,
    registry: pd.DataFrame,
    pair_rows: list[dict[str, object]],
    manual_by_key: dict[tuple[int, str], dict[str, object]],
    checkpoint_pair_rows: list[dict[str, object]],
) -> None:
    lookup = pair_path_lookup(pair_rows)
    panels = []
    for audit in checkpoint_pair_rows:
        seed = int(audit["seed_frame"])
        direction = str(audit["direction"])
        frame = int(audit["checkpoint_frame"])
        image = frozen.read_bgr(Path(str(registry.loc[frame].sar_image_path)))
        for object_type in BOUNDARIES:
            draw_path(image, lookup[(seed, direction, frame, object_type)], COLORS[object_type], 2)
            draw_path(image, {"points": manual_by_key[(frame, object_type)]["points"]}, (255, 255, 255), 1, dashed=True)
        verdict = "NUMERIC_PASS" if audit["both_boundary_frozen_0p12_pass"] else "NUMERIC_MISMATCH"
        subtitle = f"{verdict}; max median={audit['max_node_median_abs_disagreement_m']:.3f}m; white dashed=manual"
        panels.append(label_panel(image, f"Seed F{seed} {direction} at checkpoint F{frame}", subtitle))
    while len(panels) % 2:
        panels.append(np.zeros_like(panels[0]))
    rows = [np.hstack(panels[index:index + 2]) for index in range(0, len(panels), 2)]
    write_png(FIG / "CHECKPOINT_COMPARISON_ATLAS.png", np.vstack(rows))


def render_f66_conflict(
    frozen,
    registry: pd.DataFrame,
    pair_rows: list[dict[str, object]],
) -> None:
    lookup = pair_path_lookup(pair_rows)
    frame = 66
    panels = []
    cases = [
        (62, "FORWARD", "F062-forward close seed: curved state"),
        (150, "BACKWARD", "F150-backward stable seed: rigid straight state"),
    ]
    for seed, direction, title in cases:
        image = frozen.read_bgr(Path(str(registry.loc[frame].sar_image_path)))
        for object_type in BOUNDARIES:
            draw_path(image, lookup[(seed, direction, frame, object_type)], COLORS[object_type], 3)
        panels.append(label_panel(image, f"F066 {title}", "Both paths label F066 pair-safe, but their curve shapes disagree"))
    combined = frozen.read_bgr(Path(str(registry.loc[frame].sar_image_path)))
    first_colors = {"SAR_BOUNDARY_NEAR": (255, 255, 0), "SAR_BOUNDARY_FAR": (0, 165, 255)}
    second_colors = {"SAR_BOUNDARY_NEAR": (255, 0, 255), "SAR_BOUNDARY_FAR": (0, 255, 0)}
    for object_type in BOUNDARIES:
        draw_path(combined, lookup[(62, "FORWARD", frame, object_type)], first_colors[object_type], 3)
        draw_path(combined, lookup[(150, "BACKWARD", frame, object_type)], second_colors[object_type], 2, dashed=True)
    panels.append(label_panel(combined, "F066 direct conflict", "solid=F062 path; dashed=F150 path; numerical overlap audit fails"))
    write_png(FIG / "F066_NATURAL_OVERLAP_SHAPE_CONFLICT.png", np.hstack(panels))


def render_entrance(
    frozen,
    registry: pd.DataFrame,
    pair_rows: list[dict[str, object]],
    individual_rows: list[dict[str, object]],
) -> None:
    pair_lookup = pair_path_lookup(pair_rows)
    individual_lookup = {
        (int(row["seed_frame"]), str(row["direction"]), int(row["sar_frame_index"]), str(row["object_type"])): row
        for row in individual_rows
    }
    panels = []
    for frame in range(57, 69):
        image = frozen.read_bgr(Path(str(registry.loc[frame].sar_image_path)))
        pair_directions = [direction for direction in ("BACKWARD", "FORWARD") if (62, direction, frame, "SAR_BOUNDARY_NEAR") in pair_lookup]
        if pair_directions:
            direction = pair_directions[0]
            for object_type in BOUNDARIES:
                draw_path(image, pair_lookup[(62, direction, frame, object_type)], COLORS[object_type], 2)
            state = "PAIR_SAFE_SUPPORTED"
        else:
            supported = []
            for direction in ("BACKWARD", "FORWARD"):
                for object_type in BOUNDARIES:
                    key = (62, direction, frame, object_type)
                    if key in individual_lookup:
                        draw_path(image, individual_lookup[key], COLORS[object_type], 1, dashed=True)
                        supported.append(object_type.replace("SAR_BOUNDARY_", ""))
            state = "DIAGNOSTIC_" + "+".join(sorted(set(supported))) if supported else "UNKNOWN"
        panels.append(label_panel(image, f"Entrance F{frame:03d}", state))
    rows = [np.hstack(panels[index:index + 4]) for index in range(0, len(panels), 4)]
    write_png(FIG / "ENTRANCE_F057_F068_CURVE_EVOLUTION.png", np.vstack(rows))


def render_stop_atlas(
    frozen,
    registry: pd.DataFrame,
    pair_rows: list[dict[str, object]],
    stops: list[dict[str, object]],
) -> list[dict[str, object]]:
    lookup = pair_path_lookup(pair_rows)
    selected = []
    seen = set()
    for stop in stops:
        if stop["path_kind"] != "PAIR_SAFE_FROZEN":
            continue
        normalized = tuple(sorted(reason.split(":")[-1] for reason in stop["reasons"]))
        if normalized not in seen:
            seen.add(normalized)
            selected.append(stop)
    panels = []
    cases = []
    for stop in selected:
        seed = int(stop["seed_frame"])
        direction = "BACKWARD" if "BACKWARD" in stop["direction"] else "FORWARD"
        source = int(stop["source_frame"])
        destination = int(stop["destination_frame"])
        reasons = ";".join(stop["reasons"])
        source_image = frozen.read_bgr(Path(str(registry.loc[source].sar_image_path)))
        for object_type in BOUNDARIES:
            record = lookup.get((seed, direction, source, object_type))
            if record:
                draw_path(source_image, record, COLORS[object_type], 2)
        destination_image = frozen.read_bgr(Path(str(registry.loc[destination].sar_image_path)))
        panels.append(label_panel(source_image, f"F{seed} {direction} last supported F{source}", reasons[:95]))
        panels.append(label_panel(destination_image, f"Natural stop / UNKNOWN F{destination}", reasons[:95]))
        cases.append({"figure": "STOP_REASON_ATLAS.png", "seed_frame": seed, "sar_frame_index": destination, "case_role": reasons, "visual_verdict": "PENDING"})
    rows = [np.hstack(panels[index:index + 2]) for index in range(0, len(panels), 2)]
    write_png(FIG / "STOP_REASON_ATLAS.png", np.vstack(rows))
    return cases


def main() -> None:
    freeze_manifest = verify_freeze()
    POST.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    manual_rows, manual_sources = manual_inventory()
    write_jsonl(POST / "MANUAL_SEMANTIC_CHECKPOINT_INVENTORY.jsonl", manual_rows)
    manual_by_key = {(int(row["sar_frame_index"]), str(row["object_type"])): row for row in manual_rows}
    pair_rows = read_jsonl(PRE / "ALL_PAIR_SAFE_PATHS.jsonl")
    individual_rows = read_jsonl(PRE / "ALL_BOUNDARY_INDEPENDENT_PATHS.jsonl")
    segments = pd.read_csv(PRE / "LOCAL_SEGMENTS.csv")
    stops = json.loads((PRE / "STOP_EVENTS.json").read_text(encoding="utf-8"))
    frozen = load_module("r02_frozen_post_freeze_audit", FROZEN_SCRIPT)
    registry = frozen.load_registry()

    checkpoint_audit = []
    for propagated in pair_rows:
        frame = int(propagated["sar_frame_index"])
        object_type = str(propagated["object_type"])
        seed = int(propagated["seed_frame"])
        if frame == seed or (frame, object_type) not in manual_by_key:
            continue
        metrics = curve_metrics(frozen, propagated, manual_by_key[(frame, object_type)], registry)
        checkpoint_audit.append(
            {
                "seed_frame": seed,
                "direction": propagated["direction"],
                "checkpoint_frame": frame,
                "object_type": object_type,
                **metrics,
            }
        )
    pd.DataFrame(checkpoint_audit).to_csv(POST / "CHECKPOINT_GEOMETRY_AUDIT.csv", index=False, encoding="utf-8-sig")

    checkpoint_pair_rows = []
    if checkpoint_audit:
        table = pd.DataFrame(checkpoint_audit)
        for keys, group in table.groupby(["seed_frame", "direction", "checkpoint_frame"], sort=True):
            available = bool(group.available.all())
            pair_pass = bool(available and group.frozen_0p12_center_and_shape_pass.all())
            checkpoint_pair_rows.append(
                {
                    "seed_frame": int(keys[0]),
                    "direction": str(keys[1]),
                    "checkpoint_frame": int(keys[2]),
                    "boundary_count": len(group),
                    "both_boundary_metrics_available": available,
                    "both_boundary_frozen_0p12_pass": pair_pass,
                    "max_node_median_abs_disagreement_m": float(group.node_median_abs_disagreement_m.max()) if available else None,
                    "max_node_max_abs_disagreement_m": float(group.node_max_abs_disagreement_m.max()) if available else None,
                    "max_shape_rms_m": float(group.translation_removed_shape_rms_m.max()) if available else None,
                }
            )
    pd.DataFrame(checkpoint_pair_rows).to_csv(POST / "CHECKPOINT_PAIR_AUDIT.csv", index=False, encoding="utf-8-sig")

    pair_lookup = pair_path_lookup(pair_rows)
    run_keys = sorted({(int(row["seed_frame"]), str(row["direction"])) for row in pair_rows})
    overlap_rows = []
    for first_index, first in enumerate(run_keys):
        for second in run_keys[first_index + 1:]:
            if first[0] == second[0]:
                continue
            first_frames = {key[2] for key in pair_lookup if key[0] == first[0] and key[1] == first[1]}
            second_frames = {key[2] for key in pair_lookup if key[0] == second[0] and key[1] == second[1]}
            common_frames = sorted(first_frames & second_frames)
            if not common_frames:
                continue
            metric_values = []
            for frame in common_frames:
                for object_type in BOUNDARIES:
                    a = pair_lookup[(first[0], first[1], frame, object_type)]
                    b = pair_lookup[(second[0], second[1], frame, object_type)]
                    theta_a = np.asarray(a["theta_grid_deg"], dtype=float)
                    theta_b = np.asarray(b["theta_grid_deg"], dtype=float)
                    low = max(theta_a.min(), theta_b.min())
                    high = min(theta_a.max(), theta_b.max())
                    common_theta = theta_a[(theta_a >= low) & (theta_a <= high)]
                    if len(common_theta) < 3:
                        continue
                    curve_a = np.interp(common_theta, theta_a, np.asarray(a["d_curve_m"], dtype=float))
                    curve_b = np.interp(common_theta, theta_b, np.asarray(b["d_curve_m"], dtype=float))
                    delta = curve_a - curve_b
                    shape = (curve_a - np.median(curve_a)) - (curve_b - np.median(curve_b))
                    metric_values.append(
                        {
                            "frame": frame,
                            "object_type": object_type,
                            "node_median": float(np.median(np.abs(delta))),
                            "node_max": float(np.max(np.abs(delta))),
                            "shape_rms": float(np.sqrt(np.mean(shape**2))),
                        }
                    )
            if metric_values:
                overlap_rows.append(
                    {
                        "first_seed": first[0],
                        "first_direction": first[1],
                        "second_seed": second[0],
                        "second_direction": second[1],
                        "overlap_start": min(common_frames),
                        "overlap_end": max(common_frames),
                        "overlap_frame_count": len(common_frames),
                        "max_node_median_disagreement_m": max(item["node_median"] for item in metric_values),
                        "max_node_disagreement_m": max(item["node_max"] for item in metric_values),
                        "max_shape_rms_m": max(item["shape_rms"] for item in metric_values),
                        "frozen_0p12_consistent": all(
                            item["node_median"] <= frozen.MAX_BIDIRECTIONAL_DISAGREEMENT_M
                            and item["shape_rms"] <= frozen.MAX_BIDIRECTIONAL_DISAGREEMENT_M
                            for item in metric_values
                        ),
                    }
                )
    pd.DataFrame(overlap_rows).to_csv(POST / "NATURAL_SEGMENT_OVERLAP_AUDIT.csv", index=False, encoding="utf-8-sig")

    checkpoint_frames = sorted({int(row["sar_frame_index"]) for row in manual_rows})
    render_timeline(pair_rows, individual_rows, segments, stops, checkpoint_frames)
    visual_cases = render_seed_reviews(frozen, registry, pair_rows, manual_by_key)
    render_entrance(frozen, registry, pair_rows, individual_rows)
    visual_cases.extend(render_stop_atlas(frozen, registry, pair_rows, stops))
    render_checkpoint_comparisons(frozen, registry, pair_rows, manual_by_key, checkpoint_pair_rows)
    render_f66_conflict(frozen, registry, pair_rows)
    pd.DataFrame(visual_cases).to_csv(POST / "VISUAL_REVIEW_CASES.csv", index=False, encoding="utf-8-sig")

    pre_summary = json.loads((PRE / "PRE_REFERENCE_SUMMARY.json").read_text(encoding="utf-8"))
    pair_audit_pass = sum(bool(row["both_boundary_frozen_0p12_pass"]) for row in checkpoint_pair_rows)
    pair_audit_fail = sum(not bool(row["both_boundary_frozen_0p12_pass"]) for row in checkpoint_pair_rows)
    strongest_disagreement = max(
        checkpoint_pair_rows,
        key=lambda row: row["max_node_median_abs_disagreement_m"] if row["max_node_median_abs_disagreement_m"] is not None else -1,
        default=None,
    )
    stop_reason_counts: dict[str, int] = {}
    for stop in stops:
        if stop["path_kind"] != "PAIR_SAFE_FROZEN":
            continue
        for reason in stop["reasons"]:
            key = reason.split(":")[-1]
            stop_reason_counts[key] = stop_reason_counts.get(key, 0) + 1
    summary = {
        "schema": "R02_LOCAL_BOUNDARY_OBSERVABILITY_COMPUTED_AUDIT_V1",
        "pre_reference_freeze_manifest_sha256": sha256(FREEZE),
        "pre_reference_file_count": freeze_manifest["file_count"],
        "manual_source_files": manual_sources,
        "actual_manual_checkpoint_frame_count": len(checkpoint_frames),
        "actual_manual_checkpoint_frames": checkpoint_frames,
        "actual_manual_boundary_record_count": len(manual_rows),
        "primary_seed_frame_count": len(PRIMARY_SEEDS),
        "primary_seed_frames": PRIMARY_SEEDS,
        "checkpoint_crossing_audit_count": len(checkpoint_pair_rows),
        "checkpoint_geometry_consistent_count": pair_audit_pass,
        "checkpoint_geometry_inconsistent_count": pair_audit_fail,
        "strongest_checkpoint_disagreement": strongest_disagreement,
        "natural_overlap_audit_count": len(overlap_rows),
        "natural_overlap_consistent_count": sum(bool(row["frozen_0p12_consistent"]) for row in overlap_rows),
        "natural_overlap_inconsistent_count": sum(not bool(row["frozen_0p12_consistent"]) for row in overlap_rows),
        "stop_reason_distribution_pair_safe": stop_reason_counts,
        "representation": {
            "state": "D_PERP_THETA_CURVE_SAMPLED_AT_NODES",
            "per_frame_update": "ONE_RIGID_SCALAR_SHIFT_FOR_ALL_NODES",
            "curve_shape_can_change_within_path": False,
            "nodes_independently_updated": False,
            "center_correct_does_not_prove_curve_correct": True,
        },
        "pre_reference_metrics": pre_summary,
        "visual_review_status": "PENDING_MANUAL_IMAGE_REVIEW",
        "semantic_switch_error_count": None,
        "optional_scene_context_qualification": "PENDING_VISUAL_REVIEW",
        "r04_accessed": False,
        "person_experiment_run": False,
        "tree_experiment_run": False,
        "final_localization_run": False,
    }
    write_json(POST / "COMPUTED_AUDIT_SUMMARY.json", summary)
    representation_lines = [
        "# Frozen propagation representation audit",
        "",
        "- Manual geometry is converted to a `d_perp(theta)` vector; node count depends on the seed-visible theta corridor.",
        "- P0 predicts a common vertical transport, converted to one `d_perp` shift.",
        "- Candidate search adds one scalar offset to every node. The full curve is sampled for evidence, but node offsets are not independently estimated.",
        "- Consequently, `d_curve(theta) - median(d_curve)` is invariant along a path: curvature is frozen, not learned frame by frame.",
        "- Near and far proposals use separate contrast thresholds. The unchanged pair-safe comparator stops both when either proposal fails or seed pair separation/order becomes unsafe.",
        "- The boundary-independent diagnostic uses the same proposal and thresholds but continues each boundary only until its own first failure. It is diagnostic only and is not accepted as pair-safe optional scene context.",
        "- A stable center trajectory can coexist with a wrong curve shape or a silent ridge switch; checkpoint and image review are required.",
    ]
    (POST / "REPRESENTATION_AUDIT.md").write_text("\n".join(representation_lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
