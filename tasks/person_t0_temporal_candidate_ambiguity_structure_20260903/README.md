# T0 — Temporal Candidate Ambiguity Structure Study

## Objective

Study whether frame-wise optical-to-SAR candidate ambiguity contracts when the
unit of explanation becomes a temporal, set-valued SAR response family.

The study must explain, on real optical/SAR windows, which candidate
explanations disappear because of observable contradictions and which remain
indistinguishable. Descriptive counts are secondary to image-grounded case
analysis.

## Fixed boundaries

- Active workspace: `D:\profile\research\workspace`.
- Default interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- `old_work` is archive-only and must not be a runtime dependency.
- R04 is forbidden.
- Optical supplies nominal time, lifecycle/continuity, azimuth corridor, and
  event support. SAR retains response-graph, radial, and final-localization
  authority.
- P0 is common apparent transport, not PERSON motion or identity evidence.
- Q95 is candidate response support, not PERSON probability, segmentation, or
  a final box.
- No learned fusion, tracker, Hungarian assignment, unique cross-modal identity,
  score optimization, final SAR center, or final SAR box.
- Candidate explanations remain set-valued. Split/merge/deformation may coexist.
- Construction and case selection use pre-reference artifacts only. Manual
  reference is loaded only in a separate post-reference diagnostic phase.
- Because historical post-reference reports already exist and were part of the
  handoff, the analyst is not knowledge-naive. Leakage prevention therefore
  means code/data isolation plus a frozen pre-reference tree, not a claim that
  the analyst had never seen prior outcomes.

## Reused frozen inputs

- TERG-v1 physical SAR regions, optical-conditioned incidence, upper component
  families, lower-core partitions, optional bridges, and relation sets.
- TERG-R0/R1 relation and evidence-availability diagnostics.
- TERG-R2 full-stream Q95/lifecycle/P0 availability interfaces.
- B0 and range-temporal pre-reference candidate-family tables and matched-null
  controls.
- Existing raw optical/SAR paths and review-pack rendering utilities where
  compatible.

## Planned outputs

- `output/person_t0_temporal_candidate_ambiguity_structure_20260903/REPORT.md`
- a frozen pre-reference case-selection/contract/hash tree;
- 3–5 representative visual review windows;
- per-window candidate evolution and elimination/survival ledgers;
- limited information ablations tied to concrete reappearing ambiguity modes;
- a post-reference retention/failure diagnostic separated from construction;
- an explicit remaining ambiguity taxonomy and next-minimal-experiment decision.

## Implemented workflow

Use the research default interpreter:

```powershell
& "D:\MINICONDA\envs\py311\python.exe" .\run_person_t0.py --phase pre
& "D:\MINICONDA\envs\py311\python.exe" .\validate_person_t0.py
& "D:\MINICONDA\envs\py311\python.exe" .\run_person_t0.py --phase post
& "D:\MINICONDA\envs\py311\python.exe" .\run_person_t0.py --phase pack
```

`--phase pre` is the only construction phase. It recreates and freezes the
task-owned `pre_reference` tree without loading manual reference. `--phase
post` first verifies that freeze, then performs sparse reference diagnostics
without changing windows, candidate families, ledgers, or pre-reference
figures.

## Completed outputs

- Five representative windows and 12 window-track units.
- 15 frozen pre-reference figures: full optical/SAR atlases, candidate
  evolution, and P0 before/after comparisons.
- Candidate region/family events, per-frame evolution, survival/elimination
  reasons, limited information comparisons, set-valued representation overlap,
  and multi-target relation ledgers.
- Five post-reference diagnostic overlays plus frame-, family-, and
  window-track-level reference tables.
- Final `REPORT.md`, `VISUAL_REVIEW.md`, independent validator, artifact
  manifest, and external review pack ZIP.

The current frozen pre-reference tree SHA-256 is
`c2944f954884a1c11f68b2362f48b6b4919826ea2b99bf28148aae5e8c089b98`.

## Git allowlist

Only the following new paths may be staged for this task:

- `tasks/person_t0_temporal_candidate_ambiguity_structure_20260903/`
- `output/person_t0_temporal_candidate_ambiguity_structure_20260903/`
- `logs/20260903_person_t0_temporal_candidate_ambiguity_structure.md`

The inherited dirty baseline must remain untouched.
