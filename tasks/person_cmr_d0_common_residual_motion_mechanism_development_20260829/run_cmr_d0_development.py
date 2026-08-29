from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw


SCRIPT = Path(__file__).resolve()
TASK_DIR = SCRIPT.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OUTPUT = STUDY / "cmr_d0_common_residual_motion_mechanism_development"
LOG = WORKSPACE / "logs" / "20260829_person_cmr_d0_common_residual_motion_mechanism_development.md"

OPTICAL = WORKSPACE / "output" / "person_optical_guided_sar_annotation_full_20260823" / "optical_person_frame_hypotheses.parquet"
V2 = STUDY / "m0b1_v2_cross_modal_direction_discrimination"
V2_ATLAS_PAIRS = V2 / "optical_direction_diversity_atlas_pairs_pre_reference.parquet"
V2_ATLAS_CANDIDATES = V2 / "optical_direction_diversity_atlas_future_candidate_windows_pre_reference.csv"
REGION_ROOT = STUDY / "p1e_sar_only_response_interface" / "runtime_track_response_region_minimal_v1"
REGION_TABLE = REGION_ROOT / "response_region_table_pre_reference.csv"
REGION_MASKS = REGION_ROOT / "response_region_masks"
TOPOLOGY_ROOT = STUDY / "p1e_sar_only_response_interface" / "shell_uncertainty_region_topology_v1"
SHELL_DECOMP = TOPOLOGY_ROOT / "optical_shell_uncertainty_decomposition_pre_reference.csv"
TOPOLOGY_EDGES = TOPOLOGY_ROOT / "gt_blind_shell_region_pixel_edges_pre_reference.csv"
P0_ROOT = STUDY / "p0_common_apparent_motion"
P0_COMP = P0_ROOT / "comparability_registry.csv"
P0_METRICS = P0_ROOT / "common_motion_pair_metrics.csv"
P0_MODELS = P0_ROOT / "model_parameters_per_pair.jsonl"
B0R = STUDY / "p1e_sar_only_response_interface" / "b0r_minimal"
B0R_COMP = B0R / "b0r_pair_comparability_R02_R03.csv"
B0R_METRICS = B0R / "b0r_pair_metrics_R02_R03.csv"
B0R_MODELS = B0R / "b0r_model_parameters_R02_R03.jsonl"
OFFLINE_ASSIGNMENT = REGION_ROOT / "offline_one_to_one_track_reference_assignment.csv"
OPTICAL_PROVENANCE = REGION_ROOT / "optical_track_interface_provenance.csv"

SAR_IMAGE_ROOT = WORKSPACE / "output" / "pseudocolor_labelstudio_prep_20260722" / "frames" / "sar_pseudocolor"

DEVELOPMENT_RUNS = ("R01ZF", "R02ZF", "R03ZF")
CONFIRMATION_RUNS = ("R04ZF",)
SLOPE_DEG_PER_PX = 0.02666536443690682
INTERCEPT_DEG = -45.502258572693094
GMC_SCALE = 0.25
NUMERICAL_TOL = 1e-12


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "||".join(str(x) for x in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20].upper()}"


def markdown_table(frame: pd.DataFrame) -> str:
    columns = [str(x) for x in frame.columns]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().map({"true": True, "false": False}).fillna(False)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def image_path_for_observation(row: pd.Series) -> Path:
    path = Path(str(row["optical_image_path"]))
    if path.exists():
        return path
    fallback = (
        WORKSPACE
        / "output"
        / "pseudocolor_labelstudio_prep_20260722"
        / "frames"
        / "optical"
        / str(row["run_id"])
        / f"frame_{int(row['frame_index']):06d}_t{int(row['timestamp_ms']):06d}ms.jpg"
    )
    return fallback


def load_authorities() -> dict[str, Any]:
    optical = pd.read_parquet(OPTICAL)
    optical = optical[optical["box_source"].astype(str).eq("DETECTED")].copy()
    optical["frame_index"] = optical["frame_index"].astype(int)
    optical["timestamp_ms"] = optical["timestamp_ms"].astype(int)

    shell = pd.read_csv(SHELL_DECOMP)
    shell = shell[(shell["temporal_policy"] == "SAME_FRAME") & (shell["guard_variant"] == "CURRENT_G6")].copy()
    shell = shell.drop_duplicates(["run_id", "frame_index"])

    regions = pd.read_csv(REGION_TABLE)
    regions = regions[regions["percentile_tag"] == "Q095"].copy()
    regions["frame_index"] = regions["frame_index"].astype(int)

    topology = pd.read_csv(TOPOLOGY_EDGES)
    topology = topology[
        (topology["temporal_policy"] == "SAME_FRAME")
        & (topology["guard_variant"] == "CURRENT_G6")
        & (topology["percentile_tag"] == "Q095")
    ].copy()
    topology["frame_index"] = topology["frame_index"].astype(int)

    comp = pd.concat([pd.read_csv(P0_COMP), pd.read_csv(B0R_COMP)], ignore_index=True)
    comp["comparable"] = bool_series(comp["comparable"])
    comp["scheduled"] = bool_series(comp["scheduled"])
    comp = comp[(comp["lag"] == 1) & comp["scheduled"] & comp["comparable"]].copy()

    metrics = pd.concat([pd.read_csv(P0_METRICS), pd.read_csv(B0R_METRICS)], ignore_index=True)
    metrics["is_selected_frozen_model"] = bool_series(metrics["is_selected_frozen_model"])
    metrics = metrics[(metrics["lag"] == 1) & metrics["is_selected_frozen_model"]].copy()

    model_rows = load_jsonl(P0_MODELS) + load_jsonl(B0R_MODELS)
    models = {
        (str(row["run_id"]), int(row["from_frame"]), int(row["to_frame"])): row["model_state"]
        for row in model_rows
        if int(row["lag"]) == 1 and str(row["model"]) == "M1" and bool(row["model_available"])
    }
    return {
        "optical": optical,
        "shell": shell,
        "regions": regions,
        "topology": topology,
        "comparability": comp,
        "metrics": metrics,
        "models": models,
    }


def build_eligible_atlas(data: dict[str, Any]) -> pd.DataFrame:
    optical = data["optical"]
    shell = data["shell"]
    regions = data["regions"]
    topology = data["topology"]
    comp = data["comparability"]
    models = data["models"]

    time_map = optical[["run_id", "frame_index", "timestamp_ms"]].drop_duplicates()
    shell = shell.merge(
        time_map.rename(columns={"frame_index": "optical_frame_index", "timestamp_ms": "nominal_optical_timestamp_ms"}),
        on=["run_id", "nominal_optical_timestamp_ms"],
        how="left",
    )
    shell_map = shell.set_index(["run_id", "frame_index"])
    region_counts = regions.groupby(["run_id", "frame_index"]).size().to_dict()
    topology_tracks = topology.groupby(["run_id", "frame_index"])["track_id"].agg(lambda x: set(x.astype(str))).to_dict()
    observation_tracks = optical.groupby(["run_id", "frame_index"])["raw_track_fragment_id"].agg(lambda x: set(x.astype(str))).to_dict()

    rows: list[dict[str, Any]] = []
    for pair in comp.sort_values(["run_id", "from_frame", "to_frame"]).itertuples(index=False):
        key_a = (str(pair.run_id), int(pair.from_frame))
        key_b = (str(pair.run_id), int(pair.to_frame))
        source_opt = math.nan
        destination_opt = math.nan
        source_ts = math.nan
        destination_ts = math.nan
        if key_a in shell_map.index:
            entry = shell_map.loc[key_a]
            source_opt = float(entry["optical_frame_index"])
            source_ts = float(entry["nominal_optical_timestamp_ms"])
        if key_b in shell_map.index:
            entry = shell_map.loc[key_b]
            destination_opt = float(entry["optical_frame_index"])
            destination_ts = float(entry["nominal_optical_timestamp_ms"])
        source_has = np.isfinite(source_opt)
        destination_has = np.isfinite(destination_opt)
        source_tracks = observation_tracks.get((str(pair.run_id), int(source_opt)), set()) if source_has else set()
        destination_tracks = observation_tracks.get((str(pair.run_id), int(destination_opt)), set()) if destination_has else set()
        topo_source = topology_tracks.get(key_a, set())
        topo_destination = topology_tracks.get(key_b, set())
        common = sorted(source_tracks & destination_tracks & topo_source & topo_destination)
        source_q95 = int(region_counts.get(key_a, 0))
        destination_q95 = int(region_counts.get(key_b, 0))
        distinct = bool(source_has and destination_has and int(source_opt) != int(destination_opt))
        p0_available = (str(pair.run_id), int(pair.from_frame), int(pair.to_frame)) in models
        eligible = distinct and bool(common) and source_q95 > 0 and destination_q95 > 0 and p0_available
        if str(pair.run_id) in DEVELOPMENT_RUNS:
            pool = "DEVELOPMENT_POOL"
        elif str(pair.run_id) in CONFIRMATION_RUNS:
            pool = "CONFIRMATION_POOL"
        else:
            pool = "CROSS_MODAL_OTHER"
        rows.append(
            {
                "window_id": stable_id("CMRW", pair.run_id, pair.from_frame, pair.to_frame),
                "run_id": str(pair.run_id),
                "source_sar_frame": int(pair.from_frame),
                "destination_sar_frame": int(pair.to_frame),
                "source_optical_frame": int(source_opt) if source_has else pd.NA,
                "destination_optical_frame": int(destination_opt) if destination_has else pd.NA,
                "source_optical_timestamp_ms": int(source_ts) if np.isfinite(source_ts) else pd.NA,
                "destination_optical_timestamp_ms": int(destination_ts) if np.isfinite(destination_ts) else pd.NA,
                "distinct_optical_samples": distinct,
                "runtime_common_fragment_count": len(common),
                "runtime_common_fragments": ";".join(common),
                "source_q95_region_count": source_q95,
                "destination_q95_region_count": destination_q95,
                "p0_pair_comparable": True,
                "p0_model_available": p0_available,
                "static_pixel_topology_available": bool(topo_source and topo_destination),
                "cross_modal_eligible": eligible,
                "pool": pool,
                "reference_used": False,
                "manual_outcome_used_for_split": False,
            }
        )
    atlas = pd.DataFrame(rows)

    candidates = pd.read_csv(V2_ATLAS_CANDIDATES)
    diagnostic_runs = sorted(set(candidates["run_id"].astype(str)) - set(atlas["run_id"].astype(str)))
    diagnostic_rows = (
        candidates[candidates["run_id"].astype(str).isin(diagnostic_runs)]
        .groupby("run_id")
        .agg(
            optical_diversity_candidate_windows=("future_window_eligible", "size"),
            min_frame=("source_frame_index", "min"),
            max_frame=("destination_frame_index", "max"),
        )
        .reset_index()
    )
    diagnostic_rows["pool"] = "DIAGNOSTIC_POOL_OPTICAL_ONLY"
    diagnostic_rows["cross_modal_eligible"] = False
    diagnostic_rows["reason"] = "OPPOSITE_DIRECTION_OPTICAL_WINDOW_WITHOUT_COMPLETE_FROZEN_P0_TOPOLOGY_COVERAGE"

    OUTPUT.mkdir(parents=True, exist_ok=True)
    atlas.to_parquet(OUTPUT / "cmr_eligible_window_atlas.parquet", index=False, compression="zstd")
    atlas.to_csv(OUTPUT / "cmr_eligible_window_atlas.csv", index=False, encoding="utf-8-sig")
    diagnostic_rows.to_csv(OUTPUT / "cmr_optical_only_diagnostic_runs.csv", index=False, encoding="utf-8-sig")

    split_summary = (
        atlas.groupby(["pool", "run_id"])
        .agg(
            scheduled_lag1_pairs=("window_id", "size"),
            cross_modal_eligible_windows=("cross_modal_eligible", "sum"),
            eligible_branch_instances=("runtime_common_fragment_count", lambda x: int(x[atlas.loc[x.index, "cross_modal_eligible"]].sum())),
        )
        .reset_index()
    )
    split_summary.to_csv(OUTPUT / "cmr_run_split_summary.csv", index=False, encoding="utf-8-sig")
    split_payload = {
        "schema": "PERSON_CMR_D0_RUN_SPLIT_V1",
        "created_at": now_iso(),
        "starting_head": git_head(),
        "development_runs": list(DEVELOPMENT_RUNS),
        "confirmation_runs": list(CONFIRMATION_RUNS),
        "diagnostic_runs": diagnostic_rows["run_id"].astype(str).tolist(),
        "split_basis": "RUN_ID_PLUS_GT_BLIND_FROZEN_INPUT_AVAILABILITY",
        "manual_reference_used": False,
        "future_method_performance_used": False,
        "same_run_cross_pool_leakage": False,
        "confirmation_outcome_accessed": False,
        "atlas_sha256": sha256_file(OUTPUT / "cmr_eligible_window_atlas.parquet"),
        "summary": split_summary.to_dict("records"),
    }
    write_json(OUTPUT / "cmr_run_split.json", split_payload)
    split_md = [
        "# CMR run split frozen before development",
        "",
        "- State: `FROZEN_BEFORE_DEVELOPMENT`",
        f"- Frozen at HEAD: `{git_head()}`",
        "- Split basis: run identity plus GT-blind frozen input availability.",
        "- Manual reference outcome used: `NO`.",
        "- Future CMR performance used: `NO`.",
        "- Same-run cross-pool leakage: `NO`.",
        "",
        "## Pools",
        "",
        "- Development: R01ZF, R02ZF, R03ZF.",
        "- Confirmation: R04ZF; only input availability may be inspected before CMR-v0 freeze.",
        "- Diagnostic: optical opposite-direction candidate runs lacking complete frozen cross-modal P0/topology coverage.",
        "",
        "## Deterministic accounting",
        "",
        markdown_table(split_summary),
        "",
        "The confirmation pool is not used for common-motion estimation, residual calculation, method selection, real-case selection, or development reporting.",
    ]
    (OUTPUT / "CMR_RUN_SPLIT_FROZEN_BEFORE_DEVELOPMENT.md").write_text("\n".join(split_md) + "\n", encoding="utf-8")
    return atlas


def detection_mask(shape: tuple[int, int], rows: pd.DataFrame, scale: float) -> np.ndarray:
    h, w = shape
    mask = np.full((h, w), 255, dtype=np.uint8)
    for row in rows.to_dict("records"):
        x1, y1, x2, y2 = [float(row[k]) * scale for k in ("bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2")]
        pad_x = max(4.0, 0.12 * (x2 - x1))
        pad_y = max(4.0, 0.12 * (y2 - y1))
        cv2.rectangle(
            mask,
            (max(0, int(math.floor(x1 - pad_x))), max(0, int(math.floor(y1 - pad_y)))),
            (min(w - 1, int(math.ceil(x2 + pad_x))), min(h - 1, int(math.ceil(y2 + pad_y)))),
            0,
            -1,
        )
    mask[int(h * 0.94) :, :] = 0
    return mask


def fit_background_gmc(source_path: Path, destination_path: Path, source_boxes: pd.DataFrame, destination_boxes: pd.DataFrame) -> dict[str, Any]:
    source = cv2.imread(str(source_path), cv2.IMREAD_GRAYSCALE)
    destination = cv2.imread(str(destination_path), cv2.IMREAD_GRAYSCALE)
    if source is None or destination is None:
        return {"background_gmc_state": "BACKGROUND_GMC_IMAGE_UNAVAILABLE"}
    source = cv2.resize(source, None, fx=GMC_SCALE, fy=GMC_SCALE, interpolation=cv2.INTER_AREA)
    destination = cv2.resize(destination, None, fx=GMC_SCALE, fy=GMC_SCALE, interpolation=cv2.INTER_AREA)
    source_mask = detection_mask(source.shape, source_boxes, GMC_SCALE)
    destination_mask = detection_mask(destination.shape, destination_boxes, GMC_SCALE)
    points = cv2.goodFeaturesToTrack(
        source,
        maxCorners=1600,
        qualityLevel=0.008,
        minDistance=7,
        blockSize=7,
        mask=source_mask,
    )
    if points is None or len(points) < 30:
        return {"background_gmc_state": "BACKGROUND_GMC_INSUFFICIENT_FEATURES", "detected_feature_count": 0 if points is None else len(points)}
    lk = dict(
        winSize=(31, 31),
        maxLevel=4,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01),
    )
    moved, sf, _ = cv2.calcOpticalFlowPyrLK(source, destination, points, None, **lk)
    back, sb, _ = cv2.calcOpticalFlowPyrLK(destination, source, moved, None, **lk) if moved is not None else (None, None, None)
    if moved is None or back is None or sf is None or sb is None:
        return {"background_gmc_state": "BACKGROUND_GMC_FLOW_UNAVAILABLE", "detected_feature_count": len(points)}
    p0 = points.reshape(-1, 2)
    p1 = moved.reshape(-1, 2)
    pback = back.reshape(-1, 2)
    status = sf.reshape(-1).astype(bool) & sb.reshape(-1).astype(bool)
    finite = np.isfinite(p0).all(1) & np.isfinite(p1).all(1) & np.isfinite(pback).all(1)
    fb = np.linalg.norm(pback - p0, axis=1)
    h, w = source.shape
    end = np.rint(p1).astype(int)
    inside = (end[:, 0] >= 0) & (end[:, 0] < w) & (end[:, 1] >= 0) & (end[:, 1] < h)
    dest_ok = np.zeros(len(p0), dtype=bool)
    idx = np.flatnonzero(inside)
    dest_ok[idx] = destination_mask[end[idx, 1], end[idx, 0]] > 0
    keep = status & finite & inside & dest_ok & (fb <= 1.5)
    p0 = p0[keep]
    p1 = p1[keep]
    fb = fb[keep]
    if len(p0) < 24:
        return {
            "background_gmc_state": "BACKGROUND_GMC_INSUFFICIENT_VALID_TRACKS",
            "detected_feature_count": len(points),
            "valid_track_count": len(p0),
        }
    cells = np.floor(p0 / 48.0).astype(int)
    holdout = ((cells[:, 0] + 2 * cells[:, 1]) % 4) == 0
    if int((~holdout).sum()) < 18 or int(holdout.sum()) < 6:
        order = np.arange(len(p0))
        holdout = (order % 5) == 0
    affine, inliers = cv2.estimateAffinePartial2D(
        p0[~holdout],
        p1[~holdout],
        method=cv2.RANSAC,
        ransacReprojThreshold=2.5,
        maxIters=2500,
        confidence=0.995,
        refineIters=10,
    )
    if affine is None or not np.isfinite(affine).all():
        return {"background_gmc_state": "BACKGROUND_GMC_AFFINE_FIT_FAILED", "valid_track_count": len(p0)}
    scale_est = math.sqrt(float(affine[0, 0]) ** 2 + float(affine[0, 1]) ** 2)
    if not 0.94 <= scale_est <= 1.06:
        return {
            "background_gmc_state": "BACKGROUND_GMC_IMPLAUSIBLE_SCALE",
            "valid_track_count": len(p0),
            "scale_estimate": scale_est,
        }
    pred = p0[holdout] @ affine[:, :2].T + affine[:, 2]
    residual = p1[holdout] - pred
    abs_x = np.abs(residual[:, 0])
    abs_norm = np.linalg.norm(residual, axis=1)
    affine_full = affine.astype(float).copy()
    affine_full[:, 2] /= GMC_SCALE
    inlier_count = int(inliers.sum()) if inliers is not None else 0
    return {
        "background_gmc_state": "BACKGROUND_GMC_AVAILABLE",
        "detected_feature_count": len(points),
        "valid_track_count": len(p0),
        "fit_track_count": int((~holdout).sum()),
        "holdout_track_count": int(holdout.sum()),
        "fit_inlier_count": inlier_count,
        "fit_inlier_fraction": inlier_count / max(1, int((~holdout).sum())),
        "holdout_residual_x_median_px": float(np.median(abs_x) / GMC_SCALE),
        "holdout_residual_x_p90_px": float(np.quantile(abs_x, 0.9) / GMC_SCALE),
        "holdout_residual_norm_p90_px": float(np.quantile(abs_norm, 0.9) / GMC_SCALE),
        "forward_backward_error_median_px": float(np.median(fb) / GMC_SCALE),
        "scale_estimate": scale_est,
        "affine_00": float(affine_full[0, 0]),
        "affine_01": float(affine_full[0, 1]),
        "affine_02": float(affine_full[0, 2]),
        "affine_10": float(affine_full[1, 0]),
        "affine_11": float(affine_full[1, 1]),
        "affine_12": float(affine_full[1, 2]),
    }


def apply_affine_to_box(row: pd.Series, common: pd.Series) -> tuple[float, float, float, float]:
    matrix = np.asarray(
        [
            [common.affine_00, common.affine_01, common.affine_02],
            [common.affine_10, common.affine_11, common.affine_12],
        ],
        dtype=float,
    )
    corners = np.asarray(
        [
            [row.bbox_x1, row.bbox_y1, 1.0],
            [row.bbox_x2, row.bbox_y1, 1.0],
            [row.bbox_x2, row.bbox_y2, 1.0],
            [row.bbox_x1, row.bbox_y2, 1.0],
        ],
        dtype=float,
    )
    warped = corners @ matrix.T
    return float(warped[:, 0].min()), float(warped[:, 1].min()), float(warped[:, 0].max()), float(warped[:, 1].max())


def residual_state(left_low: float, left_high: float, right_low: float, right_high: float, prefix: str) -> str:
    if not all(np.isfinite([left_low, left_high, right_low, right_high])):
        return f"{prefix}_UNAVAILABLE"
    if left_low > NUMERICAL_TOL and right_low > NUMERICAL_TOL:
        return f"{prefix}_ABOVE_COMMON"
    if left_high < -NUMERICAL_TOL and right_high < -NUMERICAL_TOL:
        return f"{prefix}_BELOW_COMMON"
    if left_low <= 0 <= left_high and right_low <= 0 <= right_high:
        return f"{prefix}_COMMON_COMPATIBLE"
    return f"{prefix}_DEFORMATION_OR_MIXED"


def develop_optical_common_and_residual(atlas: pd.DataFrame, data: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    optical = data["optical"]
    windows = atlas[(atlas["pool"] == "DEVELOPMENT_POOL") & atlas["cross_modal_eligible"]].copy()
    common_rows: list[dict[str, Any]] = []
    residual_rows: list[dict[str, Any]] = []

    for window in windows.itertuples(index=False):
        source = optical[(optical["run_id"] == window.run_id) & (optical["frame_index"] == int(window.source_optical_frame))]
        destination = optical[(optical["run_id"] == window.run_id) & (optical["frame_index"] == int(window.destination_optical_frame))]
        common_fragments = str(window.runtime_common_fragments).split(";") if str(window.runtime_common_fragments) else []
        source_path = image_path_for_observation(source.iloc[0]) if len(source) else Path("MISSING")
        destination_path = image_path_for_observation(destination.iloc[0]) if len(destination) else Path("MISSING")
        gmc = fit_background_gmc(source_path, destination_path, source, destination)

        branch_observed: list[dict[str, Any]] = []
        for fragment in common_fragments:
            a = source[source["raw_track_fragment_id"].astype(str) == fragment]
            b = destination[destination["raw_track_fragment_id"].astype(str) == fragment]
            if len(a) != 1 or len(b) != 1:
                continue
            arow = a.iloc[0]
            brow = b.iloc[0]
            d_left = (float(brow.bbox_x1) - float(arow.bbox_x1)) * SLOPE_DEG_PER_PX
            d_right = (float(brow.bbox_x2) - float(arow.bbox_x2)) * SLOPE_DEG_PER_PX
            d_mid = 0.5 * (d_left + d_right)
            d_width = ((float(brow.bbox_x2) - float(brow.bbox_x1)) - (float(arow.bbox_x2) - float(arow.bbox_x1))) * SLOPE_DEG_PER_PX
            branch_observed.append(
                {
                    "raw_track_fragment_id": fragment,
                    "source": arow,
                    "destination": brow,
                    "d_left_observed_deg": d_left,
                    "d_right_observed_deg": d_right,
                    "d_mid_observed_deg": d_mid,
                    "d_width_observed_deg": d_width,
                }
            )

        mids = np.asarray([x["d_mid_observed_deg"] for x in branch_observed], dtype=float)
        lefts = np.asarray([x["d_left_observed_deg"] for x in branch_observed], dtype=float)
        rights = np.asarray([x["d_right_observed_deg"] for x in branch_observed], dtype=float)
        if len(mids) >= 2:
            consensus_mid = float(np.median(mids))
            consensus_left = float(np.median(lefts))
            consensus_right = float(np.median(rights))
            mad = float(np.median(np.abs(mids - consensus_mid)))
            consensus_unc = max(NUMERICAL_TOL, 1.4826 * mad)
            consensus_state = "BRANCH_CONSENSUS_AVAILABLE"
        else:
            consensus_mid = consensus_left = consensus_right = consensus_unc = math.nan
            consensus_state = "BRANCH_CONSENSUS_UNAVAILABLE_SINGLE_BRANCH"

        common_row = {
            "window_id": window.window_id,
            "run_id": window.run_id,
            "source_sar_frame": int(window.source_sar_frame),
            "destination_sar_frame": int(window.destination_sar_frame),
            "source_optical_frame": int(window.source_optical_frame),
            "destination_optical_frame": int(window.destination_optical_frame),
            "source_optical_path": str(source_path),
            "destination_optical_path": str(destination_path),
            "active_branch_count": len(branch_observed),
            "branch_consensus_state": consensus_state,
            "branch_consensus_left_deg": consensus_left,
            "branch_consensus_right_deg": consensus_right,
            "branch_consensus_mid_deg": consensus_mid,
            "branch_consensus_uncertainty_deg": consensus_unc,
            **gmc,
            "reference_used": False,
            "confirmation_pool_accessed": False,
        }
        if gmc.get("background_gmc_state") == "BACKGROUND_GMC_AVAILABLE":
            common_row["background_uncertainty_deg"] = max(NUMERICAL_TOL, float(gmc["holdout_residual_x_p90_px"]) * SLOPE_DEG_PER_PX)
            # At this point a location-specific prediction is retained for each branch.
            if np.isfinite(consensus_mid):
                # Window-level GMC midpoint is the median branch-location prediction.
                predicted = []
                temp_series = pd.Series(common_row)
                for item in branch_observed:
                    x1p, _, x2p, _ = apply_affine_to_box(item["source"], temp_series)
                    gleft = (x1p - float(item["source"].bbox_x1)) * SLOPE_DEG_PER_PX
                    gright = (x2p - float(item["source"].bbox_x2)) * SLOPE_DEG_PER_PX
                    predicted.append(0.5 * (gleft + gright))
                gmc_mid = float(np.median(predicted))
                common_row["background_common_mid_deg_at_branches"] = gmc_mid
                bg_unc = float(common_row["background_uncertainty_deg"])
                lo_bg, hi_bg = gmc_mid - bg_unc, gmc_mid + bg_unc
                lo_bc, hi_bc = consensus_mid - consensus_unc, consensus_mid + consensus_unc
                gap = max(0.0, max(lo_bg, lo_bc) - min(hi_bg, hi_bc))
                if max(lo_bg, lo_bc) <= min(hi_bg, hi_bc):
                    hybrid = "COMMON_ESTIMATORS_AGREE"
                elif gap <= max(bg_unc, consensus_unc):
                    hybrid = "COMMON_ESTIMATORS_MILD_DISAGREEMENT"
                else:
                    hybrid = "COMMON_ESTIMATORS_STRONG_DISAGREEMENT"
                common_row["common_estimator_gap_deg"] = gap
                common_row["hybrid_common_state"] = hybrid
            else:
                common_row["background_common_mid_deg_at_branches"] = math.nan
                common_row["common_estimator_gap_deg"] = math.nan
                common_row["hybrid_common_state"] = "BACKGROUND_ONLY_AVAILABLE"
        else:
            common_row["background_uncertainty_deg"] = math.nan
            common_row["background_common_mid_deg_at_branches"] = math.nan
            common_row["common_estimator_gap_deg"] = math.nan
            common_row["hybrid_common_state"] = (
                "BRANCH_CONSENSUS_ONLY_AVAILABLE" if np.isfinite(consensus_mid) else "COMMON_MOTION_UNAVAILABLE"
            )
        common_rows.append(common_row)

        common_series = pd.Series(common_row)
        for item in branch_observed:
            base = {
                "window_id": window.window_id,
                "run_id": window.run_id,
                "source_sar_frame": int(window.source_sar_frame),
                "destination_sar_frame": int(window.destination_sar_frame),
                "source_optical_frame": int(window.source_optical_frame),
                "destination_optical_frame": int(window.destination_optical_frame),
                "raw_track_fragment_id": item["raw_track_fragment_id"],
                "d_left_observed_deg": item["d_left_observed_deg"],
                "d_right_observed_deg": item["d_right_observed_deg"],
                "d_mid_observed_deg": item["d_mid_observed_deg"],
                "d_width_observed_deg": item["d_width_observed_deg"],
                "background_gmc_state": common_row["background_gmc_state"],
                "hybrid_common_state": common_row["hybrid_common_state"],
                "reference_used": False,
            }
            if common_row["background_gmc_state"] != "BACKGROUND_GMC_AVAILABLE":
                base.update(
                    {
                        "d_left_common_deg": math.nan,
                        "d_right_common_deg": math.nan,
                        "d_mid_common_deg": math.nan,
                        "common_uncertainty_deg": math.nan,
                        "residual_left_low_deg": math.nan,
                        "residual_left_high_deg": math.nan,
                        "residual_right_low_deg": math.nan,
                        "residual_right_high_deg": math.nan,
                        "residual_mid_descriptor_deg": math.nan,
                        "optical_residual_state": "OPTICAL_RESIDUAL_COMMON_UNAVAILABLE",
                    }
                )
            else:
                x1p, _, x2p, _ = apply_affine_to_box(item["source"], common_series)
                gleft = (x1p - float(item["source"].bbox_x1)) * SLOPE_DEG_PER_PX
                gright = (x2p - float(item["source"].bbox_x2)) * SLOPE_DEG_PER_PX
                gmid = 0.5 * (gleft + gright)
                unc = float(common_row["background_uncertainty_deg"])
                ll = item["d_left_observed_deg"] - (gleft + unc)
                lh = item["d_left_observed_deg"] - (gleft - unc)
                rl = item["d_right_observed_deg"] - (gright + unc)
                rh = item["d_right_observed_deg"] - (gright - unc)
                if common_row["hybrid_common_state"] == "COMMON_ESTIMATORS_STRONG_DISAGREEMENT":
                    state = "OPTICAL_RESIDUAL_COMMON_ESTIMATE_AMBIGUOUS"
                else:
                    state = residual_state(ll, lh, rl, rh, "OPTICAL_RESIDUAL")
                base.update(
                    {
                        "d_left_common_deg": gleft,
                        "d_right_common_deg": gright,
                        "d_mid_common_deg": gmid,
                        "common_uncertainty_deg": unc,
                        "residual_left_low_deg": ll,
                        "residual_left_high_deg": lh,
                        "residual_right_low_deg": rl,
                        "residual_right_high_deg": rh,
                        "residual_mid_descriptor_deg": item["d_mid_observed_deg"] - gmid,
                        "optical_residual_state": state,
                    }
                )
            residual_rows.append(base)

    common = pd.DataFrame(common_rows)
    residual = pd.DataFrame(residual_rows)
    common.to_parquet(OUTPUT / "optical_common_motion_development.parquet", index=False, compression="zstd")
    common.to_csv(OUTPUT / "optical_common_motion_development.csv", index=False, encoding="utf-8-sig")
    residual.to_parquet(OUTPUT / "optical_branch_residual_development.parquet", index=False, compression="zstd")
    residual.to_csv(OUTPUT / "optical_branch_residual_development.csv", index=False, encoding="utf-8-sig")
    return common, residual


def region_label(region_id: str) -> int:
    return int(str(region_id).rsplit("R", 1)[-1])


def theta_grid(shape: tuple[int, int]) -> np.ndarray:
    # Frozen geometry authority.
    cx = 511.74532586922845
    cy = 590.7763512520755
    yy, xx = np.indices(shape, dtype=float)
    return np.degrees(np.arctan2(xx - cx, cy - yy))


def angular_uncertainty_from_pixel(center_x: float, center_y: float, residual_px: float) -> float:
    if not np.isfinite(residual_px):
        return math.nan
    cx = 511.74532586922845
    cy = 590.7763512520755
    base = math.degrees(math.atan2(center_x - cx, cy - center_y))
    candidates = [
        math.degrees(math.atan2(center_x + residual_px - cx, cy - center_y)),
        math.degrees(math.atan2(center_x - residual_px - cx, cy - center_y)),
        math.degrees(math.atan2(center_x - cx, cy - (center_y + residual_px))),
        math.degrees(math.atan2(center_x - cx, cy - (center_y - residual_px))),
    ]
    return max(NUMERICAL_TOL, max(abs(v - base) for v in candidates))


def p0_matrix(model: dict[str, Any]) -> np.ndarray:
    name = str(model["model"])
    if name == "M1":
        dx, dy = model["parameters"]["translation_xy"]
        return np.asarray([[1.0, 0.0, float(dx)], [0.0, 1.0, float(dy)]], dtype=np.float32)
    if name == "M2":
        return np.asarray(model["parameters"]["affine_2x3"], dtype=np.float32)
    raise ValueError(f"unsupported frozen P0 model {name}")


def build_static_hypotheses(atlas: pd.DataFrame, data: dict[str, Any], optical_residual: pd.DataFrame) -> pd.DataFrame:
    topology = data["topology"]
    eligible = atlas[(atlas["pool"] == "DEVELOPMENT_POOL") & atlas["cross_modal_eligible"]]
    rows: list[dict[str, Any]] = []
    for window in eligible.itertuples(index=False):
        fragments = str(window.runtime_common_fragments).split(";")
        for fragment in fragments:
            source_regions = sorted(
                topology[
                    (topology["run_id"] == window.run_id)
                    & (topology["frame_index"] == int(window.source_sar_frame))
                    & (topology["track_id"].astype(str) == fragment)
                ]["region_id"].astype(str).unique()
            )
            destination_regions = sorted(
                topology[
                    (topology["run_id"] == window.run_id)
                    & (topology["frame_index"] == int(window.destination_sar_frame))
                    & (topology["track_id"].astype(str) == fragment)
                ]["region_id"].astype(str).unique()
            )
            for source_region in source_regions:
                for destination_region in destination_regions:
                    rows.append(
                        {
                            "hypothesis_id": stable_id("CMRH", window.window_id, fragment, source_region, destination_region),
                            "window_id": window.window_id,
                            "run_id": window.run_id,
                            "source_sar_frame": int(window.source_sar_frame),
                            "destination_sar_frame": int(window.destination_sar_frame),
                            "source_optical_frame": int(window.source_optical_frame),
                            "destination_optical_frame": int(window.destination_optical_frame),
                            "raw_track_fragment_id": fragment,
                            "source_region_id": source_region,
                            "destination_region_id": destination_region,
                            "static_pixel_shell_region_feasible": True,
                            "reference_used": False,
                        }
                    )
    frame = pd.DataFrame(rows)
    frame = frame.merge(
        optical_residual,
        on=[
            "window_id",
            "run_id",
            "source_sar_frame",
            "destination_sar_frame",
            "source_optical_frame",
            "destination_optical_frame",
            "raw_track_fragment_id",
        ],
        how="left",
        validate="many_to_one",
    )
    frame.to_parquet(OUTPUT / "static_cross_modal_hypotheses_development.parquet", index=False, compression="zstd")
    return frame


def develop_sar_p0_residual(hypotheses: pd.DataFrame, data: dict[str, Any]) -> pd.DataFrame:
    regions = data["regions"].set_index("region_id", drop=False)
    models = data["models"]
    metrics = data["metrics"].set_index(["run_id", "from_frame", "to_frame"])
    unique_edges = hypotheses[
        ["run_id", "source_sar_frame", "destination_sar_frame", "source_region_id", "destination_region_id"]
    ].drop_duplicates()
    rows: list[dict[str, Any]] = []
    cache: dict[str, dict[str, np.ndarray]] = {}
    theta_cache: dict[tuple[int, int], np.ndarray] = {}
    warp_cache: dict[tuple[str, int, int, str], dict[str, Any]] = {}

    for edge in unique_edges.itertuples(index=False):
        pair_key = (str(edge.run_id), int(edge.source_sar_frame), int(edge.destination_sar_frame))
        source_row = regions.loc[str(edge.source_region_id)]
        destination_row = regions.loc[str(edge.destination_region_id)]
        source_uid = str(source_row.frame_uid)
        destination_uid = str(destination_row.frame_uid)
        if destination_uid not in cache:
            cache[destination_uid] = dict(np.load(REGION_MASKS / f"{destination_uid}.npz"))
        destination_labels = cache[destination_uid]["Q095"]
        destination_mask = destination_labels == region_label(str(edge.destination_region_id))
        model = models.get(pair_key)
        if model is None:
            rows.append({
                **edge._asdict(),
                "sar_p0_residual_state": "SAR_P0_RESIDUAL_TRANSPORT_UNAVAILABLE",
                "reference_used": False,
            })
            continue
        source_cache_key = (*pair_key, str(edge.source_region_id))
        if source_cache_key not in warp_cache:
            if source_uid not in cache:
                cache[source_uid] = dict(np.load(REGION_MASKS / f"{source_uid}.npz"))
            source_labels = cache[source_uid]["Q095"]
            source_mask = source_labels == region_label(str(edge.source_region_id))
            matrix = p0_matrix(model)
            height, width = source_mask.shape
            warped_source = cv2.warpAffine(
                source_mask.astype(np.float32),
                matrix,
                (width, height),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=0.0,
            )
            warped_source = np.clip(warped_source, 0.0, 1.0)
            support = warped_source >= 0.5
            if support.any():
                theta = theta_cache.setdefault(source_mask.shape, theta_grid(source_mask.shape))
                predicted_theta_low = float(theta[support].min())
                predicted_theta_high = float(theta[support].max())
                yy, xx = np.nonzero(support)
                predicted_center_x = float(np.mean(xx))
                predicted_center_y = float(np.mean(yy))
            else:
                predicted_theta_low = predicted_theta_high = predicted_center_x = predicted_center_y = math.nan
            metric = metrics.loc[pair_key]
            if isinstance(metric, pd.DataFrame):
                metric = metric.iloc[0]
            p0_residual_px = float(metric["holdout_residual_p90_px"])
            uncertainty_deg = angular_uncertainty_from_pixel(predicted_center_x, predicted_center_y, p0_residual_px)
            warp_cache[source_cache_key] = {
                "warped": warped_source,
                "source_total": float(source_mask.sum()),
                "warped_total": float(warped_source.sum()),
                "predicted_theta_low": predicted_theta_low,
                "predicted_theta_high": predicted_theta_high,
                "p0_residual_px": p0_residual_px,
                "uncertainty_deg": uncertainty_deg,
            }
        source_payload = warp_cache[source_cache_key]
        warped = source_payload["warped"]
        intersection = float((warped * destination_mask).sum())
        source_total = float(source_payload["source_total"])
        warped_total = float(source_payload["warped_total"])
        destination_total = float(destination_mask.sum())
        union = warped_total + destination_total - intersection
        retention = intersection / source_total if source_total > 0 else math.nan
        destination_explained = intersection / destination_total if destination_total > 0 else math.nan
        soft_iou = intersection / union if union > 0 else math.nan
        predicted_theta_low = float(source_payload["predicted_theta_low"])
        predicted_theta_high = float(source_payload["predicted_theta_high"])
        p0_residual_px = float(source_payload["p0_residual_px"])
        uncertainty_deg = float(source_payload["uncertainty_deg"])
        actual_low = float(destination_row.theta_min_deg)
        actual_high = float(destination_row.theta_max_deg)
        ll = actual_low - (predicted_theta_low + uncertainty_deg)
        lh = actual_low - (predicted_theta_low - uncertainty_deg)
        rl = actual_high - (predicted_theta_high + uncertainty_deg)
        rh = actual_high - (predicted_theta_high - uncertainty_deg)
        core_state = residual_state(ll, lh, rl, rh, "SAR_P0_RESIDUAL")
        boundary = bool(source_row.touches_observable_boundary) or bool(destination_row.touches_observable_boundary)
        truncated = bool(source_row.has_truncated_support) or bool(destination_row.has_truncated_support)
        observability = "SAR_BOUNDARY_CENSORED" if boundary or truncated else "SAR_RESIDUAL_FULLY_OBSERVABLE"
        rows.append(
            {
                **edge._asdict(),
                "p0_model": str(model["model"]),
                "p0_holdout_residual_p90_px": p0_residual_px,
                "p0_angular_uncertainty_deg": uncertainty_deg,
                "predicted_theta_low_deg": predicted_theta_low,
                "predicted_theta_high_deg": predicted_theta_high,
                "observed_theta_low_deg": actual_low,
                "observed_theta_high_deg": actual_high,
                "sar_residual_left_low_deg": ll,
                "sar_residual_left_high_deg": lh,
                "sar_residual_right_low_deg": rl,
                "sar_residual_right_high_deg": rh,
                "sar_residual_mid_descriptor_deg": 0.5 * ((actual_low + actual_high) - (predicted_theta_low + predicted_theta_high)),
                "sar_width_change_deg": (actual_high - actual_low) - (predicted_theta_high - predicted_theta_low),
                "sar_p0_residual_state_core": core_state,
                "sar_observability_state": observability,
                "sar_p0_residual_state": "SAR_P0_RESIDUAL_BOUNDARY_CENSORED" if observability == "SAR_BOUNDARY_CENSORED" else core_state,
                "soft_intersection_px": intersection,
                "source_total_retention": retention,
                "destination_explained_fraction": destination_explained,
                "soft_iou": soft_iou,
                "source_touches_boundary": bool(source_row.touches_observable_boundary),
                "destination_touches_boundary": bool(destination_row.touches_observable_boundary),
                "source_truncated": bool(source_row.has_truncated_support),
                "destination_truncated": bool(destination_row.has_truncated_support),
                "reference_used": False,
                "person_motion_claimed": False,
            }
        )
    sar = pd.DataFrame(rows)
    support_flag = sar["soft_intersection_px"].fillna(0) >= 1.0
    sar["p0_supported_destination_count"] = sar[support_flag].groupby(
        ["run_id", "source_sar_frame", "destination_sar_frame", "source_region_id"]
    )["destination_region_id"].transform("nunique")
    sar["p0_supported_source_count"] = sar[support_flag].groupby(
        ["run_id", "source_sar_frame", "destination_sar_frame", "destination_region_id"]
    )["source_region_id"].transform("nunique")
    sar["p0_supported_destination_count"] = sar["p0_supported_destination_count"].fillna(0).astype(int)
    sar["p0_supported_source_count"] = sar["p0_supported_source_count"].fillna(0).astype(int)
    sar["sar_topology_state"] = np.select(
        [
            (sar["p0_supported_destination_count"] > 1) & (sar["p0_supported_source_count"] > 1),
            sar["p0_supported_destination_count"] > 1,
            sar["p0_supported_source_count"] > 1,
        ],
        ["P0_SPLIT_AND_MERGE_LIKE", "P0_SPLIT_LIKE", "P0_MERGE_LIKE"],
        default="P0_ONE_TO_ONE_LIKE_OR_UNSUPPORTED",
    )
    sar.to_parquet(OUTPUT / "sar_p0_relative_residual_development.parquet", index=False, compression="zstd")
    sar.to_csv(OUTPUT / "sar_p0_relative_residual_development.csv", index=False, encoding="utf-8-sig")
    return sar


def cross_modal_relation(optical_state: str, sar_state: str) -> str:
    if "UNAVAILABLE" in optical_state or "UNAVAILABLE" in sar_state:
        return "RESIDUAL_UNAVAILABLE"
    if "AMBIGUOUS" in optical_state:
        return "RESIDUAL_COMMON_ESTIMATE_AMBIGUOUS"
    if "BOUNDARY_CENSORED" in sar_state or "DEFORMATION" in optical_state or "DEFORMATION" in sar_state:
        return "RESIDUAL_STRUCTURALLY_INDETERMINATE"
    if "COMMON_COMPATIBLE" in optical_state or "COMMON_COMPATIBLE" in sar_state:
        return "RESIDUAL_RELATION_WEAK_OR_UNRESOLVED"
    optical_above = "ABOVE_COMMON" in optical_state
    optical_below = "BELOW_COMMON" in optical_state
    sar_above = "ABOVE_COMMON" in sar_state
    sar_below = "BELOW_COMMON" in sar_state
    if (optical_above and sar_above) or (optical_below and sar_below):
        return "RESIDUAL_DIRECTION_CONCORDANT"
    if (optical_above and sar_below) or (optical_below and sar_above):
        return "RESIDUAL_DIRECTION_CONTRADICTORY"
    return "RESIDUAL_RELATION_WEAK_OR_UNRESOLVED"


def develop_cross_modal(hypotheses: pd.DataFrame, sar: pd.DataFrame) -> pd.DataFrame:
    frame = hypotheses.merge(
        sar,
        on=["run_id", "source_sar_frame", "destination_sar_frame", "source_region_id", "destination_region_id"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_sar"),
    )
    frame["cross_modal_residual_relation"] = [
        cross_modal_relation(str(o), str(s))
        for o, s in zip(frame["optical_residual_state"], frame["sar_p0_residual_state"])
    ]
    frame["residual_direction_used_for_pruning"] = False
    frame["identity_assignment_performed"] = False
    frame["final_localization_performed"] = False
    frame.to_parquet(OUTPUT / "cross_modal_residual_hypotheses_development.parquet", index=False, compression="zstd")

    summary = (
        frame.groupby(["run_id", "optical_residual_state", "sar_p0_residual_state", "cross_modal_residual_relation"])
        .size()
        .rename("hypothesis_count")
        .reset_index()
    )
    summary.to_csv(OUTPUT / "cross_modal_residual_state_summary.csv", index=False, encoding="utf-8-sig")

    # Descriptive, GT-blind development candidates.  They are not rescue claims.
    candidate_rows: list[dict[str, Any]] = []
    for window_id, group in frame.groupby("window_id"):
        counts = group["cross_modal_residual_relation"].value_counts().to_dict()
        candidate_rows.append(
            {
                "window_id": window_id,
                "run_id": str(group.iloc[0]["run_id"]),
                "source_sar_frame": int(group.iloc[0]["source_sar_frame"]),
                "destination_sar_frame": int(group.iloc[0]["destination_sar_frame"]),
                "branch_count": int(group["raw_track_fragment_id"].nunique()),
                "hypothesis_count": len(group),
                "concordant_count": int(counts.get("RESIDUAL_DIRECTION_CONCORDANT", 0)),
                "contradictory_count": int(counts.get("RESIDUAL_DIRECTION_CONTRADICTORY", 0)),
                "weak_count": int(counts.get("RESIDUAL_RELATION_WEAK_OR_UNRESOLVED", 0)),
                "structural_indeterminate_count": int(counts.get("RESIDUAL_STRUCTURALLY_INDETERMINATE", 0)),
                "unavailable_count": int(counts.get("RESIDUAL_UNAVAILABLE", 0)),
                "possible_rescue_candidate_gt_blind": bool(
                    counts.get("RESIDUAL_DIRECTION_CONCORDANT", 0) > 0
                    and counts.get("RESIDUAL_DIRECTION_CONTRADICTORY", 0) > 0
                ),
                "manual_reference_used": False,
                "rescue_established": False,
            }
        )
    pd.DataFrame(candidate_rows).to_csv(
        OUTPUT / "gt_blind_possible_rescue_candidates_development.csv", index=False, encoding="utf-8-sig"
    )
    return frame


def build_grounding_interface() -> tuple[pd.DataFrame, dict[str, Any]]:
    assignment = pd.read_csv(OFFLINE_ASSIGNMENT)
    assignment = assignment[
        (assignment["interface_kind"] == "RAW_DETECTED_FRAGMENT_ALL")
        & (assignment["time_window_half_width_ms"] == 0)
        & assignment["assigned_track_id_offline"].notna()
    ].copy()
    assignment = assignment[assignment["run_id"].isin(DEVELOPMENT_RUNS)].copy()
    rows: list[dict[str, Any]] = []
    for fragment, group in assignment.groupby("assigned_track_id_offline"):
        targets = group["target_id"].astype(str).value_counts()
        unique_frames = int(group["frame_index"].nunique())
        unique_targets = int(len(targets))
        dominant_target = str(targets.index[0]) if len(targets) else ""
        dominant_fraction = float(targets.iloc[0] / targets.sum()) if len(targets) else math.nan
        if unique_frames >= 2 and unique_targets == 1:
            state = "LIKELY"
            reason = "FRAME_LEVEL_OFFLINE_GEOMETRIC_ASSIGNMENT_CONSISTENT_ACROSS_MULTIPLE_FRAMES"
        elif unique_frames >= 2 and unique_targets > 1:
            state = "AMBIGUOUS"
            reason = "OFFLINE_GEOMETRIC_ASSIGNMENT_MAPS_FRAGMENT_TO_MULTIPLE_TARGETS"
        else:
            state = "UNRESOLVED"
            reason = "ONLY_SINGLE_FRAME_OFFLINE_GEOMETRIC_ASSIGNMENT"
        rows.append(
            {
                "raw_track_fragment_id": str(fragment),
                "run_id": str(group.iloc[0]["run_id"]),
                "offline_target_id": dominant_target,
                "grounding_state": state,
                "assigned_frame_count": unique_frames,
                "unique_target_count": unique_targets,
                "dominant_target_fraction": dominant_fraction,
                "grounding_reason": reason,
                "provenance": str(OFFLINE_ASSIGNMENT.relative_to(WORKSPACE)),
                "interface_semantics": "OFFLINE_EVALUATION_REFERENCE_GEOMETRIC_NOT_RUNTIME_IDENTITY",
                "runtime_use_allowed": False,
                "common_motion_use_allowed": False,
                "residual_calculation_use_allowed": False,
            }
        )
    grounding = pd.DataFrame(rows).sort_values(["run_id", "raw_track_fragment_id"])
    grounding.to_csv(OUTPUT / "optical_branch_offline_grounding_interface.csv", index=False, encoding="utf-8-sig")

    provenance = pd.read_csv(OPTICAL_PROVENANCE)
    audit = {
        "schema": "PERSON_CMR_D0_OPTICAL_BRANCH_GROUNDING_AUDIT_V1",
        "created_at": now_iso(),
        "direct_manual_optical_raw_fragment_annotation_found": False,
        "offline_frame_level_geometric_assignment_found": True,
        "offline_assignment_sha256": sha256_file(OFFLINE_ASSIGNMENT),
        "optical_provenance_sha256": sha256_file(OPTICAL_PROVENANCE),
        "grounding_state_counts": grounding["grounding_state"].value_counts().to_dict(),
        "confirmed_count": int((grounding["grounding_state"] == "CONFIRMED").sum()),
        "likely_count": int((grounding["grounding_state"] == "LIKELY").sum()),
        "ambiguous_count": int((grounding["grounding_state"] == "AMBIGUOUS").sum()),
        "unresolved_count": int((grounding["grounding_state"] == "UNRESOLVED").sum()),
        "raw_interface_semantics": sorted(provenance["interface_semantics"].astype(str).unique().tolist()),
        "runtime_identity_established": False,
        "allowed_use": "OFFLINE_EVALUATION_REFERENCE_ONLY",
        "prohibited_uses": [
            "runtime_branch_generation",
            "common_motion_estimation",
            "residual_calculation",
            "hypothesis_selection",
            "timing_fit",
            "P0_or_SAR_region_generation",
            "final_inference",
        ],
    }
    write_json(OUTPUT / "optical_branch_grounding_audit.json", audit)
    return grounding, audit


def sar_image_path(run_id: str, frame_index: int) -> Path:
    files = sorted((SAR_IMAGE_ROOT / run_id).glob(f"frame_{frame_index:06d}_t*ms.jpg"))
    if not files:
        files = sorted((SAR_IMAGE_ROOT / run_id).glob(f"*{frame_index:06d}*.png"))
    return files[0] if files else Path("MISSING")


def crop_from_boxes(image: np.ndarray, boxes: list[tuple[float, float, float, float]], margin: int = 100) -> tuple[np.ndarray, tuple[int, int]]:
    h, w = image.shape[:2]
    x1 = max(0, int(min(b[0] for b in boxes) - margin))
    y1 = max(0, int(min(b[1] for b in boxes) - margin))
    x2 = min(w, int(max(b[2] for b in boxes) + margin))
    y2 = min(h, int(max(b[3] for b in boxes) + margin))
    return image[y1:y2, x1:x2].copy(), (x1, y1)


def render_optical_case(row: pd.Series, optical: pd.DataFrame, common: pd.DataFrame, output: Path) -> None:
    pair_common = common[common["window_id"] == row.window_id].iloc[0]
    source_obs = optical[
        (optical["run_id"] == row.run_id)
        & (optical["frame_index"] == int(row.source_optical_frame))
        & (optical["raw_track_fragment_id"].astype(str) == str(row.raw_track_fragment_id))
    ].iloc[0]
    destination_obs = optical[
        (optical["run_id"] == row.run_id)
        & (optical["frame_index"] == int(row.destination_optical_frame))
        & (optical["raw_track_fragment_id"].astype(str) == str(row.raw_track_fragment_id))
    ].iloc[0]
    images = [cv2.imread(str(image_path_for_observation(source_obs))), cv2.imread(str(image_path_for_observation(destination_obs)))]
    if any(x is None for x in images):
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, image, obs, title in zip(axes, images, [source_obs, destination_obs], ["source", "destination"]):
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        ax.imshow(rgb)
        rect = plt.Rectangle((obs.bbox_x1, obs.bbox_y1), obs.bbox_x2 - obs.bbox_x1, obs.bbox_y2 - obs.bbox_y1, fill=False, color="#00e5ff", linewidth=2)
        ax.add_patch(rect)
        ax.set_xlim(max(0, obs.bbox_x1 - 350), min(rgb.shape[1], obs.bbox_x2 + 350))
        ax.set_ylim(min(rgb.shape[0], obs.bbox_y2 + 250), max(0, obs.bbox_y1 - 250))
        ax.set_title(f"{title} optical F{int(obs.frame_index)}")
        ax.axis("off")
    fig.suptitle(
        f"{row.run_id} {row.raw_track_fragment_id}\n{row.optical_residual_state} | obs={row.d_mid_observed_deg:.3f} deg common={row.d_mid_common_deg:.3f} deg residual={row.residual_mid_descriptor_deg:.3f} deg\n{pair_common.hybrid_common_state}"
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=140)
    plt.close(fig)


def mask_bbox(mask: np.ndarray, margin: int = 35) -> tuple[int, int, int, int]:
    yy, xx = np.nonzero(mask)
    height, width = mask.shape
    if len(xx) == 0:
        return 0, width, height, 0
    x1 = max(0, int(xx.min()) - margin)
    x2 = min(width, int(xx.max()) + margin + 1)
    y1 = max(0, int(yy.min()) - margin)
    y2 = min(height, int(yy.max()) + margin + 1)
    return x1, x2, y2, y1


def draw_sar_supports(
    ax: plt.Axes,
    image: np.ndarray,
    supports: list[tuple[np.ndarray, str, str]],
    title: str,
    zoom: bool,
) -> None:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    ax.imshow(rgb)
    union = np.zeros(image.shape[:2], dtype=bool)
    for support, color, _ in supports:
        binary = np.asarray(support, dtype=bool)
        union |= binary
        if binary.any():
            alpha = np.zeros((*binary.shape, 4), dtype=float)
            rgb_color = np.asarray(matplotlib.colors.to_rgb(color), dtype=float)
            alpha[binary, :3] = rgb_color
            alpha[binary, 3] = 0.22
            ax.imshow(alpha)
            ax.contour(binary.astype(float), levels=[0.5], colors=[color], linewidths=1.8)
    if zoom:
        x1, x2, y2, y1 = mask_bbox(union)
        ax.set_xlim(x1, x2)
        ax.set_ylim(y2, y1)
    ax.set_title(title, fontsize=10)
    ax.axis("off")


def render_cross_modal_case(
    row: pd.Series,
    optical: pd.DataFrame,
    common: pd.DataFrame,
    data: dict[str, Any],
    output: Path,
) -> None:
    temp = OUTPUT / "figures" / "_temp_optical.png"
    render_optical_case(row, optical, common, temp)
    if not temp.exists():
        return
    optical_img = np.asarray(Image.open(temp).convert("RGB"))
    sar_a_path = sar_image_path(str(row.run_id), int(row.source_sar_frame))
    sar_b_path = sar_image_path(str(row.run_id), int(row.destination_sar_frame))
    if not sar_a_path.exists() or not sar_b_path.exists():
        return
    sar_a = cv2.imread(str(sar_a_path), cv2.IMREAD_COLOR)
    sar_b = cv2.imread(str(sar_b_path), cv2.IMREAD_COLOR)
    if sar_a is None or sar_b is None:
        return

    regions = data["regions"].set_index("region_id", drop=False)
    source_region = regions.loc[str(row.source_region_id)]
    destination_region = regions.loc[str(row.destination_region_id)]
    source_labels = np.load(REGION_MASKS / f"{source_region.frame_uid}.npz")["Q095"]
    destination_labels = np.load(REGION_MASKS / f"{destination_region.frame_uid}.npz")["Q095"]
    source_support = source_labels == int(source_region.region_label)
    destination_support = destination_labels == int(destination_region.region_label)
    model = data["models"][(str(row.run_id), int(row.source_sar_frame), int(row.destination_sar_frame))]
    predicted_occupancy = cv2.warpAffine(
        source_support.astype(np.float32),
        p0_matrix(model),
        (source_support.shape[1], source_support.shape[0]),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0.0,
    )
    predicted_support = predicted_occupancy >= 0.5

    fig = plt.figure(figsize=(16, 14))
    grid = fig.add_gridspec(3, 2, height_ratios=[1.25, 1.0, 1.0])
    optical_ax = fig.add_subplot(grid[0, :])
    optical_ax.imshow(optical_img)
    optical_ax.axis("off")
    optical_ax.set_title("Optical raw-fragment observation and common/residual decomposition", fontsize=11)

    source_full = fig.add_subplot(grid[1, 0])
    destination_full = fig.add_subplot(grid[1, 1])
    source_zoom = fig.add_subplot(grid[2, 0])
    destination_zoom = fig.add_subplot(grid[2, 1])
    source_supports = [(source_support, "#00e5ff", "source q95")]
    destination_supports = [
        (predicted_support, "#ff3df2", "P0 predicted support"),
        (destination_support, "#8cff00", "destination q95"),
    ]
    draw_sar_supports(source_full, sar_a, source_supports, f"SAR source F{int(row.source_sar_frame)} full frame", zoom=False)
    draw_sar_supports(destination_full, sar_b, destination_supports, f"SAR destination F{int(row.destination_sar_frame)} full frame", zoom=False)
    draw_sar_supports(source_zoom, sar_a, source_supports, f"Source selected q95 region: {row.source_region_id}", zoom=True)
    draw_sar_supports(destination_zoom, sar_b, destination_supports, f"Destination selected q95 region: {row.destination_region_id}", zoom=True)

    fig.suptitle(
        f"{row.sar_p0_residual_state} | {row.cross_modal_residual_relation} | {row.sar_topology_state}\n"
        f"predicted theta=[{row.predicted_theta_low_deg:.3f}, {row.predicted_theta_high_deg:.3f}] deg; "
        f"observed theta=[{row.observed_theta_low_deg:.3f}, {row.observed_theta_high_deg:.3f}] deg; "
        f"soft IoU={row.soft_iou:.3f}; retention={row.source_total_retention:.3f}; explained={row.destination_explained_fraction:.3f}\n"
        "cyan=source q95 | magenta=frozen-P0 predicted support | green=observed destination q95",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=140)
    plt.close(fig)
    temp.unlink(missing_ok=True)


def select_and_render_cases(data: dict[str, Any], common: pd.DataFrame, optical_residual: pd.DataFrame, cross: pd.DataFrame) -> pd.DataFrame:
    optical = data["optical"]
    figdir = OUTPUT / "figures" / "development_cases"
    figdir.mkdir(parents=True, exist_ok=True)
    rules = [
        ("01_clear_common_motion", optical_residual["optical_residual_state"].eq("OPTICAL_RESIDUAL_COMMON_COMPATIBLE")),
        ("02_branch_above_common", optical_residual["optical_residual_state"].eq("OPTICAL_RESIDUAL_ABOVE_COMMON")),
        ("03_branch_below_common", optical_residual["optical_residual_state"].eq("OPTICAL_RESIDUAL_BELOW_COMMON")),
        ("04_optical_deformation", optical_residual["optical_residual_state"].eq("OPTICAL_RESIDUAL_DEFORMATION_OR_MIXED")),
        ("05_common_estimator_disagreement", optical_residual["optical_residual_state"].eq("OPTICAL_RESIDUAL_COMMON_ESTIMATE_AMBIGUOUS")),
    ]
    registry: list[dict[str, Any]] = []
    selected_hypotheses: set[str] = set()
    for name, mask in rules:
        candidates = optical_residual[mask].sort_values(["run_id", "window_id", "raw_track_fragment_id"])
        if candidates.empty:
            registry.append({"case_name": name, "status": "CATEGORY_NOT_OBSERVED", "path": ""})
            continue
        if name == "01_clear_common_motion":
            row = candidates.assign(_visual_score=candidates["residual_mid_descriptor_deg"].abs()).sort_values(
                ["_visual_score", "run_id", "window_id", "raw_track_fragment_id"]
            ).iloc[0]
        elif name == "02_branch_above_common":
            row = candidates.sort_values(
                ["residual_mid_descriptor_deg", "run_id", "window_id"], ascending=[False, True, True]
            ).iloc[0]
        elif name == "04_optical_deformation":
            row = candidates.assign(_visual_score=candidates["d_width_observed_deg"].abs()).sort_values(
                ["_visual_score", "run_id", "window_id"], ascending=[False, True, True]
            ).iloc[0]
        else:
            row = candidates.iloc[0]
        path = figdir / f"{name}.png"
        render_optical_case(row, optical, common, path)
        registry.append({"case_name": name, "status": "OBSERVED", "path": str(path.relative_to(WORKSPACE)), "window_id": row.window_id, "raw_track_fragment_id": row.raw_track_fragment_id})

    possible_windows = set(
        cross.groupby("window_id")["cross_modal_residual_relation"]
        .agg(lambda values: {"RESIDUAL_DIRECTION_CONCORDANT", "RESIDUAL_DIRECTION_CONTRADICTORY"}.issubset(set(values)))
        .loc[lambda values: values]
        .index.astype(str)
    )
    if possible_windows:
        pair_quality = (
            cross[cross["window_id"].astype(str).isin(possible_windows)]
            .groupby(["window_id", "cross_modal_residual_relation"])["soft_iou"]
            .max()
            .unstack(fill_value=0)
        )
        pair_quality["paired_visual_quality"] = (
            pair_quality.get("RESIDUAL_DIRECTION_CONCORDANT", 0).fillna(0)
            + pair_quality.get("RESIDUAL_DIRECTION_CONTRADICTORY", 0).fillna(0)
        )
        paired_rescue_window = str(pair_quality["paired_visual_quality"].idxmax())
    else:
        paired_rescue_window = ""

    cross_rules = [
        ("11_sar_p0_compatible", cross["sar_p0_residual_state"].eq("SAR_P0_RESIDUAL_COMMON_COMPATIBLE")),
        ("12_sar_above_p0", cross["sar_p0_residual_state"].eq("SAR_P0_RESIDUAL_ABOVE_COMMON")),
        ("13_sar_below_p0", cross["sar_p0_residual_state"].eq("SAR_P0_RESIDUAL_BELOW_COMMON")),
        ("14_sar_deformation", cross["sar_p0_residual_state"].eq("SAR_P0_RESIDUAL_DEFORMATION_OR_MIXED")),
        ("15_sar_boundary_censored", cross["sar_p0_residual_state"].eq("SAR_P0_RESIDUAL_BOUNDARY_CENSORED")),
        ("19_residual_concordant", cross["cross_modal_residual_relation"].eq("RESIDUAL_DIRECTION_CONCORDANT")),
        ("20_residual_contradictory", cross["cross_modal_residual_relation"].eq("RESIDUAL_DIRECTION_CONTRADICTORY")),
        ("21_optical_clear_sar_ambiguous", cross["optical_residual_state"].isin(["OPTICAL_RESIDUAL_ABOVE_COMMON", "OPTICAL_RESIDUAL_BELOW_COMMON"]) & cross["cross_modal_residual_relation"].eq("RESIDUAL_STRUCTURALLY_INDETERMINATE")),
        ("23_possible_rescue_candidate", cross["window_id"].astype(str).eq(paired_rescue_window) & cross["cross_modal_residual_relation"].eq("RESIDUAL_DIRECTION_CONCORDANT")),
        ("24_deceptive_candidate", cross["window_id"].astype(str).eq(paired_rescue_window) & cross["cross_modal_residual_relation"].eq("RESIDUAL_DIRECTION_CONTRADICTORY")),
    ]
    for name, mask in cross_rules:
        candidates = cross[mask & ~cross["hypothesis_id"].isin(selected_hypotheses)].sort_values(
            ["run_id", "window_id", "hypothesis_id"]
        )
        if candidates.empty:
            registry.append({"case_name": name, "status": "CATEGORY_NOT_OBSERVED", "path": ""})
            continue
        row = candidates.sort_values(
            ["soft_iou", "source_total_retention", "destination_explained_fraction", "run_id", "window_id", "hypothesis_id"],
            ascending=[False, False, False, True, True, True],
        ).iloc[0]
        selected_hypotheses.add(str(row.hypothesis_id))
        path = figdir / f"{name}.png"
        render_cross_modal_case(row, optical, common, data, path)
        registry.append({"case_name": name, "status": "OBSERVED", "path": str(path.relative_to(WORKSPACE)), "window_id": row.window_id, "raw_track_fragment_id": row.raw_track_fragment_id, "hypothesis_id": row.hypothesis_id})
    frame = pd.DataFrame(registry)
    frame.to_csv(OUTPUT / "development_real_case_registry.csv", index=False, encoding="utf-8-sig")

    images = [Image.open(WORKSPACE / p).convert("RGB") for p in frame.loc[frame["status"] == "OBSERVED", "path"] if (WORKSPACE / p).exists()]
    if images:
        thumb_w = 800
        thumbs = []
        for im in images:
            ratio = thumb_w / im.width
            thumbs.append(im.resize((thumb_w, max(1, int(im.height * ratio)))))
        canvas = Image.new("RGB", (thumb_w, sum(x.height for x in thumbs)), "white")
        y = 0
        for im in thumbs:
            canvas.paste(im, (0, y))
            y += im.height
        canvas.save(OUTPUT / "figures" / "CMR_D0_DEVELOPMENT_CASE_CONTACT_SHEET.jpg", quality=88)
    return frame


def write_visual_review_ledger() -> None:
    text = """# CMR-D0 multimodal visual review ledger

- Review role: development-only mechanism audit; not confirmation and not runtime inference.
- CMR contact sheet reviewed: `figures/CMR_D0_DEVELOPMENT_CASE_CONTACT_SHEET.jpg`.
- Individual CMR cases reviewed: optical deformation, strong common-estimator disagreement, all five SAR structural-state examples, and the paired possible-rescue/deceptive hypotheses.
- Earlier grounding assets reviewed directly: M0B1-V2 `POST_REFERENCE_CASE_CONTACT_SHEET.png` and offline raw-fragment review packs 01, 03, and 08; the frozen review CSV records all ten packs as `UNRESOLVED`.

## Optical observations

1. The selected deformation case shows asynchronous bbox-boundary change: one boundary moves materially while the other is nearly fixed.  Occlusion and detector-box width change are visually plausible, so `DEFORMATION_OR_MIXED` is more faithful than forcing a residual sign.
2. Strong GMC/branch-consensus disagreement occurs in close multi-person, shared-umbrella/occlusion scenes.  Branch consensus can be contaminated by subject motion or detector grouping; keeping background GMC primary and emitting ambiguity is justified.
3. No `OPTICAL_RESIDUAL_BELOW_COMMON` case was manufactured.  Thirteen branches have a negative midpoint descriptor, but only three have both point boundary residuals negative and none has both uncertainty-adjusted upper bounds below zero.  Negative midpoint cases resolve to deformation/mixed or common-compatible.

## SAR observations

1. The compatible example shows near-coincident frozen-P0 prediction and observed q95 support.
2. Above/below examples show coherent relative boundary offsets while retaining high overlap; their states are image-domain response-support relations, not target velocity.
3. The deformation example has high overlap but mismatched left/right boundary behavior, validating a non-rigid state rather than centroid subtraction.
4. The censored example touches the SAR observable fan boundary, so a directional residual must remain censored.

## Cross-modal observations

The paired possible-rescue/deceptive examples come from one GT-blind development window and share the same optical residual.  Both a concordant and a contradictory SAR hypothesis have high support overlap.  This demonstrates candidate-level structural differentiation but does not identify the correct hypothesis and does not establish rescue.

## Grounding observations

The reviewed optical fragments are visually continuous over the displayed adjacent frames.  The SAR q95 regions and offline target markers remain many-to-many or otherwise lack an authoritative cross-modal identity cue.  Visual review therefore does not upgrade the existing frame-level geometric assignment to `CONFIRMED`; grounding remains offline-only `LIKELY` or `UNRESOLVED` and is prohibited from common-motion estimation, residual calculation, hypothesis selection, or final inference.
"""
    (OUTPUT / "CMR_D0_MULTIMODAL_VISUAL_REVIEW_LEDGER.md").write_text(text, encoding="utf-8")


def write_authority_review() -> None:
    text = """# CMR-D0 authoritative source review and supersession

- Review role: mechanism development authority ledger.
- Precedence: current code/schema and validators > frozen materialized artifacts > current protocols > older narratives.
- `old_work` used: `NO`.

## Reused authorities

1. Frozen P0 source-to-destination image-domain common transport and its pair/model comparability.
2. M0A soft affine mask-warp convention and q95 support-continuity semantics.
3. Latest pixel-level shell-region topology; coarse angular-extent topology is superseded.
4. M0B1-R corresponding-boundary representation; the old all-pairs displacement interval remains preserved as a negative representation.
5. M0B1-V2 GT-blind optical diversity atlas and raw-fragment runtime boundary.
6. Existing optical background GMC implementation as engineering provenance, not as a frozen CMR estimator.

## CMR-D0 supersessions

- Scene-global branch majority is retained as a diagnostic baseline but is not the primary common-motion estimator because it can absorb the branch residual being studied.
- CMR optical v0 uses detection-masked background affine-partial GMC with deterministic held-out feature residual uncertainty.
- Optical branch consensus is never averaged with background GMC.  Agreement/disagreement is an explicit state.
- SAR residual is predicted-support versus observed-support after frozen P0; centroid-minus-vector is not the primary representation.
- Existing frame-level offline geometric track-reference assignment is accepted only as an `OFFLINE_EVALUATION_REFERENCE`; it does not establish runtime identity.

## Non-claims

No physical platform trajectory, PERSON velocity, synchronization calibration, runtime identity, pruning, assignment, tracker, factor graph, P2, final center, or final box is established.
"""
    (OUTPUT / "CMR_D0_AUTHORITATIVE_SOURCE_REVIEW_AND_SUPERSESSION.md").write_text(text, encoding="utf-8")


def write_mechanism_outputs(
    atlas: pd.DataFrame,
    common: pd.DataFrame,
    optical_residual: pd.DataFrame,
    sar: pd.DataFrame,
    cross: pd.DataFrame,
    grounding: pd.DataFrame,
    cases: pd.DataFrame,
) -> dict[str, Any]:
    dev_atlas = atlas[(atlas["pool"] == "DEVELOPMENT_POOL") & atlas["cross_modal_eligible"]]
    conf_atlas = atlas[(atlas["pool"] == "CONFIRMATION_POOL") & atlas["cross_modal_eligible"]]
    optical_counts = optical_residual["optical_residual_state"].value_counts().to_dict()
    sar_counts = sar["sar_p0_residual_state"].value_counts().to_dict()
    relation_counts = cross["cross_modal_residual_relation"].value_counts().to_dict()
    common_counts = common["background_gmc_state"].value_counts().to_dict()
    hybrid_counts = common["hybrid_common_state"].value_counts().to_dict()
    distinct_windows = int(
        optical_residual.groupby("window_id")["optical_residual_state"].nunique().gt(1).sum()
    )
    negative_midpoint = int((optical_residual["residual_mid_descriptor_deg"] < 0).sum())
    both_point_negative = int(
        (
            (optical_residual["d_left_observed_deg"] - optical_residual["d_left_common_deg"] < 0)
            & (optical_residual["d_right_observed_deg"] - optical_residual["d_right_common_deg"] < 0)
        ).sum()
    )
    definite_below = int(
        (
            (optical_residual["residual_left_high_deg"] < 0)
            & (optical_residual["residual_right_high_deg"] < 0)
        ).sum()
    )
    possible_candidates = pd.read_csv(OUTPUT / "gt_blind_possible_rescue_candidates_development.csv")
    possible_count = int(possible_candidates["possible_rescue_candidate_gt_blind"].sum())

    summary = {
        "schema": "PERSON_CMR_D0_DEVELOPMENT_SUMMARY_V1",
        "created_at": now_iso(),
        "starting_head": "b6e7a3a5ade1844d14c771c7aaaa02099e663c3a",
        "report_generation_head": git_head(),
        "stage": "CMR_D0_COMMON_RESIDUAL_MOTION_MECHANISM_DEVELOPMENT",
        "stage_role": "DEVELOPMENT_NOT_CONFIRMATION",
        "development_runs": list(DEVELOPMENT_RUNS),
        "confirmation_runs": list(CONFIRMATION_RUNS),
        "scheduled_lag1_windows_all_cross_modal_runs": int(len(atlas)),
        "cross_modal_eligible_windows_all_pools": int(atlas["cross_modal_eligible"].sum()),
        "development_eligible_windows": len(dev_atlas),
        "development_eligible_branch_instances": int(dev_atlas["runtime_common_fragment_count"].sum()),
        "confirmation_input_eligible_windows": len(conf_atlas),
        "confirmation_input_eligible_branch_instances": int(conf_atlas["runtime_common_fragment_count"].sum()),
        "confirmation_mechanism_executed": False,
        "background_gmc_state_counts": common_counts,
        "hybrid_common_state_counts": hybrid_counts,
        "optical_residual_state_counts": optical_counts,
        "optical_windows_with_branch_state_distinction": distinct_windows,
        "optical_negative_midpoint_descriptor_count": negative_midpoint,
        "optical_both_point_boundaries_negative_count": both_point_negative,
        "optical_definite_below_common_count": definite_below,
        "optical_below_common_audit": "NOT_OBSERVED_AFTER_ESTIMATOR_UNCERTAINTY; NEGATIVE_MIDPOINT_CASES_ARE_DEFORMATION_OR_COMMON_COMPATIBLE",
        "sar_p0_residual_state_counts": sar_counts,
        "cross_modal_residual_relation_counts": relation_counts,
        "gt_blind_possible_rescue_candidate_windows": possible_count,
        "rescue_established": False,
        "grounding_state_counts": grounding["grounding_state"].value_counts().to_dict(),
        "grounding_runtime_use_allowed": False,
        "real_case_observed_count": int((cases["status"] == "OBSERVED").sum()),
        "real_case_category_not_observed_count": int((cases["status"] == "CATEGORY_NOT_OBSERVED").sum()),
        "ordering_route": "REJECTED_FOR_V0_WITHOUT_BRANCH_TO_SAR_EDGE_CORRESPONDENCE",
        "magnitude_fit": False,
        "weighted_score": False,
        "hypotheses_pruned": False,
        "identity_assignment_performed": False,
        "p0_modified": False,
        "confirmation_readiness": "READY_FOR_CMR_V0_CONFIRMATION",
        "readiness_qualification": "MECHANISM_CONTRACT_COMPLETE; OFFLINE_GROUNDING_IS_LIKELY_OR_AMBIGUOUS_NOT_RUNTIME_IDENTITY",
    }
    write_json(OUTPUT / "cmr_d0_final_summary.json", summary)

    development_log = f"""# CMR-D0 mechanism development log

## Iteration 0: scene-majority baseline

1. Observed problem: M0B1-V2 showed R02 branch direction exactly reproduced the scene-global direction.
2. Real case: the frozen R02 scene-common positive case.
3. Failure: branch majority is circular as a primary common estimator because branch motion can enter the baseline.
4. Repair: use detection-masked background image registration as the primary estimator; retain branch consensus only as a diagnostic.
5. Meaning: background affine-partial GMC estimates shared optical image displacement, not camera or platform trajectory.
6. Side effect: windows with weak background texture become unavailable rather than receiving a forced common vector.

## Iteration 1: common uncertainty

1. Observed problem: point estimates forced small estimator errors into false residual signs.
2. Repair: deterministic spatial feature holdout; convert held-out x-residual P90 into angular uncertainty through the frozen positive mapping slope.
3. Meaning: the uncertainty describes estimator repeatability, not bbox support width and not PERSON confidence.
4. Result: optical residual states are `{optical_counts}`.

## Iteration 2: branch consensus hybrid

1. Observed problem: background GMC and multi-branch consensus can disagree.
2. Repair: no weighted averaging.  Materialize agreement, mild disagreement, strong disagreement, and one-unavailable states.
3. Result: hybrid states are `{hybrid_counts}`.

## Iteration 3: SAR residual representation

1. Rejected idea: region-centroid displacement minus P0 vector as the primary SAR residual.
2. Repair: warp the full q95 source mask with frozen P0 soft occupancy and compare predicted versus observed left/right support boundaries, width, overlap, and topology.
3. Meaning: response-support residual, not PERSON motion.
4. Result: SAR states are `{sar_counts}`.

## Iteration 4: cross-modal relation

1. Chosen relation: direction and structural compatibility only; no magnitude equality or fitted cross-projection scale.
2. Rejected route: residual ordering as v0 evidence because no runtime-legal branch-to-SAR-edge correspondence exists; ordering would silently introduce assignment.
3. Result: relations are `{relation_counts}`.
4. GT-blind possible-rescue candidates: `{possible_count}`.  These are development cases, not established rescue.

## Iteration 5: visual mechanism audit

1. Cross-modal figures were repaired to overlay source q95, frozen-P0 predicted support, destination q95, full-frame context, and local zoom.
2. Optical deformation examples show asynchronous bbox-boundary changes; strong common-estimator conflicts occur in multi-person occlusion/shared-umbrella scenes.
3. No below-common category was created by threshold tuning: negative midpoint descriptors=`{negative_midpoint}`, both point boundaries negative=`{both_point_negative}`, both uncertainty-adjusted upper bounds negative=`{definite_below}`.
4. Paired possible-rescue/deceptive hypotheses can both retain high SAR support overlap in the same window; candidate differentiation is visible, but correctness/rescue is not established.
5. Earlier offline grounding packs were reviewed and still lack an authoritative cross-modal identity cue.

## Eligibility accounting audit

- `394` is the number of scheduled lag-1 window rows across R01ZF/R02ZF/R03ZF/R04ZF, not eligible branch instances.
- The frozen GT-blind intersection leaves `{int(atlas['cross_modal_eligible'].sum())}` eligible windows: `{len(dev_atlas)}` development and `{len(conf_atlas)}` confirmation-input windows.
- Development eligible branch instances are the sum of continuous runtime fragments over development eligible windows: `{int(dev_atlas['runtime_common_fragment_count'].sum())}`.

## Isolation and overfitting audit

- Development windows: `{len(dev_atlas)}` across R01ZF/R02ZF/R03ZF.
- Confirmation availability: `{len(conf_atlas)}` eligible R04ZF windows.
- Confirmation residuals/outcomes accessed: `NO`.
- Manual SAR reference used to choose estimator, representation, uncertainty, or cases: `NO`.
- Main overfitting risk: estimator-state definitions were developed on exposed runs and must be tested once on R04ZF without repair.
"""
    (OUTPUT / "CMR_D0_DEVELOPMENT_LOG.md").write_text(development_log, encoding="utf-8")

    spec = f"""# CMR-v0 frozen mechanism specification

- State: `CMR_V0_MECHANISM_FROZEN_AFTER_DEVELOPMENT`
- Stage role: mechanism contract ready for a separate confirmation task.
- Confirmation executed here: `NO`.

## Inputs

Runtime-legal optical detections and raw fragments; optical image pairs; nominal timing query; fixed positive optical-to-SAR azimuth mapping; q95 response regions/masks; latest pixel topology; frozen P0 pair/model/comparability; boundary/availability metadata.

Manual target identity, physical target ID, SAR reference, and offline grounding are excluded from mechanism calculation.

## Optical common apparent motion v0

1. Mask all detected target boxes with a fixed geometric padding.
2. Track background features with forward/backward LK.
3. Use a deterministic spatial holdout.
4. Fit affine-partial GMC by RANSAC to fit anchors.
5. Evaluate the affine at each branch bbox; preserve left/right boundary predictions.
6. Uncertainty is held-out x-residual P90 converted by the frozen mapping slope.
7. Branch consensus is diagnostic only.  Strong background/consensus disagreement produces `COMMON_ESTIMATE_AMBIGUOUS`; no averaging.

Unavailable states cover missing images, insufficient features/tracks, failed affine fit, or implausible scale.

## Optical branch residual v0

For each corresponding boundary, subtract the common prediction interval.  Both residual boundary intervals above zero give `ABOVE_COMMON`; both below give `BELOW_COMMON`; both containing zero give `COMMON_COMPATIBLE`; mixed boundaries give `DEFORMATION_OR_MIXED`.

Development observed no definite `BELOW_COMMON`: negative midpoint descriptors were absorbed by uncertainty or had opposing boundary behavior.  This absence is retained as a data/mechanism observation and thresholds are not tuned to populate the category.

## SAR P0-relative residual v0

Warp the binary q95 source support through frozen P0 using the frozen M0A soft affine convention.  Compare soft overlap and the 0.5-occupancy predicted boundary with the observed q95 destination support.  P0 held-out P90 residual is converted locally to angular boundary uncertainty.  Boundary/truncated cases are censored.  Split/merge-like topology is retained and never forced into rigid velocity.

## Cross-modal relation v0

Only residual direction/structure is compared.  Same definite residual sign is concordant; opposite sign is contradictory; common-compatible is weak/unresolved; deformation or censoring is structurally indeterminate; unavailable stays unavailable.  No magnitude fit, weighted score, rejection, pruning, identity, or assignment occurs.

## Output

Categorical evidence states, uncertainty, overlap/topology descriptors, provenance, and ambiguity.  The mechanism cannot output PERSON identity, physical motion, unique path, final SAR center, final SAR box, or P2.

## Development accounting

- Optical residual states: `{optical_counts}`.
- SAR residual states: `{sar_counts}`.
- Cross-modal relations: `{relation_counts}`.
- Development windows with more than one branch residual state: `{distinct_windows}`.
"""
    (OUTPUT / "CMR_V0_MECHANISM_SPECIFICATION_FROZEN.md").write_text(spec, encoding="utf-8")

    confirmation = """# CMR-v0 confirmation protocol draft

- Status: `DRAFT_NOT_EXECUTED`.
- Confirmation run: R04ZF only.
- The frozen CMR-v0 implementation and all state definitions must be hashed before any R04ZF mechanism output is generated.
- No implementation repair or threshold change is allowed after R04ZF outcome reveal unless an independently demonstrated implementation bug or data corruption exists.

## Baselines

1. `SAR_ONLY`
2. `SAR_PLUS_SCENE_COMMON`
3. `SAR_PLUS_BRANCH_RELATIVE_RESIDUAL`
4. `SAR_PLUS_COMMON_PLUS_RESIDUAL`

No weighted scalar score is allowed.  Compare categorical admissibility and pairwise explanation states.

## Primary outcome categories

- `RESCUE`: SAR-only ambiguous/wrong and residual adds the correct new distinction.
- `CONFIRMATION`: SAR-only already supports the explanation and residual agrees.
- `HARM`: SAR-only supports the correct explanation while residual favors a wrong one.
- `CONFLICT`: evidence families disagree without a justified winner.
- `NO_INFORMATION`: residual cannot distinguish.

Every hypothesis-reduction statement must be paired with supported retention.  Cluster units include run, SAR frame pair, raw fragment, and target/reference group.

## Route decision

- Stable branch-relative rescue permits later multi-hypothesis reasoning research.
- Scene-common-only value downgrades CMR to a scene-conditioned SAR prior.
- No incremental common/residual information terminates the angular branch-specific route.
"""
    (OUTPUT / "CMR_V0_CONFIRMATION_PROTOCOL_DRAFT.md").write_text(confirmation, encoding="utf-8")

    report = f"""# CMR-D0 common-residual motion mechanism development report

- Stage: `DEVELOPMENT`, not confirmation.
- Readiness: `{summary['confirmation_readiness']}`.
- Starting HEAD: `{summary['starting_head']}`.

## Data split

Across the four cross-modal runs, `394` scheduled lag-1 pair rows enter the atlas; this is a window count, not a branch-instance count.  The frozen GT-blind intersection leaves `{int(atlas['cross_modal_eligible'].sum())}` eligible windows.  Development uses R01ZF/R02ZF/R03ZF: `{len(dev_atlas)}` eligible windows and `{int(dev_atlas['runtime_common_fragment_count'].sum())}` branch instances.  R04ZF contains `{len(conf_atlas)}` eligible input windows and remains outcome-isolated.  Opposite-direction optical runs without complete frozen P0/topology are diagnostic-only.

## Optical common motion and residual

Background affine-partial GMC is the v0 primary common estimator.  Branch consensus is retained as a circularity-sensitive diagnostic and is never averaged with GMC.  Common states: `{common_counts}`; hybrid states: `{hybrid_counts}`.  Residual states: `{optical_counts}`.  `{distinct_windows}` development windows contain more than one optical branch residual state after common decomposition.  No definite below-common case is observed: `{negative_midpoint}` midpoint descriptors are negative, `{both_point_negative}` have both point boundary residuals negative, but `{definite_below}` have both uncertainty-adjusted upper bounds below zero; thresholds are not tuned to force the category.

## SAR P0-relative residual

The primary object is the frozen-P0-warped q95 support versus observed destination support.  Boundary, width, overlap, split/merge-like topology, and unavailable states are preserved.  State counts: `{sar_counts}`.  These are response-support residuals, not PERSON motion.

## Cross-modal residual relation

No magnitude equality or fitted scale is used.  Relation counts: `{relation_counts}`.  `{possible_count}` windows satisfy a GT-blind development-only pattern containing both concordant and contradictory candidate hypotheses.  They are possible rescue cases for future reference evaluation, not established rescue.

## Branch grounding

No direct manual optical raw-fragment annotation was found.  A pre-existing frame-level offline geometric track-reference assignment provides an offline-only interface.  Grounding states: `{summary['grounding_state_counts']}`.  It is excluded from runtime common motion, residuals, topology, timing, P0, and inference.

## Development lessons

- Background GMC is preferable to scene branch majority as the primary common estimator because it does not define common from the branches being tested.
- Point common estimates were insufficient; estimator uncertainty is necessary to preserve unresolved states.
- SAR centroid subtraction was rejected in favor of full support warp.
- Weighted background/branch common fusion and residual ordering were rejected.
- Multimodal visual review supports the deformation, estimator-ambiguity, SAR structural, and boundary-censoring states, while showing that high-overlap concordant and contradictory hypotheses can coexist.
- Direct review of earlier grounding packs does not establish authoritative raw-fragment-to-SAR identity.
- Confirmation overfitting risk remains real; R04ZF must be evaluated once with no repair.

## CMR-v0 and stop

The frozen contract is in `CMR_V0_MECHANISM_SPECIFICATION_FROZEN.md`.  The separate confirmation draft is not executed.  No pruning, tracker, assignment, factor graph, P2, center, or box is produced.
"""
    (OUTPUT / "CMR_D0_FINAL_DEVELOPMENT_REPORT.md").write_text(report, encoding="utf-8")
    return summary


def freeze_manifest(summary: dict[str, Any]) -> None:
    files = [p for p in OUTPUT.rglob("*") if p.is_file() and p.name not in {"cmr_d0_output_manifest.json", "cmr_d0_independent_validation.json"}]
    payload = {
        "schema": "PERSON_CMR_D0_OUTPUT_MANIFEST_V1",
        "created_at": now_iso(),
        "head": git_head(),
        "confirmation_executed": False,
        "confirmation_runs": list(CONFIRMATION_RUNS),
        "confirmation_readiness": summary["confirmation_readiness"],
        "files": [
            {"path": str(p.relative_to(WORKSPACE)), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
            for p in sorted(files)
        ],
        "prohibited_outputs": {
            "weighted_score": False,
            "hypotheses_pruned": False,
            "identity_assignment": False,
            "tracker": False,
            "factor_graph": False,
            "p2": False,
            "final_sar_center": False,
            "final_sar_box": False,
        },
    }
    write_json(OUTPUT / "cmr_d0_output_manifest.json", payload)


def run_all() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data = load_authorities()
    write_authority_review()
    atlas = build_eligible_atlas(data)
    common, optical_residual = develop_optical_common_and_residual(atlas, data)
    hypotheses = build_static_hypotheses(atlas, data, optical_residual)
    sar = develop_sar_p0_residual(hypotheses, data)
    cross = develop_cross_modal(hypotheses, sar)
    grounding, _ = build_grounding_interface()
    cases = select_and_render_cases(data, common, optical_residual, cross)
    write_visual_review_ledger()
    summary = write_mechanism_outputs(atlas, common, optical_residual, sar, cross, grounding, cases)
    freeze_manifest(summary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.all:
        raise SystemExit("use --all")
    run_all()


if __name__ == "__main__":
    main()
