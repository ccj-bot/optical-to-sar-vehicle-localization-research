# M0B1 visual QA and closeout

- Visual inspection date: 2026-08-28
- No-manual-overlay figures inspected: 12/12
- Post-reference-overlay figures inspected: 12/12
- Independent post-reference validation: `PASS (15/15)`
- Primary result: `M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT`

All figures are readable. The no-manual-overlay set contains no magenta manual
reference points. The post-reference set adds magenta points only where a
frozen supported SAR edge can be mapped for evaluation; it does not identify a
correct raw optical fragment. Green q95 region contours, cyan guarded static
shells, and yellow guard-free optical intervals are visible. Requested
concordant, contradictory, or best-incremental categories that do not exist are
explicitly labeled deterministic fallback.

No figure draws a tracker path, identity assignment, pruning result, unique
trajectory, SAR box, or final localization. The paired visual evidence is
consistent with the aggregate result: every dynamically available optical
direction interval remains indeterminate, so no incremental angular-direction
signal is established and M0B2 is not recommended.

## Integrity anchors

- Protocol SHA256:
  `702277348913B3E7CBA6A4CEBF56ACA08807021F91C2E202236EDD3573973278`
- Amendment 01 SHA256:
  `211FCCC188B88BB9D7083532AEA03E30532DDADEAE57F6E89AC1238CC0FEC138`
- Amended runner SHA256:
  `71DD0B223A5C906FC45118339EE0B2FA3B3BF76F8D55D4DD5DB5DDDF42F91ADB`
- Validator SHA256:
  `79D7EE38D3E7C1662FC6D72299A8249A5BE952649D0EFB43F51216BD901A1674`
- Pre-reference manifest SHA256:
  `D7779EB65A6CB267C29D873097E3DD71E7BE56ADD10638B8DC88689DFE54AC89`
- Pre-reference validation SHA256:
  `2B3806472AF0C39635CA39CEA1BE582B1EE720F75A941BB31352EB811876ACDD`
- Final output manifest SHA256:
  `AA085B43A682FBEDEB7080D596C8C5AB98FD1D42AD61F5CE580740E3C22CF76E`
- Independent validation SHA256:
  `729103C7F59D65FE84CF634E636ADB81B4E954054DBA9E620617CB6625F12F94`
