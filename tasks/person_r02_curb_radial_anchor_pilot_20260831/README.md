# PERSON-CURB0: R02 parallel curb radial anchor pilot

## Scope

This task studies only the R02ZF parking-lot static boundary described by the user as the road/sidewalk curb or step. The scientific question is whether a persistent SAR image-domain boundary can provide a scene-conditioned radial anchor when intersected with the existing frozen optical angular corridor.

## Fixed boundaries

- Active workspace only: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- `old_work`, archive content, and R04 content are excluded.
- Optical supplies timestamp, azimuth-corridor, and provisional visual-topology support only.
- SAR retains boundary extraction, radial image-domain support, Q95 response-family, and final-localization authority.
- No camera calibration recovery, new TERG state, P0 semantic change, tracker, identity assignment, score fusion, final PERSON center, or final PERSON box.
- The curb/static boundary is represented as a set-valued band in `(theta, range)`, never as an exact optical-to-SAR point match.
- Manual visual topology is `VISUAL_DEVELOPMENT_ONLY`; reference is forbidden until pre-reference artifacts, denominators, cases, controls, and hashes are frozen.

## Required sequence

1. Verify Git/C0/inherited-dirty baseline.
2. Inspect real timestamp-paired R02ZF optical and SAR frames before detector design.
3. Materialize `CURB_VISUAL_HYPOTHESIS_LEDGER.csv` with visual and computed verdicts kept separate.
4. Build reviewable SAR boundary candidates and data-supported bands; retain multiple hypotheses or emit `CURB_AMBIGUOUS` / `CURB_UNAVAILABLE`.
5. Freeze pre-reference artifacts and hashes.
6. Only then evaluate manual reference support and angle-only versus curb-topology burden.
7. Package review artifacts in an uncommitted ZIP and commit only lightweight allowlisted files.

## Outputs

- Main output: `D:\profile\research\workspace\output\person_r02_curb_radial_anchor_pilot_20260831`
- Log: `D:\profile\research\workspace\logs\20260831_person_r02_curb_radial_anchor_pilot.md`
- Review ZIP: `D:\profile\research\workspace\review_packs\PERSON_R02_CURB_RADIAL_ANCHOR_REVIEW_PACK_20260831.zip`

