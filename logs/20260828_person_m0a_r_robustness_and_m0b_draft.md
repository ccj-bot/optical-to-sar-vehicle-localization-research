# 2026-08-28 PERSON M0A-R robustness audit and M0B draft

## Preflight

- Active workspace: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Starting branch: `main`
- Starting HEAD: `02a112565e72a3aed4ef674377cdb9052a33b33a`
- Starting `HEAD...origin/main`: `0/0`
- Existing unrelated dirty worktree: present and preserved
- `old_work` read or used: `NO`
- Outputs constrained to `workspace\output`; task code constrained to `workspace\tasks`

## Protocol freeze

- Stage: `M0A_R_ROBUSTNESS_AND_SEMANTIC_AUDIT`
- Frozen source: `M0A_R02_LAG1_Q95_REGION_SUPPORT_TRANSPORT_PILOT`
- Audit is read-only with respect to M0A, P0, response field, q90/q95/q97.5,
  region masks, reference mapping, and matched alternatives.
- Prohibited and not performed: optical dynamics execution, M0B execution,
  timing fit, tracker, assignment, scalar score fusion, classifier, factor graph,
  SAR box, or final localization.

## Execution-only repairs

1. The frozen `MERGE_LIKE` case stores related region IDs in the source frame;
   the new renderer initially resolved them in the destination frame. Resolution
   was corrected to match the frozen M0A renderer contract.
2. `pandas.to_markdown()` required the unavailable optional `tabulate` package;
   report construction now uses a deterministic local Markdown table renderer.

Both repairs were frozen before the successful run. Neither changed any
scientific calculation, control selection, case selection, frozen M0A input, or
outcome rule. Details are in `00A_EXECUTION_REPAIR_AMENDMENT.md`.

## Final M0A-R result

- State: `M0A_R_TRANSPORT_VALID_BUT_PERSON_SPECIFICITY_NOT_ESTABLISHED`
- Frozen M0A retained: `M0A_REGION_SUPPORT_TRANSPORT_WITH_P0_GAIN`
- Effective supported clusters: 3 frame pairs, 6 source/base-edge clusters,
  2 repeated target/reference groups
- Area strata from 1,064 pre-reference source regions: `<=70`, `71-209`,
  `210-587`, `>=588 px`
- All 6 supported edges: `LARGE_Q4`
- Supported P0/ZERO/delta medians: `0.9093 / 0.8418 / +0.0550`
- Matched reference-free P0/ZERO/delta medians:
  `0.8594 / 0.8462 / +0.0223`
- Shared supported edges: `6/6`; supported target count per edge: `2`
- PERSON-exclusive positives: `0`
- Independent validation: `PASS (28/28)`
- Deterministic readable figures: `10/10`, including 1/6/19-pixel cases,
  split, merge, deceptive alternative, shared positives, and reference-free
  persistence controls

## Source review and supersession

The closeout source ledger records the actual authoritative inputs and resolves
four principal conflicts:

- the old temporal gate is superseded as a research-eligibility rule;
- `optical_person_id` is an offline stitched continuity proxy, not runtime ID;
- old angular-extent shell/region intersection is superseded by pixel edges;
- M0 docs-only mask-warp absence is superseded by frozen M0A implementation and
  validation.

Ledger:
`output/person_physics_guided_image_domain_study_20260824/m0a_r_robustness_and_semantic_audit/AUTHORITATIVE_SOURCE_REVIEW_AND_SUPERSESSION.md`

## M0B status

- Draft:
  `tasks/person_physics_guided_image_domain_study_20260824/docs/M0B_OPTICAL_SAR_ANGULAR_DYNAMIC_CONSISTENCY_PROTOCOL_DRAFT.md`
- Status: `DRAFT_NOT_EXECUTED`
- Primary optical object: `raw_track_fragment_id`
- Fixed ablations: SAR-only, angular direction, angular magnitude/order, timing
- Fixed timing sensitivity: nominal, ±1 SAR frame, ±1 nominal optical step
- No best-shift selection, offset fit, weighted score, assignment, or unique path
- Recommended future executable minimum: R02 F472-F494, lag1 only, angular
  direction first, all legal hypotheses retained

## Outputs

- Audit report:
  `output/person_physics_guided_image_domain_study_20260824/m0a_r_robustness_and_semantic_audit/M0A_R_ROBUSTNESS_AND_SEMANTIC_AUDIT_REPORT.md`
- Independent validation:
  `output/person_physics_guided_image_domain_study_20260824/m0a_r_robustness_and_semantic_audit/independent_validation.json`
- Figures:
  `output/person_physics_guided_image_domain_study_20260824/m0a_r_robustness_and_semantic_audit/figures`

## Closeout status

- M0A-R audit: complete
- M0B protocol draft: complete, not executed
- Python compilation: pass
- Frozen M0A post-reference validation: `PASS (12/12)`; output hash remained
  `5443FE501312B3177810BAC90478BE96652593C47528183E82C773B0A1CFA55D`
- Frozen P0 validation: `PASS (18/18)`; the validator's timestamp-only rewrite
  was restored so the frozen tracked artifact remains unchanged
- M0A-R independent validation rerun: `PASS (28/28)`
- Commit/push verification: pending at the time this log section was written
