# Optical–SAR Motion Consistency Minimal Study（M0）草案

- 文档日期：2026-08-28
- 状态：`M0A_EXECUTED / M0B_NOT_EXECUTED / OPTICAL_SAR_MOTION_CONSISTENCY_NOT_ESTABLISHED`
- 依赖审计：`M0_TIME_COORDINATE_AND_INTERFACE_AUDIT.md`
- 当前权威状态：`P0_FROZEN_PASS / P1E_EXPLORATORY_OBSERVATION_INTERFACES_ESTABLISHED / RUNTIME_IDENTITY_NOT_ESTABLISHED / P2_NOT_ESTABLISHED`
- 本文不实现 tracker、identity assignment、classifier、learned fusion、SAR box 或最终定位

## 2026-08-28 M0A 执行语义收窄

本 draft 原先把 `M0A_R02_LAG1_Q95_SUPPORT_WARP_PILOT` 与后续跨模态 ambiguity reduction 连续描述。正式执行前现收窄为：

`M0A_R02_LAG1_Q95_REGION_SUPPORT_TRANSPORT_PILOT = M0 SAR-temporal prerequisite`

M0A 只检验相邻 SAR 帧 q95 region-support continuity、matched-alternative ordering，以及 frozen P0 相对 ZERO 的增量。它不读取 raw optical angular dynamics，不验证 `Δtheta_optical ↔ Δtheta_SAR`，不报告 dynamic ambiguity reduction ratio，也不回答 `static many-to-many -> dynamic fewer-to-fewer`。

只有 M0A 建立可解释的 SAR temporal structure 后，下一轮 M0B 才可在独立冻结协议中加入 raw optical angular dynamics，并定义完全 GT-blind dynamic admissibility rule。M0A 无论结果为何，都不能称为 Optical–SAR motion consistency、PERSON dynamic association、runtime identity 或最终 SAR localization。

本 draft 中 soft forward bilinear splat 只是一项早期设计建议，不再视为既成 contract。正式 M0A 以结果生成前冻结的 `M0A_R02_LAG1_Q95_REGION_SUPPORT_TRANSPORT_PROTOCOL_FROZEN_BEFORE_RUN.md` 为权威。

## 2026-08-28 M0A 执行结果

- 正式状态：`M0A_REGION_SUPPORT_TRANSPORT_WITH_P0_GAIN`，仅按冻结 M0A 解释规则成立，不是 P1/P2 PASS。
- R02 F472–F494 共纳入 22/22 adjacent comparable lag1 pairs；1117 个 q95 nodes，P0/ZERO 各 51,498 条完整 compatibility rows。
- 5/5 warp synthetic tests 通过；9 个代表点的 point-vs-mask 最大误差 `0.01553 px`，冻结容差 `0.05 px`。
- reference reveal 前 17 个表/manifest/ledger/validation/病例图已 hash freeze；pre-reference validation `14/14 PASS`，post-reference final validation `12/12 PASS`。
- 6 个 reference-supported base edges 的 q95 source-total retention：P0 median `0.9093`，ZERO median `0.8418`，paired median delta `+0.0550`；P0 对 reference-unsupported matched alternatives win rate `29/30=96.7%`，supported destination rank median `1`。
- 但 supported evidence 仅来自 3 个相邻 frame pairs、6 个 base edges，且 `6/6` 均为 shared/unresolved region explanations；不能据此声称 PERSON identity、ambiguity reduction 或一般化动态关联。
- q97.5 core median retention `0.9001`，q90 envelope median `0.9121`，相对 q95 的 median delta 分别约 `-0.0122/-0.0038`；它们提供 case-level morphology 解释，没有形成稳定的额外 aggregate gain。
- 有理由讨论一个独立冻结的最小 M0B，因为 SAR 时序排序与 P0-specific gain 在当前 reference slice 上均达到预注册条件；但 M0B 必须正面处理 sample sparsity、100% shared explanations、tiny-region deterministic cases 和尚未校准的时间语义，不能直接进入 tracker/identity/localization。

## 0. 最小研究问题

M0 不测试：

`SAR pixel speed = k × optical pixel speed`

也不预先拟合 k。

M0 测试：

> 在全部 runtime-legal optical branches 与 GT-blind SAR response-region dynamic explanations 先生成并冻结的条件下，reference-supported explanation 是否比 matched wrong explanations 表现出更稳定的短时间动态一致性，并把当前 static shell–region many-to-many ambiguity 收缩为 fewer-to-fewer，同时保留 reference-supported explanations。

光学仍只提供 time/azimuth support；SAR response field/regions 提供图像域动态解释；SAR 保留 range 与最终定位权。

## 1. 非目标与硬边界

本研究不做：

- Kalman/SORT/DeepSORT 或任何 end-to-end tracker；
- Hungarian、全局一对一 assignment 或唯一 path selection；
- PERSON identity；
- classifier、learned score fusion 或 posterior；
- SAR box regression、PERSON center prediction 或 final SAR localization；
- 用 manual reference 调 timing、mapping、guard、lag、warp、threshold；
- 用 stitched `optical_person_id` 冒充 runtime identity；
- 把 response-region 当 PERSON box/confidence；
- 把 P0 当平台真实运动或 PERSON physical motion。

所有已有历史失败、旧 gate 和旧 baseline 保留，不覆盖、不改写。

## 2. 冻结输入

### 2.1 Optical

- 只使用自动 detection rows；
- 主 hypothesis key：`raw_track_fragment_id`；
- 时间：nominal integer `timestamp_ms`；
- 动态表示：

  `I_o(t) = [theta_min(t), theta_max(t)]`

- `theta` 由当前冻结 mapping 生成；
- guard 和 time policy 必须预声明；
- `optical_person_id` 及其 parent/provenance 不能进入 consistency descriptor。

### 2.2 SAR

- 冻结 C2 与实际候选场 `S(x)`；
- q95 response-regions 作为主 node layer；
- q97.5 作为 strong core；
- q90 作为 weak support/envelope；
- 复用现有 398/398 masks、region table、SAR geometry 与 valid mask；
- region ID 只在当前 frame/layer 内有效，没有跨帧 identity。

### 2.3 P0

- 复用冻结 pair-specific model parameters；
- M0 pilot 第一版只允许使用已有 lag1 M1 pair；
- 只处理 `pair_comparable=True` 且模型 available 的相邻 nominal SAR pair；
- `P0_TRANSPORT_UNAVAILABLE` 不得替换为 zero transport；
- P0 只作为 source→destination 图像域 support transport。

### 2.4 Timing 和 mapping

- registry 固定为当前 `time_scale=1`, `offset=0` 的 nominal mapping；
- 明确标记 `TIME_SYNC_NOT_CALIBRATED`；
- 不估计或选择 offset；
- 预声明 time-shift null，结果不得回写 sync registry；
- mapping slope/intercept 和 ±6° guard 不重拟合。

## 3. M0-A：SAR temporal compatibility graph

### 3.1 Nodes

对每个 frame `t` 的每个 q95 region 建立 node：

`R_j^95(t)`

node 保留：

- q95 binary mask；
- 对应 q97.5 strong-core mask intersection；
- 对应 q90 weak-support context；
- area、theta/range span；
- centroid x/y，仅 shape descriptor；
- major/minor extent、elongation；
- boundary/truncation；
- static shell degree 与 bipartite component state；
- P0 pair/model/domain availability。

不得加入 PERSON label、manual center/range、reference coverage 或 manual-selected path。

### 3.2 执行前必须冻结的 mask-warp contract

当前仓库只有 point-wise `predict_displacement()`，没有权威 mask warp。建议第一版冻结为 soft forward support rasterization：

1. 取 source binary mask 内所有 pixel centers；
2. 用冻结 P0 求 source→destination subpixel coordinates；
3. 对 destination 四邻域做 bilinear splat；
4. 多 source pixel collision 的 occupancy 累加后 clip 到 `[0,1]`；
5. 只保留 destination single-frame valid mask 内支持；
6. out-of-frame/invalid mass 单独计为 transport loss；
7. 不做 closing、dilation、watershed 或 PERSON-conditioned repair；
8. 保存 float warped occupancy 和 source/destination validity denominators。

理由：该约定兼容 M1/M2/M3 和 subpixel displacement，不需要用 reference 调二值阈值。第一轮 primary metric 可直接使用 soft mass，不强制把 warped support 再阈值化。

执行前必须把此约定写入 frozen protocol，并以少量 synthetic geometry unit tests 验证方向、单位、边界和质量守恒；这些 unit tests 不是 PERSON experiment。

### 3.3 Edge enumeration

对每个可比较 pair `t→t+1`：

1. warp 每个 source q95 region；
2. 与 destination frame 全部 q95 regions 计算 descriptors；
3. 枚举全部满足预注册最低几何可计算条件的 edge；
4. 保留 one-to-many、many-to-one、split-like、merge-like；
5. source 无 edge、destination 无 incoming edge、后续 recover 都作为显式 state；
6. 不做 mutual-nearest、Hungarian 或唯一 path。

最低可计算条件不应以 reference 决定。推荐第一版不设 learned/fused gate，只物化全 pair matrix；若存储成本需要筛选，只允许使用预声明的极低门槛，例如 warped-support overlap > 0 或固定 angular/range dilation adjacency，并同时保留被筛除计数。

### 3.4 Primary descriptors

主描述量均为 GT-blind：

1. `q95_warped_support_retention`

   `sum(W_P0(R_j^95) * 1[R_k^95]) / sum(W_P0(R_j^95))`

2. `q95_destination_explained_fraction`

   `sum(W_P0(R_j^95) * 1[R_k^95]) / area(R_k^95)`

3. `q95_soft_iou`

   soft intersection / soft union。

4. `q97p5_core_continuity`

   source q97.5 core 经 P0 warp 后被 destination q95/q97.5 保留的比例，两个版本分列保留。

5. `q90_weak_support_retention`

   只作弱 envelope 描述，不提升为 PERSON evidence。

### 3.5 Secondary descriptors

- theta-span overlap 与变化；
- range-span overlap 与变化；
- region midpoint theta change；
- centroid displacement，仅 shape descriptor；
- area ratio/log-area change；
- principal-axis/major extent change；
- boundary/truncation transition；
- source out-of-valid mass；
- split-like / merge-like local topology；
- P0 vs zero transport descriptor delta。

禁止把上述量提前加权成单一 score。第一版以 descriptor vector 和 pairwise comparisons 为主。

## 4. M0-B：Optical dynamic representation

对每个 raw fragment 的每个合法 observation：

`I_o(t) = [theta_low(t), theta_high(t)]`

记录：

- interval midpoint；
- interval width；
- signed midpoint change；
- lower/upper boundary change；
- observation gap；
- time policy、future-use flag；
- guard-free box interval 与 guarded effective interval分列；
- fan/common-FoV clipping；
- fragment availability。

不使用 optical box center 作为 PERSON 几何真值；它只是映射后 optical hypothesis descriptor。

第一版主接口建议固定：

- `RAW_DETECTED_FRAGMENT_ALL`；
- `PAST_ONLY_250MS` 用于 causal-support sensitivity；
- `SAME_FRAME` 用于 nominal timing baseline；
- `BUFFERED_100MS` 可作为预声明 latency sensitivity；
- centered windows 只作 offline diagnostic，不与 causal result 混写。

## 5. M0-C：Cross-modal consistency descriptors

### 5.1 共同方位量

第一共同量：

`Δtheta_optical ↔ Δtheta_SAR`

其中：

- optical：raw fragment mapped interval midpoint/boundaries 的变化；
- SAR：candidate edge 两端 region theta span/midpoint 的变化；
- 两者都保持 interval/uncertainty 描述，不假设是目标真实中心。

### 5.2 第一阶段可研究的量

- signed direction concordance；
- short-window monotonicity；
- optical interval-change 与 SAR region theta-change 的 rank/ordering concordance；
- temporal phase consistency；
- P0-relative support continuity；
- exploratory local scale stability：只作为 descriptor，与 matched wrong hypotheses 比较，不拟合成 reference-optimal k。

### 5.3 SAR range

`Δr_SAR` 只作辅助证据：

- 可描述 edge 两端 range span/midpoint 变化；
- 不要求与 optical pixel/angle motion 成比例；
- optical 不提供 SAR range；
- 不用 range 生成最终位置或 PERSON box。

## 6. Controls 与 matched-null 构造

每个 control 必须由确定性规则生成，不人工挑“看起来最错”的病例。

### 6.1 Zero transport

同 source/destination region pools、同 timing、同 P0 availability，只把 warp 设为 identity。它是判断 P0-specific gain 的最强直接对照。

### 6.2 Matched wrong SAR explanation

同 destination frame 中选择错误 edge/path candidate，尽量匹配：

- temporal length；
- source/destination region area；
- shell degree、region degree；
- boundary/truncation；
- P0 availability/domain；
- initial theta relation；
- search burden。

不使用 manual target ID 生成 control；reference 只在冻结后判定其是否 supported/wrong。

### 6.3 Predeclared time-shift null

使用预先固定 shift set，例如 `±1 optical nominal step`、`±1 SAR frame` 或固定 `±100 ms`，实际值必须在 protocol 中先冻结。该 null 只诊断 timing sensitivity，不用于估计 offset，不写回 registry。

### 6.4 Matched wrong optical fragment

同 run、相近 duration、shell width、availability、initial azimuth、fragment length 和 search burden 的另一个 raw fragment；不使用 stitched parent、manual identity 或 SAR reference 选择。

### 6.5 Gross sanity controls

reverse P0 或大幅 tangential perturbation可以保留，但只标为 gross sanity，不替代 calibrated matched null。

## 7. 严格物化与评价顺序

必须按以下顺序：

1. 冻结 input hashes、timing/mapping/guard/warp/lag/control contract；
2. 枚举全部 runtime-legal optical branches；
3. 枚举全部 GT-blind SAR temporal nodes/edges/hypotheses；
4. 计算全部 dynamic descriptors 与 controls；
5. 写出 runtime/pre-reference tables、masks、manifest、execution ledger；
6. 验证 runtime schema 无 reference fields，记录 `reference_loaded=false`；
7. 冻结 hashes；
8. 才读取 manual SAR reference / offline target grouping；
9. 仅做离线解释、retention、rank 和病例评价。

manual reference 不得反向改变 edge、path generation、lag、P0、formula、threshold、control 或 branch selection。

后置 reference-supported object 统一称：

`REFERENCE_SUPPORTED_DYNAMIC_EXPLANATION`

不得称“真实散射轨迹”。

## 8. 主要评价问题与指标

主问题：

`static many-to-many → dynamic fewer-to-fewer ?`

主指标：

- static ambiguity count；
- dynamic hypothesis count；
- ambiguity reduction ratio；
- reference-supported explanation retention；
- reference-supported explanation rank；
- matched-null pairwise win rate；
- rank improvement from temporal evidence；
- P0 vs zero descriptor delta；
- unavailable/boundary/P0-domain 分母完整性。

不以 classifier accuracy 为主，不因 aggregate 平均值好看而忽略 retained wrong branches 或 lost supported explanations。

建议按 frame、pair、raw fragment、static component degree、boundary/P0 condition 分层报告，不把不同搜索负担混成一个总体数。

## 9. 可视化要求

至少固定：

- clear continue case；
- split-like case；
- merge-like case；
- disappear/recover case；
- boundary/truncated case；
- P0 better than zero case；
- zero equal/better than P0 case；
- matched wrong optical/SAR case；
- static ambiguity reduced case；
- ambiguity retained case。

每个病例显示：

- source/destination SAR；
- q90/q95/q97.5 masks；
- P0-warped q95 soft support；
- 全部 temporal edges，不只显示 chosen/best edge；
- optical raw-fragment intervals 与 time policy；
- static shell–region topology；
- reference 只作后置虚线/点 overlay。

病例必须用预声明确定性规则选取，并保留困难病例。

## 10. Failure diagnosis matrix

| 观察 | 首要解释/下一检查 | 禁止跳跃 |
| --- | --- | --- |
| SAR temporal structure 自身不稳定 | response-region、mask warp、P0、lag、boundary | 不归因于跨模态 identity |
| nominal timing弱但固定 shift 显著强 | 优先独立同步诊断 | 不把 shift 当已校准 offset |
| stitched proxy 成立、raw fragment 不成立 | runtime optical continuity 是瓶颈 | 不把 stitched ID 写成 runtime truth |
| zero transport 优于 P0 | 审查 P0 在 PERSON 邻域/当前 lag 的适用性 | 不改 P0 来追 reference |
| support continuity成立、centroid不成立 | 保留 region representation | 不强迫 point tracker |
| consistency 强于 null但 ambiguity不减少 | 动态特征存在但判别力不足 | 不宣称 identity solved |
| 人眼病例可判断而方法失败 | 定位最小失败点，设计后续修复 | 不直接 gate→stop |
| 现实病例确实不可区分 | 保留 ambiguity | 不强制唯一输出 |

## 11. 推荐的下一轮最小可执行实验

名称建议：

`M0A_R02_LAG1_Q95_SUPPORT_WARP_PILOT`

范围：

1. 只用 R02 当前已有 22 个 adjacent nominal lag1 pairs；
2. 只纳入 P0 model available 且 `pair_comparable=True` 的 pairs；
3. 主 node=q95，附带 q97.5 core、q90 weak support；
4. 冻结上述一个 soft forward mask-warp convention；
5. 枚举全部 q95→q95 pair matrix，不做 tracker/assignment；
6. 比较 P0 warp 与 zero transport；
7. 加一个预声明 time-shift null 和 matched wrong SAR edge；
8. 先物化并冻结，再用 reference 评价 ambiguity reduction/retention；
9. 固定少量直接可视化病例；
10. 不估 timing offset，不加入 optical identity selection，不生成 SAR box。

为什么这是最小实验：

- 复用已有 lag1 P0、region masks、geometry 与 comparability，不需新算法栈；
- 直接测试本阶段真正缺失的 region-support transport，而不是重复旧 peak-node threading；
- 能先判断 SAR temporal graph 本身是否有稳定、P0-specific 的 support continuity；
- 若这一层失败，跨模态一致性没有可靠基础；若成立，再加入 raw-fragment angular dynamics 才有解释价值；
- 输出仍是一组 GT-blind compatibility edges 与 ambiguity counts，不会越界成为 tracker 或 identity assignment。

## 12. 停止条件

完成上述 pilot 后应停下审阅，不自动扩展 lag3/lag5、跨 run、classifier 或 tracker。只有同时满足以下条件才讨论下一步：

- mask-warp contract 通过方向/边界/质量守恒验证；
- P0 vs zero 与 matched null 的差异可重复；
- reference-supported explanation retention 不因 ambiguity reduction 明显坍塌；
- runtime/pre-reference schema 无离线字段泄漏；
- 病例图与 aggregate 结论一致；
- nominal timing 限制被明确保留。

本文只是设计草案。本轮没有运行新的 motion-consistency 实验。
