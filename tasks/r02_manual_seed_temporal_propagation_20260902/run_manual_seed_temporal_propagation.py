from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import find_peaks


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "r02_manual_seed_temporal_propagation_20260902"
OUT = WORKSPACE / "output" / "r02_manual_seed_temporal_propagation_20260902"
FIG = OUT / "figures"
MANUAL_EVENTS = (
    WORKSPACE
    / "output"
    / "r02_manual_static_scene_anchor_preparation_20260902"
    / "user_annotations"
    / "manual_static_scene_annotations.jsonl"
)
REGISTRY = (
    WORKSPACE
    / "output"
    / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830"
    / "pre_reference"
    / "full_stream_frame_registry_pre_reference.parquet"
)
P0_EDGES = (
    WORKSPACE
    / "output"
    / "person_b0_end_to_end_capability_and_bottleneck_study_20260830"
    / "pre_reference"
    / "full_stream_p0_graded_p0_q95_edges.parquet"
)
P1E_SCRIPT = (
    WORKSPACE
    / "tasks"
    / "person_physics_guided_image_domain_study_20260824"
    / "run_p1e_single_frame_position_specificity.py"
)

PROPAGATED = OUT / "propagated_static_scene_annotations.jsonl"
DIAGNOSTICS = OUT / "propagation_frame_diagnostics.csv"
REVIEW = OUT / "REVIEW_REQUIRED_FRAME_LIST.csv"
SUMMARY = OUT / "MANUAL_SEED_TEMPORAL_PROPAGATION_SUMMARY.json"
SEED_MANIFEST = OUT / "USER_CONFIRMED_SEED_AUTHORITY.json"
REPORT = OUT / "REPORT.md"
OUTPUT_MANIFEST = OUT / "OUTPUT_MANIFEST.csv"

BOUNDARIES = {
    "SAR_BOUNDARY_NEAR": {"object_id": "R02_CURB_NEAR", "color_bgr": (216, 199, 0)},
    "SAR_BOUNDARY_FAR": {"object_id": "R02_CURB_FAR", "color_bgr": (46, 157, 255)},
}
SEARCH_OFFSETS_M = np.arange(-0.30, 0.3001, 0.01, dtype=np.float32)
BACKGROUND_OFFSET_M = 0.18
MIN_AGGREGATE_CONTRAST = {
    "SAR_BOUNDARY_NEAR": 0.008,
    "SAR_BOUNDARY_FAR": 0.004,
}
MIN_NODE_SUPPORT_FRACTION = 0.50
MAX_LOCAL_OFFSET_M = 0.18
DISTINCT_CANDIDATE_DISTANCE_M = 0.18
AMBIGUOUS_SECOND_RATIO = 0.92
MAX_BIDIRECTIONAL_DISAGREEMENT_M = 0.12
MAX_PAIR_SEPARATION_DEVIATION_M = 0.30
THETA_STEP_DEG = 2.0


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_bgr(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def latest_manual_annotations() -> tuple[list[dict[str, object]], str, int]:
    raw_lines = [line for line in MANUAL_EVENTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest: dict[str, dict[str, object]] = {}
    for line in raw_lines:
        event = json.loads(line)
        latest[str(event["annotation_id"])] = event
    active = [event for event in latest.values() if event.get("event_type") != "DELETE"]
    return active, sha256_file(MANUAL_EVENTS), len(raw_lines)


def load_registry() -> pd.DataFrame:
    registry = pd.read_parquet(REGISTRY)
    registry = registry[registry.run_id.eq("R02ZF")].sort_values("sar_frame_index").copy()
    return registry.set_index("sar_frame_index", drop=False)


def load_p0_transforms() -> dict[tuple[int, int], dict[str, object]]:
    edges = pd.read_parquet(P0_EDGES)
    edges = edges[edges.run_id.eq("R02ZF")]
    grouped = (
        edges.groupby(["source_frame", "destination_frame"], as_index=False)
        .agg(
            p0_state=("p0_state", "first"),
            p0_model=("p0_model", "first"),
            translation_dx_px=("translation_dx_px", "median"),
            translation_dy_px=("translation_dy_px", "median"),
        )
    )
    return {
        (int(row.source_frame), int(row.destination_frame)): {
            "p0_state": str(row.p0_state),
            "p0_model": str(row.p0_model),
            "dx": float(row.translation_dx_px),
            "dy": float(row.translation_dy_px),
        }
        for row in grouped.itertuples(index=False)
    }


def point_to_theta_d(point: list[float], row: pd.Series) -> tuple[float, float]:
    x, y = map(float, point)
    cx = float(row.geometry_center_x_px)
    cy = float(row.geometry_center_y_px)
    ppm = float(row.geometry_radius_px) / float(row.geometry_outer_range_m)
    d = (cy - y) / ppm
    theta = math.degrees(math.atan2(x - cx, cy - y))
    return theta, d


def manual_curve(points: list[list[float]], row: pd.Series, theta_grid_deg: np.ndarray) -> np.ndarray:
    converted = sorted(point_to_theta_d(point, row) for point in points)
    theta = np.array([item[0] for item in converted], dtype=float)
    d = np.array([item[1] for item in converted], dtype=float)
    unique_theta, unique_indices = np.unique(theta, return_index=True)
    if len(unique_theta) < 2:
        raise ValueError("Manual polyline must span at least two distinct theta values")
    return np.interp(theta_grid_deg, unique_theta, d[unique_indices])


def curve_to_points(theta_grid_deg: np.ndarray, d_curve_m: np.ndarray, row: pd.Series) -> list[list[float]]:
    cx = float(row.geometry_center_x_px)
    cy = float(row.geometry_center_y_px)
    ppm = float(row.geometry_radius_px) / float(row.geometry_outer_range_m)
    theta_rad = np.deg2rad(theta_grid_deg)
    x = cx + d_curve_m * ppm * np.tan(theta_rad)
    y = cy - d_curve_m * ppm
    return [[round(float(px), 3), round(float(py), 3)] for px, py in zip(x, y)]


@dataclass
class Proposal:
    curve_m: np.ndarray
    status: str
    reasons: list[str]
    best_score: float
    best_offset_m: float
    second_score: float | None
    second_offset_m: float | None
    second_ratio: float | None
    node_support_fraction: float
    p0_dx_px: float
    p0_dy_px: float


class EvidenceCache:
    def __init__(self, registry: pd.DataFrame, p1e) -> None:
        self.registry = registry
        self.p1e = p1e
        self.cache: dict[int, np.ndarray] = {}

    def jet(self, frame_index: int) -> np.ndarray:
        if frame_index not in self.cache:
            image = read_bgr(Path(str(self.registry.loc[frame_index].sar_image_path)))
            self.cache[frame_index] = self.p1e.jet_proxy(image)[0]
        return self.cache[frame_index]


def sample_grid(
    jet: np.ndarray,
    row: pd.Series,
    theta_grid_deg: np.ndarray,
    d_grid_m: np.ndarray,
) -> np.ndarray:
    cx = float(row.geometry_center_x_px)
    cy = float(row.geometry_center_y_px)
    ppm = float(row.geometry_radius_px) / float(row.geometry_outer_range_m)
    theta = np.deg2rad(theta_grid_deg)[None, :]
    x = (cx + d_grid_m * ppm * np.tan(theta)).astype(np.float32)
    y = (cy - d_grid_m * ppm).astype(np.float32)
    return cv2.remap(
        jet.astype(np.float32),
        x,
        y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=np.nan,
    )


def propose_curve(
    object_type: str,
    source_frame: int,
    destination_frame: int,
    previous_curve_m: np.ndarray,
    theta_grid_deg: np.ndarray,
    registry: pd.DataFrame,
    transforms: dict[tuple[int, int], dict[str, object]],
    evidence: EvidenceCache,
) -> Proposal:
    key = (min(source_frame, destination_frame), max(source_frame, destination_frame))
    if key not in transforms:
        return Proposal(
            previous_curve_m.copy(),
            "PROPAGATION_AMBIGUOUS",
            ["P0_UNAVAILABLE"],
            float("nan"),
            float("nan"),
            None,
            None,
            None,
            0.0,
            float("nan"),
            float("nan"),
        )
    transform = transforms[key]
    signed_dy = float(transform["dy"]) if destination_frame > source_frame else -float(transform["dy"])
    row = registry.loc[destination_frame]
    ppm = float(row.geometry_radius_px) / float(row.geometry_outer_range_m)
    predicted_curve = previous_curve_m - signed_dy / ppm
    candidate_grid = predicted_curve[None, :] + SEARCH_OFFSETS_M[:, None]
    jet = evidence.jet(destination_frame)
    center = sample_grid(jet, row, theta_grid_deg, candidate_grid)
    closer = sample_grid(jet, row, theta_grid_deg, candidate_grid - BACKGROUND_OFFSET_M)
    farther = sample_grid(jet, row, theta_grid_deg, candidate_grid + BACKGROUND_OFFSET_M)
    node_contrast = center - np.maximum(closer, farther)
    aggregate = np.nanmedian(node_contrast, axis=1)
    finite = np.isfinite(aggregate)
    reasons: list[str] = []
    if not finite.any():
        return Proposal(
            predicted_curve,
            "PROPAGATION_AMBIGUOUS",
            ["BOUNDARY_OUTSIDE_VALID_FAN"],
            float("nan"),
            float("nan"),
            None,
            None,
            None,
            0.0,
            float(transform["dx"]),
            float(transform["dy"]),
        )
    safe_aggregate = np.where(finite, aggregate, -np.inf)
    peak_indices, _ = find_peaks(safe_aggregate, distance=6, prominence=0.0015)
    if not len(peak_indices):
        peak_indices = np.array([int(np.nanargmax(safe_aggregate))])
    candidates = sorted(
        [(float(safe_aggregate[index]), float(SEARCH_OFFSETS_M[index]), int(index)) for index in peak_indices],
        reverse=True,
    )
    best_score, best_offset, best_index = candidates[0]
    distinct = [item for item in candidates[1:] if abs(item[1] - best_offset) >= DISTINCT_CANDIDATE_DISTANCE_M]
    second_score: float | None = None
    second_offset: float | None = None
    second_ratio: float | None = None
    if distinct:
        second_score, second_offset, _ = distinct[0]
        second_ratio = second_score / best_score if best_score > 0 else None
    selected_node_contrast = node_contrast[best_index]
    node_support_fraction = float(np.mean(np.isfinite(selected_node_contrast) & (selected_node_contrast >= 0.002)))
    if best_score < MIN_AGGREGATE_CONTRAST[object_type]:
        reasons.append("BOUNDARY_RESPONSE_TOO_WEAK")
    if abs(best_offset) > MAX_LOCAL_OFFSET_M:
        reasons.append("RIDGE_JUMP_EXCEEDS_LOCAL_CORRIDOR")
    if node_support_fraction < MIN_NODE_SUPPORT_FRACTION:
        reasons.append("BOUNDARY_SUPPORT_TOO_FRAGMENTED")
    if second_ratio is not None and second_ratio >= AMBIGUOUS_SECOND_RATIO:
        reasons.append("MULTIPLE_SIMILAR_LOCAL_RIDGES")
    status = "PROPAGATION_AMBIGUOUS" if reasons else "SUPPORTED"
    return Proposal(
        predicted_curve + best_offset,
        status,
        reasons,
        best_score,
        best_offset,
        second_score,
        second_offset,
        second_ratio,
        node_support_fraction,
        float(transform["dx"]),
        float(transform["dy"]),
    )


def propagate_direction(
    start_frame: int,
    end_frame: int,
    seed_curves: dict[str, np.ndarray],
    expected_separation_m: float,
    theta_grid_deg: np.ndarray,
    registry: pd.DataFrame,
    transforms: dict[tuple[int, int], dict[str, object]],
    evidence: EvidenceCache,
    direction_name: str,
) -> tuple[dict[int, dict[str, np.ndarray]], list[dict[str, object]], dict[str, object] | None]:
    step = 1 if end_frame > start_frame else -1
    curves: dict[int, dict[str, np.ndarray]] = {
        start_frame: {name: curve.copy() for name, curve in seed_curves.items()}
    }
    diagnostics: list[dict[str, object]] = []
    stop: dict[str, object] | None = None
    current = {name: curve.copy() for name, curve in seed_curves.items()}
    for destination in range(start_frame + step, end_frame + step, step):
        source = destination - step
        proposals = {
            name: propose_curve(
                name,
                source,
                destination,
                current[name],
                theta_grid_deg,
                registry,
                transforms,
                evidence,
            )
            for name in BOUNDARIES
        }
        separation = float(np.median(proposals["SAR_BOUNDARY_FAR"].curve_m - proposals["SAR_BOUNDARY_NEAR"].curve_m))
        pair_reasons: list[str] = []
        for name, proposal in proposals.items():
            pair_reasons.extend(f"{name}:{reason}" for reason in proposal.reasons)
        if separation <= 0:
            pair_reasons.append("PAIR_ORDER_REVERSED")
        if abs(separation - expected_separation_m) > MAX_PAIR_SEPARATION_DEVIATION_M:
            pair_reasons.append("PAIR_SEPARATION_LEFT_MANUAL_CORRIDOR")
        for name, proposal in proposals.items():
            diagnostics.append(
                {
                    "direction": direction_name,
                    "source_frame": source,
                    "destination_frame": destination,
                    "object_type": name,
                    "status": "PROPAGATION_AMBIGUOUS" if pair_reasons else proposal.status,
                    "reasons": "|".join(pair_reasons if pair_reasons else proposal.reasons),
                    "best_score": proposal.best_score,
                    "best_offset_m": proposal.best_offset_m,
                    "second_score": proposal.second_score,
                    "second_offset_m": proposal.second_offset_m,
                    "second_ratio": proposal.second_ratio,
                    "node_support_fraction": proposal.node_support_fraction,
                    "p0_dx_px": proposal.p0_dx_px,
                    "p0_dy_px": proposal.p0_dy_px,
                    "pair_separation_m": separation,
                }
            )
        if pair_reasons:
            stop = {
                "direction": direction_name,
                "source_frame": source,
                "destination_frame": destination,
                "status": "PROPAGATION_AMBIGUOUS",
                "reasons": sorted(set(pair_reasons)),
            }
            break
        current = {name: proposal.curve_m for name, proposal in proposals.items()}
        curves[destination] = {name: curve.copy() for name, curve in current.items()}
    return curves, diagnostics, stop


def diagnostics_lookup(rows: list[dict[str, object]]) -> dict[tuple[str, int, str], dict[str, object]]:
    return {
        (str(row["direction"]), int(row["destination_frame"]), str(row["object_type"])): row
        for row in rows
    }


def render_review_strip(
    records: list[dict[str, object]],
    registry: pd.DataFrame,
    selected_frames: list[int],
) -> None:
    by_key = {(int(record["sar_frame_index"]), str(record["object_type"])): record for record in records}
    panels: list[np.ndarray] = []
    for frame_index in selected_frames:
        row = registry.loc[frame_index]
        image = read_bgr(Path(str(row.sar_image_path)))
        for object_type, settings in BOUNDARIES.items():
            record = by_key.get((frame_index, object_type))
            if record is None:
                continue
            points = np.round(np.array(record["points"], dtype=float)).astype(np.int32)
            cv2.polylines(image, [points], False, settings["color_bgr"], 2, cv2.LINE_AA)
            cv2.putText(
                image,
                "NEAR" if object_type.endswith("NEAR") else "FAR",
                tuple(points[len(points) // 2]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                settings["color_bgr"],
                1,
                cv2.LINE_AA,
            )
        cv2.rectangle(image, (0, 0), (image.shape[1], 42), (12, 18, 24), -1)
        cv2.putText(
            image,
            f"R02ZF SAR F{frame_index:03d} t={int(row.sar_timestamp_ms)}ms",
            (14, 27),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        panels.append(image)
    while len(panels) % 3:
        panels.append(np.full_like(panels[0], 245))
    rows = [cv2.hconcat(panels[index : index + 3]) for index in range(0, len(panels), 3)]
    contact = cv2.vconcat(rows)
    FIG.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(".png", contact)
    if not ok:
        raise RuntimeError("Could not encode propagation review strip")
    encoded.tofile(FIG / "propagation_review_strip.png")


def plot_tracks(records: list[dict[str, object]], seed_frames: list[int]) -> None:
    table = pd.DataFrame(records)
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True, constrained_layout=True)
    colors = {"SAR_BOUNDARY_NEAR": "tab:cyan", "SAR_BOUNDARY_FAR": "tab:orange"}
    for object_type, group in table.groupby("object_type"):
        group = group.sort_values("sar_frame_index")
        axes[0].plot(group.sar_frame_index, group.d_center_m, color=colors[object_type], label=object_type)
        axes[1].plot(
            group.sar_frame_index,
            group.bidirectional_disagreement_m,
            color=colors[object_type],
            marker="o",
            label=object_type,
        )
    for axis in axes:
        for seed in seed_frames:
            axis.axvline(seed, color="black", ls="--", lw=0.8)
        axis.grid(alpha=0.25)
        axis.legend()
    axes[0].set_ylabel("d_perp center [m]")
    axes[0].set_title("Manual-seed bracketed SAR boundary propagation")
    axes[1].axhline(MAX_BIDIRECTIONAL_DISAGREEMENT_M, color="red", ls=":", lw=1)
    axes[1].set_ylabel("forward/backward disagreement [m]")
    axes[1].set_title("Defined only where the two anchored propagation paths overlap")
    axes[1].set_xlabel("SAR frame index")
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "boundary_center_tracks.png", dpi=150)
    plt.close(fig)


def write_manifest() -> None:
    files = [
        PROPAGATED,
        DIAGNOSTICS,
        REVIEW,
        SUMMARY,
        SEED_MANIFEST,
        REPORT,
        FIG / "propagation_review_strip.png",
        FIG / "boundary_center_tracks.png",
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
    parser = argparse.ArgumentParser(description="R02 user-confirmed manual-seed boundary propagation")
    parser.add_argument("--accept-confirmed-draft-seeds", action="store_true")
    args = parser.parse_args()
    if not args.accept_confirmed_draft_seeds:
        raise SystemExit("Refusing DRAFT seeds without --accept-confirmed-draft-seeds")
    manual_hash_before = sha256_file(MANUAL_EVENTS)
    active, manual_hash_loaded, manual_event_count = latest_manual_annotations()
    registry = load_registry()
    transforms = load_p0_transforms()
    p1e = load_module("r02_manual_seed_p1e", P1E_SCRIPT)
    evidence = EvidenceCache(registry, p1e)
    seed_rows = [
        event
        for event in active
        if event.get("modality") == "SAR"
        and event.get("object_type") in BOUNDARIES
        and event.get("confidence_state") in {"CONFIDENT", "LIKELY"}
        and len(event.get("points", [])) >= 2
    ]
    by_frame: dict[int, dict[str, dict[str, object]]] = {}
    for event in seed_rows:
        by_frame.setdefault(int(event["sar_frame_index"]), {})[str(event["object_type"])] = event
    seed_frames = sorted(frame for frame, group in by_frame.items() if set(group) == set(BOUNDARIES))
    if len(seed_frames) != 2:
        raise ValueError(f"Expected exactly two complete semantic seed pairs, observed {seed_frames}")
    lower_seed, upper_seed = seed_frames
    theta_extents = []
    for frame in seed_frames:
        row = registry.loc[frame]
        for object_type in BOUNDARIES:
            theta_values = [point_to_theta_d(point, row)[0] for point in by_frame[frame][object_type]["points"]]
            theta_extents.append((min(theta_values), max(theta_values)))
    common_low = max(item[0] for item in theta_extents) + 1.0
    common_high = min(item[1] for item in theta_extents) - 1.0
    grid_low = math.ceil(common_low / THETA_STEP_DEG) * THETA_STEP_DEG
    grid_high = math.floor(common_high / THETA_STEP_DEG) * THETA_STEP_DEG
    theta_grid_deg = np.arange(grid_low, grid_high + 0.001, THETA_STEP_DEG, dtype=float)
    if len(theta_grid_deg) < 8:
        raise ValueError(f"Manual seed common theta corridor is too narrow: {common_low} to {common_high}")
    seed_curves: dict[int, dict[str, np.ndarray]] = {}
    for frame in seed_frames:
        row = registry.loc[frame]
        seed_curves[frame] = {
            object_type: manual_curve(by_frame[frame][object_type]["points"], row, theta_grid_deg)
            for object_type in BOUNDARIES
        }
    expected_separations = [
        float(np.median(seed_curves[frame]["SAR_BOUNDARY_FAR"] - seed_curves[frame]["SAR_BOUNDARY_NEAR"]))
        for frame in seed_frames
    ]
    expected_separation = float(np.mean(expected_separations))
    forward, forward_diag, forward_stop = propagate_direction(
        lower_seed,
        upper_seed,
        seed_curves[lower_seed],
        expected_separation,
        theta_grid_deg,
        registry,
        transforms,
        evidence,
        "FORWARD_FROM_LOWER_SEED",
    )
    backward, backward_diag, backward_stop = propagate_direction(
        upper_seed,
        lower_seed,
        seed_curves[upper_seed],
        expected_separation,
        theta_grid_deg,
        registry,
        transforms,
        evidence,
        "BACKWARD_FROM_UPPER_SEED",
    )
    all_diagnostics = forward_diag + backward_diag
    lookup = diagnostics_lookup(all_diagnostics)
    overlap_frames = sorted(set(forward) & set(backward) - set(seed_frames))
    bridge_disagreements: dict[str, list[float]] = {
        object_type: [
            float(np.median(np.abs(forward[frame][object_type] - backward[frame][object_type])))
            for frame in overlap_frames
        ]
        for object_type in BOUNDARIES
    }
    bridge_pass = bool(overlap_frames) and all(
        max(values) <= MAX_BIDIRECTIONAL_DISAGREEMENT_M
        for values in bridge_disagreements.values()
    )
    review_rows: list[dict[str, object]] = []
    records: list[dict[str, object]] = []
    for frame_index in range(lower_seed, upper_seed + 1):
        row = registry.loc[frame_index]
        if frame_index in seed_frames:
            curves = seed_curves[frame_index]
            source = "MANUAL_USER_SEMANTIC_SEED"
            disagreements = {object_type: 0.0 for object_type in BOUNDARIES}
        elif frame_index not in forward and frame_index not in backward:
            review_rows.append(
                {
                    "run_id": "R02ZF",
                    "sar_frame_index": frame_index,
                    "sar_timestamp_ms": int(row.sar_timestamp_ms),
                    "status": "PROPAGATION_AMBIGUOUS",
                    "reason": "BIDIRECTIONAL_PATH_INCOMPLETE",
                    "required_action": "USER_REVIEW_BOUNDARY_IDENTITIES",
                }
            )
            continue
        elif frame_index in forward and frame_index not in backward:
            curves = forward[frame_index]
            source = "FORWARD_FROM_LOWER_MANUAL_SEED_LOCAL_RIDGE_PROPAGATION"
            disagreements = {object_type: None for object_type in BOUNDARIES}
        elif frame_index in backward and frame_index not in forward:
            curves = backward[frame_index]
            source = "BACKWARD_FROM_UPPER_MANUAL_SEED_LOCAL_RIDGE_PROPAGATION"
            disagreements = {object_type: None for object_type in BOUNDARIES}
        else:
            disagreements = {
                object_type: float(np.median(np.abs(forward[frame_index][object_type] - backward[frame_index][object_type])))
                for object_type in BOUNDARIES
            }
            if any(value > MAX_BIDIRECTIONAL_DISAGREEMENT_M for value in disagreements.values()):
                review_rows.append(
                    {
                        "run_id": "R02ZF",
                        "sar_frame_index": frame_index,
                        "sar_timestamp_ms": int(row.sar_timestamp_ms),
                        "status": "PROPAGATION_AMBIGUOUS",
                        "reason": "FORWARD_BACKWARD_RIDGE_DISAGREEMENT",
                        "required_action": "USER_REVIEW_BOUNDARY_IDENTITIES",
                    }
                )
                continue
            curves = {
                object_type: (forward[frame_index][object_type] + backward[frame_index][object_type]) / 2.0
                for object_type in BOUNDARIES
            }
            separation = float(np.median(curves["SAR_BOUNDARY_FAR"] - curves["SAR_BOUNDARY_NEAR"]))
            if separation <= 0 or abs(separation - expected_separation) > MAX_PAIR_SEPARATION_DEVIATION_M:
                review_rows.append(
                    {
                        "run_id": "R02ZF",
                        "sar_frame_index": frame_index,
                        "sar_timestamp_ms": int(row.sar_timestamp_ms),
                        "status": "PROPAGATION_AMBIGUOUS",
                        "reason": "CONSENSUS_PAIR_ORDER_OR_SEPARATION_FAILURE",
                        "required_action": "USER_REVIEW_BOUNDARY_IDENTITIES",
                    }
                )
                continue
            source = "BIDIRECTIONAL_MANUAL_SEED_LOCAL_RIDGE_PROPAGATION"
        pair_separation = float(np.median(curves["SAR_BOUNDARY_FAR"] - curves["SAR_BOUNDARY_NEAR"]))
        for object_type, curve in curves.items():
            forward_info = lookup.get(("FORWARD_FROM_LOWER_SEED", frame_index, object_type), {})
            backward_info = lookup.get(("BACKWARD_FROM_UPPER_SEED", frame_index, object_type), {})
            records.append(
                {
                    "annotation_schema": "R02_PROPAGATED_STATIC_SCENE_ANNOTATION_V1",
                    "run_id": "R02ZF",
                    "sar_frame_index": frame_index,
                    "sar_timestamp_ms": int(row.sar_timestamp_ms),
                    "nominal_optical_frame_index": int(row.nominal_optical_frame_index),
                    "nominal_optical_timestamp_ms": int(row.nominal_optical_timestamp_ms),
                    "sync_status": str(row.sync_status),
                    "modality": "SAR",
                    "object_id": BOUNDARIES[object_type]["object_id"],
                    "object_type": object_type,
                    "geometry_type": "polyline",
                    "points": curve_to_points(theta_grid_deg, curve, row),
                    "theta_grid_deg": [float(value) for value in theta_grid_deg],
                    "d_curve_m": [round(float(value), 6) for value in curve],
                    "d_center_m": float(np.median(curve)),
                    "pair_separation_m": pair_separation,
                    "propagation_status": (
                        "MANUAL_SEED"
                        if frame_index in seed_frames
                        else (
                            "SUPPORTED_BIDIRECTIONAL"
                            if frame_index in forward and frame_index in backward
                            else ("SUPPORTED_FORWARD" if frame_index in forward else "SUPPORTED_BACKWARD")
                        )
                    ),
                    "source": source,
                    "seed_frames": seed_frames,
                    "forward_score": forward_info.get("best_score"),
                    "backward_score": backward_info.get("best_score"),
                    "bidirectional_disagreement_m": disagreements[object_type],
                    "manual_identity_authority": frame_index in seed_frames,
                    "automatic_hint_used_as_identity_authority": False,
                    "person_gt": False,
                    "final_localization": False,
                    "created_at": now_iso(),
                }
            )
    closure: dict[str, dict[str, float | int | bool]] = {}
    for object_type in BOUNDARIES:
        values = bridge_disagreements[object_type]
        closure[object_type] = {
            "overlap_frame_count": len(values),
            "overlap_median_disagreement_m": float(np.median(values)) if values else float("nan"),
            "overlap_max_disagreement_m": float(max(values)) if values else float("nan"),
            "closure_pass": bool(values and max(values) <= MAX_BIDIRECTIONAL_DISAGREEMENT_M),
        }
    OUT.mkdir(parents=True, exist_ok=True)
    PROPAGATED.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
    pd.DataFrame(all_diagnostics).to_csv(DIAGNOSTICS, index=False, encoding="utf-8-sig")
    pd.DataFrame(
        review_rows,
        columns=["run_id", "sar_frame_index", "sar_timestamp_ms", "status", "reason", "required_action"],
    ).to_csv(REVIEW, index=False, encoding="utf-8-sig")
    seed_manifest = {
        "schema": "R02_USER_CONFIRMED_SEED_AUTHORITY_V1",
        "manual_event_path": str(MANUAL_EVENTS),
        "manual_event_sha256": manual_hash_loaded,
        "manual_event_line_count": manual_event_count,
        "user_confirmation_semantics": "THE_TWO_PAIRS_DEFINE_OPTICAL_NEAR_FAR_TO_SAR_NEAR_FAR_IMAGE_SEMANTIC_IDENTITY",
        "draft_seed_acceptance": "EXPLICIT_USER_CONFIRMATION_IN_CURRENT_SESSION",
        "seed_frames": seed_frames,
        "seed_batch_indices": sorted({int(by_frame[frame][name]["batch_index"]) for frame in seed_frames for name in BOUNDARIES}),
        "seed_event_ids": sorted(str(by_frame[frame][name]["event_id"]) for frame in seed_frames for name in BOUNDARIES),
        "manual_jsonl_modified": False,
    }
    SEED_MANIFEST.write_text(json.dumps(seed_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "schema": "R02_MANUAL_SEED_TEMPORAL_PROPAGATION_SUMMARY_V1",
        "status": "PASS" if records and all(item["closure_pass"] for item in closure.values()) else "PARTIAL",
        "seed_frames": seed_frames,
        "bracketed_interval": [lower_seed, upper_seed],
        "theta_corridor_deg": [float(theta_grid_deg.min()), float(theta_grid_deg.max())],
        "theta_node_count": int(len(theta_grid_deg)),
        "expected_manual_pair_separation_m": expected_separation,
        "manual_seed_pair_separations_m": expected_separations,
        "accepted_frame_count": len({int(record["sar_frame_index"]) for record in records}),
        "propagated_record_count": len(records),
        "review_required_frame_count": len(review_rows),
        "review_required_frames": [int(row["sar_frame_index"]) for row in review_rows],
        "forward_stop": forward_stop,
        "backward_stop": backward_stop,
        "bidirectional_overlap_frames": overlap_frames,
        "bidirectional_bridge_pass": bridge_pass,
        "anchor_closure": closure,
        "manual_event_sha256_before": manual_hash_before,
        "manual_event_sha256_after": sha256_file(MANUAL_EVENTS),
        "manual_jsonl_preserved": manual_hash_before == sha256_file(MANUAL_EVENTS),
        "fixed_range_windows_used": False,
        "p0_semantics": "SAR_IMAGE_DOMAIN_COMMON_APPARENT_TRANSLATION_NOT_PHYSICAL_PLATFORM_MOTION",
        "tree_correspondence_run": False,
        "person_experiment_run": False,
        "final_localization_run": False,
        "r04_accessed": False,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    selected = sorted({lower_seed, upper_seed, *np.linspace(lower_seed, upper_seed, 5).round().astype(int).tolist()})
    render_review_strip(records, registry, selected)
    plot_tracks(records, seed_frames)
    report_lines = [
        "# R02 manual-seed temporal propagation report",
        "",
        f"- Manual semantic anchors: SAR F{lower_seed} and F{upper_seed}.",
        f"- Bracketed propagation interval: F{lower_seed}-F{upper_seed}.",
        f"- Accepted frames: {summary['accepted_frame_count']} / {upper_seed - lower_seed + 1}.",
        f"- Review-required frames: {summary['review_required_frames']}.",
        f"- Common manual theta corridor: {summary['theta_corridor_deg']} deg.",
        f"- Manual pair separation reference: {expected_separation:.3f} m.",
        f"- Bidirectional bridge closure: `{json.dumps(closure, ensure_ascii=False)}`.",
        "- Propagation used adjacent local ridge evidence and frozen P0 vertical transport; it did not perform independent fixed-range peak selection.",
        "- Optical annotations supplied semantic identity only. SAR retained image-domain boundary localization authority.",
        "- Propagated records are candidates, not manual annotations, PERSON GT, physical calibration proof, or final localization.",
        "- The append-only manual JSONL was not modified.",
    ]
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    write_manifest()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
