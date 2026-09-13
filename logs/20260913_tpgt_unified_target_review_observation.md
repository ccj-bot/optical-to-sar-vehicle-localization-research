# TPGT Unified Target Review + SAR Observation

Started 2026-09-13 on `feature/tpgt-unified-target-review-observation`.

- Active workspace: `D:/profile/research/workspace`
- Interpreter: `D:/MINICONDA/envs/py311/python.exe`
- Task code: `tasks/tpgt_unified_target_review_observation/`
- Output: `output/tpgt/unified_target_review_observation/`
- B1.2 source: read-only Git branch `feature/tpgt-gm-complete-interval-b12`, commit `946e4750b998c3667d09bcf43fa05cb7b08d1e71`
- Raw GM_RM017 optical/SAR frames are read-only and served in place; no frame dump or video copy.
- No `old_work` dependency. No detector/tracker rerun, mapping fit, mechanism, selector, or automatic annotation.
- Machine proposals remain proposal/reference layers. Human intervals start empty and require explicit save/freeze before SAR scientific observation is enabled.

Implementation and QA results will be appended after execution.

2026-09-13 Optical Review v0.3：完成 scene_review 多目标模型、target-level frame observations、VISIBLE_UNBOXED/MANUAL_OPTICAL_BBOX、scene_manifest 驱动入口，并接入 GM_RM011/017/019、R35ZF、R01ZF。构建使用 D:\MINICONDA\envs\py311\python.exe；QA 输出为 output/tpgt/unified_target_review_observation/audit/unified_workbench_qa.json；提交 98eb727。

2026-09-13 new65 detector cache 接入：R35ZF 4212 CAR + 25 PERSON proposal；R01ZF 77 CAR + 205 PERSON proposal。仅导入检测几何与类别/置信度，不导入历史 identity。
