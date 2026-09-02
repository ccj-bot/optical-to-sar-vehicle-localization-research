from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "person_r02_scene_depth_value_test_20260902"
OUT = WORKSPACE / "output" / "person_r02_scene_depth_value_test_20260902"
PRE = OUT / "pre_reference"
FIG = OUT / "figures" / "pre_reference_optical_review"

R2_PRE = (
    WORKSPACE
    / "output"
    / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830"
    / "pre_reference"
)
REGISTRY = R2_PRE / "full_stream_frame_registry_pre_reference.parquet"
SHELLS = R2_PRE / "full_stream_optical_shells_pre_reference.parquet"
OPTICAL = (
    WORKSPACE
    / "output"
    / "person_optical_guided_sar_annotation_full_20260823"
    / "optical_person_frame_hypotheses.parquet"
)
BOUNDARY_OUT = WORKSPACE / "output" / "r02_local_boundary_observability_20260902"
MANUAL_BOUNDARIES = BOUNDARY_OUT / "post_freeze_audit" / "MANUAL_SEMANTIC_CHECKPOINT_INVENTORY.jsonl"
PAIR_PATHS = BOUNDARY_OUT / "pre_reference" / "ALL_PAIR_SAFE_PATHS.jsonl"
VISUAL_VERDICTS = BOUNDARY_OUT / "post_freeze_audit" / "MANUAL_VISUAL_VERDICTS.csv"
PRIOR_OPTICAL_HALFSPACE = (
    WORKSPACE
    / "output"
    / "person_r02_curb_radial_anchor_pilot_20260831"
    / "pre_reference"
    / "optical_person_curb_topology_visual_development_only.csv"
)

MANUAL_FRAMES = [47, 62, 82, 150, 183, 239, 264, 278, 427, 454, 472]
PROPAGATED_SOURCES: dict[int, tuple[int, str]] = {
    59: (62, "BACKWARD"),
    60: (62, "BACKWARD"),
    61: (62, "BACKWARD"),
    63: (62, "FORWARD"),
    64: (62, "FORWARD"),
    65: (62, "FORWARD"),
    108: (150, "BACKWARD"),
    157: (150, "FORWARD"),
    164: (150, "FORWARD"),
    166: (183, "BACKWARD"),
    174: (183, "BACKWARD"),
    215: (264, "BACKWARD"),
    221: (183, "FORWARD"),
    259: (183, "FORWARD"),
    266: (264, "FORWARD"),
    269: (264, "FORWARD"),
    406: (454, "BACKWARD"),
    430: (454, "BACKWARD"),
    468: (454, "FORWARD"),
    481: (454, "FORWARD"),
}
EXCLUDED_KNOWN_FRAMES = {58, 66, 67, 165, 260, 270, 405, 482}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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


def fit(image: np.ndarray, width: int, height: int) -> np.ndarray:
    scale = min(width / image.shape[1], height / image.shape[0])
    resized = cv2.resize(image, (max(1, int(image.shape[1] * scale)), max(1, int(image.shape[0] * scale))))
    canvas = np.full((height, width, 3), 245, dtype=np.uint8)
    x = (width - resized.shape[1]) // 2
    y = (height - resized.shape[0]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    return canvas


def label(image: np.ndarray, lines: list[str]) -> np.ndarray:
    header = np.full((75, image.shape[1], 3), (24, 22, 22), dtype=np.uint8)
    for index, text in enumerate(lines):
        cv2.putText(header, text, (12, 26 + 23 * index), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (245, 245, 245), 1, cv2.LINE_AA)
    return np.vstack([header, image])


def boundary_inventory(registry: pd.DataFrame) -> tuple[pd.DataFrame, dict[tuple[int, str], dict[str, Any]]]:
    manual_rows = read_jsonl(MANUAL_BOUNDARIES)
    path_rows = read_jsonl(PAIR_PATHS)
    manual_index = {(int(row["sar_frame_index"]), str(row["object_type"])): row for row in manual_rows}
    path_index = {
        (
            int(row["seed_frame"]),
            str(row["direction"]),
            int(row["sar_frame_index"]),
            str(row["object_type"]),
        ): row
        for row in path_rows
    }
    registry_index = registry.set_index("sar_frame_index")
    rows: list[dict[str, Any]] = []
    geometry: dict[tuple[int, str], dict[str, Any]] = {}
    frames = sorted(set(MANUAL_FRAMES) | set(PROPAGATED_SOURCES))
    if set(frames) & EXCLUDED_KNOWN_FRAMES:
        raise RuntimeError("Known unsafe frame entered eligible set")
    for frame in frames:
        frame_row = registry_index.loc[frame]
        for object_type in ("SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"):
            if frame in MANUAL_FRAMES:
                source = manual_index[(frame, object_type)]
                provenance = "MANUAL_SEMANTIC_CHECKPOINT"
                seed_frame = frame
                direction = "MANUAL"
            else:
                seed_frame, direction = PROPAGATED_SOURCES[frame]
                source = path_index[(seed_frame, direction, frame, object_type)]
                provenance = "VISUALLY_REVIEWED_STABLE_PROPAGATION"
            points = np.asarray(source["points"], dtype=float)
            cx = float(frame_row.geometry_center_x_px)
            cy = float(frame_row.geometry_center_y_px)
            px_per_m = float(frame_row.geometry_radius_px) / float(frame_row.geometry_outer_range_m)
            theta = np.degrees(np.arctan2(points[:, 0] - cx, cy - points[:, 1]))
            radius_m = np.hypot(points[:, 0] - cx, cy - points[:, 1]) / px_per_m
            order = np.argsort(theta)
            theta = theta[order]
            radius_m = radius_m[order]
            record = {
                "run_id": "R02ZF",
                "sar_frame_index": frame,
                "object_type": object_type,
                "boundary_provenance": provenance,
                "source_seed_frame": seed_frame,
                "source_direction": direction,
                "theta_min_deg": float(theta.min()),
                "theta_max_deg": float(theta.max()),
                "radius_min_m": float(radius_m.min()),
                "radius_max_m": float(radius_m.max()),
                "points_json": json.dumps(points.tolist(), ensure_ascii=False),
                "theta_nodes_json": json.dumps(theta.tolist()),
                "radius_nodes_m_json": json.dumps(radius_m.tolist()),
                "manual_person_reference_used": False,
                "known_false_support_excluded": True,
            }
            rows.append(record)
            geometry[(frame, object_type)] = record
    result = pd.DataFrame(rows)
    for frame, group in result.groupby("sar_frame_index"):
        near = group[group.object_type.eq("SAR_BOUNDARY_NEAR")].iloc[0]
        far = group[group.object_type.eq("SAR_BOUNDARY_FAR")].iloc[0]
        low = max(float(near.theta_min_deg), float(far.theta_min_deg))
        high = min(float(near.theta_max_deg), float(far.theta_max_deg))
        if high <= low:
            raise RuntimeError(f"No common theta support at F{frame}")
    return result, geometry


def parse_intervals(value: str) -> list[list[float]]:
    return [[float(a), float(b)] for a, b in json.loads(value)]


def optical_match(shell: pd.Series, optical: pd.DataFrame) -> pd.Series:
    matches = optical[
        optical.run_id.eq("R02ZF")
        & optical.raw_track_fragment_id.astype(str).eq(str(shell.track_id))
        & optical.timestamp_ms.eq(int(shell.source_timestamp_max_ms))
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Optical match count={len(matches)} for {shell.shell_id}")
    return matches.iloc[0]


def review_queue(
    registry: pd.DataFrame, boundaries: pd.DataFrame, geometry: dict[tuple[int, str], dict[str, Any]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    shells = pd.read_parquet(SHELLS)
    shells = shells[
        shells.run_id.eq("R02ZF")
        & shells["mode"].eq("CAUSAL_REPLAY")
        & shells.frame_index.isin(boundaries.sar_frame_index.unique())
    ].copy()
    optical = pd.read_parquet(OPTICAL)
    prior = pd.read_csv(PRIOR_OPTICAL_HALFSPACE)
    prior_keys = {
        (int(row.frame_index), str(row.raw_track_fragment_id)): (str(row.topology_label), str(row.topology_confidence))
        for row in prior.itertuples(index=False)
    }
    rows: list[dict[str, Any]] = []
    for shell in shells.sort_values(["frame_index", "track_id"]).itertuples(index=False):
        shell_series = pd.Series(shell._asdict())
        opt = optical_match(shell_series, optical)
        near = geometry[(int(shell.frame_index), "SAR_BOUNDARY_NEAR")]
        far = geometry[(int(shell.frame_index), "SAR_BOUNDARY_FAR")]
        common_low = max(float(near["theta_min_deg"]), float(far["theta_min_deg"]))
        common_high = min(float(near["theta_max_deg"]), float(far["theta_max_deg"]))
        intervals = parse_intervals(str(shell.effective_intervals_json))
        full_coverage = all(low >= common_low and high <= common_high for low, high in intervals)
        overlap_width = sum(max(0.0, min(high, common_high) - max(low, common_low)) for low, high in intervals)
        angular_width = sum(high - low for low, high in intervals)
        prior_label, prior_confidence = prior_keys.get(
            (int(opt.frame_index), str(opt.raw_track_fragment_id)), ("NO_PRIOR_LABEL", "NONE")
        )
        review_key = f"OPT_F{int(opt.frame_index):03d}__{str(opt.raw_track_fragment_id)}"
        rows.append(
            {
                "run_id": "R02ZF",
                "sar_frame": int(shell.frame_index),
                "sar_timestamp_ms": int(shell.sar_timestamp_ms),
                "shell_id": str(shell.shell_id),
                "person_hypothesis_id": str(shell.track_id),
                "optical_review_id": review_key,
                "optical_frame": int(opt.frame_index),
                "optical_timestamp_ms": int(opt.timestamp_ms),
                "optical_image_path": str(opt.optical_image_path),
                "bbox_x1": float(opt.bbox_x1),
                "bbox_y1": float(opt.bbox_y1),
                "bbox_x2": float(opt.bbox_x2),
                "bbox_y2": float(opt.bbox_y2),
                "box_source": str(opt.box_source),
                "optical_person_id": str(opt.optical_person_id),
                "effective_intervals_json": str(shell.effective_intervals_json),
                "boundary_common_theta_low_deg": common_low,
                "boundary_common_theta_high_deg": common_high,
                "boundary_theta_overlap_fraction": overlap_width / angular_width if angular_width > 0 else 0.0,
                "boundary_full_theta_coverage": bool(full_coverage),
                "boundary_state": "TRUSTED_MANUAL_OR_VISUALLY_REVIEWED_STABLE",
                "manual_or_propagated_boundary_provenance": str(near["boundary_provenance"]),
                "prior_one_curb_visual_label": prior_label,
                "prior_one_curb_visual_confidence": prior_confidence,
                "scene_layer": "PENDING_VISUAL_REVIEW",
                "visual_state": "PENDING_VISUAL_REVIEW",
                "reason": "",
                "manual_person_reference_used": False,
            }
        )
    queue = pd.DataFrame(rows)
    unique_columns = [
        "optical_review_id",
        "optical_frame",
        "optical_timestamp_ms",
        "optical_image_path",
        "person_hypothesis_id",
        "optical_person_id",
        "bbox_x1",
        "bbox_y1",
        "bbox_x2",
        "bbox_y2",
        "box_source",
        "prior_one_curb_visual_label",
        "prior_one_curb_visual_confidence",
    ]
    unique = queue[unique_columns].drop_duplicates("optical_review_id").sort_values("optical_frame").reset_index(drop=True)
    unique.insert(0, "review_number", np.arange(1, len(unique) + 1))
    unique["scene_layer"] = "PENDING_VISUAL_REVIEW"
    unique["visual_state"] = "PENDING_VISUAL_REVIEW"
    unique["reason"] = ""
    unique["manual_person_reference_used"] = False
    return queue, unique


def render_optical_reviews(unique: pd.DataFrame) -> None:
    panels: list[np.ndarray] = []
    for row in unique.itertuples(index=False):
        image = read_bgr(Path(row.optical_image_path))
        x1, y1, x2, y2 = [int(round(value)) for value in (row.bbox_x1, row.bbox_y1, row.bbox_x2, row.bbox_y2)]
        context = image.copy()
        cv2.rectangle(context, (x1, y1), (x2, y2), (0, 255, 255), max(3, image.shape[1] // 900))
        margin_x = max(180, int(0.8 * (x2 - x1)))
        margin_y = max(120, int(0.35 * (y2 - y1)))
        crop = image[max(0, y1 - margin_y) : min(image.shape[0], y2 + margin_y), max(0, x1 - margin_x) : min(image.shape[1], x2 + margin_x)]
        body = np.hstack([fit(context, 900, 500), fit(crop, 600, 500)])
        panel = label(
            body,
            [
                f"#{int(row.review_number):02d} OPT F{int(row.optical_frame):03d} {row.person_hypothesis_id}",
                f"prior halfspace={row.prior_one_curb_visual_label} ({row.prior_one_curb_visual_confidence}); classify L0/L1/L2/UNCERTAIN",
            ],
        )
        panels.append(panel)
    blank = np.full_like(panels[0], 245)
    for start in range(0, len(panels), 4):
        block = panels[start : start + 4]
        while len(block) < 4:
            block.append(blank)
        sheet = np.vstack([np.hstack(block[:2]), np.hstack(block[2:])])
        write_png(FIG / f"OPTICAL_SCENE_LAYER_REVIEW_{start // 4 + 1:02d}.png", sheet)


def render_boundary_reviews(registry: pd.DataFrame, queue: pd.DataFrame, geometry: dict[tuple[int, str], dict[str, Any]]) -> None:
    frames = sorted(queue.sar_frame.unique())
    panels = []
    registry_index = registry.set_index("sar_frame_index")
    for frame in frames:
        image = read_bgr(Path(registry_index.loc[frame].sar_image_path))
        for object_type, color in (("SAR_BOUNDARY_NEAR", (255, 255, 0)), ("SAR_BOUNDARY_FAR", (0, 165, 255))):
            points = np.asarray(json.loads(geometry[(frame, object_type)]["points_json"]), dtype=float)
            cv2.polylines(image, [np.rint(points).astype(np.int32)], False, color, 3, cv2.LINE_AA)
        group = queue[queue.sar_frame.eq(frame)]
        full = int(group.boundary_full_theta_coverage.sum())
        panel = label(
            fit(image, 800, 470),
            [
                f"SAR F{frame:03d}: trusted near(cyan)/far(orange) geometry; no PERSON reference overlay",
                f"causal shells={len(group)}, full boundary-theta coverage={full}",
            ],
        )
        panels.append(panel)
    blank = np.full_like(panels[0], 245)
    for start in range(0, len(panels), 6):
        block = panels[start : start + 6]
        while len(block) < 6:
            block.append(blank)
        sheet = np.vstack([np.hstack(block[:3]), np.hstack(block[3:])])
        write_png(FIG / f"BOUNDARY_ELIGIBILITY_REVIEW_{start // 6 + 1:02d}.png", sheet)


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(WORKSPACE)
    for path in (TASK, OUT, REGISTRY, SHELLS, OPTICAL, BOUNDARY_OUT):
        lowered = str(path).lower()
        if "old_work" in lowered or "r04" in lowered:
            raise RuntimeError(f"Forbidden path: {path}")
    PRE.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    registry = pd.read_parquet(REGISTRY)
    registry = registry[registry.run_id.eq("R02ZF")].copy()
    boundaries, geometry = boundary_inventory(registry)
    queue, unique = review_queue(registry, boundaries, geometry)
    boundaries.to_csv(PRE / "BOUNDARY_VALUE_ELIGIBLE_GEOMETRY_PRE_REFERENCE.csv", index=False, encoding="utf-8-sig")
    boundaries.to_parquet(PRE / "BOUNDARY_VALUE_ELIGIBLE_GEOMETRY_PRE_REFERENCE.parquet", index=False)
    queue.to_csv(PRE / "OPTICAL_PERSON_SCENE_LAYER_QUEUE_PRE_REFERENCE.csv", index=False, encoding="utf-8-sig")
    unique.to_csv(PRE / "OPTICAL_PERSON_SCENE_LAYER_VISUAL_CASES_PRE_REFERENCE.csv", index=False, encoding="utf-8-sig")
    render_optical_reviews(unique)
    render_boundary_reviews(registry, queue, geometry)
    summary = {
        "schema": "PERSON_R02_SCENE_DEPTH_VALUE_PREPARE_V1",
        "eligible_boundary_frame_count": int(boundaries.sar_frame_index.nunique()),
        "manual_boundary_frame_count": len(MANUAL_FRAMES),
        "visually_reviewed_propagated_frame_count": len(PROPAGATED_SOURCES),
        "known_unsafe_frames_excluded": sorted(EXCLUDED_KNOWN_FRAMES),
        "causal_person_shell_rows_on_eligible_boundary_frames": len(queue),
        "unique_optical_visual_cases": len(unique),
        "full_boundary_theta_coverage_shell_rows": int(queue.boundary_full_theta_coverage.sum()),
        "partial_or_zero_boundary_theta_coverage_shell_rows": int((~queue.boundary_full_theta_coverage).sum()),
        "scene_layer_labels_frozen": False,
        "case_level_person_sar_reference_opened": False,
        "boundary_propagation_modified": False,
        "f66_used": False,
        "r04_accessed": False,
        "final_localization_run": False,
    }
    (PRE / "PREPARE_SUMMARY.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
