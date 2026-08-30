# PERSON-B0 end-to-end capability and bottleneck study log

## Pre-run

- Date: 2026-08-30 (Asia/Shanghai).
- Active repository: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Verified branch `main`.
- Verified `HEAD == origin/main == fd1fe0b1f425cb811da32cdc481140d4835633b4` and ahead/behind `0 0`.
- Existing unrelated dirty entries: 340 collapsed `git status --short` entries; they remain outside the B0 allowlist.
- `old_work` is archive-only and will not be used.
- B0 outputs are restricted to `output/person_b0_end_to_end_capability_and_bottleneck_study_20260830` plus the explicitly requested uncommitted review pack.
- TERG-D0/v1/R0/R1/R2 and P1E remain read-only.
- R04ZF, independent confirmation, P2, final localization, new tracking, learned fusion, and Hungarian assignment are out of scope.
- The historical GM vehicle-transfer calibration described by the optical-to-SAR transfer skill is incompatible with the PERSON 1024x592 stream geometry and is not injected into this study.

## Execution status

- Completed source/interface inventory and B0 diagnostic-contract definition.
- Implemented `run_person_b0.py` and an independent `validate_person_b0.py`.
- P0 benchmark: 18 pairs in 2.84 seconds, 17 available and 1 unavailable.
- Full-stream SAR-only P0: all 1,482 adjacent development pairs evaluated in 73.18 seconds.
  - R01ZF: 484 available, 10 unreliable/ambiguous, 0 unavailable.
  - R02ZF: 485 available, 6 unreliable/ambiguous, 3 unavailable.
  - R03ZF: 469 available, 24 unreliable/ambiguous, 1 unavailable.
- P0 fitting excluded foreground with conservatively dilated SAR-only Q95 masks. No PERSON boxes, optical identity, or manual reference entered P0 estimation.
- Recomputed partial-P0 and full-P0 candidates under one `PERSON_B0_GRADED_P0_FAMILY_V1_OPTIONAL_COMPATIBLE` semantics. Positive soft overlap alone is upper-possible, not decisive topology authority.
- Materialized unified per-entity burdens, diagnostic units and overlap clusters, timing-context sensitivity, threshold/authority audit, optical-identity oracle, one-anchor oracle, fixed range sweep, and combined ladder.
- `ORACLE_TIMING_UNAVAILABLE`: nominal index/FPS zero-offset mapping remains unverified; 250 ms is only a context window.

## Scientific result

- `CURRENT_RUNTIME` and `FULL_STREAM_P0` both have overall median `N_family=7` on the unit summary; on 801 matched frame/entity rows, full P0 has median family reduction 0, mean 0.230, improves 145 rows, and worsens 18 under the versioned set-valued family definition.
- Oracle optical identity has overall matched-frame median reduction 0. R02ZF is the meaningful exception: median reduction 1 and improvement on 53.5% of matched rows.
- B0 one-correct-anchor propagation has median family deletion 0 and a 7.4% positive fraction. The frozen R1 comparator also has median deletion 0 and maximum 4.
- Coarse range is dominant on 119 available reference-aligned entity/frame cases:
  - ±3 m: median `N_family 12 -> 2`, median reduction 9, reference retention 1.000.
  - ±2 m: `12 -> 1`, reduction 10, retention 1.000.
  - ±1 m: `12 -> 1`, reduction 10, retention 1.000.
  - ±0.5 m: `12 -> 1`, reduction 11, retention 1.000.
  - near-exact ±0.05 m: `12 -> 1`, reduction 11, retention 1.000.
- Direct conclusion: `COARSE_RANGE_IS_DOMINANT_MISSING_OBSERVABLE`.
- Secondary conclusions: full-stream P0 is an established but non-dominant interface; optical identity is a secondary R02-weighted limitation; relational propagation is weak at the median even with an oracle anchor; the current Q95 response representation remains range-dependent and retains a residual ambiguity tail.

## Visual and external review artifacts

- Generated four summary figures and Panels A-H with raw optical, raw SAR, Q95 outlines, angular-corridor rays, candidate annotations, and explicit oracle labels where applicable.
- Generated `review_packs/PERSON_B0_DEEP_REVIEW_PACK_20260830` and its uncommitted ZIP.
- Pack contents: 67 raw SAR JPGs, 54 deduplicated raw optical JPGs, 67 original Q95 NPZs, 24 CSVs, and 19 figures.
- ZIP bytes: 153,482,591.
- All copied raw files and masks were byte-preserving; manifest source/destination SHA256 verification passed.
- Independent validation: PASS 39/39, including pack manifest hashes and ZIP integrity.

## R04 scope note

- No R04ZF image, result value, manual reference, confirmation conclusion, or R04-derived evidence entered B0 analysis, figures, tables, report, or review pack.
- An earlier broad inventory in the inherited work did touch R04-named source/output paths and one mixed-schema file before strict filtering. Therefore a literal claim that no R04-named path was ever accessed would be false; the defensible claim is that no R04 evidence was used.

## Outputs

- Task: `tasks/person_b0_end_to_end_capability_and_bottleneck_study_20260830`
- Research output: `output/person_b0_end_to_end_capability_and_bottleneck_study_20260830`
- Report: `output/person_b0_end_to_end_capability_and_bottleneck_study_20260830/REPORT.md`
- Validator: `output/person_b0_end_to_end_capability_and_bottleneck_study_20260830/validation_results.json`
- Review ZIP, excluded from commit: `review_packs/PERSON_B0_DEEP_REVIEW_PACK_20260830.zip`
