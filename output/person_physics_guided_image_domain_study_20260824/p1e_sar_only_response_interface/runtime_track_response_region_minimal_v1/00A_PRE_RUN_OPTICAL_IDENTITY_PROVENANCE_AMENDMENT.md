# 预运行修正：现有 optical identity 的可运行时性边界

- 修正时间：2026-08-27，实验尚未运行
- 作用范围：覆盖主协议第 4.1 节对 `optical_person_id` 的过强“运行时 track”表述；其余冻结设计不变。

## 现场追溯结论

1. 原始检测/BoT-SORT `person_id`、`tracker_local_id` 和 `raw_track_fragment_id` 由光学图像独立产生，输入表不含 `physical_target_id`。
2. 最终 `optical_person_id` 不是原始在线 tracker ID。`build_annotation_batch.py` 会读取完整 run 的 fragment，使用端点位置、速度、尺度、时间间隔和全局 Hungarian assignment 做 fragment stitching，再统一重编号。
3. `optical_person_frame_hypotheses` 还允许最多 6 光学帧的短缺口插值；该插值使用完整 fragment 支持，属于 GT-blind posthoc continuity proxy，不是严格在线输出。
4. R01/R02/R04 复用既有全密度自动光学轨迹表，R03 使用两阶段自动检测；这些 raw IDs 不使用 manual SAR reference。另有旧实验曾用人工 `physical_target_id` 选择正确光学轨迹，该旧 oracle 路径明确禁止复用。

## 修正后的 A 线

### 主接口：`RAW_DETECTED_FRAGMENT_ALL`

- 使用 `box_source=DETECTED` 的全部 `raw_track_fragment_id`，包括固定检测链产生的 BoT-SORT tracklet 和无 tracker ID 的单帧匿名 fragment。
- 不使用 `accepted_for_annotation_queue` 过滤主接口；所有自动检测 fragment 都生成壳，避免用整段持续性作隐式后验 gate。
- 不使用 posthoc 插值行。
- 这是当前数据中最接近 runtime-available identity hypothesis 的接口，但仍是已保存检测流的 replay，不声称已经部署在线系统。

### 次级接口：`STITCHED_ACCEPTED_GT_BLIND_OFFLINE_PROXY`

- 使用现有 accepted `optical_person_id` 和短缺口插值。
- 只用于估计“若未来运行时 tracker 能达到当前 GT-blind 离线拼接连续性，分支搜索成本可能如何变化”。
- 不得写成当前系统已经拥有的 runtime track identity。

### 固定比较

- 两个接口均在 `0/100/250/500 ms` 半窗下完整生成所有 track shell。
- 同时报告：单 track 分支负担、所有分支负担之和、候选重复负担、all-person union 唯一负担、reference any-track retention 和一对一离线评价。
- 人工 reference 在所有壳与候选生成后才加入，绝不选择或修复 track。

本修正是由运行前 provenance 审计触发的语义收窄，不是根据 SAR 结果调参。
