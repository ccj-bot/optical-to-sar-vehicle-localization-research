# GM17 Scattering-Aware Candidate State Inference Framework Plan

Date: 2026-06-29

Status: research synthesis plan

## 1. Core Thesis

The GM17 optical-to-SAR vehicle localization problem should no longer be framed as a simple choice between candidate generation and candidate ranking.

The current evidence supports a more precise diagnosis:

* The fixed candidate bank has strong usable / coarse coverage.
* High-IoU precision is weak under the current post-inference `axis_aligned_proxy_iou` audit.
* Structured selection remains unstable even when usable candidates exist.

Therefore, the current research problem is a dual bottleneck:

```text
candidate precision bottleneck
+
structured selection bottleneck
```

The next research step should be a unified diagnostic framework:

```text
GM17 Scattering-Aware Candidate State Inference Framework
```

中文可称为：

```text
GM17 散射感知候选状态推断框架
```

The key idea is:

> Do not treat the candidate box as the vehicle itself.
> A candidate box is only a frozen hypothesis. It must be evaluated by whether it can explain optical prior, SAR scattering support, aspect-conditioned scatter offset, temporal descriptor evolution, and local keyframe identifiability.

## 2. Why The Old Story Is Insufficient

The older interpretation was:

```text
The candidate bank already contains many good candidates, but ranking fails.
```

This is now too strong.

The corrected interpretation is:

```text
The candidate bank has strong coarse coverage, but high-IoU precision is weak.
Ranking / selection is still a bottleneck, but it is not the only bottleneck.
```

This means:

* If high-IoU candidates are missing, no selector can recover exact precision.
* If usable candidates exist but are not selected, structured selection is still weak.
* If SAR evidence is ambiguous, keyframe and temporal information may help only when local identifiability is high.
* If the metric is only `axis_aligned_proxy_iou`, heading / orientation conclusions must remain deferred.

## 3. Physical Reframing

A SAR vehicle target should not be modeled as a simple projected optical box.

Separate the following states:

```text
G_t  = latent vehicle geometric state
S_t  = latent SAR scattering support
C_ti = frozen candidate box i at frame t
A_t  = SAR aspect state: left / center / right / unknown
I_t  = identifiability state
K_t  = keyframe confidence
U_t  = uncertainty / ambiguity state
```

The physical intuition is:

```text
vehicle geometry
    -> aspect-conditioned SAR scattering support
    -> observed bright points / shadow / local contrast
    -> candidate box compatibility
```

A candidate box is valid only if it can explain the SAR scattering evidence under the current aspect and temporal context.

## 4. Scatter-Geometry Separation

A central idea is that the SAR scattering center does not necessarily equal the vehicle geometric center.

Introduce a conceptual offset:

```text
scatter_center_t = vehicle_center_t + delta_t
```

where:

```text
delta_t = aspect-conditioned scattering offset
```

This offset may depend on:

* SAR aspect state;
* left / center / right viewing context;
* local background;
* vehicle size / extent;
* side-biased scattering;
* shadow and strong reflector structure;
* candidate geometry.

This explains why a candidate can be:

* coarse-correct but high-IoU weak;
* center-plausible but size-limited;
* SAR-bright but geometrically biased;
* temporally smooth but physically wrong;
* locally ambiguous but resolvable near a keyframe.

Important boundary:

```text
axis_aligned_proxy_iou is not rotated IoU.
It cannot support heading, orientation, or long-axis conclusions.
```

## 5. Center-Size Likelihood As Local Precision Explanation

The existing `center_size_likelihood_candidate_refinement` should be interpreted as research-understanding refinement, not candidate geometry refinement.

It should answer:

```text
Given a frozen candidate (cx, cy, w, h),
how plausible is this center-size state under SAR patch evidence,
optical prior, scene prior, and temporal context?
```

Diagnostic form:

```text
p(cx, cy, w, h | SAR patch, optical prior, scene prior, temporal context)
```

or log form:

```text
L_cs(i) =
    alpha_c * L_center(i)
  + alpha_s * L_size(i)
  + alpha_i * L_interaction(i)
  + alpha_o * L_optical_prior(i)
  + alpha_t * L_temporal_context(i)
  + alpha_m * L_missingness(i)
```

This mechanism should decompose high-IoU weakness into:

* center-limited;
* size-limited;
* center-size combined;
* aspect / shape-hypothesis limited;
* proxy-metric limitation;
* future rotated-OBB audit only.

It must not:

* move candidate centers;
* change candidate width or height;
* add candidates;
* delete candidates;
* replace the fixed bank;
* modify the GM17 selector;
* become a Phase5 calibration path.

## 6. SAR Aspect Sequence As Structure-Over-Time Explanation

SAR temporal information should not be reduced to ordinary temporal smoothing.

Ordinary temporal smoothing asks:

```text
Are neighboring boxes close?
```

SAR aspect sequence asks:

```text
Does the SAR scattering structure evolve coherently under aspect changes?
```

Candidate-local descriptors may include:

```text
E_left
E_center
E_right
lr_asymmetry
center_dominance
mirror_symmetry
scatter_centroid_dx
scatter_centroid_dy
scatter_compactness
peak_count
local_background_contrast
```

Expected aspect behavior:

* left aspect: lateral asymmetry, shifted scatter centroid, weaker mirror symmetry;
* center aspect: stronger center dominance, higher symmetry, more compact support;
* right aspect: opposite-side lateral bias and structured descriptor change;
* unknown aspect: weak confidence, no hard anchoring.

This mechanism is SAR-specific because it models structured scattering changes, not just coordinate continuity.

## 7. Identifiability And Keyframe Confidence

A keyframe should not be defined as a high-score frame.

A better definition is:

```text
keyframe = low-entropy / high-identifiability frame
```

A frame is more identifiable when:

* candidate likelihood distribution is concentrated;
* center-size evidence agrees;
* SAR descriptor is clear;
* optical prior and SAR support are not in conflict;
* missingness is low;
* factor disagreement is low;
* uncertainty is low.

Conceptual variables:

```text
q_cs(i | target, t) = normalized diagnostic likelihood over frozen candidates
H_t = entropy(q_cs)
I_t = identifiability state
K_t = keyframe confidence
```

High-confidence keyframes should come from low ambiguity, not post-hoc correctness.

Forbidden keyframe evidence:

* GT;
* IoU;
* oracle identity;
* center error;
* A019 final boxes;
* A021 labels;
* manual review outcomes.

## 8. Local Soft Anchor

A keyframe may act only as a local soft anchor.

It must not:

* hard-lock a candidate;
* copy candidate coordinates to neighbors;
* overwrite SAR evidence;
* propagate globally;
* force the same candidate source;
* become an active selector rule.

Diagnostic message form:

```text
M_anchor(t, i -> u, j) =
    K_t(i)
  * exp(-|u - t| / lambda_time)
  * S_descriptor(z_t(i), z_u(j))
  * S_apparent_motion(i, j, t, u)
  * G_missingness(t, u)
```

The message is only an explanation surface.

## 9. Apparent Motion Consistency

The current project should not claim real velocity or physical speed.

Use:

```text
apparent frame-to-frame consistency
```

not:

```text
real speed
physical velocity
metric vehicle motion
```

Apparent motion asks:

```text
Do candidate centers and descriptors change plausibly across local frame order under SAR / image coordinate context?
```

This should be separated from:

* existing `transition_factor`;
* existing `optical_temporal_factor`;
* SAR local structure evidence.

Its role is local consistency, not physical dynamics.

## 10. Mechanism Interaction

The mechanisms should be interpreted as a diagnostic chain:

```text
high-IoU precision decomposition
    -> identifies center / size / shape / proxy limitations

center-size likelihood
    -> explains local candidate precision over frozen candidates

SAR aspect sequence
    -> explains descriptor evolution under aspect state

identifiability / keyframe confidence
    -> identifies low-ambiguity local anchors

local soft anchor
    -> tests whether nearby frames can be stabilized without hard propagation

structured selection hypothesis
    -> explains why the current factor stack may fail
```

The important chemical interaction is:

```text
center-size likelihood clarifies local candidate precision
-> keyframe confidence identifies frames where local precision evidence is strong
-> SAR aspect sequence checks whether structure evolves coherently
-> soft anchors test whether neighboring frames can be stabilized
-> structured selection diagnosis separates bank scarcity from selection failure
```

## 11. Diagnostic Pipeline

The unified Phase4-extension diagnostic pipeline should be:

1. High-IoU Precision Decomposition
2. Center-Size Likelihood Precision Audit
3. SAR Aspect Descriptor Separability
4. Keyframe Confidence Validity
5. Soft Anchor Propagation Simulation
6. Combined Pipeline Interpretation

Each step must freeze inference-safe evidence before joining post-inference audit labels.

## 12. Leakage Controls

Forbidden during scoring:

* GT boxes;
* A019 final boxes;
* A021 condition / truncation / occlusion labels;
* IoU;
* `axis_aligned_proxy_iou`;
* oracle labels;
* center error;
* high-IoU bins;
* manual review labels;
* any field derived from the above.

Allowed only after frozen scoring / descriptor extraction:

* audit IoU;
* center error;
* oracle identity;
* failure bucket;
* condition label;
* manual review.

## 13. Double-Counting Controls

Ownership must be explicit:

```text
geometry_factor:
    generic frozen candidate geometry plausibility

sar_structure_factor:
    local SAR support and structure evidence

optical_temporal_factor:
    optical-side temporal prior

transition_factor:
    generic adjacent-frame continuity

center_size_likelihood_candidate_refinement:
    diagnostic center / size / interaction plausibility

sar_aspect_sequence_factor:
    descriptor evolution under aspect context

keyframe_anchor_factor:
    local low-entropy anchor message

apparent_motion_consistency_factor:
    local frame-to-frame candidate-state consistency
```

Any term that cannot be assigned cleanly should be marked:

```text
HOLD_FOR_FIELD_AUDIT
```

## 14. Stop / Hold / Go Gates

STOP if:

* GT / IoU / oracle / center error enters scoring;
* `axis_aligned_proxy_iou` is treated as rotated IoU;
* heading or orientation conclusions are inferred from AABB proxy;
* candidate geometry is moved;
* candidate bank is modified;
* GM17 selector is modified;
* keyframes hard-lock candidates;
* anchors propagate globally;
* model training or OOF calibration starts;
* formal Phase5 is treated as approved.

HOLD if:

* descriptor convention is uncertain;
* field origin cannot be proven;
* SAR descriptor extraction depends on final boxes;
* candidate source is used as a ranking shortcut;
* metric limitation dominates and a rotated-OBB audit is needed first.

GO to later diagnostic work only if:

* all inference-safe fields are frozen;
* post-inference audit labels are joined only after scoring / descriptor extraction;
* missingness policy is explicit;
* no selector change is required;
* output remains diagnostic-only.

## 15. Relationship To Formal Phase5

No route from this framework directly approves formal Phase5.

Formal Phase5 remains:

```text
BLOCKED_FOR_OOF_CALIBRATION
```

Formal Phase5 can be reconsidered only after:

* field allowlist / denylist is stable;
* leakage audit passes;
* double-counting audit passes;
* missing-value policy is fixed;
* candidate precision vs selection bottleneck is separated;
* diagnostic factors have clear ownership;
* release governance approves calibration.

## 16. Open Questions

1. Is high-IoU weakness mostly center-limited, size-limited, combined, or metric-limited?
2. Can SAR patch evidence support center-size likelihood without label leakage?
3. Are left / center / right aspect descriptors stable enough to define sequence structure?
4. Can keyframe confidence be defined from low entropy and factor agreement?
5. Does local soft anchoring explain selection failures without becoming hard propagation?
6. Does the fixed bank contain locally plausible states that the selector misses?
7. If not, what evidence is needed before any candidate-bank refinement can be discussed?
8. What rotated-OBB audit is needed before heading / orientation claims become valid?

## 17. Summary

The proposed unified framework reframes GM17 from candidate-box ranking to scattering-aware candidate-state inference.

The central claim is:

```text
A candidate is not correct merely because it is close.
A candidate is plausible when its geometry can explain SAR scattering support,
aspect-conditioned structure, temporal descriptor evolution,
and local identifiability under inference-safe evidence.
```

This remains diagnostic-only.

It does not approve formal Phase5.
It does not change the candidate bank.
It does not change the GM17 selector.
It does not run experiments.
It does not train models.
