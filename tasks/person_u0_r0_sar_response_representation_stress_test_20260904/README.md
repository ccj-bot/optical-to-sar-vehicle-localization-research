# U0-R0 — SAR Response Representation Stress Test

## Objective

Test whether T0 ambiguity is caused by the current response representation or
remains visible under several simple, GT-blind representations of the same SAR
display-domain response field.

The study reuses only T0 windows W1, W3, W4, and W5. It does not optimize a
tracker, rank candidates, learn a classifier, fuse scores, infer identity, or
produce a final PERSON location.

## Fixed boundaries

- Active workspace: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- `old_work` is archive-only and is not a runtime dependency.
- R04 is forbidden.
- Optical supplies only the frozen time/azimuth corridor used by T0.
- SAR retains response representation, radial structure, and final-localization
  authority.
- The available runtime SAR input is an 8-bit pseudocolor display frame. Sensor
  raw amplitude/complex/IQ is unavailable; figures must label the unmodified
  input and display-derived intensity/score fields honestly.
- The pre-construction code path does not load manual reference data, and no
  reference value may choose a threshold, hierarchy, case, formula, or manual
  pre-reference class.
- Strict analyst-naive reveal ordering cannot be claimed for this implementation:
  the reference table schema and sample rows were inspected while implementing
  the later post-reference loader. The supported boundary is code/data isolation.
- Manual reference diagnostics may run only after the pre-reference tree is
  frozen and independently validated.

## Representations under stress

1. Existing Q95 8-connected components and existing strict mutual-dominant P0
   families.
2. Q90 8-connected components on the unchanged frozen C2/S(x) field.
3. Q97.5 8-connected peak-core components on the same field.
4. A sampled component hierarchy: Q97.5 child -> Q95 parent -> Q90 parent by
   exact pixel containment.
5. Threshold-specific temporal families produced by the same frozen P0 warp and
   mutual-dominance operation at Q90/Q95/Q97.5.

This is a stress test, not a winner-selection exercise. Q90 parents are not
declared physical bundles merely because they reduce component counts.

## Execution

```powershell
& "D:\MINICONDA\envs\py311\python.exe" .\run_person_u0_r0.py --phase pre
& "D:\MINICONDA\envs\py311\python.exe" .\run_person_u0_r0.py --phase finalize-pre
& "D:\MINICONDA\envs\py311\python.exe" .\validate_person_u0_r0.py
& "D:\MINICONDA\envs\py311\python.exe" .\run_person_u0_r0.py --phase post
& "D:\MINICONDA\envs\py311\python.exe" .\run_person_u0_r0.py --phase pack
```

`--phase pre` constructs the representations, tables, and draft review figures.
`--phase finalize-pre` reuses the existing 44 representation fields, refreshes
only targeted review sheets/manual ledgers, and freezes once all selected reviews
are complete. `--phase post` refuses to run unless the freeze validates.

## Planned outputs

- `output/person_u0_r0_sar_response_representation_stress_test_20260904/HISTORICAL_OVERLAP.md`
- `output/person_u0_r0_sar_response_representation_stress_test_20260904/REPORT.md`
- representation masks/fields for 44 selected frames;
- multi-level component and hierarchy tables;
- threshold-specific P0 edges and temporal-family membership;
- W1/W3/W4/W5 compact contact sheets and sequence atlases;
- split/merge semantic reverse-audit ledger and counterexamples;
- frozen pre-reference manifest plus separate post-reference support audit;
- external review pack under `review_packs/`.

## Git allowlist

Only this task directory and
`logs/20260904_person_u0_r0_sar_response_representation_stress_test.md` may be
staged by default. Generated outputs and review images remain reproducible local
artifacts unless explicitly force-added.
