from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference_evaluation_only"
FIG = OUTPUT / "figures"
MASKS = PRE / "full_stream_q95_masks"
RUNS = ("R01ZF", "R02ZF", "R03ZF")
FRAMES_PER_RUN = 495
SAR_FPS = 30.0
OPTICAL_FPS = 18.0
TIMING_UNCERTAINTY_MS = 250
FIXED_LAG_FUTURE_MS = 100
GUARD_DEG = 6.0
SLOPE_DEG_PER_PX = 0.02666536443690682
INTERCEPT_DEG = -45.502258572693094
OPTICAL_WIDTH_PX = 3840.0
P0_SUPPORT_PIXEL_MIN = 1.0

STUDY_TASK = WORKSPACE / "tasks" / "person_physics_guided_image_domain_study_20260824"
P0_SCRIPT = STUDY_TASK / "run_p0_common_apparent_motion.py"
P1E_SCRIPT = STUDY_TASK / "run_p1e_single_frame_position_specificity.py"
CANDIDATE_SCRIPT = STUDY_TASK / "run_p1e_candidate_recall_audit.py"
REGION_SCRIPT = STUDY_TASK / "run_p1e_runtime_track_response_region_minimal.py"
SHELL_SCRIPT = STUDY_TASK / "run_p1e_optical_shell_information_gain.py"
CMR_SCRIPT = WORKSPACE / "tasks" / "person_cmr_d0_common_residual_motion_mechanism_development_20260829" / "run_cmr_d0_development.py"
R1_SCRIPT = WORKSPACE / "tasks" / "person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829" / "run_terg_r1.py"

EXPLORER = WORKSPACE / "output" / "person_multidimensional_response_explorer_20260823" / "explorer_data.js"
SAR_ROOT = WORKSPACE / "output" / "pseudocolor_labelstudio_prep_20260722" / "frames" / "sar_pseudocolor"
OPTICAL = WORKSPACE / "output" / "person_optical_guided_sar_annotation_full_20260823" / "optical_person_frame_hypotheses.parquet"
P1E_ROOT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824" / "p1e_sar_only_response_interface" / "runtime_track_response_region_minimal_v1"
P1E_REGIONS = P1E_ROOT / "response_region_table_pre_reference.csv"
P1E_MASKS = P1E_ROOT / "response_region_masks"
R1_ROOT = WORKSPACE / "output" / "person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829"
R0_ROOT = WORKSPACE / "output" / "person_terg_r0_set_valued_explanation_constraint_propagation_20260829"
V1_ROOT = WORKSPACE / "output" / "person_terg_d0r_set_valued_graph_representation_repair_20260829"
D0_ROOT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824" / "terg_d0_temporal_event_response_graph_mechanism_exploration"

MODES = {
    "CAUSAL_REPLAY": (-TIMING_UNCERTAINTY_MS, 0),
    "FIXED_LAG_100MS": (-TIMING_UNCERTAINTY_MS, FIXED_LAG_FUTURE_MS),
    "FULL_CONTEXT_OFFLINE": (-TIMING_UNCERTAINTY_MS, TIMING_UNCERTAINTY_MS),
}

_WORKER_MODULES: dict[str, Any] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "||".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20].upper()}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_table(frame: pd.DataFrame, path: Path, csv: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path.with_suffix(".parquet"), index=False, compression="zstd")
    if csv:
        frame.to_csv(path.with_suffix(".csv"), index=False, encoding="utf-8-sig")


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_explorer_payload() -> dict[str, Any]:
    text = EXPLORER.read_text(encoding="utf-8")
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


def reconstruct_frames() -> list[dict[str, Any]]:
    payload = load_explorer_payload()
    template: dict[str, dict[str, Any]] = {}
    for row in payload["frames"]:
        run_id = str(row["run_id"])
        if run_id in RUNS and run_id not in template:
            template[run_id] = row
    rows: list[dict[str, Any]] = []
    pattern = re.compile(r"frame_(\d{6})_t(\d{6})ms\.jpg$")
    for run_id in RUNS:
        paths = sorted((SAR_ROOT / run_id).glob("*.jpg"))
        if len(paths) != FRAMES_PER_RUN:
            raise RuntimeError(f"{run_id}: expected {FRAMES_PER_RUN} SAR frames, found {len(paths)}")
        source = template[run_id]
        for path in paths:
            match = pattern.search(path.name)
            if not match:
                raise RuntimeError(path)
            frame_index = int(match.group(1))
            timestamp_ms = int(match.group(2))
            optical_index = round(timestamp_ms * OPTICAL_FPS / 1000.0)
            optical_timestamp = round(optical_index * 1000.0 / OPTICAL_FPS)
            rows.append(
                {
                    "sar_frame_uid": f"{run_id}_SARF{frame_index:06d}",
                    "run_id": run_id,
                    "sar_frame_index": frame_index,
                    "sar_timestamp_ms": timestamp_ms,
                    "sar_image_path": str(path.resolve()),
                    "sar_width_px": int(source["sar_width_px"]),
                    "sar_height_px": int(source["sar_height_px"]),
                    "geometry": dict(source["geometry"]),
                    "theta_low_deg": float(source["theta_low_deg"]),
                    "theta_high_deg": float(source["theta_high_deg"]),
                    "nominal_optical_frame_index": optical_index,
                    "nominal_optical_timestamp_ms": optical_timestamp,
                    "sync_status": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
                }
            )
    return rows


def worker_init() -> None:
    global _WORKER_MODULES
    _WORKER_MODULES = {
        "p1e": load_module(f"r2_p1e_{id(object())}", P1E_SCRIPT),
        "candidate": load_module(f"r2_candidate_{id(object())}", CANDIDATE_SCRIPT),
        "region": load_module(f"r2_region_{id(object())}", REGION_SCRIPT),
    }


def compute_q95_one(frame: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    p1e = _WORKER_MODULES["p1e"]
    candidate = _WORKER_MODULES["candidate"]
    region = _WORKER_MODULES["region"]
    image = cv2.imread(frame["sar_image_path"], cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(frame["sar_image_path"])
    mask, radial, theta, px_per_m = candidate.single_frame_observation_mask(frame, image)
    maps, _ = candidate.compute_existing_candidate_maps_for_mask(p1e, frame, image, mask, radial, theta, px_per_m)
    support_radius_px = max(1, int(round(p1e.PHYSICAL_SUPPORT_RADIUS_M * px_per_m)))
    support_fraction = candidate.support_fraction_map(p1e, mask, support_radius_px)
    evaluation = p1e.build_evaluation_maps(maps, mask, support_radius_px, "fixed_support_mean_v2")
    score = evaluation[region.PRIMARY_CANDIDATE]
    eligible = mask & (support_fraction >= candidate.SUPPORT_TRUNCATED_MIN) & np.isfinite(score)
    percentile = region.percentile_field(score, eligible)
    labels, rows, threshold = region.component_descriptors(
        frame, score, percentile, eligible, support_fraction, radial, theta, px_per_m, 0.95
    )
    MASKS.mkdir(parents=True, exist_ok=True)
    mask_path = MASKS / f"{frame['sar_frame_uid']}.npz"
    np.savez_compressed(
        mask_path,
        Q095=labels,
        levels=np.asarray([0.95], dtype=np.float32),
        numeric_score_thresholds=np.asarray([threshold], dtype=np.float32),
    )
    return rows, {
        "run_id": frame["run_id"],
        "frame_uid": frame["sar_frame_uid"],
        "frame_index": frame["sar_frame_index"],
        "q95_region_count": len(rows),
        "numeric_score_threshold": threshold,
        "mask_path": str(mask_path.relative_to(WORKSPACE)).replace("\\", "/"),
    }


def generate_full_q95(frames: list[dict[str, Any]], workers: int, resume: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    region_path = PRE / "full_stream_q95_response_regions_pre_reference.parquet"
    frame_path = PRE / "full_stream_q95_frame_summary_pre_reference.parquet"
    if resume and region_path.exists() and frame_path.exists() and len(list(MASKS.glob("*.npz"))) == len(frames):
        return pd.read_parquet(region_path), pd.read_parquet(frame_path)
    MASKS.mkdir(parents=True, exist_ok=True)
    all_regions: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=workers, initializer=worker_init) as pool:
        for index, (regions, summary) in enumerate(pool.map(compute_q95_one, frames, chunksize=3), start=1):
            all_regions.extend(regions)
            frame_rows.append(summary)
            if index % 25 == 0 or index == len(frames):
                print(f"full-stream q95 {index}/{len(frames)} | {summary['frame_uid']}", flush=True)
    region_frame = pd.DataFrame(all_regions).sort_values(["run_id", "frame_index", "region_label"]).reset_index(drop=True)
    summary_frame = pd.DataFrame(frame_rows).sort_values(["run_id", "frame_index"]).reset_index(drop=True)
    write_table(region_frame, PRE / "full_stream_q95_response_regions_pre_reference")
    write_table(summary_frame, PRE / "full_stream_q95_frame_summary_pre_reference")
    return region_frame, summary_frame


def validate_q95_parity(regions: pd.DataFrame, frames: list[dict[str, Any]]) -> pd.DataFrame:
    frozen = pd.read_csv(P1E_REGIONS)
    frozen = frozen[frozen["run_id"].isin(RUNS) & frozen["percentile_tag"].eq("Q095")].copy()
    region_counts = regions.groupby("frame_uid").size().to_dict()
    frozen_counts = frozen.groupby("frame_uid").size().to_dict()
    rows: list[dict[str, Any]] = []
    for frame in frames:
        uid = frame["sar_frame_uid"]
        if not (P1E_MASKS / f"{uid}.npz").exists():
            continue
        with np.load(P1E_MASKS / f"{uid}.npz") as old, np.load(MASKS / f"{uid}.npz") as new:
            exact = bool(np.array_equal(old["Q095"], new["Q095"]))
        rows.append(
            {
                "run_id": frame["run_id"],
                "frame_uid": uid,
                "frame_index": frame["sar_frame_index"],
                "frozen_region_count": int(frozen_counts.get(uid, 0)),
                "recomputed_region_count": int(region_counts.get(uid, 0)),
                "region_count_match": int(frozen_counts.get(uid, 0)) == int(region_counts.get(uid, 0)),
                "q95_label_mask_pixel_exact": exact,
                "parity_state": "EXACT" if exact else "MISMATCH",
            }
        )
    parity = pd.DataFrame(rows)
    write_table(parity, PRE / "frozen_coverage_q95_recomputation_parity")
    if parity.empty or not parity["q95_label_mask_pixel_exact"].all():
        raise RuntimeError("full-stream Q95 recomputation failed frozen-coverage pixel parity")
    return parity


def load_optical() -> pd.DataFrame:
    optical = pd.read_parquet(OPTICAL)
    optical = optical[optical["run_id"].isin(RUNS) & optical["box_source"].astype(str).eq("DETECTED")].copy()
    optical["timestamp_ms"] = pd.to_numeric(optical["timestamp_ms"], errors="raise").astype(int)
    optical["track_id"] = optical["raw_track_fragment_id"].astype(str)
    optical["theta_box_low_deg"] = SLOPE_DEG_PER_PX * pd.to_numeric(optical["bbox_x1"]) + INTERCEPT_DEG
    optical["theta_box_high_deg"] = SLOPE_DEG_PER_PX * pd.to_numeric(optical["bbox_x2"]) + INTERCEPT_DEG
    optical["mapped_sar_frame"] = np.rint(optical["timestamp_ms"] * SAR_FPS / 1000.0).astype(int).clip(0, FRAMES_PER_RUN - 1)
    optical["touches_optical_boundary"] = (
        (pd.to_numeric(optical["bbox_x1"]) <= 5)
        | (pd.to_numeric(optical["bbox_x2"]) >= 3835)
        | (pd.to_numeric(optical["bbox_y1"]) <= 5)
        | (pd.to_numeric(optical["bbox_y2"]) >= 2155)
    )
    return optical.sort_values(["run_id", "timestamp_ms", "track_id"]).reset_index(drop=True)


def union_intervals(values: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    items = sorted((min(float(a), float(b)), max(float(a), float(b))) for a, b in values)
    output: list[list[float]] = []
    for low, high in items:
        if not output or low > output[-1][1]:
            output.append([low, high])
        else:
            output[-1][1] = max(output[-1][1], high)
    return [(a, b) for a, b in output]


def intervals_overlap(first: Iterable[tuple[float, float]], second: Iterable[tuple[float, float]]) -> bool:
    return any(max(a, c) <= min(b, d) for a, b in first for c, d in second)


def theta_grid(frame: dict[str, Any]) -> np.ndarray:
    geometry = frame["geometry"]
    yy, xx = np.indices((frame["sar_height_px"], frame["sar_width_px"]), dtype=np.float32)
    return np.degrees(np.arctan2(xx - float(geometry["center_x_px"]), float(geometry["center_y_px"]) - yy))


def build_shell_topology(
    frames: list[dict[str, Any]], regions: pd.DataFrame, optical: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    region_lookup = {
        (str(uid), int(label)): row
        for (uid, label), row in regions.set_index(["frame_uid", "region_label"]).iterrows()
    }
    optical_by_run = {run: group for run, group in optical.groupby("run_id", sort=False)}
    shell_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []
    for index, frame in enumerate(frames, start=1):
        run_id = frame["run_id"]
        query = int(frame["sar_timestamp_ms"])
        run_obs = optical_by_run.get(run_id, pd.DataFrame(columns=optical.columns))
        with np.load(MASKS / f"{frame['sar_frame_uid']}.npz") as archive:
            labels = archive["Q095"]
        grid = theta_grid(frame)
        for mode, (low_offset, high_offset) in MODES.items():
            selected = run_obs[
                (run_obs["timestamp_ms"] >= query + low_offset)
                & (run_obs["timestamp_ms"] <= query + high_offset)
            ]
            mode_edges = 0
            mode_shells = 0
            for track_id, group in selected.groupby("track_id", sort=True):
                raw = [(float(row.theta_box_low_deg) - GUARD_DEG, float(row.theta_box_high_deg) + GUARD_DEG) for row in group.itertuples(index=False)]
                effective = [
                    (max(frame["theta_low_deg"], low), min(frame["theta_high_deg"], high))
                    for low, high in union_intervals(raw)
                    if min(frame["theta_high_deg"], high) >= max(frame["theta_low_deg"], low)
                ]
                effective = union_intervals(effective)
                if not effective:
                    continue
                shell_id = f"{frame['sar_frame_uid']}__{mode}__{track_id}"
                shell_mask = np.zeros(labels.shape, dtype=bool)
                for low, high in effective:
                    shell_mask |= (grid >= low) & (grid <= high)
                selected_labels = labels[shell_mask & (labels > 0)].astype(int)
                active_labels = sorted(set(selected_labels.tolist()))
                mode_shells += 1
                shell_rows.append(
                    {
                        "run_id": run_id,
                        "frame_uid": frame["sar_frame_uid"],
                        "frame_index": frame["sar_frame_index"],
                        "sar_timestamp_ms": query,
                        "mode": mode,
                        "shell_id": shell_id,
                        "track_id": str(track_id),
                        "source_observation_count": len(group),
                        "source_timestamp_min_ms": int(group["timestamp_ms"].min()),
                        "source_timestamp_max_ms": int(group["timestamp_ms"].max()),
                        "source_has_future_observation": bool((group["timestamp_ms"] > query).any()),
                        "source_raw_fragment_ids": ";".join(sorted(set(group["raw_track_fragment_id"].astype(str)))),
                        "effective_intervals_json": json.dumps(effective),
                        "effective_width_deg": float(sum(high - low for low, high in effective)),
                        "candidate_q95_region_count": len(active_labels),
                        "timing_window_low_offset_ms": low_offset,
                        "timing_window_high_offset_ms": high_offset,
                        "manual_reference_used": False,
                        "sar_range_assigned_by_optical": False,
                        "strict_runtime_identity_claimed": False,
                    }
                )
                if len(selected_labels):
                    for label in active_labels:
                        count = int(np.count_nonzero(selected_labels == label))
                        row = region_lookup[(frame["sar_frame_uid"], label)]
                        mode_edges += 1
                        edge_rows.append(
                            {
                                "run_id": run_id,
                                "frame_uid": frame["sar_frame_uid"],
                                "frame_index": frame["sar_frame_index"],
                                "mode": mode,
                                "shell_id": shell_id,
                                "track_id": str(track_id),
                                "region_id": str(row["region_id"]),
                                "region_label": label,
                                "intersection_pixel_count": count,
                                "region_pixel_count": int(row["pixel_count"]),
                                "region_coverage_fraction": count / max(int(row["pixel_count"]), 1),
                                "theta_min_deg": float(row["theta_min_deg"]),
                                "theta_max_deg": float(row["theta_max_deg"]),
                                "range_min_m": float(row["range_min_m"]),
                                "range_max_m": float(row["range_max_m"]),
                                "pixel_intersection_used": True,
                                "edge_semantics": "GT_BLIND_GEOMETRIC_INTERSECTION_NOT_IDENTITY_OR_FINAL_LOCALIZATION",
                            }
                        )
            frame_rows.append(
                {
                    "run_id": run_id,
                    "frame_uid": frame["sar_frame_uid"],
                    "frame_index": frame["sar_frame_index"],
                    "mode": mode,
                    "active_raw_fragment_shell_count": mode_shells,
                    "shell_region_edge_count": mode_edges,
                    "q95_region_count_full_fan": int(np.max(labels)),
                    "negative_optical_time": mode_shells == 0,
                }
            )
        if index % 75 == 0 or index == len(frames):
            print(f"full-stream shell topology {index}/{len(frames)} | {frame['sar_frame_uid']}", flush=True)
    shells = pd.DataFrame(shell_rows)
    edges = pd.DataFrame(edge_rows)
    frame_summary = pd.DataFrame(frame_rows)
    write_table(shells, PRE / "full_stream_optical_shells_pre_reference")
    write_table(edges, PRE / "full_stream_shell_q95_pixel_edges_pre_reference")
    write_table(frame_summary, PRE / "full_stream_frame_observability_pre_reference")
    return shells, edges, frame_summary


def load_p0_authority() -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    cmr = load_module("r2_cmr", CMR_SCRIPT)
    data = cmr.load_authorities()
    models = data["models"]
    metrics = data["metrics"]
    rows: list[dict[str, Any]] = []
    for run_id in RUNS:
        for frame in range(FRAMES_PER_RUN - 1):
            key = (run_id, frame, frame + 1)
            rows.append(
                {
                    "run_id": run_id,
                    "source_sar_frame": frame,
                    "destination_sar_frame": frame + 1,
                    "p0_model_available": key in models,
                    "p0_state": "FROZEN_P0_MODEL_AVAILABLE" if key in models else "SAR_P0_CONTINUITY_INTERFACE_UNAVAILABLE",
                }
            )
    availability = pd.DataFrame(rows)
    write_table(availability, PRE / "full_stream_frozen_p0_availability_pre_reference")
    return models, metrics, availability


def build_p0_edges(
    frames: list[dict[str, Any]], regions: pd.DataFrame, models: dict[str, Any]
) -> pd.DataFrame:
    cmr = load_module("r2_cmr_edges", CMR_SCRIPT)
    frame_map = {(row["run_id"], row["sar_frame_index"]): row for row in frames}
    region_groups = {(run, int(frame)): group for (run, frame), group in regions.groupby(["run_id", "frame_index"])}
    rows: list[dict[str, Any]] = []
    for pair_index, key in enumerate(sorted(k for k in models if k[0] in RUNS), start=1):
        run_id, source_frame, destination_frame = key
        source_meta = frame_map[(run_id, source_frame)]
        destination_meta = frame_map[(run_id, destination_frame)]
        with np.load(MASKS / f"{source_meta['sar_frame_uid']}.npz") as archive:
            source_labels = archive["Q095"]
        with np.load(MASKS / f"{destination_meta['sar_frame_uid']}.npz") as archive:
            destination_labels = archive["Q095"]
        source_regions = region_groups[(run_id, source_frame)].set_index("region_label")
        destination_regions = region_groups[(run_id, destination_frame)].set_index("region_label")
        matrix = cmr.p0_matrix(models[key])
        height, width = source_labels.shape
        for label, source_row in source_regions.iterrows():
            source_mask = source_labels == int(label)
            warped = cv2.warpAffine(
                source_mask.astype(np.float32), matrix, (width, height), flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT, borderValue=0.0,
            )
            destination_candidates = sorted(set(destination_labels[warped > 0].astype(int).tolist()) - {0})
            for destination_label in destination_candidates:
                destination_mask = destination_labels == destination_label
                intersection = float((warped * destination_mask).sum())
                if intersection < P0_SUPPORT_PIXEL_MIN:
                    continue
                destination_row = destination_regions.loc[destination_label]
                rows.append(
                    {
                        "run_id": run_id,
                        "source_sar_frame": source_frame,
                        "destination_sar_frame": destination_frame,
                        "source_region_id": str(source_row["region_id"]),
                        "destination_region_id": str(destination_row["region_id"]),
                        "soft_intersection_px": intersection,
                        "p0_supported_continuation": True,
                        "p0_model": str(models[key]["model"]),
                        "reference_used": False,
                    }
                )
        if pair_index % 25 == 0 or pair_index == len(models):
            print(f"frozen-P0 q95 edges {pair_index}/{len([k for k in models if k[0] in RUNS])} | {run_id} F{source_frame}", flush=True)
    edges = pd.DataFrame(rows)
    if len(edges):
        out_counts = edges.groupby(["run_id", "source_sar_frame", "source_region_id"])["destination_region_id"].transform("nunique")
        in_counts = edges.groupby(["run_id", "destination_sar_frame", "destination_region_id"])["source_region_id"].transform("nunique")
        edges["p0_supported_destination_count"] = out_counts.astype(int)
        edges["p0_supported_source_count"] = in_counts.astype(int)
        edges["sar_topology_state"] = np.select(
            [(out_counts > 1) & (in_counts > 1), out_counts > 1, in_counts > 1],
            ["P0_SPLIT_AND_MERGE_LIKE", "P0_SPLIT_LIKE", "P0_MERGE_LIKE"],
            default="P0_ONE_TO_ONE_LIKE",
        )
    write_table(edges, PRE / "full_stream_available_frozen_p0_q95_edges_pre_reference")
    return edges


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, value: str) -> None:
        self.parent.setdefault(value, value)

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        self.add(left)
        self.add(right)
        a, b = self.find(left), self.find(right)
        if a == b:
            return
        root, other = sorted([a, b])
        self.parent[other] = root


def assign_dynamic_families(shell_edges: pd.DataFrame, p0_edges: pd.DataFrame) -> pd.DataFrame:
    p0_lookup = defaultdict(list)
    for row in p0_edges.itertuples(index=False):
        p0_lookup[(str(row.run_id), int(row.destination_sar_frame))].append((str(row.source_region_id), str(row.destination_region_id)))
    rows: list[dict[str, Any]] = []
    for (run_id, mode, track_id), group in shell_edges.groupby(["run_id", "mode", "track_id"], sort=False):
        available = {(int(row.frame_index), str(row.region_id)) for row in group.itertuples(index=False)}
        if mode == "FULL_CONTEXT_OFFLINE":
            graph = nx.Graph()
            graph.add_nodes_from(f"{frame}|{region}" for frame, region in available)
            for frame, region in available:
                for source, destination in p0_lookup.get((run_id, frame), []):
                    if destination == region and (frame - 1, source) in available:
                        graph.add_edge(f"{frame-1}|{source}", f"{frame}|{region}")
            component_of: dict[str, str] = {}
            for component in nx.connected_components(graph):
                family = stable_id("TERGR2F", run_id, mode, track_id, min(component))
                for node in component:
                    component_of[node] = family
            for frame, region in sorted(available):
                rows.append({"run_id": run_id, "mode": mode, "track_id": track_id, "frame_index": frame, "region_id": region, "family_id": component_of[f"{frame}|{region}"], "family_temporal_semantics": "FULL_CONTEXT_RUNTIME_LEGAL_OBSERVATION_SMOOTHING"})
        else:
            uf = UnionFind()
            by_frame = defaultdict(list)
            for frame, region in available:
                by_frame[frame].append(region)
            for frame in sorted(by_frame):
                for region in by_frame[frame]:
                    uf.add(f"{frame}|{region}")
                for source, destination in p0_lookup.get((run_id, frame), []):
                    if destination in by_frame[frame] and source in by_frame.get(frame - 1, []):
                        uf.union(f"{frame-1}|{source}", f"{frame}|{destination}")
                for region in by_frame[frame]:
                    root = uf.find(f"{frame}|{region}")
                    rows.append({"run_id": run_id, "mode": mode, "track_id": track_id, "frame_index": frame, "region_id": region, "family_id": stable_id("TERGR2F", run_id, mode, track_id, root), "family_temporal_semantics": "CAUSAL_PREFIX_FROZEN_P0_CONNECTIVITY"})
    memberships = pd.DataFrame(rows)
    write_table(memberships, PRE / "runtime_candidate_family_membership_pre_reference")
    return memberships


def reentry_candidates(optical: pd.DataFrame) -> dict[tuple[str, str], list[str]]:
    result: dict[tuple[str, str], list[str]] = {}
    for run_id, run in optical.groupby("run_id"):
        summary = []
        for track_id, group in run.groupby("track_id"):
            ordered = group.sort_values("timestamp_ms")
            first, last = ordered.iloc[0], ordered.iloc[-1]
            summary.append(
                {
                    "track_id": str(track_id),
                    "first_ts": int(first.timestamp_ms),
                    "last_ts": int(last.timestamp_ms),
                    "first_interval": [(float(first.theta_box_low_deg) - GUARD_DEG, float(first.theta_box_high_deg) + GUARD_DEG)],
                    "last_interval": [(float(last.theta_box_low_deg) - GUARD_DEG, float(last.theta_box_high_deg) + GUARD_DEG)],
                }
            )
        for current in summary:
            candidates = [
                old["track_id"]
                for old in summary
                if old["last_ts"] < current["first_ts"] and intervals_overlap(old["last_interval"], current["first_interval"])
            ]
            result[(run_id, current["track_id"])] = sorted(candidates)
    return result


def build_lifecycle(
    optical: pd.DataFrame,
    shells: pd.DataFrame,
    shell_edges: pd.DataFrame,
    memberships: pd.DataFrame,
    p0_availability: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    family_by_key = memberships.groupby(["run_id", "mode", "track_id", "frame_index"])["family_id"].agg(lambda values: sorted(set(values.astype(str)))).to_dict()
    regions_by_key = shell_edges.groupby(["run_id", "mode", "track_id", "frame_index"])["region_id"].agg(lambda values: sorted(set(values.astype(str)))).to_dict()
    shell_by_key = shells.set_index(["run_id", "mode", "track_id", "frame_index"])["effective_intervals_json"].to_dict()
    p0_lookup = p0_availability.set_index(["run_id", "destination_sar_frame"])["p0_model_available"].to_dict()
    reentry = reentry_candidates(optical)
    rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    hypotheses: list[dict[str, Any]] = []
    for (run_id, track_id), group in optical.groupby(["run_id", "track_id"], sort=False):
        group = group.sort_values("timestamp_ms")
        first_frame = int(group["mapped_sar_frame"].min())
        last_frame = int(group["mapped_sar_frame"].max())
        total_observations = int(len(group))
        boundary_first = bool(group.iloc[0]["touches_optical_boundary"])
        boundary_last = bool(group.iloc[-1]["touches_optical_boundary"])
        competing = reentry.get((run_id, track_id), [])
        hypothesis_id = stable_id("TERGR2H", run_id, track_id)
        hypotheses.append(
            {
                "hypothesis_id": hypothesis_id,
                "run_id": run_id,
                "runtime_optical_fragment_id": track_id,
                "optical_support_set": ";".join(str(int(value)) for value in sorted(group["frame_index"].unique())),
                "first_optical_timestamp_ms": int(group["timestamp_ms"].min()),
                "last_optical_timestamp_ms": int(group["timestamp_ms"].max()),
                "first_sar_frame": first_frame,
                "last_sar_frame": last_frame,
                "detected_observation_count": total_observations,
                "reentry_candidate_old_hypothesis_fragments": ";".join(competing),
                "new_identity_competitor_retained": bool(competing),
                "raw_fragment_is_person_truth": False,
                "cross_modal_identity_committed": False,
                "provenance": "AUTOMATIC_OPTICAL_TRACKLET_REPLAY_CLOSEST_AVAILABLE_RUNTIME_PROXY",
            }
        )
        for mode in MODES:
            previous_state = "UNSEEN"
            last_families: list[str] = []
            last_regions: list[str] = []
            for frame in range(first_frame, FRAMES_PER_RUN):
                timestamp = round(frame * 1000.0 / SAR_FPS)
                visible = group[group["mapped_sar_frame"].eq(frame)]
                if mode == "CAUSAL_REPLAY":
                    accessible = group[group["timestamp_ms"] <= timestamp]
                elif mode == "FIXED_LAG_100MS":
                    accessible = group[group["timestamp_ms"] <= timestamp + FIXED_LAG_FUTURE_MS]
                else:
                    accessible = group
                families = family_by_key.get((run_id, mode, track_id, frame), [])
                physical_regions = regions_by_key.get((run_id, mode, track_id, frame), [])
                if families:
                    last_families = families
                if physical_regions:
                    last_regions = physical_regions
                p0_available = bool(p0_lookup.get((run_id, frame), False))
                if frame <= last_frame:
                    repeated_available = len(accessible) >= 2
                    if not repeated_available:
                        state = "ADMISSION_PENDING"
                        support = "FIRST_FRAGMENT_OBSERVATION_ONLY"
                    elif len(families) == 1 and p0_available:
                        state = "ACTIVE"
                        support = "REPEATED_OPTICAL_CONTINUITY_AND_ONE_PREFIX_P0_FAMILY"
                    elif len(physical_regions) == 0:
                        state = "ACTIVE_AMBIGUOUS"
                        support = "OPTICAL_CONTINUITY_WITH_EMPTY_CURRENT_SHELL_REGION_SET_SYNC_OR_INTERFACE_CONFLICT_PRESERVED"
                    elif not p0_available:
                        state = "ACTIVE_AMBIGUOUS"
                        support = "OPTICAL_CONTINUITY_BUT_SAR_P0_CONTINUITY_INTERFACE_UNAVAILABLE"
                    else:
                        state = "ACTIVE_AMBIGUOUS"
                        support = "MULTIPLE_RUNTIME_LEGAL_SAR_EXPLANATION_FAMILIES"
                else:
                    if boundary_last:
                        state = "CENSORED_AT_BOUNDARY"
                        support = "LAST_OPTICAL_OBSERVATION_TOUCHES_BOUNDARY_DIRECTION_OF_CROSSING_UNRESOLVED"
                    else:
                        state = "DORMANT"
                        support = "RAW_FRAGMENT_ENDED_WITHOUT_SEMANTIC_PHYSICAL_CLOSURE"
                if frame == FRAMES_PER_RUN - 1 and state in {"ACTIVE", "ACTIVE_AMBIGUOUS", "DORMANT", "ADMISSION_PENDING"}:
                    state = "CENSORED_AT_STREAM_END"
                    support = "RUN_ENDED_BEFORE_SEMANTIC_CLOSURE"
                if state != previous_state:
                    event_rows.append(
                        {
                            "event_id": stable_id("TERGR2E", hypothesis_id, mode, frame, state),
                            "run_id": run_id,
                            "mode": mode,
                            "frame_index": frame,
                            "hypothesis_id": hypothesis_id,
                            "runtime_optical_fragment_id": track_id,
                            "previous_state": previous_state,
                            "new_state": state,
                            "transition_evidence": support,
                            "segment_generated_from_stream": True,
                        }
                    )
                current_intervals = shell_by_key.get((run_id, mode, track_id, frame), "[]")
                rows.append(
                    {
                        "run_id": run_id,
                        "mode": mode,
                        "frame_index": frame,
                        "sar_timestamp_ms": timestamp,
                        "hypothesis_id": hypothesis_id,
                        "runtime_optical_fragment_id": track_id,
                        "lifecycle_state": state,
                        "current_optical_state": "OBSERVED" if len(visible) else "NOT_OBSERVED_AT_CURRENT_FRAME",
                        "accessible_optical_observation_count": int(len(accessible)),
                        "candidate_sar_family_set": ";".join(families or last_families),
                        "candidate_sar_family_count": len(families or last_families),
                        "candidate_physical_region_set": ";".join(physical_regions or last_regions),
                        "candidate_physical_region_count": len(physical_regions or last_regions),
                        "current_shell_intervals_json": current_intervals,
                        "sar_q95_interface_state": "FULL_STREAM_RECOMPUTED_PIXEL_EXACT_ON_FROZEN_COVERAGE",
                        "sar_p0_interface_state": "FROZEN_P0_MODEL_AVAILABLE" if p0_available else "SAR_P0_CONTINUITY_INTERFACE_UNAVAILABLE",
                        "anchor_state": "ANCHOR_NOT_YET_AUDITED",
                        "uncertainty_state": support,
                        "reentry_candidate_fragments": ";".join(competing),
                        "new_identity_competitor_retained": bool(competing),
                        "closure_condition_satisfied": False,
                        "person_identity_truth_claimed": False,
                        "final_localization_claimed": False,
                    }
                )
                previous_state = state
    lifecycle = pd.DataFrame(rows)
    events = pd.DataFrame(event_rows)
    hypotheses_frame = pd.DataFrame(hypotheses)
    write_table(hypotheses_frame, PRE / "stream_hypothesis_object_registry_pre_reference")
    write_table(lifecycle, PRE / "full_stream_hypothesis_lifecycle_pre_reference")
    write_table(events, PRE / "automatically_generated_reasoning_intervals_pre_reference")
    return hypotheses_frame, lifecycle, events


def no_optical_control_counts(
    run_id: str, intervals: list[list[float]], mode: str, frame_summary: pd.DataFrame, regions: pd.DataFrame
) -> tuple[int, int]:
    negative = frame_summary[(frame_summary["run_id"].eq(run_id)) & (frame_summary["mode"].eq(mode)) & frame_summary["negative_optical_time"]]
    region_run = regions[regions["run_id"].eq(run_id)]
    singleton = 0
    any_response = 0
    for frame in negative["frame_index"].astype(int):
        part = region_run[region_run["frame_index"].eq(frame)]
        count = 0
        for row in part.itertuples(index=False):
            if intervals_overlap(intervals, [(float(row.theta_min_deg), float(row.theta_max_deg))]):
                count += 1
        singleton += int(count == 1)
        any_response += int(count > 0)
    return singleton, any_response


def audit_anchors(
    lifecycle: pd.DataFrame,
    shells: pd.DataFrame,
    frame_summary: pd.DataFrame,
    regions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    active_counts = lifecycle[lifecycle["lifecycle_state"].isin(["ACTIVE", "ACTIVE_AMBIGUOUS"])].groupby(["run_id", "mode", "frame_index"])["hypothesis_id"].nunique().to_dict()
    shell_lookup = shells.set_index(["run_id", "mode", "track_id", "frame_index"])["effective_intervals_json"].to_dict()
    rows: list[dict[str, Any]] = []
    for row in lifecycle.itertuples(index=False):
        if row.lifecycle_state not in {"ACTIVE", "ACTIVE_AMBIGUOUS"}:
            continue
        singleton_optical = active_counts.get((row.run_id, row.mode, int(row.frame_index)), 0) == 1
        intervals_text = shell_lookup.get((row.run_id, row.mode, row.runtime_optical_fragment_id, int(row.frame_index)), "[]")
        intervals = json.loads(intervals_text)
        if not singleton_optical:
            status = "REJECTED_ANCHOR"
            reason = "MULTIPLE_ACTIVE_OPTICAL_HYPOTHESES"
            control_singleton = 0
            control_any = 0
        elif row.sar_p0_interface_state != "FROZEN_P0_MODEL_AVAILABLE":
            status = "REJECTED_ANCHOR"
            reason = "SAR_P0_CONTINUITY_INTERFACE_UNAVAILABLE"
            control_singleton = 0
            control_any = 0
        elif int(row.candidate_sar_family_count) != 1 or int(row.candidate_physical_region_count) != 1:
            status = "REJECTED_ANCHOR"
            reason = "NATURAL_LOW_AMBIGUITY_NOT_REACHED"
            control_singleton = 0
            control_any = 0
        else:
            control_singleton, control_any = no_optical_control_counts(row.run_id, intervals, row.mode, frame_summary, regions)
            if control_singleton > 0:
                status = "AMBIGUOUS_ANCHOR"
                reason = "SINGLETON_Q95_EXPLANATION_ALSO_OCCURS_IN_NO_OPTICAL_CONTROL_TIME"
            else:
                status = "CANDIDATE_ANCHOR"
                reason = "SINGLETON_P0_FAMILY_WITHOUT_INDEPENDENT_RANGE_OR_IDENTITY_CORROBORATION"
        rows.append(
            {
                "run_id": row.run_id,
                "mode": row.mode,
                "frame_index": int(row.frame_index),
                "hypothesis_id": row.hypothesis_id,
                "runtime_optical_fragment_id": row.runtime_optical_fragment_id,
                "active_optical_hypothesis_count": active_counts.get((row.run_id, row.mode, int(row.frame_index)), 0),
                "candidate_sar_family_count": int(row.candidate_sar_family_count),
                "candidate_physical_region_count": int(row.candidate_physical_region_count),
                "anchor_status": status,
                "anchor_reason": reason,
                "no_optical_control_frame_with_one_q95_region_in_same_corridor_count": control_singleton,
                "no_optical_control_frame_with_any_q95_region_in_same_corridor_count": control_any,
                "independent_runtime_range_support_available": False,
                "confirmed_cross_modal_identity_claimed": False,
            }
        )
    anchor = pd.DataFrame(rows)
    lifecycle_key = ["run_id", "mode", "frame_index", "hypothesis_id"]
    anchor_state = anchor[lifecycle_key + ["anchor_status"]].drop_duplicates(lifecycle_key)
    updated = lifecycle.merge(anchor_state, on=lifecycle_key, how="left")
    updated["anchor_state"] = updated["anchor_status"].fillna("ANCHOR_INACTIVE_OR_NOT_APPLICABLE")
    updated = updated.drop(columns=["anchor_status"])
    write_table(anchor, PRE / "runtime_unary_anchor_hypothesis_ledger_pre_reference")
    write_table(updated, PRE / "full_stream_hypothesis_lifecycle_with_anchor_state_pre_reference")
    return anchor, updated


def r1_visual_ledger() -> pd.DataFrame:
    old = pd.read_csv(R1_ROOT / "post_reference" / "direct_visual_verification_verdict_post_reference.csv")
    verdicts = {
        "strongest_A_SUPPORT_1": ("VISIBLE_OPPOSITE_ANGULAR_ORDER_SINGLE_FRAME", "LOCAL_ONLY", "LOW", "The two rendered SAR contours are angularly reversed relative to the optical pair, but one frame cannot establish persistence."),
        "strongest_B_SUPPORT_2": ("VISIBLE_OPPOSITE_ANGULAR_ORDER_BOTH_FRAMES", "LOCAL_TWO_FRAME", "LOW_TO_MODERATE", "Both frames show the same reversed angular order; the cyan region changes shape and the support remains short."),
        "strongest_C_SUPPORT_AT_LEAST_5": ("VISIBLE_PERSISTENT_OPPOSITE_ANGULAR_ORDER", "PERSISTENT_FIVE_FRAME", "MODERATE", "Across F490-F494 the separated cyan/orange contours preserve the reverse angular order despite q95 morphology changes."),
        "strongest_D_LONGEST_SUPPORT": ("VISIBLE_PERSISTENT_OPPOSITE_ANGULAR_ORDER", "PERSISTENT_FIVE_FRAME", "MODERATE_TO_HIGH", "Across F490-F494 both contours remain visibly separated with stable reverse angular order."),
        "strongest_E_LIKELY_VS_EXCLUDED_ALTERNATIVE": ("VISIBLE_OPPOSITE_ANGULAR_ORDER_SINGLE_FRAME", "LOCAL_ONLY", "LOW", "The displayed frame shows the computed reverse order, but this post-reference selected case is one-frame and not persistent evidence."),
        "five_track_A_SUPPORT_1": ("VISIBLE_OPPOSITE_ANGULAR_ORDER_SINGLE_FRAME", "LOCAL_ONLY", "LOW", "The two small contours are visibly reversed in one frame only."),
        "five_track_B_SUPPORT_2": ("VISIBLE_OPPOSITE_ANGULAR_ORDER_BOTH_FRAMES", "LOCAL_TWO_FRAME", "LOW_TO_MODERATE", "Both frames preserve reverse order, but the tiny q95 regions make physical interpretation fragile."),
        "five_track_C_SUPPORT_AT_LEAST_5": ("VISIBLE_PERSISTENT_OPPOSITE_ANGULAR_ORDER", "PERSISTENT_EIGHT_FRAME", "MODERATE_TO_HIGH", "F487-F494 consistently show the cyan contour angularly to the right of the orange contour."),
        "five_track_D_LONGEST_SUPPORT": ("VISIBLE_PERSISTENT_OPPOSITE_ANGULAR_ORDER", "PERSISTENT_EIGHT_FRAME", "MODERATE", "F487-F494 preserve reverse order; contour size changes do not reverse the ordering."),
        "five_track_E_LIKELY_VS_EXCLUDED_ALTERNATIVE": ("VISIBLE_PERSISTENT_ORDER_WITH_MAJOR_MORPHOLOGY_DEFORMATION", "PERSISTENT_EIGHT_FRAME_QUALIFIED", "LOW_TO_MODERATE", "The angular interval order persists, but the cyan q95 contour expands and deforms strongly; this is not stable physical-object identity evidence."),
    }
    rows: list[dict[str, Any]] = []
    for item in old.itertuples(index=False):
        verdict, extent, confidence, note = verdicts[str(item.case_id)]
        rows.append(
            {
                "case_id": item.case_id,
                "figure_path": item.figure_path,
                "common_sar_support_frame_count": int(item.common_sar_support_frame_count),
                "computed_geometric_verdict": "RELATIVE_ANGULAR_ORDER_CONTRADICTION",
                "independent_visual_review_verdict": verdict,
                "independent_visual_support_extent": extent,
                "independent_visual_confidence": confidence,
                "q95_fragmentation_or_deformation_concern": "MATERIAL" if "E_LIKELY" in str(item.case_id) or "SUPPORT_1" in str(item.case_id) else "PRESENT_BUT_ORDER_SURVIVES",
                "review_note": note,
                "review_source": "DIRECT_IMAGE_INSPECTION_2026_08_30_NOT_DERIVED_FROM_SUPPORT_COUNT",
                "relative_order_primitive_freeze_supported": verdict.startswith("VISIBLE_PERSISTENT"),
            }
        )
    ledger = pd.DataFrame(rows)
    write_table(ledger, PRE / "r1_independent_visual_review_ledger_correction")
    return ledger


def r1_specific_likely_retention() -> tuple[pd.DataFrame, pd.DataFrame]:
    r1 = load_module("r2_r1_correction", R1_SCRIPT)
    data = r1.load_pre_reference_inputs()
    post = r1.load_post_reference_inputs()
    likely = post["grounding"][post["grounding"]["component_grounding_state"].eq("LIKELY_SUPPORTED_EXPLORATORY")]
    unique = likely.groupby(["segment_id", "track_id"]).filter(lambda rows: len(rows) == 1).set_index(["segment_id", "track_id"])["family_id"].astype(str).to_dict()
    one_old = pd.read_csv(R1_ROOT / "post_reference" / "one_anchor_propagation_capacity_post_reference.csv")
    two_old = pd.read_csv(R1_ROOT / "post_reference" / "two_anchor_propagation_capacity_post_reference.csv")

    def specific(segment_id: str, anchors: dict[str, str]) -> tuple[bool, str]:
        tracks, domains, mask = r1.construct_world_mask(segment_id, data["family_status"], data["pair"])
        conditioned = mask.copy()
        for track, family in anchors.items():
            keep = np.zeros(len(domains[track]), dtype=bool)
            keep[domains[track].index(family)] = True
            shape = [1] * len(tracks)
            shape[tracks.index(track)] = len(keep)
            conditioned &= keep.reshape(shape)
        details = []
        retained = True
        for track in tracks:
            if track in anchors or (segment_id, track) not in unique:
                continue
            family = unique[(segment_id, track)]
            index = domains[track].index(family)
            select = np.zeros(len(domains[track]), dtype=bool)
            select[index] = True
            shape = [1] * len(tracks)
            shape[tracks.index(track)] = len(select)
            exists = bool(np.any(conditioned & select.reshape(shape)))
            retained &= exists
            details.append(f"{track}:{family}:{'RETAINED' if exists else 'DELETED'}")
        return retained, ";".join(details)

    one = one_old.copy()
    values = [specific(str(row.segment_id), {str(row.anchor_track): str(row.anchor_family)}) for row in one.itertuples(index=False)]
    one["specific_likely_family_retained"] = [value[0] for value in values]
    one["specific_likely_family_retention_detail"] = [value[1] for value in values]
    one["corrected_semantics"] = "SPECIFIC_LIKELY_FAMILY_RETAINED_NOT_DOMAIN_NONEMPTY"
    two = two_old.copy()
    values = [specific(str(row.segment_id), {str(row.anchor_track_a): str(row.anchor_family_a), str(row.anchor_track_b): str(row.anchor_family_b)}) for row in two.itertuples(index=False)]
    two["specific_likely_family_retained"] = [value[0] for value in values]
    two["specific_likely_family_retention_detail"] = [value[1] for value in values]
    two["corrected_semantics"] = "SPECIFIC_LIKELY_FAMILY_RETAINED_NOT_DOMAIN_NONEMPTY"
    write_table(one, POST / "r1_one_anchor_specific_likely_family_retention_correction")
    write_table(two, POST / "r1_two_anchor_specific_likely_family_retention_correction")
    return one, two


def temporal_overlap_cluster_correction() -> tuple[pd.DataFrame, pd.DataFrame]:
    old_cluster = pd.read_csv(R1_ROOT / "pre_reference" / "underlying_temporal_episode_registry_pre_reference.csv")
    old_assignment = pd.read_csv(R1_ROOT / "pre_reference" / "episode_assignment_pre_reference.csv")
    cluster = old_cluster.rename(columns={column: column.replace("episode", "temporal_overlap_cluster") for column in old_cluster.columns})
    assignment = old_assignment.rename(columns={column: column.replace("episode", "temporal_overlap_cluster") for column in old_assignment.columns})
    cluster["cluster_semantics"] = "INTERVAL_OVERLAP_CONNECTED_COMPONENT_NOT_INDEPENDENT_PHYSICAL_EPISODE"
    assignment["cluster_semantics"] = "OVERLAPPING_SEGMENT_VIEW_MEMBERSHIP"
    write_table(cluster, PRE / "r1_temporal_overlap_cluster_registry_correction")
    write_table(assignment, PRE / "r1_temporal_overlap_cluster_assignment_correction")
    return cluster, assignment


def negative_time_audit(
    frame_summary: pd.DataFrame,
    lifecycle: pd.DataFrame,
    events: pd.DataFrame,
    optical: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (run_id, mode), frames in frame_summary.groupby(["run_id", "mode"]):
        negative_frames = set(frames.loc[frames["negative_optical_time"], "frame_index"].astype(int))
        non_dormant = lifecycle[
            lifecycle["run_id"].eq(run_id)
            & lifecycle["mode"].eq(mode)
            & lifecycle["lifecycle_state"].isin(["ACTIVE", "ACTIVE_AMBIGUOUS", "ADMISSION_PENDING"])
        ]
        negative_non_dormant_frames = sorted(negative_frames & set(non_dormant["frame_index"].astype(int)))
        admission_events = events[
            events["run_id"].eq(run_id)
            & events["mode"].eq(mode)
            & events["new_state"].eq("ADMISSION_PENDING")
        ].copy()
        run_opt = optical[optical["run_id"].eq(run_id)]
        first_frame_by_fragment = run_opt.groupby("track_id")["mapped_sar_frame"].min().astype(int).to_dict()
        admission_events["first_fragment_frame"] = admission_events["runtime_optical_fragment_id"].map(first_frame_by_fragment)
        sar_only_open = admission_events[
            admission_events["first_fragment_frame"].isna()
            | (admission_events["frame_index"].astype(int) < admission_events["first_fragment_frame"].astype(float))
        ]
        false_admission_frames = sorted(set(sar_only_open["frame_index"].astype(int)))
        first = int(run_opt["mapped_sar_frame"].min()) if len(run_opt) else FRAMES_PER_RUN
        last = int(run_opt["mapped_sar_frame"].max()) if len(run_opt) else -1
        rows.append(
            {
                "run_id": run_id,
                "mode": mode,
                "stream_frame_count": FRAMES_PER_RUN,
                "negative_optical_frame_count": len(negative_frames),
                "pre_first_optical_frame_count": first,
                "post_last_optical_frame_count": FRAMES_PER_RUN - last - 1,
                "admission_open_event_count": int(len(admission_events)),
                "optical_triggered_admission_event_count": int(len(admission_events) - len(sar_only_open)),
                "structural_sar_only_false_admission_event_count": int(len(sar_only_open)),
                "structural_sar_only_false_admission_frame_count": len(false_admission_frames),
                "structural_sar_only_false_admission_frames": ";".join(map(str, false_admission_frames)),
                "negative_time_non_dormant_hypothesis_frame_count": len(negative_non_dormant_frames),
                "negative_time_non_dormant_hypothesis_frames": ";".join(map(str, negative_non_dormant_frames)),
                "sar_clutter_used_to_open_hypothesis": False,
                "negative_time_semantics": "ADMISSION EVENTS ARE AUDITED SEPARATELY FROM PREVIOUSLY OPTICAL-TRIGGERED HYPOTHESES RETAINED ON LOCAL NO-SHELL FRAMES; THIS IS A STRUCTURAL CONTROL NOT PERSON-GT ACCURACY",
            }
        )
    audit = pd.DataFrame(rows)
    write_table(audit, PRE / "negative_time_no_optical_admission_audit_pre_reference")
    return audit


def exploratory_event_metrics(hypotheses: pd.DataFrame, optical: pd.DataFrame) -> pd.DataFrame:
    # Full-run stitched identifiers are used only here, after runtime products exist.
    parent = optical.groupby(["run_id", "track_id"])["optical_person_id"].agg(lambda values: sorted(set(values.astype(str)))).to_dict()
    rows: list[dict[str, Any]] = []
    for run_id, run in hypotheses.groupby("run_id"):
        duplicate_groups = defaultdict(list)
        for row in run.itertuples(index=False):
            for value in parent.get((run_id, row.runtime_optical_fragment_id), []):
                duplicate_groups[value].append(row.runtime_optical_fragment_id)
        rows.append(
            {
                "run_id": run_id,
                "evaluation_scope": "EXPLORATORY_GT_BLIND_FULL_RUN_STITCH_PROXY_ONLY",
                "runtime_hypothesis_count": len(run),
                "offline_parent_proxy_count": len(duplicate_groups),
                "offline_parent_with_multiple_raw_hypotheses_count": sum(len(set(values)) > 1 for values in duplicate_groups.values()),
                "max_raw_hypotheses_per_offline_parent": max((len(set(values)) for values in duplicate_groups.values()), default=0),
                "runtime_reentry_identity_resolution_count": 0,
                "identity_contamination_strict_metric_available": False,
                "strict_person_gt_available": False,
            }
        )
    metrics = pd.DataFrame(rows)
    write_table(metrics, POST / "exploratory_event_metrics_offline_proxy_only")
    return metrics


def anchor_source_audit(anchor: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "anchor_source_class": "AUTO_RUNTIME_ANCHOR",
            "runtime_use_allowed": True,
            "candidate_count": int(anchor["anchor_status"].eq("CANDIDATE_ANCHOR").sum()),
            "strong_count": int(anchor["anchor_status"].eq("STRONG_ANCHOR").sum()),
            "current_state": "NO_STRONG_AUTO_RUNTIME_ANCHOR_ESTABLISHED",
            "limitation": "Singleton shell-family moments lack independent range/identity corroboration and are challenged by no-optical clutter controls.",
        },
        {
            "anchor_source_class": "CALIBRATED_PHYSICAL_ANCHOR",
            "runtime_use_allowed": True,
            "candidate_count": 0,
            "strong_count": 0,
            "current_state": "UNAVAILABLE",
            "limitation": "No runtime-legal camera footpoint to SAR range interval, mounting/ground-plane range calibration, or platform-pose range interface was found in the frozen inputs.",
        },
        {
            "anchor_source_class": "SPARSE_MANUAL_ANCHOR",
            "runtime_use_allowed": True,
            "candidate_count": 0,
            "strong_count": 0,
            "current_state": "DIAGNOSTIC_ONLY_NOT_INJECTED_IN_AUTOMATIC_REPLAY",
            "limitation": "Evaluated as a counterfactual information requirement, not silently used as runtime evidence.",
        },
        {
            "anchor_source_class": "OFFLINE_REFERENCE_ANCHOR",
            "runtime_use_allowed": False,
            "candidate_count": 0,
            "strong_count": 0,
            "current_state": "POST_REFERENCE_EVALUATION_ONLY",
            "limitation": "Never used in full-stream replay or admission/lifecycle construction.",
        },
    ]
    frame = pd.DataFrame(rows)
    write_table(frame, PRE / "runtime_anchor_source_registry_pre_reference")
    return frame


def sparse_anchor_diagnostic(one: pd.DataFrame, two: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label, table, anchor_count in [("ONE_SPARSE_ANCHOR", one, 1), ("TWO_SPARSE_ANCHORS", two, 2)]:
        for segment_id, group in table.groupby("segment_id"):
            deleted = pd.to_numeric(group["other_track_family_deleted_count"], errors="coerce")
            rows.append(
                {
                    "segment_id": segment_id,
                    "diagnostic_mode": label,
                    "anchor_count": anchor_count,
                    "tested_anchor_configuration_count": len(group),
                    "configuration_with_any_other_domain_contraction_count": int((deleted > 0).sum()),
                    "max_other_family_deleted_count": int(deleted.max()) if len(deleted) else 0,
                    "all_specific_likely_families_retained_fraction": float(group["specific_likely_family_retained"].mean()) if len(group) else math.nan,
                    "anchor_source_semantics": "OFFLINE_LIKELY_FAMILY_STAND_IN_FOR_SPARSE_INFORMATION_REQUIREMENT_ONLY",
                    "runtime_result": False,
                }
            )
    frame = pd.DataFrame(rows)
    write_table(frame, POST / "sparse_anchor_requirement_diagnostic")
    return frame


def failure_root_diagnosis(
    anchor: pd.DataFrame, p0_availability: pd.DataFrame, lifecycle: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    p0_fraction = p0_availability.groupby("run_id")["p0_model_available"].mean().to_dict()
    for run_id in RUNS:
        run_anchor = anchor[(anchor["run_id"].eq(run_id)) & anchor["mode"].eq("CAUSAL_REPLAY")]
        run_life = lifecycle[(lifecycle["run_id"].eq(run_id)) & lifecycle["mode"].eq("CAUSAL_REPLAY")]
        reasons = Counter(run_anchor["anchor_reason"].astype(str))
        rows.extend(
            [
                {
                    "run_id": run_id,
                    "failure_root": "INCOMPLETE_FROZEN_P0_CONTINUITY_COVERAGE",
                    "observed": p0_fraction.get(run_id, 0.0) < 1.0,
                    "evidence": f"available consecutive-frame fraction={p0_fraction.get(run_id, 0.0):.4f}",
                    "classification": "DEPLOYED_RUNTIME_INTERFACE_GAP",
                },
                {
                    "run_id": run_id,
                    "failure_root": "NATURAL_SINGLETON_FAMILY_NOT_REACHED",
                    "observed": reasons.get("NATURAL_LOW_AMBIGUITY_NOT_REACHED", 0) > 0,
                    "evidence": f"rejected active rows={reasons.get('NATURAL_LOW_AMBIGUITY_NOT_REACHED', 0)}",
                    "classification": "SAR_CLUTTER_OR_CORRIDOR_AMBIGUITY",
                },
                {
                    "run_id": run_id,
                    "failure_root": "NO_RUNTIME_RANGE_GROUNDING",
                    "observed": True,
                    "evidence": "optical interface supplies azimuth corridor only; no calibrated r interval is present",
                    "classification": "MISSING_PHYSICAL_OBSERVABLE",
                },
                {
                    "run_id": run_id,
                    "failure_root": "RAW_FRAGMENT_IDENTITY_FRAGMENTATION",
                    "observed": run_life["new_identity_competitor_retained"].any(),
                    "evidence": f"rows retaining reentry/new-identity competition={int(run_life['new_identity_competitor_retained'].sum())}",
                    "classification": "RUNTIME_HYPOTHESIS_AMBIGUITY",
                },
                {
                    "run_id": run_id,
                    "failure_root": "TRUE_SEMANTIC_CLOSURE_UNOBSERVABLE",
                    "observed": not run_life["closure_condition_satisfied"].any(),
                    "evidence": "fragment end/boundary contact does not reveal exit direction or physical continuation emptiness",
                    "classification": "MISSING_LIFECYCLE_OBSERVABLE",
                },
            ]
        )
    frame = pd.DataFrame(rows)
    write_table(frame, PRE / "failure_root_cause_diagnosis_pre_reference")
    return frame


def plot_overview(optical: pd.DataFrame, p0: pd.DataFrame, anchor: pd.DataFrame) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(len(RUNS), 1, figsize=(16, 9), sharex=True)
    colors = {"REJECTED_ANCHOR": "#bdbdbd", "AMBIGUOUS_ANCHOR": "#ff9800", "CANDIDATE_ANCHOR": "#1976d2", "STRONG_ANCHOR": "#2e7d32"}
    for axis, run_id in zip(axes, RUNS):
        run = optical[optical["run_id"].eq(run_id)]
        for index, (track, group) in enumerate(run.groupby("track_id", sort=False), start=1):
            axis.scatter(group["mapped_sar_frame"], np.full(len(group), index), s=12, color="#263238")
        available = p0[(p0["run_id"].eq(run_id)) & p0["p0_model_available"]]
        if len(available):
            axis.axvspan(available["source_sar_frame"].min(), available["destination_sar_frame"].max(), color="#80cbc4", alpha=0.25, label="frozen P0 available")
        candidate = anchor[(anchor["run_id"].eq(run_id)) & anchor["mode"].eq("CAUSAL_REPLAY")]
        for status, group in candidate.groupby("anchor_status"):
            axis.scatter(group["frame_index"], np.zeros(len(group)), s=18, color=colors.get(status, "#9e9e9e"), label=status)
        axis.set_ylabel(f"{run_id}\nfragments")
        axis.grid(alpha=0.2)
        handles, labels = axis.get_legend_handles_labels()
        unique = dict(zip(labels, handles))
        axis.legend(unique.values(), unique.keys(), loc="upper left", ncol=4, fontsize=8)
    axes[-1].set_xlabel("SAR frame (full stream 0-494)")
    fig.suptitle("Full-stream optical hypotheses, frozen-P0 coverage, and causal anchor audit")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "01_full_stream_observability_and_anchor_overview.png", dpi=180)
    plt.close(fig)


def plot_lifecycle(lifecycle: pd.DataFrame) -> None:
    palette = {
        "ADMISSION_PENDING": "#fbc02d", "ACTIVE": "#2e7d32", "ACTIVE_AMBIGUOUS": "#1976d2",
        "DORMANT": "#7e57c2", "CENSORED_AT_BOUNDARY": "#ef6c00", "CENSORED_AT_STREAM_END": "#455a64",
    }
    for run_id in RUNS:
        for mode in MODES:
            part = lifecycle[(lifecycle["run_id"].eq(run_id)) & lifecycle["mode"].eq(mode)]
            tracks = list(dict.fromkeys(part["runtime_optical_fragment_id"].astype(str)))
            fig, axis = plt.subplots(figsize=(16, max(4, 0.35 * len(tracks) + 2)))
            for y, track in enumerate(tracks):
                rows = part[part["runtime_optical_fragment_id"].eq(track)].sort_values("frame_index")
                for state, group in rows.groupby("lifecycle_state"):
                    axis.scatter(group["frame_index"], np.full(len(group), y), s=14, color=palette.get(state, "#9e9e9e"), label=state)
            axis.set_yticks(range(len(tracks)))
            axis.set_yticklabels([value.replace(f"{run_id}_REUSED_{run_id}_", "") for value in tracks], fontsize=7)
            axis.set_xlim(0, FRAMES_PER_RUN - 1)
            axis.set_xlabel("SAR frame")
            axis.set_title(f"{run_id} | {mode} | stream-generated hypothesis lifecycle")
            axis.grid(alpha=0.2)
            handles, labels = axis.get_legend_handles_labels()
            unique = dict(zip(labels, handles))
            axis.legend(unique.values(), unique.keys(), loc="upper right", ncol=3, fontsize=8)
            fig.tight_layout()
            fig.savefig(FIG / f"02_lifecycle_{run_id}_{mode.lower()}.png", dpi=170)
            plt.close(fig)


def plot_burden(frame_summary: pd.DataFrame) -> None:
    fig, axes = plt.subplots(len(RUNS), len(MODES), figsize=(18, 9), sharex=True, sharey=True)
    for i, run_id in enumerate(RUNS):
        for j, mode in enumerate(MODES):
            part = frame_summary[(frame_summary["run_id"].eq(run_id)) & frame_summary["mode"].eq(mode)].sort_values("frame_index")
            axes[i, j].plot(part["frame_index"], part["q95_region_count_full_fan"], color="#90a4ae", lw=1, label="full-fan q95")
            axes[i, j].plot(part["frame_index"], part["shell_region_edge_count"], color="#d32f2f", lw=1, label="shell-region edges")
            axes[i, j].set_title(f"{run_id} | {mode}", fontsize=9)
            axes[i, j].grid(alpha=0.2)
    axes[0, 0].legend(fontsize=8)
    for axis in axes[-1, :]: axis.set_xlabel("SAR frame")
    for axis in axes[:, 0]: axis.set_ylabel("count")
    fig.suptitle("Q95 clutter burden and optical-shell intersection burden across the full stream")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "03_full_stream_q95_and_shell_burden.png", dpi=180)
    plt.close(fig)


def plot_negative_time(audit: pd.DataFrame) -> None:
    fig, axis = plt.subplots(figsize=(12, 5))
    labels = [f"{row.run_id}\n{row.mode.replace('_', ' ')}" for row in audit.itertuples(index=False)]
    axis.bar(np.arange(len(audit)), audit["negative_optical_frame_count"], color="#607d8b", label="negative optical frames")
    axis.scatter(np.arange(len(audit)), audit["negative_time_non_dormant_hypothesis_frame_count"], color="#f9a825", marker="D", label="previously optical-triggered non-dormant frames")
    axis.scatter(np.arange(len(audit)), audit["structural_sar_only_false_admission_event_count"], color="#d32f2f", label="SAR-only false-admission events")
    axis.set_xticks(np.arange(len(audit)))
    axis.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    axis.set_ylabel("frame count")
    axis.set_title("Negative-time audit: SAR clutter never opens a hypothesis without optical trigger")
    axis.legend()
    axis.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIG / "04_negative_time_structural_control.png", dpi=180)
    plt.close(fig)


def plot_r1_correction(visual: pd.DataFrame, one: pd.DataFrame, two: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    visual_counts = visual["independent_visual_support_extent"].value_counts()
    axes[0].bar(visual_counts.index, visual_counts.values, color="#1976d2")
    axes[0].tick_params(axis="x", rotation=25)
    axes[0].set_title("Independent visual ledger (not support-count generated)")
    axes[0].set_ylabel("case count")
    labels = ["one anchor", "two anchors"]
    domain_nonempty = [float(one["all_available_other_likely_families_retained"].mean()), float(two["all_available_other_likely_families_retained"].mean())]
    specific = [float(one["specific_likely_family_retained"].mean()), float(two["specific_likely_family_retained"].mean())]
    x = np.arange(2)
    axes[1].bar(x - 0.18, domain_nonempty, width=0.36, label="old DOMAIN_NONEMPTY proxy", color="#bdbdbd")
    axes[1].bar(x + 0.18, specific, width=0.36, label="SPECIFIC_LIKELY_FAMILY_RETAINED", color="#d32f2f")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels)
    axes[1].set_ylim(0, 1.05)
    axes[1].set_title("R1 anchor-retention semantic correction")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "05_r1_semantic_corrections.png", dpi=180)
    plt.close(fig)


def plot_r02_chain(anchor: pd.DataFrame, p0: pd.DataFrame, optical: pd.DataFrame) -> None:
    run_id = "R02ZF"
    fig, axis = plt.subplots(figsize=(16, 5))
    run = optical[optical["run_id"].eq(run_id)]
    for y, (track, group) in enumerate(run.groupby("track_id", sort=False), start=1):
        axis.scatter(group["mapped_sar_frame"], np.full(len(group), y), s=15, color="#263238")
    p0_run = p0[(p0["run_id"].eq(run_id)) & p0["p0_model_available"]]
    if len(p0_run): axis.axvspan(p0_run["source_sar_frame"].min(), p0_run["destination_sar_frame"].max(), color="#80cbc4", alpha=0.35)
    causal = anchor[(anchor["run_id"].eq(run_id)) & anchor["mode"].eq("CAUSAL_REPLAY")]
    candidate = causal[causal["anchor_status"].isin(["CANDIDATE_ANCHOR", "AMBIGUOUS_ANCHOR", "STRONG_ANCHOR"])]
    axis.scatter(candidate["frame_index"], np.zeros(len(candidate)), marker="*", s=70, color="#ff9800", label="candidate/ambiguous unary moment")
    axis.axvline(487, color="#d32f2f", linestyle="--", label="R1 dense relational window starts")
    axis.text(250, max(2, run["track_id"].nunique() * 0.8), "Early optical detections\nP0 continuity unavailable", ha="center", bbox=dict(facecolor="white", alpha=0.8))
    axis.text(483, max(2, run["track_id"].nunique() * 0.55), "P0 appears only after\nPERSON017/018 are already concurrent", ha="center", bbox=dict(facecolor="white", alpha=0.8))
    axis.set_xlim(0, 494)
    axis.set_xlabel("SAR frame")
    axis.set_ylabel("raw optical fragment index")
    axis.set_title("R02ZF blocked propagation chain: no early runtime unary seed reaches the dense relational window")
    axis.legend(loc="upper left")
    axis.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIG / "06_r02_anchor_relation_propagation_chain_blocked.png", dpi=190)
    plt.close(fig)


def make_report(summary: dict[str, Any], negative: pd.DataFrame) -> None:
    report = f"""# TERG-R2 scientific report

## Scope and authority

TERG-R2 is a mechanism exploration over complete R01ZF/R02ZF/R03ZF streams. It does not modify TERG-v1/R0/R1/P1E. Optical observations remain time/azimuth/lifecycle/explanation support. SAR remains the authority for image-domain response regions, range, and any future final localization. Raw fragments are hypotheses, not PERSON truth.

## R1 semantic corrections

- Anchor propagation now checks `SPECIFIC_LIKELY_FAMILY_RETAINED` by asking whether an admissible conditioned world still exists with the exact other-track likely family. It no longer substitutes `DOMAIN_NONEMPTY`.
- The old computed case geometry and the new independent visual review are separate ledgers.
- The three interval-overlap connected components are renamed `TEMPORAL_OVERLAP_CLUSTER`; they are not three asserted physical episodes.
- Direct inspection supports freezing `RELATIVE_ANGULAR_ORDER_CONTRADICTION` as an interval-order relational primitive. This does not establish physical identity, PERSON specificity, or final localization.

## Full-stream interface grounding

All three runs contain 495 SAR pseudocolor frames. Frozen geometry is constant within each run. The frozen C2/Q95 computation was replayed on all {summary['full_stream_frame_count']} frames. On the {summary['frozen_parity_frame_count']} formerly covered development frames, Q95 label masks are pixel-exact.

The important limitation is different: frozen P0 continuity is not full-stream. Available consecutive-frame fractions are {summary['p0_available_fraction_by_run']}. Outside those spans, the state is `SAR_P0_CONTINUITY_INTERFACE_UNAVAILABLE`; it is not response absence and is never used as exit evidence.

## Full-stream hypothesis management

The prototype opens an `ADMISSION_PENDING` explanation when a raw optical fragment first becomes observable. Repeated optical continuity can move it to `ACTIVE` or `ACTIVE_AMBIGUOUS`. A fragment end without a physical closure condition moves to `DORMANT`; boundary contact becomes `CENSORED_AT_BOUNDARY`; run termination becomes `CENSORED_AT_STREAM_END`. Reentry and new-identity interpretations are retained as competitors when guarded angular supports are compatible.

This is enough to express open/maintain/dormancy/reentry competition, but not enough to know true physical closure. No hypothesis reaches `CLOSED`, because fragment end, boundary contact, and missing detections do not prove that future physical continuation is impossible.

## Three replay modes

- `CAUSAL_REPLAY`: optical observations in `[t-250 ms, t]` only.
- `FIXED_LAG_100MS`: optical observations in `[t-250 ms, t+100 ms]`; 100 ms is an existing fixed interface policy, not outcome-tuned.
- `FULL_CONTEXT_OFFLINE`: full-run runtime-legal raw fragment support is available for state smoothing, while local shell construction uses `[t-250 ms, t+250 ms]`. No stitched identity or SAR reference enters construction.

## Runtime unary anchors

Strong automatic anchors established: **{summary['strong_auto_anchor_count']}**.

Candidate/ambiguous moments exist, but none becomes a strong runtime anchor. The decisive reasons are:

1. no runtime-legal optical-to-SAR range interval or equivalent calibrated physical unary observable;
2. frozen P0 continuity is absent over most early/negative-time spans;
3. singleton q95 explanations can also occur during no-optical control time;
4. raw fragment lifecycle boundaries do not imply SAR birth/death or identity;
5. shared/multi-family response remains set-valued.

R02ZF is the clearest failure chain: early optical fragments occur while frozen P0 is unavailable; P0 starts at F472 only after PERSON017/018 are already concurrent, so no early singleton family seed is carried into F487-F494.

## Negative time and admission

No SAR-only clutter frame opens a hypothesis because admission requires a runtime optical trigger. The audit records **{int(negative['structural_sar_only_false_admission_event_count'].sum())}** SAR-only false-admission events. Previously optical-triggered hypotheses can remain non-dormant on local no-shell frames; those frames are reported separately and are not relabeled as new admissions. This is a structural negative control, not a PERSON-GT accuracy result. Singleton/brief optical fragments remain pending or dormant rather than being promoted by confidence thresholds.

## Sparse anchor requirement

The post-reference likely-family stand-in is used only to measure information requirements. One or two sparse anchors can contract some other-track family domains in R1 relational segments, but the corrected ledger separately verifies whether the exact likely family survives. This demonstrates potential propagation capacity, not an automatic runtime result.

## Failure-root classification

The outcome is mixed:

- `MECHANISM_UNDERUTILIZATION`: the old SAR response-region interface was unnecessarily limited; full-stream C2/Q95 is reconstructable and parity-grounded.
- `DEPLOYED_RUNTIME_INTERFACE_GAP`: frozen P0 continuity exists only on selected spans.
- `MISSING_PHYSICAL_OBSERVABLE`: no independent unary range/geometry support exists to turn a low-ambiguity response family into a strong anchor.
- `MISSING_LIFECYCLE_OBSERVABLE`: true closure and reentry identity cannot be resolved from fragment end/boundary contact alone.

## Direct answers

1. **When to open/keep/dormant/recover/close?** The prototype can open, keep, and place hypotheses into dormancy; it explicitly creates reentry/new-identity competing explanations. It cannot yet make a scientifically justified true-close decision, so it censors rather than fabricates closure.
2. **Does the full stream naturally produce a runtime-legal unary anchor?** It produces candidate/ambiguous singleton moments, but no strong automatic runtime-legal unary anchor survives clutter controls and the missing range/P0 limitations.
3. **What minimum absolute information is still needed?** At minimum, one runtime-legal coarse range interval (or an equivalent calibrated unary physical constraint) at a low-ambiguity moment, plus deployable P0 continuity across the interval that connects that moment to the later relation graph. A sparse manual anchor can substitute diagnostically, but must remain labeled manual. This is the smallest credible path from local anchor to temporal propagation to multi-person relation constraints to family-domain contraction.

## Figures

![overview](figures/01_full_stream_observability_and_anchor_overview.png)

![burden](figures/03_full_stream_q95_and_shell_burden.png)

![negative time](figures/04_negative_time_structural_control.png)

![R1 corrections](figures/05_r1_semantic_corrections.png)

![R02 chain](figures/06_r02_anchor_relation_propagation_chain_blocked.png)
"""
    (OUTPUT / "TERG_R2_SCIENTIFIC_REPORT.md").write_text(report, encoding="utf-8")


def build_manifest() -> pd.DataFrame:
    rows = []
    for path in sorted(OUTPUT.rglob("*")):
        if path.is_file() and path.name != "ARTIFACT_MANIFEST.csv":
            rows.append(
                {
                    "path": str(path.relative_to(WORKSPACE)).replace("\\", "/"),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    manifest = pd.DataFrame(rows)
    manifest.to_csv(OUTPUT / "ARTIFACT_MANIFEST.csv", index=False, encoding="utf-8-sig")
    return manifest


def run(args: argparse.Namespace) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    PRE.mkdir(parents=True, exist_ok=True)
    POST.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    frames = reconstruct_frames()
    frame_registry = pd.DataFrame([{key: value for key, value in row.items() if key != "geometry"} | {f"geometry_{key}": value for key, value in row["geometry"].items()} for row in frames])
    write_table(frame_registry, PRE / "full_stream_frame_registry_pre_reference")
    regions, q95_summary = generate_full_q95(frames, args.workers, args.resume_regions)
    parity = validate_q95_parity(regions, frames)
    optical = load_optical()
    shells, shell_edges, frame_summary = build_shell_topology(frames, regions, optical)
    models, metrics, p0_availability = load_p0_authority()
    p0_edges = build_p0_edges(frames, regions, models)
    memberships = assign_dynamic_families(shell_edges, p0_edges)
    hypotheses, lifecycle, events = build_lifecycle(optical, shells, shell_edges, memberships, p0_availability)
    anchor, lifecycle_anchor = audit_anchors(lifecycle, shells, frame_summary, regions)
    visual = r1_visual_ledger()
    one, two = r1_specific_likely_retention()
    clusters, assignments = temporal_overlap_cluster_correction()
    negative = negative_time_audit(frame_summary, lifecycle_anchor, events, optical)
    exploratory = exploratory_event_metrics(hypotheses, optical)
    source_audit = anchor_source_audit(anchor)
    sparse = sparse_anchor_diagnostic(one, two)
    failure = failure_root_diagnosis(anchor, p0_availability, lifecycle_anchor)
    plot_overview(optical, p0_availability, anchor)
    plot_lifecycle(lifecycle_anchor)
    plot_burden(frame_summary)
    plot_negative_time(negative)
    plot_r1_correction(visual, one, two)
    plot_r02_chain(anchor, p0_availability, optical)
    p0_fraction = p0_availability.groupby("run_id")["p0_model_available"].mean().to_dict()
    p0_count = p0_availability[p0_availability["p0_model_available"]].groupby("run_id").size().to_dict()
    summary = {
        "schema": "TERG_R2_RUNTIME_GROUNDING_AND_FULL_STREAM_HYPOTHESIS_MANAGEMENT_V1",
        "generated_at": now_iso(),
        "full_stream_frame_count": len(frames),
        "full_stream_run_count": len(RUNS),
        "q95_region_count": len(regions),
        "frozen_parity_frame_count": len(parity),
        "frozen_q95_pixel_exact_fraction": float(parity["q95_label_mask_pixel_exact"].mean()),
        "p0_available_fraction_by_run": {key: float(value) for key, value in p0_fraction.items()},
        "p0_available_pair_count_by_run": {key: int(value) for key, value in p0_count.items()},
        "runtime_hypothesis_count": len(hypotheses),
        "lifecycle_row_count": len(lifecycle_anchor),
        "stream_generated_transition_count": len(events),
        "strong_auto_anchor_count": int(anchor["anchor_status"].eq("STRONG_ANCHOR").sum()),
        "candidate_auto_anchor_count": int(anchor["anchor_status"].eq("CANDIDATE_ANCHOR").sum()),
        "ambiguous_auto_anchor_count": int(anchor["anchor_status"].eq("AMBIGUOUS_ANCHOR").sum()),
        "sar_only_false_admission_event_count": int(negative["structural_sar_only_false_admission_event_count"].sum()),
        "negative_time_non_dormant_hypothesis_frame_count": int(negative["negative_time_non_dormant_hypothesis_frame_count"].sum()),
        "true_closed_hypothesis_frame_count": int(lifecycle_anchor["lifecycle_state"].eq("CLOSED").sum()),
        "relative_order_primitive_state": "RELATIVE_ANGULAR_ORDER_CONTRADICTION_FROZEN_AS_RELATIONAL_PRIMITIVE",
        "runtime_unary_anchor_conclusion": "NO_STRONG_AUTO_RUNTIME_UNARY_ANCHOR_ESTABLISHED",
        "full_stream_hypothesis_management_conclusion": "OPEN_KEEP_DORMANCY_AND_REENTRY_COMPETITION_EXPRESSED_TRUE_SEMANTIC_CLOSURE_NOT_ESTABLISHED",
        "minimum_missing_absolute_information": "RUNTIME_LEGAL_COARSE_RANGE_INTERVAL_OR_EQUIVALENT_CALIBRATED_UNARY_PHYSICAL_CONSTRAINT_PLUS_DEPLOYABLE_P0_CONTINUITY_TO_RELATION_WINDOW",
        "non_claims": [
            "NO_PERSON_IDENTITY_TRUTH", "NO_FINAL_CENTER", "NO_FINAL_BOX", "NO_LEARNED_FUSION", "NO_HUNGARIAN", "NO_FINAL_TRACKER", "NO_R04_CONFIRMATION"
        ],
    }
    write_json(OUTPUT / "terg_r2_summary.json", summary)
    make_report(summary, negative)
    manifest = build_manifest()
    print(json.dumps({"summary": summary, "artifact_count": len(manifest)}, ensure_ascii=False, indent=2), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--resume-regions", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
