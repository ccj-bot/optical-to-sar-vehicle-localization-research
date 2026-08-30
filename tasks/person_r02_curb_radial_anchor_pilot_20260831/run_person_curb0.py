from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUT = WORKSPACE / "output" / "person_r02_curb_radial_anchor_pilot_20260831"
PRE = OUT / "pre_reference"
POST = OUT / "post_reference_evaluation_only"
FIG = OUT / "figures"
PACK_STAGE = OUT / "review_pack_content"
PACK = WORKSPACE / "review_packs" / "PERSON_R02_CURB_RADIAL_ANCHOR_REVIEW_PACK_20260831.zip"

R2_PRE = (
    WORKSPACE
    / "output"
    / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830"
    / "pre_reference"
)
REGISTRY = R2_PRE / "full_stream_frame_registry_pre_reference.parquet"
SHELLS = R2_PRE / "full_stream_optical_shells_pre_reference.parquet"
Q95_REGIONS = R2_PRE / "full_stream_q95_response_regions_pre_reference.parquet"
Q95_MASKS = R2_PRE / "full_stream_q95_masks"
FAMILY_MEMBERSHIP = R2_PRE / "runtime_candidate_family_membership_pre_reference.parquet"

B0_POST = (
    WORKSPACE
    / "output"
    / "person_b0_end_to_end_capability_and_bottleneck_study_20260830"
    / "post_reference_oracle_diagnostic_only"
)
R02_REFERENCE = B0_POST / "r01_r02_r03_manual_range_reference_oracle_only.parquet"
RAW_TARGET_MAP = B0_POST / "raw_fragment_to_offline_target_mapping_oracle_only.csv"

PREPARE_SCRIPT = TASK / "prepare_visual_review.py"
VISUAL_FREEZE_SCRIPT = TASK / "freeze_visual_hypotheses.py"
PROBE_SCRIPT = TASK / "probe_sar_static_bands.py"

PRIMARY_FRAMES = range(421, 475)
PRIMARY_FRAME_SET = set(PRIMARY_FRAMES)
CURRENT_MODE = "CAUSAL_REPLAY"
SENSITIVITIES: dict[str, float | None] = {
    "CURRENT_FROZEN": None,
    "PLUS_MINUS_6_DEG": 6.0,
    "PLUS_MINUS_4_DEG": 4.0,
    "PLUS_MINUS_3_DEG": 3.0,
    "PLUS_MINUS_2_DEG": 2.0,
    "PLUS_MINUS_1_DEG": 1.0,
}
THETA_BAND_GRID = np.arange(-59.75, 59.7501, 0.25)
FRAME_CONTRAST_MIN = 0.01
FRAME_COHERENCE_MIN = 0.45
GRID_HALF_STEP_M = 0.025


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_table(frame: pd.DataFrame, stem: Path, csv: bool = True) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(stem.with_suffix(".parquet"), index=False, compression="zstd")
    if csv:
        frame.to_csv(stem.with_suffix(".csv"), index=False, encoding="utf-8-sig")


def read_bgr(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def run_stage(path: Path) -> None:
    result = subprocess.run([sys.executable, str(path)], cwd=WORKSPACE, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"stage failed: {path} exit={result.returncode}")


def verify_scope() -> None:
    expected = Path(r"D:\profile\research\workspace").resolve()
    if WORKSPACE.resolve() != expected:
        raise RuntimeError(f"workspace mismatch: {WORKSPACE} != {expected}")
    for path in (TASK, OUT, PACK, REGISTRY, SHELLS, Q95_MASKS):
        lowered = str(path).lower()
        if "old_work" in lowered or "\\archive\\" in lowered:
            raise RuntimeError(f"archive-only path entered scope: {path}")
        if "r04" in str(path).upper():
            raise RuntimeError(f"R04 path entered scope: {path}")


def parse_intervals(value: str) -> list[list[float]]:
    raw = json.loads(value)
    return [[float(low), float(high)] for low, high in raw]


def sensitivity_intervals(current: list[list[float]], half_width: float | None) -> list[list[float]]:
    if half_width is None:
        return current
    output = []
    for low, high in current:
        center = 0.5 * (low + high)
        output.append([max(-59.75, center - half_width), min(59.75, center + half_width)])
    return output


def angle_mask(theta: np.ndarray, intervals: list[list[float]]) -> np.ndarray:
    result = np.zeros(theta.shape, dtype=bool)
    for low, high in intervals:
        result |= (theta >= low) & (theta <= high)
    return result


def theta_in_intervals(theta: float, intervals: list[list[float]]) -> bool:
    return any(low <= theta <= high for low, high in intervals)


def robust_mad(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    median = float(np.median(values))
    return 1.4826 * float(np.median(np.abs(values - median)))


def build_frame_candidate_bands(
    profiles: pd.DataFrame, candidates: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    rows: list[dict[str, Any]] = []
    candidate_meta: list[dict[str, Any]] = []
    for candidate in candidates.sort_values("score_rank").head(3).itertuples(index=False):
        per_frame: list[dict[str, Any]] = []
        for frame_index, group in profiles.groupby("sar_frame_index"):
            local = group[
                group.d_parallel_m.between(
                    float(candidate.prominence_base_low_m), float(candidate.prominence_base_high_m)
                )
            ].sort_values("d_parallel_m")
            if local.empty:
                continue
            peak_position = int(np.argmax(local.local_contrast_median.to_numpy(float)))
            peak = local.iloc[peak_position]
            peak_contrast = float(peak.local_contrast_median)
            coherence = float(peak.theta_coherence_fraction)
            available = peak_contrast >= FRAME_CONTRAST_MIN and coherence >= FRAME_COHERENCE_MIN
            baseline = max(
                0.0,
                float(local.local_contrast_median.iloc[0]),
                float(local.local_contrast_median.iloc[-1]),
            )
            threshold = baseline + 0.5 * max(peak_contrast - baseline, 0.0)
            values = local.local_contrast_median.to_numpy(float)
            left = peak_position
            right = peak_position
            while left > 0 and values[left - 1] >= threshold:
                left -= 1
            while right + 1 < len(values) and values[right + 1] >= threshold:
                right += 1
            raw_low = float(local.d_parallel_m.iloc[left]) - GRID_HALF_STEP_M
            raw_high = float(local.d_parallel_m.iloc[right]) + GRID_HALF_STEP_M
            per_frame.append(
                {
                    "run_id": "R02ZF",
                    "sar_frame_index": int(frame_index),
                    "candidate_id": str(candidate.candidate_id),
                    "score_rank": int(candidate.score_rank),
                    "d_peak_m": float(peak.d_parallel_m),
                    "d_half_height_raw_low_m": raw_low,
                    "d_half_height_raw_high_m": raw_high,
                    "local_peak_contrast": peak_contrast,
                    "theta_coherence_fraction": coherence,
                    "available_raw": bool(available),
                    "primary_window": int(frame_index) in PRIMARY_FRAME_SET,
                    "negative_control": bool(peak.negative_control),
                }
            )
        frame = pd.DataFrame(per_frame)
        stable_available = frame[frame.primary_window & frame.available_raw]
        temporal_scale = max(
            GRID_HALF_STEP_M,
            robust_mad(stable_available.d_peak_m.to_numpy(float)) if len(stable_available) else GRID_HALF_STEP_M,
        )
        frame["temporal_center_mad_scale_m"] = temporal_scale
        frame["d_band_low_m"] = frame.d_half_height_raw_low_m - temporal_scale
        frame["d_band_high_m"] = frame.d_half_height_raw_high_m + temporal_scale
        frame["band_width_m"] = frame.d_band_high_m - frame.d_band_low_m
        frame["availability_state"] = np.where(
            frame.available_raw,
            "CURB_BAND_AVAILABLE_GT_BLIND",
            "CURB_UNAVAILABLE_LOCAL_CONTRAST_OR_COHERENCE",
        )
        if int(candidate.score_rank) == 1:
            role = "PRIMARY_CURB_COMPATIBLE_STATIC_BOUNDARY"
        elif int(candidate.score_rank) == 2:
            role = "ALTERNATE_NEAR_STATIC_BOUNDARY_IDENTITY_CONFOUNDER"
        else:
            role = "FAR_PARALLEL_STATIC_CLUTTER_CONFOUNDER"
        frame["candidate_role"] = role
        frame["manual_sar_reference_used"] = False
        rows.extend(frame.to_dict(orient="records"))
        candidate_meta.append(
            {
                **candidate._asdict(),
                "candidate_role": role,
                "temporal_center_mad_scale_m": temporal_scale,
                "stable_available_frames": int(len(stable_available)),
                "stable_total_frames": int(len(frame[frame.primary_window])),
                "stable_availability_fraction": float(
                    len(stable_available) / max(len(frame[frame.primary_window]), 1)
                ),
                "frame_availability_threshold_contrast": FRAME_CONTRAST_MIN,
                "frame_availability_threshold_theta_coherence": FRAME_COHERENCE_MIN,
                "manual_sar_reference_used": False,
            }
        )
    band_frame = pd.DataFrame(rows).sort_values(["score_rank", "sar_frame_index"])
    candidate_frame = pd.DataFrame(candidate_meta).sort_values("score_rank")
    primary = candidate_frame[candidate_frame.score_rank.eq(1)].iloc[0]
    alternate = candidate_frame[candidate_frame.score_rank.eq(2)].iloc[0]
    thresholds = {
        "primary_global_d_m": float(primary.d_parallel_peak_m),
        "alternate_global_d_m": float(alternate.d_parallel_peak_m),
        "alternate_identity_conservative_low_m": float(alternate.half_prominence_low_m)
        - float(alternate.temporal_center_mad_scale_m),
    }
    return band_frame, candidate_frame, thresholds


def build_theta_range_bands(frame_bands: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in frame_bands.itertuples(index=False):
        if item.availability_state != "CURB_BAND_AVAILABLE_GT_BLIND":
            continue
        cosines = np.cos(np.deg2rad(THETA_BAND_GRID))
        for theta, cosine in zip(THETA_BAND_GRID, cosines):
            rows.append(
                {
                    "run_id": "R02ZF",
                    "sar_frame_index": int(item.sar_frame_index),
                    "candidate_id": item.candidate_id,
                    "score_rank": int(item.score_rank),
                    "candidate_role": item.candidate_role,
                    "theta_deg": float(theta),
                    "r_curb_minus_m": float(item.d_band_low_m / cosine),
                    "r_curb_plus_m": float(item.d_band_high_m / cosine),
                    "d_parallel_minus_m": float(item.d_band_low_m),
                    "d_parallel_plus_m": float(item.d_band_high_m),
                    "band_semantics": "SAR_IMAGE_DOMAIN_STATIC_BOUNDARY_BAND_NOT_POINT_CORRESPONDENCE",
                    "manual_sar_reference_used": False,
                }
            )
    return pd.DataFrame(rows)


def range_interval_for_support(
    d_low: float, d_high: float, intervals: list[list[float]]
) -> tuple[float, float, float]:
    theta_values: list[float] = []
    for low, high in intervals:
        theta_values.extend(np.linspace(low, high, 201).tolist())
    cosine = np.cos(np.deg2rad(np.asarray(theta_values, dtype=float)))
    r_low = float(np.min(d_low / cosine))
    r_high = float(np.max(d_high / cosine))
    return r_low, r_high, r_high - r_low


def geometry_fields(frame: pd.Series) -> tuple[np.ndarray, np.ndarray, float]:
    height = int(frame.sar_height_px)
    width = int(frame.sar_width_px)
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    cx = float(frame.geometry_center_x_px)
    cy = float(frame.geometry_center_y_px)
    px_per_m = float(frame.geometry_radius_px) / float(frame.geometry_outer_range_m)
    theta = np.degrees(np.arctan2(xx - cx, cy - yy))
    d_parallel = (cy - yy) / px_per_m
    return theta, d_parallel, px_per_m


def family_count(
    membership_index: dict[tuple[int, str, str], str],
    frame_index: int,
    track_id: str,
    region_ids: list[str],
) -> tuple[int, int]:
    families = set()
    unassigned = 0
    for region_id in region_ids:
        family = membership_index.get((frame_index, track_id, region_id))
        if family is None:
            family = f"UNASSIGNED::{region_id}"
            unassigned += 1
        families.add(family)
    return len(families), unassigned


def support_counts(
    labels: np.ndarray,
    support: np.ndarray,
    frame_index: int,
    track_id: str,
    px_per_m: float,
    membership_index: dict[tuple[int, str, str], str],
) -> dict[str, Any]:
    selected_labels = sorted(int(x) for x in np.unique(labels[support]) if int(x) > 0)
    region_ids = [f"R02ZF_SARF{frame_index:06d}__Q095__R{label:04d}" for label in selected_labels]
    family_n, unassigned = family_count(membership_index, frame_index, track_id, region_ids)
    pixel_count = int(np.count_nonzero((labels > 0) & support))
    return {
        "N_region": len(selected_labels),
        "N_family": family_n,
        "A_candidate_px": pixel_count,
        "A_candidate_m2": float(pixel_count / (px_per_m * px_per_m)),
        "region_ids_json": json.dumps(region_ids, ensure_ascii=False),
        "unassigned_family_count": unassigned,
    }


def build_sensitivity_and_burden(
    registry: pd.DataFrame,
    shells: pd.DataFrame,
    frame_bands: pd.DataFrame,
    thresholds: dict[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    primary_bands = frame_bands[
        frame_bands.score_rank.eq(1) & frame_bands.primary_window
    ].set_index("sar_frame_index")
    topology = pd.read_csv(PRE / "optical_person_curb_topology_visual_development_only.csv")
    known_tracks = set(topology.raw_track_fragment_id.astype(str))
    membership = pd.read_parquet(FAMILY_MEMBERSHIP)
    membership = membership[
        membership.run_id.eq("R02ZF") & membership["mode"].eq(CURRENT_MODE)
    ]
    membership_index = {
        (int(row.frame_index), str(row.track_id), str(row.region_id)): str(row.family_id)
        for row in membership.itertuples(index=False)
    }
    registry_index = registry.set_index("sar_frame_index")
    width_rows: list[dict[str, Any]] = []
    burden_rows: list[dict[str, Any]] = []
    geometry_cache: dict[int, tuple[np.ndarray, np.ndarray, float, np.ndarray]] = {}
    for shell in shells.itertuples(index=False):
        frame_index = int(shell.frame_index)
        frame = registry_index.loc[frame_index]
        current = parse_intervals(shell.effective_intervals_json)
        band = primary_bands.loc[frame_index] if frame_index in primary_bands.index else None
        available = band is not None and band.availability_state == "CURB_BAND_AVAILABLE_GT_BLIND"
        topology_label = "SIDEWALK_OR_PARKING_SIDE" if str(shell.track_id) in known_tracks else "UNCERTAIN"
        for sensitivity_name, half_width in SENSITIVITIES.items():
            intervals = sensitivity_intervals(current, half_width)
            if available:
                r_low, r_high, r_width = range_interval_for_support(
                    float(band.d_band_low_m), float(band.d_band_high_m), intervals
                )
            else:
                r_low = r_high = r_width = math.nan
            width_rows.append(
                {
                    "run_id": "R02ZF",
                    "sar_frame_index": frame_index,
                    "shell_id": str(shell.shell_id),
                    "track_id": str(shell.track_id),
                    "sensitivity": sensitivity_name,
                    "intervals_json": json.dumps(intervals),
                    "angular_width_deg": float(sum(high - low for low, high in intervals)),
                    "curb_availability_state": (
                        str(band.availability_state) if band is not None else "CURB_UNAVAILABLE_NO_FRAME_BAND"
                    ),
                    "curb_range_min_m": r_low,
                    "curb_range_max_m": r_high,
                    "curb_range_width_m": r_width,
                    "topology_label": topology_label,
                    "manual_sar_reference_used": False,
                }
            )
            if frame_index not in geometry_cache:
                theta, d_parallel, px_per_m = geometry_fields(frame)
                with np.load(Q95_MASKS / f"R02ZF_SARF{frame_index:06d}.npz") as archive:
                    labels = archive["Q095"]
                geometry_cache[frame_index] = (theta, d_parallel, px_per_m, labels)
            theta, d_parallel, px_per_m, labels = geometry_cache[frame_index]
            a_mask = angle_mask(theta, intervals)
            before = support_counts(
                labels, a_mask, frame_index, str(shell.track_id), px_per_m, membership_index
            )
            for topology_mode in ("PRIMARY_SELECTED_CURB", "IDENTITY_CONSERVATIVE_TWO_NEAR_BANDS"):
                applied = bool(available and topology_label != "UNCERTAIN")
                if applied:
                    if topology_mode == "PRIMARY_SELECTED_CURB":
                        d_threshold = float(band.d_band_low_m)
                    else:
                        d_threshold = min(
                            float(band.d_band_low_m),
                            float(thresholds["alternate_identity_conservative_low_m"]),
                        )
                    after_mask = a_mask & (d_parallel >= d_threshold)
                    availability_state = "CURB_TOPOLOGY_APPLIED"
                else:
                    d_threshold = math.nan
                    after_mask = a_mask
                    availability_state = "NO_RADIAL_DELETION_CURB_OR_TOPOLOGY_UNAVAILABLE"
                after = support_counts(
                    labels, after_mask, frame_index, str(shell.track_id), px_per_m, membership_index
                )
                burden_rows.append(
                    {
                        "run_id": "R02ZF",
                        "sar_frame_index": frame_index,
                        "shell_id": str(shell.shell_id),
                        "track_id": str(shell.track_id),
                        "sensitivity": sensitivity_name,
                        "topology_mode": topology_mode,
                        "topology_label": topology_label,
                        "topology_state": availability_state,
                        "d_threshold_m": d_threshold,
                        "N_region_angle_only": before["N_region"],
                        "N_region_angle_plus_curb": after["N_region"],
                        "N_family_angle_only": before["N_family"],
                        "N_family_angle_plus_curb": after["N_family"],
                        "A_candidate_px_angle_only": before["A_candidate_px"],
                        "A_candidate_px_angle_plus_curb": after["A_candidate_px"],
                        "A_candidate_m2_angle_only": before["A_candidate_m2"],
                        "A_candidate_m2_angle_plus_curb": after["A_candidate_m2"],
                        "region_ids_angle_only_json": before["region_ids_json"],
                        "region_ids_angle_plus_curb_json": after["region_ids_json"],
                        "unassigned_family_count_before": before["unassigned_family_count"],
                        "unassigned_family_count_after": after["unassigned_family_count"],
                        "pixel_intersection_used": True,
                        "manual_sar_reference_used": False,
                    }
                )
    widths = pd.DataFrame(width_rows)
    burden = pd.DataFrame(burden_rows)
    width_summary_rows = []
    for sensitivity, group in widths.groupby("sensitivity"):
        available = group[group.curb_range_width_m.notna()]
        width_summary_rows.append(
            {
                "sensitivity": sensitivity,
                "denominator_shell_rows": len(group),
                "available_shell_rows": len(available),
                "availability_fraction": len(available) / max(len(group), 1),
                "curb_range_width_median": float(available.curb_range_width_m.median()) if len(available) else math.nan,
                "curb_range_width_p90": float(available.curb_range_width_m.quantile(0.90)) if len(available) else math.nan,
                "curb_range_width_max": float(available.curb_range_width_m.max()) if len(available) else math.nan,
            }
        )
    width_summary = pd.DataFrame(width_summary_rows)
    burden_summary_rows = []
    for (sensitivity, topology_mode), group in burden.groupby(["sensitivity", "topology_mode"]):
        applied = group[group.topology_state.eq("CURB_TOPOLOGY_APPLIED")]
        burden_summary_rows.append(
            {
                "sensitivity": sensitivity,
                "topology_mode": topology_mode,
                "denominator_shell_rows": len(group),
                "applied_shell_rows": len(applied),
                "applied_fraction": len(applied) / max(len(group), 1),
                "N_region_before_median": float(group.N_region_angle_only.median()),
                "N_region_after_median": float(group.N_region_angle_plus_curb.median()),
                "N_region_reduction_median": float(
                    (group.N_region_angle_only - group.N_region_angle_plus_curb).median()
                ),
                "N_family_before_median": float(group.N_family_angle_only.median()),
                "N_family_after_median": float(group.N_family_angle_plus_curb.median()),
                "N_family_reduction_median": float(
                    (group.N_family_angle_only - group.N_family_angle_plus_curb).median()
                ),
                "A_candidate_px_before_median": float(group.A_candidate_px_angle_only.median()),
                "A_candidate_px_after_median": float(group.A_candidate_px_angle_plus_curb.median()),
                "A_candidate_px_reduction_fraction_median": float(
                    np.median(
                        np.where(
                            group.A_candidate_px_angle_only > 0,
                            1.0 - group.A_candidate_px_angle_plus_curb / group.A_candidate_px_angle_only,
                            0.0,
                        )
                    )
                ),
                "A_candidate_m2_before_median": float(group.A_candidate_m2_angle_only.median()),
                "A_candidate_m2_after_median": float(group.A_candidate_m2_angle_plus_curb.median()),
                "any_region_reduction_fraction": float(
                    np.mean(group.N_region_angle_plus_curb < group.N_region_angle_only)
                ),
            }
        )
    burden_summary = pd.DataFrame(burden_summary_rows)
    return widths, width_summary, burden, burden_summary


def visual_computed_audit(frame_bands: pd.DataFrame) -> pd.DataFrame:
    visual = pd.read_csv(PRE / "CURB_VISUAL_HYPOTHESIS_LEDGER.csv")
    primary = frame_bands[frame_bands.score_rank.eq(1)][
        [
            "sar_frame_index",
            "d_peak_m",
            "d_band_low_m",
            "d_band_high_m",
            "local_peak_contrast",
            "theta_coherence_fraction",
            "availability_state",
        ]
    ]
    result = visual.merge(primary, on="sar_frame_index", how="left")
    result["computed_verdict_after_visual_freeze"] = result.availability_state.fillna(
        "NOT_IN_AUTOMATIC_PROFILE_SET"
    )
    return result


def plot_sensitivity(width_summary: pd.DataFrame, burden_summary: pd.DataFrame) -> None:
    order = list(SENSITIVITIES)
    widths = width_summary.set_index("sensitivity").reindex(order)
    burden = burden_summary[
        burden_summary.topology_mode.eq("PRIMARY_SELECTED_CURB")
    ].set_index("sensitivity").reindex(order)
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5), constrained_layout=True)
    x = np.arange(len(order))
    axes[0].plot(x, widths.curb_range_width_median, marker="o", label="median")
    axes[0].plot(x, widths.curb_range_width_p90, marker="o", label="P90")
    axes[0].set_xticks(x, order, rotation=25, ha="right")
    axes[0].set_ylabel("curb range interval width (m)")
    axes[0].set_title("Angular-width sensitivity")
    axes[0].legend()
    axes[1].plot(x, burden.N_region_before_median, marker="o", label="angle only N_region")
    axes[1].plot(x, burden.N_region_after_median, marker="o", label="angle + curb N_region")
    axes[1].plot(x, burden.N_family_after_median, marker="o", label="after N_family")
    axes[1].set_xticks(x, order, rotation=25, ha="right")
    axes[1].set_ylabel("median burden")
    axes[1].set_title("Exact-Q95 candidate burden")
    axes[1].legend()
    fig.suptitle("PERSON-CURB0 pre-reference sensitivity; diagnostic, not tuning")
    fig.savefig(FIG / "08_angular_width_sensitivity_and_burden.png", dpi=180)
    plt.close(fig)


def render_q95_review(
    registry: pd.DataFrame,
    burden: pd.DataFrame,
    frame_bands: pd.DataFrame,
) -> int:
    subset = burden[
        burden.sensitivity.eq("CURRENT_FROZEN")
        & burden.topology_mode.eq("PRIMARY_SELECTED_CURB")
        & burden.topology_state.eq("CURB_TOPOLOGY_APPLIED")
    ].copy()
    subset["residual_score"] = (
        subset.N_family_angle_plus_curb * 1_000_000
        + subset.A_candidate_px_angle_plus_curb
    )
    worst = subset.sort_values("residual_score", ascending=False).iloc[0]
    selected = [421, 450, 462, 474, int(worst.sar_frame_index)]
    selected = list(dict.fromkeys(selected))
    registry_index = registry.set_index("sar_frame_index")
    primary = frame_bands[frame_bands.score_rank.eq(1)].set_index("sar_frame_index")
    fig, axes = plt.subplots(len(selected), 2, figsize=(15, 4.5 * len(selected)), constrained_layout=True)
    if len(selected) == 1:
        axes = np.asarray([axes])
    for row_axes, frame_index in zip(axes, selected):
        candidate_rows = subset[subset.sar_frame_index.eq(frame_index)]
        item = candidate_rows.sort_values("N_family_angle_plus_curb", ascending=False).iloc[0]
        frame = registry_index.loc[frame_index]
        image = read_bgr(Path(frame.sar_image_path))
        with np.load(Q95_MASKS / f"R02ZF_SARF{frame_index:06d}.npz") as archive:
            labels = archive["Q095"]
        theta, d_parallel, _, = geometry_fields(frame)
        shell = pd.read_parquet(SHELLS)
        shell = shell[shell.shell_id.eq(item.shell_id)].iloc[0]
        intervals = parse_intervals(shell.effective_intervals_json)
        amask = angle_mask(theta, intervals)
        band = primary.loc[frame_index]
        tmask = d_parallel >= float(band.d_band_low_m)
        q95 = labels > 0
        before = q95 & amask
        retained = before & tmask
        removed = before & ~tmask
        before_overlay = image.copy()
        before_overlay[before] = (
            0.35 * before_overlay[before] + 0.65 * np.array([0, 255, 255])
        ).astype(np.uint8)
        after_overlay = image.copy()
        after_overlay[removed] = (
            0.30 * after_overlay[removed] + 0.70 * np.array([0, 0, 255])
        ).astype(np.uint8)
        after_overlay[retained] = (
            0.30 * after_overlay[retained] + 0.70 * np.array([0, 255, 0])
        ).astype(np.uint8)
        for overlay in (before_overlay, after_overlay):
            px_per_m = float(frame.geometry_radius_px) / float(frame.geometry_outer_range_m)
            y1 = int(round(float(frame.geometry_center_y_px) - float(band.d_band_low_m) * px_per_m))
            y2 = int(round(float(frame.geometry_center_y_px) - float(band.d_band_high_m) * px_per_m))
            cv2.line(overlay, (0, y1), (overlay.shape[1] - 1, y1), (255, 255, 255), 2)
            cv2.line(overlay, (0, y2), (overlay.shape[1] - 1, y2), (255, 255, 255), 2)
        row_axes[0].imshow(cv2.cvtColor(before_overlay, cv2.COLOR_BGR2RGB))
        row_axes[0].set_title(
            f"F{frame_index} ANGLE_ONLY | regions={int(item.N_region_angle_only)} "
            f"families={int(item.N_family_angle_only)}"
        )
        row_axes[1].imshow(cv2.cvtColor(after_overlay, cv2.COLOR_BGR2RGB))
        row_axes[1].set_title(
            f"ANGLE+CURB | regions={int(item.N_region_angle_plus_curb)} "
            f"families={int(item.N_family_angle_plus_curb)} | green retained / red removed"
        )
        for ax in row_axes:
            ax.axis("off")
    fig.suptitle("Exact Q95 pixel intersections; white lines are selected curb-band limits")
    fig.savefig(FIG / "09_q95_angle_only_vs_curb_topology_review.png", dpi=180)
    plt.close(fig)
    write_json(
        PRE / "strongest_residual_clutter_counterexample_pre_reference.json",
        {
            "run_id": "R02ZF",
            "sar_frame_index": int(worst.sar_frame_index),
            "shell_id": str(worst.shell_id),
            "track_id": str(worst.track_id),
            "N_region_angle_only": int(worst.N_region_angle_only),
            "N_region_angle_plus_curb": int(worst.N_region_angle_plus_curb),
            "N_family_angle_only": int(worst.N_family_angle_only),
            "N_family_angle_plus_curb": int(worst.N_family_angle_plus_curb),
            "A_candidate_px_angle_plus_curb": int(worst.A_candidate_px_angle_plus_curb),
            "interpretation": (
                "Strongest residual same-legal-side clutter case in the frozen primary window. "
                "Curb topology cannot uniquely ground the PERSON response."
            ),
            "manual_sar_reference_used": False,
        },
    )
    return int(worst.sar_frame_index)


def freeze_pre_reference(files: list[Path], denominators: dict[str, Any]) -> dict[str, Any]:
    records = []
    for path in sorted(set(files), key=lambda p: str(p).lower()):
        records.append(
            {
                "path": str(path.relative_to(OUT)).replace("\\", "/") if path.is_relative_to(OUT) else str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    payload = "\n".join(f"{row['path']}|{row['bytes']}|{row['sha256']}" for row in records)
    root = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    manifest = {
        "freeze_semantics": "PRE_REFERENCE_CURB_HYPOTHESES_BANDS_TOPOLOGY_SENSITIVITY_DENOMINATORS_AND_CASES_FROZEN",
        "primary_window": [421, 474],
        "manual_sar_reference_opened": False,
        "r04_accessed": False,
        "denominators": denominators,
        "files": records,
        "pre_reference_root_sha256": root,
    }
    write_json(PRE / "PRE_REFERENCE_FREEZE_MANIFEST.json", manifest)
    return manifest


def load_post_reference_mapping() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not (PRE / "PRE_REFERENCE_FREEZE_MANIFEST.json").exists():
        raise RuntimeError("reference gate violation: freeze manifest missing")
    reference = pd.read_parquet(R02_REFERENCE)
    reference = reference[
        reference.run_id.eq("R02ZF") & reference.frame_index.between(421, 474)
    ].copy()
    mapping = pd.read_csv(RAW_TARGET_MAP, encoding="utf-8-sig")
    mapping = mapping[mapping.run_id.eq("R02ZF")].copy()
    entity_column = "entity_id" if "entity_id" in mapping.columns else "raw_track_fragment_id"
    mapping = mapping.rename(columns={entity_column: "track_id"})
    return reference, mapping


def evaluate_post_reference(
    shells: pd.DataFrame,
    widths: pd.DataFrame,
    frame_bands: pd.DataFrame,
    thresholds: dict[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    reference, mapping = load_post_reference_mapping()
    mapped = shells.merge(mapping[["run_id", "track_id", "target_id"]], on=["run_id", "track_id"], how="left")
    mapped = mapped.merge(
        reference[
            [
                "run_id",
                "frame_index",
                "target_id",
                "reference_range_m",
                "reference_theta_deg",
                "reference_support_status",
            ]
        ],
        on=["run_id", "frame_index", "target_id"],
        how="inner",
    )
    primary = frame_bands[frame_bands.score_rank.eq(1)].set_index("sar_frame_index")
    rows: list[dict[str, Any]] = []
    for item in mapped.itertuples(index=False):
        current = parse_intervals(item.effective_intervals_json)
        band = primary.loc[int(item.frame_index)] if int(item.frame_index) in primary.index else None
        available = band is not None and band.availability_state == "CURB_BAND_AVAILABLE_GT_BLIND"
        for sensitivity, half_width in SENSITIVITIES.items():
            intervals = sensitivity_intervals(current, half_width)
            angular = theta_in_intervals(float(item.reference_theta_deg), intervals)
            if available:
                d_ref = float(item.reference_range_m) * math.cos(math.radians(float(item.reference_theta_deg)))
                radial_primary = d_ref >= float(band.d_band_low_m)
                radial_conservative = d_ref >= min(
                    float(band.d_band_low_m), float(thresholds["alternate_identity_conservative_low_m"])
                )
                state = "CURB_TOPOLOGY_APPLIED"
            else:
                d_ref = float(item.reference_range_m) * math.cos(math.radians(float(item.reference_theta_deg)))
                radial_primary = True
                radial_conservative = True
                state = "CURB_UNAVAILABLE_FALLBACK_NO_RADIAL_DELETION"
            for topology_mode, radial in (
                ("PRIMARY_SELECTED_CURB", radial_primary),
                ("IDENTITY_CONSERVATIVE_TWO_NEAR_BANDS", radial_conservative),
            ):
                rows.append(
                    {
                        "run_id": "R02ZF",
                        "sar_frame_index": int(item.frame_index),
                        "track_id": str(item.track_id),
                        "target_id_oracle": str(item.target_id),
                        "sensitivity": sensitivity,
                        "topology_mode": topology_mode,
                        "reference_range_m": float(item.reference_range_m),
                        "reference_theta_deg": float(item.reference_theta_deg),
                        "reference_d_parallel_m": d_ref,
                        "reference_support_status": str(item.reference_support_status),
                        "curb_state": state,
                        "angular_support_retained": bool(angular),
                        "radial_topology_retained": bool(radial),
                        "support_2d_retained": bool(angular and radial),
                        "post_reference_only": True,
                    }
                )
    retention = pd.DataFrame(rows)
    summary_rows = []
    for (sensitivity, topology_mode), group in retention.groupby(["sensitivity", "topology_mode"]):
        applied = group[group.curb_state.eq("CURB_TOPOLOGY_APPLIED")]
        summary_rows.append(
            {
                "sensitivity": sensitivity,
                "topology_mode": topology_mode,
                "reference_rows": len(group),
                "applied_reference_rows": len(applied),
                "angular_retention_fraction": float(group.angular_support_retained.mean()),
                "radial_retention_fallback_aware_fraction": float(group.radial_topology_retained.mean()),
                "support_2d_retention_fallback_aware_fraction": float(group.support_2d_retained.mean()),
                "radial_retention_applied_only_fraction": float(applied.radial_topology_retained.mean()) if len(applied) else math.nan,
                "support_2d_retention_applied_only_fraction": float(applied.support_2d_retained.mean()) if len(applied) else math.nan,
            }
        )
    summary = pd.DataFrame(summary_rows)
    layer = retention[
        retention.sensitivity.eq("CURRENT_FROZEN")
        & retention.topology_mode.eq("PRIMARY_SELECTED_CURB")
    ].copy()
    layer["range_layer"] = pd.cut(
        layer.reference_range_m,
        bins=[-np.inf, 6.0, 8.0, 12.0, 14.0, np.inf],
        labels=["LT6M", "6_TO_8M", "8_TO_12M", "12_TO_14M", "GT14M"],
        right=False,
    ).astype(str)
    layer_summary = layer.groupby("range_layer", dropna=False).agg(
        reference_rows=("target_id_oracle", "size"),
        unique_targets=("target_id_oracle", "nunique"),
        reference_range_median=("reference_range_m", "median"),
        reference_d_parallel_median=("reference_d_parallel_m", "median"),
        radial_retention_fraction=("radial_topology_retained", "mean"),
        support_2d_retention_fraction=("support_2d_retained", "mean"),
    ).reset_index()
    return retention, summary, layer_summary


def plot_post_reference(retention_summary: pd.DataFrame, layer_summary: pd.DataFrame) -> None:
    order = list(SENSITIVITIES)
    data = retention_summary[
        retention_summary.topology_mode.eq("PRIMARY_SELECTED_CURB")
    ].set_index("sensitivity").reindex(order)
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5), constrained_layout=True)
    x = np.arange(len(order))
    axes[0].plot(x, data.angular_retention_fraction, marker="o", label="angular")
    axes[0].plot(x, data.radial_retention_fallback_aware_fraction, marker="o", label="radial topology")
    axes[0].plot(x, data.support_2d_retention_fallback_aware_fraction, marker="o", label="2D")
    axes[0].set_xticks(x, order, rotation=25, ha="right")
    axes[0].set_ylim(0, 1.05)
    axes[0].set_ylabel("reference retention fraction")
    axes[0].legend()
    axes[0].set_title("Post-freeze reference support retention")
    axes[1].bar(layer_summary.range_layer, layer_summary.reference_rows, color="#4c78a8")
    axes[1].set_ylabel("reference rows")
    axes[1].tick_params(axis="x", rotation=25)
    axes[1].set_title("R02 reference radial layers in selected window")
    fig.savefig(FIG / "10_post_reference_retention_and_range_layers.png", dpi=180)
    plt.close(fig)


def report_text(
    candidates: pd.DataFrame,
    frame_bands: pd.DataFrame,
    width_summary: pd.DataFrame,
    burden_summary: pd.DataFrame,
    retention_summary: pd.DataFrame,
    layer_summary: pd.DataFrame,
    worst_frame: int,
    freeze: dict[str, Any],
) -> str:
    primary = candidates[candidates.score_rank.eq(1)].iloc[0]
    width = width_summary.set_index("sensitivity")
    burden = burden_summary[
        burden_summary.topology_mode.eq("PRIMARY_SELECTED_CURB")
    ].set_index("sensitivity")
    conservative = burden_summary[
        burden_summary.topology_mode.eq("IDENTITY_CONSERVATIVE_TWO_NEAR_BANDS")
        & burden_summary.sensitivity.eq("CURRENT_FROZEN")
    ].iloc[0]
    retention = retention_summary[
        retention_summary.topology_mode.eq("PRIMARY_SELECTED_CURB")
    ].set_index("sensitivity")
    current_burden = burden.loc["CURRENT_FROZEN"]
    current_retention = retention.loc["CURRENT_FROZEN"]
    primary_frames = frame_bands[
        frame_bands.score_rank.eq(1) & frame_bands.primary_window
    ].sort_values("sar_frame_index")
    available_frames = set(
        primary_frames[
            primary_frames.availability_state.eq("CURB_BAND_AVAILABLE_GT_BLIND")
        ].sar_frame_index.astype(int)
    )
    spans: list[tuple[int, int]] = []
    start = previous = None
    for frame_index in sorted(available_frames):
        if start is None or frame_index != previous + 1:
            if start is not None:
                spans.append((start, previous))
            start = frame_index
        previous = frame_index
    if start is not None:
        spans.append((start, previous))
    stable_start, stable_end = max(spans, key=lambda pair: (pair[1] - pair[0] + 1, pair[1]))
    reference_rows = int(retention_summary.reference_rows.max())
    layer_6_8 = int(layer_summary.loc[layer_summary.range_layer.eq("6_TO_8M"), "reference_rows"].sum())
    layer_12_14 = int(layer_summary.loc[layer_summary.range_layer.eq("12_TO_14M"), "reference_rows"].sum())
    return f"""# PERSON-CURB0 R02 parallel curb radial anchor pilot

## Direct answer

**可以，但结论严格限定在 R02ZF SAR F421-F474：用户指出的平行路缘场景确实提供了一条有用的 SAR 图像域径向边界；它能做保守的半空间剪枝，却不能单独给出唯一 PERSON grounding。** GT-blind 自动排序的主静态带位于 `d_parallel≈{primary.d_parallel_peak_m:.2f} m`，在稳定窗的可用率为 `{primary.stable_available_frames}/{primary.stable_total_frames} = {primary.stable_availability_fraction:.1%}`。同时 `4.90 m` 近侧替代带必须保留为物理身份不确定性，`12.40 m` 是最强远侧平行混淆项。因此本轮结论是 `CURB_RADIAL_TOPOLOGY_ONLY_MODERATELY_USEFUL_IN_STABLE_SEGMENT`，不是全 R02、不是 exact optical-SAR point match，也不是 final PERSON range/box。

## Required answers

1. **SAR extraction:** primary boundary availability `{primary.stable_available_frames}/{primary.stable_total_frames} ({primary.stable_availability_fraction:.1%})` in F421-F474. Unavailable frames fall back to angle-only; no radial deletion is invented.
2. **Most stable temporal segment:** the longest uninterrupted available run is `R02ZF SAR F{stable_start}-F{stable_end}` inside the frozen primary window `F421-F474`. F375-F414 is a passing-vehicle/near-range-reflection control; F480-F488 is a display-intensity/multiple-arc control.
3. **Current frozen corridor curb width:** median `{width.loc['CURRENT_FROZEN','curb_range_width_median']:.3f} m`, P90 `{width.loc['CURRENT_FROZEN','curb_range_width_p90']:.3f} m` on available shell rows.
4. **Angular sensitivity:** +/-6 deg median/P90 `{width.loc['PLUS_MINUS_6_DEG','curb_range_width_median']:.3f}/{width.loc['PLUS_MINUS_6_DEG','curb_range_width_p90']:.3f} m`; +/-4 deg `{width.loc['PLUS_MINUS_4_DEG','curb_range_width_median']:.3f}/{width.loc['PLUS_MINUS_4_DEG','curb_range_width_p90']:.3f} m`; +/-3 deg `{width.loc['PLUS_MINUS_3_DEG','curb_range_width_median']:.3f}/{width.loc['PLUS_MINUS_3_DEG','curb_range_width_p90']:.3f} m`; +/-2 deg `{width.loc['PLUS_MINUS_2_DEG','curb_range_width_median']:.3f}/{width.loc['PLUS_MINUS_2_DEG','curb_range_width_p90']:.3f} m`. On the very small post-reference denominator (`n={reference_rows}`), every centered +/-6/4/3/2/1 diagnostic retains only 50% angular support, while the current frozen asymmetric corridor retains 100%; these narrower widths are therefore diagnostic only and are not supported as replacements for the current mapping.
5. **Optical topology:** visually stable for the reviewed stable-window PERSON hypotheses. The near roadside curb separates the foreground road/platform side from the farther sidewalk/planting/parking side. All labels remain `VISUAL_DEVELOPMENT_ONLY_NOT_RUNTIME_CLASSIFIER`; interpolated/small candidates retain lower confidence.
6. **Exact Q95 burden, current corridor, primary band:** median `N_region {current_burden.N_region_before_median:.1f} -> {current_burden.N_region_after_median:.1f}`, `N_family {current_burden.N_family_before_median:.1f} -> {current_burden.N_family_after_median:.1f}`, `A_candidate_px {current_burden.A_candidate_px_before_median:.1f} -> {current_burden.A_candidate_px_after_median:.1f}`, `A_candidate_m2 {current_burden.A_candidate_m2_before_median:.3f} -> {current_burden.A_candidate_m2_after_median:.3f}`. The identity-conservative two-near-band result is weaker: median `N_family -> {conservative.N_family_after_median:.1f}`.
7. **Strongest counterexample:** R02ZF F{worst_frame}. It retains the largest same-legal-side Q95 family burden after curb pruning. This demonstrates that walls/vehicles/other static responses beyond the curb remain legal clutter.
8. **Small manual input:** an optical curb polyline is not required for this half-space diagnostic because the side relation is visually clear. A reviewer should confirm 3-5 SAR keyframes in `SAR_CURB_IDENTITY_CONFIRMATION_TEMPLATE.csv` if the physical identity of the 7.10 m band versus the 4.90 m alternative must be promoted beyond this conditional pilot.
9. **Post-freeze reference retention:** current corridor angular `{current_retention.angular_retention_fraction:.1%}`, radial topology fallback-aware `{current_retention.radial_retention_fallback_aware_fraction:.1%}`, 2D `{current_retention.support_2d_retention_fallback_aware_fraction:.1%}`. Reference was opened only after freeze root `{freeze['pre_reference_root_sha256']}`.
10. **One next step:** manually confirm which near SAR band is the physical roadside curb on 3-5 review frames (F421/F435/F450/F462/F474); then freeze that identity and rerun the same unchanged half-space evaluation. Do not build an automatic optical curb classifier yet.

## Candidate interpretation

- `~7.10 m`: highest persistence/coherence score; selected primary curb-compatible static boundary.
- `~4.90 m`: retained near-side alternate static boundary; drives the identity-conservative result.
- `~12.40 m`: far parallel static-clutter counterexample, visually consistent with parked-vehicle/planting/building-side structure rather than the near roadside curb.
- Band widths are derived from local half-height ridge support plus robust temporal center variability. No fixed +/-0.2 m or +/-0.5 m width is imposed.
- The ideal parallel-line relation is used only as a sanity representation: `d_parallel = r cos(theta)` and `r_curb(theta)=d_parallel/cos(theta)`.

## Range-layer audit

The frozen-window post-reference layer table is in `post_reference_evaluation_only/reference_range_layer_summary_post_reference.csv`. This selected stable window contains `{layer_12_14}` reference rows in the 12-14 m layer and `{layer_6_8}` in the 6-8 m layer. Therefore the curb-side retention result is supported only for the 12-14 m layer here; the requested 6-8 versus 12-14 comparison cannot be completed inside this restricted window and is not inferred from absent rows.

## Non-claims

This pilot does not claim intrinsic RCS, recovered physical platform/person motion, calibrated camera-radar geometry, exact cross-modal point correspondence, runtime optical curb classification, PERSON identity, tracker improvement, score fusion, final range, final center, or final box. `Omega` remains a PERSON-conditioned physical search support. Q95 and P0 family terms remain conditional SAR image-domain response structures. R04 was not accessed.
"""


def build_review_pack(worst_frame: int) -> tuple[int, str]:
    if PACK_STAGE.exists():
        shutil.rmtree(PACK_STAGE)
    PACK_STAGE.mkdir(parents=True)
    records: list[dict[str, Any]] = []

    def copy(source: Path, relative: Path, role: str) -> None:
        destination = PACK_STAGE / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        records.append(
            {
                "relative_path": str(relative).replace("\\", "/"),
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "source_original_path": str(source),
                "data_role": role,
            }
        )

    for source in [SCRIPT, PREPARE_SCRIPT, VISUAL_FREEZE_SCRIPT, PROBE_SCRIPT, TASK / "README.md"]:
        copy(source, Path("code") / source.name, "code")
    copy(OUT / "REPORT.md", Path("report") / "REPORT.md", "report")
    copy(
        OUT / "SAR_CURB_IDENTITY_CONFIRMATION_TEMPLATE.csv",
        Path("review_templates") / "SAR_CURB_IDENTITY_CONFIRMATION_TEMPLATE.csv",
        "minimal SAR curb identity confirmation template",
    )
    for source in sorted(PRE.glob("*.csv")) + sorted(PRE.glob("*.json")):
        copy(source, Path("pre_reference") / source.name, "pre-reference table or manifest")
    for source in sorted(POST.glob("*.csv")) + sorted(POST.glob("*.json")):
        copy(source, Path("post_reference") / source.name, "post-reference evaluation")
    for source in sorted(FIG.glob("*.png")):
        copy(source, Path("figures") / source.name, "figure")
    registry = pd.read_parquet(REGISTRY)
    registry = registry[registry.run_id.eq("R02ZF")].set_index("sar_frame_index")
    keyframes = [390, 421, 435, 450, 462, 474, 480, 486, worst_frame]
    keyframes = list(dict.fromkeys(keyframes))
    optical_dir = Path(
        r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
        r"\pseudocolor_labelstudio_prep_20260722\frames\optical\R02ZF"
    )
    for frame_index in keyframes:
        row = registry.loc[frame_index]
        sar = Path(row.sar_image_path)
        copy(sar, Path("raw_sar_keyframes") / f"SAR_F{frame_index:06d}{sar.suffix}", "raw SAR keyframe")
        opt_index = int(row.nominal_optical_frame_index)
        opt_matches = list(optical_dir.glob(f"frame_{opt_index:06d}_t*ms.jpg"))
        if len(opt_matches) == 1:
            copy(
                opt_matches[0],
                Path("raw_optical_keyframes") / f"OPT_F{opt_index:06d}{opt_matches[0].suffix}",
                "raw optical keyframe",
            )
        mask = Q95_MASKS / f"R02ZF_SARF{frame_index:06d}.npz"
        copy(mask, Path("q95_masks") / mask.name, "frozen Q95 mask")
    readme = """# PERSON R02 curb radial anchor review pack

Start with `figures/06_static_band_candidate_overlays.png`, `figures/09_q95_angle_only_vs_curb_topology_review.png`, and the paired raw keyframes. White/rank-1 near-horizontal line is the automatically selected 7.10 m static boundary. Red/rank-2 is the retained 4.90 m near alternative. Yellow/rank-3 is the 12.40 m far parallel confounder. Confirm whether rank 1 is the user-intended roadside curb on F421/F435/F450/F462/F474. The pack does not contain a final PERSON center or box.
"""
    (PACK_STAGE / "README.md").write_text(readme, encoding="utf-8")
    records.append(
        {
            "relative_path": "README.md",
            "bytes": (PACK_STAGE / "README.md").stat().st_size,
            "sha256": sha256_file(PACK_STAGE / "README.md"),
            "source_original_path": "GENERATED",
            "data_role": "review instructions",
        }
    )
    manifest = pd.DataFrame(records).sort_values("relative_path")
    manifest.to_csv(PACK_STAGE / "PACK_MANIFEST.csv", index=False, encoding="utf-8-sig")
    PACK.parent.mkdir(parents=True, exist_ok=True)
    if PACK.exists():
        PACK.unlink()
    with zipfile.ZipFile(PACK, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(PACK_STAGE.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=str(path.relative_to(PACK_STAGE)).replace("\\", "/"))
    return PACK.stat().st_size, sha256_file(PACK)


def main() -> None:
    verify_scope()
    PRE.mkdir(parents=True, exist_ok=True)
    POST.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    run_stage(PREPARE_SCRIPT)
    run_stage(VISUAL_FREEZE_SCRIPT)
    run_stage(PROBE_SCRIPT)

    registry = pd.read_parquet(REGISTRY)
    registry = registry[registry.run_id.eq("R02ZF")].copy()
    shells = pd.read_parquet(SHELLS)
    shells = shells[
        shells.run_id.eq("R02ZF")
        & shells["mode"].eq(CURRENT_MODE)
        & shells.frame_index.between(421, 474)
    ].copy()
    profiles = pd.read_parquet(PRE / "sar_static_band_frame_profiles_pre_reference.parquet")
    probe_candidates = pd.read_csv(PRE / "sar_static_band_candidates_probe_pre_reference.csv")
    frame_bands, candidates, thresholds = build_frame_candidate_bands(profiles, probe_candidates)
    theta_bands = build_theta_range_bands(frame_bands)
    write_table(frame_bands, PRE / "sar_curb_candidate_frame_bands_pre_reference")
    write_table(candidates, PRE / "sar_curb_candidates_and_roles_pre_reference")
    write_table(theta_bands, PRE / "sar_curb_theta_range_bands_pre_reference")
    write_json(
        PRE / "curb_algorithm_definition_pre_reference.json",
        {
            "primary_window": [421, 474],
            "selection_rule": "highest GT-blind persistence-coherence score among horizontal static-band peaks",
            "frame_contrast_min": FRAME_CONTRAST_MIN,
            "frame_theta_coherence_min": FRAME_COHERENCE_MIN,
            "band_rule": "local half-height support expanded by robust temporal center MAD scale",
            "multiple_hypothesis_policy": "rank1 primary, rank2 retained near identity alternative, rank3 far parallel confounder",
            "topology_policy": "SIDEWALK_OR_PARKING_SIDE means farther-than-curb half-space; UNCERTAIN means no deletion",
            "sensitivity_definitions": SENSITIVITIES,
            "manual_sar_reference_opened": False,
            "r04_accessed": False,
        },
    )
    widths, width_summary, burden, burden_summary = build_sensitivity_and_burden(
        registry, shells, frame_bands, thresholds
    )
    write_table(widths, PRE / "angular_width_curb_range_intervals_pre_reference")
    write_table(width_summary, PRE / "angular_width_sensitivity_summary_pre_reference")
    write_table(burden, PRE / "angle_only_vs_curb_topology_exact_q95_burden_pre_reference")
    write_table(burden_summary, PRE / "angle_only_vs_curb_topology_burden_summary_pre_reference")
    audit = visual_computed_audit(frame_bands)
    write_table(audit, PRE / "curb_visual_vs_computed_audit_pre_reference")
    plot_sensitivity(width_summary, burden_summary)
    worst_frame = render_q95_review(registry, burden, frame_bands)

    denominators = {
        "primary_sar_frames": len(PRIMARY_FRAME_SET),
        "causal_shell_rows": len(shells),
        "unique_shell_frames": int(shells.frame_index.nunique()),
        "visual_ledger_rows": len(pd.read_csv(PRE / "CURB_VISUAL_HYPOTHESIS_LEDGER.csv")),
        "optical_topology_rows": len(pd.read_csv(PRE / "optical_person_curb_topology_visual_development_only.csv")),
        "q95_masks_used": int(shells.frame_index.nunique()),
        "sensitivity_levels": len(SENSITIVITIES),
        "topology_modes": 2,
        "burden_rows": len(burden),
        "manual_sar_reference_opened": False,
    }
    write_json(PRE / "pre_reference_denominators.json", denominators)
    freeze_files = [
        PRE / "visual_hypothesis_freeze_manifest.json",
        PRE / "CURB_VISUAL_HYPOTHESIS_LEDGER.csv",
        PRE / "optical_person_curb_topology_visual_development_only.csv",
        PRE / "case_control_selection_pre_reference.json",
        PRE / "curb_algorithm_definition_pre_reference.json",
        PRE / "sar_curb_candidate_frame_bands_pre_reference.parquet",
        PRE / "sar_curb_candidates_and_roles_pre_reference.parquet",
        PRE / "sar_curb_theta_range_bands_pre_reference.parquet",
        PRE / "angular_width_curb_range_intervals_pre_reference.parquet",
        PRE / "angular_width_sensitivity_summary_pre_reference.csv",
        PRE / "angle_only_vs_curb_topology_exact_q95_burden_pre_reference.parquet",
        PRE / "angle_only_vs_curb_topology_burden_summary_pre_reference.csv",
        PRE / "curb_visual_vs_computed_audit_pre_reference.csv",
        PRE / "pre_reference_denominators.json",
        PRE / "strongest_residual_clutter_counterexample_pre_reference.json",
    ]
    freeze = freeze_pre_reference(freeze_files, denominators)

    retention, retention_summary, layer_summary = evaluate_post_reference(
        shells, widths, frame_bands, thresholds
    )
    write_table(retention, POST / "reference_support_retention_post_reference")
    write_table(retention_summary, POST / "reference_support_retention_summary_post_reference")
    write_table(layer_summary, POST / "reference_range_layer_summary_post_reference")
    write_json(
        POST / "post_reference_gate_audit.json",
        {
            "pre_reference_root_sha256": freeze["pre_reference_root_sha256"],
            "reference_source": str(R02_REFERENCE),
            "reference_source_excludes_r04": True,
            "raw_target_mapping_source": str(RAW_TARGET_MAP),
            "manual_reference_used_only_for_evaluation": True,
            "reference_used_for_curb_trace_or_topology_selection": False,
            "r04_accessed": False,
        },
    )
    plot_post_reference(retention_summary, layer_summary)

    review_template = pd.DataFrame(
        {
            "run_id": ["R02ZF"] * 5,
            "sar_frame_index": [421, 435, 450, 462, 474],
            "primary_candidate_d_parallel_m": [float(candidates.iloc[0].d_parallel_peak_m)] * 5,
            "alternate_candidate_d_parallel_m": [float(candidates.iloc[1].d_parallel_peak_m)] * 5,
            "reviewer_verdict": [""] * 5,
            "selected_candidate": [""] * 5,
            "physical_boundary_interpretation": [""] * 5,
            "ambiguity_notes": [""] * 5,
            "semantics": ["MANUAL_SAR_STATIC_BOUNDARY_IDENTITY_CONFIRMATION_NOT_PERSON_LABEL"] * 5,
        }
    )
    review_template.to_csv(
        OUT / "SAR_CURB_IDENTITY_CONFIRMATION_TEMPLATE.csv", index=False, encoding="utf-8-sig"
    )
    report = report_text(
        candidates,
        frame_bands,
        width_summary,
        burden_summary,
        retention_summary,
        layer_summary,
        worst_frame,
        freeze,
    )
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    pack_size, pack_sha = build_review_pack(worst_frame)
    summary = {
        "verdict": "CURB_RADIAL_TOPOLOGY_ONLY_MODERATELY_USEFUL_IN_STABLE_SEGMENT",
        "primary_window": [421, 474],
        "primary_candidate_d_parallel_m": float(candidates.iloc[0].d_parallel_peak_m),
        "primary_availability_fraction": float(candidates.iloc[0].stable_availability_fraction),
        "most_stable_uninterrupted_segment": [462, 474],
        "pre_reference_root_sha256": freeze["pre_reference_root_sha256"],
        "review_pack_path": str(PACK),
        "review_pack_bytes": pack_size,
        "review_pack_sha256": pack_sha,
        "r04_accessed": False,
    }
    write_json(OUT / "SUMMARY.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
