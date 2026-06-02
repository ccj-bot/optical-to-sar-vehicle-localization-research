# GM17 Phase3 Factor Acceptance Matrix

Date: 2026-06-02

Status: Phase3 audit matrix. This document records audit decisions only. It does not authorize experiments, calibration, learned weights, code changes, candidate-bank changes, or GM17 mainline replacement.

## 1. Source Boundary

This matrix is derived only from the formal baseline files listed in `docs/gm17_phase3_factor_prior_audit_execution.md`.

No untracked historical material, runtime outputs, archives, task scripts, tool scripts, old prompt dumps, auth/proxy material, or non-listed logs were used.

## 2. Grade Mapping

The matrix uses only `PASS`, `WARN`, `FAIL`, and `BLOCKED` as audit grades.

Baseline `evidence_grade` values from `docs/gm17_factor_prior_registry.md` are not audit grades. They are evidence-strength labels and are mapped through leakage, field-origin, join-stage, branch-scope, double-counting, and patch-dependency checks before receiving one of the four audit grades.

## 3. Matrix Schema

Each factor record includes:

- `factor_name`
- `branch_scope`
- `allowed_phase`
- `field_origin`
- `leakage_class`
- `join_stage`
- `inference_safe_fields`
- `current_code_fields`
- `monotonicity`
- `valid_range`
- `potential_transform`
- `cost_transform`
- `clip_policy`
- `missing_value_policy`
- `correlated_factors`
- `double_counting_risk`
- `patch_dependency_risk`
- `active_in_complete_vehicle`
- `diagnostic_only`
- `should_be_learned_later`
- `preliminary_grade`
- `grade_justification`
- `required_control_condition`
- `Phase4_eligibility`
- `blocker_if_any`

## 4. Acceptance Overview

| factor_name | preliminary_grade | Phase4_eligibility | blocker_if_any |
|---|---|---|---|
| `geometry_factor` | `WARN` | Conditional candidate | `B002` |
| `direction_factor` | `WARN` | Conditional candidate | `B003` |
| `source_factor` | `WARN` | Conditional candidate for non-visible source families only | `B004` |
| `sar_structure_factor` | `WARN` | Not current preferred candidate; diagnostic/support-separation review only | `B005` |
| `uncertainty_factor` | `WARN` | Not current preferred candidate; diagnostic/uncertainty-route review only | `B005` |
| `optical_temporal_factor` | `WARN` | Conditional candidate | `B007` |
| `transition_factor` | `WARN` | Conditional candidate | `B007` |
| `final_arbitration_factor` | `BLOCKED` | Not eligible as active Phase4 scoring factor | `B006` |
| `visibility_factor` | `BLOCKED` | Not eligible for complete-vehicle Phase4 | `B008` |
| `missing_extent_factor` | `BLOCKED` | Not eligible | `B008`, `B009` |
| `visible_full_center_offset_factor` | `BLOCKED` | Not eligible | `B008`, `B009` |

## 5. Detailed Factor Records

### 5.1 `geometry_factor`

| Field | Value |
|---|---|
| `factor_name` | `geometry_factor` |
| `branch_scope` | `complete_vehicle` |
| `allowed_phase` | `Phase3` |
| `field_origin` | Fixed candidate bank plus state-energy diagnostic tables. |
| `leakage_class` | `inference_safe` |
| `join_stage` | Candidate-level node fields joined by `candidate_id`. |
| `inference_safe_fields` | `r`, `cross`, `az`, `heading`, `w`, `h`, `delta_r_from_pred`, `delta_cross_from_pred`, `delta_az_from_pred`, `refined_geometry_score`, `geometry_escape_refined_score` |
| `current_code_fields` | `E_geometry`, `refined_geometry_score`, `geometry_escape_refined_score`, `delta_*` |
| `monotonicity` | Higher support score should reduce cost; larger raw deltas require transform before interpretation. |
| `valid_range` | Geometry support scores in `[0, 1]`; fan-polar coordinates finite numeric values. |
| `potential_transform` | Normalize geometry support into `[0, 1]` potential. |
| `cost_transform` | `-log(potential + eps)` |
| `clip_policy` | Clip support potential to `[eps, 1]`. |
| `missing_value_policy` | Required coordinate fields missing blocks use; neutral default only in diagnostic tables. |
| `correlated_factors` | `sar_structure_factor`, `source_factor`, `transition_factor` |
| `double_counting_risk` | Geometry escape features may include SAR shell evidence. |
| `patch_dependency_risk` | `low` |
| `active_in_complete_vehicle` | `true` |
| `diagnostic_only` | `false` |
| `should_be_learned_later` | `yes` |
| `preliminary_grade` | `WARN` |
| `grade_justification` | Inference-safe and physically meaningful, but geometry/SAR shell overlap is not fully separated. |
| `required_control_condition` | Declare which shell terms belong to geometry and which belong to SAR structure. |
| `Phase4_eligibility` | Conditional candidate. |
| `blocker_if_any` | `B002` |

### 5.2 `direction_factor`

| Field | Value |
|---|---|
| `factor_name` | `direction_factor` |
| `branch_scope` | `complete_vehicle` |
| `allowed_phase` | `Phase3` |
| `field_origin` | Signed escape posterior and state-energy diagnostic tables. |
| `leakage_class` | `inference_safe` |
| `join_stage` | Row-level posterior fields joined to candidate-level direction fields. |
| `inference_safe_fields` | `candidate_direction_bin`, `signed_escape_decision`, `P_near`, `P_pos_escape`, `P_neg_escape`, `P_ambiguous`, `signed_direction_match`, `posterior_confidence`, `posterior_margin` |
| `current_code_fields` | `E_direction`, `signed_direction_match`, `P_*`, `signed_escape_decision` |
| `monotonicity` | Higher matching posterior and margin should lower cost. |
| `valid_range` | Probabilities and match scores in `[0, 1]`; direction states from controlled labels. |
| `potential_transform` | Map candidate-direction posterior and match score into `[0, 1]` potential. |
| `cost_transform` | `-log(potential + eps)` |
| `clip_policy` | Clip posterior-derived potential to `[eps, 1]`. |
| `missing_value_policy` | Missing posterior blocks diagnostic use for the row. |
| `correlated_factors` | `source_factor`, `uncertainty_factor`, `final_arbitration_factor` |
| `double_counting_risk` | Source-family trust can embed direction assumptions. |
| `patch_dependency_risk` | `low` |
| `active_in_complete_vehicle` | `true` |
| `diagnostic_only` | `false` |
| `should_be_learned_later` | `yes` |
| `preliminary_grade` | `WARN` |
| `grade_justification` | Direction posterior is inference-safe, but source-direction overlap must be controlled. |
| `required_control_condition` | Treat source prior as source-only unless explicitly conditioned on direction. |
| `Phase4_eligibility` | Conditional candidate. |
| `blocker_if_any` | `B003` |

### 5.3 `source_factor`

| Field | Value |
|---|---|
| `factor_name` | `source_factor` |
| `branch_scope` | `complete_vehicle`, except visible source family is `partial_visibility_veto` |
| `allowed_phase` | `Phase3` for non-visible families; visible source behavior veto/uncertainty only until `Phase7`. |
| `field_origin` | Candidate bank source labels plus diagnostic source priors. |
| `leakage_class` | `inference_safe`; visible family is `diagnostic_inference_safe` only. |
| `join_stage` | Candidate-level source label and row-level support fields. |
| `inference_safe_fields` | `candidate_source`, `source_prior`; `directional_shell_score`, `track_escape_evidence`, and `signed_direction_match` may be referenced only as controlled diagnostic context or gated support context. |
| `current_code_fields` | `candidate_source`, `source_prior`, source-family mapping in diagnostics. |
| `monotonicity` | Source prior alone is not monotonic; monotonic only after direction and SAR support are included. |
| `valid_range` | Source priors and support scores in `[0, 1]`; labels from controlled source set. |
| `potential_transform` | Source prior multiplied or blended with direction/SAR support. |
| `cost_transform` | `-log(potential + eps)` |
| `clip_policy` | Clip blended potential to `[eps, 1]`. |
| `missing_value_policy` | Unknown source maps to diagnostic `WARN` and conservative low trust. |
| `correlated_factors` | `direction_factor`, `geometry_factor`, `sar_structure_factor`, `visibility_factor` |
| `double_counting_risk` | Source family may encode geometry, SAR structure, and direction assumptions; diagnostic support fields must not be counted again as independent source-prior evidence unless factor ownership is explicitly declared. |
| `patch_dependency_risk` | `low` |
| `active_in_complete_vehicle` | `true` for base/wedge/bidirectional/track_signed; visible is not full-center active. |
| `diagnostic_only` | `false` for complete-vehicle families; visible-related behavior is diagnostic/veto-only. |
| `should_be_learned_later` | `yes` |
| `preliminary_grade` | `WARN` |
| `grade_justification` | Useful source partition, but visible-source and source-direction leakage require explicit control. |
| `required_control_condition` | Limit Phase4 source use to non-visible families; visible source remains veto/uncertainty only; `directional_shell_score`, `track_escape_evidence`, and `signed_direction_match` remain gated support context unless ownership is explicitly declared. |
| `Phase4_eligibility` | Conditional candidate for non-visible source families only. |
| `blocker_if_any` | `B004` |

### 5.4 `sar_structure_factor`

| Field | Value |
|---|---|
| `factor_name` | `sar_structure_factor` |
| `branch_scope` | `complete_vehicle` |
| `allowed_phase` | `Phase3` |
| `field_origin` | State-energy diagnostic and fixed-bank factor tables. |
| `leakage_class` | `diagnostic_inference_safe` until fields are traced to non-patch origins. |
| `join_stage` | Candidate-level SAR structure joined with row-level posterior uncertainty. |
| `inference_safe_fields` | `directional_shell_score`, `geometry_escape_refined_score`, `track_escape_evidence`, `escape_conflict_score`, `P_ambiguous`, `P_artifact`, `E_sar_structure`, `E_uncertainty` |
| `current_code_fields` | `E_sar_structure`, `E_uncertainty`, `directional_shell_score`, `escape_conflict_score` |
| `monotonicity` | Higher support lowers cost; higher ambiguity/conflict raises uncertainty cost. |
| `valid_range` | Support, ambiguity, and normalized scores in `[0, 1]`. |
| `potential_transform` | Support potential from shell/geometry/escape evidence; uncertainty potential from ambiguity/conflict. |
| `cost_transform` | `-log(potential + eps)` for support and/or uncertainty route cost. |
| `clip_policy` | Clip normalized scores to `[eps, 1]`. |
| `missing_value_policy` | Missing SAR support defaults to conservative uncertainty in diagnostics. |
| `correlated_factors` | `geometry_factor`, `uncertainty_factor`, `final_arbitration_factor` |
| `double_counting_risk` | Overlaps with geometry shell evidence and uncertainty factor. |
| `patch_dependency_risk` | `medium` |
| `active_in_complete_vehicle` | Phase3 diagnostic/support-separation review only; not active Phase4 scoring. |
| `diagnostic_only` | Controlled diagnostic/review until support-vs-uncertainty and patch risks are separated. |
| `should_be_learned_later` | `yes` |
| `preliminary_grade` | `WARN` |
| `grade_justification` | Strong protection evidence, but SAR support, ambiguity, and B patch behavior are not cleanly separated. |
| `required_control_condition` | Split support evidence from uncertainty evidence before Phase4 or calibration. |
| `Phase4_eligibility` | Not a current preferred candidate; diagnostic/support-separation review only. |
| `blocker_if_any` | `B005` |

### 5.5 `uncertainty_factor`

| Field | Value |
|---|---|
| `factor_name` | `uncertainty_factor` |
| `branch_scope` | `complete_vehicle` and future `partial_visibility` |
| `allowed_phase` | `Phase3` for complete-vehicle uncertainty; `Phase7` for partial-visibility extensions. |
| `field_origin` | Signed posterior, state-energy diagnostics, SAR ambiguity diagnostics. |
| `leakage_class` | `diagnostic_inference_safe` until B patch coupling is separated. |
| `join_stage` | Row-level and candidate-level uncertainty fields joined to node and final action. |
| `inference_safe_fields` | `posterior_confidence`, `posterior_margin`, `escape_conflict_score`, `P_ambiguous`, `P_artifact`, `E_uncertainty` |
| `current_code_fields` | `E_uncertainty`, `sar_uncertainty_soft`, `P_ambiguous`, `P_artifact` |
| `monotonicity` | Higher ambiguity/conflict and lower confidence should increase uncertainty cost. |
| `valid_range` | Posterior and uncertainty scores in `[0, 1]`. |
| `potential_transform` | Penalize candidates or route final action to `reject`/`uncertain`. |
| `cost_transform` | `-log(potential + eps)` for confidence potential, or positive uncertainty penalty in diagnostics. |
| `clip_policy` | Clip normalized uncertainty and confidence potentials to `[eps, 1]`. |
| `missing_value_policy` | Missing uncertainty fields default to conservative `WARN`, not optimistic pass. |
| `correlated_factors` | `sar_structure_factor`, `direction_factor`, `final_arbitration_factor`, `visibility_factor` |
| `double_counting_risk` | Can duplicate SAR ambiguity, direction conflict, and final arbitration behavior. |
| `patch_dependency_risk` | `medium` |
| `active_in_complete_vehicle` | Phase3 diagnostic/support-separation review only; not active Phase4 scoring. |
| `diagnostic_only` | Controlled diagnostic/review until support-vs-uncertainty and patch risks are separated. |
| `should_be_learned_later` | `yes` |
| `preliminary_grade` | `WARN` |
| `grade_justification` | Strong protection evidence, but patch coupling and overlap with SAR structure/final arbitration remain unresolved. |
| `required_control_condition` | Separate uncertainty routing from SAR support and final arbitration behavior. |
| `Phase4_eligibility` | Not a current preferred candidate; diagnostic/uncertainty-route review only. |
| `blocker_if_any` | `B005` |

### 5.6 `optical_temporal_factor`

| Field | Value |
|---|---|
| `factor_name` | `optical_temporal_factor` |
| `branch_scope` | `complete_vehicle` |
| `allowed_phase` | `Phase3` |
| `field_origin` | Optical temporal inference tables and boundary-safe temporal features. |
| `leakage_class` | `inference_safe` |
| `join_stage` | Row-level and track-level prior joined to candidate nodes. |
| `inference_safe_fields` | `optical_temporal_consistency_score`, `temporal_factor_score`, `gm17_track_id`, `sar_frame_num`, `pred_r`, `pred_az`, `pred_cross` |
| `current_code_fields` | `E_optical_temporal`, `optical_temporal_consistency_score`, `temporal_factor_score` |
| `monotonicity` | Higher temporal consistency lowers cost softly. |
| `valid_range` | Consistency scores in `[0, 1]`; track/frame IDs finite and non-eval. |
| `potential_transform` | Soft prior potential; never direct center overwrite. |
| `cost_transform` | `-log(potential + eps)` |
| `clip_policy` | Clip potential to `[eps, 1]`. |
| `missing_value_policy` | Missing temporal prior defaults to neutral soft prior, not failure. |
| `correlated_factors` | `transition_factor`, `geometry_factor` |
| `double_counting_risk` | Can double-count smoothness with `transition_factor`. |
| `patch_dependency_risk` | `low` |
| `active_in_complete_vehicle` | `true` |
| `diagnostic_only` | `false` |
| `should_be_learned_later` | `yes` |
| `preliminary_grade` | `WARN` |
| `grade_justification` | Inference-safe soft prior, but smoothness overlap with transition must be controlled. |
| `required_control_condition` | Keep optical temporal as soft prior and separate from transition-edge continuity. |
| `Phase4_eligibility` | Conditional candidate. |
| `blocker_if_any` | `B007` |

### 5.7 `transition_factor`

| Field | Value |
|---|---|
| `factor_name` | `transition_factor` |
| `branch_scope` | `complete_vehicle` |
| `allowed_phase` | `Phase3` |
| `field_origin` | Fixed candidate state fields and track path diagnostics. |
| `leakage_class` | `inference_safe` |
| `join_stage` | Adjacent candidate-pair edge construction within each track. |
| `inference_safe_fields` | `r`, `cross`, `az`, `heading`, `w`, `h`, `candidate_direction_bin`, `signed_escape_decision`, `optical_temporal_consistency_score`, `gm17_track_id`, `sar_frame_num` |
| `current_code_fields` | `E_switch`, `incoming_edge_score`, `path_score`, `path_score_delta` |
| `monotonicity` | Larger state discontinuity raises transition cost. |
| `valid_range` | Finite coordinates, normalized heading convention, frame order per track. |
| `potential_transform` | Convert continuity score to edge potential. |
| `cost_transform` | `-log(potential + eps)` or equivalent positive transition cost. |
| `clip_policy` | Clip continuity potential to `[eps, 1]`; cap extreme edge costs in diagnostics. |
| `missing_value_policy` | Missing required state fields block edge construction. |
| `correlated_factors` | `optical_temporal_factor`, `direction_factor` |
| `double_counting_risk` | Can duplicate optical temporal smoothness and signed direction continuity. |
| `patch_dependency_risk` | `low` |
| `active_in_complete_vehicle` | `true` |
| `diagnostic_only` | `false` |
| `should_be_learned_later` | `yes` |
| `preliminary_grade` | `WARN` |
| `grade_justification` | Inference-safe track factor, but smoothness overlap and release-gate misuse must be controlled. |
| `required_control_condition` | Keep transition as edge continuity, not optical-temporal prior or release decision. |
| `Phase4_eligibility` | Conditional candidate. |
| `blocker_if_any` | `B007` |

### 5.8 `final_arbitration_factor`

| Field | Value |
|---|---|
| `factor_name` | `final_arbitration_factor` |
| `branch_scope` | `complete_vehicle_decision` |
| `allowed_phase` | `Phase3` diagnostic audit only. |
| `field_origin` | Diagnostic factor graph outputs and current B patch comparison artifacts. |
| `leakage_class` | `diagnostic_inference_safe`; not ready for calibration/mainline use until patch dependency is separated. |
| `join_stage` | Row-level final action after candidate/path scoring. |
| `inference_safe_fields` | Risk potential, direction potential, source potential, candidate potential, path proposal evidence, SAR uncertainty, normal keep signal. |
| `current_code_fields` | `Z_t`, `phi_final`, `two_stage_gate_reason`, `patch_action`, B patch diagnostic fields. |
| `monotonicity` | Not globally monotonic; action potentials must be interpreted by branch and risk state. |
| `valid_range` | Action potentials in `[0, 1]`. |
| `potential_transform` | Softmax-like or normalized action potential over `keep_base/use_path/reject/uncertain`. |
| `cost_transform` | `-log(action_potential + eps)` |
| `clip_policy` | Clip action potential to `[eps, 1]`. |
| `missing_value_policy` | Missing upstream factor potential blocks final arbitration for calibration. |
| `correlated_factors` | `sar_structure_factor`, `uncertainty_factor`, B patch behavior. |
| `double_counting_risk` | Can re-encode B patch behavior and duplicate uncertainty/SAR decisions. |
| `patch_dependency_risk` | `high` |
| `active_in_complete_vehicle` | `true` for diagnostic graph only. |
| `diagnostic_only` | Diagnostic consistency evidence only in this phase. |
| `should_be_learned_later` | `yes` |
| `preliminary_grade` | `BLOCKED` |
| `grade_justification` | B patch reproduction is useful diagnostic consistency evidence but not physical proof. |
| `required_control_condition` | Separate patch dependency before any Phase4 active scoring or calibration. |
| `Phase4_eligibility` | Not eligible as active Phase4 scoring factor. |
| `blocker_if_any` | `B006` |

### 5.9 `visibility_factor`

| Field | Value |
|---|---|
| `factor_name` | `visibility_factor` |
| `branch_scope` | `partial_visibility_veto` |
| `allowed_phase` | `Phase7`; Phase3 audit only as inactive/veto-only interface. |
| `field_origin` | Current visible factor diagnostics; future partial-visibility inference tables. |
| `leakage_class` | `diagnostic_inference_safe` |
| `join_stage` | Row/candidate diagnostic factor; not a direct candidate generator. |
| `inference_safe_fields` | `visible_factor`, visible support features, `P_artifact`, visibility uncertainty fields when standardized. |
| `current_code_fields` | `visible_factor`, `E_visible_veto`, `P_artifact` |
| `monotonicity` | Visible support may reduce uncertainty only within partial-visibility branch; no full-center shift is allowed. |
| `valid_range` | Visible support scores in `[0, 1]`. |
| `potential_transform` | Factor/veto/uncertainty potential only. |
| `cost_transform` | `-log(potential + eps)` when used as factor; veto can route to uncertainty. |
| `clip_policy` | Clip potential to `[eps, 1]`. |
| `missing_value_policy` | Missing visible support defaults to no visible evidence, not full-center inference. |
| `correlated_factors` | `source_factor`, `uncertainty_factor`, `visible_full_center_offset_factor` |
| `double_counting_risk` | Visible evidence can be counted as source trust and uncertainty. |
| `patch_dependency_risk` | `low` |
| `active_in_complete_vehicle` | `false` as full-center source; only veto/uncertainty note allowed. |
| `diagnostic_only` | `true` |
| `should_be_learned_later` | `yes` |
| `preliminary_grade` | `BLOCKED` |
| `grade_justification` | Visible support is physically plausible but not standardized for full-center localization and cannot generate full center. |
| `required_control_condition` | Keep visible support veto/uncertainty-only until Phase7 schema and branch gates pass. |
| `Phase4_eligibility` | Not eligible for complete-vehicle Phase4. |
| `blocker_if_any` | `B008` |

### 5.10 `missing_extent_factor`

| Field | Value |
|---|---|
| `factor_name` | `missing_extent_factor` |
| `branch_scope` | `partial_visibility` |
| `allowed_phase` | `Phase7` |
| `field_origin` | Future partial-visibility inference tables. |
| `leakage_class` | `future_inference_required` |
| `join_stage` | Future partial-visibility branch, not current complete-vehicle candidate selection. |
| `inference_safe_fields` | Future inference-safe missing extent features; visible support extent; edge/component/ridge evidence. |
| `current_code_fields` | Not yet standardized. |
| `monotonicity` | Larger missing extent should increase uncertainty; exact mapping is not standardized. |
| `valid_range` | `BLOCKED` until feature schema is standardized. |
| `potential_transform` | `BLOCKED` until Phase7. |
| `cost_transform` | `BLOCKED` until Phase7. |
| `clip_policy` | `BLOCKED` until Phase7. |
| `missing_value_policy` | Absent by default in complete-vehicle branch. |
| `correlated_factors` | `visibility_factor`, `visible_full_center_offset_factor`, `uncertainty_factor` |
| `double_counting_risk` | May duplicate visibility uncertainty in the future branch. |
| `patch_dependency_risk` | `low` |
| `active_in_complete_vehicle` | `false` |
| `diagnostic_only` | `true` |
| `should_be_learned_later` | `yes` |
| `preliminary_grade` | `BLOCKED` |
| `grade_justification` | Conceptually necessary but not standardized and not allowed in complete-vehicle selection. |
| `required_control_condition` | Keep diagnostic-only until Phase7 schema is standardized and branch isolation is accepted. |
| `Phase4_eligibility` | Not eligible. |
| `blocker_if_any` | `B008`, `B009` |

### 5.11 `visible_full_center_offset_factor`

| Field | Value |
|---|---|
| `factor_name` | `visible_full_center_offset_factor` |
| `branch_scope` | `partial_visibility` |
| `allowed_phase` | `Phase7` |
| `field_origin` | Future partial-visibility inference tables. |
| `leakage_class` | `future_inference_required` |
| `join_stage` | Future partial-visibility branch only. |
| `inference_safe_fields` | Future inference-safe visible/full-center offset features; visible support geometry; component extent evidence. |
| `current_code_fields` | Not yet standardized; visible support currently veto/factor only. |
| `monotonicity` | Larger offset uncertainty should increase uncertainty or block direct full-center action. |
| `valid_range` | `BLOCKED` until offset schema is standardized. |
| `potential_transform` | `BLOCKED` until Phase7. |
| `cost_transform` | `BLOCKED` until Phase7. |
| `clip_policy` | `BLOCKED` until Phase7. |
| `missing_value_policy` | Absent by default in complete-vehicle branch. |
| `correlated_factors` | `visibility_factor`, `missing_extent_factor`, `uncertainty_factor` |
| `double_counting_risk` | Offset and missing extent may encode the same partial-visibility evidence. |
| `patch_dependency_risk` | `low` |
| `active_in_complete_vehicle` | `false` |
| `diagnostic_only` | `true` |
| `should_be_learned_later` | `yes` |
| `preliminary_grade` | `BLOCKED` |
| `grade_justification` | Required to prevent visible-center misuse, but no standardized inference-safe implementation exists. |
| `required_control_condition` | Keep diagnostic-only until Phase7 schema is standardized; never use visible support to generate full center in current phase. |
| `Phase4_eligibility` | Not eligible. |
| `blocker_if_any` | `B008`, `B009` |
