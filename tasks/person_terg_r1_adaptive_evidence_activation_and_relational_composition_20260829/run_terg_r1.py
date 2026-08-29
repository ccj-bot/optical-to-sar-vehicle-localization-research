from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_terg_r1_adaptive_evidence_activation_and_relational_composition_20260829"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference"
FIGURES = OUTPUT / "figures"
PAIR_FIGURES = FIGURES / "excluded_pair_direct_verification"
SUMMARY_FIGURES = FIGURES / "mechanism_diagnostics"

R0_ROOT = WORKSPACE / "output" / "person_terg_r0_set_valued_explanation_constraint_propagation_20260829"
R0_PRE = R0_ROOT / "pre_reference"
R0_POST = R0_ROOT / "post_reference"
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
P1E_ROOT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "p1e_sar_only_response_interface"
    / "runtime_track_response_region_minimal_v1"
)
REGION_MASKS = P1E_ROOT / "response_region_masks"
OPTICAL_HYPOTHESES = (
    WORKSPACE / "output" / "person_optical_guided_sar_annotation_full_20260823" / "optical_person_frame_hypotheses.parquet"
)
FRAME_ROOT = WORKSPACE / "output" / "pseudocolor_labelstudio_prep_20260722" / "frames"

TARGET_SEGMENTS = {
    "strongest": "TERGS_1BB7B9183580C17A201F",
    "five_track": "TERGS_406E06BEE8B19831E091",
}

FINAL_ROUTE = "RELATIONAL_INFORMATION_REAL_BUT_ABSOLUTE_ANCHOR_REQUIRED"
EVIDENCE_ORDER = [
    "RELATIVE_ANGULAR_ORDER",
    "LIFECYCLE_PERSISTENCE",
    "SHARED_RESPONSE_STATE",
    "TOPOLOGY_HYPOTHESIS_SET",
    "BOUNDARY_CENSORING",
    "RESPONSE_COMPONENT_SET",
    "EXACT_CROSS_MODAL_TIMING",
    "RELATIVE_RANGE_LIKE_ORDER",
    "UNARY_FAMILY_DISCRIMINATION",
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def frozen_input_hashes() -> dict[str, str]:
    roots = [V1_ROOT, R0_ROOT]
    return {
        str(path.relative_to(WORKSPACE)).replace("\\", "/"): sha256_file(path)
        for root in roots
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def set_text(values: set[str] | list[str] | tuple[str, ...]) -> str:
    return "{" + ",".join(sorted(set(values))) + "}"


def load_pre_reference_inputs() -> dict[str, pd.DataFrame]:
    optical = pd.read_parquet(OPTICAL_HYPOTHESES)
    optical = optical[optical["box_source"].astype(str).eq("DETECTED")].copy()
    return {
        "pair": pd.read_parquet(R0_PRE / "pair_constraint_registry_pre_reference.parquet"),
        "family_status": pd.read_parquet(R0_PRE / "family_domain_status_pre_reference.parquet"),
        "burden": pd.read_parquet(R0_PRE / "segment_joint_world_burden_pre_reference.parquet"),
        "optical_order": pd.read_parquet(R0_PRE / "optical_raw_order_registry_pre_reference.parquet"),
        "family": pd.read_parquet(V1_PRE / "admissible_component_families_pre_reference.parquet"),
        "membership": pd.read_parquet(V1_PRE / "component_family_membership_pre_reference.parquet"),
        "physical": pd.read_parquet(V1_PRE / "physical_sar_response_regions_pre_reference.parquet"),
        "relations": pd.read_parquet(V1_PRE / "possible_relation_sets_pre_reference.parquet"),
        "temporal_burden": pd.read_parquet(V1_PRE / "temporal_stratification_burden_profiles_pre_reference.parquet"),
        "timing": pd.read_parquet(V1_PRE / "timing_authority_pre_reference.parquet"),
        "segments": pd.read_parquet(D0_PRE / "temporal_segment_atlas_pre_reference.parquet"),
        "frame_state": pd.read_parquet(D0_PRE / "optical_temporal_frame_state_pre_reference.parquet"),
        "relation_extent": pd.read_parquet(V1_PRE / "relation_temporal_support_extents_pre_reference.parquet"),
        "lower_core": pd.read_parquet(V1_PRE / "lower_core_components_pre_reference.parquet"),
        "optical": optical,
    }


def load_post_reference_inputs() -> dict[str, pd.DataFrame]:
    return {
        "grounding": pd.read_parquet(V1_POST / "component_family_grounding_post_reference.parquet"),
        "physical_grounding": pd.read_parquet(V1_POST / "physical_region_grounding_post_reference.parquet"),
    }


def parse_frame_set(text: str) -> list[int]:
    return [int(value) for value in str(text).split(";") if str(value)]


def select_pre_reference_pair_cases(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    excluded = data["pair"][
        data["pair"]["segment_id"].isin(TARGET_SEGMENTS.values())
        & data["pair"]["pairing_status"].eq("LOGICALLY_EXCLUDED_PAIRING")
    ].copy()
    rows: list[pd.Series] = []
    for segment_label, segment_id in TARGET_SEGMENTS.items():
        part = excluded[excluded["segment_id"].eq(segment_id)].copy()
        selections: list[tuple[str, pd.DataFrame, str]] = [
            ("A_SUPPORT_1", part[part["common_sar_support_frame_count"].eq(1)], "PRE_REFERENCE_MECHANICAL"),
            ("B_SUPPORT_2", part[part["common_sar_support_frame_count"].eq(2)], "PRE_REFERENCE_MECHANICAL"),
            ("C_SUPPORT_AT_LEAST_5", part[part["common_sar_support_frame_count"].ge(5)], "PRE_REFERENCE_MECHANICAL"),
            ("D_LONGEST_SUPPORT", part[part["common_sar_support_frame_count"].eq(part["common_sar_support_frame_count"].max())], "PRE_REFERENCE_MECHANICAL"),
        ]
        used: set[str] = set()
        for case_kind, candidates, reference_scope in selections:
            if candidates.empty:
                continue
            candidates = candidates.copy()
            candidates["pair_key"] = candidates["family_a"].astype(str) + "|" + candidates["family_b"].astype(str)
            candidates = candidates.sort_values(
                ["common_sar_support_frame_count", "track_a", "track_b", "family_a", "family_b"],
                ascending=[False, True, True, True, True],
            )
            unused = candidates[~candidates["pair_key"].isin(used)]
            choice = (unused if not unused.empty else candidates).iloc[0].copy()
            used.add(str(choice["pair_key"]))
            choice["case_id"] = f"{segment_label}_{case_kind}"
            choice["case_kind"] = case_kind
            choice["segment_label"] = segment_label
            choice["selection_reference_scope"] = reference_scope
            rows.append(choice)
    registry = pd.DataFrame(rows).drop(columns=["pair_key"], errors="ignore")
    return registry


def select_post_reference_pair_cases(
    data: dict[str, pd.DataFrame], grounding: pd.DataFrame
) -> pd.DataFrame:
    excluded = data["pair"][
        data["pair"]["segment_id"].isin(TARGET_SEGMENTS.values())
        & data["pair"]["pairing_status"].eq("LOGICALLY_EXCLUDED_PAIRING")
    ].copy()
    state = grounding.set_index("family_id")["component_grounding_state"].to_dict()
    excluded["family_a_grounding_state"] = excluded["family_a"].map(state).fillna("UNAVAILABLE")
    excluded["family_b_grounding_state"] = excluded["family_b"].map(state).fillna("UNAVAILABLE")
    excluded["likely_family_count_in_pair"] = (
        excluded["family_a_grounding_state"].eq("LIKELY_SUPPORTED_EXPLORATORY").astype(int)
        + excluded["family_b_grounding_state"].eq("LIKELY_SUPPORTED_EXPLORATORY").astype(int)
    )
    rows: list[pd.Series] = []
    for segment_label, segment_id in TARGET_SEGMENTS.items():
        candidates = excluded[
            excluded["segment_id"].eq(segment_id)
            & excluded["likely_family_count_in_pair"].eq(1)
        ].sort_values(
            ["common_sar_support_frame_count", "track_a", "track_b", "family_a", "family_b"],
            ascending=[False, True, True, True, True],
        )
        if candidates.empty:
            continue
        choice = candidates.iloc[0].copy()
        choice["case_id"] = f"{segment_label}_E_LIKELY_VS_EXCLUDED_ALTERNATIVE"
        choice["case_kind"] = "E_LIKELY_VS_EXCLUDED_ALTERNATIVE"
        choice["segment_label"] = segment_label
        choice["selection_reference_scope"] = "POST_REFERENCE_DIAGNOSTIC_SELECTION"
        rows.append(choice)
    return pd.DataFrame(rows)


def extract_selected_memberships(data: dict[str, pd.DataFrame], cases: pd.DataFrame) -> pd.DataFrame:
    selected = set(cases["family_a"].astype(str)) | set(cases["family_b"].astype(str))
    physical_columns = [
        "physical_region_id",
        "frame_uid",
        "theta_min_deg",
        "theta_max_deg",
    ]
    membership = data["membership"][data["membership"]["family_id"].astype(str).isin(selected)].merge(
        data["physical"][physical_columns],
        on="physical_region_id",
        how="left",
        validate="many_to_one",
    )
    columns = [
        "family_id",
        "track_id",
        "frame_index",
        "physical_region_id",
        "frame_uid",
        "region_id",
        "theta_min_deg",
        "theta_max_deg",
        "segment_id",
        "run_id",
    ]
    return membership[columns].sort_values(["segment_id", "track_id", "family_id", "frame_index", "physical_region_id"])


def image_by_timestamp(run_id: str, modality: str, timestamp_ms: int) -> Path | None:
    directory = FRAME_ROOT / modality / run_id
    matches = sorted(directory.glob(f"frame_*_t{timestamp_ms:06d}ms.*"))
    return matches[0] if matches else None


def sar_image(run_id: str, frame: int) -> Path | None:
    matches = sorted((FRAME_ROOT / "sar_pseudocolor" / run_id).glob(f"frame_{frame:06d}_*"))
    return matches[0] if matches else None


def region_mask(row: pd.Series, cache: dict[str, dict[str, np.ndarray]]) -> np.ndarray:
    frame_uid = str(row.frame_uid)
    if frame_uid not in cache:
        cache[frame_uid] = dict(np.load(REGION_MASKS / f"{frame_uid}.npz"))
    label = int(str(row.region_id).rsplit("R", 1)[-1])
    return cache[frame_uid]["Q095"] == label


def relation_from_bounds(a_low: float, a_high: float, b_low: float, b_high: float) -> str:
    if a_high < b_low:
        return "LEFT"
    if b_high < a_low:
        return "RIGHT"
    return "OVERLAP"


def optical_relation(a_low: float, a_high: float, b_low: float, b_high: float) -> str:
    if a_high < b_low:
        return "A_LEFT_OF_B"
    if b_high < a_low:
        return "A_RIGHT_OF_B"
    return "OPTICAL_OVERLAP_OR_UNCERTAIN"


def render_pair_case(
    data: dict[str, pd.DataFrame],
    case: pd.Series,
    memberships: pd.DataFrame,
) -> tuple[Path, list[dict[str, Any]]]:
    frames = parse_frame_set(case.common_sar_support_frame_set)
    track_a = str(case.track_a)
    track_b = str(case.track_b)
    family_a = str(case.family_a)
    family_b = str(case.family_b)
    run_id = str(case.run_id)
    frame_state = data["frame_state"]
    optical = data["optical"]
    physical = data["physical"].set_index("physical_region_id", drop=False)
    rows = max(1, len(frames))
    fig, axes = plt.subplots(rows, 2, figsize=(17, max(5.2, 4.5 * rows)), squeeze=False)
    cache: dict[str, dict[str, np.ndarray]] = {}
    audit_rows: list[dict[str, Any]] = []
    for row_index, frame in enumerate(frames):
        optical_axis = axes[row_index, 0]
        sar_axis = axes[row_index, 1]
        states = frame_state[
            frame_state["run_id"].eq(run_id)
            & frame_state["frame_index"].eq(frame)
            & frame_state["track_id"].astype(str).isin([track_a, track_b])
        ]
        state_lookup = {str(row.track_id): row for row in states.itertuples(index=False)}
        state_a = state_lookup.get(track_a)
        state_b = state_lookup.get(track_b)
        nominal_ts = int(state_a.nominal_optical_timestamp_ms) if state_a is not None else -1
        optical_path = image_by_timestamp(run_id, "optical", nominal_ts) if nominal_ts >= 0 else None
        optical_image = cv2.imread(str(optical_path), cv2.IMREAD_COLOR) if optical_path else None
        if optical_image is not None:
            optical_axis.imshow(cv2.cvtColor(optical_image, cv2.COLOR_BGR2RGB))
            optical_frame = optical[
                optical["run_id"].eq(run_id)
                & optical["timestamp_ms"].eq(nominal_ts)
                & optical["raw_track_fragment_id"].astype(str).isin([track_a, track_b])
            ]
            colors = {track_a: "#00e5ff", track_b: "#ff9800"}
            labels = {track_a: "A", track_b: "B"}
            for item in optical_frame.itertuples(index=False):
                x1, y1 = float(item.bbox_x1), float(item.bbox_y1)
                width = float(item.bbox_x2) - x1
                height = float(item.bbox_y2) - y1
                optical_axis.add_patch(Rectangle((x1, y1), width, height, fill=False, edgecolor=colors[str(item.raw_track_fragment_id)], linewidth=2.3))
                optical_axis.text(x1, max(12, y1 - 8), labels[str(item.raw_track_fragment_id)], color=colors[str(item.raw_track_fragment_id)], fontsize=12, weight="bold")
        if state_a is not None and state_b is not None:
            opt_relation = optical_relation(
                float(state_a.raw_theta_low_deg), float(state_a.raw_theta_high_deg),
                float(state_b.raw_theta_low_deg), float(state_b.raw_theta_high_deg),
            )
            optical_title = (
                f"OPTICAL F{int(state_a.source_timestamp_min_ms)}ms nominal={nominal_ts}ms | {opt_relation}\n"
                f"A raw=[{float(state_a.raw_theta_low_deg):.2f},{float(state_a.raw_theta_high_deg):.2f}]°; "
                f"B raw=[{float(state_b.raw_theta_low_deg):.2f},{float(state_b.raw_theta_high_deg):.2f}]°"
            )
        else:
            opt_relation = "ORDER_UNAVAILABLE"
            optical_title = f"OPTICAL unavailable for SAR F{frame}"
        optical_axis.set_title(optical_title, fontsize=9)
        optical_axis.axis("off")

        sar_path = sar_image(run_id, frame)
        sar = cv2.imread(str(sar_path), cv2.IMREAD_COLOR) if sar_path else None
        sar_relation = "UNAVAILABLE"
        a_bounds = (math.nan, math.nan)
        b_bounds = (math.nan, math.nan)
        shared = False
        if sar is not None:
            sar_axis.imshow(cv2.cvtColor(sar, cv2.COLOR_BGR2RGB))
            a_members = memberships[memberships["family_id"].eq(family_a) & memberships["frame_index"].eq(frame)]
            b_members = memberships[memberships["family_id"].eq(family_b) & memberships["frame_index"].eq(frame)]
            a_ids = set(a_members["physical_region_id"].astype(str))
            b_ids = set(b_members["physical_region_id"].astype(str))
            shared = bool(a_ids & b_ids)
            for physical_id in sorted(a_ids):
                mask = region_mask(physical.loc[physical_id], cache)
                sar_axis.contour(mask.astype(float), levels=[0.5], colors=["#00e5ff"], linewidths=2.1)
            for physical_id in sorted(b_ids):
                mask = region_mask(physical.loc[physical_id], cache)
                sar_axis.contour(mask.astype(float), levels=[0.5], colors=["#ff9800"], linewidths=2.1)
            a_bounds = (float(a_members["theta_min_deg"].min()), float(a_members["theta_max_deg"].max()))
            b_bounds = (float(b_members["theta_min_deg"].min()), float(b_members["theta_max_deg"].max()))
            sar_relation = "SHARED" if shared else relation_from_bounds(*a_bounds, *b_bounds)
        sar_axis.set_title(
            f"SAR F{frame} | {sar_relation}\n"
            f"A theta=[{a_bounds[0]:.2f},{a_bounds[1]:.2f}]°; B theta=[{b_bounds[0]:.2f},{b_bounds[1]:.2f}]°",
            fontsize=9,
        )
        sar_axis.axis("off")
        audit_rows.append(
            {
                "case_id": str(case.case_id),
                "segment_id": str(case.segment_id),
                "run_id": run_id,
                "frame_index": frame,
                "track_a": track_a,
                "track_b": track_b,
                "family_a": family_a,
                "family_b": family_b,
                "nominal_optical_timestamp_ms": nominal_ts if nominal_ts >= 0 else None,
                "optical_relation": opt_relation,
                "family_a_theta_min_deg": a_bounds[0],
                "family_a_theta_max_deg": a_bounds[1],
                "family_b_theta_min_deg": b_bounds[0],
                "family_b_theta_max_deg": b_bounds[1],
                "sar_relation": sar_relation,
                "physical_region_shared": shared,
                "r0_pairing_status": str(case.pairing_status),
            }
        )
    fig.suptitle(
        f"{case.case_id}: why the R0 pair is red\n"
        f"{case.segment_id} | common support={case.common_sar_support_frame_count} frames [{case.common_sar_support_frame_set}]\n"
        f"OPTICAL={case.optical_whole_segment_order}; SAR={case.sar_family_pair_relation_set}; R0={case.pairing_status}\n"
        "cyan=A, orange=B; optical boxes are frozen raw detections; SAR contours are frozen physical q95 regions",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    output = PAIR_FIGURES / f"{case.case_id}.jpg"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, pil_kwargs={"quality": 90, "optimize": True})
    plt.close(fig)
    return output, audit_rows


def build_direct_visual_verification(
    data: dict[str, pd.DataFrame], cases: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    memberships = extract_selected_memberships(data, cases)
    figure_paths: list[str] = []
    frame_rows: list[dict[str, Any]] = []
    for case in cases.itertuples(index=False):
        output, audit = render_pair_case(data, pd.Series(case._asdict()), memberships)
        figure_paths.append(str(output.relative_to(WORKSPACE)).replace("\\", "/"))
        frame_rows.extend(audit)
    cases["figure_path"] = figure_paths
    return cases, memberships, pd.DataFrame(frame_rows)


def build_visual_verdict(cases: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for case in cases.itertuples(index=False):
        support = int(case.common_sar_support_frame_count)
        persistent = str(case.case_kind) in {
            "C_SUPPORT_AT_LEAST_5",
            "D_LONGEST_SUPPORT",
        } or (str(case.case_kind) == "E_LIKELY_VS_EXCLUDED_ALTERNATIVE" and support >= 5)
        rows.append(
            {
                "case_id": str(case.case_id),
                "segment_id": str(case.segment_id),
                "case_kind": str(case.case_kind),
                "selection_reference_scope": str(case.selection_reference_scope),
                "common_sar_support_frame_count": support,
                "common_sar_support_frame_set": str(case.common_sar_support_frame_set),
                "relational_evidence_support_extent": (
                    "PERSISTENT_RELATIONAL_EVIDENCE" if persistent else "LOCAL_RELATIONAL_EVIDENCE"
                ),
                "human_visual_credibility": (
                    "CREDIBLE_PERSISTENT_REVERSE_ORDER"
                    if persistent
                    else "GEOMETRICALLY_CREDIBLE_BUT_TEMPORALLY_LOCAL"
                ),
                "q95_fragmentation_concern": (
                    "PRESENT_BUT_DOES_NOT_REVERSE_PERSISTENT_ORDER"
                    if persistent
                    else "MATERIAL_FOR_EVIDENCE_EXTENT_INTERPRETATION"
                ),
                "human_joint_explanation_verdict": (
                    "YES_RELATIONALLY_INCOMPATIBLE_ACROSS_PERSISTENT_SUPPORT"
                    if persistent
                    else "LOCALLY_INCOMPATIBLE_NOT_EQUAL_TO_PERSISTENT_PROOF"
                ),
                "outcome_tuned_support_threshold_created": False,
                "inspection_state": "CODEX_PERSONALLY_INSPECTED",
                "figure_path": str(case.figure_path),
            }
        )
    return pd.DataFrame(rows)


def build_episode_registry(data: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    burden = data["burden"]
    segments = data["segments"].merge(
        burden[
            [
                "segment_id",
                "N_temporal_joint_worlds",
                "N_possible_joint_worlds",
                "N_excluded_joint_worlds",
                "joint_world_contraction_fraction",
                "active_cross_modal_pair_factor_count",
                "logically_excluded_family_pairing_count",
            ]
        ],
        on="segment_id",
        how="left",
        validate="one_to_one",
    )
    assignments: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    for run_id, run_rows in segments.groupby("run_id"):
        ordered = run_rows.sort_values(["start_sar_frame", "end_sar_frame", "segment_id"])
        groups: list[list[Any]] = []
        current: list[Any] = []
        current_end = -1
        for row in ordered.itertuples(index=False):
            if not current or int(row.start_sar_frame) <= current_end:
                current.append(row)
                current_end = max(current_end, int(row.end_sar_frame))
            else:
                groups.append(current)
                current = [row]
                current_end = int(row.end_sar_frame)
        if current:
            groups.append(current)
        for index, group in enumerate(groups, start=1):
            start = min(int(row.start_sar_frame) for row in group)
            end = max(int(row.end_sar_frame) for row in group)
            episode_id = stable_id("TERGR1EP", run_id, start, end)
            for row in group:
                assignments.append(
                    {
                        "episode_id": episode_id,
                        "episode_index_within_run": index,
                        "segment_id": str(row.segment_id),
                        "run_id": str(run_id),
                        "start_sar_frame": int(row.start_sar_frame),
                        "end_sar_frame": int(row.end_sar_frame),
                        "segment_kind": str(row.segment_kind),
                        "N_excluded_joint_worlds": int(row.N_excluded_joint_worlds),
                        "segment_contracted": bool(row.N_excluded_joint_worlds > 0),
                        "independent_evidence_unit": False,
                        "episode_semantics": "OVERLAPPING_SEGMENT_VIEW_OF_ONE_UNDERLYING_TEMPORAL_EPISODE",
                    }
                )
            episodes.append(
                {
                    "episode_id": episode_id,
                    "run_id": str(run_id),
                    "episode_index_within_run": index,
                    "episode_start_sar_frame": start,
                    "episode_end_sar_frame": end,
                    "episode_frame_span": end - start + 1,
                    "segment_view_count": len(group),
                    "contracted_segment_view_count": sum(int(row.N_excluded_joint_worlds > 0) for row in group),
                    "episode_has_relational_contraction": any(row.N_excluded_joint_worlds > 0 for row in group),
                    "repeated_view_excluded_world_sum_not_independent": sum(
                        int(row.N_excluded_joint_worlds) for row in group
                    ),
                    "segment_ids": ";".join(str(row.segment_id) for row in group),
                    "segment_kinds": set_text({str(row.segment_kind) for row in group}),
                }
            )
    return pd.DataFrame(assignments), pd.DataFrame(episodes)


def evidence_availability_state(
    data: dict[str, pd.DataFrame], segment: Any, boundary_flags: dict[str, bool]
) -> list[dict[str, Any]]:
    segment_id = str(segment.segment_id)
    orders = data["optical_order"][data["optical_order"]["segment_id"].eq(segment_id)]
    relations = data["relations"][data["relations"]["segment_id"].eq(segment_id)]
    burden = data["temporal_burden"][data["temporal_burden"]["segment_id"].eq(segment_id)]
    definite = int(orders["whole_segment_definite_order"].sum()) if not orders.empty else 0
    pair_count = len(orders)
    shared_profiles = int(relations["shared_family_pair_support_count"].gt(0).sum()) if not relations.empty else 0
    lifecycle = int(burden["complete_lifecycle_possible_family_count"].sum()) if not burden.empty else 0
    multi_component = int(burden["lower_core_component_count"].gt(burden["upper_possible_family_count"]).sum())
    if int(segment.track_count) < 2:
        relative_state = "UNAVAILABLE"
    elif definite == pair_count and pair_count > 0:
        relative_state = "OBSERVABLE"
    elif definite > 0:
        relative_state = "PARTIALLY_OBSERVABLE"
    else:
        relative_state = "AMBIGUOUS"
    shared_state = (
        "UNAVAILABLE" if int(segment.track_count) < 2 else
        "OBSERVABLE" if shared_profiles == pair_count and pair_count > 0 else
        "PARTIALLY_OBSERVABLE" if shared_profiles > 0 else
        "UNAVAILABLE"
    )
    boundary_state = "CENSORED" if boundary_flags.get(segment_id, False) else "OBSERVABLE"
    topology_state = "AMBIGUOUS" if str(segment.segment_kind) in {
        "SAR_SPLIT_LIKE_CONTEXT", "SAR_MERGE_LIKE_CONTEXT"
    } else "PARTIALLY_OBSERVABLE"
    rows = [
        ("RELATIVE_ANGULAR_ORDER", relative_state, "RELATIONAL_DISCRIMINATIVE", definite > 0,
         f"{definite}/{pair_count} pair profiles have whole-segment definite raw optical order"),
        ("LIFECYCLE_PERSISTENCE", "OBSERVABLE" if lifecycle > 0 else "PARTIALLY_OBSERVABLE", "STRUCTURING", False,
         f"{lifecycle} complete-lifecycle-possible frozen families; already used in TERG-v1 construction"),
        ("SHARED_RESPONSE_STATE", shared_state, "DESCRIPTIVE", False,
         f"shared SAR physical-region support occurs in {shared_profiles}/{pair_count} relation profiles; no PERSON-state equivalence asserted"),
        ("TOPOLOGY_HYPOTHESIS_SET", topology_state, "DESCRIPTIVE", False,
         "split/merge/deformation remains a compatible SAR response-state hypothesis set"),
        ("BOUNDARY_CENSORING", boundary_state, "DESCRIPTIVE", False,
         "censoring disables morphology authority and preserves boundary-conditioned hypotheses"),
        ("RESPONSE_COMPONENT_SET", "OBSERVABLE" if multi_component > 0 else "PARTIALLY_OBSERVABLE", "STRUCTURING", False,
         "upper families may contain multiple lower-core components and multiple physical regions"),
        ("EXACT_CROSS_MODAL_TIMING", "UNAVAILABLE", "DESCRIPTIVE", False,
         "all frozen timing-authority rows prohibit exact cross-modal order"),
        ("RELATIVE_RANGE_LIKE_ORDER", "UNAVAILABLE", "UNARY_DISCRIMINATIVE", False,
         "optical has no range authority and no reliable cross-modal range-order observable is frozen"),
        ("UNARY_FAMILY_DISCRIMINATION", "UNAVAILABLE", "UNARY_DISCRIMINATIVE", False,
         "TERG-R0 deletes 0 individual families without an anchor"),
    ]
    return [
        {
            "segment_id": segment_id,
            "run_id": str(segment.run_id),
            "evidence_family": name,
            "availability_state": availability,
            "evidence_role": role,
            "activated_for_relational_exclusion": bool(active),
            "availability_basis": reason,
            "weighted_score_used": False,
            "manual_reference_used": False,
        }
        for name, availability, role, active, reason in rows
    ]


def build_evidence_availability(data: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    joined = data["membership"].merge(
        data["physical"][["physical_region_id", "touches_observable_boundary", "has_truncated_support"]],
        on="physical_region_id",
        how="left",
        validate="many_to_one",
    )
    boundary_flags = (
        joined.assign(boundary=lambda x: x["touches_observable_boundary"] | x["has_truncated_support"])
        .groupby("segment_id")["boundary"].any().to_dict()
    )
    rows = [
        item
        for segment in data["segments"].itertuples(index=False)
        for item in evidence_availability_state(data, segment, boundary_flags)
    ]
    availability = pd.DataFrame(rows)
    role_rows = []
    role_definitions = {
        "RELATIVE_ANGULAR_ORDER": ("RELATIONAL_DISCRIMINATIVE", "Only frozen evidence currently producing hard joint exclusions."),
        "LIFECYCLE_PERSISTENCE": ("STRUCTURING", "Builds temporal families; no new conditional deletion."),
        "SHARED_RESPONSE_STATE": ("DESCRIPTIVE", "Observable SAR response sharing, but no stable PERSON-state implication."),
        "TOPOLOGY_HYPOTHESIS_SET": ("DESCRIPTIVE", "Preserves split/merge/deformation alternatives."),
        "BOUNDARY_CENSORING": ("DESCRIPTIVE", "A guard that disables invalid morphology authority."),
        "RESPONSE_COMPONENT_SET": ("STRUCTURING", "Represents persistent core and transient/satellite components inside a family."),
        "EXACT_CROSS_MODAL_TIMING": ("DESCRIPTIVE", "Unavailable; exact temporal ordering is disabled."),
        "RELATIVE_RANGE_LIKE_ORDER": ("UNARY_DISCRIMINATIVE", "Candidate role, but no reliable observable exists."),
        "UNARY_FAMILY_DISCRIMINATION": ("UNARY_DISCRIMINATIVE", "Searched and absent without an anchor."),
        "ANCHOR_CONDITIONED_EXCLUSION": ("RELATIONAL_DISCRIMINATIVE", "Post-reference propagation-capacity diagnostic only."),
    }
    for evidence, (role, conclusion) in role_definitions.items():
        part = availability[availability["evidence_family"].eq(evidence)]
        role_rows.append(
            {
                "evidence_family": evidence,
                "evidence_role": role,
                "observable_segment_count": int(part["availability_state"].eq("OBSERVABLE").sum()),
                "partially_observable_segment_count": int(part["availability_state"].eq("PARTIALLY_OBSERVABLE").sum()),
                "ambiguous_segment_count": int(part["availability_state"].eq("AMBIGUOUS").sum()),
                "censored_segment_count": int(part["availability_state"].eq("CENSORED").sum()),
                "unavailable_segment_count": int(part["availability_state"].eq("UNAVAILABLE").sum()),
                "current_r1_conclusion": conclusion,
                "new_hard_constraint_authorized": evidence == "RELATIVE_ANGULAR_ORDER",
            }
        )
    return availability, pd.DataFrame(role_rows)


def transitive_closure(edges: set[tuple[str, str]]) -> set[tuple[str, str]]:
    reach = set(edges)
    changed = True
    while changed:
        changed = False
        for left, middle in list(reach):
            for source, right in list(reach):
                if middle == source and left != right and (left, right) not in reach:
                    reach.add((left, right))
                    changed = True
    return reach


def build_global_partial_order_audit(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for segment in data["segments"].itertuples(index=False):
        profiles = data["optical_order"][data["optical_order"]["segment_id"].eq(segment.segment_id)]
        edges: set[tuple[str, str]] = set()
        for profile in profiles.itertuples(index=False):
            if profile.whole_segment_optical_order == "A_LEFT_OF_B":
                edges.add((str(profile.track_a), str(profile.track_b)))
            elif profile.whole_segment_optical_order == "A_RIGHT_OF_B":
                edges.add((str(profile.track_b), str(profile.track_a)))
        closure = transitive_closure(edges)
        redundant: set[tuple[str, str]] = set()
        for edge in edges:
            if edge in transitive_closure(edges - {edge}):
                redundant.add(edge)
        rows.append(
            {
                "segment_id": str(segment.segment_id),
                "run_id": str(segment.run_id),
                "track_count": int(segment.track_count),
                "direct_definite_edge_count": len(edges),
                "partial_order_closure_edge_count": len(closure),
                "transitive_edge_added_count": len(closure - edges),
                "redundant_direct_edge_count": len(redundant),
                "irreducible_edge_count": len(edges - redundant),
                "cycle_count": sum(int(left == right) for left, right in closure),
                "direct_edge_set": ";".join(f"{left}<{right}" for left, right in sorted(edges)),
                "redundant_edge_set": ";".join(f"{left}<{right}" for left, right in sorted(redundant)),
                "global_partial_order_new_discrimination": False,
                "interpretation": "SEMANTIC_COMPOSITION_AND_REDUNDANCY_CONTROL_NOT_ADDITIONAL_INFORMATION",
            }
        )
    return pd.DataFrame(rows)


def build_pre_reference_response_component_diagnosis(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    per_frame = (
        data["membership"].groupby(["family_id", "frame_index"])
        .agg(physical_region_count=("physical_region_id", "nunique"), core_component_count=("core_component_id", "nunique"))
        .reset_index()
    )
    stats = per_frame.groupby("family_id").agg(
        observed_frame_count=("frame_index", "nunique"),
        max_physical_regions_per_frame=("physical_region_count", "max"),
        multi_region_frame_count=("physical_region_count", lambda values: int((values > 1).sum())),
        component_set_turnover_frame_count=("core_component_count", lambda values: int((values > 0).sum())),
    ).reset_index()
    result = data["family"].merge(stats, on="family_id", how="left", validate="one_to_one")
    result["family_is_internally_set_valued"] = (
        result["lower_core_component_count"].gt(1)
        | result["max_physical_regions_per_frame"].gt(1)
    )
    result["response_bundle_semantics"] = "UPPER_FAMILY_ALREADY_CONTAINS_SET_VALUED_TEMPORAL_RESPONSE_COMPONENTS"
    result["cross_family_bundle_implemented"] = False
    result["manual_reference_used"] = False
    return result


def target_in_ids(series: pd.Series, target: str) -> pd.Series:
    return series.fillna("").astype(str).str.split(";").apply(lambda values: target in values)


def build_post_reference_representation_diagnosis(
    data: dict[str, pd.DataFrame], post: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    grounding = post["grounding"]
    likely = grounding[grounding["component_grounding_state"].eq("LIKELY_SUPPORTED_EXPLORATORY")].copy()
    frame_stats = (
        data["membership"][data["membership"]["family_id"].isin(likely["family_id"])]
        .groupby(["family_id", "frame_index"])
        .agg(physical_region_count=("physical_region_id", "nunique"), core_component_count=("core_component_id", "nunique"))
        .reset_index()
        .groupby("family_id")
        .agg(
            max_physical_regions_per_frame=("physical_region_count", "max"),
            multi_region_frame_count=("physical_region_count", lambda values: int((values > 1).sum())),
            family_observed_frame_count=("frame_index", "nunique"),
        ).reset_index()
    )
    family_lookup = data["family"].set_index("family_id")
    physical_grounding = post["physical_grounding"]
    rows: list[dict[str, Any]] = []
    for item in likely.itertuples(index=False):
        family_id = str(item.family_id)
        target = str(item.dominant_target_id_offline)
        candidate_family_ids = data["family"][
            data["family"]["segment_id"].eq(item.segment_id)
            & data["family"]["track_id"].eq(item.track_id)
        ]["family_id"].astype(str).tolist()
        membership = data["membership"][data["membership"]["family_id"].isin(candidate_family_ids)].merge(
            physical_grounding[["physical_region_id", "offline_target_ids"]],
            on="physical_region_id",
            how="left",
        )
        membership["supports_target"] = target_in_ids(membership["offline_target_ids"], target)
        target_membership = membership[membership["supports_target"]]
        all_regions = set(target_membership["physical_region_id"].astype(str))
        all_frames = set(target_membership["frame_index"].astype(int))
        likely_membership = target_membership[target_membership["family_id"].astype(str).eq(family_id)]
        likely_regions = set(likely_membership["physical_region_id"].astype(str))
        likely_frames = set(likely_membership["frame_index"].astype(int))
        stat = frame_stats[frame_stats["family_id"].astype(str).eq(family_id)].iloc[0]
        frozen = family_lookup.loc[family_id]
        region_coverage = len(likely_regions) / len(all_regions) if all_regions else math.nan
        frame_coverage = len(likely_frames) / len(all_frames) if all_frames else math.nan
        reference_gap = max(0, int(item.reference_frame_count) - len(all_frames))
        rows.append(
            {
                "family_id": family_id,
                "segment_id": str(item.segment_id),
                "run_id": str(item.run_id),
                "track_id": str(item.track_id),
                "dominant_target_id_offline": target,
                "reference_frame_count": int(item.reference_frame_count),
                "reference_supported_component_frame_count": int(item.reference_supported_component_frame_count),
                "available_reference_supported_frame_count": len(all_frames),
                "likely_family_reference_supported_frame_count": len(likely_frames),
                "likely_family_reference_frame_coverage_fraction": frame_coverage,
                "available_reference_supported_region_count": len(all_regions),
                "likely_family_reference_supported_region_count": len(likely_regions),
                "likely_family_reference_region_coverage_fraction": region_coverage,
                "reference_frame_without_candidate_region_count": reference_gap,
                "lower_core_component_count": int(frozen.lower_core_component_count),
                "optional_edge_count": int(frozen.optional_edge_count),
                "max_physical_regions_per_frame": int(stat.max_physical_regions_per_frame),
                "multi_region_frame_count": int(stat.multi_region_frame_count),
                "family_is_internally_set_valued": bool(
                    frozen.lower_core_component_count > 1 or stat.max_physical_regions_per_frame > 1
                ),
                "cross_family_bundle_required_by_available_reference_support": bool(
                    (not math.isnan(region_coverage) and region_coverage < 1.0)
                    or (not math.isnan(frame_coverage) and frame_coverage < 1.0)
                ),
                "one_track_one_upper_family_verdict": "NOT_FALSIFIED_BY_CURRENT_REFERENCE_SUPPORT",
                "partial_reference_support_interpretation": (
                    "GROUNDING_OR_OBSERVABILITY_GAP_NOT_CROSS_FAMILY_BUNDLE_PROOF"
                    if reference_gap > 0 else "AVAILABLE_REFERENCE_SUPPORT_FULLY_CONTAINED"
                ),
                "runtime_use_allowed": False,
            }
        )
    return pd.DataFrame(rows)


def build_family_geometry(data: dict[str, pd.DataFrame]) -> dict[str, dict[int, tuple[set[str], float, float]]]:
    membership = data["membership"].merge(
        data["physical"][["physical_region_id", "theta_min_deg", "theta_max_deg"]],
        on="physical_region_id", how="left", validate="many_to_one"
    )
    geometry: dict[str, dict[int, tuple[set[str], float, float]]] = {}
    for family_id, family_rows in membership.groupby("family_id"):
        geometry[str(family_id)] = {
            int(frame): (
                set(rows["physical_region_id"].astype(str)),
                float(rows["theta_min_deg"].min()),
                float(rows["theta_max_deg"].max()),
            )
            for frame, rows in family_rows.groupby("frame_index")
        }
    return geometry


def build_shared_transition_diagnostic(
    data: dict[str, pd.DataFrame], post: dict[str, pd.DataFrame], episode_assignments: pd.DataFrame
) -> pd.DataFrame:
    likely = post["grounding"][
        post["grounding"]["component_grounding_state"].eq("LIKELY_SUPPORTED_EXPLORATORY")
    ]
    geometry = build_family_geometry(data)
    episode_lookup = episode_assignments.set_index("segment_id")["episode_id"].to_dict()
    rows: list[dict[str, Any]] = []
    for segment_id, segment_rows in likely.groupby("segment_id"):
        items = list(segment_rows.itertuples(index=False))
        for left, right in itertools.combinations(items, 2):
            common = sorted(set(geometry[str(left.family_id)]) & set(geometry[str(right.family_id)]))
            relations = [
                ("SHARED" if geometry[str(left.family_id)][frame][0] & geometry[str(right.family_id)][frame][0]
                 else relation_from_bounds(
                     geometry[str(left.family_id)][frame][1], geometry[str(left.family_id)][frame][2],
                     geometry[str(right.family_id)][frame][1], geometry[str(right.family_id)][frame][2],
                 ))
                for frame in common
            ]
            transitions = [
                f"{relations[index - 1]}->{relations[index]}"
                for index in range(1, len(relations))
                if relations[index] != relations[index - 1]
            ]
            rows.append(
                {
                    "segment_id": str(segment_id),
                    "episode_id": str(episode_lookup.get(str(segment_id), "UNAVAILABLE")),
                    "run_id": str(left.run_id),
                    "track_a": str(left.track_id),
                    "track_b": str(right.track_id),
                    "family_a": str(left.family_id),
                    "family_b": str(right.family_id),
                    "common_support_frame_count": len(common),
                    "relation_set": set_text(set(relations)),
                    "relation_sequence": ";".join(f"{frame}:{relation}" for frame, relation in zip(common, relations)),
                    "transition_count": len(transitions),
                    "transition_set": set_text(set(transitions)),
                    "shared_to_separated_observed": any(item.startswith("SHARED->") for item in transitions),
                    "separated_to_shared_observed": any(item.endswith("->SHARED") for item in transitions),
                    "new_shared_transition_constraint_authorized": False,
                    "interpretation": "POST_REFERENCE_SEQUENCE_DIAGNOSTIC_NOT_RUNTIME_PERSON_STATE_EQUIVALENCE",
                }
            )
    return pd.DataFrame(rows)


def construct_world_mask(
    segment_id: str, family_status: pd.DataFrame, pair_registry: pd.DataFrame
) -> tuple[list[str], dict[str, list[str]], np.ndarray]:
    segment_families = family_status[family_status["segment_id"].eq(segment_id)]
    tracks = sorted(segment_families["track_id"].astype(str).unique())
    domains = {
        track: sorted(segment_families[segment_families["track_id"].astype(str).eq(track)]["family_id"].astype(str))
        for track in tracks
    }
    mask = np.ones(tuple(len(domains[track]) for track in tracks), dtype=bool)
    segment_pairs = pair_registry[pair_registry["segment_id"].eq(segment_id)]
    for (track_a, track_b), rows in segment_pairs.groupby(["track_a", "track_b"]):
        track_a = str(track_a)
        track_b = str(track_b)
        index_a = {family: index for index, family in enumerate(domains[track_a])}
        index_b = {family: index for index, family in enumerate(domains[track_b])}
        matrix = np.ones((len(index_a), len(index_b)), dtype=bool)
        for row in rows.itertuples(index=False):
            matrix[index_a[str(row.family_a)], index_b[str(row.family_b)]] = row.pairing_status != "LOGICALLY_EXCLUDED_PAIRING"
        axis_a = tracks.index(track_a)
        axis_b = tracks.index(track_b)
        shape_a = [1] * len(tracks)
        shape_b = [1] * len(tracks)
        shape_a[axis_a] = len(index_a)
        shape_b[axis_b] = len(index_b)
        mask &= matrix[
            np.arange(len(index_a)).reshape(shape_a),
            np.arange(len(index_b)).reshape(shape_b),
        ]
    return tracks, domains, mask


def conditioned_domain_counts(
    tracks: list[str], domains: dict[str, list[str]], mask: np.ndarray, anchors: dict[str, str]
) -> tuple[int, dict[str, int]]:
    conditioned = mask.copy()
    for track, family in anchors.items():
        keep = np.zeros(len(domains[track]), dtype=bool)
        keep[domains[track].index(family)] = True
        shape = [1] * len(tracks)
        shape[tracks.index(track)] = len(keep)
        conditioned &= keep.reshape(shape)
    counts: dict[str, int] = {}
    for axis, track in enumerate(tracks):
        other_axes = tuple(index for index in range(len(tracks)) if index != axis)
        marginal = conditioned.any(axis=other_axes) if other_axes else conditioned
        counts[track] = int(np.asarray(marginal).sum())
    return int(conditioned.sum(dtype=np.int64)), counts


def build_anchor_propagation(
    data: dict[str, pd.DataFrame], post: dict[str, pd.DataFrame], episode_assignments: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    likely = post["grounding"][
        post["grounding"]["component_grounding_state"].eq("LIKELY_SUPPORTED_EXPLORATORY")
    ]
    unique = (
        likely.groupby(["segment_id", "track_id"])
        .filter(lambda rows: len(rows) == 1)
        .set_index(["segment_id", "track_id"])["family_id"].astype(str).to_dict()
    )
    episode_lookup = episode_assignments.set_index("segment_id")["episode_id"].to_dict()
    zero_rows: list[dict[str, Any]] = []
    one_rows: list[dict[str, Any]] = []
    two_rows: list[dict[str, Any]] = []
    for segment_id in sorted(data["family_status"]["segment_id"].astype(str).unique()):
        tracks, domains, mask = construct_world_mask(segment_id, data["family_status"], data["pair"])
        base_worlds, base_counts = conditioned_domain_counts(tracks, domains, mask, {})
        episode_id = str(episode_lookup.get(segment_id, "UNAVAILABLE"))
        zero_rows.append(
            {
                "segment_id": segment_id,
                "episode_id": episode_id,
                "anchor_count": 0,
                "r0_possible_world_count": base_worlds,
                "family_domain_count_before": sum(base_counts.values()),
                "family_domain_count_after": sum(base_counts.values()),
                "other_track_family_deleted_count": 0,
                "anchor_source": "NO_ANCHOR",
                "runtime_result": True,
            }
        )
        anchors = {track: unique[(segment_id, track)] for track in tracks if (segment_id, track) in unique}
        for track, family in anchors.items():
            worlds, counts = conditioned_domain_counts(tracks, domains, mask, {track: family})
            other_tracks = [value for value in tracks if value != track]
            one_rows.append(
                {
                    "segment_id": segment_id,
                    "episode_id": episode_id,
                    "anchor_track": track,
                    "anchor_family": family,
                    "anchor_source": "OFFLINE_EVALUATION_REFERENCE",
                    "r0_possible_world_count_before_anchor": base_worlds,
                    "anchor_conditioned_world_count": worlds,
                    "other_track_family_domain_count_before": sum(base_counts[value] for value in other_tracks),
                    "other_track_family_domain_count_after": sum(counts[value] for value in other_tracks),
                    "other_track_family_deleted_count": sum(base_counts[value] - counts[value] for value in other_tracks),
                    "per_track_domain_transition": ";".join(
                        f"{value}:{base_counts[value]}->{counts[value]}" for value in tracks
                    ),
                    "all_available_other_likely_families_retained": all(
                        counts[value] > 0 for value in other_tracks if (segment_id, value) in unique
                    ),
                    "runtime_result": False,
                    "best_anchor_selected": False,
                    "diagnostic_semantics": "PROPAGATION_CAPACITY_DIAGNOSTIC",
                }
            )
        for track_a, track_b in itertools.combinations(sorted(anchors), 2):
            anchor_pair = {track_a: anchors[track_a], track_b: anchors[track_b]}
            worlds, counts = conditioned_domain_counts(tracks, domains, mask, anchor_pair)
            other_tracks = [value for value in tracks if value not in anchor_pair]
            two_rows.append(
                {
                    "segment_id": segment_id,
                    "episode_id": episode_id,
                    "anchor_track_a": track_a,
                    "anchor_family_a": anchors[track_a],
                    "anchor_track_b": track_b,
                    "anchor_family_b": anchors[track_b],
                    "anchor_source": "OFFLINE_EVALUATION_REFERENCE",
                    "r0_possible_world_count_before_anchor": base_worlds,
                    "anchor_conditioned_world_count": worlds,
                    "other_track_family_domain_count_before": sum(base_counts[value] for value in other_tracks),
                    "other_track_family_domain_count_after": sum(counts[value] for value in other_tracks),
                    "other_track_family_deleted_count": sum(base_counts[value] - counts[value] for value in other_tracks),
                    "per_track_domain_transition": ";".join(
                        f"{value}:{base_counts[value]}->{counts[value]}" for value in tracks
                    ),
                    "all_available_other_likely_families_retained": all(
                        counts[value] > 0 for value in other_tracks if (segment_id, value) in unique
                    ),
                    "runtime_result": False,
                    "best_anchor_pair_selected": False,
                    "diagnostic_semantics": "PROPAGATION_CAPACITY_DIAGNOSTIC",
                }
            )
    source_registry = pd.DataFrame(
        [
            {
                "anchor_source_class": "RUNTIME_LEGAL_PHYSICAL_OR_GEOMETRY_ANCHOR",
                "available_anchor_count": 0,
                "runtime_use_allowed": True,
                "current_state": "UNAVAILABLE_IN_FROZEN_INTERFACE",
            },
            {
                "anchor_source_class": "SPARSE_MANUAL_DEVELOPMENT_ANCHOR",
                "available_anchor_count": 0,
                "runtime_use_allowed": False,
                "current_state": "NOT_PROVIDED_AND_NOT_SYNTHESIZED",
            },
            {
                "anchor_source_class": "OFFLINE_EVALUATION_REFERENCE",
                "available_anchor_count": len(unique),
                "runtime_use_allowed": False,
                "current_state": "COUNTERFACTUAL_PROPAGATION_CAPACITY_ONLY",
            },
        ]
    )
    return pd.DataFrame(zero_rows), pd.DataFrame(one_rows), pd.DataFrame(two_rows), source_registry


def render_phase_a_summary(verdict: pd.DataFrame) -> Path:
    SUMMARY_FIGURES.mkdir(parents=True, exist_ok=True)
    ordered = verdict.sort_values(["segment_id", "case_kind"])
    colors = [
        "#2e7d32" if value == "PERSISTENT_RELATIONAL_EVIDENCE" else "#f9a825"
        for value in ordered["relational_evidence_support_extent"]
    ]
    fig, axis = plt.subplots(figsize=(13, 6.5))
    labels = [str(value).replace("five_track_", "5T-").replace("strongest_", "4T-") for value in ordered["case_id"]]
    axis.barh(labels, ordered["common_sar_support_frame_count"], color=colors)
    axis.set_xlabel("common SAR support frames (provenance, not an activation threshold)")
    axis.set_title("Direct real-image verification: local versus persistent relational evidence")
    for index, value in enumerate(ordered["common_sar_support_frame_count"]):
        axis.text(float(value) + 0.1, index, str(int(value)), va="center")
    axis.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    output = SUMMARY_FIGURES / "01_phase_a_relational_support_extent.png"
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def render_episode_timeline(assignments: pd.DataFrame, episodes: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(3, 1, figsize=(15, 8), sharex=False)
    for axis, run_id in zip(axes, ["R01ZF", "R02ZF", "R03ZF"]):
        part = assignments[assignments["run_id"].eq(run_id)].sort_values(["start_sar_frame", "end_sar_frame"])
        for index, row in enumerate(part.itertuples(index=False)):
            color = "#d32f2f" if row.segment_contracted else "#90a4ae"
            axis.plot([row.start_sar_frame, row.end_sar_frame], [index, index], color=color, linewidth=6, solid_capstyle="butt")
        episode = episodes[episodes["run_id"].eq(run_id)]
        for row in episode.itertuples(index=False):
            axis.axvspan(row.episode_start_sar_frame, row.episode_end_sar_frame, color="#1565c0", alpha=0.06)
        axis.set_title(f"{run_id}: {len(part)} segment views; red = R0 contraction")
        axis.set_ylabel("segment view")
        axis.grid(axis="x", alpha=0.2)
    axes[-1].set_xlabel("SAR frame")
    fig.suptitle("Episode-aware reinterpretation: overlapping segments are repeated views, not independent successes")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    output = SUMMARY_FIGURES / "02_episode_aware_r0_timeline.png"
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def render_evidence_heatmap(availability: pd.DataFrame) -> Path:
    code = {"UNAVAILABLE": 0, "CENSORED": 1, "AMBIGUOUS": 2, "PARTIALLY_OBSERVABLE": 3, "OBSERVABLE": 4}
    segment_order = (
        availability[["segment_id", "run_id"]].drop_duplicates()
        .sort_values(["run_id", "segment_id"])["segment_id"].tolist()
    )
    matrix = np.array([
        [
            code[str(availability[
                availability["segment_id"].eq(segment) & availability["evidence_family"].eq(evidence)
            ]["availability_state"].iloc[0])]
            for evidence in EVIDENCE_ORDER
        ]
        for segment in segment_order
    ])
    fig, axis = plt.subplots(figsize=(15, 11))
    image_plot = axis.imshow(matrix, aspect="auto", cmap="viridis", vmin=0, vmax=4)
    axis.set_xticks(range(len(EVIDENCE_ORDER)), [value.replace("_", "\n") for value in EVIDENCE_ORDER], rotation=35, ha="right")
    axis.set_yticks(range(len(segment_order)), [value.replace("TERGS_", "")[:8] for value in segment_order], fontsize=7)
    axis.set_title("Evidence availability is a state, not a confidence score")
    colorbar = fig.colorbar(image_plot, ax=axis, fraction=0.025, pad=0.02)
    colorbar.set_ticks(list(code.values()))
    colorbar.set_ticklabels(list(code.keys()))
    colorbar.ax.tick_params(labelsize=8)
    fig.tight_layout()
    output = SUMMARY_FIGURES / "03_evidence_availability_state_map.png"
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def render_anchor_propagation(one_anchor: pd.DataFrame, two_anchor: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    for axis, table, label, color in [
        (axes[0], one_anchor, "1 offline-reference anchor", "#1976d2"),
        (axes[1], two_anchor, "2 offline-reference anchors", "#7b1fa2"),
    ]:
        counts = table["other_track_family_deleted_count"].value_counts().sort_index()
        axis.bar(counts.index.astype(str), counts.values, color=color)
        axis.set_title(label)
        axis.set_xlabel("other-track family domains deleted")
        axis.set_ylabel("all reported scenarios")
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle("Anchor-conditioned propagation capacity: all anchor scenarios, no best-set selection")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    output = SUMMARY_FIGURES / "04_anchor_conditioned_domain_propagation.png"
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def render_representation_diagnosis(representation: pd.DataFrame) -> Path:
    values = [
        len(representation),
        int(representation["family_is_internally_set_valued"].sum()),
        int(representation["multi_region_frame_count"].gt(0).sum()),
        int(representation["reference_frame_without_candidate_region_count"].gt(0).sum()),
        int(representation["cross_family_bundle_required_by_available_reference_support"].sum()),
    ]
    labels = ["likely families", "internally set-valued", "multi-region frames", "reference gaps", "cross-family bundle required"]
    colors = ["#455a64", "#00897b", "#43a047", "#fb8c00", "#c62828"]
    fig, axis = plt.subplots(figsize=(11, 5.5))
    bars = axis.bar(labels, values, color=colors)
    axis.bar_label(bars)
    axis.set_title("One-track-one-upper-family diagnosis: current family already carries component sets")
    axis.set_ylabel("post-reference diagnostic count")
    axis.tick_params(axis="x", rotation=20)
    axis.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    output = SUMMARY_FIGURES / "05_response_component_representation_diagnosis.png"
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def short_track(track: str) -> str:
    return str(track).rsplit("_", 1)[-1].replace("PERSON", "P")


def render_partial_order_graph(partial_order: pd.DataFrame) -> Path:
    row = partial_order[partial_order["segment_id"].eq(TARGET_SEGMENTS["five_track"])].iloc[0]
    edges = [tuple(item.split("<", 1)) for item in str(row.direct_edge_set).split(";") if item]
    redundant = {tuple(item.split("<", 1)) for item in str(row.redundant_edge_set).split(";") if item}
    tracks = sorted({value for edge in edges for value in edge})
    incoming = {track: 0 for track in tracks}
    for _, right in edges:
        incoming[right] += 1
    remaining = set(tracks)
    order: list[str] = []
    while remaining:
        ready = sorted(track for track in remaining if all(right != track or left not in remaining for left, right in edges))
        if not ready:
            ready = sorted(remaining)
        order.extend(ready)
        remaining -= set(ready)
    positions = {track: (index, 0.35 * (index % 2)) for index, track in enumerate(order)}
    fig, axis = plt.subplots(figsize=(13, 4.5))
    for left, right in edges:
        x1, y1 = positions[left]
        x2, y2 = positions[right]
        axis.annotate(
            "", xy=(x2 - 0.12, y2), xytext=(x1 + 0.12, y1),
            arrowprops={"arrowstyle": "->", "lw": 1.4 if (left, right) in redundant else 2.8,
                        "color": "#9e9e9e" if (left, right) in redundant else "#1565c0",
                        "linestyle": "--" if (left, right) in redundant else "-"},
        )
    for track, (x, y) in positions.items():
        axis.scatter([x], [y], s=1800, color="#e3f2fd", edgecolor="#1565c0", linewidth=2, zorder=3)
        axis.text(x, y, short_track(track), ha="center", va="center", weight="bold", zorder=4)
    axis.set_title("Five-track optical global partial order: blue = irreducible, dashed = redundant pair fact")
    axis.text(0.01, 0.02, "No cycle; no additional transitive edge beyond frozen pairwise facts", transform=axis.transAxes)
    axis.set_xlim(-0.8, max(positions.values())[0] + 0.8)
    axis.set_ylim(-0.6, 0.9)
    axis.axis("off")
    fig.tight_layout()
    output = SUMMARY_FIGURES / "06_five_track_global_partial_order.png"
    fig.savefig(output, dpi=180)
    plt.close(fig)
    return output


def freeze_pre_reference(paths: list[Path], input_hashes: dict[str, str]) -> None:
    write_json(PRE / "frozen_terg_v1_r0_input_hashes.json", input_hashes)
    rows = []
    for path in sorted(set(paths + [PRE / "frozen_terg_v1_r0_input_hashes.json"])):
        rows.append(
            {
                "relative_path": str(path.relative_to(OUTPUT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    pd.DataFrame(rows).to_csv(PRE / "pre_reference_hash_manifest.csv", index=False, encoding="utf-8-sig")
    write_json(
        PRE / "pre_reference_freeze_summary.json",
        {
            "pre_reference_artifact_count": len(rows),
            "manual_reference_loaded_before_freeze": False,
            "post_reference_grounding_loaded_before_freeze": False,
            "r04zf_accessed": False,
            "weighted_score_used": False,
            "support_threshold_tuned": False,
            "relative_order_primitive_visual_verdict": "PERSISTENT_RELATIONAL_EVIDENCE_CREDIBLE",
        },
    )


def write_reports(
    phase_verdict: pd.DataFrame,
    episodes: pd.DataFrame,
    availability: pd.DataFrame,
    roles: pd.DataFrame,
    partial_order: pd.DataFrame,
    representation: pd.DataFrame,
    shared_transition: pd.DataFrame,
    one_anchor: pd.DataFrame,
    two_anchor: pd.DataFrame,
    anchor_sources: pd.DataFrame,
) -> dict[str, Any]:
    persistent_count = int(phase_verdict["relational_evidence_support_extent"].eq("PERSISTENT_RELATIONAL_EVIDENCE").sum())
    contracted_episodes = int(episodes["episode_has_relational_contraction"].sum())
    one_effective = one_anchor[one_anchor["other_track_family_deleted_count"].gt(0)]
    two_effective = two_anchor[two_anchor["other_track_family_deleted_count"].gt(0)]
    representation_required = int(representation["cross_family_bundle_required_by_available_reference_support"].sum())
    shared_transitions = int(
        (shared_transition["shared_to_separated_observed"] | shared_transition["separated_to_shared_observed"]).sum()
    )
    summary = {
        "phase_a_visual_case_count": int(len(phase_verdict)),
        "persistent_relational_evidence_case_count": persistent_count,
        "relative_order_primitive_retained": True,
        "underlying_temporal_episode_count": int(len(episodes)),
        "episode_with_relational_contraction_count": contracted_episodes,
        "contracted_segment_view_count": int(episodes["contracted_segment_view_count"].sum()),
        "global_partial_order_direct_edge_count": int(partial_order["direct_definite_edge_count"].sum()),
        "global_partial_order_transitive_edge_added_count": int(partial_order["transitive_edge_added_count"].sum()),
        "global_partial_order_redundant_direct_edge_count": int(partial_order["redundant_direct_edge_count"].sum()),
        "global_partial_order_cycle_count": int(partial_order["cycle_count"].sum()),
        "likely_supported_family_count": int(len(representation)),
        "internally_set_valued_likely_family_count": int(representation["family_is_internally_set_valued"].sum()),
        "likely_family_with_multi_region_frame_count": int(representation["multi_region_frame_count"].gt(0).sum()),
        "cross_family_bundle_required_case_count": representation_required,
        "reference_grounding_or_observability_gap_case_count": int(
            representation["reference_frame_without_candidate_region_count"].gt(0).sum()
        ),
        "shared_transition_observed_count": shared_transitions,
        "one_anchor_scenario_count": int(len(one_anchor)),
        "one_anchor_other_domain_contraction_scenario_count": int(len(one_effective)),
        "one_anchor_contracted_segment_view_count": int(one_effective["segment_id"].nunique()),
        "one_anchor_contracted_episode_count": int(one_effective["episode_id"].nunique()),
        "one_anchor_max_other_family_deleted_count": int(one_anchor["other_track_family_deleted_count"].max()),
        "two_anchor_scenario_count": int(len(two_anchor)),
        "two_anchor_other_domain_contraction_scenario_count": int(len(two_effective)),
        "two_anchor_contracted_segment_view_count": int(two_effective["segment_id"].nunique()),
        "two_anchor_contracted_episode_count": int(two_effective["episode_id"].nunique()),
        "two_anchor_max_other_family_deleted_count": int(two_anchor["other_track_family_deleted_count"].max()),
        "all_other_likely_families_retained_under_one_anchor": bool(one_anchor["all_available_other_likely_families_retained"].all()),
        "all_other_likely_families_retained_under_two_anchors": bool(two_anchor["all_available_other_likely_families_retained"].all()),
        "runtime_legal_anchor_count": int(anchor_sources.loc[
            anchor_sources["anchor_source_class"].eq("RUNTIME_LEGAL_PHYSICAL_OR_GEOMETRY_ANCHOR"), "available_anchor_count"
        ].iloc[0]),
        "new_unary_discrimination_established": False,
        "new_shared_transition_discrimination_established": False,
        "cross_family_response_bundle_requirement_established": False,
        "final_route": FINAL_ROUTE,
        "terg_v1_modified": False,
        "terg_r0_modified": False,
        "r04zf_accessed": False,
        "independent_confirmation_entered": False,
    }
    write_json(OUTPUT / "terg_r1_summary.json", summary)

    report = f"""# TERG-R1 自适应证据激活与关系组合：科学报告

## 最直接的结论

最终路线：`{FINAL_ROUTE}`。

现在的问题**不是 optical+SAR 完全没有信息**。真实图像已经证明 relative angular order 是可信的关系信息；冻结 R0 也证明它能排除联合解释，并且在给定一个绝对 family anchor 后，确实能向其他 PERSON domain 传播。

但当前仍缺少一个 runtime-legal、来源清楚的绝对锚点，把“相对次序网络”落到具体 SAR response family。除此之外，lifecycle、component turnover、shared/topology、boundary 与 timing 在当前数据中大多是 structuring、descriptive 或 unavailable evidence，尚未形成新的、跨独立 episode 稳定的 family deletion。因而当前瓶颈首先是 `GROUNDING_LIMITATION + OBSERVABILITY_LIMITATION`，其次才是机制未充分利用；不是已经证实的 fundamental ambiguity，也不是已经证实的 cross-family bundle representation failure。

## 1. excluded pair 现实核验

共人工核验 {len(phase_verdict)} 个真实 optical/SAR pack，其中 {persistent_count} 个为 `PERSISTENT_RELATIONAL_EVIDENCE`。1-frame 与 2-frame 案例的反向几何在图上成立，但属于 local evidence，q95 fragmentation 对其时间证据范围有实质影响；长支持案例在完整 support frames 上持续呈现反向次序，因此 relative-order primitive 保留。

没有设置 `support >= N` 的运行阈值。support count、temporal span 与 persistence 只作为 provenance。

![Phase-A support extent](figures/mechanism_diagnostics/01_phase_a_relational_support_extent.png)

下列逐帧图直接展示“红格为什么红”：

![Strongest persistent case](figures/excluded_pair_direct_verification/strongest_D_LONGEST_SUPPORT.jpg)

![Five-track persistent case](figures/excluded_pair_direct_verification/five_track_D_LONGEST_SUPPORT.jpg)

![Five-track likely versus excluded alternative](figures/excluded_pair_direct_verification/five_track_E_LIKELY_VS_EXCLUDED_ALTERNATIVE.jpg)

## 2. episode-aware 的 R0 重新解释

38 个 segment views 聚成 {len(episodes)} 个 overlapping temporal episodes：R01ZF、R02ZF、R03ZF 各 1 个。R0 的 15 个 contracted segments 全部属于同一个 R02ZF episode；1BB7 与 CAAB 是同一证据窗口的重复 view，不能再表述为独立成功。

因此更诚实的分母是：`1/{len(episodes)} episodes show relational contraction`，而不是“15 次独立收缩”。

![Episode-aware timeline](figures/mechanism_diagnostics/02_episode_aware_r0_timeline.png)

## 3. evidence availability 与作用分类

availability 逐 segment 记录为 `OBSERVABLE / PARTIALLY_OBSERVABLE / AMBIGUOUS / CENSORED / UNAVAILABLE`，没有统一 confidence score。

- relative angular order：当前唯一 `RELATIONAL_DISCRIMINATIVE` hard primitive；
- lifecycle persistence：`STRUCTURING`，已经构造 TERG-v1 family；
- response component set：`STRUCTURING`，表达 persistent core 与 transient/satellite components；
- shared response、topology、boundary：目前为 `DESCRIPTIVE` 或 guard；
- exact cross-modal timing：3 个 run 全部 `UNAVAILABLE`；
- relative range-like order：没有可靠 observable；
- unary family discrimination：0，未建立。

![Evidence availability](figures/mechanism_diagnostics/03_evidence_availability_state_map.png)

## 4. global partial order

全部 segment 的 optical definite-order graph 共 {summary['global_partial_order_direct_edge_count']} 条 direct edges，0 个 cycle；transitive closure 没有新增冻结 pairwise facts 之外的 edge，但发现 {summary['global_partial_order_redundant_direct_edge_count']} 条 redundant direct facts。它适合作为一致性表达和证据去重，不产生新的信息或单 family deletion。

![Five-track partial order](figures/mechanism_diagnostics/06_five_track_global_partial_order.png)

## 5. shared transition 探索

post-reference likely family pairs 中没有出现可复核的 `SHARED→SEPARATED` 或 `SEPARATED→SHARED`。仅有两个 RIGHT/OVERLAP 波动序列，且都属于同一 R02ZF episode。当前不能把 shared transition 激活成 hard constraint，更不能把 SAR split/merge 写成 PERSON separation/merge。

## 6. one-track-one-family 是否被推翻

没有。

{len(representation)}/{len(representation)} 个 likely upper families 都已经包含多个 lower-core response components；{summary['likely_family_with_multi_region_frame_count']}/{len(representation)} 个还在至少一帧包含多个 physical regions。对当前 post-reference 可支持区域，唯一 likely family 的 frame coverage 与 region coverage 都为完整覆盖，跨两个 upper families 的 bundle requirement 为 {representation_required}。

有 {summary['reference_grounding_or_observability_gap_case_count']} 个 family 的 reference frames 多于当前 candidate-region 可支持 frames，这更像 grounding/observability gap，不能偷换为“需要第二个 family”。所以当前更精确的结论是：TERG-v1 upper family 本身已经是 set-valued temporal response bundle；`X_i=f_i` 的 upper-family选择尚未被现实证据推翻。

![Representation diagnosis](figures/mechanism_diagnostics/05_response_component_representation_diagnosis.png)

## 7. anchor-conditioned propagation capacity

只使用 unique `LIKELY_SUPPORTED_EXPLORATORY` family 做 `OFFLINE_EVALUATION_REFERENCE` counterfactual anchor，不把它当 runtime result，也不搜索“最佳 anchor set”。

- 0 anchor：R0 删除 0 个 individual family；
- 1 anchor：报告全部 {len(one_anchor)} 个场景，{len(one_effective)} 个场景删除其他 track family，覆盖 {one_effective['segment_id'].nunique()} 个 segment views、但仅 {one_effective['episode_id'].nunique()} 个 episode，最多删除 {summary['one_anchor_max_other_family_deleted_count']} 个；
- 2 anchors：报告全部 {len(two_anchor)} 个场景，{len(two_effective)} 个场景产生其他-domain contraction，覆盖 {two_effective['segment_id'].nunique()} 个 views、仍仅 {two_effective['episode_id'].nunique()} 个 episode，最多删除 {summary['two_anchor_max_other_family_deleted_count']} 个；
- 所有可用 other-track likely families 均保留。

这证明 relational network 不是完全松散，但 propagation 较窄，且只在同一 episode 得到支持。

![Anchor propagation](figures/mechanism_diagnostics/04_anchor_conditioned_domain_propagation.png)

## 8. 信息够不够：五类限制分解

| 限制 | 当前结论 | 直接依据 |
|---|---|---|
| `MECHANISM_UNDERUTILIZATION` | PRESENT_BUT_LIMITED | partial-order 可去重；anchor 后有窄传播；没有新 unary/shared-transition hard evidence |
| `REPRESENTATION_LIMITATION` | NOT_ESTABLISHED | likely family 已内部集合值；0 个 cross-family bundle-required case |
| `OBSERVABILITY_LIMITATION` | PRESENT | PERSON023 sparse；exact timing unavailable；optical 不提供 range authority |
| `GROUNDING_LIMITATION` | DOMINANT | runtime-legal anchor 数为 0；post-reference anchor 才触发 domain deletion |
| `FUNDAMENTAL_AMBIGUITY` | REMAINS_LOCALLY_NOT_PROVEN_GLOBAL | shared/overlap/deformation 仍有多解释，但当前不能证明全部 sensor information 根本无解 |

## 9. 需要的下一物理接口

不是再造一个 weighted score。最小缺口是一个来源清楚、runtime-legal 的局部绝对锚点，例如经过独立标定的 camera–SAR absolute geometry/range association，或其他能合法确认一个 SAR response family 与一个 optical hypothesis 对应的稀疏物理观测。它必须与 manual development anchor、offline reference 严格分开。

本轮到此停止：不进入 R04ZF、independent confirmation、P2、final center 或 final box。
"""
    (OUTPUT / "TERG_R1_SCIENTIFIC_REPORT.md").write_text(report, encoding="utf-8")

    specification = f"""# TERG-R1 Frozen Diagnostic Specification

- Final route: `{FINAL_ROUTE}`.
- Frozen inputs: TERG-v1 and TERG-R0, byte-checked before and after the run.
- Active runtime-legal hard primitive: persistent or local relative-order contradiction with support extent retained as provenance; no support threshold.
- Episode unit: overlapping segment views are grouped into one underlying temporal episode.
- Evidence activation: categorical availability state, never a weighted score.
- Explanation representation finding: upper family is already an internally set-valued temporal response component set; cross-family bundle requirement not established.
- Anchor study: exact frozen-R0 world/domain conditioning for every 0/1/2-anchor scenario; post-reference anchors are counterfactual capacity diagnostics only.
- Global partial order: consistency and redundancy representation, not a new assignment mechanism.
- Shared transition: no hard constraint authorized.
- Forbidden and unused: R04ZF, independent confirmation, learned fusion, threshold tuning, Hungarian, tracker, P2, final center, final box.
"""
    (OUTPUT / "TERG_R1_FROZEN_DIAGNOSTIC_SPECIFICATION.md").write_text(specification, encoding="utf-8")

    ledger = f"""# TERG-R1 Issue / Counterexample / Root-Cause Ledger

| Item | Evidence | Classification | Resolution |
|---|---|---|---|
| 1-frame exclusions are treated like persistent evidence | Direct case packs show correct reverse geometry but sparse q95 support | Provenance overclaim | Record `LOCAL_RELATIONAL_EVIDENCE`; do not tune a frame threshold |
| Long-support reverse order may be a matrix artifact | F487-F494 real imagery stays reverse in every common-support frame | Primitive verified | Retain relative-order contradiction |
| 15 contracted segments imply 15 independent successes | All 15 belong to one R02ZF overlap episode | Repeated-evidence overcount | Report {contracted_episodes}/{len(episodes)} contracted episodes |
| Global partial order will add new constraints | 0 transitive edges added; {summary['global_partial_order_redundant_direct_edge_count']} direct edges are redundant | Representation improvement only | Use graph for consistency/deduplication |
| Shared transition is discriminative | 0 shared-to-separated/separated-to-shared likely sequences | Negative candidate result | Keep shared descriptive/permissive |
| One-track-one-family is already false | All target-supported candidate regions remain inside one likely upper family | Hypothesis not confirmed | Do not implement arbitrary family subsets |
| Response component turnover is absent | 79/79 likely families contain multiple lower-core components; 26/79 have multi-region frames | Real internal adaptivity | Treat upper family as a set-valued response envelope |
| Anchor propagation is a runtime result | Only offline reference provides anchors; runtime-legal count is 0 | Leakage boundary | Report only `PROPAGATION_CAPACITY_DIAGNOSTIC` |
| Current information is fundamentally insufficient | Relative-order and anchor-conditioned deletion are real | Overbroad negative claim | Diagnose dominant grounding/absolute-anchor gap |
"""
    (OUTPUT / "TERG_R1_ISSUE_COUNTEREXAMPLE_ROOT_CAUSE_LEDGER.md").write_text(ledger, encoding="utf-8")
    return summary


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    initial_hashes = frozen_input_hashes()
    data = load_pre_reference_inputs()
    pre_cases = select_pre_reference_pair_cases(data)
    pre_cases, pre_memberships, pre_frame_audit = build_direct_visual_verification(data, pre_cases)
    write_table(pre_cases, PRE / "excluded_pair_visual_case_registry_pre_reference")
    write_table(pre_memberships, PRE / "selected_excluded_pair_family_memberships_pre_reference")
    write_table(pre_frame_audit, PRE / "excluded_pair_frame_relation_audit_pre_reference")

    episode_assignments, episodes = build_episode_registry(data)
    availability, roles = build_evidence_availability(data)
    partial_order = build_global_partial_order_audit(data)
    pre_components = build_pre_reference_response_component_diagnosis(data)
    pre_tables = {
        "episode_assignment_pre_reference": episode_assignments,
        "underlying_temporal_episode_registry_pre_reference": episodes,
        "evidence_availability_map_pre_reference": availability,
        "evidence_role_registry_pre_reference": roles,
        "global_partial_order_audit_pre_reference": partial_order,
        "response_component_family_diagnosis_pre_reference": pre_components,
    }
    pre_paths: list[Path] = [
        PRE / "excluded_pair_visual_case_registry_pre_reference.parquet",
        PRE / "excluded_pair_visual_case_registry_pre_reference.csv",
        PRE / "selected_excluded_pair_family_memberships_pre_reference.parquet",
        PRE / "selected_excluded_pair_family_memberships_pre_reference.csv",
        PRE / "excluded_pair_frame_relation_audit_pre_reference.parquet",
        PRE / "excluded_pair_frame_relation_audit_pre_reference.csv",
    ]
    for name, table in pre_tables.items():
        write_table(table, PRE / name)
        pre_paths.extend([PRE / f"{name}.parquet", PRE / f"{name}.csv"])
    freeze_pre_reference(pre_paths, initial_hashes)

    post = load_post_reference_inputs()
    post_cases = select_post_reference_pair_cases(data, post["grounding"])
    post_cases, post_memberships, post_frame_audit = build_direct_visual_verification(data, post_cases)
    all_cases = pd.concat([pre_cases, post_cases], ignore_index=True)
    phase_verdict = build_visual_verdict(all_cases)
    representation = build_post_reference_representation_diagnosis(data, post)
    shared_transition = build_shared_transition_diagnostic(data, post, episode_assignments)
    zero_anchor, one_anchor, two_anchor, anchor_sources = build_anchor_propagation(data, post, episode_assignments)
    write_table(post_cases, POST / "excluded_pair_likely_vs_alternative_case_registry_post_reference")
    write_table(post_memberships, POST / "selected_excluded_pair_family_memberships_post_reference")
    write_table(post_frame_audit, POST / "excluded_pair_frame_relation_audit_post_reference")
    write_table(phase_verdict, POST / "direct_visual_verification_verdict_post_reference")
    write_table(representation, POST / "one_track_one_family_diagnosis_post_reference")
    write_table(shared_transition, POST / "shared_transition_diagnostic_post_reference")
    write_table(zero_anchor, POST / "zero_anchor_baseline_post_reference")
    write_table(one_anchor, POST / "one_anchor_propagation_capacity_post_reference")
    write_table(two_anchor, POST / "two_anchor_propagation_capacity_post_reference")
    write_table(anchor_sources, POST / "anchor_source_registry_post_reference")

    figure_paths = [
        render_phase_a_summary(phase_verdict),
        render_episode_timeline(episode_assignments, episodes),
        render_evidence_heatmap(availability),
        render_anchor_propagation(one_anchor, two_anchor),
        render_representation_diagnosis(representation),
        render_partial_order_graph(partial_order),
    ]
    summary = write_reports(
        phase_verdict, episodes, availability, roles, partial_order, representation,
        shared_transition, one_anchor, two_anchor, anchor_sources,
    )
    final_hashes = frozen_input_hashes()
    if final_hashes != initial_hashes:
        raise AssertionError("frozen TERG-v1 or TERG-R0 inputs changed during TERG-R1")
    write_json(
        OUTPUT / "phase_a_direct_visual_verification_summary.json",
        {
            "phase": "EXCLUDED_PAIR_DIRECT_VISUAL_VERIFICATION_COMPLETE",
            "target_segment_count": len(TARGET_SEGMENTS),
            "selected_case_count": len(all_cases),
            "selected_case_kind_counts": all_cases["case_kind"].value_counts().to_dict(),
            "support_extent_counts": all_cases["common_sar_support_frame_count"].value_counts().sort_index().to_dict(),
            "manual_visual_verdict_pending": False,
            "relative_order_primitive_retained": True,
            "support_threshold_tuned": False,
            "terg_v1_modified": False,
            "terg_r0_modified": False,
            "r04zf_accessed": False,
        },
    )
    manifest_rows = []
    for path in sorted(OUTPUT.rglob("*")):
        if (
            not path.is_file()
            or path.name in {"ARTIFACT_MANIFEST.csv", "validation_report.json"}
            or (path.parent == PAIR_FIGURES and path.suffix.lower() == ".png")
        ):
            continue
        manifest_rows.append(
            {
                "relative_path": str(path.relative_to(OUTPUT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    pd.DataFrame(manifest_rows).to_csv(OUTPUT / "ARTIFACT_MANIFEST.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
