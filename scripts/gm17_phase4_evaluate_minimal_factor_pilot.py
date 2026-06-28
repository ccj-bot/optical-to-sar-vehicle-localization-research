from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[1]
A019_DEFAULT = WORKSPACE / "output" / "hermes_annotation_consolidation_2026-05-20" / "00_tables" / "final_gt_working.csv"
A021_DEFAULT = WORKSPACE / "output" / "hermes_annotation_consolidation_2026-05-20" / "00_tables" / "visibility_condition_working.csv"
LOG_ROOT_DEFAULT = WORKSPACE / "logs"

PILOT_CANDIDATES = "pilot_candidates_ranked.csv"
PILOT_SELECTED = "pilot_selected_rank1.csv"
PILOT_MANIFEST = "pilot_manifest.json"

PILOT_GROUP_KEYS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
EVAL_JOIN_KEYS = ["target_identity", "scene", "sar_frame_num"]
GT_REQUIRED_FIELDS = [
    "target_identity",
    "scene",
    "sar_frame_num",
    "final_cx",
    "final_cy",
    "final_w",
    "final_h",
]
GT_AX_FIELDS = ["final_ax_x1", "final_ax_y1", "final_ax_x2", "final_ax_y2"]
CONDITION_FIELDS = ["condition_type", "condition_status", "truncation_degree", "occlusion_degree"]

PROXY_IOU_THRESHOLD = 0.25
CENTER_ERROR_THRESHOLD_PX = 50.0
RECALL_KS = [1, 3, 5]


class RunLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, message: str) -> None:
        line = f"[{datetime.now().isoformat(timespec='seconds')}] {message}"
        print(line)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def read_header(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


def require_columns(name: str, columns: list[str], required: list[str]) -> None:
    missing = [col for col in required if col not in columns]
    if missing:
        raise ValueError(f"{name} missing required fields: {missing}; available={columns}")


def axis_box_from_center(df: pd.DataFrame, cx: str, cy: str, w: str, h: str, prefix: str) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out[f"{prefix}_x1"] = df[cx] - df[w] / 2.0
    out[f"{prefix}_y1"] = df[cy] - df[h] / 2.0
    out[f"{prefix}_x2"] = df[cx] + df[w] / 2.0
    out[f"{prefix}_y2"] = df[cy] + df[h] / 2.0
    return out


def proxy_iou_axis_aligned(df: pd.DataFrame) -> pd.Series:
    cand = axis_box_from_center(df, "cx", "cy", "w", "h", "cand")
    if set(GT_AX_FIELDS).issubset(df.columns) and df[GT_AX_FIELDS].notna().all(axis=1).any():
        gt_x1 = df["final_ax_x1"]
        gt_y1 = df["final_ax_y1"]
        gt_x2 = df["final_ax_x2"]
        gt_y2 = df["final_ax_y2"]
    else:
        gt = axis_box_from_center(df, "final_cx", "final_cy", "final_w", "final_h", "gt")
        gt_x1 = gt["gt_x1"]
        gt_y1 = gt["gt_y1"]
        gt_x2 = gt["gt_x2"]
        gt_y2 = gt["gt_y2"]

    inter_x1 = np.maximum(cand["cand_x1"], gt_x1)
    inter_y1 = np.maximum(cand["cand_y1"], gt_y1)
    inter_x2 = np.minimum(cand["cand_x2"], gt_x2)
    inter_y2 = np.minimum(cand["cand_y2"], gt_y2)
    inter_w = np.maximum(0.0, inter_x2 - inter_x1)
    inter_h = np.maximum(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    cand_area = np.maximum(0.0, cand["cand_x2"] - cand["cand_x1"]) * np.maximum(0.0, cand["cand_y2"] - cand["cand_y1"])
    gt_area = np.maximum(0.0, gt_x2 - gt_x1) * np.maximum(0.0, gt_y2 - gt_y1)
    union = cand_area + gt_area - inter_area
    return pd.Series(np.where(union > 0, inter_area / union, np.nan), index=df.index)


def add_eval_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    numeric_cols = ["cx", "cy", "w", "h", "final_cx", "final_cy", "final_w", "final_h"] + [c for c in GT_AX_FIELDS if c in out.columns]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["center_error"] = np.sqrt((out["cx"] - out["final_cx"]) ** 2 + (out["cy"] - out["final_cy"]) ** 2)
    out["axis_aligned_proxy_iou"] = proxy_iou_axis_aligned(out)
    out["proxy_hit_iou_0_25"] = out["axis_aligned_proxy_iou"] >= PROXY_IOU_THRESHOLD
    out["center_hit_50px"] = out["center_error"] <= CENTER_ERROR_THRESHOLD_PX
    return out


def collapse_unique(df: pd.DataFrame, keys: list[str], name: str, logger: RunLogger) -> tuple[pd.DataFrame, int]:
    duplicates = int(df.duplicated(keys, keep=False).sum())
    if duplicates:
        logger.write(f"{name} has {duplicates} duplicate rows on {keys}; keeping first for evaluation join and recording in summary.")
    return df.drop_duplicates(keys, keep="first").copy(), duplicates


def summarize_selection(df: pd.DataFrame, label: str) -> dict:
    return {
        "label": label,
        "rows": int(len(df)),
        "mean_center_error": float(df["center_error"].mean()) if len(df) else None,
        "median_center_error": float(df["center_error"].median()) if len(df) else None,
        "mean_axis_aligned_proxy_iou": float(df["axis_aligned_proxy_iou"].mean()) if len(df) else None,
        "median_axis_aligned_proxy_iou": float(df["axis_aligned_proxy_iou"].median()) if len(df) else None,
        "proxy_iou_recall_at_1_threshold_0_25": float(df["proxy_hit_iou_0_25"].mean()) if len(df) else None,
        "center_recall_at_1_threshold_50px": float(df["center_hit_50px"].mean()) if len(df) else None,
    }


def select_variant(candidates_with_gt: pd.DataFrame, variant: str) -> pd.DataFrame:
    df = candidates_with_gt.copy()
    df["candidate_id_sort"] = df["candidate_id"].astype(str)
    if variant == "combined":
        selected = df.loc[df["pilot_rank"] == 1].copy()
    elif variant == "geometry_only":
        df["geometry_rank_key"] = np.where(df["geometry_valid"].astype(bool), 0, 1)
        selected = (
            df.sort_values(PILOT_GROUP_KEYS + ["geometry_rank_key", "candidate_id_sort"], kind="mergesort")
            .groupby(PILOT_GROUP_KEYS, dropna=False)
            .head(1)
            .copy()
        )
    elif variant == "temporal_only":
        df["temporal_rank_key"] = np.where(df["temporal_distance"].notna(), 0, 1)
        df["temporal_distance_sort"] = df["temporal_distance"].fillna(np.inf)
        selected = (
            df.sort_values(PILOT_GROUP_KEYS + ["temporal_rank_key", "temporal_distance_sort", "candidate_id_sort"], kind="mergesort")
            .groupby(PILOT_GROUP_KEYS, dropna=False)
            .head(1)
            .copy()
        )
    else:
        raise ValueError(f"Unknown selection variant: {variant}")
    return selected


def rank_best_candidates(candidates_with_gt: pd.DataFrame) -> pd.DataFrame:
    df = candidates_with_gt.copy()
    best_proxy = (
        df.sort_values(PILOT_GROUP_KEYS + ["axis_aligned_proxy_iou", "center_error"], ascending=[True, True, True, True, False, True], kind="mergesort")
        .groupby(PILOT_GROUP_KEYS, dropna=False)
        .head(1)
        .copy()
    )
    best_proxy = best_proxy[PILOT_GROUP_KEYS + ["candidate_id", "pilot_rank", "axis_aligned_proxy_iou", "center_error"]].rename(
        columns={
            "candidate_id": "best_proxy_candidate_id",
            "pilot_rank": "best_proxy_pilot_rank",
            "axis_aligned_proxy_iou": "best_proxy_iou",
            "center_error": "best_proxy_center_error",
        }
    )
    best_center = (
        df.sort_values(PILOT_GROUP_KEYS + ["center_error", "axis_aligned_proxy_iou"], ascending=[True, True, True, True, True, False], kind="mergesort")
        .groupby(PILOT_GROUP_KEYS, dropna=False)
        .head(1)
        .copy()
    )
    best_center = best_center[PILOT_GROUP_KEYS + ["candidate_id", "pilot_rank", "center_error", "axis_aligned_proxy_iou"]].rename(
        columns={
            "candidate_id": "best_center_candidate_id",
            "pilot_rank": "best_center_pilot_rank",
            "center_error": "best_center_error",
            "axis_aligned_proxy_iou": "best_center_proxy_iou",
        }
    )
    return best_proxy.merge(best_center, on=PILOT_GROUP_KEYS, how="outer")


def recall_at_k(candidates_with_gt: pd.DataFrame, k: int, metric_col: str, threshold: float, higher_is_better: bool) -> float:
    within_k = candidates_with_gt.loc[candidates_with_gt["pilot_rank"] <= k].copy()
    if within_k.empty:
        return float("nan")
    if higher_is_better:
        hit_by_group = within_k.groupby(PILOT_GROUP_KEYS, dropna=False)[metric_col].max() >= threshold
    else:
        hit_by_group = within_k.groupby(PILOT_GROUP_KEYS, dropna=False)[metric_col].min() <= threshold
    return float(hit_by_group.mean())


def condition_group_summary(per_target: pd.DataFrame) -> pd.DataFrame:
    group_cols = [col for col in CONDITION_FIELDS if col in per_target.columns]
    if not group_cols:
        return pd.DataFrame()
    grouped = (
        per_target.groupby(group_cols, dropna=False)
        .agg(
            n_targets=("candidate_id", "count"),
            mean_selected_center_error=("center_error", "mean"),
            median_selected_center_error=("center_error", "median"),
            mean_selected_proxy_iou=("axis_aligned_proxy_iou", "mean"),
            proxy_iou_recall_at_1=("proxy_hit_iou_0_25", "mean"),
            center_recall_at_1=("center_hit_50px", "mean"),
            mean_best_proxy_iou=("best_proxy_iou", "mean"),
            mean_best_center_error=("best_center_error", "mean"),
        )
        .reset_index()
        .sort_values(["n_targets"], ascending=False)
    )
    return grouped


def run(args: argparse.Namespace) -> dict:
    pilot_dir = Path(args.pilot_dir)
    if not pilot_dir.exists():
        raise FileNotFoundError(f"Pilot output directory does not exist: {pilot_dir}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path(args.log_root) / f"gm17_phase4_minimal_factor_pilot_evaluation_{timestamp}.log"
    logger = RunLogger(log_path)
    logger.write(f"Starting post-inference evaluation for pilot_dir={pilot_dir}")

    ranked_path = pilot_dir / PILOT_CANDIDATES
    selected_path = pilot_dir / PILOT_SELECTED
    manifest_path = pilot_dir / PILOT_MANIFEST
    for path in [ranked_path, selected_path, manifest_path]:
        if not path.exists():
            raise FileNotFoundError(f"Required pilot output missing: {path}")

    a019_path = Path(args.a019)
    a021_path = Path(args.a021)
    ranked = pd.read_csv(ranked_path)
    selected = pd.read_csv(selected_path)
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    gt_columns = read_header(a019_path)
    cond_columns = read_header(a021_path)
    require_columns("A019", gt_columns, GT_REQUIRED_FIELDS)
    require_columns("A021", cond_columns, EVAL_JOIN_KEYS)

    gt_usecols = list(dict.fromkeys(EVAL_JOIN_KEYS + GT_REQUIRED_FIELDS + [c for c in GT_AX_FIELDS if c in gt_columns]))
    condition_usecols = list(dict.fromkeys(EVAL_JOIN_KEYS + [c for c in CONDITION_FIELDS if c in cond_columns]))
    gt = pd.read_csv(a019_path, usecols=gt_usecols)
    cond = pd.read_csv(a021_path, usecols=condition_usecols)
    logger.write(f"Read A019 only after pilot output existed: rows={len(gt)}, cols={len(gt.columns)}")
    logger.write(f"Read A021 only after pilot output existed: rows={len(cond)}, cols={len(cond.columns)}")

    gt, gt_duplicate_rows = collapse_unique(gt, EVAL_JOIN_KEYS, "A019", logger)
    cond, cond_duplicate_rows = collapse_unique(cond, EVAL_JOIN_KEYS, "A021", logger)

    candidates_gt = ranked.merge(gt, on=EVAL_JOIN_KEYS, how="left", validate="many_to_one")
    selected_gt = selected.merge(gt, on=EVAL_JOIN_KEYS, how="left", validate="many_to_one")
    missing_gt_rows = int(selected_gt["final_cx"].isna().sum())
    if missing_gt_rows:
        logger.write(f"WARNING: {missing_gt_rows} selected rows are missing A019 GT after post-inference join.")

    candidates_eval = add_eval_metrics(candidates_gt)
    selected_eval = add_eval_metrics(selected_gt)
    best_eval = rank_best_candidates(candidates_eval)
    per_target = selected_eval.merge(best_eval, on=PILOT_GROUP_KEYS, how="left", validate="one_to_one")
    per_target = per_target.merge(cond, on=EVAL_JOIN_KEYS, how="left", validate="many_to_one")

    variant_summaries = {}
    for variant in ["geometry_only", "temporal_only", "combined"]:
        variant_selected = select_variant(candidates_eval, variant)
        variant_summaries[variant] = summarize_selection(variant_selected, variant)

    recalls = {}
    for k in RECALL_KS:
        recalls[f"proxy_iou_recall_at_{k}_threshold_{PROXY_IOU_THRESHOLD}"] = recall_at_k(
            candidates_eval, k, "axis_aligned_proxy_iou", PROXY_IOU_THRESHOLD, True
        )
        recalls[f"center_recall_at_{k}_threshold_{CENTER_ERROR_THRESHOLD_PX}px"] = recall_at_k(
            candidates_eval, k, "center_error", CENTER_ERROR_THRESHOLD_PX, False
        )

    condition_groups = condition_group_summary(per_target)

    summary = {
        "run_type": "post-inference evaluation for GM_RM017-only minimal factor pilot",
        "evaluation_timestamp": timestamp,
        "pilot_dir": str(pilot_dir),
        "inputs": {
            "pilot_candidates_ranked": str(ranked_path),
            "pilot_selected_rank1": str(selected_path),
            "pilot_manifest": str(manifest_path),
            "A019": str(a019_path),
            "A021": str(a021_path),
        },
        "pilot_output_preexisted_before_A019_A021_read": True,
        "ranking_modified": False,
        "evaluation_join_keys": EVAL_JOIN_KEYS,
        "field_self_check": {
            "A019_required_fields_present": True,
            "A019_axis_aligned_proxy_fields_present": set(GT_AX_FIELDS).issubset(gt_columns),
            "A021_condition_fields_present": [c for c in CONDITION_FIELDS if c in cond_columns],
            "gt_duplicate_rows_on_eval_keys": gt_duplicate_rows,
            "condition_duplicate_rows_on_eval_keys": cond_duplicate_rows,
        },
        "metric_definitions": {
            "center_error": "Euclidean distance between rank1 candidate center and A019 final center.",
            "axis_aligned_proxy_iou": "Axis-aligned proxy IoU; not rotated IoU.",
            "proxy_iou_threshold": PROXY_IOU_THRESHOLD,
            "center_error_threshold_px": CENTER_ERROR_THRESHOLD_PX,
        },
        "counts": {
            "ranked_candidate_rows": int(len(ranked)),
            "rank1_rows": int(len(selected)),
            "groups": int(ranked.groupby(PILOT_GROUP_KEYS, dropna=False).ngroups),
            "selected_missing_gt_rows": missing_gt_rows,
        },
        "selected_rank1_summary": summarize_selection(selected_eval, "combined_rank1"),
        "best_candidate_coverage": {
            "mean_best_proxy_iou": float(best_eval["best_proxy_iou"].mean()) if len(best_eval) else None,
            "median_best_proxy_iou": float(best_eval["best_proxy_iou"].median()) if len(best_eval) else None,
            "best_proxy_iou_coverage_threshold_0_25": float((best_eval["best_proxy_iou"] >= PROXY_IOU_THRESHOLD).mean()) if len(best_eval) else None,
            "mean_best_center_error": float(best_eval["best_center_error"].mean()) if len(best_eval) else None,
            "median_best_center_error": float(best_eval["best_center_error"].median()) if len(best_eval) else None,
            "best_center_coverage_threshold_50px": float((best_eval["best_center_error"] <= CENTER_ERROR_THRESHOLD_PX).mean()) if len(best_eval) else None,
            "mean_rank_of_best_proxy_candidate": float(best_eval["best_proxy_pilot_rank"].mean()) if len(best_eval) else None,
            "median_rank_of_best_proxy_candidate": float(best_eval["best_proxy_pilot_rank"].median()) if len(best_eval) else None,
        },
        "recall": recalls,
        "variant_summaries": variant_summaries,
        "failure_grouping": {
            "condition_group_rows": int(len(condition_groups)),
            "group_fields": [c for c in CONDITION_FIELDS if c in per_target.columns],
        },
        "selection_manifest_join_summary": manifest.get("join_summary", {}),
        "leakage_statement": {
            "A019_A021_read_after_pilot_output": True,
            "evaluation_did_not_modify_pilot_sorting": True,
            "evaluation_results_not_fed_back_to_rules": True,
            "rotated_iou_not_claimed": True,
        },
        "outputs": {
            "evaluation_summary": str(pilot_dir / "evaluation_summary.json"),
            "evaluation_per_target": str(pilot_dir / "evaluation_per_target.csv"),
            "evaluation_condition_groups": str(pilot_dir / "evaluation_condition_groups.csv"),
            "evaluation_readme": str(pilot_dir / "evaluation_readme.md"),
            "log": str(log_path),
        },
    }

    per_target.to_csv(pilot_dir / "evaluation_per_target.csv", index=False, encoding="utf-8")
    condition_groups.to_csv(pilot_dir / "evaluation_condition_groups.csv", index=False, encoding="utf-8")
    with (pilot_dir / "evaluation_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with (pilot_dir / "evaluation_readme.md").open("w", encoding="utf-8") as f:
        f.write("# GM17 Phase4 Minimal Factor Pilot Evaluation\n\n")
        f.write("This evaluation is post-inference only. The pilot ranking was generated before A019/A021 were read.\n\n")
        f.write("Metrics use center error and axis-aligned proxy IoU. The proxy IoU is not rotated IoU.\n\n")
        f.write(f"Pilot directory: `{pilot_dir}`\n\n")
        f.write("Outputs:\n")
        f.write("- `evaluation_summary.json`\n")
        f.write("- `evaluation_per_target.csv`\n")
        f.write("- `evaluation_condition_groups.csv`\n")

    logger.write(f"Wrote evaluation summary: {pilot_dir / 'evaluation_summary.json'}")
    logger.write(f"Wrote per-target evaluation: {pilot_dir / 'evaluation_per_target.csv'}")
    logger.write(f"Wrote condition grouping: {pilot_dir / 'evaluation_condition_groups.csv'}")
    logger.write("Completed post-inference evaluation without modifying pilot ranking.")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate GM_RM017-only minimal factor pilot output.")
    parser.add_argument("--pilot-dir", required=True, help="Pilot output directory containing pilot CSVs and manifest")
    parser.add_argument("--a019", default=str(A019_DEFAULT), help="Path to A019 final_gt_working.csv")
    parser.add_argument("--a021", default=str(A021_DEFAULT), help="Path to A021 visibility_condition_working.csv")
    parser.add_argument("--log-root", default=str(LOG_ROOT_DEFAULT), help="Workspace log root")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
