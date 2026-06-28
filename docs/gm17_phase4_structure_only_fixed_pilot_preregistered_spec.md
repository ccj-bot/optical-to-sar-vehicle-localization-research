# GM17 Phase4S Structure-Only Fixed Pilot Preregistered Spec

## 1. Current Position

This document belongs to Phase4S. It is a pre-registered fixed pilot spec for a structure-only SAR candidate ranking pilot.

It is not v3 table tuning. It is not a final model. It does not authorize changing rules after seeing evaluation results.

The goal is to test whether SAR image structure alone can act as an independent candidate ordering signal over the full A001 candidate bank.

## 2. Candidate Pool

The candidate pool is the full A001 GM_RM017 candidate bank:

`output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv`

The pilot must:

- Use all A001 candidates for GM_RM017.
- Load only safe candidate fields: `candidate_id`, `target_identity`, `scene`, `sar_frame_num`, `gm17_track_id`, `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross`.
- Not filter by `best_proxy` or `best_center` identity from the full audit.
- Not use `candidate_source`.
- Not generate new candidates.
- Not move candidate boxes.
- Not modify the candidate bank.

The Phase4S full audit may only justify the pre-registered feature family and risk boundary. It cannot define the candidate pool.

## 3. Active Ranking Features

Only these three active ranking features are allowed in primary fixed ranking:

- `box_to_background_ratio`: higher is better.
- `inside_energy_fraction`: higher is better.
- `optional_local_contrast`: higher is better.

All other structure features are diagnostic-only unless explicitly listed in the diagnostic variant below.

## 4. Pre-Registered Variants

### S1 `primary_structure_rank3`

- Active features: `box_to_background_ratio`, `inside_energy_fraction`, `optional_local_contrast`.
- Within each target/frame/track candidate group, each feature is converted to a rank percentile.
- The three feature rank percentiles are averaged with equal weight.
- No threshold is used.
- This is the primary structure-only variant.

### S2 `conservative_structure_rank2`

- Active features: `box_to_background_ratio`, `inside_energy_fraction`.
- Within each group, both features are converted to rank percentiles.
- The two feature rank percentiles are averaged with equal weight.
- No threshold is used.
- This checks whether `optional_local_contrast` adds display-image risk.

### S3 `structure_with_spillover_diagnostic`

- Active features: `box_to_background_ratio`, `inside_energy_fraction`, `optional_local_contrast`, `edge_spillover_ratio`.
- `box_to_background_ratio`, `inside_energy_fraction`, and `optional_local_contrast` are higher-is-better.
- `edge_spillover_ratio` is lower-is-better.
- The four feature rank percentiles are averaged with equal weight.
- No threshold is used.
- Because `edge_spillover_ratio` was weak in the full audit, S3 is diagnostic and cannot be the main conclusion.

## 5. Features Not Used As Active Inputs

The following features are not active ranking inputs:

- `box_sum_intensity`.
- `box_max_intensity`.
- `peak_to_background_ratio`.
- `optional_peak_inside_box_flag`.
- `center_to_peak_distance`.
- `simple_long_axis_support`.
- `simple_short_axis_support`.
- `box_top5_mean_intensity`.

They may appear in diagnostic tables only when clearly marked as diagnostic.

## 6. Fixed Scoring Rule

The group key is:

`target_identity + scene + sar_frame_num + gm17_track_id`

For every feature in a variant:

- Higher-is-better features are ranked in descending order.
- Lower-is-better features are ranked in ascending order.
- Rank percentile is normalized as `(rank - 1) / (group_size - 1)`.
- The best value receives `0.0`; the worst value receives `1.0`.
- If a group has one candidate, its percentile is `0.0`.
- If a feature is unavailable for a candidate, its percentile is `1.0` for that variant.

The variant score is the mean of its pre-registered feature rank percentiles. Lower score is better.

Final variant rank is group-wise ascending by score, then stable ascending `candidate_id` tie-break.

No GT, A021 fields, source/provenance fields, legacy score fields, or selected outputs may be used for ranking or tie-break.

## 7. Evaluation Plan

The pilot first generates structure-only ranked outputs without loading A019 final boxes or A021 condition labels as ranking inputs.

Only after the structure-only output exists, the evaluation may read A019 and A021 to compute:

- Mean and median center error.
- Mean and median axis-aligned proxy IoU.
- Proxy IoU recall at rank 1, 3, and 5 using threshold 0.25.
- Center recall at rank 1, 3, and 5 using threshold 50 px.
- `rank1_is_best_proxy`.
- `rank1_is_best_center`.
- Best-proxy top5 and top20.
- Mean and median rank of best proxy.
- Best-candidate coverage.
- Comparison against v1 and v2.

A021 is post-inference failure grouping only. Evaluation results must not feed back into the rules.

## 8. Display/Pseudocolor Risk

This pilot uses `sar_pseudocolor_path` or equivalent display images through the Phase4S path report.

The result must be described as a diagnostic display-image pilot. It is not proof that these features are raw SAR intensity physics. If raw SAR intensity becomes available later, the features must be audited again before any physical claim is made.

## 9. Success Questions

This pilot does not need to dominate every metric. It must answer:

- Does S1 or S2 improve `rank1_is_best_proxy`?
- Does S1 or S2 improve best-proxy top5/top20?
- Does a structure-only ranking avoid the A005 temporal-zero dependency?
- Does it improve truncated+occluded groups?
- Is the signal strong enough to justify a combined structure+temporal pilot?

## 10. Failure Interpretation

If the pilot does not improve, likely causes include:

- Display-image features are not physical enough.
- A001 candidates still lack the right structure-support candidate in difficult cases.
- The feature extraction needs rotated OBB patches rather than axis-aligned crops.
- Raw SAR intensity is needed.
- Independent SAR candidate proposal is needed.

Failure does not authorize table-only v3 rule search.
