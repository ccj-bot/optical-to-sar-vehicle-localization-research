# R02 manual-boundary multi-bracket selection report

## Decision boundary

This is an image-led annotation preparation only. No propagation result, PERSON evidence, tree anchor, automatic range hint, or R04 material was used to select the brackets.
The boundary coordinate remains an image/scene-relative `d_perp` proxy and is not called PERSON radial range or physical calibration.
Frozen comparator F150-F183 is excluded and remains unchanged.

## Selected brackets

| Bracket | Inclusive SAR span | Frames | Manual endpoints | Visual selection reason |
|---|---:|---:|---|---|
| A_EARLY | F047-F082 | 36 | F047 START; F082 END | EARLY_IMAGE_LED_REPLICATION_WITH_VISIBLE_BOUNDARIES_AND_GRADUAL_CENTRAL_CLUTTER_CHANGE |
| B_MID_LATER | F239-F278 | 40 | F239 START; F278 END | MID_LATER_IMAGE_LED_REPLICATION_ACROSS_RIDGE_INTENSITY_AND_LOWER_ARC_CLUTTER_VARIATION |
| C_LATE | F427-F472 | 46 | F427 START; F472 END | LATE_IMAGE_LED_REPLICATION_INCLUDING_STRONG_TO_WEAK_TO_RECOVERED_RESPONSE_CONDITIONS |

## Visual review performed

- Reviewed the complete F0-F494 stream at 5-frame spacing with no overlays.
- Reviewed every frame in F45-F90, F235-F285, and F425-F475.
- For each final bracket, checked START, approximately 25%, 50%, 75%, END, and visible weakening/clutter transitions.
- Review strips contain 10 process frames each and show no algorithmic proposal or propagation result.

## User task

For each of the six keyframes, draw only `SAR_BOUNDARY_NEAR` and `SAR_BOUNDARY_FAR`, then save/advance. If either boundary is not visually supportable, use the unresolved/not-visible control rather than guessing.

## Explicit non-claims

The selected brackets are candidates for later independent bidirectional replication. Selection does not establish propagation, closure, physical boundary calibration, PERSON range, PERSON identity, or final localization.
