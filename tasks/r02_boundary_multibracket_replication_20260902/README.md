# R02 manual-boundary multi-bracket replication

This task executes the already authorized replication after the user completed six SAR endpoint annotations.

## Frozen propagation core

- Reuses constants and functions from `tasks/r02_manual_seed_temporal_propagation_20260902/run_manual_seed_temporal_propagation.py`.
- Adjacent-frame local ridge search.
- Frozen P0 common apparent translation.
- Independent START-forward and END-backward paths.
- Local ambiguity stop; no fixed absolute range window and no ridge switching.
- No parameter tuning against A/B/C outcomes.

## Curved-boundary handling

- Manual seeds remain `d_perp(theta)` curves, not center values or straight lines.
- Bracket A intentionally tests the transition from the strongly curved F047 seed to the much flatter F082 seed.
- Closure reports center disagreement, full-curve disagreement, translation-removed shape disagreement, near/far ordering, and response-support overlap.
- When no natural forward/backward overlap exists, those overlap-only gates are `null` with `UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP`; they are not recorded as failed comparisons. Directional near/far ordering remains a separate field.
- The original append-only manual JSONL remains unchanged. The user's explicit completion statement authorizes the latest point-rich near drafts as semantic seeds.

## Validation

Run `validate_multibracket_replication.py` after propagation. It checks strict JSON, manual-event integrity, curved F047 geometry, frozen parameters, complete frame accounting, minimal repair frames/media, empty real repair output, excluded scopes, review figures, and an isolated SAR-only browser save/render smoke test.

## Exclusions

No tree work, PERSON work, final localization, R04 access, or `old_work` dependency.
