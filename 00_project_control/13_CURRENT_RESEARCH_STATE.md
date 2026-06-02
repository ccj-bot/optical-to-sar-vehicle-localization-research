# Current Research State

Date: 2026-06-02

## Current Decision

Decision: `PASS_FOR_PHASE3_AUDIT_EXECUTION_PREP`, `BLOCKED_FOR_OOF_CALIBRATION`.

The repository is prepared for Phase3 factor prior audit execution as a documentation and audit activity. It is not authorized for OOF calibration, ranker training, CRF training, candidate-bank changes, new performance experiments, or GM17 mainline replacement.

## Current Accepted Branch And Commits

- Current accepted branch: `main`.
- Remote baseline: `origin/main`.
- Phase3 documentation branch: `origin/docs/phase3-factor-prior-audit`.
- Phase3 registry preparation commit: `66c401a`.
- Runtime-output ignore policy commit: `0d42071`.

These commits establish the formal Phase3 documentation base and repository hygiene policy. They do not authorize algorithmic changes or calibration.

## Current Allowed Work

Allowed work:

- Phase3 factor prior audit execution;
- review of field origin, leakage class, join stage, transforms, clipping, missing-value policy, correlated factors, and double-counting risk;
- review of patch-dependency risk for final arbitration, SAR structure, and uncertainty factors;
- review of complete-vehicle versus partial-visibility branch separation;
- documentation-only cleanup that preserves current research boundaries.

## Blocked Work

Blocked work:

- OOF calibration;
- ranker training;
- CRF training;
- candidate bank changes;
- GM17 mainline replacement;
- new performance experiments;
- visible support as a full-center generator;
- activating missing extent or visible/full-center offset factors in complete-vehicle selection.

## Next Minimal Action

The next minimal action is Phase3 factor prior audit execution.

The audit should use:

- `docs/gm17_factor_prior_registry.md`;
- `docs/gm17_factor_field_dictionary.md`;
- `docs/gm17_factor_dependency_audit.md`;
- `docs/gm17_phase2_phase3_readiness_audit.md`.

The goal is to decide which factors are accepted for fixed-prior revalidation, which remain diagnostic-only, and which risks block later calibration.

This next action is not OOF calibration.

## Open Risks

- `final_arbitration_factor` has high B patch dependency risk.
- `sar_structure_factor` and `uncertainty_factor` may double-count ambiguity and conflict evidence.
- `geometry_factor` and `sar_structure_factor` may double-count shell or escape evidence.
- `direction_factor` and `source_factor` may double-count direction assumptions.
- `transition_factor` and `optical_temporal_factor` may double-count smoothness.
- Visible source-family behavior can leak into full-center selection if not kept veto/uncertainty-only.
- Partial visibility factors are not standardized and remain Phase7 diagnostic-only.

## Repository Hygiene Open Items

- Tracked deleted output remains unresolved and requires a separate explicit decision. Do not restore, delete, or stage it as part of research-state documentation work.
- Local `.codex` or `.codex/` assistant state must remain out of the repository.

## Release Interpretation

`final_action` is a model-level action. `release_decision` is an AuditReleaseAgent project-level decision. These terms must remain separate in all future documents.

B patch reproduction is diagnostic consistency evidence only. It is not proof of a final physical model.
