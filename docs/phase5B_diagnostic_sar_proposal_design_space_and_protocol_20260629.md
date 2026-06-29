# Phase5B Diagnostic SAR Proposal Design Space And Protocol

Date: 2026-06-29

## 1. Purpose

Phase5B is a design-space and diagnostic-protocol memo for independent diagnostic SAR proposal generation.

Phase5B is not a final proposal-generation algorithm.

Phase5B does not implement proposals.

Phase5B does not inject proposals into C3/C4.

Phase5B does not tune thresholds or train models.

Phase5B only defines:

- candidate proposal routes worth comparing;
- allowed inference-safe inputs for each route;
- forbidden leakage sources;
- proposal / particle output interface semantics;
- future diagnostic comparison protocol for Phase5C;
- stop/go criteria before any implementation or active inference is allowed.

The purpose is to support the realigned mainline:

```text
optical target state
  + temporal prior
  + scene geometry
  + SAR image evidence
      -> SAR latent vehicle state
      -> proposal / particle / candidate nodes
      -> factor graph inference
      -> localization output
```

Phase5B does not prove that any route is correct. It defines how future routes can be compared without turning the work back into A001 row selection, C3/C4 tuning, or evaluation-label leakage.

## 2. Relationship To Phase5A

Phase5B inherits the Phase5A problem definition.

Inputs:

- optical target state;
- track / temporal prior;
- scene geometry;
- SAR image / local crop.

Target output:

- SAR latent vehicle state.

The target output is not:

- `candidate_id`;
- an A001 row;
- a C3/C4 rank;
- a table-rule selection result.

Phase5B proposals or particles are internal hypothesis representations for SAR latent vehicle state. They are not the research goal by themselves.

A proposal may represent:

- a center hypothesis;
- an extent hypothesis;
- a long-axis / orientation hypothesis;
- a range / azimuth / cross-track hypothesis;
- a visibility or partial-support hypothesis;
- a multi-hypothesis mode in an ambiguous SAR crop.

The proposal layer is therefore a bridge between the optical-conditioned shell, SAR observation evidence, and future factor graph inference. It is not a replacement for the full state-inference problem.

## 3. What Must Be Fixed Vs What Must Stay Open

This section fixes research boundaries and interfaces, not algorithm answers.

### 3.1 Must Be Fixed

The following items are fixed for Phase5B.

Problem semantics:

- the problem is optical-conditioned SAR state inference;
- the problem is not A001 row selection;
- the output is a SAR latent vehicle-state hypothesis, not a selected candidate id.

Output semantics:

- each proposal represents a possible SAR latent vehicle state or state component;
- `proposal_id` is not interchangeable with A001 `candidate_id`;
- proposal records must preserve uncertainty and provenance instead of collapsing directly to rank1 selection.

Module separation:

- optical prior layer defines shell / prior support;
- SAR observation layer evaluates SAR image evidence inside the shell;
- factor graph layer later combines proposal nodes, priors, SAR evidence, temporal consistency, and geometry constraints;
- evaluation audit layer joins A019/A021 and metrics only after inference-side artifacts exist.

Leakage boundary:

- A019 `final_*` fields cannot enter proposal generation or inference;
- GT boxes cannot enter proposal generation or inference;
- oracle labels cannot enter proposal generation or inference;
- A021 condition / truncation / occlusion labels cannot enter proposal generation or inference;
- panel review outcomes cannot enter proposal generation or inference;
- any metric computed with GT cannot enter proposal generation or inference.

Diagnostic-only status:

- Phase5B proposals, if later implemented, remain separate from active C3/C4;
- no generated proposal is mixed into C3/C4 unless a later Phase5D step is explicitly approved;
- no proposal route is treated as a production selector in Phase5B.

Proposal interface:

- `proposal_id`;
- `target_identity`;
- `scene`;
- `sar_frame_num`;
- `gm17_track_id` if available;
- `cx`;
- `cy`;
- `w`;
- `h`;
- `theta`;
- `proposal_source`;
- `optical_prior_score`;
- `sar_observation_score`;
- `uncertainty_flags`;
- `provenance`;
- `leakage_audit_status`.

Post-hoc evaluation:

- GT and A021 can only be joined after proposal generation for Phase5C ceiling audit;
- Phase5C must use the same target set when comparing proposal ceiling with A001 ceiling;
- metrics must not feed back into Phase5B route design as threshold tuning or calibration.

Stop/go criteria:

- implementation requires accepted design boundaries;
- first-round route choices must remain diagnostic;
- active inference requires separate approval after diagnostic evidence exists.

### 3.2 Must Stay Open

The following items are future empirical or design choices, not Phase5B fixed decisions.

- final proposal algorithm;
- raw SAR vs display / pseudocolor input decision;
- local energy thresholds;
- connected-component parameters;
- ridge / long-axis detector details;
- rotated OBB use as final representation;
- proposal scale set;
- scoring weights;
- active integration into C3/C4;
- training or calibration.

Phase5B must not lock these down prematurely. It may describe candidate routes, but it must not claim that one route, threshold family, detector, scale set, or rotated representation is final.

## 4. Allowed Inputs And Forbidden Inputs

### 4.1 Allowed Inference-Safe Inputs

Proposal routes may use only inputs available before evaluation joins.

Allowed inputs include:

- optical target identity;
- optical target state;
- optical visible extent when available;
- optical uncertainty metadata when available;
- temporal prior;
- neighboring-frame state estimate if it is inference-safe and not evaluation-derived;
- scene id;
- SAR frame id;
- fan geometry;
- valid SAR support mask;
- optical-conditioned search shell;
- SAR image / local crop;
- image-derived statistics from the local crop;
- approved metadata available before inference;
- route configuration declared before evaluation.

Allowed image-derived statistics may include future diagnostic measures such as local energy, local contrast, radial profiles, component support, or structure support, as long as they are computed without GT, oracle, A019 final boxes, A021 condition labels, or panel-review feedback.

### 4.2 Forbidden Inputs

The following inputs are forbidden during proposal generation, scoring, filtering, shell contraction, and inference:

- A019 `final_*` fields;
- GT boxes;
- manually finalized boxes;
- oracle best-candidate labels;
- IoU labels;
- center-error labels;
- A021 condition labels;
- A021 truncation labels;
- A021 occlusion labels;
- panel review outcomes;
- post-hoc failure labels;
- selected-vs-missed labels;
- any metric computed using GT;
- any route setting chosen by looking at evaluation results from the same target set.

These may only be used in Phase5C or evaluation-only audits after proposals are generated.

## 5. Proposal Output Interface

### 5.1 Required Fields

A future proposal / particle record must include:

- `proposal_id`
- `target_identity`
- `scene`
- `sar_frame_num`
- `gm17_track_id` if available
- `cx`
- `cy`
- `w`
- `h`
- `theta`
- `proposal_source`
- `optical_prior_score`
- `sar_observation_score`
- `uncertainty_flags`
- `provenance`
- `leakage_audit_status`

### 5.2 Recommended Additional Fields

Recommended fields include:

- `parent_shell_id`
- `source_crop_id`
- `range_state`
- `azimuth_state`
- `cross_state`
- `center_uncertainty`
- `extent_uncertainty`
- `theta_uncertainty`
- `visibility_state`
- `ambiguity_group`
- `generation_version`
- `diagnostic_only_flag`

### 5.3 Field Semantics

`proposal_id`:

- uniquely identifies a generated hypothesis;
- is not A001 `candidate_id`;
- must remain stable within one diagnostic output bundle.

`proposal_source`:

- identifies route and version;
- must distinguish shell-grid, energy/contrast, radial profile, component, ridge/axis, hybrid, or other later routes.

`optical_prior_score`:

- measures compatibility with the optical-conditioned shell;
- must not include GT, A019 final boxes, oracle labels, A021 labels, or panel review outcomes.

`sar_observation_score`:

- measures SAR image support;
- must be image-derived or based on approved inference-safe metadata;
- must not be derived from post-hoc success/failure labels.

`uncertainty_flags`:

- records ambiguity, partial support, weak orientation evidence, clutter risk, fan-edge risk, missing extent, or low observation support;
- must not copy A021 labels during inference.

`provenance`:

- records data source, route, declared configuration, version, and inference-safe inputs;
- should make route reconstruction and leakage audit possible.

`leakage_audit_status`:

- must be explicit;
- should indicate whether the proposal was generated with pre-inference fields only;
- should flag any route whose allowed inputs are unclear.

`diagnostic_only_flag`:

- should be true for Phase5B/Phase5C artifacts;
- records that the proposal is not an active C3/C4 candidate.

## 6. Proposal Design Space

This section lists candidate routes. It does not choose the final proposal route.

### Route A: Shell-Grid / Multi-Scale Window Sampling

Route name:

- shell-grid / multi-scale window sampling.

Idea:

- sample multiple centers, offsets, scales, and shapes inside the optical-conditioned shell;
- create a basic proposal set independent of A001.

Allowed evidence:

- optical shell;
- scene geometry;
- temporal prior;
- allowed size / orientation prior;
- valid SAR support mask;
- no GT.

Likely output:

- grid or sampled proposal windows;
- center and extent hypotheses;
- optional coarse `theta` modes if predeclared.

Expected benefit:

- establishes a coverage baseline independent of A001;
- tests whether the optical-conditioned shell itself contains plausible SAR target states;
- provides a controlled denominator for proposal ceiling.

Key risks:

- may become dense brute-force search;
- may not use SAR image evidence enough;
- may create high proposal count;
- may overstate ceiling if density is not reported.

First-round suitability:

- high, but only as a capped diagnostic baseline with proposal count reported.

### Route B: Local Energy / Contrast Peak Proposals

Route name:

- local energy / contrast peak proposals.

Idea:

- search for SAR local energy or contrast peaks inside the shell;
- generate center hypotheses from image-supported peaks.

Allowed evidence:

- SAR local crop;
- local intensity statistics;
- display or pseudocolor statistics only if approved and declared;
- local background contrast;
- optical shell as spatial support;
- no GT.

Likely output:

- center hypotheses;
- local support scores;
- optional local window extents around peaks.

Expected benefit:

- starts using SAR evidence directly;
- useful for center localization;
- can reveal whether A001 misses image-supported centers.

Key risks:

- clutter and bright artifacts;
- energy peak may not equal vehicle center;
- display image may not reflect raw SAR physics;
- partial visibility may shift energy away from full-body center.

First-round suitability:

- high as a diagnostic center-proposal route.

### Route C: Radial / Range-Profile Support

Route name:

- radial / range-profile support.

Idea:

- analyze profiles along range or radial direction inside the shell;
- identify peaks or bands consistent with SAR scattering support.

Allowed evidence:

- SAR crop;
- fan / range geometry;
- radial profile statistics;
- optical shell range support;
- no GT.

Likely output:

- range-supported center hypotheses;
- band proposals;
- range / azimuth / cross-track state hypotheses.

Expected benefit:

- aligns proposal generation with SAR geometry;
- may improve range-side localization;
- can expose whether failures are radial-position ambiguity rather than table selection.

Key risks:

- geometry convention errors;
- clutter peaks;
- partial visibility ambiguity;
- range-profile support may not define cross-track center.

First-round suitability:

- medium; useful but convention-dependent.

### Route D: Connected-Component Proposals

Route name:

- connected-component proposals.

Idea:

- run local foreground / component diagnostics inside the shell;
- convert component support into center and extent hypotheses.

Allowed evidence:

- SAR crop;
- local thresholding or adaptive segmentation if declared as diagnostic;
- optical shell as spatial support;
- valid SAR support mask;
- no GT.

Likely output:

- component bounding boxes;
- component centers;
- support-region proposals;
- component confidence or ambiguity flags.

Expected benefit:

- tests whether visible SAR blobs give better center/extent hypotheses than A001;
- can expose partial-support and clutter-merging behavior.

Key risks:

- threshold sensitivity;
- clutter merging;
- fragmented vehicles;
- partial vehicle support may not equal full vehicle;
- component bounding box may not be a valid rotated or physical vehicle state.

First-round suitability:

- medium to high as a conservative diagnostic route, with thresholds and component counts reported.

### Route E: Ridge / Long-Axis Support Proposals

Route name:

- ridge / long-axis support proposals.

Idea:

- detect elongated local support, ridges, or structure-tensor axis cues;
- propose `theta`, long-axis, and extent hypotheses.

Allowed evidence:

- SAR crop;
- local structure tensor, ridge, or elongated component evidence if later implemented;
- optical shell as spatial support;
- no GT.

Likely output:

- orientation hypotheses;
- long-axis support hypotheses;
- rotated extent hypotheses;
- weak-orientation flags.

Expected benefit:

- directly targets the known A001 heading weakness;
- separates SAR-derived axis support from scene-level heading grid;
- can test whether rotated/long-axis evidence changes proposal ceiling.

Key risks:

- heading convention ambiguity;
- speckle and clutter;
- not all vehicles show clean ridge support;
- risk of overfitting visual panel perception;
- risk of prematurely claiming rotated OBB validity.

First-round suitability:

- low to medium; better deferred until center proposal baselines are audited.

### Route F: Hybrid Shell + SAR Evidence Proposals

Route name:

- hybrid shell + SAR evidence proposals.

Idea:

- use optical shell to limit the candidate space;
- use SAR observation scores to rank or filter generated hypotheses;
- preserve separate optical prior and SAR observation scores.

Allowed evidence:

- optical shell;
- SAR observation scores;
- temporal prior;
- scene geometry;
- no GT.

Likely output:

- ranked diagnostic proposal set;
- per-route source contribution;
- separate optical and SAR score fields;
- uncertainty and ambiguity flags.

Expected benefit:

- closest to the realigned mainline;
- prepares a clean interface for later factor graph inference;
- can test whether SAR observation adds value beyond shell coverage.

Key risks:

- may silently become an active ranker;
- scoring weights can become hidden tuning;
- leakage risk if evaluation feedback influences design;
- may collapse uncertainty too early.

First-round suitability:

- later, after individual routes are audited.

## 7. Recommended First Diagnostic Round

The first diagnostic round should not implement a complex complete proposal generator.

Recommended first-round routes:

1. shell-grid / multi-scale window sampling;
2. local energy / contrast peak proposals;
3. simple connected-component diagnostic.

Temporarily held routes:

- ridge / long-axis orientation proposal;
- learned proposal model;
- factor graph over generated proposals;
- active C3/C4 integration;
- scoring-weight optimization;
- threshold tuning.

The first-round goal is not rank1 improvement.

The first-round goal is to answer:

- does the optical-conditioned shell cover the SAR target support?
- can SAR local evidence propose valid center / extent hypotheses outside A001?
- is the proposal ceiling different from the A001 ceiling?
- are proposals simply duplicating A001?
- do partial visibility, fan-edge, or clutter cases expose new state-model requirements?
- how many proposals are needed before ceiling appears competitive?
- which route creates useful hypotheses with auditable provenance?

First-round outputs, if later approved, must remain diagnostic-only and separate from active C3/C4.

## 8. Phase5C Diagnostic Comparison Protocol

Phase5C should compare proposal ceiling with A001 ceiling only after proposals are generated by inference-safe routes.

Required protocol:

- generate proposals first;
- join A019/A021 only after proposal generation;
- use the same target set as the A001 comparison when possible;
- report proposal count and route source before metric interpretation;
- keep proposal ceiling separate from active inference;
- prevent metrics from feeding back into Phase5B proposal generation.

Comparison dimensions:

- center coverage;
- AABB extent coverage;
- orientation capacity;
- partial visibility behavior;
- proposal count / density;
- failure modes;
- route contribution;
- whether proposals fall outside the A001 neighborhood.

Suggested Phase5C metrics:

- oracle best center error;
- oracle AABB proxy IoU;
- proposal count per target;
- shell coverage rate;
- high-quality proposal rate;
- proposal outside A001-neighborhood rate;
- orientation diversity rate;
- failure condition breakdown;
- proposal source contribution.

Rules:

- any metric must be computed after proposal generation;
- metrics cannot select thresholds for the same run;
- metrics cannot decide which proposals are retained before evaluation;
- A019/A021 joins must be downstream and auditable;
- Phase5C results cannot be used to silently patch C3/C4.

## 9. Stop / Go Criteria

### GO To Phase5B Implementation Only If

- Phase5B design boundary is accepted;
- allowed inputs are clearly defined;
- output schema is frozen for the first diagnostic run;
- leakage audit rule is explicit;
- first-round routes are selected as diagnostic only;
- route configuration is declared before evaluation;
- proposal outputs will not enter C3/C4.

### GO To Phase5C Comparison Only If

- proposals are generated without GT/A019/A021 leakage;
- proposal provenance is complete;
- proposal count and route source are auditable;
- no threshold tuning was performed using evaluation results;
- A019/A021 are joined only after proposal generation;
- proposal artifacts are separate from active inference outputs.

### HOLD / STOP If

- design depends on GT, oracle, A021, or panel review;
- proposal generation requires active C3/C4 integration;
- method becomes A001 reranking under a new name;
- scoring weights require calibration;
- output is `candidate_id` instead of SAR latent state hypothesis;
- route cannot record provenance;
- route cannot separate optical prior score from SAR observation score;
- route needs evaluation metrics to decide thresholds or retained proposals;
- route cannot preserve diagnostic-only status.

## 10. Relationship To A001 And Phase4

A001 remains the fixed-bank baseline.

C3/C4 remain selection-layer prototypes.

Phase4C/D/H remain diagnostic evidence.

Phase5B proposals do not replace A001.

Phase5B proposals do not enter C3/C4.

Phase5C may compare proposal ceiling with A001 ceiling.

Phase5D, if ever approved, may test factor graph inference over generated proposals.

Current safe conclusions:

- A001 AABB center/size pool is not the primary bottleneck under Phase4D metrics;
- A001 heading / orientation is not SAR-derived;
- fixed-bank selection result is not the full migration model;
- independent proposal design remains justified as a diagnostic route, not as immediate active inference.

Current unsafe conclusions:

- independent proposals are unnecessary;
- rotated OBB / long-axis inference is solved;
- generated proposals should be injected into C3/C4 now;
- Phase5B should tune thresholds, weights, or training objectives.

## 11. Final Statement

Phase5B defines a diagnostic proposal design space and comparison protocol. It does not assert that any proposal route is correct. It fixes research boundaries, interface semantics, and leakage controls while keeping the actual proposal algorithm open for later diagnostic evaluation.

## 12. Boundary Statement

This document is documentation-only.

- No code was added.
- No experiment was added.
- No proposal was generated.
- No candidate was generated.
- No C3/C4 ranking was changed.
- No A001/A005/A019/A021 source file was modified.
- No threshold tuning was performed.
- No model was trained.
- No calibration was performed.
- No active proposal was injected into C3/C4.
- No push was performed.
- This Phase5B file is not staged or committed unless explicitly approved later.
