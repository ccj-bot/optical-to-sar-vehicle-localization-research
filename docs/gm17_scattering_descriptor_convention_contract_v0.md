# GM17 Scattering Descriptor Convention Contract v0

Date: 2026-06-30

Status: A0.2 convention contract draft

This document defines a convention contract for future SAR descriptor work. It is not descriptor extraction, not Experiment C, not Experiment A, not a performance report, and not Phase5 approval.

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.

## 1. Purpose

The A0.1 physical convention audit left SAR descriptor extraction on HOLD because range/azimuth axis convention, crop convention, candidate-local coordinates, and normalization policy were not fully locked.

This contract introduces two descriptor modes:

```text
C0: display-XY candidate-local safe mode
C1: physical range/azimuth mode
```

The contract only defines terminology, allowed evidence, forbidden interpretations, and future schema requirements. It does not:

- open SAR image pixels;
- compute image statistics;
- compute SAR descriptors;
- compute scatter centroid;
- compute keyframe confidence;
- compute IoU or center error;
- use A019/A021/GT/oracle/final-box fields;
- modify candidate bank;
- modify the GM17 selector.

## 2. Two Descriptor Modes

### C0: Display-XY Candidate-Local Safe Mode

C0 is the safe starting convention for future descriptor-readiness design.

It uses only display image coordinates and candidate-local patch coordinates. It does not claim physical range/azimuth semantics.

Allowed coordinate language:

- `image-left`
- `image-center`
- `image-right`
- `image-up`
- `image-down`
- `candidate-local x`
- `candidate-local y`
- `inside support`
- `boundary ring`
- `outer background ring`
- `local contrast`

Forbidden coordinate language in C0:

- physical left/right;
- range-left or azimuth-right;
- heading;
- orientation;
- long-axis correctness;
- vehicle front/back;
- real velocity;
- physical range residual;
- physical azimuth residual.

C0 can support future diagnostic-readiness questions such as:

- whether candidate-local support contrast can be defined without label leakage;
- whether image-coordinate scatter-centroid offset can be represented as a display-XY feature;
- whether inside-vs-ring contrast schema is feasible;
- whether candidate mode clusters can be explained by image-coordinate support patterns;
- whether anti-keyframe ambiguity flags can be emitted from missingness and low local contrast.

C0 cannot support:

- physical range/azimuth residual claims;
- heading, orientation, or long-axis claims;
- rotated-IoU claims;
- vehicle front/back interpretation;
- physical motion or velocity claims.

C0 output names, if later approved, must keep display-coordinate semantics explicit:

```text
display_dx
display_dy
image_left_energy
image_center_energy
image_right_energy
image_up_energy
image_down_energy
candidate_local_contrast
candidate_local_missingness_flag
```

C0 must not emit names that imply physical range/azimuth unless C1 is approved.

### C1: Physical Range/Azimuth Mode

C1 is not approved by this contract.

C1 may only be considered after a separate audit locks all of the following:

- image `x/y` to range/azimuth mapping;
- sign convention;
- crop origin;
- candidate-local coordinate transform;
- image source policy;
- normalization policy;
- missingness flags;
- physical support mask or valid-support convention if needed.

Only C1 may discuss:

- `delta_range`;
- `delta_azimuth`;
- range-like descriptor asymmetry;
- azimuth-like descriptor asymmetry;
- aspect-aware physical descriptor sequence;
- physical range/azimuth consistency.

Even under C1, heading/orientation/long-axis correctness still requires a separate rotated-OBB / orientation convention audit. C1 does not turn `axis_aligned_proxy_iou` into rotated IoU.

Current C1 status:

```text
HOLD_FOR_AXIS_CONVENTION_AUDIT
HOLD_FOR_CROP_CONVENTION_AUDIT
HOLD_FOR_NORMALIZATION_POLICY
```

## 3. Image Source Policy

Current source policy:

| Source | Status | Allowed Use | Forbidden Use |
|---|---|---|---|
| Gray display PNG | Primary clue for future C0 readiness | Future display-XY descriptor-readiness design after explicit approval | Raw SAR physics claims; descriptor extraction in this A0.2 step |
| Pseudocolor display PNG | Fallback path clue only | Path availability / provenance if gray source is unavailable | Descriptor source unless separately approved |
| Raw SAR | Not confirmed | None in current contract | Any claim about radiometric SAR intensity |

Required future fields:

```text
image_source_id
image_source_path_policy
image_source_fallback_policy
image_width
image_height
source_type
display_image_limitations
```

Image source rules:

- Do not open pixels until a later explicit descriptor-readiness or extraction approval.
- Do not infer raw SAR intensity semantics from display PNGs.
- Do not use A019/A021/GT/oracle/final boxes to choose image source.
- Do not use condition labels to select gray vs pseudocolor source.

## 4. Crop Policy

Future C0 minimum crop policy, not implemented here:

- use frozen candidate `cx`, `cy`, `w`, `h` only;
- do not use final boxes;
- do not use GT;
- do not use A021 condition/truncation/occlusion labels;
- center crop on the frozen candidate center or a candidate-scaled support window;
- record crop origin as full-image coordinates;
- record crop width and height;
- clip to image bounds;
- emit boundary and missingness flags;
- map any crop-local coordinates back to full-image display XY when needed;
- preserve candidate identity without moving, resizing, adding, or deleting candidates.

Minimum future crop schema:

| Field | Meaning |
|---|---|
| `candidate_id` | Frozen candidate id. |
| `target_identity` | Target id. |
| `scene` | Scene id. |
| `sar_frame_num` | Frame id. |
| `gm17_track_id` | Track id if available. |
| `crop_policy_id` | Frozen crop convention id. |
| `crop_x0` | Full-image x origin. |
| `crop_y0` | Full-image y origin. |
| `crop_w` | Crop width in pixels. |
| `crop_h` | Crop height in pixels. |
| `candidate_local_x0` | Candidate box origin in crop-local coordinates. |
| `candidate_local_y0` | Candidate box origin in crop-local coordinates. |
| `clip_left` | Whether crop clipped left image boundary. |
| `clip_right` | Whether crop clipped right image boundary. |
| `clip_top` | Whether crop clipped top image boundary. |
| `clip_bottom` | Whether crop clipped bottom image boundary. |
| `missingness_flags` | Label-free crop/candidate availability flags. |

STOP if any crop policy uses:

- `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg`;
- A019 final boxes;
- A021 condition/truncation/occlusion labels;
- IoU;
- oracle fields;
- center error;
- manual review labels.

## 5. Multi-Scale Support Regions

Future C0 support regions should be defined only in candidate-local display coordinates.

Proposed support-region schema:

| Region | Definition Contract | Allowed Interpretation |
|---|---|---|
| `inner_core` | Central subregion inside frozen candidate support. | Candidate-local center support, not vehicle center proof. |
| `candidate_support` | Full frozen candidate box projected into crop-local display XY. | Frozen candidate support area, not the vehicle body. |
| `boundary_ring` | Ring around candidate support inside the crop. | Local boundary contrast and spillover readiness. |
| `outer_background_ring` | Wider local ring outside candidate support. | Local background reference. |

Future region fields:

```text
region_id
region_policy_id
region_x0
region_y0
region_x1
region_y1
region_clipped
region_missingness_flag
```

Rules:

- Define regions from frozen candidate geometry only.
- Keep all region coordinates in display image or candidate-local coordinates.
- Do not use final boxes to define support.
- Do not tune ring sizes from IoU, center error, condition labels, or oracle labels.
- Do not interpret image-left/image-right rings as physical left/right.

## 6. Normalization Policy

Future C0 normalization should be local and label-free.

Allowed policy families, if later approved:

- local background ring median/MAD;
- local percentile normalization;
- robust clipping declared before evaluation;
- missingness flags for low MAD, clipped ring, saturated source, empty support, or invalid crop.

Forbidden policy sources:

- IoU;
- center error;
- oracle candidate identity;
- A019 final boxes;
- A021 condition/truncation/occlusion labels;
- manual review outcomes;
- post-hoc failure buckets;
- same-run performance results.

Minimum future normalization schema:

| Field | Meaning |
|---|---|
| `normalization_policy_id` | Frozen normalization version. |
| `background_region_id` | Region used for local background. |
| `statistic_family` | `median_mad`, `percentile`, or another predeclared family. |
| `mad_floor` | Predeclared floor if using MAD. |
| `percentile_bounds` | Predeclared bounds if using percentiles. |
| `low_variance_flag` | Label-free missingness flag. |
| `clipped_background_flag` | Boundary/missingness flag. |
| `saturated_source_flag` | Source-quality flag. |
| `normalization_status` | `OK`, `HOLD`, or missingness code. |

No normalization threshold may be chosen from post-inference audit results.

## 7. What This Contract Unlocks

This contract unlocks:

- C0 descriptor-readiness script design;
- schema planning for candidate-local display-XY support regions;
- schema planning for crop origin, clipping, and missingness flags;
- safe vocabulary for image-coordinate support analysis.

This contract does not unlock:

- actual descriptor extraction;
- SAR pixel reading;
- Experiment C;
- C1 physical range/azimuth descriptor mode;
- heading/orientation/long-axis claims;
- active selector factors;
- candidate-bank modification.

Relationship to Experiment A:

Experiment A is high-IoU precision decomposition. It can proceed independently if join/key/schema validation passes, because Experiment A does not require SAR descriptor extraction.

Relationship to Experiment C:

Experiment C remains future-only. It requires explicit approval after C0 readiness is accepted or C1 convention is locked, depending on the descriptor question.

## 8. STOP / HOLD / GO

### GO

GO for:

- C0 contract drafting;
- future C0 descriptor-readiness script design;
- field/schema planning for display-XY candidate-local support regions;
- explicit C0/C1 terminology separation.

### HOLD

HOLD for:

- C0 actual descriptor extraction until explicitly approved;
- SAR image pixel reading;
- scatter-centroid computation;
- C1 physical range/azimuth mode;
- physical aspect-sequence descriptors;
- Experiment C;
- any descriptor output entering selection.

### STOP

STOP if a future step attempts:

- using final boxes for crop;
- using A019/A021/GT/oracle/IoU/center-error/final-box fields for descriptor definition;
- using condition labels for missingness policy;
- interpreting image-left as physical left;
- interpreting display-XY offsets as range/azimuth residuals;
- deriving heading/orientation/long-axis quality from `axis_aligned_proxy_iou`;
- treating `axis_aligned_proxy_iou` as rotated IoU;
- using descriptor outputs as active selector factors;
- modifying candidate bank;
- modifying the GM17 selector;
- training, OOF calibration, or formal Phase5 approval without explicit governance.

Current decision:

```text
C0 contract: drafted.
C0 descriptor extraction: HOLD.
C1 physical range/azimuth mode: HOLD.
Experiment C: HOLD.
Formal Phase5: BLOCKED_FOR_OOF_CALIBRATION.
```

