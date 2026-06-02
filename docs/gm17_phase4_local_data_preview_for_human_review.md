# GM17 Phase4 Local Data Preview For Human Review

Date: 2026-06-02

Status: local schema and tiny-sample preview for human review only. This report reads the seven listed CSV files for filesystem metadata, row counts, full headers, and the first three data rows only. It does not authorize experiments, inference, metrics, training, calibration, data-file modification, candidate-bank modification, derived dataset creation, staging, commit, or push.

Preview rule: each sample block repeats the header for readability and then shows exactly the first three data rows from that file. No full data copy is included.

## 1. `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv`

- Path: `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv`
- File size: 26799739 bytes (25.56 MiB)
- Modified time: 2026-06-01 10:08:09 local time
- Row count: 58251
- Likely role: Frozen SAR candidate bank candidate for Phase4 fixed-prior review.
- Classification: inference-safe candidate-bank source only after human approval and hash gating.
- Risk notes: Local runtime output, not automatically formal baseline. Candidate geometry may be inference-side after approval; expansion/source/temporal fields require ownership review and must not authorize candidate-bank modification or expansion.

Full header / column list:

```text
1. target_identity
2. scene
3. sar_frame
4. sar_frame_num
5. sar_pseudocolor_path
6. candidate_id
7. candidate_source
8. candidate_detail
9. cx
10. cy
11. w
12. h
13. heading
14. r
15. az
16. cross
17. delta_r_from_pred
18. delta_cross_from_pred
19. delta_az_from_pred
20. candidate_expansion_state
21. candidate_expansion_reason
22. gm17_track_id
23. gm17_anchor_strength
24. temporal_factor_score
```

First 3 rows only:

```csv
target_identity,scene,sar_frame,sar_frame_num,sar_pseudocolor_path,candidate_id,candidate_source,candidate_detail,cx,cy,w,h,heading,r,az,cross,delta_r_from_pred,delta_cross_from_pred,delta_az_from_pred,candidate_expansion_state,candidate_expansion_reason,gm17_track_id,gm17_anchor_strength,temporal_factor_score
gm_rm017_00009,GM_RM017,000302.png,302,D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png,gm_rm017_00009::base_candidate::0001,base_candidate,current_gm17_temporal_prediction,884.2430142295481,970.5339885006634,160.0,75.0,175.0,449.747,-38.36847968280792,12.0,0.0,0.0,0.0,high_risk_expand,lr_score_lt_0.9|wedge_posterior_lt_0.75,0,0.0,0.5
gm_rm017_00009,GM_RM017,000302.png,302,D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png,gm_rm017_00009::wedge_joint_candidate::0002,wedge_joint_candidate,mode_rank=1;mode_r=419.1;mode_cross=19.0;mode_az_offset=0.02,901.293322084663,1011.3249140313598,160.0,75.0,0.0,407.12177502673626,-39.34776681634841,7.007558945020477,-42.625224973263755,-4.992441054979523,-0.9792871335404882,high_risk_expand,lr_score_lt_0.9|wedge_posterior_lt_0.75,0,0.0,0.5
gm_rm017_00009,GM_RM017,000302.png,302,D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png,gm_rm017_00009::wedge_joint_candidate::0003,wedge_joint_candidate,mode_rank=1;mode_r=419.1;mode_cross=19.0;mode_az_offset=0.02,901.293322084663,1011.3249140313598,160.0,75.0,175.0,407.12177502673626,-39.34776681634841,7.007558945020477,-42.625224973263755,-4.992441054979523,-0.9792871335404882,high_risk_expand,lr_score_lt_0.9|wedge_posterior_lt_0.75,0,0.0,0.5
```

## 2. `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv`

- Path: `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv`
- File size: 190010 bytes (185.56 KiB)
- Modified time: 2026-05-28 17:27:25 local time
- Row count: 442
- Likely role: Manual final SAR box table for post-inference evaluation.
- Classification: eval-only.
- Risk notes: Contains manual/final box fields. Must be joined only after inference output exists and must not influence candidate scoring, path construction, missing-value policy, or inference outputs.

Full header / column list:

```text
1. final_id
2. scene
3. sample_id
4. sar_frame
5. sar_frame_num
6. optical_path
7. sar_pseudocolor_path
8. target_identity
9. opt_det_id
10. opt_det_label
11. final_cx
12. final_cy
13. final_w
14. final_h
15. final_heading_deg
16. final_rot_area_px
17. final_ax_x1
18. final_ax_y1
19. final_ax_x2
20. final_ax_y2
21. final_ax_area_px
22. chosen_candidate_source
23. chosen_candidate_sources_merged
24. manual_adjusted
25. visibility_status
26. review_status
27. review_note
28. review_timestamp
```

First 3 rows only:

```csv
final_id,scene,sample_id,sar_frame,sar_frame_num,optical_path,sar_pseudocolor_path,target_identity,opt_det_id,opt_det_label,final_cx,final_cy,final_w,final_h,final_heading_deg,final_rot_area_px,final_ax_x1,final_ax_y1,final_ax_x2,final_ax_y2,final_ax_area_px,chosen_candidate_source,chosen_candidate_sources_merged,manual_adjusted,visibility_status,review_status,review_note,review_timestamp
336,GM_RM011,,000000.png,0,D:\profile\research\data\GM_RM011\GM_RM011_frames\000000.png,D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000000.png,GM_RM011|000000.png|000000.png|1|O1:car:0.95,,,1140.347,1244.238,136.103,69.358,-12.000,9439.831874000001,1066.572,1196.168,1214.122,1292.308,14185.3,FULL_0514_new,FULL_0514_new,0,,reviewed,,2026-05-27T22:33:21.973414
2,GM_RM011,,000000.png,0,D:\profile\research\data\GM_RM011\GM_RM011_frames\000000.png,D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000000.png,GM_RM011|000000.png|000000.png|2|O2:car:0.87,,,1272.217,1152.230,145.119,70.695,48.000,10259.187704999998,1197.397,1074.656,1347.037,1229.804,23216.5,FULL_0514_new,FULL_0514_new,0,,reviewed,,2026-05-27T22:33:23.772696
3,GM_RM011,,000001.png,1,D:\profile\research\data\GM_RM011\GM_RM011_frames\000000.png,D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000001.png,GM_RM011|000001.png|000000.png|1|O1:car:0.95,,,1146.642,1243.802,143.942,75.440,-8.000,10858.984480000001,1070.122,1196.433,1223.162,1291.171,14498.8,FULL_0514_new,FULL_0514_new,0,,reviewed,,2026-05-27T22:33:24.348308
```

## 3. `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv`

- Path: `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv`
- File size: 87713 bytes (85.66 KiB)
- Modified time: 2026-05-28 17:27:25 local time
- Row count: 442
- Likely role: Manual visibility/truncation/occlusion condition labels for grouped review and future partial-visibility analysis.
- Classification: eval-only and future partial-visibility route only.
- Risk notes: Condition labels must not become Phase4 scoring inputs, calibration inputs, or branch activators. Partial visibility remains future Phase7 material.

Full header / column list:

```text
1. target_identity
2. scene
3. sample_id
4. sar_frame
5. sar_frame_num
6. condition_type
7. condition_degree
8. condition_status
9. truncation_degree
10. occlusion_degree
11. condition_note
12. condition_source
13. review_timestamp
```

First 3 rows only:

```csv
target_identity,scene,sample_id,sar_frame,sar_frame_num,condition_type,condition_degree,condition_status,truncation_degree,occlusion_degree,condition_note,condition_source,review_timestamp
GM_RM011|000033.png|000016.png|1|O1:car:0.88,GM_RM011,,000033.png,33,truncated,severe,reviewed,severe,none,manual_condition_review_tool,condition_review_tool,2026-05-24T22:09:31.563568
frameadd_gm_rm011_000123_000256_02,GM_RM011,frameadd_gm_rm011_000123_000256_02,000256.png,256,truncated,moderate,reviewed,moderate,none,manual_condition_review_tool,condition_review_tool,2026-05-24T22:09:35.635001
frameadd_gm_rm011_000125_000260_01,GM_RM011,frameadd_gm_rm011_000125_000260_01,000260.png,260,truncated+occluded,moderate,reviewed,moderate,mild,manual_condition_review_tool,condition_review_tool,2026-05-24T22:09:39.030277
```

## 4. `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv`

- Path: `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv`
- File size: 64342 bytes (62.83 KiB)
- Modified time: 2026-05-31 21:05:17 local time
- Row count: 205
- Likely role: Optical-to-SAR temporal soft prior table for candidate-level compatibility review.
- Classification: inference-safe soft-prior candidate only after human approval.
- Risk notes: Temporal fields must remain soft priors and must not generate or overwrite full centers. Join keys, coordinate conventions, and score ownership require human approval.

Full header / column list:

```text
1. target_identity
2. scene
3. sar_frame
4. sar_frame_num
5. sar_pseudocolor_path
6. pred_status
7. pred_cx
8. pred_cy
9. pred_w
10. pred_h
11. pred_heading_deg
12. pred_r
13. pred_az
14. pred_cross
15. score
16. lr_score
17. sar_factor_score
18. temporal_factor_score
19. gm17_temporal_source
20. gm17_temporal_decision
21. gm17_track_id
22. gm17_track_size
23. gm17_anchor_n
24. gm17_anchor_strength
25. n_candidates
```

First 3 rows only:

```csv
target_identity,scene,sar_frame,sar_frame_num,sar_pseudocolor_path,pred_status,pred_cx,pred_cy,pred_w,pred_h,pred_heading_deg,pred_r,pred_az,pred_cross,score,lr_score,sar_factor_score,temporal_factor_score,gm17_temporal_source,gm17_temporal_decision,gm17_track_id,gm17_track_size,gm17_anchor_n,gm17_anchor_strength,n_candidates
gm_rm017_00009,GM_RM017,000302.png,302,D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png,ok,884.2430142295481,970.5339885006634,160.0,75.0,175.0,449.747,-38.36847968280792,12.0,0.8700496766123451,0.8001764703658054,0.5,0.5,base,keep_base_no_anchor,0,75,0,0.0,1
frameadd_gm_rm017_000149_000310_01,GM_RM017,000310.png,310,D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000310.png,ok,902.0041512142404,986.1040863366524,160.0,75.0,0.0,426.656,-34.5740953,-12.0,0.8575798881807746,0.7609982816549539,0.5,0.9263152127595536,base,keep_base_consistent_or_weak_anchor,1,66,2,0.4854166586321305,38
gm_rm017_00016,GM_RM017,000310.png,310,D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000310.png,ok,796.5112807523187,964.7780539174112,160.0,75.0,0.0,511.175,-42.32320490687847,-18.0,0.7675070157723183,0.6862954409998868,0.6366808528168002,0.9456906195389582,temporal_shell,switch_to_temporal_shell,0,75,2,0.462920549597092,38
```

## 5. `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/signed_escape_posterior_inference.csv`

- Path: `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/signed_escape_posterior_inference.csv`
- File size: 100114 bytes (97.77 KiB)
- Modified time: 2026-06-01 11:55:05 local time
- Row count: 205
- Likely role: Row-level signed escape posterior and direction-support table.
- Classification: mixed: possible inference-safe direction support after approval; uncertainty/artifact fields are diagnostic-only.
- Risk notes: Direction posterior joins require human approval. Ambiguity/artifact probabilities and uncertainty-style fields must not become active Phase4 scoring or calibration inputs.

Full header / column list:

```text
1. target_identity
2. scene
3. sar_frame
4. sar_frame_num
5. gm17_track_id
6. P_near
7. P_neg_escape
8. P_pos_escape
9. P_ambiguous
10. P_artifact
11. posterior_confidence
12. posterior_margin
13. signed_escape_decision
14. optical_temporal_prior_score
15. ray_wedge_agreement_score
16. track_persistence_score
17. wrong_consistency_risk
18. normal_protection_score
19. old_escape_direction
20. vote_near
21. vote_neg
22. vote_pos
23. vote_near_raw
24. vote_neg_raw
25. vote_pos_raw
26. wedge_near_support
27. wedge_neg_support
28. wedge_pos_support
29. ray_near_support
30. ray_neg_support
31. ray_pos_support
```

First 3 rows only:

```csv
target_identity,scene,sar_frame,sar_frame_num,gm17_track_id,P_near,P_neg_escape,P_pos_escape,P_ambiguous,P_artifact,posterior_confidence,posterior_margin,signed_escape_decision,optical_temporal_prior_score,ray_wedge_agreement_score,track_persistence_score,wrong_consistency_risk,normal_protection_score,old_escape_direction,vote_near,vote_neg,vote_pos,vote_near_raw,vote_neg_raw,vote_pos_raw,wedge_near_support,wedge_neg_support,wedge_pos_support,ray_near_support,ray_neg_support,ray_pos_support
gm_rm017_00009,GM_RM017,000302.png,302,0,0.06753498406254022,0.6423486797808513,0.1091848499956726,0.11168253052849848,0.06924895563243745,0.6423486797808513,0.5306661492523528,neg_escape,0.2595934697507807,0.03337050525475468,0.0,1.1953602688430887,0.6427906162614928,none,0.0,0.0,0.0,0.0,0.0,0.0,0.20503683509987325,0.3868835795069838,0.06488179708939355,0.413253292001834,0.16688017844119693,0.0
frameadd_gm_rm017_000149_000310_01,GM_RM017,000310.png,310,1,0.1001854697887799,0.6317445778440284,0.09088759006866008,0.09680348570152915,0.08037887659700257,0.6317445778440284,0.5315591080552484,neg_escape,0.7266189691746365,0.030557772082395254,0.1573038060001291,1.3691134113735413,0.8136717295680994,neg,0.4930962027152617,0.37991578875842896,0.10456440379184878,0.6373780340252603,0.4621614538181924,0.1102268943855507,0.21565801654953173,0.20040629961703682,0.10263322018034075,0.4644862664535924,0.1510019116543818,0.0
gm_rm017_00016,GM_RM017,000310.png,310,0,0.15117629512667724,0.48743832899009254,0.1390382287859927,0.1287733455951266,0.09357380150211092,0.48743832899009254,0.3362620338634153,neg_escape,0.4261172997769567,0.05039008450521352,0.20313371959600757,1.2118276388984617,0.71081752997928,none,0.5961470084803047,0.2149762640724265,0.1227242391766778,0.8151116999227495,0.2398324680431371,0.1305726103230398,0.7323602992371836,0.1634527811073564,0.0,0.28840668384305757,0.14214233955428499,0.0
```

## 6. `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/candidate_refined_factor_inference.csv`

- Path: `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/candidate_refined_factor_inference.csv`
- File size: 41496586 bytes (39.57 MiB)
- Modified time: 2026-06-01 11:55:08 local time
- Row count: 58251
- Likely role: Candidate-level joined factor table containing candidate geometry, direction posterior context, and refined diagnostic scores.
- Classification: mixed: allowlist-required candidate context plus diagnostic-only SAR-structure/uncertainty fields.
- Risk notes: Rich joined table contains overlapping fields. `directional_shell_score`, `track_escape_evidence` if present, and `signed_direction_match` may be controlled diagnostic/gated support context only and must not be counted again as independent source-prior evidence unless ownership is explicitly approved.

Full header / column list:

```text
1. target_identity
2. scene
3. sar_frame
4. sar_frame_num
5. sar_pseudocolor_path
6. candidate_id
7. candidate_source
8. candidate_detail
9. cx
10. cy
11. w
12. h
13. heading
14. r
15. az
16. cross
17. delta_r_from_pred
18. delta_cross_from_pred
19. delta_az_from_pred
20. candidate_direction_bin
21. candidate_expansion_state
22. candidate_expansion_reason
23. gm17_track_id
24. directional_shell_score
25. signed_direction_match
26. geometry_escape_refined_score
27. optical_temporal_consistency_score
28. escape_conflict_score
29. normal_keep_prior
30. refined_geometry_score
31. P_near
32. P_neg_escape
33. P_pos_escape
34. P_ambiguous
35. P_artifact
36. posterior_confidence
37. posterior_margin
38. signed_escape_decision
```

First 3 rows only:

```csv
target_identity,scene,sar_frame,sar_frame_num,sar_pseudocolor_path,candidate_id,candidate_source,candidate_detail,cx,cy,w,h,heading,r,az,cross,delta_r_from_pred,delta_cross_from_pred,delta_az_from_pred,candidate_direction_bin,candidate_expansion_state,candidate_expansion_reason,gm17_track_id,directional_shell_score,signed_direction_match,geometry_escape_refined_score,optical_temporal_consistency_score,escape_conflict_score,normal_keep_prior,refined_geometry_score,P_near,P_neg_escape,P_pos_escape,P_ambiguous,P_artifact,posterior_confidence,posterior_margin,signed_escape_decision
gm_rm017_00009,GM_RM017,000302.png,302,D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png,gm_rm017_00009::base_candidate::0001,base_candidate,current_gm17_temporal_prediction,884.2430142295481,970.5339885006634,160.0,75.0,175.0,449.747,-38.36847968280792,12.0,0.0,0.0,0.0,near,high_risk_expand,lr_score_lt_0.9|wedge_posterior_lt_0.75,0,0.0,0.06753498406254022,0.023637244421889074,0.30990987311923823,0.06924895563243745,0.04341085402477032,0.017995964169749433,0.06753498406254022,0.6423486797808513,0.1091848499956726,0.11168253052849848,0.06924895563243745,0.6423486797808513,0.5306661492523528,neg_escape
gm_rm017_00009,GM_RM017,000302.png,302,D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png,gm_rm017_00009::wedge_joint_candidate::0002,wedge_joint_candidate,mode_rank=1;mode_r=419.1;mode_cross=19.0;mode_az_offset=0.02,901.293322084663,1011.3249140313598,160.0,75.0,0.0,407.12177502673626,-39.34776681634841,7.007558945020477,-42.62522497326376,-4.992441054979523,-0.9792871335404882,near,high_risk_expand,lr_score_lt_0.9|wedge_posterior_lt_0.75,0,0.0,0.06753498406254022,0.08642923478820429,0.27507491652788807,0.06924895563243745,0.008710645138850235,0.06533085880651274,0.06753498406254022,0.6423486797808513,0.1091848499956726,0.11168253052849848,0.06924895563243745,0.6423486797808513,0.5306661492523528,neg_escape
gm_rm017_00009,GM_RM017,000302.png,302,D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png,gm_rm017_00009::wedge_joint_candidate::0003,wedge_joint_candidate,mode_rank=1;mode_r=419.1;mode_cross=19.0;mode_az_offset=0.02,901.293322084663,1011.3249140313598,160.0,75.0,175.0,407.12177502673626,-39.34776681634841,7.007558945020477,-42.62522497326376,-4.992441054979523,-0.9792871335404882,near,high_risk_expand,lr_score_lt_0.9|wedge_posterior_lt_0.75,0,0.0,0.06753498406254022,0.08642923478820429,0.27507491652788807,0.06924895563243745,0.008710645138850235,0.06533085880651274,0.06753498406254022,0.6423486797808513,0.1091848499956726,0.11168253052849848,0.06924895563243745,0.6423486797808513,0.5306661492523528,neg_escape
```

## 7. `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/track_viterbi_selected_inference.csv`

- Path: `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/track_viterbi_selected_inference.csv`
- File size: 167677 bytes (163.75 KiB)
- Modified time: 2026-06-01 12:06:12 local time
- Row count: 205
- Likely role: Track-level Viterbi selected-prediction behavior reference.
- Classification: reference-only and diagnostic-only; not a Phase4 scoring input.
- Risk notes: Selected candidate IDs, path scores, switch gates, source priors, visible factors, and patch-like fields can copy selector behavior. Use only for behavior comparison after independent inference outputs exist.

Full header / column list:

```text
1. target_identity
2. scene
3. sar_frame
4. sar_frame_num
5. sar_pseudocolor_path
6. gm17_track_id
7. candidate_id
8. candidate_source
9. candidate_detail
10. candidate_direction_bin
11. cx
12. cy
13. w
14. h
15. heading
16. r
17. az
18. cross
19. delta_r_from_pred
20. delta_cross_from_pred
21. delta_az_from_pred
22. is_high_risk_inference
23. node_score
24. incoming_edge_score
25. path_score
26. path_score_delta
27. viterbi_differs_from_node_top1
28. viterbi_proposed_candidate_id
29. viterbi_proposed_source
30. viterbi_proposed_direction
31. two_stage_gate_allow_switch
32. two_stage_gate_kept_base
33. two_stage_gate_reason
34. source_prior
35. visible_factor
36. baseline_keep_prior
37. track_escape_evidence
38. directional_shell_score
39. signed_direction_match
40. geometry_escape_refined_score
41. optical_temporal_consistency_score
42. escape_conflict_score
43. normal_keep_prior
44. refined_geometry_score
45. P_near
46. P_neg_escape
47. P_pos_escape
48. P_ambiguous
49. P_artifact
50. posterior_confidence
51. posterior_margin
52. signed_escape_decision
```

First 3 rows only:

```csv
target_identity,scene,sar_frame,sar_frame_num,sar_pseudocolor_path,gm17_track_id,candidate_id,candidate_source,candidate_detail,candidate_direction_bin,cx,cy,w,h,heading,r,az,cross,delta_r_from_pred,delta_cross_from_pred,delta_az_from_pred,is_high_risk_inference,node_score,incoming_edge_score,path_score,path_score_delta,viterbi_differs_from_node_top1,viterbi_proposed_candidate_id,viterbi_proposed_source,viterbi_proposed_direction,two_stage_gate_allow_switch,two_stage_gate_kept_base,two_stage_gate_reason,source_prior,visible_factor,baseline_keep_prior,track_escape_evidence,directional_shell_score,signed_direction_match,geometry_escape_refined_score,optical_temporal_consistency_score,escape_conflict_score,normal_keep_prior,refined_geometry_score,P_near,P_neg_escape,P_pos_escape,P_ambiguous,P_artifact,posterior_confidence,posterior_margin,signed_escape_decision
gm_rm017_00009,GM_RM017,000302.png,302,D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png,0,gm_rm017_00009::base_candidate::0001,base_candidate,current_gm17_temporal_prediction,near,884.2430142295481,970.5339885006634,160.0,75.0,175.0,449.747,-38.36847968280792,12.0,0.0,0.0,0.0,True,0.7377987962166923,0.0,1.0877718641343517,1.0877718641343517,True,gm_rm017_00009::bidirectional_escape_candidate::0226,bidirectional_escape_candidate,neg_escape,False,True,gate_protected_base,0.86,1.0,0.5254488589104598,0.5681236825402618,0.0,0.0675349840625402,0.023637244421889,0.3099098731192382,0.0692489556324374,0.0434108540247703,0.0179959641697494,0.0675349840625402,0.6423486797808513,0.1091848499956726,0.1116825305284984,0.0692489556324374,0.6423486797808513,0.5306661492523528,neg_escape
gm_rm017_00016,GM_RM017,000310.png,310,D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000310.png,0,gm_rm017_00016::base_candidate::0839,base_candidate,current_gm17_temporal_prediction,near,796.5112807523187,964.7780539174112,160.0,75.0,0.0,511.175,-42.32320490687847,-18.0,0.0,0.0,0.0,True,0.8053829268994057,1.5199999809265137,3.3416532415888014,2.2538813774544497,True,gm_rm017_00016::bidirectional_escape_candidate::1064,bidirectional_escape_candidate,neg_escape,False,True,gate_protected_base,0.86,1.0,0.6287857748685888,0.487441070019141,0.0,0.1511762951266772,0.052911703294337,0.2123882645239923,0.0935738015021109,0.1074587606933633,0.0324316504742868,0.1511762951266772,0.4874383289900925,0.1390382287859927,0.1287733455951266,0.0935738015021109,0.4874383289900925,0.3362620338634153,neg_escape
gm_rm017_00020,GM_RM017,000315.png,315,D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000315.png,0,gm_rm017_00020::base_candidate::1875,base_candidate,current_gm17_temporal_prediction,near,794.3390410739911,949.1285858764464,160.0,75.0,175.0,523.737,-40.69063798345565,-24.0,0.0,0.0,0.0,True,0.7276566862295413,1.5199999809265137,5.541793424062079,2.2001401824732776,True,gm_rm017_00020::bidirectional_escape_candidate::2100,bidirectional_escape_candidate,neg_escape,False,True,gate_protected_base,0.86,1.0,0.5213772436479207,0.49944824852824826,0.0,0.1476067011375536,0.0516623453981437,0.1392322080970955,0.0863348476393057,0.0919240839705466,0.0327070922515213,0.1476067011375536,0.4562479463802708,0.1852557242851886,0.124554780557681,0.0863348476393057,0.4562479463802708,0.2709922220950821,neg_escape
```
