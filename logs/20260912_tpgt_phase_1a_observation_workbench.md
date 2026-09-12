# TPGT Phase 1A Observation Workbench

Started 2026-09-12. This is a blind-first human observation workflow enhancement over the existing six frozen Phase 1A evidence packs. It does not resample the Study Queue, modify Canonical Schema v1-R1, define M001, generate final SAR boxes, or add detection/ranking/selector logic.

- Active workspace: `D:/profile/research/workspace`
- Interpreter: `D:/MINICONDA/envs/py311/python.exe`
- Task code: `tasks/tpgt_phase_1a/`
- Output namespace: `output/tpgt/phase_1a/observation_workbench/`
- Existing media are referenced in place; no `old_work` dependency.
- Historical PERSON manual boxes and derived interpolation seeds are Open-book-only resources with distinct provenance.
- Existing unrelated worktree changes are preserved and excluded from this task.

Implementation and verification results will be appended after the workbench build.

## Implementation / verification

- Added `tasks/tpgt_phase_1a/observation_workbench/{OBSERVATION_VIEW.html,OPEN_BOOK_VIEW.html,workbench.js,workbench.css}` as a thin adapter over existing evidence-pack media and canvas-style coordinate mapping.
- Added `enhance_observation_workbench.py`, `serve_workbench.py`, and `check_observation_workbench.py`.
- Added output schema files for observation, interpretation candidate, and future CAR identity/visibility annotations. Canonical Schema v1-R1 was not edited.
- Added per-pack `workbench_data.js` and `open_book_registry.json`; blind pages do not request the registry. Open-book layers are independently switchable and labeled MANUAL / DERIVED / PROXY.
- Browser QA passed for all six queue events: native image load, forward/reverse stepping, browser-to-native ROI coordinate bounds, bookmark, blind revision, post-open-book revision, registry request only after navigation, and reference provenance labels on the PERSON anchor.
- QA generated append-only sample records and then removed those synthetic records; the output `records/` namespace is clean except for per-event README markers. No scientific observation is claimed by automated QA.
- Queue hash still matches `audit/pre_sar_selection_freeze.json`; existing six-event selection is unchanged.
- Final QA artifact: `output/tpgt/phase_1a/observation_workbench/audit/observation_workbench_qa.json` (`complete: true`). Synthetic server-written records were removed after QA; no human observation content is being asserted.
