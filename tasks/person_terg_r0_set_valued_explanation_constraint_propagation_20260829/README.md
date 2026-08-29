# PERSON TERG-R0 Set-Valued Explanation Constraint Propagation

This task explores one reasoning-layer formulation on top of the frozen TERG-v1 representation.

## Scope

- Define a consistent explanation unit and admissible-world semantics.
- Propagate lifecycle, corridor, P0 temporal structure, relation-set, shared/topology, and usable timing constraints without weighted scores, arbitrary thresholds, top-k, best paths, assignment, or reference-driven tuning.
- Measure logical contraction only between the same explanation units.
- Audit evidence contribution, redundancy, order independence, and synergy.
- Freeze pre-reference outputs before development-side post-reference evaluation.
- Perform real-image review of contraction, no-contraction, ambiguity, optional-edge, deformation, and grounding cases.

## Fixed boundaries

- Active workspace: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- TERG-v1 is frozen input and must not be modified.
- `old_work` is archive-only and is not a runtime dependency.
- Optical information is explanation/search support only; SAR retains physical-response, range, and final-localization authority.
- No R04ZF confirmation, tracker, Hungarian assignment, weighted fusion, factor graph, P2, final center, or final box.

## Stop decision

The task must end in exactly one of:

- `TERG_R0_CONSTRAINT_PROPAGATION_MECHANISM_ESTABLISHED`
- `TERG_STRUCTURAL_INFORMATION_REAL_BUT_NONDISCRIMINATIVE`
- `TERG_CONSTRAINT_PROPAGATION_HARMS_VALID_EXPLANATIONS`
- `GROUNDING_TOO_WEAK_TO_DECIDE_DISCRIMINATION`

## Run

```powershell
& 'D:\MINICONDA\envs\py311\python.exe' 'tasks\person_terg_r0_set_valued_explanation_constraint_propagation_20260829\run_terg_r0.py'
& 'D:\MINICONDA\envs\py311\python.exe' 'tasks\person_terg_r0_set_valued_explanation_constraint_propagation_20260829\validate_terg_r0.py'
```

The run script writes and hashes the complete pre-reference reasoning layer before loading TERG-v1 grounding. The validator independently reconstructs every segment world count and every family marginal from the frozen pair registry.
