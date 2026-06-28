#!/usr/bin/env python
"""GM17 Phase4 factor graph prototype wrapper.

This script restructures the already validated Phase4C C3/C4 fixed factors into
explicit candidate-node, factor-value, message, and energy tables.

Boundary:
- Full A001 GM_RM017 candidate pool only.
- No new evidence, candidate generation, candidate movement, training, tuning,
  calibration, A019/A021 inference input, source fields, legacy scores, or GT.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_A001 = "output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv"
DEFAULT_A005 = "output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv"
DEFAULT_STRUCTURE_DIR = "output/gm17_phase4_structure_only_fixed_pilot_20260628_221140"
DEFAULT_COMBINED_DIR = "output/gm17_phase4_combined_structure_temporal_fixed_pilot_20260628_224407"
DEFAULT_SPEC = "docs/gm17_phase4_factor_graph_prototype_spec.md"
DEFAULT_OUTPUT_ROOT = "output"
DEFAULT_LOG_ROOT = "logs"

GROUP_KEYS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
A001_COLUMNS = [
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
A005_COLUMNS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id", "pred_r", "pred_cross", "pred_az"]
STRUCTURE_COLUMNS = [
    "candidate_id",
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
    "s1_score",
    "s1_rank",
    "s2_score",
    "s2_rank",
    "structure_feature_status",
    "feature_source_image_type",
]
COMBINED_COLUMNS = [
    "candidate_id",
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
    "temporal_distance_raw",
    "temporal_rank_percentile",
    "s1_score",
    "s1_rank_percentile",
    "s2_score",
    "s2_rank_percentile",
    "c3_score",
    "c3_rank",
    "c4_score",
    "c4_rank",
    "temporal_join_status",
    "structure_join_status",
    "structure_feature_status",
    "feature_source_image_type",
]
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
    "B_patch",
]
EPS = 1e-12
REPAIR_NOTES = [
    "Repair 1: after a failed first run, C3/C4 formula recomputation from CSV round-tripped percentiles produced "
    "sub-1e-12 score differences that changed a small number of tied ranks. The wrapper now verifies the fixed "
    "formula against Phase4C scores within tolerance, then persists the Phase4C registered C3/C4 score/rank values "
    "as factor graph energy/rank. This changes only serialization alignment, not inputs, weights, candidate pool, "
    "or C3/C4 definitions."
]


class RunPaths:
    def __init__(self, output_root: str, log_root: str) -> None:
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(output_root) / f"gm17_phase4_factor_graph_prototype_{self.timestamp}"
        self.log_path = Path(log_root) / f"gm17_phase4_factor_graph_prototype_{self.timestamp}.log"
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GM17 Phase4 factor graph prototype wrapper.")
    parser.add_argument("--a001", default=DEFAULT_A001)
    parser.add_argument("--a005", default=DEFAULT_A005)
    parser.add_argument("--structure-dir", default=DEFAULT_STRUCTURE_DIR)
    parser.add_argument("--combined-dir", default=DEFAULT_COMBINED_DIR)
    parser.add_argument("--spec", default=DEFAULT_SPEC)
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


def key_cols_as_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in GROUP_KEYS:
        if col in out.columns:
            if col == "sar_frame_num":
                out[col] = out[col].map(safe_int_text)
            else:
                out[col] = out[col].map(norm_str)
    if "candidate_id" in out.columns:
        out["candidate_id"] = out["candidate_id"].map(norm_str)
    return out


def read_columns(path: Path, columns: list[str], label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    header = pd.read_csv(path, nrows=0).columns.tolist()
    missing = [col for col in columns if col not in header]
    if missing:
        raise ValueError(f"{label} missing required columns: {missing}")
    logging.info("Reading %s from %s", label, path)
    return key_cols_as_text(pd.read_csv(path, usecols=columns))


def validate_a001(a001: pd.DataFrame) -> None:
    scenes = sorted(a001["scene"].dropna().map(norm_str).unique().tolist())
    if scenes != ["GM_RM017"]:
        raise RuntimeError(f"A001 must be GM_RM017-only, got scenes={scenes}")
    if a001["candidate_id"].duplicated().any():
        raise RuntimeError("A001 candidate_id is not unique")
    if a001.duplicated(["candidate_id", *GROUP_KEYS]).any():
        raise RuntimeError("A001 has duplicate candidate+group rows")


def merge_with_validation(a001: pd.DataFrame, combined: pd.DataFrame) -> pd.DataFrame:
    combined_keys = combined[["candidate_id", *GROUP_KEYS]].copy()
    if combined_keys.duplicated(["candidate_id", *GROUP_KEYS]).any():
        raise RuntimeError("Phase4C combined output has duplicate candidate+group rows")
    joined = a001.merge(combined, on=["candidate_id", *GROUP_KEYS], how="left", validate="one_to_one")
    missing = int(joined["temporal_rank_percentile"].isna().sum())
    if missing:
        raise RuntimeError(f"Phase4C combined factors missing for {missing} A001 candidates")
    extra = combined_keys.merge(a001[["candidate_id", *GROUP_KEYS]], on=["candidate_id", *GROUP_KEYS], how="left", indicator=True)
    extra_count = int(extra["_merge"].eq("left_only").sum())
    if extra_count:
        raise RuntimeError(f"Phase4C combined output has {extra_count} rows outside A001")
    return joined


def join_summary(a001: pd.DataFrame, a005: pd.DataFrame, structure: pd.DataFrame, combined: pd.DataFrame) -> dict[str, Any]:
    a005_counts = a005.groupby(GROUP_KEYS, dropna=False).size().reset_index(name="n")
    ambiguous_a005 = int((a005_counts["n"] > 1).sum())
    a001_groups = a001[GROUP_KEYS].drop_duplicates()
    a005_join = a001_groups.merge(a005_counts, on=GROUP_KEYS, how="left")
    structure_keys = structure[["candidate_id", *GROUP_KEYS]].drop_duplicates()
    structure_join = a001[["candidate_id", *GROUP_KEYS]].merge(
        structure_keys.assign(structure_present=True), on=["candidate_id", *GROUP_KEYS], how="left"
    )
    combined_keys = combined[["candidate_id", *GROUP_KEYS]].drop_duplicates()
    combined_join = a001[["candidate_id", *GROUP_KEYS]].merge(
        combined_keys.assign(combined_present=True), on=["candidate_id", *GROUP_KEYS], how="left"
    )
    return {
        "a005": {
            "a005_rows": int(len(a005)),
            "a005_unique_key_rows": int((a005_counts["n"] == 1).sum()),
            "a005_ambiguous_keys": ambiguous_a005,
            "a001_groups": int(len(a001_groups)),
            "a001_groups_with_a005": int(a005_join["n"].notna().sum()),
            "a001_groups_missing_a005": int(a005_join["n"].isna().sum()),
        },
        "structure": {
            "structure_rows_loaded": int(len(structure)),
            "a001_rows": int(len(a001)),
            "candidate_rows_matched": int(structure_join["structure_present"].fillna(False).sum()),
            "candidate_rows_missing": int(structure_join["structure_present"].isna().sum()),
        },
        "phase4c_combined": {
            "combined_rows_loaded": int(len(combined)),
            "a001_rows": int(len(a001)),
            "candidate_rows_matched": int(combined_join["combined_present"].fillna(False).sum()),
            "candidate_rows_missing": int(combined_join["combined_present"].isna().sum()),
        },
    }


def build_nodes(a001: pd.DataFrame) -> pd.DataFrame:
    out = a001[A001_COLUMNS].copy()
    out["node_status"] = "active_full_a001_gm_rm017"
    return out


def build_factor_values(joined: pd.DataFrame) -> pd.DataFrame:
    out = joined[
        [
            "candidate_id",
            *GROUP_KEYS,
            "temporal_distance_raw",
            "temporal_rank_percentile",
            "s1_score",
            "s1_rank_percentile",
            "s2_score",
            "s2_rank_percentile",
            "temporal_join_status",
            "structure_join_status",
            "structure_feature_status",
            "feature_source_image_type",
        ]
    ].copy()
    out["temporal_factor_status"] = np.where(out["temporal_join_status"].eq("matched"), "available", out["temporal_join_status"])
    out["sar_structure_factor_status"] = np.where(
        out["structure_join_status"].eq("matched") & out["structure_feature_status"].astype(str).str.startswith("ok_"),
        "available_display_image",
        "unavailable",
    )
    return out[
        [
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
    ]


def build_messages(factors: pd.DataFrame) -> pd.DataFrame:
    out = factors[["candidate_id", *GROUP_KEYS, "temporal_rank_percentile", "s1_rank_percentile"]].copy()
    out = out.rename(columns={"temporal_rank_percentile": "temporal_message", "s1_rank_percentile": "sar_structure_message"})
    out["message_normalization"] = "groupwise_rank_percentile_best_0_worst_1"
    out["unavailable_component_policy"] = "component_percentile_1"
    out["lower_is_better"] = True
    return out[
        [
            "candidate_id",
            *GROUP_KEYS,
            "temporal_message",
            "sar_structure_message",
            "message_normalization",
            "unavailable_component_policy",
            "lower_is_better",
        ]
    ]


def assign_rank(df: pd.DataFrame, score_col: str, rank_col: str) -> pd.Series:
    ranked = df.sort_values([*GROUP_KEYS, score_col, "candidate_id"], ascending=[True, True, True, True, True, True])
    return ranked.groupby(GROUP_KEYS, dropna=False).cumcount().add(1).reindex(df.index)


def build_energy(messages: pd.DataFrame, combined: pd.DataFrame) -> pd.DataFrame:
    out = messages[["candidate_id", *GROUP_KEYS, "temporal_message", "sar_structure_message"]].copy()
    out["formula_c3_energy"] = 0.67 * pd.to_numeric(out["temporal_message"], errors="coerce") + 0.33 * pd.to_numeric(
        out["sar_structure_message"], errors="coerce"
    )
    out["formula_c4_diagnostic_energy"] = 0.33 * pd.to_numeric(out["temporal_message"], errors="coerce") + 0.67 * pd.to_numeric(
        out["sar_structure_message"], errors="coerce"
    )
    phase4c = combined[["candidate_id", *GROUP_KEYS, "c3_score", "c3_rank", "c4_score", "c4_rank"]].copy()
    out = out.merge(phase4c, on=["candidate_id", *GROUP_KEYS], how="inner", validate="one_to_one")
    c3_diff = pd.to_numeric(out["formula_c3_energy"], errors="coerce") - pd.to_numeric(out["c3_score"], errors="coerce")
    c4_diff = pd.to_numeric(out["formula_c4_diagnostic_energy"], errors="coerce") - pd.to_numeric(out["c4_score"], errors="coerce")
    if np.nanmax(np.abs(c3_diff)) > EPS or np.nanmax(np.abs(c4_diff)) > EPS:
        raise RuntimeError(
            f"Phase4C registered scores do not match C3/C4 formula within tolerance: "
            f"max_c3={np.nanmax(np.abs(c3_diff))}, max_c4={np.nanmax(np.abs(c4_diff))}"
        )
    out["c3_temporal_weight"] = 0.67
    out["c3_structure_weight"] = 0.33
    out["c3_energy"] = pd.to_numeric(out["c3_score"], errors="coerce")
    out["c3_rank"] = pd.to_numeric(out["c3_rank"], errors="coerce").astype(int)
    out["c4_diagnostic_energy"] = pd.to_numeric(out["c4_score"], errors="coerce")
    out["c4_diagnostic_rank"] = pd.to_numeric(out["c4_rank"], errors="coerce").astype(int)
    out["tie_break_used"] = "candidate_id_ascending_only"
    return out[
        [
            "candidate_id",
            *GROUP_KEYS,
            "c3_temporal_weight",
            "c3_structure_weight",
            "c3_energy",
            "c3_rank",
            "c4_diagnostic_energy",
            "c4_diagnostic_rank",
            "tie_break_used",
        ]
    ]


def build_selected(nodes: pd.DataFrame, energy: pd.DataFrame) -> pd.DataFrame:
    node_cols = ["candidate_id", *GROUP_KEYS, "cx", "cy", "w", "h", "heading", "r", "az", "cross"]
    enriched = energy.merge(nodes[node_cols], on=["candidate_id", *GROUP_KEYS], how="left", validate="one_to_one")
    c3 = enriched[enriched["c3_rank"].eq(1)].copy()
    c4 = enriched[enriched["c4_diagnostic_rank"].eq(1)].copy()
    c4 = c4[
        [
            *GROUP_KEYS,
            "candidate_id",
            "c4_diagnostic_energy",
            "c4_diagnostic_rank",
        ]
    ].rename(
        columns={
            "candidate_id": "c4_diagnostic_candidate_id",
            "c4_diagnostic_energy": "c4_diagnostic_rank1_energy",
            "c4_diagnostic_rank": "c4_diagnostic_rank1",
        }
    )
    c3["prototype_branch"] = "c3_primary"
    c3 = c3.rename(columns={"candidate_id": "c3_candidate_id", "c3_energy": "c3_rank1_energy", "c3_rank": "c3_rank1"})
    selected = c3.merge(c4, on=GROUP_KEYS, how="left", validate="one_to_one")
    return selected[
        [
            *GROUP_KEYS,
            "prototype_branch",
            "c3_candidate_id",
            "cx",
            "cy",
            "w",
            "h",
            "heading",
            "r",
            "az",
            "cross",
            "c3_rank1_energy",
            "c3_rank1",
            "c4_diagnostic_candidate_id",
            "c4_diagnostic_rank1_energy",
            "c4_diagnostic_rank1",
        ]
    ]


def alignment_with_phase4c(energy: pd.DataFrame, combined: pd.DataFrame) -> dict[str, Any]:
    check = energy.merge(
        combined[["candidate_id", *GROUP_KEYS, "c3_score", "c3_rank", "c4_score", "c4_rank"]],
        on=["candidate_id", *GROUP_KEYS],
        how="left",
        validate="one_to_one",
    )
    check["c3_score_abs_diff"] = (check["c3_energy"] - check["c3_score"]).abs()
    check["c4_score_abs_diff"] = (check["c4_diagnostic_energy"] - check["c4_score"]).abs()
    c3_score_ok = bool((check["c3_score_abs_diff"] <= EPS).all())
    c4_score_ok = bool((check["c4_score_abs_diff"] <= EPS).all())
    c3_rank_ok = bool((check["c3_rank_x"].astype(int) == check["c3_rank_y"].astype(int)).all())
    c4_rank_ok = bool((check["c4_diagnostic_rank"].astype(int) == check["c4_rank"].astype(int)).all())
    return {
        "c3_score_all_equal": c3_score_ok,
        "c3_rank_all_equal": c3_rank_ok,
        "c4_score_all_equal": c4_score_ok,
        "c4_rank_all_equal": c4_rank_ok,
        "max_c3_score_abs_diff": float(check["c3_score_abs_diff"].max()),
        "max_c4_score_abs_diff": float(check["c4_score_abs_diff"].max()),
        "c3_rank_mismatch_count": int((check["c3_rank_x"].astype(int) != check["c3_rank_y"].astype(int)).sum()),
        "c4_rank_mismatch_count": int((check["c4_diagnostic_rank"].astype(int) != check["c4_rank"].astype(int)).sum()),
    }


def write_manifest(
    path: Path,
    args: argparse.Namespace,
    run_paths: RunPaths,
    row_counts: dict[str, int],
    joins: dict[str, Any],
    alignment: dict[str, Any],
) -> None:
    manifest = {
        "run_timestamp": run_paths.timestamp,
        "input_paths": {
            "A001": args.a001,
            "A005": args.a005,
            "structure_only_dir": args.structure_dir,
            "structure_ranked": str(Path(args.structure_dir) / "pilot_structure_candidates_ranked.csv"),
            "combined_dir": args.combined_dir,
            "combined_ranked": str(Path(args.combined_dir) / "pilot_combined_candidates_ranked.csv"),
            "factor_graph_spec": args.spec,
        },
        "output_paths": {
            "output_dir": str(run_paths.output_dir),
            "log_path": str(run_paths.log_path),
            "candidate_nodes": str(run_paths.output_dir / "factor_graph_candidate_nodes.csv"),
            "factor_values": str(run_paths.output_dir / "factor_graph_factor_values.csv"),
            "messages": str(run_paths.output_dir / "factor_graph_messages.csv"),
            "energy": str(run_paths.output_dir / "factor_graph_energy.csv"),
            "selected_rank1": str(run_paths.output_dir / "factor_graph_selected_rank1.csv"),
        },
        "loaded_columns": {
            "A001": A001_COLUMNS,
            "A005": A005_COLUMNS,
            "structure_only": STRUCTURE_COLUMNS,
            "phase4c_combined": COMBINED_COLUMNS,
        },
        "factor_ownership": {
            "candidate_node": "A001 safe candidate geometry, full GM_RM017 bank",
            "optical_temporal_factor": "A001 r/cross/az plus A005 pred_r/pred_cross/pred_az as already recomputed in Phase4C temporal_rank_percentile",
            "sar_structure_factor": "structure-only S1/S2 display-image features over full A001",
            "combined_baseline": "C3 fixed 0.67 temporal + 0.33 S1",
            "diagnostic_branch": "C4 fixed 0.33 temporal + 0.67 S1 diagnostic only",
            "evaluation_only": "A019/A021 not read by this prototype run script",
        },
        "candidate_pool_boundary": {
            "scene": "GM_RM017-only",
            "pool": "full A001 candidate bank",
            "no_new_candidate": True,
            "no_candidate_box_movement": True,
            "no_best_proxy_or_best_center_filter": True,
            "no_gm_rm011_or_gm_rm019_expansion": True,
        },
        "row_counts": row_counts,
        "join_summary": joins,
        "c3_rule": {
            "energy": "0.67 * temporal_rank_percentile + 0.33 * s1_rank_percentile",
            "lower_is_better": True,
            "tie_break": "candidate_id ascending only",
        },
        "c4_diagnostic_rule": {
            "energy": "0.33 * temporal_rank_percentile + 0.67 * s1_rank_percentile",
            "lower_is_better": True,
            "tie_break": "candidate_id ascending only",
            "diagnostic_only": True,
        },
        "phase4c_alignment_self_check": alignment,
        "repair_notes": REPAIR_NOTES,
        "forbidden_fields_not_loaded": FORBIDDEN_NOT_LOADED,
        "no_gt_no_a021_no_source_no_legacy_score_statement": (
            "Prototype inference reads no A019 final boxes, no A021 condition/truncation/occlusion labels, "
            "no candidate_source, no temporal_factor_score, no delta_* legacy residuals, "
            "and no score/lr_score/sar_factor_score."
        ),
        "display_pseudocolor_risk_statement": (
            "SAR structure factor is inherited from display/pseudocolor-image S1/S2 features, not raw SAR intensity."
        ),
        "a005_legacy_soft_prior_risk_statement": (
            "Temporal factor is inherited from A005 pred_r/pred_cross/pred_az as a soft prior through Phase4C recomputed temporal percentiles."
        ),
        "no_new_evidence_statement": (
            "This wrapper only restructures validated Phase4C C3/C4 factors into factor graph tables; it introduces no new evidence."
        ),
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def main() -> None:
    args = parse_args()
    run_paths = RunPaths(args.output_root, args.log_root)
    setup_logging(run_paths.log_path)
    logging.info("GM17 Phase4 factor graph prototype started.")
    logging.info("Boundary: full A001 GM_RM017, C3/C4 fixed, no GT/A021/source/legacy score in inference.")

    a001 = read_columns(Path(args.a001), A001_COLUMNS, "A001 safe fields")
    a005 = read_columns(Path(args.a005), A005_COLUMNS, "A005 safe fields")
    structure = read_columns(Path(args.structure_dir) / "pilot_structure_candidates_ranked.csv", STRUCTURE_COLUMNS, "structure-only safe output")
    combined = read_columns(Path(args.combined_dir) / "pilot_combined_candidates_ranked.csv", COMBINED_COLUMNS, "Phase4C combined output")

    validate_a001(a001)
    joined = merge_with_validation(a001, combined)
    joins = join_summary(a001, a005, structure, combined)

    nodes = build_nodes(a001)
    factors = build_factor_values(joined)
    messages = build_messages(factors)
    energy = build_energy(messages, combined)
    selected = build_selected(nodes, energy)
    alignment = alignment_with_phase4c(energy, combined)

    if not (alignment["c3_score_all_equal"] and alignment["c3_rank_all_equal"] and alignment["c4_score_all_equal"] and alignment["c4_rank_all_equal"]):
        diff_path = run_paths.output_dir / "factor_graph_phase4c_alignment_diff.csv"
        energy.merge(
            combined[["candidate_id", *GROUP_KEYS, "c3_score", "c3_rank", "c4_score", "c4_rank"]],
            on=["candidate_id", *GROUP_KEYS],
            how="left",
        ).to_csv(diff_path, index=False, encoding="utf-8-sig")
        raise RuntimeError(f"Prototype C3/C4 alignment with Phase4C failed; wrote {diff_path}")

    nodes.to_csv(run_paths.output_dir / "factor_graph_candidate_nodes.csv", index=False, encoding="utf-8-sig")
    factors.to_csv(run_paths.output_dir / "factor_graph_factor_values.csv", index=False, encoding="utf-8-sig")
    messages.to_csv(run_paths.output_dir / "factor_graph_messages.csv", index=False, encoding="utf-8-sig")
    energy.to_csv(run_paths.output_dir / "factor_graph_energy.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(run_paths.output_dir / "factor_graph_selected_rank1.csv", index=False, encoding="utf-8-sig")

    row_counts = {
        "candidate_nodes": int(len(nodes)),
        "factor_values": int(len(factors)),
        "messages": int(len(messages)),
        "energy_rows": int(len(energy)),
        "selected_rank1_rows": int(len(selected)),
        "target_groups": int(nodes[GROUP_KEYS].drop_duplicates().shape[0]),
    }
    write_manifest(run_paths.output_dir / "factor_graph_prototype_manifest.json", args, run_paths, row_counts, joins, alignment)

    logging.info("Output directory: %s", run_paths.output_dir)
    logging.info("Row counts: %s", row_counts)
    logging.info("Phase4C alignment: %s", alignment)
    print(run_paths.output_dir)


if __name__ == "__main__":
    main()
