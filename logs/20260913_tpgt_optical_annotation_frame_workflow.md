# TPGT optical annotation-frame workflow

## Pre-change record

- Date: 2026-09-13
- Active workspace: `D:\profile\research\workspace`
- Branch: `feature/tpgt-unified-target-review-observation`
- Default interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Scope: optical target review UI/data contract only; no SAR page enhancement or SAR localization change.
- Runtime path audit: task assets and outputs are under `workspace\tasks` and `workspace\output`; no `old_work` runtime dependency is authorized.
- Requested workflow: create a human target at an arbitrary frame; select a detector box or draw a box; independently mark edge truncation, near-field truncation, and occlusion; confirm a continuous same-target frame span; then select a complete optical frame as the formal annotation frame.

## Post-change record

- Implemented three separate layers: target `identity_segments`, per-frame observations with coexisting condition flags, and `formal_annotations` with `primary_annotation_frame_index`.
- Added Chinese UI controls for `IMAGE_EDGE_TRUNCATED`, `NEAR_FIELD_TRUNCATED`, and `OCCLUDED`; these flags may coexist.
- Establishing or re-anchoring a target no longer auto-labels the frame as complete.
- A formal annotation frame now requires a confirmed bbox, `COMPLETE_VISIBLE`, and no truncation/occlusion flags.
- Bulk confirmation of a same-target segment preserves `bbox=null` on frames without an accepted/manual box.
- Added JSON import/export and append-only optical freeze revisions.
- Browser QA: 10/10 checks PASS in `output/tpgt/unified_target_review_observation/audit/unified_workbench_qa.json`.
- Machine-readable QA target set: `output/tpgt/unified_target_review_observation/audit/qa_human_target_set_fixture.json`.
- UI validation screenshot: `output/tpgt/unified_target_review_observation/audit/optical_annotation_frame_workflow.png` with `annotation_ui_media_manifest.json`.
- Reproduction:

```powershell
D:\MINICONDA\envs\py311\python.exe tasks\tpgt_unified_target_review_observation\build_unified_workbench.py
D:\MINICONDA\envs\py311\python.exe tasks\tpgt_unified_target_review_observation\serve_unified_workbench.py --port 8780
D:\MINICONDA\envs\py311\python.exe tasks\tpgt_unified_target_review_observation\check_unified_workbench.py
```
