# P1E 动态证据状态：最小时序信息增益实验

> 状态：`PROTOCOL_FROZEN_BEFORE_TEMPORAL_RESULTS`  
> 日期：2026-08-26  
> 数据角色：R02ZF 为已暴露开发语料；本实验不授予 P1_PASS，不声称盲验证。  
> 研究原则：不设置“单帧达到某门槛才允许研究时序”的资格 gate。

## 1. 研究问题

候选召回语义拆分结果完整保留。接下来不再问“单帧是否通过”，而问：

1. 低 rank 但参考附近存在的候选，是否在正确冻结 P0 公共输运下获得持续的时序支持？
2. 高 rank 但多人共享的候选，是否在后续帧保持共享、发生分裂，或重新形成可分离线程？
3. 正确 P0、无输运、反向/扰动输运与帧间打乱之间，是否存在可复核的信息增益差异？
4. 哪些病例是候选真正缺失，哪些是 rank 竞争、共享/未分离、暂时弱化后恢复，哪些加入正确时序仍不改善？

本实验不追求 PASS 标签，也不提前决定时序“有资格”或“没资格”被测试。

## 2. 冻结输入与保持不变的内容

- 冻结 P0：`run_p0_common_apparent_motion.py` SHA256  
  `0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8`
- 既有 C0–C3：`run_p1e_single_frame_position_specificity.py` SHA256  
  `98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1`
- B0R：`run_b0r_minimal_applicability.py` SHA256  
  `3C0DFB20B58D445D224DAD7426AEB0E6DA5E065DB07059B462F1FE528CFC8ABF`
- 候选生成：`run_p1e_candidate_recall_audit.py` SHA256  
  `84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8`
- 全部既有 GT-blind 候选 CSV SHA256  
  `D2F1673A247FDB3AB1DD884F989ADC0ABE4E33A86AEFE45B5DFB4BE286FD6EC0`
- 候选语义解释 CSV SHA256  
  `796F20EB3080C5B45CDEBBCC71584CC95C65691F056D46C4A31704A3D86E8EC7`
- B0R 背景锚点 CSV SHA256  
  `CFEFB6D4239CDB290F0689A5E79437986FCD744FCE7F023B8F2CCBCAA8367385`
- B0R 模型参数 JSONL SHA256  
  `265ADC67D62C466F2D9523FDD06F0503BC9B4AE1343D1A63CCCC3D5FE8FF5E2D`
- B0R pair metrics SHA256  
  `862BA1FEEE5A4A540DA03230F8A15192DE117BA002AB6FE67C2E8C2EFF0D042C`

不重新拟合 P0，不修改 C2/C3，不重新生成候选，不删除候选召回语义拆分结果。

## 3. 运行数据与候选集合

- 主实验：R02ZF 全部 23 帧、22 个真实相邻 lag1 帧对（F472–F494）。
- 节点集合：既有 GT-blind C2 全候选，不按 Top-5/Top-20 截断；每帧约 219–327 个候选。
- C3 只在同一 C2 候选坐标上提供结构诊断量，不替换 C2 节点集合。
- manual native PERSON reference 只在所有节点、边、线程和对照均生成后用于离线评价。

## 4. 动态证据向量

每个 C2 候选保留分量，不预先加权成一个最终总分。

### 4.1 图像域分量

- `C2_score`
- 全帧候选池 `rank`、`rank_fraction` 与 `candidate_pool_percentile`
- 1.25 m 内最强其他 C2 候选分数及差值
- 1.0 m / 2.0 m 内候选密度
- 同坐标 `C3_score`
- 固定 0.90 m 窗口内 C2 响应加权协方差的各向异性/延展代理
- 支持比例与 `FULL/TRUNCATED`

这些量只描述显示域响应和局部结构，不解释为人体固有 RCS。

### 4.2 物理/几何分量

- 候选像素位置、距离、方位和扇面支持状态
- 冻结 lag1 M1 公共表观输运；不解释为真实平台轨迹
- 候选位置附近的背景留出锚点残差：局部 P50/P90、锚点数、最大锚点距离、距离/方位双侧包围状态
- P0 预测不是绝对点，而是中心为 `x + u_hat(x)` 的不确定区域

局部不确定度固定计算：

- 初始背景锚点半径 `144 px`
- 若半径内少于 8 个留出锚点，不丢弃候选，改用最近 8 个并标记 `NEAREST8_FALLBACK`
- `epsilon = max(local_P90, global_holdout_P90, 0.5 px)`
- `sigma = sqrt(epsilon^2 + (0.30 m * px_per_m)^2)`

这些参数只用于数值稳定和不确定区域定义，不是研究资格门。

### 4.3 时序分量

对每个目标帧候选分别保留：

- `incoming_geometry_max`
- 1σ/2σ/3σ 内前驱候选数
- `incoming_support_max = max(source_C2_score * geometric_support)`
- `incoming_support_sum`
- `incoming_support_mean`
- 最佳前驱的 image rank / percentile / 几何归一化误差
- 对称的 outgoing 分量
- 1σ 图中的 merge/split ambiguity count
- 2σ 内几何互为最近邻构成的短线程长度、平均图像分位和平均归一化误差

其中 `geometric_support = exp(-0.5 * (distance / sigma)^2)`。各分量分别评价；不先合成为唯一接口分数。

## 5. 五个对照条件

对同一实际目标帧候选集合分别生成时序证据：

1. `CORRECT_P0`：冻结 M1 正向公共输运
2. `ZERO_TRANSPORT`：不做输运
3. `REVERSE_P0`：使用 `-u_hat`
4. `TANGENTIAL_PLUS_0_75M`：正确输运后沿候选局部切向固定偏移 +0.75 m
5. `SHUFFLED_SOURCE_SHIFT7`：目标帧不变，把源候选帧按 22 个 lag1 pair 循环平移 7 位；仍使用当前真实 pair 的 P0/不确定度

第 5 个对照只用于 pair 级 incoming 证据，不解释为真实连续线程。

## 6. 图结构与透明线程

- 全部 pair 先计算完整几何核；输出边 CSV 只稀疏保留 `E <= 3σ` 的边，另记录无 3σ 邻居状态。
- 1σ/2σ/3σ 只作为不确定区域层级，不决定是否运行实验。
- 对前四个按真实相邻帧连接的条件，用 `E <= 2σ` 且几何互为最近邻的边生成一对一透明短线程。
- 完整 1σ/2σ 邻接仍保留，用于分析多前驱、多后继、合并和分叉；不会强迫每帧只有一个身份。

## 7. 离线评价

所有候选图完成后，才加载 manual native reference：

- 固定半径仍报告 0.3/0.5/0.8 m，不看结果选半径
- 比较 reference 邻近候选的单帧 S rank、incoming/outgoing 时序证据 rank 和 percentile
- 比较 `CORRECT_P0` 与四个对照的 rank/percentile 差异
- 比较 reference、四方向 1.25 m 固定偏移和全候选池的线程长度/持续性
- P01/P02：重点检查低 rank 候选是否形成较长、较低归一化误差的线程
- P03/P04：允许共享状态；在相邻 manual 时刻之间用完整 2σ 图做 reachability，记录 `SHARED / SEPARATED / PARTIAL / MISSING` 的变化
- 候选缺失、低 rank、共享、边界/截断和正确 P0 后仍不改善均保留，不删除困难帧

## 8. 直接证据

至少生成：

- R02 全序列候选线程与 x-y-t / 公共输运对齐视图
- F472→F473 的 P01/P02 低 rank 与 P03/P04 共享病例
- F482→F483 的 P02 半径级缺失病例
- F490→F491 的共享响应低 rank 病例
- 正确 P0 与无输运/反向/扰动的同图对照
- 最明显的正信息增益和阴性病例（结果后选择，明确标记为解释性选择）

## 9. 输出语义

本轮输出不是新的 PASS/FAIL，也不冻结最终接口。允许的结论形式是：

- 正确 P0 对某类候选提供了可复核的新增时序信息；
- 正确 P0 与对照不可区分；
- 只改善部分状态，例如低 rank 持续性，但不能解决共享；
- 候选本身缺失，时序没有可恢复节点；
- 当前图像表示或显示链没有足够信息。

无论结果如何，都不得使用 GT 位移、下一帧 reference、`physical_target_id`、插值轨迹、光学轨迹或人工挑选候选构造节点、边或线程。
