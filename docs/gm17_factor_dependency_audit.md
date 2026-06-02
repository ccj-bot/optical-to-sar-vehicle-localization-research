# GM17 Factor Dependency Audit

Date: 2026-06-02

Purpose: summarize correlated factors and double-counting risks before any Phase4 fixed-prior revalidation or Phase5 track-block OOF calibration.

Boundary: documentation-only. This file does not authorize experiments, model training, candidate bank changes, or GM17 mainline replacement.

## Executive Status

Decision: `PASS_FOR_PHASE3_AUDIT_EXECUTION`, `BLOCKED_FOR_OOF_CALIBRATION`.

Phase3 can use this dependency audit to review factor priors. OOF calibration remains blocked until double-counting controls and patch-dependency controls are accepted by AuditReleaseAgent.

## Dependency Matrix

| factor_a | factor_b | status | overlap | risk | required_control |
|---|---|---|---|---|---|
| `sar_structure_factor` | `uncertainty_factor` | WARN | Both consume ambiguity, artifact, conflict, `E_sar_structure`, and `E_uncertainty` style evidence. | Ambiguous SAR support may be penalized twice. | Split support evidence from uncertainty evidence before calibration. |
| `geometry_factor` | `sar_structure_factor` | WARN | Directional shell and geometry escape scores can carry both geometry and SAR structure information. | Escape candidates may receive duplicate support. | Declare which shell terms belong to geometry and which belong to SAR structure. |
| `direction_factor` | `source_factor` | WARN | Source family trust often assumes an expected direction; direction factor separately scores signed posterior match. | Wrong-direction or right-direction evidence may be counted twice. | Treat source prior as source-only unless explicitly conditioned on direction. |
| `transition_factor` | `optical_temporal_factor` | WARN | Both can reward smooth track behavior and temporal consistency. | Smooth but wrong paths may be over-rewarded. | Keep optical temporal as soft prior and transition as edge continuity; audit weights separately. |
| `final_arbitration_factor` | B patch behavior | BLOCKED | Final arbitration can reproduce `sar_uncertainty_penalty_only` actions. | Model may copy patch behavior and appear physically valid. | Record patch dependency; do not calibrate until patch features are separated or controlled. |
| `visibility_factor` | `source_factor` | WARN | `visible_support_candidate` can appear as source family while visible factor also scores visible evidence. | Visible support could act like a full-center generator. | Visible source family is veto/uncertainty-only; not active as full-center source. |
| `missing_extent_factor` | `visible_full_center_offset_factor` | BLOCKED | Both future factors may encode partial visibility and missing full extent. | Partial visibility branch can double-count missing extent. | Keep both diagnostic-only until Phase7 schema is standardized. |

## Patch Dependency Audit

| factor | patch_dependency_risk | status | audit note |
|---|---|---|---|
| `final_arbitration_factor` | high | BLOCKED_FOR_CALIBRATION | B patch reproduction is diagnostic consistency evidence, not physical proof. |
| `sar_structure_factor` | medium | WARN | Accepted B patch is SAR uncertainty based; support and uncertainty must be separated. |
| `uncertainty_factor` | medium | WARN | Ambiguity/uncertainty fields explain B patch behavior and can over-protect base. |
| `direction_factor` | low | PASS | Direction conflict evidence is separately interpretable, but still correlated with source. |
| `geometry_factor` | low | PASS | Geometry has independent physical meaning, but overlaps SAR shell scores. |

## Branch Separation Audit

| factor | complete_vehicle_active | partial_visibility_active | status | note |
|---|---:|---:|---|---|
| `geometry_factor` | true | false | PASS | Complete-vehicle factor. |
| `direction_factor` | true | false | PASS | Complete-vehicle factor. |
| `source_factor` | true | limited | WARN | Visible source behavior must be veto/uncertainty only. |
| `sar_structure_factor` | true | future | WARN | Complete-vehicle SAR support active; partial visibility extension later. |
| `optical_temporal_factor` | true | false | PASS | Soft prior only. |
| `transition_factor` | true | false | PASS | Track edge factor. |
| `final_arbitration_factor` | true | future | WARN | Diagnostic consistency only; not release decision. |
| `visibility_factor` | false | true | BLOCKED_FROM_COMPLETE_VEHICLE | Veto/uncertainty only until Phase7. |
| `missing_extent_factor` | false | true | BLOCKED_NOT_STANDARDIZED | Phase7 only. |
| `visible_full_center_offset_factor` | false | true | BLOCKED_NOT_STANDARDIZED | Phase7 only. |
| `uncertainty_factor` | true | future | WARN | Complete-vehicle uncertainty active; partial extension later. |

## Calibration Gate

OOF calibration remains `BLOCKED` until:

1. Factor prior registry fields are complete.
2. Field dictionary leakage classes are accepted.
3. Double-counting risks above have explicit controls.
4. Patch dependency risk for final arbitration is controlled.
5. Partial visibility factors are inactive in complete-vehicle selection.
6. AuditReleaseAgent accepts prior-audit readiness.

No new experiments are proposed by this document.
