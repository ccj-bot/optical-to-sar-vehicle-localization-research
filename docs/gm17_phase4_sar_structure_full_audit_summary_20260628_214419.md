# GM17 Phase4S SAR Structure Full Audit Summary 20260628_214419

## 1. Purpose

This run grounds `sar_structure_factor` with full GM_RM017 evidence. It extracts SAR structure features over all targets and audits whether the feature directions separate existing candidate roles.

## 2. Why Phase4S Instead Of V3 Table Tuning

The v1/v2 results show enough A001 candidate coverage but unstable table-level geometry/temporal promotion of the best candidate. The next useful evidence is SAR patch structure, not another A001/A005 field-rule search.

## 3. Inputs And Outputs

- V1 pilot: `output/gm17_phase4_minimal_factor_pilot_20260628_110447`
- V1 diagnostics: `output/gm17_phase4_minimal_factor_pilot_v1_diagnostics_20260628_113224`
- V2 pilot: `output/gm17_phase4_minimal_factor_pilot_v2_20260628_171204`
- Scout reference: `output/gm17_phase4_sar_structure_evidence_scout_20260628_183122`
- A019 path/evaluation context: `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv`
- A021 post-inference grouping context: `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv`
- Output directory: `output\gm17_phase4_sar_structure_full_audit_20260628_214419`
- Log: `logs\gm17_phase4_sar_structure_full_audit_20260628_214419.log`
- Summary JSON: `output\gm17_phase4_sar_structure_full_audit_20260628_214419\full_structure_audit_summary.json`

## 4. SAR Path Resolution

- Targets: 205
- SAR image read success: 205
- SAR image read success rate: 1.0000
- Needs SAR path/patch manifest first: `False`

Path details are in `output\gm17_phase4_sar_structure_full_audit_20260628_214419\full_path_resolution_report.csv`.

## 5. Full 205 Target Coverage

- Target rows: 205
- Unique target-candidate feature rows: 4356
- Candidate roles include `rank1_v1`, `best_proxy`, `best_center`, `v2a/v2b/v2c_rank1`, `v1_top1_to_top5`, and `v1_top6_to_top20`.

## 6. Feature Valid Rate

- Structure feature valid rate: 1.0000
- Feature source image type: diagnostic display/pseudocolor image when `sar_pseudocolor_path` is used.

## 7. Rank1 Vs Best-Proxy Full Feature Differences

| feature | n_pairs | median_best_proxy_minus_rank1 | mean_best_proxy_minus_rank1 | directional_consistency | effect_size_robust | condition_stability | recommended_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| peak_to_background_ratio | 205 | 0.0089 | 0.0577 | 0.5463 | 0.0092 | 0.5556 | display-risk |
| box_max_intensity | 205 | 0.0000 | 0.0103 | 0.2049 | 0.0000 | 0.1111 | display-risk |
| box_to_background_ratio | 205 | 0.0101 | 0.0356 | 0.6537 | 0.0755 | 0.6667 | promising |
| inside_energy_fraction | 205 | 0.0018 | 0.0066 | 0.6537 | 0.0749 | 0.6667 | promising |
| optional_local_contrast | 205 | 0.0021 | 0.0097 | 0.6488 | 0.0678 | 0.6667 | promising |
| center_to_peak_distance | 205 | -0.4753 | -11.1420 | 0.5122 | 0.0056 | 0.5556 | unstable |
| box_top5_mean_intensity | 205 | 0.0001 | 0.0273 | 0.5122 | 0.0004 | 0.3333 | unstable |
| simple_long_axis_support | 205 | 0.0000 | -0.0301 | 0.4976 | 0.0000 | 0.4444 | unstable |
| box_sum_intensity | 205 | 0.0000 | 35.7798 | 0.4878 | 0.0000 | 0.5556 | unstable |
| optional_peak_inside_box_flag | 205 | 0.0000 | 0.1610 | 0.2244 | 0.0000 | 0.3333 | unstable |
| edge_spillover_ratio | 205 | -0.0052 | -0.0193 | 0.5756 | 0.0674 | 0.7778 | weak |
| local_background_mean | 205 | -0.0008 | -0.0014 | 0.5659 | 0.0102 | 0.6667 | weak |
| simple_short_axis_support | 205 | 0.0124 | 0.0308 | 0.5610 | 0.0814 | 0.5556 | weak |
| box_mean_intensity | 205 | 0.0006 | 0.0083 | 0.5512 | 0.0077 | 0.4444 | weak |

## 8. Consistency With 40-Case Scout

- Scout promising features: ['edge_spillover_ratio', 'inside_energy_fraction', 'box_to_background_ratio']
- Full-audit promising features: ['box_to_background_ratio', 'inside_energy_fraction', 'optional_local_contrast']
- Directionally consistent promising overlap: ['inside_energy_fraction', 'box_to_background_ratio']

## 9. Promising Features

| feature | n_pairs | directional_consistency | effect_size_robust | condition_stability | recommended_status |
| --- | --- | --- | --- | --- | --- |
| box_to_background_ratio | 205 | 0.6537 | 0.0755 | 0.6667 | promising |
| inside_energy_fraction | 205 | 0.6537 | 0.0749 | 0.6667 | promising |
| optional_local_contrast | 205 | 0.6488 | 0.0678 | 0.6667 | promising |

## 10. Weak Or Unstable Features

| feature | n_pairs | directional_consistency | effect_size_robust | condition_stability | recommended_status |
| --- | --- | --- | --- | --- | --- |
| peak_to_background_ratio | 205 | 0.5463 | 0.0092 | 0.5556 | display-risk |
| box_max_intensity | 205 | 0.2049 | 0.0000 | 0.1111 | display-risk |
| center_to_peak_distance | 205 | 0.5122 | 0.0056 | 0.5556 | unstable |
| box_top5_mean_intensity | 205 | 0.5122 | 0.0004 | 0.3333 | unstable |
| simple_long_axis_support | 205 | 0.4976 | 0.0000 | 0.4444 | unstable |
| box_sum_intensity | 205 | 0.4878 | 0.0000 | 0.5556 | unstable |
| optional_peak_inside_box_flag | 205 | 0.2244 | 0.0000 | 0.3333 | unstable |

Reliability details are in `output\gm17_phase4_sar_structure_full_audit_20260628_214419\full_feature_reliability_report.csv`.

## 11. Condition-Wise Stability

| condition_type | truncation_degree | occlusion_degree | n_targets | mean_rank1_proxy_iou | mean_best_proxy_iou | median_best_proxy_rank | edge_spillover_ratio_n_pairs | edge_spillover_ratio_median_diff | edge_spillover_ratio_directional_consistency | inside_energy_fraction_n_pairs | inside_energy_fraction_median_diff | inside_energy_fraction_directional_consistency | box_to_background_ratio_n_pairs | box_to_background_ratio_median_diff | box_to_background_ratio_directional_consistency | center_to_peak_distance_n_pairs | center_to_peak_distance_median_diff | center_to_peak_distance_directional_consistency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| none | none | none | 117 | 0.5472 | 0.7838 | 34.0000 | 117 | -0.0068 | 0.5641 | 117 | 0.0027 | 0.6581 | 117 | 0.0154 | 0.6581 | 117 | 0.0000 | 0.4786 |
| occluded | none | mild | 28 | 0.4532 | 0.7735 | 28.0000 | 28 | 0.0000 | 0.4643 | 28 | 0.0029 | 0.6786 | 28 | 0.0158 | 0.6786 | 28 | -51.3308 | 0.6429 |
| truncated | mild | none | 8 | 0.5660 | 0.8618 | 68.0000 | 8 | -0.0155 | 0.7500 | 8 | 0.0037 | 0.7500 | 8 | 0.0207 | 0.7500 | 8 | -4.3012 | 0.6250 |
| truncated | moderate | none | 3 | 0.8748 | 0.9001 | 16.0000 | 3 | 0.0000 | 0.3333 | 3 | 0.0000 | 0.3333 | 3 | 0.0000 | 0.3333 | 3 | 10.2955 | 0.0000 |
| truncated | severe | none | 17 | 0.6490 | 0.8087 | 52.0000 | 17 | -0.0052 | 0.5882 | 17 | 0.0007 | 0.7059 | 17 | 0.0040 | 0.7059 | 17 | 4.8891 | 0.3529 |
| truncated+occluded | mild | mild | 14 | 0.1744 | 0.7390 | 70.0000 | 14 | -0.0084 | 0.6429 | 14 | 0.0021 | 0.7143 | 14 | 0.0120 | 0.7143 | 14 | 5.0373 | 0.4286 |
| truncated+occluded | mild | moderate | 1 | 0.0138 | 0.8268 | 274.0000 | 1 | -0.0134 | 1.0000 | 1 | 0.0049 | 1.0000 | 1 | 0.0263 | 1.0000 | 1 | -100.9075 | 1.0000 |
| truncated+occluded | moderate | mild | 1 | 0.2446 | 0.6898 | 56.0000 | 1 | -0.0061 | 1.0000 | 1 | 0.0038 | 1.0000 | 1 | 0.0211 | 1.0000 | 1 | 19.0589 | 0.0000 |
| truncated+occluded | moderate | moderate | 6 | 0.2185 | 0.6948 | 167.0000 | 6 | -0.0080 | 0.6667 | 6 | 0.0026 | 0.6667 | 6 | 0.0143 | 0.6667 | 6 | -104.6860 | 0.8333 |
| truncated+occluded | severe | moderate | 5 | 0.1548 | 0.8437 | 218.0000 | 5 | -0.0102 | 0.8000 | 5 | -0.0010 | 0.2000 | 5 | -0.0052 | 0.2000 | 5 | -80.8179 | 0.8000 |
| truncated+occluded | severe | severe | 5 | 0.3484 | 0.7759 | 36.0000 | 5 | -0.0017 | 0.6000 | 5 | -0.0013 | 0.4000 | 5 | -0.0070 | 0.4000 | 5 | -4.4481 | 0.8000 |

## 12. Truncated+Occluded Observations

Truncated and occluded cases remain a risk group. This audit uses A021/v1 condition labels only after inference outputs exist, for grouping and panel review prioritization. They are not used as structure-factor inputs.

## 13. Panel Review Queue

- Panel review queue rows: 45
- Panels generated: 45
- Queue file: `output\gm17_phase4_sar_structure_full_audit_20260628_214419\full_panel_review_queue.csv`
- Panel directory: `output\gm17_phase4_sar_structure_full_audit_20260628_214419\panels`

## 14. Support For Structure-Only Fixed Pilot

Support decision: `True`

Reason: Full audit supports writing a pre-registered structure-only fixed pilot spec, with display-image risk noted.

## 15. Pilot Preconditions If Supported

- Write the structure-only fixed pilot rule before execution.
- Keep all thresholds fixed before seeing pilot results.
- Keep A019/A021 out of inference.
- Review representative panels, especially disagreement and truncated+occluded cases.
- Explicitly mark pseudocolor/display-image risk if raw SAR is unavailable.

## 16. If Not Supported

If the decision is not supported, the next step is either SAR path/patch manifest repair or independent candidate proposal research. Do not return to table-only v3 rule search.

## 17. Explicit Non-Actions

- No v3 ranking was generated.
- No structure-only selected output was generated.
- No threshold was tuned.
- No training was performed.
- No calibration was performed.
- A021 was not fed into inference.
- GT was not used to tune rules.
- Source/provenance was not used for sorting.
- A001/A005/A019/A021 originals were not modified.

## Output Figures

- `output\gm17_phase4_sar_structure_full_audit_20260628_214419\figures\full_feature_signal_bar.png`
- `output\gm17_phase4_sar_structure_full_audit_20260628_214419\figures\full_role_box_to_background_ratio_boxplot.png`
- `output\gm17_phase4_sar_structure_full_audit_20260628_214419\figures\full_role_inside_energy_fraction_boxplot.png`
- `output\gm17_phase4_sar_structure_full_audit_20260628_214419\figures\full_role_edge_spillover_ratio_boxplot.png`
- `output\gm17_phase4_sar_structure_full_audit_20260628_214419\figures\full_center_to_peak_distance_boxplot.png`
- `output\gm17_phase4_sar_structure_full_audit_20260628_214419\figures\full_condition_feature_stability_heatmap.png`
- `output\gm17_phase4_sar_structure_full_audit_20260628_214419\figures\full_feature_missing_rate_bar.png`
- `output\gm17_phase4_sar_structure_full_audit_20260628_214419\figures\full_panel_queue_case_type_bar.png`

## Repair Notes

- Repair 1: fixed panel queue status-column merge so an existing target-level image_read_status/path_status is preserved without pandas suffixing. This did not change inputs, feature definitions, thresholds, ranking, or audit logic.
