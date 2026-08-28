# PERSON M0B1 raw-fragment angular-direction diagnostic

- Stage: `M0B1_R02_RAW_FRAGMENT_ANGULAR_DIRECTION_DIAGNOSTIC`
- Workspace: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Output: `output/person_physics_guided_image_domain_study_20260824/m0b1_r02_raw_fragment_angular_direction_diagnostic`
- `old_work` is not read and is not a runtime dependency.

This task executes only interval-based optical/SAR angular-direction evidence
on frozen R02 lag1 SAR edges and runtime-legal raw optical fragments. It does
not execute magnitude, monotonicity, pruning, tracking, assignment, timing
calibration, factor-graph inference, SAR boxes, or final localization.

Run order:

1. `run_m0b1_raw_fragment_angular_direction.py --phase freeze`
2. `run_m0b1_raw_fragment_angular_direction.py --phase pre-reference`
3. `validate_m0b1_raw_fragment_angular_direction.py --phase pre-reference`
4. `run_m0b1_raw_fragment_angular_direction.py --phase post-reference`
5. `validate_m0b1_raw_fragment_angular_direction.py --phase post-reference`

The protocol file must exist before step 1. Reference files are not opened in
the freeze or pre-reference phases.

## Completed result

- Primary state: `M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT`
- Secondary states:
  - `M0B1_RUNTIME_OPTICAL_TEMPORAL_SAMPLING_BLOCKED`
  - `M0B1_POST_REFERENCE_RAW_FRAGMENT_EVALUATION_INTERFACE_NOT_ESTABLISHED`
- Frozen protocol SHA256:
  `702277348913B3E7CBA6A4CEBF56ACA08807021F91C2E202236EDD3573973278`
- Pre-reference bank: 308,600 records; 66,260 static-feasible; 11,252
  same-fragment distinct-sample dynamic records; zero determinate optical
  interval directions.
- Nominal reference-supported layer: 26 records, 10 dynamic available, 15 raw
  fragment breaks, 1 static-infeasible, and zero determinate directions.
- Reference-supported SAR edges: 6 across only 3 frame-pair clusters; raw
  branches remain unresolved.
- Pre-reference validation: `PASS (26/26)`.
- Post-reference validation: `PASS (15/15)`.
- Visual QA: 12 no-manual-overlay figures plus 12 post-reference-overlay
  figures inspected and readable.
- Frozen execution amendment 01 fixes only the pandas `Series.to_frame` name
  collision in case rendering; no scientific rule or frozen pre-reference
  artifact changed.
- Incremental angular signal: not observed.
- Static-shell re-expression: not identifiable because all dynamically
  available optical direction intervals contain zero.
- M0B2 recommendation: `NO`; diagnose interval width, optical sampling,
  fragment continuity, synchronization, and mapping slope first.
