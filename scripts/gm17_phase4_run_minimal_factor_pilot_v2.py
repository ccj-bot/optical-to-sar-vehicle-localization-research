from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[1]
A001_DEFAULT = WORKSPACE / "output" / "clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2" / "candidate_bank_inference.csv"
A005_DEFAULT = WORKSPACE / "output" / "clean_no_gt_localizer_2026-05-31_boundary_tables" / "gm17_temporal_inference.csv"
OUTPUT_ROOT_DEFAULT = WORKSPACE / "output"
LOG_ROOT_DEFAULT = WORKSPACE / "logs"

JOIN_KEYS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
A001_SAFE_FIELDS = [
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
A005_SAFE_FIELDS = [
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
    "pred_r",
    "pred_cross",
    "pred_az",
]
FORBIDDEN_SORT_FIELDS = [
    "temporal_factor_score",
    "delta_r_from_pred",
    "delta_cross_from_pred",
    "delta_az_from_pred",
    "pred_cx",
    "pred_cy",
    "pred_w",
    "pred_h",
    "pred_heading_deg",
    "score",
    "lr_score",
    "sar_factor_score",
    "candidate_source",
    "candidate_detail",
    "candidate_expansion_state",
    "candidate_expansion_reason",
    "gm17_temporal_source",
    "gm17_temporal_decision",
    "gm17_anchor_strength",
    "gm17_track_size",
    "gm17_anchor_n",
    "n_candidates",
]
NUMERIC_A001_FIELDS = ["cx", "cy", "w", "h", "heading", "r", "az", "cross"]
NUMERIC_A005_FIELDS = ["pred_r", "pred_cross", "pred_az"]


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
        raise ValueError(f"{name} missing required safe fields: {missing}")


def infer_angle_period(*series_list: pd.Series) -> tuple[float, str]:
    combined = pd.concat([pd.to_numeric(s, errors="coerce") for s in series_list], ignore_index=True)
    finite = combined.replace([np.inf, -np.inf], np.nan).dropna().abs()
    if finite.empty:
        return 360.0, "degree_fallback_no_finite_angles"
    if float(finite.max()) <= (2 * math.pi + 0.25):
        return 2 * math.pi, "radian_auto_detected"
    return 360.0, "degree_auto_detected"


def wrapped_abs_angle_diff(a: pd.Series, b: pd.Series, period: float) -> pd.Series:
    raw = (pd.to_numeric(a, errors="coerce") - pd.to_numeric(b, errors="coerce")).abs()
    return np.minimum(raw % period, period - (raw % period))


def robust_positive_scale(values: pd.Series) -> tuple[float, str]:
    finite = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    finite = finite[finite > 0]
    if finite.empty:
        return 1.0, "fallback_1_no_positive_values"
    mad_median = float(finite.median())
    if math.isfinite(mad_median) and mad_median > 0:
        return mad_median, "median_positive"
    q75 = float(finite.quantile(0.75))
    q25 = float(finite.quantile(0.25))
    iqr = q75 - q25
    if math.isfinite(iqr) and iqr > 0:
        return iqr, "iqr_positive"
    return 1.0, "fallback_1_zero_scale"


def robust_group_deviation(values: pd.Series) -> tuple[pd.Series, float, float, str]:
    numeric = pd.to_numeric(values, errors="coerce")
    med = float(numeric.median()) if numeric.notna().any() else float("nan")
    abs_dev = (numeric - med).abs()
    scale = float(abs_dev.median()) if abs_dev.notna().any() else float("nan")
    method = "mad"
    if not math.isfinite(scale) or scale <= 0:
        q75 = float(numeric.quantile(0.75)) if numeric.notna().any() else float("nan")
        q25 = float(numeric.quantile(0.25)) if numeric.notna().any() else float("nan")
        scale = q75 - q25
        method = "iqr"
    if not math.isfinite(scale) or scale <= 0:
        scale = 1.0
        method = "fallback_1"
    return abs_dev / scale, med, scale, method


def circular_center(values: pd.Series, period: float) -> float:
    numeric = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if numeric.empty:
        return float("nan")
    radians = numeric.to_numpy(dtype=float) / period * 2 * math.pi
    sin_mean = float(np.sin(radians).mean())
    cos_mean = float(np.cos(radians).mean())
    if abs(sin_mean) < 1e-12 and abs(cos_mean) < 1e-12:
        return float(numeric.median())
    angle = math.atan2(sin_mean, cos_mean)
    if angle < 0:
        angle += 2 * math.pi
    center = angle / (2 * math.pi) * period
    original_median = float(numeric.median())
    if original_median < 0 and center > period / 2:
        center -= period
    return center


def robust_group_angle_deviation(values: pd.Series, period: float) -> tuple[pd.Series, float, float, str]:
    center = circular_center(values, period)
    if not math.isfinite(center):
        return pd.Series(np.nan, index=values.index), center, 1.0, "fallback_1_no_center"
    diffs = wrapped_abs_angle_diff(values, pd.Series(center, index=values.index), period)
    scale = float(pd.Series(diffs).median()) if pd.Series(diffs).notna().any() else float("nan")
    method = "mad_angle"
    if not math.isfinite(scale) or scale <= 0:
        q75 = float(pd.Series(diffs).quantile(0.75)) if pd.Series(diffs).notna().any() else float("nan")
        q25 = float(pd.Series(diffs).quantile(0.25)) if pd.Series(diffs).notna().any() else float("nan")
        scale = q75 - q25
        method = "iqr_angle"
    if not math.isfinite(scale) or scale <= 0:
        scale = 1.0
        method = "fallback_1_angle"
    return pd.Series(diffs, index=values.index) / scale, center, scale, method


def add_group_geometry_features(df: pd.DataFrame, angle_period: float) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    out["aspect"] = np.maximum(out["w"], out["h"]) / np.minimum(out["w"], out["h"])
    out["area"] = out["w"] * out["h"]
    for col in [
        "aspect_deviation",
        "area_deviation",
        "heading_deviation",
        "r_deviation",
        "cross_deviation",
        "az_deviation",
    ]:
        out[col] = np.nan
    for col in ["aspect", "area", "heading", "r", "cross", "az"]:
        out[f"group_median_{col}"] = np.nan
        out[f"group_scale_{col}"] = np.nan
        out[f"group_scale_method_{col}"] = ""

    method_counts: dict[str, int] = {}
    for _, idx in out.groupby(JOIN_KEYS, dropna=False).groups.items():
        idx_list = list(idx)
        group = out.loc[idx_list]
        for col, dev_col in [
            ("aspect", "aspect_deviation"),
            ("area", "area_deviation"),
            ("r", "r_deviation"),
            ("cross", "cross_deviation"),
        ]:
            dev, med, scale, method = robust_group_deviation(group[col])
            out.loc[idx_list, dev_col] = dev.values
            out.loc[idx_list, f"group_median_{col}"] = med
            out.loc[idx_list, f"group_scale_{col}"] = scale
            out.loc[idx_list, f"group_scale_method_{col}"] = method
            method_counts[f"{col}:{method}"] = method_counts.get(f"{col}:{method}", 0) + 1
        for col, dev_col in [("heading", "heading_deviation"), ("az", "az_deviation")]:
            dev, center, scale, method = robust_group_angle_deviation(group[col], angle_period)
            out.loc[idx_list, dev_col] = dev.values
            out.loc[idx_list, f"group_median_{col}"] = center
            out.loc[idx_list, f"group_scale_{col}"] = scale
            out.loc[idx_list, f"group_scale_method_{col}"] = method
            method_counts[f"{col}:{method}"] = method_counts.get(f"{col}:{method}", 0) + 1

    components = ["heading_deviation", "r_deviation", "cross_deviation", "az_deviation", "area_deviation"]
    out["geometry_cluster_distance"] = np.sqrt(np.square(out[components].fillna(0.0)).sum(axis=1) / len(components))
    out.loc[~out["geometry_valid"], "geometry_cluster_distance"] = np.inf
    return out, method_counts


def build_paths(timestamp: str, output_root: Path, log_root: Path) -> dict[str, Path]:
    out_dir = output_root / f"gm17_phase4_minimal_factor_pilot_v2_{timestamp}"
    return {
        "output_dir": out_dir,
        "ranked_csv": out_dir / "pilot_v2_candidates_ranked.csv",
        "selected_csv": out_dir / "pilot_v2_selected_rank1_by_variant.csv",
        "manifest_json": out_dir / "pilot_v2_manifest.json",
        "log": log_root / f"gm17_phase4_minimal_factor_pilot_v2_{timestamp}.log",
    }


def run(args: argparse.Namespace) -> dict:
    timestamp = args.timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = build_paths(timestamp, Path(args.output_root), Path(args.log_root))
    paths["output_dir"].mkdir(parents=True, exist_ok=False)
    logger = RunLogger(paths["log"])

    a001_path = Path(args.a001)
    a005_path = Path(args.a005)
    logger.write("Starting GM_RM017-only minimal factor pilot v2.")
    logger.write(f"Interpreter: {args.python_note}")
    logger.write(f"A001: {a001_path}")
    logger.write(f"A005: {a005_path}")

    a001_header = read_header(a001_path)
    a005_header = read_header(a005_path)
    require_columns("A001", a001_header, A001_SAFE_FIELDS)
    require_columns("A005", a005_header, A005_SAFE_FIELDS)
    forbidden_present = {
        "A001": [c for c in FORBIDDEN_SORT_FIELDS if c in a001_header],
        "A005": [c for c in FORBIDDEN_SORT_FIELDS if c in a005_header],
    }

    a001 = pd.read_csv(a001_path, usecols=A001_SAFE_FIELDS)
    a005 = pd.read_csv(a005_path, usecols=A005_SAFE_FIELDS)
    for col in NUMERIC_A001_FIELDS:
        a001[col] = pd.to_numeric(a001[col], errors="coerce")
    for col in NUMERIC_A005_FIELDS:
        a005[col] = pd.to_numeric(a005[col], errors="coerce")

    scene_values_a001 = sorted(a001["scene"].dropna().astype(str).unique().tolist())
    scene_values_a005 = sorted(a005["scene"].dropna().astype(str).unique().tolist())

    a005_key_counts = a005.groupby(JOIN_KEYS, dropna=False).size().rename("a005_key_count").reset_index()
    ambiguous_keys = a005_key_counts.loc[a005_key_counts["a005_key_count"] > 1, JOIN_KEYS]
    a005_counts = a005.merge(a005_key_counts, on=JOIN_KEYS, how="left")
    a005_unique = a005_counts.loc[a005_counts["a005_key_count"] == 1, A005_SAFE_FIELDS].drop_duplicates(JOIN_KEYS)

    joined = a001.merge(a005_unique, on=JOIN_KEYS, how="left", validate="many_to_one")
    if not ambiguous_keys.empty:
        joined = joined.merge(ambiguous_keys.assign(join_ambiguous=True), on=JOIN_KEYS, how="left")
        joined["join_ambiguous"] = joined["join_ambiguous"].fillna(False).astype(bool)
    else:
        joined["join_ambiguous"] = False

    temporal_present = joined[["pred_r", "pred_cross", "pred_az"]].notna().all(axis=1)
    joined["missing_temporal_prior"] = (~temporal_present) & (~joined["join_ambiguous"])
    joined["join_status"] = np.select(
        [joined["join_ambiguous"], joined["missing_temporal_prior"]],
        ["ambiguous", "missing"],
        default="matched",
    )

    finite_geometry = joined[NUMERIC_A001_FIELDS].replace([np.inf, -np.inf], np.nan).notna().all(axis=1)
    joined["geometry_valid"] = finite_geometry & (joined["w"] > 0) & (joined["h"] > 0)
    joined["geometry_status"] = np.where(joined["geometry_valid"], "valid", "invalid")
    joined["geometry_rank_key"] = np.where(joined["geometry_valid"], 0, 1)

    temporal_enabled = (joined["join_status"] == "matched") & joined[["r", "cross", "az", "pred_r", "pred_cross", "pred_az"]].notna().all(axis=1)
    joined["abs_dr"] = np.where(temporal_enabled, (joined["r"] - joined["pred_r"]).abs(), np.nan)
    joined["abs_dcross"] = np.where(temporal_enabled, (joined["cross"] - joined["pred_cross"]).abs(), np.nan)
    angle_period, angle_unit = infer_angle_period(joined["az"], joined["pred_az"], joined["heading"])
    joined["abs_daz"] = np.nan
    joined.loc[temporal_enabled, "abs_daz"] = wrapped_abs_angle_diff(
        joined.loc[temporal_enabled, "az"], joined.loc[temporal_enabled, "pred_az"], angle_period
    )

    temporal_scales = {}
    for col in ["abs_dr", "abs_dcross", "abs_daz"]:
        scale, method = robust_positive_scale(joined.loc[temporal_enabled, col])
        temporal_scales[col] = {"scale": scale, "method": method}
    joined["temporal_distance_raw"] = np.nan
    if temporal_enabled.any():
        joined.loc[temporal_enabled, "temporal_distance_raw"] = np.sqrt(
            (joined.loc[temporal_enabled, "abs_dr"] / temporal_scales["abs_dr"]["scale"]) ** 2
            + (joined.loc[temporal_enabled, "abs_dcross"] / temporal_scales["abs_dcross"]["scale"]) ** 2
            + (joined.loc[temporal_enabled, "abs_daz"] / temporal_scales["abs_daz"]["scale"]) ** 2
        )
    joined["temporal_zero"] = (
        temporal_enabled
        & (joined["abs_dr"].fillna(np.inf) <= 1e-12)
        & (joined["abs_dcross"].fillna(np.inf) <= 1e-12)
        & (joined["abs_daz"].fillna(np.inf) <= 1e-12)
    )
    joined["temporal_status"] = np.select(
        [joined["join_ambiguous"], joined["missing_temporal_prior"], temporal_enabled],
        ["ambiguous", "missing", "valid"],
        default="invalid",
    )

    joined, scale_methods = add_group_geometry_features(joined, angle_period)
    joined["candidate_id_sort"] = joined["candidate_id"].astype(str)
    joined["temporal_sort_distance"] = joined["temporal_distance_raw"].fillna(np.inf)

    joined["v2a_score"] = joined["temporal_distance_raw"].fillna(0.0) + joined["geometry_cluster_distance"].replace(np.inf, 1e9)
    joined["v2b_score"] = joined["geometry_cluster_distance"].replace(np.inf, 1e9)
    temporal_rank = joined.groupby(JOIN_KEYS, dropna=False)["temporal_distance_raw"].rank(method="average", pct=True, na_option="bottom")
    joined["temporal_rank_percentile"] = temporal_rank.fillna(1.0)
    joined["v2c_score"] = joined["geometry_cluster_distance"].replace(np.inf, 1e9) + joined["temporal_rank_percentile"]

    variants = {
        "v2a": ["geometry_rank_key", "v2a_score", "candidate_id_sort"],
        "v2b": ["geometry_rank_key", "v2b_score", "temporal_sort_distance", "candidate_id_sort"],
        "v2c": ["geometry_rank_key", "v2c_score", "candidate_id_sort"],
    }
    selected_rows = []
    ranked = joined.copy()
    for variant, sort_cols in variants.items():
        rank_col = f"{variant}_rank"
        ranked_sorted = ranked.sort_values(JOIN_KEYS + sort_cols, kind="mergesort")
        ranked.loc[ranked_sorted.index, rank_col] = ranked_sorted.groupby(JOIN_KEYS, dropna=False).cumcount() + 1
        first = ranked.loc[ranked[rank_col] == 1].copy()
        first["variant"] = variant
        first["rank1_candidate_id"] = first["candidate_id"]
        first["rank1_score"] = first[f"{variant}_score"]
        selected_rows.append(first)
    selected = pd.concat(selected_rows, ignore_index=True)

    output_cols = [
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
        "pred_r",
        "pred_cross",
        "pred_az",
        "geometry_valid",
        "geometry_status",
        "aspect",
        "area",
        "abs_dr",
        "abs_dcross",
        "abs_daz",
        "temporal_distance_raw",
        "temporal_zero",
        "aspect_deviation",
        "area_deviation",
        "heading_deviation",
        "r_deviation",
        "cross_deviation",
        "az_deviation",
        "geometry_cluster_distance",
        "temporal_rank_percentile",
        "v2a_score",
        "v2a_rank",
        "v2b_score",
        "v2b_rank",
        "v2c_score",
        "v2c_rank",
        "join_status",
        "missing_temporal_prior",
        "join_ambiguous",
        "temporal_status",
        "group_scale_method_aspect",
        "group_scale_method_area",
        "group_scale_method_heading",
        "group_scale_method_r",
        "group_scale_method_cross",
        "group_scale_method_az",
    ]
    ranked[output_cols].to_csv(paths["ranked_csv"], index=False, encoding="utf-8")

    selected_cols = [
        "variant",
        "rank1_candidate_id",
        "rank1_score",
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
        "pred_r",
        "pred_cross",
        "pred_az",
        "geometry_valid",
        "temporal_distance_raw",
        "geometry_cluster_distance",
        "temporal_rank_percentile",
        "temporal_zero",
        "join_status",
        "missing_temporal_prior",
        "join_ambiguous",
    ]
    selected[selected_cols].to_csv(paths["selected_csv"], index=False, encoding="utf-8")

    manifest = {
        "run_type": "GM_RM017-only minimal factor pilot v2 fixed diagnostic pilot",
        "timestamp": timestamp,
        "inputs": {
            "A001": str(a001_path),
            "A005": str(a005_path),
        },
        "row_counts": {
            "A001": int(len(a001)),
            "A005": int(len(a005)),
            "ranked_candidates": int(len(ranked)),
            "selected_rows": int(len(selected)),
            "groups": int(ranked.groupby(JOIN_KEYS, dropna=False).ngroups),
        },
        "loaded_columns": {
            "A001": A001_SAFE_FIELDS,
            "A005": A005_SAFE_FIELDS,
        },
        "forbidden_fields_not_loaded_for_sorting": FORBIDDEN_SORT_FIELDS,
        "forbidden_fields_present_but_excluded": forbidden_present,
        "scene_values": {
            "A001": scene_values_a001,
            "A005": scene_values_a005,
        },
        "join_summary": {
            "join_keys": JOIN_KEYS,
            "a005_unique_key_rows": int(len(a005_key_counts)),
            "a005_ambiguous_keys": int(len(ambiguous_keys)),
            "candidate_rows_join_ambiguous": int(ranked["join_ambiguous"].sum()),
            "candidate_rows_missing_temporal_prior": int(ranked["missing_temporal_prior"].sum()),
            "candidate_rows_matched": int((ranked["join_status"] == "matched").sum()),
        },
        "robust_scale_fallback_summary": {
            "temporal_scales": temporal_scales,
            "group_scale_methods": scale_methods,
            "angle_period": angle_period,
            "angle_unit": angle_unit,
        },
        "variant_definitions": {
            "v2a_temporal_soft_geometry_cluster": "geometry_valid first; score=temporal_distance_raw + geometry_cluster_distance; fixed 1:1.",
            "v2b_geometry_cluster_first": "geometry_valid first; geometry_cluster_distance first; temporal_distance_raw secondary.",
            "v2c_temporal_zero_neutralized": "geometry_valid first; score=geometry_cluster_distance + temporal_rank_percentile; temporal zero marked but not an absolute winner.",
        },
        "no_gt_in_ranking_statement": True,
        "no_legacy_score_statement": {
            "temporal_factor_score_used": False,
            "delta_fields_used": False,
            "score_lr_sar_factor_used": False,
            "candidate_source_used": False,
            "gm17_temporal_decision_used": False,
        },
        "outputs": {
            "output_dir": str(paths["output_dir"]),
            "pilot_v2_candidates_ranked": str(paths["ranked_csv"]),
            "pilot_v2_selected_rank1_by_variant": str(paths["selected_csv"]),
            "pilot_v2_manifest": str(paths["manifest_json"]),
            "log": str(paths["log"]),
        },
    }
    with paths["manifest_json"].open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    logger.write(f"Wrote ranked candidates: {paths['ranked_csv']}")
    logger.write(f"Wrote selected rank1 by variant: {paths['selected_csv']}")
    logger.write(f"Wrote manifest: {paths['manifest_json']}")
    logger.write("Completed v2 pilot. No GT/eval fields were read or used for ranking.")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GM_RM017-only minimal factor pilot v2.")
    parser.add_argument("--a001", default=str(A001_DEFAULT))
    parser.add_argument("--a005", default=str(A005_DEFAULT))
    parser.add_argument("--output-root", default=str(OUTPUT_ROOT_DEFAULT))
    parser.add_argument("--log-root", default=str(LOG_ROOT_DEFAULT))
    parser.add_argument("--timestamp", default=None)
    parser.add_argument("--python-note", default=str(Path("D:/MINICONDA/envs/py311/python.exe")))
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
