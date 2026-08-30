# PERSON-C0 calibrated conservative coarse-range interface log

## Pre-run

- Date: 2026-08-30 (Asia/Shanghai).
- Active repository: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Verified branch: `main`.
- Verified `HEAD == local origin/main == c47a68d69866e4b366e7ab65261030751de85e11`; local ahead/behind `0 0`.
- Live `git fetch origin` attempt failed with a Windows Schannel TLS handshake error. Remote freshness is not yet claimed and will be retried before closeout.
- Inherited unrelated dirty baseline remains 340 collapsed `git status --short` entries, SHA256 recorded by the preceding task as `af4925ad1bdfe861e1060b769085dabbe8121e979a0ff1c4cdbe0f8e4937b175`.
- File-expanded inherited baseline remains 22,836 `git status --porcelain=v1 -uall` entries.
- The preceding intentionally uncommitted `review_packs/` directory adds one collapsed entry and 144 expanded files, yielding 341 collapsed and 22,980 expanded entries before PERSON-C0 files are added.
- Verified prior report: `output/person_range_temporal_decision_study_20260830/REPORT.md`, 8,471 bytes, SHA256 `3449a0e12715de453e6f53ab4fb6a2a21c2b7c24a122af4845f3670632ec65d9`.
- Verified prior ZIP: `review_packs/PERSON_RANGE_TEMPORAL_DECISION_REVIEW_PACK_20260830.zip`, 181,214,073 bytes, SHA256 `dec4e4fba97920d4f29e0ba046b81fd1e7b70bbbedec7df0bbe6aca3a2a0a12c`.
- Prior range-width results are oracle diagnostics only and are not a calibration substitute.
- `old_work` is archive-only and will not be searched or used.
- No R04 path content, image, result, reference, or evidence will be accessed.

## Execution status

- Preflight completed.
- Broad filename/type recovery inspected 282 candidate paths across active workspace, current raw data and related optical-SAR repositories while excluding `old_work`, archive, review packs, R04-named paths and virtual environments.
- Strong intrinsic text check covered 8,644 text files; four matching files/lines contained only negative audit/inventory statements or search code, not a numeric PERSON-scene K.
- Focused semantic scan materialized 72 hits in 15 candidate files and classified every required interface in `calibration_asset_registry.csv`.
- Verified all R01ZF/R02ZF/R03ZF optical videos are 3840x2160 at approximately 18 FPS and SAR pseudocolor videos are 1024x592 at 30 FPS.
- Verified the current optical frame chain is raw MP4 decode -> no resize -> no crop -> no letterbox -> 3840x2160 JPEG. This establishes coordinate compatibility only; it does not recover K.
- Recovered usable support assets: native image resolution/FPS, identity raw-to-stored optical coordinate chain, optical angular corridor and SAR 20 m radial render geometry. Nominal timestamps remain zero-offset/FPS-derived and semantically uncertain.
- Missing single-frame range authorities: PERSON camera K/distortion, camera height, pitch/roll, camera-radar R/t, local ground-plane envelope and runtime footpoint interval/state. No metric depth stream or verified ground homography was found.
- Global platform pose is not required for a single-frame radar-relative ground intersection; it remains a temporal/world-registration requirement.
- Generated 823 causal runtime rows: 0 `RANGE_AVAILABLE`, 823 `RANGE_UNAVAILABLE`; every row falls back to angle-only full radial support and `person_rejected_due_to_range=false`.
- Visual review covered `FOOTPOINT_OBSERVABLE`, `FOOTPOINT_PARTIAL`, `FOOTPOINT_CENSORED`, `FOOTPOINT_AMBIGUOUS` and `FOOTPOINT_UNAVAILABLE`. Computed and visual verdicts are separate.
- Actual SAR fallback example: R02ZF frame 421, 18 angle-only Q95 regions and 18 angle-plus-runtime-range regions because range is unavailable. This is fallback semantics, not a contraction experiment.
- No PERSON manual SAR reference was loaded. Interval width distribution, reference radial retention and candidate contraction are therefore N/A rather than fabricated.
- Pre-reference tree froze 11 files with root SHA256 `f0da23038b95f26d5e881d00e6390b9245f25dc9dbbb464a9cc0b7fb5e14c61b`.
- Generated five reviewed figures plus `PERSON_C0_MINIMUM_CALIBRATION_CHECKLIST.md`.
- External review ZIP generated and intentionally left uncommitted:
  - `review_packs/PERSON_C0_COARSE_RANGE_CALIBRATION_REVIEW_PACK_20260830.zip`
  - final bytes and SHA256 are recorded outside the ZIP in `output/person_c0_calibrated_conservative_coarse_range_interface_20260830/review_pack_metadata.json` to avoid a self-referential pack hash.
- Independent validator: PASS 51/51 with freeze hashes, visual states, runtime fallback, ZIP integrity/content and Git non-tracking checks.
- No R04 path content, image, result, reference or evidence was accessed or used.
