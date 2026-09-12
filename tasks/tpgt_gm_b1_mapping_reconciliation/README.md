# TPGT-GM-B1: GM Spatiotemporal Coordinate and Azimuth Mapping Reconciliation

This task reconstructs and reconciles the time, SAR native-image, SAR display/fan,
and optical-to-SAR azimuth contracts for `GM_RM011`, `GM_RM017`, and `GM_RM019`.

## Scope

- Read-only audit of historical code, tables, raw assets, and provenance.
- Scene-specific contracts first; no forced global formula.
- Optical observations may define time/azimuth corridors only.
- SAR remains authoritative for any later precise localization.
- Manual GT/reference use is explicitly recorded and is never presented as a
  GT-free runtime capability.
- No changes to TPGT Observation Workbench schemas, evidence packs, Study Queue,
  observation records, mechanism interpretation, selectors, or target detectors.

## Runtime

- Working directory: `D:\profile\research\workspace`
- Python: `D:\MINICONDA\envs\py311\python.exe`
- Entry point: `run_gm_mapping_reconciliation.py`
- Output: `D:\profile\research\workspace\output\tpgt\gm_mapping_reconciliation`
- Reproduction: `D:\MINICONDA\envs\py311\python.exe tasks/tpgt_gm_b1_mapping_reconciliation/run_gm_mapping_reconciliation.py`
- Git branch: `feature/tpgt-gm-mapping-reconciliation`

## Status

Initialized 2026-09-12. Historical lineage and asset discovery are in progress.
