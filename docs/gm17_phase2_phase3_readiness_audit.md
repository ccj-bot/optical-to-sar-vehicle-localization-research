# GM17 Phase2 / Phase3 Readiness Audit

Date: 2026-06-02

Project: 光学迁移到SAR中的车辆定位与候选选择

Scope: readiness audit only. This document reviews whether the current long-term project structure, GM17 model specification, and factor prior registry are ready to move from Phase2 model-spec review into Phase3 factor prior audit execution.

Hard boundary: no algorithm change, no candidate bank change, no ranker or CRF training, no OOF calibration, no GM17 mainline replacement, and no new performance experiment.

## 1. Executive Decision

Decision: `CONDITIONAL_GO_WITH_BLOCKERS`

Short justification: the long-term structure is directionally correct and the GM17 factor graph is specified well enough to continue Phase3 audit preparation, but it is not clean enough to start calibration-facing Phase3 execution. The registry currently records the base factor-prior fields, but it does not yet include the extended leakage, transform, missing-value, correlation, branch-scope, and patch-dependency audit fields required before OOF calibration. Phase2 should get a targeted cleanup pass, then Phase3 factor prior audit can execute. OOF calibration remains blocked.

## 2. Boundary Compliance Audit

| Item | Status | Audit Finding | Required Action |
|---|---|---|---|
| Candidate bank immutability | PASS | The reviewed documents keep the fixed v2.2 candidate bank as the proposal set and do not request candidate generation changes. | Keep candidate bank hash checks under AuditReleaseAgent. |
| No ranker training | PASS | Roadmap, subagent contract, and registry explicitly block ranker training in the current phase. | Keep blocked until after factor prior audit and a separate calibration decision. |
| No OOF calibration | PASS | Phase5 is defined as later work, and current docs say OOF calibration is not authorized in this phase. | Do not start calibration from this audit. |
| No GM17 mainline replacement | PASS | GM17 is described as staged validation; current factor graph remains diagnostic/model-spec work. | Preserve mainline until a release decision exists. |
| No new performance experiment | PASS | The roadmap and current task are documentation-only; no experiment is required or authorized. | Continue with document cleanup only. |
| No visible-to-full-center generation | WARN | The docs state visible support cannot generate full center, but `visible` still appears as a source family in the complete-vehicle factor graph interface. This is acceptable only if `visible` is constrained to factor/veto/uncertainty behavior. | Add an explicit interface note that visible source family is inactive or veto-only in complete-vehicle candidate selection until Phase7. |
| No eval leakage into inference | PASS | Specs repeatedly exclude GT, oracle, IoU, center error, condition labels, truncation labels, occlusion labels, and final-box fields from inference. | AuditReleaseAgent must enforce this on every future output. |

## 3. Long-Term Subagent Responsibility Audit

### StateGraphAgent

Status: PASS with interface warnings.

StateGraphAgent owns the complete-vehicle factor graph, hidden variables, complete-vehicle factors, MAP/Viterbi inference, and later track-block OOF planning. The responsibility boundary is mostly clear: it does not own truncation/occlusion details and does not decide release readiness.

Interface risk:

- It currently includes `visible` in `source family`, which can be useful as a placeholder but risks leaking partial visibility logic into the complete-vehicle branch.
- It plans OOF calibration but must not start calibration until AuditReleaseAgent accepts factor prior audit readiness.

### PartialVisibilityAgent

Status: PASS with delayed activation.

PartialVisibilityAgent correctly owns truncation, occlusion, visible/full-center offset, and missing extent. It explicitly states visible center is not full vehicle center and visible support can only be factor, veto, or uncertainty.

Interface risk:

- Partial visibility states are named in the model spec for compatibility, but they must remain diagnostic-only and inactive in complete-vehicle selection until Phase7.
- `visibility_factor`, `missing_extent_factor`, and `visible_full_center_offset_factor` need standardized inference-safe fields before they can participate in any selector.

### AuditReleaseAgent

Status: PASS.

AuditReleaseAgent owns boundary, candidate-pool consistency, visualization audit, grouped metrics, regression testing, manifests, boundary reports, audit reports, and release decisions. It does not score candidates or tune parameters.

### Responsibility Overlaps And Missing Ownership

| Topic | Finding | Risk | Fix |
|---|---|---|---|
| Factor prior ownership | StateGraphAgent defines factors; AuditReleaseAgent audits readiness. | The registry could drift into model design without release gating. | Keep StateGraphAgent as factor owner and AuditReleaseAgent as readiness gate. |
| Partial visibility interface | PartialVisibilityAgent owns partial factors; StateGraphAgent currently lists visibility in the long-term expression. | Partial factors could leak into complete-vehicle selection too early. | Mark partial factors as `diagnostic_only=true`, `active_in_complete_vehicle=false`, `allowed_phase=Phase7`. |
| Calibration proposal | StateGraphAgent plans OOF calibration; AuditReleaseAgent gates it. | Calibration could start before leakage and prior audits are complete. | Keep OOF blocked until all gate criteria pass. |
| Final decision naming | `final_action` and `release_decision` can be confused. | Model action could be mistaken for project release approval. | Use `final_action` only for model output `keep_base/use_path/reject/uncertain`; use `release_decision` only for AuditReleaseAgent experiment acceptance. |

Explicit distinction:

- `final_action`: model-level latent/output action inside inference, such as `keep_base`, `use_path`, `reject`, or `uncertain`.
- `release_decision`: AuditReleaseAgent decision about whether an artifact can proceed, remain diagnostic, enter calibration, or be blocked from the mainline.

## 4. Complete-Vehicle Phase2 Model Spec Audit

| Requirement | Status | Finding | Required Fix |
|---|---|---|---|
| Complete-vehicle variables: `r`, `cross`, `az`, `heading`, `size`, `direction_state`, `source_family`, `selected_candidate` | PASS | All are present in the model spec and roadmap. | None. |
| Diagnostic latent variables: `risk_state`, `direction_state`, `source_family`, `selected_candidate`, `final_action` | PASS | `R_t`, `D_t`, `F_t`, `C_t`, `Z_t` are defined with allowed states. | Rename references consistently from human-readable names to symbolic names where needed. |
| Complete-vehicle factors: geometry, direction, source, SAR structure, optical-temporal, uncertainty, transition, final arbitration | PASS | All factors are defined. | Keep visibility separate from complete-vehicle active factors. |
| MAP/Viterbi over fixed candidate paths | PASS | The spec defines fixed candidate paths, costs, and Viterbi dynamic programming. | Add pseudocode in Phase2 cleanup if the spec becomes implementation-facing. |
| Inference-safe field mapping | WARN | Major fields are listed per factor, but field origin, join stage, missing-value policy, valid range, transform, and leakage class are not yet explicit. | Add extended audit columns to the registry before Phase3 execution. |
| Candidate/source-family interface | WARN | `visible` source family exists in the complete-vehicle source family list. | Specify `visible` as veto/uncertainty only until Phase7. |
| Final arbitration interface | WARN | `final_arbitration_factor` is allowed, but it depends on B patch diagnostic fields in the current registry. | Mark patch-dependency risk explicitly and prevent treating B patch reproduction as physical proof. |

Missing or ambiguous definitions:

- `field_origin`: which upstream table produces each field.
- `join_stage`: whether the field is candidate-level, row-level, track-level, or eval-only.
- `valid_range`: expected numeric range before potential transform.
- `potential_transform` and `cost_transform`: exact mapping from raw score to potential and cost.
- `missing_value_policy`: default behavior when a field is absent or null.
- `correlated_factors` and `double_counting_risk`: especially for `E_sar_structure`, `E_uncertainty`, `P_ambiguous`, and B patch fields.
- `branch_scope`: complete vehicle vs partial visibility.

## 5. Partial Visibility Isolation Audit

| Requirement | Status | Finding | Required Action |
|---|---|---|---|
| Partial visibility delayed until complete-vehicle mainline is stable | PASS | Roadmap and subagent contract explicitly delay truncation/occlusion branch. | Keep as Phase7. |
| `visibility_state`, `missing_extent_state`, and visible/full-center offset separate from full-vehicle state | PASS | Variables are listed separately as `V_t`, `M_t`, and visible/full-center offset. | Keep separate from `S_t`. |
| Visible support only as factor, veto, or uncertainty | PASS | All reviewed docs state visible support is not a full-center generator. | Preserve this rule in every future implementation note. |
| Leakage risk from visible source family or `visible_factor` into complete-vehicle selection | WARN | `visible` appears in source family and `visible_factor` appears as inference-safe evidence. This is fine only if it is veto/uncertainty, not a positive full-center source. | Add registry fields `branch_scope`, `active_in_complete_vehicle`, and `diagnostic_only`. |
| Partial factors remain diagnostic-only | PASS | Current docs treat missing extent and visible/full-center offset as future/partial branch factors. | Keep `missing_extent_factor` and `visible_full_center_offset_factor` diagnostic-only until standardized. |

Recommendation: partial visibility factors should remain diagnostic-only. They should not influence complete-vehicle candidate selection except as explicit veto/uncertainty signals accepted by AuditReleaseAgent.

## 6. Factor Prior Registry Readiness Audit

### Base Schema Coverage

Status: PASS for base registry fields.

The current registry records the required base fields:

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

### Extended Audit Fields Needed Before OOF Calibration

Status: BLOCKED for calibration readiness.

The registry must be extended before Phase3 can be considered calibration-ready:

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

### Complete-Vehicle Factors

| Factor | Status | Readiness Finding |
|---|---|---|
| `geometry_factor` | WARN | Base fields exist; needs valid range, transform, and double-counting audit with SAR structure. |
| `direction_factor` | WARN | Base fields exist; needs monotonicity and leakage class for signed posterior fields. |
| `source_factor` | WARN | Base fields exist; needs source-family prior origin and branch-scope for `visible`. |
| `sar_structure_factor` | WARN | Strong evidence, but high double-counting risk with uncertainty and B patch fields. |
| `optical_temporal_factor` | WARN | Needs join-stage and monotonicity audit; must stay soft prior. |
| `transition_factor` | WARN | Needs transform, scale, and missing-value policy before calibration. |
| `final_arbitration_factor` | BLOCKED | Current evidence includes B patch reproduction; must record patch-dependency risk before calibration. |
| `uncertainty_factor` | WARN | Strong evidence, but overlaps SAR structure and final arbitration. Needs correlation audit. |

### Partial-Visibility Factors

| Factor | Status | Readiness Finding |
|---|---|---|
| `visibility_factor` | WARN | Can remain as veto/uncertainty; needs branch-scope and active-phase fields. |
| `missing_extent_factor` | BLOCKED | Not standardized; must remain diagnostic-only. |
| `visible_full_center_offset_factor` | BLOCKED | Not standardized; must remain diagnostic-only and cannot generate full center. |

## 7. Engineering Patch vs Physical Model Risk

Status: WARN.

The accepted `sar_uncertainty_penalty_only` B patch, hierarchical diagnostics, factor graph diagnostics, and `final_arbitration_factor` have proven diagnostic consistency. They have not proven a final physical model.

Specific risks:

- `sar_uncertainty_penalty_only` may encode an engineering safety behavior rather than a calibrated SAR physical factor.
- Hierarchical diagnostics reproduced B patch with hard thresholds; this supports explanation, not physical completeness.
- Factor graph diagnostics reproduced B patch with fewer thresholds; this supports modeling form, not final factor validity.
- `final_arbitration_factor` may copy B patch behavior if patch fields or B patch agreement anchors are overweighted.

Required framing:

- B patch reproduction is evidence of diagnostic consistency.
- B patch reproduction is not proof of a final physical model.
- Any future calibrated model must pass factor prior audit and leakage audit before release consideration.

## 8. OOF Calibration Gate

OOF weight calibration remains `BLOCKED`.

Calibration cannot start until all of the following pass:

- Phase2 model spec review passes.
- Phase3 factor prior audit passes.
- Inference/eval field separation passes.
- Partial visibility factors are isolated from complete-vehicle selection.
- AuditReleaseAgent accepts boundary and prior-audit readiness.

Additional calibration prerequisites:

- Extended registry fields are complete.
- Patch-dependency risk is explicit for final arbitration and SAR uncertainty.
- Correlated factors and double-counting risks are documented.
- Missing-value and transform policies are documented.
- Complete-vehicle active factors are separated from Phase7 partial visibility factors.

## 9. Blocking Items And Required Fixes

| Item | Class | Status | Required Fix |
|---|---|---|---|
| Add extended factor audit fields to registry | MUST_FIX_BEFORE_PHASE3 | BLOCKED | Add `field_origin`, `leakage_class`, `join_stage`, `monotonicity`, `valid_range`, `potential_transform`, `cost_transform`, `clip_policy`, `missing_value_policy`, `correlated_factors`, `double_counting_risk`, `branch_scope`, `allowed_phase`, `active_in_complete_vehicle`, `diagnostic_only`, `patch_dependency_risk`, `grade_justification`. |
| Explicitly separate `final_action` from `release_decision` in interface docs | MUST_FIX_BEFORE_PHASE3 | WARN | Add a short terminology contract to the model spec or subagent file. |
| Mark visible source family as inactive/veto-only in complete-vehicle selection | MUST_FIX_BEFORE_PHASE3 | WARN | Add branch-scope and active-phase fields for all visible-related factors. |
| Mark missing extent and visible/full-center offset as diagnostic-only | MUST_FIX_BEFORE_PHASE3 | WARN | Add `diagnostic_only=true`, `active_in_complete_vehicle=false`, `allowed_phase=Phase7`. |
| Add transform and missing-value policy per factor | SHOULD_FIX_BEFORE_PHASE4 | WARN | Required before fixed-prior factor graph revalidation becomes comparable across factors. |
| Add correlated-factor and double-counting audit | SHOULD_FIX_BEFORE_PHASE4 | WARN | Especially for SAR structure, uncertainty, final arbitration, and B patch fields. |
| Add MAP/Viterbi pseudocode to Phase2 spec | SHOULD_FIX_BEFORE_PHASE4 | WARN | Current description is adequate conceptually but not yet implementation-facing. |
| Standardize partial visibility feature origins | LATER_PHASE7 | BLOCKED | Do not activate partial visibility factors before Phase7. |
| Define missing extent state values and valid ranges | LATER_PHASE7 | BLOCKED | Required for truncation/occlusion branch, not for current complete-vehicle audit. |

No new experiments are proposed by this audit.

## 10. Final Recommendation

Final recommendation: continue with Phase2 spec cleanup and Phase3 factor prior audit preparation. Do not calibrate weights. Do not replace the GM17 mainline. Do not run new experiments.

Precise next step:

Update `docs/gm17_factor_prior_registry.md` to include the extended audit fields and fill them for complete-vehicle factors first. In the same cleanup, mark partial-visibility factors as `diagnostic_only`, `active_in_complete_vehicle=false`, and `allowed_phase=Phase7`. After that, AuditReleaseAgent can re-check whether Phase3 factor prior audit execution is ready to begin.
