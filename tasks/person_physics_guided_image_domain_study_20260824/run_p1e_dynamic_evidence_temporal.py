#!/usr/bin/env python3
"""Minimal GT-blind dynamic-evidence temporal experiment for PERSON P1E.

The runtime graph uses only existing SAR-only C2 candidates, C2/C3 response
maps, fan geometry, frozen P0 lag-1 M1 transport, and background-anchor P0
uncertainty. Manual PERSON references and fixed offsets are loaded only after
all nodes, edges, temporal evidence, and threads have been generated and
written to disk.

No single-frame eligibility gate is used. No candidate Top-K truncation is
used. P0, B0R, C0-C3, candidate generation, and prior P1E outputs are read-only.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = (
    WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
)
P1E_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface"
CANDIDATE_ROOT = (
    P1E_ROOT
    / "candidate_recall_semantic_split_v1"
    / "single_frame_candidate_recall"
)
B0R_ROOT = P1E_ROOT / "b0r_minimal"
OUTPUT_ROOT = P1E_ROOT / "dynamic_evidence_temporal_v1"
OUTPUT_DIR = OUTPUT_ROOT / "lag1_r02"
PROTOCOL_PATH = OUTPUT_ROOT / "00_DYNAMIC_EVIDENCE_MINIMAL_TEMPORAL_PROTOCOL_FROZEN_BEFORE_RUN.md"

P0_SCRIPT = TASK_DIR / "run_p0_common_apparent_motion.py"
P1E_SCRIPT = TASK_DIR / "run_p1e_single_frame_position_specificity.py"
CANDIDATE_AUDIT_SCRIPT = TASK_DIR / "run_p1e_candidate_recall_audit.py"
B0R_SCRIPT = TASK_DIR / "run_b0r_minimal_applicability.py"

CANDIDATES_CSV = CANDIDATE_ROOT / "gt_blind_candidates_all_processed_frames.csv"
REFERENCE_INTERPRETATION_CSV = (
    CANDIDATE_ROOT / "manual_reference_candidate_interpretation_v2.csv"
)
FIXED_OFFSETS_CSV = CANDIDATE_ROOT / "fixed_offset_candidate_coverage.csv"
B0R_ANCHORS_CSV = B0R_ROOT / "b0r_background_anchor_metrics_R02_R03.csv"
B0R_MODELS_JSONL = B0R_ROOT / "b0r_model_parameters_R02_R03.jsonl"
B0R_PAIR_METRICS_CSV = B0R_ROOT / "b0r_pair_metrics_R02_R03.csv"
B0R_COMPARABILITY_CSV = B0R_ROOT / "b0r_pair_comparability_R02_R03.csv"

PRIMARY = "C2_COMPACT_JET_GRADIENT_CONSENSUS"
DIAGNOSTIC = "C3_ISOTROPIC_BLOB_RIDGE_SUPPRESSED"
RUN_ID = "R02ZF"

EXPECTED_HASHES = {
    P0_SCRIPT: "0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8",
    P1E_SCRIPT: "98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1",
    B0R_SCRIPT: "3C0DFB20B58D445D224DAD7426AEB0E6DA5E065DB07059B462F1FE528CFC8ABF",
    CANDIDATE_AUDIT_SCRIPT: "84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8",
    CANDIDATES_CSV: "D2F1673A247FDB3AB1DD884F989ADC0ABE4E33A86AEFE45B5DFB4BE286FD6EC0",
    REFERENCE_INTERPRETATION_CSV: "796F20EB3080C5B45CDEBBCC71584CC95C65691F056D46C4A31704A3D86E8EC7",
    B0R_ANCHORS_CSV: "CFEFB6D4239CDB290F0689A5E79437986FCD744FCE7F023B8F2CCBCAA8367385",
    B0R_MODELS_JSONL: "265ADC67D62C466F2D9523FDD06F0503BC9B4AE1343D1A63CCCC3D5FE8FF5E2D",
    B0R_PAIR_METRICS_CSV: "862BA1FEEE5A4A540DA03230F8A15192DE117BA002AB6FE67C2E8C2EFF0D042C",
}

CONDITIONS = (
    "CORRECT_P0",
    "ZERO_TRANSPORT",
    "REVERSE_P0",
    "TANGENTIAL_PLUS_0_75M",
    "SHUFFLED_SOURCE_SHIFT7",
)
THREAD_CONDITIONS = CONDITIONS[:-1]

LOCAL_COMPETITOR_RADIUS_M = 1.25
DENSITY_RADIUS_1_M = 1.0
DENSITY_RADIUS_2_M = 2.0
STRUCTURE_RADIUS_M = 0.90
LOCAL_ANCHOR_RADIUS_PX = 144.0
LOCAL_ANCHOR_MIN_COUNT = 8
UNCERTAINTY_FLOOR_PX = 0.5
MODEL_SUPPORT_RADIUS_M = 0.30
PERTURBATION_TANGENTIAL_M = 0.75
SHUFFLE_PAIR_SHIFT = 7
EDGE_EXPORT_MAX_SIGMA = 3.0
THREAD_MUTUAL_MAX_SIGMA = 2.0
REFERENCE_RADII_M = (0.30, 0.50, 0.80)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
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


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    return value


def node_id(frame_uid: str, rank: int) -> str:
    return f"{frame_uid}__C2R{int(rank):04d}"


def rank_descending(values: np.ndarray, tie_breaker: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    safe = np.where(np.isfinite(values), values, -np.inf)
    order = np.lexsort((tie_breaker, -safe))
    ranks = np.empty(len(values), dtype=np.int32)
    ranks[order] = np.arange(1, len(values) + 1, dtype=np.int32)
    if len(values) <= 1:
        percentile = np.ones(len(values), dtype=np.float64)
    else:
        percentile = 1.0 - (ranks.astype(np.float64) - 1.0) / float(len(values) - 1)
    percentile[~np.isfinite(values)] = np.nan
    ranks[~np.isfinite(values)] = 0
    return ranks, percentile


def sample_nearest(field: np.ndarray, x: float, y: float) -> float:
    xi = int(np.clip(round(float(x)), 0, field.shape[1] - 1))
    yi = int(np.clip(round(float(y)), 0, field.shape[0] - 1))
    value = float(field[yi, xi])
    return value if np.isfinite(value) else math.nan


def local_weighted_structure(
    field: np.ndarray,
    mask: np.ndarray,
    x: float,
    y: float,
    radius_px: int,
    px_per_m: float,
) -> dict[str, float]:
    x0 = max(0, int(math.floor(x - radius_px)))
    x1 = min(field.shape[1], int(math.ceil(x + radius_px + 1)))
    y0 = max(0, int(math.floor(y - radius_px)))
    y1 = min(field.shape[0], int(math.ceil(y + radius_px + 1)))
    yy, xx = np.mgrid[y0:y1, x0:x1]
    radial_select = (xx - x) ** 2 + (yy - y) ** 2 <= radius_px**2
    select = radial_select & mask[y0:y1, x0:x1] & np.isfinite(field[y0:y1, x0:x1])
    if not np.any(select):
        return {
            "structure_anisotropy": math.nan,
            "structure_spread_m": math.nan,
            "structure_orientation_deg": math.nan,
            "structure_effective_pixel_count": 0.0,
        }
    values = np.clip(field[y0:y1, x0:x1][select].astype(np.float64), 0.0, None)
    if float(values.sum()) <= 1e-12:
        return {
            "structure_anisotropy": math.nan,
            "structure_spread_m": math.nan,
            "structure_orientation_deg": math.nan,
            "structure_effective_pixel_count": 0.0,
        }
    coordinates = np.column_stack((xx[select] - x, yy[select] - y)).astype(np.float64)
    weights = values / float(values.sum())
    mean = np.sum(coordinates * weights[:, None], axis=0)
    centered = coordinates - mean[None, :]
    covariance = (centered * weights[:, None]).T @ centered
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    small = max(float(eigenvalues[0]), 0.0)
    large = max(float(eigenvalues[1]), 0.0)
    anisotropy = (large - small) / max(large + small, 1e-9)
    principal = eigenvectors[:, 1]
    orientation = math.degrees(math.atan2(float(principal[1]), float(principal[0])))
    effective_count = 1.0 / max(float(np.sum(weights * weights)), 1e-12)
    return {
        "structure_anisotropy": float(anisotropy),
        "structure_spread_m": float(math.sqrt(large + small) / px_per_m),
        "structure_orientation_deg": float(orientation),
        "structure_effective_pixel_count": float(effective_count),
    }


def build_static_nodes(
    audit: Any,
    p0: Any,
    p1e: Any,
    frame_map: dict[str, dict[str, Any]],
    candidate_table: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    frame_context: dict[str, dict[str, Any]] = {}
    r02_frames = sorted(
        candidate_table[candidate_table["run_id"] == RUN_ID]["frame_uid"].unique(),
        key=lambda uid: int(frame_map[uid]["sar_frame_index"]),
    )
    for frame_number, frame_uid in enumerate(r02_frames, start=1):
        frame = frame_map[frame_uid]
        image_path = p0.file_url_to_path(frame["sar_image_url"])
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(image_path)
        mask, radial, theta, px_per_m = audit.single_frame_observation_mask(frame, image)
        maps, _ = audit.compute_existing_candidate_maps_for_mask(
            p1e, frame, image, mask, radial, theta, px_per_m
        )
        support_radius_px = max(
            1, int(round(p1e.PHYSICAL_SUPPORT_RADIUS_M * px_per_m))
        )
        evaluation_maps = p1e.build_evaluation_maps(
            maps, mask, support_radius_px, "fixed_support_mean_v2"
        )
        c2_map = evaluation_maps[PRIMARY]
        c3_map = evaluation_maps[DIAGNOSTIC]
        structure_radius_px = max(1, int(round(STRUCTURE_RADIUS_M * px_per_m)))

        candidates = candidate_table[
            (candidate_table["frame_uid"] == frame_uid)
            & (candidate_table["candidate"] == PRIMARY)
        ].sort_values("rank")
        xy = candidates[["x_px", "y_px"]].to_numpy(float)
        scores = candidates["score"].to_numpy(float)
        pool_count = len(candidates)
        distances_m = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=2) / px_per_m
        np.fill_diagonal(distances_m, np.inf)
        competitor_mask = distances_m <= LOCAL_COMPETITOR_RADIUS_M
        density_1 = np.sum(distances_m <= DENSITY_RADIUS_1_M, axis=1)
        density_2 = np.sum(distances_m <= DENSITY_RADIUS_2_M, axis=1)
        nearest_neighbor = np.min(distances_m, axis=1)
        competitor_max = np.full(pool_count, np.nan, dtype=np.float64)
        for index in range(pool_count):
            local_scores = scores[competitor_mask[index]]
            if local_scores.size:
                competitor_max[index] = float(np.max(local_scores))

        for local_index, candidate in enumerate(candidates.to_dict("records")):
            rank = int(candidate["rank"])
            percentile = (
                1.0 - (rank - 1) / float(pool_count - 1) if pool_count > 1 else 1.0
            )
            c3_score = sample_nearest(c3_map, candidate["x_px"], candidate["y_px"])
            structure = local_weighted_structure(
                c2_map,
                mask,
                float(candidate["x_px"]),
                float(candidate["y_px"]),
                structure_radius_px,
                px_per_m,
            )
            rows.append(
                {
                    "run_id": RUN_ID,
                    "frame_uid": frame_uid,
                    "frame_index": int(frame["sar_frame_index"]),
                    "node_id": node_id(frame_uid, rank),
                    "candidate_rank": rank,
                    "candidate_pool_count": pool_count,
                    "rank_fraction": rank / float(pool_count),
                    "candidate_pool_percentile": percentile,
                    "x_px": float(candidate["x_px"]),
                    "y_px": float(candidate["y_px"]),
                    "range_m": float(candidate["range_m"]),
                    "theta_deg": float(candidate["theta_deg"]),
                    "C2_score": float(candidate["score"]),
                    "C3_score_at_C2": c3_score,
                    "C3_to_C2_ratio": c3_score / max(float(candidate["score"]), 1e-9),
                    "local_competitor_max_C2_1_25m": competitor_max[local_index],
                    "C2_minus_local_competitor_max_1_25m": (
                        float(candidate["score"]) - competitor_max[local_index]
                        if np.isfinite(competitor_max[local_index])
                        else math.nan
                    ),
                    "other_candidate_count_1_0m": int(density_1[local_index]),
                    "other_candidate_count_2_0m": int(density_2[local_index]),
                    "nearest_other_candidate_distance_m": float(nearest_neighbor[local_index]),
                    "support_fraction": float(candidate["support_fraction"]),
                    "support_status": str(candidate["support_status"]),
                    "px_per_m": float(px_per_m),
                    "generated_without_annotation": bool(
                        candidate["generated_without_annotation"]
                    ),
                    **structure,
                }
            )
        frame_context[frame_uid] = {
            "frame": frame,
            "mask": mask,
            "px_per_m": float(px_per_m),
            "image_path": str(image_path),
        }
        print(
            f"static evidence {frame_number}/{len(r02_frames)} {frame_uid} nodes={pool_count}",
            flush=True,
        )
    return pd.DataFrame(rows), frame_context


def load_pair_records(
    frame_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    model_records: dict[tuple[str, str], dict[str, Any]] = {}
    for line in B0R_MODELS_JSONL.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if (
            record["run_id"] == RUN_ID
            and int(record["lag"]) == 1
            and record["model"] == "M1"
        ):
            model_records[(record["from_frame_uid"], record["to_frame_uid"])] = record

    metrics = pd.read_csv(B0R_PAIR_METRICS_CSV)
    selected = metrics[
        (metrics["run_id"] == RUN_ID)
        & (metrics["lag"] == 1)
        & (metrics["model"] == "M1")
        & metrics["is_selected_frozen_model"].astype(bool)
    ].copy()
    comparability = pd.read_csv(B0R_COMPARABILITY_CSV)
    comparable = comparability[
        (comparability["run_id"] == RUN_ID) & (comparability["lag"] == 1)
    ].set_index(["from_frame_uid", "to_frame_uid"])

    pairs: list[dict[str, Any]] = []
    for row in selected.sort_values("from_frame").to_dict("records"):
        key = (row["from_frame_uid"], row["to_frame_uid"])
        model_record = model_records[key]
        comp = comparable.loc[key]
        pairs.append(
            {
                "pair_index": len(pairs),
                "run_id": RUN_ID,
                "from_frame": int(row["from_frame"]),
                "to_frame": int(row["to_frame"]),
                "from_frame_uid": row["from_frame_uid"],
                "to_frame_uid": row["to_frame_uid"],
                "model_state": model_record["model_state"],
                "translation_xy": model_record["model_state"]["parameters"][
                    "translation_xy"
                ],
                "global_holdout_median_px": float(row["holdout_residual_median_px"]),
                "global_holdout_p90_px": float(row["holdout_residual_p90_px"]),
                "display_js_divergence": float(row["display_js_divergence"]),
                "display_stratum": str(row["display_stratum"]),
                "pair_comparable": bool(comp["comparable"]),
                "comparability_reason": str(comp["comparability_reason"]),
                "from_geometry": frame_map[row["from_frame_uid"]]["geometry"],
                "to_geometry": frame_map[row["to_frame_uid"]]["geometry"],
            }
        )
    if len(pairs) != 22:
        raise RuntimeError(f"expected 22 R02 lag1 pairs, got {len(pairs)}")
    return pairs


def point_polar_arrays(points: np.ndarray, geometry: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    center = np.array(
        [float(geometry["center_x_px"]), float(geometry["center_y_px"])],
        dtype=np.float64,
    )
    delta = points - center[None, :]
    radial = np.linalg.norm(delta, axis=1)
    theta = np.degrees(np.arctan2(delta[:, 0], -delta[:, 1]))
    return radial, theta


def local_uncertainty_for_nodes(
    source_nodes: pd.DataFrame,
    holdout_anchors: pd.DataFrame,
    pair: dict[str, Any],
) -> pd.DataFrame:
    anchor_xy = holdout_anchors[["x_px", "y_px"]].to_numpy(float)
    residuals = holdout_anchors["M1_residual_px"].to_numpy(float)
    anchor_radial, anchor_theta = point_polar_arrays(anchor_xy, pair["from_geometry"])
    node_xy = source_nodes[["x_px", "y_px"]].to_numpy(float)
    node_radial, node_theta = point_polar_arrays(node_xy, pair["from_geometry"])
    rows: list[dict[str, Any]] = []
    for index, node in enumerate(source_nodes.to_dict("records")):
        distances = np.linalg.norm(anchor_xy - node_xy[index][None, :], axis=1)
        selected = np.flatnonzero(distances <= LOCAL_ANCHOR_RADIUS_PX)
        mode = "RADIUS_144PX"
        if len(selected) < LOCAL_ANCHOR_MIN_COUNT:
            selected = np.argsort(distances)[: min(LOCAL_ANCHOR_MIN_COUNT, len(distances))]
            mode = "NEAREST8_FALLBACK"
        local_residuals = residuals[selected]
        local_p50 = float(np.quantile(local_residuals, 0.50))
        local_p90 = float(np.quantile(local_residuals, 0.90))
        epsilon = max(
            local_p90,
            float(pair["global_holdout_p90_px"]),
            UNCERTAINTY_FLOOR_PX,
        )
        px_per_m = float(node["px_per_m"])
        sigma = math.sqrt(epsilon**2 + (MODEL_SUPPORT_RADIUS_M * px_per_m) ** 2)
        rows.append(
            {
                "node_id": node["node_id"],
                "local_anchor_mode": mode,
                "local_holdout_count": int(len(selected)),
                "local_holdout_p50_px": local_p50,
                "local_holdout_p90_px": local_p90,
                "local_holdout_max_distance_px": float(np.max(distances[selected])),
                "radial_bracket": bool(
                    np.min(anchor_radial[selected]) <= node_radial[index]
                    <= np.max(anchor_radial[selected])
                ),
                "theta_bracket": bool(
                    np.min(anchor_theta[selected]) <= node_theta[index]
                    <= np.max(anchor_theta[selected])
                ),
                "epsilon_P0_px": float(epsilon),
                "sigma_region_px": float(sigma),
                "sigma_region_m": float(sigma / px_per_m),
            }
        )
    return pd.DataFrame(rows)


def tangential_unit(points: np.ndarray, geometry: dict[str, Any]) -> np.ndarray:
    center = np.array(
        [float(geometry["center_x_px"]), float(geometry["center_y_px"])],
        dtype=np.float64,
    )
    radial = points - center[None, :]
    norm = np.linalg.norm(radial, axis=1)
    norm = np.maximum(norm, 1e-9)
    radial = radial / norm[:, None]
    return np.column_stack((-radial[:, 1], radial[:, 0]))


def sample_mask(mask: np.ndarray, points: np.ndarray) -> np.ndarray:
    xi = np.rint(points[:, 0]).astype(int)
    yi = np.rint(points[:, 1]).astype(int)
    inside = (
        (xi >= 0)
        & (xi < mask.shape[1])
        & (yi >= 0)
        & (yi < mask.shape[0])
    )
    values = np.zeros(len(points), dtype=bool)
    values[inside] = mask[yi[inside], xi[inside]]
    return values


def build_temporal_graph(
    p0: Any,
    static_nodes: pd.DataFrame,
    frame_context: dict[str, dict[str, Any]],
    pairs: list[dict[str, Any]],
    anchors: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    uncertainty_rows: list[pd.DataFrame] = []
    incoming_rows: list[dict[str, Any]] = []
    outgoing_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    mutual_rows: list[dict[str, Any]] = []
    pair_summary_rows: list[dict[str, Any]] = []
    source_uids = [pair["from_frame_uid"] for pair in pairs]

    for pair_number, pair in enumerate(pairs, start=1):
        actual_source_nodes = static_nodes[
            static_nodes["frame_uid"] == pair["from_frame_uid"]
        ].sort_values("candidate_rank")
        destination_nodes = static_nodes[
            static_nodes["frame_uid"] == pair["to_frame_uid"]
        ].sort_values("candidate_rank")
        pair_anchors = anchors[
            (anchors["run_id"] == RUN_ID)
            & (anchors["lag"] == 1)
            & (anchors["from_frame_uid"] == pair["from_frame_uid"])
            & (anchors["to_frame_uid"] == pair["to_frame_uid"])
            & (anchors["anchor_split"] == "HOLDOUT")
        ].copy()
        if pair_anchors.empty:
            raise RuntimeError(f"no holdout anchors for {pair['from_frame_uid']}")

        actual_uncertainty = local_uncertainty_for_nodes(
            actual_source_nodes, pair_anchors, pair
        )
        actual_uncertainty.insert(0, "pair_index", pair["pair_index"])
        actual_uncertainty.insert(1, "from_frame_uid", pair["from_frame_uid"])
        actual_uncertainty.insert(2, "to_frame_uid", pair["to_frame_uid"])
        uncertainty_rows.append(actual_uncertainty)

        for condition in CONDITIONS:
            if condition == "SHUFFLED_SOURCE_SHIFT7":
                shuffled_uid = source_uids[
                    (pair["pair_index"] + SHUFFLE_PAIR_SHIFT) % len(source_uids)
                ]
                source_nodes = static_nodes[
                    static_nodes["frame_uid"] == shuffled_uid
                ].sort_values("candidate_rank")
                uncertainty = local_uncertainty_for_nodes(source_nodes, pair_anchors, pair)
                evidence_source_uid = shuffled_uid
            else:
                source_nodes = actual_source_nodes
                uncertainty = actual_uncertainty.drop(
                    columns=["pair_index", "from_frame_uid", "to_frame_uid"]
                )
                evidence_source_uid = pair["from_frame_uid"]

            uncertainty_index = uncertainty.set_index("node_id")
            source_xy = source_nodes[["x_px", "y_px"]].to_numpy(float)
            destination_xy = destination_nodes[["x_px", "y_px"]].to_numpy(float)
            translation = p0.predict_displacement(
                pair["model_state"], source_xy, pair["from_geometry"]
            )
            if condition == "CORRECT_P0" or condition == "SHUFFLED_SOURCE_SHIFT7":
                prediction = source_xy + translation
            elif condition == "ZERO_TRANSPORT":
                prediction = source_xy.copy()
            elif condition == "REVERSE_P0":
                prediction = source_xy - translation
            elif condition == "TANGENTIAL_PLUS_0_75M":
                tangent = tangential_unit(source_xy, pair["from_geometry"])
                perturbation_px = (
                    PERTURBATION_TANGENTIAL_M
                    * source_nodes["px_per_m"].to_numpy(float)[:, None]
                    * tangent
                )
                prediction = source_xy + translation + perturbation_px
            else:
                raise ValueError(condition)

            sigma = np.array(
                [
                    float(uncertainty_index.loc[item, "sigma_region_px"])
                    for item in source_nodes["node_id"]
                ],
                dtype=np.float64,
            )
            distance = np.linalg.norm(
                prediction[:, None, :] - destination_xy[None, :, :], axis=2
            )
            normalized_error = distance / np.maximum(sigma[:, None], 1e-9)
            geometry_support = np.exp(-0.5 * normalized_error**2)
            source_score = source_nodes["C2_score"].to_numpy(float)
            destination_score = destination_nodes["C2_score"].to_numpy(float)
            incoming_contribution = source_score[:, None] * geometry_support
            outgoing_contribution = destination_score[None, :] * geometry_support

            best_incoming_source = np.argmax(incoming_contribution, axis=0)
            best_geometry_source = np.argmin(normalized_error, axis=0)
            incoming_geometry_max = np.max(geometry_support, axis=0)
            incoming_support_max = np.max(incoming_contribution, axis=0)
            incoming_support_sum = np.sum(incoming_contribution, axis=0)
            incoming_geometry_sum = np.sum(geometry_support, axis=0)
            incoming_support_mean = incoming_support_sum / np.maximum(
                incoming_geometry_sum, 1e-12
            )
            incoming_count_1 = np.sum(normalized_error <= 1.0, axis=0)
            incoming_count_2 = np.sum(normalized_error <= 2.0, axis=0)
            incoming_count_3 = np.sum(normalized_error <= 3.0, axis=0)

            tie_breaker = destination_nodes["candidate_rank"].to_numpy(int)
            incoming_max_rank, incoming_max_percentile = rank_descending(
                incoming_support_max, tie_breaker
            )
            incoming_sum_rank, incoming_sum_percentile = rank_descending(
                incoming_support_sum, tie_breaker
            )
            incoming_mean_rank, incoming_mean_percentile = rank_descending(
                incoming_support_mean, tie_breaker
            )
            incoming_geometry_rank, incoming_geometry_percentile = rank_descending(
                incoming_geometry_max, tie_breaker
            )

            predicted_inside = sample_mask(
                frame_context[pair["to_frame_uid"]]["mask"], prediction
            )
            source_records = source_nodes.to_dict("records")
            destination_records = destination_nodes.to_dict("records")
            uncertainty_records = uncertainty_index.to_dict("index")

            for destination_index, destination in enumerate(destination_records):
                best_source = source_records[int(best_incoming_source[destination_index])]
                geometry_source = source_records[int(best_geometry_source[destination_index])]
                incoming_rows.append(
                    {
                        "condition": condition,
                        "pair_index": pair["pair_index"],
                        "actual_from_frame_uid": pair["from_frame_uid"],
                        "evidence_source_frame_uid": evidence_source_uid,
                        "to_frame_uid": pair["to_frame_uid"],
                        "to_frame_index": pair["to_frame"],
                        "destination_node_id": destination["node_id"],
                        "destination_candidate_rank": destination["candidate_rank"],
                        "destination_C2_score": destination["C2_score"],
                        "display_stratum": pair["display_stratum"],
                        "incoming_geometry_max": float(
                            incoming_geometry_max[destination_index]
                        ),
                        "incoming_geometry_rank": int(
                            incoming_geometry_rank[destination_index]
                        ),
                        "incoming_geometry_percentile": float(
                            incoming_geometry_percentile[destination_index]
                        ),
                        "incoming_count_1sigma": int(incoming_count_1[destination_index]),
                        "incoming_count_2sigma": int(incoming_count_2[destination_index]),
                        "incoming_count_3sigma": int(incoming_count_3[destination_index]),
                        "incoming_support_max": float(
                            incoming_support_max[destination_index]
                        ),
                        "incoming_support_max_rank": int(
                            incoming_max_rank[destination_index]
                        ),
                        "incoming_support_max_percentile": float(
                            incoming_max_percentile[destination_index]
                        ),
                        "incoming_support_sum": float(
                            incoming_support_sum[destination_index]
                        ),
                        "incoming_support_sum_rank": int(
                            incoming_sum_rank[destination_index]
                        ),
                        "incoming_support_sum_percentile": float(
                            incoming_sum_percentile[destination_index]
                        ),
                        "incoming_support_mean": float(
                            incoming_support_mean[destination_index]
                        ),
                        "incoming_support_mean_rank": int(
                            incoming_mean_rank[destination_index]
                        ),
                        "incoming_support_mean_percentile": float(
                            incoming_mean_percentile[destination_index]
                        ),
                        "best_support_source_node_id": best_source["node_id"],
                        "best_support_source_rank": int(best_source["candidate_rank"]),
                        "best_support_source_percentile": float(
                            best_source["candidate_pool_percentile"]
                        ),
                        "best_support_source_C2_score": float(best_source["C2_score"]),
                        "best_support_normalized_error": float(
                            normalized_error[
                                int(best_incoming_source[destination_index]),
                                destination_index,
                            ]
                        ),
                        "geometric_nearest_source_node_id": geometry_source["node_id"],
                        "geometric_nearest_normalized_error": float(
                            normalized_error[
                                int(best_geometry_source[destination_index]),
                                destination_index,
                            ]
                        ),
                    }
                )

            best_outgoing_destination = np.argmax(outgoing_contribution, axis=1)
            best_outgoing_geometry = np.argmin(normalized_error, axis=1)
            outgoing_geometry_max = np.max(geometry_support, axis=1)
            outgoing_support_max = np.max(outgoing_contribution, axis=1)
            outgoing_support_sum = np.sum(outgoing_contribution, axis=1)
            outgoing_geometry_sum = np.sum(geometry_support, axis=1)
            outgoing_support_mean = outgoing_support_sum / np.maximum(
                outgoing_geometry_sum, 1e-12
            )
            outgoing_count_1 = np.sum(normalized_error <= 1.0, axis=1)
            outgoing_count_2 = np.sum(normalized_error <= 2.0, axis=1)
            outgoing_count_3 = np.sum(normalized_error <= 3.0, axis=1)
            source_tie = source_nodes["candidate_rank"].to_numpy(int)
            outgoing_max_rank, outgoing_max_percentile = rank_descending(
                outgoing_support_max, source_tie
            )
            outgoing_sum_rank, outgoing_sum_percentile = rank_descending(
                outgoing_support_sum, source_tie
            )
            outgoing_mean_rank, outgoing_mean_percentile = rank_descending(
                outgoing_support_mean, source_tie
            )

            for source_index, source in enumerate(source_records):
                best_destination = destination_records[
                    int(best_outgoing_destination[source_index])
                ]
                uncertainty_row = uncertainty_records[source["node_id"]]
                outgoing_rows.append(
                    {
                        "condition": condition,
                        "pair_index": pair["pair_index"],
                        "actual_from_frame_uid": pair["from_frame_uid"],
                        "evidence_source_frame_uid": evidence_source_uid,
                        "to_frame_uid": pair["to_frame_uid"],
                        "source_node_id": source["node_id"],
                        "source_frame_uid": source["frame_uid"],
                        "source_candidate_rank": source["candidate_rank"],
                        "source_C2_score": source["C2_score"],
                        "predicted_x_px": float(prediction[source_index, 0]),
                        "predicted_y_px": float(prediction[source_index, 1]),
                        "prediction_inside_target_Omega_single": bool(
                            predicted_inside[source_index]
                        ),
                        **uncertainty_row,
                        "outgoing_geometry_max": float(
                            outgoing_geometry_max[source_index]
                        ),
                        "outgoing_count_1sigma": int(outgoing_count_1[source_index]),
                        "outgoing_count_2sigma": int(outgoing_count_2[source_index]),
                        "outgoing_count_3sigma": int(outgoing_count_3[source_index]),
                        "outgoing_support_max": float(
                            outgoing_support_max[source_index]
                        ),
                        "outgoing_support_max_rank": int(
                            outgoing_max_rank[source_index]
                        ),
                        "outgoing_support_max_percentile": float(
                            outgoing_max_percentile[source_index]
                        ),
                        "outgoing_support_sum": float(
                            outgoing_support_sum[source_index]
                        ),
                        "outgoing_support_sum_rank": int(
                            outgoing_sum_rank[source_index]
                        ),
                        "outgoing_support_sum_percentile": float(
                            outgoing_sum_percentile[source_index]
                        ),
                        "outgoing_support_mean": float(
                            outgoing_support_mean[source_index]
                        ),
                        "outgoing_support_mean_rank": int(
                            outgoing_mean_rank[source_index]
                        ),
                        "outgoing_support_mean_percentile": float(
                            outgoing_mean_percentile[source_index]
                        ),
                        "best_support_destination_node_id": best_destination["node_id"],
                        "best_support_destination_rank": int(
                            best_destination["candidate_rank"]
                        ),
                        "best_support_destination_C2_score": float(
                            best_destination["C2_score"]
                        ),
                        "best_support_normalized_error": float(
                            normalized_error[
                                source_index,
                                int(best_outgoing_destination[source_index]),
                            ]
                        ),
                        "geometric_nearest_destination_node_id": destination_records[
                            int(best_outgoing_geometry[source_index])
                        ]["node_id"],
                        "geometric_nearest_normalized_error": float(
                            normalized_error[
                                source_index,
                                int(best_outgoing_geometry[source_index]),
                            ]
                        ),
                    }
                )

            edge_source, edge_destination = np.where(
                normalized_error <= EDGE_EXPORT_MAX_SIGMA
            )
            for source_index, destination_index in zip(
                edge_source.tolist(), edge_destination.tolist()
            ):
                source = source_records[source_index]
                destination = destination_records[destination_index]
                edge_rows.append(
                    {
                        "condition": condition,
                        "pair_index": pair["pair_index"],
                        "actual_from_frame_uid": pair["from_frame_uid"],
                        "evidence_source_frame_uid": evidence_source_uid,
                        "to_frame_uid": pair["to_frame_uid"],
                        "source_node_id": source["node_id"],
                        "destination_node_id": destination["node_id"],
                        "source_rank": int(source["candidate_rank"]),
                        "destination_rank": int(destination["candidate_rank"]),
                        "source_C2_score": float(source["C2_score"]),
                        "destination_C2_score": float(destination["C2_score"]),
                        "predicted_x_px": float(prediction[source_index, 0]),
                        "predicted_y_px": float(prediction[source_index, 1]),
                        "distance_to_prediction_px": float(
                            distance[source_index, destination_index]
                        ),
                        "sigma_region_px": float(sigma[source_index]),
                        "normalized_error": float(
                            normalized_error[source_index, destination_index]
                        ),
                        "geometric_support": float(
                            geometry_support[source_index, destination_index]
                        ),
                        "source_score_x_geometry": float(
                            incoming_contribution[source_index, destination_index]
                        ),
                        "destination_score_x_geometry": float(
                            outgoing_contribution[source_index, destination_index]
                        ),
                        "within_1sigma": bool(
                            normalized_error[source_index, destination_index] <= 1.0
                        ),
                        "within_2sigma": bool(
                            normalized_error[source_index, destination_index] <= 2.0
                        ),
                        "within_3sigma": True,
                    }
                )

            if condition in THREAD_CONDITIONS:
                nearest_destination = np.argmin(normalized_error, axis=1)
                nearest_source = np.argmin(normalized_error, axis=0)
                mutual_count = 0
                for source_index, destination_index in enumerate(nearest_destination):
                    if (
                        int(nearest_source[destination_index]) == source_index
                        and normalized_error[source_index, destination_index]
                        <= THREAD_MUTUAL_MAX_SIGMA
                    ):
                        mutual_rows.append(
                            {
                                "condition": condition,
                                "pair_index": pair["pair_index"],
                                "from_frame_uid": pair["from_frame_uid"],
                                "to_frame_uid": pair["to_frame_uid"],
                                "source_node_id": source_records[source_index]["node_id"],
                                "destination_node_id": destination_records[
                                    int(destination_index)
                                ]["node_id"],
                                "normalized_error": float(
                                    normalized_error[source_index, destination_index]
                                ),
                                "geometric_support": float(
                                    geometry_support[source_index, destination_index]
                                ),
                            }
                        )
                        mutual_count += 1
            else:
                mutual_count = 0

            pair_summary_rows.append(
                {
                    "condition": condition,
                    "pair_index": pair["pair_index"],
                    "from_frame": pair["from_frame"],
                    "to_frame": pair["to_frame"],
                    "actual_from_frame_uid": pair["from_frame_uid"],
                    "evidence_source_frame_uid": evidence_source_uid,
                    "to_frame_uid": pair["to_frame_uid"],
                    "source_candidate_count": int(len(source_nodes)),
                    "destination_candidate_count": int(len(destination_nodes)),
                    "edge_count_1sigma": int(np.sum(normalized_error <= 1.0)),
                    "edge_count_2sigma": int(np.sum(normalized_error <= 2.0)),
                    "edge_count_3sigma": int(np.sum(normalized_error <= 3.0)),
                    "source_without_3sigma_neighbor_count": int(
                        np.sum(np.min(normalized_error, axis=1) > 3.0)
                    ),
                    "destination_without_3sigma_predecessor_count": int(
                        np.sum(np.min(normalized_error, axis=0) > 3.0)
                    ),
                    "mutual_nearest_edge_count_2sigma": int(mutual_count),
                    "median_nearest_normalized_error_source_to_destination": float(
                        np.median(np.min(normalized_error, axis=1))
                    ),
                    "median_nearest_normalized_error_destination_to_source": float(
                        np.median(np.min(normalized_error, axis=0))
                    ),
                    "global_holdout_p90_px": pair["global_holdout_p90_px"],
                    "display_stratum": pair["display_stratum"],
                }
            )
        print(
            f"temporal pair {pair_number}/{len(pairs)} {pair['from_frame']}->{pair['to_frame']}",
            flush=True,
        )

    return (
        pd.concat(uncertainty_rows, ignore_index=True),
        pd.DataFrame(incoming_rows),
        pd.DataFrame(outgoing_rows),
        pd.DataFrame(edge_rows),
        pd.DataFrame(mutual_rows),
        pd.DataFrame(pair_summary_rows),
    )


def ambiguity_label(count: Any) -> str:
    if not np.isfinite(float(count)):
        return "NO_TEMPORAL_SIDE"
    value = int(count)
    if value == 0:
        return "NO_CANDIDATE_WITHIN_1SIGMA"
    if value == 1:
        return "UNIQUE_WITHIN_1SIGMA"
    return "MULTIPLE_WITHIN_1SIGMA"


def build_dynamic_state(
    static_nodes: pd.DataFrame,
    incoming: pd.DataFrame,
    outgoing: pd.DataFrame,
) -> pd.DataFrame:
    states: list[pd.DataFrame] = []
    incoming_key = incoming.rename(columns={"destination_node_id": "node_id"})
    outgoing_key = outgoing.rename(columns={"source_node_id": "node_id"})
    for condition in CONDITIONS:
        state = static_nodes.copy()
        state.insert(0, "condition", condition)
        incoming_columns = [
            "node_id",
            "incoming_geometry_max",
            "incoming_geometry_rank",
            "incoming_geometry_percentile",
            "incoming_count_1sigma",
            "incoming_count_2sigma",
            "incoming_count_3sigma",
            "incoming_support_max",
            "incoming_support_max_rank",
            "incoming_support_max_percentile",
            "incoming_support_sum",
            "incoming_support_sum_rank",
            "incoming_support_sum_percentile",
            "incoming_support_mean",
            "incoming_support_mean_rank",
            "incoming_support_mean_percentile",
            "best_support_source_node_id",
            "best_support_source_rank",
            "best_support_source_percentile",
            "best_support_normalized_error",
            "display_stratum",
        ]
        condition_incoming = incoming_key[
            incoming_key["condition"] == condition
        ][incoming_columns]
        state = state.merge(condition_incoming, on="node_id", how="left")
        if condition != "SHUFFLED_SOURCE_SHIFT7":
            outgoing_columns = [
                "node_id",
                "outgoing_geometry_max",
                "outgoing_count_1sigma",
                "outgoing_count_2sigma",
                "outgoing_count_3sigma",
                "outgoing_support_max",
                "outgoing_support_max_rank",
                "outgoing_support_max_percentile",
                "outgoing_support_sum",
                "outgoing_support_sum_rank",
                "outgoing_support_sum_percentile",
                "outgoing_support_mean",
                "outgoing_support_mean_rank",
                "outgoing_support_mean_percentile",
                "best_support_destination_node_id",
                "best_support_destination_rank",
                "best_support_normalized_error",
                "epsilon_P0_px",
                "sigma_region_px",
                "sigma_region_m",
                "local_anchor_mode",
                "local_holdout_count",
                "local_holdout_p50_px",
                "local_holdout_p90_px",
                "radial_bracket",
                "theta_bracket",
                "prediction_inside_target_Omega_single",
            ]
            condition_outgoing = outgoing_key[
                outgoing_key["condition"] == condition
            ][outgoing_columns]
            state = state.merge(condition_outgoing, on="node_id", how="left")
        else:
            for column in (
                "outgoing_geometry_max",
                "outgoing_count_1sigma",
                "outgoing_count_2sigma",
                "outgoing_count_3sigma",
                "outgoing_support_max",
                "outgoing_support_max_rank",
                "outgoing_support_max_percentile",
                "outgoing_support_sum",
                "outgoing_support_sum_rank",
                "outgoing_support_sum_percentile",
                "outgoing_support_mean",
                "outgoing_support_mean_rank",
                "outgoing_support_mean_percentile",
            ):
                state[column] = np.nan

        state["incoming_ambiguity_1sigma"] = state[
            "incoming_count_1sigma"
        ].apply(ambiguity_label)
        state["outgoing_ambiguity_1sigma"] = state[
            "outgoing_count_1sigma"
        ].apply(ambiguity_label)
        both = state["incoming_support_max"].notna() & state[
            "outgoing_support_max"
        ].notna()
        state["bidirectional_support_geomean"] = np.nan
        state.loc[both, "bidirectional_support_geomean"] = np.sqrt(
            state.loc[both, "incoming_support_max"]
            * state.loc[both, "outgoing_support_max"]
        )
        state["bidirectional_support_min"] = np.nan
        state.loc[both, "bidirectional_support_min"] = np.minimum(
            state.loc[both, "incoming_support_max"],
            state.loc[both, "outgoing_support_max"],
        )
        state["bidirectional_support_geomean_rank"] = 0
        state["bidirectional_support_geomean_percentile"] = np.nan
        for frame_uid, indices in state.groupby("frame_uid").groups.items():
            index_array = np.asarray(list(indices), dtype=int)
            values = state.loc[
                index_array, "bidirectional_support_geomean"
            ].to_numpy(float)
            tie = state.loc[index_array, "candidate_rank"].to_numpy(int)
            ranks, percentile = rank_descending(values, tie)
            state.loc[index_array, "bidirectional_support_geomean_rank"] = ranks
            state.loc[
                index_array, "bidirectional_support_geomean_percentile"
            ] = percentile
        states.append(state)
    return pd.concat(states, ignore_index=True)


def build_threads(
    static_nodes: pd.DataFrame,
    mutual_edges: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[str, str], tuple[str, int]]]:
    member_rows: list[dict[str, Any]] = []
    thread_rows: list[dict[str, Any]] = []
    mapping: dict[tuple[str, str], tuple[str, int]] = {}
    node_index = static_nodes.set_index("node_id").to_dict("index")
    all_node_ids = list(node_index)
    for condition in THREAD_CONDITIONS:
        edges = mutual_edges[mutual_edges["condition"] == condition]
        next_map = dict(zip(edges["source_node_id"], edges["destination_node_id"]))
        previous_map = dict(zip(edges["destination_node_id"], edges["source_node_id"]))
        edge_error = {
            (row.source_node_id, row.destination_node_id): float(row.normalized_error)
            for row in edges.itertuples()
        }
        unvisited = set(all_node_ids)
        starts = sorted(
            [node for node in all_node_ids if node not in previous_map],
            key=lambda item: (
                int(node_index[item]["frame_index"]),
                int(node_index[item]["candidate_rank"]),
            ),
        )
        thread_number = 0
        for start in starts:
            if start not in unvisited:
                continue
            thread_number += 1
            thread_id = f"{condition}_T{thread_number:05d}"
            chain: list[str] = []
            current = start
            while current in unvisited:
                chain.append(current)
                unvisited.remove(current)
                if current not in next_map:
                    break
                current = next_map[current]
            errors: list[float] = []
            for index, item in enumerate(chain):
                record = node_index[item]
                error_to_next = math.nan
                if index + 1 < len(chain):
                    error_to_next = edge_error[(item, chain[index + 1])]
                    errors.append(error_to_next)
                member_rows.append(
                    {
                        "condition": condition,
                        "thread_id": thread_id,
                        "thread_position": index,
                        "node_id": item,
                        "frame_uid": record["frame_uid"],
                        "frame_index": int(record["frame_index"]),
                        "candidate_rank": int(record["candidate_rank"]),
                        "candidate_pool_percentile": float(
                            record["candidate_pool_percentile"]
                        ),
                        "C2_score": float(record["C2_score"]),
                        "x_px": float(record["x_px"]),
                        "y_px": float(record["y_px"]),
                        "normalized_error_to_next": error_to_next,
                    }
                )
                mapping[(condition, item)] = (thread_id, len(chain))
            records = [node_index[item] for item in chain]
            thread_rows.append(
                {
                    "condition": condition,
                    "thread_id": thread_id,
                    "node_count": int(len(chain)),
                    "start_frame_index": int(records[0]["frame_index"]),
                    "end_frame_index": int(records[-1]["frame_index"]),
                    "frame_span": int(
                        records[-1]["frame_index"] - records[0]["frame_index"] + 1
                    ),
                    "mean_C2_score": float(
                        np.mean([record["C2_score"] for record in records])
                    ),
                    "mean_candidate_pool_percentile": float(
                        np.mean(
                            [record["candidate_pool_percentile"] for record in records]
                        )
                    ),
                    "mean_rank_fraction": float(
                        np.mean([record["rank_fraction"] for record in records])
                    ),
                    "mean_normalized_error": (
                        float(np.mean(errors)) if errors else math.nan
                    ),
                    "max_normalized_error": (
                        float(np.max(errors)) if errors else math.nan
                    ),
                }
            )
        if unvisited:
            raise RuntimeError(f"unvisited nodes in {condition}: {len(unvisited)}")
    return pd.DataFrame(thread_rows), pd.DataFrame(member_rows), mapping


def add_thread_mapping(
    dynamic_state: pd.DataFrame,
    mapping: dict[tuple[str, str], tuple[str, int]],
) -> pd.DataFrame:
    output = dynamic_state.copy()
    output["thread_id"] = ""
    output["thread_node_count"] = np.nan
    for index, row in output.iterrows():
        key = (row["condition"], row["node_id"])
        if key in mapping:
            output.at[index, "thread_id"] = mapping[key][0]
            output.at[index, "thread_node_count"] = mapping[key][1]
    return output


def metric_best_within(
    nodes: pd.DataFrame,
    point: np.ndarray,
    px_per_m: float,
    radius_m: float,
) -> dict[str, Any]:
    xy = nodes[["x_px", "y_px"]].to_numpy(float)
    distances = np.linalg.norm(xy - point[None, :], axis=1) / px_per_m
    select = distances <= radius_m + 1e-9
    result: dict[str, Any] = {
        "candidate_count_within_radius": int(np.sum(select)),
        "nearest_distance_m": float(np.min(distances)) if len(distances) else math.nan,
    }
    if not np.any(select):
        for prefix in (
            "image",
            "incoming_max",
            "incoming_sum",
            "incoming_mean",
            "outgoing_max",
            "outgoing_sum",
            "bidirectional",
        ):
            result[f"{prefix}_best_rank"] = math.nan
            result[f"{prefix}_best_percentile"] = math.nan
            result[f"{prefix}_best_node_id"] = ""
        result["max_thread_node_count"] = math.nan
        return result

    selected = nodes.loc[select].copy()
    metrics = {
        "image": ("candidate_rank", "candidate_pool_percentile"),
        "incoming_max": (
            "incoming_support_max_rank",
            "incoming_support_max_percentile",
        ),
        "incoming_sum": (
            "incoming_support_sum_rank",
            "incoming_support_sum_percentile",
        ),
        "incoming_mean": (
            "incoming_support_mean_rank",
            "incoming_support_mean_percentile",
        ),
        "outgoing_max": (
            "outgoing_support_max_rank",
            "outgoing_support_max_percentile",
        ),
        "outgoing_sum": (
            "outgoing_support_sum_rank",
            "outgoing_support_sum_percentile",
        ),
        "bidirectional": (
            "bidirectional_support_geomean_rank",
            "bidirectional_support_geomean_percentile",
        ),
    }
    for prefix, (rank_column, percentile_column) in metrics.items():
        valid = selected[np.isfinite(pd.to_numeric(selected[rank_column], errors="coerce"))]
        valid = valid[pd.to_numeric(valid[rank_column], errors="coerce") > 0]
        if valid.empty:
            result[f"{prefix}_best_rank"] = math.nan
            result[f"{prefix}_best_percentile"] = math.nan
            result[f"{prefix}_best_node_id"] = ""
        else:
            best = valid.sort_values([rank_column, "candidate_rank"]).iloc[0]
            result[f"{prefix}_best_rank"] = float(best[rank_column])
            result[f"{prefix}_best_percentile"] = float(best[percentile_column])
            result[f"{prefix}_best_node_id"] = str(best["node_id"])
    result["max_thread_node_count"] = (
        float(selected["thread_node_count"].max())
        if selected["thread_node_count"].notna().any()
        else math.nan
    )
    return result


def evaluate_offline_points(
    dynamic_state: pd.DataFrame,
    references: pd.DataFrame,
    offsets: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    reference_rows: list[dict[str, Any]] = []
    offset_rows: list[dict[str, Any]] = []
    reference_primary = references[
        (references["run_id"] == RUN_ID) & (references["candidate"] == PRIMARY)
    ].copy()
    offset_primary = offsets[
        (offsets["run_id"] == RUN_ID) & (offsets["candidate"] == PRIMARY)
    ].copy()

    state_groups = {
        (condition, frame_uid): rows
        for (condition, frame_uid), rows in dynamic_state.groupby(
            ["condition", "frame_uid"], sort=False
        )
    }
    for reference in reference_primary.to_dict("records"):
        point = np.array(
            [float(reference["reference_x_px"]), float(reference["reference_y_px"])]
        )
        px_per_m = float(
            dynamic_state[
                dynamic_state["frame_uid"] == reference["frame_uid"]
            ]["px_per_m"].iloc[0]
        )
        for condition in CONDITIONS:
            nodes = state_groups[(condition, reference["frame_uid"])]
            row: dict[str, Any] = {
                "point_kind": "MANUAL_REFERENCE",
                "run_id": RUN_ID,
                "frame_uid": reference["frame_uid"],
                "frame_index": int(reference["frame_index"]),
                "target_id": reference["target_id"],
                "condition": condition,
                "point_x_px": float(point[0]),
                "point_y_px": float(point[1]),
                "reference_support_status": reference["reference_support_status"],
                "single_frame_failure_class": reference[
                    "candidate_presence_class_v2"
                ],
                "single_frame_merging_suspected": bool(
                    reference["response_merging_suspected_any_rank"]
                ),
            }
            for radius in REFERENCE_RADII_M:
                suffix = f"r{int(round(radius * 100)):02d}cm"
                metrics = metric_best_within(nodes, point, px_per_m, radius)
                row.update({f"{key}_{suffix}": value for key, value in metrics.items()})
            row["incoming_max_rank_delta_vs_image_r80cm"] = (
                row["image_best_rank_r80cm"] - row["incoming_max_best_rank_r80cm"]
                if np.isfinite(row["image_best_rank_r80cm"])
                and np.isfinite(row["incoming_max_best_rank_r80cm"])
                else math.nan
            )
            row["incoming_sum_rank_delta_vs_image_r80cm"] = (
                row["image_best_rank_r80cm"] - row["incoming_sum_best_rank_r80cm"]
                if np.isfinite(row["image_best_rank_r80cm"])
                and np.isfinite(row["incoming_sum_best_rank_r80cm"])
                else math.nan
            )
            reference_rows.append(row)

    for control in offset_primary.to_dict("records"):
        point = np.array([float(control["control_x_px"]), float(control["control_y_px"])])
        px_per_m = float(
            dynamic_state[dynamic_state["frame_uid"] == control["frame_uid"]][
                "px_per_m"
            ].iloc[0]
        )
        for condition in CONDITIONS:
            nodes = state_groups[(condition, control["frame_uid"])]
            row = {
                "point_kind": "FIXED_OFFSET",
                "run_id": RUN_ID,
                "frame_uid": control["frame_uid"],
                "frame_index": int(control["frame_index"]),
                "target_id": control["target_id"],
                "control_direction": control["control_direction"],
                "condition": condition,
                "point_x_px": float(point[0]),
                "point_y_px": float(point[1]),
                "control_support_status": control["control_support_status"],
            }
            for radius in REFERENCE_RADII_M:
                suffix = f"r{int(round(radius * 100)):02d}cm"
                metrics = metric_best_within(nodes, point, px_per_m, radius)
                row.update({f"{key}_{suffix}": value for key, value in metrics.items()})
            offset_rows.append(row)
    return pd.DataFrame(reference_rows), pd.DataFrame(offset_rows)


def candidate_set_near_point(
    static_nodes: pd.DataFrame,
    frame_uid: str,
    point: np.ndarray,
    radius_m: float,
) -> set[str]:
    nodes = static_nodes[static_nodes["frame_uid"] == frame_uid]
    px_per_m = float(nodes["px_per_m"].iloc[0])
    distances = np.linalg.norm(
        nodes[["x_px", "y_px"]].to_numpy(float) - point[None, :], axis=1
    ) / px_per_m
    return set(nodes.loc[distances <= radius_m + 1e-9, "node_id"].astype(str))


def two_reference_state(first: set[str], second: set[str]) -> str:
    if first and second:
        return "SHARED" if first.intersection(second) else "SEPARATED"
    if first or second:
        return "PARTIAL"
    return "MISSING"


def build_shared_transitions(
    static_nodes: pd.DataFrame,
    references: pd.DataFrame,
    edges: pd.DataFrame,
    mutual_edges: pd.DataFrame,
) -> pd.DataFrame:
    manual = references[
        (references["run_id"] == RUN_ID) & (references["candidate"] == PRIMARY)
    ].copy()
    frame_indices = sorted(manual["frame_index"].unique())
    groups = {
        "P01_P02": ("R02ZF_SARPERSON01", "R02ZF_SARPERSON02"),
        "P03_P04": ("R02ZF_SARPERSON03", "R02ZF_SARPERSON04"),
    }
    full_adjacency: dict[tuple[str, str], dict[str, set[str]]] = {}
    mutual_adjacency: dict[tuple[str, str], dict[str, set[str]]] = {}
    for condition in THREAD_CONDITIONS:
        for from_frame in range(472, 494):
            from_uid = f"R02ZF_SARF{from_frame:06d}"
            key = (condition, from_uid)
            subset = edges[
                (edges["condition"] == condition)
                & (edges["actual_from_frame_uid"] == from_uid)
                & edges["within_2sigma"].astype(bool)
            ]
            mapping: dict[str, set[str]] = defaultdict(set)
            for row in subset.itertuples():
                mapping[str(row.source_node_id)].add(str(row.destination_node_id))
            full_adjacency[key] = mapping
            subset_mutual = mutual_edges[
                (mutual_edges["condition"] == condition)
                & (mutual_edges["from_frame_uid"] == from_uid)
            ]
            mutual_mapping: dict[str, set[str]] = defaultdict(set)
            for row in subset_mutual.itertuples():
                mutual_mapping[str(row.source_node_id)].add(
                    str(row.destination_node_id)
                )
            mutual_adjacency[key] = mutual_mapping

    rows: list[dict[str, Any]] = []
    manual_lookup = manual.set_index(["frame_index", "target_id"])
    for group_name, (first_target, second_target) in groups.items():
        for from_frame, to_frame in zip(frame_indices[:-1], frame_indices[1:]):
            from_uid = f"R02ZF_SARF{int(from_frame):06d}"
            to_uid = f"R02ZF_SARF{int(to_frame):06d}"
            first_from = manual_lookup.loc[(from_frame, first_target)]
            second_from = manual_lookup.loc[(from_frame, second_target)]
            first_to = manual_lookup.loc[(to_frame, first_target)]
            second_to = manual_lookup.loc[(to_frame, second_target)]
            first_from_set = candidate_set_near_point(
                static_nodes,
                from_uid,
                np.array([first_from["reference_x_px"], first_from["reference_y_px"]]),
                0.80,
            )
            second_from_set = candidate_set_near_point(
                static_nodes,
                from_uid,
                np.array([second_from["reference_x_px"], second_from["reference_y_px"]]),
                0.80,
            )
            first_to_set = candidate_set_near_point(
                static_nodes,
                to_uid,
                np.array([first_to["reference_x_px"], first_to["reference_y_px"]]),
                0.80,
            )
            second_to_set = candidate_set_near_point(
                static_nodes,
                to_uid,
                np.array([second_to["reference_x_px"], second_to["reference_y_px"]]),
                0.80,
            )
            for condition in THREAD_CONDITIONS:
                for graph_mode, adjacency in (
                    ("FULL_2SIGMA", full_adjacency),
                    ("MUTUAL_NEAREST_2SIGMA", mutual_adjacency),
                ):
                    reachable = set(first_from_set).union(second_from_set)
                    peak_reachable_count = len(reachable)
                    for frame_index in range(int(from_frame), int(to_frame)):
                        uid = f"R02ZF_SARF{frame_index:06d}"
                        mapping = adjacency[(condition, uid)]
                        next_reachable: set[str] = set()
                        for item in reachable:
                            next_reachable.update(mapping.get(item, set()))
                        reachable = next_reachable
                        peak_reachable_count = max(peak_reachable_count, len(reachable))
                        if not reachable:
                            break
                    first_reachable = reachable.intersection(first_to_set)
                    second_reachable = reachable.intersection(second_to_set)
                    rows.append(
                        {
                            "group": group_name,
                            "first_target_id": first_target,
                            "second_target_id": second_target,
                            "from_frame": int(from_frame),
                            "to_frame": int(to_frame),
                            "frame_gap": int(to_frame - from_frame),
                            "condition": condition,
                            "graph_mode": graph_mode,
                            "source_single_frame_state": two_reference_state(
                                first_from_set, second_from_set
                            ),
                            "destination_single_frame_state": two_reference_state(
                                first_to_set, second_to_set
                            ),
                            "reachable_state": two_reference_state(
                                first_reachable, second_reachable
                            ),
                            "source_union_candidate_count": int(
                                len(first_from_set.union(second_from_set))
                            ),
                            "reachable_candidate_count_at_destination": int(
                                len(reachable)
                            ),
                            "peak_reachable_candidate_count": int(
                                peak_reachable_count
                            ),
                            "first_target_reachable_candidate_count": int(
                                len(first_reachable)
                            ),
                            "second_target_reachable_candidate_count": int(
                                len(second_reachable)
                            ),
                            "shared_reachable_candidate_count": int(
                                len(first_reachable.intersection(second_reachable))
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def summarize_reference_evaluation(reference_eval: pd.DataFrame) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for (condition, target_id), rows in reference_eval.groupby(
        ["condition", "target_id"]
    ):
        incoming = rows[
            np.isfinite(rows["incoming_max_best_rank_r80cm"])
            & np.isfinite(rows["image_best_rank_r80cm"])
        ]
        outgoing = rows[
            np.isfinite(rows["outgoing_max_best_rank_r80cm"])
            & np.isfinite(rows["image_best_rank_r80cm"])
        ]
        summaries.append(
            {
                "condition": condition,
                "target_id": target_id,
                "reference_count": int(len(rows)),
                "radius_candidate_missing_count_0_80m": int(
                    np.sum(rows["candidate_count_within_radius_r80cm"] == 0)
                ),
                "incoming_evaluable_count": int(len(incoming)),
                "median_image_best_rank_0_80m": (
                    float(incoming["image_best_rank_r80cm"].median())
                    if len(incoming)
                    else math.nan
                ),
                "median_incoming_max_best_rank_0_80m": (
                    float(incoming["incoming_max_best_rank_r80cm"].median())
                    if len(incoming)
                    else math.nan
                ),
                "median_incoming_sum_best_rank_0_80m": (
                    float(incoming["incoming_sum_best_rank_r80cm"].median())
                    if len(incoming)
                    else math.nan
                ),
                "median_incoming_max_rank_delta_vs_image": (
                    float(incoming["incoming_max_rank_delta_vs_image_r80cm"].median())
                    if len(incoming)
                    else math.nan
                ),
                "incoming_max_rank_improved_fraction": (
                    float(
                        (incoming["incoming_max_rank_delta_vs_image_r80cm"] > 0).mean()
                    )
                    if len(incoming)
                    else math.nan
                ),
                "incoming_max_rank_worsened_fraction": (
                    float(
                        (incoming["incoming_max_rank_delta_vs_image_r80cm"] < 0).mean()
                    )
                    if len(incoming)
                    else math.nan
                ),
                "median_incoming_max_percentile_0_80m": (
                    float(incoming["incoming_max_best_percentile_r80cm"].median())
                    if len(incoming)
                    else math.nan
                ),
                "outgoing_evaluable_count": int(len(outgoing)),
                "median_outgoing_max_best_rank_0_80m": (
                    float(outgoing["outgoing_max_best_rank_r80cm"].median())
                    if len(outgoing)
                    else math.nan
                ),
                "median_max_thread_node_count_0_80m": (
                    float(rows["max_thread_node_count_r80cm"].median())
                    if rows["max_thread_node_count_r80cm"].notna().any()
                    else math.nan
                ),
            }
        )
    return summaries


def compare_correct_to_controls(reference_eval: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    keys = ["frame_uid", "target_id"]
    correct = reference_eval[reference_eval["condition"] == "CORRECT_P0"].set_index(keys)
    for control in CONDITIONS[1:]:
        other = reference_eval[reference_eval["condition"] == control].set_index(keys)
        joined = correct.join(other, lsuffix="_correct", rsuffix="_control", how="inner")
        for metric in (
            "incoming_max_best_rank_r80cm",
            "incoming_sum_best_rank_r80cm",
            "incoming_mean_best_rank_r80cm",
        ):
            valid = joined[
                np.isfinite(joined[f"{metric}_correct"])
                & np.isfinite(joined[f"{metric}_control"])
            ]
            difference = (
                valid[f"{metric}_control"] - valid[f"{metric}_correct"]
            )
            rows.append(
                {
                    "control": control,
                    "metric": metric,
                    "paired_count": int(len(valid)),
                    "median_control_rank_minus_correct_rank": (
                        float(difference.median()) if len(valid) else math.nan
                    ),
                    "correct_better_fraction": (
                        float((difference > 0).mean()) if len(valid) else math.nan
                    ),
                    "tie_fraction": (
                        float((difference == 0).mean()) if len(valid) else math.nan
                    ),
                    "correct_worse_fraction": (
                        float((difference < 0).mean()) if len(valid) else math.nan
                    ),
                }
            )
    return rows


def summarize_threads(threads: pd.DataFrame, static_node_count: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition, group in threads.groupby("condition"):
        node_counts = group["node_count"].to_numpy(int)
        rows.append(
            {
                "condition": condition,
                "thread_count": int(len(group)),
                "median_thread_node_count": float(np.median(node_counts)),
                "p90_thread_node_count": float(np.quantile(node_counts, 0.90)),
                "max_thread_node_count": int(np.max(node_counts)),
                "node_fraction_in_threads_length_at_least_3": float(
                    np.sum(node_counts[node_counts >= 3]) / float(static_node_count)
                ),
                "node_fraction_in_threads_length_at_least_5": float(
                    np.sum(node_counts[node_counts >= 5]) / float(static_node_count)
                ),
                "node_fraction_in_threads_length_at_least_10": float(
                    np.sum(node_counts[node_counts >= 10]) / float(static_node_count)
                ),
            }
        )
    return rows


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(SCRIPT_PATH).lower() or "old_work" in str(OUTPUT_ROOT).lower():
        raise RuntimeError("forbidden old_work dependency")
    if not PROTOCOL_PATH.is_file():
        raise RuntimeError("missing pre-run dynamic evidence protocol")
    for path, expected in EXPECTED_HASHES.items():
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"hash mismatch {path}: expected {expected}, actual {actual}")

    audit = load_module("person_dynamic_candidate_audit", CANDIDATE_AUDIT_SCRIPT)
    p0 = load_module("person_dynamic_p0", P0_SCRIPT)
    p1e = load_module("person_dynamic_p1e", P1E_SCRIPT)
    p0.assert_workspace_scope()
    _, input_hash_checks = p0.load_contract_and_verify()
    explorer = audit.load_explorer()
    frame_map = {frame["sar_frame_uid"]: frame for frame in explorer["frames"]}

    candidate_table = pd.read_csv(CANDIDATES_CSV)
    candidate_table = candidate_table[candidate_table["run_id"] == RUN_ID].copy()
    if not candidate_table["generated_without_annotation"].astype(bool).all():
        raise RuntimeError("candidate provenance is not uniformly GT-blind")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Runtime stage: no manual reference file is loaded above this point.
    static_nodes, frame_context = build_static_nodes(
        audit, p0, p1e, frame_map, candidate_table
    )
    pairs = load_pair_records(frame_map)
    anchors = pd.read_csv(B0R_ANCHORS_CSV)
    (
        uncertainty,
        incoming,
        outgoing,
        edges,
        mutual_edges,
        pair_summary,
    ) = build_temporal_graph(p0, static_nodes, frame_context, pairs, anchors)
    dynamic_state = build_dynamic_state(static_nodes, incoming, outgoing)
    threads, thread_members, thread_mapping = build_threads(static_nodes, mutual_edges)
    dynamic_state = add_thread_mapping(dynamic_state, thread_mapping)

    static_nodes.to_csv(
        OUTPUT_DIR / "dynamic_candidate_nodes.csv", index=False, encoding="utf-8-sig"
    )
    uncertainty.to_csv(
        OUTPUT_DIR / "candidate_local_p0_uncertainty.csv",
        index=False,
        encoding="utf-8-sig",
    )
    incoming.to_csv(
        OUTPUT_DIR / "destination_incoming_temporal_evidence.csv",
        index=False,
        encoding="utf-8-sig",
    )
    outgoing.to_csv(
        OUTPUT_DIR / "source_outgoing_temporal_evidence.csv",
        index=False,
        encoding="utf-8-sig",
    )
    edges.to_csv(
        OUTPUT_DIR / "candidate_edges_within_3sigma.csv",
        index=False,
        encoding="utf-8-sig",
    )
    mutual_edges.to_csv(
        OUTPUT_DIR / "mutual_nearest_edges_2sigma.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pair_summary.to_csv(
        OUTPUT_DIR / "pair_condition_summary.csv", index=False, encoding="utf-8-sig"
    )
    dynamic_state.to_csv(
        OUTPUT_DIR / "dynamic_candidate_state.csv", index=False, encoding="utf-8-sig"
    )
    threads.to_csv(
        OUTPUT_DIR / "mutual_threads.csv", index=False, encoding="utf-8-sig"
    )
    thread_members.to_csv(
        OUTPUT_DIR / "mutual_thread_members.csv", index=False, encoding="utf-8-sig"
    )

    runtime_manifest = {
        "schema": "PERSON_P1E_DYNAMIC_EVIDENCE_RUNTIME_GRAPH_V1",
        "created_at": p0.now_iso(),
        "run_id": RUN_ID,
        "frame_count": int(static_nodes["frame_uid"].nunique()),
        "pair_count": int(len(pairs)),
        "static_node_count": int(len(static_nodes)),
        "conditions": list(CONDITIONS),
        "edge_count_within_3sigma": int(len(edges)),
        "mutual_edge_count": int(len(mutual_edges)),
        "manual_reference_loaded_during_runtime_graph": False,
        "physical_target_id_used": False,
        "interpolated_trajectory_used": False,
        "optical_track_used": False,
        "candidate_topk_truncation": None,
        "input_hash_checks": input_hash_checks,
        "frozen_hashes": {str(path): sha256_file(path) for path in EXPECTED_HASHES},
        "parameters": {
            "local_competitor_radius_m": LOCAL_COMPETITOR_RADIUS_M,
            "density_radii_m": [DENSITY_RADIUS_1_M, DENSITY_RADIUS_2_M],
            "structure_radius_m": STRUCTURE_RADIUS_M,
            "local_anchor_radius_px": LOCAL_ANCHOR_RADIUS_PX,
            "local_anchor_min_count": LOCAL_ANCHOR_MIN_COUNT,
            "uncertainty_floor_px": UNCERTAINTY_FLOOR_PX,
            "model_support_radius_m": MODEL_SUPPORT_RADIUS_M,
            "perturbation_tangential_m": PERTURBATION_TANGENTIAL_M,
            "shuffle_pair_shift": SHUFFLE_PAIR_SHIFT,
            "edge_export_max_sigma": EDGE_EXPORT_MAX_SIGMA,
            "thread_mutual_max_sigma": THREAD_MUTUAL_MAX_SIGMA,
        },
    }
    (OUTPUT_DIR / "runtime_graph_manifest.json").write_text(
        json.dumps(json_safe(runtime_manifest), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Offline evaluation stage begins only after all GT-blind runtime artifacts
    # above have been generated and written.
    references = pd.read_csv(REFERENCE_INTERPRETATION_CSV)
    offsets = pd.read_csv(FIXED_OFFSETS_CSV)
    reference_eval, offset_eval = evaluate_offline_points(
        dynamic_state, references, offsets
    )
    shared_transitions = build_shared_transitions(
        static_nodes, references, edges, mutual_edges
    )
    reference_eval.to_csv(
        OUTPUT_DIR / "offline_manual_reference_temporal_evaluation.csv",
        index=False,
        encoding="utf-8-sig",
    )
    offset_eval.to_csv(
        OUTPUT_DIR / "offline_fixed_offset_temporal_evaluation.csv",
        index=False,
        encoding="utf-8-sig",
    )
    shared_transitions.to_csv(
        OUTPUT_DIR / "offline_shared_state_transitions.csv",
        index=False,
        encoding="utf-8-sig",
    )

    summary = {
        "schema": "PERSON_P1E_DYNAMIC_EVIDENCE_TEMPORAL_INFORMATION_GAIN_V1",
        "created_at": p0.now_iso(),
        "status": "DYNAMIC_EVIDENCE_TEMPORAL_EXPLORATION_COMPLETE",
        "research_gate_used": False,
        "runtime_manifest": runtime_manifest,
        "reference_summaries": summarize_reference_evaluation(reference_eval),
        "correct_vs_control": compare_correct_to_controls(reference_eval),
        "thread_summaries": summarize_threads(threads, len(static_nodes)),
        "shared_transition_counts": [
            {
                "group": group,
                "condition": condition,
                "graph_mode": graph_mode,
                "reachable_state_counts": dict(
                    sorted(Counter(rows["reachable_state"]).items())
                ),
                "transition_count": int(len(rows)),
                "median_peak_reachable_candidate_count": float(
                    rows["peak_reachable_candidate_count"].median()
                ),
            }
            for (group, condition, graph_mode), rows in shared_transitions.groupby(
                ["group", "condition", "graph_mode"]
            )
        ],
        "semantic_boundaries": {
            "P0_is_platform_trajectory": False,
            "pseudocolor_brightness_is_intrinsic_person_RCS": False,
            "manual_reference_used_for_node_generation": False,
            "manual_reference_used_for_edge_generation": False,
            "physical_target_id_used_for_graph": False,
            "interpolated_trajectory_used_for_graph": False,
            "optical_used_for_graph": False,
            "P0_retuned": False,
            "existing_candidate_outputs_modified": False,
            "P1_PASS_claimed": False,
            "blind_validation_claimed": False,
        },
    }
    (OUTPUT_DIR / "temporal_information_gain_summary.json").write_text(
        json.dumps(json_safe(summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": summary["status"],
                "static_nodes": len(static_nodes),
                "edges_within_3sigma": len(edges),
                "threads": len(threads),
                "reference_evaluation_rows": len(reference_eval),
                "output": str(OUTPUT_DIR),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
