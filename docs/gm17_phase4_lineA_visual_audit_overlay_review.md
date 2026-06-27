# GM17 Phase4 Line A Visual Audit Overlay Review

This is Line A only: a derived review-only visualization packet for the SAR-domain physical-prior visual audit over VA001-VA016.

These overlay images are review-only visualization artifacts. They are not inference outputs, candidate-selection outputs, scoring outputs, training data, calibration artifacts, candidate-bank artifacts, or model-performance artifacts.

A001 and A005 were not used. Candidate banks, GM17 selected candidate outputs, IoU, center error, oracle rank, candidate rank, and model-performance fields were not used.

This page does not authorize scoring thresholds, tuned constants, learned weights, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, or model-performance claims.

## Drawing Convention

The overlays draw the recorded final GT rotated OBB from A019 using `final_cx`, `final_cy`, `final_w`, `final_h`, and `final_heading_deg`. For rendering only, image coordinates are treated as `x` increasing rightward and `y` increasing downward, and the recorded `final_heading_deg` is used directly as the OBB width-axis angle in degrees toward positive `y`. Negative and wraparound headings are used as trigonometrically equivalent angles for drawing; they are not corrected, normalized as data, or reinterpreted as a new convention.

The green arrow follows the longer of the rendered width or height axes to make visual inspection easier. It is not a claim about which stored field should be the vehicle long axis.

## Artifact Summary

| artifact | value |
|---|---|
| overlay directory | `docs/assets/gm17_phase4_lineA_visual_audit_overlays/` |
| overlay count | 16 |
| source worksheet | `docs/gm17_phase4_lineA_visual_audit_worksheet.md` |
| A019/A021 metadata resolution | 16 / 16 resolved in the worksheet and rechecked for drawing |
| failed SAR image loads | 0 |

## VA001 - GM_RM011 low-aspect-ratio cases

![VA001 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA001_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000276.png`
- optical_reference_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000132.png`
- optical_reference_preview: ![Optical reference VA001](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000132.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | saronly_gm_rm011_000276_01 |
| `scene` | GM_RM011 |
| `sar_frame_num` | 276 |
| `final_cx` | 1295.159 |
| `final_cy` | 1178.729 |
| `final_w` | 68.004 |
| `final_h` | 179.282 |
| `aspect_ratio` | 0.3793 |
| `final_heading_deg` | 2.000 |
| `final_rot_area_px` | 12191.893 |
| `final_ax_area_px` | 13474.247 |
| `condition_type` | truncated |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | none |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA002 - High-aspect-ratio cases

![VA002 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA002_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000372.png`
- optical_reference_path: `D:\profile\research\data\GM_RM017\GM_RM017_frames\000179.png`
- optical_reference_preview: ![Optical reference VA002](<D:/profile/research/data/GM_RM017/GM_RM017_frames/000179.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | gm17supp_000179_000372_det3 |
| `scene` | GM_RM017 |
| `sar_frame_num` | 372 |
| `final_cx` | 1010.409 |
| `final_cy` | 876.567 |
| `final_w` | 194.666 |
| `final_h` | 70.198 |
| `aspect_ratio` | 2.7731 |
| `final_heading_deg` | -3.000 |
| `final_rot_area_px` | 13665.163867999998 |
| `final_ax_area_px` | 15903.3 |
| `condition_type` | occluded |
| `condition_degree` | mild |
| `truncation_degree` | none |
| `occlusion_degree` | mild |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA003 - Maximum axis-aligned footprint cases

![VA003 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA003_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000005.png`
- optical_reference_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000002.png`
- optical_reference_preview: ![Optical reference VA003](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000002.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | GM_RM011\|000005.png\|000002.png\|1\|O1:car:0.96 |
| `scene` | GM_RM011 |
| `sar_frame_num` | 5 |
| `final_cx` | 1151.642 |
| `final_cy` | 1246.802 |
| `final_w` | 131.942 |
| `final_h` | 63.440 |
| `aspect_ratio` | 2.0798 |
| `final_heading_deg` | 1.000 |
| `final_rot_area_px` | 8370.40048 |
| `final_ax_area_px` | 8744.4 |
| `condition_type` | truncated |
| `condition_degree` | moderate |
| `truncation_degree` | moderate |
| `occlusion_degree` | none |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA004 - Maximum axis-aligned footprint cases

![VA004 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA004_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000001.png`
- optical_reference_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000000.png`
- optical_reference_preview: ![Optical reference VA004](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000000.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | GM_RM011\|000001.png\|000000.png\|2\|O2:car:0.87 |
| `scene` | GM_RM011 |
| `sar_frame_num` | 1 |
| `final_cx` | 1282.522 |
| `final_cy` | 1152.115 |
| `final_w` | 80.740 |
| `final_h` | 149.827 |
| `aspect_ratio` | 0.5389 |
| `final_heading_deg` | -40.000 |
| `final_rot_area_px` | 12097.03198 |
| `final_ax_area_px` | 26360.5 |
| `condition_type` | truncated |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | none |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA005 - Possible boundary/mask/visible-extent cases

![VA005 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA005_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000012.png`
- optical_reference_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000006.png`
- optical_reference_preview: ![Optical reference VA005](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000006.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | GM_RM011\|000012.png\|000006.png\|2\|O2:car:0.76 |
| `scene` | GM_RM011 |
| `sar_frame_num` | 12 |
| `final_cx` | 1152.377 |
| `final_cy` | 1243.565 |
| `final_w` | 128.333 |
| `final_h` | 62.847 |
| `aspect_ratio` | 2.0420 |
| `final_heading_deg` | 351.000 |
| `final_rot_area_px` | 8065.344051 |
| `final_ax_area_px` | 11220.3 |
| `condition_type` | truncated |
| `condition_degree` | moderate |
| `truncation_degree` | moderate |
| `occlusion_degree` | none |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA006 - Possible boundary/mask/visible-extent cases

![VA006 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA006_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000252.png`
- optical_reference_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000121.png`
- optical_reference_preview: ![Optical reference VA006](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000121.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | frameadd_gm_rm011_000121_000252_01 |
| `scene` | GM_RM011 |
| `sar_frame_num` | 252 |
| `final_cx` | 1060.390 |
| `final_cy` | 1184.032 |
| `final_w` | 90.671 |
| `final_h` | 192.525 |
| `aspect_ratio` | 0.4710 |
| `final_heading_deg` | -2.000 |
| `final_rot_area_px` | 17456.434 |
| `final_ax_area_px` | 19035.969 |
| `condition_type` | truncated |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | none |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA007 - Severe truncation examples

![VA007 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA007_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000033.png`
- optical_reference_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000016.png`
- optical_reference_preview: ![Optical reference VA007](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000016.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | GM_RM011\|000033.png\|000016.png\|1\|O1:car:0.88 |
| `scene` | GM_RM011 |
| `sar_frame_num` | 33 |
| `final_cx` | 1175.642 |
| `final_cy` | 1246.802 |
| `final_w` | 127.942 |
| `final_h` | 63.440 |
| `aspect_ratio` | 2.0167 |
| `final_heading_deg` | -18.000 |
| `final_rot_area_px` | 8116.640479999999 |
| `final_ax_area_px` | 14110.2 |
| `condition_type` | truncated |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | none |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA008 - Severe truncation examples

![VA008 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA008_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000317.png`
- optical_reference_path: `D:\profile\research\data\GM_RM017\GM_RM017_frames\000152.png`
- optical_reference_preview: ![Optical reference VA008](<D:/profile/research/data/GM_RM017/GM_RM017_frames/000152.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | frameadd_gm_rm017_000152_000317_01 |
| `scene` | GM_RM017 |
| `sar_frame_num` | 317 |
| `final_cx` | 796.483 |
| `final_cy` | 941.214 |
| `final_w` | 163.847 |
| `final_h` | 68.644 |
| `aspect_ratio` | 2.3869 |
| `final_heading_deg` | -2.000 |
| `final_rot_area_px` | 11247.113468000001 |
| `final_ax_area_px` | 12347.8 |
| `condition_type` | truncated+occluded |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | severe |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA009 - Severe truncation examples

![VA009 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA009_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000335.png`
- optical_reference_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000161.png`
- optical_reference_preview: ![Optical reference VA009](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000161.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | frameadd_gm_rm011_000161_000335_01 |
| `scene` | GM_RM011 |
| `sar_frame_num` | 335 |
| `final_cx` | 1072.276 |
| `final_cy` | 1251.935 |
| `final_w` | 139.765 |
| `final_h` | 65.852 |
| `aspect_ratio` | 2.1224 |
| `final_heading_deg` | -2.000 |
| `final_rot_area_px` | 9203.80478 |
| `final_ax_area_px` | 10036.4 |
| `condition_type` | truncated |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | none |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA010 - Severe truncation examples

![VA010 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA010_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000506.png`
- optical_reference_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000243.png`
- optical_reference_preview: ![Optical reference VA010](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000243.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | frameadd_gm_rm011_000243_000506_01 |
| `scene` | GM_RM011 |
| `sar_frame_num` | 506 |
| `final_cx` | 1058.974 |
| `final_cy` | 1249.690 |
| `final_w` | 144.761 |
| `final_h` | 71.310 |
| `aspect_ratio` | 2.0300 |
| `final_heading_deg` | 1.000 |
| `final_rot_area_px` | 10322.90691 |
| `final_ax_area_px` | 10777.3 |
| `condition_type` | truncated |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | none |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA011 - Severe truncation examples

![VA011 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA011_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000510.png`
- optical_reference_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000245.png`
- optical_reference_preview: ![Optical reference VA011](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000245.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | frameadd_gm_rm011_000245_000510_01 |
| `scene` | GM_RM011 |
| `sar_frame_num` | 510 |
| `final_cx` | 1090.811 |
| `final_cy` | 1251.093 |
| `final_w` | 137.811 |
| `final_h` | 70.630 |
| `aspect_ratio` | 1.9512 |
| `final_heading_deg` | 178.000 |
| `final_rot_area_px` | 9733.59093 |
| `final_ax_area_px` | 10570.0 |
| `condition_type` | truncated |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | none |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA012 - Severe occlusion examples

![VA012 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA012_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000317.png`
- optical_reference_path: `D:\profile\research\data\GM_RM017\GM_RM017_frames\000152.png`
- optical_reference_preview: ![Optical reference VA012](<D:/profile/research/data/GM_RM017/GM_RM017_frames/000152.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | frameadd_gm_rm017_000152_000317_01 |
| `scene` | GM_RM017 |
| `sar_frame_num` | 317 |
| `final_cx` | 796.483 |
| `final_cy` | 941.214 |
| `final_w` | 163.847 |
| `final_h` | 68.644 |
| `aspect_ratio` | 2.3869 |
| `final_heading_deg` | -2.000 |
| `final_rot_area_px` | 11247.113468000001 |
| `final_ax_area_px` | 12347.8 |
| `condition_type` | truncated+occluded |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | severe |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA013 - Severe occlusion examples; GM_RM019 representative low-n cases

![VA013 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA013_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM019\GM_RM019_SARframes\000000.png`
- optical_reference_path: `D:\profile\research\data\GM_RM019\GM_RM019_frames\000000.png`
- optical_reference_preview: ![Optical reference VA013](<D:/profile/research/data/GM_RM019/GM_RM019_frames/000000.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | saronly_gm_rm019_000000_000000_01 |
| `scene` | GM_RM019 |
| `sar_frame_num` | 0 |
| `final_cx` | 965.935 |
| `final_cy` | 1197.992 |
| `final_w` | 133.387 |
| `final_h` | 76.758 |
| `aspect_ratio` | 1.7378 |
| `final_heading_deg` | 11.000 |
| `final_rot_area_px` | 10238.519346 |
| `final_ax_area_px` | 14674.6 |
| `condition_type` | truncated+occluded |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | severe |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA014 - Severe occlusion examples

![VA014 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA014_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png`
- optical_reference_path: `D:\profile\research\data\GM_RM017\GM_RM017_frames\000145.png`
- optical_reference_preview: ![Optical reference VA014](<D:/profile/research/data/GM_RM017/GM_RM017_frames/000145.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | saronly_gm_rm017_000145_000302_01 |
| `scene` | GM_RM017 |
| `sar_frame_num` | 302 |
| `final_cx` | 689.677 |
| `final_cy` | 947.700 |
| `final_w` | 162.135 |
| `final_h` | 73.335 |
| `aspect_ratio` | 2.2109 |
| `final_heading_deg` | -4.000 |
| `final_rot_area_px` | 11890.170224999998 |
| `final_ax_area_px` | 14093.7 |
| `condition_type` | truncated+occluded |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | severe |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA015 - Severe occlusion examples

![VA015 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA015_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM011\GM_RM011_SARframes\000244.png`
- optical_reference_path: `D:\profile\research\data\GM_RM011\GM_RM011_frames\000117.png`
- optical_reference_preview: ![Optical reference VA015](<D:/profile/research/data/GM_RM011/GM_RM011_frames/000117.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | frameadd_gm_rm011_000117_000244_02 |
| `scene` | GM_RM011 |
| `sar_frame_num` | 244 |
| `final_cx` | 1047.428 |
| `final_cy` | 1208.114 |
| `final_w` | 75.056 |
| `final_h` | 136.592 |
| `aspect_ratio` | 0.5495 |
| `final_heading_deg` | 359.000 |
| `final_rot_area_px` | 10252.049152000001 |
| `final_ax_area_px` | 10675.9 |
| `condition_type` | truncated+occluded |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | severe |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.

## VA016 - Severe occlusion examples

![VA016 overlay](assets/gm17_phase4_lineA_visual_audit_overlays/VA016_overlay.png)

- original_sar_path: `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000310.png`
- optical_reference_path: `D:\profile\research\data\GM_RM017\GM_RM017_frames\000149.png`
- optical_reference_preview: ![Optical reference VA016](<D:/profile/research/data/GM_RM017/GM_RM017_frames/000149.png>)

### Key Metadata

| field | value |
|---|---|
| `target_identity` | gm_rm017_00016 |
| `scene` | GM_RM017 |
| `sar_frame_num` | 310 |
| `final_cx` | 756.110 |
| `final_cy` | 941.093 |
| `final_w` | 151.235 |
| `final_h` | 69.393 |
| `aspect_ratio` | 2.1794 |
| `final_heading_deg` | 176.000 |
| `final_rot_area_px` | 10494.650355000002 |
| `final_ax_area_px` | 12421.3 |
| `condition_type` | truncated+occluded |
| `condition_degree` | severe |
| `truncation_degree` | severe |
| `occlusion_degree` | severe |

### Human-Review Checklist

1. Does the OBB cover the main SAR support?
2. Does the OBB look like complete-vehicle extent or visible/partial extent?
3. Does the long axis appear stored in `final_w` or `final_h`?
4. Does heading appear visually consistent, 90-degree swapped, 180-degree equivalent, wrapped, or uncertain?
5. Is this case useful as a convention note, failure-mode note, future-route note, post-inference evaluation note, or only uncertainty/caveat?

### Fill-In Block

```text
visual_finding:
obb_coverage_assessment:
complete_vs_visible_extent:
width_height_convention_note:
heading_convention_note:
failure_mode_implication:
allowed_downstream_use:
forbidden_downstream_use:
reviewer_note:
reviewer_decision_status: pending / reviewed / needs_revisit
```

Allowed downstream use is limited to convention notes, failure-mode registry updates, future-route recommendations, post-inference evaluation planning notes, or uncertainty/caveat notes. Forbidden downstream use includes scoring thresholds, tuned constants, learned weights, candidate-selection rules, missing policy, factor activation, candidate-bank edits, candidate generation, oracle selection, and model-performance claims.
