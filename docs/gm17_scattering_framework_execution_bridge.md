# GM17 Scattering Framework Execution Bridge

Date: 2026-06-29

Status: pre-execution bridge draft

Current branch checked: `research/gm17-dual-bottleneck-synthesis-20260629`

Current committed framework checkpoint checked: `48e9d6f docs: add GM17 scattering-aware candidate state framework`

This document converts the committed GM17 Scattering-Aware Candidate State Inference Framework into a pre-execution diagnostic roadmap and data availability audit. It does not repeat the full theory. It only identifies what can be prepared next before any local diagnostic run is authorized.

No experiment was run. No model was trained. No OOF calibration was performed. No candidate bank was modified. No GM17 mainline selector was modified. No performance conclusion is produced.

Formal Phase5 remains `BLOCKED_FOR_OOF_CALIBRATION`.

## 1. Purpose

This document bridges:

```text
unified diagnostic framework
-> local diagnostic readiness
-> schema/path validation
-> future executable diagnostic scripts
```

It is not:

- an experiment report;
- a proposal generation run;
- a training plan;
- an OOF calibration plan;
- a candidate-bank modification plan;
- a GM17 selector patch;
- a Phase5 approval document.

The immediate question is not "which mechanism improves performance?" The immediate question is:

```text
Which frozen input tables, field layers, and output schemas must be confirmed
before the scattering-aware diagnostic pipeline can be run safely?
```

## 2. Current Committed Baseline

The current framework baseline is a stack of committed documents:

| Document | Role In Baseline |
|---|---|
| `docs/gm17_dual_bottleneck_research_synthesis.md` | Establishes the dual bottleneck: strong coarse fixed-bank coverage, weak high-IoU precision, and structured selection weakness. |
| `docs/gm17_next_diagnostic_experiment_matrix.md` | Defines the diagnostic-only experiment sequence A-F. |
| `docs/gm17_phase4_extension_high_iou_precision_decomposition_spec.md` | Details Experiment A and the center / size / combined / aspect / proxy failure buckets. |
| `docs/gm17_center_size_likelihood_candidate_refinement_spec.md` | Defines center-size likelihood as non-mutating research-understanding refinement over frozen candidates. |
| `docs/gm17_sar_temporal_keyframe_selection_mechanism_spec.md` | Defines SAR aspect sequence, keyframe confidence, local soft anchors, and apparent frame-to-frame consistency. |
| `docs/gm17_scattering_aware_candidate_state_inference_framework_plan.md` | User-provided plan that reframes candidate boxes as frozen hypotheses over latent geometry and scattering support. |
| `docs/gm17_scattering_aware_candidate_state_inference_framework.md` | Unified framework that connects latent vehicle state, SAR scattering support, aspect state, identifiability, uncertainty, and diagnostic pipeline gates. |

Relationship:

```text
dual bottleneck synthesis
  -> diagnostic experiment matrix
  -> high-IoU decomposition spec
  -> center-size likelihood spec
  -> SAR temporal/keyframe mechanism spec
  -> scattering-aware unified framework
  -> this execution bridge
```

This bridge should be treated as the first implementation-adjacent document. It still authorizes only read-only/schema-level preparation.

## 3. Diagnostic Task Graph

The future diagnostic roadmap is a dependency DAG:

```text
A. High-IoU Precision Decomposition
  -> B. Center-Size Likelihood Precision Audit
  -> C. SAR Aspect Descriptor Separability
  -> D. Keyframe Confidence Validity
  -> E. Soft Anchor Propagation Simulation
  -> F. Combined Pipeline Interpretation

A also gates C, because descriptor separability needs post-hoc precision buckets.
B gates D and E, because keyframe confidence should use center-size concentration and agreement.
C gates D and E, because keyframe confidence and soft anchors need descriptor convention clarity.
F depends on A-E.
```

| Task | Depends On | Outputs | Must Not Do |
|---|---|---|---|
| A. High-IoU Precision Decomposition | Frozen candidate/rank output, post-inference audit tables, field layer allowlist. | Schema validation report; target-level decomposition schema; failure bucket table design; readiness decision for B/C. | Do not tune selector thresholds; do not use IoU/center error/oracle during scoring; do not treat `axis_aligned_proxy_iou` as rotated IoU. |
| B. Center-Size Likelihood Precision Audit | A failure buckets; frozen candidate geometry; inference-safe SAR/optical/scene/temporal fields. | Candidate likelihood table schema; center/size/interaction readiness report; missingness map. | Do not move candidate geometry; do not generate candidates; do not train weights; do not feed likelihood into GM17 selector. |
| C. SAR Aspect Descriptor Separability | Frozen candidate windows/crop policy; SAR image or patch source; descriptor convention audit; A post-hoc labels for evaluation only. | Descriptor schema; convention audit; separability audit plan. | Do not use GT/A019/A021/IoU/oracle/center error during descriptor extraction; do not infer heading/orientation from descriptors or AABB proxy. |
| D. Keyframe Confidence Validity | B likelihood concentration; C descriptor clarity; frozen score/rank margin if available. | Keyframe confidence hypothesis schema; entropy/identifiability readiness report. | Do not define keyframes from high score alone or post-hoc correctness; do not use A021 condition labels. |
| E. Soft Anchor Propagation Simulation | D keyframe confidence; C descriptor similarity; apparent frame-to-frame consistency schema. | Local soft-anchor message schema; bounded-window simulation protocol. | Do not hard-lock candidates; do not globally propagate; do not overwrite SAR evidence; do not modify selector output. |
| F. Combined Pipeline Interpretation | A-E frozen diagnostic outputs. | Combined interpretation report; stop/hold/go recommendation. | Do not claim mainline performance; do not approve Phase5; do not calibrate or merge into C3/C4. |

The first executable-preparation target should be A schema validation, not B/C computation.

## 4. Data Availability Audit

Scope of this audit:

- Read committed document paths and script/config path references.
- List files in the current synthesis worktree.
- Check existence for candidate source paths named by manifests, summaries, scripts, and configs.
- Read only one existing CSV header: `output/runtime_v2_full_stream_transfer_opportunity_research_design_2026-04-30/00_tables/source_files_read.csv`.
- Read config text from `configs/phase5B_first_diagnostic_run_config_v0.json` as a config artifact, not as data.

Important caveat:

Most GM17 diagnostic CSV/JSON files referenced by docs and scripts are not present in the current synthesis worktree. They may exist in another local working tree or ignored output directory, but this bridge does not assume that.

| Needed Field / Artifact | Needed For | Candidate Source File | Exists? | Confidence | Notes |
|---|---|---|---|---|---|
| Fixed A001 candidate bank | A/B/C/D/E identity and frozen candidate geometry | `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv` | No | Medium path clue | Path is documented in `gm17_phase4_data_manifest_and_field_gates.md` and inventory docs, but file is absent in this worktree. |
| Candidate-factor joined table A008 | Candidate factors, temporal consistency, diagnostic joins | `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/candidate_refined_factor_inference.csv` | No | Medium path clue | Manifest names it as rich joined table; no header verified. |
| Signed escape posterior A007 | Direction / uncertainty diagnostic fields | `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/signed_escape_posterior_inference.csv` | No | Medium path clue | Path exists only as documentation clue. |
| Optical temporal prior A005 | Optical prior, temporal context, possible shell proxy | `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv` | No | High path clue | Referenced by manifest, inventory, config, and precheck script; file absent here. |
| Selected prediction reference A013 | Post-hoc behavior comparison only | `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/track_viterbi_selected_inference.csv` | No | Medium path clue | Reference-only; must not score candidates. |
| A019 final boxes | Post-inference audit/evaluation | `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv` | No | High path clue | Eval-only. Absence blocks local post-inference audit in this worktree. |
| A021 condition labels | Post-inference condition/truncation/occlusion audit | `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv` | No | High path clue | Eval-only/future-only. Absence blocks grouped audit in this worktree. |
| Minimal pilot ranked candidates | A schema validation, rank/score field inspection | `output/gm17_phase4_minimal_factor_pilot_20260628_110447/pilot_candidates_ranked.csv` | No | High path clue | Script and docs reference it; absent in current worktree. |
| Minimal pilot selected rank1 | A rank1 target-level comparison | `output/gm17_phase4_minimal_factor_pilot_20260628_110447/pilot_selected_rank1.csv` | No | High path clue | Absent in current worktree. |
| Minimal pilot manifest | Boundary/provenance for frozen run | `output/gm17_phase4_minimal_factor_pilot_20260628_110447/pilot_manifest.json` | No | High path clue | Absent; no manifest keys verified. |
| Minimal pilot evaluation summary | Post-inference evaluation summary | `output/gm17_phase4_minimal_factor_pilot_20260628_110447/evaluation_summary.json` | No | High path clue | Absent; do not assume metrics. |
| Minimal pilot per-target evaluation | A failure bucket inputs | `output/gm17_phase4_minimal_factor_pilot_20260628_110447/evaluation_per_target.csv` | No | High path clue | Absent; no columns verified here. |
| Evaluation condition groups | Grouped post-inference audit | `output/gm17_phase4_minimal_factor_pilot_20260628_110447/evaluation_condition_groups.csv` | No | High path clue | Absent. |
| V1 diagnostic summary | Existing post-inference diagnostic context | `output/gm17_phase4_minimal_factor_pilot_v1_diagnostics_20260628_113224/diagnostic_summary.json` | No | Medium path clue | Referenced in memory/docs/scripts; absent. |
| Phase4D candidate pool ceiling | Possible target/frame/track source for later diagnostic proposal route | `output/gm17_phase4D_candidate_pool_ceiling_audit_20260629_001655/candidate_pool_ceiling_per_target.csv` | No | Medium path clue | Referenced by Phase5B docs/config; absent and not current fixed-bank bridge source. |
| Phase5B proposal candidates | Separate generated-proposal diagnostic route | `output/phase5B_first_diagnostic_run_v0_20260629_102746/proposal_candidates.csv` | No | Medium path clue | Docs say it was generated in another run, but file absent here; not part of current fixed-bank bridge unless separately approved. |
| Phase5C metrics summary | Post-hoc evaluation for Phase5B proposals | `output/phase5C_v0_model_diagnostic_audit_20260629_110133/metrics_summary.json` | No | Low path clue | Name searched as requested; absent. |
| Candidate policy summary | Phase5C / proposal-policy audit clue | `output/phase5C_v0_model_diagnostic_audit_20260629_110133/candidate_policy_summary.json` | No | Low path clue | Name searched as requested; absent. |
| SAR display image source policy | C descriptor convention and SAR patch readiness | `D:/profile/research/data/GM_RM017/GM_RM017_SARframes_gray/<sar_frame>.png` | Not checked | Config clue only | External path named in config; this bridge only checked repo/current worktree, not external data tree. |
| Existing SAR crop / patch table | C descriptor extraction input | Not found in repo search | No | Low | No committed crop/patch table was found. |
| Field dictionary | Field layer mapping | `docs/gm17_factor_field_dictionary.md` | Yes | High doc clue | Document declares field classes; not a data table. |
| Phase4 data manifest/gates | Input path and allowlist/denylist | `docs/gm17_phase4_data_manifest_and_field_gates.md` | Yes | High doc clue | Human-review manifest, not an executed input manifest. |
| LineB A001/A005 field inventory | Historical header/field inventory evidence | `docs/gm17_phase4_lineB_A001_A005_field_inventory.md` | Yes | Medium doc clue | Reports prior header/row-count inspection, but current CSV files are absent. |
| Runtime source file inventory CSV | Legacy source inventory, not GM17 diagnostic table | `output/runtime_v2_full_stream_transfer_opportunity_research_design_2026-04-30/00_tables/source_files_read.csv` | Yes | High for its own header | Header read: `source_level,source_path,source_type,reason_read,data_level_relevance,date_read`. Not sufficient for GM17 A-F diagnostics. |
| Phase5B frozen config | Separate diagnostic proposal route configuration | `configs/phase5B_first_diagnostic_run_config_v0.json` | Yes | High config clue | Read as config only. It defines allowed/forbidden fields and image source policy; it does not provide fixed-bank candidate tables. |

Current availability conclusion:

```text
Ready for read-only schema/path audit design.
Not ready for local diagnostic execution from current worktree files alone.
```

## 5. Field Layer Mapping

This mapping uses committed docs, scripts, and config clues. Actual data availability remains unresolved until the source CSV/JSON files are present and headers are verified.

### Inference-Safe / Pre-Eval

| Field | Current Name / Alias | Availability In Current Worktree | Notes |
|---|---|---|---|
| `candidate_id` | `candidate_id` | Documented, data file absent | Declared in field dictionary and A001 inventory; needed for all candidate-level tasks. |
| `target_id` | likely `target_identity` | Documented, data file absent | Use `target_identity` until a formal alias map approves `target_id`. |
| `scene_id` | `scene` | Documented/configured, data file absent | Present in config allowed fields. |
| `track_id` | `gm17_track_id` | Documented, data file absent | Track grouping only; does not activate transition. |
| `frame_id` | `sar_frame_num` or `sar_frame` | Documented/configured, data file absent | Needs frame-order type check. |
| `cx`, `cy`, `w`, `h` | A001 candidate geometry | Documented, data file absent | Candidate-side only. Must not be replaced by `final_*`. |
| `heading` / `theta` | A001 stored candidate metadata | Documented, data file absent | Metadata only; not heading correctness. |
| `candidate_source` | A001 provenance | Documented, data file absent | Grouping/explanation only unless separately audited. |
| rank fields | `pilot_rank`, frozen rank/score fields | Script clue, output file absent | Allowed only if from a completed frozen run. |
| score fields | frozen selector scores | Script/docs clue, output file absent | Do not recompute or tune. |
| optical prior fields | `pred_r`, `pred_cross`, `pred_az`, `pred_cx`, `pred_cy`, `pred_w`, `pred_h` | Config/docs clue, A005 absent | Soft prior only; must not generate or overwrite candidates. |
| SAR image path | gray/pseudocolor path policy | Config clue only | External image path not checked. |

### Diagnostic-Only

| Field | Current Name / Alias | Availability | Notes |
|---|---|---|---|
| `candidate_detail` | A001 provenance detail | Documented, data absent | Explanation only; no scoring shortcut. |
| `candidate_expansion_state` | A001 provenance | Documented, data absent | Diagnostic provenance only. |
| `candidate_expansion_reason` | A001 provenance | Documented, data absent | Diagnostic provenance only. |
| `gm17_anchor_strength` | A001 provenance / anchor clue | Script clue, data absent | Must not choose anchors without separate field audit. |
| `delta_*_from_pred` | candidate-temporal residual fields | Documented, data absent | Deferred until origin review; prefer recompute from approved safe fields if later allowed. |
| SAR descriptor fields | `E_left`, `E_center`, `lr_asymmetry`, etc. | Not found as existing data | Need future extraction after convention audit; not currently available. |
| keyframe confidence | `K_keyframe_confidence` proposed | Not existing | Future diagnostic hypothesis output only. |
| soft anchor messages | `anchor_message_strength` proposed | Not existing | Future simulation output only. |

### Post-Inference Audit

| Field | Current Name / Alias | Availability | Notes |
|---|---|---|---|
| `axis_aligned_proxy_iou` | same | Script/docs clue, eval table absent | AABB proxy only; not rotated IoU. |
| center error | `center_error`, `candidate_center_err_px`, role-prefixed center errors | Script/docs clue, eval table absent | Audit/evaluation only. |
| oracle identity | `oracle_*`, `best_proxy_candidate_id`, `best_center_candidate_id` | Script/docs clue, eval table absent | Audit-only. |
| A019 final boxes | `final_cx`, `final_cy`, `final_w`, `final_h`, `final_heading_deg` | Path clue, file absent | Eval-only; no inference. |
| A021 labels | `condition_type`, `truncation_degree`, `occlusion_degree`, visibility labels | Path clue, file absent | Eval-only/future-only. |
| failure bucket | center-limited / size-limited / combined / aspect / proxy | Proposed output | Assigned only after audit labels join. |

### Forbidden During Scoring

The following are forbidden during scoring, candidate sorting, route selection, threshold choice, anchor selection, missingness policy, training, or factor activation:

- GT;
- IoU;
- `axis_aligned_proxy_iou`;
- oracle labels;
- center error;
- A019 final boxes;
- A021 condition / truncation / occlusion / visibility labels;
- `final_*` fields;
- manual review outcomes;
- high-IoU bins;
- post-hoc failure buckets;
- any field derived from the above.

### Future-Only

| Field / Artifact | Reason |
|---|---|
| rotated IoU | Requires separate rotated-OBB audit. |
| heading / orientation correctness | Cannot be inferred from `axis_aligned_proxy_iou`. |
| long-axis correctness | Requires separate convention and OBB audit. |
| SAR aspect descriptor active factor | Must remain diagnostic until descriptor convention and leakage audit pass. |
| keyframe active anchor | Must remain local soft-anchor simulation; no hard lock. |
| formal Phase5 calibration inputs | Blocked pending OOF calibration governance. |

## 6. First Runnable Diagnostic Candidate

Recommended first preparation target:

```text
1. High-IoU Precision Decomposition schema validation
```

Rationale:

- It is upstream of all later tasks.
- It can be performed as read-only/schema-only validation before any diagnostic computation.
- It establishes whether `candidate_id`, target/frame/track keys, frozen rank fields, candidate geometry, and post-inference audit fields can be joined safely.
- It can confirm whether current outputs support center-limited / size-limited / combined bucket assignment.

Current readiness:

| Candidate | Readiness | Reason |
|---|---|---|
| High-IoU Precision Decomposition schema validation | GO for path/schema audit design; HOLD for execution | Required files are named but absent in current worktree. |
| Center-Size Likelihood input readiness | HOLD | Needs A001 candidate geometry and SAR patch/image source convention; current candidate tables absent. |
| SAR descriptor extraction convention audit | HOLD | Needs SAR image/crop source and candidate windows; current repo has config path policy but no local image/crop table verified. |

Do not start B or C before A confirms actual source paths, headers, and field layers.

## 7. Script Skeleton Plan

No script files are generated by this document. The following are skeleton plans only.

### `tools/diagnostics/audit_high_iou_precision_decomposition.py`

Goal:

Validate whether frozen candidate/rank outputs and post-inference audit outputs can support Experiment A without leakage.

Inputs:

- frozen ranked candidate table;
- frozen selected rank1 table, if available;
- per-target post-inference evaluation table;
- optional evaluation summary JSON;
- optional condition-group table for post-hoc grouping only.

Required columns:

- `candidate_id`;
- `target_identity` or approved `target_id`;
- `scene`;
- `sar_frame_num` or approved `frame_id`;
- `gm17_track_id` or approved `track_id`;
- `cx`, `cy`, `w`, `h`;
- frozen `rank` / `score` fields if available;
- `axis_aligned_proxy_iou` only in audit table;
- `center_error` only in audit table;
- oracle/best candidate ids only in audit table.

Forbidden columns during scoring:

- GT;
- A019;
- A021;
- `axis_aligned_proxy_iou`;
- IoU;
- oracle;
- center error;
- condition/truncation/occlusion;
- final-box fields.

Outputs:

- schema readiness report;
- field layer mapping report;
- join-key availability table;
- proposed output schema for target-level summary, failure bucket table, and manual review list.

Stop conditions:

- required source table missing;
- join keys ambiguous;
- audit fields present in inference table;
- `axis_aligned_proxy_iou` treated as rotated IoU;
- center/size buckets require unavailable final-box fields during scoring.

### `tools/diagnostics/audit_center_size_likelihood_readiness.py`

Goal:

Validate whether center-size likelihood can be computed from inference-safe candidate geometry and SAR/optical/scene/temporal context.

Inputs:

- frozen A001 candidate table;
- approved optical temporal prior table, if available;
- SAR image/crop source convention;
- optional frozen rank output for comparison;
- no GT/A019/A021/IoU/oracle/center-error inputs.

Required columns:

- `candidate_id`;
- `target_identity`;
- `scene`;
- `sar_frame_num`;
- `gm17_track_id`;
- `cx`, `cy`, `w`, `h`;
- candidate crop bounds or derivable crop policy;
- optional `candidate_source` for grouping only;
- optional `pred_r`, `pred_cross`, `pred_az` as soft prior;
- descriptor availability flags.

Forbidden columns during scoring:

- GT;
- A019 final boxes;
- A021 labels;
- IoU;
- `axis_aligned_proxy_iou`;
- center error;
- oracle identity;
- manual review.

Outputs:

- likelihood input readiness table;
- missingness map;
- component feasibility report for `L_center`, `L_size`, `L_interaction`, `L_optical_prior`, `L_temporal_context`, `L_missingness`;
- HOLD list for unavailable descriptor/crop fields.

Stop conditions:

- candidate geometry absent;
- crop convention depends on final boxes;
- A005 prior is used to generate candidates rather than score existing ones;
- likelihood weights require audit labels;
- output is proposed as active selector input.

### `tools/diagnostics/audit_sar_descriptor_convention.py`

Goal:

Validate whether SAR aspect descriptors can be extracted from frozen candidate-local patches under a stable coordinate convention.

Inputs:

- frozen candidate geometry;
- SAR image source or patch source;
- declared crop policy;
- declared left / center / right local coordinate convention;
- no post-inference labels during descriptor extraction.

Required columns / inputs:

- `candidate_id`;
- `target_identity`;
- `scene`;
- `sar_frame_num`;
- `gm17_track_id`;
- `cx`, `cy`, `w`, `h`;
- image path or patch path;
- image width/height or patch bounds;
- crop origin if crop-local coordinates are used.

Forbidden columns during descriptor extraction:

- GT;
- A019;
- A021;
- IoU;
- `axis_aligned_proxy_iou`;
- oracle labels;
- center error;
- condition/truncation/occlusion;
- manual review.

Outputs:

- descriptor convention readiness report;
- descriptor schema for `E_left`, `E_center`, `E_right`, `lr_asymmetry`, `center_dominance`, `mirror_symmetry`, `scatter_centroid_dx`, `scatter_centroid_dy`, `scatter_compactness`, `peak_count`, `local_background_contrast`;
- missingness / boundary-touching flags;
- HOLD/GO decision for Experiment C.

Stop conditions:

- image source absent;
- crop convention is ambiguous;
- descriptor signs imply heading/orientation claims;
- descriptor extraction requires final boxes or A021 labels;
- thresholds are tuned from post-hoc labels.

## 8. Stop / Hold / Go Decision

### GO

The following can continue as read-only/schema audit work:

- locate actual current source tables for A001, A005, A019, A021, pilot ranked outputs, and per-target evaluation outputs;
- read only headers and top-level JSON keys after paths are found;
- build a field-origin map for Experiment A;
- draft output schemas for target-level summary, failure bucket table, and manual review case list.

### HOLD

Hold before execution if:

- A001 candidate bank file is absent or hash/version is not accepted;
- pilot ranked/evaluation outputs are absent;
- `target_identity` / `target_id`, `sar_frame_num` / `frame_id`, or `gm17_track_id` / `track_id` mappings are unresolved;
- SAR image/crop source is only an external path policy and not verified;
- descriptor coordinate convention is not declared;
- A019/A021 files are missing for post-inference audit;
- `candidate_source` or provenance fields are being used as ranking shortcuts;
- Phase5B generated-proposal outputs are mixed into fixed-bank diagnostics without explicit approval.

### STOP

Stop immediately if:

- any GT / IoU / oracle / center error / A019 / A021 / condition / truncation / occlusion / final-box field is used during scoring;
- `axis_aligned_proxy_iou` is treated as rotated IoU;
- heading/orientation/long-axis conclusions are inferred from AABB proxy;
- candidate geometry is moved;
- candidate bank is modified;
- GM17 selector is modified;
- a diagnostic factor is written as an active factor;
- keyframe anchors hard-lock candidates or propagate globally;
- model training starts;
- OOF calibration starts;
- a mainline performance conclusion is stated.

Current decision:

```text
GO: read-only source-path and schema validation for Experiment A.
HOLD: any local diagnostic execution until actual source CSV/JSON files are present and headers are verified.
STOP: any selector/candidate-bank/Phase5/calibration/training action.
```

## 9. Next Actions

1. Locate or provide the actual current source paths for A001 candidate bank, frozen ranked output, and per-target audit output; then read headers only.
2. Create a schema-only allowlist/denylist for Experiment A, including canonical aliases for `target_identity`, `sar_frame_num`, and `gm17_track_id`.
3. After Experiment A schema readiness passes, decide whether B should start with center-size likelihood readiness or C should first audit SAR descriptor/crop convention.
