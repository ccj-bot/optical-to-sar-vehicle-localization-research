# R02 boundary multi-bracket replication log

## Pre-run

- Active repository: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Starting `HEAD == origin/main == f1f9ee16835e0f59b04102058680d5282de6618e`, ahead/behind `0/0`.
- Existing dirty baseline remains out of scope.
- Manual input: `output/r02_boundary_multibracket_preparation_20260902/user_annotations/manual_static_scene_annotations.jsonl`.
- Manual input has 86 append-only events, SHA-256 `2650F9EC2CBE3709475144B6905DD7E9E83D18DDAB4D3876098A4877556F2F1E`.
- The user explicitly stated that annotation is complete and warned that the first early-garage sidewalk boundaries are curved.
- All six latest near polylines contain 5-6 points and are CONFIDENT but remain DRAFT because the interface step was changed without finalizing the near line. All six far polylines are CONFIDENT COMPLETE. The raw JSONL stays read-only; derived normalized seeds retain source status and event provenance.
- Frozen core constants are imported unchanged from the F150-F183 comparator implementation.
- Brackets: A F47-F82, B F239-F278, C F427-F472. Each is independently propagated in both directions.
- Outputs go only to `output/r02_boundary_multibracket_replication_20260902`.
- R04, PERSON, tree anchors, fixed range windows, final localization, and `old_work` are excluded.

## Post-run

- Reused the frozen F150-F183 implementation without modifying it; source SHA-256 is `E80BD4AE8FF808C290340A1452C35F3FE72099051B7742178AD85EA902A90967`. No corridor, jump, contrast, bridge, or pair-separation threshold was changed for A/B/C.
- Preserved all endpoint polylines as `d_perp(theta)`. At entrance frame F047, near span is about `1.105 m` with maximum linear-residual curvature about `0.261 m`; far span is about `2.075 m` with maximum linear-residual curvature about `0.660 m`. By F082 the spans are about `0.065 m` and `0.227 m`, respectively. The early curved geometry was not straightened.
- A_EARLY: forward F047-F051, stop before F052; backward F082-F074, stop before F073; uncovered F052-F073; proposed repair F062.
- B_MID_LATER: forward F239-F256, stop before F257; backward F278-F273, stop before F272; uncovered F257-F272; proposed repair F264.
- C_LATE: forward F427-F437, stop before F438; backward F472-F471, stop before F470; uncovered F438-F470; proposed repair F454.
- No new bracket has a natural bidirectional overlap. All three are therefore `BRACKET_NOT_CLOSED` with reason `NO_BIDIRECTIONAL_OVERLAP`. Overlap-only center/shape/order/support fields are standard-JSON `null` with availability `UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP`, not false failures. Directional near/far ordering is reported separately and remains positive at all propagated nodes.
- Initial manual-anchor density is `6/122 = 0.04918`. The minimal first repair batch contains one SAR-only frame per bracket: F062, F264, and F454. No automatic line/hint is displayed and `repair_user_annotations` remains empty.
- The raw 86-event manual JSONL remained byte-identical at SHA-256 `2650F9EC2CBE3709475144B6905DD7E9E83D18DDAB4D3876098A4877556F2F1E`. It is not included in this research commit.
- Independent replication validation passed `12/12`, including strict JSON, curve preservation, frozen-parameter parity, complete frame accounting, repair media, zero fabricated closed records, excluded-scope flags, figures, and an isolated SAR-only browser API/save/render QA. The browser preview rendered at `1600x1000`; its synthetic annotations were written only to a temporary directory.
- The original 18-pair annotation tool regression passed `22/22`; its real 20-event user JSONL was preserved. Generated regression files were returned to their pre-run tracked state.
- Visual inspection confirmed the repair UI opens directly at SAR F062 with only near/far steps, and the A process review visibly preserves the curved F047 entrance boundary before the unsupported gap and flatter F082 endpoint.
- R04, PERSON, tree correspondence, fixed absolute range windows, final localization, and `old_work` were not accessed or run.
