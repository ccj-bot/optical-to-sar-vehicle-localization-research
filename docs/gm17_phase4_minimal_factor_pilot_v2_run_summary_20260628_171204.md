# GM17 Phase4 Minimal Factor Pilot V2 Run Summary 20260628_171204

## 1. Purpose

This v2 run tests whether fixed, no-training rules can reduce the v1 temporal-zero base-candidate artifact and expose useful geometry/coordinate residual signal.

## 2. Inputs And Outputs

- Pilot output: `D:\profile\research\workspace\output\gm17_phase4_minimal_factor_pilot_v2_20260628_171204`
- Evaluation summary: `D:\profile\research\workspace\output\gm17_phase4_minimal_factor_pilot_v2_20260628_171204\evaluation_v2_summary.json`
- Figures: `D:\profile\research\workspace\output\gm17_phase4_minimal_factor_pilot_v2_20260628_171204\figures`

## 3. V2 Variant Definitions

- `v2a_temporal_soft_geometry_cluster`: geometry_valid first; score=temporal_distance_raw + geometry_cluster_distance; fixed 1:1.
- `v2b_geometry_cluster_first`: geometry_valid first; geometry_cluster_distance first; temporal_distance_raw secondary.
- `v2c_temporal_zero_neutralized`: geometry_valid first; score=geometry_cluster_distance + temporal_rank_percentile; temporal zero marked but not an absolute winner.

## 4. Field Use And Forbidden Fields

Ranking used only A001 safe candidate fields and A005 `pred_r/pred_cross/pred_az`. It did not use GT, A021 condition labels, `candidate_source`, legacy `delta_*`, `temporal_factor_score`, `score/lr_score/sar_factor_score`, selected outputs, B patch, oracle fields, or condition/truncation/occlusion fields.

## 5. Join Situation

{
  "join_keys": [
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id"
  ],
  "a005_unique_key_rows": 205,
  "a005_ambiguous_keys": 0,
  "candidate_rows_join_ambiguous": 0,
  "candidate_rows_missing_temporal_prior": 0,
  "candidate_rows_matched": 58251
}

## 6. Geometry Cluster Distance

`geometry_cluster_distance` is computed within each target/frame/track candidate group from robust deviations of heading, r, cross, az, and area. Scales come from group MAD, then IQR, then fallback 1. No GT statistics or A019/A021 fields are used in this distance.

## 7. Core Results

| variant | mean_center_error | median_center_error | mean_axis_aligned_proxy_iou | proxy_iou_recall_at_1_threshold_0_25 | center_recall_at_1_threshold_50px | proxy_iou_recall_at_3_threshold_0_25 | proxy_iou_recall_at_5_threshold_0_25 | rank1_is_best_proxy_rate | rank1_is_best_center_rate | best_proxy_top5_rate | best_proxy_top20_rate | mean_rank_of_best_proxy | rank1_temporal_zero_rate | n_targets | median_axis_aligned_proxy_iou | center_recall_at_3_threshold_50px | center_recall_at_5_threshold_50px | best_proxy_iou_coverage_threshold_0_25 | best_center_coverage_threshold_50px | median_rank_of_best_proxy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v1 | 32.5840 | 26.6502 | 0.4948 | 0.7512 | 0.7756 | 0.7854 | 0.8341 | 0.1122 | 0.1024 | 0.1805 | 0.2878 | 67.5756 | 1.0000 |  |  |  |  |  |  |  |
| v2a | 33.3057 | 27.2421 | 0.4887 | 0.7561 | 0.7756 | 0.8195 | 0.8585 | 0.1073 | 0.0976 | 0.1610 | 0.2878 | 72.2732 | 0.8683 | 205.0000 | 0.5309 | 0.8146 | 0.8439 | 1.0000 | 1.0000 | 42.0000 |
| v2b | 39.2576 | 29.1475 | 0.4381 | 0.7707 | 0.7366 | 0.7902 | 0.8146 | 0.0098 | 0.0098 | 0.0829 | 0.2049 | 87.5415 | 0.1073 | 205.0000 | 0.4710 | 0.7805 | 0.7951 | 1.0000 | 1.0000 | 66.0000 |
| v2c | 37.4089 | 28.4641 | 0.4526 | 0.7659 | 0.7512 | 0.8000 | 0.8146 | 0.0244 | 0.0244 | 0.1024 | 0.2634 | 76.3707 | 0.2049 | 205.0000 | 0.4764 | 0.7902 | 0.8049 | 1.0000 | 1.0000 | 50.0000 |

## 8. V1 vs V2 Comparison

- V1 rank1_is_best_proxy: 0.1122
- Best V2 variant by rank1_is_best_proxy: `v2a` at 0.1073
- V1 best_proxy top5/top20: 0.1805 / 0.2878
- `v2a` best_proxy top5/top20: 0.1610 / 0.2878
- V1 proxy IoU recall@1: 0.7512
- Best V2 proxy IoU recall@1: `v2b` at 0.7707
- V1 proxy IoU recall@5: 0.8341
- Best V2 proxy IoU recall@5: `v2a` at 0.8585

## 9. Best Variant

`v2a` is the strongest variant by rank1_is_best_proxy rate in this fixed diagnostic pilot, but it does not improve that metric over v1. `v2b` has the highest proxy IoU recall@1, but its best-proxy rank and rank1_is_best_proxy are much worse. Treat `v2a` as the least disruptive v2 variant, not as a successful final rule.

## 10. Rank1 Best-Proxy Improvement

V2 did not improve rank1_is_best_proxy. V1 was 0.1122, while the best V2 value was `v2a=0.1073`. This means the fixed v2 rule did not make rank1 select the best-proxy candidate more often.

## 11. Best-Proxy Top5 / Top20

V2 did not improve best_proxy top5/top20. V1 top5/top20 was 0.1805 / 0.2878. `v2a` was 0.1610 / 0.2878, `v2b` was 0.0829 / 0.2049, and `v2c` was 0.1024 / 0.2634.

## 12. Truncated+Occluded Failure

A021 condition labels were used only after v2 outputs existed, for post-inference grouping. Truncated+occluded groups still have rank1_is_best_proxy rate 0.0 across all v2 variants. Some v2b/v2c groups reduce mean center error relative to v2a, but the failure mode is not resolved because best-proxy candidates remain deep in rank for many truncated+occluded combinations. See `evaluation_v2_condition_groups_by_variant.csv` and `v2_condition_failure_bar.png`.

## 13. Legacy Artifact Status

V2 explicitly records `temporal_zero` and avoids using legacy `delta_*` or `temporal_factor_score`. `v2b` and `v2c` substantially reduce rank1 temporal-zero rate from v1's 1.0000 to 0.1073 and 0.2049, respectively, but they also damage rank1_is_best_proxy and best-proxy top5/top20. `v2a` keeps stronger recall@3/@5 but still has rank1 temporal-zero rate 0.8683. The legacy artifact is therefore reduced only when geometry dominates, and that tradeoff is not yet useful.

## 14. Overfit Or Instability Risk

No parameters were tuned from GT, but the fixed group-robust distances may still be unstable in small or degenerate candidate groups, especially when MAD/IQR fall back to 1. Treat this as factor signal diagnosis, not a final model.

The manifest reports fallback scale methods for `aspect` and `area` in all 205 groups. That means this v2 geometry cluster signal is mostly carried by heading/r/cross/az rather than size/aspect/area. This is a rule-stability risk and a sign that area/aspect are weak under this group-relative design.

## 15. Repair Note

The first evaluation run failed while writing the Markdown summary because the optional pandas `tabulate` dependency was not installed. The script was repaired once by replacing `DataFrame.to_markdown()` with an internal Markdown table writer. No ranking rule, evaluation metric, input data, or threshold was changed.

## 16. Next Step

- If V2B is effective, deepen `geometry_factor` fixed-prior design.
- If V2C is effective, redesign `optical_temporal_factor` so temporal evidence remains soft.
- If neither is effective, the likely need is new candidate proposal or a SAR structure factor.
- Do not continue threshold tuning; summarize factor signal first.
