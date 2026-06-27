# GM17 Phase4 Line B Combined Geometry + Optical Temporal Design Note

Date: 2026-06-28

Status: non-executable combined design note for human review. This document does not authorize experiments, candidate selection, metric computation, threshold tuning, learned weights, calibration, candidate-bank generation, candidate-bank modification, A001/A005 joins that create derived datasets, GT joins, YAML/script/notebook scaffolding, staging, commit, or push.

## 1. Current Position

Line B is currently:

```text
GM_RM017-only optical-to-SAR candidate-level pilot
```

The active design surface is deliberately narrow:

- A001 provides existing SAR candidate boxes and candidate states.
- A005 provides optical temporal soft predictions.
- `geometry_factor` may use approved A001 candidate-state fields.
- `optical_temporal_factor` may use approved A005 fan-polar prediction fields to compare against existing A001 candidate states.

This note is not an execution design. It defines field ownership, component responsibilities, missing/conflict policy direction, and human approval questions before any future implementation design. It does not choose candidates and does not compute performance.

## 2. Design Goal In Plain Language

The intended Line B question is:

```text
Among existing GM_RM017 SAR candidates in A001,
can a fixed geometry component and a soft optical temporal component
provide a defensible candidate-level prior?
```

The intended design is not:

- generating new SAR candidates;
- expanding A001;
- filtering A001;
- using A005 to overwrite candidate centers;
- using GT to pick the answer;
- training a ranker;
- copying selected-reference behavior;
- turning temporal prior into a hard lock.

A useful mental model is:

```text
A001 = existing menu of SAR candidate boxes.
A005 = soft optical-temporal suggestion in SAR fan-polar space.
Line B = compare existing menu items against geometry and soft temporal consistency.
```

## 3. Approved Context Inputs

This note depends on two prior non-executable documents:

- `docs/gm17_phase4_geometry_temporal_manifest_allowlist_denylist.md`
- `docs/gm17_phase4_lineB_A001_A005_field_inventory.md`

The field inventory established:

| asset | rows | columns | current role |
|---|---:|---:|---|
| A001 `candidate_bank_inference.csv` | 58251 | 24 | Fixed GM_RM017 candidate bank candidate. |
| A005 `gm17_temporal_inference.csv` | 205 | 25 | GM_RM017 optical temporal soft prior. |

Core fields present:

| group | fields | present where |
|---|---|---|
| A001 geometry | `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross` | A001 |
| A005 temporal fan-polar prediction | `pred_r`, `pred_cross`, `pred_az` | A005 |
| candidate join-key candidates | `target_identity`, `scene`, `sar_frame`, `sar_frame_num`, `gm17_track_id` | A001 and A005 |
| candidate identity | `candidate_id` | A001 only |

No forbidden-looking column names were found in A001/A005 by the prior field-name scan for `final_*`, `gt_*`, `iou`, `center_err`, `oracle`, `selected`, `condition`, `truncation`, or `occlusion`.

## 4. Strict Non-Execution Boundary

This note must not be read as permission to run Line B.

Blocked actions:

- no candidate selection;
- no IoU, center error, recall, rank, oracle rank, or metric computation;
- no threshold tuning;
- no learned weights;
- no calibration;
- no A019/A021 read or join;
- no A001/A005 joined output table;
- no candidate-bank modification, filtering, regeneration, or expansion;
- no GM_RM011 or GM_RM019 candidate-level expansion;
- no YAML, script, notebook, or pipeline scaffold.

Any future run needs a separate explicit approval after the design surface is accepted.

## 5. Candidate-Level Data Model

The combined design has two logical layers.

### Candidate node

Each A001 row is a candidate node:

```text
c = one existing SAR candidate box/state from A001
```

Candidate identity is carried by `candidate_id`. Candidate context is carried by `target_identity`, `scene`, `sar_frame`, `sar_frame_num`, and `gm17_track_id`.

The candidate node owns the SAR candidate state:

```text
cx, cy, w, h, heading, r, az, cross
```

### Row-level optical temporal prior

Each A005 row is a row/frame-level soft prior:

```text
p = one optical temporal prediction for a target/frame context
```

The current allowed temporal prior state is:

```text
pred_r, pred_cross, pred_az
```

A005 has no `candidate_id`, which is expected. It should be matched to candidate rows only through approved target/frame/track context keys in a future design. This note does not perform that join.

## 6. Candidate Join Surface

Candidate join-key candidates that exist in both A001 and A005:

| key | role | current decision |
|---|---|---|
| `target_identity` | target-level alignment | Candidate join key candidate. |
| `scene` | scope check | Must remain GM_RM017 for active Line B. |
| `sar_frame` | frame filename metadata | Optional integrity check after review. |
| `sar_frame_num` | numeric frame alignment | Candidate join key candidate. |
| `gm17_track_id` | track context | Join context only; does not activate transition. |

Likely future join surface for human review:

```text
target_identity + scene + sar_frame_num + gm17_track_id
```

Risks that must be checked before any future implementation:

- A001 is candidate-level while A005 is row-level, so the expected relation may be one A005 row to many A001 candidate rows.
- If A005 has duplicate rows under the proposed join keys, an implementation could create many-to-many duplication.
- If A001 rows lack an A005 prior, missing temporal prior should not become a hidden candidate veto.
- If A005 rows lack A001 candidates, Line B must not generate new candidates.
- `gm17_track_id` is context only and must not silently activate transition, Viterbi, or path scoring.

## 7. Field Ownership

### 7.1 Geometry owns intrinsic candidate state

`geometry_factor` owns A001 candidate-side state:

| field | owner | permitted design use | approval still needed |
|---|---|---|---|
| `cx` | `geometry_factor` | Candidate center x validity/context. | Frame coordinate convention and bounds. |
| `cy` | `geometry_factor` | Candidate center y validity/context. | Frame coordinate convention and bounds. |
| `w` | `geometry_factor` | Candidate OBB size axis. | Unit, positive range, and OBB convention. |
| `h` | `geometry_factor` | Candidate OBB size axis. | Unit, positive range, and OBB convention. |
| `heading` | `geometry_factor` | Candidate OBB axis angle. | Degree/radian, sign, wrap, and axis convention. |
| `r` | `geometry_factor` | Candidate fan-polar range state. | SAR fan-polar convention. |
| `az` | `geometry_factor` | Candidate fan-polar azimuth state. | Unit, sign, wrap, and valid range. |
| `cross` | `geometry_factor` | Candidate cross-range state. | Cross-range convention. |

Geometry may describe whether a candidate is internally plausible as an existing SAR candidate. It must not import temporal scores, source labels, selected-reference behavior, GT fields, or future visibility/near-field labels.

### 7.2 Optical temporal owns prediction-relative compatibility

`optical_temporal_factor` owns A005 fan-polar prediction fields:

| field | owner | permitted design use | approval still needed |
|---|---|---|---|
| `pred_r` | `optical_temporal_factor` | Soft range prior for comparison to candidate `r`. | Unit and fan-polar convention. |
| `pred_cross` | `optical_temporal_factor` | Soft cross-range prior for comparison to candidate `cross`. | Cross-range convention. |
| `pred_az` | `optical_temporal_factor` | Soft azimuth prior for comparison to candidate `az`. | Unit, sign, and wrap convention. |

The temporal component may compare an existing candidate to the temporal prior. It may not create a new candidate, shift candidate coordinates, overwrite `cx/cy/r/az/cross`, or hard-veto a candidate solely because it is far from the prior unless a later fixed policy explicitly approves that behavior.

### 7.3 Shared read but not shared ownership

For temporal comparison, the optical temporal component must read candidate `r`, `cross`, and `az`. These fields remain geometry-owned candidate state.

Ownership rule:

```text
Geometry owns intrinsic candidate state.
Optical temporal owns prediction-relative compatibility.
No field may contribute to both components as independent evidence.
```

This prevents double-counting candidate fan-polar coordinates as both geometry evidence and temporal evidence without a declared comparison.

## 8. Deferred Fields

The following fields exist but remain deferred. They are not active inputs in the current combined design note.

| field group | fields | why deferred |
|---|---|---|
| Precomputed A001 deltas | `delta_r_from_pred`, `delta_cross_from_pred`, `delta_az_from_pred` | Derivation, coordinate convention, angular wrap, and double-counting policy need origin review. |
| Opaque temporal scores | `temporal_factor_score` in A001/A005 | Could encode prior GM17 behavior or mixed evidence; origin review required. |
| A005 image-space prediction | `pred_cx`, `pred_cy` | Could become direct SAR center generator if misused. |
| A005 size/heading prediction | `pred_w`, `pred_h`, `pred_heading_deg` | Optical size/heading prior is not active; heading convention needs review. |
| A005 score fields | `score`, `lr_score`, `sar_factor_score` | Score origin and ownership are unclear from field inventory alone. |
| Source/provenance fields | `candidate_source`, `candidate_detail`, `candidate_expansion_state`, `candidate_expansion_reason`, `gm17_temporal_source` | Source route is inactive and could encode candidate-generation behavior. |
| Decision/anchor fields | `gm17_temporal_decision`, `gm17_anchor_strength`, `gm17_track_size`, `gm17_anchor_n`, `n_candidates` | Diagnostic or prior decision information; not current scoring evidence. |

Future review may decide to admit some deferred fields, but the manifest must be revised first. This design note keeps them outside active geometry + temporal scoring.

## 9. Forbidden Fields And Concepts

The following are forbidden from current Line B scoring, missing-value policy, combination rules, output schema, and candidate filtering:

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
- selected-reference outputs;
- B patch behavior;
- Viterbi/path scores;
- direction posterior fields;
- source prior fields;
- SAR structure fields;
- uncertainty fields;
- visibility or missing-extent labels;
- near-field routing fields;
- Line A derived discussion fields such as `long_axis`/`short_axis` or manual review categories.

These fields may be used only after independent future inference output exists and after a separate evaluation or diagnostic boundary is approved.

## 10. Component Definitions

This section is symbolic only. It does not define numeric constants or executable formulas.

### Geometry component

`E_geometry(c)` should represent candidate intrinsic plausibility.

Potential sub-responsibilities:

- validate candidate center fields `cx/cy`;
- validate positive size axes `w/h`;
- handle `heading` only after OBB angle convention approval;
- validate fan-polar fields `r/az/cross`;
- record invalid or missing geometry flags;
- keep geometry evidence independent from temporal prediction.

The geometry component should not know GT, IoU, selected reference, temporal decision labels, or candidate-source priority.

### Optical temporal component

`E_optical_temporal(c, p)` should represent soft compatibility between an existing candidate and an optical temporal prior.

Potential sub-responsibilities:

- compare candidate `r` with `pred_r`;
- compare candidate `cross` with `pred_cross`;
- compare candidate `az` with `pred_az` under an approved wrap policy;
- record missing temporal prior flags;
- record temporal conflict flags;
- remain a soft prior over existing candidates.

The optical temporal component should not generate centers, overwrite candidate coordinates, use `pred_cx/pred_cy`, copy `gm17_temporal_decision`, or use opaque scores before origin review.

## 11. Combined Design Surface

The combined design can be described symbolically as:

```text
E_total(c) = combine_fixed(
  E_geometry(c),
  E_optical_temporal(c, p)
)
```

Where:

- `c` is one fixed A001 candidate row;
- `p` is the approved A005 temporal-prior row for the same target/frame context;
- `E_geometry` is candidate intrinsic geometry cost/status;
- `E_optical_temporal` is soft prediction-relative compatibility cost/status.

This note does not choose:

- weights;
- thresholds;
- caps;
- cost scales;
- pass/fail values;
- selection rule;
- tie-break rule.

Any future numeric policy must be fixed before execution and must not be tuned from GT, metrics, selected-reference agreement, or Line A descriptive statistics.

## 12. Missing, Invalid, And Conflict Policy

Recommended policy direction for future human review:

| case | design response | reason |
|---|---|---|
| Missing A005 prior for an A001 candidate row | Keep candidate available; set temporal component neutral or disabled; emit `missing_temporal_prior` flag. | Temporal prior is optional support, not candidate-bank authority. |
| A005 prior exists but required `pred_r/pred_cross/pred_az` is missing | Disable or neutralize temporal component; emit `incomplete_temporal_prior` flag. | Avoid ad hoc prediction fill. |
| Invalid A001 geometry such as nonpositive `w/h` or nonfinite state | Block candidate or assign declared maximum geometry cost after human policy approval. | Invalid geometry should not be rescued by temporal proximity. |
| Geometry valid but temporal prior conflicts | Keep candidate available; emit conflict flag and temporal cost/status. | Conflict should remain visible, not hidden in final arbitration. |
| Geometry weak but temporal prior strong | Temporal support may reduce only temporal cost/status; it must not overwrite geometry weakness. | Prevents temporal prior from becoming a center generator. |
| Join keys ambiguous or many-to-many | Block temporal component for affected rows and require join review. | Wrong joins contaminate candidate compatibility. |
| `pred_status` not ok | Preferred behavior is temporal neutralization plus flag, after field approval. | Status should not become a hidden label or hard selector. |

Minimum future flags:

- `missing_temporal_prior`;
- `incomplete_temporal_prior`;
- `invalid_geometry`;
- `geometry_temporal_conflict`;
- `join_ambiguous`;
- `temporal_status_not_ok`;
- `deferred_field_not_used`.

## 13. Output Schema Expectations

This is not an output schema and does not create an output table. It only states what a future independently approved design may record.

Allowed future diagnostic/output fields may include:

- `manifest_version`;
- `candidate_bank_hash`;
- `candidate_id`;
- `target_identity`;
- `scene`;
- `sar_frame_num`;
- `gm17_track_id`;
- `geometry_component_status`;
- `optical_temporal_component_status`;
- `missing_value_flags`;
- `invalid_value_flags`;
- `join_flags`;
- `conflict_flags`;
- `deferred_field_policy`;
- `factor_version`.

Blocked future inference output fields:

- GT fields;
- IoU fields;
- center-error fields;
- oracle fields;
- selected-reference fields;
- A021 condition/truncation/occlusion labels;
- B patch fields;
- Viterbi path fields;
- final arbitration fields;
- source-prior fields;
- uncertainty fields;
- SAR-structure fields.

Post-inference evaluation, if approved later, must be a separate step after independent Line B output exists.

## 14. Human Approval Questions

Before any future scaffold or run, the researcher must decide:

- Is A001 still the approved GM_RM017-only candidate bank boundary?
- Is A001 SHA1 `6bb85d779ce3292f10539511224c8646cb8ee395` still the accepted boundary hash?
- Is A005 still the approved GM_RM017-only optical temporal prior?
- Are `target_identity + scene + sar_frame_num + gm17_track_id` the approved A001/A005 alignment keys?
- Should `sar_frame` also be required as an integrity key?
- Are `r`, `cross`, `az`, `pred_r`, `pred_cross`, and `pred_az` coordinate conventions approved?
- How should `az` wrap be handled?
- Should invalid geometry block a candidate or receive maximum geometry cost?
- Should missing temporal prior be neutral, disabled, or flagged only?
- What conflict flag should be emitted when geometry and temporal prior disagree?
- Do `delta_*_from_pred` remain deferred, or should they be admitted after origin review?
- Does `temporal_factor_score` remain deferred, or should it be decomposed?
- Are `pred_cx/pred_cy` still blocked from current Line B?

Approval of this note does not authorize experiments.

## 15. Recommended Next Step

If the researcher accepts this design note, the next safe step is:

```text
revise the non-executable manifest to include this combined design policy,
or write a human-review checklist for join/missing/conflict approval
```

Still do not run experiments. Candidate selection, metric computation, threshold tuning, GT joins, YAML/script creation, and candidate-bank modification remain blocked.
