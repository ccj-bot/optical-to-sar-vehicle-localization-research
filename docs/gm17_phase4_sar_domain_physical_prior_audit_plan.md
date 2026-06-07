# GM17 Phase4 SAR-Domain Physical Prior Audit Plan

Status: Line A SAR-domain physical prior audit plan for human review. This document defines a research audit plan only. It does not authorize experiments, inference runs, performance metrics, training, calibration, learned weights, threshold tuning, data-file modification, candidate-bank generation or modification, algorithm-code modification, executable scaffold creation, staging, commit, or push.

GM17 remains a staged evidence and feature/behavior source, not the final model template. The candidate bank is an experimental container for Line B candidate-level pilot work, not the research goal. This Line A plan is not limited by the GM_RM017-only A001 candidate-bank coverage.

## 1. Purpose

This document plans Line A: SAR-domain physical prior audit over all GT-covered samples.

The purpose is to define how to audit SAR vehicle geometry, scale, heading, visibility, truncation, occlusion, boundary behavior, and future near-field/partial-visibility evidence using manual GT coverage across GM_RM011, GM_RM017, and GM_RM019.

This is not candidate-level pilot execution and not inference. It does not score candidates, run a selector, compute metrics, tune thresholds, fit weights, calibrate, or generate a candidate bank.

## 2. Scope

The audit scope is:

- GM_RM011;
- GM_RM017;
- GM_RM019;
- all manual-GT-covered samples;
- outside-mask or boundary cases if present.

All-GT coverage is needed because SAR-domain physical priors should generalize across scenes, frame ranges, geometry conditions, and visibility conditions. A physical size, heading, aspect-ratio, or boundary-case review should not be inferred from only the GM_RM017 candidate-bank pilot when broader GT-covered SAR scenes exist.

This scope uses GT as physical-domain evidence for planning and descriptive audit only. It does not make GT an inference input, a candidate selector, or a threshold source.

## 3. Research Questions

The main scientific questions are:

- What are the SAR vehicle OBB size and aspect-ratio ranges?
- How does heading distribute across scenes?
- Are there scene-specific scale or orientation shifts?
- How do truncation, occlusion, and visibility conditions affect physical priors?
- Are outside-mask or boundary cases systematic failure modes?
- Which observations support complete-vehicle `geometry_factor`?
- Which observations should be reserved for future partial visibility or near-field routes?

The audit should identify physical-prior structure and failure-mode categories, not optimize a candidate-level model.

## 4. Data Sources

Planned sources:

- A019 `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv`;
- A021 `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv`;
- raw GM_RM011 / GM_RM017 / GM_RM019 optical and SAR frame paths where needed for provenance;
- optional mask/boundary metadata if found in existing audited docs and approved for this audit role.

A001 `candidate_bank_inference.csv` and A005 `gm17_temporal_inference.csv` are not required for Line A physical prior audit. Those belong to Line B, the GM_RM017-only optical-to-SAR candidate-level pilot.

## 5. Allowed GT Uses

Allowed GT uses:

- physical size distribution audit;
- width/height/aspect-ratio review;
- heading distribution review;
- scene-level diversity review;
- visibility/truncation/occlusion grouping;
- outside-mask and boundary-case review;
- post-inference evaluation planning;
- future partial-visibility and near-field planning.

These uses describe the SAR physical domain and organize future factor design. They do not authorize scoring or tuning.

## 6. Forbidden GT Uses

Forbidden GT uses:

- inference scoring;
- candidate selection;
- threshold tuning;
- learned weights;
- calibration;
- missing-value policy tuning by performance;
- factor activation by hindsight;
- oracle candidate selection;
- IoU/center-error use before inference;
- candidate-bank generation or expansion decisions by hindsight.

GT must not influence candidate scoring, path construction, factor inclusion, cost clipping, fixed-prior constants, missing-value behavior, or release decisions.

## 7. Physical Quantities To Audit

Planned quantities, without computing them in this round:

- `final_w`;
- `final_h`;
- `aspect_ratio = final_w / final_h`;
- `final_heading_deg`;
- `final_rot_area_px`;
- `final_ax_area_px`;
- `final_cx` / `final_cy` as spatial distribution only;
- `scene`;
- `sar_frame_num`;
- `visibility_status` if available;
- `condition_type`;
- `truncation_degree`;
- `occlusion_degree`;
- mask/boundary indicator if available.

Complete-vehicle geometry support:

- `final_w`;
- `final_h`;
- `aspect_ratio`;
- `final_heading_deg`;
- `final_rot_area_px`;
- `final_ax_area_px`;
- scene and frame coverage summaries.

Future-route support:

- `visibility_status`;
- `condition_type`;
- `truncation_degree`;
- `occlusion_degree`;
- mask/boundary indicators;
- spatial boundary cases from `final_cx` / `final_cy`;
- any later-approved near-field or geometry-regime indicator.

`final_cx` and `final_cy` are not candidate centers for inference in this audit. They may be reviewed only as spatial distribution or boundary evidence.

## 8. Grouping Plan

Planned groupings:

- by scene: GM_RM011 / GM_RM017 / GM_RM019;
- by `condition_type`;
- by `truncation_degree`;
- by `occlusion_degree`;
- by `visibility_status`;
- by in-mask vs outside-mask if metadata exists;
- by frame range if needed for temporal/scene coverage review.

Grouping should preserve outliers and boundary cases. It should not drop samples simply because they are difficult, outside a mask, truncated, occluded, or scene-imbalanced.

## 9. Factor Mapping

| audit target | factor or route | audit can inform | current role | boundary |
|---|---|---|---|---|
| OBB size, aspect ratio, heading, area, scene/frame coverage | `geometry_factor` physical scale prior | Active Phase4A domain-prior discussion for complete-vehicle geometry | physical-prior audit surface | Descriptive GT distributions cannot directly become GT-tuned scoring thresholds. |
| SAR support, scattering/shadow plausibility, shell-like support questions | `sar_structure_factor` diagnostic prior | Diagnostic-only review | diagnostic_only | Must not become active scoring until support-vs-uncertainty ownership is separated. |
| Ambiguous, artifact-like, weak-support, boundary/failure cases | `uncertainty_factor` diagnostic prior | Diagnostic-only review | diagnostic_only | Must not copy B patch or final arbitration behavior. |
| Condition/visibility groupings and visible-evidence limits | `visibility_factor` future route | Future partial-visibility planning | future_only | Visible support must not generate full center in Phase4A. |
| Truncation/occlusion effects on observed versus full extent | `missing_extent_factor` future route | Future partial-visibility schema planning | future_only | No active complete-vehicle scoring until schema and ownership are approved. |
| Visible/full-center mismatch and spatial boundary cases | `visible_full_center_offset_factor` future route | Future latent-offset planning | future_only | No visible-center shift or full-center generation in current Phase4A. |
| Geometry-regime or reliability shifts, including near-field candidates if identifiable | near-field future route | Future geometry-regime modeling | future_only | Cannot modify candidate bank, replace selector, or enter calibration. |

Line A can inform active Phase4A only at the level of physical-prior discussion for `geometry_factor`. It can also produce diagnostic and future-route evidence for SAR structure, uncertainty, visibility, missing extent, visible/full-center offset, and near-field work. It does not activate those routes as candidate scoring factors.

## 10. Interpretation Rules

Interpretation rules:

- Physical distributions can justify domain-prior discussion.
- Distributions cannot directly set GT-tuned scoring thresholds.
- Outliers should be retained and labeled, not silently removed.
- Outside-mask cases should be treated as boundary/failure-mode evidence.
- Scene imbalance must be reported.
- GM_RM019 small-sample risk must be noted if row count is low.
- Condition labels may support grouping and future-route planning, but not active scoring.
- Any physical-prior recommendation must state whether it is complete-vehicle, diagnostic-only, or future-route evidence.

The audit should distinguish descriptive physical structure from executable model rules. A descriptive pattern may motivate human review; it does not by itself define a scoring constant.

## 11. Planned Outputs For A Later Execution Round

Future outputs that may be created in a separately authorized execution round:

- physical prior summary table;
- scene-wise size/heading summary;
- condition-wise distribution summary;
- outlier/boundary case registry;
- mask coverage review;
- future partial visibility evidence table;
- future near-field evidence notes.

This document creates none of those outputs. A later execution round must remain read-only over A019/A021 and provenance inputs unless the user explicitly authorizes a broader scope.

## 12. Human Review Questions

- Should all GT-covered samples be included, even outside-mask cases?
- Which quantity is first priority: size, aspect ratio, heading, condition, mask boundary, or near-field?
- Should GM_RM019 be treated as low-sample but retained?
- Are `final_w` / `final_h` / `final_heading_deg` accepted as physical GT fields for audit only?
- Is any mask metadata available and approved?
- Should truncation/occlusion be analyzed now or only registered for Phase7?

## 13. Recommended Next Round

Preferred next round:

```text
execute a read-only SAR-domain physical prior audit summary over A019/A021, producing descriptive tables only, no inference and no model tuning
```

That round should produce the planned descriptive audit tables and registries without candidate scoring, performance metrics, learned weights, calibration, or candidate-bank changes.

Alternative next round:

```text
continue Line B by creating non-executable YAML templates for GM_RM017 geometry + optical_temporal pilot
```

Do not recommend candidate-level experiments yet.
