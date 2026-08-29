# CMR-v0 frozen mechanism specification

- State: `CMR_V0_MECHANISM_FROZEN_AFTER_DEVELOPMENT`
- Stage role: mechanism contract ready for a separate confirmation task.
- Confirmation executed here: `NO`.

## Inputs

Runtime-legal optical detections and raw fragments; optical image pairs; nominal timing query; fixed positive optical-to-SAR azimuth mapping; q95 response regions/masks; latest pixel topology; frozen P0 pair/model/comparability; boundary/availability metadata.

Manual target identity, physical target ID, SAR reference, and offline grounding are excluded from mechanism calculation.

## Optical common apparent motion v0

1. Mask all detected target boxes with a fixed geometric padding.
2. Track background features with forward/backward LK.
3. Use a deterministic spatial holdout.
4. Fit affine-partial GMC by RANSAC to fit anchors.
5. Evaluate the affine at each branch bbox; preserve left/right boundary predictions.
6. Uncertainty is held-out x-residual P90 converted by the frozen mapping slope.
7. Branch consensus is diagnostic only.  Strong background/consensus disagreement produces `COMMON_ESTIMATE_AMBIGUOUS`; no averaging.

Unavailable states cover missing images, insufficient features/tracks, failed affine fit, or implausible scale.

## Optical branch residual v0

For each corresponding boundary, subtract the common prediction interval.  Both residual boundary intervals above zero give `ABOVE_COMMON`; both below give `BELOW_COMMON`; both containing zero give `COMMON_COMPATIBLE`; mixed boundaries give `DEFORMATION_OR_MIXED`.

Development observed no definite `BELOW_COMMON`: negative midpoint descriptors were absorbed by uncertainty or had opposing boundary behavior.  This absence is retained as a data/mechanism observation and thresholds are not tuned to populate the category.

## SAR P0-relative residual v0

Warp the binary q95 source support through frozen P0 using the frozen M0A soft affine convention.  Compare soft overlap and the 0.5-occupancy predicted boundary with the observed q95 destination support.  P0 held-out P90 residual is converted locally to angular boundary uncertainty.  Boundary/truncated cases are censored.  Split/merge-like topology is retained and never forced into rigid velocity.

## Cross-modal relation v0

Only residual direction/structure is compared.  Same definite residual sign is concordant; opposite sign is contradictory; common-compatible is weak/unresolved; deformation or censoring is structurally indeterminate; unavailable stays unavailable.  No magnitude fit, weighted score, rejection, pruning, identity, or assignment occurs.

## Output

Categorical evidence states, uncertainty, overlap/topology descriptors, provenance, and ambiguity.  The mechanism cannot output PERSON identity, physical motion, unique path, final SAR center, final SAR box, or P2.

## Development accounting

- Optical residual states: `{'OPTICAL_RESIDUAL_COMMON_COMPATIBLE': 104, 'OPTICAL_RESIDUAL_ABOVE_COMMON': 76, 'OPTICAL_RESIDUAL_DEFORMATION_OR_MIXED': 45, 'OPTICAL_RESIDUAL_COMMON_ESTIMATE_AMBIGUOUS': 6}`.
- SAR residual states: `{'SAR_P0_RESIDUAL_ABOVE_COMMON': 10089, 'SAR_P0_RESIDUAL_BELOW_COMMON': 8516, 'SAR_P0_RESIDUAL_DEFORMATION_OR_MIXED': 4786, 'SAR_P0_RESIDUAL_COMMON_COMPATIBLE': 79, 'SAR_P0_RESIDUAL_BOUNDARY_CENSORED': 58}`.
- Cross-modal relations: `{'RESIDUAL_STRUCTURALLY_INDETERMINATE': 11075, 'RESIDUAL_RELATION_WEAK_OR_UNRESOLVED': 9195, 'RESIDUAL_DIRECTION_CONCORDANT': 5342, 'RESIDUAL_DIRECTION_CONTRADICTORY': 4350, 'RESIDUAL_COMMON_ESTIMATE_AMBIGUOUS': 925}`.
- Development windows with more than one branch residual state: `36`.
