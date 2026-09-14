# CA-P0 条件 SAR 响应归属：预研究审阅

日期：2026-09-14。审阅范围仅为只读检查，未修改旧 morphology 结论。

## 可用资产

- local support probe：保留 I0 实际像素 fragment、重叠 group、gap witness；明确不是物理散射中心。
- GM GT morphology：PV002 在 GM17 有 frame 330、339、344、345、353、363、378 的身份标注和案例图；A059 对应 `GM_RM017_f0344_g151`，可作为已有人工审阅的 A0 anchor。
- GM17 原生灰度帧：`000000.png`…`000765.png` 可读取，仍是显示域灰度，不是复数 SAR/RCS。
- TPGT PV002 观察记录：已有 SAR frame bracket 154–173，但 `sync_semantics=Optical/SAR exact synchronization unverified`，且没有 spatial marks/morphology；不能作为精确 optical↔SAR 对齐。
- EVOLUTION_VIEW_MANIFEST：保存 GT chart 样本的历史身份/帧号，但自身声明“GT chart convention only; no registration, new tracking or physical scatterer association”。

## 必须冻结的语义边界

本轮用 `W_{j→j+1}` 表示场景共享的图像域传输估计；不称 common motion、vehicle motion 或平台位姿。车辆身份状态 `Z_j^k` 与 SAR 响应状态 `R_j^k` 分开；无响应只能是 `UNOBSERVED/WEAK/AMBIGUOUS`。

frame 索引保持 `O_i at τ_i^opt` 与 `S_j at τ_j^sar` 分离。当前未找到可验证的精确时间映射，因此 pilot 只能冻结 coarse temporal bracket，并标记 `TEMPORAL_MAPPING_UNCERTAIN`；不得按最好看的 SAR 帧反向对齐。

corridor 若由 A059 anchor 初始化，来源只能记为 `ANCHOR_ASSISTED`，不能冒充 optical-only。anchor provenance 分为 A0 外部人工确认、A1 传播后高一致性 hypothesis、A2 tentative；传播不能升级 provenance。

forward/backward 共享同一 A0、primitive 和 transition rule 时，只能称 bidirectional reachability consistency。GT 仅 posthoc 使用；runtime 不读 GT、人工 reference 或结果生成的 corridor。

## 因果与泄漏审阅

1. local fragment 是同源显示域结构，不能跨帧命名为同一物理 scattering center。
2. `W` 不能由当前 candidate 单独估计后再用来证明 candidate；本 pilot 只使用固定局部平移近似并记录其不确定性，不能宣称 registration 已解决。
3. 不建立负样本、AUC、score、winner 或 top-k。hypothesis graph 保留多解、split/merge/temporary disappearance 与 `⊥`。
4. 每个 runtime 记录 provenance、冻结 corridor、传输估计、候选和停止状态；posthoc 单独运行并不得回灌参数。

## 继续条件与最小修复

缺少可靠 optical↔SAR 精确映射和独立 registration consensus，因此不能声称完整 cross-modal localization。它们并非本轮不可替代：可把实验缩成 anchor-assisted、coarse-bracket 的条件归属 pilot，明确 `TEMPORAL_MAPPING_UNCERTAIN`、`REGISTRATION_NOT_INDEPENDENT`，只研究集合值 hypothesis 是否有限传播以及 optical identity/time 条件是否切断部分分支。

下一步在独立分支执行约 15–25 个 GM17 SAR 帧的最小 pilot；窗口、局部 aperture、平移容差和 gap budget 在运行前冻结。若原始帧或冻结条件不足，结构化停止而不扩大走廊。
