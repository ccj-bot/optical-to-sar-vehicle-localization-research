# GM17 Phase4 Data Schema Audit

Date: 2026-06-02

Status: Phase4 data availability and schema audit. This document checks current data support only. It does not authorize experiments, inference runs, training, calibration, candidate-bank changes, code changes, GM17 replacement, partial-visibility activation, near-field activation, staging, commit, or push.

Initial repository checks:

- `git status --short --untracked-files=no`: no tracked changes reported before this document was written.
- `git log --oneline --decorate -5`: current `HEAD -> main, origin/main, origin/HEAD` was `f6a5b52 docs: add external reconnaissance round1`.

## 1. Purpose

This document checks whether the actual project data supports the Phase4 fixed-prior revalidation design.

The current research direction is frozen SAR candidate-bank selection, not raw detection. Phase4 is intended to test fixed, non-learned priors over a frozen candidate bank using only allowed complete-vehicle factors:

- `geometry_factor`
- `direction_factor`
- controlled non-visible `source_factor`
- `optical_temporal_factor`
- `transition_factor`

External methods such as OBB schemas, Viterbi, MAP, min-cost-flow, and factor graphs remain references until the current data tables confirm the required fields, row keys, candidate keys, track keys, and inference/evaluation separation.

This round inspected tracked baseline documentation and schema contracts only. No experiment, inference run, metric computation, calibration, data modification, candidate-bank modification, or code modification was performed.

## 2. Data Sources Found

No concrete, repository-relative, inspectable candidate-bank or Phase4 data-table path was found in the allowed baseline document set.

The baseline documents identify conceptual sources and field origins, but they do not provide a formal Phase4 input manifest or concrete data paths to inspect. Therefore this audit did not read data rows, compute row counts, or compute candidate-bank hashes.

| Source described by baseline | Concrete path found | Tracked or untracked status | File type | Schema inspectable | Phase4-relevant | Baseline/runtime/unknown | Audit note |
|---|---|---|---|---|---|---|---|
| fixed v2.2 candidate bank | not found | unknown | unknown | no | yes | formal concept, not inspectable table | Required for Phase4, but no table path or hash was present in the allowed baseline docs. |
| candidate bank / diagnostic outputs | not found | unknown | unknown | no | yes | unknown | Field dictionary declares candidate-level fields but not a current file path. |
| signed escape posterior diagnostic | not found | unknown | unknown | no | yes | unknown | Direction fields are declared but no input table path was identified. |
| optical temporal inference tables | not found | unknown | unknown | no | yes | unknown | Temporal fields are declared but no input table path was identified. |
| state-energy diagnostic tables | not found | unknown | unknown | no | diagnostic only | unknown | Diagnostic fields are declared; Phase4 active use remains gated. |
| evaluation tables | not found | unknown | unknown | no | post-inference only | unknown | Eval-only fields are declared as blocked from inference, but no eval table path was identified. |

Because no concrete data path was found, all field availability judgments below are schema-contract judgments, not data-verified judgments.

## 3. Candidate Bank Reality Check

The tracked baseline supports the concept of a frozen v2.2 candidate bank. It does not currently provide enough concrete data information to verify that bank in this audit.

| Requirement | Status | Evidence from allowed baseline | Risk |
|---|---|---|---|
| candidate table | unclear | Baseline refers to fixed v2.2 candidate bank and candidate-level fields. | No table path was available for header or row-count inspection. |
| `candidate_id` | declared, not data-verified | `docs/gm17_factor_field_dictionary.md` lists it as candidate-level join key. | Cannot confirm uniqueness, stability, or table presence. |
| row identity | declared as `target_identity`, not data-verified | Field dictionary lists `target_identity` as boundary-safe row identity. | Required field name may need mapping to `row_id`. |
| frame identity | declared as `sar_frame_num`, not data-verified | Field dictionary lists it as frame-level metadata. | Required field name may need mapping to `frame_id`. |
| track identity | declared as `gm17_track_id`, not data-verified | Field dictionary lists it as track-level metadata. | Cannot confirm grouping or frame order without data. |
| candidate source family | declared as `candidate_source`, not data-verified | Field dictionary lists it as candidate-level source mapping. | Cannot confirm visible/non-visible family values. |
| selected prediction reference | unclear | Research spine and model spec refer to selected prediction behavior. | No concrete field or table path identified. |
| candidate-bank hash or version | version concept found, hash not found | Phase4 design refers to fixed v2.2 candidate bank. | Hash gate cannot run until candidate-bank path is provided. |

Candidate-bank conclusion: the baseline is consistent with a frozen-bank research design, but the current allowed documents do not expose an inspectable candidate-bank file path or hash. Phase4 scaffold implementation should not start until that path and hash policy are provided or formally manifested.

## 4. Field Availability Matrix

Availability statuses:

- `unclear`: field is declared or conceptually required, but no data table was inspectable.
- `not found`: field or direct equivalent was not found in the allowed baseline schema contract.
- `declared`: field is present in the baseline field dictionary, but still not data-verified.

| Required field | Found / not found / unclear | Source file if found | Inferred factor use | Leakage class | Risk note |
|---|---|---|---|---|---|
| `candidate_id` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | all candidate factors | inference_safe | Need table path to verify key uniqueness and join coverage. |
| `row_id` | not found; likely mapping needed | none; possible equivalent `target_identity` | row joins | unknown | Phase4 scaffold should map `row_id` to `target_identity` only after data check. |
| `frame_id` | not found; likely mapping needed | none; possible equivalent `sar_frame_num` | transition, optical temporal | unknown | Need confirm frame order column and type. |
| `track_id` | not found; likely mapping needed | none; possible equivalent `gm17_track_id` | transition, optical temporal | unknown | Need confirm per-track grouping key. |
| `r` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | geometry, transition | inference_safe | Need candidate table path. |
| `cross` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | geometry, transition | inference_safe | Need candidate table path. |
| `az` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | geometry, transition | inference_safe | Need candidate table path. |
| `center_x` | not found | none | possible OBB/cartesian schema | unknown | Do not infer from `final_cx`; final fields are eval-only. |
| `center_y` | not found | none | possible OBB/cartesian schema | unknown | Do not infer from `final_cy`; final fields are eval-only. |
| `heading` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | geometry, transition | inference_safe | Need verify units/convention. |
| `w` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | geometry, transition | inference_safe | Need verify units and positive range. |
| `h` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | geometry, transition | inference_safe | Need verify units and positive range. |
| `source_family` | not found; likely mapping needed | none; possible equivalent `candidate_source` | source factor | unknown | Need confirm visible/non-visible source labels. |
| `candidate_direction_bin` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | direction, transition | inference_safe | Need verify candidate-level join. |
| `signed_escape_decision` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | direction, transition | inference_safe | Need row-to-candidate join path. |
| `signed_direction_match` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | direction, source | inference_safe | Must not be double-counted through source without ownership declaration. |
| `posterior_confidence` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | direction; uncertainty diagnostic | inference_safe for direction use | Uncertainty use remains diagnostic-only. |
| `posterior_margin` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | direction; uncertainty diagnostic | inference_safe for direction use | Uncertainty use remains diagnostic-only. |
| `pred_r` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | optical temporal | inference_safe | Need temporal table path and join key. |
| `pred_cross` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | optical temporal | inference_safe | Need temporal table path and join key. |
| `pred_az` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | optical temporal | inference_safe | Need temporal table path and join key. |
| `optical_temporal_consistency_score` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | optical temporal, transition | inference_safe | Must remain soft prior only. |
| `temporal_factor_score` | declared, data availability unclear | `docs/gm17_factor_field_dictionary.md` | optical temporal | inference_safe | Need confirm it is not metric-derived. |
| `selected_prediction_reference` | unclear | model/spec docs discuss selected prediction behavior, but no field name found | audit comparison only | unknown | Need formal field/table name; must not contain GT-derived labels before inference. |
| GT fields | declared blocked as examples | `WORKSPACE_RULES.md`, `docs/gm17_factor_field_dictionary.md` | evaluation only | eval_only_blocked | Must be excluded from inference and path construction. |
| IoU fields | declared blocked as examples | `WORKSPACE_RULES.md`, `docs/gm17_factor_field_dictionary.md` | evaluation only | eval_only_blocked | Includes `candidate_iou`, `rot_iou`. |
| center error fields | declared blocked as examples | `WORKSPACE_RULES.md`, `docs/gm17_factor_field_dictionary.md` | evaluation only | eval_only_blocked | Includes `candidate_center_err_px`, `center_err_px`. |
| oracle fields | declared blocked as examples | `WORKSPACE_RULES.md`, `docs/gm17_factor_prior_registry.md` | evaluation only | eval_only_blocked | Must not enter inference or candidate filtering. |
| truncation label | declared blocked as `truncation_degree` | `docs/gm17_factor_field_dictionary.md` | evaluation/group audit only | eval_only_blocked | Future partial-visibility branch only. |
| occlusion label | declared blocked as `occlusion_degree` | `docs/gm17_factor_field_dictionary.md` | evaluation/group audit only | eval_only_blocked | Future partial-visibility branch only. |

## 5. Factor Feasibility Assessment

### geometry_factor

Feasibility: `needs_mapping`

Geometry fields are declared: `r`, `cross`, `az`, `heading`, `w`, `h`, plus diagnostic geometry support fields. However, no current candidate table path was identified, so the scaffold cannot verify headers, numeric types, missingness, ranges, or candidate-level join keys.

Minimum next check:

- inspect candidate-bank table header;
- verify `candidate_id`, row identity, `r`, `cross`, `az`, `heading`, `w`, and `h`;
- confirm whether `center_x`/`center_y` are absent by design or stored under another inference-safe name.

### direction_factor

Feasibility: `needs_mapping`

Direction fields are declared: `candidate_direction_bin`, `signed_escape_decision`, `signed_direction_match`, `posterior_confidence`, and `posterior_margin`. No source table path or join path was identified.

Minimum next check:

- identify the signed escape posterior table;
- verify row-level keys and candidate-level direction joins;
- ensure `signed_direction_match` is owned by direction or gated source context, not counted twice.

### controlled non-visible source_factor

Feasibility: `needs_mapping`

The baseline declares `candidate_source`, while the requested schema uses `source_family`. This is likely a field-name mapping issue. The data must confirm actual source-family values and whether visible source can be separated from non-visible families.

Minimum next check:

- inspect candidate source column values;
- confirm non-visible families such as base, wedge, bidirectional, and track-signed;
- confirm visible behavior is present only as veto/uncertainty context and not as full-center source evidence.

### optical_temporal_factor

Feasibility: `needs_mapping`

The baseline declares `pred_r`, `pred_cross`, `pred_az`, `optical_temporal_consistency_score`, `temporal_factor_score`, `gm17_track_id`, and `sar_frame_num`. No optical temporal table path was found.

Minimum next check:

- identify the optical temporal inference table;
- verify row and track keys;
- confirm temporal fields are inference-safe and not derived from eval labels;
- preserve the soft-prior-only rule.

### transition_factor

Feasibility: `needs_mapping`

The baseline declares the required conceptual ingredients for per-track transitions: candidate state fields, `gm17_track_id`, `sar_frame_num`, and direction state. No table path was available to verify whether adjacent candidate edges can be constructed.

Minimum next check:

- inspect whether every candidate row has track and frame order;
- verify frame ordering within each track;
- confirm candidate counts per frame;
- confirm no eval-only fields are needed to build edges.

## 6. Transition Modeling Feasibility

Current recommendation: blocked until track/frame structure is clarified.

The literature direction supports per-track Viterbi, MAP, min-cost-flow, or factor-graph path selection. The baseline model spec also describes MAP/Viterbi over fixed candidate paths. However, the actual data-table path and header were not available in this audit.

Data reason:

- `gm17_track_id` is declared but not data-verified.
- `sar_frame_num` is declared but not data-verified.
- candidate counts per frame are unknown.
- candidate identity stability across row/frame joins is unknown.
- no edge-construction input table was identified.

Practical consequence:

- per-track chain Viterbi is the most plausible first transition scaffold if `gm17_track_id` and `sar_frame_num` are verified;
- min-cost-flow should remain later because it adds graph complexity before data availability is proven;
- candidate-level fixed-prior scoring is also blocked from implementation until candidate-bank paths are provided, though it is simpler than transition modeling.

## 7. Inference/Evaluation Separation Check

Evaluation-only fields must be excluded from inference inputs, candidate scoring, path construction, missing-value policy, factor inclusion, and inference outputs.

Fields explicitly blocked by the baseline include:

- GT fields;
- oracle fields;
- `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg`;
- `candidate_iou`;
- `candidate_center_err_px`;
- `rot_iou`;
- `center_err_px`;
- condition labels;
- `truncation_degree`;
- `occlusion_degree`.

Because no data table was inspectable, this audit cannot determine whether eval-only labels appear in the same table as inference fields.

Before any Phase4 execution scaffold, the project needs:

- a column-level allowlist for inference;
- a column-level denylist for eval-only fields;
- a rule that evaluation labels are joined only after inference outputs exist;
- a boundary check that inference outputs contain no eval-only columns.

## 8. Data-Driven Scaffold Recommendation

Recommended outcome: `blocked_until_data_paths_provided`

The external literature direction remains scientifically coherent, but implementation should not start from literature alone. The current allowed baseline documents do not provide inspectable data paths for the fixed candidate bank, direction posterior, optical temporal priors, or evaluation tables.

If data paths are provided and headers match the declared schema, the likely scaffold sequence is:

1. `geometry_only_scaffold_first`
2. `geometry_direction_scaffold_first`
3. `candidate_level_fixed_prior_scaffold`
4. `candidate_plus_transition_viterbi_scaffold`
5. `min_cost_flow_scaffold_later`

The current audit supports only this sequence as a conditional plan, not as an executable scaffold.

## 9. Missing Data Or Clarification Needed

The following paths, columns, or metadata must be provided or formally manifested before scaffold implementation:

- current fixed v2.2 candidate-bank table path;
- candidate-bank hash or version manifest;
- candidate-bank header with `candidate_id`, row identity, candidate geometry, and source-family fields;
- formal mapping between `row_id` and `target_identity`, if `target_identity` is the current row key;
- formal mapping between `track_id` and `gm17_track_id`, if `gm17_track_id` is the current track key;
- formal mapping between `frame_id` and `sar_frame_num`, if `sar_frame_num` is the current frame key;
- formal mapping between `source_family` and `candidate_source`, if `candidate_source` is the current source field;
- signed escape posterior table path and join keys;
- optical temporal inference table path and join keys;
- selected prediction reference table path and field name, if Phase4 compares to staged GM17 selected behavior;
- explicit eval-only table path or post-inference join plan;
- inference allowlist and eval-only denylist for any future scaffold.

## 10. Updated Research Judgment

The external literature direction remains valid as a research direction, but it is not yet data-verified for implementation.

Updated judgments:

- OBB/geometry schema is conceptually supported by declared fields `r`, `cross`, `az`, `heading`, `w`, and `h`, but no candidate table path was available to verify actual data.
- Direction modeling is conceptually supported by declared signed-escape and direction-match fields, but no direction posterior table path was available.
- Controlled source modeling is conceptually supported by `candidate_source`, but visible/non-visible family separation cannot be verified without data.
- Optical temporal modeling is conceptually supported by declared temporal prior fields, but no optical temporal table path was available.
- Transition modeling is conceptually supported by `gm17_track_id` and `sar_frame_num`, but actual track/frame structure and candidate counts are unverified.
- SAR structure, uncertainty, final arbitration, visibility, missing extent, visible/full-center offset, and near-field remain excluded or diagnostic/future-only and must not enter active Phase4 scoring.

Research conclusion:

```text
OBB/geometry schema plus track-level candidate path selection using MAP/Viterbi/min-cost-flow/factor graph ideas remains the strongest external direction, but Phase4 scaffold work is blocked until current data paths, headers, join keys, and allowlists are verified.
```

## 11. Recommended Next Round

Recommended next Codex round: data-path clarification and allowed-field manifest creation.

The next round should not run experiments. It should:

- identify the current fixed v2.2 candidate-bank table path;
- inspect headers, row counts, and candidate-bank hash only after the path is explicitly provided or found in a formal manifest;
- identify direction posterior and optical temporal table paths;
- create a Phase4 allowed-field manifest;
- create an eval-only denylist;
- decide whether the first executable scaffold should be geometry-only or geometry+direction after data availability is verified.

Do not start Phase4 execution, Viterbi path construction, min-cost-flow modeling, training, calibration, candidate-bank changes, GM17 replacement, or partial/near-field branch activation until these data gates are resolved.
