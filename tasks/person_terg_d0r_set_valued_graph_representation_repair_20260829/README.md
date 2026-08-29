# PERSON TERG-D0R Set-Valued Graph Representation Repair

This task implements the development-side representation repair authorized after the TERG-v0 visual-semantic audit.

## Scope

- Separate physical SAR response regions from optical-conditioned explanation incidence.
- Preserve continuous edge evidence and represent connectivity through lower/core and upper/possible graphs.
- Replace whole-segment `ANY_SHARED => ORDER_UNDEFINED` with possible relation sets and temporal support extents.
- Represent split/merge/deformation as coexisting topology hypotheses rather than hard PERSON/SAR events.
- Replace contraction wording with temporal-stratification and burden profiles while retaining actual pruning at zero.
- Remove the unverified `250 ms` default from repaired timing semantics and explicitly retain unresolved synchronization offset.
- Re-render development-side real-image before/after cases.

## Boundaries

- Active workspace: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Inputs: committed TERG-D0 development artifacts plus the completed Phase-A audit.
- Outputs: `output/person_terg_d0r_set_valued_graph_representation_repair_20260829`
- No R04ZF or held-out confirmation access.
- No reference-fitted threshold, weighted score, tracker, assignment, factor graph, P2, or final SAR center/box.
- `old_work` is archive-only and is not a runtime dependency.

## Representation principle

The lower graph uses no new numeric threshold. It contains only mutually local-dominant, exclusive one-to-one, P0-common-compatible, non-deformation, non-censored continuations. Raw soft intersection, source retention, destination explained fraction, soft IoU, residual, topology, and censoring evidence remain in the edge record. The upper graph retains every frozen D0 positive-support edge. Optional edges remain legal but cannot silently acquire the same topology authority as lower-graph edges.

## Run and validate

```powershell
& 'D:\MINICONDA\envs\py311\python.exe' 'tasks\person_terg_d0r_set_valued_graph_representation_repair_20260829\run_terg_d0r.py'
& 'D:\MINICONDA\envs\py311\python.exe' 'tasks\person_terg_d0r_set_valued_graph_representation_repair_20260829\validate_terg_d0r.py'
```

The validator independently checks structural invariants, pre/post-reference separation, weak-bridge authority, shared relation preservation, topology/timing semantics, visual artifacts, and the freeze documents. It also regenerates the SHA-256 artifact manifest.
