# P0 公共表观运动可观测性结论

**P0_PASS**

- 状态：`IMAGE_ONLY_COMMON_MOTION_OBSERVABLE_AT_PERSON_SCALE_UNDER_FROZEN_DISPLAY_DOMAIN_PROTOCOL`
- P1：`ELIGIBLE_BUT_NOT_STARTED`（本任务在 P0 停止，没有启动 P1）
- 解释边界：这里的量仅是 SAR 伪彩图像域公共表观运动与框中心残差，不是真实载体轨迹、人体固有 RCS 或目标独立运动。

## R01 模型选择与冻结

- lag 1：冻结 `M1`；选择只使用 R01 背景留出锚点。
- lag 3：冻结 `M2`；选择只使用 R01 背景留出锚点。
- lag 5：冻结 `M2`；选择只使用 R01 背景留出锚点。

## R04 完全留出验证

- 有效冻结模型帧对：579 / 579（1.000）。
- 相对 M0 降低背景留出残差的有效帧对比例：0.998；门槛 0.750。
- lag 1 / M1：改善比例 1.000，M0 中位 1.878px，补偿后中位 0.191px。
- lag 3 / M2：改善比例 0.995，M0 中位 6.058px，补偿后中位 1.366px。
- lag 5 / M2：改善比例 1.000，M0 中位 10.919px，补偿后中位 2.336px。

## 静止 PERSON 残差

- R04 PERSON 框短轴中位数：18.504px。
- 全部接受框：补偿前 P90 11.143px，补偿后 P90 3.557px；样本 1050。
- 两端均为人工锚点：补偿前 P90 12.203px，补偿后 P90 5.029px；样本 120。

## 失败帧与完整性

- 最差帧对复核：`PASS`。详见 `MULTIMODAL_WORST_FRAME_REVIEW.md` 和 `visualizations/R04_worst_pairs_montage.jpg`。
- PERSON 排除区锚点违规：0；扇面/20 m 边界违规：0。
- 不可比较原因：{}。困难帧没有按残差删除。

## 门槛

- PASS：R04_comparable_fraction_at_least_frozen_minimum
- PASS：R04_background_improvement_fraction_at_least_0_75
- PASS：R04_person_all_accepted_P90_below_short_axis_median
- PASS：R04_person_all_accepted_P90_lower_than_uncompensated
- PASS：manual_and_all_accepted_direction_consistent
- PASS：manual_person_pair_count_sufficient
- PASS：no_PERSON_or_fan_boundary_anchors_used
- PASS：R04_not_used_for_tuning
- PASS：target_regions_not_used_for_fitting_or_selection
- PASS：difficult_pairs_not_deleted
- PASS：manual_multimodal_worst_frame_review_pass

旧 `person_sar_motion_evidence_20260824` 仍是失败探针，只能说明框条件下的伪彩显示重复性，未用于本结论的物理运动解释。
