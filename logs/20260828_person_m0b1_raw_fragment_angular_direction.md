# 2026-08-28 PERSON M0B1 raw-fragment angular-direction diagnostic

## Preflight

- Workspace: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Starting branch: `main`
- Starting HEAD: `69d7b5c97f391a37f8f986c66739dc982f4a1fb5`
- Starting `HEAD...origin/main`: `0/0`
- Existing unrelated dirty worktree: present and preserved
- `old_work` read or used: `NO`

## Frozen scope

- Stage: `M0B1_R02_RAW_FRAGMENT_ANGULAR_DIRECTION_DIAGNOSTIC`
- R02 F472-F494, 22 adjacent lag1 SAR pairs
- Raw optical fragments only
- Guard-free optical intervals for dynamics
- Frozen q95 region-support intervals for SAR dynamics
- Current ±6 degree pixel-level shell topology for static feasibility
- Five fixed timing conditions, no best-shift search
- Full pre-reference materialization before reference reveal
- Pareto role removed from pruning; no hypothesis deletion

## Prohibited and not authorized

- angular magnitude or monotonicity
- weighted score, classifier, learned fusion, likelihood ratio, factor graph
- tracker, Hungarian, identity assignment, unique path
- lag3/lag5
- timing calibration or registry write-back
- ambiguity-reduction claim
- SAR box or final localization

## Pre-run audit observation

The exact current optical query sequence reproduces the earlier interface
audit: nominal R02 contains 37 same-fragment distinct-sample instances and 29
same-sample instances before static SAR-region conditioning. Under the frozen
interval displacement definition, all 37 distinct-sample optical intervals
contain zero. This is an audit observation only; the formal result must come
from the frozen M0B1 hypothesis bank, controls, reference reveal, cases, and
independent validator.

## Run status

- Protocol written and awaiting freeze execution.
- Freeze-before-run implementation review completed:
  - destination q95 area stratum now uses the frozen destination node pixel count directly;
  - empty control outputs retain fixed schemas;
  - the static-shell case slot requires a reference-supported primary;
  - the independent validator checks frozen runner and validator hashes.
- Runner SHA256: `2E047D7379080C09201316EB637390E60590BC53A681D3B979109C86EEC8BEC3`
- Validator SHA256: `79D7EE38D3E7C1662FC6D72299A8249A5BE952649D0EFB43F51216BD901A1674`

## Frozen execution amendment 01

- Pre-reference materialization completed and independently passed `26/26`.
- The first post-reference run generated evaluation/statistical tables and the
  12-slot registry, then failed before rendering the first figure.
- Cause: `pandas.Series.to_frame` name collision at `case.to_frame`.
- Correction: use explicit `case["to_frame"]` column access at every conflicting
  render-time access.
- Scientific rules, frozen pre-reference outputs, controls, direction states,
  and case-selection rules are unchanged.
- The first amended rerun exposed the same name collision at the destination
  image-path access before any figure was written; amendment 01 was expanded to
  cover both render-time accesses.
- Amended runner SHA256:
  `71DD0B223A5C906FC45118339EE0B2FA3B3BF76F8D55D4DD5DB5DDDF42F91ADB`

## Formal run result

- Frozen protocol SHA256:
  `702277348913B3E7CBA6A4CEBF56ACA08807021F91C2E202236EDD3573973278`
- Pre-reference materialization:
  - query rows: 115;
  - static pixel relations: 2,557;
  - complete hypothesis records: 308,600;
  - hard feasible: 66,260;
  - dynamic available: 11,252;
  - same optical sample: 8,674;
  - raw fragment break: 46,334;
  - static infeasible: 242,340;
  - determinate optical interval direction: 0;
  - nominal topology parity: 521/521 exact keys.
- Pre-reference independent validation: `PASS (26/26)`.
- Post-reference result:
  - state: `M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT`;
  - secondary: `M0B1_RUNTIME_OPTICAL_TEMPORAL_SAMPLING_BLOCKED`;
  - secondary: `M0B1_POST_REFERENCE_RAW_FRAGMENT_EVALUATION_INTERFACE_NOT_ESTABLISHED`;
  - supported SAR base edges: 6 from 3 frame-pair clusters;
  - nominal supported records: 26;
  - nominal supported dynamic available: 10;
  - nominal supported determinate direction: 0;
  - nominal supported sampling-block fraction: 15/26 = 0.576923;
  - incremental angular signal observed: `NO`;
  - recommend M0B2: `NO`.
- Post-reference independent validation: `PASS (15/15)`.

## Visual QA

- Inspected all 12 no-manual-overlay and all 12 post-reference-overlay figures.
- All 24 figures are readable and show the intended green q95 region, cyan
  guarded static shell, yellow guard-free optical interval, and explicit case
  state text.
- No pre-reference figure contains magenta manual reference overlays.
- Post-reference magenta overlays appear only where the frozen SAR edge can be
  linked to a supported primary; no raw branch is selected or relabeled.
- Concordant/contradictory/best-incremental slots with no real category are
  explicitly marked deterministic fallback.
- No tracker path, assignment, pruning, unique trajectory, SAR box, or final
  localization is drawn.

## Stop

- M0B1 is complete.
- M0B2, magnitude, monotonicity, pruning, factor graph, P2, and final SAR
  localization were not started.

## Frozen baseline regression

- M0A pre-reference validator: `PASS (14/14)`.
- M0A post-reference validator: `PASS (12/12)`.
- M0A-R independent validator: `PASS (28/28)`.
- P0 output validator: `PASS (18/18)`.
- The P0 validator's timestamp-only rewrite was restored; no regression-only
  artifact is included in the M0B1 change set.
