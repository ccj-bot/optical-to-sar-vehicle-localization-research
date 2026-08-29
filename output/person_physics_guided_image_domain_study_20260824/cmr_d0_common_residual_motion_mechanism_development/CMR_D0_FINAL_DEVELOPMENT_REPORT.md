# CMR-D0 common-residual motion mechanism development report

- Stage: `DEVELOPMENT`, not confirmation.
- Readiness: `READY_FOR_CMR_V0_CONFIRMATION`.
- Starting HEAD: `b6e7a3a5ade1844d14c771c7aaaa02099e663c3a`.

## Data split

Across the four cross-modal runs, `394` scheduled lag-1 pair rows enter the atlas; this is a window count, not a branch-instance count.  The frozen GT-blind intersection leaves `205` eligible windows.  Development uses R01ZF/R02ZF/R03ZF: `107` eligible windows and `231` branch instances.  R04ZF contains `98` eligible input windows and remains outcome-isolated.  Opposite-direction optical runs without complete frozen P0/topology are diagnostic-only.

## Optical common motion and residual

Background affine-partial GMC is the v0 primary common estimator.  Branch consensus is retained as a circularity-sensitive diagnostic and is never averaged with GMC.  Common states: `{'BACKGROUND_GMC_AVAILABLE': 107}`; hybrid states: `{'COMMON_ESTIMATORS_AGREE': 51, 'BACKGROUND_ONLY_AVAILABLE': 38, 'COMMON_ESTIMATORS_MILD_DISAGREEMENT': 16, 'COMMON_ESTIMATORS_STRONG_DISAGREEMENT': 2}`.  Residual states: `{'OPTICAL_RESIDUAL_COMMON_COMPATIBLE': 104, 'OPTICAL_RESIDUAL_ABOVE_COMMON': 76, 'OPTICAL_RESIDUAL_DEFORMATION_OR_MIXED': 45, 'OPTICAL_RESIDUAL_COMMON_ESTIMATE_AMBIGUOUS': 6}`.  `36` development windows contain more than one optical branch residual state after common decomposition.  No definite below-common case is observed: `13` midpoint descriptors are negative, `3` have both point boundary residuals negative, but `0` have both uncertainty-adjusted upper bounds below zero; thresholds are not tuned to force the category.

## SAR P0-relative residual

The primary object is the frozen-P0-warped q95 support versus observed destination support.  Boundary, width, overlap, split/merge-like topology, and unavailable states are preserved.  State counts: `{'SAR_P0_RESIDUAL_ABOVE_COMMON': 10089, 'SAR_P0_RESIDUAL_BELOW_COMMON': 8516, 'SAR_P0_RESIDUAL_DEFORMATION_OR_MIXED': 4786, 'SAR_P0_RESIDUAL_COMMON_COMPATIBLE': 79, 'SAR_P0_RESIDUAL_BOUNDARY_CENSORED': 58}`.  These are response-support residuals, not PERSON motion.

## Cross-modal residual relation

No magnitude equality or fitted scale is used.  Relation counts: `{'RESIDUAL_STRUCTURALLY_INDETERMINATE': 11075, 'RESIDUAL_RELATION_WEAK_OR_UNRESOLVED': 9195, 'RESIDUAL_DIRECTION_CONCORDANT': 5342, 'RESIDUAL_DIRECTION_CONTRADICTORY': 4350, 'RESIDUAL_COMMON_ESTIMATE_AMBIGUOUS': 925}`.  `51` windows satisfy a GT-blind development-only pattern containing both concordant and contradictory candidate hypotheses.  They are possible rescue cases for future reference evaluation, not established rescue.

## Branch grounding

No direct manual optical raw-fragment annotation was found.  A pre-existing frame-level offline geometric track-reference assignment provides an offline-only interface.  Grounding states: `{'LIKELY': 9, 'UNRESOLVED': 1}`.  It is excluded from runtime common motion, residuals, topology, timing, P0, and inference.

## Development lessons

- Background GMC is preferable to scene branch majority as the primary common estimator because it does not define common from the branches being tested.
- Point common estimates were insufficient; estimator uncertainty is necessary to preserve unresolved states.
- SAR centroid subtraction was rejected in favor of full support warp.
- Weighted background/branch common fusion and residual ordering were rejected.
- Multimodal visual review supports the deformation, estimator-ambiguity, SAR structural, and boundary-censoring states, while showing that high-overlap concordant and contradictory hypotheses can coexist.
- Direct review of earlier grounding packs does not establish authoritative raw-fragment-to-SAR identity.
- Confirmation overfitting risk remains real; R04ZF must be evaluated once with no repair.

## CMR-v0 and stop

The frozen contract is in `CMR_V0_MECHANISM_SPECIFICATION_FROZEN.md`.  The separate confirmation draft is not executed.  No pruning, tracker, assignment, factor graph, P2, center, or box is produced.
