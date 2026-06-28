# GM17 Phase4S SAR Structure Factor Diagnostic Design Spec

## 1. Current Position

This document belongs to Phase4S: SAR structure factor grounding.

It is not v3 ranking. It is not threshold tuning. It is not a final model. It is the diagnostic boundary for a future `sar_structure_factor`.

The current task is to move from a 40-case SAR structure scout to full GM_RM017 audit evidence before any fixed structure-only pilot is considered.

## 2. One-Sentence Definition

`sar_structure_factor` judges whether a candidate box covers the main scattering support in the SAR image, rather than merely sitting near the optical temporal prior, bright background texture, edge clutter, or a local pseudo-bright point.

## 3. Evidence Owned By The Factor

The factor may own only SAR-local image evidence around an existing candidate box:

- SAR image.
- Candidate box.
- Candidate local patch.
- Local background around the candidate.
- Energy relationship inside and outside the candidate box.
- Axis support along the candidate long and short axes.
- Main peak or high-energy region position relative to the candidate.

These inputs describe whether the candidate covers SAR structure. They do not generate candidates, move candidates, or override the optical-temporal prior.

## 4. Forbidden Evidence

The following evidence must not enter inference or scoring for `sar_structure_factor`:

- A019 `final_*` fields as inference input.
- A021 `condition`, `truncation`, or `occlusion` fields as inference input.
- `candidate_source` sorting.
- `temporal_factor_score`.
- `delta_*_from_pred`.
- `score`, `lr_score`, or `sar_factor_score`.
- GM17 selected output.
- B patch as ranking evidence.
- Oracle fields or oracle rank.
- GT-tuned thresholds.

A019 and A021 may be used only after inference outputs exist, for post-inference evaluation, path resolution, and failure grouping.

## 5. Current Candidate Feature Families

The current diagnostic candidate feature families are:

- `edge_spillover_ratio`: whether energy spills into a border band outside the candidate box.
- `inside_energy_fraction`: how much local energy is contained inside the candidate box.
- `box_to_background_ratio`: candidate box mean intensity relative to local background.
- `center_to_peak_distance`: distance from candidate center to the local high-energy peak.
- `simple_long_axis_support`: simple intensity support along the candidate long-axis direction.
- `simple_short_axis_support`: simple intensity support along the short-axis direction.
- `local_background_mean`: context only, not a direct positive signal.
- `box_top5_mean_intensity`: weak diagnostic feature for local high-energy content.

All of these are diagnostic candidate features. They are not active scoring rules.

## 6. Not Recommended As Primary Features Yet

These features should not be prioritized for a future pilot without stronger evidence:

- `box_sum_intensity`.
- `box_max_intensity`.
- `peak_to_background_ratio`.

The main reasons are sensitivity to candidate box size, pseudocolor/display mapping, and local extreme values. They may remain in audit tables for reliability checking, but should not become primary structure evidence.

## 7. Relationship To Other Factors

- `geometry_factor` owns candidate-table geometry plausibility.
- `optical_temporal_factor` owns the optical temporal soft prior.
- `sar_structure_factor` owns SAR patch structure around existing candidates.
- Visibility, missing-data, near-field, and edge cases remain future routes. A021 condition labels cannot be used to activate those routes during inference.

The intended separation is: optical proposes a soft prior, candidate tables provide fixed candidate geometry, and SAR structure decides whether the local SAR patch actually supports the candidate.

## 8. Full Audit Plan

The Phase4S full audit should:

- Extract SAR structure features for all 205 GM_RM017 targets.
- Compare `rank1_v1`, `best_proxy`, `best_center`, `v2a_rank1`, `v2b_rank1`, `v2c_rank1`, and v1 top-k candidate groups.
- Use top-k candidates only for feature distribution audit, not selection.
- Avoid creating, moving, filtering, or modifying candidates.
- Run separability analysis only.
- Enter a structure-only fixed pilot only if the full audit shows stable directionality and human panel review support.

## 9. Preconditions Before Any Structure-Only Pilot

A future structure-only fixed pilot requires:

- Stable SAR path resolution.
- Stable feature direction consistency.
- Human panel review support.
- Either raw SAR image support or explicit risk marking if only pseudocolor/display images are used.
- No GT-tuned thresholds.
- Rules written down before execution.

If these conditions are not met, the next action should be SAR path/patch manifest repair or independent candidate proposal research, not v3 table-rule search.
