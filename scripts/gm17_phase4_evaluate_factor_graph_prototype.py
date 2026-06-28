#!/usr/bin/env python
"""Evaluate GM17 Phase4 factor graph prototype after output exists."""

from __future__ import annotations

import argparse
import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_A019 = "output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv"
DEFAULT_A021 = "output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv"
DEFAULT_COMBINED_DIR = "output/gm17_phase4_combined_structure_temporal_fixed_pilot_20260628_224407"
DEFAULT_LOG_ROOT = "logs"
DEFAULT_DOCS_DIR = "docs"

GROUP_KEYS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
TARGET_KEYS = ["target_identity", "scene", "sar_frame_num"]
BRANCHES = {
    "c3": {
        "branch_name": "prototype_c3_temporal_guard_structure_promote",
        "score_col": "c3_energy",
        "rank_col": "c3_rank",
        "phase4c_score_col": "c3_score",
        "phase4c_rank_col": "c3_rank",
        "primary": True,
    },
    "c4_diagnostic": {
        "branch_name": "prototype_c4_structure_guard_temporal_soft_diagnostic",
        "score_col": "c4_diagnostic_energy",
        "rank_col": "c4_diagnostic_rank",
        "phase4c_score_col": "c4_score",
        "phase4c_rank_col": "c4_rank",
        "primary": False,
    },
}
EPS = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate GM17 Phase4 factor graph prototype.")
    parser.add_argument("--prototype-dir", required=True)
    parser.add_argument("--a019", default=DEFAULT_A019)
    parser.add_argument("--a021", default=DEFAULT_A021)
    parser.add_argument("--combined-dir", default=DEFAULT_COMBINED_DIR)
    parser.add_argument("--log-root", default=DEFAULT_LOG_ROOT)
    parser.add_argument("--docs-dir", default=DEFAULT_DOCS_DIR)
    return parser.parse_args()


def setup_logging(log_path: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )


def norm_str(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        head = text[:-2]
        if head.lstrip("-").isdigit():
            return head
    return text


def safe_int_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return norm_str(value)
    if np.isfinite(numeric):
        return str(int(numeric))
    return norm_str(value)


def safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return math.nan
    return out if math.isfinite(out) else math.nan


def key_cols_as_text(df: pd.DataFrame, keys: list[str] = GROUP_KEYS) -> pd.DataFrame:
    out = df.copy()
    for col in keys:
        if col in out.columns:
            if col == "sar_frame_num":
                out[col] = out[col].map(safe_int_text)
            else:
                out[col] = out[col].map(norm_str)
    if "candidate_id" in out.columns:
        out["candidate_id"] = out["candidate_id"].map(norm_str)
    return out


def read_required(path: Path, **kwargs: Any) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    logging.info("Reading %s", path)
    return pd.read_csv(path, **kwargs)


def require_prototype_outputs(prototype_dir: Path) -> dict[str, Path]:
    required = {
        "nodes": prototype_dir / "factor_graph_candidate_nodes.csv",
        "factors": prototype_dir / "factor_graph_factor_values.csv",
        "messages": prototype_dir / "factor_graph_messages.csv",
        "energy": prototype_dir / "factor_graph_energy.csv",
        "selected": prototype_dir / "factor_graph_selected_rank1.csv",
        "manifest": prototype_dir / "factor_graph_prototype_manifest.json",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Prototype output incomplete, missing: {missing}")
    return required


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


def build_ranked(nodes: pd.DataFrame, factors: pd.DataFrame, energy: pd.DataFrame) -> pd.DataFrame:
    node_cols = ["candidate_id", *GROUP_KEYS, "cx", "cy", "w", "h", "heading", "r", "az", "cross", "node_status"]
    factor_cols = [
        "candidate_id",
        *GROUP_KEYS,
        "temporal_distance_raw",
        "temporal_rank_percentile",
        "s1_score",
        "s1_rank_percentile",
        "s2_score",
        "s2_rank_percentile",
        "temporal_factor_status",
        "sar_structure_factor_status",
        "feature_source_image_type",
    ]
    out = nodes[node_cols].merge(factors[factor_cols], on=["candidate_id", *GROUP_KEYS], how="inner", validate="one_to_one")
    out = out.merge(energy, on=["candidate_id", *GROUP_KEYS], how="inner", validate="one_to_one")
    return key_cols_as_text(out)


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
    out = ranked.merge(gt, on=TARGET_KEYS, how="left", validate="many_to_one")
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


def evaluate_branch(evaluated: pd.DataFrame, best: pd.DataFrame, conditions: pd.DataFrame, branch: str) -> pd.DataFrame:
    definition = BRANCHES[branch]
    rank_col = definition["rank_col"]
    score_col = definition["score_col"]
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
        temporal_distance = safe_float(rank1.get("temporal_distance_raw"))
        rows.append(
            {
                **dict(zip(GROUP_KEYS, key)),
                "branch": branch,
                "branch_name": definition["branch_name"],
                "branch_role": "primary" if definition["primary"] else "diagnostic",
                "candidate_id": rank1["candidate_id"],
                "cx": rank1["cx"],
                "cy": rank1["cy"],
                "w": rank1["w"],
                "h": rank1["h"],
                "heading": rank1["heading"],
                "r": rank1["r"],
                "az": rank1["az"],
                "cross": rank1["cross"],
                "prototype_energy": rank1[score_col],
                "prototype_rank": rank1[rank_col],
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
                "rank1_temporal_zero": bool(math.isfinite(temporal_distance) and abs(temporal_distance) <= 1e-9),
                "temporal_zero_status": "zero" if math.isfinite(temporal_distance) and abs(temporal_distance) <= 1e-9 else "nonzero_or_unavailable",
                "rank1_temporal_rank_percentile": safe_float(rank1.get("temporal_rank_percentile")),
                "rank1_s1_rank_percentile": safe_float(rank1.get("s1_rank_percentile")),
                "rank1_s2_rank_percentile": safe_float(rank1.get("s2_rank_percentile")),
                "rank1_temporal_factor_status": rank1.get("temporal_factor_status", ""),
                "rank1_sar_structure_factor_status": rank1.get("sar_structure_factor_status", ""),
                "rank1_feature_source_image_type": rank1.get("feature_source_image_type", ""),
            }
        )
    out = pd.DataFrame(rows)
    if not conditions.empty:
        out = out.merge(conditions, on=TARGET_KEYS, how="left")
    return out


def summarize(per_target: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for branch, group in per_target.groupby("branch", sort=False):
        rows.append(
            {
                "branch": branch,
                "branch_name": group["branch_name"].iloc[0],
                "branch_role": group["branch_role"].iloc[0],
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
                "rank1_temporal_zero_rate": float(group["rank1_temporal_zero"].mean()),
                "n_targets": int(len(group)),
            }
        )
    return pd.DataFrame(rows)


def condition_summary(per_target: pd.DataFrame) -> pd.DataFrame:
    cols = ["branch", "branch_name", "branch_role", "condition_type", "truncation_degree", "occlusion_degree"]
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


def alignment_with_phase4c(prototype_dir: Path, ranked: pd.DataFrame, combined_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    combined = key_cols_as_text(
        read_required(
            combined_dir / "pilot_combined_candidates_ranked.csv",
            usecols=["candidate_id", *GROUP_KEYS, "c3_score", "c3_rank", "c4_score", "c4_rank"],
        )
    )
    rows = []
    diff_frames = []
    for branch, definition in BRANCHES.items():
        score_col = definition["score_col"]
        rank_col = definition["rank_col"]
        phase_score = definition["phase4c_score_col"]
        phase_rank = definition["phase4c_rank_col"]
        proto_view = ranked[["candidate_id", *GROUP_KEYS, score_col, rank_col]].rename(
            columns={score_col: "prototype_score", rank_col: "prototype_rank"}
        )
        phase_view = combined[["candidate_id", *GROUP_KEYS, phase_score, phase_rank]].rename(
            columns={phase_score: "phase4c_score", phase_rank: "phase4c_rank"}
        )
        merged = proto_view.merge(
            phase_view,
            on=["candidate_id", *GROUP_KEYS],
            how="outer",
            indicator=True,
        )
        merged["score_abs_diff"] = (
            pd.to_numeric(merged["prototype_score"], errors="coerce") - pd.to_numeric(merged["phase4c_score"], errors="coerce")
        ).abs()
        merged["rank_match"] = pd.to_numeric(merged["prototype_rank"], errors="coerce").astype("Int64").eq(
            pd.to_numeric(merged["phase4c_rank"], errors="coerce").astype("Int64")
        )
        score_match = merged["score_abs_diff"].fillna(math.inf).le(EPS)
        rank_match = merged["rank_match"].fillna(False).astype(bool)
        row = {
            "branch": branch,
            "branch_name": definition["branch_name"],
            "row_count": int(len(merged)),
            "matched_rows": int(merged["_merge"].eq("both").sum()),
            "missing_in_prototype": int(merged["_merge"].eq("right_only").sum()),
            "missing_in_phase4c": int(merged["_merge"].eq("left_only").sum()),
            "score_all_equal": bool(score_match.all()),
            "rank_all_equal": bool(rank_match.all()),
            "max_score_abs_diff": float(merged["score_abs_diff"].max()),
            "rank_mismatch_count": int((~rank_match).sum()),
        }
        rows.append(row)
        bad = merged[(~score_match) | (~rank_match) | (~merged["_merge"].eq("both"))].copy()
        if not bad.empty:
            bad.insert(0, "branch", branch)
            diff_frames.append(bad)

    alignment = pd.DataFrame(rows)
    diff = pd.concat(diff_frames, ignore_index=True) if diff_frames else pd.DataFrame()

    c3_proto = ranked[ranked["c3_rank"].astype(int).eq(1)][["candidate_id", *GROUP_KEYS]].rename(
        columns={"candidate_id": "prototype_c3_rank1_candidate_id"}
    )
    c3_combined = combined[combined["c3_rank"].astype(int).eq(1)][["candidate_id", *GROUP_KEYS]].rename(
        columns={"candidate_id": "phase4c_c3_rank1_candidate_id"}
    )
    rank1 = c3_proto.merge(c3_combined, on=GROUP_KEYS, how="outer")
    rank1["candidate_id_match"] = rank1["prototype_c3_rank1_candidate_id"].astype(str).eq(
        rank1["phase4c_c3_rank1_candidate_id"].astype(str)
    )
    rank1_row = {
        "branch": "c3_rank1",
        "branch_name": "prototype_c3_vs_phase4c_c3_rank1",
        "row_count": int(len(rank1)),
        "matched_rows": int(rank1["candidate_id_match"].sum()),
        "missing_in_prototype": int(rank1["prototype_c3_rank1_candidate_id"].isna().sum()),
        "missing_in_phase4c": int(rank1["phase4c_c3_rank1_candidate_id"].isna().sum()),
        "score_all_equal": True,
        "rank_all_equal": bool(rank1["candidate_id_match"].all()),
        "max_score_abs_diff": 0.0,
        "rank_mismatch_count": int((~rank1["candidate_id_match"]).sum()),
    }
    alignment = pd.concat([alignment, pd.DataFrame([rank1_row])], ignore_index=True)
    if not rank1["candidate_id_match"].all():
        rank1_bad = rank1[~rank1["candidate_id_match"]].copy()
        rank1_bad.insert(0, "branch", "c3_rank1")
        diff = pd.concat([diff, rank1_bad], ignore_index=True)

    diff_path = prototype_dir / "evaluation_factor_graph_alignment_diff.csv"
    if not diff.empty:
        diff.to_csv(diff_path, index=False, encoding="utf-8-sig")
    return alignment, diff


def md_table(df: pd.DataFrame, max_rows: int = 30, digits: int = 4) -> str:
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


def support_methods_chapter(summary: pd.DataFrame, alignment: pd.DataFrame) -> tuple[bool, str]:
    c3 = summary[summary["branch"].eq("c3")]
    c4 = summary[summary["branch"].eq("c4_diagnostic")]
    aligned = bool(alignment["rank_mismatch_count"].sum() == 0 and alignment["missing_in_prototype"].sum() == 0 and alignment["missing_in_phase4c"].sum() == 0)
    if c3.empty:
        return False, "C3 summary is missing."
    c3_row = c3.iloc[0]
    reason = (
        f"C3 reproduces Phase4C alignment={aligned}; mean_center_error={c3_row['mean_center_error']:.4f}; "
        f"rank1_best_proxy={c3_row['rank1_is_best_proxy_rate']:.4f}; "
        f"best_proxy_top20={c3_row['best_proxy_top20_rate']:.4f}. "
    )
    if not c4.empty:
        c4_row = c4.iloc[0]
        reason += f"C4 diagnostic top20={c4_row['best_proxy_top20_rate']:.4f} remains diagnostic."
    return aligned, reason


def write_readme(prototype_dir: Path, summary: pd.DataFrame, alignment: pd.DataFrame) -> None:
    text = "# Factor Graph Prototype Evaluation\n\n"
    text += "A019/A021 were read only after prototype output existed. C3 is the primary output; C4 is diagnostic only.\n\n"
    text += "## Branch Metrics\n\n"
    text += md_table(summary[["branch", "branch_role", "mean_center_error", "mean_axis_aligned_proxy_iou", "rank1_is_best_proxy_rate", "best_proxy_top20_rate"]])
    text += "\n\n## Alignment With Phase4C\n\n"
    text += md_table(alignment)
    (prototype_dir / "evaluation_factor_graph_readme.md").write_text(text, encoding="utf-8")


def write_summary_doc(
    docs_dir: Path,
    timestamp: str,
    prototype_dir: Path,
    manifest: dict[str, Any],
    summary: pd.DataFrame,
    condition: pd.DataFrame,
    alignment: pd.DataFrame,
    support: bool,
    support_reason: str,
) -> Path:
    docs_dir.mkdir(parents=True, exist_ok=True)
    path = docs_dir / f"gm17_phase4_factor_graph_prototype_run_summary_{timestamp}.md"
    c3_condition = condition[condition["branch"].eq("c3")]
    severe = c3_condition[
        c3_condition["truncation_degree"].astype(str).str.contains("severe", case=False, na=False)
        | c3_condition["occlusion_degree"].astype(str).str.contains("severe", case=False, na=False)
    ]
    text = f"""# GM17 Phase4 Factor Graph Prototype Run Summary {timestamp}

## 1. Purpose

This run restructures the already validated Phase4C C3 temporal-guarded structure rule into explicit factor graph prototype outputs.

## 2. Why This Is A Factor Graph Prototype

The prototype separates candidate nodes, temporal factor values, SAR structure factor values, messages, and combined energy tables. It does not tune a new weight, search C6/C7, search v3 table rules, train, or calibrate.

## 3. Candidate Node Definition

Candidate nodes are the full A001 GM_RM017 candidate bank with `candidate_id`, group keys, `cx/cy/w/h/heading/r/az/cross`, and `node_status`.

- candidate nodes: {manifest.get('row_counts', {}).get('candidate_nodes')}
- target groups: {manifest.get('row_counts', {}).get('target_groups')}

## 4. Temporal Factor Definition

The temporal factor is the Phase4C recomputed optical temporal compatibility from A001 `r/cross/az` and A005 `pred_r/pred_cross/pred_az`, represented as `temporal_distance_raw` and `temporal_rank_percentile`.

## 5. SAR Structure Factor Definition

The SAR structure factor reuses structure-only S1/S2 display-image features over full A001. This remains display/pseudocolor evidence, not raw SAR physics.

## 6. C3 Combined Energy Definition

`c3_energy = 0.67 * temporal_rank_percentile + 0.33 * s1_rank_percentile`.

Lower energy is better. Tie-break is `candidate_id` ascending only.

## 7. C4 Diagnostic Branch Definition

`c4_diagnostic_energy = 0.33 * temporal_rank_percentile + 0.67 * s1_rank_percentile`.

C4 is diagnostic only and is not the main prototype conclusion.

## 8. Alignment With Phase4C

{md_table(alignment)}

## 9. Core Evaluation Results

{md_table(summary)}

## 10. Condition Failure Results

{md_table(c3_condition[['branch', 'condition_type', 'truncation_degree', 'occlusion_degree', 'n_targets', 'rank1_is_best_proxy_rate', 'best_proxy_top20_rate', 'mean_center_error', 'mean_rank_of_best_proxy']])}

## 11. Display/Pseudocolor Risk

The SAR structure factor still comes from display/pseudocolor image features. It should not be described as raw SAR physics.

## 12. A005 Legacy Soft-Prior Risk

The temporal factor still depends on the legacy A005 soft prior, although legacy A005 score and delta fields are not used.

## 13. Severe Truncated+Occluded Status

Severe truncation/occlusion remains unresolved. The relevant C3 severe condition rows are:

{md_table(severe[['branch', 'condition_type', 'truncation_degree', 'occlusion_degree', 'n_targets', 'rank1_is_best_proxy_rate', 'best_proxy_top20_rate', 'mean_center_error']])}

## 14. Support For Method Chapter / System Flow Figure

Decision: `{support}`

Reason: {support_reason}

## 15. Next Step

- If C3 fully reproduces Phase4C, move to method chapter text and prototype interface diagram.
- If alignment fails, fix alignment before making claims.
- Future-only routes remain raw SAR, rotated OBB, visibility/missing route, and independent proposal.
- Do not return to C6/C7 or v3 table tuning.

## Boundary Statement

- A019/A021 were read only after prototype output existed.
- No A019 `final_*` entered inference.
- No A021 condition/truncation/occlusion entered inference.
- No source, legacy delta, legacy score, selected output, B patch, or oracle entered inference.
- No threshold tuning, training, calibration, stage, commit, or push.
"""
    path.write_text(text, encoding="utf-8")
    return path


def write_json(
    prototype_dir: Path,
    timestamp: str,
    summary: pd.DataFrame,
    condition: pd.DataFrame,
    alignment: pd.DataFrame,
    support: bool,
    support_reason: str,
    summary_doc: Path,
) -> None:
    payload = {
        "evaluation_timestamp": timestamp,
        "prototype_dir": str(prototype_dir),
        "branches": summary.to_dict("records"),
        "condition_group_rows": condition.to_dict("records"),
        "alignment_with_phase4c": alignment.to_dict("records"),
        "support_methods_chapter_or_system_flow_figure": bool(support),
        "support_reason": support_reason,
        "summary_doc": str(summary_doc),
        "leakage_boundary_statement": "A019/A021 were read only after prototype output existed; no GT/A021/source/legacy score entered inference.",
    }
    with (prototype_dir / "evaluation_factor_graph_summary.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> None:
    args = parse_args()
    prototype_dir = Path(args.prototype_dir)
    outputs = require_prototype_outputs(prototype_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path(args.log_root) / f"gm17_phase4_factor_graph_prototype_eval_{timestamp}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    setup_logging(log_path)
    logging.info("GM17 Phase4 factor graph prototype evaluation started.")
    logging.info("Prototype output verified before reading A019/A021: %s", prototype_dir)

    nodes = key_cols_as_text(read_required(outputs["nodes"]))
    factors = key_cols_as_text(read_required(outputs["factors"]))
    energy = key_cols_as_text(read_required(outputs["energy"]))
    with outputs["manifest"].open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    ranked = build_ranked(nodes, factors, energy)
    alignment, diff = alignment_with_phase4c(prototype_dir, ranked, Path(args.combined_dir))
    alignment.to_csv(prototype_dir / "evaluation_factor_graph_alignment_with_phase4c.csv", index=False, encoding="utf-8-sig")

    logging.info("Reading A019/A021 only after prototype output exists.")
    a019 = read_required(Path(args.a019))
    a021 = read_required(Path(args.a021))

    evaluated = add_eval_geometry(ranked, a019)
    best = best_candidates(evaluated)
    conditions = condition_context(a021)
    per_target = pd.concat(
        [evaluate_branch(evaluated, best, conditions, branch) for branch in BRANCHES],
        ignore_index=True,
    )
    summary = summarize(per_target)
    condition = condition_summary(per_target)

    per_target.to_csv(prototype_dir / "evaluation_factor_graph_per_target.csv", index=False, encoding="utf-8-sig")
    condition.to_csv(prototype_dir / "evaluation_factor_graph_condition_groups.csv", index=False, encoding="utf-8-sig")
    support, support_reason = support_methods_chapter(summary, alignment)
    write_readme(prototype_dir, summary, alignment)
    summary_doc = write_summary_doc(Path(args.docs_dir), timestamp, prototype_dir, manifest, summary, condition, alignment, support, support_reason)
    write_json(prototype_dir, timestamp, summary, condition, alignment, support, support_reason, summary_doc)

    if not diff.empty:
        logging.warning("Phase4C alignment has differences; main conclusion should be blocked until fixed.")
    logging.info("Summary doc: %s", summary_doc)
    logging.info("Support method chapter/system flow figure: %s", support)
    print(summary_doc)


if __name__ == "__main__":
    main()
