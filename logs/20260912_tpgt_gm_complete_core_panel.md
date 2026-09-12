# 2026-09-12 TPGT-GM-B1.1

## Pre-run

- Independent worktree: `D:\profile\research\wt_b11`.
- Base commit: `66c2f7189b4f508d07aa939970a4b55ace99b0fb`.
- Branch: `feature/tpgt-gm-complete-core-panel`.
- Default interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- `old_work` excluded; outputs restricted to
  `output\tpgt\gm_complete_target_core`.
- Optical-only candidate selection is frozen before SAR manual-reference use.
- A-line files and existing observations are read-only and will not be changed.

## Post-run

- Entry point: `tasks/tpgt_gm_complete_core_panel/run_gm_complete_core_panel.py`.
- Output root: `output/tpgt/gm_complete_target_core`.
- Optical-only candidate counts: GM011=1 (`PV013`), GM017=4 (`PV001`–`PV004`),
  GM019=1 (`PV003`). All remain `AUTO_CANDIDATE` with `REVIEW_REQUIRED`.
- Deferred complexity inventory records all non-core identities; no truncation,
  occlusion correction, or difficult-target analysis was performed.
- Final core panel is intentionally empty with `PENDING_HUMAN_REVIEW`; no automatic
  promotion was made.
- SAR manual reference was not opened. Frozen GM17 mapping and scene-specific/shared
  mapping models are blocked until explicit human core decisions exist.
- PERSON scout found only two singleton detector-cache observations (GM011 frame 271,
  GM017 frame 164); GM019 had no usable person detection. No PERSON core candidate.
- Optical-only CAR/PERSON contact sheets and `media_manifest.csv` were generated.
- Validation status: `PASS_WITH_REVIEW_GATE`.
