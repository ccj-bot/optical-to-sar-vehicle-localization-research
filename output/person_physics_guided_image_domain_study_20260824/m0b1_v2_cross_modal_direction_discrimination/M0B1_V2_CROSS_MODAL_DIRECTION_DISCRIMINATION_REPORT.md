# M0B1-V2 cross-modal direction discrimination report

- Primary state: `M0B1_V2_DIRECTION_SIGNAL_SCENE_COMMON_NOT_BRANCH_SPECIFIC`
- Secondary states: `M0B1_V2_RAW_BRANCH_EVALUATION_UNRESOLVED; R02_DIRECTION_SIGN_DEGENERATE; M0B1_V2_INCREMENTAL_BEYOND_SAR_ONLY_NOT_ESTABLISHED`
- Scientific status: exposed R02 development diagnostic; descriptive only

## Conclusion

The corresponding-boundary optical representation is stably observable, but R02 is direction-sign degenerate: every deduplicated optical branch pair is positive and branch decisions reproduce the global scene direction baseline.  Against 30 frozen reference-unsupported SAR alternatives, nominal direction favors the supported edge in a subset and never favors the null, but those cases are already SAR-only supported wins.  Direction therefore supplies scene-conditioned confirmation, not branch/PERSON specificity and not demonstrated incremental resolution beyond SAR-only evidence.

## Required 41-question closeout

1. Starting HEAD / report-generation HEAD: `752dd28f26666c8e9e08fd94ad0e74a2beebfade` / `752dd28f26666c8e9e08fd94ad0e74a2beebfade`. The final closeout commit and pushed HEAD are reported in the task handoff because a commit cannot contain its own hash.
2. Commit/push/divergence: completed after report generation and recorded in the final task handoff.
3. Actual authorities: current runners/schemas/validators, frozen M0A/M0A-R/M0B1/M0B1-R artifacts, latest pixel topology, then protocols and older narratives.
4. Supersession: pixel intersection supersedes coarse angular extent; raw fragments supersede stitched identity for runtime semantics; M0B1-R does not overwrite M0B1.
5. Optical representation: `M0B1_V2_CORRESPONDING_BOUNDARY_DIRECTION_V1` with left/right/mid/width descriptors and 1e-12 degree numerical tolerance.
6. SAR representation: q95 corresponding-boundary structural state with mixed/deformation preserved.
7. Pre-reference hypotheses: `308600`.
8. Static-feasible rows: `66260`.
9. Dynamic-available rows: `11252`.
10. Fragment-break rows: `46334`.
11. Same-sample rows: `8674`.
12. Optical positive/negative/deformation: see timing table; nominal deduplicated state counts `{'OPTICAL_COHERENT_POSITIVE_SHIFT': 37}`.
13. SAR positive/negative/deformation: materialized in `sar_descriptors_pre_reference.csv` and timing table.
14. Cross-modal concordant/contradictory/indeterminate/unavailable: materialized for every hypothesis and timing condition.
15. R02 scene-common: yes; sign-degenerate=`True`.
16. Per-frame branch diversity: nominal neighborhoods=13, maximum disagreement=0.0000.
17. Global baseline: unique coherent majority per exact optical temporal neighborhood.
18. Branch direction beyond global: no; differing cluster decisions=`0`.
19. Supported vs matched-null nominal pairwise: supported/null/no-decision=`5/0/25`.
20. Direction favors supported/null/no-decision: reported above and by timing in `pairwise_direction_summary.csv`.
21. SAR-only x direction cross-tab: `sar_only_direction_cross_tab.csv`.
22. Rescue/confirmation/conflict: `0/5/0` nominal matched-edge clusters.
23. Static-shell tautology: direction-blind static controls materialized; no claim of static re-expression dominance is made.
24. Timing sensitivity: optical sign stays positive across all five fixed conditions; sync remains uncalibrated.
25. Cluster-aware result: 6 supported base edges from 3 frame-pair clusters; row counts are not independent.
26. Leave-one-pair-out: materialized in `leave_one_frame_pair_out_direction.csv`; no p-value.
27. Post-reference raw-fragment evaluator: no legal direct source found; offline review interface materialized.
28. Evaluator provenance: hashes and findings in `raw_fragment_target_evaluator_audit.json`.
29. Confirmed/ambiguous/unresolved branches: `0/0/10` review packs.
30. Correct-vs-wrong raw fragment: unresolved and not executed.
31. PERSON/branch specificity: not established.
32. Scene-common dynamic prior: established descriptively for this R02 slice.
33. Incremental cross-modal information: `5` confirmatory direction decisions, but zero SAR-only ambiguity rescues; incremental resolution not established.
34. Most explanatory cases: supported positive-positive, supported deformation, matched-null contradictory, and scene-common representative.
35. Aggregate/image conflict: visual QA must check whether interval overlays and q95 regions support the categorical state; no identity inference is allowed.
36. Conflict diagnosis priority: representation/rendering bug, static geometry burden, shared/mixed SAR topology, timing availability, then physical interpretation.
37. Broader atlas: `586` eligible opposite-direction windows across `56` runs; all are future-design candidates, not cherry-picked winners.
38. Magnitude next: no; projection and scene-common decomposition remain unresolved.
39. Common apparent motion next: yes, before branch-relative residual direction validation.
40. Counterfactual admissibility next: no; gate passed=`False` and diagnostic was not executed.
41. Still forbidden: sync calibration, physical PERSON angular velocity, optical-SAR identity, PERSON-specific continuation, runtime identity, validated pruning/ambiguity reduction, unique path, final center/box, P2, or generalization.

## Pre-reference timing denominators

| timing_condition | total_hypothesis | static_feasible | dynamic_available | same_sample | fragment_break | observation_unavailable | static_infeasible | optical_positive | optical_negative | optical_deformation | optical_no_resolved | sar_positive | sar_negative | sar_deformation | cross_concordant | cross_contradictory | cross_structural_indeterminate | cross_unavailable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NOMINAL | 62073 | 13685 | 2303 | 1795 | 9587 | 0 | 48388 | 2303 | 0 | 0 | 0 | 29381 | 28535 | 4157 | 1045 | 777 | 481 | 59770 |
| SAR_SHIFT_MINUS_1 | 61299 | 12721 | 2377 | 1509 | 8835 | 3540 | 48578 | 2377 | 0 | 0 | 0 | 29094 | 28171 | 4034 | 1131 | 820 | 426 | 58922 |
| SAR_SHIFT_PLUS_1 | 61515 | 12950 | 1950 | 1856 | 9144 | 2915 | 48565 | 1950 | 0 | 0 | 0 | 29080 | 28275 | 4160 | 932 | 605 | 413 | 59565 |
| OPTICAL_SHIFT_MINUS_1_NOMINAL_STEP | 60624 | 11995 | 2196 | 1661 | 8138 | 0 | 48629 | 2196 | 0 | 0 | 0 | 28737 | 27879 | 4008 | 984 | 754 | 458 | 58428 |
| OPTICAL_SHIFT_PLUS_1_NOMINAL_STEP | 63089 | 14909 | 2426 | 1853 | 10630 | 0 | 48180 | 2426 | 0 | 0 | 0 | 29838 | 28892 | 4359 | 1109 | 808 | 509 | 60663 |

## Nominal supported-vs-null cluster decisions

| pair_index | alternative_rank | direction_pairwise_decision | global_pairwise_decision | sar_only_pairwise_outcome | joint_category |
| --- | --- | --- | --- | --- | --- |
| 0 | 3 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 0 | 2 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 0 | 5 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 0 | 4 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 0 | 1 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 0 | 1 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 0 | 5 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 0 | 2 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | ALTERNATIVE_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 0 | 4 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 0 | 3 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 10 | 5 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 10 | 4 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 10 | 2 | DIRECTION_FAVORS_SUPPORTED | DIRECTION_FAVORS_SUPPORTED | SUPPORTED_WIN | DIRECTION_CONFIRMATION |
| 10 | 1 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 10 | 3 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 10 | 3 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 10 | 5 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 10 | 1 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 10 | 4 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 10 | 2 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 15 | 2 | DIRECTION_FAVORS_SUPPORTED | DIRECTION_FAVORS_SUPPORTED | SUPPORTED_WIN | DIRECTION_CONFIRMATION |
| 15 | 4 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 15 | 1 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 15 | 5 | DIRECTION_FAVORS_SUPPORTED | DIRECTION_FAVORS_SUPPORTED | SUPPORTED_WIN | DIRECTION_CONFIRMATION |
| 15 | 3 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 15 | 3 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 15 | 4 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 15 | 2 | DIRECTION_FAVORS_SUPPORTED | DIRECTION_FAVORS_SUPPORTED | SUPPORTED_WIN | DIRECTION_CONFIRMATION |
| 15 | 1 | DIRECTION_NO_DECISION | DIRECTION_NO_DECISION | SUPPORTED_WIN | DIRECTION_REDUNDANT_NO_DECISION |
| 15 | 5 | DIRECTION_FAVORS_SUPPORTED | DIRECTION_FAVORS_SUPPORTED | SUPPORTED_WIN | DIRECTION_CONFIRMATION |

## Visual and evaluator boundary

All available requested categories are rendered from real optical and SAR images. Missing categories remain `CATEGORY_NOT_OBSERVED`. Offline review packs remain `UNRESOLVED` because neither optical_person_id nor visual appearance supplies an authoritative cross-modal target identity.

## Recommendation and stop

Use the full GT-blind atlas eligibility set to design a separately frozen common-apparent-motion versus branch-relative residual study. Do not fit magnitude or deploy direction pruning in the current R02 result.
