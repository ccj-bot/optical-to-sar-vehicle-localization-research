#!/usr/bin/env python
"""Evaluate GM17 Phase4C combined structure+temporal fixed pilot after output exists."""

from __future__ import annotations

import argparse
import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

import gm17_phase4_sar_structure_evidence_scout as scout


DEFAULT_A019 = "output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv"
DEFAULT_A021 = "output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv"
DEFAULT_V1_DIR = "output/gm17_phase4_minimal_factor_pilot_20260628_110447"
DEFAULT_V2_DIR = "output/gm17_phase4_minimal_factor_pilot_v2_20260628_171204"
DEFAULT_STRUCTURE_DIR = "output/gm17_phase4_structure_only_fixed_pilot_20260628_221140"
DEFAULT_LOG_ROOT = "logs"

GROUP_KEYS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
TARGET_KEYS = ["target_identity", "scene", "sar_frame_num"]
VARIANTS = {
    "c1": "equal_temporal_s1",
    "c2": "equal_temporal_s2",
    "c3": "temporal_guard_structure_promote",
    "c4": "structure_guard_temporal_soft_diagnostic",
    "c5": "temporal_only_recomputed_baseline",
}
ROLE_COLORS = {
    "combined_rank1": "#d62728",
    "v1_rank1": "#9467bd",
    "structure_s1_rank1": "#ff7f0e",
    "best_proxy": "#2ca02c",
    "best_center": "#1f77b4",
}
REPAIR_NOTES: list[str] = []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate GM17 Phase4C combined fixed pilot.")
    parser.add_argument("--pilot-dir", required=True)
    parser.add_argument("--a019", default=DEFAULT_A019)
    parser.add_argument("--a021", default=DEFAULT_A021)
    parser.add_argument("--v1-dir", default=DEFAULT_V1_DIR)
    parser.add_argument("--v2-dir", default=DEFAULT_V2_DIR)
    parser.add_argument("--structure-dir", default=DEFAULT_STRUCTURE_DIR)
    parser.add_argument("--log-root", default=DEFAULT_LOG_ROOT)
    parser.add_argument("--max-panels", type=int, default=60)
    return parser.parse_args()


def setup_logging(log_path: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )


def norm_str(value: Any) -> str:
    return scout.norm_str(value)


def safe_float(value: Any) -> float:
    return scout.safe_float(value)


def safe_int_text(value: Any) -> str:
    return scout.safe_int_text(value)


def key_cols_as_text(df: pd.DataFrame, keys: list[str] = GROUP_KEYS) -> pd.DataFrame:
    out = df.copy()
    for col in keys:
        if col in out.columns:
            if col == "sar_frame_num":
                out[col] = out[col].map(safe_int_text)
            else:
                out[col] = out[col].map(norm_str)
    return out


def read_required(path: Path, **kwargs: Any) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    logging.info("Reading %s", path)
    return pd.read_csv(path, **kwargs)


def axis_iou(df: pd.DataFrame) -> pd.Series:
    cand_x1 = df["cx"] - df["w"] / 2.0
    cand_y1 = df["cy"] - df["h"] / 2.0
    cand_x2 = df["cx"] + df["w"] / 2.0
    cand_y2 = df["cy"] + df["h"] / 2.0
    gt_x1 = df["final_ax_x1"]
    gt_y1 = df["final_ax_y1"]
    gt_x2 = df["final_ax_x2"]
    gt_y2 = df["final_ax_y2"]
    ix1 = np.maximum(cand_x1, gt_x1)
    iy1 = np.maximum(cand_y1, gt_y1)
    ix2 = np.minimum(cand_x2, gt_x2)
    iy2 = np.minimum(cand_y2, gt_y2)
    inter = np.maximum(0.0, ix2 - ix1) * np.maximum(0.0, iy2 - iy1)
    cand_area = np.maximum(0.0, cand_x2 - cand_x1) * np.maximum(0.0, cand_y2 - cand_y1)
    gt_area = np.maximum(0.0, gt_x2 - gt_x1) * np.maximum(0.0, gt_y2 - gt_y1)
    return inter / np.maximum(cand_area + gt_area - inter, 1e-6)


def add_eval_geometry(ranked: pd.DataFrame, a019: pd.DataFrame) -> pd.DataFrame:
    gt_cols = [
        "target_identity",
        "scene",
        "sar_frame_num",
        "final_cx",
        "final_cy",
        "final_ax_x1",
        "final_ax_y1",
        "final_ax_x2",
        "final_ax_y2",
    ]
    gt = key_cols_as_text(a019[gt_cols], TARGET_KEYS)
    gt = gt[gt["scene"].eq("GM_RM017")].drop_duplicates(TARGET_KEYS)
    out = key_cols_as_text(ranked).merge(gt, on=TARGET_KEYS, how="left", validate="many_to_one")
    for col in ["cx", "cy", "w", "h", "final_cx", "final_cy", "final_ax_x1", "final_ax_y1", "final_ax_x2", "final_ax_y2"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["center_error"] = np.sqrt((out["cx"] - out["final_cx"]) ** 2 + (out["cy"] - out["final_cy"]) ** 2)
    out["axis_aligned_proxy_iou"] = axis_iou(out)
    return out


def best_candidates(evaluated: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in evaluated.groupby(GROUP_KEYS, dropna=False, sort=False):
        proxy = group.sort_values(["axis_aligned_proxy_iou", "candidate_id"], ascending=[False, True]).iloc[0]
        center = group.sort_values(["center_error", "candidate_id"], ascending=[True, True]).iloc[0]
        rows.append(
            {
                **dict(zip(GROUP_KEYS, key)),
                "best_proxy_candidate_id": proxy["candidate_id"],
                "best_proxy_iou": safe_float(proxy["axis_aligned_proxy_iou"]),
                "best_proxy_center_error": safe_float(proxy["center_error"]),
                "best_center_candidate_id": center["candidate_id"],
                "best_center_error": safe_float(center["center_error"]),
                "best_center_proxy_iou": safe_float(center["axis_aligned_proxy_iou"]),
            }
        )
    return pd.DataFrame(rows)


def condition_context(a021: pd.DataFrame) -> pd.DataFrame:
    cols = ["target_identity", "scene", "sar_frame_num", "condition_type", "condition_status", "truncation_degree", "occlusion_degree"]
    out = key_cols_as_text(a021[cols], TARGET_KEYS)
    out = out[out["scene"].eq("GM_RM017")]
    return out.drop_duplicates(TARGET_KEYS)


def filter_group(df: pd.DataFrame, key: tuple[Any, ...]) -> pd.DataFrame:
    out = df
    for col, value in zip(GROUP_KEYS, key):
        out = out[out[col].astype(str).eq(str(value))]
    return out


def evaluate_variant(evaluated: pd.DataFrame, best: pd.DataFrame, conditions: pd.DataFrame, variant: str) -> pd.DataFrame:
    rank_col = f"{variant}_rank"
    score_col = f"{variant}_score"
    rows: list[dict[str, Any]] = []
    for key, group in evaluated.groupby(GROUP_KEYS, dropna=False, sort=False):
        group = group.sort_values([rank_col, "candidate_id"], ascending=[True, True])
        rank1 = group.iloc[0]
        top3 = group.head(3)
        top5 = group.head(5)
        best_row = filter_group(best, key)
        if best_row.empty:
            continue
        b = best_row.iloc[0]
        best_proxy_id = b["best_proxy_candidate_id"]
        best_center_id = b["best_center_candidate_id"]
        proxy_match = group[group["candidate_id"].astype(str).eq(str(best_proxy_id))]
        center_match = group[group["candidate_id"].astype(str).eq(str(best_center_id))]
        best_proxy_rank = safe_float(proxy_match.iloc[0][rank_col]) if not proxy_match.empty else math.nan
        best_center_rank = safe_float(center_match.iloc[0][rank_col]) if not center_match.empty else math.nan
        zero_distance = safe_float(rank1.get("temporal_distance_raw"))
        rows.append(
            {
                **dict(zip(GROUP_KEYS, key)),
                "variant": variant,
                "variant_name": VARIANTS[variant],
                "candidate_id": rank1["candidate_id"],
                "cx": rank1["cx"],
                "cy": rank1["cy"],
                "w": rank1["w"],
                "h": rank1["h"],
                "heading": rank1["heading"],
                "r": rank1["r"],
                "az": rank1["az"],
                "cross": rank1["cross"],
                "combined_score": rank1[score_col],
                "combined_rank": rank1[rank_col],
                "center_error": safe_float(rank1["center_error"]),
                "axis_aligned_proxy_iou": safe_float(rank1["axis_aligned_proxy_iou"]),
                "proxy_hit_iou_0_25": bool(safe_float(rank1["axis_aligned_proxy_iou"]) >= 0.25),
                "center_hit_50px": bool(safe_float(rank1["center_error"]) <= 50.0),
                "proxy_hit_top3_iou_0_25": bool((top3["axis_aligned_proxy_iou"] >= 0.25).any()),
                "proxy_hit_top5_iou_0_25": bool((top5["axis_aligned_proxy_iou"] >= 0.25).any()),
                "center_hit_top3_50px": bool((top3["center_error"] <= 50.0).any()),
                "center_hit_top5_50px": bool((top5["center_error"] <= 50.0).any()),
                "best_proxy_candidate_id": best_proxy_id,
                "best_proxy_rank": best_proxy_rank,
                "best_proxy_iou": safe_float(b["best_proxy_iou"]),
                "best_proxy_center_error": safe_float(b["best_proxy_center_error"]),
                "best_center_candidate_id": best_center_id,
                "best_center_rank": best_center_rank,
                "best_center_error": safe_float(b["best_center_error"]),
                "best_center_proxy_iou": safe_float(b["best_center_proxy_iou"]),
                "rank1_is_best_proxy": str(rank1["candidate_id"]) == str(best_proxy_id),
                "rank1_is_best_center": str(rank1["candidate_id"]) == str(best_center_id),
                "best_proxy_in_top5": bool(best_proxy_rank <= 5) if math.isfinite(best_proxy_rank) else False,
                "best_proxy_in_top20": bool(best_proxy_rank <= 20) if math.isfinite(best_proxy_rank) else False,
                "best_center_in_top5": bool(best_center_rank <= 5) if math.isfinite(best_center_rank) else False,
                "rank1_temporal_zero": bool(math.isfinite(zero_distance) and abs(zero_distance) <= 1e-9),
                "temporal_zero_dependency": "recomputed_from_A005_pred_only_no_legacy_delta_score",
                "rank1_temporal_rank_percentile": safe_float(rank1.get("temporal_rank_percentile")),
                "rank1_s1_rank_percentile": safe_float(rank1.get("s1_rank_percentile")),
                "rank1_s2_rank_percentile": safe_float(rank1.get("s2_rank_percentile")),
                "rank1_temporal_join_status": rank1.get("temporal_join_status", ""),
                "rank1_structure_feature_status": rank1.get("structure_feature_status", ""),
                "rank1_feature_source_image_type": rank1.get("feature_source_image_type", ""),
            }
        )
    out = pd.DataFrame(rows)
    if not conditions.empty:
        out = out.merge(conditions, on=TARGET_KEYS, how="left")
    return out


def summarize(per_target: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variant, group in per_target.groupby("variant", sort=False):
        rows.append(
            {
                "variant": variant,
                "variant_name": group["variant_name"].iloc[0],
                "mean_center_error": float(group["center_error"].mean()),
                "median_center_error": float(group["center_error"].median()),
                "mean_axis_aligned_proxy_iou": float(group["axis_aligned_proxy_iou"].mean()),
                "median_axis_aligned_proxy_iou": float(group["axis_aligned_proxy_iou"].median()),
                "proxy_iou_recall_at_1_threshold_0_25": float(group["proxy_hit_iou_0_25"].mean()),
                "proxy_iou_recall_at_3_threshold_0_25": float(group["proxy_hit_top3_iou_0_25"].mean()),
                "proxy_iou_recall_at_5_threshold_0_25": float(group["proxy_hit_top5_iou_0_25"].mean()),
                "center_recall_at_1_threshold_50px": float(group["center_hit_50px"].mean()),
                "center_recall_at_3_threshold_50px": float(group["center_hit_top3_50px"].mean()),
                "center_recall_at_5_threshold_50px": float(group["center_hit_top5_50px"].mean()),
                "rank1_is_best_proxy_rate": float(group["rank1_is_best_proxy"].mean()),
                "rank1_is_best_center_rate": float(group["rank1_is_best_center"].mean()),
                "best_proxy_top5_rate": float(group["best_proxy_in_top5"].mean()),
                "best_proxy_top20_rate": float(group["best_proxy_in_top20"].mean()),
                "mean_rank_of_best_proxy": float(group["best_proxy_rank"].mean()),
                "median_rank_of_best_proxy": float(group["best_proxy_rank"].median()),
                "best_proxy_iou_coverage_threshold_0_25": float((group["best_proxy_iou"] >= 0.25).mean()),
                "best_center_coverage_threshold_50px": float((group["best_center_error"] <= 50.0).mean()),
                "rank1_temporal_zero_rate": float(group["rank1_temporal_zero"].mean()),
                "temporal_zero_dependency": "recomputed_from_A005_pred_only_no_legacy_delta_score",
                "n_targets": int(len(group)),
            }
        )
    return pd.DataFrame(rows)


def condition_summary(per_target: pd.DataFrame) -> pd.DataFrame:
    cols = ["variant", "variant_name", "condition_type", "truncation_degree", "occlusion_degree"]
    return (
        per_target.groupby(cols, dropna=False)
        .agg(
            n_targets=("candidate_id", "count"),
            mean_center_error=("center_error", "mean"),
            median_center_error=("center_error", "median"),
            mean_axis_aligned_proxy_iou=("axis_aligned_proxy_iou", "mean"),
            rank1_is_best_proxy_rate=("rank1_is_best_proxy", "mean"),
            rank1_is_best_center_rate=("rank1_is_best_center", "mean"),
            best_proxy_top5_rate=("best_proxy_in_top5", "mean"),
            best_proxy_top20_rate=("best_proxy_in_top20", "mean"),
            mean_rank_of_best_proxy=("best_proxy_rank", "mean"),
            rank1_temporal_zero_rate=("rank1_temporal_zero", "mean"),
        )
        .reset_index()
    )


def comparison_table(combined_summary: pd.DataFrame, structure_dir: Path) -> pd.DataFrame:
    structure_compare_path = structure_dir / "evaluation_structure_vs_v1_v2_comparison.csv"
    if structure_compare_path.exists():
        base = pd.read_csv(structure_compare_path)
    else:
        base = pd.DataFrame()
    combined = combined_summary.copy()
    if "rank1_temporal_zero_dependency" not in combined.columns:
        combined["rank1_temporal_zero_dependency"] = combined["temporal_zero_dependency"]
    if not base.empty and "rank1_temporal_zero_dependency" not in base.columns:
        base["rank1_temporal_zero_dependency"] = ""
    all_cols = list(dict.fromkeys(list(base.columns) + list(combined.columns)))
    if base.empty:
        return combined.reindex(columns=all_cols)
    return pd.concat([base.reindex(columns=all_cols), combined.reindex(columns=all_cols)], ignore_index=True)


def md_table(df: pd.DataFrame, max_rows: int = 20, digits: int = 4) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{x:.{digits}f}")
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in view.columns) + " |")
    if len(df) > max_rows:
        lines.append(f"\n_Showing {max_rows} of {len(df)} rows._")
    return "\n".join(lines)


def bar_plot(df: pd.DataFrame, x_col: str, y_cols: list[str], out_path: Path, title: str, ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 5), dpi=140)
    x = np.arange(len(df))
    width = 0.8 / max(1, len(y_cols))
    for i, col in enumerate(y_cols):
        ax.bar(x + (i - (len(y_cols) - 1) / 2) * width, df[col], width=width, label=col)
    ax.set_xticks(x)
    ax.set_xticklabels(df[x_col], rotation=30, ha="right")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def make_figures(pilot_dir: Path, comparison: pd.DataFrame, combined_summary: pd.DataFrame, cond: pd.DataFrame, per_target: pd.DataFrame) -> list[str]:
    figures_dir = pilot_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    plot = comparison.copy()
    plot["variant_label"] = plot["variant"].astype(str)
    for name, cols, title, ylabel in [
        ("combined_vs_all_rank1_best_proxy_rate_bar.png", ["rank1_is_best_proxy_rate"], "Rank1 best-proxy rate", "rate"),
        ("combined_vs_all_best_proxy_top20_bar.png", ["best_proxy_top20_rate"], "Best-proxy top20 rate", "rate"),
        ("combined_vs_all_mean_center_error_bar.png", ["mean_center_error"], "Mean center error", "pixels"),
        (
            "combined_proxy_recall_at_k_bar.png",
            ["proxy_iou_recall_at_1_threshold_0_25", "proxy_iou_recall_at_3_threshold_0_25", "proxy_iou_recall_at_5_threshold_0_25"],
            "Proxy IoU recall at k",
            "recall",
        ),
    ]:
        path = figures_dir / name
        bar_plot(plot, "variant_label", cols, path, title, ylabel)
        paths.append(str(path))

    c = cond[cond["n_targets"] >= 3].copy()
    c["condition_label"] = c["condition_type"].astype(str) + "/" + c["truncation_degree"].astype(str) + "/" + c["occlusion_degree"].astype(str)
    pivot = c.pivot_table(index="condition_label", columns="variant", values="rank1_is_best_proxy_rate", aggfunc="mean").fillna(0)
    fig, ax = plt.subplots(figsize=(12, max(4, 0.4 * max(1, len(pivot)))), dpi=140)
    if not pivot.empty:
        failure = 1.0 - pivot
        y = np.arange(len(failure))
        width = 0.16
        for i, col in enumerate(failure.columns):
            ax.barh(y + (i - (len(failure.columns) - 1) / 2) * width, failure[col], height=width, label=col)
        ax.set_yticks(y)
        ax.set_yticklabels(failure.index, fontsize=7)
        ax.set_xlabel("1 - rank1_is_best_proxy_rate")
        ax.legend(fontsize=8)
    else:
        ax.text(0.5, 0.5, "No condition groups with n>=3", ha="center", va="center")
        ax.set_axis_off()
    ax.set_title("Combined condition group failure rate")
    fig.tight_layout()
    path = figures_dir / "combined_condition_failure_bar.png"
    fig.savefig(path)
    plt.close(fig)
    paths.append(str(path))

    fig, ax = plt.subplots(figsize=(8, 6), dpi=140)
    subset = per_target[per_target["variant"].isin(["c1", "c2", "c3", "c4"])]
    if not subset.empty:
        colors = {"c1": "#1f77b4", "c2": "#2ca02c", "c3": "#ff7f0e", "c4": "#d62728"}
        for variant, group in subset.groupby("variant"):
            ax.scatter(group["rank1_temporal_rank_percentile"], group["rank1_s1_rank_percentile"], s=16, alpha=0.65, label=variant, color=colors.get(variant))
        ax.set_xlabel("rank1 temporal percentile")
        ax.set_ylabel("rank1 S1 structure percentile")
        ax.legend()
    else:
        ax.text(0.5, 0.5, "No combined component rows", ha="center", va="center")
        ax.set_axis_off()
    ax.set_title("Combined component tradeoff")
    fig.tight_layout()
    path = figures_dir / "combined_component_tradeoff_scatter.png"
    fig.savefig(path)
    plt.close(fig)
    paths.append(str(path))
    return paths


def compact_id(value: Any) -> str:
    text = norm_str(value)
    return text if len(text) <= 18 else text[:9] + "..." + text[-6:]


def draw_box(ax: plt.Axes, row: pd.Series, role: str, color: str) -> None:
    cx, cy, w, h = (safe_float(row.get(col)) for col in ["cx", "cy", "w", "h"])
    if not all(math.isfinite(v) for v in [cx, cy, w, h]) or w <= 0 or h <= 0:
        return
    rect = Rectangle((cx - w / 2, cy - h / 2), w, h, fill=False, edgecolor=color, linewidth=1.8)
    ax.add_patch(rect)
    ax.text(
        cx - w / 2,
        cy - h / 2,
        f"{role}\n{compact_id(row.get('candidate_id'))}",
        color=color,
        fontsize=7,
        bbox={"facecolor": "black", "alpha": 0.45, "pad": 1, "edgecolor": "none"},
    )


def make_panel(image_path: str, out_path: Path, title: str, rows: list[tuple[str, pd.Series | None]]) -> bool:
    image, status = scout.load_image(image_path)
    if image is None:
        return False
    fig = plt.figure(figsize=(16, 9), dpi=140)
    grid = fig.add_gridspec(2, 4, width_ratios=[2.2, 1, 1, 1], height_ratios=[1, 1])
    ax_main = fig.add_subplot(grid[:, 0])
    ax_main.imshow(image, cmap="gray", vmin=0, vmax=1)
    ax_main.set_title("overview")
    ax_main.set_axis_off()
    for role, row in rows:
        if row is not None:
            draw_box(ax_main, row, role, ROLE_COLORS[role])
    for i, (role, row) in enumerate(rows[:6]):
        ax = fig.add_subplot(grid[i // 3, i % 3 + 1])
        if row is None:
            ax.set_axis_off()
            continue
        cx, cy, w, h = (safe_float(row.get(col)) for col in ["cx", "cy", "w", "h"])
        if not all(math.isfinite(v) for v in [cx, cy, w, h]) or w <= 0 or h <= 0:
            ax.set_axis_off()
            continue
        x1, y1, x2, y2 = scout.clipped_bounds(cx, cy, w, h, image.shape, scale=2.3)
        patch = image[y1:y2, x1:x2]
        ax.imshow(patch, cmap="gray", vmin=0, vmax=1)
        local = row.copy()
        local["cx"] = cx - x1
        local["cy"] = cy - y1
        draw_box(ax, local, role, ROLE_COLORS[role])
        ax.set_title(
            f"{role} {compact_id(row.get('candidate_id'))}\n"
            f"IoU={safe_float(row.get('axis_aligned_proxy_iou')):.3f} err={safe_float(row.get('center_error')):.1f}",
            fontsize=7,
        )
        ax.set_axis_off()
    fig.suptitle(title, fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95], h_pad=1.8, w_pad=1.5)
    fig.savefig(out_path)
    plt.close(fig)
    return True


def make_panels(
    pilot_dir: Path,
    per_target: pd.DataFrame,
    evaluated: pd.DataFrame,
    v1_eval: pd.DataFrame,
    structure_ranked: pd.DataFrame,
    path_report: pd.DataFrame,
    max_panels: int,
) -> pd.DataFrame:
    panels_dir = pilot_dir / "panels"
    panels_dir.mkdir(parents=True, exist_ok=True)
    cases = []
    for variant in ["c1", "c2", "c3"]:
        group = per_target[per_target["variant"].eq(variant)]
        success = group[group["rank1_is_best_proxy"]].sort_values("axis_aligned_proxy_iou", ascending=False).head(6)
        failure = group[~group["rank1_is_best_proxy"]].sort_values(["best_proxy_iou", "center_error"], ascending=[False, False]).head(9)
        for case_type, frame in [("success", success), ("failure", failure)]:
            for _, row in frame.iterrows():
                item = row.to_dict()
                item["panel_case_type"] = case_type
                cases.append(item)
    queue = pd.DataFrame(cases).drop_duplicates(["variant", *GROUP_KEYS]).head(max_panels)
    path_by_key = {
        tuple(norm_str(row.get(col, "")) if col != "sar_frame_num" else safe_int_text(row.get(col, "")) for col in GROUP_KEYS): row
        for row in path_report.to_dict("records")
    }
    v1_eval = key_cols_as_text(v1_eval)
    structure_ranked = key_cols_as_text(structure_ranked)
    panel_rows: list[dict[str, Any]] = []
    for idx, row in queue.reset_index(drop=True).iterrows():
        key = tuple(norm_str(row.get(col, "")) if col != "sar_frame_num" else safe_int_text(row.get(col, "")) for col in GROUP_KEYS)
        group_eval = filter_group(evaluated, key)
        if group_eval.empty:
            continue
        combined_row = group_eval[group_eval["candidate_id"].astype(str).eq(str(row["candidate_id"]))].iloc[0]
        best_proxy = group_eval[group_eval["candidate_id"].astype(str).eq(str(row["best_proxy_candidate_id"]))].iloc[0]
        best_center = group_eval[group_eval["candidate_id"].astype(str).eq(str(row["best_center_candidate_id"]))].iloc[0]
        v1_matches = filter_group(v1_eval, key)
        v1_row = None
        if not v1_matches.empty:
            v1_id = norm_str(v1_matches.iloc[0].get("candidate_id"))
            match = group_eval[group_eval["candidate_id"].astype(str).eq(v1_id)]
            if not match.empty:
                v1_row = match.iloc[0]
        structure_matches = filter_group(structure_ranked, key)
        s1_row = None
        if not structure_matches.empty:
            s1_id = norm_str(structure_matches.sort_values(["s1_rank", "candidate_id"]).iloc[0].get("candidate_id"))
            match = group_eval[group_eval["candidate_id"].astype(str).eq(s1_id)]
            if not match.empty:
                s1_row = match.iloc[0]
        image_path = norm_str(path_by_key.get(key, {}).get("resolved_path", ""))
        out_path = panels_dir / f"{row['variant']}_{idx+1:03d}_{row['panel_case_type']}_combined_panel.png"
        title = f"diagnostic review only, combined pre-registered output, no tuning | {row['variant']} {row['panel_case_type']}"
        generated = make_panel(
            image_path,
            out_path,
            title,
            [
                ("combined_rank1", combined_row),
                ("v1_rank1", v1_row),
                ("structure_s1_rank1", s1_row),
                ("best_proxy", best_proxy),
                ("best_center", best_center),
            ],
        )
        panel_rows.append(
            {
                "variant": row["variant"],
                "target_identity": row["target_identity"],
                "scene": row["scene"],
                "sar_frame_num": row["sar_frame_num"],
                "gm17_track_id": row["gm17_track_id"],
                "panel_case_type": row["panel_case_type"],
                "panel_path": str(out_path) if generated else "",
                "panel_generated": generated,
            }
        )
    panel_queue = pd.DataFrame(panel_rows)
    panel_queue.to_csv(pilot_dir / "evaluation_combined_panel_queue.csv", index=False, encoding="utf-8-sig")
    return panel_queue


def support_decision(summary: pd.DataFrame, comparison: pd.DataFrame) -> tuple[bool, str, str]:
    c_main = summary[summary["variant"].isin(["c1", "c2", "c3"])]
    v1 = comparison[comparison["variant"].astype(str).eq("v1")].iloc[0]
    s1 = comparison[comparison["variant"].astype(str).eq("s1")]
    s1_center = safe_float(s1.iloc[0]["mean_center_error"]) if not s1.empty else math.nan
    best_balanced = c_main.copy()
    best_balanced["balance_score"] = (
        best_balanced["rank1_is_best_proxy_rate"].rank(ascending=False)
        + best_balanced["best_proxy_top20_rate"].rank(ascending=False)
        + best_balanced["mean_center_error"].rank(ascending=True)
    )
    best = best_balanced.sort_values(["balance_score", "variant"]).iloc[0]
    improves_rank1 = bool((c_main["rank1_is_best_proxy_rate"] > safe_float(v1["rank1_is_best_proxy_rate"])).any())
    improves_top20 = bool((c_main["best_proxy_top20_rate"] > safe_float(v1["best_proxy_top20_rate"])).any())
    reduces_structure_center = bool(math.isfinite(s1_center) and (c_main["mean_center_error"] < s1_center).any())
    support = improves_rank1 and improves_top20 and reduces_structure_center
    reason = (
        f"{best['variant']} is the most balanced by rank1 best-proxy, top20, and center-error ranks. "
        f"rank1 improvement={improves_rank1}, top20 improvement={improves_top20}, "
        f"structure-only center-error reduction={reduces_structure_center}."
    )
    return support, norm_str(best["variant"]), reason


def write_readme(pilot_dir: Path, summary: pd.DataFrame) -> None:
    text = "# Combined Structure+Temporal Fixed Pilot Evaluation\n\n"
    text += "A019/A021 were read only after combined ranked output existed. No evaluation result fed back into ranking.\n\n"
    text += md_table(summary[["variant", "mean_center_error", "mean_axis_aligned_proxy_iou", "rank1_is_best_proxy_rate", "best_proxy_top20_rate"]])
    (pilot_dir / "evaluation_combined_readme.md").write_text(text, encoding="utf-8")


def write_json(
    pilot_dir: Path,
    timestamp: str,
    summary: pd.DataFrame,
    comparison: pd.DataFrame,
    per_target: pd.DataFrame,
    cond: pd.DataFrame,
    panel_queue: pd.DataFrame,
    support: bool,
    best_variant: str,
    reason: str,
    figure_paths: list[str],
    summary_md: Path,
) -> None:
    payload = {
        "evaluation_timestamp": timestamp,
        "pilot_dir": str(pilot_dir),
        "target_count": int(per_target[GROUP_KEYS].drop_duplicates().shape[0]),
        "variants": summary.to_dict("records"),
        "comparison_rows": comparison.to_dict("records"),
        "condition_group_rows": cond.to_dict("records"),
        "panel_generated_count": int(panel_queue["panel_generated"].sum()) if not panel_queue.empty else 0,
        "support_factor_graph_combined_pilot": bool(support),
        "most_balanced_variant": best_variant,
        "support_reason": reason,
        "figure_paths": figure_paths,
        "summary_md_path": str(summary_md),
        "repair_notes": REPAIR_NOTES,
        "leakage_boundary_statement": "A019/A021 were read only after combined output existed; no GT/A021/source/legacy score entered ranking.",
    }
    with (pilot_dir / "evaluation_combined_summary.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_summary_md(
    path: Path,
    pilot_dir: Path,
    manifest: dict[str, Any],
    summary: pd.DataFrame,
    comparison: pd.DataFrame,
    cond: pd.DataFrame,
    support: bool,
    best_variant: str,
    reason: str,
    figure_paths: list[str],
    panel_queue: pd.DataFrame,
) -> None:
    c_main = summary[summary["variant"].isin(["c1", "c2", "c3"])]
    text = f"""# GM17 Phase4C Combined Structure+Temporal Fixed Pilot Run Summary {path.stem.split('_')[-2]}_{path.stem.split('_')[-1]}

## 1. Purpose

This run tests whether a pre-registered combination of recomputed temporal consistency and SAR structure can keep temporal center stability while improving best-proxy promotion.

## 2. Why Combined Instead Of V3

V1 has useful temporal center behavior but a temporal-zero artifact. Structure-only improves best-proxy promotion but worsens mean center error. Combined tests complementary fixed signals instead of searching A001/A005 table rules.

## 3. Candidate Pool

The candidate pool is the full A001 bank.

- Ranked candidates: {manifest.get('row_counts', {}).get('ranked_candidates')}
- Target groups: {manifest.get('row_counts', {}).get('target_groups')}
- No structure-selected, best-proxy, or best-center filtering was used.

## 4. Temporal Component

Temporal is recomputed from A001 `r/cross/az` and A005 `pred_r/pred_cross/pred_az`. Legacy `delta_*`, `temporal_factor_score`, and score fields are not used.

## 5. Structure Component

Structure is reused from the structure-only full A001 output. S1/S2 are active; S3 remains diagnostic.

## 6. Variant Definitions

- C1 `equal_temporal_s1`: 0.50 temporal + 0.50 S1.
- C2 `equal_temporal_s2`: 0.50 temporal + 0.50 S2.
- C3 `temporal_guard_structure_promote`: 0.67 temporal + 0.33 S1.
- C4 `structure_guard_temporal_soft_diagnostic`: 0.33 temporal + 0.67 S1, diagnostic.
- C5 `temporal_only_recomputed_baseline`: temporal only, internal baseline.

## 7. Output Directory

`{pilot_dir}`

## 8. Join Situation

Temporal join summary: `{manifest.get('join_summary', {}).get('temporal')}`

Structure join summary: `{manifest.get('join_summary', {}).get('structure')}`

## 9. Core Results

{md_table(summary[['variant','mean_center_error','median_center_error','mean_axis_aligned_proxy_iou','rank1_is_best_proxy_rate','best_proxy_top5_rate','best_proxy_top20_rate','mean_rank_of_best_proxy','rank1_temporal_zero_rate']], max_rows=10)}

## 10. Comparison With V1/V2/Structure-Only

{md_table(comparison[['variant','mean_center_error','mean_axis_aligned_proxy_iou','rank1_is_best_proxy_rate','best_proxy_top5_rate','best_proxy_top20_rate','mean_rank_of_best_proxy']], max_rows=20)}

## 11. Rank1 Best-Proxy

{md_table(c_main[['variant','rank1_is_best_proxy_rate','rank1_is_best_center_rate']], max_rows=10)}

## 12. Best-Proxy Top20

{md_table(c_main[['variant','best_proxy_top5_rate','best_proxy_top20_rate','mean_rank_of_best_proxy','median_rank_of_best_proxy']], max_rows=10)}

## 13. Structure-Only Center-Error Reduction

Combined C1/C2/C3 are checked against structure-only S1/S2 center error. The best balanced variant is `{best_variant}`.

## 14. Truncated+Occluded Groups

{md_table(cond[cond['condition_type'].astype(str).str.lower().eq('truncated+occluded')][['variant','truncation_degree','occlusion_degree','n_targets','rank1_is_best_proxy_rate','best_proxy_top20_rate','mean_center_error','mean_rank_of_best_proxy']], max_rows=30)}

## 15. Display/Pseudocolor Risk

The structure component remains display/pseudocolor-image based. This cannot be claimed as raw SAR physics.

## 16. A005 Legacy Soft-Prior Risk

The temporal component uses A005 soft predictions, but recomputes residuals from safe fields. Legacy score and delta fields are not used.

## 17. Support For Factor Graph Combined Pilot

Decision: `{support}`

Reason: {reason}

## 18. Failure Or Success Interpretation

If weak, likely causes include temporal-structure conflict, residual temporal artifact, display-image limits, A001 candidate issues, need for raw SAR, rotated OBB, or independent candidate proposal.

## 19. Next Step

- If C1/C2 is effective, write a factor graph prototype spec.
- If C3 is most balanced, continue with temporal-guarded structure design.
- If C4 only improves top-k but damages center error, keep it diagnostic.
- If all fail, move to raw SAR, rotated patch, or independent proposal.
- Do not return to table-level v3 tuning.

## Figures

{chr(10).join(f'- `{p}`' for p in figure_paths)}

## Panels

- Panel queue rows: {len(panel_queue)}
- Panels generated: {int(panel_queue['panel_generated'].sum()) if not panel_queue.empty else 0}

## Creative Next Ideas Appendix

Future ideas only; none affected this ranking:

- Raw SAR intensity version.
- Rotated OBB patch structure.
- Temporal-structure gating.
- Conditional future visibility/missing route.
- Independent candidate proposal.
- Factor graph prototype.
- Learned model future route.

## Explicit Non-Actions

- No v3 ranking.
- No threshold tuning.
- No training.
- No calibration.
- A021 not fed into inference.
- GT not used to tune rules.
- Source/provenance not used for sorting.

## Repair Notes

{chr(10).join(f'- {note}' for note in REPAIR_NOTES) if REPAIR_NOTES else '- No repair was needed.'}
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    pilot_dir = Path(args.pilot_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path(args.log_root) / f"gm17_phase4_combined_structure_temporal_fixed_pilot_eval_{timestamp}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    setup_logging(log_path)
    logging.info("Evaluation starts only after combined output exists.")
    for note in REPAIR_NOTES:
        logging.info("Repair note: %s", note)

    ranked_path = pilot_dir / "pilot_combined_candidates_ranked.csv"
    selected_path = pilot_dir / "pilot_combined_selected_rank1_by_variant.csv"
    manifest_path = pilot_dir / "pilot_combined_manifest.json"
    if not ranked_path.exists() or not selected_path.exists() or not manifest_path.exists():
        raise FileNotFoundError("Combined output incomplete; refusing post-inference evaluation.")
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    ranked = key_cols_as_text(read_required(ranked_path))
    a019 = read_required(Path(args.a019))
    a021 = read_required(Path(args.a021))
    v1_eval = key_cols_as_text(read_required(Path(args.v1_dir) / "evaluation_per_target.csv"))
    structure_ranked = key_cols_as_text(read_required(Path(args.structure_dir) / "pilot_structure_candidates_ranked.csv"))
    path_report = key_cols_as_text(read_required(Path(args.structure_dir) / "pilot_structure_path_resolution_report.csv"))

    evaluated = add_eval_geometry(ranked, a019)
    best = best_candidates(evaluated)
    conditions = condition_context(a021)
    per_variant = [evaluate_variant(evaluated, best, conditions, variant) for variant in VARIANTS]
    per_target = pd.concat(per_variant, ignore_index=True)
    summary = summarize(per_target)
    cond = condition_summary(per_target)
    comparison = comparison_table(summary, Path(args.structure_dir))
    support, best_variant, reason = support_decision(summary, comparison)

    per_target.to_csv(pilot_dir / "evaluation_combined_per_target_by_variant.csv", index=False, encoding="utf-8-sig")
    cond.to_csv(pilot_dir / "evaluation_combined_condition_groups_by_variant.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(pilot_dir / "evaluation_combined_vs_v1_v2_structure_comparison.csv", index=False, encoding="utf-8-sig")
    write_readme(pilot_dir, summary)
    figure_paths = make_figures(pilot_dir, comparison, summary, cond, per_target)
    panel_queue = make_panels(pilot_dir, per_target, evaluated, v1_eval, structure_ranked, path_report, args.max_panels)

    summary_md = Path("docs") / f"gm17_phase4_combined_structure_temporal_fixed_pilot_run_summary_{timestamp}.md"
    write_json(pilot_dir, timestamp, summary, comparison, per_target, cond, panel_queue, support, best_variant, reason, figure_paths, summary_md)
    write_summary_md(summary_md, pilot_dir, manifest, summary, comparison, cond, support, best_variant, reason, figure_paths, panel_queue)

    logging.info("Evaluation summary: %s", pilot_dir / "evaluation_combined_summary.json")
    logging.info("Run summary: %s", summary_md)
    logging.info("Support factor graph combined pilot: %s", support)
    print(
        json.dumps(
            {
                "pilot_dir": str(pilot_dir),
                "summary_md": str(summary_md),
                "support_factor_graph_combined_pilot": support,
                "most_balanced_variant": best_variant,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
