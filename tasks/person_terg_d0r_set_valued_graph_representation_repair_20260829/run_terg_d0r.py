from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
D0_ROOT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "terg_d0_temporal_event_response_graph_mechanism_exploration"
)
D0_PRE = D0_ROOT / "pre_reference"
D0_POST = D0_ROOT / "post_reference"
P1E_ROOT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "p1e_sar_only_response_interface"
    / "runtime_track_response_region_minimal_v1"
)
PHASE_A_ROOT = WORKSPACE / "output" / "person_terg_v0_visual_semantic_reality_check_20260829"
PHASE_A_SCRIPT = (
    WORKSPACE
    / "tasks"
    / "person_terg_v0_visual_semantic_reality_check_20260829"
    / "run_visual_semantic_audit.py"
)
OUTPUT = WORKSPACE / "output" / "person_terg_d0r_set_valued_graph_representation_repair_20260829"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference"
FIGURES = OUTPUT / "figures"
BEFORE_AFTER = FIGURES / "before_after"

PHYSICAL_NODE_KEY = ["run_id", "frame_index", "region_id"]
PHYSICAL_EDGE_KEY = [
    "run_id",
    "source_sar_frame",
    "destination_sar_frame",
    "source_region_id",
    "destination_region_id",
]
def stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha1(payload.encode('utf-8')).hexdigest()[:20].upper()}"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_table(frame: pd.DataFrame, path: Path, csv: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path.with_suffix(".parquet"), index=False, compression="zstd")
    if csv:
        frame.to_csv(path.with_suffix(".csv"), index=False, encoding="utf-8-sig")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_pre_reference_inputs() -> dict[str, pd.DataFrame]:
    pre_names = {
        "nodes": "sar_response_graph_nodes_pre_reference.parquet",
        "edges": "sar_response_graph_edges_pre_reference.parquet",
        "segments": "temporal_segment_atlas_pre_reference.parquet",
        "sets": "terg_explanation_sets_pre_reference.parquet",
        "d0_components": "terg_explanation_components_pre_reference.parquet",
        "d0_memberships": "terg_component_node_membership_pre_reference.parquet",
        "order": "relative_order_compatibility_pre_reference.parquet",
        "frame_state": "optical_temporal_frame_state_pre_reference.parquet",
        "event_relations": "cross_modal_event_relations_pre_reference.parquet",
    }
    return {name: pd.read_parquet(D0_PRE / file_name) for name, file_name in pre_names.items()}


def load_post_reference_inputs() -> dict[str, pd.DataFrame]:
    return {
        "component_grounding": pd.read_parquet(D0_POST / "explanation_component_grounding.parquet"),
        "segment_grounding": pd.read_parquet(D0_POST / "temporal_segment_evaluation_grounding.parquet"),
        "reference": pd.read_csv(P1E_ROOT / "offline_reference_response_region_evaluation.csv"),
    }


def build_physical_layers(data: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    nodes = data["nodes"].copy()
    physical_columns = [
        "run_id",
        "frame_uid",
        "frame_index",
        "percentile_tag",
        "region_id",
        "region_label",
        "percentile_level",
        "numeric_score_threshold",
        "pixel_count",
        "area_m2",
        "score_max",
        "score_mean",
        "score_median",
        "centroid_x_px_shape_descriptor",
        "centroid_y_px_shape_descriptor",
        "major_extent_m",
        "minor_extent_m",
        "elongation",
        "structure_state",
        "range_min_m",
        "range_max_m",
        "theta_min_deg",
        "theta_max_deg",
        "theta_mid_deg",
        "support_fraction_min",
        "support_fraction_median",
        "touches_observable_boundary",
        "has_truncated_support",
        "reference_used_for_region_generation",
        "region_is_final_person_box",
    ]
    for column in physical_columns:
        counts = nodes.groupby(PHYSICAL_NODE_KEY)[column].nunique(dropna=False)
        if int(counts.max()) != 1:
            raise AssertionError(f"physical property differs across conditioned copies: {column}")
    physical = nodes[physical_columns].drop_duplicates(PHYSICAL_NODE_KEY).copy()
    physical["physical_region_id"] = [
        stable_id("TERGV1PR", run, frame, region)
        for run, frame, region in physical[PHYSICAL_NODE_KEY].itertuples(index=False, name=None)
    ]
    physical["physical_response_semantics"] = "SAR_Q95_IMAGE_DOMAIN_REGION_NOT_PERSON_BOX_OR_IDENTITY"
    physical["optical_conditioning_embedded"] = False

    key_to_id = physical.set_index(PHYSICAL_NODE_KEY)["physical_region_id"]
    incidence_columns = [
        "run_id",
        "frame_uid",
        "frame_index",
        "track_id",
        "shell_id",
        "region_id",
        "intersection_pixel_count",
        "intersection_area_m2",
        "region_coverage_fraction",
        "shell_effective_area_px",
        "shell_coverage_fraction",
        "intersection_theta_min_deg",
        "intersection_theta_max_deg",
        "intersection_range_min_m",
        "intersection_range_max_m",
        "temporal_policy",
        "guard_variant",
        "track_node_id",
    ]
    incidence = nodes[incidence_columns].copy()
    incidence["physical_region_id"] = [
        key_to_id.loc[(run, frame, region)]
        for run, frame, region in incidence[["run_id", "frame_index", "region_id"]].itertuples(
            index=False, name=None
        )
    ]
    incidence["incidence_id"] = [
        stable_id("TERGV1I", run, track, frame, region)
        for run, track, frame, region in incidence[
            ["run_id", "track_id", "frame_index", "region_id"]
        ].itertuples(index=False, name=None)
    ]
    incidence["incidence_semantics"] = "OPTICAL_CORRIDOR_ADMITS_PHYSICAL_SAR_REGION_NOT_IDENTITY"
    incidence["physical_region_duplicated"] = False

    segments = data["segments"].set_index("segment_id")
    set_rows: list[pd.DataFrame] = []
    for item in data["sets"].itertuples(index=False):
        segment = segments.loc[item.segment_id]
        part = incidence[
            incidence["run_id"].eq(item.run_id)
            & incidence["track_id"].astype(str).eq(str(item.track_id))
            & incidence["frame_index"].between(segment.start_sar_frame, segment.end_sar_frame)
        ].copy()
        part.insert(0, "segment_id", item.segment_id)
        part["explanation_set_incidence_id"] = [
            stable_id("TERGV1SI", item.segment_id, item.track_id, physical_id)
            for physical_id in part["physical_region_id"]
        ]
        set_rows.append(part)
    set_incidence = pd.concat(set_rows, ignore_index=True)

    shared = (
        set_incidence.groupby(["segment_id", "run_id", "frame_index", "physical_region_id", "region_id"], as_index=False)
        .agg(
            conditioned_track_count=("track_id", "nunique"),
            conditioned_track_ids=("track_id", lambda values: ";".join(sorted(set(map(str, values))))),
        )
    )
    shared = shared[shared["conditioned_track_count"].gt(1)].copy()
    shared["shared_response_semantics"] = "ONE_PHYSICAL_SAR_REGION_REFERENCED_BY_MULTIPLE_OPTICAL_INCIDENCES"
    return physical, incidence, set_incidence, shared


def build_physical_edges(
    data: dict[str, pd.DataFrame], physical: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, str]]:
    conditioned = data["edges"].copy()
    evidence_columns = [
        "p0_model",
        "p0_holdout_residual_p90_px",
        "p0_angular_uncertainty_deg",
        "predicted_theta_low_deg",
        "predicted_theta_high_deg",
        "observed_theta_low_deg",
        "observed_theta_high_deg",
        "sar_residual_left_low_deg",
        "sar_residual_left_high_deg",
        "sar_residual_right_low_deg",
        "sar_residual_right_high_deg",
        "sar_residual_mid_descriptor_deg",
        "sar_width_change_deg",
        "sar_p0_residual_state_core",
        "sar_observability_state",
        "sar_p0_residual_state",
        "soft_intersection_px",
        "source_total_retention",
        "destination_explained_fraction",
        "soft_iou",
        "source_touches_boundary",
        "destination_touches_boundary",
        "source_truncated",
        "destination_truncated",
        "p0_supported_destination_count",
        "p0_supported_source_count",
        "sar_topology_state",
        "p0_supported_continuation",
    ]
    for column in evidence_columns:
        counts = conditioned.groupby(PHYSICAL_EDGE_KEY)[column].nunique(dropna=False)
        if int(counts.max()) != 1:
            raise AssertionError(f"edge evidence differs across conditioned copies: {column}")
    copy_counts = conditioned.groupby(PHYSICAL_EDGE_KEY).size().rename("conditioned_edge_copy_count")
    edges = conditioned[PHYSICAL_EDGE_KEY + evidence_columns].drop_duplicates(PHYSICAL_EDGE_KEY).copy()
    edges = edges.join(copy_counts, on=PHYSICAL_EDGE_KEY)
    region_lookup = physical.set_index(PHYSICAL_NODE_KEY)["physical_region_id"]
    edges["source_physical_region_id"] = [
        region_lookup.loc[(run, frame, region)]
        for run, frame, region in edges[["run_id", "source_sar_frame", "source_region_id"]].itertuples(
            index=False, name=None
        )
    ]
    edges["destination_physical_region_id"] = [
        region_lookup.loc[(run, frame, region)]
        for run, frame, region in edges[
            ["run_id", "destination_sar_frame", "destination_region_id"]
        ].itertuples(index=False, name=None)
    ]
    edges["physical_edge_id"] = [
        stable_id("TERGV1PE", *values)
        for values in edges[PHYSICAL_EDGE_KEY].itertuples(index=False, name=None)
    ]

    supported = edges["p0_supported_continuation"].astype(bool)
    out_key = ["run_id", "source_sar_frame", "source_region_id"]
    in_key = ["run_id", "destination_sar_frame", "destination_region_id"]
    subset = edges[supported].copy()
    subset["upper_out_degree"] = subset.groupby(out_key)["destination_region_id"].transform("nunique")
    subset["upper_in_degree"] = subset.groupby(in_key)["source_region_id"].transform("nunique")
    subset["outgoing_max_soft_intersection_px"] = subset.groupby(out_key)["soft_intersection_px"].transform("max")
    subset["incoming_max_soft_intersection_px"] = subset.groupby(in_key)["soft_intersection_px"].transform("max")
    subset["source_local_dominant"] = np.isclose(
        subset["soft_intersection_px"], subset["outgoing_max_soft_intersection_px"]
    )
    subset["destination_local_dominant"] = np.isclose(
        subset["soft_intersection_px"], subset["incoming_max_soft_intersection_px"]
    )
    subset["mutual_local_dominant"] = subset["source_local_dominant"] & subset["destination_local_dominant"]
    subset["exclusive_one_to_one_topology"] = subset["p0_supported_destination_count"].eq(1) & subset[
        "p0_supported_source_count"
    ].eq(1)
    subset["p0_common_compatible"] = subset["sar_p0_residual_state_core"].eq(
        "SAR_P0_RESIDUAL_COMMON_COMPATIBLE"
    )
    subset["deformation_evidence"] = subset["sar_p0_residual_state"].astype(str).str.contains("DEFORMATION")
    subset["boundary_censoring_evidence"] = subset[
        ["source_touches_boundary", "destination_touches_boundary", "source_truncated", "destination_truncated"]
    ].astype(bool).any(axis=1)
    subset["lower_core_eligible"] = (
        subset["mutual_local_dominant"]
        & subset["exclusive_one_to_one_topology"]
        & subset["p0_common_compatible"]
        & ~subset["deformation_evidence"]
        & ~subset["boundary_censoring_evidence"]
    )
    derived = subset[
        [
            "physical_edge_id",
            "upper_out_degree",
            "upper_in_degree",
            "outgoing_max_soft_intersection_px",
            "incoming_max_soft_intersection_px",
            "source_local_dominant",
            "destination_local_dominant",
            "mutual_local_dominant",
            "exclusive_one_to_one_topology",
            "p0_common_compatible",
            "deformation_evidence",
            "boundary_censoring_evidence",
            "lower_core_eligible",
        ]
    ]
    edges = edges.merge(derived, on="physical_edge_id", how="left", validate="one_to_one")
    bool_columns = [
        "source_local_dominant",
        "destination_local_dominant",
        "mutual_local_dominant",
        "exclusive_one_to_one_topology",
        "p0_common_compatible",
        "deformation_evidence",
        "boundary_censoring_evidence",
        "lower_core_eligible",
    ]
    edges[bool_columns] = edges[bool_columns].astype("boolean").fillna(False).astype(bool)
    edges["connectivity_authority"] = np.select(
        [~supported, edges["lower_core_eligible"]],
        ["UNSUPPORTED", "LOWER_CORE"],
        default="UPPER_OPTIONAL",
    )
    edges["absolute_overlap_threshold_fitted"] = False
    edges["new_numeric_threshold_used_for_repair"] = False
    edges["weighted_scalar_score_used"] = False

    def relation_set(row: pd.Series) -> str:
        if not bool(row.p0_supported_continuation):
            return "{UNSUPPORTED}"
        states = {"CONTINUATION_COMPATIBLE"}
        if not bool(row.lower_core_eligible):
            states.add("UNCERTAIN_OR_WEAK_CONTACT_COMPATIBLE")
        if bool(row.deformation_evidence):
            states.add("DEFORMATION_COMPATIBLE")
        if bool(row.boundary_censoring_evidence):
            states.add("BOUNDARY_CENSORED")
        return "{" + ",".join(sorted(states)) + "}"

    def topology_set(row: pd.Series) -> str:
        if not bool(row.p0_supported_continuation):
            return "{UNSUPPORTED}"
        states = {"CONTINUATION_HYPOTHESIS"}
        if int(row.upper_out_degree) > 1:
            states.add("ONE_TO_MANY_POSSIBLE")
        if int(row.upper_in_degree) > 1:
            states.add("MANY_TO_ONE_POSSIBLE")
        if bool(row.deformation_evidence):
            states.add("DEFORMATION_POSSIBLE")
        if bool(row.boundary_censoring_evidence):
            states.add("BOUNDARY_CENSORING_POSSIBLE")
        if row.connectivity_authority == "UPPER_OPTIONAL" and (
            int(row.upper_out_degree) > 1 or int(row.upper_in_degree) > 1
        ):
            states.add("FRAGMENTATION_OR_WEAK_TOPOLOGY_UNRESOLVED")
        return "{" + ",".join(sorted(states)) + "}"

    edges["edge_relation_set"] = edges.apply(relation_set, axis=1)
    edges["topology_hypothesis_set"] = edges.apply(topology_set, axis=1)
    edges["split_merge_hard_event_claimed"] = False

    old_edge_to_physical = conditioned.merge(
        edges[PHYSICAL_EDGE_KEY + ["physical_edge_id"]], on=PHYSICAL_EDGE_KEY, how="left", validate="many_to_one"
    ).set_index("graph_edge_id")["physical_edge_id"].to_dict()
    return edges, old_edge_to_physical


def component_signature(frame: pd.DataFrame) -> tuple[tuple[int, str], ...]:
    return tuple(sorted((int(row.frame_index), str(row.region_id)) for row in frame.itertuples(index=False)))


def build_component_families(
    data: dict[str, pd.DataFrame],
    physical: pd.DataFrame,
    set_incidence: pd.DataFrame,
    edges: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d0_signatures: dict[tuple[str, str, tuple[tuple[int, str], ...]], str] = {}
    for component_id, group in data["d0_memberships"].groupby("explanation_component_id"):
        first = group.iloc[0]
        d0_signatures[(str(first.segment_id), str(first.track_id), component_signature(group))] = str(component_id)

    physical_meta = physical.set_index("physical_region_id")[["frame_index", "region_id", "theta_mid_deg"]]
    edge_lookup = edges.set_index("physical_edge_id", drop=False)
    segments = data["segments"].set_index("segment_id")
    family_rows: list[dict[str, Any]] = []
    core_rows: list[dict[str, Any]] = []
    membership_rows: list[dict[str, Any]] = []
    bridge_rows: list[dict[str, Any]] = []

    for item in data["sets"].itertuples(index=False):
        segment = segments.loc[item.segment_id]
        incidence = set_incidence[
            set_incidence["segment_id"].eq(item.segment_id)
            & set_incidence["track_id"].astype(str).eq(str(item.track_id))
        ]
        node_ids = set(incidence["physical_region_id"].astype(str))
        candidates = edges[
            edges["run_id"].eq(item.run_id)
            & edges["p0_supported_continuation"].astype(bool)
            & edges["source_sar_frame"].between(segment.start_sar_frame, segment.end_sar_frame - 1)
            & edges["source_physical_region_id"].isin(node_ids)
            & edges["destination_physical_region_id"].isin(node_ids)
        ]
        upper = nx.Graph()
        lower = nx.Graph()
        upper.add_nodes_from(node_ids)
        lower.add_nodes_from(node_ids)
        for edge in candidates.itertuples(index=False):
            upper.add_edge(
                str(edge.source_physical_region_id),
                str(edge.destination_physical_region_id),
                physical_edge_id=str(edge.physical_edge_id),
            )
            if bool(edge.lower_core_eligible):
                lower.add_edge(
                    str(edge.source_physical_region_id),
                    str(edge.destination_physical_region_id),
                    physical_edge_id=str(edge.physical_edge_id),
                )

        lower_parts = list(nx.connected_components(lower))
        lower_by_node: dict[str, str] = {}
        lower_metadata: dict[str, dict[str, Any]] = {}
        for part in lower_parts:
            core_id = stable_id("TERGV1C", item.segment_id, item.track_id, *sorted(part))
            frames = {int(physical_meta.loc[node_id, "frame_index"]) for node_id in part}
            lower_metadata[core_id] = {
                "core_component_id": core_id,
                "segment_id": item.segment_id,
                "run_id": item.run_id,
                "track_id": item.track_id,
                "core_node_count": len(part),
                "core_frame_count": len(frames),
                "core_start_sar_frame": min(frames),
                "core_end_sar_frame": max(frames),
                "core_is_multiframe": len(frames) >= 2,
                "identity_claimed": False,
                "actual_pruning_performed": False,
            }
            for node_id in part:
                lower_by_node[str(node_id)] = core_id

        for upper_part in nx.connected_components(upper):
            upper_part = set(map(str, upper_part))
            signature_frame = physical_meta.loc[sorted(upper_part)].reset_index()
            signature = tuple(
                sorted(
                    (int(row.frame_index), str(row.region_id))
                    for row in signature_frame.itertuples(index=False)
                )
            )
            d0_component_id = d0_signatures.get((str(item.segment_id), str(item.track_id), signature))
            if d0_component_id is None:
                raise AssertionError("upper component does not match frozen D0 component")
            family_id = stable_id("TERGV1F", item.segment_id, item.track_id, d0_component_id)
            family_graph = upper.subgraph(upper_part).copy()
            family_edge_ids = {
                str(payload["physical_edge_id"]) for _, _, payload in family_graph.edges(data=True)
            }
            core_edge_ids = {
                edge_id for edge_id in family_edge_ids if bool(edge_lookup.loc[edge_id, "lower_core_eligible"])
            }
            optional_edge_ids = family_edge_ids - core_edge_ids
            core_ids = sorted({lower_by_node[node_id] for node_id in upper_part})
            frames = {int(physical_meta.loc[node_id, "frame_index"]) for node_id in upper_part}
            optional_bridge_count = 0
            for source, destination in nx.bridges(family_graph):
                edge_id = str(family_graph.edges[source, destination]["physical_edge_id"])
                if edge_id not in optional_edge_ids:
                    continue
                cut = family_graph.copy()
                cut.remove_edge(source, destination)
                parts = list(nx.connected_components(cut))
                if len(parts) != 2:
                    continue
                parts = sorted(parts, key=len)
                small_frames = {int(physical_meta.loc[node_id, "frame_index"]) for node_id in parts[0]}
                large_frames = {int(physical_meta.loc[node_id, "frame_index"]) for node_id in parts[1]}
                optional_bridge_count += 1
                bridge_rows.append(
                    {
                        "family_id": family_id,
                        "segment_id": item.segment_id,
                        "run_id": item.run_id,
                        "track_id": item.track_id,
                        "physical_edge_id": edge_id,
                        "small_side_node_count": len(parts[0]),
                        "large_side_node_count": len(parts[1]),
                        "small_side_frame_count": len(small_frames),
                        "large_side_frame_count": len(large_frames),
                        "bridge_semantics": "OPTIONAL_BRIDGE_DOES_NOT_FORCE_LOWER_CORE_MERGE",
                    }
                )
            family_rows.append(
                {
                    "family_id": family_id,
                    "d0_component_id": d0_component_id,
                    "segment_id": item.segment_id,
                    "run_id": item.run_id,
                    "track_id": item.track_id,
                    "segment_frame_count": int(segment.frame_count),
                    "upper_node_count": len(upper_part),
                    "upper_frame_count": len(frames),
                    "upper_start_sar_frame": min(frames),
                    "upper_end_sar_frame": max(frames),
                    "lower_core_component_count": len(core_ids),
                    "lower_core_multiframe_component_count": sum(
                        bool(lower_metadata[core_id]["core_is_multiframe"]) for core_id in core_ids
                    ),
                    "core_edge_count": len(core_edge_ids),
                    "optional_edge_count": len(optional_edge_ids),
                    "optional_bridge_dependency_count": optional_bridge_count,
                    "connectivity_interpretation_set": (
                        "{LOWER_CORE_PARTITION,UPPER_POSSIBLE_CONNECTED_ENVELOPE}"
                        if optional_edge_ids
                        else "{LOWER_CORE_CONNECTED}"
                    ),
                    "complete_lifecycle_possible": len(frames) == int(segment.frame_count),
                    "unique_path_claimed": False,
                    "identity_claimed": False,
                    "actual_pruning_performed": False,
                }
            )
            for core_id in core_ids:
                row = dict(lower_metadata[core_id])
                row["family_id"] = family_id
                core_rows.append(row)
            for node_id in sorted(upper_part):
                meta = physical_meta.loc[node_id]
                membership_rows.append(
                    {
                        "family_id": family_id,
                        "core_component_id": lower_by_node[node_id],
                        "segment_id": item.segment_id,
                        "run_id": item.run_id,
                        "track_id": item.track_id,
                        "physical_region_id": node_id,
                        "frame_index": int(meta.frame_index),
                        "region_id": str(meta.region_id),
                        "theta_mid_deg": float(meta.theta_mid_deg),
                    }
                )

    families = pd.DataFrame(family_rows)
    cores = pd.DataFrame(core_rows).drop_duplicates("core_component_id")
    memberships = pd.DataFrame(membership_rows)
    bridges = pd.DataFrame(bridge_rows)
    if len(families) != len(data["d0_components"]) or len(memberships) != len(data["d0_memberships"]):
        raise AssertionError("upper family does not preserve frozen D0 upper envelope")
    return families, cores, memberships, bridges


def add_bridge_authority(edges: pd.DataFrame, bridges: pd.DataFrame) -> pd.DataFrame:
    if bridges.empty:
        edges["optional_bridge_family_count"] = 0
        edges["maximum_bridge_small_side_frame_count"] = 0
        edges["maximum_bridge_large_side_frame_count"] = 0
    else:
        summary = (
            bridges.groupby("physical_edge_id", as_index=False)
            .agg(
                optional_bridge_family_count=("family_id", "nunique"),
                maximum_bridge_small_side_frame_count=("small_side_frame_count", "max"),
                maximum_bridge_large_side_frame_count=("large_side_frame_count", "max"),
            )
        )
        edges = edges.merge(summary, on="physical_edge_id", how="left", validate="one_to_one")
        for column in [
            "optional_bridge_family_count",
            "maximum_bridge_small_side_frame_count",
            "maximum_bridge_large_side_frame_count",
        ]:
            edges[column] = edges[column].fillna(0).astype(int)
    edges["topology_authority"] = np.where(
        edges["optional_bridge_family_count"].gt(0),
        "OPTIONAL_BRIDGE_PRESERVED_WITHOUT_FORCED_CORE_MERGE",
        np.where(
            edges["connectivity_authority"].eq("LOWER_CORE"),
            "LOWER_CORE_CONNECTIVITY",
            edges["connectivity_authority"],
        ),
    )
    return edges


def build_relation_sets(
    data: dict[str, pd.DataFrame],
    physical: pd.DataFrame,
    families: pd.DataFrame,
    memberships: pd.DataFrame,
    set_incidence: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    bounds = physical.set_index("physical_region_id")[["theta_min_deg", "theta_max_deg"]]
    member = memberships.merge(bounds, left_on="physical_region_id", right_index=True, how="left", validate="many_to_one")
    family_frames: dict[str, dict[int, tuple[set[str], float, float]]] = {}
    for family_id, group in member.groupby("family_id"):
        payload: dict[int, tuple[set[str], float, float]] = {}
        for frame, rows in group.groupby("frame_index"):
            payload[int(frame)] = (
                set(rows["physical_region_id"].astype(str)),
                float(rows["theta_min_deg"].min()),
                float(rows["theta_max_deg"].max()),
            )
        family_frames[str(family_id)] = payload
    family_ids = families.groupby(["segment_id", "track_id"])["family_id"].agg(list).to_dict()

    profile_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    for profile in data["order"].itertuples(index=False):
        ids_a = family_ids.get((profile.segment_id, profile.track_a), [])
        ids_b = family_ids.get((profile.segment_id, profile.track_b), [])
        frame_counts: dict[int, Counter[str]] = defaultdict(Counter)
        pair_support: Counter[str] = Counter()
        family_pairs_with_common = 0
        for family_a in ids_a:
            fa = family_frames[str(family_a)]
            for family_b in ids_b:
                fb = family_frames[str(family_b)]
                common = sorted(set(fa) & set(fb))
                if not common:
                    continue
                family_pairs_with_common += 1
                relations_for_pair: set[str] = set()
                for frame in common:
                    regions_a, a_low, a_high = fa[frame]
                    regions_b, b_low, b_high = fb[frame]
                    if regions_a & regions_b:
                        relation = "SHARED"
                    elif a_high < b_low:
                        relation = "LEFT"
                    elif b_high < a_low:
                        relation = "RIGHT"
                    else:
                        relation = "OVERLAP"
                    frame_counts[int(frame)][relation] += 1
                    relations_for_pair.add(relation)
                for relation in relations_for_pair:
                    pair_support[relation] += 1

        possible = {relation for counts in frame_counts.values() for relation, count in counts.items() if count > 0}
        if "SHARED" in possible and {"LEFT", "RIGHT"}.issubset(possible):
            classification = "SHARED_PLUS_COMPETING_DIRECTIONS"
        elif "SHARED" in possible and ({"LEFT", "RIGHT"} & possible):
            classification = "SHARED_PLUS_PARTIAL_DIRECTION"
        elif possible == {"SHARED"}:
            classification = "PURE_SHARED_ONLY"
        elif len(possible) == 1:
            classification = "SINGLE_RELATION"
        else:
            classification = "SET_VALUED_NO_SHARED"

        relation_frames: dict[str, list[int]] = {key: [] for key in ["LEFT", "RIGHT", "OVERLAP", "SHARED"]}
        definite_order_frames: list[int] = []
        competing_direction_frames: list[int] = []
        unavailable_frames: list[int] = []
        profile_incidence = set_incidence[
            set_incidence["segment_id"].eq(profile.segment_id)
            & set_incidence["track_id"].astype(str).isin([str(profile.track_a), str(profile.track_b)])
        ]
        all_frames = sorted(profile_incidence["frame_index"].unique())
        for frame in all_frames:
            counts = frame_counts.get(int(frame), Counter())
            frame_set = {relation for relation, count in counts.items() if count > 0}
            if not frame_set:
                unavailable_frames.append(int(frame))
                continue
            for relation in frame_set:
                relation_frames[relation].append(int(frame))
            if frame_set in ({"LEFT"}, {"RIGHT"}):
                definite_order_frames.append(int(frame))
            if {"LEFT", "RIGHT"}.issubset(frame_set):
                competing_direction_frames.append(int(frame))
            a_regions = set(
                profile_incidence[
                    profile_incidence["frame_index"].eq(frame)
                    & profile_incidence["track_id"].astype(str).eq(str(profile.track_a))
                ]["physical_region_id"].astype(str)
            )
            b_regions = set(
                profile_incidence[
                    profile_incidence["frame_index"].eq(frame)
                    & profile_incidence["track_id"].astype(str).eq(str(profile.track_b))
                ]["physical_region_id"].astype(str)
            )
            frame_set_text = "{" + ",".join(sorted(frame_set)) + "}"
            for relation in sorted(frame_set):
                support_rows.append(
                    {
                        "order_profile_id": profile.order_profile_id,
                        "segment_id": profile.segment_id,
                        "run_id": profile.run_id,
                        "track_a": profile.track_a,
                        "track_b": profile.track_b,
                        "frame_index": int(frame),
                        "relation": relation,
                        "family_pair_frame_support_count": int(counts[relation]),
                        "possible_relation_set_at_frame": frame_set_text,
                        "physical_shared_region_count": len(a_regions & b_regions),
                        "definite_order_frame": frame_set in ({"LEFT"}, {"RIGHT"}),
                        "competing_direction_frame": {"LEFT", "RIGHT"}.issubset(frame_set),
                    }
                )

        profile_rows.append(
            {
                "order_profile_id": profile.order_profile_id,
                "segment_id": profile.segment_id,
                "run_id": profile.run_id,
                "track_a": profile.track_a,
                "track_b": profile.track_b,
                "old_relative_order_compatibility": profile.relative_order_compatibility,
                "possible_relation_set": "{" + ",".join(sorted(possible)) + "}",
                "relation_set_classification": classification,
                "family_a_count": len(ids_a),
                "family_b_count": len(ids_b),
                "family_pair_space_size": len(ids_a) * len(ids_b),
                "family_pairs_with_common_frames": family_pairs_with_common,
                "left_frame_set": ";".join(map(str, relation_frames["LEFT"])),
                "right_frame_set": ";".join(map(str, relation_frames["RIGHT"])),
                "overlap_frame_set": ";".join(map(str, relation_frames["OVERLAP"])),
                "shared_frame_set": ";".join(map(str, relation_frames["SHARED"])),
                "definite_order_frame_set": ";".join(map(str, definite_order_frames)),
                "competing_direction_frame_set": ";".join(map(str, competing_direction_frames)),
                "unavailable_frame_set": ";".join(map(str, unavailable_frames)),
                "left_family_pair_support_count": int(pair_support["LEFT"]),
                "right_family_pair_support_count": int(pair_support["RIGHT"]),
                "overlap_family_pair_support_count": int(pair_support["OVERLAP"]),
                "shared_family_pair_support_count": int(pair_support["SHARED"]),
                "old_shared_information_loss_repaired": (
                    profile.relative_order_compatibility == "SHARED_RESPONSE_ORDER_UNDEFINED" and len(possible) > 1
                ),
                "best_family_pair_selected": False,
                "weighted_vote_used": False,
                "manual_reference_used": False,
            }
        )
    return pd.DataFrame(profile_rows), pd.DataFrame(support_rows)


def build_burden_profiles(
    data: dict[str, pd.DataFrame],
    families: pd.DataFrame,
    cores: pd.DataFrame,
    set_incidence: pd.DataFrame,
    shared: pd.DataFrame,
) -> pd.DataFrame:
    segments = data["segments"].set_index("segment_id")
    rows: list[dict[str, Any]] = []
    for item in data["sets"].itertuples(index=False):
        segment = segments.loc[item.segment_id]
        inc = set_incidence[
            set_incidence["segment_id"].eq(item.segment_id)
            & set_incidence["track_id"].astype(str).eq(str(item.track_id))
        ]
        fam = families[
            families["segment_id"].eq(item.segment_id)
            & families["track_id"].astype(str).eq(str(item.track_id))
        ]
        core = cores[
            cores["segment_id"].eq(item.segment_id)
            & cores["track_id"].astype(str).eq(str(item.track_id))
        ]
        shared_ids = set(shared[shared["segment_id"].eq(item.segment_id)]["physical_region_id"].astype(str))
        rows.append(
            {
                "segment_id": item.segment_id,
                "run_id": item.run_id,
                "track_id": item.track_id,
                "static_physical_region_incidence_count": len(inc),
                "upper_possible_family_count": len(fam),
                "lower_core_component_count": len(core),
                "upper_multiframe_family_count": int(fam["upper_frame_count"].ge(2).sum()),
                "upper_isolated_family_count": int(fam["upper_frame_count"].eq(1).sum()),
                "lower_multiframe_component_count": int(core["core_frame_count"].ge(2).sum()),
                "lower_isolated_component_count": int(core["core_frame_count"].eq(1).sum()),
                "complete_lifecycle_possible_family_count": int(fam["complete_lifecycle_possible"].sum()),
                "connectivity_ambiguous_family_count": int(fam["optional_edge_count"].gt(0).sum()),
                "optional_bridge_dependent_family_count": int(fam["optional_bridge_dependency_count"].gt(0).sum()),
                "shared_physical_region_incidence_count": int(inc["physical_region_id"].isin(shared_ids).sum()),
                "temporal_stratification_available": bool(
                    fam["upper_frame_count"].ge(2).any() and fam["upper_frame_count"].eq(1).any()
                ),
                "counterfactual_contraction_performed": False,
                "actual_pruned_node_count": 0,
                "actual_pruned_family_count": 0,
                "post_reference_evaluated_discrimination_used": False,
                "burden_units_mixed": False,
                "manual_reference_used": False,
                "segment_frame_count": int(segment.frame_count),
            }
        )
    return pd.DataFrame(rows)


def build_timing_representation(data: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame_state = data["frame_state"].copy()
    timing_rows: list[dict[str, Any]] = []
    for run_id, group in frame_state.groupby("run_id"):
        frames = group.drop_duplicates("frame_index").sort_values("frame_index")
        sar_diff = frames["sar_timestamp_ms"].diff().dropna()
        optical_grid = np.sort(frames["nominal_optical_timestamp_ms"].unique())
        optical_diff = np.diff(optical_grid)
        residual = frames["nominal_optical_timestamp_ms"] - frames["sar_timestamp_ms"]
        timing_rows.append(
            {
                "run_id": run_id,
                "sync_status": ";".join(sorted(set(group["sync_status"].astype(str)))),
                "sar_nominal_grid_period_ms_median": float(sar_diff.median()),
                "optical_nominal_grid_period_ms_median": float(np.median(optical_diff)),
                "query_grid_residual_min_ms": int(residual.min()),
                "query_grid_residual_max_ms": int(residual.max()),
                "query_grid_residual_abs_max_ms": int(residual.abs().max()),
                "known_timing_uncertainty": "KNOWN_NOMINAL_GRID_AND_EXPOSED_QUERY_QUANTIZATION_ONLY",
                "known_sync_offset_interval_ms": "UNAVAILABLE",
                "sync_offset_state": "UNRESOLVED_SYNC_OFFSET_NO_BOUNDED_ACQUISITION_PROVENANCE",
                "unverified_default_margin_removed_ms": 250,
                "replacement_default_margin_ms": "NONE",
                "exact_cross_modal_order_authorized": False,
                "reference_used": False,
            }
        )
    authority = pd.DataFrame(timing_rows)
    global_bound = int(authority["query_grid_residual_abs_max_ms"].max())
    relations = data["event_relations"].copy().rename(columns={"temporal_relation": "nominal_frame_relation"})
    relations["known_query_grid_residual_abs_bound_ms"] = global_bound
    relations["sync_offset_lower_ms"] = np.nan
    relations["sync_offset_upper_ms"] = np.nan
    relations["timing_relation_set"] = np.where(
        relations["sar_event_type"].eq("NO_OBSERVABLE_SAR_EVENT_IN_EXPLANATION_SET"),
        "{SAR_EVENT_UNAVAILABLE}",
        "{OPTICAL_BEFORE_SAR,SAR_BEFORE_OPTICAL,TEMPORAL_SUPPORT_OVERLAP}",
    )
    relations["timing_relation_state"] = np.where(
        relations["sar_event_type"].eq("NO_OBSERVABLE_SAR_EVENT_IN_EXPLANATION_SET"),
        "SAR_EVENT_UNAVAILABLE",
        "TIMING_RELATION_SET_UNDER_UNCALIBRATED_SYNC",
    )
    relations["unverified_250ms_used"] = False
    relations["exact_temporal_order_authorized"] = False
    relations["reference_used"] = False
    relations = relations.drop(columns=["timing_uncertainty_ms"])
    return authority, relations


def build_grounding(
    post_data: dict[str, pd.DataFrame],
    physical: pd.DataFrame,
    families: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    family_grounding = families[
        ["family_id", "d0_component_id", "segment_id", "run_id", "track_id", "upper_frame_count"]
    ].merge(
        post_data["component_grounding"],
        left_on=["d0_component_id", "segment_id", "run_id", "track_id"],
        right_on=["explanation_component_id", "segment_id", "run_id", "track_id"],
        how="left",
        validate="one_to_one",
    )
    family_grounding["grounding_semantics_v1"] = (
        "POST_REFERENCE_EVALUATION_OF_UPPER_FAMILY_NOT_RUNTIME_SELECTION_OR_IDENTITY"
    )
    family_grounding["strict_identity_claimed"] = False

    reference = post_data["reference"]
    q95 = reference[reference["percentile_tag"].eq("Q095") & reference["nearest_region_id"].notna()].copy()
    region_to_physical = physical.set_index(["run_id", "frame_index", "region_id"])["physical_region_id"]
    q95["physical_region_id"] = [
        region_to_physical.get((run, frame, region), "")
        for run, frame, region in q95[["run_id", "frame_index", "nearest_region_id"]].itertuples(
            index=False, name=None
        )
    ]
    q95 = q95[q95["physical_region_id"].ne("")]
    physical_grounding = (
        q95.groupby(["run_id", "frame_index", "physical_region_id", "nearest_region_id"], as_index=False)
        .agg(
            offline_target_count=("target_id", "nunique"),
            offline_target_ids=("target_id", lambda values: ";".join(sorted(set(map(str, values))))),
            reference_support_states=(
                "reference_support_status",
                lambda values: ";".join(sorted(set(map(str, values)))),
            ),
        )
    )
    physical_grounding["runtime_use_allowed"] = False
    physical_grounding["grounding_semantics"] = (
        "POST_REFERENCE_PHYSICAL_REGION_DIAGNOSIS_NOT_TRACK_ASSIGNMENT"
    )
    return family_grounding, physical_grounding


def render_bridge_before_after(
    phase_registry: pd.DataFrame,
    edges: pd.DataFrame,
    old_edge_to_physical: dict[str, str],
) -> list[Path]:
    selected_old_ids = [
        "TERGE_12263C621633CF2CF4FC",
        "TERGE_DA8DFD297C778B401B67",
        "TERGE_F497E3F7B05444DD3CE7",
    ]
    edge_lookup = edges.set_index("physical_edge_id")
    paths: list[Path] = []
    for index, old_id in enumerate(selected_old_ids, start=1):
        row = phase_registry[phase_registry["graph_edge_id"].eq(old_id)].iloc[0]
        physical_id = old_edge_to_physical[old_id]
        edge = edge_lookup.loc[physical_id]
        source_image = plt.imread(str(row.detail_pack))
        fig = plt.figure(figsize=(16, 10))
        grid = fig.add_gridspec(2, 2, height_ratios=[3.1, 1.2])
        image_axis = fig.add_subplot(grid[0, :])
        image_axis.imshow(source_image)
        image_axis.axis("off")
        old_axis = fig.add_subplot(grid[1, 0])
        old_axis.plot([0.18, 0.82], [0.5, 0.5], color="red", lw=6)
        old_axis.scatter([0.18, 0.82], [0.5, 0.5], s=900, color=["#78b7e5", "#f2b46d"], edgecolor="black")
        old_axis.text(0.5, 0.68, "D0: Boolean SUPPORTED\nforces one connected component", ha="center")
        old_axis.text(
            0.5,
            0.18,
            f"bridge split {int(row.small_side_frame_count)}/{int(row.large_side_frame_count)} frame supports",
            ha="center",
        )
        old_axis.set_xlim(0, 1)
        old_axis.set_ylim(0, 1)
        old_axis.axis("off")
        new_axis = fig.add_subplot(grid[1, 1])
        new_axis.plot([0.18, 0.82], [0.5, 0.5], color="#d99b20", lw=4, ls="--")
        new_axis.scatter([0.18, 0.82], [0.5, 0.5], s=900, color=["#78b7e5", "#f2b46d"], edgecolor="black")
        new_axis.text(0.5, 0.72, "V1: UPPER_OPTIONAL bridge", ha="center", weight="bold")
        new_axis.text(0.5, 0.54, "legal possible connection; lower cores remain separate", ha="center")
        new_axis.text(
            0.5,
            0.18,
            f"relation={edge.edge_relation_set}\nIoU={edge.soft_iou:.3f}; ret={edge.source_total_retention:.3f}; "
            f"expl={edge.destination_explained_fraction:.3f}",
            ha="center",
            fontsize=9,
        )
        new_axis.set_xlim(0, 1)
        new_axis.set_ylim(0, 1)
        new_axis.axis("off")
        fig.suptitle("Weak bridge before/after: uncertainty retained without equal topology authority")
        fig.tight_layout()
        output = BEFORE_AFTER / f"{index:02d}_weak_bridge_{old_id}_before_after.png"
        fig.savefig(output, dpi=170)
        plt.close(fig)
        paths.append(output)
    return paths


def render_complete_family(
    data: dict[str, pd.DataFrame],
    edges: pd.DataFrame,
    old_edge_to_physical: dict[str, str],
) -> Path:
    component_id = "TERGXC_1FD4CF2856175478AA05"
    member = data["d0_memberships"][data["d0_memberships"]["explanation_component_id"].eq(component_id)].sort_values(
        "frame_index"
    )
    node_pairs = {
        (int(row.frame_index), str(row.region_id)): float(row.theta_mid_deg)
        for row in member.itertuples(index=False)
    }
    d0_edges = data["edges"]
    selected = d0_edges[
        d0_edges["run_id"].eq("R01ZF")
        & d0_edges["track_id"].astype(str).eq(str(member.iloc[0].track_id))
        & d0_edges["p0_supported_continuation"].astype(bool)
        & d0_edges.apply(
            lambda row: (int(row.source_sar_frame), str(row.source_region_id)) in node_pairs
            and (int(row.destination_sar_frame), str(row.destination_region_id)) in node_pairs,
            axis=1,
        )
    ].drop_duplicates(PHYSICAL_EDGE_KEY)
    edge_lookup = edges.set_index("physical_edge_id")
    pack = plt.imread(str(PHASE_A_ROOT / "figures" / "r01zf_f0_f15_all_intermediate_competing_components.png"))
    fig = plt.figure(figsize=(18, 14))
    grid = fig.add_gridspec(2, 1, height_ratios=[4.2, 1.3])
    axis = fig.add_subplot(grid[0, 0])
    axis.imshow(pack)
    axis.axis("off")
    graph_axis = fig.add_subplot(grid[1, 0])
    graph_axis.scatter(member["frame_index"], member["theta_mid_deg"], color="black", s=25, zorder=4)
    counts = Counter()
    for row in selected.itertuples(index=False):
        physical_id = old_edge_to_physical[str(row.graph_edge_id)]
        edge = edge_lookup.loc[physical_id]
        authority = str(edge.connectivity_authority)
        color = "#277fc1" if authority == "LOWER_CORE" else "#d65a4a"
        style = "-" if authority == "LOWER_CORE" else "--"
        counts[authority] += 1
        graph_axis.plot(
            [row.source_sar_frame, row.destination_sar_frame],
            [
                node_pairs[(int(row.source_sar_frame), str(row.source_region_id))],
                node_pairs[(int(row.destination_sar_frame), str(row.destination_region_id))],
            ],
            color=color,
            ls=style,
            lw=3,
        )
    graph_axis.set_xlabel("SAR frame")
    graph_axis.set_ylabel("azimuth theta (deg)")
    graph_axis.set_title(
        f"V1 component family: continuous upper envelope; lower-core edges={counts['LOWER_CORE']}, "
        f"optional deformation/uncertain edges={counts['UPPER_OPTIONAL']}"
    )
    graph_axis.grid(alpha=0.2)
    fig.suptitle(
        "Complete continuity remains visually legal, but optional deformation links no longer pretend to be identical to core links"
    )
    fig.tight_layout()
    output = BEFORE_AFTER / "04_r01zf_f0_f15_complete_component_family_before_after.png"
    fig.savefig(output, dpi=170)
    plt.close(fig)
    return output


def render_relation_before_after(profiles: pd.DataFrame) -> list[Path]:
    selections = [
        (
            "TERGOP_502E22A20AD671392149",
            PHASE_A_ROOT
            / "figures"
            / "relation_set_cases"
            / "01_partial_direction_with_local_shared_TERGOP_502E22A20AD671392149.png",
            "partial-direction",
        ),
        (
            "TERGOP_722FF98E6AE0A93EBAC5",
            PHASE_A_ROOT
            / "figures"
            / "relation_set_cases"
            / "02_competing_directions_with_shared_TERGOP_722FF98E6AE0A93EBAC5.png",
            "competing-direction",
        ),
    ]
    outputs: list[Path] = []
    for index, (profile_id, source, label) in enumerate(selections, start=5):
        profile = profiles[profiles["order_profile_id"].eq(profile_id)].iloc[0]
        image = plt.imread(str(source))
        fig, axes = plt.subplots(1, 2, figsize=(19, 8), gridspec_kw={"width_ratios": [4.5, 1.4]})
        axes[0].imshow(image)
        axes[0].axis("off")
        axes[1].axis("off")
        axes[1].text(0.5, 0.90, "D0", ha="center", size=16, weight="bold")
        axes[1].text(0.5, 0.82, str(profile.old_relative_order_compatibility), ha="center", wrap=True)
        axes[1].text(0.5, 0.66, "↓ representation repair", ha="center", color="#555555")
        axes[1].text(0.5, 0.56, "TERG-v1 possible relation set", ha="center", size=13, weight="bold")
        axes[1].text(0.5, 0.48, str(profile.possible_relation_set), ha="center", size=12)
        axes[1].text(0.5, 0.35, f"shared frames: {profile.shared_frame_set or 'none'}", ha="center", wrap=True)
        axes[1].text(0.5, 0.27, f"definite order frames: {profile.definite_order_frame_set or 'none'}", ha="center", wrap=True)
        axes[1].text(
            0.5,
            0.19,
            f"competing direction frames: {profile.competing_direction_frame_set or 'none'}",
            ha="center",
            wrap=True,
        )
        axes[1].text(0.5, 0.08, "No best family pair; no weighted vote", ha="center", color="#8a2d2d")
        fig.suptitle(f"Relative-order before/after: {label} information is retained")
        fig.tight_layout()
        output = BEFORE_AFTER / f"{index:02d}_{label}_relation_set_before_after.png"
        fig.savefig(output, dpi=170)
        plt.close(fig)
        outputs.append(output)
    return outputs


def render_physical_incidence(
    phase: Any,
    cmr: Any,
    cmr_data: dict[str, Any],
    physical: pd.DataFrame,
    incidence: pd.DataFrame,
) -> Path:
    region_id = "R01ZF_SARF000000__Q095__R0001"
    region = physical[physical["region_id"].eq(region_id)].iloc[0]
    inc = incidence[incidence["physical_region_id"].eq(region.physical_region_id)]
    image = cv2.imread(str(cmr.sar_image_path("R01ZF", 0)), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError("R01ZF F0 SAR image")
    region_rows = cmr_data["regions"].set_index("region_id", drop=False)
    mask = phase.mask_for_region(cmr, region_rows.loc[region_id], {})
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    axes[0].contour(mask.astype(float), levels=[0.5], colors=["magenta"], linewidths=2.4)
    axes[0].set_title("One physical SAR q95 response region")
    axes[0].axis("off")
    axes[1].axis("off")
    axes[1].scatter([0.5], [0.52], s=2400, color="#d74cb4", edgecolor="black")
    axes[1].text(0.5, 0.52, "PhysicalSarRegion\nR01ZF F0 R0001", ha="center", va="center", weight="bold")
    tracks = sorted(inc["track_id"].astype(str).unique())
    positions = np.linspace(0.18, 0.82, len(tracks))
    for x, track in zip(positions, tracks):
        axes[1].scatter([x], [0.87], s=1300, color="#77b9e6", edgecolor="black")
        axes[1].text(x, 0.87, track.split("_")[-1], ha="center", va="center", fontsize=9)
        axes[1].annotate("", xy=(0.5, 0.61), xytext=(x, 0.80), arrowprops={"arrowstyle": "->", "lw": 2})
    axes[1].text(0.5, 0.23, f"physical node rows = 1\nconditioned incidence rows = {len(inc)}", ha="center", size=13)
    axes[1].text(0.5, 0.10, "Shared semantics comes from incidence, not duplicated physical nodes", ha="center")
    axes[1].set_xlim(0, 1)
    axes[1].set_ylim(0, 1)
    fig.suptitle("Graph authority repair: physical response and optical conditioning are separate layers")
    fig.tight_layout()
    output = BEFORE_AFTER / "07_physical_region_vs_conditioned_incidence_before_after.png"
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def render_topology_before_after(edges: pd.DataFrame, old_edge_to_physical: dict[str, str]) -> list[Path]:
    selections = [
        (
            "TERGE_9E4C591EC7B819FF88B3",
            PHASE_A_ROOT
            / "figures"
            / "topology_stratified_cases"
            / "01_clear_split_high_iou_TERGE_9E4C591EC7B819FF88B3.png",
            "split-like",
        ),
        (
            "TERGE_061EAEA3EB63A4D88121",
            PHASE_A_ROOT
            / "figures"
            / "topology_stratified_cases"
            / "02_clear_merge_high_iou_TERGE_061EAEA3EB63A4D88121.png",
            "merge-like",
        ),
    ]
    lookup = edges.set_index("physical_edge_id")
    outputs: list[Path] = []
    for index, (old_id, source, label) in enumerate(selections, start=8):
        edge = lookup.loc[old_edge_to_physical[old_id]]
        image = plt.imread(str(source))
        fig, axes = plt.subplots(1, 2, figsize=(18, 7), gridspec_kw={"width_ratios": [4.6, 1.6]})
        axes[0].imshow(image)
        axes[0].axis("off")
        axes[1].axis("off")
        axes[1].text(0.5, 0.88, f"D0 hard category\n{edge.sar_topology_state}", ha="center", size=14, weight="bold")
        axes[1].text(0.5, 0.67, "↓", ha="center", size=20)
        axes[1].text(0.5, 0.56, "V1 topology hypothesis set", ha="center", size=14, weight="bold")
        axes[1].text(0.5, 0.43, str(edge.topology_hypothesis_set), ha="center", wrap=True)
        axes[1].text(0.5, 0.24, f"connectivity authority: {edge.connectivity_authority}", ha="center", wrap=True)
        axes[1].text(0.5, 0.12, "split/merge hard event claimed = false", ha="center", color="#8a2d2d")
        fig.suptitle(f"Topology before/after: {label} coexists with deformation/fragmentation uncertainty")
        fig.tight_layout()
        output = BEFORE_AFTER / f"{index:02d}_{label}_topology_set_before_after.png"
        fig.savefig(output, dpi=175)
        plt.close(fig)
        outputs.append(output)
    return outputs


def render_timing_authority(authority: pd.DataFrame) -> Path:
    fig, axis = plt.subplots(figsize=(13, 5.5))
    axis.axis("off")
    lines = [
        ("KNOWN", "SAR nominal grid", f"median period {authority.sar_nominal_grid_period_ms_median.median():.1f} ms"),
        ("KNOWN", "Optical nominal grid", f"median period {authority.optical_nominal_grid_period_ms_median.median():.1f} ms"),
        ("KNOWN", "Exposed query quantization", f"observed residual within ±{int(authority.query_grid_residual_abs_max_ms.max())} ms"),
        ("UNKNOWN", "Cross-modal synchronization offset", "no bounded acquisition provenance"),
        ("REMOVED", "Default ±250 ms", "not used and not replaced by an invented ±N ms"),
        ("OUTPUT", "Timing relation", "set-valued under uncalibrated synchronization"),
    ]
    colors = {"KNOWN": "#2f7d32", "UNKNOWN": "#b36b00", "REMOVED": "#a33a3a", "OUTPUT": "#315f9d"}
    for index, (state, name, detail) in enumerate(lines):
        y = 0.88 - index * 0.145
        axis.text(0.05, y, state, color=colors[state], weight="bold", size=13)
        axis.text(0.18, y, name, weight="bold", size=11)
        axis.text(0.67, y, detail, size=10)
    axis.set_title("TERG-v1 timing authority: known grid facts separated from unresolved synchronization", size=15)
    output = BEFORE_AFTER / "10_timing_known_unknown_before_after.png"
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output


def render_grounding_and_counterexample(
    data: dict[str, pd.DataFrame],
    physical: pd.DataFrame,
    family_grounding: pd.DataFrame,
    physical_grounding: pd.DataFrame,
) -> Path:
    selected_id = "TERGXC_1FD4CF2856175478AA05"
    partial_id = "TERGXC_A97D2FC78FCD287ADEEE"
    selected = family_grounding[family_grounding["d0_component_id"].eq(selected_id)].iloc[0]
    partial = family_grounding[family_grounding["d0_component_id"].eq(partial_id)].iloc[0]
    partial_member = data["d0_memberships"][
        data["d0_memberships"]["explanation_component_id"].eq(partial_id)
    ].sort_values("frame_index")
    first = partial_member.iloc[0]
    physical_id = physical.set_index(PHYSICAL_NODE_KEY).loc[
        (str(first.run_id), int(first.frame_index), str(first.region_id)), "physical_region_id"
    ]
    grounded = physical_grounding[physical_grounding["physical_region_id"].eq(physical_id)]
    offline_targets = "UNAVAILABLE" if grounded.empty else str(grounded.iloc[0].offline_target_ids)

    pack = plt.imread(str(PHASE_A_ROOT / "figures" / "r01zf_f0_f15_all_intermediate_competing_components.png"))
    fig = plt.figure(figsize=(20, 10))
    grid = fig.add_gridspec(1, 2, width_ratios=[3.3, 1.2])
    image_axis = fig.add_subplot(grid[0, 0])
    image_axis.imshow(pack)
    image_axis.axis("off")
    text_axis = fig.add_subplot(grid[0, 1])
    text_axis.axis("off")
    text_axis.text(0.02, 0.95, "D0 wording risk", weight="bold", size=16)
    text_axis.text(0.02, 0.88, "LIKELY grounding or partial/rejected wording\ncan be mistaken for runtime selection or identity.", size=12)
    text_axis.text(0.02, 0.70, "V1 post-reference grounding", weight="bold", size=16, color="#315f9d")
    text_axis.text(
        0.02,
        0.57,
        f"Complete upper family: {int(selected.upper_frame_count)} frames\n"
        f"Reference-supported frames: {int(selected.reference_supported_component_frame_count)}/"
        f"{int(selected.reference_frame_count)}\n"
        "Visual continuity is strong, but strict identity = false.",
        size=12,
    )
    text_axis.text(0.02, 0.39, "Counterexample retained", weight="bold", size=16, color="#a33a3a")
    text_axis.text(
        0.02,
        0.22,
        f"Partial upper family: {int(partial.upper_frame_count)} frames\n"
        f"Reference-supported frames for conditioned track: {int(partial.reference_supported_component_frame_count)}\n"
        f"Its F0 physical region is grounded offline to: {offline_targets}\n"
        "Therefore partial != broken/rejected selected response.",
        size=11,
    )
    text_axis.text(
        0.02,
        0.06,
        "Grounding is post-reference diagnosis only;\nnot graph construction, assignment, or final localization.",
        size=11,
        color="#6b3d2e",
    )
    fig.suptitle("Grounding and counterexample: V1 keeps possible families separate from post-reference diagnosis", size=18)
    fig.tight_layout()
    output = BEFORE_AFTER / "11_grounding_and_partial_counterexample_before_after.png"
    fig.savefig(output, dpi=160)
    plt.close(fig)
    return output


def render_contact_sheet(paths: list[Path]) -> Path:
    selected = paths[:10]
    fig, axes = plt.subplots(5, 2, figsize=(18, 22))
    for axis, path in zip(axes.flat, selected):
        axis.imshow(plt.imread(str(path)))
        axis.set_title(path.stem, fontsize=9)
        axis.axis("off")
    for axis in axes.flat[len(selected) :]:
        axis.axis("off")
    fig.suptitle("TERG-D0R real-image before/after review contact sheet", size=18)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    output = FIGURES / "TERG_V1_SET_VALUED_REPRESENTATION_REVIEW_CONTACT_SHEET.jpg"
    fig.savefig(output, dpi=120)
    plt.close(fig)
    return output


def main() -> None:
    for path in [OUTPUT, PRE, POST, FIGURES, BEFORE_AFTER]:
        path.mkdir(parents=True, exist_ok=True)
    data = load_pre_reference_inputs()
    physical, incidence, set_incidence, shared = build_physical_layers(data)
    edges, old_edge_to_physical = build_physical_edges(data, physical)
    families, cores, memberships, bridges = build_component_families(
        data, physical, set_incidence, edges
    )
    edges = add_bridge_authority(edges, bridges)
    relation_profiles, relation_support = build_relation_sets(
        data, physical, families, memberships, set_incidence
    )
    burden = build_burden_profiles(data, families, cores, set_incidence, shared)
    timing_authority, timing_relations = build_timing_representation(data)

    pre_freeze_summary = {
        "physical_region_count": len(physical),
        "conditioned_incidence_count": len(incidence),
        "set_incidence_count": len(set_incidence),
        "physical_edge_count": len(edges),
        "supported_physical_edge_count": int(edges["p0_supported_continuation"].sum()),
        "lower_core_edge_count": int(edges["lower_core_eligible"].sum()),
        "upper_optional_edge_count": int(edges["connectivity_authority"].eq("UPPER_OPTIONAL").sum()),
        "upper_family_count": len(families),
        "lower_core_component_count": len(cores),
        "optional_bridge_dependency_rows": len(bridges),
        "relation_profile_count": len(relation_profiles),
        "shared_profile_count": int(
            relation_profiles["possible_relation_set"].str.contains("SHARED", regex=False).sum()
        ),
        "shared_partial_direction_count": int(
            relation_profiles["relation_set_classification"].eq("SHARED_PLUS_PARTIAL_DIRECTION").sum()
        ),
        "shared_competing_direction_count": int(
            relation_profiles["relation_set_classification"].eq("SHARED_PLUS_COMPETING_DIRECTIONS").sum()
        ),
        "pure_shared_only_count": int(
            relation_profiles["relation_set_classification"].eq("PURE_SHARED_ONLY").sum()
        ),
        "temporal_stratification_set_count": int(burden["temporal_stratification_available"].sum()),
        "actual_pruned_node_count": int(burden["actual_pruned_node_count"].sum()),
        "actual_pruned_family_count": int(burden["actual_pruned_family_count"].sum()),
    }
    write_json(PRE / "pre_reference_freeze_summary.json", pre_freeze_summary)
    write_table(physical, PRE / "physical_sar_response_regions_pre_reference")
    write_table(incidence, PRE / "optical_conditioned_region_incidence_pre_reference")
    write_table(set_incidence, PRE / "explanation_set_region_incidence_pre_reference", csv=False)
    write_table(shared, PRE / "shared_physical_region_incidence_pre_reference")
    write_table(edges, PRE / "set_valued_physical_temporal_edges_pre_reference", csv=False)
    write_table(families, PRE / "admissible_component_families_pre_reference")
    write_table(cores, PRE / "lower_core_components_pre_reference", csv=False)
    write_table(memberships, PRE / "component_family_membership_pre_reference", csv=False)
    write_table(bridges, PRE / "optional_bridge_dependencies_pre_reference", csv=False)
    write_table(relation_profiles, PRE / "possible_relation_sets_pre_reference")
    write_table(relation_support, PRE / "relation_temporal_support_extents_pre_reference", csv=False)
    write_table(burden, PRE / "temporal_stratification_burden_profiles_pre_reference")
    write_table(timing_authority, PRE / "timing_authority_pre_reference")
    write_table(timing_relations, PRE / "timing_relation_sets_pre_reference", csv=False)

    post_data = load_post_reference_inputs()
    family_grounding, physical_grounding = build_grounding(post_data, physical, families)
    write_table(family_grounding, POST / "component_family_grounding_post_reference", csv=False)
    write_table(physical_grounding, POST / "physical_region_grounding_post_reference")

    phase = load_module(PHASE_A_SCRIPT, "terg_phase_a_for_d0r")
    cmr = phase.load_cmr()
    cmr_data = cmr.load_authorities()
    phase_bridge_registry = pd.read_csv(PHASE_A_ROOT / "tables" / "bridge_critical_edge_case_registry.csv")
    visual_paths: list[Path] = []
    visual_paths.extend(render_bridge_before_after(phase_bridge_registry, edges, old_edge_to_physical))
    visual_paths.append(render_complete_family(data, edges, old_edge_to_physical))
    visual_paths.extend(render_relation_before_after(relation_profiles))
    visual_paths.append(render_physical_incidence(phase, cmr, cmr_data, physical, incidence))
    visual_paths.extend(render_topology_before_after(edges, old_edge_to_physical))
    visual_paths.append(render_timing_authority(timing_authority))
    visual_paths.append(
        render_grounding_and_counterexample(data, physical, family_grounding, physical_grounding)
    )
    contact_sheet = render_contact_sheet(visual_paths)

    weak_phase = pd.read_csv(PHASE_A_ROOT / "tables" / "bridge_criticality.csv")
    weak_ids = {
        old_edge_to_physical[edge_id]
        for edge_id in weak_phase[weak_phase["audit_edge_family"].eq("WEAK_CONTINUATION")][
            "graph_edge_id"
        ].astype(str)
        if edge_id in old_edge_to_physical
    }
    weak_edge_rows = edges[edges["physical_edge_id"].isin(weak_ids)]
    reality_checks = {
        "phase": "TERG_D0R_SET_VALUED_GRAPH_REPRESENTATION_REPAIR",
        "confirmation_run_accessed": False,
        "r04zf_accessed": False,
        "reference_used_for_representation": False,
        "weighted_scalar_score_used": False,
        "new_numeric_threshold_used_for_repair": False,
        "physical_layer_unique": len(physical) == physical["physical_region_id"].nunique(),
        "physical_node_duplication_removed": len(physical) == 3056 and len(incidence) == 4328,
        "upper_envelope_preserves_d0_components": len(families) == len(data["d0_components"]),
        "all_phase_a_weak_bridge_edges_remain_legal_upper_edges": bool(
            weak_edge_rows["p0_supported_continuation"].all()
        ),
        "all_phase_a_weak_bridge_edges_lack_lower_core_authority": bool(
            ~weak_edge_rows["lower_core_eligible"].any()
        ),
        "shared_profile_information_preserved": (
            pre_freeze_summary["shared_profile_count"] == 78
            and pre_freeze_summary["shared_partial_direction_count"] == 27
            and pre_freeze_summary["shared_competing_direction_count"] == 51
            and pre_freeze_summary["pure_shared_only_count"] == 0
        ),
        "split_merge_hard_events_removed": bool(~edges["split_merge_hard_event_claimed"].any()),
        "timing_250ms_semantics_removed": bool(~timing_relations["unverified_250ms_used"].any()),
        "unresolved_sync_offset_preserved": bool(
            timing_authority["sync_offset_state"].eq(
                "UNRESOLVED_SYNC_OFFSET_NO_BOUNDED_ACQUISITION_PROVENANCE"
            ).all()
        ),
        "temporal_stratification_preserved": pre_freeze_summary["temporal_stratification_set_count"] == 87,
        "actual_pruning_remains_zero": (
            pre_freeze_summary["actual_pruned_node_count"] == 0
            and pre_freeze_summary["actual_pruned_family_count"] == 0
        ),
        "remaining_human_visible_limitation": (
            "Visual continuity can be stronger than lower-core authority; V1 preserves it as an upper possible "
            "family but does not claim identity or force optional deformation links into the core."
        ),
        "visual_before_after_packs": [str(path) for path in visual_paths],
        "contact_sheet": str(contact_sheet),
    }
    ready_checks = [
        value
        for key, value in reality_checks.items()
        if isinstance(value, bool) and key not in {"confirmation_run_accessed", "r04zf_accessed", "reference_used_for_representation", "weighted_scalar_score_used", "new_numeric_threshold_used_for_repair"}
    ]
    final_state = (
        "TERG_V1_READY_FOR_INDEPENDENT_CONFIRMATION"
        if all(ready_checks)
        and not reality_checks["confirmation_run_accessed"]
        and not reality_checks["r04zf_accessed"]
        and not reality_checks["reference_used_for_representation"]
        and not reality_checks["weighted_scalar_score_used"]
        and not reality_checks["new_numeric_threshold_used_for_repair"]
        else "TERG_REPRESENTATION_STILL_NOT_REALITY_ALIGNED"
    )
    summary = {
        "schema": "PERSON_TERG_V1_SET_VALUED_TEMPORAL_EXPLANATION_SUMMARY_V1",
        "final_state": final_state,
        "pre_reference_freeze_summary": pre_freeze_summary,
        "reality_alignment_checks": reality_checks,
        "mechanism_name": "TERG_V1_SET_VALUED_TEMPORAL_EXPLANATION_MECHANISM",
        "lower_core_semantic_rule": {
            "new_numeric_threshold": "NONE",
            "mutual_local_dominance": True,
            "exclusive_one_to_one_topology": True,
            "p0_residual_state_core": "SAR_P0_RESIDUAL_COMMON_COMPATIBLE",
            "deformation_evidence": False,
            "boundary_censoring_evidence": False,
            "reference_fitted": False,
            "semantics": "THRESHOLD_FREE_CATEGORICAL_INTERSECTION_WITH_RAW_CONTINUOUS_EVIDENCE_RETAINED",
        },
        "outputs": {
            "pre_reference": str(PRE),
            "post_reference": str(POST),
            "figures": str(FIGURES),
        },
    }
    write_json(OUTPUT / "terg_v1_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
