# PERSON TERG-v0 Visual-Semantic Reality Check

This task performs the development-set-only `TERG_V0_VISUAL_SEMANTIC_REALITY_CHECK`.

## Scope

- Independently inspect committed TERG-D0 optical/SAR temporal review imagery.
- Audit graph edge, component, relative-order, contraction, node-identity, and timing semantics.
- Generate pre-reference structural diagnostics and post-reference visual diagnosis only after the pre-reference artifacts are fixed.
- Decide whether a minimal representation repair is required before any future held-out confirmation.

## Boundaries

- Do not modify the frozen TERG-D0 mechanism.
- Do not tune thresholds or timing offsets against reference outcomes.
- Do not run a new held-out confirmation.
- Do not create a tracker, assignment system, weighted score, classifier, factor graph, or final SAR localizer.
- Keep physical SAR response regions distinct from optical-conditioned explanation nodes.

## Runtime

- Active workspace: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Inputs: committed TERG-D0 artifacts under `output/person_physics_guided_image_domain_study_20260824/terg_d0_temporal_event_response_graph_mechanism_exploration`
- Outputs: `output/person_terg_v0_visual_semantic_reality_check_20260829`

## Deliverables

- `TERG_V0_VISUAL_SEMANTIC_AUDIT.md`: A-O scientific audit and minimal D0R design.
- `figures/`: bridge-critical, exact-1.0, relation-set, topology, and full intermediate-frame packs.
- `tables/independent_visual_review_ledger.csv`: independent image-level judgments.
- `ARTIFACT_MANIFEST.sha256`: hashes for all task-owned files except the manifest and validation report themselves.
- `validation_report.json`: integrity/schema/reproducibility checks only; not a scientific PASS/FAIL.

## Reproduction

```powershell
& 'D:\MINICONDA\envs\py311\python.exe' tasks\person_terg_v0_visual_semantic_reality_check_20260829\run_visual_semantic_audit.py
& 'D:\MINICONDA\envs\py311\python.exe' tasks\person_terg_v0_visual_semantic_reality_check_20260829\validate_visual_semantic_audit.py --write-manifest
```
