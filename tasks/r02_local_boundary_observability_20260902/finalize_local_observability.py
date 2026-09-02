from __future__ import annotations

import csv
import json
from pathlib import Path


WORKSPACE = Path(r"D:\profile\research\workspace")
OUT = WORKSPACE / "output" / "r02_local_boundary_observability_20260902"
PRE = OUT / "pre_reference"
POST = OUT / "post_freeze_audit"


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def visual_verdicts() -> list[dict[str, object]]:
    return [
        {
            "case_id": "ENTRANCE_F58_STOP",
            "figure": "STOP_REASON_ATLAS.png",
            "seed_frame": 62,
            "frame_or_range": "F58",
            "algorithm_state": "UNKNOWN",
            "visual_verdict": "CONSERVATIVE_STOP_ACCEPTABLE",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "Far evidence is weak and fragmented; a boundary trace remains visible, but pair-safe support is not visually secure.",
        },
        {
            "case_id": "ENTRANCE_F59_F66_LOCAL_PATH",
            "figure": "ENTRANCE_F057_F068_CURVE_EVOLUTION.png",
            "seed_frame": 62,
            "frame_or_range": "F59-F66",
            "algorithm_state": "SUPPORTED",
            "visual_verdict": "LOCAL_CURVED_ENTRY_SUPPORT_PLAUSIBLE",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "The close F62 seed follows the visible curved near/far ridges over this short entrance interval.",
        },
        {
            "case_id": "ENTRANCE_F67_STOP",
            "figure": "ENTRANCE_F057_F068_CURVE_EVOLUTION.png",
            "seed_frame": 62,
            "frame_or_range": "F67",
            "algorithm_state": "UNKNOWN",
            "visual_verdict": "STRONGEST_PREMATURE_STOP_CANDIDATE",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "The near response fails the frozen gate although a human-visible boundary trace remains; conservative false-unknown is possible.",
        },
        {
            "case_id": "F66_NATURAL_OVERLAP_CONFLICT",
            "figure": "F066_NATURAL_OVERLAP_SHAPE_CONFLICT.png",
            "seed_frame": "62_vs_150",
            "frame_or_range": "F66",
            "algorithm_state": "SUPPORTED_BY_BOTH_PATHS",
            "visual_verdict": "FALSE_SUPPORT_CURVE_STATE",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": True,
            "note": "F62-forward retains the entrance curve while F150-backward imports a rigid near-horizontal state; both cannot be the correct full boundary state.",
        },
        {
            "case_id": "F150_BACKWARD_F82_CHECKPOINT",
            "figure": "CHECKPOINT_COMPARISON_ATLAS.png",
            "seed_frame": 150,
            "frame_or_range": "F82",
            "algorithm_state": "SUPPORTED",
            "visual_verdict": "CHECKPOINT_CONSISTENT",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "Automatic and manual near/far boundaries agree within the frozen numerical gate and on the same visible response.",
        },
        {
            "case_id": "F150_STABLE_SEGMENT_REVIEW",
            "figure": "F150_process_review.png",
            "seed_frame": 150,
            "frame_or_range": "F82,F108,F150,F157,F164",
            "algorithm_state": "SUPPORTED",
            "visual_verdict": "STABLE_SEGMENT_SUPPORT_PLAUSIBLE",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "Sampled start, middle, seed, and end frames remain on the visually corresponding near/far responses.",
        },
        {
            "case_id": "F150_FORWARD_F165_STOP",
            "figure": "F150_process_review.png",
            "seed_frame": 150,
            "frame_or_range": "F165",
            "algorithm_state": "UNKNOWN",
            "visual_verdict": "CONSERVATIVE_STOP_ACCEPTABLE",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "The frozen far-response gate fails at the transition; no silent continuation is forced.",
        },
        {
            "case_id": "F183_FORWARD_F239_CHECKPOINT",
            "figure": "CHECKPOINT_COMPARISON_ATLAS.png",
            "seed_frame": 183,
            "frame_or_range": "F239",
            "algorithm_state": "SUPPORTED",
            "visual_verdict": "CHECKPOINT_CONSISTENT",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "Automatic and manual geometry are visually and numerically consistent.",
        },
        {
            "case_id": "F183_STABLE_SEGMENT_REVIEW",
            "figure": "F183_process_review.png",
            "seed_frame": 183,
            "frame_or_range": "F166,F174,F183,F221,F239,F259",
            "algorithm_state": "SUPPORTED",
            "visual_verdict": "STABLE_SEGMENT_SUPPORT_PLAUSIBLE",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "The sampled path remains on the same visible response family through the stable interval.",
        },
        {
            "case_id": "F183_FORWARD_F260_STOP",
            "figure": "STOP_REASON_ATLAS.png",
            "seed_frame": 183,
            "frame_or_range": "F260",
            "algorithm_state": "UNKNOWN",
            "visual_verdict": "SAFE_STOP_WITH_VISIBLE_STRUCTURE",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "A structure remains human-visible, but the far proposal exceeds the frozen local corridor; stopping is safer than accepting a jump.",
        },
        {
            "case_id": "F264_BACKWARD_F183_CHECKPOINT",
            "figure": "CHECKPOINT_COMPARISON_ATLAS.png",
            "seed_frame": 264,
            "frame_or_range": "F183",
            "algorithm_state": "SUPPORTED_NUMERIC_MISMATCH",
            "visual_verdict": "SAME_RIDGE_SYSTEMATIC_OFFSET",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "The frozen 0.12 m check fails mainly from far-boundary offset; the image does not confirm a switch to another ridge.",
        },
        {
            "case_id": "F264_BACKWARD_F239_CHECKPOINT",
            "figure": "CHECKPOINT_COMPARISON_ATLAS.png",
            "seed_frame": 264,
            "frame_or_range": "F239",
            "algorithm_state": "SUPPORTED_NUMERIC_MISMATCH",
            "visual_verdict": "SAME_RIDGE_SYSTEMATIC_OFFSET",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "The checkpoint mismatch is an offset on the same apparent response, not a confirmed semantic ridge switch.",
        },
        {
            "case_id": "F264_SEGMENT_REVIEW",
            "figure": "F264_process_review.png",
            "seed_frame": 264,
            "frame_or_range": "F166,F215,F264,F266,F269",
            "algorithm_state": "SUPPORTED",
            "visual_verdict": "SAME_RESPONSE_WITH_OFFSET_RISK",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "Sampled frames remain on the same apparent ridge family, while checkpoint offsets show that numerical support is not exact geometry truth.",
        },
        {
            "case_id": "F264_FORWARD_F270_STOP",
            "figure": "F264_process_review.png",
            "seed_frame": 264,
            "frame_or_range": "F270",
            "algorithm_state": "UNKNOWN",
            "visual_verdict": "CONSERVATIVE_STOP_ACCEPTABLE",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "The pair is not extended beyond the frozen evidence gate.",
        },
        {
            "case_id": "F454_BACKWARD_F405_STOP",
            "figure": "STOP_REASON_ATLAS.png",
            "seed_frame": 454,
            "frame_or_range": "F405",
            "algorithm_state": "UNKNOWN",
            "visual_verdict": "INPUT_AVAILABILITY_STOP",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "P0 is unavailable for both boundaries; this is an input-availability stop, not an image-semantic claim.",
        },
        {
            "case_id": "F454_BACKWARD_F427_CHECKPOINT",
            "figure": "CHECKPOINT_COMPARISON_ATLAS.png",
            "seed_frame": 454,
            "frame_or_range": "F427",
            "algorithm_state": "SUPPORTED_NUMERIC_MISMATCH",
            "visual_verdict": "SAME_RIDGE_SYSTEMATIC_OFFSET",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "This is the largest checkpoint disagreement, but the overlay remains on the same apparent response rather than a confirmed neighboring ridge.",
        },
        {
            "case_id": "F454_FORWARD_F472_CHECKPOINT",
            "figure": "CHECKPOINT_COMPARISON_ATLAS.png",
            "seed_frame": 454,
            "frame_or_range": "F472",
            "algorithm_state": "SUPPORTED",
            "visual_verdict": "CHECKPOINT_CONSISTENT",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "Automatic and manual boundary geometry pass the frozen checkpoint comparison.",
        },
        {
            "case_id": "F454_LATE_SEGMENT_REVIEW",
            "figure": "F454_process_review.png",
            "seed_frame": 454,
            "frame_or_range": "F406,F430,F454,F468,F472,F481",
            "algorithm_state": "SUPPORTED",
            "visual_verdict": "LATE_SEGMENT_SUPPORT_PLAUSIBLE",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "The sampled late path remains on the same apparent response family; F427 retains a measurable offset caveat.",
        },
        {
            "case_id": "F454_FORWARD_F482_STOP",
            "figure": "F454_process_review.png",
            "seed_frame": 454,
            "frame_or_range": "F482",
            "algorithm_state": "UNKNOWN",
            "visual_verdict": "INPUT_AVAILABILITY_STOP",
            "semantic_ridge_switch_confirmed": False,
            "false_support_confirmed": False,
            "note": "P0 is unavailable; optional context must exit rather than extrapolate.",
        },
    ]


def main() -> None:
    pre = read_json(PRE / "PRE_REFERENCE_SUMMARY.json")
    audit = read_json(POST / "COMPUTED_AUDIT_SUMMARY.json")
    verdicts = visual_verdicts()
    write_csv(POST / "MANUAL_VISUAL_VERDICTS.csv", verdicts)

    segment_lengths = [4, 5, 85, 15, 18, 77, 99, 6, 49, 28]
    final = {
        "schema": "R02_LOCAL_BOUNDARY_OBSERVABILITY_FINAL_SUMMARY_V1",
        "direct_answer": "PARTIAL_NOT_YET_SAFE_AS_A_GENERAL_INTERFACE",
        "direct_answer_text": (
            "Sparse manual anchors initialize useful local propagation, but the current system does not yet fully achieve "
            "follow-when-observable and stop-when-not: stable intervals and the short entrance interval work, while F66 "
            "contains a SUPPORTED curve-state error caused by rigid shape propagation."
        ),
        "manual_semantic_checkpoints": {
            "frame_count": audit["actual_manual_checkpoint_frame_count"],
            "boundary_record_count": audit["actual_manual_boundary_record_count"],
            "frames": audit["actual_manual_checkpoint_frames"],
            "primary_independent_seeds": audit["primary_seed_frames"],
            "draft_interpretation": "UI_FINALIZE_OMISSION_GEOMETRY_USER_CONFIRMED",
        },
        "scientific_isolation": {
            "single_seed_geometry_only_per_run": True,
            "other_checkpoint_geometry_hidden_until_freeze": True,
            "pre_reference_freeze_manifest_sha256": audit["pre_reference_freeze_manifest_sha256"],
            "pre_reference_file_count": audit["pre_reference_file_count"],
            "parameter_tuning": False,
        },
        "algorithm_reported_observability": {
            "pair_safe_directional_segment_count": pre["pair_safe_directional_segment_count"],
            "pair_safe_directional_segments": [
                {"seed": 62, "direction": "BACKWARD", "start": 59, "end": 62},
                {"seed": 62, "direction": "FORWARD", "start": 62, "end": 66},
                {"seed": 150, "direction": "BACKWARD", "start": 66, "end": 150},
                {"seed": 150, "direction": "FORWARD", "start": 150, "end": 164},
                {"seed": 183, "direction": "BACKWARD", "start": 166, "end": 183},
                {"seed": 183, "direction": "FORWARD", "start": 183, "end": 259},
                {"seed": 264, "direction": "BACKWARD", "start": 166, "end": 264},
                {"seed": 264, "direction": "FORWARD", "start": 264, "end": 269},
                {"seed": 454, "direction": "BACKWARD", "start": 406, "end": 454},
                {"seed": 454, "direction": "FORWARD", "start": 454, "end": 481},
            ],
            "merged_pair_safe_components": pre["supported_components"],
            "pair_safe_supported_frame_count": pre["pair_safe_supported_frame_count"],
            "pair_safe_supported_frame_fraction": pre["pair_safe_supported_frame_fraction"],
            "unknown_frame_count": pre["unknown_for_optional_context_frame_count"],
            "unknown_frame_fraction": pre["unknown_for_optional_context_frame_fraction"],
            "boundary_independent_state_counts": pre["boundary_independent_state_counts"],
            "segment_length_frames": segment_lengths,
            "segment_length_median": 23.0,
            "segment_length_mean": 38.6,
            "stop_reason_distribution_pair_safe": audit["stop_reason_distribution_pair_safe"],
            "coverage_is_algorithm_claim_not_validated_safe_fraction": True,
        },
        "post_freeze_audit": {
            "checkpoint_crossings": audit["checkpoint_crossing_audit_count"],
            "checkpoint_consistent": audit["checkpoint_geometry_consistent_count"],
            "checkpoint_inconsistent": audit["checkpoint_geometry_inconsistent_count"],
            "natural_overlap_audits": audit["natural_overlap_audit_count"],
            "natural_overlap_consistent": audit["natural_overlap_consistent_count"],
            "confirmed_semantic_ridge_switch_count": 0,
            "confirmed_near_far_reversal_count": 0,
            "confirmed_false_support_curve_state_count": 1,
            "strongest_false_support_case": {
                "frame": 66,
                "paths": ["F62_FORWARD", "F150_BACKWARD"],
                "verdict": "FALSE_SUPPORT_CURVE_STATE",
                "max_node_median_disagreement_m": 0.11560599999999965,
                "max_node_disagreement_m": 0.41707099999999997,
                "max_shape_rms_m": 0.1828175025611994,
            },
            "strongest_premature_stop_candidate": {
                "frame": 67,
                "seed": 62,
                "reason": "SAR_BOUNDARY_NEAR:BOUNDARY_RESPONSE_TOO_WEAK",
                "verdict": "HUMAN_VISIBLE_TRACE_REMAINS_BUT_CONSERVATIVE_STOP_IS_SAFER",
            },
            "strongest_checkpoint_disagreement": audit["strongest_checkpoint_disagreement"],
            "manual_visual_verdict_count": len(verdicts),
        },
        "representation_verdict": {
            "current_state": audit["representation"],
            "curved_entry": "PRIMARY_REPRESENTATION_FAILURE_MODE",
            "reason": "A whole-curve scalar shift freezes curvature and cannot naturally express curved-to-straight evolution.",
        },
        "research_questions": {
            "sparse_anchors_initialize_local_propagation": "YES",
            "weak_evidence_stop_without_silent_error": "PARTIALLY_ESTABLISHED",
            "curved_to_straight_naturally_followed": "NO_CURRENT_RIGID_STATE_IS_A_PRIMARY_FAILURE_MODE",
            "optional_scene_geometry_context_qualified": "NO_NOT_YET",
        },
        "optional_scene_context_policy": {
            "current_qualification": "NOT_QUALIFIED_TO_CONSTRAIN_PERSON",
            "allowed_interim_use": "EXPERIMENTAL_READ_ONLY_DIAGNOSTIC_NEAR_MANUAL_ANCHORS_OR_STABLE_INTERVALS",
            "mandatory_exit_state": "UNKNOWN_MEANS_NO_SCENE_GEOMETRY_CONSTRAINT",
            "qualification_blocker": "No shape-adaptation or shape-observability gate; F66 proves center/evidence support can coexist with a wrong full curve state.",
        },
        "structural_recommendations_not_implemented": [
            "Retain the frozen rigid propagator as a comparator.",
            "Add a low-dimensional or regularized node-wise curve-shape update instead of one scalar shift for all nodes.",
            "Add a shape-observability gate based on curve residual and shape change, not center continuity alone.",
            "Keep near and far observability separate; accept pair context only when both boundaries and corridor geometry are safe.",
            "Do not bridge UNKNOWN gaps or tune thresholds against checkpoints.",
        ],
        "scientific_non_claims": {
            "scientifically_validated_safe_frame_fraction_established": False,
            "full_stream_boundary_trajectory_recovered": False,
            "person_experiment_run": False,
            "tree_experiment_run": False,
            "final_localization_run": False,
            "r04_accessed": False,
        },
        "artifacts": {
            "timeline_figure": "figures/R02_LOCAL_BOUNDARY_OBSERVABILITY_TIMELINE.png",
            "entrance_figure": "figures/ENTRANCE_F057_F068_CURVE_EVOLUTION.png",
            "f66_conflict_figure": "figures/F066_NATURAL_OVERLAP_SHAPE_CONFLICT.png",
            "manual_visual_verdicts": "post_freeze_audit/MANUAL_VISUAL_VERDICTS.csv",
            "report": "REPORT.md",
        },
    }
    write_json(OUT / "FINAL_SUMMARY.json", final)

    report = f"""# R02 local observability and safe boundary propagation

## Direct answer

The sparse manual-anchor plus local-propagation design is useful, but it does **not yet fully implement** “follow when observable, stop when not observable.” Stable intervals and the short entrance interval are usable; however, F66 contains one confirmed `SUPPORTED` curve-state error. The error is caused by a rigid curve representation, not by a demand for complete temporal closure.

## Scientific setup

- Eleven manual semantic checkpoints were recovered at F47, F62, F82, F150, F183, F239, F264, F278, F427, F454, and F472, comprising 22 near/far boundary records.
- F62, F150, F183, F264, and F454 were used as independent primary seeds.
- Each propagation process read only one isolated seed containing two boundaries from one frame. Other checkpoint geometry remained hidden until all pre-reference results were frozen and hashed.
- The frozen source and thresholds were reused without tuning. `DRAFT` was treated as a UI-finalization omission because the user confirmed the geometry semantics.

## What the propagator actually represents

The manual polyline is sampled into `d_perp(theta)` nodes, but every frame update applies one scalar displacement to the entire curve. Nodes provide evidence samples; they are not independently updated. Therefore the centered curve shape is invariant within a path. Near and far evidence is calculated separately, while the pair-safe comparator stops both if either boundary or the pair corridor becomes unsafe.

This matters because a stable center is not proof of a correct full curve. The current state cannot naturally represent the real entrance evolution from curved boundaries toward straighter parallel boundaries.

## Algorithm-reported local support

The ten independent directional pair-safe segments are:

| Seed | Backward | Forward |
|---|---:|---:|
| F62 | F59-F62 | F62-F66 |
| F150 | F66-F150 | F150-F164 |
| F183 | F166-F183 | F183-F259 |
| F264 | F166-F264 | F264-F269 |
| F454 | F406-F454 | F454-F481 |

Their union forms three components: F59-F164, F166-F269, and F406-F481. The algorithm labels 286/495 frames pair-safe (`57.78%`) and 209/495 frames unknown (`42.22%`). This is an algorithm-reported coverage figure, **not** a scientifically validated safe fraction.

The independent-boundary diagnostic finds near support on 307 frames, far support on 286 frames, and 21 partial frames where near continues after far becomes unknown. These 21 frames are diagnostic only and are not accepted as pair-safe context.

Directional segment lengths are 4, 5, 85, 15, 18, 77, 99, 6, 49, and 28 frames (median 23, mean 38.6). Pair-safe stop causes include weak response in seven directions, fragmented support in two, one ridge-jump stop, and four P0-unavailable boundary events.

## Post-freeze checkpoint and overlap audit

Six paths naturally crossed another manual checkpoint. Three passed the frozen 0.12 m comparison (F82 from F150-backward, F239 from F183-forward, and F472 from F454-forward); three failed numerically. The failures at F183/F239 from F264-backward and F427 from F454-backward look like systematic offsets on the same apparent response, not confirmed switches to another ridge.

No strict semantic ridge switch or near/far reversal was confirmed at the manual checkpoints. That does not make the full state safe: all three natural overlap audits failed the frozen consistency test.

## Strongest false support: F66

At F66, F62-forward preserves the curved entrance shape while F150-backward transports a nearly horizontal stable-segment shape backward. Both paths are labeled pair-safe `SUPPORTED`, yet their maximum node disagreement is 0.4171 m and shape RMS disagreement is 0.1828 m. The two full boundary states cannot both be correct.

This is recorded as `FALSE_SUPPORT_CURVE_STATE`. It is more serious than early `UNKNOWN`, even though the image does not prove that either path jumped to a different physical ridge. It proves that the observability rule does not currently protect the full curve state.

## Strongest possible false unknown: F67

F62-forward stops before F67 because near response is too weak. A human-visible trace remains in the raw image, so this is the strongest premature-stop candidate. The conservative stop is nevertheless safer than forcing continuation, and its severity is lower than the F66 false support.

F260 similarly retains visible structure, but the far proposal exceeds the frozen corridor; treating it as unknown is a defensible safe stop. F405 and F482 stop because P0 is unavailable and therefore express input availability, not image ambiguity.

## Final judgments

1. Sparse manual near/far semantic anchors are sufficient to initialize useful local propagation: **yes**.
2. The system stops on weak evidence instead of always forcing continuity: **partly established**, but not sufficient because F66 shows a supported wrong curve state.
3. The curved-to-straight entrance is a **primary failure mode of the rigid representation**.
4. The interface is **not yet qualified to constrain PERSON**, even as optional context. It may only be used as an experimental read-only diagnostic near manual anchors or in stable intervals, and `UNKNOWN` must mean complete withdrawal of the scene-geometry constraint.

## Structural next step, not implemented here

Keep the frozen rigid method as a comparator. A future version needs a constrained shape-adaptive state (for example, low-dimensional or regularized node-wise deformation) and an explicit shape-observability gate. Near/far observability should remain separate, pair context should require both plus safe corridor geometry, and no method should bridge unknown gaps or tune thresholds to checkpoints.

## Scope and non-claims

No PERSON, tree-anchor, azimuth-recalibration, final-localization, R04, or `old_work` work was run. The manual JSONL files remained read-only. Full-stream boundary recovery and a scientifically validated safe-frame fraction are not claimed.
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(OUT / "FINAL_SUMMARY.json")
    print(OUT / "REPORT.md")
    print(POST / "MANUAL_VISUAL_VERDICTS.csv")


if __name__ == "__main__":
    main()
