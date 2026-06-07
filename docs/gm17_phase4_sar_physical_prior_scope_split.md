# GM17 Phase4 SAR Physical Prior Scope Split

Status: Phase4 research-scope correction and planning note for human review. This document does not authorize experiments, inference runs, performance metrics, training, calibration, learned weights, threshold tuning, data-file modification, candidate-bank generation or modification, algorithm-code modification, executable scaffold creation, staging, commit, or push.

GM17 remains a staged evidence and feature/behavior source, not the final model template. A candidate bank is an experimental container for freezing candidate generation; it is not the research goal. A001 remains GM_RM017-only for the current candidate-level pilot, but that limitation must not be applied to every SAR-domain physical prior audit.

## 1. Purpose

This document separates two Phase4 research scopes:

1. all-GT-covered SAR-domain physical prior audit;
2. GM_RM017-only optical-to-SAR candidate-level pilot.

This is a scope correction and research planning note only. It clarifies which data layer supports which scientific question, so the project does not mistake candidate-bank coverage for physical-prior audit coverage.

The correction is:

```text
A001 is GM_RM017-only for the current candidate-level optical-transfer pilot.
That does not make all Phase4 SAR-domain physical prior audits GM_RM017-only.
```

## 2. Why The Split Is Necessary

A001 `candidate_bank_inference.csv` covers GM_RM017 only. Therefore the current candidate-level optical-to-SAR pilot, which depends on A001 and the current temporal-prior chain, is GM_RM017-only.

Manual GT covers GM_RM011, GM_RM017, and GM_RM019. Therefore SAR-domain physical prior audit should not be restricted to GM_RM017 when the research question is physical geometry, scale, heading, visibility, truncation, occlusion, boundary behavior, or near-field-related failure modes.

Physical priors need diversity and generality. A physical scale prior or SAR geometry reliability review should not be inferred from one candidate-bank-covered scene if broader GT-covered SAR scenes exist.

Candidate-bank coverage and GT coverage are different data layers:

- candidate-bank coverage defines where current candidate-level selection can be piloted;
- GT coverage defines where physical-prior distributions, condition groupings, and post-inference evaluation can be reviewed;
- neither layer automatically authorizes learned weights, calibration, candidate generation, or inference scoring with GT.

## 3. Data Layer Distinction

### Raw SAR/optical scene layer

This layer contains the raw scenes for:

- GM_RM011;
- GM_RM017;
- GM_RM019.

It supports scene diversity review, SAR/optical path provenance, SAR frame coverage checks, visual failure-mode review, and future physical-prior audit planning. It does not directly score candidates in fixed-bank Phase4.

### Manual GT / condition layer

This layer contains:

- A019 `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv`;
- A021 `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv`.

A019 is manual GT / final box material. A021 is visibility, truncation, and occlusion condition material. These tables support SAR-domain physical prior audit, condition distribution review, boundary/failure-mode review, and post-inference evaluation.

They are eval-only for candidate selection. They must not enter inference scoring, candidate selection, threshold tuning, learned weights, missing-value policy tuning, or candidate-bank generation.

### Candidate-level GM17 pilot layer

This layer contains:

- A001 `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv`;
- A005 `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv`;
- A007 `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/signed_escape_posterior_inference.csv`;
- A008 `output/clean_no_gt_localizer_2026-05-31_gm17_signed_escape_posterior/candidate_refined_factor_inference.csv`;
- A013 `output/clean_no_gt_localizer_2026-06-01_gm17_track_level_viterbi_selector/track_viterbi_selected_inference.csv`.

A001/A005 support the current GM_RM017-only geometry + optical_temporal candidate pilot after human approval and field gates. A007/A008 support future direction/source and diagnostic reviews only after ownership gates. A013 is selected-reference behavior only and must not become a scoring input.

## 4. Line A: SAR-Domain Physical Prior Audit

Line A is the all-GT-covered SAR-domain physical prior audit.

Scope:

- GM_RM011;
- GM_RM017;
- GM_RM019;
- all GT-covered samples, including samples outside masks if present.

Purpose:

- audit SAR vehicle physical geometry;
- audit OBB size and aspect ratio;
- audit heading distribution;
- audit SAR frame and scene diversity;
- audit truncation, occlusion, and visibility condition distribution;
- identify mask-outside or boundary cases as evidence for failure modes;
- support future partial visibility and near-field modeling.

Relevant factors and routes:

- `geometry_factor` physical scale prior;
- `sar_structure_factor` diagnostic prior;
- `uncertainty_factor` diagnostic prior;
- `visibility_factor` future route;
- `missing_extent_factor` future route;
- `visible_full_center_offset_factor` future route;
- near-field future route.

GT can support physical-prior audit and post-inference evaluation, but GT must not enter inference or candidate scoring. A physical prior audit can summarize GT geometry and condition coverage; it cannot tune thresholds from performance, choose candidates, or activate scoring factors by hindsight.

Line A is scientific-prior focused. It asks what SAR vehicle geometry, visibility, truncation, occlusion, boundary, and near-field-related phenomena exist in the GT-covered SAR domain.

## 5. Line B: GM_RM017-Only Optical-To-SAR Candidate Pilot

Line B is the GM_RM017-only optical-to-SAR candidate-level pilot.

Scope:

- GM_RM017-only candidate-level pilot using A001/A005 and approved allowlists.

Purpose:

- test candidate-level `geometry_factor` + `optical_temporal_factor` fixed-prior design;
- keep candidate generation frozen;
- compare existing SAR candidates against optical temporal prediction;
- preserve inference/evaluation separation;
- avoid all-scene claims.

Relevant factors:

- `geometry_factor` candidate-level design;
- `optical_temporal_factor` soft-prior design;
- later `direction_factor` / controlled non-visible `source_factor` ownership;
- later `transition_factor` only after candidate-level factors are stable.

This line cannot claim all-scene validation until GM_RM011 and GM_RM019 candidate banks / temporal priors are found or generated under an approved process. Candidate generation for GM_RM011 and GM_RM019 is a separate future route, not an implicit consequence of this scope split.

Line B is candidate-level pilot focused. It asks whether fixed, audited candidate-level factors can select among existing GM_RM017 candidates without changing the candidate bank or leaking eval-only labels.

## 6. Factor Scope Matrix

| factor_or_route | SAR-domain all-GT physical audit? | GM_RM017 candidate-level pilot? | required data layer | current status | notes |
|---|---|---|---|---|---|
| `geometry_factor` | yes | yes | Line A uses A019/A021 and raw scene context for physical scale/heading/shape audit; Line B uses A001 candidate geometry. | dual-scope | Physical-prior audit can use all GT-covered scenes; candidate scoring pilot remains GM_RM017-only. |
| `optical_temporal_factor` | no, except background context for transfer questions | yes | A005 temporal prior plus A001 candidate rows. | GM_RM017-only pilot | Current temporal/candidate chain is GM_RM017-only; not an all-GT SAR physical prior. |
| `direction_factor` | limited diagnostic planning only | future GM_RM017 candidate-level after mapping | A007/A008 for candidate pilot; GT heading may inform physical audit only as eval/analysis material. | ready_after_mapping | Do not activate in the current geometry + temporal pilot. |
| controlled non-visible `source_factor` | no active all-GT physical audit | future GM_RM017 candidate-level after source normalization | A001/A008 candidate source fields. | ready_after_mapping | Source-family provenance depends on candidate-generation layer, not GT coverage alone. |
| `transition_factor` | no active all-GT physical audit | future GM_RM017 candidate-level after node factors stable | A001/A008 track/frame/candidate state; A013 reference-only after independent output. | ready_after_mapping | Edge continuity should wait until candidate-level factors are stable. |
| `sar_structure_factor` | yes, diagnostic | no active pilot scoring | All-GT SAR/GT review, A008/A017 diagnostic context where available. | diagnostic_only | All-scene SAR physical audit can review support/structure questions without scoring candidates. |
| `uncertainty_factor` | yes, diagnostic | no active pilot scoring | A021 conditions, all-GT failure/boundary review, A007/A008 ambiguity diagnostics where available. | diagnostic_only | Ambiguity/artifact uncertainty remains diagnostic and must not copy B patch behavior. |
| `final_arbitration_factor` | no active physical prior | no | A013/A018 selected/gate/patch references only. | blocked | Final action behavior is patch-risk material, not physical prior or scoring evidence. |
| `visibility_factor` | yes, future-route audit | no active pilot scoring | A021 condition labels, visible-support diagnostics if separately reviewed, all-GT failure cases. | future_only | Visibility can be audited across all GT-covered scenes but cannot generate full center. |
| `missing_extent_factor` | yes, future-route audit | no active pilot scoring | A021 truncation/occlusion labels and all-GT boundary cases. | future_only | Missing extent remains future partial-visibility schema work. |
| `visible_full_center_offset_factor` | yes, future-route audit | no active pilot scoring | All-GT manual boxes plus future visible-support/offset schema. | future_only | Important for preventing visible-center misuse; not active candidate scoring. |
| near-field future route | yes, future-route audit | no active pilot scoring | All-GT scene/condition/boundary review plus future geometry-regime indicators. | future_only | Near-field is geometry-regime/reliability work; it cannot modify candidate bank or replace selector. |

Main conclusion: `geometry_factor` has both a broad SAR-domain physical-prior audit surface and a narrow GM_RM017 candidate-pilot surface. Most optical-transfer and candidate-selection factors depend on candidate-bank/temporal-prior coverage and therefore remain GM_RM017-only until broader candidate layers exist.

## 7. What GT May And May Not Do

Allowed GT uses:

- physical size distribution audit;
- heading distribution audit;
- aspect ratio analysis;
- visibility/truncation/occlusion grouping;
- mask coverage and boundary-case review;
- SAR frame and scene diversity review;
- failure-mode taxonomy planning;
- post-inference evaluation.

Forbidden GT uses:

- inference scoring;
- candidate selection;
- threshold tuning;
- learned weight fitting;
- calibration;
- missing-value policy tuning;
- factor activation decision based on performance;
- oracle candidate selection;
- using IoU/center error before inference;
- candidate-bank generation or expansion decisions by hindsight.

GT may describe the SAR physical domain. It must not become an inference feature, hidden optimizer, candidate selector, or calibration source in Phase4 fixed-prior work.

## 8. Implications For Current Combined Geometry + Optical Temporal Design

The combined geometry + optical_temporal manifest gate remains valid for the GM_RM017-only candidate pilot. Its A001/A005 dependency and allowlist/denylist boundaries are still correct for Line B.

`geometry_factor` also has a broader SAR-domain physical prior audit surface using all GT-covered scenes. That broader surface should audit physical size, aspect ratio, heading, condition groups, boundary cases, and future visibility/near-field routes. This broader audit does not make GT an inference input and does not approve all-scene candidate-level execution.

`optical_temporal_factor` remains GM_RM017-only for now because the current temporal/candidate chain is GM_RM017-only. Future all-scene optical-transfer validation requires GM_RM011 and GM_RM019 candidate and temporal-prior coverage, or a separately approved candidate-generation and temporal-prior process.

The corrected interpretation is:

```text
Line A: all GT-covered scenes can support SAR-domain physical prior audit.
Line B: current optical-to-SAR candidate pilot remains GM_RM017-only.
```

## 9. Recommended Next Workstreams

### Workstream A

Create a SAR-domain physical prior audit plan using all GT-covered samples.

This should be non-inference and should focus on:

- physical plausibility;
- scale;
- aspect ratio;
- heading;
- SAR scene/frame coverage;
- visibility/truncation/occlusion condition coverage;
- mask-outside and boundary cases;
- failure-mode coverage;
- future partial visibility and near-field route requirements.

Workstream A is scientific-prior focused. It asks what physical priors the SAR-domain evidence can support across all GT-covered scenes.

### Workstream B

Continue GM_RM017-only geometry + optical_temporal pilot preparation through non-executable manifest/allowlist/denylist templates.

This should preserve:

- A001 hash and scope gate;
- A005 temporal-prior gate;
- geometry and optical_temporal field ownership;
- eval-only denylist;
- diagnostic/blocked field denylist;
- no candidate-bank modification;
- no experiment execution.

Workstream B is candidate-level pilot focused. It asks whether the current GM_RM017 candidate/temporal chain can support a fixed-prior pilot over existing SAR candidates.

## 10. Human Review Questions

- Should all GM_RM011/GM_RM017/GM_RM019 GT-covered samples define the SAR-domain physical prior scope?
- Should GT outside masks be retained as boundary/failure-mode evidence?
- Which physical quantities should be audited first: `w`/`h`, aspect ratio, heading, center location, mask coverage, truncation/occlusion, or near-field indicators?
- Should the GM_RM017 candidate pilot proceed in parallel with all-GT SAR physical prior audit?
- Is GM_RM011/GM_RM019 candidate generation a separate future route?

## 11. Recommended Next Round

Preferred next round:

```text
create SAR-domain physical prior audit plan over all GT-covered samples
```

Reason: the scope correction makes it important to define Line A cleanly before future work accidentally treats GM_RM017 candidate-bank coverage as the whole SAR physical domain.

Alternative next round:

```text
create non-executable YAML manifest/allowlist/denylist templates for GM_RM017-only geometry + optical_temporal pilot
```

Use the alternative if the researcher wants to continue Line B pilot preparation first.

Do not recommend experiments yet.
