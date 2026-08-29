# PERSON TERG-v1 Scientific Freeze Report

## Final development-side state

`TERG_V1_READY_FOR_INDEPENDENT_CONFIRMATION`

This is the outcome of `TERG_D0R_SET_VALUED_GRAPH_REPRESENTATION_REPAIR`. It is a development-side representation freeze, not held-out confirmation. No R04ZF outcome, tracker, assignment, factor graph, P2, final SAR center, or final SAR box was used.

The frozen mechanism name is:

`TERG_V1_SET_VALUED_TEMPORAL_EXPLANATION_MECHANISM`

The claim is limited to conditional SAR image-domain response structure. Optical lifecycle/corridor information supplies explanation incidence, time/azimuth support, and search organization. It does not supply SAR range, identity, or final localization authority.

## What changed

### 1. Physical graph authority and optical incidence are separate

- Physical node: `(run_id, frame_index, region_id)`.
- Physical SAR response regions: 3,056 unique rows.
- Optical-conditioned incidence rows: 4,328.
- Explanation-set incidence rows: 18,937.
- Shared response now means multiple optical incidences reference the same physical SAR node.

The previous 4,328 conditioned graph nodes no longer impersonate 4,328 independent physical responses. The 1,272 excess conditioned rows remain as incidence, not duplicated physical authority.

### 2. Connectivity is set-valued and threshold-free in D0R

The upper graph preserves all 2,644 frozen D0 P0-positive physical edges. Every edge retains its raw evidence profile: soft intersection, source retention, destination explained fraction, soft IoU, P0 residual state, deformation, topology, boundary/truncation, local dominance, and bridge dependency.

No new numeric threshold was introduced. The lower core is the categorical intersection of:

- mutual local dominance;
- exclusive one-to-one supported topology;
- `SAR_P0_RESIDUAL_COMMON_COMPATIBLE`;
- no deformation evidence;
- no boundary/truncation censoring.

This yields 111 lower-core edges and 2,533 upper-optional edges. Optional does not mean rejected. It means the edge remains a legal continuation hypothesis but does not receive unconditional lower-core topology authority.

### 3. Components are represented as families

- Upper possible component families: 3,414, one-to-one with all frozen D0 components.
- Lower-core components inside those envelopes: 18,314.
- Optional bridge dependency rows: 13,724.

Each family stores a lower-core partition and an upper possible connected envelope. It does not select a unique path, component pair, identity, or target assignment.

### 4. Relative order is a real relation set

All 85 order profiles now retain `POSSIBLE_RELATION_SET` plus per-frame support extents.

For the 78 profiles with physical shared response:

- 27 retain shared plus partial-direction information;
- 51 retain shared plus competing directions;
- 0 are pure shared-only.

Thus `ANY_SHARED => WHOLE_SEGMENT_UNDEFINED` is removed. Shared, LEFT, RIGHT, and OVERLAP can coexist, with shared-frame, definite-order-frame, overlap-frame, competing-direction-frame, and unavailable-frame sets recorded separately. No best family pair and no weighted vote is used.

### 5. Split/merge are topology hypotheses, not hard events

Physical edges can carry coexisting hypotheses including continuation, one-to-many, many-to-one, deformation, boundary censoring, and fragmentation/weak-topology uncertainty. `split_merge_hard_event_claimed` is false for every edge.

The high-IoU split-like and merge-like cases remain visually continuous while local contour protrusions change. The V1 representation therefore preserves the topology possibility without calling it a unique PERSON/SAR event.

### 6. Stratification is not contraction

- Temporal stratification is available in 87 of 88 explanation sets.
- Actual pruned nodes: 0.
- Actual pruned families: 0.
- Counterfactual contraction performed: false.

The burden profile reports physical-region incidence, possible families, lower-core components, multi-frame/isolated structure, complete-lifecycle possibilities, shared structure, and optional-bridge dependence. These units are not collapsed into a single candidate-reduction number.

### 7. Timing authority is explicit

Known:

- nominal SAR grid median period: approximately 33 ms;
- nominal optical grid median period: approximately 56 ms;
- exposed nominal query-grid residual: within ±23 ms in the development records.

Unknown:

- cross-modal synchronization offset;
- any physically bounded acquisition-derived synchronization interval.

The unverified ±250 ms default is removed from the repaired relation table and is not replaced with an invented ±N ms. Available event pairs therefore output `TIMING_RELATION_SET_UNDER_UNCALIBRATED_SYNC`; exact temporal order is not authorized.

## Direct real-image answers

### Where did Boolean connectivity create unreasonable components?

Phase-A found 153 weak-edge bridge instances, corresponding to 39 conditioned graph-edge IDs and 27 unique physical edges. Examples include R01ZF F67–F68, F25–F26, and F52–F53. In these packs, a local tip/end contact could merge tens of frames on each side into one global component even though the SAR images did not justify whole-region equivalence.

### How are those cases represented after repair?

The weak physical relation remains in the upper graph with its evidence vector and continuation/weak-contact/topology hypothesis set. It is absent from the lower core. If it is topology-critical, the family stores an explicit optional bridge dependency rather than silently forcing a core merge.

### Which weak edges remain legal?

All Phase-A weak bridge edges remain legal upper edges. None receives lower-core authority. D0R did not delete them and did not tune a threshold against reference outcomes.

### Are component families more faithful than Boolean components?

Yes for the audited development cases. The upper envelope preserves every frozen D0 component, while the lower partition exposes how much connectivity depends on categorical common-compatible relations versus optional deformation, topology competition, or weak contact. This retains both continuity possibility and uncertainty.

### How much shared/order information is retained?

All 78 shared profiles preserve their non-shared information: 27 partial-direction and 51 competing-direction profiles. The partial-direction R02ZF F481–F485 case remains `{OVERLAP,RIGHT,SHARED}`; the competing case remains `{LEFT,OVERLAP,RIGHT,SHARED}` with per-frame extents.

### Is physical-region duplication removed?

Yes at the graph-authority layer: 3,056 unique physical nodes are referenced by 4,328 optical-conditioned incidence rows. Shared semantics comes from incidence multiplicity, not copied physical nodes.

### Is split/merge certainty reasonably downgraded?

Yes. Split-like and merge-like labels are retained only inside topology hypothesis sets, commonly alongside deformation and fragmentation/weak-topology uncertainty. No hard split/merge event is asserted.

### What does timing know and not know?

It knows nominal sampling grids and the exposed query-grid residual. It does not know a bounded cross-modal acquisition offset. Consequently, exact cross-modal before/after order is unavailable without calibration.

### Does temporal stratification remain real?

Yes. Multi-frame and isolated/short possible families coexist in 87 of 88 sets. This is structural organization, not deletion and not proven post-reference discrimination.

### What human-visible structure remains underexpressed?

The R01ZF F0–F15 selected response is visibly continuous through all 16 frames, but only 2 of its 15 links satisfy the deliberately conservative lower-core categorical rule; 13 remain optional because deformation or non-common residual interpretations coexist. V1 preserves the complete upper family and the visual continuity evidence, but cannot promote it to definite identity without adding authority not present in the frozen descriptors.

The partial F0–F4 response is an important counterexample: it is a separate visually persistent SAR response, and its F0 physical region is grounded post-reference to another SAR target. It is not a broken or rejected fragment of the selected response.

## Grounding boundary

The selected complete family has 4/4 reference frames supported in post-reference diagnosis, and its intermediate real images remain visually continuous. This supports reality alignment of the explanation family but does not establish runtime selection, cross-modal identity, or final localization. Grounding tables are physically separated under `post_reference`; representation construction uses only `pre_reference` inputs.

## Freeze rationale

TERG-v1 is ready for independent confirmation because the six Phase-A representation defects are repaired without threshold search, weighted scoring, reference-fitted selection, or held-out access, and the repaired semantics remain consistent with the audited real SAR cases. The open limitation is explicit and conservative: human-visible continuity can be stronger than lower-core categorical authority, so V1 keeps such structure possible rather than claiming identity.
