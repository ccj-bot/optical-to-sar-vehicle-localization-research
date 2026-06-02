# GM17 Phase3 Factor Blocker Register

Date: 2026-06-02

Status: Phase3 blocker register. This document records blocker structure and current blockers only. It does not authorize experiments, training, calibration, code changes, candidate-bank changes, subagent creation, or GM17 mainline replacement.

## 1. Source Boundary

This register is derived only from the formal baseline files listed in `docs/gm17_phase3_factor_prior_audit_execution.md`.

No untracked historical material, runtime outputs, archives, task scripts, tool scripts, old prompt dumps, auth/proxy material, or non-listed logs were used.

## 2. Blocker Register Schema

Each blocker records:

- `blocker_id`
- `affected_factor`
- `blocker_class`
- `evidence_source`
- `why_it_blocks_Phase4_or_calibration`
- `required_resolution`
- `responsible_long_term_subagent`
- `current_status`

## 3. Current Blockers

| blocker_id | affected_factor | blocker_class | evidence_source | why_it_blocks_Phase4_or_calibration | required_resolution | responsible_long_term_subagent | current_status |
|---|---|---|---|---|---|---|---|
| `B001` | All factors | Leakage and boundary gate | `WORKSPACE_RULES.md`, `CLAUDE.md`, `docs/gm17_factor_field_dictionary.md`, `00_project_control/13_CURRENT_RESEARCH_STATE.md` | Eval-only fields such as GT, oracle, IoU, center error, condition labels, truncation labels, occlusion labels, and final annotation fields must never enter inference. Any leak blocks Phase4 and calibration. | Audit every inference-facing output for field-origin, leakage class, and join-stage separation before Phase4. | `AuditReleaseAgent` | Open gate; no leakage was identified by this document-level audit. Runtime artifacts, generated tables, and future inference-facing outputs remain unaudited and must be rechecked before Phase4 or calibration. |
| `B002` | `geometry_factor`, `sar_structure_factor` | Double-counting | `docs/gm17_factor_dependency_audit.md`, `docs/gm17_factor_prior_registry.md` | Directional shell and geometry escape scores can carry both geometry and SAR-structure evidence, causing duplicate support for escape candidates. | Declare which shell and escape terms belong to geometry and which belong to SAR structure before Phase4. | `StateGraphAgent`, reviewed by `AuditReleaseAgent` | Open control condition. |
| `B003` | `direction_factor`, `source_factor` | Double-counting | `docs/gm17_factor_dependency_audit.md`, `docs/gm17_factor_prior_registry.md` | Source-family trust can embed expected direction while `direction_factor` separately scores signed posterior match. | Treat source prior as source-only unless explicit direction conditioning is documented and audited. | `StateGraphAgent`, reviewed by `AuditReleaseAgent` | Open control condition. |
| `B004` | `source_factor`, `visibility_factor` | Branch isolation | `WORKSPACE_RULES.md`, `docs/gm17_factor_dependency_audit.md`, `docs/gm17_phase2_phase3_readiness_audit.md`, `docs/gm17_factor_prior_registry.md` | Visible source behavior can leak into complete-vehicle full-center selection if treated as a positive source family. | Limit Phase4 `source_factor` to non-visible families. Keep visible source behavior veto/uncertainty-only until Phase7. | `PartialVisibilityAgent`, reviewed by `AuditReleaseAgent` | Open blocker for visible source; non-visible source can remain conditional Phase4 candidate. |
| `B005` | `sar_structure_factor`, `uncertainty_factor` | Double-counting and patch dependency | `docs/gm17_factor_dependency_audit.md`, `docs/gm17_factor_prior_registry.md`, `00_project_control/13_CURRENT_RESEARCH_STATE.md` | Ambiguity, artifact, conflict, `E_sar_structure`, and `E_uncertainty` style evidence can be counted twice. Both factors are also tied to accepted SAR uncertainty patch behavior. | Split SAR support evidence from uncertainty evidence and record patch-dependency controls before Phase4 or calibration. | `StateGraphAgent`, reviewed by `AuditReleaseAgent` | Open blocker for calibration; diagnostic review only. |
| `B006` | `final_arbitration_factor` | High patch dependency | `docs/gm17_factor_dependency_audit.md`, `docs/gm17_factor_prior_registry.md`, `docs/gm17_phase2_phase3_readiness_audit.md` | Final arbitration can reproduce B patch actions and appear physically valid without independent physical proof. | Separate `final_action` diagnostic consistency from B patch action copying; AuditReleaseAgent must accept patch-dependency audit before active Phase4 scoring or calibration. | `AuditReleaseAgent` | Blocked from active Phase4 scoring and calibration. |
| `B007` | `optical_temporal_factor`, `transition_factor` | Smoothness double-counting | `docs/gm17_factor_dependency_audit.md`, `docs/gm17_factor_prior_registry.md`, `docs/research_workflow.md` | Optical temporal and transition factors can both reward smooth paths, over-rewarding smooth but wrong trajectories. | Keep optical temporal as soft prior and transition as edge continuity; audit weights separately before any calibration. | `StateGraphAgent`, reviewed by `AuditReleaseAgent` | Open control condition. |
| `B008` | `visibility_factor`, `missing_extent_factor`, `visible_full_center_offset_factor` | Partial-visibility branch isolation | `WORKSPACE_RULES.md`, `00_project_control/12_OPTICAL_TO_SAR_LONG_TERM_SUBAGENTS.md`, `docs/optical_to_sar_vehicle_state_model_roadmap.md`, `docs/gm17_factor_prior_registry.md` | Partial visibility factors are Phase7 only and must not enter complete-vehicle selection. Visible support cannot generate full center. | Keep these factors diagnostic-only, inactive in complete-vehicle scoring, and gated behind a stable complete-vehicle branch. | `PartialVisibilityAgent`, reviewed by `AuditReleaseAgent` | Blocked from Phase4 complete-vehicle use. |
| `B009` | `missing_extent_factor`, `visible_full_center_offset_factor` | Future schema missing | `docs/gm17_factor_prior_registry.md`, `docs/gm17_factor_dependency_audit.md`, `docs/gm17_phase2_phase3_readiness_audit.md` | Current code fields, valid range, potential transform, cost transform, clip policy, and standardized inference-safe origins do not exist for these future factors. | Standardize Phase7 partial-visibility schema before any active use. | `PartialVisibilityAgent` | Blocked until Phase7 schema work. |
| `B010` | Near-field future route | Research boundary | `docs/optical_to_sar_vehicle_state_model_roadmap.md`, `docs/research_workflow.md`, `00_project_control/13_CURRENT_RESEARCH_STATE.md` | Near-field geometry regime is a future geometry-mechanism route. It cannot modify the candidate bank, replace the selector, or enter OOF calibration in Phase3. | Reference only as a future boundary: Phase7B near-field geometry regime modeling after current complete-vehicle audit gates. | `StateGraphAgent`, reviewed by `AuditReleaseAgent` | Boundary blocker; no implementation allowed in this round. |

## 4. Calibration Block Summary

OOF calibration remains blocked because:

- `final_arbitration_factor` has high B patch dependency.
- `sar_structure_factor` and `uncertainty_factor` carry patch and double-counting risks.
- Partial-visibility factors are not standardized and remain Phase7 diagnostic-only.
- AuditReleaseAgent must re-check inference/evaluation separation before any runtime artifact.

## 5. Phase4 Block Summary

This register does not authorize Phase4 execution.

Conditional Phase4 fixed-prior candidates are blocked until their listed controls are accepted:

- `geometry_factor`: `B002`
- `direction_factor`: `B003`
- non-visible `source_factor`: `B003`, `B004`
- `optical_temporal_factor`: `B007`
- `transition_factor`: `B007`

The following are not active Phase4 candidates in this audit:

- `sar_structure_factor`: `B002`, `B005`
- `uncertainty_factor`: `B005`
- `final_arbitration_factor`: `B006`
- `visibility_factor`: `B008`
- `missing_extent_factor`: `B008`, `B009`
- `visible_full_center_offset_factor`: `B008`, `B009`

## 6. Required Human Review

Before staging or committing this document set, manually check:

- The three generated files are the only intended additions.
- All paths are repository-relative.
- No runtime output, private local path, credential-adjacent detail, or old prompt material is referenced.
- Every factor has exactly one `PASS`/`WARN`/`FAIL`/`BLOCKED` audit grade.
- Phase4 language remains conditional and does not authorize revalidation execution.
- OOF calibration remains explicitly blocked.
