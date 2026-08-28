# M0B1-V2 visual QA and closeout

- QA date: 2026-08-28
- QA scope: generated contact sheet, supported concordant case, matched-null
  contradictory case, and first GT-blind opposite-direction atlas window
- Automated final validation before visual review: `171/171 PASS`

## Direct observations

1. `01_supported_optical_positive_sar_positive.png` is visually consistent
   with the categorical `DIRECTION_CONCORDANT` label.  The optical raw fragment
   shifts coherently in the positive mapped direction and the q95 SAR region
   shifts positive.  However, the SAR region contains two manual reference
   centers (03 and 04), so the image directly reinforces the shared/unresolved
   boundary and does not support optical-SAR identity.
2. `05_matched_null_contradictory.png` is visually consistent with a useful
   scene-conditioned contradiction.  The optical branch remains positive while
   the alternative SAR support moves in the opposite angular direction; the
   destination alternative region is visibly separated from the manual centers
   associated with the supported primary edge.  This is a valid explanatory
   case for why direction can confirm the supported SAR explanation.
3. The contact sheet preserves fragment-break, same-sample, deformation, and
   static-feasible contradiction cases instead of hiding them.  Categories not
   present in the data remain absent rather than being substituted.
4. `17_broader_atlas_opposite_direction_branches.png` shows a real GT-blind
   R06ZF F98->F99 window with two distinct raw fragments moving in opposite
   mapped directions.  This visually supports the atlas conclusion that R02's
   all-positive sign is a slice-specific degeneracy, not a property of the
   representation across all exposed runs.

## Aggregate versus image consistency

- No observed image contradicts the primary aggregate state
  `M0B1_V2_DIRECTION_SIGNAL_SCENE_COMMON_NOT_BRANCH_SPECIFIC`.
- The strongest positive images are shared/unresolved at the PERSON level.
- The contradictory-null image supports scene-level SAR hypothesis screening,
  but it does not distinguish correct from wrong optical branches.
- The atlas image supports the recommended next step: freeze a common apparent
  motion versus branch-relative residual protocol on all eligible windows,
  before any magnitude model or pruning rule.

## Stop boundary

No timing fit, magnitude fit, residual-motion model, pruning, tracker,
assignment, factor graph, P2, final center, or final box was executed.

