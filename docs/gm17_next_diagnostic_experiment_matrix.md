# GM17 Next Diagnostic Experiment Matrix

Date: 2026-06-29

## 1. Startup Guard Check

This document was drafted only after the delegated worktree guard passed.

- Current cwd used for repo work: `D:\profile\research\optical-to-sar-vehicle-localization-research-synthesis-20260629`
- Actual repo path: `D:/profile/research/optical-to-sar-vehicle-localization-research-synthesis-20260629`
- Current branch: `research/gm17-dual-bottleneck-synthesis-20260629`
- Initial `git status --short`: clean / empty

No experiment was run while drafting this file.

## 2. Purpose

This matrix defines the next GM17 diagnostic-only experiments. It is a planning document, not an execution report.

The current working diagnosis is:

- the fixed A001 bank has strong usable / coarse coverage under the current AABB proxy interpretation;
- high-IoU precision remains weak;
- the active bottleneck is dual: candidate precision plus structured selection;
- formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`;
- all future factors in this file are diagnostic-only unless separately audited and explicitly promoted;
- `cross_object_relation_factor` is future Phase8 only and is not part of these experiments.

The goal is to separate which part of the remaining error comes from candidate geometry precision, SAR evidence quality, confidence validity, temporal propagation, or future pipeline composition. None of these experiments may modify the candidate bank, patch the GM17 selector, train a model, or produce a mainline performance conclusion.

## 3. Global Leakage Boundary

### Inference-Safe Inputs

The following may be used during diagnostic scoring only when they exist before evaluation joins:

- frozen candidate or proposal geometry: `cx`, `cy`, `w`, `h`, `theta` when already present;
- frozen candidate or proposal identifiers and route/source fields;
- optical target state and optical-conditioned shell;
- temporal prior fields that are not derived from evaluation labels;
- SAR frame identity, scene identity, track identity, frame order, and local crop coordinates;
- SAR crop-derived descriptors computed without GT, oracle labels, IoU, center error, A019 final boxes, A021 condition labels, or panel review outcomes;
- predeclared diagnostic configuration.

### Diagnostic-Only / Post-Inference Inputs

The following are allowed only after scoring or proposal generation is frozen:

- A019 final boxes or manually finalized boxes;
- GT boxes;
- oracle best-candidate labels;
- IoU labels;
- center-error labels;
- A021 condition, truncation, occlusion, or visibility labels;
- panel review outcomes;
- post-hoc success/failure labels;
- any metric computed from GT or final boxes.

### Metric Semantics

`axis_aligned_proxy_iou` is audit-only. It is an axis-aligned proxy, not rotated IoU. It cannot support heading, orientation, long-axis, or rotated-OBB conclusions.

GT, IoU, oracle, and center error may be used only for post-inference audit. They cannot select candidates, tune thresholds, choose anchors, train weights, filter proposals, or decide route configuration.

## 4. Matrix Overview

| ID | Experiment | One-Line Purpose | Run Locally Later | Output Can Enter Formal Docs |
|---|---|---|---|---|
| A | High-IoU Precision Decomposition | Decompose weak high-IoU precision into center, size, heading-future, and shape-hypothesis components. | Yes, as post-inference audit. | Yes, as diagnostic evidence only. |
| B | Center-Size Likelihood Refinement Audit | Test whether a diagnostic center/size likelihood could explain precision failures without creating mainline candidates. | Yes, as offline audit. | Yes, if labeled proposal-only / diagnostic-only. |
| C | SAR Aspect Sequence Separability | Check whether SAR crop descriptors separate good and weak hypotheses after frozen scoring. | Yes, as descriptor audit. | Yes, if no selector or trained model is claimed. |
| D | Keyframe Confidence Validity | Audit whether inference-safe confidence signals actually predict precision after GT is joined. | Yes, after frozen confidence rules. | Yes, as validity / calibration audit only. |
| E | Soft Anchor Propagation Simulation | Simulate whether high-confidence frames can softly stabilize neighbors without hard labels or selector changes. | Yes, after D-style confidence is frozen. | Yes, as simulation evidence only. |
| F | Combined Pipeline Thought Experiment | Define a future combined diagnostic pipeline and promotion gates without running it. | No, document-only until A-E gates pass. | Yes, as planning / boundary material only. |

## 5. Experiment A: High-IoU Precision Decomposition

### Research Question

When high-IoU precision is weak despite strong coarse A001 coverage, which component is failing: center, size, future heading / rotated-OBB capacity, or candidate shape hypothesis?

Heading may only be recorded as a future question for rotated-IoU / OBB audit. It cannot be inferred from `axis_aligned_proxy_iou`.

### Required Inputs

- Frozen A001 or frozen diagnostic proposal output.
- Frozen inference scores / ranks if the audit is attached to a completed selector or proposal run.
- Candidate or proposal geometry: `cx`, `cy`, `w`, `h`, optional stored `theta`.
- Candidate or proposal source / route / provenance.
- Post-inference A019 or GT boxes for audit only.
- Optional future rotated-OBB audit source, if separately approved and available.

### Inference-Safe Inputs

- Candidate/proposal geometry and provenance available before evaluation.
- Optical-conditioned shell identity and temporal-prior identity.
- Candidate source or route source as diagnostic grouping metadata, not as scoring input unless separately approved.

### Diagnostic-Only Inputs

- GT / A019 final boxes.
- Oracle best-candidate identity.
- `axis_aligned_proxy_iou`.
- Center error and center-offset components.
- High-IoU bin labels.
- Any future rotated IoU, OBB heading error, or long-axis audit label.

### Post-Inference Audit Fields

- `center_error`, `dx`, `dy`, `abs_dx`, `abs_dy`.
- `w_error`, `h_error`, `area_ratio`, `aspect_ratio_gap`.
- `axis_aligned_proxy_iou`.
- `best_center_rank`, `best_proxy_rank`, `rank1_is_best_center`, `rank1_is_best_proxy`.
- `candidate_source` / `proposal_source`.
- `shape_hypothesis_type` if available.
- `stored_theta` and `theta_source` only as provenance.
- Future-only: `rotated_iou`, `obb_heading_error`, `long_axis_support_error`, if separately audited.

### Forbidden Fields During Scoring

- GT boxes, A019 final boxes, oracle labels.
- IoU, center error, high-IoU labels.
- A021 condition / truncation / occlusion labels.
- Panel review outcomes.
- `axis_aligned_proxy_iou`.
- Any heading or orientation label derived from GT or rotated-OBB audit.

### Expected Diagnostic Output

- A decomposition table separating center-limited, size-limited, combined center-size limited, and shape-hypothesis-limited cases.
- A heading / orientation section marked `FUTURE_ROTATED_OBB_AUDIT_ONLY`.
- Per-source and per-route summaries showing whether weak high-IoU precision is concentrated in specific candidate families.
- Examples for manual review, selected after the audit and not fed back into scoring.

### Failure Interpretation

- If center error dominates, the candidate or proposal needs better SAR center evidence.
- If size or aspect dominates, the bank/proposal family may have usable coarse centers but weak extent precision.
- If AABB proxy is high but visual orientation looks wrong, the correct interpretation is "AABB proxy cannot answer orientation"; it is not a heading conclusion.
- If all components are weak, coarse coverage may not be enough for the local SAR state and the optical-conditioned shell should be revisited.

### Stop / Go Criterion

GO to a focused follow-up only if at least one failure component explains a meaningful share of weak high-IoU cases without using forbidden inputs during scoring.

STOP if the analysis tries to tune selector thresholds, promote heading claims from AABB proxy metrics, or use oracle labels to choose candidates.

### Can It Be Run Locally Later?

Yes. It can be run locally as a post-inference audit over frozen candidate/proposal outputs.

### Can Output Enter Formal Docs?

Yes, only as diagnostic decomposition. It cannot be reported as rotated IoU, heading validity, or active selector performance.

## 6. Experiment B: Center-Size Likelihood Refinement Audit

### Research Question

Can a diagnostic center-size likelihood explain which candidates or proposal hypotheses have better precision, without generating mainline candidates or connecting to the GM17 selector?

`center_size_likelihood_candidate_refinement` is a diagnostic proposal only. It must not create A001 replacements, modify A001, or feed C3/C4.

### Required Inputs

- Frozen candidate or proposal geometries.
- Optical-conditioned shell and temporal prior.
- Allowed vehicle size / aspect prior, if declared before audit.
- SAR local crop statistics when computed without evaluation labels.
- Frozen evaluation outputs for post-inference audit only.

### Inference-Safe Inputs

- `cx`, `cy`, `w`, `h`, optional `theta` as stored candidate metadata.
- Optical prior score or shell compatibility score computed without GT.
- SAR local support descriptors computed from the crop only.
- Predeclared center-size likelihood formula or diagnostic score fields.

### Diagnostic-Only Inputs

- GT / A019 final boxes.
- IoU and center error.
- Oracle best candidate/proposal identity.
- A021 condition labels.
- Post-hoc failure buckets.

### Post-Inference Audit Fields

- `center_size_likelihood_score`.
- `center_likelihood_component`.
- `size_likelihood_component`.
- `aspect_likelihood_component`.
- Rank of best-center / best-proxy candidate by the diagnostic likelihood.
- Agreement or disagreement with frozen selector rank.
- Post-hoc precision bins by likelihood decile.

### Forbidden Fields During Scoring

- GT, A019 final boxes, oracle best labels.
- IoU, center error, high-IoU bin.
- A021 condition / truncation / occlusion labels.
- Candidate source as a shortcut if it becomes a hidden label proxy.
- Any threshold chosen after seeing audit metrics from the same target set.

### Expected Diagnostic Output

- A likelihood-audit table over existing candidates/proposals.
- Decile or bucket summaries showing whether the diagnostic likelihood correlates with post-hoc precision.
- A disagreement list where likelihood favors a candidate that the current structured selector misses.
- A leakage checklist proving no generated row entered the mainline bank or selector.

### Failure Interpretation

- If likelihood has no relationship to post-hoc precision, center-size evidence is not enough and SAR observation factors need richer descriptors.
- If likelihood finds good candidates that the selector misses, structured selection remains a bottleneck.
- If likelihood only recovers oracle behavior after GT-shaped tuning, the proposal is invalid for inference.

### Stop / Go Criterion

GO to a stricter preregistered diagnostic spec only if the likelihood is defined entirely from inference-safe fields and shows post-hoc explanatory value.

STOP if it creates new mainline candidates, changes rank outputs, uses GT-derived thresholds, or is proposed as a selector patch.

### Can It Be Run Locally Later?

Yes. It can be run as an offline audit over frozen candidate/proposal tables.

### Can Output Enter Formal Docs?

Yes, if framed as a diagnostic likelihood audit. It cannot be described as a promoted candidate generator or selector component.

## 7. Experiment C: SAR Aspect Sequence Separability

### Research Question

Do SAR aspect-sequence descriptors separate precise and imprecise hypotheses after frozen inference outputs exist?

The purpose is descriptor separability, not model training and not active selection.

### Required Inputs

- SAR display or raw crop source, with source type declared.
- Frozen candidate/proposal windows or crop coordinates.
- Frozen target/frame identities.
- Post-inference audit table for labels and precision grouping.

### Inference-Safe Inputs

The descriptor set may include:

- `E_left`
- `E_center`
- `E_right`
- `lr_asymmetry`
- `center_dominance`
- `mirror_symmetry`
- `scatter_centroid_dx`
- `scatter_centroid_dy`
- `scatter_compactness`
- `peak_count`
- `local_background_contrast`

All descriptors must be computed from SAR evidence and frozen candidate/proposal geometry without GT, IoU, oracle, A019, A021, or panel review.

### Diagnostic-Only Inputs

- Good/bad labels derived from post-hoc center error or `axis_aligned_proxy_iou`.
- GT / A019 final boxes.
- A021 visibility / truncation / occlusion labels.
- Oracle best-candidate identity.
- Manual review tags.

### Post-Inference Audit Fields

- Descriptor distributions by post-hoc precision bucket.
- Single-descriptor separability summaries.
- Pairwise descriptor interaction notes, without training a model.
- Descriptor missingness / instability flags.
- Condition-group breakdown joined only after descriptor extraction.

### Forbidden Fields During Scoring

- GT or A019 geometry.
- IoU, center error, oracle labels.
- A021 condition labels.
- Panel review labels.
- Descriptor thresholds chosen after reading audit precision from the same run.
- Learned weights or trained classifier outputs.

### Expected Diagnostic Output

- A descriptor dictionary and per-descriptor separability report.
- A table of which descriptors are stable, unstable, informative, or misleading.
- Example crops for later human review, selected post-hoc.
- A recommendation of whether SAR aspect evidence is worth a separately audited factor proposal.

### Failure Interpretation

- If descriptors are noisy or non-separable, display-image SAR aspect evidence is too weak or the crop convention is wrong.
- If descriptors separate only after A021 condition joins, they are condition diagnostics rather than inference factors.
- If descriptors separate good centers but not extents, SAR aspect evidence may help center confidence but not high-IoU precision.

### Stop / Go Criterion

GO to a preregistered SAR-aspect diagnostic factor only if descriptors are computable without leakage, stable across the target set, and show post-hoc separability.

STOP if separability depends on GT-informed thresholds, manual labels, or training.

### Can It Be Run Locally Later?

Yes. It can run locally as a descriptor extraction and post-inference separability audit.

### Can Output Enter Formal Docs?

Yes, as descriptor-audit evidence. It cannot be claimed as a trained detector or active SAR factor without a later audit.

## 8. Experiment D: Keyframe Confidence Validity

### Research Question

Can inference-safe confidence signals identify keyframes whose localization is genuinely more precise after post-hoc audit?

The confidence source may only come from inference-safe or diagnostic-safe evidence such as factor agreement, rank margin, candidate-source consensus, low uncertainty, SAR aspect match, or local temporal consistency. GT/IoU may be used only after confidence is frozen.

### Required Inputs

- Frozen candidate/proposal scores and ranks.
- Factor agreement fields, if available before evaluation.
- Rank margin or score margin fields.
- Candidate/proposal source consensus fields.
- Uncertainty flags.
- SAR aspect match descriptors from an inference-safe descriptor pass.
- Local temporal consistency fields not derived from evaluation labels.
- Post-inference audit table.

### Inference-Safe Inputs

- Factor agreement among predeclared factors.
- Rank margin or score margin.
- Candidate-source consensus, only as agreement metadata and not as an oracle shortcut.
- Low uncertainty flags from proposal generation or scoring.
- SAR aspect match from crop descriptors.
- Local temporal consistency computed without GT.

### Diagnostic-Only Inputs

- GT / A019 final boxes.
- IoU and center error.
- A021 condition labels.
- Oracle best labels.
- Manual review outcomes.

### Post-Inference Audit Fields

- Confidence bin.
- Precision by confidence bin.
- High-confidence false-positive list.
- Low-confidence true-positive list.
- Reliability / calibration-style summary.
- Condition breakdown joined after confidence assignment.

### Forbidden Fields During Scoring

- GT, A019 final boxes, IoU, center error.
- A021 labels.
- Oracle best identity.
- Post-hoc success/failure labels.
- Thresholds or bins chosen after reading the audit result from the same target set.

### Expected Diagnostic Output

- A frozen keyframe-confidence table.
- Reliability bins comparing confidence to post-hoc precision.
- A list of invalid confidence sources that look predictive only because of leakage.
- A decision on whether confidence can be used for later soft-anchor simulation.

### Failure Interpretation

- If high confidence is not more precise, keyframe confidence is invalid and must not drive propagation.
- If confidence works only for normal/non-truncated cases after A021 joins, it is not inference-safe.
- If confidence separates center precision but not high-IoU precision, it may be useful for center anchoring only.

### Stop / Go Criterion

GO to Experiment E only if confidence is frozen before GT audit and high-confidence bins have materially better post-hoc precision.

STOP if confidence depends on GT, condition labels, or post-hoc chosen thresholds.

### Can It Be Run Locally Later?

Yes. It can run locally after a confidence rule is preregistered and frozen.

### Can Output Enter Formal Docs?

Yes, as a confidence-validity audit. It cannot be described as calibrated production confidence until OOF calibration is separately available.

## 9. Experiment E: Soft Anchor Propagation Simulation

### Research Question

If keyframe confidence is valid, can high-confidence frames softly stabilize neighboring frames without hard GT anchors, candidate-bank edits, or selector changes?

This is a simulation of propagation behavior, not active inference.

### Required Inputs

- Frozen per-frame candidate/proposal outputs.
- Track identity and frame order.
- Predeclared keyframe confidence from Experiment D or an equivalent frozen confidence rule.
- Local temporal consistency fields.
- Optical-conditioned shell / temporal prior.
- Post-inference audit table for evaluation only.

### Inference-Safe Inputs

- Track and frame adjacency.
- Frozen candidate/proposal geometry.
- Frozen confidence bins or scores.
- Temporal smoothness prior that is not fitted to GT.
- SAR aspect match and uncertainty flags if already computed safely.

### Diagnostic-Only Inputs

- GT / A019 final boxes.
- IoU and center error.
- A021 condition labels.
- Oracle labels.
- Post-hoc failure groups.

### Post-Inference Audit Fields

- Anchor frame id and confidence source.
- Propagation target frame id.
- Simulated offset or soft-prior influence.
- Before/after post-hoc center error and `axis_aligned_proxy_iou`, audit-only.
- Harm cases where propagation degrades a frame.
- Condition breakdown joined only after simulation output is frozen.

### Forbidden Fields During Scoring

- Choosing anchors by GT, IoU, center error, or A021 condition.
- Adjusting propagation strength after seeing target-set metrics.
- Hard-overwriting SAR localization with optical or neighbor-frame boxes.
- Writing propagated candidates into A001.
- Feeding simulated outputs into C3/C4.

### Expected Diagnostic Output

- A propagation-simulation table with original and simulated hypotheses kept separate.
- Harm/help buckets.
- A statement of whether confidence-driven anchoring is plausible or unsafe.
- A proof that no candidate bank or selector output was modified.

### Failure Interpretation

- If propagation helps only by copying labels across frames, the mechanism is invalid.
- If high-confidence anchors harm neighbors under truncation or fan-edge cases, propagation should remain blocked.
- If propagation helps center but worsens extent, it may be limited to soft center priors.

### Stop / Go Criterion

GO to a future preregistered propagation factor only if D validates confidence and E shows help without unacceptable harm.

STOP if propagation requires GT-selected anchors, hard state overwrite, candidate-bank edits, or selector integration.

### Can It Be Run Locally Later?

Yes, after Experiment D produces a frozen confidence rule.

### Can Output Enter Formal Docs?

Yes, as simulation evidence only. It cannot be presented as active temporal inference or formal Phase5 performance.

## 10. Experiment F: Combined Pipeline Thought Experiment

### Research Question

If A-E identify useful diagnostic components, what would a combined future pipeline look like while preserving the fixed-bank baseline, blocked formal Phase5 status, and no-leakage boundary?

This is a thought experiment only. It does not run the combined pipeline.

### Required Inputs

- Diagnostic conclusions from A-E, if available.
- Existing Phase4/Phase5 boundary docs.
- Factor allowlist / denylist.
- OOF calibration blocker status.

### Inference-Safe Inputs

- Only factors that passed separate leakage and stability audits.
- Frozen candidate/proposal geometry.
- Optical-conditioned shell and temporal prior.
- SAR descriptors proven computable without GT or condition labels.
- Keyframe confidence proven valid without GT.

### Diagnostic-Only Inputs

- Audit summaries from A-E.
- GT / IoU / oracle / center-error summaries used only to justify diagnostic next steps.
- A021 condition summaries used only for failure interpretation.

### Post-Inference Audit Fields

- Proposed module boundary.
- Factor eligibility state: `allowed`, `diagnostic_only`, `future_only`, or `blocked`.
- Promotion dependency list.
- Failure-mode coverage map.
- Leakage-risk table.
- OOF calibration blocker status.

### Forbidden Fields During Scoring

- Any direct use of GT, IoU, oracle, center error, A019, A021, or panel review.
- `axis_aligned_proxy_iou` as a score.
- `cross_object_relation_factor`; it remains Phase8 only.
- Trained weights or calibration parameters without OOF approval.
- Any active candidate-bank, selector, C3/C4, or Phase5 promotion.

### Expected Diagnostic Output

- A future-pipeline sketch with module boundaries.
- A stop/go table for each candidate factor.
- A statement that formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.
- A list of what must be audited before any factor can move beyond diagnostic-only.

### Failure Interpretation

- If A-E results conflict, the pipeline should remain split by diagnostic component rather than fused.
- If factors require OOF calibration, formal promotion remains blocked even if local post-hoc results look good.
- If any component relies on evaluation labels during scoring, it is rejected.

### Stop / Go Criterion

GO only to a written preregistered design if A-E provide non-leaky, stable diagnostic evidence.

STOP if the thought experiment becomes implementation, selector tuning, candidate-bank modification, or performance claiming.

### Can It Be Run Locally Later?

No. It is document-only until A-E gates pass and a separate implementation request is approved.

### Can Output Enter Formal Docs?

Yes, as planning and boundary material. It cannot enter formal results as executed evidence.

## 11. Explicit Non-Actions

This matrix does not:

- run an experiment;
- train a model;
- modify candidate bank A001;
- generate mainline candidates;
- modify the GM17 selector;
- compute new performance metrics;
- join eval-only fields into inference;
- promote Phase5;
- use `cross_object_relation_factor`;
- commit, push, or merge.

## 12. ResearchOps Handoff Summary

- Experiment A: decomposes weak high-IoU precision into center, size, future heading/OBB, and shape-hypothesis components.
- Experiment B: audits a center-size likelihood proposal without generating mainline candidates or touching the selector.
- Experiment C: tests whether SAR aspect descriptors are separable after frozen inference-safe extraction.
- Experiment D: validates whether inference-safe confidence predicts post-hoc precision.
- Experiment E: simulates soft anchor propagation only after confidence validity is established.
- Experiment F: sketches a future combined diagnostic pipeline while keeping formal Phase5 blocked.

All six items are diagnostic-only by construction.
