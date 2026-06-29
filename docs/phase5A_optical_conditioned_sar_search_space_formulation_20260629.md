# Phase5A Optical-Conditioned SAR Search-Space Formulation

Date: 2026-06-29

## 1. Purpose

This document defines the Phase5A formulation for the realigned optical-to-SAR vehicle localization mainline.

Phase5A is documentation-only. It defines the problem, state variables, module boundaries, proposal/particle interface, and leakage controls for future work. It does not implement SAR proposal generation, alter C3/C4 ranking, tune factors, train a model, or generate candidates.

The key correction is:

> The target problem is optical-conditioned SAR state inference, not fixed A001 row selection.

The fixed A001 candidate-bank graph remains a useful selection-layer prototype and baseline, but it is not the complete optical-to-SAR migration model.

## 2. Problem Statement

### 2.1 Inputs

The realigned problem uses four input groups.

1. Optical target state

- optical target identity;
- optical box / visible extent when available;
- coarse optical pose or long-axis cue when available;
- optical visibility or truncation cue when available;
- uncertainty over the optical observation.

2. Track / temporal prior

- target identity and track continuity;
- previous or neighboring SAR frame state estimates when available;
- predicted range, azimuth, cross-track, or image-plane center distribution;
- motion consistency constraints;
- temporal uncertainty.

3. Scene geometry

- SAR frame and scene identity;
- fan geometry / range-azimuth mapping;
- valid image support and mask/fan boundary;
- expected vehicle scale range under scene geometry;
- known geometry-convention metadata.

4. SAR image / local crop

- SAR intensity evidence in the optical-conditioned search shell;
- local crop around the predicted search region;
- background / clutter context;
- partial visibility and fan-edge evidence.

### 2.2 Output

The output is a SAR latent vehicle state:

```text
x_sar = {
  center,
  extent,
  long_axis,
  range_azimuth_state,
  visibility_state,
  uncertainty_state,
  hypothesis_structure
}
```

The output is not:

- a `candidate_id`;
- a selected A001 row;
- a C3 or C4 rank entry;
- a table-rule result.

Candidate rows, proposal nodes, or particles are possible internal representations. They are not the research target by themselves. The research target is the inferred SAR vehicle localization state.

### 2.3 Main Inference Question

The Phase5 main question is:

> Given optical target state, temporal prior, scene geometry, and SAR image evidence, infer the latent vehicle state in SAR.

The desired model shape is:

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

The optical side constrains search. The SAR side performs localization inside that constrained search space.

## 3. SAR Latent Vehicle State Definition

The SAR latent vehicle state should be richer than an A001 table row. At minimum it should contain the following components.

### 3.1 Image-Plane Center

Fields:

- `cx`
- `cy`

Meaning:

- estimated center of the SAR vehicle state in image coordinates;
- may represent full-body center, visible-center proxy, or a state-specific center convention, but the convention must be explicit;
- should carry uncertainty because SAR scattering support may not be centered on the physical vehicle body.

Boundary:

- `cx`, `cy` are inferred state variables, not copied from A001 as the final answer by default.

### 3.2 Extent State

Fields:

- `w`
- `h`
- or an equivalent extent parameterization.

Meaning:

- expected SAR support extent of the target hypothesis;
- may represent full vehicle footprint, visible support, or a local SAR evidence window depending on the chosen state convention.

Required convention decisions:

- whether `w` and `h` are image-axis-aligned extents;
- whether they are rotated-box side lengths;
- whether they represent physical vehicle dimensions or SAR scattering support;
- whether partial visibility changes the latent extent or only the observation likelihood.

Boundary:

- A019 `final_w` / `final_h` and A001 `w` / `h` can be used for downstream evaluation or baseline comparison only when their role is explicit. They do not define the Phase5 latent state by themselves.

### 3.3 Long-Axis / Orientation State

Fields:

- `theta`
- `long_axis_state`
- optional `theta_uncertainty`

Meaning:

- latent orientation or long-axis support in the SAR image;
- can be a continuous angle, a discrete set of modes, or an unknown / weakly observed state;
- should distinguish SAR-derived axis evidence from scene-level candidate grid conventions.

Boundary:

- A001 heading is not assumed to be SAR-derived orientation.
- Phase5A does not resume heading-convention deep dive.
- Future orientation use must state angle unit, coordinate frame, and clockwise/counterclockwise convention before any rotated metric is claimed.

### 3.4 Range / Azimuth State

Fields:

- `range_state` or `r`
- `azimuth_state` or `az`
- `cross_state` or `cross`
- optional covariance or interval bounds.

Meaning:

- geometry-linked representation of target position in SAR scene coordinates;
- supports fan-band constraints, range profile reasoning, and cross-track consistency;
- bridges optical-conditioned shell generation and SAR observation scoring.

Boundary:

- range / azimuth / cross variables may constrain the search shell, but they do not replace SAR image evidence for final localization.

### 3.5 Visibility State

Fields:

- `visibility_state`
- optional `partial_visible_flag`
- optional `fan_edge_flag`
- optional `truncation_mode`
- optional `occlusion_or_shadow_mode`

Meaning:

- describes whether the latent full vehicle, visible SAR support, and image evidence are expected to coincide;
- allows partial visibility and fan-edge cases to be modeled without forcing the full vehicle center into the most visible SAR blob;
- captures ambiguity caused by truncation, occlusion, shadowing, layover, or mask boundaries.

Boundary:

- A021 condition labels are evaluation-only and cannot be used to set this state during inference.
- Panel review labels cannot be fed back into this state during proposal generation or ranking.

### 3.6 Uncertainty State

Fields:

- `center_uncertainty`
- `extent_uncertainty`
- `theta_uncertainty`
- `range_azimuth_uncertainty`
- `visibility_uncertainty`
- optional covariance, intervals, score distributions, or mode weights.

Meaning:

- represents ambiguity from optical transfer, temporal prediction, SAR scattering structure, and scene geometry;
- should avoid collapsing the problem to a single hard box before SAR evidence is evaluated.

Boundary:

- uncertainty is part of the model state, not a post-hoc explanation only.

### 3.7 Multi-Hypothesis State

Fields:

- `hypothesis_id`
- `parent_track_id`
- `mode_weight`
- `mode_source`
- `ambiguity_group`

Meaning:

- represents multiple plausible SAR vehicle states when the shell contains clutter, multiple bright structures, or weak directional evidence;
- supports proposal/particle sets before final factor graph inference.

Boundary:

- multi-hypothesis state is not equivalent to A001 top-k rows. A001 top-k is one fixed-bank prototype of a hypothesis set.

## 4. Optical-Conditioned Search Shell

### 4.1 Role

The optical-conditioned search shell is a prior distribution or constrained support region over possible SAR states.

It should answer:

- where in SAR the target is plausible;
- what range / azimuth / cross-track region should be searched;
- what center, size, and orientation ranges are plausible;
- how much uncertainty should be preserved for SAR evidence to resolve.

It should not answer:

- the final SAR box;
- the final rotated OBB;
- the final `candidate_id`;
- the final C3/C4 rank.

### 4.2 Optical Input As Weak Prior

Optical target state can provide:

- approximate target identity continuity;
- approximate visible extent;
- coarse pose or main-axis cue;
- coarse vehicle size prior;
- truncation or edge visibility hints;
- depth-assisted or geometry-assisted range support.

But optical evidence must remain a prior:

- depth is a weak aid, not a hard controller;
- optical visible extent is not automatically SAR visible extent;
- optical pose is not automatically SAR long-axis evidence;
- temporal continuity stabilizes the search but should not dominate SAR localization.

### 4.3 Constraint Components

Range constraint:

- limits plausible SAR distance/range support;
- should allow uncertainty intervals rather than a single hard range;
- can be informed by scene geometry, temporal prediction, and optical transfer.

Azimuth constraint:

- limits plausible fan/azimuth region;
- should preserve wrap/convention metadata;
- can form a fan-band prior with range constraints.

Cross-track constraint:

- captures lateral deviation from predicted or transferred position;
- helps avoid treating all radial candidates as equally plausible;
- should not duplicate evidence already represented by range/azimuth factors unless explicitly modeled.

Temporal continuity:

- provides state continuity over frames;
- helps distinguish track-consistent hypotheses from clutter;
- should be softened for entry, exit, partial visibility, and scene-edge cases.

Depth / optical visible state:

- can shrink or shape the shell only when uncertainty is preserved;
- should never be used as a hard guarantee of final SAR center or extent;
- should be flagged as weak prior evidence.

### 4.4 Shell Output

A future shell representation should expose:

- `target_identity`
- `scene`
- `sar_frame_num`
- center prior distribution or interval;
- range / azimuth / cross prior distribution or interval;
- extent prior distribution or interval;
- optional orientation prior distribution;
- visibility risk flags;
- uncertainty metadata;
- provenance.

No shell output in Phase5A is generated. This document only defines the expected semantics.

## 5. SAR Observation Layer

### 5.1 Role

The SAR observation layer evaluates image evidence inside the optical-conditioned shell. Its purpose is to generate, support, or reject latent SAR vehicle state hypotheses using SAR data.

It is the layer that should decide precise localization evidence inside the shell. It should not be replaced by optical prior strength alone.

### 5.2 Candidate Evidence Types

Future SAR observation features may include:

- local energy support;
- foreground/background contrast;
- radial profile consistency;
- range-direction peak support;
- structure support;
- ridge or long-axis support;
- connected component evidence;
- edge / boundary support;
- shadow or layover ambiguity evidence;
- clutter / artifact evidence;
- partial visibility evidence near fan or mask boundaries.

These are only candidate evidence definitions in Phase5A. No feature extractor, threshold, proposal generator, or model is implemented here.

### 5.3 Observation Output Semantics

The SAR observation layer may later output:

- SAR-supported center hypotheses;
- extent hypotheses;
- orientation or long-axis hypotheses;
- visibility hypotheses;
- ambiguity flags;
- observation scores with provenance;
- local crop diagnostics.

Boundary:

- it must not use A019/A021 labels to generate or filter hypotheses;
- it must not use panel review results as training or selection feedback;
- it must not write into C3/C4 active inference without explicit later approval.

## 6. Proposal / Particle Interface

### 6.1 Purpose

Future proposals or particles are an interface between the optical-conditioned shell, SAR observation layer, and factor graph inference layer.

They are not generated in Phase5A.

### 6.2 Required Fields

A future proposal / particle record should include at least:

- `proposal_id`
- `target_identity`
- `scene`
- `sar_frame_num`
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

### 6.3 Recommended Additional Fields

Additional fields may be useful later:

- `gm17_track_id`
- `range_state`
- `azimuth_state`
- `cross_state`
- `center_uncertainty`
- `extent_uncertainty`
- `theta_uncertainty`
- `visibility_state`
- `visibility_uncertainty`
- `ambiguity_group`
- `parent_shell_id`
- `source_crop_id`
- `generation_version`
- `leakage_audit_status`

### 6.4 Field Semantics

`proposal_id`:

- unique identifier for a generated hypothesis;
- not interchangeable with A001 `candidate_id`.

`proposal_source`:

- identifies whether the hypothesis comes from shell sampling, SAR local evidence, connected components, ridge support, or another future diagnostic route.

`optical_prior_score`:

- measures compatibility with optical-conditioned shell priors;
- should not encode GT, oracle, final box, panel review, or condition labels.

`sar_observation_score`:

- measures support from SAR image evidence;
- must be derived from image/crop evidence and approved inference-safe metadata only.

`uncertainty_flags`:

- records ambiguity, partial visibility, weak orientation support, clutter risk, fan-edge risk, or missing evidence;
- should not copy A021 labels during inference.

`provenance`:

- records data source, generation route, version, and inference-safe inputs;
- must make it possible to audit whether evaluation-only data leaked into proposal generation.

### 6.5 Interface Boundary

No proposal file is produced by Phase5A.

Future proposal generation must be introduced as a separate diagnostic-only Phase5B artifact unless explicitly approved otherwise.

## 7. Factor Graph Role

### 7.1 Realigned Role

The factor graph should no longer be framed as only an A001 ranker.

Its realigned role is:

- represent SAR vehicle hypotheses as nodes;
- combine optical prior compatibility;
- combine SAR observation support;
- combine temporal consistency;
- combine scene geometry constraints;
- preserve uncertainty and multi-hypothesis structure until inference resolves it;
- output a SAR localization state.

### 7.2 Factor Families

Future factor families may include:

- optical-to-SAR shell prior factor;
- SAR observation evidence factor;
- temporal consistency factor;
- scene geometry factor;
- range / azimuth / cross consistency factor;
- extent prior factor;
- orientation / long-axis support factor;
- visibility or partial-support factor;
- ambiguity / artifact penalty or uncertainty factor.

These are design categories only. Phase5A does not set weights, thresholds, caps, or executable formulas.

### 7.3 Relationship To Fixed A001 C3/C4

Fixed A001 C3/C4 should be downgraded to:

- selection-layer prototype;
- fixed-bank baseline;
- factor ownership diagnostic;
- candidate-pool ceiling reference under AABB proxy metrics;
- failure-analysis and leakage-boundary testbed.

Fixed A001 C3/C4 should not be described as:

- full optical-to-SAR migration;
- SAR image-driven state generation;
- proof of rotated OBB or long-axis inference;
- evidence that independent SAR proposals have no value.

### 7.4 C3/C4 Boundary

Future generated proposals must not be silently mixed into C3/C4.

Any test that runs a factor graph over generated proposals must be a separately approved Phase5D step, with separate outputs, provenance, and leakage audit.

## 8. Evaluation Boundary

### 8.1 A019 / A021 Usage

A019 and A021 are evaluation-only after inference.

Allowed uses:

- post-inference metric computation;
- oracle ceiling analysis;
- condition-group failure analysis;
- visual audit queue generation;
- human interpretation of failure cases.

Forbidden uses:

- proposal generation;
- proposal filtering;
- ranking score computation;
- factor graph inference;
- shell contraction;
- threshold tuning;
- training or calibration;
- panel-review feedback into the model.

### 8.2 Forbidden Leakage Sources

The following information must not enter inference-side proposal generation or scoring:

- A019 `final_*` fields;
- GT boxes or manually finalized boxes;
- oracle best-candidate labels;
- IoU or center-error labels;
- A021 condition / truncation / occlusion labels;
- panel review outcomes;
- selected/failure labels created after evaluation.

### 8.3 Audit Rule

Every future proposal or factor-graph output should be auditable by asking:

1. Which fields were available before inference?
2. Which fields were joined only after inference?
3. Could any metric, label, final box, oracle choice, or panel review have influenced proposal generation or ranking?

If the answer to question 3 is yes or unclear, the artifact is not inference-safe.

## 9. Relationship To Phase4

Phase4C, Phase4D, Phase4D geometry add-on, and Phase4D-H remain useful, but their interpretation changes.

Correct Phase4 interpretation:

- Phase4C/D/H are fixed-bank selection-layer diagnostic evidence.
- They can be retained as A001 baselines.
- They support factor ownership and failure-mode analysis.
- They define what the fixed bank can and cannot explain.

Incorrect Phase4 interpretation:

- Phase4 is not a complete optical-to-SAR migration model.
- Phase4 does not generate SAR latent vehicle states from image evidence.
- Phase4 does not prove rotated OBB alignment.
- Phase4 does not prove SAR-derived heading.
- Phase4 does not eliminate the need for independent diagnostic SAR proposal design.

The Phase4 AABB ceiling result remains valid within its metric boundary:

- A001 is not mainly pool-limited under AABB center/size proxy metrics.
- C3/C4 residual errors are mainly selection-limited under that same proxy interpretation.

But this does not decide:

- whether A001 orientation is sufficient;
- whether SAR long-axis evidence is modeled;
- whether severe truncation or partial visibility needs different state handling;
- whether independent SAR rotated proposals are useful.

## 10. Stop / Go / Hold

### STOP

- STOP A001-only ranking patch.
- STOP C6/C7 tuning.
- STOP v3 rule tuning.
- STOP heading convention deep dive for now.
- STOP active SAR proposal injection into C3/C4.

### HOLD

- HOLD proposal implementation.
- HOLD training.
- HOLD calibration.
- HOLD generated-proposal factor graph inference.
- HOLD any Phase5B/C/D execution until explicitly approved.

### GO

- GO Phase5A formulation.
- GO interface definition.
- GO leakage boundary design.
- GO diagnostic proposal design as a future documentation track.

## 11. Phase5A Deliverable Definition

Phase5A deliverable:

- problem statement for optical-conditioned SAR state inference;
- SAR latent vehicle state schema;
- optical-conditioned shell semantics;
- SAR observation layer semantics;
- proposal / particle interface fields;
- factor graph role definition;
- evaluation-only leakage boundary;
- relationship to Phase4 baseline evidence.

Phase5A non-deliverables:

- no code;
- no experiment;
- no generated candidate;
- no generated proposal;
- no C3/C4 modification;
- no A001/A005/A019/A021 modification;
- no training;
- no calibration;
- no commit unless explicitly approved.

## 12. Final Formulation

The mainline should now be stated as:

> Optical evidence defines a probabilistic SAR search shell. SAR image evidence inside that shell generates or supports latent vehicle-state hypotheses. A factor graph then integrates optical prior, SAR observation, temporal consistency, and scene geometry to infer the final SAR localization state. Fixed A001 C3/C4 results are retained only as fixed-bank selection-layer baselines and diagnostics.

This formulation prevents the fixed-bank selector from being overclaimed as the full migration model while preserving its value as a controlled baseline.

## 13. Boundary Statement

This document is documentation-only.

- No experiment was added.
- No script was added.
- No candidate was generated.
- No proposal was generated.
- No C3/C4 ranking was changed.
- No A001/A005/A019/A021 source file was modified.
- No C6/C7 tuning was performed.
- No v3 rule tuning was performed.
- No heading convention deep dive was performed.
- No model was trained.
- No calibration was performed.
- No Phase5A file was staged or committed by this document creation step.
