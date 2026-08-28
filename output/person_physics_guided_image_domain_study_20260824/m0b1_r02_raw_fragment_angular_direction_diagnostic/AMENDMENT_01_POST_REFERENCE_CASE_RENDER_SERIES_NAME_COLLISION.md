# M0B1 frozen execution amendment 01

- Stage: `M0B1_R02_RAW_FRAGMENT_ANGULAR_DIRECTION_DIAGNOSTIC`
- Amendment scope: post-reference case rendering only
- Trigger: first post-reference execution after the frozen pre-reference bank and
  its independent 26/26 validation had completed
- Failed operation: converting the `to_frame` case field to `int`
- Exception: `TypeError: int() argument must be a string, a bytes-like object or
  a real number, not 'method'`

## Cause

`case` is a `pandas.Series`. Attribute access `case.to_frame` resolved to the
existing `Series.to_frame` method instead of the frozen `to_frame` column.

## Authorized execution-only correction

Replace every render-time attribute access to the conflicting field, including:

`frames[int(case.to_frame)]`

and:

`image_path(int(case.to_frame), ...)`

with explicit column access:

`frames[int(case["to_frame"])]`.

and:

`image_path(int(case["to_frame"]), ...)`.

No timing query, pixel relation, hypothesis, interval, direction state, control
mapping, reference label, case-selection rule, outcome threshold, or scientific
claim is changed. The frozen pre-reference manifest remains untouched and must
continue to validate exactly.

- Original frozen runner SHA256:
  `2E047D7379080C09201316EB637390E60590BC53A681D3B979109C86EEC8BEC3`
- Amended runner SHA256:
  `71DD0B223A5C906FC45118339EE0B2FA3B3BF76F8D55D4DD5DB5DDDF42F91ADB`
- Validator SHA256 remains:
  `79D7EE38D3E7C1662FC6D72299A8249A5BE952649D0EFB43F51216BD901A1674`

The post-reference phase must be rerun from the frozen pre-reference outputs,
then independently validated. No M0B2 work is authorized.
