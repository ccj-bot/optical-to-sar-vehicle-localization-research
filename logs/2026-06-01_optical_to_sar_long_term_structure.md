# Optical-to-SAR Long-Term Structure Log

## Start

- Time: 2026-06-01
- Workspace: `D:\profile\research\workspace`
- Interpreter default: `D:\MINICONDA\envs\py311\python.exe`
- Task: establish long-term project structure for 光学迁移到SAR中的车辆定位与候选选择.
- Boundary: no algorithm edit, no candidate bank change, no ranker training, no GM17 mainline replacement, no new performance experiment.

## Deliverables

- `D:\profile\research\workspace\00_project_control\12_OPTICAL_TO_SAR_LONG_TERM_SUBAGENTS.md`
- `D:\profile\research\workspace\docs\optical_to_sar_vehicle_state_model_roadmap.md`
- `D:\profile\research\workspace\docs\gm17_hierarchical_factor_graph_model_spec.md`
- `D:\profile\research\workspace\docs\gm17_factor_prior_registry.md`

## Completion

- Created the long-term 3-agent control file with `StateGraphAgent`, `PartialVisibilityAgent`, and `AuditReleaseAgent`.
- Created roadmap with the project statement `光学迁移到SAR中的车辆定位与候选选择`, complete-vehicle-first route, partial visibility branch, formal factor graph expression, MAP/Viterbi inference, and Phase 1 through Phase 8 plan.
- Created GM17 hierarchical factor graph model specification with variables, factors, inference procedure, and factor prior audit gate.
- Created factor prior registry with the required schema and initial records for geometry, direction, source, SAR structure, optical temporal, transition, final arbitration, visibility, missing extent, visible/full-center offset, and uncertainty factors.
- Validation: required file paths exist; required subagent names, phase names, formal expression, visible/full-center restrictions, factor prior schema fields, and no-mainline/no-ranker/no-candidate-bank boundaries are present.
- No algorithm scripts were edited for this planning task, and no new experiment was run.

## 2026-06-02 Phase2/Phase3 Readiness Audit

- Added: `D:\profile\research\workspace\docs\gm17_phase2_phase3_readiness_audit.md`
- Scope: documentation-only readiness audit for entering Phase3 factor prior audit after Phase2 model-spec review.
- Decision: `CONDITIONAL_GO_WITH_BLOCKERS`
- Main blockers: extend factor prior registry fields, separate `final_action` from `release_decision`, mark visible and missing-extent partial factors as diagnostic-only and inactive in complete-vehicle selection.
- Boundary: no candidate bank change, no algorithm code edit, no new experiment, no ranker/CRF/OOF calibration, no GM17 mainline replacement.

## 2026-06-02 Phase3 Factor Prior Registry Cleanup

- Updated: `D:\profile\research\workspace\docs\gm17_factor_prior_registry.md`
- Added: `D:\profile\research\workspace\docs\gm17_factor_field_dictionary.md`
- Added: `D:\profile\research\workspace\docs\gm17_factor_dependency_audit.md`
- Scope: documentation-only Phase3 factor prior registry cleanup.
- Changes: added extended audit fields, per-factor audit cards, branch separation rules, terminology contract for `final_action` vs `release_decision`, patch-dependency notes, double-counting risk notes, field dictionary, and factor dependency matrix.
- Boundary: no algorithm code changed, no candidate bank modified, no new experiment run, no ranker/CRF/OOF model trained, no OOF calibration started, and GM17 mainline was not replaced.
- Status: registry is ready for Phase3 audit execution preparation; OOF calibration remains `BLOCKED`.
