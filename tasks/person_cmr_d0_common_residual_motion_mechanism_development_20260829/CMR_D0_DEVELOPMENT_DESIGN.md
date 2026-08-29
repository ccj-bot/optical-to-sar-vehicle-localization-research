# CMR-D0 development design

## Scientific role

`CMR_D0_COMMON_RESIDUAL_MOTION_MECHANISM_DEVELOPMENT` develops an
interpretable observation mechanism.  It does not seek a PASS and does not
execute confirmation.

Optical common motion and SAR P0 have analogous decomposition roles but are
not equated across modalities.  Optical residuals are image-domain branch
support residuals.  SAR residuals are q95 response-support residuals after the
frozen P0 transport.  Neither is PERSON physical velocity.

## Run-level isolation

- Development: `R01ZF`, `R02ZF`, `R03ZF`.
- Confirmation: `R04ZF`; availability audit only before freeze.
- Diagnostic: GT-blind optical opposite-direction runs without complete frozen
  cross-modal P0/topology coverage.

The split uses only run identity and pre-existing input availability.  It does
not use manual reference outcomes or CMR performance.

## Mechanism families

1. Background affine-partial GMC from detection-masked optical imagery.
2. Multi-branch robust consensus as a separate scene-consensus diagnostic.
3. Hybrid agreement state; no artificial weighted average.
4. Optical corresponding-boundary residual intervals relative to the common
   prediction and its estimator uncertainty.
5. SAR soft q95 source support warped by frozen P0 and compared with every q95
   destination region using boundary, overlap, translation, deformation, and
   topology descriptors.
6. Direction/order relations remain categorical evidence and never delete a
   hypothesis.

## Development discipline

Mechanism changes are justified by mathematics, estimator diagnostics, and
real images.  Confirmation data are not used for method selection.  Manual SAR
reference and physical target identity are prohibited from runtime mechanism
construction.
