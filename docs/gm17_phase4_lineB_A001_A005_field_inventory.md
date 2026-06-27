# GM17 Phase4 Line B A001/A005 Field Inventory

Date: 2026-06-28

Status: read-only field inventory and interpretation note. This document is not an execution design, not an experiment, not candidate selection, not metric computation, not threshold tuning, not calibration, and not a data-join artifact.

Allowed sources read in this round:

- `docs/gm17_phase4_geometry_temporal_manifest_allowlist_denylist.md`
- `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv`
- `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv`

Only CSV headers, row counts, column counts, non-empty counts, simple dtype guesses, safe sample values, and field-name scans were inspected. A019/A021 were not read, no GT table was joined, and no A001/A005 joined table was created.

## 1. 当前定位

本文档只回答一个问题：A001 candidate bank 和 A005 optical temporal prior 各自包含哪些字段，这些字段大概表达什么，以及它们和当前 Line B manifest 的 allowlist/denylist 是否一致。

本文档不是可执行配置，不选择候选，不计算 IoU、center error、recall、rank、oracle rank 或任何性能指标，不拟合权重，不调阈值，不做 calibration，不生成 YAML、脚本、notebook 或 derived dataset。它的用途是帮助研究者先读懂 A001/A005 的字段边界，再决定后续是否写非执行的 combined geometry + temporal design note。

## 2. A001 是什么

A001 是当前 GM_RM017-only Line B pilot 的 candidate bank。通俗地说，它是一张“已有 SAR 候选框清单”：每一行代表一个候选车框或候选状态，包含候选框中心、宽高、角度、fan-polar 坐标、候选来源和若干候选扩展/诊断字段。Line B 后续如果继续推进，只能在这批已存在的 SAR 候选中做设计；A001 不能被修改、过滤、扩展，也不能拿来生成 GM_RM011 或 GM_RM019 候选。

Path:

```text
output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv
```

Read-only inventory:

| item | value |
|---|---:|
| rows | 58251 |
| columns | 24 |
| scene sample | `GM_RM017` |

### 2.1 A001 identity / join fields

These fields identify the candidate row, target/frame context, and possible join keys for a future A001/A005 design. They are not scoring features by themselves.

| field | non-empty | dtype guess | safe samples | interpretation | manifest status |
|---|---:|---|---|---|---|
| `target_identity` | 58251 | string | `gm_rm017_00009`; `frameadd_gm_rm017_000149_000310_01`; `gm_rm017_00016` | Target-level identity used to align rows across GM_RM017 tables. | allow after join approval |
| `scene` | 58251 | string | `GM_RM017` | Scene scope marker. It supports the GM_RM017-only boundary check. | allow as scope metadata |
| `sar_frame` | 58251 | string | `000302.png`; `000310.png`; `000315.png` | SAR frame filename metadata. | allow as metadata |
| `sar_frame_num` | 58251 | integer | `302`; `310`; `315` | Numeric SAR frame id. It may support row alignment but does not activate transition. | allow after join approval |
| `candidate_id` | 58251 | string | `gm_rm017_00009::base_candidate::0001`; `gm_rm017_00009::wedge_joint_candidate::0002`; `gm_rm017_00009::wedge_joint_candidate::0003` | Candidate-node id. It identifies one candidate row inside the fixed bank. | allow after A001 approval |
| `gm17_track_id` | 58251 | integer | `0`; `1`; `2` | GM17 track grouping context. | allow after join approval; transition remains inactive |

Human confirmation still needed:

- whether `candidate_id` is stable and unique in the approved A001 boundary;
- whether `target_identity + sar_frame_num + gm17_track_id` is the correct A001/A005 alignment surface;
- whether `scene` should be required to equal `GM_RM017` in any future gate;
- whether `sar_frame` is only metadata or part of a future integrity check.

### 2.2 A001 candidate geometry fields

These are the main candidate-state fields named by the manifest geometry allowlist.

| field | non-empty | dtype guess | safe samples | likely meaning | manifest status |
|---|---:|---|---|---|---|
| `cx` | 58251 | float | `884.2430142295481`; `901.293322084663`; `906.9039291013452` | Candidate center x in SAR image coordinates. | allow after field approval |
| `cy` | 58251 | float | `970.5339885006634`; `1011.3249140313598`; `1006.9632015210022` | Candidate center y in SAR image coordinates. | allow after field approval |
| `w` | 58251 | float | `160.0`; `185.0`; `140.0` | Candidate OBB stored width or size axis. | allow after unit/convention approval |
| `h` | 58251 | float | `75.0`; `85.0`; `65.0` | Candidate OBB stored height or size axis. | allow after unit/convention approval |
| `heading` | 58251 | float | `175.0`; `0.0` | Candidate OBB axis angle. It is not automatically vehicle-head direction. | allow after angle convention approval |

These fields are candidate-side values. They must not be replaced by `final_cx`, `final_cy`, `final_w`, `final_h`, or `final_heading_deg`.

### 2.3 A001 fan-polar coordinate fields

These fields express the same candidate in the SAR fan-polar workspace or related range/cross-range convention. They are central to comparing an existing SAR candidate against an optical temporal prior.

| field | non-empty | dtype guess | safe samples | likely meaning | manifest status |
|---|---:|---|---|---|---|
| `r` | 58251 | float | `449.747`; `407.12177502673626`; `419.12177502673626` | Candidate fan-polar range state. | allow after convention approval |
| `az` | 58251 | float | `-38.36847968280792`; `-39.34776681634841`; `-38.34776681634841` | Candidate fan-polar azimuth state. | allow after units/sign/wrap approval |
| `cross` | 58251 | float | `12.0`; `7.007558945020477`; `19.007558945020477` | Candidate cross-range state. | allow after convention approval |

The manifest allows A005 to read these fields only for comparison. A005 must not overwrite them or generate a new candidate center.

### 2.4 A001 source / provenance fields

These fields describe where a candidate came from or why the bank contains it. They are useful for understanding the bank, but the current Line B manifest does not activate source scoring.

| field | non-empty | dtype guess | safe samples | likely meaning | manifest status |
|---|---:|---|---|---|---|
| `sar_pseudocolor_path` | 58251 | string | `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png`; `...\000310.png`; `...\000315.png` | Source SAR image path metadata. | metadata only |
| `candidate_source` | 58251 | string | `base_candidate`; `wedge_joint_candidate`; `bidirectional_escape_candidate` | Candidate-generation family or source type. | deferred; future controlled source design only |
| `candidate_detail` | 58251 | string | `current_gm17_temporal_prediction`; `mode_rank=1;mode_r=419.1;mode_cross=19.0;mode_az_offset=0.02`; `mode_rank=2;mode_r=375.0;mode_cross=16.7;mode_az_offset=0.23` | Candidate-generation detail string. | deferred/diagnostic |
| `candidate_expansion_state` | 58251 | string | `high_risk_expand`; `normal_compact` | Bank expansion state category. | deferred/diagnostic |
| `candidate_expansion_reason` | 58251 | string | `lr_score_lt_0.9|wedge_posterior_lt_0.75`; `lr_score_lt_0.9`; `base_plus_wedge_only` | Reason string for why candidate expansion occurred. | deferred/diagnostic |
| `gm17_anchor_strength` | 58251 | float | `0.0`; `0.4854166586321305`; `0.462920549597092` | Track/anchor support diagnostic. | deferred until origin review |

These fields can explain A001 provenance. They should not be used as current geometry + temporal scoring inputs without a separate source/diagnostic ownership review.

### 2.5 A001 diagnostic / deferred fields

These fields look like precomputed relationships between candidate state and temporal prediction. The manifest explicitly keeps them deferred by default.

| field | non-empty | dtype guess | safe samples | likely meaning | manifest status |
|---|---:|---|---|---|---|
| `delta_r_from_pred` | 58251 | float | `0.0`; `-42.625224973263755`; `-30.625224973263755` | Candidate range offset from a temporal prediction. | deferred until derivation/origin review |
| `delta_cross_from_pred` | 58251 | float | `0.0`; `-4.992441054979523`; `7.007558945020477` | Candidate cross-range offset from a temporal prediction. | deferred until derivation/origin review |
| `delta_az_from_pred` | 58251 | float | `0.0`; `-0.9792871335404882`; `0.02071286645951176` | Candidate azimuth offset from a temporal prediction. | deferred until derivation/origin/wrap review |
| `temporal_factor_score` | 58251 | float | `0.5`; `0.9263152127595536`; `0.9456906195389582` | Precomputed temporal support score or compatibility score. | deferred until opaque-score origin review |

The safe interpretation is: these fields may be helpful later, but the current manifest does not allow blindly using them. A future design must decide whether to recompute deltas from approved raw fields or accept these precomputed values after origin review.

### 2.6 A001 suspicious / forbidden-looking fields

Field-name scan checked for:

```text
final_*, gt_*, iou, center_err, oracle, selected, condition, truncation, occlusion
```

Result: no A001 column names matched those forbidden-looking patterns.

This is a column-name scan only. It does not prove every score-like field is safe. Fields such as `candidate_source`, `candidate_detail`, `candidate_expansion_*`, `gm17_anchor_strength`, `delta_*_from_pred`, and `temporal_factor_score` still need origin review before any future scoring use.

## 3. A005 是什么

A005 is the GM_RM017 optical temporal prior table. In plain language, it is a row-level optical-to-SAR soft prediction: for a target/frame, it records where the optical/temporal chain thinks the SAR state may be, including predicted image coordinates, predicted fan-polar coordinates, status, score-like fields, and track/anchor diagnostics.

It is not a candidate bank. It should not create, move, filter, or overwrite SAR candidates. In the current Line B boundary, A005 can only provide a soft compatibility reference for existing A001 candidates after human approval.

Path:

```text
output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv
```

Read-only inventory:

| item | value |
|---|---:|
| rows | 205 |
| columns | 25 |
| scene sample | `GM_RM017` |

### 3.1 A005 identity / join fields

These fields are candidate join-key candidates or row context fields. A005 has no `candidate_id`, which is expected because it is a row-level prior rather than a candidate table.

| field | non-empty | dtype guess | safe samples | interpretation | manifest status |
|---|---:|---|---|---|---|
| `target_identity` | 205 | string | `gm_rm017_00009`; `frameadd_gm_rm017_000149_000310_01`; `gm_rm017_00016` | Target-level identity for temporal prior rows. | allow after join approval |
| `scene` | 205 | string | `GM_RM017` | Scene scope marker. | allow as scope metadata |
| `sar_frame` | 205 | string | `000302.png`; `000310.png`; `000315.png` | SAR frame filename metadata. | allow as metadata |
| `sar_frame_num` | 205 | integer | `302`; `310`; `315` | Numeric frame id. | allow after join approval |
| `gm17_track_id` | 205 | integer | `0`; `1`; `2` | Track grouping context. | allow after join approval; transition remains inactive |
| `sar_pseudocolor_path` | 205 | string | `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000302.png`; `...\000310.png`; `...\000315.png` | SAR image path metadata. | metadata only |

Human confirmation still needed:

- whether A005 has one row per `target_identity + sar_frame_num + gm17_track_id`;
- whether `sar_frame` should be used only as metadata or also as a consistency check;
- how to handle A001 candidate rows when the matching A005 prior is missing;
- how to handle A005 rows with no A001 candidates, without creating new candidates.

### 3.2 A005 predicted SAR coordinate fields

These are the optical/temporal prediction fields. The manifest currently allows only the fan-polar prediction fields for future optical temporal comparison after approval.

| field | non-empty | dtype guess | safe samples | likely meaning | manifest status |
|---|---:|---|---|---|---|
| `pred_r` | 205 | float | `449.747`; `426.656`; `511.175` | Predicted SAR fan-polar range. | allow after A005 approval |
| `pred_az` | 205 | float | `-38.36847968280792`; `-34.5740953`; `-42.32320490687847` | Predicted SAR fan-polar azimuth. | allow after units/sign/wrap approval |
| `pred_cross` | 205 | float | `12.0`; `-12.0`; `-18.0` | Predicted SAR cross-range. | allow after convention approval |
| `pred_cx` | 205 | float | `884.2430142295481`; `902.0041512142404`; `796.5112807523187` | Predicted image-space center x. | deferred; may become center generator if misused |
| `pred_cy` | 205 | float | `970.5339885006634`; `986.1040863366524`; `964.7780539174112` | Predicted image-space center y. | deferred; may become center generator if misused |
| `pred_w` | 205 | float | `160.0`; `185.0`; `140.0` | Predicted width or size axis. | deferred; optical size prior not active |
| `pred_h` | 205 | float | `75.0`; `85.0`; `65.0` | Predicted height or size axis. | deferred; optical size prior not active |
| `pred_heading_deg` | 205 | float | `175.0`; `0.0` | Predicted heading/OBB angle. | deferred; heading convention and source need review |

The main safety issue is that `pred_cx/pred_cy` can be misread as final SAR center generation. Current Line B should instead compare existing A001 candidates against `pred_r/pred_cross/pred_az` as a soft prior.

### 3.3 A005 temporal status / diagnostic fields

These fields describe the status, source, track support, or anchor context of the temporal prior. They may be useful for future diagnostics but are not active scoring fields by default.

| field | non-empty | dtype guess | safe samples | likely meaning | manifest status |
|---|---:|---|---|---|---|
| `pred_status` | 205 | string | `ok` | Prediction status. | deferred; possible neutralization gate after review |
| `gm17_temporal_source` | 205 | string | `base`; `temporal_shell` | Source family of temporal prediction. | deferred/diagnostic |
| `gm17_temporal_decision` | 205 | string | `keep_base_no_anchor`; `keep_base_consistent_or_weak_anchor`; `switch_to_temporal_shell` | Decision label from temporal-prior generation. | deferred/diagnostic; do not copy decision behavior |
| `gm17_track_size` | 205 | integer | `75`; `66`; `60` | Track length or number of track members. | deferred/diagnostic |
| `gm17_anchor_n` | 205 | integer | `0`; `2`; `4` | Number of anchors used by temporal process. | deferred/diagnostic |
| `gm17_anchor_strength` | 205 | float | `0.0`; `0.4854166586321305`; `0.462920549597092` | Anchor strength diagnostic. | deferred/diagnostic |
| `n_candidates` | 205 | integer | `1`; `38`; `14` | Candidate count associated with the row or source process. | deferred/diagnostic |

`gm17_temporal_decision` deserves special care: even if it is useful for explaining the table, it may encode a prior decision path. It should not become a shortcut for Line B candidate selection.

### 3.4 A005 precomputed score / delta fields

A005 contains score-like fields but no `delta_*_from_pred` columns.

| field | non-empty | dtype guess | safe samples | likely meaning | manifest status |
|---|---:|---|---|---|---|
| `score` | 205 | float | `0.8700496766123451`; `0.8575798881807746`; `0.7675070157723183` | General score-like field from temporal/source process. | deferred until origin review |
| `lr_score` | 205 | float | `0.8001764703658054`; `0.7609982816549539`; `0.6862954409998868` | Score-like field, possibly localizer/regression confidence. | deferred until origin review |
| `sar_factor_score` | 205 | float | `0.5`; `0.6366808528168002`; `0.7590959315279395` | SAR-related score-like field. | deferred until ownership review |
| `temporal_factor_score` | 205 | float | `0.5`; `0.9263152127595536`; `0.9456906195389582` | Precomputed temporal support score. | deferred until opaque-score origin review |

Current safe policy: do not use these scores for Line B scoring until the project decides what they encode and whether they duplicate source, temporal decision, selected-reference behavior, or earlier model behavior.

### 3.5 A005 suspicious / forbidden-looking fields

Field-name scan checked for:

```text
final_*, gt_*, iou, center_err, oracle, selected, condition, truncation, occlusion
```

Result: no A005 column names matched those forbidden-looking patterns.

This is a field-name safety result only. It does not automatically approve score-like fields, temporal decision fields, or `pred_cx/pred_cy` as inference inputs.

## 4. A001/A005 可能如何连接

This round did not join A001 and A005. It only checked whether candidate join keys exist.

Candidate join keys present in both A001 and A005:

| candidate key | A001 exists | A005 exists | current interpretation |
|---|---|---|---|
| `target_identity` | yes | yes | Likely target-level alignment key. |
| `scene` | yes | yes | Scope check; should remain `GM_RM017`. |
| `sar_frame` | yes | yes | Frame filename metadata or optional consistency check. |
| `sar_frame_num` | yes | yes | Likely numeric frame alignment key. |
| `gm17_track_id` | yes | yes | Track context; does not activate transition. |
| `candidate_id` | yes | no | Candidate-level key exists only in A001, as expected. |

Likely future join surface for human review:

```text
target_identity + scene + sar_frame_num + gm17_track_id
```

Potential risks to confirm before any future implementation:

- A001 is candidate-level while A005 is row-level prior, so one A005 row may correspond to many A001 candidate rows.
- If multiple A005 rows share the same target/frame/track keys, a future join could become many-to-many.
- If A001 has candidates without an A005 prior, missing temporal prior should likely be neutralized or flagged, not used to punish candidates by default.
- If A005 has row-level priors without A001 candidates, Line B must not generate new candidates from those priors.
- `sar_frame` and `sar_frame_num` may be redundant; human review should decide whether both are required for integrity checks.
- `gm17_track_id` should remain join context only. It must not silently activate transition, Viterbi, or path scoring.

## 5. 与 manifest 的对应关系

### 5.1 Manifest allowlist fields found

| manifest group | field | A001 | A005 | status |
|---|---|---|---|---|
| identity/join | `candidate_id` | yes | no | Expected: candidate id belongs to A001. |
| identity/join | `target_identity` | yes | yes | Present in both; needs join approval. |
| identity/join | `scene` | yes | yes | Present in both; supports GM_RM017 scope check. |
| identity/join | `sar_frame` | yes | yes | Present in both; metadata or consistency key. |
| identity/join | `sar_frame_num` | yes | yes | Present in both; likely frame key. |
| identity/join | `gm17_track_id` | yes | yes | Present in both; context only. |
| A001 geometry | `cx` | yes | no | Present in A001 as candidate state. |
| A001 geometry | `cy` | yes | no | Present in A001 as candidate state. |
| A001 geometry | `w` | yes | no | Present in A001 as candidate state. |
| A001 geometry | `h` | yes | no | Present in A001 as candidate state. |
| A001 geometry | `heading` | yes | no | Present in A001 as candidate OBB axis angle. |
| A001 fan-polar | `r` | yes | no | Present in A001 as candidate state. |
| A001 fan-polar | `az` | yes | no | Present in A001 as candidate state. |
| A001 fan-polar | `cross` | yes | no | Present in A001 as candidate state. |
| A005 predicted | `pred_r` | no | yes | Present in A005 as soft temporal prior. |
| A005 predicted | `pred_cross` | no | yes | Present in A005 as soft temporal prior. |
| A005 predicted | `pred_az` | no | yes | Present in A005 as soft temporal prior. |

The manifest's core allowlist is therefore physically present in the expected tables.

### 5.2 Manifest denylist field-name scan

Forbidden-looking field-name patterns scanned:

```text
final_*, gt_*, iou, center_err, oracle, selected, condition, truncation, occlusion
```

Result:

| table | forbidden-looking column names found |
|---|---|
| A001 | none |
| A005 | none |

This supports the next design step, but it is not a full leakage proof. The score-like and decision-like fields still require origin review.

### 5.3 Deferred fields found

| field | table | why deferred |
|---|---|---|
| `delta_r_from_pred` | A001 | Precomputed delta; derivation, unit, and double-counting policy need review. |
| `delta_cross_from_pred` | A001 | Precomputed delta; derivation, unit, and double-counting policy need review. |
| `delta_az_from_pred` | A001 | Precomputed angular delta; wrap and derivation need review. |
| `temporal_factor_score` | A001, A005 | Opaque score; origin review needed before scoring use. |
| `pred_status` | A005 | Possible neutralization/status gate; not scoring by default. |
| `pred_cx` | A005 | Could become direct center generator if misused. |
| `pred_cy` | A005 | Could become direct center generator if misused. |
| `pred_w` | A005 | Optical size prior not active. |
| `pred_h` | A005 | Optical size prior not active. |
| `pred_heading_deg` | A005 | Heading convention and source need review. |
| `score` | A005 | Generic score-like field; origin unclear from field inventory alone. |
| `lr_score` | A005 | Score-like field; origin unclear from field inventory alone. |
| `sar_factor_score` | A005 | Score-like field; ownership unclear in current two-factor design. |
| `candidate_source` | A001 | Source-family route is inactive. |
| `candidate_detail` | A001 | Diagnostic provenance; may encode generation logic. |
| `candidate_expansion_state` | A001 | Diagnostic/provenance; not active scoring. |
| `candidate_expansion_reason` | A001 | Diagnostic/provenance; not active scoring. |
| `gm17_temporal_source` | A005 | Temporal source label; not scoring by default. |
| `gm17_temporal_decision` | A005 | Prior decision label; must not copy earlier decision behavior. |
| `gm17_anchor_strength` | A001, A005 | Anchor diagnostic; not active scoring. |
| `gm17_track_size` | A005 | Track diagnostic; transition inactive. |
| `gm17_anchor_n` | A005 | Anchor diagnostic; not active scoring. |
| `n_candidates` | A005 | Candidate-count diagnostic; not active scoring. |

## 6. 人类读者解释

A001 provides the existing SAR candidate boxes. A005 provides a row-level optical temporal soft prediction. The future Line B idea is not to generate new candidates, not to expand the bank, and not to use GT to pick an answer. The intended design question is narrower: among existing GM_RM017 SAR candidate boxes in A001, can a fixed, human-approved geometry reasonableness component and a soft optical temporal consistency component help choose or rank candidates without leaking evaluation fields?

Put another way:

```text
A001 = the menu of existing SAR candidate boxes.
A005 = a soft optical-temporal suggestion about where the target may be.
Line B = compare existing menu items against geometry and soft temporal consistency.
Line B != generate new boxes, train a ranker, or use GT to choose the winner.
```

## 7. 下一步建议

Field inventory result:

- A001/A005 are both GM_RM017-scoped by observed `scene` sample values.
- A001 contains all manifest geometry allowlist fields: `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross`.
- A005 contains all manifest optical temporal fan-polar fields: `pred_r`, `pred_cross`, `pred_az`.
- Shared candidate join-key candidates exist: `target_identity`, `scene`, `sar_frame`, `sar_frame_num`, `gm17_track_id`.
- No forbidden-looking field names were found by the requested scan.
- Several score-like, delta-like, source-like, and decision-like fields are present and must remain deferred until origin review.

Recommended next step if the researcher accepts this field inventory:

```text
write a non-executable combined geometry + temporal design note
```

That note should still remain non-executable. It can define candidate-side geometry component responsibilities, temporal soft-prior comparison responsibilities, missing-prior behavior, invalid-geometry behavior, and conflict flags. It should not run experiments.

If a later review decides that any deferred field should be allowed, revise the manifest first. If any forbidden-looking field appears in a future A001/A005 version, revise the denylist and stop before design proceeds.

Still blocked:

- no experiment;
- no candidate selection;
- no metric computation;
- no threshold tuning;
- no learned weights;
- no calibration;
- no GT join;
- no candidate-bank modification;
- no GM_RM011 or GM_RM019 expansion.
