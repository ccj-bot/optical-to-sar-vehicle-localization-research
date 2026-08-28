# M0B1-V2 corresponding-boundary cross-modal direction protocol

- Stage: `M0B1_V2_CROSS_MODAL_DIRECTION_DISCRIMINATION`
- Protocol state: `FROZEN_BEFORE_RUN`
- Study role: development-only categorical evidence audit
- Run: R02ZF SAR F472-F494, 22 lag-1 pairs
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- `old_work` dependency: `NO`

## 1. Immutable predecessors and scientific boundary

The following states remain unchanged:

- `M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT`
- `M0B1_R_INTERVAL_OPERATOR_SEMANTIC_MISMATCH_CONFIRMED`

M0B1-V2 does not reinterpret the old all-pairs interval operator as a PASS.  It
independently versions the corresponding-boundary descriptor and asks whether
direction provides categorical discrimination beyond frozen static geometry
and frozen M0A SAR-only transport.

No magnitude fit, weighted fusion, classifier, tracker, Hungarian assignment,
identity assignment, unique path, factor graph, runtime pruning, P2, final SAR
center, or final SAR box is permitted.

## 2. Authority and supersession

When sources disagree, precedence is:

1. current code/schema and independent validators;
2. frozen materialized artifacts;
3. current frozen protocol;
4. older narrative documents.

The latest pixel-level shell-region topology supersedes coarse angular-extent
intersection.  Raw `raw_track_fragment_id` is the runtime-legal optical branch;
`optical_person_id` remains a `GT_BLIND_OFFLINE_CONTINUITY_PROXY` and is not
used for identity.

## 3. Pre-reference inputs and isolation

The pre-reference stage may read only frozen M0B1/M0B1-R/M0A pre-reference
artifacts and the GT-blind detected optical hypothesis table.  It must not open
manual SAR reference, post-reference supported-edge tables, physical target
identity, or assignment products.

All descriptors, hypotheses, timing conditions, global baselines, controls,
the optical diversity atlas, pre-reference figures, and their hashes are
materialized with `reference_loaded=false` before reference reveal.

## 4. Optical descriptor V2

For optical support `I_o(t)=[L_o(t),U_o(t)]`:

- `d_left_o=L_o(t2)-L_o(t1)`
- `d_right_o=U_o(t2)-U_o(t1)`
- `d_mid_o=((L_o(t2)+U_o(t2))-(L_o(t1)+U_o(t1)))/2`
- `d_width_o=(U_o(t2)-L_o(t2))-(U_o(t1)-L_o(t1))`

Tolerance is fixed at `1e-12 degree` for numerical comparison only.

- both boundaries positive: `OPTICAL_COHERENT_POSITIVE_SHIFT`
- both negative: `OPTICAL_COHERENT_NEGATIVE_SHIFT`
- both numerical zero: `OPTICAL_NO_RESOLVED_SHIFT`
- otherwise: `OPTICAL_DEFORMATION_OR_MIXED_SHIFT`

Same-sample, fragment-break, observation-unavailable, mapping-unavailable, and
static-infeasible states remain unavailable and are never converted to zero.
Spatial support extent is not measurement uncertainty.

## 5. SAR structural descriptor

For q95 response-region angular support `I_s(t)=[L_s(t),U_s(t)]`, compute the
same four boundary/midpoint/width descriptors.  States are:

- `SAR_COHERENT_POSITIVE_SHIFT`
- `SAR_COHERENT_NEGATIVE_SHIFT`
- `SAR_NO_RESOLVED_SHIFT`
- `SAR_DEFORMATION_OR_MIXED_SHIFT`
- `SAR_DYNAMIC_UNAVAILABLE`

Split, merge, and shared topology are not forced into rigid motion. `d_mid_s`
is a geometric response-support descriptor, not PERSON true bearing.

## 6. Direction compatibility

Compatibility is defined only when both sides are coherent:

- same sign: `DIRECTION_CONCORDANT`
- opposite sign: `DIRECTION_CONTRADICTORY`
- mixed/deformation/no-resolved: `DIRECTION_STRUCTURALLY_INDETERMINATE`
- unavailable dynamic input: `DIRECTION_UNAVAILABLE`

Contradiction is an evidence state and never rejects a hypothesis.

## 7. Scene-common audit and global baseline

The deterministic optical temporal neighborhood is:

`timing_condition + source decoded optical frame + destination decoded optical frame`.

Within a neighborhood, deduplicate by raw fragment and count positive,
negative, mixed, zero, and unavailable states.  A global direction baseline is
the unique majority among coherent positive/negative states.  A tie or absence
of coherent states is `GLOBAL_DIRECTION_INDETERMINATE`.  Mixed states are
reported but do not vote as a coherent sign.

Report active fragment count, majority fraction, Shannon entropy, state
diversity, disagreement fraction, and per-fragment sequences.  Branch-specific
direction is compared directly with this global baseline.  No weighted score
is constructed.

## 8. Controls

Pre-reference controls remain direction-blind:

1. frozen M0A structural matched SAR alternatives;
2. frozen M0B1 static-shell-matched composite controls;
3. frozen M0B1 alternative raw-fragment controls, explicitly not called known
   wrong target branches without a legal evaluator.

Control selection may use static shell/region burden, topology, boundary,
truncation, availability, and initial angular relation, but not direction,
manual target, supported status, or post-reference information.

## 9. Timing conditions

Use the already frozen five fixed conditions:

- `NOMINAL`
- `SAR_SHIFT_MINUS_1`
- `SAR_SHIFT_PLUS_1`
- `OPTICAL_SHIFT_MINUS_1_NOMINAL_STEP`
- `OPTICAL_SHIFT_PLUS_1_NOMINAL_STEP`

No best shift is selected, fitted, or written back.  Synchronization remains
`NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED`.

## 10. GT-blind optical diversity atlas

Across all exposed runs in the frozen optical hypothesis artifact, use only
`box_source=DETECTED`, raw fragment IDs, and consecutive distinct observations
within each fragment.  Report per-run/per-fragment states, exact local-window
diversity, sign reversals, fragment availability, and every future-design
window satisfying the predeclared eligibility:

`active fragments >= 2 AND positive >= 1 AND negative >= 1`.

The atlas is for future experiment design only and cannot trigger additional
SAR reference evaluation in this task.

## 11. Post-reference pairwise decision

After the pre-reference validator passes, reveal frozen M0A supported edges and
reference-unsupported structural alternatives.  For the same raw fragment and
timing condition:

- supported concordant + null contradictory: `DIRECTION_FAVORS_SUPPORTED`
- supported contradictory + null concordant: `DIRECTION_FAVORS_NULL`
- otherwise: `DIRECTION_NO_DECISION`

Perform the same comparison using the global baseline.  Report whether branch
direction changes any decision relative to global direction.

SAR-only evidence remains the frozen M0A pairwise outcome and is not fused with
direction.  Joint categories are:

- SAR-only ambiguous + direction favors supported: `DIRECTION_RESCUE`
- SAR-only favors supported + direction favors supported: `DIRECTION_CONFIRMATION`
- opposing decisions: `DIRECTION_CONFLICT`
- direction no decision while SAR-only decides: `DIRECTION_REDUNDANT_NO_DECISION`
- neither decides: `DIRECTION_NO_INFORMATION`

## 12. Raw-fragment evaluator audit

The repository is audited for a traceable
`manual/physical target <-> raw_track_fragment_id` source.  If absent, an
`OFFLINE_VISUAL_RAW_FRAGMENT_TARGET_REVIEW` interface is materialized only
after hypothesis freeze.  Review states are:

- `CONFIRMED_TARGET_BRANCH`
- `LIKELY_TARGET_BRANCH`
- `AMBIGUOUS_MULTIPLE_BRANCHES`
- `NOT_TARGET_BRANCH`
- `UNRESOLVED`

Without an authoritative cross-modal identity cue, packs must remain
`UNRESOLVED`; no guess, re-stitch, representation change, timing change, shell
change, region change, or raw-track writeback is allowed.

## 13. Cluster-aware reporting

Rows are descriptive, not independent samples.  Report SAR frame pair,
supported base edge, raw fragment, optical pair, target/reference group, and
run/window clusters.  Materialize exact wins/losses/ties and leave-one-frame-
pair-out results.  No row-level p-value is permitted.

## 14. Outcome states

Allowed primary/secondary states include:

- `M0B1_V2_CROSS_MODAL_DIRECTION_INCREMENTAL_SIGNAL_OBSERVED_DEVELOPMENT_ONLY`
- `M0B1_V2_DIRECTION_SIGNAL_SCENE_COMMON_NOT_BRANCH_SPECIFIC`
- `M0B1_V2_DIRECTION_DISCRIMINATION_NOT_ESTABLISHED`
- `M0B1_V2_STATIC_GEOMETRY_REEXPRESSION_DOMINANT`
- `M0B1_V2_SYNC_SENSITIVE`
- `M0B1_V2_RAW_BRANCH_EVALUATION_UNRESOLVED`
- `M0B1_V2_BRANCH_SPECIFIC_DIRECTION_SIGNAL_OBSERVED`
- `M0B1_V2_INCREMENTAL_BEYOND_SAR_ONLY_NOT_ESTABLISHED`

Branch-specific signal requires correct-vs-wrong raw-fragment evidence that
cannot be reproduced by the global direction baseline.  It cannot be inferred
from supported SAR edges alone.

The counterfactual admissibility diagnostic is gated on at least one
`DIRECTION_RESCUE` or established branch-specific signal.  If the gate fails,
it is not run.

## 15. Visual evidence and stop

Post-reference rendering uses 17 deterministic case slots.  Missing categories
are explicitly `CATEGORY_NOT_OBSERVED`.  Real images and aggregate tables are
reviewed together.

After protocol, pre-reference freeze, validation, post-reference evaluation,
visual QA, independent validation, report, commit, and push, stop.  Do not
enter magnitude, residual-motion modeling, pruning, factor graphs, tracking,
P2, or final localization.

