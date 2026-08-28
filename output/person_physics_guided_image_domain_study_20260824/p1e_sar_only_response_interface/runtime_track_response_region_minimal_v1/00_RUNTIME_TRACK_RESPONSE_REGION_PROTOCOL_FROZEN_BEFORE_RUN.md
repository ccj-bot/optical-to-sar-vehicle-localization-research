# PERSON P1E 运行时光学 track 壳与 C2 响应区域最小实验协议

- 状态：`FROZEN_BEFORE_RUN`
- 冻结时间：2026-08-27 14:37 +08:00
- 活动目录：`D:\profile\research\workspace`
- 解释器：`D:\MINICONDA\envs\py311\python.exe`
- 输出目录：`D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\runtime_track_response_region_minimal_v1`

## 1. 研究问题与停止点

本轮只回答两个彼此独立的问题：

1. 现有光学处理链中的运行时连续性假设，能否让每个 optical track 独立产生较窄的 SAR 方位壳，并量化时间不确定度对壳宽、候选负担和离线 reference 保留的影响？
2. 在 C2 算子完全不变时，连续 C2 场的 connected response region 是否比 local-max + NMS 离散峰更忠实地描述已存在的图像域响应？

本轮不授予 P1/P2 PASS，不生成 SAR 框，不进入多模态 tracker，也不把两条接口加权成总分。完成两项诊断、病例图、边界审计和冻结 P0 回归后停止。

## 2. 固定语义

- `optical_person_id` 只允许解释为 run-scoped runtime optical continuity hypothesis，不是人工 `physical_target_id`，也不是跨模态身份真值。
- 光学只提供 time / azimuth prior；不指定 SAR range、最终响应中心或最终框。
- C2 是伪彩显示域条件性响应，不是人体固有 RCS 或稳定物理散射中心。
- connected response region 是 C2 场的显示域超水平连通区域，不是 PERSON 框。
- `SHARED_REGION` 只表示同一图像域区域同时邻近多个离线 reference，不能解释为物理散射融合。
- 旧 P0、B0R、C0-C3、candidate split、dynamic evidence、observation diagnostic 和 matched shell 结果全部只读。

## 3. 冻结依赖

运行前逐项核验 SHA256；任一不匹配立即停止，不静默替换：

- `run_p0_common_apparent_motion.py`：`0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8`
- `run_p1e_single_frame_position_specificity.py`：`98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1`
- `run_p1e_candidate_recall_audit.py`：`84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8`
- `run_p1e_optical_shell_information_gain.py`：`2C71440DF9C22FDCE17A3C4050E4E0054F6B7CA4542C44C134E2DEA3478A2203`
- `explorer_data.js`：`C39E60EB478FF7D815EFE6984D3BCF36600737E2EC3D1FF76D04020DED54EF7D`
- `optical_person_frame_hypotheses.parquet`：`15D65A299762E87BFD6F21E811C754D1DF062AC6AFC1840A1C1A9B162AB8B478`
- `optical_person_track_summary.parquet`：`1EB79D239A2CE4733A1D55317A552FE929ACFC473F2C364BEDAF9CC38787DEA0`
- `gt_blind_candidates_all_processed_frames.csv`：`D2F1673A247FDB3AB1DD884F989ADC0ABE4E33A86AEFE45B5DFB4BE286FD6EC0`
- `manual_reference_candidate_interpretation_v2.csv`：`796F20EB3080C5B45CDEBBCC71584CC95C65691F056D46C4A31704A3D86E8EC7`
- `observation_condition_table.csv`：`DE65B9705A353F0DF783E0D4A59D0274FD05547362ABE463C50C9C5469D80C21`
- matched-shell `shell_definition_table.csv`：`8A5EDD07DB9AB452A79C9AEC95469BB42A88CA23AF6EFFA7FBA8EA26D0F39C16`

## 4. A 线：运行时 optical track-conditioned shell

### 4.1 运行时 track 集

- 输入为现有 `optical_person_frame_hypotheses.parquet` / explorer 中全部 `accepted_for_annotation_queue=True` 的 optical-only 连续性假设。
- 现有 acceptance 只依赖光学检测置信度、持续帧数、尺度和固定拼接规则；弱审阅轨迹另行计数，但不在本轮运行时壳集合中。
- 所有进入运行时集合的 track 都生成壳与 SAR candidate 输出；不得用 manual SAR reference 或 `physical_target_id` 选择“正确 track”。
- 运行前必须审计 source columns、`identity_semantics`、人工修复痕迹和每个 run 的 fragment / ambiguous-stitch 状态。若发现 track ID 本身依赖人工 `physical_target_id`，A 线停止，B 线仍可继续。

### 4.2 时间不确定度

预先固定半窗：`0 / 100 / 250 / 500 ms`。

- 0 ms：当前 nominal nearest-time optical frame，不额外积累时间窗。
- 100 ms：接近既有短时插值上限的窄窗诊断。
- 250 ms：当前注册的未验证同步不确定度。
- 500 ms：双倍不确定度压力测试。

不得根据 SAR reference 结果选择“最佳时间窗”。

### 4.3 壳与候选

- 对每一 SAR 帧、每一运行时 optical track、每一固定时间窗，合并该 track 在窗口内已有的 `theta_shell_low/high_deg`，再裁剪到实际 SAR 有效扇面。
- 同时生成同一窗口的 all-person union shell 作为现有 O2 对照。
- SAR 候选只使用既有 GT-blind C2 candidate 表；不重算或修改 C2 peak。
- 记录单 track 分支负担、all-person union 的唯一搜索负担、所有 track 分支负担之和，以及壳重叠造成的 candidate duplication。
- 离线 reference 只在全部 track 壳和壳内候选 materialize 后加入，生成完整 reference × track-shell pair 表和一对一几何评价；该关联只用于评价，不是 runtime identity selector。

### 4.4 主要描述量

- shell 有效率、有效角宽、有效面积、边界裁剪；
- 每 track 壳内 candidate count / burden / local rank；
- any-track reference coverage、candidate retention、covering-track multiplicity；
- 离线一对一 track-shell / reference coverage；
- track 壳两两角度 Jaccard、重叠宽度和候选重复数；
- R02 P01/P02 global rank → all-person-union local rank → track-local rank；
- R02 P03/P04 的 optical track 壳是否已分离，若分离，是否仍与同一个 C2 peak / response region 相交。

## 5. B 线：冻结 C2 的 connected response-region 表示

### 5.1 冻结 C2 场

- 完全复用现有 `C2_COMPACT_JET_GRADIENT_CONSENSUS` 与 `fixed_support_mean_v2` 评价场。
- 固定物理尺度保持 `0.30 / 0.55 / 0.90 m`，支持半径保持 `0.30 m`。
- 不增加 C4/C5，不改变 JET proxy、radial rank、gradient、consensus 或 robust scaling。

### 5.2 超水平连通规则

- 有效中心域：`Omega_single` 且 support fraction `>= 0.50`。
- 主阈值：每帧有效中心域内 C2 评价场的 `95th percentile`。
- 预注册敏感性：`90th / 97.5th percentile`。
- 使用 8-connectivity connected components。
- 主规则不做 opening、closing、dilation、watershed，不删除小区域，不为 F482/F490 单独调阈值。
- 每个区域记录面积、C2 均值/最大值、径向/切向范围、PCA 主/次轴物理长度、elongation、边界/support 状态；这些是区域描述，不是最终框或中心。

### 5.3 离线状态

- 区域先对整帧生成，之后才读取 manual reference。
- `region_near_reference`：reference 到区域最近像素距离 `<= 0.30 m`；同时单独记录 reference 是否直接落在区域内。
- `PEAK_PRESENT`：沿用既有 0.8 m 离散峰评价，仅描述 peak 表示。
- `PEAK_MISSING_REGION_PRESENT`：0.8 m 内无既有 peak，但主阈值区域在 0.30 m 内存在。
- `SHARED_REGION`：同一主阈值 connected component 在 0.30 m 内邻近至少两个离线 reference。
- `RESPONSE_WEAK_OR_ABSENT`：无 0.8 m peak，且主阈值区域不在 0.30 m 内；90th sensitivity 单独报告，不据此改主状态。
- `CENSORED_OR_UNOBSERVABLE`：reference support 为 TRUNCATED / INVALID；仍保留图像响应描述，不自动写成 response absent。
- `EXTENDED_OR_RIDGE_RESPONSE` 为独立结构标签：区域 PCA 主轴物理长度超过冻结 C2 最大响应尺度 `0.90 m`，或 elongation `>= 3.0`。它不覆盖 peak/region 主状态。

## 6. 两条线的最小交叉审计

只做几何相交描述，不构造融合器：在主时间窗 250 ms 和主 region threshold 95% 下，记录每个 response region 与多少个 runtime optical track shell 相交；记录同一区域是否同时与多个分离或重叠的 optical shells 相交。不得据此生成 PERSON 框、身份或总分。

## 7. 直接病例与完整性

固定检查：R02 F482、F490；R02 P03/P04 shared 病例；R02 P01/P02 低 rank 病例；R03 边界病例。另以确定性规则从完整结果选择一个 peak-present 清晰病例和一个 response-weak 病例，选择规则和全部分母写入输出，不删除困难帧。

运行后必须：

- 输出逐帧/逐 track/逐 region CSV、机器可读 summary、HTML 和病例图；
- 验证运行时表不含或不使用 `physical_target_id`；
- 验证旧 matched-shell 250 ms union 可复现；
- 运行冻结 P0 `validate_p0_outputs.py`；
- 更新现有日志与任务 README；
- 不 commit、不 push。
