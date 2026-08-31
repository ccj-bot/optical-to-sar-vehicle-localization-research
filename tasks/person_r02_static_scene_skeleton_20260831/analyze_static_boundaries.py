from __future__ import annotations

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
from scipy.ndimage import gaussian_filter1d, median_filter


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "person_r02_static_scene_skeleton_20260831"
OUT = WORKSPACE / "output" / "person_r02_static_scene_skeleton_20260831"
PRE = OUT / "pre_reference"
FIG = OUT / "figures"
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

THETA_GRID_DEG = np.arange(-50.0, 50.0001, 1.0, dtype=np.float32)
D_GRID_M = np.arange(2.0, 15.0001, 0.05, dtype=np.float32)
BACKGROUND_OFFSET_M = 0.35
MIN_LOCAL_CONTRAST = 0.0100
BOUNDARIES = {
    "STATIC_BOUNDARY_A": {"nominal_m": 4.90, "low_m": 3.80, "high_m": 5.80, "color": "tab:cyan"},
    "STATIC_BOUNDARY_B": {"nominal_m": 7.10, "low_m": 6.00, "high_m": 8.30, "color": "tab:orange"},
    "STATIC_BOUNDARY_C": {"nominal_m": 12.40, "low_m": 10.60, "high_m": 14.20, "color": "magenta"},
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_bgr(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def sample_horizontal_family(
    field: np.ndarray,
    cx: float,
    cy: float,
    px_per_m: float,
    d_values: np.ndarray,
) -> np.ndarray:
    d = d_values[:, None].astype(np.float32)
    theta = np.deg2rad(THETA_GRID_DEG[None, :]).astype(np.float32)
    map_x = cx + d * px_per_m * np.tan(theta)
    map_y = np.broadcast_to(cy - d * px_per_m, map_x.shape).astype(np.float32)
    return cv2.remap(
        field.astype(np.float32),
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=np.nan,
    )


def ridge_width(d_values: np.ndarray, profile: np.ndarray, peak_index: int, peak_value: float) -> float:
    if not np.isfinite(peak_value) or peak_value <= 0:
        return float("nan")
    threshold = peak_value * 0.5
    left = peak_index
    right = peak_index
    while left > 0 and np.isfinite(profile[left - 1]) and profile[left - 1] >= threshold:
        left -= 1
    while right + 1 < len(profile) and np.isfinite(profile[right + 1]) and profile[right + 1] >= threshold:
        right += 1
    return float(d_values[right] - d_values[left] + (d_values[1] - d_values[0]))


def extract_frame(row: pd.Series, p1e) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    image = read_bgr(Path(row.sar_image_path))
    jet, _ = p1e.jet_proxy(image)
    cx = float(row.geometry_center_x_px)
    cy = float(row.geometry_center_y_px)
    px_per_m = float(row.geometry_radius_px) / float(row.geometry_outer_range_m)
    center = sample_horizontal_family(jet, cx, cy, px_per_m, D_GRID_M)
    low = sample_horizontal_family(jet, cx, cy, px_per_m, D_GRID_M - BACKGROUND_OFFSET_M)
    high = sample_horizontal_family(jet, cx, cy, px_per_m, D_GRID_M + BACKGROUND_OFFSET_M)
    contrast = center - np.maximum(low, high)
    contrast = gaussian_filter1d(np.nan_to_num(contrast, nan=-1.0), sigma=1.2, axis=0)
    curve_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for boundary_id, settings in BOUNDARIES.items():
        window = (D_GRID_M >= settings["low_m"]) & (D_GRID_M <= settings["high_m"])
        d_window = D_GRID_M[window]
        local = contrast[window]
        peak_indices = np.argmax(local, axis=0)
        peak_values = local[peak_indices, np.arange(local.shape[1])]
        d_raw = d_window[peak_indices].astype(float)
        d_smooth = median_filter(d_raw, size=7, mode="nearest")
        valid = np.isfinite(peak_values) & (peak_values >= MIN_LOCAL_CONTRAST)
        widths = np.array(
            [ridge_width(d_window, local[:, idx], int(peak_indices[idx]), float(peak_values[idx])) for idx in range(local.shape[1])],
            dtype=float,
        )
        for theta_index, theta in enumerate(THETA_GRID_DEG):
            curve_rows.append(
                {
                    "run_id": "R02ZF",
                    "sar_frame_index": int(row.sar_frame_index),
                    "sar_timestamp_ms": int(row.sar_timestamp_ms),
                    "boundary_id": boundary_id,
                    "theta_deg": float(theta),
                    "d_peak_raw_m": float(d_raw[theta_index]),
                    "d_peak_smooth_m": float(d_smooth[theta_index]),
                    "local_peak_contrast": float(peak_values[theta_index]),
                    "ridge_half_height_width_m": float(widths[theta_index]),
                    "available": bool(valid[theta_index]),
                    "manual_person_reference_used": False,
                }
            )
        central = np.abs(THETA_GRID_DEG) <= 45.0
        usable = valid & central
        values = d_smooth[usable]
        theta_values = THETA_GRID_DEG[usable]
        center_m = float(np.median(values)) if values.size else float("nan")
        summary_rows.append(
            {
                "run_id": "R02ZF",
                "sar_frame_index": int(row.sar_frame_index),
                "sar_timestamp_ms": int(row.sar_timestamp_ms),
                "boundary_id": boundary_id,
                "nominal_d_m": float(settings["nominal_m"]),
                "d_center_m": center_m,
                "d_curve_p90_absdev_m": float(np.quantile(np.abs(values - center_m), 0.90)) if values.size else float("nan"),
                "available_theta_fraction": float(np.mean(usable[central])),
                "median_local_peak_contrast": float(np.median(peak_values[usable])) if values.size else float("nan"),
                "median_response_thickness_m": float(np.nanmedian(widths[usable])) if values.size else float("nan"),
                "theta_extent_low_deg": float(theta_values.min()) if values.size else float("nan"),
                "theta_extent_high_deg": float(theta_values.max()) if values.size else float("nan"),
                "frame_available": bool(
                    values.size >= 20
                    and np.mean(usable[central]) >= 0.45
                    and np.quantile(np.abs(values - center_m), 0.90) <= 0.55
                ),
                "manual_person_reference_used": False,
            }
        )
    return curve_rows, summary_rows


def longest_true_run(frame_indices: np.ndarray, mask: np.ndarray) -> tuple[int | None, int | None, int]:
    best: tuple[int | None, int | None, int] = (None, None, 0)
    start: int | None = None
    previous: int | None = None
    for frame, keep in zip(frame_indices.astype(int), mask.astype(bool)):
        if keep and (start is None or previous is None or frame != previous + 1):
            start = frame
        if not keep and start is not None and previous is not None:
            length = previous - start + 1
            if length > best[2]:
                best = (start, previous, length)
            start = None
        previous = frame
    if start is not None and previous is not None:
        length = previous - start + 1
        if length > best[2]:
            best = (start, previous, length)
    return best


def build_pair_tables(curves: pd.DataFrame, summaries: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    a = curves[curves.boundary_id.eq("STATIC_BOUNDARY_A")].rename(
        columns={"d_peak_smooth_m": "d_a_m", "local_peak_contrast": "contrast_a", "available": "available_a"}
    )
    b = curves[curves.boundary_id.eq("STATIC_BOUNDARY_B")].rename(
        columns={"d_peak_smooth_m": "d_b_m", "local_peak_contrast": "contrast_b", "available": "available_b"}
    )
    keep = ["sar_frame_index", "theta_deg", "d_a_m", "contrast_a", "available_a"]
    pair = a[keep].merge(
        b[["sar_frame_index", "theta_deg", "d_b_m", "contrast_b", "available_b"]],
        on=["sar_frame_index", "theta_deg"],
        how="inner",
    )
    pair["both_available"] = pair.available_a & pair.available_b
    pair["delta_r_m"] = pair.d_b_m - pair.d_a_m
    pair["manual_person_reference_used"] = False
    summary_rows: list[dict[str, object]] = []
    availability = summaries.pivot(index="sar_frame_index", columns="boundary_id", values="frame_available")
    for frame_index, frame in pair.groupby("sar_frame_index", sort=True):
        central = frame.theta_deg.abs().le(45.0)
        valid = central & frame.both_available
        values = frame.loc[valid, "delta_r_m"].to_numpy(float)
        median = float(np.median(values)) if values.size else float("nan")
        summary_rows.append(
            {
                "run_id": "R02ZF",
                "sar_frame_index": int(frame_index),
                "sar_timestamp_ms": int(summaries[summaries.sar_frame_index.eq(frame_index)].sar_timestamp_ms.iloc[0]),
                "pair_id": "PARALLEL_BOUNDARY_PAIR_A_B",
                "theta_overlap_fraction": float(np.mean(valid[central])),
                "delta_r_median_m": median,
                "delta_r_p90_absdev_m": float(np.quantile(np.abs(values - median), 0.90)) if values.size else float("nan"),
                "delta_r_theta_p90_minus_p10_m": float(np.quantile(values, 0.90) - np.quantile(values, 0.10)) if values.size else float("nan"),
                "ordering_a_before_b_fraction": float(np.mean(values > 0)) if values.size else float("nan"),
                "pair_available": bool(
                    values.size >= 20
                    and np.mean(valid[central]) >= 0.25
                    and bool(availability.loc[int(frame_index), "STATIC_BOUNDARY_A"])
                    and bool(availability.loc[int(frame_index), "STATIC_BOUNDARY_B"])
                ),
                "manual_person_reference_used": False,
            }
        )
    return pair, pd.DataFrame(summary_rows)


def add_p0_residuals(summary: pd.DataFrame) -> pd.DataFrame:
    edges = pd.read_parquet(P0_EDGES)
    edges = edges[edges.run_id.eq("R02ZF")]
    transforms = (
        edges.groupby(["source_frame", "destination_frame"], as_index=False)
        .agg(
            p0_state=("p0_state", "first"),
            p0_model=("p0_model", "first"),
            translation_dx_px=("translation_dx_px", "median"),
            translation_dy_px=("translation_dy_px", "median"),
        )
        .sort_values("source_frame")
    )
    ppm = 591.340317 / 20.0
    centers = summary.pivot(index="sar_frame_index", columns="boundary_id", values="d_center_m")
    rows: list[dict[str, object]] = []
    for transform in transforms.itertuples(index=False):
        for boundary_id in BOUNDARIES:
            source = float(centers.loc[int(transform.source_frame), boundary_id])
            destination = float(centers.loc[int(transform.destination_frame), boundary_id])
            predicted_destination = source - float(transform.translation_dy_px) / ppm
            rows.append(
                {
                    "run_id": "R02ZF",
                    "source_frame": int(transform.source_frame),
                    "destination_frame": int(transform.destination_frame),
                    "boundary_id": boundary_id,
                    "source_d_center_m": source,
                    "destination_d_center_m": destination,
                    "p0_translation_dx_px": float(transform.translation_dx_px),
                    "p0_translation_dy_px": float(transform.translation_dy_px),
                    "p0_predicted_destination_d_m": predicted_destination,
                    "raw_adjacent_delta_m": destination - source,
                    "p0_compensated_residual_m": destination - predicted_destination,
                    "p0_state": str(transform.p0_state),
                    "p0_model": str(transform.p0_model),
                    "p0_semantics": "SAR_IMAGE_DOMAIN_COMMON_APPARENT_TRANSLATION_NOT_PHYSICAL_PLATFORM_MOTION",
                    "manual_person_reference_used": False,
                }
            )
    return pd.DataFrame(rows)


def summarize(summary: pd.DataFrame, pair_summary: pd.DataFrame, p0: pd.DataFrame) -> dict[str, object]:
    pair = pair_summary.sort_values("sar_frame_index").copy()
    eligible = (
        pair.pair_available
        & pair.delta_r_median_m.between(1.5, 3.0)
        & pair.delta_r_p90_absdev_m.le(0.55)
        & pair.ordering_a_before_b_fraction.ge(0.95)
    )
    stable_start, stable_end, stable_length = longest_true_run(pair.sar_frame_index.to_numpy(), eligible.to_numpy())
    stable = pair[pair.sar_frame_index.between(stable_start, stable_end)] if stable_start is not None else pair.iloc[0:0]
    boundary_stats: dict[str, object] = {}
    for boundary_id, group in summary.groupby("boundary_id"):
        available = group[group.frame_available]
        boundary_stats[boundary_id] = {
            "available_frames": int(group.frame_available.sum()),
            "total_frames": int(len(group)),
            "availability_fraction": float(group.frame_available.mean()),
            "median_d_center_m": float(available.d_center_m.median()) if len(available) else None,
            "p90_temporal_absdev_m": float(
                np.quantile(np.abs(available.d_center_m - available.d_center_m.median()), 0.90)
            ) if len(available) else None,
            "median_response_thickness_m": float(available.median_response_thickness_m.median()) if len(available) else None,
        }
    p0_stats: dict[str, object] = {}
    for boundary_id, group in p0.groupby("boundary_id"):
        p0_stats[boundary_id] = {
            "available_pairs": int(group.p0_compensated_residual_m.notna().sum()),
            "raw_adjacent_abs_delta_median": float(group.raw_adjacent_delta_m.abs().median()),
            "p0_compensated_abs_residual_median": float(group.p0_compensated_residual_m.abs().median()),
            "p0_compensated_abs_residual_p90": float(group.p0_compensated_residual_m.abs().quantile(0.90)),
        }
    return {
        "run_id": "R02ZF",
        "boundary_names_are_physical_identity_neutral": True,
        "boundary_stats_full_sequence": boundary_stats,
        "pair_available_frames": int(pair.pair_available.sum()),
        "pair_total_frames": int(len(pair)),
        "pair_availability_fraction": float(pair.pair_available.mean()),
        "pair_delta_r_median_m": float(pair.loc[pair.pair_available, "delta_r_median_m"].median()),
        "pair_delta_r_temporal_p90_absdev_m": float(
            np.quantile(
                np.abs(
                    pair.loc[pair.pair_available, "delta_r_median_m"]
                    - pair.loc[pair.pair_available, "delta_r_median_m"].median()
                ),
                0.90,
            )
        ),
        "pair_delta_r_median_theta_p90_absdev_m": float(
            pair.loc[pair.pair_available, "delta_r_p90_absdev_m"].median()
        ),
        "pair_ordering_a_before_b_median_fraction": float(
            pair.loc[pair.pair_available, "ordering_a_before_b_fraction"].median()
        ),
        "longest_stable_segment": [
            int(stable_start) if stable_start is not None else None,
            int(stable_end) if stable_end is not None else None,
        ],
        "longest_stable_segment_length": int(stable_length),
        "stable_segment_pair_delta_r_median_m": float(stable.delta_r_median_m.median()) if len(stable) else None,
        "stable_segment_pair_delta_r_p90_temporal_absdev_m": float(
            np.quantile(np.abs(stable.delta_r_median_m - stable.delta_r_median_m.median()), 0.90)
        ) if len(stable) else None,
        "p0_compensation": p0_stats,
        "pair_separation_is_invariant_to_common_p0_translation": True,
        "person_reference_used": False,
        "r04_accessed": False,
    }


def plot_results(summary: pd.DataFrame, pair_summary: pd.DataFrame, result: dict[str, object]) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(3, 1, figsize=(15, 11), sharex=True, constrained_layout=True)
    for boundary_id, settings in BOUNDARIES.items():
        group = summary[summary.boundary_id.eq(boundary_id)].sort_values("sar_frame_index")
        axes[0].plot(group.sar_frame_index, group.d_center_m, color=settings["color"], lw=1.0, label=boundary_id)
        axes[1].plot(group.sar_frame_index, group.available_theta_fraction, color=settings["color"], lw=1.0)
    axes[0].set_ylabel("median d(theta,t) [m]")
    axes[0].legend(ncol=3)
    axes[0].set_title("R02ZF neutral static-boundary trajectories; no PERSON reference")
    axes[1].set_ylabel("available theta fraction")
    axes[1].axhline(0.30, color="black", ls="--", lw=0.8)
    axes[2].plot(pair_summary.sar_frame_index, pair_summary.delta_r_median_m, color="tab:green", label="median B-A separation")
    axes[2].fill_between(
        pair_summary.sar_frame_index,
        pair_summary.delta_r_median_m - pair_summary.delta_r_p90_absdev_m,
        pair_summary.delta_r_median_m + pair_summary.delta_r_p90_absdev_m,
        color="tab:green",
        alpha=0.18,
        label="within-frame theta P90 absdev",
    )
    start, end = result["longest_stable_segment"]
    if start is not None:
        for ax in axes:
            ax.axvspan(start, end, color="gold", alpha=0.18)
    axes[2].set_ylabel("Delta_r B-A [m]")
    axes[2].set_xlabel("SAR frame index")
    axes[2].legend()
    fig.savefig(FIG / "01_static_boundary_full_sequence_and_pair_separation.png", dpi=180)
    plt.close(fig)


def overlay_core(registry: pd.DataFrame, curves: pd.DataFrame) -> None:
    selected = [183, 190, 200, 210, 225]
    colors = {
        "STATIC_BOUNDARY_A": (255, 255, 0),
        "STATIC_BOUNDARY_B": (0, 165, 255),
        "STATIC_BOUNDARY_C": (255, 0, 255),
    }
    tiles = []
    for frame_index in selected:
        row = registry[registry.sar_frame_index.eq(frame_index)].iloc[0]
        image = read_bgr(Path(row.sar_image_path))
        overlay = image.copy()
        px_per_m = float(row.geometry_radius_px) / float(row.geometry_outer_range_m)
        frame = curves[curves.sar_frame_index.eq(frame_index)]
        for boundary_id, group in frame.groupby("boundary_id"):
            points = []
            for item in group.sort_values("theta_deg").itertuples(index=False):
                theta = math.radians(float(item.theta_deg))
                d = float(item.d_peak_smooth_m)
                x = int(round(float(row.geometry_center_x_px) + d * px_per_m * math.tan(theta)))
                y = int(round(float(row.geometry_center_y_px) - d * px_per_m))
                if 0 <= x < overlay.shape[1] and 0 <= y < overlay.shape[0]:
                    points.append((x, y))
            if len(points) > 1:
                cv2.polylines(overlay, [np.asarray(points, dtype=np.int32)], False, colors[boundary_id], 2, cv2.LINE_AA)
        cv2.putText(
            overlay,
            f"SAR F{frame_index:03d} t={int(row.sar_timestamp_ms):06d}ms",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        tiles.append(cv2.resize(overlay, (768, 444)))
    canvas = np.vstack(tiles)
    ok, encoded = cv2.imencode(".png", canvas)
    if not ok:
        raise RuntimeError("overlay encode")
    encoded.tofile(FIG / "02_core_sar_boundary_curve_overlays.png")


def main() -> None:
    PRE.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    p1e = load_module("person_p1e_static_skeleton", P1E_SCRIPT)
    registry = pd.read_parquet(REGISTRY)
    registry = registry[registry.run_id.eq("R02ZF")].sort_values("sar_frame_index")
    curve_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for count, (_, row) in enumerate(registry.iterrows(), start=1):
        curves, summaries = extract_frame(row, p1e)
        curve_rows.extend(curves)
        summary_rows.extend(summaries)
        if count % 50 == 0:
            print(f"processed {count}/{len(registry)}", flush=True)
    curves = pd.DataFrame(curve_rows)
    summaries = pd.DataFrame(summary_rows)
    pair_curves, pair_summary = build_pair_tables(curves, summaries)
    p0 = add_p0_residuals(summaries)
    result = summarize(summaries, pair_summary, p0)
    curves.to_parquet(PRE / "static_boundary_theta_time_tracks_pre_reference.parquet", index=False)
    summaries.to_csv(PRE / "static_boundary_frame_summary_pre_reference.csv", index=False, encoding="utf-8-sig")
    summaries.to_parquet(PRE / "static_boundary_frame_summary_pre_reference.parquet", index=False)
    pair_curves.to_parquet(PRE / "parallel_boundary_pair_theta_time_pre_reference.parquet", index=False)
    pair_summary.to_csv(PRE / "parallel_boundary_pair_frame_summary_pre_reference.csv", index=False, encoding="utf-8-sig")
    pair_summary.to_parquet(PRE / "parallel_boundary_pair_frame_summary_pre_reference.parquet", index=False)
    p0.to_csv(PRE / "static_boundary_p0_compensation_audit_pre_reference.csv", index=False, encoding="utf-8-sig")
    p0.to_parquet(PRE / "static_boundary_p0_compensation_audit_pre_reference.parquet", index=False)
    (PRE / "static_boundary_analysis_summary_pre_reference.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    plot_results(summaries, pair_summary, result)
    overlay_core(registry, curves)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
