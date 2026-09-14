# TPGT overlapping proposal selection and frame removal

## Pre-change

- Date: 2026-09-14
- Branch: `feature/tpgt-unified-target-review-observation`
- Workspace: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Scope: optical annotation UI only; no detector inference, SAR page, mapping, tracker, or identity automation changes.
- Problem: overlapping YOLO proposals are resolved implicitly by box area, and the user cannot remove a wrong bbox/frame association from an existing Human Target.

## Post-change

- Overlapping visible proposals now open an explicit chooser with model, class, confidence, and box size. Hovering a choice previews its bbox in yellow.
- Existing targets only show proposals from the same target domain (PERSON versus vehicle family).
- Added `CLEAR_FRAME_BBOX`, preserving identity while removing the bbox.
- Added `REMOVE_FRAME_FROM_TARGET`, deleting one observation and splitting/trimming identity segments.
- Added `REMOVE_FRAME_RANGE_FROM_TARGET`, allowing an incorrect tail such as PERSON_001 frames 242–367 to be removed in one action.
- Added whole-target deletion for unfrozen targets; deleted snapshots remain in `deleted_targets`. Frozen targets cannot be directly deleted.
- All corrections are represented in exported `edit_history`.
- Browser QA covers overlap choice, bbox clearing, single-frame removal, range removal, and previous annotation workflow checks.
