# 光学辅助 SAR 定位研究

本仓库保存研究代码、方法说明与证据边界。光学提供对象线索、方位和搜索先验；SAR 提供当前响应与定位依据。原始采集、模型权重、生成图像和视频在仓库外保存。

## 当前阶段（2026-11-02）

|研究线|已形成的资产|尚未成立的结论|
|---|---|---|
|PERSON|rc9运行代码；六场景配置与结果已在本地冻结；数值回归和复核界面已验证|六场景独立识别准确率；R07响应归属与001/007关联|
|CAR数据|R35帧表、坐标、时间、来源及观测/参考隔离读取器|完整时序人工真值；光学候选或SAR片段的物理身份|
|CAR连续标注|三辆静止车SAR358–494的位置/轴向修订；亮带侧单端6px余量|逐帧实测整车尺寸、弱远端轮廓与独立精度|
|机制研究|补偿累积、局部响应与整车范围差异、邻车竞争及失败反例|从高图像相关性直接推导车辆归属或物理恢复|

当前车辆顺序为：中部完整静止车连续参考 → 完整车辆时序预测 → 边缘/近场机制。SAR-only空间观测研究在独立仓库/分支维护，不与这里的光学辅助结果合并计分。

## 入口

- [逐节点研究记录：为什么、怎么做、结果、解释与下一步](docs/research/RESEARCH_NODES_20261102.md)
- [发布前独立语义复核](docs/research/INDEPENDENT_SEMANTIC_REVIEW_20261102.md)

- [当前研究状态与证据](docs/research/STATUS_20261102.md)
- [关键设想、验证与失败](docs/research/FINDINGS_AND_OPEN_QUESTIONS.md)
- [复现依赖与运行范围](docs/research/REPRODUCIBILITY.md)
- [PERSON运行代码](tools/person_localizer/README.md)
- [CAR数据接口](tools/car_data_contract/README.md)
- [连续标注修订](tasks/car_central_static_repair_20261102/README.md)
- [亮带侧余量修订](tasks/car_bright_band_margin_20261102/README.md)

历史Phase3因子审计、旧交接和既有实验继续保留。它们不是当前科研进度的完整描述，也不应与后续样本和指标混成一次结果。

## 数据与使用范围

源码快照包含可复用组件和带明确数据依赖的研究脚本；不等于上传了整个本地冻结包。`output/`中的标注、视频、数组、参考快照和封存结果不在Git中。参见[来源索引](docs/research/SOURCE_PROVENANCE.json)和[资产规则](docs/research/ARTIFACTS.md)。
