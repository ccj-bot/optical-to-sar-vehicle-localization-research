# GM17 Dual-Bottleneck Research Synthesis

Date: 2026-06-29

Status: long-form research synthesis only.

This document does not authorize experiments, model training, OOF calibration, candidate-bank modification, active selector changes, generated-proposal integration, threshold tuning, commit, push, or merge. It synthesizes the current GM17 fixed-bank diagnosis and defines diagnostic-only Phase4-extension research directions before any formal Phase5 decision.

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`. Any future factor described here is diagnostic-only unless it receives a separate audit for field origin, leakage class, double-counting controls, missing-value policy, and release approval.

## 1. Executive Position

The current GM17 evidence should be read as a dual-bottleneck diagnosis:

1. The fixed A001 bank has strong usable/coarse coverage under the current post-inference axis-aligned proxy audit, so the bank is not simply empty or grossly missing most targets.
2. High-IoU precision is weak. The bank contains many plausible coarse candidates but very few near-exact candidates under the same axis-aligned proxy.
3. Selection is also weak. Existing fixed-bank scoring frequently ranks legacy temporal/base candidates above better candidates already present deeper in A001.
4. Therefore the current bottleneck is not "candidate bank versus selector" as a single either/or problem. It is candidate precision plus structured selection.
5. The next safe research step is a Phase4-extension diagnostic pipeline that separates candidate precision diagnostics from structured factor-selection diagnostics. It must not become an active selector or formal Phase5 calibration.

The old story, "A001 has enough coverage, so the remaining problem is just selection," is incomplete. It remains true at coarse coverage levels, but it hides the high-precision sparsity of the bank and overstates what axis-aligned proxy IoU can prove. The better story is:

```text
optical prior gives a useful coarse shell
    -> A001 contains many coarse candidate states
    -> near-exact candidate precision is rare
    -> existing fixed selection over-ranks structured artifacts
    -> diagnostic factors must separate precision, selection, and leakage
```

## 2. Boundary And Evidence Rules

This synthesis uses completed audit results as background only. It does not create a new result.

Allowed background interpretation:

- A001 is a fixed GM_RM017 candidate menu for the current Phase4 work.
- C3/C4 and related factor-graph outputs are fixed-bank selection-layer diagnostics.
- A019/A021 and IoU/center-error fields are post-inference audit fields.
- `axis_aligned_proxy_iou` is an audit-only AABB-style proxy. It is not rotated IoU.
- `axis_aligned_proxy_iou` cannot support heading, vehicle orientation, or SAR long-axis conclusions.

Blocked interpretation:

- Do not claim that the full optical-to-SAR migration problem is solved.
- Do not claim that A001 proves rotated OBB orientation coverage.
- Do not use eval-only fields as inference inputs.
- Do not treat future diagnostic factors as active selector rules.
- Do not treat this synthesis as OOF calibration approval.
- Do not modify the candidate bank or GM17 mainline selector.

## 3. Audit Background: Coarse Coverage Versus Precision

The following values are post-inference audit background only. They are not new experiments and must not be used as active inference inputs:

| audit item | value | interpretation boundary |
|---|---:|---|
| coverage@0.5 | 203 / 205 = 99.02% | Strong coarse/usable coverage under axis-aligned proxy audit. |
| coverage@0.75 | 140 / 205 = 68.29% | Moderate useful overlap exists for many targets. |
| coverage@0.9 | 18 / 205 = 8.78% | Near-exact high-overlap candidates are uncommon. |
| coverage@0.95 | 1 / 205 = 0.49% | Very high precision is almost absent. |
| candidate-level purity@0.95 | 2 / 58251 = 0.0034% | Near-exact candidates are extremely sparse inside the bank. |
| only target with IoU > 0.95 candidates | `gm17supp_000181_000378_det3`, count = 2 | This is a post-inference audit fact only. |

All IoU values in this table refer to post-inference `axis_aligned_proxy_iou`. They are not rotated IoU. They cannot support heading, orientation, or rotated OBB conclusions.

This table supports two simultaneous statements:

- Fixed bank has strong usable/coarse coverage.
- High-IoU precision is weak.

Those statements are not contradictory. A candidate bank can be good enough to cover a target at coarse AABB overlap and still lack dense, precise, orientation-aware state hypotheses.

## 4. Why The Old Story Is Insufficient

The earlier selection-limited story was useful because it pushed the project away from premature candidate-bank expansion. It noticed that better candidates often exist inside A001 and that the active rank1 choice can be worse than another bank candidate.

That story is now insufficient for four reasons.

First, "coverage" was too broad a word. Coverage at 0.5 and 0.75 is strong, but coverage at 0.9 and 0.95 is weak. A coarse candidate may be enough to show that the optical-to-SAR shell reaches the right region, but it is not enough to claim high-precision localization.

Second, the audit metric is axis-aligned. It ignores candidate heading and therefore does not evaluate rotated OBB quality. It can diagnose center/size proximity under an AABB proxy, but it cannot validate SAR-derived orientation, vehicle long-axis support, or heading correctness.

Third, existing selection behavior still overuses structured artifacts. The minimal-factor v1 diagnostic showed that rank1 often stays on base candidates while best-proxy candidates are deeper in A001. That is a structured selection bottleneck, not just random noise.

Fourth, candidate precision and selection interact. If near-exact candidates are sparse, the selector must be much better at preserving and promoting rare good candidates. If selection is structured poorly, even a candidate bank with useful coverage will look worse than it should.

The revised story is therefore a dual-bottleneck story:

```text
candidate precision bottleneck:
    A001 reaches the target region but has sparse near-exact candidates.

structured selection bottleneck:
    existing fixed rules often fail to promote the best available candidate.
```

## 5. Candidate Precision Bottleneck

Candidate precision concerns what candidate states exist before selection.

The strong coarse coverage suggests that the optical-to-SAR prior and A001 generation history put many candidates in the right neighborhood. However, the weak high-IoU audit suggests that the current candidate lattice is not dense or structured enough around the exact vehicle state under the axis-aligned proxy. Because the proxy is not rotated IoU, the precision bottleneck may be even more complex once orientation and long-axis state are considered.

The immediate research question is not "should we expand the bank now?" That is blocked. The safe diagnostic question is:

```text
Which state dimensions explain the gap between coarse coverage and high-IoU precision?
```

Candidate precision diagnostics should inspect:

- center residuals in `cx/cy` and fan-polar `r/cross/az`;
- size and extent residuals through `w/h`;
- axis-aligned overlap sensitivity to center versus size;
- candidate-source families only as post-hoc explanations, not scoring inputs;
- heading/orientation capacity separately from `axis_aligned_proxy_iou`.

Any generated proposal, candidate refinement, or bank expansion remains out of scope. The current document only supports diagnostic decomposition of precision error.

## 6. Structured Selection Bottleneck

Structured selection concerns how existing candidates are ranked.

The fixed-bank diagnostics show that the best candidate is often present but not selected. The minimal-factor v1 diagnosis found:

- rank1 is frequently a legacy base candidate;
- best-proxy and best-center candidates often appear tens of ranks below rank1;
- temporal-zero/base-candidate artifacts can dominate selection;
- source/provenance explains failures post hoc but must not become an active scoring input.

Phase4C and the factor-graph wrapper showed that temporal and SAR-structure signals are complementary enough to justify factor ownership and graph-style representation. However, the wrapper is still a representation and diagnostic interface over the fixed A001 bank. It is not a new ranking search, not a proposal generator, and not proof that the final optical-to-SAR model is solved.

The safe structured-selection question is:

```text
Can diagnostic factor ownership explain why rare better candidates are under-ranked
without adding evidence, tuning weights, or using eval-only fields?
```

This shifts the work from table-rule chasing to controlled diagnosis of factor responsibilities.

## 7. Diagnostic Factor Directions

The factors below are research synthesis targets only. They are not active selector rules. Each must remain diagnostic-only unless separately audited.

### 7.1 `center_size_likelihood_candidate_refinement`

Purpose:

Diagnose whether high-IoU weakness is driven more by candidate center error, size/extent error, or their interaction.

Candidate role:

- candidate-level diagnostic factor;
- uses existing candidate geometry only;
- does not move candidates;
- does not create candidates;
- does not modify the bank.

Allowed diagnostic inputs after audit:

- `candidate_id`;
- `target_identity`;
- `sar_frame_num`;
- `cx`, `cy`;
- `w`, `h`;
- `r`, `cross`, `az`;
- approved frame/fan validity metadata if available.

Blocked inputs:

- `final_*`;
- `candidate_iou`;
- `axis_aligned_proxy_iou`;
- `rot_iou`;
- center-error fields;
- oracle ranks;
- A021 condition labels;
- panel review labels;
- `candidate_source` as a scoring input.

Interpretation:

This factor should not "refine" by moving a candidate. The word `refinement` here means diagnostic likelihood decomposition over existing candidate geometry. It asks whether a candidate's center and size look internally plausible and whether errors concentrate in center, size, or both. Any actual candidate generation or geometry adjustment would require a separate future route.

Relationship to existing factors:

- Extends `geometry_factor` by splitting center and size likelihood instead of treating geometry as one undifferentiated cost.
- Must not absorb `sar_structure_factor` evidence such as local contrast, shell support, or ambiguity.
- Must not use `optical_temporal_factor` deltas unless ownership is separately transferred.

### 7.2 `sar_aspect_sequence_factor`

Purpose:

Diagnose whether SAR-side aspect, extent, or long-axis consistency across a target sequence can explain better candidates already present in A001.

Candidate role:

- sequence-level diagnostic factor;
- compares existing candidate geometry across nearby frames;
- uses aspect/size patterns only after heading and width/height conventions are explicitly documented.

Allowed diagnostic inputs after audit:

- `target_identity`;
- `gm17_track_id`;
- `sar_frame_num`;
- `w`, `h`;
- `heading` as stored candidate axis metadata;
- `r`, `cross`, `az` for state continuity context.

Blocked interpretation:

- Do not infer vehicle heading from `axis_aligned_proxy_iou`.
- Do not claim A001 heading is SAR-derived orientation.
- Do not use this factor to prove rotated OBB quality.
- Do not treat scene-level fixed heading grids as physical orientation evidence.

Relationship to existing factors:

- It is adjacent to `transition_factor`, but it is not a general smoothness reward.
- It is adjacent to `geometry_factor`, but it emphasizes sequence-level aspect/extent consistency rather than per-candidate state validity.
- It must not double-count `sar_structure_factor` long-axis support unless support evidence is separately owned and audited.

### 7.3 `apparent_motion_consistency_factor`

Purpose:

Diagnose whether a candidate sequence has plausible apparent motion in SAR fan-polar state without letting temporal smoothness overrule SAR evidence.

Candidate role:

- edge/sequence diagnostic factor;
- compares existing candidates across adjacent or nearby frames;
- stays separate from optical prediction compatibility.

Allowed diagnostic inputs after audit:

- `target_identity`;
- `gm17_track_id`;
- `sar_frame_num`;
- candidate `r`, `cross`, `az`;
- candidate `cx`, `cy` only as coordinate context;
- candidate identity and row keys.

Blocked inputs:

- A019/A021 labels;
- center-error or IoU fields;
- selected-output path scores;
- Viterbi selected outputs as scoring inputs;
- any active use of `candidate_source`.

Relationship to existing factors:

- Refines the boundary between `transition_factor` and `optical_temporal_factor`.
- `optical_temporal_factor` compares a candidate to an optical-derived prediction.
- `apparent_motion_consistency_factor` compares candidate states to neighboring candidate states.
- These must not both reward the same hidden smoothness signal without a double-counting audit.

### 7.4 `keyframe_anchor_factor`

Purpose:

Diagnose whether a small number of reliable frames can act as sequence anchors for explaining candidate ranking failures, without using ground truth or human audit labels as inference.

Candidate role:

- diagnostic sequence anchor factor;
- identifies whether candidate confidence is locally stronger at some frames under inference-safe evidence;
- propagates no active decision unless separately approved.

Potential inference-safe or diagnostic-only evidence after audit:

- high-confidence geometry consistency within A001;
- SAR-structure support if support-vs-uncertainty ownership is separated;
- stable temporal compatibility if optical temporal remains soft;
- candidate-node consistency across frames.

Blocked anchor sources:

- A019 final annotations;
- A021 condition/truncation/occlusion labels;
- oracle candidate identity;
- manual panel review decisions;
- post-inference IoU;
- `axis_aligned_proxy_iou`;
- best-proxy or best-center identity.

Relationship to existing factors:

- It is not `transition_factor`; it diagnoses whether some frames should be trusted more as explanatory anchors.
- It is not `final_arbitration_factor`; it cannot copy B patch behavior.
- It is not a release decision or active track selector.

### 7.5 `cross_object_relation_factor`

Status: future Phase8 only.

This factor is intentionally out of scope for the current Phase4-extension diagnostic pipeline. It may eventually ask whether multi-object relations, shared road context, spacing, or scene-level constraints can help disambiguate SAR localization. It must not enter Phase4 diagnostics, formal Phase5 readiness, OOF calibration, or GM17 fixed-bank selector logic.

Reasons to hold until Phase8:

- It introduces cross-object coupling beyond the current single-target candidate graph.
- It risks leaking scene annotation structure.
- It creates new double-counting risks with temporal, transition, source, and keyframe factors.
- It requires a separate multi-object schema and leakage audit.

## 8. Relationship To Existing Factor Stack

The proposed diagnostic directions should be understood as refinements around the existing factor stack, not replacements.

| existing factor | current role | relationship to new diagnostics |
|---|---|---|
| `geometry_factor` | Candidate-state geometry ownership: center, size, heading metadata, fan-polar state. | `center_size_likelihood_candidate_refinement` decomposes geometry precision into center and size diagnostics; `sar_aspect_sequence_factor` adds sequence-level aspect consistency only after convention audit. |
| `sar_structure_factor` | SAR display/pseudocolor structure support over existing candidates. | New factors must not absorb SAR support, ambiguity, artifact, or contrast evidence unless ownership is transferred. Support-vs-uncertainty separation remains required. |
| `optical_temporal_factor` | Soft compatibility between existing candidate state and A005 optical-temporal prior. | `apparent_motion_consistency_factor` must stay separate: it compares candidate-to-candidate motion, not candidate-to-optical prediction. |
| `transition_factor` | Edge continuity across candidate states. | `apparent_motion_consistency_factor` can become a more explicit diagnostic form of motion continuity, but it cannot double-count optical temporal smoothness. |
| `final_arbitration_factor` | Blocked from active scoring because of patch-dependency risk. | `keyframe_anchor_factor` must not become final arbitration or copy B patch behavior. |
| partial-visibility factors | Phase7/future diagnostic-only. | Not activated here. Any missing-extent or visible-full-center logic remains outside complete-vehicle Phase4-extension scoring. |
| `cross_object_relation_factor` | Future relational factor. | Future Phase8 only. No current diagnostic or active role. |

## 9. Phase4-Extension Diagnostic Pipeline

This pipeline is the recommended safe route before any formal Phase5 reconsideration. It is explicitly diagnostic-only.

### Step A: Freeze boundary and manifests

Required checks:

- confirm the work uses the fixed A001 GM_RM017 candidate bank;
- confirm candidate IDs and row counts;
- confirm A019/A021 are unavailable until post-inference audit;
- confirm no generated proposal is injected;
- confirm no candidate geometry is moved or rewritten.

Output:

- a diagnostic manifest;
- allowlist/denylist for fields;
- no experiment result.

### Step B: Precision decomposition audit

Question:

```text
When high-IoU precision fails, is the dominant gap center, size, aspect, fan-polar state, heading capacity, or proxy-metric limitation?
```

Allowed output:

- post-inference diagnostic tables;
- axis-aligned proxy caveat;
- no rotated-IoU or orientation conclusion unless a rotated metric and annotation protocol are separately approved.

### Step C: Structured selection decomposition audit

Question:

```text
When a better candidate exists, which factor ownership failure explains why it is under-ranked?
```

Diagnostic branches:

- geometry-only;
- center-size likelihood view;
- optical-temporal soft-prior view;
- apparent motion consistency view;
- SAR aspect sequence view;
- keyframe anchor explanation view.

These branches should be compared as explanations, not activated as a new selector.

### Step D: Leakage and double-counting audit

Required controls:

- no `final_*`, IoU, center-error, oracle, A021 condition, truncation, or occlusion fields before output exists;
- no `candidate_source` scoring unless a future source-factor audit explicitly allows it;
- no use of `axis_aligned_proxy_iou` as a training target or inference feature;
- separate temporal-prior compatibility from transition/motion consistency;
- separate geometry coordinate plausibility from SAR structure support;
- separate SAR support from uncertainty/patch behavior.

### Step E: Stop/go review before formal Phase5

The pipeline can produce a research recommendation, but it cannot self-approve formal Phase5. Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION` unless all stop/go gates below pass and AuditReleaseAgent or an equivalent release review accepts them.

## 10. Stop / Go Gates Before Formal Phase5

### STOP

Stop immediately if any of the following occurs:

- candidate bank is modified;
- generated proposals are inserted into C3/C4 or GM17 mainline selection;
- A019/A021 fields enter inference;
- `axis_aligned_proxy_iou` is treated as rotated IoU or heading evidence;
- new factor scores are used as active selector rules;
- thresholds or weights are tuned from GT, IoU, center error, or condition groups;
- C6/C7 or v3 table-rule search is restarted as the mainline;
- OOF calibration is started;
- training is started;
- commit, push, merge, or staging is attempted without explicit approval.

### HOLD

Hold, pending separate audit:

- any active `center_size_likelihood_candidate_refinement` scoring;
- any sequence-level `sar_aspect_sequence_factor` scoring;
- any active `apparent_motion_consistency_factor`;
- any `keyframe_anchor_factor` propagation;
- any source-family scoring;
- any raw SAR or rotated OBB proposal generation;
- any all-scene extension beyond GM_RM017;
- any partial-visibility factor activation.

### GO

Allowed next work, if separately requested:

- documentation-only diagnostic design;
- field allowlist/denylist refinement;
- post-inference precision decomposition using completed outputs;
- post-inference structured-selection explanation using completed outputs;
- visualization of audit-only failure cases with explicit metric caveats;
- factor ownership diagrams;
- leakage and double-counting checklists.

### Formal Phase5 Gate

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION` until:

1. factor ownership for geometry, SAR structure, optical temporal, transition/motion, and keyframe anchor diagnostics is accepted;
2. field leakage classes and join stages are audited for every diagnostic output;
3. high-IoU precision claims are separated from coarse coverage claims;
4. axis-aligned proxy metrics are separated from rotated OBB/orientation claims;
5. double-counting controls are written and accepted;
6. patch-dependency risks remain isolated from physical model claims;
7. a release review explicitly authorizes the next phase.

## 11. Leakage Controls

The most important leakage rule is temporal ordering:

```text
inference-facing candidate/factor outputs first
post-inference A019/A021 joins second
audit metrics and failure labels last
```

Forbidden inference inputs:

- A019 `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg`;
- `candidate_iou`;
- `axis_aligned_proxy_iou`;
- `rot_iou`;
- center-error fields;
- best-proxy or best-center identity;
- oracle ranks or oracle labels;
- A021 condition, truncation, and occlusion fields;
- manual review labels;
- selected outputs from another variant;
- B patch outputs or final arbitration behavior;
- post-inference source/provenance conclusions.

Permitted after-output audit use:

- compute coverage and precision diagnostics;
- group failures by condition labels;
- explain source/provenance patterns;
- compare selected candidates to best available candidates;
- identify audit cases for human review.

Any future script or table should include a manifest field that states whether each column is `inference_safe`, `diagnostic_inference_safe`, `eval_only_blocked`, or `future_inference_required`.

## 12. Double-Counting Controls

The dual-bottleneck synthesis makes double-counting more dangerous because the same failure can be explained by multiple correlated factors. Controls must be explicit:

| risk pair | double-counting risk | control |
|---|---|---|
| `geometry_factor` vs `center_size_likelihood_candidate_refinement` | Center/size plausibility counted twice. | Treat center-size likelihood as a decomposition view of geometry unless a separate active factor is approved. |
| `geometry_factor` vs `sar_structure_factor` | Shell or escape support can mix geometry and SAR evidence. | Geometry uses explicit candidate state only; SAR structure owns image support. |
| `sar_structure_factor` vs uncertainty/patch behavior | Ambiguity and artifact evidence can be penalized twice or copy B patch logic. | Split support from uncertainty; keep patch behavior diagnostic-only. |
| `optical_temporal_factor` vs `apparent_motion_consistency_factor` | Both can reward smoothness. | Optical temporal compares candidate to prior; motion compares candidate to neighboring candidates. |
| `transition_factor` vs `sar_aspect_sequence_factor` | Sequence consistency can be counted as both motion and aspect stability. | Aspect sequence must own size/aspect/axis pattern only; transition owns state continuity. |
| `keyframe_anchor_factor` vs final arbitration | Anchor selection can become a hidden release decision. | Anchors remain explanation-only; no candidate override or release decision. |
| source/provenance vs any factor | Candidate family can proxy hidden geometry, direction, or SAR support. | Source remains post-hoc unless a source-factor audit explicitly approves active use. |
| `cross_object_relation_factor` vs sequence factors | Scene-level relations can duplicate temporal/track context. | Future Phase8 only. |

## 13. Research Claim Template

Safe claim:

```text
GM17 fixed-bank Phase4 diagnostics indicate strong coarse candidate coverage but weak high-IoU precision under a post-inference axis-aligned proxy metric. Existing fixed selection also under-ranks better candidates already present in A001. The current diagnosis is therefore a dual bottleneck: candidate precision plus structured selection. Proposed center-size, aspect-sequence, apparent-motion, and keyframe-anchor factors are diagnostic-only Phase4-extension hypotheses pending leakage and double-counting audits. Formal Phase5 remains BLOCKED_FOR_OOF_CALIBRATION.
```

Unsafe claim:

```text
A001 solves optical-to-SAR localization, and new factors can now be activated as a selector for Phase5.
```

Unsafe because it overstates coarse proxy coverage, ignores high-IoU sparsity, treats audit metrics as inference evidence, and bypasses OOF/calibration blockers.

## 14. Recommended Next Documentation Unit

The next documentation unit, if requested, should be one of:

1. `gm17_phase4_extension_precision_decomposition_spec.md`
2. `gm17_phase4_extension_structured_selection_diagnostic_spec.md`
3. `gm17_phase4_extension_factor_leakage_double_counting_matrix.md`

Each should remain documentation-only unless the user explicitly requests an audited post-inference diagnostic run. None should modify A001, C3/C4, the GM17 mainline selector, or formal Phase5 status.

## 15. Boundary Statement

This synthesis is documentation-only.

- No experiment was run.
- No training was run.
- No OOF calibration was started or approved.
- No candidate bank was modified.
- No generated proposals were created or injected.
- No GM17 mainline selector was modified.
- No eval-only field was promoted into inference.
- No `axis_aligned_proxy_iou` value was treated as rotated IoU.
- No heading or orientation conclusion was drawn from axis-aligned proxy metrics.
- No `cross_object_relation_factor` was activated; it remains future Phase8 only.
- No commit, push, merge, or staging was performed.
