#!/usr/bin/env python3
"""Render the semantic-correction report from frozen candidate-recall CSVs.

This is a report-only/post-processing step. It does not regenerate GT-blind
candidates, retune P0, change C0-C3, or modify the previous P1E outputs. The
only response-map computation is a deterministic replay for explanatory case
figures; all candidate coordinates and ranks are read from the already written
CSV files.
"""

from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
import numpy as np
import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = (
    WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
)
P1E_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface"
REPORT_ROOT = P1E_ROOT / "candidate_recall_semantic_split_v1"
DATA_DIR = REPORT_ROOT / "single_frame_candidate_recall"
VIS_DIR = DATA_DIR / "visualizations_v2"

AUDIT_SCRIPT = TASK_DIR / "run_p1e_candidate_recall_audit.py"
P0_SCRIPT = TASK_DIR / "run_p0_common_apparent_motion.py"
P1E_SCRIPT = TASK_DIR / "run_p1e_single_frame_position_specificity.py"
OLD_P1E_DIR = P1E_ROOT / "single_frame" / "manual_v4_physical_scale_p0_mask"

PRIMARY = "C2_COMPACT_JET_GRADIENT_CONSENSUS"
DIAGNOSTIC = "C3_ISOTROPIC_BLOB_RIDGE_SUPPRESSED"
AUDIT_CANDIDATES = (PRIMARY, DIAGNOSTIC)
RUNS = ("R01ZF", "R02ZF", "R03ZF", "R04ZF")
RADIUS_M = 0.80

EXPECTED_P0_SHA256 = "0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8"
EXPECTED_P1E_SHA256 = "98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1"
EXPECTED_B0R_SCRIPT_SHA256 = "3C0DFB20B58D445D224DAD7426AEB0E6DA5E065DB07059B462F1FE528CFC8ABF"

INTERPRETATION_CSV = DATA_DIR / "manual_reference_candidate_interpretation_v2.csv"
CASE_REGISTRY_CSV = DATA_DIR / "case_registry_v2.csv"
SUMMARY_JSON = DATA_DIR / "candidate_semantic_interpretation_v2.json"
REPORT_MD = REPORT_ROOT / "01_CANDIDATE_RECALL_SEMANTIC_INTERPRETATION.md"
REPORT_HTML = REPORT_ROOT / "P1E_CANDIDATE_RECALL_SEMANTIC_SPLIT_REPORT.html"
VALIDATION_JSON = DATA_DIR / "report_validation.json"

CASE_SPECS = (
    {
        "frame_uid": "R02ZF_SARF000472",
        "target_id": "R02ZF_SARPERSON01",
        "slug": "r02_f472_p01_shared_low_rank",
        "note": "P01/P02 share a low-ranked C2 peak while P03/P04 share a Top-2 peak in the same frame.",
    },
    {
        "frame_uid": "R02ZF_SARF000482",
        "target_id": "R02ZF_SARPERSON02",
        "slug": "r02_f482_p02_missing",
        "note": "P02 has no C2 candidate within 0.8 m; P03/P04 still share the Top-1 response.",
    },
    {
        "frame_uid": "R02ZF_SARF000494",
        "target_id": "R02ZF_SARPERSON01",
        "slug": "r02_f494_p01_long_chain",
        "note": "P01/P02 share rank 24 on the long response chain; P03/P04 share rank 1.",
    },
    {
        "frame_uid": "R02ZF_SARF000483",
        "target_id": "R02ZF_SARPERSON03",
        "slug": "r02_f483_p03_top1_shared",
        "note": "P03/P04 are both covered by the same Top-1 C2 peak: candidate existence is strong, uniqueness is not.",
    },
    {
        "frame_uid": "R02ZF_SARF000490",
        "target_id": "R02ZF_SARPERSON03",
        "slug": "r02_f490_p03_shared_rank12",
        "note": "The shared P03/P04 response falls to rank 12, showing frame-dependent shortlist instability.",
    },
    {
        "frame_uid": "R03ZF_SARF000458",
        "target_id": "R03ZF_SARPERSON01",
        "slug": "r03_f458_single_frame_full",
        "note": "Omega_single_v1 is FULL and a C2 peak lies about 0.02 m from reference, but only at rank 18.",
    },
    {
        "frame_uid": "R03ZF_SARF000488",
        "target_id": "R03ZF_SARPERSON01",
        "slug": "r03_f488_top5_boundary",
        "note": "Boundary-scene single-frame observation is FULL and the nearby C2 peak reaches rank 5.",
    },
    {
        "frame_uid": "R04ZF_SARF000000",
        "target_id": "R04ZF_SARPERSON01",
        "slug": "r04_f000_isolated_top1",
        "note": "An isolated response case where both C2 and C3 place rank 1 near the reference.",
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


def pct(value: float | int | None, digits: int = 1) -> str:
    if value is None or not np.isfinite(float(value)):
        return "—"
    return f"{100.0 * float(value):.{digits}f}%"


def number(value: float | int | None, digits: int = 2) -> str:
    if value is None or not np.isfinite(float(value)):
        return "—"
    return f"{float(value):.{digits}f}"


def target_short(target_id: str) -> str:
    match = re.search(r"(\d+)$", str(target_id))
    return f"P{int(match.group(1)):02d}" if match else str(target_id)


def relative_url(path: Path) -> str:
    return path.relative_to(REPORT_ROOT).as_posix()


def add_any_rank_interpretation(
    references: pd.DataFrame,
    candidates: pd.DataFrame,
    frame_map: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Add overlapping, non-exclusive semantic layers without changing recall."""
    output = references.copy()
    output["shared_candidate_count_0_80m_any_rank"] = 0
    output["shared_candidate_ranks_0_80m_any_rank"] = ""
    output["shared_best_candidate_reference_count_0_80m_any_rank"] = 0
    output["max_reference_count_per_shared_candidate_0_80m_any_rank"] = 0
    output["shared_with_target_ids_0_80m_any_rank"] = ""
    output["response_merging_suspected_any_rank"] = False
    output["nearest_candidate_rank_fraction_of_frame_pool"] = np.nan

    for (frame_uid, candidate_name), group in output.groupby(
        ["frame_uid", "candidate"], sort=False
    ):
        frame = frame_map[str(frame_uid)]
        px_per_m = float(frame["geometry"]["radius_px"]) / float(
            frame["geometry"]["outer_range_m"]
        )
        candidate_group = candidates[
            (candidates["frame_uid"] == frame_uid)
            & (candidates["candidate"] == candidate_name)
        ].sort_values("rank")
        if candidate_group.empty:
            continue

        reference_xy = group[["reference_x_px", "reference_y_px"]].to_numpy(float)
        candidate_xy = candidate_group[["x_px", "y_px"]].to_numpy(float)
        distances_m = (
            np.linalg.norm(reference_xy[:, None, :] - candidate_xy[None, :, :], axis=2)
            / px_per_m
        )
        within = distances_m <= RADIUS_M + 1e-9
        reference_count_per_candidate = within.sum(axis=0)
        ranks = candidate_group["rank"].to_numpy(int)
        target_ids = group["target_id"].astype(str).to_numpy()
        output_indices = list(group.index)

        for local_index, output_index in enumerate(output_indices):
            in_radius_columns = np.flatnonzero(within[local_index])
            shared_columns = np.array(
                [
                    column
                    for column in in_radius_columns
                    if int(reference_count_per_candidate[column]) > 1
                ],
                dtype=int,
            )
            shared_ranks = sorted(int(ranks[column]) for column in shared_columns)
            output.at[output_index, "shared_candidate_count_0_80m_any_rank"] = int(
                len(shared_columns)
            )
            output.at[output_index, "shared_candidate_ranks_0_80m_any_rank"] = ";".join(
                str(rank) for rank in shared_ranks
            )
            output.at[output_index, "response_merging_suspected_any_rank"] = bool(
                len(shared_columns)
            )
            if len(shared_columns):
                output.at[
                    output_index,
                    "max_reference_count_per_shared_candidate_0_80m_any_rank",
                ] = int(max(reference_count_per_candidate[column] for column in shared_columns))
                shared_targets: set[str] = set()
                for column in shared_columns:
                    for other_index in np.flatnonzero(within[:, column]):
                        if other_index != local_index:
                            shared_targets.add(str(target_ids[other_index]))
                output.at[
                    output_index, "shared_with_target_ids_0_80m_any_rank"
                ] = ";".join(sorted(shared_targets))

            if len(in_radius_columns):
                best_column = min(in_radius_columns, key=lambda column: int(ranks[column]))
                output.at[
                    output_index,
                    "shared_best_candidate_reference_count_0_80m_any_rank",
                ] = int(reference_count_per_candidate[best_column])

            nearest_rank = output.at[output_index, "nearest_candidate_rank"]
            candidate_count = output.at[output_index, "candidate_count_frame"]
            if np.isfinite(nearest_rank) and np.isfinite(candidate_count) and candidate_count > 0:
                output.at[
                    output_index, "nearest_candidate_rank_fraction_of_frame_pool"
                ] = float(nearest_rank) / float(candidate_count)

    def presence_class(row: pd.Series) -> str:
        if row["reference_support_status"] == "INVALID":
            return "SINGLE_FRAME_INVALID"
        if bool(row["recall_at_1_r_80cm"]):
            return "CANDIDATE_PRESENT_TOP1"
        if bool(row["recall_at_5_r_80cm"]):
            return "CANDIDATE_RANK_COMPETITION_TOP5"
        if (
            np.isfinite(row["nearest_candidate_distance_m"])
            and float(row["nearest_candidate_distance_m"]) <= RADIUS_M
        ):
            return "CANDIDATE_RANK_COMPETITION_BEYOND_TOP5"
        return "CANDIDATE_MISSING_OR_CURRENT_REPRESENTATION_FAILURE"

    output["candidate_presence_class_v2"] = output.apply(presence_class, axis=1)
    output["boundary_or_truncation_flag_v2"] = output[
        "reference_support_status"
    ].isin(["TRUNCATED", "INVALID"])

    def combined_interpretation(row: pd.Series) -> str:
        labels = [str(row["candidate_presence_class_v2"])]
        if bool(row["response_merging_suspected_any_rank"]):
            labels.append("RESPONSE_MERGING_SUSPECTED_ANY_RANK")
        if row["reference_support_status"] == "TRUNCATED":
            labels.append("BORDER_TRUNCATED")
        return " + ".join(labels)

    output["semantic_case_interpretation_v2"] = output.apply(
        combined_interpretation, axis=1
    )
    output["response_merging_semantics_v2"] = (
        "ONE_OR_MORE_GT_BLIND_CANDIDATE_PEAKS_FALL_WITHIN_0_80M_OF_MULTIPLE_"
        "MANUAL_REFERENCE_CENTERS;_DIAGNOSTIC_ONLY_NOT_PHYSICAL_FUSION_PROOF"
    )
    return output


def summarize_reference_group(rows: pd.DataFrame) -> dict[str, Any]:
    evaluable = rows[rows["reference_support_status"] != "INVALID"].copy()
    result: dict[str, Any] = {
        "reference_count": int(len(rows)),
        "evaluable_count": int(len(evaluable)),
        "support_status_counts": dict(
            sorted(Counter(rows["reference_support_status"]).items())
        ),
        "candidate_within_0_80m_rate_any_rank": (
            float((evaluable["nearest_candidate_distance_m"] <= RADIUS_M).mean())
            if len(evaluable)
            else math.nan
        ),
        "median_nearest_candidate_distance_m": (
            float(evaluable["nearest_candidate_distance_m"].median())
            if len(evaluable)
            else math.nan
        ),
        "median_nearest_candidate_rank": (
            float(evaluable["nearest_candidate_rank"].median())
            if len(evaluable)
            else math.nan
        ),
        "median_nearest_candidate_rank_fraction_of_frame_pool": (
            float(evaluable["nearest_candidate_rank_fraction_of_frame_pool"].median())
            if len(evaluable)
            else math.nan
        ),
        "response_merging_suspected_any_rank_rate": (
            float(evaluable["response_merging_suspected_any_rank"].astype(bool).mean())
            if len(evaluable)
            else math.nan
        ),
        "shared_best_candidate_rate_any_rank": (
            float(
                (
                    evaluable[
                        "shared_best_candidate_reference_count_0_80m_any_rank"
                    ]
                    > 1
                ).mean()
            )
            if len(evaluable)
            else math.nan
        ),
        "candidate_presence_class_counts_v2": dict(
            sorted(Counter(evaluable["candidate_presence_class_v2"]).items())
        ),
    }
    for k_value in (1, 2, 3, 5):
        for radius_m in (0.30, 0.50, 0.80):
            column = f"recall_at_{k_value}_r_{int(round(radius_m * 100)):02d}cm"
            result[column] = float(evaluable[column].mean()) if len(evaluable) else math.nan
    return result


def build_summary(
    p0: Any,
    interpretation: pd.DataFrame,
    frame_counts: pd.DataFrame,
    controls: pd.DataFrame,
    original_summary: dict[str, Any],
    old_metrics: pd.DataFrame,
    input_hash_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    group_summaries: list[dict[str, Any]] = []
    for candidate_name in AUDIT_CANDIDATES:
        candidate_rows = interpretation[interpretation["candidate"] == candidate_name]
        group_summaries.append(
            {
                "candidate": candidate_name,
                "group": "ALL",
                **summarize_reference_group(candidate_rows),
            }
        )
        for run_id in RUNS:
            run_rows = candidate_rows[candidate_rows["run_id"] == run_id]
            group_summaries.append(
                {
                    "candidate": candidate_name,
                    "group": "RUN",
                    "run_id": run_id,
                    **summarize_reference_group(run_rows),
                }
            )
        r02_rows = candidate_rows[candidate_rows["run_id"] == "R02ZF"]
        for target_id, target_rows in r02_rows.groupby("target_id"):
            group_summaries.append(
                {
                    "candidate": candidate_name,
                    "group": "R02_TARGET",
                    "run_id": "R02ZF",
                    "target_id": target_id,
                    **summarize_reference_group(target_rows),
                }
            )

    candidate_count_summaries: list[dict[str, Any]] = []
    for (run_id, candidate_name), rows in frame_counts.groupby(
        ["run_id", "candidate"]
    ):
        candidate_count_summaries.append(
            {
                "run_id": run_id,
                "candidate": candidate_name,
                "frame_count": int(rows["frame_uid"].nunique()),
                "candidate_count_min": int(rows["candidate_count"].min()),
                "candidate_count_median": float(rows["candidate_count"].median()),
                "candidate_count_max": int(rows["candidate_count"].max()),
                "candidate_min_spacing_m_min": float(
                    rows["candidate_min_spacing_m"].min()
                ),
                "candidate_min_spacing_m_median": float(
                    rows["candidate_min_spacing_m"].median()
                ),
            }
        )

    r03_new = interpretation[
        (interpretation["run_id"] == "R03ZF")
        & (interpretation["candidate"] == PRIMARY)
    ].copy()
    r03_old = old_metrics[
        (old_metrics["run_id"] == "R03ZF")
        & (old_metrics["candidate"] == PRIMARY)
    ][["frame_uid", "target_id", "evaluation_status"]].copy()
    r03_comparison = r03_new.merge(
        r03_old, on=["frame_uid", "target_id"], how="left"
    )[
        [
            "frame_uid",
            "frame_index",
            "target_id",
            "evaluation_status",
            "reference_support_status",
            "nearest_candidate_distance_m",
            "nearest_candidate_rank",
            "recall_at_5_r_80cm",
        ]
    ].to_dict("records")

    r02_offset = controls[
        (controls["run_id"] == "R02ZF")
        & (controls["candidate"] == PRIMARY)
        & (controls["control_support_status"] != "INVALID")
    ]
    offset_direction_recall5 = {
        direction: float(rows["recall_at_5_r_80cm"].mean())
        for direction, rows in r02_offset.groupby("control_direction")
    }

    hashes = {
        "P0_script_sha256": sha256_file(P0_SCRIPT),
        "P1E_C0_C3_script_sha256": sha256_file(P1E_SCRIPT),
        "B0R_script_sha256": sha256_file(TASK_DIR / "run_b0r_minimal_applicability.py"),
        "candidate_audit_script_sha256": sha256_file(AUDIT_SCRIPT),
        "candidate_csv_sha256": sha256_file(
            DATA_DIR / "gt_blind_candidates_all_processed_frames.csv"
        ),
        "manual_reference_recall_csv_sha256": sha256_file(
            DATA_DIR / "manual_reference_candidate_recall.csv"
        ),
        "fixed_offset_csv_sha256": sha256_file(
            DATA_DIR / "fixed_offset_candidate_coverage.csv"
        ),
    }

    return {
        "schema": "PERSON_P1E_CANDIDATE_RECALL_SEMANTIC_INTERPRETATION_V2",
        "created_at": p0.now_iso(),
        "status": "SEMANTIC_SPLIT_COMPLETE_TEMPORAL_GATE_NOT_OPEN",
        "source_candidate_generation_rerun": False,
        "source_candidate_generation_preserved": True,
        "input_hash_checks": input_hash_checks,
        "hashes": hashes,
        "semantic_layers": {
            "candidate_existence_raw_peak_field": (
                "ANY_GT_BLIND_LOCAL_MAXIMUM_WITHIN_RADIUS; NOT AN OPERATIONAL SHORTLIST"
            ),
            "candidate_recall_shortlist": "RECALL_AT_PREDECLARED_K_AND_RADIUS",
            "unique_localization": (
                "REFERENCE_VS_LOCAL_COMPETING_RESPONSE_AND_TOP1_COMPETITION"
            ),
            "response_merging_suspected": (
                "A_GT_BLIND_PEAK_WITHIN_0_80M_OF_MULTIPLE_MANUAL_CENTERS; "
                "NOT_PHYSICAL_FUSION_PROOF"
            ),
            "peak_to_reference_center_offset": (
                "OPERATOR_HIGH_SCORE_LOCATION_MINUS_MANUAL_BOX_GEOMETRIC_CENTER; "
                "NOT_DIRECT_PHYSICAL_RESOLUTION_OR_SCATTERING_CENTER_ERROR"
            ),
            "local_competing_response_pool": (
                "NOT_GUARANTEED_PURE_BACKGROUND; TESTS WHETHER_REFERENCE_BEATS_"
                "LOCAL_STRONG_COMPETITORS"
            ),
        },
        "group_summaries": group_summaries,
        "candidate_count_summaries": candidate_count_summaries,
        "R02_C2_fixed_offset_recall_at_5_r_0_80m": offset_direction_recall5,
        "R02_C2_temporal_gate": original_summary["R02_C2_temporal_gate"],
        "R03_single_vs_temporal_mask_examples": r03_comparison,
        "decision": {
            "R02_is_single_failure_type": False,
            "P01_P02": (
                "NEARBY_RAW_PEAKS_OFTEN_EXIST_BUT_DO_NOT_ENTER_TOP5; "
                "P02_ALSO_HAS_TWO_RADIUS_LEVEL_MISSES"
            ),
            "P03_P04": (
                "TOP5_CANDIDATE_DISCOVERY_PRESENT_IN_8_OF_9_FRAMES_PER_TARGET; "
                "SHARED_RESPONSE_AND_UNIQUENESS_AMBIGUITY"
            ),
            "minimal_temporal_experiment_run": False,
            "reason": "PREDECLARED_R02_C2_TEMPORAL_ENTRY_GATE_FAILED",
            "P1_PASS_claimed": False,
            "blind_validation_claimed": False,
            "P0_retuned": False,
            "existing_P1E_outputs_modified": False,
            "SAR_boxes_created_or_moved": 0,
        },
    }


def summary_lookup(
    summary: dict[str, Any],
    candidate_name: str,
    group: str,
    run_id: str | None = None,
    target_id: str | None = None,
) -> dict[str, Any]:
    for row in summary["group_summaries"]:
        if row["candidate"] != candidate_name or row["group"] != group:
            continue
        if run_id is not None and row.get("run_id") != run_id:
            continue
        if target_id is not None and row.get("target_id") != target_id:
            continue
        return row
    raise KeyError((candidate_name, group, run_id, target_id))


def candidate_style(rank: int) -> tuple[str, float]:
    palette = ["#ffe600", "#00e5ff", "#ff4fd8", "#72ff72", "#ff8c42"]
    if rank <= 5:
        return palette[rank - 1], 2.0
    return "#f5f5f5", 1.2


def add_text_with_stroke(axis: plt.Axes, x: float, y: float, text_value: str, color: str) -> None:
    artist = axis.text(x, y, text_value, color=color, fontsize=8, weight="bold")
    artist.set_path_effects(
        [path_effects.withStroke(linewidth=2.2, foreground="#111111")]
    )


def reference_coverage_counts(
    candidate_rows: list[dict[str, Any]],
    reference_xy: np.ndarray,
    px_per_m: float,
) -> dict[int, int]:
    counts: dict[int, int] = {}
    for row in candidate_rows:
        point = np.array([float(row["x_px"]), float(row["y_px"])])
        distances = np.linalg.norm(reference_xy - point[None, :], axis=1) / px_per_m
        counts[int(row["rank"])] = int(np.sum(distances <= RADIUS_M + 1e-9))
    return counts


def draw_references(
    axis: plt.Axes,
    annotations: list[dict[str, Any]],
    selected_target: str,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> None:
    for annotation in annotations:
        selected = annotation["instance_id"] == selected_target
        color = "#ff2d2d" if selected else "#30f3ff"
        center_x = float(annotation["cx"]) - x_offset
        center_y = float(annotation["cy"]) - y_offset
        axis.scatter(
            [center_x],
            [center_y],
            marker="x",
            c=color,
            s=100 if selected else 70,
            linewidths=2.2,
            zorder=10,
        )
        rectangle = Rectangle(
            (
                center_x - float(annotation["width"]) / 2.0,
                center_y - float(annotation["height"]) / 2.0,
            ),
            float(annotation["width"]),
            float(annotation["height"]),
            fill=False,
            edgecolor=color,
            linewidth=1.4 if selected else 0.9,
            alpha=0.95,
            zorder=9,
        )
        axis.add_patch(rectangle)
        add_text_with_stroke(
            axis,
            center_x + 4,
            center_y - 5,
            target_short(annotation["instance_id"]),
            color,
        )


def select_local_candidate_rows(
    candidate_rows: list[dict[str, Any]],
    selected_reference: np.ndarray,
    reference_xy: np.ndarray,
    px_per_m: float,
    bounds: tuple[int, int, int, int],
) -> list[dict[str, Any]]:
    x0, x1, y0, y1 = bounds
    enriched: list[tuple[dict[str, Any], float, int]] = []
    coverage = reference_coverage_counts(candidate_rows, reference_xy, px_per_m)
    for row in candidate_rows:
        x = float(row["x_px"])
        y = float(row["y_px"])
        if not (x0 <= x < x1 and y0 <= y < y1):
            continue
        distance_m = float(np.linalg.norm(np.array([x, y]) - selected_reference) / px_per_m)
        rank = int(row["rank"])
        if rank <= 5 or distance_m <= 1.40 or coverage.get(rank, 0) > 1:
            enriched.append((row, distance_m, coverage.get(rank, 0)))
    if len(enriched) <= 26:
        return [item[0] for item in sorted(enriched, key=lambda item: int(item[0]["rank"]))]

    keep: dict[int, dict[str, Any]] = {}
    for row, distance_m, shared_count in enriched:
        rank = int(row["rank"])
        if rank <= 5 or shared_count > 1:
            keep[rank] = row
    for row, _, _ in sorted(enriched, key=lambda item: item[1])[:12]:
        keep[int(row["rank"])] = row
    return [keep[rank] for rank in sorted(keep)[:26]]


def draw_candidates(
    axis: plt.Axes,
    rows: list[dict[str, Any]],
    selected_reference: np.ndarray,
    reference_xy: np.ndarray,
    px_per_m: float,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> None:
    coverage = reference_coverage_counts(rows, reference_xy, px_per_m)
    if rows:
        nearest_rank = min(
            rows,
            key=lambda row: np.linalg.norm(
                np.array([float(row["x_px"]), float(row["y_px"])])
                - selected_reference
            ),
        )["rank"]
    else:
        nearest_rank = None
    for row in rows:
        rank = int(row["rank"])
        x = float(row["x_px"]) - x_offset
        y = float(row["y_px"]) - y_offset
        color, linewidth = candidate_style(rank)
        axis.scatter(
            [x],
            [y],
            s=80 if rank <= 5 else 62,
            facecolors="none",
            edgecolors=color,
            linewidths=linewidth,
            zorder=12,
        )
        if coverage.get(rank, 0) > 1:
            axis.scatter(
                [x],
                [y],
                s=145,
                marker="s",
                facecolors="none",
                edgecolors="#42ff8b",
                linewidths=1.5,
                zorder=11,
            )
        if nearest_rank is not None and int(nearest_rank) == rank:
            axis.scatter(
                [x],
                [y],
                s=180,
                marker="*",
                facecolors="none",
                edgecolors="#ffffff",
                linewidths=1.3,
                zorder=13,
            )
        add_text_with_stroke(axis, x + 4, y - 4, str(rank), color)


def draw_fixed_offsets(
    axis: plt.Axes,
    offsets: dict[str, np.ndarray],
    x_offset: float,
    y_offset: float,
) -> None:
    abbreviations = {
        "RADIAL_IN": "RI",
        "RADIAL_OUT": "RO",
        "TANGENTIAL_NEG": "T-",
        "TANGENTIAL_POS": "T+",
    }
    for direction, point in offsets.items():
        x = float(point[0]) - x_offset
        y = float(point[1]) - y_offset
        axis.scatter(
            [x], [y], marker="+", c="#d7a5ff", s=70, linewidths=1.5, zorder=8
        )
        add_text_with_stroke(axis, x + 3, y + 9, abbreviations[direction], "#d7a5ff")


def metric_title(rows: pd.DataFrame, candidate_name: str) -> str:
    row = rows[rows["candidate"] == candidate_name].iloc[0]
    rank_text = (
        str(int(row["nearest_candidate_rank"]))
        if np.isfinite(row["nearest_candidate_rank"])
        else "NA"
    )
    shared = "yes" if bool(row["response_merging_suspected_any_rank"]) else "no"
    top5 = "yes" if bool(row["recall_at_5_r_80cm"]) else "no"
    return (
        f"{candidate_name[:2]} local | nearest r{rank_text}, "
        f"d={number(row['nearest_candidate_distance_m'])}m | Top5={top5}, shared={shared}"
    )


def plot_case(
    audit: Any,
    p0: Any,
    p1e: Any,
    frame: dict[str, Any],
    selected_annotation: dict[str, Any],
    interpretation_rows: pd.DataFrame,
    candidates: pd.DataFrame,
    output_path: Path,
    case_note: str,
) -> None:
    image_path = p0.file_url_to_path(frame["sar_image_url"])
    image_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise FileNotFoundError(image_path)
    mask, radial, theta, px_per_m = audit.single_frame_observation_mask(frame, image_bgr)
    maps, _ = audit.compute_existing_candidate_maps_for_mask(
        p1e, frame, image_bgr, mask, radial, theta, px_per_m
    )
    support_radius_px = max(
        1, int(round(p1e.PHYSICAL_SUPPORT_RADIUS_M * px_per_m))
    )
    evaluation_maps = p1e.build_evaluation_maps(
        maps, mask, support_radius_px, "fixed_support_mean_v2"
    )
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    manual_annotations = [
        annotation
        for annotation in frame["annotations"]
        if annotation["source"] == "MANUAL_NATIVE_SAR"
    ]
    selected_reference = np.array(
        [float(selected_annotation["cx"]), float(selected_annotation["cy"])]
    )
    reference_xy = np.array(
        [[float(row["cx"]), float(row["cy"])] for row in manual_annotations],
        dtype=float,
    )
    crop_radius = int(round(2.35 * px_per_m))
    x0 = max(0, int(round(selected_reference[0])) - crop_radius)
    x1 = min(image_rgb.shape[1], int(round(selected_reference[0])) + crop_radius + 1)
    y0 = max(0, int(round(selected_reference[1])) - crop_radius)
    y1 = min(image_rgb.shape[0], int(round(selected_reference[1])) + crop_radius + 1)
    bounds = (x0, x1, y0, y1)
    offsets = audit.fixed_offset_points(
        p1e, selected_reference, frame["geometry"], px_per_m
    )

    candidate_rows: dict[str, list[dict[str, Any]]] = {}
    for candidate_name in AUDIT_CANDIDATES:
        subset = candidates[
            (candidates["frame_uid"] == frame["sar_frame_uid"])
            & (candidates["candidate"] == candidate_name)
        ].sort_values("rank")
        candidate_rows[candidate_name] = subset.to_dict("records")

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    plt.subplots_adjust(left=0.025, right=0.99, bottom=0.075, top=0.88, wspace=0.05, hspace=0.13)

    axes[0, 0].imshow(image_rgb)
    draw_references(axes[0, 0], manual_annotations, selected_annotation["instance_id"])
    draw_candidates(
        axes[0, 0],
        candidate_rows[PRIMARY][:5],
        selected_reference,
        reference_xy,
        px_per_m,
    )
    axes[0, 0].set_title("Raw SAR full frame | C2 Top-5", fontsize=10)
    axes[0, 0].axis("off")

    for column, candidate_name in enumerate(AUDIT_CANDIDATES, start=1):
        score = evaluation_maps[candidate_name].copy()
        score[~mask] = np.nan
        axes[0, column].imshow(score, cmap="magma", vmin=0.0, vmax=1.0)
        draw_references(
            axes[0, column], manual_annotations, selected_annotation["instance_id"]
        )
        draw_candidates(
            axes[0, column],
            candidate_rows[candidate_name][:5],
            selected_reference,
            reference_xy,
            px_per_m,
        )
        axes[0, column].set_title(
            f"{candidate_name[:2]} global S(x) | GT-blind Top-5", fontsize=10
        )
        axes[0, column].axis("off")

    axes[1, 0].imshow(image_rgb[y0:y1, x0:x1])
    draw_references(
        axes[1, 0],
        manual_annotations,
        selected_annotation["instance_id"],
        x_offset=x0,
        y_offset=y0,
    )
    local_c2 = select_local_candidate_rows(
        candidate_rows[PRIMARY], selected_reference, reference_xy, px_per_m, bounds
    )
    draw_candidates(
        axes[1, 0],
        local_c2,
        selected_reference,
        reference_xy,
        px_per_m,
        x_offset=x0,
        y_offset=y0,
    )
    draw_fixed_offsets(axes[1, 0], offsets, x0, y0)
    axes[1, 0].add_patch(
        Circle(
            (selected_reference[0] - x0, selected_reference[1] - y0),
            RADIUS_M * px_per_m,
            fill=False,
            edgecolor="#ff4040",
            linestyle="--",
            linewidth=1.2,
        )
    )
    axes[1, 0].set_xlim(0, x1 - x0)
    axes[1, 0].set_ylim(y1 - y0, 0)
    axes[1, 0].set_title("Raw local | red circle = 0.8 m; purple = fixed offsets", fontsize=10)
    axes[1, 0].axis("off")

    for column, candidate_name in enumerate(AUDIT_CANDIDATES, start=1):
        local_map = evaluation_maps[candidate_name][y0:y1, x0:x1].copy()
        local_mask = mask[y0:y1, x0:x1]
        local_map[~local_mask] = np.nan
        axes[1, column].imshow(local_map, cmap="magma", vmin=0.0, vmax=1.0)
        draw_references(
            axes[1, column],
            manual_annotations,
            selected_annotation["instance_id"],
            x_offset=x0,
            y_offset=y0,
        )
        local_rows = select_local_candidate_rows(
            candidate_rows[candidate_name],
            selected_reference,
            reference_xy,
            px_per_m,
            bounds,
        )
        draw_candidates(
            axes[1, column],
            local_rows,
            selected_reference,
            reference_xy,
            px_per_m,
            x_offset=x0,
            y_offset=y0,
        )
        axes[1, column].add_patch(
            Circle(
                (selected_reference[0] - x0, selected_reference[1] - y0),
                RADIUS_M * px_per_m,
                fill=False,
                edgecolor="#ff4040",
                linestyle="--",
                linewidth=1.2,
            )
        )
        axes[1, column].set_xlim(0, x1 - x0)
        axes[1, column].set_ylim(y1 - y0, 0)
        axes[1, column].set_title(metric_title(interpretation_rows, candidate_name), fontsize=9)
        axes[1, column].axis("off")

    fig.suptitle(
        f"{frame['run_id']} F{int(frame['sar_frame_index'])} {target_short(selected_annotation['instance_id'])} | {case_note}",
        fontsize=13,
        weight="bold",
    )
    fig.text(
        0.5,
        0.025,
        "Candidate coordinates/ranks come from the frozen GT-blind CSV. Red X/box = selected offline reference; cyan = other references; green square = candidate shared by multiple references; white star = nearest shown candidate.",
        ha="center",
        fontsize=9,
        color="#333333",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160, facecolor="white")
    plt.close(fig)


def plot_recall_summary(summary: dict[str, Any], output_path: Path) -> None:
    run_rows = [
        summary_lookup(summary, PRIMARY, "RUN", run_id=run_id) for run_id in RUNS
    ]
    target_ids = [f"R02ZF_SARPERSON{index:02d}" for index in range(1, 5)]
    target_rows = [
        summary_lookup(summary, PRIMARY, "R02_TARGET", target_id=target_id)
        for target_id in target_ids
    ]
    k_values = (1, 3, 5)
    colors = ["#3659a2", "#e07a2f", "#2e9a62"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    x_run = np.arange(len(RUNS))
    width = 0.23
    for offset_index, k_value in enumerate(k_values):
        values = [row[f"recall_at_{k_value}_r_80cm"] for row in run_rows]
        bars = axes[0].bar(
            x_run + (offset_index - 1) * width,
            values,
            width,
            label=f"Recall@{k_value}",
            color=colors[offset_index],
        )
        axes[0].bar_label(bars, labels=[pct(value, 0) for value in values], fontsize=8)
    axes[0].set_xticks(x_run, RUNS)
    axes[0].set_ylim(0, 1.08)
    axes[0].set_ylabel("Recall within 0.8 m")
    axes[0].set_title("C2 by development run")
    axes[0].grid(axis="y", alpha=0.2)
    axes[0].legend(loc="lower left")

    x_target = np.arange(len(target_ids))
    for offset_index, k_value in enumerate(k_values):
        values = [row[f"recall_at_{k_value}_r_80cm"] for row in target_rows]
        bars = axes[1].bar(
            x_target + (offset_index - 1) * width,
            values,
            width,
            label=f"Recall@{k_value}",
            color=colors[offset_index],
        )
        axes[1].bar_label(bars, labels=[pct(value, 0) for value in values], fontsize=8)
    axes[1].set_xticks(x_target, ["P01", "P02", "P03", "P04"])
    axes[1].set_ylim(0, 1.08)
    axes[1].set_ylabel("Recall within 0.8 m")
    axes[1].set_title("C2 within R02")
    axes[1].grid(axis="y", alpha=0.2)
    axes[1].legend(loc="lower left")

    fig.suptitle("GT-blind shortlist recall: candidate existence is not the same as unique localization")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=170, facecolor="white")
    plt.close(fig)


def html_table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{html.escape(str(value))}</th>" for value in headers)
    body = []
    for row in rows:
        body.append(
            "<tr>"
            + "".join(f"<td>{html.escape(str(value))}</td>" for value in row)
            + "</tr>"
        )
    return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(str(value) for value in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def build_report_tables(summary: dict[str, Any]) -> dict[str, list[list[Any]]]:
    run_rows: list[list[Any]] = []
    for run_id in RUNS:
        row = summary_lookup(summary, PRIMARY, "RUN", run_id=run_id)
        run_rows.append(
            [
                run_id,
                row["reference_count"],
                pct(row["recall_at_1_r_80cm"]),
                pct(row["recall_at_3_r_80cm"]),
                pct(row["recall_at_5_r_80cm"]),
                pct(row["candidate_within_0_80m_rate_any_rank"]),
                number(row["median_nearest_candidate_rank"], 1),
                pct(row["response_merging_suspected_any_rank_rate"]),
            ]
        )

    r02_target_rows: list[list[Any]] = []
    for index in range(1, 5):
        target_id = f"R02ZF_SARPERSON{index:02d}"
        row = summary_lookup(summary, PRIMARY, "R02_TARGET", target_id=target_id)
        counts = row["candidate_presence_class_counts_v2"]
        r02_target_rows.append(
            [
                f"P{index:02d}",
                row["reference_count"],
                pct(row["recall_at_1_r_80cm"]),
                pct(row["recall_at_3_r_80cm"]),
                pct(row["recall_at_5_r_80cm"]),
                pct(row["candidate_within_0_80m_rate_any_rank"]),
                number(row["median_nearest_candidate_rank"], 1),
                counts.get("CANDIDATE_MISSING_OR_CURRENT_REPRESENTATION_FAILURE", 0),
                pct(row["response_merging_suspected_any_rank_rate"]),
                pct(row["shared_best_candidate_rate_any_rank"]),
            ]
        )

    c3_rows: list[list[Any]] = []
    for index in range(1, 5):
        target_id = f"R02ZF_SARPERSON{index:02d}"
        row = summary_lookup(summary, DIAGNOSTIC, "R02_TARGET", target_id=target_id)
        c3_rows.append(
            [
                f"P{index:02d}",
                pct(row["recall_at_1_r_80cm"]),
                pct(row["recall_at_5_r_80cm"]),
                pct(row["candidate_within_0_80m_rate_any_rank"]),
                number(row["median_nearest_candidate_rank"], 1),
            ]
        )

    count_rows: list[list[Any]] = []
    for row in summary["candidate_count_summaries"]:
        count_rows.append(
            [
                row["run_id"],
                row["candidate"][:2],
                row["frame_count"],
                f"{row['candidate_count_min']} / {number(row['candidate_count_median'], 0)} / {row['candidate_count_max']}",
                f"{number(row['candidate_min_spacing_m_min'], 3)} / {number(row['candidate_min_spacing_m_median'], 3)}",
            ]
        )

    r03_rows: list[list[Any]] = []
    for row in summary["R03_single_vs_temporal_mask_examples"]:
        r03_rows.append(
            [
                int(row["frame_index"]),
                row["evaluation_status"],
                row["reference_support_status"],
                number(row["nearest_candidate_distance_m"], 3),
                number(row["nearest_candidate_rank"], 0),
                "yes" if bool(row["recall_at_5_r_80cm"]) else "no",
            ]
        )
    return {
        "run": run_rows,
        "r02_target": r02_target_rows,
        "c3": c3_rows,
        "count": count_rows,
        "r03": r03_rows,
    }


def write_reports(
    summary: dict[str, Any],
    case_registry: list[dict[str, Any]],
    recall_figure: Path,
) -> None:
    tables = build_report_tables(summary)
    gate = summary["R02_C2_temporal_gate"]
    r02 = summary_lookup(summary, PRIMARY, "RUN", run_id="R02ZF")
    p01 = summary_lookup(
        summary, PRIMARY, "R02_TARGET", target_id="R02ZF_SARPERSON01"
    )
    p02 = summary_lookup(
        summary, PRIMARY, "R02_TARGET", target_id="R02ZF_SARPERSON02"
    )
    p03 = summary_lookup(
        summary, PRIMARY, "R02_TARGET", target_id="R02ZF_SARPERSON03"
    )
    p04 = summary_lookup(
        summary, PRIMARY, "R02_TARGET", target_id="R02ZF_SARPERSON04"
    )

    run_headers = [
        "run",
        "references",
        "R@1 0.8m",
        "R@3 0.8m",
        "R@5 0.8m",
        "any-rank peak <=0.8m",
        "median nearest rank",
        "merging suspected",
    ]
    target_headers = [
        "R02 target",
        "n",
        "R@1",
        "R@3",
        "R@5",
        "any-rank peak <=0.8m",
        "median rank",
        "radius misses",
        "any shared peak",
        "best peak shared",
    ]
    c3_headers = ["R02 target", "R@1", "R@5", "any-rank peak <=0.8m", "median rank"]
    count_headers = ["run", "operator", "frames", "candidate count min/median/max", "spacing min/median (m)"]
    r03_headers = ["frame", "old frozen-P0 P1E status", "Omega_single_v1", "nearest d (m)", "rank", "Top5"]

    case_html = []
    case_md = []
    for case in case_registry:
        image_url = relative_url(Path(case["path"]))
        caption = (
            f"{case['frame_uid']} / {target_short(case['target_id'])}: "
            f"C2 nearest rank {case['C2_nearest_rank']}, d={number(case['C2_nearest_distance_m'], 3)} m, "
            f"Top5={'yes' if case['C2_recall_at_5_r_80cm'] else 'no'}, "
            f"shared={'yes' if case['C2_response_merging_suspected_any_rank'] else 'no'}. "
            f"{case['note']}"
        )
        case_html.append(
            f"<figure><img src='{html.escape(image_url)}' alt='{html.escape(caption)}'><figcaption>{html.escape(caption)}</figcaption></figure>"
        )
        case_md.append(f"![{caption}]({image_url})\n\n{caption}")

    gate_rows = [
        ["R02 C2 Recall@5(0.8m) >= 60%", pct(gate["recall_at_5_r_0_80m"]), "pass" if gate["checks"]["R02_C2_recall5_0_80m_at_least_0_60"] else "fail"],
        ["Top5 - Top1 >= 20 percentage points", pct(gate["top5_minus_top1"]), "pass" if gate["checks"]["R02_C2_top5_minus_top1_at_least_0_20"] else "fail"],
        ["reference - fixed-offset median >= 10 points", pct(gate["reference_minus_offset_median"]), "pass" if gate["checks"]["R02_C2_reference_minus_offset_median_at_least_0_10"] else "fail"],
        ["P01 or P02 Recall@5 >= 50%", f"P01={pct(gate['R02_target_recall_at_5_r_0_80m']['R02ZF_SARPERSON01'])}, P02={pct(gate['R02_target_recall_at_5_r_0_80m']['R02ZF_SARPERSON02'])}", "pass" if gate["checks"]["R02_P01_or_P02_recall5_at_least_0_50"] else "fail"],
    ]

    css = """
    :root { --ink:#172033; --muted:#5d687a; --line:#d9dfeb; --blue:#315a9b; --green:#19714c; --red:#a53535; --paper:#fff; --wash:#f4f7fb; }
    * { box-sizing:border-box; } body { margin:0; color:var(--ink); background:var(--wash); font-family:"Segoe UI","Microsoft YaHei",Arial,sans-serif; line-height:1.65; }
    main { max-width:1500px; margin:0 auto; background:var(--paper); padding:34px 46px 72px; box-shadow:0 0 40px rgba(24,38,64,.08); }
    h1 { font-size:30px; margin:0 0 8px; } h2 { margin-top:38px; padding-top:18px; border-top:1px solid var(--line); font-size:23px; } h3 { margin-top:25px; font-size:18px; }
    p, li { max-width:1100px; } .lede { font-size:18px; } .meta { color:var(--muted); font-size:14px; }
    .verdict { border-left:6px solid var(--blue); background:#edf4ff; padding:18px 22px; margin:22px 0; }
    .stop { border-left-color:var(--red); background:#fff0f0; } .good { border-left-color:var(--green); background:#edf9f3; }
    code { background:#eef1f6; padding:2px 5px; border-radius:4px; } a { color:#174f9f; }
    .table-wrap { overflow:auto; margin:14px 0 22px; } table { border-collapse:collapse; min-width:760px; font-size:14px; } th,td { border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; } th { background:#edf2f8; white-space:nowrap; }
    figure { margin:24px 0 38px; } figure img { width:100%; height:auto; border:1px solid var(--line); background:white; } figcaption { color:var(--muted); font-size:14px; margin-top:8px; }
    .small { font-size:13px; color:var(--muted); } .links li { margin:6px 0; }
    @media (max-width:800px) { main { padding:22px 18px 50px; } h1 { font-size:25px; } }
    """

    html_text = f"""<!doctype html>
<html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>PERSON P1E 候选召回语义拆分</title><style>{css}</style></head>
<body><main>
<h1>PERSON P1E：候选存在性与单帧唯一定位性语义拆分</h1>
<p class='meta'>版本：candidate_recall_semantic_split_v1 · 数据角色：R01/R02/R03/R04 均为已暴露开发语料 · 不授予 P1_PASS · 未运行时序</p>
<div class='verdict'>
<strong>本轮结论：</strong>R02 不是单一的“PERSON 响应不存在”，也不是整体的“Top-5 候选召回已经成立”。P03/P04 属于候选已进入高响应短名单但共享响应/唯一性不足；P01/P02 多数帧存在参考附近的低 rank 局部峰，却 0/9 进入 Top-5，P02 还有 2/9 个 0.8 m 半径级缺失。预注册时序入口门槛未通过，因此本轮不运行 lag1/lag3 时序。
</div>

<h2>1. 先把三层问题分开</h2>
<ol>
<li><strong>原始峰存在：</strong>整幅 S(x) 经 GT-blind 局部极大值与 NMS 后，参考位置 0.8 m 内是否有任意候选峰。这说明算子附近有峰，但不等于它进入可用短名单。</li>
<li><strong>候选短名单召回：</strong>固定 K=1/2/3/5 后的 Recall@K(r)。这是本轮决定是否值得做最小时序消歧的核心。</li>
<li><strong>单帧唯一定位：</strong>参考能否击败局部最强竞争响应、是否为 Top-1、以及同一峰是否覆盖多个参考中心。原 hard-background 应解释为 <em>local competing-response pool</em>，不保证是纯背景。</li>
</ol>
<p>原 <code>peak_to_reference_center_offset</code> 只表示 S(x) 的局部高分位置相对人工框几何中心的偏移；它不能直接当作物理空间分辨率、真实散射中心误差或融合机制的因果证明。</p>

<h2>2. R02 的直接答案</h2>
<p class='lede'>C2 的 R02 Recall@1/3/5(0.8 m) 为 <strong>{pct(r02['recall_at_1_r_80cm'])} / {pct(r02['recall_at_3_r_80cm'])} / {pct(r02['recall_at_5_r_80cm'])}</strong>。Top-1 到 Top-5 只恢复 {pct(gate['top5_minus_top1'])}，而且 Top-3 到 Top-5 没有继续恢复。</p>
{html_table(target_headers, tables['r02_target'])}
<ul>
<li><strong>P01：</strong>9/9 帧在 0.8 m 内有某个 C2 峰，但最近峰 rank 中位数 {number(p01['median_nearest_candidate_rank'],1)}，Top-5 为 0/9。</li>
<li><strong>P02：</strong>7/9 帧在 0.8 m 内有峰，最近 rank 中位数 {number(p02['median_nearest_candidate_rank'],1)}；另 2/9 是半径级候选缺失/当前表示未捕捉。</li>
<li><strong>P03/P04：</strong>各 8/9 进入 Top-5、5/9 为 Top-1，但 9/9 均有候选同时落入多个 reference 的 0.8 m 邻域，故位置唯一性不足。</li>
</ul>
<div class='verdict good'>更准确的说法是：P01/P02 的“原始局部峰存在性”多数成立，但“高响应 Top-5 短名单召回”不成立；P03/P04 的短名单召回成立，但主要落在共享/融合响应上。<code>response_merging_suspected</code> 只是图像域重叠诊断，不是物理融合证明。</div>
<figure><img src='{html.escape(relative_url(recall_figure))}' alt='C2 Recall at K summary'><figcaption>固定 K 与 0.8 m 半径的 GT-blind 候选召回。所有候选先于 GT 评价生成。</figcaption></figure>

<h2>3. 跨 run 与候选池规模</h2>
{html_table(run_headers, tables['run'])}
<p>完整逐帧候选数已保存在 CSV。C2 每帧通常有数百个局部极大值，因此“0.8 m 内有任意峰”与“进入全扇面 Top-5”是不同强度的结论。</p>
{html_table(count_headers, tables['count'])}

<h2>4. C3 诊断没有修复 P01/P02</h2>
{html_table(c3_headers, tables['c3'])}
<p>C3 在 P01/P02 的 Recall@5 仍为 0，最近 rank 中位数约 121/99。它没有把两者提升到高响应短名单，因此本轮不把 C3 解释为修复。</p>

<h2>5. Omega_single 与 Omega_temporal 必须分开</h2>
<p><code>Omega_single_v1</code> 只要求真实扇面内仍有单帧观测且固定支持核有效；<code>Omega_temporal</code> 还要求冻结 P0 公共输运和局部误差预算可用。后者是前者子集，P0 不可比较不等于单帧不可观察。</p>
{html_table(r03_headers, tables['r03'])}
<p>F458 是最直接反例：旧 frozen-P0-mask P1E 因低有效支持而弃权，新单帧域为 FULL，C2 在约 0.02 m 处确有峰，但 rank=18。它证明语义拆分必要，却不证明 Top-5 候选召回足够。</p>

<h2>6. 预注册时序入口：未打开</h2>
{html_table(["frozen check", "observed", "result"], gate_rows)}
<div class='verdict stop'><strong>停止决定：</strong>四项门槛中三项失败。按照运行前冻结规则，不执行 lag1，也不追加 lag3。因而本轮不能回答“P0 输运是否改善 rank”，更不能声称时序提供了新增信息；这些问题保持未检验，而不是阴性结果。</div>

<h2>7. 真实病例：原图、全局响应、局部响应与 GT-blind 候选</h2>
<p class='small'>病例图是结果后的解释性选择，只用于展示成功/失败结构，不参与候选生成、阈值选择或时序入口判定。局部图只画实际落入裁剪区且属于 Top-5、靠近参考或被多个参考共享的候选；不会再把裁剪区外 marker 标签画进局部图。</p>
{''.join(case_html)}

<h2>8. 研究边界与可复核文件</h2>
<ul class='links'>
<li><a href='00_CANDIDATE_RECALL_PROTOCOL_FROZEN_BEFORE_RUN.md'>运行前冻结协议</a></li>
<li><a href='{html.escape(relative_url(DATA_DIR / 'manual_reference_candidate_recall.csv'))}'>原始逐 reference Recall@K CSV（不修改）</a></li>
<li><a href='{html.escape(relative_url(INTERPRETATION_CSV))}'>语义解释 v2 CSV（新增 any-rank 共享候选层）</a></li>
<li><a href='{html.escape(relative_url(DATA_DIR / 'gt_blind_candidates_all_processed_frames.csv'))}'>全部 GT-blind 候选 CSV</a></li>
<li><a href='{html.escape(relative_url(DATA_DIR / 'candidate_count_by_frame.csv'))}'>逐帧候选数 CSV</a></li>
<li><a href='{html.escape(relative_url(DATA_DIR / 'fixed_offset_candidate_coverage.csv'))}'>固定空间偏移覆盖 CSV</a></li>
<li><a href='{html.escape(relative_url(SUMMARY_JSON))}'>机器可读语义总结 JSON</a></li>
<li><a href='{html.escape(relative_url(VALIDATION_JSON))}'>报告链接与图片校验 JSON</a></li>
</ul>
<p class='small'>冻结 P0 未重拟合；B0R 与旧 P1E 结果未删除或覆盖；C0-C3 未修改；真实框、ID、光学/插值轨迹未用于候选生成或时序边；本轮未创建/移动 SAR 框，未授予 P1_PASS，四个 run 仍为开发语料。</p>
</main></body></html>"""
    REPORT_HTML.write_text(html_text, encoding="utf-8")

    case_md_text = "\n\n".join(case_md)
    md_text = f"""# PERSON P1E 候选存在性—唯一定位性语义拆分

> 状态：`SEMANTIC_SPLIT_COMPLETE_TEMPORAL_GATE_NOT_OPEN`  
> 数据角色：R01/R02/R03/R04 均为已暴露开发语料；不授予 P1_PASS；本轮未运行时序。

## 结论

R02 不是单一的“PERSON 响应不存在”，也不是整体的“Top-5 候选召回已经成立”。

- P01：9/9 帧在 0.8 m 内存在 C2 局部峰，但最近 rank 中位数 {number(p01['median_nearest_candidate_rank'],1)}，Top-5 为 0/9。
- P02：7/9 帧在 0.8 m 内存在峰，Top-5 为 0/9；另 2/9 为半径级候选缺失/当前表示未捕捉。
- P03/P04：各 8/9 进入 Top-5、5/9 为 Top-1，但九帧均出现同一 GT-blind 候选落入多个 reference 的 0.8 m 邻域。
- R02 总体 Recall@1/3/5(0.8 m) = {pct(r02['recall_at_1_r_80cm'])} / {pct(r02['recall_at_3_r_80cm'])} / {pct(r02['recall_at_5_r_80cm'])}；Top-5 相对 Top-1 仅恢复 {pct(gate['top5_minus_top1'])}。

因此，P01/P02 多数属于“参考附近有低 rank 原始峰，但没有进入高响应 Top-5 短名单”，P02 还混有 2 个候选缺失；P03/P04 属于“候选召回成立，但共享响应与唯一性不足”。`response_merging_suspected` 仅为图像域诊断，不是物理融合证明。

## 三层评价

1. 原始峰存在：任意 GT-blind 局部峰是否在 reference 的固定半径内。
2. 候选短名单召回：固定 K=1/2/3/5 的 Recall@K(r)。
3. 单帧唯一定位：reference 能否击败局部强竞争响应、是否 Top-1、是否与其他 reference 共享候选。

原 hard-background 应改释为 `local competing-response pool`。`peak_to_reference_center_offset` 只表示算子高分位置相对人工框几何中心的偏移，不直接等于物理分辨率或真实散射中心误差。

## R02 分目标

{markdown_table(target_headers, tables['r02_target'])}

## 跨 run

{markdown_table(run_headers, tables['run'])}

## 候选池规模

{markdown_table(count_headers, tables['count'])}

## C3 诊断

{markdown_table(c3_headers, tables['c3'])}

C3 对 P01/P02 的 Recall@5 仍为 0，最近 rank 中位数约 121/99，没有形成修复。

## 单帧域与时序域

{markdown_table(r03_headers, tables['r03'])}

F458 在 `Omega_single_v1` 中为 FULL，且约 0.02 m 处有 C2 峰，但 rank=18。它证明“P0 不可比较不等于单帧不可观察”，不证明 Top-5 召回足够。

## 时序入口

{markdown_table(["frozen check", "observed", "result"], gate_rows)}

预注册门槛三项失败，因此本轮不运行 lag1/lag3。P0 输运能否改善候选 rank、是否提供新增信息，当前仍是未检验问题，不是阴性结论。

## 病例图

{case_md_text}

## 文件

- [HTML 报告]({REPORT_HTML.name})
- [运行前冻结协议](00_CANDIDATE_RECALL_PROTOCOL_FROZEN_BEFORE_RUN.md)
- [原始 Recall@K CSV]({relative_url(DATA_DIR / 'manual_reference_candidate_recall.csv')})
- [语义解释 v2 CSV]({relative_url(INTERPRETATION_CSV)})
- [全部 GT-blind 候选]({relative_url(DATA_DIR / 'gt_blind_candidates_all_processed_frames.csv')})
- [机器可读总结]({relative_url(SUMMARY_JSON)})
- [报告校验]({relative_url(VALIDATION_JSON)})

冻结 P0、B0R、C0-C3 与旧 P1E 结果均未修改；本轮不授予 P1_PASS，不声称盲验证。
"""
    REPORT_MD.write_text(md_text, encoding="utf-8")


def validate_report(case_paths: list[Path]) -> dict[str, Any]:
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
    unreadable_images = [
        str(path)
        for path in case_paths
        if cv2.imread(str(path), cv2.IMREAD_COLOR) is None
    ]
    return {
        "schema": "PERSON_P1E_CANDIDATE_RECALL_REPORT_VALIDATION_V1",
        "html_path": str(REPORT_HTML),
        "html_local_reference_count": int(len(local_references)),
        "missing_local_references": missing,
        "case_image_count": int(len(case_paths)),
        "unreadable_case_images": unreadable_images,
        "status": "PASS" if not missing and not unreadable_images else "FAIL",
    }


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(SCRIPT_PATH).lower() or "old_work" in str(REPORT_ROOT).lower():
        raise RuntimeError("forbidden old_work dependency")
    if not (REPORT_ROOT / "00_CANDIDATE_RECALL_PROTOCOL_FROZEN_BEFORE_RUN.md").is_file():
        raise RuntimeError("missing frozen pre-run protocol")
    required_inputs = (
        DATA_DIR / "manual_reference_candidate_recall.csv",
        DATA_DIR / "gt_blind_candidates_all_processed_frames.csv",
        DATA_DIR / "candidate_count_by_frame.csv",
        DATA_DIR / "fixed_offset_candidate_coverage.csv",
        DATA_DIR / "candidate_recall_summary.json",
    )
    missing_inputs = [str(path) for path in required_inputs if not path.is_file()]
    if missing_inputs:
        raise FileNotFoundError(missing_inputs)

    audit = load_module("person_candidate_audit_report_source", AUDIT_SCRIPT)
    p0 = load_module("person_p0_candidate_report", P0_SCRIPT)
    p1e = load_module("person_p1e_candidate_report", P1E_SCRIPT)
    p0.assert_workspace_scope()
    _, input_hash_checks = p0.load_contract_and_verify()

    if sha256_file(P0_SCRIPT) != EXPECTED_P0_SHA256:
        raise RuntimeError("frozen P0 hash mismatch")
    if sha256_file(P1E_SCRIPT) != EXPECTED_P1E_SHA256:
        raise RuntimeError("existing C0-C3 P1E hash mismatch")
    if sha256_file(TASK_DIR / "run_b0r_minimal_applicability.py") != EXPECTED_B0R_SCRIPT_SHA256:
        raise RuntimeError("B0R script hash mismatch")

    explorer = audit.load_explorer()
    frame_map = {frame["sar_frame_uid"]: frame for frame in explorer["frames"]}
    references = pd.read_csv(DATA_DIR / "manual_reference_candidate_recall.csv")
    candidates = pd.read_csv(DATA_DIR / "gt_blind_candidates_all_processed_frames.csv")
    frame_counts = pd.read_csv(DATA_DIR / "candidate_count_by_frame.csv")
    controls = pd.read_csv(DATA_DIR / "fixed_offset_candidate_coverage.csv")
    old_metrics = pd.read_csv(OLD_P1E_DIR / "p1e_single_frame_metrics_manual.csv")
    original_summary = json.loads(
        (DATA_DIR / "candidate_recall_summary.json").read_text(encoding="utf-8-sig")
    )

    if not candidates["generated_without_annotation"].astype(bool).all():
        raise RuntimeError("candidate provenance flag is not uniformly GT-blind")
    interpretation = add_any_rank_interpretation(references, candidates, frame_map)
    interpretation.to_csv(INTERPRETATION_CSV, index=False, encoding="utf-8-sig")

    summary = build_summary(
        p0,
        interpretation,
        frame_counts,
        controls,
        original_summary,
        old_metrics,
        input_hash_checks,
    )
    SUMMARY_JSON.write_text(
        json.dumps(json_safe(summary), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    VIS_DIR.mkdir(parents=True, exist_ok=True)
    recall_figure = VIS_DIR / "c2_recall_at_k_summary.png"
    plot_recall_summary(summary, recall_figure)

    case_registry: list[dict[str, Any]] = []
    case_paths: list[Path] = [recall_figure]
    for index, spec in enumerate(CASE_SPECS, start=1):
        frame = frame_map[spec["frame_uid"]]
        selected_annotation = next(
            annotation
            for annotation in frame["annotations"]
            if annotation["instance_id"] == spec["target_id"]
            and annotation["source"] == "MANUAL_NATIVE_SAR"
        )
        rows = interpretation[
            (interpretation["frame_uid"] == spec["frame_uid"])
            & (interpretation["target_id"] == spec["target_id"])
        ]
        output_path = VIS_DIR / f"case_v2_{index:02d}_{spec['slug']}.png"
        plot_case(
            audit,
            p0,
            p1e,
            frame,
            selected_annotation,
            rows,
            candidates,
            output_path,
            spec["note"],
        )
        c2_row = rows[rows["candidate"] == PRIMARY].iloc[0]
        c3_row = rows[rows["candidate"] == DIAGNOSTIC].iloc[0]
        case_registry.append(
            {
                "case_index": index,
                "frame_uid": spec["frame_uid"],
                "target_id": spec["target_id"],
                "note": spec["note"],
                "path": str(output_path),
                "C2_nearest_rank": int(c2_row["nearest_candidate_rank"]),
                "C2_nearest_distance_m": float(c2_row["nearest_candidate_distance_m"]),
                "C2_recall_at_5_r_80cm": bool(c2_row["recall_at_5_r_80cm"]),
                "C2_response_merging_suspected_any_rank": bool(
                    c2_row["response_merging_suspected_any_rank"]
                ),
                "C2_semantic_case_interpretation_v2": c2_row[
                    "semantic_case_interpretation_v2"
                ],
                "C3_nearest_rank": int(c3_row["nearest_candidate_rank"]),
                "C3_nearest_distance_m": float(c3_row["nearest_candidate_distance_m"]),
                "C3_recall_at_5_r_80cm": bool(c3_row["recall_at_5_r_80cm"]),
            }
        )
        case_paths.append(output_path)

    pd.DataFrame(case_registry).to_csv(
        CASE_REGISTRY_CSV, index=False, encoding="utf-8-sig"
    )
    # The HTML intentionally links to its own validation artifact. Create the
    # path before link checking, then replace it with the completed report.
    VALIDATION_JSON.write_text("{}\n", encoding="utf-8")
    write_reports(summary, case_registry, recall_figure)
    validation = validate_report(case_paths)
    validation["report_script_sha256"] = sha256_file(SCRIPT_PATH)
    validation["interpretation_csv_sha256"] = sha256_file(INTERPRETATION_CSV)
    validation["summary_json_sha256"] = sha256_file(SUMMARY_JSON)
    VALIDATION_JSON.write_text(
        json.dumps(json_safe(validation), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if validation["status"] != "PASS":
        raise RuntimeError(json.dumps(validation, ensure_ascii=False, indent=2))

    print(
        json.dumps(
            {
                "status": validation["status"],
                "report_html": str(REPORT_HTML),
                "report_markdown": str(REPORT_MD),
                "interpretation_csv": str(INTERPRETATION_CSV),
                "summary_json": str(SUMMARY_JSON),
                "case_image_count": len(case_registry),
                "temporal_experiment_run": False,
                "temporal_gate_open": bool(
                    summary["R02_C2_temporal_gate"][
                        "open_minimal_lag1_temporal_experiment"
                    ]
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
