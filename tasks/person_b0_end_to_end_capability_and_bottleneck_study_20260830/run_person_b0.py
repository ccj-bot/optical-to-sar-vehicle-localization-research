#!/usr/bin/env python3
"""PERSON-B0 end-to-end capability and bottleneck study.

This runner is intentionally diagnostic.  It keeps optical evidence as
time/azimuth/lifecycle support, keeps SAR response regions authoritative, and
uses post-reference data only in explicitly labelled oracle stages.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import shutil
import sys
import time
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
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
OUTPUT = WORKSPACE / "output" / "person_b0_end_to_end_capability_and_bottleneck_study_20260830"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference_oracle_diagnostic_only"
FIG = OUTPUT / "figures"
PACK = WORKSPACE / "review_packs" / "PERSON_B0_DEEP_REVIEW_PACK_20260830"
PACK_ZIP = PACK.with_suffix(".zip")
RUNS = ("R01ZF", "R02ZF", "R03ZF")
FRAMES_PER_RUN = 495
SAR_FPS = 30.0
OPTICAL_FPS = 18.0
CONTEXT_LOOKBACK_MS = 250
CONTEXT_LOOKAHEAD_MS = 0
FAMILY_SEMANTICS = "PERSON_B0_GRADED_P0_FAMILY_V1_OPTIONAL_COMPATIBLE"
Q95_EXCLUSION_DILATION_PX = 24

R2_ROOT = WORKSPACE / "output" / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830"
R2_PRE = R2_ROOT / "pre_reference"
R2_FIG = R2_ROOT / "figures"
Q95_MASKS = R2_PRE / "full_stream_q95_masks"
Q95_REGIONS = R2_PRE / "full_stream_q95_response_regions_pre_reference.parquet"
SHELLS = R2_PRE / "full_stream_optical_shells_pre_reference.parquet"
SHELL_EDGES = R2_PRE / "full_stream_shell_q95_pixel_edges_pre_reference.parquet"
FRAME_REGISTRY = R2_PRE / "full_stream_frame_registry_pre_reference.parquet"
OPTICAL = WORKSPACE / "output" / "person_optical_guided_sar_annotation_full_20260823" / "optical_person_frame_hypotheses.parquet"
SAR_ROOT = WORKSPACE / "output" / "pseudocolor_labelstudio_prep_20260722" / "frames" / "sar_pseudocolor"
P0_SCRIPT = WORKSPACE / "tasks" / "person_physics_guided_image_domain_study_20260824" / "run_p0_common_apparent_motion.py"
CMR_SCRIPT = WORKSPACE / "tasks" / "person_cmr_d0_common_residual_motion_mechanism_development_20260829" / "run_cmr_d0_development.py"
RANGE_REFERENCE = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "p1e_sar_only_response_interface"
    / "candidate_recall_semantic_split_v1"
    / "single_frame_candidate_recall"
    / "manual_reference_candidate_recall.csv"
)
FAMILY_GROUNDING = (
    WORKSPACE
    / "output"
    / "person_terg_r0_set_valued_explanation_constraint_propagation_20260829"
    / "post_reference"
    / "family_grounding_retention_post_reference.parquet"
)
R1_ANCHOR = (
    WORKSPACE
    / "output"
    / "person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829"
    / "post_reference"
    / "one_anchor_propagation_capacity_post_reference.parquet"
)
SEGMENT_ATLAS = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "terg_d0_temporal_event_response_graph_mechanism_exploration"
    / "pre_reference"
    / "temporal_segment_atlas_pre_reference.parquet"
)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "||".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20].upper()}"


def write_table(frame: pd.DataFrame, path: Path, parquet: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    if parquet:
        frame.to_parquet(path.with_suffix(".parquet"), index=False, compression="zstd")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def assert_scope() -> None:
    expected = Path(r"D:\profile\research\workspace").resolve()
    if WORKSPACE.resolve() != expected:
        raise RuntimeError(f"workspace mismatch: {WORKSPACE} != {expected}")
    for path in (TASK, OUTPUT, PACK, P0_SCRIPT, Q95_MASKS):
        if "old_work" in str(path).lower():
            raise RuntimeError(f"archive-only dependency: {path}")
    if any("R04" in str(path).upper() for path in (OUTPUT, PACK, Q95_MASKS, SHELL_EDGES)):
        raise RuntimeError("R04 path entered B0 scope")


def frame_metadata() -> pd.DataFrame:
    frame = pd.read_parquet(FRAME_REGISTRY)
    frame = frame[frame["run_id"].isin(RUNS)].copy()
    if set(frame["run_id"].unique()) != set(RUNS):
        raise RuntimeError("incomplete development run registry")
    return frame.sort_values(["run_id", "sar_frame_index"]).reset_index(drop=True)


def p0_config() -> dict[str, Any]:
    module = load_module("person_b0_p0_config", P0_SCRIPT)
    config = dict(module.ALGORITHM_CONFIG)
    config["lags"] = [1]
    return config


def _load_q95_exclusion(frame_uid: str, shape: tuple[int, int]) -> np.ndarray:
    with np.load(Q95_MASKS / f"{frame_uid}.npz") as archive:
        labels = archive["Q095"]
    if labels.shape != shape:
        raise RuntimeError(f"q95 shape mismatch for {frame_uid}: {labels.shape} != {shape}")
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (2 * Q95_EXCLUSION_DILATION_PX + 1, 2 * Q95_EXCLUSION_DILATION_PX + 1),
    )
    return cv2.dilate((labels > 0).astype(np.uint8), kernel, iterations=1).astype(bool)


def _cached_frame(module: Any, row: dict[str, Any], config: dict[str, Any]) -> Any:
    image_path = Path(str(row["sar_image_path"]))
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(image_path)
    metadata = {
        "run_id": str(row["run_id"]),
        "sar_frame_index": int(row["sar_frame_index"]),
        "sar_timestamp_ms": int(row["sar_timestamp_ms"]),
        "geometry": json.loads(row["geometry_json"]) if isinstance(row.get("geometry_json"), str) else row.get("geometry"),
        "theta_low_deg": float(row["theta_low_deg"]),
        "theta_high_deg": float(row["theta_high_deg"]),
        "annotations": [],
    }
    if not metadata["geometry"]:
        metadata["geometry"] = {
            "center_x_px": float(row["geometry_center_x_px"]),
            "center_y_px": float(row["geometry_center_y_px"]),
            "radius_px": float(row["geometry_radius_px"]),
            "outer_range_m": float(row["geometry_outer_range_m"]),
        }
    base_mask, fields = module.build_base_mask(metadata, image, config)
    exclusion = _load_q95_exclusion(str(row["sar_frame_uid"]), image.shape[:2])
    return module.CachedFrame(
        metadata=metadata,
        image_path=image_path,
        representation=module.build_representation(image, base_mask),
        display_gray=cv2.cvtColor(image, cv2.COLOR_BGR2GRAY),
        base_mask=base_mask,
        radial=fields["radial"],
        theta=fields["theta"],
        person_mask=exclusion,
    )


def _pair_result(module: Any, a: Any, b: Any, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    tracks = module.track_background_anchors(a, b, config)
    points = tracks["points"]
    tracked = tracks["tracked"]
    holdout = tracks["holdout"]
    n_fit = int((~holdout).sum())
    n_holdout = int(holdout.sum())
    fit_cells = module.spatial_cell_count(points[~holdout], float(config["split_cell_px"])) if len(points) else 0
    comparable = (
        tracks["reason"] == "OK"
        and n_fit >= int(config["min_fit_anchors"])
        and n_holdout >= int(config["min_holdout_anchors"])
        and fit_cells >= int(config["min_fit_spatial_cells"])
    )
    reason = tracks["reason"]
    if reason == "OK" and n_fit < int(config["min_fit_anchors"]):
        reason = "INSUFFICIENT_FIT_ANCHORS"
    elif reason == "OK" and n_holdout < int(config["min_holdout_anchors"]):
        reason = "INSUFFICIENT_HOLDOUT_ANCHORS"
    elif reason == "OK" and fit_cells < int(config["min_fit_spatial_cells"]):
        reason = "INSUFFICIENT_SPATIAL_COVERAGE"
    models = module.fit_models(points, tracked, holdout, a.metadata["geometry"], config) if len(points) else {}
    m1 = models.get("M1", {"available": False, "reason": reason})
    m0_med = m0_p90 = m1_med = m1_p90 = math.nan
    improves_median = improves_p90 = False
    if comparable and bool(m1.get("available")):
        p = points[holdout]
        t = tracked[holdout]
        m0_res = np.linalg.norm(t - p, axis=1)
        pred = module.predict_displacement(m1, p, a.metadata["geometry"])
        m1_res = np.linalg.norm((p + pred) - t, axis=1)
        m0_med, m0_p90 = float(np.median(m0_res)), float(np.quantile(m0_res, 0.90))
        m1_med, m1_p90 = float(np.median(m1_res)), float(np.quantile(m1_res, 0.90))
        improves_median = m1_med < m0_med
        improves_p90 = m1_p90 < m0_p90
    if not comparable or not bool(m1.get("available")):
        state = "P0_UNAVAILABLE"
    elif improves_median and improves_p90:
        state = "P0_AVAILABLE"
    else:
        state = "P0_UNRELIABLE_OR_AMBIGUOUS"
    row = {
        "run_id": str(a.metadata["run_id"]),
        "source_frame": int(a.metadata["sar_frame_index"]),
        "destination_frame": int(b.metadata["sar_frame_index"]),
        "source_frame_uid": f"{a.metadata['run_id']}_SARF{int(a.metadata['sar_frame_index']):06d}",
        "destination_frame_uid": f"{b.metadata['run_id']}_SARF{int(b.metadata['sar_frame_index']):06d}",
        "lag": 1,
        "p0_state": state,
        "reason": reason,
        "model_type": "M1" if bool(m1.get("available")) else "MISSING",
        "comparable": bool(comparable),
        "fit_anchor_count": n_fit,
        "holdout_anchor_count": n_holdout,
        "fit_spatial_cell_count": fit_cells,
        "valid_pixel_fraction": float(tracks["valid_fraction"]),
        "m0_holdout_median_px": m0_med,
        "m0_holdout_p90_px": m0_p90,
        "m1_holdout_median_px": m1_med,
        "m1_holdout_p90_px": m1_p90,
        "m1_improves_median": improves_median,
        "m1_improves_p90": improves_p90,
        "foreground_exclusion": f"SAR_ONLY_Q95_DILATED_{Q95_EXCLUSION_DILATION_PX}px",
        "manual_person_reference_used": False,
        "optical_identity_used": False,
        "semantics": "SAR_IMAGE_DOMAIN_COMMON_APPARENT_TRANSLATION_NOT_PHYSICAL_PLATFORM_MOTION",
    }
    model = None
    if bool(m1.get("available")):
        model = {
            "run_id": row["run_id"],
            "from_frame": row["source_frame"],
            "to_frame": row["destination_frame"],
            "lag": 1,
            "model": "M1",
            "p0_state": state,
            "parameters": m1["parameters"],
            "runtime_authority_allowed": state == "P0_AVAILABLE",
            "reference_used": False,
        }
    return row, model


def _process_run_p0(run_id: str, rows: list[dict[str, Any]], selected_pairs: set[int] | None = None) -> dict[str, Any]:
    module = load_module(f"person_b0_p0_worker_{run_id}", P0_SCRIPT)
    config = dict(module.ALGORITHM_CONFIG)
    config["lags"] = [1]
    rows = sorted(rows, key=lambda item: int(item["sar_frame_index"]))
    metrics: list[dict[str, Any]] = []
    models: list[dict[str, Any]] = []
    if selected_pairs is not None:
        for pair_index in sorted(selected_pairs):
            a = _cached_frame(module, rows[pair_index], config)
            b = _cached_frame(module, rows[pair_index + 1], config)
            metric, model = _pair_result(module, a, b, config)
            metrics.append(metric)
            if model is not None:
                models.append(model)
        return {"run_id": run_id, "metrics": metrics, "models": models}
    previous = None
    for index, row in enumerate(rows):
        current = _cached_frame(module, row, config)
        if previous is not None and (selected_pairs is None or index - 1 in selected_pairs):
            metric, model = _pair_result(module, previous, current, config)
            metrics.append(metric)
            if model is not None:
                models.append(model)
        previous = current
    return {"run_id": run_id, "metrics": metrics, "models": models}


def run_p0(workers: int, benchmark_pairs: int | None = None) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    registry = frame_metadata()
    selected: dict[str, set[int] | None] = {}
    if benchmark_pairs is not None:
        per_run = max(1, benchmark_pairs // len(RUNS))
        for run_id in RUNS:
            selected[run_id] = set(np.linspace(0, FRAMES_PER_RUN - 2, per_run, dtype=int).tolist())
    else:
        selected = {run_id: None for run_id in RUNS}
    started = time.perf_counter()
    futures = []
    results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=min(workers, len(RUNS))) as pool:
        for run_id in RUNS:
            rows = registry[registry["run_id"] == run_id].to_dict("records")
            futures.append(pool.submit(_process_run_p0, run_id, rows, selected[run_id]))
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"P0 {result['run_id']}: {len(result['metrics'])} adjacent pairs", flush=True)
    metrics = pd.DataFrame([row for result in results for row in result["metrics"]]).sort_values(["run_id", "source_frame"])
    models = [row for result in results for row in result["models"]]
    elapsed = time.perf_counter() - started
    summary = (
        metrics.groupby(["run_id", "p0_state"]).size().rename("pair_count").reset_index()
        if len(metrics)
        else pd.DataFrame(columns=["run_id", "p0_state", "pair_count"])
    )
    summary["elapsed_seconds"] = elapsed
    summary["pairs_per_second"] = len(metrics) / max(elapsed, 1e-9)
    if benchmark_pairs is not None:
        write_table(metrics, PRE / "p0_benchmark_pair_metrics", parquet=False)
        write_table(summary, PRE / "p0_benchmark_summary", parquet=False)
    else:
        write_table(metrics, PRE / "full_stream_p0_availability")
        write_jsonl(PRE / "full_stream_p0_models.jsonl", models)
        write_table(summary, PRE / "full_stream_p0_summary", parquet=False)
    print(summary.to_string(index=False), flush=True)
    return metrics, models


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
        if a != b:
            root, other = sorted((a, b))
            self.parent[other] = root


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_full_models() -> dict[tuple[str, int, int], dict[str, Any]]:
    rows = load_jsonl(PRE / "full_stream_p0_models.jsonl")
    return {
        (str(row["run_id"]), int(row["from_frame"]), int(row["to_frame"])): row
        for row in rows
        if row["run_id"] in RUNS and row["p0_state"] == "P0_AVAILABLE"
    }


def load_partial_models() -> dict[tuple[str, int, int], dict[str, Any]]:
    paths = [
        WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824" / "p0_common_apparent_motion" / "intermediate" / "R01_model_parameters_per_pair.jsonl",
        WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824" / "p1e_sar_only_response_interface" / "b0r_minimal" / "b0r_model_parameters_R02_R03.jsonl",
    ]
    result: dict[tuple[str, int, int], dict[str, Any]] = {}
    for path in paths:
        for row in load_jsonl(path):
            if row.get("run_id") not in RUNS or int(row.get("lag", -1)) != 1:
                continue
            if row.get("model") != "M1" or not bool(row.get("model_available")):
                continue
            result[(str(row["run_id"]), int(row["from_frame"]), int(row["to_frame"]))] = {
                "run_id": row["run_id"],
                "from_frame": int(row["from_frame"]),
                "to_frame": int(row["to_frame"]),
                "model": "M1",
                "parameters": row["model_state"]["parameters"],
                "p0_state": "FROZEN_PARTIAL_P0_AVAILABLE",
                "runtime_authority_allowed": True,
                "reference_used": False,
            }
    return result


def p0_matrix(model: dict[str, Any]) -> np.ndarray:
    dx, dy = model["parameters"]["translation_xy"]
    return np.asarray([[1.0, 0.0, float(dx)], [0.0, 1.0, float(dy)]], dtype=np.float32)


def build_graded_edges(models: dict[tuple[str, int, int], dict[str, Any]], scenario: str) -> pd.DataFrame:
    cached = PRE / f"{scenario.lower()}_graded_p0_q95_edges.parquet"
    if cached.exists():
        return pd.read_parquet(cached)
    regions = pd.read_parquet(Q95_REGIONS)
    regions = regions[regions["run_id"].isin(RUNS)].copy()
    groups = {(str(run), int(frame)): group.set_index("region_label") for (run, frame), group in regions.groupby(["run_id", "frame_index"])}
    rows: list[dict[str, Any]] = []
    for pair_number, ((run_id, source_frame, destination_frame), model) in enumerate(sorted(models.items()), start=1):
        source_uid = f"{run_id}_SARF{source_frame:06d}"
        destination_uid = f"{run_id}_SARF{destination_frame:06d}"
        with np.load(Q95_MASKS / f"{source_uid}.npz") as archive:
            source_labels = archive["Q095"]
        with np.load(Q95_MASKS / f"{destination_uid}.npz") as archive:
            destination_labels = archive["Q095"]
        height, width = source_labels.shape
        matrix = p0_matrix(model)
        source_regions = groups[(run_id, source_frame)]
        destination_regions = groups[(run_id, destination_frame)]
        for source_label, source_row in source_regions.iterrows():
            source_mask = source_labels == int(source_label)
            warped = cv2.warpAffine(
                source_mask.astype(np.float32), matrix, (width, height), flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT, borderValue=0.0,
            )
            warped_support = float(warped.sum())
            destination_candidates = sorted(set(destination_labels[warped > 0].astype(int).tolist()) - {0})
            for destination_label in destination_candidates:
                destination_mask = destination_labels == int(destination_label)
                intersection = float((warped * destination_mask).sum())
                if intersection <= 0.0:
                    continue
                destination_row = destination_regions.loc[destination_label]
                source_px = float(source_row["pixel_count"])
                destination_px = float(destination_row["pixel_count"])
                source_retention = intersection / max(warped_support, 1e-9)
                destination_explained = intersection / max(destination_px, 1e-9)
                soft_iou = intersection / max(warped_support + destination_px - intersection, 1e-9)
                rows.append({
                    "scenario": scenario,
                    "run_id": run_id,
                    "source_frame": source_frame,
                    "destination_frame": destination_frame,
                    "source_frame_uid": source_uid,
                    "destination_frame_uid": destination_uid,
                    "p0_state": model["p0_state"],
                    "p0_model": "M1",
                    "translation_dx_px": float(matrix[0, 2]),
                    "translation_dy_px": float(matrix[1, 2]),
                    "source_region_id": str(source_row["region_id"]),
                    "destination_region_id": str(destination_row["region_id"]),
                    "soft_intersection_px": intersection,
                    "source_support_px": source_px,
                    "warped_source_support_px": warped_support,
                    "destination_support_px": destination_px,
                    "source_retention": source_retention,
                    "destination_explained": destination_explained,
                    "soft_iou": soft_iou,
                    "upper_possible": True,
                    "reference_used": False,
                })
        if pair_number % 100 == 0 or pair_number == len(models):
            print(f"{scenario} graded edges {pair_number}/{len(models)}", flush=True)
    edges = pd.DataFrame(rows)
    if not len(edges):
        return edges
    source_max = edges.groupby(["run_id", "source_frame", "source_region_id"])["source_retention"].transform("max")
    destination_max = edges.groupby(["run_id", "destination_frame", "destination_region_id"])["destination_explained"].transform("max")
    edges["source_dominant"] = np.isclose(edges["source_retention"], source_max, rtol=1e-9, atol=1e-12)
    edges["destination_dominant"] = np.isclose(edges["destination_explained"], destination_max, rtol=1e-9, atol=1e-12)
    edges["optional_compatible"] = edges["source_dominant"] | edges["destination_dominant"]
    edges["lower_mutual_dominant"] = edges["source_dominant"] & edges["destination_dominant"]
    out_degree = edges[edges["optional_compatible"]].groupby(["run_id", "source_frame", "source_region_id"])["destination_region_id"].transform("nunique")
    in_degree = edges[edges["optional_compatible"]].groupby(["run_id", "destination_frame", "destination_region_id"])["source_region_id"].transform("nunique")
    edges["optional_out_degree"] = out_degree.reindex(edges.index).fillna(0).astype(int)
    edges["optional_in_degree"] = in_degree.reindex(edges.index).fillna(0).astype(int)
    edges["topology_ambiguity"] = np.select(
        [(edges["optional_out_degree"] > 1) & (edges["optional_in_degree"] > 1), edges["optional_out_degree"] > 1, edges["optional_in_degree"] > 1],
        ["SPLIT_AND_MERGE_LIKE", "SPLIT_LIKE", "MERGE_LIKE"],
        default="ONE_TO_ONE_LIKE_OR_NONOPTIONAL",
    )
    edges["family_authority_semantics"] = FAMILY_SEMANTICS
    write_table(edges, PRE / f"{scenario.lower()}_graded_p0_q95_edges")
    return edges


def optical_identity_map() -> pd.DataFrame:
    optical = pd.read_parquet(OPTICAL)
    optical = optical[(optical["run_id"].isin(RUNS)) & optical["raw_track_fragment_id"].notna()].copy()
    mapping = optical[["run_id", "raw_track_fragment_id", "optical_person_id"]].drop_duplicates()
    counts = mapping.groupby(["run_id", "raw_track_fragment_id"])["optical_person_id"].nunique()
    if int((counts > 1).sum()) != 0:
        raise RuntimeError("raw fragment maps to multiple offline optical identities")
    write_table(mapping, PRE / "raw_fragment_to_oracle_optical_identity", parquet=False)
    return mapping


def candidate_rows(mode: str, entity_kind: str) -> pd.DataFrame:
    shell_edges = pd.read_parquet(SHELL_EDGES)
    shell_edges = shell_edges[(shell_edges["run_id"].isin(RUNS)) & (shell_edges["mode"] == mode)].copy()
    rows = shell_edges[["run_id", "frame_index", "track_id", "region_id"]].drop_duplicates()
    rows = rows.rename(columns={"track_id": "raw_track_fragment_id"})
    if entity_kind == "RAW_FRAGMENT":
        rows["entity_id"] = rows["raw_track_fragment_id"].astype(str)
    elif entity_kind == "ORACLE_OPTICAL_IDENTITY":
        rows = rows.merge(optical_identity_map(), on=["run_id", "raw_track_fragment_id"], how="left", validate="many_to_one")
        rows = rows[rows["optical_person_id"].notna()].copy()
        rows["entity_id"] = rows["optical_person_id"].astype(str)
    else:
        raise ValueError(entity_kind)
    return rows[["run_id", "frame_index", "entity_id", "raw_track_fragment_id", "region_id"]].drop_duplicates()


def family_membership(candidates: pd.DataFrame, edges: pd.DataFrame, scenario: str) -> pd.DataFrame:
    candidates = candidates.drop_duplicates(["run_id", "frame_index", "entity_id", "region_id"]).copy()
    candidates["node"] = candidates["frame_index"].astype(str) + "|" + candidates["region_id"].astype(str)
    usable = edges[edges["optional_compatible"]].copy()
    source = candidates[["run_id", "frame_index", "entity_id", "region_id", "node"]].rename(
        columns={"frame_index": "source_frame", "region_id": "source_region_id", "node": "source_node"}
    )
    destination = candidates[["run_id", "frame_index", "entity_id", "region_id", "node"]].rename(
        columns={"frame_index": "destination_frame", "region_id": "destination_region_id", "node": "destination_node"}
    )
    linked = usable.merge(source, on=["run_id", "source_frame", "source_region_id"], how="inner")
    linked = linked.merge(destination, on=["run_id", "destination_frame", "destination_region_id", "entity_id"], how="inner")
    rows: list[dict[str, Any]] = []
    for (run_id, entity_id), group in candidates.groupby(["run_id", "entity_id"], sort=False):
        uf = UnionFind()
        for node in group["node"].astype(str):
            uf.add(node)
        e = linked[(linked["run_id"] == run_id) & (linked["entity_id"] == entity_id)]
        for edge in e.itertuples(index=False):
            uf.union(str(edge.source_node), str(edge.destination_node))
        for row in group.itertuples(index=False):
            root = uf.find(str(row.node))
            rows.append({
                "scenario": scenario,
                "run_id": run_id,
                "frame_index": int(row.frame_index),
                "entity_id": str(entity_id),
                "region_id": str(row.region_id),
                "family_id": stable_id("B0F", scenario, run_id, entity_id, root),
                "family_semantics": FAMILY_SEMANTICS,
            })
    membership = pd.DataFrame(rows)
    write_table(membership, PRE / f"{scenario.lower()}_candidate_family_membership")
    return membership


def interval_union_width(values: Iterable[str]) -> float:
    intervals: list[tuple[float, float]] = []
    for value in values:
        for low, high in json.loads(value):
            intervals.append((float(low), float(high)))
    if not intervals:
        return 0.0
    merged: list[list[float]] = []
    for low, high in sorted(intervals):
        if not merged or low > merged[-1][1]:
            merged.append([low, high])
        else:
            merged[-1][1] = max(merged[-1][1], high)
    return float(sum(high - low for low, high in merged))


def burden_frame(candidates: pd.DataFrame, membership: pd.DataFrame, scenario: str, mode: str, entity_kind: str) -> pd.DataFrame:
    regions = pd.read_parquet(Q95_REGIONS)[["run_id", "frame_index", "region_id", "pixel_count", "area_m2", "range_min_m", "range_max_m", "theta_min_deg", "theta_max_deg"]]
    data = candidates.merge(membership, on=["run_id", "frame_index", "entity_id", "region_id"], how="left", validate="many_to_one")
    data = data.merge(regions, on=["run_id", "frame_index", "region_id"], how="left", validate="many_to_one")
    shells = pd.read_parquet(SHELLS)
    shells = shells[(shells["run_id"].isin(RUNS)) & (shells["mode"] == mode)].copy()
    shells = shells.rename(columns={"track_id": "raw_track_fragment_id"})
    if entity_kind == "ORACLE_OPTICAL_IDENTITY":
        shells = shells.merge(optical_identity_map(), on=["run_id", "raw_track_fragment_id"], how="left", validate="many_to_one")
        shells["entity_id"] = shells["optical_person_id"]
    else:
        shells["entity_id"] = shells["raw_track_fragment_id"]
    shell_width = shells.groupby(["run_id", "frame_index", "entity_id"])["effective_intervals_json"].agg(interval_union_width).rename("search_width_deg").reset_index()
    frame_registry = frame_metadata().set_index(["run_id", "sar_frame_index"])
    rows: list[dict[str, Any]] = []
    for (run_id, frame_index, entity_id), group in data.groupby(["run_id", "frame_index", "entity_id"], sort=False):
        unique = group.drop_duplicates("region_id")
        meta = frame_registry.loc[(run_id, int(frame_index))]
        px_per_m = float(meta["geometry_radius_px"]) / float(meta["geometry_outer_range_m"])
        fan_span = float(meta["theta_high_deg"] - meta["theta_low_deg"])
        width_row = shell_width[(shell_width["run_id"] == run_id) & (shell_width["frame_index"] == frame_index) & (shell_width["entity_id"] == entity_id)]
        width = float(width_row.iloc[0]["search_width_deg"]) if len(width_row) else math.nan
        full_fan_px = 0.5 * float(meta["geometry_radius_px"]) ** 2 * math.radians(fan_span)
        search_px = full_fan_px * max(width, 0.0) / max(fan_span, 1e-9) if math.isfinite(width) else math.nan
        candidate_px = float(unique["pixel_count"].sum())
        rows.append({
            "scenario": scenario,
            "mode": mode,
            "entity_kind": entity_kind,
            "run_id": run_id,
            "frame_index": int(frame_index),
            "entity_id": str(entity_id),
            "N_region": int(unique["region_id"].nunique()),
            "N_family": int(group["family_id"].nunique()),
            "A_candidate_px": candidate_px,
            "A_candidate_m2": float(unique["area_m2"].sum()),
            "A_search_support_px_angular_sector_approx": search_px,
            "A_search_support_m2_angular_sector_approx": search_px / max(px_per_m * px_per_m, 1e-9),
            "A_candidate_over_A_search_support": candidate_px / max(search_px, 1e-9) if math.isfinite(search_px) else math.nan,
            "search_width_deg": width,
            "reference_used": False,
        })
    burden = pd.DataFrame(rows)
    joint_rows = []
    for (run_id, frame_index), group in burden.groupby(["run_id", "frame_index"]):
        counts = [int(value) for value in group["N_family"] if int(value) > 0]
        joint_rows.append({"run_id": run_id, "frame_index": int(frame_index), "N_joint_world": math.prod(counts) if len(counts) > 1 else (counts[0] if counts else 0)})
    burden = burden.merge(pd.DataFrame(joint_rows), on=["run_id", "frame_index"], how="left")
    return burden


def build_unit_registry(current_burden: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {"unit_id": "R01_FULL", "run_id": "R01ZF", "start_frame": 0, "end_frame": 494, "unit_kind": "FULL_STREAM", "overlap_cluster_id": "R01_FULL_CLUSTER", "selection_rule": "complete development stream"},
        {"unit_id": "R02_FULL", "run_id": "R02ZF", "start_frame": 0, "end_frame": 494, "unit_kind": "FULL_STREAM", "overlap_cluster_id": "R02_FULL_CLUSTER", "selection_rule": "complete development stream"},
        {"unit_id": "R03_FULL", "run_id": "R03ZF", "start_frame": 0, "end_frame": 494, "unit_kind": "FULL_STREAM", "overlap_cluster_id": "R03_FULL_CLUSTER", "selection_rule": "complete development stream"},
        {"unit_id": "R02_CRITICAL_CHAIN_F450_F494", "run_id": "R02ZF", "start_frame": 450, "end_frame": 494, "unit_kind": "EARLY_TO_RELATION_CHAIN", "overlap_cluster_id": "R02_F450_F494_CLUSTER", "selection_rule": "user-required fixed critical chain"},
        {"unit_id": "R02_EARLY_F450_F475", "run_id": "R02ZF", "start_frame": 450, "end_frame": 475, "unit_kind": "LOWER_AMBIGUITY_CONTEXT", "overlap_cluster_id": "R02_F450_F494_CLUSTER", "selection_rule": "user-required early subsection"},
        {"unit_id": "R02_RELATION_F487_F494", "run_id": "R02ZF", "start_frame": 487, "end_frame": 494, "unit_kind": "DENSE_RELATION", "overlap_cluster_id": "R02_F450_F494_CLUSTER", "selection_rule": "user-required relation window"},
        {"unit_id": "R03_NATURAL_SINGLETON_F450_F475", "run_id": "R03ZF", "start_frame": 450, "end_frame": 475, "unit_kind": "NATURAL_SINGLETON", "overlap_cluster_id": "R03_F450_F475_CLUSTER", "selection_rule": "user-required natural-singleton window"},
        {"unit_id": "R03_SINGLETON_CORE_F454_F471", "run_id": "R03ZF", "start_frame": 454, "end_frame": 471, "unit_kind": "NATURAL_SINGLETON_CORE", "overlap_cluster_id": "R03_F450_F475_CLUSTER", "selection_rule": "user-required core review window"},
    ]
    for run_id in RUNS:
        run = current_burden[current_burden["run_id"] == run_id]
        per_frame = run.groupby("frame_index").agg(entity_count=("entity_id", "nunique"), mean_regions=("N_region", "mean"))
        if not len(per_frame):
            continue
        rolling = per_frame["mean_regions"].rolling(10, min_periods=5).mean()
        multi_end = int(rolling.idxmax())
        early_start = int(per_frame.index.min())
        late_end = int(per_frame.index.max())
        rows.extend([
            {"unit_id": f"{run_id}_MECHANICAL_EARLY", "run_id": run_id, "start_frame": early_start, "end_frame": min(early_start + 9, 494), "unit_kind": "EARLY", "overlap_cluster_id": f"{run_id}_MECHANICAL_EARLY_CLUSTER", "selection_rule": "first ten frames with runtime candidate burden"},
            {"unit_id": f"{run_id}_MECHANICAL_MAX_BURDEN", "run_id": run_id, "start_frame": max(0, multi_end - 9), "end_frame": multi_end, "unit_kind": "MULTI_OR_AMBIGUOUS", "overlap_cluster_id": f"{run_id}_MECHANICAL_MAX_CLUSTER", "selection_rule": "maximum fixed ten-frame rolling mean N_region"},
            {"unit_id": f"{run_id}_MECHANICAL_BOUNDARY", "run_id": run_id, "start_frame": max(0, late_end - 9), "end_frame": late_end, "unit_kind": "BOUNDARY_OR_DORMANCY", "overlap_cluster_id": f"{run_id}_MECHANICAL_BOUNDARY_CLUSTER", "selection_rule": "last ten frames with runtime candidate burden"},
        ])
    registry = pd.DataFrame(rows).drop_duplicates("unit_id")
    write_table(registry, PRE / "development_diagnostic_unit_registry", parquet=False)
    return registry


def aggregate_units(burden: pd.DataFrame, units: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for unit in units.itertuples(index=False):
        subset = burden[(burden["run_id"] == unit.run_id) & burden["frame_index"].between(int(unit.start_frame), int(unit.end_frame))]
        for entity_id, group in subset.groupby("entity_id"):
            rows.append({
                "scenario": str(group.iloc[0]["scenario"]),
                "unit_id": unit.unit_id,
                "overlap_cluster_id": unit.overlap_cluster_id,
                "run_id": unit.run_id,
                "entity_id": entity_id,
                "observed_frame_count": int(group["frame_index"].nunique()),
                "N_region_median": float(group["N_region"].median()),
                "N_region_mean": float(group["N_region"].mean()),
                "N_region_max": int(group["N_region"].max()),
                "N_family_median": float(group["N_family"].median()),
                "N_family_mean": float(group["N_family"].mean()),
                "N_family_max": int(group["N_family"].max()),
                "A_candidate_px_median": float(group["A_candidate_px"].median()),
                "A_candidate_m2_median": float(group["A_candidate_m2"].median()),
                "A_candidate_over_A_search_support_median": float(group["A_candidate_over_A_search_support"].median()),
                "N_joint_world_median_secondary": float(group["N_joint_world"].median()),
            })
    return pd.DataFrame(rows)


def load_range_reference_filtered() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with RANGE_REFERENCE.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("run_id") not in RUNS:
                continue
            rows.append({
                "run_id": row["run_id"],
                "frame_index": int(row["frame_index"]),
                "target_id": row["target_id"],
                "reference_range_m": float(row["reference_range_m"]),
                "reference_theta_deg": float(row["reference_theta_deg"]),
                "reference_support_status": row["reference_support_status"],
            })
    frame = pd.DataFrame(rows).drop_duplicates(["run_id", "frame_index", "target_id"])
    write_table(frame, POST / "r01_r02_r03_manual_range_reference_oracle_only")
    return frame


def entity_target_map() -> tuple[pd.DataFrame, pd.DataFrame]:
    grounding = pd.read_parquet(FAMILY_GROUNDING)
    grounding = grounding[grounding["run_id"].isin(RUNS) & grounding["dominant_target_id_offline"].notna()].copy()
    raw_counts = grounding.groupby(["run_id", "track_id", "dominant_target_id_offline"]).size().rename("support_rows").reset_index()
    raw_counts = raw_counts.sort_values(["run_id", "track_id", "support_rows", "dominant_target_id_offline"], ascending=[True, True, False, True])
    raw = raw_counts.drop_duplicates(["run_id", "track_id"]).rename(columns={"track_id": "entity_id", "dominant_target_id_offline": "target_id"})
    raw["entity_kind"] = "RAW_FRAGMENT"
    identity = optical_identity_map().merge(raw[["run_id", "entity_id", "target_id"]].rename(columns={"entity_id": "raw_track_fragment_id"}), on=["run_id", "raw_track_fragment_id"], how="left")
    identity_counts = identity.dropna(subset=["target_id"]).groupby(["run_id", "optical_person_id", "target_id"]).size().rename("support_fragments").reset_index()
    identity_counts = identity_counts.sort_values(["run_id", "optical_person_id", "support_fragments", "target_id"], ascending=[True, True, False, True])
    oracle = identity_counts.drop_duplicates(["run_id", "optical_person_id"]).rename(columns={"optical_person_id": "entity_id"})
    oracle["entity_kind"] = "ORACLE_OPTICAL_IDENTITY"
    write_table(raw, POST / "raw_fragment_to_offline_target_mapping_oracle_only", parquet=False)
    write_table(oracle, POST / "oracle_optical_identity_to_offline_target_mapping", parquet=False)
    return raw, oracle


def range_sweep(membership: pd.DataFrame, entity_kind: str, scenario: str) -> pd.DataFrame:
    candidates = membership.merge(pd.read_parquet(Q95_REGIONS)[["run_id", "frame_index", "region_id", "pixel_count", "area_m2", "range_min_m", "range_max_m"]], on=["run_id", "frame_index", "region_id"], how="left")
    raw_map, oracle_map = entity_target_map()
    mapping = oracle_map if entity_kind == "ORACLE_OPTICAL_IDENTITY" else raw_map
    candidates = candidates.merge(mapping[["run_id", "entity_id", "target_id"]], on=["run_id", "entity_id"], how="left")
    reference = load_range_reference_filtered()
    candidates = candidates.merge(reference, on=["run_id", "frame_index", "target_id"], how="inner")
    rows: list[dict[str, Any]] = []
    for tolerance in (3.0, 2.0, 1.0, 0.5, 0.05):
        keep = candidates[
            (candidates["range_max_m"] >= candidates["reference_range_m"] - tolerance)
            & (candidates["range_min_m"] <= candidates["reference_range_m"] + tolerance)
        ].copy()
        grouped_keep = {key: group for key, group in keep.groupby(["run_id", "frame_index", "entity_id"])}
        for key, group in candidates.groupby(["run_id", "frame_index", "entity_id"]):
            retained = grouped_keep.get(key, group.iloc[0:0])
            unique = retained.drop_duplicates("region_id")
            rows.append({
                "scenario": scenario,
                "entity_kind": entity_kind,
                "run_id": key[0],
                "frame_index": int(key[1]),
                "entity_id": key[2],
                "target_id_oracle": str(group.iloc[0]["target_id"]),
                "range_tolerance_m": tolerance,
                "range_oracle_level": "ORACLE_RANGE_NEAR_EXACT" if tolerance == 0.05 else f"COARSE_RANGE_PM_{tolerance:g}M",
                "N_region_before": int(group["region_id"].nunique()),
                "N_region_after": int(unique["region_id"].nunique()),
                "N_family_before": int(group["family_id"].nunique()),
                "N_family_after": int(retained["family_id"].nunique()),
                "A_candidate_px_before": float(group.drop_duplicates("region_id")["pixel_count"].sum()),
                "A_candidate_px_after": float(unique["pixel_count"].sum()),
                "A_candidate_m2_before": float(group.drop_duplicates("region_id")["area_m2"].sum()),
                "A_candidate_m2_after": float(unique["area_m2"].sum()),
                "reference_range_retained": bool(len(retained)),
                "oracle_diagnostic_only": True,
            })
    result = pd.DataFrame(rows)
    write_table(result, POST / f"{scenario.lower()}_coarse_range_oracle_sweep")
    return result


def _shell_centers(entity_kind: str) -> pd.DataFrame:
    shells = pd.read_parquet(SHELLS)
    shells = shells[(shells["run_id"].isin(RUNS)) & (shells["mode"] == "CAUSAL_REPLAY")].copy()
    shells = shells.rename(columns={"track_id": "raw_track_fragment_id"})
    if entity_kind == "ORACLE_OPTICAL_IDENTITY":
        shells = shells.merge(optical_identity_map(), on=["run_id", "raw_track_fragment_id"], how="left")
        shells["entity_id"] = shells["optical_person_id"]
    else:
        shells["entity_id"] = shells["raw_track_fragment_id"]
    def center(values: Iterable[str]) -> float:
        intervals = [pair for value in values for pair in json.loads(value)]
        if not intervals:
            return math.nan
        weights = np.asarray([max(float(high) - float(low), 1e-6) for low, high in intervals])
        centers = np.asarray([(float(low) + float(high)) / 2.0 for low, high in intervals])
        return float(np.average(centers, weights=weights))
    return shells.groupby(["run_id", "frame_index", "entity_id"])["effective_intervals_json"].agg(center).rename("optical_shell_theta_center_deg").reset_index()


def _apply_range_to_membership(membership: pd.DataFrame, entity_kind: str, tolerance: float | None) -> pd.DataFrame:
    regions = pd.read_parquet(Q95_REGIONS)[["run_id", "frame_index", "region_id", "range_min_m", "range_max_m", "theta_min_deg", "theta_max_deg"]]
    data = membership.merge(regions, on=["run_id", "frame_index", "region_id"], how="left")
    if tolerance is None:
        return data
    raw_map, oracle_map = entity_target_map()
    mapping = oracle_map if entity_kind == "ORACLE_OPTICAL_IDENTITY" else raw_map
    data = data.merge(mapping[["run_id", "entity_id", "target_id"]], on=["run_id", "entity_id"], how="left")
    reference = load_range_reference_filtered()
    data = data.merge(reference[["run_id", "frame_index", "target_id", "reference_range_m"]], on=["run_id", "frame_index", "target_id"], how="left")
    has_ref = data["reference_range_m"].notna()
    overlaps = (data["range_max_m"] >= data["reference_range_m"] - tolerance) & (data["range_min_m"] <= data["reference_range_m"] + tolerance)
    return data[(~has_ref) | overlaps].copy()


def one_anchor_effect(
    membership: pd.DataFrame,
    entity_kind: str,
    units: pd.DataFrame,
    scenario: str,
    range_tolerance: float | None = None,
) -> pd.DataFrame:
    data = _apply_range_to_membership(membership, entity_kind, range_tolerance)
    shell_centers = _shell_centers(entity_kind)
    data = data.merge(shell_centers, on=["run_id", "frame_index", "entity_id"], how="left")
    raw_map, oracle_map = entity_target_map()
    mapping = oracle_map if entity_kind == "ORACLE_OPTICAL_IDENTITY" else raw_map
    if "target_id" not in data.columns:
        data = data.merge(mapping[["run_id", "entity_id", "target_id"]], on=["run_id", "entity_id"], how="left")
    reference = load_range_reference_filtered()
    if "reference_range_m" not in data.columns:
        data = data.merge(reference[["run_id", "frame_index", "target_id", "reference_range_m"]], on=["run_id", "frame_index", "target_id"], how="left")
    data["reference_range_supported"] = (
        data["reference_range_m"].notna()
        & (data["range_min_m"] <= data["reference_range_m"])
        & (data["range_max_m"] >= data["reference_range_m"])
    )
    rows: list[dict[str, Any]] = []
    for unit in units.itertuples(index=False):
        subset = data[(data["run_id"] == unit.run_id) & data["frame_index"].between(int(unit.start_frame), int(unit.end_frame))].copy()
        entities = sorted(subset["entity_id"].dropna().astype(str).unique())
        if len(entities) < 2:
            continue
        for anchor_entity in entities:
            anchor = subset[subset["entity_id"] == anchor_entity]
            support = anchor.groupby("family_id")["reference_range_supported"].sum().sort_values(ascending=False)
            if not len(support) or int(support.iloc[0]) <= 0:
                continue
            top = support[support == support.iloc[0]].index.astype(str).tolist()
            if len(top) != 1:
                continue
            anchor_family = top[0]
            anchor_rows = anchor[anchor["family_id"] == anchor_family]
            for other_entity in entities:
                if other_entity == anchor_entity:
                    continue
                other = subset[subset["entity_id"] == other_entity]
                families = sorted(other["family_id"].astype(str).unique())
                retained: list[str] = []
                contradicted: list[str] = []
                for family_id in families:
                    candidate = other[other["family_id"] == family_id]
                    decisive_contradiction = False
                    shared_frames = sorted(set(anchor_rows["frame_index"]) & set(candidate["frame_index"]))
                    for frame_index in shared_frames:
                        a_frame = anchor_rows[anchor_rows["frame_index"] == frame_index]
                        b_frame = candidate[candidate["frame_index"] == frame_index]
                        a_opt = a_frame["optical_shell_theta_center_deg"].dropna()
                        b_opt = b_frame["optical_shell_theta_center_deg"].dropna()
                        if not len(a_opt) or not len(b_opt):
                            continue
                        optical_delta = float(b_opt.iloc[0] - a_opt.iloc[0])
                        if abs(optical_delta) <= 1.0:
                            continue
                        desired = 1 if optical_delta > 0 else -1
                        compatible = False
                        for ar in a_frame.itertuples(index=False):
                            for br in b_frame.itertuples(index=False):
                                overlap = not (float(br.theta_min_deg) > float(ar.theta_max_deg) or float(ar.theta_min_deg) > float(br.theta_max_deg))
                                if overlap:
                                    compatible = True
                                    break
                                sar_delta = ((float(br.theta_min_deg) + float(br.theta_max_deg)) - (float(ar.theta_min_deg) + float(ar.theta_max_deg))) / 2.0
                                if (1 if sar_delta > 0 else -1) == desired:
                                    compatible = True
                                    break
                            if compatible:
                                break
                        if not compatible:
                            decisive_contradiction = True
                            break
                    if decisive_contradiction:
                        contradicted.append(family_id)
                    else:
                        retained.append(family_id)
                rows.append({
                    "scenario": scenario,
                    "unit_id": unit.unit_id,
                    "overlap_cluster_id": unit.overlap_cluster_id,
                    "run_id": unit.run_id,
                    "anchor_entity_id": anchor_entity,
                    "anchor_family_id_oracle": anchor_family,
                    "other_entity_id": other_entity,
                    "N_family_before": len(families),
                    "N_family_after": len(retained),
                    "N_family_deleted": len(contradicted),
                    "range_tolerance_m_if_combined": range_tolerance if range_tolerance is not None else math.nan,
                    "relation_semantics": "SET_VALUED_RELATIVE_ANGULAR_ORDER_WITH_INTERVAL_OVERLAP_UNDEFINED",
                    "anchor_selection": "UNIQUE_MAX_REFERENCE_RANGE_SUPPORT_ORACLE_ONLY",
                    "oracle_diagnostic_only": True,
                })
    result = pd.DataFrame(rows)
    write_table(result, POST / f"{scenario.lower()}_one_correct_unary_anchor_effect")
    return result


def legacy_anchor_audit() -> pd.DataFrame:
    anchor = pd.read_parquet(R1_ANCHOR)
    segments = pd.read_parquet(SEGMENT_ATLAS)[["segment_id", "run_id", "start_sar_frame", "end_sar_frame", "overlap_cluster_id"]] if "overlap_cluster_id" in pd.read_parquet(SEGMENT_ATLAS).columns else pd.read_parquet(SEGMENT_ATLAS)[["segment_id", "run_id", "start_sar_frame", "end_sar_frame"]]
    anchor = anchor.merge(segments, on="segment_id", how="left")
    p0 = pd.read_parquet(PRE / "full_stream_p0_availability.parquet")
    coverage = []
    for row in anchor.itertuples(index=False):
        pairs = p0[(p0["run_id"] == row.run_id) & p0["source_frame"].between(int(row.start_sar_frame), max(int(row.start_sar_frame), int(row.end_sar_frame) - 1))]
        coverage.append(float((pairs["p0_state"] == "P0_AVAILABLE").mean()) if len(pairs) else math.nan)
    anchor["full_stream_p0_available_pair_fraction_in_segment"] = coverage
    anchor["scope_note"] = "FROZEN_R1_RELATION_ORACLE_REPORTED_AS_INDEPENDENT_COMPARATOR; B0_RECOMPUTED_ANCHOR_TABLE_USES_B0_FAMILIES"
    write_table(anchor, POST / "frozen_r1_one_anchor_capacity_comparator")
    return anchor


def combined_ladder_table(
    ladder: pd.DataFrame,
    identity_effect: pd.DataFrame,
    range_full: pd.DataFrame,
    range_combined: pd.DataFrame,
    anchor: pd.DataFrame,
    anchor_range: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    overall = ladder[ladder["run_id"] == "ALL_DEVELOPMENT_RUNS"]
    for row in overall.itertuples(index=False):
        rows.append({"ladder_stage": row.scenario, "N_family_before_median": math.nan, "N_family_after_median": row.N_family_median, "N_family_reduction_median": math.nan, "reference_retention_fraction": math.nan, "burden_basis": "PER_ENTITY_PER_FRAME_OR_UNIT_AGGREGATE", "scope": "PRE_REFERENCE_OR_RUNTIME_LEGAL" if row.scenario != "ORACLE_OPTICAL_IDENTITY" else "ORACLE_DIAGNOSTIC_ONLY"})
    rows.append({
        "ladder_stage": "ORACLE_OPTICAL_IDENTITY_EFFECT_MATCHED_FRAMES",
        "N_family_before_median": float(identity_effect["N_family_current"].median()),
        "N_family_after_median": float(identity_effect["N_family_oracle_id"].median()),
        "N_family_reduction_median": float(identity_effect["N_family_reduction"].median()),
        "reference_retention_fraction": math.nan,
        "burden_basis": "MATCHED_ENTITY_FRAME",
        "scope": "ORACLE_DIAGNOSTIC_ONLY",
    })
    for label, frame in (("FULL_P0_PLUS_COARSE_RANGE", range_full), ("FULL_P0_PLUS_ORACLE_ID_PLUS_COARSE_RANGE", range_combined)):
        for level, group in frame.groupby("range_oracle_level"):
            rows.append({
                "ladder_stage": f"{label}::{level}",
                "N_family_before_median": float(group["N_family_before"].median()),
                "N_family_after_median": float(group["N_family_after"].median()),
                "N_family_reduction_median": float((group["N_family_before"] - group["N_family_after"]).median()),
                "reference_retention_fraction": float(group["reference_range_retained"].mean()),
                "burden_basis": "MATCHED_ENTITY_FRAME",
                "scope": "ORACLE_DIAGNOSTIC_ONLY",
            })
    for label, frame in (("FULL_P0_PLUS_ONE_CORRECT_ANCHOR", anchor), ("FULL_P0_PLUS_ORACLE_ID_PLUS_ONE_ANCHOR_PLUS_PM3M_RANGE", anchor_range)):
        rows.append({
            "ladder_stage": label,
            "N_family_before_median": float(frame["N_family_before"].median()) if len(frame) else math.nan,
            "N_family_after_median": float(frame["N_family_after"].median()) if len(frame) else math.nan,
            "N_family_reduction_median": float(frame["N_family_deleted"].median()) if len(frame) else math.nan,
            "reference_retention_fraction": math.nan,
            "burden_basis": "DECLARED_DIAGNOSTIC_UNIT_FAMILY_DOMAIN",
            "scope": "ORACLE_DIAGNOSTIC_ONLY",
        })
    result = pd.DataFrame(rows)
    write_table(result, POST / "combined_oracle_ladder", parquet=False)
    return result


def selected_frame_registry() -> pd.DataFrame:
    units = pd.read_csv(PRE / "development_diagnostic_unit_registry.csv", encoding="utf-8-sig")
    selected: dict[tuple[str, int], str] = {}
    r02 = [450, 455, 460, 465, 470, 472, 475, 480, 485] + list(range(487, 495))
    for frame in r02:
        selected[("R02ZF", frame)] = "R02_CRITICAL_CHAIN_FIXED"
    for frame in range(450, 476):
        selected[("R03ZF", frame)] = "R03_NATURAL_SINGLETON_FIXED"
    for kind, reason in (("EARLY", "R01_MECHANICAL_EARLY"), ("MULTI_OR_AMBIGUOUS", "R01_MECHANICAL_AMBIGUOUS"), ("BOUNDARY_OR_DORMANCY", "R01_MECHANICAL_BOUNDARY")):
        row = units[(units["run_id"] == "R01ZF") & (units["unit_kind"] == kind)].iloc[0]
        frames = np.linspace(int(row.start_frame), int(row.end_frame), min(6, int(row.end_frame) - int(row.start_frame) + 1), dtype=int)
        for frame in frames:
            selected[("R01ZF", int(frame))] = reason
    rows = [{"run_id": run_id, "frame_index": frame, "selection_role": role} for (run_id, frame), role in sorted(selected.items())]
    result = pd.DataFrame(rows)
    write_table(result, PRE / "review_selected_frame_registry", parquet=False)
    return result


def matched_clutter_controls(selected: pd.DataFrame) -> pd.DataFrame:
    regions = pd.read_parquet(Q95_REGIONS)
    shells = pd.read_parquet(SHELLS)
    shells = shells[(shells["run_id"] == "R03ZF") & (shells["mode"] == "CAUSAL_REPLAY")]
    optical = pd.read_parquet(OPTICAL)
    detected_optical_frames = set(optical[(optical["run_id"] == "R03ZF") & (optical["box_source"] == "DETECTED")]["frame_index"].astype(int))
    registry = frame_metadata()
    no_optical_sar = registry[(registry["run_id"] == "R03ZF") & ~registry["nominal_optical_frame_index"].astype(int).isin(detected_optical_frames)]
    rows: list[dict[str, Any]] = []
    for target_frame in (459, 466, 470):
        shell = shells[shells["frame_index"] == target_frame].sort_values("candidate_q95_region_count").iloc[0]
        intervals = [(float(a), float(b)) for a, b in json.loads(shell["effective_intervals_json"])]
        candidates = []
        for frame_index in no_optical_sar["sar_frame_index"].astype(int):
            if 450 <= frame_index <= 475:
                continue
            frame_regions = regions[(regions["run_id"] == "R03ZF") & (regions["frame_index"] == frame_index)]
            overlap = frame_regions[frame_regions.apply(lambda row: any(float(row.theta_max_deg) >= low and float(row.theta_min_deg) <= high for low, high in intervals), axis=1)]
            if len(overlap) == 1:
                candidates.append(frame_index)
        if not candidates:
            continue
        ordered = sorted(candidates)
        choices = {
            "NEAREST_IN_TIME_SINGLETON_CLUTTER": min(ordered, key=lambda value: (abs(value - target_frame), value)),
            "MEDIAN_TIME_SINGLETON_CLUTTER": ordered[(len(ordered) - 1) // 2],
            "FARTHEST_IN_TIME_SINGLETON_CLUTTER": max(ordered, key=lambda value: (abs(value - target_frame), -value)),
        }
        for rule, control_frame in choices.items():
            rows.append({
                "run_id": "R03ZF",
                "target_natural_singleton_frame": target_frame,
                "control_frame": int(control_frame),
                "selection_rule": rule,
                "candidate_count_in_frozen_target_corridor": 1,
                "target_corridor_intervals_json": json.dumps(intervals),
                "no_optical_definition": "NOMINAL_OPTICAL_FRAME_HAS_NO_DETECTED_OPTICAL_PERSON_ROW",
                "manual_reference_used_for_selection": False,
            })
            selected.loc[len(selected)] = ["R03ZF", int(control_frame), f"R03_CONTROL_{rule}"]
    controls = pd.DataFrame(rows).drop_duplicates(["target_natural_singleton_frame", "selection_rule"])
    write_table(controls, POST / "matched_clutter_control_ledger", parquet=False)
    write_table(selected.drop_duplicates(["run_id", "frame_index"]), PRE / "review_selected_frame_registry", parquet=False)
    return controls


def natural_singleton_ledger() -> pd.DataFrame:
    shells = pd.read_parquet(SHELLS)
    shells = shells[(shells["run_id"] == "R03ZF") & (shells["mode"] == "CAUSAL_REPLAY") & shells["frame_index"].between(450, 475)]
    p0 = pd.read_parquet(PRE / "full_stream_p0_availability.parquet")
    result = shells[["run_id", "frame_index", "track_id", "candidate_q95_region_count", "effective_intervals_json"]].copy()
    result["natural_singleton"] = result["candidate_q95_region_count"] == 1
    result = result.merge(p0[["run_id", "source_frame", "p0_state"]].rename(columns={"source_frame": "frame_index", "p0_state": "outgoing_pair_p0_state"}), on=["run_id", "frame_index"], how="left")
    result["runtime_anchor_claimed"] = False
    result["semantics"] = "NATURAL_SINGLETON_CANDIDATE_NOT_CONFIRMED_IDENTITY_OR_RANGE_ANCHOR"
    write_table(result, POST / "natural_singleton_anchor_ledger", parquet=False)
    return result


def _optical_frame_path(run_id: str, optical_index: int) -> Path | None:
    optical = pd.read_parquet(OPTICAL)
    run = optical[optical["run_id"] == run_id]
    if not len(run):
        return None
    root = Path(str(run.iloc[0]["optical_image_path"])).parent
    matches = sorted(root.glob(f"frame_{optical_index:06d}_t*ms.jpg"))
    return matches[0] if matches else None


def _overlay_sar(run_id: str, frame_index: int, keep_regions: set[str] | None = None, excluded_regions: set[str] | None = None) -> np.ndarray:
    registry = frame_metadata()
    row = registry[(registry["run_id"] == run_id) & (registry["sar_frame_index"] == frame_index)].iloc[0]
    image = cv2.imread(str(row["sar_image_path"]), cv2.IMREAD_COLOR)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    with np.load(Q95_MASKS / f"{run_id}_SARF{frame_index:06d}.npz") as archive:
        labels = archive["Q095"]
    regions = pd.read_parquet(Q95_REGIONS)
    frame_regions = regions[(regions["run_id"] == run_id) & (regions["frame_index"] == frame_index)]
    for rr in frame_regions.itertuples(index=False):
        region_id = str(rr.region_id)
        mask = (labels == int(rr.region_label)).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if keep_regions is not None and region_id in keep_regions:
            color = (40, 235, 80)
        elif excluded_regions is not None and region_id in excluded_regions:
            color = (245, 55, 55)
        else:
            color = (255, 210, 40)
        cv2.drawContours(image, contours, -1, color, 2)
    shells = pd.read_parquet(SHELLS)
    shell_rows = shells[(shells["run_id"] == run_id) & (shells["mode"] == "CAUSAL_REPLAY") & (shells["frame_index"] == frame_index)]
    interval_values = shell_rows["effective_intervals_json"].astype(str).tolist()
    if not interval_values and run_id == "R03ZF" and (POST / "matched_clutter_control_ledger.csv").exists():
        controls = pd.read_csv(POST / "matched_clutter_control_ledger.csv", encoding="utf-8-sig")
        match = controls[controls["control_frame"] == frame_index]
        if len(match):
            interval_values = [str(match.iloc[0]["target_corridor_intervals_json"])]
    cx, cy, radius = float(row["geometry_center_x_px"]), float(row["geometry_center_y_px"]), float(row["geometry_radius_px"])
    for value in interval_values:
        for low, high in json.loads(value):
            for angle in (float(low), float(high)):
                rad = math.radians(angle)
                x = int(round(cx + radius * math.sin(rad)))
                y = int(round(cy - radius * math.cos(rad)))
                cv2.line(image, (int(round(cx)), int(round(cy))), (x, y), (40, 230, 245), 2, cv2.LINE_AA)
    return image


def _optical_image(run_id: str, frame_index: int) -> tuple[np.ndarray | None, int]:
    registry = frame_metadata()
    row = registry[(registry["run_id"] == run_id) & (registry["sar_frame_index"] == frame_index)].iloc[0]
    optical_index = int(row["nominal_optical_frame_index"])
    path = _optical_frame_path(run_id, optical_index)
    if path is None:
        return None, optical_index
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB), optical_index


def _paired_panel(path: Path, title: str, cases: list[tuple[str, int, str, set[str] | None, set[str] | None]], oracle: bool = False) -> None:
    fig, axes = plt.subplots(len(cases), 2, figsize=(13, max(4, 4 * len(cases))), squeeze=False)
    for row_index, (run_id, frame_index, note, keep, excluded) in enumerate(cases):
        optical, optical_index = _optical_image(run_id, frame_index)
        if optical is None:
            axes[row_index, 0].text(0.5, 0.5, f"Optical F{optical_index} unavailable", ha="center", va="center")
        else:
            axes[row_index, 0].imshow(optical)
        axes[row_index, 0].set_title(f"{run_id} nominal optical F{optical_index}\n{note}")
        axes[row_index, 0].axis("off")
        axes[row_index, 1].imshow(_overlay_sar(run_id, frame_index, keep, excluded))
        axes[row_index, 1].set_title(f"{run_id} SAR F{frame_index} | yellow Q95, green survive, red exclude")
        axes[row_index, 1].axis("off")
    prefix = "ORACLE DIAGNOSTIC ONLY — " if oracle else ""
    fig.suptitle(prefix + title, fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def generate_figures() -> None:
    ladder = pd.read_csv(POST / "combined_oracle_ladder.csv", encoding="utf-8-sig")
    p0 = pd.read_parquet(PRE / "full_stream_p0_availability.parquet")
    identity = pd.read_csv(POST / "oracle_optical_identity_effect.csv", encoding="utf-8-sig")
    anchor = pd.read_csv(POST / "full_p0_one_correct_unary_anchor_effect.csv", encoding="utf-8-sig")
    range_rows = pd.read_csv(POST / "full_stream_p0_coarse_range_oracle_sweep.csv", encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(11, 6))
    plot = ladder[(ladder["N_family_after_median"].notna()) & (ladder["burden_basis"] != "DECLARED_DIAGNOSTIC_UNIT_FAMILY_DOMAIN")].copy()
    ax.barh(np.arange(len(plot)), plot["N_family_after_median"], color=["#607d8b" if "RANGE" not in s else "#2e7d32" for s in plot["ladder_stage"]])
    ax.set_yticks(np.arange(len(plot)), [s.replace("FULL_P0_PLUS_", "") for s in plot["ladder_stage"]], fontsize=8)
    ax.invert_yaxis(); ax.set_xlabel("Median N_family after information layer"); ax.set_title("PERSON-B0 matched frame-level oracle/interface ladder")
    fig.tight_layout(); fig.savefig(FIG / "01_b0_oracle_interface_ladder.png", dpi=180); plt.close(fig)
    p0_summary = p0.groupby(["run_id", "p0_state"]).size().unstack(fill_value=0)
    ax = p0_summary.plot(kind="bar", stacked=True, figsize=(9, 5), color={"P0_AVAILABLE": "#2e7d32", "P0_UNRELIABLE_OR_AMBIGUOUS": "#f9a825", "P0_UNAVAILABLE": "#c62828"})
    ax.set_ylabel("Adjacent pair count"); ax.set_title("Full-stream SAR-only P0 availability"); ax.figure.tight_layout(); ax.figure.savefig(FIG / "02_full_stream_p0_availability.png", dpi=180); plt.close(ax.figure)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    identity.groupby("run_id")["N_family_reduction"].mean().plot.bar(ax=axes[0], color="#1565c0", title="Oracle optical identity mean family reduction")
    anchor.groupby("run_id")["N_family_deleted"].mean().plot.bar(ax=axes[1], color="#6a1b9a", title="One-anchor relation mean family deletion")
    for ax in axes: ax.axhline(0, color="black", lw=0.8); ax.set_ylabel("families")
    fig.tight_layout(); fig.savefig(FIG / "03_identity_and_anchor_gain_by_run.png", dpi=180); plt.close(fig)
    sweep = range_rows.assign(reduction=range_rows["N_family_before"] - range_rows["N_family_after"]).groupby("range_oracle_level").agg(after=("N_family_after", "median"), reduction=("reduction", "median"), retention=("reference_range_retained", "mean")).reset_index()
    fig, ax = plt.subplots(figsize=(10, 5)); ax.bar(sweep["range_oracle_level"], sweep["after"], color="#2e7d32"); ax.set_ylabel("Median N_family after range"); ax.tick_params(axis="x", rotation=25); ax.set_title("Coarse range is the dominant oracle discriminator (oracle only)"); fig.tight_layout(); fig.savefig(FIG / "04_coarse_range_oracle_sweep.png", dpi=180); plt.close(fig)

    current = pd.read_parquet(PRE / "current_runtime_frame_burden.parquet")
    full = pd.read_parquet(PRE / "full_stream_p0_frame_burden.parquet")
    merged = current.merge(full, on=["run_id", "frame_index", "entity_id"], suffixes=("_current", "_full"))
    arow = merged.sort_values("N_region_current", ascending=False).iloc[0]
    brow = merged.assign(red=merged["N_family_current"] - merged["N_family_full"]).sort_values("red", ascending=False).iloc[0]
    crow = identity[identity["run_id"] == "R02ZF"].sort_values("N_family_reduction", ascending=False).iloc[0]
    dset = anchor[(anchor["run_id"] == "R02ZF") & anchor["unit_id"].str.contains("RELATION")]
    drow = (dset if len(dset) else anchor[anchor["run_id"] == "R02ZF"]).sort_values("N_family_deleted", ascending=False).iloc[0]
    erow = range_rows.assign(red=range_rows["N_family_before"] - range_rows["N_family_after"]).sort_values("red", ascending=False).iloc[0]
    frow = range_rows[range_rows["range_tolerance_m"] == 0.5].sort_values("N_family_after", ascending=False).iloc[0]
    def range_sets(row: pd.Series) -> tuple[set[str], set[str]]:
        membership = pd.read_parquet(PRE / "full_stream_p0_candidate_family_membership.parquet")
        region = pd.read_parquet(Q95_REGIONS)
        frame = membership[(membership["run_id"] == row.run_id) & (membership["frame_index"] == int(row.frame_index)) & (membership["entity_id"] == row.entity_id)].merge(region[["region_id", "range_min_m", "range_max_m"]], on="region_id")
        ref = load_range_reference_filtered(); _, raw_map = None, None
        raw_mapping, _ = entity_target_map(); target = raw_mapping[(raw_mapping["run_id"] == row.run_id) & (raw_mapping["entity_id"] == row.entity_id)]["target_id"].iloc[0]
        rr = ref[(ref["run_id"] == row.run_id) & (ref["frame_index"] == int(row.frame_index)) & (ref["target_id"] == target)]["reference_range_m"].iloc[0]
        keep = set(frame[(frame["range_max_m"] >= rr - float(row.range_tolerance_m)) & (frame["range_min_m"] <= rr + float(row.range_tolerance_m))]["region_id"].astype(str))
        all_regions = set(frame["region_id"].astype(str)); return keep, all_regions - keep
    ekeep, eexclude = range_sets(erow); fkeep, fexclude = range_sets(frow)
    _paired_panel(FIG / "panel_A_current_runtime_high_ambiguity.png", "Panel A — current runtime high ambiguity", [(arow.run_id, int(arow.frame_index), f"N_region={int(arow.N_region_current)}, N_family={int(arow.N_family_current)}", None, None)])
    _paired_panel(FIG / "panel_B_full_p0_candidate_change.png", "Panel B — full-P0 candidate-family change", [(brow.run_id, int(brow.frame_index), f"N_family {int(brow.N_family_current)} -> {int(brow.N_family_full)}", None, None)])
    _paired_panel(FIG / "panel_C_oracle_optical_identity_effect.png", "Panel C — oracle optical identity effect", [(crow.run_id, int(crow.frame_index), f"N_family {int(crow.N_family_current)} -> {int(crow.N_family_oracle_id)}", None, None)], oracle=True)
    _paired_panel(FIG / "panel_D_one_anchor_relation_propagation.png", "Panel D — one correct anchor relation propagation", [(drow.run_id, int(487 if drow.run_id == 'R02ZF' else 0), f"deleted {int(drow.N_family_deleted)} families in diagnostic unit", None, None)], oracle=True)
    _paired_panel(FIG / "panel_E_coarse_range_pruning.png", "Panel E — coarse-range pruning", [(erow.run_id, int(erow.frame_index), f"±{erow.range_tolerance_m:g}m: {int(erow.N_family_before)} -> {int(erow.N_family_after)} families", ekeep, eexclude)], oracle=True)
    _paired_panel(FIG / "panel_F_range_residual_ambiguity_counterexample.png", "Panel F — strongest residual ambiguity after ±0.5m range", [(frow.run_id, int(frow.frame_index), f"still {int(frow.N_family_after)} families", fkeep, fexclude)], oracle=True)
    controls = pd.read_csv(POST / "matched_clutter_control_ledger.csv", encoding="utf-8-sig")
    gcases = [("R03ZF", 459, "natural singleton", None, None)] + [("R03ZF", int(row.control_frame), row.selection_rule, None, None) for row in controls[controls["target_natural_singleton_frame"] == 459].itertuples(index=False)]
    _paired_panel(FIG / "panel_G_r03_natural_singleton_vs_controls.png", "Panel G — R03 natural singleton versus mechanical no-optical controls", gcases)
    hcases = [("R02ZF", frame, label, None, None) for frame, label in [(450, "early"), (472, "bridge start"), (487, "relation window"), (494, "late")]]
    _paired_panel(FIG / "panel_H_r02_early_to_late_bridge.png", "Panel H — R02 early-to-late temporal bridge", hcases)


def build_report() -> None:
    p0 = pd.read_parquet(PRE / "full_stream_p0_availability.parquet")
    current = pd.read_parquet(PRE / "current_runtime_frame_burden.parquet")
    full = pd.read_parquet(PRE / "full_stream_p0_frame_burden.parquet")
    merged = current.merge(full, on=["run_id", "frame_index", "entity_id"], suffixes=("_current", "_full"))
    identity = pd.read_csv(POST / "oracle_optical_identity_effect.csv", encoding="utf-8-sig")
    range_rows = pd.read_csv(POST / "full_stream_p0_coarse_range_oracle_sweep.csv", encoding="utf-8-sig")
    anchor = pd.read_csv(POST / "full_p0_one_correct_unary_anchor_effect.csv", encoding="utf-8-sig")
    p0_counts = p0.groupby(["run_id", "p0_state"]).size().unstack(fill_value=0)
    change = merged["N_family_current"] - merged["N_family_full"]
    range_summary = range_rows.assign(reduction=range_rows["N_family_before"] - range_rows["N_family_after"]).groupby("range_oracle_level").agg(before=("N_family_before", "median"), after=("N_family_after", "median"), reduction=("reduction", "median"), retention=("reference_range_retained", "mean"))
    lines = [
        "# PERSON-B0 end-to-end capability and bottleneck study",
        "",
        "## Direct scientific conclusion",
        "",
        "**COARSE_RANGE_IS_DOMINANT_MISSING_OBSERVABLE.** Full-stream P0 is now a successful, high-coverage SAR image-domain interface, but it is not the dominant missing discriminator. Oracle optical continuity is a secondary, scene-dependent interface limitation concentrated in R02. One correct unary anchor plus the existing set-valued angular-order relation has median zero effect on other-person family burden. The current Q95 response representation therefore remains highly ambiguous without range, while a very coarse range interval already collapses most families.",
        "",
        "If only one direction can be funded now: prioritize a conservative runtime-capable coarse SAR range observable/interface. Do not spend the next cycle primarily on more P0 states or a new optical tracker; keep the response representation under review because even near-exact range has a small residual non-singleton tail.",
        "",
        "## Key numbers",
        "",
        f"- Full-stream P0: {len(p0)}/{len(p0)} adjacent pairs evaluated; states by run: `{p0_counts.to_dict()}`.",
        f"- Full P0 family effect on matched runtime rows: median reduction `{float(change.median()):.1f}`, mean `{float(change.mean()):.3f}`, improved rows `{int((change>0).sum())}/{len(change)}`, worsened rows `{int((change<0).sum())}/{len(change)}`.",
        f"- Oracle optical identity: median reduction `{float(identity.N_family_reduction.median()):.1f}` overall; R02 median `{float(identity[identity.run_id=='R02ZF'].N_family_reduction.median()):.1f}` and positive fraction `{float((identity[identity.run_id=='R02ZF'].N_family_reduction>0).mean()):.3f}`.",
        f"- One correct anchor: median deleted families `{float(anchor.N_family_deleted.median()):.1f}`, positive fraction `{float((anchor.N_family_deleted>0).mean()):.3f}`, maximum `{int(anchor.N_family_deleted.max())}` over the declared units.",
    ]
    for level, row in range_summary.iterrows():
        lines.append(f"- {level}: median N_family `{row.before:.1f} -> {row.after:.1f}` (reduction `{row.reduction:.1f}`), reference retention `{row.retention:.3f}` on available R01/R02/R03 reference rows.")
    lines += [
        "",
        "## Bottleneck classification",
        "",
        "- `MISSING_PHYSICAL_OBSERVABLE`: dominant; coarse range creates the only order-of-magnitude contraction.",
        "- `RESPONSE_REPRESENTATION_AMBIGUITY`: still present; range is needed to make Q95 families discriminative, and a residual tail remains.",
        "- `OPTICAL_IDENTITY_LIMITATION`: secondary and heterogeneous, strongest in R02.",
        "- `INTERFACE_GAP`: full-stream P0 gap is closed as an interface, but closing it does not close localization ambiguity.",
        "- `MECHANISM_UNDERUTILIZATION`: not supported as the dominant story; current relation propagation remains weak even with an oracle anchor.",
        "- `FUNDAMENTAL_AMBIGUITY`: not fully established because coarse range resolves most tested cases; residual ambiguity remains conditional on this response representation and sparse reference coverage.",
        "",
        "## Timing and non-claims",
        "",
        "`ORACLE_TIMING_UNAVAILABLE`. The 250 ms value is only an observation context. No synchronization-error bound, recovered physical motion, intrinsic RCS, cross-modal identity, final center, or final box is claimed. All range, anchor, identity, and post-reference retention results are development diagnostics only.",
        "",
        "## Figures",
        "",
    ]
    for path in sorted(FIG.glob("*.png")):
        lines.append(f"![{path.stem}](figures/{path.name})")
        lines.append("")
    (OUTPUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    write_json(OUTPUT / "summary.json", {
        "scientific_conclusion": "COARSE_RANGE_IS_DOMINANT_MISSING_OBSERVABLE",
        "secondary_conclusions": ["CURRENT_RESPONSE_REPRESENTATION_REMAINS_RANGE_DEPENDENT_AND_AMBIGUOUS", "OPTICAL_IDENTITY_IS_SECONDARY_R02_WEIGHTED_BOTTLENECK", "RELATIONAL_PROPAGATION_TOO_WEAK_AT_MEDIAN_EVEN_WITH_ORACLE_ANCHOR", "FULL_STREAM_P0_INTERFACE_ESTABLISHED_NOT_DOMINANT"],
        "oracle_timing": "ORACLE_TIMING_UNAVAILABLE",
        "p0_pair_count": int(len(p0)),
        "p0_state_counts": {run: {state: int(value) for state, value in states.items()} for run, states in p0_counts.to_dict("index").items()},
        "r04_evidence_used": False,
    })


def copy_verified(source: Path, destination: Path, records: list[dict[str, Any]], role: str, scope: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    source_hash = sha256_file(source)
    destination_hash = sha256_file(destination)
    if source_hash != destination_hash:
        raise RuntimeError(f"copy hash mismatch: {source} -> {destination}")
    records.append({
        "relative_path": destination.relative_to(PACK).as_posix(),
        "bytes": destination.stat().st_size,
        "sha256": destination_hash,
        "source_original_path": str(source.resolve()),
        "data_role": role,
        "runtime_or_oracle_scope": scope,
    })


def build_review_pack() -> None:
    if PACK.exists():
        shutil.rmtree(PACK)
    PACK.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    selected = pd.read_csv(PRE / "review_selected_frame_registry.csv", encoding="utf-8-sig")
    registry = frame_metadata()
    raw_sar_count = raw_optical_count = q95_count = 0
    optical_seen: set[str] = set()
    for row in selected.itertuples(index=False):
        meta = registry[(registry["run_id"] == row.run_id) & (registry["sar_frame_index"] == int(row.frame_index))].iloc[0]
        sar_source = Path(str(meta["sar_image_path"]))
        copy_verified(sar_source, PACK / "raw_sar" / row.run_id / sar_source.name, records, f"raw SAR {row.selection_role}", "RUNTIME_LEGAL_RAW_INPUT")
        raw_sar_count += 1
        mask_source = Q95_MASKS / f"{row.run_id}_SARF{int(row.frame_index):06d}.npz"
        copy_verified(mask_source, PACK / "q95_masks" / row.run_id / mask_source.name, records, "original Q95 label mask", "RUNTIME_LEGAL_DERIVED_INTERFACE")
        q95_count += 1
        optical_path = _optical_frame_path(row.run_id, int(meta["nominal_optical_frame_index"]))
        if optical_path is not None and str(optical_path).lower() not in optical_seen:
            copy_verified(optical_path, PACK / "raw_optical" / row.run_id / optical_path.name, records, "nominal-mapped raw optical", "RUNTIME_LEGAL_RAW_INPUT_NOMINAL_MAPPING_UNVERIFIED")
            optical_seen.add(str(optical_path).lower())
            raw_optical_count += 1

    selected_regions = pd.read_parquet(Q95_REGIONS).merge(selected[["run_id", "frame_index"]].drop_duplicates(), on=["run_id", "frame_index"], how="inner")
    (PACK / "tables").mkdir(parents=True, exist_ok=True)
    selected_regions.to_csv(PACK / "tables" / "selected_q95_region_table.csv", index=False, encoding="utf-8-sig")
    records.append({"relative_path": "tables/selected_q95_region_table.csv", "bytes": (PACK / "tables" / "selected_q95_region_table.csv").stat().st_size, "sha256": sha256_file(PACK / "tables" / "selected_q95_region_table.csv"), "source_original_path": str(Q95_REGIONS.resolve()), "data_role": "selected Q95 physical region descriptors", "runtime_or_oracle_scope": "RUNTIME_LEGAL_DERIVED_INTERFACE"})
    table_files = [
        PRE / "full_stream_p0_availability.csv",
        PRE / "full_stream_p0_summary.csv",
        PRE / "full_stream_p0_graded_p0_q95_edges.csv",
        PRE / "current_partial_p0_graded_p0_q95_edges.csv",
        PRE / "current_runtime_frame_burden.csv",
        PRE / "full_stream_p0_frame_burden.csv",
        PRE / "development_diagnostic_unit_registry.csv",
        PRE / "threshold_and_authority_audit.csv",
        PRE / "context_window_sensitivity.csv",
        PRE / "review_selected_frame_registry.csv",
        POST / "b0_burden_ladder.csv",
        POST / "per_person_candidate_burden.csv",
        POST / "oracle_optical_identity_effect.csv",
        POST / "full_p0_one_correct_unary_anchor_effect.csv",
        POST / "frozen_r1_one_anchor_capacity_comparator.csv",
        POST / "full_stream_p0_coarse_range_oracle_sweep.csv",
        POST / "full_p0_plus_oracle_id_coarse_range_oracle_sweep.csv",
        POST / "combined_oracle_ladder.csv",
        POST / "natural_singleton_anchor_ledger.csv",
        POST / "matched_clutter_control_ledger.csv",
        POST / "oracle_timing_status.csv",
        R2_PRE / "full_stream_hypothesis_lifecycle_pre_reference.csv",
    ]
    for source in table_files:
        copy_verified(source, PACK / "tables" / source.name, records, "B0 key table" if OUTPUT in source.parents else "frozen dependency table", "MIXED_SEE_FILENAME_AND_README")
    copy_verified(PRE / "full_stream_p0_models.jsonl", PACK / "p0" / "full_stream_p0_models.jsonl", records, "full-stream P0 M1 parameters", "RUNTIME_LEGAL_WHEN_P0_AVAILABLE")

    code_files = [
        SCRIPT,
        TASK / "validate_person_b0.py",
        P0_SCRIPT,
        CMR_SCRIPT,
        WORKSPACE / "tasks" / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830" / "run_terg_r2.py",
        WORKSPACE / "tasks" / "person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829" / "run_terg_r1.py",
        WORKSPACE / "tasks" / "person_physics_guided_image_domain_study_20260824" / "run_p1e_runtime_track_response_region_minimal.py",
        WORKSPACE / "tasks" / "person_physics_guided_image_domain_study_20260824" / "run_p1e_optical_shell_information_gain.py",
    ]
    for source in code_files:
        copy_verified(source, PACK / "code" / source.name, records, "directly relevant implementation", "CODE_PROVENANCE")
    for source in sorted(FIG.glob("*.png")):
        copy_verified(source, PACK / "figures" / source.name, records, "B0 figure", "VISUAL_DIAGNOSTIC")
    r2_names = [
        "01_full_stream_observability_and_anchor_overview.png",
        "02_lifecycle_R02ZF_causal_replay.png",
        "02_lifecycle_R03ZF_causal_replay.png",
        "03_full_stream_q95_and_shell_burden.png",
        "04_negative_time_structural_control.png",
        "05_r1_semantic_corrections.png",
        "06_r02_anchor_relation_propagation_chain_blocked.png",
    ]
    for name in r2_names:
        source = R2_FIG / name
        if source.exists():
            copy_verified(source, PACK / "figures" / "r2_frozen" / source.name, records, "frozen R2 key figure", "FROZEN_DEPENDENCY_VISUAL")

    sha = __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    readme = f"""# PERSON_B0_DEEP_REVIEW_PACK_20260830

Commit basis at pack creation: `{sha}` (B0 files may be committed immediately after pack validation; see final task report for committed SHA).

## Scope and source contract

- Development runs only: R01ZF, R02ZF, R03ZF.
- No R04 image or confirmation evidence enters B0 analysis or this pack.
- Raw SAR: `{SAR_ROOT}`; copied byte-for-byte.
- Raw optical: paths in `{OPTICAL}`; nominal mapping uses SAR timestamp -> round(timestamp * 18/1000), zero offset unverified.
- Q95 masks: `{Q95_MASKS}`; NPZ keys are `Q095`, `levels`, and `numeric_score_thresholds`.
- `Q095` integer label equals `region_label` in `tables/selected_q95_region_table.csv`; `region_id` is the stable physical-region identifier.
- Full P0: SAR-only common apparent translation. `translation_xy` is image-domain M1 `(dx,dy)`; it is not platform motion. Q95 masks dilated by {Q95_EXCLUSION_DILATION_PX}px exclude response foreground during fitting.

## Mechanical selection

- R02: fixed critical chain F450,455,460,465,470,472,475,480,485,487-494.
- R03: complete F450-F475; controls for F459/F466/F470 are nearest-time, median-time, and farthest-time singleton clutter among nominal no-optical frames, never reference-picked.
- R01: six evenly spaced frames from each mechanically derived early, maximum rolling burden, and boundary window.
- Every selected SAR frame has its original Q95 NPZ; every available nominal optical frame is deduplicated and copied without re-encoding.

## Ladder inputs

- CURRENT_RUNTIME: raw fragment + causal nominal context + corridor + Q95 + frozen partial P0 under B0 graded family semantics.
- FULL_STREAM_P0: same inputs, replacing partial P0 with B0 full-stream SAR-only P0.
- ORACLE_OPTICAL_IDENTITY: replaces raw-fragment entity grouping with the existing offline continuity proxy. Oracle only.
- ORACLE_TIMING: unavailable; no sync truth exists.
- ONE_CORRECT_UNARY_ANCHOR: offline unique reference-supported family, then set-valued relative angular-order compatibility. Oracle only.
- COARSE/ORACLE RANGE: interval intersection with manual native-SAR reference range. Oracle only.

## Runtime/legal versus oracle fields

- Runtime-legal: raw optical fragments, nominal timestamps, angular corridors, raw SAR, Q95 regions, graded SAR-only P0 where available.
- Oracle/post-reference only: `optical_person_id`, `target_id_oracle`, reference range/theta, anchor selection, retention metrics, and all files under names containing `oracle` or `post_reference`.
- No final center/box or cross-modal identity is produced.

## Five cases to review first

1. R02 F450: early low-ambiguity start before the dense relation window.
2. R02 F487-F494: dense relation window; compare full-P0 availability and weak anchor propagation.
3. R03 F459: natural singleton.
4. R03 F466/F470: repeated singleton candidates.
5. `matched_clutter_control_ledger.csv`: mechanical no-optical singleton clutter counterexamples.

## Main result to challenge

Full P0 is successfully available for most adjacent pairs but does not reduce median family burden. Oracle optical identity is secondary and R02-weighted. Coarse range ±3m changes the median family burden from 12 to 2, while ±2m or tighter changes it to 1 on the available reference subset. The pack is intended to let an external reviewer inspect whether this range result is a legitimate missing-observable diagnosis or an artifact of the Q95 response representation.
"""
    (PACK / "README_FOR_GPT_DEEP_REVIEW.md").write_text(readme, encoding="utf-8")
    records.append({"relative_path": "README_FOR_GPT_DEEP_REVIEW.md", "bytes": (PACK / "README_FOR_GPT_DEEP_REVIEW.md").stat().st_size, "sha256": sha256_file(PACK / "README_FOR_GPT_DEEP_REVIEW.md"), "source_original_path": "GENERATED", "data_role": "review instructions", "runtime_or_oracle_scope": "DOCUMENTATION"})
    manifest = pd.DataFrame(records).sort_values("relative_path")
    manifest.to_csv(PACK / "PACK_MANIFEST.csv", index=False, encoding="utf-8-sig")
    pack_summary = {
        "raw_sar_image_count": raw_sar_count,
        "raw_optical_image_count": raw_optical_count,
        "q95_mask_count": q95_count,
        "csv_count": len(list(PACK.rglob("*.csv"))),
        "figure_count": len(list(PACK.rglob("*.png"))),
        "manifest_entry_count": len(manifest),
        "manifest_copy_hashes_pass": True,
    }
    write_json(PACK / "PACK_SUMMARY.json", pack_summary)
    manifest.loc[len(manifest)] = ["PACK_SUMMARY.json", (PACK / "PACK_SUMMARY.json").stat().st_size, sha256_file(PACK / "PACK_SUMMARY.json"), "GENERATED", "pack counts", "DOCUMENTATION"]
    manifest.to_csv(PACK / "PACK_MANIFEST.csv", index=False, encoding="utf-8-sig")
    if PACK_ZIP.exists():
        PACK_ZIP.unlink()
    with zipfile.ZipFile(PACK_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(PACK.rglob("*")):
            if path.is_file():
                archive.write(path, Path(PACK.name) / path.relative_to(PACK))
    print(json.dumps({**pack_summary, "zip": str(PACK_ZIP), "zip_bytes": PACK_ZIP.stat().st_size}, ensure_ascii=False), flush=True)


def generate_artifacts() -> None:
    selected = selected_frame_registry()
    matched_clutter_controls(selected)
    natural_singleton_ledger()
    generate_figures()
    build_report()


def threshold_audit() -> pd.DataFrame:
    rows = [
        ("Q95 percentile", "q95", "A_REPRESENTATION_DEFINITION", "Defines response-region representation; not calibrated PERSON confidence.", "eligible for representation claims only"),
        ("Optical angular guard", "+/-6 deg", "C_ENGINEERING_POLICY", "Legacy engineering corridor guard without independent physical calibration.", "not eligible for strongest causal claim"),
        ("R2 context lookback", "250 ms", "C_ENGINEERING_POLICY", "Observation context, not synchronization uncertainty.", "sensitivity only"),
        ("R2 fixed future context", "100 ms", "C_ENGINEERING_POLICY", "Offline/fixed-lag observation context.", "sensitivity only"),
        ("R2 P0 continuation", ">=1 soft pixel", "D_ARBITRARY_OR_LEGACY_THRESHOLD", "Positive overlap is retained only as UPPER_POSSIBLE in B0.", "not topology authority"),
        ("B0 optional edge", "source-dominant OR destination-dominant", "A_REPRESENTATION_DEFINITION", "Pareto-compatible graded edge; ties retained.", "versioned B0 family definition"),
        ("B0 lower edge", "source-dominant AND destination-dominant", "A_REPRESENTATION_DEFINITION", "Mutual-dominance lower relation.", "conservative core"),
        ("Optical observation count", ">=2", "D_ARBITRARY_OR_LEGACY_THRESHOLD", "Bookkeeping activation rule, not identity evidence.", "not scientific discriminator"),
        ("Q95 foreground exclusion dilation", f"{Q95_EXCLUSION_DILATION_PX}px", "C_ENGINEERING_POLICY", "SAR-only conservative foreground exclusion for P0 fitting.", "availability sensitivity; no PERSON reference"),
        ("P0 fit anchors", "24", "A_REPRESENTATION_DEFINITION", "Frozen observability/comparability protocol.", "interface availability only"),
        ("P0 holdout anchors", "8", "A_REPRESENTATION_DEFINITION", "Frozen observability/comparability protocol.", "interface availability only"),
        ("P0 spatial cells", "10", "A_REPRESENTATION_DEFINITION", "Frozen spatial coverage requirement.", "interface availability only"),
        ("Range +/-0.5/1/2/3m", "fixed oracle sweep", "A_REPRESENTATION_DEFINITION", "Predeclared development diagnostic; never runtime input.", "oracle upper-bound claims only"),
    ]
    frame = pd.DataFrame(rows, columns=["parameter", "value", "authority_class", "interpretation", "claim_use"])
    frame["outcome_tuned_in_b0"] = False
    write_table(frame, PRE / "threshold_and_authority_audit", parquet=False)
    return frame


def summarize_ladder(unit_tables: list[pd.DataFrame]) -> pd.DataFrame:
    data = pd.concat(unit_tables, ignore_index=True)
    summary = data.groupby(["scenario", "run_id"]).agg(
        entity_unit_count=("entity_id", "size"),
        N_region_median=("N_region_median", "median"),
        N_family_median=("N_family_median", "median"),
        A_candidate_px_median=("A_candidate_px_median", "median"),
        A_candidate_m2_median=("A_candidate_m2_median", "median"),
        A_candidate_over_A_search_support_median=("A_candidate_over_A_search_support_median", "median"),
    ).reset_index()
    overall = data.groupby("scenario").agg(
        entity_unit_count=("entity_id", "size"),
        N_region_median=("N_region_median", "median"),
        N_family_median=("N_family_median", "median"),
        A_candidate_px_median=("A_candidate_px_median", "median"),
        A_candidate_m2_median=("A_candidate_m2_median", "median"),
        A_candidate_over_A_search_support_median=("A_candidate_over_A_search_support_median", "median"),
    ).reset_index()
    overall["run_id"] = "ALL_DEVELOPMENT_RUNS"
    result = pd.concat([summary, overall], ignore_index=True)
    write_table(result, POST / "b0_burden_ladder", parquet=False)
    write_table(data, POST / "per_person_candidate_burden")
    return result


def context_sensitivity(full_edges: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mode in ("CAUSAL_REPLAY", "FIXED_LAG_100MS", "FULL_CONTEXT_OFFLINE"):
        candidates = candidate_rows(mode, "RAW_FRAGMENT")
        memberships = family_membership(candidates, full_edges, f"FULL_P0_{mode}")
        burden = burden_frame(candidates, memberships, f"FULL_P0_{mode}", mode, "RAW_FRAGMENT")
        for run_id, group in burden.groupby("run_id"):
            rows.append({
                "run_id": run_id,
                "context_mode": mode,
                "context_lookback_ms": CONTEXT_LOOKBACK_MS,
                "context_lookahead_ms": {"CAUSAL_REPLAY": 0, "FIXED_LAG_100MS": 100, "FULL_CONTEXT_OFFLINE": 250}[mode],
                "N_region_median": float(group["N_region"].median()),
                "N_family_median": float(group["N_family"].median()),
                "A_candidate_over_A_search_support_median": float(group["A_candidate_over_A_search_support"].median()),
                "sync_uncertainty_bound_claimed": False,
            })
    frame = pd.DataFrame(rows)
    write_table(frame, PRE / "context_window_sensitivity", parquet=False)
    timing = pd.DataFrame([{
        "oracle_stage": "ORACLE_TIMING",
        "status": "ORACLE_TIMING_UNAVAILABLE",
        "reason": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED; only grid quantization is known and sync offset truth is unavailable.",
        "invented_timing_truth": False,
    }])
    write_table(timing, POST / "oracle_timing_status", parquet=False)
    return frame


def run_ladder() -> dict[str, pd.DataFrame]:
    threshold_audit()
    partial_edges = build_graded_edges(load_partial_models(), "CURRENT_PARTIAL_P0")
    full_edges = build_graded_edges(load_full_models(), "FULL_STREAM_P0")
    current_candidates = candidate_rows("CAUSAL_REPLAY", "RAW_FRAGMENT")
    current_membership = family_membership(current_candidates, partial_edges, "CURRENT_RUNTIME")
    full_membership = family_membership(current_candidates, full_edges, "FULL_STREAM_P0")
    oracle_candidates = candidate_rows("CAUSAL_REPLAY", "ORACLE_OPTICAL_IDENTITY")
    oracle_membership = family_membership(oracle_candidates, full_edges, "ORACLE_OPTICAL_IDENTITY")
    current_burden = burden_frame(current_candidates, current_membership, "CURRENT_RUNTIME", "CAUSAL_REPLAY", "RAW_FRAGMENT")
    full_burden = burden_frame(current_candidates, full_membership, "FULL_STREAM_P0", "CAUSAL_REPLAY", "RAW_FRAGMENT")
    oracle_burden = burden_frame(oracle_candidates, oracle_membership, "ORACLE_OPTICAL_IDENTITY", "CAUSAL_REPLAY", "ORACLE_OPTICAL_IDENTITY")
    units = build_unit_registry(current_burden)
    current_units = aggregate_units(current_burden, units)
    full_units = aggregate_units(full_burden, units)
    oracle_units = aggregate_units(oracle_burden, units)
    ladder = summarize_ladder([current_units, full_units, oracle_units])
    write_table(current_burden, PRE / "current_runtime_frame_burden")
    write_table(full_burden, PRE / "full_stream_p0_frame_burden")
    write_table(oracle_burden, POST / "oracle_optical_identity_frame_burden")
    current_roll = current_membership.merge(optical_identity_map(), left_on=["run_id", "entity_id"], right_on=["run_id", "raw_track_fragment_id"], how="left")
    current_roll = current_roll.groupby(["run_id", "frame_index", "optical_person_id"]).agg(N_family_current=("family_id", "nunique"), N_region_current=("region_id", "nunique")).reset_index()
    oracle_roll = oracle_membership.groupby(["run_id", "frame_index", "entity_id"]).agg(N_family_oracle_id=("family_id", "nunique"), N_region_oracle_id=("region_id", "nunique")).reset_index().rename(columns={"entity_id": "optical_person_id"})
    identity_effect = current_roll.merge(oracle_roll, on=["run_id", "frame_index", "optical_person_id"], how="outer")
    identity_effect["N_family_reduction"] = identity_effect["N_family_current"] - identity_effect["N_family_oracle_id"]
    identity_effect["oracle_diagnostic_only"] = True
    write_table(identity_effect, POST / "oracle_optical_identity_effect")
    range_full = range_sweep(full_membership, "RAW_FRAGMENT", "FULL_STREAM_P0")
    range_combined = range_sweep(oracle_membership, "ORACLE_OPTICAL_IDENTITY", "FULL_P0_PLUS_ORACLE_ID")
    anchor = one_anchor_effect(full_membership, "RAW_FRAGMENT", units, "FULL_P0")
    anchor_range = one_anchor_effect(oracle_membership, "ORACLE_OPTICAL_IDENTITY", units, "FULL_P0_PLUS_ORACLE_ID_PLUS_PM3M_RANGE", range_tolerance=3.0)
    legacy_anchor_audit()
    combined = combined_ladder_table(ladder, identity_effect, range_full, range_combined, anchor, anchor_range)
    context = context_sensitivity(full_edges)
    return {
        "partial_edges": partial_edges,
        "full_edges": full_edges,
        "current_membership": current_membership,
        "full_membership": full_membership,
        "oracle_membership": oracle_membership,
        "current_burden": current_burden,
        "full_burden": full_burden,
        "oracle_burden": oracle_burden,
        "units": units,
        "ladder": ladder,
        "identity_effect": identity_effect,
        "range_full": range_full,
        "range_combined": range_combined,
        "anchor": anchor,
        "anchor_range": anchor_range,
        "combined": combined,
        "context": context,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    bench = sub.add_parser("benchmark-p0")
    bench.add_argument("--pairs", type=int, default=18)
    bench.add_argument("--workers", type=int, default=3)
    full = sub.add_parser("full-p0")
    full.add_argument("--workers", type=int, default=3)
    sub.add_parser("ladder")
    sub.add_parser("artifacts")
    sub.add_parser("pack")
    args = parser.parse_args()
    assert_scope()
    PRE.mkdir(parents=True, exist_ok=True)
    POST.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    if args.command == "benchmark-p0":
        run_p0(args.workers, benchmark_pairs=args.pairs)
    elif args.command == "full-p0":
        run_p0(args.workers, benchmark_pairs=None)
    elif args.command == "ladder":
        run_ladder()
    elif args.command == "artifacts":
        generate_artifacts()
    elif args.command == "pack":
        build_review_pack()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
