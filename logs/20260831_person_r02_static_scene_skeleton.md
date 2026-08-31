# PERSON-R02-S0 run log

## Pre-run state

- Started: 2026-08-31 Asia/Shanghai.
- Active repository: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Verified `HEAD == origin/main == bb9ac8299bf7577be4a357f57b2df9aa7495a3b2`; ahead/behind `0/0`.
- Existing inherited dirty worktree is preserved without cleanup or broad staging.
- Verified raw R02ZF optical path exists with 298 frames and raw R02ZF SAR pseudocolor path exists with 495 frames.
- `old_work` and archive content are not runtime inputs. R04 is excluded and must not be accessed.
- PERSON discrimination, PERSON reference-guided boundary selection, final localization, P2, learned models, new tracking, and full camera calibration are paused/excluded.
- Time pairing uses filename timestamps; same frame indices are not treated as synchronized. `NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED` remains explicit.

## Planned run

1. Materialize the timestamp-paired R02ZF inventory and synchronized continuous review strips, centered first on optical F120 / SAR F200.
2. Reuse the prior GT-blind SAR boundary evidence only as an input hypothesis, rename the three bands neutrally, and trace them across the full R02ZF sequence.
3. Inspect real optical/SAR images to select 2-5 visual static landmarks and retain competing SAR bright-point trajectories.
4. Quantify boundary co-presence, curved separation, temporal stability, matched landmark residuals, and leave-one-anchor-out behavior if at least three anchors survive.
5. Generate review figures, report, manifest, validator, and an uncommitted review pack.

## Post-run result

- Completed with `D:\MINICONDA\envs\py311\python.exe`; no `old_work` runtime path was used.
- Correct timestamp pairing is materialized for all 495 SAR frames against 298 optical frames. The maximum nearest nominal timestamp residual is 23 ms; the core case is exactly OPT F120 / SAR F200 at `t=006667ms`. `NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED` remains the synchronization status.
- The three neutral SAR layers are centered near A `4.85 m`, B `7.30 m`, and C `12.40 m`, with full-sequence availability `353/495`, `173/495`, and `296/495` respectively.
- A/B jointly pass the strict curved-ridge gate on `122/495` frames. Available-frame median separation is `2.500 m`; temporal P90 absolute variation is `0.250 m`; median within-frame theta P90 absolute variation is `0.542 m`.
- The longest strict stable subsegment is SAR F330-F335. Its median A/B separation is `2.512 m` and temporal P90 absolute variation is `0.100 m`.
- Radial verdict: `PARALLEL_BOUNDARY_PAIR_SUPPORTED_IN_STABLE_SUBSEGMENTS_PHYSICAL_STRIP_IDENTITY_PLAUSIBLE_NOT_UNIQUE`.
- Three visually distinct strapped roadside trees were followed. Optical availability is TREE_A `61/66`, TREE_B `70/81`, TREE_C `67/81`.
- No tree-to-SAR compact point survived multi-frame matched competition. Confirmed static anchors: `0`; `CURRENT_AZIMUTH_MAPPING = STATIC_ANCHORS_INSUFFICIENT_TO_JUDGE`. No offset/slope correction or mapping rewrite is authorized.
- The user's tree has a strong single-frame false candidate near `18.75 m`: F200 residual about `+0.14 deg`, but only `50.9%` persistence with median/P90 absolute residual `1.76/4.51 deg`.
- C is retained as `THIRD_PERSISTENT_SCENE_LAYER_IDENTITY_COMPOSITE`, not pure random clutter and not a uniquely named physical edge.
- The early 7-11-frame template landmark experiment was removed from the formal code/evidence whitelist. Its local tables and coordinate-grid figures remain only as unstaged development diagnostics and are excluded from the output manifest and review pack.
- Independent validator: `PASS 17/17`. It recomputes synchronization, denominators, pair metrics, stable-segment selection, tree counts, zero confirmed anchors, non-claims, continuous raw-sequence counts, and ZIP per-entry integrity.
- Main report: `output/person_r02_static_scene_skeleton_20260831/REPORT.md`.
- Main figure: `output/person_r02_static_scene_skeleton_20260831/figures/R02_STATIC_SCENE_SKELETON_OVERVIEW.png`.
- Validation: `output/person_r02_static_scene_skeleton_20260831/VALIDATION_RESULTS.csv` and `VALIDATION_SUMMARY.json`.
- Review pack remains uncommitted: `review_packs/PERSON_R02_STATIC_SCENE_SKELETON_REVIEW_PACK_20260831.zip`.
- Review pack size: `296,514,783 bytes`; SHA256: `fdc32727bfff78037fd7718797f388d9523c2e2fa295aee8a054589745c6b62a`; entries: `134`.
- PERSON reference, PERSON discrimination/grounding, final location/box, R04, P2, learned models, new trackers, full calibration, intrinsic RCS, and physical platform-motion recovery were not used or claimed.
