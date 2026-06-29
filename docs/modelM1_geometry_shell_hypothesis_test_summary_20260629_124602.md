# Model M1 Geometry-Aware Shell Hypothesis Test Summary

Date: 20260629_124602

## 1. Purpose

This is a model hypothesis test loop, not a generic audit. It defines M1, runs a post-hoc experiment, analyzes the result, judges whether M1 holds, and decides the next model step.

## 2. M1 Hypothesis

Model M1: SAR localization error should be modeled in geometry-aware range/cross/azimuth coordinates rather than as isotropic image x/y grid offsets.

中文解释：光学到 SAR 的迁移误差不应主要建模为图像平面 x/y 上的均匀偏移，而应建模为 SAR 几何中的 range、cross、azimuth 方向不确定性。如果 A001 的优势主要来自 range/cross 方向上的系统性修正，那么 Phase5B-v1 应该优先重构 geometry-aware shell，而不是调 v0 的 energy peak、Otsu、top-k 或 crop。

## 3. Experiment Design

Inputs are frozen Phase5B-v0 proposals, Phase5C-v0 post-hoc results, A005 proxy fields, A001 oracle candidate ids from Phase4D, and A001 candidate-bank geometry fields. A001 and Phase5C fields are used only post-hoc for this model test.

## 4. A001 Anatomy Results

- Target count: 205
- Best-center candidate join success: 205 / 205 (1.0)
- Best-IoU candidate join success: 205 / 205 (1.0)
- Best-center normalized offset median / p90: 0.11003 / 0.388783
- Best-center |delta_r| median / p90: 15.551671 / 69.463451
- Best-center |delta_cross| median / p90: 5.309785 / 15.813312
- Best-center |delta_az| median / p90: 0.790778 / 1.072631
- Best-center scale_w median / p90: 1.0 / 1.0
- Best-center scale_h median / p90: 1.0 / 1.0

Candidate source and expansion distributions are written to `modelM1_a001_geometry_offset_summary.json`.

## 5. v0 Route A vs A001

The comparison file `modelM1_v0_routeA_vs_a001_offset_comparison.csv` measures whether v0 A-only x/y grid hypotheses cover the A001 oracle offset. The key diagnostic is `offset_vector_gap_center_norm`, paired with A001 `delta_r`, `delta_cross`, and `delta_az`.

Median center offset gap norm: 0.082096

P90 center offset gap norm: 0.226195

## 6. Evidence For / Against M1

Label counts:

- `mixed_or_unclear`: 121
- `weak_or_no_support_for_M1`: 36
- `supports_candidate_source_diversity`: 33
- `supports_M1_range_cross`: 14
- `supports_M1_anisotropic_xy`: 1

Percentage supporting M1: 0.073171

Percentage supporting M1 among A001-advantage cases: 0.08982

Alternative explanations:

- Extent model instead: 0.0
- Candidate-source diversity: 0.160976
- Weak/no support: 0.17561

Non-exclusive evidence factors are written to `modelM1_evidence_factors_per_target.csv`.

Threshold sensitivity for the M1 support definition is written to `modelM1_threshold_sensitivity.csv`:

- threshold 0.05: support 116 / 205 all targets (0.565854), 116 / 167 A001-advantage targets (0.694611)
- threshold 0.10: support 74 / 205 all targets (0.360976), 74 / 167 A001-advantage targets (0.443114)
- threshold 0.15: support 43 / 205 all targets (0.209756), 43 / 167 A001-advantage targets (0.257485)
- threshold 0.20: support 23 / 205 all targets (0.112195), 23 / 167 A001-advantage targets (0.137725)
- threshold 0.25: support 14 / 205 all targets (0.068293), 14 / 167 A001-advantage targets (0.083832)

## 7. Route D Readiness

Route D readiness: `PARTIAL`.

Reasons:

- fan/range valid support mask not identified
- range/cross to image x/y mapping not frozen
- raw SAR source not identified for Route D

Inference-side r/az/cross fields are available, but Route D is not READY until fan/range valid support and coordinate mapping are frozen.

## 8. New-Hypothesis Cases

New-hypothesis review cases are written to `modelM1_new_hypothesis_review_cases.csv`.

Review case count: 10

Manual question: Is this a true SAR-supported state? Is outside-A001 novelty real? Does it support geometry-aware shell, SAR observation, or neither?

## 9. M1 Judgment

Final M1 judgment: `M1_NOT_SUPPORTED`.

This judgment follows the transparent rule recorded in `modelM1_evidence_summary.json`: support labels need to cover at least 40% of all targets or 40% of A001-advantage targets for partial support, and 60% for strong support. High missing joins force inconclusive.

M1 strong claim is not supported. This rejects the claim that A001's advantage is mainly explained by range/cross offsets not covered by v0 Route A. It does not reject SAR geometry-aware modeling in general. The stronger signal is candidate-source structure, especially wedge_joint_candidate.

## 10. Next Model Decision

Next = propose M2 such as extent-scale or candidate-source diversity model.

## 11. Boundary

- Post-hoc model hypothesis test only.
- No v1 proposal generated.
- No v1 generator.
- No Phase5B-v0 config change.
- No v0 proposal regeneration.
- No source file modification.
- No C3/C4 integration.
- No threshold tuning.
- No training.
- No calibration.
- No push.
