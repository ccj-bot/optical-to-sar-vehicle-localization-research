# PERSON-C0 calibrated conservative coarse-range interface

## Purpose

Determine whether current, legitimate project assets can support a GT-blind and runtime-legal conservative PERSON coarse-range interval

`R_i(t) = [r_min, r_max]`

and physical search support

`Omega_i(t) = Theta_i(t) x R_i(t)`.

The study must recover and verify calibration assets before attempting geometry. It may conclude `CALIBRATION_ASSETS_INSUFFICIENT_FOR_RUNTIME_RANGE_PROTOTYPE`; no parameter may be fabricated to avoid that conclusion.

## Frozen boundaries

- Active repository: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Starting commit: `c47a68d69866e4b366e7ab65261030751de85e11`.
- `old_work` is archive-only and is not searched or used.
- R04 paths and contents are excluded from inventory, loading, analysis, figures, packing, and conclusions.
- Optical provides conditional time, azimuth, lifecycle, and optional geometric range support only.
- SAR retains response-family, range-image interpretation, and any future final-localization authority.
- `Omega` is PERSON-conditioned physical search support, not a PERSON center, box, identity, classifier output, or detection gate.
- Q95 regions and P0 families remain conditional SAR image-domain response supports.
- No offline target identity, PERSON SAR reference, empirical bbox-height fit, fixed `range +/- 2 m`, deep monocular depth, learned/weighted fusion, tracker, P2, or final localization is allowed in range generation.
- `RANGE_UNAVAILABLE` degrades to angle-only support and never rejects PERSON or closes a hypothesis.
- Manual SAR reference may be used only after any runtime artifacts and case selections are frozen and hashed.

## Scientific sequence

1. Recover and classify camera/radar calibration, coordinate-chain, mounting, ground, pose, timing, and acquisition assets.
2. Materialize `calibration_asset_registry.csv` with `FOUND_AND_VERIFIED`, `FOUND_BUT_SEMANTICS_UNCERTAIN`, `FOUND_BUT_INCOMPATIBLE`, or `MISSING`.
3. Track `raw -> resize -> crop -> letterbox -> stored optical frame` before transforming camera intrinsics.
4. Separate `SINGLE_FRAME_RELATIVE_RANGE_REQUIREMENT` from `TEMPORAL_WORLD_REGISTRATION_REQUIREMENT`.
5. If sufficient, propagate footpoint and calibration envelopes through verified ray/ground geometry to a conservative interval.
6. If insufficient, stop downstream geometry and produce `PERSON_C0_MINIMUM_CALIBRATION_CHECKLIST.md`.
7. Keep computed and visual verdicts separate.

## Paths

- Task code: `tasks/person_c0_calibrated_conservative_coarse_range_interface_20260830`
- Output: `output/person_c0_calibrated_conservative_coarse_range_interface_20260830`
- Log: `logs/20260830_person_c0_calibrated_conservative_coarse_range_interface.md`
- External review pack ZIP: `review_packs/PERSON_C0_COARSE_RANGE_CALIBRATION_REVIEW_PACK_20260830.zip`

## Required result

The report must directly answer whether recoverable calibration exists, whether single-frame relative range needs global platform pose, which minimum physical quantities remain missing, whether runtime intervals were generated, and what the next physical action is. If range geometry is blocked, interval width, reference retention, and angle-plus-range contraction remain unavailable rather than inferred from oracle diagnostics.

## Result

- Decision: `CALIBRATION_ASSETS_INSUFFICIENT_FOR_RUNTIME_RANGE_PROTOTYPE`.
- Recoverable current assets: 3840x2160 optical and 1024x592 SAR stream geometry/FPS, identity raw-to-stored optical coordinate chain, optical angular corridor, and SAR 20 m radial render geometry.
- Missing: PERSON camera K/distortion, camera height/pitch/roll, camera-radar R/t, local ground plane, and runtime footpoint interval/state.
- Global platform pose: not required for single-frame relative range; required for world-registered temporal geometry.
- Runtime table: 0/823 range available, 823/823 `RANGE_UNAVAILABLE`, all safely falling back to angle-only support.
- Manual SAR reference: not loaded; realized width, radial retention, and contraction are N/A.
- Pre-reference root SHA256: `f0da23038b95f26d5e881d00e6390b9245f25dc9dbbb464a9cc0b7fb5e14c61b` over 11 files.
- Independent validator: PASS 51/51 with review pack.
- Review ZIP: `review_packs/PERSON_C0_COARSE_RANGE_CALIBRATION_REVIEW_PACK_20260830.zip`, intentionally uncommitted; final bytes and SHA256 are stored externally in `output/person_c0_calibrated_conservative_coarse_range_interface_20260830/review_pack_metadata.json`.
- R04 access: false.
