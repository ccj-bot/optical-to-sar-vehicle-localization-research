# TERG-v0 图像—计算—语义一致性复核

## 最终决策

`TERG_V0_NEEDS_MINIMAL_REPRESENTATION_REPAIR_BEFORE_CONFIRMATION`

TERG 的大方向与真实 SAR 时序结构基本一致：光学 corridor 能限定解释空间，SAR q95/P0 时序结构能把静态 many-to-many 候选组织成完整、部分、孤立、共享和形变等不同解释。R01ZF F0–F15 的完整 response 在全部中间帧中视觉连续，证明 lifecycle/corridor/P0 temporal explanation 这条主线有价值。

但当前实现把边不确定性、关系集合和物理 region/条件化 node 重新压成 Boolean connectivity 或单一类别，已经产生可见的表示—现实偏差。进入新 confirmation 前应设计并实现最小 `TERG_D0R`；本任务只给出设计，不修改冻结机制，也没有访问 R04ZF/held-out confirmation。

## 范围与证据顺序

- Phase A 只读审计；TERG-D0 mechanism 未修改。
- 先复核 committed visual packs 和 contact sheet，再生成 development-only diagnostics，最后才使用 magenta offline reference 做 post-reference diagnosis。
- 审阅了 `07/08/09/10/11/15/16`、`TERG_D0_TEMPORAL_REVIEW_CONTACT_SHEET.jpg`、10 个 bridge-critical packs、4 个 exact-1.0 packs、2 个 relation-set packs、5 个 topology packs，以及 R01ZF F0–F15 全中间帧 pack。
- audit family 只用于描述，不是新 runtime threshold；没有按 reference 搜索 overlap threshold 或 timing offset。

## 主要结果

### 1. Boolean edge 与 bridge criticality — confirmed mechanism representation defect

- 52,460 条候选边中有 3,702 条 Boolean supported edge。
- `soft_intersection_px` 是 bilinear warp 后的分数 overlap mass，不是整数像素数。精确 `1.0` 只有 4 条，实际只有两组物理 region pair，分别因两个 track-conditioned graph 重复出现。
- 去掉精确 `1.0` 边只使总 component 数从 3,414 变为 3,422；且这 4 条边都不是当前长 component 的 bridge。因此“精确 1 pixel 是全局主因”被否定。
- 更广泛的低证据/非局部主导边才是问题：3,435 个唯一 supported edge 在至少一个 segment-component 中是 bridge；39 个唯一 audit-weak edge 是 bridge。视觉上，多条边只是小 response 与巨大、分叉或长条 destination q95 region 的局部接触，却能把 20/27、27/26、21/26 等大块 frame support 合成一个 component。
- 这不等于这些边必然错误。它们常表达“局部 continuation 仍可能”，但不能被 Boolean graph 自动升级为“整个两侧 component 无条件同属一个解释”。

结论：需要把 edge evidence 保留在 graph 内部，并输出 core/possible component family 与 bridge dependency；不应把 `1.0` 换成另一个经 reference 调出的硬阈值。

### 2. Physical SAR region 与 conditioned node — confirmed semantic defect

- conditioned graph node：4,328。
- 唯一 physical `(run, frame, region_id)`：3,056。
- 1,192 个 physical region 被复制到多个 optical track；这些 region 对应 2,464 个 conditioned node；单个 physical region 最多有 4 个 conditioned copy。
- 图包 06/07 与 08/09 显示同一物理 source/destination region pair 因不同 `track_id` 形成两条 graph edge。

因此必须明确两层：

1. `PhysicalSarRegion(run, frame, region_id)`：真实 q95 response region；
2. `ConditionedExplanation(track, segment, physical_region_id)`：该 physical region 被某 optical corridor 接纳的 incidence。

现文档中“shared response 是同一个 graph node 而不是 duplicated node”的说法与实现不符；这是语义/数据模型缺陷，不是身份证据。

### 3. Relative order aggregate — confirmed information suppression

共有 85 个 order profile，其中 78 个当前被压成 `SHARED_RESPONSE_ORDER_UNDEFINED`。这 78 个 profile 都确实至少出现一个 physical shared region，因此 local SAR ambiguity 不是虚构的；但它们也全部保留了被 aggregate label 丢弃的其他关系：

- 27：`{RIGHT, OVERLAP, SHARED}`，属于局部 shared 但仍有单向关系支持；
- 51：包含 `{LEFT, RIGHT, SHARED}`，部分还包含 `OVERLAP`，属于竞争方向集合；
- 0：只有 `{SHARED}`。

R02ZF F481–F485 的 partial-direction pack 中，前四帧几乎全是 RIGHT，只有最后一帧出现一个 physical shared region；当前整段仍被标成 undefined。competing-direction pack 中，RIGHT 占主导，最后两帧出现 shared，末帧另有少量 LEFT。两者都证明 `POSSIBLE_RELATION_SET + per-frame/support extent` 比 whole-set categorical label 更忠实。

这里不能把“真实 ambiguity”和“aggregation suppression”分成互斥人数：当前 78/78 同时有真实局部 shared evidence，也有 78/78 的其他 relation information 被抑制。

### 4. “87/88 potential disambiguation” — confirmed terminology overclaim

- 88/88 explanation set 的全部 static node 都仍在某个 connected component 中。
- 实际删除 component：0；实际删除 node：0。
- 87/88 仅表示一个 set 内同时存在 multi-frame 与 isolated component，即 temporal stratification 可用。
- post-reference 有 79 个 set 恰好一个 `LIKELY_SUPPORTED_EXPLORATORY` component，但这属于 evaluated concentration，并受稀疏 reference/assignment interface 限制。

应改称：

- pre-reference：`TEMPORAL_STRATIFICATION_AVAILABLE_IN_87_OF_88_EXPLANATION_SETS`；
- 只在假设保留规则下：`COUNTERFACTUAL_CONTRACTION`；
- post-reference：`EVALUATED_EXPLANATION_CONCENTRATION`。

这部分主要是文档命名问题；当前 runtime 没有真实 pruning，不能继续无限定地写“87/88 contraction”。

### 5. Complete/partial 与 grounding — direction supported, wording needs restraint

R01ZF F0–F15：

- `TERGXC_1FD4CF2856175478AA05` 在 16 帧上从约 `-30.45°` 平滑移动到 `-16.91°`，逐帧 SAR 图像连续；complete continuity 在此案例中得到现实支持。
- `TERGXC_A97D2FC78FCD287ADEEE` 是 F0–F4、约 `-45°` 的独立 response，视觉上不是 selected response 的 q95 暂时断裂；complete/partial 在该案例中可区分。
- selected component 的 4 个 reference frames 都受支持，且未标注中间帧视觉连续，因此其 temporal continuity 证据比当前稀疏 `LIKELY` grounding interface 更强；但不能升级为 true identity。
- partial component 在 F0 的 physical `R0002` 实际是另一个 SAR target 的 offline Q95 reference region。它对 PERSON002 的 conditioned assignment 是零支持，不等于该物理 response 被 SAR 图像“否定”。旧文档中的 “rejected alternative” 过强。

本 focus case 没有确认 `Q95_FRAGMENTATION_FALSE_ISOLATION`；该怀疑在此被否定。其他 segments 是否存在这种现象仍未穷尽证明。

### 6. Split/merge — confirmed unstable categorical semantics

结构敏感性：

| variant | split | merge | split+merge |
|---|---:|---:|---:|
| all positive support | 222 | 250 | 13 |
| remove exact-1 mass | 218 | 246 | 13 |
| remove bottom 1% IoU | 198 | 215 | 12 |
| remove non-dominant bottom decile | 76 | 64 | 2 |

精确 `1.0` 不是主要驱动；更宽的 weak/non-dominant family 会显著改变 topology。高-IoU “clear split/merge” 图中，主体 response 仍连续，只是轮廓凸起出现/消失，同时被 residual interface 标成 deformation。最低证据案例 soft mass `1.289`、IoU `0.00034`、source retention 近零，却仍进入 split-like topology。

结论：`P0_SPLIT_LIKE/P0_MERGE_LIKE` 可保留为 uncertain topology hypothesis，但不应作为稳定、单一的 event primitive。boundary/truncation split/merge 在本 development sample 中没有符合显式 flag 的案例，保持 unresolved。

### 7. Timing — unverified placeholder plus implementation gap

- `250 ms` 可追溯到 P1E exploratory commit `edd7c1ba91577f18fa54877f82ee92eb779aab33` 中预先列出的 `0/100/250/500 ms` sensitivity windows，以及文档字段 `sync_uncertainty_ms=250`。
- 未找到 measured synchronization uncertainty、offset distribution 或 calibration provenance。
- TERG event relation 实际只比较原始 SAR frame support interval；`timing_uncertainty_ms=250` 只是记录字段，未参与 interval widening。

故分类为 `UNVERIFIED_TIMING_MARGIN`。冻结 specification 已承认 widening 未实现，但 250 本身仍不能被解释为已知 uncertainty distribution。

## A–O 直接回答

### A. 大方向是否与真实 SAR 时序一致？

是，作为“保留多个 SAR temporal explanations 并进行结构化”的方向成立；不支持把它解释为 tracker、identity assignment 或 final localization。

### B. Boolean edge 会否产生视觉不合理 bridge？

会。已确认多条局部接触/region-growth edge 成为两个长 frame-support 子图的唯一桥；但不是所有弱边都视觉错误。

### C. `soft_intersection_px >= 1` 在真实图中代表什么？

代表 bilinear-warped source mask 与 destination q95 mask 的分数 overlap mass 达到 1.0；可以是多个 fractional pixels 的和，不等于“一个可靠物理像素”。精确 1.0 图中是极小接触。

### D. 是否需要 edge uncertainty representation？

需要。边应保留 evidence vector、局部 dominance、deformation/boundary 状态和 bridge dependency，并形成 core/possible component family。

### E. 78/85 shared/order-undefined 中多少是真实 ambiguity，多少是 suppression？

两者重叠而非互斥：78/78 有真实 local physical sharing；同时 78/78 都有其他 relation 被单标签抑制，其中 27 是 partial-direction，51 是 competing-direction，0 是 pure-shared-only。

### F. relation-set 是否更忠实？

是。它不选择 best component pair，也不做 weighted vote，却能保留 `{RIGHT,OVERLAP,SHARED}` 或 `{LEFT,RIGHT,SHARED}` 及其 frame/support extent。

### G. 87/88 应准确称为什么？

`TEMPORAL_STRATIFICATION_AVAILABLE_IN_87_OF_88_EXPLANATION_SETS`；只有假设性过滤才叫 `COUNTERFACTUAL_CONTRACTION`。

### H. complete/partial 在真实图中可否区分？

在重点 R01ZF F0–F15 案例中可以，且 partial 是另一条真实局部 response，不是 selected response 的明显断裂；不可把 partial 自动称为错误或被拒绝。

### I. split/merge 是否稳定？

不稳定，受 weak/non-dominant edge 与 q95 contour deformation 强烈影响；应降为 uncertain topology hypothesis。清洁的 boundary case 未建立。

### J. ±250 ms provenance？

来自早期 exploratory sensitivity/window convention，未找到测量或标定依据；是 `UNVERIFIED_TIMING_MARGIN`。

### K. timing uncertainty 如何表示？

用 `SET_OF_TIMING_HYPOTHESES`：nominal grid relation、已知 sampling quantization、未标定 offset family、在明确 uncertainty family 下的 interval-widened relation set。不得按 reference performance 选 offset。

### L. physical region 与 conditioned node 是否混淆？

是，confirmed。实现按 track 复制 node，物理共享与 graph-node duplication 必须分层表达。

### M. 哪些主要是文档命名问题？

“87/88 contraction”、把 partial 叫 rejected、把 `LIKELY` 当 identity、把 250 ms 写成已知 uncertainty、把 physical sharing 描述为未复制的同一 graph node。

### N. 哪些是真正 representation defect？

Boolean edge 直接决定 global connectivity；whole-set order label 丢 relation set/extent；physical/conditioned node 未分层；split/merge 单类别过度解释形态；timing descriptor 未生成 set-valued relation。

### O. 哪些怀疑被视觉检查否定？

精确 `1.0` 边不是全局 component 问题的主要来源；重点 complete component 没有发生中途视觉跳转；重点 partial component 不是 selected response 的 q95 false isolation；TERG 总体 temporal-explanation 方向没有被反例推翻。

## Minimal D0R design（只设计，不实现）

1. **两层 node model**：以 `PhysicalSarRegion` 为物理节点；用 `ConditionedExplanationIncidence` 连接 optical track/corridor 与物理节点。物理 P0 edge 只计算一次，conditioned graph 引用它而不复制物理事实。
2. **edge evidence record**：保存 overlap mass、双向 explained fraction、soft IoU、source/destination local dominance、deformation、boundary/truncation、timing/model availability。不要先压成单 Boolean。
3. **connectivity family**：输出 `core_graph`、`possible_graph`、`bridge_dependency` 和由 optional edge 产生的 component family。`CORE/WEAK/UNCERTAIN/DEFORMATION/UNSUPPORTED` 是语义层，不是一个加权分数；当前 quantile family 仅用于 audit，不直接冻结成 runtime threshold。
4. **relation-set algebra**：每个 profile 输出 `possible_relation_set`、每种 relation 的 frame extent、component-pair support extent、physical shared frames、definite/ambiguous frames。禁止 best pair 和 weighted vote。
5. **topology hypothesis**：split/merge 绑定到 physical region 层，并同时报告 deformation 与 edge-sensitivity；不再把它们当唯一 event state。
6. **terminology**：stratification、counterfactual contraction、evaluated concentration 分开；不暗示 runtime pruning。
7. **timing hypotheses**：relation 由 interval family计算并保持 set-valued；unknown offset 保持 unknown，直到独立 calibration 提供可审计范围。

这些修复的唯一目的，是更准确地表达“哪些 SAR temporal explanations 仍然合理”，不是提高 reference accuracy。

## Stop boundary

Phase A 审计完成，D0R 最小设计完成。未修改 TERG-D0、未执行 TERG-v1、未访问或运行新的 held-out confirmation。
