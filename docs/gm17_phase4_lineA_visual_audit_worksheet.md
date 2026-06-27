# GM17 Phase4 Line A Visual Audit Worksheet

This worksheet is Line A only: human visual review for the SAR-domain physical-prior audit over manual-GT-covered samples in GM_RM011, GM_RM017, and GM_RM019.

A001 and A005 are not used. Candidate banks, GM17 selected candidate outputs, IoU, center error, oracle rank, candidate rank, and model-performance fields are not used.

This worksheet is for human visual review only. It does not authorize inference, candidate selection, scoring, threshold tuning, training, calibration, candidate-bank generation, candidate-bank modification, or model-performance claims.

The worksheet is editable by the human reviewer. Fill in the human review fields under each VA section; do not rewrite the resolved metadata unless the source tables are separately corrected under human approval.

Source material used:

- `docs/gm17_phase4_lineA_visual_audit_plan.md`
- `docs/gm17_phase4_sar_domain_physical_prior_audit_summary.md`
- A019 `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv`
- A021 `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv`

Resolution summary:

- VA sections included: VA001-VA016.
- A019 metadata resolved: 16 / 16.
- A021 metadata resolved: 16 / 16.
- Ambiguous matches: 0.
- Unresolved matches: 0.
- SAR image links inserted: 16 / 16.
- Optical reference image links inserted: 16 / 16.

## Worksheet Safety Reminder

Allowed outputs:

- convention note;
- failure-mode registry update;
- future-route recommendation;
- post-inference evaluation planning note;
- uncertainty/caveat note.

Forbidden outputs:

- scoring threshold;
- tuned constant;
- learned weight;
- candidate-selection rule;
- missing policy;
- factor activation;
- candidate-bank edit;
- candidate generation;
- oracle selection;
- model performance claim.

## VA001 - GM_RM011 Low-Aspect-Ratio Case

### Basic Identity

- review_id: VA001
- audit_category: GM_RM011 low-aspect-ratio cases
- target_identity: `saronly_gm_rm011_000276_01`
- scene: GM_RM011
- sar_frame_num: 276
- sample_id: `saronly_gm_rm011_000276_01`
- seed_reason: Lowest observed aspect ratio: 0.3793; final_w=68.004, final_h=179.282.
- reviewer_prompt: Decide whether this is width/height convention, true orientation, truncation, boundary behavior, or visible-extent annotation.

### Resolved A019 Metadata

- final_cx: 1295.159
- final_cy: 1178.729
- final_w: 68.004
- final_h: 179.282
- aspect_ratio: 0.3793
- final_heading_deg: 2.000
- final_rot_area_px: 12191.893
- final_ax_area_px: 13474.247
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000276.png`
- optical_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000132.png`
- review_status: reviewed
- chosen_candidate_source: manual_sar_supplement
- manual_adjusted: 1

### Resolved A021 Condition Metadata

- condition_type: truncated
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: none
- condition_status: reviewed
- condition_note: gm11_sar250_300_supplement

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA001](<D:/profile/research/data/GM_RM011/GM_RM011_SARframes/000276.png>)

Optical reference only:

![Optical reference VA001](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000132.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA002 - High-Aspect-Ratio Case

### Basic Identity

- review_id: VA002
- audit_category: High-aspect-ratio cases
- target_identity: `gm17supp_000179_000372_det3`
- scene: GM_RM017
- sar_frame_num: 372
- sample_id: `gm17supp_000179_000372_det3`
- seed_reason: Highest observed aspect ratio: 2.7731; final_w=194.666, final_h=70.198.
- reviewer_prompt: Decide whether this is valid long-axis vehicle geometry or an over-extended annotation.

### Resolved A019 Metadata

- final_cx: 1010.409
- final_cy: 876.567
- final_w: 194.666
- final_h: 70.198
- aspect_ratio: 2.7731
- final_heading_deg: -3.000
- final_rot_area_px: 13665.163867999998
- final_ax_area_px: 15903.3
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000372.png`
- optical_path: `D:\profile\research\data\GM_RM017\GM_RM017_frames\000179.png`
- review_status: reviewed
- chosen_candidate_source: manual_adjust
- manual_adjusted: 1

### Resolved A021 Condition Metadata

- condition_type: occluded
- condition_degree: mild
- truncation_degree: none
- occlusion_degree: mild
- condition_status: reviewed
- condition_note: manual_condition_review_tool

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA002](<D:/profile/research/data/GM_RM017/GM_RM017_SARframes/000372.png>)

Optical reference only:

![Optical reference VA002](<D:/profile/research/data/GM_RM017/GM_RM017_frames/000179.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA003 - Compact Axis-Aligned Footprint Case

### Basic Identity

- review_id: VA003
- audit_category: Maximum axis-aligned footprint cases
- target_identity: `GM_RM011|000005.png|000002.png|1|O1:car:0.96`
- scene: GM_RM011
- sar_frame_num: 5
- sample_id: blank
- seed_reason: Smallest observed final_ax_area_px: 8744.4000.
- reviewer_prompt: Check whether compact footprint is valid or reflects truncation/visible extent.

### Resolved A019 Metadata

- final_cx: 1151.642
- final_cy: 1246.802
- final_w: 131.942
- final_h: 63.440
- aspect_ratio: 2.0798
- final_heading_deg: 1.000
- final_rot_area_px: 8370.40048
- final_ax_area_px: 8744.4
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000005.png`
- optical_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000002.png`
- review_status: reviewed
- chosen_candidate_source: FULL_0514_new
- manual_adjusted: 0

### Resolved A021 Condition Metadata

- condition_type: truncated
- condition_degree: moderate
- truncation_degree: moderate
- occlusion_degree: none
- condition_status: reviewed
- condition_note: inherited_from_previous_sar:GM_RM011|000004.png|000002.png|1|O1:car:0.96

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA003](<D:/profile/research/data/GM_RM011/GM_RM011_SARframes/000005.png>)

Optical reference only:

![Optical reference VA003](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000002.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA004 - Large Axis-Aligned Footprint Case

### Basic Identity

- review_id: VA004
- audit_category: Maximum axis-aligned footprint cases
- target_identity: `GM_RM011|000001.png|000000.png|2|O2:car:0.87`
- scene: GM_RM011
- sar_frame_num: 1
- sample_id: blank
- seed_reason: Largest observed final_ax_area_px: 26360.5000.
- reviewer_prompt: Check whether large footprint is rotation-induced, boundary-related, or an annotation issue.

### Resolved A019 Metadata

- final_cx: 1282.522
- final_cy: 1152.115
- final_w: 80.740
- final_h: 149.827
- aspect_ratio: 0.5389
- final_heading_deg: -40.000
- final_rot_area_px: 12097.03198
- final_ax_area_px: 26360.5
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000001.png`
- optical_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000000.png`
- review_status: reviewed
- chosen_candidate_source: FULL_0514_new
- manual_adjusted: 0

### Resolved A021 Condition Metadata

- condition_type: truncated
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: none
- condition_status: reviewed
- condition_note: inherited_from_previous_sar:GM_RM011|000000.png|000000.png|2|O2:car:0.87

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA004](<D:/profile/research/data/GM_RM011/GM_RM011_SARframes/000001.png>)

Optical reference only:

![Optical reference VA004](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000000.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA005 - Small Rotated Footprint Case

### Basic Identity

- review_id: VA005
- audit_category: Possible boundary/mask/visible-extent cases
- target_identity: `GM_RM011|000012.png|000006.png|2|O2:car:0.76`
- scene: GM_RM011
- sar_frame_num: 12
- sample_id: blank
- seed_reason: Smallest observed final_rot_area_px: 8065.3441.
- reviewer_prompt: Check whether the rotated footprint represents a complete vehicle or visible support.

### Resolved A019 Metadata

- final_cx: 1152.377
- final_cy: 1243.565
- final_w: 128.333
- final_h: 62.847
- aspect_ratio: 2.0420
- final_heading_deg: 351.000
- final_rot_area_px: 8065.344051
- final_ax_area_px: 11220.3
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000012.png`
- optical_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000006.png`
- review_status: reviewed
- chosen_candidate_source: manual_adjust
- manual_adjusted: 1

### Resolved A021 Condition Metadata

- condition_type: truncated
- condition_degree: moderate
- truncation_degree: moderate
- occlusion_degree: none
- condition_status: reviewed
- condition_note: manual_condition_review_tool

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA005](<D:/profile/research/data/GM_RM011/GM_RM011_SARframes/000012.png>)

Optical reference only:

![Optical reference VA005](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000006.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA006 - Large Rotated Footprint Case

### Basic Identity

- review_id: VA006
- audit_category: Possible boundary/mask/visible-extent cases
- target_identity: `frameadd_gm_rm011_000121_000252_01`
- scene: GM_RM011
- sar_frame_num: 252
- sample_id: `frameadd_gm_rm011_000121_000252_01`
- seed_reason: Largest observed final_rot_area_px: 17456.4340.
- reviewer_prompt: Check whether the footprint is physically plausible or driven by annotation/boundary behavior.

### Resolved A019 Metadata

- final_cx: 1060.390
- final_cy: 1184.032
- final_w: 90.671
- final_h: 192.525
- aspect_ratio: 0.4710
- final_heading_deg: -2.000
- final_rot_area_px: 17456.434
- final_ax_area_px: 19035.969
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000252.png`
- optical_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000121.png`
- review_status: reviewed
- chosen_candidate_source: manual_sar_supplement
- manual_adjusted: 1

### Resolved A021 Condition Metadata

- condition_type: truncated
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: none
- condition_status: reviewed
- condition_note: gm11_sar250_300_supplement

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA006](<D:/profile/research/data/GM_RM011/GM_RM011_SARframes/000252.png>)

Optical reference only:

![Optical reference VA006](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000121.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA007 - Severe Truncation Case

### Basic Identity

- review_id: VA007
- audit_category: Severe truncation examples
- target_identity: `GM_RM011|000033.png|000016.png|1|O1:car:0.88`
- scene: GM_RM011
- sar_frame_num: 33
- sample_id: blank
- seed_reason: condition_type=truncated, truncation_degree=severe.
- reviewer_prompt: Determine whether the final box is complete-vehicle extent or visible/partial extent.

### Resolved A019 Metadata

- final_cx: 1175.642
- final_cy: 1246.802
- final_w: 127.942
- final_h: 63.440
- aspect_ratio: 2.0167
- final_heading_deg: -18.000
- final_rot_area_px: 8116.640479999999
- final_ax_area_px: 14110.2
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000033.png`
- optical_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000016.png`
- review_status: reviewed
- chosen_candidate_source: FULL_0514_new
- manual_adjusted: 0

### Resolved A021 Condition Metadata

- condition_type: truncated
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: none
- condition_status: reviewed
- condition_note: manual_condition_review_tool

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA007](<D:/profile/research/data/GM_RM011/GM_RM011_SARframes/000033.png>)

Optical reference only:

![Optical reference VA007](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000016.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA008 - Severe Truncation And Occlusion Case

### Basic Identity

- review_id: VA008
- audit_category: Severe truncation examples
- target_identity: `frameadd_gm_rm017_000152_000317_01`
- scene: GM_RM017
- sar_frame_num: 317
- sample_id: `frameadd_gm_rm017_000152_000317_01`
- seed_reason: condition_type=truncated+occluded, truncation_degree=severe.
- reviewer_prompt: Review combined truncation and occlusion effects on extent and center reliability.

### Resolved A019 Metadata

- final_cx: 796.483
- final_cy: 941.214
- final_w: 163.847
- final_h: 68.644
- aspect_ratio: 2.3869
- final_heading_deg: -2.000
- final_rot_area_px: 11247.113468000001
- final_ax_area_px: 12347.8
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000317.png`
- optical_path: `D:\profile\research\data\GM_RM017\GM_RM017_frames\000152.png`
- review_status: reviewed
- chosen_candidate_source: W22_0422
- manual_adjusted: 0

### Resolved A021 Condition Metadata

- condition_type: truncated+occluded
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: severe
- condition_status: reviewed
- condition_note: manual_condition_review_tool

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA008](<D:/profile/research/data/GM_RM017/GM_RM017_SARframes/000317.png>)

Optical reference only:

![Optical reference VA008](<D:/profile/research/data/GM_RM017/GM_RM017_frames/000152.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA009 - Severe Truncation Case

### Basic Identity

- review_id: VA009
- audit_category: Severe truncation examples
- target_identity: `frameadd_gm_rm011_000161_000335_01`
- scene: GM_RM011
- sar_frame_num: 335
- sample_id: `frameadd_gm_rm011_000161_000335_01`
- seed_reason: condition_type=truncated, truncation_degree=severe.
- reviewer_prompt: Determine whether missing extent should remain future-route context only.

### Resolved A019 Metadata

- final_cx: 1072.276
- final_cy: 1251.935
- final_w: 139.765
- final_h: 65.852
- aspect_ratio: 2.1224
- final_heading_deg: -2.000
- final_rot_area_px: 9203.80478
- final_ax_area_px: 10036.4
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000335.png`
- optical_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000161.png`
- review_status: reviewed
- chosen_candidate_source: W22_0422
- manual_adjusted: 0

### Resolved A021 Condition Metadata

- condition_type: truncated
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: none
- condition_status: reviewed
- condition_note: manual_condition_review_tool

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA009](<D:/profile/research/data/GM_RM011/GM_RM011_SARframes/000335.png>)

Optical reference only:

![Optical reference VA009](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000161.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA010 - Severe Truncation Case

### Basic Identity

- review_id: VA010
- audit_category: Severe truncation examples
- target_identity: `frameadd_gm_rm011_000243_000506_01`
- scene: GM_RM011
- sar_frame_num: 506
- sample_id: `frameadd_gm_rm011_000243_000506_01`
- seed_reason: condition_type=truncated, truncation_degree=severe.
- reviewer_prompt: Review if the visual evidence supports complete-vehicle annotation or visible extent.

### Resolved A019 Metadata

- final_cx: 1058.974
- final_cy: 1249.690
- final_w: 144.761
- final_h: 71.310
- aspect_ratio: 2.0300
- final_heading_deg: 1.000
- final_rot_area_px: 10322.90691
- final_ax_area_px: 10777.3
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000506.png`
- optical_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000243.png`
- review_status: reviewed
- chosen_candidate_source: W22_0422
- manual_adjusted: 0

### Resolved A021 Condition Metadata

- condition_type: truncated
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: none
- condition_status: reviewed
- condition_note: manual_condition_review_tool

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA010](<D:/profile/research/data/GM_RM011/GM_RM011_SARframes/000506.png>)

Optical reference only:

![Optical reference VA010](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000243.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA011 - Severe Truncation Case

### Basic Identity

- review_id: VA011
- audit_category: Severe truncation examples
- target_identity: `frameadd_gm_rm011_000245_000510_01`
- scene: GM_RM011
- sar_frame_num: 510
- sample_id: `frameadd_gm_rm011_000245_000510_01`
- seed_reason: condition_type=truncated, truncation_degree=severe.
- reviewer_prompt: Check for boundary/mask behavior and record only a caveat if unresolved.

### Resolved A019 Metadata

- final_cx: 1090.811
- final_cy: 1251.093
- final_w: 137.811
- final_h: 70.630
- aspect_ratio: 1.9512
- final_heading_deg: 178.000
- final_rot_area_px: 9733.59093
- final_ax_area_px: 10570.0
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000510.png`
- optical_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000245.png`
- review_status: reviewed
- chosen_candidate_source: W22_0422
- manual_adjusted: 0

### Resolved A021 Condition Metadata

- condition_type: truncated
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: none
- condition_status: reviewed
- condition_note: manual_condition_review_tool

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA011](<D:/profile/research/data/GM_RM011/GM_RM011_SARframes/000510.png>)

Optical reference only:

![Optical reference VA011](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000245.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA012 - Severe Occlusion Case

### Basic Identity

- review_id: VA012
- audit_category: Severe occlusion examples
- target_identity: `frameadd_gm_rm017_000152_000317_01`
- scene: GM_RM017
- sar_frame_num: 317
- sample_id: `frameadd_gm_rm017_000152_000317_01`
- seed_reason: condition_type=truncated+occluded, occlusion_degree=severe.
- reviewer_prompt: Review whether occlusion changes box reliability beyond the truncation finding.

### Resolved A019 Metadata

- final_cx: 796.483
- final_cy: 941.214
- final_w: 163.847
- final_h: 68.644
- aspect_ratio: 2.3869
- final_heading_deg: -2.000
- final_rot_area_px: 11247.113468000001
- final_ax_area_px: 12347.8
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000317.png`
- optical_path: `D:\profile\research\data\GM_RM017\GM_RM017_frames\000152.png`
- review_status: reviewed
- chosen_candidate_source: W22_0422
- manual_adjusted: 0

### Resolved A021 Condition Metadata

- condition_type: truncated+occluded
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: severe
- condition_status: reviewed
- condition_note: manual_condition_review_tool

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA012](<D:/profile/research/data/GM_RM017/GM_RM017_SARframes/000317.png>)

Optical reference only:

![Optical reference VA012](<D:/profile/research/data/GM_RM017/GM_RM017_frames/000152.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA013 - Severe Occlusion And GM_RM019 Low-N Case

### Basic Identity

- review_id: VA013
- audit_category: Severe occlusion examples; GM_RM019 representative low-n cases
- target_identity: `saronly_gm_rm019_000000_000000_01`
- scene: GM_RM019
- sar_frame_num: 0
- sample_id: `saronly_gm_rm019_000000_000000_01`
- seed_reason: condition_type=truncated+occluded, occlusion_degree=severe; GM_RM019 low-n example.
- reviewer_prompt: Treat as a low-sample representative check, not a scene-level validation claim.

### Resolved A019 Metadata

- final_cx: 965.935
- final_cy: 1197.992
- final_w: 133.387
- final_h: 76.758
- aspect_ratio: 1.7378
- final_heading_deg: 11.000
- final_rot_area_px: 10238.519346
- final_ax_area_px: 14674.6
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM019\GM_RM019_SARframes\000000.png`
- optical_path: `D:\profile\research\data\GM_RM019\GM_RM019_frames\000000.png`
- review_status: reviewed
- chosen_candidate_source: manual_adjust
- manual_adjusted: 1

### Resolved A021 Condition Metadata

- condition_type: truncated+occluded
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: severe
- condition_status: reviewed
- condition_note: manual_condition_review_tool

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA013](<D:/profile/research/data/GM_RM019/GM_RM019_SARframes/000000.png>)

Optical reference only:

![Optical reference VA013](<D:/profile/research/data/GM_RM019/GM_RM019_frames/000000.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA014 - Severe Occlusion Case

### Basic Identity

- review_id: VA014
- audit_category: Severe occlusion examples
- target_identity: `saronly_gm_rm017_000145_000302_01`
- scene: GM_RM017
- sar_frame_num: 302
- sample_id: `saronly_gm_rm017_000145_000302_01`
- seed_reason: condition_type=truncated+occluded, occlusion_degree=severe.
- reviewer_prompt: Check whether occlusion affects final center and extent interpretation.

### Resolved A019 Metadata

- final_cx: 689.677
- final_cy: 947.700
- final_w: 162.135
- final_h: 73.335
- aspect_ratio: 2.2109
- final_heading_deg: -4.000
- final_rot_area_px: 11890.170224999998
- final_ax_area_px: 14093.7
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png`
- optical_path: `D:\profile\research\data\GM_RM017\GM_RM017_frames\000145.png`
- review_status: reviewed
- chosen_candidate_source: W22_0422
- manual_adjusted: 0

### Resolved A021 Condition Metadata

- condition_type: truncated+occluded
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: severe
- condition_status: reviewed
- condition_note: manual_condition_review_tool

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA014](<D:/profile/research/data/GM_RM017/GM_RM017_SARframes/000302.png>)

Optical reference only:

![Optical reference VA014](<D:/profile/research/data/GM_RM017/GM_RM017_frames/000145.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA015 - Severe Occlusion And Heading-Wraparound Case

### Basic Identity

- review_id: VA015
- audit_category: Severe occlusion examples
- target_identity: `frameadd_gm_rm011_000117_000244_02`
- scene: GM_RM011
- sar_frame_num: 244
- sample_id: `frameadd_gm_rm011_000117_000244_02`
- seed_reason: condition_type=truncated+occluded, occlusion_degree=severe.
- reviewer_prompt: Record failure-mode context only; do not derive a scoring rule.

### Resolved A019 Metadata

- final_cx: 1047.428
- final_cy: 1208.114
- final_w: 75.056
- final_h: 136.592
- aspect_ratio: 0.5495
- final_heading_deg: 359.000
- final_rot_area_px: 10252.049152000001
- final_ax_area_px: 10675.9
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000244.png`
- optical_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000117.png`
- review_status: reviewed
- chosen_candidate_source: manual_adjust
- manual_adjusted: 1

### Resolved A021 Condition Metadata

- condition_type: truncated+occluded
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: severe
- condition_status: reviewed
- condition_note: manual_condition_review_tool

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA015](<D:/profile/research/data/GM_RM011/GM_RM011_SARframes/000244.png>)

Optical reference only:

![Optical reference VA015](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000117.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.

## VA016 - Severe Occlusion Case

### Basic Identity

- review_id: VA016
- audit_category: Severe occlusion examples
- target_identity: `gm_rm017_00016`
- scene: GM_RM017
- sar_frame_num: 310
- sample_id: `gm_rm017_00016`
- seed_reason: condition_type=truncated+occluded, occlusion_degree=severe.
- reviewer_prompt: Review whether the final annotation is complete-vehicle, partial, or uncertain.

### Resolved A019 Metadata

- final_cx: 756.110
- final_cy: 941.093
- final_w: 151.235
- final_h: 69.393
- aspect_ratio: 2.1794
- final_heading_deg: 176.000
- final_rot_area_px: 10494.650355000002
- final_ax_area_px: 12421.3
- sar_pseudocolor_path: `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000310.png`
- optical_path: `D:\profile\research\data\GM_RM017\GM_RM017_frames\000149.png`
- review_status: reviewed
- chosen_candidate_source: W22_0422
- manual_adjusted: 0

### Resolved A021 Condition Metadata

- condition_type: truncated+occluded
- condition_degree: severe
- truncation_degree: severe
- occlusion_degree: severe
- condition_status: reviewed
- condition_note: manual_condition_review_tool

### Image Preview

SAR pseudocolor:

![SAR pseudocolor VA016](<D:/profile/research/data/GM_RM017/GM_RM017_SARframes/000310.png>)

Optical reference only:

![Optical reference VA016](<D:/profile/research/data/GM_RM017/GM_RM017_frames/000149.png>)

### Human Fill-In Template

```text
visual_finding:
convention_implication:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

### Safety Reminder

Allowed outputs: convention note, failure-mode registry update, future-route recommendation, post-inference evaluation planning note, uncertainty/caveat note.

Forbidden outputs: scoring threshold, tuned constant, learned weight, candidate-selection rule, missing policy, factor activation, candidate-bank edit, candidate generation, oracle selection, model performance claim.
