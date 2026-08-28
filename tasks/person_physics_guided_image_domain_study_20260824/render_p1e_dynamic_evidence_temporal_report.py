#!/usr/bin/env python3
"""Post-process and render the PERSON P1E dynamic-evidence temporal experiment.

This script is report-only. It reads the already written GT-blind candidate
nodes, temporal edges, evidence vectors, and transparent threads. Manual SAR
references and fixed spatial controls are used only for offline evaluation and
for explanatory figure selection. It does not refit P0, regenerate C2/C3,
change candidate extraction, or overwrite earlier P1E results.
"""

from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = (
    WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
)
P1E_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface"
REPORT_ROOT = P1E_ROOT / "dynamic_evidence_temporal_v1"
DATA_DIR = REPORT_ROOT / "lag1_r02"
POST_DIR = DATA_DIR / "post_analysis_v1"
VIS_DIR = POST_DIR / "visualizations"
CANDIDATE_SOURCE_ROOT = (
    P1E_ROOT
    / "candidate_recall_semantic_split_v1"
    / "single_frame_candidate_recall"
)
B0R_ROOT = P1E_ROOT / "b0r_minimal"

P0_SCRIPT = TASK_DIR / "run_p0_common_apparent_motion.py"
P1E_SCRIPT = TASK_DIR / "run_p1e_single_frame_position_specificity.py"
AUDIT_SCRIPT = TASK_DIR / "run_p1e_candidate_recall_audit.py"
DYNAMIC_SCRIPT = TASK_DIR / "run_p1e_dynamic_evidence_temporal.py"

EXPECTED_P0_SHA256 = "0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8"
EXPECTED_P1E_SHA256 = "98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1"
EXPECTED_AUDIT_SHA256 = "84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8"
EXPECTED_DYNAMIC_SHA256 = "08FC073B2F5205BBD4D40DA0DD7872F006EC4E2965EABAE1D2FA50BE28E5B529"
EXPECTED_MANIFEST_SHA256 = "8A88308699374E975B7F1A2DD937A97F023A30EFAD41C59CDC1AC71F846702B1"
EXPECTED_RUN_SUMMARY_SHA256 = "BFD0A16BFF9B6FD1BE6035B0D5BB443DDC45E24ACE44F775AE45906DB4F537ED"

MANIFEST_JSON = DATA_DIR / "runtime_graph_manifest.json"
RUN_SUMMARY_JSON = DATA_DIR / "temporal_information_gain_summary.json"
PROTOCOL_PATH = REPORT_ROOT / "00_DYNAMIC_EVIDENCE_MINIMAL_TEMPORAL_PROTOCOL_FROZEN_BEFORE_RUN.md"
SOURCE_FIXED_OFFSETS_CSV = CANDIDATE_SOURCE_ROOT / "fixed_offset_candidate_coverage.csv"
B0R_COMPARABILITY_CSV = B0R_ROOT / "b0r_pair_comparability_R02_R03.csv"
NODES_CSV = DATA_DIR / "dynamic_candidate_nodes.csv"
UNCERTAINTY_CSV = DATA_DIR / "candidate_local_p0_uncertainty.csv"
INCOMING_CSV = DATA_DIR / "destination_incoming_temporal_evidence.csv"
OUTGOING_CSV = DATA_DIR / "source_outgoing_temporal_evidence.csv"
EDGES_CSV = DATA_DIR / "candidate_edges_within_3sigma.csv"
MUTUAL_EDGES_CSV = DATA_DIR / "mutual_nearest_edges_2sigma.csv"
STATE_CSV = DATA_DIR / "dynamic_candidate_state.csv"
THREADS_CSV = DATA_DIR / "mutual_threads.csv"
THREAD_MEMBERS_CSV = DATA_DIR / "mutual_thread_members.csv"
REFERENCE_CSV = DATA_DIR / "offline_manual_reference_temporal_evaluation.csv"
OFFSET_CSV = DATA_DIR / "offline_fixed_offset_temporal_evaluation.csv"
SHARED_CSV = DATA_DIR / "offline_shared_state_transitions.csv"
PAIR_SUMMARY_CSV = DATA_DIR / "pair_condition_summary.csv"

PAIRED_REFERENCE_CSV = POST_DIR / "manual_reference_correct_vs_controls.csv"
REFERENCE_OFFSET_CSV = POST_DIR / "reference_vs_fixed_offset_temporal_comparison.csv"
DISPLAY_STRATUM_CSV = POST_DIR / "display_stratum_temporal_comparison.csv"
CASE_REGISTRY_CSV = POST_DIR / "case_registry.csv"
INTERPRETATION_JSON = POST_DIR / "dynamic_evidence_interpretation_v1.json"
VALIDATION_JSON = POST_DIR / "report_validation.json"
REPORT_MD = REPORT_ROOT / "01_DYNAMIC_EVIDENCE_TEMPORAL_INFORMATION_GAIN_REPORT.md"
METHOD_AUDIT_MD = REPORT_ROOT / "02_DYNAMIC_EVIDENCE_METHOD_AUDIT.md"
REPORT_HTML = REPORT_ROOT / "P1E_DYNAMIC_EVIDENCE_TEMPORAL_REPORT.html"

CORRECT = "CORRECT_P0"
ZERO = "ZERO_TRANSPORT"
REVERSE = "REVERSE_P0"
PERTURBED = "TANGENTIAL_PLUS_0_75M"
SHUFFLED = "SHUFFLED_SOURCE_SHIFT7"
CONDITIONS = (CORRECT, ZERO, REVERSE, PERTURBED, SHUFFLED)
GRAPH_CONDITIONS = (CORRECT, ZERO, REVERSE, PERTURBED)
CONTROL_LABELS = {
    ZERO: "No transport",
    REVERSE: "Reverse P0",
    PERTURBED: "+0.75 m tangential",
    SHUFFLED: "Shuffled source",
}
TARGETS = tuple(f"R02ZF_SARPERSON{index:02d}" for index in range(1, 5))
TARGET_COLORS = {
    "R02ZF_SARPERSON01": "#ff4040",
    "R02ZF_SARPERSON02": "#ff9f1c",
    "R02ZF_SARPERSON03": "#24d6ff",
    "R02ZF_SARPERSON04": "#c77dff",
}

CASE_SPECS = (
    {
        "pair_index": 0,
        "target_ids": (TARGETS[0], TARGETS[1]),
        "slug": "f472_f473_p01_p02_low_rank_shared",
        "note": "P01/P02 start with low-ranked, partly shared local responses; temporal support improves some ranks but is not uniquely P0-specific.",
    },
    {
        "pair_index": 0,
        "target_ids": (TARGETS[2], TARGETS[3]),
        "slug": "f472_f473_p03_p04_high_rank_shared",
        "note": "P03/P04 share a high response from the first pair; the legal state is shared rather than two resolved identities.",
    },
    {
        "pair_index": 10,
        "target_ids": (TARGETS[1],),
        "slug": "f482_f483_p02_missing_then_competed",
        "note": "P02 has no C2 node within 0.8 m at F482; the F483 nearby node exists but receives poor incoming rank, so lag1 cannot recover a missing predecessor.",
    },
    {
        "pair_index": 15,
        "target_ids": (TARGETS[0], TARGETS[1]),
        "slug": "f487_f488_low_rank_partial_recovery",
        "note": "A positive case: both low-rank P01/P02 responses improve under correct P0, although the advantage over zero transport remains modest.",
    },
    {
        "pair_index": 17,
        "target_ids": (TARGETS[0],),
        "slug": "f489_f490_p01_temporal_collapse",
        "note": "A decisive counterexample: P01 image rank 13 collapses to incoming-max rank 255 under correct P0.",
    },
    {
        "pair_index": 17,
        "target_ids": (TARGETS[2], TARGETS[3]),
        "slug": "f489_f490_p03_p04_shared_rank_collapse",
        "note": "The shared P03/P04 response remains unresolved: max/sum ranks collapse to 105/120, while mean rank 3 and a 23-node thread remain supportive.",
    },
    {
        "pair_index": 21,
        "target_ids": (TARGETS[2], TARGETS[3]),
        "slug": "f493_f494_top1_shared_temporal_collapse",
        "note": "A mixed-state counterexample: shared image Top-1 is demoted to max/sum ranks 206/220, while mean rank 2 and a 23-node thread remain supportive.",
    },
)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    return value


def number(value: Any, digits: int = 2) -> str:
    if value is None:
        return "—"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(numeric):
        return "—"
    return f"{numeric:.{digits}f}"


def pct(value: Any, digits: int = 1) -> str:
    if value is None:
        return "—"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(numeric):
        return "—"
    return f"{100.0 * numeric:.{digits}f}%"


def target_short(target_id: str) -> str:
    match = re.search(r"(\d+)$", str(target_id))
    return f"P{int(match.group(1)):02d}" if match else str(target_id)


def relative_url(path: Path) -> str:
    return path.relative_to(REPORT_ROOT).as_posix()


def read_tables() -> dict[str, pd.DataFrame]:
    paths = {
        "nodes": NODES_CSV,
        "uncertainty": UNCERTAINTY_CSV,
        "incoming": INCOMING_CSV,
        "outgoing": OUTGOING_CSV,
        "edges": EDGES_CSV,
        "mutual_edges": MUTUAL_EDGES_CSV,
        "state": STATE_CSV,
        "threads": THREADS_CSV,
        "thread_members": THREAD_MEMBERS_CSV,
        "references": REFERENCE_CSV,
        "offsets": OFFSET_CSV,
        "shared": SHARED_CSV,
        "pairs": PAIR_SUMMARY_CSV,
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(missing)
    return {name: pd.read_csv(path) for name, path in paths.items()}


def make_paired_reference(
    references: pd.DataFrame, pairs: pd.DataFrame
) -> pd.DataFrame:
    keys = ["frame_uid", "target_id"]
    pair_meta = (
        pairs[pairs["condition"] == CORRECT][
            ["pair_index", "to_frame_uid", "display_stratum", "global_holdout_p90_px"]
        ]
        .drop_duplicates("to_frame_uid")
        .rename(columns={"to_frame_uid": "frame_uid"})
    )
    base = references[references["condition"] == CORRECT].copy()
    base = base.merge(pair_meta, on="frame_uid", how="left")
    keep = [
        "incoming_max_best_rank_r80cm",
        "incoming_max_best_percentile_r80cm",
        "incoming_sum_best_rank_r80cm",
        "incoming_sum_best_percentile_r80cm",
        "incoming_mean_best_rank_r80cm",
        "incoming_mean_best_percentile_r80cm",
        "outgoing_max_best_rank_r80cm",
        "outgoing_max_best_percentile_r80cm",
        "max_thread_node_count_r80cm",
    ]
    for condition in CONDITIONS:
        subset = references[references["condition"] == condition][keys + keep].copy()
        subset = subset.rename(
            columns={column: f"{condition}__{column}" for column in keep}
        )
        if condition == CORRECT:
            base = base.drop(columns=keep).merge(subset, on=keys, how="left")
        else:
            base = base.merge(subset, on=keys, how="left")

    image_rank = base["image_best_rank_r80cm"]
    correct_rank = base[f"{CORRECT}__incoming_max_best_rank_r80cm"]
    zero_rank = base[f"{ZERO}__incoming_max_best_rank_r80cm"]
    base["image_to_correct_rank_improvement"] = image_rank - correct_rank
    base["zero_to_correct_rank_advantage"] = zero_rank - correct_rank

    def state_label(row: pd.Series) -> str:
        if not np.isfinite(row["image_best_rank_r80cm"]):
            return "CANDIDATE_MISSING_WITHIN_0_8M"
        correct_value = row[f"{CORRECT}__incoming_max_best_rank_r80cm"]
        if not np.isfinite(correct_value):
            return "NO_INCOMING_SIDE_FIRST_FRAME"
        delta = row["image_to_correct_rank_improvement"]
        if delta > 0:
            return "TEMPORAL_RANK_IMPROVED"
        if delta < 0:
            return "TEMPORAL_RANK_WORSENED"
        return "TEMPORAL_RANK_STABLE"

    def specificity_label(row: pd.Series) -> str:
        value = row["zero_to_correct_rank_advantage"]
        if not np.isfinite(value):
            return "NOT_PAIRED"
        if value > 0:
            return "CORRECT_BETTER_THAN_ZERO"
        if value < 0:
            return "CORRECT_WORSE_THAN_ZERO"
        return "TIE_WITH_ZERO"

    base["dynamic_state_label"] = base.apply(state_label, axis=1)
    base["p0_specificity_label"] = base.apply(specificity_label, axis=1)
    return base.sort_values(["frame_index", "target_id"]).reset_index(drop=True)


def make_reference_offset_comparison(
    references: pd.DataFrame, offsets: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        ref_subset = references[references["condition"] == condition]
        off_subset = offsets[offsets["condition"] == condition]
        for reference in ref_subset.to_dict("records"):
            matched = off_subset[
                (off_subset["frame_uid"] == reference["frame_uid"])
                & (off_subset["target_id"] == reference["target_id"])
            ]
            for control in matched.to_dict("records"):
                row = {
                    "condition": condition,
                    "frame_uid": reference["frame_uid"],
                    "frame_index": int(reference["frame_index"]),
                    "target_id": reference["target_id"],
                    "control_direction": control["control_direction"],
                }
                for prefix in ("image", "incoming_max"):
                    ref_value = reference[f"{prefix}_best_percentile_r80cm"]
                    off_value = control[f"{prefix}_best_percentile_r80cm"]
                    row[f"reference_{prefix}_percentile"] = ref_value
                    row[f"offset_{prefix}_percentile"] = off_value
                    row[f"reference_minus_offset_{prefix}_percentile"] = (
                        ref_value - off_value
                        if np.isfinite(ref_value) and np.isfinite(off_value)
                        else np.nan
                    )
                ref_thread = reference["max_thread_node_count_r80cm"]
                off_thread = control["max_thread_node_count_r80cm"]
                row["reference_thread_node_count"] = ref_thread
                row["offset_thread_node_count"] = off_thread
                row["reference_minus_offset_thread_node_count"] = (
                    ref_thread - off_thread
                    if np.isfinite(ref_thread) and np.isfinite(off_thread)
                    else np.nan
                )
                rows.append(row)
    return pd.DataFrame(rows)


def paired_rank_summary(
    references: pd.DataFrame, control: str, metric: str
) -> dict[str, Any]:
    keys = ["frame_uid", "target_id"]
    correct = references[references["condition"] == CORRECT].set_index(keys)
    other = references[references["condition"] == control].set_index(keys)
    joined = correct[[metric]].join(other[[metric]], lsuffix="_correct", rsuffix="_control")
    joined = joined.dropna()
    delta = joined[f"{metric}_control"] - joined[f"{metric}_correct"]
    return {
        "control": control,
        "metric": metric,
        "paired_count": int(len(delta)),
        "median_control_rank_minus_correct_rank": float(delta.median()),
        "correct_better_fraction": float((delta > 0).mean()),
        "tie_fraction": float((delta == 0).mean()),
        "correct_worse_fraction": float((delta < 0).mean()),
    }


def build_target_summaries(paired: pd.DataFrame) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for target_id, rows in paired.groupby("target_id", sort=True):
        evaluable = rows.dropna(
            subset=[f"{CORRECT}__incoming_max_best_rank_r80cm"]
        )
        specificity = evaluable.dropna(subset=["zero_to_correct_rank_advantage"])
        output.append(
            {
                "target_id": target_id,
                "target": target_short(target_id),
                "reference_count": int(len(rows)),
                "candidate_missing_count_0_8m": int(
                    rows["image_best_rank_r80cm"].isna().sum()
                ),
                "incoming_evaluable_count": int(len(evaluable)),
                "median_image_rank": float(rows["image_best_rank_r80cm"].median()),
                "median_correct_incoming_max_rank": float(
                    evaluable[f"{CORRECT}__incoming_max_best_rank_r80cm"].median()
                ),
                "median_image_to_correct_rank_improvement": float(
                    evaluable["image_to_correct_rank_improvement"].median()
                ),
                "correct_improved_vs_image_fraction": float(
                    (evaluable["image_to_correct_rank_improvement"] > 0).mean()
                ),
                "correct_worsened_vs_image_fraction": float(
                    (evaluable["image_to_correct_rank_improvement"] < 0).mean()
                ),
                "median_zero_minus_correct_rank": float(
                    specificity["zero_to_correct_rank_advantage"].median()
                ),
                "correct_better_than_zero_fraction": float(
                    (specificity["zero_to_correct_rank_advantage"] > 0).mean()
                ),
                "correct_tied_with_zero_fraction": float(
                    (specificity["zero_to_correct_rank_advantage"] == 0).mean()
                ),
                "correct_worse_than_zero_fraction": float(
                    (specificity["zero_to_correct_rank_advantage"] < 0).mean()
                ),
                "severe_temporal_worsening_count_at_least_50_ranks": int(
                    (evaluable["image_to_correct_rank_improvement"] <= -50).sum()
                ),
                "median_reference_near_thread_length": float(
                    rows[f"{CORRECT}__max_thread_node_count_r80cm"].median()
                ),
            }
        )
    return output


def build_display_stratum_rows(
    references: pd.DataFrame, pairs: pd.DataFrame
) -> pd.DataFrame:
    output: list[dict[str, Any]] = []
    correct_pairs = pairs[pairs["condition"] == CORRECT].set_index("pair_index")
    for control in (ZERO, REVERSE, PERTURBED):
        control_pairs = pairs[pairs["condition"] == control].set_index("pair_index")
        joined = correct_pairs[
            ["display_stratum", "median_nearest_normalized_error_source_to_destination"]
        ].join(
            control_pairs[["median_nearest_normalized_error_source_to_destination"]],
            lsuffix="_correct",
            rsuffix="_control",
        )
        joined["advantage"] = (
            joined["median_nearest_normalized_error_source_to_destination_control"]
            - joined["median_nearest_normalized_error_source_to_destination_correct"]
        )
        for stratum, rows in joined.groupby("display_stratum"):
            output.append(
                {
                    "level": "GT_BLIND_PAIR_GEOMETRY",
                    "control": control,
                    "display_stratum": stratum,
                    "count": int(len(rows)),
                    "median_control_error_minus_correct_error": float(
                        rows["advantage"].median()
                    ),
                    "correct_lower_error_fraction": float(
                        (rows["advantage"] > 0).mean()
                    ),
                    "median_control_rank_minus_correct_rank": np.nan,
                    "correct_better_rank_fraction": np.nan,
                    "tie_rank_fraction": np.nan,
                    "correct_worse_rank_fraction": np.nan,
                }
            )

    pair_meta = (
        pairs[pairs["condition"] == CORRECT][["to_frame_uid", "display_stratum"]]
        .drop_duplicates("to_frame_uid")
        .rename(columns={"to_frame_uid": "frame_uid"})
    )
    enriched = references.merge(pair_meta, on="frame_uid", how="left")
    keys = ["frame_uid", "target_id"]
    correct = enriched[enriched["condition"] == CORRECT].set_index(keys)
    for control in (ZERO, REVERSE, PERTURBED, SHUFFLED):
        other = enriched[enriched["condition"] == control].set_index(keys)
        joined = correct[
            ["display_stratum", "incoming_max_best_rank_r80cm"]
        ].join(
            other[["incoming_max_best_rank_r80cm"]],
            lsuffix="_correct",
            rsuffix="_control",
        )
        joined = joined.dropna()
        joined["advantage"] = (
            joined["incoming_max_best_rank_r80cm_control"]
            - joined["incoming_max_best_rank_r80cm_correct"]
        )
        for stratum, rows in joined.groupby("display_stratum"):
            output.append(
                {
                    "level": "OFFLINE_REFERENCE_RANK",
                    "control": control,
                    "display_stratum": stratum,
                    "count": int(len(rows)),
                    "median_control_error_minus_correct_error": np.nan,
                    "correct_lower_error_fraction": np.nan,
                    "median_control_rank_minus_correct_rank": float(
                        rows["advantage"].median()
                    ),
                    "correct_better_rank_fraction": float(
                        (rows["advantage"] > 0).mean()
                    ),
                    "tie_rank_fraction": float((rows["advantage"] == 0).mean()),
                    "correct_worse_rank_fraction": float(
                        (rows["advantage"] < 0).mean()
                    ),
                }
            )
    return pd.DataFrame(output)


def build_transport_scale(
    outgoing: pd.DataFrame, nodes: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, Any]]:
    correct = outgoing[outgoing["condition"] == CORRECT].merge(
        nodes[["node_id", "x_px", "y_px", "px_per_m"]],
        left_on="source_node_id",
        right_on="node_id",
        how="left",
    )
    correct["transport_displacement_m"] = np.hypot(
        correct["predicted_x_px"] - correct["x_px"],
        correct["predicted_y_px"] - correct["y_px"],
    ) / correct["px_per_m"]
    per_pair = (
        correct.groupby(["pair_index", "actual_from_frame_uid", "to_frame_uid"])
        .agg(
            transport_displacement_m=("transport_displacement_m", "median"),
            sigma_region_m=("sigma_region_m", "median"),
            local_p0_p90_px=("local_holdout_p90_px", "median"),
        )
        .reset_index()
    )
    ratio = per_pair["transport_displacement_m"] / per_pair["sigma_region_m"]
    summary = {
        "pair_count": int(len(per_pair)),
        "median_transport_displacement_m": float(
            per_pair["transport_displacement_m"].median()
        ),
        "median_sigma_region_m": float(per_pair["sigma_region_m"].median()),
        "median_transport_to_sigma_ratio": float(ratio.median()),
        "min_transport_displacement_m": float(
            per_pair["transport_displacement_m"].min()
        ),
        "max_transport_displacement_m": float(
            per_pair["transport_displacement_m"].max()
        ),
    }
    return per_pair, summary


def build_fixed_offset_summary(comparison: pd.DataFrame) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for condition in GRAPH_CONDITIONS:
        rows = comparison[comparison["condition"] == condition]
        image = rows.dropna(
            subset=["reference_minus_offset_image_percentile"]
        )
        temporal = rows.dropna(
            subset=["reference_minus_offset_incoming_max_percentile"]
        )
        thread = rows.dropna(
            subset=["reference_minus_offset_thread_node_count"]
        )
        output.append(
            {
                "condition": condition,
                "image_pair_count": int(len(image)),
                "median_reference_minus_offset_image_percentile": float(
                    image["reference_minus_offset_image_percentile"].median()
                ),
                "positive_image_margin_fraction": float(
                    (image["reference_minus_offset_image_percentile"] > 0).mean()
                ),
                "temporal_pair_count": int(len(temporal)),
                "median_reference_minus_offset_temporal_percentile": float(
                    temporal[
                        "reference_minus_offset_incoming_max_percentile"
                    ].median()
                ),
                "positive_temporal_margin_fraction": float(
                    (
                        temporal[
                            "reference_minus_offset_incoming_max_percentile"
                        ]
                        > 0
                    ).mean()
                ),
                "thread_pair_count": int(len(thread)),
                "median_reference_minus_offset_thread_nodes": float(
                    thread["reference_minus_offset_thread_node_count"].median()
                ),
                "reference_longer_thread_fraction": float(
                    (thread["reference_minus_offset_thread_node_count"] > 0).mean()
                ),
            }
        )
    return output


def build_method_audit(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    state = tables["state"]
    mutual_edges = tables["mutual_edges"]
    uncertainty = tables["uncertainty"]
    outgoing = tables["outgoing"]
    references = tables["references"]
    shared = tables["shared"]
    pairs = tables["pairs"]
    nodes = tables["nodes"]

    rank_columns = {
        "incoming_geometry_rank": "geometry",
        "incoming_support_max_rank": "max",
        "incoming_support_sum_rank": "sum",
        "incoming_support_mean_rank": "mean",
    }
    rank_similarity: list[dict[str, Any]] = []
    correct_state = state[state["condition"] == CORRECT]
    zero_state = state[state["condition"] == ZERO]
    for column, label in rank_columns.items():
        joined = correct_state[["node_id", "frame_uid", column]].merge(
            zero_state[["node_id", column]],
            on="node_id",
            suffixes=("_correct", "_zero"),
        )
        frame_rows: list[dict[str, Any]] = []
        for frame_uid, rows in joined.groupby("frame_uid"):
            valid = rows[[f"{column}_correct", f"{column}_zero"]].dropna()
            if len(valid) <= 2:
                continue
            delta = valid[f"{column}_zero"] - valid[f"{column}_correct"]
            frame_rows.append(
                {
                    "frame_uid": frame_uid,
                    "candidate_count": int(len(valid)),
                    "spearman": float(
                        valid[f"{column}_correct"].corr(
                            valid[f"{column}_zero"], method="spearman"
                        )
                    ),
                    "exact_rank_tie_fraction": float((delta == 0).mean()),
                    "median_absolute_rank_delta": float(np.abs(delta).median()),
                }
            )
        frame_table = pd.DataFrame(frame_rows)
        overall = joined[[f"{column}_correct", f"{column}_zero"]].dropna()
        rank_similarity.append(
            {
                "component": label,
                "frame_count": int(len(frame_table)),
                "median_frame_spearman_correct_vs_zero": float(
                    frame_table["spearman"].median()
                ),
                "overall_spearman_correct_vs_zero": float(
                    overall[f"{column}_correct"].corr(
                        overall[f"{column}_zero"], method="spearman"
                    )
                ),
                "median_frame_exact_rank_tie_fraction": float(
                    frame_table["exact_rank_tie_fraction"].median()
                ),
                "median_frame_absolute_rank_delta": float(
                    frame_table["median_absolute_rank_delta"].median()
                ),
            }
        )

    edge_overlap: list[dict[str, Any]] = []
    correct_edge_set = set(
        map(
            tuple,
            mutual_edges[mutual_edges["condition"] == CORRECT][
                ["pair_index", "source_node_id", "destination_node_id"]
            ].to_numpy(),
        )
    )
    for control in (ZERO, REVERSE, PERTURBED):
        control_set = set(
            map(
                tuple,
                mutual_edges[mutual_edges["condition"] == control][
                    ["pair_index", "source_node_id", "destination_node_id"]
                ].to_numpy(),
            )
        )
        intersection = correct_edge_set & control_set
        union = correct_edge_set | control_set
        edge_overlap.append(
            {
                "control": control,
                "correct_edge_count": int(len(correct_edge_set)),
                "control_edge_count": int(len(control_set)),
                "intersection_count": int(len(intersection)),
                "intersection_over_correct": float(
                    len(intersection) / len(correct_edge_set)
                ),
                "jaccard": float(len(intersection) / len(union)),
            }
        )

    thread_similarity: list[dict[str, Any]] = []
    correct_threads = correct_state[["node_id", "thread_node_count"]]
    for control in (ZERO, REVERSE, PERTURBED):
        control_threads = state[state["condition"] == control][
            ["node_id", "thread_node_count"]
        ]
        joined = correct_threads.merge(
            control_threads,
            on="node_id",
            suffixes=("_correct", "_control"),
        ).dropna()
        delta = (
            joined["thread_node_count_control"]
            - joined["thread_node_count_correct"]
        )
        thread_similarity.append(
            {
                "control": control,
                "node_count": int(len(joined)),
                "spearman": float(
                    joined["thread_node_count_correct"].corr(
                        joined["thread_node_count_control"], method="spearman"
                    )
                ),
                "exact_equal_fraction": float((delta == 0).mean()),
                "median_absolute_delta": float(np.abs(delta).median()),
            }
        )

    shared_keys = ["group", "from_frame", "to_frame", "graph_mode"]
    correct_shared = shared[shared["condition"] == CORRECT][
        shared_keys + ["reachable_state"]
    ]
    zero_shared = shared[shared["condition"] == ZERO][
        shared_keys + ["reachable_state"]
    ]
    shared_joined = correct_shared.merge(
        zero_shared,
        on=shared_keys,
        suffixes=("_correct", "_zero"),
    )

    density_correlations: list[dict[str, Any]] = []
    density_columns = {
        "incoming_geometry_max": "geometry",
        "incoming_support_max": "max",
        "incoming_support_sum": "sum",
        "incoming_support_mean": "mean",
    }
    for column, label in density_columns.items():
        for count_column, radius_label in (
            ("incoming_count_1sigma", "1sigma"),
            ("incoming_count_2sigma", "2sigma"),
        ):
            correlations: list[float] = []
            for _, rows in correct_state.groupby("frame_uid"):
                valid = rows[[column, count_column]].dropna()
                if len(valid) <= 2 or valid[count_column].nunique() <= 1:
                    continue
                correlations.append(
                    float(valid[column].corr(valid[count_column], method="spearman"))
                )
            density_correlations.append(
                {
                    "component": label,
                    "count_radius": radius_label,
                    "frame_count": int(len(correlations)),
                    "median_frame_spearman": float(np.median(correlations)),
                }
            )

    uncertainty_summary = {
        "row_count": int(len(uncertainty)),
        "nearest8_fallback_count": int(
            (uncertainty["local_anchor_mode"] == "NEAREST8_FALLBACK").sum()
        ),
        "nearest8_fallback_fraction": float(
            (uncertainty["local_anchor_mode"] == "NEAREST8_FALLBACK").mean()
        ),
        "radial_unbracketed_fraction": float(
            (~uncertainty["radial_bracket"].astype(bool)).mean()
        ),
        "theta_unbracketed_fraction": float(
            (~uncertainty["theta_bracket"].astype(bool)).mean()
        ),
        "either_dimension_unbracketed_fraction": float(
            (~(
                uncertainty["radial_bracket"].astype(bool)
                & uncertainty["theta_bracket"].astype(bool)
            )).mean()
        ),
        "both_dimensions_unbracketed_fraction": float(
            (
                ~uncertainty["radial_bracket"].astype(bool)
                & ~uncertainty["theta_bracket"].astype(bool)
            ).mean()
        ),
        "median_sigma_region_m": float(uncertainty["sigma_region_m"].median()),
        "p90_sigma_region_m": float(uncertainty["sigma_region_m"].quantile(0.90)),
        "max_sigma_region_m": float(uncertainty["sigma_region_m"].max()),
    }

    perturbed_outgoing = outgoing[outgoing["condition"] == PERTURBED]
    correct_pool = pairs[pairs["condition"] == CORRECT].set_index("pair_index")[
        "source_candidate_count"
    ]
    shuffled_pool = pairs[pairs["condition"] == SHUFFLED].set_index("pair_index")[
        "source_candidate_count"
    ]
    shuffled_pool_delta = shuffled_pool - correct_pool

    correct_references = references[
        (references["condition"] == CORRECT)
        & references["incoming_max_best_node_id_r80cm"].notna()
    ]
    unique_outcomes = correct_references[
        ["frame_uid", "incoming_max_best_node_id_r80cm"]
    ].drop_duplicates()
    multiplicity = (
        correct_references.groupby(
            ["frame_uid", "incoming_max_best_node_id_r80cm"]
        )
        .size()
        .value_counts()
        .sort_index()
    )

    unique_control_outcomes: list[dict[str, Any]] = []
    reference_keys = ["frame_uid", "target_id"]
    correct_eval = references[references["condition"] == CORRECT].set_index(
        reference_keys
    )
    for control in (ZERO, REVERSE, PERTURBED, SHUFFLED):
        other_eval = references[references["condition"] == control].set_index(
            reference_keys
        )
        joined = correct_eval[
            ["incoming_max_best_rank_r80cm", "incoming_max_best_node_id_r80cm"]
        ].join(
            other_eval[
                ["incoming_max_best_rank_r80cm", "incoming_max_best_node_id_r80cm"]
            ],
            lsuffix="_correct",
            rsuffix="_control",
        ).reset_index()
        joined = joined.dropna(
            subset=[
                "incoming_max_best_rank_r80cm_correct",
                "incoming_max_best_rank_r80cm_control",
            ]
        )
        raw_delta = (
            joined["incoming_max_best_rank_r80cm_control"]
            - joined["incoming_max_best_rank_r80cm_correct"]
        )
        unique = joined.drop_duplicates(
            [
                "frame_uid",
                "incoming_max_best_node_id_r80cm_correct",
                "incoming_max_best_node_id_r80cm_control",
            ]
        ).copy()
        unique_delta = (
            unique["incoming_max_best_rank_r80cm_control"]
            - unique["incoming_max_best_rank_r80cm_correct"]
        )
        unique_control_outcomes.append(
            {
                "control": control,
                "raw_reference_rows": int(len(joined)),
                "raw_median_control_minus_correct_rank": float(raw_delta.median()),
                "unique_paired_outcome_count": int(len(unique)),
                "unique_median_control_minus_correct_rank": float(
                    unique_delta.median()
                ),
                "unique_correct_better_fraction": float((unique_delta > 0).mean()),
                "unique_tie_fraction": float((unique_delta == 0).mean()),
                "unique_correct_worse_fraction": float((unique_delta < 0).mean()),
            }
        )

    manual = references[references["condition"] == CORRECT].drop_duplicates(
        ["frame_uid", "target_id"]
    )
    px_per_frame = nodes.groupby("frame_uid")["px_per_m"].first()
    distance_rows: list[dict[str, Any]] = []
    for frame_uid, rows in manual.groupby("frame_uid"):
        for pair_name, first_id, second_id in (
            ("P01_P02", TARGETS[0], TARGETS[1]),
            ("P03_P04", TARGETS[2], TARGETS[3]),
        ):
            first = rows[rows["target_id"] == first_id]
            second = rows[rows["target_id"] == second_id]
            if first.empty or second.empty:
                continue
            distance_m = float(
                np.hypot(
                    first["point_x_px"].iloc[0] - second["point_x_px"].iloc[0],
                    first["point_y_px"].iloc[0] - second["point_y_px"].iloc[0],
                )
                / px_per_frame.loc[frame_uid]
            )
            distance_rows.append(
                {"frame_uid": frame_uid, "pair": pair_name, "distance_m": distance_m}
            )
    distance_table = pd.DataFrame(distance_rows)
    reference_pair_distances = [
        {
            "pair": pair_name,
            "frame_count": int(len(rows)),
            "min_distance_m": float(rows["distance_m"].min()),
            "median_distance_m": float(rows["distance_m"].median()),
            "max_distance_m": float(rows["distance_m"].max()),
        }
        for pair_name, rows in distance_table.groupby("pair")
    ]

    component_case_rows: list[dict[str, Any]] = []
    selected_cases = {
        (483, TARGETS[1]),
        (487, TARGETS[1]),
        (490, TARGETS[0]),
        (490, TARGETS[2]),
        (490, TARGETS[3]),
        (494, TARGETS[2]),
        (494, TARGETS[3]),
    }
    correct_reference_all = references[references["condition"] == CORRECT]
    zero_reference_all = references[references["condition"] == ZERO].set_index(
        reference_keys
    )
    for row in correct_reference_all.to_dict("records"):
        key = (int(row["frame_index"]), row["target_id"])
        if key not in selected_cases:
            continue
        zero_row = zero_reference_all.loc[(row["frame_uid"], row["target_id"])]
        component_case_rows.append(
            {
                "frame_index": int(row["frame_index"]),
                "target": target_short(row["target_id"]),
                "image_rank": json_safe(row["image_best_rank_r80cm"]),
                "correct_max_rank": json_safe(row["incoming_max_best_rank_r80cm"]),
                "correct_sum_rank": json_safe(row["incoming_sum_best_rank_r80cm"]),
                "correct_mean_rank": json_safe(row["incoming_mean_best_rank_r80cm"]),
                "correct_thread_length": json_safe(row["max_thread_node_count_r80cm"]),
                "zero_max_rank": json_safe(zero_row["incoming_max_best_rank_r80cm"]),
            }
        )

    missing_case_rows = []
    for frame_index in (482, 490):
        row = correct_reference_all[
            (correct_reference_all["frame_index"] == frame_index)
            & (correct_reference_all["target_id"] == TARGETS[1])
        ].iloc[0]
        missing_case_rows.append(
            {
                "frame_index": frame_index,
                "target": "P02",
                "candidate_count_within_0_8m": int(
                    row["candidate_count_within_radius_r80cm"]
                ),
                "nearest_candidate_distance_m": float(
                    row["nearest_distance_m_r80cm"]
                ),
            }
        )

    comparability = pd.read_csv(B0R_COMPARABILITY_CSV)
    comparability_r02_lag1 = comparability[
        (comparability["run_id"] == "R02ZF") & (comparability["lag"] == 1)
    ]
    schema_columns = set(state.columns)
    return {
        "runtime_dependency_boundary": {
            "reference_values_used_by_node_edge_thread_computation": False,
            "reference_csv_bytes_hashed_before_graph": True,
            "explorer_with_annotation_fields_loaded_before_graph": True,
            "annotation_fields_accessed_by_runtime_graph_functions": False,
            "strict_sealed_data_isolation_claimed": False,
            "accurate_claim": "reference content did not participate in graph computation",
        },
        "correct_vs_zero_all_node_rank_similarity": rank_similarity,
        "mutual_edge_overlap": edge_overlap,
        "thread_length_similarity": thread_similarity,
        "shared_state_correct_vs_zero": {
            "comparison_count": int(len(shared_joined)),
            "exact_state_match_count": int(
                (
                    shared_joined["reachable_state_correct"]
                    == shared_joined["reachable_state_zero"]
                ).sum()
            ),
            "exact_state_match_fraction": float(
                (
                    shared_joined["reachable_state_correct"]
                    == shared_joined["reachable_state_zero"]
                ).mean()
            ),
        },
        "density_correlations": density_correlations,
        "uncertainty_support": uncertainty_summary,
        "control_fairness": {
            "tangential_perturbation_outside_target_mask_fraction": float(
                (~perturbed_outgoing[
                    "prediction_inside_target_Omega_single"
                ].astype(bool)).mean()
            ),
            "shuffled_source_pool_delta_min": int(shuffled_pool_delta.min()),
            "shuffled_source_pool_delta_median": float(shuffled_pool_delta.median()),
            "shuffled_source_pool_delta_max": int(shuffled_pool_delta.max()),
            "interpretation": (
                "Tangential and shuffled controls are gross sanity checks, not calibrated nulls."
            ),
        },
        "reference_outcome_multiplicity": {
            "evaluable_reference_rows": int(len(correct_references)),
            "unique_frame_best_node_outcomes": int(len(unique_outcomes)),
            "outcome_multiplicity_counts": {
                str(int(key)): int(value) for key, value in multiplicity.items()
            },
            "unique_control_outcomes": unique_control_outcomes,
        },
        "reference_pair_distances": reference_pair_distances,
        "shared_radius_m": 0.8,
        "component_case_rows": component_case_rows,
        "missing_case_rows": missing_case_rows,
        "reproducibility_gaps": {
            "dynamic_script_in_runtime_manifest_hashes": str(DYNAMIC_SCRIPT)
            in set(json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))["frozen_hashes"]),
            "protocol_in_runtime_manifest_hashes": str(PROTOCOL_PATH)
            in set(json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))["frozen_hashes"]),
            "fixed_offset_source_pre_run_hash_pinned": False,
            "B0R_comparability_pre_run_hash_pinned": False,
            "dynamic_script_current_sha256": sha256_file(DYNAMIC_SCRIPT),
            "protocol_current_sha256": sha256_file(PROTOCOL_PATH),
            "fixed_offset_source_current_sha256": sha256_file(
                SOURCE_FIXED_OFFSETS_CSV
            ),
            "B0R_comparability_current_sha256": sha256_file(
                B0R_COMPARABILITY_CSV
            ),
            "R02_lag1_comparability_rows": int(len(comparability_r02_lag1)),
            "R02_lag1_comparable_true_count": int(
                comparability_r02_lag1["comparable"].astype(bool).sum()
            ),
            "pair_comparable_asserted_or_filtered_by_dynamic_graph": False,
            "schema_has_best_support_normalized_error_x": "best_support_normalized_error_x"
            in schema_columns,
            "schema_has_best_support_normalized_error_y": "best_support_normalized_error_y"
            in schema_columns,
            "schema_has_unsuffixed_best_support_normalized_error": "best_support_normalized_error"
            in schema_columns,
        },
    }


def build_interpretation(
    manifest: dict[str, Any],
    run_summary: dict[str, Any],
    tables: dict[str, pd.DataFrame],
    paired: pd.DataFrame,
    offset_comparison: pd.DataFrame,
    display_rows: pd.DataFrame,
    transport_per_pair: pd.DataFrame,
    transport_summary: dict[str, Any],
    input_hash_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    references = tables["references"]
    controls: list[dict[str, Any]] = []
    for metric in (
        "incoming_max_best_rank_r80cm",
        "incoming_sum_best_rank_r80cm",
        "incoming_mean_best_rank_r80cm",
    ):
        for control in (ZERO, REVERSE, PERTURBED, SHUFFLED):
            controls.append(paired_rank_summary(references, control, metric))

    correct_state = tables["state"][tables["state"]["condition"] == CORRECT]
    density_corr = correct_state[
        [
            "incoming_support_sum",
            "incoming_support_max",
            "incoming_support_mean",
            "incoming_count_2sigma",
        ]
    ].corr(method="spearman")
    thread_summaries = run_summary["thread_summaries"]
    fixed_summary = build_fixed_offset_summary(offset_comparison)

    method_audit = build_method_audit(tables)
    return {
        "schema": "PERSON_P1E_DYNAMIC_EVIDENCE_INTERPRETATION_V1",
        "status": "TEMPORAL_STRUCTURE_PRESENT_P0_SPECIFIC_GAIN_NOT_ESTABLISHED",
        "research_gate_used": False,
        "run_role": "EXPOSED_DEVELOPMENT_CORPUS_NOT_BLIND_VALIDATION",
        "runtime_counts": {
            "frames": int(manifest["frame_count"]),
            "lag1_pairs": int(manifest["pair_count"]),
            "static_nodes": int(manifest["static_node_count"]),
            "edges_within_3sigma": int(manifest["edge_count_within_3sigma"]),
            "mutual_nearest_edges": int(manifest["mutual_edge_count"]),
            "manual_reference_evaluation_rows": int(len(references)),
        },
        "target_summaries": build_target_summaries(paired),
        "correct_vs_controls": controls,
        "transport_scale": transport_summary,
        "thread_summaries": thread_summaries,
        "fixed_offset_summaries": fixed_summary,
        "display_stratum_rows": display_rows.to_dict("records"),
        "shared_transition_counts": run_summary["shared_transition_counts"],
        "density_diagnostics": {
            "spearman_sum_vs_incoming_count_2sigma": float(
                density_corr.loc["incoming_support_sum", "incoming_count_2sigma"]
            ),
            "spearman_max_vs_incoming_count_2sigma": float(
                density_corr.loc["incoming_support_max", "incoming_count_2sigma"]
            ),
            "spearman_sum_vs_max": float(
                density_corr.loc["incoming_support_sum", "incoming_support_max"]
            ),
        },
        "method_audit": method_audit,
        "direct_findings": {
            "low_rank_partial_recovery": (
                "P01 improves in 6/8 incoming-evaluable manual frames and P02 in 4/6, "
                "but P0-specific advantage over zero transport is inconsistent."
            ),
            "candidate_missing": (
                "P02 has no C2 node within 0.8 m at F482 and F490; lag1 evidence cannot create a missing node."
            ),
            "shared_state": (
                "P03/P04 remain SHARED in all eight manual intervals under both the full 2sigma graph "
                "and mutual-nearest 2sigma threads; no split is observed."
            ),
            "decisive_counterexamples": (
                "P01 F490 changes image rank 13 to temporal rank 255; P03/P04 F494 change "
                "image rank 1 to temporal rank 206 under correct P0."
            ),
            "p0_specific_information": (
                "Correct P0 beats reverse and gross perturbation/shuffle sanity checks, but "
                "P0-specific gain over zero transport is not established."
            ),
        },
        "semantic_boundaries": {
            "P0_is_real_platform_trajectory": False,
            "pseudocolor_is_intrinsic_person_RCS": False,
            "manual_reference_used_for_runtime_graph": False,
            "manual_reference_bytes_or_annotation_container_never_read_before_graph": False,
            "strict_sealed_data_isolation_claimed": False,
            "physical_target_id_used_for_runtime_graph": False,
            "optical_or_interpolated_track_used_for_runtime_graph": False,
            "candidate_topk_truncation_used": False,
            "P0_retuned": False,
            "P1_PASS_claimed": False,
            "blind_validation_claimed": False,
        },
        "hash_checks": {
            "contract_inputs": input_hash_checks,
            "P0_script_sha256": sha256_file(P0_SCRIPT),
            "P1E_C0_C3_script_sha256": sha256_file(P1E_SCRIPT),
            "candidate_audit_script_sha256": sha256_file(AUDIT_SCRIPT),
            "dynamic_experiment_script_sha256": sha256_file(DYNAMIC_SCRIPT),
            "runtime_manifest_sha256": sha256_file(MANIFEST_JSON),
            "run_summary_sha256": sha256_file(RUN_SUMMARY_JSON),
        },
        "transport_pair_rows": transport_per_pair.to_dict("records"),
    }


def plot_manual_rank_dynamics(paired: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), sharex=True)
    for axis, target_id in zip(axes.flat, TARGETS):
        rows = paired[paired["target_id"] == target_id].sort_values("frame_index")
        frames = rows["frame_index"].to_numpy()
        axis.plot(
            frames,
            rows["image_best_rank_r80cm"],
            color="#20242c",
            marker="o",
            linestyle="--",
            label="single-frame image rank",
        )
        axis.plot(
            frames,
            rows[f"{CORRECT}__incoming_max_best_rank_r80cm"],
            color="#1d8f59",
            marker="s",
            label="correct P0 temporal rank",
        )
        axis.plot(
            frames,
            rows[f"{ZERO}__incoming_max_best_rank_r80cm"],
            color="#2f6fca",
            marker="^",
            alpha=0.85,
            label="zero-transport temporal rank",
        )
        missing = rows[rows["image_best_rank_r80cm"].isna()]
        if not missing.empty:
            axis.scatter(
                missing["frame_index"],
                np.full(len(missing), 320.0),
                marker="x",
                s=80,
                color="#b22d2d",
                label="no node within 0.8 m",
            )
        axis.set_yscale("log")
        axis.set_ylim(330, 0.8)
        axis.grid(True, which="both", alpha=0.22)
        axis.set_title(target_short(target_id), weight="bold")
        axis.set_ylabel("rank (1 is best)")
    axes[-1, 0].set_xlabel("SAR frame index")
    axes[-1, 1].set_xlabel("SAR frame index")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
    fig.suptitle(
        "R02 manual-reference neighborhood: image rank and incoming temporal rank",
        fontsize=15,
        weight="bold",
    )
    fig.text(
        0.5,
        0.03,
        "References are used only after the GT-blind graph is complete. Large downward jumps are temporal failures, not deleted cases.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=[0.02, 0.07, 1, 0.94])
    fig.savefig(output_path, dpi=170, facecolor="white")
    plt.close(fig)


def plot_control_information_gain(
    references: pd.DataFrame, output_path: Path
) -> None:
    metrics = (
        ("incoming_max_best_rank_r80cm", "incoming support max"),
        ("incoming_sum_best_rank_r80cm", "incoming support sum"),
        ("incoming_mean_best_rank_r80cm", "incoming support mean"),
    )
    colors = {
        ZERO: "#2f6fca",
        REVERSE: "#9b59b6",
        PERTURBED: "#e67e22",
        SHUFFLED: "#59636f",
    }
    keys = ["frame_uid", "target_id"]
    correct = references[references["condition"] == CORRECT].set_index(keys)
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.5), sharey=True)
    rng = np.random.default_rng(20260826)
    for axis, (metric, title) in zip(axes, metrics):
        for x_index, control in enumerate((ZERO, REVERSE, PERTURBED, SHUFFLED)):
            other = references[references["condition"] == control].set_index(keys)
            joined = correct[[metric]].join(
                other[[metric]], lsuffix="_correct", rsuffix="_control"
            ).dropna()
            delta = (
                joined[f"{metric}_control"] - joined[f"{metric}_correct"]
            ).to_numpy()
            jitter = rng.uniform(-0.10, 0.10, size=len(delta))
            axis.scatter(
                np.full(len(delta), x_index) + jitter,
                delta,
                s=24,
                alpha=0.55,
                color=colors[control],
            )
            axis.scatter(
                [x_index],
                [np.median(delta)],
                marker="D",
                s=80,
                color="#111111",
                edgecolor="white",
                linewidth=0.8,
                zorder=10,
            )
        axis.axhline(0, color="#333333", linewidth=1)
        axis.set_xticks(range(4))
        axis.set_xticklabels(["zero", "reverse", "+0.75m", "shuffle"], rotation=22)
        axis.set_title(title)
        axis.set_yscale("symlog", linthresh=5)
        axis.grid(True, axis="y", alpha=0.2)
    axes[0].set_ylabel("control rank - correct-P0 rank\npositive means correct P0 is better")
    fig.suptitle(
        "P0-specific information gain depends on which temporal evidence component is read",
        fontsize=14,
        weight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(output_path, dpi=170, facecolor="white")
    plt.close(fig)


def plot_transport_scale(per_pair: pd.DataFrame, output_path: Path) -> None:
    x = per_pair["pair_index"].to_numpy()
    fig, axis = plt.subplots(figsize=(13, 5.4))
    axis.plot(
        x,
        per_pair["transport_displacement_m"],
        marker="o",
        color="#1f77b4",
        label="frozen P0 lag1 displacement",
    )
    axis.plot(
        x,
        per_pair["sigma_region_m"],
        marker="s",
        color="#d35400",
        label="local temporal region sigma",
    )
    axis.fill_between(
        x,
        0,
        per_pair["transport_displacement_m"],
        color="#1f77b4",
        alpha=0.08,
    )
    axis.set_xlabel("lag1 pair index (F472→473 is 0)")
    axis.set_ylabel("meters")
    axis.grid(True, alpha=0.25)
    axis.legend(frameon=False)
    axis.set_title(
        "The expected lag1 transport is much smaller than the allowed local region",
        fontsize=14,
        weight="bold",
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=170, facecolor="white")
    plt.close(fig)


def plot_thread_persistence(
    threads: pd.DataFrame,
    references: pd.DataFrame,
    offsets: pd.DataFrame,
    output_path: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    palette = {
        CORRECT: "#1d8f59",
        ZERO: "#2f6fca",
        REVERSE: "#9b59b6",
        PERTURBED: "#e67e22",
    }
    max_length = int(threads["node_count"].max())
    x = np.arange(1, max_length + 1)
    for condition in GRAPH_CONDITIONS:
        values = threads[threads["condition"] == condition]["node_count"].to_numpy()
        survival = np.array([(values >= length).mean() for length in x])
        axes[0].plot(x, survival, label=condition, color=palette[condition])
    axes[0].set_yscale("log")
    axes[0].set_xlabel("thread node count")
    axes[0].set_ylabel("fraction of threads with at least this length")
    axes[0].grid(True, which="both", alpha=0.22)
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].set_title("All GT-blind mutual-nearest threads")

    box_data: list[np.ndarray] = []
    box_labels: list[str] = []
    for condition in (CORRECT, ZERO):
        ref_values = references[
            references["condition"] == condition
        ]["max_thread_node_count_r80cm"].dropna().to_numpy()
        off_values = offsets[
            offsets["condition"] == condition
        ]["max_thread_node_count_r80cm"].dropna().to_numpy()
        box_data.extend([ref_values, off_values])
        box_labels.extend([f"{condition}\nreference", f"{condition}\noffset"])
    axes[1].boxplot(box_data, tick_labels=box_labels, showfliers=False)
    axes[1].set_ylabel("max thread node count within 0.8 m")
    axes[1].grid(True, axis="y", alpha=0.22)
    axes[1].set_title("Offline reference neighborhoods vs fixed spatial controls")
    fig.suptitle(
        "Long temporal structure exists, but correct P0 and zero transport are nearly indistinguishable",
        fontsize=14,
        weight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(output_path, dpi=170, facecolor="white")
    plt.close(fig)


def plot_spacetime_projection(
    members: pd.DataFrame,
    nodes: pd.DataFrame,
    references: pd.DataFrame,
    output_path: Path,
) -> None:
    enriched = members.merge(
        nodes[["node_id", "px_per_m"]], on="node_id", how="left"
    )
    manual = references[references["condition"] == CORRECT].drop_duplicates(
        ["frame_uid", "target_id"]
    )
    groups = (
        ("P01/P02", TARGETS[:2], "x_px", "x pixel"),
        ("P03/P04", TARGETS[2:], "y_px", "y pixel"),
    )
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), sharex=True)
    for column, condition in enumerate((CORRECT, ZERO)):
        condition_members = enriched[enriched["condition"] == condition]
        for row_index, (group_name, target_ids, coordinate, ylabel) in enumerate(groups):
            axis = axes[row_index, column]
            group_manual = manual[manual["target_id"].isin(target_ids)]
            qualified: list[tuple[str, float, int]] = []
            for thread_id, thread_rows in condition_members.groupby("thread_id"):
                near = False
                for member in thread_rows.to_dict("records"):
                    frame_refs = group_manual[
                        group_manual["frame_uid"] == member["frame_uid"]
                    ]
                    if frame_refs.empty:
                        continue
                    dx = frame_refs["point_x_px"].to_numpy() - float(member["x_px"])
                    dy = frame_refs["point_y_px"].to_numpy() - float(member["y_px"])
                    distance_m = np.hypot(dx, dy) / float(member["px_per_m"])
                    if np.any(distance_m <= 1.0):
                        near = True
                        break
                if near and len(thread_rows) >= 3:
                    qualified.append(
                        (
                            thread_id,
                            float(thread_rows["candidate_pool_percentile"].mean()),
                            int(len(thread_rows)),
                        )
                    )
            qualified = sorted(
                qualified, key=lambda item: (item[2], item[1]), reverse=True
            )[:80]
            for thread_id, mean_percentile, length in qualified:
                rows = condition_members[
                    condition_members["thread_id"] == thread_id
                ].sort_values("frame_index")
                color = plt.cm.viridis(np.clip(mean_percentile, 0.0, 1.0))
                axis.plot(
                    rows["frame_index"],
                    rows[coordinate],
                    color=color,
                    alpha=0.28 if length < 10 else 0.65,
                    linewidth=0.8 if length < 10 else 1.6,
                )
            for target_id in target_ids:
                rows = group_manual[group_manual["target_id"] == target_id]
                value_column = "point_x_px" if coordinate == "x_px" else "point_y_px"
                axis.scatter(
                    rows["frame_index"],
                    rows[value_column],
                    s=48,
                    marker="x",
                    linewidths=2,
                    color=TARGET_COLORS[target_id],
                    label=target_short(target_id),
                    zorder=10,
                )
            axis.grid(True, alpha=0.2)
            axis.set_ylabel(ylabel)
            axis.set_title(
                f"{condition} | {group_name} | {len(qualified)} post-hoc selected threads"
            )
            axis.legend(frameon=False, fontsize=8)
    axes[-1, 0].set_xlabel("frame index")
    axes[-1, 1].set_xlabel("frame index")
    fig.suptitle(
        "x-y-t response-tube projections: persistent structure is visible, shared structure does not split",
        fontsize=14,
        weight="bold",
    )
    fig.text(
        0.5,
        0.02,
        "Threads were built GT-blind. References are used only to select which already-built threads are shown and to mark offline locations.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=[0, 0.045, 1, 0.94])
    fig.savefig(output_path, dpi=170, facecolor="white")
    plt.close(fig)


def manual_annotations(frame: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in frame["annotations"]
        if row.get("source") == "MANUAL_NATIVE_SAR"
    ]


def draw_manual_references(
    axis: plt.Axes,
    annotations: list[dict[str, Any]],
    selected_targets: tuple[str, ...],
    x0: int,
    y0: int,
) -> None:
    for annotation in annotations:
        target_id = annotation["instance_id"]
        selected = target_id in selected_targets
        color = TARGET_COLORS.get(target_id, "#d0d0d0")
        alpha = 1.0 if selected else 0.45
        axis.scatter(
            [float(annotation["cx"]) - x0],
            [float(annotation["cy"]) - y0],
            marker="x",
            s=90 if selected else 45,
            linewidths=2.2 if selected else 1.2,
            color=color,
            alpha=alpha,
            zorder=20,
        )
        if selected:
            axis.text(
                float(annotation["cx"]) - x0 + 3,
                float(annotation["cy"]) - y0 - 4,
                target_short(target_id),
                color=color,
                fontsize=8,
                weight="bold",
                zorder=21,
            )


def load_frame_assets(
    audit: Any,
    p0: Any,
    p1e: Any,
    frame: dict[str, Any],
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    frame_uid = frame["sar_frame_uid"]
    if frame_uid in cache:
        return cache[frame_uid]
    image_path = p0.file_url_to_path(frame["sar_image_url"])
    image_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise FileNotFoundError(image_path)
    mask, radial, theta, px_per_m = audit.single_frame_observation_mask(
        frame, image_bgr
    )
    maps, _ = audit.compute_existing_candidate_maps_for_mask(
        p1e, frame, image_bgr, mask, radial, theta, px_per_m
    )
    support_radius_px = max(
        1, int(round(p1e.PHYSICAL_SUPPORT_RADIUS_M * px_per_m))
    )
    evaluation_maps = p1e.build_evaluation_maps(
        maps, mask, support_radius_px, "fixed_support_mean_v2"
    )
    output = {
        "image_rgb": cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB),
        "mask": mask,
        "C2": evaluation_maps["C2_COMPACT_JET_GRADIENT_CONSENSUS"],
        "px_per_m": float(px_per_m),
    }
    cache[frame_uid] = output
    return output


def crop_for_targets(
    frame: dict[str, Any], target_ids: tuple[str, ...], shape: tuple[int, int]
) -> tuple[int, int, int, int, np.ndarray]:
    selected = [
        row
        for row in manual_annotations(frame)
        if row["instance_id"] in target_ids
    ]
    if not selected:
        raise RuntimeError(
            f"destination frame {frame['sar_frame_uid']} lacks selected manual references"
        )
    center = np.mean(
        [[float(row["cx"]), float(row["cy"])] for row in selected], axis=0
    )
    px_per_m = float(frame["geometry"]["radius_px"]) / float(
        frame["geometry"]["outer_range_m"]
    )
    radius = int(round(2.25 * px_per_m))
    height, width = shape
    x0 = max(0, int(round(center[0])) - radius)
    x1 = min(width, int(round(center[0])) + radius + 1)
    y0 = max(0, int(round(center[1])) - radius)
    y1 = min(height, int(round(center[1])) + radius + 1)
    return x0, x1, y0, y1, center


def draw_local_candidates(
    axis: plt.Axes,
    node_rows: pd.DataFrame,
    x0: int,
    y0: int,
    selected_points: np.ndarray,
    px_per_m: float,
    temporal_rows: pd.DataFrame | None = None,
) -> None:
    temporal_map: dict[str, float] = {}
    if temporal_rows is not None:
        temporal_map = dict(
            zip(
                temporal_rows["destination_node_id"],
                temporal_rows["incoming_support_max_rank"],
            )
        )
    for row in node_rows.to_dict("records"):
        point = np.array([float(row["x_px"]), float(row["y_px"])])
        distance = (
            np.min(np.linalg.norm(selected_points - point[None, :], axis=1))
            / px_per_m
        )
        rank = int(row["candidate_rank"])
        if rank > 5 and distance > 1.15:
            continue
        color = "#ffe600" if rank <= 5 else "#f7f7f7"
        axis.scatter(
            [point[0] - x0],
            [point[1] - y0],
            s=70 if rank <= 5 else 54,
            facecolors="none",
            edgecolors=color,
            linewidths=1.6,
            zorder=12,
        )
        if distance <= 0.85:
            temporal_rank = temporal_map.get(row["node_id"], np.nan)
            label = f"i{rank}"
            if np.isfinite(temporal_rank):
                label += f"/t{int(temporal_rank)}"
            axis.text(
                point[0] - x0 + 3,
                point[1] - y0 - 3,
                label,
                color=color,
                fontsize=7,
                weight="bold",
                zorder=13,
            )


def plot_pair_case(
    audit: Any,
    p0: Any,
    p1e: Any,
    frame_map: dict[str, dict[str, Any]],
    tables: dict[str, pd.DataFrame],
    spec: dict[str, Any],
    output_path: Path,
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    pair_index = int(spec["pair_index"])
    pair = tables["pairs"][
        (tables["pairs"]["condition"] == CORRECT)
        & (tables["pairs"]["pair_index"] == pair_index)
    ].iloc[0]
    source_frame = frame_map[pair["actual_from_frame_uid"]]
    destination_frame = frame_map[pair["to_frame_uid"]]
    source_assets = load_frame_assets(audit, p0, p1e, source_frame, cache)
    destination_assets = load_frame_assets(audit, p0, p1e, destination_frame, cache)
    x0, x1, y0, y1, _ = crop_for_targets(
        destination_frame,
        tuple(spec["target_ids"]),
        destination_assets["image_rgb"].shape[:2],
    )
    selected_annotations = [
        row
        for row in manual_annotations(destination_frame)
        if row["instance_id"] in spec["target_ids"]
    ]
    selected_points = np.array(
        [[float(row["cx"]), float(row["cy"])] for row in selected_annotations]
    )
    px_per_m = destination_assets["px_per_m"]

    source_nodes = tables["nodes"][
        tables["nodes"]["frame_uid"] == source_frame["sar_frame_uid"]
    ]
    destination_nodes = tables["nodes"][
        tables["nodes"]["frame_uid"] == destination_frame["sar_frame_uid"]
    ]
    source_local = source_nodes[
        source_nodes["x_px"].between(x0, x1)
        & source_nodes["y_px"].between(y0, y1)
    ]
    destination_local = destination_nodes[
        destination_nodes["x_px"].between(x0, x1)
        & destination_nodes["y_px"].between(y0, y1)
    ]

    fig, axes = plt.subplots(2, 4, figsize=(19, 9.5))
    plt.subplots_adjust(
        left=0.02, right=0.99, bottom=0.075, top=0.88, wspace=0.04, hspace=0.14
    )

    raw_panels = (
        (axes[0, 0], source_assets["image_rgb"], source_frame, "source raw SAR"),
        (axes[0, 1], source_assets["C2"], source_frame, "source C2 response"),
        (
            axes[0, 2],
            destination_assets["image_rgb"],
            destination_frame,
            "destination raw SAR",
        ),
        (
            axes[0, 3],
            destination_assets["C2"],
            destination_frame,
            "destination C2 response",
        ),
    )
    for axis, image_data, frame, title in raw_panels:
        if image_data.ndim == 2:
            local = image_data[y0:y1, x0:x1].copy()
            mask = (
                source_assets["mask"]
                if frame["sar_frame_uid"] == source_frame["sar_frame_uid"]
                else destination_assets["mask"]
            )[y0:y1, x0:x1]
            local[~mask] = np.nan
            axis.imshow(local, cmap="magma", vmin=0.0, vmax=1.0)
        else:
            axis.imshow(image_data[y0:y1, x0:x1])
        draw_manual_references(
            axis, manual_annotations(frame), tuple(spec["target_ids"]), x0, y0
        )
        node_rows = (
            source_local
            if frame["sar_frame_uid"] == source_frame["sar_frame_uid"]
            else destination_local
        )
        draw_local_candidates(
            axis, node_rows, x0, y0, selected_points, px_per_m, None
        )
        axis.set_xlim(0, x1 - x0)
        axis.set_ylim(y1 - y0, 0)
        axis.set_title(title)
        axis.axis("off")

    source_lookup = source_nodes.set_index("node_id")
    destination_lookup = destination_nodes.set_index("node_id")
    for axis, condition in zip(axes[1], GRAPH_CONDITIONS):
        local_map = destination_assets["C2"][y0:y1, x0:x1].copy()
        local_mask = destination_assets["mask"][y0:y1, x0:x1]
        local_map[~local_mask] = np.nan
        axis.imshow(local_map, cmap="magma", vmin=0.0, vmax=1.0)
        draw_manual_references(
            axis,
            manual_annotations(destination_frame),
            tuple(spec["target_ids"]),
            x0,
            y0,
        )
        condition_out = tables["outgoing"][
            (tables["outgoing"]["condition"] == condition)
            & (tables["outgoing"]["pair_index"] == pair_index)
        ].copy()
        condition_out["distance_to_selected_m"] = condition_out.apply(
            lambda row: float(
                np.min(
                    np.linalg.norm(
                        selected_points
                        - np.array(
                            [row["predicted_x_px"], row["predicted_y_px"]]
                        )[None, :],
                        axis=1,
                    )
                )
                / px_per_m
            ),
            axis=1,
        )
        shown_sources = condition_out[
            (condition_out["distance_to_selected_m"] <= 1.35)
            | (condition_out["source_candidate_rank"] <= 5)
        ].sort_values(["distance_to_selected_m", "source_candidate_rank"]).head(12)

        condition_in = tables["incoming"][
            (tables["incoming"]["condition"] == condition)
            & (tables["incoming"]["pair_index"] == pair_index)
        ]
        draw_local_candidates(
            axis,
            destination_local,
            x0,
            y0,
            selected_points,
            px_per_m,
            condition_in,
        )
        shown_ids = set(shown_sources["source_node_id"])
        mutual = tables["mutual_edges"][
            (tables["mutual_edges"]["condition"] == condition)
            & (tables["mutual_edges"]["pair_index"] == pair_index)
            & (tables["mutual_edges"]["source_node_id"].isin(shown_ids))
        ]
        predicted_lookup = condition_out.drop_duplicates("source_node_id").set_index(
            "source_node_id"
        )
        for edge in mutual.to_dict("records"):
            if (
                edge["destination_node_id"] not in destination_lookup.index
                or edge["source_node_id"] not in predicted_lookup.index
            ):
                continue
            destination = destination_lookup.loc[edge["destination_node_id"]]
            predicted = predicted_lookup.loc[edge["source_node_id"]]
            axis.plot(
                [float(predicted["predicted_x_px"]) - x0, float(destination["x_px"]) - x0],
                [float(predicted["predicted_y_px"]) - y0, float(destination["y_px"]) - y0],
                color="#bff6ff",
                linewidth=1.0,
                alpha=0.75,
                zorder=8,
            )
        for source in shown_sources.to_dict("records"):
            if source["source_node_id"] not in source_lookup.index:
                continue
            origin = source_lookup.loc[source["source_node_id"]]
            predicted_x = float(source["predicted_x_px"])
            predicted_y = float(source["predicted_y_px"])
            if not (x0 <= predicted_x <= x1 and y0 <= predicted_y <= y1):
                continue
            axis.annotate(
                "",
                xy=(predicted_x - x0, predicted_y - y0),
                xytext=(float(origin["x_px"]) - x0, float(origin["y_px"]) - y0),
                arrowprops=dict(arrowstyle="->", color="#52e0ff", lw=1.0, alpha=0.7),
                zorder=9,
            )
            axis.scatter(
                [predicted_x - x0],
                [predicted_y - y0],
                marker="^",
                s=52,
                facecolors="none",
                edgecolors="#52e0ff",
                linewidths=1.2,
                zorder=10,
            )
            axis.add_patch(
                Circle(
                    (predicted_x - x0, predicted_y - y0),
                    float(source["sigma_region_px"]),
                    fill=False,
                    edgecolor="#52e0ff",
                    linewidth=0.6,
                    alpha=0.25,
                    zorder=7,
                )
            )
        summary_row = tables["pairs"][
            (tables["pairs"]["condition"] == condition)
            & (tables["pairs"]["pair_index"] == pair_index)
        ].iloc[0]
        axis.set_xlim(0, x1 - x0)
        axis.set_ylim(y1 - y0, 0)
        axis.set_title(
            f"{condition}\nmedian nearest E={summary_row['median_nearest_normalized_error_source_to_destination']:.2f} sigma",
            fontsize=9,
        )
        axis.axis("off")

    from_index = int(pair["from_frame"])
    to_index = int(pair["to_frame"])
    fig.suptitle(
        f"R02 F{from_index}→F{to_index} {'/'.join(target_short(t) for t in spec['target_ids'])} | {spec['note']}",
        fontsize=13,
        weight="bold",
    )
    fig.text(
        0.5,
        0.025,
        "C2 nodes and temporal relations were generated without GT. X markers and the local case crop are offline evaluation overlays. i=single-frame image rank; t=incoming-support-max rank.",
        ha="center",
        fontsize=8.7,
    )
    fig.savefig(output_path, dpi=165, facecolor="white")
    plt.close(fig)

    destination_eval = tables["references"][
        (tables["references"]["condition"] == CORRECT)
        & (tables["references"]["frame_uid"] == destination_frame["sar_frame_uid"])
        & (tables["references"]["target_id"].isin(spec["target_ids"]))
    ]
    case_metrics = [
        {
            "target_id": row["target_id"],
            "image_rank_r80cm": json_safe(row["image_best_rank_r80cm"]),
            "correct_incoming_max_rank_r80cm": json_safe(
                row["incoming_max_best_rank_r80cm"]
            ),
            "candidate_count_r80cm": int(row["candidate_count_within_radius_r80cm"]),
        }
        for row in destination_eval.to_dict("records")
    ]
    return {
        "pair_index": pair_index,
        "from_frame": from_index,
        "to_frame": to_index,
        "target_ids": list(spec["target_ids"]),
        "note": spec["note"],
        "path": str(output_path),
        "destination_metrics": case_metrics,
    }


def html_table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{html.escape(str(value))}</th>" for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    output.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(output)


def find_summary(
    rows: list[dict[str, Any]], key: str, value: str
) -> dict[str, Any]:
    return next(row for row in rows if row[key] == value)


def write_reports(
    interpretation: dict[str, Any],
    case_registry: list[dict[str, Any]],
    figures: dict[str, Path],
) -> None:
    targets = interpretation["target_summaries"]
    controls = interpretation["correct_vs_controls"]
    threads = interpretation["thread_summaries"]
    fixed = interpretation["fixed_offset_summaries"]
    transport = interpretation["transport_scale"]
    audit = interpretation["method_audit"]

    all_node_rows = [
        [
            row["component"],
            row["frame_count"],
            number(row["median_frame_spearman_correct_vs_zero"], 4),
            pct(row["median_frame_exact_rank_tie_fraction"]),
            number(row["median_frame_absolute_rank_delta"], 1),
        ]
        for row in audit["correct_vs_zero_all_node_rank_similarity"]
    ]
    all_node_headers = [
        "component",
        "frames",
        "median frame Spearman",
        "median exact-rank ties",
        "median |rank delta|",
    ]
    edge_rows = [
        [
            CONTROL_LABELS.get(row["control"], row["control"]),
            row["correct_edge_count"],
            row["control_edge_count"],
            pct(row["intersection_over_correct"]),
            number(row["jaccard"], 4),
        ]
        for row in audit["mutual_edge_overlap"]
    ]
    edge_headers = [
        "control",
        "correct edges",
        "control edges",
        "correct-edge overlap",
        "Jaccard",
    ]
    component_case_rows = [
        [
            f"F{row['frame_index']}",
            row["target"],
            number(row["image_rank"], 0),
            number(row["correct_max_rank"], 0),
            number(row["correct_sum_rank"], 0),
            number(row["correct_mean_rank"], 0),
            number(row["correct_thread_length"], 0),
            number(row["zero_max_rank"], 0),
        ]
        for row in audit["component_case_rows"]
    ]
    component_case_headers = [
        "frame",
        "target",
        "image rank",
        "correct max",
        "correct sum",
        "correct mean",
        "thread len",
        "zero max",
    ]

    target_rows = [
        [
            row["target"],
            row["reference_count"],
            row["candidate_missing_count_0_8m"],
            row["incoming_evaluable_count"],
            number(row["median_image_rank"], 1),
            number(row["median_correct_incoming_max_rank"], 1),
            number(row["median_image_to_correct_rank_improvement"], 1),
            pct(row["correct_improved_vs_image_fraction"]),
            number(row["median_zero_minus_correct_rank"], 1),
            pct(row["correct_better_than_zero_fraction"]),
            row["severe_temporal_worsening_count_at_least_50_ranks"],
        ]
        for row in targets
    ]
    target_headers = [
        "target",
        "refs",
        "missing",
        "incoming n",
        "image median rank",
        "correct median rank",
        "image→correct median gain",
        "improved vs image",
        "zero-correct median",
        "correct better than zero",
        "worsened ≥50 ranks",
    ]

    control_rows = []
    metric_labels = {
        "incoming_max_best_rank_r80cm": "max",
        "incoming_sum_best_rank_r80cm": "sum",
        "incoming_mean_best_rank_r80cm": "mean",
    }
    for row in controls:
        control_rows.append(
            [
                metric_labels[row["metric"]],
                CONTROL_LABELS[row["control"]],
                row["paired_count"],
                number(row["median_control_rank_minus_correct_rank"], 1),
                pct(row["correct_better_fraction"]),
                pct(row["tie_fraction"]),
                pct(row["correct_worse_fraction"]),
            ]
        )
    control_headers = [
        "component",
        "control",
        "paired n",
        "median control-correct rank",
        "correct better",
        "tie",
        "correct worse",
    ]

    thread_rows = [
        [
            row["condition"],
            row["thread_count"],
            number(row["median_thread_node_count"], 1),
            number(row["p90_thread_node_count"], 1),
            row["max_thread_node_count"],
            pct(row["node_fraction_in_threads_length_at_least_10"]),
        ]
        for row in threads
    ]
    thread_headers = ["condition", "threads", "median len", "P90 len", "max", "nodes in len≥10"]

    fixed_rows = [
        [
            row["condition"],
            number(row["median_reference_minus_offset_image_percentile"], 3),
            pct(row["positive_image_margin_fraction"]),
            number(row["median_reference_minus_offset_temporal_percentile"], 3),
            pct(row["positive_temporal_margin_fraction"]),
            number(row["median_reference_minus_offset_thread_nodes"], 1),
            pct(row["reference_longer_thread_fraction"]),
        ]
        for row in fixed
    ]
    fixed_headers = [
        "condition",
        "image ref-offset percentile",
        "image positive",
        "temporal ref-offset percentile",
        "temporal positive",
        "thread ref-offset nodes",
        "reference longer",
    ]

    case_html: list[str] = []
    case_md: list[str] = []
    for case in case_registry:
        path = Path(case["path"])
        url = relative_url(path)
        targets_text = "/".join(target_short(value) for value in case["target_ids"])
        caption = f"F{case['from_frame']}→F{case['to_frame']} {targets_text}: {case['note']}"
        case_html.append(
            f"<figure><img src='{html.escape(url)}' alt='{html.escape(caption)}'><figcaption>{html.escape(caption)}</figcaption></figure>"
        )
        case_md.append(f"![{caption}]({url})\n\n{caption}")

    p01 = find_summary(targets, "target", "P01")
    p02 = find_summary(targets, "target", "P02")
    p03 = find_summary(targets, "target", "P03")
    correct_threads = find_summary(threads, "condition", CORRECT)
    zero_threads = find_summary(threads, "condition", ZERO)
    max_zero = next(
        row
        for row in controls
        if row["metric"] == "incoming_max_best_rank_r80cm"
        and row["control"] == ZERO
    )
    max_reverse = next(
        row
        for row in controls
        if row["metric"] == "incoming_max_best_rank_r80cm"
        and row["control"] == REVERSE
    )
    max_perturbed = next(
        row
        for row in controls
        if row["metric"] == "incoming_max_best_rank_r80cm"
        and row["control"] == PERTURBED
    )
    max_shuffled = next(
        row
        for row in controls
        if row["metric"] == "incoming_max_best_rank_r80cm"
        and row["control"] == SHUFFLED
    )
    mean_zero = next(
        row
        for row in controls
        if row["metric"] == "incoming_mean_best_rank_r80cm"
        and row["control"] == ZERO
    )
    all_node_max = next(
        row
        for row in audit["correct_vs_zero_all_node_rank_similarity"]
        if row["component"] == "max"
    )
    all_node_sum = next(
        row
        for row in audit["correct_vs_zero_all_node_rank_similarity"]
        if row["component"] == "sum"
    )
    all_node_mean = next(
        row
        for row in audit["correct_vs_zero_all_node_rank_similarity"]
        if row["component"] == "mean"
    )
    zero_edges = next(
        row for row in audit["mutual_edge_overlap"] if row["control"] == ZERO
    )
    zero_thread_similarity = next(
        row for row in audit["thread_length_similarity"] if row["control"] == ZERO
    )
    uncertainty_audit = audit["uncertainty_support"]
    outcome_audit = audit["reference_outcome_multiplicity"]
    shared_audit = audit["shared_state_correct_vs_zero"]
    control_fairness = audit["control_fairness"]
    reproducibility = audit["reproducibility_gaps"]
    p01_p02_distance = next(
        row for row in audit["reference_pair_distances"] if row["pair"] == "P01_P02"
    )
    p03_p04_distance = next(
        row for row in audit["reference_pair_distances"] if row["pair"] == "P03_P04"
    )

    css = """
    :root { --ink:#172033; --muted:#5d687a; --line:#d8dfeb; --blue:#315a9b; --green:#19714c; --red:#a53535; --paper:#fff; --wash:#f4f7fb; }
    * { box-sizing:border-box; } body { margin:0; color:var(--ink); background:var(--wash); font-family:"Segoe UI","Microsoft YaHei",Arial,sans-serif; line-height:1.65; }
    main { max-width:1520px; margin:0 auto; background:var(--paper); padding:34px 46px 72px; box-shadow:0 0 40px rgba(24,38,64,.08); }
    h1 { font-size:30px; margin:0 0 8px; } h2 { margin-top:38px; padding-top:18px; border-top:1px solid var(--line); font-size:23px; } h3 { margin-top:25px; font-size:18px; }
    p, li { max-width:1160px; } .lede { font-size:18px; } .meta { color:var(--muted); font-size:14px; }
    .verdict { border-left:6px solid var(--blue); background:#edf4ff; padding:18px 22px; margin:22px 0; } .negative { border-left-color:var(--red); background:#fff1f1; } .positive { border-left-color:var(--green); background:#edf9f3; }
    code { background:#eef1f6; padding:2px 5px; border-radius:4px; } a { color:#174f9f; }
    .table-wrap { overflow:auto; margin:14px 0 22px; } table { border-collapse:collapse; min-width:800px; font-size:14px; } th,td { border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; } th { background:#edf2f8; white-space:nowrap; }
    figure { margin:24px 0 38px; } figure img { width:100%; height:auto; border:1px solid var(--line); background:white; } figcaption { color:var(--muted); font-size:14px; margin-top:8px; }
    .small { font-size:13px; color:var(--muted); } .links li { margin:6px 0; }
    @media (max-width:800px) { main { padding:22px 18px 50px; } h1 { font-size:25px; } }
    """

    html_text = f"""<!doctype html>
<html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>PERSON P1E 动态证据最小时序信息增益</title><style>{css}</style></head>
<body><main>
<h1>PERSON P1E：动态证据状态与最小时序信息增益</h1>
<p class='meta'>版本：dynamic_evidence_temporal_v1 / lag1_r02 · R02ZF 为已暴露开发语料 · 不设单帧资格 gate · 不授予 P1_PASS</p>
<div class='verdict'>
<strong>直接结论：</strong>透明的动态证据图已经建立，并证明真实序列中存在持续响应结构、gross 错误输运会破坏这种结构；但<strong>冻结 P0 相对不输运的特异信息增益尚未建立</strong>。在最强的 zero 对照下，incoming-max 中位优势仅 {number(max_zero['median_control_rank_minus_correct_rank'],1)} 名，正确更好/平/更差为 {pct(max_zero['correct_better_fraction'])} / {pct(max_zero['tie_fraction'])} / {pct(max_zero['correct_worse_fraction'])}；全部候选的 max/sum/mean 排序 Spearman 中位又高达 {number(all_node_max['median_frame_spearman_correct_vs_zero'],4)} / {number(all_node_sum['median_frame_spearman_correct_vs_zero'],4)} / {number(all_node_mean['median_frame_spearman_correct_vs_zero'],4)}。当前主要时序信息来自慢变化/近同坐标持续性，而不是已被分离出来的 P0-specific 位移信息。
</div>
<ul>
<li><strong>P01/P02：</strong>相对各自单帧 rank，P01 有 6/8 帧改善，中位改善 {number(p01['median_image_to_correct_rank_improvement'],1)} 名；P02 有 4/6 帧改善，中位改善 {number(p02['median_image_to_correct_rank_improvement'],1)} 名。但相对 zero transport，P01 仅 4/8 更好，P02 仅 2/6 更好，并存在 F483、F487、F490 的严重反例。</li>
<li><strong>P03/P04：</strong>0.8 m 邻域图没有观察到分离；正确 P0 的完整与互为最近邻 2σ 图中八个 manual 间隔都为 SHARED，zero 也完全相同。F490/F494 的 max/sum 排名严重下降，但 mean 仍为 3/2、线程仍长 23，说明动态证据向量内部是混合状态，不是“所有时序量共同失败”。</li>
<li><strong>候选缺失：</strong>P02 F482 在 0.8 m 下确实缺节点；F490 最近候选约 {number(next(row['nearest_candidate_distance_m'] for row in audit['missing_case_rows'] if row['frame_index']==490),3)} m，只比 0.8 m 多约 2 cm，是固定半径边界病例。当前 lag1 图不能创造缺失节点，也没有跨缺失帧的显式 missing-state bridge。</li>
</ul>

<h2>1. 这次到底检验了什么</h2>
<p>每帧先由既有 SAR-only C2 响应独立产生全部候选，不截断 Top-K。每个候选保留图像证据向量；冻结 P0 只把候选输运为一个带局部不确定度的可能区域；相邻帧候选再产生 incoming/outgoing 支持、歧义计数和透明短线程。reference 的数值内容没有参与节点、边或线程计算，ID 和固定偏移只用于图完成后的离线评价。</p>
<p class='small'>审计边界：运行前哈希检查读取过 reference CSV 的字节，且含 annotation 字段的 explorer 容器在图计算前已整体加载；图函数没有访问这些 annotation 字段。因此准确表述是“reference 内容未参与图计算”，而不是“相关数据从未被读取或加载”。本轮是计算依赖 GT-blind，不声称严格 sealed-data process isolation。</p>
<p>所以本实验问的是“候选证据状态如何变化”，不是“先过单帧 gate 才有资格看时序”，也不是把 P0 当真实平台轨迹或把伪彩亮度当人体固有 RCS。</p>

<h2>2. 图像、物理与时序各自贡献什么</h2>
<ol>
<li><strong>图像证据：</strong>C2 score、候选池 percentile/rank、局部竞争差、候选密度、C3 与局部结构各向异性。它告诉我们“这一帧哪里有响应、响应有多强、是否紧凑或共享”。</li>
<li><strong>物理/几何约束：</strong>扇面位置、固定物理尺度、支持区、冻结 P0 公共表观输运和局部背景残差。它只限定合理接续区域，不提供真实目标位移。</li>
<li><strong>时序证据：</strong>incoming support max/sum/mean、前驱/后继数、互为最近邻线程、共享/分叉状态。它允许弱候选得到支持，也允许强候选被后续证据降级。</li>
</ol>
<p><code>max</code> 读最强前驱，<code>sum</code> 累积全部前驱，二者都使用 <code>source_C2 × geometry</code>，没有乘入 destination C2，因此不是融合 posterior；<code>mean</code> 再除以几何权重和，弱化候选数量影响，但相对 zero 有 {pct(mean_zero['tie_fraction'])} reference 配对持平。帧内与 1σ 前驱数的 Spearman 中位约为 max={number(next(row['median_frame_spearman'] for row in audit['density_correlations'] if row['component']=='max' and row['count_radius']=='1sigma'),3)}、sum={number(next(row['median_frame_spearman'] for row in audit['density_correlations'] if row['component']=='sum' and row['count_radius']=='1sigma'),3)}、mean={number(next(row['median_frame_spearman'] for row in audit['density_correlations'] if row['component']=='mean' and row['count_radius']=='1sigma'),3)}。所以 max/sum 也混有“候选机会数/局部密度”，三者必须并列。</p>
<p class='small'>离线 <code>metric_best_within</code> 会为 image/max/sum/mean 各自在 0.8 m 邻域内重新选择最优节点；“image rank → temporal rank”是 reference 邻域覆盖与重排序诊断，不是运行时同一个候选不可逆地更新成新总分。</p>

<h2>3. R02 分目标动态状态</h2>
{html_table(target_headers, target_rows)}
<figure><img src='{html.escape(relative_url(figures['rank_dynamics']))}' alt='manual rank dynamics'><figcaption>逐 manual 帧的单帧 rank、正确 P0 incoming-max rank 与 zero-transport rank。纵轴为对数且 rank 1 在上方；所有困难帧都保留。</figcaption></figure>

<h2>4. 正确 P0 是否提供了单帧之外的新增信息</h2>
{html_table(control_headers, control_rows)}
<p>incoming-max 下，正确 P0 相对 reverse 的中位优势为 {number(max_reverse['median_control_rank_minus_correct_rank'],1)} 名、相对 +0.75 m 扰动为 {number(max_perturbed['median_control_rank_minus_correct_rank'],1)} 名、相对打乱帧为 {number(max_shuffled['median_control_rank_minus_correct_rank'],1)} 名。它说明 gross 错位和错误时序会破坏结构；但 +0.75 m 约为当前 lag1 位移的 7.3 倍、且有 {pct(control_fairness['tangential_perturbation_outside_target_mask_fraction'])} 预测落出目标帧有效区；shuffle 又只有一个 shift7，源候选池相对真实源每 pair 相差 {control_fairness['shuffled_source_pool_delta_min']} 到 +{control_fairness['shuffled_source_pool_delta_max']}。二者是 sanity check，不是校准 null。</p>
{html_table(all_node_headers, all_node_rows)}
{html_table(edge_headers, edge_rows)}
<p>正确 P0 与 zero 的 2σ 互为最近邻边有 {pct(zero_edges['intersection_over_correct'])} 重合，Jaccard={number(zero_edges['jaccard'],4)}；按 node 对齐的线程长度 Spearman={number(zero_thread_similarity['spearman'],4)}，{pct(zero_thread_similarity['exact_equal_fraction'])} 节点线程长度完全相同；shared reachable state 更是 {shared_audit['exact_state_match_count']}/{shared_audit['comparison_count']} 一致。这些全图 GT-blind 证据比单纯 reference 中位数更强地说明：lag1 的 P0-specific 增量尚未显示出来。</p>
<figure><img src='{html.escape(relative_url(figures['control_gain']))}' alt='control information gain'><figcaption>每个点是同一 reference 的配对差；正值表示正确 P0 rank 更好。max、sum、mean 的结论强度不同。</figcaption></figure>

<h2>5. 为什么正确 P0 和不输运如此接近</h2>
<p>冻结 lag1 公共输运的中位位移约 <strong>{number(transport['median_transport_displacement_m'],3)} m</strong>，而局部可能区域的中位 σ 约 <strong>{number(transport['median_sigma_region_m'],3)} m</strong>，二者比值约 {number(transport['median_transport_to_sigma_ratio'],2)}。因此 zero transport 通常仍落在同一个宽容区域内。这个尺度关系能解释“正确方向优于明显错误方向，但不容易击败原地持续性”。</p>
<p>局部误差支持并不均匀：{pct(uncertainty_audit['nearest8_fallback_fraction'])} 候选使用最近 8 锚点 fallback，{pct(uncertainty_audit['either_dimension_unbracketed_fraction'])} 至少有一个距离/方位维度未被所选锚点双侧包围。这些状态本轮按“动态证据向量”保留而未作为 gate，但应限制个案解释强度。</p>
<figure><img src='{html.escape(relative_url(figures['transport_scale']))}' alt='transport scale'><figcaption>逐 lag1 pair 的冻结 P0 位移与局部不确定区域尺度。该不确定度是运行时几何预算，不是严格校准置信上界。</figcaption></figure>

<h2>6. 长线程是否就是 P0 的新增信息</h2>
{html_table(thread_headers, thread_rows)}
<p>正确 P0 与 zero transport 的线程中位长度都为 {number(correct_threads['median_thread_node_count'],1)}，P90 都为 {number(correct_threads['p90_thread_node_count'],1)}，长度 ≥10 的节点比例分别为 {pct(correct_threads['node_fraction_in_threads_length_at_least_10'])} 与 {pct(zero_threads['node_fraction_in_threads_length_at_least_10'])}。长线程说明真实序列有持续结构，但大量持续性来自慢变化或同坐标延续，不能单独归功于 P0。</p>
{html_table(fixed_headers, fixed_rows)}
<figure><img src='{html.escape(relative_url(figures['threads']))}' alt='thread persistence'><figcaption>左：全部 GT-blind 线程的长度生存曲线；右：reference 邻域与四方向固定空间控制的线程长度。reference 附近确有更长结构，但正确 P0 与 zero transport 几乎相同。</figcaption></figure>
<figure><img src='{html.escape(relative_url(figures['spacetime']))}' alt='spacetime projection'><figcaption>x-y-t 的两种判别坐标投影。P01/P02 用 x，P03/P04 用 y；线程先 GT-blind 构建，reference 只用于结果后选择可视线程。当前邻域图没有形成两条可观察的分离管道。</figcaption></figure>
<p><code>SHARED</code> 必须谨慎解释：P01/P02 reference 间距为 {number(p01_p02_distance['min_distance_m'],3)}–{number(p01_p02_distance['max_distance_m'],3)} m，P03/P04 为 {number(p03_p04_distance['min_distance_m'],3)}–{number(p03_p04_distance['max_distance_m'],3)} m，而审计半径固定为 0.8 m，邻域天然高度重叠。30 个可评价 reference 行只对应 {outcome_audit['unique_frame_best_node_outcomes']} 个 unique frame×best-node outcome。因此 SHARED 只表示当前邻域集合重叠/未观察到分离，不证明物理响应必然融合或身份不可分。</p>
<h3>证据分量相互矛盾的关键病例</h3>
{html_table(component_case_headers, component_case_rows)}

<h2>7. 显示变化分层</h2>
<p>22 个 pair 中 baseline/high/elevated 分别为 16/5/1。manual paired rows 中 baseline n=26，正确 P0 相对 zero 的 incoming-max 中位优势为 0 名；high 只有 F488 的 4 个 reference 行，而且 P03/P04 等行共享同一节点，独立信息远少于 4；elevated 没有 manual reference。因此不能从本轮断言显示分层对 PERSON 时序证据的因果作用。详细逐层结果保存在机器可读 CSV。</p>

<h2>8. 直接病例：原图、C2 响应、候选关系与四种输运</h2>
<p class='small'>每幅图上排是源/目标原始 SAR 与 C2 响应，下排是正确 P0、zero、reverse 和 +0.75 m 扰动。三角形为输运预测，圆为 1σ 区域，线为互为最近邻关系。病例与裁剪区由 reference 在结果后选择，不参与任何节点、边或 rank 的生成。</p>
{''.join(case_html)}

<h2>9. 当前能回答与不能回答的内容</h2>
<div class='verdict positive'><strong>能回答：</strong>真实 R02 序列有持续 SAR 响应结构；明显错误方向、gross 偏移和错误帧序会破坏它；部分低 rank 候选在某些时刻能获得支持。</div>
<div class='verdict negative'><strong>不能回答：</strong>P0-specific lag1 信息增益尚未建立；当前时序不能稳定击败 zero transport、创造缺失节点，或在 0.8 m 重叠邻域中把 P03/P04 解析成两条身份线程，也不能据此冻结接口或授予 P1_PASS。</div>
<p>最小下一步不应重新堆单帧特征，也不应增加硬 gate。更有信息量的是：在不调 P0 的前提下，预先固定 lag3/两步接续和 missing-state bridge 的透明版本，检查位移尺度相对不确定区是否增大、弱候选是否跨短暂缺失恢复，以及正确 P0 是否开始稳定区别于 zero。若仍无区别，应把“同坐标慢变持续性占主导”作为核心阴性结果。</p>

<h2>10. 可复核文件</h2>
<ul class='links'>
<li><a href='00_DYNAMIC_EVIDENCE_MINIMAL_TEMPORAL_PROTOCOL_FROZEN_BEFORE_RUN.md'>运行前冻结协议</a></li>
<li><a href='{html.escape(relative_url(MANIFEST_JSON))}'>GT-blind runtime graph manifest</a></li>
<li><a href='{html.escape(relative_url(RUN_SUMMARY_JSON))}'>原始时序机器总结</a></li>
<li><a href='{html.escape(relative_url(PAIRED_REFERENCE_CSV))}'>逐 reference 正确 P0 与对照配对表</a></li>
<li><a href='{html.escape(relative_url(REFERENCE_OFFSET_CSV))}'>reference 与固定空间控制比较表</a></li>
<li><a href='{html.escape(relative_url(DISPLAY_STRATUM_CSV))}'>显示变化分层比较表</a></li>
<li><a href='{html.escape(relative_url(INTERPRETATION_JSON))}'>本报告机器可读解释总结</a></li>
<li><a href='{html.escape(METHOD_AUDIT_MD.name)}'>独立方法审阅与复现缺口</a></li>
<li><a href='{html.escape(relative_url(VALIDATION_JSON))}'>报告与哈希校验</a></li>
</ul>
<p class='small'>冻结 P0、B0R、C0-C3、候选召回结果和旧 P1E 结果均未修改；原始图像与标注只读；没有创建或移动 SAR 框；没有使用 optical/插值轨迹或 physical_target_id 构造图。复现审阅还记录了字段名碰撞、动态脚本/协议未被原 runtime manifest 自身冻结、fixed-offset/comparability 未预先 pin hash 等缺口；这些不改变当前数字，但限制其作为最终冻结接口的资格。</p>
</main></body></html>"""
    REPORT_HTML.write_text(html_text, encoding="utf-8")

    md_text = f"""# PERSON P1E 动态证据状态与最小时序信息增益

> 状态：TEMPORAL_STRUCTURE_PRESENT_P0_SPECIFIC_GAIN_NOT_ESTABLISHED  
> 数据角色：R02ZF 为已暴露开发语料；不设单帧资格 gate；不授予 P1_PASS。

## 结论

已经建立透明动态证据图，并证明真实序列有持续响应结构、gross 错误输运会破坏它；但冻结 P0 相对 zero transport 的特异信息增益尚未建立。

- 相对 zero transport 的 incoming-max 中位优势只有 {number(max_zero['median_control_rank_minus_correct_rank'],1)} 名，正确更好/平/更差为 {pct(max_zero['correct_better_fraction'])} / {pct(max_zero['tie_fraction'])} / {pct(max_zero['correct_worse_fraction'])}；全部候选 max/sum/mean 排序 Spearman 中位为 {number(all_node_max['median_frame_spearman_correct_vs_zero'],4)} / {number(all_node_sum['median_frame_spearman_correct_vs_zero'],4)} / {number(all_node_mean['median_frame_spearman_correct_vs_zero'],4)}。
- P01 相对单帧在 6/8 帧改善，中位改善 {number(p01['median_image_to_correct_rank_improvement'],1)} 名；P02 在 4/6 帧改善，中位改善 {number(p02['median_image_to_correct_rank_improvement'],1)} 名。但相对 zero，P01 仅 4/8 更好，P02 仅 2/6 更好。
- P02 F482 在 0.8 m 下缺节点；F490 最近节点为约 0.820 m，是阈值边界病例。时序不能创造节点。
- P03/P04 的八个 manual 间隔在正确 P0 和 zero 下都保持 SHARED。F490/F494 的 max/sum 降级，但 mean rank 仍为 3/2、线程长 23，不能写成所有时序分量共同失败。
- 正确 P0 与 zero 的线程长度统计几乎相同，长线程不能单独归功于 P0。

## R02 分目标

{markdown_table(target_headers, target_rows)}

![逐帧 rank]({relative_url(figures['rank_dynamics'])})

## 正确 P0 与对照

{markdown_table(control_headers, control_rows)}

### 全部候选的 CORRECT-vs-ZERO 相似度

{markdown_table(all_node_headers, all_node_rows)}

{markdown_table(edge_headers, edge_rows)}

正确 P0 与 zero 的互为最近邻边 {pct(zero_edges['intersection_over_correct'])} 重合，线程长度 {pct(zero_thread_similarity['exact_equal_fraction'])} 完全相同，shared state {shared_audit['exact_state_match_count']}/{shared_audit['comparison_count']} 一致。+0.75 m 与 shuffle 只是 gross sanity，不是校准 null。

![正确 P0 与对照]({relative_url(figures['control_gain'])})

冻结 lag1 位移中位数约 {number(transport['median_transport_displacement_m'],3)} m，局部区域 σ 中位数约 {number(transport['median_sigma_region_m'],3)} m；zero transport 通常仍落在同一可能区域内。

局部误差支持中，{pct(uncertainty_audit['nearest8_fallback_fraction'])} 使用 nearest-8 fallback，{pct(uncertainty_audit['either_dimension_unbracketed_fraction'])} 至少一个距离/方位维度未被锚点双侧包围。

![输运尺度]({relative_url(figures['transport_scale'])})

## 线程与固定空间控制

{markdown_table(thread_headers, thread_rows)}

{markdown_table(fixed_headers, fixed_rows)}

![线程持续性]({relative_url(figures['threads'])})

![x-y-t 投影]({relative_url(figures['spacetime'])})

`SHARED` 使用 0.8 m 邻域，而 P01/P02 间距仅 {number(p01_p02_distance['min_distance_m'],3)}–{number(p01_p02_distance['max_distance_m'],3)} m、P03/P04 仅 {number(p03_p04_distance['min_distance_m'],3)}–{number(p03_p04_distance['max_distance_m'],3)} m；它只表示邻域重叠/未观察到分离，不证明物理融合。

### 证据分量相互矛盾的病例

{markdown_table(component_case_headers, component_case_rows)}

## 直接病例

{chr(10).join(case_md)}

## 当前边界

能确认的是：真实序列存在持续 SAR 响应，明显错误方向、gross 偏移和错误帧序会破坏它，部分低 rank 候选在某些时刻能得到支持。

仍不能确认的是：P0-specific lag1 信息增益、缺失节点恢复、P03/P04 身份分离，或可冻结的 SAR-only 定位接口。

建议的最小后续是预先固定 lag3/两步接续和 missing-state bridge，继续比较 correct、zero、错误输运与打乱帧；不新增硬 gate，也不重调 P0。

## 文件

- [HTML 报告]({REPORT_HTML.name})
- [运行前冻结协议](00_DYNAMIC_EVIDENCE_MINIMAL_TEMPORAL_PROTOCOL_FROZEN_BEFORE_RUN.md)
- [runtime graph manifest]({relative_url(MANIFEST_JSON)})
- [逐 reference 配对表]({relative_url(PAIRED_REFERENCE_CSV)})
- [固定空间控制比较]({relative_url(REFERENCE_OFFSET_CSV)})
- [显示分层比较]({relative_url(DISPLAY_STRATUM_CSV)})
- [机器可读解释]({relative_url(INTERPRETATION_JSON)})
- [独立方法审阅与复现缺口]({METHOD_AUDIT_MD.name})
- [报告校验]({relative_url(VALIDATION_JSON)})

冻结 P0、B0R、C0-C3 与旧 P1E 结果均未修改；不授予 P1_PASS，不声称盲验证。
    """
    REPORT_MD.write_text(md_text, encoding="utf-8")

    method_audit_text = f"""# PERSON P1E 动态证据方法审阅

> 审阅性质：独立只读复核；不修改冻结 P0、B0R、C0-C3、候选或动态图结果。  
> 总判断：计算依赖保持 GT-blind；时序持续结构成立；P0-specific lag1 增益未建立。

## 1. GT-blind 的准确边界

- `build_static_nodes` 只使用既有 C2 候选、SAR 图、单帧有效掩膜、C2/C3 和扇面几何；节点/边/线程没有访问下一帧 reference、target ID、optical 或插值轨迹。
- reference CSV 在运行图前被 SHA256 读取，含 annotation 字段的 explorer 容器也在图前整体加载；但这些 reference/annotation 数值没有进入图计算。
- 因此允许的表述是“reference content did not participate in graph computation”，不是“reference/annotation data were never read or loaded”。本轮不声称严格 sealed-data process isolation。
- 冻结 P0 的 background anchors 继承了 P0 阶段的 PERSON 排除掩膜；这不是本轮定位 GT 泄漏，但未来真正在线 SAR-only P0 仍需定义运行时排除区来源。

## 2. CORRECT 与 ZERO 的全图相似度

{markdown_table(all_node_headers, all_node_rows)}

{markdown_table(edge_headers, edge_rows)}

- CORRECT-vs-ZERO 互为最近邻边覆盖率 {pct(zero_edges['intersection_over_correct'])}，Jaccard={number(zero_edges['jaccard'],4)}。
- 按 node 对齐线程长度 Spearman={number(zero_thread_similarity['spearman'],4)}，完全相等 {pct(zero_thread_similarity['exact_equal_fraction'])}，绝对差中位数 {number(zero_thread_similarity['median_absolute_delta'],1)}。
- shared reachable state 为 {shared_audit['exact_state_match_count']}/{shared_audit['comparison_count']} 完全一致。
- 这比“reference 中位 +1.5 rank”更直接地说明：当前主要时序结构是慢变化/同坐标持续性，尚未分离出稳定 P0-specific 增量。

## 3. 对照公平性

- `ZERO_TRANSPORT` 是最强对照：同帧池、同目标帧、同不确定度，只去掉 P0 位移。
- `REVERSE_P0` 是同尺度错误方向对照，但 CORRECT 与 REVERSE 的边/线程仍有高重合。
- `TANGENTIAL_PLUS_0_75M` 约为真实 lag1 位移的 7.3 倍，且 {pct(control_fairness['tangential_perturbation_outside_target_mask_fraction'])} 预测出有效区，只能作 gross sanity。
- `SHUFFLED_SOURCE_SHIFT7` 只有一个固定 shift；源候选池相对真实源每 pair 相差 {control_fairness['shuffled_source_pool_delta_min']} 至 +{control_fairness['shuffled_source_pool_delta_max']}，混入帧内容、候选池规模和显示差异，不是校准随机 null。

## 4. 不确定度与局部锚点覆盖

- 6147 个 source-node uncertainty row 中，nearest-8 fallback 为 {pct(uncertainty_audit['nearest8_fallback_fraction'])}。
- radial 未双侧包围 {pct(uncertainty_audit['radial_unbracketed_fraction'])}；theta 未双侧包围 {pct(uncertainty_audit['theta_unbracketed_fraction'])}；任一维未包围 {pct(uncertainty_audit['either_dimension_unbracketed_fraction'])}。
- sigma 中位/P90/最大为 {number(uncertainty_audit['median_sigma_region_m'],4)} / {number(uncertainty_audit['p90_sigma_region_m'],4)} / {number(uncertainty_audit['max_sigma_region_m'],4)} m；它是设计容差层级，不是校准置信区间。
- lag1 P0 位移中位约 {number(transport['median_transport_displacement_m'],4)} m，仅为 sigma 的 {number(transport['median_transport_to_sigma_ratio'],3)}，直接限制 CORRECT 与 ZERO 可分性。

## 5. reference 重复与 SHARED 语义

- 30 个 incoming-max 可评价 reference 行只对应 {outcome_audit['unique_frame_best_node_outcomes']} 个 unique `(frame, best node)` outcome；10 个 outcome 被两个 reference 共用。
- P01/P02 间距 {number(p01_p02_distance['min_distance_m'],3)}–{number(p01_p02_distance['max_distance_m'],3)} m；P03/P04 间距 {number(p03_p04_distance['min_distance_m'],3)}–{number(p03_p04_distance['max_distance_m'],3)} m；审计半径为 0.8 m。
- `SHARED` 只表示两个 0.8 m 邻域候选集合有交集，并不区分“只有共享节点”和“共享节点加各自独立节点”，也不具备 identity 语义。
- 所以“当前邻域图未观察到分离”成立；“物理响应必然融合/身份不可分”不成立。

## 6. 证据分量不能合并成单一结论

{markdown_table(component_case_headers, component_case_rows)}

- max/sum 只使用 `source_C2 × geometry`，不含 destination C2；不是 posterior。
- sum 显著混入候选密度；max 也受更多前驱机会和最近几何影响。
- mean 弱化密度影响，但 CORRECT-vs-ZERO reference 配对 {pct(mean_zero['tie_fraction'])} 持平。
- 离线评价会为每个分量重新选择 0.8 m 内最优节点，所以 rank delta 是邻域重排序诊断，不是同一候选状态的运行时更新。

## 7. 复现与 schema 缺口

- 原 runtime manifest 没有冻结动态脚本自身（当前 SHA256 `{reproducibility['dynamic_script_current_sha256']}`）或运行前协议（当前 `{reproducibility['protocol_current_sha256']}`）。
- fixed-offset source（当前 `{reproducibility['fixed_offset_source_current_sha256']}`）和 B0R comparability（当前 `{reproducibility['B0R_comparability_current_sha256']}`）未进入预运行 `EXPECTED_HASHES`。
- 当前 R02 lag1 comparability 为 {reproducibility['R02_lag1_comparable_true_count']}/{reproducibility['R02_lag1_comparability_rows']} True，因此当前结果未受影响；但动态图代码没有 assert/filter `pair_comparable`，未来扩展会有静默风险。
- incoming/outgoing 同名 `best_support_normalized_error` merge 后形成 `_x/_y`，SHUFFLED 又保留无后缀列；消费 `dynamic_candidate_state.csv` 时必须按 condition 明确读取，不能把无后缀列当通用字段。

## 8. 审阅后允许的总括

当前实验建立了透明的 GT-blind 候选图，并证明真实序列有持续响应且 gross 错位会破坏它；但由于 P0 lag1 位移仅约 0.34 个设计容差，CORRECT 与 ZERO 在候选排序、边、线程和 shared 状态上高度相同，尚未显示稳定的 P0-specific 时序信息增益。P01 有局部恢复，P02 高度异质，P03/P04 持续共享且当前 0.8 m 邻域定义本身不能检验身份分离。
"""
    METHOD_AUDIT_MD.write_text(method_audit_text, encoding="utf-8")


def validate_report(
    manifest: dict[str, Any], case_paths: list[Path], figure_paths: list[Path]
) -> dict[str, Any]:
    html_text = REPORT_HTML.read_text(encoding="utf-8")
    references = re.findall(r"(?:src|href)=['\"]([^'\"]+)['\"]", html_text)
    local_references = [
        item
        for item in references
        if not item.startswith(("http://", "https://", "data:", "#"))
    ]
    missing: list[str] = []
    for item in local_references:
        path = (REPORT_ROOT / item).resolve()
        if not path.exists():
            missing.append(item)
    unreadable = [
        str(path)
        for path in case_paths + figure_paths
        if cv2.imread(str(path), cv2.IMREAD_COLOR) is None
    ]
    checks = {
        "workspace_exact": WORKSPACE.resolve()
        == Path(r"D:\profile\research\workspace").resolve(),
        "P0_hash": sha256_file(P0_SCRIPT) == EXPECTED_P0_SHA256,
        "P1E_hash": sha256_file(P1E_SCRIPT) == EXPECTED_P1E_SHA256,
        "candidate_audit_hash": sha256_file(AUDIT_SCRIPT) == EXPECTED_AUDIT_SHA256,
        "dynamic_script_hash": sha256_file(DYNAMIC_SCRIPT) == EXPECTED_DYNAMIC_SHA256,
        "runtime_manifest_hash": sha256_file(MANIFEST_JSON)
        == EXPECTED_MANIFEST_SHA256,
        "run_summary_hash": sha256_file(RUN_SUMMARY_JSON)
        == EXPECTED_RUN_SUMMARY_SHA256,
        "contract_hashes_all_match": all(
            bool(row.get("match")) for row in manifest["input_hash_checks"]
        ),
        "runtime_manifest_reference_use_flag_is_false": not bool(
            manifest["manual_reference_loaded_during_runtime_graph"]
        ),
        "runtime_graph_no_topk": manifest["candidate_topk_truncation"] is None,
        "html_links_complete": not missing,
        "images_readable": not unreadable,
        "case_count": len(case_paths) == len(CASE_SPECS),
    }
    return {
        "schema": "PERSON_P1E_DYNAMIC_EVIDENCE_REPORT_VALIDATION_V1",
        "checks": checks,
        "html_local_reference_count": int(len(local_references)),
        "missing_local_references": missing,
        "checked_image_count": int(len(case_paths) + len(figure_paths)),
        "unreadable_images": unreadable,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(SCRIPT_PATH).lower() or "old_work" in str(REPORT_ROOT).lower():
        raise RuntimeError("forbidden old_work dependency")
    if not (REPORT_ROOT / "00_DYNAMIC_EVIDENCE_MINIMAL_TEMPORAL_PROTOCOL_FROZEN_BEFORE_RUN.md").is_file():
        raise RuntimeError("missing frozen temporal protocol")

    expected = {
        P0_SCRIPT: EXPECTED_P0_SHA256,
        P1E_SCRIPT: EXPECTED_P1E_SHA256,
        AUDIT_SCRIPT: EXPECTED_AUDIT_SHA256,
        DYNAMIC_SCRIPT: EXPECTED_DYNAMIC_SHA256,
        MANIFEST_JSON: EXPECTED_MANIFEST_SHA256,
        RUN_SUMMARY_JSON: EXPECTED_RUN_SUMMARY_SHA256,
    }
    for path, expected_hash in expected.items():
        actual = sha256_file(path)
        if actual != expected_hash:
            raise RuntimeError(
                f"hash mismatch {path}: expected {expected_hash}, actual {actual}"
            )

    audit = load_module("person_dynamic_report_audit", AUDIT_SCRIPT)
    p0 = load_module("person_dynamic_report_p0", P0_SCRIPT)
    p1e = load_module("person_dynamic_report_p1e", P1E_SCRIPT)
    p0.assert_workspace_scope()
    _, input_hash_checks = p0.load_contract_and_verify()
    if not all(bool(row.get("match")) for row in input_hash_checks):
        raise RuntimeError("contract input SHA256 mismatch")

    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    run_summary = json.loads(RUN_SUMMARY_JSON.read_text(encoding="utf-8"))
    tables = read_tables()
    if not tables["nodes"]["generated_without_annotation"].astype(bool).all():
        raise RuntimeError("node provenance is not uniformly GT-blind")

    POST_DIR.mkdir(parents=True, exist_ok=True)
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    paired = make_paired_reference(tables["references"], tables["pairs"])
    offset_comparison = make_reference_offset_comparison(
        tables["references"], tables["offsets"]
    )
    display_rows = build_display_stratum_rows(
        tables["references"], tables["pairs"]
    )
    transport_per_pair, transport_summary = build_transport_scale(
        tables["outgoing"], tables["nodes"]
    )
    paired.to_csv(PAIRED_REFERENCE_CSV, index=False, encoding="utf-8-sig")
    offset_comparison.to_csv(
        REFERENCE_OFFSET_CSV, index=False, encoding="utf-8-sig"
    )
    display_rows.to_csv(DISPLAY_STRATUM_CSV, index=False, encoding="utf-8-sig")

    interpretation = build_interpretation(
        manifest,
        run_summary,
        tables,
        paired,
        offset_comparison,
        display_rows,
        transport_per_pair,
        transport_summary,
        input_hash_checks,
    )
    INTERPRETATION_JSON.write_text(
        json.dumps(json_safe(interpretation), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    figures = {
        "rank_dynamics": VIS_DIR / "manual_reference_rank_dynamics.png",
        "control_gain": VIS_DIR / "correct_p0_control_information_gain.png",
        "transport_scale": VIS_DIR / "lag1_transport_vs_uncertainty_scale.png",
        "threads": VIS_DIR / "thread_persistence_reference_vs_offsets.png",
        "spacetime": VIS_DIR / "spacetime_response_tube_projection.png",
    }
    plot_manual_rank_dynamics(paired, figures["rank_dynamics"])
    plot_control_information_gain(tables["references"], figures["control_gain"])
    plot_transport_scale(transport_per_pair, figures["transport_scale"])
    plot_thread_persistence(
        tables["threads"], tables["references"], tables["offsets"], figures["threads"]
    )
    plot_spacetime_projection(
        tables["thread_members"], tables["nodes"], tables["references"], figures["spacetime"]
    )

    explorer = audit.load_explorer()
    frame_map = {frame["sar_frame_uid"]: frame for frame in explorer["frames"]}
    cache: dict[str, dict[str, Any]] = {}
    case_registry: list[dict[str, Any]] = []
    case_paths: list[Path] = []
    for index, spec in enumerate(CASE_SPECS, start=1):
        output_path = VIS_DIR / f"case_{index:02d}_{spec['slug']}.png"
        case_registry.append(
            plot_pair_case(
                audit,
                p0,
                p1e,
                frame_map,
                tables,
                spec,
                output_path,
                cache,
            )
        )
        case_paths.append(output_path)
    pd.DataFrame(case_registry).to_csv(
        CASE_REGISTRY_CSV, index=False, encoding="utf-8-sig"
    )

    write_reports(interpretation, case_registry, figures)
    # Create the linked validation artifact before checking local report links;
    # it is immediately replaced by the complete validation payload below.
    VALIDATION_JSON.write_text("{}\n", encoding="utf-8")
    validation = validate_report(manifest, case_paths, list(figures.values()))
    VALIDATION_JSON.write_text(
        json.dumps(json_safe(validation), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if validation["status"] != "PASS":
        raise RuntimeError(f"report validation failed: {validation}")
    print(
        json.dumps(
            {
                "status": interpretation["status"],
                "report_html": str(REPORT_HTML),
                "report_md": str(REPORT_MD),
                "case_count": len(case_paths),
                "validation": validation["status"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
