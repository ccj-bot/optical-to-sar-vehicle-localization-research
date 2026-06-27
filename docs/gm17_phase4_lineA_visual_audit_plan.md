# GM17 Phase4 Line A Visual Audit Plan

This is a non-executing human visual audit plan for Line A: the SAR-domain physical prior audit over manual-GT-covered samples in GM_RM011, GM_RM017, and GM_RM019.

The plan is seeded by `docs/gm17_phase4_sar_domain_physical_prior_audit_summary.md`. It does not run inference, select candidates, compute model performance, tune thresholds, fit weights, calibrate models, generate candidate banks, or activate any candidate-level factor.

# Scope And Positioning

Line A is the all-GT-covered SAR-domain physical prior audit. It uses A019 and A021 only as descriptive GT-domain audit evidence:

- A019 `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv`
- A021 `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv`

A001 and A005 remain Line B-only. They must not be used in this visual audit plan, because the current A001 candidate bank and A005 temporal prior support only the GM_RM017 candidate-level pilot.

GT in this plan is allowed only for:

- physical distribution review;
- annotation convention review;
- failure-mode review;
- post-inference evaluation planning.

GT in this plan is forbidden as inference evidence, candidate-selection evidence, threshold-tuning evidence, learned-weight evidence, or candidate-bank generation evidence.

GM17 remains a staged evidence source, candidate-structure source, feature/field source, failure-case source, selected-behavior reference, and patch-dependency risk exposure. GM17 is not the final model template. B patch reproduction is not physical proof.

# Why Visual Audit Is Needed

The descriptive Line A summary found several issues that cannot be resolved from table statistics alone.

GM_RM011 has an aspect-ratio split. Its median `final_w/final_h` is much lower than GM_RM017 and GM_RM019, while its upper quartile overlaps the long-axis convention seen elsewhere. A human reviewer must determine whether this is physical diversity, heading convention, width/height assignment convention, visible-extent annotation, truncation, boundary behavior, or mixed annotation practice.

Width and height convention is uncertain. `final_w` and `final_h` may not mean the same physical axis across all scenes or headings. Visual inspection should decide whether the width/height fields are consistently tied to an oriented-box long axis, image axes, or a scene-specific annotation convention.

Heading has wraparound and sign-convention risk. `final_heading_deg` includes negative values and values near 359 degrees. This requires visual review before any future heading prior, angle-normalization convention, or circular-statistics interpretation is declared.

Severe truncation and severe occlusion are common enough to affect physical-prior interpretation. Truncation dominates GM_RM011 and GM_RM019, while GM_RM017 contains the main non-truncated subset. A human reviewer should identify which cases represent full-vehicle boxes, visible-extent boxes, or ambiguous partial-visibility situations.

Axis-aligned area extremes may reflect rotated boxes, boundary conditions, or annotation inconsistency. The visual audit should distinguish rotation-induced axis-aligned expansion from genuine abnormal footprint or annotation issues.

GM_RM019 has a low-sample warning. It has only 25 rows, so representative visual inspection is needed before treating it as a stable physical-prior source.

# Human Visual Audit Categories

| audit category | review objective | evidence to inspect | expected reviewer question | allowed conclusion type | forbidden conclusion type |
|---|---|---|---|---|---|
| GM_RM011 low-aspect-ratio cases | Determine whether low `final_w/final_h` reflects vehicle orientation, box convention, truncation, visible extent, or annotation inconsistency. | SAR pseudocolor frame, final OBB, `final_w`, `final_h`, `final_heading_deg`, A021 condition labels. | Is the OBB long vehicle axis encoded as `final_h`, or is this a partial/boundary visible-extent box? | Convention note; failure-mode registry update; uncertainty/caveat note. | Scoring threshold; exclusion rule; learned weight; candidate-selection rule. |
| High-aspect-ratio cases | Check whether high aspect ratio is a valid long-axis vehicle box or an over-extended annotation. | SAR pseudocolor frame, final OBB, axis-aligned extent, condition labels. | Does the high ratio represent a valid complete vehicle, a stretched box, or scene-specific annotation behavior? | Convention note; failure-mode registry update. | Tuned maximum aspect-ratio constant; automatic rejection rule. |
| Heading wraparound / sign-convention cases | Resolve whether negative headings and headings near 359 degrees are equivalent wraparound states or inconsistent labels. | Final OBB orientation, `final_heading_deg`, image orientation, scene convention notes. | Should headings be normalized circularly, and what sign convention is visually supported? | Convention note; post-inference evaluation planning note. | Heading scoring threshold; factor activation decision. |
| Maximum axis-aligned footprint cases | Distinguish rotation-induced large axis-aligned boxes from annotation or boundary problems. | Rotated OBB, enclosing axis-aligned box footprint, SAR target extent, boundary/mask context if visible. | Is the large axis-aligned footprint an expected result of rotation, or does it indicate an annotation issue? | Failure-mode registry update; uncertainty/caveat note. | Area threshold; candidate-bank edit; missing policy. |
| Severe truncation examples | Identify whether GT boxes represent complete vehicle extent, visible support, or a compromise annotation under missing extent. | SAR frame, final OBB, A021 `truncation_degree`, visual missing extent. | Does the final box encode full vehicle or visible portion under severe truncation? | Future-route recommendation for visibility/missing extent; failure-mode registry update. | Visibility-factor activation; missing-extent scoring rule; full-center reconstruction rule. |
| Severe occlusion examples | Determine whether occlusion changes box reliability, center placement, or extent interpretation. | SAR frame, final OBB, A021 `occlusion_degree`, nearby target clutter/support. | Does occlusion preserve enough evidence for a complete-vehicle box, or should it be treated as review-risk context? | Failure-mode registry update; uncertainty/caveat note; post-inference evaluation planning note. | Uncertainty-factor activation; SAR-structure score; candidate-selection rule. |
| GM_RM019 representative low-n cases | Review whether GM_RM019 should remain in Line A with low-sample caveat and whether its examples are representative or special cases. | GM_RM019 seeded example, scene-level summary, condition labels. | Does the GM_RM019 sample support descriptive physical-prior context, or only a caveated future audit route? | Uncertainty/caveat note; future-route recommendation. | All-scene validation claim; GM_RM019 candidate-bank generation. |
| Possible boundary/mask/visible-extent cases | Flag whether boundary, mask, or visible-extent behavior needs a future audit layer. | Rows already flagged by severe truncation, extreme aspect ratio, or extreme footprint; any visible boundary/mask context in imagery. | Is this a complete-vehicle annotation or a visible-support annotation under boundary/mask limitation? | Future-route recommendation; failure-mode registry update. | Near-field activation; visible-support-to-full-center scoring rule; candidate-bank edit. |

# Allowed And Forbidden Outputs

Allowed outputs from human visual audit:

- convention note;
- failure-mode registry update;
- future-route recommendation;
- post-inference evaluation planning note;
- uncertainty/caveat note.

Forbidden outputs from human visual audit:

- scoring threshold;
- tuned constant;
- learned weight;
- candidate-selection rule;
- missing policy;
- factor activation decision;
- candidate-bank edit;
- GM_RM011 or GM_RM019 candidate generation;
- oracle selection;
- model performance claim.

# Seeded Review Queue

This queue is seeded only from the outlier/failure examples already listed in `docs/gm17_phase4_sar_domain_physical_prior_audit_summary.md`. It is descriptive and must not become an exclusion list, threshold list, or candidate-selection list.

| review_id | audit_category | target_identity | scene | sar_frame_num | sample_id | seed reason | reviewer prompt |
|---|---|---|---|---:|---|---|---|
| VA001 | GM_RM011 low-aspect-ratio cases | `saronly_gm_rm011_000276_01` | GM_RM011 | 276 | `saronly_gm_rm011_000276_01` | Lowest observed aspect ratio: 0.3793; `final_w=68.004`, `final_h=179.282`. | Decide whether this is width/height convention, true orientation, truncation, boundary behavior, or visible-extent annotation. |
| VA002 | High-aspect-ratio cases | `gm17supp_000179_000372_det3` | GM_RM017 | 372 | `gm17supp_000179_000372_det3` | Highest observed aspect ratio: 2.7731; `final_w=194.666`, `final_h=70.198`. | Decide whether this is valid long-axis vehicle geometry or an over-extended annotation. |
| VA003 | Maximum axis-aligned footprint cases | `GM_RM011\|000005.png\|000002.png\|1\|O1:car:0.96` | GM_RM011 | 5 | blank | Smallest observed `final_ax_area_px`: 8744.4000. | Check whether compact footprint is valid or reflects truncation/visible extent. |
| VA004 | Maximum axis-aligned footprint cases | `GM_RM011\|000001.png\|000000.png\|2\|O2:car:0.87` | GM_RM011 | 1 | blank | Largest observed `final_ax_area_px`: 26360.5000. | Check whether large footprint is rotation-induced, boundary-related, or an annotation issue. |
| VA005 | Possible boundary/mask/visible-extent cases | `GM_RM011\|000012.png\|000006.png\|2\|O2:car:0.76` | GM_RM011 | 12 | blank | Smallest observed `final_rot_area_px`: 8065.3441. | Check whether the rotated footprint represents a complete vehicle or visible support. |
| VA006 | Possible boundary/mask/visible-extent cases | `frameadd_gm_rm011_000121_000252_01` | GM_RM011 | 252 | `frameadd_gm_rm011_000121_000252_01` | Largest observed `final_rot_area_px`: 17456.4340. | Check whether the footprint is physically plausible or driven by annotation/boundary behavior. |
| VA007 | Severe truncation examples | `GM_RM011\|000033.png\|000016.png\|1\|O1:car:0.88` | GM_RM011 | 33 | blank | `condition_type=truncated`, `truncation_degree=severe`. | Determine whether the final box is complete-vehicle extent or visible/partial extent. |
| VA008 | Severe truncation examples | `frameadd_gm_rm017_000152_000317_01` | GM_RM017 | 317 | `frameadd_gm_rm017_000152_000317_01` | `condition_type=truncated+occluded`, `truncation_degree=severe`. | Review combined truncation and occlusion effects on extent and center reliability. |
| VA009 | Severe truncation examples | `frameadd_gm_rm011_000161_000335_01` | GM_RM011 | 335 | `frameadd_gm_rm011_000161_000335_01` | `condition_type=truncated`, `truncation_degree=severe`. | Determine whether missing extent should remain future-route context only. |
| VA010 | Severe truncation examples | `frameadd_gm_rm011_000243_000506_01` | GM_RM011 | 506 | `frameadd_gm_rm011_000243_000506_01` | `condition_type=truncated`, `truncation_degree=severe`. | Review if the visual evidence supports complete-vehicle annotation or visible extent. |
| VA011 | Severe truncation examples | `frameadd_gm_rm011_000245_000510_01` | GM_RM011 | 510 | `frameadd_gm_rm011_000245_000510_01` | `condition_type=truncated`, `truncation_degree=severe`. | Check for boundary/mask behavior and record only a caveat if unresolved. |
| VA012 | Severe occlusion examples | `frameadd_gm_rm017_000152_000317_01` | GM_RM017 | 317 | `frameadd_gm_rm017_000152_000317_01` | `condition_type=truncated+occluded`, `occlusion_degree=severe`. | Review whether occlusion changes box reliability beyond the truncation finding. |
| VA013 | Severe occlusion examples; GM_RM019 representative low-n cases | `saronly_gm_rm019_000000_000000_01` | GM_RM019 | 0 | `saronly_gm_rm019_000000_000000_01` | `condition_type=truncated+occluded`, `occlusion_degree=severe`; GM_RM019 low-n example. | Treat as a low-sample representative check, not a scene-level validation claim. |
| VA014 | Severe occlusion examples | `saronly_gm_rm017_000145_000302_01` | GM_RM017 | 302 | `saronly_gm_rm017_000145_000302_01` | `condition_type=truncated+occluded`, `occlusion_degree=severe`. | Check whether occlusion affects final center and extent interpretation. |
| VA015 | Severe occlusion examples | `frameadd_gm_rm011_000117_000244_02` | GM_RM011 | 244 | `frameadd_gm_rm011_000117_000244_02` | `condition_type=truncated+occluded`, `occlusion_degree=severe`. | Record failure-mode context only; do not derive a scoring rule. |
| VA016 | Severe occlusion examples | `gm_rm017_00016` | GM_RM017 | 310 | `gm_rm017_00016` | `condition_type=truncated+occluded`, `occlusion_degree=severe`. | Review whether the final annotation is complete-vehicle, partial, or uncertain. |

No additional GM_RM019 representative rows are seeded here because the current summary provided only one GM_RM019 outlier/failure example. A broader GM_RM019 visual sample should be a future human-approved audit expansion, not an invented row list in this plan.

No explicit heading-wraparound rows are seeded here because the current summary reported the heading range and convention risk but did not list specific heading outlier identities. A future visual queue may add heading-specific rows after direct human approval or a separate descriptive extraction.

# Decision Log Template

| field | value |
|---|---|
| `review_id` |  |
| `target_identity` |  |
| `scene` |  |
| `sar_frame_num` |  |
| `audit_category` |  |
| `visual_finding` |  |
| `convention_implication` |  |
| `failure_mode_implication` |  |
| `allowed_downstream_use` | convention note / failure-mode registry update / future-route recommendation / post-inference evaluation planning note / uncertainty-caveat note |
| `forbidden_downstream_use` | scoring threshold / tuned constant / learned weight / candidate-selection rule / missing policy / factor activation / candidate-bank edit / candidate generation / oracle selection / model performance claim |
| `reviewer_note` |  |

Reviewer decisions should be phrased as observations and caveats. They should not be phrased as factors, costs, labels for inference, candidate filters, or data-generation instructions.

# Review Procedure

1. Open the SAR pseudocolor frame and the corresponding final GT box for the seeded row.
2. Inspect the visual relation between SAR support, final OBB, visible extent, and any boundary/mask context.
3. Compare the visual finding with the row's audit category and A021 condition labels.
4. Record only an allowed output type in the decision log.
5. If a case appears to require inference, candidate selection, candidate-bank edits, or threshold selection, mark it as forbidden for this plan and defer it to human research planning.
6. Keep Line A and Line B separated: do not consult A001/A005, candidate ranks, selected candidates, temporal priors, IoU, center error, oracle fields, or performance tables.

# How This Visual Audit Informs Future Work

This visual audit plan may inform future `geometry_factor` physical plausibility discussion by clarifying box convention, width/height interpretation, heading wraparound, and scene-specific annotation behavior.

It may inform future visibility and missing-extent route design by identifying whether severe truncation and severe occlusion cases are complete-vehicle annotations, visible-extent annotations, or unresolved failure-mode cases.

It may inform post-inference evaluation planning by identifying condition groups and caveats that should be reported after inference outputs are generated and then joined with eval-only labels.

It does not activate `visibility_factor`, `missing_extent_factor`, `sar_structure_factor`, `uncertainty_factor`, near-field route, partial-visibility route, or any candidate-level scoring. It also does not authorize GM_RM011 or GM_RM019 candidate generation, candidate-bank modification, oracle selection, threshold tuning, learned weights, calibration, or model-performance claims.
