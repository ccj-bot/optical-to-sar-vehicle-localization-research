# TERG-R2 runtime grounding and full-stream hypothesis management log

## Pre-run

- Date: 2026-08-30 (Asia/Shanghai)
- Active repository: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Frozen starting HEAD: `7669ec914edeef1aa2e38204cfe19b9753aeb322`
- Verified `HEAD == origin/main` before work.
- Existing unrelated dirty entries: 340; they are outside the R2 allowlist and will remain untouched.
- `old_work` is archive-only; no R2 runtime dependency may point to it.
- TERG-v1/R0/R1/P1E are read-only.
- R04ZF, P2, final localization, learned fusion, Hungarian assignment, and final tracking are out of scope.

## Execution record

- Verified branch `main` and frozen start `HEAD == origin/main == 7669ec914edeef1aa2e38204cfe19b9753aeb322` before execution.
- Dirty-worktree accounting uses two views: the inherited note recorded 340 collapsed status entries; expanded `--untracked-files=all` reported 22,839 paths at handoff. Only the R2 task, output, and this log are in the allowlist.
- Syntax-checked the runner with `D:\MINICONDA\envs\py311\python.exe -m py_compile`.
- Ran the full job with 6 workers over all 1,485 frames, then reran downstream products with `--resume-regions` after correcting negative-time admission semantics.
- Added `validate_terg_r2.py` and completed 84 independent checks with status `PASS`.

## Actual outputs and counts

- Output root: `output/person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830`
- Full-stream frame registry: 1,485 rows; R01ZF/R02ZF/R03ZF each contain F0-F494.
- Full-stream Q95 regions: 74,485.
- Full-stream Q95 masks: 1,485 readable archives.
- Frozen Q95 parity: 202/202 frames pixel-exact; region counts also match on all 202.
- Frozen P0 pair availability: R01ZF 141/494, R02ZF 22/494, R03ZF 36/494.
- Runtime fragment hypotheses: 50.
- Lifecycle rows: 23,289; stream-generated transitions: 403.
- Lifecycle state rows: ACTIVE 5, ACTIVE_AMBIGUOUS 1,446, ADMISSION_PENDING 139, DORMANT 13,179, CENSORED_AT_BOUNDARY 8,418, CENSORED_AT_STREAM_END 102, CLOSED 0.
- Automatic anchor ledger: STRONG 0, CANDIDATE 0, AMBIGUOUS 5, REJECTED 1,446.
- All five ambiguous moments belong to R03ZF `R03ZF_I01_T0004` at causal F459/F466/F470 and fixed-lag F466/F470; each has one family/one current region but fails the no-optical clutter control and lacks independent runtime range support.
- R02ZF produces no candidate or ambiguous unary anchor. Frozen P0 begins at F472 after PERSON017/018 are already concurrent, so no early unary family seed reaches the F487-F494 relation window.
- Negative-time structural audit: 0 SAR-only false-admission events in all 9 run-mode combinations. Seven local no-shell frames retain a previously optical-triggered non-dormant hypothesis; they are continuation cases, not new admissions.
- Sparse-anchor diagnostic, post-reference stand-in only: one-anchor configurations contract another domain in 9/79 tested configurations; two-anchor configurations in 13/65. Exact likely-family retention remains 1.0 in the corrected ledger. This is propagation-capacity evidence, not a runtime result.
- Artifact manifest: 1,551 entries; independent size and SHA-256 verification passed for every entry.
- Figures: 14 PNGs generated.

## Visual verification

Opened and inspected at original detail:

- `01_full_stream_observability_and_anchor_overview.png`
- `02_lifecycle_R02ZF_causal_replay.png`
- `02_lifecycle_R03ZF_causal_replay.png`
- `03_full_stream_q95_and_shell_burden.png`
- `04_negative_time_structural_control.png`
- `05_r1_semantic_corrections.png`
- `06_r02_anchor_relation_propagation_chain_blocked.png`

All focused figures are readable and consistent with the tables. The negative-time plot visibly separates zero SAR-only admission events from previously optical-triggered non-dormant frames.

## Scientific conclusion

1. The prototype can create, retain, make dormant, censor, and preserve reentry/new-identity competing hypotheses. It does not yet know when physical continuation is impossible, so it cannot justify true `CLOSED`.
2. The complete streams do not establish a strong automatic runtime-legal unary anchor. R03ZF offers five ambiguous singleton moments only; R01ZF/R02ZF do not provide a surviving seed.
3. The minimum credible additional absolute information is a runtime-legal coarse range interval or equivalent calibrated unary physical constraint at a low-ambiguity moment, plus deployable P0 continuity connecting that moment to the later relational window.

## Preserved boundaries

- No TERG-v1/R0/R1/P1E file was modified.
- No `old_work` runtime path was used.
- No R04ZF confirmation, P2, final center/box, learned fusion, Hungarian assignment, or final tracker was introduced.
- Raw optical fragments remain hypotheses; optical supplies time/azimuth/lifecycle support only; SAR retains response/range/final-localization authority.
- Missing P0 remains `SAR_P0_CONTINUITY_INTERFACE_UNAVAILABLE` and is never treated as response absence or exit evidence.
