# TERG-R2 runtime grounding and full-stream hypothesis management

## Scope

This task is a mechanism exploration over the complete available R01ZF, R02ZF, and R03ZF streams. It studies runtime-legal hypothesis admission, maintenance, dormancy, reentry, exit, unary-anchor hypotheses, temporal propagation, negative-time behavior, and sparse-anchor requirements.

## Frozen boundaries

- TERG-v1, R0, R1, and P1E are read-only inputs.
- `old_work` is archive-only and must not be used at runtime.
- Optical observations provide time, azimuth, lifecycle, and explanation support only.
- SAR retains response-graph, range, and final-localization authority.
- Raw optical fragments are runtime hypotheses, not PERSON identity truth.
- Full-run stitched optical identity and manual SAR reference are evaluation-only.
- Missing SAR response-region coverage is `SAR_RESPONSE_INTERFACE_UNAVAILABLE`, never response absence.
- No R04ZF confirmation, P2, final center/box, learned fusion, Hungarian assignment, or final tracker is introduced.
- State transitions use logical/set-valued evidence semantics, not weighted scores.

## Interpreter and outputs

- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Task code: this directory
- Outputs: `output/person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830`
- Log: `logs/20260830_person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management.md`

## Required deliverables

1. R1 semantic-correction ledger and independent visual-review ledger.
2. Full-stream R01ZF/R02ZF/R03ZF replay in causal, fixed-lag, and full-context modes.
3. Stream-level hypothesis state and automatically emitted reasoning intervals.
4. Runtime unary-anchor and anchor-lifecycle diagnosis.
5. Negative-time, sparse-anchor, propagation, and failure-root diagnostics.
6. Scientific report, figures, machine-readable tables, manifest, and independent validator.

## Reproduction

```powershell
D:\MINICONDA\envs\py311\python.exe tasks\person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830\run_terg_r2.py --workers 6
D:\MINICONDA\envs\py311\python.exe tasks\person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830\validate_terg_r2.py
```

Use `--resume-regions` only after a complete 1,485-mask generation when regenerating downstream tables and figures.

## Frozen outcome snapshot

- 1,485 SAR frames: 495 each for R01ZF/R02ZF/R03ZF.
- 202 frozen-coverage frames reproduce Q95 label masks pixel-exactly.
- Frozen P0 pair availability: R01ZF 141, R02ZF 22, R03ZF 36; all other pairs remain explicitly unavailable.
- 50 runtime optical-fragment hypotheses and 403 stream-generated state transitions.
- 0 strong automatic runtime unary anchors; 5 R03ZF singleton moments remain ambiguous after no-optical clutter controls.
- 0 SAR-only false-admission events and 0 scientifically justified `CLOSED` states.
- Independent validation: 84 checks passed, including all artifact-manifest sizes and hashes.

The direct conclusion is that open/keep/dormancy/reentry competition can be expressed, but true semantic closure and an automatic absolute seed are not established. The minimum credible missing information is a runtime-legal coarse range interval or equivalent calibrated unary physical constraint, plus deployable P0 continuity from that low-ambiguity moment into a later relation window.
