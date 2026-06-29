# GM17 Phase4-Extension High-IoU Precision Decomposition Spec

Date: 2026-06-29

Status: diagnostic-only draft

This document extracts Experiment A from `docs/gm17_next_diagnostic_experiment_matrix.md` into a more concrete Phase4-extension diagnostic specification. It is not an execution report and does not approve formal Phase5.

No experiment is run by this specification. No model is trained. No OOF calibration is performed. No candidate bank is modified. No GM17 mainline selector is modified. No new performance conclusion is produced.

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.

## 1. Diagnostic Goal

The diagnostic question is:

Why can GM17 show strong usable / coarse fixed-bank coverage while `coverage@0.9` and `coverage@0.95` remain weak under the current post-inference proxy audit?

The working interpretation is that coarse coverage and high-IoU precision measure different properties:

- Coarse coverage asks whether A001 contains a candidate in the right local neighborhood.
- High-IoU precision asks whether A001 contains a near-exact state under the current audit proxy.
- A candidate can be useful for coarse localization while still missing the exact center, extent, aspect, or shape hypothesis needed for high proxy overlap.
- A structured selector can only choose from candidate states that already exist; it cannot recover precision that the fixed bank does not contain.

Therefore this diagnostic decomposes the high-IoU gap into candidate-state dimensions. It is a candidate precision decomposition, not a candidate-bank modification, proposal-generation path, threshold-tuning path, or active selector design.

The diagnostic may answer questions such as:

- Are weak high-IoU cases mostly center-limited?
- Are they mostly size- or extent-limited?
- Do center and size errors interact?
- Are shape hypotheses or aspect assumptions the limiting factor?
- Is the current metric itself hiding a rotated-OBB or heading question that cannot be answered by an AABB proxy?

It must not answer:

- whether a new candidate bank should be generated;
- whether A001 should be edited;
- whether a new selector should be activated;
- whether formal Phase5 is ready;
- whether heading, orientation, or long-axis accuracy is valid.

## 2. Metric Boundary

`axis_aligned_proxy_iou` is an audit-only axis-aligned bounding-box proxy. It is not rotated IoU.

Allowed interpretation:

- post-inference proxy overlap between axis-aligned boxes;
- coarse separation of weak / medium / high proxy-overlap cases;
- diagnostic grouping after candidate scoring or selection is frozen;
- evidence that the current candidate state may be center-, size-, or shape-limited under an AABB proxy.

Forbidden interpretation:

- rotated-IoU performance;
- heading correctness;
- vehicle orientation correctness;
- SAR long-axis correctness;
- OBB convention correctness;
- selector score or training target;
- threshold used to choose candidates, anchors, routes, or parameters.

Any future rotated-OBB metric, heading error, or long-axis audit must be separately specified, separately audited, and clearly marked as outside this AABB proxy diagnostic.

## 3. Input Field Layers

### 3.1 Inference-Safe / Pre-Eval Fields

These fields may be carried into a future local diagnostic script before evaluation joins, provided they already exist in frozen candidate or selector outputs and are not derived from GT, A019, A021, IoU, oracle labels, center error, or panel review.

Candidate identity and grouping:

- `target_id`;
- `scene_id`;
- `track_id`, if already available before evaluation joins;
- `frame_id` or frame order;
- `candidate_id` or proposal id;
- `rank` and frozen score fields from a completed run, if the run already exists and is not changed by this diagnostic;
- `candidate_source`, `proposal_source`, route, or provenance fields as grouping metadata only.

Candidate geometry:

- `cx`, `cy`;
- `w`, `h`;
- stored `theta`, if already present as candidate metadata;
- candidate crop coordinates;
- shell identity or optical-conditioned local search identity.

Inference-safe evidence descriptors:

- optical-conditioned shell metadata computed before evaluation;
- temporal-prior metadata not derived from evaluation labels;
- SAR crop statistics computed without GT, A019, A021, IoU, oracle labels, center error, or panel review;
- declared missing-value flags.

These fields must not be reweighted, retuned, or converted into an active scoring rule by this spec.

### 3.2 Diagnostic-Only / Post-Inference Fields

These fields may be joined only after candidate selection, candidate ranking, or proposal scoring is frozen. They are used only for audit tables and failure buckets.

Reference and metric fields:

- GT boxes;
- A019 final boxes or manually finalized boxes;
- `axis_aligned_proxy_iou`;
- proxy high-IoU bins such as `<0.5`, `0.5-0.7`, `0.7-0.9`, `0.9-0.95`, `>=0.95`, if bins are declared before inspection;
- center error;
- `dx`, `dy`, `abs_dx`, `abs_dy`;
- width / height / area / aspect deltas;
- oracle best-candidate identity;
- rank of oracle or best-proxy candidate after frozen scoring.

Condition fields:

- A021 condition labels;
- truncation labels;
- occlusion labels;
- visibility labels;
- panel review notes;
- post-hoc manual-review decisions.

Future-only fields:

- rotated IoU;
- OBB heading error;
- long-axis support error;
- rotated-box convention audit outcomes.

Future-only fields are not part of the current AABB proxy diagnostic unless separately approved.

### 3.3 Forbidden During Scoring Fields

The following must not be used to select candidates, sort candidates, tune thresholds, choose anchors, choose routes, train weights, filter proposals, or modify a selector:

- GT boxes;
- A019 final boxes;
- A021 condition, truncation, occlusion, or visibility labels;
- oracle labels;
- `axis_aligned_proxy_iou`;
- any IoU label;
- high-IoU bin labels;
- center error;
- `dx`, `dy`, `abs_dx`, `abs_dy` when computed from GT or A019;
- panel review outcomes;
- manual-review pass/fail labels;
- future rotated-IoU / heading / long-axis labels;
- any field computed from the above.

If a future script cannot prove a field is inference-safe, the field must default to diagnostic-only or forbidden.

## 4. Decomposition Dimensions

The future diagnostic should assign each audited candidate or target to one or more post-hoc failure dimensions. The assignment is explanatory only and must not feed back into scoring.

### 4.1 Center-Limited

Definition:

The candidate has a plausible size / shape hypothesis, but its center is offset enough that high proxy overlap fails.

Audit-only evidence:

- center error;
- `dx`, `dy`, `abs_dx`, `abs_dy`;
- rank position of the best-center candidate after frozen scoring;
- comparison between rank1 and best-center candidate, after scoring is frozen.

Interpretation:

If this bucket dominates, the next diagnostic priority is center evidence: SAR local energy, radial profile, local contrast, or temporal center stability. It does not authorize candidate-bank edits.

### 4.2 Size-Limited

Definition:

The candidate center is close enough to be useful, but width, height, area, or extent mismatch prevents high proxy overlap.

Audit-only evidence:

- width error;
- height error;
- area ratio;
- extent mismatch;
- aspect-ratio gap, if computed from AABB boxes only;
- comparison against same-target candidates with similar centers but different extents.

Interpretation:

If this bucket dominates, the next diagnostic priority is center-size likelihood precision audit. The audit may explain whether existing size / extent hypotheses are too narrow, too wide, or systematically biased. It must not edit A001.

### 4.3 Center-Size Combined

Definition:

Neither center nor size alone explains the high-IoU failure. The candidate is moderately wrong in both state dimensions, and the interaction prevents high proxy overlap.

Audit-only evidence:

- joint center / size bucket;
- center error crossed with area ratio;
- `dx`, `dy` crossed with width / height deltas;
- comparison between best-center and best-proxy candidates after frozen scoring.

Interpretation:

If this bucket dominates, a one-dimensional fix is unlikely to be sufficient. Later diagnostics should test whether inference-safe center evidence and size plausibility must be evaluated together. This remains a diagnostic planning point, not an active factor.

### 4.4 Aspect / Shape-Hypothesis Limited

Definition:

The candidate has roughly plausible center and scale, but the AABB aspect, crop support, or shape hypothesis appears inconsistent with the post-inference audit reference.

Audit-only evidence:

- aspect-ratio gap;
- candidate source or route concentration after post-hoc grouping;
- shape-hypothesis type, if already present;
- SAR crop descriptor notes computed without labels and inspected only after scoring is frozen;
- manual-review case list selected after audit.

Interpretation:

If this bucket dominates, a later Experiment C may be needed to test SAR descriptor separability. The current diagnostic may only recommend that need; it must not train a classifier or activate a descriptor selector.

### 4.5 Future Rotated-OBB / Heading Audit Only

Definition:

Some failures may appear visually related to heading, vehicle orientation, or long-axis support, but `axis_aligned_proxy_iou` cannot validate that claim.

Allowed current output:

- mark the case as `FUTURE_ROTATED_OBB_AUDIT_ONLY`;
- record stored `theta` and `theta_source` as provenance only;
- note whether a separate rotated-OBB reference would be required.

Forbidden current output:

- heading correctness claims;
- orientation correctness claims;
- long-axis correctness claims;
- rotated-IoU conclusions;
- selector changes based on heading labels.

### 4.6 Proxy-Metric Limitation

Definition:

The observed weakness may partly come from the mismatch between the AABB proxy and the true SAR vehicle state. This is a metric limitation bucket, not a model result.

Audit-only evidence:

- AABB proxy failure with visually ambiguous or orientation-sensitive cases;
- cases where AABB aspect/extent looks misleading relative to SAR structure;
- cases requiring manual review or future rotated-OBB audit to interpret.

Interpretation:

If this bucket is frequent, the correct next step is to document metric insufficiency and design a separate OBB audit. It is not valid to infer rotated-box performance from the AABB proxy.

## 5. Output Table Design For A Future Local Diagnostic Script

This section defines expected table schemas only. It does not run a script and does not create outputs.

### 5.1 Target-Level Summary

Purpose:

One row per target, summarizing the best available frozen candidate and the post-hoc reason high-IoU precision did or did not fail.

Suggested columns:

| Column | Layer | Notes |
|---|---|---|
| `target_id` | inference-safe | Target key. |
| `scene_id` | inference-safe | Scene grouping. |
| `track_id` | inference-safe if pre-eval | Optional grouping. |
| `frame_id` | inference-safe | Frame key or order. |
| `rank1_candidate_id` | inference-safe from frozen run | Must come from completed outputs. |
| `best_proxy_candidate_id` | post-inference audit | Oracle-like; audit only. |
| `rank1_candidate_source` | inference-safe metadata | Grouping only. |
| `best_proxy_candidate_source` | post-inference audit | Audit only when tied to oracle role. |
| `rank1_axis_aligned_proxy_iou` | post-inference audit | AABB proxy only. |
| `best_axis_aligned_proxy_iou` | post-inference audit | AABB proxy only. |
| `rank1_center_error` | post-inference audit | Not scoring input. |
| `best_center_error` | post-inference audit | Not scoring input. |
| `failure_bucket_primary` | post-inference audit | Center, size, combined, aspect/shape, proxy limitation, future OBB. |
| `failure_bucket_secondary` | post-inference audit | Optional multi-label. |
| `manual_review_flag` | post-inference audit | Case-list routing only. |

### 5.2 Per-Scene Summary

Purpose:

Identify whether precision limits are concentrated in particular SAR scenes without producing a new mainline performance claim.

Suggested columns:

| Column | Layer | Notes |
|---|---|---|
| `scene_id` | inference-safe | Scene key. |
| `n_targets` | post-inference aggregate | Count over audited rows. |
| `n_center_limited` | post-inference aggregate | Failure bucket count. |
| `n_size_limited` | post-inference aggregate | Failure bucket count. |
| `n_center_size_combined` | post-inference aggregate | Failure bucket count. |
| `n_aspect_shape_limited` | post-inference aggregate | Failure bucket count. |
| `n_proxy_metric_limited` | post-inference aggregate | Failure bucket count. |
| `n_future_obb_audit_only` | post-inference aggregate | No heading conclusion. |
| `scene_review_priority` | post-inference audit | Manual review routing only. |

### 5.3 Per-Track Summary

Purpose:

Check whether precision failure is sequence-structured while keeping time as a stabilizer, not a dominant localization controller.

Suggested columns:

| Column | Layer | Notes |
|---|---|---|
| `track_id` | inference-safe if pre-eval | Track key. |
| `scene_id` | inference-safe | Scene grouping. |
| `n_frames` | inference-safe / aggregate | Count only. |
| `dominant_failure_bucket` | post-inference audit | Explanatory only. |
| `bucket_transition_notes` | post-inference audit | Descriptive, not scoring. |
| `center_error_pattern` | post-inference audit | Audit-only pattern label. |
| `size_error_pattern` | post-inference audit | Audit-only pattern label. |
| `needs_keyframe_confidence_audit` | post-inference recommendation | Can route to Experiment D, not Phase5. |

### 5.4 Per-Candidate-Source Post-Hoc Audit Summary

Purpose:

Group precision failures by candidate source or route after the audit. This is source-level explanation only and must not become a source-priority selector.

Suggested columns:

| Column | Layer | Notes |
|---|---|---|
| `candidate_source` | inference-safe metadata | Grouping only. |
| `n_candidates_audited` | post-inference aggregate | Count over frozen outputs. |
| `n_targets_with_source_as_rank1` | post-inference aggregate | Descriptive. |
| `n_targets_with_source_as_best_proxy` | post-inference audit | Oracle-like; audit only. |
| `center_limited_share` | post-inference aggregate | Explanatory. |
| `size_limited_share` | post-inference aggregate | Explanatory. |
| `aspect_shape_limited_share` | post-inference aggregate | Explanatory. |
| `proxy_metric_limited_share` | post-inference aggregate | Explanatory. |
| `source_risk_note` | post-inference audit | Manual note, no selector promotion. |

### 5.5 Failure Bucket Table

Purpose:

Provide the main decomposition result as a diagnostic table, not a performance leaderboard.

Suggested columns:

| Column | Layer | Notes |
|---|---|---|
| `failure_bucket` | post-inference audit | Controlled vocabulary. |
| `definition` | spec metadata | Human-readable definition. |
| `n_targets` | post-inference aggregate | Count. |
| `share_of_audited_targets` | post-inference aggregate | Diagnostic proportion. |
| `common_candidate_sources` | post-inference aggregate | Source grouping only. |
| `common_scene_ids` | post-inference aggregate | Scene grouping only. |
| `common_track_patterns` | post-inference aggregate | Track grouping only. |
| `recommended_next_experiment` | post-inference recommendation | B, C, D, or HOLD. |
| `promotion_allowed` | spec metadata | Always `no` for selector / Phase5. |

### 5.6 Manual Review Case List

Purpose:

Create a bounded list of examples for human interpretation after all scoring is frozen. The list may support future audit design but cannot feed back into the current diagnostic scoring.

Suggested columns:

| Column | Layer | Notes |
|---|---|---|
| `case_id` | post-inference audit | Stable review key. |
| `target_id` | inference-safe | Target key. |
| `scene_id` | inference-safe | Scene key. |
| `track_id` | inference-safe if pre-eval | Optional. |
| `rank1_candidate_id` | inference-safe from frozen run | Completed output only. |
| `best_proxy_candidate_id` | post-inference audit | Oracle-like; audit only. |
| `primary_review_reason` | post-inference audit | Center, size, aspect, proxy limitation, future OBB. |
| `aabb_proxy_warning` | spec metadata | Remind reviewer that proxy is not rotated IoU. |
| `forbidden_feedback_warning` | spec metadata | Must not be used for scoring updates. |
| `review_note` | post-inference audit | Human note, not a selector input. |

## 6. Stop / Hold / Go Gate

### GO To Experiment B

Proceed to Experiment B, renamed as a center-size likelihood precision audit, only if all conditions hold:

- scoring or candidate ranking is frozen before any GT / A019 / A021 / IoU / center-error join;
- the decomposition identifies a clear center, size, or center-size interaction pattern;
- the proposed center-size likelihood can be defined from inference-safe fields only;
- output wording remains diagnostic-only;
- no candidate-bank edit, candidate generation, selector change, threshold tuning, training, or OOF calibration is required.

### GO To Experiment C

Proceed to Experiment C only if aspect / shape-hypothesis limitation appears material and SAR descriptor separability is needed to explain it.

Experiment C must compute descriptors without GT, A019, A021, IoU, oracle labels, center error, or panel review. Post-hoc labels may be joined only after descriptor extraction is frozen.

### HOLD

Hold the research thread if:

- failure buckets are diffuse and no component explains a meaningful share of weak high-IoU cases;
- metric limitations dominate and a separate rotated-OBB / heading audit is needed first;
- required provenance fields are missing or mixed with post-inference labels;
- field origin cannot be proven;
- the diagnostic would require selector tuning to become interpretable.

### STOP

Stop immediately if any of the following happens:

- GT, A019, A021, IoU, oracle labels, center error, or panel review are used during scoring;
- `axis_aligned_proxy_iou` is treated as rotated IoU;
- heading, orientation, or long-axis conclusions are inferred from the AABB proxy;
- the diagnostic starts modifying A001 or any candidate bank;
- the diagnostic changes the GM17 mainline selector;
- thresholds are tuned from post-hoc labels;
- model training is proposed or started;
- OOF calibration is started or approved;
- formal Phase5 is treated as approved.

## 7. Relationship To Later Experiments

This spec is the first decomposition step. It may route later diagnostic work, but it cannot directly promote any factor into the mainline.

If center error dominates:

- follow-up should inspect inference-safe center evidence;
- likely diagnostic targets include SAR local energy, radial profile, contrast, center stability, and candidate center provenance;
- this may inform a future center-evidence audit, not a candidate-bank edit.

If size, extent, or aspect dominates:

- follow-up should inspect center-size likelihood precision audit;
- the wording should avoid `candidate_refinement` unless explicitly defined as non-mutating diagnostic decomposition;
- no candidate geometry may be moved, generated, or inserted into A001.

If aspect / shape hypotheses remain unclear:

- proceed to Experiment C only as SAR descriptor separability audit;
- descriptors must be frozen before post-hoc labels are joined;
- no trained classifier, active selector, or Phase5 claim may be produced.

If keyframe or temporal consistency becomes relevant:

- route to Experiment D or E only after the underlying confidence source is inference-safe;
- GT / IoU / center error may validate confidence post hoc but cannot choose anchors.

If metric limitation dominates:

- design a separate rotated-OBB / heading audit;
- do not reinterpret `axis_aligned_proxy_iou` as heading evidence.

No route from this spec goes directly to formal Phase5. Formal Phase5 remains blocked until OOF calibration governance, leakage audits, double-counting checks, missing-value policy, field allowlist / denylist, and release approval are separately completed.

## 8. Non-Actions In This Draft

- No experiment was run.
- No model was trained.
- No OOF calibration was performed.
- No candidate bank was modified.
- No GM17 selector was modified.
- No candidate geometry was moved or generated.
- No new performance conclusion was produced.
- No file staging or commit is authorized by this document.
