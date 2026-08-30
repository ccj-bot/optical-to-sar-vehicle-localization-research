# PERSON-B0 end-to-end capability and bottleneck study

## Purpose

This is a development-diagnostic oracle/interface ladder over the complete available R01ZF, R02ZF, and R03ZF PERSON optical-to-SAR streams. It asks which information layer materially reduces a unified per-PERSON candidate burden before any new runtime algorithm is designed.

## Unified burden units

- `N_region`: surviving physical Q95 SAR regions.
- `N_family`: surviving temporal response families under one explicitly versioned B0 family semantics.
- `A_candidate_px` and `A_candidate_m2`: union candidate support area.
- `A_candidate_over_A_search_support`: candidate area normalized by the optical-corridor SAR search support.
- `N_joint_world`: multi-hypothesis joint explanation burden, reported only as a secondary quantity.

## Ladder separation

- `CURRENT_RUNTIME`: runtime-legal R2 inputs only.
- `FULL_STREAM_P0`: SAR-only adjacent-pair apparent-transport interface, with explicit available/ambiguous/unavailable states.
- `ORACLE_OPTICAL_IDENTITY`: post-reference development diagnostic only.
- `ORACLE_TIMING`: diagnostic only when actual timing evidence exists; otherwise unavailable.
- `ONE_CORRECT_UNARY_ANCHOR`: post-reference oracle only.
- `COARSE_RANGE_ORACLE` and `ORACLE_RANGE`: post-reference oracle only.
- Combined ladders remain set-valued logical intersections, never weighted fusion.

## Frozen boundaries

- Starting commit: `fd1fe0b1f425cb811da32cdc481140d4835633b4`.
- TERG-D0/v1/R0/R1/R2 and P1E are read-only dependencies.
- `old_work` is archive-only and is not a runtime dependency.
- Optical supplies time, azimuth, lifecycle, and oracle-only identity/range diagnostics when explicitly labeled.
- SAR retains response-region, range, and any future final-localization authority.
- No R04ZF confirmation, P2, final center/box, new tracker, learned fusion, or Hungarian assignment.
- The legacy 2308x1334 GM vehicle calibration is not applied to the 1024x592 PERSON streams.

## Paths

- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Task code: this directory
- Output: `output/person_b0_end_to_end_capability_and_bottleneck_study_20260830`
- Log: `logs/20260830_person_b0_end_to_end_capability_and_bottleneck_study.md`
- External review pack: `review_packs/PERSON_B0_DEEP_REVIEW_PACK_20260830`
- ZIP (not committed): `review_packs/PERSON_B0_DEEP_REVIEW_PACK_20260830.zip`

## Timing terminology

The R2 `TIMING_UNCERTAINTY_MS=250` constant is treated here only as an engineering observation context. B0 uses `CONTEXT_LOOKBACK_MS` and `CONTEXT_LOOKAHEAD_MS`; no independent synchronization-error bound is claimed.

## Reproduction

Use `D:\MINICONDA\envs\py311\python.exe`:

```powershell
python run_person_b0.py benchmark-p0 --pairs 18 --workers 3
python run_person_b0.py full-p0 --workers 3
python run_person_b0.py ladder
python run_person_b0.py artifacts
python validate_person_b0.py
python run_person_b0.py pack
python validate_person_b0.py --require-pack
```

The full-stream P0 stage evaluates all 1,482 adjacent R01ZF/R02ZF/R03ZF pairs. The pack command recreates the external review directory and ZIP; the ZIP is intentionally excluded from Git.

## Result

- Direct conclusion: `COARSE_RANGE_IS_DOMINANT_MISSING_OBSERVABLE`.
- Full-stream P0 interface: established with explicit availability states, but median candidate-family burden is unchanged.
- Oracle optical identity: secondary and concentrated in R02ZF.
- One correct unary anchor plus existing set-valued angular order: median zero deletion of other-person families.
- Coarse range: median `N_family` changes from 12 to 2 at ±3 m and to 1 at ±2/1/0.5 m on the available post-reference development subset.
- Timing oracle: `ORACLE_TIMING_UNAVAILABLE`.
- Independent validator: PASS 39/39 with the review pack present.

See `output/person_b0_end_to_end_capability_and_bottleneck_study_20260830/REPORT.md` for the report and figures.
