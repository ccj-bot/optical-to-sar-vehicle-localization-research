from __future__ import annotations

import importlib.util
import json
import math
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
TERG_ROOT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "terg_d0_temporal_event_response_graph_mechanism_exploration"
)
PRE = TERG_ROOT / "pre_reference"
POST = TERG_ROOT / "post_reference"
P1E_ROOT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "p1e_sar_only_response_interface"
    / "runtime_track_response_region_minimal_v1"
)
CMR_SCRIPT = (
    WORKSPACE
    / "tasks"
    / "person_cmr_d0_common_residual_motion_mechanism_development_20260829"
    / "run_cmr_d0_development.py"
)
OUTPUT = WORKSPACE / "output" / "person_terg_v0_visual_semantic_reality_check_20260829"
TABLES = OUTPUT / "tables"
FIGURES = OUTPUT / "figures"
BRIDGE_FIGURES = FIGURES / "bridge_critical_edges"
TOPOLOGY_FIGURES = FIGURES / "topology_stratified_cases"
EXACT_ONE_FIGURES = FIGURES / "exact_one_soft_overlap_edges"
RELATION_FIGURES = FIGURES / "relation_set_cases"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_cmr():
    spec = importlib.util.spec_from_file_location("terg_audit_cmr", CMR_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen CMR module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_tables() -> dict[str, pd.DataFrame]:
    names = {
        "edges": PRE / "sar_response_graph_edges_pre_reference.parquet",
        "nodes": PRE / "sar_response_graph_nodes_pre_reference.parquet",
        "components": PRE / "terg_explanation_components_pre_reference.parquet",
        "memberships": PRE / "terg_component_node_membership_pre_reference.parquet",
        "segments": PRE / "temporal_segment_atlas_pre_reference.parquet",
        "sets": PRE / "terg_explanation_sets_pre_reference.parquet",
        "order": PRE / "relative_order_compatibility_pre_reference.parquet",
        "component_grounding": POST / "explanation_component_grounding.parquet",
        "segment_grounding": POST / "temporal_segment_evaluation_grounding.parquet",
    }
    data = {name: pd.read_parquet(path) for name, path in names.items()}
    data["reference"] = pd.read_csv(P1E_ROOT / "offline_reference_response_region_evaluation.csv")
    data["assignment"] = pd.read_csv(P1E_ROOT / "offline_one_to_one_track_reference_assignment.csv")
    return data


def endpoint_node_maps(nodes: pd.DataFrame) -> tuple[dict[tuple[str, str, int, str], str], dict[str, int]]:
    node_key = {
        (str(r.run_id), str(r.track_id), int(r.frame_index), str(r.region_id)): str(r.track_node_id)
        for r in nodes.itertuples(index=False)
    }
    node_frame = {str(r.track_node_id): int(r.frame_index) for r in nodes.itertuples(index=False)}
    return node_key, node_frame


def add_edge_descriptors(edges: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    frame = edges.copy()
    supported = frame[frame["p0_supported_continuation"]].copy()
    out_key = ["run_id", "track_id", "source_sar_frame", "source_region_id"]
    in_key = ["run_id", "track_id", "destination_sar_frame", "destination_region_id"]
    supported["outgoing_max_soft_intersection_px"] = supported.groupby(out_key)["soft_intersection_px"].transform("max")
    supported["incoming_max_soft_intersection_px"] = supported.groupby(in_key)["soft_intersection_px"].transform("max")
    supported["source_local_dominant"] = np.isclose(
        supported["soft_intersection_px"], supported["outgoing_max_soft_intersection_px"]
    )
    supported["destination_local_dominant"] = np.isclose(
        supported["soft_intersection_px"], supported["incoming_max_soft_intersection_px"]
    )
    supported["mutual_local_dominant"] = supported["source_local_dominant"] & supported["destination_local_dominant"]
    supported["outgoing_relative_strength"] = supported["soft_intersection_px"] / supported[
        "outgoing_max_soft_intersection_px"
    ].replace(0, np.nan)
    supported["incoming_relative_strength"] = supported["soft_intersection_px"] / supported[
        "incoming_max_soft_intersection_px"
    ].replace(0, np.nan)

    q = {
        "soft_intersection_q01": float(supported["soft_intersection_px"].quantile(0.01)),
        "soft_intersection_q05": float(supported["soft_intersection_px"].quantile(0.05)),
        "soft_intersection_q10": float(supported["soft_intersection_px"].quantile(0.10)),
        "soft_iou_q01": float(supported["soft_iou"].quantile(0.01)),
        "soft_iou_q05": float(supported["soft_iou"].quantile(0.05)),
        "soft_iou_q10": float(supported["soft_iou"].quantile(0.10)),
        "soft_iou_median": float(supported["soft_iou"].median()),
    }
    deformation = supported["sar_p0_residual_state"].astype(str).str.contains("DEFORMATION")
    boundary = (
        supported["source_touches_boundary"].astype(bool)
        | supported["destination_touches_boundary"].astype(bool)
        | supported["source_truncated"].astype(bool)
        | supported["destination_truncated"].astype(bool)
    )
    low_evidence = (
        supported["soft_intersection_px"].le(q["soft_intersection_q10"])
        | supported["soft_iou"].le(q["soft_iou_q10"])
    )
    supported["audit_edge_family"] = np.select(
        [
            deformation,
            low_evidence & ~supported["mutual_local_dominant"],
            supported["mutual_local_dominant"] & ~low_evidence & ~boundary,
        ],
        ["DEFORMATION_LINK", "WEAK_CONTINUATION", "CORE_CONTINUATION"],
        default="UNCERTAIN_CONTINUATION",
    )
    supported["audit_family_is_mechanism_threshold"] = False
    descriptors = supported[
        [
            "graph_edge_id",
            "outgoing_max_soft_intersection_px",
            "incoming_max_soft_intersection_px",
            "source_local_dominant",
            "destination_local_dominant",
            "mutual_local_dominant",
            "outgoing_relative_strength",
            "incoming_relative_strength",
            "audit_edge_family",
            "audit_family_is_mechanism_threshold",
        ]
    ]
    frame = frame.merge(descriptors, on="graph_edge_id", how="left", validate="one_to_one")
    frame.loc[~frame["p0_supported_continuation"], "audit_edge_family"] = "UNSUPPORTED"
    frame["exact_one_soft_pixel_mass"] = np.isclose(frame["soft_intersection_px"].fillna(0), 1.0)
    return frame, q


def physical_node_audit(nodes: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    keys = ["run_id", "frame_index", "region_id"]
    physical = (
        nodes.groupby(keys, as_index=False)
        .agg(conditioned_node_count=("track_node_id", "nunique"), conditioned_track_count=("track_id", "nunique"))
    )
    physical["duplicated_across_optical_tracks"] = physical["conditioned_track_count"].gt(1)
    summary = {
        "conditioned_graph_node_rows": int(len(nodes)),
        "unique_physical_sar_response_regions": int(len(physical)),
        "physical_regions_duplicated_across_tracks": int(physical["duplicated_across_optical_tracks"].sum()),
        "conditioned_nodes_belonging_to_duplicated_physical_regions": int(
            physical.loc[physical["duplicated_across_optical_tracks"], "conditioned_node_count"].sum()
        ),
        "maximum_track_conditioned_copies_of_one_physical_region": int(physical["conditioned_track_count"].max()),
    }
    return physical, summary


def bridge_audit(
    edges: pd.DataFrame,
    memberships: pd.DataFrame,
    components: pd.DataFrame,
    node_key: dict[tuple[str, str, int, str], str],
    node_frame: dict[str, int],
) -> pd.DataFrame:
    supported = edges[edges["p0_supported_continuation"]].copy()
    edge_by_id = supported.set_index("graph_edge_id", drop=False)
    rows: list[dict[str, Any]] = []
    for component in components[components["component_node_count"].gt(1)].itertuples(index=False):
        member = memberships[memberships["explanation_component_id"].eq(component.explanation_component_id)]
        member_ids = set(member["track_node_id"].astype(str))
        candidate = supported[
            supported["run_id"].eq(component.run_id)
            & supported["track_id"].astype(str).eq(str(component.track_id))
            & supported["source_sar_frame"].between(component.segment_start_sar_frame, component.segment_end_sar_frame - 1)
        ]
        graph = nx.Graph()
        graph.add_nodes_from(member_ids)
        for edge in candidate.itertuples(index=False):
            source = node_key.get((str(edge.run_id), str(edge.track_id), int(edge.source_sar_frame), str(edge.source_region_id)))
            destination = node_key.get(
                (str(edge.run_id), str(edge.track_id), int(edge.destination_sar_frame), str(edge.destination_region_id))
            )
            if source in member_ids and destination in member_ids:
                graph.add_edge(source, destination, graph_edge_id=str(edge.graph_edge_id))
        for source, destination in nx.bridges(graph):
            edge_id = str(graph.edges[source, destination]["graph_edge_id"])
            payload = edge_by_id.loc[edge_id]
            cut = graph.copy()
            cut.remove_edge(source, destination)
            parts = sorted(nx.connected_components(cut), key=len)
            if len(parts) != 2:
                continue
            small, large = parts
            small_frames = {node_frame[n] for n in small}
            large_frames = {node_frame[n] for n in large}
            rows.append(
                {
                    "explanation_component_id": component.explanation_component_id,
                    "segment_id": component.segment_id,
                    "run_id": component.run_id,
                    "track_id": component.track_id,
                    "graph_edge_id": edge_id,
                    "source_sar_frame": int(payload.source_sar_frame),
                    "destination_sar_frame": int(payload.destination_sar_frame),
                    "source_region_id": str(payload.source_region_id),
                    "destination_region_id": str(payload.destination_region_id),
                    "soft_intersection_px": float(payload.soft_intersection_px),
                    "source_total_retention": float(payload.source_total_retention),
                    "destination_explained_fraction": float(payload.destination_explained_fraction),
                    "soft_iou": float(payload.soft_iou),
                    "audit_edge_family": str(payload.audit_edge_family),
                    "sar_p0_residual_state": str(payload.sar_p0_residual_state),
                    "sar_topology_state": str(payload.sar_topology_state),
                    "mutual_local_dominant": bool(payload.mutual_local_dominant),
                    "exact_one_soft_pixel_mass": bool(payload.exact_one_soft_pixel_mass),
                    "component_node_count": int(component.component_node_count),
                    "component_frame_count": int(component.component_frame_count),
                    "small_side_node_count": len(small),
                    "large_side_node_count": len(large),
                    "small_side_frame_count": len(small_frames),
                    "large_side_frame_count": len(large_frames),
                    "bridge_frame_balance": len(small_frames) / max(1, len(large_frames)),
                }
            )
    return pd.DataFrame(rows)


def graph_summary_for_mask(
    segment: Any,
    track_id: str,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    edge_mask: pd.Series,
    node_key: dict[tuple[str, str, int, str], str],
) -> dict[str, Any]:
    n = nodes[
        nodes["run_id"].eq(segment.run_id)
        & nodes["track_id"].astype(str).eq(track_id)
        & nodes["frame_index"].between(segment.start_sar_frame, segment.end_sar_frame)
    ]
    graph = nx.Graph()
    graph.add_nodes_from(n["track_node_id"].astype(str))
    e = edges[
        edge_mask
        & edges["run_id"].eq(segment.run_id)
        & edges["track_id"].astype(str).eq(track_id)
        & edges["source_sar_frame"].between(segment.start_sar_frame, segment.end_sar_frame - 1)
    ]
    for row in e.itertuples(index=False):
        source = node_key.get((str(row.run_id), str(row.track_id), int(row.source_sar_frame), str(row.source_region_id)))
        destination = node_key.get(
            (str(row.run_id), str(row.track_id), int(row.destination_sar_frame), str(row.destination_region_id))
        )
        if source in graph and destination in graph:
            graph.add_edge(source, destination)
    parts = list(nx.connected_components(graph))
    frame_lookup = n.set_index("track_node_id")["frame_index"].astype(int).to_dict()
    part_frame_counts = [len({frame_lookup[x] for x in part}) for part in parts]
    return {
        "component_count": len(parts),
        "multi_frame_component_count": int(sum(x >= 2 for x in part_frame_counts)),
        "isolated_component_count": int(sum(x == 1 for x in part_frame_counts)),
        "largest_component_node_count": max((len(x) for x in parts), default=0),
        "largest_component_frame_count": max(part_frame_counts, default=0),
        "full_frame_coverage_component_count": int(sum(x == int(segment.frame_count) for x in part_frame_counts)),
    }


def connectivity_sensitivity(
    sets: pd.DataFrame,
    segments: pd.DataFrame,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    node_key: dict[tuple[str, str, int, str], str],
    q: dict[str, float],
) -> pd.DataFrame:
    base = edges["p0_supported_continuation"].astype(bool)
    variants = {
        "ALL_POSITIVE_SOFT_SUPPORT": base,
        "REMOVE_EXACT_ONE_SOFT_PIXEL_MASS": base & ~edges["exact_one_soft_pixel_mass"],
        "REMOVE_BOTTOM_1PCT_SOFT_IOU": base & edges["soft_iou"].gt(q["soft_iou_q01"]),
        "REMOVE_NONDOMINANT_BOTTOM_DECILE": base
        & ~(
            edges["soft_iou"].le(q["soft_iou_q10"])
            & ~edges["mutual_local_dominant"].fillna(False)
        ),
        "MUTUAL_LOCAL_DOMINANCE_ONLY": base & edges["mutual_local_dominant"].fillna(False),
    }
    segment_lookup = segments.set_index("segment_id")
    rows: list[dict[str, Any]] = []
    for item in sets.itertuples(index=False):
        segment = segment_lookup.loc[item.segment_id]
        for name, mask in variants.items():
            summary = graph_summary_for_mask(segment, str(item.track_id), nodes, edges, mask, node_key)
            rows.append(
                {
                    "segment_id": item.segment_id,
                    "run_id": item.run_id,
                    "track_id": item.track_id,
                    "variant": name,
                    **summary,
                }
            )
    return pd.DataFrame(rows)


def topology_sensitivity(edges: pd.DataFrame, q: dict[str, float]) -> pd.DataFrame:
    base = edges["p0_supported_continuation"].astype(bool)
    variants = {
        "ALL_POSITIVE_SOFT_SUPPORT": base,
        "REMOVE_EXACT_ONE_SOFT_PIXEL_MASS": base & ~edges["exact_one_soft_pixel_mass"],
        "REMOVE_BOTTOM_1PCT_SOFT_IOU": base & edges["soft_iou"].gt(q["soft_iou_q01"]),
        "REMOVE_NONDOMINANT_BOTTOM_DECILE": base
        & ~(
            edges["soft_iou"].le(q["soft_iou_q10"])
            & ~edges["mutual_local_dominant"].fillna(False)
        ),
    }
    rows: list[dict[str, Any]] = []
    source_keys = ["run_id", "track_id", "source_sar_frame", "source_region_id"]
    destination_keys = ["run_id", "track_id", "destination_sar_frame", "destination_region_id"]
    for name, mask in variants.items():
        retained = edges[mask].copy()
        out_count = retained.groupby(source_keys).size().rename("out_count")
        in_count = retained.groupby(destination_keys).size().rename("in_count")
        retained = retained.join(out_count, on=source_keys).join(in_count, on=destination_keys)
        retained["recomputed_topology"] = np.select(
            [
                retained["out_count"].gt(1) & retained["in_count"].gt(1),
                retained["out_count"].gt(1),
                retained["in_count"].gt(1),
            ],
            ["P0_SPLIT_AND_MERGE_LIKE", "P0_SPLIT_LIKE", "P0_MERGE_LIKE"],
            default="P0_ONE_TO_ONE_LIKE_OR_UNSUPPORTED",
        )
        counts = retained["recomputed_topology"].value_counts().to_dict()
        rows.append(
            {
                "variant": name,
                "retained_supported_edge_count": len(retained),
                "one_to_one_edge_count": int(counts.get("P0_ONE_TO_ONE_LIKE_OR_UNSUPPORTED", 0)),
                "split_edge_count": int(counts.get("P0_SPLIT_LIKE", 0)),
                "merge_edge_count": int(counts.get("P0_MERGE_LIKE", 0)),
                "split_and_merge_edge_count": int(counts.get("P0_SPLIT_AND_MERGE_LIKE", 0)),
            }
        )
    return pd.DataFrame(rows)


def relation_set_audit(
    order: pd.DataFrame, components: pd.DataFrame, memberships: pd.DataFrame, nodes: pd.DataFrame
) -> pd.DataFrame:
    bounds = nodes[["track_node_id", "theta_min_deg", "theta_max_deg"]].drop_duplicates("track_node_id")
    member = memberships.merge(bounds, on="track_node_id", how="left", validate="many_to_one")
    component_frames: dict[str, dict[int, tuple[set[str], float, float]]] = {}
    for component_id, group in member.groupby("explanation_component_id"):
        frame_payload: dict[int, tuple[set[str], float, float]] = {}
        for frame, rows in group.groupby("frame_index"):
            frame_payload[int(frame)] = (
                set(rows["region_id"].astype(str)),
                float(rows["theta_min_deg"].min()),
                float(rows["theta_max_deg"].max()),
            )
        component_frames[str(component_id)] = frame_payload
    component_ids = components.groupby(["segment_id", "track_id"])["explanation_component_id"].agg(list).to_dict()

    rows: list[dict[str, Any]] = []
    for profile in order.itertuples(index=False):
        ids_a = component_ids.get((profile.segment_id, profile.track_a), [])
        ids_b = component_ids.get((profile.segment_id, profile.track_b), [])
        relation_occurrences: Counter[str] = Counter()
        pair_support: Counter[str] = Counter()
        pair_count_with_common_frames = 0
        exclusive_pair_counts: Counter[str] = Counter()
        for comp_a in ids_a:
            fa = component_frames[str(comp_a)]
            for comp_b in ids_b:
                fb = component_frames[str(comp_b)]
                common = sorted(set(fa) & set(fb))
                if not common:
                    continue
                pair_count_with_common_frames += 1
                pair_relations: set[str] = set()
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
                    relation_occurrences[relation] += 1
                    pair_relations.add(relation)
                for relation in pair_relations:
                    pair_support[relation] += 1
                if len(pair_relations) == 1:
                    exclusive_pair_counts[next(iter(pair_relations))] += 1
        possible = {key for key, value in relation_occurrences.items() if value > 0}
        if possible == {"SHARED"}:
            classification = "SHARED_ONLY"
        elif "SHARED" in possible and {"LEFT", "RIGHT"}.issubset(possible):
            classification = "SHARED_PLUS_COMPETING_DIRECTIONS"
        elif "SHARED" in possible and ("LEFT" in possible or "RIGHT" in possible):
            classification = "SHARED_PLUS_PARTIAL_DIRECTION"
        elif "SHARED" in possible and "OVERLAP" in possible:
            classification = "SHARED_PLUS_OVERLAP"
        elif "SHARED" in possible:
            classification = "SHARED_WITH_OTHER_UNRESOLVED_RELATIONS"
        elif {"LEFT", "RIGHT"}.issubset(possible):
            classification = "COMPETING_DIRECTIONS_WITHOUT_SHARED"
        elif len(possible) == 1:
            classification = "SINGLE_RELATION_NO_SHARED"
        else:
            classification = "SET_VALUED_NO_SHARED"
        rows.append(
            {
                "order_profile_id": profile.order_profile_id,
                "segment_id": profile.segment_id,
                "run_id": profile.run_id,
                "track_a": profile.track_a,
                "track_b": profile.track_b,
                "current_relative_order_compatibility": profile.relative_order_compatibility,
                "current_shared_region_frame_count": int(profile.shared_region_frame_count),
                "component_pair_space_size": int(profile.component_pair_space_size),
                "component_pairs_with_common_frames": pair_count_with_common_frames,
                "possible_relation_set": "{" + ",".join(sorted(possible)) + "}",
                "relation_set_classification": classification,
                **{f"pair_frame_{key.lower()}_count": int(relation_occurrences[key]) for key in ("LEFT", "RIGHT", "SHARED", "OVERLAP")},
                **{f"component_pair_support_{key.lower()}_count": int(pair_support[key]) for key in ("LEFT", "RIGHT", "SHARED", "OVERLAP")},
                **{f"exclusive_component_pair_{key.lower()}_count": int(exclusive_pair_counts[key]) for key in ("LEFT", "RIGHT", "SHARED", "OVERLAP")},
            }
        )
    return pd.DataFrame(rows)


def contraction_audit(
    sets: pd.DataFrame,
    components: pd.DataFrame,
    component_grounding: pd.DataFrame,
) -> pd.DataFrame:
    component = components.merge(
        component_grounding,
        on=["segment_id", "run_id", "track_id", "explanation_component_id"],
        how="left",
        validate="one_to_one",
    )
    rows: list[dict[str, Any]] = []
    for item in sets.itertuples(index=False):
        group = component[
            component["segment_id"].eq(item.segment_id) & component["track_id"].astype(str).eq(str(item.track_id))
        ]
        multi = group[group["component_frame_count"].ge(2)]
        isolated = group[group["component_frame_count"].eq(1)]
        likely = group[group["component_grounding_state"].eq("LIKELY_SUPPORTED_EXPLORATORY")]
        rows.append(
            {
                "segment_id": item.segment_id,
                "run_id": item.run_id,
                "track_id": item.track_id,
                "static_corridor_node_count": int(item.static_corridor_node_count),
                "sum_component_node_count": int(group["component_node_count"].sum()),
                "all_static_nodes_retained_in_some_component": int(group["component_node_count"].sum())
                == int(item.static_corridor_node_count),
                "plausible_explanation_component_count": int(item.plausible_explanation_component_count),
                "multi_frame_component_count": int(item.multi_frame_component_count),
                "isolated_component_count": int(item.isolated_component_count),
                "actual_pruned_component_count": 0,
                "actual_pruned_node_count": 0,
                "counterfactual_isolated_component_count": len(isolated),
                "counterfactual_isolated_node_count": int(isolated["component_node_count"].sum()),
                "counterfactual_multiframe_node_count": int(multi["component_node_count"].sum()),
                "likely_supported_component_count_post_reference": len(likely),
                "likely_supported_multiframe_component_count_post_reference": int(
                    likely["component_frame_count"].ge(2).sum()
                ),
                "likely_supported_isolated_component_count_post_reference": int(
                    likely["component_frame_count"].eq(1).sum()
                ),
                "current_potential_disambiguation_gt_blind": bool(item.potential_disambiguation_gt_blind),
                "recommended_pre_reference_term": "TEMPORAL_STRATIFICATION",
            }
        )
    return pd.DataFrame(rows)


def save_edge_distribution_figure(edges: pd.DataFrame, q: dict[str, float]) -> None:
    supported = edges[edges["p0_supported_continuation"]]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    axes[0, 0].hist(supported["soft_intersection_px"], bins=80, color="#4776e6")
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_title("Positive soft-overlap mass (log count)")
    axes[0, 0].axvline(q["soft_intersection_q01"], color="black", linestyle="--", label="1% descriptor")
    axes[0, 0].legend()
    axes[0, 1].hist(supported["soft_iou"], bins=80, color="#44a37a")
    axes[0, 1].set_title("Soft IoU")
    axes[0, 1].axvline(q["soft_iou_q01"], color="black", linestyle="--", label="1% descriptor")
    axes[0, 1].legend()
    family = supported["audit_edge_family"].value_counts()
    axes[1, 0].bar(family.index, family.values, color=["#e95d4f", "#6c8cd5", "#e0aa3e", "#5bbf75"][: len(family)])
    axes[1, 0].tick_params(axis="x", rotation=25)
    axes[1, 0].set_title("Audit-only evidence families (not mechanism classes)")
    sample = supported.sample(min(3702, len(supported)), random_state=29)
    for name, group in sample.groupby("audit_edge_family"):
        axes[1, 1].scatter(
            group["source_total_retention"], group["destination_explained_fraction"], s=10, alpha=0.45, label=name
        )
    axes[1, 1].set_xlabel("source retention")
    axes[1, 1].set_ylabel("destination explained")
    axes[1, 1].set_title("Directional evidence descriptors")
    axes[1, 1].legend(fontsize=7)
    fig.suptitle("TERG-v0 positive-edge evidence: descriptive audit, no threshold fitting")
    fig.tight_layout()
    fig.savefig(FIGURES / "edge_evidence_distribution.png", dpi=180)
    plt.close(fig)


def mask_for_region(cmr: Any, region_row: pd.Series, cache: dict[str, dict[str, np.ndarray]]) -> np.ndarray:
    uid = str(region_row.frame_uid)
    if uid not in cache:
        cache[uid] = dict(np.load(cmr.REGION_MASKS / f"{uid}.npz"))
    return cache[uid]["Q095"] == cmr.region_label(str(region_row.region_id))


def render_edge_detail(
    cmr: Any,
    cmr_data: dict[str, Any],
    edge: pd.Series,
    regions_by_id: pd.DataFrame,
    output: Path,
    subtitle: str,
) -> bool:
    source_row = regions_by_id.loc[str(edge.source_region_id)]
    destination_row = regions_by_id.loc[str(edge.destination_region_id)]
    cache: dict[str, dict[str, np.ndarray]] = {}
    source_mask = mask_for_region(cmr, source_row, cache)
    destination_mask = mask_for_region(cmr, destination_row, cache)
    model = cmr_data["models"].get((str(edge.run_id), int(edge.source_sar_frame), int(edge.destination_sar_frame)))
    if model is None:
        return False
    warped = cv2.warpAffine(
        source_mask.astype(np.float32),
        cmr.p0_matrix(model),
        (source_mask.shape[1], source_mask.shape[0]),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0.0,
    )
    source_path = cmr.sar_image_path(str(edge.run_id), int(edge.source_sar_frame))
    destination_path = cmr.sar_image_path(str(edge.run_id), int(edge.destination_sar_frame))
    source_img = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
    destination_img = cv2.imread(str(destination_path), cv2.IMREAD_COLOR)
    if source_img is None or destination_img is None:
        return False
    source_rgb = cv2.cvtColor(source_img, cv2.COLOR_BGR2RGB)
    destination_rgb = cv2.cvtColor(destination_img, cv2.COLOR_BGR2RGB)
    union = source_mask | destination_mask | (warped >= 0.05)
    yy, xx = np.nonzero(union)
    if len(xx):
        margin = 45
        x1, x2 = max(0, int(xx.min()) - margin), min(union.shape[1], int(xx.max()) + margin + 1)
        y1, y2 = max(0, int(yy.min()) - margin), min(union.shape[0], int(yy.max()) + margin + 1)
    else:
        x1, x2, y1, y2 = 0, union.shape[1], 0, union.shape[0]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    axes[0].imshow(source_rgb)
    axes[0].contour(source_mask.astype(float), levels=[0.5], colors=["cyan"], linewidths=2)
    axes[0].set_title(f"source SAR F{int(edge.source_sar_frame)} / q95")
    axes[1].imshow(warped, cmap="magma", vmin=0, vmax=1)
    axes[1].contour(destination_mask.astype(float), levels=[0.5], colors=["lime"], linewidths=1.4)
    axes[1].set_title("P0 warped source; lime=destination q95")
    axes[2].imshow(destination_rgb)
    axes[2].contour(destination_mask.astype(float), levels=[0.5], colors=["yellow"], linewidths=2)
    axes[2].contour((warped >= 0.5).astype(float), levels=[0.5], colors=["red"], linewidths=1.2)
    axes[2].set_title(f"destination SAR F{int(edge.destination_sar_frame)}")
    for axis in axes:
        axis.set_xlim(x1, x2)
        axis.set_ylim(y2, y1)
        axis.axis("off")
    fig.suptitle(
        f"{subtitle}\n{edge.graph_edge_id} | soft mass={edge.soft_intersection_px:.3f} | "
        f"ret={edge.source_total_retention:.3f} | expl={edge.destination_explained_fraction:.3f} | "
        f"IoU={edge.soft_iou:.3f} | {edge.audit_edge_family}"
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return True


def render_exact_one_edges(
    cmr: Any,
    cmr_data: dict[str, Any],
    edges: pd.DataFrame,
    regions_by_id: pd.DataFrame,
) -> pd.DataFrame:
    selected = edges[
        edges["p0_supported_continuation"].astype(bool) & edges["exact_one_soft_pixel_mass"].astype(bool)
    ].sort_values(["source_sar_frame", "track_id", "graph_edge_id"])
    rows: list[dict[str, Any]] = []
    for index, edge in enumerate(selected.itertuples(index=False), start=1):
        output = EXACT_ONE_FIGURES / f"{index:02d}_{edge.graph_edge_id}.png"
        ok = render_edge_detail(
            cmr,
            cmr_data,
            pd.Series(edge._asdict()),
            regions_by_id,
            output,
            "EXACT 1.0 fractional bilinear-overlap mass; descriptive audit only",
        )
        rows.append(
            {
                "case_index": index,
                "status": "RENDERED" if ok else "IMAGE_UNAVAILABLE",
                "graph_edge_id": edge.graph_edge_id,
                "run_id": edge.run_id,
                "track_id": edge.track_id,
                "source_sar_frame": int(edge.source_sar_frame),
                "destination_sar_frame": int(edge.destination_sar_frame),
                "source_region_id": edge.source_region_id,
                "destination_region_id": edge.destination_region_id,
                "soft_intersection_px": float(edge.soft_intersection_px),
                "source_total_retention": float(edge.source_total_retention),
                "destination_explained_fraction": float(edge.destination_explained_fraction),
                "soft_iou": float(edge.soft_iou),
                "detail_pack": str(output),
            }
        )
    return pd.DataFrame(rows)


def render_relation_case(
    cmr: Any,
    cmr_data: dict[str, Any],
    data: dict[str, pd.DataFrame],
    profile: pd.Series,
    output: Path,
    case_name: str,
) -> dict[str, Any]:
    segments = data["segments"].set_index("segment_id")
    segment = segments.loc[str(profile.segment_id)]
    frames = list(range(int(segment.start_sar_frame), int(segment.end_sar_frame) + 1))
    track_a = str(profile.track_a)
    track_b = str(profile.track_b)
    nodes = data["nodes"]
    memberships = data["memberships"]
    components = data["components"]

    bounds = nodes[["track_node_id", "theta_min_deg", "theta_max_deg"]].drop_duplicates("track_node_id")
    member = memberships[
        memberships["segment_id"].eq(profile.segment_id)
        & memberships["track_id"].astype(str).isin([track_a, track_b])
    ].merge(bounds, on="track_node_id", how="left", validate="many_to_one")
    component_frames: dict[str, dict[int, tuple[set[str], float, float]]] = {}
    for component_id, group in member.groupby("explanation_component_id"):
        payload: dict[int, tuple[set[str], float, float]] = {}
        for frame, rows in group.groupby("frame_index"):
            payload[int(frame)] = (
                set(rows["region_id"].astype(str)),
                float(rows["theta_min_deg"].min()),
                float(rows["theta_max_deg"].max()),
            )
        component_frames[str(component_id)] = payload
    component_ids = components[
        components["segment_id"].eq(profile.segment_id)
        & components["track_id"].astype(str).isin([track_a, track_b])
    ].groupby("track_id")["explanation_component_id"].agg(list).to_dict()
    relation_by_frame: dict[int, Counter[str]] = {frame: Counter() for frame in frames}
    for comp_a in component_ids.get(track_a, []):
        fa = component_frames[str(comp_a)]
        for comp_b in component_ids.get(track_b, []):
            fb = component_frames[str(comp_b)]
            for frame in sorted(set(fa) & set(fb)):
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
                relation_by_frame[int(frame)][relation] += 1

    case_nodes = nodes[
        nodes["run_id"].eq(profile.run_id)
        & nodes["track_id"].astype(str).isin([track_a, track_b])
        & nodes["frame_index"].isin(frames)
    ]
    region_rows = cmr_data["regions"].set_index("region_id", drop=False)
    cache: dict[str, dict[str, np.ndarray]] = {}
    fig = plt.figure(figsize=(max(13, len(frames) * 3.0), 7.6))
    grid = fig.add_gridspec(2, len(frames), height_ratios=[2.15, 1.25])
    shared_counts: list[int] = []
    for column, frame in enumerate(frames):
        axis = fig.add_subplot(grid[0, column])
        image_path = cmr.sar_image_path(str(profile.run_id), frame)
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            axis.set_title(f"F{frame} unavailable")
            axis.axis("off")
            shared_counts.append(0)
            continue
        axis.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        frame_nodes = case_nodes[case_nodes["frame_index"].eq(frame)]
        regions_a = set(frame_nodes[frame_nodes["track_id"].astype(str).eq(track_a)]["region_id"].astype(str))
        regions_b = set(frame_nodes[frame_nodes["track_id"].astype(str).eq(track_b)]["region_id"].astype(str))
        shared = regions_a & regions_b
        shared_counts.append(len(shared))
        for region_id in sorted(regions_a | regions_b):
            if region_id not in region_rows.index:
                continue
            mask = mask_for_region(cmr, region_rows.loc[region_id], cache)
            if region_id in shared:
                color, width = "magenta", 1.8
            elif region_id in regions_a:
                color, width = "cyan", 0.9
            else:
                color, width = "orange", 0.9
            axis.contour(mask.astype(float), levels=[0.5], colors=[color], linewidths=width)
        axis.set_title(f"{profile.run_id} F{frame}\nphysical shared={len(shared)}", fontsize=8)
        axis.axis("off")

    relation_axis = fig.add_subplot(grid[1, :])
    order = ["LEFT", "RIGHT", "OVERLAP", "SHARED"]
    colors = {"LEFT": "#2f78c4", "RIGHT": "#e58b2a", "OVERLAP": "#8a63b8", "SHARED": "#d936a6"}
    values = np.array([[relation_by_frame[frame][key] for frame in frames] for key in order], dtype=float)
    totals = values.sum(axis=0)
    fractions = np.divide(values, totals, out=np.zeros_like(values), where=totals > 0) * 100.0
    bottom = np.zeros(len(frames), dtype=float)
    for index, key in enumerate(order):
        relation_axis.bar(frames, fractions[index], bottom=bottom, color=colors[key], label=key, width=0.82)
        bottom += fractions[index]
    relation_axis.set_ylim(0, 100)
    relation_axis.set_ylabel("component-pair/frame relation support (%)")
    relation_axis.set_xlabel("SAR frame (nominal grid; synchronization uncalibrated)")
    relation_axis.set_xticks(frames)
    relation_axis.legend(ncol=4, loc="upper left", fontsize=8)
    shared_axis = relation_axis.twinx()
    shared_axis.plot(frames, shared_counts, color="black", marker="o", linewidth=1.2, label="physical shared regions")
    shared_axis.set_ylabel("unique physical shared q95 regions")
    shared_axis.set_ylim(0, max(1, max(shared_counts)) * 1.35)
    shared_axis.legend(loc="upper right", fontsize=8)
    fig.suptitle(
        f"{case_name}: current={profile.current_relative_order_compatibility}; "
        f"possible={profile.possible_relation_set}\n"
        f"cyan/orange are track-conditioned incidence; magenta is one physical region admitted by both corridors"
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return {
        "case_name": case_name,
        "order_profile_id": str(profile.order_profile_id),
        "segment_id": str(profile.segment_id),
        "run_id": str(profile.run_id),
        "track_a": track_a,
        "track_b": track_b,
        "frame_count": len(frames),
        "current_relative_order_compatibility": str(profile.current_relative_order_compatibility),
        "possible_relation_set": str(profile.possible_relation_set),
        "frames_with_physical_sharing": int(sum(value > 0 for value in shared_counts)),
        "maximum_shared_physical_regions_in_one_frame": int(max(shared_counts, default=0)),
        "detail_pack": str(output),
    }


def render_relation_cases(
    cmr: Any,
    cmr_data: dict[str, Any],
    data: dict[str, pd.DataFrame],
    relation: pd.DataFrame,
) -> pd.DataFrame:
    selections = [
        ("partial_direction_with_local_shared", "TERGOP_502E22A20AD671392149"),
        ("competing_directions_with_shared", "TERGOP_722FF98E6AE0A93EBAC5"),
    ]
    rows: list[dict[str, Any]] = []
    for index, (case_name, profile_id) in enumerate(selections, start=1):
        candidates = relation[relation["order_profile_id"].eq(profile_id)]
        if candidates.empty:
            rows.append({"case_name": case_name, "order_profile_id": profile_id, "status": "PROFILE_NOT_FOUND"})
            continue
        profile = candidates.iloc[0]
        output = RELATION_FIGURES / f"{index:02d}_{case_name}_{profile_id}.png"
        row = render_relation_case(cmr, cmr_data, data, profile, output, case_name)
        row["status"] = "RENDERED"
        rows.append(row)
    return pd.DataFrame(rows)


def render_bridge_cases(
    cmr: Any,
    cmr_data: dict[str, Any],
    edges: pd.DataFrame,
    bridges: pd.DataFrame,
    regions_by_id: pd.DataFrame,
) -> pd.DataFrame:
    if bridges.empty:
        return pd.DataFrame()
    ranked = bridges.copy()
    ranked["priority"] = (
        ranked["exact_one_soft_pixel_mass"].astype(int) * 100000
        + ranked["audit_edge_family"].eq("WEAK_CONTINUATION").astype(int) * 10000
        + ranked["small_side_frame_count"] * 100
        - ranked["soft_iou"]
    )
    selected = ranked.sort_values(["priority", "soft_iou"], ascending=[False, True]).drop_duplicates("graph_edge_id").head(10)
    edge_lookup = edges.set_index("graph_edge_id", drop=False)
    rows: list[dict[str, Any]] = []
    for index, bridge in enumerate(selected.itertuples(index=False), start=1):
        edge = edge_lookup.loc[str(bridge.graph_edge_id)]
        output = BRIDGE_FIGURES / f"{index:02d}_{bridge.graph_edge_id}.png"
        ok = render_edge_detail(
            cmr,
            cmr_data,
            edge,
            regions_by_id,
            output,
            f"BRIDGE_CRITICAL: split {bridge.small_side_frame_count}/{bridge.large_side_frame_count} frame supports",
        )
        if ok:
            rows.append(
                {
                    **bridge._asdict(),
                    "source_sar_image": str(cmr.sar_image_path(str(edge.run_id), int(edge.source_sar_frame))),
                    "destination_sar_image": str(cmr.sar_image_path(str(edge.run_id), int(edge.destination_sar_frame))),
                    "detail_pack": str(output),
                }
            )
    return pd.DataFrame(rows)


def render_topology_cases(
    cmr: Any,
    cmr_data: dict[str, Any],
    edges: pd.DataFrame,
    regions_by_id: pd.DataFrame,
    q: dict[str, float],
) -> pd.DataFrame:
    supported = edges[edges["p0_supported_continuation"]].copy()
    selectors: list[tuple[str, pd.DataFrame, str]] = [
        (
            "clear_split_high_iou",
            supported[supported["sar_topology_state"].eq("P0_SPLIT_LIKE")].sort_values("soft_iou", ascending=False),
            "Clear split-like candidate (high soft IoU)",
        ),
        (
            "clear_merge_high_iou",
            supported[supported["sar_topology_state"].eq("P0_MERGE_LIKE")].sort_values("soft_iou", ascending=False),
            "Clear merge-like candidate (high soft IoU)",
        ),
        (
            "deformation_with_topology",
            supported[
                supported["sar_topology_state"].str.contains("SPLIT|MERGE")
                & supported["sar_p0_residual_state"].str.contains("DEFORMATION")
            ].sort_values("soft_iou", ascending=False),
            "Topology label coexists with deformation",
        ),
        (
            "weak_edge_topology",
            supported[
                supported["sar_topology_state"].str.contains("SPLIT|MERGE")
                & supported["soft_iou"].le(q["soft_iou_q05"])
            ].sort_values("soft_iou"),
            "Weak-evidence split/merge topology",
        ),
        (
            "boundary_topology",
            supported[
                supported["sar_topology_state"].str.contains("SPLIT|MERGE")
                & (
                    supported["source_touches_boundary"].astype(bool)
                    | supported["destination_touches_boundary"].astype(bool)
                    | supported["source_truncated"].astype(bool)
                    | supported["destination_truncated"].astype(bool)
                )
            ],
            "Boundary/censoring topology case",
        ),
        (
            "lowest_iou_supported",
            supported.sort_values("soft_iou"),
            "Lowest-IoU supported continuation (fragmentation probe)",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for index, (name, candidates, subtitle) in enumerate(selectors, start=1):
        if candidates.empty:
            rows.append({"case_name": name, "status": "CATEGORY_NOT_OBSERVED"})
            continue
        edge = candidates.iloc[0]
        output = TOPOLOGY_FIGURES / f"{index:02d}_{name}_{edge.graph_edge_id}.png"
        ok = render_edge_detail(cmr, cmr_data, edge, regions_by_id, output, subtitle)
        rows.append(
            {
                "case_name": name,
                "status": "RENDERED" if ok else "IMAGE_UNAVAILABLE",
                "graph_edge_id": edge.graph_edge_id,
                "run_id": edge.run_id,
                "source_sar_frame": int(edge.source_sar_frame),
                "destination_sar_frame": int(edge.destination_sar_frame),
                "sar_topology_state": edge.sar_topology_state,
                "sar_p0_residual_state": edge.sar_p0_residual_state,
                "soft_intersection_px": float(edge.soft_intersection_px),
                "soft_iou": float(edge.soft_iou),
                "detail_pack": str(output),
            }
        )
    return pd.DataFrame(rows)


def render_focus_segment(
    cmr: Any,
    data: dict[str, pd.DataFrame],
    edges: pd.DataFrame,
    bridges: pd.DataFrame,
) -> dict[str, Any]:
    segment_id = "TERGS_E766DA8C46F860D1BA2F"
    selected_id = "TERGXC_1FD4CF2856175478AA05"
    partial_id = "TERGXC_A97D2FC78FCD287ADEEE"
    components = data["components"]
    memberships = data["memberships"]
    nodes = data["nodes"]
    segment_components = components[components["segment_id"].eq(segment_id)].copy()
    selected_meta = segment_components[segment_components["explanation_component_id"].eq(selected_id)].iloc[0]
    track_id = str(selected_meta.track_id)
    alternatives = segment_components[
        segment_components["track_id"].astype(str).eq(track_id)
        & ~segment_components["explanation_component_id"].isin([selected_id, partial_id])
    ]
    strongest_competitor = alternatives[alternatives["component_frame_count"].ge(2)].sort_values(
        ["component_frame_count", "component_node_count"], ascending=False
    ).iloc[0]
    node_pixels = nodes.set_index("track_node_id")["pixel_count"].to_dict()
    isolated = alternatives[alternatives["component_frame_count"].eq(1)].copy()
    isolated["max_pixel_count"] = isolated["explanation_component_id"].map(
        memberships.groupby("explanation_component_id")["track_node_id"].agg(
            lambda values: max(float(node_pixels.get(v, 0)) for v in values)
        )
    )
    isolated_choice = isolated.sort_values("max_pixel_count", ascending=False).iloc[0]
    focus_bridges = bridges[
        bridges["segment_id"].eq(segment_id) & bridges["track_id"].astype(str).eq(track_id)
    ].sort_values(["small_side_frame_count", "soft_iou"], ascending=[False, True])
    weak_bridge_component = (
        str(focus_bridges.iloc[0].explanation_component_id) if len(focus_bridges) else str(strongest_competitor.explanation_component_id)
    )
    component_style = {
        selected_id: ("selected complete", "red", 2.2),
        partial_id: ("partial F0-F4", "cyan", 1.8),
        str(strongest_competitor.explanation_component_id): ("strongest competing multi-frame", "orange", 1.6),
        str(isolated_choice.explanation_component_id): ("isolated alternative", "lime", 1.6),
        weak_bridge_component: ("bridge-critical alternative", "violet", 1.6),
    }
    component_members = {
        component_id: memberships[memberships["explanation_component_id"].eq(component_id)]
        for component_id in component_style
    }
    region_rows = nodes.drop_duplicates("region_id").set_index("region_id", drop=False)
    cache: dict[str, dict[str, np.ndarray]] = {}
    reference = data["reference"]

    fig, axes = plt.subplots(4, 4, figsize=(20, 13))
    for frame, axis in enumerate(axes.flat):
        image_path = cmr.sar_image_path("R01ZF", frame)
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            axis.set_title(f"F{frame} unavailable")
            axis.axis("off")
            continue
        axis.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        for component_id, (label, color, width) in component_style.items():
            member = component_members[component_id]
            frame_rows = member[member["frame_index"].eq(frame)]
            for region_id in frame_rows["region_id"].astype(str):
                mask = mask_for_region(cmr, region_rows.loc[region_id], cache)
                axis.contour(mask.astype(float), levels=[0.5], colors=[color], linewidths=width)
        frame_reference = reference[
            reference["run_id"].eq("R01ZF")
            & reference["frame_index"].eq(frame)
            & reference["percentile_tag"].eq("Q095")
        ]
        for region_id in frame_reference["nearest_region_id"].dropna().astype(str).unique():
            if region_id in region_rows.index:
                mask = mask_for_region(cmr, region_rows.loc[region_id], cache)
                axis.contour(mask.astype(float), levels=[0.5], colors=["magenta"], linewidths=1.1, linestyles="--")
        axis.set_title(f"R01ZF F{frame}", fontsize=9)
        axis.axis("off")
    handles = [plt.Line2D([0], [0], color=color, lw=width, label=label) for label, color, width in component_style.values()]
    handles.append(plt.Line2D([0], [0], color="magenta", lw=1.2, ls="--", label="offline reference region"))
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=9)
    fig.suptitle("R01ZF F0-F15: all intermediate SAR frames and competing TERG explanations")
    fig.tight_layout(rect=(0, 0.055, 1, 0.96))
    focus_path = FIGURES / "r01zf_f0_f15_all_intermediate_competing_components.png"
    fig.savefig(focus_path, dpi=180)
    plt.close(fig)

    segment = data["segments"].set_index("segment_id").loc[segment_id]
    seg_nodes = nodes[
        nodes["run_id"].eq(segment.run_id)
        & nodes["frame_index"].between(segment.start_sar_frame, segment.end_sar_frame)
        & nodes["track_id"].astype(str).isin(str(segment.track_ids).split(";"))
    ]
    seg_edges = edges[
        edges["p0_supported_continuation"]
        & edges["run_id"].eq(segment.run_id)
        & edges["source_sar_frame"].between(segment.start_sar_frame, segment.end_sar_frame - 1)
        & edges["track_id"].astype(str).isin(str(segment.track_ids).split(";"))
    ]
    key_to_theta = {
        (str(r.track_id), int(r.frame_index), str(r.region_id)): float(r.theta_mid_deg)
        for r in seg_nodes.itertuples(index=False)
    }
    colors = {
        "CORE_CONTINUATION": "#2585d9",
        "WEAK_CONTINUATION": "#e6a21a",
        "UNCERTAIN_CONTINUATION": "#8c8c8c",
        "DEFORMATION_LINK": "#d84b4b",
    }
    fig, axis = plt.subplots(figsize=(16, 8))
    for row in seg_edges.itertuples(index=False):
        source = key_to_theta.get((str(row.track_id), int(row.source_sar_frame), str(row.source_region_id)))
        destination = key_to_theta.get((str(row.track_id), int(row.destination_sar_frame), str(row.destination_region_id)))
        if source is None or destination is None:
            continue
        axis.plot(
            [row.source_sar_frame, row.destination_sar_frame],
            [source, destination],
            color=colors.get(str(row.audit_edge_family), "gray"),
            alpha=0.55,
            linewidth=1.1,
        )
    axis.scatter(seg_nodes["frame_index"], seg_nodes["theta_mid_deg"], s=16, color="black", alpha=0.55)
    membership = memberships[memberships["segment_id"].eq(segment_id)]
    for component_id, (label, color, width) in component_style.items():
        part = membership[membership["explanation_component_id"].eq(component_id)].sort_values("frame_index")
        axis.plot(part["frame_index"], part["theta_mid_deg"], color=color, lw=width, marker="o", ms=3, label=label)
    focus_bridge_ids = set(focus_bridges["graph_edge_id"].astype(str))
    for row in seg_edges[seg_edges["graph_edge_id"].astype(str).isin(focus_bridge_ids)].itertuples(index=False):
        source = key_to_theta.get((str(row.track_id), int(row.source_sar_frame), str(row.source_region_id)))
        destination = key_to_theta.get((str(row.track_id), int(row.destination_sar_frame), str(row.destination_region_id)))
        if source is not None and destination is not None:
            axis.scatter(
                [(row.source_sar_frame + row.destination_sar_frame) / 2],
                [(source + destination) / 2],
                marker="*",
                s=130,
                color="black",
                zorder=8,
            )
    axis.set_xlabel("SAR frame (nominal grid; synchronization uncalibrated)")
    axis.set_ylabel("azimuth theta (deg)")
    axis.set_title("Edge-critical temporal graph: audit-only evidence families; stars are bridges")
    axis.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    graph_path = FIGURES / "r01zf_f0_f15_edge_critical_temporal_graph.png"
    fig.savefig(graph_path, dpi=190)
    plt.close(fig)
    return {
        "segment_id": segment_id,
        "track_id": track_id,
        "selected_complete_component": selected_id,
        "partial_component": partial_id,
        "strongest_competing_multiframe_component": str(strongest_competitor.explanation_component_id),
        "isolated_alternative_component": str(isolated_choice.explanation_component_id),
        "weak_bridge_alternative_component": weak_bridge_component,
        "all_intermediate_pack": str(focus_path),
        "edge_critical_graph": str(graph_path),
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    BRIDGE_FIGURES.mkdir(parents=True, exist_ok=True)
    TOPOLOGY_FIGURES.mkdir(parents=True, exist_ok=True)
    EXACT_ONE_FIGURES.mkdir(parents=True, exist_ok=True)
    RELATION_FIGURES.mkdir(parents=True, exist_ok=True)

    data = load_tables()
    cmr = load_cmr()
    cmr_data = cmr.load_authorities()
    edges, q = add_edge_descriptors(data["edges"])
    data["edges"] = edges
    node_key, node_frame = endpoint_node_maps(data["nodes"])

    physical, physical_summary = physical_node_audit(data["nodes"])
    bridges = bridge_audit(edges, data["memberships"], data["components"], node_key, node_frame)
    sensitivity = connectivity_sensitivity(data["sets"], data["segments"], data["nodes"], edges, node_key, q)
    topology = topology_sensitivity(edges, q)
    relation = relation_set_audit(data["order"], data["components"], data["memberships"], data["nodes"])
    contraction = contraction_audit(data["sets"], data["components"], data["component_grounding"])

    edge_columns = [
        "graph_edge_id",
        "run_id",
        "track_id",
        "source_sar_frame",
        "destination_sar_frame",
        "source_region_id",
        "destination_region_id",
        "soft_intersection_px",
        "source_total_retention",
        "destination_explained_fraction",
        "soft_iou",
        "sar_p0_residual_state",
        "sar_topology_state",
        "p0_supported_continuation",
        "mutual_local_dominant",
        "outgoing_relative_strength",
        "incoming_relative_strength",
        "audit_edge_family",
        "exact_one_soft_pixel_mass",
    ]
    edges[edge_columns].to_parquet(TABLES / "edge_evidence_descriptors.parquet", index=False, compression="zstd")
    edges[edge_columns].to_csv(TABLES / "edge_evidence_descriptors.csv", index=False, encoding="utf-8-sig")
    physical.to_csv(TABLES / "physical_region_vs_conditioned_node_audit.csv", index=False, encoding="utf-8-sig")
    bridges.to_csv(TABLES / "bridge_criticality.csv", index=False, encoding="utf-8-sig")
    sensitivity.to_csv(TABLES / "connectivity_sensitivity.csv", index=False, encoding="utf-8-sig")
    topology.to_csv(TABLES / "topology_sensitivity.csv", index=False, encoding="utf-8-sig")
    relation.to_csv(TABLES / "possible_relation_set_audit.csv", index=False, encoding="utf-8-sig")
    contraction.to_csv(TABLES / "temporal_stratification_contraction_audit.csv", index=False, encoding="utf-8-sig")

    save_edge_distribution_figure(edges, q)
    regions_by_id = cmr_data["regions"].set_index("region_id", drop=False)
    bridge_registry = render_bridge_cases(cmr, cmr_data, edges, bridges, regions_by_id)
    topology_registry = render_topology_cases(cmr, cmr_data, edges, regions_by_id, q)
    exact_one_registry = render_exact_one_edges(cmr, cmr_data, edges, regions_by_id)
    relation_registry = render_relation_cases(cmr, cmr_data, data, relation)
    focus = render_focus_segment(cmr, data, edges, bridges)
    bridge_registry.to_csv(TABLES / "bridge_critical_edge_case_registry.csv", index=False, encoding="utf-8-sig")
    topology_registry.to_csv(TABLES / "topology_stratified_case_registry.csv", index=False, encoding="utf-8-sig")
    exact_one_registry.to_csv(TABLES / "exact_one_soft_overlap_edge_registry.csv", index=False, encoding="utf-8-sig")
    relation_registry.to_csv(TABLES / "relation_set_case_registry.csv", index=False, encoding="utf-8-sig")

    supported = edges[edges["p0_supported_continuation"]]
    shared_relation = relation[
        relation["current_relative_order_compatibility"].eq("SHARED_RESPONSE_ORDER_UNDEFINED")
    ]
    sensitivity_aggregate = (
        sensitivity.groupby("variant", as_index=False)
        .agg(
            explanation_set_rows=("segment_id", "size"),
            total_component_count=("component_count", "sum"),
            total_multi_frame_component_count=("multi_frame_component_count", "sum"),
            total_isolated_component_count=("isolated_component_count", "sum"),
            total_full_frame_coverage_component_count=("full_frame_coverage_component_count", "sum"),
            median_largest_component_frame_count=("largest_component_frame_count", "median"),
            maximum_largest_component_frame_count=("largest_component_frame_count", "max"),
        )
    )
    sensitivity_aggregate.to_csv(TABLES / "connectivity_sensitivity_aggregate.csv", index=False, encoding="utf-8-sig")

    summary = {
        "schema": "PERSON_TERG_V0_VISUAL_SEMANTIC_REALITY_CHECK_DIAGNOSTIC_SUMMARY_V1",
        "phase": "PHASE_A_READ_ONLY_DIAGNOSIS",
        "mechanism_modified": False,
        "confirmation_run_accessed": False,
        "edge_support_semantics": {
            "supported_edge_count": int(len(supported)),
            "exact_one_soft_pixel_mass_edge_count": int(supported["exact_one_soft_pixel_mass"].sum()),
            "soft_overlap_is_fractional_bilinear_mass_not_integer_pixel_count": True,
            "quantiles": q,
            "audit_edge_family_counts": supported["audit_edge_family"].value_counts().to_dict(),
        },
        "physical_node_semantics": physical_summary,
        "bridge_criticality": {
            "bridge_instance_count_across_segment_components": int(len(bridges)),
            "unique_bridge_edge_count": int(bridges["graph_edge_id"].nunique()) if len(bridges) else 0,
            "exact_one_soft_pixel_bridge_instance_count": int(bridges["exact_one_soft_pixel_mass"].sum()) if len(bridges) else 0,
            "weak_family_bridge_instance_count": int(bridges["audit_edge_family"].eq("WEAK_CONTINUATION").sum()) if len(bridges) else 0,
            "maximum_small_side_frame_count": int(bridges["small_side_frame_count"].max()) if len(bridges) else 0,
        },
        "relation_set": {
            "current_shared_order_undefined_profiles": int(len(shared_relation)),
            "shared_profile_relation_set_classification_counts": shared_relation[
                "relation_set_classification"
            ].value_counts().to_dict(),
            "all_profile_relation_set_classification_counts": relation[
                "relation_set_classification"
            ].value_counts().to_dict(),
        },
        "contraction_semantics": {
            "explanation_set_rows": int(len(contraction)),
            "all_static_nodes_retained_in_some_component_rows": int(
                contraction["all_static_nodes_retained_in_some_component"].sum()
            ),
            "actual_pruned_component_count": 0,
            "actual_pruned_node_count": 0,
            "temporal_stratification_rows": int(contraction["current_potential_disambiguation_gt_blind"].sum()),
            "post_reference_rows_with_exactly_one_likely_component": int(
                contraction["likely_supported_component_count_post_reference"].eq(1).sum()
            ),
        },
        "timing_provenance": {
            "value_ms": 250,
            "first_tracked_person_p1e_constant_commit": "edd7c1ba91577f18fa54877f82ee92eb779aab33",
            "provenance_class": "UNVERIFIED_TIMING_MARGIN",
            "measured_synchronization_uncertainty": False,
            "known_offset_distribution": False,
            "terg_implementation_uses_value_in_interval_relation": False,
            "terg_implementation_records_descriptor_only": True,
        },
        "focus_segment": focus,
        "exact_one_edge_cases": exact_one_registry.to_dict(orient="records"),
        "relation_set_cases": relation_registry.to_dict(orient="records"),
        "output_tables": [str(path) for path in sorted(TABLES.glob("*"))],
        "output_figures": [str(path) for path in sorted(FIGURES.rglob("*.png"))],
    }
    write_json(OUTPUT / "diagnostic_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
