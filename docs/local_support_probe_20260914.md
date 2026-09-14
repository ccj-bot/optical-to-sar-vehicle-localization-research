# 局部原场支撑与允许断裂的中尺度组织：A059 探索

2026-09-14 · feature/oty2-sar-vehicle-morphology-object

## 先看结果：局部支撑有所改善，整体组织仍未解决

本轮可以把 A059 主、弱响应中的部分组织表示成**真实像素路径的集合，附带不填充的间隔剖面**，不再以 PCA chord 代替支撑。冻结 native 窗口的共同内部中，这些局部支撑保持一致。但这不是完整主带恢复，更不是正确目标归属：原图同一亮核仍有竞争方向解释，shuffled 也产生看似合理的同向片段和低谷。

先看下图四个局部案例。每行左为原场，中为实际支撑像素及端点，右为间隔上的 I0 剖面。青色虚线只是取样位置，绝不是亮桥。G4/G73/G96/G13 均为计算后人工选择的说明案例，不是程序 winner。

![主带、弱带、竞争方向和打乱图的具体支撑](../output/local_support_probe/figures/FOCUSED_GROUP_CASES.png)

因此，本轮的进展是“可检查的局部支撑和断裂”，尚不是“已经忠实表达整车组织”。下一步应继续完善 primitive 的二维宽度和方向歧义，仅做小范围 grouping 试验，不回到完整 MorphologyObject 关系扩张。

## 1. 数据、冻结条件与表示边界

只运行七个条件：已有 A059 original/shuffled、上一轮精确 A_cores_only/C_dark_middle_raised，以及 GM17 f344 三个 native aperture。没有道路负样本、时序、车辆评分、检测框或目标 Mask。保存的支撑布尔图仅为路径诊断，不是车辆分割。

original/shuffled 使用已提交示例的原 I0，验证灰度多重集完全一致。这是既有 GT 坐标图的 bilinear 显示采样；**不把它叫 native 像素**。A/C 直接读取旧干预的字段与对象，不重做近似干预。C 是指定矩形内 max(I0,q85)，并非整个矩形都恒定；原先超过平台的高值仍保留。

native 实验直接截取灰度源图 000344.png，同一坐标像素值完全一致，无旋转、resize、bilinear 或新增归一化。W3 与上一轮冻结 wide 场核验一致。所有数据仍是显示域响应，不是复数 SAR、物理散射中心或 RCS。I1/I2/I4 是同源尺度视图，不是独立观测。

| 窗口 | 冻结范围 [xmin,ymin,xmax,ymax) | 尺寸 |
|---|---|---|
| W1 | [1050,965,1230,1055) | 180×90 |
| W2 | [1020,935,1260,1070) | 240×135 |
| W3 | [990,900,1290,1080) | 300×180 |

三个窗口分别运行，不向小窗口补读外部 halo。配置及 core 在纠正后的实验前冻结，未按结果调参。主/弱/间隔 ROI 只用于事后读图，core 不读取 GT 或这些 ROI。完整字段、路径、分组成员及剖面见浏览页和 records/，冻结记录见 PRE_RUN_FREEZE.json 与 original_native_freeze.json。

## 2. 当前 segment 为何失败

旧机制把三个层次混在一起：全 aperture 分位数提出 connected support，连通块吞并决定其整体形状，再用 PCA 长宽比决定是否输出拟合段。因此，一处真实条带仍在，整个连通块却可能因外围加入而变胖，导致整段被拒绝。拟合线还可能跨过内部暗断口，常值平台则可能借面积与长宽比成为大段。

下面追踪同一 native 主带像素 (1140,1035) 所在的旧 q80 连通块，而不是更换候选：

| aperture | q80 显示灰度水平 | 该连通支持面积 px | PCA 长宽比 | 旧规则 |
|---|---:|---:|---:|---|
| W1 | 65.6432 | 2565 | 4.468 | 接受 |
| W2 | 60.7556 | 3300 | 4.259 | 接受 |
| W3 | 58.0051 | 5795 | 1.549 | 拒绝 |

![旧水平变化、连通吞并及整段拒绝](../output/local_support_probe/figures/BASELINE_LEVELS_AND_REJECTION.png)

这是该具体组件的失败链，不是一般车辆判别统计。q65 下该组件在三个窗口都被拒绝；稳定的空输出不是恢复成功。预算不是这里的主因，primitive 本身已丢掉条带。

## 3. 两条局部 proposal 路线及三种语义

路线 A 是有限 13×13 邻域的严格局部分位秩支撑：I0 高于邻域第 78 百分位。它没有整窗分位数依赖，但产生大量细碎支持；其连通区域只叫 UNRESOLVED_SUPPORT_REGION，不升级成 ridge。外围连接仍可能改变整个连通块的 extent。局部分位数不是“发现了车辆阈值”。

路线 B 直接提出原场 crest 路径。四个冻结数字方向上，每点须同时高于横向两侧距离 2、4 的邻点；I0 与 I1 都成立才提出候选。沿该方向至少三个连续实际像素构成 path。不存在 PCA 插值端点，不补中间缺失像素。I1 为 sigma=1、radius=3 的有限高斯；I2/I4 分别 radius=6/12，仅记录同一原路径的尺度变化。

每个 fragment 保存真实 support_xy、path_xy、首末端点、数字局部形状、方向、长度和尺度，以及 I0/I1/I2/I4 每点的中心/两侧样本及 crest 布尔见证。拟合 axis 不代替 support。内部一旦局部支撑断开就分成不同路径；断口存在于片段间，而非用一条假连续线跨越。

三种语义有效，但不是强迫互斥、穷尽的目标类别：

| 语义 | 本轮可检查含义 | 不能推出 |
|---|---|---|
| CONTINUOUS_RIDGE | 实际相邻像素构成满足局部 crest 条件的路径 | 物理散射连续、完整条带宽度、车辆部件 |
| FRAGMENT_GROUP | 有限范围内实际片段的组织假设，保留间隔 | 正确整体归属、每个间隔都是暗谷、唯一方向 |
| UNSUPPORTED_CHORD | 旧 chord 固定走廊里未找到规定的原场支撑路径 | 更宽、弯曲或断裂的真实条带不存在 |

旧 chord 审计冻结为 2px 走廊、3px 端点邻域和 8 连通原支持路径。A059 的三个旧 chord、shuffled 的十五个在此约定下均不满足；C 的两个短 chord 满足、另两个不满足。不能把“严格支撑判据没找到”当成“图像无结构”。

## 4. A059 的 group 到底保留什么

group 是非传递的 anchor 邻域假设：同方向、中心距离≤24px、横向偏移≤3px、最近实际端点间隔≤12px、union 轴向 extent≤48px。数值是冻结的局部提案约定，不是车辆定义。保留重叠替代组，不递归吞并、不排名。

group support 精确等于成员实际像素的并集。每一候选间隔保存两端、离散取样线、I0 剖面、缺失局部支撑位置及谷点。**不满足 crest 不等于暗**；是否有暗谷必须回看 I0。

G4 的 F0_2/F0_5/F0_6 位于主亮带约 x=62–98,y=8–9，表达局部延展及分裂。F0_5 为真实 30 点路径；I0/I1 30 点满足同位置 crest，I2 保留24点，I4仅5点。组内部分间隔并不呈现暗谷，因此不能宣称所有片段均“由暗谷分隔”。

G73 的五条实际片段位于弱带约 x=37–80,y=61–63，既有串列也有重叠平行行，暗断口没有被补成支撑。F0_103 的22点在 I0/I1/I2 均保留 crest，I4仍有17点。较弱的组织可以比更亮但较细碎的局部在中尺度保留更久；这仅是具名路径的观察。

![原路径上多个尺度的见证](../output/local_support_probe/figures/SCALE_WITNESSES.png)

这两个小组不是覆盖整个主侧/弱侧的完整对象。本轮未重新形成一个可唯一命名为“主车辆条带”的大 segment。G96 在同一强核附近给出竞争的竖向 group，说明四方向路径可能对亮核生成多种解释。

## 5. shuffled 与平台：哪里改善，哪里仍失败

![原图的连续场与实际局部支撑](../output/local_support_probe/figures/A059_original_support.png)

![相同灰度多重集的 shuffled 支撑](../output/local_support_probe/figures/A059_shuffled_support.png)

shuffled G13 的 F0_32（y56,x82–84）和 F0_34（y59,x74–78）真实存在，并能给出同向排列和低谷剖面。这些不是捏造像素，却仍是偶然几何。故“同向 + 有间隔 + 有谷”不能自动升级成 original 的高级组织。本轮阻止了无支撑 chord 冒充连续结构，但**没有解决随机片段被误解成高层组织**。分歧开始出现在局部 group 的语义提升，而不仅是支撑是否真实。

![精确 A 干预](../output/local_support_probe/figures/A_cores_only_support.png)

![精确 C 干预](../output/local_support_probe/figures/C_dark_middle_raised_support.png)

A 的11483个最低平台像素没有 oriented support；C 恒值平台区域经9×9内缩后1490像素也没有支撑。全常值合成场不产生 rank support、fragment 或 group。原因是严格的双侧局部 contrast 在常值内部自然不成立，而非面积/PCA惩罚。

平台边缘、角点及 C 中保留的原高值岛仍可产生真实局部路径；本轮不声称免疫所有低纹理平台伪影。填暗内部还会改变两侧局部条件，不能把干预差异归结成单一“形态消失分数”。

## 6. native aperture stability：支撑稳定不等于整体解析成功

![同一 native 主侧的三窗口结果](../output/local_support_probe/figures/NATIVE_MAIN.png)

![同一 native 弱侧的三窗口结果](../output/local_support_probe/figures/NATIVE_WEAK.png)

![主弱之间的 native 间隔](../output/local_support_probe/figures/NATIVE_GAP.png)

两次比较 W2|W1 与 W3|W1 都得到：局部 rank 支撑83个变化像素、oriented 支撑50个、group union支撑49个；避开 W1 边界9px后这三者均为0。I0/I1 crest 的有限依赖半径为7px，最小三点 run 再需2px，所以 interior 支撑一致有局部性解释，**不是车辆特异性的实验证明**。group union 的一致是本次观察，不推广成9px的一般 group 定理。

逐个按 native 坐标比较，而非 ID：W1 的370个 fragment 中363个在两宽窗中有完全相同的截断支撑；166个 group 中159个有相同截断支撑及成员分区；809个 rank 区域中752个匹配。保留所有兼容匹配，不做唯一归属。这些分母是结构记录对照，不是检测 recall。片段成员与 extent 不能仅靠 union 图判断；未匹配项保留在 APERTURE_COMPARISON.json，本轮未逐个给出语义裁决。

旧 q65/q80 levelset 在 W1→W3 共同9px内部改变1981/1987像素，旧被接受 q80 支撑改变2430像素。局部提案因此比整窗分位数稳定，但窄数字方向和严格原场条件也可能漏掉宽弱肩、弯曲及任意角度结构。稳定不等于完整。

![边界和内部支撑变化定位](../output/local_support_probe/figures/NATIVE_STABILITY.png)

## 7. 表示负担、验证与被撤回的初稿

| 条件 | 实际路径 | 候选局部组 | 间隔见证 |
|---|---:|---:|---:|
| original | 467 | 277 | 626 |
| shuffled | 136 | 29 | 32 |
| A | 45 | 18 | 36 |
| C | 374 | 203 | 482 |
| native W1 | 370 | 166 | 352 |
| native W2 | 730 | 351 | 648 |
| native W3 | 1187 | 577 | 1016 |

表只描述记录负担。原图组更多不能转成判别能力；W3仍有577个重叠假设，远未成为紧凑整体表示。未触发冻结5000 fragment/5000 pair停止预算，也没有通过叠加 score 消除歧义。

技术验证通过：源哈希与像素一致、core/config 未变、路径真实端点和相邻性、各尺度双侧取样独立复核、组精确成员并集、不填间隔、native interior支撑一致、恒值场及分离条带测试、original/shuffled灰度多重集相同。状态明确为 PASS_TECHNICAL_NOT_VEHICLE_OR_SEMANTIC_VALIDATION。

本轮最初一次 pilot 被撤回，原因是混用了 GT bilinear 图裁切和 native 窗口、用 chord 自身分位数预定低值比例、保留投影端点，以及无限近邻组合。其脚本作为 rejected_pilot.py 留审计记录并禁止执行，旧输出保留但不作为本文证据。随后冻结并执行本报告设计，没有用无效 pilot 结果宣称成功。

实验中共享 checkout 被另一会话切到其他分支。为不干扰旧未提交内容，最终代码/报告/日志放在指定分支隔离 worktree；不宣称整个共享 workspace 的非回归通过。仅提交本轮新增代码、报告、日志，不提交产物或改动上一轮文件，不推送。

## 8. 对本轮八个问题的结论

1. **旧 segment 主因**：整窗水平变化、connected support吞并、整块PCA筛掉真实局部，以及 chord未经过实际支撑检查；不是仅缺少一种 relation。
2. **三种语义有用**：将连续路径、断裂组合和拟合猜测分开；UNSUPPORTED 必须带判定范围，不能成为图像真值。
3. **更局部的 proposal 可行**：有限邻域 rank/双侧crest比 whole-aperture quantile 稳定。前者细碎，后者方向/宽度过窄。
4. **A059 主要组织只能部分表达**：G4/G73解释局部主弱片段及断口，尚未恢复完整主侧group；G96保留竞争解释。
5. **shuffled 假高级组织仍是风险**：G13说明真实支撑加低谷仍可偶然成立，不能按名字升级成整体结构。
6. **平台内部被自然抑制**：严格双侧局部支撑避免恒值内核；边缘/高值岛不在此保证内。
7. **同一局部支撑更稳定**：native共同内部成立；分组成员也需独立核验，不能从稳定像素偷换为正确对象。
8. **先继续 primitive**：不宜恢复完整 MorphologyObject grouping。只推荐两条小范围后续：其一，给真实片段补回二维横截面/弱肩宽度，允许弯曲与任意方向但不得补暗口；其二，在固定原图/shuffled/平台/native夹具上研究共享像素与竞争方向的替代分解，保留多解，不添加 score 或 selector。

本轮最大的瓶颈从“拟合线伪装原场支撑”推进到“原场支撑虽真实但过薄、方向竞争，而且局部几何不足以承担整体组织语义”。这比一张漂亮但无法回指图像的 graph 更可检查，仍不是已完成的车辆 morphology 对象。
