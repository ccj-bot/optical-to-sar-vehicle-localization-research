# 预运行澄清：C2 response-region 的 percentile 与结构标签

- 澄清时间：2026-08-27，实验尚未运行
- 原因：只读代码审计确认，既有 reference percentile 使用固定 4096-bin CDF；候选实际输入场是 0.30 m 支持盘均值 `S(x)`，而不是基础 C2。为保持完全同义，在运行前澄清实现细节。

## 覆盖主协议第 5 节的两点

1. `B90/B95/B97.5` 使用既有 observation diagnostic 的 4096-bin CDF percentile field：

   `Bq(x) = valid_center(x) AND percentile_4096(S(x)) >= q`

   其中 `S(x)` 为冻结 C2 经过 `fixed_support_mean_v2` 后的实际候选场。报告必须同时区分“基础 C2”和“实际 S(x)”。

2. `EXTENDED_OR_RIDGE_RESPONSE` 的主轴条件改为更保守的：

   `major_extent_m > 1.80 m`

   即冻结 C2 最大响应直径 0.90 m 的两倍；elongation 条件仍为 `>=3.0`。原协议中的 `>0.90 m` 不再使用，避免把略大于单尺度支持的普通连通块过度解释为延展结构。

其余规则保持不变：8-connectivity、无 opening/closing/dilation、无面积过滤、无 GT 调阈值、区域先生成后评价。
