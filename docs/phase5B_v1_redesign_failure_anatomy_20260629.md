# Phase5B-v1 Redesign And Failure Anatomy

Date: 2026-06-29

## 1. Purpose

This document is based on the frozen Phase5B-v0 proposal generation and the Phase5C-v0 post-hoc diagnostic audit.

Its purpose is not to tune Phase5B-v0 parameters. Its purpose is to explain why v0 is not sufficient, identify the likely failure anatomy, and define a physically interpretable Phase5B-v1 redesign direction.

This document is documentation-only. It adds no code, runs no experiment, generates no proposal, rejoins no A019/A021 table beyond citing existing Phase5C-v0 results, recomputes no GT/oracle metric, recomputes no IoU or center error, performs no C3/C4 comparison beyond citing the existing Phase5C summary, tunes no threshold, trains no model, performs no calibration, and does not push.

## 2. Phase5B-v0 Result Summary

Phase5C-v0 reported:

- Phase5B ABC center error mean / median = `17.3953 / 13.8270`;
- Phase5B ABC IoU mean / median = `0.6824 / 0.7214`;
- A001 center error mean / median = `7.5406 / 5.6366`;
- A001 IoU mean / median = `0.7846 / 0.7943`;
- Phase5B better count = `50`;
- A001 better count = `167`;
- `prior_dominant` = `192`;
- `energy_center_helpful` = `7`;
- `component_extent_helpful` = `1`;
- `A001_still_stronger` = `130`;
- `phase5B_adds_new_hypothesis` = `4`.

Phase5B-v0 is not a complete failure. It established a clean, frozen, leakage-controlled proposal space and made A/B/C route behavior diagnosable. It also found a small number of cases where Phase5B-v0 may add hypotheses beyond A001.

However, v0 is not strong enough to enter Phase5D globally. The problem is not proposal count. The problem is the structure of the model terms: v0 mostly samples around a coarse A005 proxy shell, while its SAR image routes do not yet provide reliable center or extent evidence.

## 3. Main Diagnosis: v0 Is Prior-Dominant

The main Phase5C-v0 diagnosis is that v0 is prior-dominant.

`A_only` and `A+B+C` are close:

- `A_only` mean / median center error = `17.8661 / 13.8919`;
- `A+B+C` mean / median center error = `17.3953 / 13.8270`;
- `A_only` mean / median IoU = `0.6811 / 0.7214`;
- `A+B+C` mean / median IoU = `0.6824 / 0.7214`.

B/C contributions are weak at the dataset level:

- `energy_center_helpful` = `7`;
- `component_extent_helpful` = `1`;
- `prior_dominant` = `192`.

This means Route A has value as a coarse optical/temporal prior shell. A005 is not useless: it often provides a reasonable region around the target. But Route A is not a precision localization model. Its center precision is much weaker than the A001 oracle ceiling.

Therefore, the v1 problem should not be framed as "tune B/C until v0 wins." The v1 problem should be: replace isotropic x/y shell sampling with geometry-aware SAR state hypotheses, then use SAR observations as support factors.

## 4. Why Route B Failed As A Proposal Generator

Route B failed as an independent proposal generator because a local energy peak is not equivalent to a vehicle center.

Phase5C-v0 showed `B_only` center error mean / median = `75.9797 / 65.0326`, and `B_only` IoU mean / median = `0.2272 / 0.2555`. This is far too weak to act as an independent box generator.

The physical issue is clear. A SAR bright point can be:

- a corner-like scatterer on only one part of the vehicle;
- clutter;
- speckle;
- shadow boundary;
- partial vehicle support;
- display encoding artifact;
- a strong return from an object that is not the target.

Treating that peak as a center proposal is too strong. It asks one local observation to solve the state-estimation problem alone.

Phase5B-v1 should convert Route B into a SAR observation-support factor. It should score geometry-aware hypotheses using evidence such as inside contrast support, peak-to-shell consistency, local background contrast, and local support asymmetry. It should not directly generate a final center box.

## 5. Why Route C Failed As Extent Generator

Route C failed as a direct extent generator because a connected-component bounding box is not a complete vehicle box.

Phase5C-v0 showed `C_only` center error mean / median = `59.7390 / 38.6041`, and `C_only` IoU mean / median = `0.2777 / 0.3019`. Only `1` target was labeled `component_extent_helpful`.

The physical issue is also clear. SAR visible support can be fragmented, partial, merged with clutter, cut by the fan boundary, or dominated by only a small scatterer. A component box may represent visible support, but it does not necessarily represent full body extent.

Phase5B-v1 should convert Route C into visible-support evidence. It should output support scores, fragmentation flags, boundary-touching flags, and clutter-risk indicators. It should not treat the component bounding box as the full vehicle extent. A later support-aware extent model can use this evidence while preserving uncertainty.

## 6. Why A001 Is Still Stronger

A001 remains clearly stronger than Phase5B-v0:

- A001 center error mean / median = `7.5406 / 5.6366`;
- Phase5B ABC center error mean / median = `17.3953 / 13.8270`;
- A001 IoU mean / median = `0.7846 / 0.7943`;
- Phase5B ABC IoU mean / median = `0.6824 / 0.7214`;
- `A001_still_stronger` = `130`.

This does not mean the project should return to A001 row selection. It means A001 candidate generation likely contains stronger implicit geometry and candidate-expansion priors than the current Phase5B-v0 shell-grid approximation.

A001 may be stronger because of center offset coverage, range/cross correction, extent scale diversity, candidate expansion states, or source diversity. But A001 `candidate_id` itself is not the model target and should not be copied into Phase5B-v1 as a direct answer.

A useful next diagnostic is an A001-vs-v0 failure anatomy audit. It should analyze, post-hoc only:

- A001 oracle best offset relative to A005 predicted center;
- A001 oracle best offset relative to Phase5B Route A best offset;
- `delta_r`, `delta_cross`, and `delta_az` distributions where available;
- `best_iou_candidate_source_or_type`;
- `candidate_expansion_state` and `candidate_expansion_reason`;
- whether A001's advantage comes mainly from range shift, cross shift, scale, or candidate-source diversity.

This audit should be used for understanding, not for directly tuning v0 thresholds.

## 7. What The 4 New-Hypothesis Cases Mean

Phase5C-v0 found `phase5B_adds_new_hypothesis = 4`.

This means Phase5B-v0 is not empty of new information. It can sometimes produce hypotheses outside the fixed A001 neighborhood that look useful under post-hoc evaluation.

But four cases are not enough to justify global Phase5D. They are enough to justify manual inspection.

Manual review should answer:

- Are these true SAR-supported new states?
- Are they artifacts of the A001-neighborhood criterion?
- Do they come from Route A shell offset, Route B energy, or Route C support?
- Do they correlate with edge, truncation, clutter, or partial visibility?
- Do they suggest a hypothesis mechanism that v1 should preserve?

The current decision is: manually inspect the four cases before deciding any proposal fusion strategy.

## 8. Phase5B-v1 Design Principles

### 1. Do Not Tune v0 Thresholds

Phase5B-v1 should not be an Otsu/percentile retune, top-k retune, crop enlargement, or denser x/y grid. Those changes would be post-hoc optimization around v0's weakness rather than a model redesign.

### 2. Geometry First

SAR uncertainty should not be modeled primarily as isotropic image x/y grid offsets. It should be modeled in range, azimuth, and cross directions. v1 should use A005 `pred_r`, `pred_az`, `pred_cross`, and scene geometry to produce physically meaningful uncertainty.

### 3. Observation As Support, Not Box Generator

Energy and component evidence should not directly emit final proposal boxes. They should support or weaken geometry-aware hypotheses.

### 4. Multi-Hypothesis With Physical Semantics

v1 should preserve multiple hypotheses, but each hypothesis should have range, cross, extent, and uncertainty semantics. The goal is not arbitrary dense sampling.

### 5. Evaluation Separation

A019, A021, and A001 oracle outputs remain post-hoc only. A v1 config must be frozen before generation. Phase5C-v1 must not feed back into the same generation run.

## 9. Proposed Phase5B-v1 Model

The v1 state should be represented as:

```text
s = {
  cx, cy,
  w, h,
  r, az, cross,
  range_uncertainty,
  cross_uncertainty,
  visible_support_state,
  observation_support_scores,
  hypothesis_source
}
```

The proposed v1 generation chain is:

```text
optical/temporal proxy
  -> geometry-aware range/cross shell
  -> range/radial support proposal family
  -> SAR observation support scoring
  -> frozen proposal bank
  -> Phase5C-v1 audit
```

v1 is not simply "add Route D." Route D should become one of the physical main routes, while B/C become support evidence. Route A should change from image x/y grid sampling into geometry-aware shell discretization.

## 10. Candidate v1 Routes

### Route A1: Geometry-Aware Shell Discretization

Route A1 should use `pred_r`, `pred_cross`, and `pred_az` to generate anisotropic hypotheses. It should separate range uncertainty and cross uncertainty instead of using a simple 3x3 x/y grid as the primary route.

### Route D1: Radial / Range-Profile Support

Route D1 should search for SAR support along the range or radial direction within the shell. Its goal is to explain center/range shift, not to chase a single bright point.

### Observation B1: Local Contrast Support Factor

B1 should not independently generate centers. It should score A1/D1 hypotheses using local contrast support, peak-to-hypothesis consistency, and background contrast.

### Observation C1: Visible Support Consistency Factor

C1 should not independently generate bounding boxes. It should score A1/D1 hypotheses by support consistency and report fragmentation, boundary, and clutter flags.

### Optional: A001-Anatomy-Informed Diagnostic Only

The v1 design can use A001-vs-v0 failure anatomy to understand missing geometry freedom. It must not copy A001 candidates or candidate IDs as model outputs.

## 11. Required Preconditions Before v1 Implementation

Before implementing Phase5B-v1, the following must be confirmed:

- fan/range coordinate convention;
- relationship between `pred_r`, `pred_az`, `pred_cross`, and image x/y;
- valid support policy;
- Route D input source;
- raw SAR or display SAR source decision;
- whether grayscale display PNG is acceptable for v1 or only diagnostic;
- v1 target set;
- frozen v1 config;
- leakage audit;
- output schema update.

If these are not confirmed, v1 implementation should remain on hold.

## 12. Recommended Next Step

The next step should not be writing a v1 generator immediately.

Recommended next step:

```text
Phase5B-v1 pre-design audit:
A001-vs-v0 failure anatomy + range/cross convention readiness
```

The pre-design audit should output:

- A001 oracle best offset distribution relative to A005 prediction;
- v0 A-only best offset distribution;
- A001 advantage decomposition;
- candidate source and expansion-state analysis;
- manual list of the 4 `phase5B_adds_new_hypothesis` cases;
- Route D readiness checklist;
- v1 config design implications.

This keeps the research path in model redesign rather than threshold tuning.

## 13. Decision

- Phase5D: HOLD globally.
- Phase5B-v1: OPEN.
- v0 threshold tuning: REJECT.
- Direct C3/C4 integration: REJECT.
- A001 candidate copying: REJECT.
- Geometry-aware shell redesign: GO.
- Route D readiness audit: GO.
- B/C as observation factors: GO.
- Manual inspection of the 4 new-hypothesis cases: GO.

## 14. Boundary Statement

- Documentation-only.
- No code.
- No experiment.
- No proposal generated.
- No A019/A021 join.
- No GT/oracle metric recomputation.
- No IoU or center error recomputation.
- No C3/C4 comparison.
- No threshold tuning.
- No training.
- No calibration.
- No push.
- File not staged or committed unless explicitly approved.
