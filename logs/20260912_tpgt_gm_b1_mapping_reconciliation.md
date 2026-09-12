# 2026-09-12 TPGT-GM-B1 mapping reconciliation

## Pre-run

- Active workspace verified: `D:\profile\research\workspace`.
- `D:\profile\research\old_work` is excluded and remains archive-only.
- Default interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Output root: `D:\profile\research\workspace\output\tpgt\gm_mapping_reconciliation`.
- A-line boundary: no edits to `tasks/tpgt_phase_1a`, Observation schemas,
  evidence packs, Study Queue, mechanism interpretation, or CAR/PERSON records.
- Existing dirty-worktree content is user-owned; this task will use an explicit
  new-file allowlist only.

## Work log

- Began historical lineage, source-code, raw-asset, and metadata discovery.

## Post-run

- Entry point executed with `D:\MINICONDA\envs\py311\python.exe`:
  `tasks/tpgt_gm_b1_mapping_reconciliation/run_gm_mapping_reconciliation.py`.
- Output root: `output/tpgt/gm_mapping_reconciliation`.
- Asset baseline verified live: each scene has 368 optical PNGs, 766 pseudo-color
  PNGs, and 766 gray PNGs; optical dimensions are 800x600 and SAR dimensions are
  2308x1334 with no missing/duplicate frame indices.
- Gray/pseudo comparison intentionally remains conservative: same frame index and
  dimensions are confirmed, deterministic pixel derivation is not proven.
- Time contracts: exact synchronization `UNKNOWN`; T0/T1/T2 are operational or
  descriptive models, with local SAR windows retained.
- Coordinate contracts: deterministic display fan forward/inverse round-trip
  passed with maximum error 0 px; upstream sensor/imaging chain and raw mask hash
  remain unresolved.
- Azimuth contracts: GM017 has 20 development and 45 held-out eligible anchors;
  linear open-book fit is retained with held-out uncertainty. GM011/GM019 have no
  eligible scene-specific anchors and remain unresolved.
- Validation status: `PASS_WITH_CONSERVATIVE_UNRESOLVED_FIELDS`.
- No A-line files, schemas, evidence packs, queues, observation records, or
  mechanism interpretations were modified.
