# TPGT-GM-B1.1 Complete-Target Core Panel

Build a small optical-first complete-CAR candidate panel for GM_RM011,
GM_RM017, and GM_RM019; freeze review candidates before opening SAR manual
reference for azimuth validation; and perform an optical-only PERSON scout.

## Boundaries

- No edits to A-line workbench, Study Queue, schemas, or observations.
- No truncation correction, difficult-target rescue, detector development,
  SAR selector, mechanism inference, or final SAR annotation.
- Automatic rules create `AUTO_CANDIDATE` rows only. Human review is required
  before promotion to the final core panel.
- Optical selection products contain no SAR GT, residual, or response evidence.

## Runtime

- Worktree: `D:\profile\research\wt_b11`
- Python: `D:\MINICONDA\envs\py311\python.exe`
- Output: `output\tpgt\gm_complete_target_core`
- Branch: `feature/tpgt-gm-complete-core-panel`
