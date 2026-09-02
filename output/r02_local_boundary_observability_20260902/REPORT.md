# R02 local observability and safe boundary propagation

## Direct answer

The sparse manual-anchor plus local-propagation design is useful, but it does **not yet fully implement** “follow when observable, stop when not observable.” Stable intervals and the short entrance interval are usable; however, F66 contains one confirmed `SUPPORTED` curve-state error. The error is caused by a rigid curve representation, not by a demand for complete temporal closure.

## Scientific setup

- Eleven manual semantic checkpoints were recovered at F47, F62, F82, F150, F183, F239, F264, F278, F427, F454, and F472, comprising 22 near/far boundary records.
- F62, F150, F183, F264, and F454 were used as independent primary seeds.
- Each propagation process read only one isolated seed containing two boundaries from one frame. Other checkpoint geometry remained hidden until all pre-reference results were frozen and hashed.
- The frozen source and thresholds were reused without tuning. `DRAFT` was treated as a UI-finalization omission because the user confirmed the geometry semantics.

## What the propagator actually represents

The manual polyline is sampled into `d_perp(theta)` nodes, but every frame update applies one scalar displacement to the entire curve. Nodes provide evidence samples; they are not independently updated. Therefore the centered curve shape is invariant within a path. Near and far evidence is calculated separately, while the pair-safe comparator stops both if either boundary or the pair corridor becomes unsafe.

This matters because a stable center is not proof of a correct full curve. The current state cannot naturally represent the real entrance evolution from curved boundaries toward straighter parallel boundaries.

## Algorithm-reported local support

The ten independent directional pair-safe segments are:

| Seed | Backward | Forward |
|---|---:|---:|
| F62 | F59-F62 | F62-F66 |
| F150 | F66-F150 | F150-F164 |
| F183 | F166-F183 | F183-F259 |
| F264 | F166-F264 | F264-F269 |
| F454 | F406-F454 | F454-F481 |

Their union forms three components: F59-F164, F166-F269, and F406-F481. The algorithm labels 286/495 frames pair-safe (`57.78%`) and 209/495 frames unknown (`42.22%`). This is an algorithm-reported coverage figure, **not** a scientifically validated safe fraction.

The independent-boundary diagnostic finds near support on 307 frames, far support on 286 frames, and 21 partial frames where near continues after far becomes unknown. These 21 frames are diagnostic only and are not accepted as pair-safe context.

Directional segment lengths are 4, 5, 85, 15, 18, 77, 99, 6, 49, and 28 frames (median 23, mean 38.6). Pair-safe stop causes include weak response in seven directions, fragmented support in two, one ridge-jump stop, and four P0-unavailable boundary events.

## Post-freeze checkpoint and overlap audit

Six paths naturally crossed another manual checkpoint. Three passed the frozen 0.12 m comparison (F82 from F150-backward, F239 from F183-forward, and F472 from F454-forward); three failed numerically. The failures at F183/F239 from F264-backward and F427 from F454-backward look like systematic offsets on the same apparent response, not confirmed switches to another ridge.

No strict semantic ridge switch or near/far reversal was confirmed at the manual checkpoints. That does not make the full state safe: all three natural overlap audits failed the frozen consistency test.

## Strongest false support: F66

At F66, F62-forward preserves the curved entrance shape while F150-backward transports a nearly horizontal stable-segment shape backward. Both paths are labeled pair-safe `SUPPORTED`, yet their maximum node disagreement is 0.4171 m and shape RMS disagreement is 0.1828 m. The two full boundary states cannot both be correct.

This is recorded as `FALSE_SUPPORT_CURVE_STATE`. It is more serious than early `UNKNOWN`, even though the image does not prove that either path jumped to a different physical ridge. It proves that the observability rule does not currently protect the full curve state.

## Strongest possible false unknown: F67

F62-forward stops before F67 because near response is too weak. A human-visible trace remains in the raw image, so this is the strongest premature-stop candidate. The conservative stop is nevertheless safer than forcing continuation, and its severity is lower than the F66 false support.

F260 similarly retains visible structure, but the far proposal exceeds the frozen corridor; treating it as unknown is a defensible safe stop. F405 and F482 stop because P0 is unavailable and therefore express input availability, not image ambiguity.

## Final judgments

1. Sparse manual near/far semantic anchors are sufficient to initialize useful local propagation: **yes**.
2. The system stops on weak evidence instead of always forcing continuity: **partly established**, but not sufficient because F66 shows a supported wrong curve state.
3. The curved-to-straight entrance is a **primary failure mode of the rigid representation**.
4. The interface is **not yet qualified to constrain PERSON**, even as optional context. It may only be used as an experimental read-only diagnostic near manual anchors or in stable intervals, and `UNKNOWN` must mean complete withdrawal of the scene-geometry constraint.

## Structural next step, not implemented here

Keep the frozen rigid method as a comparator. A future version needs a constrained shape-adaptive state (for example, low-dimensional or regularized node-wise deformation) and an explicit shape-observability gate. Near/far observability should remain separate, pair context should require both plus safe corridor geometry, and no method should bridge unknown gaps or tune thresholds to checkpoints.

## Scope and non-claims

No PERSON, tree-anchor, azimuth-recalibration, final-localization, R04, or `old_work` work was run. The manual JSONL files remained read-only. Full-stream boundary recovery and a scientifically validated safe-frame fraction are not claimed.
