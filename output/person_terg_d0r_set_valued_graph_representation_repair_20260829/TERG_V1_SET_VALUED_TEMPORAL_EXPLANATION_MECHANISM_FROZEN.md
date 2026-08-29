# TERG_V1_SET_VALUED_TEMPORAL_EXPLANATION_MECHANISM — FROZEN

## Freeze state

- Development-side state: `TERG_V1_READY_FOR_INDEPENDENT_CONFIRMATION`
- Freeze date: 2026-08-29 Asia/Shanghai
- Confirmation executed: no
- R04ZF accessed: no
- Reference fitted representation: no
- Weighted scalar score: no
- New numeric repair threshold: no

## Frozen authority model

1. `PhysicalSarRegion(run_id, frame_index, region_id)` is the unique physical SAR image-domain response node.
2. `OpticalConditionedRegionIncidence` connects optical fragment/corridor hypotheses to physical SAR nodes without claiming identity.
3. Physical P0 temporal edges are stored once and retain their full evidence vector.
4. The upper graph contains every frozen D0 P0-positive edge.
5. The lower core contains only mutually local-dominant, exclusive one-to-one, P0-common-compatible, non-deformation, non-censored edges.
6. No new overlap, retention, explained-fraction, IoU, or reference-performance threshold may be inserted into this freeze.
7. Optional edges remain legal. They cannot force lower-core equivalence or be described as rejected solely because they are optional.

## Frozen outputs

- `physical_sar_response_regions_pre_reference`
- `optical_conditioned_region_incidence_pre_reference`
- `explanation_set_region_incidence_pre_reference`
- `set_valued_physical_temporal_edges_pre_reference`
- `admissible_component_families_pre_reference`
- `lower_core_components_pre_reference`
- `component_family_membership_pre_reference`
- `optional_bridge_dependencies_pre_reference`
- `possible_relation_sets_pre_reference`
- `relation_temporal_support_extents_pre_reference`
- `temporal_stratification_burden_profiles_pre_reference`
- `timing_authority_pre_reference`
- `timing_relation_sets_pre_reference`

Post-reference grounding is stored separately and is not an input to graph construction.

## Frozen relation semantics

- Edge relations are sets, not single forced labels.
- Component output is a lower-core partition plus an upper possible connected envelope.
- Relative order output is a `POSSIBLE_RELATION_SET` with temporal support extents.
- Shared response does not erase LEFT, RIGHT, or OVERLAP support.
- No best family pair, assignment, or weighted vote is authorized.
- Split, merge, deformation, fragmentation, boundary, and weak-contact interpretations may coexist.
- Split/merge is not a hard PERSON/SAR event.

## Frozen burden terminology

- `TEMPORAL_STRATIFICATION`: observed multi-frame versus isolated/short organization.
- `COUNTERFACTUAL_CONTRACTION`: only a hypothetical filtering analysis.
- `ACTUAL_PRUNING`: zero in this mechanism.
- `POST_REFERENCE_EVALUATED_DISCRIMINATION`: post-reference diagnosis only.

These terms and their units must not be mixed.

## Frozen timing semantics

- Known: nominal SAR/optical grids and exposed query-grid quantization residual.
- Unknown: bounded cross-modal synchronization offset.
- Removed: unverified default ±250 ms as an uncertainty authority.
- Output under missing calibration: `TIMING_RELATION_SET_UNDER_UNCALIBRATED_SYNC`.
- Exact cross-modal temporal order is not authorized.

## Explicit non-claims

TERG-v1 does not establish intrinsic RCS, recovered physical motion, stable person identity, optical-to-SAR assignment, target tracking, factor-graph inference, P2, candidate pruning, final SAR range, final center, or final box.

Optical remains explanation/search support. SAR retains physical response, range, and final-localization authority.

## Change control

Any future change to node authority, lower/upper connectivity, relation vocabulary, timing authority, reference boundary, or pruning behavior requires a new version. Independent confirmation must use untouched held-out material and must not retroactively tune this representation.
