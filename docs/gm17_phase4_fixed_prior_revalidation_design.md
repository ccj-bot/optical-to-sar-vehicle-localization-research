# Purpose And Boundary

Status: Phase4 fixed-prior revalidation experiment design only.

This document defines how a future Phase4 round should design fixed-prior revalidation under frozen inputs and strict audit gates. It does not authorize execution.

Phase4 fixed-prior revalidation is intended to test whether audited complete-vehicle factors can explain candidate selection behavior under predeclared, non-learned priors. It is not:

- training;
- calibration;
- learned-weight estimation;
- candidate-bank expansion;
- GM17 mainline replacement;
- partial-visibility implementation;
- near-field implementation;
- OOF calibration;
- new model deployment.

GM17 remains a staged evidence source, not the final model template. B patch reproduction is diagnostic consistency evidence only and must not be treated as final physical-model proof.

The only output of this round is this design document. No experiment, inference run, metric computation, candidate-bank change, code change, staging, commit, or push is authorized.

# Research Questions

Phase4 fixed-prior revalidation should answer design-level questions before any execution round:

1. Can the audited complete-vehicle factors explain candidate selection under fixed priors?
2. Which factor groups contribute stable evidence without learned weights?
3. Which factors expose failure modes, branch leakage, patch dependency, or double-counting?
4. Does the design avoid copying B patch action behavior?
5. Does the design preserve inference/evaluation separation from input construction through audit reporting?
6. Can selected-candidate behavior be reviewed without treating GM17 as the final system architecture?
7. Which controls must be accepted by `AuditReleaseAgent` before any runtime Phase4 execution?

# Frozen Inputs And Gates

Phase4 execution may be considered only if all inputs and gates are frozen before inference.

Required frozen inputs:

- fixed v2.2 candidate bank;
- candidate-level fields allowed by the Phase3 acceptance matrix;
- row-level and track-level inference-safe metadata needed for allowed factors;
- predeclared fixed-prior factor inclusion masks;
- predeclared potential, cost, clipping, and missing-value policies;
- repository-relative manifest of all input tables and hashes, to be created only in a future execution round.

Required gates:

- candidate bank hash gate must pass before any inference;
- inference/evaluation field separation must pass before any inference;
- allowed baseline files must be explicitly listed in the future execution manifest;
- no untracked historical material may be used;
- no runtime output, archive, task script, tool script, old prompt dump, or auth/proxy material may be used as evidence;
- no candidate-bank changes are allowed;
- no learned weights are allowed;
- no OOF calibration is allowed;
- no GM17 mainline replacement is allowed;
- no partial-visibility or near-field branch activation is allowed.

Evaluation-only fields, including GT, oracle, IoU, center error, condition labels, truncation labels, occlusion labels, and final annotation fields, must remain outside inference inputs and inference outputs. They may be joined only after inference for audit and evaluation reports.

# Allowed Factors

The following factors are the only allowed active fixed-prior candidates for future Phase4 design. They remain conditional and must satisfy their Phase3 controls before any execution.

| Factor | Phase4 role | Required control condition |
|---|---|---|
| `geometry_factor` | Candidate-level complete-vehicle node cost. | Declare which shell and escape terms belong to geometry and which belong to SAR structure before execution. Prevent geometry/SAR shell double-counting. |
| `direction_factor` | Candidate-level direction compatibility cost. | Keep signed direction evidence separate from source-family trust. Do not count direction assumptions both through `direction_factor` and `source_factor`. |
| controlled non-visible `source_factor` | Candidate-level source-family prior for `base`, `wedge`, `bidirectional`, and `track_signed` only. | Visible source behavior remains veto/uncertainty-only and inactive as a full-center source. `directional_shell_score`, `track_escape_evidence`, and `signed_direction_match` may be used only as controlled diagnostic or gated support context unless ownership is explicitly declared. |
| `optical_temporal_factor` | Soft row/track prior over complete-vehicle candidate state. | Keep optical temporal evidence as a soft prior only. It must not hard-lock, overwrite, or directly generate a full center. |
| `transition_factor` | Track-level edge continuity cost between adjacent candidate states. | Keep transition as edge continuity, not as optical-temporal duplication and not as a release gate. Smoothness overlap with `optical_temporal_factor` must be audited. |

All allowed factors must use fixed, predeclared transforms and no learned weights. Any factor missing required fields must follow the predeclared missing-value policy rather than being silently optimized or tuned.

# Excluded Or Diagnostic-Only Factors

The following factors are excluded from active Phase4 scoring.

| Factor | Phase4 status | Reason |
|---|---|---|
| `sar_structure_factor` | Diagnostic review surface only. | It overlaps with geometry shell evidence and `uncertainty_factor`. It carries medium patch-dependency risk because accepted B patch behavior is SAR-uncertainty based. It may appear only in support-vs-uncertainty separation review until ownership and patch risks are resolved. |
| `uncertainty_factor` | Diagnostic review surface only. | It overlaps with SAR ambiguity, direction conflict, final arbitration behavior, and B patch protection. It may appear only in uncertainty-route review until support-vs-uncertainty and patch risks are separated. |
| `final_arbitration_factor` | Blocked from active scoring and calibration. | It has high B patch dependency and can copy B patch action behavior. It may remain diagnostic consistency evidence only and must not be treated as physical-model proof. |
| `visibility_factor` | Diagnostic-only and Phase7-bound. | Visible support may act only as factor, veto, or uncertainty evidence. It must not generate a full center or act as a full-center source. |
| `missing_extent_factor` | Diagnostic-only and future-phase. | Current inference-safe schema, valid range, transforms, costs, and clipping are not standardized. It must not enter the complete-vehicle mainline. |
| `visible_full_center_offset_factor` | Diagnostic-only and future-phase. | No standardized inference-safe offset schema exists. Visible support must not generate or shift a latent full-vehicle center in Phase4. |

Partial visibility and near-field categories may be referenced only as future-boundary failure categories. They must not be activated in Phase4.

# Fixed-Prior Factor Graph Design

This section defines design-level structure only. It is not implementation code.

Node definition:

- Each candidate node represents one fixed candidate from the frozen candidate bank for one row/frame.
- Candidate node state may include fan-polar and OBB fields such as `r`, `cross`, `az`, `heading`, `w`, `h`, source family, and direction state when available and inference-safe.
- Each node must have a stable `candidate_id` join key and row identity.

Edge definition:

- Each edge links candidate nodes between adjacent frames inside the same track.
- Edge construction may use only inference-safe track/frame metadata and candidate state fields.
- No eval-only fields may be used to create edges.

Candidate-level costs:

- Allowed node costs may come from `geometry_factor`, `direction_factor`, and controlled non-visible `source_factor`.
- Each included factor converts a predeclared potential into cost using the documented fixed transform, for example `-log(potential + eps)`.
- Factor inclusion must be declared before inference.
- Excluded factors must not contribute active node cost.

Track-level transition costs:

- `transition_factor` may contribute edge costs between adjacent candidate states.
- `optical_temporal_factor` may contribute a soft row/track prior, but must not duplicate transition continuity unless the ownership split is declared.
- Transition costs must not act as release decisions.

Fixed-prior combination principle:

- Phase4 uses fixed, predeclared factor inclusion and cost combination rules.
- No factor coefficient may be learned from evaluation labels.
- No coefficient may be tuned using Phase4 metric outcomes.
- No OOF split, ranker, CRF, or calibrated model may be introduced.
- Any scalar factor constants must be declared before inference and treated as design priors, not learned weights.

Missing-value policy:

- Missing required state fields for geometry or transition block the affected factor path for that row or edge according to the predeclared policy.
- Missing temporal prior defaults to neutral soft prior.
- Unknown non-visible source defaults to conservative low trust or diagnostic `WARN`.
- Missing excluded diagnostic fields must not cause active scoring fallback.

Clipping policy:

- Potentials must be clipped to `[eps, 1]` before `-log` cost conversion.
- Extreme edge costs may be capped only if the cap is predeclared and not tuned from evaluation outcomes.
- Clipping must be applied consistently across ablations.

No learned weights:

- Fixed-prior revalidation is not weight learning.
- Any future calibrated weights must wait until Phase5 gates pass.

# Ablation Matrix

The future execution round should predeclare ablations before any inference run. The following matrix is a design plan only and must not be executed in this round.

| Ablation ID | Active fixed-prior factors | Purpose |
|---|---|---|
| `A01_geometry_only` | `geometry_factor` | Test geometry support without direction, source, temporal, or transition effects. |
| `A02_direction_only` | `direction_factor` | Test signed direction compatibility alone. |
| `A03_non_visible_source_only` | controlled non-visible `source_factor` | Test source-family prior without visible source behavior. |
| `A04_optical_temporal_only` | `optical_temporal_factor` | Test soft temporal prior without node geometry or edge transition. |
| `A05_transition_only` | `transition_factor` | Test track continuity alone. |
| `A06_geometry_direction` | `geometry_factor`, `direction_factor` | Test basic complete-vehicle node compatibility. |
| `A07_geometry_direction_source` | `geometry_factor`, `direction_factor`, controlled non-visible `source_factor` | Test candidate-source contribution after direction and geometry controls. |
| `A08_geometry_direction_optical_temporal` | `geometry_factor`, `direction_factor`, `optical_temporal_factor` | Test soft optical temporal effect without transition edge duplication. |
| `A09_geometry_direction_transition` | `geometry_factor`, `direction_factor`, `transition_factor` | Test edge continuity after basic node compatibility. |
| `A10_all_allowed_fixed_priors` | `geometry_factor`, `direction_factor`, controlled non-visible `source_factor`, `optical_temporal_factor`, `transition_factor` | Test the full allowed complete-vehicle fixed-prior design. |

Excluded factors must remain excluded in all ablations. In particular, `sar_structure_factor`, `uncertainty_factor`, and `final_arbitration_factor` must not enter active scoring through hidden proxy fields.

# Metrics And Grouped Analysis

This section defines future metrics and grouped analysis only. It does not run metrics.

Inference-side outputs:

- selected candidate ID per row/frame;
- selected path per track when transition is active;
- active factor costs used for the selection;
- missing-value flags for included factors;
- manifest of active ablation ID and fixed-prior settings.

Evaluation-side metrics:

- candidate selection agreement with staged GM17 selected-prediction references;
- center error only if evaluation-only labels are joined strictly after inference;
- IoU or rotated-IoU only if evaluation-only labels are joined strictly after inference;
- selected-prediction behavior summaries by ablation.

Grouped analysis:

- group by source family, separating non-visible source families from visible source behavior;
- group by ambiguity/conflict state only as audit-side grouping if those fields are not active scoring inputs;
- group by track and frame order;
- group by missing-value policy outcome;
- group by failure taxonomy category.

Inference/evaluation separation:

- Eval-only fields must not influence candidate scoring, path construction, factor inclusion, or missing-value policy.
- Evaluation labels may be joined only after inference outputs have already been generated.
- Reports must clearly mark inference-safe fields, diagnostic-only fields, future fields, and eval-only fields.

No new performance conclusion should be reported unless it is tied to a future boundary-audited Phase4 execution artifact.

# Failure Taxonomy

Expected failure categories for future Phase4 analysis:

| Failure category | Description | Boundary |
|---|---|---|
| Geometry/SAR shell double-counting | Geometry escape or shell evidence may duplicate SAR structure evidence. | Active scoring must declare geometry ownership and keep SAR structure diagnostic-only. |
| Source-direction double-counting | Source family trust may repeat signed direction assumptions. | Source prior must remain source-only unless direction conditioning is explicitly owned and audited. |
| Optical-temporal/transition smoothness double-counting | Soft temporal prior and edge continuity may both reward smooth but wrong paths. | Keep temporal prior and transition edge roles separated. |
| B patch reproduction risk | Design may appear valid by copying B patch behavior. | `final_arbitration_factor`, `patch_action`, and B patch action-copying must remain outside active scoring. |
| Ambiguous SAR evidence | SAR ambiguity may explain protection behavior but is not cleanly separated from uncertainty. | `sar_structure_factor` and `uncertainty_factor` remain diagnostic review surfaces only. |
| Partial visibility false support | Visible fragments may be mistaken for full-center evidence. | Visible support cannot generate full center and remains Phase7-bound. |
| Near-field geometry regime mismatch | Near-field may indicate a geometry-mechanism shift rather than ordinary occlusion. | Near-field is a future-boundary category only; it cannot modify the candidate bank or replace the selector. |

# Expected Artifacts For Future Execution

The future execution round may define or generate the following artifacts after gates pass. This document does not create them.

- fixed-prior config manifest;
- candidate bank hash report;
- formal allowed-field manifest;
- inference/evaluation leakage audit report;
- ablation manifest;
- inference output table without eval-only fields;
- factor cost decomposition table;
- track-level selected path table;
- evaluation-only metric report after inference;
- grouped failure report;
- B patch copying risk review;
- visualization audit pack;
- AuditReleaseAgent boundary report;
- AuditReleaseAgent release decision.

All future artifacts must be repository-relative, reviewed for sensitive or runtime-only material before commit, and separated from unreviewed `tasks/`, `tools/`, `output/`, `artifacts/`, and `archive/` content.

# GO/NO-GO Gate For Phase4 Execution

Phase4 execution is `NO-GO` until all of the following are true:

- candidate bank is frozen and hash-checked;
- field leakage audit passes before inference;
- factor ownership is declared for geometry/SAR shell terms, direction/source assumptions, and temporal/transition smoothness;
- no B patch action copying is present in active scoring;
- `sar_structure_factor`, `uncertainty_factor`, and `final_arbitration_factor` are excluded from active scoring;
- `visibility_factor`, `missing_extent_factor`, and `visible_full_center_offset_factor` are excluded from active scoring;
- partial visibility and near-field branches remain inactive;
- missing-value and clipping policies are predeclared;
- all ablations are predeclared before execution;
- no learned weights, OOF calibration, ranker, CRF, or selector replacement is introduced;
- inference/evaluation separation is accepted by `AuditReleaseAgent`;
- `AuditReleaseAgent` accepts the Phase4 execution design and boundary gate.

Only after these conditions pass may a separate write-enabled execution-scaffold design round be considered. That later round still must not run experiments unless explicitly authorized after the gates pass.

# Remaining Blockers

The Phase4 design carries forward Phase3 blockers:

| Blocker | Phase4 carry-forward meaning |
|---|---|
| `B001` leakage and boundary gate | Every future inference-facing output must pass field-origin, leakage-class, and join-stage audit. Runtime artifacts and generated tables remain unaudited until future execution review. |
| `B002` geometry/SAR structure double-counting | Geometry/SAR shell ownership must be declared before any geometry-active ablation. |
| `B003` direction/source double-counting | Source priors must not duplicate signed direction evidence unless explicit ownership is declared. |
| `B004` visible-source branch isolation | Visible source behavior must remain veto/uncertainty-only and not a full-center source. |
| `B005` SAR structure/uncertainty double-counting and patch dependency | `sar_structure_factor` and `uncertainty_factor` remain diagnostic-only review surfaces until separation is accepted. |
| `B006` final arbitration B patch dependency | `final_arbitration_factor` remains blocked from active scoring and calibration. |
| `B007` optical-temporal/transition smoothness double-counting | Temporal prior and transition edge ownership must be separated before combined ablations. |
| `B008` partial-visibility branch isolation | Partial visibility factors remain inactive in complete-vehicle Phase4. |
| `B009` future partial-visibility schema missing | Missing extent and visible/full-center offset remain future Phase7 schema work. |
| `B010` near-field future route boundary | Near-field is future-boundary only; it cannot modify the candidate bank, replace the selector, or enter OOF calibration. |

# Recommended Next Round

Recommended next round:

1. Human review of this Phase4 fixed-prior revalidation design document.
2. If accepted, a separate write-enabled round may create a Phase4 execution scaffold design document or manifest plan.
3. Experiment execution must still remain blocked until the GO/NO-GO gate passes and the user explicitly authorizes execution.

The next round should continue to preserve:

- GM17 as staged evidence, not final model template;
- B patch reproduction as diagnostic consistency evidence only;
- Phase4 as fixed-prior revalidation, not calibration;
- OOF calibration as blocked;
- visible support as non-generative for full center;
- missing extent as diagnostic-only/future-phase;
- near-field as future-boundary and not candidate-bank or selector replacement work.
