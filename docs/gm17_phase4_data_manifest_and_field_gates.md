# GM17 Phase4 Data Manifest And Field Gates

Date: 2026-06-02

Status: proposed Phase4 data manifest and field-gate plan. This document is for human review only. It does not authorize experiments, inference runs, metrics, training, calibration, data-file modification, candidate-bank modification, code modification, GM17 replacement, partial-visibility activation, near-field activation, staging, commit, or push.

## 1. Purpose

This document turns the local data inventory into a proposed Phase4 data manifest, inference allowlist, eval-only denylist, and human approval gate plan.

Phase4 remains fixed-prior revalidation over a frozen SAR candidate bank. External methods, local runtime outputs, selected-prediction references, and manual GT tables are not automatically accepted as Phase4 inputs. They become Phase4 inputs only after human approval, hash acceptance, field mapping review, and inference/evaluation separation review.

No experiment execution is authorized by this document.

## 2. Proposed Data Manifest

All local runtime-output paths require human approval before becoming Phase4 inputs.

| manifest_key | proposed_path | asset_id_from_inventory | role | status | required_human_approval | notes |
|---|---|---|---|---|---|---|
| `candidate_bank_path` | `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv` | A001 | Frozen v2.2 candidate bank candidate. | needs_human_review | yes | Best local candidate-bank path; local runtime output, not automatically formal baseline. |
| `candidate_bank_hash` | `6bb85d779ce3292f10539511224c8646cb8ee395` | A001 | Boundary hash for candidate bank. | needs_human_review | yes | Computed in local inventory; must be accepted as Phase4 boundary hash. |
| `candidate_table_path` | `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/candidate_refined_factor_inference.csv` | A008 | Candidate-factor join table for geometry/direction/diagnostic fields. | needs_human_review | yes | Rich joined table; must be allowlisted because it contains diagnostic fields. |
| `direction_posterior_path` | `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/signed_escape_posterior_inference.csv` | A007 | Row-level signed escape posterior and direction confidence. | needs_human_review | yes | Required for `direction_factor`; uncertainty-style fields remain diagnostic-only. |
| `optical_temporal_prior_path` | `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv` | A005 | Optical-to-SAR temporal soft prior. | needs_human_review | yes | Candidate for `optical_temporal_factor`; must remain soft prior only. |
| `selected_prediction_reference_path` | `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/track_viterbi_selected_inference.csv` | A013 | Staged selected-prediction behavior reference. | needs_human_review | yes | Reference only; must not be used as candidate scoring input. |
| `manual_gt_box_path` | `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv` | A019 | Manual GT box table for post-inference evaluation. | needs_human_review | yes | Eval-only; must be joined only after inference output exists. |
| `eval_only_label_path` | `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv` | A021 | Manual visibility/truncation/occlusion labels. | needs_human_review | yes | Eval-only and future-branch-only; not Phase4 scoring input. |

## 3. Candidate Bank Boundary

Candidate bank path:

```text
output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv
```

Candidate bank SHA1:

```text
6bb85d779ce3292f10539511224c8646cb8ee395
```

Row count from local inventory:

```text
58251
```

Why it is likely current:

- It is the best local candidate for the fixed v2.2 Phase4 bank.
- It has candidate-level keys and complete-vehicle geometry fields.
- The local inventory recorded it as A001 and `likely_current`.
- The Viterbi selector boundary report recorded matching before/after candidate-bank SHA1 values.

Why it still requires human approval:

- It is a local runtime output.
- It is not automatically accepted as formal baseline solely because it exists.
- A human researcher must confirm that this is the accepted v2.2 candidate bank for Phase4.
- A human researcher must confirm that the SHA1 above is the boundary hash to enforce.

Hash policy for future scaffold runs:

- Read the candidate bank without modifying it.
- Compute SHA1 before each scaffold run.
- Compare the computed SHA1 to `6bb85d779ce3292f10539511224c8646cb8ee395`.
- Stop if the hash differs unless the user explicitly authorizes a new bank boundary.
- Do not regenerate, edit, filter, expand, or replace the candidate bank in Phase4.

## 4. Inference-Safe Allowlist Draft

Status values:

- `needs_human_review`: locally available but not yet approved as a Phase4 inference field.
- `blocked`: must not enter Phase4 inference scoring.
- `approved`: not used in this draft because every runtime-output source still requires human approval.

### Base identity and join keys

| field_or_group | source file | factor use | status | risk note |
|---|---|---|---|---|
| `candidate_id` | A001, A008 | all candidate factors | needs_human_review | Required candidate key; human must confirm uniqueness and stability in A001. |
| `target_identity` | A001, A005, A007, A008 | row join key | needs_human_review | Proposed mapping to `row_id`; must be confirmed. |
| `sar_frame` | A001, A005, A008 | frame/path metadata | needs_human_review | Path/name metadata only; not a scoring feature. |
| `sar_frame_num` | A001, A005, A007, A008 | frame ordering, transition | needs_human_review | Proposed mapping to `frame_id`; numeric ordering must be confirmed. |
| `gm17_track_id` | A001, A005, A007, A008 | track grouping, transition | needs_human_review | Proposed mapping to `track_id`; grouping must be confirmed. |

### geometry_factor

| field_or_group | source file | factor use | status | risk note |
|---|---|---|---|---|
| `cx` | A001 | candidate center x; maps to `center_x` | needs_human_review | Candidate field only; never use `final_cx` as inference center. |
| `cy` | A001 | candidate center y; maps to `center_y` | needs_human_review | Candidate field only; never use `final_cy` as inference center. |
| `w` | A001 | candidate size | needs_human_review | Confirm units and positive range. |
| `h` | A001 | candidate size | needs_human_review | Confirm units and positive range. |
| `heading` | A001 | candidate OBB heading | needs_human_review | Confirm degree/radian convention and orientation sign. |
| `r` | A001 | fan-polar geometry | needs_human_review | Candidate-bank field; allowed only after bank approval. |
| `az` | A001 | fan-polar geometry | needs_human_review | Candidate-bank field; confirm coordinate convention. |
| `cross` | A001 | fan-polar geometry | needs_human_review | Candidate-bank field; confirm coordinate convention. |
| `delta_r_from_pred`, `delta_cross_from_pred`, `delta_az_from_pred` | A001, A008 | geometry compatibility | needs_human_review | Use only if confirmed inference-safe and not derived from eval labels. |
| `refined_geometry_score`, `geometry_escape_refined_score` | A008 | possible diagnostic geometry support | blocked | Diagnostic/ownership-gated; may overlap SAR structure. Not active Phase4 until another audit accepts ownership. |

### direction_factor

| field_or_group | source file | factor use | status | risk note |
|---|---|---|---|---|
| `candidate_direction_bin` | A008 | candidate direction state | needs_human_review | Not present in raw A001 bank; candidate join must be approved. |
| `signed_escape_decision` | A007, A008 | row-level direction prior | needs_human_review | Join from posterior table must be approved. |
| `signed_direction_match` | A008 | direction compatibility | needs_human_review | Must not be counted again as independent source-prior evidence. |
| `posterior_confidence` | A007, A008 | direction confidence | needs_human_review | Direction use may be allowed; uncertainty use remains diagnostic-only. |
| `posterior_margin` | A007, A008 | direction confidence margin | needs_human_review | Direction use may be allowed; uncertainty use remains diagnostic-only. |
| `P_near`, `P_neg_escape`, `P_pos_escape` | A007, A008 | direction posterior components | needs_human_review | Use only if confirmed inference-safe for direction scoring. |
| `P_ambiguous`, `P_artifact` | A007, A008 | ambiguity/artifact posterior | blocked | Diagnostic/uncertainty/visibility route only; not active Phase4 scoring. |

### controlled non-visible source_factor

| field_or_group | source file | factor use | status | risk note |
|---|---|---|---|---|
| `candidate_source` | A001, A008 | source-family prior | needs_human_review | Human must confirm source values and non-visible family mapping. |
| source-family mapping fields if present | A008, A013, possible diagnostic outputs | source normalization | needs_human_review | Visible source behavior must remain veto/uncertainty-only and not full-center evidence. |
| `source_prior` | A013 | candidate source prior | blocked | Diagnostic output field; do not activate as independent source score without another audit. |
| `directional_shell_score`, `track_escape_evidence`, `signed_direction_match` as source support | A008, A013 | gated source context only | blocked | Must not be counted as independent source-prior evidence unless ownership is declared. |

### optical_temporal_factor

| field_or_group | source file | factor use | status | risk note |
|---|---|---|---|---|
| `pred_r` | A005 | soft fan-polar prior | needs_human_review | Soft prior only; cannot generate or overwrite full center. |
| `pred_cross` | A005 | soft fan-polar prior | needs_human_review | Soft prior only; confirm join by `target_identity`. |
| `pred_az` | A005 | soft fan-polar prior | needs_human_review | Soft prior only; confirm coordinate convention. |
| `temporal_factor_score` | A005, A001 | soft temporal prior | needs_human_review | Must not duplicate transition smoothness without ownership. |
| `optical_temporal_consistency_score` | A008 | candidate-level temporal consistency | needs_human_review | Candidate join must be approved; soft prior only. |

### transition_factor

| field_or_group | source file | factor use | status | risk note |
|---|---|---|---|---|
| `gm17_track_id` | A001, A008 | track grouping | needs_human_review | Track grouping must be human-confirmed. |
| `sar_frame_num` | A001, A008 | frame ordering | needs_human_review | Numeric ordering and adjacency policy must be confirmed. |
| `candidate_id` | A001, A008 | node identity | needs_human_review | Candidate stability must be confirmed. |
| `r`, `cross`, `az`, `heading`, `w`, `h` | A001 | transition state | needs_human_review | Use for continuity only after candidate bank approval. |
| `optical_temporal_consistency_score` in transition | A008 | possible transition support | needs_human_review | Risk of optical-temporal/transition double-counting; keep roles separated. |

## 5. Eval-Only Denylist Draft

The following fields and prefixes must not enter inference inputs, candidate scoring, path construction, factor selection, missing-value policy, or inference outputs.

| field_or_prefix | examples / source | status | note |
|---|---|---|---|
| `gt_*` | `gt_r`, `gt_az`, `gt_cx`, `gt_cy` | blocked | GT-derived values are eval-only. |
| `final_*` | `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg`, `final_ax_*` | blocked | Manual/final annotation fields; post-inference only. |
| `oracle_*` | `oracle_rank_iou`, `oracle_rank_center`, `oracle_best_*` | blocked | Oracle fields are evaluation-only. |
| `candidate_iou` | A002 | blocked | Candidate/GT overlap metric. |
| `rot_iou` | A002, A006, A014 | blocked | Evaluation metric. |
| `center_err_px` | A002, A006, A014 | blocked | Evaluation metric. |
| `candidate_center_err_px` | A002 | blocked | Candidate/GT error metric. |
| `selected_iou` | A014 and related eval outputs | blocked | Selected-output metric; post-inference only. |
| `selected_center_err_px` | A014 and related eval outputs | blocked | Selected-output metric; post-inference only. |
| `condition_type` | A021 and eval outputs | blocked | Evaluation grouping and future partial-visibility label only. |
| `truncation_degree` | A021 and eval outputs | blocked | Evaluation grouping and future Phase7 label only. |
| `occlusion_degree` | A021 and eval outputs | blocked | Evaluation grouping and future Phase7 label only. |
| visibility condition labels | `condition_status`, `condition_degree`, `visibility_status` when used as manual label | blocked | Future partial-visibility/eval-only material. |
| manual GT box fields | `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg`, manual `cx/cy/w/h/heading_deg` from GT tables | blocked | Manual annotation fields may be joined only after inference output exists. |
| selected-reference metric fields | `baseline_iou`, `baseline_center_err_px`, `delta_iou_vs_hybrid`, `delta_center_err_vs_hybrid` | blocked | Selected-reference metrics must not influence inference. |

GT and manual annotation fields may be joined only after inference output exists.

## 6. Diagnostic-Only Field Gate

The following fields may be useful for review, debugging, or future branches, but they must not become active Phase4 scoring fields without another audit.

| diagnostic group | fields / examples | gate decision | risk |
|---|---|---|---|
| `sar_structure_factor` fields | `directional_shell_score`, `geometry_escape_refined_score`, `track_escape_evidence`, `escape_conflict_score`, `E_sar_structure` | diagnostic-only | Overlaps geometry and uncertainty; support-vs-uncertainty ownership unresolved. |
| `uncertainty_factor` fields | `P_ambiguous`, `P_artifact`, `E_uncertainty`, `sar_uncertainty_soft`, uncertainty routing fields | diagnostic-only | Patch dependency and ambiguity/final-arbitration overlap. |
| `final_arbitration_factor` fields | `two_stage_gate_reason`, `two_stage_gate_allow_switch`, `two_stage_gate_kept_base`, `Z_t`, `phi_final_score`, `cost_final` | blocked from active Phase4 scoring | Can copy B patch or selector action behavior. |
| B patch fields | `patch_variant`, `patch_action`, `patch_triggered`, `sar_uncertainty_penalty_triggered`, `direction_veto_triggered`, `bpatch_candidate_id` | diagnostic-only | B patch reproduction is diagnostic consistency evidence, not physical proof. |
| visibility / missing extent / visible-full-center-offset fields | `visible_factor`, `visible_status`, `visible_extent_features`, `shape_mask_conf`, `support_px`, `visible_area_ratio`, `centroid_offset_px`, `off_x`, `off_y` | future/diagnostic-only | Visible support must not generate full center. |
| near-field fields | `is_near_field` or any geometry-regime indicator if present | future-only | Near-field cannot modify candidate bank, replace selector, or enter OOF calibration. |
| selected prediction reference fields | selected `candidate_id`, `viterbi_proposed_candidate_id`, `viterbi_differs_from_node_top1`, `path_score`, `path_score_delta`, `node_score`, selected output fields | reference-only | May compare behavior after inference; must not score candidates in Phase4. |

## 7. Field Mapping Decisions Needed

Human review items:

- Confirm A001 as accepted v2.2 candidate bank.
- Confirm candidate bank SHA1 `6bb85d779ce3292f10539511224c8646cb8ee395`.
- Confirm A019 `final_gt_working.csv` as manual GT source.
- Confirm candidate `cx`/`cy` maps to `center_x`/`center_y`.
- Confirm `target_identity` maps to `row_id`.
- Confirm `sar_frame_num` maps to `frame_id`.
- Confirm `gm17_track_id` maps to `track_id`.
- Confirm `candidate_source` values and non-visible source families.
- Confirm direction posterior join from A007 to candidate rows.
- Confirm temporal prior join from A005 to candidate rows.
- Confirm track/frame ordering for transition.

## 8. Factor Readiness After Manifest

| factor | readiness status | basis | remaining gate |
|---|---|---|---|
| `geometry_factor` | ready_after_human_approval | A001 contains candidate geometry fields and candidate keys. | Human approval of A001, hash, and geometry field mapping. |
| `direction_factor` | needs_mapping | A007 and A008 expose posterior and joined direction fields. | Direction join, `P_*` policy, and source/direction ownership review. |
| controlled non-visible `source_factor` | needs_mapping | A001/A008 expose `candidate_source`. | Source-family normalization and visible-source isolation. |
| `optical_temporal_factor` | ready_after_human_approval | A005 contains temporal prior fields; A008 exposes candidate-level temporal consistency. | Human approval of A005 and soft-prior-only use. |
| `transition_factor` | needs_mapping | A001/A008 contain `gm17_track_id`, `sar_frame_num`, and candidate state. | Track/frame ordering and smoothness double-counting review. |
| `sar_structure_factor` | diagnostic_only | Diagnostic fields exist in A008/A017. | Not active Phase4 scoring. |
| `uncertainty_factor` | diagnostic_only | Uncertainty fields exist in A007/A008/A017/A018. | Not active Phase4 scoring. |
| `final_arbitration_factor` | diagnostic_only | Selector/gate/patch fields exist in A013/A018. | Blocked from active scoring and calibration. |
| visibility/missing extent/visible-full-center-offset | future_only | Visible/condition fields exist in A012/A021. | Future Phase7 only. |
| near-field route | future_only | Not a complete-vehicle Phase4 route. | Future geometry-regime work only. |

## 9. Recommended Scaffold Sequence

Recommended sequence:

1. geometry-only scaffold.
2. geometry + optical-temporal scaffold.
3. geometry + direction after mapping approval.
4. candidate-level fixed-prior scaffold.
5. transition/Viterbi scaffold after track/frame ordering approval.
6. min-cost-flow later.

This is better than jumping straight to min-cost-flow because:

- the current candidate bank and field gates still require human approval;
- geometry and temporal fields are the clearest local-data supports;
- direction fields require join and ownership review;
- source-family values require non-visible/visible separation;
- transition needs track/frame ordering validation and optical-temporal/transition double-counting control;
- min-cost-flow adds graph complexity before the candidate-level factor gates are stable.

## 10. Human Approval Checklist

Before any scaffold implementation, the researcher must approve:

- A001 candidate-bank path.
- Candidate-bank SHA1 `6bb85d779ce3292f10539511224c8646cb8ee395`.
- A005 optical temporal prior path.
- A007 direction posterior path.
- A008 candidate-factor join table role.
- A013 selected-prediction reference role as reference-only.
- A019 manual GT path as post-inference eval-only source.
- A021 condition label path as eval-only/future-branch source.
- `target_identity` to `row_id` mapping.
- `sar_frame_num` to `frame_id` mapping.
- `gm17_track_id` to `track_id` mapping.
- `cx`/`cy` to `center_x`/`center_y` mapping for candidates only.
- `candidate_source` source-family mapping and visible-source isolation.
- Direction posterior join keys and allowed `P_*` fields.
- Temporal prior join keys and soft-prior-only policy.
- Eval-only denylist.
- Diagnostic-only gate for SAR structure, uncertainty, final arbitration, B patch, visibility, missing extent, visible/full-center offset, selected-reference, and near-field fields.

## 11. Next Recommended Round

Recommended next Codex round after human review:

- create YAML manifest, inference allowlist, and eval-only denylist files after human approval; or
- create a geometry-only scaffold design if the user approves A001 and the basic geometry allowlist.

Do not recommend running experiments yet. Execution should remain blocked until the manifest, allowlist, denylist, candidate-bank hash gate, and human approvals are accepted.
