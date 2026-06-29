# Phase5B Literature-Informed Pre-Implementation Review

Date: 2026-06-29

## 1. Purpose

This document is a documentation-only, literature-informed design review for Phase5B.

It reviews the first diagnostic SAR proposal direction before any implementation. It uses literature and local project evidence to decide whether the current Phase5B first diagnostic run specification is too narrow, too broad, or missing a key route.

This document does not:

- implement proposals;
- generate proposals;
- add experiments;
- tune thresholds;
- train models;
- change C3/C4;
- change A001/A005/A019/A021;
- select a final algorithm.

The goal is to make the pre-implementation route choice better grounded. It is not to turn a literature method into the final answer.

## 2. Current Project Position

The project has been realigned away from fixed A001 candidate-bank selection and toward optical-conditioned SAR state inference.

The current mainline is:

```text
optical target state
  + temporal prior
  + scene geometry
  + SAR image evidence
      -> SAR latent vehicle state
      -> proposal / particle / candidate nodes
      -> factor graph inference
      -> localization output
```

The realignment memo fixes the main correction: A001 C3/C4 are selection-layer diagnostics over an externally supplied bank, not a complete optical-to-SAR migration model.

Phase5A defines the SAR latent vehicle state as including at least:

- `cx`, `cy`;
- `w`, `h`, or another extent state;
- `theta` / long-axis state;
- range / azimuth / cross state;
- visibility state;
- uncertainty state;
- multi-hypothesis state.

Phase5B design-space protocol fixes the boundary:

- proposal rows represent SAR latent vehicle-state hypotheses;
- proposal rows are not A001 rows;
- `proposal_id` is not `candidate_id`;
- A019/A021/GT/oracle/panel review cannot enter proposal generation or inference;
- generated proposals must remain separate from active C3/C4.

The current Phase5B first diagnostic run spec allows three routes:

- Route A: shell-grid / multi-scale sampling;
- Route B: local energy / contrast peak proposals;
- Route C: simple connected-component diagnostic.

The current problem is not:

- fixed A001 row selection;
- C3/C4 tuning;
- v3 rule tuning;
- rotated OBB metric chasing;
- heading convention deep dive.

The current problem is:

- how an optical-conditioned shell should constrain SAR search;
- how SAR image evidence inside that shell can generate or support latent vehicle-state hypotheses;
- how proposals can become future factor graph nodes without becoming final results or active C3/C4 inputs.

## 3. Literature Map

### 3.1 Optical-SAR / Cross-Modal Registration

Main idea:

- Optical-SAR registration literature treats optical and SAR imagery as multimodal data with nonlinear radiometric differences, speckle, structural mismatch, and possible geometry differences.
- Mutual-information approaches can match modalities without direct intensity equality [Suri and Reinartz, 2010].
- Feature/structure approaches such as HOPC, SAR-SIFT, and RIFT attempt to build descriptors that are more stable under nonlinear radiation differences and SAR speckle [Ye et al., 2017; Dellinger et al., 2015; Li et al., 2020].
- Recent surveys separate intensity-based, handcrafted feature-based, and learning-based SAR-optical registration routes and note that direct optical/SAR intensity matching is fragile [Sommervold et al., 2023].

Implication for this project:

- Optical should provide a prior or search shell, not the final SAR box.
- Optical-derived center/extent/pose should remain uncertain because optical and SAR support do not correspond one-to-one.
- Registration ideas motivate shell construction and cross-modal uncertainty handling, not direct use of optical boxes as SAR labels.

Risk for this project:

- A full registration method could become a separate research direction and distract from the first Phase5B diagnostic.
- Feature matching methods often assume broader image-pair registration, while Phase5B needs target-level proposal hypotheses inside an already constrained shell.
- Learning-based registration is not appropriate now because training/calibration is explicitly held.

First-round suitability:

- Use registration literature as design justification for optical-as-prior.
- Do not implement registration in the first diagnostic run.

### 3.2 SAR Vehicle / Object Detection

Main idea:

- SAR images contain speckle, clutter, scattering-center effects, shadow/layover ambiguity, and target signatures that can vary with viewing geometry [Goodman, 1976; Gao et al., 2009].
- Public SAR vehicle work often relies on MSTAR chips; official MSTAR data are target chips and clutter collections, not a large-scene vehicle-localization benchmark [AFRL, accessed 2026-06-29].
- Recent SAR vehicle detection datasets highlight that vehicle detection in large SAR scenes remains difficult because vehicle datasets are scarce, backgrounds are complex, and MSTAR-style chips lack full scene context [Liu et al., 2023].

Implication for this project:

- Local energy and contrast are reasonable first diagnostic cues, but a bright point is not automatically the vehicle center.
- Connected components are reasonable for visible support, but a component bbox is not automatically the full vehicle extent.
- Display-image diagnostics can be useful, but they must be labeled as display/pseudocolor-risk unless raw SAR source and scaling are audited.

Risk for this project:

- SAR evidence can support center/extent hypotheses, but it can also lock onto clutter, shadow, sidelobes, or partial support.
- A learned SAR detector would require training and benchmark decisions that are outside Phase5B.

First-round suitability:

- Route B and Route C are justified as diagnostic image-derived proposal routes.
- They should produce hypotheses and provenance, not final detections.

### 3.3 Classical Region Proposal / Object Proposal

Main idea:

- Classical proposal methods intentionally separate candidate generation from final recognition. Sliding windows and multi-scale sampling provide coverage baselines; Selective Search and objectness methods use segmentation, grouping, or scoring to improve proposal efficiency [Uijlings et al., 2013; Alexe et al., 2012].
- Edge Boxes shows that structural cues can generate proposal boxes without a trained class-specific detector [Zitnick and Dollar, 2014].
- Simple thresholding and connected components are classical image-region mechanisms but are sensitive to threshold choices [Otsu, 1979].

Implication for this project:

- Route A is valid as a coverage baseline because it tests shell support independent of A001.
- Route C is valid as a visible-support diagnostic, but threshold family and component-size policy must be predeclared.
- Proposal count, coverage, and oracle ceiling must be reported together. A dense proposal set can have a high ceiling without being a useful inference method.

Risk for this project:

- Proposal ceiling is not active inference performance.
- Sliding-window coverage can become brute-force search if proposal density is not capped and reported.
- Component proposals can become hidden threshold tuning if evaluation metrics are used to choose thresholds.

First-round suitability:

- Route A is the safest baseline if shell source is accepted.
- Route C is suitable only with a predeclared threshold family and provenance.

### 3.4 Bayesian Filtering / Multi-Hypothesis State Estimation

Main idea:

- Particle filters represent posterior uncertainty with samples/hypotheses rather than forcing a single state early [Gordon et al., 1993; Arulampalam et al., 2002].
- Multiple-hypothesis tracking explicitly keeps several candidate association/state explanations under clutter and missed detections [Reid, 1979].

Implication for this project:

- A Phase5B proposal is best interpreted as a latent state hypothesis, not as a final selected candidate.
- Temporal prior should be soft. It should constrain plausible support, but SAR observation should still decide precise localization inside the shell.
- Multi-hypothesis output is a feature, not a defect, for ambiguous SAR crops.

Risk for this project:

- If Phase5B collapses proposals to rank1 too early, it repeats the fixed-bank selector framing.
- If temporal prior dominates, the run becomes optical/temporal shell evaluation rather than SAR observation.

First-round suitability:

- Support preserving route-wise proposal sets and uncertainty flags.
- Do not run a tracker or particle filter in the first diagnostic.

### 3.5 Factor Graph / Probabilistic Graphical Model

Main idea:

- Factor graphs represent variables and factors separately, allowing priors, observations, and constraints to be combined through an explicit graph structure [Kschischang et al., 2001; Dellaert, 2012].
- In robotics/state estimation, factor graphs are used to combine motion, observation, and geometry evidence into state estimates [Dellaert, 2012; Dellaert and Kaess, 2017].

Implication for this project:

- Generated proposal nodes and fixed A001 candidate nodes are both hypothesis carriers.
- The research object is the SAR latent vehicle state, not the row id of the carrier.
- Phase5B should output proposal nodes that a later factor graph could consume, while leaving Phase5D inactive until approved.

Risk for this project:

- A hybrid proposal route can silently become a ranker if it starts optimizing scores before the proposal ceiling is audited.
- C3/C4 integration would erase the diagnostic-only boundary.

First-round suitability:

- Define proposal schema and provenance now.
- Do not run a factor graph over generated proposals in the first diagnostic.

### 3.6 SAR Local Structure / Ridge / Long-Axis Evidence

Main idea:

- Edge, ridge, vesselness, and structure-tensor methods use elongated or oriented local support to infer structural direction [Canny, 1986; Frangi et al., 1998].
- In SAR, long-axis or ridge cues may be valuable but are affected by speckle, clutter, view angle, shadow, and partial visibility.

Implication for this project:

- A ridge / long-axis route is scientifically justified because A001 GM_RM017 heading is a fixed two-value scene grid `[0, 175]`, not SAR-derived orientation.
- However, Phase4D geometry add-on already showed that heading convention and GT rotated OBB convention are not fully audited.
- A first round should stabilize center/extent proposal behavior before claiming orientation capacity.

Risk for this project:

- Ridge cues can overfit panel perception.
- Long-axis detection can be confused by display artifacts, partial support, and convention errors.
- It can prematurely imply rotated OBB correctness.

First-round suitability:

- Hold Route E for later.
- Re-enable only after center/extent proposal baselines and image-source conventions are stable.

## 4. Assessment Of Current Phase5B First Diagnostic Run Spec

### 4.1 Are The Three Allowed Routes Reasonable?

Yes, with one readiness caveat.

Route A, shell-grid / multi-scale sampling:

- reasonable as a shell coverage baseline;
- best at answering whether the search shell is capable of covering target support;
- blocked or partial until shell/proxy-shell source is accepted.

Route B, local energy / contrast peaks:

- reasonable as the first SAR-observation route;
- supported by SAR target detection literature and local Phase4 structure audits;
- must not equate peak with vehicle center.

Route C, simple connected components:

- reasonable as a visible-support route;
- useful for center/extent hypotheses and partial-support diagnostics;
- must declare threshold family and component-size policy before any run.

### 4.2 Is A Key First-Round Route Missing?

Possibly, but it should be optional and readiness-gated.

Route D, radial / range-profile support, is a plausible optional first-round route because:

- SAR localization is strongly tied to range geometry;
- local project artifacts already contain inference-side range/ray profile outputs, such as `gm17_ray_profile_peaks_inference.csv`, `gm17_range_posterior_modes_inference.csv`, and `gm17_wedge_profile_modes_inference.csv`;
- Phase5A explicitly includes range / azimuth / cross state.

However, Route D should not be part of the default first diagnostic run until:

- fan/range convention is explicitly identified;
- the shell/proxy shell source is accepted;
- the route can output center/band hypotheses without borrowing A019/A021/oracle information;
- route provenance separates range profile evidence from temporal prior and A001-derived candidate generation.

Decision:

- Add Route D as an optional diagnostic-only route in the review, not as a default first-round route.
- Recommended status: PARTIAL / optional if convention readiness is approved; otherwise second round.

### 4.3 Are The Held Routes Reasonable?

Yes.

Held routes:

- ridge / long-axis;
- learned model;
- factor graph over generated proposals;
- active C3/C4 integration;
- scoring-weight optimization;
- threshold tuning.

The hold is justified:

- ridge / long-axis depends on orientation conventions and should follow center/extent baselines;
- learned models violate the current hold on training/calibration;
- factor graph over generated proposals belongs to Phase5D after proposal ceiling is known;
- C3/C4 integration would turn diagnostic proposals into active inference;
- score/threshold tuning from evaluation metrics would leak Phase5C back into Phase5B.

### 4.4 Is The First-Round Objective Correct?

Yes.

The first round should not pursue rank1 improvement.

It should answer:

- shell coverage;
- SAR evidence proposal capacity;
- proposal-vs-A001 ceiling difference;
- outside-A001 hypotheses;
- partial visibility / clutter / fan-edge state-model needs.

This objective is consistent with both object proposal literature and probabilistic state-estimation literature: first establish the hypothesis space and diagnostic ceiling, then decide whether active inference is justified.

## 5. Literature-Informed Route Review

### Route A: Shell-Grid / Multi-Scale Sampling

Literature motivation:

- Sliding windows and multi-scale proposal sampling are classical coverage baselines.
- Object proposal literature separates proposal coverage from final recognition [Uijlings et al., 2013; Alexe et al., 2012].

Why useful as coverage baseline:

- tests whether the shell itself can contain plausible SAR center/extent hypotheses;
- independent of A001 candidate enumeration;
- gives a denominator for proposal ceiling and proposal density.

What it can prove:

- whether a predeclared shell/proxy shell has enough spatial support;
- whether the proposal count required for coverage is reasonable;
- whether A001 ceiling and shell ceiling differ.

What it cannot prove:

- SAR image evidence quality;
- final localization performance;
- orientation correctness;
- active ranker quality.

Risks:

- dense brute-force behavior;
- high oracle ceiling driven by proposal count;
- shell proxy may be A001-biased if built from A001 candidate envelope.

Recommended first-round status:

- KEEP as default, but only after shell/proxy-shell source is accepted.

Required input readiness:

- frozen target set;
- shell source or proxy shell;
- crop/support bounds;
- scale and offset grid declared before run;
- maximum proposals per target declared.

### Route B: Local Energy / Contrast Peak Proposals

Literature motivation:

- SAR detection commonly starts from local intensity, clutter statistics, and CFAR-style contrast reasoning [Gao et al., 2009].
- Speckle and clutter make raw intensity unreliable if treated as a final detector [Goodman, 1976].

SAR-specific justification:

- SAR vehicles may produce bright scattering support;
- local contrast can help distinguish target-like support from local background;
- project Phase4 structure audits found `box_to_background_ratio`, `inside_energy_fraction`, and `optional_local_contrast` promising as diagnostic-only features on the 205-target audit.

Why it may help center hypothesis:

- it can find image-supported centers inside the shell rather than relying on A001 centers;
- it can expose cases where A001 center coverage and local SAR support disagree.

Why energy peak is not necessarily vehicle center:

- bright scattering centers can be off-center;
- partial visibility can move energy toward one visible part;
- clutter and sidelobes can dominate local peaks;
- display/pseudocolor scaling can alter apparent contrast.

Risks:

- clutter peaks;
- display-image risk;
- no raw SAR source confirmed;
- hidden threshold tuning if peak count or peak threshold is selected from evaluation results.

Recommended first-round status:

- KEEP as default diagnostic route.

Required input readiness:

- SAR image source id;
- crop policy;
- local background policy;
- energy peak count;
- support-mask policy;
- image-type label: display/pseudocolor vs grayscale/raw.

### Route C: Simple Connected-Component Diagnostic

Literature motivation:

- Connected components and thresholding are simple region proposal mechanisms.
- Otsu thresholding is a classical way to define threshold families, but SAR clutter makes threshold-only segmentation fragile [Otsu, 1979; Goodman, 1976].

Why component proposal may help extent/visible support:

- components can expose visible SAR support that is not centered on A001;
- component bbox/centroid can provide center and AABB extent hypotheses;
- boundary-touching components can flag fan-edge or partial-support risk.

Why component bbox may not equal full vehicle:

- component may represent only a scattering part;
- vehicle support may fragment into multiple components;
- clutter may merge with the target;
- thresholding may clip low-intensity but valid vehicle support.

Risks:

- threshold sensitivity;
- component merge/split instability;
- display-image scaling;
- partial vehicle support mistaken for full extent.

Recommended first-round status:

- KEEP as default diagnostic route, with conservative wording.

Required input readiness:

- threshold family declared before run;
- min/max component size declared before run;
- boundary-touching policy;
- duplicate merge policy;
- diagnostic uncertainty flags.

### Route D: Radial / Range-Profile Support

Current first-run spec status:

- not included in the first three default routes.

Should it be optional first round?

- Yes, but only as an optional diagnostic route if range/fan convention readiness is accepted before implementation.

Decision basis:

- SAR geometry makes range/radial support scientifically relevant;
- the local workspace already has inference-side range-profile artifacts;
- Phase5A state definition includes range / azimuth / cross variables;
- however, convention readiness is not yet strong enough to make Route D default.

Dependencies:

- fan/range convention id;
- range-to-image coordinate mapping;
- valid support mask;
- shell/proxy shell;
- separation of temporal prior, SAR peak evidence, and A001-derived candidate generation.

Recommended first-round status:

- OPTIONAL / PARTIAL.
- Include only if the implementation approval explicitly accepts a range-profile route configuration.
- Otherwise keep as second-round.

### Route E: Ridge / Long-Axis Support

Why valuable:

- directly addresses the A001 heading weakness;
- can produce SAR-derived orientation or long-axis hypotheses;
- may be important for rotated OBB and severe truncation cases.

Why risky:

- heading convention is not fully audited;
- GT final width/height/heading semantics are not fully reliable as rotated OBB truth;
- local ridge support may be clutter or shadow;
- display image can distort perceived axis support.

Why not first round:

- center/extent baseline is not yet established;
- route could turn into panel-perception fitting;
- orientation metrics would require convention audit before claims.

Evidence that would make it worth enabling later:

- Route A/B/C establish stable center/extent proposal behavior;
- image source and coordinate conventions are fixed;
- theta output convention is declared;
- Phase5C shows a meaningful gap in orientation capacity not explained by center/extent.

Recommended status:

- HOLD.

### Route F: Hybrid Shell + SAR Evidence

Why closest to final mainline:

- combines optical shell with SAR observation evidence;
- preserves optical prior and SAR observation scores as separate fields;
- is closest to future factor graph node generation.

Why too risky for first round:

- scoring can become hidden ranker tuning;
- route weights can become calibration without being called calibration;
- evaluation feedback can leak into generation;
- uncertainty may collapse to rank1 too early.

How it could become a hidden ranker:

- selecting thresholds from Phase5C metrics;
- merging optical and SAR scores into one active ranking score;
- retaining only top proposals before ceiling audit;
- comparing against C3/C4 and then patching C3/C4.

What must be true before enabling:

- A/B/C or A/B/C/D proposal ceiling is audited;
- separate optical and SAR score fields are stable;
- provenance and leakage audit pass;
- route_config_id is frozen before metrics;
- Phase5D approval exists if graph inference is tested.

Recommended status:

- HOLD for first round.

## 6. Input Source And Readiness Inventory

This inventory is based on existing workspace files. It does not create new files.

### 6.1 Target Set

Current status:

- Phase4D GM_RM017 205-target set is usable as the provisional target set.

Evidence/path:

- `output/gm17_phase4D_candidate_pool_ceiling_audit_20260629_001655/candidate_pool_ceiling_summary.json`
- `output/gm17_phase4D_candidate_pool_ceiling_audit_20260629_001655/candidate_pool_ceiling_per_target.csv`

Observed evidence:

- `target_group_count = 205`;
- A001 baseline ceiling exists;
- per-target post-hoc failure labels exist in `candidate_pool_ceiling_per_target.csv`.

Readiness:

- PARTIAL.

Reason:

- the target set exists through Phase4D output, but there is no separate frozen `target_set_freeze.csv`.

Future target set freeze schema:

- `target_set_id`;
- `target_identity`;
- `scene`;
- `sar_frame_num`;
- `gm17_track_id`;
- `source_phase`;
- `source_path`;
- `include_flag`;
- `freeze_timestamp`;
- `leakage_boundary_note`.

No target-set freeze file is generated in this review.

### 6.2 Shell / Proxy Shell

Current status:

- formal optical-conditioned shell is not frozen.

Possible proxy shells:

| proxy | path if known | fields | inference-safe status | GT/A019/A021 derived? | uncertainty semantics | risk | recommendation |
|---|---|---|---|---|---|---|---|
| A001 candidate envelope | `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv` | `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross` | inference-side table, but A001-biased | no explicit GT columns in header | envelope only if explicitly defined | can collapse back to A001 reranking | use only as baseline/proxy with strong caveat |
| optical temporal prior window | `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv` | `pred_cx`, `pred_cy`, `pred_w`, `pred_h`, `pred_r`, `pred_az`, `pred_cross` | potentially inference-safe if legacy scores/deltas excluded | no final/GT columns in header | soft prior, not final shell | may inherit legacy A005/A001 bias | candidate proxy if source approved |
| ray/range profile support | `output/clean_no_gt_localizer_2026-05-31_gm17_ray_profile/gm17_range_posterior_modes_inference.csv` and `gm17_ray_profile_peaks_inference.csv` | `mode_r`, `peak_r`, `peak_score`, `range_prior_r` | inference-side route artifact | not in header | range-mode support | convention dependency | use only for optional Route D after convention approval |
| wedge profile modes | `output/clean_no_gt_localizer_2026-05-31_gm17_wedge_escape/gm17_wedge_profile_modes_inference.csv` | `r_hat`, `cross_hat`, `az_offset_hat`, `posterior_score` | manifest states inference boundary | not in header | range/cross mode support | tied to earlier candidate expansion logic | optional diagnostic evidence, not default shell |
| visible extent features | `output/clean_no_gt_localizer_2026-05-31_visible_extent_gated/visible_extent_features.csv` | `support_px`, `est_w`, `est_h`, `component_count`, edge-touch flags | image-derived inference feature table | not in header | visible support only | can become threshold gate | useful for readiness, not formal shell |

Key judgment:

- shell source is the largest blocker for first-round implementation.

Recommendation:

- HOLD implementation until a shell source or proxy shell is explicitly accepted.
- If no formal shell exists, use an approved proxy shell only with a `shell_source_id`, `shell_version`, and uncertainty note.

### 6.3 SAR Image / Local Crop Source

Current status:

- display/pseudocolor SAR path is available and has been resolved in existing audits.

Evidence/path:

- `output/gm17_phase4_sar_structure_evidence_scout_20260628_183122/scout_path_resolution_report.csv`
- `output/gm17_phase4_sar_structure_full_audit_20260628_214419/full_path_resolution_report.csv`

Observed path pattern:

- `D:\profile\research\data\GM_RM017\GM_RM017_SARframes\000310.png`
- images read as `1334 x 2308` in local audit rows.

Current risk:

- existing structure audits label the source as `diagnostic_on_display_image`;
- raw SAR or grayscale source is not confirmed here;
- display/pseudocolor may alter energy/contrast.

First-round recommendation:

- display/pseudocolor can be used for diagnostic-only Route B/C if clearly labeled;
- raw/grayscale should remain PARTIAL/BLOCKED until source is identified;
- every route must store `sar_image_source_id` and `source_crop_id`.

### 6.4 Scene Geometry / Valid Support

Current status:

- image bounds are known from prior image reads;
- A001/A005-style fields expose `r`, `az`, `cross`, `pred_r`, `pred_az`, `pred_cross`;
- formal coordinate convention metadata and valid support mask are not frozen.

Evidence/path:

- `candidate_bank_inference.csv` has `r`, `az`, `cross`;
- `gm17_temporal_inference.csv` has `pred_r`, `pred_az`, `pred_cross`;
- image path reports contain image size.

Readiness:

- PARTIAL.

Risk:

- route D and any radial/range support depend on convention correctness;
- valid support mask policy is not yet a frozen artifact.

Recommendation:

- Route A/B/C can proceed after basic image bounds and support policy are approved;
- Route D requires a `coordinate_convention_id` and `valid_support_source_id`.

### 6.5 Temporal Prior

Current status:

- inference-side temporal prior exists.

Evidence/path:

- `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv`

Relevant fields:

- `pred_cx`, `pred_cy`, `pred_w`, `pred_h`, `pred_heading_deg`;
- `pred_r`, `pred_az`, `pred_cross`;
- `gm17_track_id`;
- score-like and decision-like fields also exist.

Readiness:

- PARTIAL.

Risk:

- temporal score fields can reintroduce legacy A001/A005 bias;
- temporal prior can dominate SAR evidence if used as scoring.

Recommendation:

- first round should use temporal only as shell/proxy metadata if approved;
- do not use `score`, `lr_score`, `sar_factor_score`, or `temporal_factor_score` as proposal scoring inputs.

## 7. Readiness Matrix

| item | current status | evidence/path | risk | recommendation | readiness |
|---|---|---|---|---|---|
| target set | Phase4D 205 targets exist | `candidate_pool_ceiling_summary.json`, `candidate_pool_ceiling_per_target.csv` | no independent frozen target list | freeze before implementation | PARTIAL |
| shell/proxy shell | no formal Phase5 shell frozen | A001 envelope, temporal inference, ray/wedge profile artifacts | biggest blocker; A001 bias risk | approve one proxy or create formal shell spec first | BLOCKED |
| SAR pseudocolor/display image | path resolved in prior audits | `full_path_resolution_report.csv`, `scout_path_resolution_report.csv` | display artifact risk | usable for diagnostic-only A/B/C with source label | PARTIAL |
| SAR grayscale/raw image | not confirmed in this review | none confirmed | energy/contrast semantics uncertain | identify source before raw-SAR claims | BLOCKED |
| valid support mask | not frozen | image bounds known; mask source not found | proposals may sample invalid support | define support policy before run | PARTIAL |
| fan geometry | fields exist | `r`, `az`, `cross`, `pred_r`, `pred_az`, `pred_cross` | convention not fully frozen | sufficient for cautious proxy, not for default Route D | PARTIAL |
| coordinate convention | incomplete | geometry add-on says heading convention not fully audited | rotated/radial claims risky | define `coordinate_convention_id` before Route D/E | PARTIAL |
| temporal prior | inference table exists | `gm17_temporal_inference.csv` | score leakage / legacy bias | use only as soft shell/proxy metadata | PARTIAL |
| Route A | methodologically safe | first-run spec | blocked by shell source | default only after shell approval | PARTIAL |
| Route B | justified by SAR evidence | Phase4 structure audits and literature | display-image risk; peak-center mismatch | keep default diagnostic | PARTIAL |
| Route C | justified by component proposals | visible extent and structure audits | threshold sensitivity | keep default diagnostic with predeclared threshold family | PARTIAL |
| optional Route D | locally plausible | ray/range/wedge inference artifacts | convention dependency | optional only after range/fan readiness | PARTIAL |
| Phase5C post-hoc boundary | clear in specs | Phase5B protocol and first-run spec | metric feedback leakage | keep strict generate-then-join rule | READY |

## 8. Recommended First Diagnostic Run After Literature Review

Recommendation:

- retain the original three default routes;
- add Route D only as optional and readiness-gated;
- keep Route E and Route F held.

Default routes:

- Route A: shell-grid / multi-scale sampling;
- Route B: local energy / contrast peak proposals;
- Route C: simple connected-component diagnostic.

Optional route:

- Route D: radial / range-profile support, only if shell source, fan/range convention, and provenance rules are accepted before implementation.

Held routes:

- Route E: ridge / long-axis support;
- Route F: hybrid shell + SAR evidence ranker;
- learned models;
- factor graph over generated proposals;
- active C3/C4 integration;
- threshold/weight tuning.

Safest route:

- Route A is conceptually safest as a coverage baseline, but it is blocked by shell/proxy-shell readiness.

Most practical SAR-evidence route:

- Route B, because SAR display image paths are already resolved and local contrast/energy evidence has prior diagnostic support.

Largest blocker:

- formal shell/proxy shell source and coordinate/support convention.

Can implementation proceed now?

- HOLD.

Minimum precondition before implementation:

- approve a shell/proxy shell source;
- freeze target set id;
- identify SAR image source id and crop policy;
- define valid support source or bounds policy;
- submit a predeclared config block;
- approve leakage audit checklist.

## 9. Updated Predeclared Config Template

This template is more explicit than the current first-run spec, but it does not fill numeric values.

```yaml
experiment_id: TBD_before_implementation
target_set_id: TBD_before_implementation
route_config_id: TBD_before_implementation

shell_source_id: TBD_before_implementation
shell_version: TBD_before_implementation

sar_image_source_id: TBD_before_implementation
crop_policy_id: TBD_before_implementation
valid_support_source_id: TBD_before_implementation
coordinate_convention_id: TBD_before_implementation

route_list:
  - shell_grid
  - energy_contrast_peak
  - connected_component
  # optional: radial_range_profile

max_proposals_per_target: TBD_before_implementation
shell_margin_or_crop_size: TBD_before_implementation
scale_set: TBD_before_implementation
offset_grid: TBD_before_implementation

energy_peak_count: TBD_before_implementation
local_background_policy: TBD_before_implementation

component_threshold_family: TBD_before_implementation
component_size_filter: TBD_before_implementation
component_merge_policy: TBD_before_implementation
duplicate_merge_policy: TBD_before_implementation

optional_radial_profile_policy: TBD_before_implementation

output_bundle_id: TBD_before_implementation
leakage_audit_policy: TBD_before_implementation
```

Rules:

- all values must be declared before implementation;
- no values may be selected using Phase5C metrics;
- changing a value after seeing metrics requires a new `route_config_id`;
- all route outputs must remain diagnostic-only and separate from C3/C4.

## 10. Phase5C Evaluation Preview

Phase5C remains post-hoc. It must not feed back into Phase5B proposal generation.

Future Phase5C should compare:

- proposal ceiling vs A001 ceiling;
- shell coverage;
- oracle best center error;
- oracle AABB proxy IoU;
- outside-A001-neighborhood rate;
- route contribution;
- proposal density;
- condition breakdown;
- orientation diversity only if route supports `theta`;
- partial visibility / fan-edge / clutter cases.

Interpretation boundary:

- proposal ceiling is not active inference performance;
- high oracle quality at high proposal density is not enough;
- outside-A001 hypotheses require visual and provenance audit;
- condition breakdown cannot tune proposal thresholds;
- generated proposals cannot enter C3/C4 without later explicit approval.

## 11. Final Recommendation

Recommendation status:

- HOLD implementation for now.

Reason:

- the largest blocker is not route choice; it is shell/proxy-shell readiness and coordinate/support convention.

If implementation is later approved, first round should allow:

- Route A: shell-grid / multi-scale sampling;
- Route B: local energy / contrast peak proposals;
- Route C: simple connected-component diagnostic.

Route D:

- optional only if fan/range convention and shell source readiness are approved.

Continue to hold:

- Route E ridge / long-axis;
- Route F hybrid shell + SAR evidence;
- learned models;
- factor graph over generated proposals;
- active C3/C4 integration;
- scoring or threshold tuning.

Must remain open:

- raw SAR vs display/pseudocolor decision;
- final proposal algorithm;
- concrete threshold values;
- proposal scale set;
- rotated OBB representation;
- learned detector design;
- factor graph integration.

Must be fixed before implementation:

- target set id;
- shell/proxy-shell source;
- SAR image source id;
- crop policy;
- valid support source;
- coordinate convention id;
- route_config_id;
- leakage audit policy.

## 12. References

- [AFRL, accessed 2026-06-29] Air Force Research Laboratory. MSTAR Public Targets. Official dataset page. URL: https://www.sdms.afrl.af.mil/index.php?collection=mstar&page=targets
- [Alexe et al., 2012] Bogdan Alexe, Thomas Deselaers, Vittorio Ferrari. Measuring the Objectness of Image Windows. IEEE Transactions on Pattern Analysis and Machine Intelligence, 2012. DOI: https://doi.org/10.1109/TPAMI.2012.28
- [Arulampalam et al., 2002] M. S. Arulampalam, S. Maskell, N. Gordon, T. Clapp. A Tutorial on Particle Filters for Online Nonlinear/Non-Gaussian Bayesian Tracking. IEEE Transactions on Signal Processing, 2002. DOI: https://doi.org/10.1109/78.978374
- [Canny, 1986] John Canny. A Computational Approach to Edge Detection. IEEE Transactions on Pattern Analysis and Machine Intelligence, 1986. DOI: https://doi.org/10.1109/TPAMI.1986.4767851
- [Dellaert, 2012] Frank Dellaert. Factor Graphs and GTSAM: A Hands-on Introduction. Georgia Tech Technical Report GT-RIM-CP&R-2012-002, 2012. URL: https://repository.gatech.edu/entities/publication/0c2ac17c-1df4-48fe-8532-8f746868934a
- [Dellaert and Kaess, 2017] Frank Dellaert, Michael Kaess. Factor Graphs for Robot Perception. Foundations and Trends in Robotics, 2017. DOI: https://doi.org/10.1561/2300000043 URL: https://www.cs.cmu.edu/~kaess/pub/Dellaert17fnt.pdf
- [Dellinger et al., 2015] F. Dellinger, J. Delon, Y. Gousseau, J. Michel, F. Tupin. SAR-SIFT: A SIFT-Like Algorithm for SAR Images. IEEE Transactions on Geoscience and Remote Sensing, 2015. DOI: https://doi.org/10.1109/TGRS.2014.2323552
- [Frangi et al., 1998] Alejandro F. Frangi, Wiro J. Niessen, Koen L. Vincken, Max A. Viergever. Multiscale Vessel Enhancement Filtering. MICCAI, LNCS 1496, 1998. DOI: https://doi.org/10.1007/BFb0056195
- [Gao et al., 2009] Gui Gao, Li Liu, Lingjun Zhao, Gongtao Shi, Gangyao Kuang. An Adaptive and Fast CFAR Algorithm Based on Automatic Censoring for Target Detection in High-Resolution SAR Images. IEEE Transactions on Geoscience and Remote Sensing, 2009. DOI: https://doi.org/10.1109/TGRS.2008.2006504
- [Sommervold et al., 2023] Oscar Sommervold, Marco Gazzea, Reza Arghandeh. A Survey on SAR and Optical Satellite Image Registration. Remote Sensing, 2023. DOI: https://doi.org/10.3390/rs15030850
- [Goodman, 1976] Joseph W. Goodman. Some Fundamental Properties of Speckle. Journal of the Optical Society of America, 1976. DOI: https://doi.org/10.1364/JOSA.66.001145
- [Gordon et al., 1993] N. J. Gordon, D. J. Salmond, A. F. M. Smith. Novel Approach to Nonlinear/Non-Gaussian Bayesian State Estimation. IEE Proceedings F - Radar and Signal Processing, 1993. DOI: https://doi.org/10.1049/ip-f-2.1993.0015
- [Kschischang et al., 2001] F. R. Kschischang, B. J. Frey, H.-A. Loeliger. Factor Graphs and the Sum-Product Algorithm. IEEE Transactions on Information Theory, 2001. DOI: https://doi.org/10.1109/18.910572
- [Li et al., 2020] Jiayuan Li, Qingwu Hu, Mingyao Ai. RIFT: Multi-Modal Image Matching Based on Radiation-Variation Insensitive Feature Transform. IEEE Transactions on Image Processing, 2020. DOI: https://doi.org/10.1109/TIP.2019.2959244
- [Liu et al., 2023] Zhigang Liu, Shengjie Luo, Yiting Wang. Mix MSTAR: A Synthetic Benchmark Dataset for Multi-Class Rotation Vehicle Detection in Large-Scale SAR Images. Remote Sensing, 2023. DOI: https://doi.org/10.3390/rs15184558
- [Otsu, 1979] Nobuyuki Otsu. A Threshold Selection Method from Gray-Level Histograms. IEEE Transactions on Systems, Man, and Cybernetics, 1979. DOI: https://doi.org/10.1109/TSMC.1979.4310076
- [Reid, 1979] Donald B. Reid. An Algorithm for Tracking Multiple Targets. IEEE Transactions on Automatic Control, 1979. DOI: https://doi.org/10.1109/TAC.1979.1102177
- [Suri and Reinartz, 2010] Sahil Suri, Peter Reinartz. Mutual-Information-Based Registration of TerraSAR-X and Ikonos Imagery in Urban Areas. IEEE Transactions on Geoscience and Remote Sensing, 2010. DOI: https://doi.org/10.1109/TGRS.2009.2034842
- [Uijlings et al., 2013] J. R. R. Uijlings, K. E. A. van de Sande, T. Gevers, A. W. M. Smeulders. Selective Search for Object Recognition. International Journal of Computer Vision, 2013. DOI: https://doi.org/10.1007/s11263-013-0620-5
- [Ye et al., 2017] Yuanxin Ye, Jie Shan, Lorenzo Bruzzone, Li Shen. Robust Registration of Multimodal Remote Sensing Images Based on Structural Similarity. IEEE Transactions on Geoscience and Remote Sensing, 2017. DOI: https://doi.org/10.1109/TGRS.2017.2656380
- [Zitnick and Dollar, 2014] C. Lawrence Zitnick, Piotr Dollar. Edge Boxes: Locating Object Proposals from Edges. ECCV, 2014. DOI: https://doi.org/10.1007/978-3-319-10602-1_26

## 13. Boundary Statement

This document is documentation-only.

- Literature-informed review only.
- No code was added.
- No experiment was added.
- No proposal was generated.
- No candidate was generated.
- No C3/C4 ranking was changed.
- No A001/A005/A019/A021 source file was modified.
- No threshold tuning was performed.
- No model was trained.
- No calibration was performed.
- No active proposal was injected into C3/C4.
- No push was performed.
- This file is not staged or committed unless explicitly approved later.
