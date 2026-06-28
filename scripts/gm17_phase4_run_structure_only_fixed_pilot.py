#!/usr/bin/env python
"""GM17 Phase4S pre-registered structure-only fixed pilot.

Ranking boundary:
- Candidate pool is the full A001 GM_RM017 candidate bank.
- Only A001 safe candidate fields, SAR image path resolution, and SAR image
  structure features are used for ranking.
- No A019 final boxes, no A021 condition labels, no source/provenance fields,
  no legacy score fields, no thresholds, no training, and no calibration.
"""

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

import gm17_phase4_sar_structure_evidence_scout as scout


DEFAULT_A001 = "output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv"
DEFAULT_A019 = "output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv"
DEFAULT_FULL_AUDIT = "output/gm17_phase4_sar_structure_full_audit_20260628_214419"
DEFAULT_OUTPUT_ROOT = "output"
DEFAULT_LOG_ROOT = "logs"

SAFE_A001_COLUMNS = [
    "candidate_id",
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
    "cx",
    "cy",
    "w",
    "h",
    "heading",
    "r",
    "az",
    "cross",
]
GROUP_KEYS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
FEATURE_COLUMNS = [
    "box_to_background_ratio",
    "inside_energy_fraction",
    "optional_local_contrast",
    "edge_spillover_ratio",
]
DIAGNOSTIC_ONLY_FEATURES = [
    "edge_spillover_ratio",
    "box_mean_intensity",
    "local_background_mean",
    "structure_feature_status",
    "feature_source_image_type",
    "box_clip_fraction",
    "local_patch_area_px",
]
FORBIDDEN_FIELDS_NOT_LOADED = [
    "candidate_source",
    "candidate_detail",
    "candidate_expansion_state",
    "candidate_expansion_reason",
    "gm17_anchor_strength",
    "temporal_factor_score",
    "delta_r_from_pred",
    "delta_cross_from_pred",
    "delta_az_from_pred",
    "score",
    "lr_score",
    "sar_factor_score",
    "final_*",
    "gt_*",
    "condition",
    "truncation",
    "occlusion",
    "oracle",
    "selected",
]
VARIANTS = {
    "s1": {
        "name": "primary_structure_rank3",
        "features": [
            ("box_to_background_ratio", "higher"),
            ("inside_energy_fraction", "higher"),
            ("optional_local_contrast", "higher"),
        ],
        "primary": True,
    },
    "s2": {
        "name": "conservative_structure_rank2",
        "features": [
            ("box_to_background_ratio", "higher"),
            ("inside_energy_fraction", "higher"),
        ],
        "primary": False,
    },
    "s3": {
        "name": "structure_with_spillover_diagnostic",
        "features": [
            ("box_to_background_ratio", "higher"),
            ("inside_energy_fraction", "higher"),
            ("optional_local_contrast", "higher"),
            ("edge_spillover_ratio", "lower"),
        ],
        "primary": False,
    },
}
EPS = 1e-6
REPAIR_NOTES: list[str] = []


class RunPaths:
    def __init__(self, output_root: str, log_root: str) -> None:
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(output_root) / f"gm17_phase4_structure_only_fixed_pilot_{self.timestamp}"
        self.log_path = Path(log_root) / f"gm17_phase4_structure_only_fixed_pilot_{self.timestamp}.log"
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GM17 Phase4S structure-only fixed pilot.")
    parser.add_argument("--a001", default=DEFAULT_A001)
    parser.add_argument("--a019", default=DEFAULT_A019)
    parser.add_argument("--full-audit-dir", default=DEFAULT_FULL_AUDIT)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--log-root", default=DEFAULT_LOG_ROOT)
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


def key_cols_as_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in GROUP_KEYS:
        if col in out.columns:
            if col == "sar_frame_num":
                out[col] = out[col].map(safe_int_text)
            else:
                out[col] = out[col].map(norm_str)
    return out


def read_a001_safe(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    header = pd.read_csv(path, nrows=0).columns.tolist()
    missing = [col for col in SAFE_A001_COLUMNS if col not in header]
    if missing:
        raise ValueError(f"A001 missing required safe columns: {missing}")
    logging.info("Reading A001 safe columns only from %s", path)
    df = pd.read_csv(path, usecols=SAFE_A001_COLUMNS)
    df = key_cols_as_text(df)
    forbidden_loaded = [col for col in df.columns if col not in SAFE_A001_COLUMNS]
    if forbidden_loaded:
        raise RuntimeError(f"Unexpected forbidden columns loaded from A001: {forbidden_loaded}")
    scenes = sorted(set(df["scene"].map(norm_str)))
    if any(scene in {"GM_RM011", "GM_RM019"} for scene in scenes):
        raise RuntimeError(f"A001 contains forbidden scenes for this GM_RM017 pilot: {scenes}")
    if scenes != ["GM_RM017"]:
        raise RuntimeError(f"A001 is not GM_RM017-only by scene column: {scenes}")
    return df


def find_sar_path_column(columns: list[str]) -> str:
    if "sar_pseudocolor_path" in columns:
        return "sar_pseudocolor_path"
    candidates: list[tuple[int, str]] = []
    for col in columns:
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
    candidates.sort(reverse=True)
    return candidates[0][1] if candidates else ""


def load_path_report(full_audit_dir: Path, a019_path: Path, candidate_groups: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    report_path = full_audit_dir / "full_path_resolution_report.csv"
    if report_path.exists():
        logging.info("Using Phase4S full audit path report: %s", report_path)
        path_report = pd.read_csv(report_path)
        path_report = key_cols_as_text(path_report)
        return path_report, str(report_path)

    logging.warning("Full audit path report unavailable; falling back to A019 path fields only.")
    header = pd.read_csv(a019_path, nrows=0).columns.tolist()
    path_col = find_sar_path_column(header)
    if not path_col:
        raise RuntimeError("Could not find SAR image path field in A019 fallback.")
    usecols = ["target_identity", "scene", "sar_frame_num", path_col]
    a019_paths = pd.read_csv(a019_path, usecols=usecols)
    a019_paths = key_cols_as_text(a019_paths)
    merged = candidate_groups.merge(a019_paths, on=["target_identity", "scene", "sar_frame_num"], how="left")
    merged["gm17_track_id"] = merged["gm17_track_id"].map(norm_str)
    merged["resolved_path"] = merged[path_col].fillna("").map(norm_str)
    merged["path_exists"] = merged["resolved_path"].map(lambda p: bool(p) and Path(p).exists())
    merged["path_status"] = np.where(merged["path_exists"], "a019_path_exists", "a019_path_missing")
    merged["feature_source_image_type"] = "diagnostic_on_display_image" if "pseudocolor" in path_col.lower() else "sar_image"
    merged["image_read_status"] = "not_attempted"
    return merged, f"{a019_path}:{path_col}"


def read_images(path_report: pd.DataFrame) -> tuple[pd.DataFrame, dict[tuple[str, str, str, str], np.ndarray | None]]:
    rows: list[dict[str, Any]] = []
    image_cache: dict[tuple[str, str, str, str], np.ndarray | None] = {}
    for record in path_report.to_dict("records"):
        key = tuple(norm_str(record.get(col, "")) if col != "sar_frame_num" else safe_int_text(record.get(col, "")) for col in GROUP_KEYS)
        image, status = scout.load_image(norm_str(record.get("resolved_path", "")))
        record["image_read_status"] = status
        record["image_height"] = image.shape[0] if image is not None else math.nan
        record["image_width"] = image.shape[1] if image is not None else math.nan
        image_cache[key] = image
        rows.append(record)
    return pd.DataFrame(rows), image_cache


def structure_features_for_candidate(image: np.ndarray | None, row: pd.Series, source_type: str) -> dict[str, Any]:
    out = {
        "box_to_background_ratio": math.nan,
        "inside_energy_fraction": math.nan,
        "optional_local_contrast": math.nan,
        "edge_spillover_ratio": math.nan,
        "box_mean_intensity": math.nan,
        "local_background_mean": math.nan,
        "structure_feature_status": "image_unavailable",
        "feature_source_image_type": source_type,
        "box_clip_fraction": math.nan,
        "local_patch_area_px": math.nan,
    }
    if image is None:
        return out
    cx = safe_float(row.get("cx"))
    cy = safe_float(row.get("cy"))
    w = safe_float(row.get("w"))
    h = safe_float(row.get("h"))
    if not all(math.isfinite(v) for v in [cx, cy, w, h]) or w <= 0 or h <= 0:
        out["structure_feature_status"] = "invalid_box_geometry"
        return out

    x1, y1, x2, y2 = scout.clipped_bounds(cx, cy, w, h, image.shape, scale=1.0)
    ex1, ey1, ex2, ey2 = scout.clipped_bounds(cx, cy, w, h, image.shape, scale=2.0)
    bx1, by1, bx2, by2 = scout.clipped_bounds(cx, cy, w, h, image.shape, scale=1.25)
    if x2 <= x1 or y2 <= y1 or ex2 <= ex1 or ey2 <= ey1:
        out["structure_feature_status"] = "empty_box_or_local_patch_after_clip"
        return out

    box = image[y1:y2, x1:x2]
    local = image[ey1:ey2, ex1:ex2]
    box_sum = float(np.sum(box))
    box_mean = float(np.mean(box)) if box.size else math.nan
    local_sum = float(np.sum(local)) if local.size else math.nan

    local_mask = np.ones(local.shape, dtype=bool)
    inner_x1 = max(0, x1 - ex1)
    inner_x2 = min(local.shape[1], x2 - ex1)
    inner_y1 = max(0, y1 - ey1)
    inner_y2 = min(local.shape[0], y2 - ey1)
    if inner_x2 > inner_x1 and inner_y2 > inner_y1:
        local_mask[inner_y1:inner_y2, inner_x1:inner_x2] = False
    background = local[local_mask]
    background_mean = float(np.mean(background)) if background.size else 0.0

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

    nominal_area = float(w * h)
    clipped_area = float(max(0, x2 - x1) * max(0, y2 - y1))
    out.update(
        {
            "box_to_background_ratio": box_mean / (background_mean + EPS),
            "inside_energy_fraction": box_sum / (local_sum + EPS),
            "optional_local_contrast": box_mean - background_mean,
            "edge_spillover_ratio": spillover_sum / (box_sum + EPS),
            "box_mean_intensity": box_mean,
            "local_background_mean": background_mean,
            "structure_feature_status": "ok_axis_aligned_diagnostic_on_display_image"
            if source_type == "diagnostic_on_display_image"
            else "ok_axis_aligned_diagnostic",
            "box_clip_fraction": clipped_area / (nominal_area + EPS),
            "local_patch_area_px": float(max(0, ex2 - ex1) * max(0, ey2 - ey1)),
        }
    )
    return out


def compute_features(candidates: pd.DataFrame, path_report: pd.DataFrame, image_cache: dict[tuple[str, str, str, str], np.ndarray | None]) -> pd.DataFrame:
    path_by_key = {
        tuple(norm_str(row.get(col, "")) if col != "sar_frame_num" else safe_int_text(row.get(col, "")) for col in GROUP_KEYS): row
        for row in path_report.to_dict("records")
    }
    rows: list[dict[str, Any]] = []
    total = len(candidates)
    for idx, (_, row) in enumerate(candidates.iterrows(), start=1):
        if idx % 10000 == 0:
            logging.info("Computed structure features for %s/%s candidates.", idx, total)
        key = tuple(norm_str(row.get(col, "")) if col != "sar_frame_num" else safe_int_text(row.get(col, "")) for col in GROUP_KEYS)
        path_info = path_by_key.get(key, {})
        feature = structure_features_for_candidate(
            image_cache.get(key),
            row,
            norm_str(path_info.get("feature_source_image_type", "unresolved")),
        )
        rows.append(feature)
    return pd.concat([candidates.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def rank_percentile(series: pd.Series, higher_is_better: bool) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    out = pd.Series(1.0, index=series.index, dtype=float)
    valid = values[np.isfinite(values)]
    n = len(valid)
    if n == 0:
        return out
    if n == 1:
        out.loc[valid.index] = 0.0
        return out
    ranks = valid.rank(ascending=not higher_is_better, method="average")
    out.loc[valid.index] = (ranks - 1.0) / (n - 1.0)
    return out


def apply_variant_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    grouped = out.groupby(GROUP_KEYS, dropna=False, sort=False)
    for variant_key, definition in VARIANTS.items():
        component_cols: list[str] = []
        for feature, direction in definition["features"]:
            col = f"{variant_key}_{feature}_rank_pct"
            out[col] = grouped[feature].transform(lambda s, d=direction: rank_percentile(s, d == "higher"))
            component_cols.append(col)
        score_col = f"{variant_key}_score"
        rank_col = f"{variant_key}_rank"
        out[score_col] = out[component_cols].mean(axis=1)
        sorted_idx = out.sort_values(GROUP_KEYS + [score_col, "candidate_id"], ascending=True).index
        ranks = (
            out.loc[sorted_idx, GROUP_KEYS + [score_col, "candidate_id"]]
            .groupby(GROUP_KEYS, dropna=False, sort=False)
            .cumcount()
            + 1
        )
        out.loc[sorted_idx, rank_col] = ranks.to_numpy()
        out[rank_col] = out[rank_col].astype(int)
    return out


def selected_rank1_by_variant(ranked: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for variant_key, definition in VARIANTS.items():
        rank_col = f"{variant_key}_rank"
        score_col = f"{variant_key}_score"
        view = ranked[ranked[rank_col].eq(1)].copy()
        view["variant"] = variant_key
        view["variant_name"] = definition["name"]
        view["structure_score"] = view[score_col]
        view["structure_rank"] = view[rank_col]
        rows.append(view)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def write_manifest(
    path: Path,
    args: argparse.Namespace,
    candidates: pd.DataFrame,
    ranked: pd.DataFrame,
    path_report: pd.DataFrame,
    path_source: str,
    run_paths: RunPaths,
) -> None:
    feature_valid = ranked["structure_feature_status"].astype(str).str.startswith("ok_")
    manifest = {
        "run_timestamp": run_paths.timestamp,
        "input_paths": {
            "A001": args.a001,
            "full_audit_dir": args.full_audit_dir,
            "path_source": path_source,
            "A019_fallback_path_only": args.a019,
        },
        "output_paths": {
            "output_dir": str(run_paths.output_dir),
            "log_path": str(run_paths.log_path),
            "ranked_candidates": str(run_paths.output_dir / "pilot_structure_candidates_ranked.csv"),
            "selected_rank1_by_variant": str(run_paths.output_dir / "pilot_structure_selected_rank1_by_variant.csv"),
        },
        "row_counts": {
            "a001_candidates": int(len(candidates)),
            "ranked_candidates": int(len(ranked)),
            "target_groups": int(candidates[GROUP_KEYS].drop_duplicates().shape[0]),
        },
        "loaded_columns": SAFE_A001_COLUMNS,
        "active_features": {
            "s1_primary_structure_rank3": ["box_to_background_ratio", "inside_energy_fraction", "optional_local_contrast"],
            "s2_conservative_structure_rank2": ["box_to_background_ratio", "inside_energy_fraction"],
            "s3_structure_with_spillover_diagnostic": [
                "box_to_background_ratio",
                "inside_energy_fraction",
                "optional_local_contrast",
                "edge_spillover_ratio",
            ],
        },
        "diagnostic_only_features": DIAGNOSTIC_ONLY_FEATURES,
        "forbidden_fields_not_loaded": FORBIDDEN_FIELDS_NOT_LOADED,
        "path_resolution_summary": {
            "groups": int(len(path_report)),
            "path_exists_count": int(path_report.get("path_exists", pd.Series(False)).fillna(False).astype(bool).sum())
            if "path_exists" in path_report
            else None,
            "path_source": path_source,
        },
        "image_read_success": {
            "groups_read_ok": int(path_report["image_read_status"].eq("ok").sum()),
            "groups_total": int(len(path_report)),
            "success_rate": float(path_report["image_read_status"].eq("ok").mean()) if len(path_report) else 0.0,
        },
        "feature_valid_rate": float(feature_valid.mean()) if len(ranked) else 0.0,
        "variant_definitions": VARIANTS,
        "score_rule": {
            "group_keys": GROUP_KEYS,
            "component_rank_percentile": "(rank - 1) / (n_valid - 1), best=0, worst=1, invalid=1",
            "variant_score": "mean of pre-registered component rank percentiles",
            "lower_score_is_better": True,
            "tie_break": "candidate_id ascending only",
        },
        "no_gt_in_ranking_statement": "A019 final boxes are not loaded for ranking. A019 is only an optional SAR path fallback.",
        "no_a021_in_ranking_statement": "A021 is not read by the pilot script.",
        "display_pseudocolor_risk_statement": (
            "Features are computed on SAR display/pseudocolor images from the path report. "
            "This is a diagnostic display-image pilot, not raw SAR intensity physics proof."
        ),
        "repair_notes": REPAIR_NOTES,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def main() -> int:
    args = parse_args()
    run_paths = RunPaths(args.output_root, args.log_root)
    setup_logging(run_paths.log_path)
    logging.info("GM17 Phase4S structure-only fixed pilot started.")
    logging.info("Boundary: pre-registered fixed ranking, no GT/A021/source/legacy score in ranking.")
    for note in REPAIR_NOTES:
        logging.info("Repair note: %s", note)

    a001 = read_a001_safe(Path(args.a001))
    groups = a001[GROUP_KEYS].drop_duplicates().copy()
    path_report, path_source = load_path_report(Path(args.full_audit_dir), Path(args.a019), groups)
    path_report = key_cols_as_text(path_report)
    path_report, image_cache = read_images(path_report)

    merged = a001.merge(
        path_report[GROUP_KEYS + ["resolved_path", "image_read_status", "feature_source_image_type"]],
        on=GROUP_KEYS,
        how="left",
    )
    if merged["resolved_path"].isna().any():
        logging.warning("Some A001 groups have no resolved SAR path; features will be unavailable for those groups.")
    logging.info("A001 candidates: %s", len(merged))
    logging.info("Target groups: %s", groups.shape[0])
    logging.info("SAR image read success rate: %.4f", path_report["image_read_status"].eq("ok").mean())

    featured = compute_features(merged[SAFE_A001_COLUMNS], path_report, image_cache)
    ranked = apply_variant_scores(featured)

    output_cols = [
        *SAFE_A001_COLUMNS,
        "box_to_background_ratio",
        "inside_energy_fraction",
        "optional_local_contrast",
        "edge_spillover_ratio",
        "box_mean_intensity",
        "local_background_mean",
        "structure_feature_status",
        "feature_source_image_type",
        "box_clip_fraction",
        "local_patch_area_px",
        "s1_score",
        "s1_rank",
        "s2_score",
        "s2_rank",
        "s3_score",
        "s3_rank",
    ]
    ranked[output_cols].to_csv(run_paths.output_dir / "pilot_structure_candidates_ranked.csv", index=False, encoding="utf-8-sig")
    selected = selected_rank1_by_variant(ranked)
    selected_cols = [
        "variant",
        "variant_name",
        *SAFE_A001_COLUMNS,
        "box_to_background_ratio",
        "inside_energy_fraction",
        "optional_local_contrast",
        "edge_spillover_ratio",
        "structure_feature_status",
        "feature_source_image_type",
        "structure_score",
        "structure_rank",
        "s1_score",
        "s1_rank",
        "s2_score",
        "s2_rank",
        "s3_score",
        "s3_rank",
    ]
    selected[selected_cols].to_csv(
        run_paths.output_dir / "pilot_structure_selected_rank1_by_variant.csv",
        index=False,
        encoding="utf-8-sig",
    )
    path_report.to_csv(run_paths.output_dir / "pilot_structure_path_resolution_report.csv", index=False, encoding="utf-8-sig")
    write_manifest(run_paths.output_dir / "pilot_structure_manifest.json", args, a001, ranked, path_report, path_source, run_paths)

    logging.info("Output directory: %s", run_paths.output_dir)
    logging.info("Ranked candidates: %s", len(ranked))
    logging.info("Selected rank1 rows: %s", len(selected))
    logging.info("Feature valid rate: %.4f", ranked["structure_feature_status"].astype(str).str.startswith("ok_").mean())
    print(
        json.dumps(
            {
                "output_dir": str(run_paths.output_dir),
                "ranked_candidates": int(len(ranked)),
                "target_groups": int(groups.shape[0]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
