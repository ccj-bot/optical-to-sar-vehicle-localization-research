# GM17 Phase4C Combined Structure+Temporal Fixed Pilot Preregistered Spec

## 1. Current Position

This document belongs to Phase4C. It is a combined structure+temporal pre-registered fixed pilot.

It is not v3 table tuning. It is not a final model. It does not allow changing rules after evaluation results are seen.

The pilot tests whether two independent signals are complementary: optical temporal consistency can protect center error, while SAR structure can promote candidates with stronger image support.

## 2. Candidate Pool

The candidate pool is the full A001 GM_RM017 candidate bank.

The pilot must:

- Use all A001 candidates.
- Not filter by structure-selected rank1.
- Not filter by `best_proxy` or `best_center` identity.
- Not generate new candidates.
- Not move candidate boxes.
- Not modify the candidate bank.

The combined pilot ranks existing candidates only.

## 3. Active Temporal Signal

The temporal signal is recomputed only from A001 safe candidate fields and A005 safe prediction fields:

- A001: `r`, `cross`, `az`.
- A005: `pred_r`, `pred_cross`, `pred_az`.

The pilot must not use legacy `delta_*_from_pred`, `temporal_factor_score`, `score`, `lr_score`, or `sar_factor_score`.

For each candidate:

- `abs_dr = abs(r - pred_r)`.
- `abs_dcross = abs(cross - pred_cross)`.
- `abs_daz` is wrapped angular distance between `az` and `pred_az`.
- `temporal_distance_raw` is a robust normalized distance within the candidate group.
- Lower temporal distance is better.
- The distance is converted to group-wise `temporal_rank_percentile`, where best is `0.0` and worst is `1.0`.

If A005 is missing or ambiguous for a group, temporal is marked unavailable and its percentile is `1.0`.

## 4. Active Structure Signal

The structure signal reuses the pre-registered structure-only output computed over the full A001 candidate bank without GT or A021 input.

Primary structure signals:

- S1: `box_to_background_ratio`, `inside_energy_fraction`, `optional_local_contrast`.
- S2: `box_to_background_ratio`, `inside_energy_fraction`.

S3 is diagnostic only because `edge_spillover_ratio` was weak in the full audit.

For combined scoring, `s1_score` and `s2_score` are converted again to group-wise rank percentiles, lower is better. Structure unavailable candidates receive percentile `1.0`.

## 5. Pre-Registered Variants

### C1 `equal_temporal_s1`

- Score = `0.5 * temporal_rank_percentile + 0.5 * s1_rank_percentile`.
- Lower score is better.
- Main variant.

### C2 `equal_temporal_s2`

- Score = `0.5 * temporal_rank_percentile + 0.5 * s2_rank_percentile`.
- Lower score is better.
- Main variant, used to check optional local contrast risk.

### C3 `temporal_guard_structure_promote`

- Score = `0.67 * temporal_rank_percentile + 0.33 * s1_rank_percentile`.
- Lower score is better.
- Tests whether a temporal guard can preserve v1 center-error advantage while allowing structure to promote better candidates.

### C4 `structure_guard_temporal_soft_diagnostic`

- Score = `0.33 * temporal_rank_percentile + 0.67 * s1_rank_percentile`.
- Lower score is better.
- Diagnostic only. It tests whether structure-dominant ranking further improves best-proxy top-k at the cost of center error.

### C5 `temporal_only_recomputed_baseline`

- Score = `temporal_rank_percentile`.
- Lower score is better.
- Internal baseline only, not a new method.

Weights are fixed here and must not be changed after evaluation.

## 6. Scoring Rule

The group key is:

`target_identity + scene + sar_frame_num + gm17_track_id`

All components are group-wise rank percentiles:

- Best component value gets `0.0`.
- Worst component value gets `1.0`.
- If a group has one candidate, the available component percentile is `0.0`.
- Unavailable components are `1.0`.
- Combined score is lower-is-better.
- Tie-break is stable ascending `candidate_id` only.

No GT, A021, source/provenance field, legacy score, selected output, B patch, or oracle field may be used for ranking or tie-break.

## 7. Evaluation Plan

The pilot first generates combined ranked output. Only after that output exists, evaluation may read A019 and A021.

Evaluation metrics:

- Mean and median center error.
- Mean and median axis-aligned proxy IoU.
- Proxy IoU recall at rank 1, 3, and 5 using threshold 0.25.
- Center recall at rank 1, 3, and 5 using threshold 50 px.
- `rank1_is_best_proxy`.
- `rank1_is_best_center`.
- Best-proxy top5 and top20.
- Mean and median rank of best proxy.
- Best candidate coverage.
- Temporal-zero dependency or status.

The evaluation compares against v1, v2, and structure-only. A021 is post-inference failure grouping only. Results must not feed back into the rule.

## 8. Success Questions

The combined pilot does not need every metric to be best. It should answer:

- Do C1/C2 improve `rank1_is_best_proxy` over v1?
- Do C1/C2 retain the structure-only best-proxy top20 advantage?
- Does C3 reduce the structure-only mean center error?
- Is any combined variant more balanced than v1, v2, and structure-only?
- Is the result strong enough to justify a factor graph combined pilot?

## 9. Risks

- Structure is computed on display/pseudocolor images, not raw SAR intensity.
- Temporal comes from the legacy A005 soft prior.
- A001 remains a legacy candidate-bank container.
- Severe truncated+occluded targets may still fail.
- This pilot is not a final physical model.

If the result fails, likely causes include temporal-structure conflict, persistent temporal artifact, display-image structure limits, A001 candidate limitations, need for raw SAR, need for rotated OBB patch features, or need for independent candidate proposal.
