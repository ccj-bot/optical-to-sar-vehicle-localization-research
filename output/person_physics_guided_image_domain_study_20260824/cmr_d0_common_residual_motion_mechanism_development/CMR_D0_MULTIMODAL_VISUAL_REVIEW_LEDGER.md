# CMR-D0 multimodal visual review ledger

- Review role: development-only mechanism audit; not confirmation and not runtime inference.
- CMR contact sheet reviewed: `figures/CMR_D0_DEVELOPMENT_CASE_CONTACT_SHEET.jpg`.
- Individual CMR cases reviewed: optical deformation, strong common-estimator disagreement, all five SAR structural-state examples, and the paired possible-rescue/deceptive hypotheses.
- Earlier grounding assets reviewed directly: M0B1-V2 `POST_REFERENCE_CASE_CONTACT_SHEET.png` and offline raw-fragment review packs 01, 03, and 08; the frozen review CSV records all ten packs as `UNRESOLVED`.

## Optical observations

1. The selected deformation case shows asynchronous bbox-boundary change: one boundary moves materially while the other is nearly fixed.  Occlusion and detector-box width change are visually plausible, so `DEFORMATION_OR_MIXED` is more faithful than forcing a residual sign.
2. Strong GMC/branch-consensus disagreement occurs in close multi-person, shared-umbrella/occlusion scenes.  Branch consensus can be contaminated by subject motion or detector grouping; keeping background GMC primary and emitting ambiguity is justified.
3. No `OPTICAL_RESIDUAL_BELOW_COMMON` case was manufactured.  Thirteen branches have a negative midpoint descriptor, but only three have both point boundary residuals negative and none has both uncertainty-adjusted upper bounds below zero.  Negative midpoint cases resolve to deformation/mixed or common-compatible.

## SAR observations

1. The compatible example shows near-coincident frozen-P0 prediction and observed q95 support.
2. Above/below examples show coherent relative boundary offsets while retaining high overlap; their states are image-domain response-support relations, not target velocity.
3. The deformation example has high overlap but mismatched left/right boundary behavior, validating a non-rigid state rather than centroid subtraction.
4. The censored example touches the SAR observable fan boundary, so a directional residual must remain censored.

## Cross-modal observations

The paired possible-rescue/deceptive examples come from one GT-blind development window and share the same optical residual.  Both a concordant and a contradictory SAR hypothesis have high support overlap.  This demonstrates candidate-level structural differentiation but does not identify the correct hypothesis and does not establish rescue.

## Grounding observations

The reviewed optical fragments are visually continuous over the displayed adjacent frames.  The SAR q95 regions and offline target markers remain many-to-many or otherwise lack an authoritative cross-modal identity cue.  Visual review therefore does not upgrade the existing frame-level geometric assignment to `CONFIRMED`; grounding remains offline-only `LIKELY` or `UNRESOLVED` and is prohibited from common-motion estimation, residual calculation, hypothesis selection, or final inference.
