# PERSON-CURB0 R02 parallel curb radial anchor pilot

## Direct answer

**可以，但结论严格限定在 R02ZF SAR F421-F474：用户指出的平行路缘场景确实提供了一条有用的 SAR 图像域径向边界；它能做保守的半空间剪枝，却不能单独给出唯一 PERSON grounding。** GT-blind 自动排序的主静态带位于 `d_parallel≈7.10 m`，在稳定窗的可用率为 `48/54 = 88.9%`。同时 `4.90 m` 近侧替代带必须保留为物理身份不确定性，`12.40 m` 是最强远侧平行混淆项。因此本轮结论是 `CURB_RADIAL_TOPOLOGY_ONLY_MODERATELY_USEFUL_IN_STABLE_SEGMENT`，不是全 R02、不是 exact optical-SAR point match，也不是 final PERSON range/box。

## Required answers

1. **SAR extraction:** primary boundary availability `48/54 (88.9%)` in F421-F474. Unavailable frames fall back to angle-only; no radial deletion is invented.
2. **Most stable temporal segment:** the longest uninterrupted available run is `R02ZF SAR F462-F474` inside the frozen primary window `F421-F474`. F375-F414 is a passing-vehicle/near-range-reflection control; F480-F488 is a display-intensity/multiple-arc control.
3. **Current frozen corridor curb width:** median `2.257 m`, P90 `2.779 m` on available shell rows.
4. **Angular sensitivity:** +/-6 deg median/P90 `1.579/2.385 m`; +/-4 deg `1.127/1.667 m`; +/-3 deg `0.905/1.316 m`; +/-2 deg `0.684/0.974 m`. On the very small post-reference denominator (`n=4`), every centered +/-6/4/3/2/1 diagnostic retains only 50% angular support, while the current frozen asymmetric corridor retains 100%; these narrower widths are therefore diagnostic only and are not supported as replacements for the current mapping.
5. **Optical topology:** visually stable for the reviewed stable-window PERSON hypotheses. The near roadside curb separates the foreground road/platform side from the farther sidewalk/planting/parking side. All labels remain `VISUAL_DEVELOPMENT_ONLY_NOT_RUNTIME_CLASSIFIER`; interpolated/small candidates retain lower confidence.
6. **Exact Q95 burden, current corridor, primary band:** median `N_region 8.0 -> 7.0`, `N_family 8.0 -> 7.0`, `A_candidate_px 2192.0 -> 1873.0`, `A_candidate_m2 2.507 -> 2.143`. The identity-conservative two-near-band result is weaker: median `N_family -> 8.0`.
7. **Strongest counterexample:** R02ZF F431. It retains the largest same-legal-side Q95 family burden after curb pruning. This demonstrates that walls/vehicles/other static responses beyond the curb remain legal clutter.
8. **Small manual input:** an optical curb polyline is not required for this half-space diagnostic because the side relation is visually clear. A reviewer should confirm 3-5 SAR keyframes in `SAR_CURB_IDENTITY_CONFIRMATION_TEMPLATE.csv` if the physical identity of the 7.10 m band versus the 4.90 m alternative must be promoted beyond this conditional pilot.
9. **Post-freeze reference retention:** current corridor angular `100.0%`, radial topology fallback-aware `100.0%`, 2D `100.0%`. Reference was opened only after freeze root `3febe4272067cb2bed4b403b8d8eeb09777c96d6c878c8dbc44eea0479b1b9ec`.
10. **One next step:** manually confirm which near SAR band is the physical roadside curb on 3-5 review frames (F421/F435/F450/F462/F474); then freeze that identity and rerun the same unchanged half-space evaluation. Do not build an automatic optical curb classifier yet.

## Candidate interpretation

- `~7.10 m`: highest persistence/coherence score; selected primary curb-compatible static boundary.
- `~4.90 m`: retained near-side alternate static boundary; drives the identity-conservative result.
- `~12.40 m`: far parallel static-clutter counterexample, visually consistent with parked-vehicle/planting/building-side structure rather than the near roadside curb.
- Band widths are derived from local half-height ridge support plus robust temporal center variability. No fixed +/-0.2 m or +/-0.5 m width is imposed.
- The ideal parallel-line relation is used only as a sanity representation: `d_parallel = r cos(theta)` and `r_curb(theta)=d_parallel/cos(theta)`.

## Range-layer audit

The frozen-window post-reference layer table is in `post_reference_evaluation_only/reference_range_layer_summary_post_reference.csv`. This selected stable window contains `4` reference rows in the 12-14 m layer and `0` in the 6-8 m layer. Therefore the curb-side retention result is supported only for the 12-14 m layer here; the requested 6-8 versus 12-14 comparison cannot be completed inside this restricted window and is not inferred from absent rows.

## Non-claims

This pilot does not claim intrinsic RCS, recovered physical platform/person motion, calibrated camera-radar geometry, exact cross-modal point correspondence, runtime optical curb classification, PERSON identity, tracker improvement, score fusion, final range, final center, or final box. `Omega` remains a PERSON-conditioned physical search support. Q95 and P0 family terms remain conditional SAR image-domain response structures. R04 was not accessed.
