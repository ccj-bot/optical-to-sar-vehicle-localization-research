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
        raise ValueError(f"{name} is missing required safe fields: {missing}")


def check_gm_rm017_only(name: str, df: pd.DataFrame) -> dict:
    target = df["target_identity"].astype(str).str.lower()
    accepted_patterns = ["gm_rm017", "gm17supp", "gm17_"]
    rejected_patterns = ["gm_rm011", "gm_rm019", "gm11", "gm19"]
    accepted_mask = pd.Series(False, index=df.index)
    for pattern in accepted_patterns:
        accepted_mask = accepted_mask | target.str.contains(pattern, regex=False)
    rejected_mask = pd.Series(False, index=df.index)
    for pattern in rejected_patterns:
        rejected_mask = rejected_mask | target.str.contains(pattern, regex=False)
    ok_mask = accepted_mask & (~rejected_mask)
    bad = df.loc[~ok_mask, "target_identity"].dropna().astype(str).unique().tolist()
    if bad:
        raise ValueError(f"{name} is not GM_RM017-only; examples: {bad[:10]}")
    return {
        "checked_field": "target_identity",
        "gm_rm017_only": True,
        "accepted_patterns": accepted_patterns,
        "rejected_patterns": rejected_patterns,
        "fix_note": "Accepted gm17supp/gm17_ target identities as GM_RM017 supplemental legacy rows after first run exposed this naming convention.",
        "unique_target_identity_count": int(df["target_identity"].nunique(dropna=True)),
    }


def robust_scale(values: pd.Series) -> float:
    finite = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    finite = finite[finite > 0]
    if finite.empty:
        return 1.0
    median = float(finite.median())
    if math.isfinite(median) and median > 0:
        return median
    q75 = float(finite.quantile(0.75))
    q25 = float(finite.quantile(0.25))
    iqr = q75 - q25
    if math.isfinite(iqr) and iqr > 0:
        return iqr
    max_value = float(finite.max())
    return max_value if math.isfinite(max_value) and max_value > 0 else 1.0


def infer_angle_period(az: pd.Series, pred_az: pd.Series) -> tuple[float, str]:
    combined = pd.concat([az, pred_az], ignore_index=True)
    finite = pd.to_numeric(combined, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().abs()
    if finite.empty:
        return 360.0, "degree_fallback_no_finite_angles"
    max_abs = float(finite.max())
    if max_abs <= (2 * math.pi + 0.25):
        return 2 * math.pi, "radian_auto_detected"
    return 360.0, "degree_auto_detected"


def wrapped_abs_angle_diff(a: pd.Series, b: pd.Series, period: float) -> pd.Series:
    diff = (a - b).abs()
    return np.minimum(diff, period - (diff % period))


def build_output_paths(timestamp: str, output_root: Path, log_root: Path) -> dict[str, Path]:
    output_dir = output_root / f"gm17_phase4_minimal_factor_pilot_{timestamp}"
    return {
        "output_dir": output_dir,
        "ranked_csv": output_dir / "pilot_candidates_ranked.csv",
        "selected_csv": output_dir / "pilot_selected_rank1.csv",
        "manifest_json": output_dir / "pilot_manifest.json",
        "log": log_root / f"gm17_phase4_minimal_factor_pilot_{timestamp}.log",
    }


def run(args: argparse.Namespace) -> dict:
    timestamp = args.timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = build_output_paths(timestamp, Path(args.output_root), Path(args.log_root))
    paths["output_dir"].mkdir(parents=True, exist_ok=False)
    logger = RunLogger(paths["log"])

    a001_path = Path(args.a001)
    a005_path = Path(args.a005)
    logger.write("Starting GM_RM017-only minimal factor pilot selection.")
    logger.write(f"A001: {a001_path}")
    logger.write(f"A005: {a005_path}")

    a001_columns = read_header(a001_path)
    a005_columns = read_header(a005_path)
    require_columns("A001", a001_columns, A001_SAFE_FIELDS)
    require_columns("A005", a005_columns, A005_SAFE_FIELDS)
    forbidden_present = {
        "A001": [col for col in FORBIDDEN_SORT_FIELDS if col in a001_columns],
        "A005": [col for col in FORBIDDEN_SORT_FIELDS if col in a005_columns],
    }
    logger.write(f"Forbidden fields present but excluded from ranking loads: {forbidden_present}")

    a001_header_cols = len(a001_columns)
    a005_header_cols = len(a005_columns)
    a001 = pd.read_csv(a001_path, usecols=A001_SAFE_FIELDS)
    a005 = pd.read_csv(a005_path, usecols=A005_SAFE_FIELDS)
    a001_row_count = int(len(a001))
    a005_row_count = int(len(a005))
    logger.write(f"Loaded A001 safe columns only: rows={a001_row_count}, cols={len(a001.columns)}")
    logger.write(f"Loaded A005 safe columns only: rows={a005_row_count}, cols={len(a005.columns)}")

    a001_check = check_gm_rm017_only("A001", a001)
    a005_check = check_gm_rm017_only("A005", a005)

    for col in NUMERIC_A001_FIELDS:
        a001[col] = pd.to_numeric(a001[col], errors="coerce")
    for col in NUMERIC_A005_FIELDS:
        a005[col] = pd.to_numeric(a005[col], errors="coerce")

    key_counts = a005.groupby(JOIN_KEYS, dropna=False).size().rename("a005_key_count").reset_index()
    ambiguous_keys = key_counts.loc[key_counts["a005_key_count"] > 1, JOIN_KEYS]
    a005_with_counts = a005.merge(key_counts, on=JOIN_KEYS, how="left")
    a005_non_ambiguous = (
        a005_with_counts.loc[a005_with_counts["a005_key_count"] == 1, A005_SAFE_FIELDS]
        .drop_duplicates(subset=JOIN_KEYS, keep="first")
    )

    joined = a001.merge(a005_non_ambiguous, on=JOIN_KEYS, how="left", validate="many_to_one")
    if not ambiguous_keys.empty:
        ambiguous_marker = ambiguous_keys.assign(join_ambiguous=True)
        joined = joined.merge(ambiguous_marker, on=JOIN_KEYS, how="left")
        joined["join_ambiguous"] = joined["join_ambiguous"].fillna(False).astype(bool)
    else:
        joined["join_ambiguous"] = False

    has_temporal_values = joined[["pred_r", "pred_cross", "pred_az"]].notna().all(axis=1)
    joined["missing_temporal_prior"] = (~has_temporal_values) & (~joined["join_ambiguous"])
    joined["join_status"] = np.select(
        [joined["join_ambiguous"], joined["missing_temporal_prior"]],
        ["ambiguous", "missing"],
        default="matched",
    )

    finite_geometry = joined[NUMERIC_A001_FIELDS].replace([np.inf, -np.inf], np.nan).notna().all(axis=1)
    positive_size = (joined["w"] > 0) & (joined["h"] > 0)
    joined["geometry_valid"] = finite_geometry & positive_size
    joined["geometry_status"] = np.where(joined["geometry_valid"], "valid", "invalid")
    joined["geometry_rank_key"] = np.where(joined["geometry_valid"], 0, 1)

    temporal_enabled = (joined["join_status"] == "matched") & joined[["r", "cross", "az", "pred_r", "pred_cross", "pred_az"]].notna().all(axis=1)
    joined["abs_dr"] = np.where(temporal_enabled, (joined["r"] - joined["pred_r"]).abs(), np.nan)
    joined["abs_dcross"] = np.where(temporal_enabled, (joined["cross"] - joined["pred_cross"]).abs(), np.nan)
    period, angle_unit = infer_angle_period(joined.loc[temporal_enabled, "az"], joined.loc[temporal_enabled, "pred_az"])
    joined["abs_daz"] = np.nan
    if temporal_enabled.any():
        joined.loc[temporal_enabled, "abs_daz"] = wrapped_abs_angle_diff(
            joined.loc[temporal_enabled, "az"],
            joined.loc[temporal_enabled, "pred_az"],
            period,
        )

    scales = {
        "abs_dr": robust_scale(joined.loc[temporal_enabled, "abs_dr"]),
        "abs_dcross": robust_scale(joined.loc[temporal_enabled, "abs_dcross"]),
        "abs_daz": robust_scale(joined.loc[temporal_enabled, "abs_daz"]),
    }
    joined["temporal_distance"] = np.nan
    if temporal_enabled.any():
        normalized = (
            (joined.loc[temporal_enabled, "abs_dr"] / scales["abs_dr"]) ** 2
            + (joined.loc[temporal_enabled, "abs_dcross"] / scales["abs_dcross"]) ** 2
            + (joined.loc[temporal_enabled, "abs_daz"] / scales["abs_daz"]) ** 2
        )
        joined.loc[temporal_enabled, "temporal_distance"] = np.sqrt(normalized)

    joined["temporal_status"] = np.select(
        [
            joined["join_status"] == "ambiguous",
            joined["join_status"] == "missing",
            temporal_enabled,
        ],
        ["ambiguous", "missing", "valid"],
        default="invalid",
    )
    joined["temporal_rank_key"] = np.where(joined["temporal_distance"].notna(), 0, 1)
    joined["temporal_distance_sort"] = joined["temporal_distance"].fillna(np.inf)
    joined["candidate_id_sort"] = joined["candidate_id"].astype(str)

    ranked = joined.sort_values(
        JOIN_KEYS + ["geometry_rank_key", "temporal_rank_key", "temporal_distance_sort", "candidate_id_sort"],
        kind="mergesort",
    ).copy()
    ranked["pilot_rank"] = ranked.groupby(JOIN_KEYS, dropna=False).cumcount() + 1

    output_columns = [
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
        "geometry_valid",
        "geometry_status",
        "temporal_status",
        "abs_dr",
        "abs_dcross",
        "abs_daz",
        "temporal_distance",
        "join_status",
        "missing_temporal_prior",
        "join_ambiguous",
        "pilot_rank",
    ]
    ranked_output = ranked[output_columns].copy()
    selected = ranked_output.loc[ranked_output["pilot_rank"] == 1].copy()

    ranked_output.to_csv(paths["ranked_csv"], index=False, encoding="utf-8")
    selected.to_csv(paths["selected_csv"], index=False, encoding="utf-8")

    group_count = int(ranked.groupby(JOIN_KEYS, dropna=False).ngroups)
    manifest = {
        "run_type": "GM_RM017-only minimal factor pilot selection",
        "timestamp": timestamp,
        "inputs": {
            "A001": str(a001_path),
            "A005": str(a005_path),
        },
        "input_table_shapes": {
            "A001": {"rows": a001_row_count, "columns": a001_header_cols},
            "A005": {"rows": a005_row_count, "columns": a005_header_cols},
        },
        "gm_rm017_only_checks": {
            "A001": a001_check,
            "A005": a005_check,
        },
        "used_fields_for_ranking": {
            "A001": A001_SAFE_FIELDS,
            "A005": A005_SAFE_FIELDS,
            "join_keys": JOIN_KEYS,
        },
        "forbidden_fields_present_but_not_used_for_ranking": forbidden_present,
        "forbidden_fields_not_used_for_sorting_statement": True,
        "ranking_rule": [
            "geometry_valid first",
            "valid temporal_distance first",
            "smaller recomputed temporal_distance first",
            "candidate_id stable sort fallback",
            "no GT, no legacy score, no selected behavior",
        ],
        "temporal_distance": {
            "definition": "sqrt((abs_dr/scale_dr)^2 + (abs_dcross/scale_cross)^2 + (abs_daz/scale_az)^2)",
            "scales": scales,
            "angle_period": period,
            "angle_unit": angle_unit,
            "delta_legacy_fields_used": False,
            "temporal_factor_score_used": False,
        },
        "join_summary": {
            "group_count": group_count,
            "a005_unique_join_key_count": int(len(key_counts)),
            "a005_ambiguous_join_key_count": int(len(ambiguous_keys)),
            "candidate_rows_missing_temporal_prior": int(ranked_output["missing_temporal_prior"].sum()),
            "candidate_rows_join_ambiguous": int(ranked_output["join_ambiguous"].sum()),
            "candidate_rows_temporal_valid": int((ranked_output["temporal_status"] == "valid").sum()),
        },
        "output_shapes": {
            "pilot_candidates_ranked": {"rows": int(len(ranked_output)), "columns": int(len(ranked_output.columns))},
            "pilot_selected_rank1": {"rows": int(len(selected)), "columns": int(len(selected.columns))},
        },
        "outputs": {
            "output_dir": str(paths["output_dir"]),
            "pilot_candidates_ranked": str(paths["ranked_csv"]),
            "pilot_selected_rank1": str(paths["selected_csv"]),
            "pilot_manifest": str(paths["manifest_json"]),
            "log": str(paths["log"]),
        },
    }
    with paths["manifest_json"].open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    logger.write(f"Wrote ranked candidates: {paths['ranked_csv']}")
    logger.write(f"Wrote rank1 selected candidates: {paths['selected_csv']}")
    logger.write(f"Wrote manifest: {paths['manifest_json']}")
    logger.write("Completed minimal factor pilot selection without GT/evaluation inputs.")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GM_RM017-only minimal factor pilot selection.")
    parser.add_argument("--a001", default=str(A001_DEFAULT), help="Path to A001 candidate_bank_inference.csv")
    parser.add_argument("--a005", default=str(A005_DEFAULT), help="Path to A005 gm17_temporal_inference.csv")
    parser.add_argument("--output-root", default=str(OUTPUT_ROOT_DEFAULT), help="Workspace output root")
    parser.add_argument("--log-root", default=str(LOG_ROOT_DEFAULT), help="Workspace log root")
    parser.add_argument("--timestamp", default=None, help="Optional run timestamp YYYYMMDD_HHMMSS")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
