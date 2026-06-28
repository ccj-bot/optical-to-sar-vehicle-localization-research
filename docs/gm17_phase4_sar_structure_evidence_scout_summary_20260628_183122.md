# GM17 Phase4 SAR Structure Evidence Scout Summary 20260628_183122

## 1. Purpose

This run is a diagnostic SAR image structure evidence scout over v1/v2 failure and control cases. It compares existing candidate roles (`rank1_v1`, `best_proxy`, `best_center`, `v2a_rank1`, `v2b_rank1`, `v2c_rank1`) in the SAR image patch to identify future `sar_structure_factor` evidence candidates.

It is not v3 ranking, not a tuned selector, not a final model, and not an execution configuration.

## 2. Why Not Continue V3 Table Tuning

The v1/v2 pilots already indicate that the A001 candidate bank has coverage, while table-level geometry/temporal sorting does not reliably promote the best candidate to rank1. V2 reduced the temporal-zero artifact only with tradeoffs that degraded rank1-best-proxy and best-proxy top-k behavior. Continuing table-field rule search risks overfitting diagnostic/evaluation artifacts instead of adding SAR-side structure evidence.

## 3. Inputs And Outputs

- V1 pilot: `output/gm17_phase4_minimal_factor_pilot_20260628_110447`
- V1 diagnostics: `output/gm17_phase4_minimal_factor_pilot_v1_diagnostics_20260628_113224`
- V2 pilot: `output/gm17_phase4_minimal_factor_pilot_v2_20260628_171204`
- A019 path table used only for SAR image path resolution: `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv`
- Output directory: `output\gm17_phase4_sar_structure_evidence_scout_20260628_183122`
- Log: `logs\gm17_phase4_sar_structure_evidence_scout_20260628_183122.log`
- Summary JSON: `output\gm17_phase4_sar_structure_evidence_scout_20260628_183122\scout_summary.json`
- This Markdown summary: `docs\gm17_phase4_sar_structure_evidence_scout_summary_20260628_183122.md`

## 4. Case Selection Strategy

Cases were selected from post-inference v1/v2 outputs for diagnostic inspection only. The selection categories were temporal-zero bad cases, deep best-proxy rank cases, truncated+occluded moderate/severe cases, low-rank1/high-best-proxy IoU cases, v2b/v2c no-improvement cases, and success controls.

| case_type | n |
| --- | --- |
| temporal_zero_bad | 6 |
| best_proxy_rank_gt_50 | 6 |
| truncated_occluded_moderate_severe | 6 |
| rank1_low_iou_best_proxy_high_iou | 6 |
| v2b_v2c_no_improve | 6 |
| success_control | 6 |
| failure_fill | 4 |

## 5. SAR Image Path Resolution

- Selected cases: 40
- A019/SAR path exists: 40
- SAR image read success: 40
- Missing or unreadable images: 0

The path report is written to `output\gm17_phase4_sar_structure_evidence_scout_20260628_183122\scout_path_resolution_report.csv`.

## 6. Panel Generation

- Panels generated: 40
- Panel directory: `output\gm17_phase4_sar_structure_evidence_scout_20260628_183122\panels`

Panels show candidate roles on the SAR image and local patches. Rectangles are axis-aligned diagnostic boxes derived from candidate geometry, not final predictions.

## 7. Rank1 Vs Best-Proxy Visual Difference

The paired feature comparison is diagnostic: it asks whether `best_proxy` candidates tend to show stronger SAR local structure than `rank1_v1` among selected cases. These values are not thresholds and are not active scoring rules.

| feature | n | mean_diff | median_diff | directional_consistency | diagnostic_signal_strength | interpretation_hint |
| --- | --- | --- | --- | --- | --- | --- |
| edge_spillover_ratio | 40 | -0.0355 | -0.0208 | 0.7750 | 0.3353 | best_proxy lower is favorable |
| inside_energy_fraction | 40 | 0.0108 | 0.0045 | 0.7500 | 0.2540 | best_proxy higher is favorable |
| box_to_background_ratio | 40 | 0.0575 | 0.0239 | 0.7500 | 0.2511 | best_proxy higher is favorable |
| center_to_peak_distance | 40 | -33.1039 | -30.7616 | 0.6000 | 0.2358 | best_proxy lower is favorable |
| simple_long_axis_support | 40 | 0.0224 | 0.0219 | 0.7250 | 0.2164 | best_proxy higher is favorable |
| simple_short_axis_support | 40 | 0.0533 | 0.0243 | 0.6750 | 0.1654 | best_proxy higher is favorable |
| local_background_mean | 40 | -0.0009 | -0.0027 | 0.5750 | 0.0216 | best_proxy lower is favorable |
| box_top5_mean_intensity | 40 | 0.0458 | 0.0047 | 0.5250 | 0.0178 | best_proxy higher is favorable |
| peak_to_background_ratio | 40 | 0.0510 | 0.0189 | 0.5250 | 0.0139 | best_proxy higher is favorable |
| box_mean_intensity | 40 | 0.0146 | 0.0011 | 0.5750 | 0.0084 | best_proxy higher is favorable |
| box_max_intensity | 40 | 0.0148 | 0.0010 | 0.5000 | 0.0051 | best_proxy higher is favorable |
| box_sum_intensity | 40 | 25.3778 | -0.5739 | 0.4500 | 0.0003 | best_proxy higher is favorable |

## 8. SAR Structure Candidate Feature Statistics

All computed structure values are labeled diagnostic candidate features. The feature table is written to `output\gm17_phase4_sar_structure_evidence_scout_20260628_183122\scout_structure_features.csv` and role-level summaries are written to `output\gm17_phase4_sar_structure_evidence_scout_20260628_183122\scout_role_comparison_summary.csv`.

## 9. Truncated+Occluded Failure Observations

Selected truncated/occluded cases remain a high-risk diagnostic group. The scout compares whether best-proxy candidates have clearer local energy concentration or axis support than temporal-first rank1 candidates, but this run does not convert those observations into a rule.

| primary_case_type | condition_type | truncation_degree | occlusion_degree | n_cases | image_read_ok | panels_generated | mean_rank1_proxy_iou | mean_best_proxy_iou | median_best_proxy_rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| best_proxy_rank_gt_50 | truncated+occluded | mild | mild | 3 | 3 | 3 | 0.0185 | 0.8235 | 254.0000 |
| best_proxy_rank_gt_50 | truncated+occluded | moderate | moderate | 1 | 1 | 1 | 0.0056 | 0.7723 | 268.0000 |
| best_proxy_rank_gt_50 | truncated+occluded | severe | moderate | 1 | 1 | 1 | 0.0161 | 0.8806 | 218.0000 |
| best_proxy_rank_gt_50 | truncated+occluded | severe | severe | 1 | 1 | 1 | 0.0290 | 0.7996 | 274.0000 |
| failure_fill | none | none | none | 2 | 2 | 2 | 0.1512 | 0.7445 | 96.0000 |
| failure_fill | occluded | none | mild | 2 | 2 | 2 | 0.1762 | 0.8355 | 82.0000 |
| rank1_low_iou_best_proxy_high_iou | none | none | none | 4 | 4 | 4 | 0.1260 | 0.7208 | 206.0000 |
| rank1_low_iou_best_proxy_high_iou | truncated | mild | none | 1 | 1 | 1 | 0.2026 | 0.9074 | 272.0000 |
| rank1_low_iou_best_proxy_high_iou | truncated+occluded | mild | mild | 1 | 1 | 1 | 0.0223 | 0.7555 | 208.0000 |
| success_control | none | none | none | 2 | 2 | 2 | 0.8781 | 0.8859 | 28.5000 |
| success_control | truncated | moderate | none | 3 | 3 | 3 | 0.8748 | 0.9001 | 16.0000 |
| success_control | truncated | severe | none | 1 | 1 | 1 | 0.9186 | 0.9694 | 2.0000 |
| temporal_zero_bad | none | none | none | 2 | 2 | 2 | 0.0000 | 0.7968 | 386.0000 |
| temporal_zero_bad | truncated | mild | none | 1 | 1 | 1 | 0.2474 | 0.8678 | 436.0000 |
| temporal_zero_bad | truncated+occluded | mild | mild | 1 | 1 | 1 | 0.0274 | 0.8754 | 266.0000 |
| temporal_zero_bad | truncated+occluded | mild | moderate | 1 | 1 | 1 | 0.0138 | 0.8268 | 274.0000 |
| temporal_zero_bad | truncated+occluded | severe | moderate | 1 | 1 | 1 | 0.0094 | 0.9432 | 268.0000 |
| truncated_occluded_moderate_severe | truncated+occluded | moderate | moderate | 3 | 3 | 3 | 0.2140 | 0.7940 | 224.0000 |
| truncated_occluded_moderate_severe | truncated+occluded | severe | moderate | 2 | 2 | 2 | 0.1024 | 0.8505 | 143.0000 |
| truncated_occluded_moderate_severe | truncated+occluded | severe | severe | 1 | 1 | 1 | 0.1147 | 0.8953 | 194.0000 |

_Showing 20 of 21 rows._

## 10. Success Control Observations

Success controls are included only as a visual/feature sanity check. They help distinguish features that are broadly stable across correct-looking candidates from features that only appear in failure cases.

## 11. Potential Future `sar_structure_factor` Features

Most promising diagnostic candidates in this run:

- `edge_spillover_ratio`: n=40, median best_proxy-rank1 diff=-0.0208, directional consistency=0.78; best_proxy lower is favorable.
- `inside_energy_fraction`: n=40, median best_proxy-rank1 diff=0.0045, directional consistency=0.75; best_proxy higher is favorable.
- `box_to_background_ratio`: n=40, median best_proxy-rank1 diff=0.0239, directional consistency=0.75; best_proxy higher is favorable.

These can support a future diagnostic design spec only after human review of panels and feature caveats.

## 12. Unstable Or Not Recommended Features

Least stable diagnostic candidates in this run:

- `box_sum_intensity`: n=40, median best_proxy-rank1 diff=-0.5739, directional consistency=0.45; best_proxy higher is favorable.
- `box_max_intensity`: n=40, median best_proxy-rank1 diff=0.0010, directional consistency=0.50; best_proxy higher is favorable.
- `peak_to_background_ratio`: n=40, median best_proxy-rank1 diff=0.0189, directional consistency=0.53; best_proxy higher is favorable.

Features with weak directional consistency, small paired sample count, or strong dependence on pseudocolor rendering should remain diagnostic-only.

## 13. Relationship To Geometry And Optical Temporal Factors

`geometry_factor` still owns candidate-table geometry plausibility, and `optical_temporal_factor` remains a soft optical-to-SAR temporal suggestion. The potential `sar_structure_factor` would be SAR-image evidence inside existing A001 candidate boxes. It should not generate new candidates, move boxes, or use GT/evaluation fields during inference.

## 14. Explicit Non-Actions

- No v3 ranking was generated.
- No thresholds were tuned.
- No weights were trained.
- No calibration was performed.
- A021/condition labels were not fed into inference.
- `candidate_source`, `temporal_factor_score`, `delta_*_from_pred`, `score/lr_score/sar_factor_score`, selected outputs, B patches, and oracle-style inputs were not used for sorting.
- A001/A005/A019/A021 originals were not modified.

## 15. Next-Step Recommendation

- If the panel review confirms clear SAR-structure differences, write `sar_structure_factor diagnostic design spec`.
- If path or patch alignment issues are found, first create a SAR path/patch manifest review.
- If SAR structure still cannot distinguish roles, shift attention to independent candidate proposal rather than more table-level v3 rule search.
- Do not continue table-only v3 rule search from this output.

Current support for the next diagnostic design spec: `True`.

## 16. Output Figures

- `output\gm17_phase4_sar_structure_evidence_scout_20260628_183122\figures\role_box_to_background_ratio_boxplot.png`
- `output\gm17_phase4_sar_structure_evidence_scout_20260628_183122\figures\role_center_to_peak_distance_boxplot.png`
- `output\gm17_phase4_sar_structure_evidence_scout_20260628_183122\figures\role_inside_energy_fraction_boxplot.png`
- `output\gm17_phase4_sar_structure_evidence_scout_20260628_183122\figures\case_type_panel_success_bar.png`
- `output\gm17_phase4_sar_structure_evidence_scout_20260628_183122\figures\feature_signal_candidate_bar.png`

## Repair Note

One small script repair was made before the final recorded run: panel labels used escaped newline text, which made patch titles crowded. The repair changed only visual label line breaks and the recorded repair note; it did not change inputs, case selection, feature logic, ranking, thresholds, or metrics.
