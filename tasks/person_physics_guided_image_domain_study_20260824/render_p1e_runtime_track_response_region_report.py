#!/usr/bin/env python3
"""Render the minimal runtime-track shell and frozen-C2 response-region report.

This script does not rerun the 398-frame experiment.  It reads the frozen
outputs, derives report-only summaries, recomputes the already-frozen C2 field
for seven visualization cases, and writes a Chinese HTML report.
"""

from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OUTPUT_DIR = (
    STUDY_OUTPUT
    / "p1e_sar_only_response_interface"
    / "runtime_track_response_region_minimal_v1"
)
VIS_DIR = OUTPUT_DIR / "visualizations"
MASK_DIR = OUTPUT_DIR / "response_region_masks"
REPORT_PATH = OUTPUT_DIR / "P1E_RUNTIME_TRACK_RESPONSE_REGION_MINIMAL_REPORT.html"
DERIVED_PATH = OUTPUT_DIR / "report_derived_metrics.json"

ANALYSIS_SCRIPT = TASK_DIR / "run_p1e_runtime_track_response_region_minimal.py"
SUMMARY_PATH = OUTPUT_DIR / "diagnostic_summary.json"
PROTOCOL_PATH = OUTPUT_DIR / "00_RUNTIME_TRACK_RESPONSE_REGION_PROTOCOL_FROZEN_BEFORE_RUN.md"
PROVENANCE_AMENDMENT_PATH = OUTPUT_DIR / "00A_PRE_RUN_OPTICAL_IDENTITY_PROVENANCE_AMENDMENT.md"
REGION_AMENDMENT_PATH = OUTPUT_DIR / "00B_PRE_RUN_REGION_RULE_CLARIFICATION.md"
TIME_PATH = OUTPUT_DIR / "time_uncertainty_track_shell_tradeoff.csv"
PROVENANCE_PATH = OUTPUT_DIR / "optical_track_interface_provenance.csv"
FRAME_BURDEN_PATH = OUTPUT_DIR / "track_frame_branch_burden_summary.csv"
TRACK_SUMMARY_PATH = OUTPUT_DIR / "offline_reference_track_summary.csv"
ASSIGNMENT_PATH = OUTPUT_DIR / "offline_one_to_one_track_reference_assignment.csv"
REGION_PATH = OUTPUT_DIR / "response_region_table.csv"
REFERENCE_REGION_PATH = OUTPUT_DIR / "offline_reference_response_region_evaluation.csv"
ENTITY_REGION_PATH = OUTPUT_DIR / "offline_observation_entity_response_region_evaluation.csv"
ENTITY_SUMMARY_PATH = OUTPUT_DIR / "observation_entity_response_region_summary.csv"
INTERSECTION_PATH = OUTPUT_DIR / "response_region_track_shell_intersection.csv"
OVERLAP_PATH = OUTPUT_DIR / "track_shell_overlap_table.csv"
SHELL_DEFINITION_PATH = OUTPUT_DIR / "track_shell_definition_table.csv"
CANDIDATE_PARITY_PATH = OUTPUT_DIR / "candidate_recomputation_parity.csv"
CASE_PATH = OUTPUT_DIR / "case_registry.csv"

RAW_INTERFACE = "RAW_DETECTED_FRAGMENT_ALL"
STITCHED_INTERFACE = "STITCHED_ACCEPTED_GT_BLIND_OFFLINE_PROXY"
PRIMARY_CANDIDATE = "C2_COMPACT_JET_GRADIENT_CONSENSUS"

FOCUS_TARGET_SUFFIXES = {
    "R02_F482_PEAK_MISSING_REGION": ("01", "02"),
    "R02_F490_RADIUS_SENSITIVE_REGION": ("01", "02"),
    "R02_P03_P04_SHARED_REGION": ("03", "04"),
    "R03_OUTER_RANGE_BOUNDARY_OBSERVATION": ("01",),
    "R04_F0_CLEAR_PEAK_PRESENT": ("01",),
    "R04_F35_Q90_ONLY_BORDERLINE": ("01",),
    "R02_P01_LOW_RANK_TRACK_SHELL": ("01", "02"),
}


plt.rcParams.update(
    {
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.titleweight": "bold",
    }
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def num(value: Any, digits: int = 3, missing: str = "—") -> str:
    return f"{float(value):.{digits}f}" if finite(value) else missing


def pct(value: Any, digits: int = 1, missing: str = "—") -> str:
    return f"{100.0 * float(value):.{digits}f}%" if finite(value) else missing


def as_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def target_label(target_id: Any) -> str:
    text = str(target_id)
    return "P" + text.rsplit("SARPERSON", 1)[-1] if "SARPERSON" in text else text


def relative_asset(path: Path) -> str:
    return Path(os.path.relpath(path, OUTPUT_DIR)).as_posix()


def make_table(headers: Iterable[str], rows: Iterable[Iterable[Any]]) -> str:
    head = "".join(f"<th>{esc(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{esc(item)}</td>" for item in row) + "</tr>"
        for row in rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def image_block(path: Path, title: str, caption: str, eager: bool = False) -> str:
    rel = relative_asset(path)
    return f"""
    <figure class="evidence-figure">
      <a href="{esc(rel)}" target="_blank" rel="noopener">
        <img src="{esc(rel)}" alt="{esc(title)}" loading="{'eager' if eager else 'lazy'}">
      </a>
      <figcaption><strong>{esc(title)}</strong><br>{caption}</figcaption>
    </figure>
    """


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_figure(fig: Any, name: str) -> Path:
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    path = VIS_DIR / name
    fig.savefig(path, dpi=175, bbox_inches="tight")
    plt.close(fig)
    return path


def provenance_summary(data: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_id in ("R01ZF", "R02ZF", "R03ZF", "R04ZF"):
        raw = data[(data["run_id"] == run_id) & (data["interface_kind"] == RAW_INTERFACE)]
        stitched = data[(data["run_id"] == run_id) & (data["interface_kind"] == STITCHED_INTERFACE)]
        rows.append(
            {
                "run_id": run_id,
                "raw_fragment_tracks": int(len(raw)),
                "stitched_accepted_tracks": int(len(stitched)),
                "stitched_ambiguous_count_sum": int(
                    pd.to_numeric(stitched["ambiguous_stitch_count_max"], errors="coerce").fillna(0).sum()
                ),
                "stitched_tracks_with_interpolation": int(as_bool(stitched["contains_posthoc_interpolation"]).sum()),
            }
        )
    return rows


def plot_provenance(rows: list[dict[str, Any]]) -> Path:
    labels = [row["run_id"] for row in rows]
    raw = [row["raw_fragment_tracks"] for row in rows]
    stitched = [row["stitched_accepted_tracks"] for row in rows]
    ambiguous = [row["stitched_ambiguous_count_sum"] for row in rows]
    x = np.arange(len(labels))
    width = 0.24
    fig, axis = plt.subplots(figsize=(9.5, 5.1), constrained_layout=True)
    bars1 = axis.bar(x - width, raw, width, label="自动 raw fragments", color="#2878b5")
    bars2 = axis.bar(x, stitched, width, label="stitched accepted proxy", color="#45a778")
    bars3 = axis.bar(x + width, ambiguous, width, label="stitched ambiguous 计数和", color="#d68c45")
    axis.set_xticks(x, labels)
    axis.set_ylabel("track / ambiguity count")
    axis.set_title("光学 track 来源：fragmentation 与离线 stitching 断点")
    axis.set_ylim(0, max(raw + stitched + ambiguous) + 5)
    axis.grid(axis="y", alpha=0.22)
    axis.legend(frameon=False, ncol=3, loc="upper right")
    for bars in (bars1, bars2, bars3):
        axis.bar_label(bars, padding=2, fontsize=9)
    axis.text(
        0.01,
        0.94,
        "R02: 33 raw fragments → 9 stitched tracks，accepted 中 ambiguous 合计 10",
        transform=axis.transAxes,
        va="top",
        fontsize=9,
        color="#694119",
    )
    return save_figure(fig, "report_optical_track_provenance.png")


def plot_time_tradeoff(time_data: pd.DataFrame) -> Path:
    raw = time_data[time_data["interface_kind"] == RAW_INTERFACE].sort_values(
        "time_window_half_width_ms"
    )
    x = raw["time_window_half_width_ms"].to_numpy(dtype=float)
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.8), constrained_layout=True)
    axes[0].plot(x, 100 * raw["reference_any_track_candidate_retention_0p8m"], "o-", lw=2.2, label="reference 邻近候选保留")
    axes[0].plot(x, 100 * raw["reference_any_track_coverage"], "s--", lw=1.8, label="reference 方位覆盖")
    axes[0].plot(x, 100 * raw["reference_track_prior_availability_fraction"], "^:", lw=1.8, label="track prior 可用")
    axes[0].set_title("时间半窗增大：保留率提高")
    axes[0].set_xlabel("居中时间半窗 / ms")
    axes[0].set_ylabel("比例 / %")
    axes[0].set_ylim(65, 102)
    axes[0].grid(alpha=0.23)
    axes[0].legend(frameon=False, fontsize=9)

    axes[1].plot(x, 100 * raw["single_track_candidate_burden_median_given_artifact_and_shell"], "o-", lw=2.2, label="单 track burden 中位")
    axes[1].plot(x, 100 * raw["all_track_union_candidate_burden_median_given_artifact_and_shell"], "s--", lw=1.9, label="all-track union burden")
    axes[1].plot(x, 100 * raw["sum_track_branch_burden_median_given_artifact_and_shell"], "^:", lw=1.9, label="分支 burden 求和")
    axes[1].plot(x, 100 * raw["duplicate_branch_fraction_median_given_artifact_and_shell"], "d-.", lw=1.5, label="分支重复比例")
    axes[1].set_title("同时：搜索负担与分支重复上升")
    axes[1].set_xlabel("居中时间半窗 / ms")
    axes[1].set_ylabel("候选负担 / %")
    axes[1].grid(alpha=0.23)
    axes[1].legend(frameon=False, fontsize=9)
    fig.suptitle("RAW automatic fragment 接口的时间不确定度—搜索成本权衡", fontsize=14, weight="bold")
    return save_figure(fig, "report_time_window_retention_burden_tradeoff.png")


def entity_coverage_summary(entity_data: pd.DataFrame) -> list[dict[str, Any]]:
    q95 = entity_data[np.isclose(entity_data["percentile_level"], 0.95)].copy()
    groups = [
        ("PERSON_REFERENCE", "PERSON reference"),
        ("FIXED_OFFSET_CONTROL", "固定径向/切向偏移"),
        ("GEOMETRY_MATCHED_CONTROL", "几何匹配空间对照"),
        ("LOCAL_COMPETING_CONTROL", "局部竞争响应"),
    ]
    rows: list[dict[str, Any]] = []
    for entity_kind, label in groups:
        selected = q95[q95["entity_kind"] == entity_kind]
        rows.append(
            {
                "entity_kind": entity_kind,
                "label": label,
                "rows": int(len(selected)),
                "direct_inside": float(as_bool(selected["entity_directly_inside_region"]).mean()),
                "near_0p30m": float(as_bool(selected["region_near_entity_0p30m"]).mean()),
            }
        )
    return rows


def plot_entity_coverage(rows: list[dict[str, Any]]) -> Path:
    labels = [row["label"] for row in rows]
    direct = [100 * row["direct_inside"] for row in rows]
    near = [100 * row["near_0p30m"] for row in rows]
    x = np.arange(len(labels))
    width = 0.36
    fig, axis = plt.subplots(figsize=(10.5, 5.2), constrained_layout=True)
    b1 = axis.bar(x - width / 2, direct, width, label="reference/control 点直接落入 q95 region", color="#276fbf")
    b2 = axis.bar(x + width / 2, near, width, label="0.30 m 内存在 q95 region", color="#69b578")
    axis.set_xticks(x, labels, rotation=10, ha="right")
    axis.set_ylim(0, 105)
    axis.set_ylabel("覆盖比例 / %")
    axis.set_title("冻结 C2 response-region 的位置特异性与局部竞争")
    axis.grid(axis="y", alpha=0.23)
    axis.legend(frameon=False, fontsize=9)
    axis.bar_label(b1, labels=[f"{value:.1f}%" for value in direct], padding=2, fontsize=8)
    axis.bar_label(b2, labels=[f"{value:.1f}%" for value in near], padding=2, fontsize=8)
    for index, row in enumerate(rows):
        axis.text(index, 2, f"n={row['rows']}", ha="center", va="bottom", fontsize=8, color="#34495e")
    return save_figure(fig, "report_q95_reference_control_region_coverage.png")


def r02_rank_summary(track_summary: pd.DataFrame) -> list[dict[str, Any]]:
    selected = track_summary[
        (track_summary["run_id"] == "R02ZF")
        & (track_summary["interface_kind"] == RAW_INTERFACE)
        & (track_summary["time_window_half_width_ms"] == 250)
    ].copy()
    rows: list[dict[str, Any]] = []
    for suffix in ("01", "02", "03", "04"):
        group = selected[selected["target_id"].astype(str).str.endswith(suffix)]
        rows.append(
            {
                "person": f"P{suffix}",
                "reference_rows": int(len(group)),
                "global_rank_median": float(pd.to_numeric(group["best_track_global_rank_0p8m_offline_eval"], errors="coerce").median()),
                "union_rank_median": float(pd.to_numeric(group["union_local_rank_0p8m"], errors="coerce").median()),
                "track_rank_median": float(pd.to_numeric(group["best_track_local_rank_0p8m_offline_eval"], errors="coerce").median()),
                "retention_fraction": float(as_bool(group["any_track_candidate_retention_0p8m"]).mean()),
                "valid_rank_rows": int(pd.to_numeric(group["best_track_global_rank_0p8m_offline_eval"], errors="coerce").notna().sum()),
            }
        )
    return rows


def plot_r02_ranks(rows: list[dict[str, Any]]) -> Path:
    labels = [row["person"] for row in rows]
    global_rank = [row["global_rank_median"] for row in rows]
    union_rank = [row["union_rank_median"] for row in rows]
    track_rank = [row["track_rank_median"] for row in rows]
    x = np.arange(len(labels))
    width = 0.24
    fig, axis = plt.subplots(figsize=(9.8, 5.2), constrained_layout=True)
    b1 = axis.bar(x - width, global_rank, width, label="全扇面 global rank", color="#9aa6b2")
    b2 = axis.bar(x, union_rank, width, label="all-track union local rank", color="#4c91d9")
    b3 = axis.bar(x + width, track_rank, width, label="offline best-track local rank", color="#42a66b")
    axis.set_xticks(x, labels)
    axis.set_ylabel("rank 中位数（越低越好）")
    axis.set_title("R02：track-conditioned 方位压缩改变问题规模，但不等于唯一定位")
    axis.grid(axis="y", alpha=0.22)
    axis.legend(frameon=False, fontsize=9)
    axis.set_ylim(0, max(global_rank + union_rank + track_rank) + 4)
    for bars in (b1, b2, b3):
        axis.bar_label(bars, padding=2, fontsize=9, fmt="%.0f")
    for index, row in enumerate(rows):
        axis.text(index, max(global_rank[index], union_rank[index], track_rank[index]) + 0.9, f"有 rank {row['valid_rank_rows']}/{row['reference_rows']}", ha="center", fontsize=8)
    return save_figure(fig, "report_r02_global_union_track_rank.png")


def shell_pair_jaccard_summary(assignments: pd.DataFrame, overlap: pd.DataFrame) -> list[dict[str, Any]]:
    a = assignments[
        (assignments["run_id"] == "R02ZF")
        & (assignments["interface_kind"] == RAW_INTERFACE)
    ].copy()
    o = overlap[(overlap["run_id"] == "R02ZF") & (overlap["interface_kind"] == RAW_INTERFACE)].copy()
    rows: list[dict[str, Any]] = []
    for left_suffix, right_suffix, label in (("01", "02", "P01/P02"), ("03", "04", "P03/P04")):
        for window_ms in (0, 100, 250, 500):
            values: list[float] = []
            window_assignments = a[a["time_window_half_width_ms"] == window_ms]
            for frame_uid, group in window_assignments.groupby("frame_uid", sort=False):
                left = group[group["target_id"].astype(str).str.endswith(left_suffix)]
                right = group[group["target_id"].astype(str).str.endswith(right_suffix)]
                if len(left) != 1 or len(right) != 1:
                    continue
                left_track = left.iloc[0]["assigned_track_id_offline"]
                right_track = right.iloc[0]["assigned_track_id_offline"]
                if pd.isna(left_track) or pd.isna(right_track) or left_track == right_track:
                    continue
                candidates = o[
                    (o["frame_uid"] == frame_uid)
                    & (o["time_window_half_width_ms"] == window_ms)
                    & (
                        ((o["left_track_id"] == left_track) & (o["right_track_id"] == right_track))
                        | ((o["left_track_id"] == right_track) & (o["right_track_id"] == left_track))
                    )
                ]
                if len(candidates) == 1:
                    values.append(float(candidates.iloc[0]["angular_jaccard"]))
            rows.append(
                {
                    "pair": label,
                    "window_ms": window_ms,
                    "frame_rows": len(values),
                    "median": float(np.median(values)) if values else math.nan,
                    "q25": float(np.quantile(values, 0.25)) if values else math.nan,
                    "q75": float(np.quantile(values, 0.75)) if values else math.nan,
                    "semantics": "OFFLINE_ONE_TO_ONE_REFERENCE_ASSOCIATION_USED_ONLY_AFTER_ALL_RUNTIME_SHELLS_EXIST",
                }
            )
    return rows


def plot_shell_jaccard(rows: list[dict[str, Any]]) -> Path:
    fig, axis = plt.subplots(figsize=(9.7, 5.0), constrained_layout=True)
    colors = {"P01/P02": "#2c78bf", "P03/P04": "#c46d34"}
    for pair in ("P01/P02", "P03/P04"):
        selected = [row for row in rows if row["pair"] == pair]
        x = np.asarray([row["window_ms"] for row in selected], dtype=float)
        y = np.asarray([row["median"] for row in selected], dtype=float)
        low = np.asarray([row["q25"] for row in selected], dtype=float)
        high = np.asarray([row["q75"] for row in selected], dtype=float)
        axis.plot(x, y, "o-", lw=2.1, label=pair, color=colors[pair])
        axis.fill_between(x, low, high, alpha=0.16, color=colors[pair])
        for row in selected:
            if finite(row["median"]):
                axis.text(row["window_ms"], row["median"] + 0.018, f"n={row['frame_rows']}", ha="center", fontsize=8, color=colors[pair])
    axis.set_ylim(0.35, 0.88)
    axis.set_xlabel("居中时间半窗 / ms")
    axis.set_ylabel("两条 offline-associated track shells 的角度 Jaccard")
    axis.set_title("R02 track 壳仍显著重叠；窗口越宽不自动带来身份分离")
    axis.grid(alpha=0.23)
    axis.legend(frameon=False)
    axis.text(
        0.01,
        0.02,
        "每个窗口的可关联帧数不同；reference 只用于壳全部生成后的离线配对，不参与壳生成。",
        transform=axis.transAxes,
        fontsize=8.5,
        color="#556270",
    )
    return save_figure(fig, "report_r02_track_shell_jaccard.png")


def draw_reference_and_peaks(
    axis: Any,
    frame_refs: pd.DataFrame,
    focus_refs: pd.DataFrame,
    frame_candidates: pd.DataFrame,
    px_per_m: float,
    annotate_nearest: bool,
) -> None:
    if len(frame_candidates):
        axis.scatter(
            frame_candidates["x_px"],
            frame_candidates["y_px"],
            s=np.clip(35 - 0.06 * pd.to_numeric(frame_candidates["rank"], errors="coerce"), 5, 28),
            facecolors="none",
            edgecolors="white",
            linewidths=0.7,
            alpha=0.65,
        )
    focus_ids = set(focus_refs["target_id"].astype(str))
    for index, ref in enumerate(frame_refs.itertuples(index=False)):
        is_focus = str(ref.target_id) in focus_ids
        color = plt.get_cmap("Set1")(index % 9)
        axis.scatter(
            ref.reference_x_px,
            ref.reference_y_px,
            marker="x",
            s=100 if is_focus else 55,
            c=[color],
            linewidths=2.8 if is_focus else 1.4,
            alpha=1.0 if is_focus else 0.45,
            zorder=9,
        )
        if is_focus:
            axis.text(
                ref.reference_x_px + 4,
                ref.reference_y_px - 4,
                target_label(ref.target_id),
                color=color,
                fontsize=9,
                weight="bold",
                zorder=10,
            )
            if annotate_nearest and len(frame_candidates):
                dx = frame_candidates["x_px"].to_numpy(dtype=float) - float(ref.reference_x_px)
                dy = frame_candidates["y_px"].to_numpy(dtype=float) - float(ref.reference_y_px)
                nearest_index = int(np.argmin(dx * dx + dy * dy))
                nearest = frame_candidates.iloc[nearest_index]
                distance_m = math.hypot(float(nearest.x_px) - float(ref.reference_x_px), float(nearest.y_px) - float(ref.reference_y_px)) / px_per_m
                axis.plot(
                    [ref.reference_x_px, nearest.x_px],
                    [ref.reference_y_px, nearest.y_px],
                    linestyle="--",
                    linewidth=1.1,
                    color=color,
                    alpha=0.85,
                    zorder=8,
                )
                axis.text(
                    nearest.x_px + 3,
                    nearest.y_px + 3,
                    f"r{int(nearest['rank'])} / {distance_m:.2f}m",
                    color=color,
                    fontsize=7.5,
                    bbox={"facecolor": "black", "alpha": 0.42, "edgecolor": "none", "pad": 1.2},
                    zorder=10,
                )


def local_case_caption_rows(
    case: pd.Series,
    focus_refs: pd.DataFrame,
    reference_region: pd.DataFrame,
    track_summary: pd.DataFrame,
) -> list[str]:
    frame_uid = str(case["frame_uid"])
    q95 = reference_region[
        (reference_region["frame_uid"] == frame_uid)
        & np.isclose(reference_region["percentile_level"], 0.95)
        & reference_region["target_id"].isin(focus_refs["target_id"])
    ]
    raw250 = track_summary[
        (track_summary["frame_uid"] == frame_uid)
        & (track_summary["interface_kind"] == RAW_INTERFACE)
        & (track_summary["time_window_half_width_ms"] == 250)
        & track_summary["target_id"].isin(focus_refs["target_id"])
    ]
    lines: list[str] = []
    for row in q95.itertuples(index=False):
        line = (
            f"{target_label(row.target_id)}: {row.representation_state}"
            f"{' / SHARED' if bool(row.shared_region_flag) else ''}; "
            f"C2 pct={float(row.reference_C2_percentile_existing):.3f}; "
            f"peak r={int(row.nearest_peak_rank_existing) if finite(row.nearest_peak_rank_existing) else '—'}"
            f"/{num(row.nearest_peak_distance_m_existing, 2)}m; "
            f"region={row.nearest_region_structure_state}"
        )
        track = raw250[raw250["target_id"] == row.target_id]
        if len(track) == 1:
            item = track.iloc[0]
            line += (
                f"; global→union→track={num(item.best_track_global_rank_0p8m_offline_eval,0)}"
                f"→{num(item.union_local_rank_0p8m,0)}→{num(item.best_track_local_rank_0p8m_offline_eval,0)}"
            )
        lines.append(line)
    return lines


def render_local_cases(
    cases: pd.DataFrame,
    reference_region: pd.DataFrame,
    track_summary: pd.DataFrame,
) -> list[dict[str, Any]]:
    analysis = load_module("person_runtime_track_region_report_analysis", ANALYSIS_SCRIPT)
    p0 = analysis.load_module("person_runtime_track_region_report_p0", analysis.P0_SCRIPT)
    p1e = analysis.load_module("person_runtime_track_region_report_p1e", analysis.P1E_SCRIPT)
    candidate_module = analysis.load_module(
        "person_runtime_track_region_report_candidate", analysis.CANDIDATE_SCRIPT
    )
    frames, _ = analysis.load_explorer_sanitized()
    frame_map = {str(frame["sar_frame_uid"]): frame for frame in frames}
    references_all = pd.read_csv(analysis.REFERENCES_CSV, low_memory=False)
    references = references_all[references_all["candidate"] == PRIMARY_CANDIDATE].copy()
    candidates_all = pd.read_csv(analysis.CANDIDATES_CSV, low_memory=False)
    candidates = candidates_all[candidates_all["candidate"] == PRIMARY_CANDIDATE].copy()
    shells = pd.read_csv(SHELL_DEFINITION_PATH, low_memory=False)

    outputs: list[dict[str, Any]] = []
    for case in cases.sort_values("case_index").itertuples(index=False):
        frame_uid = str(case.frame_uid)
        frame = frame_map[frame_uid]
        image_path = p0.file_url_to_path(frame["sar_image_url"])
        image_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image_bgr is None:
            raise FileNotFoundError(image_path)
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        mask, radial, theta, px_per_m = candidate_module.single_frame_observation_mask(
            frame, image_bgr
        )
        maps, _ = candidate_module.compute_existing_candidate_maps_for_mask(
            p1e, frame, image_bgr, mask, radial, theta, px_per_m
        )
        support_radius_px = max(1, int(round(p1e.PHYSICAL_SUPPORT_RADIUS_M * px_per_m)))
        evaluation_maps = p1e.build_evaluation_maps(
            maps, mask, support_radius_px, "fixed_support_mean_v2"
        )
        score = evaluation_maps[PRIMARY_CANDIDATE]
        archive = np.load(MASK_DIR / f"{frame_uid}.npz")
        labels90 = archive["Q090"]
        labels95 = archive["Q095"]
        labels975 = archive["Q0975"]
        frame_refs = references[references["frame_uid"] == frame_uid].copy()
        suffixes = FOCUS_TARGET_SUFFIXES.get(str(case.case_slug), tuple())
        focus_refs = frame_refs[
            frame_refs["target_id"].astype(str).str.endswith(suffixes)
        ].copy() if suffixes else frame_refs.copy()
        if focus_refs.empty:
            focus_refs = frame_refs.copy()
        frame_candidates = candidates[candidates["frame_uid"] == frame_uid].copy()
        margin_px = 2.2 * float(px_per_m)
        x0 = max(0, int(math.floor(focus_refs["reference_x_px"].min() - margin_px)))
        x1 = min(image_rgb.shape[1] - 1, int(math.ceil(focus_refs["reference_x_px"].max() + margin_px)))
        y0 = max(0, int(math.floor(focus_refs["reference_y_px"].min() - margin_px)))
        y1 = min(image_rgb.shape[0] - 1, int(math.ceil(focus_refs["reference_y_px"].max() + margin_px)))
        min_span = int(round(4.2 * px_per_m))
        if x1 - x0 < min_span:
            center = (x0 + x1) // 2
            x0 = max(0, center - min_span // 2)
            x1 = min(image_rgb.shape[1] - 1, x0 + min_span)
            x0 = max(0, x1 - min_span)
        if y1 - y0 < min_span:
            center = (y0 + y1) // 2
            y0 = max(0, center - min_span // 2)
            y1 = min(image_rgb.shape[0] - 1, y0 + min_span)
            y0 = max(0, y1 - min_span)

        raw_shells = shells[
            (shells["frame_uid"] == frame_uid)
            & (shells["interface_kind"] == RAW_INTERFACE)
            & (shells["time_window_half_width_ms"] == 250)
            & (shells["shell_scope"] == "TRACK")
        ]
        fig, axes = plt.subplots(2, 2, figsize=(11.6, 9.2), constrained_layout=True)
        axes[0, 0].imshow(image_rgb)
        axes[0, 0].set_title("原始 SAR 伪彩图 + 冻结 GT-blind peaks")
        draw_reference_and_peaks(axes[0, 0], frame_refs, focus_refs, frame_candidates, px_per_m, True)

        axes[0, 1].imshow(score, cmap="magma", vmin=0, vmax=1)
        axes[0, 1].contour(labels95 > 0, levels=[0.5], colors=["#5af0ff"], linewidths=1.2)
        axes[0, 1].set_title("实际候选输入 S(x) + q95 连通 region")
        draw_reference_and_peaks(axes[0, 1], frame_refs, focus_refs, frame_candidates, px_per_m, False)

        axes[1, 0].imshow(image_rgb)
        axes[1, 0].contour(labels90 > 0, levels=[0.5], colors=["#ffd166"], linewidths=1.0)
        axes[1, 0].contour(labels95 > 0, levels=[0.5], colors=["#5af0ff"], linewidths=1.5)
        axes[1, 0].contour(labels975 > 0, levels=[0.5], colors=["#ff4da6"], linewidths=1.0)
        axes[1, 0].set_title("q90 / q95 / q97.5 表示敏感性")
        draw_reference_and_peaks(axes[1, 0], frame_refs, focus_refs, frame_candidates, px_per_m, False)

        axes[1, 1].imshow(image_rgb)
        analysis.draw_shell_rays(axes[1, 1], frame, raw_shells, plt.get_cmap("tab10"))
        axes[1, 1].set_title(f"全部 RAW track 壳 · ±250 ms · {len(raw_shells)} branches")
        draw_reference_and_peaks(axes[1, 1], frame_refs, focus_refs, frame_candidates.iloc[0:0], px_per_m, False)

        for axis in axes.ravel():
            axis.set_xlim(x0, x1)
            axis.set_ylim(y1, y0)
            axis.set_xticks([])
            axis.set_yticks([])
        focus_series = pd.Series(case._asdict())
        detail_lines = local_case_caption_rows(
            focus_series, focus_refs, reference_region, track_summary
        )
        fig.suptitle(
            f"{frame_uid} · {case.case_slug}\n"
            + "\n".join(detail_lines)
            + "\nreference 仅为离线叠加；region / peak / track shells 均已先生成",
            fontsize=11.5,
            weight="bold",
        )
        path = save_figure(
            fig,
            f"local_zoom_case_{int(case.case_index):02d}_{case.case_slug}.png",
        )
        outputs.append(
            {
                "case_index": int(case.case_index),
                "frame_uid": frame_uid,
                "case_slug": str(case.case_slug),
                "focus_targets": [target_label(value) for value in focus_refs["target_id"]],
                "local_visualization_path": str(path),
                "full_visualization_path": str(case.visualization_path),
                "detail_lines": detail_lines,
            }
        )
    return outputs


def case_caption(case: dict[str, Any]) -> str:
    slug = case["case_slug"]
    captions = {
        "R02_F482_PEAK_MISSING_REGION": "P02 reference 处 C2 percentile 0.959；最近离散峰 rank 14、距 1.159 m，但 reference 直接落入 q95 extended region。该 region 与 P01 共享，表示 response present / peak missing，而不是唯一定位。",
        "R02_F490_RADIUS_SENSITIVE_REGION": "P02 percentile 0.993；最近峰距 0.820 m，刚超过固定 0.8 m。q95 region 主轴约 4.09 m，包含多个既有 peak，说明固定峰半径对 missing 语义敏感。",
        "R02_P03_P04_SHARED_REGION": "P03/P04 同处一个 compact q95 region；P01/P02 同时处于另一 shared extended region。这里只能描述图像域 shared / 未分离，不能声称物理散射融合。",
        "R03_OUTER_RANGE_BOUNDARY_OBSERVATION": "R03 F458 距最大距离边界约 0.888 m，冻结 P0 为 EXTENDED；但单帧 q95 region 与 peak 都存在，直接说明 P0 transport core 与单帧可观察域不是同一个 mask。",
        "R04_F0_CLEAR_PEAK_PRESENT": "清晰的 PEAK_PRESENT 对照病例，用于说明 region 表示并非只为修补困难帧；离散峰与紧凑 region 可以一致。",
        "R04_F35_Q90_ONLY_BORDERLINE": "P01 reference percentile 0.916、最近峰 rank 86；0.30 m 内只有 q90 region，没有 q95 region。它保留弱/边缘状态，而不是通过调阈值把病例强行救成 q95。",
        "R02_P01_LOW_RANK_TRACK_SHELL": "R02 P01 低 rank 病例：全部 runtime track 壳先产生，随后离线查看 global→union→track 的问题压缩；这不是人工选择正确 track 的运行时算法。",
    }
    return captions.get(slug, "直接病例。")


def build_report() -> tuple[str, dict[str, Any]]:
    summary = load_json(SUMMARY_PATH)
    time_data = pd.read_csv(TIME_PATH, low_memory=False)
    provenance = pd.read_csv(PROVENANCE_PATH, low_memory=False)
    track_summary = pd.read_csv(TRACK_SUMMARY_PATH, low_memory=False)
    assignments = pd.read_csv(ASSIGNMENT_PATH, low_memory=False)
    reference_region = pd.read_csv(REFERENCE_REGION_PATH, low_memory=False)
    entity_region = pd.read_csv(ENTITY_REGION_PATH, low_memory=False)
    overlap = pd.read_csv(OVERLAP_PATH, low_memory=False)
    candidate_parity = pd.read_csv(CANDIDATE_PARITY_PATH, low_memory=False)
    cases = pd.read_csv(CASE_PATH, low_memory=False)

    provenance_rows = provenance_summary(provenance)
    entity_rows = entity_coverage_summary(entity_region)
    r02_rows = r02_rank_summary(track_summary)
    jaccard_rows = shell_pair_jaccard_summary(assignments, overlap)

    summary_figures = [
        plot_provenance(provenance_rows),
        plot_time_tradeoff(time_data),
        plot_entity_coverage(entity_rows),
        plot_r02_ranks(r02_rows),
        plot_shell_jaccard(jaccard_rows),
    ]
    local_cases = render_local_cases(cases, reference_region, track_summary)

    raw_time = time_data[time_data["interface_kind"] == RAW_INTERFACE].sort_values(
        "time_window_half_width_ms"
    )
    q95 = reference_region[np.isclose(reference_region["percentile_level"], 0.95)].copy()
    shared_by_run = {
        run_id: float(as_bool(group["shared_region_flag"]).mean())
        for run_id, group in q95.groupby("run_id")
    }
    peak_missing = q95[q95["representation_state"] == "PEAK_MISSING_REGION_PRESENT"]
    q90_only = q95[q95["superlevel_presence_state"] == "Q090_ONLY_REGION_PRESENT"]
    covered = candidate_parity[as_bool(candidate_parity["candidate_artifact_frame_covered"])]
    uncovered = candidate_parity[~as_bool(candidate_parity["candidate_artifact_frame_covered"])]

    derived = {
        "schema": "PERSON_P1E_RUNTIME_TRACK_RESPONSE_REGION_REPORT_DERIVED_V1",
        "created_at": now_iso(),
        "status": "REPORT_LAYER_ONLY_NO_EXPERIMENT_RETUNING",
        "analysis_summary_status": summary["status"],
        "analysis_script_sha256": sha256_file(ANALYSIS_SCRIPT),
        "report_script_sha256": sha256_file(SCRIPT_PATH),
        "provenance_by_run": provenance_rows,
        "time_uncertainty_raw_interface": raw_time.to_dict("records"),
        "q95_entity_coverage": entity_rows,
        "r02_rank_summary": r02_rows,
        "r02_offline_associated_shell_jaccard": jaccard_rows,
        "q95_shared_fraction_by_run": shared_by_run,
        "peak_missing_region_present_rows": peak_missing[
            ["frame_uid", "target_id", "reference_C2_percentile_existing", "nearest_peak_rank_existing", "nearest_peak_distance_m_existing", "nearest_region_area_m2", "nearest_region_major_extent_m", "nearest_region_structure_state", "shared_region_flag"]
        ].to_dict("records"),
        "q090_only_rows": q90_only[
            ["frame_uid", "target_id", "reference_C2_percentile_existing", "nearest_peak_rank_existing", "nearest_peak_distance_m_existing"]
        ].to_dict("records"),
        "candidate_artifact_coverage": {
            "covered_frames": int(len(covered)),
            "uncovered_frames": int(len(uncovered)),
            "covered_all_exact_match": bool(as_bool(covered["all_candidate_fields_match"]).all()),
            "uncovered_semantics": "NO_LEGACY_CANDIDATE_ARTIFACT_FOR_FRAME_NOT_ZERO_CANDIDATES",
        },
        "summary_figures": [str(path) for path in summary_figures],
        "local_cases": local_cases,
    }
    DERIVED_PATH.write_text(
        json.dumps(json_safe(derived), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    time_rows = [
        [
            int(row.time_window_half_width_ms),
            pct(row.reference_track_prior_availability_fraction),
            pct(row.reference_any_track_candidate_retention_0p8m),
            pct(row.single_track_candidate_burden_median_given_artifact_and_shell),
            pct(row.all_track_union_candidate_burden_median_given_artifact_and_shell),
            pct(row.sum_track_branch_burden_median_given_artifact_and_shell),
            pct(row.duplicate_branch_fraction_median_given_artifact_and_shell),
        ]
        for row in raw_time.itertuples(index=False)
    ]
    provenance_table_rows = [
        [
            row["run_id"],
            row["raw_fragment_tracks"],
            row["stitched_accepted_tracks"],
            row["stitched_ambiguous_count_sum"],
            row["stitched_tracks_with_interpolation"],
        ]
        for row in provenance_rows
    ]
    r02_table_rows = [
        [
            row["person"],
            row["reference_rows"],
            f"{num(row['global_rank_median'],0)} → {num(row['union_rank_median'],0)} → {num(row['track_rank_median'],0)}",
            f"{row['valid_rank_rows']}/{row['reference_rows']}",
            pct(row["retention_fraction"]),
        ]
        for row in r02_rows
    ]
    coverage_table_rows = [
        [row["label"], row["rows"], pct(row["direct_inside"]), pct(row["near_0p30m"])]
        for row in entity_rows
    ]
    jaccard_table_rows = [
        [row["pair"], row["window_ms"], row["frame_rows"], num(row["median"], 3), f"{num(row['q25'],3)}–{num(row['q75'],3)}"]
        for row in jaccard_rows
    ]
    missing_table_rows = [
        [
            row.frame_uid,
            target_label(row.target_id),
            num(row.reference_C2_percentile_existing, 3),
            int(row.nearest_peak_rank_existing),
            num(row.nearest_peak_distance_m_existing, 3),
            num(row.nearest_region_area_m2, 3),
            num(row.nearest_region_major_extent_m, 3),
            row.nearest_region_structure_state,
            "是" if bool(row.shared_region_flag) else "否",
        ]
        for row in peak_missing.itertuples(index=False)
    ]
    q90_table_rows = [
        [
            row.frame_uid,
            target_label(row.target_id),
            num(row.reference_C2_percentile_existing, 3),
            int(row.nearest_peak_rank_existing),
            num(row.nearest_peak_distance_m_existing, 3),
        ]
        for row in q90_only.itertuples(index=False)
    ]

    summary_figure_meta = [
        (summary_figures[0], "光学 track provenance", "raw fragment 是主运行时近似接口；stitched accepted 只是全 run 的 GT-blind offline continuity proxy。"),
        (summary_figures[1], "时间窗的保留率—负担权衡", "窗口增大同时提高保留率、壳宽、候选负担和分支重复；不能看 SAR 结果后选择所谓最优窗口。"),
        (summary_figures[2], "q95 response-region 的 reference/control 覆盖", "PERSON reference 的直接覆盖很高，但 local competing response 也高，说明区域表示恢复 response presence，不授予唯一性。"),
        (summary_figures[3], "R02 global→union→track rank", "P01/P02 进一步变简单；P03/P04 仍是高 rank shared，track 壳没有解决 SAR 局部未分离。"),
        (summary_figures[4], "R02 两 track 壳重叠", "离线 reference 只在全部壳生成后用于配对评价；窗口分母不同，图只用于说明壳没有形成稳定空间分离。"),
    ]
    summary_figure_html = "".join(
        image_block(path, title, caption, eager=index < 2)
        for index, (path, title, caption) in enumerate(summary_figure_meta)
    )

    local_case_map = {item["case_slug"]: item for item in local_cases}
    case_html_parts: list[str] = []
    for index, case in enumerate(cases.sort_values("case_index").itertuples(index=False)):
        local = local_case_map[str(case.case_slug)]
        caption = case_caption(local)
        case_html_parts.append(
            f'<article class="case-block"><h3>病例 {int(case.case_index):02d} · {esc(case.frame_uid)}</h3>'
            f'<p>{caption}</p><div class="figure-grid">'
            + image_block(Path(local["local_visualization_path"]), "局部放大", "原图、实际 S(x)、q90/q95/q97.5 和全部 RAW track 壳；reference 仅离线叠加。", eager=index == 0)
            + image_block(Path(local["full_visualization_path"]), "全扇面六联图", "用于同时核查扇面边界、全局 C2 结构、全部 track 壳和 response-region 敏感性。")
            + "</div></article>"
        )
    case_html = "".join(case_html_parts)

    output_files = [
        PROTOCOL_PATH,
        PROVENANCE_AMENDMENT_PATH,
        REGION_AMENDMENT_PATH,
        SUMMARY_PATH,
        DERIVED_PATH,
        TIME_PATH,
        PROVENANCE_PATH,
        FRAME_BURDEN_PATH,
        TRACK_SUMMARY_PATH,
        ASSIGNMENT_PATH,
        REGION_PATH,
        REFERENCE_REGION_PATH,
        ENTITY_REGION_PATH,
        ENTITY_SUMMARY_PATH,
        INTERSECTION_PATH,
        OVERLAP_PATH,
        CANDIDATE_PARITY_PATH,
        CASE_PATH,
    ]
    output_links = "".join(
        f'<a href="{esc(relative_asset(path))}" target="_blank" rel="noopener">{esc(path.name)}</a>'
        for path in output_files
    )

    person_entity = next(row for row in entity_rows if row["entity_kind"] == "PERSON_REFERENCE")
    fixed_entity = next(row for row in entity_rows if row["entity_kind"] == "FIXED_OFFSET_CONTROL")
    geometry_entity = next(row for row in entity_rows if row["entity_kind"] == "GEOMETRY_MATCHED_CONTROL")
    local_entity = next(row for row in entity_rows if row["entity_kind"] == "LOCAL_COMPETING_CONTROL")
    raw250 = raw_time[raw_time["time_window_half_width_ms"] == 250].iloc[0]

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PERSON P1E · runtime optical track 壳与 C2 response-region 最小实验</title>
  <style>
    :root {{ --ink:#13283b; --muted:#5b6a78; --paper:#f4f7fa; --card:#fff; --line:#d8e1e9; --blue:#276fbf; --green:#16866f; --orange:#c36a24; --pink:#b63d72; --purple:#7656a5; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--paper); color:var(--ink); font:15px/1.7 "Segoe UI","Microsoft YaHei",sans-serif; }}
    header {{ padding:48px max(24px,calc((100vw - 1220px)/2)); color:white; background:linear-gradient(126deg,#10283c,#1d5366 58%,#17725e); }}
    header h1 {{ margin:0 0 12px; font-size:clamp(30px,4vw,50px); line-height:1.14; }}
    header p {{ max-width:1000px; margin:8px 0; color:#dcecf1; font-size:17px; }}
    .status {{ display:inline-block; margin-top:14px; padding:7px 12px; border:1px solid #81cbb7; border-radius:999px; background:#0b5143; font-weight:800; }}
    nav {{ position:sticky; top:0; z-index:6; display:flex; gap:8px; overflow:auto; padding:10px max(20px,calc((100vw - 1220px)/2)); background:#ffffffee; border-bottom:1px solid var(--line); backdrop-filter:blur(8px); }}
    nav a {{ color:#284760; text-decoration:none; white-space:nowrap; padding:5px 9px; border-radius:7px; }} nav a:hover {{ background:#e8f0f6; }}
    main {{ width:min(1220px,calc(100% - 32px)); margin:28px auto 80px; }}
    section,.case-block {{ margin:24px 0; padding:26px; background:var(--card); border:1px solid var(--line); border-radius:16px; box-shadow:0 8px 28px #18334b08; }}
    .case-block {{ padding:20px; background:#fbfcfe; }}
    h2 {{ margin:0 0 16px; font-size:28px; }} h3 {{ margin:0 0 8px; font-size:19px; }}
    .lead {{ font-size:17px; color:#354c60; }}
    .grid-2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }}
    .grid-4 {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }}
    .card {{ padding:18px; border:1px solid var(--line); border-radius:12px; background:#fbfcfe; }}
    .metric {{ padding:16px; border-left:4px solid var(--blue); border-radius:10px; background:#f1f6fc; }}
    .metric strong {{ display:block; font-size:26px; color:#174f91; }}
    .callout {{ margin:16px 0; padding:16px 18px; border-left:5px solid var(--green); background:#edf9f5; border-radius:10px; }}
    .warning {{ border-left-color:var(--orange); background:#fff6eb; }}
    .negative {{ border-left-color:var(--pink); background:#fff1f6; }}
    .purple {{ border-left-color:var(--purple); background:#f6f1fb; }}
    .table-wrap {{ overflow:auto; margin:14px 0; }} table {{ width:100%; border-collapse:collapse; min-width:760px; }} th,td {{ padding:9px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }} th {{ position:sticky; top:0; background:#edf3f7; color:#31485c; }}
    .figure-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }}
    .evidence-figure {{ margin:0; padding:12px; border:1px solid var(--line); border-radius:12px; background:#fbfcfe; }} .evidence-figure img {{ display:block; width:100%; height:auto; border-radius:8px; }} figcaption {{ padding:10px 3px 2px; color:var(--muted); }}
    code {{ padding:2px 5px; border-radius:5px; background:#edf2f6; }}
    .answer .q {{ color:var(--blue); font-weight:800; margin-bottom:6px; }}
    .file-links {{ display:flex; flex-wrap:wrap; gap:9px; }} .file-links a {{ padding:7px 10px; border:1px solid var(--line); border-radius:8px; color:#215586; text-decoration:none; background:#f8fbff; }}
    .foot {{ color:var(--muted); font-size:13px; }}
    @media (max-width:880px) {{ .grid-2,.grid-4,.figure-grid {{ grid-template-columns:1fr; }} section,.case-block {{ padding:19px; }} }}
  </style>
</head>
<body>
<header>
  <h1>运行时光学 track 壳与 C2 response-region：两个接口是否已经站得住</h1>
  <p>本轮没有进入 P2，也没有建立复杂 tracker。它只回答两个更基础的问题：自动 optical tracklet 能否独立缩小 SAR 方位搜索；冻结 C2 连续场能否比 local-max/NMS 离散峰更忠实地表达图像中已经存在的条件性响应。</p>
  <span class="status">COMPLETE_NO_NEW_PASS_FAIL_NO_P2_CLAIM</span>
</header>
<nav><a href="#conclusion">结论</a><a href="#boundary">接口边界</a><a href="#tracks">optical track</a><a href="#time">时间窗</a><a href="#r02">R02</a><a href="#regions">response-region</a><a href="#cases">病例</a><a href="#answers">直接回答</a><a href="#audit">审计</a></nav>
<main>
  <section id="conclusion">
    <h2>一、结论先行</h2>
    <div class="callout"><strong>C2 response-region 接口获得了明确的语义增益：</strong>在已暴露开发语料上，q95 region 直接覆盖 PERSON reference 为 {pct(person_entity['direct_inside'])}，0.30 m 邻近覆盖为 {pct(person_entity['near_0p30m'])}；F482/F490 两条原来的 candidate missing 都变成 <code>PEAK_MISSING_REGION_PRESENT</code>。这说明离散峰曾漏掉图像中已存在的连续响应，不表示已经生成 PERSON 框。</div>
    <div class="callout warning"><strong>runtime optical identity 仍未建立：</strong>主接口是全部自动 detected raw fragments；R02 有 33 个 fragment，而 stitched accepted 只有 9 条且 ambiguous stitch 合计 10。stitched 结果只能作为 GT-blind offline continuity proxy，不能冒充严格在线 track identity。</div>
    <div class="grid-4">
      <div class="metric"><span>398 帧 region 覆盖</span><strong>398 / 398</strong><small>连续 S(x) 与 region masks</small></div>
      <div class="metric"><span>q95 直接覆盖</span><strong>{pct(summary['response_region_primary_q95']['reference_direct_inside_fraction'])}</strong><small>PERSON reference；posthoc 开发语料</small></div>
      <div class="metric"><span>q95 共享比例</span><strong>{pct(summary['response_region_primary_q95']['shared_region_fraction'])}</strong><small>R02 为 {pct(shared_by_run.get('R02ZF'))}</small></div>
      <div class="metric"><span>RAW ±250 ms 保留</span><strong>{pct(raw250.reference_any_track_candidate_retention_0p8m)}</strong><small>union burden 中位 {pct(raw250.all_track_union_candidate_burden_median_given_artifact_and_shell)}</small></div>
    </div>
    <div class="callout negative"><strong>仍未解决：</strong>local competing response 的 q95 直接覆盖仍达 {pct(local_entity['direct_inside'])}，R02 P03/P04 继续 shared；因此 response-region 支持“候选响应存在/形状如何”，没有建立单帧唯一定位。光学 track 壳只缩小方位问题，不直接决定 SAR range、中心或最终响应位置。</div>
  </section>

  <section id="boundary">
    <h2>二、两个接口必须严格分开</h2>
    <div class="grid-2">
      <div class="card"><h3>Optical track-shell 接口</h3><ul><li>输入：自动光学检测/tracklet、固定 optical→SAR 方位映射、固定 guard、预定义时间半窗、SAR 扇面几何；</li><li>输出：每条 track 独立的粗 azimuth shell；</li><li>禁止：人工 <code>physical_target_id</code>、SAR reference、SAR range GT、人工选“正确 track”；</li><li>所有 track 分支均先输出，reference 只在最后离线评价。</li></ul></div>
      <div class="card"><h3>SAR response-region 接口</h3><ul><li>输入：冻结 C2 的实际候选场 <code>S(x)=fixed_support_mean_v2(C2)</code>；</li><li>规则：全有效域 q90/q95/q97.5、4096-bin percentile、8-connectivity；</li><li>不做：形态学桥接、面积删除、watershed、PERSON 个案调阈值；</li><li>region 是显示域条件性响应，不是 PERSON 框，也不是人体固有 RCS 或稳定散射中心。</li></ul></div>
    </div>
    <p class="callout purple"><strong>“runtime”准确口径：</strong>raw fragment 来源最接近现有运行时可获得的自动 tracklet；但本轮 ±100/250/500 ms 使用居中窗口，可能包含未来光学观测。因此它是带缓冲/离线时间不确定度诊断，不是已经完成的零延迟 causal online tracker。</p>
  </section>

  <section id="tracks">
    <h2>三、现有 optical track identity 到底能提供什么</h2>
    {make_table(['run','raw fragment tracks','stitched accepted tracks','stitched ambiguous 合计','含 posthoc 插值的 stitched tracks'], provenance_table_rows)}
    <p class="lead">R01/R04 的碎片化相对可控；R02 是主要断点。raw 与 stitched 在当前短时间窗内的 reference coverage/retention 几乎相同，说明离线 stitching 尚未产生明确的壳几何增益。它的价值目前是诊断连续性上限，不是已经建立了可靠 runtime identity。</p>
    {image_block(summary_figures[0], 'Track provenance 与断点', '所有 raw fragments 都进入主接口；accepted tier 没有被用来过滤主接口。')}
  </section>

  <section id="time">
    <h2>四、时间不确定度：保留率与搜索负担同时增长</h2>
    {make_table(['半窗/ms','track prior 可用','reference 候选保留','单 track burden 中位','union burden 中位','分支 burden 求和','分支重复比例'], time_rows)}
    <p class="callout warning"><strong>不能把 500 ms 读成“最好”。</strong>0→500 ms 时 reference 候选保留由 76.9% 增到 93.2%，但单 track burden 由 14.5% 增到 25.8%，union burden 由 28.2% 增到 41.0%，分支重复也从 0 增到约 40.9%。同步精度的价值正体现在这条曲线上：更窄的可信时间窗可以减少壳宽与分支负担，而不是让 SAR 让渡最终定位权。</p>
    {image_block(summary_figures[1], '时间窗保留率—候选负担', '窗口是运行结果前固定的 0/100/250/500 ms；没有看完结果再挑一个最漂亮的值。')}
  </section>

  <section id="r02">
    <h2>五、R02：track-conditioned 搜索更小，但 identity / shared 未解决</h2>
    {make_table(['PERSON','reference 帧数','global→union→offline best-track rank 中位','有 rank 的帧','任一 track 保留'], r02_table_rows)}
    <div class="grid-2">
      <div class="card"><h3>P01 / P02</h3><p>P01 的 11→3→2、P02 的 18→6→4 表明：相对 all-person union shell，每条 track 独立出壳还能进一步降低部分全扇面竞争。但 P02 仍只有 7/9 帧有 0.8 m 离散峰；这不是唯一定位已经成立。</p></div>
      <div class="card"><h3>P03 / P04</h3><p>二者仍为 1→1→1，但当前壳本身没有稳定分离。offline-associated 两壳的角度 Jaccard 在多个窗口仍约 0.5–0.6，且窗口/fragment 可用帧数不同。因而当前还不能形成“光学壳已清楚分开、SAR 却只有同一 response”的强证据。</p></div>
    </div>
    {make_table(['离线配对','半窗/ms','可配对帧','Jaccard 中位','IQR'], jaccard_table_rows)}
    <div class="figure-grid">
      {image_block(summary_figures[3], 'R02 global→union→track rank', 'offline best-track 只用于评价 track-conditioned 上限；运行时没有用 reference 选择这条 track。')}
      {image_block(summary_figures[4], 'R02 track 壳重叠', '每个窗口的 n 不同，不能把曲线解释成纯时间窗因果。')}
    </div>
  </section>

  <section id="regions">
    <h2>六、从“峰”到“响应区域”，究竟修正了什么</h2>
    {make_table(['离线位置实体','行数','直接落入 q95 region','0.30 m 内有 q95 region'], coverage_table_rows)}
    <div class="grid-2">
      <div class="card"><h3>修正 candidate missing 语义</h3><p>251 条 PERSON reference 中，249 条本来就有 0.8 m 离散峰；F482/F490 两条没有峰但都有 q95 region。另有 R02 F494 P01、R04 F35 P01 只在 q90 有 region；q90 内完全无 region 的 reference 为 0。</p></div>
      <div class="card"><h3>没有修正局部竞争与 shared</h3><p>q95 direct coverage：PERSON {pct(person_entity['direct_inside'])}，固定偏移 {pct(fixed_entity['direct_inside'])}，几何匹配对照 {pct(geometry_entity['direct_inside'])}，局部竞争响应 {pct(local_entity['direct_inside'])}。对远离 reference 的对照有明显位置优势，但 local competing 仍高，不能授予唯一性。</p></div>
    </div>
    {make_table(['frame','PERSON','C2 percentile','最近峰 rank','峰距/m','q95 area/m²','major/m','结构','shared'], missing_table_rows)}
    <h3>q90-only 弱状态</h3>
    {make_table(['frame','PERSON','C2 percentile','最近峰 rank','峰距/m'], q90_table_rows)}
    {image_block(summary_figures[2], 'q95 reference 与空间对照', '所有位置实体都在 region 完整生成后才离线评价；这不是盲验证。')}
    <p class="callout"><strong>最稳妥的新接口描述：</strong>response-region 能区分 <code>PEAK_PRESENT</code>、<code>PEAK_MISSING_REGION_PRESENT</code>、q90-only 弱状态、extended/ridge、shared 与 censored/unobservable；这些仍是 reference-conditioned 离线解释标签，不是已经完成的 GT-blind runtime 状态分类器。</p>
  </section>

  <section id="cases">
    <h2>七、七个直接病例：先看真实图像，再看汇总</h2>
    <p class="lead">每个病例同时提供局部放大和全扇面六联图。局部图聚焦用户指定的 PERSON 组；全扇面图用于确认模型没有只截取有利局部、没有忽略扇面边界，也没有把 reference 用于生成 region、peak 或 shell。</p>
    {case_html}
  </section>

  <section id="answers">
    <h2>八、这轮最重要的六个直接回答</h2>
    <div class="grid-2">
      <article class="card answer" id="q1"><div class="q">Q1 · 现有光学链是否已有可靠 runtime track identity？</div><h3>还没有</h3><p>自动 raw fragments 可以作为主运行时近似输入，但 R02 碎片化严重；stitched accepted 是全 run Hungarian stitching 与短缺口插值的 GT-blind offline proxy，不能替代严格 causal runtime identity。</p></article>
      <article class="card answer" id="q2"><div class="q">Q2 · 每条 track 独立出壳是否比 all-person union 更有用？</div><h3>对 P01/P02 有额外搜索压缩</h3><p>P01 11→3→2，P02 18→6→4；说明 track-conditioned 壳能把全场竞争进一步缩小。但它依赖 tracklet 可用性和重叠，不保证唯一定位。</p></article>
      <article class="card answer" id="q3"><div class="q">Q3 · P03/P04 的 optical shells 是否已经分离？</div><h3>没有稳定分离</h3><p>当前 guard、时间不确定度、fragment availability 使两壳仍明显重叠；因此 shared SAR region 与 optical identity 的关系还不能被强判定。</p></article>
      <article class="card answer" id="q4"><div class="q">Q4 · response-region 是否比 peak node 更忠实？</div><h3>是，尤其对 response-present / peak-missing</h3><p>F482/F490 被一致修正为 q95 region present；q95 reference direct coverage 98.0%，固定/几何空间对照显著更低。它更忠实地表达连续 C2 field，但不是 PERSON 框。</p></article>
      <article class="card answer" id="q5"><div class="q">Q5 · 它是否解决 shared / 空间未分离？</div><h3>没有，而且明确保留了 shared 状态</h3><p>总体 q95 shared 37.5%，R02 94.4%；P03/P04 仍可落在同一 compact region。shared region 只表示图像域重叠，不能直接声称物理散射融合。</p></article>
      <article class="card answer" id="q6"><div class="q">Q6 · 接口清楚后，下一步是什么？</div><h3>先补 runtime track/sync，再做最小 region-shell 时序相交</h3><p>最有价值的是把 centered diagnostic 变成可量化的 causal/buffered track uncertainty，并验证 track 分支连续性；之后才研究 <code>optical track shell ∩ SAR response region + 冻结 P0 region propagation</code>。本轮没有实现 region tracker，也没有进入 P2。</p></article>
    </div>
  </section>

  <section id="audit">
    <h2>九、可复核边界与数据覆盖</h2>
    <div class="grid-2">
      <div class="card"><h3>候选 artifact 覆盖</h3><p>旧 GT-blind candidate artifact 只覆盖 126/398 帧；这 126 帧的数量、rank、坐标、score、support 全部精确复现，最大浮点差约 1.11e−16。其余 272 帧标记为 <code>NO_LEGACY_CANDIDATE_ARTIFACT_FOR_FRAME</code>，绝不解释为“零候选”。连续 response-region 则覆盖 398/398 帧。</p></div>
      <div class="card"><h3>明确没有做</h3><ul><li>没有重拟合或调参冻结 P0；</li><li>没有修改 B0R、C0–C3 或旧结果；</li><li>没有用人工 physical_target_id 生成 runtime track；</li><li>没有让光学指定 SAR range、中心或框；</li><li>没有把 response region 当最终 PERSON 框；</li><li>没有把 RGB/JET 当独立雷达物理通道或人体固有 RCS；</li><li>没有授予 P1/P2 PASS，不声称盲验证。</li></ul></div>
    </div>
    <p class="callout warning"><strong>停止点：</strong>本报告只是已暴露 R01–R04 开发语料上的最小接口诊断。状态仍为 <code>COMPLETE_NO_NEW_PASS_FAIL_NO_P2_CLAIM</code>；SAR 保留 range 与最终定位权，不生成 SAR 框，不自动进入复杂多模态 tracker。</p>
    <div class="file-links">{output_links}</div>
    <p class="foot">分析脚本 SHA256：<code>{esc(summary['analysis_script_sha256'])}</code><br>报告生成器 SHA256：<code>{esc(sha256_file(SCRIPT_PATH))}</code><br>报告生成时间：{esc(now_iso())}</p>
  </section>

  <section><h2>附：五张汇总图</h2><div class="figure-grid">{summary_figure_html}</div></section>
</main>
</body>
</html>"""

    context = {
        "summary": summary,
        "derived": derived,
        "time_data": time_data,
        "provenance": provenance,
        "track_summary": track_summary,
        "assignments": assignments,
        "reference_region": reference_region,
        "entity_region": entity_region,
        "overlap": overlap,
        "candidate_parity": candidate_parity,
        "cases": cases,
        "summary_figures": summary_figures,
        "local_cases": local_cases,
    }
    return html_text, context


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(OUTPUT_DIR).lower():
        raise RuntimeError("forbidden old_work output")
    html_text, _ = build_report()
    REPORT_PATH.write_text(html_text, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "REPORT_RENDERED",
                "report_path": str(REPORT_PATH),
                "report_sha256": sha256_file(REPORT_PATH),
                "derived_path": str(DERIVED_PATH),
                "report_script_sha256": sha256_file(SCRIPT_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
