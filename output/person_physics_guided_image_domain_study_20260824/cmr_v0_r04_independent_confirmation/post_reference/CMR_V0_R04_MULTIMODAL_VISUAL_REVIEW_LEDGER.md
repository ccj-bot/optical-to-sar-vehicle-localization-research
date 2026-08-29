# CMR-v0 R04 multimodal visual review ledger

- Review date: `2026-08-29`.
- Review scope: the frozen 16-slot registry, the full contact sheet, and the full-resolution unique positive and harmful pair renders.
- Mechanism status during review: frozen; no CMR-v0, P0, q95, timing, uncertainty, residual-state, topology, threshold, or case-selection change was made.
- Image semantics: optical boxes are raw-fragment observations; cyan is source q95, magenta is frozen P0-predicted support, green is observed destination q95. Manual reference is used only for post-reference evaluation.

## Aggregate-to-visual agreement

### R04 F157 -> F158: visually supported primary, residual contribution non-decisive

The reference-supported primary destination `R0003` preserves the distinctive two-lobed response and is almost fully covered by the frozen predicted support (`soft IoU=0.906`, source retention `0.950`, destination explained `0.952`). The reviewed wrong alternatives `R0020` and `R0021` are spatially separate from the predicted support and have zero overlap/retention/explained fraction. Human review therefore agrees that the primary SAR explanation is substantially more plausible than these controls.

However, this visual distinction is already expressed by `SCENE_COMMON_PRIMARY_PREFERRED`. The optical residual is strictly `COMMON_COMPATIBLE`, both strict cross-modal relations remain unresolved/structurally indeterminate, and only the natural continuous sign creates the two `TENDENCY_SEPARATION` rows. The four reported `CONFIRMATION` rows must therefore not be read as four independent branch-residual confirmations.

Review labels:

- `AGGREGATE_PRIMARY_EXPLANATION_VISUALLY_SUPPORTED`
- `AGGREGATE_POSITIVE_VISUALLY_AMBIGUOUS` for attribution specifically to branch residual, because the common component already selects the primary and the four rows come from one window/target/temporal cluster.
- `STRICT_UNRESOLVED_WITH_MEANINGFUL_TENDENCY` for controls `R0020` and `R0021`.

Registry slots `03`, `07`, `08`, `10`, and `13` are repeated semantic views of this same evaluated pair family, not independent visual observations. The deformation label is credible: the supported q95 response is non-rigid/two-lobed, yet it remains a valid observed response rather than an invalid sample.

### R04 F162 -> F163: visually plausible primary but residual reverses

The reference-supported primary destination `R0005` remains a large two-lobed response continuous with source `R0007`; the frozen prediction overlaps it strongly (`soft IoU=0.786`, source retention `0.857`, destination explained `0.904`). The reviewed control `R0048` is a small isolated response immediately to the right with zero overlap, retention, and explained fraction. Human review therefore favors the primary SAR explanation and agrees with `SCENE_COMMON_PRIMARY_PREFERRED`.

CMR branch-relative tendency nevertheless labels the primary as opposing (`optical residual +0.269 deg`, primary SAR residual `-0.296 deg`) and the tiny control as supportive (`+4.814 deg`), producing `REVERSED_SEPARATION / HARM`. This is a real method-reality discrepancy: a sign-consistent angular residual favors a visually and geometrically weak isolated structure over the continuous reference-supported response.

Review labels:

- `HUMAN_OBSERVABLE_METHOD_UNRESOLVED`
- `METHOD_REALITY_DISCREPANCY`
- `VISUAL_PRIMARY_PLAUSIBLE_CMR_RESIDUAL_HARM`

Likely causes are representation and observation effects rather than a reason to modify R04: q95 deformation changes angular boundaries and midpoint, a small isolated region can obtain a clean residual sign despite zero common-support overlap, optical-to-SAR projection is not a calibrated motion equivalence, timing uncertainty is wide, and the raw optical fragment is only offline likely-grounded. Registry slots `04`, `12`, and `16` are repeated views of this same harmful pair family.

## Category accounting

Observed registry slots: `8/16`; category-not-observed slots: `8/16`.

Not observed under the frozen R04 evaluation were: SAR-only ambiguous with CMR separation, scene-common wrong rescued by CMR, concordant or contradictory high-overlap wrong alternatives, boundary-censored evaluated pair, optical-strong/SAR-weak evaluated pair, unresolved-grounding evaluated pair, and a strict/asymmetric best-separation case. Their absence is retained as `CATEGORY_NOT_OBSERVED`; no substitute case was manufactured.

## Visual conclusion

The images support real SAR scene-common continuity in both evaluated windows. They do not support treating branch residual as a decisive selector: it adds two tendency-only distinctions in F157 -> F158, gives no distinction in two comparisons, and reverses against the visually plausible primary in F162 -> F163. The direct visual review therefore agrees with retaining CMR only as non-decisive dynamic evidence and with redesigning the branch residual, if pursued, only on development data that are independent of R04.

No claim is made about intrinsic PERSON RCS, physical PERSON motion, calibrated synchronization, runtime identity, range, final center, or final box.
