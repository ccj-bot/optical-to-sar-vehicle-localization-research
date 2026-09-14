# TPGT Unified Target Review + SAR Observation

当前光学入口实现：从任意帧建立人工目标 → 选择 detector proposal 或手动画框 → 确认连续同一目标帧段 → 逐帧记录可见性及可共存的边缘截断/近场截断/遮挡 → 选取完整可见的正式标注帧 → 冻结人工目标 revision。

`identity_segments` 记录人工确认的同一目标连续性；`visible_segments` 由逐帧可见状态生成；`formal_annotations[]` 保存完整可见帧的正式 bbox 标注，`primary_annotation_frame_index` 指向当前主标注帧。批量确认 identity 区间不会给缺框帧插值或伪造 bbox。

当前帧全部 proposal 现在常驻显示在右侧列表，不需要先点中图像区域；鼠标悬停列表项会高亮对应 bbox，直接点击即可选择。重叠 proposal 点击后也通过候选列表人工选择，不再按面积静默决定。编辑操作分为“清除本帧框”（保留 identity）、“从目标移除本帧”、“从目标移除指定帧段”（同步截断或拆分 identity segment）和“删除整个未冻结目标”；纠错操作写入 `edit_history`，整目标删除保留在 `deleted_targets` 中。

边界：YOLO/B1.2/历史 SAR 关联只可作为 proposal/source provenance；不重跑 detector/tracker，不做 ReID、physical identity 自动生成、mapping、mechanism、final SAR box 或自动跨模态 assignment。活动工作区为 `D:/profile/research/workspace`，解释器为 `D:/MINICONDA/envs/py311/python.exe`。

```powershell
D:\MINICONDA\envs\py311\python.exe tasks\tpgt_unified_target_review_observation\build_unified_workbench.py
D:\MINICONDA\envs\py311\python.exe tasks\tpgt_unified_target_review_observation\serve_unified_workbench.py --port 8780
```

打开 `http://127.0.0.1:8780/index.html`。
