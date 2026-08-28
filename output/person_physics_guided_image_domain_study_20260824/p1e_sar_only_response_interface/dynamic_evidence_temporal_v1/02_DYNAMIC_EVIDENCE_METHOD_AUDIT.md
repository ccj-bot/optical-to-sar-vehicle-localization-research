# PERSON P1E 动态证据方法审阅

> 审阅性质：独立只读复核；不修改冻结 P0、B0R、C0-C3、候选或动态图结果。  
> 总判断：计算依赖保持 GT-blind；时序持续结构成立；P0-specific lag1 增益未建立。

## 1. GT-blind 的准确边界

- `build_static_nodes` 只使用既有 C2 候选、SAR 图、单帧有效掩膜、C2/C3 和扇面几何；节点/边/线程没有访问下一帧 reference、target ID、optical 或插值轨迹。
- reference CSV 在运行图前被 SHA256 读取，含 annotation 字段的 explorer 容器也在图前整体加载；但这些 reference/annotation 数值没有进入图计算。
- 因此允许的表述是“reference content did not participate in graph computation”，不是“reference/annotation data were never read or loaded”。本轮不声称严格 sealed-data process isolation。
- 冻结 P0 的 background anchors 继承了 P0 阶段的 PERSON 排除掩膜；这不是本轮定位 GT 泄漏，但未来真正在线 SAR-only P0 仍需定义运行时排除区来源。

## 2. CORRECT 与 ZERO 的全图相似度

| component | frames | median frame Spearman | median exact-rank ties | median |rank delta| |
| --- | --- | --- | --- | --- |
| geometry | 22 | 0.9142 | 1.6% | 21.5 |
| max | 22 | 0.9756 | 3.4% | 11.5 |
| sum | 22 | 0.9794 | 4.0% | 10.0 |
| mean | 22 | 0.9916 | 19.3% | 2.0 |

| control | correct edges | control edges | correct-edge overlap | Jaccard |
| --- | --- | --- | --- | --- |
| No transport | 4654 | 4661 | 96.0% | 0.9210 |
| Reverse P0 | 4654 | 4615 | 91.0% | 0.8413 |
| +0.75 m tangential | 4654 | 3199 | 8.3% | 0.0516 |

- CORRECT-vs-ZERO 互为最近邻边覆盖率 96.0%，Jaccard=0.9210。
- 按 node 对齐线程长度 Spearman=0.8998，完全相等 73.8%，绝对差中位数 0.0。
- shared reachable state 为 32/32 完全一致。
- 这比“reference 中位 +1.5 rank”更直接地说明：当前主要时序结构是慢变化/同坐标持续性，尚未分离出稳定 P0-specific 增量。

## 3. 对照公平性

- `ZERO_TRANSPORT` 是最强对照：同帧池、同目标帧、同不确定度，只去掉 P0 位移。
- `REVERSE_P0` 是同尺度错误方向对照，但 CORRECT 与 REVERSE 的边/线程仍有高重合。
- `TANGENTIAL_PLUS_0_75M` 约为真实 lag1 位移的 7.3 倍，且 4.5% 预测出有效区，只能作 gross sanity。
- `SHUFFLED_SOURCE_SHIFT7` 只有一个固定 shift；源候选池相对真实源每 pair 相差 -97 至 +92，混入帧内容、候选池规模和显示差异，不是校准随机 null。

## 4. 不确定度与局部锚点覆盖

- 6147 个 source-node uncertainty row 中，nearest-8 fallback 为 22.4%。
- radial 未双侧包围 27.6%；theta 未双侧包围 18.3%；任一维未包围 39.7%。
- sigma 中位/P90/最大为 0.3005 / 0.3120 / 0.3264 m；它是设计容差层级，不是校准置信区间。
- lag1 P0 位移中位约 0.1030 m，仅为 sigma 的 0.342，直接限制 CORRECT 与 ZERO 可分性。

## 5. reference 重复与 SHARED 语义

- 30 个 incoming-max 可评价 reference 行只对应 20 个 unique `(frame, best node)` outcome；10 个 outcome 被两个 reference 共用。
- P01/P02 间距 0.510–0.656 m；P03/P04 间距 0.695–0.808 m；审计半径为 0.8 m。
- `SHARED` 只表示两个 0.8 m 邻域候选集合有交集，并不区分“只有共享节点”和“共享节点加各自独立节点”，也不具备 identity 语义。
- 所以“当前邻域图未观察到分离”成立；“物理响应必然融合/身份不可分”不成立。

## 6. 证据分量不能合并成单一结论

| frame | target | image rank | correct max | correct sum | correct mean | thread len | zero max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F483 | P02 | 9 | 114 | 116 | 15 | 7 | 86 |
| F487 | P02 | 18 | 198 | 203 | 17 | 7 | 134 |
| F490 | P01 | 13 | 255 | 269 | 15 | 2 | 281 |
| F490 | P04 | 12 | 105 | 120 | 3 | 23 | 116 |
| F490 | P03 | 12 | 105 | 120 | 3 | 23 | 116 |
| F494 | P04 | 1 | 206 | 220 | 2 | 23 | 221 |
| F494 | P03 | 1 | 206 | 220 | 2 | 23 | 221 |

- max/sum 只使用 `source_C2 × geometry`，不含 destination C2；不是 posterior。
- sum 显著混入候选密度；max 也受更多前驱机会和最近几何影响。
- mean 弱化密度影响，但 CORRECT-vs-ZERO reference 配对 83.3% 持平。
- 离线评价会为每个分量重新选择 0.8 m 内最优节点，所以 rank delta 是邻域重排序诊断，不是同一候选状态的运行时更新。

## 7. 复现与 schema 缺口

- 原 runtime manifest 没有冻结动态脚本自身（当前 SHA256 `08FC073B2F5205BBD4D40DA0DD7872F006EC4E2965EABAE1D2FA50BE28E5B529`）或运行前协议（当前 `A89B20DCD2BF077FAAB8EB6BFE70DF33C12CEBC1350891D48F718C170F161B3A`）。
- fixed-offset source（当前 `914417E3D08758E0BAFEA2955FD11EE368E70043D4D2731C59FB8DC6B63077A3`）和 B0R comparability（当前 `4D0B454A7131212221AD3911B8A9652B93BF0BECDC35F1B9E54B19B4F5735D13`）未进入预运行 `EXPECTED_HASHES`。
- 当前 R02 lag1 comparability 为 22/22 True，因此当前结果未受影响；但动态图代码没有 assert/filter `pair_comparable`，未来扩展会有静默风险。
- incoming/outgoing 同名 `best_support_normalized_error` merge 后形成 `_x/_y`，SHUFFLED 又保留无后缀列；消费 `dynamic_candidate_state.csv` 时必须按 condition 明确读取，不能把无后缀列当通用字段。

## 8. 审阅后允许的总括

当前实验建立了透明的 GT-blind 候选图，并证明真实序列有持续响应且 gross 错位会破坏它；但由于 P0 lag1 位移仅约 0.34 个设计容差，CORRECT 与 ZERO 在候选排序、边、线程和 shared 状态上高度相同，尚未显示稳定的 P0-specific 时序信息增益。P01 有局部恢复，P02 高度异质，P03/P04 持续共享且当前 0.8 m 邻域定义本身不能检验身份分离。
