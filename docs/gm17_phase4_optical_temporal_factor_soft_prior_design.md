# GM17 Phase4 Optical Temporal Factor Soft-Prior Design

Status: Phase4A research design note only. It defines `optical_temporal_factor` as an interpretable fixed-prior soft factor. It does not authorize experiments, inference, metrics, training, calibration, code changes, data-file changes, candidate-bank generation or modification, GM17 mainline replacement, staging, commit, or push.

GM17 remains a staged evidence and feature/behavior source, not the final model template. A001 remains a GM_RM017-only pilot container candidate unless human review accepts its scope and hash. B patch behavior remains diagnostic consistency evidence only, not physical-model proof.

## 1. Purpose

This document defines `optical_temporal_factor` as the second Phase4A fixed-prior design target after `geometry_factor`.

The role of this factor is to ask whether optical-side temporal prediction provides interpretable soft support for selecting among already existing SAR candidates. It is a research design note only. It does not execute an experiment, produce an inference output, compute a metric, fit a weight, calibrate a threshold, or modify the candidate bank.

The output of this round is only the design boundary: allowed fields, excluded fields, ownership decisions, missing-value behavior, and the relationship between optical temporal evidence, geometry, and transition.

## 2. Why optical_temporal_factor After geometry_factor

`geometry_factor` comes first because it defines the intrinsic candidate state: fan-polar location, OBB-like size and heading, and candidate-level geometry fields. Without that state definition, optical temporal evidence has nothing clean to compare against.

`optical_temporal_factor` follows geometry because it is a cross-modal temporal support term over candidate state. It should compare an existing candidate's SAR fan-polar state with the optical-side prediction for the same target/frame. It should not generate the SAR center, overwrite candidate geometry, or decide that the temporal prediction itself is the full-vehicle SAR localization.

The ordering also resolves a known boundary from the geometry design. `delta_r_from_pred`, `delta_cross_from_pred`, and `delta_az_from_pred` are prediction-relative fields, so they need explicit ownership before any two-factor model is designed. If geometry owns only intrinsic candidate state, then prediction-relative offsets naturally belong to optical temporal compatibility.

## 3. Research Hypothesis

The Phase4A hypothesis for `optical_temporal_factor` is:

```text
An SAR candidate whose fan-polar state is compatible with the optical-side temporal prediction should receive lower fixed-prior cost than a candidate that deviates strongly from the temporal prior, provided the temporal prior remains soft and does not generate, overwrite, or force a SAR full-vehicle center.
```

This factor supports candidate selection over a frozen bank. It is not candidate generation. A candidate absent from the bank cannot be created by the temporal prior, and a bank candidate cannot be shifted into place by the temporal prior.

## 4. Graph Role

`optical_temporal_factor` is a node/row-level soft-prior factor. For each candidate row, it scores compatibility between the candidate's existing SAR state and the optical-to-SAR temporal prediction for the same target/frame.

It is not:

- an edge transition factor;
- a Viterbi path smoother;
- a final release gate;
- a candidate generator;
- a full-center generator;
- a learned registration module;
- a calibration model.

The graph meaning is local candidate compatibility. Track-level context may provide the prediction, but the factor's cost is attached to the candidate node or row, not to an edge between adjacent candidate nodes.

## 5. Evidence Sources

### GM17 evidence source

GM17 exposes temporal prediction and temporal factor fields through A005 `gm17_temporal_inference.csv` and related candidate tables. A001 `candidate_bank_inference.csv` contains candidate rows with `temporal_factor_score` and prediction-relative deltas. A008 `candidate_refined_factor_inference.csv` contains `optical_temporal_consistency_score` in a joined candidate-factor table. A013 `track_viterbi_selected_inference.csv` is selected-behavior reference only and must not become a scoring input.

These are staged evidence sources. They can inform field mapping and behavior decomposition, but they do not make GM17 the final model template.

### Literature grounding

External reconnaissance found that optical-SAR matching and cross-modal localization literature supports the idea of a soft prior and supports alignment-failure interpretation. However, most direct optical-SAR matching work uses learned registration, learned correspondence, domain adaptation, or supervised matching objectives. Those methods are future learning/calibration background, not direct Phase4 fixed-prior scoring.

Tracking and temporal consistency literature supports temporal context, MAP/Viterbi reasoning, and path-level selection over fixed candidates. That evidence is relevant to `transition_factor`, but it must not be confused with `optical_temporal_factor`. In this note, temporal prediction compatibility is a row-level prior; transition continuity is a separate edge factor to be designed later.

### Local observability

Local document-level previews show the following relevant observable fields:

- temporal prior fields: `pred_r`, `pred_cross`, `pred_az`, `pred_cx`, `pred_cy`, `pred_w`, `pred_h`, `pred_heading_deg`, `temporal_factor_score`;
- candidate compatibility fields: `candidate_id`, `r`, `cross`, `az`, `delta_r_from_pred`, `delta_cross_from_pred`, `delta_az_from_pred`, `optical_temporal_consistency_score`;
- join/context fields: `target_identity`, `sar_frame_num`, `gm17_track_id`.

A005 supports a temporal soft-prior design after human approval. A001 currently supports only a GM_RM017 pilot container; it does not by itself establish a full GM_RM011/GM_RM017/GM_RM019 Phase4 bank.

## 6. Allowed Optical-Temporal Fields

Proposed allowed fields after human approval:

| field | intended use | allowed now or deferred | risk |
|---|---|---|---|
| `target_identity` | Join temporal prior to candidate rows for the same target/frame. | allowed after join-key approval | Wrong join would attach a temporal prior to the wrong target. |
| `sar_frame_num` | Frame identity and ordering context for temporal prior lookup. | allowed after frame mapping approval | Must not become an eval grouping label or hidden transition edge. |
| `gm17_track_id` | Track grouping context for the temporal prediction source. | allowed after track mapping approval | May blur node prior with track transition if reused for edge costs. |
| `pred_r` | Optical-side temporal prediction in SAR fan-polar range. | allowed after A005 approval | Soft prior only; cannot generate or replace candidate range. |
| `pred_cross` | Optical-side temporal prediction in SAR cross-range offset. | allowed after A005 approval | Coordinate convention must be confirmed. |
| `pred_az` | Optical-side temporal prediction in SAR azimuth. | allowed after A005 approval | Coordinate convention and units must be confirmed. |
| `temporal_factor_score` | Existing temporal support score from GM17 evidence. | allowed only as soft prior after ownership review | Could copy GM17 behavior if used as an opaque score without decomposition. |
| `candidate_id` | Candidate identity for row-level compatibility. | allowed after candidate-bank approval | Candidate stability and uniqueness must be confirmed. |
| `r` | Candidate fan-polar range to compare with `pred_r`. | allowed after candidate-bank approval | Geometry field; temporal factor may only read it for comparison. |
| `cross` | Candidate cross-range offset to compare with `pred_cross`. | allowed after candidate-bank approval | Geometry field; must not be redefined by temporal prior. |
| `az` | Candidate azimuth to compare with `pred_az`. | allowed after candidate-bank approval | Geometry field; units/sign must be confirmed. |
| `delta_r_from_pred` | Candidate range deviation from temporal prediction. | allowed for `optical_temporal_factor` after origin approval | Must not be counted again by geometry unless ownership is transferred. |
| `delta_cross_from_pred` | Candidate cross-range deviation from temporal prediction. | allowed for `optical_temporal_factor` after origin approval | High double-counting risk if geometry also uses it. |
| `delta_az_from_pred` | Candidate azimuth deviation from temporal prediction. | allowed for `optical_temporal_factor` after origin approval | Needs coordinate and angular wrap policy. |
| `pred_cx` | Image-space prediction x coordinate. | deferred | Risk of acting as direct center generator. |
| `pred_cy` | Image-space prediction y coordinate. | deferred | Risk of overwriting SAR candidate center. |
| `pred_w` | Predicted box width. | deferred | Could become learned or optical size prior without approval. |
| `pred_h` | Predicted box height. | deferred | Could force candidate size instead of scoring compatibility. |
| `pred_heading_deg` | Predicted heading. | deferred | Heading convention and source ownership unclear. |
| `optical_temporal_consistency_score` | Candidate-level temporal consistency in A008. | deferred until joined-table ownership approval | May duplicate `temporal_factor_score` or transition smoothness. |

The core design should start with `pred_r`, `pred_cross`, `pred_az`, candidate `r`, `cross`, `az`, and the three `delta_*_from_pred` fields if their field origins are accepted.

## 7. Fields That Must Not Be Used

The following fields, prefixes, and field families must not enter `optical_temporal_factor` scoring, missing-value policy, threshold choice, factor inclusion, candidate generation, path construction, or inference outputs:

- `final_*`;
- `gt_*`;
- `oracle_*`;
- `candidate_iou`;
- `rot_iou`;
- `center_err_px`;
- `candidate_center_err_px`;
- `selected_iou`;
- `selected_center_err_px`;
- `condition_type`;
- `truncation_degree`;
- `occlusion_degree`;
- `visible_factor`;
- visible support fields;
- `source_prior`;
- `node_score`;
- `path_score`;
- `two_stage_gate_*`;
- `patch_action` and B patch fields;
- selected-reference fields from A013.

Learned optical-SAR registration confidence is also excluded unless a future learning/calibration phase explicitly approves it. Correspondence labels, alignment labels, learned matching logits, detector confidence, and evaluation-derived agreement scores are not Phase4A fixed-prior evidence.

## 8. Soft-Prior Boundary

`optical_temporal_factor` may reward compatibility with a temporal prior, but it must not generate, overwrite, or shift the SAR candidate center.

The factor should compare existing candidate states to temporal prediction:

```text
candidate_state = {r, cross, az}
temporal_prior = {pred_r, pred_cross, pred_az}
compatibility = declared function of candidate_state versus temporal_prior
```

It must not:

- create new candidates;
- replace candidate geometry;
- move candidate `cx`/`cy`, `r`, `cross`, or `az`;
- turn `pred_cx`/`pred_cy` into the selected center;
- use manual GT to adjust the temporal prior;
- use final annotations or evaluation errors to tune temporal thresholds;
- use temporal support as a hard release gate.

If temporal evidence is missing or invalid, the design should disable or neutralize the temporal factor according to a predeclared policy rather than force a candidate decision.

## 9. Delta Field Ownership

This note recommends assigning the prediction-relative delta fields to `optical_temporal_factor`:

- `delta_r_from_pred`;
- `delta_cross_from_pred`;
- `delta_az_from_pred`.

Reason: these fields measure deviation from temporal prediction, not intrinsic candidate geometry. Candidate `r`, `cross`, and `az` are geometry-owned state fields. The delta fields are compatibility measurements between that state and the optical-side temporal prior.

This ownership prevents `geometry_factor` from silently absorbing optical temporal evidence. If any `delta_*_from_pred` field is later moved to `geometry_factor`, a separate ownership audit is required. That audit must explain why prediction-relative evidence is geometry rather than temporal support, and how double-counting with `optical_temporal_factor` is prevented.

## 10. Fixed-Prior Potential Design

The following components are design-level candidates only. No learned weights, fitted thresholds, GT-derived constants, or metric-tuned cutoffs are assigned here.

| component | meaning | input fields | allowed/deferred status | risk |
|---|---|---|---|---|
| fan-polar temporal distance potential | Candidate fan-polar state is close to optical-side temporal prediction. | `r`, `cross`, `az`, `pred_r`, `pred_cross`, `pred_az` | allowed after field and coordinate approval | Must be clipped so it cannot overpower geometry. |
| temporal score potential | Existing temporal support score contributes a soft prior. | `temporal_factor_score` | allowed only after score-origin review | Opaque score may copy GM17 behavior. |
| candidate-to-prediction offset potential | Explicit offsets are converted into compatibility cost. | `delta_r_from_pred`, `delta_cross_from_pred`, `delta_az_from_pred` | recommended for optical temporal ownership after origin approval | Must not also be counted by geometry. |
| prediction-validity gate | Invalid temporal predictions disable or neutralize the factor. | `pred_status` if approved | deferred until `pred_status` policy is accepted | Bad gate design can become a hard rejection mechanism. |
| temporal consistency potential | Joined candidate-level consistency supports compatibility. | `optical_temporal_consistency_score` | deferred until A008 ownership approval | May duplicate temporal score or transition smoothness. |

Symbolic design form:

```text
temporal_cost = clipped_cost(distance_or_score(candidate_state, temporal_prior))
```

The function and constants must be predeclared before any future execution. They must not be fit from GT, IoU, center error, selected-candidate agreement, or calibration outcomes.

## 11. Cost Transform Principles

Design-level rules:

- Lower cost means stronger compatibility with the temporal prior.
- Cost must increase monotonically with candidate-prediction deviation.
- Cost must be clipped or capped so temporal evidence cannot overpower geometry or act as a hard gate.
- Temporal prior must remain soft; a large deviation can raise cost but should not automatically block a candidate unless a separate, approved invalidity rule exists.
- Missing prediction should follow declared fallback behavior.
- Invalid prediction should disable or neutralize the temporal factor.
- No eval-only label may influence cost, clipping, transform choice, missing-value behavior, or threshold choice.
- No calibration, learned weight, OOF split, ranker, CRF, or metric-tuned scalar is allowed.

Acceptable symbolic examples:

```text
distance_temporal = norm([delta_r, delta_cross, wrapped_delta_az])
support_temporal = monotone_decreasing(distance_temporal)
cost_temporal = -log(clip(support_temporal, eps, max_support))
```

These are formulas for design discussion only. They are not executable scaffold code and do not assign numeric thresholds.

## 12. Missing Value And Valid Range Policy

Proposed policy before human review:

| condition | proposed behavior | rationale |
|---|---|---|
| Missing `pred_r`, `pred_cross`, or `pred_az` | Disable temporal factor for the row and assign neutral cost; emit diagnostic flag. | Temporal prior is absent, so it should not help or hurt a candidate. |
| Missing one `delta_*_from_pred` field while raw candidate and prediction fields exist | Recompute is not allowed in this document; mark field incomplete and use raw state comparison only if future design approves it. Otherwise neutralize temporal factor and flag. | Avoid silent ad hoc derivation or partial scoring. |
| Missing all `delta_*_from_pred` fields | Use direct candidate-vs-prediction state comparison only after implementation design approval; otherwise neutral cost and diagnostic flag. | Keeps this note non-executable and prevents hidden transforms. |
| Missing `temporal_factor_score` | Do not use score potential; allow explicit offset potential if approved, otherwise neutral temporal cost. | Opaque score is optional, not required. |
| `pred_status` not `ok` | Deferred policy: preferred behavior is disable or neutralize the temporal factor and emit diagnostic flag. | Invalid prediction should not become a hard candidate veto without approval. |
| Nonfinite temporal fields | Disable temporal factor for the row and emit diagnostic flag; block only the temporal factor, not the candidate row. | Nonfinite values are unsafe as costs. |
| Inconsistent frame/track join | Block temporal factor use for affected rows and emit diagnostic flag. | Wrong temporal joins are leakage-like errors. |
| Temporal prior absent for a candidate row | Neutral temporal cost and diagnostic flag. | Candidate geometry remains available; temporal evidence is simply absent. |
| Candidate exists without temporal prior | Keep candidate available to other factors; disable temporal cost. | Temporal factor is support, not candidate-bank authority. |

High cost should be reserved for valid predictions that are strongly incompatible under a predeclared transform. Missing or invalid temporal evidence should normally produce neutral cost or factor disablement, not punishment, because punishing absence would turn an optional prior into a hidden gate.

## 13. Optical Temporal vs Geometry Ownership Boundary

`geometry_factor` owns intrinsic candidate geometry:

- candidate `cx`, `cy`;
- candidate `w`, `h`;
- candidate `heading`;
- candidate `r`, `cross`, `az`;
- coordinate validity and candidate-state plausibility.

`optical_temporal_factor` owns deviation from optical-side temporal prediction:

- `pred_r`, `pred_cross`, `pred_az`;
- prediction-validity context if approved;
- `delta_r_from_pred`, `delta_cross_from_pred`, `delta_az_from_pred`;
- temporal compatibility cost over existing candidate state.

Geometry should not use temporal prediction offsets unless another audit transfers ownership. Optical temporal may read geometry-owned candidate state only to compute compatibility; it must not redefine geometry or shift the candidate.

## 14. Optical Temporal vs Transition Ownership Boundary

`optical_temporal_factor` is a node/row-level soft prior relative to the optical-to-SAR temporal prediction for that target/frame.

`transition_factor` is an edge factor between adjacent candidate states. It should score continuity across neighboring frames within a track after candidate nodes are defined.

Both factors can reward smoothness. That creates a double-counting risk:

- optical temporal may reward a candidate because it agrees with a predicted temporal trend;
- transition may reward adjacent candidates because their states are smooth.

The ownership rule is that optical temporal compares one candidate to a prediction, while transition compares one candidate to another candidate in an adjacent frame. Transition should not be introduced until optical temporal ownership is stable and the design can show that the two costs do not reward the same hidden signal twice.

## 15. Optical Temporal-Only And Geometry+Temporal Ablation Role

Future testing, if separately authorized, should include:

- `optical_temporal_only`: test whether the temporal prior alone has interpretable candidate-selection signal without geometry or edge transition.
- `geometry_only`: preserve the first baseline for intrinsic candidate geometry.
- `geometry_plus_optical_temporal`: test whether temporal prediction adds evidence beyond geometry.

The scientific role is not to chase a metric in this document. The role is to determine whether optical-side temporal prediction contributes an independent, interpretable soft prior. The ablations should reveal:

- whether temporal prior adds signal beyond geometry;
- whether temporal prior is just copying GM17 selected behavior;
- whether temporal prior conflicts with plausible SAR candidate geometry;
- whether temporal evidence over-stabilizes wrong candidates;
- whether missing or invalid temporal predictions are common enough to require redesign.

No future ablation should use eval-only fields in inference. Evaluation labels may be joined only after inference outputs already exist.

## 16. Expected Future Artifacts

Future approved rounds may create the following artifacts, but this document does not create them:

- `optical_temporal_factor` config section;
- optical temporal allowlist;
- temporal cost schema;
- temporal missing-value policy;
- geometry plus temporal ablation manifest;
- post-inference evaluation join plan;
- temporal conflict diagnostic report.

Any future artifact must preserve the frozen candidate-bank boundary, inference/evaluation separation, no learned weights, no OOF calibration, and no activation of diagnostic-only or future factors.

## 17. Human Review Questions

- Should `delta_r_from_pred`, `delta_cross_from_pred`, and `delta_az_from_pred` be assigned to `optical_temporal_factor`?
- Is `pred_r`/`pred_cross`/`pred_az` the preferred temporal prior state?
- Are `pred_cx`/`pred_cy` allowed only as diagnostic context, or can they be used as soft candidate compatibility fields?
- Should `temporal_factor_score` be used directly, or should it be decomposed into explicit offset costs?
- What should happen when `pred_status` is not `ok`?
- Should missing temporal prior produce neutral cost or disable the factor?
- How should optical temporal conflict with geometry be diagnosed?
- Should `optical_temporal_factor` be designed before direction/source ownership audit?

## 18. Recommended Next Round

Recommended next round:

```text
direction/source ownership audit
```

Reason: after geometry and optical temporal ownership are separated, the next major double-counting risk is between `direction_factor` and controlled non-visible `source_factor`. Source-family trust can silently encode direction, geometry, or SAR-structure assumptions unless ownership is declared.

Alternative next round:

```text
geometry + optical_temporal combined fixed-prior design note
```

This alternative is reasonable if the researcher wants to define the first two-factor model before direction/source. It should still remain a design note only.

Do not recommend running experiments yet. Phase4 execution remains blocked until the candidate bank, manifest, allowlist, denylist, factor ownership, missing-value policy, clipping policy, and inference/evaluation separation gates are accepted by human review.
