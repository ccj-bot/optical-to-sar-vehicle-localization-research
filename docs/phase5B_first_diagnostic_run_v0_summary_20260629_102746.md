# Phase5B First Diagnostic Run v0 Summary

Date: 20260629_102746

## Purpose

This run generated diagnostic proposal hypotheses from the frozen Phase5B v0 config. It is not Phase5C evaluation, not C3/C4 integration, and not a final SAR localization model.

## Config

- Config id: `phase5B_diag_v0_predeclared`
- Experiment id: `phase5B_first_diagnostic_run_v0`
- Output directory: `output/phase5B_first_diagnostic_run_v0_20260629_102746`

## Input Sources

- Config: `configs/phase5B_first_diagnostic_run_config_v0.json`
- Target identity/frame/track source: `output/gm17_phase4D_candidate_pool_ceiling_audit_20260629_001655/candidate_pool_ceiling_per_target.csv`
- A005 proxy source: `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv`
- SAR image source: grayscale display PNG, with pseudocolor fallback if needed.

Only pre-inference allowed fields were used. A019/A021, GT boxes, oracle labels, IoU, center error, panel review, and post-hoc failure labels were not joined or read for generation.

## Route Counts

- `shell_grid`: 5535 proposals; mean 27.0 per target
- `energy_contrast_peak`: 1025 proposals; mean 5.0 per target
- `connected_component`: 930 proposals; mean 4.536585 per target

Total proposals after exact-geometry deduplication: 7490

## Warnings

- 205 selected SAR display PNGs converted for diagnostic pixel operations: gm17_sarframes_gray_display_png:RGB->L

## Boundary

- No Phase5C metrics were computed.
- No A019/A021 join was performed.
- No GT/oracle labels were used.
- No IoU or center error was computed.
- No C3/C4 comparison was made.
- No A001/A005/A019/A021 source file was modified.
- No threshold tuning, training, or calibration was performed.

## Next Step

Phase5C post-hoc ceiling audit can be designed only after this proposal output is frozen and reviewed. Phase5C must stay separate from Phase5B generation and cannot modify this v0 config for the same run.
