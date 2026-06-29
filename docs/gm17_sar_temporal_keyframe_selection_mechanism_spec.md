# GM17 SAR Temporal Keyframe Selection Mechanism Spec

Date: 2026-06-29

Status: diagnostic-only mechanism draft

This document designs a unified diagnostic mechanism for SAR aspect sequence evidence, keyframe local soft anchors, apparent motion consistency, and structured selection hypotheses under the GM17 dual-bottleneck framework.

It is not an active selector. It does not modify the GM17 mainline selector. It does not modify A001 or any candidate bank. It does not run an experiment, train a model, perform OOF calibration, or produce a new mainline performance conclusion.

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.

## 1. Purpose

The dual bottleneck diagnosis says that GM17 has:

- a candidate precision bottleneck;
- a structured selection bottleneck.

The center-size likelihood mechanism addresses local candidate precision. This document addresses the structured selection side: when candidate precision signals exist, how could SAR temporal structure, keyframe confidence, local soft anchors, and apparent motion consistency interact without becoming temporal smoothing or an active selector?

The diagnostic question is:

Can inference-safe SAR structure and local sequence context explain why some frozen candidates should be trusted more than others, especially near keyframes, without using GT, IoU, oracle labels, center error, A019 final boxes, A021 condition labels, or panel review outcomes during scoring?

## 2. Why SAR Aspect Sequence Is Not Ordinary Temporal Smoothing

Ordinary temporal smoothing assumes neighboring frames should have similar positions or scores. That is too weak and too risky for GM17.

SAR aspect sequence is different:

- it focuses on how SAR scattering structure changes with viewing / azimuth context;
- it treats time as an ordered observation sequence, not as a guarantee of smooth geometry;
- it asks whether candidate-local descriptors evolve coherently under left / center / right aspect states;
- it does not average boxes;
- it does not force rank continuity;
- it does not hard-propagate labels from one frame to another;
- it does not assume true physical velocity can be recovered from frame-to-frame displacement.

The mechanism should capture structured evidence such as:

```text
candidate looks locally precise in frame t
neighboring frames show compatible SAR aspect descriptors
apparent displacement is plausible under local coordinate context
therefore frame t can act as a soft local anchor for diagnostic explanation
```

This is not:

```text
rank1 in frame t is correct
therefore neighbors must follow it
```

## 3. Left / Center / Right SAR Aspect States

The left / center / right states are diagnostic aspect bins. They are not GT labels and not heading correctness labels.

They may be derived only from inference-safe viewing context, such as optical-to-SAR fan geometry, SAR frame metadata, pre-eval azimuth ordering, or candidate-local coordinate conventions. If the state origin cannot be proven inference-safe, the field must be held out of scoring.

### 3.1 Left Aspect

Possible SAR structure pattern:

- stronger scatter energy on one lateral side of the candidate patch;
- shifted scatter centroid relative to candidate center;
- asymmetric edge support;
- weaker mirror symmetry;
- local background contrast stronger on the exposed side;
- ambiguous center if the visible scattering peak sits off-center.

Diagnostic implication:

Left-aspect frames may be center-limited if the SAR peak is not at the vehicle center. A candidate with good local energy but biased center support may need center-size likelihood and aspect-aware interpretation.

### 3.2 Center Aspect

Possible SAR structure pattern:

- more balanced left / right energy;
- stronger center dominance;
- higher mirror symmetry;
- compact scatter support;
- clearer inside / outside contrast around the candidate extent;
- fewer competing side peaks.

Diagnostic implication:

Center-aspect frames may be stronger keyframe candidates if their confidence is derived from inference-safe agreement across SAR structure, center-size likelihood, and frozen score margin. This must still be validated only post hoc.

### 3.3 Right Aspect

Possible SAR structure pattern:

- asymmetric energy opposite to left aspect;
- scatter centroid shift in the opposite lateral direction;
- boundary support changes relative to candidate width;
- mirror-symmetry reduction similar to left aspect but reversed;
- different peak count or compactness due to viewing geometry.

Diagnostic implication:

Right-aspect frames should not simply be smoothed with left-aspect frames. The descriptor sequence should expect structured change, not identical appearance.

### 3.4 Unknown / Mixed Aspect

Possible SAR structure pattern:

- weak or diffuse energy;
- multiple peaks;
- unclear left / right split;
- missing crop support;
- edge-of-frame ambiguity;
- local clutter.

Diagnostic implication:

Unknown aspect should reduce confidence and prevent hard anchoring. It may trigger manual review or HOLD, not active selection.

## 4. Candidate-Local SAR Descriptor Definition

For a frozen candidate `i` at frame `t`, define a candidate-local SAR patch and descriptor vector:

```text
z_t(i) = [
  E_left,
  E_center,
  E_right,
  lr_asymmetry,
  center_dominance,
  mirror_symmetry,
  scatter_centroid_dx,
  scatter_centroid_dy,
  scatter_compactness,
  peak_count,
  local_background_contrast
]
```

These descriptors are computed from SAR evidence and frozen candidate geometry only. They must not use GT boxes, A019 final boxes, A021 labels, IoU, oracle labels, center error, high-IoU bins, or panel review.

### 4.1 Energy Partition

Partition the candidate-local patch into left, center, and right regions under a declared local coordinate convention:

```text
E_left   = normalized energy in left subregion
E_center = normalized energy in center subregion
E_right  = normalized energy in right subregion
```

The coordinate convention must be fixed before audit labels are joined. If the patch orientation convention is uncertain, descriptor use must be marked `HOLD_FOR_CONVENTION_AUDIT`.

### 4.2 Lateral Asymmetry

```text
lr_asymmetry = (E_right - E_left) / (E_right + E_left + epsilon)
```

Interpretation:

- near zero may indicate balanced aspect or weak signal;
- positive / negative values indicate lateral imbalance under the declared convention;
- sign cannot be interpreted as vehicle heading correctness.

### 4.3 Center Dominance

```text
center_dominance = E_center / (E_left + E_center + E_right + epsilon)
```

Interpretation:

- high values may indicate compact center support;
- low values may indicate side-biased scattering, clutter, or wrong extent;
- it is a candidate-local descriptor, not a correctness label.

### 4.4 Mirror Symmetry

```text
mirror_symmetry = 1 - normalized_distance(left_profile, mirror(right_profile))
```

Interpretation:

- high symmetry may support center-aspect or balanced structure;
- low symmetry may reflect left / right aspect, clutter, truncation, or incorrect candidate geometry;
- A021 truncation / occlusion labels may explain it only after post-inference audit.

### 4.5 Scatter Centroid Offset

```text
scatter_centroid_dx = centroid_x(SAR energy inside candidate patch) - candidate_cx
scatter_centroid_dy = centroid_y(SAR energy inside candidate patch) - candidate_cy
```

The centroid is computed from SAR patch energy. It is not a GT center. Large offsets may be diagnostic evidence for center-limited cases, but center error labels may be joined only after scoring is frozen.

### 4.6 Scatter Compactness

```text
scatter_compactness = concentration of SAR energy around the local scatter centroid
```

Possible definitions:

- inverse second moment around the scatter centroid;
- ratio of energy inside a central support radius to total candidate-patch energy;
- entropy-style compactness over thresholded scatter support.

Definition must be frozen before audit.

### 4.7 Peak Count

```text
peak_count = number of local SAR peaks under a declared peak detector
```

The peak detector must be fixed. `peak_count` is not a learned feature and not a post-hoc label.

### 4.8 Local Background Contrast

```text
local_background_contrast =
  energy_inside_candidate_support - energy_in_local_background_ring
```

The background ring must be computed from candidate geometry, not final boxes.

## 5. Inference-Safe Keyframe Confidence

Keyframe confidence asks whether a frame appears locally trustworthy before any audit labels are joined.

Allowed evidence:

- center-size likelihood concentration over frozen candidates;
- agreement between `L_center`, `L_size`, and `L_interaction`;
- candidate-local SAR descriptor quality;
- high center dominance or compactness, if descriptor convention is valid;
- stable local background contrast;
- frozen rank margin from an existing completed run, if available before evaluation joins;
- agreement between optical prior and SAR evidence;
- low missingness;
- local sequence consistency with neighboring inference-safe descriptors.

Forbidden evidence:

- GT boxes;
- A019 final boxes;
- A021 condition / truncation / occlusion labels;
- IoU;
- `axis_aligned_proxy_iou`;
- oracle best-candidate labels;
- center error;
- high-IoU bins;
- manual review outcomes.

Example diagnostic confidence form:

```text
K_t(i) =
  sigma(
      a1 * concentration_cs(t, i)
    + a2 * descriptor_quality(t, i)
    + a3 * center_size_agreement(t, i)
    + a4 * frozen_rank_margin(t, i)
    - a5 * missingness(t, i)
  )
```

All coefficients are symbolic or preregistered. They are not learned from post-hoc labels.

`K_t(i)` is a diagnostic keyframe-confidence hypothesis, not a selector score.

## 6. Keyframe Local Soft Anchor

A keyframe local soft anchor is a high-confidence frame-candidate pair that can send bounded diagnostic support to nearby frames.

It must be:

- local in time;
- soft, not hard;
- decayed by temporal distance;
- limited by uncertainty and missingness;
- reversible during audit;
- never used to lock a candidate or overwrite a rank.

### 6.1 Soft Anchor Message

For anchor candidate `i` in frame `t` and neighbor candidate `j` in frame `u`:

```text
M_anchor(t, i -> u, j) =
    K_t(i)
  * exp(-|u - t| / lambda_time)
  * S_descriptor(z_t(i), z_u(j))
  * S_apparent_motion(i, j, t, u)
  * G_missingness(t, u)
```

Where:

- `K_t(i)` is inference-safe keyframe confidence;
- `S_descriptor` compares SAR descriptors under aspect-aware expectations;
- `S_apparent_motion` checks apparent displacement plausibility;
- `G_missingness` downweights missing or unreliable patches.

This message is diagnostic-only. It must not become a production factor without separate audit and explicit approval.

### 6.2 Locality Rule

Soft anchors may only affect a bounded neighborhood:

```text
|u - t| <= W_anchor
```

`W_anchor` must be fixed before audit. Long-range propagation is forbidden in this draft.

### 6.3 No Hard Lock Rule

The anchor cannot force neighbor candidate identity.

Forbidden:

- copying keyframe candidate coordinates to neighbors;
- requiring the same candidate source;
- overriding SAR evidence;
- deleting neighbor candidates;
- modifying candidate geometry;
- using anchor outcome as a label.

Allowed:

- diagnostic message strength;
- local consistency explanation;
- post-hoc analysis of whether soft messages align with later audit labels.

## 7. Apparent Motion Consistency

Apparent motion consistency replaces true velocity. The GM17 diagnostic should not claim physical speed or metric vehicle motion unless a separate calibrated motion model exists.

The apparent motion term asks:

Do candidate centers and descriptors change in a plausible way across adjacent frames under the local image / SAR coordinate context?

Possible inputs:

- frame order;
- candidate centers in SAR local coordinates;
- optical-conditioned shell movement;
- fan / azimuth context;
- local descriptor continuity;
- candidate source / route as grouping metadata only.

Example term:

```text
S_apparent_motion(i, j, t, u) =
  exp(- residual_apparent_displacement(i, j, t, u) / sigma_motion)
```

Where residual apparent displacement is measured against a weak local expectation, such as:

- small displacement in stabilized local coordinates;
- displacement compatible with optical prior movement;
- displacement compatible with fan / azimuth transition;
- descriptor-consistent shift of scatter centroid.

Forbidden:

- true speed claims;
- acceleration claims;
- using GT displacement;
- using final-box displacement;
- using center error;
- tuning `sigma_motion` from IoU or oracle labels.

## 8. Aspect-Aware Descriptor Sequence

SAR descriptor sequence should expect structured changes, not identical appearance.

Example aspect transition expectations:

| Aspect Transition | Expected Descriptor Behavior | Diagnostic Use |
|---|---|---|
| left -> center | lateral asymmetry moves toward balance; center dominance may rise | candidate may become stronger keyframe |
| center -> right | lateral asymmetry reverses or shifts; center dominance may drop | avoid naive smoothing |
| left -> right | strong descriptor change may be normal if azimuth changes | do not penalize as temporal inconsistency without context |
| unknown -> any | confidence remains limited until descriptor quality improves | avoid hard anchor |

These are hypotheses for diagnostic comparison. They are not trained rules and not active selector constraints.

## 9. Structured Selection Hypothesis

The unified mechanism can be represented as a diagnostic factor graph view:

```text
candidate node C_ti:
  frozen candidate i at frame t

local factors:
  F_cs(C_ti)       center-size likelihood components
  F_sar(C_ti)      SAR descriptor quality / structure
  F_opt(C_ti)      optical prior compatibility

sequence factors:
  F_aspect(C_ti, C_uj)     aspect-aware descriptor consistency
  F_anchor(C_ti, C_uj)     keyframe soft-anchor message
  F_motion(C_ti, C_uj)     apparent motion consistency

audit-only labels:
  GT / A019 / IoU / center error / A021 / oracle
```

The graph is a research explanation surface. It must not emit active rank1 selections in this draft.

Allowed outputs:

- diagnostic factor values;
- message values;
- conflict maps;
- hypotheses about why selection may be structured poorly;
- stop / hold / go recommendations for later audits.

Forbidden outputs:

- replacement rank;
- modified GM17 selector output;
- calibrated factor weights;
- Phase5 readiness claim;
- mainline performance conclusion.

## 10. Avoiding Double Counting

The mechanism overlaps with existing GM17 factors. Ownership must remain explicit.

### 10.1 `transition_factor`

Owns:

- generic adjacent-frame consistency;
- local continuity penalties already present in the existing design.

This spec must not duplicate it by adding another generic smoothness term.

Allowed addition:

- aspect-aware descriptor consistency;
- keyframe-local soft messages with bounded influence;
- apparent motion residuals labeled as diagnostic-only.

### 10.2 `optical_temporal_factor`

Owns:

- optical temporal prior;
- frame order and optical-side sequence expectations.

This spec must not repackage optical temporal prior as SAR evidence.

Allowed addition:

- SAR descriptor behavior conditioned on pre-eval aspect context;
- diagnostic comparison between optical temporal support and SAR structure support.

### 10.3 `sar_structure_factor`

Owns:

- local SAR support;
- contrast;
- structural evidence around a candidate.

This spec must not double count the same SAR energy statistic under multiple names.

Allowed addition:

- explicit left / center / right descriptor decomposition;
- descriptor sequence behavior across frames;
- keyframe confidence from agreement among SAR structure, center-size likelihood, and frozen rank margin.

### 10.4 `center_size_likelihood_candidate_refinement`

Owns:

- local candidate precision plausibility over `(cx, cy, w, h)`;
- center / size / interaction decomposition.

This spec receives:

- `L_center`;
- `L_size`;
- `L_interaction`;
- `L_cs`;
- missingness flags;
- concentration profile over frozen candidates.

It must not reinterpret post-hoc center-limited or size-limited labels as inputs.

## 11. How Center-Size Likelihood Feeds This Mechanism

The center-size likelihood mechanism improves the structured selection diagnostic by providing a sharper local candidate plausibility profile.

Without it:

- SAR temporal logic may only know that neighboring candidates are geometrically near;
- keyframe confidence may be based on vague score margin;
- apparent motion may smooth the wrong center;
- aspect descriptor mismatch may be confused with bad candidate size.

With it:

- keyframes can be chosen from frames where center and size evidence agree;
- soft anchors can be limited to locally plausible candidate states;
- apparent motion can compare candidates that are plausible at the right scale;
- descriptor sequence can distinguish shape/aspect changes from center-size errors;
- structured selection conflicts can be localized to specific factors.

The mechanism receives only inference-safe center-size fields. It cannot receive post-hoc failure buckets, high-IoU labels, or oracle identities.

## 12. Diagnostic-Only Output Design

Future local scripts may output tables, but this document does not run them.

### 12.1 Descriptor Table

One row per frozen candidate per frame:

- `target_id`;
- `scene_id`;
- `track_id`;
- `frame_id`;
- `candidate_id`;
- `candidate_source`;
- `E_left`;
- `E_center`;
- `E_right`;
- `lr_asymmetry`;
- `center_dominance`;
- `mirror_symmetry`;
- `scatter_centroid_dx`;
- `scatter_centroid_dy`;
- `scatter_compactness`;
- `peak_count`;
- `local_background_contrast`;
- descriptor missingness flags;
- convention audit flag.

No GT / IoU / A019 / A021 / oracle / center-error fields are allowed in this table.

### 12.2 Keyframe Confidence Hypothesis Table

One row per candidate-frame hypothesis:

- `target_id`;
- `track_id`;
- `frame_id`;
- `candidate_id`;
- `K_keyframe_confidence`;
- `center_size_concentration`;
- `descriptor_quality`;
- `center_size_agreement`;
- `frozen_rank_margin`;
- `missingness_penalty`;
- `keyframe_candidate_flag`;
- `keyframe_reason_code`.

This table is an inference-safe hypothesis table. It is not proof of correctness.

### 12.3 Soft Anchor Message Table

One row per local message:

- `anchor_frame_id`;
- `anchor_candidate_id`;
- `neighbor_frame_id`;
- `neighbor_candidate_id`;
- `temporal_gap`;
- `descriptor_similarity`;
- `apparent_motion_similarity`;
- `missingness_gate`;
- `anchor_message_strength`;
- `locality_window`;
- `hard_lock_flag`, always `false`.

### 12.4 Structured Selection Hypothesis Table

One row per target or track:

- `target_id`;
- `track_id`;
- dominant local factor;
- dominant sequence factor;
- factor conflict type;
- whether center-size evidence and SAR descriptor evidence agree;
- whether keyframe soft anchor supports or conflicts with frozen rank;
- recommended next diagnostic;
- `active_selector_allowed`, always `false`;
- `phase5_allowed`, always `false`.

### 12.5 Post-Inference Audit Join Table

This table may be produced only after all diagnostic hypothesis tables are frozen:

- frozen diagnostic fields from the tables above;
- `axis_aligned_proxy_iou`, audit-only AABB proxy;
- center error, audit-only;
- oracle identity, audit-only;
- A019 / GT final boxes, audit-only;
- A021 condition / truncation / occlusion labels, audit-only;
- post-hoc failure bucket;
- manual review flag.

This table can evaluate diagnostic hypotheses. It cannot modify scoring.

## 13. Failure Modes

### 13.1 Descriptor Convention Failure

Problem:

Left / right descriptors are not stable because patch orientation convention is unclear.

Response:

Mark `HOLD_FOR_CONVENTION_AUDIT`. Do not use signs of `lr_asymmetry` for conclusions.

### 13.2 Temporal Smoothing Drift

Problem:

Soft anchors start behaving like hard smoothing and suppress SAR evidence in neighboring frames.

Response:

Reduce to explanation-only messages, enforce local window, and keep `hard_lock_flag=false`.

### 13.3 Keyframe Leakage

Problem:

Keyframes are selected because they later have high IoU, low center error, or favorable A021 labels.

Response:

STOP. Keyframe confidence must be recomputed from inference-safe fields only.

### 13.4 Apparent Motion Overclaim

Problem:

The diagnostic begins claiming real velocity or physical speed.

Response:

STOP. Apparent motion is a local coordinate consistency check, not a calibrated motion model.

### 13.5 Double Counting With Existing Factors

Problem:

The same SAR contrast or temporal prior appears in both existing factors and new mechanism terms.

Response:

Assign ownership, remove duplicate term, or mark `HOLD_FOR_DOUBLE_COUNTING_AUDIT`.

### 13.6 Candidate Precision Deficit

Problem:

Temporal and keyframe messages are coherent, but no frozen candidate has plausible center-size state.

Response:

Report candidate precision scarcity. Do not modify candidate bank in this mechanism.

## 14. Stop / Hold / Go Gates

### GO To Diagnostic Audit

Proceed to a future local diagnostic audit only if:

- SAR descriptors can be computed from frozen candidate geometry and SAR patches without labels;
- left / center / right aspect convention is declared;
- keyframe confidence uses inference-safe fields only;
- soft anchor window and decay are fixed before audit;
- apparent motion is defined as coordinate consistency, not true velocity;
- center-size likelihood inputs are inference-safe;
- post-inference audit labels are joined only after hypothesis tables are frozen.

### HOLD

Hold if:

- descriptor convention is uncertain;
- SAR patch extraction depends on final boxes;
- A021 labels are needed to determine descriptor quality;
- keyframe confidence depends on post-hoc success;
- temporal messages duplicate existing `transition_factor`;
- optical temporal evidence is being counted twice;
- center-size likelihood is unavailable or label-contaminated.

### STOP

Stop immediately if:

- GT, IoU, oracle, center error, A019 final boxes, A021 labels, or panel review outcomes enter scoring;
- `axis_aligned_proxy_iou` is treated as rotated IoU;
- heading, orientation, or long-axis conclusions are inferred from `axis_aligned_proxy_iou`;
- keyframe anchors hard-lock candidates;
- anchors propagate globally;
- candidate geometry is moved;
- candidate bank is modified;
- GM17 mainline selector is modified;
- a trained model or learned calibration is introduced;
- OOF calibration is started or approved;
- formal Phase5 is treated as approved;
- a mainline performance conclusion is stated.

## 15. Handoff Summary

This mechanism unifies four diagnostic ideas:

1. SAR aspect sequence: descriptor evolution under left / center / right aspect context, not ordinary smoothing.
2. Keyframe confidence: inference-safe local trust hypotheses, not post-hoc correctness labels.
3. Local soft anchors: bounded messages to neighbors, not hard locks or global propagation.
4. Apparent motion consistency: local coordinate consistency, not real velocity.

The mechanism receives candidate precision evidence from `center_size_likelihood_candidate_refinement` and produces diagnostic-only structured selection hypotheses. It may explain why the existing factor stack misses good frozen candidates, but it cannot replace the selector, modify A001, approve Phase5, or claim performance improvement.
