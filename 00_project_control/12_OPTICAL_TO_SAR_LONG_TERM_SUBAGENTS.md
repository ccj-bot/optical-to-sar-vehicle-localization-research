# Optical-to-SAR Long-Term Subagents

Date: 2026-06-01

Project name: 光学迁移到SAR中的车辆定位与候选选择

This file supersedes the GM17-only two-agent framing for long-term planning. GM17 remains an important staged validation line, but it is not the final system. The long-term objective is a maintainable vehicle-state and candidate-selection model that can first handle complete, structurally clear vehicles, then extend to truncation, occlusion, and partial visibility.

Current boundary for this planning step:

- Do not modify the candidate bank.
- Do not train a ranker, CRF, or OOF weight model.
- Do not modify the GM17 mainline selector.
- Do not run new performance experiments.
- Do not package engineering patches as final physical models.
- Do not use visible support as a full-center generator.

## Agent 1: StateGraphAgent

Scope: complete-vehicle optimistic mainline and hierarchical factor graph modeling.

Responsibilities:

- Own the hierarchical factor graph model for complete, unoccluded, structurally clear vehicle cases.
- Define latent variables:
  - `risk state`
  - `direction state`
  - `source family`
  - `selected candidate`
  - `final action`
- Define complete-vehicle factors:
  - geometry
  - direction
  - source
  - SAR structure
  - optical temporal
  - transition
  - final arbitration
- Maintain the MAP/Viterbi inference design over fixed candidates.
- Convert current GM17 diagnostic prototypes into a model specification before any mainline refactor.
- Plan later track-block OOF weight calibration, after factor prior audit passes.
- Keep optical temporal evidence as a soft prior, not as a hard center generator.
- Keep visible or Godel evidence out of direct full-center generation.

Non-responsibilities:

- Does not model truncation and occlusion details.
- Does not own visible/full-center offset or missing extent state.
- Does not train weights in the current planning phase.
- Does not decide release readiness.

Required stop/go questions:

- Are complete-vehicle variables and factors explicitly defined?
- Are all factor inputs inference-safe?
- Does MAP/Viterbi inference use the fixed candidate bank?
- Is the current behavior explainable without adding ad hoc hard thresholds?
- Has factor prior audit passed before any calibration proposal?

## Agent 2: PartialVisibilityAgent

Scope: truncation, occlusion, visible/full-center mismatch, and missing extent modeling.

Responsibilities:

- Own partial visibility modeling after the complete-vehicle mainline is stable.
- Explicitly model that visible center is not equal to full vehicle center.
- Treat visible support only as:
  - factor
  - veto
  - uncertainty signal
- Define partial visibility variables:
  - `visibility state`
  - `missing extent state`
  - `visible/full-center offset`
- Design partial-visibility factors:
  - visibility factor
  - missing extent factor
  - visible/full-center offset factor
  - visibility uncertainty factor
- Audit truncation and occlusion cases separately from complete-vehicle cases.
- Prevent partial-visibility heuristics from destabilizing the complete-vehicle mainline.

Non-responsibilities:

- Does not select the complete-vehicle mainline candidate.
- Does not directly generate final full-center boxes from visible support.
- Does not enter candidate selection before the complete-vehicle mainline is stable.
- Does not train rankers or calibrate global weights.

Required stop/go questions:

- Is visible evidence being used only as factor, veto, or uncertainty?
- Are partial visibility and missing extent states separate from full-vehicle state?
- Does the design avoid treating visible center as full vehicle center?
- Is the branch gated behind a stable complete-vehicle mainline?

## Agent 3: AuditReleaseAgent

Scope: boundary audit, candidate-pool consistency, visualization audit, grouped metrics, and regression testing.

Responsibilities:

- Verify candidate bank hash and candidate-pool consistency.
- Enforce inference/eval field separation.
- Reject inference outputs containing eval-only fields such as:
  - `gt_*`
  - `oracle_*`
  - `candidate_iou`
  - `candidate_center_err_px`
  - `rot_iou`
  - `center_err_px`
  - `range_err_px`
  - `condition_type`
  - `truncation_degree`
  - `occlusion_degree`
  - `final_*`
- Reject reports that only show oracle coverage without selected-prediction behavior.
- Maintain required release artifacts:
  - `run_manifest`
  - `boundary_check_report`
  - `audit_report`
  - `release_decision`
- Audit normal regressions, hard-case behavior, center-error tails, IoU=0 rows, and grouped failure modes.
- Decide whether an experiment remains diagnostic, can proceed to calibration, can enter prototype selector, or must stop.

Non-responsibilities:

- Does not score candidates.
- Does not tune weights.
- Does not choose factor priors.
- Does not implement model changes.

Required stop/go questions:

- Did candidate bank hash remain unchanged?
- Are inference and eval fields separated?
- Does the report include selected-prediction behavior, not only oracle coverage?
- Are regressions visible by group?
- Is there a clear release decision?
- If audit fails, no artifact is allowed into the mainline.

## Collaboration Contract

StateGraphAgent proposes the complete-vehicle factor graph and MAP/Viterbi inference. PartialVisibilityAgent proposes partial visibility extensions only after the complete-vehicle path is stable. AuditReleaseAgent is the release gate and does not score or tune.

Default sequence:

1. StateGraphAgent defines or updates model specification.
2. AuditReleaseAgent checks boundary and factor prior audit readiness.
3. StateGraphAgent runs fixed-prior diagnostic prototypes only after specification is stable.
4. AuditReleaseAgent validates fixed-prior outputs.
5. StateGraphAgent may propose track-block OOF calibration only after factor prior audit passes.
6. PartialVisibilityAgent starts truncation/occlusion branch after complete-vehicle selector behavior is stable.
7. AuditReleaseAgent decides whether hybrid integration can proceed.

Release rule:

No model, factor, calibration, or selector change enters the GM17 or broader optical-to-SAR mainline until AuditReleaseAgent accepts the boundary report, selected-prediction audit, grouped regression audit, and release decision.
