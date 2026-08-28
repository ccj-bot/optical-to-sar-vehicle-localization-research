# M0B1 R02 raw-fragment angular-direction diagnostic

- State: `M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT`
- Study role: interval angular-direction observability and discrimination diagnostic
- Pareto role: descriptive only; no pruning was performed
- M0B2, magnitude, monotonicity, tracker, assignment, timing fit, and localization: not executed

## Conclusion

The interval representation does not provide enough determinate optical angular direction to establish incremental cross-modal direction information. Same-sample and raw-fragment-break states remain unavailable rather than zero or contradictory. Because the post-reference interface cannot identify a correct raw fragment for a manual target without introducing a new assignment layer, positive labels remain SAR-edge-supported with unresolved raw branches.

## Timing implementation

`NOMINAL` uses the exact decoded optical frame index stored for each SAR frame. SAR shifts query the fixed neighboring SAR frame's nominal optical index; boundary shifts are unavailable. Optical shifts add exactly one decoded optical frame to each endpoint query. No best shift is selected or written back.

## Direction-state summary

| timing_condition | evaluation_group | N_total_hypothesis_records | N_hard_feasible | N_dynamic_available | N_same_optical_sample | N_fragment_break | N_observation_unavailable | N_static_shell_infeasible | N_direction_indeterminate | N_direction_concordant | N_direction_contradictory | N_direction_unavailable | dynamic_availability_rate_of_total | determinate_direction_rate_of_dynamic_available |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NOMINAL | REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED | 26 | 25 | 10 | 0 | 15 | 0 | 1 | 10 | 0 | 0 | 16 | 0.3846 | 0.0000 |
| NOMINAL | FROZEN_MATCHED_SAR_NULL | 105 | 99 | 35 | 0 | 64 | 0 | 6 | 35 | 0 | 0 | 70 | 0.3333 | 0.0000 |
| SAR_SHIFT_MINUS_1 | REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED | 21 | 19 | 0 | 8 | 11 | 2 | 2 | 0 | 0 | 0 | 21 | 0.0000 | 0.0000 |
| SAR_SHIFT_MINUS_1 | FROZEN_MATCHED_SAR_NULL | 87 | 76 | 0 | 26 | 50 | 10 | 11 | 0 | 0 | 0 | 87 | 0.0000 | 0.0000 |
| SAR_SHIFT_PLUS_1 | REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED | 26 | 25 | 0 | 10 | 15 | 0 | 1 | 0 | 0 | 0 | 26 | 0.0000 | 0.0000 |
| SAR_SHIFT_PLUS_1 | FROZEN_MATCHED_SAR_NULL | 105 | 99 | 0 | 35 | 64 | 0 | 6 | 0 | 0 | 0 | 105 | 0.0000 | 0.0000 |
| OPTICAL_SHIFT_MINUS_1_NOMINAL_STEP | REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED | 21 | 20 | 9 | 0 | 11 | 0 | 1 | 9 | 0 | 0 | 12 | 0.4286 | 0.0000 |
| OPTICAL_SHIFT_MINUS_1_NOMINAL_STEP | FROZEN_MATCHED_SAR_NULL | 92 | 86 | 35 | 0 | 51 | 0 | 6 | 35 | 0 | 0 | 57 | 0.3804 | 0.0000 |
| OPTICAL_SHIFT_PLUS_1_NOMINAL_STEP | REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED | 22 | 21 | 9 | 0 | 12 | 0 | 1 | 9 | 0 | 0 | 13 | 0.4091 | 0.0000 |
| OPTICAL_SHIFT_PLUS_1_NOMINAL_STEP | FROZEN_MATCHED_SAR_NULL | 102 | 96 | 34 | 0 | 62 | 0 | 6 | 34 | 0 | 0 | 68 | 0.3333 | 0.0000 |

## Timing sensitivity

| timing_condition | N_total_hypothesis_records | N_hard_feasible | N_dynamic_available | N_same_optical_sample | N_fragment_break | N_observation_unavailable | N_static_shell_infeasible | N_direction_indeterminate | N_direction_concordant | N_direction_contradictory | N_direction_unavailable | dynamic_availability_rate_of_total | determinate_direction_rate_of_dynamic_available |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NOMINAL | 62073 | 13685 | 2303 | 1795 | 9587 | 0 | 48388 | 2303 | 0 | 0 | 59770 | 0.0371 | 0.0000 |
| SAR_SHIFT_MINUS_1 | 61299 | 12721 | 2377 | 1509 | 8835 | 3540 | 48578 | 2377 | 0 | 0 | 58922 | 0.0388 | 0.0000 |
| SAR_SHIFT_PLUS_1 | 61515 | 12950 | 1950 | 1856 | 9144 | 2915 | 48565 | 1950 | 0 | 0 | 59565 | 0.0317 | 0.0000 |
| OPTICAL_SHIFT_MINUS_1_NOMINAL_STEP | 60624 | 11995 | 2196 | 1661 | 8138 | 0 | 48629 | 2196 | 0 | 0 | 58428 | 0.0362 | 0.0000 |
| OPTICAL_SHIFT_PLUS_1_NOMINAL_STEP | 63089 | 14909 | 2426 | 1853 | 10630 | 0 | 48180 | 2426 | 0 | 0 | 60663 | 0.0385 | 0.0000 |

## Static-shell tautology control

Matched pairs: `13`. Direction was not used to select controls. With insufficient determinate interval directions, static-containment re-expression cannot be separated from new dynamic information in this slice.

## Cluster structure

Supported SAR edges: `6` from `3` frame-pair clusters. Row-level hypothesis counts are not independent observations. Per-pair and per-fragment tables are materialized separately.

## Real cases

Twelve deterministic slots are stored with paired no-manual-overlay and post-reference-overlay figures. If a requested direction category is absent, the registry explicitly records the deterministic fallback instead of fabricating a concordant or contradictory case.

## Non-claims and stop

This diagnostic does not establish synchronization, physical PERSON angular velocity, PERSON-specific SAR continuation, raw-fragment identity, ambiguity reduction, pruning validity, a unique path, or final SAR localization. Stop after M0B1; do not enter magnitude or M0B2 automatically.
