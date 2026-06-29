# Phase5C-v0 Model Diagnostic Audit Summary

Date: 20260629_110133

## Purpose

Phase5C-v0 is a post-hoc model diagnostic audit. It evaluates frozen Phase5B-v0 proposals after generation and does not modify Phase5B-v0 config, regenerate proposals, tune thresholds, train, calibrate, or integrate anything into C3/C4.

## Inputs

- Phase5B-v0 proposals: `output/phase5B_first_diagnostic_run_v0_20260629_102746/proposal_candidates.csv`
- A001 / Phase4D baseline: `output/gm17_phase4D_candidate_pool_ceiling_audit_20260629_001655/candidate_pool_ceiling_per_target.csv`
- A019 final boxes: `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv`
- A021 condition labels: `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv`
- A001 candidate bank for novelty: `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv`

All A019/A021/A001 oracle fields are post-hoc evaluation inputs only. They were not used for Phase5B generation.

## Overall Result

- Target count: 205
- Proposal count: 7490
- Phase5B ABC mean / median center error: 17.395281 / 13.827046
- Phase5B ABC mean / median IoU: 0.682362 / 0.721434
- A001 mean / median center error: 7.540596 / 5.636615
- A001 mean / median IoU: 0.78458 / 0.794266
- Phase5B better count: 50
- A001 better count: 167

## Route Diagnosis

- `A_only`: mean center `17.866096`, median center `13.891861`, mean IoU `0.681113`, median IoU `0.721434`
- `B_only`: mean center `75.97969`, median center `65.032626`, mean IoU `0.227228`, median IoU `0.255458`
- `C_only`: mean center `59.738981`, median center `38.604072`, mean IoU `0.277747`, median IoU `0.301866`
- `A_plus_B`: mean center `17.561791`, median center `13.891861`, mean IoU `0.682145`, median IoU `0.721434`
- `A_plus_C`: mean center `17.649918`, median center `13.827046`, mean IoU `0.68133`, median IoU `0.721434`
- `B_plus_C`: mean center `51.620166`, median center `35.619647`, mean IoU `0.30466`, median IoU `0.341841`
- `A_plus_B_plus_C`: mean center `17.395281`, median center `13.827046`, mean IoU `0.682362`, median IoU `0.721434`

Route contribution labels:

- `prior_dominant`: 192
- `energy_center_helpful`: 7
- `mixed_or_unclear`: 5
- `component_extent_helpful`: 1

## Problem Attribution

- `A001_still_stronger`: 130
- `prior_dominant`: 67
- `phase5B_adds_new_hypothesis`: 4
- `component_fragmentation_or_clutter`: 4

Top recommended next actions:

- `open_phase5B_v1`: 130
- `inspect_sample_manually`: 67
- `prepare_phase5D`: 4
- `strengthen_sar_observation`: 4

## Interesting Sample Buckets

- `A001_bad_Phase5B_good`: 10
- `Phase5B_bad_A001_good`: 10
- `outside_A001_high_quality_proposals`: 10
- `RouteB_center_rescue`: 7
- `component_clutter_or_fragmentation`: 4
- `RouteC_extent_rescue`: 1

See `output/phase5C_v0_model_diagnostic_audit_20260629_110133/phase5C_v0_interesting_samples.csv`.

## Interpretation

- Prior shell usefulness is diagnosed by `A_only` and its gap to `A_plus_B_plus_C`.
- SAR center evidence is diagnosed by `B_center_gain_over_A`.
- Visible support is diagnosed by `C_iou_gain_over_A`.
- Novel hypotheses beyond A001 are diagnosed by the optional A001-neighborhood file when available.
- Failure attribution separates shell limitation, weak SAR center evidence, visible-support value, component fragmentation/clutter, Phase5B novelty, and A001 superiority.

## Recommendation

OPEN Phase5B-v1

## Boundary

- Post-hoc only.
- Phase5B v0 config not changed.
- Proposals not regenerated.
- No C3/C4 integration.
- No threshold tuning.
- No training.
- No calibration.
- No push.
