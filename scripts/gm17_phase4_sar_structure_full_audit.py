#!/usr/bin/env python
"""GM17 Phase4S SAR structure factor full audit.

This is a diagnostic separability audit. It does not create v3 ranking, does not
create a structure-only selected output, and does not tune thresholds or train
weights. A019/A021 are read only after existing v1/v2 outputs exist, for path
resolution, evaluation context, and failure grouping.
"""

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


DEFAULT_V1_DIR = "output/gm17_phase4_minimal_factor_pilot_20260628_110447"
DEFAULT_V1_DIAGNOSTICS = "output/gm17_phase4_minimal_factor_pilot_v1_diagnostics_20260628_113224"
DEFAULT_V2_DIR = "output/gm17_phase4_minimal_factor_pilot_v2_20260628_171204"
DEFAULT_SCOUT_DIR = "output/gm17_phase4_sar_structure_evidence_scout_20260628_183122"
DEFAULT_A019 = "output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv"
DEFAULT_A021 = "output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv"
DEFAULT_OUTPUT_ROOT = "output"
DEFAULT_LOG_ROOT = "logs"

KEY_COLS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
TARGET_PATH_KEY_COLS = ["target_identity", "scene", "sar_frame_num"]
PRIMARY_ROLES = ["rank1_v1", "best_proxy", "best_center", "v2a_rank1", "v2b_rank1", "v2c_rank1"]
AUDIT_ROLES = PRIMARY_ROLES + ["v1_top1_to_top5", "v1_top6_to_top20"]
PANEL_ROLES = PRIMARY_ROLES
COMPARISONS = [
    ("rank1_v1_vs_best_proxy", "rank1_v1", "best_proxy"),
    ("rank1_v1_vs_best_center", "rank1_v1", "best_center"),
    ("v2a_rank1_vs_best_proxy", "v2a_rank1", "best_proxy"),
    ("v2b_rank1_vs_best_proxy", "v2b_rank1", "best_proxy"),
    ("v2c_rank1_vs_best_proxy", "v2c_rank1", "best_proxy"),
]
BASE_FEATURES = list(scout.FEATURE_COLUMNS)
AUDIT_FEATURES = BASE_FEATURES + ["optional_local_contrast", "optional_peak_inside_box_flag"]
PRIOR_PROMISING = ["edge_spillover_ratio", "inside_energy_fraction", "box_to_background_ratio"]
PRIOR_UNSTABLE = ["box_sum_intensity", "box_max_intensity", "peak_to_background_ratio"]
DISPLAY_RISK_FEATURES = {"box_max_intensity", "peak_to_background_ratio"}
HIGHER_BETTER = dict(scout.HIGHER_BETTER)
HIGHER_BETTER.update(
    {
        "optional_local_contrast": True,
        "optional_peak_inside_box_flag": True,
    }
)
ROLE_COLORS = {
    "rank1_v1": "#d62728",
    "best_proxy": "#2ca02c",
    "best_center": "#1f77b4",
    "v2a_rank1": "#9467bd",
    "v2b_rank1": "#ff7f0e",
    "v2c_rank1": "#8c564b",
    "v1_top1_to_top5": "#7f7f7f",
    "v1_top6_to_top20": "#bcbd22",
}
EPS = 1e-6
REPAIR_NOTES: list[str] = [
    "Repair 1: fixed panel queue status-column merge so an existing target-level "
    "image_read_status/path_status is preserved without pandas suffixing. This did "
    "not change inputs, feature definitions, thresholds, ranking, or audit logic."
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GM17 Phase4S SAR structure full audit.")
    parser.add_argument("--v1-dir", default=DEFAULT_V1_DIR)
    parser.add_argument("--v1-diagnostics", default=DEFAULT_V1_DIAGNOSTICS)
    parser.add_argument("--v2-dir", default=DEFAULT_V2_DIR)
    parser.add_argument("--scout-dir", default=DEFAULT_SCOUT_DIR)
    parser.add_argument("--a019", default=DEFAULT_A019)
    parser.add_argument("--a021", default=DEFAULT_A021)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--log-root", default=DEFAULT_LOG_ROOT)
    parser.add_argument("--max-panels", type=int, default=60)
    return parser.parse_args()


class RunPaths:
    def __init__(self, output_root: str, log_root: str) -> None:
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(output_root) / f"gm17_phase4_sar_structure_full_audit_{self.timestamp}"
        self.figures_dir = self.output_dir / "figures"
        self.panels_dir = self.output_dir / "panels"
        self.log_path = Path(log_root) / f"gm17_phase4_sar_structure_full_audit_{self.timestamp}.log"
        self.summary_md_path = Path("docs") / f"gm17_phase4_sar_structure_full_audit_summary_{self.timestamp}.md"
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        self.panels_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.summary_md_path.parent.mkdir(parents=True, exist_ok=True)


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


def finite_or_nan(value: Any) -> float:
    number = safe_float(value)
    return number if math.isfinite(number) else math.nan


def bool_value(value: Any) -> bool:
    return scout.bool_value(value)


def safe_int_text(value: Any) -> str:
    return scout.safe_int_text(value)


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    logging.info("Reading %s", path)
    return pd.read_csv(path, **kwargs)


def key_cols_as_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in KEY_COLS:
        if col in out.columns:
            if col == "sar_frame_num":
                out[col] = out[col].map(safe_int_text)
            else:
                out[col] = out[col].map(norm_str)
    return out


def path_key_cols_as_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in TARGET_PATH_KEY_COLS:
        if col in out.columns:
            if col == "sar_frame_num":
                out[col] = out[col].map(safe_int_text)
            else:
                out[col] = out[col].map(norm_str)
    return out


def key_from_record(record: pd.Series | dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        norm_str(record.get("target_identity", "")),
        norm_str(record.get("scene", "")),
        safe_int_text(record.get("sar_frame_num", "")),
        norm_str(record.get("gm17_track_id", "")),
    )


def feature_key(record: pd.Series | dict[str, Any]) -> str:
    return "|".join([*key_from_record(record), norm_str(record.get("candidate_id", ""))])


def read_scout_reference(scout_dir: Path) -> tuple[dict[str, Any], pd.DataFrame]:
    summary_path = scout_dir / "scout_summary.json"
    comparison_path = scout_dir / "scout_role_comparison_summary.csv"
    summary: dict[str, Any] = {}
    comparison = pd.DataFrame()
    if summary_path.exists():
        with summary_path.open("r", encoding="utf-8") as f:
            summary = json.load(f)
    if comparison_path.exists():
        comparison = pd.read_csv(comparison_path)
    return summary, comparison


def build_v2_wide(v2_eval: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    keyed = key_cols_as_text(v2_eval)
    for key, group in keyed.groupby(KEY_COLS, dropna=False):
        record = dict(zip(KEY_COLS, key))
        for _, row in group.iterrows():
            variant = norm_str(row.get("variant", ""))
            if not variant:
                continue
            record[f"{variant}_candidate_id"] = norm_str(row.get("candidate_id", ""))
            record[f"{variant}_center_error"] = finite_or_nan(row.get("center_error"))
            record[f"{variant}_proxy_iou"] = finite_or_nan(row.get("axis_aligned_proxy_iou"))
            record[f"{variant}_rank1_is_best_proxy"] = bool_value(row.get("rank1_is_best_proxy"))
            record[f"{variant}_rank1_is_best_center"] = bool_value(row.get("rank1_is_best_center"))
        rows.append(record)
    return pd.DataFrame(rows)


def build_targets(v1_eval: pd.DataFrame, v1_diag: pd.DataFrame, v2_wide: pd.DataFrame, a021: pd.DataFrame) -> pd.DataFrame:
    base = key_cols_as_text(v1_eval).copy()
    base = base.rename(columns={"candidate_id": "rank1_candidate_id"})
    keep_cols = [
        *KEY_COLS,
        "rank1_candidate_id",
        "pilot_rank",
        "center_error",
        "axis_aligned_proxy_iou",
        "best_proxy_candidate_id",
        "best_proxy_pilot_rank",
        "best_proxy_iou",
        "best_proxy_center_error",
        "best_center_candidate_id",
        "best_center_pilot_rank",
        "best_center_error",
        "best_center_proxy_iou",
        "condition_type",
        "condition_status",
        "truncation_degree",
        "occlusion_degree",
    ]
    base = base[[col for col in keep_cols if col in base.columns]].copy()
    base = base.rename(
        columns={
            "center_error": "rank1_center_error",
            "axis_aligned_proxy_iou": "rank1_proxy_iou",
        }
    )

    diag_cols = [
        *KEY_COLS,
        "temporal_zero_candidate_count",
        "rank1_is_best_proxy",
        "rank1_is_best_center",
        "best_proxy_in_top5",
        "best_proxy_in_top20",
        "best_center_in_top5",
        "best_center_in_top20",
    ]
    diag = key_cols_as_text(v1_diag)[[col for col in diag_cols if col in v1_diag.columns]].copy()
    targets = base.merge(diag, on=KEY_COLS, how="left")
    targets = targets.merge(key_cols_as_text(v2_wide), on=KEY_COLS, how="left")

    if not a021.empty:
        a021_norm = path_key_cols_as_text(a021)
        a021_cols = [
            "target_identity",
            "scene",
            "sar_frame_num",
            "condition_type",
            "condition_status",
            "truncation_degree",
            "occlusion_degree",
        ]
        a021_keep = a021_norm[[col for col in a021_cols if col in a021_norm.columns]].copy()
        a021_keep = a021_keep.rename(
            columns={
                "condition_type": "a021_condition_type",
                "condition_status": "a021_condition_status",
                "truncation_degree": "a021_truncation_degree",
                "occlusion_degree": "a021_occlusion_degree",
            }
        )
        counts = (
            a021_norm.groupby(TARGET_PATH_KEY_COLS, dropna=False)
            .size()
            .reset_index(name="a021_match_count")
        )
        targets = targets.merge(a021_keep.drop_duplicates(TARGET_PATH_KEY_COLS), on=TARGET_PATH_KEY_COLS, how="left")
        targets = targets.merge(counts, on=TARGET_PATH_KEY_COLS, how="left")
    else:
        targets["a021_match_count"] = 0

    targets["rank1_proxy_iou_num"] = targets["rank1_proxy_iou"].map(finite_or_nan)
    targets["best_proxy_iou_num"] = targets["best_proxy_iou"].map(finite_or_nan)
    targets["rank1_center_error_num"] = targets["rank1_center_error"].map(finite_or_nan)
    targets["best_center_error_num"] = targets["best_center_error"].map(finite_or_nan)
    targets["best_proxy_rank_num"] = targets["best_proxy_pilot_rank"].map(finite_or_nan)
    targets["temporal_zero_candidate_count_num"] = targets["temporal_zero_candidate_count"].map(finite_or_nan)
    targets["rank1_is_best_proxy_bool"] = targets["rank1_is_best_proxy"].map(bool_value)
    targets["rank1_is_best_center_bool"] = targets["rank1_is_best_center"].map(bool_value)
    targets["proxy_iou_gap_best_minus_rank1"] = targets["best_proxy_iou_num"] - targets["rank1_proxy_iou_num"]
    targets["center_gap_rank1_minus_best_center"] = targets["rank1_center_error_num"] - targets["best_center_error_num"]

    cond = targets["condition_type"].map(lambda x: norm_str(x).lower())
    trunc = targets["truncation_degree"].map(lambda x: norm_str(x).lower())
    occ = targets["occlusion_degree"].map(lambda x: norm_str(x).lower())
    temporal_zero_bad = (
        (targets["temporal_zero_candidate_count_num"] > 0)
        & (~targets["rank1_is_best_proxy_bool"])
        & (targets["proxy_iou_gap_best_minus_rank1"] > 0)
    )
    truncated_occluded = cond.eq("truncated+occluded") | (trunc.isin(["moderate", "severe"]) & occ.isin(["mild", "moderate", "severe"]))
    success = targets["rank1_is_best_proxy_bool"] | targets["rank1_is_best_center_bool"]
    deep_proxy = (~targets["rank1_is_best_proxy_bool"]) & (targets["best_proxy_rank_num"] > 50)
    targets["case_group"] = np.select(
        [
            temporal_zero_bad,
            deep_proxy,
            truncated_occluded,
            success,
        ],
        [
            "temporal_zero_bad",
            "best_proxy_deep_failure",
            "truncated_occluded_risk",
            "success_control",
        ],
        default="general_audit",
    )
    targets["target_audit_id"] = [f"T{i:03d}" for i in range(1, len(targets) + 1)]
    return targets


def find_sar_path_column(a019: pd.DataFrame) -> str:
    if "sar_pseudocolor_path" in a019.columns:
        return "sar_pseudocolor_path"
    candidates: list[tuple[int, str]] = []
    for col in a019.columns:
        lower = col.lower()
        score = 0
        if "sar" in lower:
            score += 2
        if "path" in lower:
            score += 2
        if "image" in lower or "img" in lower:
            score += 1
        if score:
            candidates.append((score, col))
    if not candidates:
        return ""
    candidates.sort(reverse=True)
    return candidates[0][1]


def resolve_sar_paths(targets: pd.DataFrame, a019: pd.DataFrame, path_col: str) -> pd.DataFrame:
    if a019.empty or not path_col:
        rows = []
        for _, target in targets.iterrows():
            rows.append(
                {
                    "target_audit_id": target["target_audit_id"],
                    "target_identity": target["target_identity"],
                    "scene": target["scene"],
                    "sar_frame_num": target["sar_frame_num"],
                    "gm17_track_id": target["gm17_track_id"],
                    "a019_match_count": 0,
                    "sar_path_field": path_col,
                    "resolved_path": "",
                    "path_exists": False,
                    "path_status": "no_a019_path_field",
                    "feature_source_image_type": "unresolved",
                    "image_read_status": "not_attempted",
                }
            )
        return pd.DataFrame(rows)

    a019_norm = path_key_cols_as_text(a019)
    grouped = {key: group for key, group in a019_norm.groupby(TARGET_PATH_KEY_COLS, dropna=False)}
    rows: list[dict[str, Any]] = []
    for _, target in targets.iterrows():
        key = (
            norm_str(target.get("target_identity", "")),
            norm_str(target.get("scene", "")),
            safe_int_text(target.get("sar_frame_num", "")),
        )
        matches = grouped.get(key, pd.DataFrame())
        resolved_path = ""
        status = "no_a019_match"
        exists = False
        if not matches.empty:
            path_value = norm_str(matches.iloc[0].get(path_col, ""))
            if path_value:
                resolved_path = path_value
                exists = Path(path_value).exists()
                status = "a019_path_exists" if exists else "a019_path_missing"
            else:
                status = "a019_match_empty_path"
        source_type = "diagnostic_on_display_image" if "pseudocolor" in path_col.lower() else "sar_image"
        rows.append(
            {
                "target_audit_id": target["target_audit_id"],
                "target_identity": target["target_identity"],
                "scene": target["scene"],
                "sar_frame_num": target["sar_frame_num"],
                "gm17_track_id": target["gm17_track_id"],
                "a019_match_count": int(len(matches)),
                "sar_path_field": path_col,
                "resolved_path": resolved_path,
                "path_exists": bool(exists),
                "path_status": status,
                "feature_source_image_type": source_type if exists else "unresolved",
                "image_read_status": "not_attempted",
            }
        )
    return pd.DataFrame(rows)


def build_candidate_index(df: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    if "candidate_id" not in df.columns:
        return out
    keyed = key_cols_as_text(df)
    for record in keyed.to_dict("records"):
        cid = norm_str(record.get("candidate_id", ""))
        if not cid:
            continue
        out.setdefault(cid, []).append(record)
    return out


def lookup_candidate(candidate_id: str, target: pd.Series, indices: list[dict[str, list[dict[str, Any]]]]) -> dict[str, Any] | None:
    cid = norm_str(candidate_id)
    if not cid:
        return None
    target_key = key_from_record(target)
    for index in indices:
        records = index.get(cid, [])
        if not records:
            continue
        for record in records:
            if key_from_record(record) == target_key:
                return record
        return records[0]
    return None


def geometry_from_candidate(record: dict[str, Any] | None) -> dict[str, Any]:
    return {col: finite_or_nan(record.get(col)) if record else math.nan for col in ["cx", "cy", "w", "h", "heading", "r", "az", "cross"]}


def target_mask(df: pd.DataFrame, target: pd.Series) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for col, value in zip(KEY_COLS, key_from_record(target)):
        mask &= df[col].astype(str).eq(value)
    return mask


def v2_variant_row(v2_eval: pd.DataFrame, target: pd.Series, variant: str) -> dict[str, Any] | None:
    rows = v2_eval[target_mask(v2_eval, target) & v2_eval["variant"].astype(str).eq(variant)]
    if rows.empty:
        return None
    return rows.iloc[0].to_dict()


def role_metrics(target: pd.Series, role: str, v2_row: dict[str, Any] | None = None, candidate_row: dict[str, Any] | None = None) -> dict[str, Any]:
    if role == "rank1_v1":
        return {
            "candidate_rank": finite_or_nan(target.get("pilot_rank", 1)),
            "proxy_iou": finite_or_nan(target.get("rank1_proxy_iou")),
            "center_error": finite_or_nan(target.get("rank1_center_error")),
            "role_is_best_proxy": bool_value(target.get("rank1_is_best_proxy")),
            "role_is_best_center": bool_value(target.get("rank1_is_best_center")),
        }
    if role == "best_proxy":
        return {
            "candidate_rank": finite_or_nan(target.get("best_proxy_pilot_rank")),
            "proxy_iou": finite_or_nan(target.get("best_proxy_iou")),
            "center_error": finite_or_nan(target.get("best_proxy_center_error")),
            "role_is_best_proxy": True,
            "role_is_best_center": False,
        }
    if role == "best_center":
        return {
            "candidate_rank": finite_or_nan(target.get("best_center_pilot_rank")),
            "proxy_iou": finite_or_nan(target.get("best_center_proxy_iou")),
            "center_error": finite_or_nan(target.get("best_center_error")),
            "role_is_best_proxy": False,
            "role_is_best_center": True,
        }
    if role.startswith("v2") and v2_row:
        variant = role.split("_")[0]
        return {
            "candidate_rank": finite_or_nan(v2_row.get(f"{variant}_rank", 1)),
            "proxy_iou": finite_or_nan(v2_row.get("axis_aligned_proxy_iou")),
            "center_error": finite_or_nan(v2_row.get("center_error")),
            "role_is_best_proxy": bool_value(v2_row.get("rank1_is_best_proxy")),
            "role_is_best_center": bool_value(v2_row.get("rank1_is_best_center")),
        }
    return {
        "candidate_rank": finite_or_nan(candidate_row.get("pilot_rank")) if candidate_row else math.nan,
        "proxy_iou": math.nan,
        "center_error": math.nan,
        "role_is_best_proxy": False,
        "role_is_best_center": False,
    }


def build_candidate_roles(targets: pd.DataFrame, v1_ranked: pd.DataFrame, v2_ranked: pd.DataFrame, v2_eval: pd.DataFrame) -> pd.DataFrame:
    v1_index = build_candidate_index(v1_ranked)
    v2_index = build_candidate_index(v2_ranked)
    indices = [v1_index, v2_index]
    rows: list[dict[str, Any]] = []
    v1_grouped = {key: group.sort_values("pilot_rank") for key, group in v1_ranked.groupby(KEY_COLS, dropna=False)}

    for _, target in targets.iterrows():
        target_key = key_from_record(target)
        primary_candidates = {
            "rank1_v1": norm_str(target.get("rank1_candidate_id", "")),
            "best_proxy": norm_str(target.get("best_proxy_candidate_id", "")),
            "best_center": norm_str(target.get("best_center_candidate_id", "")),
        }
        v2_rows: dict[str, dict[str, Any] | None] = {}
        for variant in ["v2a", "v2b", "v2c"]:
            row = v2_variant_row(v2_eval, target, variant)
            v2_rows[f"{variant}_rank1"] = row
            primary_candidates[f"{variant}_rank1"] = norm_str(row.get("candidate_id", "")) if row else ""

        for role in PRIMARY_ROLES:
            cid = primary_candidates.get(role, "")
            v2_row = v2_rows.get(role)
            candidate = lookup_candidate(cid, target, indices)
            if candidate is None and v2_row:
                candidate = v2_row
            out = {
                "target_audit_id": target["target_audit_id"],
                "target_identity": target["target_identity"],
                "scene": target["scene"],
                "sar_frame_num": target["sar_frame_num"],
                "gm17_track_id": target["gm17_track_id"],
                "case_group": target["case_group"],
                "role": role,
                "role_detail": role,
                "candidate_id": cid,
                "is_topk_distribution_role": False,
            }
            out.update(role_metrics(target, role, v2_row=v2_row, candidate_row=candidate))
            out.update(geometry_from_candidate(candidate))
            out["feature_key"] = feature_key(out)
            rows.append(out)

        top_group = v1_grouped.get(target_key, pd.DataFrame())
        if not top_group.empty:
            for _, cand_row in top_group[top_group["pilot_rank"].between(1, 20, inclusive="both")].iterrows():
                rank = int(finite_or_nan(cand_row.get("pilot_rank")))
                role = "v1_top1_to_top5" if rank <= 5 else "v1_top6_to_top20"
                candidate = cand_row.to_dict()
                out = {
                    "target_audit_id": target["target_audit_id"],
                    "target_identity": target["target_identity"],
                    "scene": target["scene"],
                    "sar_frame_num": target["sar_frame_num"],
                    "gm17_track_id": target["gm17_track_id"],
                    "case_group": target["case_group"],
                    "role": role,
                    "role_detail": f"{role}_rank_{rank:02d}",
                    "candidate_id": norm_str(cand_row.get("candidate_id", "")),
                    "is_topk_distribution_role": True,
                }
                out.update(role_metrics(target, role, candidate_row=candidate))
                out.update(geometry_from_candidate(candidate))
                out["feature_key"] = feature_key(out)
                rows.append(out)

    role_df = pd.DataFrame(rows)
    role_df["candidate_duplicate_role_count"] = role_df.groupby("feature_key")["role"].transform("count")
    return role_df


def update_path_report_with_reads(path_report: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, np.ndarray | None]]:
    image_cache: dict[str, np.ndarray | None] = {}
    rows: list[dict[str, Any]] = []
    for record in path_report.to_dict("records"):
        image, status = scout.load_image(record.get("resolved_path", ""))
        record["image_read_status"] = status
        record["image_height"] = image.shape[0] if image is not None else math.nan
        record["image_width"] = image.shape[1] if image is not None else math.nan
        if status != "ok" and record.get("path_exists"):
            record["path_status"] = f"{record.get('path_status')};image_{status}"
        image_cache[record["target_audit_id"]] = image
        rows.append(record)
    return pd.DataFrame(rows), image_cache


def compute_full_features(image: np.ndarray | None, candidate: pd.Series, source_type: str) -> dict[str, Any]:
    out = {feature: math.nan for feature in AUDIT_FEATURES}
    out.update(
        {
            "candidate_box_area_px": math.nan,
            "clipped_box_area_px": math.nan,
            "local_patch_area_px": math.nan,
            "box_clip_fraction": math.nan,
            "local_patch_width": math.nan,
            "local_patch_height": math.nan,
            "feature_source_image_type": source_type,
        }
    )
    base = scout.compute_structure_features(image, candidate)
    out.update(base)
    if image is None:
        out["structure_feature_status"] = "image_unavailable"
        return out

    cx = safe_float(candidate.get("cx"))
    cy = safe_float(candidate.get("cy"))
    w = safe_float(candidate.get("w"))
    h = safe_float(candidate.get("h"))
    heading = safe_float(candidate.get("heading"))
    if not all(math.isfinite(v) for v in [cx, cy, w, h]) or w <= 0 or h <= 0:
        out["structure_feature_status"] = "invalid_box_geometry"
        return out

    x1, y1, x2, y2 = scout.clipped_bounds(cx, cy, w, h, image.shape, scale=1.0)
    ex1, ey1, ex2, ey2 = scout.clipped_bounds(cx, cy, w, h, image.shape, scale=2.0)
    nominal_area = float(w * h)
    clipped_area = float(max(0, x2 - x1) * max(0, y2 - y1))
    local_area = float(max(0, ex2 - ex1) * max(0, ey2 - ey1))
    out["candidate_box_area_px"] = nominal_area
    out["clipped_box_area_px"] = clipped_area
    out["local_patch_area_px"] = local_area
    out["box_clip_fraction"] = clipped_area / (nominal_area + EPS)
    out["local_patch_width"] = float(max(0, ex2 - ex1))
    out["local_patch_height"] = float(max(0, ey2 - ey1))

    if x2 <= x1 or y2 <= y1 or ex2 <= ex1 or ey2 <= ey1:
        out["structure_feature_status"] = "empty_box_or_local_patch_after_clip"
        return out

    local = image[ey1:ey2, ex1:ex2]
    inner_x1 = max(0, x1 - ex1)
    inner_x2 = min(local.shape[1], x2 - ex1)
    inner_y1 = max(0, y1 - ey1)
    inner_y2 = min(local.shape[0], y2 - ey1)
    if local.size:
        peak_y, peak_x = np.unravel_index(np.argmax(local), local.shape)
        out["optional_peak_inside_box_flag"] = float(inner_x1 <= peak_x < inner_x2 and inner_y1 <= peak_y < inner_y2)
    if math.isfinite(out.get("box_mean_intensity", math.nan)) and math.isfinite(out.get("local_background_mean", math.nan)):
        out["optional_local_contrast"] = out["box_mean_intensity"] - out["local_background_mean"]
    if out.get("structure_feature_status") == "ok_axis_aligned_diagnostic" and source_type == "diagnostic_on_display_image":
        out["structure_feature_status"] = "ok_axis_aligned_diagnostic_on_display_image"
    return out


def compute_structure_feature_table(candidate_roles: pd.DataFrame, path_report: pd.DataFrame, image_cache: dict[str, np.ndarray | None]) -> pd.DataFrame:
    path_by_target = {row["target_audit_id"]: row for row in path_report.to_dict("records")}
    unique_candidates = candidate_roles.drop_duplicates("feature_key").copy()
    rows: list[dict[str, Any]] = []
    role_map = candidate_roles.groupby("feature_key")["role_detail"].apply(lambda s: ";".join(sorted(set(map(str, s))))).to_dict()
    for _, candidate in unique_candidates.iterrows():
        target_id = candidate["target_audit_id"]
        path_info = path_by_target.get(target_id, {})
        features = compute_full_features(
            image_cache.get(target_id),
            candidate,
            norm_str(path_info.get("feature_source_image_type", "unresolved")),
        )
        out = candidate.to_dict()
        out["role_details_all"] = role_map.get(candidate["feature_key"], "")
        out["image_read_status"] = norm_str(path_info.get("image_read_status", "not_attempted"))
        out["sar_image_path"] = norm_str(path_info.get("resolved_path", ""))
        out.update(features)
        rows.append(out)
    return pd.DataFrame(rows)


def join_roles_with_features(candidate_roles: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [
        "feature_key",
        "image_read_status",
        "sar_image_path",
        "structure_feature_status",
        "feature_source_image_type",
        "candidate_box_area_px",
        "clipped_box_area_px",
        "local_patch_area_px",
        "box_clip_fraction",
        *AUDIT_FEATURES,
    ]
    return candidate_roles.merge(features[[col for col in feature_cols if col in features.columns]], on="feature_key", how="left")


def build_role_comparison(role_features: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    target_context = targets[
        [
            "target_audit_id",
            "target_identity",
            "scene",
            "sar_frame_num",
            "gm17_track_id",
            "case_group",
            "condition_type",
            "truncation_degree",
            "occlusion_degree",
        ]
    ].drop_duplicates("target_audit_id")
    rows: list[dict[str, Any]] = []
    primary = role_features[role_features["role"].isin(PRIMARY_ROLES)].copy()
    for target_id, group in primary.groupby("target_audit_id", sort=False):
        by_role = {row["role"]: row for _, row in group.iterrows()}
        context_rows = target_context[target_context["target_audit_id"].eq(target_id)]
        context = context_rows.iloc[0].to_dict() if not context_rows.empty else {"target_audit_id": target_id}
        for comparison, left_role, right_role in COMPARISONS:
            if left_role not in by_role or right_role not in by_role:
                continue
            left = by_role[left_role]
            right = by_role[right_role]
            for feature in AUDIT_FEATURES:
                left_value = finite_or_nan(left.get(feature))
                right_value = finite_or_nan(right.get(feature))
                diff = right_value - left_value if math.isfinite(left_value) and math.isfinite(right_value) else math.nan
                higher_better = HIGHER_BETTER.get(feature, True)
                favorable = bool(diff > 0) if higher_better and math.isfinite(diff) else bool(diff < 0) if math.isfinite(diff) else False
                row = {
                    **context,
                    "comparison": comparison,
                    "left_role": left_role,
                    "right_role": right_role,
                    "feature": feature,
                    "left_candidate_id": left.get("candidate_id", ""),
                    "right_candidate_id": right.get("candidate_id", ""),
                    "left_value": left_value,
                    "right_value": right_value,
                    "right_minus_left": diff,
                    "higher_is_better": higher_better,
                    "right_favorable": favorable,
                    "left_proxy_iou": finite_or_nan(left.get("proxy_iou")),
                    "right_proxy_iou": finite_or_nan(right.get("proxy_iou")),
                    "left_center_error": finite_or_nan(left.get("center_error")),
                    "right_center_error": finite_or_nan(right.get("center_error")),
                }
                rows.append(row)
    return pd.DataFrame(rows)


def robust_scale(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return 1.0
    iqr = float(clean.quantile(0.75) - clean.quantile(0.25))
    if math.isfinite(iqr) and iqr > EPS:
        return iqr
    std = float(clean.std(ddof=0))
    if math.isfinite(std) and std > EPS:
        return std
    return 1.0


def condition_stability_for_feature(comparison: pd.DataFrame, feature: str) -> float:
    rows = comparison[(comparison["comparison"].eq("rank1_v1_vs_best_proxy")) & (comparison["feature"].eq(feature))].copy()
    if rows.empty:
        return math.nan
    values: list[bool] = []
    for _, group in rows.groupby(["condition_type", "truncation_degree", "occlusion_degree"], dropna=False):
        valid = group[pd.to_numeric(group["right_minus_left"], errors="coerce").notna()]
        if len(valid) < 3:
            continue
        higher_better = HIGHER_BETTER.get(feature, True)
        median_diff = float(valid["right_minus_left"].median())
        values.append(median_diff > 0 if higher_better else median_diff < 0)
    return float(np.mean(values)) if values else math.nan


def feature_reliability(role_features: pd.DataFrame, separability: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    sep_by_feature = {row["feature"]: row for _, row in separability.iterrows()}
    total = max(1, len(role_features))
    for feature in AUDIT_FEATURES:
        values = pd.to_numeric(role_features[feature], errors="coerce")
        missing_rate = float(values.isna().mean())
        finite = values[np.isfinite(values)]
        anomaly_rate = 1.0
        if not finite.empty:
            if feature.endswith("ratio"):
                anomaly_rate = float(((finite < 0) | (finite > 100)).mean())
            elif feature.endswith("flag"):
                anomaly_rate = float((~finite.isin([0.0, 1.0])).mean())
            else:
                anomaly_rate = float((finite < 0).mean()) if feature not in {"optional_local_contrast"} else 0.0
        size_corr = corr_abs(values, role_features.get("candidate_box_area_px", pd.Series(index=role_features.index, dtype=float)))
        background_corr = corr_abs(values, role_features.get("local_background_mean", pd.Series(index=role_features.index, dtype=float)))
        sep = sep_by_feature.get(feature, {})
        status = sep.get("recommended_status", "weak")
        rows.append(
            {
                "feature": feature,
                "n_rows": int(total),
                "valid_count": int(values.notna().sum()),
                "missing_rate": missing_rate,
                "anomaly_rate": anomaly_rate,
                "abs_spearman_corr_with_box_area": size_corr,
                "abs_spearman_corr_with_local_background": background_corr,
                "strong_box_size_dependence": bool(math.isfinite(size_corr) and size_corr >= 0.50),
                "strong_background_dependence": bool(math.isfinite(background_corr) and background_corr >= 0.50),
                "display_image_risk": True,
                "recommended_status": status,
                "recommended_for_pilot": bool(status == "promising" and missing_rate <= 0.05 and not (math.isfinite(size_corr) and size_corr >= 0.70)),
            }
        )
    return pd.DataFrame(rows)


def corr_abs(a: pd.Series, b: pd.Series) -> float:
    df = pd.DataFrame({"a": pd.to_numeric(a, errors="coerce"), "b": pd.to_numeric(b, errors="coerce")}).dropna()
    if len(df) < 3:
        return math.nan
    corr = df["a"].corr(df["b"], method="spearman")
    return abs(float(corr)) if math.isfinite(corr) else math.nan


def build_feature_separability(role_comparison: pd.DataFrame, role_features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    primary_pair = role_comparison[role_comparison["comparison"].eq("rank1_v1_vs_best_proxy")].copy()
    for feature in AUDIT_FEATURES:
        feature_rows = primary_pair[primary_pair["feature"].eq(feature)].copy()
        diffs = pd.to_numeric(feature_rows["right_minus_left"], errors="coerce").dropna()
        n_pairs = int(len(diffs))
        higher_better = HIGHER_BETTER.get(feature, True)
        if n_pairs:
            favorable = diffs > 0 if higher_better else diffs < 0
            directional = float(favorable.mean())
            mean_diff = float(diffs.mean())
            median_diff = float(diffs.median())
        else:
            directional = math.nan
            mean_diff = math.nan
            median_diff = math.nan
        scale = robust_scale(role_features[feature]) if feature in role_features.columns else 1.0
        effect = abs(median_diff) / scale if math.isfinite(median_diff) else math.nan
        condition_stability = condition_stability_for_feature(role_comparison, feature)
        if feature in DISPLAY_RISK_FEATURES:
            status = "display-risk"
        elif feature in PRIOR_UNSTABLE or (math.isfinite(directional) and directional < 0.55):
            status = "unstable"
        elif math.isfinite(directional) and directional >= 0.62 and math.isfinite(effect) and effect >= 0.05:
            status = "promising"
        else:
            status = "weak"
        rows.append(
            {
                "feature": feature,
                "n_pairs": n_pairs,
                "mean_best_proxy_minus_rank1": mean_diff,
                "median_best_proxy_minus_rank1": median_diff,
                "directional_consistency": directional,
                "effect_size_robust": effect,
                "condition_stability": condition_stability,
                "recommended_status": status,
                "higher_is_better": higher_better,
                "diagnostic_only_note": "separability audit only; no active scoring threshold",
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["recommended_status", "directional_consistency", "effect_size_robust"],
        ascending=[True, False, False],
    )


def build_condition_group_summary(targets: pd.DataFrame, role_comparison: pd.DataFrame) -> pd.DataFrame:
    target_summary = targets.groupby(["condition_type", "truncation_degree", "occlusion_degree"], dropna=False).agg(
        n_targets=("target_audit_id", "count"),
        mean_rank1_proxy_iou=("rank1_proxy_iou_num", "mean"),
        mean_best_proxy_iou=("best_proxy_iou_num", "mean"),
        median_best_proxy_rank=("best_proxy_rank_num", "median"),
    )
    pair = role_comparison[role_comparison["comparison"].eq("rank1_v1_vs_best_proxy")]
    feature_pieces: list[pd.DataFrame] = []
    for feature in ["edge_spillover_ratio", "inside_energy_fraction", "box_to_background_ratio", "center_to_peak_distance"]:
        part = pair[pair["feature"].eq(feature)].groupby(
            ["condition_type", "truncation_degree", "occlusion_degree"], dropna=False
        ).agg(
            **{
                f"{feature}_n_pairs": ("right_minus_left", "count"),
                f"{feature}_median_diff": ("right_minus_left", "median"),
                f"{feature}_directional_consistency": ("right_favorable", "mean"),
            }
        )
        feature_pieces.append(part)
    out = target_summary
    for part in feature_pieces:
        out = out.join(part, how="left")
    return out.reset_index()


def select_panel_queue(targets: pd.DataFrame, path_report: pd.DataFrame, role_comparison: pd.DataFrame, max_panels: int) -> pd.DataFrame:
    max_panels = max(1, int(max_panels))
    target_df = targets.copy()
    missing_status_cols = [col for col in ["path_status", "image_read_status"] if col not in target_df.columns]
    if missing_status_cols:
        target_df = target_df.merge(
            path_report[["target_audit_id", *missing_status_cols]],
            on="target_audit_id",
            how="left",
        )
    pair = role_comparison[role_comparison["comparison"].eq("rank1_v1_vs_best_proxy")]
    signal = pair[pair["feature"].isin(PRIOR_PROMISING)].groupby("target_audit_id").agg(
        promising_feature_favorable_count=("right_favorable", "sum"),
        promising_feature_pair_count=("right_favorable", "count"),
    )
    target_df = target_df.merge(signal, on="target_audit_id", how="left")
    target_df["promising_feature_favorable_count"] = target_df["promising_feature_favorable_count"].fillna(0)
    target_df["promising_feature_pair_count"] = target_df["promising_feature_pair_count"].fillna(0)
    target_df["feature_disagreement_score"] = (
        target_df["proxy_iou_gap_best_minus_rank1"].fillna(0).abs()
        + (target_df["promising_feature_pair_count"] - target_df["promising_feature_favorable_count"]).fillna(0)
    )

    selections: list[pd.DataFrame] = []
    def add(label: str, frame: pd.DataFrame, limit: int, sort_cols: list[str], ascending: list[bool]) -> None:
        if frame.empty:
            return
        view = frame.sort_values(sort_cols, ascending=ascending).head(limit).copy()
        view["panel_queue_case_type"] = label
        selections.append(view)

    add(
        "path_or_patch_anomaly",
        target_df[~target_df["image_read_status"].eq("ok")],
        10,
        ["target_audit_id"],
        [True],
    )
    add(
        "strong_failure",
        target_df[~target_df["rank1_is_best_proxy_bool"]],
        15,
        ["proxy_iou_gap_best_minus_rank1", "best_proxy_rank_num"],
        [False, False],
    )
    add(
        "truncated_occluded",
        target_df[target_df["condition_type"].astype(str).str.lower().eq("truncated+occluded")],
        12,
        ["proxy_iou_gap_best_minus_rank1"],
        [False],
    )
    add(
        "feature_disagreement",
        target_df,
        12,
        ["feature_disagreement_score"],
        [False],
    )
    add(
        "strong_success",
        target_df[target_df["rank1_is_best_proxy_bool"] | target_df["rank1_is_best_center_bool"]],
        10,
        ["rank1_proxy_iou_num"],
        [False],
    )
    add(
        "representative_normal",
        target_df[target_df["condition_type"].astype(str).str.lower().isin(["none", "normal", ""])],
        10,
        ["target_audit_id"],
        [True],
    )

    if selections:
        queue = pd.concat(selections, ignore_index=True)
    else:
        queue = target_df.copy()
        queue["panel_queue_case_type"] = "fallback"
    queue = queue.drop_duplicates("target_audit_id", keep="first").head(max_panels).copy()
    if len(queue) < min(max_panels, 40):
        fill = target_df[~target_df["target_audit_id"].isin(queue["target_audit_id"])].copy()
        fill = fill.sort_values(["proxy_iou_gap_best_minus_rank1", "target_audit_id"], ascending=[False, True])
        fill["panel_queue_case_type"] = "coverage_fill"
        queue = pd.concat([queue, fill], ignore_index=True).drop_duplicates("target_audit_id", keep="first").head(max_panels)
    queue["panel_queue_rank"] = range(1, len(queue) + 1)
    return queue


def compact_candidate_id(candidate_id: str) -> str:
    text = norm_str(candidate_id)
    if len(text) <= 18:
        return text
    return text[:9] + "..." + text[-6:]


def draw_rect(ax: plt.Axes, row: pd.Series, color: str, label: str) -> None:
    cx, cy, w, h = (safe_float(row.get(col)) for col in ["cx", "cy", "w", "h"])
    if not all(math.isfinite(v) for v in [cx, cy, w, h]) or w <= 0 or h <= 0:
        return
    rect = Rectangle((cx - w / 2.0, cy - h / 2.0), w, h, fill=False, edgecolor=color, linewidth=1.8)
    ax.add_patch(rect)
    ax.text(
        cx - w / 2.0,
        cy - h / 2.0,
        label,
        color=color,
        fontsize=7,
        bbox={"facecolor": "black", "alpha": 0.45, "pad": 1, "edgecolor": "none"},
    )


def make_panel(target_id: str, image: np.ndarray | None, role_features: pd.DataFrame, out_dir: Path) -> str:
    if image is None:
        return ""
    primary = role_features[role_features["role"].isin(PANEL_ROLES)].copy()
    if primary.empty:
        return ""
    fig = plt.figure(figsize=(15, 9), dpi=140)
    grid = fig.add_gridspec(2, 4, width_ratios=[2.2, 1, 1, 1], height_ratios=[1, 1])
    ax_main = fig.add_subplot(grid[:, 0])
    ax_main.imshow(image, cmap="gray", vmin=0, vmax=1)
    ax_main.set_title(f"{target_id} overview")
    ax_main.set_axis_off()
    for role in PANEL_ROLES:
        rows = primary[primary["role"].eq(role)]
        if rows.empty:
            continue
        row = rows.iloc[0]
        label = f"{role}\n{compact_candidate_id(row.get('candidate_id', ''))}"
        draw_rect(ax_main, row, ROLE_COLORS.get(role, "#222222"), label)

    for idx, role in enumerate(PANEL_ROLES):
        ax = fig.add_subplot(grid[idx // 3, idx % 3 + 1])
        rows = primary[primary["role"].eq(role)]
        if rows.empty:
            ax.set_axis_off()
            continue
        row = rows.iloc[0]
        cx, cy, w, h = (safe_float(row.get(col)) for col in ["cx", "cy", "w", "h"])
        if not all(math.isfinite(v) for v in [cx, cy, w, h]) or w <= 0 or h <= 0:
            ax.set_title(f"{role}: invalid box", fontsize=8)
            ax.set_axis_off()
            continue
        x1, y1, x2, y2 = scout.clipped_bounds(cx, cy, w, h, image.shape, scale=2.3)
        patch = image[y1:y2, x1:x2]
        ax.imshow(patch, cmap="gray", vmin=0, vmax=1)
        local = row.copy()
        local["cx"] = cx - x1
        local["cy"] = cy - y1
        draw_rect(ax, local, ROLE_COLORS.get(role, "#222222"), role)
        title = (
            f"{role} {compact_candidate_id(row.get('candidate_id', ''))}\n"
            f"IoU={safe_float(row.get('proxy_iou')):.3f} "
            f"err={safe_float(row.get('center_error')):.1f} "
            f"rank={safe_float(row.get('candidate_rank')):.0f}"
        )
        ax.set_title(title, fontsize=7, pad=2)
        ax.set_axis_off()
    fig.suptitle("Phase4S full audit panel: diagnostic only, no active scoring", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95], h_pad=2.0, w_pad=1.5)
    out_path = out_dir / f"{target_id}_full_audit_panel.png"
    fig.savefig(out_path)
    plt.close(fig)
    return str(out_path)


def make_panels(queue: pd.DataFrame, role_features: pd.DataFrame, image_cache: dict[str, np.ndarray | None], panels_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, item in queue.iterrows():
        target_id = item["target_audit_id"]
        path = make_panel(target_id, image_cache.get(target_id), role_features[role_features["target_audit_id"].eq(target_id)], panels_dir)
        rows.append({"target_audit_id": target_id, "panel_path": path, "panel_generated": bool(path)})
    return queue.merge(pd.DataFrame(rows), on="target_audit_id", how="left")


def make_boxplot(role_features: pd.DataFrame, feature: str, output_path: Path) -> None:
    data: list[np.ndarray] = []
    labels: list[str] = []
    for role in AUDIT_ROLES:
        values = pd.to_numeric(role_features.loc[role_features["role"].eq(role), feature], errors="coerce").dropna().to_numpy()
        if values.size:
            data.append(values)
            labels.append(role)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    if data:
        ax.boxplot(data, tick_labels=labels, showfliers=False)
        ax.tick_params(axis="x", rotation=30)
        ax.set_ylabel(feature)
    else:
        ax.text(0.5, 0.5, "No valid feature values", ha="center", va="center")
        ax.set_axis_off()
    ax.set_title(f"Full audit role distribution: {feature}")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def make_feature_signal_bar(separability: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    if separability.empty:
        ax.text(0.5, 0.5, "No separability rows", ha="center", va="center")
        ax.set_axis_off()
    else:
        plot = separability.copy()
        plot["signal"] = plot["directional_consistency"].fillna(0) * plot["effect_size_robust"].fillna(0)
        plot = plot.sort_values("signal", ascending=True).tail(12)
        colors = ["#2ca02c" if s == "promising" else "#ff7f0e" if s == "weak" else "#d62728" for s in plot["recommended_status"]]
        ax.barh(plot["feature"], plot["signal"], color=colors)
        ax.set_xlabel("directional consistency x robust effect size")
    ax.set_title("Full audit diagnostic feature signal")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def make_condition_heatmap(role_comparison: pd.DataFrame, output_path: Path) -> None:
    pair = role_comparison[role_comparison["comparison"].eq("rank1_v1_vs_best_proxy")]
    features = ["edge_spillover_ratio", "inside_energy_fraction", "box_to_background_ratio", "center_to_peak_distance"]
    rows = []
    labels = []
    for key, group in pair.groupby(["condition_type", "truncation_degree", "occlusion_degree"], dropna=False):
        label = "/".join(norm_str(v) for v in key)
        labels.append(label)
        vals = []
        for feature in features:
            f = group[group["feature"].eq(feature)]
            vals.append(float(f["right_favorable"].mean()) if not f.empty else math.nan)
        rows.append(vals)
    matrix = np.array(rows, dtype=float) if rows else np.empty((0, len(features)))
    fig, ax = plt.subplots(figsize=(10, max(4, 0.35 * max(1, len(labels)))), dpi=140)
    if matrix.size:
        im = ax.imshow(matrix, aspect="auto", vmin=0, vmax=1, cmap="viridis")
        ax.set_xticks(np.arange(len(features)))
        ax.set_xticklabels(features, rotation=30, ha="right")
        ax.set_yticks(np.arange(len(labels)))
        ax.set_yticklabels(labels, fontsize=7)
        fig.colorbar(im, ax=ax, label="directional consistency")
    else:
        ax.text(0.5, 0.5, "No condition feature rows", ha="center", va="center")
        ax.set_axis_off()
    ax.set_title("Condition-wise feature stability, best_proxy vs rank1_v1")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def make_missing_rate_bar(reliability: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    plot = reliability.sort_values("missing_rate", ascending=True)
    ax.barh(plot["feature"], plot["missing_rate"], color="#4c78a8")
    ax.set_xlabel("missing rate")
    ax.set_title("Full audit feature missing rate")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def make_panel_queue_bar(panel_queue: pd.DataFrame, output_path: Path) -> None:
    counts = panel_queue["panel_queue_case_type"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    ax.bar(counts.index, counts.values, color="#72b7b2")
    ax.tick_params(axis="x", rotation=30)
    ax.set_ylabel("case count")
    ax.set_title("Panel review queue case types")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def make_figures(role_features: pd.DataFrame, separability: pd.DataFrame, role_comparison: pd.DataFrame, reliability: pd.DataFrame, panel_queue: pd.DataFrame, figures_dir: Path) -> list[str]:
    figure_paths: list[str] = []
    path = figures_dir / "full_feature_signal_bar.png"
    make_feature_signal_bar(separability, path)
    figure_paths.append(str(path))
    for feature, name in [
        ("box_to_background_ratio", "full_role_box_to_background_ratio_boxplot.png"),
        ("inside_energy_fraction", "full_role_inside_energy_fraction_boxplot.png"),
        ("edge_spillover_ratio", "full_role_edge_spillover_ratio_boxplot.png"),
        ("center_to_peak_distance", "full_center_to_peak_distance_boxplot.png"),
    ]:
        path = figures_dir / name
        make_boxplot(role_features, feature, path)
        figure_paths.append(str(path))
    path = figures_dir / "full_condition_feature_stability_heatmap.png"
    make_condition_heatmap(role_comparison, path)
    figure_paths.append(str(path))
    path = figures_dir / "full_feature_missing_rate_bar.png"
    make_missing_rate_bar(reliability, path)
    figure_paths.append(str(path))
    path = figures_dir / "full_panel_queue_case_type_bar.png"
    make_panel_queue_bar(panel_queue, path)
    figure_paths.append(str(path))
    return figure_paths


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


def support_decision(path_success_rate: float, feature_valid_rate: float, separability: pd.DataFrame, panel_count: int) -> tuple[bool, bool, str]:
    needs_manifest = path_success_rate < 0.90
    promising = separability[separability["recommended_status"].eq("promising")]
    stable_count = int((promising["directional_consistency"] >= 0.60).sum()) if not promising.empty else 0
    support = (not needs_manifest) and feature_valid_rate >= 0.90 and stable_count >= 2 and panel_count >= 40
    if needs_manifest:
        reason = "SAR image read success is below 90%; repair path/patch manifest before any pilot."
    elif not support:
        reason = "Feature signal is not yet stable enough for structure-only fixed pilot."
    else:
        reason = "Full audit supports writing a pre-registered structure-only fixed pilot spec, with display-image risk noted."
    return support, needs_manifest, reason


def write_summary_json(
    run_paths: RunPaths,
    args: argparse.Namespace,
    targets: pd.DataFrame,
    features: pd.DataFrame,
    path_report: pd.DataFrame,
    separability: pd.DataFrame,
    condition_summary: pd.DataFrame,
    reliability: pd.DataFrame,
    panel_queue: pd.DataFrame,
    figure_paths: list[str],
    support: bool,
    needs_manifest: bool,
    decision_reason: str,
    scout_summary: dict[str, Any],
) -> None:
    image_success = int(path_report["image_read_status"].eq("ok").sum())
    path_success_rate = image_success / max(1, len(path_report))
    feature_valid = features["structure_feature_status"].astype(str).str.startswith("ok_")
    feature_valid_rate = float(feature_valid.mean()) if len(features) else 0.0
    promising = separability[separability["recommended_status"].eq("promising")].sort_values(
        ["directional_consistency", "effect_size_robust"], ascending=[False, False]
    )
    weak = separability[~separability["recommended_status"].eq("promising")].sort_values(
        ["recommended_status", "directional_consistency"], ascending=[True, True]
    )
    payload = {
        "run_timestamp": run_paths.timestamp,
        "input_paths": {
            "v1_dir": args.v1_dir,
            "v1_diagnostics": args.v1_diagnostics,
            "v2_dir": args.v2_dir,
            "scout_dir": args.scout_dir,
            "a019": args.a019,
            "a021": args.a021,
        },
        "output_paths": {
            "output_dir": str(run_paths.output_dir),
            "figures_dir": str(run_paths.figures_dir),
            "panels_dir": str(run_paths.panels_dir),
            "log_path": str(run_paths.log_path),
            "markdown_summary": str(run_paths.summary_md_path),
        },
        "target_count": int(len(targets)),
        "unique_candidate_count": int(len(features)),
        "sar_image_read_success_rate": path_success_rate,
        "sar_image_read_success_count": image_success,
        "structure_feature_valid_rate": feature_valid_rate,
        "panel_generated_count": int(panel_queue["panel_generated"].sum()) if "panel_generated" in panel_queue else 0,
        "top_promising_features": promising.head(5).to_dict("records"),
        "weak_or_unstable_features": weak.head(8).to_dict("records"),
        "best_proxy_vs_rank1_overall_differences": separability.to_dict("records"),
        "condition_wise_stability": condition_summary.to_dict("records"),
        "support_structure_only_fixed_pilot": bool(support),
        "needs_sar_path_patch_manifest_first": bool(needs_manifest),
        "decision_reason": decision_reason,
        "scout_reference_promising_features": [x.get("feature") for x in scout_summary.get("promising_sar_structure_features", [])],
        "scout_reference_unstable_features": [x.get("feature") for x in scout_summary.get("unstable_or_not_recommended_features", [])],
        "repair_notes": REPAIR_NOTES,
        "leakage_boundary_statement": (
            "Diagnostic separability audit only. No v3 ranking, no structure-only selected output, "
            "no threshold tuning, no training, no calibration, no A021 inference input, no GT-tuned rules, "
            "and no candidate_source/source sorting."
        ),
        "figure_paths": figure_paths,
    }
    with (run_paths.output_dir / "full_structure_audit_summary.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_markdown_summary(
    run_paths: RunPaths,
    args: argparse.Namespace,
    targets: pd.DataFrame,
    features: pd.DataFrame,
    path_report: pd.DataFrame,
    separability: pd.DataFrame,
    reliability: pd.DataFrame,
    condition_summary: pd.DataFrame,
    panel_queue: pd.DataFrame,
    support: bool,
    needs_manifest: bool,
    decision_reason: str,
    scout_summary: dict[str, Any],
    figure_paths: list[str],
) -> None:
    image_success = int(path_report["image_read_status"].eq("ok").sum())
    path_success_rate = image_success / max(1, len(path_report))
    feature_valid = features["structure_feature_status"].astype(str).str.startswith("ok_")
    feature_valid_rate = float(feature_valid.mean()) if len(features) else 0.0
    promising = separability[separability["recommended_status"].eq("promising")].sort_values(
        ["directional_consistency", "effect_size_robust"], ascending=[False, False]
    )
    unstable = separability[separability["recommended_status"].isin(["unstable", "display-risk"])].copy()
    scout_promising = [x.get("feature") for x in scout_summary.get("promising_sar_structure_features", [])]
    full_promising = list(promising["feature"].head(5))
    consistent = [f for f in scout_promising if f in full_promising]
    text = f"""# GM17 Phase4S SAR Structure Full Audit Summary {run_paths.timestamp}

## 1. Purpose

This run grounds `sar_structure_factor` with full GM_RM017 evidence. It extracts SAR structure features over all targets and audits whether the feature directions separate existing candidate roles.

## 2. Why Phase4S Instead Of V3 Table Tuning

The v1/v2 results show enough A001 candidate coverage but unstable table-level geometry/temporal promotion of the best candidate. The next useful evidence is SAR patch structure, not another A001/A005 field-rule search.

## 3. Inputs And Outputs

- V1 pilot: `{args.v1_dir}`
- V1 diagnostics: `{args.v1_diagnostics}`
- V2 pilot: `{args.v2_dir}`
- Scout reference: `{args.scout_dir}`
- A019 path/evaluation context: `{args.a019}`
- A021 post-inference grouping context: `{args.a021}`
- Output directory: `{run_paths.output_dir}`
- Log: `{run_paths.log_path}`
- Summary JSON: `{run_paths.output_dir / 'full_structure_audit_summary.json'}`

## 4. SAR Path Resolution

- Targets: {len(targets)}
- SAR image read success: {image_success}
- SAR image read success rate: {path_success_rate:.4f}
- Needs SAR path/patch manifest first: `{needs_manifest}`

Path details are in `{run_paths.output_dir / 'full_path_resolution_report.csv'}`.

## 5. Full 205 Target Coverage

- Target rows: {len(targets)}
- Unique target-candidate feature rows: {len(features)}
- Candidate roles include `rank1_v1`, `best_proxy`, `best_center`, `v2a/v2b/v2c_rank1`, `v1_top1_to_top5`, and `v1_top6_to_top20`.

## 6. Feature Valid Rate

- Structure feature valid rate: {feature_valid_rate:.4f}
- Feature source image type: diagnostic display/pseudocolor image when `sar_pseudocolor_path` is used.

## 7. Rank1 Vs Best-Proxy Full Feature Differences

{md_table(separability[['feature','n_pairs','median_best_proxy_minus_rank1','mean_best_proxy_minus_rank1','directional_consistency','effect_size_robust','condition_stability','recommended_status']], max_rows=20)}

## 8. Consistency With 40-Case Scout

- Scout promising features: {scout_promising}
- Full-audit promising features: {full_promising}
- Directionally consistent promising overlap: {consistent}

## 9. Promising Features

{md_table(promising[['feature','n_pairs','directional_consistency','effect_size_robust','condition_stability','recommended_status']], max_rows=10)}

## 10. Weak Or Unstable Features

{md_table(unstable[['feature','n_pairs','directional_consistency','effect_size_robust','condition_stability','recommended_status']], max_rows=10)}

Reliability details are in `{run_paths.output_dir / 'full_feature_reliability_report.csv'}`.

## 11. Condition-Wise Stability

{md_table(condition_summary.head(20), max_rows=20)}

## 12. Truncated+Occluded Observations

Truncated and occluded cases remain a risk group. This audit uses A021/v1 condition labels only after inference outputs exist, for grouping and panel review prioritization. They are not used as structure-factor inputs.

## 13. Panel Review Queue

- Panel review queue rows: {len(panel_queue)}
- Panels generated: {int(panel_queue['panel_generated'].sum()) if 'panel_generated' in panel_queue else 0}
- Queue file: `{run_paths.output_dir / 'full_panel_review_queue.csv'}`
- Panel directory: `{run_paths.panels_dir}`

## 14. Support For Structure-Only Fixed Pilot

Support decision: `{support}`

Reason: {decision_reason}

## 15. Pilot Preconditions If Supported

- Write the structure-only fixed pilot rule before execution.
- Keep all thresholds fixed before seeing pilot results.
- Keep A019/A021 out of inference.
- Review representative panels, especially disagreement and truncated+occluded cases.
- Explicitly mark pseudocolor/display-image risk if raw SAR is unavailable.

## 16. If Not Supported

If the decision is not supported, the next step is either SAR path/patch manifest repair or independent candidate proposal research. Do not return to table-only v3 rule search.

## 17. Explicit Non-Actions

- No v3 ranking was generated.
- No structure-only selected output was generated.
- No threshold was tuned.
- No training was performed.
- No calibration was performed.
- A021 was not fed into inference.
- GT was not used to tune rules.
- Source/provenance was not used for sorting.
- A001/A005/A019/A021 originals were not modified.

## Output Figures

{chr(10).join(f'- `{path}`' for path in figure_paths)}

## Repair Notes

{chr(10).join(f'- {note}' for note in REPAIR_NOTES) if REPAIR_NOTES else '- No repair was needed during this run.'}
"""
    run_paths.summary_md_path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_paths = RunPaths(args.output_root, args.log_root)
    setup_logging(run_paths.log_path)
    logging.info("GM17 Phase4S SAR structure full audit started.")
    logging.info("Interpreter expected by caller: D:\\MINICONDA\\envs\\py311\\python.exe")
    logging.info("Boundary: diagnostic separability audit only; no v3 ranking or selected output.")
    for note in REPAIR_NOTES:
        logging.info("Repair note: %s", note)

    v1_dir = Path(args.v1_dir)
    v1_diag_dir = Path(args.v1_diagnostics)
    v2_dir = Path(args.v2_dir)
    scout_dir = Path(args.scout_dir)

    v1_ranked = key_cols_as_text(read_csv(v1_dir / "pilot_candidates_ranked.csv"))
    v1_selected = key_cols_as_text(read_csv(v1_dir / "pilot_selected_rank1.csv"))
    v1_eval = key_cols_as_text(read_csv(v1_dir / "evaluation_per_target.csv"))
    v1_diag = key_cols_as_text(read_csv(v1_diag_dir / "diagnostic_per_target.csv"))
    v2_ranked = key_cols_as_text(read_csv(v2_dir / "pilot_v2_candidates_ranked.csv"))
    v2_eval = key_cols_as_text(read_csv(v2_dir / "evaluation_v2_per_target_by_variant.csv"))
    scout_summary, _scout_comparison = read_scout_reference(scout_dir)

    a019 = read_csv(Path(args.a019))
    a021 = read_csv(Path(args.a021)) if Path(args.a021).exists() else pd.DataFrame()
    a019_path_col = find_sar_path_column(a019)
    logging.info("A019 SAR path column selected: %s", a019_path_col)

    v2_wide = build_v2_wide(v2_eval)
    targets = build_targets(v1_eval, v1_diag, v2_wide, a021)
    selected_ids = set(v1_selected["candidate_id"].map(norm_str)) if "candidate_id" in v1_selected.columns else set()
    targets["rank1_in_pilot_selected_rank1"] = targets["rank1_candidate_id"].map(norm_str).isin(selected_ids)
    path_report = resolve_sar_paths(targets, a019, a019_path_col)
    path_report, image_cache = update_path_report_with_reads(path_report)
    targets = targets.merge(
        path_report[["target_audit_id", "path_status", "image_read_status", "feature_source_image_type"]],
        on="target_audit_id",
        how="left",
    )

    candidate_roles = build_candidate_roles(targets, v1_ranked, v2_ranked, v2_eval)
    features = compute_structure_feature_table(candidate_roles, path_report, image_cache)
    role_features = join_roles_with_features(candidate_roles, features)
    role_comparison = build_role_comparison(role_features, targets)
    separability = build_feature_separability(role_comparison, role_features)
    reliability = feature_reliability(role_features, separability)
    condition_summary = build_condition_group_summary(targets, role_comparison)
    panel_queue = select_panel_queue(targets, path_report, role_comparison, args.max_panels)
    panel_queue = make_panels(panel_queue, role_features, image_cache, run_paths.panels_dir)
    figure_paths = make_figures(role_features, separability, role_comparison, reliability, panel_queue, run_paths.figures_dir)

    feature_valid_rate = float(features["structure_feature_status"].astype(str).str.startswith("ok_").mean()) if len(features) else 0.0
    path_success_rate = float(path_report["image_read_status"].eq("ok").mean()) if len(path_report) else 0.0
    support, needs_manifest, decision_reason = support_decision(
        path_success_rate,
        feature_valid_rate,
        separability,
        int(panel_queue["panel_generated"].sum()),
    )

    targets.to_csv(run_paths.output_dir / "full_audit_targets.csv", index=False, encoding="utf-8-sig")
    candidate_roles.to_csv(run_paths.output_dir / "full_audit_candidate_roles.csv", index=False, encoding="utf-8-sig")
    features.to_csv(run_paths.output_dir / "full_structure_features.csv", index=False, encoding="utf-8-sig")
    role_comparison.to_csv(run_paths.output_dir / "full_role_comparison.csv", index=False, encoding="utf-8-sig")
    separability.to_csv(run_paths.output_dir / "full_feature_separability.csv", index=False, encoding="utf-8-sig")
    condition_summary.to_csv(run_paths.output_dir / "full_condition_group_summary.csv", index=False, encoding="utf-8-sig")
    reliability.to_csv(run_paths.output_dir / "full_feature_reliability_report.csv", index=False, encoding="utf-8-sig")
    panel_queue.to_csv(run_paths.output_dir / "full_panel_review_queue.csv", index=False, encoding="utf-8-sig")
    path_report.to_csv(run_paths.output_dir / "full_path_resolution_report.csv", index=False, encoding="utf-8-sig")

    write_summary_json(
        run_paths,
        args,
        targets,
        features,
        path_report,
        separability,
        condition_summary,
        reliability,
        panel_queue,
        figure_paths,
        support,
        needs_manifest,
        decision_reason,
        scout_summary,
    )
    write_markdown_summary(
        run_paths,
        args,
        targets,
        features,
        path_report,
        separability,
        reliability,
        condition_summary,
        panel_queue,
        support,
        needs_manifest,
        decision_reason,
        scout_summary,
        figure_paths,
    )

    logging.info("Output directory: %s", run_paths.output_dir)
    logging.info("Markdown summary: %s", run_paths.summary_md_path)
    logging.info("Targets: %s", len(targets))
    logging.info("Unique candidates: %s", len(features))
    logging.info("SAR image read success rate: %.4f", path_success_rate)
    logging.info("Panel count: %s", int(panel_queue["panel_generated"].sum()))
    logging.info("Support structure-only fixed pilot: %s", support)
    print(
        json.dumps(
            {
                "output_dir": str(run_paths.output_dir),
                "summary_md": str(run_paths.summary_md_path),
                "support_structure_only_fixed_pilot": support,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
