# R02 manual static-scene anchor preparation

This task provides a local, user-driven annotation tool for sparse R02ZF static scene geometry.

The V1 batch contains 18 timestamp-nearest pairs. It includes the exact OPT F120 / SAR F200 core case and only two pairs from the prior F330-F335 stable-segment context.

## Scope

- This is scene-level static geometry annotation, not PERSON GT.
- The user is the identity authority for optical/SAR near and far boundaries and any tree correspondence.
- Automatic 4.9/7.1/12.4 m candidates are optional visual hints only, disabled by default and never preselected.
- No seed propagation, model fitting, PERSON localization, fixed-range tree model, or R04 access is performed in this task.
- Timestamp-nearest pairing is used; equal frame indices are never assumed to be synchronized.
- `NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED` remains explicit.

## Entry point

Double-click `START_R02_STATIC_ANNOTATION.bat`. It starts a localhost-only Python server and opens the simplified browser UI.

The batch file uses `D:\MINICONDA\envs\py311\python.exe` and starts `r02_static_scene_browser_server.py` without requiring command-line input. The earlier OpenCV interface remains available through `START_R02_STATIC_ANNOTATION_LEGACY.bat`.

## Simplified V2 interaction

- Default workflow contains only four guided boundary steps.
- The active modality receives the larger panel automatically.
- Mouse-wheel zoom and space-drag panning preserve original-image coordinates.
- Completed polyline vertices can be dragged directly for precise correction.
- Completing a boundary advances automatically; completing SAR far advances to the next pair.
- Tree tools are collapsed and optional.
- Existing append-only JSONL events are loaded without migration or overwrite.

## Inputs and outputs

- Batch: `D:\profile\research\workspace\output\r02_manual_static_scene_anchor_preparation_20260902\R02_STATIC_SCENE_ANNOTATION_BATCH_V1.csv`
- User annotation directory: `D:\profile\research\workspace\output\r02_manual_static_scene_anchor_preparation_20260902\user_annotations`
- Append-only manual event log: `manual_static_scene_annotations.jsonl`
- Current annotation summary: `manual_static_scene_annotation_summary.csv`
- Per-pair progress: `manual_static_scene_batch_progress.csv`
- Live coverage summary: `ANNOTATION_COVERAGE_REPORT.json`
- Session state: `annotation_session_state.json`

User annotation files are intentionally not included in the research commit. Propagation, when separately authorized after V1 completion, must write to `propagated_static_scene_annotations.jsonl` and must never overwrite the manual event log.
