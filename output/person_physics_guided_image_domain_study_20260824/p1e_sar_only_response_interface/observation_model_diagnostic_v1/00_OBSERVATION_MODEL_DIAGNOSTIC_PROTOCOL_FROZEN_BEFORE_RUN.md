# PERSON-SAR 观测模型诊断 v1：运行前冻结协议

状态：`FROZEN_BEFORE_NEW_DIAGNOSTIC_RESULTS`

日期：2026-08-26

## 1. 研究问题

本轮不增加 C4/C5，不修改 C0-C3，不重拟合冻结 P0，也不建立复杂 tracker。研究对象改为：

> 在只有 SAR JPEG/JET 伪彩图、冻结扇面几何、冻结 P0 公共表观输运以及尚未严格同步的光学先验时，一个条件性 PERSON 图像域响应处于什么观测状态；图像、几何、显示、时序和光学分别提供什么约束。

本轮不授予新的 `PASS/FAIL`，不以单帧 Recall@K 作为进入时序的 gate，不构造未经校准的总分。

## 2. 保留且只读的既有结果

- 冻结 P0：lag1=`M1`，lag3=`M2`，lag5=`M2`；不调参、不重选模型。
- B0R、P1E C0-C3、candidate semantic split、dynamic evidence temporal v1 全部保留。
- 旧 candidate 脚本中的 temporal gate 只作为历史产物，不再控制研究资格。
- 旧 `hard background` 统一解释为 `local competing-response/control pool`，不是纯背景。
- 候选峰是当前显示域的局部高响应，不是人体固有 RCS、稳定物理散射中心或真实目标轨迹。

冻结依赖 SHA256：

| 依赖 | SHA256 |
| --- | --- |
| `run_p0_common_apparent_motion.py` | `0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8` |
| `run_p1e_single_frame_position_specificity.py` | `98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1` |
| `run_p1e_candidate_recall_audit.py` | `84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8` |
| `run_p1e_dynamic_evidence_temporal.py` | `08FC073B2F5205BBD4D40DA0DD7872F006EC4E2965EABAE1D2FA50BE28E5B529` |
| C2/C3 GT-blind candidate CSV | `D2F1673A247FDB3AB1DD884F989ADC0ABE4E33A86AEFE45B5DFB4BE286FD6EC0` |
| reference semantic interpretation v2 | `796F20EB3080C5B45CDEBBCC71584CC95C65691F056D46C4A31704A3D86E8EC7` |
| fixed-offset controls | `914417E3D08758E0BAFEA2955FD11EE368E70043D4D2731C59FB8DC6B63077A3` |
| R01 PERSON azimuth pilot | `3463FFF0A8D1507ECA383356E0FB108BD60E1226A19890B62EA8C8FD5090BA42` |
| R04 cross-run azimuth audit | `24D0CEE627B272EA76A64BC245C0779DA2F6ED428E885C77490A177DBE470A14` |

运行时仍必须调用 `research_contract_v1.json` 的输入哈希核验；不一致即停止。

## 3. 统一观测实体

统一 `observation_condition_table.csv` 至少包含：

1. `PERSON_REFERENCE`：人工 SAR reference，仅离线评价；
2. `SAR_ONLY_C2_CANDIDATE`：由既有 C2 全图 GT-blind 生成的全部候选，不截断为 Top-5；
3. `FIXED_OFFSET_CONTROL`：既有径向/切向 1.25 m 对照；
4. `GEOMETRY_MATCHED_CONTROL`：既有同距离、切向平移对照；
5. `LOCAL_COMPETING_CONTROL`：既有局部最强竞争响应位置。

每个实体使用同一位置条件计算函数。reference/ID/框只用于离线标注实体和结果解释，不进入 C2/C3、P0、光学壳或候选生成。

## 4. 单帧观测条件

每个位置固定记录：

- range、azimuth；
- 到左/右扇面边界的角距离及对应弧长；
- 到 20 m 外边界的距离；
- fixed 0.30 m support 的有效像素比例；
- `FULL / TRUNCATED / INVALID` 支持状态；
- C2 fixed-support score、全有效区 percentile；
- 最近 C2 候选距离、rank、rank fraction；
- 1 m/2 m 候选密度、局部最强竞争响应差；
- C3 at-position、C2 局部 anisotropy、spread 和 orientation。

不把 reference center 到局部峰的距离解释为物理分辨率或真实散射中心误差。

## 5. 显示链代理

RGB/JET 三通道视为同一显示标量的冗余编码，不作为独立雷达物理通道。每帧仅记录可审计的显示代理：

- JET 最近 LUT 标量的 p01/p05/p50/p95/p99 和 p95-p05；
- 有效区 32-bin 标量熵与有效量化级数；
- 高端平台比例 `JET>=250/255`；
- 低端平台比例 `JET<=5/255`；
- 到理想 JET LUT 的 JPEG 颜色距离 p50/p95；
- 非白有效区比例；
- 冻结 P0 的 pairwise JS divergence 与 display stratum。

描述性状态固定为：

- `DISPLAY_HIGH_CENSOR_PROXY`：高端平台比例 >= 1%；
- `DISPLAY_COMPRESSED_PROXY`：p95-p05 < 0.15 或有效量化级数 <= 24；
- `DISPLAY_SHIFT`：相邻 pair 为冻结 P0 elevated/high stratum，或任一连续显示代理在 run 内 robust |z|>3；
- 以上均不是回波物理变弱/增强的证明。

## 6. 空间可靠域：多标签而非统一 gate

### SAR_SINGLE_FRAME_OBSERVABLE

- 连续量：fixed-support 有效比例；
- 标签：`FULL / TRUNCATED / INVALID`；
- 不继承 P0 的 1 m 外边界退让和 1.5° 侧边退让作为单帧不可观察判定。

### P0_TRANSPORT_CORE

位置与 pair 同时满足：

- 冻结 pair comparable 且冻结 selected model available；
- source 位于冻结 P0 base mask；
- 144 px 半径内至少 8 个 holdout anchors，不使用 nearest-8 fallback；
- range 与 azimuth 两维均被 holdout anchors 双侧包围；
- 冻结输运预测点位于 destination `SAR_SINGLE_FRAME_OBSERVABLE`。

### P0_TRANSPORT_EXTENDED

selected model 可预测且 source/destination 仍有单帧观测，但因 P0 边界退让、单侧锚点、锚点不足而使用 nearest-8、或局部 sigma 较大而不属于 CORE。它是“可预测但不确定度更大”的描述，不是自动删除。

### P0_TRANSPORT_UNAVAILABLE

selected model/pair 不可用、没有 holdout support、或 source/destination 单帧观测无效。

不把上述标签合成为一个总可靠度分数。保留 local sigma、anchor count、bracketing、coverage span、fallback 和边界距离的原始维度。

## 7. lag1/3/5：几何可分辨性与响应保持性

固定诊断量：

1. `transport_separability = |u_hat_l(x)| / sigma_local_l(x)`；仅描述 correct 与 zero 的几何分离程度，不设门槛。
2. `C2_field_retention_correct`：在每 4 px 的确定性网格上，source C2 fixed-support 场与按冻结 P0 取样的 destination C2 场的 Pearson 相关。
3. `C2_field_retention_zero`：同一 source/destination、同一网格，不做输运。
4. `correct_minus_zero_retention`：只比较对齐是否带来新增信息。
5. source C2 候选在 correct/zero 预测位置的 destination C2 score/percentile，候选池不做 Top-K 截断。

同时按 run、lag、display stratum、P0 domain 和 edge 状态分层。lag 变大并不预设更好：预期同时观察几何分离上升和显示域响应去相关。

## 8. 光学软引入审计

只审计 O1/O2，不让光学决定 SAR range 或最终位置。

- 固定 common-FoV 映射来源：R01 PERSON pilot `theta = 0.02666536443690682*u - 45.502258572693094`；状态为 provisional，R04 仅证明 conditional plausibility，未冻结 runtime calibration。
- 固定光学画幅 `[0,3840]` 映射到的 provisional 方位范围与 SAR 扇面交集，作为 `MULTIMODAL_COMMON_FOV_PROVISIONAL`；不外推为精确映射。
- 使用 explorer 中已存在的 `theta_shell_low/high`，其 provenance 为 `PROVISIONAL_R01_R04_CENTERLINE_PLUS_6DEG_GUARD_SYNC_UNVERIFIED`。
- O2 时间窗固定为名义配对前后 `±250 ms`；壳为窗口内所有 optical PERSON 壳的并集，不用 physical_target_id 选择。
- 等宽 shifted-shell control 固定为每个壳整体 `-18°` 与 `+18°`；不根据结果选 shift。
- 分别报告 reference、C2 candidates 和 controls 的 nominal/window shell coverage；reference 仅离线评价。

若正确壳与 shifted 壳无差异，记录阴性结果；若正确壳只因面积更大获益，不能称为跨模态信息。

## 9. 真实病例与二维图

报告至少直接展示：

- R02 P01/P02 低 rank 或 missing；
- R02 P03/P04 shared/overlap；
- R03 20 m 边界截断与恢复；
- 一个 display-shift 明显病例；
- 一个 P0 anchor fallback/单侧覆盖病例；
- 一个 isolated/clear 对照病例。

每个病例包含原始 SAR、C2 响应、全部局部候选、manual reference（离线叠加）、fixed/matched controls、边界、显示状态和 P0 条件。shared/merge-like 只描述图像域候选共享，不作物理散射融合结论。

## 10. 固定输出

- `observation_condition_table.csv`
- `frame_display_condition_table.csv`
- `p0_local_transport_condition_table.csv`
- `lag_transport_response_tradeoff.csv`
- `optical_shell_audit.csv`
- `condition_state_summary.csv`
- `diagnostic_summary.json`
- `visualizations/`
- `P1E_OBSERVATION_MODEL_DIAGNOSTIC_REPORT.html`
- `report_validation.json`

## 11. 停止条件与措辞

本轮结束于诊断结论，不进入新特征冻结、复杂 tracker 或正式多模态定位实验。允许的结论形式是：

- 某类 response state 与某些观测条件集中共现；
- 冻结 P0 的空间可靠性随 range/azimuth/anchor coverage 变化；
- 某 lag 下 correct 与 zero 的几何可分性和 C2 保持性如何权衡；
- 当前 provisional optical shell 是否值得进入下一轮受控多模态候选实验。

禁止把相关共现写成单一因果证明，禁止把伪彩亮度写成人体固有 RCS，禁止把 P0 写成真实平台轨迹。
