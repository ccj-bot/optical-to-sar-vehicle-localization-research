# PERSON P1E Observation Interface 当前状态与语义一致性审阅

- 审阅日期：2026-08-28
- 审阅性质：代码、协议、物化产物与报告的只读语义审计
- 当前研究状态：`P0_FROZEN_PASS / P1E_EXPLORATORY_OBSERVATION_INTERFACES_ESTABLISHED / RUNTIME_IDENTITY_NOT_ESTABLISHED / P2_NOT_ESTABLISHED`
- 本轮改动：仅新增本文档并更新研究日志；未运行新实验，未修改 P0、B0R、C0–C3、候选、光学壳、response-region 或 topology 生成代码

## 0. 审阅结论

当前代码总体守住了核心运行时边界：SAR 响应场、GT-blind 候选、光学粗方位壳、SAR response-region 和最新像素级 shell–region topology 的生成均没有使用人工 `physical_target_id`、manual SAR reference、人工框中心或 SAR range GT。最新 topology 版本还显式先物化全部 `pre_reference` 产物，再读取 reference 做离线解释。

但当前仓库不是一个已经完成的“PERSON 定位接口”，而是由若干职责不同的观测接口组成：

1. 光学 raw fragment 提供不稳定的、近似运行时可用的方位分支；
2. optical shell 提供 time/azimuth 搜索支持，不提供 SAR range 或最终位置；
3. SAR response-region 表达冻结 C2 响应场中相对高响应的空间支持，不是 PERSON 框；
4. shell–region topology 表达搜索分支与响应区域之间的几何歧义，不是身份关联；
5. manual SAR reference 与目标 ID 只在上述对象完整生成后用于离线评价。

目前没有发现“GT 进入响应/壳/拓扑生成”的实现性泄漏。主要风险来自三类语义混用：

- **历史结论未退役**：旧单帧结论和 temporal gate 仍保留在原文件中，但已被后续动态证据与观测模型工作替代；
- **GT-blind 不等于 runtime**：全 run posthoc stitching、居中时间窗和带离线 provenance 的审计表虽然不使用 PERSON GT，仍不等于因果在线输入；
- **结构状态不等于 PERSON 状态**：region、local degree、component topology 可 GT-blind 计算，但 `PEAK_MISSING_REGION_PRESENT`、PERSON `SHARED_REGION`、P01–P04 归因仍依赖 manual reference。

因此，当前最准确的总体表述是：

> 已建立一组 GT-blind、运行时输入边界基本合规的 SAR/光学观测对象，以及清楚的离线评价层；尚未建立稳定 runtime optical identity、PERSON-specific SAR region 判别、跨模态身份关联或最终定位输出。

## 1. 审阅范围与权威顺序

### 1.1 已审阅对象

- P1E 单帧 C0–C3 与固定支持区 `S(x)`；
- candidate semantic split；
- dynamic evidence temporal v1；
- observation model diagnostic v1；
- matched optical-shell information gain v1；
- runtime-track / response-region minimal v1；
- shell uncertainty / region topology v1；
- 对应协议、CSV/JSON schema、HTML 报告、验证器与任务 README；
- `old_work` 仅检查防护语句是否存在，未读取或依赖其中内容。

### 1.2 当前解释的权威顺序

出现冲突时，按以下顺序解释：

1. 当前实际生成代码、物化 schema、执行 ledger 和独立验证器；
2. 同一实验的 pre-run amendment，高于被其明确修正的主协议段落；
3. 最新 `shell_uncertainty_region_topology_v1` 协议与报告；
4. 较早 observation、matched-shell、runtime-track、dynamic-evidence 报告；
5. 更早的 `P1E_EXPLORATORY_CONCLUSION.md` 与 candidate temporal gate 仅作历史记录。

### 1.3 已确认的 supersession 关系

| 历史表述 | 当前状态 | 权威口径 |
| --- | --- | --- |
| `P1E_EXPLORATORY_CONCLUSION.md` 写“时序未启动”“不进入时序” | 已被后续 lag1 dynamic evidence 实验事实上替代 | 该文件只描述当时的单帧开发判断，不是当前研究状态 |
| candidate split 的 `SEMANTIC_SPLIT_COMPLETE_TEMPORAL_GATE_NOT_OPEN` | 后续明确取消单帧资格 gate | gate 只保留为历史产物，不再控制研究问题能否被测试 |
| runtime-track 主协议把 `optical_person_id` 称为 runtime continuity hypothesis | 运行前 provenance 审计发现其包含全 run stitching 和短缺口插值 | `00A_PRE_RUN_OPTICAL_IDENTITY_PROVENANCE_AMENDMENT.md` 优先：raw fragment 是主接口，`optical_person_id` 只是 GT-blind offline continuity proxy |
| `response_region_track_shell_intersection.csv` 使用 region 角跨度与 shell 相交 | 最新 topology 已改为真实像素相交 | 后续空间拓扑解释必须以 `gt_blind_shell_region_pixel_edges_pre_reference.csv` 为准 |
| “没有 `MULTIPLE_SHELLS_ONE_REGION` component” | 完整连通分量常扩展成 multi-shell/multi-region | 判断局部共享必须同时查看 region degree，不能只看 component 名称 |

## 2. “runtime”在本文中的三个层级

为避免继续把不同概念都称为 runtime，本文固定区分：

| 层级 | 定义 | 当前达到情况 |
| --- | --- | --- |
| `RUNTIME_LEGAL_INPUTS` | 生成时不使用 manual SAR reference、人工 `physical_target_id`、SAR range GT 或人工选轨 | C2/S(x)、raw-fragment shell、response-region、像素 topology 基本达到 |
| `CAUSAL_RUNTIME_AVAILABLE` | 所需输入在该时刻或允许的固定延迟内可获得，不读取未来观测或全 run 后处理 | same-frame、past-only shell 较接近；centered window 和 stitched proxy 不满足零延迟因果语义 |
| `DEPLOYED_RUNTIME_INTERFACE` | 已有稳定在线模块、输入合同、失败状态和跨 run 验证 | 当前尚未达到 |

因此，“GT-blind”“pre-reference”“runtime-compatible”只能说明部分边界，不应自动写成“已建立在线系统”。

## 3. 五类核心对象的规范定义

### 3.1 Optical fragment

#### 主对象：`raw_track_fragment_id`

- 来源：自动光学检测、BoT-SORT tracklet 或单帧匿名 fragment；只取 `box_source=DETECTED`。
- 几何输入：检测框横向范围、检测时间、固定 optical→SAR 方位映射。
- 当前角色：最接近 `RUNTIME_LEGAL_INPUTS` 的 optical identity hypothesis。
- 重要限制：它可能很短、碎片化、匿名或同一物理目标被拆成多个 fragment；它不是稳定 PERSON identity。

#### 次级对象：`optical_person_id`

- 来源：读取完整 run 后进行 fragment stitching、全局 assignment、统一重编号，并允许短缺口插值。
- 当前角色：`GT_BLIND_OFFLINE_CONTINUITY_PROXY`，用于估计未来更好 runtime continuity 可能带来的工程上限。
- 禁止角色：不得称为当前 runtime track identity，不得作为 PERSON identity truth，不得与人工 `physical_target_id` 等同。

#### 已发现的表级混合

最新 `pre_reference` shell 表中保留了 `source_parent_stitched_ids`、`source_ambiguous_stitch_count_max`、`source_accepted_parent_fraction` 等 provenance 字段。这些字段没有参与 shell 几何生成，但它们是 posthoc 审计元数据，不是运行时输入。因此：

- shell 几何本身可按 raw fragment 解释；
- 整张审计表不能不经字段白名单直接当作 runtime message schema。

### 3.2 Optical shell

Optical shell 是由一个或多个 optical detection box 经固定方位映射、固定 guard、预定义时间策略和 SAR fan clipping 形成的**方位区间集合**。

运行时允许输入：

- optical raw fragment 的检测框和时间；
- 固定 optical→SAR azimuth mapping；
- 固定 guard 或预先冻结的不确定度规则；
- SAR 扇面几何、common-FoV 和单帧有效区。

它只输出：

- azimuth interval；
- 有效角宽、面积、fan/common-FoV clipping；
- latency、fragment availability 与 uncertainty provenance。

它不输出：

- SAR range；
- SAR 响应中心；
- PERSON 框；
- “正确 optical track”；
- 跨模态 identity。

术语注意：

- matched-shell 实验中的 `TRUE` 只表示“由实际 optical observations 生成的壳”，不是 ground-truth SAR 位置，也不保证 reference 一定在壳内；
- `SAME_FRAME` 只表示名义 optical timestamp 与查询时间相同，严格物理同步尚未验证；
- `CENTERED_*` 可以使用未来观测，只能称 buffered/offline uncertainty diagnostic，不能称零延迟 causal runtime。

### 3.3 SAR response-region

当前 response-region 的实际生成链为：

```text
SAR pseudocolor image
  -> frozen C2 image operator
  -> S(x) = fixed_support_mean_v2(C2), support radius 0.30 m
  -> frame-valid percentile field (4096-bin CDF)
  -> q90 / q95 / q97.5 superlevel mask
  -> 8-connected components
```

因此 response-region：

- 是实际候选场 `S(x)` 的超水平连通区域，不是未经支持盘平均的基础 C2；
- 使用相对帧内 percentile，不是绝对强度、PERSON 概率或校准置信度；
- 可以记录面积、range/azimuth 跨度、主次轴、elongation、边界接触和支持截断；
- `centroid_*_shape_descriptor` 只是形状描述量，不是最终定位中心；
- region ID 只在当前帧与 percentile layer 内有效，不具有跨帧 identity；
- 不是 PERSON box、稳定散射中心或人体固有 RCS 支持区。

`PEAK_MISSING_REGION_PRESENT` 等标签不是 region 生成结果本身，而是 region 完整生成后，使用 manual reference 和旧离散候选做出的离线表示解释。

### 3.4 Shell–region topology

最新权威拓扑由真实像素相交构造：若 region 的像素落入 shell 的有效方位区间，则形成一条 edge，并记录交叠像素数、面积、region/shell 覆盖比例及交叠 range/azimuth 跨度。

GT-blind 可直接得到：

- shell degree：一个 shell 相交多少 regions；
- region degree：一个 region 被多少 shells 覆盖；
- `ONE_SHELL_ONE_REGION`、`ONE_SHELL_MULTIPLE_REGIONS`、`MULTIPLE_SHELLS_ONE_REGION`、`MULTIPLE_SHELLS_MULTIPLE_REGIONS` 等二部连通分量状态；
- shell/region 无边、边界、截断、common-FoV、display 和候选采样 P0 条件。

这些量表达的是**搜索分支与图像响应支持之间的结构化歧义**。它们不执行：

- PERSON identity assignment；
- “哪个 shell 属于哪个人”的判定；
- SAR range 或框生成；
- response-region 的 PERSON 语义分类。

必须同时保留 local degree 与 component topology。一个 region 可以局部被多个 shells 覆盖，但因为这些 shell 还连接其它 regions，完整 component 会被标成 `MULTIPLE_SHELLS_MULTIPLE_REGIONS`；不能据此否定局部 `multiple shells -> one region` 现象。

### 3.5 Physical reference / manual SAR reference

当前仓库中不应继续裸用 `physical reference` 这一称呼，因为它容易暗示比实际标注更强的物理真值。当前实际有两个离线对象：

1. **manual native SAR geometric reference**：人工 SAR 框、框几何中心、宽高、range/azimuth 和 support 状态；
2. **offline target grouping label**：`target_id` / `instance_id` / 人工 `physical_target_id`，用于按目标汇总或解释病例。

规范口径：

- manual reference 是人工框几何参考，不是物理散射中心、RCS 中心或运行时预测；
- reference center 到 peak/region 的距离是相对人工框中心的算子偏移，不是空间分辨率或散射中心误差的直接测量；
- `physical_target_id` 是人工身份标签，不是 runtime optical track identity；
- P01/P02/P03/P04 只能在所有 shell、region、edge 和 topology 生成后用于离线解释；
- offline one-to-one shell/reference assignment 是评价工具，不是运行时 identity assignment。

## 4. 主要物化产物的 runtime/offline 分类

| 产物 | 分类 | 必须如何读取 |
| --- | --- | --- |
| `gt_blind_candidates_all_processed_frames.csv` | GT-blind candidate artifact，但不是全 398 帧 runtime stream | 候选坐标生成不使用 annotation；R01/R03/R04 的审计帧选择部分依赖 manual frame presence，且文件仅覆盖 126/398 帧。无行不得解释为零候选 |
| `observation_condition_table.csv` | 混合审计表 | 同表含 `SAR_ONLY_C2_CANDIDATE`、`PERSON_REFERENCE` 和 controls；runtime 使用必须按 `entity_kind` 与字段白名单过滤，不能整表直接输入 |
| matched-shell `shell_definition_table.csv` | pre-reference shell/control 表 | `TRUE`/`MATCHED_NULL` 均先生成；它是 all-person union prior 实验，不是 track identity 接口 |
| `track_shell_definition_table.csv` | 混合接口审计表 | 同时含 RAW 和 STITCHED 两种 interface，并携带 posthoc provenance；必须按 `interface_kind`、时间窗和字段白名单读取 |
| `response_region_table_pre_reference.csv` + masks | GT-blind SAR image-domain product | 覆盖 398/398 帧；没有 PERSON 标签；允许作为 response-region 的权威基础产物 |
| `optical_shell_uncertainty_decomposition_pre_reference.csv` | shell 几何 pre-reference 产品 + 离线 provenance 元数据 | 几何不使用 SAR reference；`source_parent_stitched_*` 等列只能用于审计，不能作为 runtime 特征 |
| `gt_blind_shell_region_pixel_edges_pre_reference.csv` | GT-blind 最新权威 edge | 使用真实像素相交；优先于旧角跨度 intersection 表 |
| `gt_blind_*nodes*` / `gt_blind_bipartite_components_pre_reference.csv` | GT-blind topology product | local degree/component 是歧义结构，不是 PERSON identity 或定位结果 |
| `offline_reference_*`、`manual_reference_*`、`offline_one_to_one_*` | 仅离线评价 | 可以计算 retention、rank、shared、病例解释；不得反向参与 shell、region、edge 或分支选择 |

额外说明：`pre_reference` 的准确含义是“在该物化阶段尚未读取 manual SAR reference”。它不保证表内每个 provenance 字段都可在线获得，也不等于严格 sealed-data process isolation。当前 explorer 容器本身含 annotations，代码在生成前做字段净化；因此允许说“annotation content 未参与计算”，不允许说“annotation data 从未被加载”。

## A. 已建立能力

### A1. SAR-only 位置响应场

- C0–C3 可在有效扇面任意位置生成，不使用 PERSON 框中心、框宽高、`physical_target_id` 或光学轨迹。
- 当前主分析场是冻结 C2 经固定 0.30 m 支持盘平均得到的 `S(x)`。
- 固定物理尺度来自预声明的 PERSON class support hypotheses 与扇面几何换算，不来自逐框宽高。

### A2. 候选存在性与唯一性已分开

- GT-blind local-max/NMS candidates 先在整帧响应场生成，再用 reference 做 Recall@K、rank、距离和 shared 评价。
- 旧 `hard background` 已正确收窄为 local competing-response/control pool。
- peak offset 已正确收窄为算子相对人工框几何中心的偏移。

### A3. 单帧可观察域与 P0 transport 域已分开

- `SAR_SINGLE_FRAME_OBSERVABLE` 不再与 `P0_TRANSPORT_CORE/EXTENDED/UNAVAILABLE` 混为一个 mask。
- P0 不可比较不自动等于单帧没有 SAR 响应。
- P0 仍是背景估计的公共表观输运与设计误差条件，不是平台真实轨迹。

### A4. 光学粗方位先验具备受控搜索信息

- matched-cost TRUE/NULL 实验支持“实际光学粗方位覆盖比等搜索成本错误壳更能保留 reference 邻近 C2 响应”。
- 该优势主要来自正确方位覆盖和候选负担压缩，不是壳内 C2 变得更 PERSON-specific。
- 光学仍未指定 SAR range、响应中心或最终框。

### A5. Raw-fragment track-shell 接口已建立为运行时近似

- 全部自动 detected raw fragments 可独立生成 shell，不按 accepted tier、manual reference 或人工 ID 选择分支。
- same-frame、past-only、buffered 和 centered 时间条件可分别量化 availability、shell width、retention 和 burden。
- `optical_person_id` 的 posthoc 性质已由 amendment 正式纠正。

### A6. Response-region 比离散 peak 更忠实地表达 response presence

- q90/q95/q97.5 regions 覆盖全部 398 帧。
- F482/F490 已从“0.8 m 内没有离散候选”修正为 `PEAK_MISSING_REGION_PRESENT`，说明 candidate missing 不等于 continuous response missing。
- extended/ridge、boundary/truncated 等 shape/observation descriptors 可在不使用 GT 的情况下生成。

### A7. GT-blind shell–region 歧义拓扑已建立

- 最新 edge 使用真实像素相交，不再依赖粗角包围盒相交。
- local shell/region degree 和二部 component topology 可直接描述 one-to-one、one-to-many、many-to-one 和 many-to-many 搜索结构。
- 执行 ledger 和 manifest 证明 shell/region/edge/topology 先于 manual reference 物化；独立验证器检查 runtime 表无 `physical_target_id`、`target_id` 和 reference 坐标列。

## B. 未解决问题

### B1. Runtime optical identity 尚未建立

- raw fragments 在 R02 中严重碎片化，可能一人多 fragment、匿名 fragment 或帧间中断；
- stitched accepted 只给出 GT-blind offline continuity 上限；
- 当前没有经过部署验证的稳定 causal track ID。

### B2. 严格同步和 mapping uncertainty 尚未校准

- `SAME_FRAME` 只是名义配对；
- fixed mapping 与 ±6° guard 的误差来源没有被独立校准成可部署不确定度；
- centered window 的 retention 增益与未来观测、时间 union 和 fragment availability 同时变化。

### B3. SAR response-region 尚未建立 PERSON-specific 唯一性

- q95 region 对 PERSON reference 的覆盖高，但 local competing response 覆盖同样较高；
- R02 P03/P04 及部分 P01/P02 继续共享同一 region；
- region presence 解决的是“响应是否被 peak 表示漏掉”，不是“这个 region 是否唯一属于 PERSON”。

### B4. Shell–region topology 仍是歧义描述，不是关联解

- 多数 R02 q95 regions 被多个 shells 覆盖；
- one-shell/multi-region 与 multi-shell/multi-region 都很常见；
- 当前没有合法依据从拓扑图中选择唯一 shell、唯一 region 或 PERSON identity。

### B5. Candidate artifact 不是完整 runtime stream

- 旧 candidate artifact 只覆盖 126/398 帧；
- `generated_without_annotation=True` 说明候选坐标生成不使用 annotation，不说明审计帧集合是全流 GT-independent sampling；
- `accepted_peak_count` 中的 accepted 只是通过冻结 local-max/NMS 的候选，不是人工接受或 PERSON-positive。

### B6. Runtime 与 offline 数据仍存在表级共置

- `observation_condition_table.csv` 同时包含 candidates、references 和 controls；
- shell 表保留 offline stitching provenance；
- 当前靠 `entity_kind`、`interface_kind` 和使用约定维持边界，尚未形成独立的 runtime-only schema contract。

### B7. 严格 sealed-data process isolation 尚未建立

- explorer 容器含 annotation 字段，部分混合 CSV 同时含 reference 与 runtime-like rows；
- 当前代码通过先过滤/净化保证 reference content 不参与计算，但不能声称 GT 文件从未加载；
- 所有 R01–R04 都是已暴露开发语料，当前结论不具备盲验证资格。

## C. 当前假设

以下均是工作假设，不是已证明的物理事实：

1. **条件性图像域响应假设**：C2/S(x) 捕捉的是目标、场景、成像与显示链共同形成的相对图像结构，不是人体固有 RCS。
2. **粗方位先验假设**：固定 optical→SAR mapping、时间不确定度与 guard 可以形成有用 azimuth support，但不提供 range 或精确点。
3. **Raw fragment 可运行时近似假设**：自动 detection/tracklet replay 能代表未来 runtime optical branch 的最低能力，但当前碎片化不代表未来最终 tracker 性能。
4. **相对区域表示假设**：q90/q95/q97.5 regions 可表达当前帧响应支持的层级与形状，但其阈值是帧内相对量，不是跨帧绝对强度标尺。
5. **拓扑歧义假设**：shell/region local degree 与 component topology 能描述当前搜索结构复杂度，但不包含 PERSON identity 语义。
6. **显示条件假设**：display JS/shift、边界和 support truncation 会改变可观察性；这些代理不能直接解释为目标真实回波增强或减弱。
7. **P0 条件假设**：冻结 P0 可提供公共表观输运及局部设计误差条件；它不是真实平台轨迹，也不能从 PERSON reference 反向校准。
8. **开发语料假设**：现有四个 run 只用于机制发现、失败诊断和接口审计；真正效果确认需要公式与语义冻结后的新采集盲验证。

## D. 不允许继续使用的解释

以下表述应停止使用，或必须加上右侧限定：

| 不允许的解释 | 允许的准确表述 |
| --- | --- |
| raw fragment 就是一个真实 PERSON identity | raw fragment 是自动 optical tracklet/fragment hypothesis |
| `optical_person_id` 是当前 runtime track ID | 它是全 run GT-blind offline continuity proxy |
| `TRUE shell` 是 SAR 真值壳 | 它是由实际 optical observations 生成、与 matched null 对照的粗方位壳 |
| same-frame 等于严格物理同步 | same-frame 只是当前名义时间索引/时间戳匹配条件 |
| centered shell 是 causal online 输出 | centered window 可能使用未来观测，只能称 buffered/offline diagnostic |
| optical shell 给出了 PERSON 的 SAR 位置 | shell 只限定 azimuth search support，不指定 range 或中心 |
| q95 region 是 PERSON box | q95 region 是相对高 `S(x)` 的连通支持区 |
| region centroid 是最终定位点 | centroid 只是 region shape descriptor |
| q95 表示 95% PERSON 置信度 | q95 是当前有效域的帧内响应 percentile |
| region presence 等于 PERSON detection | region 也可能覆盖 local competing response；PERSON 语义尚未建立 |
| `SHARED_REGION` 证明物理散射融合 | 它只表示同一图像域 region 邻近多个离线 references |
| multi-shell/one-region component 不存在，所以没有共享 | 必须查看 region local degree；component 可能扩展为 multi-shell/multi-region |
| topology 已经完成跨模态 identity association | topology 只表达几何相交和搜索歧义，不选择 identity |
| offline best-track / one-to-one assignment 是运行时能力 | 它们只是在全部分支生成后的离线评价上限 |
| reference center 是真实散射中心 | 它是人工 SAR 框几何中心 |
| peak-to-reference offset 是 SAR 空间分辨率 | 它是当前算子局部高分位置相对人工框中心的偏移 |
| `accepted_peak_count` 是人工接受的 PERSON peak | 它是冻结 GT-blind local-max/NMS artifact 中落入 region 的候选数 |
| candidate artifact 无行等于该帧没有候选 | 旧 artifact 只覆盖 126/398 帧；未覆盖必须标记 unavailable |
| local competing-response pool 是纯背景 | 它是局部强竞争响应控制池，可能含 PERSON 相关或融合显示结构 |
| P0 公共表观运动是真实平台轨迹 | 它只是背景估计的图像域公共输运 |
| RGB/JET 通道是独立雷达物理通道 | 它们是同一伪彩显示链的观测代理 |
| `P1E_EXPLORATORY_CONCLUSION.md` 的“不进入时序”仍是当前结论 | 它是已被后续动态证据工作替代的历史开发判断 |

## E. 下一阶段实验建议

本节只提出受控实验问题，不实现新算法。优先级按“先修清输入和评价语义，再谈功能扩展”排列。

### E1. Runtime-only schema 与 process-isolation 复核

目标：把“算法生成边界合规”进一步落实为“产物接口不会被误用”。

- 为 raw fragment、causal/buffered shell、response-region、pixel edge、node/component 分别定义 runtime-only 字段白名单；
- 将 `source_parent_stitched_ids`、accepted parent、manual reference、offline assignment 明确归入 audit/evaluation schema；
- 用独立进程只读取净化后的 runtime inputs 重放现有冻结产物并核对哈希；
- 不改变任何 C2、shell、region 或 topology 公式。

### E2. Optical causal availability / latency 审计

目标：量化当前 optical branch 在真实运行时间条件下能提供什么，而不是选择“最好窗口”。

- 固定比较 same-frame、past-only 和预定义 buffered latency；
- 报告 fragment availability、shell 数、宽度、fan clipping、common-FoV、candidate burden；
- manual reference 只在所有分支生成后评价 retention；
- 不做 identity assignment，不用 reference 选 fragment。

### E3. Mapping 与 guard 的独立不确定度审计

目标：区分 box angular span、mapping error、guard 和 temporal union 的贡献。

- 使用独立几何标定证据或新采集校准数据；
- 不用当前 PERSON SAR reference 调 intercept、slope 或 guard；
- 预先冻结比较项，报告壳宽和重叠的变化，不把较窄壳自动写成更正确。

### E4. 冻结 response-region 的位置特异性复核

目标：验证 region presence 相对局部竞争控制的可重复性，而不是再新增 C4/C5。

- 保持 C2、固定支持盘、q90/q95/q97.5 和 connected-component 规则不变；
- 在新采集或独立封存数据上比较 manual reference、固定偏移、几何匹配和 local competing controls；
- 同时报告 region coverage、面积、形状、边界/截断和 shared，不选择“最好 percentile”；
- 不生成 PERSON box，不训练分类器。

### E5. 固定 topology 的可重复性审计

目标：确认 one-to-many / many-to-one / many-to-many 是否是可重复观测结构，而不是当前开发语料偶然现象。

- 冻结 raw-fragment shell、时间策略、guard、response-region 和 pixel-intersection 规则；
- 在新数据上只复核 local degree、component topology、no-edge、edge/truncated 状态与搜索负担；
- reference 只用于后置解释哪些 topology 与 PERSON 邻近响应共现；
- 不从 topology 中选择 identity 或最终位置。

### E6. 新采集盲验证准备

只有在 E1–E5 明确输入合同、因果可用性、弃权语义和冻结评价后，才建议建立新的 acquisition group：

- 预先冻结代码哈希、尺度、mask、时间策略、guard、region 层级、controls 和分母；
- 开发 run 不再承担确认意义；
- 新数据在 runtime/pre-reference 产物全部物化后再解封 manual reference；
- 仍不自动进入 tracker、classifier、score fusion、identity assignment 或 SAR box regression。

## 5. 代码—产物—报告一致性检查结果

### 5.1 一致的部分

- 单帧 `S(x)` 生成函数与报告一致：只使用 SAR 伪彩图、扇面几何、固定物理尺度和有效 mask；
- candidate extraction 与 reference 评价顺序一致：整帧候选先生成，之后才逐 reference 评价；
- runtime-track amendment 与实际代码一致：RAW 为主，STITCHED 为 offline proxy；
- response-region 协议澄清与代码一致：实际场为 `fixed_support_mean_v2(C2)`，不是基础 C2；
- 最新 topology 报告与代码一致：edge 使用像素相交，reference 在 topology 后物化；
- 最新独立验证器显式检查 runtime 表不含 `physical_target_id`、`target_id` 和 reference 坐标列。

### 5.2 需要读者主动纠正的部分

- 任务 README 首行状态尚未列出 runtime-track 与 shell-topology 两个最新完成状态；后文 161–201 行才包含当前结果；
- README 79–92 行及 `P1E_EXPLORATORY_CONCLUSION.md` 是旧单帧状态，不能覆盖后续章节；
- candidate protocol/summary 仍物化 temporal gate 字段，只能当历史审计字段；
- runtime-track 主协议第 20、47–50 行被 amendment 修正，不能脱离 amendment 单独引用；
- `response_region_track_shell_intersection.csv` 名称容易让人误认为最新 topology，实际仅为粗 angular extent intersection；
- `accepted_peak_count` 容易被误解为人工接受，后续文档应始终加 `GT_BLIND_NMS` 限定；
- `pre_reference` 文件可带 offline stitching provenance；读取时必须区分“未用 SAR reference”与“因果 runtime 可用”。

本轮按用户要求不修改这些历史文件或冻结模块，仅在本文建立统一解释边界。

## 6. 关键证据索引

- SAR-only map 与固定支持盘：[`run_p1e_single_frame_position_specificity.py`](../run_p1e_single_frame_position_specificity.py)，309–361、494–512、1173–1218 行。
- GT-blind candidate extraction 与 reference 后置评价：[`run_p1e_candidate_recall_audit.py`](../run_p1e_candidate_recall_audit.py)，237–293、560–700 行。
- observation entity 混合表：[`run_p1e_observation_model_diagnostic.py`](../run_p1e_observation_model_diagnostic.py)，549–697 行。
- matched TRUE/NULL shell 先生成、reference 后读取：[`run_p1e_optical_shell_information_gain.py`](../run_p1e_optical_shell_information_gain.py)，267–394、1601–1796 行。
- raw/stitched identity 边界与 sanitized explorer：[`run_p1e_runtime_track_response_region_minimal.py`](../run_p1e_runtime_track_response_region_minimal.py)，139–170、223–259 行。
- response-region 定义与完整 pre-reference 生成：[`run_p1e_runtime_track_response_region_minimal.py`](../run_p1e_runtime_track_response_region_minimal.py)，363–459、1823–1924 行。
- 旧 angular intersection：[`run_p1e_runtime_track_response_region_minimal.py`](../run_p1e_runtime_track_response_region_minimal.py)，1401–1434 行。
- 最新 raw-fragment shell 与 uncertainty decomposition：[`run_p1e_shell_uncertainty_region_topology.py`](../run_p1e_shell_uncertainty_region_topology.py)，236–390 行。
- 最新像素 edge、local degree 与 component topology：[`run_p1e_shell_uncertainty_region_topology.py`](../run_p1e_shell_uncertainty_region_topology.py)，496–674 行。
- pre-reference 到 offline reference 的执行顺序：[`run_p1e_shell_uncertainty_region_topology.py`](../run_p1e_shell_uncertainty_region_topology.py)，1249–1349 行。
- runtime 表字段边界的独立验证：[`validate_p1e_shell_uncertainty_region_topology_report.py`](../validate_p1e_shell_uncertainty_region_topology_report.py)，345–389 行。
- optical identity 正式修正：[`00A_PRE_RUN_OPTICAL_IDENTITY_PROVENANCE_AMENDMENT.md`](../../../output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/runtime_track_response_region_minimal_v1/00A_PRE_RUN_OPTICAL_IDENTITY_PROVENANCE_AMENDMENT.md)。
- 最新 topology 协议：[`00_SHELL_UNCERTAINTY_REGION_TOPOLOGY_PROTOCOL_FROZEN_BEFORE_RUN.md`](../../../output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/shell_uncertainty_region_topology_v1/00_SHELL_UNCERTAINTY_REGION_TOPOLOGY_PROTOCOL_FROZEN_BEFORE_RUN.md)。
- 最新 topology 报告：[`P1E_SHELL_UNCERTAINTY_REGION_TOPOLOGY_REPORT.html`](../../../output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/shell_uncertainty_region_topology_v1/P1E_SHELL_UNCERTAINTY_REGION_TOPOLOGY_REPORT.html)。

## 7. 本次审阅停止点

- 未新增或修改算法；
- 未运行 P0/P1E 实验或重新生成既有报告；
- 未修改冻结 P0、B0R、C0–C3、candidate、shell、region 或 topology 模块；
- 未创建 tracker、classifier、score fusion、identity assignment 或 SAR box regression；
- 未创建、移动或修改 SAR 框；
- 未读取或依赖 `old_work`；
- 未 commit、未 push。
