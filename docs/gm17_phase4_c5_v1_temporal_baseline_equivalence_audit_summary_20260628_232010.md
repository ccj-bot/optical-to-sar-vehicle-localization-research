# GM17 Phase4 C5-vs-v1 Temporal Baseline Equivalence Audit 20260628_232010

## Current Position

This is a post-hoc sanity check explaining why C5 and v1 can have identical rank1 center/IoU metrics while `rank1_is_best_proxy` differs.

It does not generate a new ranking, tune a threshold, train a model, calibrate weights, or modify A001/A005/A019/A021.

## Inputs

- v1 evaluation: `output\gm17_phase4_minimal_factor_pilot_20260628_110447\evaluation_per_target.csv`
- combined evaluation: `output\gm17_phase4_combined_structure_temporal_fixed_pilot_20260628_224407\evaluation_combined_per_target_by_variant.csv`
- combined variant audited: `c5`

## Method

- Join v1 rank1 rows and combined C5 rank1 rows by `target_identity + scene + sar_frame_num + gm17_track_id`.
- Compare rank1 `candidate_id`.
- When IDs differ, compare selected box geometry using `cx/cy/w/h` with a numeric serialization tolerance of `1e-9`.
- Compare post-hoc `rank1_is_best_proxy` identity status only for explanation.

## Results

- matched target groups: `205`
- same candidate_id count: `205`
- same_candidate_id_rate: `1.0000`
- same geometry count: `205`
- same_geometry_rate: `1.0000`
- different_id_same_geometry_count: `0`
- same center_error count: `205`
- same axis_aligned_proxy_iou count: `205`
- same best_proxy_candidate_id count: `175`
- same best_proxy_candidate_id rate: `0.8537`
- v1 rank1_is_best_proxy rate: `0.1122`
- C5 rank1_is_best_proxy rate: `0.1463`
- rank1_is_best_proxy changed count: `7`

## Interpretation

C5 and v1 select the same rank1 `candidate_id` and the same `cx/cy/w/h` geometry for every target.

Therefore the identical center error and axis-aligned proxy IoU are expected: the selected rank1 box is the same. The `rank1_is_best_proxy` difference is not caused by a different C5 selected candidate. It comes from post-hoc best-proxy identity accounting in the evaluation outputs: for the changed rows, the C5 evaluation marks the same rank1 candidate as the best-proxy identity while the v1 evaluation records a different best-proxy candidate ID.

## Different-ID Examples

No different-ID examples were found.

## Rank1 Best-Proxy Changed Examples

| target_identity | scene | sar_frame_num | gm17_track_id | v1_candidate_id | c5_candidate_id | v1_best_proxy_candidate_id | c5_best_proxy_candidate_id | v1_best_proxy_rank | c5_best_proxy_rank | v1_rank1_is_best_proxy | c5_rank1_is_best_proxy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gm17supp_000172_000359_det3 | GM_RM017 | 359 | 0 | gm17supp_000172_000359_det3::base_candidate::37080 | gm17supp_000172_000359_det3::base_candidate::37080 | gm17supp_000172_000359_det3::wedge_joint_candidate::37143 | gm17supp_000172_000359_det3::base_candidate::37080 | 2 | 1.0 | no | yes |
| gm17supp_000173_000361_det3 | GM_RM017 | 361 | 0 | gm17supp_000173_000361_det3::base_candidate::38404 | gm17supp_000173_000361_det3::base_candidate::38404 | gm17supp_000173_000361_det3::wedge_joint_candidate::38469 | gm17supp_000173_000361_det3::base_candidate::38404 | 32 | 1.0 | no | yes |
| gm17supp_000175_000364_det3 | GM_RM017 | 364 | 0 | gm17supp_000175_000364_det3::base_candidate::39871 | gm17supp_000175_000364_det3::base_candidate::39871 | gm17supp_000175_000364_det3::wedge_joint_candidate::39934 | gm17supp_000175_000364_det3::base_candidate::39871 | 2 | 1.0 | no | yes |
| gm17supp_000176_000366_det2 | GM_RM017 | 366 | 0 | gm17supp_000176_000366_det2::base_candidate::40686 | gm17supp_000176_000366_det2::base_candidate::40686 | gm17supp_000176_000366_det2::wedge_joint_candidate::40749 | gm17supp_000176_000366_det2::base_candidate::40686 | 6 | 1.0 | no | yes |
| gm17supp_000177_000368_det3 | GM_RM017 | 368 | 0 | gm17supp_000177_000368_det3::base_candidate::41827 | gm17supp_000177_000368_det3::base_candidate::41827 | gm17supp_000177_000368_det3::wedge_joint_candidate::41890 | gm17supp_000177_000368_det3::base_candidate::41827 | 4 | 1.0 | no | yes |
| gm_rm017_00071 | GM_RM017 | 356 | 0 | gm_rm017_00071::base_candidate::34939 | gm_rm017_00071::base_candidate::34939 | gm_rm017_00071::wedge_joint_candidate::34998 | gm_rm017_00071::base_candidate::34939 | 86 | 1.0 | no | yes |
| gm_rm017_00089 | GM_RM017 | 369 | 0 | gm_rm017_00089::base_candidate::42316 | gm_rm017_00089::base_candidate::42316 | gm_rm017_00089::wedge_joint_candidate::42375 | gm_rm017_00089::base_candidate::42316 | 106 | 1.0 | no | yes |

## Boundary Statement

- This audit reads only completed evaluation outputs.
- It does not read A001, A005, A019, or A021 directly.
- It does not create, filter, move, or re-rank candidates.
- It does not change any Phase4C rule.
