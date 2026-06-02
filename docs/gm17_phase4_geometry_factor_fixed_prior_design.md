# GM17 Phase4A Geometry Factor Fixed-Prior Design

Date: 2026-06-02

Status: Phase4A geometry factor fixed-prior design note for human review. This document defines a research design only. It does not authorize experiments, inference runs, metrics, training, calibration, data-file modification, candidate-bank generation, candidate-bank modification, algorithm-code modification, executable scaffold creation, staging, commit, or push.

## 1. Purpose

This document defines `geometry_factor` as the first fixed-prior factor design for Phase4A.

The goal is to turn the geometry evidence exposed by GM17 into an interpretable node factor in the hierarchical factor graph. This is not experiment execution, not code implementation, not weight tuning, not calibration, and not a candidate-bank approval.

`geometry_factor` is scoped to complete-vehicle candidate geometry. It must evaluate candidate state fields only. It must not use SAR structure diagnostics, uncertainty diagnostics, final arbitration behavior, B patch fields, selected-reference behavior, or evaluation-only labels as inference evidence.

## 2. Why geometry_factor First

`geometry_factor` is the first Phase4A factor to design because it is the most basic complete-vehicle candidate node factor. Every later complete-vehicle factor depends on candidate geometry being interpretable and auditable.

It has the clearest local field support. A001 and A008 expose candidate identity, row/frame/track keys, center, size, heading, and fan-polar state fields. These fields are direct candidate-state fields rather than learned scores, selected outputs, or manual labels.

It does not require direction/source ownership mapping. `direction_factor` must separate signed posterior evidence from source-family trust, and `source_factor` must normalize source families. Geometry can be defined before those mappings.

It is the natural baseline before adding `optical_temporal_factor`, `direction_factor`, controlled non-visible `source_factor`, or `transition_factor`. A geometry-only design creates a reference point for later factor additions.

It also forces an early boundary decision with `sar_structure_factor`. Geometry can use explicit candidate coordinate/state fields, but it must not silently absorb shell, escape, support, ambiguity, or diagnostic SAR fields.

## 3. Research Hypothesis

Hypothesis:

```text
A candidate whose full-vehicle geometry is compatible with the SAR fan-polar state and expected complete-vehicle OBB state should receive lower fixed-prior cost than a candidate with inconsistent range, cross-range, azimuth, heading, size, or offset.
```

`geometry_factor` should evaluate candidate geometry only. It should not evaluate:

- SAR structure support;
- SAR ambiguity or artifact uncertainty;
- final arbitration or gate behavior;
- selected-reference behavior;
- GT agreement;
- IoU, center error, oracle rank, final annotation, condition label, truncation label, or occlusion label agreement.

The factor tests whether complete-vehicle candidate geometry has interpretable explanatory value under fixed priors before other evidence routes are added.

## 4. Graph Role

`geometry_factor` is a node factor.

It scores each candidate independently within a row/frame. The candidate node is identified by `candidate_id` and is tied to a row/frame context through `target_identity` and `sar_frame_num`.

`geometry_factor` is not:

- an edge factor;
- a track transition factor;
- a final release decision;
- a selector patch;
- a candidate generator;
- a candidate-bank approval mechanism;
- an evaluation metric.

It contributes a candidate-level geometry compatibility cost only if the candidate bank, field mappings, and allowlist are human-approved.

## 5. Evidence Sources

### GM17 evidence source

GM17 exposes candidate geometry through candidate-bank-like and candidate-factor tables. A001 contains direct candidate geometry fields. A008 contains candidate geometry fields plus diagnostic/refined fields.

GM17 is used here only as a staged feature and behavior source. It is not the final model template and not proof that the original weighted scoring architecture is correct.

### Literature grounding

External reconnaissance supports `geometry_factor` as a schema-grounded factor:

- SAR and remote-sensing OBB literature supports explicit center, size, and heading representation.
- SIVED and SAR vehicle OBB references support SAR vehicle geometry schema and oriented vehicle annotations.
- Rotated-object detection literature is useful as schema/protocol background for OBB state, angle convention, and ablation organization.

These sources do not authorize detector training, proposal generation, detector confidence as a factor score, learned weights, or candidate-bank expansion.

### Local observability

Locally observable candidate geometry fields include:

- `candidate_id`
- `target_identity`
- `sar_frame_num`
- `gm17_track_id`
- `cx`
- `cy`
- `w`
- `h`
- `heading`
- `r`
- `az`
- `cross`
- `delta_r_from_pred`
- `delta_cross_from_pred`
- `delta_az_from_pred`

A001 currently supports a GM_RM017-only pilot container. It does not support all-scene validation by itself because the raw scene audit found GM_RM011 and GM_RM019 raw/GT coverage without A001 candidate rows. A001 remains a candidate-bank candidate until human review accepts its scope and hash.

## 6. Allowed Inference-Safe Geometry Fields

Proposed geometry allowlist after human approval:

| field | role | status for geometry_factor | notes |
|---|---|---|---|
| `candidate_id` | candidate node identity | allowed after approval | Required to identify candidate nodes. |
| `target_identity` | row identity | allowed after approval | Proposed row key; mapping to `row_id` requires confirmation. |
| `sar_frame_num` | frame identity | allowed after approval | Numeric ordering is not needed for geometry-only scoring but should be validated. |
| `gm17_track_id` | track identity/context | allowed as metadata after approval | Geometry-only scoring must not use transition behavior. |
| `cx` | candidate center x | allowed after approval | Candidate center only; never substitute `final_cx`. |
| `cy` | candidate center y | allowed after approval | Candidate center only; never substitute `final_cy`. |
| `w` | candidate width | allowed after approval | Must be positive and unit-reviewed. |
| `h` | candidate height | allowed after approval | Must be positive and unit-reviewed. |
| `heading` | candidate OBB heading | allowed after approval | Degree/radian and sign convention require human review. |
| `r` | fan-polar range state | allowed after approval | Candidate-state field. |
| `az` | fan-polar azimuth state | allowed after approval | Coordinate convention requires review. |
| `cross` | fan-polar cross-range state | allowed after approval | Coordinate convention requires review. |

Delta fields require separate ownership review:

| field | possible role | current decision | risk |
|---|---|---|---|
| `delta_r_from_pred` | candidate offset from temporal prediction in range | defer until ownership review | May belong to `geometry_factor` or `optical_temporal_factor`. |
| `delta_cross_from_pred` | candidate offset from temporal prediction in cross-range | defer until ownership review | May duplicate optical-temporal soft-prior evidence. |
| `delta_az_from_pred` | candidate offset from temporal prediction in azimuth | defer until ownership review | Needs coordinate and temporal-origin review. |

Design decision:

Use explicit candidate geometry fields first. Treat `delta_*` fields as boundary fields until human review assigns them to `geometry_factor` or defers them to `optical_temporal_factor`.

## 7. Excluded Fields

The following fields or prefixes must not enter `geometry_factor` inference inputs, factor selection, cost construction, missing-value policy, or inference outputs:

- `final_*`
- `gt_*`
- `oracle_*`
- `candidate_iou`
- `rot_iou`
- `center_err_px`
- `candidate_center_err_px`
- `selected_iou`
- `selected_center_err_px`
- `condition_type`
- `truncation_degree`
- `occlusion_degree`
- `visible_factor`
- visible support fields
- `source_prior`
- `node_score`
- `path_score`
- `two_stage_gate_*`
- `patch_action`
- B patch fields such as `patch_variant`, `patch_triggered`, `sar_uncertainty_penalty_triggered`, `direction_veto_triggered`, and `bpatch_candidate_id`

The following fields are blocked from active geometry use until another audit transfers ownership:

- `refined_geometry_score`
- `geometry_escape_refined_score`
- `directional_shell_score`
- `track_escape_evidence`
- `escape_conflict_score`

Reason:

These diagnostic/refined fields overlap with `sar_structure_factor`, `uncertainty_factor`, or `final_arbitration_factor`. They may encode SAR shell support, escape evidence, ambiguity, artifact behavior, source support, or selector actions. They are not part of the first geometry fixed-prior design.

## 8. Geometry State Definition

Design-level candidate geometry state:

```text
geometry_state(c) = {
  candidate_id,
  target_identity,
  sar_frame_num,
  gm17_track_id,
  center = (cx, cy),
  size = (w, h),
  heading,
  fan_polar_state = (r, az, cross)
}
```

Coordinate roles:

- `cx` and `cy` are candidate center coordinates.
- `final_cx` and `final_cy` are eval-only GT/manual annotation fields and are not part of inference.
- `w` and `h` are candidate size fields.
- `heading` is candidate OBB heading; degree/radian and sign convention must be reviewed before implementation.
- `r`, `az`, and `cross` are fan-polar candidate geometry fields.
- `target_identity` identifies the row/sample context.
- `sar_frame_num` identifies the SAR frame context.
- `gm17_track_id` may be used as context metadata but not as transition evidence in geometry-only design.

The geometry state is complete-vehicle oriented. It does not represent visible fragments, missing extent, partial support, or near-field regime state.

## 9. Fixed-Prior Potential Design

This section defines possible fixed-prior components without implementation, learned weights, fitted parameters, or GT-derived thresholds.

| component | meaning | input fields | decision | risk |
|---|---|---|---|---|
| size plausibility potential | Candidate size should be physically plausible for the complete-vehicle prior. | `w`, `h` | allowed at design level | Needs valid ranges from human review or predeclared domain prior, not GT fitting. |
| heading plausibility potential | Candidate heading should be valid under the declared OBB angle convention. | `heading` | allowed at design level | Angle wraparound and sign convention must be explicit. |
| fan-polar consistency potential | Candidate fan-polar state should be internally valid and coordinate-convention-consistent. | `r`, `az`, `cross` | allowed at design level | Must not import SAR shell support or direction posterior evidence. |
| candidate-center plausibility potential | Candidate center should be a valid image/SAR-frame coordinate if frame bounds are available and approved. | `cx`, `cy` | allowed at design level only if bounds are part of approved manifest | Bounds must not be inferred from GT boxes or eval labels. |
| temporal-prediction offset potential | Candidate offset from temporal prediction may support geometry/temporal compatibility. | `delta_r_from_pred`, `delta_cross_from_pred`, `delta_az_from_pred` | deferred | Likely overlaps `optical_temporal_factor`; ownership must be decided first. |

Design constraints:

- No learned weights.
- No fitted parameters.
- No thresholds computed from GT, IoU, center error, oracle fields, final annotations, or condition labels.
- No detector confidence.
- No selected-reference scores.
- No SAR structure diagnostics.

If symbolic notation is used later, it should stay design-level, for example:

```text
cost_geometry(c) = fixed_combine(
  cost_size(c),
  cost_heading(c),
  cost_fan_polar(c),
  optional cost_center_validity(c)
)
```

The `fixed_combine` rule must be predeclared and must not be tuned from evaluation outcomes.

## 10. Cost Transform Principles

Design-level rules:

- Lower cost means stronger geometry compatibility.
- Cost must be monotonic with geometric inconsistency for each approved component.
- Component costs must be clipped or capped so one geometry component cannot dominate all others unless that domination rule is explicitly declared.
- Missing values must produce a declared fallback cost or block the factor for that row.
- Invalid geometry, such as nonpositive `w` or `h`, should be flagged.
- Angle wraparound must be handled explicitly.
- No eval-only label may influence potential, cost, clipping, missing-value policy, factor inclusion, or output schema.
- No calibration, OOF split, learned weight, metric-tuned coefficient, or experiment result may alter fixed-prior costs.

A generic symbolic transform may be:

```text
cost_component = -log(clip(potential_component, eps, 1.0))
```

This is a design principle only. It does not define an executable formula or parameter value.

## 11. Missing Value And Valid Range Policy

Required policy decisions:

| condition | proposed Phase4A policy | rationale |
|---|---|---|
| missing `cx` or `cy` | block `geometry_factor` for that candidate and emit diagnostic flag | Center is required for complete-vehicle geometry. |
| missing `r`, `az`, or `cross` | block fan-polar component; if center/size/heading are valid, candidate may receive partial geometry with missing-field flag only if human review allows partial cost | Fan-polar geometry is central, but all-or-nothing behavior must be predeclared. |
| missing `heading` | assign declared high cost or block heading component; do not infer from GT/final fields | Heading convention is part of OBB geometry. |
| missing `w` or `h` | block size component and flag candidate; do not infer from GT/final fields | Size is required for complete-vehicle OBB state. |
| invalid `w` or `h` where value is `<= 0` | block candidate geometry or assign maximum declared geometry cost | Nonpositive size is invalid geometry. |
| angle convention mismatch | block heading component until convention is resolved | Mixed heading conventions can invert geometry evidence. |
| NaN or infinite numeric value | block affected component and emit diagnostic flag | Nonfinite values cannot be scored safely. |
| out-of-range but finite `cx`/`cy` if image bounds are approved | assign high cost or block center-validity component according to predeclared policy | Must be based on approved frame bounds, not GT labels. |
| out-of-range but finite `r`/`az`/`cross` | assign high cost or block fan-polar component according to predeclared policy | Requires approved coordinate ranges. |

Neutral cost should be used sparingly. A neutral fallback is acceptable only for optional components. Required state fields should block the affected component or candidate path according to the predeclared policy.

## 12. Geometry vs SAR Structure Ownership Boundary

This is the critical boundary for `geometry_factor`.

`geometry_factor` owns candidate coordinate and state plausibility:

- candidate center;
- candidate size;
- candidate heading;
- candidate fan-polar state;
- approved validity/range checks over explicit candidate state fields.

`sar_structure_factor` owns SAR support, shell evidence, escape evidence, structural ambiguity, artifact evidence, and support-vs-uncertainty diagnostics. It remains diagnostic-only in Phase4A.

`geometry_factor` must not silently absorb:

- `directional_shell_score`
- `geometry_escape_refined_score`
- `track_escape_evidence`
- `escape_conflict_score`
- `P_ambiguous`
- `P_artifact`
- `E_sar_structure`
- `E_uncertainty`
- SAR uncertainty routing fields
- B patch or final arbitration fields

Ownership rule:

```text
geometry_factor may use explicit candidate state fields only unless a later audit transfers a diagnostic field into geometry with declared ownership, leakage class, cost transform, and double-counting controls.
```

Until that transfer occurs, shell/escape/refined diagnostic fields remain excluded from active geometry scoring.

## 13. Geometry-Only Ablation Role

The geometry-only design will serve as the first fixed-prior baseline.

Its scientific role is to test whether complete-vehicle candidate geometry alone provides interpretable candidate-selection evidence under a frozen candidate container. It does not claim final performance and does not prove the full model.

It becomes the reference before adding:

- `optical_temporal_factor`;
- `direction_factor`;
- controlled non-visible `source_factor`;
- `transition_factor`.

It also helps detect double-counting. If later factors improve behavior, their contribution can be interpreted only against a clean geometry baseline. If later gains come from fields that geometry should already own, or from diagnostic SAR structure fields, the factor graph is not clean.

This document does not execute the ablation.

## 14. Expected Future Artifacts

Future artifacts that may be created in separate authorized rounds:

- `geometry_factor` config section;
- geometry allowlist;
- geometry cost schema;
- geometry missing-value policy;
- geometry diagnostic report;
- geometry-only inference output schema;
- post-inference evaluation join plan.

These artifacts are not created in this round.

## 15. Human Review Questions

The researcher should decide:

- Are `cx` and `cy` accepted as candidate `center_x` and `center_y`?
- Are `r`, `az`, and `cross` accepted as fan-polar geometry fields?
- Is `heading` in degrees, and what is the sign convention?
- Are `w` and `h` fixed vehicle priors or candidate-specific geometry?
- Should `delta_r_from_pred`, `delta_cross_from_pred`, and `delta_az_from_pred` belong to `geometry_factor` or `optical_temporal_factor`?
- Should `refined_geometry_score` and `geometry_escape_refined_score` remain diagnostic-only?
- Should `directional_shell_score`, `track_escape_evidence`, and `escape_conflict_score` remain in `sar_structure_factor` diagnostics?
- What valid ranges should be used before any scaffold implementation?
- Should invalid `w`/`h` block a candidate or assign maximum geometry cost?
- Should missing fan-polar fields block the whole geometry factor or only the fan-polar component?
- Should the first pilot be geometry-only on the GM_RM017 candidate container?

## 16. Recommended Next Round

Recommended next round:

```text
optical_temporal_factor soft-prior design note
```

Condition:

This is the preferred next round if human review accepts the geometry ownership rule and keeps `delta_*` fields either excluded or explicitly deferred to `optical_temporal_factor`.

Reason:

`optical_temporal_factor` is the next ready fixed-prior factor, but it must remain soft-prior-only and must not generate or overwrite full center. Designing it after geometry clarifies whether temporal prediction offsets belong to geometry or temporal ownership.

Alternative next round:

```text
geometry factor config/manifest design
```

Use this alternative only if the user wants to prepare a scaffold manifest after human approval of geometry field mappings, valid ranges, missing-value policy, and the A001 GM_RM017 pilot scope.

Do not recommend running experiments yet.
