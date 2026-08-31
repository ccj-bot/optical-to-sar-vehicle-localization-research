# PERSON-R02-S0 R02 static radial-azimuth scene skeleton

## Direct answer

**4.9 m 和 7.1 m 更像同一人行道/路缘带的两条平行物理边，但证据只支持“稳定片段中的成对场景骨架”，不能把两条线唯一命名为具体前/后缘；树在 F120/F200 单帧上确有很像的 SAR 亮点，却没有通过完整多帧轨迹竞争，因此暂时不能作为已确认方位静态锚。**

## Radial skeleton verdict

- Verdict: `PARALLEL_BOUNDARY_PAIR_SUPPORTED_IN_STABLE_SUBSEGMENTS_PHYSICAL_STRIP_IDENTITY_PLAUSIBLE_NOT_UNIQUE`.
- Neutral identities remain `STATIC_BOUNDARY_A/B/C`; response strength, persistence, and physical identity are not equated.
- A/B pair is jointly available on `122/495 = 24.6%` frames under the strict curved-ridge coherence gate.
- Across available pair frames, median separation is `2.500 m`; temporal P90 absolute variation is `0.250 m`; median within-frame theta P90 absolute variation is `0.542 m`.
- Longest strict stable segment: SAR F330-F335; median separation `2.512 m`, temporal P90 absolute variation `0.100 m`.
- A full-sequence center `4.85 m` (availability `71.3%`), B `7.30 m` (`34.9%`), C `12.40 m` (`59.8%`).
- P0 common-translation compensation leaves A/B separation invariant by construction. Individual adjacent-frame compensated median absolute residuals are A `0.011 m`, B `0.053 m`, C `0.044 m`. P0 remains SAR image-domain common apparent translation, not recovered platform motion.

## Physical interpretation

- The optical sequence visibly contains a road-side curb/front edge and a farther sidewalk/planting edge. The measured A/B separation and ordering are compatible with one physical strip, so the former `primary/alternate` competition interpretation is rejected for this scene-skeleton analysis.
- Exact edge naming remains set-valued: A/B may correspond to `ROAD-SIDE CURB FRONT EDGE` and `SIDEWALK REAR / PLANTING EDGE`, but this ordering is not promoted to calibrated cross-modal identity.
- C at about `12.40 m` is not well described as pure random clutter. It is a third persistent parking/planting/building-side response layer, likely composite and sometimes vehicle-contaminated: `THIRD_PERSISTENT_SCENE_LAYER_IDENTITY_COMPOSITE`.
- At the exact core time OPT F120 / SAR F200, A and C satisfy the strict single-boundary gate, while B has strong response but excessive theta-shape variation; the core case is illustrative, not the strictest pair segment.

## Tree / static azimuth anchor verdict

- Three visually distinct strapped roadside trees were followed using manual visual knots plus yellow-strap image support. Optical availability: TREE_A 61/66 frames, TREE_B 70/81, TREE_C 67/81.
- Confirmed SAR static anchors: `0`. Final mapping verdict: `STATIC_ANCHORS_INSUFFICIENT_TO_JUDGE`.
- Best user-tree range competitor is `14.50 m`: persistence `75/108 = 69.4%`, median absolute theta residual `1.63 deg`, P90 `3.71 deg`. It fails the temporal trajectory gate.
- Strongest false single-frame correspondence is the user tree's `18.75 m` competitor: at SAR F200 its theta residual is only about `+0.14 deg`, but across the sequence persistence is `50.9%`, median absolute residual `1.76 deg`, and P90 `4.51 deg`. It disappears/reappears and does not maintain one compact response trajectory.
- Rank-1 signed median residuals for the three visual tree candidates are close to zero (`+0.30`, `+0.14`, `-0.20 deg`) but have broad, discontinuous spreads. This is exactly why no stable offset or slope correction is inferred.
- `CURRENT_AZIMUTH_MAPPING = STATIC_ANCHORS_INSUFFICIENT_TO_JUDGE`; no mapping rewrite and no leave-one-anchor-out calibration claim are authorized.

## Core figure and evidence

- Main overview: `figures/R02_STATIC_SCENE_SKELETON_OVERVIEW.png`.
- Exact timestamp core case uses `OPT F120 t006667ms` and `SAR F200 t006667ms`; SAR F95 is not used as synchronized evidence.
- Continuous review sheets cover optical F80-F200 and SAR F133-F333. The review pack also contains raw optical F110-F135, raw SAR F183-F225, and the strict stable segment.
- The earlier 7-11-frame template landmark experiment and coordinate-grid development diagnostics are excluded from the final evidence chain and review pack; the tree conclusion comes from the longer yellow-strap sequence plus matched SAR-point competition.

## Independent validation

- Machine-readable results: `VALIDATION_RESULTS.csv` and `VALIDATION_SUMMARY.json`.
- The validator independently recomputes the exact F120/F200 timestamp match, complete 495-frame denominators, A/B stable segment, tree counts, zero confirmed anchors, non-claims, and review-pack integrity.

## Decision for future PERSON work

`SCENE_SKELETON_WORTH_RETAINING_AS_CONSERVATIVE_CONTEXT_NOT_YET_PERSON_MECHANISM`.

The radial A/B/C ordering is useful scene context and the A/B pair is physically plausible. However, tree-point identity and the current angular mapping are not confirmed strongly enough to use the scene skeleton for PERSON pruning or grounding yet. A next study should manually label one compact SAR point through an uninterrupted tree passage, or use a designed static reflector/known pole, before revisiting PERSON.

## Non-claims

No PERSON reference, PERSON discrimination, PERSON range, final localization, final center/box, R04, P2, learned model, new tracker, full camera calibration, intrinsic RCS, physical platform-motion recovery, or mapping rewrite is used or claimed. All optical semantics are visual-development only, and all SAR point identities remain set-valued unless explicitly rejected by temporal competition.
