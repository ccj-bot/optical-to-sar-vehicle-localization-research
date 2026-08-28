# 2026-08-24 PERSON 成像机理约束图像域研究日志

## 启动记录

- 启动时间：2026-08-24 10:42:26 Asia/Shanghai
- 活动工作区：D:\profile\research\workspace
- 任务目录：D:\profile\research\workspace\tasks\person_physics_guided_image_domain_study_20260824
- 输出目录：D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824
- 解释器：D:\MINICONDA\envs\py311\python.exe
- old_work：不读取、不作为运行依赖
- 原始光学、SAR图像与人工标注：只读

## 用户确认的课题方向

- 课题归入SAR成像机理和物理尺度约束下的图像域PERSON目标特征探究。
- 结合光学进行图像域、多维度和多模态研究。
- 需要把研究逻辑、阶段状态和重要边界持续记录到工作区及持久记忆。

## 本轮语义冻结

- 研究对象是条件性SAR图像观测响应，不是人体固有RCS或固定模板。
- 框轨迹不等于目标独立运动；公共表观运动不等于载体真实轨迹。
- 光学只提供时间、行为和方位搜索先验，SAR保留最终定位权。
- person_sar_motion_evidence_20260824 标记为物理运动解释无效的失败探针。

## 继承的CAR经验

- 公共场景输运必须由独立背景区域拟合，目标区域不能参与。
- 背景锚点要分拟合和留出；发现集与验证场景要分开。
- 同传感器像素不能称为固定物理背景。
- 时序一致只能作为有上限的软证据，不能生成最终目标框。

## 已建立文件

- tasks/person_physics_guided_image_domain_study_20260824/README.md
- output/person_physics_guided_image_domain_study_20260824/00_RESEARCH_CHARTER.md
- output/person_physics_guided_image_domain_study_20260824/01_P0_COMMON_APPARENT_MOTION_PROTOCOL.md
- output/person_physics_guided_image_domain_study_20260824/research_contract_v1.json

## 当前状态

- RESEARCH_CONTRACT_FROZEN
- P0_PROTOCOL_FROZEN_NOT_RUN
- 下一次运行只允许实施P0：R01发现、R04留出验证的公共表观运动可观测性测试。

## 记录与路径校验

- 任务README、研究章程、P0协议、JSON契约和日志均已确认位于D:\profile\research\workspace。
- research_contract_v1.json已通过PowerShell JSON解析：status=P0_PROTOCOL_FROZEN_NOT_RUN，old_work_dependency=false，P0=NEXT。
- 三个冻结输入的SHA256复核与契约一致，原始图像和标注未修改。
- 初次补丁曾落入D:\profile\research根目录下的同名临时任务/输出目录；5个本轮新建文件已迁回workspace，两个确认为空的临时目录已删除。
- 持久记忆增量：C:\Users\陈嘉瑜\.codex\memories\extensions\ad_hoc\notes\20260824-104226-person-physics-guided-image-domain-mainline.md。
- 本轮未运行P0计算、未生成候选、未创建或移动SAR框。

## 新Session交接

- 已生成可直接复制的新Session交接Prompt：D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\02_NEXT_SESSION_HANDOFF_PROMPT.md。
- Prompt固定P0为唯一目标，包含必读顺序、输入边界、禁止语义、R01发现/R04留出协议、通过门槛、输出清单和完成定义。
- Prompt要求默认单代理执行、减少并发，不自动进入P1，不修改原始图像或SAR框。

## P0 实施启动（2026-08-24 10:56:43 +08:00）

- 当前唯一任务：实施 P0 公共表观运动可观测性检验；完成后停止，不进入 P1。
- 当前状态：P0_PROTOCOL_FROZEN_NOT_RUN -> P0_EXECUTION_STARTED。
- 已按交接顺序完整复读任务 README、研究章程、P0 预注册协议、机器契约、本日志、GM_RM017 公共场景输运审计日志和旧失败探针摘要。
- 活动工作区：D:\profile\research\workspace；未读取或依赖 old_work。
- 解释器固定为：D:\MINICONDA\envs\py311\python.exe。
- 原始光学、SAR 图像和标注保持只读；不创建或移动 SAR 框。
- R01ZF 仅用于发现与冻结，R04ZF 仅用于冻结后的独立验证；R02ZF、R03ZF 不参与本阶段。
- 输入 SHA256 状态：待本次重新核验；若与 research_contract_v1.json 不一致则立即停止。

### P0 输入哈希门（2026-08-24）

- PASS：D:\browser\person_SAR_fullframe_interpolation_review_1787483093904.json = E3CA1F07552030F46770420EED16AEF362E9DD74C909A6BEB23C54D29F79AF8A。
- PASS：output\person_multidimensional_response_explorer_20260823\explorer_data.js = C39E60EB478FF7D815EFE6984D3BCF36600737E2EC3D1FF76D04020DED54EF7D。
- PASS：output\pseudocolor_azimuth_calibration_20260803\geometry\fan_geometry_report.json = B8A166D2ABCF57B1B3868692651D68610B5FA5B135E6D0BC48DC1D2CDB3F5A93。
- 参考探针文件也与契约哈希 5150F3EFFC884912A5A229E2FFD1F6DC011DC8BEE8297F2D4B6F3E06E7FD2801 一致，但只保留为失败探针，不进入物理运动解释。
- 输入哈希门结论：通过，允许继续 P0；没有替换任何输入。

### R01ZF 发现集完成与冻结（2026-08-24 11:12:53 +08:00）

- 运行解释器：D:\MINICONDA\envs\py311\python.exe。
- 任务代码：tasks\person_physics_guided_image_domain_study_20260824\run_p0_common_apparent_motion.py；合成平移/仿射自检 PASS。
- R01ZF：142 帧；lag 1/3/5 共 417 个预定帧对，417 个均满足固定可比较条件。
- 背景锚点严格确定性分为拟合与留出；每帧对拟合锚点中位数 203，留出锚点中位数 70。
- PERSON 扩张排除区锚点违规 0；扇面/20 m 边界排除区锚点违规 0；目标像素用于拟合/选型 0。
- R01 背景留出选型冻结：lag1=M1 全局平移；lag3=M2 全局仿射；lag5=M2 全局仿射。
- 选型只依据 R01 背景留出锚点：冻结模型留出残差中位数分别为 0.246 / 0.873 / 1.294 px，M0 分别为 2.582 / 7.987 / 13.766 px。
- 显示变化分层阈值也只由 R01 冻结，未直接归因于增益变化。
- 冻结载荷 SHA256：0F9F8D26CEDBA676ED70C9BF7DBEB9FEBD62290557FE03B0410E77B665A7A20B。
- 冻结代码 SHA256：0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8。
- R04ZF 尚未用于调参或选型；下一步只允许验证冻结配置。

## P0 完成记录（2026-08-24 11:25:08 +08:00）

### 最终判定

- `P0_PASS`
- 状态：`IMAGE_ONLY_COMMON_MOTION_OBSERVABLE_AT_PERSON_SCALE_UNDER_FROZEN_DISPLAY_DOMAIN_PROTOCOL`。
- 阶段状态：`P0_COMPLETE_STOPPED_BEFORE_P1`。
- P1：`ELIGIBLE_BUT_NOT_STARTED`；本轮严格停止在 P0，没有启动 P1 或 P2。

### R04ZF 完全留出验证

- R01 冻结载荷 SHA256：0F9F8D26CEDBA676ED70C9BF7DBEB9FEBD62290557FE03B0410E77B665A7A20B；R04 运行前已验证冻结载荷和主程序代码哈希。
- R04ZF：196 帧；lag 1/3/5 共 579 个预定帧对，579/579 均可比较；困难帧未删除。
- 相对 M0 降低背景留出残差：578/579 = 0.998273，高于预注册门槛 0.75。
- lag1 / M1：195/195 改善；M0 帧对中位残差 1.878 px，补偿后 0.191 px。
- lag3 / M2：192/193 改善；M0 帧对中位残差 6.058 px，补偿后 1.366 px。
- lag5 / M2：191/191 改善；M0 帧对中位残差 10.919 px，补偿后 2.336 px。
- 唯一背景反向帧对：R04ZF 168→171、lag3，M2 留出中位残差 4.502 px，M0 为 4.287 px；原样保留并列入失败病例。
- 显示变化分层：BASELINE 476 对、ELEVATED 45 对、HIGH 58 对；没有把变化直接归因于增益。

### 静止 PERSON 残差与敏感性

- R04 PERSON 框短轴中位数：18.504 px。
- 全部接受框：1050 个可评估 PERSON 帧对；未补偿 P90 11.143 px，补偿后 P90 3.557 px。
- 两端均为人工锚点：120 个 PERSON 帧对；未补偿 P90 12.203 px，补偿后 P90 5.029 px。
- 两个子集的中位数与 P90 均为补偿后更低，结论方向一致。
- 全部接受框最大残差：33→38、lag5、P02，11.398 px；两端为插值接受框且属于 HIGH 显示变化层。
- 人工端点最大残差：45→48、lag3、P02，10.903 px。
- 上述离群帧均未用于模型选择或调参，且仍低于 R04 PERSON 框短轴总体中位数。

### 最差帧多模态复核

- 已逐张复核背景留出残差最差 6 个帧对，以及全部接受框和人工端点各 6 个 PERSON 最差帧对。
- PERSON 扩张排除区锚点违规：0；扇面/20 m 边界排除区锚点违规：0；目标像素参与拟合：0。
- 锚点在扇面内部跨距离和方位分布；未见模型由 PERSON 框附近结构或扇面外弧/侧边主导。
- 多模态复核状态：`PASS`。详细记录：output\person_physics_guided_image_domain_study_20260824\p0_common_apparent_motion\MULTIMODAL_WORST_FRAME_REVIEW.md。

### 输出与边界

- 主程序：tasks\person_physics_guided_image_domain_study_20260824\run_p0_common_apparent_motion.py。
- 复核可视化程序：tasks\person_physics_guided_image_domain_study_20260824\render_p0_person_review_assets.py；只读取冻结结果并绘图，不重新拟合模型。
- 输出目录：output\person_physics_guided_image_domain_study_20260824\p0_common_apparent_motion；最终含 41 个文件，约 171 MB。
- 核心文件：model_selection_R01.json、frozen_validation_R04.json、common_motion_pair_metrics.csv、background_anchor_holdout_metrics.csv、stationary_person_residuals.csv、comparability_registry.csv、P0_CONCLUSION.md。
- 最终输入 SHA256 再次复核：合同中的三个冻结输入仍全部匹配；原始图像、标注和扇面几何未修改。
- 交付验证：tasks\person_physics_guided_image_domain_study_20260824\validate_p0_outputs.py 共执行 18 项检查，`validation_report.json` 状态为 `PASS`；覆盖哈希链、运行集、行数、门槛、遮罩完整性和全部图像可读性。
- 未读取或依赖 old_work；未创建或移动 SAR 框；未修改原始光学/SAR图像或标注；未 commit、未 push。
- 语义边界保持：公共表观运动不是载体真实轨迹；SAR框轨迹不是目标独立运动；PERSON响应不是人体固有RCS模板；旧 person_sar_motion_evidence 仍为失败探针。

## P0 解释层补充启动（2026-08-24）

- 用户要求把现有判定补成“总体问题—理论推导—实际计算—指标—结果含义—失败病例”的完整研究叙事。
- 本次只读取已冻结的 R01/R04 产物，生成总览图与说明文档；不重新拟合、不修改冻结主程序、不调整 P0 门槛或结论。
- 绘图脚本：tasks\person_physics_guided_image_domain_study_20260824\render_p0_research_overview.py。
- 解释器：D:\MINICONDA\envs\py311\python.exe。
- 预定输出：output\person_physics_guided_image_domain_study_20260824\p0_common_apparent_motion\visualizations\P0_RESEARCH_OVERVIEW.png，以及同目录下的 P0_THEORY_METHOD_RESULTS_OVERVIEW.md。
- 继续保持 P0_COMPLETE_STOPPED_BEFORE_P1；不创建或移动 SAR 框，不进入 P1。

## P0 解释层补充完成（2026-08-24）

- 已生成完整说明：output\person_physics_guided_image_domain_study_20260824\p0_common_apparent_motion\P0_THEORY_METHOD_RESULTS_OVERVIEW.md。
- 已生成并人工检查一页总览图：output\person_physics_guided_image_domain_study_20260824\p0_common_apparent_motion\visualizations\P0_RESEARCH_OVERVIEW.png。
- 说明按“验证对象与非对象—理论分解—操作性可观测定义—有效区和背景锚点—M0/M1/M2/M3—R01冻结—R04指标—静止PERSON残差—失败病例—解释边界”组织。
- 总览图直接包含唯一背景反向帧对 168→171（lag 3），没有用汇总统计遮蔽失败病例。
- 本次只读取冻结产物；`model_refit=false`。冻结主程序 SHA256 仍与 R01 记录一致，未修改 `run_p0_common_apparent_motion.py`。
- 再次运行既有交付校验：18/18 checks，`validation_report.json = PASS`；新增总览图可读，报告内图像链接均存在。
- P0 最终结论仍为 `P0_PASS`；P1 仍为 `ELIGIBLE_BUT_NOT_STARTED`，没有自动进入 P1。
- 未读取或依赖 old_work；未修改原始图像、标注或扇面几何；未创建或移动 SAR 框；未 commit、未 push。

## P0 背景残差与 lag 交互式 HTML 说明启动（2026-08-24）

- 用户反馈仍不清楚“背景是什么、背景残差用来做什么、lag 是什么、各层指标说明什么”，要求从操作层讲透并交付 HTML 报告。
- 本次只读取 P0 已冻结 JSON/CSV 和现有失败帧图，抽取真实 HOLDOUT 背景锚点作为逐项算例；不重新追踪锚点、不重新拟合模型、不调整 R01/R04 结论。
- 解释器：D:\MINICONDA\envs\py311\python.exe。
- 任务脚本预定：tasks\person_physics_guided_image_domain_study_20260824\render_p0_explained_html.py。
- HTML 预定输出：output\person_physics_guided_image_domain_study_20260824\p0_common_apparent_motion\P0_BACKGROUND_RESIDUAL_EXPLAINER.html。
- 继续保持 `P0_COMPLETE_STOPPED_BEFORE_P1`；不进入 P1，不创建或移动 SAR 框。

## P0 背景残差与 lag 交互式 HTML 说明完成（2026-08-24）

- 已生成 HTML：output\person_physics_guided_image_domain_study_20260824\p0_common_apparent_motion\P0_BACKGROUND_RESIDUAL_EXPLAINER.html。
- 生成脚本：tasks\person_physics_guided_image_domain_study_20260824\render_p0_explained_html.py；只读取冻结 JSON/CSV，`model_refit=false`，无外部网络依赖。
- 报告共 13 个解释章节，重点区分背景位移 `d`、公共模型预测 `u_hat(x)` 和背景残差 `||d-u_hat(x)||`；明确背景由有效区内的稀疏局部梯度锚点及其位移向量描述，不是语义背景类别或平均颜色模板。
- 已解释 lag 为帧索引间隔而非秒数：R04 196 帧对应 lag1=195 对、lag3=193 对、lag5=191 对；这些帧对存在重叠，不声称统计独立。
- HTML 从 `background_anchor_holdout_metrics.csv` 嵌入真实 HOLDOUT 锚点：典型 lag1/3/5 和唯一反向帧对 168→171；可切换小残差、接近中位数和最大残差锚点。
- 默认真实算例：R04 6→7、lag1、M1，锚点观测 (1.963,-0.076) px，预测 (1.789,-0.157) px，残差向量 (0.173,0.080) px，残差长度 0.191 px；M0 下该锚点残差为 1.964 px。
- 图中坐标已明确采用图像约定：`+dx` 向右，`+dy` 向下。
- 浏览器自动化验收：4 个帧对按钮、3 个锚点按钮和 3 行真实锚点表均成功生成；失败案例最大锚点切换后显示 15.797 px；页面脚本错误 0，本地图片 4/4 可读，横向溢出 0。
- 视觉验收图：visualizations\P0_BACKGROUND_RESIDUAL_EXPLAINER_preview.png 和 visualizations\P0_BACKGROUND_RESIDUAL_EXPLAINER_residual_section.png。
- 再次运行既有 P0 校验：18/18 checks，`validation_report.json = PASS`；冻结主程序 SHA256 仍与 R01 记录一致。
- P0 结论不变：`P0_PASS`；P1 仍为 `ELIGIBLE_BUT_NOT_STARTED`。未读取或依赖 old_work，未修改原始图像/标注，未创建或移动 SAR 框，未 commit、未 push。

## P0 后深化研究方案与独立审阅启动（2026-08-25）

- 用户要求先形成深化研究方案，再开启独立子路径审阅，收到意见后再做本地证据研究。
- 当前状态限定为 `POST_P0_RESEARCH_PLANNING_ONLY`；本轮不运行 P1，不修改 P0 冻结模型或结论，不自动进入 P2。
- 已形成审阅前草案：output\person_physics_guided_image_domain_study_20260824\03_POST_P0_DEEPENING_RESEARCH_PLAN_DRAFT.md。
- 草案路线：B0 P0→P1桥接审计；P1A测量定义与可靠性；P1B条件响应发现；P1C完整run留出确认与P2资格门。
- 独立审阅子路径：`independent_post_p0_review`；要求不预设结论、不修改草案、不运行实验，并把意见写入 04_INDEPENDENT_REVIEW_OF_POST_P0_PLAN.md。
- 活动目录：D:\profile\research\workspace；解释器仍为 D:\MINICONDA\envs\py311\python.exe；old_work 不读取、不依赖。

## P0 后深化方案独立审阅完成（2026-08-25）

- 审阅输出：output\person_physics_guided_image_domain_study_20260824\04_INDEPENDENT_REVIEW_OF_POST_P0_PLAN.md。
- 独立结论：`MAJOR_REVISION_REQUIRED`；草案可作为探索骨架，但当前不能作为 P1 确认性协议或 P2 资格门。
- 关键证据：现有 R01/R02/R03/R04 四个 run 均已在既有多维探索中查看并形成 PERSON 响应假设，不存在真正未暴露的 P1 确认 run；当前条件也与 run 高度混杂。
- 关键风险：852 个接受框中 251 个为人工原生框、600 个为线性插值框，框条件测量存在循环与运行时不可用风险；全部 398 帧的光学—SAR同步仍未验证，现有数据没有冻结的 behavior 字段。
- 建议路线：现有四个 run 全部降为开发/探索语料，先做来源/暴露/适用域审计和少量 SAR-only 测量定义；真正 P1 确认需新的封存独立 run。没有新数据时应停在 `P1_EXPLORATORY_ONLY_NO_BLIND_CONFIRMATION`，不得开放 P2。
- 本子路径只读核验现有章程、协议、P0结论、失败病例、契约与当前探索元数据；未运行 P1、未重新拟合 P0、未修改草案、未读取 old_work、未修改原始图像或标注、未创建或移动 SAR 框。

## 独立审阅后的本地证据研究启动（2026-08-25 11:23:49 +08:00）

- 独立审阅已返回 `MAJOR_REVISION_REQUIRED`；本轮只研究并核实现有数据能支持到哪里，不启动 P1 特征实验，也不把既有四个 run 重新包装为盲验证集。
- 预定输出：`output\person_physics_guided_image_domain_study_20260824\05_POST_REVIEW_LOCAL_EVIDENCE_AUDIT.md` 与 `06_POST_P0_DEEPENING_RESEARCH_PLAN_REVISED.md`。
- 核验重点：run/target/frame 规模、框来源、既有数据暴露、同步与 behavior 字段、人工端点在 lag 1/3/5 中的覆盖，以及条件与 run 的混杂。
- 活动目录固定为 `D:\profile\research\workspace`；解释器固定为 `D:\MINICONDA\envs\py311\python.exe`；不读取或依赖 `old_work`。
- 原始光学、SAR 图像和标注只读；不创建、移动或修正 SAR 框；不修改 P0 冻结模型和结论；不 commit、不 push。

## 独立审阅后的本地证据研究完成（2026-08-25 11:32:44 +08:00）

### 本地核验结论

- 合同三个冻结输入 SHA256 再次核验 3/3 匹配；没有替换输入。
- 复核规模：4 个 run、398 帧、11 个 run 内 PERSON ID、852 个接受框；原生人工框 251、线性插值框 600、人工调整插值框 1。
- 既有 `RESEARCH_INTERPRETATION_V2.md` 第 9–14、31–61、86–90 行已分别赋予四个 run 发现/失败病例角色并形成后续假设，因此 R01/R02/R03/R04 均为已暴露语料，不能重新命名为 P1 盲确认集。
- 人工—人工端点对（lag 1/3/5）：R01=4/20/72，R02=12/8/8，R03=0/0/0，R04=4/37/79。lag 与框来源/人工标注间隔明显混杂；不得把跨 lag 差异直接解释为 PERSON 时序或动力学规律。
- 398/398 帧同步状态均为 `NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED`；frame 和 694 条 optical-person 记录中均无 behavior 字段。光学行为已移出 P1 确认性核心。
- 条件与 run 高度绑定：R01 最近 PERSON 约 11.79 px；R02 23 帧/四人并含既有显示跳变病例；R03 17.53–19.11 m、距 20 m 边界约 0.60–2.10 m；R04 长时序且目标较分离。

### 方案修订

- 初稿 `B0 → P1A → P1B → P1C` 修订为 `B0R → P1E → P1-FREEZE → P1V`。
- 现有四个 run 全部只用于 P1E 探索开发；真正 P1V 必须使用新的封存 acquisition group。
- 主测量族限制为两类：单帧位置特异性、冻结 P0 与局部误差预算下的时序一致性。
- 原生人工框作为离线主评价；插值框只做覆盖与敏感性；真实框中心、宽高和 `physical_target_id` 不得成为运行时输入。
- 没有新盲数据时，最高状态为 `P1_EXPLORATORY_ONLY_NO_BLIND_CONFIRMATION`；P2 保持 `BLOCKED`。

### 新增与更新文件

- `tasks\person_physics_guided_image_domain_study_20260824\audit_post_p0_local_evidence.py`
- `output\person_physics_guided_image_domain_study_20260824\05_POST_REVIEW_LOCAL_EVIDENCE_AUDIT_DATA.json`
- `output\person_physics_guided_image_domain_study_20260824\05_POST_REVIEW_LOCAL_EVIDENCE_AUDIT.md`
- `output\person_physics_guided_image_domain_study_20260824\06_POST_P0_DEEPENING_RESEARCH_PLAN_REVISED.md`
- 已更新任务 `README.md` 记录审后路线和当前门控状态。

### 校验与停止状态

- 使用 `D:\MINICONDA\envs\py311\python.exe` 重新运行审计脚本，机器可读结果与合同计数、同步状态、behavior 字段审计和 12 组 lag 人工端点计数全部一致。
- `POST_REVIEW_VALIDATION PASS`；既有 P0 `validation_report.json` 仍为 `PASS`；没有生成任何 `P1*` 结果目录或文件。
- 本轮未运行 B0R 的 R02/R03 公共运动适用域计算，未运行 P1 特征实验，未进入 P2，未修改 P0，未读取 `old_work`，未修改原始图像或标注，未创建或移动 SAR 框，未 commit、未 push。
- 下一项建议任务仅为 B0R-2/B0R-3：用冻结 P0 配置检查 R02/R03 背景可比性与目标位置局部误差预算；等待单独授权。

## B0R 最小适用域与 P1E 响应接口探索启动（2026-08-25 18:45:45 +08:00）

- 用户已授权先完成最低必要 B0R，随后直接进入 P1E 单帧位置特异性探索；`06_POST_P0_DEEPENING_RESEARCH_PLAN_REVISED.md` 为主要边界，但候选公式不作为唯一实现。
- 研究目标：尽快建立或否定一个可在 SAR 有效区域任意位置 `x` 运行时计算的 PERSON 条件性响应分数 `S(x)`；真实框中心、宽高和 `physical_target_id` 只用于离线评价。
- B0R 只使用冻结 P0 配置前向检查 R02/R03，不重选模型、不调参数；只决定哪些帧对/位置可做时序，哪些只能单帧或必须弃权。
- P1E 先看真实 SAR 图像与响应图，只比较少量有物理/几何解释的候选；必须包含匹配背景、局部硬背景和固定径向/切向偏移对照以及成功/失败病例。
- 若单帧位置特异性未建立，不以复杂时序模型掩盖；只在单帧直接证据成立后运行最小时序一致性。
- 活动目录：`D:\profile\research\workspace`；解释器：`D:\MINICONDA\envs\py311\python.exe`；输出限定到本研究任务目录。
- 冻结输入 SHA256 重新核验 3/3 通过；冻结 P0 主程序 SHA256 仍为 `0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8`。
- 不读取或依赖 `old_work`；不修改原始图像、标注、P0 冻结代码或冻结结论；不创建、移动或修正 SAR 框；不 commit、不 push。

## B0R/P1E 交付收口与 P0 回归验证启动（2026-08-25）

- 当前只收口已经完成的最低必要 B0R、独立审核修正和 P1E 单帧探索；不再增加候选、不进入补偿后时序、不授予 `P1_PASS`。
- 权威单帧结果限定为 `p1e_sar_only_response_interface\single_frame\manual_v4_physical_scale_p0_mask`；早期 `manual`、`manual_v2_fixed_support`、`manual_v3_p0_mask_fixed_support` 保留为审核过程证据，不删除、不冒充当前结果。
- 已复核冻结 P0 主程序 SHA256：`0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8`，与 R01 冻结记录一致。
- 已检查最终 HTML 的本地引用和图片可读性：21 个本地引用、8 幅嵌入证据图，缺失或不可读为 0。
- 下一项仅运行既有 `validate_p0_outputs.py` 的 18 项回归检查，确认 P1E 工作没有改变 P0；解释器仍为 `D:\MINICONDA\envs\py311\python.exe`。

## B0R 最低门控与 P1E 单帧探索完成（2026-08-25）

### 最低必要 B0R

- 状态：`B0R_MINIMAL_COMPLETE_NO_P0_RETUNING`；只对 R02ZF/R03ZF 前向应用冻结 P0，lag1/3/5 仍分别使用 M1/M2/M2。
- R02ZF 目标位置可做时序/不可比较/背景支持不足：lag1=`56/32/0`，lag3=`19/61/0`，lag5=`0/68/4`。
- R03ZF：lag1=`7/29/0`，lag3=`1/33/0`，lag5=`0/32/0`。
- B0R 已足够决定“哪里允许以后做时序、哪里只能单帧或弃权”，不继续无限扩展审计；局部误差预算只是冻结模型在邻近留出背景锚点上的经验残差，不解释为严格校准置信上界。
- B0R 没有使用真实目标位移设定预算，没有让 PERSON 区域参与拟合或模型选择，没有重新调 P0，也没有创建或移动 SAR 框。

### 独立审核与评价修正

- 独立审核首先否定了首轮结果可直接成为接口，指出三项关键偏差：9 px 邻域最大值导致饱和；P1E 有效掩膜宽于冻结 P0；响应尺度间接来自 PERSON 框短轴。
- 当前权威实验已逐项修正：主分数改为固定 `0.30 m` 支持盘均值；有效区直接复用冻结 P0 掩膜；响应尺度固定为 `0.30/0.55/0.90 m` 并由扇面几何换算，不读取 PERSON 框宽高。
- 参考位置、米制匹配背景、固定径向/切向偏移和局部硬背景使用同一 `S(x)` 算子；另报告硬背景池 P90/P95/最大值和局部峰到参考位置距离。
- 新增且只新增一个结构候选 C3：Hessian 紧凑亮核加结构张量长脊惩罚；没有继续堆积特征。

### P1E 单帧直接证据

- 权威目录：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\single_frame\manual_v4_physical_scale_p0_mask`。
- 数据规模：112 帧、251 个原生人工框、4 个候选；240 个可评价，11 个因冻结 P0 支持区不足明确弃权。
- 首选探索候选 C2：总体胜最强硬背景 `85.4%`，中位 `Delta_hard=0.187`，中位 `Delta_hard-P95=0.329`，峰距中位/P90=`0.132/0.452 m`。
- C2 跨 run：R01=`96.8%`，R02=`47.2%`，R03=`100%`（仅 2 个可评价人工框），R04=`88.0%`。
- 独立从逐框 CSV 复算确认：R02 的 C2 对最强硬背景中位优势约 `-0.017`，峰距中位/P90=`0.570/0.633 m`；P01/P02 的目标级中位 `Delta_hard` 分别为 `-0.153/-0.070`。
- C3 能修复 R04 F90 一类“原图有亮核但旧顶帽漏检”的表示问题，却不能修复 R02 多人/长亮链，也会压低部分延展真实响应，因此只保留为结构诊断候选。
- 最清楚成功病例：R04 F100/P03；条件性成功：R02 F490/P03；表示修复：R04 F90/P03。
- 决定性失败：R02 F472/P01 多人亮链、R02 F494/P01 不可分辨长链、R04 F32/P02 延展结构；R03 F458 正确弃权，R03 F494 进入有效区后恢复但样本极少。

### 当前研究判断与停止边界

- 状态：`P1E_SINGLE_FRAME_CONDITIONAL_SIGNAL_FOUND_BUT_NOT_STABLE_ENOUGH_FOR_INTERFACE_FREEZE`。
- 目前可以生成运行时可计算的 SAR-only `S(x)`，且孤立紧凑响应具有位置优势；但不能形成跨条件稳定、可直接承担后续定位的通用接口。
- 主要阻断是多人/长亮链条件下 PERSON 条件响应与场景强散射缺乏可分离的位置结构，并伴随约 `0.6 m` 的峰位漂移；空间分辨/场景融合是主因，表示问题只解释部分失败，显示链可能限制信息但不是唯一原因。
- 因单帧一般位置特异性未建立，本轮不进入补偿后时序，不运行全部插值框敏感性，不冻结 P1 接口，不授予 `P1_PASS`，P2 继续 `BLOCKED`。

### 交付与回归验证

- HTML：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\P1E_SAR_ONLY_RESPONSE_INTERFACE_REPORT.html`。
- Markdown：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\P1E_EXPLORATORY_CONCLUSION.md`。
- HTML 本地证据链检查：21 个本地引用、8 幅嵌入证据图，缺失或不可读为 0；顶部浏览器截图布局正常。
- 重新运行冻结 P0 交付验证：`18/18`，`validation_report.json = PASS`；生成时间 `2026-08-25T20:22:54+08:00`。
- 冻结 P0 主程序 SHA256 仍为 `0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8`；合同三个输入 SHA256 仍全部匹配，没有替换输入。
- 未读取或依赖 `old_work`；未修改原始光学/SAR 图像、标注或冻结 P0；未创建、移动或修正 SAR 框；未 commit、未 push；现有脏 worktree 中无关文件保持原样。

## B0R/P1E 代码打包启动（2026-08-26 12:42:00 +08:00）

- 用户要求打包上次执行的全部代码。本次只复制代码、冻结依赖和复现所需的小型协议/配置，不重新运行研究、不修改源文件。
- 打包范围采用完整任务代码超集：任务目录内全部 Python 脚本；另附任务 README、06 号研究边界、研究契约、P0 冻结模型记录、B0R/P1E 机器汇总和探索结论，避免遗漏隐式依赖。
- 明确不包含原始光学/SAR 图像、原始标注、`old_work`、大体积逐锚点/逐框 CSV、中间响应图和浏览器缓存。
- 输出限定到 `output\person_physics_guided_image_domain_study_20260824\code_packages`；解释器仍以 `D:\MINICONDA\envs\py311\python.exe` 为复现默认环境。
- 将生成独立目录、README、SHA256 清单和 ZIP，并在交付前直接读取 ZIP 内容复核每个文件哈希。

## B0R/P1E 代码打包完成（2026-08-26）

- 未压缩目录：`output\person_physics_guided_image_domain_study_20260824\code_packages\PERSON_P0_B0R_P1E_CODE_20260826`。
- ZIP：`output\person_physics_guided_image_domain_study_20260824\code_packages\PERSON_P0_B0R_P1E_CODE_20260826.zip`。
- ZIP 大小：146655 bytes；SHA256：`07249455A72D1F4572EFED4A2A37E0B85923A8116ECCFAE98117698FDE83C15F`。
- ZIP 外部校验文件：`PERSON_P0_B0R_P1E_CODE_20260826.zip.sha256.txt`。
- 包内包含任务目录全部 9 个 Python 脚本；代码副本与当前源文件逐一比较，SHA256 不一致数为 0。
- 另含任务 README、章程/P0 协议/研究契约、04–06 审核与研究边界、P0 冻结选型及验证报告、B0R/P1E 权威小型汇总和 P1E 探索结论；清单主体共 23 个文件、434807 bytes。
- ZIP 内部验证：36 个目录/文件条目；23 个清单文件逐一验哈希通过；9 个 Python 文件全部通过 AST 语法解析；7 个 JSON 文件全部可解析；危险绝对/父目录条目 0；`old_work` 条目 0；最终状态 `PASS`。
- 原始光学/SAR 图像、标注、大体积 CSV、响应图和中间产物没有进入代码包；没有修改任何源代码、原始数据或 SAR 框；未 commit、未 push。

## P1E 候选存在性—唯一定位性语义拆分启动（2026-08-26）

- 本轮保留冻结 P0、既有 B0R、C0–C3 和全部旧 P1E 结果；只新建 `candidate_recall_semantic_split_v1` 版本目录。
- 代码审阅确认 C0–C3 响应图生成没有使用 PERSON 框中心/宽高、`physical_target_id` 或光学轨迹；语义问题位于评价解释，而不是现有 `S(x)` 的运行时输入边界。
- 现有 hard-background 指标改释为“局部竞争响应池”；局部峰距只表示算子高分位置相对人工框几何中心的偏移，不直接解释为空间分辨率或真实散射中心误差。
- 已在查看新 Recall@K 结果前冻结协议：`00_CANDIDATE_RECALL_PROTOCOL_FROZEN_BEFORE_RUN.md`。固定 C2/C3、`K=1/2/3/5`、`r=0.3/0.5/0.8 m`、局部极大值半径 `0.30 m`、NMS 间距 `0.45 m` 和单帧支持状态规则。
- `Omega_single_v1` 使用真实扇面外缘/侧边与固定支持有效比例；`Omega_temporal` 仍严格受冻结 P0 和局部背景误差预算约束。
- 冻结 P0 主程序 SHA256 仍为 `0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8`；解释器为 `D:\MINICONDA\envs\py311\python.exe`。
- 不读取或依赖 `old_work`，不修改原始图像/标注，不创建或移动 SAR 框，不 commit/push。

## P1E 候选召回语义拆分收口启动（2026-08-26）

- 接续已完成的 GT-blind 候选生成，不重新生成候选、不修改冻结 P0、B0R、C0–C3 或旧 P1E 结果。
- 本次只基于既有 CSV 增加 any-rank 共享候选解释层，区分候选存在、全局 rank 竞争、疑似共享响应与边界/截断；`response_merging_suspected` 仅作图像域诊断，不解释为物理融合证明。
- 将重绘重点病例，局部图只显示实际落入裁剪区的候选；全局图仅标 Top-5，局部图标出参考附近的相关候选 rank。
- 预注册时序入口规则保持不变；若门槛不通过，本轮不运行 lag1/lag3 时序。
- 活动目录为 `D:\profile\research\workspace`；解释器为 `D:\MINICONDA\envs\py311\python.exe`；不读取 `old_work`，不修改原始图像/标注，不创建或移动 SAR 框，不 commit/push。

## P1E 候选存在性—唯一定位性语义拆分完成（2026-08-26）

### 实现与语义边界

- 代码审阅确认 C0–C3 响应图先由 SAR 图像、扇面几何、固定物理尺度和运行时有效掩膜生成；候选提取与缓存发生在人工 annotation 枚举之前。真实框、`physical_target_id`、光学/插值轨迹没有进入 `S(x)` 或候选生成。
- 没有重跑 GT-blind 候选生成；新增 `render_p1e_candidate_recall_semantic_report.py` 只读取既有候选/Recall CSV，增加 any-rank 共享候选解释层并重放固定响应图用于病例可视化。
- 新解释把三层问题分开：任意局部峰存在、固定 Top-K 短名单召回、单帧唯一定位。旧 hard-background 改释为 `local competing-response pool`；旧峰距只解释为算子高分位置相对人工框几何中心的偏移。
- `response_merging_suspected_any_rank` 定义为同一 GT-blind 候选落入多个 reference 的 0.8 m 邻域；只作图像域共享响应诊断，不作为物理融合证明。

### R02 C2 结果

- Recall@1/3/5(0.8 m)：`27.8% / 44.4% / 44.4%`；Top-5 相对 Top-1 恢复 `16.7` 个百分点，Top-3 到 Top-5 没有继续恢复。
- P01：0.8 m 内任意峰 9/9，Top-5 0/9，最近候选 rank 中位数 14、范围 7–24；7/9 帧存在某个与其他 PERSON reference 共享的半径内候选，其中 3/9 的最佳半径内候选本身共享。
- P02：0.8 m 内任意峰 7/9，Top-5 0/9，最近 rank 中位数 14；2/9 为半径级候选缺失/当前表示未捕捉；7/9 存在共享候选，且 7/9 的最佳半径内候选共享。
- P03/P04：各 8/9 进入 Top-5、5/9 为 Top-1；9/9 存在共享候选，且 9/9 的最佳半径内候选共享。主要问题是共享响应与唯一性，而不是候选完全缺失。
- R02 C2 每帧候选数为 219–327，中位数 294；因此“参考附近有任意峰”只是原始峰场存在性，不等于进入全扇面 Top-5 操作短名单。
- 四方向 1.25 m 固定偏移的 Recall@5(0.8 m) 均为 0，reference 相对固定偏移仍有正覆盖优势。

### C3、边界与时序决定

- C3 没有修复 P01/P02：Recall@5 均为 0，最近候选 rank 中位数约 121/99；继续只作结构诊断。
- `Omega_single_v1` 将单帧观测与 P0 时序可靠域拆开。R03 四个人工 reference 均为 FULL；F458 约 0.021 m 处有 C2 峰但 rank=18，F462 约 0.102 m/rank13，F488 约 0.086 m/rank5，F494 约 0.111 m/rank6。
- F458/F462 在旧 frozen-P0-mask P1E 中为 `ABSTAIN_LOW_VALID_SUPPORT`，新结果证明“P0 不可比较不等于单帧不可观察”，但 F458/F462 仍未进入 Top-5。
- 预注册时序入口：Recall@5>=60% 失败；Top5-Top1>=20 个百分点失败；reference 相对固定偏移优势通过；P01/P02 至少一者 Recall@5>=50% 失败。四项中三项失败，因此没有运行 lag1/lag3，也没有创建任何时序结果文件。
- 本轮不能回答冻结 P0 输运是否改善候选 rank，也不能声称时序提供新增信息；该问题保持未检验，而非阴性结论。

### 输出与验证

- HTML：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\candidate_recall_semantic_split_v1\P1E_CANDIDATE_RECALL_SEMANTIC_SPLIT_REPORT.html`。
- Markdown：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\candidate_recall_semantic_split_v1\01_CANDIDATE_RECALL_SEMANTIC_INTERPRETATION.md`。
- 解释层 CSV：`single_frame_candidate_recall\manual_reference_candidate_interpretation_v2.csv`；机器总结：`candidate_semantic_interpretation_v2.json`；病例索引：`case_registry_v2.csv`。
- 新版可视化：1 幅 Recall@K 汇总图和 8 幅真实 SAR/全局响应/局部响应/候选覆盖病例图；局部图不再绘制裁剪区外候选标签。
- 报告自检：17 个本地引用缺失 0，9 幅被校验图片不可读 0，`report_validation.json = PASS`；Edge headless 顶部截图布局正常。
- 独立一致性复核 13/13 通过：502 行解释记录、88,153 个 GT-blind 候选、126 个处理帧、NMS 最小间距 0.451 m、R02 Recall 和分目标结论均与原始 CSV 一致，未发现时序结果文件。
- 合同三个冻结输入 SHA256 3/3 匹配；失效探针引用哈希也匹配但仍仅允许显示重复性失败探针语义。
- 冻结哈希保持：P0=`0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8`；旧 P1E C0–C3=`98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1`；B0R=`3C0DFB20B58D445D224DAD7426AEB0E6DA5E065DB07059B462F1FE528CFC8ABF`。
- 再次运行冻结 P0 回归验证：`18/18`，`validation_report.json = PASS`。
- 旧结论已作语义修正但旧文件不删除：P01/P02 不能写成 PERSON 响应完全不存在，而应写成参考附近常有低 rank 原始峰、未进入高响应 Top-5，且 P02 混有少量候选缺失；P03/P04 为候选召回成立但共享响应/唯一性不足。
- 未修改冻结 P0、B0R、C0–C3 或旧 P1E 结果；未读取 `old_work`，未修改原始图像/标注，未创建或移动 SAR 框，未 commit、未 push；P2 继续 `BLOCKED`。

## P1E 动态证据最小时序信息增益实验启动（2026-08-26）

- 用户明确取消“单帧达到某 gate 才允许进入时序”的阶段式逻辑；候选召回语义拆分完整保留，时序改为可逆的动态证据状态研究。
- 主问题：低 rank 候选能否在冻结 P0 公共输运下获得持续支持；高 rank 共享候选能否分裂/分离；正确 P0 是否相对无输运、反向/扰动和帧间打乱产生新增信息。
- 已只读复核实际接口：R02 有 F472–F494 共 23 帧、22 个 lag1 pair，冻结模型均为 M1；每帧现有 GT-blind C2 候选约 219–327。B0R 已提供逐 pair 模型参数、背景留出锚点残差和全局 P90，可在任意候选位置建立 GT-blind 局部不确定区域。
- 在查看时序结果前新增协议：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\dynamic_evidence_temporal_v1\00_DYNAMIC_EVIDENCE_MINIMAL_TEMPORAL_PROTOCOL_FROZEN_BEFORE_RUN.md`。
- 协议不设置研究资格 gate；只冻结数值稳定参数、证据向量、五个对照和离线评价。候选不按 Top-5/Top-20 截断，manual reference 只在完整节点/边/线程生成后加载。
- 活动目录：`D:\profile\research\workspace`；解释器：`D:\MINICONDA\envs\py311\python.exe`；不读取 `old_work`，不修改冻结 P0/B0R/C0–C3/旧 P1E，不修改原始图像或标注，不创建或移动 SAR 框，不 commit/push。

## P1E 动态证据 lag1 实验与独立审阅收口（2026-08-26）

### 执行与运行时边界

- 已完成 R02ZF F472–F494 的 lag1 动态证据图：23 帧、22 个可比较 pair、6,457 个未截断 GT-blind C2 节点、52,926 条 3σ 边、17,129 条互为最近邻边。
- 没有使用单帧 Recall gate 决定是否研究时序，也没有强制 Top-5；候选节点、时序边和线程只使用 SAR 响应、候选位置、扇面几何、冻结 P0 和候选位置的局部 P0 设计容差。
- reference/ID/固定偏移仅在完整图生成后用于离线评价。准确审计结论是“reference 内容没有参与图计算”；reference CSV 字节在图前被哈希、含 annotation 字段的 explorer 容器在图前整体加载，因此不声称严格 sealed-data process isolation。
- 冻结 P0、B0R、C0–C3、候选召回结果和旧 P1E 结果均未修改；动态图实验没有读取 `old_work`，没有修改原始图像/标注，没有创建或移动 SAR 框，没有 commit/push。

### 科学结果

- 审阅后状态收紧为 `TEMPORAL_STRUCTURE_PRESENT_P0_SPECIFIC_GAIN_NOT_ESTABLISHED`。
- 能确认：真实序列中存在持续 SAR 响应结构，反向、0.75 m 切向 gross 扰动和错误帧序会破坏一部分结构；部分低 rank 候选在某些帧获得时序支持。
- 不能确认：正确 P0 相对 `ZERO_TRANSPORT` 带来稳定的特异信息增益。reference incoming max/sum 的中位优势均仅 1.5 名；mean 中位优势为 0，83.3% 配对持平。
- 全部节点的 CORRECT-vs-ZERO rank Spearman 中位：max=0.9756、sum=0.9794、mean=0.9916；2σ 互为最近邻边重合 95.96%，Jaccard=0.921；线程长度 73.8% 完全相同，shared state 32/32 一致。
- 冻结 lag1 位移中位约 0.103 m，而局部 σ 中位约 0.301 m，仅约 0.34σ；zero transport 通常仍位于同一可能区域，这是当前 P0-specific 可分性不足的直接尺度解释。
- P01 相对单帧有局部恢复；P02 高度异质，相对 zero 仅 2/6 个可评价帧更好。P02 F482 在 0.8 m 内缺节点；F490 最近节点约 0.820 m，属于固定半径边界病例。
- P03/P04 在 0.8 m 邻域下持续 `SHARED`，但该半径与两人 0.695–0.808 m 间距重叠，只能解释为邻域共享/当前未观察到分离，不能当作物理融合或身份不可分证明。
- F490/F494 的 max/sum 严重降级，但 mean rank 仍为 2–3、线程长仍为 23；各证据分量必须并列解释，不能把 incoming max/sum 当成 posterior 或将其失败写成“所有时序量共同失败”。

### 独立审阅与复现缺口

- 全节点比较进一步确认 CORRECT 与 ZERO 高度相似；`TANGENTIAL_PLUS_0_75M` 和单一 shift7 shuffle 仅为 gross sanity，不是校准 null。
- 6,147 个 source-node uncertainty row 中，nearest-8 fallback 占 22.45%；39.74% 至少一个距离/方位维度未被背景锚点双侧包围；σ 是设计容差，不是校准置信区间。
- 30 个可评价 reference 行只对应 20 个 unique `(frame, best node)` outcome；`SHARED` 与 reference 配对统计不能按 30 个独立身份结果解释。
- 已记录但没有修改原动态图的复现缺口：`best_support_normalized_error` 合并字段有 `_x/_y` 与无后缀混合；动态图脚本/协议、fixed-offset source、B0R comparability 未全部进入原 runtime manifest 的预运行冻结哈希；动态图代码未 assert/filter `pair_comparable`，但本次 R02 lag1 为 22/22 True。

### 输出与验证

- HTML：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\dynamic_evidence_temporal_v1\P1E_DYNAMIC_EVIDENCE_TEMPORAL_REPORT.html`。
- Markdown：`01_DYNAMIC_EVIDENCE_TEMPORAL_INFORMATION_GAIN_REPORT.md`；独立方法审阅：`02_DYNAMIC_EVIDENCE_METHOD_AUDIT.md`。
- 机器解释：`lag1_r02\post_analysis_v1\dynamic_evidence_interpretation_v1.json`；逐 reference 配对、固定偏移、显示分层与病例索引均位于同一 `post_analysis_v1`。
- 报告生成器：`tasks\person_physics_guided_image_domain_study_20260824\render_p1e_dynamic_evidence_temporal_report.py`；重新编译并运行成功，没有重跑动态图实验。
- 报告自检 `PASS`：13/13 检查通过；21 个本地引用缺失 0；12 幅检查图片不可读 0；7 个直接病例齐全；Edge headless 首屏布局正常。
- 2026-08-26 16:40:39 +08:00 再次运行冻结 P0 回归：18/18 PASS；`research_contract_v1.json` 三个输入 SHA256 3/3 匹配，没有替换输入。
- 本轮不授予 `P1_PASS`，不声称盲验证，不自动进入复杂跟踪。若继续，最小后续应预先固定 lag3/两步接续和显式 missing-state bridge，并继续对比 correct、zero、错误输运和打乱帧，不恢复单帧资格 gate。

## PERSON-SAR 观测模型重构与最小诊断启动（2026-08-26）

- 用户要求暂停“继续增加 lag / 增强单帧特征”的惯性路线，不新增 C4/C5，不直接套复杂 tracker；本轮改为分解 SAR 条件性响应的图像、物理/几何、显示、P0、时序、光学软先验和歧义状态。
- 首要任务是完整阅读并追溯当前 P0、B0R/P1E、candidate semantic split、dynamic evidence temporal 的代码、报告、审阅与机器结果；既有结果只继承、不覆盖、不推翻。
- 计划建立统一 observation-condition table，覆盖 PERSON reference、GT-blind SAR candidates 和 matched/fixed controls；优先检查 range、azimuth、扇面边界、20 m 边界、support 有效率、display 状态、P0 local sigma/anchor coverage/fallback、C2/C3 结构和候选密度。
- 将把 `SAR_SINGLE_FRAME_OBSERVABLE`、`P0_TRANSPORT_CORE`、`P0_TRANSPORT_EXTENDED`、`MULTIMODAL_COMMON_FOV` 分开描述，优先连续可靠性和多标签状态，不作为新的研究资格 gate；冻结 P0 保持不动。
- 时间尺度诊断将比较 lag1/3/5 的 transport displacement / local uncertainty 与响应保持性，寻找几何可分辨性和图像响应去相关之间的 tradeoff，不预设更大 lag 更好。
- 光学只审计固定共同视场与粗时间窗/方位壳的现有可追溯能力；不使用精确逐帧光学点、`physical_target_id`、光学框 range 或未验证行为/姿态，SAR 保留最终定位权，并要求等宽 shifted-shell control。
- 活动目录限定为 `D:\profile\research\workspace`；解释器固定为 `D:\MINICONDA\envs\py311\python.exe`；不读取或依赖 `old_work`，不修改原始图像/标注，不创建或移动 SAR 框，不 commit/push。

## PERSON-SAR 观测模型诊断收口继续（2026-08-26）

- 接续已完成的 398 帧首轮诊断，不改变冻结协议、观测定义或旧结果；先逐张复核 8 个直接病例及 6 个汇总图，再生成最终 HTML。
- 修复 `sample_nearest` 在 P0 预测点为 NaN 时先转整数所产生的 RuntimeWarning；NaN 仍按既定语义保留为 unavailable/default，不改变有效预测点的采样结果。
- 将诊断脚本自身 SHA256 写入 `diagnostic_summary.json`，随后使用 `D:\MINICONDA\envs\py311\python.exe` 重跑并做旧输出一致性检查。
- 本次仍不读取 `old_work`，不重调冻结 P0，不修改 B0R/C0-C3/旧 P1E，不修改原始图像或标注，不创建或移动 SAR 框，不 commit/push。

## PERSON-SAR 观测模型诊断完成（2026-08-26）

### 执行与复现

- 使用 `D:\MINICONDA\envs\py311\python.exe` 完成 398 帧重跑；统一观测条件表 39,764 行、逐帧显示表 398 行、P0 局部条件表 112,753 行、lag 权衡表 1,158 行、病例 8 个。
- 修复 `sample_nearest` 对 NaN P0 预测点先转整数的 RuntimeWarning；NaN 仍按 unavailable/default 语义处理。修复后未再出现该 warning。
- 修复前后 7 个核心 CSV SHA256 全部一致：`observation_condition_table.csv`、`frame_display_condition_table.csv`、`p0_local_transport_condition_table.csv`、`lag_transport_response_tradeoff.csv`、`optical_shell_audit.csv`、`condition_state_summary.csv`、`case_registry.csv`；科学结果未改变。
- 诊断脚本 SHA256：`25F5D05333E85BAAC95ADA59D581C06C3533CF137FC83462D66CBA1D6A6CCCBE`；独立审阅修正后的报告生成器 SHA256：`C4EC3D0E24CA43F0C779B8609D838CB50ADDFFFA8B974CB772ABFB13B79DD272`。
- 合同三个冻结输入 SHA256 3/3 匹配；失败探针哈希也匹配但仅允许显示重复性失败探针语义。

### 主要诊断结果

- R02 P01/P02 不是统一的“响应不存在”：两者最近候选均为 9/9 rank>5，其中各 7/9 同时被离线标记为 shared；P02 另有 2/9 在 0.8 m 内 candidate missing。P03/P04 各 9/9 shared，每个目标均为 5 帧 rank1、3 帧 rank2、1 帧 rank12。shared/missing/low-rank 是人工 reference 条件下的离线评价状态，不是已经建立的 GT-blind runtime 状态检测器。
- P02 两个 missing 位于 FULL support、lag1 P0 core、无 display shift，不能由边界、P0 低可靠或显示突变单独解释；当前表示/峰提取和局部竞争仍是独立候选原因。
- `SAR_SINGLE_FRAME_OBSERVABLE` 与 P0 transport 域已分开。R03 reference lag1 core=0%，但单帧仍可观察；F494 有 rank=6 候选而 lag1 P0 unavailable。
- 全场 lag1/3/5 的位移/sigma 中位为 `0.255/0.697/1.019`；correct-P0 C2 retention 为 `0.873/0.779/0.720`；correct-zero 为 `0.014/0.087/0.171`。这只构成描述性聚合 tradeoff：lag1=M1、lag3/5=M2，帧对集合与 display 状态不同，R03 lag5 也不单调，不能写成纯 lag 因果效应。sigma 含固定 0.30 m support 项，是设计容差而非校准置信区间。
- 全场 C2 field alignment 与 PERSON 邻近候选消歧严格分开：前者存在小而系统的 correct 增益；旧 dynamic evidence 的 lag1 P0-specific PERSON rank/thread 增益仍未建立。
- display 离散代理中 high-censor 全 0、compressed 全 1，均缺乏区分力；连续 JS/robust shift 可分层，lag5 high-change retention 低于 baseline，但不作物理回波或增益因果解释。
- provisional optical ±250 ms azimuth shell 的 reference 覆盖高于 ±18° shifted controls，但同步仍未验证；shift 前等宽，扇面裁剪后真/假壳角宽并不相等。现有 `coverage_per_degree` 是“候选覆盖比例/平均扇内角宽”proxy，不是候选数/度；该 proxy 在正确壳与 shifted controls 间相近。当前只支持下一轮做公平裁剪/面积控制的 shell 实验，SAR 保留最终定位权。

### 报告、验证与停止点

- HTML：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\observation_model_diagnostic_v1\P1E_OBSERVATION_MODEL_DIAGNOSTIC_REPORT.html`；独立审阅修正后 SHA256：`7BB645D2F63DAF0D521B974ED40556B3F6CBBF0BC6BC0AD692393ECDB00B3CB2`。
- 自动验证：`report_validation.json = PASS (14/14)`；校验合同输入、代码哈希、行数、既有 C2 candidate score 一致性、C0-C3 冻结实现、14 张图、全部 HTML 本地链接、八问与新增因果/运行时语义边界。
- Edge headless 1600×1100 首屏实际渲染正常；独立审阅修正后的截图：`observation_model_diagnostic_v1\report_browser_qa_top_revised.png`。
- 2026-08-26 20:50:51 +08:00 最终再次运行冻结 P0 回归：`18/18 PASS`；合同三个输入 SHA256 逐项匹配，冻结主脚本、R04 链接、掩膜完整性、最差帧复核和 `old_work` 依赖检查全部通过。
- 本轮状态：`OBSERVATION_MODEL_DIAGNOSTIC_COMPLETE_NO_NEW_PASS_FAIL`。不进入复杂 tracker、不新增 C4/C5、不冻结总分或最终接口；下一轮如获授权，优先设计观测可靠度条件下的 missing/shared 状态实验和公平的 optical-shell candidate control，而不是机械增加 lag。
- 未读取或依赖 `old_work`，未修改原始图像/标注，未创建或移动 SAR 框，未修改冻结 P0/B0R/C0-C3/旧 P1E，未 commit、未 push；P2 仍为 `BLOCKED`。

## 等搜索成本 optical-shell 信息增益实验启动（2026-08-26）

- 用户将下一步收窄为：在相同 SAR 搜索成本下，正确粗光学方位先验是否比错误方位先验更能保留 PERSON 附近 SAR-only C2 响应并减少无关候选。
- 新结果目录：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\optical_shell_information_gain_v1`；旧 P0、B0R、C0-C3、candidate split、dynamic evidence 和 `observation_model_diagnostic_v1` 全部只读保留。
- TRUE shell 固定为 ±250 ms 内所有 optical PERSON 粗方位壳的并集，不使用 `physical_target_id` 选择轨迹；光学不提供 SAR range，SAR 在壳内仍使用既有 GT-blind C2 candidates 自主判断。
- matched null 只依据光学壳、固定映射、时间窗、SAR 几何、`SAR_SINGLE_FRAME_OBSERVABLE` 实际像素面积和 common-FoV 生成；固定 0.5° shift 网格、最小偏移 12°、角区间 Jaccard≤0.80，每帧选择 3 个至少相隔 8°的最低几何代价 null。
- 几何-only 预审计覆盖 398 帧，其中 376 帧存在 TRUE shell；376/376 均可生成 3 个 null。预审计没有读取 C2 candidate、C2 score 或人工 reference。
- 运行前协议：`00_MATCHED_OPTICAL_SHELL_INFORMATION_GAIN_PROTOCOL_FROZEN_BEFORE_RUN.md`。解释器固定为 `D:\MINICONDA\envs\py311\python.exe`；不读取 `old_work`，不生成 SAR 框，不新增总分/分类器/tracker，不 commit/push。

## 等搜索成本 optical-shell 首轮结果收口重跑启动（2026-08-27）

- 首轮已成功生成 398 帧、376 个 TRUE shell、1,128 个 matched null、245 条可配对 reference 和 8 个直接病例；不改变冻结 shell/null/C2 设计，只做 warning 清理、GT 后置评价顺序显式化和统计语义补全。
- 新增全 251 条 reference 的 `OPTICAL_PRIOR_UNAVAILABLE` 无条件核算，明确保留 R01 F133/F135/F140/F141 P01 与 R04 F175/F180 P03 共 6 条不可用记录，不从覆盖率静默删除。
- 新增 Top-K 全尺度、P0/display/support 条件化、TRUE 与 NULL 都保留候选时的局部 rank、仅有 C2 candidate 帧的搜索成本/P0 汇总，以及 response-present-but-peak-missing 审计；不新增总分、分类器、tracker 或 SAR 框。
- 初次成功运行 5 个核心 CSV 哈希已写入 `initial_run_core_hash_baseline.json`，重跑后将逐项比较并解释仅由新增列/警告修复造成的差异。
- 活动目录仍为 `D:\profile\research\workspace`；解释器仍为 `D:\MINICONDA\envs\py311\python.exe`；不读取 `old_work`，不修改冻结 P0/B0R/C0-C3 或旧诊断，不 commit/push。

## 等搜索成本 optical-shell 信息增益诊断完成（2026-08-27）

### 方法与复现

- 完成 398 帧全量重跑：376 个 TRUE shell、1,128 个 matched NULL、1,504 条 shell definition、50,337 条壳内候选记录、245 条可配对 reference、全 251 条无条件 applicability、9 个直接病例。
- NULL 固定为每帧 3 个，仍只由光学壳、固定映射、±250 ms 时间窗、SAR 扇面、`SAR_SINGLE_FRAME_OBSERVABLE` 与 provisional common-FoV 选择；reference、C2 candidate、C2 score、SAR range GT 和 `physical_target_id` 不参与 NULL 选择。
- warning/顺序修正后完整运行无 warning。首轮核心哈希中 `shell_definition_table.csv`、`shell_candidate_table.csv`、`shell_candidate_metrics.csv` 逐项完全不变；evaluation/comparison 仅因追加条件列、严格一对一口径和无条件统计而产生新哈希。
- 运行顺序已显式记录为：冻结依赖哈希 → 生成 TRUE/NULL shell → 截取既有 GT-blind C2 candidates → materialize reference slice 离线评价。候选 P0 parity 与 reference 位于同一个 observation CSV，因此准确口径是不声称严格 sealed process isolation，但 reference 内容没有参与 shell/null/candidate 计算。

### 主要结果

- 几何公平性：扇内角宽误差中位 0、P90 约数值零；有效面积误差中位 `6.39e-5`、P90 `2.46e-4`；common-FoV overlap 差中位 `0.0168`；A/B/C=`843/226/59`，困难控制未删除。
- 245 条有壳 reference：TRUE/NULL 中心覆盖 `89.4%/26.8%`，0.8 m candidate presence `89.4%/27.3%`，full-best retention `89.0%/26.9%`，严格一对一覆盖 `73.5%/22.2%`，Top-5/0.8 m `81.6%/24.5%`；reference 加权 candidate burden 中位 `44.6%/44.3%`。
- 全 251 条无条件分母：先验可用 `245/251=97.6%`；6 条 `OPTICAL_PRIOR_UNAVAILABLE` 为 R01 F133/F135/F140/F141 P01 和 R04 F175/F180 P03。无条件 TRUE 中心覆盖/候选保留均 `87.3%`，Top-5/0.8 m `79.7%`。
- 机制分解：给定 reference 已在壳内，candidate presence TRUE/NULL `99.1%/97.5%`、Top-5 `90.9%/87.8%`。TRUE 与至少一个 NULL 都保留候选的 114 条记录中，local-rank 中位优势 `0`，`62.3%` tie，TRUE better `12.3%`、worse `25.4%`。结论是正确壳提供方位几何保留信息，没有建立新的壳内 C2 唯一性。
- R02 P01 global→TRUE local rank 中位 `11→3`，P02 `18→6`；两者低 rank 有全扇面竞争成分，但各 `7/9` 同时 shared，P02 F482/F490 仍 candidate missing。P03/P04 `1→1`、TRUE reference coverage 各 `7/9`，shared 未解决。
- F482/F490 的 reference C2 percentile 约 `0.959/0.993`，最近离散峰距约 `1.159/0.820 m`，均 FULL support、P0 CORE、无 display shift。`missing` 仍只表示 local-max/NMS+固定半径表示缺峰，不等于物理响应消失。
- 有 C2 candidate 的 120 帧上，TRUE P0 CORE 比例中位 `57.5%` 低于 NULL `66.2%`，fallback `20.6%` 高于 NULL `12.8%`；优势不来自更可靠 P0 区。DISPLAY_SHIFT baseline/shift 两层均有正保留差，但不作因果解释。

### 报告、验证与停止点

- HTML：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\optical_shell_information_gain_v1\P1E_MATCHED_OPTICAL_SHELL_INFORMATION_GAIN_REPORT.html`。
- 报告验证：`report_validation.json = PASS (14/14)`；9 个病例图可读、全部本地链接可解析；Edge headless 1600×1100 首屏截图 `report_browser_qa_top.png` 已实际检查。
- 分析脚本 SHA256：`2C71440DF9C22FDCE17A3C4050E4E0054F6B7CA4542C44C134E2DEA3478A2203`；报告生成器 SHA256：`02BAF81874BCA96569788402E5BA01A7FF1BBCFC61978974173A9187571D112F`；HTML SHA256：`69ADCB3CA5C982E5E87C3ADB0E007F79325CC942FB8B4D7EF614B4B6EB561E47`。
- 2026-08-27 00:29:34 +08:00 冻结 P0 回归再次 `18/18 PASS`；research contract 三个输入 SHA256 `3/3` 匹配，冻结主脚本、R01→R04 链接、掩膜完整性、最差帧审阅与 `old_work` 依赖检查全部通过。
- 本轮状态：`MATCHED_OPTICAL_SHELL_DIAGNOSTIC_COMPLETE_NO_NEW_PASS_FAIL`。不生成 SAR 框，不授予 P1/P2 PASS，不声称盲验证，不自动开启复杂 tracker。若继续，优先验证同步/runtime optical track identity，并对重复的 response-present-but-peak-missing 做最小 response-region 表示审计；SAR 保留 range 与最终定位权。
- 未读取或依赖 `old_work`，未修改原始图像或标注，未修改冻结 P0/B0R/C0-C3/旧诊断，未创建或移动 SAR 框，未 commit、未 push。

## 运行时 optical track 壳与 C2 response-region 最小实验启动（2026-08-27）

- 用户明确要求不把 matched optical-shell 解释为 P2 成立，也不进入复杂多模态 tracker；本轮只研究两个已暴露接口：运行时 optical track 的方位壳压缩能力，以及冻结 C2 连续场相对 local-max/NMS 峰表示的语义保真度。
- 活动目录固定为 `D:\profile\research\workspace`；解释器固定为 `D:\MINICONDA\envs\py311\python.exe`；`old_work` 不读取、不依赖。
- 新结果目录：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\runtime_track_response_region_minimal_v1`；旧 P0、B0R、C0-C3、candidate split、dynamic evidence、observation diagnostic 与 matched shell 全部只读。
- 启动审计已确认当前全场光学链存在 `optical_person_id`、`track_tier`、fragment stitching 和 `identity_semantics=RUN_SCOPED_OPTICAL_CONTINUITY_HYPOTHESIS_NOT_PHYSICAL_IDENTITY_TRUTH` 字段；仍需在运行前完整追溯 R01/R02/R03/R04 来源，特别排除人工 `physical_target_id` 回填进入 runtime ID。
- 预运行协议已冻结：track 时间半窗固定为 `0/100/250/500 ms`；所有 optical-only accepted tracks 都输出壳，不按 SAR GT 选择；C2 region 主阈值固定为有效域 95th percentile，90th/97.5th 仅作敏感性，8-connectivity、无形态学桥接、无小区删除。
- 本轮不新增 C4/C5，不修改 C2，不生成 SAR range 或框，不构造总分，不授予 P1/P2 PASS，不 commit/push；完成两条独立诊断、最小交叉相交审计、直接病例、冻结 P0 回归后停止。
- 运行前 provenance 修正：现有 `optical_person_id` 是不使用 GT 的整段 fragment Hungarian 拼接与短缺口插值结果，只能称 `GT_BLIND_OFFLINE_CONTINUITY_PROXY`，不能直接称严格 runtime ID。主 track-shell 接口因此改为全部自动 `raw_track_fragment_id` 检测 tracklet；stitched accepted ID 只作为次级工程上限。该修正在看本轮 SAR 结果前记录，不改变时间窗、C2 region 或评价规则。
- 运行前 region 实现澄清：主/敏感性区域使用既有 4096-bin CDF 在实际 `fixed_support_mean_v2` 候选场 `S(x)` 上定义 B95/B90/B97.5；基础 C2 只作算子结构展示。`EXTENDED_OR_RIDGE_RESPONSE` 主轴条件收紧为 `>1.80 m`（最大冻结 C2 尺度 0.90 m 的两倍）或 elongation `>=3.0`，避免过度解释普通连通块。
- 正式运行前实现核查补全两项不可省略的完整性：各时间窗没有 track shell 的帧/reference 必须作为 `TRACK_SHELL_UNAVAILABLE` 留在无条件分母；250 ms parity 必须直接比较新 stitched union 与旧 matched TRUE 壳，不能只让旧代码自我复现。
- 分析脚本已用 `D:\MINICONDA\envs\py311\python.exe` 通过 `py_compile`；R01/R02/R03/R04 各一帧冒烟均逐项复现冻结 C2 candidate 的数量、rank、坐标、score、support fraction/status，并成功生成 q95 region、raw fragment shell 和 stitched proxy shell。
- 正式运行将逐帧重算 candidate parity；任何冻结输入 SHA256、research contract 或 candidate parity 不一致均立即停止。人工 SAR reference 仍只在全部 track shell、region 和壳内 GT-blind candidate 生成后物化。
- 首次 398 帧 pre-reference 运行按保护逻辑中止：旧 `gt_blind_candidates_all_processed_frames.csv` 实际只覆盖 126 个 candidate-audit 帧（R01 39、R02 23、R03 4、R04 60），其余 272 帧“无 CSV 行”不等价于“应有 0 个 candidate”。覆盖的 126 帧候选数量、rank、坐标、score、support 已全部精确复现，最大浮点差约 `1.11e-16`；未覆盖帧只保留新生成的连续 C2 response region，不把本轮重算峰混入既有 candidate 接口。
- 已将 parity 语义改为 `COVERED_FRAME_EXACT_MATCH` 与 `NO_LEGACY_CANDIDATE_ARTIFACT_FOR_FRAME`，并保留 398 个 region mask、pre-reference region 表和 track-shell 表继续后置评价，避免重复图像计算；此修正不读取人工 reference、不改变 C2/区域/track 壳设计。

## 运行时 optical track 壳与 C2 response-region 报告收尾继续（2026-08-27）

- 承接已经完成且状态为 `COMPLETE_NO_NEW_PASS_FAIL_NO_P2_CLAIM` 的 398 帧最小实验；不重跑或重调冻结 P0、B0R、C0-C3、track-shell 规则和 response-region 规则。
- 本次只完成独立中文 HTML 报告、汇总图、局部病例放大、自动审计、Edge 首屏视觉 QA、冻结 P0 回归、README 与日志收口。
- 活动目录继续限定为 `D:\profile\research\workspace`；解释器固定为 `D:\MINICONDA\envs\py311\python.exe`；不读取或依赖 `old_work`，不修改原始图像/标注，不创建或移动 SAR 框，不 commit/push。
- 报告必须保持两条接口分离：主 optical 接口为全部自动 detected raw fragments，stitched accepted 仅是 GT-blind offline continuity proxy；C2 response region 是显示域响应表示，不是 PERSON 框或人体固有 RCS。
- 最终仍停止在最小诊断：不授予 P1/P2 PASS，不进入 region tracker，不把人工 `physical_target_id` 用作 runtime optical identity，SAR 保留 range 和最终定位权。

## 运行时 optical track 壳与 C2 response-region 最小诊断完成（2026-08-27）

### 执行与接口边界

- 398 帧实验最终状态确认：`COMPLETE_NO_NEW_PASS_FAIL_NO_P2_CLAIM`；分析脚本 SHA256=`051B414753B73118CF77712A35DF86EC5FB05C12B2C00217EB14BFE81DFDCBBA`，冻结依赖与 research contract 输入哈希全部匹配，正式运行无 warning。
- 主 optical 接口固定为 `RAW_DETECTED_FRAGMENT_ALL`，全部自动 detected raw fragments 都独立出壳；次级 stitched accepted 仅为 `GT_BLIND_OFFLINE_CONTINUITY_PROXY`。两者都没有使用人工 `physical_target_id`、SAR reference 或 SAR range GT 生成壳。
- R01/R02/R03/R04 raw fragments 为 `12/33/5/11`，stitched accepted tracks 为 `6/9/2/5`；R02 accepted 中 ambiguous stitch 合计 `10`，严格 runtime identity 未建立。
- 时间半窗 `0/100/250/500 ms` 均按预先固定值报告。RAW reference 候选保留为 `76.9/81.7/87.3/93.2%`，单 track burden 中位为 `14.5/16.4/22.0/25.8%`，union burden 中位为 `28.2/31.5/35.9/41.0%`；没有事后选窗口。
- 居中窗口可能使用未来光学观测，所以当前准确口径是带缓冲的时间不确定度诊断，不是已建立的零延迟 causal online tracker。

### 主要结果

- R02 RAW ±250 ms 的 `global→union→offline best-track` rank 中位为：P01 `11→3→2`、P02 `18→6→4`、P03/P04 `1→1→1`。P01/P02 搜索问题进一步缩小，但 offline best-track 只用于后置评价，运行时没有人工选轨。
- P03/P04 track shells 仍明显重叠；offline-associated 角度 Jaccard 在不同窗口约 `0.5–0.6`，且窗口可配对分母不同。当前不能形成“光学壳已分离而 SAR 仍共享”的强证据。
- 冻结 C2 response-region 主规则为 q95，q90/q97.5 只做敏感性；4096-bin percentile、8-connectivity、无形态学桥接、无小区删除、无 PERSON 个案调参。
- q95 PERSON reference 直接覆盖 `98.0%`，0.30 m 邻近覆盖 `99.2%`；F482/F490 两条从 candidate missing 修正为 `PEAK_MISSING_REGION_PRESENT`。q90-only 两条为 R02 F494 P01、R04 F35 P01；q90 内完全无 region 为 0。
- q95 直接覆盖对照为 PERSON `98.0%`、固定偏移 `1.8%`、几何匹配空间对照 `3.9%`、local competing response `63.3%`。region 表示恢复 response presence 语义，但没有解决局部竞争或唯一定位。
- F482 P02：percentile `0.959`、最近峰 rank 14/距 `1.159 m`、q95 shared extended region `1.362 m²`、主轴 `2.257 m`。F490 P02：percentile `0.993`、最近峰 rank 14/距 `0.820 m`、q95 shared extended region `2.148 m²`、主轴 `4.094 m`。
- q95 shared fraction 总体 `37.5%`，R02 `94.4%`，R01 `60.6%`，R03/R04 当前 reference 为 0；shared 只描述图像域响应重叠，不是物理散射融合证明。
- 旧 GT-blind candidate artifact 只覆盖 `126/398` 帧；覆盖帧逐字段精确复现，最大浮点差 `1.11e-16`。其余 272 帧明确标记 `NO_LEGACY_CANDIDATE_ARTIFACT_FOR_FRAME`，未解释为零候选；response-region masks 为 `398/398`。

### 报告、验证与停止点

- 新中文 HTML：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\runtime_track_response_region_minimal_v1\P1E_RUNTIME_TRACK_RESPONSE_REGION_MINIMAL_REPORT.html`，SHA256=`226FDA62494A4FD984EC6D2E68FA96D8A4FC2EA838A0E35CE721126FF483FDE1`。
- 报告生成器：`render_p1e_runtime_track_response_region_report.py`，SHA256=`A9FE022A044718E3A376BEF39FE5F15273405008E305EB3D1FD77489EF082BAE`；独立验证器：`validate_p1e_runtime_track_response_region_report.py`，SHA256=`02ECD3F9934C0431D7D00D81B790CF92A243468DA272698A439FFF86D233267A`。
- 报告包含 5 张汇总图、7 张局部病例图和 7 张全扇面病例图；独立 `report_validation.json = PASS (18/18)`，66 个本地链接缺失 0，19 张正式图不可读 0。
- Edge headless 1600×1100 首屏截图：`runtime_track_response_region_minimal_v1\report_browser_qa_top.png`；已实际检查，中文、导航、结论卡片和首屏布局正常。
- 2026-08-27 18:22:43 +08:00 使用 `D:\MINICONDA\envs\py311\python.exe` 再次运行冻结 P0 回归：`18/18 PASS`。
- 未读取或依赖 `old_work`，未修改原始图像/标注，未修改冻结 P0/B0R/C0–C3 或旧结果，未创建或移动 SAR 框，未 commit、未 push。
- 本轮到此停止：不授予 P1/P2 PASS，不声称盲验证，不进入 region tracker 或复杂多模态 tracker。若以后继续，优先验证 causal/buffered runtime optical track 与同步不确定度，再考虑 `optical track shell ∩ SAR response region + frozen P0 region propagation`；SAR 继续保留 range 与最终定位权。

## 光学方位壳不确定度与 response-region 拓扑诊断启动（2026-08-27）

- 承接 `runtime_track_response_region_minimal_v1`，本轮只回答 optical azimuth-shell 不确定度组成与 GT-blind shell ↔ SAR response-region 二部拓扑；若 A/B 已清楚即停止，不机械进入 region 时序传播。
- 活动目录固定为 `D:\profile\research\workspace`；解释器固定为 `D:\MINICONDA\envs\py311\python.exe`；`old_work` 不读取、不依赖。
- 新结果目录：`output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\shell_uncertainty_region_topology_v1`；旧 P0、B0R、C0-C3、C2 response regions 和既有报告全部只读。
- 方位壳宽度预注册为“代表性单框角宽 + 时间/视角 union 扩张 + guard 实际增量 − SAR fan clipping”的代数分解；时间策略固定为 same-frame、past-only 250 ms、buffered +100 ms、centered ±250 ms。
- guard 敏感性固定为每侧 `6° / 2.651812° / 0°`，后两者只作几何反事实，不根据 SAR reference 选择，不代表可部署壳或已完成重新标定。
- 主 topology 使用全部自动 raw fragments、当前 6° guard、same-frame / past-only / centered 三种时间策略和 q90/q95/q97.5 region；边必须由真实像素相交生成，不能以角包围盒相交代替。
- `physical_target_id`、SAR range GT 和 reference 禁止进入 shell/region/edge/topology 生成；reference 仅在完整图生成后用于解释 P01/P02/P03/P04、F482/F490 和 shared/peak-missing 语义。
- 本轮不新增 C4/C5，不训练分类器，不构造总分/复杂 tracker，不生成 SAR range/box，不授予 P1/P2 PASS，不 commit/push。

## 光学壳不确定度与 region 拓扑正式收口继续（2026-08-27）

- 承接已完成的 398 帧 `shell_uncertainty_region_topology_v1` 正式实验；不重算、不调节 shell、guard、时间窗、C2 或 q90/q95/q97.5 region 规则。
- 本次只补独立验证器、Edge 首屏 QA、冻结 P0 回归、README/日志与最终 SHA256；验证器独立读取物化表，不导入主分析模块。
- 独立审计将核对冻结输入与 398 个 mask 哈希、代数分解闭合、same-frame/past-only 无未来观测、pre-reference 先于 reference 物化、runtime 表无人工 `physical_target_id`、pixel edge 与 node/component degree 一致、854 条旧 centered ±250 ms raw shell 完全奇偶、HTML 本地链接和 12 张正式图可读。
- 活动目录仍为 `D:\profile\research\workspace`；解释器仍为 `D:\MINICONDA\envs\py311\python.exe`；不读取或依赖 `old_work`，不修改冻结 P0/B0R/C0-C3 或旧结果，不创建/移动 SAR 框，不 commit/push。
- 本轮停止边界不变：只回答 optical shell 不确定度组成与 GT-blind shell–region 结构化关联，不进入 P2，不机械开启 region 时序传播。

## 光学方位壳不确定度与 response-region 拓扑诊断完成（2026-08-27）

### 执行与完整性

- 398 帧正式实验最终状态为 `COMPLETE_NO_NEW_PASS_FAIL_NO_P2_CLAIM`；输出目录为 `output\person_physics_guided_image_domain_study_20260824\p1e_sar_only_response_interface\shell_uncertainty_region_topology_v1`。
- 全部 pre-reference 产品先生成：14,607 条 shell 分解、97,219 条 pixel edges、6,927 个 shell nodes、207,603 个 region nodes、136,391 个 component、3,582 条逐帧拓扑；其后才物化 4,518 条人工 reference 解释。清单 `reference_loaded=false`，runtime 产品未使用人工 `physical_target_id`、SAR reference 或光学指定 SAR range。
- 独立验证器不导入主分析模块，直接读取物化表重算，最终 `report_validation.json = PASS (18/18)`。冻结输入哈希与 398 个 region masks 聚合哈希全部匹配；记录分解最大闭合误差 `7.105427357601002e-15°`；same-frame/past-only 未来观测为 0。
- shell/region local degree 分别对 6,927/207,603 个 nodes 重算，均 0 mismatch；97,219 条 edges 的 component 归属 0 mismatch；136,391 个 components 的 shell/region/edge 数和 topology state 重算均 0 mismatch。
- 新 centered ±250 ms raw shell 与上一轮冻结接口直接 merge：`854/854` 均为 both，宽度误差 0、面积误差 0、interval 完全一致。

### 主要诊断结论

- R02 名义 same-frame 的典型帧：单框角宽 `2.686°`，guard 增量 `12°`，单 track 壳宽 `14.686°`；centered ±250 ms 额外时间/视角 union `6.906°`，单 track 壳宽 `21.619°`。多人 shell 未分离不是单一同步问题，guard 与时间 union 是独立扩张来源。
- R02 `retention / all-track union burden`：same-frame `83.3% / 28.3%`，past-only 250 ms `91.7% / 29.0%`，buffered +100 ms `94.4% / 29.8%`，centered ±250 ms `94.4% / 31.9%`。这些是 latency–uncertainty–burden 描述，不作最优窗口选择。
- same-frame 当前 ±6° guard 的 associated-shell Jaccard：P01/P02 `0.635`，P03/P04 `0.517`（仅 `4/9` 帧双壳可用）。±2.652° 与 0° 几何反事实可降低同帧重叠，但不构成可部署新 mapping；centered 0° 下界仍约 `0.492/0.505`，说明时间 union 会重新产生重叠。
- R02 q95 已与壳相交 regions 中，多壳覆盖从 same-frame `211/257=82.1%` 增至 centered `268/307=87.3%`。这使 local degree 成为 GT-blind ambiguity state；完整 component 多为 multi-shell/multi-region，不能只看 `MULTIPLE_SHELLS_ONE_REGION` 标签是否出现。
- R02 q95 shared reference 34 条中，same-frame 24 条、centered 30 条所属 region 被多个 shells 覆盖；centered `34/34` 均处于 multi-shell/multi-region component。粗方位壳缩小搜索，但没有解决局部 SAR response sharing。
- F482/F490 P02 均保持 `PEAK_MISSING_REGION_PRESENT`；F482 P01/P02 共用 q95 R0012（degree 2→3），F490 P01/P02 共用 q95 R0012（degree 3）。continuous region 比离散 peak 更忠实地表达 response presence，但仍不等于 PERSON box 或 identity separation。
- `SHELL_NO_REGION` 未出现不能解释为 PERSON evidence：q90/q95/q97.5 是逐帧相对分位层，每个壳都会碰到某个相对高响应。运行时可计算的 region level/shape、local degree、component topology 与 reference-conditioned 的 peak/shared/P01–P04 解释继续严格分层。

### 报告、验证与停止点

- 中文 HTML：`P1E_SHELL_UNCERTAINTY_REGION_TOPOLOGY_REPORT.html`，SHA256=`1784553864685880CACDDDB0AFA125C067039628E15C43EC256AD784E02B6A02`。
- 分析脚本 SHA256=`18AABE0BF28B71719323944366F6973B73E8F789559C275313431ECE52293027`；报告生成器 SHA256=`1990C657585A15F0F37F0777FD60D590C0CFA26AC4C385D3F9F53321671F6A42`；独立验证器 SHA256=`BE61EDDB73E7A15A050A8F947B28C5E211A67C6C43CBE30BB388ED4F6EB0B287`；`report_validation.json` SHA256=`836561FC3C61C91DC705A58646608302D9E77EE3D83EF231750481D58566F209`。
- HTML 的 19 个本地链接与 12 张正式图全部可读。Edge headless 1600×1100 首屏截图 `report_browser_qa_top.png` SHA256=`C791A8CC0BB354BF20B0040B8236084B19EB34C1F142BF81B71ABC3A40E14F08`；已实际检查，中文、首屏结论和布局正常。
- 2026-08-27 20:02 +08:00 使用 `D:\MINICONDA\envs\py311\python.exe` 再次运行冻结 P0 回归，结果 `18/18 PASS`。
- 本轮到此停止：不授予 P1/P2 PASS，不声称盲验证，不生成 SAR range/box，不构造总分/分类器/tracker，不进入 region 时序传播。光学继续只提供 time/azimuth prior，SAR 保留 range 与最终定位权。
- 未读取或依赖 `old_work`，未修改原始图像/标注，未修改冻结 P0/B0R/C0-C3 或旧结果，未创建或移动 SAR 框，未 commit、未 push。

## P1E observation interface 当前状态与语义一致性审阅启动（2026-08-28）

- 本轮为纯文档审计：完整追踪 `optical fragment → optical shell → SAR response-region → shell-region topology → physical reference/offline evaluation` 的对象定义、生成输入、物化表和报告解释。
- 唯一计划新增文件为 `tasks\person_physics_guided_image_domain_study_20260824\docs\current_state_review.md`；不新增算法，不运行新实验，不修改冻结 P0/B0R/C0-C3、既有 shell/region/topology 生成模块或旧报告。
- 审阅重点是 runtime 与 offline evaluation 的边界，特别核查 `raw_track_fragment_id`、GT-blind offline continuity proxy、人工 `physical_target_id`、manual SAR reference、q90/q95/q97.5 region、local degree 与 component topology 是否存在语义混用。
- 明确禁止进入 tracker、classifier、score fusion、identity assignment 或 SAR box regression；下一阶段建议只允许提出受控实验问题，不实现算法。
- 活动目录为 `D:\profile\research\workspace`；默认解释器为 `D:\MINICONDA\envs\py311\python.exe`；不读取或依赖 `old_work`，不 commit、不 push。

## P1E observation interface 当前状态与语义一致性审阅完成（2026-08-28）

- 已完成纯文档审计，新增：`tasks\person_physics_guided_image_domain_study_20260824\docs\current_state_review.md`。
- 审阅覆盖当前 P1E 单帧 S(x)、candidate semantic split、dynamic evidence、observation diagnostic、matched optical shell、runtime-track/response-region、shell uncertainty/topology 的代码、协议、CSV/JSON schema、HTML 和验证器；未运行新实验。
- 核心确认：C2/S(x)、raw-fragment optical shell、response-region 和最新像素级 shell–region topology 的生成未使用人工 `physical_target_id`、manual SAR reference、人工框中心或 SAR range GT；最新 topology 先物化 pre-reference shell/region/edge/component，之后才 materialize reference slice 做离线解释。
- 核心语义边界：`raw_track_fragment_id` 是自动 optical tracklet hypothesis，不是 PERSON identity；`optical_person_id` 是全 run GT-blind offline continuity proxy；optical shell 只提供 time/azimuth prior；response-region 不是 PERSON box；topology 只描述几何相交与搜索歧义；manual SAR reference 是人工框几何参考，不是物理散射中心。
- 已记录的主要语义风险：旧 `P1E_EXPLORATORY_CONCLUSION.md` 的“时序未启动/不进入时序”已经失效；candidate temporal gate 只属历史；runtime-track 主协议对 `optical_person_id` 的过强表述由 `00A` amendment 修正；旧 `response_region_track_shell_intersection.csv` 只是角跨度相交，最新像素 edge 表才是权威 topology；`SHARED_REGION`、`PEAK_MISSING_REGION_PRESENT` 和 offline one-to-one/best-track 仍是 reference-conditioned 评价，不能冒充 runtime identity 或定位结果。
- 额外澄清：旧 candidate artifact 仅覆盖 126/398 帧，且审计帧集合部分由 manual frame presence 选择；候选坐标本身虽不使用 annotation，但该 artifact 不能称完整 runtime stream。`accepted_peak_count` 仅表示通过冻结 GT-blind local-max/NMS 的候选，不是人工接受或 PERSON-positive。
- 文档已包含 A 已建立能力、B 未解决问题、C 当前假设、D 不允许继续使用的解释、E 下一阶段受控实验建议，并明确禁止 tracker、classifier、score fusion、identity assignment 和 SAR box regression。
- 本地文档链接检查 `14/14` 存在；必需章节 A–E 齐全。未修改 P0、B0R、C0–C3、candidate、shell、region、topology 或旧报告；未创建或移动 SAR 框；未读取或依赖 `old_work`；未 commit、未 push。

## P1E observation interface baseline 与 M0 prerequisite audit 启动（2026-08-28）

- 目标一：以精确路径收口 `P1E observation interface exploratory baseline`，只纳入当前 PERSON task、研究日志和轻量协议/报告/summary/validation/manifest，不纳入大型 CSV、图像、mask、browser cache、模型、ZIP/code-package snapshot 或无关 dirty history。
- 目标二：只读审计 optical/SAR 时间、nominal mapping、optical→SAR azimuth、SAR range/azimuth geometry、P0 数学方向和 region-mask warp 能力，并写 M0 docs-only draft。
- 活动目录固定为 `D:\profile\research\workspace`；默认解释器为 `D:\MINICONDA\envs\py311\python.exe`；不读取或依赖 `old_work`。
- 明确不运行新的 motion-consistency 实验，不重跑旧实验，不修改公式/manual SAR reference/历史结果，不实现 tracker、Hungarian、identity assignment、classifier、learned fusion、SAR box 或最终定位。
- Git 预检查：repo=`D:\profile\research\workspace`，branch=`main`，起始 HEAD=`c474bdc053d993599ec8813b10e51461b3ee5912`，remote=`origin`；semantic audit 与当前 PERSON task/log 尚未跟踪，worktree 另有大量无关历史 dirty state，必须 exact-path staging。

## P1E observation interface baseline 内容收口完成，待精确 Git 提交（2026-08-28）

- 新增 `docs/M0_TIME_COORDINATE_AND_INTERFACE_AUDIT.md`：确认 optical≈18 FPS、SAR=30 FPS 均来自 OpenCV video metadata；timestamp 是 `round(frame_index*1000/fps)` nominal index/FPS 值；R01–R04 registry 为 zero-offset placeholder，严格同步 `NOT_CALIBRATED`；398 个 nominal pair residual 为 `[-23,+23] ms`、absolute P95 `23 ms`，只代表 nominal-grid quantization。
- 审计确认固定 mapping 为 `theta_deg=0.02666536443690682*x_px-45.502258572693094`；box x1/x2 先形成 angular span，再独立加入 guard、temporal union、fan/common-FoV clipping。参数来自 R01 manual PERSON pilot，designation=`PILOT_REFERENCE_ONLY`，R04 只提供 conditional-on-sync 且不 refit 的支持。
- SAR 1024×592 geometry 固定为 center `(511.7453,590.7764)` px、radius `591.3403` px、outer range `20 m`、`29.5670 px/m`；range/azimuth 分别为 `hypot/px_per_m` 与 `atan2(x-cx,cy-y)`，正方位向图像右。
- P0 是 source→destination 的 pair-specific image-pixel apparent displacement；lag1=M1 translation、lag3/5=M2 affine。point predictor 可用于任意 mask pixels，但当前没有权威 full-mask warp API，因此标记 `MASK_WARP_MATHEMATICALLY_FEASIBLE / NOT_IMPLEMENTED / NOT_MATERIALIZED`。
- 新增 `docs/M0_OPTICAL_SAR_MOTION_CONSISTENCY_MINIMAL_STUDY_DRAFT.md`：主 node=q95、q97.5 strong core、q90 weak support；枚举 one-to-many/many-to-one GT-blind temporal edges；主量为 P0-warped support retention/overlap，跨模态首先比较 `Δtheta_optical↔Δtheta_SAR`；manual reference 只在完整物化冻结后评价。
- README 已加入上述两份文档入口并改为当前权威状态。两份 M0 文档均为 `NOT_EXECUTED`；本轮没有生成新实验产物。
- 下一真正最小可执行实验建议为 `M0A_R02_LAG1_Q95_SUPPORT_WARP_PILOT`：只用已有 comparable adjacent pairs，冻结一个 soft forward mask-warp contract，枚举全部 q95→q95 edges，比较 P0/zero/time-shift/matched-wrong，先物化再评价；不做 tracker 或 identity。
- Git 提交应使用 message `Establish P1E observation interface exploratory baseline`，tag `p1e-observation-interface-baseline-20260828`；提交 SHA、push 与最终 divergence 在完成 staged diff 审阅后由最终交付记录。

## M0A R02 lag1 q95 region-support transport pilot 启动（2026-08-28）

- 起始 baseline/HEAD=`edd7c1ba91577f18fa54877f82ee92eb779aab33`，branch=`main`，tag=`p1e-observation-interface-baseline-20260828`，`origin/main` 一致，起始 divergence `0/0`。
- 本轮科学角色固定为 `M0_SAR_TEMPORAL_PREREQUISITE`：只检验 R02 adjacent lag1 q95 region-support continuity、结构匹配 alternatives 的排序信息，以及 frozen P0 相对 ZERO transport 的增量。
- 明确不验证 Optical–SAR motion consistency，不报告跨模态 ambiguity reduction，不进入 raw optical angular dynamics、M0B、tracker、identity assignment、classifier、score fusion 或 SAR localization。
- 活动目录固定为 `D:\profile\research\workspace`；解释器固定为 `D:\MINICONDA\envs\py311\python.exe`；不读取或依赖 `old_work`。
- R02 response-region 当前覆盖 F472–F494 共 23 帧；B0R lag1 M1 为 22/22 model available 且 `pair_comparable=True`。
- 正式 pre-run protocol 已先建立于 `output\person_physics_guided_image_domain_study_20260824\m0a_r02_lag1_q95_region_support_transport_pilot\M0A_R02_LAG1_Q95_REGION_SUPPORT_TRANSPORT_PROTOCOL_FROZEN_BEFORE_RUN.md`；当前尚为 implementation-hash 待填状态，任何 synthetic test 或数据实验均未运行。
- warp 计划收窄为 frozen lag1 M1 source→destination OpenCV soft affine occupancy warp；必须先通过 identity、integer、subpixel、boundary-loss、P0 point-vs-mask 5 项 synthetic tests，并独立保存 source-total 与 conditional-valid denominators。

## M0A protocol/code 正式冻结、等待运行（2026-08-28 14:52 +08:00）

- 解释器固定为 `D:\MINICONDA\envs\py311\python.exe`；活动目录仍为 `D:\profile\research\workspace`，未读取或依赖 `old_work`。
- protocol 状态已从 `PRE_IMPLEMENTATION_DRAFT_NOT_RUN` 改为 `FROZEN_BEFORE_RUN`；协议 SHA256=`9C461A58659B775D0C21B9E35403A82E859FA0BB383335D6246202861E5DB56F`。
- `protocol_freeze.json` 已物化：冻结 starting HEAD、22 个 adjacent lag1 pairs、4 个 implementation hashes、56 个逐文件 dependency hashes、工具链版本与 `reference_loaded=false` policy。
- 四个实现 SHA256：runner=`6B2A193D11B15DD8B5FC633925AB70DB0282983605D4A864BCE41309DA63DE40`；synthetic tests=`AA82E876F4E0D8103EEB25100C966C261A7339B2C23C0EEEF8318D3723297374`；independent validator=`B0523DFAC749F92F3DF9FE7DBCB18995F6853BCECCF3DFD8C8F50F868812C018`；renderer/report=`54656541AC38DF4C32D143AC1E8E1E62BDC898A5FA9C1CC3850ECFBD3779F945`。
- freeze 前已修正 CSV boolean parsing 与 supported-rank tie break；同 retention 时固定按 destination region ID 升序。源码 compile/import read-test 均通过，尚未生成 synthetic 或实验结果。

## M0A preflight cardinality 修正并重新冻结（2026-08-28）

- 首次 synthetic 命令在第 5 项读取 R02 runtime inputs 时，于 F477 被错误的全帧常数断言阻断；metadata 与按冻结 valid-mask 公式重算逐帧完全一致，F477/F478/F484/F490 为 `364950`，其余为 `364951`。这不是 warp 数值失败，也没有写出 `warp_synthetic_tests.json` 或任何实验矩阵。
- 最小修复仅移除 `EXPECTED_VALID_PIXELS=364951` 的跨帧常数断言；继续保留每帧重算值必须与该帧 `omega_single_pixel_count` 完全一致的审计。没有改 valid-mask 公式、P0、warp、descriptor、control 或 outcome rule。
- 已在任何正式 synthetic/实验结果生成前重新冻结为 `REV1_AFTER_VALID_MASK_CARDINALITY_ASSERTION_FIX`：runner SHA256=`752046236AAC98D0B12CB878193F923A702D83936BB57903425E489D13803EA0`，新 protocol SHA256=`2B14EDC408AFFDF153ACACDEE110FA0A25BB41F481BFB853D7F2970DB17CD311`；其余 3 个实现及全部输入哈希不变。

## M0A pre-reference 图像冻结范围补全（2026-08-28）

- 首次 pre-reference 物化得到预期 23 帧、22 pairs、1117 nodes、102,996 matrix rows 和 257,490 matched rows，且未加载 reference；但复核 freeze 函数发现其未把 9 张 pre-reference case PNG 纳入 hash freeze。
- 因 reference 尚未 reveal，该批表仅作为预检产物，不作为正式冻结输出。已补充“先渲染 9 张无人工 overlay 病例图→独立验证→表与图一起 freeze”的要求并重新冻结为 REV2。
- REV2 protocol SHA256=`89D2AE5884255F7E0D03187E80BF49E99CFBD31F03C5BBC54F86EBC707FC74E3`；runner SHA256=`4ABA5781293EAE950DC78D530F33FC5191B81B7163AFCEC0AD38BFC030213FDC`；validator SHA256=`70D77D3363FCE0F596A583921E2F910660C6E3AC044277DAAD658A3ED0365946`。synthetic tester、renderer 与 frozen inputs 不变；将从 synthetic/pre-reference 阶段重新运行。

## M0A merge-like 可视化侧别修正（2026-08-28）

- REV2 pre-reference 表重跑后，renderer 在 merge-like case 发现 registry 的 related IDs 是 source regions，而旧绘图路径错误按 destination region 查找并停止。该错误只影响未冻结的病例 PNG；matrix、matched sets、case selection 与 reference boundary 均未改变，manual reference 仍未加载。
- 最小修复为 merge-like related IDs 在 source frame 绘制；split-like 与 post-reference alternative 仍在 destination frame 绘制。重新冻结为 REV3：protocol SHA256=`B85F9C4D42200B97B7E5374A05168904B5BB7848C06AAE6E10113ACE63042E43`，renderer SHA256=`C6AF40E4DDDEE7B06FC97AA0D1584C42FAE0007E260DF108D5C1A79DBC929FEE`；其余实现与输入哈希不变。

## M0A independent validator 性能等价修正（2026-08-28）

- REV3 已成功生成 9/9 pre-reference figures；独立 validator 未报科学检查错误，但逐 primary edge 扫描全部 51,498 条 P0 matrix，形成不必要的高复杂度。已停止该只读验证进程，未生成 validation JSON，reference 仍未加载。
- 仅把 source pool 查找改成预建 `(pair_index, source_region_id)` 分组索引；structural distance、top-5 tie order、denominator checks 与 PASS 条件完全不变。
- 重新冻结为 REV4：protocol SHA256=`0A2116AD3FCBF7C77751B365BFE0063C7FD91A6C77AE64346FAE80D52281E025`，validator SHA256=`F2E4297F2EBB6E9AA34FD33C52249F997607E76BA5918651DA0179A45539BDC6`；其余实现与输入哈希不变。

## M0A R02 lag1 q95 region-support transport pilot 完成（2026-08-28）

### 执行与完整性

- 最终冻结 revision=`REV4_VALIDATOR_GROUP_INDEX_PERFORMANCE_ONLY`；protocol SHA256=`0A2116AD3FCBF7C77751B365BFE0063C7FD91A6C77AE64346FAE80D52281E025`。
- 正式纳入 R02 F472–F494 共 23 帧、22/22 adjacent lag1 comparable pairs、1117 q95 nodes；完整 P0/ZERO matrix 各 51,498 rows，matched structural alternatives 257,490 rows。
- 5/5 warp synthetic tests PASS：identity/integer/subpixel/boundary-loss 数值符合冻结定义；9 个真实 representative points 的 P0 point-prediction vs mask-warp 最大误差 `0.0155228 px < 0.05 px`。
- pre-reference independent validation=`PASS 14/14`；完整矩阵 expected/actual 均 102,996，denominator 最大闭合误差 `1.11e-16`，matched structural distance 最大复算差 `8.88e-15`，禁止人工字段 0，9/9 pre-reference PNG 可读。
- pre-reference 17 个表/manifest/ledger/validation/PNG 已在 reference reveal 前冻结，freeze payload SHA256=`99FE416DCDB9A817BDF5D79DC76CAB1F0D691119B5DC2C740132B0619F602831`；final validation=`PASS 12/12`，确认 reveal 后这些文件未变化。
- reference reveal 后生成 12 张 post-reference case PNG、HTML、post tables/summary 和 execution ledger；Edge headless 1600×1100 首屏已实际检查，结论卡、denominator、q97.5/q90 与禁止结论边界正常显示。直接人工检查了 P0>ZERO、ZERO>P0、split-like、merge-like、deceptive alternative 5 张病例。

### 主要结果

- 冻结 outcome rule 得到 `M0A_REGION_SUPPORT_TRANSPORT_WITH_P0_GAIN`。6 个 reference-supported base edges 的 P0 q95 source-total retention median=`0.909324`，ZERO median=`0.841774`；P0−ZERO median=`+0.055026`，P0 better=`5/6`、ZERO better=`1/6`、tie=`0/6`。
- supported P0 在同 source 全 destination pool 的 rank median=`1`；5/6 rank1，1/6 rank2。对 reference-unsupported frozen matched alternatives，P0 win/tie/loss=`29/0/1`，win rate=`96.7%`；ZERO win rate同样为 `96.7%`，说明 continuity 本身很强，而 P0-specific gain 是较小的附加量。
- 仅有 3 个相邻 frame pairs（472→473、482→483、487→488）同时具备连续 q95 reference mapping，共 6 个 base edges；6/6 都支持两个 manual targets，`shared_or_unresolved=100%`。因此该 outcome 有明显 sample sparsity 与 shared-region 限制。
- GT-blind 每 source 的最佳 P0 destination retention（1064 source nodes）median=`0.6838`，ZERO median=`0.6378`，best-delta median=`0`、mean=`+0.0293`；大量完整 matrix edges 为零交集，不能把 all-edge median 0 误写为 continuity failure。
- supported q97.5→q97.5 median=`0.9001`，supported q90 envelope median=`0.9121`；相对 q95 median差约 `-0.0122/-0.0038`。它们主要揭示局部 core/envelope 重排，而不是稳定提高 aggregate retention。
- supported edges 的 valid transport fraction 全部为 1，所以本 slice 中 source-total 与 conditional-valid 数值相同；boundary/truncated 分母公式已在全矩阵验证，但没有 reference-supported boundary evidence。

### 真实病例与限制

- F477→F478 `P0_CLEARLY_BETTER_THAN_ZERO`：P0 `0.8229` vs ZERO `0`，但 source q95 只有 6 pixels；它证明 warp direction/局部对齐可产生大差值，不代表稳健 PERSON continuity。
- F491→F492 `ZERO_BETTER_THAN_P0`：P0 `0.3294` vs ZERO `1.0`，source 19 pixels；优先诊断小 region、region resegmentation 与 lag1 M1 尺度，不修改 P0。
- F478→F479 split-like：1969-pixel extended source 对两个 destination lobes均有明显解释，主 edge P0 `0.4336`、ZERO `0.4190`，q90 `0.9075`；是 envelope continuity 明显高于单一 q95 lobe 的真实结构变化病例。
- F479→F480 merge-like：主 edge P0 `0.9416`、ZERO `0.9245`，q97.5 `0.9693`；两个 source lobes进入同一 extended destination region，支持“merge-like image-domain response”描述，不支持物理目标融合或 identity conclusion。
- F472→F473 P01/P02 supported edge：P0 q95 `0.2650`、ZERO `0.2685`、rank2；一个 frozen reference-unsupported matched alternative 达 `0.3134`，margin=`0.0484`。同时 q90 envelope=`0.8719`，表明弱层 continuity 强而 q95 主 region ordering 有一例被 alternative 反超。
- deterministic `P0_APPROX_EQUAL_ZERO` 选到了 `0 vs 0`，因为全 matrix q75 为 0；boundary case 是 1-pixel truncated source。两者是病例选择受 sparse/tiny regions 支配的真实方法限制，应在未来协议中加入完全 GT-blind minimum support stratum，但本轮结果保持不改。

### 停止点

- 当前只能称为 SAR image-domain one-step region-support temporal prerequisite，不能称 Optical–SAR motion consistency：本轮没有 raw optical angular dynamics，没有 `Δtheta_optical↔Δtheta_SAR`，没有 GT-blind admissibility pruning，没有 assignment/identity，也没有 SAR range/box output。
- 有理由讨论一个独立冻结、仍然最小的 M0B，因为 supported ordering 与 P0-specific gain 达到预注册条件；但必须以 6-edge/3-pair sparsity、100% shared explanations、tiny-region case-selection sensitivity 和 `TIME_SYNC_NOT_CALIBRATED` 为前置风险，不应直接进入 tracker 或最终定位。
- 本轮到此停止：未运行 lag3/lag5、M0B、optical angular dynamics、tracker、Hungarian、identity assignment、classifier、score fusion 或 SAR localization；未读取/依赖 `old_work`，未修改原始图像/标注、冻结 P0/B0R/C0–C3 或人工 SAR reference。
