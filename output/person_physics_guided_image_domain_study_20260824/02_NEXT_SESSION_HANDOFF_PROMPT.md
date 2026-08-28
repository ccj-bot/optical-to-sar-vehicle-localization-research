# 新 Session 交接 Prompt：PERSON P0 公共表观运动可观测性

请直接复制下方内容到新的 Codex session：

---

你现在接手 D:\profile\research 中的 PERSON 光学—SAR研究。不要重新发散课题方向，也不要直接进入分类器、候选排序或自动框。当前唯一任务是实施并完成 P0：仅凭SAR伪彩图像，检验场景公共表观运动在PERSON尺度上是否可观测。

当前冻结状态：P0_PROTOCOL_FROZEN_NOT_RUN。完成P0后停止，不要自动进入P1。

## 一、固定工作环境

- 唯一活动工作区：D:\profile\research\workspace
- old_work：档案区，禁止读取或作为运行依赖
- 默认解释器：D:\MINICONDA\envs\py311\python.exe
- 任务代码：D:\profile\research\workspace\tasks\person_physics_guided_image_domain_study_20260824
- 输出根目录：D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824
- 日志：D:\profile\research\workspace\logs\20260824_person_physics_guided_image_domain_study.md
- 原始光学、SAR图像和人工标注全部只读
- 当前worktree已有大量用户文件和无关变化；不得清理、回滚、移动或提交无关内容。没有用户明确授权时不要commit或push。
- 默认单代理执行，减少并发和token消耗。

## 二、开始前必须按顺序完整阅读

1. D:\profile\research\workspace\tasks\person_physics_guided_image_domain_study_20260824\README.md
2. D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\00_RESEARCH_CHARTER.md
3. D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\01_P0_COMMON_APPARENT_MOTION_PROTOCOL.md
4. D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\research_contract_v1.json
5. D:\profile\research\workspace\logs\20260824_person_physics_guided_image_domain_study.md
6. D:\profile\research\workspace\logs\s1_lr_gm_rm017_motion_coherent_response_flow_20260716.md
7. D:\profile\research\workspace\output\person_sar_motion_evidence_20260824\motion_evidence_summary.json

读取后先核验research_contract_v1.json中的三个输入SHA256；如果不一致，暂停计算并报告，不要静默换输入。

## 三、必须保持的研究语义

- PERSON研究对象是目标、场景散射、载体行为、孔径/处理和伪彩显示共同形成的条件性图像域观测响应，不是人体固有RCS模板。
- SAR框轨迹是图像坐标观测路径，不等于目标独立运动。
- 公共表观运动是图像配准量，不等于真实载体轨迹或地理配准。
- 同一个传感器像素不等于同一个物理背景点。
- 局部相似度只能作为显示重复性的软证据，不能证明PERSON身份、目标运动或物理散射稳定性。
- 光学只提供时间、行为、连续性假设和方位搜索壳；SAR保留最终定位权。
- 现有person_sar_motion_evidence_20260824是失败探针，只能用于展示旧语义为什么无效，不能作为P0成功基线。
- 全局直方图变化只能称GLOBAL_DISPLAY_DISTRIBUTION_CHANGE_CAUSE_UNKNOWN，不能直接归因于自动增益或成像链路跳变。

## 四、当前已确认的数据边界

- R01ZF、R02ZF、R03ZF、R04ZF共398个SAR帧。
- 11个run内PERSON ID，852个用户接受框：251个人工原生框、600个线性插值框、1个手调插值框。
- R01ZF和R04ZF中的6个PERSON物理上静止，适合验证公共表观运动；不是移动人体正样本。
- 当前只有光学图像、SAR伪彩JPEG/MP4、扇面几何和人工框。
- 没有原始幅度、复相位、载体位置/速度/姿态、孔径及运动补偿元数据，光学/SAR物理同步也未验证。

## 五、本 Session 的唯一目标

完成P0公共表观运动可观测性实验：

- 发现集：R01ZF。
- 留出集：R04ZF；在R01完成模型和参数冻结前，不得参与选型或调参。
- R02ZF、R03ZF本阶段不用于拟合、模型选择或通过判定。
- 时间间隔固定比较lag 1、3、5。
- 比较M0无补偿、M1全局平移、M2全局仿射、M3距离—方位局部运动场。只有锚点数量和空间覆盖足够时才能启用M3。
- 优先使用对伪彩和增益变化较稳健的梯度、边缘或局部秩表征；JET逆映射只能称显示域代理。

## 六、禁止的数据泄漏与捷径

1. PERSON框及安全扩张区不得参与公共运动拟合、模型选择或背景锚点筛选。
2. 扇面外白区、20m边界邻域和低有效像素区不得作为稳定背景锚点。
3. 背景锚点必须分为拟合与留出两组。
4. 不得把目标框位移复制给附近背景作为负对照。
5. 不得使用人工physical_target_id为运行时逻辑选择正确光学轨迹。
6. 不得通过删除困难帧、重新调R04参数或把插值平滑性当真实运动来获得通过。
7. 不得创建、移动或替换任何SAR标注框。

## 七、建议实施顺序

1. 在日志中追加P0启动记录、解释器、输入路径和哈希。
2. 建立扇面有效掩膜、PERSON扩张掩膜和显示分布变化分层。
3. 在R01生成背景锚点并固定拟合/留出划分。
4. 对lag 1、3、5运行M0至M3，先检查留出背景残差和直接可视化，不先看PERSON结果选模型。
5. 在R01冻结模型阶数、参数、锚点规则和不可比较规则，保存model_selection_R01.json。
6. 不做任何调整，直接运行R04，保存frozen_validation_R04.json。
7. 计算静止PERSON补偿前后残差，并分人工锚点子集与全部接受框子集报告。
8. 多模态视觉复核最差帧对，确认配准没有吸附到PERSON、扇面边界或大范围伪彩变化。
9. 输出P0_PASS或P0_FAIL；完成P0后停止，不自动进入P1。

## 八、预注册通过门槛

这些只是图像域可用性门槛，不代表物理真值：

1. R04留出背景中，冻结模型相对M0在至少75%的有效帧对上降低残差。
2. R04静止PERSON补偿后残差P90低于当前PERSON框短轴中位数，并明显低于未补偿残差。
3. 人工锚点帧子集与全部接受框子集的结论方向一致。
4. 结果不依赖目标区域参与拟合、R04调参或静默删除困难帧。

若失败，正式记录状态IMAGE_ONLY_COMMON_MOTION_NOT_OBSERVABLE_AT_PERSON_SCALE，并停止把框残差解释为目标独立运动。不要为了继续P1而放宽门槛。

## 九、代码和输出要求

- 主程序建议：D:\profile\research\workspace\tasks\person_physics_guided_image_domain_study_20260824\run_p0_common_apparent_motion.py
- P0输出建议放在：D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\p0_common_apparent_motion
- 至少生成：
  - common_motion_pair_metrics.csv
  - background_anchor_holdout_metrics.csv
  - stationary_person_residuals.csv
  - comparability_registry.csv
  - model_selection_R01.json
  - frozen_validation_R04.json
  - p0_result.json
  - 简洁的补偿前后可视化和README/报告
- research_contract_v1.json是冻结的预注册契约，不要为迎合结果而覆盖；运行结果写入独立的p0_result.json。
- 运行前后都更新现有日志，记录输入哈希、命令、输出、失败帧和最终状态。
- 使用D:\MINICONDA\envs\py311\python.exe运行和验证，不使用HFM_ENVI。

## 十、完成定义与汇报方式

只有以下事项全部完成才能称P0完成：输入哈希通过、R01选型冻结、R04不调参验证、最差帧视觉复核、输出文件验证、日志更新以及明确的P0_PASS/P0_FAIL。

最终用中文向用户汇报，先给结论，再说明：

- 图像域公共表观运动是否在PERSON尺度上可观测；
- 哪个模型被R01选中，R04是否独立通过；
- 静止PERSON残差改善多少；
- 哪些场景/帧不可比较；
- 能否进入P1，以及不能声称什么。

不要用大而玄乎的网页或机械统计代替直接配准图、残差证据和失败病例。

---
