# GM17 Factor Field Dictionary

Date: 2026-06-02

Purpose: support Phase3 factor prior audit by documenting important fields, origins, leakage class, join stage, allowed usage, and consuming factors.

Boundary: documentation-only. This file does not authorize new inference code, candidate-bank changes, experiments, ranker training, OOF calibration, or GM17 mainline replacement.

## Leakage Classes

- `inference_safe`: may be used in inference if field origin and join stage are respected.
- `diagnostic_inference_safe`: may be used in diagnostic prototypes, but must be re-audited before calibration/mainline use.
- `eval_only_blocked`: must not enter inference.
- `future_inference_required`: concept is allowed, but current inference-safe field is not standardized.

## Field Dictionary

| field | field_origin | leakage_class | join_stage | allowed_usage | consumed_by |
|---|---|---|---|---|---|
| `candidate_id` | v2.2 candidate bank / diagnostic outputs | inference_safe | candidate-level key | join key only | all candidate factors |
| `target_identity` | boundary-safe row identity | inference_safe | row-level key | row grouping and joins | all factors |
| `gm17_track_id` | boundary-safe track metadata | inference_safe | track-level key | track grouping | transition_factor, optical_temporal_factor |
| `sar_frame_num` | boundary-safe frame metadata | inference_safe | frame-level key | temporal ordering | transition_factor, optical_temporal_factor |
| `candidate_source` | v2.2 candidate bank | inference_safe | candidate-level | source family mapping; visible source is veto/uncertainty only | source_factor, visibility_factor |
| `r` | candidate bank / factor diagnostics | inference_safe | candidate-level | fan-polar state | geometry_factor, transition_factor |
| `cross` | candidate bank / factor diagnostics | inference_safe | candidate-level | fan-polar state | geometry_factor, transition_factor |
| `az` | candidate bank / factor diagnostics | inference_safe | candidate-level | fan-polar state | geometry_factor, transition_factor |
| `heading` | candidate bank / factor diagnostics | inference_safe | candidate-level | OBB state | geometry_factor, transition_factor |
| `w` | candidate bank / factor diagnostics | inference_safe | candidate-level | OBB size | geometry_factor, transition_factor |
| `h` | candidate bank / factor diagnostics | inference_safe | candidate-level | OBB size | geometry_factor, transition_factor |
| `delta_r_from_pred` | candidate bank/factor diagnostic derivation | inference_safe | candidate-level | geometry compatibility | geometry_factor |
| `delta_cross_from_pred` | candidate bank/factor diagnostic derivation | inference_safe | candidate-level | geometry compatibility | geometry_factor |
| `delta_az_from_pred` | candidate bank/factor diagnostic derivation | inference_safe | candidate-level | geometry compatibility | geometry_factor |
| `candidate_direction_bin` | candidate expansion / state diagnostics | inference_safe | candidate-level | direction state | direction_factor, transition_factor |
| `signed_escape_decision` | signed escape posterior diagnostic | inference_safe | row-level joined to candidates | signed direction prior | direction_factor, transition_factor |
| `P_near` | signed escape posterior diagnostic | inference_safe | row-level joined to candidates | direction posterior | direction_factor |
| `P_pos_escape` | signed escape posterior diagnostic | inference_safe | row-level joined to candidates | direction posterior | direction_factor |
| `P_neg_escape` | signed escape posterior diagnostic | inference_safe | row-level joined to candidates | direction posterior | direction_factor |
| `P_ambiguous` | signed escape posterior / uncertainty diagnostic | diagnostic_inference_safe | row-level joined to candidates | ambiguity/uncertainty | sar_structure_factor, uncertainty_factor |
| `P_artifact` | signed escape posterior / uncertainty diagnostic | diagnostic_inference_safe | row-level joined to candidates | artifact/visible veto | sar_structure_factor, visibility_factor, uncertainty_factor |
| `posterior_confidence` | signed escape posterior diagnostic | inference_safe | row-level joined to candidates | confidence | direction_factor, uncertainty_factor |
| `posterior_margin` | signed escape posterior diagnostic | inference_safe | row-level joined to candidates | confidence margin | direction_factor, uncertainty_factor |
| `signed_direction_match` | factor diagnostic | inference_safe | candidate-level | direction compatibility | direction_factor, source_factor |
| `source_prior` | factor diagnostic/source mapping | diagnostic_inference_safe | candidate-level | source prior | source_factor |
| `directional_shell_score` | SAR/geometry diagnostic | diagnostic_inference_safe | candidate-level | shell support | geometry_factor, sar_structure_factor, source_factor |
| `geometry_escape_refined_score` | SAR/geometry diagnostic | diagnostic_inference_safe | candidate-level | escape geometry/SAR support | geometry_factor, sar_structure_factor |
| `refined_geometry_score` | factor diagnostic | diagnostic_inference_safe | candidate-level | geometry support | geometry_factor |
| `track_escape_evidence` | track/posterior diagnostic | diagnostic_inference_safe | row-level joined to candidates | escape support | source_factor, sar_structure_factor |
| `escape_conflict_score` | SAR/posterior diagnostic | diagnostic_inference_safe | row-level joined to candidates | conflict/uncertainty | sar_structure_factor, uncertainty_factor |
| `E_geometry` | state-energy diagnostic | diagnostic_inference_safe | candidate-level | diagnostic energy only | geometry_factor |
| `E_sar_structure` | state-energy diagnostic | diagnostic_inference_safe | candidate-level | diagnostic SAR structure energy | sar_structure_factor |
| `E_uncertainty` | state-energy diagnostic | diagnostic_inference_safe | candidate-level | diagnostic uncertainty energy | uncertainty_factor |
| `E_direction` | state-energy diagnostic | diagnostic_inference_safe | candidate-level | diagnostic direction energy | direction_factor |
| `optical_temporal_consistency_score` | optical-to-SAR temporal diagnostic | inference_safe | row/candidate joined prior | soft temporal prior only | optical_temporal_factor, transition_factor |
| `temporal_factor_score` | optical-to-SAR temporal diagnostic | inference_safe | row-level prior | soft temporal prior only | optical_temporal_factor |
| `pred_r` | boundary-safe temporal/fan-polar prior | inference_safe | row-level prior | soft prior only | optical_temporal_factor |
| `pred_az` | boundary-safe temporal/fan-polar prior | inference_safe | row-level prior | soft prior only | optical_temporal_factor |
| `pred_cross` | boundary-safe temporal/fan-polar prior | inference_safe | row-level prior | soft prior only | optical_temporal_factor |
| `visible_factor` | visible support diagnostic | diagnostic_inference_safe | row/candidate diagnostic | veto/uncertainty/factor only; no full-center generation | visibility_factor, uncertainty_factor |
| `E_visible_veto` | state-energy diagnostic | diagnostic_inference_safe | candidate-level diagnostic | veto/uncertainty only | visibility_factor |
| `two_stage_gate_reason` | current selector/gate diagnostic | diagnostic_inference_safe | selected-row diagnostic | audit comparison only | final_arbitration_factor |
| `patch_action` | B patch diagnostic output | diagnostic_inference_safe | selected-row diagnostic | audit comparison only; patch dependency risk | final_arbitration_factor |
| `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg` | eval table | eval_only_blocked | eval-only | audit/evaluation only | none in inference |
| `candidate_iou` | eval table | eval_only_blocked | eval-only | audit/evaluation only | none in inference |
| `candidate_center_err_px` | eval table | eval_only_blocked | eval-only | audit/evaluation only | none in inference |
| `rot_iou` | eval table | eval_only_blocked | eval-only | audit/evaluation only | none in inference |
| `center_err_px` | eval table | eval_only_blocked | eval-only | audit/evaluation only | none in inference |
| `condition_type` | eval/annotation table | eval_only_blocked | eval-only | group audit only | none in inference |
| `truncation_degree` | eval/annotation table | eval_only_blocked | eval-only | group audit only | none in inference |
| `occlusion_degree` | eval/annotation table | eval_only_blocked | eval-only | group audit only | none in inference |

## Usage Gate

- PASS: Complete-vehicle factors may consume `inference_safe` fields after join-stage audit.
- WARN: `diagnostic_inference_safe` fields may remain in diagnostic prototypes, but require explicit patch/dependency audit before calibration.
- FAIL: `eval_only_blocked` fields must not enter inference.
- BLOCKED: `future_inference_required` fields cannot be active until standardized.
