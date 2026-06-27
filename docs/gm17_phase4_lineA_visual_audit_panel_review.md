# GM17 第四阶段 A线可视化审阅面板

本文档只用于 A线：对 GM_RM011、GM_RM017、GM_RM019 中已有人工 GT 样本做可视化审阅。

这些面板是人工审阅用的派生图片，不是推理结果，不是候选选择结果，不是打分结果，不是训练数据，不是校准结果，也不是候选库产物。

如果面板里画出了光学目标框，它也只用于人工参照，不能转成打分特征、阈值、训练标签、校准依据、候选选择规则或候选库修改依据。

本页没有使用 A001 作为候选库来源，也没有使用 A005 作为时间先验来源。没有使用候选排名、GM17 已选候选、交并比、中心误差、oracle 排名、召回率或模型性能字段。

本页不授权打分阈值、调参常数、学习权重、缺失策略、因子激活、候选库修改、候选生成、oracle 选择或模型性能结论。

## 画框和解析约定

SAR 图中的红色旋转框来自 A019 的 `final_cx`、`final_cy`、`final_w`、`final_h`、`final_heading_deg`。绘图时只按图像坐标显示：横向为 x，向右增加；纵向为 y，向下增加；记录里的 `final_heading_deg` 直接作为红框宽轴方向使用。这个约定只用于显示，不代表已经修正或重新解释角度。

SAR 局部放大图以 GT 中心为中心，围绕红框留出审阅边距，并在图像边界处截断。光学目标框只从 `review_queue.csv` 里的 `opt_x1`、`opt_y1`、`opt_x2`、`opt_y2` 解析；匹配条件是场景、目标身份、SAR 帧号，以及有样本编号时同时匹配样本编号。若光学框坐标为空或多匹配，就不自动画框。

## 审阅口径

本轮审阅不是修 GT，也不是定规则。目标是把人工标注框在 SAR 图上的含义说清楚，尤其是宽高存储约定、可见范围、截断、遮挡和 SAR 散射逸散。

`final_w / final_h` 不是物理意义上的车长 / 车宽。它只是当前旋转框两个存储轴的长度比。如果视觉长轴存进 `final_h`，比值会小于 1；如果视觉长轴存进 `final_w`，比值会大于 1。因此审阅时应记录“视觉长轴更像存在 `final_w` 还是 `final_h`”，不要把 `final_w/final_h < 1` 直接解释成车辆形状异常。

SAR GT 框优先理解为对主要车体支持区域的人工框定，而不是对所有 SAR 亮斑、拖尾、旁瓣或逸散散射的全量包围。远离主体、断开的亮斑可以记录为“散射逸散 / 不确定支持”，但不要自动当作车体边界。如果主体被截断或只显示部分车体，应记录“完整车体范围不确定”或“可见/部分范围风险”。

建议填写重点：

- SAR 框覆盖评价：红框是否覆盖主要连续 SAR 支持，而不是是否覆盖全部散射。
- SAR 完整车体还是可见部分：判断更像完整车体范围、可见/部分范围，还是无法确定。
- 宽高存储约定：记录视觉长轴更接近 `final_w` 还是 `final_h`，以及该判断是否受截断或角度影响。
- 角度约定备注：只记录视觉一致、90 度互换、180 度等价、角度回绕或不确定；不要修正角度。
- 失败模式含义：只写约定说明、失败模式记录、未来路线建议、后推理评估备注或不确定性备注。

## 长轴和角度共性提取

这一节只做审阅辅助，不定义车头方向，不定义航向因子，也不进入推理或打分。

统一读法：

- 车体长轴：`max(final_w, final_h)`。
- 车体短轴：`min(final_w, final_h)`。
- 长轴存储字段：长轴当前存放在 `final_w` 还是 `final_h`。
- 无符号长轴角：如果长轴在 `final_w`，使用记录角度 `final_heading_deg`；如果长轴在 `final_h`，使用 `final_heading_deg + 90`。然后折叠到 0 到 180 度，因为车头和车尾方向在当前审阅中不区分。

这个角度只能表示“车体长轴方向大致如何”，不能表示车头朝向，也不能直接变成候选选择规则。

| 样本 | 长轴存储字段 | 长轴长度 | 短轴长度 | 长短轴比 | 无符号长轴角 |
|---|---:|---:|---:|---:|---:|
| VA001 | `final_h` | 179.282 | 68.004 | 2.636 | 92.0 度 |
| VA002 | `final_w` | 194.666 | 70.198 | 2.773 | 177.0 度 |
| VA003 | `final_w` | 131.942 | 63.440 | 2.080 | 1.0 度 |
| VA004 | `final_h` | 149.827 | 80.740 | 1.856 | 50.0 度 |
| VA005 | `final_w` | 128.333 | 62.847 | 2.042 | 171.0 度 |
| VA006 | `final_h` | 192.525 | 90.671 | 2.123 | 88.0 度 |
| VA007 | `final_w` | 127.942 | 63.440 | 2.017 | 162.0 度 |
| VA008 | `final_w` | 163.847 | 68.644 | 2.387 | 178.0 度 |
| VA009 | `final_w` | 139.765 | 65.852 | 2.122 | 178.0 度 |
| VA010 | `final_w` | 144.761 | 71.310 | 2.030 | 1.0 度 |
| VA011 | `final_w` | 137.811 | 70.630 | 1.951 | 178.0 度 |
| VA012 | `final_w` | 163.847 | 68.644 | 2.387 | 178.0 度 |
| VA013 | `final_w` | 133.387 | 76.758 | 1.738 | 11.0 度 |
| VA014 | `final_w` | 162.135 | 73.335 | 2.211 | 176.0 度 |
| VA015 | `final_h` | 136.592 | 75.056 | 1.820 | 89.0 度 |
| VA016 | `final_w` | 151.235 | 69.393 | 2.179 | 176.0 度 |

## 后续推进口径

当前不把样本预先固定成若干物理类别。审阅先提取可复核的共性信息：人工框是否覆盖主要车体区域，是否触及 SAR 有效区边界，长轴存储和长轴角度是否稳定，是否存在离主体较远的散射逸散，以及是否需要通过时序补充解释进入或退出。

GT 框的工作理解是：人工框通常覆盖绝大部分车体区域，可按车体主体范围理解；只有当 SAR 有效区截断、图像边界或明显局部可见时，才把完整范围不确定作为风险提示。已有补充 GT 仍按人工 GT 处理；自动检测到框体落在 SAR 有效区外时，只写入 GT 表备注，作为人工复核提示，不改变坐标、状态、候选或推理逻辑。

截断、遮挡和散射逸散暂不拆成硬标签。若光学信息不能稳定支持某个细分类，就只记录可见现象和不确定性，避免把小样本现象提前变成规则。

仅 SAR 样本优先作为时序补充线索来整理进入和退出逻辑。它可以帮助解释目标何时进入或离开可见区，但不作为候选生成、候选修改或主线选择规则。

## 文件概览

| 项目 | 内容 |
|---|---|
| 面板图片目录 | `docs/assets/gm17_phase4_lineA_visual_audit_panels/` |
| 面板数量 | 16 |
| 光学目标已解析 | 13 |
| 光学目标未解析 | 3 |
| 光学目标多匹配 | 0 |
| 图片读取失败 | 0 |

## VA001 - GM_RM011 低长宽比样例

![VA001 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA001_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000276.png`
- 原始光学图：`D:\profile\research\data\GM_RM011\GM_RM011_frames\000132.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 1295.159 |
| 中心 y | `final_cy` | 1178.729 |
| 框宽 | `final_w` | 68.004 |
| 框高 | `final_h` | 179.282 |
| 宽高比 | `aspect_ratio` | 0.3793 |
| 记录角度 | `final_heading_deg` | 2.000 |
| 旋转框面积 | `final_rot_area_px` | 12191.893 |
| 外接轴对齐框面积 | `final_ax_area_px` | 13474.247 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断（原始值：`truncated`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 无（原始值：`none`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 未解析（原始值：`unresolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `saronly` |
| 光学框坐标 | `` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | review_queue.csv 有匹配行，但光学框坐标为空或无效。 |

### VA001 参考填写草稿

下面只是参考写法，人工审阅时可以直接改。

```text
视觉发现：红色旋转框覆盖底部主要 SAR 支持区域；上方存在较明显散射或逸散，不宜直接视为完整车体边界。
SAR框覆盖评价：覆盖主要支持，但逸散是否属于车体边界仍不确定。
SAR完整车体还是可见部分：更像严重截断下的可见或部分车体范围，完整车体范围不确定。
宽高存储约定：本例视觉长轴更接近 final_h；不能把 final_w/final_h 小于 1 直接解释为物理异常。
角度约定备注：当前仅按记录角度显示，暂不修正角度约定。
光学对应关系评价：光学目标未解析，不据此判断光学和 SAR 的对应质量。
截断遮挡评价：A021 标为截断、严重、无遮挡；审阅重点是截断和散射逸散对 GT 范围的影响。
失败模式含义：可作为 GM_RM011 低宽高比、严重截断、SAR 逸散的人工复核样例。
允许后续使用：约定说明；失败模式记录；不确定性备注。
禁止后续使用：不得用于阈值、打分、候选选择、因子激活、候选库修改、候选生成或模型性能结论。
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA002 - 高长宽比样例

![VA002 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA002_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000372.png`
- 原始光学图：`D:\profile\research\data\GM_RM017\GM_RM017_frames\000179.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 1010.409 |
| 中心 y | `final_cy` | 876.567 |
| 框宽 | `final_w` | 194.666 |
| 框高 | `final_h` | 70.198 |
| 宽高比 | `aspect_ratio` | 2.7731 |
| 记录角度 | `final_heading_deg` | -3.000 |
| 旋转框面积 | `final_rot_area_px` | 13665.163867999998 |
| 外接轴对齐框面积 | `final_ax_area_px` | 15903.3 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 遮挡（原始值：`occluded`） |
| 情况程度 | `condition_degree` | 轻度（原始值：`mild`） |
| 截断程度 | `truncation_degree` | 无（原始值：`none`） |
| 遮挡程度 | `occlusion_degree` | 轻度（原始值：`mild`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `164.258, 310.422, 343.952, 377.454` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA003 - 轴对齐外接面积极值样例

![VA003 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA003_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000005.png`
- 原始光学图：`D:\profile\research\data\GM_RM011\GM_RM011_frames\000002.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 1151.642 |
| 中心 y | `final_cy` | 1246.802 |
| 框宽 | `final_w` | 131.942 |
| 框高 | `final_h` | 63.440 |
| 宽高比 | `aspect_ratio` | 2.0798 |
| 记录角度 | `final_heading_deg` | 1.000 |
| 旋转框面积 | `final_rot_area_px` | 8370.40048 |
| 外接轴对齐框面积 | `final_ax_area_px` | 8744.4 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断（原始值：`truncated`） |
| 情况程度 | `condition_degree` | 中度（原始值：`moderate`） |
| 截断程度 | `truncation_degree` | 中度（原始值：`moderate`） |
| 遮挡程度 | `occlusion_degree` | 无（原始值：`none`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `2.379, 278.506, 729.620, 599.001` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA004 - 轴对齐外接面积极值样例

![VA004 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA004_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000001.png`
- 原始光学图：`D:\profile\research\data\GM_RM011\GM_RM011_frames\000000.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 1282.522 |
| 中心 y | `final_cy` | 1152.115 |
| 框宽 | `final_w` | 80.740 |
| 框高 | `final_h` | 149.827 |
| 宽高比 | `aspect_ratio` | 0.5389 |
| 记录角度 | `final_heading_deg` | -40.000 |
| 旋转框面积 | `final_rot_area_px` | 12097.03198 |
| 外接轴对齐框面积 | `final_ax_area_px` | 26360.5 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断（原始值：`truncated`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 无（原始值：`none`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `710.731, 319.801, 799.548, 509.427` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA005 - 边界、掩膜或可见范围疑似样例

![VA005 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA005_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000012.png`
- 原始光学图：`D:\profile\research\data\GM_RM011\GM_RM011_frames\000006.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 1152.377 |
| 中心 y | `final_cy` | 1243.565 |
| 框宽 | `final_w` | 128.333 |
| 框高 | `final_h` | 62.847 |
| 宽高比 | `aspect_ratio` | 2.0420 |
| 记录角度 | `final_heading_deg` | 351.000 |
| 旋转框面积 | `final_rot_area_px` | 8065.344051 |
| 外接轴对齐框面积 | `final_ax_area_px` | 11220.3 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断（原始值：`truncated`） |
| 情况程度 | `condition_degree` | 中度（原始值：`moderate`） |
| 截断程度 | `truncation_degree` | 中度（原始值：`moderate`） |
| 遮挡程度 | `occlusion_degree` | 无（原始值：`none`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `1.403, 266.243, 798.902, 597.899` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA006 - 边界、掩膜或可见范围疑似样例

![VA006 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA006_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000252.png`
- 原始光学图：`D:\profile\research\data\GM_RM011\GM_RM011_frames\000121.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 1060.390 |
| 中心 y | `final_cy` | 1184.032 |
| 框宽 | `final_w` | 90.671 |
| 框高 | `final_h` | 192.525 |
| 宽高比 | `aspect_ratio` | 0.4710 |
| 记录角度 | `final_heading_deg` | -2.000 |
| 旋转框面积 | `final_rot_area_px` | 17456.434 |
| 外接轴对齐框面积 | `final_ax_area_px` | 19035.969 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断（原始值：`truncated`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 无（原始值：`none`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `yolo11l_gm_rm011_000121_Y01_car_0.62` |
| 光学检测标签 | `yolo11l_car` |
| 光学框坐标 | `0.286, 267.625, 182.487, 485.781` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA007 - 严重截断样例

![VA007 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA007_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000033.png`
- 原始光学图：`D:\profile\research\data\GM_RM011\GM_RM011_frames\000016.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 1175.642 |
| 中心 y | `final_cy` | 1246.802 |
| 框宽 | `final_w` | 127.942 |
| 框高 | `final_h` | 63.440 |
| 宽高比 | `aspect_ratio` | 2.0167 |
| 记录角度 | `final_heading_deg` | -18.000 |
| 旋转框面积 | `final_rot_area_px` | 8116.640479999999 |
| 外接轴对齐框面积 | `final_ax_area_px` | 14110.2 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断（原始值：`truncated`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 无（原始值：`none`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `48.309, 282.444, 797.900, 597.780` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA008 - 严重截断样例

![VA008 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA008_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000317.png`
- 原始光学图：`D:\profile\research\data\GM_RM017\GM_RM017_frames\000152.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 796.483 |
| 中心 y | `final_cy` | 941.214 |
| 框宽 | `final_w` | 163.847 |
| 框高 | `final_h` | 68.644 |
| 宽高比 | `aspect_ratio` | 2.3869 |
| 记录角度 | `final_heading_deg` | -2.000 |
| 旋转框面积 | `final_rot_area_px` | 11247.113468000001 |
| 外接轴对齐框面积 | `final_ax_area_px` | 12347.8 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断并遮挡（原始值：`truncated+occluded`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 严重（原始值：`severe`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `2.727, 300.000, 70.909, 360.000` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA009 - 严重截断样例

![VA009 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA009_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000335.png`
- 原始光学图：`D:\profile\research\data\GM_RM011\GM_RM011_frames\000161.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 1072.276 |
| 中心 y | `final_cy` | 1251.935 |
| 框宽 | `final_w` | 139.765 |
| 框高 | `final_h` | 65.852 |
| 宽高比 | `aspect_ratio` | 2.1224 |
| 记录角度 | `final_heading_deg` | -2.000 |
| 旋转框面积 | `final_rot_area_px` | 9203.80478 |
| 外接轴对齐框面积 | `final_ax_area_px` | 10036.4 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断（原始值：`truncated`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 无（原始值：`none`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `2.727, 300.000, 280.909, 594.545` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA010 - 严重截断样例

![VA010 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA010_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000506.png`
- 原始光学图：`D:\profile\research\data\GM_RM011\GM_RM011_frames\000243.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 1058.974 |
| 中心 y | `final_cy` | 1249.690 |
| 框宽 | `final_w` | 144.761 |
| 框高 | `final_h` | 71.310 |
| 宽高比 | `aspect_ratio` | 2.0300 |
| 记录角度 | `final_heading_deg` | 1.000 |
| 旋转框面积 | `final_rot_area_px` | 10322.90691 |
| 外接轴对齐框面积 | `final_ax_area_px` | 10777.3 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断（原始值：`truncated`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 无（原始值：`none`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `5.455, 362.727, 381.818, 594.545` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA011 - 严重截断样例

![VA011 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA011_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000510.png`
- 原始光学图：`D:\profile\research\data\GM_RM011\GM_RM011_frames\000245.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 1090.811 |
| 中心 y | `final_cy` | 1251.093 |
| 框宽 | `final_w` | 137.811 |
| 框高 | `final_h` | 70.630 |
| 宽高比 | `aspect_ratio` | 1.9512 |
| 记录角度 | `final_heading_deg` | 178.000 |
| 旋转框面积 | `final_rot_area_px` | 9733.59093 |
| 外接轴对齐框面积 | `final_ax_area_px` | 10570.0 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断（原始值：`truncated`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 无（原始值：`none`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `2.727, 316.364, 515.455, 591.818` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA012 - 严重遮挡样例

![VA012 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA012_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000317.png`
- 原始光学图：`D:\profile\research\data\GM_RM017\GM_RM017_frames\000152.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 796.483 |
| 中心 y | `final_cy` | 941.214 |
| 框宽 | `final_w` | 163.847 |
| 框高 | `final_h` | 68.644 |
| 宽高比 | `aspect_ratio` | 2.3869 |
| 记录角度 | `final_heading_deg` | -2.000 |
| 旋转框面积 | `final_rot_area_px` | 11247.113468000001 |
| 外接轴对齐框面积 | `final_ax_area_px` | 12347.8 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断并遮挡（原始值：`truncated+occluded`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 严重（原始值：`severe`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `2.727, 300.000, 70.909, 360.000` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA013 - 严重遮挡与 GM_RM019 低样本代表样例

![VA013 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA013_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM019\GM_RM019_SARframes\000000.png`
- 原始光学图：`D:\profile\research\data\GM_RM019\GM_RM019_frames\000000.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 965.935 |
| 中心 y | `final_cy` | 1197.992 |
| 框宽 | `final_w` | 133.387 |
| 框高 | `final_h` | 76.758 |
| 宽高比 | `aspect_ratio` | 1.7378 |
| 记录角度 | `final_heading_deg` | 11.000 |
| 旋转框面积 | `final_rot_area_px` | 10238.519346 |
| 外接轴对齐框面积 | `final_ax_area_px` | 14674.6 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断并遮挡（原始值：`truncated+occluded`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 严重（原始值：`severe`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 未解析（原始值：`unresolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | review_queue.csv 有匹配行，但光学框坐标为空或无效。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA014 - 严重遮挡样例

![VA014 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA014_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png`
- 原始光学图：`D:\profile\research\data\GM_RM017\GM_RM017_frames\000145.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 689.677 |
| 中心 y | `final_cy` | 947.700 |
| 框宽 | `final_w` | 162.135 |
| 框高 | `final_h` | 73.335 |
| 宽高比 | `aspect_ratio` | 2.2109 |
| 记录角度 | `final_heading_deg` | -4.000 |
| 旋转框面积 | `final_rot_area_px` | 11890.170224999998 |
| 外接轴对齐框面积 | `final_ax_area_px` | 14093.7 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断并遮挡（原始值：`truncated+occluded`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 严重（原始值：`severe`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 未解析（原始值：`unresolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | review_queue.csv 有匹配行，但光学框坐标为空或无效。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA015 - 严重遮挡样例

![VA015 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA015_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000244.png`
- 原始光学图：`D:\profile\research\data\GM_RM011\GM_RM011_frames\000117.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 1047.428 |
| 中心 y | `final_cy` | 1208.114 |
| 框宽 | `final_w` | 75.056 |
| 框高 | `final_h` | 136.592 |
| 宽高比 | `aspect_ratio` | 0.5495 |
| 记录角度 | `final_heading_deg` | 359.000 |
| 旋转框面积 | `final_rot_area_px` | 10252.049152000001 |
| 外接轴对齐框面积 | `final_ax_area_px` | 10675.9 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断并遮挡（原始值：`truncated+occluded`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 严重（原始值：`severe`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `0.000, 248.182, 114.545, 387.273` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

## VA016 - 严重遮挡样例

![VA016 审阅面板](assets/gm17_phase4_lineA_visual_audit_panels/VA016_panel.png)

- 原始 SAR 图：`D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000310.png`
- 原始光学图：`D:\profile\research\data\GM_RM017\GM_RM017_frames\000149.png`

### SAR GT 信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 中心 x | `final_cx` | 756.110 |
| 中心 y | `final_cy` | 941.093 |
| 框宽 | `final_w` | 151.235 |
| 框高 | `final_h` | 69.393 |
| 宽高比 | `aspect_ratio` | 2.1794 |
| 记录角度 | `final_heading_deg` | 176.000 |
| 旋转框面积 | `final_rot_area_px` | 10494.650355000002 |
| 外接轴对齐框面积 | `final_ax_area_px` | 12421.3 |

### 可见性、截断和遮挡信息

| 项目 | 原始字段 | 值 |
|---|---|---|
| 情况类型 | `condition_type` | 截断并遮挡（原始值：`truncated+occluded`） |
| 情况程度 | `condition_degree` | 严重（原始值：`severe`） |
| 截断程度 | `truncation_degree` | 严重（原始值：`severe`） |
| 遮挡程度 | `occlusion_degree` | 严重（原始值：`severe`） |

### 光学目标解析信息

| 项目 | 值 |
|---|---|
| 解析状态 | 已解析（原始值：`resolved`） |
| 光学检测编号 | `` |
| 光学检测标签 | `` |
| 光学框坐标 | `0.102, 315.387, 18.400, 334.214` |
| 解析来源 | review_queue.csv 中的 opt_x1、opt_y1、opt_x2、opt_y2 |
| 解析备注 | 已从 review_queue.csv 的 opt_x1、opt_y1、opt_x2、opt_y2 解析光学目标框，仅作人工参考。 |

### 人工填写区

```text
视觉发现：
SAR框覆盖评价：
SAR完整车体还是可见部分：
宽高存储约定：
角度约定备注：
光学对应关系评价：
截断遮挡评价：
失败模式含义：
允许后续使用：
禁止后续使用：
审阅备注：
审阅状态：待审 / 已审 / 需要复查
```

