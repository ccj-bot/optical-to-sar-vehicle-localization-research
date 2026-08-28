# PERSON P1E 光学方位壳不确定度与 SAR 响应区域拓扑最小诊断协议

- 状态：`FROZEN_BEFORE_RUN`
- 冻结时间：2026-08-27 19:17 +08:00
- 活动目录：`D:\profile\research\workspace`
- 解释器：`D:\MINICONDA\envs\py311\python.exe`
- 输出目录：`D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\shell_uncertainty_region_topology_v1`

## 1. 本轮问题与停止点

本轮只回答：

1. 现有 optical azimuth shell 的宽度、重叠和不可用性分别由检测框角跨度、固定 mapping guard、时间窗 union、raw fragment 可用性/重叠以及 SAR fan/common-FoV clipping 贡献多少；
2. 在不读取人工 `physical_target_id` 或 SAR reference 的运行状态下，每帧全部 optical raw-fragment shells 与冻结 C2 q90/q95/q97.5 response regions 能形成何种二部关系拓扑。

若 A/B 已回答清楚，本轮停止；不机械进入 P0 region 时序传播。不授予 P1/P2 PASS，不生成 SAR range/box，不构造总分、分类器或 tracker。

## 2. 固定研究边界

- 主 optical 接口：`RAW_DETECTED_FRAGMENT_ALL`。每个自动 detected `raw_track_fragment_id` 独立出壳；不使用 `accepted_for_annotation_queue` 作运行时 gate。
- `optical_person_id` 只允许作为 GT-blind offline stitching provenance，用于量化 fragmentation；不是严格 runtime identity，更不是人工 `physical_target_id`。
- 光学只提供 time/azimuth prior，不指定 SAR range、response center 或最终框。
- C2、q90/q95/q97.5 masks 与 region descriptors 全部复用上一轮冻结产物，不重算、不调阈值。
- q95 region 不是 PERSON box；shared/merge-like 只描述图像域重叠，不证明物理散射融合。
- JET/RGB 是显示链观测，不解释为人体固有 RCS 或稳定物理散射中心。
- 所有 shell、region、edge、topology 与 GT-blind node state 必须先完整生成；SAR reference 只在其后物化用于离线解释。

## 3. 冻结依赖与哈希

任一依赖不匹配立即停止，不静默替换：

- `run_p1e_runtime_track_response_region_minimal.py`：`051B414753B73118CF77712A35DF86EC5FB05C12B2C00217EB14BFE81DFDCBBA`
- `run_p1e_candidate_recall_audit.py`：`84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8`
- `run_p1e_optical_shell_information_gain.py`：`2C71440DF9C22FDCE17A3C4050E4E0054F6B7CA4542C44C134E2DEA3478A2203`
- `track_shell_definition_table.csv`：`B6C58404F54F542133EE5678EBB93B97758BE85EFE71CA252C41FD3018C061C5`
- `response_region_table_pre_reference.csv`：`A2BB425C366EA0DE461C427113E8E836A556F65250677146B6F26129E853C339`
- `candidate_recomputation_parity.csv`：`21FA3270E268EEC460E603C07F1D840182780E0FB671B0ABFC04E12256C35329`
- `offline_reference_response_region_evaluation.csv`：`4522FE9B65249180B073EA16E87BF11A528DC079B3831348CD7610E3685B7353`
- `observation_condition_table.csv`：`DE65B9705A353F0DF783E0D4A59D0274FD05547362ABE463C50C9C5469D80C21`
- `optical_person_frame_hypotheses.parquet`：`15D65A299762E87BFD6F21E811C754D1DF062AC6AFC1840A1C1A9B162AB8B478`
- `R01 model_summary.json`：`3463FFF0A8D1507ECA383356E0FB108BD60E1226A19890B62EA8C8FD5090BA42`
- `R04 validation_report.json`：`24D0CEE627B272EA76A64BC245C0779DA2F6ED428E885C77490A177DBE470A14`
- `explorer_data.js`：`C39E60EB478FF7D815EFE6984D3BCF36600737E2EC3D1FF76D04020DED54EF7D`
- 398 个 `response_region_masks/*.npz` 的排序 `name:sha256` 聚合 SHA256：`0D9E10C41DB2EE02E060E9AF789AC59C6CD80591B11DC591222CA2B400656CB1`

## 4. A：方位壳不确定度分解

### 4.1 固定映射与精确分解

沿用固定线性映射：

`theta = 0.02666536443690682 * optical_x - 45.502258572693094 deg`

当前每侧 guard 固定为 `6 deg`。对每个 frame × raw fragment × temporal policy，报告：

- 单个 detection box 的角宽中位数/最大值；
- 无 guard 的 detection-box interval union 宽度；
- 时间/视角扩张：`raw box union width - representative single-box width`；
- guard 实际增量：`guarded union width - raw box union width`；
- fan clipping 损失：`guarded union width - effective in-fan width`；
- common-FoV overlap、左右 clipping、有效面积和负担；
- source observation count、raw fragment/parent stitched provenance、future-observation 使用状态。

这四项构成代数分解，不把 mapping residual 当独立随机物理量。

### 4.2 预先固定的时间策略

- `SAME_FRAME`：仅 `timestamp == nominal optical timestamp`，零未来观测；
- `PAST_ONLY_250MS`：`[-250, 0] ms`，零未来观测；
- `BUFFERED_100MS`：`[-250, +100] ms`，允许固定 100 ms 延迟；
- `CENTERED_250MS`：`[-250, +250] ms`，可使用未来观测；
- 另复核既有 centered `0/100/250/500 ms` 宽度—retention—burden 描述，不据结果选“最佳窗口”。

### 4.3 guard/mapping 几何敏感性

预先固定：

- `CURRENT_G6`：每侧 6 deg，当前实现；
- `R04_MAE_PROXY_G2P652`：每侧 2.651812 deg，只是“若 cross-run mapping/timing error 可压缩到既有 R04 nominal-zero macro MAE 量级”的几何敏感性，不是校准覆盖界；
- `NO_GUARD_LOWER_BOUND_G0`：每侧 0 deg，只给 raw optical box 投影下界，不是可部署壳。

三者全部运行，不按 SAR reference 选择。必须明确：纯 intercept 修正只平移壳，不自动缩窄；只有可验证的 mapping uncertainty 下降才可能合理缩 guard。

### 4.4 离线解释

在全部 shell 生成后，才使用 reference：

- 报告 reference retention、burden 与 one-to-one angular assignment；
- 专门报告 R02 P01/P02、P03/P04 的 associated-shell Jaccard；
- 回答 same-frame 下不可分性还剩多少，以及在固定时间策略下仅缩 guard 的几何上限；
- 不用 reference 调 mapping、guard、窗口或 raw fragment。

## 5. B：GT-blind shell ↔ response-region 二部拓扑

### 5.1 主拓扑切片

主接口固定为 raw fragments + `CURRENT_G6`。对 `SAME_FRAME`、`PAST_ONLY_250MS`、`CENTERED_250MS` 三个时间策略，以及 q90/q95/q97.5 三层分别构图。

每帧先生成所有 shell nodes、region nodes，再按真实像素相交生成 edges。角包围盒相交不能替代像素相交。

### 5.2 节点和边字段

- shell：有效角宽/面积、clipping、common-FoV overlap、fragment provenance、是否使用未来观测；
- region：面积、角/距离跨度、compact/extended-ridge、observable-boundary/truncated support、accepted-peak artifact coverage；
- edge：intersection pixel count/area、region coverage fraction、shell coverage fraction、intersection theta/range span；
- condition：frame display JS/shift；P0 仅使用 GT-blind C2 candidate 采样形成 `candidate-sampled` condition，没采样时明确 `UNAVAILABLE`，不得用 reference 填补。

### 5.3 GT-blind 拓扑状态

按二部连通分量标记：

- `ONE_SHELL_ONE_REGION`
- `ONE_SHELL_MULTIPLE_REGIONS`
- `MULTIPLE_SHELLS_ONE_REGION`
- `MULTIPLE_SHELLS_MULTIPLE_REGIONS`
- `SHELL_NO_REGION`
- `REGION_NO_SHELL`

这些状态可直接运行时计算，但不等于 PERSON identity 或最终定位。

### 5.4 峰/区域语义分层

GT-blind 可计算：region level/shape、edge/censor、shell/region degree、component topology、以及仅在 legacy candidate artifact 覆盖帧内的 `accepted peak in region`。

必须离线 reference-conditioned：`PEAK_PRESENT`、`PEAK_MISSING_REGION_PRESENT`、PERSON `SHARED_REGION`、reference retention/rank、P01/P02/P03/P04 病例解释。旧 candidate artifact 未覆盖的 272 帧不得写成 peak absent。

## 6. 直接病例与可视化

固定病例：R02 F482/F490；R02 P01/P02 low-rank；R02 P03/P04 shared；一个 R03 edge case。另按确定性规则从完整 GT-blind topology 中选典型 `one-shell/multi-region`、`multi-shell/one-region` 和 `shell/no-region`，不删除困难帧。

每个病例至少显示：原 SAR 图、q90/q95/q97.5 region、全部 raw shell、像素级 edges、GT-blind component state；reference 只作为后置虚线/点叠加。

## 7. 完整性与停止条件

- 输出逐 shell 分解、frame uncertainty、guard counterfactual、pixel edge、node/component/frame topology、离线 reference interpretation、机器 summary、中文 HTML 与病例图；
- 自动验证运行时表不含 `physical_target_id`，shell/region/edge 生成时间先于 reference materialization；
- 冻结 P0 `validate_p0_outputs.py` 必须回归；
- 更新 README 与现有日志；
- 不读取/依赖 `old_work`，不修改原图/标注/P0/B0R/C0-C3/旧结果，不创建或移动 SAR 框，不 commit/push。
