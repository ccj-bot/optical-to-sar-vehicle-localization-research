# GM17 Scattering A0 Resolver Run Review 20260630 013623

Date: 2026-06-30

Status: A0.1 resolver output review

Reviewed output:

```text
output/gm17_scattering_artifact_resolver_20260630_013623
```

This document reviews the first read-only A0 resolver run. It is not an experiment report, not a performance conclusion, not Experiment A approval, and not Phase5 approval.

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.

## 1. Purpose

This review converts the A0 resolver output into a formal audit note.

The reviewed run only performed metadata, path, header/schema, manifest, alias, pairwise-join-readiness, and physical-opportunity checks. It did not compute metrics, IoU, center error, SAR descriptors, scatter centroid, keyframe confidence, or soft-anchor simulation.

The scope of this document is:

- record what the resolver found;
- separate Line-FB fixed-bank artifacts from Line-GP generated-proposal artifacts;
- identify join readiness and join-policy blockers;
- record physical convention HOLD items before any descriptor work;
- keep Experiment A as a separate later step.

## 2. Run Metadata

| Field | Value |
|---|---|
| Resolver commit | `ae74461 tools: add GM17 scattering A0 artifact resolver` |
| Output directory | `D:\profile\research\optical-to-sar-vehicle-localization-research-synthesis-20260629\output\gm17_scattering_artifact_resolver_20260630_013623` |
| Generated at | `2026-06-30T01:36:23` |
| Command mode | Conservative metadata/schema resolver, run with `--skip-row-count` |
| `py_compile` | Passed in the A0 resolver checkpoint; not rerun during this A0.1 review |
| `experiment_ran` | `false` |
| `metrics_computed` | `false` |
| `candidate_bank_modified` | `false` |
| `selector_modified` | `false` |
| `line_gp_excluded_from_fixed_bank_conclusion` | `true` |
| `performance_conclusion_produced` | `false` |
| `candidate_geometry_modified` | `false` |
| `descriptors_computed` | `false` |
| `keyframe_confidence_computed` | `false` |
| `soft_anchor_simulation_ran` | `false` |
| `formal_phase5_status` | `BLOCKED_FOR_OOF_CALIBRATION` |

## 3. Artifact Resolution Summary

Source files reviewed:

- `resolver_summary.json`
- `artifact_manifest.csv`
- `stop_hold_go_report.md`

Top-level counts:

| Item | Value |
|---|---:|
| Artifact count | 23 |
| Manifest `GO` | 18 |
| Manifest `HOLD` | 1 |
| Manifest `EXCLUDED_LINE` | 4 |
| Line-FB artifacts | 11 |
| External artifacts | 1 |
| Docs artifacts | 6 |
| Config artifacts | 1 |
| Line-GP artifacts | 4 |
| Row-count skipped count | 12 |

Row counts were skipped by flag. The resolver still read headers, JSON top-level keys, file existence, file size, hashes or metadata where allowed, and path roles. It did not read raw candidate/eval rows for metric computation.

### Line-FB Core Artifacts Found

| Artifact | Status | Field Layer | Role |
|---|---|---|---|
| `A001_candidate_bank` | `GO` | `inference_safe` | Fixed candidate identity and frozen candidate geometry schema lock. |
| `A005_optical_temporal_prior` | `GO` | `inference_safe` | Soft optical/temporal prior and context schema lock. |
| `A007_signed_escape_posterior` | `GO` | `mixed` | Schema/path clue, diagnostic field availability, factor provenance, double-counting audit readiness. |
| `A008_candidate_factor_joined` | `GO` | `mixed` | Joined candidate factor/provenance readiness clue, not active scoring. |
| `frozen_ranked_candidates` | `GO` | `mixed` | Frozen rank and score reference schema lock only. |
| `selected_rank1_output` | `GO` | `mixed` | Frozen selected rank1 reference for post-hoc comparison only. |
| `per_target_audit_output` | `GO` | `post_inference_audit` | Post-inference target-level audit schema lock. |
| `evaluation_summary` | `GO` | `post_inference_audit` | JSON key inventory for completed post-inference audit output. |
| `evaluation_condition_groups` | `GO` | `post_inference_audit` | Post-inference grouped audit schema lock. |
| `A019_final_boxes` | `GO` | `post_inference_audit` | Final-box schema lock for post-inference audit only. |
| `A021_condition_labels` | `GO` | `post_inference_audit` | Condition/truncation/occlusion schema lock for post-inference grouping only. |

Important boundary: all A019/A021/final/condition/oracle/audit fields remain post-inference audit only. They do not become inference inputs, scoring fields, crop sources, selector patches, or candidate-bank modification inputs.

### SAR Image / Crop Source

| Artifact | Status | Notes |
|---|---|---|
| `SAR_image_or_crop_source` | `HOLD` | External image directory exists and top-level inventory was read: 766 `.png` files, first names `000000.png` to `000004.png`. The resolver did not open pixels, did not recursively hash the directory, and did not treat existence as descriptor readiness. Notes include `external_image_path_exists_but_axis_crop_convention_unverified`. |

SAR image/crop source existence is a prerequisite clue only. It does not confirm range/azimuth convention, crop origin, local coordinates, normalization policy, descriptor readiness, or physical interpretability.

### Line-GP Excluded Artifacts

| Artifact | Exists | Status | Boundary |
|---|---|---|---|
| `phase4D_candidate_pool_ceiling` | `true` | `EXCLUDED_LINE` | Path/schema clue only; `NOT_FOR_FIXED_BANK_CONCLUSION`. |
| `phase5B_proposal_candidates` | `true` | `EXCLUDED_LINE` | Generated-proposal line; not mixed into Line-FB. |
| `phase5C_metrics_summary` | `false` | `EXCLUDED_LINE` | Excluded generated-proposal audit path clue only. |
| `phase5C_candidate_policy_summary` | `false` | `EXCLUDED_LINE` | Excluded generated-proposal policy path clue only. |

Line-GP artifacts cannot support fixed-bank ceiling claims, A001 conclusions, selector patches, or formal Phase5 approval.

## 4. What This Changes

Old state from the execution bridge:

```text
The current synthesis worktree appeared to lack GM17 candidate/eval CSV/JSON artifacts.
```

New state after the A0 resolver run:

```text
With extra roots, the resolver found concrete Line-FB artifacts in adjacent local research output roots.
```

This is a meaningful readiness update, but only at A0 metadata/schema level.

It establishes:

- concrete paths for A001/A005/A007/A008 and frozen fixed-bank output artifacts;
- header/schema presence for Line-FB main-chain artifacts;
- separated accounting for Line-GP generated-proposal artifacts;
- a first pairwise join readiness report;
- a field alias risk inventory;
- physical convention blockers.

It does not establish:

- Experiment A results;
- high-IoU decomposition results;
- center-size likelihood results;
- SAR descriptor readiness;
- keyframe readiness;
- any mainline performance conclusion;
- formal Phase5 readiness.

## 5. Pairwise Join Summary

Source file reviewed:

- `pairwise_join_readiness.csv`

The resolver checked pairwise readiness using each artifact's own header columns only. It did not read sample rows, perform actual joins, or compute row-match counts.

| Join ID | Left | Right | Required Keys | Status | Notes |
|---|---|---|---|---|---|
| `A001_to_frozen_ranked` | `A001_candidate_bank` | `frozen_ranked_candidates` | `target_id;scene_id;frame_id;track_id;candidate_id` | `GO` | Both sides expose all required aliases. |
| `frozen_ranked_to_per_target_audit` | `frozen_ranked_candidates` | `per_target_audit_output` | `target_id;scene_id;frame_id;track_id` | `GO` | Both sides expose all required aliases. |
| `per_target_audit_to_A019` | `per_target_audit_output` | `A019_final_boxes` | `target_id;scene_id;frame_id;track_id` | `HOLD` | A019 exposes `target_id;scene_id;frame_id` but no `track_id` alias. |
| `per_target_audit_to_A021` | `per_target_audit_output` | `A021_condition_labels` | `target_id;scene_id;frame_id;track_id` | `HOLD` | A021 exposes `target_id;scene_id;frame_id` but no `track_id` alias. |
| `A001_to_A005` | `A001_candidate_bank` | `A005_optical_temporal_prior` | `target_id;scene_id;frame_id;track_id` | `GO` | Both sides expose all required aliases. |
| `A001_to_A008` | `A001_candidate_bank` | `A008_candidate_factor_joined` | `target_id;scene_id;frame_id;track_id;candidate_id` | `GO` | Both sides expose all required aliases. |
| `A007_to_A008` | `A007_signed_escape_posterior` | `A008_candidate_factor_joined` | `target_id;scene_id;frame_id;track_id` | `GO` | Both sides expose all required aliases. |

Interpretation:

- The Line-FB candidate/rank/factor chain is schema-ready at header level.
- A019/A021 joins require a post-inference join-key policy decision.
- The A019/A021 HOLD is not proof of unusability. It means the current resolver required `track_id`, while the annotation tables appear to be target/frame-level artifacts.
- Any future validation must remain key-only until explicitly approved.

## 6. Observed Alias Risk Summary

Source file reviewed:

- `observed_field_alias_hits.csv`

Summary:

| Item | Result |
|---|---|
| `STOP_RISK` rows | 0 observed |
| `HOLD_FOR_FIELD_LAYER_AUDIT` rows | 0 observed |
| Observed alias status counts | `OBSERVED=103`, `ABSENT=2371`, `PROVENANCE_ONLY_REVIEW=10`, `AUDIT_ONLY_OK=46` |

Observed risk interpretation:

- `candidate_source`, `candidate_detail`, `candidate_expansion_state`, `candidate_expansion_reason`, `proposal_source`, and `provenance` appear, but remain provenance-only. They are not ranking evidence, selector evidence, route shortcuts, or anchor-choice inputs.
- `axis_aligned_proxy_iou` appears only in `per_target_audit_output` as `AUDIT_ONLY_OK`.
- `center_error`, oracle/best-candidate fields, `final_*`, and A021 condition/truncation/occlusion fields appear only in post-inference audit artifacts or excluded/future-line artifacts.
- `rotated_iou_future`, range/azimuth residual fields, and orientation/heading/long-axis error fields did not surface as inference inputs in the observed headers/keys.

Boundary:

`axis_aligned_proxy_iou` is audit-only AABB proxy. It is not rotated IoU and cannot support heading, orientation, or long-axis conclusions.

## 7. Physical Opportunity Summary

Source file reviewed:

- `physical_opportunity_checklist.csv`

Physical checklist status counts:

| Status | Count |
|---|---:|
| `HOLD` | 6 |
| `GO` | 3 |

HOLD rows:

| Check ID | Status Meaning |
|---|---|
| `range_azimuth_axis_convention` | Prerequisites present, but range/azimuth convention is unverified. HOLD for axis convention audit. |
| `scatter_centroid_offset_feasibility` | Prerequisites present, but crop origin, coordinate convention, and normalization are unverified. |
| `candidate_local_crop_convention` | Prerequisites present, but crop origin and local coordinate convention are unverified. |
| `multi_scale_support_regions` | Prerequisites present, but crop/local convention is unverified. |
| `local_background_normalization` | Prerequisites present, but intensity normalization policy is unverified. |
| `sar_image_or_crop_source` | Image source path exists, but convention is unverified. |

GO rows, at prerequisite/header level only:

| Check ID | Meaning |
|---|---|
| `frame_track_ordering` | Frame and track aliases are present. |
| `candidate_mode_cluster_feasibility` | Candidate id and geometry aliases are present. |
| `identifiability_anti_keyframe_feasibility` | Frozen rank/score aliases and SAR source path are present. |

Important interpretation:

```text
prerequisites_present != descriptor readiness GO
```

The resolver did not compute descriptors or image statistics. SAR descriptor extraction remains blocked until axis, crop, local-coordinate, and normalization contracts are explicitly audited and frozen.

## 8. Current Decision

Current decision:

```text
HOLD for Experiment A.
GO only for A0.1 documentation and convention/join policy audit.
```

Allowed next work:

- review A0 resolver outputs;
- write physical convention audit plan;
- write post-inference join key policy;
- prepare future key-only/schema-only validation steps.

Still forbidden:

- Experiment A/B/C/D/E/F;
- metrics computation;
- new IoU computation;
- center error computation;
- SAR descriptor computation;
- scatter centroid computation;
- keyframe confidence computation;
- soft-anchor simulation;
- training;
- OOF calibration;
- candidate bank modification;
- GM17 selector modification;
- Phase5 approval;
- use of A019/A021/GT/IoU/oracle/center-error/final-box fields for scoring.

