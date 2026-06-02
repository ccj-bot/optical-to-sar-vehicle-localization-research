# GM17 Factor Prior Registry

Date: 2026-06-02

Purpose: Phase3 audit-execution-ready registry for factor priors before any track-block OOF weight calibration or selector refactor.

Project: 光学迁移到SAR中的车辆定位与候选选择

Status: documentation-only audit registry. GM17 remains a staged validation line. The entries below are prior-audit records, not learned weights and not final physical claims.

## Boundary

- PASS: Do not change candidate bank.
- PASS: Do not train ranker, CRF, or OOF weights.
- PASS: Do not replace GM17 mainline.
- PASS: Do not run new performance experiments from this registry.
- PASS: Do not use GT, oracle, IoU, center error, condition labels, truncation labels, occlusion labels, or final-box fields in inference.
- WARN: Visible-related fields may be consumed only as factor, veto, or uncertainty. They are not full-center generators.
- BLOCKED: OOF calibration remains blocked until Phase2 model-spec review and Phase3 factor prior audit both pass.

## Terminology Contract

- `final_action` means model-level output inside inference, such as `keep_base`, `use_path`, `reject`, or `uncertain`.
- `release_decision` means AuditReleaseAgent-level project decision about whether an artifact can proceed, remain diagnostic, enter calibration, or be blocked.
- Do not mix these terms. `final_action` is a factor graph variable. `release_decision` is an audit/release gate.

## Required Registry Schema

Every factor must record the base fields:

- `factor_name`
- `factor_type`
- `physical_meaning`
- `expected_direction`
- `inference_safe_fields`
- `current_code_fields`
- `supporting_evidence`
- `failure_cases`
- `risk_if_overweighted`
- `risk_if_underweighted`
- `evidence_grade`
- `should_be_learned_later`

Every factor must also record the Phase3 audit-execution fields:

- `field_origin`
- `leakage_class`
- `join_stage`
- `monotonicity`
- `valid_range`
- `potential_transform`
- `cost_transform`
- `clip_policy`
- `missing_value_policy`
- `correlated_factors`
- `double_counting_risk`
- `branch_scope`
- `allowed_phase`
- `active_in_complete_vehicle`
- `diagnostic_only`
- `patch_dependency_risk`
- `grade_justification`

Evidence grade:

- `A`: validated across selected-prediction behavior and boundary-audited diagnostics.
- `B`: useful in GM17 diagnostics but not yet calibrated or broadly validated.
- `C`: plausible physical prior but weak, future-facing, or mixed current evidence.
- `D`: diagnostic-only or high-risk until redesigned.

Leakage class:

- `inference_safe`: allowed in inference if field origin and join stage are audited.
- `diagnostic_inference_safe`: allowed only for diagnostic prototypes, not mainline selectors.
- `eval_only_blocked`: not allowed in inference.
- `future_inference_required`: field concept is valid but current inference-safe source is not standardized.

## Patch-Dependency Risk Note

B patch reproduction is diagnostic consistency evidence only. It is not proof of a final physical model.

The following factors must explicitly record patch dependency:

- `final_arbitration_factor`: high patch-dependency risk because it can copy B patch action behavior.
- `sar_structure_factor`: medium patch-dependency risk because accepted B patch is a SAR uncertainty penalty.
- `uncertainty_factor`: medium patch-dependency risk because ambiguous/SAR uncertainty signals drove the accepted patch.

Any future OOF calibration must distinguish physical support from engineering patch reproduction.

## Branch Separation Rule

- Complete-vehicle factors may be active in Phase2/Phase3 only if their fields are inference-safe.
- `visibility_factor` may only act as factor, veto, or uncertainty. It must not generate full center.
- `missing_extent_factor` is `diagnostic_only=true`, `active_in_complete_vehicle=false`, `allowed_phase=Phase7`.
- `visible_full_center_offset_factor` is `diagnostic_only=true`, `active_in_complete_vehicle=false`, `allowed_phase=Phase7`.
- Any visible-related source family is not allowed to act as a full-center generator.

## Factor Status Index

| factor_name | branch_scope | allowed_phase | active_in_complete_vehicle | diagnostic_only | evidence_grade | phase3_status |
|---|---|---|---:|---:|---|---|
| geometry_factor | complete_vehicle | Phase3 | true | false | B | PASS |
| direction_factor | complete_vehicle | Phase3 | true | false | B | PASS |
| source_factor | complete_vehicle | Phase3 | true | false | B | PASS_WITH_VISIBLE_WARN |
| sar_structure_factor | complete_vehicle | Phase3 | true | false | A | PASS_WITH_PATCH_WARN |
| optical_temporal_factor | complete_vehicle | Phase3 | true | false | B | PASS |
| transition_factor | complete_vehicle | Phase3 | true | false | B | PASS |
| final_arbitration_factor | complete_vehicle_decision | Phase3 | true | false | B | WARN_PATCH_DEPENDENCY |
| visibility_factor | partial_visibility_veto | Phase7 | false | true | C | BLOCKED_FROM_COMPLETE_VEHICLE |
| missing_extent_factor | partial_visibility | Phase7 | false | true | C | BLOCKED_NOT_STANDARDIZED |
| visible_full_center_offset_factor | partial_visibility | Phase7 | false | true | C | BLOCKED_NOT_STANDARDIZED |
| uncertainty_factor | cross_cutting | Phase3 | true | false | A | PASS_WITH_DOUBLE_COUNT_WARN |

## Factor Audit Cards

### geometry_factor

- `factor_name`: `geometry_factor`
- `factor_type`: `complete_vehicle_node`
- `physical_meaning`: fan-polar compatibility of candidate range, cross-ray offset, azimuth, heading, and size.
- `expected_direction`: higher geometry support lowers candidate cost.
- `inference_safe_fields`: `r`, `cross`, `az`, `heading`, `w`, `h`, `delta_r_from_pred`, `delta_cross_from_pred`, `delta_az_from_pred`, `refined_geometry_score`, `geometry_escape_refined_score`
- `current_code_fields`: `E_geometry`, `refined_geometry_score`, `geometry_escape_refined_score`, `delta_*`
- `supporting_evidence`: strong single-factor signal in GM17 fixed-bank diagnostics; supports hard19 candidate availability.
- `failure_cases`: `gm17supp_000167_000347_det4` remains node-energy wrong; geometry alone does not surface the selected candidate.
- `risk_if_overweighted`: chooses geometrically plausible but SAR-unsupported escape candidates.
- `risk_if_underweighted`: keeps wrong base when real escape geometry exists.
- `evidence_grade`: `B`
- `should_be_learned_later`: `yes`
- `field_origin`: fixed candidate bank plus state-energy diagnostic tables.
- `leakage_class`: `inference_safe`
- `join_stage`: candidate-level node fields joined by `candidate_id`.
- `monotonicity`: higher support score should monotonically reduce cost; larger raw deltas should not be interpreted directly without transform.
- `valid_range`: geometry support scores expected in `[0, 1]`; fan-polar coordinates are finite numeric values.
- `potential_transform`: normalize geometry support into `[0, 1]` potential.
- `cost_transform`: `-log(potential + eps)`.
- `clip_policy`: clip support potential to `[eps, 1]`.
- `missing_value_policy`: BLOCKED if required coordinate fields are missing; default support scores to neutral only in diagnostic tables.
- `correlated_factors`: `sar_structure_factor`, `source_factor`, `transition_factor`
- `double_counting_risk`: WARN; geometry escape features may already include SAR-structure-like shell evidence.
- `branch_scope`: `complete_vehicle`
- `allowed_phase`: `Phase3`
- `active_in_complete_vehicle`: `true`
- `diagnostic_only`: `false`
- `patch_dependency_risk`: `low`
- `grade_justification`: useful and inference-safe, but geometry alone is insufficient and has known node-energy failure.

### direction_factor

- `factor_name`: `direction_factor`
- `factor_type`: `complete_vehicle_node`
- `physical_meaning`: compatibility between candidate direction and signed escape posterior.
- `expected_direction`: direction agreement lowers cost; direction conflict raises uncertainty.
- `inference_safe_fields`: `candidate_direction_bin`, `signed_escape_decision`, `P_near`, `P_pos_escape`, `P_neg_escape`, `P_ambiguous`, `signed_direction_match`, `posterior_confidence`, `posterior_margin`
- `current_code_fields`: `E_direction`, `signed_direction_match`, `P_*`, `signed_escape_decision`
- `supporting_evidence`: seven-case diagnostics isolate wrong-direction failures; factor graph explanations are direction-dominated.
- `failure_cases`: `gm_rm017_00029`, `gm_rm017_00027`
- `risk_if_overweighted`: over-vetoes useful escapes when signed posterior is noisy.
- `risk_if_underweighted`: allows wrong-direction over-switch.
- `evidence_grade`: `B`
- `should_be_learned_later`: `yes`
- `field_origin`: signed escape posterior and state-energy diagnostic tables.
- `leakage_class`: `inference_safe`
- `join_stage`: row-level posterior fields joined to candidate-level direction fields.
- `monotonicity`: higher matching posterior and margin should lower cost.
- `valid_range`: probabilities and match scores in `[0, 1]`; direction states from controlled labels.
- `potential_transform`: map candidate-direction posterior and match score into `[0, 1]` potential.
- `cost_transform`: `-log(potential + eps)`.
- `clip_policy`: clip posterior-derived potential to `[eps, 1]`.
- `missing_value_policy`: if posterior is missing, mark factor diagnostic BLOCKED for the row.
- `correlated_factors`: `source_factor`, `uncertainty_factor`, `final_arbitration_factor`
- `double_counting_risk`: WARN; source trust often embeds direction assumptions.
- `branch_scope`: `complete_vehicle`
- `allowed_phase`: `Phase3`
- `active_in_complete_vehicle`: `true`
- `diagnostic_only`: `false`
- `patch_dependency_risk`: `low`
- `grade_justification`: direction failures are clear, but posterior calibration is not yet learned.

### source_factor

- `factor_name`: `source_factor`
- `factor_type`: `complete_vehicle_node`
- `physical_meaning`: trustworthiness of candidate source family under current direction and risk state.
- `expected_direction`: trusted source family lowers cost only when direction and SAR structure agree.
- `inference_safe_fields`: `candidate_source`, `source_prior`, `directional_shell_score`, `track_escape_evidence`, `signed_direction_match`
- `current_code_fields`: `candidate_source`, `source_prior`, source-family mapping in diagnostics.
- `supporting_evidence`: hard repairs concentrate in `bidirectional_escape_candidate` and `wedge_joint_candidate`; base remains protective for normal rows.
- `failure_cases`: source-family risk remains high for wedge, bidirectional, and track-signed if unconstrained.
- `risk_if_overweighted`: prefers source artifacts or over-switches normal rows.
- `risk_if_underweighted`: blocks useful hard-case escape sources.
- `evidence_grade`: `B`
- `should_be_learned_later`: `yes`
- `field_origin`: candidate bank source labels plus diagnostic source priors.
- `leakage_class`: `inference_safe`; visible family is `diagnostic_inference_safe` only.
- `join_stage`: candidate-level source label and row-level support fields.
- `monotonicity`: source prior alone is not monotonic; monotonic only after direction and SAR support are included.
- `valid_range`: source priors and support scores in `[0, 1]`; source labels from controlled candidate source set.
- `potential_transform`: source prior multiplied or blended with direction/SAR support.
- `cost_transform`: `-log(potential + eps)`.
- `clip_policy`: clip blended potential to `[eps, 1]`.
- `missing_value_policy`: unknown source maps to diagnostic WARN and conservative low trust.
- `correlated_factors`: `direction_factor`, `geometry_factor`, `sar_structure_factor`, `visibility_factor`
- `double_counting_risk`: WARN; source family may encode geometry and SAR structure assumptions.
- `branch_scope`: `complete_vehicle`, except visible source family is `partial_visibility_veto`.
- `allowed_phase`: `Phase3` for non-visible families; visible source behavior active only as veto/uncertainty until `Phase7`.
- `active_in_complete_vehicle`: `true` for base/wedge/bidirectional/track_signed; visible is not full-center active.
- `diagnostic_only`: `false` for complete-vehicle source families; visible-related behavior is diagnostic/veto-only.
- `patch_dependency_risk`: `low`
- `grade_justification`: useful source partition, but source labels can double-count support and must not make visible full-center predictions.

### sar_structure_factor

- `factor_name`: `sar_structure_factor`
- `factor_type`: `complete_vehicle_node`
- `physical_meaning`: SAR wedge/ray/shell support and ambiguity for vehicle structure.
- `expected_direction`: strong SAR support lowers escape cost; ambiguous SAR raises uncertainty or rejection pressure.
- `inference_safe_fields`: `directional_shell_score`, `geometry_escape_refined_score`, `track_escape_evidence`, `escape_conflict_score`, `P_ambiguous`, `P_artifact`, `E_sar_structure`, `E_uncertainty`
- `current_code_fields`: `E_sar_structure`, `E_uncertainty`, `directional_shell_score`, `escape_conflict_score`
- `supporting_evidence`: accepted B patch uses SAR uncertainty to remove normal over-switch without hurting hard19.
- `failure_cases`: `gm_rm017_00025`, `gm_rm017_00027`
- `risk_if_overweighted`: over-penalizes real hard-case escape if ambiguity is common.
- `risk_if_underweighted`: reintroduces normal over-switch.
- `evidence_grade`: `A`
- `should_be_learned_later`: `yes`
- `field_origin`: state-energy diagnostic and fixed-bank factor tables.
- `leakage_class`: `diagnostic_inference_safe` until fields are traced to non-patch origins.
- `join_stage`: candidate-level SAR structure joined with row-level posterior uncertainty.
- `monotonicity`: higher support lowers cost; higher ambiguity/conflict raises uncertainty cost.
- `valid_range`: support, ambiguity, and energy-derived normalized scores in `[0, 1]`.
- `potential_transform`: support potential from shell/geometry/escape evidence; uncertainty potential from ambiguity/conflict.
- `cost_transform`: `-log(potential + eps)` for support and/or uncertainty route cost.
- `clip_policy`: clip all normalized scores to `[eps, 1]`.
- `missing_value_policy`: missing SAR support defaults to conservative uncertainty in diagnostics.
- `correlated_factors`: `geometry_factor`, `uncertainty_factor`, `final_arbitration_factor`
- `double_counting_risk`: WARN; overlaps with geometry shell evidence and uncertainty factor.
- `branch_scope`: `complete_vehicle`
- `allowed_phase`: `Phase3`
- `active_in_complete_vehicle`: `true`
- `diagnostic_only`: `false`, but patch-linked fields must remain audited.
- `patch_dependency_risk`: `medium`; accepted B patch is explicitly SAR uncertainty based.
- `grade_justification`: strongest current protection evidence, but partially tied to B patch behavior.

### optical_temporal_factor

- `factor_name`: `optical_temporal_factor`
- `factor_type`: `complete_vehicle_soft_prior`
- `physical_meaning`: soft consistency with optical track mapped into SAR fan-polar trend.
- `expected_direction`: temporal consistency lowers cost but must not hard-lock center.
- `inference_safe_fields`: `optical_temporal_consistency_score`, `temporal_factor_score`, `gm17_track_id`, `sar_frame_num`, `pred_r`, `pred_az`, `pred_cross`
- `current_code_fields`: `E_optical_temporal`, `optical_temporal_consistency_score`, `temporal_factor_score`
- `supporting_evidence`: track-level selector benefits from path context; literature traceability supports optical-to-SAR prior as soft evidence.
- `failure_cases`: prior temporal-only trials could hurt normal rows if overused.
- `risk_if_overweighted`: smooths wrong path or preserves wrong base.
- `risk_if_underweighted`: loses track-level stability and context.
- `evidence_grade`: `B`
- `should_be_learned_later`: `yes`
- `field_origin`: optical temporal inference tables and boundary-safe temporal features.
- `leakage_class`: `inference_safe`
- `join_stage`: row-level and track-level prior joined to candidate nodes.
- `monotonicity`: higher temporal consistency lowers cost softly.
- `valid_range`: consistency scores in `[0, 1]`; track/frame IDs finite and non-eval.
- `potential_transform`: soft prior potential; never direct center overwrite.
- `cost_transform`: `-log(potential + eps)`.
- `clip_policy`: clip potential to `[eps, 1]`.
- `missing_value_policy`: missing temporal prior defaults to neutral soft prior, not failure.
- `correlated_factors`: `transition_factor`, `geometry_factor`
- `double_counting_risk`: WARN; transition and optical temporal can both reward smoothness.
- `branch_scope`: `complete_vehicle`
- `allowed_phase`: `Phase3`
- `active_in_complete_vehicle`: `true`
- `diagnostic_only`: `false`
- `patch_dependency_risk`: `low`
- `grade_justification`: useful as soft prior but not validated as a hard localization signal.

### transition_factor

- `factor_name`: `transition_factor`
- `factor_type`: `track_edge`
- `physical_meaning`: adjacent-frame continuity over fan-polar state, OBB geometry, and signed state.
- `expected_direction`: smooth physically plausible transitions lower path cost.
- `inference_safe_fields`: `r`, `cross`, `az`, `heading`, `w`, `h`, `candidate_direction_bin`, `signed_escape_decision`, `optical_temporal_consistency_score`, `gm17_track_id`, `sar_frame_num`
- `current_code_fields`: `E_switch`, `incoming_edge_score`, `path_score`, `path_score_delta`
- `supporting_evidence`: track Viterbi/DP improved selected prediction and exposes path proposal behavior.
- `failure_cases`: under-switch cases remain protected by gate; transition alone cannot decide release.
- `risk_if_overweighted`: propagates wrong escape across a segment.
- `risk_if_underweighted`: loses sequence-level stabilization.
- `evidence_grade`: `B`
- `should_be_learned_later`: `yes`
- `field_origin`: fixed candidate state fields and track path diagnostics.
- `leakage_class`: `inference_safe`
- `join_stage`: adjacent candidate-pair edge construction within each track.
- `monotonicity`: larger state discontinuity raises transition cost.
- `valid_range`: finite coordinates, heading in normalized OBB convention, frame order per track.
- `potential_transform`: convert continuity score to edge potential.
- `cost_transform`: `-log(potential + eps)` or equivalent positive transition cost.
- `clip_policy`: clip continuity potential to `[eps, 1]`; cap extreme edge costs in diagnostics.
- `missing_value_policy`: BLOCKED if required state fields are missing for edge construction.
- `correlated_factors`: `optical_temporal_factor`, `direction_factor`
- `double_counting_risk`: WARN; may double-count optical temporal smoothness and signed direction continuity.
- `branch_scope`: `complete_vehicle`
- `allowed_phase`: `Phase3`
- `active_in_complete_vehicle`: `true`
- `diagnostic_only`: `false`
- `patch_dependency_risk`: `low`
- `grade_justification`: track evidence is useful, but transition should not act as release gate by itself.

### final_arbitration_factor

- `factor_name`: `final_arbitration_factor`
- `factor_type`: `decision_node`
- `physical_meaning`: soft model-level `final_action` selection after risk, direction, source, candidate, path, and uncertainty evidence.
- `expected_direction`: high normal protection or SAR uncertainty favors `keep_base`/`reject`; clear path evidence favors `use_path`.
- `inference_safe_fields`: risk potential, direction potential, source potential, candidate potential, path proposal evidence, SAR uncertainty, normal keep signal.
- `current_code_fields`: `Z_t`, `phi_final`, `two_stage_gate_reason`, `patch_action`, B patch diagnostic fields.
- `supporting_evidence`: factor graph diagnostic reproduced B patch and reduced hard threshold count.
- `failure_cases`: if too tied to B patch, remains diagnostic rather than independent model.
- `risk_if_overweighted`: hides model weaknesses by copying patch behavior.
- `risk_if_underweighted`: reintroduces normal regressions or under-switch.
- `evidence_grade`: `B`
- `should_be_learned_later`: `yes`
- `field_origin`: diagnostic factor graph outputs and current B patch comparison artifacts.
- `leakage_class`: `diagnostic_inference_safe`; not ready for mainline calibration until patch dependency is separated.
- `join_stage`: row-level final action after candidate/path scoring.
- `monotonicity`: not globally monotonic; action potentials must be interpreted by branch and risk state.
- `valid_range`: action potentials in `[0, 1]`.
- `potential_transform`: softmax-like or normalized action potential over `keep_base/use_path/reject/uncertain`.
- `cost_transform`: `-log(action_potential + eps)`.
- `clip_policy`: clip action potential to `[eps, 1]`.
- `missing_value_policy`: missing required upstream factor potential blocks final arbitration for calibration.
- `correlated_factors`: `sar_structure_factor`, `uncertainty_factor`, B patch behavior.
- `double_counting_risk`: FAIL for calibration until patch dependency is explicitly controlled; it can re-encode B patch.
- `branch_scope`: `complete_vehicle_decision`
- `allowed_phase`: `Phase3` diagnostic audit only; calibration blocked until patch dependency audit passes.
- `active_in_complete_vehicle`: `true`
- `diagnostic_only`: `false` for diagnostic graph, but not release-ready.
- `patch_dependency_risk`: `high`
- `grade_justification`: reproduces B patch, which is useful consistency evidence but not physical proof.

### visibility_factor

- `factor_name`: `visibility_factor`
- `factor_type`: `partial_visibility_node`
- `physical_meaning`: visible SAR support under partial visibility.
- `expected_direction`: good visible evidence may support, veto, or raise/lower uncertainty, but must not generate full center.
- `inference_safe_fields`: `visible_factor`, visible support features, `P_artifact`, visibility uncertainty fields when standardized.
- `current_code_fields`: `visible_factor`, `E_visible_veto`, `P_artifact`
- `supporting_evidence`: literature and GM17 traceability show visible support is sparse and aspect-dependent.
- `failure_cases`: visible support weak for hard19; visible/full-center mismatch risk.
- `risk_if_overweighted`: treats visible center as full center and creates biased boxes.
- `risk_if_underweighted`: ignores useful veto and uncertainty signal.
- `evidence_grade`: `C`
- `should_be_learned_later`: `yes`
- `field_origin`: current visible factor diagnostics; future partial-visibility inference tables.
- `leakage_class`: `diagnostic_inference_safe`
- `join_stage`: row/candidate diagnostic factor; not a direct candidate generator.
- `monotonicity`: higher visible support may reduce uncertainty only within partial-visibility branch; no monotonic full-center shift is allowed.
- `valid_range`: visible support scores in `[0, 1]`.
- `potential_transform`: factor/veto/uncertainty potential only.
- `cost_transform`: `-log(potential + eps)` when used as factor; veto can route to uncertainty.
- `clip_policy`: clip potential to `[eps, 1]`.
- `missing_value_policy`: missing visible support defaults to no visible evidence, not full-center inference.
- `correlated_factors`: `source_factor`, `uncertainty_factor`, `visible_full_center_offset_factor`
- `double_counting_risk`: WARN; visible fields can be counted both as source trust and uncertainty.
- `branch_scope`: `partial_visibility_veto`
- `allowed_phase`: `Phase7`; can be audited in Phase3 only as inactive/veto-only interface.
- `active_in_complete_vehicle`: `false` as full-center source; only veto/uncertainty note allowed.
- `diagnostic_only`: `true`
- `patch_dependency_risk`: `low`
- `grade_justification`: physically plausible but not standardized for full-center localization.

### missing_extent_factor

- `factor_name`: `missing_extent_factor`
- `factor_type`: `partial_visibility_node`
- `physical_meaning`: missing extent caused by truncation or occlusion.
- `expected_direction`: greater missing extent increases uncertainty and shifts reasoning to partial-visibility branch.
- `inference_safe_fields`: future inference-safe missing extent features; visible support extent; edge/component/ridge evidence.
- `current_code_fields`: not yet standardized.
- `supporting_evidence`: required by roadmap but not active in complete-vehicle mainline.
- `failure_cases`: truncation/occlusion cases outside current complete-vehicle scope.
- `risk_if_overweighted`: overfits partial cases and destabilizes complete-vehicle selection.
- `risk_if_underweighted`: cannot model partial visibility failures.
- `evidence_grade`: `C`
- `should_be_learned_later`: `yes`
- `field_origin`: future partial-visibility inference tables.
- `leakage_class`: `future_inference_required`
- `join_stage`: future partial-visibility branch, not current complete-vehicle candidate selection.
- `monotonicity`: larger missing extent should increase uncertainty; exact mapping not standardized.
- `valid_range`: BLOCKED until feature schema is standardized.
- `potential_transform`: BLOCKED until Phase7.
- `cost_transform`: BLOCKED until Phase7.
- `clip_policy`: BLOCKED until Phase7.
- `missing_value_policy`: absent by default in complete-vehicle branch.
- `correlated_factors`: `visibility_factor`, `visible_full_center_offset_factor`, `uncertainty_factor`
- `double_counting_risk`: WARN for future branch; missing extent may duplicate visibility uncertainty.
- `branch_scope`: `partial_visibility`
- `allowed_phase`: `Phase7`
- `active_in_complete_vehicle`: `false`
- `diagnostic_only`: `true`
- `patch_dependency_risk`: `low`
- `grade_justification`: conceptually necessary for partial visibility but not standardized.

### visible_full_center_offset_factor

- `factor_name`: `visible_full_center_offset_factor`
- `factor_type`: `partial_visibility_node`
- `physical_meaning`: offset between visible support center and latent full vehicle center.
- `expected_direction`: larger offset uncertainty prevents direct full-center generation from visible support.
- `inference_safe_fields`: future inference-safe visible/full-center offset features; visible support geometry; component extent evidence.
- `current_code_fields`: not yet standardized; visible support currently veto/factor only.
- `supporting_evidence`: existing rule that visible center is not full vehicle center.
- `failure_cases`: partial visible targets and missing extent cases.
- `risk_if_overweighted`: incorrectly shifts final center from visible fragments.
- `risk_if_underweighted`: leaves partial visibility branch under-specified.
- `evidence_grade`: `C`
- `should_be_learned_later`: `yes`
- `field_origin`: future partial-visibility inference tables.
- `leakage_class`: `future_inference_required`
- `join_stage`: future partial-visibility branch only.
- `monotonicity`: larger offset uncertainty should increase uncertainty or block direct full-center action.
- `valid_range`: BLOCKED until offset schema is standardized.
- `potential_transform`: BLOCKED until Phase7.
- `cost_transform`: BLOCKED until Phase7.
- `clip_policy`: BLOCKED until Phase7.
- `missing_value_policy`: absent by default in complete-vehicle branch.
- `correlated_factors`: `visibility_factor`, `missing_extent_factor`, `uncertainty_factor`
- `double_counting_risk`: WARN for future branch; offset and missing extent may encode the same partial-visibility evidence.
- `branch_scope`: `partial_visibility`
- `allowed_phase`: `Phase7`
- `active_in_complete_vehicle`: `false`
- `diagnostic_only`: `true`
- `patch_dependency_risk`: `low`
- `grade_justification`: required to prevent visible-center misuse, but no standardized inference-safe implementation yet.

### uncertainty_factor

- `factor_name`: `uncertainty_factor`
- `factor_type`: `cross_cutting`
- `physical_meaning`: aggregates low confidence, ambiguity, artifact risk, and factor conflict.
- `expected_direction`: higher uncertainty raises cost or routes to `reject`/`uncertain`.
- `inference_safe_fields`: `posterior_confidence`, `posterior_margin`, `escape_conflict_score`, `P_ambiguous`, `P_artifact`, `E_uncertainty`
- `current_code_fields`: `E_uncertainty`, `sar_uncertainty_soft`, `P_ambiguous`, `P_artifact`
- `supporting_evidence`: accepted B patch and diagnostics show uncertainty protects normal rows.
- `failure_cases`: `gm_rm017_00025`, `gm_rm017_00027`; under-switch cases if too strong.
- `risk_if_overweighted`: blocks valid hard-case escape.
- `risk_if_underweighted`: allows ambiguous over-switch.
- `evidence_grade`: `A`
- `should_be_learned_later`: `yes`
- `field_origin`: signed posterior, state-energy diagnostics, SAR ambiguity diagnostics.
- `leakage_class`: `diagnostic_inference_safe` until B patch coupling is separated.
- `join_stage`: row-level and candidate-level uncertainty fields joined to node and final action.
- `monotonicity`: higher ambiguity/conflict/lower confidence should increase uncertainty cost.
- `valid_range`: posterior and uncertainty scores in `[0, 1]`.
- `potential_transform`: uncertainty potential can either penalize candidate or route final action to reject/uncertain.
- `cost_transform`: `-log(potential + eps)` for confidence potential, or positive uncertainty penalty in diagnostics.
- `clip_policy`: clip normalized uncertainty and confidence potentials to `[eps, 1]`.
- `missing_value_policy`: missing uncertainty fields default to conservative WARN, not optimistic pass.
- `correlated_factors`: `sar_structure_factor`, `direction_factor`, `final_arbitration_factor`, `visibility_factor`
- `double_counting_risk`: WARN; uncertainty can duplicate SAR ambiguity, direction conflict, and final arbitration behavior.
- `branch_scope`: `complete_vehicle` and future `partial_visibility`
- `allowed_phase`: `Phase3` for complete-vehicle uncertainty; Phase7 for partial-visibility uncertainty extensions.
- `active_in_complete_vehicle`: `true`
- `diagnostic_only`: `false`, but patch-linked uncertainty fields must remain audited.
- `patch_dependency_risk`: `medium`
- `grade_justification`: strong protection evidence, but tied to accepted SAR uncertainty patch behavior.

## Double-Counting Audit Summary

- WARN: `sar_structure_factor` and `uncertainty_factor` overlap through `E_sar_structure`, `E_uncertainty`, `P_ambiguous`, and conflict fields.
- WARN: `geometry_factor` and `sar_structure_factor` overlap through directional shell and geometry escape features.
- WARN: `direction_factor` and `source_factor` overlap because source-family trust often encodes expected direction.
- WARN: `transition_factor` and `optical_temporal_factor` overlap through smoothness and temporal priors.
- BLOCKED_FOR_CALIBRATION: `final_arbitration_factor` and B patch behavior overlap directly through diagnostic action reproduction.

See `docs/gm17_factor_dependency_audit.md` for the separate dependency matrix.

## Phase3 Stop/Go Decision

Decision: `PASS_FOR_PHASE3_AUDIT_EXECUTION_PREP`, `BLOCKED_FOR_OOF_CALIBRATION`.

The registry is now ready to support Phase3 factor prior audit execution, with explicit WARN/BLOCKED items. It is not a calibration-ready artifact. AuditReleaseAgent must re-check boundary reports, field dictionary usage, and dependency risks before any Phase4 fixed-prior revalidation or Phase5 OOF calibration.
