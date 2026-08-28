# PERSON 成像机理约束图像域研究

- 当前权威状态：`P0_FROZEN_PASS / P1E_EXPLORATORY_OBSERVATION_INTERFACES_ESTABLISHED / RUNTIME_IDENTITY_NOT_ESTABLISHED / P2_NOT_ESTABLISHED`
- 活动工作区：D:\profile\research\workspace
- 任务目录：D:\profile\research\workspace\tasks\person_physics_guided_image_domain_study_20260824
- 输出目录：D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824
- 解释器：D:\MINICONDA\envs\py311\python.exe
- old_work：不读取、不作为运行依赖

## 研究定位

本任务研究成像机理与物理尺度约束下，PERSON 目标在 SAR 伪彩图像域中的条件性观测响应，并结合光学的语义、行为、时间和方位先验进行多模态关联。

研究对象不是人体固有 RCS 或固定人体模板，而是目标、场景散射、载体行为、孔径积累、运动补偿和显示链共同作用后的图像域响应。

## 固定语义

1. 光学只提供时间、连续 ID 假设、行为状态和方位搜索带；不直接指定 SAR 亮点或最终框。
2. SAR 图像证据决定搜索带内的最终响应位置。
3. SAR 框轨迹是图像坐标观测路径，不等于目标独立运动。
4. 公共表观运动是图像域配准量，不等于真实载体轨迹。
5. 局部相似度只表示条件性显示重复性，不是身份、人体概率、RCS 或物理散射稳定性。
6. 现有 person_sar_motion_evidence_20260824 保留为失败探针，不允许用于物理目标运动解释。

## 三阶段路线

### P0：公共表观运动可观测性

- R01ZF 作为发现集，R04ZF 作为不调参留出集。
- 拟合时屏蔽 PERSON 框和扇面无效区，只用多个背景结构估计帧间公共表观运动。
- 比较无补偿、全局平移、全局仿射和距离—方位局部运动场。
- 用静止 PERSON 的补偿后残差和留出背景结构检查模型是否达到目标尺度内的可用精度。

### P1：补偿后的 PERSON 条件响应

- 独立审阅后，现有 R01/R02/R03/R04 全部视为已暴露的探索开发语料，不能授予盲确认意义上的 P1_PASS。
- 主研究收窄为两类：可在任意候选位置计算的单帧位置特异性，以及冻结 P0 与局部误差预算下的时序一致性。
- 原生人工框用于离线主评价；插值框只用于覆盖和敏感性，真实框中心、宽高或 physical_target_id 不得成为运行时输入。
- 真正 P1 确认必须使用新的封存 acquisition group；没有新数据时止于 `P1_EXPLORATORY_ONLY_NO_BLIND_CONFIRMATION`。

### P2：光学—SAR多模态关联

- 当前同步未验证且没有 behavior 字段，光学行为移出 P1 核心；只有在 SAR 测量冻结并通过新数据盲验证后，才另设跨模态审计。
- 使用未验证同步的时间偏移假设，而不是默认同帧真同步。
- 光学生成方位搜索壳；SAR候选、时序边和歧义状态完成关联。
- 不允许运行时使用人工 physical_target_id 选择正确光学轨迹。

## 当前入口

- 人类可读研究章程：output/person_physics_guided_image_domain_study_20260824/00_RESEARCH_CHARTER.md
- P0预注册协议：output/person_physics_guided_image_domain_study_20260824/01_P0_COMMON_APPARENT_MOTION_PROTOCOL.md
- 机器可读契约：output/person_physics_guided_image_domain_study_20260824/research_contract_v1.json
- 新Session交接Prompt：output/person_physics_guided_image_domain_study_20260824/02_NEXT_SESSION_HANDOFF_PROMPT.md

## P0 完成状态（2026-08-24）

- 最终判定：`P0_PASS`。
- 冻结模型：lag 1 = M1 全局平移；lag 3 = M2 全局仿射；lag 5 = M2 全局仿射。
- R04 留出验证：579/579 个帧对可比较，578/579 相对 M0 降低背景留出残差。
- 静止 PERSON：全部接受框补偿后 P90 = 3.557 px；人工端点子集补偿后 P90 = 5.029 px；R04 PERSON 框短轴中位数 = 18.504 px。
- 最差帧视觉复核通过：没有发现背景模型吸附 PERSON 扩张区或扇面/20 m 边界。
- P1：P0 完成时为 `ELIGIBLE_BUT_NOT_STARTED`；2026-08-25 已在用户单独授权后进入 B0R/P1E 探索，但没有授予 P1_PASS。
- P0 输出：output/person_physics_guided_image_domain_study_20260824/p0_common_apparent_motion
- P0 理论—计算—指标—结果总览：output/person_physics_guided_image_domain_study_20260824/p0_common_apparent_motion/P0_THEORY_METHOD_RESULTS_OVERVIEW.md
- P0 一页总览图：output/person_physics_guided_image_domain_study_20260824/p0_common_apparent_motion/visualizations/P0_RESEARCH_OVERVIEW.png
- P0 背景、lag、残差与指标交互式讲解：output/person_physics_guided_image_domain_study_20260824/p0_common_apparent_motion/P0_BACKGROUND_RESIDUAL_EXPLAINER.html
- 交付验证：p0_common_apparent_motion/validation_report.json = `PASS`（18/18 checks）。

## P0 后深化研究规划状态（2026-08-25）

- 审阅前方案：output/person_physics_guided_image_domain_study_20260824/03_POST_P0_DEEPENING_RESEARCH_PLAN_DRAFT.md
- 独立科学审阅：output/person_physics_guided_image_domain_study_20260824/04_INDEPENDENT_REVIEW_OF_POST_P0_PLAN.md，结论 `MAJOR_REVISION_REQUIRED`
- 审后本地证据审计：output/person_physics_guided_image_domain_study_20260824/05_POST_REVIEW_LOCAL_EVIDENCE_AUDIT.md
- 机器可读审计结果：output/person_physics_guided_image_domain_study_20260824/05_POST_REVIEW_LOCAL_EVIDENCE_AUDIT_DATA.json
- 当前修订路线：output/person_physics_guided_image_domain_study_20260824/06_POST_P0_DEEPENING_RESEARCH_PLAN_REVISED.md
- 可复核审计脚本：tasks/person_physics_guided_image_domain_study_20260824/audit_post_p0_local_evidence.py
- B0R 与 P1E 的当前实际状态见下节；P2 仍保持 `BLOCKED`。

## B0R 与 P1E 当前状态（2026-08-25）

- B0R 最低必要门控已完成：R02 目标位置 lag1/3/5 可做时序分别为 56/19/0；R03 为 7/1/0。B0R 只决定哪里可做时序，不是校准置信上界。
- P1E 单帧主分析使用 251 个原生人工框；响应图先按整帧生成，框只用于离线采样。
- 已修正首轮评价偏差：不再使用局部最大值膨胀；主分数为固定 0.30 m 支持盘均值；有效区直接复用冻结 P0 掩膜。
- 响应尺度改为扇面几何换算的固定 0.30/0.55/0.90 m 物理尺度，不读取 PERSON 框宽高生成分数。
- 当前首选候选为 `C2_COMPACT_JET_GRADIENT_CONSENSUS`：总体对局部最强硬背景胜率 85.4%，但 R02 仅 47.2%，峰到参考位置中位距离约 0.57 m；R02 P01/P02 的目标级硬背景中位优势为负。
- 新增的 `C3_ISOTROPIC_BLOB_RIDGE_SUPPRESSED` 能修复部分 R04 亮核漏检，但没有修复 R02，不作为通用替代。
- 当前探索结论：`P1E_SINGLE_FRAME_CONDITIONAL_SIGNAL_FOUND_BUT_NOT_STABLE_ENOUGH_FOR_INTERFACE_FREEZE`。
- 因单帧通用位置特异性未建立，本轮未进入补偿后时序、未运行全部插值框敏感性、未授予 P1_PASS。
- B0R/P1E 输出：output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface
- HTML 直接证据报告：output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/P1E_SAR_ONLY_RESPONSE_INTERFACE_REPORT.html
- Markdown 结论：output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/P1E_EXPLORATORY_CONCLUSION.md

## P1E 候选存在性—唯一定位性语义拆分（2026-08-26）

- 冻结 P0、B0R、C0–C3 和旧 P1E 结果全部保留；新增版本目录为 `p1e_sar_only_response_interface/candidate_recall_semantic_split_v1`。
- GT-blind 候选在整幅 `S(x)` 上先做局部极大值与 NMS，再读取人工 reference 做离线评价；固定 `K=1/2/3/5`、`r=0.3/0.5/0.8 m`，没有按 GT 中心先搜峰。
- R02 C2 的 Recall@1/3/5(0.8 m) 为 `27.8% / 44.4% / 44.4%`；Top-5 相对 Top-1 只恢复 `16.7` 个百分点。
- P01：9/9 帧在 0.8 m 内存在某个 C2 局部峰，但最近候选 rank 中位数 14，Top-5 为 0/9；P02：7/9 有半径内峰，Top-5 仍为 0/9，另 2/9 为半径级候选缺失/当前表示未捕捉。
- P03/P04：各 8/9 进入 Top-5、5/9 为 Top-1，但 9/9 均存在同一 GT-blind 候选落入多个人工 reference 的 0.8 m 邻域；该结果只标记 `response_merging_suspected`，不是物理融合证明。
- C3 没有修复 P01/P02：两者 Recall@5 仍为 0，最近候选 rank 中位数约 121/99。
- `Omega_single_v1` 与冻结 P0 时序域已拆开。R03 四个人工 reference 在单帧域中均为 FULL；F458 约 0.02 m 处存在 C2 候选但 rank=18，说明“P0 不可比较不等于单帧不可观察”，不说明 Top-5 召回足够。
- 该版本当时按预注册时序入口四项中三项失败而没有运行 lag1/lag3；这是历史开发决定，不再作为后续研究资格 gate。2026-08-26 用户取消阶段式 gate 后，已在独立版本目录直接完成 lag1 动态证据实验。
- 旧结论应修正为：R02 P01/P02 多数帧不是“PERSON 响应完全不存在”，而是“参考附近常有低 rank 原始峰，但没有进入高响应 Top-5 短名单”；P02 另混有少量候选缺失。P03/P04 则是候选召回成立但唯一性不足。
- 新代码：`render_p1e_candidate_recall_semantic_report.py`；候选生成代码仍为 `run_p1e_candidate_recall_audit.py`。
- HTML 报告：`output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/candidate_recall_semantic_split_v1/P1E_CANDIDATE_RECALL_SEMANTIC_SPLIT_REPORT.html`。
- Markdown：`output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/candidate_recall_semantic_split_v1/01_CANDIDATE_RECALL_SEMANTIC_INTERPRETATION.md`。
- 机器可读解释：`single_frame_candidate_recall/candidate_semantic_interpretation_v2.json`；逐 reference 解释层：`single_frame_candidate_recall/manual_reference_candidate_interpretation_v2.csv`。

## P1E 动态证据状态与 lag1 最小时序信息增益（2026-08-26）

- 版本目录：`output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/dynamic_evidence_temporal_v1`；R02ZF 为已暴露开发语料，不授予 `P1_PASS`，不声称盲验证。
- 本实验不设单帧资格 gate，也不截断 Top-K。使用全部 23 帧的 6,457 个既有 GT-blind C2 候选，建立 22 个 lag1 pair、52,926 条 3σ 边、17,129 条互为最近邻边；人工 reference 只在完整节点/边/线程生成后用于离线评价。
- 当前总状态：`TEMPORAL_STRUCTURE_PRESENT_P0_SPECIFIC_GAIN_NOT_ESTABLISHED`。真实序列存在持续 SAR 响应结构，gross 错误输运会破坏该结构；但正确 P0 相对 `ZERO_TRANSPORT` 的特异增量没有建立。
- 正确 P0 相对 zero 的 incoming max/sum 中位优势均仅 1.5 名，mean 中位优势为 0 且 83.3% 配对持平；全部节点 max/sum/mean 排序 Spearman 中位为 0.9756/0.9794/0.9916。
- 2σ 互为最近邻边中，正确 P0 与 zero 重合 95.96%，Jaccard=0.921；线程长度 73.8% 完全相同，shared state 32/32 一致。lag1 P0 位移中位约 0.103 m，而局部设计容差 σ 中位约 0.301 m，仅相隔约 0.34σ，这是当前难以区分正确与零输运的主要直接原因。
- P01 有局部恢复；P02 高度异质，且相对 zero 仅 2/6 个可评价帧更好。P02 F482 在 0.8 m 内缺节点；F490 最近节点约 0.820 m，是固定半径边界病例，lag1 不能凭空创造候选。
- P03/P04 在当前 0.8 m 邻域定义下持续 `SHARED`，但两人间距约 0.695–0.808 m；该标签只表示离线邻域重叠/未观察到分离，不证明物理融合或身份不可分。
- F490/F494 是证据分量冲突病例：incoming max/sum 严重下降，但 mean rank 仍为 2–3、线程长度仍为 23。因此 image、geometry、max/sum/mean、thread 和 ambiguity 状态必须并列保留，不能过早加权成单一 posterior 或 PASS/FAIL。
- 运行边界准确表述为：reference 内容没有参与节点、边或线程计算；但 reference CSV 字节在图前被哈希，含 annotation 字段的 explorer 容器也曾整体加载，因此不声称严格 sealed-data process isolation。
- 局部不确定度仍有审计限制：22.45% 候选使用 nearest-8 fallback，39.74% 至少一个距离/方位维度未被锚点双侧包围；`TANGENTIAL_PLUS_0_75M` 和单一 shift7 shuffle 只作为 gross sanity，不是校准 null。
- 复现审阅记录但未回写原动态图的缺口包括：同名 `best_support_normalized_error` 合并字段存在 `_x/_y` 与无后缀混合；动态图脚本/协议及 fixed-offset、B0R comparability 没有全部进入原 manifest 的预运行冻结哈希；动态图代码未 assert/filter `pair_comparable`，但本次 R02 lag1 为 22/22 comparable。
- 计算代码：`run_p1e_dynamic_evidence_temporal.py`；解释与报告代码：`render_p1e_dynamic_evidence_temporal_report.py`。
- HTML：`output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/dynamic_evidence_temporal_v1/P1E_DYNAMIC_EVIDENCE_TEMPORAL_REPORT.html`。
- Markdown：`01_DYNAMIC_EVIDENCE_TEMPORAL_INFORMATION_GAIN_REPORT.md`；独立方法审阅：`02_DYNAMIC_EVIDENCE_METHOD_AUDIT.md`；机器解释：`lag1_r02/post_analysis_v1/dynamic_evidence_interpretation_v1.json`。
- 报告自检 13/13 通过：21 个本地引用缺失 0，12 幅图不可读 0，7 个直接病例齐全；Edge headless 首屏布局正常。
- 冻结 P0 回归验证再次为 18/18 PASS，合同三个输入 SHA256 3/3 匹配。未重调 P0，未修改 B0R/C0–C3/旧 P1E、原始图像或标注，未创建或移动 SAR 框，未 commit、未 push。
- 下一步若继续，应把 lag3/两步接续与显式 missing-state bridge 作为预先固定的小实验，并继续以 correct、zero、错误输运和打乱帧比较；不引入单帧资格 gate，也不自动进入复杂跟踪器。

## PERSON-SAR 观测模型诊断 v1（2026-08-26）

- 当前研究对象已从“单帧找唯一点或机械增加 lag”重构为条件性响应的动态观测状态：image、observation condition、P0/geometric、temporal、optical 和 ambiguity 六个维度并列保留，不构造未经校准的总分。
- 新版本目录：`output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/observation_model_diagnostic_v1`；旧 P0、B0R、C0-C3、candidate split 与 dynamic evidence 结果均保留且未覆盖。
- 统一 `observation_condition_table.csv` 共 39,764 行，覆盖 251 个 PERSON reference、37,015 个既有 GT-blind C2 candidates，以及固定偏移、几何匹配和局部竞争 controls；同一位置条件函数记录 range、azimuth、扇面/20 m 边界、support、显示代理、P0 local sigma/锚点覆盖、C2/C3 与 provisional optical shell。
- R02 P01/P02 的最近候选均为 9/9 rank>5，其中各有 7/9 同时被离线标记为 shared；P02 另有 2/9 在 0.8 m 内 candidate missing。P03/P04 各 9/9 shared，每个目标均为 5 帧 rank1、3 帧 rank2、1 帧 rank12。这里的 shared/missing/low-rank 都是人工 reference 条件下的离线评价状态，不是已经建立的 GT-blind runtime 状态检测器；`shared` 只表示图像域候选邻域重叠，不解释为物理散射融合。
- P02 的两个 missing 病例位于 FULL support、lag1 P0 core 且无 display shift，不能主要归因于边界、P0 低可靠或显示突变；当前表示/候选提取与局部竞争仍是独立阻断。
- 空间语义已拆分为 `SAR_SINGLE_FRAME_OBSERVABLE`、`P0_TRANSPORT_CORE`、`P0_TRANSPORT_EXTENDED` 与 provisional `MULTIMODAL_COMMON_FOV`。R03 reference lag1 core 为 0%，但单帧仍可观察；F494 有 rank=6 候选而 lag1 P0 unavailable，直接说明 P0 不可比较不等于单帧不可观察。
- lag1/3/5 的全场中位 `transport displacement / local sigma` 为 `0.255 / 0.697 / 1.019`；correct-P0 C2 field retention 为 `0.873 / 0.779 / 0.720`，correct-zero 增量为 `0.014 / 0.087 / 0.171`。这是描述性聚合 tradeoff：lag1 使用 M1、lag3/5 使用 M2，帧对集合和 display 状态也不同，且 R03 lag5 不单调，不能把差异写成纯 lag 因果效应。这里的 sigma 含固定 0.30 m support 项，只是设计容差，不是校准置信区间。
- 该全场 C2 field-alignment 增益与旧 dynamic evidence 的 PERSON 邻近候选消歧是不同问题：前者有小而系统的 correct 增益，后者在 lag1 仍未建立稳定 P0-specific 增益。
- `DISPLAY_HIGH_CENSOR_PROXY` 全部为 0；`DISPLAY_COMPRESSED_PROXY` 全部为 1，均缺乏区分力。连续 display JS/robust shift 可分层，lag5 高 display-change 的 correct retention 低于 baseline，但只能解释为显示观测条件共现，不能归因于 PERSON 固有 RCS 或真实回波变弱。
- provisional ±250 ms optical azimuth shell 对 reference 的覆盖高于 ±18° shifted controls；但同步未验证，shift 前虽等宽，扇面裁剪后的真/假壳角宽并不相等。现有 `coverage_per_degree` 实际是“候选覆盖比例/平均扇内角宽”proxy，而不是候选数/度；该 proxy 在正确壳与 shifted controls 间相近。因此只支持下一轮带公平裁剪/面积控制的多模态候选实验，光学仍不决定 SAR range 或最终响应位置。
- 诊断代码：`run_p1e_observation_model_diagnostic.py`；HTML 生成/验证：`render_p1e_observation_model_report.py`。
- HTML：`output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/observation_model_diagnostic_v1/P1E_OBSERVATION_MODEL_DIAGNOSTIC_REPORT.html`；自动验证 `report_validation.json = PASS (14/14)`；浏览器首屏已实际渲染检查。
- 诊断重跑修复了 NaN 预测点转整数的 RuntimeWarning；7 个核心 CSV 的 SHA256 与修复前完全一致。诊断脚本 SHA256=`25F5D05333E85BAAC95ADA59D581C06C3533CF137FC83462D66CBA1D6A6CCCBE`，报告生成器 SHA256=`C4EC3D0E24CA43F0C779B8609D838CB50ADDFFFA8B974CB772ABFB13B79DD272`，HTML SHA256=`7BB645D2F63DAF0D521B974ED40556B3F6CBBF0BC6BC0AD692393ECDB00B3CB2`。冻结 P0 回归再次为 `18/18 PASS`，合同三个输入 SHA256 仍全部匹配。
- 本轮不授予新 PASS/FAIL，不训练分类器或复杂 tracker，不冻结最终接口；若继续，当前优先级是基于观测可靠度设计受控的 missing/shared 状态实验和公平 optical-shell control，而不是机械堆新特征或只增加 lag。

## 等搜索成本 optical-shell 信息增益诊断 v1（2026-08-27）

- 新版本目录：`output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/optical_shell_information_gain_v1`；冻结 P0、B0R、C0–C3、candidate split、dynamic evidence 与 observation diagnostic 均保持只读。
- TRUE 壳使用 SAR 时间戳 ±250 ms 内全部 optical PERSON 粗方位壳并集，不按 `physical_target_id` 选轨；376 个有 TRUE 壳的帧均固定生成 3 个 matched NULL，共 1,128 个。NULL 只用固定光学映射、SAR 扇面、`SAR_SINGLE_FRAME_OBSERVABLE` 与 provisional common-FoV，人工 reference 与 C2 candidate 均不参与选择。
- 几何公平性：NULL 相对 TRUE 的扇内角宽误差中位为 0、P90 约数值零；有效面积误差中位 `6.39e-5`、P90 `2.46e-4`；common-FoV overlap 差中位 `0.0168`；A/B/C 控制质量为 `843/226/59`，困难控制没有删除。
- 在 245 条有 TRUE 壳的 reference 上，TRUE/NULL 的中心几何覆盖为 `89.4% / 26.8%`，0.8 m 邻近候选存在为 `89.4% / 27.3%`，full-fan 最佳邻近候选保留为 `89.0% / 26.9%`，严格一对一覆盖为 `73.5% / 22.2%`，Top-5/0.8 m 为 `81.6% / 24.5%`。reference 加权 candidate burden 中位几乎相同：`44.6% / 44.3%`。
- 全 251 条 reference 的无条件口径单独保留：光学先验可用 `245/251=97.6%`；不可用 6 条为 R01 F133/F135/F140/F141 P01 与 R04 F175/F180 P03。将其计入分母后，TRUE 中心覆盖和 0.8 m 候选保留均为 `87.3%`，Top-5/0.8 m 为 `79.7%`。
- 优势主要来自正确方位覆盖，而不是新的壳内 C2 判别：给定 reference 已落入壳内，候选存在为 TRUE/NULL `99.1% / 97.5%`，Top-5 为 `90.9% / 87.8%`；在 TRUE 与至少一个 NULL 都保留邻近候选的 114 条记录中，local-rank 中位优势为 `0`，`62.3%` 持平，TRUE 更好 `12.3%`、更差 `25.4%`。
- R02 P01 的 global rank 中位 `11→3`，P02 `18→6`，说明低 rank 有明显全扇面竞争成分；但 P01/P02 各 `7/9` 同时 shared，P02 F482/F490 仍缺 0.8 m 离散峰。P03/P04 `1→1` 且 TRUE 覆盖各仅 `7/9`，覆盖时 shared 仍在：方位壳缩小搜索范围，没有解决 SAR 空间共享/未分离。
- F482/F490 的 reference C2 percentile 分别约 `0.959/0.993`，最近离散峰距约 `1.159/0.820 m`，两者均 FULL support、P0 CORE、无 display shift。因此 `candidate missing` 不能解释为 SAR 响应消失；本轮只记录 response-region/ridge support 的后续方向，没有新增算法。
- 仅有 C2 candidate 的 120 帧中，TRUE 的 P0 CORE 比例中位低于 NULL（`57.5% / 66.2%`），fallback 高于 NULL（`20.6% / 12.8%`）；TRUE 优势不能归因于更可靠的 P0 区域。DISPLAY_SHIFT 两层均保有正候选保留差，但只作共现分层，不作显示链因果解释。
- HTML：`P1E_MATCHED_OPTICAL_SHELL_INFORMATION_GAIN_REPORT.html`；报告验证 `PASS (14/14)`，9 个直接病例和全部本地链接可读，Edge 1600×1100 首屏实际渲染正常。分析脚本 SHA256=`2C71440DF9C22FDCE17A3C4050E4E0054F6B7CA4542C44C134E2DEA3478A2203`，报告生成器 SHA256=`02BAF81874BCA96569788402E5BA01A7FF1BBCFC61978974173A9187571D112F`，HTML SHA256=`69ADCB3CA5C982E5E87C3ADB0E007F79325CC942FB8B4D7EF614B4B6EB561E47`。
- 首轮 `shell_definition_table.csv`、`shell_candidate_table.csv`、`shell_candidate_metrics.csv` 的 SHA256 在 warning/顺序修正后逐项完全不变；完整重跑没有 warning。2026-08-27 00:29:34 +08:00 冻结 P0 回归再次 `18/18 PASS`，合同三个输入 SHA256 `3/3` 匹配，未读取 `old_work`、未修改原始图像/标注、未创建或移动 SAR 框、未 commit/push。
- 当前科学判断：已有开发证据支持“粗光学方位映射提供真实的搜索域信息”，但没有建立壳内唯一定位、严格同步或最终 P2。若继续，优先验证同步和 runtime optical track identity，并对 F482/F490 做最小 response-region 表示审计；SAR 继续决定 range 与最终响应位置。

## 运行时 optical track 壳与冻结 C2 response-region 最小诊断 v1（2026-08-27）

- 新版本目录：`output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/runtime_track_response_region_minimal_v1`；最终状态为 `COMPLETE_NO_NEW_PASS_FAIL_NO_P2_CLAIM`。
- 本轮没有新增 C4/C5、总分、分类器、region tracker 或 SAR 框；冻结 P0、B0R、C0–C3 和全部旧结果保持只读。光学仍只提供 time/azimuth prior，SAR 保留 range 与最终定位权。
- 主 optical 接口为 `RAW_DETECTED_FRAGMENT_ALL`：全部自动 detected `raw_track_fragment_id` 都独立出壳，不按 accepted tier、人工 `physical_target_id` 或 SAR reference 过滤。次级 `STITCHED_ACCEPTED_GT_BLIND_OFFLINE_PROXY` 是全 run Hungarian stitching 与短缺口插值形成的离线连续性代理，不能称严格 runtime identity。
- 光学 provenance：R01/R02/R03/R04 的 raw fragments 分别为 `12/33/5/11`，stitched accepted tracks 为 `6/9/2/5`；R02 accepted tracks 的 ambiguous stitch 合计 `10`，是当前 runtime identity 的主要断点。
- 固定时间半窗为 `0/100/250/500 ms`。RAW 接口的 reference 候选保留率为 `76.9%/81.7%/87.3%/93.2%`；单 track burden 中位为 `14.5%/16.4%/22.0%/25.8%`，all-track union burden 中位为 `28.2%/31.5%/35.9%/41.0%`。窗口增大是保留率—搜索负担权衡，不能看结果后选择所谓最优窗口。
- 这些窗口是居中诊断，`100/250/500 ms` 可能包含未来光学观测；因此现有主接口是“最接近运行时的自动 tracklet 来源 + 带缓冲的时间不确定度诊断”，还不是零延迟 causal online tracker。
- R02 在 RAW ±250 ms 下的 `global→all-track union→offline best-track` rank 中位：P01 `11→3→2`，P02 `18→6→4`，P03/P04 均为 `1→1→1`。P01/P02 的全场竞争进一步缩小，但离线 best-track 只用于后置评价，运行时没有用 reference 选轨。
- P03/P04 的 track shells 没有稳定分离；offline-associated 壳的角度 Jaccard 在不同窗口仍约 `0.5–0.6`，且各窗口可配对帧数不同。当前不能声称“光学 identity 已分开而 SAR 仍只有同一响应”。
- 冻结 C2 的实际候选场保持为 `S(x)=fixed_support_mean_v2(C2)`；response-region 固定使用全有效域 q90/q95/q97.5、4096-bin percentile、8-connectivity，不做形态学桥接、面积删除、watershed 或 PERSON 个案调参。
- q95 response-region 对 251 条 PERSON reference 的直接覆盖为 `98.0%`，0.30 m 邻近覆盖为 `99.2%`；`PEAK_MISSING_REGION_PRESENT` 共 2 条，正是 R02 F482/F490；q90-only 共 2 条，为 R02 F494 P01 与 R04 F35 P01；q90 内完全无 region 为 0。
- q95 直接覆盖的离线位置对照：PERSON `98.0%`，固定偏移 `1.8%`，几何匹配空间对照 `3.9%`，local competing response `63.3%`。这支持 region 比离散 peak node 更忠实地表达已有响应，但局部竞争仍强，不能授予单帧唯一定位。
- F482 P02：C2 percentile `0.959`，最近峰 rank 14、距 `1.159 m`；q95 shared extended region 面积 `1.362 m²`、主轴 `2.257 m`。F490 P02：percentile `0.993`，最近峰 rank 14、距 `0.820 m`；q95 shared extended region 面积 `2.148 m²`、主轴 `4.094 m`，region 内含 ranks `13/14/15/18`。
- q95 shared fraction 总体为 `37.5%`，R02 为 `94.4%`，R01 为 `60.6%`，当前 R03/R04 reference 为 0。shared region 只描述图像域响应重叠/未分离，不是物理散射融合证明。
- 旧 candidate artifact 只覆盖 `126/398` 帧（R01 39、R02 23、R03 4、R04 60）；覆盖帧的数量、rank、坐标、score、support 全部精确复现，最大浮点差约 `1.11e-16`。其余 272 帧标记为 `NO_LEGACY_CANDIDATE_ARTIFACT_FOR_FRAME`，不得解释为零候选；连续 response-region 与 masks 覆盖 `398/398` 帧。
- 正式病例共 7 个：F482、F490、F483 shared、R03 F458 外距离边界、R04 F0 清晰对照、R04 F35 q90-only、R02 F488 低 rank track-shell；每个病例同时提供局部四联图和全扇面六联图。
- 分析代码：`run_p1e_runtime_track_response_region_minimal.py`，SHA256=`051B414753B73118CF77712A35DF86EC5FB05C12B2C00217EB14BFE81DFDCBBA`。
- 报告代码：`render_p1e_runtime_track_response_region_report.py`，SHA256=`A9FE022A044718E3A376BEF39FE5F15273405008E305EB3D1FD77489EF082BAE`；独立验证代码：`validate_p1e_runtime_track_response_region_report.py`，SHA256=`02ECD3F9934C0431D7D00D81B790CF92A243468DA272698A439FFF86D233267A`。
- HTML：`P1E_RUNTIME_TRACK_RESPONSE_REGION_MINIMAL_REPORT.html`，SHA256=`226FDA62494A4FD984EC6D2E68FA96D8A4FC2EA838A0E35CE721126FF483FDE1`；独立 `report_validation.json = PASS (18/18)`，66 个本地链接缺失 0，19 张正式图不可读 0。
- Edge headless 1600×1100 首屏已实际检查：`report_browser_qa_top.png`，布局与中文渲染正常。2026-08-27 18:22:43 +08:00 冻结 P0 回归再次为 `18/18 PASS`。
- 当前停止点：两个接口的职责已经更清楚，但不授予 P1/P2 PASS、不声称盲验证、不进入复杂多模态 tracker。若以后继续，优先把居中 track-window 诊断变成可量化的 causal/buffered runtime track 与同步不确定度，再研究 `optical track shell ∩ SAR response region + frozen P0 region propagation`。

## Optical shell 不确定度分解与 GT-blind shell–region 拓扑 v1（2026-08-27）

- 新版本目录：`output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/shell_uncertainty_region_topology_v1`；最终状态为 `COMPLETE_NO_NEW_PASS_FAIL_NO_P2_CLAIM`。本轮只回答光学粗方位壳的不确定度组成，以及全部 runtime optical raw-fragment shells 与冻结 C2 q90/q95/q97.5 response regions 在不看 GT 时能形成什么结构化关联；没有进入 P2、没有生成 SAR range/box、没有总分/分类器/tracker。
- 正式运行先物化全部 pre-reference 产物，再读取人工 reference：14,607 条 shell 分解、97,219 条真实像素级 edges、6,927 个 shell nodes、207,603 个 region nodes、136,391 个二部连通分量、3,582 条逐帧拓扑，之后才生成 4,518 条 reference-conditioned 解释。`pre_reference_manifest.json` 明确为 `reference_loaded=false`；运行时表中人工 `physical_target_id`、SAR reference、光学赋值 SAR range 的使用计数均为 0。
- R02 的名义 same-frame 典型帧分解为：单检测框角宽 `2.686°`，时间 union 增量 `0°`，固定每侧 ±6° guard 实际增加 `12°`，单 track 有效壳宽 `14.686°`。centered ±250 ms 的时间/视角 union 额外增加 `6.906°`，单 track 壳宽升至 `21.619°`。因此多人壳不可分不能只归因于同步；当前 guard 与时间 union 是两个独立来源。
- R02 的 `reference retention / all-track union burden`：same-frame `83.3% / 28.3%`，past-only 250 ms `91.7% / 29.0%`，buffered +100 ms `94.4% / 29.8%`，centered ±250 ms `94.4% / 31.9%`。same-frame 与 past-only 的未来观测使用数均为 0；buffered/centered 明确携带允许延迟或未来观测状态，不把 centered 诊断称作 causal online tracker。
- 当前 ±6° guard 下，R02 offline-associated shell Jaccard 为 P01/P02 `0.635`、P03/P04 `0.517`（后者只有 `4/9` 帧可同时关联两条 distinct shell）。预先固定的 ±2.652° 几何敏感性降至 `0.415/0.325`，0° raw-box 下界降至 `0/0.025`；但这些只是几何反事实，不是可部署新壳。即使 centered ±250 ms 使用 0° 下界，Jaccard 仍约 `0.492/0.505`，说明时间窗 union 本身也会重新制造重叠。
- R02 有 33 个 raw fragments、14 个 GT-blind offline parent continuity IDs，7 个 parent 含多个 fragments，单 parent 最多 10 个 fragments；same-frame 活动 raw 壳中位仅 3 个。P03/P04 的 distinct associated shells 同时可用从 same-frame `4/9` 增至 centered `7/9`，体现的不只是宽度问题，也有 fragment availability/continuity 问题。严格 runtime optical identity 仍未建立。
- shell–region edge 全部由真实像素相交生成。R02 q95 中，same-frame 与至少一个壳相交的 257 个 regions 里，211 个被至少 2 个 shells 覆盖（`82.1%`）；past-only 为 `233/273=85.3%`；centered 为 `268/307=87.3%`。因此 local region degree 已能 GT-blind 直接表达 `multiple shells → one region` 的共享歧义。
- 完整连通分量没有 `MULTIPLE_SHELLS_ONE_REGION`，不代表共享 region 不存在：相关 shells 同时还连接其它 regions，分量扩展成 `MULTIPLE_SHELLS_MULTIPLE_REGIONS`。同理没有 `SHELL_NO_REGION` 是因为 q90/q95/q97.5 是逐帧分位超水平层，每个当前壳至少会碰到某个相对高响应；这不构成 PERSON 证据。未来接口必须同时保留 component topology 与 shell/region local degree。
- R02 旧 q95 shared reference 共 34 条：same-frame 有 24 条所属 region 被多个 shells 覆盖；centered 为 30 条，且 `34/34` 均进入 multi-shell/multi-region component。P01/P02 的低 rank 被方位壳压缩后常表现为 one-shell/multi-region 或 multi-multi 搜索歧义；P03/P04 的 shared 主要表现为 multi-shell 覆盖同一局部 region，但仍不能解释为物理散射融合。
- F482/F490 的 P02 均保持 `PEAK_MISSING_REGION_PRESENT`。F482 的 P01/P02 共用 q95 `R0012`，该 region degree 为 same-frame `2`、centered `3`；F490 的 P01/P02 共用 q95 `R0012`，region degree 为 `3`。离散 peak missing 不等于连续 response missing，但 region presence 仍不能完成 identity 分离或最终定位。
- GT-blind 可直接计算的状态包括：region 层级/shape、像素相交、shell/region local degree、component topology、edge/truncation/common-FoV/display 条件，以及旧 candidate artifact 覆盖帧内的 accepted-peak-in-region。`PEAK_PRESENT`、`PEAK_MISSING_REGION_PRESENT`、PERSON `SHARED_REGION`、reference retention/rank 和 P01–P04 归因仍只属于 reference-conditioned 离线解释。
- 独立验证器 `validate_p1e_shell_uncertainty_region_topology_report.py` 不导入主分析模块，直接重算后为 `PASS (18/18)`：冻结输入哈希全部一致，398 个 region masks 聚合 SHA256 匹配，分解记录最大闭合误差 `7.105e-15°`，same-frame/past-only 无未来观测，pre-reference 顺序与哈希成立，6,927/207,603 个 node degree 零不一致，97,219 条 edge 的 component 归属零不一致，136,391 个 component 的 node/edge/topology 重算零不一致。
- 与上一轮冻结接口的 centered ±250 ms raw shells 逐项复核为 `854/854` 完全一致：宽度误差 0、有效面积误差 0、interval JSON 完全一致。HTML 共 19 个本地链接、12 张正式图，缺失/不可读均为 0。
- 分析代码 SHA256=`18AABE0BF28B71719323944366F6973B73E8F789559C275313431ECE52293027`；报告生成器 SHA256=`1990C657585A15F0F37F0777FD60D590C0CFA26AC4C385D3F9F53321671F6A42`；独立验证器 SHA256=`BE61EDDB73E7A15A050A8F947B28C5E211A67C6C43CBE30BB388ED4F6EB0B287`；HTML SHA256=`1784553864685880CACDDDB0AFA125C067039628E15C43EC256AD784E02B6A02`。
- Edge headless 1600×1100 首屏 `report_browser_qa_top.png` 已实际检查，中文、结论卡、边界说明和首图布局正常。2026-08-27 20:02 +08:00 冻结 P0 回归再次为 `18/18 PASS`。
- 当前停止点：本轮已经回答 A/B 两个基础问题，因此不机械实施 P0 region 时序传播。若未来继续，应先独立改善可验证的 runtime optical continuity、同步与 mapping uncertainty，再用同一 GT-blind topology 观察 burden/degree 是否下降；光学仍只提供 time/azimuth prior，SAR 保留 range 与最终定位权。

## 当前语义审计与 M0 docs-only 准备（2026-08-28）

- 当前状态的规范解释以 `docs/current_state_review.md` 为入口；旧 `P1E_EXPLORATORY_CONCLUSION.md` 与旧 temporal gate 只作历史记录。
- 时间、坐标、mapping、SAR geometry、P0 和 runtime/offline 字段审计：`docs/M0_TIME_COORDINATE_AND_INTERFACE_AUDIT.md`。
- 下一阶段最小研究设计草案：`docs/M0_OPTICAL_SAR_MOTION_CONSISTENCY_MINIMAL_STUDY_DRAFT.md`。
- 两份 M0 文档状态均为 `DOCS_ONLY / NOT_EXECUTED`；本轮未运行新 motion-consistency 实验，未实现 tracker、identity assignment、classifier、SAR box 或最终定位。
- 下一轮建议先做极小的 `R02 lag1 q95 support-warp pilot`：冻结一个 mask-warp contract，枚举全部 GT-blind q95→q95 compatibility edges，比较 P0/zero/matched-null，先物化再离线评价；不直接进入 tracker。
