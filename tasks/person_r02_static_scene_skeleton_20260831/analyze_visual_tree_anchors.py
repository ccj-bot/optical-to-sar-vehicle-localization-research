from __future__ import annotations

import json
import math
import re
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import median_filter
from scipy.signal import find_peaks


WORKSPACE = Path(r"D:\profile\research\workspace")
OUT = WORKSPACE / "output" / "person_r02_static_scene_skeleton_20260831"
PRE = OUT / "pre_reference"
FIG = OUT / "figures" / "tree_anchor_review"
RAW_OPT = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\optical\R02ZF"
)
REGISTRY = (
    WORKSPACE
    / "output"
    / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830"
    / "pre_reference"
    / "full_stream_frame_registry_pre_reference.parquet"
)
Q95 = (
    WORKSPACE
    / "output"
    / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830"
    / "pre_reference"
    / "full_stream_q95_response_regions_pre_reference.parquet"
)
NAME_RE = re.compile(r"frame_(\d+)_t(\d+)ms\.jpg$", re.IGNORECASE)
MAPPING_A = 0.02666536443690682
MAPPING_B = -45.502258572693094

# Codex visual-development knots from true R02ZF optical frames. Each row follows
# one visibly distinct strapped roadside tree as it traverses right-to-left.
TREE_KNOTS = {
    "TREE_A_USER_F120": {
        "knots": {80: 3260.0, 100: 2210.0, 120: 1660.0, 140: 600.0},
        "frame_start": 80,
        "frame_end": 145,
        "core_user_tree": True,
        "color_bgr": (0, 255, 0),
    },
    "TREE_B_NEXT": {
        "knots": {120: 3950.0, 140: 2300.0, 160: 1850.0, 180: 950.0, 200: 100.0},
        "frame_start": 120,
        "frame_end": 200,
        "core_user_tree": False,
        "color_bgr": (0, 165, 255),
    },
    "TREE_C_NEXT": {
        "knots": {160: 3450.0, 180: 2850.0, 200: 2050.0, 220: 1400.0, 240: 500.0},
        "frame_start": 160,
        "frame_end": 240,
        "core_user_tree": False,
        "color_bgr": (255, 255, 0),
    },
}


def read_bgr(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def optical_inventory() -> pd.DataFrame:
    rows = []
    for path in sorted(RAW_OPT.glob("frame_*_t*ms.jpg")):
        match = NAME_RE.match(path.name)
        if match:
            rows.append(
                {
                    "optical_frame_index": int(match.group(1)),
                    "optical_timestamp_ms": int(match.group(2)),
                    "optical_image_path": str(path),
                }
            )
    return pd.DataFrame(rows)


def yellow_component_candidates(image: np.ndarray, predicted_x: float) -> list[dict[str, float]]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([12, 75, 90]), np.array([42, 255, 255]))
    spatial = np.zeros_like(mask)
    x0 = max(0, int(round(predicted_x - 220)))
    x1 = min(image.shape[1], int(round(predicted_x + 220)))
    spatial[430:930, x0:x1] = mask[430:930, x0:x1]
    spatial = cv2.morphologyEx(spatial, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, _, stats, centroids = cv2.connectedComponentsWithStats(spatial, connectivity=8)
    rows: list[dict[str, float]] = []
    for label in range(1, count):
        x, y, width, height, area = stats[label]
        cx, cy = centroids[label]
        if area < 18 or area > 3500 or width < 4 or height < 3:
            continue
        if not (430 <= cy <= 930):
            continue
        proximity = abs(float(cx) - predicted_x)
        if proximity > 200:
            continue
        shape_bonus = 0.0 if width >= height else 0.25
        cost = proximity / 80.0 + abs(float(cy) - 665.0) / 260.0 + shape_bonus - min(float(area), 800.0) / 1600.0
        rows.append(
            {
                "component_x_px": float(cx),
                "component_y_px": float(cy),
                "bbox_x_px": float(x),
                "bbox_y_px": float(y),
                "bbox_width_px": float(width),
                "bbox_height_px": float(height),
                "area_px": float(area),
                "detection_cost": float(cost),
            }
        )
    return sorted(rows, key=lambda row: row["detection_cost"])


def track_trees(inventory: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for tree_id, settings in TREE_KNOTS.items():
        knots = settings["knots"]
        interpolator = PchipInterpolator(np.array(list(knots.keys()), float), np.array(list(knots.values()), float))
        local = inventory[inventory.optical_frame_index.between(settings["frame_start"], settings["frame_end"])]
        raw_detections: list[dict[str, object]] = []
        for item in local.itertuples(index=False):
            predicted_x = float(interpolator(int(item.optical_frame_index)))
            image = read_bgr(Path(item.optical_image_path))
            candidates = yellow_component_candidates(image, predicted_x)
            if candidates:
                best = candidates[0]
                detected = float(best["component_x_px"])
                available = bool(abs(detected - predicted_x) <= 110.0 and best["detection_cost"] <= 2.2)
            else:
                best = {
                    "component_x_px": float("nan"),
                    "component_y_px": float("nan"),
                    "bbox_x_px": float("nan"),
                    "bbox_y_px": float("nan"),
                    "bbox_width_px": float("nan"),
                    "bbox_height_px": float("nan"),
                    "area_px": float("nan"),
                    "detection_cost": float("nan"),
                }
                detected = float("nan")
                available = False
            raw_detections.append(
                {
                    "run_id": "R02ZF",
                    "tree_id": tree_id,
                    "optical_frame_index": int(item.optical_frame_index),
                    "optical_timestamp_ms": int(item.optical_timestamp_ms),
                    "optical_image_path": str(item.optical_image_path),
                    "rough_visual_x_px": predicted_x,
                    "detected_yellow_x_px": detected,
                    "track_available_raw": available,
                    "manual_knot_frame": int(item.optical_frame_index) in knots,
                    "manual_knot_x_px": float(knots.get(int(item.optical_frame_index), float("nan"))),
                    "core_user_tree": bool(settings["core_user_tree"]),
                    **best,
                }
            )
        frame = pd.DataFrame(raw_detections)
        available_values = frame.detected_yellow_x_px.where(frame.track_available_raw)
        smooth_input = available_values.interpolate(limit=3, limit_direction="both").to_numpy(float)
        if np.isfinite(smooth_input).sum() >= 5:
            smooth = median_filter(smooth_input, size=5, mode="nearest")
        else:
            smooth = frame.rough_visual_x_px.to_numpy(float)
        frame["optical_x_px"] = np.where(frame.track_available_raw, smooth, np.nan)
        frame["theta_pred_deg"] = MAPPING_A * frame.optical_x_px + MAPPING_B
        frame["optical_axis_uncertainty_px"] = 45.0
        frame["theta_prediction_uncertainty_deg"] = abs(MAPPING_A) * 45.0
        frame["track_available"] = frame.track_available_raw & frame.optical_x_px.notna()
        frame["semantic_state"] = "VISUAL_DEVELOPMENT_STATIC_ANCHOR"
        frame["manual_person_reference_used"] = False
        rows.extend(frame.to_dict("records"))
    return pd.DataFrame(rows)


def q95_centers() -> pd.DataFrame:
    q95 = pd.read_parquet(Q95)
    q95 = q95[q95.run_id.eq("R02ZF")].copy().rename(columns={"frame_index": "sar_frame_index"})
    registry = pd.read_parquet(REGISTRY)
    registry = registry[registry.run_id.eq("R02ZF")][
        [
            "sar_frame_index",
            "sar_timestamp_ms",
            "geometry_center_x_px",
            "geometry_center_y_px",
            "geometry_radius_px",
            "geometry_outer_range_m",
        ]
    ]
    q95 = q95.merge(registry, on="sar_frame_index", how="left")
    dx = q95.centroid_x_px_shape_descriptor - q95.geometry_center_x_px
    dy = q95.geometry_center_y_px - q95.centroid_y_px_shape_descriptor
    px_per_m = q95.geometry_radius_px / q95.geometry_outer_range_m
    q95["theta_center_deg"] = np.degrees(np.arctan2(dx, dy))
    q95["range_center_m"] = np.hypot(dx, dy) / px_per_m
    q95["compact_point_like"] = (
        q95.structure_state.eq("COMPACT_OR_UNRESOLVED_SHAPE")
        & q95.major_extent_m.le(1.8)
        & q95.minor_extent_m.le(1.0)
        & q95.elongation.le(3.5)
        & q95.pixel_count.le(1500)
    )
    return q95


def interpolate_to_sar(tracks: pd.DataFrame) -> pd.DataFrame:
    registry = pd.read_parquet(REGISTRY)
    registry = registry[registry.run_id.eq("R02ZF")][["sar_frame_index", "sar_timestamp_ms"]]
    rows: list[dict[str, object]] = []
    for tree_id, frame in tracks[tracks.track_available].groupby("tree_id"):
        frame = frame.sort_values("optical_timestamp_ms")
        if len(frame) < 10:
            continue
        local = registry[registry.sar_timestamp_ms.between(frame.optical_timestamp_ms.min(), frame.optical_timestamp_ms.max())]
        x = np.interp(
            local.sar_timestamp_ms.to_numpy(float),
            frame.optical_timestamp_ms.to_numpy(float),
            frame.optical_x_px.to_numpy(float),
        )
        for item, optical_x in zip(local.itertuples(index=False), x):
            rows.append(
                {
                    "run_id": "R02ZF",
                    "tree_id": tree_id,
                    "sar_frame_index": int(item.sar_frame_index),
                    "sar_timestamp_ms": int(item.sar_timestamp_ms),
                    "optical_x_interp_px": float(optical_x),
                    "theta_pred_deg": float(MAPPING_A * optical_x + MAPPING_B),
                    "theta_prediction_uncertainty_deg": abs(MAPPING_A) * 45.0,
                    "sync_status": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
                    "manual_person_reference_used": False,
                }
            )
    return pd.DataFrame(rows)


def range_competition(predictions: pd.DataFrame, q95: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    score_rows: list[dict[str, object]] = []
    for tree_id, pred in predictions.groupby("tree_id"):
        merged = q95.merge(pred, on=["run_id", "sar_frame_index", "sar_timestamp_ms"], how="inner")
        merged["theta_residual_deg"] = merged.theta_center_deg - merged.theta_pred_deg
        merged = merged[
            merged.compact_point_like
            & merged.theta_residual_deg.abs().le(5.0)
            & merged.range_center_m.between(3.0, 19.5)
        ]
        for center in np.arange(3.5, 19.01, 0.25):
            selected = []
            local = merged[merged.range_center_m.between(center - 0.85, center + 0.85)]
            for _, frame in local.groupby("sar_frame_index"):
                frame = frame.copy()
                frame["cost"] = frame.theta_residual_deg.abs() + 0.20 * (frame.range_center_m - center).abs()
                selected.append(frame.sort_values(["cost", "score_max"], ascending=[True, False]).iloc[0])
            selected_frame = pd.DataFrame(selected)
            if len(selected_frame):
                persistence = selected_frame.sar_frame_index.nunique() / pred.sar_frame_index.nunique()
                median_abs = float(selected_frame.theta_residual_deg.abs().median())
                p90_abs = float(selected_frame.theta_residual_deg.abs().quantile(0.90))
                range_iqr = float(selected_frame.range_center_m.quantile(0.75) - selected_frame.range_center_m.quantile(0.25))
                score = float(persistence / (1.0 + median_abs + 0.35 * range_iqr))
            else:
                persistence = 0.0
                median_abs = p90_abs = range_iqr = float("nan")
                score = 0.0
            score_rows.append(
                {
                    "run_id": "R02ZF",
                    "tree_id": tree_id,
                    "range_hypothesis_center_m": float(center),
                    "available_sar_frames": int(pred.sar_frame_index.nunique()),
                    "matched_frames": int(len(selected_frame)),
                    "persistence_fraction": float(persistence),
                    "median_abs_theta_residual_deg": median_abs,
                    "p90_abs_theta_residual_deg": p90_abs,
                    "matched_range_iqr_m": range_iqr,
                    "trajectory_score": score,
                    "manual_person_reference_used": False,
                }
            )
    grid = pd.DataFrame(score_rows)
    winner_rows: list[dict[str, object]] = []
    for tree_id, group in grid.groupby("tree_id"):
        peaks, _ = find_peaks(group.trajectory_score.to_numpy(float), distance=4)
        candidates = group.iloc[peaks].sort_values("trajectory_score", ascending=False) if len(peaks) else group.nlargest(10, "trajectory_score")
        selected_centers = []
        for item in candidates.itertuples(index=False):
            if all(abs(item.range_hypothesis_center_m - center) >= 1.0 for center in selected_centers):
                selected_centers.append(float(item.range_hypothesis_center_m))
                row = item._asdict()
                row["competition_rank"] = len(selected_centers)
                winner_rows.append(row)
            if len(selected_centers) == 3:
                break
    winners = pd.DataFrame(winner_rows)
    detail_rows: list[dict[str, object]] = []
    for item in winners.itertuples(index=False):
        pred = predictions[predictions.tree_id.eq(item.tree_id)]
        merged = q95.merge(pred, on=["run_id", "sar_frame_index", "sar_timestamp_ms"], how="inner")
        merged["theta_residual_deg"] = merged.theta_center_deg - merged.theta_pred_deg
        merged = merged[
            merged.compact_point_like
            & merged.theta_residual_deg.abs().le(5.0)
            & merged.range_center_m.between(item.range_hypothesis_center_m - 0.85, item.range_hypothesis_center_m + 0.85)
        ]
        for _, frame in merged.groupby("sar_frame_index"):
            frame = frame.copy()
            frame["cost"] = frame.theta_residual_deg.abs() + 0.20 * (frame.range_center_m - item.range_hypothesis_center_m).abs()
            chosen = frame.sort_values(["cost", "score_max"], ascending=[True, False]).iloc[0]
            detail_rows.append(
                {
                    "run_id": "R02ZF",
                    "tree_id": item.tree_id,
                    "competition_rank": int(item.competition_rank),
                    "range_hypothesis_center_m": float(item.range_hypothesis_center_m),
                    "sar_frame_index": int(chosen.sar_frame_index),
                    "sar_timestamp_ms": int(chosen.sar_timestamp_ms),
                    "region_id": str(chosen.region_id),
                    "theta_pred_deg": float(chosen.theta_pred_deg),
                    "theta_sar_deg": float(chosen.theta_center_deg),
                    "theta_residual_deg": float(chosen.theta_residual_deg),
                    "range_sar_m": float(chosen.range_center_m),
                    "score_max": float(chosen.score_max),
                    "manual_person_reference_used": False,
                }
            )
    detail = pd.DataFrame(detail_rows)
    winners["anchor_verdict"] = np.where(
        winners.available_sar_frames.ge(30)
        & winners.matched_frames.ge(25)
        & winners.persistence_fraction.ge(0.45)
        & winners.median_abs_theta_residual_deg.le(1.5)
        & winners.p90_abs_theta_residual_deg.le(3.0)
        & winners.matched_range_iqr_m.le(1.5),
        "STATIC_AZIMUTH_ANCHOR_CANDIDATE",
        "VISUAL_CANDIDATE_NOT_TEMPORALLY_CONFIRMED",
    )
    return grid, winners, detail


def mapping_diagnostic(winners: pd.DataFrame, detail: pd.DataFrame) -> tuple[dict[str, object], pd.DataFrame]:
    accepted = winners[
        winners.competition_rank.eq(1) & winners.anchor_verdict.eq("STATIC_AZIMUTH_ANCHOR_CANDIDATE")
    ]
    selected = detail[
        detail.competition_rank.eq(1) & detail.tree_id.isin(accepted.tree_id)
    ]
    loo_rows = []
    if len(accepted) >= 3:
        for held in sorted(accepted.tree_id.unique()):
            train = selected[~selected.tree_id.eq(held)]
            test = selected[selected.tree_id.eq(held)]
            x_train = (train.theta_pred_deg - MAPPING_B) / MAPPING_A
            x_test = (test.theta_pred_deg - MAPPING_B) / MAPPING_A
            fit = np.polyfit(x_train, train.theta_sar_deg, 1)
            residual = test.theta_sar_deg.to_numpy(float) - (fit[0] * x_test.to_numpy(float) + fit[1])
            loo_rows.append(
                {
                    "held_out_tree_id": held,
                    "train_tree_count": int(train.tree_id.nunique()),
                    "fit_slope_deg_per_px": float(fit[0]),
                    "fit_intercept_deg": float(fit[1]),
                    "held_out_median_abs_residual_deg": float(np.median(np.abs(residual))),
                    "held_out_p90_abs_residual_deg": float(np.quantile(np.abs(residual), 0.90)),
                    "manual_person_reference_used": False,
                }
            )
    loo = pd.DataFrame(loo_rows)
    if len(selected):
        x = (selected.theta_pred_deg - MAPPING_B) / MAPPING_A
        fit = np.polyfit(x, selected.theta_sar_deg, 1)
        median_error = float(selected.theta_residual_deg.median())
        p90_abs = float(selected.theta_residual_deg.abs().quantile(0.90))
        delta_a = float(fit[0] - MAPPING_A)
        delta_b = float(fit[1] - MAPPING_B)
    else:
        fit = [float("nan"), float("nan")]
        median_error = p90_abs = delta_a = delta_b = float("nan")
    if len(accepted) < 3:
        mapping_verdict = "STATIC_ANCHORS_INSUFFICIENT_TO_JUDGE"
    elif loo.held_out_median_abs_residual_deg.max() > 2.0:
        mapping_verdict = "INCONSISTENT"
    elif abs(delta_a) > 0.0015:
        mapping_verdict = "REQUIRES_LINEAR_CORRECTION"
    elif abs(median_error) > 0.75:
        mapping_verdict = "CONSISTENT_UP_TO_SMALL_OFFSET"
    else:
        mapping_verdict = "CONSISTENT_WITH_STATIC_SCENE_ANCHORS"
    return {
        "accepted_static_anchor_count": int(len(accepted)),
        "accepted_static_anchor_ids": sorted(accepted.tree_id.astype(str).tolist()),
        "median_theta_residual_deg": median_error,
        "p90_abs_theta_residual_deg": p90_abs,
        "diagnostic_fit_slope_deg_per_px": float(fit[0]),
        "diagnostic_fit_intercept_deg": float(fit[1]),
        "diagnostic_delta_a_deg_per_px": delta_a,
        "diagnostic_delta_b_deg": delta_b,
        "leave_one_anchor_out_available": bool(len(loo) >= 3),
        "current_azimuth_mapping_verdict": mapping_verdict,
        "mapping_update_authorized": False,
        "person_reference_used": False,
        "r04_accessed": False,
    }, loo


def render_track_contact_sheets(tracks: pd.DataFrame) -> None:
    for tree_id, frame in tracks.groupby("tree_id"):
        tiles = []
        settings = TREE_KNOTS[tree_id]
        for item in frame.iloc[::5].itertuples(index=False):
            image = read_bgr(Path(item.optical_image_path))
            overlay = image.copy()
            rough_x = int(round(item.rough_visual_x_px))
            cv2.line(overlay, (rough_x, 400), (rough_x, 950), (255, 0, 255), 5, cv2.LINE_AA)
            if item.track_available:
                x = int(round(item.optical_x_px))
                cv2.line(overlay, (x, 400), (x, 950), settings["color_bgr"], 8, cv2.LINE_AA)
                cv2.rectangle(
                    overlay,
                    (int(item.bbox_x_px), int(item.bbox_y_px)),
                    (int(item.bbox_x_px + item.bbox_width_px), int(item.bbox_y_px + item.bbox_height_px)),
                    settings["color_bgr"],
                    5,
                )
            cv2.putText(overlay, f"{tree_id} OPT F{item.optical_frame_index:03d}", (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3, cv2.LINE_AA)
            tiles.append(cv2.resize(overlay, (820, 432)))
        rows = []
        for start in range(0, len(tiles), 3):
            row = tiles[start : start + 3]
            row.extend([np.full_like(tiles[0], 245)] * (3 - len(row)))
            rows.append(np.hstack(row))
        canvas = np.vstack(rows)
        ok, encoded = cv2.imencode(".png", canvas)
        if not ok:
            raise RuntimeError(tree_id)
        encoded.tofile(FIG / f"06_{tree_id}_optical_yellow_strap_track_every5.png")


def plot_results(tracks: pd.DataFrame, grid: pd.DataFrame, detail: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(16, 13), constrained_layout=True)
    for index, tree_id in enumerate(TREE_KNOTS):
        frame = tracks[tracks.tree_id.eq(tree_id)]
        available = frame[frame.track_available]
        axes[index, 0].plot(frame.optical_frame_index, frame.rough_visual_x_px, color="tab:gray", label="manual-knot PCHIP")
        axes[index, 0].scatter(available.optical_frame_index, available.optical_x_px, s=10, color="tab:green", label="yellow strap detection")
        axes[index, 0].legend()
        axes[index, 0].set_title(tree_id)
        axes[index, 0].set_ylabel("optical x [px]")
        score = grid[grid.tree_id.eq(tree_id)]
        axes[index, 1].plot(score.range_hypothesis_center_m, score.trajectory_score)
        axes[index, 1].set_ylabel("matched trajectory score")
        axes[index, 1].set_xlabel("SAR range competitor [m]")
    axes[-1, 0].set_xlabel("optical frame index")
    fig.savefig(FIG / "07_tree_tracks_and_sar_range_competition.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(15, 11), sharex=False, constrained_layout=True)
    for ax, tree_id in zip(axes, TREE_KNOTS):
        local = detail[detail.tree_id.eq(tree_id)]
        for rank, group in local.groupby("competition_rank"):
            ax.plot(group.sar_frame_index, group.theta_residual_deg, marker=".", lw=0.9, label=f"rank {rank} @ {group.range_hypothesis_center_m.median():.2f}m")
        ax.axhline(0, color="black", lw=0.8)
        ax.set_ylabel("theta residual [deg]")
        ax.set_title(tree_id)
        ax.legend(ncol=3)
    axes[-1].set_xlabel("SAR frame index")
    fig.savefig(FIG / "08_tree_sar_competitor_residuals.png", dpi=180)
    plt.close(fig)


def main() -> None:
    PRE.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    inventory = optical_inventory()
    tracks = track_trees(inventory)
    predictions = interpolate_to_sar(tracks)
    q95 = q95_centers()
    grid, winners, detail = range_competition(predictions, q95)
    mapping, loo = mapping_diagnostic(winners, detail)
    knot_rows = []
    for tree_id, settings in TREE_KNOTS.items():
        for frame_index, x in settings["knots"].items():
            knot_rows.append(
                {
                    "tree_id": tree_id,
                    "optical_frame_index": frame_index,
                    "optical_x_px": x,
                    "selection_semantics": "CODEX_VISUAL_DEVELOPMENT_MANUAL_KNOT_NO_PERSON_REFERENCE",
                }
            )
    pd.DataFrame(knot_rows).to_csv(PRE / "tree_visual_manual_knot_ledger_pre_reference.csv", index=False, encoding="utf-8-sig")
    tracks.to_csv(PRE / "tree_visual_yellow_strap_tracks_pre_reference.csv", index=False, encoding="utf-8-sig")
    tracks.to_parquet(PRE / "tree_visual_yellow_strap_tracks_pre_reference.parquet", index=False)
    predictions.to_csv(PRE / "tree_theta_predictions_to_sar_pre_reference.csv", index=False, encoding="utf-8-sig")
    predictions.to_parquet(PRE / "tree_theta_predictions_to_sar_pre_reference.parquet", index=False)
    grid.to_csv(PRE / "tree_sar_range_competition_grid_pre_reference.csv", index=False, encoding="utf-8-sig")
    winners.to_csv(PRE / "tree_sar_competition_winners_pre_reference.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(PRE / "tree_sar_competitor_trajectories_pre_reference.csv", index=False, encoding="utf-8-sig")
    detail.to_parquet(PRE / "tree_sar_competitor_trajectories_pre_reference.parquet", index=False)
    loo.to_csv(PRE / "tree_static_anchor_leave_one_out_pre_reference.csv", index=False, encoding="utf-8-sig")
    (PRE / "tree_static_anchor_mapping_summary_pre_reference.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    render_track_contact_sheets(tracks)
    plot_results(tracks, grid, detail)
    print(tracks.groupby("tree_id").track_available.agg(["sum", "count"]).to_string())
    print(winners.to_string(index=False))
    print(json.dumps(mapping, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
