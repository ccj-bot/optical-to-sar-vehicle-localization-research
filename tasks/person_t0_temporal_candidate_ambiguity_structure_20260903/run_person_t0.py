from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_t0_temporal_candidate_ambiguity_structure_20260903"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference_diagnostic_only"
PACK = WORKSPACE / "review_packs" / "PERSON_T0_TEMPORAL_CANDIDATE_AMBIGUITY_STRUCTURE_20260903"
PACK_ZIP = PACK.with_suffix(".zip")

R2_PRE = WORKSPACE / "output" / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830" / "pre_reference"
D0R_PRE = WORKSPACE / "output" / "person_terg_d0r_set_valued_graph_representation_repair_20260829" / "pre_reference"
R0_PRE = WORKSPACE / "output" / "person_terg_r0_set_valued_explanation_constraint_propagation_20260829" / "pre_reference"
RANGE_PRE = WORKSPACE / "output" / "person_range_temporal_decision_study_20260830" / "pre_reference"
B0_PRE = WORKSPACE / "output" / "person_b0_end_to_end_capability_and_bottleneck_study_20260830" / "pre_reference"
B0_POST = WORKSPACE / "output" / "person_b0_end_to_end_capability_and_bottleneck_study_20260830" / "post_reference_oracle_diagnostic_only"
OPTICAL_PATH = WORKSPACE / "output" / "person_optical_guided_sar_annotation_full_20260823" / "optical_person_frame_hypotheses.parquet"

FRAME_REGISTRY = R2_PRE / "full_stream_frame_registry_pre_reference.parquet"
Q95_REGIONS = R2_PRE / "full_stream_q95_response_regions_pre_reference.parquet"
Q95_MASKS = R2_PRE / "full_stream_q95_masks"
SHELLS = R2_PRE / "full_stream_optical_shells_pre_reference.parquet"
SHELL_EDGES = R2_PRE / "full_stream_shell_q95_pixel_edges_pre_reference.parquet"
RUNTIME_FAMILIES = R2_PRE / "runtime_candidate_family_membership_pre_reference.parquet"
LIFECYCLE = R2_PRE / "full_stream_hypothesis_lifecycle_pre_reference.parquet"
P0_AVAILABILITY = R2_PRE / "full_stream_frozen_p0_availability_pre_reference.parquet"
P0_EDGES = R2_PRE / "full_stream_available_frozen_p0_q95_edges_pre_reference.parquet"
P0_MODELS = B0_PRE / "full_stream_p0_models.jsonl"
STRICT_MEMBERSHIP = RANGE_PRE / "global_mutual_dominant_p0_family_membership.parquet"
NATURAL_EVENTS = RANGE_PRE / "all_natural_corridor_family_frame_events.parquet"
MATCHED_NULL_TOP = RANGE_PRE / "r03_source_and_matched_null_top_family_records.parquet"
MATCHED_NULL_CONTROLS = RANGE_PRE / "r03_matched_null_control_ledger.csv"
D0R_FAMILIES = D0R_PRE / "admissible_component_families_pre_reference.parquet"
D0R_MEMBERSHIP = D0R_PRE / "component_family_membership_pre_reference.parquet"
D0R_EDGES = D0R_PRE / "set_valued_physical_temporal_edges_pre_reference.parquet"
R1_FAMILY_DIAG = WORKSPACE / "output" / "person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829" / "pre_reference" / "response_component_family_diagnosis_pre_reference.parquet"
R0_BURDEN = R0_PRE / "segment_joint_world_burden_pre_reference.parquet"
R0_FAMILY_STATUS = R0_PRE / "family_domain_status_pre_reference.parquet"

REFERENCE = B0_POST / "r01_r02_r03_manual_range_reference_oracle_only.parquet"
FRAGMENT_TARGET_MAP = B0_POST / "raw_fragment_to_offline_target_mapping_oracle_only.csv"

RUNS = ("R01ZF", "R02ZF", "R03ZF")
MODE = "CAUSAL_REPLAY"

WINDOWS = [
    {
        "window_id": "W1_R01_SINGLE_AZIMUTH_SWEEP_F097_F112",
        "run_id": "R01ZF",
        "start_frame": 97,
        "end_frame": 112,
        "track_ids": ["R01ZF_REUSED_R01ZF_PERSON003"],
        "case_axes": "single currently observed optical fragment; large azimuth change; long-lived competing SAR support",
        "selection_rule": "fixed from pre-reference lifecycle and shell tables: PERSON003 is the only currently observed fragment while older hypotheses remain censored",
    },
    {
        "window_id": "W2_R03_SINGLE_WEAK_AZIMUTH_F458_F475",
        "run_id": "R03ZF",
        "start_frame": 458,
        "end_frame": 475,
        "track_ids": ["R03ZF_I01_T0004"],
        "case_axes": "single optical fragment; weak azimuth change; recurrence versus matched-null background compatibility",
        "selection_rule": "fixed from pre-reference shell/lifecycle tables and the pre-frozen R03 matched-null design; no PERSON reference used",
    },
    {
        "window_id": "W3_R02_TWO_TARGET_ENTRY_F469_F480",
        "run_id": "R02ZF",
        "start_frame": 469,
        "end_frame": 480,
        "track_ids": ["R02ZF_REUSED_R02ZF_PERSON017", "R02ZF_REUSED_R02ZF_PERSON018"],
        "case_axes": "two-target entry/approach; early P0 unavailability; shared candidate support",
        "selection_rule": "fixed from pre-reference lifecycle, shell, and P0 availability states to separate missing interface from candidate elimination",
    },
    {
        "window_id": "W4_R02_MULTI_TARGET_COMPETITION_F487_F494",
        "run_id": "R02ZF",
        "start_frame": 487,
        "end_frame": 494,
        "track_ids": [
            "R02ZF_REUSED_R02ZF_PERSON017",
            "R02ZF_REUSED_R02ZF_PERSON018",
            "R02ZF_REUSED_R02ZF_PERSON021",
            "R02ZF_REUSED_R02ZF_PERSON023",
            "R02ZF_REUSED_R02ZF_PERSON024",
        ],
        "case_axes": "five optical fragments; shared response; split/merge/deformation; identity permutation pressure",
        "selection_rule": "fixed from pre-reference current-observation and relation-overlap tables at the dense R02 stream ending",
    },
    {
        "window_id": "W5_R01_HIGH_BACKGROUND_TOPOLOGY_F048_F055",
        "run_id": "R01ZF",
        "start_frame": 48,
        "end_frame": 55,
        "track_ids": [
            "R01ZF_REUSED_R01ZF_PERSON001",
            "R01ZF_REUSED_R01ZF_PERSON002",
            "R01ZF_REUSED_R01ZF_PERSON003",
        ],
        "case_axes": "strong full-fan Q95 background; multi-region families; topology/deformation representation stress",
        "selection_rule": "fixed from pre-reference Q95 burden, set-valued family, and topology tables; not selected by reference retention",
    },
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: object) -> str:
    value = "|".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(value).hexdigest()[:20].upper()}"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_table(frame: pd.DataFrame, stem: Path, parquet: bool = True) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(stem.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    if parquet:
        frame.to_parquet(stem.with_suffix(".parquet"), index=False, compression="zstd")


def read_non_r04(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    try:
        frame = pd.read_parquet(path, columns=columns, filters=[("run_id", "in", list(RUNS))])
    except (ValueError, TypeError, KeyError):
        frame = pd.read_parquet(path, columns=columns)
        if "run_id" in frame.columns:
            frame = frame[frame["run_id"].isin(RUNS)].copy()
    if "run_id" in frame.columns and frame["run_id"].astype(str).str.contains("R04", case=False, na=False).any():
        raise RuntimeError(f"R04 row entered T0 input: {path}")
    return frame


def semicolon(values: Iterable[object]) -> str:
    return ";".join(sorted({str(value) for value in values if pd.notna(value) and str(value)}))


def parse_set(value: object) -> set[str]:
    if pd.isna(value) or not str(value):
        return set()
    return {item for item in str(value).split(";") if item}


def window_mask(frame: pd.DataFrame, window: dict[str, Any]) -> pd.Series:
    return (
        frame["run_id"].eq(window["run_id"])
        & frame["frame_index"].between(window["start_frame"], window["end_frame"])
    )


def analysis_contract() -> dict[str, Any]:
    return {
        "schema": "PERSON_T0_TEMPORAL_CANDIDATE_AMBIGUITY_STRUCTURE_V1",
        "construction_phase": "PRE_REFERENCE_ONLY",
        "scientific_question": "which frame-wise candidate explanations die from observable temporal/structural contradictions, which survive, and what independent observable remains absent",
        "allowed_runtime_evidence": [
            "optical raw fragment continuity and nominal timestamps",
            "optical azimuth corridor",
            "SAR Q95 image-domain response support",
            "frozen P0 common apparent transport",
            "set-valued SAR family structure and topology",
            "relative multi-target relation when observable",
        ],
        "forbidden_construction_evidence": [
            "SAR PERSON GT or manual PERSON reference",
            "oracle range",
            "manual cross-modal correspondence",
            "R04",
            "learned fusion or new classifier",
            "unique identity assignment, Hungarian matching, tracker score, final SAR center, or final SAR box",
        ],
        "semantics": {
            "P0": "common apparent transport, not PERSON motion or identity",
            "Q95": "SAR image-domain response support, not PERSON probability, segmentation, identity, or box",
            "optical": "nominal time, lifecycle, azimuth corridor, event support only",
            "SAR": "response graph, radial structure, and final-localization authority",
            "candidate_path": "set-valued feasible explanation, not a committed track",
        },
        "timing": "nominal index/FPS zero-offset proxy with unresolved cross-modal synchronization",
        "case_selection": "five windows fixed mechanically from pre-reference lifecycle, observability, Q95 burden, relation, and matched-null control interfaces",
        "historical_knowledge_caveat": "analyst is not outcome-naive; protection is code/data phase isolation plus hashed pre-reference freeze",
        "count_interpretation": "angle-region, causal-upper-family, and strict-mutual-core counts are non-nested representation views; differences are descriptive, not a monotonic tracker score",
    }


def load_pre_inputs() -> dict[str, pd.DataFrame]:
    frames = read_non_r04(FRAME_REGISTRY)
    frames = frames.rename(columns={"sar_frame_index": "frame_index"})
    data = {
        "frames": frames,
        "regions": read_non_r04(Q95_REGIONS),
        "shells": read_non_r04(SHELLS),
        "shell_edges": read_non_r04(SHELL_EDGES),
        "runtime_families": read_non_r04(RUNTIME_FAMILIES),
        "lifecycle": read_non_r04(LIFECYCLE),
        "p0_availability": read_non_r04(P0_AVAILABILITY),
        "p0_edges": read_non_r04(P0_EDGES),
        "strict_membership": read_non_r04(STRICT_MEMBERSHIP),
        "natural_events": read_non_r04(NATURAL_EVENTS),
        "d0r_families": read_non_r04(D0R_FAMILIES),
        "d0r_membership": read_non_r04(D0R_MEMBERSHIP),
        "d0r_edges": read_non_r04(D0R_EDGES),
        "r1_family_diag": read_non_r04(R1_FAMILY_DIAG),
        "r0_burden": read_non_r04(R0_BURDEN),
        "r0_family_status": read_non_r04(R0_FAMILY_STATUS),
    }
    data["optical"] = read_non_r04(OPTICAL_PATH)
    data["matched_null_top"] = read_non_r04(MATCHED_NULL_TOP)
    data["matched_null_controls"] = pd.read_csv(MATCHED_NULL_CONTROLS, encoding="utf-8-sig")
    for name, frame in data.items():
        if "run_id" in frame.columns and frame["run_id"].astype(str).str.contains("R04", case=False, na=False).any():
            raise RuntimeError(f"R04 entered {name}")
    return data


def selected_frames() -> set[tuple[str, int]]:
    return {
        (window["run_id"], frame)
        for window in WINDOWS
        for frame in range(window["start_frame"], window["end_frame"] + 1)
    }


def build_input_manifest(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    table_inputs = [
        (FRAME_REGISTRY, "SAR frame and raw-image registry"),
        (Q95_REGIONS, "full-stream Q95 region geometry"),
        (SHELLS, "causal optical azimuth corridors"),
        (SHELL_EDGES, "angle-admitted Q95 region incidences"),
        (RUNTIME_FAMILIES, "causal upper-possible P0 connectivity families"),
        (LIFECYCLE, "runtime optical-fragment lifecycle and interface state"),
        (P0_AVAILABILITY, "frozen P0 availability"),
        (P0_EDGES, "frozen P0-supported Q95 edges"),
        (P0_MODELS, "frozen P0 translations for before/after review"),
        (STRICT_MEMBERSHIP, "strict mutual-dominant P0 core families"),
        (NATURAL_EVENTS, "natural-corridor strict-family observations"),
        (MATCHED_NULL_TOP, "pre-frozen R03 matched-null recurrence results"),
        (MATCHED_NULL_CONTROLS, "pre-frozen R03 matched-null selection ledger"),
        (D0R_FAMILIES, "TERG-v1 upper-possible component families"),
        (D0R_MEMBERSHIP, "TERG-v1 family membership"),
        (D0R_EDGES, "TERG-v1 set-valued topology and optional bridges"),
        (R1_FAMILY_DIAG, "set-valued family representation diagnosis"),
        (R0_BURDEN, "multi-target joint-world relation burden"),
        (R0_FAMILY_STATUS, "R0 family-domain status and non-deletion evidence"),
        (OPTICAL_PATH, "raw optical fragment observations and image paths"),
    ]
    rows: list[dict[str, Any]] = []
    for path, role in table_inputs:
        if not path.exists():
            raise FileNotFoundError(path)
        rows.append({
            "input_kind": "TABLE_OR_MODEL",
            "path": str(path),
            "role": role,
            "scope_filter": "run_id in {R01ZF,R02ZF,R03ZF}; selected windows/tracks only",
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    frames = data["frames"].set_index(["run_id", "frame_index"])
    optical = data["optical"]
    for run_id, frame_index in sorted(selected_frames()):
        meta = frames.loc[(run_id, frame_index)]
        sar_path = Path(str(meta.sar_image_path))
        mask_path = Q95_MASKS / f"{run_id}_SARF{frame_index:06d}.npz"
        optical_index = int(meta.nominal_optical_frame_index)
        run_optical = optical[optical["run_id"].eq(run_id)]
        root = Path(str(run_optical.iloc[0].optical_image_path)).parent
        optical_matches = sorted(root.glob(f"frame_{optical_index:06d}_t*ms.jpg"))
        if not optical_matches:
            raise FileNotFoundError(f"optical frame {run_id} {optical_index} under {root}")
        for kind, path, role in [
            ("RAW_SAR_IMAGE", sar_path, "real SAR visual review"),
            ("Q95_MASK", mask_path, "Q95 component contour review"),
            ("RAW_OPTICAL_IMAGE", optical_matches[0], "optical bbox and lifecycle visual review"),
        ]:
            if not path.exists():
                raise FileNotFoundError(path)
            rows.append({
                "input_kind": kind,
                "path": str(path),
                "role": role,
                "scope_filter": f"{run_id} frame {frame_index}",
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    manifest = pd.DataFrame(rows).drop_duplicates(["path", "role"]).sort_values(["input_kind", "path"]).reset_index(drop=True)
    if manifest["path"].astype(str).str.contains("R04", case=False, na=False).any():
        raise RuntimeError("R04 path entered input manifest")
    return manifest


def p0_models() -> dict[tuple[str, int, int], dict[str, Any]]:
    models: dict[tuple[str, int, int], dict[str, Any]] = {}
    with P0_MODELS.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("run_id") not in RUNS or int(row.get("lag", 1)) != 1:
                continue
            models[(str(row["run_id"]), int(row["from_frame"]), int(row["to_frame"]))] = row
    return models


def track_frames(window: dict[str, Any], shells: pd.DataFrame, track_id: str) -> list[int]:
    subset = shells[
        shells["run_id"].eq(window["run_id"])
        & shells["mode"].eq(MODE)
        & shells["track_id"].eq(track_id)
        & shells["frame_index"].between(window["start_frame"], window["end_frame"])
    ]
    return sorted(subset["frame_index"].astype(int).unique().tolist())


def build_window_registry(data: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    windows: list[dict[str, Any]] = []
    tracks: list[dict[str, Any]] = []
    shells = data["shells"]
    lifecycle = data["lifecycle"]
    p0 = data["p0_availability"]
    regions = data["regions"]
    shell_edges = data["shell_edges"]
    for window in WINDOWS:
        selected = set(window["track_ids"])
        run_id, start, end = window["run_id"], window["start_frame"], window["end_frame"]
        life = lifecycle[
            lifecycle["run_id"].eq(run_id)
            & lifecycle["mode"].eq(MODE)
            & lifecycle["frame_index"].between(start, end)
        ]
        observed = sorted(life.loc[life["current_optical_state"].eq("OBSERVED"), "runtime_optical_fragment_id"].astype(str).unique())
        p0w = p0[p0["run_id"].eq(run_id) & p0["source_sar_frame"].between(start, end - 1)]
        regw = regions[regions["run_id"].eq(run_id) & regions["frame_index"].between(start, end)]
        edgesw = shell_edges[
            shell_edges["run_id"].eq(run_id)
            & shell_edges["mode"].eq(MODE)
            & shell_edges["track_id"].isin(selected)
            & shell_edges["frame_index"].between(start, end)
        ]
        windows.append({
            **{key: window[key] for key in ["window_id", "run_id", "start_frame", "end_frame", "case_axes", "selection_rule"]},
            "frame_count": end - start + 1,
            "selected_track_count": len(selected),
            "selected_track_ids": semicolon(selected),
            "currently_observed_track_ids_in_window": semicolon(observed),
            "p0_available_pair_count": int(p0w["p0_model_available"].sum()),
            "p0_unavailable_pair_count": int((~p0w["p0_model_available"].astype(bool)).sum()),
            "median_full_fan_q95_region_count": float(regw.groupby("frame_index")["region_id"].nunique().median()),
            "median_selected_angle_region_count": float(edgesw.groupby("frame_index")["region_id"].nunique().median()),
            "construction_reference_used": False,
            "r04_used": False,
        })
        for track_id in window["track_ids"]:
            sw = shells[
                shells["run_id"].eq(run_id)
                & shells["mode"].eq(MODE)
                & shells["track_id"].eq(track_id)
                & shells["frame_index"].between(start, end)
            ].sort_values("frame_index")
            if sw.empty:
                raise RuntimeError(f"selected track has no causal shell: {window['window_id']} {track_id}")
            centers = sw["effective_intervals_json"].map(lambda value: float(np.mean(json.loads(value)[0])))
            tracks.append({
                "window_id": window["window_id"],
                "run_id": run_id,
                "track_id": track_id,
                "first_shell_frame": int(sw["frame_index"].min()),
                "last_shell_frame": int(sw["frame_index"].max()),
                "shell_frame_count": int(sw["frame_index"].nunique()),
                "theta_center_start_deg": float(centers.iloc[0]),
                "theta_center_end_deg": float(centers.iloc[-1]),
                "theta_center_change_deg": float(centers.iloc[-1] - centers.iloc[0]),
                "median_corridor_width_deg": float(sw["effective_width_deg"].median()),
                "track_enters_inside_window": bool(int(sw["frame_index"].min()) > start),
                "manual_reference_used": False,
            })
    return pd.DataFrame(windows), pd.DataFrame(tracks)


def build_candidate_evolution(data: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    shell_edges = data["shell_edges"]
    runtime = data["runtime_families"]
    strict = data["strict_membership"]
    lifecycle = data["lifecycle"]
    shells = data["shells"]
    regions = data["regions"]

    all_rows: list[pd.DataFrame] = []
    frame_rows: list[dict[str, Any]] = []
    geom = regions[[
        "run_id", "frame_index", "region_id", "pixel_count", "area_m2", "range_min_m", "range_max_m",
        "theta_min_deg", "theta_max_deg", "touches_observable_boundary", "has_truncated_support", "structure_state",
    ]]
    for window in WINDOWS:
        for track_id in window["track_ids"]:
            base = shell_edges[
                shell_edges["run_id"].eq(window["run_id"])
                & shell_edges["mode"].eq(MODE)
                & shell_edges["track_id"].eq(track_id)
                & shell_edges["frame_index"].between(window["start_frame"], window["end_frame"])
            ].copy()
            base = base.merge(
                runtime[
                    runtime["run_id"].eq(window["run_id"])
                    & runtime["mode"].eq(MODE)
                    & runtime["track_id"].eq(track_id)
                ][["run_id", "frame_index", "track_id", "region_id", "family_id"]].rename(columns={"family_id": "causal_upper_family_id"}),
                on=["run_id", "frame_index", "track_id", "region_id"], how="left", validate="one_to_one",
            )
            base = base.merge(
                strict[["run_id", "frame_index", "region_id", "strict_family_id"]],
                on=["run_id", "frame_index", "region_id"], how="left", validate="many_to_one",
            )
            base = base.merge(geom, on=["run_id", "frame_index", "region_id"], how="left", validate="many_to_one", suffixes=("", "_geom"))
            if base[["causal_upper_family_id", "strict_family_id"]].isna().any().any():
                raise RuntimeError(f"family mapping incomplete for {window['window_id']} {track_id}")
            base["window_id"] = window["window_id"]
            all_rows.append(base)

    rows = pd.concat(all_rows, ignore_index=True)
    share = (
        rows.groupby(["window_id", "run_id", "frame_index", "strict_family_id"])["track_id"]
        .agg(shared_track_count="nunique", shared_track_ids=semicolon)
        .reset_index()
    )
    rows = rows.merge(share, on=["window_id", "run_id", "frame_index", "strict_family_id"], how="left")
    rows["identity_competition_observed"] = rows["shared_track_count"].gt(1)

    for window in WINDOWS:
        for track_id in window["track_ids"]:
            frames = track_frames(window, shells, track_id)
            life = lifecycle[
                lifecycle["run_id"].eq(window["run_id"])
                & lifecycle["mode"].eq(MODE)
                & lifecycle["runtime_optical_fragment_id"].eq(track_id)
            ].set_index("frame_index")
            sw = shells[
                shells["run_id"].eq(window["run_id"])
                & shells["mode"].eq(MODE)
                & shells["track_id"].eq(track_id)
            ].set_index("frame_index")
            subset = rows[rows["window_id"].eq(window["window_id"]) & rows["track_id"].eq(track_id)]
            for frame_index in frames:
                frame = subset[subset["frame_index"].eq(frame_index)]
                strict_groups = frame.groupby("strict_family_id")["region_id"].nunique() if len(frame) else pd.Series(dtype=int)
                current = life.loc[frame_index] if frame_index in life.index else None
                shell = sw.loc[frame_index]
                frame_rows.append({
                    "window_id": window["window_id"],
                    "run_id": window["run_id"],
                    "track_id": track_id,
                    "frame_index": frame_index,
                    "angle_region_count": int(frame["region_id"].nunique()),
                    "causal_upper_family_count": int(frame["causal_upper_family_id"].nunique()),
                    "strict_mutual_core_family_count": int(frame["strict_family_id"].nunique()),
                    "multi_region_strict_family_count": int((strict_groups > 1).sum()),
                    "shared_strict_family_count": int(frame.loc[frame["shared_track_count"].gt(1), "strict_family_id"].nunique()),
                    "angle_region_set": semicolon(frame["region_id"]),
                    "causal_upper_family_set": semicolon(frame["causal_upper_family_id"]),
                    "strict_mutual_core_family_set": semicolon(frame["strict_family_id"]),
                    "current_optical_state": "UNAVAILABLE" if current is None else str(current.current_optical_state),
                    "lifecycle_state": "UNAVAILABLE" if current is None else str(current.lifecycle_state),
                    "sar_p0_interface_state": "UNAVAILABLE" if current is None else str(current.sar_p0_interface_state),
                    "effective_intervals_json": str(shell.effective_intervals_json),
                    "corridor_width_deg": float(shell.effective_width_deg),
                    "count_comparison_semantics": "NON_NESTED_REPRESENTATION_VIEWS_NOT_MONOTONIC_TRACKER_ABLATION",
                })
    event_columns = [
        "window_id", "run_id", "track_id", "frame_index", "region_id", "strict_family_id", "causal_upper_family_id",
        "pixel_count", "area_m2", "range_min_m", "range_max_m", "theta_min_deg", "theta_max_deg", "structure_state",
        "touches_observable_boundary", "has_truncated_support", "shared_track_count", "shared_track_ids",
        "identity_competition_observed", "intersection_pixel_count", "region_coverage_fraction",
    ]
    return rows[event_columns].sort_values(["window_id", "track_id", "frame_index", "strict_family_id", "region_id"]), pd.DataFrame(frame_rows)


def build_family_ledger(events: pd.DataFrame, frame_evolution: pd.DataFrame, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    strict = data["strict_membership"]
    p0_availability = data["p0_availability"].set_index(["run_id", "source_sar_frame", "destination_sar_frame"])
    p0_edges = data["p0_edges"]
    rows: list[dict[str, Any]] = []
    for window in WINDOWS:
        for track_id in window["track_ids"]:
            frame_subset = frame_evolution[frame_evolution["window_id"].eq(window["window_id"]) & frame_evolution["track_id"].eq(track_id)]
            if frame_subset.empty:
                continue
            first_shell = int(frame_subset["frame_index"].min())
            last_shell = int(frame_subset["frame_index"].max())
            available_frames = set(frame_subset["frame_index"].astype(int))
            subset = events[events["window_id"].eq(window["window_id"]) & events["track_id"].eq(track_id)]
            candidate_next_by_frame = {
                int(frame): set(group["region_id"].astype(str))
                for frame, group in subset.groupby("frame_index")
            }
            for family_id, group in subset.groupby("strict_family_id", sort=False):
                group = group.sort_values("frame_index")
                seen_frames = sorted(group["frame_index"].astype(int).unique().tolist())
                first, last = seen_frames[0], seen_frames[-1]
                full_window_persistence = set(seen_frames) == available_frames
                late = first > first_shell
                region_ids_last = set(group.loc[group["frame_index"].eq(last), "region_id"].astype(str))
                representation = bool(group.groupby("frame_index")["region_id"].nunique().gt(1).any())
                topology_states: set[str] = set()
                family_region_ids = set(group["region_id"].astype(str))
                relevant_edges = p0_edges[
                    p0_edges["run_id"].eq(window["run_id"])
                    & (p0_edges["source_region_id"].isin(family_region_ids) | p0_edges["destination_region_id"].isin(family_region_ids))
                    & p0_edges["source_sar_frame"].between(first, max(first, last_shell - 1))
                ]
                topology_states.update(relevant_edges["sar_topology_state"].dropna().astype(str))
                if any(state != "P0_ONE_TO_ONE_LIKE" for state in topology_states):
                    representation = True

                optional_destinations: set[str] = set()
                detail = ""
                if last == last_shell:
                    status = "SURVIVED_TO_WINDOW_END"
                    detail = f"remained angle-compatible at the track's final reviewed shell frame F{last}; this is survival, not identity or localization"
                else:
                    next_frame = last + 1
                    key = (window["run_id"], last, next_frame)
                    p0_available = bool(p0_availability.loc[key].p0_model_available) if key in p0_availability.index else False
                    global_next = strict[
                        strict["run_id"].eq(window["run_id"])
                        & strict["strict_family_id"].eq(family_id)
                        & strict["frame_index"].eq(next_frame)
                    ]
                    next_candidates = candidate_next_by_frame.get(next_frame, set())
                    if not p0_available:
                        status = "P0_INTERFACE_UNAVAILABLE_CANNOT_DECIDE"
                        detail = f"strict observation ended at F{last}, but frozen P0 is unavailable for F{last}->F{next_frame}; absence cannot be called physical death"
                    elif len(global_next) and not set(global_next["region_id"].astype(str)).intersection(next_candidates):
                        status = "LEFT_AZIMUTH_CORRIDOR"
                        detail = f"the same strict full-fan family has support at F{next_frame}, but none intersects this optical corridor"
                    else:
                        optional = p0_edges[
                            p0_edges["run_id"].eq(window["run_id"])
                            & p0_edges["source_sar_frame"].eq(last)
                            & p0_edges["destination_sar_frame"].eq(next_frame)
                            & p0_edges["source_region_id"].isin(region_ids_last)
                            & p0_edges["destination_region_id"].isin(next_candidates)
                            & p0_edges["p0_supported_continuation"].astype(bool)
                        ]
                        optional_destinations = set(optional["destination_region_id"].astype(str))
                        if optional_destinations:
                            status = "STRICT_CORE_BREAK_BUT_UPPER_OPTIONAL_CONTINUATION"
                            detail = f"mutual-dominant core ended at F{last}, while {len(optional_destinations)} non-unique P0-compatible corridor destination(s) remain at F{next_frame}"
                        else:
                            status = "NO_STRICT_P0_CONTINUATION"
                            detail = f"with P0 available, neither the strict family nor an upper P0-compatible corridor continuation is present at F{next_frame}"

                secondary: list[str] = []
                if late:
                    secondary.append("LATE_APPEARANCE")
                if representation:
                    secondary.append("REPRESENTATION_FRAGMENTATION_OR_TOPOLOGY_AMBIGUITY")
                if window["run_id"] == "R03ZF" and full_window_persistence:
                    secondary.append("BACKGROUND_COMPATIBLE_PERSISTENCE")
                if int(group["shared_track_count"].max()) > 1:
                    secondary.append("MULTI_TARGET_IDENTITY_PERMUTATION_COMPATIBLE")
                rows.append({
                    "window_id": window["window_id"],
                    "run_id": window["run_id"],
                    "track_id": track_id,
                    "strict_family_id": family_id,
                    "first_observed_frame": first,
                    "last_observed_frame": last,
                    "admissible_frame_count": len(seen_frames),
                    "available_shell_frame_count": len(available_frames),
                    "temporal_span_frames": last - first + 1,
                    "window_occupancy": len(seen_frames) / len(available_frames),
                    "full_reviewed_shell_persistence": full_window_persistence,
                    "primary_status": status,
                    "secondary_statuses": semicolon(secondary),
                    "reason": detail,
                    "late_appearance": late,
                    "representation_fragmentation_or_topology_ambiguity": representation,
                    "topology_states": semicolon(topology_states),
                    "shared_with_other_selected_track": int(group["shared_track_count"].max()) > 1,
                    "maximum_shared_track_count": int(group["shared_track_count"].max()),
                    "touches_observable_boundary": bool(group["touches_observable_boundary"].any()),
                    "has_truncated_support": bool(group["has_truncated_support"].any()),
                    "theta_center_min_deg": float(((group["theta_min_deg"] + group["theta_max_deg"]) / 2).min()),
                    "theta_center_max_deg": float(((group["theta_min_deg"] + group["theta_max_deg"]) / 2).max()),
                    "range_center_min_m": float(((group["range_min_m"] + group["range_max_m"]) / 2).min()),
                    "range_center_max_m": float(((group["range_min_m"] + group["range_max_m"]) / 2).max()),
                    "optional_destination_region_count_at_break": len(optional_destinations),
                    "person_identity_claimed": False,
                    "final_localization_claimed": False,
                })
    return pd.DataFrame(rows).sort_values(["window_id", "track_id", "primary_status", "first_observed_frame", "strict_family_id"])


def build_ablation_ledger(frame_evolution: pd.DataFrame, family_ledger: pd.DataFrame, data: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for (window_id, run_id, track_id), group in frame_evolution.groupby(["window_id", "run_id", "track_id"], sort=False):
        ledger = family_ledger[family_ledger["window_id"].eq(window_id) & family_ledger["track_id"].eq(track_id)]
        rows.append({
            "window_id": window_id,
            "run_id": run_id,
            "track_id": track_id,
            "reviewed_frame_count": int(group["frame_index"].nunique()),
            "median_angle_region_count": float(group["angle_region_count"].median()),
            "median_causal_upper_family_count": float(group["causal_upper_family_count"].median()),
            "median_strict_mutual_core_family_count": float(group["strict_mutual_core_family_count"].median()),
            "median_shared_strict_family_count": float(group["shared_strict_family_count"].median()),
            "family_survived_to_window_end_count": int(ledger["primary_status"].eq("SURVIVED_TO_WINDOW_END").sum()),
            "family_left_corridor_count": int(ledger["primary_status"].eq("LEFT_AZIMUTH_CORRIDOR").sum()),
            "family_no_strict_continuation_count": int(ledger["primary_status"].eq("NO_STRICT_P0_CONTINUATION").sum()),
            "family_optional_continuation_count": int(ledger["primary_status"].eq("STRICT_CORE_BREAK_BUT_UPPER_OPTIONAL_CONTINUATION").sum()),
            "family_p0_unavailable_cannot_decide_count": int(ledger["primary_status"].eq("P0_INTERFACE_UNAVAILABLE_CANNOT_DECIDE").sum()),
            "information_removed_counterfactual": "azimuth-only permits frame-wise ridge switching; removing P0 continuity erases strict/optional break evidence; removing optical identity exposes shared-family permutation; removing topology hides representation fragmentation",
            "comparison_warning": "counts are non-nested representation views and cannot be interpreted as a monotonic score or tracker benchmark",
        })

    d0r_families = data["d0r_families"]
    diag = data["r1_family_diag"][[
        "family_id", "observed_frame_count", "max_physical_regions_per_frame", "multi_region_frame_count",
        "component_set_turnover_frame_count", "family_is_internally_set_valued", "response_bundle_semantics",
    ]]
    d0 = d0r_families.merge(diag, on="family_id", how="left", validate="one_to_one")
    d0_rows: list[pd.DataFrame] = []
    for window in WINDOWS:
        subset = d0[
            d0["run_id"].eq(window["run_id"])
            & d0["track_id"].isin(window["track_ids"])
            & d0["upper_end_sar_frame"].ge(window["start_frame"])
            & d0["upper_start_sar_frame"].le(window["end_frame"])
        ].copy()
        subset["window_id"] = window["window_id"]
        d0_rows.append(subset)
    d0_ledger = pd.concat(d0_rows, ignore_index=True) if d0_rows else pd.DataFrame()

    family_ranges = d0r_families.groupby(["segment_id", "run_id"], as_index=False).agg(
        segment_start_frame=("upper_start_sar_frame", "min"),
        segment_end_frame=("upper_end_sar_frame", "max"),
    )
    r0 = data["r0_burden"].merge(family_ranges, on=["segment_id", "run_id"], how="left", validate="one_to_one")
    status = data["r0_family_status"].groupby("segment_id", as_index=False).agg(
        possible_family_count=("family_id", "nunique"),
        excluded_family_count=("family_status", lambda values: int(pd.Series(values).astype(str).str.contains("EXCLUDED").sum())),
    )
    r0 = r0.merge(status, on="segment_id", how="left")
    relation_rows: list[pd.DataFrame] = []
    for window in WINDOWS:
        subset = r0[
            r0["run_id"].eq(window["run_id"])
            & r0["segment_end_frame"].ge(window["start_frame"])
            & r0["segment_start_frame"].le(window["end_frame"])
        ].copy()
        subset["window_id"] = window["window_id"]
        subset["relation_interpretation"] = np.where(
            subset["N_excluded_joint_worlds"].gt(0),
            "RELATION_REMOVES_JOINT_ASSIGNMENT_WORLDS_WITHOUT_PROVING_INDIVIDUAL_FAMILY_IDENTITY",
            "NO_RELATIONAL_CONTRACTION_IN_THIS_OVERLAPPING_SEGMENT",
        )
        relation_rows.append(subset)
    relation_ledger = pd.concat(relation_rows, ignore_index=True) if relation_rows else pd.DataFrame()
    return pd.DataFrame(rows), d0_ledger, relation_ledger


def load_rgb(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"cannot read {path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def optical_image_for_sar(run_id: str, frame_index: int, data: dict[str, pd.DataFrame]) -> tuple[np.ndarray, pd.DataFrame, int]:
    meta = data["frames"][(data["frames"]["run_id"].eq(run_id)) & (data["frames"]["frame_index"].eq(frame_index))].iloc[0]
    optical_index = int(meta.nominal_optical_frame_index)
    run = data["optical"][data["optical"]["run_id"].eq(run_id)]
    root = Path(str(run.iloc[0].optical_image_path)).parent
    matches = sorted(root.glob(f"frame_{optical_index:06d}_t*ms.jpg"))
    if not matches:
        raise FileNotFoundError(f"missing optical image {run_id} {optical_index}")
    return load_rgb(matches[0]), run[run["frame_index"].eq(optical_index)].copy(), optical_index


def draw_optical_boxes(axis: Any, boxes: pd.DataFrame, selected: list[str]) -> None:
    colors = ["#ff3b30", "#00a6d6", "#ffcc00", "#9c27b0", "#00a65a"]
    for index, track_id in enumerate(selected):
        for row in boxes[boxes["raw_track_fragment_id"].eq(track_id)].itertuples(index=False):
            axis.add_patch(plt.Rectangle(
                (float(row.bbox_x1), float(row.bbox_y1)), float(row.bbox_x2-row.bbox_x1), float(row.bbox_y2-row.bbox_y1),
                fill=False, edgecolor=colors[index % len(colors)], linewidth=2.4,
            ))
            axis.text(float(row.bbox_x1), float(row.bbox_y1), track_id.split("_")[-1], color="white", fontsize=7,
                      bbox={"facecolor": colors[index % len(colors)], "alpha": 0.75, "pad": 1})


def mask_for_region_ids(run_id: str, frame_index: int, region_ids: set[str], regions: pd.DataFrame) -> np.ndarray:
    with np.load(Q95_MASKS / f"{run_id}_SARF{frame_index:06d}.npz") as archive:
        labels = archive["Q095"]
    frame = regions[regions["run_id"].eq(run_id) & regions["frame_index"].eq(frame_index)]
    wanted = set(frame.loc[frame["region_id"].isin(region_ids), "region_label"].astype(int))
    return np.isin(labels, list(wanted)).astype(np.uint8)


def sar_overlay(run_id: str, frame_index: int, window_id: str, selected_tracks: list[str], events: pd.DataFrame, data: dict[str, pd.DataFrame]) -> np.ndarray:
    meta = data["frames"][(data["frames"]["run_id"].eq(run_id)) & (data["frames"]["frame_index"].eq(frame_index))].iloc[0]
    image = load_rgb(Path(str(meta.sar_image_path)))
    with np.load(Q95_MASKS / f"{run_id}_SARF{frame_index:06d}.npz") as archive:
        labels = archive["Q095"]
    frame_regions = data["regions"][data["regions"]["run_id"].eq(run_id) & data["regions"]["frame_index"].eq(frame_index)]
    relevant = events[events["window_id"].eq(window_id) & events["frame_index"].eq(frame_index) & events["track_id"].isin(selected_tracks)]
    candidate_ids = set(relevant["region_id"].astype(str))
    shared_ids = set(relevant.loc[relevant["shared_track_count"].gt(1), "region_id"].astype(str))
    overlay = image.copy()
    for row in frame_regions.itertuples(index=False):
        mask = (labels == int(row.region_label)).astype(np.uint8)
        if not mask.any():
            continue
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if str(row.region_id) in shared_ids:
            color, width = (255, 60, 210), 3
        elif str(row.region_id) in candidate_ids:
            color, width = (30, 240, 100), 2
        else:
            color, width = (250, 205, 40), 1
        cv2.drawContours(overlay, contours, -1, color, width)
    return overlay


def render_window_atlas(window: dict[str, Any], events: pd.DataFrame, frame_evolution: pd.DataFrame, data: dict[str, pd.DataFrame]) -> Path:
    frames = list(range(window["start_frame"], window["end_frame"] + 1))
    columns = 4
    rows = math.ceil(len(frames) / columns)
    fig = plt.figure(figsize=(22, rows * 6.4), constrained_layout=True)
    grid = fig.add_gridspec(rows * 2, columns, hspace=0.03, wspace=0.02)
    for position, frame_index in enumerate(frames):
        row, col = divmod(position, columns)
        optical_image, boxes, optical_index = optical_image_for_sar(window["run_id"], frame_index, data)
        axis = fig.add_subplot(grid[row * 2, col])
        axis.imshow(optical_image)
        draw_optical_boxes(axis, boxes, window["track_ids"])
        axis.axis("off")
        axis.set_title(f"Optical nominal F{optical_index} | SAR F{frame_index}", fontsize=9)
        axis = fig.add_subplot(grid[row * 2 + 1, col])
        axis.imshow(sar_overlay(window["run_id"], frame_index, window["window_id"], window["track_ids"], events, data))
        axis.axis("off")
        summary = frame_evolution[frame_evolution["window_id"].eq(window["window_id"]) & frame_evolution["frame_index"].eq(frame_index)]
        label = ", ".join(
            f"{str(row.track_id).split('_')[-1]} A{int(row.angle_region_count)}/U{int(row.causal_upper_family_count)}/S{int(row.strict_mutual_core_family_count)}"
            for row in summary.itertuples(index=False)
        )
        axis.set_title(label, fontsize=7)
    for position in range(len(frames), rows * columns):
        row, col = divmod(position, columns)
        fig.add_subplot(grid[row * 2, col]).axis("off")
        fig.add_subplot(grid[row * 2 + 1, col]).axis("off")
    fig.suptitle(
        f"{window['window_id']}\nOptical boxes above; SAR Q95 below: yellow=full fan, green=selected corridor, magenta=shared by selected optical fragments\nQ95 is response support, not PERSON segmentation; A/U/S are non-nested angle / causal-upper / strict-core views",
        fontsize=14,
    )
    path = PRE / "figures" / f"{window['window_id']}_frame_atlas.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=135, bbox_inches="tight")
    plt.close(fig)
    return path


def render_candidate_evolution(window: dict[str, Any], events: pd.DataFrame, frame_evolution: pd.DataFrame) -> Path:
    tracks = window["track_ids"]
    fig, axes = plt.subplots(len(tracks), 2, figsize=(20, max(6, 4.4 * len(tracks))), squeeze=False, constrained_layout=True)
    for row_index, track_id in enumerate(tracks):
        event = events[events["window_id"].eq(window["window_id"]) & events["track_id"].eq(track_id)].copy()
        family_rank = event.groupby("strict_family_id").agg(frames=("frame_index", "nunique"), first=("frame_index", "min")).sort_values(["frames", "first"], ascending=[False, True])
        displayed = family_rank.head(18).index.tolist()
        y_map = {family_id: index for index, family_id in enumerate(displayed)}
        axis = axes[row_index, 0]
        for family_id in displayed:
            group = event[event["strict_family_id"].eq(family_id)]
            by_frame = group.groupby("frame_index").agg(shared=("shared_track_count", "max"), regions=("region_id", "nunique")).reset_index()
            y = y_map[family_id]
            axis.plot(by_frame["frame_index"], [y] * len(by_frame), color="#7f8c8d", alpha=0.55, linewidth=1)
            colors = np.where(by_frame["shared"].gt(1), "#d81b9c", "#1b9e77")
            sizes = np.where(by_frame["regions"].gt(1), 58, 24)
            axis.scatter(by_frame["frame_index"], [y] * len(by_frame), c=colors, s=sizes, edgecolors="black", linewidths=0.25)
        axis.set_yticks(range(len(displayed)))
        axis.set_yticklabels([family[-8:] for family in displayed], fontsize=7)
        axis.invert_yaxis()
        axis.set_xlim(window["start_frame"] - 0.5, window["end_frame"] + 0.5)
        axis.set_title(f"{track_id} | top {len(displayed)} strict families by reviewed-frame occupancy\nmagenta=shared identity competition; large marker=multi-region representation")
        axis.set_xlabel("SAR frame")
        axis.set_ylabel("strict family suffix")

        evolution = frame_evolution[frame_evolution["window_id"].eq(window["window_id"]) & frame_evolution["track_id"].eq(track_id)].sort_values("frame_index")
        axis = axes[row_index, 1]
        axis.plot(evolution["frame_index"], evolution["angle_region_count"], "o-", label="angle-admitted Q95 regions", color="#d95f02")
        axis.plot(evolution["frame_index"], evolution["causal_upper_family_count"], "o-", label="causal upper-possible families", color="#1f78b4")
        axis.plot(evolution["frame_index"], evolution["strict_mutual_core_family_count"], "o-", label="strict mutual-core families", color="#33a02c")
        axis.plot(evolution["frame_index"], evolution["shared_strict_family_count"], "o--", label="shared with selected peers", color="#d81b9c")
        axis.set_xlim(window["start_frame"] - 0.5, window["end_frame"] + 0.5)
        axis.set_xlabel("SAR frame")
        axis.set_ylabel("count (descriptive, non-nested)")
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8, loc="upper right")
    fig.suptitle(
        f"T0 candidate evolution — {window['window_id']}\nThese are set-valued feasible explanations, not tracker identities or final localization",
        fontsize=15,
    )
    path = PRE / "figures" / f"{window['window_id']}_candidate_evolution.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=155, bbox_inches="tight")
    plt.close(fig)
    return path


def choose_p0_pair(window: dict[str, Any], events: pd.DataFrame, data: dict[str, pd.DataFrame]) -> tuple[int, int]:
    selected = events[events["window_id"].eq(window["window_id"]) & events["track_id"].isin(window["track_ids"])]
    source_ids = defaultdict(set)
    destination_ids = defaultdict(set)
    for frame_index, group in selected.groupby("frame_index"):
        source_ids[int(frame_index)] = set(group["region_id"].astype(str))
        destination_ids[int(frame_index)] = set(group["region_id"].astype(str))
    candidates: list[tuple[float, int, int]] = []
    for source in range(window["start_frame"], window["end_frame"]):
        destination = source + 1
        availability = data["p0_availability"]
        row = availability[
            availability["run_id"].eq(window["run_id"])
            & availability["source_sar_frame"].eq(source)
            & availability["destination_sar_frame"].eq(destination)
        ]
        if row.empty or not bool(row.iloc[0].p0_model_available):
            continue
        edges = data["p0_edges"]
        edge = edges[
            edges["run_id"].eq(window["run_id"])
            & edges["source_sar_frame"].eq(source)
            & edges["destination_sar_frame"].eq(destination)
            & edges["source_region_id"].isin(source_ids[source])
            & edges["destination_region_id"].isin(destination_ids[destination])
        ]
        candidates.append((float(edge["soft_intersection_px"].sum()), source, destination))
    if not candidates:
        raise RuntimeError(f"no P0-available pair in {window['window_id']}")
    _, source, destination = max(candidates)
    return source, destination


def draw_mask_contours(image: np.ndarray, mask: np.ndarray, color: tuple[int, int, int], width: int = 2) -> np.ndarray:
    output = image.copy()
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(output, contours, -1, color, width)
    return output


def render_p0_before_after(window: dict[str, Any], events: pd.DataFrame, data: dict[str, pd.DataFrame], models: dict[tuple[str, int, int], dict[str, Any]]) -> Path:
    source, destination = choose_p0_pair(window, events, data)
    selected = events[events["window_id"].eq(window["window_id"]) & events["track_id"].isin(window["track_ids"])]
    source_ids = set(selected.loc[selected["frame_index"].eq(source), "region_id"].astype(str))
    destination_ids = set(selected.loc[selected["frame_index"].eq(destination), "region_id"].astype(str))
    source_mask = mask_for_region_ids(window["run_id"], source, source_ids, data["regions"])
    destination_mask = mask_for_region_ids(window["run_id"], destination, destination_ids, data["regions"])
    meta = data["frames"][data["frames"]["run_id"].eq(window["run_id"]) & data["frames"]["frame_index"].eq(destination)].iloc[0]
    destination_image = load_rgb(Path(str(meta.sar_image_path)))
    model = models[(window["run_id"], source, destination)]
    dx, dy = map(float, model["parameters"]["translation_xy"])
    matrix = np.asarray([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=np.float32)
    warped = cv2.warpAffine(source_mask, matrix, (source_mask.shape[1], source_mask.shape[0]), flags=cv2.INTER_NEAREST)
    before = draw_mask_contours(destination_image, destination_mask, (250, 210, 30), 2)
    before = draw_mask_contours(before, source_mask, (255, 55, 55), 2)
    after = draw_mask_contours(destination_image, destination_mask, (250, 210, 30), 2)
    after = draw_mask_contours(after, warped, (30, 220, 245), 2)
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), constrained_layout=True)
    axes[0].imshow(before); axes[0].axis("off"); axes[0].set_title("Before P0: source candidate contours red; destination contours yellow")
    axes[1].imshow(after); axes[1].axis("off"); axes[1].set_title(f"After frozen P0 translation: source cyan; dx={dx:.2f}px, dy={dy:.2f}px")
    fig.suptitle(
        f"{window['window_id']} | F{source}->F{destination}\nP0 is common apparent transport used to inspect support continuity; it is not PERSON motion or identity evidence",
        fontsize=14,
    )
    path = PRE / "figures" / f"{window['window_id']}_p0_before_after.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=165, bbox_inches="tight")
    plt.close(fig)
    return path


def build_ambiguity_taxonomy(family_ledger: pd.DataFrame, relation_ledger: pd.DataFrame, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    statuses = [
        ("AZIMUTH_EXIT", "LEFT_AZIMUTH_CORRIDOR", "optical azimuth corridor", "family continues in full-fan SAR but exits the optical corridor", "angle information can eliminate this explanation without a radial answer"),
        ("STRICT_TEMPORAL_BREAK", "NO_STRICT_P0_CONTINUATION", "frozen P0 strict mutual support", "no strict or optional corridor continuation with the interface available", "strict image-domain continuity can eliminate some explanations"),
        ("OPTIONAL_TOPOLOGY", "STRICT_CORE_BREAK_BUT_UPPER_OPTIONAL_CONTINUATION", "set-valued P0/topology", "strict core breaks but deformation/split/merge-compatible support remains", "cannot force death or unique continuation"),
        ("MISSING_INTERFACE", "P0_INTERFACE_UNAVAILABLE_CANNOT_DECIDE", "P0 availability", "continuity interface is unavailable", "absence of evidence must remain unavailable, not candidate death"),
        ("WINDOW_END_SURVIVOR", "SURVIVED_TO_WINDOW_END", "all retained runtime-legal evidence", "candidate remains feasible at reviewed end", "survival is not PERSON identity or final localization"),
        ("BACKGROUND_COMPATIBLE_RECURRENCE", "BACKGROUND_COMPATIBLE_PERSISTENCE", "matched-null recurrence control", "smooth/persistent family patterns also occur in zero-detected-optical-PERSON windows", "temporal recurrence is not PERSON specificity"),
        ("REPRESENTATION_INSTABILITY", "REPRESENTATION_FRAGMENTATION_OR_TOPOLOGY_AMBIGUITY", "Q95 support and set-valued topology", "one explanation contains multi-region, split/merge, deformation, or fragmentation alternatives", "fixing identity by one-to-one linking would overclaim"),
        ("MULTI_TARGET_PERMUTATION", "MULTI_TARGET_IDENTITY_PERMUTATION_COMPATIBLE", "optical identity plus relative relation", "one SAR family is compatible with multiple optical fragments", "relative order can remove some joint worlds but need not delete any individual family"),
        ("LATE_ENTRY", "LATE_APPEARANCE", "lifecycle and corridor admission", "candidate first appears after the reviewed track shell begins", "appearance is descriptive and not automatically a cross-modal event match"),
    ]
    rows: list[dict[str, Any]] = []
    for ambiguity, status, source, definition, claim in statuses:
        primary = int(family_ledger["primary_status"].eq(status).sum())
        secondary = int(family_ledger["secondary_statuses"].fillna("").str.split(";").map(lambda values: status in values).sum())
        windows = semicolon(family_ledger.loc[
            family_ledger["primary_status"].eq(status) | family_ledger["secondary_statuses"].fillna("").str.contains(status, regex=False),
            "window_id",
        ])
        rows.append({
            "ambiguity_mode": ambiguity,
            "ledger_status": status,
            "information_source": source,
            "observed_definition": definition,
            "primary_family_count": primary,
            "secondary_family_count": secondary,
            "observed_window_ids": windows,
            "supported_interpretation": claim,
        })
    rows.append({
        "ambiguity_mode": "UNRESOLVED_RADIAL_OR_EQUIVALENT_UNARY_SEPARATION",
        "ledger_status": "NOT_DIRECTLY_OBSERVABLE_PRE_REFERENCE",
        "information_source": "currently absent runtime-legal independent unary physical constraint",
        "observed_definition": "multiple temporally persistent families remain angle-compatible at different SAR radial descriptors",
        "primary_family_count": int(family_ledger["primary_status"].eq("SURVIVED_TO_WINDOW_END").sum()),
        "secondary_family_count": 0,
        "observed_window_ids": semicolon(family_ledger.loc[family_ledger["primary_status"].eq("SURVIVED_TO_WINDOW_END"), "window_id"]),
        "supported_interpretation": "T0 may diagnose the need for independent information, but pre-reference evidence alone must not name metric range as the only solution",
    })
    return pd.DataFrame(rows)


def pre_summary(window_registry: pd.DataFrame, track_registry: pd.DataFrame, frame_evolution: pd.DataFrame, family_ledger: pd.DataFrame, relation_ledger: pd.DataFrame, input_manifest: pd.DataFrame) -> dict[str, Any]:
    return {
        "schema": "PERSON_T0_PRE_REFERENCE_FREEZE_SUMMARY_V1",
        "window_count": int(len(window_registry)),
        "window_track_count": int(len(track_registry)),
        "reviewed_window_frame_count": int(window_registry["frame_count"].sum()),
        "candidate_frame_state_count": int(len(frame_evolution)),
        "strict_family_window_track_count": int(len(family_ledger)),
        "primary_status_counts": {str(key): int(value) for key, value in family_ledger["primary_status"].value_counts().sort_index().items()},
        "survivor_count": int(family_ledger["primary_status"].eq("SURVIVED_TO_WINDOW_END").sum()),
        "relation_segment_count": int(len(relation_ledger)),
        "relation_segment_with_joint_world_contraction_count": int(relation_ledger["N_excluded_joint_worlds"].gt(0).sum()) if len(relation_ledger) else 0,
        "input_manifest_row_count": int(len(input_manifest)),
        "manual_reference_loaded": False,
        "r04_used": False,
        "scientific_claim_state": "PRE_REFERENCE_STRUCTURE_FROZEN_NOT_PERSON_CONFIRMED",
    }


def write_pre_report(summary: dict[str, Any], window_registry: pd.DataFrame, ablation: pd.DataFrame, taxonomy: pd.DataFrame) -> None:
    status_lines = "\n".join(f"- `{key}`: {value}" for key, value in summary["primary_status_counts"].items())
    windows = "\n".join(
        f"- `{row.window_id}`: {row.case_axes}; tracks={row.selected_track_count}, frames={row.frame_count}, P0 unavailable pairs={row.p0_unavailable_pair_count}."
        for row in window_registry.itertuples(index=False)
    )
    median_lines = "\n".join(
        f"- `{row.window_id}` / `{row.track_id}`: median angle regions {row.median_angle_region_count:g}, causal upper families {row.median_causal_upper_family_count:g}, strict mutual-core families {row.median_strict_mutual_core_family_count:g}, shared strict families {row.median_shared_strict_family_count:g}."
        for row in ablation.itertuples(index=False)
    )
    taxonomy_lines = "\n".join(
        f"- `{row.ambiguity_mode}`: primary={row.primary_family_count}, secondary={row.secondary_family_count}; {row.supported_interpretation}"
        for row in taxonomy.itertuples(index=False)
    )
    text = f"""# T0 — Temporal Candidate Ambiguity Structure Study

## Phase status

The pre-reference construction tree is frozen. No PERSON reference, oracle range, manual cross-modal correspondence, or R04 evidence was loaded by this phase. The analyst is not historically outcome-naive; the defensible protection is phase-separated code/data access plus the hash manifest.

This phase studies set-valued feasible SAR explanations. It does not produce a tracker identity, PERSON score, final center, or SAR box.

## Frozen representative windows

{windows}

## Candidate-state ledger

The complete ledger records why a strict mutual-core family ended or survived. Status counts are descriptive:

{status_lines}

`P0_INTERFACE_UNAVAILABLE_CANNOT_DECIDE` is deliberately not counted as an elimination. `STRICT_CORE_BREAK_BUT_UPPER_OPTIONAL_CONTINUATION` preserves deformation/split/merge-compatible alternatives rather than forcing one-to-one continuity.

## Information-layer comparison

{median_lines}

These counts are non-nested. The causal upper-possible family and strict mutual-core partition answer different representation questions, so their numeric difference is not a monotonic performance gain.

## Remaining ambiguity taxonomy before reveal

{taxonomy_lines}

## Pre-reference interpretation boundary

The frozen evidence can show that angle exit, strict P0 support failure, representation ambiguity, missing P0 availability, and shared multi-target support are different mechanisms. It can also show that multiple temporally persistent radial-separated explanations survive. It cannot yet say which surviving family is the true PERSON response or whether metric range is the unique missing observation.

## Visual evidence

Each window has a full frame atlas, a candidate-evolution view, and one P0 before/after support comparison under `pre_reference/figures/`. Yellow contours are full-fan Q95 support, green contours intersect selected optical corridors, and magenta contours are shared by multiple selected optical fragments.

## Next phase

Only after verifying the pre-reference freeze may `--phase post` load the manual research reference for retention/failure diagnosis. Post-reference results must remain diagnostic and cannot retroactively change the frozen windows, candidates, ledgers, or figures.
"""
    (OUTPUT / "REPORT_PRE_REFERENCE.md").write_text(text, encoding="utf-8")


def freeze_pre_reference() -> pd.DataFrame:
    rows = []
    for path in sorted(PRE.rglob("*")):
        if not path.is_file() or path.name == "pre_reference_freeze_manifest.csv":
            continue
        rows.append({
            "relative_path": str(path.relative_to(PRE)).replace("\\", "/"),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    manifest = pd.DataFrame(rows)
    manifest.to_csv(PRE / "pre_reference_freeze_manifest.csv", index=False, encoding="utf-8-sig")
    return manifest


def verify_pre_reference() -> dict[str, Any]:
    manifest_path = PRE / "pre_reference_freeze_manifest.csv"
    if not manifest_path.exists():
        raise RuntimeError("pre-reference freeze manifest is missing")
    manifest = pd.read_csv(manifest_path, encoding="utf-8-sig")
    expected = set(manifest["relative_path"].astype(str))
    actual = {
        str(path.relative_to(PRE)).replace("\\", "/")
        for path in PRE.rglob("*")
        if path.is_file() and path.name != manifest_path.name
    }
    if expected != actual:
        raise RuntimeError(f"pre-reference tree changed: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")
    mismatches = []
    for row in manifest.itertuples(index=False):
        path = PRE / str(row.relative_path)
        actual_hash = sha256_file(path)
        if actual_hash != str(row.sha256) or path.stat().st_size != int(row.size_bytes):
            mismatches.append(str(row.relative_path))
    if mismatches:
        raise RuntimeError(f"pre-reference hash mismatch: {mismatches}")
    return {"file_count": len(manifest), "tree_sha256": hashlib.sha256("".join(manifest.sort_values("relative_path")["sha256"]).encode("utf-8")).hexdigest()}


def run_pre() -> None:
    if PRE.exists():
        shutil.rmtree(PRE)
    PRE.mkdir(parents=True, exist_ok=True)
    data = load_pre_inputs()
    contract = analysis_contract()
    write_json(PRE / "analysis_contract.json", contract)
    input_manifest = build_input_manifest(data)
    write_table(input_manifest, PRE / "input_manifest", parquet=False)
    window_registry, track_registry = build_window_registry(data)
    write_table(window_registry, PRE / "window_registry")
    write_table(track_registry, PRE / "window_track_registry")
    events, frame_evolution = build_candidate_evolution(data)
    write_table(events, PRE / "candidate_region_family_events")
    write_table(frame_evolution, PRE / "candidate_frame_evolution")
    family_ledger = build_family_ledger(events, frame_evolution, data)
    write_table(family_ledger, PRE / "candidate_survival_elimination_ledger")
    ablation, d0r_ledger, relation_ledger = build_ablation_ledger(frame_evolution, family_ledger, data)
    write_table(ablation, PRE / "limited_information_ablation_ledger")
    write_table(d0r_ledger, PRE / "set_valued_representation_overlap_ledger")
    write_table(relation_ledger, PRE / "multi_target_relation_ablation_ledger")
    taxonomy = build_ambiguity_taxonomy(family_ledger, relation_ledger, data)
    write_table(taxonomy, PRE / "remaining_ambiguity_taxonomy_pre_reference", parquet=False)

    models = p0_models()
    for window in WINDOWS:
        render_window_atlas(window, events, frame_evolution, data)
        render_candidate_evolution(window, events, frame_evolution)
        render_p0_before_after(window, events, data, models)

    summary = pre_summary(window_registry, track_registry, frame_evolution, family_ledger, relation_ledger, input_manifest)
    write_json(PRE / "pre_reference_freeze_summary.json", summary)
    write_pre_report(summary, window_registry, ablation, taxonomy)
    manifest = freeze_pre_reference()
    verification = verify_pre_reference()
    print(json.dumps({"phase": "pre", "summary": summary, "freeze_file_count": len(manifest), "verification": verification}, ensure_ascii=False, indent=2))


def reference_hits(regions: pd.DataFrame, reference_row: Any) -> pd.DataFrame:
    return regions[
        regions["theta_min_deg"].le(float(reference_row.reference_theta_deg))
        & regions["theta_max_deg"].ge(float(reference_row.reference_theta_deg))
        & regions["range_min_m"].le(float(reference_row.reference_range_m))
        & regions["range_max_m"].ge(float(reference_row.reference_range_m))
    ]


def build_post_reference_tables(
    reference: pd.DataFrame,
    mapping: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    events = pd.read_parquet(PRE / "candidate_region_family_events.parquet")
    evolution = pd.read_parquet(PRE / "candidate_frame_evolution.parquet")
    family_ledger = pd.read_parquet(PRE / "candidate_survival_elimination_ledger.parquet")
    windows = pd.read_parquet(PRE / "window_registry.parquet").set_index("window_id")
    tracks = pd.read_parquet(PRE / "window_track_registry.parquet")
    regions = read_non_r04(Q95_REGIONS)
    reference = reference[reference["run_id"].isin(RUNS)].copy()
    mapping = mapping[mapping["run_id"].isin(RUNS) & mapping["entity_kind"].eq("RAW_FRAGMENT")].copy()

    diagnostic_rows: list[dict[str, Any]] = []
    hit_event_rows: list[dict[str, Any]] = []
    for track in tracks.itertuples(index=False):
        mapped = mapping[mapping["run_id"].eq(track.run_id) & mapping["entity_id"].eq(track.track_id)]
        if len(mapped) != 1:
            raise RuntimeError(f"expected one post-reference target mapping for {track.track_id}, got {len(mapped)}")
        target_id = str(mapped.iloc[0].target_id)
        window = windows.loc[track.window_id]
        refs = reference[
            reference["run_id"].eq(track.run_id)
            & reference["target_id"].eq(target_id)
            & reference["frame_index"].between(int(window.start_frame), int(window.end_frame))
        ].sort_values("frame_index")
        for ref in refs.itertuples(index=False):
            frame_index = int(ref.frame_index)
            full_frame = regions[regions["run_id"].eq(track.run_id) & regions["frame_index"].eq(frame_index)]
            full_hit = reference_hits(full_frame, ref)
            candidate = events[
                events["window_id"].eq(track.window_id)
                & events["track_id"].eq(track.track_id)
                & events["frame_index"].eq(frame_index)
            ]
            candidate_hit = reference_hits(candidate, ref)
            track_shell_available = bool((
                evolution["window_id"].eq(track.window_id)
                & evolution["track_id"].eq(track.track_id)
                & evolution["frame_index"].eq(frame_index)
            ).any())
            if not track_shell_available:
                state = "TRACK_NOT_YET_ADMITTED_IN_WINDOW"
            elif full_hit.empty:
                state = "REFERENCE_NOT_IN_Q95_SUPPORT"
            elif candidate_hit.empty:
                state = "Q95_REFERENCE_SUPPORT_OUTSIDE_OPTICAL_CORRIDOR"
            else:
                state = "REFERENCE_IN_CANDIDATE_SET"
            frame_state = evolution[
                evolution["window_id"].eq(track.window_id)
                & evolution["track_id"].eq(track.track_id)
                & evolution["frame_index"].eq(frame_index)
            ]
            diagnostic_rows.append({
                "window_id": track.window_id,
                "run_id": track.run_id,
                "track_id": track.track_id,
                "target_id_oracle_mapping": target_id,
                "frame_index": frame_index,
                "reference_support_status": str(ref.reference_support_status),
                "reference_range_m": float(ref.reference_range_m),
                "reference_theta_deg": float(ref.reference_theta_deg),
                "track_shell_available": track_shell_available,
                "post_reference_state": state,
                "full_fan_q95_reference_region_count": int(full_hit["region_id"].nunique()),
                "full_fan_q95_reference_region_ids": semicolon(full_hit["region_id"]),
                "candidate_reference_region_count": int(candidate_hit["region_id"].nunique()),
                "candidate_reference_region_ids": semicolon(candidate_hit["region_id"]),
                "reference_strict_family_count": int(candidate_hit["strict_family_id"].nunique()) if len(candidate_hit) else 0,
                "reference_strict_family_ids": semicolon(candidate_hit["strict_family_id"]) if len(candidate_hit) else "",
                "reference_causal_upper_family_ids": semicolon(candidate_hit["causal_upper_family_id"]) if len(candidate_hit) else "",
                "total_candidate_strict_family_count": int(frame_state.iloc[0].strict_mutual_core_family_count) if len(frame_state) else 0,
                "non_reference_strict_family_count_on_sample": int(max(0, (frame_state.iloc[0].strict_mutual_core_family_count if len(frame_state) else 0) - candidate_hit["strict_family_id"].nunique())),
                "reference_loaded_after_frozen_construction": True,
                "construction_changed_by_reference": False,
            })
            for row in candidate_hit.itertuples(index=False):
                hit_event_rows.append({
                    "window_id": track.window_id,
                    "run_id": track.run_id,
                    "track_id": track.track_id,
                    "target_id_oracle_mapping": target_id,
                    "frame_index": frame_index,
                    "region_id": str(row.region_id),
                    "strict_family_id": str(row.strict_family_id),
                    "causal_upper_family_id": str(row.causal_upper_family_id),
                })
    diagnostic = pd.DataFrame(diagnostic_rows).sort_values(["window_id", "track_id", "frame_index"])
    hit_events = pd.DataFrame(hit_event_rows)

    if hit_events.empty:
        hit_family = pd.DataFrame(columns=["window_id", "track_id", "strict_family_id", "reference_hit_frame_count", "reference_hit_frames"])
    else:
        hit_family = hit_events.groupby(["window_id", "track_id", "strict_family_id"], as_index=False).agg(
            reference_hit_frame_count=("frame_index", "nunique"),
            reference_hit_frames=("frame_index", lambda values: semicolon(int(value) for value in values)),
            target_ids_oracle_mapping=("target_id_oracle_mapping", semicolon),
        )
    family_diagnostic = family_ledger.merge(
        hit_family,
        on=["window_id", "track_id", "strict_family_id"],
        how="left",
    )
    family_diagnostic["reference_hit_frame_count"] = family_diagnostic["reference_hit_frame_count"].fillna(0).astype(int)
    family_diagnostic["reference_hit_frames"] = family_diagnostic["reference_hit_frames"].fillna("")
    family_diagnostic["target_ids_oracle_mapping"] = family_diagnostic["target_ids_oracle_mapping"].fillna("")
    family_diagnostic["reference_overlap_observed"] = family_diagnostic["reference_hit_frame_count"].gt(0)

    def family_role(row: pd.Series) -> str:
        if row.reference_overlap_observed and row.primary_status == "SURVIVED_TO_WINDOW_END":
            return "REFERENCE_OVERLAP_SURVIVOR"
        if row.reference_overlap_observed and row.primary_status == "STRICT_CORE_BREAK_BUT_UPPER_OPTIONAL_CONTINUATION":
            return "REFERENCE_OVERLAP_STRICT_CORE_BREAK_WITH_OPTIONAL_CONTINUATION"
        if row.reference_overlap_observed:
            return "REFERENCE_OVERLAP_OTHER_NONSURVIVOR_STATE"
        if row.primary_status == "SURVIVED_TO_WINDOW_END":
            return "SURVIVOR_WITH_NO_REFERENCE_OVERLAP_ON_SPARSE_SAMPLES"
        return "NONSURVIVOR_WITH_NO_REFERENCE_OVERLAP_ON_SPARSE_SAMPLES"

    family_diagnostic["post_reference_role"] = family_diagnostic.apply(family_role, axis=1)
    family_diagnostic["no_reference_overlap_is_false_candidate_claimed"] = False

    summary_rows: list[dict[str, Any]] = []
    for (window_id, run_id, track_id, target_id), group in diagnostic.groupby(
        ["window_id", "run_id", "track_id", "target_id_oracle_mapping"], sort=False
    ):
        family = family_diagnostic[family_diagnostic["window_id"].eq(window_id) & family_diagnostic["track_id"].eq(track_id)]
        admitted = group[group["track_shell_available"]]
        summary_rows.append({
            "window_id": window_id,
            "run_id": run_id,
            "track_id": track_id,
            "target_id_oracle_mapping": target_id,
            "reference_sample_frame_count": int(group["frame_index"].nunique()),
            "admitted_reference_sample_frame_count": int(admitted["frame_index"].nunique()),
            "reference_in_candidate_frame_count": int(group["post_reference_state"].eq("REFERENCE_IN_CANDIDATE_SET").sum()),
            "reference_not_in_q95_frame_count": int(group["post_reference_state"].eq("REFERENCE_NOT_IN_Q95_SUPPORT").sum()),
            "q95_reference_outside_corridor_frame_count": int(group["post_reference_state"].eq("Q95_REFERENCE_SUPPORT_OUTSIDE_OPTICAL_CORRIDOR").sum()),
            "track_not_yet_admitted_frame_count": int(group["post_reference_state"].eq("TRACK_NOT_YET_ADMITTED_IN_WINDOW").sum()),
            "reference_in_candidate_fraction_of_admitted_samples": float(
                group["post_reference_state"].eq("REFERENCE_IN_CANDIDATE_SET").sum() / len(admitted)
            ) if len(admitted) else np.nan,
            "unique_reference_overlap_strict_family_count": int(family.loc[family["reference_overlap_observed"], "strict_family_id"].nunique()),
            "reference_overlap_survivor_family_count": int(family["post_reference_role"].eq("REFERENCE_OVERLAP_SURVIVOR").sum()),
            "reference_overlap_optional_break_family_count": int(family["post_reference_role"].eq("REFERENCE_OVERLAP_STRICT_CORE_BREAK_WITH_OPTIONAL_CONTINUATION").sum()),
            "survivor_family_count": int(family["primary_status"].eq("SURVIVED_TO_WINDOW_END").sum()),
            "survivor_without_reference_overlap_on_sparse_samples_count": int(family["post_reference_role"].eq("SURVIVOR_WITH_NO_REFERENCE_OVERLAP_ON_SPARSE_SAMPLES").sum()),
            "denominator_note": "manual reference is sparse; no-reference-overlap survivors are unresolved, not proven false candidates",
        })
    track_summary = pd.DataFrame(summary_rows)
    state_summary = diagnostic.groupby("post_reference_state", as_index=False).agg(
        sample_count=("frame_index", "size"),
        window_count=("window_id", "nunique"),
        track_count=("track_id", "nunique"),
    )
    return diagnostic, family_diagnostic, track_summary, state_summary


def polar_to_pixel(frame_meta: pd.Series, range_m: float, theta_deg: float) -> tuple[float, float]:
    radius = float(range_m) / float(frame_meta.geometry_outer_range_m) * float(frame_meta.geometry_radius_px)
    theta = math.radians(float(theta_deg))
    x = float(frame_meta.geometry_center_x_px) + radius * math.sin(theta)
    y = float(frame_meta.geometry_center_y_px) - radius * math.cos(theta)
    return x, y


def render_reference_overlay(
    window: dict[str, Any],
    diagnostic: pd.DataFrame,
    events: pd.DataFrame,
    data: dict[str, pd.DataFrame],
) -> Path:
    subset = diagnostic[diagnostic["window_id"].eq(window["window_id"])]
    frames = sorted(subset["frame_index"].astype(int).unique().tolist())
    if not frames:
        raise RuntimeError(f"no reference samples in {window['window_id']}")
    fig, axes = plt.subplots(1, len(frames), figsize=(7 * len(frames), 6), squeeze=False, constrained_layout=True)
    colors = ["#ff3b30", "#00a6d6", "#ffcc00", "#9c27b0", "#00a65a"]
    frame_registry = data["frames"].set_index(["run_id", "frame_index"])
    for column, frame_index in enumerate(frames):
        axis = axes[0, column]
        axis.imshow(sar_overlay(window["run_id"], frame_index, window["window_id"], window["track_ids"], events, data))
        frame_meta = frame_registry.loc[(window["run_id"], frame_index)]
        frame_diag = subset[subset["frame_index"].eq(frame_index)]
        labels: list[str] = []
        for index, row in enumerate(frame_diag.itertuples(index=False)):
            x, y = polar_to_pixel(frame_meta, float(row.reference_range_m), float(row.reference_theta_deg))
            color = colors[window["track_ids"].index(str(row.track_id)) % len(colors)]
            marker = "o" if row.post_reference_state == "REFERENCE_IN_CANDIDATE_SET" else "x"
            if marker == "o":
                axis.scatter([x], [y], marker=marker, s=150, linewidths=2.5, facecolors="none", edgecolors=color)
            else:
                axis.scatter([x], [y], marker=marker, s=150, linewidths=2.5, c=color)
            axis.text(x + 5, y - 5, str(row.track_id).split("_")[-1], color="white", fontsize=7, bbox={"facecolor": color, "alpha": 0.75, "pad": 1})
            labels.append(f"{str(row.track_id).split('_')[-1]}:{row.post_reference_state}")
        axis.axis("off")
        axis.set_title(f"SAR F{frame_index}\n" + "\n".join(labels), fontsize=8)
    fig.suptitle(
        f"Post-reference diagnostic only — {window['window_id']}\nCircles: reference remains in frozen candidate set; X: unavailable/admission/Q95/corridor failure. Frozen contours are unchanged.",
        fontsize=14,
    )
    path = POST / "figures" / f"{window['window_id']}_reference_overlay.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=165, bbox_inches="tight")
    plt.close(fig)
    return path


def write_visual_review(
    track_summary: pd.DataFrame,
    family_diagnostic: pd.DataFrame,
    relation: pd.DataFrame,
    matched_top: pd.DataFrame,
) -> None:
    ablation = pd.read_parquet(PRE / "limited_information_ablation_ledger.parquet")

    def metric(window_id: str, track_suffix: str) -> pd.Series:
        row = ablation[ablation["window_id"].eq(window_id) & ablation["track_id"].str.endswith(track_suffix)]
        if len(row) != 1:
            raise RuntimeError(f"missing ablation metric {window_id} {track_suffix}")
        return row.iloc[0]

    w1 = metric(WINDOWS[0]["window_id"], "PERSON003")
    w2 = metric(WINDOWS[1]["window_id"], "T0004")
    w3a = metric(WINDOWS[2]["window_id"], "PERSON017")
    w3b = metric(WINDOWS[2]["window_id"], "PERSON018")
    w4_metrics = ablation[ablation["window_id"].eq(WINDOWS[3]["window_id"])]
    w5_metrics = ablation[ablation["window_id"].eq(WINDOWS[4]["window_id"])]
    null = matched_top[matched_top["trajectory_kind"].eq("MATCHED_NO_PERSON_TIME_SHIFT")]
    source = matched_top[matched_top["trajectory_kind"].eq("SOURCE_MOVING_PERSON_CORRIDOR")].iloc[0]
    w4_relation = relation[relation["window_id"].eq(WINDOWS[3]["window_id"])]
    max_contraction = float(w4_relation["joint_world_contraction_fraction"].max())

    text = f"""# T0 逐窗口真实图像审阅

审阅日期：2026-09-03。审阅对象是冻结后的 5 张全帧 atlas、5 张 candidate-evolution 图和 5 张 P0 前后对比图。下述判断来自图像与冻结 ledger 的联合检查，不来自 candidate count 单独替代观察。

## W1 — R01 单目标大方位变化，F97–F112

- 光学 PERSON003 连续向扇区右侧移动，冻结 corridor 中心变化约 13.75°；SAR 中则同时保留近、中、远多个响应带。
- 中位每帧为 angle regions `{w1.median_angle_region_count:g}`、causal upper families `{w1.median_causal_upper_family_count:g}`、strict core families `{w1.median_strict_mutual_core_family_count:g}`。到窗口末仍有 `{int(w1.family_survived_to_window_end_count)}` 个按 track 计的 strict-family 解释。
- 参考抽样 F100/F105/F110 都落在同一个 strict family，且该 family 存活到 F112；但它只是 14 个末端存活解释之一。
- 图像判断：方位确实让一部分结构退出，P0 也能维持许多局部轮廓，但二者没有区分长期平行、径向分离的解释。这里真正缺的是一个独立 unary 物理约束；它可能是 radial-like，也可能是等价的已标定 SAR-native/跨模态信息，T0 不把“米制距离”预设为唯一答案。

## W2 — R03 单目标弱方位变化，F458–F475

- 光学目标很小且靠近入口，corridor 中心只变化约 5.93°；SAR 每帧通常只有 1–6 个候选，但可见响应包括扇区边缘亮点、中心竖向背景和底部近距结构。
- 三种计数视图的中位数都是 `{w2.median_strict_mutual_core_family_count:g}`；这不是时序“压缩成功”，而是当前 Q95 region 基本一对一进入各 family。
- 参考支持 family 在全部 18 个审阅帧中持续，并存活到窗口末。与此同时，源 corridor 的 top-family occupancy 为 `{float(source.temporal_occupancy):.3f}`，6 个 zero-detected-optical-PERSON matched-null 窗口的 top occupancy 为 `{', '.join(f'{value:.3f}' for value in null.temporal_occupancy)}`，其中也出现 1.000。
- 图像判断：这条响应可以连续，但“连续”不是 PERSON specificity。若要进一步消歧，需要 event-specific 或局部结构上的判别证据，并继续与 matched-null 对照，而不是给 recurrence 加分。

## W3 — R02 双目标进入/接近，F469–F480

- PERSON017/018 在光学中相邻进入；SAR 内大量 corridor region 同时被两条光学 fragment 接纳。中位 strict family 数分别为 `{w3a.median_strict_mutual_core_family_count:g}` 和 `{w3b.median_strict_mutual_core_family_count:g}`，其中共享 family 中位分别为 `{w3a.median_shared_strict_family_count:g}` 和 `{w3b.median_shared_strict_family_count:g}`。
- 冻结 P0 在窗口初段不可用，因此早期 family 缺失被保留为 `P0_INTERFACE_UNAVAILABLE_CANNOT_DECIDE`，没有伪装成候选死亡。
- 揭盲后的三个抽样帧 F472/F473/F480 中，两个人各自的参考点都在候选集合，但参考支持从 3 个不同 strict family 经过；而且两个人在同一抽样帧落入相同 strict family。
- 图像判断：这里主要不是“没有 temporal information”，而是 Q95/strict-core representation 在变形、分裂和共享响应下碎裂，同时 optical identity 无法把共享 SAR bundle 唯一分配。应保留 set-valued bundle；一对一 tracker 会把表示问题伪装成身份跳变。

## W4 — R02 五目标身份竞争，F487–F494

- 五条光学 fragment 在有限角区密集并存；SAR atlas 中多数候选轮廓为 magenta，即同时兼容多个光学身份。五条 fragment 的中位 strict-family burden 为 `{', '.join(f'{value:g}' for value in w4_metrics.median_strict_mutual_core_family_count)}`，共享 burden 几乎同量级。
- 相对角序关系能删除 joint assignment worlds；本窗口重叠 segment 的最大 contraction 为 `{max_contraction:.3f}`。但冻结 R0 没有删除任何单独 family，因此“关系有信息”与“得到唯一身份”必须分开。
- 揭盲后，PERSON017 在 F494 的参考点不落入任何 Q95 region，属于 representation miss；PERSON018 的参考支持在末帧切换到另一个 strict family。PERSON021 与 PERSON023 的不同参考目标却持续落在同一个 strict family；PERSON023/024 还是同一离线目标的两个 raw fragments，后者在 F489 才进入 shell。
- 图像判断：多目标歧义首先表现为 shared bundle 和 raw-fragment re-entry/permutation，不是单纯的最近邻问题。缺少的是能锚定 bundle 内部物理关系的独立信息，同时需要不把 Q95 split/merge 强制 Boolean 化。

## W5 — R01 强背景与 topology stress，F48–F55

- 三人清晰可见，但 SAR 中道路/边缘/强散射背景产生大量长期 Q95 结构。三条 fragment 的中位 strict-family burden 分别为 `{', '.join(f'{value:g}' for value in w5_metrics.median_strict_mutual_core_family_count)}`，末端存活 family 分别为 `{', '.join(str(int(value)) for value in w5_metrics.family_survived_to_window_end_count)}`。
- PERSON001 与 PERSON002 是不同参考目标，却在 F50/F55 都落入同一个 strict family；PERSON003 的参考 family 独立但仍与大量径向分离背景 family 共存。
- P0 前后图能看到约 1.86 px 公共平移后的轮廓对齐，但这种对齐同时适用于背景 ridge，不能升级为 PERSON motion 或 identity。
- 图像判断：这是 C 与 D 的叠加——已有时序不足以压缩背景 ambiguity，同时 candidate representation 让多个物理目标/响应合入同一 set-valued family。继续增加 linking score 不会解决问题。

## 跨窗口判断

1. `azimuth exit` 和明确的 strict P0 support break 会自然杀死一部分解释；这是真实的部署期消歧信息。
2. P0 不可用时不能判断死亡；upper optional continuation 存在时也不能强行一对一续接。
3. 大方位变化并未让 W1/W5 收敛到少数解释；弱方位 W2 的干净持续又被 matched-null 反例否定为特异性证据。
4. W3/W4 显示当前 bottleneck 的一部分来自 representation/shared bundle，而不是只缺一个更强 tracker。
5. 因此 T0 结果以“情况 C + 情况 D”为主，夹有局部 B：时序能移除若干瞬态解释，但总体仍需新的独立观测与最小表示修复；二者必须分开验证。
"""
    (OUTPUT / "VISUAL_REVIEW.md").write_text(text, encoding="utf-8")


def write_final_report(
    verification: dict[str, Any],
    diagnostic: pd.DataFrame,
    family_diagnostic: pd.DataFrame,
    track_summary: pd.DataFrame,
    state_summary: pd.DataFrame,
    relation: pd.DataFrame,
) -> dict[str, Any]:
    pre_summary_data = json.loads((PRE / "pre_reference_freeze_summary.json").read_text(encoding="utf-8"))
    total_samples = int(len(diagnostic))
    admitted = int(diagnostic["track_shell_available"].sum())
    retained = int(diagnostic["post_reference_state"].eq("REFERENCE_IN_CANDIDATE_SET").sum())
    q95_miss = int(diagnostic["post_reference_state"].eq("REFERENCE_NOT_IN_Q95_SUPPORT").sum())
    not_admitted = int(diagnostic["post_reference_state"].eq("TRACK_NOT_YET_ADMITTED_IN_WINDOW").sum())
    corridor_miss = int(diagnostic["post_reference_state"].eq("Q95_REFERENCE_SUPPORT_OUTSIDE_OPTICAL_CORRIDOR").sum())
    survivor = family_diagnostic[family_diagnostic["primary_status"].eq("SURVIVED_TO_WINDOW_END")]
    survivor_reference = int(survivor["reference_overlap_observed"].sum())
    survivor_no_reference = int((~survivor["reference_overlap_observed"]).sum())
    relation_contracted = relation[relation["N_excluded_joint_worlds"].gt(0)]
    max_relation = float(relation_contracted["joint_world_contraction_fraction"].max()) if len(relation_contracted) else 0.0
    summary = {
        "schema": "PERSON_T0_POST_REFERENCE_DIAGNOSTIC_SUMMARY_V1",
        "pre_reference_tree_sha256": verification["tree_sha256"],
        "reference_sample_count": total_samples,
        "admitted_reference_sample_count": admitted,
        "reference_in_candidate_count": retained,
        "reference_in_candidate_fraction_of_admitted_samples": retained / admitted if admitted else None,
        "reference_not_in_q95_count": q95_miss,
        "q95_reference_outside_corridor_count": corridor_miss,
        "track_not_yet_admitted_count": not_admitted,
        "survivor_family_window_track_count": int(len(survivor)),
        "survivor_with_reference_overlap_on_sparse_samples_count": survivor_reference,
        "survivor_without_reference_overlap_on_sparse_samples_count": survivor_no_reference,
        "maximum_observed_relation_joint_world_contraction_fraction": max_relation,
        "conclusion": "CASE_C_PLUS_CASE_D_WITH_LOCAL_CASE_B_TEMPORAL_ELIMINATION_BUT_LARGE_SURVIVOR_BURDEN_AND_REPRESENTATION_SHARED_BUNDLE_FAILURES",
        "non_claims": [
            "sparse sampled retention is not full-stream validated retention",
            "no-reference-overlap survivor is not proven false",
            "no intrinsic RCS or recovered physical motion claim",
            "no final PERSON identity, center, or box",
            "validator or hash PASS is not scientific confirmation",
        ],
    }
    write_json(POST / "post_reference_summary.json", summary)

    status_lines = "\n".join(f"- `{row.post_reference_state}`: {int(row.sample_count)}" for row in state_summary.itertuples(index=False))
    track_lines = "\n".join(
        f"- `{row.window_id}` / `{row.track_id}`: admitted {row.admitted_reference_sample_frame_count}/{row.reference_sample_frame_count}, candidate retained {row.reference_in_candidate_frame_count}, reference-support strict families {row.unique_reference_overlap_strict_family_count}, end survivors {row.survivor_family_count}."
        for row in track_summary.itertuples(index=False)
    )
    text = f"""# T0 — Temporal Candidate Ambiguity Structure Study

## 结论先行

T0 的结果不是“时序已经完成定位”，也不是“时序完全无用”。真实结构更接近：**情况 C + 情况 D，夹有局部情况 B**。

- 方位退出与严格 P0 continuity break 确实会自然消掉一部分错误解释。
- 但在 12 个 window-track 单元中，冻结 ledger 仍有 `{pre_summary_data['survivor_count']}` 个按 track 计的 family 解释存活到各自窗口末；W1/W4/W5 的 sequence-level ambiguity 仍很大。
- W2 的干净长期 recurrence 被 matched-null 证明为 background-compatible，不能升级为 PERSON specificity。
- W3/W4 的主要困难包含 Q95 split/merge/fragmentation、shared response bundle 和 identity permutation；这不是再加一个 linking score 就能解决的 tracker 问题。

因此，现有 optical identity + azimuth trajectory + SAR temporal/structural continuity 能移除若干瞬态候选，却没有把总体 frame-wise ambiguity 普遍压缩为少数可唯一解释路径。

## 冻结与揭盲边界

预参考树包含 5 个窗口、15 张图、完整候选 ledger，并在揭盲前冻结为 `{verification['tree_sha256']}`。construction phase 未读取 PERSON reference、oracle range 或 R04。历史报告已使分析者不是 outcome-naive，因此本研究只声称代码/数据隔离与哈希冻结，不声称分析者盲法。

独立 validator 的 PASS 只覆盖 artifact integrity、schema、R04 exclusion from outputs 与 phase separation；不等于科学确认。

## 候选为何消失、为何存活

冻结 primary status：

- `LEFT_AZIMUTH_CORRIDOR`: {pre_summary_data['primary_status_counts'].get('LEFT_AZIMUTH_CORRIDOR', 0)}。同一 full-fan family 在下一帧仍存在，但退出该 optical corridor；这是方位信息的真实消歧。
- `NO_STRICT_P0_CONTINUATION`: {pre_summary_data['primary_status_counts'].get('NO_STRICT_P0_CONTINUATION', 0)}。P0 可用且 strict/upper corridor continuation 均不存在；这是 SAR image-domain continuity 的真实反证。
- `STRICT_CORE_BREAK_BUT_UPPER_OPTIONAL_CONTINUATION`: {pre_summary_data['primary_status_counts'].get('STRICT_CORE_BREAK_BUT_UPPER_OPTIONAL_CONTINUATION', 0)}。strict core 断裂但 deformation/split/merge-compatible continuation 仍在，不能强行宣告死亡。
- `P0_INTERFACE_UNAVAILABLE_CANNOT_DECIDE`: {pre_summary_data['primary_status_counts'].get('P0_INTERFACE_UNAVAILABLE_CANNOT_DECIDE', 0)}。接口缺失只能保留 unavailable。
- `SURVIVED_TO_WINDOW_END`: {pre_summary_data['primary_status_counts'].get('SURVIVED_TO_WINDOW_END', 0)}。满足现有条件直到窗口末，但 survival 不等于 PERSON identity 或 localization。

这些总数是 window-track family ledger 行，不是彼此独立的物理目标计数；共享 family 会在不同 optical fragment 下分别出现。

## 揭盲诊断与完整分母

本轮代表窗口只有 `{total_samples}` 个 sparse manual-reference 抽样行，其中 `{admitted}` 个发生在相应 optical fragment 已进入 shell 之后。状态为：

{status_lines}

在已进入 shell 的抽样分母上，参考点有 `{retained}/{admitted}` 留在冻结候选集合中；另有 `{q95_miss}` 帧是 full-fan Q95 自身没有覆盖参考，`{corridor_miss}` 帧是 Q95 有参考但 optical corridor 排除，`{not_admitted}` 帧发生在对应 raw fragment 尚未进入 shell。这是 sparse diagnostic，不是 full-stream retention rate。

逐 track：

{track_lines}

参考支持 family 的重要结构：

- W1 与 W2：同一参考 family 跨抽样帧持续并存活，但周围仍有大量长期错误解释。
- W3：F472/F473/F480 的参考支持分裂到 3 个 strict family，且两个人在同一帧共享同一个 family；表示碎裂与身份竞争同时存在。
- W4：PERSON017 在 F494 出现 Q95 representation miss；PERSON018 的参考 family 在末帧切换；PERSON021 与 PERSON023 的不同参考目标却共享同一 family。
- W5：PERSON001 与 PERSON002 的不同参考目标共享同一 strict family，PERSON003 虽独立仍与大量径向分离背景解释并存。

末端 survivor 中，只有 `{survivor_reference}` 个在 sparse reference samples 上观察到参考重叠，`{survivor_no_reference}` 个未观察到。后者不能直接叫“错误候选”，因为 reference 稀疏；它们是仍待判别的 survivor burden。

## 信息拆解

1. **Azimuth 有效但不充分。** W1/W5 中可见部分 family 随 corridor 退出，但大量近、中、远响应同时追随宽角 corridor。
2. **P0 continuity 有效但非身份信息。** 1.86–3.10 px 量级的公共输运让许多轮廓对齐，也同样让道路/背景 ridge 对齐。
3. **Optical identity 暴露 permutation，却不能完成 SAR assignment。** W3/W4 大量 family 被多个 fragment 共同接纳。
4. **Relative relation 删除 joint worlds，不删除 individual family。** 代表窗口重叠 segment 的最大 joint-world contraction 为 `{max_relation:.3f}`，但冻结 R0 的 individual family deletion 仍为 0。
5. **Temporal recurrence 不是 PERSON specificity。** R03 matched-null 中无 optical PERSON 的窗口也产生同样平滑且完整的长期 family。
6. **Candidate representation 是独立瓶颈。** 参考支持在 W3/W4 跨 strict family 断裂，且 W4 有 Q95 miss；不能把这些都归咎于缺少新传感信息。

## Remaining ambiguity taxonomy

- `radial-separated persistent alternatives`: W1/W5 的多个长期平行解释仍满足 angle + P0；需要独立 unary 物理约束，但 T0 不预设必须是 metric range。
- `background-compatible recurrence`: W2 的持续 family 与 matched-null 不可凭 recurrence 区分。
- `shared response bundle / identity permutation`: W3/W4 中一个 SAR family 可同时兼容多个 optical identity。
- `representation fragmentation`: 真参考支持跨 strict family 变化，或 Q95 不覆盖参考。
- `optional topology`: split/merge/deformation 下 strict core break 不等于物理响应消失。
- `timing/P0 unavailable`: entry/change-point 附近缺少接口时必须保留 unknown。

## 当前真正缺少的观测

不是单一答案，而是两类缺口：

1. 对 W1/W5 这类长期径向分离 survivor，需要一个与 azimuth/recurrence 独立的 unary 物理判别量。候选可以包括 SAR-native radial profile/axis support、可部署的粗区间或序关系，但必须逐项做 reference-blind、matched-control 检验，不能先认定 optical metric range。
2. 对 W3/W4，需要最小的 set-valued response-bundle representation 修复，使 split/merge/deformation 与 raw-fragment re-entry 不被硬化为唯一 identity path；修复本身不能引入 tracker score、Hungarian 或 PERSON classifier。

## 下一步最小实验

建议 `U0 — Independent Observable Discrimination Audit`，只使用 T0 已冻结的 survivor 对：

- 组 A：W1/W5 径向分离、长期共同存活的 family pairs；
- 组 B：W3/W4 shared bundle / permutation cases；
- 组 C：W2 source recurrence 与 6 个 matched-null recurrence controls。

对每一组分别测试单个信息源：SAR-native unary structure、可部署 optical ordinal/interval cue、multi-target relation 或 event change-point。采用 A-only/B-only、完整 unavailable 状态和 pre-reference freeze；揭盲只回答“哪类具体错误解释被重新排除”，不做 score fusion、阈值搜索或最终框回归。

## 文件导航

- 逐图判断：`VISUAL_REVIEW.md`
- 冻结 construction：`pre_reference/`
- 揭盲逐帧诊断：`post_reference_diagnostic_only/reference_frame_diagnostic.csv`
- family 生存/参考关系：`post_reference_diagnostic_only/reference_family_diagnostic.csv`
- 外部复核：review pack ZIP
"""
    (OUTPUT / "REPORT.md").write_text(text, encoding="utf-8")
    return summary


def post_reference_diagnostic() -> None:
    verification = verify_pre_reference()
    if POST.exists():
        shutil.rmtree(POST)
    POST.mkdir(parents=True, exist_ok=True)
    if not REFERENCE.exists() or not FRAGMENT_TARGET_MAP.exists():
        raise FileNotFoundError("post-reference inputs are unavailable")
    reference = pd.read_parquet(REFERENCE)
    mapping = pd.read_csv(FRAGMENT_TARGET_MAP, encoding="utf-8-sig")
    diagnostic, family_diagnostic, track_summary, state_summary = build_post_reference_tables(reference, mapping)
    write_table(diagnostic, POST / "reference_frame_diagnostic")
    write_table(family_diagnostic, POST / "reference_family_diagnostic")
    write_table(track_summary, POST / "reference_window_track_summary")
    write_table(state_summary, POST / "reference_state_summary", parquet=False)
    write_json(POST / "post_reference_phase_state.json", {
        "pre_reference_verification": verification,
        "reference_path": str(REFERENCE),
        "reference_sha256": sha256_file(REFERENCE),
        "fragment_target_map_path": str(FRAGMENT_TARGET_MAP),
        "fragment_target_map_sha256": sha256_file(FRAGMENT_TARGET_MAP),
        "status": "REFERENCE_LOADED_ONLY_AFTER_VERIFIED_PRE_REFERENCE_FREEZE",
        "construction_changed": False,
    })

    events = pd.read_parquet(PRE / "candidate_region_family_events.parquet")
    data = {
        "frames": read_non_r04(FRAME_REGISTRY).rename(columns={"sar_frame_index": "frame_index"}),
        "regions": read_non_r04(Q95_REGIONS),
        "optical": read_non_r04(OPTICAL_PATH),
    }
    for window in WINDOWS:
        render_reference_overlay(window, diagnostic, events, data)

    relation = pd.read_parquet(PRE / "multi_target_relation_ablation_ledger.parquet")
    matched_top = read_non_r04(MATCHED_NULL_TOP)
    write_visual_review(track_summary, family_diagnostic, relation, matched_top)
    summary = write_final_report(verification, diagnostic, family_diagnostic, track_summary, state_summary, relation)
    manifest = build_artifact_manifest()
    print(json.dumps({
        "phase": "post",
        "pre_reference_verification": verification,
        "summary": summary,
        "artifact_count": len(manifest),
    }, ensure_ascii=False, indent=2))


def build_artifact_manifest() -> pd.DataFrame:
    rows = []
    for path in sorted(OUTPUT.rglob("*")):
        if path.is_file() and path.name != "ARTIFACT_MANIFEST.csv":
            rows.append({"path": str(path.relative_to(WORKSPACE)).replace("\\", "/"), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    frame = pd.DataFrame(rows)
    frame.to_csv(OUTPUT / "ARTIFACT_MANIFEST.csv", index=False, encoding="utf-8-sig")
    return frame


def build_pack() -> None:
    verify_pre_reference()
    if PACK.exists():
        shutil.rmtree(PACK)
    PACK.mkdir(parents=True, exist_ok=True)
    paths = [
        TASK / "README.md",
        SCRIPT,
        TASK / "validate_person_t0.py",
        OUTPUT / "REPORT_PRE_REFERENCE.md",
        OUTPUT / "REPORT.md",
        OUTPUT / "VISUAL_REVIEW.md",
    ]
    paths += sorted(PRE.glob("*.csv")) + sorted((PRE / "figures").glob("*.png"))
    paths += sorted(POST.glob("*.csv")) + sorted((POST / "figures").glob("*.png"))
    records = []
    for source in paths:
        if not source.exists():
            continue
        if source.is_relative_to(PRE):
            relative = Path("pre_reference") / source.relative_to(PRE)
        elif source.is_relative_to(POST):
            relative = Path("post_reference_diagnostic_only") / source.relative_to(POST)
        elif source.is_relative_to(TASK):
            relative = Path("task") / source.name
        else:
            relative = Path(source.name)
        destination = PACK / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        records.append({"relative_path": str(relative).replace("\\", "/"), "size_bytes": destination.stat().st_size, "sha256": sha256_file(destination)})
    readme = """# PERSON T0 external review pack

Review the frame atlases first, then candidate-evolution and P0 before/after figures. Use the CSV ledgers for exact status provenance. Yellow is full-fan Q95 support, green is corridor-admitted support, and magenta is support shared by selected optical fragments.

This pack is pre-reference construction evidence. Q95 is not PERSON segmentation; P0 is common apparent transport; family survival is not identity or final localization. The analyst had historical outcome knowledge, so the defensible boundary is the verified frozen tree rather than analyst blinding.
"""
    readme_path = PACK / "README.md"
    readme_path.write_text(readme, encoding="utf-8")
    records.append({"relative_path": "README.md", "size_bytes": readme_path.stat().st_size, "sha256": sha256_file(readme_path)})
    pd.DataFrame(records).sort_values("relative_path").to_csv(PACK / "MANIFEST.csv", index=False, encoding="utf-8-sig")
    if PACK_ZIP.exists():
        PACK_ZIP.unlink()
    with zipfile.ZipFile(PACK_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(PACK.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(PACK))
    print(json.dumps({"pack": str(PACK), "zip": str(PACK_ZIP), "file_count": len(records) + 1}, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["pre", "post", "pack", "manifest"], required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.phase == "pre":
        run_pre()
    elif args.phase == "post":
        post_reference_diagnostic()
    elif args.phase == "pack":
        build_pack()
    else:
        manifest = build_artifact_manifest()
        print(json.dumps({"artifact_count": len(manifest)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
