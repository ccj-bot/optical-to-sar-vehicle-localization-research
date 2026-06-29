# Phase5B First Diagnostic Run Specification

Date: 2026-06-29

## 1. Purpose

This document specifies the first diagnostic run for Phase5B.

It is a documentation-only implementation specification. It narrows the Phase5B design space into the minimum first diagnostic run that may be implemented later if explicitly approved.

This document is not:

- a final proposal-generation algorithm;
- an experiment result;
- executable code;
- a proposal output;
- an active inference plan for C3/C4.

Phase5B first diagnostic run specification:

- no code;
- no proposal generated;
- no experiment;
- no C3/C4 change;
- no threshold tuning;
- no training;
- no calibration.

The purpose is to define what a later approved diagnostic implementation would be allowed to do, what it would output, and how it would prevent A019/A021/GT/oracle/panel-review leakage.

## 2. First-Round Objective

The first diagnostic round does not pursue rank1 improvement.

It does not attempt to replace C3/C4.

It does not try to prove one proposal route is the final algorithm.

It only answers the following questions:

- does the optical-conditioned shell cover SAR target support?
- can SAR local evidence produce valid center / extent hypotheses outside A001?
- might proposal ceiling differ from A001 ceiling?
- are proposals simply repeating A001?
- do partial visibility, fan-edge, or clutter cases expose new state-model requirements?

The expected output of a future approved run would be a diagnostic proposal set with provenance, not an active localization result.

The diagnostic value is in ceiling, coverage, route contribution, and leakage-safe comparison. It is not in immediate rank1 selection.

## 3. Target Set

The provisional target set is the Phase4D GM_RM017 205-target set.

Rationale:

- the target set already has an A001 baseline ceiling;
- the target set already has Phase4D per-target failure labels;
- the target set is small enough for controlled visual and leakage audit;
- using the same target set allows Phase5C to compare proposal ceiling with A001 ceiling.

Boundary:

- Phase4D failure labels are post-hoc diagnostic labels only;
- failure labels must not enter proposal generation;
- failure labels must not select thresholds;
- failure labels must not choose which proposal route succeeds;
- A019/A021 can only be joined after proposal generation for Phase5C evaluation.

If a formal optical-conditioned shell is not yet available for all 205 targets, the first diagnostic run may use a current available proxy shell, but only if its source, fields, and uncertainty semantics are documented before implementation.

## 4. Inputs

### 4.1 Allowed Inputs

Only inference-safe inputs may be used during proposal generation.

Allowed inputs:

- optical-conditioned shell, or current available proxy shell if no formal shell exists yet;
- SAR image / local crop;
- scene geometry;
- valid SAR support mask or valid image support;
- temporal prior if inference-safe;
- target identity metadata;
- frame metadata;
- route configuration declared before proposal generation.

Allowed SAR-derived information:

- image-derived local energy;
- image-derived local contrast;
- image-derived foreground / component support;
- crop-local metadata needed to map proposal coordinates;
- support-mask membership.

Allowed shell-derived information:

- target identity;
- scene;
- SAR frame number;
- shell center / range / azimuth / cross support if available;
- shell crop region;
- predeclared scale or extent prior if available before evaluation.

### 4.2 Forbidden Inputs

The following inputs are forbidden during proposal generation, filtering, route scoring, threshold selection, and any first-round diagnostic implementation:

- A019 `final_*` fields;
- A019 final boxes;
- A021 fields;
- GT boxes;
- manually finalized boxes;
- oracle best labels;
- IoU labels;
- center-error labels;
- panel review outcomes;
- post-hoc failure labels;
- selected-vs-missed labels;
- any metric computed using GT;
- any route setting chosen by inspecting evaluation results from the same target set.

These forbidden fields may only be joined after proposal generation in Phase5C evaluation.

## 5. First-Round Routes

Only three proposal routes are allowed in the first diagnostic round.

### Route A: Shell-Grid / Multi-Scale Sampling

Allowed status:

- allowed for first diagnostic run.

Purpose:

- create a controlled shell-coverage baseline independent of A001;
- test whether the shell can contain plausible center / extent hypotheses without SAR image scoring.

Allowed evidence:

- optical-conditioned shell or approved proxy shell;
- scene geometry;
- valid support;
- predeclared scale set;
- predeclared offset grid;
- temporal prior only if inference-safe.

Likely future output:

- sampled center / extent windows;
- route source `shell_grid`;
- optical prior compatibility placeholder or score if defined before evaluation;
- no SAR observation score unless the route is explicitly paired with image diagnostics in a later approved variant.

First-round role:

- coverage baseline.

### Route B: Local Energy / Contrast Peak Proposals

Allowed status:

- allowed for first diagnostic run.

Purpose:

- test whether SAR local evidence inside the shell can generate center hypotheses not supplied by A001;
- separate image-supported centers from shell-only grid coverage.

Allowed evidence:

- SAR image / local crop;
- local energy statistics;
- local contrast statistics;
- local background estimate if predeclared;
- optical-conditioned shell or approved proxy shell;
- valid support.

Likely future output:

- center hypotheses around local peaks;
- optional local window extents;
- route source `energy_contrast_peak`;
- SAR observation score derived from image statistics only.

First-round role:

- center proposal diagnostic.

### Route C: Simple Connected-Component Diagnostic

Allowed status:

- allowed for first diagnostic run.

Purpose:

- test whether local foreground / support components provide useful center and extent hypotheses;
- expose clutter merging, partial support, and fragmented vehicle support cases.

Allowed evidence:

- SAR image / local crop;
- predeclared threshold family;
- valid support;
- optical-conditioned shell or approved proxy shell;
- component size filters declared before evaluation.

Likely future output:

- component centers;
- component AABB extent hypotheses;
- component support metadata;
- route source `connected_component`;
- uncertainty flags for fragmented, merged, tiny, large, or boundary-touching components.

First-round role:

- center / extent support diagnostic.

### 5.4 Disallowed First-Round Routes

The following routes are not allowed in the first diagnostic run:

- ridge / long-axis orientation proposal;
- learned model;
- factor graph over generated proposals;
- active C3/C4 integration;
- scoring-weight optimization;
- threshold tuning using evaluation results.

Rationale:

- ridge / long-axis proposal depends on orientation convention and should follow center/extent baselines;
- learned models and calibration are outside documentation-only Phase5B scope;
- factor graph over generated proposals belongs to a later Phase5D only if approved;
- C3/C4 integration would break the diagnostic-only boundary;
- threshold tuning from metrics would leak evaluation into proposal generation.

## 6. Predeclared Configuration

All proposal-generation parameters must be declared before any future proposal generation.

The first diagnostic implementation, if later approved, must submit a configuration block before running. The configuration block must be reviewed as part of the leakage boundary, not inferred from evaluation metrics.

Required predeclared configuration categories:

- maximum proposals per target;
- shell source and shell id policy;
- shell margin / crop size;
- scale set;
- offset grid;
- energy peak count;
- local background definition for energy / contrast;
- component threshold family if connected components are used;
- minimum component size;
- maximum component size;
- boundary-touching component policy;
- duplicate proposal merge policy;
- coordinate convention;
- support-mask policy;
- route configuration id;
- output bundle id.

This document does not set numeric values for those parameters.

Allowed placeholder semantics:

- values may be marked `TBD before implementation`;
- placeholders are not executable defaults;
- any later numeric value must be declared before proposal generation;
- no numeric value may be chosen by looking at A019/A021/oracle/panel-review results.

Configuration freeze rule:

- after proposal generation starts, first-round configuration cannot be changed based on Phase5C metrics;
- if configuration must change, it becomes a new diagnostic run with a new `route_config_id`.

## 7. Output Schema

A future first-round proposal CSV must contain at least the following fields:

- `proposal_id`
- `target_identity`
- `scene`
- `sar_frame_num`
- `gm17_track_id`
- `cx`
- `cy`
- `w`
- `h`
- `theta`
- `proposal_source`
- `route_name`
- `route_config_id`
- `optical_prior_score`
- `sar_observation_score`
- `uncertainty_flags`
- `parent_shell_id`
- `source_crop_id`
- `provenance`
- `leakage_audit_status`
- `diagnostic_only_flag`

Field requirements:

- `proposal_id` must not reuse A001 `candidate_id`;
- `proposal_source` and `route_name` must identify the generating route;
- `route_config_id` must link to the predeclared configuration;
- `optical_prior_score` must not include GT, A019, A021, oracle, panel review, or evaluation metrics;
- `sar_observation_score` must be image-derived or `NA` when the route has no SAR evidence score;
- `uncertainty_flags` must record ambiguity without copying A021 labels;
- `provenance` must record input sources and route version;
- `leakage_audit_status` must be explicit for every row;
- `diagnostic_only_flag` must be true for all first-round outputs.

No output CSV is produced by this document.

## 8. Phase5C Evaluation Handoff

Phase5C may begin only after first-round proposals are generated by an approved implementation.

Phase5C join rule:

- generate proposals first;
- freeze proposal output;
- only then join A019/A021 and evaluation metrics;
- record the join as post-hoc evaluation;
- never write evaluation labels back into proposal generation.

Phase5C comparison should include:

- proposal oracle best center error;
- proposal oracle AABB proxy IoU;
- proposal count per target;
- high-quality proposal rate;
- outside-A001-neighborhood rate;
- route contribution;
- condition breakdown.

Required interpretation boundaries:

- proposal ceiling is not active inference performance;
- proposal oracle is not a deployed selector;
- high proposal count must be reported alongside quality metrics;
- outside-A001-neighborhood proposals must be inspected for valid SAR support, not automatically treated as improvement;
- condition breakdown must remain post-hoc and cannot tune first-round routes.

Phase5C may compare against Phase4D A001 ceiling only under the same target-set boundary and clearly stated metric definitions.

## 9. Stop / Go

### 9.1 GO Implementation Only If

Implementation may proceed only if all of the following are true:

- input sources are identified;
- shell proxy is acceptable and documented if no formal shell exists;
- SAR image / local crop source is identified;
- scene geometry / valid support source is identified;
- predeclared configuration exists;
- output schema is accepted;
- leakage audit rules are accepted;
- target set is fixed before running;
- generated proposals will remain separate from C3/C4.

### 9.2 STOP / HOLD If

Stop or hold if any of the following occurs:

- shell source is unclear;
- SAR image source is unclear;
- scene geometry / valid support source is unclear;
- route needs GT;
- route needs A019 final fields;
- route needs A021 labels;
- route needs oracle labels;
- route needs panel review;
- route cannot produce provenance;
- route cannot assign `route_config_id`;
- route collapses into A001 reranking;
- route requires threshold tuning from evaluation metrics;
- output is a `candidate_id` instead of a SAR latent state hypothesis;
- generated proposals would be injected into C3/C4.

### 9.3 Review Gate Before Execution

Before any implementation, a reviewer should approve:

- target set;
- input source inventory;
- shell source or shell proxy;
- route list;
- route configuration block;
- output schema;
- leakage audit checklist;
- planned Phase5C join boundary.

Without that approval, Phase5B remains documentation-only.

## 10. Boundary Statement

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
- This file is not staged or committed unless explicitly approved later.
