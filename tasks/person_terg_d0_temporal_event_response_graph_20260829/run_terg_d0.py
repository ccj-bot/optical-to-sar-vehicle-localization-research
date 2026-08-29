from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations, product
from pathlib import Path
from typing import Any, Iterable

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
STUDY = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OUTPUT = STUDY / "terg_d0_temporal_event_response_graph_mechanism_exploration"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference"
FIGURES = POST / "figures" / "temporal_review_packs"

OPTICAL_PATH = WORKSPACE / "output" / "person_optical_guided_sar_annotation_full_20260823" / "optical_person_frame_hypotheses.parquet"
REGION_ROOT = STUDY / "p1e_sar_only_response_interface" / "runtime_track_response_region_minimal_v1"
REGION_TABLE = REGION_ROOT / "response_region_table_pre_reference.csv"
REGION_MASKS = REGION_ROOT / "response_region_masks"
SHELL_ROOT = STUDY / "p1e_sar_only_response_interface" / "shell_uncertainty_region_topology_v1"
SHELL_TABLE = SHELL_ROOT / "optical_shell_uncertainty_decomposition_pre_reference.csv"
TOPOLOGY_TABLE = SHELL_ROOT / "gt_blind_shell_region_pixel_edges_pre_reference.csv"
OFFLINE_ASSIGNMENT = REGION_ROOT / "offline_one_to_one_track_reference_assignment.csv"
OFFLINE_REFERENCE = REGION_ROOT / "offline_reference_response_region_evaluation.csv"
CMR_ROOT = STUDY / "cmr_d0_common_residual_motion_mechanism_development"
CMR_ATLAS = CMR_ROOT / "cmr_eligible_window_atlas.csv"
CMR_SCRIPT = WORKSPACE / "tasks" / "person_cmr_d0_common_residual_motion_mechanism_development_20260829" / "run_cmr_d0_development.py"

DEVELOPMENT_RUNS = ("R01ZF", "R02ZF", "R03ZF")
LOCKED_CONFIRMATION_RUNS = ("R04ZF",)
TIMING_UNCERTAINTY_MS = 250
P0_SUPPORT_PIXEL_MIN = 1.0  # inherited frozen CMR/P0 graph-support primitive


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "||".join(str(x) for x in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20].upper()}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()


def bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().map({"true": True, "false": False, "1": True, "0": False}).fillna(False)


def load_cmr_module():
    spec = importlib.util.spec_from_file_location("terg_cmr_frozen", CMR_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen CMR development module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_interval(text: str) -> tuple[float, float]:
    values = json.loads(str(text))
    if not values:
        return math.nan, math.nan
    return float(min(v[0] for v in values)), float(max(v[1] for v in values))


def contiguous_intervals(values: Iterable[int]) -> list[tuple[int, int]]:
    items = sorted(set(int(v) for v in values))
    if not items:
        return []
    result: list[tuple[int, int]] = []
    start = previous = items[0]
    for value in items[1:]:
        if value != previous + 1:
            result.append((start, previous))
            start = value
        previous = value
    result.append((start, previous))
    return result


def interval_relation(a_low: float, a_high: float, b_low: float, b_high: float) -> str:
    if not all(np.isfinite([a_low, a_high, b_low, b_high])):
        return "ORDER_UNAVAILABLE"
    if a_high < b_low:
        return "A_LEFT_OF_B"
    if b_high < a_low:
        return "A_RIGHT_OF_B"
    return "ORDER_OVERLAP_OR_UNCERTAIN"


def load_pre_reference_authorities() -> dict[str, Any]:
    cmr = load_cmr_module()
    cmr_data = cmr.load_authorities()

    optical = pd.read_parquet(OPTICAL_PATH)
    optical = optical[
        optical["box_source"].astype(str).eq("DETECTED") & optical["run_id"].isin(DEVELOPMENT_RUNS)
    ].copy()
    optical["frame_index"] = optical["frame_index"].astype(int)
    optical["timestamp_ms"] = optical["timestamp_ms"].astype(int)

    shell = pd.read_csv(SHELL_TABLE)
    shell = shell[
        shell["run_id"].isin(DEVELOPMENT_RUNS)
        & shell["temporal_policy"].eq("SAME_FRAME")
        & shell["guard_variant"].eq("CURRENT_G6")
    ].copy()
    shell["frame_index"] = shell["frame_index"].astype(int)

    topology = pd.read_csv(TOPOLOGY_TABLE)
    topology = topology[
        topology["run_id"].isin(DEVELOPMENT_RUNS)
        & topology["temporal_policy"].eq("SAME_FRAME")
        & topology["guard_variant"].eq("CURRENT_G6")
        & topology["percentile_tag"].eq("Q095")
    ].copy()
    topology["frame_index"] = topology["frame_index"].astype(int)

    regions = pd.read_csv(REGION_TABLE)
    regions = regions[regions["run_id"].isin(DEVELOPMENT_RUNS) & regions["percentile_tag"].eq("Q095")].copy()
    regions["frame_index"] = regions["frame_index"].astype(int)

    return {
        "cmr": cmr,
        "cmr_data": cmr_data,
        "optical": optical,
        "shell": shell,
        "topology": topology,
        "regions": regions,
    }


def build_optical_frame_state(data: dict[str, Any]) -> pd.DataFrame:
    shell = data["shell"].copy()
    raw = shell["raw_box_intervals_json"].map(parse_interval)
    guarded = shell["effective_intervals_json"].map(parse_interval)
    shell["raw_theta_low_deg"] = [v[0] for v in raw]
    shell["raw_theta_high_deg"] = [v[1] for v in raw]
    shell["raw_theta_mid_deg"] = 0.5 * (shell["raw_theta_low_deg"] + shell["raw_theta_high_deg"])
    shell["guarded_theta_low_deg"] = [v[0] for v in guarded]
    shell["guarded_theta_high_deg"] = [v[1] for v in guarded]
    shell["track_id"] = shell["track_id"].astype(str)
    shell["active_track_count"] = shell.groupby(["run_id", "frame_index"])["track_id"].transform("nunique")
    shell["observation_boundary_or_truncation"] = (
        pd.to_numeric(shell["total_clip_deg"], errors="coerce").fillna(0).gt(0)
        | pd.to_numeric(shell["nearest_boundary_gap_deg"], errors="coerce").fillna(np.inf).le(0)
    )
    keep = [
        "run_id", "frame_uid", "frame_index", "sar_timestamp_ms", "nominal_optical_timestamp_ms",
        "sync_status", "track_id", "source_observation_count", "source_timestamp_min_ms",
        "source_timestamp_max_ms", "source_has_future_observation", "source_ambiguous_stitch_count_max",
        "raw_theta_low_deg", "raw_theta_high_deg", "raw_theta_mid_deg", "guarded_theta_low_deg",
        "guarded_theta_high_deg", "effective_width_deg", "left_clip_deg", "right_clip_deg",
        "total_clip_deg", "nearest_boundary_gap_deg", "active_track_count",
        "observation_boundary_or_truncation", "physical_target_id_used", "sar_reference_used",
        "strict_runtime_identity_claimed",
    ]
    state = shell[keep].sort_values(["run_id", "track_id", "frame_index"]).reset_index(drop=True)
    assert not state.duplicated(["run_id", "track_id", "frame_index"]).any()
    return state


def add_segment(rows: list[dict[str, Any]], run_id: str, start: int, end: int, tracks: Iterable[str],
                segment_kind: str, selection_reason: str) -> None:
    track_list = sorted(set(str(x) for x in tracks))
    if end < start or end - start + 1 < 5 or not track_list:
        return
    segment_id = stable_id("TERGS", run_id, start, end, ";".join(track_list), segment_kind)
    rows.append({
        "segment_id": segment_id,
        "run_id": run_id,
        "start_sar_frame": int(start),
        "end_sar_frame": int(end),
        "frame_count": int(end - start + 1),
        "track_ids": ";".join(track_list),
        "track_count": len(track_list),
        "segment_kind": segment_kind,
        "selection_reason": selection_reason,
        "manual_reference_used_for_selection": False,
        "confirmation_run_accessed": False,
    })


def frame_pair_relations(frame_state: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (run_id, frame_index), group in frame_state.groupby(["run_id", "frame_index"]):
        by_track = {str(r.track_id): r for r in group.itertuples(index=False)}
        for a, b in combinations(sorted(by_track), 2):
            ra, rb = by_track[a], by_track[b]
            relation = interval_relation(
                float(ra.raw_theta_low_deg), float(ra.raw_theta_high_deg),
                float(rb.raw_theta_low_deg), float(rb.raw_theta_high_deg),
            )
            gap = max(
                0.0,
                float(rb.raw_theta_low_deg) - float(ra.raw_theta_high_deg),
                float(ra.raw_theta_low_deg) - float(rb.raw_theta_high_deg),
            )
            rows.append({
                "run_id": run_id, "frame_index": int(frame_index), "track_a": a, "track_b": b,
                "optical_order_relation": relation, "interval_gap_deg": gap,
                "reference_used": False,
            })
    return pd.DataFrame(rows)


def build_base_segments(frame_state: pd.DataFrame, pair_relations: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for (run_id, track_id), group in frame_state.groupby(["run_id", "track_id"]):
        for start, end in contiguous_intervals(group["frame_index"]):
            add_segment(rows, run_id, start, end, [track_id], "CONTINUOUS_FRAGMENT_LIFECYCLE",
                        "GT_BLIND_CONTINUOUS_RUNTIME_VISIBLE_SHELL_PRESENCE")

    for run_id, group in frame_state.groupby("run_id"):
        frame_sets = group.groupby("frame_index")["track_id"].agg(lambda x: tuple(sorted(set(x.astype(str))))).sort_index()
        start = previous = int(frame_sets.index[0])
        active = frame_sets.iloc[0]
        for frame, tracks in frame_sets.iloc[1:].items():
            frame = int(frame)
            if frame != previous + 1 or tracks != active:
                add_segment(rows, run_id, start, previous, active, "ACTIVE_FRAGMENT_SET_PLATEAU",
                            "GT_BLIND_STABLE_RUNTIME_VISIBLE_ACTIVE_FRAGMENT_SET")
                start, active = frame, tracks
            previous = frame
        add_segment(rows, run_id, start, previous, active, "ACTIVE_FRAGMENT_SET_PLATEAU",
                    "GT_BLIND_STABLE_RUNTIME_VISIBLE_ACTIVE_FRAGMENT_SET")

    if not pair_relations.empty:
        for (run_id, track_a, track_b), group in pair_relations.groupby(["run_id", "track_a", "track_b"]):
            group = group.sort_values("frame_index")
            frames = group["frame_index"].astype(int).tolist()
            relations = group["optical_order_relation"].astype(str).tolist()
            start_i = 0
            for i in range(1, len(group) + 1):
                boundary = i == len(group) or frames[i] != frames[i - 1] + 1 or relations[i] != relations[i - 1]
                if boundary:
                    add_segment(rows, run_id, frames[start_i], frames[i - 1], [track_a, track_b],
                                "RELATIVE_ORDER_STATE_PLATEAU",
                                f"GT_BLIND_OPTICAL_INTERVAL_ORDER_STATE::{relations[start_i]}")
                    if i < len(group):
                        context_start = max(frames[start_i], frames[i - 1] - 4)
                        context_end = min(frames[-1], frames[i] + 4)
                        add_segment(rows, run_id, context_start, context_end, [track_a, track_b],
                                    "RELATIVE_ORDER_TRANSITION_CONTEXT",
                                    f"GT_BLIND_ORDER_STATE_CHANGE::{relations[i-1]}->{relations[i]}")
                    start_i = i

    frame = pd.DataFrame(rows).drop_duplicates("segment_id")
    return frame.sort_values(["run_id", "start_sar_frame", "end_sar_frame", "segment_kind"]).reset_index(drop=True)


def build_track_hypotheses(data: dict[str, Any], frame_state: pd.DataFrame) -> pd.DataFrame:
    topology = data["topology"]
    candidates = (
        topology.groupby(["run_id", "track_id", "frame_index"])["region_id"]
        .agg(lambda x: sorted(set(x.astype(str))))
        .to_dict()
    )
    model_keys = set(data["cmr_data"]["models"])
    rows: list[dict[str, Any]] = []
    for (run_id, track_id), group in frame_state.groupby(["run_id", "track_id"]):
        frames = sorted(group["frame_index"].astype(int).unique())
        for source in frames:
            destination = source + 1
            if destination not in frames or (run_id, source, destination) not in model_keys:
                continue
            source_regions = candidates.get((run_id, track_id, source), [])
            destination_regions = candidates.get((run_id, track_id, destination), [])
            for source_region, destination_region in product(source_regions, destination_regions):
                rows.append({
                    "track_hypothesis_id": stable_id("TERGH", run_id, track_id, source, destination, source_region, destination_region),
                    "run_id": run_id,
                    "track_id": str(track_id),
                    "source_sar_frame": int(source),
                    "destination_sar_frame": int(destination),
                    "source_region_id": source_region,
                    "destination_region_id": destination_region,
                    "manual_reference_used": False,
                    "identity_assignment_performed": False,
                })
    return pd.DataFrame(rows)


def build_graph(data: dict[str, Any], frame_state: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    hypotheses = build_track_hypotheses(data, frame_state)
    if hypotheses.empty:
        raise RuntimeError("no TERG graph hypotheses")
    cmr = data["cmr"]
    cmr.OUTPUT = PRE
    sar = cmr.develop_sar_p0_residual(hypotheses, data["cmr_data"])
    edges = hypotheses.merge(
        sar,
        on=["run_id", "source_sar_frame", "destination_sar_frame", "source_region_id", "destination_region_id"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_sar"),
    )
    edges["graph_edge_id"] = [
        stable_id("TERGE", r, t, s, d, sr, dr)
        for r, t, s, d, sr, dr in zip(
            edges["run_id"], edges["track_id"], edges["source_sar_frame"], edges["destination_sar_frame"],
            edges["source_region_id"], edges["destination_region_id"]
        )
    ]
    edges["p0_supported_continuation"] = pd.to_numeric(edges["soft_intersection_px"], errors="coerce").fillna(0).ge(P0_SUPPORT_PIXEL_MIN)
    edges["edge_relation"] = np.select(
        [
            edges["sar_p0_residual_state"].astype(str).str.contains("UNAVAILABLE"),
            ~edges["p0_supported_continuation"],
            edges["sar_topology_state"].astype(str).eq("P0_SPLIT_AND_MERGE_LIKE"),
            edges["sar_topology_state"].astype(str).eq("P0_SPLIT_LIKE"),
            edges["sar_topology_state"].astype(str).eq("P0_MERGE_LIKE"),
        ],
        [
            "P0_TRANSPORT_UNAVAILABLE", "P0_UNSUPPORTED_ALTERNATIVE", "P0_SPLIT_AND_MERGE_LIKE_CONTINUATION",
            "P0_SPLIT_LIKE_CONTINUATION", "P0_MERGE_LIKE_CONTINUATION",
        ],
        default="P0_SUPPORTED_CONTINUATION",
    )
    edges["edge_used_for_unique_tracking"] = False
    edges["reference_used"] = False

    topology = data["topology"].copy()
    regions = data["regions"].copy()
    nodes = topology.merge(
        regions,
        on=["run_id", "frame_uid", "frame_index", "percentile_tag", "region_id", "region_label"],
        how="left",
        validate="many_to_one",
        suffixes=("_corridor", ""),
    )
    nodes["track_node_id"] = [
        stable_id("TERGN", r, t, f, region)
        for r, t, f, region in zip(nodes["run_id"], nodes["track_id"], nodes["frame_index"], nodes["region_id"])
    ]
    nodes["theta_mid_deg"] = 0.5 * (pd.to_numeric(nodes["theta_min_deg"]) + pd.to_numeric(nodes["theta_max_deg"]))
    nodes["node_is_person_box"] = False
    nodes["reference_used"] = False

    nodes.to_parquet(PRE / "sar_response_graph_nodes_pre_reference.parquet", index=False, compression="zstd")
    edges.to_parquet(PRE / "sar_response_graph_edges_pre_reference.parquet", index=False, compression="zstd")
    return nodes, edges


def augment_segments_with_sar_contexts(segments: pd.DataFrame, frame_state: pd.DataFrame,
                                       nodes: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    rows = segments.to_dict("records")
    supported = edges[edges["p0_supported_continuation"]].copy()
    supported["split_like"] = supported["sar_topology_state"].astype(str).str.contains("SPLIT")
    supported["merge_like"] = supported["sar_topology_state"].astype(str).str.contains("MERGE")
    for run_id, group in supported.groupby("run_id"):
        active_by_frame = frame_state[frame_state["run_id"] == run_id].groupby("frame_index")["track_id"].agg(lambda x: sorted(set(x.astype(str)))).to_dict()
        for family, column in [("SAR_SPLIT_LIKE_CONTEXT", "split_like"), ("SAR_MERGE_LIKE_CONTEXT", "merge_like")]:
            counts = group[group[column]].groupby("source_sar_frame").size().sort_values(ascending=False)
            selected: list[int] = []
            for frame in counts.index.astype(int):
                if all(abs(frame - old) > 4 for old in selected):
                    selected.append(frame)
                if len(selected) == 3:
                    break
            for frame in selected:
                context_frames = range(frame - 3, frame + 5)
                tracks = sorted({t for f in context_frames for t in active_by_frame.get(f, [])})
                add_segment(rows, run_id, frame - 3, frame + 4, tracks, family,
                            "GT_BLIND_HIGH_COUNT_EXISTING_P0_TOPOLOGY_CONTEXT")

    boundary = nodes[
        bool_series(nodes["touches_observable_boundary"]) | bool_series(nodes["has_truncated_support"])
    ]
    for run_id, group in boundary.groupby("run_id"):
        counts = group.groupby("frame_index").size().sort_values(ascending=False)
        if len(counts):
            frame = int(counts.index[0])
            tracks = frame_state[(frame_state["run_id"] == run_id) & frame_state["frame_index"].between(frame - 3, frame + 4)]["track_id"].unique()
            add_segment(rows, run_id, frame - 3, frame + 4, tracks, "SAR_BOUNDARY_CENSOR_CONTEXT",
                        "GT_BLIND_Q95_BOUNDARY_OR_TRUNCATED_SUPPORT_CONTEXT")

    result = pd.DataFrame(rows).drop_duplicates("segment_id")
    return result.sort_values(["run_id", "start_sar_frame", "end_sar_frame", "segment_kind"]).reset_index(drop=True)


def build_optical_events(segments: pd.DataFrame, frame_state: pd.DataFrame,
                         pair_relations: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    track_bounds = frame_state.groupby(["run_id", "track_id"])["frame_index"].agg(["min", "max"]).to_dict("index")

    def append(segment: pd.Series, event_type: str, tracks: list[str], low: int, high: int,
               uncertainty: str, interpretations: list[str], evidence: str) -> None:
        rows.append({
            "optical_event_id": stable_id("TERGOE", segment.segment_id, event_type, ";".join(tracks), low, high),
            "segment_id": segment.segment_id, "run_id": segment.run_id, "event_type": event_type,
            "involved_track_ids": ";".join(tracks), "support_start_sar_frame": int(low),
            "support_end_sar_frame": int(high), "event_uncertainty_state": uncertainty,
            "competing_interpretations_json": json.dumps(interpretations, ensure_ascii=False),
            "observable_evidence": evidence, "event_is_hard_label": False, "manual_reference_used": False,
        })

    for segment in segments.itertuples(index=False):
        seg = pd.Series(segment._asdict())
        tracks = str(segment.track_ids).split(";")
        for track in tracks:
            state = frame_state[
                (frame_state["run_id"] == segment.run_id)
                & (frame_state["track_id"] == track)
                & frame_state["frame_index"].between(segment.start_sar_frame, segment.end_sar_frame)
            ]
            if state.empty:
                continue
            low, high = int(state["frame_index"].min()), int(state["frame_index"].max())
            append(seg, "OBSERVATION_PRESENCE_INTERVAL", [track], low, high,
                   "INTERVAL_OBSERVATION", ["continuous presence", "detector-supported fragment presence"],
                   f"runtime-visible shell presence in {state['frame_index'].nunique()} SAR frames")
            bounds = track_bounds[(segment.run_id, track)]
            if low == int(bounds["min"]):
                append(seg, "OBSERVATION_BIRTH_HYPOTHESIS", [track], low, min(high, low + 1),
                       "SET_VALUED", ["scene entry", "detector birth", "fragment start"],
                       "first runtime-visible observation of fragment")
            if high == int(bounds["max"]):
                append(seg, "OBSERVATION_DEATH_HYPOTHESIS", [track], max(low, high - 1), high,
                       "SET_VALUED", ["scene exit", "detector loss", "fragment end"],
                       "last runtime-visible observation of fragment")
            censored = state[bool_series(state["observation_boundary_or_truncation"])]
            if not censored.empty:
                append(seg, "OPTICAL_BOUNDARY_OR_TRUNCATION_STATE", [track],
                       int(censored["frame_index"].min()), int(censored["frame_index"].max()),
                       "UNCERTAINTY_STATE", ["partial visibility", "fan/common-FoV clipping", "bbox truncation"],
                       "runtime-visible shell interval touches an observable boundary")

        for track_a, track_b in combinations(sorted(tracks), 2):
            rel = pair_relations[
                (pair_relations["run_id"] == segment.run_id)
                & (pair_relations["track_a"] == track_a)
                & (pair_relations["track_b"] == track_b)
                & pair_relations["frame_index"].between(segment.start_sar_frame, segment.end_sar_frame)
            ].sort_values("frame_index")
            if rel.empty:
                continue
            states = rel["optical_order_relation"].astype(str)
            definite = set(states) & {"A_LEFT_OF_B", "A_RIGHT_OF_B"}
            if len(definite) == 1 and not states.eq("ORDER_OVERLAP_OR_UNCERTAIN").any():
                append(seg, "RELATIVE_ORDER_STABLE", [track_a, track_b], int(rel.frame_index.min()), int(rel.frame_index.max()),
                       "DEFINITE_INTERVAL_ORDER", sorted(definite), "raw optical angular intervals remain disjoint with stable order")
            if len(definite) == 2:
                left_frames = rel.loc[states.eq("A_LEFT_OF_B"), "frame_index"]
                right_frames = rel.loc[states.eq("A_RIGHT_OF_B"), "frame_index"]
                low = min(int(left_frames.max()), int(right_frames.max()))
                high = max(int(left_frames.min()), int(right_frames.min()))
                low, high = min(low, high), max(low, high)
                append(seg, "RELATIVE_ORDER_CHANGE_CANDIDATE", [track_a, track_b], low, high,
                       "SET_VALUED_TRANSITION_INTERVAL",
                       ["physical crossing", "depth-order projection", "detector switch", "grouping ambiguity"],
                       "definite optical interval order appears on both sides of the transition")
            overlap = rel[states.eq("ORDER_OVERLAP_OR_UNCERTAIN")]
            if not overlap.empty:
                append(seg, "RELATIVE_ORDER_OVERLAP_UNCERTAINTY", [track_a, track_b],
                       int(overlap.frame_index.min()), int(overlap.frame_index.max()), "UNCERTAINTY_STATE",
                       ["angular overlap", "possible occlusion", "projection ambiguity", "grouping ambiguity"],
                       "raw angular support intervals overlap")
            first_gap, last_gap = float(rel.iloc[0].interval_gap_deg), float(rel.iloc[-1].interval_gap_deg)
            if last_gap < first_gap:
                tendency = "PAIR_GAP_APPROACH_TENDENCY_DESCRIPTOR"
            elif last_gap > first_gap:
                tendency = "PAIR_GAP_SEPARATION_TENDENCY_DESCRIPTOR"
            else:
                tendency = "PAIR_GAP_STABLE_DESCRIPTOR"
            append(seg, tendency, [track_a, track_b], int(rel.frame_index.min()), int(rel.frame_index.max()),
                   "CONTINUOUS_SIGN_DESCRIPTOR_NO_FITTED_THRESHOLD",
                   ["angular support gap trend", "camera projection trend", "bbox deformation"],
                   f"endpoint interval gap changes from {first_gap:.4f} to {last_gap:.4f} deg")

    return pd.DataFrame(rows).drop_duplicates("optical_event_id").sort_values(["run_id", "segment_id", "support_start_sar_frame", "event_type"])


def components_for_segment(segment: pd.Series, track: str, nodes: pd.DataFrame, edges: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    n = nodes[
        (nodes["run_id"] == segment.run_id) & (nodes["track_id"].astype(str) == track)
        & nodes["frame_index"].between(segment.start_sar_frame, segment.end_sar_frame)
    ].copy()
    e = edges[
        (edges["run_id"] == segment.run_id) & (edges["track_id"].astype(str) == track)
        & edges["source_sar_frame"].between(segment.start_sar_frame, segment.end_sar_frame - 1)
        & edges["p0_supported_continuation"]
    ].copy()
    graph = nx.DiGraph()
    node_key = {(str(r.region_id), int(r.frame_index)): str(r.track_node_id) for r in n.itertuples(index=False)}
    graph.add_nodes_from(n["track_node_id"].astype(str))
    for row in e.itertuples(index=False):
        source = node_key.get((str(row.source_region_id), int(row.source_sar_frame)))
        destination = node_key.get((str(row.destination_region_id), int(row.destination_sar_frame)))
        if source and destination:
            graph.add_edge(source, destination, graph_edge_id=str(row.graph_edge_id))

    edge_by_id = e.set_index("graph_edge_id", drop=False)

    summaries: list[dict[str, Any]] = []
    memberships: list[dict[str, Any]] = []
    for component_nodes in nx.weakly_connected_components(graph):
        sub = n[n["track_node_id"].astype(str).isin(component_nodes)].copy()
        component_id = stable_id("TERGXC", segment.segment_id, track, ";".join(sorted(component_nodes)))
        component_edge_ids = [
            str(payload["graph_edge_id"])
            for _, _, payload in graph.subgraph(component_nodes).edges(data=True)
        ]
        sub_edges = edge_by_id.loc[component_edge_ids] if component_edge_ids else e.iloc[0:0]
        frames = sorted(sub["frame_index"].astype(int).unique())
        summaries.append({
            "explanation_component_id": component_id, "segment_id": segment.segment_id,
            "run_id": segment.run_id, "track_id": track, "segment_start_sar_frame": int(segment.start_sar_frame),
            "segment_end_sar_frame": int(segment.end_sar_frame), "segment_frame_count": int(segment.frame_count),
            "component_start_sar_frame": min(frames), "component_end_sar_frame": max(frames),
            "component_frame_count": len(frames), "component_node_count": len(sub),
            "component_supported_edge_count": len(sub_edges),
            "component_transition_count": sub_edges[["source_sar_frame", "destination_sar_frame"]].drop_duplicates().shape[0] if len(sub_edges) else 0,
            "component_frame_coverage_fraction": len(frames) / int(segment.frame_count),
            "contains_split_like": bool(sub_edges["sar_topology_state"].astype(str).str.contains("SPLIT").any()) if len(sub_edges) else False,
            "contains_merge_like": bool(sub_edges["sar_topology_state"].astype(str).str.contains("MERGE").any()) if len(sub_edges) else False,
            "contains_deformation": bool(sub_edges["sar_p0_residual_state"].astype(str).str.contains("DEFORMATION").any()) if len(sub_edges) else False,
            "contains_boundary_censoring": bool(bool_series(sub["touches_observable_boundary"]).any() or bool_series(sub["has_truncated_support"]).any()),
            "unique_path_claimed": False, "identity_claimed": False, "manual_reference_used": False,
        })
        for row in sub.itertuples(index=False):
            memberships.append({
                "explanation_component_id": component_id, "segment_id": segment.segment_id,
                "run_id": segment.run_id, "track_id": track, "frame_index": int(row.frame_index),
                "region_id": str(row.region_id), "track_node_id": str(row.track_node_id),
                "theta_mid_deg": float(row.theta_mid_deg), "manual_reference_used": False,
            })
    return summaries, memberships


def build_explanation_sets(segments: pd.DataFrame, nodes: pd.DataFrame, edges: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summaries: list[dict[str, Any]] = []
    memberships: list[dict[str, Any]] = []
    set_rows: list[dict[str, Any]] = []
    for segment in segments.itertuples(index=False):
        seg = pd.Series(segment._asdict())
        for track in str(segment.track_ids).split(";"):
            comps, members = components_for_segment(seg, track, nodes, edges)
            summaries.extend(comps)
            memberships.extend(members)
            static_nodes = nodes[
                (nodes["run_id"] == segment.run_id) & (nodes["track_id"].astype(str) == track)
                & nodes["frame_index"].between(segment.start_sar_frame, segment.end_sar_frame)
            ]
            multi = [x for x in comps if x["component_frame_count"] >= 2]
            isolated = [x for x in comps if x["component_frame_count"] == 1]
            set_rows.append({
                "segment_id": segment.segment_id, "run_id": segment.run_id, "track_id": track,
                "static_corridor_node_count": len(static_nodes), "plausible_explanation_component_count": len(comps),
                "multi_frame_component_count": len(multi), "isolated_component_count": len(isolated),
                "temporally_supported_node_count": sum(x["component_node_count"] for x in multi),
                "potential_disambiguation_gt_blind": bool(multi and isolated),
                "explanation_is_set_valued": True, "unique_component_selected": False,
                "manual_reference_used": False,
            })
    return pd.DataFrame(summaries), pd.DataFrame(memberships), pd.DataFrame(set_rows)


def build_sar_events(components: pd.DataFrame, memberships: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    supported = edges[edges["p0_supported_continuation"]].copy()
    edge_groups: dict[str, pd.DataFrame] = {}
    for (segment_id, run_id, track_id), member_group in memberships.groupby(["segment_id", "run_id", "track_id"]):
        component_map = {
            (int(row.frame_index), str(row.region_id)): str(row.explanation_component_id)
            for row in member_group.itertuples(index=False)
        }
        component_meta = components[
            (components["segment_id"] == segment_id) & (components["track_id"].astype(str) == str(track_id))
        ]
        if component_meta.empty:
            continue
        start = int(component_meta["segment_start_sar_frame"].iloc[0])
        end = int(component_meta["segment_end_sar_frame"].iloc[0])
        candidate_edges = supported[
            (supported["run_id"] == run_id) & (supported["track_id"].astype(str) == str(track_id))
            & supported["source_sar_frame"].between(start, end - 1)
        ].copy()
        if candidate_edges.empty:
            continue
        candidate_edges["source_component_id"] = [
            component_map.get((int(f), str(region)), "")
            for f, region in zip(candidate_edges["source_sar_frame"], candidate_edges["source_region_id"])
        ]
        candidate_edges["destination_component_id"] = [
            component_map.get((int(f), str(region)), "")
            for f, region in zip(candidate_edges["destination_sar_frame"], candidate_edges["destination_region_id"])
        ]
        candidate_edges = candidate_edges[
            candidate_edges["source_component_id"].ne("")
            & candidate_edges["source_component_id"].eq(candidate_edges["destination_component_id"])
        ]
        for component_id, group in candidate_edges.groupby("source_component_id"):
            edge_groups[str(component_id)] = group

    for component in components.itertuples(index=False):
        def append(event_type: str, low: int, high: int, uncertainty: str, evidence: str) -> None:
            rows.append({
                "sar_event_id": stable_id("TERGSE", component.explanation_component_id, event_type, low, high),
                "segment_id": component.segment_id, "run_id": component.run_id,
                "explanation_component_id": component.explanation_component_id, "track_id": component.track_id,
                "event_type": event_type, "support_start_sar_frame": int(low), "support_end_sar_frame": int(high),
                "event_uncertainty_state": uncertainty, "observable_evidence": evidence,
                "event_is_person_event": False, "event_is_hard_label": False, "manual_reference_used": False,
            })
        append("SAR_RESPONSE_PERSISTENCE" if component.component_frame_count >= 2 else "SAR_SINGLE_FRAME_RESPONSE_HYPOTHESIS",
               component.component_start_sar_frame, component.component_end_sar_frame,
               "GRAPH_COMPONENT_HYPOTHESIS", f"{component.component_node_count} q95 nodes and {component.component_supported_edge_count} P0-supported edges")
        if component.component_start_sar_frame > component.segment_start_sar_frame:
            append("SAR_RESPONSE_BIRTH_WITHIN_SEGMENT", component.component_start_sar_frame, component.component_start_sar_frame,
                   "SET_VALUED", "first q95 node in this explanation component")
        if component.component_end_sar_frame < component.segment_end_sar_frame:
            append("SAR_RESPONSE_DEATH_WITHIN_SEGMENT", component.component_end_sar_frame, component.component_end_sar_frame,
                   "SET_VALUED", "last q95 node in this explanation component")
        e = edge_groups.get(str(component.explanation_component_id), supported.iloc[0:0])
        for family, pattern in [
            ("SAR_SPLIT_LIKE_HYPOTHESIS", "SPLIT"), ("SAR_MERGE_LIKE_HYPOTHESIS", "MERGE"),
            ("SAR_DEFORMATION_HYPOTHESIS", "DEFORMATION"), ("SAR_BOUNDARY_CENSORING_STATE", "BOUNDARY_CENSORED"),
        ]:
            column = "sar_topology_state" if pattern in {"SPLIT", "MERGE"} else "sar_p0_residual_state"
            match = e[e[column].astype(str).str.contains(pattern)]
            if not match.empty:
                append(family, int(match.source_sar_frame.min()), int(match.destination_sar_frame.max()),
                       "STRUCTURAL_HYPOTHESIS", f"existing frozen {column} contains {pattern}")
    return pd.DataFrame(rows).drop_duplicates("sar_event_id")


def build_event_relations(optical_events: pd.DataFrame, sar_events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for segment_id, optical_group in optical_events.groupby("segment_id"):
        sar_group = sar_events[sar_events["segment_id"] == segment_id]
        for optical_event in optical_group.itertuples(index=False):
            if sar_group.empty:
                rows.append({
                    "event_relation_id": stable_id("TERGER", optical_event.optical_event_id, "NO_SAR_EVENT"),
                    "segment_id": segment_id, "run_id": optical_event.run_id,
                    "optical_event_id": optical_event.optical_event_id, "optical_event_type": optical_event.event_type,
                    "sar_event_id": "", "sar_event_type": "NO_OBSERVABLE_SAR_EVENT_IN_EXPLANATION_SET",
                    "temporal_relation": "SAR_EVENT_UNAVAILABLE", "timing_uncertainty_ms": TIMING_UNCERTAINTY_MS,
                    "relation_semantics": "COOCCURRENCE_NOT_CAUSAL_OR_IDENTITY", "manual_reference_used": False,
                })
                continue
            for sar_event in sar_group.itertuples(index=False):
                optical_low = int(optical_event.support_start_sar_frame)
                optical_high = int(optical_event.support_end_sar_frame)
                sar_low = int(sar_event.support_start_sar_frame)
                sar_high = int(sar_event.support_end_sar_frame)
                # Frame intervals remain primary. +/-250 ms is recorded as an uncalibrated widening descriptor.
                if max(optical_low, sar_low) <= min(optical_high, sar_high):
                    relation = "TEMPORAL_SUPPORT_OVERLAP"
                elif optical_high < sar_low:
                    relation = "OPTICAL_BEFORE_SAR"
                else:
                    relation = "SAR_BEFORE_OPTICAL"
                rows.append({
                    "event_relation_id": stable_id("TERGER", optical_event.optical_event_id, sar_event.sar_event_id),
                    "segment_id": segment_id, "run_id": optical_event.run_id,
                    "optical_event_id": optical_event.optical_event_id, "optical_event_type": optical_event.event_type,
                    "sar_event_id": sar_event.sar_event_id, "sar_event_type": sar_event.event_type,
                    "temporal_relation": relation, "timing_uncertainty_ms": TIMING_UNCERTAINTY_MS,
                    "relation_semantics": "COOCCURRENCE_NOT_CAUSAL_OR_IDENTITY", "manual_reference_used": False,
                })
    return pd.DataFrame(rows)


def build_compatibility_profiles(segments: pd.DataFrame, frame_state: pd.DataFrame, components: pd.DataFrame,
                                 memberships: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for component in components.itertuples(index=False):
        segment = segments.loc[segments["segment_id"] == component.segment_id].iloc[0]
        member = memberships[memberships["explanation_component_id"] == component.explanation_component_id]
        covered_frames = set(member["frame_index"].astype(int))
        optical_frames = set(frame_state[
            (frame_state["run_id"] == component.run_id) & (frame_state["track_id"].astype(str) == str(component.track_id))
            & frame_state["frame_index"].between(segment.start_sar_frame, segment.end_sar_frame)
        ]["frame_index"].astype(int))
        transitions = max(0, len(optical_frames) - 1)
        bridged = int(component.component_transition_count)
        lifecycle = "LIFECYCLE_COMPLETE" if covered_frames == optical_frames and optical_frames else (
            "LIFECYCLE_PARTIAL" if covered_frames else "LIFECYCLE_UNAVAILABLE"
        )
        continuity = "P0_CONTINUITY_COMPLETE" if transitions and bridged >= transitions else (
            "P0_CONTINUITY_PARTIAL" if bridged else "P0_CONTINUITY_UNAVAILABLE"
        )
        rows.append({
            "compatibility_profile_id": stable_id("TERGCP", component.explanation_component_id),
            "segment_id": component.segment_id, "run_id": component.run_id, "track_id": component.track_id,
            "explanation_component_id": component.explanation_component_id,
            "lifecycle_compatibility": lifecycle,
            "corridor_compatibility": "CORRIDOR_COMPLETE" if covered_frames == optical_frames and optical_frames else "CORRIDOR_PARTIAL",
            "p0_continuity_compatibility": continuity,
            "topology_state": "MULTI_TOPOLOGY_OR_DEFORMATION" if component.contains_split_like or component.contains_merge_like or component.contains_deformation else "PERSISTENCE_OR_SINGLE_RESPONSE",
            "evidence_conflict_preserved": bool(lifecycle == "LIFECYCLE_COMPLETE" and continuity != "P0_CONTINUITY_COMPLETE"),
            "weighted_score_used": False, "pruning_performed": False, "manual_reference_used": False,
        })
    return pd.DataFrame(rows)


def build_order_compatibility(segments: pd.DataFrame, pair_relations: pd.DataFrame, components: pd.DataFrame,
                              memberships: pd.DataFrame, nodes: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    node_lookup = nodes[["track_node_id", "theta_min_deg", "theta_max_deg"]].drop_duplicates("track_node_id")
    member = memberships.merge(node_lookup, on="track_node_id", how="left", validate="many_to_one")
    for segment in segments.itertuples(index=False):
        tracks = sorted(str(segment.track_ids).split(";"))
        if len(tracks) < 2:
            continue
        for track_a, track_b in combinations(tracks, 2):
            optical = pair_relations[
                (pair_relations["run_id"] == segment.run_id) & (pair_relations["track_a"] == track_a)
                & (pair_relations["track_b"] == track_b)
                & pair_relations["frame_index"].between(segment.start_sar_frame, segment.end_sar_frame)
            ]
            optical_states = set(optical["optical_order_relation"].astype(str))
            if len(optical_states) == 1:
                optical_state = next(iter(optical_states))
            elif optical_states:
                optical_state = "OPTICAL_ORDER_SET_VALUED"
            else:
                optical_state = "ORDER_UNAVAILABLE"
            comps_a = components[(components["segment_id"] == segment.segment_id) & (components["track_id"].astype(str) == track_a)]
            comps_b = components[(components["segment_id"] == segment.segment_id) & (components["track_id"].astype(str) == track_b)]
            component_ids_a = set(comps_a["explanation_component_id"].astype(str))
            component_ids_b = set(comps_b["explanation_component_id"].astype(str))
            ma = member[member["explanation_component_id"].astype(str).isin(component_ids_a)]
            mb = member[member["explanation_component_id"].astype(str).isin(component_ids_b)]
            common_frames = sorted(set(ma.frame_index.astype(int)) & set(mb.frame_index.astype(int)))
            sar_states: list[str] = []
            shared = False
            shared_region_frame_count = 0
            for frame in common_frames:
                fa = ma[ma.frame_index == frame]
                fb = mb[mb.frame_index == frame]
                if set(fa.region_id.astype(str)) & set(fb.region_id.astype(str)):
                    shared = True
                    shared_region_frame_count += 1
                    sar_states.append("SAR_SHARED_RESPONSE_ORDER_UNDEFINED")
                    continue
                sar_states.append(interval_relation(
                    float(fa.theta_min_deg.min()), float(fa.theta_max_deg.max()),
                    float(fb.theta_min_deg.min()), float(fb.theta_max_deg.max()),
                ))
            unique_sar = set(sar_states)
            sar_state = next(iter(unique_sar)) if len(unique_sar) == 1 else (
                "SAR_ORDER_SET_VALUED" if unique_sar else "ORDER_UNAVAILABLE"
            )
            if shared:
                relation = "SHARED_RESPONSE_ORDER_UNDEFINED"
            elif optical_state in {"A_LEFT_OF_B", "A_RIGHT_OF_B"} and sar_state == optical_state:
                relation = "ORDER_SUPPORTIVE"
            elif optical_state in {"A_LEFT_OF_B", "A_RIGHT_OF_B"} and sar_state in {"A_LEFT_OF_B", "A_RIGHT_OF_B"}:
                relation = "ORDER_CONTRADICTORY"
            elif "UNAVAILABLE" in optical_state or "UNAVAILABLE" in sar_state:
                relation = "ORDER_UNAVAILABLE"
            else:
                relation = "ORDER_AMBIGUOUS"
            rows.append({
                "order_profile_id": stable_id("TERGOP", segment.segment_id, track_a, track_b),
                "segment_id": segment.segment_id, "run_id": segment.run_id, "track_a": track_a, "track_b": track_b,
                "component_a_count": len(comps_a), "component_b_count": len(comps_b),
                "component_pair_space_size": len(comps_a) * len(comps_b),
                "optical_order_state": optical_state, "sar_order_state": sar_state,
                "relative_order_compatibility": relation, "common_frame_count": len(common_frames),
                "shared_response_observed": shared, "shared_region_frame_count": shared_region_frame_count,
                "order_representation": "SET_VALUED_AGGREGATE_OVER_ALL_EXPLANATION_COMPONENTS",
                "weighted_score_used": False, "manual_reference_used": False,
            })
    return pd.DataFrame(rows)


def build_vocabulary_and_counterexamples(optical_events: pd.DataFrame, sar_events: pd.DataFrame,
                                         relations: pd.DataFrame, order: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for modality, events, id_col in [("OPTICAL", optical_events, "optical_event_id"), ("SAR", sar_events, "sar_event_id")]:
        for event_type, group in events.groupby("event_type"):
            segment_count = int(group["segment_id"].nunique())
            run_count = int(group["run_id"].nunique())
            if event_type.endswith("DESCRIPTOR") or "TENDENCY_DESCRIPTOR" in event_type:
                disposition = "DESCRIPTOR_NOT_HARD_EVENT"
            elif "UNCERTAINTY" in event_type or "BOUNDARY" in event_type:
                disposition = "UNCERTAINTY_OR_CENSORING_STATE"
            elif segment_count >= 2:
                disposition = "REPEATED_PROVISIONAL_EVENT_PRIMITIVE"
            else:
                disposition = "SINGLE_CASE_HYPOTHESIS_RETAINED_FOR_COUNTEREXAMPLE_REVIEW"
            rows.append({
                "modality": modality, "event_type": event_type, "instance_count": len(group),
                "segment_count": segment_count, "run_count": run_count, "vocabulary_disposition": disposition,
                "threshold_fitted_to_outcome": False, "reference_used": False,
            })

    counters: list[dict[str, Any]] = []
    overlap = relations[relations["temporal_relation"] == "TEMPORAL_SUPPORT_OVERLAP"]
    for event_type, group in optical_events.groupby("event_type"):
        event_ids = set(group["optical_event_id"])
        with_overlap = set(overlap[overlap["optical_event_id"].isin(event_ids)]["optical_event_id"])
        for event_id in sorted(event_ids - with_overlap):
            row = group[group["optical_event_id"] == event_id].iloc[0]
            counters.append({
                "counterexample_id": stable_id("TERGCE", event_id, "NO_OVERLAP"), "segment_id": row.segment_id,
                "run_id": row.run_id, "hypothesis_under_test": event_type,
                "counterexample_type": "OPTICAL_EVENT_WITHOUT_OVERLAPPING_SAR_EVENT_IN_EXPLANATION_SET",
                "representation_implication": "do not require a same-name or synchronous SAR event",
                "reference_used": False,
            })
    if not order.empty:
        for row in order[order["relative_order_compatibility"].isin(["ORDER_CONTRADICTORY", "SHARED_RESPONSE_ORDER_UNDEFINED"])].itertuples(index=False):
            counters.append({
                "counterexample_id": stable_id("TERGCE", row.order_profile_id), "segment_id": row.segment_id,
                "run_id": row.run_id, "hypothesis_under_test": "RELATIVE_ORDER_IS_ALWAYS_CROSS_MODAL_DETERMINATE",
                "counterexample_type": row.relative_order_compatibility,
                "representation_implication": "retain set-valued/shared order rather than force a pair assignment",
                "reference_used": False,
            })
    return pd.DataFrame(rows), pd.DataFrame(counters).drop_duplicates("counterexample_id")


def source_manifest() -> dict[str, Any]:
    paths = [OPTICAL_PATH, REGION_TABLE, SHELL_TABLE, TOPOLOGY_TABLE, CMR_SCRIPT, CMR_ATLAS]
    return {
        "schema": "PERSON_TERG_D0_SOURCE_AUTHORITY_MANIFEST_V1",
        "created_at": now_iso(), "git_head": git_head(), "development_runs": list(DEVELOPMENT_RUNS),
        "locked_confirmation_runs": list(LOCKED_CONFIRMATION_RUNS), "old_work_used": False,
        "files": [{"path": str(p.relative_to(WORKSPACE)), "bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in paths],
        "offline_reference_loaded": False, "offline_assignment_loaded": False,
    }


def discover() -> None:
    if (PRE / "pre_reference_manifest.json").exists():
        raise RuntimeError("pre-reference TERG discovery is already frozen")
    PRE.mkdir(parents=True, exist_ok=True)
    print("TERG discover: loading pre-reference authorities", flush=True)
    data = load_pre_reference_authorities()
    frame_state = build_optical_frame_state(data)
    pair_relations = frame_pair_relations(frame_state)
    base_segments = build_base_segments(frame_state, pair_relations)
    print(f"TERG discover: frame states={len(frame_state)} base segments={len(base_segments)}", flush=True)
    node_checkpoint = PRE / "sar_response_graph_nodes_pre_reference.parquet"
    edge_checkpoint = PRE / "sar_response_graph_edges_pre_reference.parquet"
    if node_checkpoint.exists() and edge_checkpoint.exists():
        nodes = pd.read_parquet(node_checkpoint)
        edges = pd.read_parquet(edge_checkpoint)
        print(f"TERG discover: reused complete graph checkpoint nodes={len(nodes)} edges={len(edges)}", flush=True)
    else:
        nodes, edges = build_graph(data, frame_state)
        print(f"TERG discover: built graph nodes={len(nodes)} edges={len(edges)}", flush=True)
    segments = augment_segments_with_sar_contexts(base_segments, frame_state, nodes, edges)
    optical_events = build_optical_events(segments, frame_state, pair_relations)
    print(f"TERG discover: augmented segments={len(segments)} optical events={len(optical_events)}", flush=True)
    components, memberships, explanation_sets = build_explanation_sets(segments, nodes, edges)
    print(f"TERG discover: components={len(components)} memberships={len(memberships)}", flush=True)
    sar_events = build_sar_events(components, memberships, edges)
    event_relations = build_event_relations(optical_events, sar_events)
    compatibility = build_compatibility_profiles(segments, frame_state, components, memberships, edges)
    order = build_order_compatibility(segments, pair_relations, components, memberships, nodes)
    vocabulary, counterexamples = build_vocabulary_and_counterexamples(optical_events, sar_events, event_relations, order)
    print(f"TERG discover: SAR events={len(sar_events)} event relations={len(event_relations)} order profiles={len(order)}", flush=True)

    representation_changes = pd.DataFrame([{
        "change_id": "TERG_D0_CHANGE_001_COMPONENT_PAIR_ORDER_AGGREGATION",
        "original_design": "materialize every explanation-component pair for relative-order compatibility",
        "real_data_counterexample": "corridor graphs contain many isolated and multi-frame components, making the Cartesian pair space combinatorial and semantically suggestive of a hidden assignment search",
        "failure_reason": "representation does not match set-valued ambiguity and creates unnecessary component-pair enumeration",
        "new_representation": "one set-valued aggregate order profile per optical track pair and segment, retaining component counts, pair-space size, shared frames, and all observed SAR order states",
        "new_semantics": "relation over explanation sets rather than candidate assignment pairs",
        "reference_used": False, "search_expanded": False,
        "side_effect": "individual component-pair IDs are not materialized; aggregate ambiguity and pair-space size remain explicit",
        "old_baseline_retained": True,
    }])

    tables = {
        "optical_temporal_frame_state_pre_reference": frame_state,
        "optical_pair_order_state_pre_reference": pair_relations,
        "temporal_segment_atlas_pre_reference": segments,
        "optical_event_hypotheses_pre_reference": optical_events,
        "terg_explanation_components_pre_reference": components,
        "terg_component_node_membership_pre_reference": memberships,
        "terg_explanation_sets_pre_reference": explanation_sets,
        "sar_event_hypotheses_pre_reference": sar_events,
        "cross_modal_event_relations_pre_reference": event_relations,
        "cross_modal_compatibility_profiles_pre_reference": compatibility,
        "relative_order_compatibility_pre_reference": order,
        "event_vocabulary_discovery_pre_reference": vocabulary,
        "counterexample_ledger_pre_reference": counterexamples,
        "representation_change_ledger_pre_reference": representation_changes,
    }
    for name, frame in tables.items():
        frame.to_parquet(PRE / f"{name}.parquet", index=False, compression="zstd")
        if len(frame) <= 250000:
            frame.to_csv(PRE / f"{name}.csv", index=False, encoding="utf-8-sig")

    write_json(OUTPUT / "source_authority_manifest.json", source_manifest())
    summary = {
        "schema": "PERSON_TERG_D0_PRE_REFERENCE_DISCOVERY_SUMMARY_V1", "created_at": now_iso(),
        "development_runs": list(DEVELOPMENT_RUNS), "confirmation_runs_accessed": False,
        "optical_track_frame_states": len(frame_state), "temporal_segments": len(segments),
        "segment_kind_counts": segments["segment_kind"].value_counts().to_dict(),
        "graph_nodes": len(nodes), "graph_edge_hypotheses": len(edges),
        "p0_supported_edges": int(edges["p0_supported_continuation"].sum()),
        "explanation_components": len(components), "explanation_sets": len(explanation_sets),
        "potential_disambiguation_sets": int(explanation_sets["potential_disambiguation_gt_blind"].sum()),
        "optical_event_counts": optical_events["event_type"].value_counts().to_dict(),
        "sar_event_counts": sar_events["event_type"].value_counts().to_dict(),
        "order_compatibility_counts": order["relative_order_compatibility"].value_counts().to_dict() if len(order) else {},
        "counterexample_count": len(counterexamples), "manual_reference_used": False,
        "weighted_score_used": False, "unique_tracking_performed": False, "final_localization_performed": False,
    }
    write_json(PRE / "pre_reference_discovery_summary.json", summary)

    files = sorted(p for p in PRE.rglob("*") if p.is_file())
    manifest = {
        "schema": "PERSON_TERG_D0_PRE_REFERENCE_HASH_FREEZE_V1", "created_at": now_iso(),
        "status": "PRE_REFERENCE_TEMPORAL_ATLAS_GRAPH_EVENTS_AND_EXPLANATION_SETS_FROZEN",
        "reference_loaded": False, "assignment_loaded": False, "confirmation_run_accessed": False,
        "files": [{"path": str(p.relative_to(WORKSPACE)), "bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in files],
    }
    write_json(PRE / "pre_reference_manifest.json", manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def verify_pre_reference() -> dict[str, Any]:
    path = PRE / "pre_reference_manifest.json"
    if not path.exists():
        raise RuntimeError("pre-reference manifest missing")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for item in manifest["files"]:
        file_path = WORKSPACE / item["path"]
        if not file_path.exists() or file_path.stat().st_size != int(item["bytes"]) or sha256_file(file_path) != item["sha256"]:
            raise RuntimeError(f"pre-reference file changed: {file_path}")
    return manifest


def load_pre_table(name: str) -> pd.DataFrame:
    return pd.read_parquet(PRE / f"{name}.parquet")


def build_grounding(segments: pd.DataFrame, explanation_sets: pd.DataFrame,
                    components: pd.DataFrame, memberships: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    assignment = pd.read_csv(OFFLINE_ASSIGNMENT)
    assignment = assignment[
        assignment["run_id"].isin(DEVELOPMENT_RUNS)
        & assignment["interface_kind"].eq("RAW_DETECTED_FRAGMENT_ALL")
        & pd.to_numeric(assignment["time_window_half_width_ms"], errors="coerce").eq(0)
        & assignment["assigned_track_id_offline"].notna()
    ].copy()
    reference = pd.read_csv(OFFLINE_REFERENCE)
    reference = reference[reference["run_id"].isin(DEVELOPMENT_RUNS) & reference["percentile_tag"].eq("Q095")].copy()
    segment_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    for item in explanation_sets.itertuples(index=False):
        segment = segments[segments["segment_id"] == item.segment_id].iloc[0]
        a = assignment[
            (assignment["run_id"] == item.run_id)
            & (assignment["assigned_track_id_offline"].astype(str) == str(item.track_id))
            & assignment["frame_index"].between(segment.start_sar_frame, segment.end_sar_frame)
        ]
        counts = a["target_id"].astype(str).value_counts()
        if len(counts) == 1 and int(a["frame_index"].nunique()) >= 2:
            state = "LIKELY"
        elif len(counts) > 1:
            state = "AMBIGUOUS"
        else:
            state = "UNRESOLVED"
        dominant_target = str(counts.index[0]) if len(counts) else ""
        segment_rows.append({
            "segment_id": item.segment_id, "run_id": item.run_id, "track_id": item.track_id,
            "grounding_state": state, "dominant_target_id_offline": dominant_target,
            "assigned_frame_count": int(a["frame_index"].nunique()), "unique_target_count": len(counts),
            "dominant_target_fraction": float(counts.iloc[0] / counts.sum()) if len(counts) else math.nan,
            "grounding_semantics": "OFFLINE_FRAME_LEVEL_GEOMETRIC_REFERENCE_NOT_RUNTIME_IDENTITY",
            "runtime_use_allowed": False,
        })
        comps = components[(components["segment_id"] == item.segment_id) & (components["track_id"].astype(str) == str(item.track_id))]
        target_ref = reference[
            (reference["run_id"] == item.run_id) & (reference["target_id"].astype(str) == dominant_target)
            & reference["frame_index"].between(segment.start_sar_frame, segment.end_sar_frame)
            & reference["nearest_region_id"].notna()
        ] if dominant_target else reference.iloc[0:0]
        supported_components = 0
        temp_rows: list[dict[str, Any]] = []
        for component in comps.itertuples(index=False):
            member = memberships[memberships["explanation_component_id"] == component.explanation_component_id]
            hits = target_ref.merge(member[["frame_index", "region_id"]], left_on=["frame_index", "nearest_region_id"], right_on=["frame_index", "region_id"], how="inner")
            hit_frames = int(hits["frame_index"].nunique())
            if hit_frames:
                supported_components += 1
            temp_rows.append({
                "segment_id": item.segment_id, "run_id": item.run_id, "track_id": item.track_id,
                "explanation_component_id": component.explanation_component_id,
                "dominant_target_id_offline": dominant_target, "reference_frame_count": int(target_ref["frame_index"].nunique()),
                "reference_supported_component_frame_count": hit_frames,
                "shared_reference_frame_count": int(hits["shared_region_flag"].fillna(False).astype(bool).sum()) if len(hits) else 0,
            })
        for row in temp_rows:
            if state != "LIKELY":
                component_state = f"{state}_SEGMENT_GROUNDING"
            elif supported_components > 1 and row["reference_supported_component_frame_count"] > 0:
                component_state = "MULTIPLE_VALID_EXPLANATIONS"
            elif row["reference_supported_component_frame_count"] >= 2:
                component_state = "LIKELY_SUPPORTED_EXPLORATORY"
            elif row["reference_supported_component_frame_count"] == 1:
                component_state = "UNRESOLVED_SINGLE_REFERENCE_HIT"
            else:
                component_state = "UNRESOLVED_NO_REFERENCE_SUPPORT_IN_COMPONENT"
            row["component_grounding_state"] = component_state
            row["strict_identity_claimed"] = False
            component_rows.append(row)
    return pd.DataFrame(segment_rows).drop_duplicates(["segment_id", "track_id"]), pd.DataFrame(component_rows)


def select_cases(segments: pd.DataFrame, explanation_sets: pd.DataFrame, components: pd.DataFrame,
                 optical_events: pd.DataFrame, sar_events: pd.DataFrame, compatibility: pd.DataFrame,
                 segment_grounding: pd.DataFrame, component_grounding: pd.DataFrame,
                 counterexamples: pd.DataFrame) -> pd.DataFrame:
    slots: list[tuple[str, pd.DataFrame, list[str]]] = []
    event_join = optical_events.merge(segments, on=["segment_id", "run_id"], how="left")
    sar_join = sar_events.merge(segments, on=["segment_id", "run_id"], how="left")
    likely = component_grounding[component_grounding["component_grounding_state"].isin(["LIKELY_SUPPORTED_EXPLORATORY", "MULTIPLE_VALID_EXPLANATIONS"])]
    potential = explanation_sets[explanation_sets["potential_disambiguation_gt_blind"]]
    slots.extend([
        ("01_long_single_object_persistence", segments[(segments.track_count == 1)].sort_values("frame_count", ascending=False), ["segment_id"]),
        ("02_stable_two_object_order", event_join[event_join.event_type.eq("RELATIVE_ORDER_STABLE")].sort_values("frame_count", ascending=False), ["segment_id"]),
        ("03_optical_approach_tendency", event_join[event_join.event_type.eq("PAIR_GAP_APPROACH_TENDENCY_DESCRIPTOR")].sort_values("frame_count", ascending=False), ["segment_id"]),
        ("04_optical_separation_tendency", event_join[event_join.event_type.eq("PAIR_GAP_SEPARATION_TENDENCY_DESCRIPTOR")].sort_values("frame_count", ascending=False), ["segment_id"]),
        ("05_optical_order_change_candidate", event_join[event_join.event_type.eq("RELATIVE_ORDER_CHANGE_CANDIDATE")].sort_values("frame_count", ascending=False), ["segment_id"]),
        ("06_optical_overlap_uncertainty", event_join[event_join.event_type.eq("RELATIVE_ORDER_OVERLAP_UNCERTAINTY")].sort_values("frame_count", ascending=False), ["segment_id"]),
        ("07_sar_split_like", sar_join[sar_join.event_type.eq("SAR_SPLIT_LIKE_HYPOTHESIS")].sort_values("frame_count", ascending=False), ["segment_id", "explanation_component_id"]),
        ("08_sar_merge_like", sar_join[sar_join.event_type.eq("SAR_MERGE_LIKE_HYPOTHESIS")].sort_values("frame_count", ascending=False), ["segment_id", "explanation_component_id"]),
        ("09_complete_p0_continuity", compatibility[compatibility.p0_continuity_compatibility.eq("P0_CONTINUITY_COMPLETE")], ["segment_id", "explanation_component_id"]),
        ("10_partial_or_unavailable_p0_continuity", compatibility[~compatibility.p0_continuity_compatibility.eq("P0_CONTINUITY_COMPLETE")], ["segment_id", "explanation_component_id"]),
        ("11_likely_grounded_potential_disambiguation", likely.merge(potential, on=["segment_id", "run_id", "track_id"], how="inner"), ["segment_id", "explanation_component_id"]),
        ("12_multiple_valid_or_ambiguous_grounding", component_grounding[component_grounding.component_grounding_state.str.contains("MULTIPLE|AMBIGUOUS")], ["segment_id", "explanation_component_id"]),
        ("13_boundary_or_censoring", segments[segments.segment_kind.eq("SAR_BOUNDARY_CENSOR_CONTEXT")], ["segment_id"]),
        ("14_birth_death_event", sar_join[sar_join.event_type.str.contains("BIRTH|DEATH")].sort_values("frame_count", ascending=False), ["segment_id", "explanation_component_id"]),
        ("15_shared_response_grounding", component_grounding[component_grounding.shared_reference_frame_count.gt(0)], ["segment_id", "explanation_component_id"]),
        ("16_counterexample", counterexamples, ["segment_id"]),
    ])
    rows: list[dict[str, Any]] = []
    used: set[str] = set()
    for name, candidates, keys in slots:
        if candidates.empty:
            rows.append({"case_name": name, "status": "CATEGORY_NOT_OBSERVED", "segment_id": "", "explanation_component_id": "", "path": ""})
            continue
        selected = None
        for candidate in candidates.itertuples(index=False):
            sid = str(getattr(candidate, "segment_id"))
            identity = name + sid + str(getattr(candidate, "explanation_component_id", ""))
            if identity not in used:
                selected = candidate
                used.add(identity)
                break
        if selected is None:
            selected = next(candidates.itertuples(index=False))
        rows.append({
            "case_name": name, "status": "OBSERVED", "segment_id": str(getattr(selected, "segment_id")),
            "explanation_component_id": str(getattr(selected, "explanation_component_id", "")),
            "path": str((FIGURES / f"{name}.png").relative_to(WORKSPACE)),
        })
    return pd.DataFrame(rows)


def image_path_for_optical(observation: pd.Series) -> Path:
    path = Path(str(observation.optical_image_path))
    if path.exists():
        return path
    return WORKSPACE / "output" / "pseudocolor_labelstudio_prep_20260722" / "frames" / "optical" / str(observation.run_id) / f"frame_{int(observation.frame_index):06d}_t{int(observation.timestamp_ms):06d}ms.jpg"


def render_case(case: pd.Series, segments: pd.DataFrame, frame_state: pd.DataFrame, optical: pd.DataFrame,
                nodes: pd.DataFrame, edges: pd.DataFrame, components: pd.DataFrame, memberships: pd.DataFrame,
                reference: pd.DataFrame, cmr: Any) -> None:
    case_path = WORKSPACE / str(case.path)
    selected_component_id = str(case.explanation_component_id) if pd.notna(case.explanation_component_id) else ""
    if selected_component_id.lower() == "nan":
        selected_component_id = ""
    if case_path.exists() and case_path.stat().st_size > 100_000 and not selected_component_id:
        return
    segment = segments[segments["segment_id"] == case.segment_id].iloc[0]
    tracks = str(segment.track_ids).split(";")
    all_frames = list(range(int(segment.start_sar_frame), int(segment.end_sar_frame) + 1))
    sample_idx = np.linspace(0, len(all_frames) - 1, min(5, len(all_frames))).round().astype(int)
    sample_frames = [all_frames[i] for i in sorted(set(sample_idx))]
    fig = plt.figure(figsize=(22, 12), constrained_layout=True)
    grid = fig.add_gridspec(3, len(sample_frames), height_ratios=[1.0, 1.05, 1.25])
    fig.suptitle(
        f"{case.case_name} | {segment.run_id} F{segment.start_sar_frame}-{segment.end_sar_frame} | "
        f"{segment.segment_kind} | tracks={len(tracks)}\n"
        "Optical: runtime raw fragments/corridors only | SAR: q95 response regions and frozen P0 graph | magenta=offline reference-supported region",
        fontsize=13,
    )
    cmap = plt.get_cmap("tab10")
    track_colors = {track: cmap(i % 10) for i, track in enumerate(tracks)}
    selected_members = memberships[memberships["explanation_component_id"].astype(str) == selected_component_id] if selected_component_id else memberships.iloc[0:0]
    for col, frame in enumerate(sample_frames):
        ax = fig.add_subplot(grid[0, col])
        state = frame_state[(frame_state.run_id == segment.run_id) & (frame_state.frame_index == frame) & frame_state.track_id.isin(tracks)]
        timestamp = int(state.nominal_optical_timestamp_ms.iloc[0]) if len(state) else -1
        obs = optical[(optical.run_id == segment.run_id) & (optical.timestamp_ms == timestamp)]
        image = None
        if len(obs):
            image = cv2.imread(str(image_path_for_optical(obs.iloc[0])))
        if image is None:
            ax.text(0.5, 0.5, "optical missing", ha="center", va="center")
        else:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            ax.imshow(image)
            for row in obs[obs.raw_track_fragment_id.astype(str).isin(tracks)].itertuples(index=False):
                color = track_colors[str(row.raw_track_fragment_id)]
                rect = plt.Rectangle((row.bbox_x1, row.bbox_y1), row.bbox_x2-row.bbox_x1, row.bbox_y2-row.bbox_y1,
                                     fill=False, color=color, linewidth=2)
                ax.add_patch(rect)
                ax.text(row.bbox_x1, max(0, row.bbox_y1-4), str(row.raw_track_fragment_id).split("_")[-1], color=color, fontsize=7)
        ax.set_title(f"Optical nominal t={timestamp} ms\nSAR F{frame}", fontsize=8)
        ax.axis("off")

        ax2 = fig.add_subplot(grid[1, col])
        sar_path = cmr.sar_image_path(str(segment.run_id), int(frame))
        sar = cv2.imread(str(sar_path)) if sar_path.exists() else None
        if sar is None:
            ax2.text(0.5, 0.5, "SAR missing", ha="center", va="center")
        else:
            sar = cv2.cvtColor(sar, cv2.COLOR_BGR2RGB)
            ax2.imshow(sar)
            mask_path = REGION_MASKS / f"{segment.run_id}_SARF{frame:06d}.npz"
            labels = np.load(mask_path)["Q095"]
            frame_nodes = nodes[(nodes.run_id == segment.run_id) & (nodes.frame_index == frame) & nodes.track_id.astype(str).isin(tracks)]
            for row in frame_nodes.itertuples(index=False):
                contour_mask = (labels == int(str(row.region_id).rsplit("R", 1)[-1])).astype(np.uint8)
                contours, _ = cv2.findContours(contour_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    points = contour[:, 0, :]
                    ax2.plot(points[:, 0], points[:, 1], color=track_colors[str(row.track_id)], linewidth=0.8, alpha=0.65)
            selected_regions = selected_members[selected_members["frame_index"] == frame]["region_id"].astype(str)
            for region_id in selected_regions:
                label = int(str(region_id).rsplit("R", 1)[-1])
                contours, _ = cv2.findContours((labels == label).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    points = contour[:, 0, :]
                    ax2.plot(points[:, 0], points[:, 1], color="yellow", linewidth=2.0)
            ref = reference[(reference.run_id == segment.run_id) & (reference.frame_index == frame) & reference.nearest_region_id.notna()]
            for row in ref.itertuples(index=False):
                label = int(str(row.nearest_region_id).rsplit("R", 1)[-1])
                contours, _ = cv2.findContours((labels == label).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    points = contour[:, 0, :]
                    ax2.plot(points[:, 0], points[:, 1], color="magenta", linewidth=2.0)
        ax2.set_title(f"SAR q95 candidates F{frame}", fontsize=8)
        ax2.axis("off")

    graph_ax = fig.add_subplot(grid[2, :])
    seg_nodes = nodes[(nodes.run_id == segment.run_id) & nodes.frame_index.between(segment.start_sar_frame, segment.end_sar_frame) & nodes.track_id.astype(str).isin(tracks)]
    seg_edges = edges[(edges.run_id == segment.run_id) & edges.source_sar_frame.between(segment.start_sar_frame, segment.end_sar_frame-1) & edges.track_id.astype(str).isin(tracks) & edges.p0_supported_continuation]
    if len(seg_edges) > 4000:
        seg_edges = seg_edges.sort_values("graph_edge_id").iloc[np.linspace(0, len(seg_edges)-1, 4000).round().astype(int)]
    membership = memberships[memberships.segment_id == segment.segment_id]
    component_map = membership.set_index("track_node_id")["explanation_component_id"].to_dict() if len(membership) else {}
    component_ids = sorted(set(component_map.values()))
    component_colors = {component: cmap(i % 10) for i, component in enumerate(component_ids)}
    region_node = {(str(r.track_id), int(r.frame_index), str(r.region_id)): str(r.track_node_id) for r in seg_nodes.itertuples(index=False)}
    for row in seg_edges.itertuples(index=False):
        source_id = region_node.get((str(row.track_id), int(row.source_sar_frame), str(row.source_region_id)))
        destination_id = region_node.get((str(row.track_id), int(row.destination_sar_frame), str(row.destination_region_id)))
        if source_id and destination_id:
            source = seg_nodes[seg_nodes.track_node_id == source_id].iloc[0]
            destination = seg_nodes[seg_nodes.track_node_id == destination_id].iloc[0]
            selected_edge = bool(selected_component_id and component_map.get(source_id) == selected_component_id and component_map.get(destination_id) == selected_component_id)
            graph_ax.plot(
                [source.frame_index, destination.frame_index], [source.theta_mid_deg, destination.theta_mid_deg],
                color="red" if selected_edge else "0.75", linewidth=1.5 if selected_edge else 0.45,
                alpha=0.95 if selected_edge else 0.5, zorder=4 if selected_edge else 1,
            )
    for row in seg_nodes.itertuples(index=False):
        component = component_map.get(str(row.track_node_id), "")
        selected_node = bool(selected_component_id and component == selected_component_id)
        graph_ax.scatter(
            row.frame_index, row.theta_mid_deg, s=28 if selected_node else 8,
            color="red" if selected_node else component_colors.get(component, "0.5"),
            alpha=0.95 if selected_node else 0.75, zorder=5 if selected_node else 2,
        )
    for track in tracks:
        corridor = frame_state[(frame_state.run_id == segment.run_id) & (frame_state.track_id.astype(str) == track) & frame_state.frame_index.between(segment.start_sar_frame, segment.end_sar_frame)]
        graph_ax.fill_between(corridor.frame_index, corridor.raw_theta_low_deg, corridor.raw_theta_high_deg, color=track_colors[track], alpha=0.10)
        graph_ax.plot(corridor.frame_index, corridor.raw_theta_mid_deg, color=track_colors[track], linewidth=1.2, label=f"optical corridor {track.split('_')[-1]}")
    graph_ax.set_xlabel("SAR frame (nominal timing, uncalibrated)")
    graph_ax.set_ylabel("azimuth theta (deg)")
    graph_ax.set_title("Set-valued SAR temporal response graph inside optical corridors; red/yellow highlights selected component; lines are not tracker paths")
    graph_ax.legend(fontsize=7, ncol=max(1, len(tracks)), loc="upper right")
    case_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(case_path, dpi=120)
    plt.close(fig)


def make_contact_sheet(registry: pd.DataFrame) -> None:
    images: list[tuple[str, Image.Image]] = []
    for row in registry[registry.status == "OBSERVED"].itertuples(index=False):
        path = WORKSPACE / str(row.path)
        if path.exists():
            image = Image.open(path).convert("RGB")
            image.thumbnail((900, 490))
            images.append((row.case_name, image.copy()))
    width = 1840
    rows = max(1, math.ceil(len(images) / 2))
    canvas = Image.new("RGB", (width, rows * 540), "white")
    draw = ImageDraw.Draw(canvas)
    for i, (name, image) in enumerate(images):
        x = (i % 2) * 920
        y = (i // 2) * 540
        draw.text((x + 10, y + 5), name, fill="black")
        canvas.paste(image, (x + 10, y + 35))
    canvas.save(POST / "TERG_D0_TEMPORAL_REVIEW_CONTACT_SHEET.jpg", quality=92)


def ground() -> None:
    manifest = verify_pre_reference()
    POST.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    segments = load_pre_table("temporal_segment_atlas_pre_reference")
    frame_state = load_pre_table("optical_temporal_frame_state_pre_reference")
    optical_events = load_pre_table("optical_event_hypotheses_pre_reference")
    nodes = pd.read_parquet(PRE / "sar_response_graph_nodes_pre_reference.parquet")
    edges = pd.read_parquet(PRE / "sar_response_graph_edges_pre_reference.parquet")
    components = load_pre_table("terg_explanation_components_pre_reference")
    memberships = load_pre_table("terg_component_node_membership_pre_reference")
    explanation_sets = load_pre_table("terg_explanation_sets_pre_reference")
    sar_events = load_pre_table("sar_event_hypotheses_pre_reference")
    compatibility = load_pre_table("cross_modal_compatibility_profiles_pre_reference")
    counterexamples = load_pre_table("counterexample_ledger_pre_reference")

    segment_grounding, component_grounding = build_grounding(segments, explanation_sets, components, memberships)
    segment_grounding.to_csv(POST / "temporal_segment_evaluation_grounding.csv", index=False, encoding="utf-8-sig")
    component_grounding.to_csv(POST / "explanation_component_grounding.csv", index=False, encoding="utf-8-sig")
    segment_grounding.to_parquet(POST / "temporal_segment_evaluation_grounding.parquet", index=False, compression="zstd")
    component_grounding.to_parquet(POST / "explanation_component_grounding.parquet", index=False, compression="zstd")

    registry = select_cases(segments, explanation_sets, components, optical_events, sar_events, compatibility,
                            segment_grounding, component_grounding, counterexamples)
    data = load_pre_reference_authorities()
    reference = pd.read_csv(OFFLINE_REFERENCE)
    reference = reference[reference.run_id.isin(DEVELOPMENT_RUNS) & reference.percentile_tag.eq("Q095")].copy()
    for row in registry[registry.status == "OBSERVED"].itertuples(index=False):
        render_case(pd.Series(row._asdict()), segments, frame_state, data["optical"], nodes, edges, components,
                    memberships, reference, data["cmr"])
    registry.to_csv(POST / "temporal_review_case_registry.csv", index=False, encoding="utf-8-sig")
    make_contact_sheet(registry)

    grounded = component_grounding[component_grounding.component_grounding_state.isin(["LIKELY_SUPPORTED_EXPLORATORY", "MULTIPLE_VALID_EXPLANATIONS"])]
    summary = {
        "schema": "PERSON_TERG_D0_DEVELOPMENT_SUMMARY_V1", "created_at": now_iso(),
        "stage": "TERG_D0_TEMPORAL_EVENT_RESPONSE_GRAPH_MECHANISM_EXPLORATION",
        "development_runs": list(DEVELOPMENT_RUNS), "r04_or_new_confirmation_accessed": False,
        "temporal_segments": len(segments), "segment_kind_counts": segments.segment_kind.value_counts().to_dict(),
        "optical_event_counts": optical_events.event_type.value_counts().to_dict(),
        "sar_event_counts": sar_events.event_type.value_counts().to_dict(),
        "graph_nodes": len(nodes), "graph_edge_hypotheses": len(edges),
        "p0_supported_edges": int(edges.p0_supported_continuation.sum()),
        "explanation_sets": len(explanation_sets), "explanation_components": len(components),
        "potential_disambiguation_sets_gt_blind": int(explanation_sets.potential_disambiguation_gt_blind.sum()),
        "segment_grounding_counts": segment_grounding.grounding_state.value_counts().to_dict(),
        "component_grounding_counts": component_grounding.component_grounding_state.value_counts().to_dict(),
        "grounded_component_count": len(grounded),
        "review_cases_observed": int((registry.status == "OBSERVED").sum()),
        "review_cases_not_observed": int((registry.status == "CATEGORY_NOT_OBSERVED").sum()),
        "direct_visual_review_status": "PENDING_DIRECT_MULTIMODAL_REVIEW_LEDGER",
        "terg_v0_freeze_status": "PENDING_DIRECT_VISUAL_REVIEW_AND_MECHANISM_DECISION",
        "prohibited_outputs": {
            "weighted_score": False, "tracker": False, "hungarian": False, "identity_assignment": False,
            "unique_path": False, "factor_graph": False, "p2": False, "final_sar_center": False, "final_sar_box": False,
        },
        "pre_reference_manifest_sha256": sha256_file(PRE / "pre_reference_manifest.json"),
    }
    write_json(POST / "terg_d0_development_summary.json", summary)
    write_json(POST / "REFERENCE_GROUNDING_REVEAL_MARKER.json", {
        "schema": "PERSON_TERG_D0_REFERENCE_GROUNDING_REVEAL_V1", "created_at": now_iso(),
        "status": "OFFLINE_GROUNDING_LOADED_AFTER_PRE_REFERENCE_GRAPH_HASH_FREEZE",
        "pre_reference_manifest_sha256": sha256_file(PRE / "pre_reference_manifest.json"),
        "offline_assignment_sha256": sha256_file(OFFLINE_ASSIGNMENT),
        "offline_reference_sha256": sha256_file(OFFLINE_REFERENCE),
        "runtime_identity_claimed": False,
    })
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def freeze_final() -> None:
    required = [
        POST / "TERG_D0_MULTIMODAL_VISUAL_REVIEW_LEDGER.md",
        POST / "TERG_D0_DEVELOPMENT_REPORT.md",
        POST / "TERG_V0_MECHANISM_SPECIFICATION_FROZEN.md",
        POST / "TERG_V0_FUTURE_CONFIRMATION_PROTOCOL_DRAFT.md",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(f"manual closeout files missing: {missing}")
    files = sorted(p for p in OUTPUT.rglob("*") if p.is_file() and p.name not in {"terg_d0_final_manifest.json", "terg_d0_independent_validation.json"})
    write_json(OUTPUT / "terg_d0_final_manifest.json", {
        "schema": "PERSON_TERG_D0_FINAL_MANIFEST_V1", "created_at": now_iso(), "git_head_before_commit": git_head(),
        "files": [{"path": str(p.relative_to(WORKSPACE)), "bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in files],
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["discover", "ground", "freeze-final"])
    args = parser.parse_args()
    {"discover": discover, "ground": ground, "freeze-final": freeze_final}[args.phase]()


if __name__ == "__main__":
    main()
