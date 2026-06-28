# GM17 Phase4 Minimal Factor Pilot Experiment Plan

## 1. Current Positioning

This document is a **minimal factor pilot experiment plan** for the new optical-to-SAR hierarchical candidate factor graph model.

It is only a planning document. It does not:

- run an experiment;
- create code;
- execute candidate selection;
- calculate metrics;
- read or join A019/A021;
- modify the candidate bank;
- train, tune, or calibrate anything.

This plan is not a GM17 patch, not an A001/A005 join scaffold, and not a legacy-score repair plan. It defines a GM_RM017-only pilot that can later test whether `geometry_factor` and `optical_temporal_factor` contain interpretable, separable candidate-level signals.

## 2. Experimental Questions

The pilot should answer only bounded factor-signal questions:

- Under a frozen A001 candidate bank, does `geometry_factor` provide candidate-level discrimination?
- Does `optical_temporal_factor` provide candidate-level discrimination?
- Is a fixed geometry + temporal combination more stable than either single factor?
- Do failures concentrate in Line A risk conditions such as truncation, occlusion, near-field, SAR-only, or optical-unresolved cases?
- Can the pilot expose usable factor evidence without proving final new-model performance?

This pilot can validate factor signals. It cannot prove that A001/A005 are correct, cannot prove that the final new model is performant, and cannot justify continued GM17 patching.

## 3. Experiment Scope

The scope is intentionally narrow:

- GM_RM017 only.
- A001 as a frozen old candidate bank and GM_RM017-only pilot container.
- A005 as a soft optical-temporal prior for pilot temporal-consistency reference.
- No extension to GM_RM011 or GM_RM019.
- No generation of new candidates.
- No modification, filtering, expansion, or repair of A001.
- No use of legacy `score`, `decision`, `source`, or `anchor` fields.

If the frozen A001 container is inadequate, the conclusion is that this legacy pilot is bounded or unsuitable. It does not mean the new factor graph model failed.

## 4. Input Fields

The following fields are safe as future experiment-design inputs. This document does not actually read or join any data.

### A001 Candidate Identity and Context

- `candidate_id`
- `target_identity`
- `scene`
- `sar_frame_num`
- `gm17_track_id`

### A001 Geometry

- `cx`
- `cy`
- `w`
- `h`
- `heading`
- `r`
- `az`
- `cross`

### A005 Temporal Prior

- `pred_r`
- `pred_cross`
- `pred_az`

### A001/A005 Join Candidate Fields

- `target_identity`
- `scene`
- `sar_frame_num`
- `gm17_track_id`

These join keys are listed only to define a future design surface. This document does not perform the join.

## 5. Forbidden Fields

The pilot design must explicitly forbid the following fields from factor scoring, rule design, threshold selection, and candidate ranking:

- A019 `final_*`
- A021 `condition`, `truncation`, `occlusion`
- IoU
- center error
- recall
- oracle rank
- selected behavior
- B patch outputs
- `temporal_factor_score`
- `delta_*_from_pred`
- `pred_cx`
- `pred_cy`
- `pred_w`
- `pred_h`
- `pred_heading_deg`
- `score`
- `lr_score`
- `sar_factor_score`
- `candidate_source`
- `candidate_detail`
- `candidate_expansion_*`
- `gm17_temporal_source`
- `gm17_temporal_decision`
- `gm17_anchor_strength`
- `gm17_track_size`
- `gm17_anchor_n`
- `n_candidates`

These fields are forbidden because they can leak GT/evaluation information, reproduce GM17 selected behavior, import B patch logic, or turn A001/A005 into a legacy scoring framework.

## 6. Experiment Group Design

### E0 Candidate-Bank Coverage Check

Purpose:

- Confirm whether A001 contains candidates close enough to GT for a bounded pilot to be meaningful.

Rules:

- This is post-inference/evaluation in nature and must not participate in scoring.
- A019 may be used only in a future independent evaluation stage.
- If coverage is insufficient, the result means A001 is not suitable as a pilot container.
- Insufficient coverage does not mean the factors failed.

### E1 Geometry-Only Pilot

Purpose:

- Observe whether candidate geometry plausibility can exclude clearly bad candidates.

Allowed evidence:

- A001 candidate geometry fields only.

Forbidden evidence:

- A005.
- Legacy scores.
- GT-derived thresholds.
- A019/A021.
- Selected behavior.

Expected result type:

- A fixed-rule geometry plausibility output, not a trained score.

### E2 Optical-Temporal-Only Pilot

Purpose:

- Observe whether the optical temporal soft prior can provide candidate-level discrimination.

Allowed comparison:

- A001 candidate `r`, `cross`, `az` against A005 `pred_r`, `pred_cross`, `pred_az`.

Forbidden evidence:

- `temporal_factor_score`
- `delta_*_from_pred`
- `pred_cx` / `pred_cy` as candidate center generation or overwrite fields
- GT-derived thresholds
- legacy temporal decision fields

Expected result type:

- A soft temporal consistency output, not a hard optical controller.

### E3 Geometry + Temporal Combined Pilot

Purpose:

- Compare whether a fixed combination of safe geometry and temporal signals is more stable than either single factor.

Rules:

- Combine only safe signals from E1 and E2.
- Use fixed rules only.
- Do not tune rules with GT.
- Do not train weights.
- Do not calibrate.
- Do not copy legacy scores or selected behavior.

Expected result type:

- A bounded combined-factor pilot output for later post-inference evaluation.

## 7. Baseline Design

The pilot should compare factor outputs against simple baselines:

- random candidate baseline;
- first/base candidate baseline, only if A001 has a non-leaky base-candidate definition;
- temporal-nearest baseline, recomputed only from safe `r`/`cross`/`az` to `pred_r`/`pred_cross`/`pred_az` distance;
- geometry-only baseline;
- combined fixed-prior baseline.

Forbidden baseline sources:

- GM17 selected output;
- oracle;
- B patch;
- legacy score;
- legacy decision;
- legacy source;
- legacy anchor.

Baselines must test whether the planned factors contain signal. They must not reproduce old GM17 behavior.

## 8. Evaluation Plan

Evaluation can only happen after an independent pilot output has been generated from safe A001/A005 fields.

Future evaluation sequence:

1. Generate pilot output using only safe A001/A005 fields.
2. Join A019 only after output generation to calculate post-inference metrics.
3. Join A021 only after output generation for failure grouping.

Metrics may be planned but must not be calculated in this document:

- best candidate coverage;
- selected candidate IoU;
- selected center error;
- rank of best GT-overlap candidate;
- recall@K;
- per-condition failure grouping;
- per-truncation/occlusion subgroup analysis.

These metrics must not feed back into thresholds, weights, fixed rules, or calibration.

## 9. Ablation Design

Future ablations should include:

- geometry only;
- temporal only;
- geometry + temporal;
- no temporal when A005 is missing;
- no heading;
- no azimuth;
- no size prior;
- invalid geometry exclusion vs neutralization comparison.

The invalid-geometry comparison is only a preset strategy comparison. It must not be tuned with GT.

## 10. Success Criteria

Success does not mean that headline metrics must be high. Success means the pilot can answer whether the bounded evidence path is useful:

- Can it show whether A001 has pilot coverage?
- Can it determine whether `geometry_factor` has an independent signal?
- Can it determine whether `optical_temporal_factor` has an independent signal?
- Can it determine whether the combination is better than either single factor?
- Can it identify whether failures concentrate in specific conditions?
- Can it provide evidence for the new factor graph model without continuing to repair GM17?

If the result is negative but well explained, the pilot still succeeds as an architecture decision tool.

## 11. Failure Interpretation

Possible failure reasons include:

- A001 candidate-bank coverage is insufficient.
- A005 temporal prediction is inaccurate.
- A001/A005 join is unstable.
- `r`/`cross`/`az` coordinate conventions are inconsistent.
- Severe truncation, occlusion, or near-field cases make GT evaluation difficult.
- Legacy candidate generation limits the pilot ceiling.

These failures do not equal new-model failure. They only show that the legacy pilot boundary is limited or that a future independent candidate proposal layer is needed.

## 12. Leakage Prevention Rules

The future pilot must enforce the following leakage rules:

- GT may only be joined after candidate output generation.
- A021 may only be used for grouped analysis after candidate output generation.
- Do not tune rules using IoU or center error.
- Do not use oracle rank.
- Do not use selected behavior.
- Do not use legacy `score`, `decision`, `source`, or `anchor` fields.
- Do not convert Line A descriptive statistics into thresholds.
- Do not use A005 to generate, move, or overwrite SAR candidates.
- Do not treat A001/A005 as proof of physical correctness.

These rules are required to keep the pilot aligned with the new model architecture instead of the old GM17 patch path.

## 13. Future Execution Prerequisites

Before any future script is written, the following must be completed and reviewed:

- A001 hash confirmation.
- A001 row count confirmation.
- `candidate_id` uniqueness check.
- A001/A005 join integrity audit.
- Coordinate convention confirmation.
- Missing A005 prior policy.
- Invalid geometry policy.
- Output schema confirmation.
- Post-inference evaluation join boundary confirmation.

These are prerequisites for a later implementation specification. They are not performed in this document.

## 14. Recommended Next Steps

After this document is reviewed manually, the next step can be a minimal pilot implementation specification.

Only after the implementation specification is accepted should a script be written. The first script version must read only approved inputs and output an independent pilot result without reading A019/A021. The evaluation script must be separate and may run only after pilot output generation.

Until then, A001/A005 join/scaffold work remains paused except where explicitly scoped as a GM_RM017-only legacy pilot.
