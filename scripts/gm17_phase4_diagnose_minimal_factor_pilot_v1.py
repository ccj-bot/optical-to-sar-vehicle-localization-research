from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_PILOT_DIR = WORKSPACE / "output" / "gm17_phase4_minimal_factor_pilot_20260628_110447"
DEFAULT_A001 = WORKSPACE / "output" / "clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2" / "candidate_bank_inference.csv"
DEFAULT_OUTPUT_ROOT = WORKSPACE / "output"
DEFAULT_LOG_ROOT = WORKSPACE / "logs"
DEFAULT_DOCS_ROOT = WORKSPACE / "docs"

GROUP_KEYS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
EVAL_CONDITION_FIELDS = ["condition_type", "condition_status", "truncation_degree", "occlusion_degree"]
PROVENANCE_FIELDS = [
    "candidate_id",
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
    "candidate_source",
    "candidate_detail",
    "candidate_expansion_state",
    "candidate_expansion_reason",
    "gm17_anchor_strength",
]
ROLE_GEOMETRY_FIELDS = ["w", "h", "heading", "r", "cross", "az", "temporal_distance"]
PLOT_DPI = 140


class RunLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, message: str) -> None:
        line = f"[{datetime.now().isoformat(timespec='seconds')}] {message}"
        print(line)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def pct(value: float | None) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "n/a"
    return f"{100.0 * value:.1f}%"


def finite_float(value) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if not math.isfinite(out):
        return None
    return out


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    den = den.replace(0, np.nan)
    return num / den


def compact_counts(series: pd.Series, limit: int = 8) -> str:
    if series.empty:
        return ""
    counts = series.fillna("<missing>").astype(str).value_counts().head(limit)
    return "; ".join(f"{k}:{int(v)}" for k, v in counts.items())


def load_required_outputs(pilot_dir: Path) -> dict[str, Path]:
    paths = {
        "ranked": pilot_dir / "pilot_candidates_ranked.csv",
        "selected": pilot_dir / "pilot_selected_rank1.csv",
        "manifest": pilot_dir / "pilot_manifest.json",
        "evaluation_summary": pilot_dir / "evaluation_summary.json",
        "evaluation_per_target": pilot_dir / "evaluation_per_target.csv",
        "evaluation_condition_groups": pilot_dir / "evaluation_condition_groups.csv",
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required v1 output files: {missing}")
    return paths


def merge_provenance(ranked: pd.DataFrame, a001_path: Path, logger: RunLogger) -> tuple[pd.DataFrame, dict]:
    header = list(pd.read_csv(a001_path, nrows=0).columns)
    available = [field for field in PROVENANCE_FIELDS if field in header]
    missing = [field for field in PROVENANCE_FIELDS if field not in header]
    provenance_status = {
        "a001_path": str(a001_path),
        "requested_fields": PROVENANCE_FIELDS,
        "available_fields": available,
        "missing_fields": missing,
        "used_only_for_diagnostics": True,
    }
    if len(available) < len(GROUP_KEYS) + 1:
        logger.write("A001 provenance merge skipped because required identity fields are unavailable.")
        for field in PROVENANCE_FIELDS:
            if field not in ranked.columns and field not in GROUP_KEYS + ["candidate_id"]:
                ranked[field] = pd.NA
        return ranked, provenance_status

    diag = pd.read_csv(a001_path, usecols=available)
    merge_keys = [field for field in ["candidate_id"] + GROUP_KEYS if field in available]
    extra_fields = [field for field in available if field not in merge_keys]
    duplicate_count = int(diag.duplicated(merge_keys, keep=False).sum()) if merge_keys else 0
    if duplicate_count:
        logger.write(f"A001 provenance has {duplicate_count} duplicate rows on {merge_keys}; keeping first for diagnostics.")
    diag = diag.drop_duplicates(merge_keys, keep="first")
    merged = ranked.merge(diag[merge_keys + extra_fields], on=merge_keys, how="left", validate="many_to_one")
    for field in PROVENANCE_FIELDS:
        if field not in merged.columns and field not in GROUP_KEYS + ["candidate_id"]:
            merged[field] = pd.NA
    provenance_status["duplicate_rows_on_merge_keys"] = duplicate_count
    provenance_status["merged_rows"] = int(len(merged))
    logger.write(f"Merged A001 provenance fields for diagnostics only: {extra_fields}")
    return merged, provenance_status


def attach_role_columns(base: pd.DataFrame, ranked_diag: pd.DataFrame, role: str, id_col: str) -> pd.DataFrame:
    candidate_cols = [
        "candidate_id",
        *GROUP_KEYS,
        "pilot_rank",
        "cx",
        "cy",
        "w",
        "h",
        "heading",
        "r",
        "cross",
        "az",
        "temporal_distance",
        "candidate_source",
        "candidate_detail",
        "candidate_expansion_state",
        "candidate_expansion_reason",
        "gm17_anchor_strength",
    ]
    candidate_cols = [col for col in candidate_cols if col in ranked_diag.columns]
    if f"{role}_pilot_rank" in base.columns and "pilot_rank" in candidate_cols:
        candidate_cols.remove("pilot_rank")
    role_table = ranked_diag[candidate_cols].drop_duplicates(["candidate_id", *GROUP_KEYS], keep="first").copy()
    rename_map = {col: f"{role}_{col}" for col in candidate_cols if col not in GROUP_KEYS}
    role_table = role_table.rename(columns=rename_map)
    return base.merge(
        role_table,
        left_on=[*GROUP_KEYS, id_col],
        right_on=[*GROUP_KEYS, f"{role}_candidate_id"],
        how="left",
        validate="one_to_one",
    )


def add_role_derived(df: pd.DataFrame, role: str) -> pd.DataFrame:
    w = pd.to_numeric(df.get(f"{role}_w"), errors="coerce")
    h = pd.to_numeric(df.get(f"{role}_h"), errors="coerce")
    df[f"{role}_aspect"] = safe_ratio(w, h)
    df[f"{role}_area"] = w * h
    return df


def prepare_per_target(ranked_diag: pd.DataFrame, eval_per_target: pd.DataFrame) -> pd.DataFrame:
    base = eval_per_target.copy()
    base["rank1_candidate_id"] = base["candidate_id"]
    base["rank1_center_error"] = base["center_error"]
    base["rank1_proxy_iou"] = base["axis_aligned_proxy_iou"]

    base = attach_role_columns(base, ranked_diag, "rank1", "rank1_candidate_id")
    base = attach_role_columns(base, ranked_diag, "best_proxy", "best_proxy_candidate_id")
    base = attach_role_columns(base, ranked_diag, "best_center", "best_center_candidate_id")
    for role in ["rank1", "best_proxy", "best_center"]:
        base = add_role_derived(base, role)

    zero = ranked_diag.loc[pd.to_numeric(ranked_diag["temporal_distance"], errors="coerce").abs() <= 1e-12].copy()
    zero_counts = (
        zero.groupby(GROUP_KEYS, dropna=False)
        .agg(
            temporal_zero_candidate_count=("candidate_id", "count"),
            temporal_zero_candidate_sources=("candidate_source", compact_counts),
        )
        .reset_index()
    )
    base = base.merge(zero_counts, on=GROUP_KEYS, how="left")
    base["temporal_zero_candidate_count"] = base["temporal_zero_candidate_count"].fillna(0).astype(int)
    base["temporal_zero_candidate_sources"] = base["temporal_zero_candidate_sources"].fillna("")

    base["best_proxy_in_top5"] = pd.to_numeric(base["best_proxy_pilot_rank"], errors="coerce") <= 5
    base["best_proxy_in_top20"] = pd.to_numeric(base["best_proxy_pilot_rank"], errors="coerce") <= 20
    base["best_center_in_top5"] = pd.to_numeric(base["best_center_pilot_rank"], errors="coerce") <= 5
    base["best_center_in_top20"] = pd.to_numeric(base["best_center_pilot_rank"], errors="coerce") <= 20
    base["rank1_is_best_proxy"] = base["rank1_candidate_id"] == base["best_proxy_candidate_id"]
    base["rank1_is_best_center"] = base["rank1_candidate_id"] == base["best_center_candidate_id"]
    base["delta_rank1_minus_best_proxy_iou"] = base["rank1_proxy_iou"] - base["best_proxy_iou"]
    base["delta_rank1_minus_best_center_error"] = base["rank1_center_error"] - base["best_center_error"]
    base["temporal_zero_bad_case"] = (
        (pd.to_numeric(base["rank1_temporal_distance"], errors="coerce").abs() <= 1e-12)
        & ((base["rank1_center_error"] > 50.0) | (base["rank1_proxy_iou"] < 0.25))
    )
    return base


def build_role_long(per_target: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for role in ["rank1", "best_proxy", "best_center"]:
        if role == "rank1":
            metric_center = "rank1_center_error"
            metric_iou = "rank1_proxy_iou"
        elif role == "best_proxy":
            metric_center = "best_proxy_center_error"
            metric_iou = "best_proxy_iou"
        else:
            metric_center = "best_center_error"
            metric_iou = "best_center_proxy_iou"

        cols = [*GROUP_KEYS, *EVAL_CONDITION_FIELDS]
        part = per_target[cols].copy()
        part["role"] = role
        part["candidate_id"] = per_target[f"{role}_candidate_id"]
        part["pilot_rank"] = per_target[f"{role}_pilot_rank"]
        part["center_error"] = per_target[metric_center]
        part["axis_aligned_proxy_iou"] = per_target[metric_iou]
        for field in ["cx", "cy", "w", "h", "aspect", "area", "heading", "r", "cross", "az", "temporal_distance"]:
            col = f"{role}_{field}"
            part[field] = per_target[col] if col in per_target.columns else pd.NA
        for field in ["candidate_source", "candidate_detail", "candidate_expansion_state", "candidate_expansion_reason", "gm17_anchor_strength"]:
            col = f"{role}_{field}"
            part[field] = per_target[col] if col in per_target.columns else pd.NA
        rows.append(part)
    return pd.concat(rows, ignore_index=True)


def rank_distribution(per_target: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for role, col in [("best_proxy", "best_proxy_pilot_rank"), ("best_center", "best_center_pilot_rank")]:
        ranks = pd.to_numeric(per_target[col], errors="coerce").dropna()
        summary = {
            "row_type": "summary",
            "role": role,
            "rank": pd.NA,
            "n_targets": int(len(ranks)),
            "cumulative_rate": pd.NA,
            "mean_rank": float(ranks.mean()) if len(ranks) else np.nan,
            "median_rank": float(ranks.median()) if len(ranks) else np.nan,
            "p75_rank": float(ranks.quantile(0.75)) if len(ranks) else np.nan,
            "p90_rank": float(ranks.quantile(0.90)) if len(ranks) else np.nan,
            "max_rank": float(ranks.max()) if len(ranks) else np.nan,
        }
        for k in [1, 3, 5, 10, 20]:
            summary[f"top{k}_rate"] = float((ranks <= k).mean()) if len(ranks) else np.nan
        rows.append(summary)
        counts = ranks.astype(int).value_counts().sort_index()
        total = len(ranks)
        cumulative = 0
        for rank, count in counts.items():
            cumulative += int(count)
            rows.append(
                {
                    "row_type": "histogram",
                    "role": role,
                    "rank": int(rank),
                    "n_targets": int(count),
                    "cumulative_rate": cumulative / total if total else np.nan,
                    "mean_rank": pd.NA,
                    "median_rank": pd.NA,
                    "p75_rank": pd.NA,
                    "p90_rank": pd.NA,
                    "max_rank": pd.NA,
                    "top1_rate": pd.NA,
                    "top3_rate": pd.NA,
                    "top5_rate": pd.NA,
                    "top10_rate": pd.NA,
                    "top20_rate": pd.NA,
                }
            )
    return pd.DataFrame(rows)


def angle_abs_diff(a: pd.Series, b: pd.Series, period: float = 360.0) -> pd.Series:
    diff = (pd.to_numeric(a, errors="coerce") - pd.to_numeric(b, errors="coerce")).abs()
    return np.minimum(diff % period, period - (diff % period))


def build_gap_rows(per_target: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for comparison, role in [("rank1_vs_best_proxy", "best_proxy"), ("rank1_vs_best_center", "best_center")]:
        rows.append(
            pd.DataFrame(
                {
                    **{field: per_target[field] for field in EVAL_CONDITION_FIELDS},
                    "comparison": comparison,
                    "delta_center_error": per_target["rank1_center_error"]
                    - (per_target["best_proxy_center_error"] if role == "best_proxy" else per_target["best_center_error"]),
                    "delta_proxy_iou": per_target["rank1_proxy_iou"]
                    - (per_target["best_proxy_iou"] if role == "best_proxy" else per_target["best_center_proxy_iou"]),
                    "abs_w_diff": (per_target["rank1_w"] - per_target[f"{role}_w"]).abs(),
                    "abs_h_diff": (per_target["rank1_h"] - per_target[f"{role}_h"]).abs(),
                    "abs_aspect_diff": (per_target["rank1_aspect"] - per_target[f"{role}_aspect"]).abs(),
                    "abs_area_diff": (per_target["rank1_area"] - per_target[f"{role}_area"]).abs(),
                    "abs_heading_diff": angle_abs_diff(per_target["rank1_heading"], per_target[f"{role}_heading"]),
                    "abs_r_diff": (per_target["rank1_r"] - per_target[f"{role}_r"]).abs(),
                    "abs_cross_diff": (per_target["rank1_cross"] - per_target[f"{role}_cross"]).abs(),
                    "abs_az_diff": angle_abs_diff(per_target["rank1_az"], per_target[f"{role}_az"]),
                    "delta_temporal_distance": per_target["rank1_temporal_distance"] - per_target[f"{role}_temporal_distance"],
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def summarize_gaps(gap_rows: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "delta_center_error",
        "delta_proxy_iou",
        "abs_w_diff",
        "abs_h_diff",
        "abs_aspect_diff",
        "abs_area_diff",
        "abs_heading_diff",
        "abs_r_diff",
        "abs_cross_diff",
        "abs_az_diff",
        "delta_temporal_distance",
    ]

    def aggregate(df: pd.DataFrame, scope: str, group_values: dict | None = None) -> dict:
        row = {"scope": scope}
        if group_values:
            row.update(group_values)
        else:
            for field in EVAL_CONDITION_FIELDS:
                row[field] = "ALL"
        row["comparison"] = df["comparison"].iloc[0] if len(df) else ""
        row["n_targets"] = int(len(df))
        for metric in metrics:
            row[f"mean_{metric}"] = float(df[metric].mean()) if len(df) else np.nan
            row[f"median_{metric}"] = float(df[metric].median()) if len(df) else np.nan
        return row

    rows = []
    for comparison, comp_df in gap_rows.groupby("comparison", dropna=False):
        rows.append(aggregate(comp_df, "overall"))
        for keys, group in comp_df.groupby(EVAL_CONDITION_FIELDS, dropna=False):
            group_values = dict(zip(EVAL_CONDITION_FIELDS, keys))
            rows.append(aggregate(group, "condition_group", group_values))
    return pd.DataFrame(rows)


def temporal_zero_artifact(per_target: pd.DataFrame) -> pd.DataFrame:
    out = per_target[
        [
            *GROUP_KEYS,
            *EVAL_CONDITION_FIELDS,
            "rank1_candidate_id",
            "best_proxy_candidate_id",
            "best_center_candidate_id",
            "temporal_zero_candidate_count",
            "temporal_zero_candidate_sources",
            "rank1_temporal_distance",
            "best_proxy_temporal_distance",
            "best_center_temporal_distance",
            "rank1_center_error",
            "rank1_proxy_iou",
            "best_proxy_iou",
            "best_proxy_center_error",
            "best_center_error",
            "best_center_proxy_iou",
            "rank1_w",
            "rank1_h",
            "rank1_aspect",
            "rank1_area",
            "best_proxy_w",
            "best_proxy_h",
            "best_proxy_aspect",
            "best_proxy_area",
            "rank1_r",
            "rank1_cross",
            "rank1_az",
            "best_proxy_r",
            "best_proxy_cross",
            "best_proxy_az",
            "rank1_candidate_source",
            "best_proxy_candidate_source",
            "best_center_candidate_source",
            "temporal_zero_bad_case",
        ]
    ].copy()
    out["rank1_is_temporal_zero"] = pd.to_numeric(out["rank1_temporal_distance"], errors="coerce").abs() <= 1e-12
    out["best_proxy_is_temporal_zero"] = pd.to_numeric(out["best_proxy_temporal_distance"], errors="coerce").abs() <= 1e-12
    out["best_center_is_temporal_zero"] = pd.to_numeric(out["best_center_temporal_distance"], errors="coerce").abs() <= 1e-12
    out["temporal_zero_equals_best_proxy"] = out["rank1_candidate_id"] == out["best_proxy_candidate_id"]
    out["temporal_zero_equals_best_center"] = out["rank1_candidate_id"] == out["best_center_candidate_id"]
    out["rank1_best_proxy_abs_w_diff"] = (out["rank1_w"] - out["best_proxy_w"]).abs()
    out["rank1_best_proxy_abs_h_diff"] = (out["rank1_h"] - out["best_proxy_h"]).abs()
    out["rank1_best_proxy_abs_aspect_diff"] = (out["rank1_aspect"] - out["best_proxy_aspect"]).abs()
    out["rank1_best_proxy_abs_area_diff"] = (out["rank1_area"] - out["best_proxy_area"]).abs()
    out["rank1_best_proxy_abs_r_diff"] = (out["rank1_r"] - out["best_proxy_r"]).abs()
    out["rank1_best_proxy_abs_cross_diff"] = (out["rank1_cross"] - out["best_proxy_cross"]).abs()
    out["rank1_best_proxy_abs_az_diff"] = angle_abs_diff(out["rank1_az"], out["best_proxy_az"])
    return out


def failure_groups(per_target: pd.DataFrame) -> pd.DataFrame:
    return (
        per_target.groupby(EVAL_CONDITION_FIELDS, dropna=False)
        .agg(
            n_targets=("rank1_candidate_id", "count"),
            mean_rank1_center_error=("rank1_center_error", "mean"),
            mean_rank1_proxy_iou=("rank1_proxy_iou", "mean"),
            rank1_recall_proxy0_25=("rank1_proxy_iou", lambda s: float((s >= 0.25).mean())),
            best_proxy_coverage_proxy0_25=("best_proxy_iou", lambda s: float((s >= 0.25).mean())),
            mean_best_proxy_pilot_rank=("best_proxy_pilot_rank", "mean"),
            rank1_is_best_proxy_rate=("rank1_is_best_proxy", "mean"),
            temporal_zero_bad_case_rate=("temporal_zero_bad_case", "mean"),
            best_proxy_top5_rate=("best_proxy_in_top5", "mean"),
            best_proxy_top20_rate=("best_proxy_in_top20", "mean"),
            best_center_top5_rate=("best_center_in_top5", "mean"),
            best_center_top20_rate=("best_center_in_top20", "mean"),
        )
        .reset_index()
        .sort_values(["temporal_zero_bad_case_rate", "mean_rank1_center_error"], ascending=[False, False])
    )


def v2_hypotheses(per_target: pd.DataFrame, gap_summary: pd.DataFrame, temporal_zero: pd.DataFrame) -> pd.DataFrame:
    overall_proxy = gap_summary[
        (gap_summary["scope"] == "overall") & (gap_summary["comparison"] == "rank1_vs_best_proxy")
    ].iloc[0]
    bad = temporal_zero[temporal_zero["temporal_zero_bad_case"]].copy()
    rows = [
        {
            "hypothesis": "size_aspect_fixed_prior",
            "diagnostic_evidence": f"Mean rank1-vs-best_proxy aspect gap={overall_proxy['mean_abs_aspect_diff']:.4f}; w gap={overall_proxy['mean_abs_w_diff']:.2f}; h gap={overall_proxy['mean_abs_h_diff']:.2f}.",
            "candidate_direction": "Audit whether fixed vehicle-size/aspect plausibility can separate temporal-zero base candidates from better covered candidates.",
            "risk": "Must not fit thresholds from GT; use predeclared physical prior only.",
            "not_a_rule": True,
        },
        {
            "hypothesis": "area_fixed_prior",
            "diagnostic_evidence": f"Mean rank1-vs-best_proxy area gap={overall_proxy['mean_abs_area_diff']:.2f}.",
            "candidate_direction": "Check whether area consistency can reject implausible base candidates before temporal distance dominates.",
            "risk": "Area alone can over-penalize truncation and missing extent.",
            "not_a_rule": True,
        },
        {
            "hypothesis": "heading_consistency",
            "diagnostic_evidence": f"Mean rank1-vs-best_proxy heading gap={overall_proxy['mean_abs_heading_diff']:.2f}.",
            "candidate_direction": "Inspect whether heading is stable enough for a fixed prior or should remain diagnostic only.",
            "risk": "OBB heading convention may be unstable; do not promote without convention audit.",
            "not_a_rule": True,
        },
        {
            "hypothesis": "range_cross_az_residual_structure",
            "diagnostic_evidence": f"Mean gaps r={overall_proxy['mean_abs_r_diff']:.2f}, cross={overall_proxy['mean_abs_cross_diff']:.2f}, az={overall_proxy['mean_abs_az_diff']:.2f}.",
            "candidate_direction": "Compare temporal-zero candidates against best candidates to see if SAR-side local residual structure can help.",
            "risk": "r/cross/az are shared with temporal comparison; avoid double-counting.",
            "not_a_rule": True,
        },
        {
            "hypothesis": "temporal_zero_legacy_artifact",
            "diagnostic_evidence": f"Temporal-zero bad cases={int(bad.shape[0])}; rank1 temporal-zero rate={float((temporal_zero['rank1_is_temporal_zero']).mean()):.4f}.",
            "candidate_direction": "Separate base-candidate artifact from true optical-temporal consistency in v2 design.",
            "risk": "Do not use temporal_factor_score or legacy delta fields to shortcut this separation.",
            "not_a_rule": True,
        },
        {
            "hypothesis": "source_provenance_diagnostic_only",
            "diagnostic_evidence": "Source/provenance fields were merged only after ranking for explanation.",
            "candidate_direction": "Use source/provenance to identify legacy artifact patterns, not as active scoring evidence.",
            "risk": "candidate_source can encode historical selected behavior or generation path; do not sort with it.",
            "not_a_rule": True,
        },
    ]
    return pd.DataFrame(rows)


def plot_hist(series: pd.Series, title: str, xlabel: str, path: Path) -> None:
    plt.figure(figsize=(7, 4))
    plt.hist(pd.to_numeric(series, errors="coerce").dropna(), bins=30, color="#4C78A8", edgecolor="white")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(path, dpi=PLOT_DPI)
    plt.close()


def plot_scatter(x: pd.Series, y: pd.Series, title: str, xlabel: str, ylabel: str, path: Path) -> None:
    plt.figure(figsize=(5, 5))
    plt.scatter(x, y, s=18, alpha=0.7, color="#F58518")
    valid = pd.concat([x, y], axis=1).dropna()
    if not valid.empty:
        lo = float(valid.min().min())
        hi = float(valid.max().max())
        plt.plot([lo, hi], [lo, hi], color="#555555", linewidth=1)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(path, dpi=PLOT_DPI)
    plt.close()


def condition_label(df: pd.DataFrame) -> pd.Series:
    return (
        df["condition_type"].fillna("NA").astype(str)
        + " / "
        + df["truncation_degree"].fillna("NA").astype(str)
        + " / "
        + df["occlusion_degree"].fillna("NA").astype(str)
    )


def plot_condition_bar(df: pd.DataFrame, value_col: str, title: str, ylabel: str, path: Path, top_n: int = 12) -> None:
    tmp = df.copy()
    tmp["label"] = condition_label(tmp)
    tmp = tmp.sort_values(value_col, ascending=False).head(top_n)
    plt.figure(figsize=(9, 4.8))
    plt.bar(tmp["label"], tmp[value_col], color="#54A24B")
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=PLOT_DPI)
    plt.close()


def write_plots(per_target: pd.DataFrame, failure_df: pd.DataFrame, figures_dir: Path) -> dict[str, str]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "best_proxy_rank_hist": figures_dir / "best_proxy_rank_hist.png",
        "best_center_rank_hist": figures_dir / "best_center_rank_hist.png",
        "rank1_vs_best_proxy_iou_scatter": figures_dir / "rank1_vs_best_proxy_iou_scatter.png",
        "rank1_center_error_by_condition": figures_dir / "rank1_center_error_by_condition.png",
        "best_proxy_rank_by_condition": figures_dir / "best_proxy_rank_by_condition.png",
        "temporal_zero_bad_cases_bar": figures_dir / "temporal_zero_bad_cases_bar.png",
    }
    plot_hist(per_target["best_proxy_pilot_rank"], "Best Proxy Candidate Rank", "pilot rank", paths["best_proxy_rank_hist"])
    plot_hist(per_target["best_center_pilot_rank"], "Best Center Candidate Rank", "pilot rank", paths["best_center_rank_hist"])
    plot_scatter(
        per_target["rank1_proxy_iou"],
        per_target["best_proxy_iou"],
        "Rank1 vs Best Proxy IoU",
        "rank1 proxy IoU",
        "best proxy IoU",
        paths["rank1_vs_best_proxy_iou_scatter"],
    )
    plot_condition_bar(
        failure_df,
        "mean_rank1_center_error",
        "Rank1 Center Error by Condition",
        "mean center error",
        paths["rank1_center_error_by_condition"],
    )
    plot_condition_bar(
        failure_df,
        "mean_best_proxy_pilot_rank",
        "Best Proxy Rank by Condition",
        "mean best-proxy pilot rank",
        paths["best_proxy_rank_by_condition"],
    )
    plot_condition_bar(
        failure_df,
        "temporal_zero_bad_case_rate",
        "Temporal-Zero Bad Case Rate by Condition",
        "bad case rate",
        paths["temporal_zero_bad_cases_bar"],
    )
    return {name: str(path) for name, path in paths.items()}


def json_sanitize(obj):
    if isinstance(obj, dict):
        return {str(k): json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_sanitize(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if not math.isfinite(float(obj)) else float(obj)
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    if pd.isna(obj):
        return None
    return obj


def source_summary(per_target: pd.DataFrame, temporal_zero: pd.DataFrame) -> dict:
    return {
        "rank1_candidate_source_distribution": per_target["rank1_candidate_source"].fillna("<missing>").astype(str).value_counts().head(10).to_dict(),
        "best_proxy_candidate_source_distribution": per_target["best_proxy_candidate_source"].fillna("<missing>").astype(str).value_counts().head(10).to_dict(),
        "best_center_candidate_source_distribution": per_target["best_center_candidate_source"].fillna("<missing>").astype(str).value_counts().head(10).to_dict(),
        "temporal_zero_candidate_source_distribution_compact_top": compact_counts(
            temporal_zero["temporal_zero_candidate_sources"].str.split("; ").explode().dropna(),
            limit=12,
        ),
        "used_only_for_diagnostics": True,
    }


def build_summary(
    args: argparse.Namespace,
    output_dir: Path,
    doc_path: Path,
    paths: dict[str, Path],
    output_paths: dict[str, Path],
    manifest: dict,
    eval_summary: dict,
    per_target: pd.DataFrame,
    rank_dist: pd.DataFrame,
    failure_df: pd.DataFrame,
    temporal_zero: pd.DataFrame,
    gap_summary: pd.DataFrame,
    hypotheses: pd.DataFrame,
    provenance_status: dict,
    figure_paths: dict[str, str],
) -> dict:
    proxy_summary = rank_dist[(rank_dist["row_type"] == "summary") & (rank_dist["role"] == "best_proxy")].iloc[0]
    center_summary = rank_dist[(rank_dist["row_type"] == "summary") & (rank_dist["role"] == "best_center")].iloc[0]
    worst_groups = failure_df.head(5).to_dict(orient="records")
    strongest_gap = (
        gap_summary[(gap_summary["scope"] == "overall") & (gap_summary["comparison"] == "rank1_vs_best_proxy")]
        .iloc[0]
        .to_dict()
    )
    temporal_zero_bad = temporal_zero[temporal_zero["temporal_zero_bad_case"]]
    summary = {
        "run_type": "GM_RM017-only minimal factor pilot v1 diagnostic analysis",
        "timestamp": output_dir.name.replace("gm17_phase4_minimal_factor_pilot_v1_diagnostics_", ""),
        "inputs": {
            "pilot_dir": str(Path(args.pilot_dir)),
            "a001": str(Path(args.a001)),
            **{name: str(path) for name, path in paths.items()},
        },
        "outputs": {name: str(path) for name, path in output_paths.items()},
        "markdown_summary": str(doc_path),
        "target_count": int(len(per_target)),
        "candidate_count": int(pd.read_csv(paths["ranked"], usecols=["candidate_id"]).shape[0]),
        "rank_distribution_summary": {
            "best_proxy": proxy_summary.to_dict(),
            "best_center": center_summary.to_dict(),
        },
        "rank1_is_best_proxy_rate": float(per_target["rank1_is_best_proxy"].mean()),
        "rank1_is_best_center_rate": float(per_target["rank1_is_best_center"].mean()),
        "best_proxy_top5_rate": float(per_target["best_proxy_in_top5"].mean()),
        "best_proxy_top20_rate": float(per_target["best_proxy_in_top20"].mean()),
        "best_center_top5_rate": float(per_target["best_center_in_top5"].mean()),
        "best_center_top20_rate": float(per_target["best_center_in_top20"].mean()),
        "temporal_zero_artifact_summary": {
            "rank1_temporal_zero_rate": float((pd.to_numeric(per_target["rank1_temporal_distance"], errors="coerce").abs() <= 1e-12).mean()),
            "mean_temporal_zero_candidates_per_target": float(per_target["temporal_zero_candidate_count"].mean()),
            "median_temporal_zero_candidates_per_target": float(per_target["temporal_zero_candidate_count"].median()),
            "max_temporal_zero_candidates_per_target": int(per_target["temporal_zero_candidate_count"].max()),
            "temporal_zero_bad_case_count": int(len(temporal_zero_bad)),
            "temporal_zero_bad_case_rate": float(temporal_zero["temporal_zero_bad_case"].mean()),
            "rank1_temporal_zero_equals_best_proxy_rate": float(temporal_zero["temporal_zero_equals_best_proxy"].mean()),
            "rank1_temporal_zero_equals_best_center_rate": float(temporal_zero["temporal_zero_equals_best_center"].mean()),
        },
        "failure_grouping_highlights": worst_groups,
        "geometry_gap_overall_rank1_vs_best_proxy": strongest_gap,
        "v2_hypotheses": hypotheses.to_dict(orient="records"),
        "source_provenance_summary": source_summary(per_target, temporal_zero),
        "provenance_merge_status": provenance_status,
        "figure_paths": figure_paths,
        "leakage_statement": {
            "post_inference_diagnostic_only": True,
            "v1_selection_not_rerun": True,
            "v2_ranking_not_generated": True,
            "thresholds_not_tuned": True,
            "weights_not_trained": True,
            "calibration_not_run": True,
            "source_provenance_used_only_for_diagnostics": True,
            "evaluation_not_fed_back_to_v1_rules": True,
            "a021_condition_not_promoted_to_active_factor": True,
        },
        "source_eval_summary": {
            "selected_rank1_summary": eval_summary.get("selected_rank1_summary", {}),
            "best_candidate_coverage": eval_summary.get("best_candidate_coverage", {}),
            "selection_manifest_join_summary": eval_summary.get("selection_manifest_join_summary", manifest.get("join_summary", {})),
        },
    }
    return json_sanitize(summary)


def write_markdown_summary(
    doc_path: Path,
    output_dir: Path,
    summary: dict,
    failure_df: pd.DataFrame,
    gap_summary: pd.DataFrame,
    hypotheses: pd.DataFrame,
) -> None:
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    proxy_summary = summary["rank_distribution_summary"]["best_proxy"]
    center_summary = summary["rank_distribution_summary"]["best_center"]
    temporal = summary["temporal_zero_artifact_summary"]
    source = summary["source_provenance_summary"]
    gap = summary["geometry_gap_overall_rank1_vs_best_proxy"]
    worst = failure_df.head(6)

    lines = [
        f"# GM17 Phase4 Minimal Factor Pilot V1 Diagnostic Summary {summary['timestamp']}",
        "",
        "## 1. Diagnostic Purpose",
        "",
        "This run diagnoses the completed GM_RM017-only minimal factor pilot v1. It asks why A001 contains good candidates while the v1 rank1 rule often does not select the best-proxy or best-center candidate.",
        "",
        "## 2. Inputs Used",
        "",
        f"- Pilot directory: `{summary['inputs']['pilot_dir']}`",
        f"- A001 provenance source: `{summary['inputs']['a001']}`",
        "- V1 outputs: `pilot_candidates_ranked.csv`, `pilot_selected_rank1.csv`, `pilot_manifest.json`, `evaluation_summary.json`, `evaluation_per_target.csv`, `evaluation_condition_groups.csv`",
        "",
        "## 3. Output Directory",
        "",
        f"`{output_dir}`",
        "",
        "## 4. Boundary Statement",
        "",
        "This is post-inference diagnostic analysis only. It does not rerun v1 selection, does not create v2 ranking, does not tune thresholds, does not train weights, and does not promote A021 condition labels into inference.",
        "",
        "A001 `candidate_source` / provenance fields were read only after ranking for diagnostic explanation. They were not used for sorting, scoring, or v2 rule generation.",
        "",
        "## 5. Rank1 vs Best Candidate Findings",
        "",
        f"- Targets: {summary['target_count']}",
        f"- Candidates: {summary['candidate_count']}",
        f"- `rank1_is_best_proxy` rate: {pct(summary['rank1_is_best_proxy_rate'])}",
        f"- `rank1_is_best_center` rate: {pct(summary['rank1_is_best_center_rate'])}",
        f"- Best-proxy in top5 / top20: {pct(summary['best_proxy_top5_rate'])} / {pct(summary['best_proxy_top20_rate'])}",
        f"- Best-center in top5 / top20: {pct(summary['best_center_top5_rate'])} / {pct(summary['best_center_top20_rate'])}",
        "",
        "## 6. Best Candidate Rank Distribution",
        "",
        f"- Best-proxy mean / median / p90 rank: {proxy_summary['mean_rank']:.2f} / {proxy_summary['median_rank']:.2f} / {proxy_summary['p90_rank']:.2f}",
        f"- Best-center mean / median / p90 rank: {center_summary['mean_rank']:.2f} / {center_summary['median_rank']:.2f} / {center_summary['p90_rank']:.2f}",
        "",
        "The best candidate is usually present in A001 but often appears tens of ranks below the v1 temporal-first rank1 choice.",
        "",
        "## 7. Temporal-Zero Artifact Diagnostic",
        "",
        f"- Rank1 temporal-zero rate: {pct(temporal['rank1_temporal_zero_rate'])}",
        f"- Mean / median / max temporal-zero candidates per target: {temporal['mean_temporal_zero_candidates_per_target']:.2f} / {temporal['median_temporal_zero_candidates_per_target']:.2f} / {temporal['max_temporal_zero_candidates_per_target']}",
        f"- Temporal-zero bad cases: {temporal['temporal_zero_bad_case_count']} ({pct(temporal['temporal_zero_bad_case_rate'])})",
        f"- Rank1 temporal-zero equals best-proxy / best-center: {pct(temporal['rank1_temporal_zero_equals_best_proxy_rate'])} / {pct(temporal['rank1_temporal_zero_equals_best_center_rate'])}",
        "",
        "This supports the diagnosis that the v1 temporal component is strongly affected by an A005-aligned legacy base-candidate artifact.",
        "",
        "## 8. Geometry Difference Diagnostic",
        "",
        f"- Mean rank1-vs-best_proxy center-error gap: {gap['mean_delta_center_error']:.2f}",
        f"- Mean rank1-vs-best_proxy proxy-IoU gap: {gap['mean_delta_proxy_iou']:.4f}",
        f"- Mean absolute width / height / aspect / area gaps: {gap['mean_abs_w_diff']:.2f} / {gap['mean_abs_h_diff']:.2f} / {gap['mean_abs_aspect_diff']:.4f} / {gap['mean_abs_area_diff']:.2f}",
        f"- Mean absolute heading / r / cross / az gaps: {gap['mean_abs_heading_diff']:.2f} / {gap['mean_abs_r_diff']:.2f} / {gap['mean_abs_cross_diff']:.2f} / {gap['mean_abs_az_diff']:.2f}",
        "",
        "The most actionable geometry directions are fixed size/aspect/area plausibility and careful residual analysis in r/cross/az. These are diagnostic directions, not tuned rules.",
        "",
        "## 9. Failure Grouping Diagnostic",
        "",
        "Worst groups by temporal-zero bad-case rate and center error:",
        "",
        "| condition | n | mean rank1 center error | mean rank1 proxy IoU | rank1 best-proxy rate | top20 best-proxy | bad-case rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in worst.iterrows():
        label = f"{row['condition_type']} / {row['truncation_degree']} / {row['occlusion_degree']}"
        lines.append(
            f"| {label} | {int(row['n_targets'])} | {row['mean_rank1_center_error']:.2f} | {row['mean_rank1_proxy_iou']:.4f} | {pct(row['rank1_is_best_proxy_rate'])} | {pct(row['best_proxy_top20_rate'])} | {pct(row['temporal_zero_bad_case_rate'])} |"
        )
    lines.extend(
        [
            "",
            "Failure remains concentrated in truncated+occluded groups, especially mild/moderate/severe combinations where rank1 temporal-zero candidates miss better candidates deeper in A001.",
            "",
            "## 10. Source / Provenance Diagnostic",
            "",
            f"- Rank1 source distribution: `{source['rank1_candidate_source_distribution']}`",
            f"- Best-proxy source distribution: `{source['best_proxy_candidate_source_distribution']}`",
            "",
            "Source/provenance is useful for identifying legacy artifacts, but should remain diagnostic-only. It should not become an active scoring input.",
            "",
            "## 11. Geometry Factor V2 Candidate Directions",
            "",
        ]
    )
    for _, row in hypotheses.iterrows():
        if row["hypothesis"] in ["size_aspect_fixed_prior", "area_fixed_prior", "heading_consistency", "range_cross_az_residual_structure"]:
            lines.append(f"- `{row['hypothesis']}`: {row['candidate_direction']} Evidence: {row['diagnostic_evidence']}")
    lines.extend(
        [
            "",
            "## 12. Optical Temporal Factor V2 Candidate Directions",
            "",
            "- Separate A005-aligned base-candidate artifacts from true temporal consistency.",
            "- Keep temporal evidence soft; do not let optical prior overwrite or move SAR candidates.",
            "- Recompute any temporal residuals only from approved safe fields, not legacy `delta_*_from_pred` or `temporal_factor_score`.",
            "",
            "## 13. Explicitly Not Recommended",
            "",
            "- Do not directly sort by `candidate_source`.",
            "- Do not use `temporal_factor_score`.",
            "- Do not use `delta_*_from_pred`.",
            "- Do not tune thresholds from GT.",
            "- Do not feed A021 condition labels into inference.",
            "",
            "## 14. Next Step",
            "",
            "If this diagnostic is accepted, write a `geometry_factor v2 fixed-prior spec` focused on physical size/aspect/area and coordinate residual ownership. In parallel, write an `optical_temporal_factor v2 diagnostic spec` that separates temporal-zero base artifacts from real temporal consistency. Do not directly tune v2 thresholds from these evaluation results.",
        ]
    )
    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_root) / f"gm17_phase4_minimal_factor_pilot_v1_diagnostics_{timestamp}"
    figures_dir = output_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=False)
    log_path = Path(args.log_root) / f"gm17_phase4_minimal_factor_pilot_v1_diagnostics_{timestamp}.log"
    logger = RunLogger(log_path)
    logger.write("Starting GM_RM017-only minimal factor pilot v1 diagnostic analysis.")

    pilot_dir = Path(args.pilot_dir)
    paths = load_required_outputs(pilot_dir)
    with paths["manifest"].open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    with paths["evaluation_summary"].open("r", encoding="utf-8") as f:
        eval_summary = json.load(f)

    ranked = pd.read_csv(paths["ranked"])
    eval_per_target = pd.read_csv(paths["evaluation_per_target"])
    eval_condition_groups = pd.read_csv(paths["evaluation_condition_groups"])
    logger.write(f"Loaded ranked candidates: rows={len(ranked)}")
    logger.write(f"Loaded evaluation_per_target: rows={len(eval_per_target)}")

    ranked_diag, provenance_status = merge_provenance(ranked, Path(args.a001), logger)
    per_target = prepare_per_target(ranked_diag, eval_per_target)
    role_long = build_role_long(per_target)
    rank_dist = rank_distribution(per_target)
    gap_rows = build_gap_rows(per_target)
    gap_summary = summarize_gaps(gap_rows)
    temporal_zero = temporal_zero_artifact(per_target)
    failure_df = failure_groups(per_target)
    hypotheses = v2_hypotheses(per_target, gap_summary, temporal_zero)
    figure_paths = write_plots(per_target, failure_df, figures_dir)

    per_target_cols = [
        "target_identity",
        "scene",
        "sar_frame_num",
        "gm17_track_id",
        "condition_type",
        "condition_status",
        "truncation_degree",
        "occlusion_degree",
        "rank1_candidate_id",
        "best_proxy_candidate_id",
        "best_proxy_pilot_rank",
        "best_proxy_iou",
        "best_proxy_center_error",
        "best_center_candidate_id",
        "best_center_pilot_rank",
        "best_center_error",
        "best_center_proxy_iou",
        "rank1_center_error",
        "rank1_proxy_iou",
        "delta_rank1_minus_best_proxy_iou",
        "delta_rank1_minus_best_center_error",
        "temporal_zero_candidate_count",
        "best_proxy_in_top5",
        "best_proxy_in_top20",
        "best_center_in_top5",
        "best_center_in_top20",
        "rank1_is_best_proxy",
        "rank1_is_best_center",
        "rank1_temporal_distance",
        "best_proxy_temporal_distance",
        "best_center_temporal_distance",
        "rank1_w",
        "rank1_h",
        "rank1_aspect",
        "rank1_area",
        "rank1_heading",
        "rank1_r",
        "rank1_cross",
        "rank1_az",
        "best_proxy_w",
        "best_proxy_h",
        "best_proxy_aspect",
        "best_proxy_area",
        "best_proxy_heading",
        "best_proxy_r",
        "best_proxy_cross",
        "best_proxy_az",
        "best_center_w",
        "best_center_h",
        "best_center_aspect",
        "best_center_area",
        "best_center_heading",
        "best_center_r",
        "best_center_cross",
        "best_center_az",
        "rank1_candidate_source",
        "best_proxy_candidate_source",
        "best_center_candidate_source",
    ]
    per_target_cols = [col for col in per_target_cols if col in per_target.columns]

    output_paths = {
        "diagnostic_per_target": output_dir / "diagnostic_per_target.csv",
        "diagnostic_candidate_roles_long": output_dir / "diagnostic_candidate_roles_long.csv",
        "diagnostic_rank_distribution": output_dir / "diagnostic_rank_distribution.csv",
        "diagnostic_geometry_gap_summary": output_dir / "diagnostic_geometry_gap_summary.csv",
        "diagnostic_temporal_zero_artifact": output_dir / "diagnostic_temporal_zero_artifact.csv",
        "diagnostic_failure_groups": output_dir / "diagnostic_failure_groups.csv",
        "diagnostic_v2_hypothesis_candidates": output_dir / "diagnostic_v2_hypothesis_candidates.csv",
        "diagnostic_summary": output_dir / "diagnostic_summary.json",
    }
    per_target[per_target_cols].to_csv(output_paths["diagnostic_per_target"], index=False, encoding="utf-8")
    role_long.to_csv(output_paths["diagnostic_candidate_roles_long"], index=False, encoding="utf-8")
    rank_dist.to_csv(output_paths["diagnostic_rank_distribution"], index=False, encoding="utf-8")
    gap_summary.to_csv(output_paths["diagnostic_geometry_gap_summary"], index=False, encoding="utf-8")
    temporal_zero.to_csv(output_paths["diagnostic_temporal_zero_artifact"], index=False, encoding="utf-8")
    failure_df.to_csv(output_paths["diagnostic_failure_groups"], index=False, encoding="utf-8")
    hypotheses.to_csv(output_paths["diagnostic_v2_hypothesis_candidates"], index=False, encoding="utf-8")

    doc_path = DEFAULT_DOCS_ROOT / f"gm17_phase4_minimal_factor_pilot_v1_diagnostic_summary_{timestamp}.md"
    summary = build_summary(
        args,
        output_dir,
        doc_path,
        paths,
        output_paths,
        manifest,
        eval_summary,
        per_target,
        rank_dist,
        failure_df,
        temporal_zero,
        gap_summary,
        hypotheses,
        provenance_status,
        figure_paths,
    )
    summary["outputs"]["figures_dir"] = str(figures_dir)
    summary["outputs"]["log"] = str(log_path)
    with output_paths["diagnostic_summary"].open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    write_markdown_summary(doc_path, output_dir, summary, failure_df, gap_summary, hypotheses)

    logger.write(f"Wrote diagnostics output directory: {output_dir}")
    logger.write(f"Wrote markdown summary: {doc_path}")
    logger.write("Completed v1 diagnostic analysis without rerunning selection or generating v2 ranking.")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose GM_RM017-only minimal factor pilot v1 output.")
    parser.add_argument("--pilot-dir", default=str(DEFAULT_PILOT_DIR), help="Path to v1 pilot output directory")
    parser.add_argument("--a001", default=str(DEFAULT_A001), help="Path to A001 candidate bank for diagnostic provenance only")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Workspace output root")
    parser.add_argument("--log-root", default=str(DEFAULT_LOG_ROOT), help="Workspace log root")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
