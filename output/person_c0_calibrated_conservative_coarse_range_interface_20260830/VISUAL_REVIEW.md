# PERSON-C0 visual review

## Separation of verdict types

- Computed verdict: only machine-checkable geometry/input availability and exact Q95 pixel-intersection facts.
- Visual verdict: a human image review of whether the ground-contact interface is exposed, partial, censored, ambiguous, or unavailable.
- Neither verdict assigns a PERSON identity, SAR center, or final box.

## Optical footpoint cases

| case | frame | visual state | computed verdict | visual verdict |
| --- | --- | --- | --- | --- |
| FP_CANDIDATE_01 | R01ZF F10 | FOOTPOINT_OBSERVABLE | BBOX_BOTTOM_NOT_ACCEPTED_AS_EXACT_FOOTPOINT | Shoes and local ground contact are visually exposed; a bounded pixel interval could be annotated, but bbox bottom is not accepted as exact. |
| FP_CANDIDATE_02 | R02ZF F293 | FOOTPOINT_PARTIAL | BBOX_BOTTOM_NOT_ACCEPTED_AS_EXACT_FOOTPOINT | Lower body is visible but the nearby second PERSON and crop context make the contact interval a partial observation rather than an exact point. |
| FP_CANDIDATE_03 | R02ZF F158 | FOOTPOINT_CENSORED | BBOX_BOTTOM_NOT_ACCEPTED_AS_EXACT_FOOTPOINT | Far-small PERSON lower body is hidden by the parked vehicle; bbox bottom terminates on the occluder, not the ground contact. |
| FP_CANDIDATE_04 | R03ZF F259 | FOOTPOINT_AMBIGUOUS | BBOX_BOTTOM_NOT_ACCEPTED_AS_EXACT_FOOTPOINT | Small doorway/boundary-scale target: the exact ground-contact pixels cannot be distinguished reliably from local structure. |
| FP_CANDIDATE_05 | R03ZF F257 | FOOTPOINT_CENSORED | BBOX_BOTTOM_NOT_ACCEPTED_AS_EXACT_FOOTPOINT | The observation enters through the image boundary and does not expose a complete lower-body/ground-contact interface. |
| FP_CANDIDATE_06 | R01ZF F275 | FOOTPOINT_UNAVAILABLE | BBOX_BOTTOM_NOT_ACCEPTED_AS_EXACT_FOOTPOINT | Only a boundary fragment is detected; no defensible PERSON footpoint interval is present. |

## SAR angle-only fallback

- Actual case: `R02ZF` SAR frame `421`, hypothesis `R02ZF_REUSED_R02ZF_PERSON100014`.
- Computed angle-only candidate count: `18` Q95 regions by exact frozen pixel intersection.
- Runtime range state: `RANGE_UNAVAILABLE`.
- Correct fallback result: angle-plus-runtime-range is identical to angle-only (`18 -> 18`).
- Visual verdict: the two panels are intentionally identical; no annulus or contraction was invented.

## Strongest failure case

R02ZF optical F158 is a far-small observation whose lower body is hidden by a parked vehicle. The detector-box bottom lands on the occluder rather than the ground contact. Even if calibration were supplied, this row should remain `FOOTPOINT_CENSORED` and normally produce `RANGE_UNAVAILABLE` unless another independent physical observation interface is added.
