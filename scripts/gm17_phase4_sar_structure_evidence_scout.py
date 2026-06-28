#!/usr/bin/env python
"""GM17 Phase4 SAR structure evidence scout.

This script is a diagnostic scout over already-produced v1/v2 outputs. It does
not create a v3 ranking, does not tune thresholds, and does not use evaluation
labels or conditions as inference inputs. A019 is read only to resolve SAR image
paths for post-inference visual/feature inspection.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


DEFAULT_V1_DIR = "output/gm17_phase4_minimal_factor_pilot_20260628_110447"
DEFAULT_V1_DIAGNOSTICS = "output/gm17_phase4_minimal_factor_pilot_v1_diagnostics_20260628_113224"
DEFAULT_V2_DIR = "output/gm17_phase4_minimal_factor_pilot_v2_20260628_171204"
DEFAULT_OUTPUT_ROOT = "output"
DEFAULT_LOG_ROOT = "logs"
DEFAULT_A019_PATH = "output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv"
REPAIR_NOTE = (
    "One small script repair was made before the final recorded run: panel labels used escaped "
    "newline text, which made patch titles crowded. The repair changed only visual label line "
    "breaks and the recorded repair note; it did not change inputs, case selection, feature "
    "logic, ranking, thresholds, or metrics."
)

KEY_COLS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
ROLE_ORDER = ["rank1_v1", "best_proxy", "best_center", "v2a_rank1", "v2b_rank1", "v2c_rank1"]
VARIANT_BY_ROLE = {
    "v2a_rank1": "v2a",
    "v2b_rank1": "v2b",
    "v2c_rank1": "v2c",
}
ROLE_COLORS = {
    "rank1_v1": "#e41a1c",
    "best_proxy": "#4daf4a",
    "best_center": "#377eb8",
    "v2a_rank1": "#984ea3",
    "v2b_rank1": "#ff7f00",
    "v2c_rank1": "#a65628",
}
FEATURE_COLUMNS = [
    "box_mean_intensity",
    "box_max_intensity",
    "box_sum_intensity",
    "box_top5_mean_intensity",
    "local_background_mean",
    "box_to_background_ratio",
    "peak_to_background_ratio",
    "center_to_peak_distance",
    "inside_energy_fraction",
    "edge_spillover_ratio",
    "simple_long_axis_support",
    "simple_short_axis_support",
]
HIGHER_BETTER = {
    "box_mean_intensity": True,
    "box_max_intensity": True,
    "box_sum_intensity": True,
    "box_top5_mean_intensity": True,
    "local_background_mean": False,
    "box_to_background_ratio": True,
    "peak_to_background_ratio": True,
    "center_to_peak_distance": False,
    "inside_energy_fraction": True,
    "edge_spillover_ratio": False,
    "simple_long_axis_support": True,
    "simple_short_axis_support": True,
}
BOXPLOT_FEATURES = [
    "box_to_background_ratio",
    "center_to_peak_distance",
    "inside_energy_fraction",
]
EPS = 1e-6


@dataclass
class RunPaths:
    timestamp: str
    output_dir: Path
    figures_dir: Path
    panels_dir: Path
    log_path: Path
    summary_md_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GM17 Phase4 SAR structure evidence scout.")
    parser.add_argument("--v1-dir", default=DEFAULT_V1_DIR)
    parser.add_argument("--v1-diagnostics", default=DEFAULT_V1_DIAGNOSTICS)
    parser.add_argument("--v2-dir", default=DEFAULT_V2_DIR)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--log-root", default=DEFAULT_LOG_ROOT)
    parser.add_argument("--sar-root", default=None)
    parser.add_argument("--max-cases", type=int, default=40)
    return parser.parse_args()


def make_run_paths(output_root: str, log_root: str) -> RunPaths:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_root) / f"gm17_phase4_sar_structure_evidence_scout_{timestamp}"
    figures_dir = output_dir / "figures"
    panels_dir = output_dir / "panels"
    log_path = Path(log_root) / f"gm17_phase4_sar_structure_evidence_scout_{timestamp}.log"
    summary_md_path = Path("docs") / f"gm17_phase4_sar_structure_evidence_scout_summary_{timestamp}.md"
    output_dir.mkdir(parents=True, exist_ok=False)
    figures_dir.mkdir(parents=True, exist_ok=True)
    panels_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    summary_md_path.parent.mkdir(parents=True, exist_ok=True)
    return RunPaths(timestamp, output_dir, figures_dir, panels_dir, log_path, summary_md_path)


def setup_logging(log_path: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def norm_str(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if pd.isna(value):
        return False
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def safe_float(value: Any) -> float:
    try:
        if pd.isna(value):
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def finite_or_none(value: Any) -> float | None:
    number = safe_float(value)
    if math.isfinite(number):
        return number
    return None


def safe_int_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    try:
        f = float(value)
        if f.is_integer():
            return str(int(f))
    except (TypeError, ValueError):
        pass
    return str(value)


def read_csv_required(path: Path, **kwargs: Any) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    logging.info("Reading %s", path)
    return pd.read_csv(path, **kwargs)


def key_from_row(row: pd.Series | dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        norm_str(row.get("target_identity", "")),
        norm_str(row.get("scene", "")),
        safe_int_text(row.get("sar_frame_num", "")),
        norm_str(row.get("gm17_track_id", "")),
    )


def key_cols_as_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in KEY_COLS:
        if col in out.columns:
            if col == "sar_frame_num":
                out[col] = out[col].map(safe_int_text)
            else:
                out[col] = out[col].map(norm_str)
    return out


def flatten_v2_eval(v2_eval: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in key_cols_as_text(v2_eval).groupby(KEY_COLS, dropna=False):
        record = dict(zip(KEY_COLS, key))
        for _, row in group.iterrows():
            variant = norm_str(row.get("variant", ""))
            if not variant:
                continue
            prefix = variant
            record[f"{prefix}_candidate_id"] = norm_str(row.get("candidate_id", ""))
            record[f"{prefix}_center_error"] = safe_float(row.get("center_error"))
            record[f"{prefix}_proxy_iou"] = safe_float(row.get("axis_aligned_proxy_iou"))
            record[f"{prefix}_rank1_is_best_proxy"] = bool_value(row.get("rank1_is_best_proxy"))
            record[f"{prefix}_rank1_is_best_center"] = bool_value(row.get("rank1_is_best_center"))
            record[f"{prefix}_best_proxy_rank"] = safe_float(row.get("best_proxy_rank"))
        rows.append(record)
    return pd.DataFrame(rows)


def enrich_case_flags(base: pd.DataFrame, v2_wide: pd.DataFrame) -> pd.DataFrame:
    merged = key_cols_as_text(base).merge(key_cols_as_text(v2_wide), on=KEY_COLS, how="left")
    merged["rank1_is_best_proxy_bool"] = merged["rank1_is_best_proxy"].map(bool_value)
    merged["rank1_proxy_iou_num"] = merged["rank1_proxy_iou"].map(safe_float)
    merged["best_proxy_iou_num"] = merged["best_proxy_iou"].map(safe_float)
    merged["best_proxy_rank_num"] = merged["best_proxy_pilot_rank"].map(safe_float)
    merged["rank1_center_error_num"] = merged["rank1_center_error"].map(safe_float)
    merged["best_center_error_num"] = merged["best_center_error"].map(safe_float)
    merged["temporal_zero_count_num"] = merged["temporal_zero_candidate_count"].map(safe_float)
    cond = merged["condition_type"].map(lambda x: norm_str(x).lower())
    trunc = merged["truncation_degree"].map(lambda x: norm_str(x).lower())
    occ = merged["occlusion_degree"].map(lambda x: norm_str(x).lower())
    moderate_or_severe_trunc = trunc.isin(["moderate", "severe"])
    moderate_or_severe_occ = occ.isin(["moderate", "severe"])

    merged["flag_temporal_zero_bad"] = (
        (merged["temporal_zero_count_num"] > 0)
        & (~merged["rank1_is_best_proxy_bool"])
        & (merged["best_proxy_iou_num"] > merged["rank1_proxy_iou_num"])
    )
    merged["flag_best_proxy_deep"] = (
        (~merged["rank1_is_best_proxy_bool"]) & (merged["best_proxy_rank_num"] > 50)
    )
    merged["flag_truncated_occluded_moderate_severe"] = (
        cond.eq("truncated+occluded") & (moderate_or_severe_trunc | moderate_or_severe_occ)
    )
    merged["flag_low_rank1_high_best"] = (
        (merged["rank1_proxy_iou_num"] < 0.25) & (merged["best_proxy_iou_num"] >= 0.5)
    )
    merged["flag_v2bc_no_improve"] = (
        (~merged.get("v2b_rank1_is_best_proxy", pd.Series(False, index=merged.index)).fillna(False).map(bool_value))
        & (~merged.get("v2c_rank1_is_best_proxy", pd.Series(False, index=merged.index)).fillna(False).map(bool_value))
        & (merged.get("v2b_best_proxy_rank", pd.Series(np.nan, index=merged.index)).map(safe_float) > 20)
        & (merged.get("v2c_best_proxy_rank", pd.Series(np.nan, index=merged.index)).map(safe_float) > 20)
    )
    merged["flag_success_control"] = (
        merged["rank1_is_best_proxy_bool"]
        | ((merged["rank1_proxy_iou_num"] >= 0.5) & (merged["rank1_center_error_num"] <= 50))
    )
    merged["selection_severity"] = (
        (merged["best_proxy_iou_num"] - merged["rank1_proxy_iou_num"]).fillna(0)
        + (merged["best_proxy_rank_num"].fillna(0) / 200.0)
        + (merged["rank1_center_error_num"].fillna(0) / 200.0)
    )
    return merged


def collect_case_tags(row: pd.Series) -> list[str]:
    mapping = [
        ("temporal_zero_bad", "flag_temporal_zero_bad"),
        ("best_proxy_rank_gt_50", "flag_best_proxy_deep"),
        ("truncated_occluded_moderate_severe", "flag_truncated_occluded_moderate_severe"),
        ("rank1_low_iou_best_proxy_high_iou", "flag_low_rank1_high_best"),
        ("v2b_v2c_no_improve", "flag_v2bc_no_improve"),
        ("success_control", "flag_success_control"),
    ]
    return [name for name, col in mapping if bool_value(row.get(col, False))]


def select_cases(case_pool: pd.DataFrame, max_cases: int) -> pd.DataFrame:
    max_cases = max(1, int(max_cases))
    category_plan = [
        ("temporal_zero_bad", "flag_temporal_zero_bad", False),
        ("best_proxy_rank_gt_50", "flag_best_proxy_deep", False),
        ("truncated_occluded_moderate_severe", "flag_truncated_occluded_moderate_severe", False),
        ("rank1_low_iou_best_proxy_high_iou", "flag_low_rank1_high_best", False),
        ("v2b_v2c_no_improve", "flag_v2bc_no_improve", False),
        ("success_control", "flag_success_control", True),
    ]
    base_quota = max(3, max_cases // len(category_plan))
    quotas = {name: base_quota for name, _, _ in category_plan}
    quotas["success_control"] = max(3, min(6, max_cases // 6 + 1))

    selected_indices: list[int] = []
    selected_set: set[int] = set()
    primary_case_types: dict[int, str] = {}

    for category, flag, success in category_plan:
        candidates = case_pool[case_pool[flag].map(bool_value)].copy()
        if success:
            candidates = candidates.sort_values(
                ["rank1_proxy_iou_num", "rank1_center_error_num"], ascending=[False, True]
            )
        else:
            candidates = candidates.sort_values("selection_severity", ascending=False)
        for idx in candidates.index:
            if len(selected_indices) >= max_cases:
                break
            if idx in selected_set:
                continue
            selected_indices.append(idx)
            selected_set.add(idx)
            primary_case_types[idx] = category
            if sum(primary_case_types.get(i) == category for i in selected_indices) >= quotas[category]:
                break

    if len(selected_indices) < max_cases:
        fill = case_pool[~case_pool.index.isin(selected_indices)].copy()
        fill = fill.sort_values("selection_severity", ascending=False)
        for idx in fill.index:
            if len(selected_indices) >= max_cases:
                break
            selected_indices.append(idx)
            selected_set.add(idx)
            primary_case_types[idx] = "failure_fill"

    selected = case_pool.loc[selected_indices].copy()
    selected["primary_case_type"] = [primary_case_types.get(idx, "failure_fill") for idx in selected.index]
    selected["case_tags"] = selected.apply(lambda row: ";".join(collect_case_tags(row)), axis=1)
    selected = selected.reset_index(drop=True)
    selected["case_id"] = [f"C{i:03d}" for i in range(1, len(selected) + 1)]
    return selected


def build_candidate_index(df: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    indexed: dict[str, list[dict[str, Any]]] = {}
    if "candidate_id" not in df.columns:
        return indexed
    keyed = key_cols_as_text(df)
    for record in keyed.to_dict("records"):
        cid = norm_str(record.get("candidate_id", ""))
        if not cid:
            continue
        indexed.setdefault(cid, []).append(record)
    return indexed


def lookup_candidate(
    candidate_id: Any,
    case_row: pd.Series,
    indices: Iterable[dict[str, list[dict[str, Any]]]],
) -> dict[str, Any] | None:
    cid = norm_str(candidate_id)
    if not cid:
        return None
    target_key = key_from_row(case_row)
    for index in indices:
        records = index.get(cid, [])
        if not records:
            continue
        for record in records:
            if key_from_row(record) == target_key:
                return record
        return records[0]
    return None


def first_v2_variant_row(v2_eval: pd.DataFrame, case_row: pd.Series, variant: str) -> dict[str, Any] | None:
    keyed = key_cols_as_text(v2_eval)
    mask = np.ones(len(keyed), dtype=bool)
    for col, value in zip(KEY_COLS, key_from_row(case_row)):
        mask &= keyed[col].astype(str).eq(value).to_numpy()
    mask &= keyed["variant"].astype(str).eq(variant).to_numpy()
    rows = keyed.loc[mask]
    if rows.empty:
        return None
    return rows.iloc[0].to_dict()


def geometry_from_record(record: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in ["cx", "cy", "w", "h", "heading", "r", "az", "cross"]:
        out[col] = safe_float(record.get(col)) if record else math.nan
    return out


def role_metric_from_case(case_row: pd.Series, role: str, v2_row: dict[str, Any] | None = None) -> dict[str, Any]:
    if role == "rank1_v1":
        return {
            "role_rank": safe_float(case_row.get("pilot_rank", 1)),
            "role_proxy_iou": safe_float(case_row.get("rank1_proxy_iou")),
            "role_center_error": safe_float(case_row.get("rank1_center_error")),
            "role_is_best_proxy": bool_value(case_row.get("rank1_is_best_proxy")),
            "role_is_best_center": bool_value(case_row.get("rank1_is_best_center")),
        }
    if role == "best_proxy":
        return {
            "role_rank": safe_float(case_row.get("best_proxy_pilot_rank")),
            "role_proxy_iou": safe_float(case_row.get("best_proxy_iou")),
            "role_center_error": safe_float(case_row.get("best_proxy_center_error")),
            "role_is_best_proxy": True,
            "role_is_best_center": False,
        }
    if role == "best_center":
        return {
            "role_rank": safe_float(case_row.get("best_center_pilot_rank")),
            "role_proxy_iou": safe_float(case_row.get("best_center_proxy_iou")),
            "role_center_error": safe_float(case_row.get("best_center_error")),
            "role_is_best_proxy": False,
            "role_is_best_center": True,
        }
    if role in VARIANT_BY_ROLE and v2_row:
        variant = VARIANT_BY_ROLE[role]
        return {
            "role_rank": safe_float(v2_row.get(f"{variant}_rank", 1)),
            "role_proxy_iou": safe_float(v2_row.get("axis_aligned_proxy_iou")),
            "role_center_error": safe_float(v2_row.get("center_error")),
            "role_is_best_proxy": bool_value(v2_row.get("rank1_is_best_proxy")),
            "role_is_best_center": bool_value(v2_row.get("rank1_is_best_center")),
        }
    return {
        "role_rank": math.nan,
        "role_proxy_iou": math.nan,
        "role_center_error": math.nan,
        "role_is_best_proxy": False,
        "role_is_best_center": False,
    }


def build_role_rows(
    selected_cases: pd.DataFrame,
    v1_ranked: pd.DataFrame,
    v2_ranked: pd.DataFrame,
    v2_eval: pd.DataFrame,
    path_info: pd.DataFrame,
) -> pd.DataFrame:
    v1_index = build_candidate_index(v1_ranked)
    v2_index = build_candidate_index(v2_ranked)
    path_by_case = {row["case_id"]: row for row in path_info.to_dict("records")}
    rows: list[dict[str, Any]] = []

    for _, case_row in selected_cases.iterrows():
        case_id = case_row["case_id"]
        role_to_candidate = {
            "rank1_v1": case_row.get("rank1_candidate_id"),
            "best_proxy": case_row.get("best_proxy_candidate_id"),
            "best_center": case_row.get("best_center_candidate_id"),
        }
        v2_variant_rows: dict[str, dict[str, Any] | None] = {}
        for role, variant in VARIANT_BY_ROLE.items():
            v2_row = first_v2_variant_row(v2_eval, case_row, variant)
            v2_variant_rows[role] = v2_row
            role_to_candidate[role] = v2_row.get("candidate_id") if v2_row else ""

        duplicate_group_by_candidate: dict[str, int] = {}
        group_counter = 0
        for candidate_id in role_to_candidate.values():
            cid = norm_str(candidate_id)
            if not cid:
                continue
            if cid not in duplicate_group_by_candidate:
                group_counter += 1
                duplicate_group_by_candidate[cid] = group_counter

        for role in ROLE_ORDER:
            candidate_id = norm_str(role_to_candidate.get(role, ""))
            v2_row = v2_variant_rows.get(role)
            lookup = lookup_candidate(candidate_id, case_row, [v1_index, v2_index])
            if lookup is None and v2_row:
                lookup = v2_row
            geometry = geometry_from_record(lookup)
            metrics = role_metric_from_case(case_row, role, v2_row)
            path_record = path_by_case.get(case_id, {})
            row = {
                "case_id": case_id,
                "primary_case_type": case_row.get("primary_case_type", ""),
                "case_tags": case_row.get("case_tags", ""),
                "role": role,
                "candidate_id": candidate_id,
                "role_duplicate_group": duplicate_group_by_candidate.get(candidate_id, np.nan),
                "target_identity": case_row.get("target_identity", ""),
                "scene": case_row.get("scene", ""),
                "sar_frame_num": case_row.get("sar_frame_num", ""),
                "gm17_track_id": case_row.get("gm17_track_id", ""),
                "condition_type": case_row.get("condition_type", ""),
                "condition_status": case_row.get("condition_status", ""),
                "truncation_degree": case_row.get("truncation_degree", ""),
                "occlusion_degree": case_row.get("occlusion_degree", ""),
                "sar_image_path": path_record.get("resolved_path", ""),
                "sar_path_status": path_record.get("path_status", ""),
            }
            row.update(metrics)
            row.update(geometry)
            rows.append(row)
    return pd.DataFrame(rows)


def load_a019_paths() -> pd.DataFrame:
    path = Path(DEFAULT_A019_PATH)
    usecols = ["target_identity", "scene", "sar_frame", "sar_frame_num", "sar_pseudocolor_path"]
    if not path.exists():
        logging.warning("A019 path table not found: %s", path)
        return pd.DataFrame(columns=usecols)
    return key_cols_as_text(pd.read_csv(path, usecols=usecols[:-1] + [usecols[-1]]))


def candidate_paths_from_sar_root(
    sar_root: str | None,
    scene: str,
    sar_frame: str,
    a019_path: str,
) -> list[Path]:
    if not sar_root:
        return []
    root = Path(sar_root)
    filename = Path(a019_path).name if a019_path else sar_frame
    attempts = [
        root / filename,
        root / scene / filename,
        root / f"{scene}_SARframes" / filename,
        root / scene / f"{scene}_SARframes" / filename,
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for path in attempts:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def resolve_paths(selected_cases: pd.DataFrame, sar_root: str | None) -> pd.DataFrame:
    a019 = load_a019_paths()
    if not a019.empty:
        a019 = a019[a019["scene"].astype(str).eq("GM_RM017")].copy()
    grouped = {
        key: group
        for key, group in a019.groupby(["target_identity", "scene", "sar_frame_num"], dropna=False)
    }

    rows: list[dict[str, Any]] = []
    for _, case in selected_cases.iterrows():
        key = (
            norm_str(case.get("target_identity", "")),
            norm_str(case.get("scene", "")),
            safe_int_text(case.get("sar_frame_num", "")),
        )
        matches = grouped.get(key, pd.DataFrame())
        a019_path = ""
        sar_frame = ""
        attempts: list[str] = []
        status = "no_a019_match"
        resolved_path = ""
        exists = False
        if not matches.empty:
            a019_path = norm_str(matches.iloc[0].get("sar_pseudocolor_path", ""))
            sar_frame = norm_str(matches.iloc[0].get("sar_frame", ""))
            if a019_path:
                attempts.append(a019_path)
                if Path(a019_path).exists():
                    resolved_path = a019_path
                    exists = True
                    status = "a019_path_exists"
                else:
                    status = "a019_path_missing"
            else:
                status = "a019_match_no_path"
            if not exists:
                for attempt in candidate_paths_from_sar_root(sar_root, key[1], sar_frame, a019_path):
                    attempts.append(str(attempt))
                    if attempt.exists():
                        resolved_path = str(attempt)
                        exists = True
                        status = "sar_root_path_exists"
                        break

        rows.append(
            {
                "case_id": case.get("case_id", ""),
                "target_identity": case.get("target_identity", ""),
                "scene": case.get("scene", ""),
                "sar_frame_num": case.get("sar_frame_num", ""),
                "gm17_track_id": case.get("gm17_track_id", ""),
                "primary_case_type": case.get("primary_case_type", ""),
                "a019_match_count": int(len(matches)) if isinstance(matches, pd.DataFrame) else 0,
                "a019_sar_frame": sar_frame,
                "a019_sar_pseudocolor_path": a019_path,
                "resolved_path": resolved_path,
                "path_exists": exists,
                "path_status": status,
                "attempted_paths": " | ".join(attempts),
                "image_read_status": "not_attempted",
            }
        )
    return pd.DataFrame(rows)


def load_image(path: str) -> tuple[np.ndarray | None, str]:
    if not path:
        return None, "no_path"
    p = Path(path)
    if not p.exists():
        return None, "path_missing"
    suffix = p.suffix.lower()
    try:
        if suffix == ".npy":
            arr = np.load(p)
        elif suffix == ".mat":
            try:
                from scipy.io import loadmat
            except Exception as exc:  # pragma: no cover - environment dependent
                return None, f"mat_unsupported:{exc}"
            mat = loadmat(p)
            arr = None
            for key, value in mat.items():
                if key.startswith("__"):
                    continue
                candidate = np.asarray(value)
                if candidate.ndim >= 2 and np.issubdtype(candidate.dtype, np.number):
                    arr = candidate
                    break
            if arr is None:
                return None, "mat_no_numeric_array"
        else:
            from PIL import Image

            with Image.open(p) as image:
                arr = np.asarray(image.convert("RGB"))
        gray = normalize_to_gray(arr)
        if gray is None:
            return None, "image_normalization_failed"
        return gray, "ok"
    except Exception as exc:  # pragma: no cover - recorded in output
        return None, f"read_error:{type(exc).__name__}:{exc}"


def normalize_to_gray(arr: np.ndarray) -> np.ndarray | None:
    if arr is None:
        return None
    array = np.asarray(arr)
    if array.ndim == 0:
        return None
    if array.ndim > 2:
        array = array[..., :3].astype(float)
        array = 0.299 * array[..., 0] + 0.587 * array[..., 1] + 0.114 * array[..., 2]
    else:
        array = array.astype(float)
    array = np.squeeze(array)
    if array.ndim != 2:
        return None
    finite = np.isfinite(array)
    if not finite.any():
        return None
    min_val = float(np.nanmin(array[finite]))
    max_val = float(np.nanmax(array[finite]))
    if max_val > min_val:
        array = (array - min_val) / (max_val - min_val)
    else:
        array = np.zeros_like(array, dtype=float)
    array[~np.isfinite(array)] = 0.0
    return np.clip(array, 0.0, 1.0)


def clipped_bounds(cx: float, cy: float, w: float, h: float, image_shape: tuple[int, int], scale: float = 1.0) -> tuple[int, int, int, int]:
    height, width = image_shape
    half_w = max(w * scale / 2.0, 0.0)
    half_h = max(h * scale / 2.0, 0.0)
    x1 = max(0, int(math.floor(cx - half_w)))
    x2 = min(width, int(math.ceil(cx + half_w)))
    y1 = max(0, int(math.floor(cy - half_h)))
    y2 = min(height, int(math.ceil(cy + half_h)))
    return x1, y1, x2, y2


def sample_line_support(
    image: np.ndarray,
    cx: float,
    cy: float,
    length: float,
    angle_deg: float,
    background_mean: float,
    n_samples: int = 64,
) -> float:
    if not all(math.isfinite(v) for v in [cx, cy, length, angle_deg]) or length <= 1:
        return math.nan
    theta = math.radians(angle_deg)
    dx = math.cos(theta)
    dy = math.sin(theta)
    offsets = np.linspace(-length / 2.0, length / 2.0, n_samples)
    xs = np.rint(cx + offsets * dx).astype(int)
    ys = np.rint(cy + offsets * dy).astype(int)
    valid = (xs >= 0) & (xs < image.shape[1]) & (ys >= 0) & (ys < image.shape[0])
    if not valid.any():
        return math.nan
    values = image[ys[valid], xs[valid]]
    return float(np.mean(values) / (background_mean + EPS))


def compute_structure_features(image: np.ndarray | None, role_row: pd.Series) -> dict[str, Any]:
    features = {col: math.nan for col in FEATURE_COLUMNS}
    if image is None:
        features["structure_feature_status"] = "image_unavailable"
        return features

    cx = safe_float(role_row.get("cx"))
    cy = safe_float(role_row.get("cy"))
    w = safe_float(role_row.get("w"))
    h = safe_float(role_row.get("h"))
    heading = safe_float(role_row.get("heading"))
    if not all(math.isfinite(v) for v in [cx, cy, w, h]) or w <= 0 or h <= 0:
        features["structure_feature_status"] = "invalid_box_geometry"
        return features

    x1, y1, x2, y2 = clipped_bounds(cx, cy, w, h, image.shape, scale=1.0)
    if x2 <= x1 or y2 <= y1:
        features["structure_feature_status"] = "empty_box_after_clip"
        return features
    box = image[y1:y2, x1:x2]
    if box.size == 0:
        features["structure_feature_status"] = "empty_box_pixels"
        return features

    ex1, ey1, ex2, ey2 = clipped_bounds(cx, cy, w, h, image.shape, scale=2.0)
    local = image[ey1:ey2, ex1:ex2]
    mask = np.ones(local.shape, dtype=bool)
    inner_x1 = max(0, x1 - ex1)
    inner_x2 = min(local.shape[1], x2 - ex1)
    inner_y1 = max(0, y1 - ey1)
    inner_y2 = min(local.shape[0], y2 - ey1)
    if inner_x2 > inner_x1 and inner_y2 > inner_y1:
        mask[inner_y1:inner_y2, inner_x1:inner_x2] = False
    background_pixels = local[mask]
    background_mean = float(np.mean(background_pixels)) if background_pixels.size else math.nan
    if not math.isfinite(background_mean):
        background_mean = 0.0

    box_flat = box.reshape(-1)
    top_n = max(1, int(math.ceil(0.05 * box_flat.size)))
    top_values = np.partition(box_flat, -top_n)[-top_n:]
    box_sum = float(np.sum(box))
    local_sum = float(np.sum(local))
    box_mean = float(np.mean(box))
    box_max = float(np.max(box))

    peak_y_local, peak_x_local = np.unravel_index(np.argmax(local), local.shape)
    peak_x = ex1 + peak_x_local
    peak_y = ey1 + peak_y_local
    center_to_peak = float(math.hypot(peak_x - cx, peak_y - cy))

    band_scale = 1.25
    bx1, by1, bx2, by2 = clipped_bounds(cx, cy, w, h, image.shape, scale=band_scale)
    band = image[by1:by2, bx1:bx2]
    band_mask = np.ones(band.shape, dtype=bool)
    band_inner_x1 = max(0, x1 - bx1)
    band_inner_x2 = min(band.shape[1], x2 - bx1)
    band_inner_y1 = max(0, y1 - by1)
    band_inner_y2 = min(band.shape[0], y2 - by1)
    if band_inner_x2 > band_inner_x1 and band_inner_y2 > band_inner_y1:
        band_mask[band_inner_y1:band_inner_y2, band_inner_x1:band_inner_x2] = False
    band_pixels = band[band_mask]
    spillover_sum = float(np.sum(band_pixels)) if band_pixels.size else 0.0

    if not math.isfinite(heading):
        heading = 0.0
    features.update(
        {
            "box_mean_intensity": box_mean,
            "box_max_intensity": box_max,
            "box_sum_intensity": box_sum,
            "box_top5_mean_intensity": float(np.mean(top_values)),
            "local_background_mean": background_mean,
            "box_to_background_ratio": box_mean / (background_mean + EPS),
            "peak_to_background_ratio": box_max / (background_mean + EPS),
            "center_to_peak_distance": center_to_peak,
            "inside_energy_fraction": box_sum / (local_sum + EPS),
            "edge_spillover_ratio": spillover_sum / (box_sum + EPS),
            "simple_long_axis_support": sample_line_support(image, cx, cy, max(w, h), heading, background_mean),
            "simple_short_axis_support": sample_line_support(image, cx, cy, min(w, h), heading + 90.0, background_mean),
            "structure_feature_status": "ok_axis_aligned_diagnostic",
        }
    )
    return features


def compute_all_features(role_rows: pd.DataFrame, path_report: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, np.ndarray | None], pd.DataFrame]:
    image_cache: dict[str, np.ndarray | None] = {}
    image_status: dict[str, str] = {}
    updated_path_rows = path_report.to_dict("records")
    path_status_by_case = {row["case_id"]: row for row in updated_path_rows}

    for row in updated_path_rows:
        path = row.get("resolved_path", "")
        image, status = load_image(path)
        image_cache[row["case_id"]] = image
        image_status[row["case_id"]] = status
        row["image_read_status"] = status
        row["image_height"] = image.shape[0] if image is not None else np.nan
        row["image_width"] = image.shape[1] if image is not None else np.nan
        if status != "ok" and row.get("path_exists"):
            row["path_status"] = f"{row.get('path_status')};image_{status}"
        path_status_by_case[row["case_id"]] = row

    feature_rows: list[dict[str, Any]] = []
    for _, role_row in role_rows.iterrows():
        case_id = role_row["case_id"]
        image = image_cache.get(case_id)
        feature = compute_structure_features(image, role_row)
        out = role_row.to_dict()
        out.update(feature)
        out["image_read_status"] = image_status.get(case_id, "not_attempted")
        feature_rows.append(out)
    return pd.DataFrame(feature_rows), image_cache, pd.DataFrame(updated_path_rows)


def compact_candidate_id(candidate_id: str) -> str:
    text = norm_str(candidate_id)
    if len(text) <= 16:
        return text
    return text[:8] + "..." + text[-5:]


def draw_rect(ax: plt.Axes, row: pd.Series, color: str, label: str, linewidth: float = 2.0) -> None:
    cx = safe_float(row.get("cx"))
    cy = safe_float(row.get("cy"))
    w = safe_float(row.get("w"))
    h = safe_float(row.get("h"))
    if not all(math.isfinite(v) for v in [cx, cy, w, h]) or w <= 0 or h <= 0:
        return
    x1 = cx - w / 2.0
    y1 = cy - h / 2.0
    rect = Rectangle((x1, y1), w, h, fill=False, edgecolor=color, linewidth=linewidth)
    ax.add_patch(rect)
    ax.text(
        x1,
        y1,
        label,
        color=color,
        fontsize=7,
        bbox={"facecolor": "black", "alpha": 0.45, "pad": 1, "edgecolor": "none"},
    )


def make_case_panel(
    case_id: str,
    image: np.ndarray | None,
    role_features: pd.DataFrame,
    panels_dir: Path,
) -> str:
    if image is None:
        return ""

    unique_rows: list[pd.Series] = []
    seen_candidates: set[str] = set()
    for role in ROLE_ORDER:
        rows = role_features[role_features["role"].eq(role)]
        if rows.empty:
            continue
        row = rows.iloc[0]
        cid = norm_str(row.get("candidate_id", ""))
        if cid in seen_candidates:
            continue
        seen_candidates.add(cid)
        unique_rows.append(row)

    fig = plt.figure(figsize=(15, 9), dpi=140)
    grid = fig.add_gridspec(2, 4, width_ratios=[2.2, 1, 1, 1], height_ratios=[1, 1])
    ax_main = fig.add_subplot(grid[:, 0])
    ax_main.imshow(image, cmap="gray", vmin=0, vmax=1)
    ax_main.set_title(f"{case_id} overview")
    ax_main.set_axis_off()

    for row in unique_rows:
        role = norm_str(row.get("role", ""))
        label = f"{role}\n{compact_candidate_id(row.get('candidate_id', ''))}"
        draw_rect(ax_main, row, ROLE_COLORS.get(role, "#222222"), label)

    for patch_idx in range(6):
        ax = fig.add_subplot(grid[patch_idx // 3, patch_idx % 3 + 1])
        if patch_idx >= len(unique_rows):
            ax.set_axis_off()
            continue
        row = unique_rows[patch_idx]
        cx = safe_float(row.get("cx"))
        cy = safe_float(row.get("cy"))
        w = safe_float(row.get("w"))
        h = safe_float(row.get("h"))
        role = norm_str(row.get("role", ""))
        if not all(math.isfinite(v) for v in [cx, cy, w, h]) or w <= 0 or h <= 0:
            ax.set_title(f"{role}: invalid box", fontsize=8)
            ax.set_axis_off()
            continue
        x1, y1, x2, y2 = clipped_bounds(cx, cy, w, h, image.shape, scale=2.3)
        patch = image[y1:y2, x1:x2]
        ax.imshow(patch, cmap="gray", vmin=0, vmax=1)
        local_row = row.copy()
        local_row["cx"] = cx - x1
        local_row["cy"] = cy - y1
        draw_rect(ax, local_row, ROLE_COLORS.get(role, "#222222"), role, linewidth=1.6)
        title = (
            f"{role} {compact_candidate_id(row.get('candidate_id', ''))}\n"
            f"IoU={safe_float(row.get('role_proxy_iou')):.3f} "
            f"err={safe_float(row.get('role_center_error')):.1f} "
            f"rank={safe_float(row.get('role_rank')):.0f}"
        )
        ax.set_title(title, fontsize=7, pad=2)
        ax.set_axis_off()

    fig.suptitle(
        "Diagnostic SAR structure scout: candidate roles only, no active scoring",
        fontsize=11,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95], h_pad=2.0, w_pad=1.5)
    out_path = panels_dir / f"{case_id}_sar_structure_panel.png"
    fig.savefig(out_path)
    plt.close(fig)
    return str(out_path)


def make_all_panels(features: pd.DataFrame, image_cache: dict[str, np.ndarray | None], panels_dir: Path) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for case_id, group in features.groupby("case_id", sort=False):
        panel_path = make_case_panel(case_id, image_cache.get(case_id), group, panels_dir)
        records.append(
            {
                "case_id": case_id,
                "panel_path": panel_path,
                "panel_generated": bool(panel_path),
            }
        )
    return pd.DataFrame(records)


def summarize_role_comparison(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]]]:
    ok = features[features["structure_feature_status"].eq("ok_axis_aligned_diagnostic")].copy()
    rows: list[dict[str, Any]] = []
    for role in ROLE_ORDER:
        role_df = ok[ok["role"].eq(role)]
        for feature in FEATURE_COLUMNS:
            values = pd.to_numeric(role_df[feature], errors="coerce").dropna()
            rows.append(
                {
                    "summary_type": "role_distribution",
                    "role_or_comparison": role,
                    "feature": feature,
                    "n": int(values.shape[0]),
                    "mean": float(values.mean()) if not values.empty else math.nan,
                    "median": float(values.median()) if not values.empty else math.nan,
                    "std": float(values.std(ddof=0)) if values.shape[0] > 1 else math.nan,
                    "mean_diff": math.nan,
                    "median_diff": math.nan,
                    "positive_count": math.nan,
                    "negative_count": math.nan,
                    "directional_consistency": math.nan,
                    "diagnostic_signal_strength": math.nan,
                    "interpretation_hint": "diagnostic role distribution only",
                }
            )

    signal_rows: list[dict[str, Any]] = []
    for feature in FEATURE_COLUMNS:
        pivot = ok.pivot_table(index="case_id", columns="role", values=feature, aggfunc="first")
        if "rank1_v1" not in pivot.columns or "best_proxy" not in pivot.columns:
            continue
        pair = pivot[["rank1_v1", "best_proxy"]].dropna()
        if pair.empty:
            continue
        diff = pair["best_proxy"] - pair["rank1_v1"]
        higher_better = HIGHER_BETTER.get(feature, True)
        favorable = diff > 0 if higher_better else diff < 0
        unfavorable = diff < 0 if higher_better else diff > 0
        all_values = pd.to_numeric(ok[feature], errors="coerce").dropna()
        scale = float(all_values.quantile(0.75) - all_values.quantile(0.25)) if len(all_values) > 1 else 0.0
        if not math.isfinite(scale) or scale <= EPS:
            scale = float(all_values.std(ddof=0)) if len(all_values) > 1 else 1.0
        if not math.isfinite(scale) or scale <= EPS:
            scale = 1.0
        median_diff = float(diff.median())
        consistency = float(favorable.mean())
        strength = abs(median_diff) / scale * consistency
        hint = "best_proxy higher is favorable" if higher_better else "best_proxy lower is favorable"
        row = {
            "summary_type": "best_proxy_minus_rank1_v1",
            "role_or_comparison": "best_proxy_minus_rank1_v1",
            "feature": feature,
            "n": int(pair.shape[0]),
            "mean": math.nan,
            "median": math.nan,
            "std": math.nan,
            "mean_diff": float(diff.mean()),
            "median_diff": median_diff,
            "positive_count": int((diff > 0).sum()),
            "negative_count": int((diff < 0).sum()),
            "directional_consistency": consistency,
            "diagnostic_signal_strength": float(strength),
            "interpretation_hint": hint,
        }
        rows.append(row)
        signal_rows.append(row)

    comparison = pd.DataFrame(rows)
    signal_df = pd.DataFrame(signal_rows).sort_values("diagnostic_signal_strength", ascending=False)
    promising = signal_df.head(3).to_dict("records") if not signal_df.empty else []
    unstable = (
        signal_df.sort_values(["directional_consistency", "diagnostic_signal_strength"], ascending=[True, True])
        .head(3)
        .to_dict("records")
        if not signal_df.empty
        else []
    )
    return comparison, signal_df, promising, unstable


def make_boxplot(features: pd.DataFrame, feature: str, out_path: Path) -> None:
    ok = features[features["structure_feature_status"].eq("ok_axis_aligned_diagnostic")]
    data: list[np.ndarray] = []
    labels: list[str] = []
    for role in ROLE_ORDER:
        values = pd.to_numeric(ok.loc[ok["role"].eq(role), feature], errors="coerce").dropna().to_numpy()
        if values.size:
            data.append(values)
            labels.append(role)
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=140)
    if data:
        ax.boxplot(data, labels=labels, showfliers=False)
        ax.set_ylabel(feature)
        ax.tick_params(axis="x", rotation=25)
    else:
        ax.text(0.5, 0.5, "No readable SAR image features", ha="center", va="center")
        ax.set_axis_off()
    ax.set_title(f"Diagnostic role distribution: {feature}")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def make_case_type_panel_success_bar(case_summary: pd.DataFrame, out_path: Path) -> None:
    counts = (
        case_summary.groupby("primary_case_type")
        .agg(selected_cases=("case_id", "count"), panels_generated=("panel_generated", "sum"), image_read_ok=("image_read_ok", "sum"))
        .reset_index()
    )
    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    if not counts.empty:
        x = np.arange(len(counts))
        width = 0.25
        ax.bar(x - width, counts["selected_cases"], width, label="selected")
        ax.bar(x, counts["image_read_ok"], width, label="image read ok")
        ax.bar(x + width, counts["panels_generated"], width, label="panel")
        ax.set_xticks(x)
        ax.set_xticklabels(counts["primary_case_type"], rotation=30, ha="right")
        ax.legend()
        ax.set_ylabel("case count")
    else:
        ax.text(0.5, 0.5, "No cases", ha="center", va="center")
        ax.set_axis_off()
    ax.set_title("Case type path/panel success")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def make_feature_signal_bar(signal_df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    if not signal_df.empty:
        plot_df = signal_df.sort_values("diagnostic_signal_strength", ascending=True).tail(10)
        ax.barh(plot_df["feature"], plot_df["diagnostic_signal_strength"], color="#4c78a8")
        ax.set_xlabel("diagnostic signal strength")
    else:
        ax.text(0.5, 0.5, "No paired rank1/best_proxy feature signal", ha="center", va="center")
        ax.set_axis_off()
    ax.set_title("Diagnostic candidate feature signal, best_proxy vs rank1_v1")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def make_figures(features: pd.DataFrame, case_summary: pd.DataFrame, signal_df: pd.DataFrame, figures_dir: Path) -> list[str]:
    figure_paths: list[str] = []
    for feature in BOXPLOT_FEATURES:
        path = figures_dir / f"role_{feature}_boxplot.png"
        make_boxplot(features, feature, path)
        figure_paths.append(str(path))
    path = figures_dir / "case_type_panel_success_bar.png"
    make_case_type_panel_success_bar(case_summary, path)
    figure_paths.append(str(path))
    path = figures_dir / "feature_signal_candidate_bar.png"
    make_feature_signal_bar(signal_df, path)
    figure_paths.append(str(path))
    return figure_paths


def make_failure_group_summary(selected_cases: pd.DataFrame, path_report: pd.DataFrame, panel_report: pd.DataFrame) -> pd.DataFrame:
    case_summary = selected_cases.merge(
        path_report[["case_id", "path_status", "image_read_status"]],
        on="case_id",
        how="left",
    ).merge(panel_report, on="case_id", how="left")
    case_summary["image_read_ok"] = case_summary["image_read_status"].eq("ok")
    case_summary["panel_generated"] = case_summary["panel_generated"].fillna(False).map(bool)
    grouped = (
        case_summary.groupby(
            ["primary_case_type", "condition_type", "truncation_degree", "occlusion_degree"],
            dropna=False,
        )
        .agg(
            n_cases=("case_id", "count"),
            image_read_ok=("image_read_ok", "sum"),
            panels_generated=("panel_generated", "sum"),
            mean_rank1_proxy_iou=("rank1_proxy_iou_num", "mean"),
            mean_best_proxy_iou=("best_proxy_iou_num", "mean"),
            median_best_proxy_rank=("best_proxy_rank_num", "median"),
        )
        .reset_index()
    )
    return grouped


def md_table_from_df(df: pd.DataFrame, max_rows: int = 20, float_digits: int = 4) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{x:.{float_digits}f}")
    headers = list(view.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in headers) + " |")
    if len(df) > max_rows:
        lines.append(f"\n_Showing {max_rows} of {len(df)} rows._")
    return "\n".join(lines)


def describe_feature_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "- No paired feature signal could be computed because readable SAR features were unavailable."
    lines: list[str] = []
    for row in rows:
        feature = row.get("feature", "")
        n = int(row.get("n", 0))
        consistency = safe_float(row.get("directional_consistency"))
        median_diff = safe_float(row.get("median_diff"))
        hint = row.get("interpretation_hint", "")
        lines.append(
            f"- `{feature}`: n={n}, median best_proxy-rank1 diff={median_diff:.4f}, "
            f"directional consistency={consistency:.2f}; {hint}."
        )
    return "\n".join(lines)


def write_markdown_summary(
    run_paths: RunPaths,
    args: argparse.Namespace,
    selected_cases: pd.DataFrame,
    path_report: pd.DataFrame,
    panel_report: pd.DataFrame,
    comparison_summary: pd.DataFrame,
    failure_group_summary: pd.DataFrame,
    promising: list[dict[str, Any]],
    unstable: list[dict[str, Any]],
    figure_paths: list[str],
    support_next_spec: bool,
) -> None:
    path_success = int(path_report["path_exists"].sum()) if "path_exists" in path_report else 0
    image_success = int(path_report["image_read_status"].eq("ok").sum()) if "image_read_status" in path_report else 0
    panel_count = int(panel_report["panel_generated"].sum()) if "panel_generated" in panel_report else 0
    case_counts = selected_cases["primary_case_type"].value_counts().rename_axis("case_type").reset_index(name="n")
    role_pair = comparison_summary[comparison_summary["summary_type"].eq("best_proxy_minus_rank1_v1")]
    core_features = role_pair[role_pair["feature"].isin(FEATURE_COLUMNS)][
        [
            "feature",
            "n",
            "mean_diff",
            "median_diff",
            "directional_consistency",
            "diagnostic_signal_strength",
            "interpretation_hint",
        ]
    ].sort_values("diagnostic_signal_strength", ascending=False)

    text = f"""# GM17 Phase4 SAR Structure Evidence Scout Summary {run_paths.timestamp}

## 1. Purpose

This run is a diagnostic SAR image structure evidence scout over v1/v2 failure and control cases. It compares existing candidate roles (`rank1_v1`, `best_proxy`, `best_center`, `v2a_rank1`, `v2b_rank1`, `v2c_rank1`) in the SAR image patch to identify future `sar_structure_factor` evidence candidates.

It is not v3 ranking, not a tuned selector, not a final model, and not an execution configuration.

## 2. Why Not Continue V3 Table Tuning

The v1/v2 pilots already indicate that the A001 candidate bank has coverage, while table-level geometry/temporal sorting does not reliably promote the best candidate to rank1. V2 reduced the temporal-zero artifact only with tradeoffs that degraded rank1-best-proxy and best-proxy top-k behavior. Continuing table-field rule search risks overfitting diagnostic/evaluation artifacts instead of adding SAR-side structure evidence.

## 3. Inputs And Outputs

- V1 pilot: `{args.v1_dir}`
- V1 diagnostics: `{args.v1_diagnostics}`
- V2 pilot: `{args.v2_dir}`
- A019 path table used only for SAR image path resolution: `{DEFAULT_A019_PATH}`
- Output directory: `{run_paths.output_dir}`
- Log: `{run_paths.log_path}`
- Summary JSON: `{run_paths.output_dir / 'scout_summary.json'}`
- This Markdown summary: `{run_paths.summary_md_path}`

## 4. Case Selection Strategy

Cases were selected from post-inference v1/v2 outputs for diagnostic inspection only. The selection categories were temporal-zero bad cases, deep best-proxy rank cases, truncated+occluded moderate/severe cases, low-rank1/high-best-proxy IoU cases, v2b/v2c no-improvement cases, and success controls.

{md_table_from_df(case_counts, max_rows=20)}

## 5. SAR Image Path Resolution

- Selected cases: {len(selected_cases)}
- A019/SAR path exists: {path_success}
- SAR image read success: {image_success}
- Missing or unreadable images: {len(selected_cases) - image_success}

The path report is written to `{run_paths.output_dir / 'scout_path_resolution_report.csv'}`.

## 6. Panel Generation

- Panels generated: {panel_count}
- Panel directory: `{run_paths.panels_dir}`

Panels show candidate roles on the SAR image and local patches. Rectangles are axis-aligned diagnostic boxes derived from candidate geometry, not final predictions.

## 7. Rank1 Vs Best-Proxy Visual Difference

The paired feature comparison is diagnostic: it asks whether `best_proxy` candidates tend to show stronger SAR local structure than `rank1_v1` among selected cases. These values are not thresholds and are not active scoring rules.

{md_table_from_df(core_features, max_rows=20)}

## 8. SAR Structure Candidate Feature Statistics

All computed structure values are labeled diagnostic candidate features. The feature table is written to `{run_paths.output_dir / 'scout_structure_features.csv'}` and role-level summaries are written to `{run_paths.output_dir / 'scout_role_comparison_summary.csv'}`.

## 9. Truncated+Occluded Failure Observations

Selected truncated/occluded cases remain a high-risk diagnostic group. The scout compares whether best-proxy candidates have clearer local energy concentration or axis support than temporal-first rank1 candidates, but this run does not convert those observations into a rule.

{md_table_from_df(failure_group_summary, max_rows=20)}

## 10. Success Control Observations

Success controls are included only as a visual/feature sanity check. They help distinguish features that are broadly stable across correct-looking candidates from features that only appear in failure cases.

## 11. Potential Future `sar_structure_factor` Features

Most promising diagnostic candidates in this run:

{describe_feature_rows(promising)}

These can support a future diagnostic design spec only after human review of panels and feature caveats.

## 12. Unstable Or Not Recommended Features

Least stable diagnostic candidates in this run:

{describe_feature_rows(unstable)}

Features with weak directional consistency, small paired sample count, or strong dependence on pseudocolor rendering should remain diagnostic-only.

## 13. Relationship To Geometry And Optical Temporal Factors

`geometry_factor` still owns candidate-table geometry plausibility, and `optical_temporal_factor` remains a soft optical-to-SAR temporal suggestion. The potential `sar_structure_factor` would be SAR-image evidence inside existing A001 candidate boxes. It should not generate new candidates, move boxes, or use GT/evaluation fields during inference.

## 14. Explicit Non-Actions

- No v3 ranking was generated.
- No thresholds were tuned.
- No weights were trained.
- No calibration was performed.
- A021/condition labels were not fed into inference.
- `candidate_source`, `temporal_factor_score`, `delta_*_from_pred`, `score/lr_score/sar_factor_score`, selected outputs, B patches, and oracle-style inputs were not used for sorting.
- A001/A005/A019/A021 originals were not modified.

## 15. Next-Step Recommendation

- If the panel review confirms clear SAR-structure differences, write `sar_structure_factor diagnostic design spec`.
- If path or patch alignment issues are found, first create a SAR path/patch manifest review.
- If SAR structure still cannot distinguish roles, shift attention to independent candidate proposal rather than more table-level v3 rule search.
- Do not continue table-only v3 rule search from this output.

Current support for the next diagnostic design spec: `{support_next_spec}`.

## 16. Output Figures

{chr(10).join(f'- `{path}`' for path in figure_paths)}

## Repair Note

{REPAIR_NOTE}
"""
    run_paths.summary_md_path.write_text(text, encoding="utf-8")


def write_summary_json(
    run_paths: RunPaths,
    args: argparse.Namespace,
    selected_cases: pd.DataFrame,
    path_report: pd.DataFrame,
    panel_report: pd.DataFrame,
    comparison_summary: pd.DataFrame,
    promising: list[dict[str, Any]],
    unstable: list[dict[str, Any]],
    figure_paths: list[str],
    support_next_spec: bool,
) -> None:
    role_pair = comparison_summary[comparison_summary["summary_type"].eq("best_proxy_minus_rank1_v1")]
    case_type_counts = selected_cases["primary_case_type"].value_counts().to_dict()
    payload = {
        "run_timestamp": run_paths.timestamp,
        "input_paths": {
            "v1_dir": args.v1_dir,
            "v1_diagnostics": args.v1_diagnostics,
            "v2_dir": args.v2_dir,
            "a019_path_table": DEFAULT_A019_PATH,
            "sar_root": args.sar_root,
        },
        "output_paths": {
            "output_dir": str(run_paths.output_dir),
            "figures_dir": str(run_paths.figures_dir),
            "panels_dir": str(run_paths.panels_dir),
            "log_path": str(run_paths.log_path),
            "markdown_summary": str(run_paths.summary_md_path),
        },
        "sample_count": int(len(selected_cases)),
        "sar_images_path_exists_count": int(path_report["path_exists"].sum()) if "path_exists" in path_report else 0,
        "sar_images_read_success_count": int(path_report["image_read_status"].eq("ok").sum()) if "image_read_status" in path_report else 0,
        "panel_generated_count": int(panel_report["panel_generated"].sum()) if "panel_generated" in panel_report else 0,
        "missing_or_unreadable_image_count": int(len(selected_cases) - path_report["image_read_status"].eq("ok").sum()),
        "case_type_counts": {str(k): int(v) for k, v in case_type_counts.items()},
        "rank1_vs_best_proxy_structure_feature_differences": role_pair.to_dict("records"),
        "promising_sar_structure_features": promising,
        "unstable_or_not_recommended_features": unstable,
        "support_next_sar_structure_factor_diagnostic_design_spec": bool(support_next_spec),
        "leakage_boundary_statement": (
            "Diagnostic only. No v3 ranking, no threshold tuning, no weight training, no calibration, "
            "no GT/condition feedback into inference, no candidate_source sorting, and no original A001/A005/A019/A021 mutation."
        ),
        "figure_paths": figure_paths,
        "repair_note": REPAIR_NOTE,
    }
    with (run_paths.output_dir / "scout_summary.json").open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> int:
    args = parse_args()
    run_paths = make_run_paths(args.output_root, args.log_root)
    setup_logging(run_paths.log_path)
    logging.info("Using diagnostic-only SAR structure evidence scout.")
    logging.info("Interpreter boundary: use the active py311 environment supplied by the caller.")
    logging.info("No old_work paths are required.")
    logging.info("Repair note: %s", REPAIR_NOTE)

    v1_dir = Path(args.v1_dir)
    v1_diag_dir = Path(args.v1_diagnostics)
    v2_dir = Path(args.v2_dir)

    v1_eval = read_csv_required(v1_dir / "evaluation_per_target.csv")
    v1_ranked = read_csv_required(v1_dir / "pilot_candidates_ranked.csv")
    v1_diag = read_csv_required(v1_diag_dir / "diagnostic_per_target.csv")
    v2_eval = read_csv_required(v2_dir / "evaluation_v2_per_target_by_variant.csv")
    v2_ranked = read_csv_required(v2_dir / "pilot_v2_candidates_ranked.csv")

    v1_eval = key_cols_as_text(v1_eval)
    v1_ranked = key_cols_as_text(v1_ranked)
    v1_diag = key_cols_as_text(v1_diag)
    v2_eval = key_cols_as_text(v2_eval)
    v2_ranked = key_cols_as_text(v2_ranked)

    if "rank1_candidate_id" not in v1_diag.columns:
        rank1_map = v1_eval[KEY_COLS + ["candidate_id"]].rename(columns={"candidate_id": "rank1_candidate_id"})
        v1_diag = v1_diag.merge(rank1_map, on=KEY_COLS, how="left")
    if "pilot_rank" not in v1_diag.columns:
        v1_diag["pilot_rank"] = 1

    v2_wide = flatten_v2_eval(v2_eval)
    case_pool = enrich_case_flags(v1_diag, v2_wide)
    selected_cases = select_cases(case_pool, args.max_cases)
    logging.info("Selected %s cases.", len(selected_cases))

    path_report = resolve_paths(selected_cases, args.sar_root)
    role_rows = build_role_rows(selected_cases, v1_ranked, v2_ranked, v2_eval, path_report)
    features, image_cache, path_report = compute_all_features(role_rows, path_report)
    panel_report = make_all_panels(features, image_cache, run_paths.panels_dir)
    failure_group_summary = make_failure_group_summary(selected_cases, path_report, panel_report)
    comparison_summary, signal_df, promising, unstable = summarize_role_comparison(features)

    case_summary_for_fig = selected_cases.merge(
        path_report[["case_id", "image_read_status"]],
        on="case_id",
        how="left",
    ).merge(panel_report, on="case_id", how="left")
    case_summary_for_fig["image_read_ok"] = case_summary_for_fig["image_read_status"].eq("ok")
    case_summary_for_fig["panel_generated"] = case_summary_for_fig["panel_generated"].fillna(False).map(bool)
    figure_paths = make_figures(features, case_summary_for_fig, signal_df, run_paths.figures_dir)

    selected_cases.to_csv(run_paths.output_dir / "scout_case_selection.csv", index=False, encoding="utf-8-sig")
    role_rows.to_csv(run_paths.output_dir / "scout_candidate_roles.csv", index=False, encoding="utf-8-sig")
    features.to_csv(run_paths.output_dir / "scout_structure_features.csv", index=False, encoding="utf-8-sig")
    comparison_summary.to_csv(run_paths.output_dir / "scout_role_comparison_summary.csv", index=False, encoding="utf-8-sig")
    path_report.to_csv(run_paths.output_dir / "scout_path_resolution_report.csv", index=False, encoding="utf-8-sig")
    failure_group_summary.to_csv(run_paths.output_dir / "scout_failure_group_summary.csv", index=False, encoding="utf-8-sig")

    support_next_spec = (
        int(path_report["image_read_status"].eq("ok").sum()) >= min(10, len(selected_cases))
        and len(promising) >= 2
    )
    write_summary_json(
        run_paths,
        args,
        selected_cases,
        path_report,
        panel_report,
        comparison_summary,
        promising,
        unstable,
        figure_paths,
        support_next_spec,
    )
    write_markdown_summary(
        run_paths,
        args,
        selected_cases,
        path_report,
        panel_report,
        comparison_summary,
        failure_group_summary,
        promising,
        unstable,
        figure_paths,
        support_next_spec,
    )

    logging.info("Output directory: %s", run_paths.output_dir)
    logging.info("Markdown summary: %s", run_paths.summary_md_path)
    logging.info("Panels generated: %s", int(panel_report["panel_generated"].sum()))
    logging.info("SAR images read: %s", int(path_report["image_read_status"].eq("ok").sum()))
    logging.info("Done.")
    print(json.dumps({"output_dir": str(run_paths.output_dir), "summary_md": str(run_paths.summary_md_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
