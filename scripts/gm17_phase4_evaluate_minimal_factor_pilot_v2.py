from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[1]
A019_DEFAULT = WORKSPACE / "output" / "hermes_annotation_consolidation_2026-05-20" / "00_tables" / "final_gt_working.csv"
A021_DEFAULT = WORKSPACE / "output" / "hermes_annotation_consolidation_2026-05-20" / "00_tables" / "visibility_condition_working.csv"
V1_OUTPUT_DEFAULT = WORKSPACE / "output" / "gm17_phase4_minimal_factor_pilot_20260628_110447"
V1_DIAG_DEFAULT = WORKSPACE / "output" / "gm17_phase4_minimal_factor_pilot_v1_diagnostics_20260628_113224"
LOG_ROOT_DEFAULT = WORKSPACE / "logs"
DOCS_ROOT_DEFAULT = WORKSPACE / "docs"

JOIN_KEYS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
EVAL_JOIN_KEYS = ["target_identity", "scene", "sar_frame_num"]
CONDITION_FIELDS = ["condition_type", "condition_status", "truncation_degree", "occlusion_degree"]
GT_FIELDS = [
    "target_identity",
    "scene",
    "sar_frame_num",
    "final_cx",
    "final_cy",
    "final_w",
    "final_h",
    "final_ax_x1",
    "final_ax_y1",
    "final_ax_x2",
    "final_ax_y2",
]
PROXY_IOU_THRESHOLD = 0.25
CENTER_THRESHOLD = 50.0
VARIANTS = ["v2a", "v2b", "v2c"]


class RunLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, message: str) -> None:
        line = f"[{datetime.now().isoformat(timespec='seconds')}] {message}"
        print(line)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def pilot_timestamp(pilot_dir: Path) -> str:
    match = re.search(r"(\d{8}_\d{6})$", pilot_dir.name)
    return match.group(1) if match else datetime.now().strftime("%Y%m%d_%H%M%S")


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)


def axis_iou(df: pd.DataFrame) -> pd.Series:
    cand_x1 = df["cx"] - df["w"] / 2.0
    cand_y1 = df["cy"] - df["h"] / 2.0
    cand_x2 = df["cx"] + df["w"] / 2.0
    cand_y2 = df["cy"] + df["h"] / 2.0
    gt_x1 = df["final_ax_x1"]
    gt_y1 = df["final_ax_y1"]
    gt_x2 = df["final_ax_x2"]
    gt_y2 = df["final_ax_y2"]
    inter_x1 = np.maximum(cand_x1, gt_x1)
    inter_y1 = np.maximum(cand_y1, gt_y1)
    inter_x2 = np.minimum(cand_x2, gt_x2)
    inter_y2 = np.minimum(cand_y2, gt_y2)
    inter = np.maximum(0.0, inter_x2 - inter_x1) * np.maximum(0.0, inter_y2 - inter_y1)
    cand_area = np.maximum(0.0, cand_x2 - cand_x1) * np.maximum(0.0, cand_y2 - cand_y1)
    gt_area = np.maximum(0.0, gt_x2 - gt_x1) * np.maximum(0.0, gt_y2 - gt_y1)
    union = cand_area + gt_area - inter
    return pd.Series(np.where(union > 0, inter / union, np.nan), index=df.index)


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["cx", "cy", "w", "h", "final_cx", "final_cy", "final_w", "final_h", "final_ax_x1", "final_ax_y1", "final_ax_x2", "final_ax_y2"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["center_error"] = np.sqrt((out["cx"] - out["final_cx"]) ** 2 + (out["cy"] - out["final_cy"]) ** 2)
    out["axis_aligned_proxy_iou"] = axis_iou(out)
    out["proxy_hit_iou_0_25"] = out["axis_aligned_proxy_iou"] >= PROXY_IOU_THRESHOLD
    out["center_hit_50px"] = out["center_error"] <= CENTER_THRESHOLD
    return out


def summarize_selected(df: pd.DataFrame) -> dict:
    return {
        "n_targets": int(len(df)),
        "mean_center_error": float(df["center_error"].mean()),
        "median_center_error": float(df["center_error"].median()),
        "mean_axis_aligned_proxy_iou": float(df["axis_aligned_proxy_iou"].mean()),
        "median_axis_aligned_proxy_iou": float(df["axis_aligned_proxy_iou"].median()),
        "proxy_iou_recall_at_1_threshold_0_25": float(df["proxy_hit_iou_0_25"].mean()),
        "center_recall_at_1_threshold_50px": float(df["center_hit_50px"].mean()),
    }


def load_unique(path: Path, usecols: list[str], keys: list[str], logger: RunLogger, name: str) -> tuple[pd.DataFrame, int]:
    df = pd.read_csv(path, usecols=usecols)
    dups = int(df.duplicated(keys, keep=False).sum())
    if dups:
        logger.write(f"{name} duplicate rows on {keys}: {dups}; keeping first for post-inference evaluation.")
    return df.drop_duplicates(keys, keep="first"), dups


def variant_rank_col(variant: str) -> str:
    return f"{variant}_rank"


def best_rows(candidates: pd.DataFrame, variant: str) -> pd.DataFrame:
    rank_col = variant_rank_col(variant)
    best_proxy = (
        candidates.sort_values(JOIN_KEYS + ["axis_aligned_proxy_iou", "center_error"], ascending=[True, True, True, True, False, True], kind="mergesort")
        .groupby(JOIN_KEYS, dropna=False)
        .head(1)
    )
    best_proxy = best_proxy[JOIN_KEYS + ["candidate_id", rank_col, "axis_aligned_proxy_iou", "center_error"]].rename(
        columns={
            "candidate_id": "best_proxy_candidate_id",
            rank_col: "best_proxy_rank",
            "axis_aligned_proxy_iou": "best_proxy_iou",
            "center_error": "best_proxy_center_error",
        }
    )
    best_center = (
        candidates.sort_values(JOIN_KEYS + ["center_error", "axis_aligned_proxy_iou"], ascending=[True, True, True, True, True, False], kind="mergesort")
        .groupby(JOIN_KEYS, dropna=False)
        .head(1)
    )
    best_center = best_center[JOIN_KEYS + ["candidate_id", rank_col, "center_error", "axis_aligned_proxy_iou"]].rename(
        columns={
            "candidate_id": "best_center_candidate_id",
            rank_col: "best_center_rank",
            "center_error": "best_center_error",
            "axis_aligned_proxy_iou": "best_center_proxy_iou",
        }
    )
    return best_proxy.merge(best_center, on=JOIN_KEYS, how="outer")


def recall_at_k(candidates: pd.DataFrame, variant: str, k: int, metric: str, threshold: float, higher: bool) -> float:
    subset = candidates.loc[candidates[variant_rank_col(variant)] <= k]
    if higher:
        hits = subset.groupby(JOIN_KEYS, dropna=False)[metric].max() >= threshold
    else:
        hits = subset.groupby(JOIN_KEYS, dropna=False)[metric].min() <= threshold
    return float(hits.mean())


def evaluate_variant(candidates: pd.DataFrame, conditions: pd.DataFrame, variant: str) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    rank_col = variant_rank_col(variant)
    rank1 = candidates.loc[candidates[rank_col] == 1].copy()
    rank1 = rank1.merge(best_rows(candidates, variant), on=JOIN_KEYS, how="left", validate="one_to_one")
    rank1["variant"] = variant
    rank1["rank1_is_best_proxy"] = rank1["candidate_id"] == rank1["best_proxy_candidate_id"]
    rank1["rank1_is_best_center"] = rank1["candidate_id"] == rank1["best_center_candidate_id"]
    rank1 = rank1.merge(conditions, on=EVAL_JOIN_KEYS, how="left", validate="many_to_one")
    summary = summarize_selected(rank1)
    summary.update(
        {
            "variant": variant,
            "proxy_iou_recall_at_3_threshold_0_25": recall_at_k(candidates, variant, 3, "axis_aligned_proxy_iou", PROXY_IOU_THRESHOLD, True),
            "proxy_iou_recall_at_5_threshold_0_25": recall_at_k(candidates, variant, 5, "axis_aligned_proxy_iou", PROXY_IOU_THRESHOLD, True),
            "center_recall_at_3_threshold_50px": recall_at_k(candidates, variant, 3, "center_error", CENTER_THRESHOLD, False),
            "center_recall_at_5_threshold_50px": recall_at_k(candidates, variant, 5, "center_error", CENTER_THRESHOLD, False),
            "best_proxy_iou_coverage_threshold_0_25": float((best_rows(candidates, variant)["best_proxy_iou"] >= PROXY_IOU_THRESHOLD).mean()),
            "best_center_coverage_threshold_50px": float((best_rows(candidates, variant)["best_center_error"] <= CENTER_THRESHOLD).mean()),
            "mean_rank_of_best_proxy": float(rank1["best_proxy_rank"].mean()),
            "median_rank_of_best_proxy": float(rank1["best_proxy_rank"].median()),
            "rank1_is_best_proxy_rate": float(rank1["rank1_is_best_proxy"].mean()),
            "rank1_is_best_center_rate": float(rank1["rank1_is_best_center"].mean()),
            "best_proxy_top5_rate": float((rank1["best_proxy_rank"] <= 5).mean()),
            "best_proxy_top20_rate": float((rank1["best_proxy_rank"] <= 20).mean()),
            "rank1_temporal_zero_rate": float(rank1["temporal_zero"].mean()) if "temporal_zero" in rank1 else None,
        }
    )
    group_cols = ["variant"] + CONDITION_FIELDS
    condition_groups = (
        rank1.groupby(group_cols, dropna=False)
        .agg(
            n_targets=("candidate_id", "count"),
            mean_center_error=("center_error", "mean"),
            median_center_error=("center_error", "median"),
            mean_proxy_iou=("axis_aligned_proxy_iou", "mean"),
            proxy_recall_at_1=("proxy_hit_iou_0_25", "mean"),
            center_recall_at_1=("center_hit_50px", "mean"),
            rank1_is_best_proxy_rate=("rank1_is_best_proxy", "mean"),
            mean_best_proxy_rank=("best_proxy_rank", "mean"),
        )
        .reset_index()
    )
    return summary, rank1, condition_groups


def read_v1(v1_output: Path, v1_diag: Path) -> tuple[dict, dict]:
    with (v1_output / "evaluation_summary.json").open("r", encoding="utf-8") as f:
        eval_summary = json.load(f)
    with (v1_diag / "diagnostic_summary.json").open("r", encoding="utf-8") as f:
        diag_summary = json.load(f)
    return eval_summary, diag_summary


def comparison_rows(v1_eval: dict, v1_diag: dict, v2_summaries: dict) -> pd.DataFrame:
    rows = []
    v1_selected = v1_eval.get("selected_rank1_summary", {})
    v1_recall = v1_eval.get("recall", {})
    v1_best = v1_eval.get("best_candidate_coverage", {})
    rows.append(
        {
            "variant": "v1",
            "mean_center_error": v1_selected.get("mean_center_error"),
            "median_center_error": v1_selected.get("median_center_error"),
            "mean_axis_aligned_proxy_iou": v1_selected.get("mean_axis_aligned_proxy_iou"),
            "proxy_iou_recall_at_1_threshold_0_25": v1_selected.get("proxy_iou_recall_at_1_threshold_0_25"),
            "center_recall_at_1_threshold_50px": v1_selected.get("center_recall_at_1_threshold_50px"),
            "proxy_iou_recall_at_3_threshold_0_25": v1_recall.get("proxy_iou_recall_at_3_threshold_0.25"),
            "proxy_iou_recall_at_5_threshold_0_25": v1_recall.get("proxy_iou_recall_at_5_threshold_0.25"),
            "rank1_is_best_proxy_rate": v1_diag.get("rank1_is_best_proxy_rate"),
            "rank1_is_best_center_rate": v1_diag.get("rank1_is_best_center_rate"),
            "best_proxy_top5_rate": v1_diag.get("rank_distribution_summary", {}).get("best_proxy", {}).get("top5_rate"),
            "best_proxy_top20_rate": v1_diag.get("rank_distribution_summary", {}).get("best_proxy", {}).get("top20_rate"),
            "mean_rank_of_best_proxy": v1_best.get("mean_rank_of_best_proxy_candidate"),
            "rank1_temporal_zero_rate": v1_diag.get("temporal_zero_artifact", {}).get("rank1_temporal_zero_rate", 1.0),
        }
    )
    for variant, summary in v2_summaries.items():
        row = {"variant": variant}
        row.update(summary)
        rows.append(row)
    return pd.DataFrame(rows)


def make_bar(path: Path, df: pd.DataFrame, metric: str, title: str, ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.8))
    plot_df = df[["variant", metric]].dropna()
    ax.bar(plot_df["variant"], plot_df[metric], color=["#6b7280", "#2563eb", "#059669", "#d97706"][: len(plot_df)])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("variant")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def make_figures(fig_dir: Path, comparison: pd.DataFrame, per_target: pd.DataFrame, condition_groups: pd.DataFrame) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    make_bar(fig_dir / "v1_v2_proxy_iou_recall_bar.png", comparison, "proxy_iou_recall_at_1_threshold_0_25", "Proxy IoU Recall@1", "recall")
    make_bar(fig_dir / "v1_v2_center_error_bar.png", comparison, "mean_center_error", "Mean Center Error", "px")
    make_bar(fig_dir / "v1_v2_rank1_best_proxy_rate_bar.png", comparison, "rank1_is_best_proxy_rate", "Rank1 Is Best Proxy Rate", "rate")

    fig, ax = plt.subplots(figsize=(8, 4.8))
    for variant in VARIANTS:
        values = per_target.loc[per_target["variant"] == variant, "best_proxy_rank"].dropna()
        ax.hist(values, bins=30, alpha=0.45, label=variant)
    ax.set_title("V2 Best Proxy Rank Distribution")
    ax.set_xlabel("best_proxy_rank")
    ax.set_ylabel("targets")
    ax.legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "v2_variant_best_proxy_rank_hist.png", dpi=160)
    plt.close(fig)

    fail = condition_groups.copy()
    fail["condition_label"] = (
        fail["condition_type"].astype(str)
        + "/"
        + fail["truncation_degree"].astype(str)
        + "/"
        + fail["occlusion_degree"].astype(str)
    )
    worst = fail.sort_values(["mean_center_error"], ascending=False).head(12)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    labels = worst["variant"] + " " + worst["condition_label"]
    ax.barh(labels, worst["mean_center_error"], color="#dc2626")
    ax.set_title("V2 Condition Failure Groups by Mean Center Error")
    ax.set_xlabel("mean center error")
    fig.tight_layout()
    fig.savefig(fig_dir / "v2_condition_failure_bar.png", dpi=160)
    plt.close(fig)


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    display = df.copy()
    for col in display.columns:
        if pd.api.types.is_float_dtype(display[col]):
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else f"{float(x):.4f}")
        else:
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else str(x))
    headers = list(display.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in display.iterrows():
        values = [str(row[col]).replace("|", "\\|") for col in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_summary_doc(path: Path, pilot_dir: Path, summary: dict, comparison: pd.DataFrame, best_variant: str) -> None:
    v1 = comparison.loc[comparison["variant"] == "v1"].iloc[0].to_dict()
    best = comparison.loc[comparison["variant"] == best_variant].iloc[0].to_dict()
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# GM17 Phase4 Minimal Factor Pilot V2 Run Summary {summary['timestamp']}\n\n")
        f.write("## 1. Purpose\n\n")
        f.write("This v2 run tests whether fixed, no-training rules can reduce the v1 temporal-zero base-candidate artifact and expose useful geometry/coordinate residual signal.\n\n")
        f.write("## 2. Inputs And Outputs\n\n")
        f.write(f"- Pilot output: `{pilot_dir}`\n")
        f.write(f"- Evaluation summary: `{pilot_dir / 'evaluation_v2_summary.json'}`\n")
        f.write(f"- Figures: `{pilot_dir / 'figures'}`\n\n")
        f.write("## 3. V2 Variant Definitions\n\n")
        for key, value in summary["manifest"]["variant_definitions"].items():
            f.write(f"- `{key}`: {value}\n")
        f.write("\n## 4. Field Use And Forbidden Fields\n\n")
        f.write("Ranking used only A001 safe candidate fields and A005 `pred_r/pred_cross/pred_az`. It did not use GT, A021 condition labels, `candidate_source`, legacy `delta_*`, `temporal_factor_score`, `score/lr_score/sar_factor_score`, selected outputs, B patch, oracle fields, or condition/truncation/occlusion fields.\n\n")
        f.write("## 5. Join Situation\n\n")
        f.write(json.dumps(summary["manifest"]["join_summary"], ensure_ascii=False, indent=2))
        f.write("\n\n## 6. Geometry Cluster Distance\n\n")
        f.write("`geometry_cluster_distance` is computed within each target/frame/track candidate group from robust deviations of heading, r, cross, az, and area. Scales come from group MAD, then IQR, then fallback 1. No GT statistics or A019/A021 fields are used in this distance.\n\n")
        f.write("## 7. Core Results\n\n")
        f.write(dataframe_to_markdown(comparison))
        f.write("\n\n")
        f.write("## 8. V1 vs V2 Comparison\n\n")
        f.write(f"- V1 rank1_is_best_proxy: {v1.get('rank1_is_best_proxy_rate'):.4f}\n")
        f.write(f"- Best V2 variant by rank1_is_best_proxy: `{best_variant}` at {best.get('rank1_is_best_proxy_rate'):.4f}\n")
        f.write(f"- V1 best_proxy top5/top20: {v1.get('best_proxy_top5_rate'):.4f} / {v1.get('best_proxy_top20_rate'):.4f}\n")
        f.write(f"- `{best_variant}` best_proxy top5/top20: {best.get('best_proxy_top5_rate'):.4f} / {best.get('best_proxy_top20_rate'):.4f}\n\n")
        f.write("## 9. Best Variant\n\n")
        f.write(f"`{best_variant}` is the strongest variant by rank1_is_best_proxy rate in this fixed diagnostic pilot.\n\n")
        f.write("## 10. Temporal-Zero Artifact\n\n")
        f.write("V2 explicitly records `temporal_zero` and avoids using legacy `delta_*` or `temporal_factor_score`. Compare rank1 temporal-zero rates in `evaluation_v2_vs_v1_comparison.csv`.\n\n")
        f.write("## 11. Truncated+Occluded Failure\n\n")
        f.write("A021 condition labels were used only after v2 outputs existed, for post-inference grouping. See `evaluation_v2_condition_groups_by_variant.csv` and `v2_condition_failure_bar.png`.\n\n")
        f.write("## 12. Overfit Or Instability Risk\n\n")
        f.write("No parameters were tuned from GT, but the fixed group-robust distances may still be unstable in small or degenerate candidate groups, especially when MAD/IQR fall back to 1. Treat this as factor signal diagnosis, not a final model.\n\n")
        f.write("## 13. Next Step\n\n")
        f.write("- If V2B is effective, deepen `geometry_factor` fixed-prior design.\n")
        f.write("- If V2C is effective, redesign `optical_temporal_factor` so temporal evidence remains soft.\n")
        f.write("- If neither is effective, the likely need is new candidate proposal or a SAR structure factor.\n")
        f.write("- Do not continue threshold tuning; summarize factor signal first.\n")


def run(args: argparse.Namespace) -> dict:
    pilot_dir = Path(args.pilot_dir)
    timestamp = pilot_timestamp(pilot_dir)
    log_path = Path(args.log_root) / f"gm17_phase4_minimal_factor_pilot_v2_evaluation_{timestamp}.log"
    logger = RunLogger(log_path)
    logger.write(f"Starting v2 post-inference evaluation for {pilot_dir}")

    ranked_path = pilot_dir / "pilot_v2_candidates_ranked.csv"
    selected_path = pilot_dir / "pilot_v2_selected_rank1_by_variant.csv"
    manifest_path = pilot_dir / "pilot_v2_manifest.json"
    for path in [ranked_path, selected_path, manifest_path]:
        require_file(path)

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    ranked = pd.read_csv(ranked_path)
    _selected = pd.read_csv(selected_path)
    logger.write("Confirmed v2 output exists before reading A019/A021.")

    a019_path = Path(args.a019)
    a021_path = Path(args.a021)
    gt, gt_dups = load_unique(a019_path, GT_FIELDS, EVAL_JOIN_KEYS, logger, "A019")
    cond_usecols = EVAL_JOIN_KEYS + CONDITION_FIELDS
    cond, cond_dups = load_unique(a021_path, cond_usecols, EVAL_JOIN_KEYS, logger, "A021")
    logger.write(f"Read A019 post-inference: rows={len(gt)}")
    logger.write(f"Read A021 post-inference: rows={len(cond)}")

    candidates = ranked.merge(gt, on=EVAL_JOIN_KEYS, how="left", validate="many_to_one")
    candidates = add_metrics(candidates)

    summaries = {}
    per_targets = []
    cond_groups = []
    for variant in VARIANTS:
        s, per, cg = evaluate_variant(candidates, cond, variant)
        summaries[variant] = s
        per_targets.append(per)
        cond_groups.append(cg)
    per_target = pd.concat(per_targets, ignore_index=True)
    condition_groups = pd.concat(cond_groups, ignore_index=True)

    v1_eval, v1_diag = read_v1(Path(args.v1_output), Path(args.v1_diagnostics))
    comparison = comparison_rows(v1_eval, v1_diag, summaries)
    v2_only = comparison.loc[comparison["variant"].isin(VARIANTS)].copy()
    best_variant = str(v2_only.sort_values(["rank1_is_best_proxy_rate", "proxy_iou_recall_at_1_threshold_0_25"], ascending=False).iloc[0]["variant"])

    figures_dir = pilot_dir / "figures"
    make_figures(figures_dir, comparison, per_target, condition_groups)

    summary = {
        "run_type": "GM_RM017-only minimal factor pilot v2 post-inference evaluation",
        "timestamp": timestamp,
        "pilot_dir": str(pilot_dir),
        "manifest": manifest,
        "a019_a021_read_after_v2_output_confirmed": True,
        "a021_used_only_for_post_inference_grouping": True,
        "source_provenance_not_used_for_ranking": True,
        "gt_not_used_for_ranking_or_tuning": True,
        "gt_duplicate_rows_on_eval_keys": gt_dups,
        "condition_duplicate_rows_on_eval_keys": cond_dups,
        "variant_summaries": summaries,
        "best_variant_by_rank1_is_best_proxy": best_variant,
        "outputs": {
            "evaluation_v2_summary": str(pilot_dir / "evaluation_v2_summary.json"),
            "evaluation_v2_per_target_by_variant": str(pilot_dir / "evaluation_v2_per_target_by_variant.csv"),
            "evaluation_v2_condition_groups_by_variant": str(pilot_dir / "evaluation_v2_condition_groups_by_variant.csv"),
            "evaluation_v2_vs_v1_comparison": str(pilot_dir / "evaluation_v2_vs_v1_comparison.csv"),
            "evaluation_v2_readme": str(pilot_dir / "evaluation_v2_readme.md"),
            "figures_dir": str(figures_dir),
            "summary_doc": str(Path(args.docs_root) / f"gm17_phase4_minimal_factor_pilot_v2_run_summary_{timestamp}.md"),
            "log": str(log_path),
        },
    }

    per_target.to_csv(pilot_dir / "evaluation_v2_per_target_by_variant.csv", index=False, encoding="utf-8")
    condition_groups.to_csv(pilot_dir / "evaluation_v2_condition_groups_by_variant.csv", index=False, encoding="utf-8")
    comparison.to_csv(pilot_dir / "evaluation_v2_vs_v1_comparison.csv", index=False, encoding="utf-8")
    with (pilot_dir / "evaluation_v2_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with (pilot_dir / "evaluation_v2_readme.md").open("w", encoding="utf-8") as f:
        f.write("# GM17 Phase4 Minimal Factor Pilot V2 Evaluation\n\n")
        f.write("Post-inference evaluation only. A019/A021 were read after v2 outputs existed.\n\n")
        f.write(f"Best variant by rank1_is_best_proxy: `{best_variant}`\n\n")
        f.write("Outputs: summary JSON, per-target CSV, condition-group CSV, v1-v2 comparison CSV, figures.\n")
    doc_path = Path(args.docs_root) / f"gm17_phase4_minimal_factor_pilot_v2_run_summary_{timestamp}.md"
    write_summary_doc(doc_path, pilot_dir, summary, comparison, best_variant)

    logger.write(f"Wrote v2 evaluation summary: {pilot_dir / 'evaluation_v2_summary.json'}")
    logger.write(f"Wrote v2 run summary doc: {doc_path}")
    logger.write("Completed v2 post-inference evaluation and figures.")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate GM_RM017-only minimal factor pilot v2.")
    parser.add_argument("--pilot-dir", required=True)
    parser.add_argument("--a019", default=str(A019_DEFAULT))
    parser.add_argument("--a021", default=str(A021_DEFAULT))
    parser.add_argument("--v1-output", default=str(V1_OUTPUT_DEFAULT))
    parser.add_argument("--v1-diagnostics", default=str(V1_DIAG_DEFAULT))
    parser.add_argument("--log-root", default=str(LOG_ROOT_DEFAULT))
    parser.add_argument("--docs-root", default=str(DOCS_ROOT_DEFAULT))
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
