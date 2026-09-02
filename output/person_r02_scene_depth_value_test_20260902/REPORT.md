# R02 PERSON scene-depth boundary value test

## Direct answer

If the near/far boundaries are correct and fully cover the frozen optical corridor, they reduce median R02 PERSON Q95 support from **13 to 10 regions/families** and from **2667 to 2160 px** (3.051 to 2.471 m2 proxy), a **12.5% median area contraction** across 13 fully covered shell rows. P90/max family burden remains 11/11; singleton and <=2-family fractions are both 0%.

The final decision is **INSUFFICIENT_PERSON_OVERLAP**. Only 1 uncontaminated reference row overlaps the selected cases, and **0 uncontaminated reference rows** satisfy the pre-frozen full-boundary-theta application rule. Contraction is measured, but reference retention and `FALSE_SCENE_LAYER_PRUNE` risk are not scientifically estimable.

## Frozen denominator

- Trusted boundary frames: 31; causal shell rows: 27; unique optical visual cases: 24.
- Optical visual layers: 23 `L2`, 1 `UNCERTAIN`, no observed `L0/L1` cases.
- Exact two-boundary application: 13/27; 14 rows fall back because both curves do not fully cover the optical corridor.
- Pre-reference root SHA256: `9d7a1f5c8197e3964730bacd74756febf5383de1d754ae80464de5e626872622`.

## Candidate contraction

| Condition | Applied rows | Median region/family | Median area px | Median area reduction | P75 / P90 reduction |
|---|---:|---:|---:|---:|---:|
| One-curb halfspace | 19 | 7->7 | 2435->1949 | 8.5% | 20.3% / 22.1% |
| Two-boundary L2 layer | 13 | 13->10 | 2667->2160 | 12.5% | 22.5% / 22.6% |

On the 8 rows where both radial conditions are available, family burden is **13.0->10.5->10.5** and median area is **2688->2112->2062 px** for angle-only, one-curb, and two-boundary. Two boundaries change family count relative to one curb on **0/8 rows** and add only **2.2% median** incremental area contraction (maximum 3.5%). The far halfspace therefore captures nearly all observed L2 discrimination.

## Reference safety and range strata

- Two matched references exist; F472/PERSON017 is the previously exposed operator-contaminated case.
- The single clean reference is L2 at 13.885 m, but the two-boundary condition is fallback, not applied.
- Fallback-aware 100% retention is not safety evidence. Applied clean retention denominator is zero, so the false-prune rate is unavailable.
- Layer/range summary: L2/12_TO_14M: 1. There are no 6-8 m rows and no L0/L1 contrast, so radial-stratum correspondence cannot be tested.

## Strongest cases and failures

- Strongest contraction: SAR F430, optical F258, `R02ZF_REUSED_R02ZF_PERSON100017`: family 13->11, area 2620->1986 px (24.2%).
- Strongest residual clutter: SAR F108, optical F64, `R02ZF_REUSED_R02ZF_PERSON100002`: 11 families and 2460 px remain in the valid L2 layer.
- Representation warning: SAR F406 reduces families 10->8 but removes only 6.1% of Q95 area.
- F472 is the key availability counterexample: the PERSON layer is visually clear, but the optical corridor exceeds the trusted boundary-theta span, so the rule withdraws instead of extrapolating.

## Decision and only next step

Decision: **INSUFFICIENT_PERSON_OVERLAP**. The measured contraction is modest, leaves about ten families, and provides no family-level gain over one curb on the common denominator. With zero uncontaminated applied reference rows, this run does not justify repairing F66 or engineering full-stream curve propagation.

The only next step is a **small reference-blind overlap collection**: select a few already trusted, full-theta boundary frames containing PERSON hypotheses in at least L1 and L2; freeze optical layers and supports; then evaluate retention. Do not repair F66, expand coverage, recalibrate azimuth, use R04, or enter final localization first.

## Scope and non-claims

This is `VISUAL_DEVELOPMENT_ONLY` and `VALUE IF CORRECT`. Optical supplies angle and scene-layer support; SAR Q95 remains candidate authority. No identity, center, box, intrinsic RCS, physical motion, tracker, weighted fusion, learned depth, R04, or final localization is claimed.
