# R02 local boundary observability log

## Pre-run

- Active repository: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Starting `HEAD == origin/main == ef61a07cf4f3515b83beab3c4fb54b73a9bb1643`, ahead/behind `0/0`.
- Existing dirty baseline contains 342 entries and remains out of scope.
- Manual JSONL sources are read-only. Current hashes are `5EA5882BD764524E5FD61C1D72C7594AAA9BBF9ABFCD5A1BD9FE992BDE278FC9`, `2650F9EC2CBE3709475144B6905DD7E9E83D18DDAB4D3876098A4877556F2F1E`, and `00C795D6F1997324AA087537EF19A9AC9566400A2CC36FF24C40D9ED63C84FEB`.
- Primary independent seeds are F062, F150, F183, F264, and F454. All other manual geometry is hidden from each propagation process.
- Frozen source SHA-256 is `E80BD4AE8FF808C290340A1452C35F3FE72099051B7742178AD85EA902A90967`; thresholds are not tuned.
- Representation audit: the existing propagator retains a sampled full curve, but each frame update is a rigid whole-curve scalar `d_perp` shift. Curve nodes do not independently adapt. Near/far proposals are separate, but the original path stops the pair when any boundary or pair corridor fails.
- Outputs go only to `output/r02_local_boundary_observability_20260902`.
- R04, PERSON, tree anchors, azimuth recalibration, final localization, and `old_work` are excluded.

## Post-run

- Five independent seeds completed forward/backward propagation with unchanged frozen thresholds. Pre-reference freeze contains 38 files; manifest SHA-256 is `351D791EFE4734E1B315486E16A842B7A1D48067EB0AFB0745D3FB580B2A9AD2`.
- Pair-safe directional segments are F59-F62, F62-F66, F66-F150, F150-F164, F166-F183, F183-F259, F166-F264, F264-F269, F406-F454, and F454-F481.
- Their union labels 286/495 frames pair-safe (57.78%) and 209/495 frames unknown (42.22%). This remains an algorithm-reported fraction, not a validated safe fraction.
- Boundary-independent diagnostics report near support on 307 frames, far support on 286 frames, 21 partial frames, and 188 diagnostic-unknown frames. Partial geometry is not accepted as pair-safe context.
- Post-freeze checkpoint audit passed 3/6 crossings at the frozen 0.12 m gate. The three numerical failures look like same-ridge offsets; no checkpoint-confirmed semantic ridge switch or near/far reversal was found.
- Natural overlap failed 3/3 consistency audits. At F66, F62-forward retains a curved entrance state while F150-backward imports a rigid near-horizontal state; both are marked supported. This is recorded as one confirmed `FALSE_SUPPORT_CURVE_STATE`.
- F67 is the strongest premature-stop candidate because a human-visible trace remains after the near weak-response stop. F260 is a defensible safe ridge-jump stop. F405/F482 are P0 input-availability stops.
- Final verdict: sparse anchors initialize useful local propagation, but current rigid curve state does not yet fully achieve “follow when observable, stop when not.” Curved entry is a primary representation failure mode.
- Optional scene context is not yet qualified to constrain PERSON. Interim use is limited to read-only diagnostics near manual anchors/stable intervals, with complete withdrawal at `UNKNOWN`.
- Final artifacts: `output/r02_local_boundary_observability_20260902/FINAL_SUMMARY.json`, `REPORT.md`, `post_freeze_audit/MANUAL_VISUAL_VERDICTS.csv`, figures, and `VALIDATION_REPORT.json`.
- Validation passed 158 checks before review-pack creation. The review ZIP is generated at `output/r02_local_boundary_observability_20260902/R02_LOCAL_BOUNDARY_OBSERVABILITY_REVIEW_PACK_20260902.zip` and is intentionally not committed.
- No manual JSONL was modified or copied verbatim. R04, PERSON, tree anchors, azimuth recalibration, final localization, and `old_work` remained out of scope.
