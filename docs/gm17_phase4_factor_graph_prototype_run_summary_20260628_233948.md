# GM17 Phase4 Factor Graph Prototype Run Summary 20260628_233948

## 1. Purpose

This run restructures the already validated Phase4C C3 temporal-guarded structure rule into explicit factor graph prototype outputs.

## 2. Why This Is A Factor Graph Prototype

The prototype separates candidate nodes, temporal factor values, SAR structure factor values, messages, and combined energy tables. It does not tune a new weight, search C6/C7, search v3 table rules, train, or calibrate.

## 3. Candidate Node Definition

Candidate nodes are the full A001 GM_RM017 candidate bank with `candidate_id`, group keys, `cx/cy/w/h/heading/r/az/cross`, and `node_status`.

- candidate nodes: 58251
- target groups: 205

## 4. Temporal Factor Definition

The temporal factor is the Phase4C recomputed optical temporal compatibility from A001 `r/cross/az` and A005 `pred_r/pred_cross/pred_az`, represented as `temporal_distance_raw` and `temporal_rank_percentile`.

## 5. SAR Structure Factor Definition

The SAR structure factor reuses structure-only S1/S2 display-image features over full A001. This remains display/pseudocolor evidence, not raw SAR physics.

## 6. C3 Combined Energy Definition

`c3_energy = 0.67 * temporal_rank_percentile + 0.33 * s1_rank_percentile`.

Lower energy is better. Tie-break is `candidate_id` ascending only.

## 7. C4 Diagnostic Branch Definition

`c4_diagnostic_energy = 0.33 * temporal_rank_percentile + 0.67 * s1_rank_percentile`.

C4 is diagnostic only and is not the main prototype conclusion.

## 8. Alignment With Phase4C

| branch | branch_name | row_count | matched_rows | missing_in_prototype | missing_in_phase4c | score_all_equal | rank_all_equal | max_score_abs_diff | rank_mismatch_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c3 | prototype_c3_temporal_guard_structure_promote | 58251 | 58251 | 0 | 0 | True | True | 0.0000 | 0 |
| c4_diagnostic | prototype_c4_structure_guard_temporal_soft_diagnostic | 58251 | 58251 | 0 | 0 | True | True | 0.0000 | 0 |
| c3_rank1 | prototype_c3_vs_phase4c_c3_rank1 | 205 | 205 | 0 | 0 | True | True | 0.0000 | 0 |

## 9. Core Evaluation Results

| branch | branch_name | branch_role | mean_center_error | median_center_error | mean_axis_aligned_proxy_iou | median_axis_aligned_proxy_iou | proxy_iou_recall_at_1_threshold_0_25 | proxy_iou_recall_at_3_threshold_0_25 | proxy_iou_recall_at_5_threshold_0_25 | center_recall_at_1_threshold_50px | center_recall_at_3_threshold_50px | center_recall_at_5_threshold_50px | rank1_is_best_proxy_rate | rank1_is_best_center_rate | best_proxy_top5_rate | best_proxy_top20_rate | mean_rank_of_best_proxy | median_rank_of_best_proxy | rank1_temporal_zero_rate | n_targets |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c3 | prototype_c3_temporal_guard_structure_promote | primary | 25.9912 | 15.2038 | 0.6053 | 0.6613 | 0.8927 | 0.9171 | 0.9171 | 0.8976 | 0.9171 | 0.9171 | 0.1512 | 0.1171 | 0.2244 | 0.3854 | 71.4293 | 32.0000 | 0.2829 | 205 |
| c4_diagnostic | prototype_c4_structure_guard_temporal_soft_diagnostic | diagnostic | 29.5407 | 14.0380 | 0.5958 | 0.6746 | 0.8878 | 0.8927 | 0.9024 | 0.8927 | 0.8927 | 0.9024 | 0.1268 | 0.1268 | 0.2732 | 0.5122 | 52.3756 | 19.0000 | 0.1707 | 205 |

## 10. Condition Failure Results

| branch | condition_type | truncation_degree | occlusion_degree | n_targets | rank1_is_best_proxy_rate | best_proxy_top20_rate | mean_center_error | mean_rank_of_best_proxy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c3 | none | none | none | 117 | 0.2137 | 0.4274 | 19.8606 | 66.7778 |
| c3 | occluded | none | mild | 28 | 0.1429 | 0.4643 | 19.0993 | 29.7500 |
| c3 | truncated | mild | none | 8 | 0.1250 | 0.3750 | 14.3393 | 68.1250 |
| c3 | truncated | moderate | none | 3 | 0.3333 | 1.0000 | 3.4242 | 8.3333 |
| c3 | truncated | severe | none | 17 | 0.0000 | 0.2941 | 21.6636 | 56.1765 |
| c3 | truncated+occluded | mild | mild | 14 | 0.0000 | 0.0714 | 47.9007 | 106.2143 |
| c3 | truncated+occluded | mild | moderate | 1 | 0.0000 | 0.0000 | 160.7874 | 228.0000 |
| c3 | truncated+occluded | moderate | mild | 1 | 0.0000 | 0.0000 | 31.2519 | 52.0000 |
| c3 | truncated+occluded | moderate | moderate | 6 | 0.0000 | 0.3333 | 85.6518 | 119.6667 |
| c3 | truncated+occluded | severe | moderate | 5 | 0.0000 | 0.0000 | 74.9774 | 200.8000 |
| c3 | truncated+occluded | severe | severe | 5 | 0.0000 | 0.4000 | 45.0025 | 196.6000 |

## 11. Display/Pseudocolor Risk

The SAR structure factor still comes from display/pseudocolor image features. It should not be described as raw SAR physics.

## 12. A005 Legacy Soft-Prior Risk

The temporal factor still depends on the legacy A005 soft prior, although legacy A005 score and delta fields are not used.

## 13. Severe Truncated+Occluded Status

Severe truncation/occlusion remains unresolved. The relevant C3 severe condition rows are:

| branch | condition_type | truncation_degree | occlusion_degree | n_targets | rank1_is_best_proxy_rate | best_proxy_top20_rate | mean_center_error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| c3 | truncated | severe | none | 17 | 0.0000 | 0.2941 | 21.6636 |
| c3 | truncated+occluded | severe | moderate | 5 | 0.0000 | 0.0000 | 74.9774 |
| c3 | truncated+occluded | severe | severe | 5 | 0.0000 | 0.4000 | 45.0025 |

## 14. Support For Method Chapter / System Flow Figure

Decision: `True`

Reason: C3 reproduces Phase4C alignment=True; mean_center_error=25.9912; rank1_best_proxy=0.1512; best_proxy_top20=0.3854. C4 diagnostic top20=0.5122 remains diagnostic.

## 15. Next Step

- If C3 fully reproduces Phase4C, move to method chapter text and prototype interface diagram.
- If alignment fails, fix alignment before making claims.
- Future-only routes remain raw SAR, rotated OBB, visibility/missing route, and independent proposal.
- Do not return to C6/C7 or v3 table tuning.

## Boundary Statement

- A019/A021 were read only after prototype output existed.
- No A019 `final_*` entered inference.
- No A021 condition/truncation/occlusion entered inference.
- No source, legacy delta, legacy score, selected output, B patch, or oracle entered inference.
- No threshold tuning, training, calibration, stage, commit, or push.
