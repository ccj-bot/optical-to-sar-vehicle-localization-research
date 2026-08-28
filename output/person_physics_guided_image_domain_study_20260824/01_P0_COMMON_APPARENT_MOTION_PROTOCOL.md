# P0 预注册协议：SAR公共表观运动可观测性

## 目的

检验只有SAR伪彩图像时，能否从不含PERSON目标的背景结构估计帧间公共表观运动，并在未调参场景中把静止PERSON的图像轨迹残差压缩到目标尺度以内。

这里估计的是图像域公共表观运动，不是载体真实运动或地理配准。

## 固定数据划分

- 发现集：R01ZF，3个已知静止PERSON。
- 留出集：R04ZF，3个已知静止PERSON；在R01完成模型和参数冻结前不参与选择。
- R02ZF、R03ZF：本阶段不参与拟合或选型，留给后续条件扩展。

## 输入

- 当前复核导出：D:\browser\person_SAR_fullframe_interpolation_review_1787483093904.json
- 多维探索数据：D:\profile\research\workspace\output\person_multidimensional_response_explorer_20260823\explorer_data.js
- 扇面几何：D:\profile\research\workspace\output\pseudocolor_azimuth_calibration_20260803\geometry\fan_geometry_report.json
- 原始SAR伪彩JPEG仅通过现有file URL只读访问。

## 拟合约束

1. PERSON框及其安全扩张区不得参与公共运动拟合。
2. 扇面外白区、20 m边界邻域和低有效像素区域不得作为稳定背景锚点。
3. 使用对伪彩增益更稳健的梯度、秩或边缘表征；近似JET索引只作为显示域代理。
4. 不能把目标框位移复制给附近背景作为负对照。
5. 背景锚点必须分为拟合与留出两组，目标区域不得参与模型选择。
6. 全局显示分布明显变化的帧单独分层报告，不能静默删除或直接归因于增益变化。

## 比较模型

- M0：无补偿/同传感器像素基线。
- M1：全局平移。
- M2：全局仿射。
- M3：距离—方位条件下的局部运动场；只有背景锚点数量和覆盖足够时启用。

时间间隔固定比较lag 1、3、5。模型阶数和参数只在R01选择，随后冻结并直接运行R04。

## 观测指标

- 拟合背景锚点残差与留出背景锚点残差；
- 补偿前后静止PERSON框中心残差；
- 不同距离/方位区域的残差分布；
- 显示分布变化、多人邻近和边界风险分层；
- 每对帧的配准置信度和不可比较原因。

## 操作性通过门槛

这些门槛只判定图像域方法是否值得继续，不代表物理真值：

1. R04留出背景中，冻结模型相对M0在至少75%的有效帧对上降低残差。
2. R04静止PERSON补偿后残差P90低于当前PERSON框短轴中位数，并且明显低于未补偿残差。
3. 结论在人工锚点帧子集与全部接受框子集上方向一致。
4. 不能依靠删除困难帧、目标框参与拟合或R04重新调参才能通过。

若任一核心门槛失败，则状态为IMAGE_ONLY_COMMON_MOTION_NOT_OBSERVABLE_AT_PERSON_SCALE，停止把框残差解释为目标独立运动。

## 预定输出

- common_motion_pair_metrics.csv
- background_anchor_holdout_metrics.csv
- stationary_person_residuals.csv
- comparability_registry.csv
- model_selection_R01.json
- frozen_validation_R04.json
- 补偿前后可视化和简短结论页

