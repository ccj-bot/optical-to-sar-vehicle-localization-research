# GM17 Scattering Post-Inference Join Key Policy

Date: 2026-06-30

Status: A0.1 post-inference join policy draft

This document defines a join-key policy for fixed-bank GM17 post-inference audit. It is not an actual join, not an experiment, not a metrics computation, and not Phase5 approval.

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.

## 1. Purpose

The A0 resolver reported:

```text
per_target_audit_to_A019 = HOLD because A019 lacks track_id alias
per_target_audit_to_A021 = HOLD because A021 lacks track_id alias
```

This policy resolves the semantic question:

```text
Should post-inference A019/A021 audit joins require track_id,
or should they use target/frame-level keys when the annotation table is target/frame-level?
```

Current answer:

```text
Do not force track_id for A019/A021 unless that table explicitly has a track_id field.
Use target/frame-level audit joins, then require future key-only uniqueness validation.
```

This document does not execute that validation.

## 2. Join Types

### Candidate-Level Join

Used for:

- `A001_candidate_bank -> frozen_ranked_candidates`
- `A001_candidate_bank -> A008_candidate_factor_joined`
- candidate-level factors;
- frozen candidate row identity;
- candidate-level rank/score/factor schema readiness.

Recommended canonical keys:

| Canonical Key | Current Alias |
|---|---|
| `target_id` | `target_identity` |
| `scene_id` | `scene` |
| `frame_id` | `sar_frame_num` or `sar_frame` |
| `track_id` | `gm17_track_id` |
| `candidate_id` | `candidate_id` |

Candidate-level joins should require `candidate_id` when both sides are candidate-row tables. They should require `track_id` when both sides expose it and the table is track-aware.

Candidate-level joins must not use:

- A019 final boxes;
- A021 condition labels;
- GT;
- IoU;
- oracle fields;
- center error;
- `candidate_source` as ranking evidence.

### Target/Frame-Level Audit Join

Used for:

- `per_target_audit_output -> A019_final_boxes`;
- `per_target_audit_output -> A021_condition_labels`;
- post-inference grouping and evaluation context after frozen output exists.

Recommended canonical keys:

| Canonical Key | Current Alias | Required? |
|---|---|---|
| `target_id` | `target_identity` | Yes |
| `scene_id` | `scene` | Yes |
| `frame_id` | `sar_frame_num` or `sar_frame` | Yes |
| `sample_id` | `sample_id` | Optional disambiguator when present |
| `final_id` | `final_id` | Optional A019-specific disambiguator when present |
| `track_id` | `gm17_track_id` | Required only if the audit table explicitly has it |

Policy:

```text
A019/A021 annotation tables may naturally be target/frame-level.
Lack of track_id is not automatically a join failure.
```

However, target/frame-level joins must pass future key-only validation before any audit use.

## 3. Why A019/A021 May Not Need `track_id`

A019 and A021 are annotation/evaluation tables, not candidate-row inference tables.

Observed A0 resolver facts:

- A019 exposes `target_id`, `scene_id`, and `frame_id` aliases, but not `track_id`.
- A021 exposes `target_id`, `scene_id`, and `frame_id` aliases, but not `track_id`.
- Candidate/rank/factor tables expose `gm17_track_id`.

Existing repository precedent:

- `scripts/gm17_phase4_evaluate_minimal_factor_pilot.py` declares `PILOT_GROUP_KEYS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]` for pilot candidate groups, but `EVAL_JOIN_KEYS = ["target_identity", "scene", "sar_frame_num"]` for A019/A021 evaluation joins.
- `scripts/gm17_phase4_evaluate_combined_structure_temporal_fixed_pilot.py` and `scripts/gm17_phase4_evaluate_factor_graph_prototype.py` use `GROUP_KEYS` with `gm17_track_id` for candidate groups and `TARGET_KEYS = ["target_identity", "scene", "sar_frame_num"]` for A019/A021 context.
- `scripts/phase5C_v0_model_diagnostic_audit.py` builds `final_by_target` and `condition_by_target` by `target_identity` after checking A019/A021 headers, showing an older target-level post-hoc join precedent.

Interpretation:

```text
Candidate-level identity and target/frame-level annotation identity are different layers.
```

Therefore, the resolver's strict `track_id` requirement is a useful warning, not the final policy for A019/A021.

The required next step is not to invent a track id. The required next step is a key-only uniqueness and coverage validation over target/frame-level keys.

## 4. Required Future Key-Only Validation

Future script name, if later approved:

```text
tools/diagnostics/validate_gm17_post_inference_join_keys.py
```

Do not create or run the script in this A0.1 step.

Allowed future validation behavior:

- read only join key columns;
- normalize key text consistently;
- count duplicate key sets in each table;
- count missing key values;
- count unmatched key sets between tables;
- output a key-only readiness report;
- output examples of keys only if needed for debugging, without eval values.

Forbidden future validation behavior:

- read IoU columns;
- read center-error columns;
- read final box numeric geometry except key columns;
- read A021 condition values except key columns;
- compute metrics;
- compute performance;
- compute new IoU;
- compute center error;
- tune thresholds;
- modify source tables;
- use A019/A021 to score candidates.

Minimum output schema for future key-only validation:

| Field | Meaning |
|---|---|
| `join_pair` | Canonical pair id. |
| `left_artifact_id` | Left artifact. |
| `right_artifact_id` | Right artifact. |
| `proposed_keys` | Keys used for the validation. |
| `left_missing_key_rows` | Count of rows with missing key fields on the left. |
| `right_missing_key_rows` | Count of rows with missing key fields on the right. |
| `left_duplicate_key_count` | Count of duplicate key groups on the left. |
| `right_duplicate_key_count` | Count of duplicate key groups on the right. |
| `left_only_key_count` | Count of left keys not present on right. |
| `right_only_key_count` | Count of right keys not present on left. |
| `status` | `GO`, `HOLD`, or `STOP`. |
| `notes` | Boundary and interpretation notes. |

## 5. Proposed Key Policy

| Join Pair | Proposed Keys | Required? | Status | Notes |
|---|---|---|---|---|
| `A001 -> frozen ranked` | `target_identity`, `scene`, `sar_frame_num`, `gm17_track_id`, `candidate_id` | Yes | `GO at header level` | Candidate-level pair; resolver showed both sides have keys. |
| `frozen ranked -> per-target audit` | `target_identity`, `scene`, `sar_frame_num`, `gm17_track_id` | Yes for current schema | `GO at header level` | Frozen output to post-inference audit table; resolver showed both sides have keys. |
| `per-target audit -> A019` | `target_identity`, `scene`, `sar_frame_num`; optional `sample_id` / `final_id` if needed and available | Yes after key-only validation | `HOLD` | Do not force `gm17_track_id` unless A019 explicitly provides it. Validate uniqueness and coverage first. |
| `per-target audit -> A021` | `target_identity`, `scene`, `sar_frame_num`; optional `sample_id` if needed and available | Yes after key-only validation | `HOLD` | Do not force `gm17_track_id` unless A021 explicitly provides it. Validate uniqueness and coverage first. |
| `A001 -> A005` | `target_identity`, `scene`, `sar_frame_num`, `gm17_track_id` | Yes | `GO at header level` | Prior/context join; no candidate id required because A005 is target/frame/track prior. |
| `A001 -> A008` | `target_identity`, `scene`, `sar_frame_num`, `gm17_track_id`, `candidate_id` | Yes | `GO at header level` | Candidate-level factor join. |
| `A007 -> A008` | `target_identity`, `scene`, `sar_frame_num`, `gm17_track_id` | Yes | `GO at header level` | Posterior/factor join at target/frame/track level; no candidate id required unless future schema says otherwise. |

Policy details:

- Use `candidate_id` only for candidate-row joins.
- Use `gm17_track_id` for track-aware inference/factor/rank joins.
- Use target/frame-level keys for A019/A021 if those tables are target/frame annotation tables.
- Never derive `gm17_track_id` from A019/A021 labels.
- Never use A019/A021 values as scoring inputs.

## 6. STOP / HOLD / GO

### GO

The following are currently GO:

- schema-level pairwise readiness for Line-FB main candidate/rank/factor chain;
- A001 to frozen ranked header-level join readiness;
- frozen ranked to per-target audit header-level join readiness;
- A001 to A005 header-level join readiness;
- A001 to A008 header-level join readiness;
- A007 to A008 header-level join readiness;
- target/frame-level join policy drafting.

### HOLD

The following remain HOLD:

- A019/A021 post-inference audit joins until target/frame key-only uniqueness validation is approved and completed;
- SAR axis/crop/normalization convention;
- SAR descriptor extraction;
- Experiment A schema validation execution;
- any use of final/condition labels beyond post-inference audit policy design.

### STOP

Stop immediately if any future step attempts:

- derive `track_id` from eval labels;
- use A019/A021 to score candidates;
- use `final_*` fields for descriptor crops;
- use condition/truncation/occlusion labels for missingness policy, route choice, keyframe policy, or anchor choice;
- use IoU, oracle, or center error during scoring;
- treat `axis_aligned_proxy_iou` as rotated IoU;
- infer heading/orientation/long-axis quality from AABB proxy;
- modify candidate bank;
- modify the GM17 selector;
- run training, OOF calibration, or formal Phase5 without explicit approval.

Current decision:

```text
GO for policy documentation.
HOLD for A019/A021 audit joins until future key-only validation.
STOP for any eval-field use during scoring or descriptor crop construction.
```

