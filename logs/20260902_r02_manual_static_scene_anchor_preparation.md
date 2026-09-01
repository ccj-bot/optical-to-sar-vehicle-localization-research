# R02 manual static-scene anchor preparation log

## Pre-run

- Started 2026-09-02 Asia/Shanghai.
- Active repository: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Verified `HEAD == origin/main == 2543847289e973390cf7265acf071b508a7eba02`; ahead/behind `0/0`.
- Existing dirty baseline is preserved without cleanup or broad staging.
- Raw R02ZF inputs contain 298 optical frames and 495 SAR pseudocolor frames.
- `old_work`, archive runtime paths, R04, PERSON GT, PERSON localization, seed propagation, boundary fitting, and automatic tree correspondence are excluded.
- This task stops after producing and validating a manual annotation tool. Real user annotations remain uncommitted.

## Post-run

- Created task folder: `tasks/r02_manual_static_scene_anchor_preparation_20260902`.
- Created an 18-pair timestamp-nearest batch spanning optical F0-F297.
- Dense core coverage includes optical F110, F115, F120, F125, F130, and F135.
- The exact user core case is included as OPT F120 `t=006667ms` / SAR F200 `t=006667ms`, nominal residual `0 ms`.
- Prior stable-segment context is limited to two pairs only: OPT F198 / SAR F330 and OPT F201 / SAR F335. These are batch coverage choices, not identity authority.
- The optical end frame F297 pairs to its true nearest SAR F494 with nominal residual `-33 ms`; all 18 pairs were independently rechecked against raw filename timestamps.
- Implemented a fixed-size OpenCV side-by-side annotator with original-image coordinate storage.
- Boundary labels use polylines; tree labels use points. `TREE_UNKNOWN`, `UNCERTAIN`, `NOT_VISIBLE`, and `SKIPPED` remain legal states.
- Every click appends and fsyncs a JSONL event immediately. Deletion appends a delete event rather than erasing manual history.
- Current-summary CSV, pair-progress CSV, session state, and `ANNOTATION_COVERAGE_REPORT.json` are regenerated after every annotation event.
- Automatic optical mapping and SAR 4.9/7.1/12.4 displays are explicitly labeled `AUTOMATIC_HINT`, disabled by default, and never preselected or saved as identity authority.
- One-click launcher: `tasks/r02_manual_static_scene_anchor_preparation_20260902/START_R02_STATIC_ANNOTATION.bat`.
- One-page instructions: `tasks/r02_manual_static_scene_anchor_preparation_20260902/HOW_TO_ANNOTATE_R02_STATIC_SCENE.md`.
- User annotations will be created under `output/r02_manual_static_scene_anchor_preparation_20260902/user_annotations` only when the user launches the tool. No real user annotation was created in this run.
- Validation passed `18/18`, including batch timing, required classes, confidence states, append-only autosave/reload, `TREE_UNKNOWN`, default-off hints, empty template, and absence of propagation/PERSON outputs.
- OpenCV GUI backend is `WIN32UI`; a real window open/render/close smoke test passed.
- Preview: `output/r02_manual_static_scene_anchor_preparation_20260902/ANNOTATOR_PREVIEW.png`.
- No seed propagation, boundary fitting, tree correspondence experiment, PERSON experiment, or R04 access was performed.
