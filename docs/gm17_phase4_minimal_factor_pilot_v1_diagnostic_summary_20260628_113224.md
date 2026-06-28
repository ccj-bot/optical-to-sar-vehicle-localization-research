# GM17 Phase4 Minimal Factor Pilot V1 Diagnostic Summary 20260628_113224

## 1. Diagnostic Purpose

This run diagnoses the completed GM_RM017-only minimal factor pilot v1. It asks why A001 contains good candidates while the v1 rank1 rule often does not select the best-proxy or best-center candidate.

## 2. Inputs Used

- Pilot directory: `output\gm17_phase4_minimal_factor_pilot_20260628_110447`
- A001 provenance source: `D:\profile\research\workspace\output\clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2\candidate_bank_inference.csv`
- V1 outputs: `pilot_candidates_ranked.csv`, `pilot_selected_rank1.csv`, `pilot_manifest.json`, `evaluation_summary.json`, `evaluation_per_target.csv`, `evaluation_condition_groups.csv`

## 3. Output Directory

`D:\profile\research\workspace\output\gm17_phase4_minimal_factor_pilot_v1_diagnostics_20260628_113224`

## 4. Boundary Statement

This is post-inference diagnostic analysis only. It does not rerun v1 selection, does not create v2 ranking, does not tune thresholds, does not train weights, and does not promote A021 condition labels into inference.

A001 `candidate_source` / provenance fields were read only after ranking for diagnostic explanation. They were not used for sorting, scoring, or v2 rule generation.

## 5. Rank1 vs Best Candidate Findings

- Targets: 205
- Candidates: 58251
- `rank1_is_best_proxy` rate: 11.2%
- `rank1_is_best_center` rate: 10.2%
- Best-proxy in top5 / top20: 18.0% / 28.8%
- Best-center in top5 / top20: 16.1% / 27.3%

## 6. Best Candidate Rank Distribution

- Best-proxy mean / median / p90 rank: 67.58 / 40.00 / 190.80
- Best-center mean / median / p90 rank: 72.75 / 40.00 / 206.40

The best candidate is usually present in A001 but often appears tens of ranks below the v1 temporal-first rank1 choice.

## 7. Temporal-Zero Artifact Diagnostic

- Rank1 temporal-zero rate: 100.0%
- Mean / median / max temporal-zero candidates per target: 1.48 / 1.00 / 3
- Temporal-zero bad cases: 53 (25.9%)
- Rank1 temporal-zero equals best-proxy / best-center: 11.2% / 10.2%

This supports the diagnosis that the v1 temporal component is strongly affected by an A005-aligned legacy base-candidate artifact.

## 8. Geometry Difference Diagnostic

- Mean rank1-vs-best_proxy center-error gap: 24.01
- Mean rank1-vs-best_proxy proxy-IoU gap: -0.2898
- Mean absolute width / height / aspect / area gaps: 2.22 / 0.93 / 0.0036 / 329.15
- Mean absolute heading / r / cross / az gaps: 75.98 / 26.26 / 6.72 / 0.60

The most actionable geometry directions are fixed size/aspect/area plausibility and careful residual analysis in r/cross/az. These are diagnostic directions, not tuned rules.

## 9. Failure Grouping Diagnostic

Worst groups by temporal-zero bad-case rate and center error:

| condition | n | mean rank1 center error | mean rank1 proxy IoU | rank1 best-proxy rate | top20 best-proxy | bad-case rate |
|---|---:|---:|---:|---:|---:|---:|
| truncated+occluded / mild / moderate | 1 | 98.25 | 0.0138 | 0.0% | 0.0% | 100.0% |
| truncated+occluded / moderate / mild | 1 | 56.30 | 0.2446 | 0.0% | 0.0% | 100.0% |
| truncated+occluded / severe / moderate | 5 | 78.20 | 0.1548 | 0.0% | 0.0% | 80.0% |
| truncated+occluded / moderate / moderate | 6 | 67.42 | 0.2185 | 0.0% | 0.0% | 66.7% |
| truncated+occluded / mild / mild | 14 | 66.70 | 0.1744 | 0.0% | 0.0% | 64.3% |
| truncated+occluded / severe / severe | 5 | 51.34 | 0.3484 | 0.0% | 40.0% | 40.0% |

Failure remains concentrated in truncated+occluded groups, especially mild/moderate/severe combinations where rank1 temporal-zero candidates miss better candidates deeper in A001.

## 10. Source / Provenance Diagnostic

- Rank1 source distribution: `{'base_candidate': 205}`
- Best-proxy source distribution: `{'wedge_joint_candidate': 147, 'base_candidate': 23, 'bidirectional_escape_candidate': 15, 'multi_peak_ray_candidate': 12, 'track_signed_escape_candidate': 7, 'visible_support_candidate': 1}`

Source/provenance is useful for identifying legacy artifacts, but should remain diagnostic-only. It should not become an active scoring input.

## 11. Geometry Factor V2 Candidate Directions

- `size_aspect_fixed_prior`: Audit whether fixed vehicle-size/aspect plausibility can separate temporal-zero base candidates from better covered candidates. Evidence: Mean rank1-vs-best_proxy aspect gap=0.0036; w gap=2.22; h gap=0.93.
- `area_fixed_prior`: Check whether area consistency can reject implausible base candidates before temporal distance dominates. Evidence: Mean rank1-vs-best_proxy area gap=329.15.
- `heading_consistency`: Inspect whether heading is stable enough for a fixed prior or should remain diagnostic only. Evidence: Mean rank1-vs-best_proxy heading gap=75.98.
- `range_cross_az_residual_structure`: Compare temporal-zero candidates against best candidates to see if SAR-side local residual structure can help. Evidence: Mean gaps r=26.26, cross=6.72, az=0.60.

## 12. Optical Temporal Factor V2 Candidate Directions

- Separate A005-aligned base-candidate artifacts from true temporal consistency.
- Keep temporal evidence soft; do not let optical prior overwrite or move SAR candidates.
- Recompute any temporal residuals only from approved safe fields, not legacy `delta_*_from_pred` or `temporal_factor_score`.

## 13. Explicitly Not Recommended

- Do not directly sort by `candidate_source`.
- Do not use `temporal_factor_score`.
- Do not use `delta_*_from_pred`.
- Do not tune thresholds from GT.
- Do not feed A021 condition labels into inference.

## 14. Next Step

If this diagnostic is accepted, write a `geometry_factor v2 fixed-prior spec` focused on physical size/aspect/area and coordinate residual ownership. In parallel, write an `optical_temporal_factor v2 diagnostic spec` that separates temporal-zero base artifacts from real temporal consistency. Do not directly tune v2 thresholds from these evaluation results.
