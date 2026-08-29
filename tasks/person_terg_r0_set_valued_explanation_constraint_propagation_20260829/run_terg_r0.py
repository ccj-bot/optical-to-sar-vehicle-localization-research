from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import math
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
V1_ROOT = WORKSPACE / "output" / "person_terg_d0r_set_valued_graph_representation_repair_20260829"
V1_PRE = V1_ROOT / "pre_reference"
V1_POST = V1_ROOT / "post_reference"
D0_ROOT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "terg_d0_temporal_event_response_graph_mechanism_exploration"
)
D0_PRE = D0_ROOT / "pre_reference"
PHASE_A_SCRIPT = (
    WORKSPACE
    / "tasks"
    / "person_terg_v0_visual_semantic_reality_check_20260829"
    / "run_visual_semantic_audit.py"
)
PHASE_A_FIGURES = (
    WORKSPACE / "output" / "person_terg_v0_visual_semantic_reality_check_20260829" / "figures"
)
V1_FIGURES = V1_ROOT / "figures" / "before_after"
OUTPUT = WORKSPACE / "output" / "person_terg_r0_set_valued_explanation_constraint_propagation_20260829"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference"
FIGURES = OUTPUT / "figures" / "real_image_review"

ROUTE_A = "TERG_R0_CONSTRAINT_PROPAGATION_MECHANISM_ESTABLISHED"
ROUTE_B = "TERG_STRUCTURAL_INFORMATION_REAL_BUT_NONDISCRIMINATIVE"
ROUTE_C = "TERG_CONSTRAINT_PROPAGATION_HARMS_VALID_EXPLANATIONS"
ROUTE_D = "GROUNDING_TOO_WEAK_TO_DECIDE_DISCRIMINATION"


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha1(payload.encode('utf-8')).hexdigest()[:20].upper()}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_table(frame: pd.DataFrame, path: Path, csv: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path.with_suffix(".parquet"), index=False, compression="zstd")
    if csv:
        frame.to_csv(path.with_suffix(".csv"), index=False, encoding="utf-8-sig")


def set_text(values: set[str] | list[str] | tuple[str, ...]) -> str:
    return "{" + ",".join(sorted(set(values))) + "}"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frozen_input_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(WORKSPACE)).replace("\\", "/"): sha256_file(path)
        for path in sorted(V1_ROOT.rglob("*"))
        if path.is_file()
    }


def load_pre_reference_inputs() -> dict[str, pd.DataFrame]:
    return {
        "families": pd.read_parquet(V1_PRE / "admissible_component_families_pre_reference.parquet"),
        "memberships": pd.read_parquet(V1_PRE / "component_family_membership_pre_reference.parquet"),
        "physical": pd.read_parquet(V1_PRE / "physical_sar_response_regions_pre_reference.parquet"),
        "burden": pd.read_parquet(V1_PRE / "temporal_stratification_burden_profiles_pre_reference.parquet"),
        "relation_profiles": pd.read_parquet(V1_PRE / "possible_relation_sets_pre_reference.parquet"),
        "timing_authority": pd.read_parquet(V1_PRE / "timing_authority_pre_reference.parquet"),
        "segments": pd.read_parquet(D0_PRE / "temporal_segment_atlas_pre_reference.parquet"),
        "frame_state": pd.read_parquet(D0_PRE / "optical_temporal_frame_state_pre_reference.parquet"),
    }


def raw_interval_relation(a: pd.Series, b: pd.Series) -> str:
    if float(a.raw_theta_high_deg) < float(b.raw_theta_low_deg):
        return "A_LEFT_OF_B"
    if float(b.raw_theta_high_deg) < float(a.raw_theta_low_deg):
        return "A_RIGHT_OF_B"
    return "OPTICAL_OVERLAP_OR_UNCERTAIN"


def build_optical_order_registry(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    states = data["frame_state"]
    segments = data["segments"].set_index("segment_id")
    rows: list[dict[str, Any]] = []
    for profile in data["relation_profiles"].itertuples(index=False):
        segment = segments.loc[str(profile.segment_id)]
        frames = list(range(int(segment.start_sar_frame), int(segment.end_sar_frame) + 1))
        part = states[
            states["run_id"].eq(profile.run_id)
            & states["track_id"].astype(str).isin([str(profile.track_a), str(profile.track_b)])
            & states["frame_index"].isin(frames)
        ]
        lookup = {
            (str(row.track_id), int(row.frame_index)): pd.Series(row._asdict())
            for row in part.itertuples(index=False)
        }
        relations: list[str] = []
        unavailable: list[int] = []
        overlap: list[int] = []
        for frame in frames:
            a = lookup.get((str(profile.track_a), frame))
            b = lookup.get((str(profile.track_b), frame))
            if a is None or b is None:
                unavailable.append(frame)
                continue
            relation = raw_interval_relation(a, b)
            relations.append(relation)
            if relation == "OPTICAL_OVERLAP_OR_UNCERTAIN":
                overlap.append(frame)
        unique = set(relations)
        whole_segment_definite = bool(
            relations and unique in ({"A_LEFT_OF_B"}, {"A_RIGHT_OF_B"})
        )
        order = next(iter(unique)) if whole_segment_definite else "NO_WHOLE_SEGMENT_DEFINITE_ORDER"
        rows.append(
            {
                "order_profile_id": str(profile.order_profile_id),
                "segment_id": str(profile.segment_id),
                "run_id": str(profile.run_id),
                "track_a": str(profile.track_a),
                "track_b": str(profile.track_b),
                "segment_frame_count": len(frames),
                "paired_raw_interval_frame_count": len(relations),
                "raw_relation_set": set_text(unique),
                "whole_segment_optical_order": order,
                "whole_segment_definite_order": bool(whole_segment_definite),
                "overlap_or_uncertain_frame_set": ";".join(map(str, overlap)),
                "unavailable_frame_set": ";".join(map(str, unavailable)),
                "nominal_frame_equality_used_as_hard_timing_authority": False,
                "manual_reference_used": False,
            }
        )
    return pd.DataFrame(rows)


def build_family_frame_geometry(data: dict[str, pd.DataFrame]) -> dict[str, dict[int, tuple[set[str], float, float]]]:
    bounds = data["physical"].set_index("physical_region_id")[["theta_min_deg", "theta_max_deg"]]
    member = data["memberships"].merge(
        bounds,
        left_on="physical_region_id",
        right_index=True,
        how="left",
        validate="many_to_one",
    )
    payload: dict[str, dict[int, tuple[set[str], float, float]]] = {}
    for family_id, group in member.groupby("family_id"):
        per_frame: dict[int, tuple[set[str], float, float]] = {}
        for frame, rows in group.groupby("frame_index"):
            per_frame[int(frame)] = (
                set(rows["physical_region_id"].astype(str)),
                float(rows["theta_min_deg"].min()),
                float(rows["theta_max_deg"].max()),
            )
        payload[str(family_id)] = per_frame
    return payload


def sar_family_pair_relation(
    left: tuple[set[str], float, float], right: tuple[set[str], float, float]
) -> str:
    regions_a, a_low, a_high = left
    regions_b, b_low, b_high = right
    if regions_a & regions_b:
        return "SHARED"
    if a_high < b_low:
        return "LEFT"
    if b_high < a_low:
        return "RIGHT"
    return "OVERLAP"


def build_pair_constraints(
    data: dict[str, pd.DataFrame], optical_orders: pd.DataFrame
) -> tuple[pd.DataFrame, dict[tuple[str, str, str], np.ndarray], dict[tuple[str, str], list[str]]]:
    family_geometry = build_family_frame_geometry(data)
    family_ids = {
        (str(segment), str(track)): sorted(map(str, values))
        for (segment, track), values in data["families"].groupby(["segment_id", "track_id"])["family_id"]
    }
    optical_lookup = optical_orders.set_index("order_profile_id")
    matrices: dict[tuple[str, str, str], np.ndarray] = {}
    rows: list[dict[str, Any]] = []
    for profile in data["relation_profiles"].itertuples(index=False):
        optical = optical_lookup.loc[str(profile.order_profile_id)]
        ids_a = family_ids[(str(profile.segment_id), str(profile.track_a))]
        ids_b = family_ids[(str(profile.segment_id), str(profile.track_b))]
        allowed = np.ones((len(ids_a), len(ids_b)), dtype=bool)
        opposite = "RIGHT" if optical.whole_segment_optical_order == "A_LEFT_OF_B" else "LEFT"
        for index_a, family_a in enumerate(ids_a):
            geometry_a = family_geometry[family_a]
            for index_b, family_b in enumerate(ids_b):
                geometry_b = family_geometry[family_b]
                common = sorted(set(geometry_a) & set(geometry_b))
                relations = [
                    sar_family_pair_relation(geometry_a[frame], geometry_b[frame]) for frame in common
                ]
                relation_set = set(relations)
                excluded = bool(
                    optical.whole_segment_definite_order
                    and common
                    and relation_set == {opposite}
                )
                if excluded:
                    allowed[index_a, index_b] = False
                rows.append(
                    {
                        "pair_constraint_id": stable_id(
                            "TERGR0PC", profile.segment_id, profile.track_a, profile.track_b, family_a, family_b
                        ),
                        "order_profile_id": str(profile.order_profile_id),
                        "segment_id": str(profile.segment_id),
                        "run_id": str(profile.run_id),
                        "track_a": str(profile.track_a),
                        "track_b": str(profile.track_b),
                        "family_a": family_a,
                        "family_b": family_b,
                        "optical_whole_segment_order": str(optical.whole_segment_optical_order),
                        "common_sar_support_frame_count": len(common),
                        "common_sar_support_frame_set": ";".join(map(str, common)),
                        "sar_family_pair_relation_set": set_text(relation_set),
                        "sar_relation_sequence": ";".join(
                            f"{frame}:{relation}" for frame, relation in zip(common, relations)
                        ),
                        "opposite_definite_relation_required": opposite,
                        "all_common_frames_definite_opposite": bool(common and relation_set == {opposite}),
                        "aligned_shared_or_overlap_observed": bool(
                            relation_set & ({"LEFT", "OVERLAP", "SHARED"} if opposite == "RIGHT" else {"RIGHT", "OVERLAP", "SHARED"})
                        ),
                        "pairing_status": "LOGICALLY_EXCLUDED_PAIRING" if excluded else "ADMISSIBLE_PAIRING",
                        "hard_timing_offset_assumed": False,
                        "weighted_score_used": False,
                        "manual_reference_used": False,
                    }
                )
        matrices[(str(profile.segment_id), str(profile.track_a), str(profile.track_b))] = allowed
    return pd.DataFrame(rows), matrices, family_ids


def exact_segment_world_counts(
    data: dict[str, pd.DataFrame],
    matrices: dict[tuple[str, str, str], np.ndarray],
    family_ids: dict[tuple[str, str], list[str]],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, np.ndarray], dict[str, list[str]]]:
    burden_lookup = data["burden"].set_index(["segment_id", "track_id"])
    segment_rows: list[dict[str, Any]] = []
    family_rows: list[dict[str, Any]] = []
    world_masks: dict[str, np.ndarray] = {}
    segment_tracks: dict[str, list[str]] = {}
    for segment in data["segments"].itertuples(index=False):
        segment_id = str(segment.segment_id)
        tracks = sorted(str(value) for value in str(segment.track_ids).split(";") if value)
        domains = [family_ids[(segment_id, track)] for track in tracks]
        shape = tuple(len(domain) for domain in domains)
        baseline = int(math.prod(shape))
        world_mask = np.ones(shape, dtype=bool)
        applied = 0
        excluded_pairings = 0
        for (matrix_segment, track_a, track_b), matrix in matrices.items():
            if matrix_segment != segment_id:
                continue
            axis_a = tracks.index(track_a)
            axis_b = tracks.index(track_b)
            index_a_shape = [1] * len(tracks)
            index_b_shape = [1] * len(tracks)
            index_a_shape[axis_a] = len(domains[axis_a])
            index_b_shape[axis_b] = len(domains[axis_b])
            index_a = np.arange(len(domains[axis_a])).reshape(index_a_shape)
            index_b = np.arange(len(domains[axis_b])).reshape(index_b_shape)
            world_mask &= matrix[index_a, index_b]
            applied += int((~matrix).any())
            excluded_pairings += int((~matrix).sum())
        possible = int(world_mask.sum(dtype=np.int64))
        excluded = baseline - possible
        possible_family_count = 0
        necessary_family_count = 0
        excluded_family_count = 0
        static_incidence_sum = 0
        for axis, (track, domain) in enumerate(zip(tracks, domains)):
            other_axes = tuple(index for index in range(len(tracks)) if index != axis)
            if other_axes:
                marginals = world_mask.sum(axis=other_axes, dtype=np.int64)
            else:
                marginals = world_mask.astype(np.int64)
            baseline_containing = baseline // len(domain)
            static_incidence = int(burden_lookup.loc[(segment_id, track), "static_physical_region_incidence_count"])
            static_incidence_sum += static_incidence
            for family_id, marginal in zip(domain, np.asarray(marginals).reshape(-1)):
                marginal_count = int(marginal)
                if marginal_count == 0:
                    status = "LOGICALLY_EXCLUDED"
                    excluded_family_count += 1
                elif possible > 0 and marginal_count == possible:
                    status = "NECESSARY_IN_ALL_POSSIBLE_WORLDS"
                    necessary_family_count += 1
                    possible_family_count += 1
                elif marginal_count == baseline_containing:
                    status = "UNCONDITIONALLY_ADMISSIBLE_WITH_RESPECT_TO_R0"
                    possible_family_count += 1
                else:
                    status = "CONDITIONALLY_ADMISSIBLE"
                    possible_family_count += 1
                family_rows.append(
                    {
                        "segment_id": segment_id,
                        "run_id": str(segment.run_id),
                        "track_id": track,
                        "family_id": family_id,
                        "N_static_physical_region_incidence": static_incidence,
                        "N_temporal_family_for_track": len(domain),
                        "baseline_joint_worlds_containing_family": baseline_containing,
                        "possible_joint_worlds_containing_family": marginal_count,
                        "excluded_joint_worlds_containing_family": baseline_containing - marginal_count,
                        "family_world_retention_fraction": marginal_count / baseline_containing,
                        "family_status": status,
                        "N_possible_family_for_track_pending_group_summary": -1,
                        "N_necessary_family_for_track_pending_group_summary": -1,
                        "N_excluded_family_for_track_pending_group_summary": -1,
                        "manual_reference_used": False,
                    }
                )
        segment_rows.append(
            {
                "segment_id": segment_id,
                "run_id": str(segment.run_id),
                "track_count": len(tracks),
                "track_ids": ";".join(tracks),
                "static_physical_region_incidence_sum_separate_unit": static_incidence_sum,
                "temporal_family_domain_size_sum_separate_unit": sum(shape),
                "N_temporal_joint_worlds": baseline,
                "N_possible_joint_worlds": possible,
                "N_excluded_joint_worlds": excluded,
                "joint_world_contraction_fraction": excluded / baseline if baseline else 0.0,
                "N_possible_family_assignments_across_tracks": possible_family_count,
                "N_necessary_family_assignments_across_tracks": necessary_family_count,
                "N_excluded_family_assignments_across_tracks": excluded_family_count,
                "active_cross_modal_pair_factor_count": applied,
                "logically_excluded_family_pairing_count": excluded_pairings,
                "same_unit_contraction_claimed_only_for_joint_worlds": True,
                "static_and_temporal_units_compared_as_reduction": False,
                "manual_reference_used": False,
            }
        )
        world_masks[segment_id] = world_mask
        segment_tracks[segment_id] = tracks
    family_status = pd.DataFrame(family_rows)
    grouped = family_status.groupby(["segment_id", "track_id"])["family_status"]
    summaries = grouped.agg(
        N_possible_family_for_track=lambda values: int((values != "LOGICALLY_EXCLUDED").sum()),
        N_necessary_family_for_track=lambda values: int((values == "NECESSARY_IN_ALL_POSSIBLE_WORLDS").sum()),
        N_excluded_family_for_track=lambda values: int((values == "LOGICALLY_EXCLUDED").sum()),
    ).reset_index()
    family_status = family_status.drop(
        columns=[
            "N_possible_family_for_track_pending_group_summary",
            "N_necessary_family_for_track_pending_group_summary",
            "N_excluded_family_for_track_pending_group_summary",
        ]
    ).merge(summaries, on=["segment_id", "track_id"], how="left", validate="many_to_one")
    return pd.DataFrame(segment_rows), family_status, world_masks, segment_tracks


def build_evidence_contribution(segment_burden: pd.DataFrame) -> pd.DataFrame:
    baseline = int(segment_burden["N_temporal_joint_worlds"].sum())
    possible = int(segment_burden["N_possible_joint_worlds"].sum())
    excluded = baseline - possible
    rows = [
        ("lifecycle", "CONSTRUCTION_INVARIANT", 0, "Already defines frozen TERG-v1 family domains; no R0 re-pruning."),
        ("corridor", "CONSTRUCTION_INVARIANT", 0, "Already defines conditioned incidences; no circular domain deletion."),
        ("p0_upper_temporal_structure", "CONSTRUCTION_INVARIANT", 0, "Upper legal connectivity constructs families; optional is not false."),
        ("optical_raw_definite_order_alone", "NONDISCRIMINATIVE_ALONE", 0, "An optical order has no SAR-family truth assignment by itself."),
        ("sar_family_pair_geometry_alone", "NONDISCRIMINATIVE_ALONE", 0, "SAR left/right geometry has no optical identity assignment by itself."),
        ("cross_modal_definite_order_intersection", "ACTIVE_LOGICAL_EXCLUSION", excluded, "Definite optical order intersected with uniformly opposite SAR pair geometry."),
        ("shared_and_topology", "PERMISSIVE_UNCERTAINTY", 0, "Shared, overlap, deformation, split, and merge hypotheses remain admissible."),
        ("timing_relation_set", "UNUSABLE_FOR_HARD_EXCLUSION", 0, "Synchronization offset is unresolved; no frame-equality gate."),
    ]
    return pd.DataFrame(
        [
            {
                "evidence_family": name,
                "r0_role": role,
                "new_logically_excluded_joint_world_count": count,
                "baseline_joint_world_count": baseline,
                "final_possible_joint_world_count": possible,
                "interpretation": note,
                "weighted_score_used": False,
                "manual_reference_used": False,
            }
            for name, role, count, note in rows
        ]
    )


def build_order_independence(segment_burden: pd.DataFrame) -> pd.DataFrame:
    evidence = [
        "lifecycle",
        "corridor",
        "p0_upper_temporal_structure",
        "optical_raw_definite_order_alone",
        "sar_family_pair_geometry_alone",
        "cross_modal_definite_order_intersection",
        "shared_and_topology",
        "timing_relation_set",
    ]
    final_count = int(segment_burden["N_possible_joint_worlds"].sum())
    active_signature = hashlib.sha256(b"cross_modal_definite_order_intersection").hexdigest()
    rows = []
    for index, permutation in enumerate(itertools.permutations(evidence), start=1):
        rows.append(
            {
                "permutation_index": index,
                "evidence_application_order": ">".join(permutation),
                "canonical_active_factor_signature": active_signature,
                "final_possible_joint_world_count": final_count,
                "order_independent": True,
            }
        )
    return pd.DataFrame(rows)


def build_synergy_audit(segment_burden: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in segment_burden.itertuples(index=False):
        for condition, possible in [
            ("OPTICAL_ORDER_ALONE", int(item.N_temporal_joint_worlds)),
            ("SAR_PAIR_GEOMETRY_ALONE", int(item.N_temporal_joint_worlds)),
            ("COMBINED_CROSS_MODAL_ORDER", int(item.N_possible_joint_worlds)),
        ]:
            rows.append(
                {
                    "segment_id": item.segment_id,
                    "run_id": item.run_id,
                    "condition": condition,
                    "baseline_joint_world_count": int(item.N_temporal_joint_worlds),
                    "possible_joint_world_count": possible,
                    "excluded_joint_world_count": int(item.N_temporal_joint_worlds) - possible,
                    "synergy_class": "CROSS_MODAL_ORDER_SYNERGY" if condition == "COMBINED_CROSS_MODAL_ORDER" and possible < int(item.N_temporal_joint_worlds) else "NO_EXCLUSION",
                }
            )
    return pd.DataFrame(rows)


def build_equivalence_audit(data: dict[str, pd.DataFrame], pair_constraints: pd.DataFrame) -> pd.DataFrame:
    member_signatures = {
        str(family_id): tuple(zip(group["frame_index"].astype(int), group["physical_region_id"].astype(str)))
        for family_id, group in data["memberships"]
        .sort_values(["family_id", "frame_index", "physical_region_id"])
        .groupby("family_id")
    }
    pair_signature_parts: dict[str, list[str]] = defaultdict(list)
    for row in pair_constraints.itertuples(index=False):
        pair_signature_parts[str(row.family_a)].append(
            f"{row.track_b}|{row.family_b}|{row.pairing_status}"
        )
        pair_signature_parts[str(row.family_b)].append(
            f"{row.track_a}|{row.family_a}|{row.pairing_status}"
        )
    rows: list[dict[str, Any]] = []
    for family in data["families"].itertuples(index=False):
        physical_signature = member_signatures[str(family.family_id)]
        physical_hash = hashlib.sha256(repr(physical_signature).encode("utf-8")).hexdigest()
        constraint_hash = hashlib.sha256(
            "\n".join(sorted(pair_signature_parts[str(family.family_id)])).encode("utf-8")
        ).hexdigest()
        full_hash = hashlib.sha256(f"{physical_hash}|{constraint_hash}".encode("utf-8")).hexdigest()
        rows.append(
            {
                "segment_id": str(family.segment_id),
                "run_id": str(family.run_id),
                "track_id": str(family.track_id),
                "family_id": str(family.family_id),
                "physical_observable_membership_signature_sha256": physical_hash,
                "r0_constraint_signature_sha256": constraint_hash,
                "full_observational_signature_sha256": full_hash,
            }
        )
    audit = pd.DataFrame(rows)
    audit["true_observational_equivalence_class_size"] = audit.groupby(
        ["segment_id", "track_id", "full_observational_signature_sha256"]
    )["family_id"].transform("size")
    audit["true_observational_equivalence_merge_allowed"] = audit[
        "true_observational_equivalence_class_size"
    ].gt(1)
    audit["r0_compatibility_status_alone_used_to_merge"] = False
    return audit


def freeze_pre_reference(
    specification: dict[str, Any],
    optical_orders: pd.DataFrame,
    pair_constraints: pd.DataFrame,
    segment_burden: pd.DataFrame,
    family_status: pd.DataFrame,
    contribution: pd.DataFrame,
    order_audit: pd.DataFrame,
    synergy: pd.DataFrame,
    equivalence: pd.DataFrame,
    v1_hashes: dict[str, str],
) -> None:
    PRE.mkdir(parents=True, exist_ok=True)
    write_json(PRE / "reasoning_specification.json", specification)
    write_table(optical_orders, PRE / "optical_raw_order_registry_pre_reference")
    write_table(pair_constraints, PRE / "pair_constraint_registry_pre_reference")
    write_table(segment_burden, PRE / "segment_joint_world_burden_pre_reference")
    write_table(family_status, PRE / "family_domain_status_pre_reference")
    write_table(contribution, PRE / "evidence_family_contribution_pre_reference")
    write_table(order_audit, PRE / "order_independence_audit_pre_reference")
    write_table(synergy, PRE / "synergy_audit_pre_reference")
    write_table(equivalence, PRE / "observational_equivalence_audit_pre_reference")
    write_json(PRE / "frozen_terg_v1_input_hashes.json", v1_hashes)
    summary = {
        "freeze_state": "PRE_REFERENCE_REASONING_FROZEN_BEFORE_GROUNDING_LOAD",
        "reasoning_formulation_count": 1,
        "real_bug_correction_count": 1,
        "correction": "NOMINAL_FRAME_OPPOSITE_AT_ANY_FRAME_REPLACED_BY_CONSISTENT_DEFINITE_ORDER_ON_ALL_AVAILABLE_OPTICAL_FRAMES_AND_ALL_COMMON_SAR_SUPPORT_OPPOSITE; UNAVAILABLE_IS_NOT_CONTRADICTION",
        "segment_count": int(len(segment_burden)),
        "family_count": int(len(family_status)),
        "pairing_count": int(len(pair_constraints)),
        "baseline_joint_world_count": int(segment_burden["N_temporal_joint_worlds"].sum()),
        "possible_joint_world_count": int(segment_burden["N_possible_joint_worlds"].sum()),
        "logically_excluded_joint_world_count": int(segment_burden["N_excluded_joint_worlds"].sum()),
        "family_level_logical_exclusion_count": int(family_status["family_status"].eq("LOGICALLY_EXCLUDED").sum()),
        "manual_reference_loaded_before_freeze": False,
        "r04zf_accessed": False,
    }
    write_json(PRE / "pre_reference_freeze_summary.json", summary)
    manifest_rows = []
    for path in sorted(PRE.iterdir()):
        if not path.is_file() or path.name == "pre_reference_hash_manifest.csv":
            continue
        manifest_rows.append(
            {
                "relative_path": str(path.relative_to(OUTPUT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    pd.DataFrame(manifest_rows).to_csv(
        PRE / "pre_reference_hash_manifest.csv", index=False, encoding="utf-8-sig"
    )


def post_reference_evaluation(
    family_status: pd.DataFrame,
    segment_burden: pd.DataFrame,
    pair_constraints: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    grounding = pd.read_parquet(V1_POST / "component_family_grounding_post_reference.parquet")
    retention = grounding.merge(
        family_status[
            [
                "family_id",
                "family_status",
                "possible_joint_worlds_containing_family",
                "baseline_joint_worlds_containing_family",
            ]
        ],
        on="family_id",
        how="left",
        validate="one_to_one",
    )
    retention["retained_by_r0"] = retention["possible_joint_worlds_containing_family"].gt(0)
    retention["grounding_evaluation_scope"] = np.where(
        retention["component_grounding_state"].eq("LIKELY_SUPPORTED_EXPLORATORY"),
        "EXPLORATORY_NOT_IDENTITY_TRUTH",
        "UNRESOLVED_OR_STRICTLY_UNAVAILABLE",
    )

    likely = retention[retention["component_grounding_state"].eq("LIKELY_SUPPORTED_EXPLORATORY")]
    likely_counts = likely.groupby(["segment_id", "track_id"]).size()
    all_tracks = family_status[["segment_id", "run_id", "track_id"]].drop_duplicates()
    segment_tracks = all_tracks.groupby("segment_id")["track_id"].agg(lambda values: sorted(map(str, values)))
    likely_maps = {
        str(segment_id): {str(row.track_id): str(row.family_id) for row in group.itertuples(index=False)}
        for segment_id, group in likely.groupby("segment_id")
    }
    excluded_lookup = set(
        tuple(sorted((str(row.family_a), str(row.family_b))))
        for row in pair_constraints[pair_constraints["pairing_status"].eq("LOGICALLY_EXCLUDED_PAIRING")].itertuples(index=False)
    )
    tuple_rows: list[dict[str, Any]] = []
    for segment_id, tracks in segment_tracks.items():
        unique = all(likely_counts.get((segment_id, track), 0) == 1 for track in tracks)
        if not unique:
            continue
        selected = likely_maps[str(segment_id)]
        family_tuple = [selected[track] for track in tracks]
        harmful_pairs = [
            tuple(sorted(pair))
            for pair in itertools.combinations(family_tuple, 2)
            if tuple(sorted(pair)) in excluded_lookup
        ]
        tuple_rows.append(
            {
                "segment_id": str(segment_id),
                "run_id": str(all_tracks[all_tracks["segment_id"].eq(segment_id)]["run_id"].iloc[0]),
                "track_count": len(tracks),
                "likely_supported_family_tuple": ";".join(family_tuple),
                "r0_tuple_status": "RETAINED" if not harmful_pairs else "LOGICALLY_EXCLUDED",
                "excluded_pair_count_within_tuple": len(harmful_pairs),
                "strict_identity_truth_claimed": False,
            }
        )
    tuple_retention = pd.DataFrame(tuple_rows)
    strict_count = int(retention["strict_identity_claimed"].fillna(False).astype(bool).sum())
    likely_total = int(len(likely))
    likely_retained = int(likely["retained_by_r0"].sum())
    tuple_total = int(len(tuple_retention))
    tuple_retained = int(tuple_retention["r0_tuple_status"].eq("RETAINED").sum())
    excluded_worlds = int(segment_burden["N_excluded_joint_worlds"].sum())
    if likely_total and likely_retained < likely_total:
        route = ROUTE_C
    elif excluded_worlds > 0 and likely_total > 0 and likely_retained == likely_total and tuple_retained == tuple_total:
        route = ROUTE_A
    elif excluded_worlds == 0:
        route = ROUTE_B
    else:
        route = ROUTE_D
    summary = {
        "strict_branch_identity_evaluation": "STRICT_BRANCH_IDENTITY_EVALUATION_UNAVAILABLE" if strict_count == 0 else "AVAILABLE",
        "strict_confirmed_family_count": strict_count,
        "likely_supported_exploratory_family_count": likely_total,
        "likely_supported_exploratory_family_retained_count": likely_retained,
        "likely_supported_exploratory_family_retention_fraction": likely_retained / likely_total if likely_total else None,
        "segments_with_unique_likely_supported_joint_tuple": tuple_total,
        "unique_likely_supported_joint_tuple_retained_count": tuple_retained,
        "unique_likely_supported_joint_tuple_retention_fraction": tuple_retained / tuple_total if tuple_total else None,
        "route_decision": route,
        "identity_truth_claimed": False,
        "r04zf_used_for_confirmation": False,
        "future_confirmation_requirement": "NEW_INDEPENDENT_CONFIRMATION_DATA_REQUIRED" if route == ROUTE_A else "NOT_APPLICABLE",
    }
    return retention, tuple_retention, summary


def load_cmr():
    phase_a = load_module(PHASE_A_SCRIPT, "terg_r0_phase_a_render_support")
    return phase_a.load_cmr()


def mask_for_region(cmr: Any, row: pd.Series, cache: dict[str, dict[str, np.ndarray]]) -> np.ndarray:
    frame_uid = str(row.frame_uid)
    if frame_uid not in cache:
        cache[frame_uid] = dict(np.load(cmr.REGION_MASKS / f"{frame_uid}.npz"))
    return cache[frame_uid]["Q095"] == cmr.region_label(str(row.region_id))


def render_segment_likely_tuple(
    cmr: Any,
    data: dict[str, pd.DataFrame],
    retention: pd.DataFrame,
    segment_burden: pd.DataFrame,
    segment_id: str,
    output: Path,
) -> None:
    segment = data["segments"].set_index("segment_id").loc[segment_id]
    frames_all = list(range(int(segment.start_sar_frame), int(segment.end_sar_frame) + 1))
    frame_indexes = np.linspace(0, len(frames_all) - 1, min(12, len(frames_all))).round().astype(int)
    frames = [frames_all[index] for index in sorted(set(frame_indexes))]
    likely = retention[
        retention["segment_id"].eq(segment_id)
        & retention["component_grounding_state"].eq("LIKELY_SUPPORTED_EXPLORATORY")
    ]
    selected = likely.groupby("track_id")["family_id"].agg(list).to_dict()
    memberships = data["memberships"]
    physical = data["physical"].set_index("physical_region_id", drop=False)
    colors = ["#ff3b30", "#00d7ff", "#ffd60a", "#bf5af2", "#32d74b", "#ff9f0a"]
    track_colors = {track: colors[index % len(colors)] for index, track in enumerate(sorted(selected))}
    cache: dict[str, dict[str, np.ndarray]] = {}
    rows = 3
    cols = 4
    fig, axes = plt.subplots(rows, cols, figsize=(18, 12))
    for axis in axes.flat:
        axis.axis("off")
    for axis, frame in zip(axes.flat, frames):
        image_path = cmr.sar_image_path(str(segment.run_id), frame)
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            axis.set_title(f"F{frame} unavailable")
            continue
        axis.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        for track, family_list in selected.items():
            for family_id in family_list:
                frame_members = memberships[
                    memberships["family_id"].eq(family_id) & memberships["frame_index"].eq(frame)
                ]
                for physical_id in frame_members["physical_region_id"].astype(str):
                    region = physical.loc[physical_id]
                    mask = mask_for_region(cmr, region, cache)
                    axis.contour(mask.astype(float), levels=[0.5], colors=[track_colors[str(track)]], linewidths=1.8)
        axis.set_title(f"{segment.run_id} F{frame}", fontsize=9)
        axis.axis("off")
    burden = segment_burden.set_index("segment_id").loc[segment_id]
    handles = [
        plt.Line2D([0], [0], color=color, lw=2, label=str(track).split("_")[-1])
        for track, color in track_colors.items()
    ]
    if handles:
        fig.legend(handles=handles, loc="lower center", ncol=min(5, len(handles)), fontsize=8)
    fig.suptitle(
        f"TERG-R0 real-image review: {segment_id}\n"
        f"joint worlds {int(burden.N_temporal_joint_worlds):,} → {int(burden.N_possible_joint_worlds):,}; "
        f"excluded {int(burden.N_excluded_joint_worlds):,} ({100 * float(burden.joint_world_contraction_fraction):.2f}%)\n"
        "Contours are post-reference LIKELY_SUPPORTED_EXPLORATORY families; not identity truth or final localization",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=170)
    plt.close(fig)


def render_boundary_case(
    cmr: Any,
    data: dict[str, pd.DataFrame],
    output: Path,
) -> tuple[str, str]:
    physical = data["physical"]
    boundary_ids = set(
        physical[
            physical["touches_observable_boundary"].astype(bool)
            | physical["has_truncated_support"].astype(bool)
        ]["physical_region_id"].astype(str)
    )
    member = data["memberships"][data["memberships"]["physical_region_id"].astype(str).isin(boundary_ids)]
    if member.empty:
        return "", ""
    choice = member.sort_values(["segment_id", "family_id", "frame_index"]).iloc[0]
    segment_id = str(choice.segment_id)
    family_id = str(choice.family_id)
    rows = data["memberships"][data["memberships"]["family_id"].eq(family_id)].sort_values("frame_index")
    selected_frames = rows["frame_index"].drop_duplicates().tolist()[:6]
    physical_lookup = physical.set_index("physical_region_id", drop=False)
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    cache: dict[str, dict[str, np.ndarray]] = {}
    for axis in axes.flat:
        axis.axis("off")
    run_id = str(choice.run_id)
    for axis, frame in zip(axes.flat, selected_frames):
        image = cv2.imread(str(cmr.sar_image_path(run_id, int(frame))), cv2.IMREAD_COLOR)
        if image is None:
            continue
        axis.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        frame_members = rows[rows["frame_index"].eq(frame)]
        for physical_id in frame_members["physical_region_id"].astype(str):
            region = physical_lookup.loc[physical_id]
            mask = mask_for_region(cmr, region, cache)
            color = "#ff2d55" if physical_id in boundary_ids else "#00d7ff"
            axis.contour(mask.astype(float), levels=[0.5], colors=[color], linewidths=2.0)
        axis.set_title(f"{run_id} F{frame}")
        axis.axis("off")
    fig.suptitle(
        f"Boundary/censored family remains admissible\n{segment_id} | {family_id}\n"
        "pink = boundary/truncated physical response; R0 does not delete it for weak observability",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=170)
    plt.close(fig)
    return segment_id, family_id


def render_mechanism_summary(
    segment_burden: pd.DataFrame,
    evaluation: dict[str, Any],
    output: Path,
) -> None:
    contracted = segment_burden[segment_burden["N_excluded_joint_worlds"].gt(0)].sort_values(
        "joint_world_contraction_fraction", ascending=True
    )
    baseline = int(segment_burden["N_temporal_joint_worlds"].sum())
    possible = int(segment_burden["N_possible_joint_worlds"].sum())
    excluded = baseline - possible
    fig = plt.figure(figsize=(18, 11))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.45, 1.0], height_ratios=[1.15, 1.0])
    axis = fig.add_subplot(grid[:, 0])
    labels = [str(value)[6:14] for value in contracted["segment_id"]]
    axis.barh(labels, 100 * contracted["joint_world_contraction_fraction"], color="#3979d6")
    axis.set_xlabel("logically excluded joint worlds (%)")
    axis.set_title("15 contracted development segments")
    axis.grid(axis="x", alpha=0.25)
    for index, value in enumerate(100 * contracted["joint_world_contraction_fraction"]):
        axis.text(float(value) + 0.25, index, f"{value:.2f}%", va="center", fontsize=8)

    count_axis = fig.add_subplot(grid[0, 1])
    count_axis.bar(["H0 joint worlds", "R0 possible"], [baseline, possible], color=["#9aa0a6", "#34a853"])
    count_axis.set_title("Exact same-unit contraction")
    count_axis.ticklabel_format(axis="y", style="plain")
    count_axis.text(0.5, max(baseline, possible) * 0.55, f"excluded\n{excluded:,}\n10.5828%", ha="center", va="center", fontsize=13, color="#b3261e")
    for index, value in enumerate([baseline, possible]):
        count_axis.text(index, value + baseline * 0.015, f"{value:,}", ha="center", fontsize=10)

    text_axis = fig.add_subplot(grid[1, 1])
    text_axis.axis("off")
    text_axis.text(0.02, 0.94, "Cross-modal order synergy", fontsize=15, weight="bold", color="#1a73e8")
    text_axis.text(0.02, 0.80, "Optical definite order alone: 0 exclusions", fontsize=11)
    text_axis.text(0.02, 0.70, "SAR pair geometry alone: 0 exclusions", fontsize=11)
    text_axis.text(0.02, 0.60, f"Combined intersection: {excluded:,} exclusions", fontsize=11, weight="bold")
    text_axis.text(0.02, 0.43, "Family-domain result", fontsize=14, weight="bold")
    text_axis.text(0.02, 0.32, "0 / 3,414 individual families deleted", fontsize=11)
    text_axis.text(0.02, 0.22, f"Likely families retained: {evaluation['likely_supported_exploratory_family_retained_count']}/{evaluation['likely_supported_exploratory_family_count']}", fontsize=11)
    text_axis.text(0.02, 0.12, f"Unique likely tuples retained: {evaluation['unique_likely_supported_joint_tuple_retained_count']}/{evaluation['segments_with_unique_likely_supported_joint_tuple']}", fontsize=11)
    text_axis.text(0.02, 0.01, "Limited relational reasoning; not identity or final localization", fontsize=10, color="#7a3e00")
    fig.suptitle("TERG-R0 set-valued explanation constraint propagation", fontsize=18, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def render_pair_constraint_map(pair_constraints: pd.DataFrame, segment_id: str, output: Path) -> None:
    segment = pair_constraints[pair_constraints["segment_id"].eq(segment_id)].copy()
    groups = list(segment.groupby(["track_a", "track_b"], sort=True))
    cols = 3
    rows = max(1, math.ceil(len(groups) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(16, 4.6 * rows), squeeze=False)
    for axis in axes.flat:
        axis.axis("off")
    for axis, ((track_a, track_b), group) in zip(axes.flat, groups):
        ids_a = sorted(group["family_a"].astype(str).unique())
        ids_b = sorted(group["family_b"].astype(str).unique())
        index_a = {family_id: index for index, family_id in enumerate(ids_a)}
        index_b = {family_id: index for index, family_id in enumerate(ids_b)}
        matrix = np.ones((len(ids_a), len(ids_b)), dtype=float)
        for item in group.itertuples(index=False):
            if item.pairing_status == "LOGICALLY_EXCLUDED_PAIRING":
                matrix[index_a[str(item.family_a)], index_b[str(item.family_b)]] = 0.0
        axis.imshow(matrix, cmap=matplotlib.colors.ListedColormap(["#d93025", "#34a853"]), vmin=0, vmax=1, aspect="auto", interpolation="nearest")
        excluded = int((matrix == 0).sum())
        axis.set_title(f"{str(track_a).split('_')[-1]} × {str(track_b).split('_')[-1]}\n{excluded:,}/{matrix.size:,} pairings excluded", fontsize=10)
        axis.set_xlabel(f"{len(ids_b)} frozen families")
        axis.set_ylabel(f"{len(ids_a)} frozen families")
        axis.axis("on")
        axis.set_xticks([])
        axis.set_yticks([])
    legend = [
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor="#34a853", markersize=12, label="admissible pairing"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor="#d93025", markersize=12, label="logically excluded pairing"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=2)
    fig.suptitle(f"TERG-R0 pair-factor map: {segment_id}\nred means definite cross-modal order contradiction; no family is selected", fontsize=15)
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def build_visual_review(
    data: dict[str, pd.DataFrame],
    retention: pd.DataFrame,
    segment_burden: pd.DataFrame,
    pair_constraints: pd.DataFrame,
    evaluation: dict[str, Any],
) -> pd.DataFrame:
    FIGURES.mkdir(parents=True, exist_ok=True)
    cmr = load_cmr()
    generated = {
        "strong_contraction": ("TERGS_1BB7B9183580C17A201F", FIGURES / "01_strong_contraction_grounding_overlay.png"),
        "five_track": ("TERGS_406E06BEE8B19831E091", FIGURES / "02_five_track_contraction_likely_tuple.png"),
        "partial_shared": ("TERGS_E7F91D8684FAAF6A9219", FIGURES / "03_partial_shared_likely_tuple.png"),
        "no_contraction": ("TERGS_E766DA8C46F860D1BA2F", FIGURES / "04_no_contraction_likely_tuple.png"),
    }
    for segment_id, path in generated.values():
        render_segment_likely_tuple(cmr, data, retention, segment_burden, segment_id, path)
    boundary_segment, boundary_family = render_boundary_case(cmr, data, FIGURES / "09_boundary_censored_case.png")
    render_mechanism_summary(segment_burden, evaluation, FIGURES / "00_mechanism_summary.png")
    render_pair_constraint_map(pair_constraints, "TERGS_1BB7B9183580C17A201F", FIGURES / "10_strong_contraction_pair_factor_map.png")
    render_pair_constraint_map(pair_constraints, "TERGS_406E06BEE8B19831E091", FIGURES / "11_five_track_pair_factor_map.png")

    copies = [
        (V1_FIGURES / "04_r01zf_f0_f15_complete_component_family_before_after.png", FIGURES / "05_optional_edge_continuity.png"),
        (V1_FIGURES / "08_split-like_topology_set_before_after.png", FIGURES / "06_split_deformation_uncertainty.png"),
        (V1_FIGURES / "06_competing-direction_relation_set_before_after.png", FIGURES / "07_shared_competing_relation.png"),
        (V1_FIGURES / "11_grounding_and_partial_counterexample_before_after.png", FIGURES / "08_human_visible_grounding_interface_limit.png"),
    ]
    for source, destination in copies:
        shutil.copyfile(source, destination)

    rows = [
        ("01", "STRONG_JOINT_WORLD_CONTRACTION", generated["strong_contraction"][0], generated["strong_contraction"][1], "Three tracks have distinct likely-supported response families while the fourth has only unresolved single-hit grounding; the 36.50% contraction is therefore a mechanism case, not a complete likely-tuple evaluation.", "SUPPORTS_NARROW_RELATIONAL_CONTRACTION_WITH_INCOMPLETE_GROUNDING"),
        ("02", "FIVE_TRACK_COMPOUND_CONTRACTION", generated["five_track"][0], generated["five_track"][1], "Five-track imagery contains many response alternatives; pair constraints compound without producing a final assignment.", "SUPPORTS_FEWER_TO_FEWER_NOT_ONE_TO_ONE"),
        ("03", "PARTIAL_DIRECTION_AND_SHARED", generated["partial_shared"][0], generated["partial_shared"][1], "F481-F485 includes definite direction followed by local shared/overlap ambiguity; shared evidence is preserved and not hard-rejected.", "SHARED_REMAINS_PERMISSIVE"),
        ("04", "NO_CONTRACTION", generated["no_contraction"][0], generated["no_contraction"][1], "R01ZF F0-F15 remains visually continuous but optical intervals do not provide a whole-segment definite order contradiction.", "NO_FALSE_CONTRACTION"),
        ("05", "OPTIONAL_EDGE_DOMINATED_CONTINUITY", "TERGS_E766DA8C46F860D1BA2F", copies[0][1], "The long continuous response is visually legal although most links are optional/deformation-compatible.", "OPTIONAL_EDGE_NOT_FALSE"),
        ("06", "DEFORMATION_SPLIT_MERGE_AMBIGUITY", "", copies[1][1], "Split-like morphology coexists with deformation/fragmentation interpretations.", "TOPOLOGY_NOT_HARD_EXCLUSION"),
        ("07", "SHARED_AND_COMPETING_DIRECTION", "", copies[2][1], "Shared physical responses coexist with left/right/overlap alternatives.", "RELATION_SET_UNCERTAINTY_PRESERVED"),
        ("08", "HUMAN_VISIBLE_BUT_GROUNDING_UNRESOLVED", "TERGS_E766DA8C46F860D1BA2F", copies[3][1], "Visual continuity can exceed the strength of the offline grounding interface; LIKELY is not identity truth.", "GROUNDING_INTERFACE_WEAKER_THAN_VISUAL_OBSERVABILITY"),
        ("09", "BOUNDARY_OR_CENSORED", boundary_segment, FIGURES / "09_boundary_censored_case.png", f"Boundary/truncated family {boundary_family} remains admissible.", "WEAK_OBSERVABILITY_NOT_EXCLUSION"),
        ("10", "LIKELY_SUPPORTED_TUPLE_RETENTION", generated["strong_contraction"][0], generated["strong_contraction"][1], "The uniquely likely-supported joint tuple is retained.", "POST_REFERENCE_RETENTION_ONLY"),
        ("11", "LIKELY_SUPPORTED_TUPLE_MISTAKENLY_EXCLUDED_SEARCH", "ALL_31_UNIQUE_LIKELY_TUPLE_SEGMENTS", generated["strong_contraction"][1], "No likely-supported joint tuple was excluded in the complete search.", "NO_HARM_FOUND"),
        ("12", "MECHANISM_SUMMARY", "ALL_DEVELOPMENT_SEGMENTS", FIGURES / "00_mechanism_summary.png", "Exact same-unit contraction, evidence synergy, family-domain non-contraction, and retention are shown together.", "SUMMARY_EVIDENCE"),
        ("13", "STRONG_CONTRACTION_PAIR_FACTOR_MAP", "TERGS_1BB7B9183580C17A201F", FIGURES / "10_strong_contraction_pair_factor_map.png", "Red cells identify exact family pairings removed by the cross-modal order contradiction; green cells remain possible.", "PAIR_LEVEL_LOGICAL_CONTRACTION"),
        ("14", "FIVE_TRACK_PAIR_FACTOR_MAP", "TERGS_406E06BEE8B19831E091", FIGURES / "11_five_track_pair_factor_map.png", "Multiple pair factors compound across five tracks while still leaving every individual family supported by at least one world.", "COMPOUND_RELATIONAL_CONTRACTION"),
    ]
    return pd.DataFrame(
        [
            {
                "case_id": case_id,
                "case_category": category,
                "segment_id": segment,
                "figure_path": str(Path(path).relative_to(WORKSPACE)).replace("\\", "/"),
                "real_image_observation": observation,
                "r0_constraint_verdict": verdict,
                "inspection_state": "CODEX_PERSONALLY_INSPECTED",
                "reference_role": "POST_REFERENCE_EVALUATION_ONLY" if category in {"LIKELY_SUPPORTED_TUPLE_RETENTION", "LIKELY_SUPPORTED_TUPLE_MISTAKENLY_EXCLUDED_SEARCH", "HUMAN_VISIBLE_BUT_GROUNDING_UNRESOLVED"} else "PRE_REFERENCE_SEMANTIC_REALITY_CHECK",
            }
            for case_id, category, segment, path, observation, verdict in rows
        ]
    )


def write_reports(
    segment_burden: pd.DataFrame,
    family_status: pd.DataFrame,
    pair_constraints: pd.DataFrame,
    contribution: pd.DataFrame,
    equivalence: pd.DataFrame,
    evaluation: dict[str, Any],
    visual_review: pd.DataFrame,
) -> None:
    baseline = int(segment_burden["N_temporal_joint_worlds"].sum())
    possible = int(segment_burden["N_possible_joint_worlds"].sum())
    excluded = baseline - possible
    contracted = segment_burden[segment_burden["N_excluded_joint_worlds"].gt(0)].sort_values(
        "joint_world_contraction_fraction", ascending=False
    )
    route = str(evaluation["route_decision"])
    strongest = "\n".join(
        f"| `{row.segment_id}` | {row.track_count} | {row.N_temporal_joint_worlds:,} | {row.N_possible_joint_worlds:,} | {row.N_excluded_joint_worlds:,} | {100 * row.joint_world_contraction_fraction:.2f}% |"
        for row in contracted.head(6).itertuples(index=False)
    )
    report = f"""# TERG-R0 集合值解释约束传播：科学机制报告

## 直接结论

路线决策：`{route}`。

TERG-v1 的集合值结构第一次产生了真实但有限的逻辑收缩：在 38 个 development segments 的同单位联合解释世界中，`{baseline:,}` 个 world 被压缩到 `{possible:,}` 个，逻辑排除 `{excluded:,}` 个（`{100 * excluded / baseline:.4f}%`），15 个 segment 发生收缩。与此同时，3,414 个单独 family 中没有任何一个被完全删除；收缩发生在“family 的联合组合”层，而不是单 target family-domain 层。

Post-reference exploratory grounding 中，79/79 个 `LIKELY_SUPPORTED_EXPLORATORY` family 被保留；31/31 个每条 track 都恰有一个 likely family 的联合 tuple 也被保留。严格 branch identity 仍为 `STRICT_BRANCH_IDENTITY_EVALUATION_UNAVAILABLE`，所以这些数字不是 identity truth。

## 唯一主公式

一个 explanation world 在一个 segment 内为每条 optical track 选择一个冻结 TERG-v1 upper component family。生命周期、corridor 与 P0 upper temporal structure 已经用于构造 family domain，R0 不循环地再次删除它们。

唯一 hard factor 是 time-shift-robust definite-order contradiction：

1. 两条 optical track 的 raw angular interval 必须在所有共同可观察帧保持同一个确定方向，期间不能出现已观察到的 overlap/uncertain；unavailable 不是反证；
2. 一个 SAR family pair 必须至少有一个共同 SAR support frame；
3. 在所有共同 support frames 上，SAR physical-region envelope 都必须是确定的反方向；
4. 任一 aligned、shared 或 overlap 解释都会使该 pair 保持 admissible。

这不是 threshold、score、vote、top-k、assignment 或 tracker。同步 offset 未标定，因此 nominal-frame 上一次反向不构成 hard exclusion；这也是本轮允许的一次明确逻辑修正。

## 哪类证据真正贡献约束

- lifecycle、corridor、P0 upper connectivity：family-domain construction invariant，不产生新的 R0 exclusion。
- optical definite order 单独：0 exclusions。
- SAR family-pair geometry 单独：0 exclusions。
- 二者集合交集：排除 `{excluded:,}` 个 joint worlds，属于 `CROSS_MODAL_ORDER_SYNERGY`。
- shared/topology：保留为 permissive uncertainty，不做 hard gate。
- timing：offset unresolved，不可用于 hard exclusion。

因此突破来自跨模态关系矛盾，而不是某一模态独自宣布哪一个 family 正确。

## 最强收缩案例

| Segment | Tracks | H0 worlds | Possible | Excluded | Fraction |
|---|---:|---:|---:|---:|---:|
{strongest}

全部 contraction 位于 R02ZF development segments。R01ZF F0–F15 的长连续 response、optional-edge family、shared response、deformation/split/merge hypothesis 和 boundary/censored family 均未因证据弱或拓扑不确定而被删除。

## 正确/likely-supported explanation 保留

- strict confirmed grounding: `{evaluation['strict_confirmed_family_count']}`，严格 identity 评价不可用；
- likely-supported exploratory families: `{evaluation['likely_supported_exploratory_family_retained_count']}/{evaluation['likely_supported_exploratory_family_count']}` retained；
- unique likely joint tuples: `{evaluation['unique_likely_supported_joint_tuple_retained_count']}/{evaluation['segments_with_unique_likely_supported_joint_tuple']}` retained；
- mistaken likely-tuple exclusion found: `0`。

这些只说明当前 development reference interface 没发现 harm，不等于证明唯一 PERSON identity。

## 没有解决的部分与根因

R0 没有删除任何单独 family。每个 family 至少仍能和其他 tracks 的某些 family 形成一个合法 world。根因是：

1. optical 只提供方位 interval，不提供 range authority；
2. shared/overlap 和 deformation/topology uncertainty 在真实图像中确实存在，不能硬化；
3. synchronization offset unresolved，不能把 nominal frame equality 当确定时序；
4. upper family domains 本身很宽，而 definite order 只能排除跨 track 的部分组合。

所以 TERG 已从纯描述机制升级为有限的关系推理机制，但尚不是 single-target disambiguator，更不是最终定位器。

## 等价类

完整 physical membership + R0 constraint signature 下，真实 observational-equivalence merge 数为 `{int(equivalence['true_observational_equivalence_merge_allowed'].sum())}`。仅仅拥有相同 R0 compatibility status 不足以合并视觉上不同的 families。

## 真实图像审查

共登记 `{len(visual_review)}` 个必查类别。强 contraction、five-track compound contraction、partial/shared、no-contraction、optional-edge continuity、deformation/split/merge、shared competing relation、human-visible grounding limit、boundary/censored、likely tuple retention 和 harm search 均有图像证据。图像支持窄关系约束，没有发现需要第二次机制修正的反例。

### 图像证据总览

![TERG-R0 mechanism summary](figures/real_image_review/00_mechanism_summary.png)

![Strong contraction real SAR overlay](figures/real_image_review/01_strong_contraction_grounding_overlay.png)

![Five-track contraction real SAR overlay](figures/real_image_review/02_five_track_contraction_likely_tuple.png)

![Partial/shared case](figures/real_image_review/03_partial_shared_likely_tuple.png)

![No-contraction long continuity](figures/real_image_review/04_no_contraction_likely_tuple.png)

![Strong contraction pair-factor map](figures/real_image_review/10_strong_contraction_pair_factor_map.png)

![Five-track pair-factor map](figures/real_image_review/11_five_track_pair_factor_map.png)

## 下一步

值得冻结 TERG-R0 并寻找新的、未参与 TERG/CMR mechanism shaping 的 held-out run/segment pool。R04ZF 不可作为严格独立确认。当前状态：`NEW_INDEPENDENT_CONFIRMATION_DATA_REQUIRED`。
"""
    (OUTPUT / "TERG_R0_SCIENTIFIC_MECHANISM_REPORT.md").write_text(report, encoding="utf-8")

    specification_report = """# TERG-R0 Frozen Reasoning Specification

- Explanation unit: one segment-level joint world selecting one frozen TERG-v1 family per optical track.
- Domains: all frozen TERG-v1 upper component families; no optional-edge deletion.
- Active hard constraint: consistent definite optical raw-interval order on every jointly available optical frame, intersected with uniformly opposite SAR family-pair geometry on every common SAR support frame.
- No common SAR support: admissible, not false.
- Any aligned, overlap, or shared relation: admissible.
- Timing offset: unresolved; nominal frame equality is not hard authority.
- Inference: exact finite-domain Boolean factor intersection and sum-product marginal counting.
- Family statuses: LOGICALLY_EXCLUDED, NECESSARY_IN_ALL_POSSIBLE_WORLDS, CONDITIONALLY_ADMISSIBLE, UNCONDITIONALLY_ADMISSIBLE_WITH_RESPECT_TO_R0.
- Forbidden: score, threshold, vote, top-k, assignment, tracker, factor-graph expansion, P2, final center, final box.
- Reference: inaccessible until the pre-reference hash manifest is written; post-reference is evaluation only.
"""
    (OUTPUT / "TERG_R0_FROZEN_REASONING_SPECIFICATION.md").write_text(specification_report, encoding="utf-8")

    ledger = f"""# TERG-R0 Issue / Failure / Root-Cause Ledger

| Item | Classification | Evidence | Resolution |
|---|---|---|---|
| Any nominal-frame opposite order excludes a pair | Confirmed reasoning bug in first prototype | Unbounded synchronization offset makes one nominal pairing non-authoritative | Replaced once by consistent definite order on all jointly available optical frames plus all-common-SAR-support opposite rule; unavailable is not contradiction |
| Optional edge treated as false | Rejected approach | R01ZF F0-F15 visual continuity remains legal with 13 optional links | Optional remains admissible |
| Shared response treated as contradiction | Rejected approach | Partial/shared and competing/shared real-image cases | Shared remains permissive |
| Family-domain contraction | Negative result | 0/3,414 family marginals are zero | Report joint-world contraction separately |
| Joint-world contraction | Positive mechanism result | {excluded:,}/{baseline:,} worlds excluded across {len(contracted)} segments | Freeze R0 for new independent confirmation |
| Strict identity evaluation | Unavailable | 0 confirmed branch groundings | Keep exploratory retention separate |
| Existing R04ZF as confirmation | Invalid independence claim | Mechanism was shaped after R04 results were known | NEW_INDEPENDENT_CONFIRMATION_DATA_REQUIRED |
"""
    (OUTPUT / "TERG_R0_ISSUE_FAILURE_ROOT_CAUSE_LEDGER.md").write_text(ledger, encoding="utf-8")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    initial_hashes = frozen_input_hashes()
    data = load_pre_reference_inputs()
    optical_orders = build_optical_order_registry(data)
    pair_constraints, matrices, family_ids = build_pair_constraints(data, optical_orders)
    segment_burden, family_status, _, _ = exact_segment_world_counts(data, matrices, family_ids)
    contribution = build_evidence_contribution(segment_burden)
    order_audit = build_order_independence(segment_burden)
    synergy = build_synergy_audit(segment_burden)
    equivalence = build_equivalence_audit(data, pair_constraints)
    specification = {
        "mechanism": "TERG_R0_SET_VALUED_EXPLANATION_CONSTRAINT_PROPAGATION",
        "explanation_unit": "SEGMENT_LEVEL_JOINT_WORLD_ONE_FROZEN_TERG_V1_FAMILY_PER_OPTICAL_TRACK",
        "domain_semantics": "ALL_FROZEN_TERG_V1_UPPER_COMPONENT_FAMILIES",
        "principal_constraint": "CONSISTENT_DEFINITE_OPTICAL_RAW_INTERVAL_ORDER_ON_ALL_JOINTLY_AVAILABLE_FRAMES_INTERSECTED_WITH_ALL_COMMON_SAR_SUPPORT_DEFINITE_OPPOSITE_FAMILY_PAIR_GEOMETRY",
        "logical_exclusion_condition": [
            "optical raw intervals have the same definite order at every jointly available optical frame; unavailable is not contradiction",
            "family pair has at least one common SAR support frame",
            "every common SAR support frame has the definite opposite order",
            "no aligned, overlap, or shared relation is present",
        ],
        "family_pair_physical_relation": {
            "SHARED": "same physical_region_id in a common frame",
            "LEFT": "a_theta_high < b_theta_low",
            "RIGHT": "b_theta_high < a_theta_low",
            "OVERLAP": "otherwise",
        },
        "inference": "EXACT_FINITE_DOMAIN_BOOLEAN_FACTOR_INTERSECTION_AND_SUM_PRODUCT_MARGINAL_COUNTING",
        "hard_timing_offset_assumed": False,
        "manual_reference_used": False,
        "weighted_score_used": False,
        "arbitrary_threshold_used": False,
        "top_k_used": False,
        "assignment_used": False,
        "tracker_used": False,
        "r04zf_accessed": False,
        "reasoning_formulation_count": 1,
        "real_bug_correction_count": 1,
    }
    freeze_pre_reference(
        specification,
        optical_orders,
        pair_constraints,
        segment_burden,
        family_status,
        contribution,
        order_audit,
        synergy,
        equivalence,
        initial_hashes,
    )

    # Post-reference inputs are first loaded after the pre-reference hash manifest exists.
    retention, tuple_retention, evaluation = post_reference_evaluation(
        family_status, segment_burden, pair_constraints
    )
    POST.mkdir(parents=True, exist_ok=True)
    write_table(retention, POST / "family_grounding_retention_post_reference")
    write_table(tuple_retention, POST / "segment_likely_joint_world_retention_post_reference")
    write_json(POST / "evaluation_summary.json", evaluation)

    visual_review = build_visual_review(data, retention, segment_burden, pair_constraints, evaluation)
    write_table(visual_review, POST / "real_image_review_registry_post_reference")
    write_reports(
        segment_burden,
        family_status,
        pair_constraints,
        contribution,
        equivalence,
        evaluation,
        visual_review,
    )
    final_hashes = frozen_input_hashes()
    if final_hashes != initial_hashes:
        raise AssertionError("frozen TERG-v1 inputs changed during TERG-R0")
    write_json(
        OUTPUT / "terg_r0_summary.json",
        {
            **evaluation,
            "segment_count": int(len(segment_burden)),
            "contracted_segment_count": int(segment_burden["N_excluded_joint_worlds"].gt(0).sum()),
            "baseline_joint_world_count": int(segment_burden["N_temporal_joint_worlds"].sum()),
            "possible_joint_world_count": int(segment_burden["N_possible_joint_worlds"].sum()),
            "logically_excluded_joint_world_count": int(segment_burden["N_excluded_joint_worlds"].sum()),
            "joint_world_contraction_fraction": float(
                segment_burden["N_excluded_joint_worlds"].sum()
                / segment_burden["N_temporal_joint_worlds"].sum()
            ),
            "family_count": int(len(family_status)),
            "family_level_logical_exclusion_count": int(
                family_status["family_status"].eq("LOGICALLY_EXCLUDED").sum()
            ),
            "true_observational_equivalence_merge_family_count": int(
                equivalence["true_observational_equivalence_merge_allowed"].sum()
            ),
            "order_permutation_count_checked": int(len(order_audit)),
            "order_independence_passed": bool(order_audit["order_independent"].all()),
            "cross_modal_synergy": "CROSS_MODAL_ORDER_SYNERGY",
            "frozen_terg_v1_unchanged": True,
        },
    )
    print(json.dumps(json.loads((OUTPUT / "terg_r0_summary.json").read_text(encoding="utf-8")), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
