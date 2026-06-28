# GM17 Phase4S Structure-Only Fixed Pilot Run Summary 20260628_221310

## 1. Purpose

This run tests a pre-registered structure-only SAR ranking signal over the full A001 GM_RM017 candidate bank.

## 2. Why This Is Pre-Registered

The active features, rank-percentile scoring, variant definitions, and tie-break were fixed before evaluation. A019/A021 were read only after `pilot_structure_candidates_ranked.csv` and `pilot_structure_selected_rank1_by_variant.csv` existed.

## 3. Candidate Pool

The candidate pool is the full A001 bank, not full-audit `best_proxy` or `best_center` role candidates.

- A001 candidates: 58251
- Target groups: 205

## 4. Active And Diagnostic Features

Active features are `box_to_background_ratio`, `inside_energy_fraction`, and `optional_local_contrast`. `edge_spillover_ratio` is active only in diagnostic S3.

Diagnostic-only fields include `box_mean_intensity`, `local_background_mean`, `structure_feature_status`, `feature_source_image_type`, `box_clip_fraction`, and `local_patch_area_px`.

## 5. Variant Definitions

- S1 `primary_structure_rank3`: three active features, equal rank-percentile mean.
- S2 `conservative_structure_rank2`: `box_to_background_ratio` and `inside_energy_fraction`, equal rank-percentile mean.
- S3 `structure_with_spillover_diagnostic`: S1 features plus lower-is-better `edge_spillover_ratio`; diagnostic only.

Lower score is better. Tie-break is `candidate_id` ascending only.

## 6. Output Directory

`output\gm17_phase4_structure_only_fixed_pilot_20260628_221140`

## 7. Path Resolution And Image Reading

- Image read success rate: 1.0
- Feature valid rate: 1.0
- Feature source risk: diagnostic display/pseudocolor image.

## 8. Core Results

| variant | mean_center_error | median_center_error | mean_axis_aligned_proxy_iou | rank1_is_best_proxy_rate | best_proxy_top5_rate | best_proxy_top20_rate | mean_rank_of_best_proxy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| s1 | 44.8422 | 15.3955 | 0.5394 | 0.1561 | 0.2488 | 0.5415 | 51.7317 |
| s2 | 44.6709 | 15.4849 | 0.5337 | 0.1561 | 0.2439 | 0.5415 | 51.9366 |
| s3 | 39.1083 | 14.9849 | 0.5607 | 0.1415 | 0.2341 | 0.5317 | 52.2585 |

## 9. V1/V2 Comparison

| variant | mean_center_error | mean_axis_aligned_proxy_iou | rank1_is_best_proxy_rate | best_proxy_top5_rate | best_proxy_top20_rate | mean_rank_of_best_proxy |
| --- | --- | --- | --- | --- | --- | --- |
| v1 | 32.5840 | 0.4948 | 0.1122 | 0.1805 | 0.2878 | 67.5756 |
| v2a | 33.3057 | 0.4887 | 0.1073 | 0.1610 | 0.2878 | 72.2732 |
| v2b | 39.2576 | 0.4381 | 0.0098 | 0.0829 | 0.2049 | 87.5415 |
| v2c | 37.4089 | 0.4526 | 0.0244 | 0.1024 | 0.2634 | 76.3707 |
| s1 | 44.8422 | 0.5394 | 0.1561 | 0.2488 | 0.5415 | 51.7317 |
| s2 | 44.6709 | 0.5337 | 0.1561 | 0.2439 | 0.5415 | 51.9366 |
| s3 | 39.1083 | 0.5607 | 0.1415 | 0.2341 | 0.5317 | 52.2585 |

## 10. Rank1 Best-Proxy

S1/S2 rank1 best-proxy rates:

| variant | rank1_is_best_proxy_rate | rank1_is_best_center_rate |
| --- | --- | --- |
| s1 | 0.1561 | 0.1756 |
| s2 | 0.1561 | 0.1707 |

## 11. Best-Proxy Top5/Top20

| variant | best_proxy_top5_rate | best_proxy_top20_rate | mean_rank_of_best_proxy | median_rank_of_best_proxy |
| --- | --- | --- | --- | --- |
| s1 | 0.2488 | 0.5415 | 51.7317 | 18.0000 |
| s2 | 0.2439 | 0.5415 | 51.9366 | 19.0000 |

## 12. Truncated+Occluded Groups

| variant | truncation_degree | occlusion_degree | n_targets | rank1_is_best_proxy_rate | best_proxy_top5_rate | best_proxy_top20_rate | mean_rank_of_best_proxy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| s1 | mild | mild | 14 | 0.0000 | 0.0000 | 0.3571 | 55.4286 |
| s1 | mild | moderate | 1 | 0.0000 | 0.0000 | 0.0000 | 45.0000 |
| s1 | moderate | mild | 1 | 0.0000 | 0.0000 | 1.0000 | 11.0000 |
| s1 | moderate | moderate | 6 | 0.1667 | 0.1667 | 0.3333 | 90.0000 |
| s1 | severe | moderate | 5 | 0.0000 | 0.0000 | 0.0000 | 167.0000 |
| s1 | severe | severe | 5 | 0.0000 | 0.0000 | 0.4000 | 148.0000 |
| s2 | mild | mild | 14 | 0.0000 | 0.0000 | 0.3571 | 55.2857 |
| s2 | mild | moderate | 1 | 0.0000 | 0.0000 | 0.0000 | 45.0000 |
| s2 | moderate | mild | 1 | 0.0000 | 0.0000 | 1.0000 | 11.0000 |
| s2 | moderate | moderate | 6 | 0.1667 | 0.1667 | 0.3333 | 90.0000 |
| s2 | severe | moderate | 5 | 0.0000 | 0.0000 | 0.0000 | 167.0000 |
| s2 | severe | severe | 5 | 0.0000 | 0.0000 | 0.4000 | 147.6000 |
| s3 | mild | mild | 14 | 0.0000 | 0.0000 | 0.3571 | 51.0000 |
| s3 | mild | moderate | 1 | 0.0000 | 0.0000 | 0.0000 | 31.0000 |
| s3 | moderate | mild | 1 | 0.0000 | 1.0000 | 1.0000 | 5.0000 |
| s3 | moderate | moderate | 6 | 0.1667 | 0.1667 | 0.3333 | 85.5000 |
| s3 | severe | moderate | 5 | 0.0000 | 0.0000 | 0.0000 | 160.0000 |
| s3 | severe | severe | 5 | 0.0000 | 0.0000 | 0.4000 | 144.8000 |

## 13. Display/Pseudocolor Risk

This is a diagnostic display-image pilot. It does not prove raw SAR intensity physics. A raw SAR version should be audited before physical claims.

## 14. Support For Combined Structure+Temporal Pilot

Decision: `True`

Reason: S1/S2 improves at least one primary best-proxy promotion metric over v1; combined pilot is justified as a pre-registered next test.

## 15. Failure Or Success Interpretation

Structure-only signal is useful but remains display-image limited; combine only through a pre-registered next spec.

## 16. Next Step

- If S1/S2 is useful, write a combined factor pilot pre-registered spec.
- If structure-only is weak but specific groups improve, run condition/failure diagnostics.
- If globally weak, move toward raw SAR or independent candidate proposal.
- Do not return to table-level v3 tuning.

## 17. Explicit Non-Actions

- No v3 ranking was generated.
- No threshold was tuned.
- No training was performed.
- No calibration was performed.
- A021 was not fed into inference.
- GT was not used to tune rules.
- Source/provenance was not used for sorting.

## Figures

- `output\gm17_phase4_structure_only_fixed_pilot_20260628_221140\figures\structure_vs_v1_v2_proxy_iou_recall_bar.png`
- `output\gm17_phase4_structure_only_fixed_pilot_20260628_221140\figures\structure_vs_v1_v2_center_error_bar.png`
- `output\gm17_phase4_structure_only_fixed_pilot_20260628_221140\figures\structure_rank1_best_proxy_rate_bar.png`
- `output\gm17_phase4_structure_only_fixed_pilot_20260628_221140\figures\structure_best_proxy_topk_bar.png`
- `output\gm17_phase4_structure_only_fixed_pilot_20260628_221140\figures\structure_condition_group_failure_bar.png`
- `output\gm17_phase4_structure_only_fixed_pilot_20260628_221140\figures\structure_feature_distribution_by_selected_variant.png`

## Panels

- Panel queue rows: 57
- Panels generated: 57

## Creative Next Ideas Appendix

These are future ideas only; none entered this ranking:

- Raw SAR intensity version of the same fixed features.
- Rotated OBB patch features instead of axis-aligned crops.
- Ridge or axis support descriptors.
- Local peak-cluster support instead of single-pixel peak evidence.
- Structure+temporal gating with pre-registered ownership boundaries.
- Independent SAR candidate proposal for cases where A001 lacks the right structure-support candidate.
- Learned model route after raw-SAR and leakage controls are settled.

## Repair Notes

- No repair was needed.
