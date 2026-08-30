# PERSON range-temporal decision study

## Purpose

This development study compares two runtime-legal unary-information routes without assuming either conclusion:

1. Existing temporal information: moving optical angular corridor, recurrent SAR Q95 temporal family, and long-horizon trajectory descriptors.
2. Conservative coarse range: a physically grounded interval interface when calibration and footpoint observability permit it.

The primary unit is candidate-support contraction (`N_region`, set-valued `N_family`, and candidate area) with reference radial-support retention, matched-control specificity, coverage, and availability reported separately.

## Frozen boundaries

- Active repository: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- `old_work` is archive-only and is not a runtime dependency.
- Starting commit: `a1e160c0b503380391689c40a1cf773ad579a4bc`.
- Existing B0, TERG, P1E, and P0 artifacts are read-only dependencies.
- Optical supplies time, azimuth, lifecycle, corridor trajectory, and conditional footpoint geometry only.
- SAR retains response-family, range, and any future final-localization authority.
- Q95 regions/families are conditional SAR image-domain responses, not PERSON boxes, classifiers, identities, intrinsic RCS, or recovered physical motion.
- Manual reference is post-reference diagnostic only. Pre-reference recurrence records, controls, trajectory expressions, denominators, and case selections must be materialized and hashed first.
- No R04ZF access, confirmation, P2, final PERSON center/box, learned model, new tracker, Hungarian assignment, weighted fusion, or end-to-end classifier.
- Range is optional evidence authority: unavailable or censored geometry falls back to angle-only support and never rejects PERSON by itself.

## Paths

- Task code: `tasks/person_range_temporal_decision_study_20260830`
- Output: `output/person_range_temporal_decision_study_20260830`
- Log: `logs/20260830_person_range_temporal_decision_study.md`
- External review pack: `review_packs/PERSON_RANGE_TEMPORAL_DECISION_REVIEW_PACK_20260830`
- ZIP, excluded from Git: `review_packs/PERSON_RANGE_TEMPORAL_DECISION_REVIEW_PACK_20260830.zip`

## Required answers

The report must directly answer whether R03 recurrent singleton behavior remains informative under moving-corridor matched controls; whether current trajectories provide coarse depth/range; what a runtime range interval could legally use; which interval width retains most B0 contraction; the strongest counterexample; and the single recommended next direction.

## Reproduction

Use `D:\MINICONDA\envs\py311\python.exe`:

```powershell
python run_person_range_temporal.py pre
python run_person_range_temporal.py post
python run_person_range_temporal.py figures
python run_person_range_temporal.py pack
python validate_person_range_temporal.py --require-pack
```

`pre` materializes and hashes all recurrence records, deterministic matched controls, trajectory expressions, calibration inventory, denominators, and case definitions before any manual reference is opened. `post` refuses to run if those hashes change.

## Result

- R03 source: one strict mutual-dominant family is admissible for 48/48 frames and unique five times.
- Matched no-PERSON controls: one family is unique eleven times; another persists for 48/48 frames. Recurrence and smooth trajectory geometry are therefore not sufficiently PERSON-specific.
- Runtime physical range interval: not established because camera K, camera height, pitch/roll, camera-radar extrinsic, ground plane, platform pose and verified synchronization are missing.
- B0 engineering target: about ±2 m half-width. ±3 m is valuable but leaves median `N_family=2`; ±2 m reaches median `1`; ±1 m has no additional median gain.
- Independent validator: PASS 49/49 with the review pack present.
- R04 access: false.

See `output/person_range_temporal_decision_study_20260830/REPORT.md` and the uncommitted external review ZIP.
