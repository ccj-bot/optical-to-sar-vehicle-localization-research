# R02 boundary multi-bracket annotation preparation

This task prepares three visually selected, temporally separated R02ZF SAR boundary brackets for manual endpoint annotation.

## Scope

- Preparation only: no propagation is run.
- Three brackets cover EARLY, MID/LATER, and LATE portions of the R02ZF SAR stream.
- Each bracket contributes only a START and END SAR keyframe.
- The user annotates only `SAR_BOUNDARY_NEAR` and `SAR_BOUNDARY_FAR`.
- Optical frames are retained only as timestamp-nearest metadata/media compatibility; no new optical annotation is requested.
- Automatic hints remain disabled by default. Previous propagation results are not displayed.
- Frozen comparator F150-F183 is excluded from new bracket selection.
- Tree work, PERSON work, R04, and `old_work` are excluded.

## Outputs

- `R02_BOUNDARY_MULTIBRACKET_ANNOTATION_BATCH_V1.csv`
- `MULTIBRACKET_SELECTION_REPORT.md`
- `figures/bracket_A_review_strip.png`
- `figures/bracket_B_review_strip.png`
- `figures/bracket_C_review_strip.png`
- a dedicated one-click launcher using the existing browser annotation tool

## Selected manual keyframes

| Bracket | Span | START | END | Inclusive frames |
|---|---|---:|---:|---:|
| A_EARLY | F047-F082 | F047 | F082 | 36 |
| B_MID_LATER | F239-F278 | F239 | F278 | 40 |
| C_LATE | F427-F472 | F427 | F472 | 46 |

The selection is based on real consecutive SAR images. Each bracket retains visible response-strength or clutter variation; bracket C deliberately includes a strong-to-weak-to-recovered interval.

## User operation

Double-click `START_R02_BOUNDARY_MULTIBRACKET_ANNOTATION.bat`.

For each of six SAR keyframes:

1. draw `SAR_BOUNDARY_NEAR` and press Enter;
2. draw `SAR_BOUNDARY_FAR` and press Enter;
3. the browser advances to the next keyframe automatically.

The isolated manual output directory is:

`D:\profile\research\workspace\output\r02_boundary_multibracket_preparation_20260902\user_annotations`

If a boundary is genuinely unclear, record it as unresolved/not visible instead of guessing. Do not use the old static-scene launcher for this six-keyframe batch.
