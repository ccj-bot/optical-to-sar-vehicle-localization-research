# GM17 Center-Size Likelihood Candidate Refinement Spec

Date: 2026-06-29

Status: diagnostic-only mechanism draft

This document connects the Phase4-extension high-IoU precision decomposition to `center_size_likelihood_candidate_refinement`. The name is retained because it is the current research-thread label, but the mechanism is explicitly non-mutating: it does not move, generate, delete, replace, or insert candidates. A safer operational alias is `center_size_likelihood_precision_audit`.

No experiment is run by this document. No model is trained. No OOF calibration is performed. No candidate bank is modified. No GM17 mainline selector is modified. No new mainline performance conclusion is produced.

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.

## 1. Purpose

The high-IoU precision decomposition separates weak `coverage@0.9` / `coverage@0.95` into candidate-state failure modes. This spec defines the next diagnostic mechanism for the center and size parts of that decomposition.

The core question is:

Given a frozen candidate `(cx, cy, w, h)`, how plausible is that candidate's center and size under SAR local evidence, optical prior context, scene prior, and temporal context, without using post-inference labels?

The mechanism should explain whether weak high-IoU precision is caused by:

- center error;
- width / height / extent error;
- center-size interaction;
- candidate shape or aspect hypothesis mismatch that is visible through size / aspect terms;
- insufficient candidate precision even when coarse A001 coverage is strong.

It must not become:

- candidate-bank expansion;
- generated-proposal integration;
- candidate geometry adjustment;
- threshold tuning;
- an active selector rule;
- a Phase5 calibration path.

## 2. Why Coarse Coverage Can Be Strong While High-IoU Precision Is Weak

Coarse coverage means a candidate exists in a useful neighborhood of the target. High-IoU precision requires a much tighter candidate state.

The gap can happen in at least three center-size ways:

1. **Center-limited:** the candidate extent is plausible, but `(cx, cy)` is offset enough to lose high overlap.
2. **Size-limited:** the center is plausible, but `w`, `h`, area, or aspect mismatch prevents high overlap.
3. **Center-size combined:** modest center error and modest size error interact, so neither dimension alone explains the failure.

These buckets are post-inference explanations. They are not labels that may be used to score candidates.

The diagnostic aim is to learn whether the existing fixed bank already contains candidates whose center-size state is plausible under inference-safe evidence, and whether the current structured selector is failing to identify them. If the bank does not contain such candidates, the conclusion is still diagnostic: it documents candidate precision scarcity but does not authorize candidate-bank modification.

## 3. Definition

`center_size_likelihood_candidate_refinement` is a diagnostic likelihood view over frozen candidate geometry:

```text
candidate state s_i = (cx_i, cy_i, w_i, h_i)
evidence e_i = (SAR patch, optical prior, scene prior, temporal context)

L_cs(i) = log p(cx_i, cy_i, w_i, h_i | e_i)
```

The word `refinement` means refinement of research understanding, not refinement of candidate coordinates.

Allowed:

- evaluate a likelihood or pseudo-likelihood for an existing candidate;
- decompose that likelihood into center, size, and interaction terms;
- compare likelihood patterns against post-inference audit buckets after scoring is frozen;
- identify whether future diagnostics should inspect center evidence, size evidence, temporal support, or SAR descriptors.

Forbidden:

- moving `(cx, cy)`;
- changing `w` or `h`;
- adding a candidate to A001;
- deleting a candidate from A001;
- replacing rank1 output;
- sorting candidates for mainline inference;
- feeding likelihood into C3/C4 or any GM17 mainline selector;
- using GT, IoU, oracle, center error, A019, A021, or final boxes during scoring.

## 4. Diagnostic-Only Audit Contract

The mechanism is a two-stage audit design.

Stage 1: freeze all inference-safe candidate fields.

- Candidate geometry exists before any evaluation join.
- SAR patch descriptors are computed without GT / IoU / A019 / A021 / oracle / center error.
- Optical prior and temporal context fields are declared before audit labels are available.
- Symbolic likelihood components and missing-value policies are fixed.

Stage 2: join post-inference audit fields.

- GT / A019 / final boxes may be used only to compute audit labels.
- `axis_aligned_proxy_iou` may be used only as an AABB proxy audit metric.
- Center error may be used only to assign explanatory buckets.
- A021 condition / truncation / occlusion labels may be used only to interpret failure groups after scoring is frozen.

The audit may report whether likelihood components align with post-hoc failure buckets. It may not report selector performance improvement, calibrated accuracy, or Phase5 readiness.

## 5. Inference-Safe Inputs

These fields may be used to define diagnostic likelihood components only if they are available before evaluation joins.

### 5.1 Candidate Geometry

- `candidate_id`;
- `target_id`;
- `scene_id`;
- `track_id`, if pre-eval;
- `frame_id` or frame order;
- `cx`, `cy`;
- `w`, `h`;
- stored `theta`, if already present as metadata, not as a heading correctness label;
- candidate crop bounds;
- candidate source / route metadata as grouping or provenance.

### 5.2 SAR Patch Evidence

SAR evidence must be computed from the local patch around each frozen candidate. It must not use final boxes or post-hoc labels.

Potential diagnostic descriptors:

- local foreground energy;
- local background energy;
- target-to-background contrast;
- center mass within the candidate support;
- support compactness;
- radial energy profile around `(cx, cy)`;
- edge / boundary support near candidate extent;
- left / center / right subregion energies;
- top / middle / bottom subregion energies;
- peak count;
- peak spread;
- SAR crop quality / missingness flags.

These descriptors are not a trained representation. They are hand-declared diagnostic evidence for explaining center-size plausibility.

### 5.3 Optical Prior

Allowed optical-conditioned priors:

- optical-to-SAR shell identity;
- allowed local search region;
- vehicle size prior as a range, not a single hard value;
- coarse pose / main-axis prior as weak metadata;
- fan-polar or azimuth-band context;
- truncation restoration signals only if they are inference-time inputs and not A021 labels;
- depth as weak context only if already part of the pre-eval pipeline.

### 5.4 Scene Prior

Allowed scene context:

- scene id;
- local SAR background statistics;
- road / region context if available without labels;
- range-bin / azimuth-bin context;
- expected vehicle size ranges declared before audit;
- missingness / edge-of-frame flags computed without GT.

### 5.5 Temporal Context

Allowed temporal context:

- neighboring frame order;
- frozen candidate geometry in neighboring frames;
- pre-eval optical temporal prior;
- inference-safe temporal consistency descriptors;
- keyframe-confidence hypotheses computed without post-hoc labels.

Temporal context must not become hard propagation. It may provide a soft diagnostic term only.

## 6. Post-Inference Audit Fields

These fields may be joined only after likelihood computation is frozen.

- GT boxes;
- A019 final boxes or manually finalized boxes;
- final-box-derived center;
- `axis_aligned_proxy_iou`;
- high-IoU bins;
- oracle best-candidate identity;
- center error;
- `dx`, `dy`, `abs_dx`, `abs_dy`;
- width error;
- height error;
- area ratio;
- aspect-ratio gap;
- A021 condition labels;
- truncation labels;
- occlusion labels;
- visibility labels;
- panel review notes;
- manual-review outcome;
- future rotated-IoU / heading / long-axis labels, if separately audited.

These fields are explanatory labels only. They cannot be used in likelihood scoring, hyperparameter choice, candidate filtering, anchor selection, or route selection.

## 7. Likelihood Form

The target form is:

```text
p(cx, cy, w, h | SAR patch, optical prior, scene prior, temporal context)
```

For audit design, use a log decomposition:

```text
L_cs(i) =
    alpha_c  * L_center(i)
  + alpha_s  * L_size(i)
  + alpha_i  * L_interaction(i)
  + alpha_o  * L_optical_prior(i)
  + alpha_t  * L_temporal_context(i)
  + alpha_m  * L_missingness(i)
```

Where:

- `i` indexes an existing frozen candidate;
- all `alpha_*` are symbolic or preregistered constants for diagnostic analysis;
- no `alpha_*` may be learned from GT, IoU, center error, oracle labels, A019, A021, or final boxes;
- no component may be calibrated by OOF in this draft.

The likelihood may be normalized within a target only for diagnostics:

```text
q_cs(i | target) = exp(L_cs(i)) / sum_j exp(L_cs(j))
```

This normalized value is not an active posterior for mainline selection. It is a diagnostic concentration score: does inference-safe evidence concentrate around candidates that later prove center-size plausible?

## 8. Component Definitions

### 8.1 Center Term

Purpose:

Estimate whether the SAR patch supports the candidate center.

Possible evidence:

- local energy concentration near `(cx, cy)`;
- radial profile centered on `(cx, cy)`;
- contrast between center support and surrounding background;
- scatter centroid offset from `(cx, cy)`;
- consistency between optical prior center and SAR evidence center;
- neighbor-frame center stability, if computed without labels.

Example pseudo-term:

```text
L_center(i) =
  - beta_1 * norm(scatter_centroid(i) - candidate_center(i))
  + beta_2 * center_energy_contrast(i)
  - beta_3 * center_support_missingness(i)
```

The scatter centroid is derived from SAR patch evidence only. It is not a GT center.

### 8.2 Size Term

Purpose:

Estimate whether the candidate width and height are plausible.

Possible evidence:

- edge support near candidate boundaries;
- energy falloff outside candidate extent;
- extent compactness;
- vehicle size prior range;
- local background contrast around the candidate box;
- width / height plausibility under scene and optical context.

Example pseudo-term:

```text
L_size(i) =
  + gamma_1 * boundary_support(i)
  + gamma_2 * inside_outside_contrast(i)
  - gamma_3 * size_prior_penalty(w_i, h_i)
  - gamma_4 * extent_missingness(i)
```

The size prior is a range or weak prior, not a hard clamp.

### 8.3 Center-Size Interaction Term

Purpose:

Capture the fact that center and size are not independent. A box can look plausible in size only when centered correctly, and a center can look plausible only at the right support scale.

Possible evidence:

- energy compactness at the candidate scale;
- center dominance relative to candidate extent;
- edge support symmetry around the candidate center;
- inside / outside contrast at multiple size hypotheses already present in the fixed bank;
- disagreement between center term and size term.

Example pseudo-term:

```text
L_interaction(i) =
  + eta_1 * scale_matched_center_support(i)
  + eta_2 * boundary_symmetry_about_center(i)
  - eta_3 * center_size_disagreement(i)
```

No new candidate sizes are generated. If multiple sizes are compared, they must already exist as frozen candidates.

### 8.4 Optical Prior Term

Purpose:

Keep the optical-to-SAR shell as a soft prior without allowing it to dominate precise SAR localization.

Possible evidence:

- candidate remains inside the predeclared shell;
- distance to shell center or fan-band support;
- compatibility with size range;
- compatibility with weak pose / main-axis metadata.

Example pseudo-term:

```text
L_optical_prior(i) =
  - rho_1 * shell_distance_penalty(i)
  - rho_2 * weak_size_prior_penalty(i)
```

The optical term should not reward occupancy alone. It should remain a soft neighborhood prior.

### 8.5 Temporal Context Term

Purpose:

Allow sequence context to stabilize candidate plausibility while avoiding hard propagation.

Possible evidence:

- local consistency with neighboring frozen candidate states;
- apparent motion plausibility in image / SAR coordinates;
- agreement with keyframe soft anchors if those anchors are computed from inference-safe evidence;
- descriptor continuity across adjacent frames.

Example pseudo-term:

```text
L_temporal_context(i, t) =
  + tau_1 * local_neighbor_agreement(i, t)
  - tau_2 * apparent_motion_residual(i, t)
  - tau_3 * temporal_gap_penalty(i, t)
```

This is not true velocity estimation. It is apparent consistency over frame-indexed candidate states.

## 9. Failure Bucket Assignment

Failure buckets are assigned only after post-inference audit labels are joined.

### Center-Limited

Criteria:

- post-hoc center error is large relative to the candidate's size / support;
- size term is plausible or less problematic;
- best-center candidate differs from rank1 or best-proxy candidate;
- likelihood center term fails to concentrate around the post-hoc better center candidate.

Diagnostic conclusion:

The next question is whether SAR center evidence or keyframe anchoring can improve candidate discrimination.

### Size-Limited

Criteria:

- center error is relatively small;
- width / height / area / aspect mismatch explains weak proxy overlap;
- size term fails to distinguish plausible extent candidates;
- same-center or nearby-center candidates differ mostly by extent.

Diagnostic conclusion:

The next question is whether size evidence, boundary support, or SAR aspect descriptors can separate better extents.

### Center-Size Combined

Criteria:

- both center and size errors are moderate;
- neither center nor size alone explains the failure;
- interaction term is weak or contradictory;
- best-center and best-proxy roles split across different frozen candidates.

Diagnostic conclusion:

The next question is whether a joint center-size likelihood is necessary before temporal or keyframe mechanisms can help.

### Aspect / Shape-Hypothesis Limited

Criteria:

- center and size are not sufficient to explain the proxy failure;
- aspect ratio or shape hypothesis differs by candidate source;
- SAR crop descriptors suggest structured left / center / right or long-axis ambiguity;
- future rotated-OBB audit may be required.

Diagnostic conclusion:

Route to SAR aspect sequence / descriptor separability diagnostics, not to heading conclusions.

### Proxy-Metric Limitation

Criteria:

- AABB proxy behavior does not match visual or structural interpretation;
- likely rotated-OBB / orientation issue cannot be answered by `axis_aligned_proxy_iou`;
- manual review indicates metric ambiguity.

Diagnostic conclusion:

Design a separate rotated-OBB audit. Do not infer heading or orientation from the proxy.

## 10. How This Helps SAR Temporal / Keyframe Mechanisms

The center-size likelihood audit can improve the candidate space available to temporal and keyframe diagnostics without modifying the candidate bank.

It provides:

- a per-candidate plausibility profile over existing candidates;
- a distinction between center evidence and size evidence;
- a way to identify candidates that are stable in center but weak in size;
- a way to identify candidates that are plausible locally but need temporal disambiguation;
- a way to define keyframe confidence from inference-safe evidence, before post-hoc evaluation labels are joined.

The SAR temporal / keyframe mechanism can consume only inference-safe products:

- frozen candidate geometry;
- SAR patch descriptor values;
- diagnostic likelihood components computed without labels;
- missingness flags;
- pre-eval temporal context.

It cannot consume:

- high-IoU labels;
- oracle identity;
- center error;
- A019 / GT boxes;
- A021 condition labels;
- post-hoc failure buckets.

The chemical interaction is:

```text
center-size likelihood clarifies local candidate precision
-> keyframe confidence identifies frames where local precision evidence is strong
-> soft anchors explain whether neighboring frames can be stabilized
-> structured selection hypothesis tests whether existing factor interactions are missing
```

Every arrow is diagnostic-only.

## 11. Output Design For Future Audit

A future local audit script may produce tables, but this document does not run that script.

### Candidate Likelihood Table

One row per frozen candidate:

- `target_id`;
- `candidate_id`;
- `scene_id`;
- `track_id`;
- `frame_id`;
- `cx`, `cy`, `w`, `h`;
- `candidate_source`;
- `L_center`;
- `L_size`;
- `L_interaction`;
- `L_optical_prior`;
- `L_temporal_context`;
- `L_missingness`;
- `L_cs`;
- `q_cs_within_target`;
- `component_missing_flags`.

No post-inference audit labels appear in this table.

### Post-Hoc Alignment Table

One row per target or candidate after audit labels are joined:

- `target_id`;
- `candidate_id`;
- frozen `L_*` components;
- `axis_aligned_proxy_iou`, audit only;
- center error, audit only;
- width / height / area errors, audit only;
- high-IoU bin, audit only;
- oracle role, audit only;
- primary failure bucket;
- secondary failure bucket;
- manual review flag.

This table may be used for explanation only.

### Bucket Summary Table

One row per failure bucket:

- bucket name;
- count;
- share of audited targets;
- dominant likelihood component weakness;
- dominant candidate source, post-hoc grouping only;
- recommended next diagnostic;
- stop / hold / go recommendation.

## 12. Leakage And Double-Counting Controls

### Leakage Controls

- Freeze all candidate geometry and SAR descriptors before joining audit labels.
- Freeze all component definitions before joining audit labels.
- Do not learn weights from audit labels.
- Do not tune thresholds from `axis_aligned_proxy_iou`, center error, or oracle identity.
- Do not use A021 labels for scoring or missing-value policy.
- Keep A019 / GT boxes out of descriptor extraction.

### Double-Counting Controls

The mechanism overlaps conceptually with existing geometry and structure factors, so ownership must be explicit.

| Existing / Proposed Component | Owns | Must Not Double Count |
|---|---|---|
| `geometry_factor` | frozen candidate geometry and generic geometric plausibility | post-hoc center/size error labels |
| `sar_structure_factor` | local SAR support / structure evidence | A021 condition or final-box labels |
| `optical_temporal_factor` | pre-eval optical temporal prior | post-hoc track correctness |
| `transition_factor` | generic adjacent-frame consistency | keyframe confidence or oracle identity |
| `center_size_likelihood_candidate_refinement` | diagnostic decomposition of center, size, and interaction plausibility | active ranking, candidate edits, Phase5 calibration |

If a term cannot be clearly assigned, it must be removed or marked `HOLD_FOR_FIELD_AUDIT`.

## 13. Stop / Go Gates

### GO To SAR Temporal / Keyframe Mechanism

Proceed only if:

- likelihood components can be computed from inference-safe inputs;
- center / size / interaction signals are not just proxies for post-hoc labels;
- missingness is explicit;
- a keyframe confidence candidate can be defined without GT / IoU / oracle / center error / A019 / A021;
- results remain diagnostic-only.

### GO To Experiment B Audit

Proceed to a local post-inference audit later only if:

- the table schemas are frozen;
- the scoring fields are separated from audit fields;
- no weight learning or threshold tuning is requested;
- output is labeled diagnostic-only.

### HOLD

Hold if:

- SAR descriptor extraction cannot be separated from final boxes;
- center and size evidence are too entangled to interpret;
- candidate source metadata is being used as a rank shortcut;
- A021 condition labels are needed to make the mechanism work;
- the mechanism starts implying candidate-bank edits.

### STOP

Stop immediately if:

- candidate coordinates are moved;
- new candidates are generated;
- A001 is modified;
- GM17 selector logic is modified;
- `axis_aligned_proxy_iou` is used as rotated IoU;
- heading or orientation conclusions are made from the AABB proxy;
- GT, IoU, oracle, center error, A019 final boxes, A021 labels, or panel review outcomes enter scoring;
- training or OOF calibration is started;
- formal Phase5 is treated as approved.

## 14. Handoff Summary

This mechanism is the bridge between high-IoU precision decomposition and temporal / keyframe structured selection diagnostics. It asks whether existing candidates contain center-size states that are locally plausible under inference-safe evidence. If yes, temporal and keyframe mechanisms can test whether those locally plausible states can be stabilized across nearby frames. If no, the conclusion remains diagnostic candidate precision scarcity, not candidate-bank authorization.
