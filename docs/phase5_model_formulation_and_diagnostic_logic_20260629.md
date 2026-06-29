# Phase5 Model Formulation And Diagnostic Logic

Date: 2026-06-29

## 1. Purpose

This document explains the Phase5 model formulation and diagnostic logic. It is documentation-only.

It does not add a new experiment, generate proposals, run Phase5C evaluation, claim a final model, join A019/A021, compute GT/oracle metrics, compute IoU or center error, compare C3/C4, tune thresholds, train a model, or perform calibration.

The purpose is to explain Phase5B-v0 A/B/C routes as a diagnosable, physically interpretable, probabilistically coherent early model form. Phase5B-v0 should not be described as a simple stack of `shell_grid`, `energy_contrast_peak`, and `connected_component` heuristics. It should be described as a diagnostic discrete approximation to posterior support over a SAR latent vehicle state.

## 2. Research Question

The current research question is not:

- fixed A001 candidate-row selection;
- C3/C4 rank tuning;
- v3 rule tuning;
- rotated OBB metric chasing;
- heuristic feature stacking.

The current question is:

Given an optical-observed vehicle target, temporal prior, scene geometry, and SAR local image evidence, infer or approximate the latent SAR vehicle state.

中文解释：我们要研究的是如何从光学侧观测到的目标状态，迁移到 SAR 图像中的目标状态推断，而不是在已有 A001 候选库中选择一行。A001 candidate bank can remain a baseline and a historical selection-layer prototype, but it is not the full optical-to-SAR migration model.

## 3. Latent SAR Vehicle State

The latent SAR vehicle state is represented conceptually as:

```text
s = {
  center,
  extent,
  orientation / long-axis state,
  range-azimuth-cross state,
  visibility / support state,
  uncertainty,
  hypothesis identity
}
```

`center` is a position hypothesis in SAR image coordinates. It is the image-space location that the model treats as a possible SAR vehicle support center, not necessarily the optical box center.

`extent` is the visible or localizable SAR support range. It does not have to equal the full physical vehicle box from optical imagery. In partial visibility, edge truncation, shadowing, or clutter cases, a SAR-support extent can be smaller, fragmented, or shifted relative to the complete optical vehicle footprint.

`orientation / long-axis state` represents SAR body-axis or scattering-axis hypotheses in the eventual model. In Phase5B-v0, `theta` is only metadata copied from the A005 proxy where available. It is not a SAR-derived long-axis state, and v0 does not claim rotated OBB localization.

`range-azimuth-cross state` represents geometry-aware SAR coordinates and offsets. In v0, this information is carried from A005 proxy fields where available, but radial/range-profile modeling is disabled until the fan/range convention and valid support mapping are frozen.

`visibility / support state` represents partial support, fragmented components, boundary-touching components, clutter risk, and other SAR-specific support conditions. These are model variables and uncertainty flags, not just failure labels.

`uncertainty` is part of the state representation. A multi-hypothesis output is expected at this stage because SAR evidence can be ambiguous.

`hypothesis identity` preserves multiple candidate state hypotheses through `proposal_id`. It prevents the model from collapsing too early to a rank1 output before the posterior support has been diagnosed.

## 4. Conditional Inference View

The target problem can be written as:

```text
p(s | o, t, g, I_sar)
```

where:

- `s` is the SAR latent vehicle state;
- `o` is the optical target state;
- `t` is the temporal prior;
- `g` is scene geometry and coordinate support;
- `I_sar` is local SAR image evidence.

The optical/temporal prior constrains the feasible state space. It should provide a search shell or prior distribution, not directly decide the final SAR box.

SAR image evidence provides observation support inside that shell. It can support possible centers, visible extents, scattering structures, and future long-axis evidence.

Geometry and coordinate conventions restrict the valid region. In v0, valid support is limited to display-image bounds because fan/range support masks are not yet frozen.

Uncertainty and multi-hypothesis behavior are part of the model. They are not automatically errors. The first diagnostic run is expected to preserve several state hypotheses per target so that Phase5C can diagnose which parts of the posterior support are useful.

## 5. Factorized Interpretation

Phase5B-v0 is best interpreted as a factorized support model:

```text
support(s)
  approx prior_optical_temporal(s | o, t)
       + observation_sar(s | I_sar)
       + geometry_support(s | g)
       + uncertainty / hypothesis management
```

In factor-graph language:

- state node: SAR vehicle state hypothesis `s`;
- optical/temporal prior factor: constrains plausible SAR state around the optical-conditioned temporal shell;
- SAR observation factor: supports or weakens hypotheses using local SAR evidence;
- geometry/support factor: enforces coordinate, crop, image-bound, and future valid-support constraints;
- temporal/multi-hypothesis factor: keeps multiple plausible hypotheses until evaluation or downstream inference decides how to fuse them;
- evaluation factor: not part of inference.

A019, A021, GT boxes, oracle labels, IoU, center error, and panel review belong only to evaluation audit. They are not inference factors and must not enter proposal generation.

A001 `candidate_id` is not the state itself. It was the row identifier for an older fixed-bank candidate carrier.

Phase5B `proposal_id` is also not the final result. It is a discrete id for a latent state hypothesis generated for diagnostic posterior-support analysis.

## 6. Physical Meaning Of Route A/B/C

### 6.1 Route A: shell_grid As Prior-Support Discretization

`shell_grid` does not use SAR pixels. It discretizes the optical/temporal proxy shell into a bounded set of center and extent hypotheses.

Its physical motivation is that optical-to-SAR transfer contains mismatch: time offset, projection error, SAR display support differing from optical box support, and possible target appearance changes. Therefore, the model should not fully trust a single A005 point prediction.

Route A samples limited hypotheses around the A005 proxy center and extent. It is a prior-support family, not an image detector.

Route A cannot prove that SAR image evidence is effective. It can only diagnose whether the optical/temporal shell covers the target well enough to create useful SAR state hypotheses.

If Route A has a strong Phase5C ceiling, the proxy shell is likely useful as a prior. If Route A is weak, the correct response is to rework the optical-conditioned shell, not to tune SAR observation thresholds.

### 6.2 Route B: energy_contrast_peak As SAR Center-Evidence Hypothesis

`energy_contrast_peak` is the weakest v0 form of a SAR observation factor.

The physical motivation is that a vehicle in SAR may produce local bright scattering or high contrast relative to the local background. A local peak can therefore be a center-support hypothesis.

But a bright peak is not the vehicle center. It may be a corner reflector-like scatterer, clutter, speckle, shadow boundary, display encoding artifact, or only one part of a partially visible vehicle.

Route B has a SAR-domain motivation, but it is not a full detector. It diagnoses whether local contrast or energy can propose useful center hypotheses beyond A005 and A001.

If Route B is useful in Phase5C, SAR observation factors have value for center localization. If Route B is weak, the next step is not to tune top-k or thresholds inside v0; the next step is to consider raw SAR, range/radial profile evidence, or a stronger SAR observation model.

### 6.3 Route C: connected_component As Visible-Support Extent Hypothesis

`connected_component` is not final segmentation.

It uses simple foreground-like support inside the SAR crop to create visible-support extent hypotheses. A component bounding box is not the complete vehicle box. It can represent only visible scatter, a fragmented support region, a merged clutter region, or a boundary-truncated support patch.

Route C diagnoses whether visible SAR support can provide extent information. It is a support-factor family, not a final full-body box estimator.

If Route C improves extent coverage or AABB IoU in Phase5C, visible support is a useful model component. If Route C mostly produces fragments or clutter merges, the current component observation is too weak and should be replaced or made uncertainty-aware.

## 7. Why This Is Not Heuristic Stacking

Phase5B-v0 looks like it contains a grid, image peaks, and components, but the goal is not to stack features and chase a score.

The v0 routes split a complex posterior-support problem into diagnosable factor families:

- prior support family: `shell_grid`;
- SAR center evidence family: `energy_contrast_peak`;
- SAR visible-support extent family: `connected_component`.

Each route answers a different model question:

- Does the prior shell cover plausible SAR states?
- Does local SAR energy provide center evidence?
- Does visible support provide extent evidence?

These route families should be diagnosed separately in Phase5C. They should not be merged into a black-box score, tuned against GT, or inserted into C3/C4 active inference.

## 8. What Phase5B-v0 Has Implemented

Phase5B-v0 has implemented a frozen diagnostic proposal-generation pass:

- frozen config: `configs/phase5B_first_diagnostic_run_config_v0.json`;
- route config id: `phase5B_diag_v0_predeclared`;
- proposal output: `output/phase5B_first_diagnostic_run_v0_20260629_102746/proposal_candidates.csv`;
- total proposals: `7490`;
- `shell_grid`: `5535`;
- `energy_contrast_peak`: `1025`;
- `connected_component`: `930`;
- no A019/A021 join;
- no GT/oracle metrics;
- no IoU or center error;
- no C3/C4 comparison.

This step only constructs a hypothesis space. It does not evaluate whether the hypotheses are correct.

## 9. What Phase5C Should Diagnose

Phase5C should be a model diagnostic, not a generic metric report or final performance claim.

### H1: Prior-Shell Coverage

Question: Does Route A cover the SAR target?

If Route A performs well, the A005 proxy shell is useful as a prior-support source. If Route A performs poorly, the shell should be rebuilt before investing in stronger SAR observation factors.

### H2: SAR Center Evidence

Question: Does Route B provide additional center support?

If Route B improves center hypotheses, local contrast or energy has value as a SAR observation factor. If Route B is weak, display-grayscale peak evidence is insufficient and the observation model should move toward raw SAR, range profile, radial support, or richer structure evidence.

### H3: SAR Visible-Support Extent

Question: Does Route C improve visible extent or AABB proxy support?

If Route C improves extent coverage, visible support has modeling value. If Route C fails through fragments, boundary artifacts, or clutter merges, connected-component observation is not reliable enough in v0.

### H4: Novelty Beyond A001

Question: Do Phase5B proposals provide hypotheses outside the fixed A001 candidate-bank neighborhood?

Phase5C should separate at least:

- A001 bad / Phase5B good;
- A001 good / Phase5B bad;
- both good;
- both bad.

This determines whether generated proposals add a genuinely new search-space capability or merely reproduce the fixed-bank behavior.

### H5: Failure-Condition Sensitivity

Question: Does Phase5B behave differently under truncation, occlusion, fan-edge, clutter, and partial-visibility conditions?

A021 condition labels can only be joined after proposal outputs are frozen for Phase5C. They must not influence Phase5B generation, route thresholds, or v0 configuration.

## 10. Decision Logic After Phase5C

### Case A: Route A Strong, Route B/C Weak

Interpretation: the optical/temporal shell is useful, but the SAR observation model is weak.

Next step:

- rebuild SAR observation;
- consider Route D range/radial profile;
- inspect raw SAR source availability;
- do not tune connected-component thresholds blindly.

### Case B: Route B Improves Center Hypotheses

Interpretation: SAR local contrast contributes useful center evidence.

Next step:

- keep an energy observation factor;
- research more robust SAR center evidence;
- consider adding a SAR observation factor to a future factor graph after Phase5C review.

### Case C: Route C Improves Extent Hypotheses

Interpretation: visible SAR support contributes useful extent evidence.

Next step:

- keep a visible-support factor;
- model fragmentation and boundary-touching uncertainty;
- design a support-aware extent model instead of treating component boxes as full vehicle boxes.

### Case D: Phase5B Improves A001-Bad Cases

Interpretation: generated proposals provide new state hypotheses beyond the fixed A001 bank.

Next step:

- prepare Phase5D factor graph over generated proposals;
- or design proposal fusion as a separate stage;
- still do not directly integrate generated proposals into C3/C4.

### Case E: Phase5B Globally Weaker Than A001

Interpretation: the v0 model formulation is insufficient.

Next step:

- reconstruct a formal optical-conditioned shell;
- introduce Route D after fan/range convention is frozen;
- re-audit SAR image source and display encoding;
- open Phase5B-v1 as a new frozen configuration rather than tuning v0 after seeing metrics.

## 11. What Is Not Claimed

Phase5B-v0 does not claim:

- optical-to-SAR localization is solved;
- generated proposals are final detections;
- an energy peak equals the vehicle center;
- a connected-component box equals the complete vehicle box;
- the A005 proxy shell is the final optical-conditioned shell;
- `theta` is SAR-derived orientation;
- proposal ceiling equals actual inference performance;
- Phase5B can directly replace A001;
- generated proposals can directly enter C3/C4.

## 12. Relationship To Future Factor Graph

If Phase5C shows that the proposal space has ceiling value, Phase5D can be considered. Phase5D is not automatic and should not start before Phase5C demonstrates that generated proposals add useful posterior support.

A reasonable Phase5D direction would be:

- proposal nodes as SAR latent state hypotheses;
- optical prior factor;
- SAR observation factor;
- geometry/support factor;
- temporal consistency factor;
- uncertainty and multi-hypothesis handling.

Phase5D would then fuse proposal hypotheses under a factor graph. It should not be treated as a C3/C4 patch, a fixed-bank ranker tweak, or a post-hoc metric tuning step.

## 13. Boundary Statement

- Documentation-only.
- No code.
- No experiment.
- No proposal generated.
- No A019/A021 join.
- No GT/oracle metrics.
- No IoU or center error.
- No C3/C4 comparison.
- No threshold tuning.
- No training.
- No calibration.
- No push.
- File not staged or committed unless explicitly approved.
