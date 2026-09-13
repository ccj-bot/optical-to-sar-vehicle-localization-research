# TPGT Unified Target Review + SAR Observation

统一入口实现：完整光学时序人工复核 → 人工目标/区间冻结 → PRE_OPEN_BOOK SAR display-domain Observation → Open-book interpretation。

边界：B1.2 只读 proposal；不重跑 detector/tracker，不做 mapping、mechanism、final SAR box 或自动跨模态 assignment。活动工作区为 `D:/profile/research/workspace`，解释器为 `D:/MINICONDA/envs/py311/python.exe`。

```powershell
D:\MINICONDA\envs\py311\python.exe tasks\tpgt_unified_target_review_observation\build_unified_workbench.py
D:\MINICONDA\envs\py311\python.exe tasks\tpgt_unified_target_review_observation\serve_unified_workbench.py --port 8780
```

打开 `http://127.0.0.1:8780/index.html`。
