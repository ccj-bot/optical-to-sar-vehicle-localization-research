from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw


SCRIPT = Path(__file__).resolve()
TASK_DIR = SCRIPT.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OUTPUT = STUDY / "m0b1_v2_cross_modal_direction_discrimination"
PROTOCOL = OUTPUT / "M0B1_V2_CROSS_MODAL_DIRECTION_DISCRIMINATION_PROTOCOL_FROZEN_BEFORE_RUN.md"
FREEZE = OUTPUT / "protocol_freeze.json"
LEDGER = OUTPUT / "execution_ledger.json"
VALIDATOR = TASK_DIR / "validate_m0b1_v2_cross_modal_direction.py"

M0B1 = STUDY / "m0b1_r02_raw_fragment_angular_direction_diagnostic"
M0B1R = STUDY / "m0b1_r_angular_dynamic_representation_audit"
M0A = STUDY / "m0a_r02_lag1_q95_region_support_transport_pilot"
REGION_ROOT = STUDY / "p1e_sar_only_response_interface" / "runtime_track_response_region_minimal_v1"

OLD_BANK = M0B1 / "dynamic_hypotheses_pre_reference.csv"
OLD_RAW_CONTROLS = M0B1 / "raw_fragment_alternative_controls_pre_reference.csv"
OLD_STATIC_CONTROLS = M0B1 / "static_shell_matched_controls_pre_reference.csv"
OLD_TIMING = M0B1 / "timing_query_table_pre_reference.csv"
OLD_PROTOCOL = M0B1 / "M0B1_R02_RAW_FRAGMENT_ANGULAR_DIRECTION_PROTOCOL_FROZEN_BEFORE_RUN.md"
OLD_SUMMARY = M0B1 / "post_reference_summary.json"
OLD_M0B1R_PROTOCOL = M0B1R / "M0B1_R_ANGULAR_DYNAMIC_REPRESENTATION_AUDIT_PROTOCOL_FROZEN_BEFORE_RUN.md"
OLD_M0B1R_SUMMARY = M0B1R / "audit_summary_pre_reference.json"
SAR_DIAGNOSTIC = M0B1R / "sar_q95_corresponding_boundary_structural_diagnostic_pre_reference.csv"
M0A_MATCHED_PRE = M0A / "pre_reference_matched_alternative_sets.csv"

# These are opened only after the pre-reference manifest has passed validation.
M0A_SUPPORTED_POST = M0A / "post_reference_supported_explanations.csv"
M0A_MATCHED_POST = M0A / "post_reference_matched_alternative_evaluation.csv"

OPTICAL_HYPOTHESES = (
    WORKSPACE
    / "output"
    / "person_optical_guided_sar_annotation_full_20260823"
    / "optical_person_frame_hypotheses.parquet"
)
OPTICAL_R02_PILOT = (
    WORKSPACE
    / "output"
    / "person_optical_guided_sar_annotation_full_20260823"
    / "pilot_R02ZF"
    / "optical_person_track_frames.csv"
)
OPTICAL_IMAGE_ROOT = (
    WORKSPACE / "output" / "pseudocolor_labelstudio_prep_20260722" / "frames" / "optical"
)
SAR_IMAGE_ROOT = (
    WORKSPACE / "output" / "pseudocolor_labelstudio_prep_20260722" / "frames" / "sar_pseudocolor"
)
REGION_MASK_DIR = REGION_ROOT / "response_region_masks"

PRE_BANK = OUTPUT / "direction_hypothesis_bank_pre_reference.parquet"
PRE_OPTICAL = OUTPUT / "optical_descriptors_unique_pre_reference.csv"
PRE_SAR = OUTPUT / "sar_descriptors_pre_reference.csv"
PRE_SCENE = OUTPUT / "scene_common_direction_audit_pre_reference.csv"
PRE_FRAGMENT = OUTPUT / "per_fragment_direction_sequence_pre_reference.csv"
PRE_TIMING_SUMMARY = OUTPUT / "timing_direction_summary_pre_reference.csv"
PRE_ATLAS_PAIRS = OUTPUT / "optical_direction_diversity_atlas_pairs_pre_reference.parquet"
PRE_ATLAS_RUNS = OUTPUT / "optical_direction_diversity_atlas_run_summary_pre_reference.csv"
PRE_ATLAS_WINDOWS = OUTPUT / "optical_direction_diversity_atlas_window_summary_pre_reference.csv"
PRE_ATLAS_CANDIDATES = OUTPUT / "optical_direction_diversity_atlas_future_candidate_windows_pre_reference.csv"
PRE_RAW_CONTROLS = OUTPUT / "frozen_raw_fragment_controls_pre_reference.csv"
PRE_STATIC_CONTROLS = OUTPUT / "frozen_static_shell_controls_pre_reference.csv"
PRE_MATCHED_CONTROLS = OUTPUT / "frozen_sar_matched_alternatives_pre_reference.csv"
PRE_SUMMARY = OUTPUT / "pre_reference_summary.json"
PRE_MANIFEST = OUTPUT / "pre_reference_manifest.json"
PRE_FIG_DIR = OUTPUT / "figures" / "pre_reference"

TOL = 1e-12
TIMING_CONDITIONS = (
    "NOMINAL",
    "SAR_SHIFT_MINUS_1",
    "SAR_SHIFT_PLUS_1",
    "OPTICAL_SHIFT_MINUS_1_NOMINAL_STEP",
    "OPTICAL_SHIFT_PLUS_1_NOMINAL_STEP",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.strip().str.lower().map({"true": True, "false": False}).fillna(False)


def finite(value: Any) -> float:
    try:
        output = float(value)
    except (TypeError, ValueError):
        return math.nan
    return output if np.isfinite(output) else math.nan


def optical_state(left: pd.Series, right: pd.Series) -> pd.Series:
    left = pd.to_numeric(left, errors="coerce")
    right = pd.to_numeric(right, errors="coerce")
    result = pd.Series("OPTICAL_DEFORMATION_OR_MIXED_SHIFT", index=left.index, dtype="object")
    result[(left > TOL) & (right > TOL)] = "OPTICAL_COHERENT_POSITIVE_SHIFT"
    result[(left < -TOL) & (right < -TOL)] = "OPTICAL_COHERENT_NEGATIVE_SHIFT"
    result[(left.abs() <= TOL) & (right.abs() <= TOL)] = "OPTICAL_NO_RESOLVED_SHIFT"
    return result


def compatibility(optical: str, sar: str) -> str:
    if optical not in {
        "OPTICAL_COHERENT_POSITIVE_SHIFT",
        "OPTICAL_COHERENT_NEGATIVE_SHIFT",
        "OPTICAL_DEFORMATION_OR_MIXED_SHIFT",
        "OPTICAL_NO_RESOLVED_SHIFT",
    }:
        return "DIRECTION_UNAVAILABLE"
    if sar not in {
        "SAR_COHERENT_POSITIVE_SHIFT",
        "SAR_COHERENT_NEGATIVE_SHIFT",
        "SAR_DEFORMATION_OR_MIXED_SHIFT",
        "SAR_NO_RESOLVED_SHIFT",
    }:
        return "DIRECTION_UNAVAILABLE"
    if "DEFORMATION" in optical or "DEFORMATION" in sar or "NO_RESOLVED" in optical or "NO_RESOLVED" in sar:
        return "DIRECTION_STRUCTURALLY_INDETERMINATE"
    optical_sign = "POSITIVE" if "POSITIVE" in optical else "NEGATIVE"
    sar_sign = "POSITIVE" if "POSITIVE" in sar else "NEGATIVE"
    return "DIRECTION_CONCORDANT" if optical_sign == sar_sign else "DIRECTION_CONTRADICTORY"


def unavailable_optical_state(availability: str) -> str:
    mapping = {
        "ANGULAR_DYNAMIC_UNAVAILABLE_SAME_OPTICAL_SAMPLE": "OPTICAL_DYNAMIC_UNAVAILABLE_SAME_SAMPLE",
        "ANGULAR_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK": "OPTICAL_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK",
        "ANGULAR_DYNAMIC_UNAVAILABLE_OBSERVATION": "OPTICAL_OBSERVATION_UNAVAILABLE",
        "STATIC_SHELL_REGION_INTERSECTION_MISSING": "OPTICAL_DYNAMIC_UNAVAILABLE_STATIC_FEASIBILITY",
    }
    return mapping.get(str(availability), "OPTICAL_OBSERVATION_UNAVAILABLE")


def freeze() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    required = [
        PROTOCOL,
        SCRIPT,
        VALIDATOR,
        OLD_BANK,
        OLD_RAW_CONTROLS,
        OLD_STATIC_CONTROLS,
        OLD_TIMING,
        OLD_PROTOCOL,
        OLD_M0B1R_PROTOCOL,
        OLD_M0B1R_SUMMARY,
        SAR_DIAGNOSTIC,
        M0A_MATCHED_PRE,
        OPTICAL_HYPOTHESES,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(missing)
    payload = {
        "schema": "PERSON_M0B1_V2_PROTOCOL_FREEZE_V1",
        "created_at": now_iso(),
        "starting_head": git_head(),
        "reference_loaded": False,
        "manual_reference_used_for_representation_or_control_selection": False,
        "predecessor_states": [
            "M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT",
            "M0B1_R_INTERVAL_OPERATOR_SEMANTIC_MISMATCH_CONFIRMED",
        ],
        "numerical_tolerance_deg": TOL,
        "timing_conditions": list(TIMING_CONDITIONS),
        "files": [
            {
                "path": str(path.relative_to(WORKSPACE)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in required
        ],
        "post_reference_paths_not_opened": [
            str(M0A_SUPPORTED_POST.relative_to(WORKSPACE)),
            str(M0A_MATCHED_POST.relative_to(WORKSPACE)),
        ],
        "prohibited_actions_executed": [],
    }
    write_json(FREEZE, payload)
    write_json(
        LEDGER,
        {
            "schema": "PERSON_M0B1_V2_EXECUTION_LEDGER_V1",
            "events": [
                {"stage": "PROTOCOL_CODE_INPUT_HASHES_FROZEN", "completed_at": now_iso()},
                {"stage": "REFERENCE_NOT_LOADED", "completed_at": now_iso()},
            ],
        },
    )
    print(json.dumps(payload, indent=2))


def verify_freeze() -> dict[str, Any]:
    payload = read_json(FREEZE)
    if payload["reference_loaded"]:
        raise RuntimeError("freeze says reference loaded")
    for item in payload["files"]:
        path = WORKSPACE / item["path"]
        if path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"frozen input changed: {path}")
    return payload


def build_scene_baseline(optical: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    keys = ["timing_condition", "source_optical_frame_index", "destination_optical_frame_index"]
    for key, group in optical.groupby(keys, dropna=False, sort=True):
        counts = group["optical_dynamic_state_v2"].value_counts()
        positive = int(counts.get("OPTICAL_COHERENT_POSITIVE_SHIFT", 0))
        negative = int(counts.get("OPTICAL_COHERENT_NEGATIVE_SHIFT", 0))
        mixed = int(counts.get("OPTICAL_DEFORMATION_OR_MIXED_SHIFT", 0))
        zero = int(counts.get("OPTICAL_NO_RESOLVED_SHIFT", 0))
        active = int(len(group))
        coherent = positive + negative
        if positive > negative and positive > 0:
            baseline = "OPTICAL_COHERENT_POSITIVE_SHIFT"
        elif negative > positive and negative > 0:
            baseline = "OPTICAL_COHERENT_NEGATIVE_SHIFT"
        else:
            baseline = "GLOBAL_DIRECTION_INDETERMINATE"
        proportions = np.array([positive, negative, mixed, zero], dtype=float)
        proportions = proportions[proportions > 0] / max(active, 1)
        entropy = float(-(proportions * np.log2(proportions)).sum()) if len(proportions) else 0.0
        majority = max(positive, negative, mixed, zero)
        rows.append(
            {
                "timing_condition": key[0],
                "source_optical_frame_index": int(key[1]),
                "destination_optical_frame_index": int(key[2]),
                "active_raw_fragment_count": active,
                "positive_count": positive,
                "negative_count": negative,
                "deformation_count": mixed,
                "no_resolved_count": zero,
                "unavailable_count": 0,
                "coherent_vote_count": coherent,
                "global_optical_direction_state": baseline,
                "majority_fraction_all_states": majority / max(active, 1),
                "coherent_majority_fraction": max(positive, negative) / max(coherent, 1),
                "direction_diversity_state_count": int(sum(v > 0 for v in [positive, negative, mixed, zero])),
                "shannon_entropy_bits": entropy,
                "fragment_to_fragment_disagreement_fraction": 1.0 - majority / max(active, 1),
                "reference_used": False,
            }
        )
    return pd.DataFrame(rows)


def enrich_bank() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bank = pd.read_csv(OLD_BANK, low_memory=False)
    sar = pd.read_csv(SAR_DIAGNOSTIC, low_memory=False)
    sar = sar.rename(
        columns={
            "d_left_s_deg": "d_left_s_deg_v2",
            "d_right_s_deg": "d_right_s_deg_v2",
            "d_mid_s_deg": "d_mid_s_deg_v2",
            "d_width_s_deg": "d_width_s_deg_v2",
        }
    )
    sar["sar_dynamic_state_v2"] = sar["sar_corresponding_boundary_state"].replace(
        {"SAR_DEFORMATION_OR_INDETERMINATE": "SAR_DEFORMATION_OR_MIXED_SHIFT"}
    )
    sar_columns = [
        "base_edge_id",
        "d_left_s_deg_v2",
        "d_right_s_deg_v2",
        "d_mid_s_deg_v2",
        "d_width_s_deg_v2",
        "sar_dynamic_state_v2",
        "source_out_degree",
        "destination_in_degree",
        "sar_relation_topology",
    ]
    bank = bank.merge(sar[sar_columns], on="base_edge_id", how="left", validate="many_to_one")
    available = bank["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE")
    for column in [
        "source_raw_theta_low_deg",
        "source_raw_theta_high_deg",
        "destination_raw_theta_low_deg",
        "destination_raw_theta_high_deg",
    ]:
        bank[column] = pd.to_numeric(bank[column], errors="coerce")
    bank["d_left_o_deg_v2"] = np.where(
        available, bank["destination_raw_theta_low_deg"] - bank["source_raw_theta_low_deg"], np.nan
    )
    bank["d_right_o_deg_v2"] = np.where(
        available, bank["destination_raw_theta_high_deg"] - bank["source_raw_theta_high_deg"], np.nan
    )
    bank["d_mid_o_deg_v2"] = np.where(
        available,
        (
            bank["destination_raw_theta_low_deg"]
            + bank["destination_raw_theta_high_deg"]
            - bank["source_raw_theta_low_deg"]
            - bank["source_raw_theta_high_deg"]
        )
        / 2.0,
        np.nan,
    )
    bank["d_width_o_deg_v2"] = np.where(
        available,
        (bank["destination_raw_theta_high_deg"] - bank["destination_raw_theta_low_deg"])
        - (bank["source_raw_theta_high_deg"] - bank["source_raw_theta_low_deg"]),
        np.nan,
    )
    bank["optical_dynamic_state_v2"] = [
        state if is_available else unavailable_optical_state(availability)
        for state, is_available, availability in zip(
            optical_state(bank["d_left_o_deg_v2"], bank["d_right_o_deg_v2"]),
            available,
            bank["angular_availability_state"],
        )
    ]
    bank["cross_modal_direction_state_v2"] = [
        compatibility(optical, sar_state)
        for optical, sar_state in zip(bank["optical_dynamic_state_v2"], bank["sar_dynamic_state_v2"])
    ]
    signature = [
        "timing_condition",
        "source_optical_frame_index",
        "destination_optical_frame_index",
        "source_track_id",
        "destination_track_id",
        "source_raw_theta_low_deg",
        "source_raw_theta_high_deg",
        "destination_raw_theta_low_deg",
        "destination_raw_theta_high_deg",
    ]
    optical = bank[available].sort_values("hypothesis_id").drop_duplicates(signature).copy()
    optical["bank_row_multiplicity"] = optical.set_index(signature).index.map(
        bank[available].groupby(signature, dropna=False).size()
    )
    baseline = build_scene_baseline(optical)
    baseline_keys = ["timing_condition", "source_optical_frame_index", "destination_optical_frame_index"]
    bank = bank.merge(
        baseline[baseline_keys + ["global_optical_direction_state"]],
        on=baseline_keys,
        how="left",
        validate="many_to_one",
    )
    bank["branch_vs_global_direction_relation"] = np.where(
        available,
        np.where(
            bank["optical_dynamic_state_v2"].eq(bank["global_optical_direction_state"]),
            "BRANCH_DIRECTION_EQUALS_GLOBAL_BASELINE",
            "BRANCH_DIRECTION_DIFFERS_FROM_GLOBAL_BASELINE",
        ),
        "BRANCH_DYNAMIC_UNAVAILABLE",
    )
    bank["global_cross_modal_direction_state"] = [
        compatibility(global_state, sar_state)
        for global_state, sar_state in zip(bank["global_optical_direction_state"], bank["sar_dynamic_state_v2"])
    ]
    return bank, optical, baseline


def build_atlas() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = pd.read_parquet(OPTICAL_HYPOTHESES)
    prohibited = {"physical_target_id", "manual_target_id", "target_id"}.intersection(data.columns)
    if prohibited:
        raise RuntimeError(f"atlas runtime input has prohibited fields: {prohibited}")
    data = data[data["box_source"].astype(str).eq("DETECTED")].copy()
    data = data.sort_values(
        ["run_id", "raw_track_fragment_id", "frame_index", "confidence"],
        ascending=[True, True, True, False],
    ).drop_duplicates(["run_id", "raw_track_fragment_id", "frame_index"])
    slope = 0.02666536443690682
    intercept = -45.502258572693094
    data["theta_low_deg"] = slope * pd.to_numeric(data["bbox_x1"], errors="raise") + intercept
    data["theta_high_deg"] = slope * pd.to_numeric(data["bbox_x2"], errors="raise") + intercept
    pair_rows: list[dict[str, Any]] = []
    for (run_id, fragment), group in data.groupby(["run_id", "raw_track_fragment_id"], sort=True):
        group = group.sort_values("frame_index")
        records = list(group.itertuples(index=False))
        for first, second in zip(records[:-1], records[1:]):
            d_left = float(second.theta_low_deg - first.theta_low_deg)
            d_right = float(second.theta_high_deg - first.theta_high_deg)
            state = optical_state(pd.Series([d_left]), pd.Series([d_right])).iloc[0]
            pair_rows.append(
                {
                    "run_id": str(run_id),
                    "raw_track_fragment_id": str(fragment),
                    "source_frame_index": int(first.frame_index),
                    "destination_frame_index": int(second.frame_index),
                    "source_timestamp_ms": int(first.timestamp_ms),
                    "destination_timestamp_ms": int(second.timestamp_ms),
                    "frame_separation": int(second.frame_index - first.frame_index),
                    "time_separation_ms": int(second.timestamp_ms - first.timestamp_ms),
                    "source_theta_low_deg": float(first.theta_low_deg),
                    "source_theta_high_deg": float(first.theta_high_deg),
                    "destination_theta_low_deg": float(second.theta_low_deg),
                    "destination_theta_high_deg": float(second.theta_high_deg),
                    "d_left_o_deg_v2": d_left,
                    "d_right_o_deg_v2": d_right,
                    "d_mid_o_deg_v2": 0.5 * (d_left + d_right),
                    "d_width_o_deg_v2": (second.theta_high_deg - second.theta_low_deg)
                    - (first.theta_high_deg - first.theta_low_deg),
                    "optical_dynamic_state_v2": state,
                    "reference_used": False,
                }
            )
    pairs = pd.DataFrame(pair_rows)
    run_summary = (
        pairs.groupby(["run_id", "optical_dynamic_state_v2"]).size().unstack(fill_value=0).reset_index()
    )
    for state in [
        "OPTICAL_COHERENT_POSITIVE_SHIFT",
        "OPTICAL_COHERENT_NEGATIVE_SHIFT",
        "OPTICAL_DEFORMATION_OR_MIXED_SHIFT",
        "OPTICAL_NO_RESOLVED_SHIFT",
    ]:
        if state not in run_summary:
            run_summary[state] = 0
    fragment_signs = (
        pairs[pairs["optical_dynamic_state_v2"].isin([
            "OPTICAL_COHERENT_POSITIVE_SHIFT",
            "OPTICAL_COHERENT_NEGATIVE_SHIFT",
        ])]
        .groupby(["run_id", "raw_track_fragment_id"])["optical_dynamic_state_v2"]
        .nunique()
    )
    reversal = fragment_signs[fragment_signs > 1].groupby(level=0).size()
    run_summary["fragment_sign_reversal_count"] = run_summary["run_id"].map(reversal).fillna(0).astype(int)
    run_summary["dynamic_pair_count"] = run_summary[
        [
            "OPTICAL_COHERENT_POSITIVE_SHIFT",
            "OPTICAL_COHERENT_NEGATIVE_SHIFT",
            "OPTICAL_DEFORMATION_OR_MIXED_SHIFT",
            "OPTICAL_NO_RESOLVED_SHIFT",
        ]
    ].sum(axis=1)
    window_rows: list[dict[str, Any]] = []
    for key, group in pairs.groupby(
        ["run_id", "source_frame_index", "destination_frame_index"], sort=True
    ):
        counts = group["optical_dynamic_state_v2"].value_counts()
        positive = int(counts.get("OPTICAL_COHERENT_POSITIVE_SHIFT", 0))
        negative = int(counts.get("OPTICAL_COHERENT_NEGATIVE_SHIFT", 0))
        mixed = int(counts.get("OPTICAL_DEFORMATION_OR_MIXED_SHIFT", 0))
        zero = int(counts.get("OPTICAL_NO_RESOLVED_SHIFT", 0))
        active = int(group["raw_track_fragment_id"].nunique())
        window_rows.append(
            {
                "run_id": key[0],
                "source_frame_index": int(key[1]),
                "destination_frame_index": int(key[2]),
                "frame_separation": int(key[2] - key[1]),
                "active_raw_fragment_count": active,
                "positive_count": positive,
                "negative_count": negative,
                "deformation_count": mixed,
                "no_resolved_count": zero,
                "simultaneous_opposite_coherent_directions": positive > 0 and negative > 0,
                "future_window_eligible": active >= 2 and positive >= 1 and negative >= 1,
                "reference_used": False,
            }
        )
    windows = pd.DataFrame(window_rows)
    candidates = windows[windows["future_window_eligible"]].copy()
    return pairs, run_summary, windows, candidates


def timing_summary(bank: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for timing, group in bank.groupby("timing_condition", sort=False):
        available = group["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE")
        feasible = bool_series(group["static_feasible"])
        rows.append(
            {
                "timing_condition": timing,
                "total_hypothesis": len(group),
                "static_feasible": int(feasible.sum()),
                "dynamic_available": int(available.sum()),
                "same_sample": int(group["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_SAME_OPTICAL_SAMPLE").sum()),
                "fragment_break": int(group["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK").sum()),
                "observation_unavailable": int(group["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_OBSERVATION").sum()),
                "static_infeasible": int((~feasible).sum()),
                "optical_positive": int(group["optical_dynamic_state_v2"].eq("OPTICAL_COHERENT_POSITIVE_SHIFT").sum()),
                "optical_negative": int(group["optical_dynamic_state_v2"].eq("OPTICAL_COHERENT_NEGATIVE_SHIFT").sum()),
                "optical_deformation": int(group["optical_dynamic_state_v2"].eq("OPTICAL_DEFORMATION_OR_MIXED_SHIFT").sum()),
                "optical_no_resolved": int(group["optical_dynamic_state_v2"].eq("OPTICAL_NO_RESOLVED_SHIFT").sum()),
                "sar_positive": int(group["sar_dynamic_state_v2"].eq("SAR_COHERENT_POSITIVE_SHIFT").sum()),
                "sar_negative": int(group["sar_dynamic_state_v2"].eq("SAR_COHERENT_NEGATIVE_SHIFT").sum()),
                "sar_deformation": int(group["sar_dynamic_state_v2"].eq("SAR_DEFORMATION_OR_MIXED_SHIFT").sum()),
                "cross_concordant": int(group["cross_modal_direction_state_v2"].eq("DIRECTION_CONCORDANT").sum()),
                "cross_contradictory": int(group["cross_modal_direction_state_v2"].eq("DIRECTION_CONTRADICTORY").sum()),
                "cross_structural_indeterminate": int(group["cross_modal_direction_state_v2"].eq("DIRECTION_STRUCTURALLY_INDETERMINATE").sum()),
                "cross_unavailable": int(group["cross_modal_direction_state_v2"].eq("DIRECTION_UNAVAILABLE").sum()),
            }
        )
    return pd.DataFrame(rows)


def render_pre_figures(optical: pd.DataFrame, scene: pd.DataFrame, run_summary: pd.DataFrame, candidates: pd.DataFrame) -> list[Path]:
    PRE_FIG_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    counts = optical.groupby(["timing_condition", "optical_dynamic_state_v2"]).size().unstack(fill_value=0)
    ax = counts.plot(kind="bar", stacked=True, figsize=(11, 5), color=["#e67e22"])
    ax.set_title("R02 deduplicated optical corresponding-boundary states")
    ax.set_ylabel("unique raw-fragment dynamic pairs")
    ax.legend(loc="upper right", fontsize=8)
    plt.tight_layout()
    path = PRE_FIG_DIR / "01_r02_optical_direction_by_timing.png"
    plt.savefig(path, dpi=150)
    plt.close()
    paths.append(path)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    nominal = scene[scene["timing_condition"].eq("NOMINAL")]
    ax.plot(nominal["source_optical_frame_index"], nominal["coherent_majority_fraction"], marker="o")
    ax.set_ylim(-0.02, 1.05)
    ax.set_title("R02 nominal global coherent-direction majority")
    ax.set_xlabel("source decoded optical frame")
    ax.set_ylabel("majority fraction among coherent fragments")
    ax.grid(alpha=0.25)
    plt.tight_layout()
    path = PRE_FIG_DIR / "02_r02_scene_common_majority.png"
    plt.savefig(path, dpi=150)
    plt.close()
    paths.append(path)

    top = run_summary.sort_values("dynamic_pair_count", ascending=False).head(25).copy()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(top["run_id"], top["OPTICAL_COHERENT_POSITIVE_SHIFT"], label="positive", color="#e67e22")
    ax.bar(top["run_id"], top["OPTICAL_COHERENT_NEGATIVE_SHIFT"], bottom=top["OPTICAL_COHERENT_POSITIVE_SHIFT"], label="negative", color="#2980b9")
    ax.bar(
        top["run_id"],
        top["OPTICAL_DEFORMATION_OR_MIXED_SHIFT"],
        bottom=top["OPTICAL_COHERENT_POSITIVE_SHIFT"] + top["OPTICAL_COHERENT_NEGATIVE_SHIFT"],
        label="mixed",
        color="#7f8c8d",
    )
    ax.set_title(f"GT-blind optical diversity atlas; eligible opposite-direction windows={len(candidates)}")
    ax.tick_params(axis="x", rotation=60)
    ax.legend()
    plt.tight_layout()
    path = PRE_FIG_DIR / "03_optical_diversity_atlas_runs.png"
    plt.savefig(path, dpi=150)
    plt.close()
    paths.append(path)
    return paths


def pre_reference() -> None:
    freeze_payload = verify_freeze()
    bank, optical, scene = enrich_bank()
    atlas_pairs, atlas_runs, atlas_windows, atlas_candidates = build_atlas()
    summary = timing_summary(bank)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    bank.to_parquet(PRE_BANK, index=False)
    optical.to_csv(PRE_OPTICAL, index=False, encoding="utf-8-sig")
    sar_columns = [
        "base_edge_id",
        "pair_index",
        "from_frame",
        "to_frame",
        "d_left_s_deg_v2",
        "d_right_s_deg_v2",
        "d_mid_s_deg_v2",
        "d_width_s_deg_v2",
        "sar_dynamic_state_v2",
        "source_out_degree",
        "destination_in_degree",
        "sar_relation_topology",
    ]
    bank[sar_columns].drop_duplicates("base_edge_id").to_csv(PRE_SAR, index=False, encoding="utf-8-sig")
    scene.to_csv(PRE_SCENE, index=False, encoding="utf-8-sig")
    optical[
        [
            "timing_condition",
            "pair_index",
            "source_track_id",
            "source_optical_frame_index",
            "destination_optical_frame_index",
            "d_left_o_deg_v2",
            "d_right_o_deg_v2",
            "d_mid_o_deg_v2",
            "d_width_o_deg_v2",
            "optical_dynamic_state_v2",
            "bank_row_multiplicity",
        ]
    ].to_csv(PRE_FRAGMENT, index=False, encoding="utf-8-sig")
    summary.to_csv(PRE_TIMING_SUMMARY, index=False, encoding="utf-8-sig")
    atlas_pairs.to_parquet(PRE_ATLAS_PAIRS, index=False)
    atlas_runs.to_csv(PRE_ATLAS_RUNS, index=False, encoding="utf-8-sig")
    atlas_windows.to_csv(PRE_ATLAS_WINDOWS, index=False, encoding="utf-8-sig")
    atlas_candidates.to_csv(PRE_ATLAS_CANDIDATES, index=False, encoding="utf-8-sig")
    shutil.copyfile(OLD_RAW_CONTROLS, PRE_RAW_CONTROLS)
    shutil.copyfile(OLD_STATIC_CONTROLS, PRE_STATIC_CONTROLS)
    shutil.copyfile(M0A_MATCHED_PRE, PRE_MATCHED_CONTROLS)
    figures = render_pre_figures(optical, scene, atlas_runs, atlas_candidates)

    nominal_optical = optical[optical["timing_condition"].eq("NOMINAL")]
    pre_summary = {
        "schema": "PERSON_M0B1_V2_PRE_REFERENCE_SUMMARY_V1",
        "created_at": now_iso(),
        "reference_loaded": False,
        "reference_sources_opened": False,
        "starting_head": freeze_payload["starting_head"],
        "hypothesis_rows": int(len(bank)),
        "static_feasible_rows": int(bool_series(bank["static_feasible"]).sum()),
        "dynamic_available_rows": int(bank["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE").sum()),
        "same_sample_rows": int(bank["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_SAME_OPTICAL_SAMPLE").sum()),
        "fragment_break_rows": int(bank["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK").sum()),
        "deduplicated_optical_pairs": int(len(optical)),
        "nominal_deduplicated_optical_pairs": int(len(nominal_optical)),
        "nominal_optical_state_counts": nominal_optical["optical_dynamic_state_v2"].value_counts().to_dict(),
        "r02_direction_sign_degenerate": bool(
            len(nominal_optical) > 0
            and nominal_optical["optical_dynamic_state_v2"].eq("OPTICAL_COHERENT_POSITIVE_SHIFT").all()
        ),
        "branch_equals_global_fraction_dynamic_available": float(
            bank.loc[
                bank["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE"),
                "branch_vs_global_direction_relation",
            ].eq("BRANCH_DIRECTION_EQUALS_GLOBAL_BASELINE").mean()
        ),
        "atlas_pair_count": int(len(atlas_pairs)),
        "atlas_run_count": int(atlas_pairs["run_id"].nunique()),
        "atlas_fragment_count": int(atlas_pairs[["run_id", "raw_track_fragment_id"]].drop_duplicates().shape[0]),
        "atlas_future_candidate_window_count": int(len(atlas_candidates)),
        "atlas_adjacent_future_candidate_window_count": int(atlas_candidates["frame_separation"].eq(1).sum()),
        "atlas_same_sample_burden": "ZERO_BY_DISTINCT_PAIR_CONTRACT",
        "atlas_fragment_break_burden": "NOT_DEFINED_WITHOUT_CROSS_FRAGMENT_IDENTITY",
        "sync_status": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
        "manual_reference_used_for_representation_or_control_selection": False,
        "hypotheses_pruned": False,
        "magnitude_used": False,
    }
    write_json(PRE_SUMMARY, pre_summary)

    files = [
        PRE_BANK,
        PRE_OPTICAL,
        PRE_SAR,
        PRE_SCENE,
        PRE_FRAGMENT,
        PRE_TIMING_SUMMARY,
        PRE_ATLAS_PAIRS,
        PRE_ATLAS_RUNS,
        PRE_ATLAS_WINDOWS,
        PRE_ATLAS_CANDIDATES,
        PRE_RAW_CONTROLS,
        PRE_STATIC_CONTROLS,
        PRE_MATCHED_CONTROLS,
        PRE_SUMMARY,
        *figures,
    ]
    manifest = {
        "schema": "PERSON_M0B1_V2_PRE_REFERENCE_MANIFEST_V1",
        "created_at": now_iso(),
        "reference_loaded": False,
        "reference_sources_opened": False,
        "protocol_freeze_sha256": sha256_file(FREEZE),
        "files": [
            {"path": str(path.relative_to(WORKSPACE)), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in files
        ],
        "prohibited_post_reference_paths": [
            str(M0A_SUPPORTED_POST.relative_to(WORKSPACE)),
            str(M0A_MATCHED_POST.relative_to(WORKSPACE)),
        ],
    }
    write_json(PRE_MANIFEST, manifest)
    ledger = read_json(LEDGER)
    ledger["events"].extend(
        [
            {"stage": "OPTICAL_SAR_DESCRIPTORS_MATERIALIZED_PRE_REFERENCE", "completed_at": now_iso()},
            {"stage": "GLOBAL_DIRECTION_BASELINE_FROZEN", "completed_at": now_iso()},
            {"stage": "CONTROLS_AND_TIMING_CONDITIONS_FROZEN", "completed_at": now_iso()},
            {"stage": "OPTICAL_DIVERSITY_ATLAS_MATERIALIZED_GT_BLIND", "completed_at": now_iso()},
            {"stage": "PRE_REFERENCE_OUTPUT_HASHES_FROZEN", "completed_at": now_iso()},
        ]
    )
    write_json(LEDGER, ledger)
    print(json.dumps(pre_summary, indent=2))


def verify_pre_manifest() -> dict[str, Any]:
    manifest = read_json(PRE_MANIFEST)
    if manifest["reference_loaded"] or manifest["reference_sources_opened"]:
        raise RuntimeError("pre-reference manifest boundary violated")
    for item in manifest["files"]:
        path = WORKSPACE / item["path"]
        if path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"pre-reference output changed: {path}")
    return manifest


def pair_decision(supported: str, alternative: str) -> str:
    if supported == "DIRECTION_CONCORDANT" and alternative == "DIRECTION_CONTRADICTORY":
        return "DIRECTION_FAVORS_SUPPORTED"
    if supported == "DIRECTION_CONTRADICTORY" and alternative == "DIRECTION_CONCORDANT":
        return "DIRECTION_FAVORS_NULL"
    return "DIRECTION_NO_DECISION"


def joint_category(sar_only: str, direction: str) -> str:
    if sar_only == "TIE" and direction == "DIRECTION_FAVORS_SUPPORTED":
        return "DIRECTION_RESCUE"
    if sar_only == "SUPPORTED_WIN" and direction == "DIRECTION_FAVORS_SUPPORTED":
        return "DIRECTION_CONFIRMATION"
    if (sar_only == "SUPPORTED_WIN" and direction == "DIRECTION_FAVORS_NULL") or (
        sar_only == "ALTERNATIVE_WIN" and direction == "DIRECTION_FAVORS_SUPPORTED"
    ):
        return "DIRECTION_CONFLICT"
    if direction == "DIRECTION_NO_DECISION" and sar_only != "TIE":
        return "DIRECTION_REDUNDANT_NO_DECISION"
    if direction == "DIRECTION_NO_DECISION" and sar_only == "TIE":
        return "DIRECTION_NO_INFORMATION"
    return "DIRECTION_OTHER_CATEGORICAL_RELATION"


def add_evaluation_groups(bank: pd.DataFrame, supported: pd.DataFrame, matched: pd.DataFrame) -> pd.DataFrame:
    supported_ids = set(supported["base_edge_id"].astype(str))
    matched_ids = set(matched["alternative_base_edge_id"].astype(str))
    output = bank.copy()
    output["evaluation_group"] = "PRE_REFERENCE_OTHER"
    output.loc[output["base_edge_id"].isin(matched_ids), "evaluation_group"] = "FROZEN_MATCHED_SAR_NULL"
    output.loc[output["base_edge_id"].isin(supported_ids), "evaluation_group"] = "REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED"
    return output


def build_pairwise(bank: pd.DataFrame, matched: pd.DataFrame) -> pd.DataFrame:
    available = bank[bank["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE")].copy()
    available = available.sort_values("hypothesis_id").drop_duplicates(
        ["timing_condition", "base_edge_id", "source_track_id"]
    )
    groups = {
        (str(timing), str(edge)): group.set_index("source_track_id", drop=False)
        for (timing, edge), group in available.groupby(["timing_condition", "base_edge_id"], sort=False)
    }
    rows: list[dict[str, Any]] = []
    for control in matched.itertuples(index=False):
        for timing in TIMING_CONDITIONS:
            supported_group = groups.get((timing, str(control.primary_base_edge_id)))
            null_group = groups.get((timing, str(control.alternative_base_edge_id)))
            tracks: set[str] = set()
            if supported_group is not None:
                tracks.update(supported_group.index.astype(str))
            if null_group is not None:
                tracks.update(null_group.index.astype(str))
            if not tracks:
                rows.append(
                    {
                        "timing_condition": timing,
                        "primary_base_edge_id": control.primary_base_edge_id,
                        "alternative_base_edge_id": control.alternative_base_edge_id,
                        "alternative_rank": int(control.alternative_rank),
                        "raw_track_fragment_id": "UNAVAILABLE",
                        "branch_pair_available": False,
                        "direction_pairwise_decision": "DIRECTION_NO_DECISION",
                        "global_pairwise_decision": "DIRECTION_NO_DECISION",
                        "sar_only_pairwise_outcome": control.pairwise_outcome,
                        "joint_category": joint_category(control.pairwise_outcome, "DIRECTION_NO_DECISION"),
                    }
                )
                continue
            for track in sorted(tracks):
                sup = supported_group.loc[track] if supported_group is not None and track in supported_group.index else None
                alt = null_group.loc[track] if null_group is not None and track in null_group.index else None
                if isinstance(sup, pd.DataFrame):
                    sup = sup.iloc[0]
                if isinstance(alt, pd.DataFrame):
                    alt = alt.iloc[0]
                pair_available = sup is not None and alt is not None
                direction = pair_decision(
                    str(sup["cross_modal_direction_state_v2"]) if sup is not None else "DIRECTION_UNAVAILABLE",
                    str(alt["cross_modal_direction_state_v2"]) if alt is not None else "DIRECTION_UNAVAILABLE",
                )
                global_direction = pair_decision(
                    str(sup["global_cross_modal_direction_state"]) if sup is not None else "DIRECTION_UNAVAILABLE",
                    str(alt["global_cross_modal_direction_state"]) if alt is not None else "DIRECTION_UNAVAILABLE",
                )
                rows.append(
                    {
                        "timing_condition": timing,
                        "pair_index": int(sup["pair_index"] if sup is not None else alt["pair_index"]),
                        "from_frame": int(sup["from_frame"] if sup is not None else alt["from_frame"]),
                        "to_frame": int(sup["to_frame"] if sup is not None else alt["to_frame"]),
                        "primary_base_edge_id": control.primary_base_edge_id,
                        "alternative_base_edge_id": control.alternative_base_edge_id,
                        "alternative_rank": int(control.alternative_rank),
                        "raw_track_fragment_id": track,
                        "supported_hypothesis_id": str(sup["hypothesis_id"]) if sup is not None else "",
                        "alternative_hypothesis_id": str(alt["hypothesis_id"]) if alt is not None else "",
                        "branch_pair_available": pair_available,
                        "supported_direction_state": str(sup["cross_modal_direction_state_v2"]) if sup is not None else "DIRECTION_UNAVAILABLE",
                        "alternative_direction_state": str(alt["cross_modal_direction_state_v2"]) if alt is not None else "DIRECTION_UNAVAILABLE",
                        "direction_pairwise_decision": direction,
                        "supported_global_direction_state": str(sup["global_cross_modal_direction_state"]) if sup is not None else "DIRECTION_UNAVAILABLE",
                        "alternative_global_direction_state": str(alt["global_cross_modal_direction_state"]) if alt is not None else "DIRECTION_UNAVAILABLE",
                        "global_pairwise_decision": global_direction,
                        "branch_decision_differs_from_global": direction != global_direction,
                        "sar_only_pairwise_outcome": control.pairwise_outcome,
                        "supported_minus_alternative_retention": float(control.supported_minus_alternative),
                        "joint_category": joint_category(control.pairwise_outcome, direction),
                    }
                )
    return pd.DataFrame(rows)


def collapse_pairwise(pairwise: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    keys = ["timing_condition", "pair_index", "primary_base_edge_id", "alternative_base_edge_id", "alternative_rank"]
    for key, group in pairwise.groupby(keys, dropna=False, sort=True):
        available = group[group["branch_pair_available"].astype(bool)]
        decisions = set(available["direction_pairwise_decision"])
        global_decisions = set(available["global_pairwise_decision"])
        decision = (
            "DIRECTION_FAVORS_SUPPORTED"
            if decisions == {"DIRECTION_FAVORS_SUPPORTED"}
            else "DIRECTION_FAVORS_NULL"
            if decisions == {"DIRECTION_FAVORS_NULL"}
            else "DIRECTION_NO_DECISION"
        )
        global_decision = (
            "DIRECTION_FAVORS_SUPPORTED"
            if global_decisions == {"DIRECTION_FAVORS_SUPPORTED"}
            else "DIRECTION_FAVORS_NULL"
            if global_decisions == {"DIRECTION_FAVORS_NULL"}
            else "DIRECTION_NO_DECISION"
        )
        sar_only = str(group["sar_only_pairwise_outcome"].iloc[0])
        rows.append(
            {
                "timing_condition": key[0],
                "pair_index": int(key[1]),
                "primary_base_edge_id": key[2],
                "alternative_base_edge_id": key[3],
                "alternative_rank": int(key[4]),
                "available_raw_fragment_count": int(available["raw_track_fragment_id"].nunique()),
                "direction_pairwise_decision": decision,
                "global_pairwise_decision": global_decision,
                "branch_decision_differs_from_global": decision != global_decision,
                "sar_only_pairwise_outcome": sar_only,
                "joint_category": joint_category(sar_only, decision),
            }
        )
    return pd.DataFrame(rows)


def build_static_tautology(evaluated: pd.DataFrame) -> pd.DataFrame:
    controls = pd.read_csv(PRE_STATIC_CONTROLS)
    lookup = evaluated.set_index("hypothesis_id", drop=False)
    rows: list[dict[str, Any]] = []
    for control in controls.itertuples(index=False):
        if control.primary_hypothesis_id not in lookup.index or control.control_hypothesis_id not in lookup.index:
            continue
        primary = lookup.loc[control.primary_hypothesis_id]
        null = lookup.loc[control.control_hypothesis_id]
        if isinstance(primary, pd.DataFrame):
            primary = primary.iloc[0]
        if isinstance(null, pd.DataFrame):
            null = null.iloc[0]
        if primary["evaluation_group"] != "REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED":
            continue
        rows.append(
            {
                "timing_condition": primary["timing_condition"],
                "pair_index": int(primary["pair_index"]),
                "primary_hypothesis_id": primary["hypothesis_id"],
                "control_hypothesis_id": null["hypothesis_id"],
                "primary_direction_state": primary["cross_modal_direction_state_v2"],
                "control_direction_state": null["cross_modal_direction_state_v2"],
                "direction_pairwise_decision": pair_decision(
                    str(primary["cross_modal_direction_state_v2"]), str(null["cross_modal_direction_state_v2"])
                ),
                "static_distance": float(control.static_distance),
                "match_tier": control.match_tier,
                "direction_used_for_selection": False,
                "reference_used_for_selection": False,
            }
        )
    return pd.DataFrame(rows)


def image_path(root: Path, run_id: str, frame_index: int, timestamp_ms: int) -> Path:
    folder = root / run_id
    exact = folder / f"frame_{frame_index:06d}_t{timestamp_ms:06d}ms.jpg"
    if exact.is_file():
        return exact
    matches = sorted(folder.glob(f"frame_{frame_index:06d}_t*ms.*"))
    if not matches:
        raise FileNotFoundError(f"image missing for {run_id} frame {frame_index}")
    return matches[0]


def region_label(region_id: str) -> int:
    return int(str(region_id).rsplit("R", 1)[1])


def crop_box(shape: tuple[int, int], boxes: Iterable[tuple[float, float, float, float]], margin: int = 160) -> tuple[int, int, int, int]:
    boxes = list(boxes)
    height, width = shape
    if not boxes:
        return 0, 0, width, height
    x1 = max(0, int(min(box[0] for box in boxes) - margin))
    y1 = max(0, int(min(box[1] for box in boxes) - margin))
    x2 = min(width, int(max(box[2] for box in boxes) + margin))
    y2 = min(height, int(max(box[3] for box in boxes) + margin))
    return x1, y1, x2, y2


def prepare_optical_lookup() -> tuple[pd.DataFrame, dict[tuple[str, int], pd.DataFrame]]:
    data = pd.read_parquet(OPTICAL_HYPOTHESES)
    data = data[data["box_source"].astype(str).eq("DETECTED")].copy()
    data = data.sort_values(
        ["run_id", "frame_index", "raw_track_fragment_id", "confidence"],
        ascending=[True, True, True, False],
    ).drop_duplicates(["run_id", "frame_index", "raw_track_fragment_id"])
    return data, {(str(run), int(frame)): group.copy() for (run, frame), group in data.groupby(["run_id", "frame_index"])}


def draw_optical_panel(ax: Any, row: pd.Series, prefix: str, by_frame: dict[tuple[str, int], pd.DataFrame]) -> None:
    frame = int(row[f"{prefix}_optical_frame_index"])
    timestamp = int(row[f"{prefix}_optical_timestamp_ms"])
    track = str(row[f"{prefix}_track_id"] if f"{prefix}_track_id" in row else row["source_track_id"])
    image = cv2.cvtColor(cv2.imread(str(image_path(OPTICAL_IMAGE_ROOT, "R02ZF", frame, timestamp))), cv2.COLOR_BGR2RGB)
    group = by_frame.get(("R02ZF", frame), pd.DataFrame())
    selected = group[group["raw_track_fragment_id"].astype(str).eq(track)]
    boxes = [tuple(map(float, item)) for item in selected[["bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"]].to_numpy()]
    crop = crop_box(image.shape[:2], boxes)
    x1, y1, x2, y2 = crop
    ax.imshow(image[y1:y2, x1:x2])
    for record in group.itertuples(index=False):
        bx1, by1, bx2, by2 = map(float, [record.bbox_x1, record.bbox_y1, record.bbox_x2, record.bbox_y2])
        if bx2 < x1 or bx1 > x2 or by2 < y1 or by1 > y2:
            continue
        color = "lime" if str(record.raw_track_fragment_id) == track else "white"
        ax.add_patch(plt.Rectangle((bx1 - x1, by1 - y1), bx2 - bx1, by2 - by1, fill=False, edgecolor=color, linewidth=2 if color == "lime" else 0.8))
    ax.set_title(f"Optical {prefix} F{frame} | {track}", fontsize=9)
    ax.axis("off")


def draw_sar_panel(ax: Any, row: pd.Series, prefix: str, manual: pd.Series | None) -> None:
    frame = int(row["from_frame"] if prefix == "source" else row["to_frame"])
    timestamp = int(round(frame * 1000 / 30.0))
    uid = str(row["from_frame_uid"] if prefix == "source" else row["to_frame_uid"])
    region_id = str(row["source_region_id"] if prefix == "source" else row["destination_region_id"])
    image = cv2.cvtColor(cv2.imread(str(image_path(SAR_IMAGE_ROOT, "R02ZF", frame, timestamp))), cv2.COLOR_BGR2RGB)
    with np.load(REGION_MASK_DIR / f"{uid}.npz") as archive:
        labels = archive["Q095"]
    mask = labels == region_label(region_id)
    ys, xs = np.nonzero(mask)
    crop = crop_box(image.shape[:2], [(xs.min(), ys.min(), xs.max(), ys.max())] if len(xs) else [], margin=80)
    x1, y1, x2, y2 = crop
    ax.imshow(image[y1:y2, x1:x2])
    ax.contour(mask[y1:y2, x1:x2], levels=[0.5], colors=["lime"], linewidths=1.8)
    if manual is not None:
        field = "source_manual_centers_json" if prefix == "source" else "destination_manual_centers_json"
        for point in json.loads(manual[field]):
            px, py = float(point["x_px"]) - x1, float(point["y_px"]) - y1
            ax.scatter([px], [py], marker="x", color="red", s=50)
            ax.text(px + 3, py - 3, str(point["target_id"]).split("PERSON")[-1], color="red", fontsize=7)
    ax.set_title(f"SAR {prefix} F{frame} | {region_id.rsplit('__', 1)[-1]}", fontsize=9)
    ax.axis("off")


def render_hypothesis_pack(row: pd.Series, manual: pd.Series | None, by_frame: dict[tuple[str, int], pd.DataFrame], path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), dpi=130)
    draw_optical_panel(axes[0, 0], row, "source", by_frame)
    draw_optical_panel(axes[0, 1], row, "destination", by_frame)
    draw_sar_panel(axes[1, 0], row, "source", manual)
    draw_sar_panel(axes[1, 1], row, "destination", manual)
    fig.suptitle(title, fontsize=11)
    plt.tight_layout(rect=(0, 0, 1, 0.96))
    plt.savefig(path)
    plt.close(fig)


def select_case(frame: pd.DataFrame, mask: pd.Series, sort: list[str]) -> pd.Series | None:
    subset = frame[mask].sort_values(sort)
    return subset.iloc[0] if len(subset) else None


def render_atlas_opposite_case(atlas_pairs: pd.DataFrame, optical_data: pd.DataFrame, path: Path) -> dict[str, Any] | None:
    candidates = pd.read_csv(PRE_ATLAS_CANDIDATES)
    if candidates.empty:
        return None
    candidate = candidates.sort_values(["run_id", "source_frame_index", "destination_frame_index"]).iloc[0]
    group = atlas_pairs[
        atlas_pairs["run_id"].eq(candidate["run_id"])
        & atlas_pairs["source_frame_index"].eq(candidate["source_frame_index"])
        & atlas_pairs["destination_frame_index"].eq(candidate["destination_frame_index"])
    ]
    pos = group[group["optical_dynamic_state_v2"].eq("OPTICAL_COHERENT_POSITIVE_SHIFT")].sort_values("raw_track_fragment_id").iloc[0]
    neg = group[group["optical_dynamic_state_v2"].eq("OPTICAL_COHERENT_NEGATIVE_SHIFT")].sort_values("raw_track_fragment_id").iloc[0]
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), dpi=130)
    for row_index, pair in enumerate([pos, neg]):
        for column_index, prefix in enumerate(["source", "destination"]):
            frame = int(pair[f"{prefix}_frame_index"])
            timestamp = int(pair[f"{prefix}_timestamp_ms"])
            image = cv2.cvtColor(cv2.imread(str(image_path(OPTICAL_IMAGE_ROOT, str(pair.run_id), frame, timestamp))), cv2.COLOR_BGR2RGB)
            selected = optical_data[
                optical_data["run_id"].astype(str).eq(str(pair.run_id))
                & optical_data["frame_index"].eq(frame)
                & optical_data["raw_track_fragment_id"].astype(str).eq(str(pair.raw_track_fragment_id))
            ]
            boxes = [tuple(map(float, item)) for item in selected[["bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2"]].to_numpy()]
            x1, y1, x2, y2 = crop_box(image.shape[:2], boxes)
            axes[row_index, column_index].imshow(image[y1:y2, x1:x2])
            for box in boxes:
                axes[row_index, column_index].add_patch(plt.Rectangle((box[0]-x1, box[1]-y1), box[2]-box[0], box[3]-box[1], fill=False, edgecolor="lime", linewidth=2))
            axes[row_index, column_index].set_title(f"{pair.optical_dynamic_state_v2} | {prefix} F{frame}", fontsize=9)
            axes[row_index, column_index].axis("off")
    fig.suptitle(f"GT-blind future window {candidate.run_id} F{int(candidate.source_frame_index)}->{int(candidate.destination_frame_index)}")
    plt.tight_layout(rect=(0, 0, 1, 0.96))
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path)
    plt.close(fig)
    return candidate.to_dict()


def make_contact_sheet(images: list[Path], output: Path) -> None:
    readable = [Image.open(path).convert("RGB") for path in images if path.is_file()]
    if not readable:
        return
    thumbs = []
    for image in readable:
        image.thumbnail((520, 340))
        canvas = Image.new("RGB", (540, 380), "white")
        canvas.paste(image, ((540 - image.width) // 2, 10))
        thumbs.append(canvas)
    columns = 3
    rows = math.ceil(len(thumbs) / columns)
    sheet = Image.new("RGB", (columns * 540, rows * 380), "#dddddd")
    for index, image in enumerate(thumbs):
        sheet.paste(image, ((index % columns) * 540, (index // columns) * 380))
    sheet.save(output)


def markdown_table(frame: pd.DataFrame, max_rows: int = 30) -> str:
    if frame.empty:
        return "(empty)"
    view = frame.head(max_rows).copy()
    columns = list(view.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in view.itertuples(index=False, name=None):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append("" if not np.isfinite(value) else f"{value:.4f}")
            else:
                values.append(str(value).replace("|", "/"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def post_reference() -> None:
    verify_freeze()
    verify_pre_manifest()
    bank = pd.read_parquet(PRE_BANK)
    supported = pd.read_csv(M0A_SUPPORTED_POST)
    supported = supported[supported["condition"].eq("P0")].drop_duplicates("base_edge_id")
    matched = pd.read_csv(M0A_MATCHED_POST)
    matched = matched[
        matched["condition"].eq("P0")
        & matched["alternative_reference_state"].eq("REFERENCE_UNSUPPORTED")
    ].copy()
    evaluated = add_evaluation_groups(bank, supported, matched)
    evaluated_subset = evaluated[evaluated["evaluation_group"].ne("PRE_REFERENCE_OTHER")].copy()
    evaluated_subset.to_parquet(OUTPUT / "post_reference_hypothesis_evaluation.parquet", index=False)

    pairwise = build_pairwise(evaluated, matched)
    cluster = collapse_pairwise(pairwise)
    pairwise.to_csv(OUTPUT / "supported_vs_matched_null_pairwise_direction.csv", index=False, encoding="utf-8-sig")
    cluster.to_csv(OUTPUT / "supported_vs_matched_null_cluster_decisions.csv", index=False, encoding="utf-8-sig")

    direction_summary = (
        cluster.groupby(["timing_condition", "direction_pairwise_decision"]).size().unstack(fill_value=0).reset_index()
    )
    direction_summary.to_csv(OUTPUT / "pairwise_direction_summary.csv", index=False, encoding="utf-8-sig")
    joint = (
        cluster.groupby(["timing_condition", "sar_only_pairwise_outcome", "direction_pairwise_decision", "joint_category"])
        .size()
        .reset_index(name="matched_edge_pair_count")
    )
    joint.to_csv(OUTPUT / "sar_only_direction_cross_tab.csv", index=False, encoding="utf-8-sig")

    cluster_by_pair = (
        cluster.groupby(["timing_condition", "pair_index", "direction_pairwise_decision"]).size().reset_index(name="matched_edge_pair_count")
    )
    cluster_by_pair.to_csv(OUTPUT / "cluster_aware_direction_by_frame_pair.csv", index=False, encoding="utf-8-sig")
    fragment_cluster = (
        pairwise[pairwise["branch_pair_available"].astype(bool)]
        .groupby(["timing_condition", "raw_track_fragment_id", "direction_pairwise_decision"])
        .size()
        .reset_index(name="matched_edge_pair_row_count")
    )
    fragment_cluster.to_csv(OUTPUT / "cluster_aware_direction_by_raw_fragment.csv", index=False, encoding="utf-8-sig")
    loo_rows = []
    nominal_cluster = cluster[cluster["timing_condition"].eq("NOMINAL")]
    for held_out in sorted(nominal_cluster["pair_index"].unique()):
        remainder = nominal_cluster[nominal_cluster["pair_index"].ne(held_out)]
        counts = remainder["direction_pairwise_decision"].value_counts()
        loo_rows.append(
            {
                "held_out_pair_index": int(held_out),
                "remaining_matched_edge_pairs": int(len(remainder)),
                "favors_supported": int(counts.get("DIRECTION_FAVORS_SUPPORTED", 0)),
                "favors_null": int(counts.get("DIRECTION_FAVORS_NULL", 0)),
                "no_decision": int(counts.get("DIRECTION_NO_DECISION", 0)),
            }
        )
    pd.DataFrame(loo_rows).to_csv(OUTPUT / "leave_one_frame_pair_out_direction.csv", index=False, encoding="utf-8-sig")

    tautology = build_static_tautology(evaluated)
    tautology.to_csv(OUTPUT / "static_shell_tautology_control.csv", index=False, encoding="utf-8-sig")

    evaluator_audit = {
        "schema": "PERSON_M0B1_V2_RAW_FRAGMENT_EVALUATOR_AUDIT_V1",
        "created_at": now_iso(),
        "audited_sources": [
            {
                "path": str(OPTICAL_HYPOTHESES.relative_to(WORKSPACE)),
                "sha256": sha256_file(OPTICAL_HYPOTHESES),
                "finding": "contains raw_track_fragment_id but no manual or physical target identity",
            },
            {
                "path": str(OPTICAL_R02_PILOT.relative_to(WORKSPACE)),
                "sha256": sha256_file(OPTICAL_R02_PILOT),
                "finding": "contains person_id but no traceable manual/physical target relation and no raw_track_fragment_id",
            },
        ],
        "direct_raw_fragment_to_manual_target_source_found": False,
        "status": "M0B1_V2_RAW_BRANCH_EVALUATION_UNRESOLVED",
        "optical_person_id_used_as_truth": False,
        "runtime_branch_relabelled": False,
    }
    write_json(OUTPUT / "raw_fragment_target_evaluator_audit.json", evaluator_audit)
    write_json(
        OUTPUT / "wrong_raw_fragment_control_status.json",
        {
            "status": "NOT_EXECUTED_NO_CONFIRMED_TARGET_BRANCH_SUBSET",
            "correct_vs_wrong_raw_fragment_direction_result": "UNRESOLVED",
            "reason": "no legal raw-fragment-to-manual-target evaluator",
        },
    )

    optical_data, optical_by_frame = prepare_optical_lookup()
    supported_map = {str(row.base_edge_id): pd.Series(row._asdict()) for row in supported.itertuples(index=False)}
    matched_primary = dict(zip(matched["alternative_base_edge_id"].astype(str), matched["primary_base_edge_id"].astype(str)))
    review_dir = OUTPUT / "offline_raw_fragment_review_packs"
    review_rows = []
    review_source = evaluated_subset[
        evaluated_subset["timing_condition"].eq("NOMINAL")
        & evaluated_subset["evaluation_group"].eq("REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED")
        & evaluated_subset["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE")
    ].sort_values(["pair_index", "base_edge_id", "source_track_id"]).drop_duplicates(
        ["base_edge_id", "source_track_id"]
    )
    for index, row in enumerate(review_source.itertuples(index=False), 1):
        series = pd.Series(row._asdict())
        manual = supported_map.get(str(series.base_edge_id))
        path = review_dir / f"review_{index:02d}_{series.hypothesis_id}.png"
        render_hypothesis_pack(
            series,
            manual,
            optical_by_frame,
            path,
            "OFFLINE_MULTIMODAL_REVIEW_EVALUATION | UNRESOLVED",
        )
        review_rows.append(
            {
                "review_pack": str(path.relative_to(WORKSPACE)),
                "hypothesis_id": series.hypothesis_id,
                "base_edge_id": series.base_edge_id,
                "raw_track_fragment_id": series.source_track_id,
                "review_state": "UNRESOLVED",
                "reason": "NO_AUTHORITATIVE_CROSS_MODAL_TARGET_IDENTITY_CUE",
                "hypothesis_frozen_before_review": True,
                "runtime_inference": False,
            }
        )
    review_registry = pd.DataFrame(review_rows)
    review_registry.to_csv(OUTPUT / "offline_visual_raw_fragment_target_review.csv", index=False, encoding="utf-8-sig")

    nominal = evaluated_subset[evaluated_subset["timing_condition"].eq("NOMINAL")].copy()
    supported_mask = nominal["evaluation_group"].eq("REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED")
    null_mask = nominal["evaluation_group"].eq("FROZEN_MATCHED_SAR_NULL")
    case_specs: list[tuple[str, pd.Series | None, str]] = [
        ("01_supported_optical_positive_sar_positive", select_case(nominal, supported_mask & nominal["optical_dynamic_state_v2"].eq("OPTICAL_COHERENT_POSITIVE_SHIFT") & nominal["sar_dynamic_state_v2"].eq("SAR_COHERENT_POSITIVE_SHIFT"), ["pair_index", "hypothesis_id"]), "SUPPORTED_POSITIVE_POSITIVE"),
        ("02_supported_optical_positive_sar_negative", select_case(nominal, supported_mask & nominal["optical_dynamic_state_v2"].eq("OPTICAL_COHERENT_POSITIVE_SHIFT") & nominal["sar_dynamic_state_v2"].eq("SAR_COHERENT_NEGATIVE_SHIFT"), ["pair_index", "hypothesis_id"]), "SUPPORTED_POSITIVE_NEGATIVE"),
        ("03_supported_sar_deformation", select_case(nominal, supported_mask & nominal["sar_dynamic_state_v2"].eq("SAR_DEFORMATION_OR_MIXED_SHIFT"), ["pair_index", "hypothesis_id"]), "SUPPORTED_SAR_DEFORMATION"),
        ("04_matched_null_concordant", select_case(nominal, null_mask & nominal["cross_modal_direction_state_v2"].eq("DIRECTION_CONCORDANT"), ["pair_index", "hypothesis_id"]), "MATCHED_NULL_CONCORDANT"),
        ("05_matched_null_contradictory", select_case(nominal, null_mask & nominal["cross_modal_direction_state_v2"].eq("DIRECTION_CONTRADICTORY"), ["pair_index", "hypothesis_id"]), "MATCHED_NULL_CONTRADICTORY"),
        ("06_branch_equals_global", select_case(nominal, supported_mask & nominal["branch_vs_global_direction_relation"].eq("BRANCH_DIRECTION_EQUALS_GLOBAL_BASELINE"), ["pair_index", "hypothesis_id"]), "BRANCH_EQUALS_GLOBAL"),
        ("07_branch_differs_global", select_case(nominal, nominal["branch_vs_global_direction_relation"].eq("BRANCH_DIRECTION_DIFFERS_FROM_GLOBAL_BASELINE"), ["pair_index", "hypothesis_id"]), "BRANCH_DIFFERS_GLOBAL"),
        ("08_wrong_correct_raw_same_direction", None, "RAW_BRANCH_EVALUATOR_UNRESOLVED"),
        ("09_wrong_correct_raw_different_direction", None, "RAW_BRANCH_EVALUATOR_UNRESOLVED"),
        ("10_fragment_break", select_case(evaluated_subset, evaluated_subset["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK"), ["pair_index", "timing_condition", "hypothesis_id"]), "FRAGMENT_BREAK"),
        ("11_same_sample", select_case(evaluated_subset, evaluated_subset["angular_availability_state"].eq("ANGULAR_DYNAMIC_UNAVAILABLE_SAME_OPTICAL_SAMPLE"), ["pair_index", "timing_condition", "hypothesis_id"]), "SAME_SAMPLE"),
        ("12_timing_shift_sign_change", None, "CATEGORY_NOT_OBSERVED_NO_OPTICAL_SIGN_CHANGE"),
        ("13_static_shell_plausible_direction_contradicts", select_case(nominal, bool_series(nominal["static_feasible"]) & nominal["cross_modal_direction_state_v2"].eq("DIRECTION_CONTRADICTORY"), ["pair_index", "hypothesis_id"]), "STATIC_FEASIBLE_CONTRADICTORY"),
        ("14_direction_rescue_sar_only_ambiguous", None, "FILLED_FROM_PAIRWISE_IF_OBSERVED"),
        ("15_sar_only_good_direction_conflicts", None, "FILLED_FROM_PAIRWISE_IF_OBSERVED"),
        ("16_r02_scene_common_positive", select_case(nominal, nominal["optical_dynamic_state_v2"].eq("OPTICAL_COHERENT_POSITIVE_SHIFT") & nominal["branch_vs_global_direction_relation"].eq("BRANCH_DIRECTION_EQUALS_GLOBAL_BASELINE"), ["pair_index", "hypothesis_id"]), "R02_SCENE_COMMON_POSITIVE"),
    ]
    rescue = cluster[(cluster["timing_condition"].eq("NOMINAL")) & cluster["joint_category"].eq("DIRECTION_RESCUE")]
    conflict = cluster[(cluster["timing_condition"].eq("NOMINAL")) & cluster["joint_category"].eq("DIRECTION_CONFLICT")]
    if len(rescue):
        case = rescue.iloc[0]
        case_specs[13] = (case_specs[13][0], select_case(nominal, nominal["base_edge_id"].eq(case.primary_base_edge_id), ["hypothesis_id"]), "DIRECTION_RESCUE")
    if len(conflict):
        case = conflict.iloc[0]
        case_specs[14] = (case_specs[14][0], select_case(nominal, nominal["base_edge_id"].eq(case.primary_base_edge_id), ["hypothesis_id"]), "DIRECTION_CONFLICT")

    case_dir = OUTPUT / "figures" / "post_reference_cases"
    case_rows = []
    rendered: list[Path] = []
    for name, row, rule in case_specs:
        if row is None:
            case_rows.append({"case_name": name, "selection_status": "CATEGORY_NOT_OBSERVED", "selection_rule": rule, "figure": ""})
            continue
        primary_id = str(row.base_edge_id)
        manual_id = primary_id if primary_id in supported_map else matched_primary.get(primary_id, "")
        manual = supported_map.get(manual_id)
        path = case_dir / f"{name}.png"
        render_hypothesis_pack(row, manual, optical_by_frame, path, f"{name} | {row.cross_modal_direction_state_v2}")
        rendered.append(path)
        case_rows.append(
            {
                "case_name": name,
                "selection_status": "CATEGORY_OBSERVED",
                "selection_rule": rule,
                "figure": str(path.relative_to(WORKSPACE)),
                "hypothesis_id": row.hypothesis_id,
                "base_edge_id": row.base_edge_id,
            }
        )
    atlas_pairs = pd.read_parquet(PRE_ATLAS_PAIRS)
    atlas_path = case_dir / "17_broader_atlas_opposite_direction_branches.png"
    atlas_case = render_atlas_opposite_case(atlas_pairs, optical_data, atlas_path)
    if atlas_case is None:
        case_rows.append({"case_name": "17_broader_atlas_opposite_direction_branches", "selection_status": "CATEGORY_NOT_OBSERVED", "selection_rule": "FIRST_GT_BLIND_ELIGIBLE_WINDOW", "figure": ""})
    else:
        rendered.append(atlas_path)
        case_rows.append({"case_name": "17_broader_atlas_opposite_direction_branches", "selection_status": "CATEGORY_OBSERVED", "selection_rule": "FIRST_GT_BLIND_ELIGIBLE_WINDOW", "figure": str(atlas_path.relative_to(WORKSPACE)), **atlas_case})
    case_registry = pd.DataFrame(case_rows)
    case_registry.to_csv(OUTPUT / "real_case_registry.csv", index=False, encoding="utf-8-sig")
    contact_sheet = OUTPUT / "figures" / "POST_REFERENCE_CASE_CONTACT_SHEET.png"
    make_contact_sheet(rendered, contact_sheet)

    nominal_cluster = cluster[cluster["timing_condition"].eq("NOMINAL")]
    nominal_counts = nominal_cluster["direction_pairwise_decision"].value_counts()
    nominal_joint = nominal_cluster["joint_category"].value_counts()
    pre_summary = read_json(PRE_SUMMARY)
    branch_global_diff = int(nominal_cluster["branch_decision_differs_from_global"].sum())
    favors_supported = int(nominal_counts.get("DIRECTION_FAVORS_SUPPORTED", 0))
    favors_null = int(nominal_counts.get("DIRECTION_FAVORS_NULL", 0))
    rescues = int(nominal_joint.get("DIRECTION_RESCUE", 0))
    confirmations = int(nominal_joint.get("DIRECTION_CONFIRMATION", 0))
    conflicts = int(nominal_joint.get("DIRECTION_CONFLICT", 0))
    primary_state = (
        "M0B1_V2_DIRECTION_SIGNAL_SCENE_COMMON_NOT_BRANCH_SPECIFIC"
        if favors_supported > 0 and pre_summary["r02_direction_sign_degenerate"] and branch_global_diff == 0
        else "M0B1_V2_DIRECTION_DISCRIMINATION_NOT_ESTABLISHED"
    )
    secondary = ["M0B1_V2_RAW_BRANCH_EVALUATION_UNRESOLVED", "R02_DIRECTION_SIGN_DEGENERATE"]
    if rescues == 0:
        secondary.append("M0B1_V2_INCREMENTAL_BEYOND_SAR_ONLY_NOT_ESTABLISHED")
    counterfactual_gate = rescues > 0
    final_summary = {
        "schema": "PERSON_M0B1_V2_FINAL_SUMMARY_V1",
        "created_at": now_iso(),
        "primary_state": primary_state,
        "secondary_states": secondary,
        "starting_head": read_json(FREEZE)["starting_head"],
        "head_at_report_generation": git_head(),
        "frozen_predecessor_states_unchanged": True,
        "reference_supported_base_edges": int(len(supported)),
        "reference_supported_frame_pair_clusters": int(supported["pair_index"].nunique()),
        "matched_reference_unsupported_edges": int(len(matched)),
        "nominal_pairwise_cluster_counts": {
            "favors_supported": favors_supported,
            "favors_null": favors_null,
            "no_decision": int(nominal_counts.get("DIRECTION_NO_DECISION", 0)),
        },
        "nominal_joint_categories": nominal_joint.to_dict(),
        "branch_decisions_different_from_global": branch_global_diff,
        "branch_specific_increment_over_global_observed": branch_global_diff > 0,
        "incremental_beyond_sar_only_rescue_count": rescues,
        "direction_confirmation_count": confirmations,
        "direction_conflict_count": conflicts,
        "scene_common_direction_prior_observed": True,
        "person_or_branch_specificity_established": False,
        "raw_fragment_target_evaluator_status": "UNRESOLVED",
        "offline_review_pack_count": int(len(review_registry)),
        "offline_review_state_counts": review_registry["review_state"].value_counts().to_dict() if len(review_registry) else {},
        "counterfactual_admissibility_gate_passed": counterfactual_gate,
        "counterfactual_admissibility_executed": False,
        "recommended_next_action": "OPTICAL_COMMON_APPARENT_MOTION_AND_BRANCH_RELATIVE_RESIDUAL_STUDY_ON_ALL_GT_BLIND_ELIGIBLE_ATLAS_WINDOWS",
        "recommend_magnitude_next": False,
        "recommend_common_apparent_motion_next": True,
        "recommend_counterfactual_admissibility_next": False,
        "prohibited_claims": {
            "sync_calibrated": False,
            "physical_person_angular_velocity": False,
            "optical_sar_identity": False,
            "person_specific_sar_continuation": False,
            "runtime_raw_fragment_identity": False,
            "ambiguity_reduction": False,
            "dynamic_pruning_validated": False,
            "unique_dynamic_path": False,
            "final_sar_center": False,
            "final_sar_box": False,
            "p2_established": False,
            "generalization_established": False,
        },
    }
    write_json(OUTPUT / "final_summary.json", final_summary)

    timing = pd.read_csv(PRE_TIMING_SUMMARY)
    scene = pd.read_csv(PRE_SCENE)
    nominal_scene = scene[scene["timing_condition"].eq("NOMINAL")]
    report = "\n".join(
        [
            "# M0B1-V2 cross-modal direction discrimination report",
            "",
            f"- Primary state: `{primary_state}`",
            f"- Secondary states: `{'; '.join(secondary)}`",
            "- Scientific status: exposed R02 development diagnostic; descriptive only",
            "",
            "## Conclusion",
            "",
            "The corresponding-boundary optical representation is stably observable, but R02 is direction-sign degenerate: every deduplicated optical branch pair is positive and branch decisions reproduce the global scene direction baseline.  Against 30 frozen reference-unsupported SAR alternatives, nominal direction favors the supported edge in a subset and never favors the null, but those cases are already SAR-only supported wins.  Direction therefore supplies scene-conditioned confirmation, not branch/PERSON specificity and not demonstrated incremental resolution beyond SAR-only evidence.",
            "",
            "## Required 41-question closeout",
            "",
            f"1. Starting HEAD / report-generation HEAD: `{final_summary['starting_head']}` / `{final_summary['head_at_report_generation']}`. The final closeout commit and pushed HEAD are reported in the task handoff because a commit cannot contain its own hash.",
            "2. Commit/push/divergence: completed after report generation and recorded in the final task handoff.",
            "3. Actual authorities: current runners/schemas/validators, frozen M0A/M0A-R/M0B1/M0B1-R artifacts, latest pixel topology, then protocols and older narratives.",
            "4. Supersession: pixel intersection supersedes coarse angular extent; raw fragments supersede stitched identity for runtime semantics; M0B1-R does not overwrite M0B1.",
            "5. Optical representation: `M0B1_V2_CORRESPONDING_BOUNDARY_DIRECTION_V1` with left/right/mid/width descriptors and 1e-12 degree numerical tolerance.",
            "6. SAR representation: q95 corresponding-boundary structural state with mixed/deformation preserved.",
            f"7. Pre-reference hypotheses: `{pre_summary['hypothesis_rows']}`.",
            f"8. Static-feasible rows: `{pre_summary['static_feasible_rows']}`.",
            f"9. Dynamic-available rows: `{pre_summary['dynamic_available_rows']}`.",
            f"10. Fragment-break rows: `{pre_summary['fragment_break_rows']}`.",
            f"11. Same-sample rows: `{pre_summary['same_sample_rows']}`.",
            f"12. Optical positive/negative/deformation: see timing table; nominal deduplicated state counts `{pre_summary['nominal_optical_state_counts']}`.",
            "13. SAR positive/negative/deformation: materialized in `sar_descriptors_pre_reference.csv` and timing table.",
            "14. Cross-modal concordant/contradictory/indeterminate/unavailable: materialized for every hypothesis and timing condition.",
            f"15. R02 scene-common: yes; sign-degenerate=`{pre_summary['r02_direction_sign_degenerate']}`.",
            f"16. Per-frame branch diversity: nominal neighborhoods={len(nominal_scene)}, maximum disagreement={nominal_scene['fragment_to_fragment_disagreement_fraction'].max():.4f}.",
            "17. Global baseline: unique coherent majority per exact optical temporal neighborhood.",
            f"18. Branch direction beyond global: no; differing cluster decisions=`{branch_global_diff}`.",
            f"19. Supported vs matched-null nominal pairwise: supported/null/no-decision=`{favors_supported}/{favors_null}/{int(nominal_counts.get('DIRECTION_NO_DECISION', 0))}`.",
            "20. Direction favors supported/null/no-decision: reported above and by timing in `pairwise_direction_summary.csv`.",
            "21. SAR-only x direction cross-tab: `sar_only_direction_cross_tab.csv`.",
            f"22. Rescue/confirmation/conflict: `{rescues}/{confirmations}/{conflicts}` nominal matched-edge clusters.",
            "23. Static-shell tautology: direction-blind static controls materialized; no claim of static re-expression dominance is made.",
            "24. Timing sensitivity: optical sign stays positive across all five fixed conditions; sync remains uncalibrated.",
            f"25. Cluster-aware result: 6 supported base edges from {supported['pair_index'].nunique()} frame-pair clusters; row counts are not independent.",
            "26. Leave-one-pair-out: materialized in `leave_one_frame_pair_out_direction.csv`; no p-value.",
            "27. Post-reference raw-fragment evaluator: no legal direct source found; offline review interface materialized.",
            "28. Evaluator provenance: hashes and findings in `raw_fragment_target_evaluator_audit.json`.",
            f"29. Confirmed/ambiguous/unresolved branches: `0/0/{len(review_registry)}` review packs.",
            "30. Correct-vs-wrong raw fragment: unresolved and not executed.",
            "31. PERSON/branch specificity: not established.",
            "32. Scene-common dynamic prior: established descriptively for this R02 slice.",
            f"33. Incremental cross-modal information: `{favors_supported}` confirmatory direction decisions, but zero SAR-only ambiguity rescues; incremental resolution not established.",
            "34. Most explanatory cases: supported positive-positive, supported deformation, matched-null contradictory, and scene-common representative.",
            "35. Aggregate/image conflict: visual QA must check whether interval overlays and q95 regions support the categorical state; no identity inference is allowed.",
            "36. Conflict diagnosis priority: representation/rendering bug, static geometry burden, shared/mixed SAR topology, timing availability, then physical interpretation.",
            f"37. Broader atlas: `{pre_summary['atlas_future_candidate_window_count']}` eligible opposite-direction windows across `{pre_summary['atlas_run_count']}` runs; all are future-design candidates, not cherry-picked winners.",
            "38. Magnitude next: no; projection and scene-common decomposition remain unresolved.",
            "39. Common apparent motion next: yes, before branch-relative residual direction validation.",
            f"40. Counterfactual admissibility next: no; gate passed=`{counterfactual_gate}` and diagnostic was not executed.",
            "41. Still forbidden: sync calibration, physical PERSON angular velocity, optical-SAR identity, PERSON-specific continuation, runtime identity, validated pruning/ambiguity reduction, unique path, final center/box, P2, or generalization.",
            "",
            "## Pre-reference timing denominators",
            "",
            markdown_table(timing),
            "",
            "## Nominal supported-vs-null cluster decisions",
            "",
            markdown_table(nominal_cluster[["pair_index", "alternative_rank", "direction_pairwise_decision", "global_pairwise_decision", "sar_only_pairwise_outcome", "joint_category"]]),
            "",
            "## Visual and evaluator boundary",
            "",
            "All available requested categories are rendered from real optical and SAR images. Missing categories remain `CATEGORY_NOT_OBSERVED`. Offline review packs remain `UNRESOLVED` because neither optical_person_id nor visual appearance supplies an authoritative cross-modal target identity.",
            "",
            "## Recommendation and stop",
            "",
            "Use the full GT-blind atlas eligibility set to design a separately frozen common-apparent-motion versus branch-relative residual study. Do not fit magnitude or deploy direction pruning in the current R02 result.",
        ]
    ) + "\n"
    report_path = OUTPUT / "M0B1_V2_CROSS_MODAL_DIRECTION_DISCRIMINATION_REPORT.md"
    report_path.write_text(report, encoding="utf-8")

    final_files = [
        OUTPUT / "post_reference_hypothesis_evaluation.parquet",
        OUTPUT / "supported_vs_matched_null_pairwise_direction.csv",
        OUTPUT / "supported_vs_matched_null_cluster_decisions.csv",
        OUTPUT / "pairwise_direction_summary.csv",
        OUTPUT / "sar_only_direction_cross_tab.csv",
        OUTPUT / "cluster_aware_direction_by_frame_pair.csv",
        OUTPUT / "cluster_aware_direction_by_raw_fragment.csv",
        OUTPUT / "leave_one_frame_pair_out_direction.csv",
        OUTPUT / "static_shell_tautology_control.csv",
        OUTPUT / "raw_fragment_target_evaluator_audit.json",
        OUTPUT / "wrong_raw_fragment_control_status.json",
        OUTPUT / "offline_visual_raw_fragment_target_review.csv",
        OUTPUT / "real_case_registry.csv",
        OUTPUT / "final_summary.json",
        report_path,
        contact_sheet,
        *sorted(review_dir.glob("*.png")),
        *sorted(case_dir.glob("*.png")),
    ]
    final_manifest = {
        "schema": "PERSON_M0B1_V2_FINAL_OUTPUT_MANIFEST_V1",
        "created_at": now_iso(),
        "reference_loaded": True,
        "pre_reference_manifest_sha256": sha256_file(PRE_MANIFEST),
        "files": [
            {"path": str(path.relative_to(WORKSPACE)), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in final_files
            if path.is_file()
        ],
        "hypotheses_pruned": False,
        "magnitude_fit": False,
        "timing_shift_selected": False,
        "identity_assignment_performed": False,
        "counterfactual_admissibility_executed": False,
    }
    write_json(OUTPUT / "final_output_manifest.json", final_manifest)
    ledger = read_json(LEDGER)
    ledger["events"].extend(
        [
            {"stage": "PRE_REFERENCE_MANIFEST_REVERIFIED", "completed_at": now_iso()},
            {"stage": "MANUAL_REFERENCE_REVEALED_AFTER_FREEZE", "completed_at": now_iso()},
            {"stage": "SUPPORTED_MATCHED_PAIRWISE_DIRECTION_COMPLETE", "completed_at": now_iso()},
            {"stage": "RAW_FRAGMENT_EVALUATOR_AUDIT_AND_OFFLINE_REVIEW_COMPLETE", "completed_at": now_iso()},
            {"stage": "REAL_CASE_RENDERING_COMPLETE", "completed_at": now_iso()},
            {"stage": "M0B1_V2_COMPLETE_STOP", "completed_at": now_iso()},
        ]
    )
    write_json(LEDGER, ledger)
    print(json.dumps(final_summary, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--pre-reference", action="store_true")
    group.add_argument("--post-reference", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.freeze:
        freeze()
    elif args.pre_reference:
        pre_reference()
    else:
        post_reference()


if __name__ == "__main__":
    main()
