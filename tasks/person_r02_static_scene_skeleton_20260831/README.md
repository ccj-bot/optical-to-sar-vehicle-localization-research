# PERSON-R02-S0: R02 static radial-azimuth scene skeleton

## Scope

This task pauses PERSON discrimination and studies only the static scene skeleton of R02ZF. It tests whether the persistent SAR structures near 4.90 m, 7.10 m, and 12.40 m form an ordered set of physical scene boundaries, and whether visually selected static optical landmarks have persistent SAR bright-point trajectories compatible with the frozen optical-to-SAR azimuth mapping.

## Fixed boundaries

- Active workspace only: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- `old_work`, archive content, R04, P2, learned models, new trackers, full calibration, PERSON grounding, and final boxes are excluded.
- Optical frame indices are never equated directly with SAR indices; pairing uses filename timestamps and retains `NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED`.
- Optical supplies visual static-landmark identity hypotheses and predicted azimuth only.
- SAR supplies radial boundaries, bright-point trajectories, and all image-domain localization evidence.
- The 4.90/7.10/12.40 m candidates use neutral names `STATIC_BOUNDARY_A/B/C`; response strength, persistence, and physical identity stay distinct.
- Static landmark matches remain set-valued until multi-frame persistence, trajectory residual, and matched competition support them.
- No PERSON reference may tune or identify boundaries or landmarks.

## Required outputs

- Timestamp-paired R02ZF inventory and continuous optical/SAR contact sheets.
- Curved `(theta, range, time)` boundary tracks for A/B/C.
- A/B separation stability and near-to-far ordering audit.
- Visual static-landmark ledger, SAR bright-point competitors, residuals, and leave-one-anchor-out diagnostics when possible.
- A synchronized F120/F200 core figure and a scene-skeleton overview.
- Report, summary, validator results, manifest, and an uncommitted review ZIP.

## Evidence-chain cleanup

- The early template landmark experiment covered only 7-11 SAR frames and is not part of the final evidence chain.
- Final tree conclusions use the longer yellow-strap optical tracks plus multi-range SAR point competition.
- Coordinate grids may be regenerated for development, but they are excluded from the review pack and research commit.

## Paths

- Output: `D:\profile\research\workspace\output\person_r02_static_scene_skeleton_20260831`
- Log: `D:\profile\research\workspace\logs\20260831_person_r02_static_scene_skeleton.md`
- Review ZIP: `D:\profile\research\workspace\review_packs\PERSON_R02_STATIC_SCENE_SKELETON_REVIEW_PACK_20260831.zip`
