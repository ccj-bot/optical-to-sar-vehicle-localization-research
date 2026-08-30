from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "person_range_temporal_decision_study_20260830"
OUTPUT = WORKSPACE / "output" / "person_range_temporal_decision_study_20260830"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference_diagnostic_only"
FIG = OUTPUT / "figures"
PACK = WORKSPACE / "review_packs" / "PERSON_RANGE_TEMPORAL_DECISION_REVIEW_PACK_20260830"
PACK_ZIP = WORKSPACE / "review_packs" / "PERSON_RANGE_TEMPORAL_DECISION_REVIEW_PACK_20260830.zip"

B0 = WORKSPACE / "output" / "person_b0_end_to_end_capability_and_bottleneck_study_20260830"
B0_PRE = B0 / "pre_reference"
B0_POST = B0 / "post_reference_oracle_diagnostic_only"
R2_PRE = WORKSPACE / "output" / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830" / "pre_reference"

Q95_REGIONS = R2_PRE / "full_stream_q95_response_regions_pre_reference.parquet"
Q95_MASKS = R2_PRE / "full_stream_q95_masks"
SHELLS = R2_PRE / "full_stream_optical_shells_pre_reference.parquet"
SHELL_EDGES = R2_PRE / "full_stream_shell_q95_pixel_edges_pre_reference.parquet"
FRAME_REGISTRY = R2_PRE / "full_stream_frame_registry_pre_reference.parquet"
P0_EDGES = B0_PRE / "full_stream_p0_graded_p0_q95_edges.parquet"
B0_MEMBERSHIP = B0_PRE / "full_stream_p0_candidate_family_membership.parquet"
OPTICAL = WORKSPACE / "output" / "person_optical_guided_sar_annotation_full_20260823" / "optical_person_frame_hypotheses.parquet"

REFERENCE = B0_POST / "r01_r02_r03_manual_range_reference_oracle_only.parquet"
FRAGMENT_TARGET_MAP = B0_POST / "raw_fragment_to_offline_target_mapping_oracle_only.csv"
RANGE_SWEEP = B0_POST / "full_stream_p0_coarse_range_oracle_sweep.parquet"

RUNS = ("R01ZF", "R02ZF", "R03ZF")
SOURCE_RUN = "R03ZF"
SOURCE_ENTITY = "R03ZF_I01_T0004"
SOURCE_START = 447
SOURCE_END = 494
SOURCE_FRAMES = list(range(SOURCE_START, SOURCE_END + 1))
KEY_FRAMES = (451, 457, 459, 466, 470)
MODE = "CAUSAL_REPLAY"


def ensure_dirs() -> None:
    for path in (TASK, OUTPUT, PRE, POST, FIG, PACK.parent):
        path.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:20].upper()}"


def write_table(df: pd.DataFrame, stem: Path, parquet: bool = True) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(stem.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    if parquet:
        df.to_parquet(stem.with_suffix(".parquet"), index=False)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def markdown_table(df: pd.DataFrame) -> str:
    columns = [str(column) for column in df.columns]
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for values in df.itertuples(index=False, name=None):
        rows.append("| " + " | ".join(str(value) for value in values) + " |")
    return "\n".join(rows)


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, x: str) -> None:
        self.parent.setdefault(x, x)

    def find(self, x: str) -> str:
        self.add(x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if ra < rb:
                self.parent[rb] = ra
            else:
                self.parent[ra] = rb


def intervals(value: str) -> list[tuple[float, float]]:
    return [(float(a), float(b)) for a, b in json.loads(value)]


def interval_center(value: str) -> float:
    values = intervals(value)
    total = sum(b - a for a, b in values)
    if total <= 0:
        return float(np.mean([(a + b) / 2 for a, b in values]))
    return float(sum(((a + b) / 2) * (b - a) for a, b in values) / total)


def strict_family_membership(regions: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for run_id in RUNS:
        run_regions = regions[regions["run_id"] == run_id]
        uf = UnionFind()
        for region_id in run_regions["region_id"].astype(str):
            uf.add(region_id)
        run_edges = edges[(edges["run_id"] == run_id) & edges["lower_mutual_dominant"]]
        for row in run_edges.itertuples(index=False):
            uf.union(str(row.source_region_id), str(row.destination_region_id))
        groups: dict[str, list[str]] = {}
        for region_id in run_regions["region_id"].astype(str):
            groups.setdefault(uf.find(region_id), []).append(region_id)
        id_by_root = {root: stable_id("P0MF", run_id, min(members)) for root, members in groups.items()}
        for row in run_regions.itertuples(index=False):
            root = uf.find(str(row.region_id))
            rows.append({
                "run_id": run_id,
                "frame_index": int(row.frame_index),
                "region_id": str(row.region_id),
                "strict_family_id": id_by_root[root],
                "strict_family_semantics": "MUTUAL_DOMINANT_P0_COMPONENT_NO_OPTIONAL_UNION",
            })
    return pd.DataFrame(rows)


def frame_family_events(candidate_regions: pd.DataFrame, family_map: pd.DataFrame, regions: pd.DataFrame) -> pd.DataFrame:
    if candidate_regions.empty:
        return pd.DataFrame()
    geom_cols = [
        "run_id", "frame_index", "region_id", "pixel_count", "area_m2", "range_min_m", "range_max_m",
        "theta_min_deg", "theta_max_deg", "touches_observable_boundary", "has_truncated_support",
    ]
    data = candidate_regions.merge(family_map, on=["run_id", "frame_index", "region_id"], how="left", validate="many_to_one")
    data = data.merge(regions[geom_cols], on=["run_id", "frame_index", "region_id"], how="left", validate="many_to_one")
    group_cols = ["trajectory_id", "trajectory_kind", "run_id", "trajectory_offset", "frame_index", "strict_family_id"]
    family_rows: list[dict[str, Any]] = []
    for keys, group in data.groupby(group_cols, sort=False):
        trajectory_id, trajectory_kind, run_id, offset, frame_index, family_id = keys
        unique = group.drop_duplicates("region_id")
        weights = unique["pixel_count"].astype(float).clip(lower=1)
        theta_center = (unique["theta_min_deg"].astype(float) + unique["theta_max_deg"].astype(float)) / 2
        range_center = (unique["range_min_m"].astype(float) + unique["range_max_m"].astype(float)) / 2
        family_rows.append({
            "trajectory_id": trajectory_id,
            "trajectory_kind": trajectory_kind,
            "run_id": run_id,
            "trajectory_offset": int(offset),
            "frame_index": int(frame_index),
            "strict_family_id": family_id,
            "region_ids": ";".join(sorted(unique["region_id"].astype(str))),
            "N_region_in_family": int(unique["region_id"].nunique()),
            "A_candidate_px_in_family": float(unique["pixel_count"].sum()),
            "A_candidate_m2_in_family": float(unique["area_m2"].sum()),
            "theta_center_deg": float(np.average(theta_center, weights=weights)),
            "theta_min_deg": float(unique["theta_min_deg"].min()),
            "theta_max_deg": float(unique["theta_max_deg"].max()),
            "range_center_m": float(np.average(range_center, weights=weights)),
            "range_min_m": float(unique["range_min_m"].min()),
            "range_max_m": float(unique["range_max_m"].max()),
            "touches_observable_boundary": bool(unique["touches_observable_boundary"].any()),
            "has_truncated_support": bool(unique["has_truncated_support"].any()),
        })
    events = pd.DataFrame(family_rows)
    counts = events.groupby(["trajectory_id", "frame_index"])["strict_family_id"].nunique().rename("N_strict_family").reset_index()
    regions_count = data.groupby(["trajectory_id", "frame_index"])["region_id"].nunique().rename("N_region").reset_index()
    events = events.merge(counts, on=["trajectory_id", "frame_index"], how="left")
    events = events.merge(regions_count, on=["trajectory_id", "frame_index"], how="left")
    events["observation_state"] = np.where(events["N_strict_family"] == 1, "UNIQUE_FAMILY_OBSERVATION", "COMPETING_FAMILY_OBSERVATION")
    return events


def recurrence_records(events: pd.DataFrame, trajectory_lengths: dict[str, int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (trajectory_id, family_id), group in events.groupby(["trajectory_id", "strict_family_id"], sort=False):
        group = group.sort_values("trajectory_offset")
        offsets = group["trajectory_offset"].astype(int).tolist()
        unique_offsets = group.loc[group["N_strict_family"] == 1, "trajectory_offset"].astype(int).tolist()
        gaps = np.diff(offsets) if len(offsets) > 1 else np.asarray([], dtype=int)
        reselections = int(np.sum(gaps > 1))
        ambiguous_bridges = 0
        present = set(offsets)
        ambiguous = set(group.loc[group["N_strict_family"] > 1, "trajectory_offset"].astype(int))
        for offset in ambiguous:
            if offset - 1 in present and offset + 1 in present:
                ambiguous_bridges += 1
        row0 = group.iloc[0]
        rows.append({
            "trajectory_id": trajectory_id,
            "trajectory_kind": row0["trajectory_kind"],
            "run_id": row0["run_id"],
            "strict_family_id": family_id,
            "admissible_frame_count": int(len(set(offsets))),
            "unique_frame_count": int(len(set(unique_offsets))),
            "competing_frame_count": int(len(set(offsets)) - len(set(unique_offsets))),
            "temporal_span_frames": int(max(offsets) - min(offsets) + 1),
            "trajectory_length_frames": int(trajectory_lengths[trajectory_id]),
            "temporal_occupancy": float(len(set(offsets)) / trajectory_lengths[trajectory_id]),
            "reselection_after_gap_count": reselections,
            "ambiguous_bridge_count": int(ambiguous_bridges),
            "first_offset": int(min(offsets)),
            "last_offset": int(max(offsets)),
            "admissible_offsets": ";".join(map(str, offsets)),
            "unique_offsets": ";".join(map(str, unique_offsets)),
            "range_center_min_m": float(group["range_center_m"].min()),
            "range_center_max_m": float(group["range_center_m"].max()),
            "theta_center_min_deg": float(group["theta_center_deg"].min()),
            "theta_center_max_deg": float(group["theta_center_deg"].max()),
        })
    return pd.DataFrame(rows)


def select_top_family(records: pd.DataFrame) -> pd.DataFrame:
    if records.empty:
        return records
    return (
        records.sort_values(
            ["trajectory_id", "unique_frame_count", "admissible_frame_count", "temporal_span_frames", "strict_family_id"],
            ascending=[True, False, False, False, True],
        )
        .drop_duplicates("trajectory_id")
        .reset_index(drop=True)
    )


def exact_corridor_regions(
    run_id: str,
    frame_index: int,
    corridor_json: str,
    frame_meta: pd.Series,
    region_lookup: pd.DataFrame,
) -> list[str]:
    with np.load(Q95_MASKS / f"{run_id}_SARF{frame_index:06d}.npz") as archive:
        labels = archive["Q095"]
    yy, xx = np.indices(labels.shape)
    theta = np.degrees(np.arctan2(xx - float(frame_meta["geometry_center_x_px"]), float(frame_meta["geometry_center_y_px"]) - yy))
    corridor = np.zeros(labels.shape, dtype=bool)
    for low, high in intervals(corridor_json):
        corridor |= (theta >= low) & (theta <= high)
    labels_hit = np.unique(labels[corridor & (labels > 0)]).astype(int)
    by_label = region_lookup.set_index("region_label")
    return [str(by_label.loc[label, "region_id"]) for label in labels_hit if label in by_label.index]


def build_all_entity_events(
    shells: pd.DataFrame,
    shell_edges: pd.DataFrame,
    family_map: pd.DataFrame,
    regions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    use_shells = shells[(shells["run_id"].isin(RUNS)) & (shells["mode"] == MODE)].copy()
    use_edges = shell_edges[(shell_edges["run_id"].isin(RUNS)) & (shell_edges["mode"] == MODE)].copy()
    shell_meta = use_shells[["run_id", "frame_index", "track_id", "effective_intervals_json"]].drop_duplicates()
    candidates = use_edges[["run_id", "frame_index", "track_id", "region_id"]].drop_duplicates()
    candidates = candidates.merge(shell_meta, on=["run_id", "frame_index", "track_id"], how="left", validate="many_to_one")
    candidates["trajectory_id"] = candidates["run_id"].astype(str) + "::" + candidates["track_id"].astype(str)
    candidates["trajectory_kind"] = "NATURAL_OPTICAL_CORRIDOR"
    min_frame = candidates.groupby("trajectory_id")["frame_index"].transform("min")
    candidates["trajectory_offset"] = candidates["frame_index"].astype(int) - min_frame.astype(int)
    events = frame_family_events(candidates, family_map, regions)
    corridor = shell_meta.copy()
    corridor["trajectory_id"] = corridor["run_id"].astype(str) + "::" + corridor["track_id"].astype(str)
    corridor["corridor_center_deg"] = corridor["effective_intervals_json"].map(interval_center)
    corridor["corridor_width_deg"] = corridor["effective_intervals_json"].map(lambda value: sum(b - a for a, b in intervals(value)))
    events = events.merge(corridor[["trajectory_id", "frame_index", "track_id", "effective_intervals_json", "corridor_center_deg", "corridor_width_deg"]], on=["trajectory_id", "frame_index"], how="left")
    lengths = use_shells.groupby(use_shells["run_id"].astype(str) + "::" + use_shells["track_id"].astype(str))["frame_index"].nunique().astype(int).to_dict()
    records = recurrence_records(events, lengths)
    return events, records


def source_and_null_trajectories(
    shells: pd.DataFrame,
    registry: pd.DataFrame,
    optical: pd.DataFrame,
    regions: pd.DataFrame,
    p0: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = shells[
        (shells["run_id"] == SOURCE_RUN)
        & (shells["mode"] == MODE)
        & (shells["track_id"] == SOURCE_ENTITY)
        & shells["frame_index"].between(SOURCE_START, SOURCE_END)
    ].sort_values("frame_index")
    if source["frame_index"].nunique() != len(SOURCE_FRAMES):
        raise RuntimeError("R03 source trajectory is incomplete")

    run_registry = registry[registry["run_id"] == SOURCE_RUN].set_index("sar_frame_index")
    run_regions = regions[regions["run_id"] == SOURCE_RUN]
    density = run_regions.groupby("frame_index")["region_id"].nunique().reindex(range(495), fill_value=0)
    boundary = run_regions.groupby("frame_index")["touches_observable_boundary"].mean().reindex(range(495), fill_value=0.0)
    p0_available = p0[(p0["run_id"] == SOURCE_RUN)].set_index("source_frame")["p0_state"].eq("P0_AVAILABLE").reindex(range(495), fill_value=False)
    detected_frames = set(optical[(optical["run_id"] == SOURCE_RUN) & (optical["box_source"] == "DETECTED")]["frame_index"].astype(int))
    sar_has_person = registry[registry["run_id"] == SOURCE_RUN].set_index("sar_frame_index")["nominal_optical_frame_index"].astype(int).isin(detected_frames)

    source_density = density.loc[SOURCE_START:SOURCE_END].to_numpy(dtype=float)
    source_boundary = boundary.loc[SOURCE_START:SOURCE_END].to_numpy(dtype=float)
    source_p0 = p0_available.loc[SOURCE_START:SOURCE_END].to_numpy(dtype=float)
    candidates: list[dict[str, Any]] = []
    length = len(SOURCE_FRAMES)
    for start in range(0, 495 - length + 1):
        end = start + length - 1
        if not (end < SOURCE_START or start > SOURCE_END):
            continue
        if bool(sar_has_person.reindex(range(start, end + 1), fill_value=True).any()):
            continue
        d = density.loc[start:end].to_numpy(dtype=float)
        b = boundary.loc[start:end].to_numpy(dtype=float)
        a = p0_available.loc[start:end].to_numpy(dtype=float)
        candidates.append({
            "control_start": start,
            "control_end": end,
            "duration_frames": length,
            "detected_optical_person_frames": 0,
            "density_profile_mae": float(np.mean(np.abs(d - source_density))),
            "mean_density_difference": float(abs(np.mean(d) - np.mean(source_density))),
            "boundary_profile_mae": float(np.mean(np.abs(b - source_boundary))),
            "p0_availability_difference": float(abs(np.mean(a) - np.mean(source_p0))),
            "temporal_distance_frames": int(min(abs(start - SOURCE_START), abs(end - SOURCE_END))),
            "selection_outcome_used": False,
        })
    ledger = pd.DataFrame(candidates)
    if ledger.empty:
        raise RuntimeError("no eligible matched null windows")
    chosen: list[pd.Series] = []
    nearest = ledger.sort_values(["temporal_distance_frames", "control_start"]).iloc[0]
    chosen.append(nearest)
    ranked = ledger.sort_values([
        "density_profile_mae", "mean_density_difference", "boundary_profile_mae", "p0_availability_difference", "temporal_distance_frames", "control_start"
    ])
    for _, row in ranked.iterrows():
        if int(row.control_start) == int(nearest.control_start):
            continue
        if all(abs(int(row.control_start) - int(existing.control_start)) >= length for existing in chosen):
            chosen.append(row)
        if len(chosen) == 6:
            break
    control_ledger = pd.DataFrame(chosen).reset_index(drop=True)
    control_ledger["trajectory_id"] = [f"R03_NULL_{int(v):03d}_{int(v)+length-1:03d}" for v in control_ledger["control_start"]]
    control_ledger["selection_rule"] = ["NEAREST_TIME_FULL_NO_PERSON_WINDOW"] + [f"NUISANCE_LEXICOGRAPHIC_MATCH_RANK_{i}" for i in range(1, len(control_ledger))]
    control_ledger["preserved_nuisance"] = "duration+corridor_width+angular_trajectory_shape+same_run+P0_availability+response_density+boundary_profile"
    control_ledger["broken_relation"] = "corridor trajectory moved away from its observed optical PERSON time while SAR stream remains unchanged"
    control_ledger["manual_reference_used"] = False

    trajectory_rows: list[dict[str, Any]] = []
    for offset, shell in enumerate(source.itertuples(index=False)):
        trajectory_rows.append({
            "trajectory_id": "R03_SOURCE_F447_F494",
            "trajectory_kind": "SOURCE_MOVING_PERSON_CORRIDOR",
            "run_id": SOURCE_RUN,
            "trajectory_offset": offset,
            "source_frame_index": int(shell.frame_index),
            "frame_index": int(shell.frame_index),
            "effective_intervals_json": str(shell.effective_intervals_json),
            "corridor_center_deg": interval_center(str(shell.effective_intervals_json)),
            "corridor_width_deg": float(shell.effective_width_deg),
        })
    for control in control_ledger.itertuples(index=False):
        for offset, shell in enumerate(source.itertuples(index=False)):
            actual = int(control.control_start) + offset
            trajectory_rows.append({
                "trajectory_id": str(control.trajectory_id),
                "trajectory_kind": "MATCHED_NO_PERSON_TIME_SHIFT",
                "run_id": SOURCE_RUN,
                "trajectory_offset": offset,
                "source_frame_index": int(shell.frame_index),
                "frame_index": actual,
                "effective_intervals_json": str(shell.effective_intervals_json),
                "corridor_center_deg": interval_center(str(shell.effective_intervals_json)),
                "corridor_width_deg": float(shell.effective_width_deg),
            })
    trajectory = pd.DataFrame(trajectory_rows)
    return trajectory, control_ledger


def shifted_candidate_regions(trajectory: pd.DataFrame, registry: pd.DataFrame, regions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    registry_lookup = registry.set_index(["run_id", "sar_frame_index"])
    region_groups = {(run, int(frame)): group for (run, frame), group in regions.groupby(["run_id", "frame_index"])}
    for row in trajectory.itertuples(index=False):
        meta = registry_lookup.loc[(row.run_id, int(row.frame_index))]
        frame_regions = region_groups[(row.run_id, int(row.frame_index))]
        selected = exact_corridor_regions(row.run_id, int(row.frame_index), row.effective_intervals_json, meta, frame_regions)
        for region_id in selected:
            rows.append({
                "trajectory_id": row.trajectory_id,
                "trajectory_kind": row.trajectory_kind,
                "run_id": row.run_id,
                "trajectory_offset": int(row.trajectory_offset),
                "frame_index": int(row.frame_index),
                "source_frame_index": int(row.source_frame_index),
                "region_id": region_id,
                "effective_intervals_json": row.effective_intervals_json,
                "corridor_center_deg": float(row.corridor_center_deg),
                "corridor_width_deg": float(row.corridor_width_deg),
            })
    return pd.DataFrame(rows)


def trajectory_geometry(events: pd.DataFrame, top: pd.DataFrame, trajectory: pd.DataFrame) -> pd.DataFrame:
    merged = events.merge(top[["trajectory_id", "strict_family_id"]], on=["trajectory_id", "strict_family_id"], how="inner")
    if "corridor_center_deg" not in merged.columns or "corridor_width_deg" not in merged.columns:
        merged = merged.merge(trajectory[["trajectory_id", "trajectory_offset", "corridor_center_deg", "corridor_width_deg"]], on=["trajectory_id", "trajectory_offset"], how="left", validate="many_to_one")
    rows: list[dict[str, Any]] = []
    for trajectory_id, group in merged.groupby("trajectory_id"):
        group = group.sort_values("trajectory_offset")
        x = group["corridor_center_deg"].to_numpy(dtype=float)
        t = group["trajectory_offset"].to_numpy(dtype=float)
        theta = group["theta_center_deg"].to_numpy(dtype=float)
        rng = group["range_center_m"].to_numpy(dtype=float)
        if len(group) >= 2 and np.ptp(x) > 0:
            theta_coef = np.polyfit(x, theta, 1)
            theta_pred = np.polyval(theta_coef, x)
            range_coef = np.polyfit(x, rng, 1)
            range_pred = np.polyval(range_coef, x)
        else:
            theta_coef = np.asarray([math.nan, math.nan]); theta_pred = np.full_like(theta, np.nan)
            range_coef = np.asarray([math.nan, math.nan]); range_pred = np.full_like(rng, np.nan)
        if len(group) >= 3:
            tcoef_theta = np.polyfit(t, theta, 2); tpred_theta = np.polyval(tcoef_theta, t)
            tcoef_range = np.polyfit(t, rng, 2); tpred_range = np.polyval(tcoef_range, t)
        else:
            tpred_theta = np.full_like(theta, np.nan); tpred_range = np.full_like(rng, np.nan)
        rows.append({
            "trajectory_id": trajectory_id,
            "trajectory_kind": group.iloc[0]["trajectory_kind"],
            "strict_family_id": group.iloc[0]["strict_family_id"],
            "observed_frames": int(len(group)),
            "theta_from_corridor_affine_slope": float(theta_coef[0]),
            "theta_from_corridor_affine_intercept": float(theta_coef[1]),
            "theta_from_corridor_median_abs_residual_deg": float(np.nanmedian(np.abs(theta - theta_pred))),
            "range_from_corridor_affine_slope_m_per_deg": float(range_coef[0]),
            "range_from_corridor_median_abs_residual_m": float(np.nanmedian(np.abs(rng - range_pred))),
            "theta_time_quadratic_median_abs_residual_deg": float(np.nanmedian(np.abs(theta - tpred_theta))),
            "range_time_quadratic_median_abs_residual_m": float(np.nanmedian(np.abs(rng - tpred_range))),
            "theta_first_difference_median_abs_deg": float(np.median(np.abs(np.diff(theta)))) if len(theta) > 1 else math.nan,
            "range_first_difference_median_abs_m": float(np.median(np.abs(np.diff(rng)))) if len(rng) > 1 else math.nan,
            "absolute_depth_observable_from_this_relation": False,
            "blocking_missing_inputs": "verified timing offset; platform pose/velocity; camera K; camera height/pitch/roll; camera-radar extrinsic; ground plane",
        })
    return pd.DataFrame(rows)


def calibration_inventory(registry: pd.DataFrame, optical: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    image_rows: list[dict[str, Any]] = []
    image_dims: dict[str, tuple[int, int]] = {}
    for run_id in RUNS:
        run = optical[optical["run_id"] == run_id]
        path = Path(str(run.iloc[0]["optical_image_path"]))
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"cannot read optical image {path}")
        h, w = image.shape[:2]
        image_dims[run_id] = (w, h)
        image_rows.append({"run_id": run_id, "optical_width_px": w, "optical_height_px": h, "sample_path": str(path), "source": "RAW_IMAGE_HEADER"})

    known_candidates = [
        WORKSPACE / "output" / "pseudocolor_azimuth_calibration_20260803" / "CALIBRATION_PROTOCOL.md",
        WORKSPACE / "tools" / "configs" / "depthpro_sar_center_calibration_candidate_2026-04-13.json",
    ]
    rows = [
        {"interface": "camera_K", "status": "MISSING_FOR_PERSON_SCENE", "evidence": "no PERSON-scene intrinsic matrix in known manifests or filename inventory", "runtime_usable": False},
        {"interface": "camera_height", "status": "MISSING_FOR_PERSON_SCENE", "evidence": "no measured camera height record discovered", "runtime_usable": False},
        {"interface": "camera_pitch_roll", "status": "MISSING_FOR_PERSON_SCENE", "evidence": "no measured pitch/roll record discovered", "runtime_usable": False},
        {"interface": "camera_radar_extrinsic_R_t", "status": "MISSING_FOR_PERSON_SCENE", "evidence": "no camera-radar rigid transform discovered", "runtime_usable": False},
        {"interface": "ground_plane", "status": "MISSING_FOR_PERSON_SCENE", "evidence": "no plane normal/offset or slope envelope discovered", "runtime_usable": False},
        {"interface": "platform_pose_velocity", "status": "MISSING_FOR_PERSON_SCENE", "evidence": "no synchronized platform trajectory discovered", "runtime_usable": False},
        {"interface": "optical_image_resolution", "status": "AVAILABLE_FROM_RAW_HEADERS", "evidence": json.dumps({k: list(v) for k, v in image_dims.items()}), "runtime_usable": True},
        {"interface": "optical_to_sar_nominal_timing", "status": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED", "evidence": str(FRAME_REGISTRY), "runtime_usable": "CONTEXT_ONLY"},
        {"interface": "sar_fan_metric_geometry", "status": "AVAILABLE_20M_RADIAL_RENDER_GEOMETRY", "evidence": str(FRAME_REGISTRY), "runtime_usable": True},
        {"interface": "optical_angular_corridor", "status": "AVAILABLE_SEARCH_SUPPORT", "evidence": str(SHELLS), "runtime_usable": True},
        {"interface": "historical_vehicle_azimuth_candidate", "status": "WITHHELD_AND_NOT_CAMERA_K", "evidence": str(known_candidates[0]), "runtime_usable": False},
        {"interface": "historical_depthpro_vehicle_candidate", "status": "INCOMPATIBLE_LEGACY_VEHICLE_MODEL", "evidence": str(known_candidates[1]), "runtime_usable": False},
    ]
    inventory = pd.DataFrame(rows)

    foot = optical[(optical["run_id"].isin(RUNS)) & optical["raw_track_fragment_id"].notna()].copy()
    states: list[str] = []
    for row in foot.itertuples(index=False):
        w, h = image_dims[str(row.run_id)]
        exact_boundary = float(row.bbox_x1) <= 0 or float(row.bbox_y1) <= 0 or float(row.bbox_x2) >= w - 1 or float(row.bbox_y2) >= h - 1
        if str(row.box_source) != "DETECTED":
            states.append("FOOTPOINT_AMBIGUOUS_NONDETECTED_BOX")
        elif exact_boundary:
            states.append("FOOTPOINT_CENSORED_EXACT_IMAGE_BOUNDARY")
        else:
            states.append("FOOTPOINT_GEOMETRY_INPUT_PRESENT_VISUAL_STATE_PENDING")
    foot["footpoint_observability_pre_visual"] = states
    foot["bbox_bottom_normalized"] = [float(v) / image_dims[str(r)][1] for v, r in zip(foot["bbox_y2"], foot["run_id"])]
    foot["bbox_height_normalized"] = [float(v) / image_dims[str(r)][1] for v, r in zip(foot["bbox_height"], foot["run_id"])]
    foot["bbox_bottom_is_physical_footpoint_claimed"] = False
    return inventory, foot


def freeze_pre_reference() -> None:
    files = sorted(path for path in PRE.rglob("*") if path.is_file() and path.name not in {"pre_reference_freeze_manifest.csv", "pre_reference_freeze_summary.json"})
    rows = [{"relative_path": str(path.relative_to(PRE)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in files]
    manifest = pd.DataFrame(rows)
    manifest.to_csv(PRE / "pre_reference_freeze_manifest.csv", index=False, encoding="utf-8-sig")
    root_hash = hashlib.sha256("\n".join(f"{row['relative_path']}|{row['bytes']}|{row['sha256']}" for row in rows).encode("utf-8")).hexdigest()
    write_json(PRE / "pre_reference_freeze_summary.json", {
        "status": "PRE_REFERENCE_FROZEN",
        "file_count": len(rows),
        "root_sha256": root_hash,
        "manual_reference_loaded": False,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip(),
    })


def verify_pre_reference() -> dict[str, Any]:
    manifest_path = PRE / "pre_reference_freeze_manifest.csv"
    if not manifest_path.exists():
        raise RuntimeError("pre-reference freeze manifest missing")
    manifest = pd.read_csv(manifest_path)
    failures = []
    for row in manifest.itertuples(index=False):
        path = PRE / str(row.relative_path)
        if not path.exists() or path.stat().st_size != int(row.bytes) or sha256_file(path) != str(row.sha256):
            failures.append(str(row.relative_path))
    if failures:
        raise RuntimeError(f"pre-reference freeze verification failed: {failures[:10]}")
    return json.loads((PRE / "pre_reference_freeze_summary.json").read_text(encoding="utf-8"))


def run_pre() -> None:
    ensure_dirs()
    if any("R04" in str(path).upper() for path in (OUTPUT, PRE, POST, PACK)):
        raise RuntimeError("R04 path contamination")
    regions = pd.read_parquet(Q95_REGIONS)
    regions = regions[regions["run_id"].isin(RUNS)].copy()
    edges = pd.read_parquet(P0_EDGES)
    edges = edges[edges["run_id"].isin(RUNS)].copy()
    shells = pd.read_parquet(SHELLS)
    shell_edges = pd.read_parquet(SHELL_EDGES)
    registry = pd.read_parquet(FRAME_REGISTRY)
    registry = registry[registry["run_id"].isin(RUNS)].copy()
    optical = pd.read_parquet(OPTICAL)
    optical = optical[optical["run_id"].isin(RUNS)].copy()
    p0 = pd.read_parquet(B0_PRE / "full_stream_p0_availability.parquet")

    family_map = strict_family_membership(regions, edges)
    write_table(family_map, PRE / "global_mutual_dominant_p0_family_membership")

    all_events, all_records = build_all_entity_events(shells, shell_edges, family_map, regions)
    write_table(all_events, PRE / "all_natural_corridor_family_frame_events")
    write_table(all_records, PRE / "all_natural_corridor_recurrence_records")
    write_table(select_top_family(all_records), PRE / "all_natural_corridor_top_family_records")

    trajectory, controls = source_and_null_trajectories(shells, registry, optical, regions, p0)
    write_table(trajectory, PRE / "r03_source_and_matched_null_trajectory_registry")
    write_table(controls, PRE / "r03_matched_null_control_ledger", parquet=False)
    shifted = shifted_candidate_regions(trajectory, registry, regions)
    write_table(shifted, PRE / "r03_source_and_matched_null_candidate_regions")
    events = frame_family_events(shifted, family_map, regions)
    events = events.merge(trajectory[["trajectory_id", "trajectory_offset", "source_frame_index", "effective_intervals_json", "corridor_center_deg", "corridor_width_deg"]], on=["trajectory_id", "trajectory_offset"], how="left", validate="many_to_one")
    write_table(events, PRE / "r03_source_and_matched_null_family_frame_events")
    lengths = {trajectory_id: len(SOURCE_FRAMES) for trajectory_id in trajectory["trajectory_id"].unique()}
    records = recurrence_records(events, lengths)
    top = select_top_family(records)
    write_table(records, PRE / "r03_source_and_matched_null_recurrence_records")
    write_table(top, PRE / "r03_source_and_matched_null_top_family_records")
    geometry = trajectory_geometry(events, top, trajectory)
    write_table(geometry, PRE / "r03_source_and_matched_null_trajectory_geometry")

    inventory, foot = calibration_inventory(registry, optical)
    write_table(inventory, PRE / "runtime_coarse_range_calibration_inventory", parquet=False)
    write_table(foot, PRE / "optical_footpoint_descriptor_inventory")
    write_table(registry, PRE / "development_frame_registry_snapshot")
    write_json(PRE / "analysis_contract.json", {
        "source": {"run_id": SOURCE_RUN, "entity_id": SOURCE_ENTITY, "frames": [SOURCE_START, SOURCE_END], "key_frames": list(KEY_FRAMES)},
        "family_primary_semantics": "MUTUAL_DOMINANT_P0_COMPONENT_NO_OPTIONAL_UNION",
        "b0_set_valued_family_burden_retained_as_secondary": True,
        "null_selection": "full 48-frame time shifts within R03; zero nominal optical detected-PERSON frames; nearest plus nuisance-only lexicographic response-density/P0/boundary matches; no recurrence outcome or reference used",
        "trajectory_expression": "descriptive affine corridor-to-family theta/range plus quadratic time smoothness; no absolute depth inversion without platform/camera geometry",
        "range_interface": "AVAILABLE_RANGE_INTERVAL or UNAVAILABLE; never a PERSON rejection gate",
        "manual_reference_loaded": False,
        "r04_accessed": False,
    })
    freeze_pre_reference()
    print(json.dumps({"status": "PRE_REFERENCE_COMPLETE_AND_FROZEN", "controls": len(controls), "events": len(events), "records": len(records)}, indent=2))


def family_reference_evaluation(
    records: pd.DataFrame,
    events: pd.DataFrame,
    reference: pd.DataFrame,
    mapping: pd.DataFrame,
) -> pd.DataFrame:
    mapping = mapping[["run_id", "entity_id", "target_id"]].drop_duplicates()
    events = events.copy()
    natural = events[events["trajectory_kind"] == "NATURAL_OPTICAL_CORRIDOR"].copy()
    natural["entity_id"] = natural["trajectory_id"].str.split("::").str[1]
    natural = natural.merge(mapping, on=["run_id", "entity_id"], how="left", validate="many_to_one")
    natural = natural.merge(reference, on=["run_id", "frame_index", "target_id"], how="left", validate="many_to_one")
    available = natural[natural["reference_range_m"].notna()].copy()
    available["reference_radial_support_retained"] = (available["range_min_m"] <= available["reference_range_m"]) & (available["range_max_m"] >= available["reference_range_m"])
    available["reference_theta_support_retained"] = (available["theta_min_deg"] <= available["reference_theta_deg"]) & (available["theta_max_deg"] >= available["reference_theta_deg"])
    available["reference_2d_support_retained"] = available["reference_radial_support_retained"] & available["reference_theta_support_retained"]
    summary = available.groupby(["trajectory_id", "strict_family_id"]).agg(
        reference_frame_count=("frame_index", "nunique"),
        reference_radial_support_retained_fraction=("reference_radial_support_retained", "mean"),
        reference_theta_support_retained_fraction=("reference_theta_support_retained", "mean"),
        reference_2d_support_retained_fraction=("reference_2d_support_retained", "mean"),
    ).reset_index()
    result = records.merge(summary, on=["trajectory_id", "strict_family_id"], how="left")
    result["reference_frame_count"] = result["reference_frame_count"].fillna(0).astype(int)
    return result


def footpoint_reference_diagnostic(
    foot: pd.DataFrame,
    registry: pd.DataFrame,
    reference: pd.DataFrame,
    mapping: pd.DataFrame,
) -> pd.DataFrame:
    inverse = mapping[["run_id", "entity_id", "target_id"]].drop_duplicates()
    registry = registry[["run_id", "sar_frame_index", "sar_timestamp_ms", "nominal_optical_frame_index", "sync_status"]]
    rows: list[dict[str, Any]] = []
    for ref in reference.itertuples(index=False):
        fragments = inverse[(inverse["run_id"] == ref.run_id) & (inverse["target_id"] == ref.target_id)]["entity_id"].astype(str).tolist()
        meta = registry[(registry["run_id"] == ref.run_id) & (registry["sar_frame_index"] == int(ref.frame_index))].iloc[0]
        for fragment in fragments:
            candidates = foot[(foot["run_id"] == ref.run_id) & (foot["raw_track_fragment_id"] == fragment)].copy()
            candidates = candidates[(candidates["timestamp_ms"] <= int(meta.sar_timestamp_ms)) & (candidates["timestamp_ms"] >= int(meta.sar_timestamp_ms) - 250)]
            if candidates.empty:
                rows.append({"run_id": ref.run_id, "frame_index": int(ref.frame_index), "target_id": ref.target_id, "entity_id": fragment, "range_geometry_status": "UNAVAILABLE_NO_CAUSAL_OPTICAL_OBSERVATION_IN_CONTEXT", "reference_range_m": float(ref.reference_range_m)})
                continue
            obs = candidates.sort_values(["timestamp_ms", "frame_index"]).iloc[-1]
            rows.append({
                "run_id": ref.run_id,
                "frame_index": int(ref.frame_index),
                "target_id": ref.target_id,
                "entity_id": fragment,
                "optical_frame_index": int(obs.frame_index),
                "optical_timestamp_ms": int(obs.timestamp_ms),
                "nominal_time_delta_ms": int(meta.sar_timestamp_ms) - int(obs.timestamp_ms),
                "range_geometry_status": obs.footpoint_observability_pre_visual,
                "bbox_bottom_normalized": float(obs.bbox_bottom_normalized),
                "bbox_height_normalized": float(obs.bbox_height_normalized),
                "reference_range_m": float(ref.reference_range_m),
                "sync_status": meta.sync_status,
                "runtime_range_interval_computed": False,
                "reason_not_computed": "missing camera K/height/pitch-roll/extrinsic/ground plane; bbox bottom not yet a validated footpoint",
            })
    return pd.DataFrame(rows)


def range_analysis(sweep: pd.DataFrame, reference: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary = sweep.groupby(["range_tolerance_m", "range_oracle_level"]).agg(
        row_count=("entity_id", "size"),
        N_family_before_median=("N_family_before", "median"),
        N_family_after_median=("N_family_after", "median"),
        N_family_after_mean=("N_family_after", "mean"),
        N_region_after_median=("N_region_after", "median"),
        A_candidate_m2_after_median=("A_candidate_m2_after", "median"),
        reference_radial_support_retained_fraction=("reference_range_retained", "mean"),
        non_singleton_fraction=("N_family_after", lambda x: float((x > 1).mean())),
        maximum_N_family_after=("N_family_after", "max"),
    ).reset_index().sort_values("range_tolerance_m", ascending=False)

    r02_ref = reference[reference["run_id"] == "R02ZF"].copy()
    r02_ref["prompt_range_group"] = np.select(
        [r02_ref["reference_range_m"].between(6, 8), r02_ref["reference_range_m"].between(12, 14)],
        ["R02_6_TO_8M", "R02_12_TO_14M"],
        default="R02_OTHER_RANGE",
    )
    r02 = sweep[sweep["run_id"] == "R02ZF"].merge(
        r02_ref[["run_id", "frame_index", "target_id", "prompt_range_group"]].drop_duplicates(),
        left_on=["run_id", "frame_index", "target_id_oracle"],
        right_on=["run_id", "frame_index", "target_id"],
        how="left",
    )
    r02_summary = r02.groupby(["range_tolerance_m", "prompt_range_group"]).agg(
        row_count=("entity_id", "size"),
        reference_range_median=("target_id_oracle", lambda _: math.nan),
        N_family_before_median=("N_family_before", "median"),
        N_family_after_median=("N_family_after", "median"),
        non_singleton_fraction=("N_family_after", lambda x: float((x > 1).mean())),
        reference_radial_support_retained_fraction=("reference_range_retained", "mean"),
    ).reset_index()
    med = r02_ref.groupby("prompt_range_group")["reference_range_m"].median().to_dict()
    r02_summary["reference_range_median"] = r02_summary["prompt_range_group"].map(med)

    counter = sweep.sort_values(["range_tolerance_m", "N_family_after", "N_family_before"], ascending=[True, False, False]).copy()
    counter["counterexample_kind"] = np.where(
        (counter["range_tolerance_m"] <= 0.05) & (counter["N_family_after"] > 1),
        "NEAR_EXACT_RANGE_STILL_MULTIPLE_FAMILIES",
        np.where((counter["range_tolerance_m"] == 3.0) & (counter["N_family_after"] > 1), "PM3M_STILL_MULTIPLE_FAMILIES", "OTHER"),
    )
    counter = counter[counter["counterexample_kind"] != "OTHER"]
    return summary, r02_summary, counter


def rank_corr(x: pd.Series, y: pd.Series) -> float:
    mask = x.notna() & y.notna()
    if mask.sum() < 3:
        return math.nan
    return float(x[mask].rank(method="average").corr(y[mask].rank(method="average")))


def make_post_summary(
    matched_top: pd.DataFrame,
    geometry: pd.DataFrame,
    reference_records: pd.DataFrame,
    range_summary: pd.DataFrame,
    calibration: pd.DataFrame,
    counterexamples: pd.DataFrame,
) -> dict[str, Any]:
    source = matched_top[matched_top["trajectory_kind"] == "SOURCE_MOVING_PERSON_CORRIDOR"].iloc[0]
    null = matched_top[matched_top["trajectory_kind"] == "MATCHED_NO_PERSON_TIME_SHIFT"]
    source_geom = geometry[geometry["trajectory_kind"] == "SOURCE_MOVING_PERSON_CORRIDOR"].iloc[0]
    null_geom = geometry[geometry["trajectory_kind"] == "MATCHED_NO_PERSON_TIME_SHIFT"]
    empirical_p = float((1 + (null["unique_frame_count"] >= source.unique_frame_count).sum()) / (1 + len(null)))
    source_ref = reference_records[(reference_records["trajectory_id"] == f"{SOURCE_RUN}::{SOURCE_ENTITY}") & (reference_records["strict_family_id"] == source.strict_family_id)]
    pm3 = range_summary[range_summary["range_tolerance_m"] == 3.0].iloc[0]
    pm2 = range_summary[range_summary["range_tolerance_m"] == 2.0].iloc[0]
    pm1 = range_summary[range_summary["range_tolerance_m"] == 1.0].iloc[0]
    missing = calibration[calibration["status"].astype(str).str.startswith("MISSING")]["interface"].tolist()
    strongest = counterexamples.sort_values(["N_family_after", "N_family_before"], ascending=False).iloc[0].to_dict() if len(counterexamples) else None
    return {
        "plain_language_conclusion": "现有时序里有真实的 recurrent-family 支持，但 matched no-PERSON 轨迹也能产生同类结构；它尚不足以替代粗距离。当前更应该补一维可校准的保守粗距离，目标做到约 ±2 m，±3 m 可用但仍常保留多 family，±1 m 在中位数上没有新增收益。",
        "scientific_states": ["TEMPORAL_RECURRENT_GROUNDING_SIGNAL_PRESENT_BUT_NOT_PERSON_SPECIFIC_ENOUGH", "COARSE_RANGE_STILL_DOMINANT", "CALIBRATED_RANGE_FEASIBILITY_BLOCKED_BY_MISSING_GEOMETRY"],
        "source_recurrent_unique_frames": int(source.unique_frame_count),
        "source_recurrent_occupancy": float(source.temporal_occupancy),
        "matched_null_count": int(len(null)),
        "matched_null_unique_frame_counts": null["unique_frame_count"].astype(int).tolist(),
        "matched_null_empirical_tail_probability": empirical_p,
        "source_reference_radial_support_retained_fraction": float(source_ref.iloc[0].reference_radial_support_retained_fraction) if len(source_ref) else None,
        "trajectory_geometry": {
            "source_theta_affine_median_abs_residual_deg": float(source_geom.theta_from_corridor_median_abs_residual_deg),
            "null_theta_affine_residual_range_deg": [float(null_geom.theta_from_corridor_median_abs_residual_deg.min()), float(null_geom.theta_from_corridor_median_abs_residual_deg.max())],
            "absolute_depth_recovered": False,
        },
        "runtime_coarse_range": {"status": "BLOCKED_BY_MISSING_CALIBRATION", "missing": missing, "footpoint_is_validated": False},
        "range_width_decision": {
            "recommended_target": "CONSERVATIVE_HALF_WIDTH_ABOUT_2M",
            "pm3_median_family_after": float(pm3.N_family_after_median),
            "pm2_median_family_after": float(pm2.N_family_after_median),
            "pm1_median_family_after": float(pm1.N_family_after_median),
            "more_precise_than_pm2_required_by_current_median": False,
        },
        "strongest_range_counterexample": strongest,
        "near_exact_range_still_multiple_family_counterexample_exists": bool((counterexamples["counterexample_kind"] == "NEAR_EXACT_RANGE_STILL_MULTIPLE_FAMILIES").any()) if len(counterexamples) else False,
        "next_priority": "IMPLEMENT_AND_CALIBRATE_A_CONSERVATIVE_OPTIONAL_COARSE_RANGE_INTERVAL_INTERFACE",
        "r04_accessed": False,
    }


def run_post() -> None:
    freeze = verify_pre_reference()
    reference = pd.read_parquet(REFERENCE)
    mapping = pd.read_csv(FRAGMENT_TARGET_MAP, encoding="utf-8-sig")
    sweep = pd.read_parquet(RANGE_SWEEP)
    records = pd.read_parquet(PRE / "all_natural_corridor_recurrence_records.parquet")
    events = pd.read_parquet(PRE / "all_natural_corridor_family_frame_events.parquet")
    matched_top = pd.read_parquet(PRE / "r03_source_and_matched_null_top_family_records.parquet")
    geometry = pd.read_parquet(PRE / "r03_source_and_matched_null_trajectory_geometry.parquet")
    foot = pd.read_parquet(PRE / "optical_footpoint_descriptor_inventory.parquet")
    registry = pd.read_parquet(PRE / "development_frame_registry_snapshot.parquet")
    calibration = pd.read_csv(PRE / "runtime_coarse_range_calibration_inventory.csv", encoding="utf-8-sig")

    ref_records = family_reference_evaluation(records, events, reference, mapping)
    write_table(ref_records, POST / "natural_recurrence_post_reference_support_audit")
    top_ref = select_top_family(ref_records)
    write_table(top_ref, POST / "natural_top_recurrence_post_reference_support_audit")

    foot_ref = footpoint_reference_diagnostic(foot, registry, reference, mapping)
    write_table(foot_ref, POST / "footpoint_reference_compatibility_diagnostic")
    available_foot = foot_ref[foot_ref["bbox_bottom_normalized"].notna()].copy()
    foot_summary = pd.DataFrame([{
        "available_rows": int(len(available_foot)),
        "bbox_bottom_vs_reference_range_spearman": rank_corr(available_foot["bbox_bottom_normalized"], available_foot["reference_range_m"]),
        "bbox_height_vs_reference_range_spearman": rank_corr(available_foot["bbox_height_normalized"], available_foot["reference_range_m"]),
        "runtime_range_interval_established": False,
        "reason": "descriptors are post-reference audited only; missing geometry and unvalidated footpoint semantics prevent a runtime interval",
    }])
    write_table(foot_summary, POST / "footpoint_descriptor_post_reference_summary", parquet=False)

    range_summary, r02_summary, counter = range_analysis(sweep, reference)
    write_table(range_summary, POST / "range_width_candidate_contraction_summary", parquet=False)
    write_table(r02_summary, POST / "r02_range_group_separation_summary", parquet=False)
    write_table(counter, POST / "range_counterexample_ledger")

    source_top = matched_top[matched_top["trajectory_kind"] == "SOURCE_MOVING_PERSON_CORRIDOR"].iloc[0]
    natural_counter = top_ref[
        (top_ref["reference_frame_count"] > 0)
        & (top_ref["reference_radial_support_retained_fraction"] < 0.5)
    ].sort_values(["admissible_frame_count", "temporal_occupancy", "unique_frame_count"], ascending=False)
    write_table(natural_counter, POST / "temporal_recurrence_reference_counterexamples")

    summary = make_post_summary(matched_top, geometry, ref_records, range_summary, calibration, counter)
    summary["pre_reference_freeze_root_sha256"] = freeze["root_sha256"]
    summary["footpoint_descriptor_summary"] = foot_summary.iloc[0].to_dict()
    summary["strongest_temporal_reference_counterexample"] = natural_counter.iloc[0].to_dict() if len(natural_counter) else None
    write_json(POST / "decision_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


def load_rgb(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"cannot read {path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def optical_for_sar(run_id: str, sar_frame: int, registry: pd.DataFrame, optical: pd.DataFrame, entity_id: str | None = None) -> tuple[np.ndarray, pd.Series | None, int]:
    meta = registry[(registry["run_id"] == run_id) & (registry["sar_frame_index"] == sar_frame)].iloc[0]
    optical_index = int(meta.nominal_optical_frame_index)
    run = optical[(optical["run_id"] == run_id)]
    root = Path(str(run.iloc[0]["optical_image_path"])).parent
    matches = sorted(root.glob(f"frame_{optical_index:06d}_t*ms.jpg"))
    if not matches:
        raise RuntimeError(f"missing optical {run_id} {optical_index}")
    image = load_rgb(matches[0])
    boxes = run[run["frame_index"] == optical_index]
    if entity_id is not None:
        boxes = boxes[boxes["raw_track_fragment_id"] == entity_id]
    box = boxes.iloc[0] if len(boxes) else None
    return image, box, optical_index


def sar_overlay(run_id: str, frame_index: int, keep_region_ids: set[str], regions: pd.DataFrame, registry: pd.DataFrame) -> np.ndarray:
    path = Path(str(registry[(registry["run_id"] == run_id) & (registry["sar_frame_index"] == frame_index)].iloc[0].sar_image_path))
    image = load_rgb(path)
    with np.load(Q95_MASKS / f"{run_id}_SARF{frame_index:06d}.npz") as archive:
        labels = archive["Q095"]
    frame_regions = regions[(regions["run_id"] == run_id) & (regions["frame_index"] == frame_index)]
    overlay = image.copy()
    for row in frame_regions.itertuples(index=False):
        mask = (labels == int(row.region_label)).astype(np.uint8)
        if not mask.any():
            continue
        contour, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        color = (40, 220, 80) if str(row.region_id) in keep_region_ids else (245, 200, 30)
        cv2.drawContours(overlay, contour, -1, color, 2)
    return overlay


def draw_bbox(ax: Any, box: pd.Series | None) -> None:
    if box is None:
        return
    x1, y1, x2, y2 = map(float, (box.bbox_x1, box.bbox_y1, box.bbox_x2, box.bbox_y2))
    ax.add_patch(plt.Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, edgecolor="#ff3b30", linewidth=2))


def draw_all_boxes(ax: Any, boxes: pd.DataFrame) -> None:
    colors = ["#ff3b30", "#00a6d6", "#ffcc00", "#9c27b0", "#00a65a"]
    for index, (_, box) in enumerate(boxes.iterrows()):
        x1, y1, x2, y2 = map(float, (box.bbox_x1, box.bbox_y1, box.bbox_x2, box.bbox_y2))
        ax.add_patch(plt.Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, edgecolor=colors[index % len(colors)], linewidth=2))


def figure_timeline(regions: pd.DataFrame, registry: pd.DataFrame, optical: pd.DataFrame) -> None:
    events = pd.read_parquet(PRE / "r03_source_and_matched_null_family_frame_events.parquet")
    top = pd.read_parquet(PRE / "r03_source_and_matched_null_top_family_records.parquet")
    trajectory = pd.read_parquet(PRE / "r03_source_and_matched_null_trajectory_registry.parquet")
    source_id = "R03_SOURCE_F447_F494"
    family_id = str(top[top["trajectory_id"] == source_id].iloc[0].strict_family_id)
    source_events = events[events["trajectory_id"] == source_id].copy()
    family_events = source_events[source_events["strict_family_id"] == family_id].copy()
    fig = plt.figure(figsize=(18, 13), constrained_layout=True)
    grid = fig.add_gridspec(5, 5, height_ratios=[1.05, 1.05, 0.8, 0.8, 0.8])
    for col, frame in enumerate(KEY_FRAMES):
        optical_image, box, optical_index = optical_for_sar(SOURCE_RUN, frame, registry, optical, SOURCE_ENTITY)
        ax = fig.add_subplot(grid[0, col]); ax.imshow(optical_image); draw_bbox(ax, box); ax.axis("off"); ax.set_title(f"Optical F{optical_index}\nraw bbox/corridor source")
        region_ids = set(family_events[family_events["frame_index"] == frame]["region_ids"].astype(str).str.split(";").explode().dropna())
        ax = fig.add_subplot(grid[1, col]); ax.imshow(sar_overlay(SOURCE_RUN, frame, region_ids, regions, registry)); ax.axis("off")
        n_family = int(source_events[source_events["frame_index"] == frame]["N_strict_family"].iloc[0])
        ax.set_title(f"SAR F{frame} | {'UNIQUE' if n_family == 1 else 'AMBIGUOUS'} | Nfamily={n_family}")
    frames = np.arange(SOURCE_START, SOURCE_END + 1)
    counts = source_events.groupby("frame_index")["N_strict_family"].first().reindex(frames)
    ax = fig.add_subplot(grid[2, :]); colors = ["#d73027" if value == 1 else "#4575b4" for value in counts]
    ax.bar(frames, counts, color=colors); ax.set_ylabel("strict P0 families"); ax.set_xlim(SOURCE_START - 0.5, SOURCE_END + 0.5); ax.set_title("Repeated uniqueness is an observation pattern; the green family persists through blue ambiguous intervals")
    traj = trajectory[trajectory["trajectory_id"] == source_id].set_index("frame_index")
    fam = family_events.set_index("frame_index")
    ax = fig.add_subplot(grid[3, :]); ax.fill_between(frames, traj.loc[frames, "corridor_center_deg"] - traj.loc[frames, "corridor_width_deg"] / 2, traj.loc[frames, "corridor_center_deg"] + traj.loc[frames, "corridor_width_deg"] / 2, alpha=0.2, color="#fdae61", label="optical corridor")
    ax.plot(fam.index, fam["theta_center_deg"], "o-", color="#1a9850", ms=3, label="recurrent SAR family theta descriptor"); ax.set_ylabel("theta (deg)"); ax.legend(loc="best")
    ax = fig.add_subplot(grid[4, :]); ax.plot(fam.index, fam["range_center_m"], "o-", color="#542788", ms=3); ax.set_ylabel("SAR family range descriptor (m)"); ax.set_xlabel("SAR frame"); ax.set_xlim(SOURCE_START - 0.5, SOURCE_END + 0.5)
    fig.suptitle("MOVING CORRIDOR × TEMPORAL FAMILY TIMELINE — R03ZF_I01_T0004, F447–F494", fontsize=17)
    fig.savefig(FIG / "01_r03_moving_corridor_temporal_family_timeline.png", dpi=180)
    plt.close(fig)


def figure_null_and_geometry() -> None:
    top = pd.read_parquet(PRE / "r03_source_and_matched_null_top_family_records.parquet")
    geom = pd.read_parquet(PRE / "r03_source_and_matched_null_trajectory_geometry.parquet")
    plot = top.merge(geom, on=["trajectory_id", "trajectory_kind", "strict_family_id"], suffixes=("", "_geom"))
    source = plot[plot["trajectory_kind"] == "SOURCE_MOVING_PERSON_CORRIDOR"]
    null = plot[plot["trajectory_kind"] == "MATCHED_NO_PERSON_TIME_SHIFT"].sort_values("trajectory_id")
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
    labels = ["SOURCE"] + [row.trajectory_id.replace("R03_NULL_", "") for row in null.itertuples(index=False)]
    values = [int(source.iloc[0].unique_frame_count)] + null["unique_frame_count"].astype(int).tolist()
    axes[0].bar(labels, values, color=["#d73027"] + ["#4575b4"] * len(null)); axes[0].set_title("Top-family repeated unique observations"); axes[0].tick_params(axis="x", rotation=45)
    values = [float(source.iloc[0].temporal_occupancy)] + null["temporal_occupancy"].astype(float).tolist()
    axes[1].bar(labels, values, color=["#d73027"] + ["#4575b4"] * len(null)); axes[1].set_title("Top-family temporal occupancy"); axes[1].tick_params(axis="x", rotation=45); axes[1].set_ylim(0, 1.05)
    values = [float(source.iloc[0].theta_from_corridor_median_abs_residual_deg)] + null["theta_from_corridor_median_abs_residual_deg"].astype(float).tolist()
    axes[2].bar(labels, values, color=["#d73027"] + ["#4575b4"] * len(null)); axes[2].set_title("Affine corridor↔family theta residual"); axes[2].set_ylabel("median absolute residual (deg)"); axes[2].tick_params(axis="x", rotation=45)
    fig.suptitle("Matched moving-trajectory controls: recurrence and smooth geometry are not unique to PERSON timing")
    fig.savefig(FIG / "02_matched_null_recurrence_and_trajectory_geometry.png", dpi=180)
    plt.close(fig)


def figure_range() -> None:
    summary = pd.read_csv(POST / "range_width_candidate_contraction_summary.csv", encoding="utf-8-sig").sort_values("range_tolerance_m", ascending=False)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    labels = ["near exact" if x <= 0.05 else f"±{x:g}m" for x in summary["range_tolerance_m"]]
    axes[0].plot(labels, summary["N_family_after_median"], "o-", color="#542788", lw=2); axes[0].axhline(1, color="gray", ls="--"); axes[0].set_ylabel("median N_family after range"); axes[0].set_title("±2m reaches the median singleton regime")
    axes[1].plot(labels, summary["non_singleton_fraction"], "o-", color="#d95f02", lw=2); axes[1].set_ylabel("fraction with N_family > 1"); axes[1].set_title("Residual ambiguity remains, especially at ±3m")
    for ax in axes: ax.tick_params(axis="x", rotation=35)
    fig.suptitle("B0 oracle aligned engineering target — support contraction, not final PERSON localization")
    fig.savefig(FIG / "03_range_width_candidate_contraction.png", dpi=180)
    plt.close(fig)


def figure_mechanism() -> None:
    summary = json.loads((POST / "decision_summary.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(16, 7)); ax.set_xlim(0, 16); ax.set_ylim(0, 8); ax.axis("off")
    boxes = [
        (0.4, 4.7, 3.2, 2.2, "OPTICAL STREAM\nraw fragment + bbox\n→ moving angular corridor\n→ optional range interval / UNAVAILABLE", "#e8f1fa"),
        (4.6, 4.7, 3.2, 2.2, "SAR IMAGE DOMAIN\nQ95 physical regions\n+ strict mutual-dominant P0\n+ set-valued alternatives retained", "#eef8e8"),
        (8.8, 5.25, 2.9, 1.1, "UNARY SUPPORT\nangle; optional coarse range;\nconditional recurrence", "#fff2cc"),
        (8.8, 3.75, 2.9, 1.1, "RELATIONAL SUPPORT\norder only when observable;\nshared response keeps order undefined", "#fce4d6"),
        (12.5, 4.55, 3.0, 2.35, f"AMBIGUITY RETAINED\nmany → few families\n±3m median → {summary['range_width_decision']['pm3_median_family_after']:.0f}\n±2m median → {summary['range_width_decision']['pm2_median_family_after']:.0f}\nnot identity / not final box", "#f4e6f7"),
    ]
    for x, y, w, h, text, color in boxes:
        patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", facecolor=color, edgecolor="#333", linewidth=1.5); ax.add_patch(patch); ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=11)
    for start, end in [((3.6, 5.8), (4.6, 5.8)), ((7.8, 5.8), (8.8, 5.8)), ((11.7, 5.8), (12.5, 5.8)), ((7.8, 5.2), (8.8, 4.3)), ((11.7, 4.3), (12.5, 5.1))]:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=15, linewidth=1.5, color="#444"))
    ax.text(8, 1.7, "Observation-conditioned authority: unavailable range falls back to angle-only; single-frame singleton remains local weak evidence; recurrence and range are evaluated separately before any combination.", ha="center", va="center", fontsize=11.5)
    ax.text(8, 7.55, "PERSON optical→SAR candidate-support contraction mechanism", ha="center", va="center", fontsize=18, weight="bold")
    fig.savefig(FIG / "04_core_candidate_support_contraction_mechanism.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def atlas_cases(cases: list[tuple[str, int, str, str | None]], name: str, regions: pd.DataFrame, registry: pd.DataFrame, optical: pd.DataFrame, top_family_map: dict[tuple[str, int], set[str]]) -> None:
    cols = 4
    rows = math.ceil(len(cases) / cols)
    fig, axes = plt.subplots(rows * 2, cols, figsize=(16, rows * 6), constrained_layout=True)
    axes = np.asarray(axes).reshape(rows * 2, cols)
    for idx, (run_id, frame, note, entity) in enumerate(cases):
        r, c = divmod(idx, cols)
        requested_entity = None if entity == "__ALL__" else entity
        image, box, optical_index = optical_for_sar(run_id, frame, registry, optical, requested_entity)
        axes[2 * r, c].imshow(image)
        if entity == "__ALL__":
            draw_all_boxes(axes[2 * r, c], optical[(optical["run_id"] == run_id) & (optical["frame_index"] == optical_index) & (optical["box_source"] == "DETECTED")])
        else:
            draw_bbox(axes[2 * r, c], box)
        axes[2 * r, c].axis("off"); axes[2 * r, c].set_title(f"{run_id} optical F{optical_index}\n{note}")
        axes[2 * r + 1, c].imshow(sar_overlay(run_id, frame, top_family_map.get((run_id, frame), set()), regions, registry)); axes[2 * r + 1, c].axis("off"); axes[2 * r + 1, c].set_title(f"{run_id} SAR F{frame}")
    for idx in range(len(cases), rows * cols):
        r, c = divmod(idx, cols); axes[2 * r, c].axis("off"); axes[2 * r + 1, c].axis("off")
    fig.savefig(FIG / name, dpi=150)
    plt.close(fig)


def run_figures() -> None:
    verify_pre_reference()
    regions = pd.read_parquet(Q95_REGIONS); regions = regions[regions["run_id"].isin(RUNS)]
    registry = pd.read_parquet(FRAME_REGISTRY); registry = registry[registry["run_id"].isin(RUNS)]
    optical = pd.read_parquet(OPTICAL); optical = optical[optical["run_id"].isin(RUNS)]
    figure_timeline(regions, registry, optical)
    figure_null_and_geometry()
    figure_range()
    figure_mechanism()

    events = pd.read_parquet(PRE / "r03_source_and_matched_null_family_frame_events.parquet")
    top = pd.read_parquet(PRE / "r03_source_and_matched_null_top_family_records.parquet")
    top_ids = top.set_index("trajectory_id")["strict_family_id"].to_dict()
    top_family_map: dict[tuple[str, int], set[str]] = {}
    source_events = events[(events["trajectory_id"] == "R03_SOURCE_F447_F494") & (events["strict_family_id"] == top_ids["R03_SOURCE_F447_F494"])]
    for row in source_events.itertuples(index=False):
        top_family_map[(SOURCE_RUN, int(row.frame_index))] = set(str(row.region_ids).split(";"))
    r03a = [(SOURCE_RUN, frame, "source recurrence visual review", SOURCE_ENTITY) for frame in range(447, 461)]
    r03b = [(SOURCE_RUN, frame, "source recurrence visual review", SOURCE_ENTITY) for frame in range(461, 476)]
    atlas_cases(r03a, "05_visual_atlas_r03_f447_f460.png", regions, registry, optical, top_family_map)
    atlas_cases(r03b, "06_visual_atlas_r03_f461_f475.png", regions, registry, optical, top_family_map)
    atlas_cases([("R02ZF", frame, "R02 dense/range-group review", "__ALL__") for frame in range(472, 495)], "07_visual_atlas_r02_f472_f494.png", regions, registry, optical, {})

    controls = pd.read_csv(PRE / "r03_matched_null_control_ledger.csv", encoding="utf-8-sig")
    null_cases: list[tuple[str, int, str, str | None]] = []
    for row in controls.itertuples(index=False):
        trajectory_id = str(row.trajectory_id); family_id = top_ids[trajectory_id]
        e = events[(events["trajectory_id"] == trajectory_id) & (events["strict_family_id"] == family_id)]
        unique = e[e["N_strict_family"] == 1]["frame_index"].astype(int).tolist()
        chosen = unique[:2] if unique else e["frame_index"].astype(int).tolist()[:2]
        for frame in chosen:
            region_ids = set(e[e["frame_index"] == frame]["region_ids"].astype(str).str.split(";").explode().dropna())
            top_family_map[(SOURCE_RUN, frame)] = region_ids
            null_cases.append((SOURCE_RUN, frame, trajectory_id, None))
    atlas_cases(null_cases, "08_visual_atlas_matched_null_key_events.png", regions, registry, optical, top_family_map)

    sweep = pd.read_parquet(RANGE_SWEEP)
    r01_pm3_success = sweep[(sweep["run_id"] == "R01ZF") & (sweep["range_tolerance_m"] == 3.0) & (sweep["N_family_after"] == 1)].sort_values("N_family_before", ascending=False).iloc[0]
    r01_pm3_failure = sweep[(sweep["run_id"] == "R01ZF") & (sweep["range_tolerance_m"] == 3.0)].sort_values("N_family_after", ascending=False).iloc[0]
    r01_pm2_failure = sweep[(sweep["run_id"] == "R01ZF") & (sweep["range_tolerance_m"] == 2.0)].sort_values("N_family_after", ascending=False).iloc[0]
    r01_cases = [
        ("R01ZF", int(r01_pm3_success.frame_index), f"±3m effective: Nfamily {int(r01_pm3_success.N_family_before)}→1", str(r01_pm3_success.entity_id)),
        ("R01ZF", int(r01_pm3_failure.frame_index), f"±3m residual: Nfamily {int(r01_pm3_failure.N_family_before)}→{int(r01_pm3_failure.N_family_after)}", str(r01_pm3_failure.entity_id)),
        ("R01ZF", int(r01_pm2_failure.frame_index), f"±2m residual: Nfamily {int(r01_pm2_failure.N_family_before)}→{int(r01_pm2_failure.N_family_after)}", str(r01_pm2_failure.entity_id)),
    ]
    atlas_cases(r01_cases, "09_visual_atlas_r01_range_success_and_failures.png", regions, registry, optical, {})

    decision = json.loads((POST / "decision_summary.json").read_text(encoding="utf-8"))
    temporal_counter = decision.get("strongest_temporal_reference_counterexample")
    if temporal_counter:
        all_events = pd.read_parquet(PRE / "all_natural_corridor_family_frame_events.parquet")
        ce = all_events[(all_events["trajectory_id"] == temporal_counter["trajectory_id"]) & (all_events["strict_family_id"] == temporal_counter["strict_family_id"])]
        ce_frames = ce["frame_index"].astype(int).tolist()
        chosen = [ce_frames[0], ce_frames[len(ce_frames)//2], ce_frames[-1]]
        for frame in chosen:
            top_family_map[(str(temporal_counter["run_id"]), frame)] = set(ce[ce["frame_index"] == frame]["region_ids"].astype(str).str.split(";").explode().dropna())
        atlas_cases([(str(temporal_counter["run_id"]), frame, "long recurrent wrong-family counterexample", str(temporal_counter["trajectory_id"]).split("::",1)[1]) for frame in chosen], "10_visual_atlas_temporal_reference_counterexample.png", regions, registry, optical, top_family_map)
    print(json.dumps({"status": "FIGURES_COMPLETE", "count": len(list(FIG.glob('*.png')))}, indent=2))


def write_report() -> None:
    summary = json.loads((POST / "decision_summary.json").read_text(encoding="utf-8"))
    top = pd.read_parquet(PRE / "r03_source_and_matched_null_top_family_records.parquet")
    geometry = pd.read_parquet(PRE / "r03_source_and_matched_null_trajectory_geometry.parquet")
    range_summary = pd.read_csv(POST / "range_width_candidate_contraction_summary.csv", encoding="utf-8-sig")
    r02 = pd.read_csv(POST / "r02_range_group_separation_summary.csv", encoding="utf-8-sig")
    foot = pd.read_csv(POST / "footpoint_descriptor_post_reference_summary.csv", encoding="utf-8-sig").iloc[0]
    source = top[top["trajectory_kind"] == "SOURCE_MOVING_PERSON_CORRIDOR"].iloc[0]
    null = top[top["trajectory_kind"] == "MATCHED_NO_PERSON_TIME_SHIFT"]
    source_geom = geometry[geometry["trajectory_kind"] == "SOURCE_MOVING_PERSON_CORRIDOR"].iloc[0]
    lines = [
        "# PERSON range-temporal decision study",
        "",
        "## Plain-language answer",
        "",
        f"**{summary['plain_language_conclusion']}**",
        "",
        "## Six direct answers",
        "",
        f"1. **R03 recurrence:** the five singleton frames select one strict mutual-dominant P0 family. That family is admissible for `{int(source.admissible_frame_count)}/{int(source.trajectory_length_frames)}` frames and unique on `{int(source.unique_frame_count)}` frames. This is a real recurrent SAR image-domain support pattern, not five unrelated blobs. It is not by itself PERSON-specific.",
        f"2. **Moving-corridor controls:** `{len(null)}` deterministic same-run, 48-frame, zero-detected-optical-PERSON time shifts retained the corridor trajectory exactly and matched SAR density/P0/boundary nuisance variables without using recurrence outcomes or reference. Their top-family unique counts were `{null.unique_frame_count.astype(int).tolist()}`; empirical source-tail probability is `{summary['matched_null_empirical_tail_probability']:.3f}`. The signal remains descriptive support, not a sufficient unary grounder.",
        f"3. **Trajectory geometry:** the source family's affine corridor-to-SAR-theta median residual is `{float(source_geom.theta_from_corridor_median_abs_residual_deg):.3f}°`, but matched clutter families also produce smooth low-dimensional trajectories. Absolute/coarse depth cannot be recovered because verified timing offset, platform pose/velocity, camera K, mounting geometry and ground plane are absent. SAR-family range evolution is a descriptor, not an optical range estimate.",
        "4. **Likely runtime range source:** a footpoint/ground-plane ray intersection remains the most direct legal interface, but it is not implementable from current files. Camera K, height, pitch/roll, camera-radar R/t, ground plane and synchronized platform pose are missing; bbox bottoms are not yet validated footpoints. Existing vehicle azimuth/depth candidates are withheld or geometrically incompatible.",
        f"5. **Required interval width:** B0 gives median `N_family` after range of `{summary['range_width_decision']['pm3_median_family_after']:.0f}` at ±3 m, `{summary['range_width_decision']['pm2_median_family_after']:.0f}` at ±2 m, and `{summary['range_width_decision']['pm1_median_family_after']:.0f}` at ±1 m. Therefore the engineering target is about **±2 m half-width** (roughly 4 m full interval). ±3 m is useful but often leaves alternatives; tighter than ±2 m has no additional median benefit in this development subset.",
        "6. **Single next priority:** implement and calibrate an optional conservative coarse-range interval interface. Keep recurrence records as secondary/backup evidence and a later complement, but do not spend the next cycle deepening recurrence as the sole mainline.",
        "",
        "## Matched-control interpretation",
        "",
        "The control preserves duration, per-frame corridor width, angular trajectory shape, scene/run, response-density profile, P0 availability and boundary profile. It breaks only the relation between that moving corridor and the time at which the optical PERSON was observed. Control selection is pre-reference and lexicographic on nuisance mismatch; it never sees recurrent-family outcomes.",
        "",
        "## Runtime coarse-range feasibility",
        "",
        f"The post-reference descriptor audit had `{int(foot.available_rows)}` rows. Rank correlations (`bbox bottom`, `bbox height`) versus reference range were `{float(foot.bbox_bottom_vs_reference_range_spearman):.3f}` and `{float(foot.bbox_height_vs_reference_range_spearman):.3f}`. These are oracle-aligned diagnostics only and do not establish a range function. No fixed ±2 m was appended to a point estimate.",
        "",
        "## R02 azimuth × range support",
        "",
        markdown_table(r02),
        "",
        "The prompted 6–8 m and 12–14 m strata are physically separated in radial support. Their range intervals can therefore partition families even when azimuth corridors overlap. This is an `AZIMUTH × RANGE` search-support result, not a final PERSON box or identity assignment.",
        "",
        "## Strongest counterexamples",
        "",
        f"- Temporal: `{summary.get('strongest_temporal_reference_counterexample')}`.",
        f"- Range: `{summary.get('strongest_range_counterexample')}`.",
        "- A visually clean, long P0 family in a no-PERSON matched window remains possible; therefore long continuity and smooth trajectory cannot be promoted to PERSON specificity.",
        f"- Near-exact range still multi-family counterexample present: `{summary.get('near_exact_range_still_multiple_family_counterexample_exists')}`. None exists in the 119-row B0 subset; the residual tail is at ±0.5/1/2/3 m, not near-exact range.",
        "",
        "## Visual review",
        "",
        "The raw optical/SAR atlases were reviewed directly. R03 confirms a coherent far-range family but an ambiguous small-scale doorway footpoint; matched no-PERSON windows contain equally clean background families; R02 shows multi-person occlusion and boundary censoring; R01 contains both a clean-footpoint ±3 m success and ±3/±2 m residual multi-family failures. See `VISUAL_REVIEW.md` and `post_reference_diagnostic_only/visual_review_ledger.csv`. Visual verdicts are not runtime rules.",
        "",
        "## Observation-conditioned authority",
        "",
        "- Clean, independently validated footpoint plus calibrated geometry: activate `AVAILABLE_RANGE_INTERVAL`.",
        "- Censored/ambiguous footpoint or missing geometry: `RANGE_UNAVAILABLE`, fall back to angle-only support.",
        "- Stable repeated recurrence: retain as conditional temporal unary support.",
        "- Single-frame singleton: local weak observation only.",
        "- Shared SAR response: retain `SHARED_RESPONSE_ORDER_UNDEFINED`.",
        "",
        "## Non-claims",
        "",
        "Q95 regions and P0 families are conditional SAR image-domain response supports. This study does not claim intrinsic RCS, recovered physical motion, causal cross-modal identity, final PERSON center, final box, calibrated probability, tracker, classifier, or P2/R04 confirmation. `REFERENCE_RADIAL_SUPPORT_RETAINED` is not true identity retention.",
        "",
        "## Core figures",
        "",
        "![timeline](figures/01_r03_moving_corridor_temporal_family_timeline.png)",
        "",
        "![matched null](figures/02_matched_null_recurrence_and_trajectory_geometry.png)",
        "",
        "![range](figures/03_range_width_candidate_contraction.png)",
        "",
        "![mechanism](figures/04_core_candidate_support_contraction_mechanism.png)",
        "",
        "## Frozen sequencing and scope",
        "",
        f"Pre-reference root SHA256: `{summary['pre_reference_freeze_root_sha256']}`. Manual reference was loaded only after that tree verified byte-for-byte. R04 accessed: `false`.",
    ]
    (OUTPUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_verified(source: Path, destination: Path, records: list[dict[str, Any]], role: str, scope: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if sha256_file(source) != sha256_file(destination):
        raise RuntimeError(f"copy hash mismatch: {source}")
    records.append({
        "relative_path": str(destination.relative_to(PACK)).replace("\\", "/"),
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
        "source_original_path": str(source.resolve()),
        "data_role": role,
        "runtime_or_oracle_scope": scope,
    })


def run_pack() -> None:
    verify_pre_reference()
    write_report()
    if PACK.exists():
        shutil.rmtree(PACK)
    PACK.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    for source in [TASK / "README.md", TASK / "run_person_range_temporal.py", TASK / "validate_person_range_temporal.py", OUTPUT / "REPORT.md", OUTPUT / "VISUAL_REVIEW.md"]:
        copy_verified(source, PACK / ("code" if source.parent == TASK and source.suffix == ".py" else "documentation") / source.name, records, "study code/documentation", "MIXED_SEE_REPORT")
    for root, scope in [(PRE, "PRE_REFERENCE_FROZEN"), (POST, "POST_REFERENCE_DIAGNOSTIC_ONLY"), (FIG, "FIGURE_MIXED_SEE_REPORT")]:
        for source in sorted(root.rglob("*")):
            if source.is_file():
                copy_verified(source, PACK / ("tables" if root != FIG else "figures") / root.name / source.name, records, "study artifact", scope)

    registry = pd.read_parquet(FRAME_REGISTRY); registry = registry[registry["run_id"].isin(RUNS)]
    optical = pd.read_parquet(OPTICAL); optical = optical[optical["run_id"].isin(RUNS)]
    selected: dict[tuple[str, int], str] = {}
    for frame in range(447, 495): selected[("R03ZF", frame)] = "R03_SOURCE_F447_F494"
    for frame in range(472, 495): selected[("R02ZF", frame)] = "R02_DENSE_RANGE_GROUP_F472_F494"
    controls = pd.read_csv(PRE / "r03_matched_null_control_ledger.csv", encoding="utf-8-sig")
    events = pd.read_parquet(PRE / "r03_source_and_matched_null_family_frame_events.parquet")
    top = pd.read_parquet(PRE / "r03_source_and_matched_null_top_family_records.parquet").set_index("trajectory_id")
    for control in controls.itertuples(index=False):
        family_id = str(top.loc[control.trajectory_id, "strict_family_id"])
        e = events[(events["trajectory_id"] == control.trajectory_id) & (events["strict_family_id"] == family_id)]
        frames = e[e["N_strict_family"] == 1]["frame_index"].astype(int).tolist()[:3]
        if not frames: frames = e["frame_index"].astype(int).tolist()[:3]
        for frame in frames: selected[("R03ZF", frame)] = f"MATCHED_NULL_{control.trajectory_id}"
    counter = pd.read_parquet(POST / "range_counterexample_ledger.parquet")
    for row in counter.sort_values(["counterexample_kind", "N_family_after"], ascending=[True, False]).drop_duplicates("counterexample_kind").itertuples(index=False):
        selected[(str(row.run_id), int(row.frame_index))] = str(row.counterexample_kind)
    sweep = pd.read_parquet(RANGE_SWEEP)
    success = sweep[(sweep["range_tolerance_m"] == 3.0) & (sweep["N_family_after"] == 1)].sort_values("N_family_before", ascending=False)
    if len(success):
        row = success.iloc[0]; selected[(str(row.run_id), int(row.frame_index))] = "PM3M_EFFECTIVE_CASE"

    optical_seen: set[str] = set()
    for (run_id, frame), role in sorted(selected.items()):
        meta = registry[(registry["run_id"] == run_id) & (registry["sar_frame_index"] == frame)].iloc[0]
        sar_source = Path(str(meta.sar_image_path))
        copy_verified(sar_source, PACK / "raw_sar" / run_id / sar_source.name, records, role, "RUNTIME_LEGAL_RAW_INPUT")
        mask = Q95_MASKS / f"{run_id}_SARF{frame:06d}.npz"
        copy_verified(mask, PACK / "selected_q95_npz" / run_id / mask.name, records, role, "RUNTIME_LEGAL_DERIVED_INTERFACE")
        run = optical[optical["run_id"] == run_id]
        root = Path(str(run.iloc[0]["optical_image_path"])).parent
        optical_index = int(meta.nominal_optical_frame_index)
        matches = sorted(root.glob(f"frame_{optical_index:06d}_t*ms.jpg"))
        if matches and str(matches[0]).lower() not in optical_seen:
            copy_verified(matches[0], PACK / "raw_optical" / run_id / matches[0].name, records, role, "RUNTIME_LEGAL_RAW_INPUT_NOMINAL_MAPPING_UNVERIFIED")
            optical_seen.add(str(matches[0]).lower())

    calibration_sources = [
        WORKSPACE / "output" / "pseudocolor_azimuth_calibration_20260803" / "CALIBRATION_PROTOCOL.md",
        FRAME_REGISTRY,
    ]
    for source in calibration_sources:
        copy_verified(source, PACK / "calibration_and_metadata" / source.name, records, "actual available calibration/metadata evidence", "RUNTIME_OR_WITHHELD_SEE_INVENTORY")

    readme = f"""# PERSON range-temporal decision review pack

This pack reproduces the frozen moving-corridor recurrence/matched-null analysis and the post-reference range decision audit.

- Pre-reference root hash: `{json.loads((POST / 'decision_summary.json').read_text(encoding='utf-8'))['pre_reference_freeze_root_sha256']}`.
- Raw optical uses nominal SAR-to-optical index mapping; zero offset remains unverified.
- Q95 NPZ key `Q095` is an integer region-label image. Region geometry and strict mutual-dominant P0 family membership are in the tables.
- R03 raw coverage: F447-F494 plus deterministic matched-null key events.
- R02 raw coverage: F472-F494.
- R01 includes a ±3 m success and requested residual range counterexamples when present.
- Missing calibration is explicit in `runtime_coarse_range_calibration_inventory.csv`; no camera parameters are guessed.
- Q95 families are SAR image-domain candidate support, not identity or final boxes.
- R04 was not accessed.
"""
    readme_path = PACK / "README.md"; readme_path.write_text(readme, encoding="utf-8")
    records.append({"relative_path": "README.md", "bytes": readme_path.stat().st_size, "sha256": sha256_file(readme_path), "source_original_path": "GENERATED", "data_role": "review instructions", "runtime_or_oracle_scope": "DOCUMENTATION"})
    manifest = pd.DataFrame(records).sort_values("relative_path")
    manifest.to_csv(PACK / "PACK_MANIFEST.csv", index=False, encoding="utf-8-sig")
    summary = {
        "raw_sar_count": int((manifest["relative_path"].str.startswith("raw_sar/")).sum()),
        "raw_optical_count": int((manifest["relative_path"].str.startswith("raw_optical/")).sum()),
        "selected_q95_npz_count": int((manifest["relative_path"].str.startswith("selected_q95_npz/")).sum()),
        "csv_count": int(manifest["relative_path"].str.endswith(".csv").sum()),
        "figure_count": int(manifest["relative_path"].str.endswith(".png").sum()),
        "manifest_entries": int(len(manifest)),
    }
    write_json(PACK / "PACK_SUMMARY.json", summary)
    if PACK_ZIP.exists(): PACK_ZIP.unlink()
    with zipfile.ZipFile(PACK_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(PACK.rglob("*")):
            if path.is_file(): archive.write(path, Path(PACK.name) / path.relative_to(PACK))
    summary["zip_bytes"] = PACK_ZIP.stat().st_size
    summary["zip_sha256"] = sha256_file(PACK_ZIP)
    write_json(PACK / "PACK_SUMMARY.json", summary)
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["pre", "post", "figures", "pack", "all"])
    args = parser.parse_args()
    if args.stage in {"pre", "all"}: run_pre()
    if args.stage in {"post", "all"}: run_post()
    if args.stage in {"figures", "all"}: run_figures()
    if args.stage in {"pack", "all"}: run_pack()


if __name__ == "__main__":
    main()
