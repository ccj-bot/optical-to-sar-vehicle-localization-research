# GM17 Scattering-Aware Candidate State Inference Framework

Date: 2026-06-29

Status: unified research framework draft

Chinese meaning: GM17 散射感知候选状态推断框架

Primary plan source:

- `docs/gm17_scattering_aware_candidate_state_inference_framework_plan.md`

Related baseline documents:

- `docs/gm17_dual_bottleneck_research_synthesis.md`
- `docs/gm17_next_diagnostic_experiment_matrix.md`
- `docs/gm17_phase4_extension_high_iou_precision_decomposition_spec.md`
- `docs/gm17_center_size_likelihood_candidate_refinement_spec.md`
- `docs/gm17_sar_temporal_keyframe_selection_mechanism_spec.md`

This document is a unifying framework. It is not an experiment report, not a training plan, not OOF calibration, not a candidate-bank modification plan, and not a GM17 mainline selector patch.

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.

## 1. Executive Summary

The GM17 optical-to-SAR localization problem should be framed as scattering-aware candidate state inference, not direct candidate-box ranking.

The key shift is:

```text
candidate box != vehicle state
candidate box = frozen hypothesis about a latent vehicle/scattering state
```

The framework separates:

- latent vehicle geometric state;
- latent SAR scattering support;
- frozen candidate box;
- SAR aspect state;
- identifiability / keyframe state;
- uncertainty state.

The current research diagnosis remains a dual bottleneck:

- fixed A001 candidate bank has strong usable / coarse coverage;
- high-IoU precision is weak under the current post-inference `axis_aligned_proxy_iou` audit;
- structured selection is still weak when usable candidates exist.

The unified framework connects five mechanism families:

1. high-IoU precision decomposition;
2. center-size likelihood precision audit;
3. SAR aspect sequence descriptors;
4. identifiability and keyframe confidence;
5. local soft anchors and apparent frame-to-frame consistency.

All mechanisms are diagnostic-only unless separately audited and explicitly promoted through release governance. None are active factors in this document.

## 2. Why Candidate Boxes Are Not Enough

A candidate box is a compact geometry record, usually represented as:

```text
C_ti = (cx_i, cy_i, w_i, h_i, optional theta_i, metadata_i)
```

It is useful, but incomplete. It does not directly encode:

- whether the SAR bright response is centered on the vehicle geometric center;
- whether the visible SAR support is side-biased under the current aspect;
- whether the candidate extent matches SAR support or only covers a coarse region;
- whether nearby frames provide coherent aspect-conditioned evidence;
- whether the frame is identifiable enough to act as a local anchor;
- whether the current metric can answer the physical question being asked.

The old simplified story was:

```text
The bank contains good candidates; ranking fails.
```

The corrected story is:

```text
The bank contains many useful coarse candidates,
but near-exact candidate states are sparse,
and structured selection still fails to identify better frozen hypotheses.
```

This means candidate boxes are evidence containers, not vehicles. A candidate should be evaluated by whether its geometry can explain optical prior, SAR scattering support, aspect-conditioned offset, temporal descriptor evolution, and local identifiability under inference-safe evidence.

## 3. Dual Bottleneck Revisited

The dual bottleneck is:

```text
candidate precision bottleneck
+
structured selection bottleneck
```

### Candidate Precision Bottleneck

Candidate precision asks what states exist before selection.

Strong coarse coverage says A001 often places candidates in the right neighborhood. Weak high-IoU precision says the fixed bank often lacks a near-exact state under the current AABB proxy audit.

This may reflect:

- center error;
- size / extent error;
- center-size interaction;
- aspect or shape-hypothesis mismatch;
- metric limitation from using an AABB proxy;
- future rotated-OBB / heading questions that the current proxy cannot answer.

### Structured Selection Bottleneck

Structured selection asks whether the system can identify the best available frozen candidate when a useful candidate exists.

The selection bottleneck may reflect:

- weak interaction between local SAR evidence and geometry;
- temporal smoothness overpowering SAR evidence;
- candidate-source shortcuts;
- poor handling of aspect-conditioned SAR structure;
- lack of keyframe identifiability modeling;
- double-counting among existing geometry, SAR, optical-temporal, and transition factors.

The two bottlenecks interact. If high-precision candidates are rare, the selector must preserve and recognize them. If the selector is structurally weak, even a candidate bank with usable coverage can underperform its own potential.

## 4. Physical Interpretation: Geometry State vs SAR Scattering Support

The framework separates vehicle geometry from SAR scattering support.

Latent vehicle geometry:

```text
G_t = vehicle geometric state at frame t
```

Latent SAR scattering support:

```text
S_t = SAR scattering support generated by G_t under aspect, background, and sensor context
```

Frozen candidate:

```text
C_ti = candidate box i at frame t
```

The physical chain is:

```text
vehicle geometry
  -> aspect-conditioned SAR scattering support
  -> observed bright points / shadow / local contrast
  -> candidate compatibility
```

The SAR scattering center does not necessarily equal the vehicle geometric center:

```text
scatter_center_t = vehicle_center_t + delta_t
```

Where:

```text
delta_t = aspect-conditioned scattering offset
```

`delta_t` may depend on:

- left / center / right aspect state;
- side-biased scattering;
- strong reflector location;
- shadow and local background;
- vehicle size and candidate extent;
- SAR patch missingness;
- local clutter.

This separation explains why a candidate can be:

- coarse-correct but high-IoU weak;
- SAR-bright but geometrically biased;
- center-plausible but size-limited;
- temporally smooth but physically wrong;
- ambiguous in a weak frame but explainable near a keyframe.

Metric boundary:

`axis_aligned_proxy_iou` is an audit-only AABB proxy. It is not rotated IoU. It cannot support heading, orientation, long-axis, or rotated-OBB conclusions.

## 5. Latent Variables

The framework uses conceptual latent variables to organize diagnostics. They are not active model variables in the current mainline.

```text
G_t   = latent vehicle geometric state
S_t   = latent SAR scattering support
C_ti  = frozen candidate box i at frame t
A_t   = SAR aspect state: left / center / right / unknown
I_t   = identifiability state
K_t   = keyframe confidence
U_t   = uncertainty / ambiguity state
z_ti  = candidate-local SAR descriptor vector
L_cs  = center-size diagnostic likelihood
```

### `G_t`: Latent Vehicle Geometric State

Represents the physical vehicle geometry. It is not directly observed from a candidate box. Any claim about heading or orientation requires a separate rotated-OBB audit, not `axis_aligned_proxy_iou`.

### `S_t`: Latent SAR Scattering Support

Represents observed or latent SAR support that may be offset from `G_t`. It includes bright points, contrast, compactness, local background relation, and shadow/support behavior.

### `C_ti`: Frozen Candidate Box

Represents an existing candidate hypothesis. It may be scored or audited diagnostically, but this framework does not move, add, delete, or replace it.

### `A_t`: SAR Aspect State

Represents left / center / right / unknown aspect context. It is a diagnostic state derived only from inference-safe viewing context or held out for convention audit.

### `I_t` and `K_t`: Identifiability and Keyframe Confidence

`I_t` represents whether the frame is intrinsically identifiable under inference-safe evidence. `K_t` is a diagnostic confidence that a frame-candidate pair can act as a local soft anchor.

### `U_t`: Uncertainty State

Represents ambiguity from missingness, diffuse scatter, conflicting factors, weak descriptors, or uncertain aspect convention.

## 6. Evidence Layers

Evidence must be separated by availability and leakage risk.

### Inference-Safe / Pre-Eval Evidence

These fields may be used in diagnostic hypothesis construction if they exist before evaluation joins:

- frozen candidate geometry: `cx`, `cy`, `w`, `h`, optional stored `theta`;
- candidate id, target id, scene id, frame id, track id if pre-eval;
- candidate source / route metadata as grouping metadata only;
- optical-conditioned shell identity and prior context;
- vehicle size prior as a range;
- SAR crop descriptors computed from frozen candidate geometry;
- local background contrast and SAR energy statistics;
- frame order and local temporal context;
- missingness flags computed without final boxes or labels;
- predeclared diagnostic configuration.

### Diagnostic-Only / Post-Inference Evidence

These fields may be joined only after candidate scoring, descriptor extraction, or diagnostic hypothesis generation is frozen:

- GT boxes;
- A019 final boxes or manually finalized boxes;
- IoU;
- `axis_aligned_proxy_iou`;
- oracle best-candidate identity;
- center error;
- high-IoU bins;
- A021 condition, truncation, occlusion, visibility labels;
- final-box-derived fields;
- manual review outcomes;
- post-hoc failure buckets.

### Forbidden During Scoring

The following cannot select candidates, tune thresholds, choose anchors, choose routes, train weights, filter proposals, or define active factors:

- GT;
- IoU;
- `axis_aligned_proxy_iou`;
- oracle labels;
- center error;
- A019 final boxes;
- A021 condition / truncation / occlusion / visibility labels;
- final-box fields;
- manual review labels;
- any field derived from the above.

## 7. Factor Interaction Map

The framework is a diagnostic interaction map, not an active factor graph.

```text
frozen candidate C_ti
  -> local center-size likelihood
  -> candidate-local SAR descriptor
  -> aspect-sequence consistency
  -> identifiability / keyframe confidence
  -> local soft-anchor message
  -> apparent frame-to-frame consistency
  -> post-inference audit interpretation
```

### Diagnostic Factor Ownership

| Component | Owns | Must Not Own |
|---|---|---|
| `geometry_factor` | generic frozen candidate geometry plausibility | post-hoc center/size error |
| `sar_structure_factor` | local SAR support and structure evidence | A021 condition labels or final-box labels |
| `optical_temporal_factor` | optical-side temporal prior | SAR descriptor evolution |
| `transition_factor` | generic adjacent-frame continuity | keyframe identity or oracle correctness |
| `center_size_likelihood_candidate_refinement` | diagnostic center / size / interaction plausibility | candidate movement, candidate generation, active selection |
| `sar_aspect_sequence_factor` | descriptor evolution under aspect context | ordinary smoothing or heading correctness |
| `keyframe_anchor_factor` | local low-entropy soft-anchor message | hard lock, global propagation, final arbitration |
| `apparent_motion_consistency_factor` | apparent frame-to-frame candidate-state consistency | real speed or physical velocity |

Any term that cannot be assigned cleanly must be marked:

```text
HOLD_FOR_FIELD_AUDIT
```

## 8. Center-Size Likelihood As Local Precision Explanation

The center-size likelihood mechanism asks:

```text
Given frozen candidate (cx, cy, w, h),
how plausible is this center-size state under SAR patch evidence,
optical prior, scene prior, and temporal context?
```

Target form:

```text
p(cx, cy, w, h | SAR patch, optical prior, scene prior, temporal context)
```

Diagnostic log form:

```text
L_cs(i) =
    alpha_c * L_center(i)
  + alpha_s * L_size(i)
  + alpha_i * L_interaction(i)
  + alpha_o * L_optical_prior(i)
  + alpha_t * L_temporal_context(i)
  + alpha_m * L_missingness(i)
```

Potential normalized diagnostic concentration:

```text
q_cs(i | target, t) = exp(L_cs(i)) / sum_j exp(L_cs(j))
```

Interpretation:

- `L_center` explains whether SAR support agrees with candidate center.
- `L_size` explains whether SAR support and priors agree with width / height / extent.
- `L_interaction` explains whether center and size are jointly plausible.
- `L_optical_prior` keeps optical-to-SAR context as a weak prior.
- `L_temporal_context` provides local sequence support without hard propagation.
- `L_missingness` prevents unreliable evidence from masquerading as confidence.

The word `refinement` means research-understanding refinement. It does not mean candidate geometry modification.

Forbidden:

- move candidate centers;
- change width or height;
- add or delete candidates;
- replace A001;
- modify GM17 selector output;
- train weights;
- calibrate OOF;
- use post-inference audit labels during scoring.

## 9. SAR Aspect Sequence As Structure-Over-Time Explanation

SAR aspect sequence is not ordinary temporal smoothing.

Ordinary smoothing asks:

```text
Are neighboring boxes close?
```

SAR aspect sequence asks:

```text
Does candidate-local SAR scattering structure evolve coherently under aspect context?
```

Candidate-local descriptor vector:

```text
z_ti = [
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

Descriptor meanings:

- `E_left`, `E_center`, `E_right`: normalized energy in candidate-local subregions.
- `lr_asymmetry`: lateral imbalance under a declared local coordinate convention.
- `center_dominance`: share of energy concentrated in the center subregion.
- `mirror_symmetry`: left/right structural symmetry under the declared convention.
- `scatter_centroid_dx`, `scatter_centroid_dy`: SAR-energy centroid offset from candidate center, not GT center error.
- `scatter_compactness`: concentration of SAR support around local scatter centroid.
- `peak_count`: number of local SAR peaks under a frozen detector.
- `local_background_contrast`: contrast between candidate support and local background ring.

Aspect hypotheses:

| Aspect | Expected Diagnostic Pattern | Boundary |
|---|---|---|
| left | lateral asymmetry, shifted scatter centroid, weaker symmetry | not heading correctness |
| center | stronger center dominance, higher symmetry, compact support | possible identifiability signal |
| right | opposite-side lateral bias and structured descriptor change | not a mirror-validated orientation claim |
| unknown | weak confidence, ambiguous descriptors, missingness risk | no hard anchor |

Descriptor convention must be fixed before post-inference labels are joined. If convention is uncertain, mark `HOLD_FOR_CONVENTION_AUDIT`.

## 10. Identifiability And Keyframe Confidence

A keyframe should not be defined as a high-score frame. A high score can be wrong, over-smoothed, source-biased, or produced by an unstable factor interaction.

A better diagnostic definition is:

```text
keyframe = low-entropy / high-identifiability frame-candidate context
```

Identifiability increases when:

- candidate likelihood distribution is concentrated;
- center-size evidence agrees across components;
- SAR descriptor is clear;
- optical prior and SAR support do not conflict;
- descriptor missingness is low;
- factor disagreement is low;
- uncertainty is low;
- local sequence context is coherent without requiring hard propagation.

Diagnostic entropy:

```text
H_t = - sum_i q_cs(i | target, t) * log q_cs(i | target, t)
```

Identifiability:

```text
I_t = f(low H_t, factor agreement, descriptor clarity, low missingness, low uncertainty)
```

Keyframe confidence:

```text
K_t(i) = diagnostic confidence for candidate i at frame t
```

`K_t(i)` must be built from inference-safe or diagnostic-safe pre-eval evidence only. It cannot use GT, IoU, oracle identity, center error, A019, A021, condition labels, truncation labels, occlusion labels, final boxes, or manual review.

## 11. Local Soft Anchor And Apparent Motion

### Local Soft Anchor

A keyframe may act only as a local soft anchor. It can explain support for nearby frames, but it cannot force a decision.

Diagnostic message:

```text
M_anchor(t, i -> u, j) =
    K_t(i)
  * exp(-|u - t| / lambda_time)
  * S_descriptor(z_t(i), z_u(j))
  * S_apparent_motion(i, j, t, u)
  * G_missingness(t, u)
```

Required constraints:

- local window only: `|u - t| <= W_anchor`;
- decays with temporal distance;
- downweights missingness;
- never hard-locks a candidate;
- never copies candidate coordinates;
- never overwrites SAR evidence;
- never propagates globally;
- never forces the same candidate source.

### Apparent Frame-To-Frame Consistency

Use:

```text
apparent frame-to-frame consistency
```

Do not use:

```text
real speed
physical velocity
metric vehicle motion
```

The term asks whether candidate centers and descriptors change plausibly across local frame order under SAR / image coordinate context.

Allowed:

- local displacement plausibility in candidate coordinates;
- descriptor continuity;
- fan / azimuth context compatibility;
- optical prior movement as weak context;
- scatter-centroid shift consistency.

Forbidden:

- true speed claims;
- acceleration claims;
- GT displacement;
- final-box displacement;
- tuning from IoU or oracle labels.

## 12. Diagnostic-Only Pipeline

The unified Phase4-extension pipeline is:

1. High-IoU Precision Decomposition
2. Center-Size Likelihood Precision Audit
3. SAR Aspect Descriptor Separability
4. Keyframe Confidence Validity
5. Soft Anchor Propagation Simulation
6. Combined Diagnostic Interpretation

### Step 1: High-IoU Precision Decomposition

Purpose:

Separate weak high-IoU proxy performance into center-limited, size-limited, center-size combined, aspect / shape-hypothesis limited, future OBB audit, and proxy-metric limitation buckets.

Boundary:

`axis_aligned_proxy_iou` is post-inference AABB proxy only.

### Step 2: Center-Size Likelihood Precision Audit

Purpose:

Test whether inference-safe SAR, optical, scene, and temporal evidence can explain center-size plausibility over frozen candidates.

Boundary:

No candidate geometry modification and no active selector.

### Step 3: SAR Aspect Descriptor Separability

Purpose:

Check whether candidate-local SAR descriptors separate precise and imprecise hypotheses after descriptor extraction is frozen.

Boundary:

Post-hoc labels may evaluate separability but cannot define descriptors or thresholds.

### Step 4: Keyframe Confidence Validity

Purpose:

Audit whether low-entropy / high-identifiability keyframe hypotheses predict post-hoc precision after confidence is frozen.

Boundary:

Keyframes cannot be chosen from high-IoU labels, center error, A019, A021, or manual review.

### Step 5: Soft Anchor Propagation Simulation

Purpose:

Simulate whether local soft anchors explain neighboring frames without hard locks or global propagation.

Boundary:

No candidate override, no selector replacement, no propagation into mainline output.

### Step 6: Combined Diagnostic Interpretation

Purpose:

Connect candidate precision scarcity, local likelihood quality, SAR aspect structure, keyframe identifiability, and structured selection weakness.

Boundary:

No formal Phase5 approval and no mainline performance claim.

## 13. Leakage And Double-Counting Controls

### Leakage Controls

All inference-safe evidence must be frozen before post-inference audit labels are joined.

Forbidden during scoring:

- GT boxes;
- A019 final boxes;
- A021 condition / truncation / occlusion / visibility labels;
- IoU;
- `axis_aligned_proxy_iou`;
- oracle labels;
- center error;
- high-IoU bins;
- manual review labels;
- final-box-derived fields.

Allowed only after frozen scoring / descriptor extraction:

- audit IoU;
- center error;
- oracle identity;
- failure bucket;
- condition label;
- truncation / occlusion label;
- manual review note.

### Double-Counting Controls

The same evidence must not be counted under multiple names.

Risk cases:

- SAR contrast appears in both `sar_structure_factor` and descriptor quality;
- temporal continuity appears in both `transition_factor` and soft-anchor messages;
- optical prior appears in both `optical_temporal_factor` and center-size likelihood;
- geometry plausibility appears in both `geometry_factor` and center-size likelihood;
- keyframe confidence becomes hidden final arbitration.

Control rules:

- declare term ownership before audit;
- keep source/provenance fields as grouping metadata unless separately approved;
- mark ambiguous terms `HOLD_FOR_FIELD_AUDIT`;
- do not tune weights from post-hoc labels;
- do not report diagnostic factor outputs as selector outputs.

## 14. Stop / Hold / Go Gates

### STOP

Stop immediately if:

- GT / IoU / oracle / center error enters scoring;
- A019 / A021 / condition / truncation / occlusion / final-box fields enter inference;
- `axis_aligned_proxy_iou` is treated as rotated IoU;
- heading, orientation, or long-axis conclusions are inferred from AABB proxy;
- candidate geometry is moved;
- candidate bank is modified;
- GM17 selector is modified;
- keyframes hard-lock candidates;
- anchors propagate globally;
- SAR evidence is overwritten by temporal anchors;
- model training starts;
- OOF calibration starts;
- formal Phase5 is treated as approved.

### HOLD

Hold if:

- descriptor convention is uncertain;
- field origin cannot be proven;
- SAR descriptor extraction depends on final boxes;
- candidate source is used as a ranking shortcut;
- metric limitation dominates and a rotated-OBB audit is needed first;
- center-size likelihood components cannot be separated from existing geometry / SAR factors;
- keyframe confidence requires post-hoc labels;
- missingness policy is unclear.

### GO

Proceed to later diagnostic work only if:

- inference-safe fields are frozen;
- post-inference audit labels are joined only after scoring / descriptor extraction;
- missingness policy is explicit;
- factor ownership is declared;
- no selector change is required;
- no candidate-bank edit is required;
- no training or OOF calibration is required;
- output remains diagnostic-only.

## 15. Relationship To Formal Phase5

No route from this framework directly approves formal Phase5.

Formal Phase5 remains:

```text
BLOCKED_FOR_OOF_CALIBRATION
```

Formal Phase5 can be reconsidered only after separate governance accepts:

- stable field allowlist / denylist;
- leakage audit;
- double-counting audit;
- missing-value policy;
- separation of candidate precision bottleneck and structured selection bottleneck;
- diagnostic factor ownership;
- OOF calibration design and approval;
- release review.

This framework can produce research recommendations. It cannot self-approve calibration, selector changes, or mainline claims.

## 16. Open Questions

1. Is weak high-IoU precision mostly center-limited, size-limited, center-size combined, aspect / shape-limited, or proxy-metric limited?
2. Can SAR patch evidence support center-size likelihood without label leakage?
3. Are left / center / right aspect descriptors stable enough under a declared patch convention?
4. Can scatter centroid shift explain center bias without becoming a GT-derived correction?
5. Can keyframe confidence be defined by low entropy and factor agreement rather than high score?
6. Can local soft anchors explain neighboring-frame stabilization without hard propagation?
7. Does apparent frame-to-frame consistency add diagnostic value beyond `transition_factor` and `optical_temporal_factor`?
8. Does the fixed bank contain locally plausible states that structured selection misses?
9. If candidate precision scarcity dominates, what evidence is needed before any future candidate-bank discussion?
10. What separate rotated-OBB audit is required before heading, orientation, or long-axis claims become valid?
