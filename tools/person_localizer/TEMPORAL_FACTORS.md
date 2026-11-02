> Historical factor-interface note (2026-10-26/27). The later rc9 CLI integration is described in README.md; statements below about rc7 are dated history.

# PERSON 两目标时序因子接口

实现日期：2026-10-26 至 2026-10-27。当前是独立实验入口，rc7 默认 CLI 未替换。

输入是光学 query/方位区间、SAR 工作图、逐帧可测 mask、共享背景运输及其误差摘要。每个人的局部状态为 `残余位置 × supported/weak`；GM17 使用 81 个位置、2 个响应模式，两人共 26,244 个联合状态。状态中的位置是 SAR 显示图域支撑假设。

## 可替换的接口

|接口|输入与输出|当前实现|
|---|---|---|
|`joint_response_factors`|同一帧的 y、背景 Z、两个候选响应库 Q1/Q2、同一个训练 mask、冻结强度先验 → 联合/单人相对背景 log 因子|对非负半正态强度先验积分，每个场景像素只进入一次|
|`response_state_energy`|联合/单人图像因子 → 两人位置和响应模式的能量表|背景、只解释一人、同时解释两人四种状态|
|`transition_potential`|残余位置网格、实际 SAR 帧间隔、策略 → 相邻时刻势|公共运输坐标中的高斯位置增量，加响应模式持续性|
|`forward_backward`|节点能量、两人的边势、初始分布 → 前向/平滑联合权重|两目标分离转移、耦合节点的精确 sum-product|
|`viterbi`|相同节点/边/初始分布 → 联合路径|精确两目标 MAP，双回指|
|`ridge_readout`|冻结位置/模式、训练像素、独立测试像素 → 误差和强度|使用同一非负强度先验的后验模式，不读取测试像素拟合|

`temporal_factors.py` 同时保留第一版的逐帧 masked CV 因子，便于复现其弱状态退化。推荐使用 `amplitude_factors.py` 的响应因子和位移势。

组合方式：

```python
image_energy = response_state_energy(
    joint_response_factors(y, Z, Q1, Q2, frame_mask & train_fold, prior)
)
energy = image_energy + optical_energy1[:, None] + optical_energy2[None, :]
# 将各帧 energy 和相邻时刻 transition_potential 交给两个推理器。
filtered, smoothed = forward_backward(energies, edges1, edges2, prior1, prior2)
path = viterbi(energies, edges1, edges2, prior1, prior2)
```

图像因子不能按 query 各算一遍后作为独立似然相乘；两个基函数共同解释同一批像素。缺测帧返回中性图像因子，几何与状态转移仍保留；光学 HOLD 不因内部传播变成可输出观测。方位有限支撑超出局部网格时明确报几何冲突，不能悄悄降低几何权重。

公共运输目前沿用背景估计，误差以光学角度容差进入；尚无联合背景隐变量或显式残余速度。响应模糊尺度从 A 窗选择后冻结，响应强度在每帧积分/重估。相邻 SAR 图像仍有相关性；空间温度由 A 残差相关估计，归一化权重不是校准的人物身份概率。

## 实验入口

`tasks/person_gm17_factor_inference_20261026/run.py` 复现逐帧 mask 联合初始化和第一版失败；`run_amplitude_v2.py` 继承同一初始化，冻结 A 强度先验后执行第二版；`verify_results.py` 验证封存、积分、留出像素隔离和分量删除；`render_temporal.py` 输出无字媒体。

输出：`output/person_gm17_factor_inference_20261026/amplitude_prior_v2`。这是看过第一版结果后的开发迭代；尚未在 R01/R04/R07/R50 上回归此模块。
