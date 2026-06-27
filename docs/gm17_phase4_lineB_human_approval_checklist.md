# GM17 Phase4 Line B Human Approval Checklist

Date: 2026-06-28

Status: execution-precondition human approval checklist. This document is not an experiment, not an execution config, not YAML, not a script, not a notebook, not a scaffold, and not a candidate-selection instruction.

## 1. 当前定位

本文档整理进入任何未来 Line B execution、scaffold、join audit 或 candidate selection 之前必须由人工批准的问题。

Current Line B remains:

```text
GM_RM017-only optical-to-SAR candidate-level pilot
```

Current roles:

- A001 is the existing SAR candidate menu.
- A005 is a soft optical-temporal suggestion.
- A019/A021 remain eval-only and must not enter inference, scoring, candidate filtering, missing-value policy, or threshold decisions.

This checklist does not authorize:

- candidate selection;
- experiments;
- metric computation;
- GT join;
- A019/A021 reading or joining;
- A001/A005 joined derived dataset creation;
- candidate bank modification;
- YAML/script/notebook/scaffold creation;
- threshold tuning;
- learned weights;
- calibration;
- GM_RM011 or GM_RM019 expansion.

## 2. Approval Group A: A001 Candidate-Bank Boundary

A001 path under review:

```text
output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv
```

Known current inventory:

| item | current value |
|---|---|
| row count | `58251` |
| column count | `24` |
| candidate-bank SHA1 from manifest | `6bb85d779ce3292f10539511224c8646cb8ee395` |
| current scene scope | `GM_RM017-only` |

Checklist:

| approval item | required decision | approve | revise | hold | notes |
|---|---|---|---|---|---|
| A001 path approval | Confirm this path is the accepted Line B GM_RM017 candidate-bank boundary. | [ ] | [ ] | [ ] | |
| A001 SHA1 approval | Confirm `6bb85d779ce3292f10539511224c8646cb8ee395` is the accepted boundary hash. | [ ] | [ ] | [ ] | |
| A001 row count approval | Confirm `58251` rows is the expected candidate-bank row count for this boundary. | [ ] | [ ] | [ ] | |
| Scene-scope approval | Confirm A001 remains GM_RM017-only and is not evidence for GM_RM011/GM_RM019 candidate execution. | [ ] | [ ] | [ ] | |
| `candidate_id` uniqueness/stability | Confirm `candidate_id` is unique, stable, and safe as candidate-node identity. | [ ] | [ ] | [ ] | |
| Read-only policy | Confirm A001 must be read-only in any future work. | [ ] | [ ] | [ ] | |
| No filtering policy | Confirm future Line B cannot filter A001 before an approved scoring/diagnostic design exists. | [ ] | [ ] | [ ] | |
| No expansion policy | Confirm future Line B cannot expand A001 or generate new candidates from A005. | [ ] | [ ] | [ ] | |
| No modification policy | Confirm future Line B cannot overwrite, regenerate, or alter A001. | [ ] | [ ] | [ ] | |

Stop condition:

```text
If A001 path, hash, row count, GM_RM017-only scope, or candidate_id stability is not approved,
do not proceed to scaffold, join audit, or candidate selection.
```

## 3. Approval Group B: A005 Optical Temporal Prior Boundary

A005 path under review:

```text
output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv
```

Known current inventory:

| item | current value |
|---|---|
| row count | `205` |
| column count | `25` |
| current scene scope | `GM_RM017-only` |
| table role | row-level optical temporal prior |

Checklist:

| approval item | required decision | approve | revise | hold | notes |
|---|---|---|---|---|---|
| A005 path approval | Confirm this path is the accepted Line B GM_RM017 optical temporal prior boundary. | [ ] | [ ] | [ ] | |
| A005 row count approval | Confirm `205` rows is the expected temporal-prior row count for this boundary. | [ ] | [ ] | [ ] | |
| Scene-scope approval | Confirm A005 remains GM_RM017-only and is not all-scene temporal-prior coverage. | [ ] | [ ] | [ ] | |
| Row-level prior role | Confirm A005 is a row/frame-level prior, not a candidate bank. | [ ] | [ ] | [ ] | |
| Soft-prior-only role | Confirm A005 may only provide soft compatibility evidence. | [ ] | [ ] | [ ] | |
| No candidate generation | Confirm A005 cannot generate new candidates. | [ ] | [ ] | [ ] | |
| No candidate movement | Confirm A005 cannot move, shift, or overwrite A001 candidate coordinates. | [ ] | [ ] | [ ] | |
| No hard lock | Confirm A005 cannot hard-lock selection to temporal prediction. | [ ] | [ ] | [ ] | |

Stop condition:

```text
If A005 is not approved as a GM_RM017-only soft prior,
do not use it in Line B scaffold, join audit, or candidate selection.
```

## 4. Approval Group C: A001/A005 Join Approval

Proposed join surface for human review:

```text
target_identity + scene + sar_frame_num + gm17_track_id
```

Candidate context field:

```text
candidate_id exists only in A001 and must not be required in A005.
```

Checklist:

| approval item | required decision | approve | revise | hold | notes |
|---|---|---|---|---|---|
| Join-surface approval | Confirm `target_identity + scene + sar_frame_num + gm17_track_id` is the approved A001/A005 alignment surface. | [ ] | [ ] | [ ] | |
| `sar_frame` integrity check | Decide whether `sar_frame` must also match as an integrity check. | [ ] | [ ] | [ ] | |
| One-to-many expectation | Confirm expected relation is A005 row-level prior to one-or-many A001 candidates, not candidate-to-candidate matching. | [ ] | [ ] | [ ] | |
| Many-to-many risk check | Confirm future join audit must check duplicate A005 rows under the approved join keys. | [ ] | [ ] | [ ] | |
| Missing A005 for A001 | Approve policy for A001 candidate rows that have no A005 prior. | [ ] | [ ] | [ ] | Recommended: neutralize/disable temporal component and flag. |
| A005 prior without A001 candidate | Approve policy for A005 prior rows that have no A001 candidates. | [ ] | [ ] | [ ] | Required: do not create new candidates. |
| `candidate_id` scope | Confirm `candidate_id` is A001-only and A005 should not be expected to contain it. | [ ] | [ ] | [ ] | |
| No derived table yet | Confirm no A001/A005 joined derived dataset may be created before an approved join-audit plan. | [ ] | [ ] | [ ] | |

Stop condition:

```text
If join surface or duplicate/missing policies are unresolved,
the next safe action is a non-executable join key review note, not a join.
```

## 5. Approval Group D: Coordinate And Angle Convention

Fields under convention review:

| A001 candidate field | A005 temporal field | relation |
|---|---|---|
| `r` | `pred_r` | range comparison |
| `cross` | `pred_cross` | cross-range comparison |
| `az` | `pred_az` | azimuth comparison |
| `heading` | none active | OBB axis angle only |

Checklist:

| approval item | required decision | approve | revise | hold | notes |
|---|---|---|---|---|---|
| `r` / `pred_r` unit match | Confirm A001 `r` and A005 `pred_r` use the same coordinate system and unit. | [ ] | [ ] | [ ] | |
| `cross` / `pred_cross` convention | Confirm cross-range unit, sign, and origin are consistent. | [ ] | [ ] | [ ] | |
| `az` / `pred_az` unit | Confirm azimuth units are consistent. | [ ] | [ ] | [ ] | |
| `az` / `pred_az` sign | Confirm azimuth sign convention is consistent. | [ ] | [ ] | [ ] | |
| `az` / `pred_az` wrap | Confirm wrap policy for azimuth comparison. | [ ] | [ ] | [ ] | |
| `heading` interpretation | Confirm `heading` is only an OBB axis angle, not vehicle-head direction. | [ ] | [ ] | [ ] | |
| Angle-difference policy | Decide whether a shared angular difference strategy is required for `az` and any future `heading` comparison. | [ ] | [ ] | [ ] | |
| No `pred_heading_deg` use | Confirm `pred_heading_deg` stays blocked unless manifest is revised. | [ ] | [ ] | [ ] | |

Stop condition:

```text
If r/cross/az conventions are not approved,
the next safe action is coordinate convention review, not scaffold or candidate selection.
```

## 6. Approval Group E: Missing / Invalid / Conflict Policy

Checklist:

| approval item | required decision | approve | revise | hold | notes |
|---|---|---|---|---|---|
| Missing A005 prior | Confirm missing A005 prior should be neutralized or disabled, not punished. | [ ] | [ ] | [ ] | Recommended flag: `missing_temporal_prior`. |
| Incomplete temporal prediction | Decide how to handle missing `pred_r`, `pred_cross`, or `pred_az`. | [ ] | [ ] | [ ] | Recommended flag: `incomplete_temporal_prior`. |
| Invalid `w/h` | Decide whether nonpositive `w/h` blocks candidate or receives maximum geometry cost. | [ ] | [ ] | [ ] | Must be fixed before execution. |
| Nonfinite candidate state | Decide policy for nonfinite `cx/cy/w/h/heading/r/az/cross`. | [ ] | [ ] | [ ] | |
| Geometry-temporal conflict | Approve conflict-flag behavior when geometry is valid but temporal prior disagrees. | [ ] | [ ] | [ ] | Recommended flag: `geometry_temporal_conflict`. |
| Strong temporal, weak geometry | Confirm temporal support cannot rescue invalid or weak geometry beyond temporal component status. | [ ] | [ ] | [ ] | |
| `pred_status` not ok | Decide whether non-ok status disables/neutralizes temporal component and emits a flag. | [ ] | [ ] | [ ] | Recommended flag: `temporal_status_not_ok`. |
| Join ambiguity | Confirm ambiguous or many-to-many join blocks temporal component for affected rows. | [ ] | [ ] | [ ] | Recommended flag: `join_ambiguous`. |
| Deferred-field policy flag | Confirm use of blocked/deferred fields remains prohibited and should be flagged if attempted. | [ ] | [ ] | [ ] | Recommended flag: `deferred_field_not_used`. |

Stop condition:

```text
If missing/invalid/conflict policies are not approved,
do not create a scaffold or selection routine.
```

## 7. Approval Group F: Deferred And Forbidden Fields

The following fields remain blocked unless the manifest is revised first.

### Deferred A001/A005 fields

| field or group | current decision | approve blocked status | revise manifest first | hold |
|---|---|---|---|---|
| `delta_*_from_pred` | blocked/deferred | [ ] | [ ] | [ ] |
| `temporal_factor_score` | blocked/deferred | [ ] | [ ] | [ ] |
| `pred_cx`, `pred_cy` | blocked/deferred | [ ] | [ ] | [ ] |
| `pred_w`, `pred_h`, `pred_heading_deg` | blocked/deferred | [ ] | [ ] | [ ] |
| `score`, `lr_score`, `sar_factor_score` | blocked/deferred | [ ] | [ ] | [ ] |
| `candidate_source`, `candidate_detail`, `candidate_expansion_*` | blocked/deferred | [ ] | [ ] | [ ] |
| `gm17_temporal_source`, `gm17_temporal_decision` | blocked/deferred | [ ] | [ ] | [ ] |
| `gm17_anchor_strength`, `gm17_track_size`, `gm17_anchor_n`, `n_candidates` | blocked/deferred | [ ] | [ ] | [ ] |

### Forbidden eval / selected / condition fields

| field or pattern | current decision | approve blocked status | revise manifest first | hold |
|---|---|---|---|---|
| `final_*` | forbidden | [ ] | [ ] | [ ] |
| `gt_*` | forbidden | [ ] | [ ] | [ ] |
| `iou` fields | forbidden | [ ] | [ ] | [ ] |
| `center_err` fields | forbidden | [ ] | [ ] | [ ] |
| `oracle` fields | forbidden | [ ] | [ ] | [ ] |
| `selected` fields | forbidden | [ ] | [ ] | [ ] |
| `condition` fields | forbidden | [ ] | [ ] | [ ] |
| `truncation` fields | forbidden | [ ] | [ ] | [ ] |
| `occlusion` fields | forbidden | [ ] | [ ] | [ ] |

Required decision:

```text
If any deferred field is desired for active scoring,
revise the manifest first.
Do not admit deferred fields directly in scaffold or candidate selection.
```

## 8. Approval Group G: Execution Boundary

Checklist:

| approval item | required decision | approve | revise | hold | notes |
|---|---|---|---|---|---|
| Candidate selection ban | Confirm candidate selection remains forbidden until later explicit approval. | [ ] | [ ] | [ ] | |
| Experiment ban | Confirm experiments remain forbidden. | [ ] | [ ] | [ ] | |
| Metric computation ban | Confirm IoU, center error, recall, rank, oracle rank, and performance metrics remain forbidden. | [ ] | [ ] | [ ] | |
| A019/A021 read/join ban | Confirm A019/A021 must not be read or joined for Line B inference/scoring design. | [ ] | [ ] | [ ] | |
| GT leakage ban | Confirm GT/eval fields cannot affect scoring, thresholds, missing policy, or candidate filtering. | [ ] | [ ] | [ ] | |
| YAML/script/notebook/scaffold ban | Confirm no executable artifact may be created from this checklist. | [ ] | [ ] | [ ] | |
| Candidate-bank modification ban | Confirm no A001 filtering, editing, regeneration, replacement, or expansion. | [ ] | [ ] | [ ] | |
| GM_RM011/GM_RM019 expansion ban | Confirm no candidate-level expansion to GM_RM011 or GM_RM019. | [ ] | [ ] | [ ] | |
| Stage/commit/push ban | Confirm this checklist alone does not authorize staging, commit, or push. | [ ] | [ ] | [ ] | |

Stop condition:

```text
If any execution boundary is not approved,
keep Line B in non-executable design mode.
```

## 9. Final Decision Section

Use this section for the human review decision.

### Decision

Choose one:

- [ ] approve
- [ ] revise
- [ ] hold

### Approved items

List approved groups or individual items:

```text

```

### Unresolved items

List unresolved groups or individual items:

```text

```

### Required revisions

List manifest, field-inventory, or design-note revisions required before any next step:

```text

```

### Next safe action

Choose one:

- [ ] non-executable join-integrity audit plan
- [ ] join key review note
- [ ] coordinate convention review
- [ ] manifest revision for deferred fields
- [ ] keep Line B on hold
- [ ] other non-executable review:

```text

```

Reviewer:

```text

```

Review date:

```text

```

## 10. Recommended Next Safe Actions

| approval result | next safe action | still forbidden |
|---|---|---|
| All groups approved | Write a non-executable join-integrity audit plan. | No join execution, no candidate selection, no metrics. |
| Join surface not approved | Write a join key review note. | No A001/A005 joined table. |
| Coordinate or angle convention not approved | Write a coordinate convention review. | No temporal comparison, no angular cost design. |
| Missing/invalid/conflict policy not approved | Revise the combined design note or write a policy review note. | No scaffold, no selection routine. |
| Deferred field desired for use | Revise the manifest first. | Do not use deferred fields directly. |
| Forbidden-looking field appears in a future table version | Stop and revise denylist/manifest. | No scaffold or candidate selection. |
| A001/A005 boundary not approved | Keep Line B on hold. | No execution or scaffold. |

The most conservative next step after full approval is:

```text
non-executable join-integrity audit plan
```

That plan should define what would be checked in a future approval round, but it should still not run a join, create a derived dataset, compute metrics, or select candidates.
