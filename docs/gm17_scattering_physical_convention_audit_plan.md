# GM17 Scattering Physical Convention Audit Plan

Date: 2026-06-30

Status: A0.1 physical convention audit plan

This document audits repository evidence for SAR axis, crop, local-coordinate, and intensity-normalization conventions. It is not descriptor extraction, not Experiment C, not Experiment A, and not Phase5 approval.

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.

## 1. Purpose

The A0 resolver found SAR image/crop prerequisites but left physical convention checks on HOLD.

This plan converts that HOLD state into a concrete audit checklist before any SAR descriptor extraction can be approved.

It answers:

- what convention evidence exists in the repository;
- what is only a clue rather than a frozen contract;
- what remains missing before SAR descriptor work;
- what future convention contract must be locked.

This document does not:

- open SAR image pixels;
- compute descriptors;
- compute scatter centroids;
- compute image statistics;
- compute IoU or center error;
- run Experiment A/B/C;
- create or modify scripts;
- change candidate geometry;
- change the GM17 selector.

## 2. Evidence Sources Searched

Resolver outputs reviewed:

- `output/gm17_scattering_artifact_resolver_20260630_013623/resolver_summary.json`
- `output/gm17_scattering_artifact_resolver_20260630_013623/artifact_manifest.csv`
- `output/gm17_scattering_artifact_resolver_20260630_013623/physical_opportunity_checklist.csv`
- `output/gm17_scattering_artifact_resolver_20260630_013623/observed_field_alias_hits.csv`
- `output/gm17_scattering_artifact_resolver_20260630_013623/stop_hold_go_report.md`

Primary docs/configs reviewed:

- `configs/phase5B_first_diagnostic_run_config_v0.json`
- `docs/phase5B_shell_proxy_and_coordinate_decision_20260629.md`
- `docs/phase5B_first_diagnostic_run_spec_20260629.md`
- `docs/phase5B_precheck_sources_and_config_summary_20260629_095113.md`
- `docs/gm17_scattering_framework_execution_bridge.md`
- `docs/gm17_scattering_framework_artifact_resolver_spec.md`

Script/config/doc search scope:

- `docs/*.md`
- `scripts/*.py`
- `configs/*.json`

Search terms included:

```text
range
azimuth
cross
pred_r
pred_az
pred_cross
sar_frame
SARframes_gray
SARframes_pseudo
crop
patch
local coordinate
coordinate
x/y
fan
shell
wedge
candidate crop
background ring
normalization
intensity
grayscale
pseudocolor
GM_RM017_SARframes_gray
candidate_refined_factor_inference
signed_escape_posterior
```

Evidence status meanings:

| Status | Meaning |
|---|---|
| `CONFIRMED` | A repository source explicitly defines the item enough for the stated narrow use. |
| `CLUE_ONLY` | A source suggests a convention, but it is not enough to approve descriptor extraction. |
| `HOLD` | Evidence is incomplete or ambiguous; descriptor work must wait. |
| `NOT_FOUND` | No relevant evidence was found in the searched scope. |

## 3. Axis Convention Findings

| Question | Evidence Found | Status | Notes |
|---|---|---|---|
| Is image `x/y` convention declared? | `phase5B_first_diagnostic_run_config_v0.json` declares `coordinate_convention_id = full_image_xy_display_png_v1`; `phase5B_shell_proxy_and_coordinate_decision_20260629.md` says full-image pixel coordinates use `x` rightward and `y` downward for A/B/C documentation. | `CONFIRMED` for display image XY naming; `CLUE_ONLY` for future descriptor work | This is sufficient as a documentation clue for display PNG full-image coordinates, not as descriptor readiness. |
| Do image `x/y` axes correspond to range/azimuth? | The same docs explicitly hold fan/range convention and valid-support mapping for Route D. | `HOLD` | No evidence locks which image axis is range-like or azimuth-like for physical descriptors. |
| Do `r`, `az`, `cross`, `pred_r`, `pred_az`, and `pred_cross` fields exist? | A001/A005 headers and Phase5B docs/configs list these fields. | `CONFIRMED` for field existence | Field existence does not prove sign convention or physical mapping. |
| Is sign convention for range/azimuth/cross explicit? | No explicit sign contract was found in the searched docs/configs/scripts. | `NOT_FOUND` | This blocks range/azimuth residual interpretation and descriptor sign claims. |
| Do fan/shell/wedge docs define a local coordinate convention? | Docs discuss fan, shell, wedge, range, azimuth, and cross concepts; Phase5B docs say fan/range mapping remains not frozen. | `CLUE_ONLY` / `HOLD` | Existing language is design context, not a locked coordinate contract. |
| Is evidence sufficient to interpret `delta_range` / `delta_azimuth` physically? | A001-like fields such as `delta_r_from_pred`, `delta_cross_from_pred`, and `delta_az_from_pred` are named in docs/headers, but sign/origin semantics are not frozen. | `HOLD` | These fields may be used as schema clues only until axis convention is audited. |
| Can `axis_aligned_proxy_iou` support heading/orientation/long-axis conclusions? | Resolver alias map and reports mark it as AABB proxy only. | `CONFIRMED` as forbidden | It cannot support heading, orientation, or long-axis conclusions. |

Axis decision:

```text
Full-image display XY naming is partially documented.
Range/azimuth physical mapping remains HOLD.
```

## 4. Crop Convention Findings

| Question | Evidence Found | Status | Notes |
|---|---|---|---|
| Are candidate coordinates full-image coordinates? | Phase5B shell/proxy decision states A001 `cx/cy/w/h` and A005 `pred_cx/pred_cy/pred_w/pred_h` are full-image pixel coordinates. | `CONFIRMED` for candidate/prior tables | This does not define descriptor crop extraction. |
| Is crop origin recorded? | Phase5B config declares `store_crop_origin = true` and says crop-local computation must map back to full-image coordinates. | `CLUE_ONLY` | This is a Phase5B config clue, not an A0 descriptor extraction output contract. |
| How is candidate-local patch derived from `cx/cy/w/h`? | No current A0 descriptor crop contract was found. Phase5B config defines an A005-centered 512 px square crop, not a candidate-centered descriptor crop. | `HOLD` | Candidate-local crop derivation must be separately specified. |
| Is crop padding / boundary clipping specified? | Phase5B config declares `a005_centered_512px_square_clipped_to_image_bounds_v0`, `crop_size_px = 512`, and `clip_to_image_bounds = true`. | `CLUE_ONLY` | Useful clue for a future contract; insufficient for scattering descriptor extraction readiness. |
| Are final boxes used for crop? | No evidence found that current config uses A019 final boxes for crop; resolver forbids `final_*` as crop source. | `NOT_FOUND` for use; `CONFIRMED` as forbidden | Any future use of final boxes for crop is STOP. |
| Is there a candidate-side-only crop policy? | No locked candidate-side-only crop policy was found. | `HOLD` | Future descriptor work must define whether crops are candidate-centered, A005-centered, multi-scale, or support-region based. |
| Are multi-scale support regions defined? | A0 resolver marks prerequisites present but crop/local convention unverified; Phase5B config has route scales for proposal generation, not descriptor support-region contract. | `HOLD` | Multi-scale descriptor support remains blocked. |

Crop decision:

```text
Full-image candidate/prior coordinate fields are documented.
Descriptor crop origin, candidate-local frame, crop scale, and support-region policy remain HOLD.
```

## 5. Intensity / Background Normalization Findings

| Question | Evidence Found | Status | Notes |
|---|---|---|---|
| Gray or pseudocolor source? | Phase5B config prefers `D:/profile/research/data/GM_RM017/GM_RM017_SARframes_gray/<sar_frame>.png` and uses `sar_pseudocolor_path` as fallback. Resolver found external grayscale image directory with top-level `.png` inventory. | `CLUE_ONLY` | Source path existence does not prove descriptor readiness. |
| Is local background policy defined? | Phase5B config has `crop_robust_background` with median/MAD on selected grayscale crop, `minimum_mad = 1.0`, and `border_exclusion_px = 8`. | `CLUE_ONLY` | This is a proposal-route config clue, not an audited descriptor contract. |
| Is robust z-score or percentile normalization defined for descriptors? | Median/MAD and fixed percentile route clues exist in Phase5B config. No general descriptor normalization policy was found. | `HOLD` | Descriptor-specific normalization remains unset. |
| Are speckle/intensity normalization rules defined? | No explicit speckle model, calibration, raw SAR intensity source, or radiometric normalization contract found. | `NOT_FOUND` | Do not claim raw SAR physics from display PNGs. |
| Are missingness / edge flags defined? | Phase5B config has boundary-touching component policy and uncertainty flags for proposal routes. | `CLUE_ONLY` | Useful precedent, but not a descriptor missingness contract. |
| Are raw SAR arrays available and defined? | Phase5B shell/proxy decision says raw SAR was not confirmed. | `NOT_FOUND` | Display PNGs are the only current source clue. |

Normalization decision:

```text
Grayscale display PNG and crop-local median/MAD clues exist.
Descriptor intensity normalization remains HOLD.
```

## 6. Descriptor Readiness Decision

Current decision:

```text
HOLD for SAR descriptor extraction.
```

Reason:

- range/azimuth axis convention is not frozen;
- crop origin and local coordinate convention are not frozen for descriptor extraction;
- candidate-local crop policy is not defined;
- multi-scale support-region policy is not defined;
- intensity normalization policy is not a descriptor contract;
- raw SAR source and radiometric semantics are not confirmed;
- external SAR image directory existence is only a prerequisite clue.

What is allowed now:

- cite SAR image/crop source as prerequisite present;
- design a future convention contract;
- design header/schema-only checks;
- keep descriptor fields as future diagnostic outputs.

What is not allowed now:

- compute `E_left`, `E_center`, `E_right`, `lr_asymmetry`, `center_dominance`, `mirror_symmetry`, `scatter_centroid_dx`, `scatter_centroid_dy`, `scatter_compactness`, `peak_count`, or local contrast;
- derive scatter centroid;
- infer heading/orientation from descriptors or AABB proxy;
- use A019/A021/final boxes for crops;
- use condition labels for missingness, route choice, keyframe choice, or anchors.

## 7. Proposed Convention Contract

Before any future descriptor extraction, a separate convention contract must freeze at least the following fields.

| Contract Field | Required Decision |
|---|---|
| `image_source_id` | `gray_display_png`, `pseudocolor_display_png`, raw SAR, or another explicitly approved source. |
| `image_source_path_policy` | Exact path construction and fallback order. |
| `coordinate_frame` | Full-image coordinates, crop-local coordinates, or both with mandatory origin mapping. |
| `x_axis_meaning` | Display image x only, or physically range-like/azimuth-like after audit. |
| `y_axis_meaning` | Display image y only, or physically range-like/azimuth-like after audit. |
| `range_like_axis` | Must be explicitly mapped or marked unavailable. |
| `azimuth_like_axis` | Must be explicitly mapped or marked unavailable. |
| `sign_convention` | Positive direction for any range/azimuth/cross residual. |
| `crop_center_policy` | Candidate-centered, A005-centered, track-centered, or other inference-safe policy. |
| `crop_scale_policy` | Fixed pixel size, candidate-relative scale, A005-relative scale, or multi-scale policy. |
| `crop_padding_policy` | Padding, clipping, or invalid-region handling. |
| `boundary_clipping_policy` | Exact image-bound behavior and missingness flags. |
| `local_background_region` | Ring, border, annulus, crop residual, or no local background. |
| `normalization_policy` | Median/MAD, percentile, raw intensity, z-score, or explicitly none. |
| `missingness_flags` | Boundary touch, crop clipped, low contrast, support absent, saturated, invalid source. |
| `forbidden_sources` | A019/A021/GT/oracle/IoU/center-error/final-box fields. |

Minimum gate:

```text
Descriptor work cannot move from HOLD to GO until this contract exists and is approved.
```

