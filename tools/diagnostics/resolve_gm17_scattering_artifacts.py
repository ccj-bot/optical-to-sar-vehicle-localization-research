#!/usr/bin/env python3
"""A0 artifact resolver for the GM17 scattering-aware diagnostic framework.

This script is intentionally metadata-only. It locates known path clues, reads
headers or JSON top-level keys, counts table rows by streaming, computes hashes
for reasonably sized files, and emits readiness artifacts for a later
diagnostic run.

It does not compute metrics, IoU, center error, SAR descriptors, keyframe
confidence, soft-anchor messages, thresholds, weights, or selector outputs.
It does not modify source data, the candidate bank, or the GM17 selector.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


MANIFEST_COLUMNS = [
    "artifact_id",
    "line",
    "path",
    "exists",
    "source_type",
    "row_count",
    "columns_or_keys",
    "hash",
    "field_layer",
    "allowed_use",
    "forbidden_use",
    "status",
    "notes",
]

ALIAS_COLUMNS = [
    "canonical_field",
    "aliases",
    "required_line",
    "field_layer",
    "allowed_use",
    "forbidden_use",
    "status",
    "notes",
]

CHECKLIST_COLUMNS = [
    "check_id",
    "opportunity",
    "needed_artifacts",
    "readiness",
    "allowed_future_use",
    "forbidden_use",
    "status",
    "notes",
]

PAIRWISE_JOIN_COLUMNS = [
    "join_id",
    "left_artifact_id",
    "right_artifact_id",
    "required_keys",
    "left_has_keys",
    "right_has_keys",
    "status",
    "notes",
]

OBSERVED_ALIAS_COLUMNS = [
    "canonical_field",
    "alias",
    "artifact_id",
    "path",
    "observed",
    "field_layer",
    "status",
    "notes",
]

CRITICAL_LINE_FB_ARTIFACTS = [
    "A001_candidate_bank",
    "frozen_ranked_candidates",
    "per_target_audit_output",
]

JOIN_KEY_ALIASES = {
    "target_id": ["target_id", "target_identity", "sample_id", "case_id"],
    "scene_id": ["scene_id", "scene", "scene_name", "gm_scene"],
    "frame_id": ["frame_id", "sar_frame_num", "sar_frame", "frame", "frame_idx"],
    "track_id": ["track_id", "gm17_track_id", "track", "track_num"],
    "candidate_id": ["candidate_id", "cand_id"],
}

GEOMETRY_ALIASES = {
    "cx": ["cx", "candidate_cx", "box_cx"],
    "cy": ["cy", "candidate_cy", "box_cy"],
    "w": ["w", "candidate_w", "box_w"],
    "h": ["h", "candidate_h", "box_h"],
}

RANGE_AZ_ALIASES = [
    "r",
    "range",
    "az",
    "azimuth",
    "cross",
    "pred_r",
    "pred_az",
    "pred_cross",
]

SCORE_RANK_ALIASES = [
    "rank",
    "pilot_rank",
    "selected_rank",
    "rank1",
    "score",
    "factor_score",
    "selector_score",
    "path_score",
    "node_score",
]

PHYSICAL_CONVENTION_CHECKS = {
    "range_azimuth_axis_convention",
    "scatter_centroid_offset_feasibility",
    "candidate_local_crop_convention",
    "multi_scale_support_regions",
    "local_background_normalization",
    "sar_image_or_crop_source",
}

PAIRWISE_JOIN_SPECS = [
    (
        "A001_to_frozen_ranked",
        "A001_candidate_bank",
        "frozen_ranked_candidates",
        ["target_id", "scene_id", "frame_id", "track_id", "candidate_id"],
    ),
    (
        "frozen_ranked_to_per_target_audit",
        "frozen_ranked_candidates",
        "per_target_audit_output",
        ["target_id", "scene_id", "frame_id", "track_id"],
    ),
    (
        "per_target_audit_to_A019",
        "per_target_audit_output",
        "A019_final_boxes",
        ["target_id", "scene_id", "frame_id", "track_id"],
    ),
    (
        "per_target_audit_to_A021",
        "per_target_audit_output",
        "A021_condition_labels",
        ["target_id", "scene_id", "frame_id", "track_id"],
    ),
    (
        "A001_to_A005",
        "A001_candidate_bank",
        "A005_optical_temporal_prior",
        ["target_id", "scene_id", "frame_id", "track_id"],
    ),
    (
        "A001_to_A008",
        "A001_candidate_bank",
        "A008_candidate_factor_joined",
        ["target_id", "scene_id", "frame_id", "track_id", "candidate_id"],
    ),
    (
        "A007_to_A008",
        "A007_signed_escape_posterior",
        "A008_candidate_factor_joined",
        ["target_id", "scene_id", "frame_id", "track_id"],
    ),
]

EVAL_ONLY_CANONICAL_FIELDS = {
    "axis_aligned_proxy_iou",
    "rotated_iou_future",
    "center_error",
    "range_azimuth_error_fields",
    "orientation_error_fields",
    "oracle_fields",
    "final_box_fields",
    "condition_fields",
}


@dataclass(frozen=True)
class ArtifactCandidate:
    artifact_id: str
    line: str
    path: str
    source_type: str
    field_layer: str
    allowed_use: str
    forbidden_use: str
    required_for_a0: bool = False
    notes: str = ""


def artifact_candidates() -> list[ArtifactCandidate]:
    """Known path clues from the A0 plan, bridge, and resolver spec."""

    fixed_bank_forbidden = (
        "modify, filter, expand, replace, rerank, retune, or use eval-only "
        "fields for scoring"
    )
    audit_forbidden = "use as inference input, scoring field, crop source, or selector patch"
    line_gp_forbidden = (
        "NOT_FOR_FIXED_BANK_CONCLUSION; do not mix into Line-FB readiness, "
        "A001 ceiling claims, selector patches, or Phase5 approval"
    )

    return [
        ArtifactCandidate(
            "A001_candidate_bank",
            "Line-FB",
            "output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv",
            "csv",
            "inference_safe",
            "fixed-bank candidate identity and frozen candidate geometry schema lock",
            fixed_bank_forbidden,
            True,
        ),
        ArtifactCandidate(
            "A005_optical_temporal_prior",
            "Line-FB",
            "output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv",
            "csv",
            "inference_safe",
            "soft optical temporal prior and context schema lock",
            "generate candidates, overwrite centers, become hard controller, or tune selector",
            False,
        ),
        ArtifactCandidate(
            "A007_signed_escape_posterior",
            "Line-FB",
            "output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/signed_escape_posterior_inference.csv",
            "csv",
            "mixed",
            "schema/path clue, diagnostic field availability, factor provenance, double-counting audit readiness",
            "active scoring, threshold tuning, selector patch, performance claim, Phase5 approval",
            False,
        ),
        ArtifactCandidate(
            "A008_candidate_factor_joined",
            "Line-FB",
            "output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/candidate_refined_factor_inference.csv",
            "csv",
            "mixed",
            "schema/path clue, diagnostic field availability, factor provenance, double-counting audit readiness",
            "active scoring, threshold tuning, selector patch, performance claim, Phase5 approval",
            False,
        ),
        ArtifactCandidate(
            "frozen_ranked_candidates",
            "Line-FB",
            "output/gm17_phase4_minimal_factor_pilot_20260628_110447/pilot_candidates_ranked.csv",
            "csv",
            "mixed",
            "frozen rank and score reference schema lock only",
            "rerank, retune, recompute scores, or claim new performance",
            True,
        ),
        ArtifactCandidate(
            "selected_rank1_output",
            "Line-FB",
            "output/gm17_phase4_minimal_factor_pilot_20260628_110447/pilot_selected_rank1.csv",
            "csv",
            "mixed",
            "frozen selected rank1 reference for post-hoc comparison only",
            "use as scoring input or selector patch",
            False,
        ),
        ArtifactCandidate(
            "per_target_audit_output",
            "Line-FB",
            "output/gm17_phase4_minimal_factor_pilot_20260628_110447/evaluation_per_target.csv",
            "csv",
            "post_inference_audit",
            "post-inference target-level audit schema lock",
            audit_forbidden,
            True,
        ),
        ArtifactCandidate(
            "evaluation_summary",
            "Line-FB",
            "output/gm17_phase4_minimal_factor_pilot_20260628_110447/evaluation_summary.json",
            "json",
            "post_inference_audit",
            "JSON key inventory for completed post-inference audit output",
            "use summary values as scoring or performance claims in A0",
            False,
        ),
        ArtifactCandidate(
            "evaluation_condition_groups",
            "Line-FB",
            "output/gm17_phase4_minimal_factor_pilot_20260628_110447/evaluation_condition_groups.csv",
            "csv",
            "post_inference_audit",
            "post-inference grouped audit schema lock",
            audit_forbidden,
            False,
        ),
        ArtifactCandidate(
            "A019_final_boxes",
            "Line-FB",
            "output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv",
            "csv",
            "post_inference_audit",
            "A019 final-box schema lock for post-inference audit only",
            audit_forbidden,
            False,
        ),
        ArtifactCandidate(
            "A021_condition_labels",
            "Line-FB",
            "output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv",
            "csv",
            "post_inference_audit",
            "A021 condition/truncation/occlusion schema lock for post-inference grouping only",
            "use for scoring, missingness policy, route choice, keyframe choice, or anchors",
            False,
        ),
        ArtifactCandidate(
            "SAR_image_or_crop_source",
            "external",
            "D:/profile/research/data/GM_RM017/GM_RM017_SARframes_gray",
            "image_dir",
            "inference_safe",
            "SAR image/crop source existence and filename-pattern readiness only",
            "open/process pixels, compute descriptors, recurse/hash image directory, or use final boxes for crops",
            False,
            "external path clue; image pixels must not be opened by A0",
        ),
        ArtifactCandidate(
            "field_dictionary",
            "docs",
            "docs/gm17_factor_field_dictionary.md",
            "docs",
            "docs",
            "field layer and alias mapping context",
            "proof of current data existence or performance evidence",
            False,
        ),
        ArtifactCandidate(
            "phase4_data_manifest",
            "docs",
            "docs/gm17_phase4_data_manifest_and_field_gates.md",
            "docs",
            "docs",
            "path and field-layer clue source",
            "proof of current data existence or approval to run diagnostics",
            False,
        ),
        ArtifactCandidate(
            "lineB_A001_A005_field_inventory",
            "docs",
            "docs/gm17_phase4_lineB_A001_A005_field_inventory.md",
            "docs",
            "docs",
            "historical A001/A005 field inventory clue",
            "substitute for current header/hash validation",
            False,
        ),
        ArtifactCandidate(
            "execution_bridge",
            "docs",
            "docs/gm17_scattering_framework_execution_bridge.md",
            "docs",
            "docs",
            "current framework-to-execution bridge",
            "experiment report, Phase5 approval, or performance evidence",
            False,
        ),
        ArtifactCandidate(
            "A0_artifact_physical_plan",
            "docs",
            "docs/gm17_scattering_framework_A0_artifact_and_physical_diagnostic_plan.md",
            "docs",
            "docs",
            "A0 artifact and physical diagnostic plan",
            "experiment report, Phase5 approval, or performance evidence",
            False,
        ),
        ArtifactCandidate(
            "artifact_resolver_spec",
            "docs",
            "docs/gm17_scattering_framework_artifact_resolver_spec.md",
            "docs",
            "docs",
            "A0 resolver engineering specification",
            "experiment report, Phase5 approval, or performance evidence",
            False,
        ),
        ArtifactCandidate(
            "phase5B_config",
            "config",
            "configs/phase5B_first_diagnostic_run_config_v0.json",
            "json",
            "mixed",
            "config key inventory and excluded-line path clue only",
            "approve Phase5, train, calibrate, tune, or mix proposals into Line-FB",
            False,
        ),
        ArtifactCandidate(
            "phase4D_candidate_pool_ceiling",
            "Line-GP",
            "output/gm17_phase4D_candidate_pool_ceiling_audit_20260629_001655/candidate_pool_ceiling_per_target.csv",
            "csv",
            "future_only",
            "excluded generated/proposal-route path clue only",
            line_gp_forbidden,
            False,
        ),
        ArtifactCandidate(
            "phase5B_proposal_candidates",
            "Line-GP",
            "output/phase5B_first_diagnostic_run_v0_20260629_102746/proposal_candidates.csv",
            "csv",
            "future_only",
            "excluded generated-proposal candidate path clue only",
            line_gp_forbidden,
            False,
        ),
        ArtifactCandidate(
            "phase5C_metrics_summary",
            "Line-GP",
            "output/phase5C_v0_model_diagnostic_audit_20260629_110133/metrics_summary.json",
            "json",
            "future_only",
            "excluded generated-proposal audit path clue only",
            line_gp_forbidden,
            False,
        ),
        ArtifactCandidate(
            "phase5C_candidate_policy_summary",
            "Line-GP",
            "output/phase5C_v0_model_diagnostic_audit_20260629_110133/candidate_policy_summary.json",
            "json",
            "future_only",
            "excluded generated-proposal policy path clue only",
            line_gp_forbidden,
            False,
        ),
    ]


def field_alias_rows() -> list[dict[str, str]]:
    """Static alias/layer policy required before later diagnostics."""

    return [
        {
            "canonical_field": "target_id",
            "aliases": "target_identity;target_id;sample_id;case_id",
            "required_line": "Line-FB",
            "field_layer": "inference_safe_if_pre_eval",
            "allowed_use": "target joins and grouping",
            "forbidden_use": "infer correctness or audit outcome",
            "status": "HOLD_FOR_FIELD_ORIGIN_AUDIT",
            "notes": "prefer target_identity until canonical mapping is locked",
        },
        {
            "canonical_field": "scene_id",
            "aliases": "scene;scene_id;scene_name;gm_scene",
            "required_line": "Line-FB",
            "field_layer": "inference_safe",
            "allowed_use": "scene grouping",
            "forbidden_use": "shortcut for condition labels or correctness",
            "status": "HOLD_FOR_FIELD_ORIGIN_AUDIT",
            "notes": "scene aliases must be confirmed from headers",
        },
        {
            "canonical_field": "frame_id",
            "aliases": "sar_frame_num;sar_frame;frame;frame_idx;frame_id",
            "required_line": "Line-FB",
            "field_layer": "inference_safe",
            "allowed_use": "frame ordering after type/convention check",
            "forbidden_use": "real speed, physical velocity, or global smoothing claim",
            "status": "HOLD_FOR_FIELD_ORIGIN_AUDIT",
            "notes": "sar_frame_num/frame_id ordering must be locked before temporal diagnostics",
        },
        {
            "canonical_field": "track_id",
            "aliases": "gm17_track_id;track;track_num;track_id",
            "required_line": "Line-FB",
            "field_layer": "inference_safe_if_pre_eval",
            "allowed_use": "track grouping and local sequence context",
            "forbidden_use": "activate global propagation or hard anchors",
            "status": "HOLD_FOR_FIELD_ORIGIN_AUDIT",
            "notes": "gm17_track_id/track_id grouping must be confirmed from headers",
        },
        {
            "canonical_field": "candidate_id",
            "aliases": "candidate_id;cand_id",
            "required_line": "Line-FB",
            "field_layer": "inference_safe_for_fixed_bank",
            "allowed_use": "candidate identity and stable joins",
            "forbidden_use": "rewrite, regenerate, or import generated proposal ids into Line-FB",
            "status": "HOLD_FOR_FIELD_ORIGIN_AUDIT",
            "notes": "proposal_id is intentionally excluded unless a future route is approved",
        },
        {
            "canonical_field": "cx",
            "aliases": "cx;candidate_cx;box_cx",
            "required_line": "Line-FB",
            "field_layer": "inference_safe_if_candidate_side",
            "allowed_use": "frozen candidate center x",
            "forbidden_use": "replace with final_cx or modify candidate geometry",
            "status": "HOLD_FOR_FIELD_ORIGIN_AUDIT",
            "notes": "candidate-side origin must be verified",
        },
        {
            "canonical_field": "cy",
            "aliases": "cy;candidate_cy;box_cy",
            "required_line": "Line-FB",
            "field_layer": "inference_safe_if_candidate_side",
            "allowed_use": "frozen candidate center y",
            "forbidden_use": "replace with final_cy or modify candidate geometry",
            "status": "HOLD_FOR_FIELD_ORIGIN_AUDIT",
            "notes": "candidate-side origin must be verified",
        },
        {
            "canonical_field": "w",
            "aliases": "w;candidate_w;box_w",
            "required_line": "Line-FB",
            "field_layer": "inference_safe_if_candidate_side",
            "allowed_use": "frozen candidate width/axis-size metadata",
            "forbidden_use": "replace with final_w or modify candidate geometry",
            "status": "HOLD_FOR_FIELD_ORIGIN_AUDIT",
            "notes": "candidate-side origin must be verified",
        },
        {
            "canonical_field": "h",
            "aliases": "h;candidate_h;box_h",
            "required_line": "Line-FB",
            "field_layer": "inference_safe_if_candidate_side",
            "allowed_use": "frozen candidate height/axis-size metadata",
            "forbidden_use": "replace with final_h or modify candidate geometry",
            "status": "HOLD_FOR_FIELD_ORIGIN_AUDIT",
            "notes": "candidate-side origin must be verified",
        },
        {
            "canonical_field": "theta",
            "aliases": "theta;heading;candidate_heading;final_heading_deg",
            "required_line": "Line-FB for candidate metadata; audit-only for final_heading_deg",
            "field_layer": "mixed",
            "allowed_use": "candidate stored angle metadata only after origin review",
            "forbidden_use": "heading/orientation correctness or use final_heading_deg for inference",
            "status": "HOLD_FOR_FIELD_ORIGIN_AUDIT",
            "notes": "axis_aligned_proxy_iou cannot validate theta or heading",
        },
        {
            "canonical_field": "rank",
            "aliases": "rank;pilot_rank;selected_rank;rank1",
            "required_line": "Line-FB frozen output",
            "field_layer": "frozen_output_only",
            "allowed_use": "frozen run reference and schema validation",
            "forbidden_use": "recompute, retune, or use selected output as scoring input",
            "status": "HOLD_FOR_FIELD_ORIGIN_AUDIT",
            "notes": "rank is allowed only when tied to a completed frozen output",
        },
        {
            "canonical_field": "score",
            "aliases": "score;factor_score;selector_score;path_score;node_score",
            "required_line": "Line-FB frozen output or reference",
            "field_layer": "frozen_output_only_or_diagnostic_only",
            "allowed_use": "frozen reference and rank-margin readiness after origin review",
            "forbidden_use": "train, tune, calibrate, or learn weights",
            "status": "HOLD_FOR_FIELD_ORIGIN_AUDIT",
            "notes": "score origin must be locked before any interpretation",
        },
        {
            "canonical_field": "candidate_source",
            "aliases": (
                "candidate_source;proposal_source;route;provenance;"
                "candidate_detail;candidate_expansion_state;candidate_expansion_reason"
            ),
            "required_line": "Line-FB or Line-GP",
            "field_layer": "grouping_provenance_only",
            "allowed_use": "post-hoc grouping and artifact lineage",
            "forbidden_use": "ranking evidence, route shortcut, selector evidence, or anchor choice",
            "status": "HOLD_FOR_LINE_AUDIT",
            "notes": "candidate_source/route/provenance is not ranking evidence",
        },
        {
            "canonical_field": "axis_aligned_proxy_iou",
            "aliases": "axis_aligned_proxy_iou;candidate_iou;proxy_iou;rank1_proxy_iou;iou",
            "required_line": "audit table",
            "field_layer": "post_inference_audit_only",
            "allowed_use": "AABB proxy audit after scoring is frozen",
            "forbidden_use": "score, train, tune, or infer rotated IoU, heading, orientation, or long-axis quality",
            "status": "FORBIDDEN_DURING_SCORING",
            "notes": "audit-only AABB proxy, not rotated IoU",
        },
        {
            "canonical_field": "rotated_iou_future",
            "aliases": "rot_iou;rotated_iou;obb_iou;oriented_iou;rotated_obb_iou",
            "required_line": "future rotated-OBB audit table",
            "field_layer": "future_only_post_inference_audit",
            "allowed_use": "separate rotated-OBB audit only after explicit approval",
            "forbidden_use": "do not mix with axis_aligned_proxy_iou; do not use for scoring; do not infer heading/orientation in current A0",
            "status": "FORBIDDEN_DURING_SCORING",
            "notes": "future-only rotated-OBB audit field; not the AABB proxy",
        },
        {
            "canonical_field": "center_error",
            "aliases": (
                "center_error;*center_error*;candidate_center_err_px;"
                "center_err_px;center_err;*center_err*"
            ),
            "required_line": "audit table",
            "field_layer": "post_inference_audit_only",
            "allowed_use": "failure bucket assignment after scoring is frozen",
            "forbidden_use": "scoring, scatter-centroid definition, keyframe choice, or anchor choice",
            "status": "FORBIDDEN_DURING_SCORING",
            "notes": "center error remains post-inference audit only",
        },
        {
            "canonical_field": "range_azimuth_error_fields",
            "aliases": (
                "range_err_px;range_error;range_residual;"
                "az_err_px;azimuth_err;azimuth_error;azimuth_residual"
            ),
            "required_line": "audit table or future axis-convention audit",
            "field_layer": "post_inference_audit_or_future_only",
            "allowed_use": "post-inference range/azimuth residual audit only after axis convention is locked",
            "forbidden_use": "scoring, generic center-error substitution, descriptor sign validation, or physical velocity claims",
            "status": "FORBIDDEN_DURING_SCORING",
            "notes": "range/azimuth residuals are not generic center_error and require axis convention audit",
        },
        {
            "canonical_field": "orientation_error_fields",
            "aliases": (
                "heading_err_deg;heading_error;orientation_error;"
                "theta_error;long_axis_error;heading_residual"
            ),
            "required_line": "future rotated-OBB / convention audit table",
            "field_layer": "future_only_post_inference_audit",
            "allowed_use": "future heading/orientation/long-axis audit only after explicit convention approval",
            "forbidden_use": "scoring, AABB proxy interpretation, active selector input, or current A0 heading conclusion",
            "status": "FORBIDDEN_DURING_SCORING",
            "notes": "orientation/heading/long-axis errors require separate rotated-OBB/convention audit",
        },
        {
            "canonical_field": "oracle_fields",
            "aliases": (
                "oracle;oracle_*;best_candidate_id;best_proxy_candidate_id;"
                "best_center_candidate_id;oracle_rank_iou;oracle_rank_center"
            ),
            "required_line": "audit table",
            "field_layer": "post_inference_audit_only",
            "allowed_use": "post-hoc role accounting after frozen scoring",
            "forbidden_use": "candidate selection, threshold choice, training, or ranking",
            "status": "FORBIDDEN_DURING_SCORING",
            "notes": "oracle fields can never enter scoring",
        },
        {
            "canonical_field": "final_box_fields",
            "aliases": "final_*;final_cx;final_cy;final_w;final_h;final_heading_deg;gt_*;A019",
            "required_line": "A019 / audit table",
            "field_layer": "post_inference_audit_only",
            "allowed_use": "audit/evaluation join after frozen scoring",
            "forbidden_use": "descriptor crop, scoring, inference geometry, candidate modification, or heading claims",
            "status": "FORBIDDEN_DURING_SCORING",
            "notes": "final_* and A019 are eval-only",
        },
        {
            "canonical_field": "condition_fields",
            "aliases": (
                "condition_type;truncation_degree;occlusion_degree;"
                "visibility_label;partial_visible;condition;condition_*;*condition*;"
                "truncation;truncation_*;*truncation*;occlusion;occlusion_*;*occlusion*;A021"
            ),
            "required_line": "A021 / audit table",
            "field_layer": "post_inference_audit_or_future_only",
            "allowed_use": "post-inference grouped audit only",
            "forbidden_use": "missingness policy, score, route, threshold, keyframe, or anchor choice",
            "status": "FORBIDDEN_DURING_SCORING",
            "notes": "A021 condition/truncation/occlusion labels are not inference inputs",
        },
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve GM17 scattering-framework A0 artifacts without running diagnostics."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative path clues. Defaults to current directory.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Output directory. Defaults to "
            "output/gm17_scattering_artifact_resolver_<timestamp> under repo root."
        ),
    )
    parser.add_argument(
        "--extra-root",
        action="append",
        default=[],
        help=(
            "Additional root to try for relative artifact paths. May be repeated. "
            "The resolver tries repo root first, then extra roots; it does not glob."
        ),
    )
    parser.add_argument(
        "--artifact-overrides-json",
        default=None,
        help=(
            "Optional JSON mapping artifact_id to an absolute or relative path. "
            "Overrides preserve line classification and forbidden-use policy."
        ),
    )
    parser.add_argument(
        "--max-hash-bytes",
        type=int,
        default=50 * 1024 * 1024,
        help="Maximum file size to hash. Larger files record hash_skipped_large_file.",
    )
    parser.add_argument(
        "--skip-row-count",
        action="store_true",
        help="Read table headers only and skip streaming row counts.",
    )
    parser.add_argument(
        "--max-row-count-bytes",
        type=int,
        default=200 * 1024 * 1024,
        help="Maximum file size for streaming row counts. Larger files record row_count_skipped_large_file.",
    )
    parser.add_argument(
        "--dir-scan-limit",
        type=int,
        default=10000,
        help="Maximum top-level entries to inspect for image directories.",
    )
    return parser.parse_args()


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def load_artifact_overrides(path_text: str | None, repo_root: Path) -> dict[str, str]:
    if not path_text:
        return {}
    override_path = resolve_first_existing_path(repo_root, [], path_text)[0]
    with override_path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("--artifact-overrides-json must contain a JSON object")
    return {str(key): str(value) for key, value in data.items()}


def candidate_paths_for(repo_root: Path, extra_roots: list[Path], path_text: str) -> list[Path]:
    raw = Path(path_text)
    if raw.is_absolute() or (len(path_text) >= 2 and path_text[1] == ":"):
        return [raw]
    return [repo_root / raw] + [extra_root / raw for extra_root in extra_roots]


def resolve_first_existing_path(
    repo_root: Path,
    extra_roots: list[Path],
    path_text: str,
) -> tuple[Path, list[Path]]:
    tried_paths = candidate_paths_for(repo_root, extra_roots, path_text)
    for candidate_path in tried_paths:
        if candidate_path.exists():
            return candidate_path, tried_paths
    return tried_paths[0], tried_paths


def normalized_columns(columns_or_keys: str) -> set[str]:
    if not columns_or_keys:
        return set()
    return {part.strip().lower() for part in columns_or_keys.split(";") if part.strip()}


def has_any_column(rows: Iterable[dict[str, str]], aliases: Iterable[str]) -> bool:
    alias_set = {alias.lower() for alias in aliases}
    for row in rows:
        if normalized_columns(row.get("columns_or_keys", "")) & alias_set:
            return True
    return False


def has_all_geometry(rows: Iterable[dict[str, str]]) -> bool:
    rows_list = list(rows)
    return all(has_any_column(rows_list, aliases) for aliases in GEOMETRY_ALIASES.values())


def artifact_has_key(row: dict[str, str], canonical_key: str) -> bool:
    aliases = JOIN_KEY_ALIASES.get(canonical_key, [canonical_key])
    return bool(normalized_columns(row.get("columns_or_keys", "")) & {alias.lower() for alias in aliases})


def alias_observed(alias: str, columns_or_keys: set[str]) -> bool:
    alias_lower = alias.strip().lower()
    if not alias_lower:
        return False
    if "*" in alias_lower:
        return any(fnmatch.fnmatch(column, alias_lower) for column in columns_or_keys)
    return alias_lower in columns_or_keys


def read_csv_header_and_count(
    path: Path,
    delimiter: str,
    skip_row_count: bool,
    max_row_count_bytes: int,
) -> tuple[str, str, str]:
    """Read only the header and stream row count; do not store sample rows."""

    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            header = next(reader, [])
            if skip_row_count:
                return ";".join(header), "", "header_only; row_count_skipped_by_flag"
            if path.stat().st_size > max_row_count_bytes:
                return ";".join(header), "", "header_only; row_count_skipped_large_file"
            row_count = sum(1 for _ in reader)
    except OSError as exc:
        return "", "", f"table_header_read_error={exc}"
    return ";".join(header), str(row_count), "header_and_row_count_only"


def read_json_top_level_keys(
    path: Path,
    max_read_bytes: int,
    skip_row_count: bool,
) -> tuple[str, str, str]:
    size = path.stat().st_size
    if size > max_read_bytes:
        return "", "", "json_keys_skipped_large_file"
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        return "", "", f"json_key_read_error={exc}"

    if isinstance(data, dict):
        return ";".join(str(key) for key in data.keys()), "", "json_top_level_keys_only"
    if isinstance(data, list):
        if skip_row_count:
            return "json_top_level_type=list", "", "json_array_length_skipped_by_flag"
        return "json_top_level_type=list", str(len(data)), "json_array_length_only_no_sample_rows"
    return f"json_top_level_type={type(data).__name__}", "", "json_top_level_type_only"


def count_jsonl_lines(
    path: Path,
    skip_row_count: bool,
    max_row_count_bytes: int,
) -> tuple[str, str, str]:
    if skip_row_count:
        return "jsonl_keys_unread_no_sample_rows", "", "jsonl_line_count_skipped_by_flag"
    if path.stat().st_size > max_row_count_bytes:
        return "jsonl_keys_unread_no_sample_rows", "", "jsonl_line_count_skipped_large_file"
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            row_count = sum(1 for _ in handle)
    except OSError as exc:
        return "", "", f"jsonl_count_error={exc}"
    return "jsonl_keys_unread_no_sample_rows", str(row_count), "jsonl_line_count_only"


def sha256_or_skip(path: Path, max_hash_bytes: int) -> str:
    if path.is_dir():
        return "hash_skipped_directory"
    size = path.stat().st_size
    if size > max_hash_bytes:
        return "hash_skipped_large_file"

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def inspect_image_dir(path: Path, dir_scan_limit: int) -> tuple[str, str]:
    """Inspect top-level filenames only; do not recurse or open pixels."""

    extensions: Counter[str] = Counter()
    seen = 0
    first_names: list[str] = []
    truncated = False
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                seen += 1
                if seen <= 5:
                    first_names.append(entry.name)
                if entry.is_file():
                    extensions[Path(entry.name).suffix.lower() or "<no_ext>"] += 1
                if seen >= dir_scan_limit:
                    truncated = True
                    break
    except OSError as exc:
        return "", f"image_dir_scan_error={exc}"

    ext_summary = ",".join(f"{key}:{value}" for key, value in sorted(extensions.items()))
    notes = [
        f"top_level_entry_count_approx={seen}",
        f"scan_truncated={str(truncated).lower()}",
        f"extensions={ext_summary or 'none'}",
        f"first_names={';'.join(first_names)}",
        "no_pixels_opened",
        "no_recursive_hash",
    ]
    return "image_directory_top_level_inventory_only", "; ".join(notes)


def classify_status(candidate: ArtifactCandidate, exists: bool, source_type: str) -> str:
    if candidate.line == "Line-GP":
        return "EXCLUDED_LINE"
    if not exists:
        if candidate.required_for_a0:
            return "HOLD"
        return "PATH_CLUE_ONLY"
    if source_type == "image_dir" and candidate.line == "external":
        return "HOLD"
    return "GO"


def inspect_candidate(
    candidate: ArtifactCandidate,
    repo_root: Path,
    extra_roots: list[Path],
    artifact_overrides: dict[str, str],
    max_hash_bytes: int,
    skip_row_count: bool,
    max_row_count_bytes: int,
    dir_scan_limit: int,
) -> dict[str, str]:
    path_text = artifact_overrides.get(candidate.artifact_id, candidate.path)
    resolved, tried_paths = resolve_first_existing_path(repo_root, extra_roots, path_text)
    exists = resolved.exists()
    source_type = candidate.source_type
    row_count = ""
    columns_or_keys = ""
    file_hash = ""
    notes = [candidate.notes] if candidate.notes else []
    if candidate.artifact_id in artifact_overrides:
        notes.append("artifact_path_override_used")
    notes.append("tried_paths=" + "|".join(str(path) for path in tried_paths))

    if exists:
        try:
            stat = resolved.stat()
            notes.append(f"size_bytes={stat.st_size}")
        except OSError as exc:
            notes.append(f"stat_error={exc}")

        if resolved.is_dir():
            if source_type == "image_dir":
                columns_or_keys, dir_notes = inspect_image_dir(resolved, dir_scan_limit)
                notes.append(dir_notes)
            else:
                notes.append("directory_not_hashed")
            file_hash = "hash_skipped_directory"
        elif resolved.is_file():
            file_hash = sha256_or_skip(resolved, max_hash_bytes)
            lower_suffix = resolved.suffix.lower()
            if source_type == "csv" or lower_suffix == ".csv":
                columns_or_keys, row_count, read_note = read_csv_header_and_count(
                    resolved,
                    ",",
                    skip_row_count=skip_row_count,
                    max_row_count_bytes=max_row_count_bytes,
                )
                notes.append(read_note)
            elif source_type == "tsv" or lower_suffix == ".tsv":
                columns_or_keys, row_count, read_note = read_csv_header_and_count(
                    resolved,
                    "\t",
                    skip_row_count=skip_row_count,
                    max_row_count_bytes=max_row_count_bytes,
                )
                notes.append(read_note)
            elif source_type == "json" or lower_suffix == ".json":
                columns_or_keys, row_count, read_note = read_json_top_level_keys(
                    resolved,
                    max_hash_bytes,
                    skip_row_count=skip_row_count,
                )
                notes.append(read_note)
            elif source_type == "jsonl" or lower_suffix == ".jsonl":
                columns_or_keys, row_count, read_note = count_jsonl_lines(
                    resolved,
                    skip_row_count=skip_row_count,
                    max_row_count_bytes=max_row_count_bytes,
                )
                notes.append(read_note)
            elif source_type == "parquet" or lower_suffix == ".parquet":
                columns_or_keys = "parquet_schema_unread_standard_library"
                notes.append("parquet_schema_requires_non_stdlib_reader")
            else:
                notes.append("metadata_hash_only")
        else:
            notes.append("path_exists_but_is_not_regular_file_or_directory")
    else:
        notes.append("path_does_not_exist")

    if candidate.line == "Line-GP":
        notes.append("NOT_FOR_FIXED_BANK_CONCLUSION")
    if candidate.artifact_id == "SAR_image_or_crop_source":
        notes.append("image_dir_top_level_only_if_present")
        if exists:
            notes.append("external_image_path_exists_but_axis_crop_convention_unverified")
        else:
            notes.append("external_image_path_missing_or_unresolved; axis_crop_convention_unverified")
    if candidate.artifact_id == "phase5B_config":
        notes.append("config_only_not_phase5_approval")

    return {
        "artifact_id": candidate.artifact_id,
        "line": candidate.line,
        "path": str(resolved),
        "exists": str(exists).lower(),
        "source_type": source_type,
        "row_count": row_count,
        "columns_or_keys": columns_or_keys,
        "hash": file_hash,
        "field_layer": candidate.field_layer,
        "allowed_use": candidate.allowed_use,
        "forbidden_use": candidate.forbidden_use,
        "status": classify_status(candidate, exists, source_type),
        "notes": "; ".join(part for part in notes if part),
    }


def rows_by_artifact(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["artifact_id"]: row for row in rows}


def existing_rows(rows: list[dict[str, str]], artifact_ids: Iterable[str]) -> list[dict[str, str]]:
    wanted = set(artifact_ids)
    return [
        row
        for row in rows
        if row["artifact_id"] in wanted and row.get("exists", "").lower() == "true"
    ]


def pairwise_join_readiness_rows(
    manifest_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    by_artifact = rows_by_artifact(manifest_rows)
    rows: list[dict[str, str]] = []

    for join_id, left_id, right_id, required_keys in PAIRWISE_JOIN_SPECS:
        left = by_artifact.get(left_id)
        right = by_artifact.get(right_id)
        left_exists = left is not None and left.get("exists") == "true"
        right_exists = right is not None and right.get("exists") == "true"
        left_has = [key for key in required_keys if left and artifact_has_key(left, key)]
        right_has = [key for key in required_keys if right and artifact_has_key(right, key)]
        left_missing = [key for key in required_keys if key not in left_has]
        right_missing = [key for key in required_keys if key not in right_has]

        notes = [
            "header_columns_only",
            "no_sample_rows",
            "no_actual_join",
            "no_row_match_count",
        ]
        if not left_exists:
            notes.append(f"left_missing_or_unresolved={left_id}")
        if not right_exists:
            notes.append(f"right_missing_or_unresolved={right_id}")
        if left_missing:
            notes.append("left_missing_keys=" + ",".join(left_missing))
        if right_missing:
            notes.append("right_missing_keys=" + ",".join(right_missing))

        status = "GO" if left_exists and right_exists and not left_missing and not right_missing else "HOLD"

        rows.append(
            {
                "join_id": join_id,
                "left_artifact_id": left_id,
                "right_artifact_id": right_id,
                "required_keys": ";".join(required_keys),
                "left_has_keys": ";".join(left_has),
                "right_has_keys": ";".join(right_has),
                "status": status,
                "notes": "; ".join(notes),
            }
        )

    return rows


def observed_field_alias_hit_rows(
    manifest_rows: list[dict[str, str]],
    alias_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for alias_policy in alias_rows:
        canonical = alias_policy["canonical_field"]
        aliases = [part.strip() for part in alias_policy["aliases"].split(";") if part.strip()]
        canonical_eval_only = canonical in EVAL_ONLY_CANONICAL_FIELDS
        for artifact in manifest_rows:
            columns = normalized_columns(artifact.get("columns_or_keys", ""))
            artifact_inference_facing = (
                artifact.get("line") == "Line-FB"
                and artifact.get("field_layer") in {"inference_safe", "mixed"}
            )
            for alias in aliases:
                observed = alias_observed(alias, columns)
                status = "ABSENT"
                notes = "header_or_key_not_observed"

                if observed:
                    if canonical_eval_only and artifact_inference_facing:
                        if artifact.get("field_layer") == "inference_safe":
                            status = "STOP_RISK"
                        else:
                            status = "HOLD_FOR_FIELD_LAYER_AUDIT"
                        notes = (
                            "eval_only_alias_observed_in_line_fb_inference_facing_artifact; "
                            "do_not_use_for_scoring"
                        )
                    elif canonical_eval_only and artifact.get("field_layer") == "post_inference_audit":
                        status = "AUDIT_ONLY_OK"
                        notes = "eval_only_alias_observed_in_post_inference_audit_artifact"
                    elif canonical == "candidate_source":
                        status = "PROVENANCE_ONLY_REVIEW"
                        notes = "candidate_source_route_provenance_is_not_ranking_evidence"
                    else:
                        status = "OBSERVED"
                        notes = "alias_observed_in_header_or_json_key"

                rows.append(
                    {
                        "canonical_field": canonical,
                        "alias": alias,
                        "artifact_id": artifact["artifact_id"],
                        "path": artifact["path"],
                        "observed": str(observed).lower(),
                        "field_layer": artifact.get("field_layer", ""),
                        "status": status,
                        "notes": notes,
                    }
                )

    return rows


def physical_opportunity_rows(manifest_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_artifact = rows_by_artifact(manifest_rows)
    a001_rows = existing_rows(manifest_rows, ["A001_candidate_bank"])
    a005_rows = existing_rows(manifest_rows, ["A005_optical_temporal_prior"])
    ranked_rows = existing_rows(manifest_rows, ["frozen_ranked_candidates"])
    sar_source = by_artifact.get("SAR_image_or_crop_source", {})
    sar_exists = sar_source.get("exists") == "true"

    geometry_ready = has_all_geometry(a001_rows)
    candidate_id_ready = has_any_column(a001_rows, JOIN_KEY_ALIASES["candidate_id"])
    frame_ready = has_any_column(a001_rows + ranked_rows, JOIN_KEY_ALIASES["frame_id"])
    track_ready = has_any_column(a001_rows + ranked_rows, JOIN_KEY_ALIASES["track_id"])
    range_az_ready = has_any_column(a001_rows + a005_rows, RANGE_AZ_ALIASES)
    score_rank_ready = has_any_column(ranked_rows, SCORE_RANK_ALIASES)

    def status(condition: bool) -> str:
        return "GO" if condition else "HOLD"

    return [
        {
            "check_id": "range_azimuth_axis_convention",
            "opportunity": "range / azimuth axis convention",
            "needed_artifacts": "A001_candidate_bank;A005_optical_temporal_prior;SAR_image_or_crop_source;field_dictionary",
            "readiness": (
                f"prerequisites_present={str(range_az_ready).lower()}; "
                "convention_unverified; HOLD_FOR_AXIS_CONVENTION_AUDIT"
            ),
            "allowed_future_use": "later decompose offsets into range-like and azimuth-like components after convention lock",
            "forbidden_use": "compute delta_range/delta_azimuth or infer heading/orientation in A0",
            "status": "HOLD",
            "notes": (
                "schema-only check; field/path presence is not proof of range/azimuth axis, "
                "sign convention, or local coordinate convention"
            ),
        },
        {
            "check_id": "scatter_centroid_offset_feasibility",
            "opportunity": "scatter centroid offset feasibility",
            "needed_artifacts": "A001_candidate_bank;SAR_image_or_crop_source",
            "readiness": (
                f"prerequisites_present={str(geometry_ready and sar_exists).lower()}; "
                "crop_origin_unverified; convention_unverified; "
                "HOLD_FOR_CROP_CONVENTION_AUDIT; HOLD_FOR_NORMALIZATION_POLICY"
            ),
            "allowed_future_use": "future scatter_centroid_dx/dy feasibility after crop and normalization lock",
            "forbidden_use": "compute scatter centroid, use GT center, center error, or final boxes",
            "status": "HOLD",
            "notes": "A0 does not open SAR pixels; prerequisites present do not imply descriptor readiness",
        },
        {
            "check_id": "candidate_local_crop_convention",
            "opportunity": "candidate-local crop convention",
            "needed_artifacts": "A001_candidate_bank;SAR_image_or_crop_source;field_dictionary",
            "readiness": (
                f"prerequisites_present={str(geometry_ready and sar_exists).lower()}; "
                "crop_origin_unverified; local_coordinate_convention_unverified; "
                "HOLD_FOR_CROP_CONVENTION_AUDIT"
            ),
            "allowed_future_use": "future candidate-side crop policy design",
            "forbidden_use": "use final boxes, A019, A021, or manual labels to define crops",
            "status": "HOLD",
            "notes": "candidate geometry and image paths are prerequisites only, not crop convention approval",
        },
        {
            "check_id": "multi_scale_support_regions",
            "opportunity": "multi-scale support regions",
            "needed_artifacts": "A001_candidate_bank;SAR_image_or_crop_source",
            "readiness": (
                f"prerequisites_present={str(geometry_ready).lower()}; "
                "crop_origin_unverified; local_coordinate_convention_unverified; "
                "HOLD_FOR_CROP_CONVENTION_AUDIT"
            ),
            "allowed_future_use": "future inner/core/support/ring schema design",
            "forbidden_use": "compute energy, compactness, support spill-out, or label-conditioned thresholds",
            "status": "HOLD",
            "notes": "support-region prerequisites do not prove descriptor or region convention readiness",
        },
        {
            "check_id": "local_background_normalization",
            "opportunity": "local background normalization",
            "needed_artifacts": "A001_candidate_bank;SAR_image_or_crop_source",
            "readiness": (
                f"prerequisites_present={str(geometry_ready and sar_exists).lower()}; "
                "intensity_normalization_policy_unverified; HOLD_FOR_NORMALIZATION_POLICY"
            ),
            "allowed_future_use": "future local ring / robust normalization feasibility",
            "forbidden_use": "tune percentile thresholds from audit outcomes or condition labels",
            "status": "HOLD",
            "notes": "A0 does not compute image statistics and does not approve normalization policy",
        },
        {
            "check_id": "sar_image_or_crop_source",
            "opportunity": "SAR image / crop source",
            "needed_artifacts": "SAR_image_or_crop_source;phase5B_config",
            "readiness": (
                f"prerequisites_present={str(sar_exists).lower()}; "
                "image_source_path_only; convention_unverified; "
                "HOLD_FOR_AXIS_CONVENTION_AUDIT; HOLD_FOR_CROP_CONVENTION_AUDIT"
            ),
            "allowed_future_use": "future descriptor extraction readiness after convention lock",
            "forbidden_use": "open/process pixels in A0 or use display source as performance evidence",
            "status": "HOLD",
            "notes": sar_source.get("notes", ""),
        },
        {
            "check_id": "frame_track_ordering",
            "opportunity": "frame / track ordering",
            "needed_artifacts": "A001_candidate_bank;frozen_ranked_candidates",
            "readiness": "frame and track aliases present" if frame_ready and track_ready else "missing frame or track aliases",
            "allowed_future_use": "future local sequence context after ordering type check",
            "forbidden_use": "real speed, physical velocity, smoothing boxes, or global propagation",
            "status": status(frame_ready and track_ready),
            "notes": "does not inspect values or detect gaps in A0",
        },
        {
            "check_id": "candidate_mode_cluster_feasibility",
            "opportunity": "candidate mode cluster feasibility",
            "needed_artifacts": "A001_candidate_bank",
            "readiness": "candidate_id and geometry aliases present" if candidate_id_ready and geometry_ready else "missing candidate_id or geometry aliases",
            "allowed_future_use": "future diagnostic-only geometry mode clustering",
            "forbidden_use": "create candidates, move boxes, or form clusters from IoU/oracle labels",
            "status": status(candidate_id_ready and geometry_ready),
            "notes": "A0 does not cluster candidates",
        },
        {
            "check_id": "identifiability_anti_keyframe_feasibility",
            "opportunity": "identifiability / anti-keyframe feasibility",
            "needed_artifacts": "frozen_ranked_candidates;SAR_image_or_crop_source;future descriptor schema",
            "readiness": "frozen rank/score aliases and SAR source path present" if score_rank_ready and sar_exists else "missing frozen score/rank aliases or SAR source",
            "allowed_future_use": "future low-entropy/high-identifiability and anti-keyframe schema design",
            "forbidden_use": "define keyframes from high IoU, center error, A021 labels, or hard locks",
            "status": status(score_rank_ready and sar_exists),
            "notes": "descriptor clarity is future-only and not computed here",
        },
    ]


def assess_join_keys(manifest_rows: list[dict[str, str]]) -> tuple[str, list[str]]:
    fb_rows = [
        row
        for row in manifest_rows
        if row["line"] == "Line-FB"
        and row.get("exists") == "true"
        and row["source_type"] in {"csv", "tsv", "parquet"}
    ]
    missing = [
        canonical
        for canonical, aliases in JOIN_KEY_ALIASES.items()
        if not has_any_column(fb_rows, aliases)
    ]
    return ("GO" if not missing else "HOLD", missing)


def detect_line_mixing(manifest_rows: list[dict[str, str]]) -> tuple[str, list[str]]:
    risky_rows: list[str] = []
    seen_paths: dict[str, str] = {}
    for row in manifest_rows:
        path = row["path"].lower()
        line = row["line"]
        if line == "Line-FB" and ("phase5b" in path or "proposal" in path):
            risky_rows.append(row["artifact_id"])
        if path in seen_paths and seen_paths[path] != line:
            risky_rows.append(row["artifact_id"])
        seen_paths[path] = line
    return ("HOLD" if risky_rows else "GO", risky_rows)


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_stop_hold_go_report(
    manifest_rows: list[dict[str, str]],
    checklist_rows: list[dict[str, str]],
    pairwise_rows: list[dict[str, str]],
    observed_alias_rows: list[dict[str, str]],
    repo_root: Path,
    output_dir: Path,
) -> str:
    by_artifact = rows_by_artifact(manifest_rows)
    missing_critical = [
        artifact_id
        for artifact_id in CRITICAL_LINE_FB_ARTIFACTS
        if by_artifact.get(artifact_id, {}).get("exists") != "true"
    ]
    join_status, missing_join_keys = assess_join_keys(manifest_rows)
    mix_status, risky_line_rows = detect_line_mixing(manifest_rows)
    axis_hold = any(
        row["check_id"] in {"range_azimuth_axis_convention", "candidate_local_crop_convention"}
        and row["status"] != "GO"
        for row in checklist_rows
    )

    status_counts = Counter(row["status"] for row in manifest_rows)
    line_counts = Counter(row["line"] for row in manifest_rows)
    pairwise_counts = Counter(row["status"] for row in pairwise_rows)
    alias_risk_rows = [
        row
        for row in observed_alias_rows
        if row["observed"] == "true"
        and row["status"] in {"STOP_RISK", "HOLD_FOR_FIELD_LAYER_AUDIT"}
    ]
    alias_risk_counts = Counter(row["status"] for row in alias_risk_rows)
    physical_convention_holds = [
        row["check_id"]
        for row in checklist_rows
        if row["check_id"] in PHYSICAL_CONVENTION_CHECKS and row["status"] == "HOLD"
    ]

    lines = [
        "# GM17 Scattering A0 Resolver STOP/HOLD/GO Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"Repo root: `{repo_root}`",
        f"Output directory: `{output_dir}`",
        "",
        "This report is A0 metadata/schema readiness only. It is not an experiment report,",
        "not Experiment A, not Phase5 approval, and not a performance conclusion.",
        "",
        "Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.",
        "",
        "## Invariants",
        "",
        "- `experiment_ran`: false",
        "- `metrics_computed`: false",
        "- `candidate_bank_modified`: false",
        "- `selector_modified`: false",
        "- `line_gp_excluded_from_fixed_bank_conclusion`: true",
        "",
        "## GO",
        "",
        "- Header/schema/hash/manifest only.",
        "- Path resolution, file existence checks, row counts, CSV/TSV headers, JSON top-level keys.",
        "- Field alias mapping and field-layer classification.",
        "- Physical opportunity checklist without descriptor, metric, keyframe, or soft-anchor computation.",
        "- Pairwise join readiness from headers only, without actual joins or row-match counts.",
        "",
        "## HOLD",
        "",
        f"- Missing A001 candidate bank: {'yes' if 'A001_candidate_bank' in missing_critical else 'no'}.",
        f"- Missing frozen ranked output: {'yes' if 'frozen_ranked_candidates' in missing_critical else 'no'}.",
        f"- Missing per-target audit/evaluation output: {'yes' if 'per_target_audit_output' in missing_critical else 'no'}.",
        f"- Ambiguous join keys: {'yes' if join_status == 'HOLD' else 'no'}"
        + (f" ({', '.join(missing_join_keys)})" if missing_join_keys else "."),
        f"- Unknown SAR axis/crop convention: {'yes' if axis_hold else 'no'}.",
        f"- Line-FB / Line-GP mixed: {'yes' if mix_status == 'HOLD' else 'no'}"
        + (f" ({', '.join(risky_line_rows)})" if risky_line_rows else "."),
        f"- Pairwise joins on HOLD: {pairwise_counts.get('HOLD', 0)} of {len(pairwise_rows)}.",
        f"- Physical convention holds: {len(physical_convention_holds)}"
        + (f" ({', '.join(physical_convention_holds)})" if physical_convention_holds else "."),
        f"- Observed eval-only alias risks: {len(alias_risk_rows)}"
        + (f" {dict(alias_risk_counts)}" if alias_risk_rows else "."),
        "",
        "## STOP",
        "",
        "- Metrics computation.",
        "- Experiment run.",
        "- New IoU computation.",
        "- Center error computation.",
        "- SAR descriptor computation.",
        "- Keyframe confidence computation.",
        "- Soft-anchor simulation.",
        "- Candidate bank modification.",
        "- Candidate geometry movement.",
        "- Selector modification.",
        "- Threshold tuning or weight learning.",
        "- Phase5 / OOF / training / calibration.",
        "- Eval-only fields used for scoring.",
        "- `axis_aligned_proxy_iou` treated as rotated IoU.",
        "- Heading, orientation, or long-axis conclusions made from AABB proxy.",
        "",
        "## Line Separation",
        "",
        "- Line-FB is the fixed-bank diagnostic line.",
        "- Line-GP is generated-proposal / Phase5B route evidence and is excluded from Line-FB readiness.",
        "- Line-GP rows in the manifest are marked `EXCLUDED_LINE` and `NOT_FOR_FIXED_BANK_CONCLUSION`.",
        "",
        "## Pairwise Join Readiness Summary",
        "",
        f"- Pairwise rows: {len(pairwise_rows)}",
        f"- Pairwise status counts: {dict(pairwise_counts)}",
        "- Pairwise readiness uses each artifact's own header/keys only.",
        "- It does not use global column presence, sample rows, actual joins, or row-match counts.",
        "",
        "## Observed Eval-Only Alias Risk Summary",
        "",
        f"- Observed eval-only alias risk rows: {len(alias_risk_rows)}",
        f"- Risk status counts: {dict(alias_risk_counts)}",
        "- `axis_aligned_proxy_iou`, future rotated/OBB IoU fields, oracle, center-error, range/azimuth residuals, orientation errors, `final_*`, A019, A021, condition, truncation, and occlusion aliases remain audit-only, future-only, or forbidden during scoring.",
        "",
        "## Physical Convention HOLD Summary",
        "",
        f"- Physical convention HOLD rows: {len(physical_convention_holds)}",
        "- Physical opportunity prerequisites present does not equal descriptor readiness GO.",
        "- Range/azimuth axis, crop origin, local coordinate convention, and intensity normalization policy must be explicitly audited before descriptor work.",
        "",
        "## Counts",
        "",
        f"- Manifest rows: {len(manifest_rows)}",
        f"- Status counts: {dict(status_counts)}",
        f"- Line counts: {dict(line_counts)}",
        "",
        "## Current Decision",
        "",
    ]

    if (
        missing_critical
        or join_status == "HOLD"
        or axis_hold
        or mix_status == "HOLD"
        or pairwise_counts.get("HOLD", 0)
        or alias_risk_rows
    ):
        lines.append("`HOLD`: A0 manifest/schema output may be reviewed, but Experiment A remains blocked.")
    else:
        lines.append("`GO_FOR_A0_REVIEW_ONLY`: required artifacts and schema clues are present for A0 review.")

    lines.extend(
        [
            "",
            "This decision does not authorize Experiment A, B, C, D, E, or F.",
            "Experiment A remains a separate later step.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_summary(
    manifest_rows: list[dict[str, str]],
    checklist_rows: list[dict[str, str]],
    pairwise_rows: list[dict[str, str]],
    observed_alias_rows: list[dict[str, str]],
    repo_root: Path,
    output_dir: Path,
    extra_roots: list[Path],
    artifact_overrides: dict[str, str],
) -> dict[str, object]:
    status_counts = Counter(row["status"] for row in manifest_rows)
    line_counts = Counter(row["line"] for row in manifest_rows)
    checklist_status_counts = Counter(row["status"] for row in checklist_rows)
    pairwise_status_counts = Counter(row["status"] for row in pairwise_rows)
    alias_status_counts = Counter(row["status"] for row in observed_alias_rows)
    join_status, missing_join_keys = assess_join_keys(manifest_rows)
    mix_status, risky_line_rows = detect_line_mixing(manifest_rows)
    row_count_skipped_count = sum(
        1
        for row in manifest_rows
        if "row_count_skipped" in row.get("notes", "")
        or "json_array_length_skipped" in row.get("notes", "")
        or "jsonl_line_count_skipped" in row.get("notes", "")
    )
    physical_convention_holds = [
        row["check_id"]
        for row in checklist_rows
        if row["check_id"] in PHYSICAL_CONVENTION_CHECKS and row["status"] == "HOLD"
    ]

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "repo_root": str(repo_root),
        "output_dir": str(output_dir),
        "script_scope": "A0_artifact_schema_physical_readiness_only",
        "experiment_ran": False,
        "metrics_computed": False,
        "candidate_bank_modified": False,
        "selector_modified": False,
        "line_gp_excluded_from_fixed_bank_conclusion": True,
        "formal_phase5_status": "BLOCKED_FOR_OOF_CALIBRATION",
        "performance_conclusion_produced": False,
        "candidate_geometry_modified": False,
        "descriptors_computed": False,
        "keyframe_confidence_computed": False,
        "soft_anchor_simulation_ran": False,
        "artifact_count": len(manifest_rows),
        "manifest_status_counts": dict(status_counts),
        "line_counts": dict(line_counts),
        "physical_checklist_status_counts": dict(checklist_status_counts),
        "pairwise_join_status_counts": dict(pairwise_status_counts),
        "observed_alias_status_counts": dict(alias_status_counts),
        "join_key_status": join_status,
        "missing_join_key_groups": missing_join_keys,
        "line_mixing_status": mix_status,
        "line_mixing_risks": risky_line_rows,
        "pairwise_join_output": str(output_dir / "pairwise_join_readiness.csv"),
        "observed_alias_hits_output": str(output_dir / "observed_field_alias_hits.csv"),
        "extra_roots": [str(path) for path in extra_roots],
        "artifact_overrides_used": dict(artifact_overrides),
        "row_count_skipped_count": row_count_skipped_count,
        "physical_convention_holds": physical_convention_holds,
        "a007_a008_included": True,
        "outputs": {
            "artifact_manifest": str(output_dir / "artifact_manifest.csv"),
            "field_alias_map": str(output_dir / "field_alias_map.csv"),
            "physical_opportunity_checklist": str(
                output_dir / "physical_opportunity_checklist.csv"
            ),
            "pairwise_join_readiness": str(output_dir / "pairwise_join_readiness.csv"),
            "observed_field_alias_hits": str(output_dir / "observed_field_alias_hits.csv"),
            "stop_hold_go_report": str(output_dir / "stop_hold_go_report.md"),
            "resolver_summary": str(output_dir / "resolver_summary.json"),
        },
    }


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    extra_roots = [Path(path).resolve() for path in args.extra_root]
    artifact_overrides = load_artifact_overrides(args.artifact_overrides_json, repo_root)
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = repo_root / output_dir
    else:
        output_dir = repo_root / "output" / f"gm17_scattering_artifact_resolver_{timestamp()}"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = [
        inspect_candidate(
            candidate,
            repo_root,
            extra_roots=extra_roots,
            artifact_overrides=artifact_overrides,
            max_hash_bytes=args.max_hash_bytes,
            skip_row_count=args.skip_row_count,
            max_row_count_bytes=args.max_row_count_bytes,
            dir_scan_limit=args.dir_scan_limit,
        )
        for candidate in artifact_candidates()
    ]
    alias_rows = field_alias_rows()
    checklist_rows = physical_opportunity_rows(manifest_rows)
    pairwise_rows = pairwise_join_readiness_rows(manifest_rows)
    observed_alias_rows = observed_field_alias_hit_rows(manifest_rows, alias_rows)

    write_csv(output_dir / "artifact_manifest.csv", manifest_rows, MANIFEST_COLUMNS)
    write_csv(output_dir / "field_alias_map.csv", alias_rows, ALIAS_COLUMNS)
    write_csv(
        output_dir / "physical_opportunity_checklist.csv",
        checklist_rows,
        CHECKLIST_COLUMNS,
    )
    write_csv(
        output_dir / "pairwise_join_readiness.csv",
        pairwise_rows,
        PAIRWISE_JOIN_COLUMNS,
    )
    write_csv(
        output_dir / "observed_field_alias_hits.csv",
        observed_alias_rows,
        OBSERVED_ALIAS_COLUMNS,
    )

    report = build_stop_hold_go_report(
        manifest_rows,
        checklist_rows,
        pairwise_rows,
        observed_alias_rows,
        repo_root,
        output_dir,
    )
    (output_dir / "stop_hold_go_report.md").write_text(report, encoding="utf-8")

    summary = build_summary(
        manifest_rows,
        checklist_rows,
        pairwise_rows,
        observed_alias_rows,
        repo_root,
        output_dir,
        extra_roots,
        artifact_overrides,
    )
    (output_dir / "resolver_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"A0 resolver outputs written to: {output_dir}")
    print("No experiments, metrics, descriptors, training, calibration, candidate-bank edits, or selector edits were run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
