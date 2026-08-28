# M0A-R authoritative source review and supersession ledger

- Review date: 2026-08-28
- Workspace: `D:\profile\research\workspace`
- Starting HEAD: `02a112565e72a3aed4ef674377cdb9052a33b33a`
- Precedence rule: current code/schema, frozen materialized artifacts, and
  independent validators outrank older narrative documents.
- Scope: source review for M0A-R closeout and M0B draft design only.
- `old_work` read or used: `NO`
- M0B executed: `NO`

## Authoritative files actually reviewed

### Current state and design documents

1. `tasks/person_physics_guided_image_domain_study_20260824/README.md`
2. `tasks/person_physics_guided_image_domain_study_20260824/docs/current_state_review.md`
3. `tasks/person_physics_guided_image_domain_study_20260824/docs/M0_TIME_COORDINATE_AND_INTERFACE_AUDIT.md`
4. `tasks/person_physics_guided_image_domain_study_20260824/docs/M0_OPTICAL_SAR_MOTION_CONSISTENCY_MINIMAL_STUDY_DRAFT.md`
5. `tasks/person_physics_guided_image_domain_study_20260824/docs/M0B_OPTICAL_SAR_ANGULAR_DYNAMIC_CONSISTENCY_PROTOCOL_DRAFT.md`

### Frozen M0A implementation and materialized evidence

6. `output/person_physics_guided_image_domain_study_20260824/m0a_r02_lag1_q95_region_support_transport_pilot/M0A_R02_LAG1_Q95_REGION_SUPPORT_TRANSPORT_PROTOCOL_FROZEN_BEFORE_RUN.md`
7. `tasks/person_physics_guided_image_domain_study_20260824/run_m0a_r02_lag1_q95_region_support_transport.py`
8. `tasks/person_physics_guided_image_domain_study_20260824/validate_m0a_r02_lag1_q95_region_support_transport.py`
9. `tasks/person_physics_guided_image_domain_study_20260824/test_m0a_mask_warp.py`
10. `output/person_physics_guided_image_domain_study_20260824/m0a_r02_lag1_q95_region_support_transport_pilot/M0A_R02_LAG1_Q95_REGION_SUPPORT_TRANSPORT_REPORT.html`
11. `output/person_physics_guided_image_domain_study_20260824/m0a_r02_lag1_q95_region_support_transport_pilot/final_output_manifest.json`
12. `output/person_physics_guided_image_domain_study_20260824/m0a_r02_lag1_q95_region_support_transport_pilot/execution_ledger.json`
13. `output/person_physics_guided_image_domain_study_20260824/m0a_r02_lag1_q95_region_support_transport_pilot/final_validation.json`
14. `output/person_physics_guided_image_domain_study_20260824/m0a_r02_lag1_q95_region_support_transport_pilot/post_reference_summary.json`
15. The frozen pre-reference node, P0/ZERO compatibility, matched-alternative,
    post-reference supported-explanation, and case-registry tables named in the
    M0A frozen protocol and M0A-R protocol hashes.

### Current response-region, topology, optical, timing, and P0 authorities

16. `tasks/person_physics_guided_image_domain_study_20260824/run_p1e_runtime_track_response_region_minimal.py`
17. `output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/runtime_track_response_region_minimal_v1/00_RUNTIME_TRACK_RESPONSE_REGION_PROTOCOL_FROZEN_BEFORE_RUN.md`
18. `output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/runtime_track_response_region_minimal_v1/00A_PRE_RUN_OPTICAL_IDENTITY_PROVENANCE_AMENDMENT.md`
19. `output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/runtime_track_response_region_minimal_v1/00B_PRE_RUN_REGION_RULE_CLARIFICATION.md`
20. `output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/runtime_track_response_region_minimal_v1/response_region_table_pre_reference.csv`
21. `tasks/person_physics_guided_image_domain_study_20260824/run_p1e_shell_uncertainty_region_topology.py`
22. `tasks/person_physics_guided_image_domain_study_20260824/validate_p1e_shell_uncertainty_region_topology_report.py`
23. `output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/shell_uncertainty_region_topology_v1/00_SHELL_UNCERTAINTY_REGION_TOPOLOGY_PROTOCOL_FROZEN_BEFORE_RUN.md`
24. `output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/shell_uncertainty_region_topology_v1/gt_blind_shell_region_pixel_edges_pre_reference.csv`
25. `output/person_physics_guided_image_domain_study_20260824/p1e_sar_only_response_interface/shell_uncertainty_region_topology_v1/pre_reference_manifest.json`
26. `tasks/person_physics_guided_image_domain_study_20260824/run_p0_common_apparent_motion.py`
27. `output/person_physics_guided_image_domain_study_20260824/01_P0_COMMON_APPARENT_MOTION_PROTOCOL.md`
28. `output/person_physics_guided_image_domain_study_20260824/p0_common_apparent_motion/model_parameters_per_pair.jsonl`
29. `output/person_physics_guided_image_domain_study_20260824/p0_common_apparent_motion/validation_report.json`

## Conflicts and supersessions

| Earlier statement or artifact | Current authority | Resolution for M0A-R and M0B |
| --- | --- | --- |
| Candidate-split temporal qualification gate controlled whether temporal work could proceed. | `current_state_review.md`, later dynamic work, and frozen M0A artifacts. | The old gate is historical only and is superseded as a research-eligibility rule. It remains preserved, not deleted. |
| The runtime-track main protocol described `optical_person_id` too strongly as a runtime continuity hypothesis. | `00A_PRE_RUN_OPTICAL_IDENTITY_PROVENANCE_AMENDMENT.md` plus current code/schema. | `raw_track_fragment_id` is the primary runtime-legal optical object. `optical_person_id` is a full-run stitched/interpolated `GT_BLIND_OFFLINE_CONTINUITY_PROXY`, not runtime identity. |
| `response_region_track_shell_intersection.csv` used coarse region angular extent against shell intervals. | Pixel-edge code, frozen topology protocol, `gt_blind_shell_region_pixel_edges_pre_reference.csv`, and its validator. | Current topology authority is true pixel-level shell-region intersection. The older angular-extent table is historical and cannot support current topology claims. |
| `M0_TIME_COORDINATE_AND_INTERFACE_AUDIT.md` recorded that authoritative mask warp was not implemented/materialized. | Frozen M0A protocol, M0A runner, `test_m0a_mask_warp.py`, warp synthetic results, final manifest, and final validator. | This was true at the M0 docs-only snapshot but is superseded by M0A's frozen soft affine mask-warp contract and validation. |
| Early M0 draft language proposed a future mask-warp convention and possible low-threshold adjacency. | Frozen M0A protocol and complete P0/ZERO pair matrices. | M0A is now the authority: the soft forward support rasterization and all-pair materialization are implemented and frozen. The draft remains provenance, not an executable contract. |
| A q95 region exists in every frame and may appear highly persistent. | Frozen response-field definition plus M0A-R matched reference-free controls. | Existence and persistence are image-domain properties, not PERSON-presence or identity evidence. |
| M0A's `29/30` matched comparisons may look like 30 independent observations. | M0A-R cluster tables and leave-one-frame-pair-out audit. | They are nested under six supported base edges and only three frame-pair clusters; interpretation is descriptive, not confirmatory. |

## Current authoritative semantics

- Frozen M0A remains `M0A_REGION_SUPPORT_TRANSPORT_WITH_P0_GAIN`.
- M0A-R adds the qualification
  `M0A_R_TRANSPORT_VALID_BUT_PERSON_SPECIFICITY_NOT_ESTABLISHED`.
- The positive unit remains `REFERENCE_SUPPORTED_DYNAMIC_EXPLANATION`; all six
  positives are shared by two target references and PERSON-exclusive positives
  are zero.
- Optical provides nominal time and azimuth-shell hypotheses only. SAR retains
  range and final-localization authority.
- M0B is a draft for incremental raw-fragment angular evidence. It has not been
  executed and does not authorize a tracker, assignment, timing fit, weighted
  score, factor-graph inference, or final SAR box.
