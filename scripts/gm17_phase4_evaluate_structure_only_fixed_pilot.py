#!/usr/bin/env python
"""Evaluate GM17 Phase4S structure-only fixed pilot after inference output exists."""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
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
DEFAULT_V1_DIAGNOSTICS = "output/gm17_phase4_minimal_factor_pilot_v1_diagnostics_20260628_113224"
DEFAULT_V2_DIR = "output/gm17_phase4_minimal_factor_pilot_v2_20260628_171204"
DEFAULT_LOG_ROOT = "logs"

GROUP_KEYS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
TARGET_KEYS = ["target_identity", "scene", "sar_frame_num"]
VARIANTS = {
    "s1": "primary_structure_rank3",
    "s2": "conservative_structure_rank2",
    "s3": "structure_with_spillover_diagnostic",
}
SAFE_GEOM_COLS = ["cx", "cy", "w", "h", "heading", "r", "az", "cross"]
ROLE_COLORS = {
    "structure_rank1": "#d62728",
    "v1_rank1": "#9467bd",
    "best_proxy": "#2ca02c",
    "best_center": "#1f77b4",
}
REPAIR_NOTES: list[str] = []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate structure-only fixed pilot.")
    parser.add_argument("--pilot-dir", required=True)
    parser.add_argument("--a019", default=DEFAULT_A019)
    parser.add_argument("--a021", default=DEFAULT_A021)
    parser.add_argument("--v1-dir", default=DEFAULT_V1_DIR)
    parser.add_argument("--v1-diagnostics", default=DEFAULT_V1_DIAGNOSTICS)
    parser.add_argument("--v2-dir", default=DEFAULT_V2_DIR)
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


def axis_iou(cand: pd.DataFrame) -> pd.Series:
    cand_x1 = cand["cx"] - cand["w"] / 2.0
    cand_y1 = cand["cy"] - cand["h"] / 2.0
    cand_x2 = cand["cx"] + cand["w"] / 2.0
    cand_y2 = cand["cy"] + cand["h"] / 2.0
    gt_x1 = cand["final_ax_x1"]
    gt_y1 = cand["final_ax_y1"]
    gt_x2 = cand["final_ax_x2"]
    gt_y2 = cand["final_ax_y2"]
    ix1 = np.maximum(cand_x1, gt_x1)
    iy1 = np.maximum(cand_y1, gt_y1)
    ix2 = np.minimum(cand_x2, gt_x2)
    iy2 = np.minimum(cand_y2, gt_y2)
    iw = np.maximum(0.0, ix2 - ix1)
    ih = np.maximum(0.0, iy2 - iy1)
    inter = iw * ih
    cand_area = np.maximum(0.0, cand_x2 - cand_x1) * np.maximum(0.0, cand_y2 - cand_y1)
    gt_area = np.maximum(0.0, gt_x2 - gt_x1) * np.maximum(0.0, gt_y2 - gt_y1)
    union = cand_area + gt_area - inter
    return inter / np.maximum(union, 1e-6)


def add_evaluation_geometry(ranked: pd.DataFrame, a019: pd.DataFrame) -> pd.DataFrame:
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
    merged = key_cols_as_text(ranked).merge(gt, on=TARGET_KEYS, how="left", validate="many_to_one")
    for col in ["cx", "cy", "w", "h", "final_cx", "final_cy", "final_ax_x1", "final_ax_y1", "final_ax_x2", "final_ax_y2"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")
    merged["center_error"] = np.sqrt((merged["cx"] - merged["final_cx"]) ** 2 + (merged["cy"] - merged["final_cy"]) ** 2)
    merged["axis_aligned_proxy_iou"] = axis_iou(merged)
    return merged


def best_candidates(evaluated: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in evaluated.groupby(GROUP_KEYS, dropna=False, sort=False):
        by_proxy = group.sort_values(["axis_aligned_proxy_iou", "candidate_id"], ascending=[False, True]).iloc[0]
        by_center = group.sort_values(["center_error", "candidate_id"], ascending=[True, True]).iloc[0]
        rows.append(
            {
                **dict(zip(GROUP_KEYS, key)),
                "best_proxy_candidate_id": by_proxy["candidate_id"],
                "best_proxy_iou": safe_float(by_proxy["axis_aligned_proxy_iou"]),
                "best_proxy_center_error": safe_float(by_proxy["center_error"]),
                "best_center_candidate_id": by_center["candidate_id"],
                "best_center_error": safe_float(by_center["center_error"]),
                "best_center_proxy_iou": safe_float(by_center["axis_aligned_proxy_iou"]),
            }
        )
    return pd.DataFrame(rows)


def condition_context(a021: pd.DataFrame) -> pd.DataFrame:
    cols = ["target_identity", "scene", "sar_frame_num", "condition_type", "condition_status", "truncation_degree", "occlusion_degree"]
    keep = key_cols_as_text(a021[cols], TARGET_KEYS)
    keep = keep[keep["scene"].eq("GM_RM017")]
    return keep.drop_duplicates(TARGET_KEYS)


def evaluate_variant(evaluated: pd.DataFrame, best: pd.DataFrame, conditions: pd.DataFrame, variant: str) -> pd.DataFrame:
    rank_col = f"{variant}_rank"
    rows: list[dict[str, Any]] = []
    for key, group in evaluated.groupby(GROUP_KEYS, dropna=False, sort=False):
        group = group.sort_values([rank_col, "candidate_id"], ascending=[True, True])
        rank1 = group.iloc[0]
        top3 = group.head(3)
        top5 = group.head(5)
        top20 = group.head(20)
        best_row = best
        for col, value in zip(GROUP_KEYS, key):
            best_row = best_row[best_row[col].astype(str).eq(str(value))]
        if best_row.empty:
            continue
        b = best_row.iloc[0]
        best_proxy_id = b["best_proxy_candidate_id"]
        best_center_id = b["best_center_candidate_id"]
        best_proxy_matches = group[group["candidate_id"].astype(str).eq(str(best_proxy_id))]
        best_center_matches = group[group["candidate_id"].astype(str).eq(str(best_center_id))]
        best_proxy_rank = safe_float(best_proxy_matches.iloc[0][rank_col]) if not best_proxy_matches.empty else math.nan
        best_center_rank = safe_float(best_center_matches.iloc[0][rank_col]) if not best_center_matches.empty else math.nan
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
                "structure_score": rank1[f"{variant}_score"],
                "structure_rank": rank1[rank_col],
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
                "rank1_temporal_zero_dependency": "not_applicable_independent_from_A005",
                "rank1_feature_status": rank1.get("structure_feature_status", ""),
                "rank1_feature_source_image_type": rank1.get("feature_source_image_type", ""),
                "rank1_box_to_background_ratio": safe_float(rank1.get("box_to_background_ratio")),
                "rank1_inside_energy_fraction": safe_float(rank1.get("inside_energy_fraction")),
                "rank1_optional_local_contrast": safe_float(rank1.get("optional_local_contrast")),
                "rank1_edge_spillover_ratio": safe_float(rank1.get("edge_spillover_ratio")),
            }
        )
    out = pd.DataFrame(rows)
    if not conditions.empty:
        out = out.merge(conditions, on=TARGET_KEYS, how="left")
    return out


def summarize_variant(per_target: pd.DataFrame) -> pd.DataFrame:
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
                "rank1_temporal_zero_rate": math.nan,
                "rank1_temporal_zero_dependency": "not_applicable_independent_from_A005",
                "n_targets": int(len(group)),
            }
        )
    return pd.DataFrame(rows)


def condition_groups(per_target: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["variant", "variant_name", "condition_type", "truncation_degree", "occlusion_degree"]
    return (
        per_target.groupby(group_cols, dropna=False)
        .agg(
            n_targets=("candidate_id", "count"),
            mean_center_error=("center_error", "mean"),
            median_center_error=("center_error", "median"),
            mean_axis_aligned_proxy_iou=("axis_aligned_proxy_iou", "mean"),
            rank1_is_best_proxy_rate=("rank1_is_best_proxy", "mean"),
            rank1_is_best_center_rate=("rank1_is_best_center", "mean"),
            best_proxy_top5_rate=("best_proxy_in_top5", "mean"),
            best_proxy_top20_rate=("best_proxy_in_top20", "mean"),
            proxy_iou_recall_at_1_threshold_0_25=("proxy_hit_iou_0_25", "mean"),
            center_recall_at_1_threshold_50px=("center_hit_50px", "mean"),
            mean_rank_of_best_proxy=("best_proxy_rank", "mean"),
        )
        .reset_index()
    )


def comparison_table(structure_summary: pd.DataFrame, v2_dir: Path) -> pd.DataFrame:
    v2_compare_path = v2_dir / "evaluation_v2_vs_v1_comparison.csv"
    if v2_compare_path.exists():
        compare = pd.read_csv(v2_compare_path)
    else:
        compare = pd.DataFrame()
    rows = []
    for _, row in structure_summary.iterrows():
        rows.append(
            {
                "variant": row["variant"],
                "variant_name": row["variant_name"],
                "mean_center_error": row["mean_center_error"],
                "median_center_error": row["median_center_error"],
                "mean_axis_aligned_proxy_iou": row["mean_axis_aligned_proxy_iou"],
                "proxy_iou_recall_at_1_threshold_0_25": row["proxy_iou_recall_at_1_threshold_0_25"],
                "center_recall_at_1_threshold_50px": row["center_recall_at_1_threshold_50px"],
                "proxy_iou_recall_at_3_threshold_0_25": row["proxy_iou_recall_at_3_threshold_0_25"],
                "proxy_iou_recall_at_5_threshold_0_25": row["proxy_iou_recall_at_5_threshold_0_25"],
                "rank1_is_best_proxy_rate": row["rank1_is_best_proxy_rate"],
                "rank1_is_best_center_rate": row["rank1_is_best_center_rate"],
                "best_proxy_top5_rate": row["best_proxy_top5_rate"],
                "best_proxy_top20_rate": row["best_proxy_top20_rate"],
                "mean_rank_of_best_proxy": row["mean_rank_of_best_proxy"],
                "rank1_temporal_zero_rate": math.nan,
                "n_targets": row["n_targets"],
                "median_axis_aligned_proxy_iou": row["median_axis_aligned_proxy_iou"],
                "center_recall_at_3_threshold_50px": row["center_recall_at_3_threshold_50px"],
                "center_recall_at_5_threshold_50px": row["center_recall_at_5_threshold_50px"],
                "best_proxy_iou_coverage_threshold_0_25": row["best_proxy_iou_coverage_threshold_0_25"],
                "best_center_coverage_threshold_50px": row["best_center_coverage_threshold_50px"],
                "median_rank_of_best_proxy": row["median_rank_of_best_proxy"],
                "rank1_temporal_zero_dependency": row["rank1_temporal_zero_dependency"],
            }
        )
    structure = pd.DataFrame(rows)
    if not compare.empty:
        if "variant_name" not in compare.columns:
            compare["variant_name"] = compare["variant"]
        if "rank1_temporal_zero_dependency" not in compare.columns:
            compare["rank1_temporal_zero_dependency"] = ""
        all_cols = list(dict.fromkeys(list(compare.columns) + list(structure.columns)))
        return pd.concat([compare.reindex(columns=all_cols), structure.reindex(columns=all_cols)], ignore_index=True)
    return structure


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
    fig, ax = plt.subplots(figsize=(11, 5), dpi=140)
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


def make_figures(pilot_dir: Path, comparison: pd.DataFrame, structure_summary: pd.DataFrame, condition_summary: pd.DataFrame, selected: pd.DataFrame) -> list[str]:
    figures_dir = pilot_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    plot_compare = comparison.copy()
    plot_compare["variant_label"] = plot_compare["variant"].astype(str)
    for name, cols, title, ylabel in [
        (
            "structure_vs_v1_v2_proxy_iou_recall_bar.png",
            [
                "proxy_iou_recall_at_1_threshold_0_25",
                "proxy_iou_recall_at_3_threshold_0_25",
                "proxy_iou_recall_at_5_threshold_0_25",
            ],
            "Proxy IoU recall, structure vs v1/v2",
            "recall",
        ),
        (
            "structure_vs_v1_v2_center_error_bar.png",
            ["mean_center_error", "median_center_error"],
            "Center error, structure vs v1/v2",
            "pixels",
        ),
        (
            "structure_rank1_best_proxy_rate_bar.png",
            ["rank1_is_best_proxy_rate"],
            "Rank1 is best-proxy rate",
            "rate",
        ),
        (
            "structure_best_proxy_topk_bar.png",
            ["best_proxy_top5_rate", "best_proxy_top20_rate"],
            "Best-proxy top-k rate",
            "rate",
        ),
    ]:
        path = figures_dir / name
        bar_plot(plot_compare, "variant_label", cols, path, title, ylabel)
        paths.append(str(path))

    cond = condition_summary.copy()
    cond["condition_label"] = cond["condition_type"].astype(str) + "/" + cond["truncation_degree"].astype(str) + "/" + cond["occlusion_degree"].astype(str)
    cond = cond[cond["variant"].isin(["s1", "s2", "s3"])]
    cond = cond[cond["n_targets"] >= 3]
    pivot = cond.pivot_table(index="condition_label", columns="variant", values="rank1_is_best_proxy_rate", aggfunc="mean").fillna(0)
    fig, ax = plt.subplots(figsize=(11, max(4, 0.4 * max(1, len(pivot)))), dpi=140)
    if not pivot.empty:
        failure = 1.0 - pivot
        x = np.arange(len(failure))
        width = 0.25
        for i, col in enumerate(failure.columns):
            ax.barh(x + (i - 1) * width, failure[col], height=width, label=col)
        ax.set_yticks(x)
        ax.set_yticklabels(failure.index, fontsize=7)
        ax.set_xlabel("1 - rank1_is_best_proxy_rate")
        ax.legend()
    else:
        ax.text(0.5, 0.5, "No condition groups with n>=3", ha="center", va="center")
        ax.set_axis_off()
    ax.set_title("Structure condition group failure rate")
    fig.tight_layout()
    path = figures_dir / "structure_condition_group_failure_bar.png"
    fig.savefig(path)
    plt.close(fig)
    paths.append(str(path))

    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    feature_cols = ["box_to_background_ratio", "inside_energy_fraction", "optional_local_contrast", "edge_spillover_ratio"]
    data = []
    labels = []
    for variant in ["s1", "s2", "s3"]:
        view = selected[selected["variant"].eq(variant)]
        for feature in feature_cols:
            if feature in view.columns:
                vals = pd.to_numeric(view[feature], errors="coerce").dropna().to_numpy()
                if vals.size:
                    data.append(vals)
                    labels.append(f"{variant}:{feature}")
    if data:
        ax.boxplot(data, tick_labels=labels, showfliers=False)
        ax.tick_params(axis="x", rotation=35)
        ax.set_ylabel("feature value")
    else:
        ax.text(0.5, 0.5, "No selected feature values", ha="center", va="center")
        ax.set_axis_off()
    ax.set_title("Structure feature distribution by selected variant")
    fig.tight_layout()
    path = figures_dir / "structure_feature_distribution_by_selected_variant.png"
    fig.savefig(path)
    plt.close(fig)
    paths.append(str(path))
    return paths


def compact_id(value: Any) -> str:
    text = norm_str(value)
    return text if len(text) <= 18 else text[:9] + "..." + text[-6:]


def draw_box(ax: plt.Axes, row: pd.Series, label: str, color: str) -> None:
    cx, cy, w, h = (safe_float(row.get(col)) for col in ["cx", "cy", "w", "h"])
    if not all(math.isfinite(v) for v in [cx, cy, w, h]) or w <= 0 or h <= 0:
        return
    rect = Rectangle((cx - w / 2, cy - h / 2), w, h, fill=False, edgecolor=color, linewidth=1.8)
    ax.add_patch(rect)
    ax.text(
        cx - w / 2,
        cy - h / 2,
        label,
        color=color,
        fontsize=7,
        bbox={"facecolor": "black", "alpha": 0.45, "pad": 1, "edgecolor": "none"},
    )


def make_panel(
    image_path: str,
    out_path: Path,
    title: str,
    structure_row: pd.Series,
    v1_row: pd.Series | None,
    best_proxy_row: pd.Series,
    best_center_row: pd.Series,
) -> bool:
    image, status = scout.load_image(image_path)
    if image is None:
        return False
    roles = [
        ("structure_rank1", structure_row),
        ("v1_rank1", v1_row),
        ("best_proxy", best_proxy_row),
        ("best_center", best_center_row),
    ]
    fig = plt.figure(figsize=(14, 8), dpi=140)
    grid = fig.add_gridspec(2, 3, width_ratios=[2.1, 1, 1], height_ratios=[1, 1])
    ax_main = fig.add_subplot(grid[:, 0])
    ax_main.imshow(image, cmap="gray", vmin=0, vmax=1)
    ax_main.set_title("overview")
    ax_main.set_axis_off()
    for role, row in roles:
        if row is None:
            continue
        draw_box(ax_main, row, f"{role}\n{compact_id(row.get('candidate_id'))}", ROLE_COLORS[role])
    for idx, (role, row) in enumerate(roles):
        ax = fig.add_subplot(grid[idx // 2, idx % 2 + 1])
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
            f"IoU={safe_float(row.get('axis_aligned_proxy_iou')):.3f} "
            f"err={safe_float(row.get('center_error')):.1f}",
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
    path_report: pd.DataFrame,
    max_panels: int,
) -> pd.DataFrame:
    panels_dir = pilot_dir / "panels"
    panels_dir.mkdir(parents=True, exist_ok=True)
    candidates = []
    for variant, group in per_target.groupby("variant", sort=False):
        fail = group[~group["rank1_is_best_proxy"]].sort_values(["best_proxy_iou", "center_error"], ascending=[False, False]).head(8)
        success = group[group["rank1_is_best_proxy"]].sort_values("axis_aligned_proxy_iou", ascending=False).head(5)
        trunc = group[group["condition_type"].astype(str).str.lower().eq("truncated+occluded")].sort_values("best_proxy_iou", ascending=False).head(7)
        for case_type, frame in [("failure", fail), ("success", success), ("truncated_occluded", trunc)]:
            for _, row in frame.iterrows():
                item = row.to_dict()
                item["panel_case_type"] = case_type
                candidates.append(item)
    queue = pd.DataFrame(candidates).drop_duplicates(["variant", *GROUP_KEYS]).head(max_panels)
    path_by_key = {
        tuple(norm_str(row.get(col, "")) if col != "sar_frame_num" else safe_int_text(row.get(col, "")) for col in GROUP_KEYS): row
        for row in path_report.to_dict("records")
    }
    v1_eval = key_cols_as_text(v1_eval)
    panel_rows = []
    for idx, row in queue.reset_index(drop=True).iterrows():
        key = tuple(norm_str(row.get(col, "")) if col != "sar_frame_num" else safe_int_text(row.get(col, "")) for col in GROUP_KEYS)
        group = evaluated
        for col, value in zip(GROUP_KEYS, key):
            group = group[group[col].astype(str).eq(str(value))]
        if group.empty:
            continue
        structure = group[group["candidate_id"].astype(str).eq(str(row["candidate_id"]))].iloc[0]
        best_proxy = group[group["candidate_id"].astype(str).eq(str(row["best_proxy_candidate_id"]))].iloc[0]
        best_center = group[group["candidate_id"].astype(str).eq(str(row["best_center_candidate_id"]))].iloc[0]
        v1_matches = v1_eval
        for col, value in zip(GROUP_KEYS, key):
            v1_matches = v1_matches[v1_matches[col].astype(str).eq(str(value))]
        v1_row = None
        if not v1_matches.empty:
            v1_id = norm_str(v1_matches.iloc[0].get("candidate_id"))
            match = group[group["candidate_id"].astype(str).eq(v1_id)]
            if not match.empty:
                v1_row = match.iloc[0]
        image_path = norm_str(path_by_key.get(key, {}).get("resolved_path", ""))
        out_path = panels_dir / f"{row['variant']}_{idx+1:03d}_{row['panel_case_type']}_structure_panel.png"
        title = (
            f"diagnostic review only, structure-only pre-registered output, no tuning | "
            f"{row['variant']} {row['panel_case_type']}"
        )
        generated = make_panel(image_path, out_path, title, structure, v1_row, best_proxy, best_center)
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
    panel_queue.to_csv(pilot_dir / "evaluation_structure_panel_queue.csv", index=False, encoding="utf-8-sig")
    return panel_queue


def support_combined(summary: pd.DataFrame, comparison: pd.DataFrame) -> tuple[bool, str]:
    v1_rows = comparison[comparison["variant"].astype(str).eq("v1")]
    if v1_rows.empty:
        return False, "No v1 baseline row available for combined-pilot decision."
    v1 = v1_rows.iloc[0]
    s12 = summary[summary["variant"].isin(["s1", "s2"])]
    if s12.empty:
        return False, "S1/S2 summary rows missing."
    best_rank1 = float(s12["rank1_is_best_proxy_rate"].max())
    best_top20 = float(s12["best_proxy_top20_rate"].max())
    improved_rank1 = best_rank1 > safe_float(v1.get("rank1_is_best_proxy_rate"))
    improved_top20 = best_top20 > safe_float(v1.get("best_proxy_top20_rate"))
    if improved_rank1 or improved_top20:
        return True, "S1/S2 improves at least one primary best-proxy promotion metric over v1; combined pilot is justified as a pre-registered next test."
    return False, "S1/S2 does not improve primary best-proxy promotion metrics over v1; inspect panels before combined pilot."


def write_readme(pilot_dir: Path, summary: pd.DataFrame, comparison: pd.DataFrame) -> None:
    text = "# Structure-Only Fixed Pilot Evaluation\n\n"
    text += "This directory contains post-inference evaluation for the pre-registered structure-only pilot. A019/A021 were read only after pilot ranked output existed.\n\n"
    text += "## Variant Summary\n\n"
    text += md_table(summary[["variant", "mean_center_error", "mean_axis_aligned_proxy_iou", "rank1_is_best_proxy_rate", "best_proxy_top5_rate", "best_proxy_top20_rate"]])
    text += "\n"
    (pilot_dir / "evaluation_structure_readme.md").write_text(text, encoding="utf-8")


def write_summary_json(
    pilot_dir: Path,
    eval_timestamp: str,
    summary: pd.DataFrame,
    comparison: pd.DataFrame,
    per_target: pd.DataFrame,
    condition_summary: pd.DataFrame,
    panel_queue: pd.DataFrame,
    support: bool,
    support_reason: str,
    figure_paths: list[str],
    summary_md_path: Path,
) -> None:
    payload = {
        "evaluation_timestamp": eval_timestamp,
        "pilot_dir": str(pilot_dir),
        "target_count": int(per_target[GROUP_KEYS].drop_duplicates().shape[0]),
        "variants": summary.to_dict("records"),
        "comparison_rows": comparison.to_dict("records"),
        "condition_group_rows": condition_summary.to_dict("records"),
        "panel_generated_count": int(panel_queue["panel_generated"].sum()) if not panel_queue.empty else 0,
        "support_combined_structure_temporal_pilot": bool(support),
        "support_reason": support_reason,
        "rank1_temporal_zero_dependency": "not_applicable_independent_from_A005",
        "figure_paths": figure_paths,
        "summary_md_path": str(summary_md_path),
        "repair_notes": REPAIR_NOTES,
        "leakage_boundary_statement": (
            "A019/A021 were read only after structure-only ranked output existed. "
            "No GT/A021/source/legacy score was used for structure ranking."
        ),
    }
    with (pilot_dir / "evaluation_structure_summary.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_run_summary(
    path: Path,
    pilot_dir: Path,
    manifest: dict[str, Any],
    summary: pd.DataFrame,
    comparison: pd.DataFrame,
    condition_summary: pd.DataFrame,
    support: bool,
    support_reason: str,
    figure_paths: list[str],
    panel_queue: pd.DataFrame,
) -> None:
    s1s2 = summary[summary["variant"].isin(["s1", "s2"])]
    failure_reason = "Structure-only signal is useful but remains display-image limited; combine only through a pre-registered next spec."
    if not support:
        failure_reason = "Structure-only signal does not clearly improve best-proxy promotion globally; likely causes include feature insufficiency, display image limits, need for raw SAR, rotated boxes, or independent candidate proposal."
    text = f"""# GM17 Phase4S Structure-Only Fixed Pilot Run Summary {path.stem.split('_')[-2]}_{path.stem.split('_')[-1]}

## 1. Purpose

This run tests a pre-registered structure-only SAR ranking signal over the full A001 GM_RM017 candidate bank.

## 2. Why This Is Pre-Registered

The active features, rank-percentile scoring, variant definitions, and tie-break were fixed before evaluation. A019/A021 were read only after `pilot_structure_candidates_ranked.csv` and `pilot_structure_selected_rank1_by_variant.csv` existed.

## 3. Candidate Pool

The candidate pool is the full A001 bank, not full-audit `best_proxy` or `best_center` role candidates.

- A001 candidates: {manifest.get('row_counts', {}).get('a001_candidates')}
- Target groups: {manifest.get('row_counts', {}).get('target_groups')}

## 4. Active And Diagnostic Features

Active features are `box_to_background_ratio`, `inside_energy_fraction`, and `optional_local_contrast`. `edge_spillover_ratio` is active only in diagnostic S3.

Diagnostic-only fields include `box_mean_intensity`, `local_background_mean`, `structure_feature_status`, `feature_source_image_type`, `box_clip_fraction`, and `local_patch_area_px`.

## 5. Variant Definitions

- S1 `primary_structure_rank3`: three active features, equal rank-percentile mean.
- S2 `conservative_structure_rank2`: `box_to_background_ratio` and `inside_energy_fraction`, equal rank-percentile mean.
- S3 `structure_with_spillover_diagnostic`: S1 features plus lower-is-better `edge_spillover_ratio`; diagnostic only.

Lower score is better. Tie-break is `candidate_id` ascending only.

## 6. Output Directory

`{pilot_dir}`

## 7. Path Resolution And Image Reading

- Image read success rate: {manifest.get('image_read_success', {}).get('success_rate')}
- Feature valid rate: {manifest.get('feature_valid_rate')}
- Feature source risk: diagnostic display/pseudocolor image.

## 8. Core Results

{md_table(summary[['variant','mean_center_error','median_center_error','mean_axis_aligned_proxy_iou','rank1_is_best_proxy_rate','best_proxy_top5_rate','best_proxy_top20_rate','mean_rank_of_best_proxy']], max_rows=10)}

## 9. V1/V2 Comparison

{md_table(comparison[['variant','mean_center_error','mean_axis_aligned_proxy_iou','rank1_is_best_proxy_rate','best_proxy_top5_rate','best_proxy_top20_rate','mean_rank_of_best_proxy']], max_rows=10)}

## 10. Rank1 Best-Proxy

S1/S2 rank1 best-proxy rates:

{md_table(s1s2[['variant','rank1_is_best_proxy_rate','rank1_is_best_center_rate']], max_rows=10)}

## 11. Best-Proxy Top5/Top20

{md_table(s1s2[['variant','best_proxy_top5_rate','best_proxy_top20_rate','mean_rank_of_best_proxy','median_rank_of_best_proxy']], max_rows=10)}

## 12. Truncated+Occluded Groups

{md_table(condition_summary[condition_summary['condition_type'].astype(str).str.lower().eq('truncated+occluded')][['variant','truncation_degree','occlusion_degree','n_targets','rank1_is_best_proxy_rate','best_proxy_top5_rate','best_proxy_top20_rate','mean_rank_of_best_proxy']], max_rows=20)}

## 13. Display/Pseudocolor Risk

This is a diagnostic display-image pilot. It does not prove raw SAR intensity physics. A raw SAR version should be audited before physical claims.

## 14. Support For Combined Structure+Temporal Pilot

Decision: `{support}`

Reason: {support_reason}

## 15. Failure Or Success Interpretation

{failure_reason}

## 16. Next Step

- If S1/S2 is useful, write a combined factor pilot pre-registered spec.
- If structure-only is weak but specific groups improve, run condition/failure diagnostics.
- If globally weak, move toward raw SAR or independent candidate proposal.
- Do not return to table-level v3 tuning.

## 17. Explicit Non-Actions

- No v3 ranking was generated.
- No threshold was tuned.
- No training was performed.
- No calibration was performed.
- A021 was not fed into inference.
- GT was not used to tune rules.
- Source/provenance was not used for sorting.

## Figures

{chr(10).join(f'- `{p}`' for p in figure_paths)}

## Panels

- Panel queue rows: {len(panel_queue)}
- Panels generated: {int(panel_queue['panel_generated'].sum()) if not panel_queue.empty else 0}

## Creative Next Ideas Appendix

These are future ideas only; none entered this ranking:

- Raw SAR intensity version of the same fixed features.
- Rotated OBB patch features instead of axis-aligned crops.
- Ridge or axis support descriptors.
- Local peak-cluster support instead of single-pixel peak evidence.
- Structure+temporal gating with pre-registered ownership boundaries.
- Independent SAR candidate proposal for cases where A001 lacks the right structure-support candidate.
- Learned model route after raw-SAR and leakage controls are settled.

## Repair Notes

{chr(10).join(f'- {note}' for note in REPAIR_NOTES) if REPAIR_NOTES else '- No repair was needed.'}
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    pilot_dir = Path(args.pilot_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path(args.log_root) / f"gm17_phase4_structure_only_fixed_pilot_eval_{timestamp}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    setup_logging(log_path)
    logging.info("Evaluation starts only after pilot output exists.")
    for note in REPAIR_NOTES:
        logging.info("Repair note: %s", note)

    ranked_path = pilot_dir / "pilot_structure_candidates_ranked.csv"
    selected_path = pilot_dir / "pilot_structure_selected_rank1_by_variant.csv"
    manifest_path = pilot_dir / "pilot_structure_manifest.json"
    if not ranked_path.exists() or not selected_path.exists() or not manifest_path.exists():
        raise FileNotFoundError("Pilot output is incomplete; refusing to read A019/A021 before pilot output exists.")

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    ranked = key_cols_as_text(read_required(ranked_path))
    selected = key_cols_as_text(read_required(selected_path))

    a019 = read_required(Path(args.a019))
    a021 = read_required(Path(args.a021))
    v1_eval = key_cols_as_text(read_required(Path(args.v1_dir) / "evaluation_per_target.csv"))
    v1_diag_summary_path = Path(args.v1_diagnostics) / "diagnostic_summary.json"
    if v1_diag_summary_path.exists():
        logging.info("Reading %s", v1_diag_summary_path)
        _ = json.load(v1_diag_summary_path.open("r", encoding="utf-8"))

    evaluated = add_evaluation_geometry(ranked, a019)
    best = best_candidates(evaluated)
    conditions = condition_context(a021)
    per_variant = []
    for variant in ["s1", "s2", "s3"]:
        per_variant.append(evaluate_variant(evaluated, best, conditions, variant))
    per_target = pd.concat(per_variant, ignore_index=True)
    summary = summarize_variant(per_target)
    cond_summary = condition_groups(per_target)
    comparison = comparison_table(summary, Path(args.v2_dir))
    support, support_reason = support_combined(summary, comparison)

    per_target.to_csv(pilot_dir / "evaluation_structure_per_target_by_variant.csv", index=False, encoding="utf-8-sig")
    cond_summary.to_csv(pilot_dir / "evaluation_structure_condition_groups_by_variant.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(pilot_dir / "evaluation_structure_vs_v1_v2_comparison.csv", index=False, encoding="utf-8-sig")
    write_readme(pilot_dir, summary, comparison)

    path_report = key_cols_as_text(read_required(pilot_dir / "pilot_structure_path_resolution_report.csv"))
    figure_paths = make_figures(pilot_dir, comparison, summary, cond_summary, selected)
    panel_queue = make_panels(pilot_dir, per_target, evaluated, v1_eval, path_report, args.max_panels)

    summary_md_path = Path("docs") / f"gm17_phase4_structure_only_fixed_pilot_run_summary_{timestamp}.md"
    write_summary_json(
        pilot_dir,
        timestamp,
        summary,
        comparison,
        per_target,
        cond_summary,
        panel_queue,
        support,
        support_reason,
        figure_paths,
        summary_md_path,
    )
    write_run_summary(
        summary_md_path,
        pilot_dir,
        manifest,
        summary,
        comparison,
        cond_summary,
        support,
        support_reason,
        figure_paths,
        panel_queue,
    )

    logging.info("Evaluation summary: %s", pilot_dir / "evaluation_structure_summary.json")
    logging.info("Run summary: %s", summary_md_path)
    logging.info("Support combined pilot: %s", support)
    print(
        json.dumps(
            {
                "pilot_dir": str(pilot_dir),
                "summary_md": str(summary_md_path),
                "support_combined_structure_temporal_pilot": support,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
