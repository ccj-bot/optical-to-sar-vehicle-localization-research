# GM17 Phase4 Local Data Inventory And Manual-GT Audit

Date: 2026-06-02

Status: local data inventory and manual-GT audit for Phase4 planning. This is not experiment execution. It does not authorize inference runs, metrics, training, calibration, candidate-bank modification, code modification, GM17 replacement, partial-visibility activation, near-field activation, staging, commit, or push.

Initial repository checks:

- `git status --short --untracked-files=no`: no tracked changes reported before this document was written.
- `git log --oneline --decorate -5`: current `HEAD -> main` was `d198ae5 docs: add phase4 data schema audit`.

## 1. Purpose

This document inventories local data assets and manual GT annotations to support Phase4 fixed-prior revalidation planning.

The project studies optical-to-SAR vehicle localization as frozen SAR candidate-bank selection. Manual GT boxes and condition labels are evaluation-only. They may be inventoried and used later for post-inference evaluation, but they must not be used for inference, candidate scoring, path construction, factor selection, or missing-value policy.

This round inspected local paths, metadata, headers, row counts, a tiny first-row schema sample where useful, and one candidate-bank hash. It did not run experiments or inference.

## 2. Discovery Method

Methods used:

- Required repository checks with `git status --short --untracked-files=no` and `git log --oneline --decorate -5`.
- Top-level directory listing with `Get-ChildItem`.
- Lightweight recursive metadata scan over likely directories.
- Header and row-count inspection for CSV files.
- JSON key inspection for boundary reports and run manifests.
- SHA1 computation only for the main candidate-bank-like file.

Directories inspected:

- `docs/`
- `logs/`
- `output/`
- `outputs/` when present
- `artifacts/`
- `archive/`
- `tasks/`
- `tools/`
- `data/` when present
- `datasets/` when present
- `annotations/` when present
- `labels/` when present
- `results/` when present
- `reports/` when present

File extensions considered:

- `.csv`, `.tsv`, `.json`, `.jsonl`, `.parquet`, `.pkl`, `.xlsx`, `.txt`, `.md`, `.yaml`, `.yml`, `.npz`, `.npy`, `.mat`

Limitations:

- The scan did not recursively dump file contents.
- Large CSVs were inspected by header, row count, metadata, and selected schema samples only.
- Heuristic category counts are inventory aids, not formal baseline judgments.
- Local runtime outputs are not formal baseline unless human review accepts them.
- Old prompt dumps were not used as scientific evidence.
- `data/`, `datasets/`, `annotations/`, `labels/`, `results/`, and `reports/` were considered, but only existing paths contributed files.

Inventory category counts from the heuristic scan:

| category | assets_found |
|---|---:|
| `diagnostic_output` | 97 |
| `selected_prediction_reference` | 82 |
| `eval_only_labels` | 67 |
| `research_note` | 59 |
| `runtime_output` | 42 |
| `script_or_tool_reference` | 41 |
| `manual_gt_boxes` | 11 |
| `candidate_table` | 5 |
| `direction_posterior` | 4 |
| `optical_temporal_prior` | 2 |
| `candidate_bank_candidate` | 2 |

## 3. Local Data Asset Overview

| asset_id | path | file_type | size | modified_time | category | schema_inspected | row_count_if_available | hash_if_available | current_status | notes |
|---|---|---|---:|---|---|---|---:|---|---|---|
| A001 | `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv` | CSV | 26799739 | 2026-06-01T10:08:09 | `candidate_bank_candidate` | yes | 58251 | SHA1 `6bb85d779ce3292f10539511224c8646cb8ee395` | likely_current | Best local candidate for fixed v2.2 Phase4 bank; local runtime output, not tracked. |
| A002 | `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_oracle_eval.csv` | CSV | 34715625 | 2026-06-01T10:08:14 | `eval_only_labels` | yes | 58251 | not computed | likely_current | Eval-only candidate oracle table; contains GT/final/IoU/error/oracle columns. |
| A003 | `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/boundary_check_report.json` | JSON | 1953 | 2026-06-01T10:08:14 | `diagnostic_output` | yes | n/a | not computed | likely_current | Identifies checked inference inputs and reports no forbidden columns in candidate bank. |
| A004 | `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/gm17_hard_candidate_expansion_v2_summary.json` | JSON | 3956 | 2026-06-01T10:08:15 | `diagnostic_output` | yes | n/a | not computed | likely_current | Runtime summary; useful for version label only, not a Phase4 result source. |
| A005 | `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv` | CSV | 64342 | 2026-05-31T21:05:17 | `optical_temporal_prior` | yes | 205 | not computed | likely_current | GM17 temporal prior table with `pred_r`, `pred_az`, `pred_cross`, `temporal_factor_score`, `gm17_track_id`. |
| A006 | `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_eval.csv` | CSV | 91765 | 2026-05-31T21:05:17 | `eval_only_labels` | yes | 205 | not computed | likely_current | Eval counterpart of temporal inference table; contains final boxes and error fields. |
| A007 | `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/signed_escape_posterior_inference.csv` | CSV | 100114 | 2026-06-01T11:55:05 | `direction_posterior` | yes | 205 | not computed | likely_current | Direction posterior table with `P_*`, `posterior_confidence`, `posterior_margin`, `signed_escape_decision`. |
| A008 | `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/candidate_refined_factor_inference.csv` | CSV | 41496586 | 2026-06-01T11:55:08 | `candidate_table` | yes | 58251 | not computed | needs_human_review | Rich candidate-factor table with geometry, direction, posterior, and diagnostic fields; not the frozen bank itself. |
| A009 | `output/clean_no_gt_localizer_2026-05-31_gm17_wedge_escape/gm17_track_signed_modes_inference.csv` | CSV | 176564 | 2026-05-31T22:28:56 | `direction_posterior` | yes | 205 | not computed | needs_human_review | Track-signed support table. |
| A010 | `output/clean_no_gt_localizer_2026-05-31_gm17_wedge_escape/gm17_wedge_profile_modes_inference.csv` | CSV | 384416 | 2026-05-31T22:28:51 | `direction_posterior` | yes | 993 | not computed | needs_human_review | Wedge/profile mode source; row count differs from GM17 rows because multiple modes exist. |
| A011 | `output/clean_no_gt_localizer_2026-05-31_gm17_ray_profile/gm17_range_posterior_modes_inference.csv` | CSV | 166760 | 2026-05-31T21:09:31 | `direction_posterior` | yes | 903 | not computed | needs_human_review | Range posterior modes source. |
| A012 | `output/clean_no_gt_localizer_2026-05-31_visible_extent_gated/visible_extent_features.csv` | CSV | 133385 | 2026-05-31T21:06:02 | `diagnostic_output` | yes | 422 | not computed | needs_human_review | Visible support/extent diagnostics; future/diagnostic only, not active Phase4 scoring. |
| A013 | `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/track_viterbi_selected_inference.csv` | CSV | 167677 | 2026-06-01T12:06:12 | `selected_prediction_reference` | yes | 205 | not computed | needs_human_review | Selected-prediction inference output; useful as staged behavior reference, not candidate-bank input. |
| A014 | `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/track_viterbi_selected_eval.csv` | CSV | 263425 | 2026-06-01T12:06:13 | `selected_prediction_reference` | yes | 205 | not computed | needs_human_review | Eval counterpart; contains final boxes, condition labels, and selected metrics. |
| A015 | `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/track_viterbi_path_diagnostics.csv` | CSV | 109051 | 2026-06-01T12:06:12 | `diagnostic_output` | yes | 205 | not computed | needs_human_review | Path diagnostic output; contains candidate/path scores and final candidate fields. |
| A016 | `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/boundary_check_report.json` | JSON | 2682 | 2026-06-01T12:06:13 | `diagnostic_output` | yes | n/a | not computed | needs_human_review | Reports input SHA1s and forbidden-column checks for Viterbi selector outputs. |
| A017 | `output/clean_no_gt_localizer_2026-06-01_gm17_factor_graph_diagnostic/factor_graph_potentials_inference.csv` | CSV | 35318856 | 2026-06-01T22:28:44 | `diagnostic_output` | yes | 58251 | not computed | needs_human_review | Factor graph diagnostic potentials; contains final-action latent fields and must remain diagnostic. |
| A018 | `output/clean_no_gt_localizer_2026-06-01_gm17_gate_minimal_patch/patched_selected_inference.csv` | CSV | 635180 | 2026-06-01T13:47:25 | `diagnostic_output` | yes | 615 | not computed | needs_human_review | Patch comparison output; B patch fields are diagnostic only. |
| A019 | `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv` | CSV | 190010 | 2026-05-28T17:27:25 | `manual_gt_boxes` | yes | 442 | not computed | likely_current | Canonical-looking manual GT working table; evaluation-only. |
| A020 | `output/hermes_annotation_consolidation_2026-05-20/00_tables/review_queue.csv` | CSV | 150281 | 2026-05-28T17:27:25 | `manual_gt_boxes` | yes | 442 | not computed | likely_current | Review queue with final-box columns; queue state is not necessarily final truth. |
| A021 | `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv` | CSV | 87713 | 2026-05-28T17:27:25 | `eval_only_labels` | yes | 442 | not computed | likely_current | Manual truncation/occlusion/condition labels; evaluation/future-branch only. |
| A022 | `output/hermes_annotation_consolidation_2026-05-20/00_tables/candidate_boxes_long.csv` | CSV | 529159 | 2026-05-22T08:56:28 | `candidate_table` | yes | 1315 | not computed | historical | Human-review candidate source table for earlier annotation workflow, not GM17 v2.2 bank. |
| A023 | `output/hermes_annotation_consolidation_2026-05-20/00_tables/candidate_groups.csv` | CSV | 92004 | 2026-05-22T08:56:28 | `candidate_table` | yes | 336 | not computed | historical | Candidate grouping/review support table. |
| A024 | `output/dataset_freeze_20260525_043207/final_gt.csv` | CSV | 122861 | 2026-05-24T18:09:17 | `manual_gt_boxes` | yes | 336 | not computed | historical | Frozen GT snapshot; likely superseded by `final_gt_working.csv` but needs human confirmation. |
| A025 | `output/dataset_freeze_20260525_043207/visibility_conditions.csv` | CSV | 64191 | 2026-05-24T22:09:48 | `eval_only_labels` | yes | 336 | not computed | historical | Frozen condition labels. |
| A026 | `output/gm11_sar250_300_supplement_2026-05-28/00_tables/gm11_sar250_300_supplement_final_gt_ready.csv` | CSV | 66979 | 2026-05-28T17:19:01 | `manual_gt_boxes` | yes | 106 | not computed | historical | Supplement final-GT-ready table later merged into canonical table. |
| A027 | `output/gm11_sar250_300_supplement_2026-05-28/00_tables/gm11_sar250_300_supplement_boxes.csv` | CSV | 52972 | 2026-05-28T17:19:01 | `manual_gt_boxes` | yes | 106 | not computed | historical | Supplement manual box/source table. |
| A028 | `output/part1_localization_2026-05-25/manual_annotations_RM011_250_300.csv` | CSV | 64 | 2026-05-28T14:02:10 | `manual_gt_boxes` | yes | 1 | not computed | historical | Small manual annotation file with OBB-like fields. |
| A029 | `output/part1_localization_2026-05-25/candidate_oracle.csv` | CSV | 39595 | 2026-05-25T17:05:15 | `eval_only_labels` | yes | 322 | not computed | historical | Oracle/eval table; not inference-safe. |
| A030 | `logs/clean_no_gt_localizer_2026-05-31.md` | Markdown | 43979 | 2026-06-01T13:48:35 | `research_note` | yes | n/a | not computed | needs_human_review | Runtime log for no-GT localizer line; useful for path provenance only. |
| A031 | `docs/gm17_next_step_research_decision.md` | Markdown | 10185 | 2026-06-01T10:06:21 | `research_note` | yes | n/a | not computed | needs_human_review | Research decision note that names v2.2 inputs and outputs. |

## 4. Candidate Bank And Candidate Table Candidates

| path | candidate_id presence | row/frame key presence | track key presence | geometry fields | source field | direction fields | selected prediction in same file | eval-only fields in same file | risk notes |
|---|---|---|---|---|---|---|---|---|---|
| `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv` | yes | `target_identity`, `sar_frame`, `sar_frame_num` | `gm17_track_id` | `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross`, `delta_*` | `candidate_source` | no `candidate_direction_bin`; has candidate expansion metadata | no | no forbidden eval fields found in boundary report | Best candidate-bank file; local runtime output must be human-approved as Phase4 bank. |
| `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/candidate_refined_factor_inference.csv` | yes | `target_identity`, `sar_frame`, `sar_frame_num` | `gm17_track_id` | `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross`, `delta_*`, `refined_geometry_score` | `candidate_source` | `candidate_direction_bin`, `signed_direction_match`, `signed_escape_decision`, `P_*`, `posterior_confidence`, `posterior_margin` | no | no obvious eval-only fields in header | Rich candidate factor table; includes diagnostic SAR/uncertainty fields that must be allowlisted/gated. |
| `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/track_viterbi_selected_inference.csv` | yes | `target_identity`, `sar_frame`, `sar_frame_num` | `gm17_track_id` | `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross` | `candidate_source`, `source_prior` | `candidate_direction_bin`, `signed_direction_match`, `signed_escape_decision`, `P_*` | yes, selected candidate output | no forbidden columns reported by boundary check | Useful selected-prediction reference, not raw candidate bank. Contains diagnostic gate and path fields. |
| `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/track_viterbi_path_diagnostics.csv` | yes | `target_identity`, `sar_frame_num` | `gm17_track_id` | no full geometry fields | `candidate_source` | `candidate_direction_bin`, `signed_escape_decision` | yes | contains fields named `final_candidate_*`; not GT final boxes but naming is risky | Diagnostic only; do not use as Phase4 candidate table without review. |
| `output/clean_no_gt_localizer_2026-05-31_gm17_wedge_escape/gm17_wedge_escape_candidate_bank_inference.csv` | yes | `target_identity`, `sar_frame_num` | not found in header | `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross` | not found in inspected header sample | no | has `final_score` naming risk | Historical candidate-bank-like file; likely pre-v2.2 and should not be Phase4 bank. |
| `output/hermes_annotation_consolidation_2026-05-20/00_tables/candidate_boxes_long.csv` | no `candidate_id`; has candidate rank/source | `target_identity`, `sar_frame`, `sar_frame_num` | no | `cx`, `cy`, `w`, `h`, `heading_deg`, axis-aligned fields | `candidate_source` | no | no | Manual review candidate table, not GM17 v2.2 bank. |

## 5. Manual GT Box Inventory

Manual GT boxes are evaluation-only and must not enter Phase4 inference.

| path | annotation format | likely coordinate format | OBB or axis-aligned | likely fields | linked to frame/track/candidate | eval-only status | risk notes |
|---|---|---|---|---|---|---|---|
| `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv` | CSV manual final GT table | pixel center/size/heading plus axis-aligned extents | OBB plus axis-aligned box | `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg`, `final_ax_*` | linked by `target_identity`, `scene`, `sar_frame`, `sar_frame_num`; no candidate_id | eval-only | Likely current canonical GT table, but human must confirm. |
| `output/hermes_annotation_consolidation_2026-05-20/00_tables/review_queue.csv` | CSV review queue | pixel final box columns plus optical bbox | OBB-like final fields | `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg`, optical `opt_*` fields | linked by `target_identity`, frame fields; queue state only | eval-only | Queue may contain pending/review state; do not treat as final truth without `final_gt_working.csv`. |
| `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv` | CSV condition labels | non-box label table | n/a | `condition_type`, `truncation_degree`, `occlusion_degree` | linked by `target_identity`, `scene`, `sar_frame_num` | eval-only | Partial-visibility labels remain future/eval-only. |
| `output/dataset_freeze_20260525_043207/final_gt.csv` | CSV dataset freeze | pixel center/size/heading plus axis-aligned extents | OBB plus axis-aligned box | `final_*`, `final_ax_*` | linked by `target_identity`, frame fields | eval-only | Historical freeze, likely superseded. |
| `output/dataset_freeze_20260525_043207/visibility_conditions.csv` | CSV dataset freeze | condition labels | n/a | `condition_type`, `truncation_degree`, `occlusion_degree` | linked by `target_identity`, frame fields | eval-only | Historical freeze. |
| `output/gm11_sar250_300_supplement_2026-05-28/00_tables/gm11_sar250_300_supplement_final_gt_ready.csv` | CSV supplement final GT | pixel center/size/heading plus axis-aligned extents | OBB plus axis-aligned box | `final_*`, `final_ax_*` | linked by `target_identity`, frame fields | eval-only | Supplement source later merged; historical unless user says otherwise. |
| `output/gm11_sar250_300_supplement_2026-05-28/00_tables/gm11_sar250_300_supplement_boxes.csv` | CSV supplement boxes | pixel center/size/heading | OBB-like | `cx`, `cy`, `w`, `h`, `heading_deg`, condition fields | linked by target/frame and optical link fields | eval-only | Manual boxes despite non-`final_` column names; must not be inference input. |
| `output/part1_localization_2026-05-25/manual_annotations_RM011_250_300.csv` | small CSV manual annotations | pixel center/size/heading | OBB-like | `frame`, `cx`, `cy`, `w`, `h`, `heading_deg` | frame only | eval-only | Tiny historical manual file with one row. |

## 6. Field Availability Matrix From Local Data

| Phase4 required field | found / not found / unclear | actual local field name | source file | leakage class | factor use | risk note |
|---|---|---|---|---|---|---|
| `candidate_id` | found | `candidate_id` | A001, A008, A013 | inference-safe | all candidate factors | Use A001 as bank key; selected outputs are references only. |
| `row_id` or `target_identity` | found | `target_identity` | A001, A005, A007, A008, A013, A019 | inference-safe for candidate/inference tables; eval-only for GT tables | joins | Use `target_identity` as row key. |
| `frame_id` or `sar_frame_num` | found | `sar_frame_num`, `sar_frame` | A001, A005, A007, A008, A013 | inference-safe | transition, temporal | Use `sar_frame_num` for ordering after numeric-type check. |
| `track_id` or `gm17_track_id` | found | `gm17_track_id` | A001, A005, A007, A008, A013 | inference-safe | transition, temporal | Needs human review of track grouping. |
| `r` | found | `r` | A001, A008, A013 | inference-safe | geometry, transition | Candidate-bank value available. |
| `cross` | found | `cross` | A001, A008, A013 | inference-safe | geometry, transition | Candidate-bank value available. |
| `az` | found | `az` | A001, A008, A013 | inference-safe | geometry, transition | Candidate-bank value available. |
| `center_x` | found as mapping | `cx`; eval-only equivalent `final_cx` | A001 for inference-safe candidate center; A019 for GT | inference-safe only for `cx`; eval-only for `final_cx` | geometry | Manifest should map candidate `center_x` to `cx`, never to `final_cx`. |
| `center_y` | found as mapping | `cy`; eval-only equivalent `final_cy` | A001 for inference-safe candidate center; A019 for GT | inference-safe only for `cy`; eval-only for `final_cy` | geometry | Manifest should map candidate `center_y` to `cy`, never to `final_cy`. |
| `heading` | found | `heading`; GT uses `final_heading_deg`; manual boxes use `heading_deg` | A001, A008, A019, A027 | inference-safe for candidate `heading`; eval-only for manual/final fields | geometry, transition | Confirm degrees and sign convention. |
| `w` | found | `w`; GT uses `final_w` | A001, A008, A019 | inference-safe for candidate `w`; eval-only for GT | geometry, transition | Candidate size available. |
| `h` | found | `h`; GT uses `final_h` | A001, A008, A019 | inference-safe for candidate `h`; eval-only for GT | geometry, transition | Candidate size available. |
| `source_family` or `candidate_source` | found | `candidate_source`; diagnostic `source_family_state` | A001, A008, A013, A017 | inference-safe for `candidate_source`; diagnostic for state labels | source factor | Need source family normalization and visible/non-visible separation. |
| `candidate_direction_bin` | found | `candidate_direction_bin` | A008, A013 | inference-safe | direction, transition | Not present in raw A001 bank; available after factor join. |
| `signed_escape_decision` | found | `signed_escape_decision` | A007, A008, A013 | inference-safe | direction, transition | Row-level posterior joined to candidates. |
| `signed_direction_match` | found | `signed_direction_match` | A008, A013 | inference-safe but ownership-gated | direction/source | Must not be counted twice as independent source evidence. |
| `posterior_confidence` | found | `posterior_confidence` | A007, A008, A013 | inference-safe for direction use; diagnostic for uncertainty | direction | Do not activate uncertainty factor. |
| `posterior_margin` | found | `posterior_margin` | A007, A008, A013 | inference-safe for direction use; diagnostic for uncertainty | direction | Do not activate uncertainty factor. |
| `pred_r` | found | `pred_r` | A005, A010, A013 eval output | inference-safe in A005 | optical temporal | Use A005 as temporal prior source. |
| `pred_cross` | found | `pred_cross` | A005, A010, A013 eval output | inference-safe in A005 | optical temporal | Use A005 as temporal prior source. |
| `pred_az` | found | `pred_az` | A005, A010, A013 eval output | inference-safe in A005 | optical temporal | Use A005 as temporal prior source. |
| `optical_temporal_consistency_score` | found | `optical_temporal_consistency_score` | A008, A013 | inference-safe | optical temporal | Candidate-level joined prior available. |
| `temporal_factor_score` | found | `temporal_factor_score` | A001, A005, A013 eval output | inference-safe in A001/A005 | optical temporal | Soft-prior-only. |
| `selected_prediction_reference` | found as output | selected row in `track_viterbi_selected_inference.csv`; selected `candidate_id` | A013 | diagnostic/staged reference | comparison only | Do not use as inference input for Phase4 candidate scoring. |
| GT box fields | found | `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg`, `final_ax_*` | A019, A024, A026 | eval-only | post-inference evaluation | Manual GT only. |
| IoU / center error / oracle / final annotation fields | found | `candidate_iou`, `rot_iou`, `center_err_px`, `candidate_center_err_px`, `oracle_*`, `final_*` | A002, A006, A014, A029 | eval-only | post-inference evaluation | Mixed eval tables require strict denylist. |

## 7. Factor Feasibility From Local Data

### geometry_factor

Feasibility: `ready_for_scaffold`

Local-data reason: A001 has `candidate_id`, row/frame/track keys, `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross`, and `delta_*` fields. A008 adds `refined_geometry_score` and `geometry_escape_refined_score`, but those are diagnostic/ownership-gated. A geometry-only scaffold can start from A001 after human confirmation that A001 is the accepted v2.2 bank.

### direction_factor

Feasibility: `needs_mapping`

Local-data reason: A007 supplies row-level signed posterior fields, and A008/A013 contain candidate-joined `candidate_direction_bin`, `signed_direction_match`, `posterior_confidence`, `posterior_margin`, and `signed_escape_decision`. The mapping and ownership split need review before scaffold use.

### controlled non-visible source_factor

Feasibility: `needs_mapping`

Local-data reason: `candidate_source` exists in A001/A008/A013. Human review must normalize source families and confirm which values are non-visible. Source must not inherit `directional_shell_score`, `track_escape_evidence`, or `signed_direction_match` as independent source-prior evidence without ownership declaration.

### optical_temporal_factor

Feasibility: `ready_for_scaffold`

Local-data reason: A005 has `pred_r`, `pred_az`, `pred_cross`, `temporal_factor_score`, `gm17_track_id`, `sar_frame_num`, and candidate count metadata. A001 also carries `temporal_factor_score`. Use as soft prior only.

### transition_factor

Feasibility: `needs_mapping`

Local-data reason: A001/A008/A013 contain `gm17_track_id` and `sar_frame_num`, and A013/A015 show that prior Viterbi-style path diagnostics exist. A Phase4 transition scaffold still needs a human-approved manifest and row/frame ordering check. Per-track Viterbi is more appropriate than min-cost-flow as the first transition route.

## 8. Inference/Evaluation Separation Risk

The local inventory found many files that mix inference-style columns and eval-only columns. Examples include:

- `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_oracle_eval.csv`
- `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_eval.csv`
- `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/track_viterbi_selected_eval.csv`
- `output/clean_no_gt_localizer_2026-06-01_gm17_gate_minimal_patch/patched_selected_eval.csv`
- `output/dataset_freeze_20260525_043207/final_gt.csv`
- `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv`

Recommended separation before any scaffold:

- create an inference allowlist for A001/A005/A007/A008-derived fields;
- create an eval-only denylist covering `gt_*`, `oracle_*`, `final_*`, `candidate_iou`, `candidate_center_err_px`, `rot_iou`, `center_err_px`, `selected_iou`, `selected_center_err_px`, `condition_type`, `truncation_degree`, and `occlusion_degree`;
- join manual GT and eval labels only after inference output exists;
- keep selected-prediction references out of factor scoring;
- keep B patch and final arbitration diagnostics out of active Phase4 scoring.

Special naming risk:

- `output/clean_no_gt_localizer_2026-05-31_gm17_wedge_escape/gm17_wedge_escape_candidate_bank_inference.csv` contains `final_score`. This appears score-like rather than GT, but the `final_*` prefix is boundary-risky. Treat that older candidate-bank-like table as historical unless reviewed.

## 9. Candidate Bank Hash And Version Status

Main candidate-bank-like file:

```text
output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv
```

Computed SHA1:

```text
6bb85d779ce3292f10539511224c8646cb8ee395
```

Boundary report cross-check:

- `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/boundary_check_report.json` records `candidate_bank_before` and `candidate_bank_after` as the same SHA1.
- `candidate_bank_modified`: `false`
- `candidate_generation_changed`: `false`

Hash policy recommendation:

- accept A001 only after human review as the Phase4 candidate bank path;
- record SHA1 before every future scaffold run;
- fail any scaffold run if SHA1 changes without explicit authorization;
- never regenerate or modify this file in Phase4 audit/scaffold rounds.

## 10. Recommended Phase4 Data Manifest

Do not create the manifest in this round. A future manifest should use this structure:

| manifest_key | recommended local value | status |
|---|---|---|
| `candidate_bank_path` | `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv` | needs human approval |
| `candidate_bank_hash` | `6bb85d779ce3292f10539511224c8646cb8ee395` | computed in this audit |
| `candidate_table_path` | `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/candidate_refined_factor_inference.csv` | needs mapping/allowlist |
| `direction_posterior_path` | `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/signed_escape_posterior_inference.csv` | needs mapping/allowlist |
| `optical_temporal_prior_path` | `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv` | likely current |
| `selected_prediction_reference_path` | `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/track_viterbi_selected_inference.csv` | diagnostic/staged reference only |
| `manual_gt_box_path` | `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv` | needs human approval |
| `eval_only_label_path` | `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv` plus eval counterparts | eval-only |
| `inference_allowlist_path` | to create in later round | missing |
| `eval_denylist_path` | to create in later round | missing |

## 11. Updated Phase4 Scaffold Recommendation

Recommended scaffold path: `geometry_direction_scaffold_first`

Reason:

- Geometry fields are directly present in the candidate bank A001.
- Temporal priors and track/frame keys are present and can support soft priors.
- Direction posterior fields exist in A007 and candidate-joined direction fields exist in A008, but they require mapping/ownership review.
- Source fields exist but need visible/non-visible source-family normalization.
- Transition fields exist, but transition should wait until candidate-level geometry/direction mapping and row/frame ordering are reviewed.

Detailed sequence:

1. Create Phase4 data manifest.
2. Create inference allowlist and eval-only denylist.
3. Start with `geometry_only_scaffold_first` if the user wants maximum caution.
4. Move to `geometry_direction_scaffold_first` after direction joins are reviewed.
5. Move to `candidate_level_fixed_prior_scaffold`.
6. Add `candidate_plus_transition_viterbi_scaffold` after track/frame ordering is verified.
7. Keep `min_cost_flow_scaffold_later`.

Do not start execution yet. This recommendation is for scaffold design after human review.

## 12. Human Review Checklist

The human researcher must confirm:

- A001 is the current accepted v2.2 candidate bank.
- The candidate bank SHA1 `6bb85d779ce3292f10539511224c8646cb8ee395` should be accepted as the Phase4 boundary hash.
- A008 is the correct candidate-factor join table or should be rebuilt/manifested from A001, A005, and A007.
- `candidate_source` values map correctly to non-visible source families.
- Visible source behavior is isolated and not used as full-center evidence.
- `gm17_track_id` is the correct track key.
- `sar_frame_num` is the correct frame-order key.
- `target_identity` is the correct row key.
- Candidate `cx`/`cy` may be mapped to Phase4 `center_x`/`center_y`.
- Manual GT path should be `final_gt_working.csv` rather than a dataset-freeze or supplement table.
- Manual GT boxes are OBBs with `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg`.
- Condition labels are evaluation-only and future-branch-only.
- Eval-only columns are isolated by denylist before any scaffold execution.
- B patch, uncertainty, final arbitration, visibility, missing extent, visible/full-center offset, and near-field fields remain inactive.

## 13. Next Recommended Action

Recommended next Codex round:

```text
Create Phase4 data manifest plus inference allowlist and eval-only denylist.
```

That round should:

- write a manifest document or manifest plan only if authorized;
- list accepted input paths and candidate-bank hash;
- define exact field mappings from local column names to Phase4 schema names;
- define inference-safe allowlist columns;
- define eval-only denylist columns;
- keep all old runtime outputs under human-review status until accepted.

Do not run experiments, inference, metrics, training, calibration, candidate-bank changes, code changes, staging, commit, or push in that next round unless explicitly authorized.
