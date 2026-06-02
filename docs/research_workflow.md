# Research Workflow

This document defines the current research workflow for optical-to-SAR vehicle localization and candidate selection. It is a research governance document, not an implementation plan for product engineering.

## Current Allowed Work

The current allowed work is Phase3 factor prior audit execution. This means reviewing factor origins, leakage classes, transforms, missing-value policies, correlated factors, branch scope, and patch-dependency risk.

The current work does not authorize algorithm changes, experiments, training, candidate-bank changes, OOF calibration, or GM17 mainline replacement.

Phase3 audit execution remains an audit activity. It is not calibration, implementation, or a new performance experiment, and it must not produce learned weights or new performance conclusions.

## Phase Route

### Phase 1: Long-Term Research Structure

Define long-term agents, roadmap, fixed candidate-bank boundary, and research governance. Status: complete.

### Phase 2: Complete-Vehicle Model Specification

Define complete-vehicle variables, source families, factor graph structure, final_action semantics, and MAP/Viterbi-style inference over fixed candidates. Status: specification prepared and reviewed with conditions.

### Phase 3: Factor Prior Audit

Audit every factor before calibration. Required coverage includes field origin, leakage class, join stage, monotonicity, valid range, transforms, clipping, missing-value policy, correlated factors, double-counting risk, branch scope, allowed phase, diagnostic-only flags, and patch-dependency risk.

Current status: allowed to proceed as audit execution.

Phase3 audit execution should produce audit decisions and risk classifications only. It should not create learned weights, selector replacements, or new performance claims.

### Phase 4: Fixed-Prior Revalidation

Revalidate a fixed-prior factor graph after Phase3 audit passes. This phase requires:

- Phase3 factor prior audit PASS;
- inference/evaluation separation PASS;
- candidate bank unchanged;
- factor transform and missing-value policies documented;
- double-counting and patch-dependency controls accepted;
- AuditReleaseAgent approval to run fixed-prior revalidation.

Phase4 is not authorized by the current document alone.

### Phase 5: Track-Block OOF Calibration

Calibrate factor weights only after fixed-prior behavior and factor audit controls are accepted. Entry conditions include:

- Phase2 model spec accepted;
- Phase3 factor prior audit accepted;
- Phase4 fixed-prior revalidation accepted;
- track-block split policy defined;
- leakage audit accepted;
- patch-dependency controls accepted;
- partial visibility factors isolated from complete-vehicle selection;
- AuditReleaseAgent release_decision allows calibration.

Current status: BLOCKED.

### Phase 6: Complete-Vehicle Selector Prototype

Only after Phase5 approval, test whether a complete-vehicle factor graph can become a selector candidate. This phase must include selected-prediction audit, normal-regression audit, hard-case audit, boundary report, and release_decision.

Current status: BLOCKED.

### Phase 7: Partial Visibility Branch

Model truncation, occlusion, missing extent, and visible/full-center offset after the complete-vehicle mainline is stable. Visible support remains factor, veto, or uncertainty evidence only. It cannot generate a full center.

Current status: BLOCKED until the complete-vehicle branch is stable and audited.

### Phase 8: Hybrid Integration

Integrate complete-vehicle and partial-visibility branches only after both are independently auditable. This phase requires full-scene audit, regression analysis, and AuditReleaseAgent acceptance.

Current status: BLOCKED.

## Current Prohibitions

- OOF calibration.
- GM17 mainline replacement.
- Ranker training.
- CRF training.
- New performance experiments.
- Candidate bank changes.
- Visible support as full-center generation.

## Minimal Next Action

Execute the Phase3 factor prior audit using the registry, field dictionary, and dependency audit. The goal is to decide which factors are inference-safe, which remain diagnostic-only, and which risks block Phase4 or Phase5.
