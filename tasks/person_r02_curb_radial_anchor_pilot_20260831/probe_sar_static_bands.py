from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks, peak_prominences, peak_widths


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "person_r02_curb_radial_anchor_pilot_20260831"
OUT = WORKSPACE / "output" / "person_r02_curb_radial_anchor_pilot_20260831"
PRE = OUT / "pre_reference"
FIG = OUT / "figures"
REGISTRY = (
    WORKSPACE
    / "output"
    / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830"
    / "pre_reference"
    / "full_stream_frame_registry_pre_reference.parquet"
)
P1E_SCRIPT = (
    WORKSPACE
    / "tasks"
    / "person_physics_guided_image_domain_study_20260824"
    / "run_p1e_single_frame_position_specificity.py"
)

PRIMARY = list(range(421, 475))
CONTROLS = [0, 30, 60, 375, 390, 405, 414, 480, 486, 488]
D_GRID_M = np.arange(2.0, 15.0001, 0.05, dtype=np.float32)
THETA_GRID_DEG = np.arange(-50.0, 50.0001, 0.5, dtype=np.float32)
LOCAL_BACKGROUND_OFFSET_M = 0.40


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_bgr(path: Path) -> np.ndarray:
    arr = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        raise FileNotFoundError(path)
    return arr


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
    sampled = cv2.remap(
        field.astype(np.float32),
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=np.nan,
    )
    return sampled


def frame_profile(row: pd.Series, p1e) -> pd.DataFrame:
    image = read_bgr(Path(row.sar_image_path))
    jet, lut_distance = p1e.jet_proxy(image)
    cx = float(row.geometry_center_x_px)
    cy = float(row.geometry_center_y_px)
    px_per_m = float(row.geometry_radius_px) / float(row.geometry_outer_range_m)
    center = sample_horizontal_family(jet, cx, cy, px_per_m, D_GRID_M)
    low = sample_horizontal_family(jet, cx, cy, px_per_m, D_GRID_M - LOCAL_BACKGROUND_OFFSET_M)
    high = sample_horizontal_family(jet, cx, cy, px_per_m, D_GRID_M + LOCAL_BACKGROUND_OFFSET_M)
    local_max = np.maximum(low, high)
    response_median = np.nanmedian(center, axis=1)
    response_q75 = np.nanquantile(center, 0.75, axis=1)
    contrast_median = np.nanmedian(center - local_max, axis=1)
    coherence = np.nanmean(center > local_max + 0.01, axis=1)
    jpeg_lut_distance_median = float(np.median(lut_distance[np.any(image < 248, axis=2)]))
    return pd.DataFrame(
        {
            "run_id": "R02ZF",
            "sar_frame_index": int(row.sar_frame_index),
            "sar_timestamp_ms": int(row.sar_timestamp_ms),
            "d_parallel_m": D_GRID_M,
            "response_median": response_median,
            "response_q75": response_q75,
            "local_contrast_median": contrast_median,
            "theta_coherence_fraction": coherence,
            "jet_lut_distance_median": jpeg_lut_distance_median,
            "primary_window": int(row.sar_frame_index) in PRIMARY,
            "negative_control": int(row.sar_frame_index) in CONTROLS,
        }
    )


def aggregate_profile(profiles: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    stable = profiles[profiles.primary_window].copy()
    grouped = stable.groupby("d_parallel_m", sort=True)
    agg = grouped.agg(
        response_median=("response_median", "median"),
        response_q75=("response_q75", "median"),
        contrast_median=("local_contrast_median", "median"),
        contrast_p25=("local_contrast_median", lambda x: float(np.quantile(x, 0.25))),
        theta_coherence_median=("theta_coherence_fraction", "median"),
        theta_coherence_p25=("theta_coherence_fraction", lambda x: float(np.quantile(x, 0.25))),
        temporal_persistence=("local_contrast_median", lambda x: float(np.mean(np.asarray(x) > 0.01))),
        temporal_positive_fraction=("local_contrast_median", lambda x: float(np.mean(np.asarray(x) > 0.0))),
        temporal_contrast_iqr=("local_contrast_median", lambda x: float(np.quantile(x, 0.75) - np.quantile(x, 0.25))),
    ).reset_index()
    smooth = gaussian_filter1d(np.maximum(agg.contrast_median.to_numpy(float), 0.0), sigma=2.0)
    score = smooth * np.sqrt(
        np.clip(agg.temporal_persistence.to_numpy(float), 0.0, 1.0)
        * np.clip(agg.theta_coherence_median.to_numpy(float), 0.0, 1.0)
    )
    agg["contrast_smooth"] = smooth
    agg["persistence_coherence_score"] = score
    peaks, _ = find_peaks(score, distance=12, prominence=max(float(np.max(score)) * 0.03, 1e-6))
    if len(peaks) == 0:
        return agg, pd.DataFrame()
    prominences, left_bases, right_bases = peak_prominences(score, peaks)
    widths, _, left_ips, right_ips = peak_widths(score, peaks, rel_height=0.5)
    step = float(D_GRID_M[1] - D_GRID_M[0])
    candidates = []
    for peak, prominence, left_base, right_base, width, left_ip, right_ip in zip(
        peaks, prominences, left_bases, right_bases, widths, left_ips, right_ips
    ):
        candidates.append(
            {
                "candidate_id": f"STATIC_BAND_D{float(D_GRID_M[peak]):05.2f}",
                "d_parallel_peak_m": float(D_GRID_M[peak]),
                "score": float(score[peak]),
                "prominence": float(prominence),
                "half_prominence_low_m": float(D_GRID_M[0] + left_ip * step),
                "half_prominence_high_m": float(D_GRID_M[0] + right_ip * step),
                "half_prominence_width_m": float(width * step),
                "prominence_base_low_m": float(D_GRID_M[int(left_base)]),
                "prominence_base_high_m": float(D_GRID_M[int(right_base)]),
                "response_median": float(agg.response_median.iloc[peak]),
                "contrast_median": float(agg.contrast_median.iloc[peak]),
                "contrast_p25": float(agg.contrast_p25.iloc[peak]),
                "theta_coherence_median": float(agg.theta_coherence_median.iloc[peak]),
                "theta_coherence_p25": float(agg.theta_coherence_p25.iloc[peak]),
                "temporal_persistence": float(agg.temporal_persistence.iloc[peak]),
                "temporal_positive_fraction": float(agg.temporal_positive_fraction.iloc[peak]),
                "temporal_contrast_iqr": float(agg.temporal_contrast_iqr.iloc[peak]),
            }
        )
    candidate_frame = pd.DataFrame(candidates).sort_values(
        ["score", "prominence", "d_parallel_peak_m"], ascending=[False, False, True]
    )
    candidate_frame["score_rank"] = np.arange(1, len(candidate_frame) + 1)
    return agg, candidate_frame


def figure(agg: pd.DataFrame, candidates: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(13, 11), sharex=True, constrained_layout=True)
    axes[0].plot(agg.d_parallel_m, agg.response_median, label="median JET response")
    axes[0].plot(agg.d_parallel_m, agg.response_q75, label="median frame Q75 response", alpha=0.75)
    axes[0].legend()
    axes[0].set_ylabel("response")
    axes[1].plot(agg.d_parallel_m, agg.contrast_median, label="median local contrast")
    axes[1].plot(agg.d_parallel_m, agg.contrast_p25, label="P25 local contrast", alpha=0.8)
    axes[1].plot(agg.d_parallel_m, agg.contrast_smooth, label="positive smoothed contrast", lw=2)
    axes[1].axhline(0.0, color="black", lw=0.8)
    axes[1].legend()
    axes[1].set_ylabel("contrast")
    axes[2].plot(agg.d_parallel_m, agg.temporal_persistence, label="temporal persistence")
    axes[2].plot(agg.d_parallel_m, agg.theta_coherence_median, label="theta coherence median")
    score = agg.persistence_coherence_score
    axes[2].plot(agg.d_parallel_m, score / max(float(score.max()), 1e-9), label="normalized combined score", lw=2)
    for row in candidates.head(10).itertuples(index=False):
        for ax in axes:
            ax.axvline(row.d_parallel_peak_m, color="tab:red", alpha=0.28, lw=1)
        axes[2].text(row.d_parallel_peak_m, 0.03, str(row.score_rank), rotation=90, va="bottom", ha="right")
    axes[2].legend()
    axes[2].set_xlabel("parallel-line perpendicular distance d (m)")
    axes[2].set_ylabel("fraction / normalized score")
    fig.suptitle("R02ZF F421-F474 GT-blind static horizontal-band profile; no PERSON reference")
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "05_gt_blind_static_band_profile_probe.png", dpi=180)
    plt.close(fig)


def candidate_overlay_figure(registry: pd.DataFrame, candidates: pd.DataFrame) -> None:
    selected_frames = [390, 421, 435, 450, 462, 474, 480, 486]
    rows = registry[registry.sar_frame_index.isin(selected_frames)].set_index("sar_frame_index")
    colors = [(255, 255, 255), (0, 0, 255), (0, 255, 255)]
    top = list(candidates.head(3).itertuples(index=False))
    fig, axes = plt.subplots(4, 2, figsize=(15, 12), constrained_layout=True)
    for ax, frame_index in zip(axes.ravel(), selected_frames):
        row = rows.loc[frame_index]
        image = read_bgr(Path(row.sar_image_path))
        overlay = image.copy()
        px_per_m = float(row.geometry_radius_px) / float(row.geometry_outer_range_m)
        for color, candidate in zip(colors, top):
            y = int(round(float(row.geometry_center_y_px) - candidate.d_parallel_peak_m * px_per_m))
            cv2.line(overlay, (0, y), (overlay.shape[1] - 1, y), color, 2, cv2.LINE_AA)
            cv2.putText(
                overlay,
                f"rank{candidate.score_rank} d={candidate.d_parallel_peak_m:.2f}m",
                (12, max(24, y - 7)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
                cv2.LINE_AA,
            )
        ax.imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
        role = "PRIMARY" if frame_index in PRIMARY else "NEGATIVE CONTROL"
        ax.set_title(f"R02ZF SAR F{frame_index} | {role}")
        ax.axis("off")
    fig.suptitle("GT-blind persistent horizontal-band candidates; colors are hypotheses, not curb identity")
    fig.savefig(FIG / "06_static_band_candidate_overlays.png", dpi=180)
    plt.close(fig)


def temporal_heatmap(profiles: pd.DataFrame, candidates: pd.DataFrame) -> None:
    stable = profiles[profiles.primary_window].pivot(
        index="sar_frame_index", columns="d_parallel_m", values="local_contrast_median"
    )
    fig, ax = plt.subplots(figsize=(14, 6), constrained_layout=True)
    image = ax.imshow(
        stable.to_numpy(),
        aspect="auto",
        origin="lower",
        extent=[float(stable.columns.min()), float(stable.columns.max()), float(stable.index.min()), float(stable.index.max())],
        cmap="coolwarm",
        vmin=-0.025,
        vmax=0.025,
    )
    for row in candidates.head(3).itertuples(index=False):
        ax.axvline(row.d_parallel_peak_m, color="black", ls="--", alpha=0.65)
        ax.text(row.d_parallel_peak_m, float(stable.index.max()) + 0.3, f"rank{row.score_rank}", ha="center")
    ax.set_xlabel("parallel-line perpendicular distance d (m)")
    ax.set_ylabel("SAR frame index")
    ax.set_title("F421-F474 local horizontal-band contrast through time")
    fig.colorbar(image, ax=ax, label="median center-minus-local-background JET contrast")
    fig.savefig(FIG / "07_static_band_temporal_heatmap.png", dpi=180)
    plt.close(fig)


def main() -> None:
    p1e = load_module("person_curb0_p1e", P1E_SCRIPT)
    registry = pd.read_parquet(REGISTRY)
    registry = registry[
        registry.run_id.eq("R02ZF")
        & registry.sar_frame_index.isin(PRIMARY + CONTROLS)
    ].sort_values("sar_frame_index")
    all_profiles = []
    for index, row in enumerate(registry.itertuples(index=False), start=1):
        all_profiles.append(frame_profile(pd.Series(row._asdict()), p1e))
        if index % 10 == 0 or index == len(registry):
            print(f"profile {index}/{len(registry)}", flush=True)
    profiles = pd.concat(all_profiles, ignore_index=True)
    agg, candidates = aggregate_profile(profiles)
    profiles.to_parquet(PRE / "sar_static_band_frame_profiles_pre_reference.parquet", index=False, compression="zstd")
    agg.to_csv(PRE / "sar_static_band_aggregate_profile_pre_reference.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(PRE / "sar_static_band_candidates_probe_pre_reference.csv", index=False, encoding="utf-8-sig")
    figure(agg, candidates)
    candidate_overlay_figure(registry, candidates)
    temporal_heatmap(profiles, candidates)
    summary = {
        "primary_window": [421, 474],
        "negative_controls": CONTROLS,
        "d_grid_m": [float(D_GRID_M.min()), float(D_GRID_M.max()), float(D_GRID_M[1] - D_GRID_M[0])],
        "theta_grid_deg": [float(THETA_GRID_DEG.min()), float(THETA_GRID_DEG.max()), float(THETA_GRID_DEG[1] - THETA_GRID_DEG[0])],
        "local_background_offset_m": LOCAL_BACKGROUND_OFFSET_M,
        "candidate_count": int(len(candidates)),
        "top_candidates": candidates.head(10).to_dict(orient="records"),
        "manual_sar_reference_used": False,
        "r04_accessed": False,
        "semantics": "GT_BLIND_STATIC_HORIZONTAL_BAND_PROBE_NOT_PERSON_RESPONSE_OR_FINAL_LOCALIZATION",
    }
    (PRE / "sar_static_band_probe_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(candidates.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
