# PERSON range-temporal decision study log

## Pre-run

- Date: 2026-08-30 (Asia/Shanghai).
- Active repository: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Verified branch: `main`.
- Verified `HEAD == origin/main == a1e160c0b503380391689c40a1cf773ad579a4bc`; ahead/behind `0 0`.
- Existing unrelated dirty baseline: 340 collapsed `git status --short` entries; baseline SHA256 `af4925ad1bdfe861e1060b769085dabbe8121e979a0ff1c4cdbe0f8e4937b175`.
- File-expanded `git status --porcelain=v1 -uall` count is 22,836 because untracked directories are expanded. Nothing in that inherited baseline will be cleaned or broadly staged.
- Verified B0 report at `output/person_b0_end_to_end_capability_and_bottleneck_study_20260830/REPORT.md`.
- Verified B0 ZIP at `review_packs/PERSON_B0_DEEP_REVIEW_PACK_20260830.zip`: 153,482,595 bytes, SHA256 `e795b7648ef20110b2387881909d0f1b7df25047b2e7236378a9b79777b7d34e`.
- B0 direct result is treated as a prior diagnostic, not this study's conclusion: coarse range was the strongest tested oracle, while recurrent moving-corridor specificity and runtime range feasibility remained untested.
- `old_work` is archive-only and will not be used.
- R04ZF is excluded from inventory, data loading, analysis, figures, reference reveal, review pack, and conclusions.
- Pre-reference outputs will be frozen and hashed before manual range/reference tables are loaded.

## Execution status

- Preflight and B0 review completed.
- Implemented `run_person_range_temporal.py` and independent `validate_person_range_temporal.py`.
- Pre-reference tree completed and froze 27 files before reference reveal; root SHA256 `dbe75cc78d46752358279509491193b93feceadfee01054ec42a54c804eb4e7e`.
- Defined strict temporal families only from 47/47-style mutual-dominant P0 continuity; retained B0 set-valued optional-family burden as a separate dependency rather than making optional Union-Find the sole metric.
- R03 source `R03ZF_I01_T0004`, F447-F494: top strict family admissible 48/48, unique on F451/F457/F459/F466/F470, reference radial support retained on all four available mapped reference rows.
- Constructed six deterministic same-run 48-frame time-shift controls with zero nominal optical detected-PERSON frames. Selection used duration, exact corridor trajectory, response density, P0 availability and boundary nuisance variables only; recurrence outcomes and reference were not used.
- Strongest matched null: 11 unique observations, exceeding source five. Another background family occupied 48/48 frames. Source corridor-to-family theta affine median residual was 0.406 deg; matched null range was 0.162-0.954 deg.
- R02 wrong-family counterexample: 28/41-frame occupancy with zero reference radial, theta and 2D support on available rows.
- Calibration inventory found no PERSON-scene camera K, height, pitch/roll, camera-radar R/t, ground plane or synchronized platform pose. The historical vehicle candidates remain withheld/incompatible and were not reused.
- Footpoint descriptor audit: 119 oracle-aligned rows; bbox height versus reference range Spearman `-0.777`, bbox bottom `-0.329`. These are post-reference descriptors only, not a runtime range function.
- Visual review completed on R03 F447-F475, matched null key events, R02 F472-F494, the R02 wrong-family counterexample, and R01 range success/failure cases. Computed and visual verdicts are separate in `visual_review_ledger.csv`.
- B0 range width result on 119 reference-aligned rows:
  - ±3 m: median `N_family 12 -> 2`, non-singleton fraction 0.655, maximum 7.
  - ±2 m: `12 -> 1`, non-singleton fraction 0.471, maximum 4.
  - ±1 m: `12 -> 1`, non-singleton fraction 0.176, maximum 3.
  - near-exact: `12 -> 1`, no residual multi-family row in this subset.
- Decision: `TEMPORAL_RECURRENT_GROUNDING_SIGNAL_PRESENT_BUT_NOT_PERSON_SPECIFIC_ENOUGH + COARSE_RANGE_STILL_DOMINANT + CALIBRATED_RANGE_FEASIBILITY_BLOCKED_BY_MISSING_GEOMETRY`.
- Single next priority: implement and calibrate an optional conservative coarse-range interval interface with an engineering target near ±2 m. Range unavailable falls back to angle-only support.
- Generated 10 figures, including the core candidate-support contraction mechanism.
- External review pack generated and validated:
  - ZIP: `review_packs/PERSON_RANGE_TEMPORAL_DECISION_REVIEW_PACK_20260830.zip`
  - bytes: 181,214,073
  - SHA256: `dec4e4fba97920d4f29e0ba046b81fd1e7b70bbbedec7df0bbe6aca3a2a0a12c`
  - 89 raw SAR images, 59 deduplicated raw optical images, 89 original Q95 NPZs, 24 CSVs, 10 figures, 299 manifest entries.
- Independent validator: PASS 49/49 with review-pack hash and ZIP integrity checks.
- No R04 path, image, result, manual reference or evidence was accessed or used.
