# R02 local boundary observability

This task reframes R02ZF static near/far boundary work as sparse semantic checkpoints plus conservative local propagation.

## Scientific isolation

- Primary seed frames are F062, F150, F183, F264, and F454.
- Each propagation process reads one isolated seed file containing only that frame's near/far geometry.
- Other manual checkpoints are not read by propagation and are revealed only after the pre-reference outputs are hashed.
- The frozen F150-F183 propagation implementation and thresholds are imported unchanged.

## Representation audit

The frozen implementation samples a manual polyline as `d_perp(theta)` nodes, transports it with P0, and searches one scalar offset for the whole curve. Nodes are evaluated along the ridge but are not independently displaced, so curve shape is rigid within a path. Near/far evidence is computed separately, while the original pair-safe path stops when either boundary or the pair corridor becomes unsafe.

This task reports both:

- the unchanged pair-safe path used as conservative optional scene context;
- a boundary-independent observability diagnostic using the same frozen per-boundary proposal and thresholds, so near-only and far-only availability can be observed without accepting pair-unsafe geometry.

## Outputs

Outputs are written under `output/r02_local_boundary_observability_20260902`. `pre_reference` is frozen before any cross-checkpoint audit. Manual JSONL files remain read-only. No PERSON, tree, final localization, R04, or `old_work` path is used.

Finalization adds `FINAL_SUMMARY.json`, `REPORT.md`, `post_freeze_audit/MANUAL_VISUAL_VERDICTS.csv`, and `VALIDATION_REPORT.json`. The review pack ZIP is generated in the same output directory but is intentionally excluded from Git.

## Reproduction order

Use `D:\MINICONDA\envs\py311\python.exe`:

1. `run_pre_reference_local_observability.py prepare`
2. one isolated `propagate` process per seed
3. `consolidate` and `freeze`
4. `audit_and_render_local_observability.py`
5. `finalize_local_observability.py`
6. `validate_local_observability.py`
7. `build_review_pack.py`

Do not rerun steps 1-4 merely to regenerate the final report; the committed pre-reference manifest is the scientific freeze boundary.
