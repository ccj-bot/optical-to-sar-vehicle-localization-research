# GM17 Scattering A0.2 Join Validation Acceptance

Date: 2026-06-30

Status: A0.2b key-only join validation acceptance note

Current validation output:

```text
output/gm17_post_inference_join_key_validation_20260630_091128
```

This document is a key-only join validation acceptance note. It is not an experiment, not Experiment A, not a metric report, not a performance conclusion, and not Phase5 approval.

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.

## 1. Purpose

This note records the A0.2b policy decision for A019/A021 post-inference audit joins.

It accepts target/frame-level left coverage for A019/A021 annotation tables when the right side is a source superset.

It does not:

- compute IoU;
- compute center error;
- read final box numeric values;
- read A021 condition/truncation/occlusion values;
- run high-IoU decomposition;
- run Experiment A;
- use A019/A021 for scoring;
- modify candidate bank;
- modify the GM17 selector.

## 2. Previous Result

Previous output:

```text
output/gm17_post_inference_join_key_validation_20260630_090227
```

Previous strict symmetric result:

| join_pair | previous_status | left_only | right_only | interpretation |
|---|---|---:|---:|---|
| `per_target_audit_to_A019` | `HOLD` | 0 | 237 | The per-target audit left side was fully covered, but A019 had additional annotation keys outside the GM17 per-target audit subset. |
| `per_target_audit_to_A021` | `HOLD` | 0 | 237 | The per-target audit left side was fully covered, but A021 had additional annotation keys outside the GM17 per-target audit subset. |

The previous HOLD came from a symmetric-set expectation. It was useful as a warning, but it over-constrained annotation tables that are broader source inventories.

## 3. Policy Decision

A019 and A021 are target/frame-level annotation tables.

For A019/A021 post-inference audit joins, the accepted policy is:

```text
per_target_audit left side must be fully covered.
right-side annotation source may be a superset.
```

Policy status name:

```text
POLICY_ACCEPTED_GO_FOR_LEFT_COVERAGE
```

This status applies only if all of the following are true:

- required key columns are present on both sides;
- `left_missing_key_rows = 0`;
- `right_missing_key_rows = 0`;
- `left_duplicate_key_count = 0`;
- `right_duplicate_key_count = 0`;
- `left_only_key_count = 0`;
- `right_only_key_count > 0`;
- the join spec explicitly sets `left_coverage_required = true`;
- the join spec explicitly sets `right_superset_allowed = true`.

This is intentionally not a plain `GO`. It means the join is accepted for left-side audit coverage under a source-superset annotation policy. It does not imply symmetric universe equality.

## 4. Validation Result

New output:

```text
output/gm17_post_inference_join_key_validation_20260630_091128
```

| join_pair | status | left_only | right_only | duplicate | missing | interpretation |
|---|---|---:|---:|---|---|---|
| `per_target_audit_to_A019` | `POLICY_ACCEPTED_GO_FOR_LEFT_COVERAGE` | 0 | 237 | left 0 / right 0 | left 0 / right 0 | Every per-target audit key is covered by A019. The 237 right-only keys are accepted as annotation source superset keys. |
| `per_target_audit_to_A021` | `POLICY_ACCEPTED_GO_FOR_LEFT_COVERAGE` | 0 | 237 | left 0 / right 0 | left 0 / right 0 | Every per-target audit key is covered by A021. The 237 right-only keys are accepted as annotation source superset keys. |
| `frozen_ranked_to_per_target_audit` | `GO` | 0 | 0 | left 205 / right 0 | left 0 / right 0 | Candidate-row many-to-one duplicates on the left are expected; all target/frame/track audit keys are covered. |

The validator read only join-key columns. It did not read final-box numeric values, condition labels, IoU values, center-error values, oracle values, or descriptor values.

## 5. Boundary

This acceptance note does not authorize:

- performance reporting;
- Experiment A decomposition;
- high-IoU bucket assignment;
- metric computation;
- new IoU computation;
- center error computation;
- descriptor extraction;
- scatter centroid computation;
- keyframe confidence;
- soft-anchor simulation;
- active selector changes;
- candidate-bank modification;
- Phase5 approval.

Allowed interpretation:

```text
A019/A021 post-inference audit joins are schema/key acceptable for the GM17 per-target audit subset under left-coverage policy.
```

Forbidden interpretation:

```text
A019/A021 are scoring inputs.
The right-side annotation universe exactly equals the per-target audit universe.
Experiment A has been run.
Performance has improved.
```

