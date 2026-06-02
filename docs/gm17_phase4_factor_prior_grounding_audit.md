# GM17 Phase4 Factor Prior Grounding Audit

Date: 2026-06-02

Status: Phase4 factor prior grounding audit for human review. This document is a research-mainline synthesis only. It does not authorize experiments, inference runs, metric computation, training, calibration, data-file modification, candidate-bank generation, candidate-bank modification, algorithm-code modification, staging, commit, or push.

## 1. Purpose

This document audits whether the candidate-selection behavior exposed by GM17 can be grounded as structured, interpretable factor priors for a future hierarchical factor graph.

The audit converts three kinds of evidence into factor-level research judgments:

- GM17 weighted-scoring and selected-behavior evidence;
- external literature and method-family evidence;
- local data observability from the Phase4 inventory, preview, manifest, and raw-scene provenance documents.

The data inventory supports factor grounding, but it is not the research contribution. A candidate bank is an experimental container used to freeze proposal generation so candidate-selection factors can be audited. A001 is a GM_RM017-only candidate-bank candidate unless human review approves a narrower Phase4A pilot scope. It is not the full research dataset and not the research goal.

## 2. Research Mainline Restatement

The project studies optical-to-SAR vehicle localization as candidate selection over a frozen SAR candidate bank.

The original GM17 line used weighted scoring terms to rank and select candidates. It exposed useful structure, but the new research direction is not to preserve GM17 as a final template. The new direction is to decompose weighted candidate scoring into a hierarchical factor graph with explicit factor ownership, interpretable evidence routes, and inference/evaluation separation.

GM17 now provides:

- staged evidence;
- candidate structure and feature fields;
- failure cases;
- selected-behavior references;
- patch-dependency risk exposure;
- diagnostic examples for future factor design.

GM17 is not the final physical model, not the final architecture, and not a mainline to keep patching indefinitely. B patch reproduction is diagnostic consistency evidence, not physical proof. Phase4 is fixed-prior revalidation of audited factors, not learned calibration, OOF training, ranker training, candidate-bank expansion, or GM17 replacement.

## 3. From GM17 Weighted Scoring To Hierarchical Factors

The original weighted-scoring line compressed several evidence sources into a single candidate score. That is useful for staged behavior, but it hides ownership:

- geometry evidence can be mixed with SAR structure evidence;
- direction evidence can be mixed with source-family trust;
- temporal priors can be mixed with track smoothness;
- uncertainty can become an implicit final arbitration gate;
- patch-like behavior can look like a physical model if it reproduces selected outputs.

A hierarchical factor graph reframes the problem as structured candidate-state inference. Candidate nodes represent fixed candidate states for a row/frame. Node factors can score candidate geometry, signed direction compatibility, source-family provenance, and optical-temporal soft priors. Edge factors can score track-level continuity between adjacent candidate states. Diagnostic surfaces can be preserved without becoming active factors.

This separation improves the science in four ways:

- Interpretability: each factor states what physical or procedural evidence it owns.
- Physical meaning: geometry, direction, temporal context, SAR ambiguity, and source provenance are not treated as interchangeable score terms.
- Auditability: inference-safe fields, diagnostic-only fields, and eval-only labels can be checked independently.
- Future learning discipline: learned weights or calibration become meaningful only after fixed-prior factor behavior is coherent and leakage-free.

Post-inference evaluation remains outside the graph. GT boxes, oracle fields, IoU, center error, condition labels, truncation labels, occlusion labels, and final annotation fields may be joined only after inference outputs already exist.

## 4. Literature And External Evidence Role

External literature supports factor grounding, not direct model import.

SAR and remote-sensing OBB work supports `geometry_factor` by giving oriented-box, angle, and object-state schema references. SIVED is the strongest vehicle-specific OBB/schema reference. SAR detector papers and rotated-detector repositories remain schema, protocol, and ablation references only; detector training, proposal generation, and detector confidence are not Phase4-active evidence.

Tracking-by-detection, MAP data association, Viterbi, and min-cost-flow literature support `transition_factor` as path selection over fixed candidates. This is algorithm-structure evidence: it helps define edge costs and path inference, but it does not authorize learned association embeddings, detector confidence, or imported tracking systems.

Optical-SAR matching literature supports `optical_temporal_factor` as a soft cross-modal prior and a source of alignment-failure concepts. Most of that literature is learned matching or registration, so it is mainly future learning/calibration background. It cannot become fixed-prior Phase4 scoring through learned correspondence, pseudo-labels, or alignment metrics.

Amodal, partial-visibility, and near-field radar literature supports future routes only. It helps frame missing extent, visible/full-center mismatch, and geometry-regime reliability, but it does not activate partial visibility or near-field modeling in Phase4A.

External repositories are method references. They are not direct code imports, not candidate-bank generators, not detector-confidence sources, and not learned-weight sources for Phase4A.

## 5. Data Evidence Role

The local data evidence determines observability and feasibility, not the research goal.

Key data facts from the current local audits:

- Raw scene folders exist for GM_RM011, GM_RM017, and GM_RM019 under `D:\profile\research\data`.
- Each of GM_RM011, GM_RM017, and GM_RM019 has 368 optical PNG frames and 766 SAR PNG frames.
- A019 `final_gt_working.csv` covers GM_RM011, GM_RM017, and GM_RM019 and remains eval-only.
- A021 `visibility_condition_working.csv` aligns one-to-one with A019 target identities and remains eval-only/future-route material.
- A001 `candidate_bank_inference.csv` covers GM_RM017 only: 58251 candidate rows, 205 target identities, 79 SAR frame numbers, and 5 GM17 tracks.
- A005 `gm17_temporal_inference.csv` exists as an optical-to-SAR temporal soft-prior table.
- A007 `signed_escape_posterior_inference.csv` exists as row-level signed direction posterior evidence.
- A008 `candidate_refined_factor_inference.csv` exists as a candidate-factor joined table, but it mixes candidate geometry, direction, posterior context, and diagnostic SAR/uncertainty fields.
- A013 `track_viterbi_selected_inference.csv` exists as selected-behavior reference only, not as a candidate-scoring input.

These facts are enough to ground factor observability for a GM_RM017-only fixed-prior design note. They are not enough to approve A001 as an all-scene Phase4 frozen candidate bank.

## 6. Active Complete-Vehicle Factor Audits

### geometry_factor

Research hypothesis:

Candidate geometry is the core complete-vehicle node factor. A candidate whose full-vehicle state is compatible with the SAR fan-polar geometry and expected OBB state should receive a stronger fixed prior than a candidate whose range, cross-range, azimuth, heading, or size is inconsistent.

Physical/literature grounding:

SAR vehicle OBB and remote-sensing oriented-box literature supports explicit geometry state. The strongest external role is schema/protocol grounding: oriented center, size, heading, fan-polar state, and angle convention.

GM17 feature/structure source:

GM17 exposes candidate geometry through the fixed candidate bank and candidate-factor tables. A001 contains `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross`, and `delta_*` fields. A008 adds diagnostic geometry-like scores such as `refined_geometry_score` and `geometry_escape_refined_score`.

Local observable fields:

- A001: `candidate_id`, `target_identity`, `sar_frame_num`, `gm17_track_id`, `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross`, `delta_r_from_pred`, `delta_cross_from_pred`, `delta_az_from_pred`.
- A008: candidate-level geometry plus diagnostic refined geometry fields.

Inference-safe fields:

- Candidate-bank fields from A001 after human approval and hash/scope gate.
- Candidate `cx`/`cy`, not `final_cx`/`final_cy`.
- Candidate `w`, `h`, `heading`, `r`, `az`, `cross`, and preapproved `delta_*` fields if field origins are accepted.

Diagnostic/eval fields to exclude:

- `final_*`, `gt_*`, oracle fields, IoU fields, center-error fields.
- `refined_geometry_score` and `geometry_escape_refined_score` until ownership versus SAR structure is declared.

Double-counting risk with SAR structure:

Directional shell and escape geometry can encode both geometric compatibility and SAR structural support. Ownership must declare which terms belong to `geometry_factor` and which remain in `sar_structure_factor` diagnostics.

Phase4 readiness:

`ready_for_fixed_prior_design` for a design note and possible GM_RM017-only pilot container after human approval. It is not all-scene ready until candidate-bank scope is settled.

Long-term model value:

Geometry is the anchor of the complete-vehicle branch. If geometry cannot be made clean and interpretable under fixed priors, later direction/source/transition factors will not be scientifically stable.

### direction_factor

Research hypothesis:

Signed direction evidence can distinguish near/base candidates from directional escape candidates and reduce wrong-side candidate selection, provided it is not counted again through source-family trust or uncertainty penalties.

Direction/posterior meaning:

The factor should represent compatibility between a candidate direction state and a row-level signed escape posterior. It should not represent ambiguity, artifact risk, final arbitration, or source-family preference.

GM17 evidence source:

GM17 exposes signed escape posterior and direction-match behavior through A007 and A008. Prior diagnostics show direction evidence is useful but fragile if overused as a global veto.

Local observable fields:

- A007: `P_near`, `P_neg_escape`, `P_pos_escape`, `P_ambiguous`, `P_artifact`, `posterior_confidence`, `posterior_margin`, `signed_escape_decision`.
- A008: `candidate_direction_bin`, `signed_direction_match`, `signed_escape_decision`, posterior fields joined to candidates.

Inference-safe direction fields:

- `candidate_direction_bin`;
- `signed_escape_decision`;
- `signed_direction_match` only as direction evidence;
- `posterior_confidence` and `posterior_margin` only for direction-confidence use;
- `P_near`, `P_neg_escape`, `P_pos_escape` if human review accepts the direction posterior policy.

Diagnostic uncertainty fields to exclude:

- `P_ambiguous`;
- `P_artifact`;
- uncertainty routing fields;
- any final arbitration, patch, or selected-action fields.

Source/direction double-counting risk:

Candidate source families such as wedge, bidirectional escape, and track-signed escape can imply direction assumptions. `source_factor` must not reward the same signed direction evidence again unless the ownership split is explicitly declared.

Phase4 readiness:

`ready_after_mapping`. Direction needs join-key approval, allowed `P_*` policy, and source/direction ownership review.

Long-term model value:

Direction is a key state variable for explaining hard directional failures, but it must remain a structured compatibility factor rather than a hidden veto or source prior.

### controlled non-visible source_factor

Research hypothesis:

Candidate source/provenance can encode the reliability of candidate-generation families if it is limited to non-visible complete-vehicle source families and stripped of geometry/direction evidence that belongs elsewhere.

Candidate source/provenance meaning:

The factor should represent the procedural source family of a candidate, such as base, wedge, bidirectional escape, or track-signed source. It should not represent selected behavior, visible support, direction confidence, or refined geometry score.

GM17 source families:

Observed candidate sources include `base_candidate`, `wedge_joint_candidate`, `bidirectional_escape_candidate`, `track_signed_escape_candidate`, `multi_peak_ray_candidate`, and `visible_support_candidate`. The complete-vehicle source factor should be limited to reviewed non-visible families.

Local observable fields:

- A001/A008/A013: `candidate_source`;
- A013: `source_prior`, but only as diagnostic/reference output unless separately audited;
- A008/A013: `directional_shell_score`, `track_escape_evidence`, `signed_direction_match` as gated context only.

Visible-source isolation:

`visible_support_candidate` and any visible support behavior must remain veto/uncertainty-only or future partial-visibility material. Visible support must not become positive full-center evidence.

Risk of absorbing direction or geometry evidence:

Source labels can encode where a candidate came from, and that process may already reflect geometry and direction assumptions. `directional_shell_score`, `track_escape_evidence`, and `signed_direction_match` must not be counted again as independent source-prior evidence unless ownership is explicitly approved.

Phase4 readiness:

`ready_after_mapping`. It needs source-family normalization, visible/non-visible isolation, and source/direction ownership review.

Long-term model value:

Source provenance can explain why different proposal families have different reliability. It is valuable only if it stays provenance-based rather than becoming a proxy for geometry, direction, or patch actions.

### optical_temporal_factor

Research hypothesis:

Optical-to-SAR temporal prediction can act as a soft prior over complete-vehicle candidate state, helping select candidates consistent with expected trajectory without overwriting SAR evidence.

Optical-to-SAR temporal prior meaning:

The factor should provide row/track-level soft compatibility, not a hard center generator. It can reward candidates near a temporal prediction in fan-polar state, but it must not force the full center or bypass SAR candidate evidence.

Literature support:

Optical-SAR matching and cross-modal alignment literature supports soft-prior interpretation and alignment-failure reasoning. Most direct matching methods are learned, so Phase4A uses the concept, not learned matching weights or correspondence outputs.

Local observable fields:

- A005: `pred_r`, `pred_cross`, `pred_az`, `pred_cx`, `pred_cy`, `pred_w`, `pred_h`, `pred_heading_deg`, `temporal_factor_score`, `gm17_track_id`, `sar_frame_num`;
- A008: `optical_temporal_consistency_score`;
- A001: `temporal_factor_score`.

Soft-prior-only rule:

The factor can provide a fixed-prior compatibility term. It must not generate, overwrite, hard-lock, or directly shift a SAR full-vehicle center.

Risk of generating or overwriting SAR center:

Using `pred_cx`/`pred_cy` as direct final center evidence would collapse candidate selection into temporal prediction. Candidate selection must remain over frozen SAR candidates.

Risk of double-counting with transition:

Temporal priors and transition smoothness can both reward smooth paths. Ownership must define optical-temporal as a row/track prior and transition as an edge continuity factor.

Phase4 readiness:

`ready_for_fixed_prior_design` for a soft-prior design note, after human approval of A005 and field mapping.

Long-term model value:

Optical temporal context is central to cross-modal localization, but fixed-prior Phase4A must show it helps without becoming a center generator or learned registration shortcut.

### transition_factor

Research hypothesis:

Track-level edge continuity can improve candidate selection by enforcing coherent paths through fixed candidate states across adjacent frames.

Edge-factor role:

`transition_factor` is an edge factor, not a node factor. It should score continuity between candidates in adjacent frames within the same track using candidate state fields and predeclared costs.

Literature support:

MAP data association, Viterbi, shortest-path, and min-cost-flow tracking literature provide the strongest external structure for path selection over fixed candidate detections. The support is structural, not a license to import detector confidence or learned tracking weights.

Local observable fields:

- A001/A008: `gm17_track_id`, `sar_frame_num`, `candidate_id`, `r`, `cross`, `az`, `heading`, `w`, `h`;
- A013: selected-reference Viterbi output, path scores, and switch/gate diagnostics for behavior comparison only.

Track/frame requirements:

Human review must approve `gm17_track_id`, numeric `sar_frame_num` ordering, candidate identity stability, and adjacency policy before transition design becomes executable.

Risk of double-counting optical-temporal smoothness:

If optical-temporal prior already rewards path consistency, transition can over-reward smooth but wrong trajectories. Ownership must keep optical temporal as soft row/track prior and transition as edge continuity.

Why it should come after candidate-level factors:

Transition can hide weak node factors by smoothing over local mistakes. Candidate-level geometry, direction, source, and optical-temporal ownership should be stable before edge factors are introduced.

Phase4 readiness:

`ready_after_mapping`. It is suitable for a design note after track/frame ordering and temporal/transition ownership review.

Long-term model value:

Transition is the bridge from independent candidate scoring to hierarchical track inference. It is likely essential for the long-term factor graph, but premature use can mask unresolved factor ownership problems.

## 7. Diagnostic, Blocked, And Future Factor Audits

### sar_structure_factor

Physical relevance:

SAR structure can explain why some candidates have stronger physical support, scattering/shadow consistency, or escape-shell evidence. It is scientifically relevant to SAR vehicle localization.

Local diagnostic fields:

Fields and examples include `directional_shell_score`, `geometry_escape_refined_score`, `track_escape_evidence`, `escape_conflict_score`, and `E_sar_structure`.

Why diagnostic-only:

These fields overlap with geometry and uncertainty. They may also be tied to patch-risk surfaces. Until SAR support is separated from uncertainty and geometry, `sar_structure_factor` remains diagnostic-only and not active Phase4 scoring.

### uncertainty_factor

Ambiguity/artifact relevance:

SAR ambiguity and artifact likelihood matter because ambiguous or artifact-heavy evidence can make the selected candidate unreliable.

Local posterior fields:

Fields include `P_ambiguous`, `P_artifact`, `posterior_margin`, `posterior_confidence`, `E_uncertainty`, `sar_uncertainty_soft`, and uncertainty routing fields.

Hidden arbitration risk:

If uncertainty is allowed to penalize or protect candidates directly, it can become a hidden final arbitration factor and copy patch behavior.

Why diagnostic-only:

Uncertainty remains diagnostic-only until SAR structure, ambiguity, final arbitration, and B patch coupling are separated.

### final_arbitration_factor

Selected-behavior/B patch relevance:

Final arbitration fields explain how selector behavior, gate reasons, and patch actions changed candidate selection. They are useful for diagnosing staged GM17 behavior.

Patch dependency risk:

Fields such as `two_stage_gate_reason`, `two_stage_gate_allow_switch`, `two_stage_gate_kept_base`, `Z_t`, `phi_final_score`, `patch_action`, and patch-trigger fields can copy B patch behavior.

Why blocked:

This factor is blocked from active scoring and calibration. B patch reproduction can show diagnostic consistency, but it is not physical proof.

### visibility_factor

Partial visibility relevance:

Visibility evidence matters for truncation, occlusion, partial support, and future branch reasoning.

Local condition/visible evidence:

Fields and tables include A021 condition labels, A012 visible extent features, `visible_factor`, support-area fields, and visibility status fields.

Why future-only:

Visible support must not generate a full center. Visibility remains a future partial-visibility route, not a complete-vehicle Phase4A scoring factor.

### missing_extent_factor

Future role:

Missing extent can model which parts of the vehicle are absent or unreliable under truncation/occlusion.

Why future-only:

No standardized inference-safe feature schema, valid range, transform, cost, or clipping policy exists for Phase4A. It belongs to future Phase7 partial-visibility schema work.

### visible_full_center_offset_factor

Visible/full-center mismatch:

A visible support centroid can differ from the latent full-vehicle center. This mismatch is important because treating visible support as the full center can create systematic localization errors.

Why future-only:

No standardized offset schema exists. The current complete-vehicle branch must not use visible support to shift or generate a full center.

### near-field future route

Near-field should be treated as a geometry-regime or reliability problem, not as an ordinary occlusion flag and not as a current selector replacement.

Near-field may eventually require a separate geometry-regime state, reliability model, or branch-specific factor. In Phase4A it must not modify the candidate bank, replace the complete-vehicle selector, or enter OOF calibration.

## 8. Factor-To-Data-To-Literature Matrix

| factor | graph role | research hypothesis | GM17 evidence source | external literature support | local observable fields | inference-safe fields | diagnostic-only fields | eval-only fields | double-counting risk | patch-dependency risk | current status | recommended next action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `geometry_factor` | node factor | Candidate geometry explains complete-vehicle compatibility. | A001 candidate bank; A008 factor table; state-energy diagnostics. | SAR/remote-sensing OBB schema, SIVED, rotated OBB references. | `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross`, `delta_*`. | A001 candidate fields after scope/hash approval. | `refined_geometry_score`, `geometry_escape_refined_score` until ownership is declared. | `final_*`, `gt_*`, IoU, center error, oracle fields. | High with `sar_structure_factor`. | Low to medium through refined/escape diagnostic scores. | `ready_for_fixed_prior_design` | Create geometry fixed-prior design note first. |
| `direction_factor` | node factor | Signed direction posterior improves escape/near compatibility. | A007 posterior; A008 joined direction fields. | Direction and angle schema references; optical-SAR matching as background only. | `candidate_direction_bin`, `signed_escape_decision`, `signed_direction_match`, `P_near`, `P_neg_escape`, `P_pos_escape`, `posterior_confidence`, `posterior_margin`. | Direction-only posterior fields after mapping approval. | `P_ambiguous`, `P_artifact`, uncertainty routing fields. | Eval metrics and labels. | High with `source_factor`. | Medium if direction veto copies patch behavior. | `ready_after_mapping` | Run direction/source ownership audit. |
| controlled non-visible `source_factor` | node factor | Source family reliability can be modeled as provenance prior. | A001/A008 `candidate_source`; A013 diagnostic source prior. | SAR dataset/proposal schema and source/provenance concepts. | `candidate_source`, source-family mapping fields. | Non-visible `candidate_source` after normalization. | `source_prior`, `directional_shell_score`, `track_escape_evidence`, `signed_direction_match` as source support unless ownership is declared. | GT/manual/eval fields. | High with direction, geometry, SAR structure. | Medium if source prior copies selected behavior. | `ready_after_mapping` | Normalize source families and isolate visible source. |
| `optical_temporal_factor` | soft node/row prior | Optical-to-SAR temporal prediction can guide candidate selection without generating center. | A005 temporal inference; A008 temporal consistency; A001 temporal score. | Optical-SAR matching as soft-prior and failure-mode support. | `pred_r`, `pred_cross`, `pred_az`, `pred_cx`, `pred_cy`, `temporal_factor_score`, `optical_temporal_consistency_score`. | A005 soft-prior fields after approval. | Learned matching confidence, alignment diagnostics unless separately audited. | GT, final boxes, correspondence labels, eval metrics. | High with `transition_factor`. | Low unless used as release gate. | `ready_for_fixed_prior_design` | Create optical-temporal soft-prior design note after geometry. |
| `transition_factor` | edge factor | Track continuity improves path selection over fixed candidates. | A001/A008 track/frame/candidate state; A013 selected Viterbi reference. | MAP, Viterbi, min-cost-flow, tracking-by-detection structure. | `gm17_track_id`, `sar_frame_num`, `candidate_id`, `r`, `cross`, `az`, `heading`, `w`, `h`. | Candidate state and track/frame keys after ordering approval. | A013 path scores, gate reasons, selected candidate references. | Tracking metrics, GT association metrics, selected eval outputs. | High with `optical_temporal_factor`. | Medium if selected-reference path scores are copied. | `ready_after_mapping` | Delay until candidate-level ownership is stable. |
| `sar_structure_factor` | diagnostic node/support surface | SAR structural support may explain physically plausible candidates. | A008/A017 structure diagnostics. | SAR detection, scattering, shadow, and OBB background. | `directional_shell_score`, `geometry_escape_refined_score`, `track_escape_evidence`, `escape_conflict_score`, `E_sar_structure`. | None for active Phase4A. | All SAR structure support fields. | Eval metrics and labels. | High with geometry and uncertainty. | Medium through SAR uncertainty patch coupling. | `diagnostic_only` | Keep support-vs-uncertainty separation audit. |
| `uncertainty_factor` | diagnostic uncertainty surface | Ambiguity/artifact likelihood explains unreliable SAR evidence. | A007/A008 posterior and uncertainty diagnostics. | SAR ambiguity/detection background. | `P_ambiguous`, `P_artifact`, `posterior_margin`, `E_uncertainty`, uncertainty routing fields. | None for active Phase4A. | All uncertainty and artifact fields. | Eval metrics and labels. | High with SAR structure and final arbitration. | High through accepted SAR uncertainty patch behavior. | `diagnostic_only` | Keep uncertainty-route audit separate from scoring. |
| `final_arbitration_factor` | blocked final action layer | Selected action behavior can expose patch dependency. | A013/A018 selected/gate/patch outputs. | No active Phase4 method support; diagnostic comparison only. | `two_stage_gate_reason`, `two_stage_gate_allow_switch`, `Z_t`, `phi_final_score`, `patch_action`. | None. | Diagnostic comparison fields only. | Eval metrics and final labels. | High with uncertainty and SAR structure. | High. | `blocked` | Keep blocked from scoring and calibration. |
| `visibility_factor` | future partial-visibility factor | Visible support may explain partial evidence but not full center. | A012 visible diagnostics; A021 condition labels. | Amodal/partial-visibility literature. | `visible_factor`, support fields, condition labels. | None for active Phase4A. | Visible support diagnostics. | A021 labels, truncation/occlusion labels. | High with source and uncertainty. | Medium if visible support copies patch gates. | `future_only` | Keep Phase7-only; no full-center generation. |
| `missing_extent_factor` | future partial-visibility factor | Missing extent can model occluded/truncated vehicle state. | Future schema only; A021 labels as eval grouping. | Amodal/partial-visibility literature. | No standardized inference-safe schema. | None. | Any provisional missing extent diagnostics. | Truncation/occlusion labels. | High with visibility and offset. | Low currently. | `future_only` | Defer to Phase7 schema work. |
| `visible_full_center_offset_factor` | future latent offset factor | Visible centroid and full center can differ. | Future schema only; visible diagnostics as warning. | Amodal/full-object reasoning. | No standardized offset schema. | None. | Visible centroid/offset diagnostics if any. | Manual full boxes and labels. | High with visibility and missing extent. | Low currently. | `future_only` | Defer to Phase7; prohibit visible full-center shifts. |
| near-field future route | future geometry-regime route | Near-field may change geometry reliability. | Boundary notes only. | Automotive radar/near-field references as future route. | No current Phase4A fields. | None. | Any future geometry-regime indicators. | Eval grouping labels if later defined. | High with geometry if mixed prematurely. | Low currently. | `future_only` | Keep as Phase7B route; no candidate-bank or selector replacement. |

## 9. Factor Interaction And Ownership Risks

Geometry versus SAR structure:

- Risk: shell, escape, and refined geometry scores can reward the same SAR support twice.
- Ownership rule: candidate coordinate and fan-polar compatibility belongs to `geometry_factor`; SAR support/ambiguity diagnostics remain `sar_structure_factor` until a separate support schema is accepted.

Direction versus source:

- Risk: source family may imply direction while `direction_factor` separately scores signed direction match.
- Ownership rule: `direction_factor` owns signed direction posterior and candidate direction compatibility; `source_factor` owns only source-family provenance unless explicit direction-conditioned source ownership is reviewed.

Optical temporal versus transition:

- Risk: both factors can reward smooth paths.
- Ownership rule: `optical_temporal_factor` is a soft row/track prior relative to optical-to-SAR prediction; `transition_factor` is edge continuity between adjacent candidate states.

Uncertainty becoming hidden arbitration:

- Risk: ambiguity/artifact penalties can become a final decision gate rather than a diagnostic surface.
- Ownership rule: uncertainty fields remain diagnostic-only until support, ambiguity, and final-action ownership are separated.

Final arbitration copying B patch behavior:

- Risk: selected action fields can reproduce B patch behavior and look like physical proof.
- Ownership rule: final arbitration remains blocked from active scoring and calibration; it may be used only to expose patch dependency.

Visibility evidence generating full center:

- Risk: visible fragments or support centroids can be mistaken for the latent full-vehicle center.
- Ownership rule: visible support may become future veto/uncertainty evidence only; it must not generate or shift full center in Phase4A.

Near-field replacing complete-vehicle selector:

- Risk: near-field labels or reliability guesses can become an uncontrolled selector replacement or candidate-bank modification route.
- Ownership rule: near-field is future geometry-regime modeling only and cannot modify the candidate bank, replace the selector, or enter OOF calibration.

## 10. Phase4A Modeling Path

Recommended Phase4A path:

1. Design `geometry_factor` fixed priors first.
2. Add `optical_temporal_factor` as a soft-prior second step.
3. Add `direction_factor` only after mapping and direction/source ownership approval.
4. Add controlled non-visible `source_factor` only after source-family normalization and visible-source isolation.
5. Add `transition_factor` only after track/frame ordering and optical-temporal/transition ownership review.
6. Keep SAR structure, uncertainty, final arbitration, visibility, missing extent, visible/full-center offset, and near-field out of active Phase4A scoring.

A GM_RM017-only candidate-level pilot may be used as a validation container after human review of A001 scope and hash. That pilot is not the full research dataset. If Phase4A is meant to cover GM_RM011, GM_RM017, and GM_RM019, candidate-generation coverage for GM_RM011 and GM_RM019 must be handled as a separate candidate-generation audit route before all-scene validation.

## 11. What This Audit Enables

This audit enables:

- factor-specific fixed-prior design;
- factor observability analysis;
- Phase4A pilot planning;
- future all-scene validation planning;
- later learned weighting only after fixed-prior evidence is clean.

It does not authorize experiments, inference, metrics, training, calibration, candidate-bank generation, candidate-bank modification, code changes, GM17 replacement, partial-visibility activation, or near-field activation.

## 12. Human Review Questions

The researcher should decide:

- Are the five active complete-vehicle factors the correct Phase4A core?
- Should `geometry_factor` be the first fixed-prior design target?
- Should `optical_temporal_factor` be second, or should `direction_factor` come first?
- Which source families are truly non-visible?
- Is `multi_peak_ray_candidate` an allowed non-visible source family, or should Phase4A start with only base, wedge, bidirectional, and track-signed families?
- Which direction posterior fields are allowed as direction evidence versus uncertainty diagnostics?
- Should `posterior_confidence` and `posterior_margin` be direction confidence only, or should they remain diagnostic until uncertainty ownership is resolved?
- Should transition wait until candidate-level factor ownership is stable?
- What evidence threshold is required before moving from fixed priors to learning/calibration?
- Should GM_RM011/GM_RM019 candidate generation be treated as a separate candidate-generation audit route?

## 13. Recommended Next Round

Recommended next round:

```text
geometry_factor fixed-prior design note
```

Rationale:

- Geometry is the least dependent on unresolved source/direction/transition ownership.
- Geometry fields are directly observable in A001 for a GM_RM017-only pilot container.
- Geometry is the natural baseline for later optical-temporal, direction, source, and transition ablations.
- Geometry also forces the most important ownership decision with SAR structure before any combined factor graph is attempted.

Secondary follow-up rounds after the geometry note:

- `optical_temporal_factor` soft-prior design note;
- direction/source ownership audit;
- transition/Viterbi design note only after candidate-level factors are stable;
- candidate-generation audit for GM_RM011/GM_RM019 as a separate route if all-scene Phase4A is required.

Do not recommend running experiments yet.
