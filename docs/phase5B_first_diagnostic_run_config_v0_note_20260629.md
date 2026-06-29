# Phase5B First Diagnostic Run Config v0 Note

Date: 2026-06-29

## 1. Purpose

This note documents `configs/phase5B_first_diagnostic_run_config_v0.json`.

The config freezes the first diagnostic proposal-generation contract for Phase5B. It is not a proposal output, not an experiment result, not a ranker, and not a Phase5C evaluation. It exists so that a later approved implementation can run a fixed, leakage-controlled diagnostic instead of choosing parameters after seeing evaluation metrics.

## 2. Why These Parameters Are Frozen

The v0 parameters are frozen before generation to prevent Phase5C post-hoc metrics from tuning Phase5B generation.

The crop, scale set, offset grid, peak count, component threshold family, component filters, and duplicate policy all affect proposal ceiling. If those values are adjusted after seeing A019/A021, oracle IoU, center error, condition labels, or panel review, the run would no longer be a valid diagnostic proposal audit.

The values are deliberately conservative:

- a shared `512 px` A005-centered crop keeps search local but leaves SAR evidence room;
- shell grid uses `3` scales and a `3x3` symmetric offset grid, giving at most `27` shell-grid proposals per target;
- energy/contrast uses at most `5` local peaks per target;
- connected components keep at most `5` components per target;
- total first-run output is capped at `37` proposals per target before route-level deduplication.

These values are not selected from GT, A019/A021, oracle labels, panel review, or Phase5C metrics.

## 3. Route Summary

`shell_grid` is enabled as the coverage baseline. It uses the A005 proxy shell, three size scales, and a symmetric 3x3 offset grid. It does not use SAR pixel values.

`energy_contrast_peak` is enabled as a SAR center-hypothesis route. It uses grayscale display PNG pixels inside the A005-centered crop, a robust crop-local background policy, fixed top-5 peak selection, and non-maximum suppression. It does not claim that a bright peak is the vehicle center.

`connected_component` is enabled as a visible-support extent diagnostic. It uses simple crop-local threshold families, relative component-size filters, and keeps boundary-touching components with uncertainty flags instead of discarding them.

## 4. Disabled Routes

Disabled in v0:

- `radial_range_profile`: fan/range convention and valid support mapping are not frozen;
- `ridge_long_axis`: orientation and long-axis convention are not ready for the first center/extent diagnostic;
- `learned_model`: training and calibration remain held;
- `factor_graph_over_generated_proposals`: Phase5D only after proposal ceiling audit;
- `active_c3_c4_integration`: Phase5B diagnostic outputs must remain separate from C3/C4;
- `hybrid_shell_sar_ranker`: hybrid scoring could become hidden ranker tuning before proposal ceiling audit.

## 5. Leakage Boundary

Allowed generation inputs remain limited to Phase4D target identity/frame/track fields, A005 proxy-shell fields, and SAR image path/dimension/pixel values for future generation.

Forbidden during generation:

- A019 `final_*`;
- A021 condition labels;
- GT boxes;
- oracle labels;
- IoU and center-error labels;
- panel review outcomes;
- post-hoc failure labels;
- Phase4D metric columns such as `selection_limited`, `pool_limited`, `oracle_usable`, `best_iou`, and `best_center_error`;
- A005 score and decision fields such as `score`, `lr_score`, `sar_factor_score`, `temporal_factor_score`, and `gm17_temporal_decision`.

A019/A021 may only be joined after a future proposal output is generated and frozen for Phase5C evaluation. Phase5C metrics cannot modify this same v0 configuration.

## 6. Implementation Status

This round only adds the frozen config and this note. It does not generate proposals.

The precheck showed that source availability is sufficient: 205 targets join to A005, grayscale PNGs are available for all targets, pseudocolor fallback is available for all targets, and selected image dimensions are consistent.

Recommendation: after explicit approval, it is reasonable to enter the minimal Phase5B proposal implementation for routes A/B/C only, using `phase5B_diag_v0_predeclared`. Route D and all disabled routes remain out of scope.

## 7. Boundary Statement

- No new proposal implementation code was added.
- No proposal was generated.
- No candidate was generated.
- No `proposal_candidates.csv` was generated.
- No A019/A021 join was performed.
- No GT/oracle metrics were computed.
- No C3/C4 ranking was changed.
- No A001/A005/A019/A021 source file was modified.
- No threshold tuning was performed.
- No model was trained.
- No calibration was performed.
- No push was performed.
- This config and note are not staged or committed unless explicitly approved later.
