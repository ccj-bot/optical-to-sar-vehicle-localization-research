# Phase5B Shell Proxy And Coordinate Decision

Date: 2026-06-29

## 1. Purpose

This document is a documentation-only decision review for the Phase5B shell/proxy-shell, coordinate, valid-support, and SAR image-source blocker.

It does not execute proposal generation. It does not implement a shell builder, generate proposals, create candidates, run an experiment, tune thresholds, train a model, calibrate scores, modify C3/C4, or modify A001/A005/A019/A021.

The goal is narrower: decide which existing inference-side source can serve as the first diagnostic proxy shell, what coordinate and image-source assumptions are acceptable for the first diagnostic routes, and what remains blocked before any implementation approval.

## 2. Candidate Shell / Proxy Sources

### A. A001 Candidate Envelope

| field | decision |
|---|---|
| path if known | `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv` |
| available fields | `target_identity`, `scene`, `sar_frame`, `sar_frame_num`, `sar_pseudocolor_path`, `candidate_id`, `candidate_source`, `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross`, `delta_r_from_pred`, `delta_cross_from_pred`, `delta_az_from_pred`, `gm17_track_id` |
| inference-side available | Yes, as the fixed A001 candidate bank. Prior boundary reports found no forbidden eval columns in the inference table header. |
| derived from A019/A021/GT/oracle/panel review | Not indicated by header or boundary report for the inference table. |
| collapses back to A001 candidate selection | High risk. Using the candidate envelope as the shell can turn Phase5B back into A001-neighborhood sampling or A001 row reranking. |
| uncertainty semantics | Not a probabilistic shell. It is a discrete candidate menu with many externally supplied rows. An envelope would be a derived diagnostic proxy, not an optical-conditioned shell. |
| coordinate convention | Full-image pixel coordinates for `cx`, `cy`, `w`, `h`; fan-polar-like `r`, `az`, `cross` fields exist but their convention is not fully frozen for Phase5B. |
| risks | A001 bias, hidden candidate-bank reuse, candidate density affecting shell size, heading grid inherited from A001, row identity leakage into proposal interpretation. |
| recommendation | REJECT as the preferred first-round shell. ACCEPT_WITH_CAVEAT only as a post-hoc A001-neighborhood baseline or fallback comparison, not as the primary proposal shell. |

### B. Optical Temporal Prior Window

| field | decision |
|---|---|
| path if known | `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv` |
| available fields | `target_identity`, `scene`, `sar_frame`, `sar_frame_num`, `sar_pseudocolor_path`, `pred_status`, `pred_cx`, `pred_cy`, `pred_w`, `pred_h`, `pred_heading_deg`, `pred_r`, `pred_az`, `pred_cross`, `gm17_track_id`, track metadata, score-like fields |
| inference-side available | Yes. It is the A005 optical/temporal prior table for GM_RM017. |
| derived from A019/A021/GT/oracle/panel review | No forbidden final/GT/oracle fields are present in the inspected header. Evaluation counterpart is separate and must not be joined. |
| collapses back to A001 candidate selection | Lower risk if used only for shell center, extent prior, frame path, track id, and range/az/cross metadata. Risk rises if score fields or legacy selection decisions are used. |
| uncertainty semantics | Soft prior only. It gives a predicted center/extent and fan-polar state, not final localization. A shell must be created later by predeclared margin/crop/uncertainty policy. |
| coordinate convention | Full-image pixel `pred_cx`, `pred_cy`, `pred_w`, `pred_h`; `pred_r`, `pred_az`, `pred_cross` available but range/fan convention remains partially audited. |
| risks | Temporal prior may inherit legacy bias; a single predicted box can be mistaken for final SAR localization; score fields can reintroduce C3/C4-like ranking. |
| recommendation | ACCEPT_WITH_CAVEAT as the preferred first-round proxy-shell source. Use only identity, frame, path, `pred_cx`, `pred_cy`, `pred_w`, `pred_h`, `pred_r`, `pred_az`, `pred_cross`, and `gm17_track_id`. Exclude `score`, `lr_score`, `sar_factor_score`, `temporal_factor_score`, and decision fields from proposal generation. |

### C. Earlier ROI Corridor / Escape Band Output

| field | decision |
|---|---|
| path if known | `output/clean_no_gt_localizer_2026-05-31_gm17_ray_escape/gm17_ray_escape_predictions_inference.csv`; related candidate top-k table: `gm17_ray_escape_candidate_topk.csv` |
| available fields | Prediction table has `pred_cx`, `pred_cy`, `pred_w`, `pred_h`, `pred_heading_deg`, `pred_r`, `pred_az`, `pred_cross`, `posterior_score`, `ray_escape_source`, `ray_escape_decision`, `ray_escape_mode_rank`, `ray_escape_mode_r`, `n_candidates`. Candidate top-k table includes candidate-style selected rows. |
| inference-side available | Yes, as an earlier diagnostic/inference-side output. |
| derived from A019/A021/GT/oracle/panel review | The inference table header does not expose GT/final/oracle fields, but related eval/oracle outputs exist in the same task folder and must stay excluded. |
| collapses back to A001 candidate selection | Medium to high risk. It is already a prior refinement/selection behavior artifact and includes candidate count, source, decision, score, and top-k style surfaces. |
| uncertainty semantics | Direction/range escape support, not a general optical-conditioned shell. It may imply one escape mode rather than preserving a neutral search shell. |
| coordinate convention | Full-image predicted pixel geometry plus range-like `ray_escape_mode_r`; fan/range convention remains not frozen for Phase5B. |
| risks | Hidden reranking, mode-decision leakage, earlier selector assumptions, confusion between diagnostic escape correction and Phase5 shell. |
| recommendation | HOLD for shell/proxy selection. It may inform later optional Route D readiness only after convention and provenance rules are approved. Do not use candidate top-k output as a Phase5B shell. |

### D. Ray / Range Profile Support

| field | decision |
|---|---|
| path if known | `output/clean_no_gt_localizer_2026-05-31_gm17_ray_profile/gm17_range_posterior_modes_inference.csv`; `output/clean_no_gt_localizer_2026-05-31_gm17_ray_profile/gm17_ray_profile_peaks_inference.csv` |
| available fields | `mode_r`, `posterior_score`, `opt_score`, `pred_score`, `track_score`, `sar_peak_score`, `nearest_peak_rank`, `r_opt`, `sigma_opt`, `r_pred`, `r_track`, `mode_rank`; peak table has `pred_az`, `pred_r`, `range_prior_r`, `range_prior_sigma`, `peak_r`, `peak_score`, `peak_prominence`, `peak_width` |
| inference-side available | Yes, as inference-side ray/range diagnostic artifacts. |
| derived from A019/A021/GT/oracle/panel review | Inference headers do not expose final/GT/oracle fields. Eval counterparts exist and must stay excluded. |
| collapses back to A001 candidate selection | Not directly as candidate rows, but it can inherit upstream temporal/range priors and can become hidden scoring if posterior scores are used to select a shell. |
| uncertainty semantics | Range-mode support only. It does not define a full 2D image shell or extent by itself. |
| coordinate convention | Range-like coordinate only; image mapping and fan convention are not sufficiently frozen for default first-round proposal generation. |
| risks | Range convention error, false SAR peaks, inability to determine cross-track/center alone, leakage through posterior mode selection if used as a hard filter. |
| recommendation | HOLD as a primary shell. ACCEPT_WITH_CAVEAT only for optional Route D after `coordinate_convention_id`, fan/range mapping, and provenance policy are approved. |

### E. Wedge Profile Modes

| field | decision |
|---|---|
| path if known | `output/clean_no_gt_localizer_2026-05-31_gm17_wedge_escape/gm17_wedge_profile_modes_inference.csv` |
| available fields | `target_identity`, `scene`, `sar_frame_num`, `gm17_track_id`, `pred_r`, `pred_az`, `pred_cross`, `range_prior_r`, `range_prior_sigma`, `r_hat`, `cross_hat`, `az_offset_hat`, `r_std`, `cross_std`, `az_std`, `peak_r`, `peak_score`, `sar_mode_score`, `posterior_score`, `mode_rank`, visibility/risk fields |
| inference-side available | Yes, with a run manifest stating that inference scoring read inference tables, SAR images, and upstream inference features only. |
| derived from A019/A021/GT/oracle/panel review | The inference table header does not expose final/GT/oracle columns. Eval/oracle tables in the folder are excluded. |
| collapses back to A001 candidate selection | Medium risk. It is tied to earlier wedge escape/candidate expansion logic and may overrepresent prior Phase4 candidate behavior. |
| uncertainty semantics | Range/cross/azimuth mode support with mode scores and std-like fields. It is useful for state uncertainty, but not a neutral image-plane shell. |
| coordinate convention | Fan-polar-like coordinates and peak ranges; not enough to define default image-plane sampling without approved mapping. |
| risks | Convention dependency, score leakage, mode collapse, historical selector coupling, visible-risk semantics not approved for Phase5B generation. |
| recommendation | HOLD as primary shell. Use only as future optional geometry/range evidence after source ownership and coordinate convention review. |

### F. Visible Extent Features

| field | decision |
|---|---|
| path if known | `output/clean_no_gt_localizer_2026-05-31_visible_extent_gated/visible_extent_features.csv`; related `visible_extent_predictions_inference.csv` |
| available fields | `target_identity`, `scene`, `sar_frame_num`, `pred_r`, `visible_status`, `shape_mask_conf`, `support_px`, `support_quality`, `est_w`, `est_h`, `visible_area_ratio`, component/edge-touch fields, offsets; predictions table has predicted and refined geometry fields |
| inference-side available | Yes as image-derived diagnostic output; prior inventory marks it needs human review and diagnostic/future use. |
| derived from A019/A021/GT/oracle/panel review | No forbidden eval fields are indicated in the inspected inference header. |
| collapses back to A001 candidate selection | Not directly, but using refined geometry would turn visible support into a pseudo-final box, which violates Phase5A semantics. |
| uncertainty semantics | Visible SAR support, not optical prior shell. It can describe partial support and component behavior, but it should not define the search region. |
| coordinate convention | Component offsets and estimated extents are tied to image/crop processing conventions that are not declared for Phase5B. |
| risks | Visible centroid drift, threshold dependence, partial support mistaken for full vehicle, hidden image threshold tuning. |
| recommendation | REJECT as shell/proxy source. ACCEPT_WITH_CAVEAT later as SAR observation/readiness evidence for Route C, not as a shell. |

### G. Fan Geometry Prior Window

| field | decision |
|---|---|
| path if known | No standalone Phase5 fan-window artifact is frozen. Fan-like fields appear in A005/A001/ray/wedge tables as `r`, `az`, `cross`, `pred_r`, `pred_az`, `pred_cross`. |
| available fields | Existing fields can support range/azimuth/cross reasoning, but no frozen `shell_x1/y1/x2/y2` or fan-mask artifact is available. |
| inference-side available | Partially. Field values exist, but not as a formally defined shell object. |
| derived from A019/A021/GT/oracle/panel review | The candidate and temporal inference headers do not expose GT/final/oracle fields. |
| collapses back to A001 candidate selection | Low if independently specified later; medium if derived from A001 candidate spread. |
| uncertainty semantics | Potentially the correct long-term shell semantics, but not yet encoded as a first-round artifact. |
| coordinate convention | Fan/range/azimuth/cross mapping is not frozen enough for Route D or sector-band sampling. |
| risks | Incorrect fan convention, overshrunk shell, partial-visible center outside shell, route D overclaim. |
| recommendation | HOLD as an implementation source. Treat as the preferred future formal shell family, not the immediate first-round proxy. |

### H. Other Existing Inference-Safe Sources

| source | path if known | decision |
|---|---|---|
| Signed escape posterior | `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/signed_escape_posterior_inference.csv` | HOLD. It is useful uncertainty/direction evidence, but it is not a shell. |
| Candidate refined factor table | `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/candidate_refined_factor_inference.csv` | REJECT as shell. It is candidate-row based and can repackage A001 ranking behavior. |
| Older wedge candidate bank | `output/clean_no_gt_localizer_2026-05-31_gm17_wedge_escape/gm17_wedge_escape_candidate_bank_inference.csv` | REJECT. Prior inventory flags naming risk such as `final_score`; historical candidate-bank-like table. |
| Selected prediction / Viterbi outputs | `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/...` | REJECT. Selected outputs are behavior references, not input shell sources. |
| Raw scene directories | `D:\profile\research\data\GM_RM017\GM_RM017_SARframes`, `GM_RM017_SARframes_gray`, `GM_RM017_frames`, `GM_RM017_depth` | ACCEPT_WITH_CAVEAT for image/frame availability only. They do not define a target-specific shell without an inference-safe prior. |

## 3. Required Shell Semantics For First Diagnostic Run

The first diagnostic run needs a shell/proxy-shell record, even if it is materialized only inside a later approved implementation.

Required fields:

| field | requirement | current decision |
|---|---|---|
| `shell_id` | Stable id per target shell. | Can be derived later from target id plus shell source/version. Placeholder allowed until implementation config is approved. |
| `target_identity` | Required. | Available in A005 and Phase4D target set. |
| `scene` | Required. | Available in A005. |
| `sar_frame_num` | Required. | Available in A005. |
| `gm17_track_id` | Required when available. | Available in A005. |
| `shell_cx`, `shell_cy` | Required for center-window proxy. | Use A005 `pred_cx`, `pred_cy` under preferred proxy. |
| `shell_x1`, `shell_y1`, `shell_x2`, `shell_y2` | Required if bbox shell is used. | Not directly available. Can be generated later from `pred_cx`, `pred_cy`, `pred_w`, `pred_h`, and predeclared margin/crop policy. BLOCKED until that policy is declared. |
| `range_min`, `range_max`, `az_min`, `az_max`, `cross_min`, `cross_max` | Optional for A/B/C; required for Route D or fan-band shell. | Not directly available as bounds. A005 has point estimates only. Bounds are BLOCKED until uncertainty policy is declared. |
| `uncertainty_note` | Required. | Must state that A005 is a soft temporal/optical proxy, not final SAR localization. |
| `shell_source` | Required. | Preferred source: `gm17_temporal_inference_proxy`. |
| `shell_version` | Required. | Use source path/version id in a future config; do not invent executable version here. |
| `leakage_audit_status` | Required. | Must state inference-side source only and score/eval fields excluded. |
| `diagnostic_only_flag` | Required. | Always true for Phase5B first diagnostic. |

Missing-field policy:

- Missing `shell_id` can be a placeholder in this document, but must be fixed before implementation.
- Missing bbox shell bounds are not fatal for documentation, but implementation is BLOCKED until crop/margin policy is predeclared.
- Missing range/azimuth/cross bounds are acceptable for Route A/B/C if image-coordinate windows are used; they block Route D.
- Missing fan/valid-support mask is acceptable only if first round uses full-image bounds as the valid-support policy; any fan-mask claim remains blocked.

## 4. SAR Image Source Decision

### Pseudocolor / Display PNG

| field | decision |
|---|---|
| path field | A005 and A001 expose `sar_pseudocolor_path`, for example `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png`. Existing path-resolution reports confirm these PNG paths. |
| coordinate compatibility | Compatible with A001/A005 full-image pixel coordinates in existing audits; prior reports show images read as `1334 x 2308`. |
| inference-side available | Yes. It is referenced by inference-side tables. |
| display/pseudocolor artifact risk | High for energy/contrast semantics. It is a display image, not verified raw SAR intensity. |
| first-round recommendation | ACCEPT_WITH_CAVEAT as fallback image source and for visual/crop provenance. Do not make raw-SAR physics claims from this source. |

### Grayscale / Display PNG

| field | decision |
|---|---|
| path field | Directory exists: `D:\profile\research\data\GM_RM017\GM_RM017_SARframes_gray`. File names match SAR frame stems such as `000302.png`, but no existing A005 path column points directly to this folder. |
| coordinate compatibility | Expected to match the same frame grid as pseudocolor PNGs, but this must be verified by a future implementation precheck before use. |
| inference-side available | Yes as raw local scene data, not as a joined eval source. |
| display/pseudocolor artifact risk | Lower than pseudocolor for first diagnostic image operations, but still a display PNG rather than confirmed raw SAR. |
| first-round recommendation | ACCEPT_WITH_CAVEAT as preferred Route B/C image source if same-frame existence and image dimensions are prechecked before implementation. The path derivation policy must be declared in `sar_image_source_id` and `crop_policy_id`. |

### Raw SAR

| field | decision |
|---|---|
| path field | No raw `.mat`, `.raw`, `.bin`, `.tif`, or SAR-array source was identified in the GM_RM017 scene directory scan for this review. |
| coordinate compatibility | Unknown. |
| inference-side available | Not confirmed. |
| display/pseudocolor artifact risk | Not applicable until raw source is found. |
| first-round recommendation | HOLD / BLOCKED. Do not claim raw SAR intensity support in Phase5B first round. |

### Local Crop Source

| field | decision |
|---|---|
| path field | No preexisting crop table is selected. Crops should be derived later from the selected shell/proxy shell and SAR image source. |
| coordinate compatibility | Must preserve full-image coordinates by storing crop origin offsets. |
| inference-side available | Derivable from inference-side shell and image source only after implementation approval. |
| display/pseudocolor artifact risk | Same as selected image source. |
| first-round recommendation | ACCEPT_WITH_CAVEAT as a future derived artifact only. No crop is generated by this document. |

## 5. Coordinate And Valid Support Decision

Image coordinate convention:

- Use full-image pixel coordinates for first-round A/B/C documentation.
- Convention: `x` increases rightward, `y` increases downward, and `cx/cy` are image-plane center coordinates.
- This is consistent with existing A001/A005 fields and path-resolution reports, but it should still be named explicitly as `coordinate_convention_id = full_image_xy_display_png_v1` in a future config.

`cx/cy` convention:

- A005 `pred_cx/pred_cy` become `shell_cx/shell_cy` only.
- They are not final SAR centers.
- A001 `cx/cy` must not be copied into generated proposals except for explicitly separated A001-neighborhood comparison.

Crop coordinate vs full-image coordinate:

- Proposal outputs must use full-image coordinates.
- Any crop-local computation must store `crop_x0`, `crop_y0`, image source id, and source crop id in future outputs.
- A crop-local center must be mapped back to full-image `cx/cy` before Phase5C evaluation.

Valid image bounds:

- Known GM_RM017 SAR display PNG dimensions from prior path-resolution reports: height `1334`, width `2308`.
- First-round A/B/C may use image bounds only as valid support: `0 <= x < width`, `0 <= y < height`.
- This is a minimal support policy, not a fan-valid mask.

Fan / valid support mask availability:

- No frozen valid fan/support mask artifact is selected in this review.
- Fan-polar fields exist, but a mask or exact range/azimuth-to-image convention is not frozen.

Range / azimuth / cross convention:

- A001/A005/ray/wedge tables expose `r`, `az`, `cross`, `pred_r`, `pred_az`, `pred_cross`, `r_hat`, `cross_hat`, and related fields.
- These fields can be carried as metadata in the shell/proxy source.
- They are not sufficient for default Route D generation until `coordinate_convention_id`, range mapping, and valid support are approved.

Support-mask policy:

- First-round A/B/C can use `valid_support_source_id = image_bounds_only_display_png`.
- Route D must HOLD until fan/range convention and support policy are stronger.
- Route E must HOLD because heading/orientation and long-axis conventions remain outside the first-round center/extent baseline.

Route conclusions:

- Route A/B/C can be defined with image-coordinate shell windows and image bounds.
- Route D must HOLD unless a separate approval freezes fan/range convention and support mapping.
- Route E continues HOLD.

## 6. Recommended First-Round Shell Decision

Preferred shell/proxy shell source:

- `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv`
- Decision: ACCEPT_WITH_CAVEAT.
- Use as `gm17_temporal_inference_proxy`.
- Allowed fields: `target_identity`, `scene`, `sar_frame`, `sar_frame_num`, `sar_pseudocolor_path`, `pred_cx`, `pred_cy`, `pred_w`, `pred_h`, `pred_r`, `pred_az`, `pred_cross`, `gm17_track_id`, and track-size metadata if needed for audit.
- Excluded fields: `score`, `lr_score`, `sar_factor_score`, `temporal_factor_score`, `gm17_temporal_decision`, and any selected/ranking behavior.

Fallback shell/proxy shell source:

- A001 candidate envelope only as a fallback diagnostic envelope, not as the primary shell.
- Decision: ACCEPT_WITH_CAVEAT for fallback only if the implementation explicitly labels it `a001_envelope_baseline_proxy` and reports that it is A001-biased.
- It must not use `candidate_id`, C3/C4 ranks, oracle labels, selected files, or candidate source to rank or filter generated proposals.

Rejected or held shell sources:

- visible extent features: REJECT as shell, possible later Route C observation evidence.
- candidate refined factor table: REJECT as shell because it is candidate-row based.
- selected prediction/Viterbi outputs: REJECT because selected behavior is not a shell source.
- ray/range profile support: HOLD for optional Route D only.
- wedge profile modes: HOLD for optional geometry evidence only.
- fan geometry prior window: HOLD until formal fan-band shell artifact exists.
- raw SAR source: BLOCKED because not identified.

Route readiness:

- Route A can proceed in design only with the A005 proxy and a predeclared margin/crop/scale policy. Implementation remains HOLD until that config exists.
- Route B can proceed in design with grayscale display PNG preferred and pseudocolor fallback, but implementation remains HOLD until image-source id, crop policy, and local background policy are declared.
- Route C can proceed in design with grayscale display PNG preferred, but implementation remains HOLD until threshold family, component-size policy, and crop policy are declared.
- Optional Route D remains HOLD.

Decision on implementation:

- HOLD implementation for now.
- The source-selection part of the shell blocker is reduced, but not fully cleared because numeric shell/crop policy, target-set freeze id, image-source id, and support policy are not yet predeclared.

## 7. Updated Readiness

| item | status | source/path | risk | decision | readiness |
|---|---|---|---|---|---|
| target set | Phase4D GM_RM017 205 targets available | `output/gm17_phase4D_candidate_pool_ceiling_audit_20260629_001655/candidate_pool_ceiling_per_target.csv` | No standalone frozen target-set file | Use provisional `phase4D_gm_rm017_205_target_set` id in config, but freeze before execution | PARTIAL |
| selected shell/proxy shell | Preferred proxy selected | `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv` | Single temporal predicted box can be overread as final SAR state | ACCEPT_WITH_CAVEAT | PARTIAL |
| fallback shell/proxy shell | A001 envelope only as baseline fallback | `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv` | A001 bias and reranking collapse | ACCEPT_WITH_CAVEAT for fallback only | PARTIAL |
| SAR image source | Grayscale display PNG preferred; pseudocolor fallback | `D:\profile\research\data\GM_RM017\GM_RM017_SARframes_gray`; `D:\profile\research\data\GM_RM017\GM_RM017_SARframes` | Display-image artifacts; raw SAR absent | ACCEPT_WITH_CAVEAT | PARTIAL |
| crop policy | Not declared | future config field | Crop can change proposal behavior | Require predeclared margin/crop and origin-offset policy | BLOCKED |
| coordinate convention | Full-image XY display PNG convention acceptable for A/B/C | A001/A005 pixel fields plus prior path-resolution reports | Needs explicit id; not enough for Route D | ACCEPT_WITH_CAVEAT for A/B/C | PARTIAL |
| valid support policy | Image bounds only acceptable for A/B/C | prior reports: image height `1334`, width `2308` | Not a fan-valid mask | ACCEPT_WITH_CAVEAT | PARTIAL |
| Route A | Shell-grid can be specified | A005 proxy | blocked by margin/scale/offset config | conditional design GO, execution HOLD | PARTIAL |
| Route B | Energy/contrast can be specified | grayscale display PNG preferred | display artifact, peak-center mismatch, background policy missing | conditional design GO, execution HOLD | PARTIAL |
| Route C | component diagnostic can be specified | grayscale display PNG preferred | threshold and component policy missing | conditional design GO, execution HOLD | PARTIAL |
| optional Route D | range/radial support not ready | ray/range and wedge tables | fan/range convention and support mapping not frozen | HOLD | BLOCKED |

## 8. Predeclared Config Implications

The selected shell/proxy decision implies these config fields must exist before any future implementation.

```yaml
target_set_id: phase4D_gm_rm017_205_target_set  # provisional id; freeze before execution

shell_source_id: gm17_temporal_inference_proxy
shell_source_path: output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv
shell_version: TBD_before_implementation

fallback_shell_source_id: a001_envelope_baseline_proxy
fallback_shell_source_path: output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv
fallback_shell_use: comparison_only_or_explicit_fallback

sar_image_source_id: gm17_sarframes_gray_display_png
sar_image_source_path_policy: D:\profile\research\data\GM_RM017\GM_RM017_SARframes_gray\<sar_frame>.png
sar_image_fallback_source_id: gm17_sarframes_pseudocolor_display_png
sar_image_fallback_path_field: sar_pseudocolor_path

crop_policy_id: TBD_before_implementation
valid_support_source_id: image_bounds_only_display_png
coordinate_convention_id: full_image_xy_display_png_v1

route_list:
  - shell_grid
  - energy_contrast_peak
  - connected_component

route_config_id: TBD_before_implementation
output_bundle_id: TBD_before_implementation
```

Do not fill numeric values in this document. The following remain required before execution:

- shell margin or crop size;
- scale set;
- offset grid;
- maximum proposals per target;
- energy peak count;
- local background policy;
- component threshold family;
- component size filter;
- duplicate merge policy;
- leakage audit policy.

Route D config implication:

- `optional_radial_profile_policy` remains unset.
- `coordinate_convention_id` is not strong enough for radial/range proposal generation.
- Route D cannot be added to `route_list` unless a separate fan/range convention approval occurs.

## 9. Final Recommendation

Recommendation status:

- HOLD implementation.

Maximum blocker status:

- Partially relieved. The preferred proxy shell source is now selected: A005 `gm17_temporal_inference.csv`.
- Not fully cleared. Implementation still needs target-set freeze id, shell/crop margin policy, image-source id verification, valid-support policy, route config id, and leakage audit policy.

If a later implementation is approved, first round may only use:

- Route A: shell-grid / multi-scale sampling over the A005 proxy shell;
- Route B: local energy / contrast peak proposals inside the A005 proxy shell;
- Route C: simple connected-component diagnostic inside the A005 proxy shell.

Route D:

- Not allowed by default.
- HOLD until fan/range convention, valid support mapping, and range-to-image provenance are approved.

Still forbidden:

- Route E ridge / long-axis proposal;
- Route F hybrid ranker;
- C3/C4 integration;
- A001 row reranking under a new name;
- A019/A021/GT/oracle/panel-review use during generation;
- threshold tuning from Phase5C metrics;
- training;
- calibration.

## 10. Boundary Statement

This document is documentation-only.

- No code was added.
- No experiment was added.
- No proposal was generated.
- No candidate was generated.
- No C3/C4 ranking was changed.
- No A001/A005/A019/A021 source file was modified.
- No threshold tuning was performed.
- No model was trained.
- No calibration was performed.
- No push was performed.
- This file is not staged or committed unless explicitly approved later.
