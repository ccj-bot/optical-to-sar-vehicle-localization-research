# 2026-08-31 PERSON-CURB0 pre-run log

## Pre-run state

- Task: R02 parallel curb radial anchor pilot.
- Active workdir: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Branch: `main`.
- Verified HEAD: `35b4ea2b523562a0f05d1899c7f4df0dcb7ef50c`.
- Verified origin/main: `35b4ea2b523562a0f05d1899c7f4df0dcb7ef50c`.
- Ahead/behind: `0/0`.
- Inherited dirty baseline excluding review packs: 340 collapsed entries and 22,836 file-expanded entries.
- Current total including review packs before this task: 341 collapsed entries and 22,981 file-expanded entries.
- C0 report exists and states `823/823 RANGE_UNAVAILABLE` with no legal geometric runtime range interval.
- Existing C0 review ZIP verified at 15,585,007 bytes, SHA256 `32f1911c69f51313399606c4fcdcccb1f6b4f8550e052eb89a9cb8970f028fbd`.
- `old_work` and archive-only material: not used.
- R04 content: not accessed.

## Pre-run scientific contract

- Real R02ZF images must be reviewed before automatic curb extraction is designed.
- Optical/SAR pairing uses registry timestamps and uncertainty, not frame-index equality.
- Visual curb hypotheses and computed detector verdicts remain separate.
- Multiple plausible SAR static-boundary hypotheses are retained.
- Any selected radial band width must be supported by observed ridge thickness, candidate multiplicity, or temporal variability.
- Ideal parallel-line geometry is diagnostic only.
- Optical topology is provisional `VISUAL_DEVELOPMENT_ONLY` and cannot choose the SAR boundary.
- Uncertain topology causes no radial deletion.
- Q95 pruning uses exact pixel intersections; `Omega` remains a physical search support, not a PERSON box.
- Manual reference remains closed until pre-reference freeze and hashing are complete.

## Run log

- Pre-run documentation created before experiment execution.
- Directly reviewed 39 timestamp-paired R02ZF optical/SAR frame pairs before automatic extraction.
- Frozen primary window: SAR F421-F474; negative controls: F375/F390/F405/F414 and F480/F486/F488, plus early branching frames F0/F30/F60.
- GT-blind static-band candidates: 7.10 m primary, 4.90 m retained near alternative, 12.40 m far parallel confounder.
- Primary extraction availability: 48/54 frames (88.9%); longest uninterrupted available segment: F462-F474.
- Current frozen corridor curb interval width: median 2.257 m, P90 2.779 m.
- Sensitivity median/P90 widths: +/-6 deg 1.579/2.385 m; +/-4 deg 1.127/1.667 m; +/-3 deg 0.905/1.316 m; +/-2 deg 0.684/0.974 m; +/-1 deg 0.460/0.641 m.
- Current-corridor exact-Q95 median burden under the selected primary band: N_region 8 -> 7, N_family 8 -> 7, A_candidate_px 2192 -> 1873, A_candidate_m2 2.507 -> 2.143.
- Identity-conservative 4.90/7.10 m set has median N_family 8 -> 8, so the physical-identity ambiguity materially weakens the gain.
- Strongest residual same-side clutter case: R02ZF F431, 18 -> 15 families after primary curb pruning.
- Pre-reference root SHA256: `3febe4272067cb2bed4b403b8d8eeb09777c96d6c878c8dbc44eea0479b1b9ec`.
- Post-freeze reference denominator: 4 rows, all in 12-14 m; no 6-8 m rows in the selected stable window. Current corridor retains 100% angular/radial/2D support; every centered narrower sensitivity retains only 50% angular/2D support on this small denominator.
- Validator: 69/69 PASS.
- Report: `D:\profile\research\workspace\output\person_r02_curb_radial_anchor_pilot_20260831\REPORT.md`.
- Minimal SAR identity confirmation template: `D:\profile\research\workspace\output\person_r02_curb_radial_anchor_pilot_20260831\SAR_CURB_IDENTITY_CONFIRMATION_TEMPLATE.csv`.
- Review ZIP remains uncommitted: `D:\profile\research\workspace\review_packs\PERSON_R02_CURB_RADIAL_ANCHOR_REVIEW_PACK_20260831.zip`, 35,224,414 bytes, SHA256 `6531b197f7d3aea0b11ca3b77800935c6b55d24e79dbc036cc91da65c14be0f6`.
- R04 content accessed: false.
