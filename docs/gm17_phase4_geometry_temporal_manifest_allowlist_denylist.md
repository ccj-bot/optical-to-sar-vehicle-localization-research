# GM17 Phase4 Line B Geometry + Optical Temporal Manifest Allowlist Denylist

Date: 2026-06-28

Status: non-executable Line B manifest, allowlist, denylist, and approval-gate design for human review. This document does not authorize experiments, candidate selection, metric computation, model training, calibration, threshold tuning, learned weights, candidate-bank generation, candidate-bank modification, GM_RM011 or GM_RM019 expansion, script scaffolding, staging, commit, or push.

## 1. Scope Lock

Line B is currently restricted to:

```text
GM_RM017-only optical-to-SAR candidate-level pilot
```

The reason is data-layer coverage:

- A001 candidate bank currently supports GM_RM017 only.
- A005 optical temporal prior currently supports GM_RM017 only.
- A001/A005 do not support GM_RM011 or GM_RM019 candidate-level execution.
- GM_RM011 and GM_RM019 remain valid for Line A SAR-domain physical-prior audit and future route planning, but not for current Line B candidate-level scoring.

The active Line B design surface is limited to:

- `geometry_factor`, using approved A001 candidate-state fields only;
- `optical_temporal_factor`, using approved A005 optical-to-SAR temporal prior fields only.

Inactive in this document:

- `direction_factor`;
- controlled non-visible `source_factor`;
- `transition_factor`;
- `sar_structure_factor`;
- `uncertainty_factor`;
- `visibility_factor`;
- `missing_extent_factor`;
- visible/full-center offset route;
- near-field route;
- final arbitration or selected-reference copying.

Line A findings remain interpretation boundaries. They can explain why some fields are eval-only, audit-only, or future-route material, but they cannot become Line B scoring parameters.

## 2. Non-Execution Contract

This document is a design boundary only.

It explicitly does not do any of the following:

- run candidate selection;
- compute IoU, center error, recall, rank, oracle rank, or any performance metric;
- tune thresholds or constants from GT, metrics, Line A statistics, or selected-reference behavior;
- create executable YAML, Python, CLI, notebook, or pipeline scaffolds;
- read A019/A021 before an independent future inference output exists;
- alter, filter, regenerate, expand, or replace A001;
- derive GM_RM011 or GM_RM019 candidate banks from A001/A005;
- activate partial-visibility, missing-extent, near-field, SAR-structure, uncertainty, direction, source, transition, or final arbitration logic.

Any future run requires a separate user approval after this design is accepted.

## 3. Proposed Non-Executable Manifest

All paths below are proposed design entries. They are not executable configuration.

| manifest_key | asset_id | proposed_path | scene scope | role | Line B status | approval gate |
|---|---|---|---|---|---|---|
| `candidate_bank_path` | A001 | `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv` | GM_RM017 only | Frozen candidate-bank candidate for existing SAR candidates. | proposed input after human approval | Approve path, hash, scene scope, row count, key stability, and field mapping. |
| `candidate_bank_hash` | A001 | `6bb85d779ce3292f10539511224c8646cb8ee395` | GM_RM017 only | Boundary SHA1 recorded by prior manifest design. | proposed boundary after human approval | Future execution must recompute and match before any use. |
| `candidate_bank_row_count` | A001 | `58251` | GM_RM017 only | Prior inventory row-count record. | documentation only | Future execution must re-check before use. |
| `optical_temporal_prior_path` | A005 | `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv` | GM_RM017 only | Optical-to-SAR temporal soft prior. | proposed input after human approval | Approve path, field origin, join keys, and soft-prior-only behavior. |
| `manual_gt_box_path` | A019 | `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv` | GM_RM011, GM_RM017, GM_RM019 | Manual final SAR GT boxes. | post-inference eval-only | Must not be joined before independent future Line B output exists. |
| `eval_only_label_path` | A021 | `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv` | GM_RM011, GM_RM017, GM_RM019 | Visibility, truncation, occlusion, and condition labels. | post-inference eval-only and future-route context | Must not influence scoring, gates, thresholds, missing policy, or factor activation. |
| `lineA_physical_structure_context` | Line A docs | `docs/gm17_phase4_lineA_sar_vehicle_physical_structure_findings.md` and related Line A audit docs | GM_RM011, GM_RM017, GM_RM019 | SAR physical interpretation boundary. | audit-context only | May define denylist/caveat language, not numeric scoring parameters. |

Deferred assets:

| asset | current Line B decision | reason |
|---|---|---|
| A007 signed escape posterior | deferred | Direction posterior belongs to future `direction_factor`, not current geometry + optical temporal pilot. |
| A008 candidate refined factor join table | deferred | It may contain diagnostic, selected-behavior, posterior, or precomputed score fields whose ownership is not active here. |
| A013 selected prediction reference | blocked from scoring | Selected-reference behavior can copy prior selector decisions and is post-inference comparison only. |
| A017/A018 diagnostic or patch outputs | blocked from scoring | SAR structure, uncertainty, and final arbitration are inactive and cannot copy B patch behavior. |

## 4. Candidate-Bank Boundary Gate

A future scaffold or execution round may use A001 only if all candidate-bank gates pass.

Required gates:

| gate | required decision | stop condition |
|---|---|---|
| Path gate | Human approves A001 path as the GM_RM017-only pilot bank. | Path differs or user does not approve. |
| Hash gate | Future run recomputes SHA1 and matches `6bb85d779ce3292f10539511224c8646cb8ee395`. | Hash mismatch. |
| Scene gate | Candidate rows are confirmed to be GM_RM017-only. | Any attempt to treat A001 as GM_RM011 or GM_RM019 coverage. |
| Row-count gate | Future run records current row count and compares with accepted manifest boundary. | Unexplained row-count mismatch. |
| Key gate | `candidate_id` is stable and unique within A001. | Duplicates or unstable key construction. |
| GT-leak gate | No `final_*`, `gt_*`, IoU, center-error, oracle, condition, or selected-reference metric field enters candidate scoring. | Any eval-only or selected-reference field appears in an inference input set. |
| Mutation gate | A001 is read-only. | Any filtering, regeneration, expansion, overwrite, or candidate-bank modification. |

This gate freezes proposal generation for the pilot. It does not approve the candidate selector, scoring formula, or experiment execution.

## 5. Optical Temporal Prior Gate

A future scaffold or execution round may use A005 only if all temporal-prior gates pass.

Required gates:

| gate | required decision | stop condition |
|---|---|---|
| Path gate | Human approves A005 path as the GM_RM017-only optical temporal prior. | Path differs or user does not approve. |
| Scene gate | A005 is confirmed to align with GM_RM017 pilot rows only. | Any attempt to use A005 as all-scene temporal prior. |
| Join gate | Join keys between A001 and A005 are approved before implementation. | Ambiguous, many-to-many, missing, or inconsistent join ownership. |
| Soft-prior gate | A005 may compare against existing candidates but must not generate, shift, overwrite, or filter candidate centers. | Temporal fields become a hard center generator or hard veto. |
| Status gate | `pred_status` or similar validity fields, if present, are diagnostic or neutralization gates only after approval. | Status fields become hidden labels or tuning handles. |
| Opaque-score gate | Any opaque temporal score requires origin review before use. | Score origin is unclear or duplicates selected-reference behavior. |

The temporal prior may support candidate compatibility only. It cannot replace SAR candidate localization.

## 6. Base Identity And Join Allowlist

The following fields may be used as identity, provenance, or join fields after human approval. They are not scoring features by themselves.

| field | source | intended role | status | caveat |
|---|---|---|---|---|
| `candidate_id` | A001 | Candidate node identity. | allow after A001 approval | Must be stable and unique. |
| `target_identity` | A001, A005 | Row/target alignment key. | allow after join approval | Must not be used as a leakage key into GT. |
| `scene` if present | A001, A005 | Scope validation and diagnostic metadata. | allow after scope approval | Must remain GM_RM017-only for active Line B. |
| `sar_frame` | A001, A005 if present | Frame/path metadata. | allow as metadata | Not a scoring feature. |
| `sar_frame_num` | A001, A005 | Frame identity for row alignment. | allow after join approval | Context only; does not activate transition. |
| `gm17_track_id` | A001, A005 | Track context for temporal-prior lookup. | allow after join approval | Context only; does not activate transition or Viterbi. |

Join approval must be explicit before any future code derives factor inputs.

## 7. Geometry Factor Allowlist

The `geometry_factor` may use only candidate-state fields from A001 after A001 path, hash, scope, and field mapping are approved.

| field | source | intended Line B use | status | caveat |
|---|---|---|---|---|
| `cx` | A001 | Candidate center x. | allow after field approval | Candidate state only; never substitute `final_cx`. |
| `cy` | A001 | Candidate center y. | allow after field approval | Candidate state only; never substitute `final_cy`. |
| `w` | A001 | Candidate OBB width or stored size axis. | allow after field approval | Confirm units and positive valid range. |
| `h` | A001 | Candidate OBB height or stored size axis. | allow after field approval | Confirm units and positive valid range. |
| `heading` | A001 | Candidate OBB axis angle. | allow after field approval | Confirm degree/radian, sign, wrap, and axis convention. |
| `r` | A001 | Candidate fan-polar range state. | allow after field approval | Confirm SAR fan-polar convention. |
| `az` | A001 | Candidate fan-polar azimuth state. | allow after field approval | Confirm units, sign, and wrap. |
| `cross` | A001 | Candidate fan-polar cross-range state. | allow after field approval | Confirm coordinate convention. |

Geometry design caveats from Line A:

- `w/h` or `final_w/final_h` observations do not define scoring thresholds.
- `heading` is an OBB axis angle until the convention is approved; it is not automatically a vehicle-head direction.
- Long-axis discussion can inform documentation but cannot create a tuned constant.
- Severe truncation, near-field, optical unresolved, and scatter spillover are future-route caveats, not active geometry inputs.

## 8. Optical Temporal Factor Allowlist

The `optical_temporal_factor` may use only approved A005 temporal-prior fields and approved A001 candidate state for comparison.

| field | source | intended Line B use | status | caveat |
|---|---|---|---|---|
| `pred_r` | A005 | Soft optical-to-SAR range prior. | allow after A005 approval | May compare to candidate `r`; cannot replace candidate `r`. |
| `pred_cross` | A005 | Soft optical-to-SAR cross-range prior. | allow after A005 approval | May compare to candidate `cross`; cannot replace candidate `cross`. |
| `pred_az` | A005 | Soft optical-to-SAR azimuth prior. | allow after A005 approval | Requires angular convention and wrap approval. |
| `pred_status` or equivalent validity field | A005 if present | Optional diagnostic or neutralization gate. | deferred until field review | Not a scoring feature by default. |
| `temporal_factor_score` | A005 if present | Possible precomputed support field. | deferred until origin review | Opaque scores must not copy selected-reference or transition behavior. |
| `r` | A001 | Candidate state read for comparison to `pred_r`. | allow through geometry ownership | Temporal factor reads but does not own or overwrite it. |
| `cross` | A001 | Candidate state read for comparison to `pred_cross`. | allow through geometry ownership | Temporal factor reads but does not own or overwrite it. |
| `az` | A001 | Candidate state read for comparison to `pred_az`. | allow through geometry ownership | Temporal factor reads but does not own or overwrite it. |

Precomputed delta fields such as `delta_r_from_pred`, `delta_cross_from_pred`, and `delta_az_from_pred` are not active by default. They require source-table review, derivation review, unit review, and double-counting review before use.

## 9. Eval-Only Denylist

The following fields, prefixes, field families, and derived concepts are blocked from inference inputs, candidate scoring, factor inclusion, cost construction, missing-value policy, clipping policy, threshold choice, path construction, and inference outputs.

| denied item | examples | source layer | allowed use |
|---|---|---|---|
| Manual final GT fields | `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg`, `final_rot_area_px`, `final_ax_area_px` | A019 | Post-inference evaluation or Line A audit only. |
| GT prefixes | `gt_*` | Eval tables or diagnostic outputs | Post-inference evaluation only. |
| Oracle fields | `oracle_*`, `oracle_rank_*`, `oracle_best_*` | Eval outputs | Post-inference analysis only. |
| IoU metrics | `candidate_iou`, `rot_iou`, `selected_iou`, `baseline_iou` | Eval outputs | Post-inference metric reporting only. |
| Center-error metrics | `center_err_px`, `candidate_center_err_px`, `selected_center_err_px`, `baseline_center_err_px` | Eval outputs | Post-inference metric reporting only. |
| Visibility and condition labels | `visibility_status`, `condition_type`, `condition_degree`, `condition_status` | A021 | Post-inference grouping and future-route planning only. |
| Truncation labels | `truncation_degree`, truncation-derived flags | A021 | Failure-mode grouping and future missing-extent route only. |
| Occlusion labels | `occlusion_degree`, occlusion-derived flags | A021 | Failure-mode grouping and future visibility route only. |
| Line A derived discussion fields | `long_axis`, `short_axis`, `review_long_axis_field`, audit interpretation categories | Line A docs or future review notes | Documentation, audit, and caveat discussion only. |
| Manual review categories | `likely_complete_vehicle_extent`, `likely_sar_visible_or_truncated_extent`, `sar_only_or_optical_unresolved_extent`, `near_field_or_mask_boundary_extent`, `uncertain_extent` | Line A audit interpretation | Future human-review context only. |

A019 and A021 can be joined only after an independent future inference output exists.

## 10. Scope And Expansion Denylist

The following actions are blocked in the current Line B design.

| blocked action | reason |
|---|---|
| Treating A001 as GM_RM011 or GM_RM019 coverage. | A001 is GM_RM017-only in the current boundary. |
| Treating A005 as GM_RM011 or GM_RM019 temporal-prior coverage. | A005 is GM_RM017-only in the current boundary. |
| Generating GM_RM011 or GM_RM019 candidate banks as part of Line B. | Candidate generation is a separate future route requiring approval. |
| Expanding A001 by copying, filtering, or adapting GM_RM017 candidates to other scenes. | This would modify the candidate-bank boundary and create unsupported coverage. |
| Claiming all-scene candidate-level validation from Line B. | Current candidate-level pilot has GM_RM017 coverage only. |
| Using Line A all-GT statistics to tune Line B thresholds. | Line A is audit-only and eval-only. |

GM_RM011 and GM_RM019 remain valid Line A audit scenes and future-route planning scenes.

## 11. Diagnostic And Future-Route Denylist

The following fields and field families are not active Line B scoring inputs.

| group | denied fields or examples | current decision |
|---|---|---|
| Direction posterior | `signed_escape_decision`, `candidate_direction_bin`, `signed_direction_match`, `posterior_confidence`, `posterior_margin`, `P_near`, `P_neg_escape`, `P_pos_escape` | Future `direction_factor` only after ownership review. |
| Source family | `candidate_source`, `source_prior`, visible/non-visible source-family mappings | Future controlled source design only after normalization and leakage review. |
| Transition and path behavior | `path_score`, `node_score`, Viterbi selected fields, track-level selected output fields | Blocked from current pilot; transition is inactive. |
| SAR structure | `directional_shell_score`, `track_escape_evidence`, `refined_geometry_score`, `geometry_escape_refined_score`, SAR support fields | Diagnostic or future SAR-structure route only. |
| Uncertainty | `P_ambiguous`, `P_artifact`, `E_uncertainty`, ambiguity/artifact routes | Diagnostic or future uncertainty route only. |
| Final arbitration | `two_stage_gate_*`, `phi_final_score`, `cost_final`, final selector fields | Blocked because it can copy selected behavior. |
| B patch behavior | `patch_action`, `patch_variant`, `patch_triggered`, B patch candidate fields | Diagnostic consistency evidence only, not scoring proof. |
| Visibility or missing extent | visible support fields, mask-support fields, missing-extent fields, full-center offset fields | Future route only. |
| Near-field | near-field flags, boundary-regime indicators, mask-boundary action fields | Future route only. |

These fields may be discussed in future design notes. They are not part of the current geometry + optical temporal manifest.

## 12. Combination And Scoring Gate

No combination rule is approved by this document.

Before any future scaffold, human review must approve:

- whether the pilot uses component costs, component scores, or only diagnostic records;
- the fixed combination rule, if any;
- missing-value policy for geometry fields;
- missing-value or neutralization policy for temporal prior fields;
- invalid `w/h/heading/r/az/cross` policy;
- angular wrap policy for `az` and `heading`;
- whether any precomputed temporal score is allowed;
- whether any precomputed delta field is allowed;
- output schema and manifest versioning.

Hard boundaries:

- no learned weights;
- no GT-tuned thresholds;
- no metric-tuned constants;
- no hard temporal lock;
- no temporal center generation;
- no selected-reference copying;
- no final arbitration;
- no rescue of invalid geometry by temporal prior;
- no penalty for missing temporal prior unless explicitly approved as a declared missing-prior policy.

## 13. Future Output Schema Expectations

This section is a design expectation only and does not create an output file.

A future independent Line B output, if separately approved later, may include:

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
- `factor_version`.

Fields blocked from any future inference output:

- GT fields;
- IoU fields;
- center-error fields;
- oracle fields;
- selected-reference fields;
- A021 condition labels;
- Line A review categories;
- B patch fields;
- Viterbi path fields;
- final arbitration fields.

Metrics and eval grouping can be added only after independent future inference output exists and after a separate evaluation join is approved.

## 14. Human Approval Checklist

Before any future execution, the researcher must approve:

- A001 path as the GM_RM017-only candidate-bank boundary.
- A001 SHA1 `6bb85d779ce3292f10539511224c8646cb8ee395`.
- A001 row count after a future re-check.
- A001 key stability and `candidate_id` uniqueness.
- A005 path as the GM_RM017-only temporal-prior boundary.
- A001/A005 join keys.
- A001 geometry field mapping and units.
- A005 temporal field mapping and units.
- `heading` and `az` angle convention.
- Missing-value, invalid-value, and conflict policies.
- Whether `temporal_factor_score` remains deferred or is decomposed.
- Whether precomputed `delta_*_from_pred` fields remain blocked or are approved.
- Eval-only denylist.
- Diagnostic and future-route denylist.
- Post-inference A019/A021 join boundary.

Approval of this document alone does not authorize execution.

## 15. Recommended Next Step

Recommended next step after human review:

```text
review and approve or revise this non-executable Line B manifest boundary
```

Only after that approval should a later round consider non-executable YAML templates or a scaffold design. Experiments, candidate selection, metric computation, tuning, and candidate-bank expansion should remain blocked.
