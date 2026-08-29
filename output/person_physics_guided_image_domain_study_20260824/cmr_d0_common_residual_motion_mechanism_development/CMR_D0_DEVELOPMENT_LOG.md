# CMR-D0 mechanism development log

## Iteration 0: scene-majority baseline

1. Observed problem: M0B1-V2 showed R02 branch direction exactly reproduced the scene-global direction.
2. Real case: the frozen R02 scene-common positive case.
3. Failure: branch majority is circular as a primary common estimator because branch motion can enter the baseline.
4. Repair: use detection-masked background image registration as the primary estimator; retain branch consensus only as a diagnostic.
5. Meaning: background affine-partial GMC estimates shared optical image displacement, not camera or platform trajectory.
6. Side effect: windows with weak background texture become unavailable rather than receiving a forced common vector.

## Iteration 1: common uncertainty

1. Observed problem: point estimates forced small estimator errors into false residual signs.
2. Repair: deterministic spatial feature holdout; convert held-out x-residual P90 into angular uncertainty through the frozen positive mapping slope.
3. Meaning: the uncertainty describes estimator repeatability, not bbox support width and not PERSON confidence.
4. Result: optical residual states are `{'OPTICAL_RESIDUAL_COMMON_COMPATIBLE': 104, 'OPTICAL_RESIDUAL_ABOVE_COMMON': 76, 'OPTICAL_RESIDUAL_DEFORMATION_OR_MIXED': 45, 'OPTICAL_RESIDUAL_COMMON_ESTIMATE_AMBIGUOUS': 6}`.

## Iteration 2: branch consensus hybrid

1. Observed problem: background GMC and multi-branch consensus can disagree.
2. Repair: no weighted averaging.  Materialize agreement, mild disagreement, strong disagreement, and one-unavailable states.
3. Result: hybrid states are `{'COMMON_ESTIMATORS_AGREE': 51, 'BACKGROUND_ONLY_AVAILABLE': 38, 'COMMON_ESTIMATORS_MILD_DISAGREEMENT': 16, 'COMMON_ESTIMATORS_STRONG_DISAGREEMENT': 2}`.

## Iteration 3: SAR residual representation

1. Rejected idea: region-centroid displacement minus P0 vector as the primary SAR residual.
2. Repair: warp the full q95 source mask with frozen P0 soft occupancy and compare predicted versus observed left/right support boundaries, width, overlap, and topology.
3. Meaning: response-support residual, not PERSON motion.
4. Result: SAR states are `{'SAR_P0_RESIDUAL_ABOVE_COMMON': 10089, 'SAR_P0_RESIDUAL_BELOW_COMMON': 8516, 'SAR_P0_RESIDUAL_DEFORMATION_OR_MIXED': 4786, 'SAR_P0_RESIDUAL_COMMON_COMPATIBLE': 79, 'SAR_P0_RESIDUAL_BOUNDARY_CENSORED': 58}`.

## Iteration 4: cross-modal relation

1. Chosen relation: direction and structural compatibility only; no magnitude equality or fitted cross-projection scale.
2. Rejected route: residual ordering as v0 evidence because no runtime-legal branch-to-SAR-edge correspondence exists; ordering would silently introduce assignment.
3. Result: relations are `{'RESIDUAL_STRUCTURALLY_INDETERMINATE': 11075, 'RESIDUAL_RELATION_WEAK_OR_UNRESOLVED': 9195, 'RESIDUAL_DIRECTION_CONCORDANT': 5342, 'RESIDUAL_DIRECTION_CONTRADICTORY': 4350, 'RESIDUAL_COMMON_ESTIMATE_AMBIGUOUS': 925}`.
4. GT-blind possible-rescue candidates: `51`.  These are development cases, not established rescue.

## Iteration 5: visual mechanism audit

1. Cross-modal figures were repaired to overlay source q95, frozen-P0 predicted support, destination q95, full-frame context, and local zoom.
2. Optical deformation examples show asynchronous bbox-boundary changes; strong common-estimator conflicts occur in multi-person occlusion/shared-umbrella scenes.
3. No below-common category was created by threshold tuning: negative midpoint descriptors=`13`, both point boundaries negative=`3`, both uncertainty-adjusted upper bounds negative=`0`.
4. Paired possible-rescue/deceptive hypotheses can both retain high SAR support overlap in the same window; candidate differentiation is visible, but correctness/rescue is not established.
5. Earlier offline grounding packs were reviewed and still lack an authoritative cross-modal identity cue.

## Eligibility accounting audit

- `394` is the number of scheduled lag-1 window rows across R01ZF/R02ZF/R03ZF/R04ZF, not eligible branch instances.
- The frozen GT-blind intersection leaves `205` eligible windows: `107` development and `98` confirmation-input windows.
- Development eligible branch instances are the sum of continuous runtime fragments over development eligible windows: `231`.

## Isolation and overfitting audit

- Development windows: `107` across R01ZF/R02ZF/R03ZF.
- Confirmation availability: `98` eligible R04ZF windows.
- Confirmation residuals/outcomes accessed: `NO`.
- Manual SAR reference used to choose estimator, representation, uncertainty, or cases: `NO`.
- Main overfitting risk: estimator-state definitions were developed on exposed runs and must be tested once on R04ZF without repair.
