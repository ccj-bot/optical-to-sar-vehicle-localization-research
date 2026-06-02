# Optical-to-SAR Vehicle Localization Research

This repository is a research workspace for vehicle localization and candidate selection in optical-to-SAR transfer. It records model specifications, audit decisions, factor-prior evidence, and research governance for a long-term hierarchical factor graph approach.

This is not a product engineering repository. The primary goals are:

- preserve the research evidence chain;
- keep model evolution auditable;
- separate inference-safe fields from evaluation-only fields;
- document stop/go decisions before calibration or selector refactoring;
- prevent runtime outputs, sensitive materials, and unreviewed scripts from entering the formal research record.

## Current Direction

The current work is not a GM17 patch experiment. GM17 remains a staged validation line, but the long-term direction is a complete-vehicle-first hierarchical factor graph:

```text
fixed candidate bank
-> vehicle state variables
-> factor priors
-> MAP/Viterbi-style inference
-> final_action
-> AuditReleaseAgent release_decision
```

The current permitted work is Phase3 factor prior audit execution. Phase3 audit preparation is ready as a documentation artifact. Track-block OOF calibration remains BLOCKED.

## Repository Status

- Default branch: `main`.
- Current formal baseline: Phase3 factor prior audit preparation.
- Current allowed work: Phase3 factor prior audit execution.
- Blocked work: OOF calibration, ranker training, CRF training, candidate-bank changes, and GM17 mainline replacement.

## Current Boundaries

- Do not change the candidate bank.
- Do not train a ranker, CRF, or OOF model.
- Do not replace the GM17 mainline selector.
- Do not run new performance experiments from the current documents.
- Do not package B patch reproduction as proof of a final physical model.
- Do not use visible support as a full-center generator.
- Do not allow evaluation-only fields into inference outputs.

## Core Document Entry Points

- `00_project_control/12_OPTICAL_TO_SAR_LONG_TERM_SUBAGENTS.md`
- `00_project_control/13_CURRENT_RESEARCH_STATE.md`
- `docs/optical_to_sar_vehicle_state_model_roadmap.md`
- `docs/gm17_hierarchical_factor_graph_model_spec.md`
- `docs/gm17_phase2_phase3_readiness_audit.md`
- `docs/gm17_factor_prior_registry.md`
- `docs/gm17_factor_field_dictionary.md`
- `docs/gm17_factor_dependency_audit.md`
- `docs/research_workflow.md`
- `docs/research_asset_policy.md`

## Status Summary

- Phase3 factor prior audit execution preparation: PASS.
- OOF calibration: BLOCKED.
- Partial visibility full-center generation: BLOCKED.
- GM17 mainline replacement: BLOCKED.

This README does not make performance claims. Any metric, recovery count, or selected-prediction statement must remain tied to a boundary-audited report and must not be generalized beyond its documented scope.
