# Audit Scope

This document is Line A only: a read-only SAR-domain physical prior descriptive audit over all manual-GT-covered samples in GM_RM011, GM_RM017, and GM_RM019.

The audit uses A019 and A021 only:

- A019 `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv`
- A021 `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv`

A001 and A005 are not used. A001/A005 remain part of the separate GM_RM017-only Line B candidate-level pilot, not this all-GT SAR-domain physical-prior audit.

The goal is to describe the SAR GT domain: vehicle size, aspect ratio, orientation, footprint, scene coverage, and visibility/truncation/occlusion context. These summaries are not inference, candidate selection, performance evaluation, threshold tuning, model calibration, or learned prior fitting.

# Data Sources

| source | path | rows | scenes | role |
|---|---:|---:|---|---|
| A019 | `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv` | 442 | GM_RM011, GM_RM017, GM_RM019 | Manual final SAR GT boxes and review metadata. |
| A021 | `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv` | 442 | GM_RM011, GM_RM017, GM_RM019 | Visibility, truncation, and occlusion condition labels. |

Scene coverage:

| scene | A019 rows | A021 rows | sar_frame_num range in A019 |
|---|---:|---:|---|
| GM_RM011 | 201 | 201 | 0 to 510 |
| GM_RM017 | 216 | 216 | 302 to 446 |
| GM_RM019 | 25 | 25 | 0 to 354 |
| total | 442 | 442 | mixed |

Join check for descriptive condition grouping:

- Join keys used: `target_identity`, `scene`, `sample_id`, `sar_frame`, `sar_frame_num`.
- A019 matched A021 rows: 442 / 442.
- A019 unmatched rows: 0.
- A021 unmatched rows: 0.
- Multi-match A019 rows: 0.

Join limitation: the join is used only to describe GT-domain condition groupings. It does not authorize using A021 condition labels in inference, candidate scoring, fixed-prior cost construction, missing-value policy tuning, or candidate-bank generation.

# GT-Domain Field Inventory

Physical audit fields from A019:

| field | audit role | inference status |
|---|---|---|
| `final_cx`, `final_cy` | Manual GT center coordinate distribution. | Eval-only; may describe GT domain, not candidate inference. |
| `final_w`, `final_h` | Manual GT OBB size distribution. | Eval-only; may inform physical discussion, not tuned scoring thresholds. |
| `aspect_ratio = final_w / final_h` | Derived descriptive shape ratio. | Eval-only derived audit field. |
| `final_heading_deg` | Manual GT OBB orientation distribution. | Eval-only; sign/wrap convention needs review before any future factor use. |
| `final_rot_area_px`, `final_ax_area_px` | Rotated and axis-aligned footprint distribution. | Eval-only physical audit fields. |
| `scene`, `sar_frame_num` | Scene/frame grouping. | Reference grouping only. |

Condition grouping fields:

| field | audit role | inference status |
|---|---|---|
| `visibility_status` | A019 visibility status label. | Grouping/future-route evidence only. |
| `condition_type`, `condition_degree` | A021 condition type and severity. | Grouping/future-route evidence only. |
| `condition_status` | A021 review state. | Review metadata only. |
| `truncation_degree`, `occlusion_degree` | A021 truncation and occlusion severity. | Grouping/future-route evidence only. |

Reference/eval-only fields:

- Identifiers and paths: `final_id`, `target_identity`, `sample_id`, `sar_frame`, `optical_path`, `sar_pseudocolor_path`.
- Optical/reference metadata: `opt_det_id`, `opt_det_label`.
- Review provenance: `chosen_candidate_source`, `chosen_candidate_sources_merged`, `manual_adjusted`, `review_status`, `review_note`, `review_timestamp`, `condition_note`, `condition_source`.

Reference-source counts in A019:

| field/value | count |
|---|---:|
| `chosen_candidate_source=manual_adjust` | 215 |
| `chosen_candidate_source=manual_sar_supplement` | 106 |
| `chosen_candidate_source=FULL_0514_new` | 58 |
| `chosen_candidate_source=W22_0422` | 54 |
| `chosen_candidate_source=SCENE_0503_new` | 8 |
| `chosen_candidate_source=SCENE_0503_w22` | 1 |
| `manual_adjusted=1` | 321 |
| `manual_adjusted=0` | 121 |
| `review_status=reviewed` | 442 |

Center-coordinate descriptive check:

| group | field | count | missing | min | p25 | median | p75 | max | mean | std |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| overall | `final_cx` | 442 | 0 | 689.677 | 1059.503 | 1152.377 | 1222.004 | 1586.542 | 1132.092 | 146.187 |
| overall | `final_cy` | 442 | 0 | 869.331 | 942.370 | 1150.512 | 1200.366 | 1259.405 | 1080.283 | 137.850 |
| GM_RM011 | `final_cx` | 201 | 0 | 1041.691 | 1138.545 | 1167.377 | 1217.882 | 1301.341 | 1170.487 | 65.787 |
| GM_RM011 | `final_cy` | 201 | 0 | 1144.115 | 1188.002 | 1198.305 | 1246.802 | 1259.405 | 1208.535 | 32.027 |
| GM_RM017 | `final_cx` | 216 | 0 | 689.677 | 954.441 | 1089.321 | 1232.510 | 1586.542 | 1095.013 | 188.395 |
| GM_RM017 | `final_cy` | 216 | 0 | 869.331 | 882.131 | 942.261 | 1007.500 | 1013.655 | 946.284 | 52.193 |
| GM_RM019 | `final_cx` | 25 | 0 | 965.935 | 1033.125 | 1177.387 | 1257.965 | 1302.806 | 1143.759 | 117.476 |
| GM_RM019 | `final_cy` | 25 | 0 | 1186.528 | 1197.992 | 1205.403 | 1211.612 | 1231.275 | 1206.898 | 12.786 |

# Vehicle Size Distribution

Overall size distribution:

| field | count | missing | min | p25 | median | p75 | max | mean | std |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `final_w` | 442 | 0 | 63.882 | 84.489 | 145.782 | 162.053 | 198.122 | 131.934 | 37.344 |
| `final_h` | 442 | 0 | 62.847 | 70.202 | 76.384 | 156.614 | 204.011 | 102.023 | 46.527 |

By-scene size distribution:

| scene | field | count | missing | min | p25 | median | p75 | max | mean | std |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GM_RM011 | `final_w` | 201 | 0 | 63.882 | 76.246 | 82.429 | 129.942 | 151.303 | 97.605 | 27.078 |
| GM_RM011 | `final_h` | 201 | 0 | 62.847 | 65.852 | 160.736 | 177.221 | 204.011 | 134.931 | 52.414 |
| GM_RM017 | `final_w` | 216 | 0 | 137.225 | 153.978 | 161.887 | 168.436 | 198.122 | 161.793 | 11.252 |
| GM_RM017 | `final_h` | 216 | 0 | 62.896 | 71.202 | 74.774 | 78.417 | 90.716 | 74.829 | 5.030 |
| GM_RM019 | `final_w` | 25 | 0 | 133.387 | 144.410 | 147.480 | 150.903 | 182.277 | 149.956 | 12.214 |
| GM_RM019 | `final_h` | 25 | 0 | 64.500 | 69.546 | 72.000 | 74.613 | 82.244 | 72.389 | 4.179 |

Descriptive interpretation:

- No missing or nonpositive `final_w` / `final_h` values were found.
- GM_RM017 and GM_RM019 have tight height distributions near the low-70 px range.
- GM_RM011 has a much broader and taller `final_h` distribution, with median `final_h=160.736`. This likely reflects scene-specific orientation/box-convention behavior and should be reviewed before any size prior is formalized.

# Aspect Ratio Distribution

Aspect ratio is computed as `final_w / final_h` for descriptive audit only.

| group | count | missing | min | p25 | median | p75 | max | mean | std |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| overall | 442 | 0 | 0.379 | 0.515 | 2.017 | 2.178 | 2.773 | 1.635 | 0.776 |
| GM_RM011 | 201 | 0 | 0.379 | 0.437 | 0.491 | 1.986 | 2.231 | 1.007 | 0.751 |
| GM_RM017 | 216 | 0 | 1.795 | 2.042 | 2.170 | 2.287 | 2.773 | 2.169 | 0.172 |
| GM_RM019 | 25 | 0 | 1.738 | 1.936 | 2.069 | 2.166 | 2.528 | 2.077 | 0.194 |

Descriptive interpretation:

- GM_RM017 and GM_RM019 are concentrated around an approximately 2:1 width/height convention.
- GM_RM011 is not concentrated around the same convention: its median aspect ratio is 0.491, while its p75 is 1.986. This suggests a mixed or scene-dependent OBB orientation/width-height convention, not necessarily physical vehicle diversity alone.
- This audit should not convert the observed aspect-ratio range into a scoring threshold. Human review should first determine whether `final_w` and `final_h` are consistently assigned relative to heading or image axes across scenes.

# Orientation Distribution

| group | count | missing | min | p25 | median | p75 | max | mean | std |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| overall | 442 | 0 | -40.000 | -3.000 | 0.000 | 174.000 | 359.000 | 54.104 | 96.372 |
| GM_RM011 | 201 | 0 | -40.000 | -5.000 | 0.000 | 2.000 | 359.000 | 21.592 | 73.646 |
| GM_RM017 | 216 | 0 | -10.000 | -3.000 | 0.000 | 177.000 | 359.000 | 83.889 | 106.675 |
| GM_RM019 | 25 | 0 | -9.000 | 2.000 | 6.000 | 170.000 | 177.000 | 58.160 | 81.650 |

Descriptive interpretation:

- No missing `final_heading_deg` values were found.
- The heading range spans negative values and values near 359 degrees. This is consistent with a wraparound/sign-convention issue that must be explicitly reviewed before any future heading prior or heading-validity rule is declared.
- The high standard deviation is expected under a wrapped angular representation and should not be interpreted as ordinary linear dispersion without circular-angle handling.

# Area / Footprint Distribution

Overall footprint distribution:

| field | count | missing | min | p25 | median | p75 | max | mean | std |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `final_rot_area_px` | 442 | 0 | 8065.344 | 10559.227 | 11993.744 | 13140.812 | 17456.434 | 11925.581 | 2055.380 |
| `final_ax_area_px` | 442 | 0 | 8744.400 | 12196.975 | 13723.873 | 15074.087 | 26360.500 | 13989.381 | 2686.512 |

By-scene footprint distribution:

| scene | field | count | missing | min | p25 | median | p75 | max | mean | std |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GM_RM011 | `final_rot_area_px` | 201 | 0 | 8065.344 | 8775.939 | 12097.032 | 13826.678 | 17456.434 | 11843.519 | 2641.697 |
| GM_RM011 | `final_ax_area_px` | 201 | 0 | 8744.400 | 11924.281 | 13945.458 | 15495.621 | 26360.500 | 14293.425 | 3285.259 |
| GM_RM017 | `final_rot_area_px` | 216 | 0 | 9333.137 | 11067.919 | 12110.747 | 12963.676 | 17041.860 | 12125.230 | 1359.639 |
| GM_RM017 | `final_ax_area_px` | 216 | 0 | 9908.000 | 12331.700 | 13680.850 | 14876.000 | 23244.900 | 13765.332 | 1975.324 |
| GM_RM019 | `final_rot_area_px` | 25 | 0 | 9281.233 | 10096.746 | 10618.560 | 11207.329 | 13569.698 | 10860.382 | 1146.508 |
| GM_RM019 | `final_ax_area_px` | 25 | 0 | 9848.500 | 11696.400 | 12957.700 | 14674.600 | 19428.900 | 13480.652 | 2495.497 |

Descriptive interpretation:

- No missing footprint-area values were found.
- Rotated-area medians are similar for GM_RM011 and GM_RM017, while GM_RM019 is slightly lower and has only 25 rows.
- Axis-aligned area is wider, especially in GM_RM011, which is expected when heading and OBB orientation cause the enclosing axis-aligned box to expand.

# Visibility / Truncation Context

A019 `visibility_status`:

| value | count |
|---|---:|
| blank | 332 |
| `truncated_visible` | 109 |
| `uncertain` | 1 |

A021 condition distribution:

| field/value | count |
|---|---:|
| `condition_type=none` | 125 |
| `condition_type=truncated` | 248 |
| `condition_type=occluded` | 28 |
| `condition_type=truncated+occluded` | 41 |
| `condition_degree=none` | 125 |
| `condition_degree=mild` | 55 |
| `condition_degree=moderate` | 84 |
| `condition_degree=severe` | 178 |
| `truncation_degree=none` | 153 |
| `truncation_degree=mild` | 29 |
| `truncation_degree=moderate` | 83 |
| `truncation_degree=severe` | 177 |
| `occlusion_degree=none` | 373 |
| `occlusion_degree=mild` | 44 |
| `occlusion_degree=moderate` | 14 |
| `occlusion_degree=severe` | 11 |
| `condition_status=reviewed` | 442 |

Condition distribution by scene:

| scene | condition summary |
|---|---|
| GM_RM011 | 194 `truncated`, 7 `truncated+occluded`; truncation: 4 mild, 65 moderate, 132 severe; occlusion: 194 none, 1 mild, 2 moderate, 4 severe. |
| GM_RM017 | 125 `none`, 28 `occluded`, 30 `truncated`, 33 `truncated+occluded`; truncation: 153 none, 23 mild, 10 moderate, 30 severe; occlusion: 155 none, 43 mild, 12 moderate, 6 severe. |
| GM_RM019 | 24 `truncated`, 1 `truncated+occluded`; truncation: 2 mild, 8 moderate, 15 severe; occlusion: 24 none, 1 severe. |

Interpretation:

- Truncation is a major GT-domain condition: 289 / 442 rows have `condition_type` containing truncation, and 177 rows have `truncation_degree=severe`.
- Occlusion is less frequent but still present: 69 / 442 rows have `condition_type` containing occlusion, and 11 rows have `occlusion_degree=severe`.
- GM_RM011 and GM_RM019 are dominated by truncation labels, while GM_RM017 contains the only large `condition_type=none` subset.
- These labels are condition/failure-mode context only. They must not be used as inference inputs or Phase4 fixed-prior factor scores.

# Outlier Registry

No rows had missing `final_w`, missing `final_h`, missing `final_heading_deg`, nonpositive `final_w`, nonpositive `final_h`, missing `condition_type`, missing `truncation_degree`, or missing `occlusion_degree`.

The compact registry below lists observed extremes and high-severity condition examples for human review. These are descriptive review flags only, not exclusion rules, thresholds, or candidate-scoring criteria.

| review reason | target_identity | scene | sar_frame_num | sample_id | observed value |
|---|---|---|---:|---|---|
| lowest observed aspect_ratio | `saronly_gm_rm011_000276_01` | GM_RM011 | 276 | `saronly_gm_rm011_000276_01` | aspect_ratio 0.3793; `final_w=68.004`, `final_h=179.282` |
| highest observed aspect_ratio | `gm17supp_000179_000372_det3` | GM_RM017 | 372 | `gm17supp_000179_000372_det3` | aspect_ratio 2.7731; `final_w=194.666`, `final_h=70.198` |
| smallest observed `final_rot_area_px` | `GM_RM011\|000012.png\|000006.png\|2\|O2:car:0.76` | GM_RM011 | 12 | blank | 8065.3441 |
| largest observed `final_rot_area_px` | `frameadd_gm_rm011_000121_000252_01` | GM_RM011 | 252 | `frameadd_gm_rm011_000121_000252_01` | 17456.4340 |
| smallest observed `final_ax_area_px` | `GM_RM011\|000005.png\|000002.png\|1\|O1:car:0.96` | GM_RM011 | 5 | blank | 8744.4000 |
| largest observed `final_ax_area_px` | `GM_RM011\|000001.png\|000000.png\|2\|O2:car:0.87` | GM_RM011 | 1 | blank | 26360.5000 |
| severe truncation example | `GM_RM011\|000033.png\|000016.png\|1\|O1:car:0.88` | GM_RM011 | 33 | blank | `condition_type=truncated`, `truncation_degree=severe` |
| severe truncation example | `frameadd_gm_rm017_000152_000317_01` | GM_RM017 | 317 | `frameadd_gm_rm017_000152_000317_01` | `condition_type=truncated+occluded`, `truncation_degree=severe` |
| severe truncation example | `frameadd_gm_rm011_000161_000335_01` | GM_RM011 | 335 | `frameadd_gm_rm011_000161_000335_01` | `condition_type=truncated`, `truncation_degree=severe` |
| severe truncation example | `frameadd_gm_rm011_000243_000506_01` | GM_RM011 | 506 | `frameadd_gm_rm011_000243_000506_01` | `condition_type=truncated`, `truncation_degree=severe` |
| severe truncation example | `frameadd_gm_rm011_000245_000510_01` | GM_RM011 | 510 | `frameadd_gm_rm011_000245_000510_01` | `condition_type=truncated`, `truncation_degree=severe` |
| severe occlusion example | `frameadd_gm_rm017_000152_000317_01` | GM_RM017 | 317 | `frameadd_gm_rm017_000152_000317_01` | `condition_type=truncated+occluded`, `occlusion_degree=severe` |
| severe occlusion example | `saronly_gm_rm019_000000_000000_01` | GM_RM019 | 0 | `saronly_gm_rm019_000000_000000_01` | `condition_type=truncated+occluded`, `occlusion_degree=severe` |
| severe occlusion example | `saronly_gm_rm017_000145_000302_01` | GM_RM017 | 302 | `saronly_gm_rm017_000145_000302_01` | `condition_type=truncated+occluded`, `occlusion_degree=severe` |
| severe occlusion example | `frameadd_gm_rm011_000117_000244_02` | GM_RM011 | 244 | `frameadd_gm_rm011_000117_000244_02` | `condition_type=truncated+occluded`, `occlusion_degree=severe` |
| severe occlusion example | `gm_rm017_00016` | GM_RM017 | 310 | `gm_rm017_00016` | `condition_type=truncated+occluded`, `occlusion_degree=severe` |

Human-review focus:

- Confirm whether GM_RM011 low aspect-ratio cases reflect true vehicle orientation, box width/height convention, visible-extent annotation, or truncation/boundary behavior.
- Inspect the maximum axis-aligned area cases for rotation-induced expansion versus box-size inconsistency.
- Review severe truncation and severe occlusion examples before formalizing any complete-vehicle physical prior.

# Interpretation For Fixed Priors

This audit can inform the research discussion around `geometry_factor` and future physical-prior design in four ways.

First, it gives the human researcher a GT-domain scale summary. The observed complete GT box distributions show the approximate vehicle size and footprint ranges present in the manually reviewed SAR domain. These values may support discussion of physical plausibility, but they do not define tuned constants or thresholds.

Second, it exposes a scene-dependent aspect-ratio and orientation issue. GM_RM017 and GM_RM019 look close to a stable long-axis convention, while GM_RM011 appears mixed by the `final_w/final_h` ratio. Any future size/aspect/heading prior needs a declared OBB convention before it can become a fixed-prior component.

Third, it identifies condition-heavy scene structure. GM_RM011 and GM_RM019 are mostly truncated; GM_RM017 contains the main non-truncated subset. This is important for failure-mode planning, partial-visibility route design, and future missing-extent questions, but it does not activate visibility, missing extent, SAR structure, or uncertainty scoring in Phase4.

Fourth, it supports future route planning. Severe truncation, severe occlusion, wide axis-aligned footprints, and heading wraparound are candidate topics for future visibility, missing-extent, boundary, and near-field audits. They should remain separated from the current complete-vehicle fixed-prior candidate pilot.

These descriptive statistics do not prove that a fixed prior will improve candidate selection. They only describe the SAR GT domain that any scientifically defensible prior must respect.

# Non-Claims And Boundaries

- No inference was run.
- No candidate selection was performed.
- No model performance metrics were computed.
- No IoU, center error, recall, oracle rank, or candidate-selection quality metric was computed.
- No thresholds were tuned.
- No learned weights were fitted.
- No calibration or OOF calibration was performed.
- No GT field was used as inference evidence.
- No data file was modified.
- No candidate bank was generated, expanded, or modified.
- Line A does not authorize Line B experiments.
- A001/A005 were not used in this audit.
- A021 condition labels remain grouping/future-route evidence only.
- `visibility_factor`, `missing_extent_factor`, near-field routes, `sar_structure_factor`, and `uncertainty_factor` are not activated by this audit.
- The observed GT distributions may support human review of physical-prior plausibility, but they do not define scoring thresholds, tuned constants, or learned model parameters.

# Human Review Checklist

- Decide whether all 442 GT rows should remain in the SAR-domain physical-prior audit scope.
- Decide whether GM_RM019 should be retained with a low-sample-count warning because it has only 25 rows.
- Review the GM_RM011 aspect-ratio split before interpreting width/height distributions as physical vehicle shape.
- Resolve the heading convention, including negative values and 359-degree wraparound.
- Decide which severe truncation and severe occlusion rows need manual visual review.
- Decide how outside-mask, boundary, or visible-extent cases should be represented if additional metadata appears.
- Decide whether size, aspect ratio, or heading should be formalized first for human-declared fixed-prior design.
- Decide whether condition analysis should remain future-only or receive a deeper descriptive audit before any partial-visibility route.
- Confirm that A019/A021 remain eval-only and are not included in inference manifests, candidate scoring, or candidate-bank generation.
