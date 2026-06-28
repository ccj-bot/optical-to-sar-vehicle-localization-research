# GM17 Phase4C Combined Structure+Temporal Fixed Pilot Run Summary 20260628_224459

## 1. Purpose

This run tests whether a pre-registered combination of recomputed temporal consistency and SAR structure can keep temporal center stability while improving best-proxy promotion.

## 2. Why Combined Instead Of V3

V1 has useful temporal center behavior but a temporal-zero artifact. Structure-only improves best-proxy promotion but worsens mean center error. Combined tests complementary fixed signals instead of searching A001/A005 table rules.

## 3. Candidate Pool

The candidate pool is the full A001 bank.

- Ranked candidates: 58251
- Target groups: 205
- No structure-selected, best-proxy, or best-center filtering was used.

## 4. Temporal Component

Temporal is recomputed from A001 `r/cross/az` and A005 `pred_r/pred_cross/pred_az`. Legacy `delta_*`, `temporal_factor_score`, and score fields are not used.

## 5. Structure Component

Structure is reused from the structure-only full A001 output. S1/S2 are active; S3 remains diagnostic.

## 6. Variant Definitions

- C1 `equal_temporal_s1`: 0.50 temporal + 0.50 S1.
- C2 `equal_temporal_s2`: 0.50 temporal + 0.50 S2.
- C3 `temporal_guard_structure_promote`: 0.67 temporal + 0.33 S1.
- C4 `structure_guard_temporal_soft_diagnostic`: 0.33 temporal + 0.67 S1, diagnostic.
- C5 `temporal_only_recomputed_baseline`: temporal only, internal baseline.

## 7. Output Directory

`output\gm17_phase4_combined_structure_temporal_fixed_pilot_20260628_224407`

## 8. Join Situation

Temporal join summary: `{'a005_rows': 205, 'a005_unique_key_rows': 205, 'a005_ambiguous_keys': 0, 'candidate_rows_matched': 58251, 'candidate_rows_missing': 0, 'candidate_rows_ambiguous': 0}`

Structure join summary: `{'structure_rows': 58251, 'a001_rows': 58251, 'matched_rows': 58251, 'missing_rows': 0}`

## 9. Core Results

| variant | mean_center_error | median_center_error | mean_axis_aligned_proxy_iou | rank1_is_best_proxy_rate | best_proxy_top5_rate | best_proxy_top20_rate | mean_rank_of_best_proxy | rank1_temporal_zero_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c1 | 27.7065 | 14.0380 | 0.6058 | 0.1317 | 0.2537 | 0.4634 | 59.3366 | 0.2488 |
| c2 | 27.7914 | 14.0380 | 0.6040 | 0.1317 | 0.2537 | 0.4683 | 59.4829 | 0.2488 |
| c3 | 25.9912 | 15.2038 | 0.6053 | 0.1512 | 0.2244 | 0.3854 | 71.4293 | 0.2829 |
| c4 | 29.5407 | 14.0380 | 0.5958 | 0.1268 | 0.2732 | 0.5122 | 52.3756 | 0.1707 |
| c5 | 32.5840 | 26.6502 | 0.4948 | 0.1463 | 0.2049 | 0.3122 | 95.6488 | 1.0000 |

## 10. Comparison With V1/V2/Structure-Only

| variant | mean_center_error | mean_axis_aligned_proxy_iou | rank1_is_best_proxy_rate | best_proxy_top5_rate | best_proxy_top20_rate | mean_rank_of_best_proxy |
| --- | --- | --- | --- | --- | --- | --- |
| v1 | 32.5840 | 0.4948 | 0.1122 | 0.1805 | 0.2878 | 67.5756 |
| v2a | 33.3057 | 0.4887 | 0.1073 | 0.1610 | 0.2878 | 72.2732 |
| v2b | 39.2576 | 0.4381 | 0.0098 | 0.0829 | 0.2049 | 87.5415 |
| v2c | 37.4089 | 0.4526 | 0.0244 | 0.1024 | 0.2634 | 76.3707 |
| s1 | 44.8422 | 0.5394 | 0.1561 | 0.2488 | 0.5415 | 51.7317 |
| s2 | 44.6709 | 0.5337 | 0.1561 | 0.2439 | 0.5415 | 51.9366 |
| s3 | 39.1083 | 0.5607 | 0.1415 | 0.2341 | 0.5317 | 52.2585 |
| c1 | 27.7065 | 0.6058 | 0.1317 | 0.2537 | 0.4634 | 59.3366 |
| c2 | 27.7914 | 0.6040 | 0.1317 | 0.2537 | 0.4683 | 59.4829 |
| c3 | 25.9912 | 0.6053 | 0.1512 | 0.2244 | 0.3854 | 71.4293 |
| c4 | 29.5407 | 0.5958 | 0.1268 | 0.2732 | 0.5122 | 52.3756 |
| c5 | 32.5840 | 0.4948 | 0.1463 | 0.2049 | 0.3122 | 95.6488 |

## 11. Rank1 Best-Proxy

| variant | rank1_is_best_proxy_rate | rank1_is_best_center_rate |
| --- | --- | --- |
| c1 | 0.1317 | 0.1268 |
| c2 | 0.1317 | 0.1268 |
| c3 | 0.1512 | 0.1171 |

## 12. Best-Proxy Top20

| variant | best_proxy_top5_rate | best_proxy_top20_rate | mean_rank_of_best_proxy | median_rank_of_best_proxy |
| --- | --- | --- | --- | --- |
| c1 | 0.2537 | 0.4634 | 59.3366 | 26.0000 |
| c2 | 0.2537 | 0.4683 | 59.4829 | 26.0000 |
| c3 | 0.2244 | 0.3854 | 71.4293 | 32.0000 |

## 13. Structure-Only Center-Error Reduction

Combined C1/C2/C3 are checked against structure-only S1/S2 center error. The best balanced variant is `c3`.

## 14. Truncated+Occluded Groups

| variant | truncation_degree | occlusion_degree | n_targets | rank1_is_best_proxy_rate | best_proxy_top20_rate | mean_center_error | mean_rank_of_best_proxy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| c1 | mild | mild | 14 | 0.0000 | 0.1429 | 44.1926 | 81.0714 |
| c1 | mild | moderate | 1 | 0.0000 | 0.0000 | 160.7874 | 144.0000 |
| c1 | moderate | mild | 1 | 0.0000 | 0.0000 | 31.2519 | 34.0000 |
| c1 | moderate | moderate | 6 | 0.0000 | 0.3333 | 83.1403 | 94.3333 |
| c1 | severe | moderate | 5 | 0.0000 | 0.0000 | 73.6868 | 168.0000 |
| c1 | severe | severe | 5 | 0.0000 | 0.4000 | 80.6209 | 184.6000 |
| c2 | mild | mild | 14 | 0.0000 | 0.1429 | 44.3145 | 80.9286 |
| c2 | mild | moderate | 1 | 0.0000 | 0.0000 | 160.7874 | 144.0000 |
| c2 | moderate | mild | 1 | 0.0000 | 0.0000 | 31.2519 | 34.0000 |
| c2 | moderate | moderate | 6 | 0.0000 | 0.3333 | 83.1403 | 94.3333 |
| c2 | severe | moderate | 5 | 0.0000 | 0.0000 | 73.6868 | 168.0000 |
| c2 | severe | severe | 5 | 0.0000 | 0.4000 | 80.6209 | 184.6000 |
| c3 | mild | mild | 14 | 0.0000 | 0.0714 | 47.9007 | 106.2143 |
| c3 | mild | moderate | 1 | 0.0000 | 0.0000 | 160.7874 | 228.0000 |
| c3 | moderate | mild | 1 | 0.0000 | 0.0000 | 31.2519 | 52.0000 |
| c3 | moderate | moderate | 6 | 0.0000 | 0.3333 | 85.6518 | 119.6667 |
| c3 | severe | moderate | 5 | 0.0000 | 0.0000 | 74.9774 | 200.8000 |
| c3 | severe | severe | 5 | 0.0000 | 0.4000 | 45.0025 | 196.6000 |
| c4 | mild | mild | 14 | 0.0000 | 0.2143 | 43.6971 | 65.5714 |
| c4 | mild | moderate | 1 | 0.0000 | 0.0000 | 160.7874 | 83.0000 |
| c4 | moderate | mild | 1 | 0.0000 | 1.0000 | 20.6367 | 17.0000 |
| c4 | moderate | moderate | 6 | 0.0000 | 0.5000 | 98.6769 | 84.1667 |
| c4 | severe | moderate | 5 | 0.0000 | 0.0000 | 120.7073 | 157.2000 |
| c4 | severe | severe | 5 | 0.0000 | 0.2000 | 81.4897 | 174.2000 |
| c5 | mild | mild | 14 | 0.0000 | 0.0000 | 66.6993 | 136.5714 |
| c5 | mild | moderate | 1 | 0.0000 | 0.0000 | 98.2493 | 328.0000 |
| c5 | moderate | mild | 1 | 0.0000 | 0.0000 | 56.3009 | 68.0000 |
| c5 | moderate | moderate | 6 | 0.0000 | 0.1667 | 67.4230 | 142.0000 |
| c5 | severe | moderate | 5 | 0.0000 | 0.0000 | 78.2030 | 226.8000 |
| c5 | severe | severe | 5 | 0.0000 | 0.4000 | 51.3364 | 212.4000 |

## 15. Display/Pseudocolor Risk

The structure component remains display/pseudocolor-image based. This cannot be claimed as raw SAR physics.

## 16. A005 Legacy Soft-Prior Risk

The temporal component uses A005 soft predictions, but recomputes residuals from safe fields. Legacy score and delta fields are not used.

## 17. Support For Factor Graph Combined Pilot

Decision: `True`

Reason: c3 is the most balanced by rank1 best-proxy, top20, and center-error ranks. rank1 improvement=True, top20 improvement=True, structure-only center-error reduction=True.

## 18. Failure Or Success Interpretation

If weak, likely causes include temporal-structure conflict, residual temporal artifact, display-image limits, A001 candidate issues, need for raw SAR, rotated OBB, or independent candidate proposal.

## 19. Next Step

- If C1/C2 is effective, write a factor graph prototype spec.
- If C3 is most balanced, continue with temporal-guarded structure design.
- If C4 only improves top-k but damages center error, keep it diagnostic.
- If all fail, move to raw SAR, rotated patch, or independent proposal.
- Do not return to table-level v3 tuning.

## Figures

- `output\gm17_phase4_combined_structure_temporal_fixed_pilot_20260628_224407\figures\combined_vs_all_rank1_best_proxy_rate_bar.png`
- `output\gm17_phase4_combined_structure_temporal_fixed_pilot_20260628_224407\figures\combined_vs_all_best_proxy_top20_bar.png`
- `output\gm17_phase4_combined_structure_temporal_fixed_pilot_20260628_224407\figures\combined_vs_all_mean_center_error_bar.png`
- `output\gm17_phase4_combined_structure_temporal_fixed_pilot_20260628_224407\figures\combined_proxy_recall_at_k_bar.png`
- `output\gm17_phase4_combined_structure_temporal_fixed_pilot_20260628_224407\figures\combined_condition_failure_bar.png`
- `output\gm17_phase4_combined_structure_temporal_fixed_pilot_20260628_224407\figures\combined_component_tradeoff_scatter.png`

## Panels

- Panel queue rows: 45
- Panels generated: 45

## Creative Next Ideas Appendix

Future ideas only; none affected this ranking:

- Raw SAR intensity version.
- Rotated OBB patch structure.
- Temporal-structure gating.
- Conditional future visibility/missing route.
- Independent candidate proposal.
- Factor graph prototype.
- Learned model future route.

## Explicit Non-Actions

- No v3 ranking.
- No threshold tuning.
- No training.
- No calibration.
- A021 not fed into inference.
- GT not used to tune rules.
- Source/provenance not used for sorting.

## Repair Notes

- Repair 1: the first pilot run hit a pandas group-index writeback error for temporal-unavailable rows. The fix changed only implementation indexing and did not change the pre-registered active features, weights, variants, candidate pool, or ranking rules.
