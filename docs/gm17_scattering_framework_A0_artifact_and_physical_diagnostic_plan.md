# GM17 Scattering Framework A0 Artifact And Physical Diagnostic Plan

Date: 2026-06-29

Status: research execution planning draft

## 1. Purpose

This document defines the next step after the GM17 Scattering-Aware Candidate State Inference Framework and its execution bridge.

The immediate goal is not to run Experiment A, B, C, D, E, or F.

The immediate goal is:

```text
A0. Artifact Resolver + Schema Lock + Physical Opportunity Audit
```

This A0 step must determine:

1. which concrete files belong to the fixed-bank diagnostic line;
2. which files are only generated-proposal / Phase5B line and must not be mixed in;
3. which headers, keys, and field aliases exist;
4. which fields are inference-safe, diagnostic-only, post-inference audit, forbidden, or future-only;
5. which physical SAR information can later be used for center-size, scattering-offset, aspect-sequence, and keyframe diagnostics.

This document is not an experiment report.

It does not approve formal Phase5.

It does not run diagnostics.

It does not train models.

It does not modify candidate bank.

It does not modify GM17 selector.

It does not produce a new performance conclusion.

Formal Phase5 remains:

```text
BLOCKED_FOR_OOF_CALIBRATION
```

## 2. Why A0 Must Exist Before Experiment A

The current execution bridge already shows that the synthesis worktree lacks actual GM17 candidate/eval CSV/JSON outputs. Many paths are known only as document/config clues.

Therefore, directly implementing Experiment A is unsafe.

The main risks are:

1. reading the wrong candidate bank;
2. mixing fixed-bank A001 diagnostics with generated-proposal Phase5B outputs;
3. using eval-only fields during scoring;
4. treating `axis_aligned_proxy_iou` as if it were rotated IoU;
5. drawing heading/orientation conclusions from AABB proxy metrics;
6. interpreting old pilot outputs as current frozen outputs;
7. losing the distinction between candidate precision scarcity and structured selection failure.

A0 should lock the data layer before any diagnostic computation.

## 3. Two Artifact Lines

All artifact search must separate two lines.

### 3.1 Line-FB: Fixed-Bank Diagnostic Line

This is the current allowed line.

It contains fixed candidate bank and frozen selection/evaluation artifacts.

Allowed purpose:

```text
diagnose fixed-bank candidate precision + structured selection
```

Possible artifacts:

* A001 fixed candidate bank;
* A005 optical temporal prior;
* frozen ranked candidate output;
* selected rank1 output;
* per-target audit/evaluation table;
* A019 final boxes, post-inference only;
* A021 condition/visibility labels, post-inference only;
* SAR image or crop source, if available;
* field dictionary and manifest docs.

### 3.2 Line-GP: Generated-Proposal / Phase5B Diagnostic Line

This line may exist as local outputs, but it is not the current fixed-bank line.

Allowed purpose:

```text
path clue only, unless separately approved
```

Forbidden current use:

* do not mix proposal candidates into fixed-bank high-IoU conclusion;
* do not use generated proposal outputs to claim A001 ceiling;
* do not use Phase5B outputs to justify formal Phase5;
* do not use proposal route as candidate-bank modification authorization.

Any artifact from Line-GP must be marked:

```text
NOT_FOR_FIXED_BANK_CONCLUSION
```

## 4. A0 Required Artifacts

A0 should attempt to locate the following artifacts, but only in read-only mode.

| Artifact ID                   | Line                | Required For | Expected Role                                                  |
| ----------------------------- | ------------------- | ------------ | -------------------------------------------------------------- |
| `A001_candidate_bank`         | Line-FB             | A/B/C/D/E    | frozen candidate geometry and candidate identities             |
| `A005_optical_temporal_prior` | Line-FB             | B/D/E        | optical prior and temporal context                             |
| `frozen_ranked_candidates`    | Line-FB             | A/D/F        | frozen rank/score reference                                    |
| `selected_rank1_output`       | Line-FB             | A/F          | rank1 comparison after scoring is frozen                       |
| `per_target_audit_output`     | Line-FB             | A/F          | post-inference target-level evaluation                         |
| `A019_final_boxes`            | Line-FB, audit-only | A/F          | final boxes for post-inference audit only                      |
| `A021_condition_labels`       | Line-FB, audit-only | A/F          | condition/truncation/occlusion grouping only                   |
| `SAR_image_or_crop_source`    | Line-FB             | C/D/E        | descriptor extraction source, no labels                        |
| `field_dictionary`            | docs                | all          | field layer mapping                                            |
| `data_manifest_or_inventory`  | docs                | all          | path and field clues                                           |
| `Phase5B_outputs`             | Line-GP             | future only  | generated-proposal route, excluded from fixed-bank conclusions |

## 5. Header-Only And Metadata-Only Rules

A0 may read:

* file existence;
* file size;
* row count;
* CSV/Parquet/JSON headers;
* JSON top-level keys;
* hashes;
* modified time;
* path;
* file role;
* short sample rows only if needed for schema inference and if no metrics are computed.

A0 must not compute:

* new performance metrics;
* new IoU statistics;
* selector accuracy;
* threshold sweeps;
* calibrated weights;
* ranker outputs;
* factor scores;
* descriptor separability;
* keyframe validity;
* soft-anchor propagation results.

A0 may produce:

* artifact manifest;
* schema availability report;
* field alias map;
* field layer allowlist/denylist draft;
* STOP/HOLD/GO recommendation.

## 6. Artifact Manifest Schema

A0 should produce a small manifest table.

Suggested columns:

| Column            | Meaning                                                                                   |
| ----------------- | ----------------------------------------------------------------------------------------- |
| `artifact_id`     | canonical artifact name                                                                   |
| `line`            | `Line-FB`, `Line-GP`, `docs`, `external`, or `unknown`                                    |
| `path`            | resolved local path                                                                       |
| `exists`          | true/false                                                                                |
| `source_type`     | csv/json/parquet/image_dir/docs/config                                                    |
| `row_count`       | row count if table and cheap to inspect                                                   |
| `columns_or_keys` | column names or top-level keys                                                            |
| `hash`            | file hash if file exists and size is reasonable                                           |
| `field_layer`     | inference-safe / diagnostic-only / post-inference audit / forbidden / future-only / mixed |
| `allowed_use`     | allowed purpose                                                                           |
| `forbidden_use`   | forbidden purpose                                                                         |
| `status`          | GO / HOLD / STOP / PATH_CLUE_ONLY                                                         |
| `notes`           | concise explanation                                                                       |

The manifest is not a performance report.

## 7. Field Alias Map

A0 must create a field alias map before later scripts are written.

Canonical aliases:

| Canonical Field          | Possible Aliases                                                              | Layer                            |
| ------------------------ | ----------------------------------------------------------------------------- | -------------------------------- |
| `target_id`              | `target_identity`, `sample_id`, `case_id`                                     | inference-safe if pre-eval       |
| `scene_id`               | `scene`, `scene_name`, `gm_scene`                                             | inference-safe                   |
| `track_id`               | `gm17_track_id`, `track`, `track_num`                                         | inference-safe if pre-eval       |
| `frame_id`               | `sar_frame_num`, `sar_frame`, `frame`, `frame_idx`                            | inference-safe                   |
| `candidate_id`           | `candidate_id`, `proposal_id`, `cand_id`                                      | inference-safe for fixed bank    |
| `cx`                     | `cx`, `candidate_cx`, `box_cx`                                                | inference-safe if candidate-side |
| `cy`                     | `cy`, `candidate_cy`, `box_cy`                                                | inference-safe if candidate-side |
| `w`                      | `w`, `candidate_w`, `box_w`                                                   | inference-safe if candidate-side |
| `h`                      | `h`, `candidate_h`, `box_h`                                                   | inference-safe if candidate-side |
| `theta`                  | `theta`, `heading`, `candidate_heading`                                       | metadata only, not correctness   |
| `rank`                   | `rank`, `pilot_rank`, `selected_rank`                                         | frozen-output only               |
| `score`                  | `score`, `factor_score`, `selector_score`                                     | frozen-output only               |
| `candidate_source`       | `candidate_source`, `proposal_source`, `route`                                | grouping/provenance only         |
| `axis_aligned_proxy_iou` | `axis_aligned_proxy_iou`, `candidate_iou`, `proxy_iou`                        | post-inference audit only        |
| `center_error`           | `center_error`, `candidate_center_err_px`, `center_err_px`                    | post-inference audit only        |
| `oracle_id`              | `oracle_candidate_id`, `best_candidate_id`, `best_proxy_candidate_id`         | post-inference audit only        |
| `final_box`              | `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg`             | post-inference audit only        |
| `condition_label`        | `condition_type`, `truncation_degree`, `occlusion_degree`, `visibility_label` | post-inference audit/future-only |

If alias origin is unclear, status must be:

```text
HOLD_FOR_FIELD_ORIGIN_AUDIT
```

## 8. Physical Diagnostic Opportunity Audit

A0 should not only find tables. It should also identify what physical SAR information can later be exploited.

This does not compute descriptors. It only checks whether the inputs needed for descriptors exist.

### 8.1 Range / Azimuth Axis Opportunity

SAR image axes are not physically symmetric.

A0 should ask:

* Is image x/y convention documented?
* Is range direction known?
* Is azimuth direction known?
* Is crop coordinate convention known?
* Is vehicle fan-polar or optical-to-SAR mapping available?
* Can `dx/dy` later be decomposed into range-like and azimuth-like components?
* Are frame numbers ordered consistently with azimuth/aspect change?

If yes, later center error and scatter offset should be analyzed as:

```text
delta_range
delta_azimuth
```

not only Euclidean distance.

Important:

If the axis convention is not proven, descriptor sign and scatter offset direction must be marked:

```text
HOLD_FOR_AXIS_CONVENTION_AUDIT
```

### 8.2 Scatter-Geometry Offset Opportunity

A0 should check whether later computation can define:

```text
scatter_centroid - candidate_center
```

without using GT.

Required inputs:

* SAR image or crop source;
* frozen candidate geometry;
* candidate crop bounds;
* intensity normalization policy;
* missingness/boundary flags.

Possible future outputs:

* `scatter_centroid_dx`;
* `scatter_centroid_dy`;
* range-like / azimuth-like scatter offset;
* local compactness;
* side-biased support.

Forbidden:

* using GT center as scatter center;
* using center error to define scatter centroid;
* using final boxes to crop descriptor patches.

### 8.3 Multi-Scale Support Opportunity

A0 should check whether later descriptor extraction can use multiple support regions:

```text
inner core
candidate support
boundary ring
outer background ring
```

This helps distinguish:

* candidate too small;
* candidate too large;
* true SAR support;
* background bright clutter;
* support spill-out;
* edge/boundary missingness.

No descriptor should rely only on raw inside-box energy unless local background normalization is also considered.

### 8.4 Local Background Normalization Opportunity

SAR intensity is scene/frame dependent.

A0 should check whether future descriptor extraction can support:

* local background ring;
* robust z-score against nearby background;
* percentile normalization;
* inside-vs-ring contrast;
* missingness / edge-of-frame flags.

This prevents raw energy from becoming a scene-specific shortcut.

### 8.5 Candidate Mode Cluster Opportunity

The fixed bank may contain hundreds of candidates per target. Individual candidates may be noisy. A0 should check whether candidate geometry is rich enough for diagnostic-only clustering.

Future cluster concept:

```text
candidate mode cluster = group of candidates close in center-size state
```

Potential future fields:

* `cluster_id`;
* `cluster_center_cx`;
* `cluster_center_cy`;
* `cluster_median_w`;
* `cluster_median_h`;
* `cluster_count`;
* `cluster_source_mix`;
* `cluster_score_concentration`;
* `cluster_best_proxy_iou`, audit-only;
* `cluster_failure_bucket`, audit-only.

Use:

* distinguish isolated good candidates from stable candidate modes;
* test whether selector misses an entire plausible mode or only fine precision inside a mode.

Forbidden:

* using clusters to generate new candidates;
* using audit labels to form clusters during scoring;
* promoting cluster selection into mainline selector without separate approval.

### 8.6 Identifiability And Anti-Keyframe Opportunity

A0 should check whether future keyframe confidence can use only inference-safe signals.

Potential future signals:

* likelihood concentration;
* rank margin from frozen output;
* SAR descriptor clarity;
* missingness;
* factor agreement;
* low conflict between optical prior and SAR support;
* low descriptor ambiguity.

A keyframe should be:

```text
low entropy / high identifiability
```

Not:

```text
high post-hoc IoU frame
```

A0 should also introduce anti-keyframe / no-anchor states:

```text
anchor_allowed = high identifiability
anchor_blocked = high ambiguity or missingness
```

This prevents strong but ambiguous SAR evidence from propagating errors.

## 9. Misinterpretations To Avoid

### 9.1 Candidate Box Equals Vehicle

Wrong:

```text
candidate box = vehicle state
```

Correct:

```text
candidate box = frozen hypothesis about geometry/scattering state
```

### 9.2 Scatter Center Equals Vehicle Center

Wrong:

```text
brightest SAR point = vehicle center
```

Correct:

```text
scatter center can be offset from vehicle geometric center under aspect and background context
```

### 9.3 Temporal Means Smooth Boxes

Wrong:

```text
temporal consistency = neighboring boxes should be similar
```

Correct:

```text
SAR temporal structure = descriptor evolution should be coherent under aspect context
```

### 9.4 Keyframe Means High Score

Wrong:

```text
keyframe = highest score frame
```

Correct:

```text
keyframe = low-entropy / high-identifiability local evidence state
```

### 9.5 Candidate Source Means Ranking Evidence

Wrong:

```text
candidate_source is a source prior for selection
```

Correct:

```text
candidate_source is grouping/provenance unless separately audited
```

### 9.6 Axis-Aligned Proxy Means OBB Quality

Wrong:

```text
axis_aligned_proxy_iou supports heading/orientation conclusions
```

Correct:

```text
axis_aligned_proxy_iou is audit-only AABB proxy
```

### 9.7 Phase5B Proposals Explain Fixed Bank

Wrong:

```text
Phase5B generated proposals can be mixed into fixed-bank ceiling
```

Correct:

```text
Line-GP must remain separate from Line-FB unless explicitly approved
```

## 10. A0 STOP / HOLD / GO

### GO

Proceed with A0 if only doing:

* path resolution;
* header reading;
* JSON key reading;
* row counts;
* file hashing;
* manifest creation;
* field alias mapping;
* physical opportunity checklist.

### HOLD

Hold if:

* A001 candidate file is missing;
* frozen ranked output is missing;
* per-target audit output is missing;
* join keys are ambiguous;
* SAR image/crop source is external and unverified;
* axis/range/azimuth convention is unclear;
* candidate source is being used as scoring shortcut;
* Phase5B generated-proposal outputs are mixed with Line-FB.

### STOP

Stop immediately if:

* an experiment is run;
* metrics are recomputed;
* thresholds are tuned;
* GT/IoU/oracle/center error enters scoring;
* candidate geometry is modified;
* candidate bank is changed;
* GM17 selector is changed;
* Phase5 is treated as approved;
* model training or OOF calibration starts.

## 11. Next Script After This Plan

After this plan is saved, the first allowed script should be:

```text
tools/diagnostics/resolve_gm17_scattering_artifacts.py
```

This script should only perform A0.

Allowed script actions:

* locate candidate paths;
* check file existence;
* read headers / top-level keys;
* count rows;
* compute hashes;
* emit manifest;
* emit field alias map;
* emit STOP/HOLD/GO report.

Forbidden script actions:

* compute high-IoU decomposition;
* compute center-size likelihood;
* compute SAR descriptors;
* compute keyframe confidence;
* run soft-anchor simulation;
* train or calibrate;
* modify any source data;
* alter candidate bank or selector.

## 12. What We Can Use Later

If A0 confirms availability, the project can potentially exploit:

1. fixed candidate geometry from A001;
2. optical temporal prior from A005;
3. frozen ranking / rank margin;
4. SAR image or crop evidence;
5. local background statistics;
6. range / azimuth axis convention;
7. frame and track ordering;
8. candidate mode clusters;
9. provenance as grouping metadata;
10. post-inference A019/A021 labels for audit only;
11. high-IoU failure buckets as post-hoc explanations;
12. uncertainty / missingness flags;
13. descriptor clarity for identifiability;
14. anti-keyframe states to prevent wrong propagation.

The innovation is not merely adding features.

The innovation is building a physically interpretable diagnostic chain:

```text
frozen candidate state
-> local SAR scattering support
-> scatter-geometry offset
-> center-size plausibility
-> aspect-aware descriptor evolution
-> identifiability / anti-keyframe decision
-> local soft-anchor explanation
-> structured selection diagnosis
```

All of this remains diagnostic-only until separately approved.
