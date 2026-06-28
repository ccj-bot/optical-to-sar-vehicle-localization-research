#!/usr/bin/env python
"""GM17 Phase4C pre-registered combined structure+temporal fixed pilot.

Ranking boundary:
- Candidate pool is the full A001 GM_RM017 bank.
- Temporal is recomputed from A001 safe geometry fields and A005 pred_r,
  pred_cross, pred_az only.
- Structure is reused from the pre-registered structure-only full A001 output.
- No A019/A021/GT/source/legacy score fields are used for ranking.
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
DEFAULT_A005 = "output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv"
DEFAULT_STRUCTURE_DIR = "output/gm17_phase4_structure_only_fixed_pilot_20260628_221140"
DEFAULT_OUTPUT_ROOT = "output"
DEFAULT_LOG_ROOT = "logs"

GROUP_KEYS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
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
SAFE_A005_COLUMNS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id", "pred_r", "pred_cross", "pred_az"]
STRUCTURE_COLUMNS = [
    "candidate_id",
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
    "box_to_background_ratio",
    "inside_energy_fraction",
    "optional_local_contrast",
    "edge_spillover_ratio",
    "s1_score",
    "s1_rank",
    "s2_score",
    "s2_rank",
    "s3_score",
    "s3_rank",
    "structure_feature_status",
    "feature_source_image_type",
]
VARIANTS = {
    "c1": {
        "name": "equal_temporal_s1",
        "weights": {"temporal_rank_percentile": 0.50, "s1_rank_percentile": 0.50},
        "primary": True,
    },
    "c2": {
        "name": "equal_temporal_s2",
        "weights": {"temporal_rank_percentile": 0.50, "s2_rank_percentile": 0.50},
        "primary": True,
    },
    "c3": {
        "name": "temporal_guard_structure_promote",
        "weights": {"temporal_rank_percentile": 0.67, "s1_rank_percentile": 0.33},
        "primary": True,
    },
    "c4": {
        "name": "structure_guard_temporal_soft_diagnostic",
        "weights": {"temporal_rank_percentile": 0.33, "s1_rank_percentile": 0.67},
        "primary": False,
    },
    "c5": {
        "name": "temporal_only_recomputed_baseline",
        "weights": {"temporal_rank_percentile": 1.00},
        "primary": False,
    },
}
FORBIDDEN_NOT_LOADED = [
    "candidate_source",
    "candidate_detail",
    "candidate_expansion_state",
    "candidate_expansion_reason",
    "temporal_factor_score",
    "delta_*_from_pred",
    "score",
    "lr_score",
    "sar_factor_score",
    "final_*",
    "condition",
    "truncation",
    "occlusion",
    "oracle",
    "selected",
]
EPS = 1e-6
REPAIR_NOTES: list[str] = [
    "Repair 1: fixed pandas group-index writeback for temporal unavailable rows. "
    "This changed only implementation indexing and did not change pre-registered "
    "features, weights, variants, or ranking rules."
]


class RunPaths:
    def __init__(self, output_root: str, log_root: str) -> None:
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(output_root) / f"gm17_phase4_combined_structure_temporal_fixed_pilot_{self.timestamp}"
        self.log_path = Path(log_root) / f"gm17_phase4_combined_structure_temporal_fixed_pilot_{self.timestamp}.log"
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GM17 Phase4C combined fixed pilot.")
    parser.add_argument("--a001", default=DEFAULT_A001)
    parser.add_argument("--a005", default=DEFAULT_A005)
    parser.add_argument("--structure-dir", default=DEFAULT_STRUCTURE_DIR)
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


def read_safe_csv(path: Path, required: list[str], label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    header = pd.read_csv(path, nrows=0).columns.tolist()
    missing = [col for col in required if col not in header]
    if missing:
        raise ValueError(f"{label} missing required columns: {missing}")
    logging.info("Reading %s safe columns from %s", label, path)
    return key_cols_as_text(pd.read_csv(path, usecols=required))


def validate_a001(a001: pd.DataFrame) -> None:
    scenes = sorted(set(a001["scene"].map(norm_str)))
    if any(scene in {"GM_RM011", "GM_RM019"} for scene in scenes):
        raise RuntimeError(f"A001 contains forbidden scenes for this pilot: {scenes}")
    if scenes != ["GM_RM017"]:
        raise RuntimeError(f"A001 must be GM_RM017-only by scene column, got {scenes}")
    if a001["candidate_id"].duplicated().any():
        raise RuntimeError("A001 candidate_id is not unique.")


def validate_structure(structure: pd.DataFrame) -> None:
    dup = structure.duplicated(["candidate_id", *GROUP_KEYS]).sum()
    if dup:
        raise RuntimeError(f"Structure output has duplicate candidate+group rows: {dup}")


def wrapped_abs_angle_diff(a: pd.Series, b: pd.Series) -> pd.Series:
    diff = (pd.to_numeric(a, errors="coerce") - pd.to_numeric(b, errors="coerce") + 180.0) % 360.0 - 180.0
    return diff.abs()


def robust_scale(values: pd.Series) -> tuple[float, str]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return 1.0, "fallback_empty_1"
    med = float(clean.median())
    mad = float((clean - med).abs().median())
    if math.isfinite(mad) and mad > EPS:
        return mad, "mad"
    iqr = float(clean.quantile(0.75) - clean.quantile(0.25))
    if math.isfinite(iqr) and iqr > EPS:
        return iqr, "iqr"
    std = float(clean.std(ddof=0))
    if math.isfinite(std) and std > EPS:
        return std, "std"
    return 1.0, "fallback_1"


def add_temporal(a001: pd.DataFrame, a005: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    dup_counts = a005.groupby(GROUP_KEYS, dropna=False).size().reset_index(name="a005_key_count")
    ambiguous = dup_counts[dup_counts["a005_key_count"] > 1]
    a005_unique = a005.drop_duplicates(GROUP_KEYS, keep=False).copy()
    joined = a001.merge(a005_unique, on=GROUP_KEYS, how="left", validate="many_to_one")
    joined = joined.merge(dup_counts, on=GROUP_KEYS, how="left")
    joined["a005_key_count"] = joined["a005_key_count"].fillna(0).astype(int)
    joined["temporal_join_status"] = np.select(
        [joined["a005_key_count"].eq(0), joined["a005_key_count"].gt(1)],
        ["missing", "ambiguous"],
        default="matched",
    )
    for col in ["r", "cross", "az", "pred_r", "pred_cross", "pred_az"]:
        joined[col] = pd.to_numeric(joined[col], errors="coerce")
    joined["abs_dr"] = (joined["r"] - joined["pred_r"]).abs()
    joined["abs_dcross"] = (joined["cross"] - joined["pred_cross"]).abs()
    joined["abs_daz"] = wrapped_abs_angle_diff(joined["az"], joined["pred_az"])
    joined["temporal_available"] = joined["temporal_join_status"].eq("matched") & joined[["abs_dr", "abs_dcross", "abs_daz"]].notna().all(axis=1)

    rows = []
    scale_records = []
    for key, group in joined.groupby(GROUP_KEYS, dropna=False, sort=False):
        idx = group.index
        available = group[group["temporal_available"]]
        if available.empty:
            joined.loc[idx, "temporal_distance_raw"] = math.nan
            joined.loc[idx, "temporal_rank_percentile"] = 1.0
            scale_records.append({**dict(zip(GROUP_KEYS, key)), "scale_r": math.nan, "scale_cross": math.nan, "scale_az": math.nan, "scale_method_r": "unavailable", "scale_method_cross": "unavailable", "scale_method_az": "unavailable"})
            continue
        scale_r, method_r = robust_scale(available["abs_dr"])
        scale_cross, method_cross = robust_scale(available["abs_dcross"])
        scale_az, method_az = robust_scale(available["abs_daz"])
        dist = np.sqrt(
            (group["abs_dr"] / (scale_r + EPS)) ** 2
            + (group["abs_dcross"] / (scale_cross + EPS)) ** 2
            + (group["abs_daz"] / (scale_az + EPS)) ** 2
        )
        joined.loc[idx, "temporal_distance_raw"] = dist
        unavailable_idx = joined.loc[idx].index[~joined.loc[idx, "temporal_available"].to_numpy()]
        joined.loc[unavailable_idx, "temporal_distance_raw"] = math.nan
        joined.loc[idx, "temporal_rank_percentile"] = rank_percentile(joined.loc[idx, "temporal_distance_raw"], higher_is_better=False)
        scale_records.append(
            {
                **dict(zip(GROUP_KEYS, key)),
                "scale_r": scale_r,
                "scale_cross": scale_cross,
                "scale_az": scale_az,
                "scale_method_r": method_r,
                "scale_method_cross": method_cross,
                "scale_method_az": method_az,
                "available_candidates": int(available.shape[0]),
                "group_candidates": int(group.shape[0]),
            }
        )
    summary = {
        "a005_rows": int(len(a005)),
        "a005_unique_key_rows": int(dup_counts[dup_counts["a005_key_count"].eq(1)].shape[0]),
        "a005_ambiguous_keys": int(len(ambiguous)),
        "candidate_rows_matched": int(joined["temporal_join_status"].eq("matched").sum()),
        "candidate_rows_missing": int(joined["temporal_join_status"].eq("missing").sum()),
        "candidate_rows_ambiguous": int(joined["temporal_join_status"].eq("ambiguous").sum()),
    }
    return joined, summary, pd.DataFrame(scale_records)


def rank_percentile(series: pd.Series, higher_is_better: bool) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    out = pd.Series(1.0, index=series.index, dtype=float)
    valid = values[np.isfinite(values)]
    if valid.empty:
        return out
    if len(valid) == 1:
        out.loc[valid.index] = 0.0
        return out
    ranks = valid.rank(ascending=not higher_is_better, method="average")
    out.loc[valid.index] = (ranks - 1.0) / (len(valid) - 1.0)
    return out


def join_structure(temporal_df: pd.DataFrame, structure: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    join_keys = ["candidate_id", *GROUP_KEYS]
    merged = temporal_df.merge(structure, on=join_keys, how="left", validate="one_to_one", suffixes=("", "_structure"))
    merged["structure_join_status"] = np.where(merged["s1_score"].notna(), "matched", "missing")
    missing = int(merged["structure_join_status"].eq("missing").sum())
    if missing:
        raise RuntimeError(f"Structure output missing for {missing} A001 candidate rows; refusing combined pilot.")
    summary = {
        "structure_rows": int(len(structure)),
        "a001_rows": int(len(temporal_df)),
        "matched_rows": int(merged["structure_join_status"].eq("matched").sum()),
        "missing_rows": missing,
    }
    return merged, summary


def add_structure_components(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["structure_available"] = out["structure_join_status"].eq("matched") & out["structure_feature_status"].astype(str).str.startswith("ok_")
    grouped = out.groupby(GROUP_KEYS, dropna=False, sort=False)
    for feature in ["s1_score", "s2_score", "s3_score"]:
        component = feature.replace("_score", "_rank_percentile")
        out[component] = grouped[feature].transform(lambda s: rank_percentile(s, higher_is_better=False))
        out.loc[~out["structure_available"], component] = 1.0
    return out


def add_variant_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for variant, definition in VARIANTS.items():
        score = pd.Series(0.0, index=out.index)
        for component, weight in definition["weights"].items():
            score = score + float(weight) * pd.to_numeric(out[component], errors="coerce").fillna(1.0)
        score_col = f"{variant}_score"
        rank_col = f"{variant}_rank"
        out[score_col] = score
        sorted_idx = out.sort_values(GROUP_KEYS + [score_col, "candidate_id"], ascending=True).index
        ranks = out.loc[sorted_idx, GROUP_KEYS].groupby(GROUP_KEYS, dropna=False, sort=False).cumcount() + 1
        out.loc[sorted_idx, rank_col] = ranks.to_numpy()
        out[rank_col] = out[rank_col].astype(int)
    return out


def selected_rank1(ranked: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for variant, definition in VARIANTS.items():
        view = ranked[ranked[f"{variant}_rank"].eq(1)].copy()
        view["variant"] = variant
        view["variant_name"] = definition["name"]
        view["combined_score"] = view[f"{variant}_score"]
        view["combined_rank"] = view[f"{variant}_rank"]
        rows.append(view)
    return pd.concat(rows, ignore_index=True)


def write_manifest(
    path: Path,
    args: argparse.Namespace,
    run_paths: RunPaths,
    ranked: pd.DataFrame,
    temporal_summary: dict[str, Any],
    structure_summary: dict[str, Any],
    scale_summary: pd.DataFrame,
) -> None:
    scale_methods = {}
    for col in ["scale_method_r", "scale_method_cross", "scale_method_az"]:
        if col in scale_summary.columns:
            scale_methods[col] = scale_summary[col].value_counts(dropna=False).to_dict()
    payload = {
        "run_timestamp": run_paths.timestamp,
        "input_paths": {
            "A001": args.a001,
            "A005": args.a005,
            "structure_only_dir": args.structure_dir,
            "structure_ranked": str(Path(args.structure_dir) / "pilot_structure_candidates_ranked.csv"),
        },
        "output_paths": {
            "output_dir": str(run_paths.output_dir),
            "log_path": str(run_paths.log_path),
            "ranked_candidates": str(run_paths.output_dir / "pilot_combined_candidates_ranked.csv"),
            "selected_rank1_by_variant": str(run_paths.output_dir / "pilot_combined_selected_rank1_by_variant.csv"),
        },
        "row_counts": {
            "ranked_candidates": int(len(ranked)),
            "target_groups": int(ranked[GROUP_KEYS].drop_duplicates().shape[0]),
        },
        "loaded_columns": {
            "A001": SAFE_A001_COLUMNS,
            "A005": SAFE_A005_COLUMNS,
            "structure": STRUCTURE_COLUMNS,
        },
        "join_summary": {
            "temporal": temporal_summary,
            "structure": structure_summary,
        },
        "temporal_scale_summary": {
            "scale_methods": scale_methods,
            "scale_summary_csv": str(run_paths.output_dir / "pilot_combined_temporal_scale_summary.csv"),
        },
        "structure_availability_summary": {
            "structure_available_rows": int(ranked["structure_available"].sum()),
            "structure_unavailable_rows": int((~ranked["structure_available"]).sum()),
            "feature_source_image_type_counts": ranked["feature_source_image_type"].value_counts(dropna=False).to_dict(),
        },
        "variant_definitions": VARIANTS,
        "score_rule": {
            "group_keys": GROUP_KEYS,
            "component_percentiles": "best=0, worst=1, unavailable=1",
            "combined_score": "fixed weighted sum of pre-registered percentiles",
            "lower_score_is_better": True,
            "tie_break": "candidate_id ascending only",
        },
        "forbidden_fields_not_loaded": FORBIDDEN_NOT_LOADED,
        "no_gt_no_a021_no_source_no_legacy_score_statement": (
            "Pilot ranking reads no A019 final boxes, no A021 condition labels, no candidate_source, "
            "no temporal_factor_score, no delta_* legacy residuals, and no score/lr_score/sar_factor_score."
        ),
        "display_pseudocolor_risk_statement": (
            "Structure component is inherited from display/pseudocolor SAR image features, not raw SAR intensity."
        ),
        "a005_legacy_soft_prior_risk_statement": (
            "Temporal component uses A005 pred_r/pred_cross/pred_az as a soft prior and recomputes residuals. "
            "Legacy A005 score fields are not used."
        ),
        "repair_notes": REPAIR_NOTES,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> int:
    args = parse_args()
    run_paths = RunPaths(args.output_root, args.log_root)
    setup_logging(run_paths.log_path)
    logging.info("GM17 Phase4C combined structure+temporal fixed pilot started.")
    logging.info("Boundary: pre-registered fixed variants; no GT/A021/source/legacy score in ranking.")
    for note in REPAIR_NOTES:
        logging.info("Repair note: %s", note)

    a001 = read_safe_csv(Path(args.a001), SAFE_A001_COLUMNS, "A001")
    validate_a001(a001)
    a005 = read_safe_csv(Path(args.a005), SAFE_A005_COLUMNS, "A005")
    structure_path = Path(args.structure_dir) / "pilot_structure_candidates_ranked.csv"
    structure = read_safe_csv(structure_path, STRUCTURE_COLUMNS, "structure-only output")
    validate_structure(structure)

    temporal, temporal_summary, scale_summary = add_temporal(a001, a005)
    joined, structure_summary = join_structure(temporal, structure)
    combined = add_structure_components(joined)
    combined = add_variant_scores(combined)
    selected = selected_rank1(combined)

    output_cols = [
        *SAFE_A001_COLUMNS,
        "pred_r",
        "pred_cross",
        "pred_az",
        "abs_dr",
        "abs_dcross",
        "abs_daz",
        "temporal_distance_raw",
        "temporal_rank_percentile",
        "s1_score",
        "s1_rank",
        "s1_rank_percentile",
        "s2_score",
        "s2_rank",
        "s2_rank_percentile",
        "s3_score",
        "s3_rank",
        "s3_rank_percentile",
        "c1_score",
        "c1_rank",
        "c2_score",
        "c2_rank",
        "c3_score",
        "c3_rank",
        "c4_score",
        "c4_rank",
        "c5_score",
        "c5_rank",
        "temporal_join_status",
        "structure_join_status",
        "temporal_available",
        "structure_available",
        "box_to_background_ratio",
        "inside_energy_fraction",
        "optional_local_contrast",
        "edge_spillover_ratio",
        "structure_feature_status",
        "feature_source_image_type",
    ]
    combined[output_cols].to_csv(run_paths.output_dir / "pilot_combined_candidates_ranked.csv", index=False, encoding="utf-8-sig")

    selected_cols = [
        "variant",
        "variant_name",
        *SAFE_A001_COLUMNS,
        "combined_score",
        "combined_rank",
        "temporal_distance_raw",
        "temporal_rank_percentile",
        "s1_score",
        "s1_rank_percentile",
        "s2_score",
        "s2_rank_percentile",
        "c1_score",
        "c1_rank",
        "c2_score",
        "c2_rank",
        "c3_score",
        "c3_rank",
        "c4_score",
        "c4_rank",
        "c5_score",
        "c5_rank",
        "temporal_join_status",
        "structure_join_status",
        "structure_feature_status",
        "feature_source_image_type",
    ]
    selected[selected_cols].to_csv(run_paths.output_dir / "pilot_combined_selected_rank1_by_variant.csv", index=False, encoding="utf-8-sig")
    scale_summary.to_csv(run_paths.output_dir / "pilot_combined_temporal_scale_summary.csv", index=False, encoding="utf-8-sig")
    write_manifest(
        run_paths.output_dir / "pilot_combined_manifest.json",
        args,
        run_paths,
        combined,
        temporal_summary,
        structure_summary,
        scale_summary,
    )

    logging.info("Output directory: %s", run_paths.output_dir)
    logging.info("Ranked candidates: %s", len(combined))
    logging.info("Selected rank1 rows: %s", len(selected))
    logging.info("Temporal join summary: %s", temporal_summary)
    logging.info("Structure join summary: %s", structure_summary)
    print(
        json.dumps(
            {
                "output_dir": str(run_paths.output_dir),
                "ranked_candidates": int(len(combined)),
                "target_groups": int(combined[GROUP_KEYS].drop_duplicates().shape[0]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
