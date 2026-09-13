# GM_RM017 frame 231 PERSON overlay diagnosis

- Date: 2026-09-13
- Scope: read-only diagnosis; no detector or UI implementation changed.
- Workspace: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- `old_work` was not used.

## Finding

The absent PERSON boxes are a workbench data-wiring issue, not a confirmed detector miss.

The two detector tables currently wired into `scene.detections.yolo11/yolo26` were generated with class IDs `[2,5,7]` (`car`, `bus`, `truck`) only. Both therefore contain zero rows at frame 231 and cannot display PERSON boxes.

The imported read-only PERSON rescout file `output/tpgt/unified_target_review_observation/proposals/GM17_PERSON_DETECTIONS.csv` does contain two frame-231 detections:

- confidence `0.850202`, bbox `(296.551, 290.051, 353.443, 458.138)`;
- confidence `0.872544`, bbox `(455.888, 295.905, 499.729, 421.520)`.

Their source is `YOLO11l / full_368_frame_rescout`. The builder currently stores these 91 PERSON rows under `data.proposals.person_detections`, while the optical overlay reads only `scene.detections`. Consequently, the UI PERSON checkbox has no GM PERSON stream to render.

## Boundary

These boxes remain detector proposals only. Wiring them into the overlay must not promote provisional PERSON tracks or detections to Human Target identity.
