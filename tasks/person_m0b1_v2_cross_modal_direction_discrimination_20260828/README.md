# PERSON M0B1-V2 cross-modal direction discrimination

- Active workspace: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Task output: `D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\m0b1_v2_cross_modal_direction_discrimination`
- `old_work`: archive-only and not used

This task independently versions the corresponding-boundary optical angular
descriptor established by M0B1-R and tests its categorical relationship to
frozen q95 SAR temporal edges.  It preserves the frozen predecessor states:

- `M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT`
- `M0B1_R_INTERVAL_OPERATOR_SEMANTIC_MISMATCH_CONFIRMED`

The task does not fit angular magnitude, timing, weights, a classifier, a
tracker, an assignment, a path, a factor graph, a pruning rule, or a SAR box.

Final state:

- `M0B1_V2_DIRECTION_SIGNAL_SCENE_COMMON_NOT_BRANCH_SPECIFIC`
- `M0B1_V2_RAW_BRANCH_EVALUATION_UNRESOLVED`
- `M0B1_V2_INCREMENTAL_BEYOND_SAR_ONLY_NOT_ESTABLISHED`
- pre-reference validation: `116/116 PASS`
- final validation after visual-QA manifest registration: `175/175 PASS`
- nominal matched-edge direction decisions: `5 favors supported / 0 favors null / 25 no decision`
- SAR-only ambiguity rescues: `0`
- GT-blind future opposite-direction windows: `586` (`585` adjacent-frame)

Run order:

```powershell
& 'D:\MINICONDA\envs\py311\python.exe' .\run_m0b1_v2_cross_modal_direction.py --freeze
& 'D:\MINICONDA\envs\py311\python.exe' .\run_m0b1_v2_cross_modal_direction.py --pre-reference
& 'D:\MINICONDA\envs\py311\python.exe' .\validate_m0b1_v2_cross_modal_direction.py --pre
& 'D:\MINICONDA\envs\py311\python.exe' .\run_m0b1_v2_cross_modal_direction.py --post-reference
& 'D:\MINICONDA\envs\py311\python.exe' .\validate_m0b1_v2_cross_modal_direction.py --post
```

The first post-reference run required
`AMENDMENT_01_POST_REFERENCE_SENTINEL_PAIR_INDEX.md`, a reporting-key repair
that did not change pre-reference artifacts or scientific rules.
