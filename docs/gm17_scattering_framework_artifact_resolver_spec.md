# GM17 Scattering Framework Artifact Resolver Spec

Date: 2026-06-30

Status: A0 resolver engineering specification

Primary plan:

- `docs/gm17_scattering_framework_A0_artifact_and_physical_diagnostic_plan.md`

Required context:

- `docs/gm17_scattering_framework_execution_bridge.md`
- `docs/gm17_scattering_aware_candidate_state_inference_framework.md`
- `docs/gm17_phase4_extension_high_iou_precision_decomposition_spec.md`
- `docs/gm17_center_size_likelihood_candidate_refinement_spec.md`
- `docs/gm17_sar_temporal_keyframe_selection_mechanism_spec.md`

This document specifies A0 only:

```text
A0. Artifact Resolver + Schema Lock + Physical Opportunity Audit
```

It does not implement the resolver script. It does not run Experiment A. It does not run any diagnostic.

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.

## 1. Purpose

A0 is the artifact, schema, and field-layer locking step before Experiment A.

Its job is to answer:

```text
Which concrete artifacts exist, which line do they belong to,
which headers/keys are available, and which field layers are safe?
```

A0 is allowed to prepare execution by resolving paths and schemas. It is not allowed to compute diagnostic results.

A0 is not:

- Experiment A high-IoU precision decomposition;
- Experiment B center-size likelihood precision audit;
- Experiment C SAR descriptor separability;
- keyframe confidence validation;
- soft-anchor propagation;
- a performance report;
- a selector patch;
- a candidate-bank modification;
- OOF calibration;
- formal Phase5 approval.

The resolver must produce engineering artifacts only:

- artifact manifest;
- schema lock;
- field alias map;
- field layer allowlist / denylist draft;
- physical opportunity checklist;
- STOP / HOLD / GO report.

## 2. Artifact Lines

The resolver must keep artifact lines separated.

### Line-FB: Fixed-Bank A001 Diagnostics

Line-FB is the only currently allowed line.

Definition:

```text
Line-FB = fixed A001 candidate bank + frozen fixed-bank selection/evaluation artifacts
```

Allowed use:

- prepare fixed-bank candidate precision diagnostics;
- prepare structured selection diagnostics over frozen candidates;
- validate schema for Experiment A;
- validate readiness for center-size likelihood and SAR descriptor audits.

Line-FB must remain fixed-bank only. It must not import generated proposal candidates, Phase5B proposal outputs, or Phase5C proposal evaluations unless a later user instruction explicitly opens that scope.

### Line-GP: Generated-Proposal / Phase5B Diagnostics

Line-GP may exist in local docs, configs, scripts, or output path clues.

Definition:

```text
Line-GP = generated proposal / Phase5B route artifacts and their post-hoc audits
```

Allowed current use:

- path clue only;
- schema clue only;
- excluded-line accounting;
- future-line inventory.

Required label:

```text
NOT_FOR_FIXED_BANK_CONCLUSION
```

Forbidden current use:

- do not mix proposal candidates into A001 fixed-bank high-IoU conclusions;
- do not use Phase5B generated proposals to claim A001 ceiling;
- do not treat Phase5B outputs as candidate-bank modification authorization;
- do not use Phase5C metrics to tune Line-FB thresholds;
- do not use generated proposal route evidence to approve formal Phase5.

### Docs / Config / External Lines

The resolver may also label artifacts as:

- `docs`: research docs, field dictionaries, manifests, bridge specs;
- `config`: frozen or draft config files;
- `external`: paths outside the repo, such as SAR image directories;
- `unknown`: unresolved candidate paths.

Docs and configs are not data tables. They can define roles and field expectations, but they cannot prove current data availability by themselves.

## 3. Required Artifacts

The resolver should attempt to locate and classify at least the following artifacts.

| Artifact ID | Line | Required For | Expected Role | Allowed Use | Forbidden Use |
|---|---|---|---|---|---|
| `A001_candidate_bank` | Line-FB | A/B/C/D/E | Fixed candidate geometry and candidate identities. | Header/schema/hash lock; fixed-bank candidate geometry source. | Modify, filter, expand, replace, or treat as generated proposal output. |
| `A005_optical_temporal_prior` | Line-FB | B/D/E | Optical prior and temporal context. | Soft context only after field approval. | Generate candidates, overwrite candidate centers, or become hard controller. |
| `frozen_ranked_candidates` | Line-FB | A/D/F | Frozen rank/score reference from a completed fixed-bank run. | Schema validation; frozen rank margin readiness. | Rerank, retune, or recompute scores. |
| `selected_rank1_output` | Line-FB | A/F | Selected rank1 output after scoring is frozen. | Post-hoc comparison against audit labels. | Use as scoring input or selector patch. |
| `per_target_audit_output` | Line-FB | A/F | Target-level post-inference evaluation/audit table. | Audit-only failure bucket readiness. | Score, filter, select, or tune candidates. |
| `A019_final_boxes` | Line-FB audit-only | A/F | Final boxes for post-inference audit only. | Audit join after scoring is frozen. | Inference input, crop source, descriptor crop, scoring field. |
| `A021_condition_labels` | Line-FB audit-only | A/F | Condition/truncation/occlusion grouping. | Post-inference grouping only. | Missingness policy, score, threshold, route choice, anchor choice. |
| `SAR_image_or_crop_source` | Line-FB / external | C/D/E | SAR image or candidate-local crop source. | Descriptor extraction readiness only after convention lock. | Use final boxes or eval labels to define crop. |
| `field_dictionary` | docs | all | Field layer classification. | Alias/layer mapping. | Proof of data existence. |
| `data_manifest_or_inventory` | docs | all | Path and field clues. | Candidate path list; expected schema. | Treat old paths as current without existence/hash check. |
| `Phase5B_generated_proposal_outputs` | Line-GP | future only | Generated proposal route outputs, excluded from fixed-bank conclusions. | Path clue / excluded-line manifest only. | Fixed-bank ceiling, A001 conclusion, selector patch, Phase5 approval. |
| `Phase5C_generated_proposal_audit` | Line-GP | future only | Post-hoc evaluation of generated proposals. | Path clue / excluded-line manifest only. | Tune Line-FB or Phase5B parameters for the same run. |

Minimum Line-FB readiness for Experiment A schema validation:

```text
A001_candidate_bank
+ frozen_ranked_candidates
+ per_target_audit_output
+ field_dictionary / manifest
```

If any of these are missing, A0 may still emit a manifest, but Experiment A must remain HOLD.

## 4. Header-Only Validation Rules

A0 may inspect only metadata and schema.

Allowed:

- path resolution;
- file existence;
- file size;
- modified time;
- file hash;
- row count;
- CSV/TSV/Parquet columns;
- JSON top-level keys;
- image directory existence and file-name pattern;
- path role classification;
- line classification: Line-FB / Line-GP / docs / config / external / unknown.

Allowed with caution:

- short sample rows only when required to infer schema type, provided no metric, distribution, threshold, or label-derived result is computed;
- path normalization;
- hash computation for source files;
- duplicate artifact path detection.

Forbidden:

- compute metrics;
- compute new IoU;
- compute center error;
- compute descriptor values;
- compute keyframe confidence;
- compute soft-anchor messages;
- compute route scores;
- tune thresholds;
- learn weights;
- run Experiment A/B/C/D/E/F;
- use eval-only fields for scoring;
- join A019/A021/GT/oracle labels into inference-facing tables;
- modify source data.

The resolver must treat `axis_aligned_proxy_iou` as post-inference audit-only AABB proxy. It must not interpret it as rotated IoU or heading/orientation evidence.

## 5. Artifact Manifest Schema

The resolver output manifest must use this schema.

| Field | Type | Required | Description |
|---|---|---|---|
| `artifact_id` | string | yes | Canonical artifact id, e.g. `A001_candidate_bank`. |
| `line` | enum | yes | `Line-FB`, `Line-GP`, `docs`, `config`, `external`, or `unknown`. |
| `path` | string | yes | Resolved path or path clue. |
| `exists` | boolean | yes | Whether the path exists at resolver time. |
| `source_type` | enum/string | yes | `csv`, `tsv`, `json`, `jsonl`, `parquet`, `image_dir`, `image_file`, `docs`, `config`, `unknown`. |
| `row_count` | integer/null | yes | Row count for table-like files when cheap and safe to inspect. |
| `columns_or_keys` | string/list | yes | Header columns or JSON top-level keys; empty if unavailable. |
| `hash` | string/null | yes | File hash if file exists and hashing is allowed. |
| `field_layer` | enum/string | yes | `inference_safe`, `diagnostic_only`, `post_inference_audit`, `forbidden`, `future_only`, `mixed`, `docs`, or `unknown`. |
| `allowed_use` | string | yes | Concise permitted use. |
| `forbidden_use` | string | yes | Concise forbidden use. |
| `status` | enum | yes | `GO`, `HOLD`, `STOP`, `PATH_CLUE_ONLY`, or `EXCLUDED_LINE`. |
| `notes` | string | yes | Short explanation of decision and uncertainty. |

Recommended status semantics:

| Status | Meaning |
|---|---|
| `GO` | Artifact exists, line is valid, schema is readable, and field layer is compatible with A0. |
| `HOLD` | Artifact is relevant but missing, ambiguous, or incomplete. |
| `STOP` | Artifact or field violates hard boundary. |
| `PATH_CLUE_ONLY` | Path appears in docs/config but does not exist or is not validated. |
| `EXCLUDED_LINE` | Artifact belongs to Line-GP or another excluded line and must not support Line-FB conclusions. |

The manifest is not a performance report and must not contain metrics summaries.

## 6. Field Alias Map

The resolver must emit a field alias map before any diagnostic script is written.

| Canonical Field | Possible Aliases | Required Line | Field Layer | Allowed Use | Forbidden Use |
|---|---|---|---|---|---|
| `target_id` | `target_identity`, `sample_id`, `case_id` | Line-FB | inference-safe if pre-eval | Target joins and grouping. | Do not infer correctness. |
| `scene_id` | `scene`, `scene_name`, `gm_scene` | Line-FB | inference-safe | Scene grouping. | Do not use as shortcut for condition labels. |
| `frame_id` | `sar_frame_num`, `sar_frame`, `frame`, `frame_idx` | Line-FB | inference-safe | Frame ordering after type check. | Do not infer physical velocity. |
| `track_id` | `gm17_track_id`, `track`, `track_num` | Line-FB | inference-safe if pre-eval | Track grouping and local sequence context. | Do not activate global propagation. |
| `candidate_id` | `candidate_id`, `cand_id` | Line-FB | inference-safe | Candidate identity. | Do not rewrite or regenerate ids. |
| `cx` | `cx`, `candidate_cx`, `box_cx` | Line-FB | inference-safe if candidate-side | Frozen candidate center x. | Do not replace with `final_cx`. |
| `cy` | `cy`, `candidate_cy`, `box_cy` | Line-FB | inference-safe if candidate-side | Frozen candidate center y. | Do not replace with `final_cy`. |
| `w` | `w`, `candidate_w`, `box_w` | Line-FB | inference-safe if candidate-side | Frozen candidate width/axis size. | Do not replace with `final_w`. |
| `h` | `h`, `candidate_h`, `box_h` | Line-FB | inference-safe if candidate-side | Frozen candidate height/axis size. | Do not replace with `final_h`. |
| `theta` | `theta`, `heading`, `candidate_heading`, `final_heading_deg` | Line-FB for candidate metadata; audit-only for `final_heading_deg` | mixed | Candidate stored angle as metadata only. | Do not infer heading/orientation correctness; never use `final_heading_deg` for inference. |
| `rank` | `rank`, `pilot_rank`, `selected_rank`, `rank1` | Line-FB frozen output | frozen-output only | Frozen run reference and schema validation. | Do not recompute or retune. |
| `score` | `score`, `factor_score`, `selector_score`, `path_score`, `node_score` | Line-FB frozen output or reference | frozen-output only / diagnostic-only | Frozen reference only after origin review. | Do not tune or train; do not mix selected-reference scores into scoring. |
| `candidate_source` | `candidate_source`, `proposal_source`, `route`, `candidate_detail`, `candidate_expansion_state`, `candidate_expansion_reason`, `provenance` | Line-FB or Line-GP | grouping/provenance only | Post-hoc grouping and artifact lineage. | Do not rank or choose candidates from source. |
| `axis_aligned_proxy_iou` | `axis_aligned_proxy_iou`, `candidate_iou`, `proxy_iou`, `rank1_proxy_iou` | audit table | post-inference audit only | AABB proxy audit after scoring is frozen. | Do not score, train, tune, or infer rotated IoU/heading/orientation. |
| `center_error` | `center_error`, `candidate_center_err_px`, `center_err_px`, role-prefixed center errors | audit table | post-inference audit only | Failure bucket assignment after scoring is frozen. | Do not define scatter centroid or keyframes. |
| `oracle_fields` | `oracle_*`, `best_candidate_id`, `best_proxy_candidate_id`, `best_center_candidate_id`, `oracle_rank_iou`, `oracle_rank_center` | audit table | post-inference audit only | Audit comparison and role accounting. | Do not choose candidates or thresholds. |
| `final_box_fields` | `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg`, `gt_*` | A019 / final boxes | post-inference audit only | Audit/evaluation join after frozen scoring. | Do not crop descriptors, score, or define inference geometry. |
| `condition_fields` | `condition_type`, `truncation_degree`, `occlusion_degree`, `visibility_label`, `partial_visible` | A021 / eval labels | post-inference audit / future-only | Group audit only after scoring. | Do not define missingness, confidence, route, score, or keyframe. |

Alias resolution rules:

1. Prefer candidate-side fields over final-box fields.
2. If an alias could be Line-FB or Line-GP, mark it `HOLD_FOR_LINE_AUDIT`.
3. If an alias could be pre-eval or post-inference, mark it `HOLD_FOR_FIELD_ORIGIN_AUDIT`.
4. If a field name contains `iou`, `oracle`, `center_err`, `final_`, `condition`, `truncation`, or `occlusion`, default to post-inference audit or forbidden until proven otherwise.
5. If `proposal_id` appears in a generated-proposal artifact, classify the artifact as Line-GP unless explicitly approved for a separate route.

## 7. Physical Opportunity Checklist

A0 must check physical readiness without computing physical descriptors.

### 7.1 Range / Azimuth Axis Convention

Checklist:

- Is image x/y convention documented?
- Is range axis direction documented?
- Is azimuth axis direction documented?
- Is fan-polar mapping available?
- Are `r`, `az`, and `cross` fields present in candidate-side artifacts?
- Is frame ordering compatible with aspect-sequence analysis?
- Is sign convention for `dx/dy` known?

Allowed A0 output:

- `axis_convention_status`;
- `range_axis_known`;
- `azimuth_axis_known`;
- `fan_polar_fields_present`;
- `HOLD_FOR_AXIS_CONVENTION_AUDIT` if unresolved.

Forbidden:

- compute `delta_range`;
- compute `delta_azimuth`;
- interpret descriptor sign as heading/orientation.

### 7.2 Scatter Centroid Offset Feasibility

Checklist:

- Is SAR image or crop source available?
- Can candidate-local patches be defined from frozen candidate geometry?
- Is crop origin stored or derivable without final boxes?
- Is image intensity available before evaluation labels?
- Are missingness / boundary flags derivable without A019/A021?

Allowed A0 output:

- whether `scatter_centroid_dx/dy` are feasible later;
- required source artifacts;
- missing blockers.

Forbidden:

- compute scatter centroid;
- use GT center as scatter center;
- use center error to define scatter offset;
- use A019/final boxes to crop candidate-local patches.

### 7.3 Candidate-Local Crop Convention

Checklist:

- Is crop coordinate system full-image or crop-local?
- Is crop origin stored?
- Are candidate boxes transformed correctly into crop coordinates?
- Is crop size/padding policy declared?
- Are boundary-touching candidates flagged?
- Can crop be computed from candidate-side fields only?

Output status:

- `GO` only if crop convention is fully pre-eval;
- `HOLD_FOR_CROP_CONVENTION_AUDIT` if any transform depends on final boxes or manual labels.

### 7.4 Multi-Scale Support Regions

Checklist:

- Can inner core, candidate support, boundary ring, and outer background ring be defined from candidate geometry?
- Can support regions handle rotated candidate metadata without making heading correctness claims?
- Is boundary clipping policy declared?
- Is missingness recorded for partial out-of-bounds support?

Allowed A0 output:

- support-region feasibility only.

Forbidden:

- compute energy;
- compute compactness;
- compare support regions by label-derived success.

### 7.5 Local Background Normalization

Checklist:

- Is a local background ring definable from candidate-side geometry?
- Can background sampling avoid final boxes?
- Can per-frame intensity normalization be declared without labels?
- Can edge/missing background be flagged?

Allowed A0 output:

- background normalization feasibility.

Forbidden:

- tune percentile thresholds from post-hoc outcomes;
- use condition labels to set normalization policy.

### 7.6 SAR Image / Crop Source

Checklist:

- Is there a committed image path field?
- Is there an external SAR image directory policy?
- Is grayscale or pseudocolor source identified?
- Is image dimension readable later by header-only checks?
- Are display-image limitations documented?

The resolver may record external paths but should not assume they are valid unless checked.

### 7.7 Frame / Track Ordering

Checklist:

- Are `frame_id` / `sar_frame_num` values present?
- Are `track_id` / `gm17_track_id` values present?
- Is ordering numeric or lexical?
- Are duplicate target/frame/track keys detectable?
- Are gaps or missing frames detectable by metadata only?

Forbidden:

- physical velocity claims;
- smoothing boxes;
- global propagation.

### 7.8 Candidate Mode Cluster Feasibility

Checklist:

- Are there enough candidates per target to define local geometry clusters later?
- Are `cx/cy/w/h` present?
- Are candidate ids stable?
- Can clusters be defined without audit labels?
- Can `candidate_source` remain provenance only?

Allowed A0 output:

- cluster feasibility status.

Forbidden:

- create new candidates;
- move candidates to cluster centers;
- use `best_proxy` or IoU labels to form clusters.

### 7.9 Identifiability / Anti-Keyframe Feasibility

Checklist:

- Are frozen rank/score fields available?
- Can likelihood concentration be computed later from inference-safe fields only?
- Are descriptor clarity fields planned but not yet computed?
- Are missingness flags available or computable without A021?
- Is there a way to mark `anchor_blocked` for ambiguous frames?

Allowed A0 output:

- keyframe readiness status;
- anti-keyframe feasibility status.

Forbidden:

- define keyframe from high IoU;
- define keyframe from center error;
- choose anchors from A021 condition labels;
- hard-lock candidates.

## 8. Misinterpretation Guardrails

The resolver spec must carry these guardrails into any future A0 script output.

| Misinterpretation | Forbidden Reading | Required Reading |
|---|---|---|
| Candidate box equals vehicle | `candidate box = vehicle` | `candidate box = frozen hypothesis about vehicle/scattering state` |
| Scatter center equals vehicle center | `brightest SAR point = vehicle center` | `scatter center may be aspect/background offset from geometry center` |
| Temporal consistency means smoothing boxes | `neighbor boxes should be similar` | `descriptor evolution and candidate-state consistency must remain local and aspect-aware` |
| Keyframe means high score | `keyframe = high score frame` | `keyframe = low-entropy / high-identifiability context` |
| Candidate source means ranking evidence | `candidate_source is selector evidence` | `candidate_source is grouping/provenance unless separately audited` |
| `axis_aligned_proxy_iou` equals rotated IoU | AABB proxy proves OBB quality | AABB proxy is audit-only and cannot support heading/orientation |
| Phase5B outputs equal fixed-bank ceiling | Generated proposals explain A001 fixed-bank ceiling | Line-GP is excluded from Line-FB conclusions |

Additional hard statements:

- `final_*` fields are post-inference audit only.
- A021 condition/truncation/occlusion labels cannot define scoring, keyframes, or missingness policy.
- Oracle fields cannot select candidates.
- Descriptor signs cannot support heading/orientation until a separate rotated-OBB / convention audit exists.
- A0 output cannot be cited as model performance.

## 9. STOP / HOLD / GO

### GO

Proceed only with:

- header/schema/hash/manifest work;
- path resolution;
- row counts;
- JSON top-level key checks;
- image directory/path existence checks;
- field alias mapping;
- field layer classification;
- physical opportunity checklist;
- STOP/HOLD/GO report.

GO does not mean Experiment A is approved. It means A0 resolver work is still within bounds.

### HOLD

Hold if:

- A001 candidate bank is missing;
- frozen ranked output is missing;
- selected rank1 output is missing when rank1 comparison is required;
- per-target audit/evaluation table is missing;
- A019/A021 audit sources are missing for post-inference grouping;
- join keys are ambiguous;
- `target_identity` / `target_id` mapping is unresolved;
- `sar_frame_num` / `frame_id` ordering is unresolved;
- `gm17_track_id` / `track_id` grouping is unresolved;
- SAR axis/crop convention is unknown;
- SAR image/crop source is external and unchecked;
- field origin is unclear;
- Line-FB and Line-GP are mixed;
- candidate source/provenance fields are being interpreted as rank evidence.

### STOP

Stop immediately if:

- metrics are computed;
- new IoU is computed;
- center error is computed;
- descriptors are computed;
- keyframe confidence is computed;
- an experiment is run;
- candidate bank is modified;
- candidate geometry is moved;
- generated proposals are mixed into fixed-bank conclusions;
- GM17 selector is modified;
- thresholds are tuned;
- weights are learned;
- OOF calibration starts;
- training starts;
- eval-only fields are used for scoring;
- `axis_aligned_proxy_iou` is treated as rotated IoU;
- heading/orientation conclusions are made from AABB proxy;
- formal Phase5 is treated as approved.

## 10. Next Script Plan

Future script name:

```text
tools/diagnostics/resolve_gm17_scattering_artifacts.py
```

This spec does not create that script. It defines the allowed contract for a later user-approved implementation.

Allowed script actions:

- locate paths from docs/config/default candidate lists;
- check existence;
- read headers;
- read JSON top-level keys;
- count rows;
- compute hashes;
- classify artifact line;
- classify field layer;
- output artifact manifest;
- output alias map;
- output physical opportunity checklist;
- output STOP/HOLD/GO report.

Forbidden script actions:

- compute diagnostic metrics;
- run Experiment A;
- run Experiment B/C/D/E/F;
- compute high-IoU decomposition;
- compute center-size likelihood;
- compute SAR descriptors;
- compute scatter centroid;
- compute keyframe confidence;
- compute soft-anchor messages;
- tune thresholds;
- train or calibrate;
- modify source data;
- modify candidate bank;
- modify GM17 selector.

Suggested future outputs:

```text
output/gm17_scattering_artifact_resolver_<timestamp>/artifact_manifest.csv
output/gm17_scattering_artifact_resolver_<timestamp>/field_alias_map.csv
output/gm17_scattering_artifact_resolver_<timestamp>/physical_opportunity_checklist.csv
output/gm17_scattering_artifact_resolver_<timestamp>/stop_hold_go_report.md
output/gm17_scattering_artifact_resolver_<timestamp>/resolver_summary.json
```

Suggested report-level invariant:

```json
{
  "experiment_ran": false,
  "metrics_computed": false,
  "candidate_bank_modified": false,
  "selector_modified": false,
  "line_gp_excluded_from_fixed_bank_conclusion": true,
  "formal_phase5_status": "BLOCKED_FOR_OOF_CALIBRATION"
}
```

## 11. Resolver Readiness Statement

The next approved implementation should start with A0 only.

The first successful A0 output should not say:

```text
Experiment A is complete.
```

It should say:

```text
Artifacts resolved, schemas locked, field layers classified,
and physical diagnostic opportunities identified.
Experiment A remains a separate later step.
```
