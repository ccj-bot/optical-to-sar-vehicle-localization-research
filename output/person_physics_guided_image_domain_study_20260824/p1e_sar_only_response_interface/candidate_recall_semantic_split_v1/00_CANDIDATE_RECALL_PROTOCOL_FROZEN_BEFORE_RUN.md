# P1E 候选存在性—唯一定位性语义拆分最小实验

> 状态：`PROTOCOL_FROZEN_BEFORE_CANDIDATE_RECALL_RUN`  
> 日期：2026-08-26  
> 数据角色：R01ZF/R02ZF/R03ZF/R04ZF 全部为已暴露开发语料，不授予 P1_PASS。

## 1. 代码审阅结论

当前 C0–C3 响应图生成函数只读取 SAR 伪彩图像、扇面几何、固定物理尺度和有效掩膜。PERSON 框中心、框宽高、`physical_target_id` 和光学轨迹只在响应图生成后用于离线采样、对照和可视化。因此现有 P1E 结果保留，不重做、不删除。

需要纠正的是评价语义：

- 现有 `hard_background_score` 实际来自排除了已知 PERSON 中心邻域后的局部强响应池，改称 `local_competing_response_pool`；它检验参考位置能否击败局部最强竞争响应，不证明对照一定是纯背景。
- 现有局部峰距表示当前 `S(x)` 高分位置相对人工参考框几何中心的偏移；它不是物理空间分辨率、真实散射中心误差或场景融合的直接测量。
- 现有指标继续作为“单帧唯一定位/竞争”证据，但不能单独否定候选级可发现性。

## 2. 保持冻结的内容

- P0 主程序 SHA256：`0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8`；不修改、不重拟合、不调参。
- 当前 P1E C0–C3 代码 SHA256：`98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1`；候选公式和固定尺度保持不变。
- B0R 程序 SHA256：`3C0DFB20B58D445D224DAD7426AEB0E6DA5E065DB07059B462F1FE528CFC8ABF`；既有 B0R 结果保留。
- C2 是主候选，C3 是结构诊断候选。
- `S(x)` 仍使用固定 `0.30 m` 支持盘均值，响应尺度库仍为 `0.30/0.55/0.90 m`。

## 3. 单帧观测域 `Omega_single_v1`

`Omega_single_v1` 与 P0 时序适用域分开：

- 距离范围：`0.75 m <= range <= 20.0 m`；
- 方位范围：使用每帧真实扇面 `theta_low_deg <= theta <= theta_high_deg`，不使用 P0 的 `1.5 deg` 时序侧边退让；
- 外边界：使用真实扇面外缘，不使用 P0 的 `1.0 m` 时序退让；
- 像素必须不是扇面外白区，随后做固定 `3x3` 开运算去除单像素毛刺；
- 用固定 `0.30 m` 支持盘计算有效像素比例：
  - `FULL`：比例 `>= 0.80`；
  - `TRUNCATED`：`0.50 <= 比例 < 0.80`；
  - `INVALID`：比例 `< 0.50`。

候选中心允许位于 `FULL` 或 `TRUNCATED`，但必须携带状态。时序仍只允许使用冻结 P0 与局部背景误差预算可比较的位置，因此 `Omega_temporal` 是 `Omega_single_v1` 的子集。

## 4. GT-blind 候选提取

候选先从整帧 `S(x)` 独立生成，随后才读取人工 reference：

- 局部极大值检测物理半径：`0.30 m`；
- 贪心 NMS 最小候选间距：`0.45 m`；
- 候选最低分：`S(x) > 1e-6`；
- 不预先限制候选总数，全部候选按分数降序排列；相同分数按 `y,x` 固定排序；
- 主报告 C2，C3 作诊断敏感性；
- 候选生成阶段禁止使用标注、ID、轨迹、光学或 GT 中心邻域搜索。

## 5. 离线评价

固定：

- `K = 1, 2, 3, 5`；
- 物理覆盖半径 `r = 0.3, 0.5, 0.8 m`；
- 固定空间对照仍使用 `1.25 m` 的径向内/外、切向负/正偏移，仅用于离线评价。

逐 reference 报告：

- 最近候选距离和最近候选 rank；
- Top-K 中离 reference 最近的距离；
- `Recall@K(r)`；
- 是否与同帧其他 PERSON reference 共享同一个邻近候选，用作 `response_merging_suspected` 诊断；
- `FULL/TRUNCATED/INVALID`；
- 单帧原始 `S(x)` 分数和旧的局部最强竞争响应指标只作为并列语义层。

逐帧报告候选数、Top-5 分数、候选最小间距。汇总必须包含四个 run 和 R02 P01/P02/P03/P04。

## 6. 是否启动最小时序的预先决策规则

只有 C2 在 R02 同时满足以下开发性条件，才启动 lag1 最小时序消歧：

1. `Recall@5(0.8 m) >= 0.60`；
2. `Recall@5(0.8 m) - Recall@1(0.8 m) >= 0.20`；
3. reference 的 `Recall@5(0.8 m)` 至少比四方向固定偏移位置的中位覆盖率高 `0.10`；
4. P01 或 P02 至少一个目标的 `Recall@5(0.8 m) >= 0.50`。

该规则只决定是否值得运行最小时序，不产生 P1_PASS。

## 7. 若触发时序，冻结的最小形式

- 只运行 R02 lag1；不做长期 identity tracking；
- 每帧候选仍由 SAR-only `S(x)` 独立产生；源候选池固定 Top-20；
- 每个源候选的局部误差预算只由该帧对邻近留出背景锚点计算：半径 `144 px`、至少 `8` 个锚点、距离/方位双侧包围，`epsilon=max(local P90, global P90)`；
- 候选级最大可用 `epsilon` 固定为 `0.30 m` 对应像素，不使用 PERSON 框尺寸；
- `sigma=sqrt(epsilon^2 + (0.30 m * px_per_m)^2)`；
- 几何支持：`exp(-0.5 * (distance/sigma)^2)`；
- 组合分数：`0.5 * target_frame_S + 0.5 * max(source_S * geometric_support)`；
- 对照：无补偿 `u=0`、反向错误输运 `-u_hat`；
- GT、`physical_target_id`、插值轨迹和光学轨迹均不得参与边构造或候选选择，只用于最终离线 rank/coverage 评价。

## 8. 输出语义

本轮不追求新的 PASS/FAIL 标签。目标是区分：

- `candidate_missing`；
- `candidate_rank_competition`；
- `response_merging_suspected`；
- `boundary_or_truncation`；
- `current_representation_failure`。

旧结论“不进入时序”保留为上一开发版本的解释性决定；本实验允许依据候选召回证据修改该决定，但不修改旧文件。
