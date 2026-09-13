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
