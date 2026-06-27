# GM17 Phase4 Line A SAR 车辆物理结构发现

## 1. 当前定位

本文档是 Phase4 Line A 的 SAR 车辆物理结构共性发现总结。Line A 关注 GM_RM011、GM_RM017、GM_RM019 中已有 manual-GT 覆盖样本在 SAR 域呈现出的车辆尺度、长轴结构、OBB 方向约定、散射支撑、截断、遮挡和近场风险。

本文档不是 GT 语义最终标注，不是 442 行人工标注任务，不是模型设计实现，不是候选选择实验，也不是 GM17 复现或 patch 继续推进。它的目标是从 A019/A021 的描述性统计、已有 visual audit plan、worksheet、overlay review 和 visual audit panel 中提炼当前已经能站住的 SAR 车辆共性结构，同时把必要边界讲清楚。

当前不把样本钻入无限细的边界分类。边界分类只服务于物理结构共性分析：哪些样本可以支撑完整车辆尺度讨论，哪些样本只能作为截断、视场、遮挡、近场或不确定风险上下文。

## 1.1 核心发现摘要

- 当前三场景 manual-GT 样本中的 SAR 车辆 GT 呈现较稳定的长轴和 footprint 结构。
- GM_RM017 和 GM_RM019 的长轴比例较稳定，GM_RM011 存在 `final_w/final_h` 或 OBB convention 混合风险。
- `final_w/final_h` 是 OBB 存储轴比值，不自动等于物理车长/车宽。
- `final_heading_deg` 是 OBB 轴角度记录，不自动等于车辆车头方向。
- GT 框主要关注车体主体散射支撑，不应为了包住所有 SAR 能量而自动扩大。
- severe truncation、near-field、optical unresolved 等现象应作为 future route 风险上下文，而不是当前完整车辆主线输入。
- Line A 结论只能支持物理解释边界，不能变成 Line B scoring 参数。

## 2. 证据来源

本文档使用以下已有 Line A 材料作为审计上下文：

- `docs/gm17_phase4_sar_domain_physical_prior_audit_summary.md`
- `docs/gm17_phase4_lineA_visual_audit_plan.md`
- `docs/gm17_phase4_lineA_visual_audit_worksheet.md`
- `docs/gm17_phase4_lineA_visual_audit_overlay_review.md`
- `docs/gm17_phase4_lineA_visual_audit_panel_review.md`

A019 `final_gt_working.csv` 和 A021 `visibility_condition_working.csv` 只作为 GT 域描述性审计证据。A019 中的 `final_*` 字段是人工 GT 记录，不是推理输入；A021 中的可见性、截断和遮挡字段是审计分组和未来路线证据，不是当前评分因子。

A001 和 A005 仍然只属于 GM_RM017-only 的 Line B candidate-level pilot，不参与本文档。本文档不使用 candidate bank，不使用 GM17 selected outputs，不使用 IoU、center error、oracle rank、candidate rank 或模型性能字段。

## 3. SAR 车辆尺度共性

A019 的 `final_w`、`final_h`、`final_rot_area_px` 和 `final_ax_area_px` 支持一个基本判断：在当前三场景 manual-GT 样本中，SAR 车辆 GT 的旋转框尺度呈现有限分布范围和一定集中性，尤其 GM_RM017 和 GM_RM019 的短轴分布较稳定，车辆 footprint 没有表现为完全无约束的随机框。

已有 summary 中，整体 `final_w` 中位数约为 145.782，`final_h` 中位数约为 76.384；`final_rot_area_px` 中位数约为 11993.744，`final_ax_area_px` 中位数约为 13723.873。这些数值说明当前样本内的人工 GT 在旋转框尺度上具有可讨论的集中性，可以用于物理合理性讨论，但不能写成跨数据集普适规律。

场景差异很关键。GM_RM017 的 `final_w/final_h` 中位数约为 2.170，GM_RM019 约为 2.069，二者呈现较稳定的约 2:1 长轴结构。GM_RM011 则不能按 `final_w/final_h` 的字面比值直接混合解释：它的中位比值约为 0.491，但上四分位又接近 1.986，明显显示宽高存储、heading/OBB 约定、可见范围或场景边界因素混合在一起。

因此，这些统计可以支持“车辆尺度是否物理合理”的讨论，但不能直接形成 scoring threshold、tuned constant 或候选筛选阈值。尤其不能把 GM_RM011 的 `final_w/final_h` 字面分布和 GM_RM017/GM_RM019 的分布直接拼成一个统一物理长宽比规则。

## 4. 长轴结构共性

车辆长轴结构是当前 Line A 中最稳定的物理线索之一。无论长轴被存进 `final_w` 还是 `final_h`，visual audit panel 显示多数车辆 GT 仍围绕一个主车体长轴展开，而不是任意形状的散射包围框。

但 `final_w` 和 `final_h` 是 OBB 存储轴，不自动等于物理车长和车宽。GM_RM011 的低 `final_w/final_h` 样本不应被立即解释为车辆形状异常；更合理的读法是先判断视觉长轴当前存储在 `final_w` 还是 `final_h`。

在讨论层，可以使用：

- `long_axis = max(final_w, final_h)`
- `short_axis = min(final_w, final_h)`

这个口径有助于跨场景解释车辆尺度和长轴结构，但它只是跨场景审计/讨论口径。它不重写 A019 字段，不生成新 GT，不进入 inference、candidate scoring、threshold 或 calibration。若后续确实需要记录人工观察，可建立 review-only 字段，例如 `review_long_axis_field`，用于说明长轴存储字段，不作为模型字段，也不作为 candidate-level 评分证据。

## 5. heading/OBB 方向共性与风险

`final_heading_deg` 当前更适合理解为 OBB 轴角度记录，而不是车辆车头方向。已有 summary 显示 heading 存在负值、接近 359 度的 wraparound、以及 0 度和 180 度等价风险。visual audit panel 中也能看到同一类长轴结构可能以接近 0 度、接近 180 度或 `final_h` 轴承载长轴的方式出现。

因此，heading 当前可以支持 OBB convention audit 和未来方向约定讨论，但不能直接作为当前 direction prior 或 scoring factor。尤其不能把 `final_heading_deg` 直接解释为车头朝向，也不能把角度差作为当前候选打分项。

如果后续讨论 heading，应先明确三个层次：OBB 存储轴角、无符号长轴角、车辆有向车头角。Line A 目前只能支持前两个层次的审计讨论，不能证明第三个层次。

## 6. SAR 散射支撑与 GT 框关系

visual audit 暴露的一个稳定共性是：GT 框通常关注主要车体散射支撑，而不是包住所有 SAR 能量。SAR 图像中经常出现离主体有一定距离的亮斑、拖尾、旁瓣或背景响应，这些不应自动被解释为车体边界。

当前建议使用以下解释边界：

- main body scatter：与车体主体连续、能支撑车辆中心和长轴判断的主要散射。
- spillover scatter：离主体较近或方向相关的逸散散射，可记录为风险或不确定支持。
- background clutter：与主体不连续、可能来自环境或其他目标的背景杂波。
- mask edge artifact：图像有效区边界、纯黑/纯白背景或边界连通区域导致的截断和显示伪影。

SAR 逸散不应自动要求扩大 GT 框，也不应直接修改 candidate bank、生成候选规则或触发候选评分项。它可以作为后续 SAR structure、uncertainty 或 visibility 路线的研究素材，但当前只保留为 Line A 的物理解释 caveat。

## 7. 截断、遮挡、近场和视场不一致风险

truncation 和 occlusion 在 Line A 中非常重要，尤其 GM_RM011 和 GM_RM019。已有 summary 显示，A021 中包含 truncation 的样本数量很高，严重 truncation 也较多；GM_RM017 则包含主要的非截断子集。

但 A021 的 truncation/occlusion 是原始描述标签，视觉上可能混合了多种物理和标注来源：

- optical truncation
- SAR mask truncation
- near-field boundary
- optical out-of-view
- cover/cloth occlusion
- 多车干扰
- scatter spillover

这些风险应作为 future visibility、missing-extent 和 near-field route 的证据，而不是当前 complete-vehicle `geometry_factor` 的直接输入。严重截断样本尤其不能被当作完整车辆尺度的强证据；它们更适合作为“完整范围可能不确定”的审计上下文。

## 8. GT 框语义边界的适度定义

当前不需要展开过细 taxonomy。为了服务物理结构共性分析，以下解释边界已经足够：

- `likely_complete_vehicle_extent`：GT 框大体覆盖主要车体区域，可用于讨论完整车辆尺度和长轴结构。
- `likely_sar_visible_or_truncated_extent`：GT 框更像覆盖 SAR 中可见主体或被截断后的主体范围，完整车体范围需要 caveat。
- `sar_only_or_optical_unresolved_extent`：SAR 中有人工 GT 或时序补充线索，但光学对应关系不稳定或未解析，只能作为审计风险上下文。
- `near_field_or_mask_boundary_extent`：GT 框触及 SAR 有效区、图像边界或近场边界，完整 extent 和中心解释需要谨慎。
- `uncertain_extent`：视觉证据不足以判断完整车体、可见范围或边界影响。

这些是 audit interpretation categories，不是 442 行最终标签，不要求人工逐行标注全部样本，也不直接进入模型字段。后续如需 triage，应先由 Codex 给出 suggested tags，再做小规模人工抽样确认。

## 9. 对 geometry_factor 的启示

Line A 支持 `geometry_factor` 在研究讨论中关注车辆尺度、长轴结构、OBB footprint 和候选几何合理性。它说明 SAR GT 不是任意框，车辆主轴和 footprint 有可解释的物理结构。

但 `geometry_factor` 必须避免以下错误用法：

- 直接用 GT 统计生成阈值；
- 把 `final_w/final_h` 字面比值当作物理车长宽；
- 把 `final_heading_deg` 当作车头方向；
- 把 severe truncation 样本当完整车辆尺度强证据；
- 把 SAR 逸散当作框扩展依据；
- 把 A019/A021 的 eval-only 字段带入 inference 或 candidate scoring。

Line A 支持的是物理解释边界，不是 Line B scoring 参数。它可以帮助后续 manifest 明确哪些字段只能作为评估、审计、分组和失败分析上下文，不能帮助当前模型直接学习或调参。

## 10. 对后续 Line B manifest 的启示

本文档不激活 Line B。后续 Line B 的 geometry + optical_temporal manifest 可以吸收本文档中的字段安全边界：

- GT fields remain eval-only/audit-only；
- long_axis 解释只作为 discussion；
- severe truncation、near-field 和 optical unresolved 作为 post-inference caveat；
- A001/A005 仍仅属于 GM_RM017-only pilot；
- Line B 不从 GM_RM011/GM_RM019 生成 candidate bank；
- Line B 不把 `final_*`、A021 condition 字段或人工 review category 作为 inference 输入。

本文档不授权 candidate scoring、candidate bank 修改、GM_RM011/GM_RM019 candidate generation 或模型实验。它只提供一个更清楚的 SAR 物理结构背景，使后续 Line B manifest 能更准确地区分 inference-safe、eval-only、audit-only 和 future-route 字段。

## 11. 下一步建议

当前建议暂停大规模人工逐行审阅，不再要求人工完整审 442 个 GT 样本，也不让 Codex 给 442 行下最终语义标签。

下一步更稳妥的推进方式是：

- 保留少量代表性或高风险 VA 样本作为说明性 case；
- 把本文档作为 Line A 物理结构共性总结；
- 之后回到 Line B，先写 `docs/gm17_phase4_geometry_temporal_manifest_allowlist_denylist.md`，并将其限定为非执行版 manifest/allowlist/denylist，不跑实验、不调参、不 candidate selection；
- 继续保持 A001/A005 的 GM_RM017-only 边界；
- 如果未来确实需要 442 行 triage，采用 Codex suggested tags 加小规模人工抽样确认，不做全量人工标注。

最需要后续讨论的问题不是“把所有边界类别分清楚”，而是：哪些 SAR 车辆结构共性足够稳定，可以成为未来层级因子图中的可解释变量；哪些现象必须留在 visibility、missing-extent 或 near-field future route 中。
