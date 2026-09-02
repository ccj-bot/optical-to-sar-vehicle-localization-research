# R02 manual-seed temporal propagation

This task continues the user-confirmed R02 static-scene boundary semantics from two manual SAR anchor pairs.

## Fixed scope

- Manual identity authority: SAR F150 and F183 annotations in the append-only user JSONL.
- The current manual records are `DRAFT`, but the user explicitly confirmed that they define the intended image semantics. Running requires `--accept-confirmed-draft-seeds`.
- Propagation is limited to the bracketed stable interval SAR F150-F183.
- Near and far boundaries are propagated jointly, but remain separate identities.
- Each adjacent step uses the previous curve, local SAR ridge contrast, and frozen P0 common apparent vertical transport.
- Forward and backward propagation must agree before an intermediate frame is accepted.
- Ambiguity produces `PROPAGATION_AMBIGUOUS` and a review-list row; the algorithm never switches to another ridge automatically.
- There are no fixed 4.9/7.1/12.4 m search windows, PERSON outputs, final boxes, tree correspondence, or R04 access.
- The manual JSONL is read-only. All derived records are written under the task output directory.

## Run

```powershell
D:\MINICONDA\envs\py311\python.exe tasks\r02_manual_seed_temporal_propagation_20260902\run_manual_seed_temporal_propagation.py --accept-confirmed-draft-seeds
D:\MINICONDA\envs\py311\python.exe tasks\r02_manual_seed_temporal_propagation_20260902\validate_manual_seed_temporal_propagation.py
```

## Main outputs

- `propagated_static_scene_annotations.jsonl`
- `propagation_frame_diagnostics.csv`
- `REVIEW_REQUIRED_FRAME_LIST.csv`
- `MANUAL_SEED_TEMPORAL_PROPAGATION_SUMMARY.json`
- `figures/propagation_review_strip.png`
- `REPORT.md`
