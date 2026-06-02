# GM17 Phase3 Factor Prior Audit Execution

Date: 2026-06-02

Status: Phase3 audit execution document. This document is not an experiment report, not an implementation plan, not a calibration report, and not a GM17 mainline replacement proposal.

## 1. Baseline And Boundary

Formal baseline files used:

- `README.md`
- `WORKSPACE_RULES.md`
- `CLAUDE.md`
- `00_project_control/13_CURRENT_RESEARCH_STATE.md`
- `00_project_control/12_OPTICAL_TO_SAR_LONG_TERM_SUBAGENTS.md`
- `docs/research_workflow.md`
- `docs/research_asset_policy.md`
- `docs/gm17_factor_prior_registry.md`
- `docs/gm17_factor_field_dictionary.md`
- `docs/gm17_factor_dependency_audit.md`
- `docs/gm17_phase2_phase3_readiness_audit.md`
- `docs/gm17_hierarchical_factor_graph_model_spec.md`
- `docs/optical_to_sar_vehicle_state_model_roadmap.md`
- `logs/2026-06-01_optical_to_sar_long_term_structure.md`

No untracked historical material, runtime outputs, archives, task scripts, tool scripts, old prompt dumps, auth/proxy material, or non-listed logs were used.

The tracked working tree was checked before writing this document set with:

- `git status --short --untracked-files=no`: no tracked changes reported before writing. This command hides untracked files and must not be interpreted as a full repository-cleanliness claim.
- `git status --short --untracked-files=all -- docs/gm17_phase3_factor_prior_audit_execution.md docs/gm17_phase3_factor_acceptance_matrix.md docs/gm17_phase3_factor_blocker_register.md`: the three new Phase3 documents must be reviewed path-scope before stage or commit.
- `git log --oneline --decorate -5`: `14eb129` was current `HEAD -> main, origin/main, origin/HEAD`.

## 2. Current Phase Judgment

The next valid activity is `Phase3 factor prior audit execution`.

This is an audit activity only. It does not authorize calibration, implementation, training, candidate-bank changes, new performance experiments, GM17 mainline replacement, learned-weight generation, or OOF calibration.

GM17 is treated as a staged evidence source, not as the final system architecture or final physical model template. B patch reproduction is diagnostic consistency evidence only and must not be treated as final physical-model proof.

## 3. Responsibility Boundaries

The long-term subagents are research-governance roles, not runtime agents.

| Role | Phase3 responsibility used here | Explicit non-responsibility in this round |
|---|---|---|
| `StateGraphAgent` | Complete-vehicle factor definitions, MAP/Viterbi model boundary, complete-vehicle Phase4 candidate framing. | No runtime agent creation, no model implementation, no training. |
| `PartialVisibilityAgent` | Partial visibility, truncation, occlusion, missing extent, visible/full-center offset boundary notes. | No activation of partial visibility branch and no full-center generation from visible support. |
| `AuditReleaseAgent` | Candidate-bank, leakage, double-counting, patch-dependency, and release-gate review boundaries. | No scoring, tuning, or factor-prior selection by implementation. |

`Phase3FactorAuditExecutor` may be used only as a temporary stage-execution label for this document set. It is not a long-term subagent.

## 4. Audit Grade Contract

This execution uses only four audit grades:

- `PASS`: field origin, leakage class, join stage, range/transform/missing policy are clear; no eval-only field is introduced; double-counting and patch-dependency risks are controlled; the factor may become a Phase4 fixed-prior revalidation candidate.
- `WARN`: the factor may remain in Phase3/Phase4 diagnostic or controlled fixed-prior checks, but must carry explicit control conditions.
- `FAIL`: the definition is unsafe or inconsistent and must go back to spec or registry correction.
- `BLOCKED`: the factor must not enter Phase4 or calibration. It can only remain diagnostic-only or future-phase until schema, branch isolation, or AuditReleaseAgent gates pass.

The baseline registry also contains `evidence_grade` values `A`, `B`, and `C`. In this document set those values are treated only as baseline evidence-strength labels. They are not Phase3 audit grades. The Phase3 audit grade is derived from leakage, join-stage, transform, missing-value, double-counting, branch-scope, and patch-dependency controls.

## 5. Factor Audit Order

The audit order is:

1. `geometry_factor`
2. `direction_factor`
3. `source_factor`
4. `sar_structure_factor`
5. `uncertainty_factor`
6. `optical_temporal_factor`
7. `transition_factor`
8. `final_arbitration_factor`
9. `visibility_factor`
10. `missing_extent_factor`
11. `visible_full_center_offset_factor`

## 6. Acceptance Summary

| Audit grade | Count | Factors |
|---|---:|---|
| `PASS` | 0 | None as unconditional Phase4 entries. |
| `WARN` | 7 | `geometry_factor`, `direction_factor`, `source_factor`, `sar_structure_factor`, `uncertainty_factor`, `optical_temporal_factor`, `transition_factor` |
| `FAIL` | 0 | None found from the formal baseline. |
| `BLOCKED` | 4 | `final_arbitration_factor`, `visibility_factor`, `missing_extent_factor`, `visible_full_center_offset_factor` |

Interpretation:

- No factor receives an unconditional `PASS` because every complete-vehicle candidate still carries a documented control condition or AuditReleaseAgent gate.
- `WARN` factors may support controlled Phase3 and, where explicitly eligible, controlled Phase4 fixed-prior revalidation.
- `BLOCKED` factors remain diagnostic-only or future-phase and must not enter Phase4 active fixed-prior scoring or calibration.

The detailed acceptance matrix is recorded in `docs/gm17_phase3_factor_acceptance_matrix.md`.

## 7. Factor-By-Factor Audit Execution

### 7.1 `geometry_factor`

Audit grade: `WARN`.

Baseline basis:

- Field origin is fixed candidate bank plus state-energy diagnostic tables.
- Leakage class is `inference_safe`.
- Join stage is candidate-level node fields joined by `candidate_id`.
- Required range, transform, clip, and missing-value policies are present in the registry.

Main control condition:

- Separate geometry terms from SAR shell or escape terms before Phase4. `directional_shell_score` and `geometry_escape_refined_score` can carry SAR-structure evidence, so duplicate support must be prevented.

Phase4 eligibility:

- Eligible only as a controlled complete-vehicle fixed-prior candidate after geometry-vs-SAR shell ownership is declared.

### 7.2 `direction_factor`

Audit grade: `WARN`.

Baseline basis:

- Field origin is signed escape posterior and state-energy diagnostic tables.
- Leakage class is `inference_safe`.
- Join stage is row-level posterior fields joined to candidate-level direction fields.
- Posterior probabilities, match scores, and margins have bounded potential policies.

Main control condition:

- Keep signed direction evidence separate from source-family trust. Direction assumptions must not be counted once through `direction_factor` and again through `source_factor`.

Phase4 eligibility:

- Eligible only as a controlled complete-vehicle fixed-prior candidate after source-direction overlap is explicitly controlled.

### 7.3 `source_factor`

Audit grade: `WARN`.

Baseline basis:

- Field origin is candidate bank source labels plus diagnostic source priors.
- Non-visible candidate source labels are inference-safe in the complete-vehicle branch.
- Visible source behavior is only diagnostic/veto/uncertainty behavior.

Main control condition:

- Use `source_factor` in Phase4 only for non-visible source families: `base`, `wedge`, `bidirectional`, and `track_signed`. Visible-source behavior must remain veto/uncertainty-only and must not generate full-center predictions.

Phase4 eligibility:

- Controlled non-visible `source_factor` is eligible. Visible-source behavior is not eligible as a complete-vehicle full-center source.

### 7.4 `sar_structure_factor`

Audit grade: `WARN`.

Baseline basis:

- Field origin is state-energy diagnostic and fixed-bank factor tables.
- Leakage class is `diagnostic_inference_safe` until fields are traced to non-patch origins.
- Patch-dependency risk is `medium`.
- Baseline dependency audit records overlap with `uncertainty_factor`, `geometry_factor`, and `final_arbitration_factor`.

Main control condition:

- Split SAR support evidence from uncertainty evidence before Phase4 or calibration. SAR ambiguity, artifact, conflict, `E_sar_structure`, and `E_uncertainty` style evidence must not be penalized twice.

Phase4 eligibility:

- Not a current preferred Phase4 fixed-prior candidate in this audit. It may remain in controlled diagnostic or support-separation review until overlap with uncertainty and B patch behavior is resolved.

### 7.5 `uncertainty_factor`

Audit grade: `WARN`.

Baseline basis:

- Field origin is signed posterior, state-energy diagnostics, and SAR ambiguity diagnostics.
- Leakage class is `diagnostic_inference_safe` until B patch coupling is separated.
- Patch-dependency risk is `medium`.
- It can aggregate ambiguity, artifact risk, confidence, conflict, and factor disagreement.

Main control condition:

- Keep uncertainty routing separate from SAR support and final arbitration behavior. Missing uncertainty fields should default to conservative `WARN`, not optimistic pass.

Phase4 eligibility:

- Not a current preferred Phase4 fixed-prior candidate. It may remain as controlled diagnostic or uncertainty-route evidence only after SAR-structure overlap is separated.

### 7.6 `optical_temporal_factor`

Audit grade: `WARN`.

Baseline basis:

- Field origin is optical temporal inference tables and boundary-safe temporal features.
- Leakage class is `inference_safe`.
- Join stage is row-level and track-level prior joined to candidate nodes.
- Missing temporal prior defaults to neutral soft prior, not failure.

Main control condition:

- Optical temporal evidence must remain a soft prior and must not hard-lock or overwrite the full center. Smoothness overlap with `transition_factor` must be controlled.

Phase4 eligibility:

- Eligible only as a controlled complete-vehicle fixed-prior candidate when kept as a soft prior and separated from transition-edge continuity.

### 7.7 `transition_factor`

Audit grade: `WARN`.

Baseline basis:

- Field origin is fixed candidate state fields and track path diagnostics.
- Leakage class is `inference_safe`.
- Join stage is adjacent candidate-pair edge construction within each track.
- Missing required state fields block edge construction.

Main control condition:

- Keep transition continuity separate from optical temporal smoothness and signed direction continuity. Transition must not become a release gate by itself.

Phase4 eligibility:

- Eligible only as a controlled complete-vehicle fixed-prior candidate after smoothness overlap with `optical_temporal_factor` is controlled.

### 7.8 `final_arbitration_factor`

Audit grade: `BLOCKED`.

Baseline basis:

- Field origin is diagnostic factor graph outputs and B patch comparison artifacts.
- Leakage class is `diagnostic_inference_safe`.
- Patch-dependency risk is `high`.
- Baseline dependency audit marks final arbitration against B patch behavior as blocked for calibration.

Blocking condition:

- `final_arbitration_factor` can copy B patch action behavior and make diagnostic reproduction look like physical model validity.

Phase4 eligibility:

- Not eligible as an active Phase4 fixed-prior scoring factor or for calibration. It may remain Phase3 diagnostic consistency evidence only until patch dependency is separated and accepted by AuditReleaseAgent.

### 7.9 `visibility_factor`

Audit grade: `BLOCKED`.

Baseline basis:

- Field origin is current visible factor diagnostics and future partial-visibility inference tables.
- Leakage class is `diagnostic_inference_safe`.
- Branch scope is `partial_visibility_veto`.
- Allowed phase is `Phase7`.

Blocking condition:

- Visible support must not generate a full center or act as a full-center candidate source.

Phase4 eligibility:

- Not eligible for complete-vehicle Phase4. It may remain inactive/veto/uncertainty interface evidence and future Phase7 diagnostic material.

### 7.10 `missing_extent_factor`

Audit grade: `BLOCKED`.

Baseline basis:

- Field origin is future partial-visibility inference tables.
- Leakage class is `future_inference_required`.
- Current code fields are not standardized.
- Allowed phase is `Phase7`.

Blocking condition:

- Valid range, transform, cost, clipping, and inference-safe schema are blocked until Phase7 standardization.

Phase4 eligibility:

- Not eligible. It remains diagnostic-only and must not enter the complete-vehicle mainline.

### 7.11 `visible_full_center_offset_factor`

Audit grade: `BLOCKED`.

Baseline basis:

- Field origin is future partial-visibility inference tables.
- Leakage class is `future_inference_required`.
- Current code fields are not standardized.
- Allowed phase is `Phase7`.

Blocking condition:

- No standardized inference-safe offset schema exists, and visible support must not be used to generate or shift a latent full-vehicle center in the current phase.

Phase4 eligibility:

- Not eligible. It remains diagnostic-only and future Phase7 material.

## 8. Controlled Phase4 Eligibility Note

This document does not authorize Phase4 execution.

Controlled Phase4 fixed-prior revalidation candidates, if AuditReleaseAgent accepts the control conditions, are:

- `geometry_factor`
- `direction_factor`
- controlled non-visible `source_factor`
- `optical_temporal_factor`
- `transition_factor`

The following are not current preferred Phase4 fixed-prior candidates and require additional control or separation first:

- `sar_structure_factor`: requires support-vs-uncertainty separation and patch-risk control.
- `uncertainty_factor`: requires SAR-structure and final-arbitration overlap control.
- `final_arbitration_factor`: blocked from active Phase4 scoring and calibration until B patch dependency is separated.

The following remain diagnostic-only or future-phase:

- `visibility_factor`
- `missing_extent_factor`
- `visible_full_center_offset_factor`

OOF calibration remains blocked.

## 9. Partial Visibility And Near-Field Boundary

Truncation, occlusion, near-field geometry regime, partial visibility, and missing extent may be referenced only as future research boundaries in this Phase3 document set.

Preserved prohibitions:

- Visible support must not generate full center.
- Missing extent must not enter the complete-vehicle mainline.
- Near-field state must not modify the candidate bank.
- Near-field state must not replace the complete-vehicle selector.
- Partial or near-field branches must not enter OOF calibration.
- No new experiments are authorized.

Future route:

- Phase7A: truncation/occlusion partial visibility modeling.
- Phase7B: near-field geometry regime modeling.
- Phase8: hybrid integration and arbitration.

Near-field should be treated as a future geometry-mechanism or geometry-reliability route, not as an occlusion shortcut, not as a candidate generator, and not as a replacement for the complete-vehicle selector.

## 10. GO/NO-GO Recommendation

GO:

- Proceed with human review of this Phase3 audit document set.
- Use the acceptance matrix and blocker register as the next AuditReleaseAgent review surface.

NO-GO:

- Do not run Phase4 revalidation yet.
- Do not start OOF calibration.
- Do not train a ranker, CRF, or OOF model.
- Do not modify algorithms.
- Do not modify the candidate bank.
- Do not replace the GM17 mainline.
- Do not activate partial visibility or near-field branches.

## 11. Related Documents In This Set

- `docs/gm17_phase3_factor_acceptance_matrix.md`
- `docs/gm17_phase3_factor_blocker_register.md`
