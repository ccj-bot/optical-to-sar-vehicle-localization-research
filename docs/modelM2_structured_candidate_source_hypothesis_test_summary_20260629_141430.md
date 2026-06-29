# Model M2 Structured Candidate-Source Hypothesis Test Summary

Date: 20260629_141430

## 1. Purpose

This is a model hypothesis test loop, not a generic audit and not an attempt to copy A001. It tests whether A001's Phase5C advantage is better explained by structured candidate-source families than by generic range/cross shell offsets alone.

## 2. M2 Hypothesis

M2: A001's advantage over Phase5B-v0 is not mainly caused by generic range/cross shell offsets, but by structured candidate-source families, especially `wedge_joint_candidate`, which may encode SAR-support geometry, ray/wedge consistency, escape mechanisms, or source-specific uncertainty.

## 3. Experiment Design

Inputs are frozen Phase5B-v0 proposals, Phase5C-v0 post-hoc comparison files, the latest M1 outputs, the A001 candidate bank, Phase4D A001 baseline, and A021 condition labels as post-hoc labels only.

Latest M1 output: `output/modelM1_geometry_shell_hypothesis_test_20260629_124602`.

Target count: 205.

## 4. Candidate-Source Dominance

Best-center source highlights:

- `wedge_joint_candidate`: count 148 (0.721951), median center error 5.76993, median delta center -7.030378
- `base_candidate`: count 21 (0.102439), median center error 5.849116, median delta center -0.0
- `bidirectional_escape_candidate`: count 15 (0.073171), median center error 5.846514, median delta center -34.45162
- `multi_peak_ray_candidate`: count 12 (0.058537), median center error 3.449865, median delta center -4.194589
- `track_signed_escape_candidate`: count 8 (0.039024), median center error 4.128222, median delta center -22.268704
- `visible_support_candidate`: count 1 (0.004878), median center error 5.480977, median delta center -13.710931

Full source dominance is written to `modelM2_candidate_source_oracle_dominance.csv`.

## 5. Condition Dependency

Condition dependency is reported by source x `condition_type`, source x `truncation_degree`, and source x `occlusion_degree` in `modelM2_candidate_source_condition_dependency.csv`.

This join is post-hoc only. It does not feed A021 condition labels into proposal generation or inference.

## 6. Source-Family Geometry Anatomy

Source-family geometry anatomy is written to `modelM2_source_family_geometry_anatomy.csv`.

Best-center highlights:

- `wedge_joint_candidate` / best_center: median normalized offset 0.122467, median |delta_r| 17.26878, median |delta_cross| 6.580356, median offset gap 0.084282
- `base_candidate` / best_center: median normalized offset 0.0, median |delta_r| 0.0, median |delta_cross| 0.0, median offset gap 0.0
- `bidirectional_escape_candidate` / best_center: median normalized offset 0.544112, median |delta_r| 96.0, median |delta_cross| 12.0, median offset gap 0.220368
- `multi_peak_ray_candidate` / best_center: median normalized offset 0.049608, median |delta_r| 3.614064, median |delta_cross| 0.0, median offset gap 0.049608
- `track_signed_escape_candidate` / best_center: median normalized offset 0.37132, median |delta_r| 60.0, median |delta_cross| 24.0, median offset gap 0.203651
- `visible_support_candidate` / best_center: median normalized offset 0.208935, median |delta_r| 33.358026, median |delta_cross| 15.822102, median offset gap 0.135795

## 7. Wedge-Specific Findings

- Wedge best-center count/rate: 148 / 205 (0.721951)
- Wedge best-IoU count/rate: 139 / 205 (0.678049)
- Wedge strong both count: 101
- Wedge strong center count: 31
- Wedge strong IoU count: 1
- Wedge not-better count: 17
- Association interpretation: wedge advantage is source-family dominated with range/cross and hard-condition co-signals

Per-target wedge evidence is written to `modelM2_wedge_joint_candidate_analysis.csv`; summary is written to `modelM2_wedge_summary.json`.

## 8. Density / Diversity Suspicion

Density-only suspicion count/rate: 14 / 205 (0.068293).

Density-only suspicion appears in 14/205 cases in the auxiliary density audit, but it does not dominate final M2 evidence labels. This suggests candidate density/source diversity may contribute in a few cases, but it is not the primary explanation for A001's advantage.

The density check is written to `modelM2_candidate_density_vs_source_diversity.csv`. This check asks whether A001 is strong only because candidate count or source diversity is high. It does not copy any A001 candidate id.

## 9. Evidence For / Against M2

Label counts:

- `supports_M2_wedge_structured_source`: 126
- `weak_or_no_support_for_M2`: 39
- `supports_M2_escape_or_ray_source`: 33
- `supports_M2_source_diversity`: 7

Percentages:

- Wedge structured source: 0.614634
- Wedge structured source among A001-advantage cases: 0.754491
- Source diversity: 0.034146
- Escape/ray source: 0.160976
- Density-only final evidence label: 0.0
- Density-only auxiliary audit suspicion: 0.068293
- Weak/no support: 0.190244

Per-target evidence is written to `modelM2_per_target_evidence.csv`.

## 10. M2 Judgment

Final M2 judgment: `M2_STRONGLY_SUPPORTED`.

Reason: wedge structured-source support exceeds both all-target and A001-advantage thresholds.

This supports a source-structured modeling direction only as a next design hypothesis. It is not a v1 proposal generator and not a final inference result.

## 11. Next Model Decision

Next model family: `M2a_wedge_consistency_model`.

Rationale: structured source-family evidence is strong enough to design, not run, a wedge-aware v1 proposal model after manual review.

Decision flags:

- `should_commit_to_v1_generator_now`: False
- `should_hold_phase5D`: True
- `should_reject_A001_copying`: True
- `should_run_manual_review`: True

Manual review should focus on wedge-strong cases, ray/escape hard-condition cases, density-only suspicion cases, and Phase5B-good counterexamples before any v1 generator is approved.

## 12. Boundary

- Post-hoc model hypothesis test only.
- No v1 proposal generated.
- No v1 generator.
- No A001 candidate copying.
- No Phase5B-v0 config change.
- No v0 proposal regeneration.
- No source file modification.
- No C3/C4 integration.
- No threshold tuning.
- No training.
- No calibration.
- No push.
