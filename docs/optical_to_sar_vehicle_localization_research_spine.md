# Optical-to-SAR Vehicle Localization Research Spine

## Project Context Primer

This project studies vehicle localization in optical-to-SAR transfer. The problem is not ordinary object detection in a single image. Optical imagery provides a prior about where a vehicle track should be, while SAR imagery contains a different physical signal: radar scattering, layover, shadows, aspect-dependent highlights, and geometry distortions. The research question is how to localize a vehicle in SAR when the visible SAR evidence is indirect, sparse, or structurally different from the optical appearance.

The current abstraction is candidate selection, not raw detection. A frozen SAR candidate bank supplies a fixed set of possible vehicle boxes or states for each target/frame. The research system does not generate new candidates in the current line. It asks which existing SAR candidate should be selected, rejected, or treated as uncertain under a physically interpretable set of factors. This keeps the scientific question narrow: can the model explain and choose among a fixed proposal set without changing the search space?

GM17 is the staged evidence source for this line. It provides selected-prediction behavior, fixed candidate-bank references, diagnostic examples, B patch behavior, factor-prior evidence, and failure-case exposure. GM17 is not the final model template, not the final physical architecture, and not a mainline to keep patching indefinitely. Its value is that it exposes what a future model must explain and where current patch-based behavior is fragile.

The B patch is likewise diagnostic evidence, not physical proof. Reproducing B patch behavior can show that a factor graph has enough structure to mimic a known diagnostic repair, but it does not prove that the factors are physically correct, independently calibrated, or safe to deploy as a final selector. Any model that copies B patch actions without separating the physical support from the engineering safety behavior remains scientifically suspect.

The long-term modeling goal is a hierarchical factor graph reconstruction framework. The model should represent vehicle state, candidate identity, source family, direction state, temporal consistency, and track continuity as structured latent or observed factors over a fixed candidate bank. The intended inference style is MAP/Viterbi over candidates and tracks, with factors converted into costs through predeclared transforms. This route is meant to move from patch reasoning toward auditable physical and statistical explanations.

The current mainline is complete-vehicle first. It assumes the whole vehicle is recoverable enough for a full-center candidate selection problem. That mainline deliberately excludes truncation, occlusion, missing extent, visible/full-center offset, and near-field geometry-regime changes from active modeling. Those cases matter scientifically, but they are future branches; they must not contaminate the complete-vehicle audit.

The allowed Phase4 active fixed-prior factors are:

- `geometry_factor`;
- `direction_factor`;
- controlled non-visible `source_factor`;
- `optical_temporal_factor`;
- `transition_factor`.

These factors are allowed only as fixed-prior candidates and only under their Phase3 control conditions. They must not use learned weights, OOF calibration, candidate-bank changes, or evaluation-only labels.

The excluded diagnostic-only or future factors are:

- `sar_structure_factor`;
- `uncertainty_factor`;
- `final_arbitration_factor`;
- `visibility_factor`;
- `missing_extent_factor`;
- `visible_full_center_offset_factor`.

`sar_structure_factor` and `uncertainty_factor` remain diagnostic review surfaces because their evidence overlaps and because SAR uncertainty is entangled with B patch behavior. `final_arbitration_factor` remains blocked from active scoring because it can copy B patch actions. Visibility, missing extent, and visible/full-center offset remain future Phase7 partial-visibility material.

Partial visibility is the future Phase7 route for truncation, occlusion, missing extent, and visible/full-center mismatch. It must explicitly model that visible support is not the full vehicle center. Visible support may become factor, veto, or uncertainty evidence, but it must not generate a full-center prediction.

Near-field is a future geometry-regime route, not simply an occlusion variant. It may require a different reliability model for SAR geometry. In the current research line, near-field cannot modify the candidate bank, cannot replace the complete-vehicle selector, and cannot enter OOF calibration.

Inference/evaluation separation is central to the science. Inference must use only inference-safe fields and diagnostic-safe fields allowed by the phase. Evaluation-only fields such as GT, oracle, IoU, center error, condition labels, truncation labels, occlusion labels, and final annotation fields may be joined only after inference outputs already exist. This separation is what lets the project distinguish explanatory modeling from hindsight scoring.

Phase4 fixed-prior revalidation is supposed to test whether the audited complete-vehicle factors can explain candidate selection under frozen inputs and predeclared, non-learned priors. It is not supposed to prove final performance, learn weights, tune factors, calibrate OOF models, replace GM17, or activate future branches. Its scientific value is to reveal whether a small set of physically interpretable complete-vehicle factors has coherent explanatory power before the project considers learning or calibration.

# Research Problem

The scientific problem is to localize vehicles in SAR imagery using optical-to-SAR transfer while preserving interpretability and avoiding leakage from evaluation labels. SAR vehicle appearance is not a simple visual translation of optical appearance. Radar response depends on geometry, range/azimuth structure, scattering centers, aspect, layover, shadow, and local scene conditions. A vehicle that is obvious in optical imagery may be fragmented or displaced in SAR.

This project therefore frames the current task as structured candidate selection. Given a frozen set of SAR candidate boxes or states, the model must decide which candidate best represents the full vehicle under complete-vehicle assumptions. The immediate research question is not "can a detector find every vehicle from pixels?" but "can a physically interpretable selector choose among fixed SAR candidates using audited evidence?"

This framing matters because it separates three problems that are often mixed:

- candidate generation: what possible SAR boxes exist;
- candidate selection: which candidate should be chosen;
- evaluation: how close the selected candidate is to annotation or reference behavior.

The current line studies the second problem under a frozen proposal set. That keeps failure analysis concrete. If a correct candidate exists but is not selected, the selector logic is the issue. If no candidate can represent the true vehicle, that is candidate-bank coverage, which is outside the current Phase4 active scope.

# Scenario And Data Abstraction

The working scenario is a track-level optical-to-SAR localization setting. Optical information provides a temporal and geometric prior. SAR imagery provides candidate evidence through a fixed candidate bank and derived candidate/state features. Each target/frame can be represented as a row with candidate-level alternatives. Tracks provide frame order, continuity constraints, and soft temporal context.

The abstraction is:

```text
optical track prior
-> frozen SAR candidate bank
-> candidate-level state fields
-> fixed-prior factor costs
-> MAP/Viterbi-style candidate selection
-> inference output
-> evaluation-only audit join
```

The candidate bank is frozen. This is a scientific constraint, not just a software convenience. A fixed bank makes it possible to ask whether factor evidence explains selected-prediction behavior without moving the goalposts by adding new proposals. Candidate-bank changes would change the research question and are therefore blocked in the current line.

Candidate nodes may carry fields such as range, cross-range offset, azimuth, heading, width, height, direction state, and source family. Track-level metadata supports temporal ordering and transition costs. Source family labels distinguish candidate origins such as base, wedge, bidirectional, and track-signed candidates. Visible source behavior is not allowed to become a full-center source in the current mainline.

Evaluation labels are deliberately outside inference. They may be used later to compute center error, IoU, group summaries, or failure categories, but only after inference outputs have already been produced.

# What GM17 Is And Is Not

GM17 is the staged reference line that made the current research route possible. It provides:

- selected-prediction behavior that a future model must explain;
- a fixed candidate-bank reference;
- B patch behavior and diagnostic repair examples;
- hierarchical diagnostic and factor-graph diagnostic examples;
- evidence about factor priors;
- failure cases and risk exposure.

GM17 is not:

- the final system architecture;
- the final physical model;
- proof that a patch is scientifically correct;
- a reason to keep patching indefinitely;
- an authorization to train, calibrate, or replace the mainline.

The correct interpretation is that GM17 is a constrained evidence source. It shows that selected prediction over a fixed candidate bank can be studied through factor behavior, but it does not settle the final form of the model. Its failures are as important as its successes because they reveal where geometry, direction, source, SAR ambiguity, temporal context, and patch dependency interact.

The B patch is especially important to keep in context. If a factor graph reproduces B patch behavior, that may be evidence that the graph can express the same diagnostic decision. It is not proof that the graph has learned or represented the underlying SAR physics. A model that reproduces an engineering patch can still be copying the patch. This is why `final_arbitration_factor`, SAR uncertainty, and action-copying behavior remain high-risk until separated.

# Why A Hierarchical Factor Graph

A hierarchical factor graph is the long-term target because this problem has multiple interacting sources of evidence. A single score or heuristic threshold cannot cleanly represent the difference between geometric compatibility, signed direction evidence, source-family trust, optical temporal context, transition smoothness, SAR ambiguity, and partial visibility.

The factor graph gives the project a way to ask structured questions:

- What is the candidate state?
- What source family produced the candidate?
- Does the candidate match expected geometry?
- Does it match the signed escape direction?
- Is temporal context supporting or misleading?
- Is track continuity stabilizing the path or propagating an error?
- Which evidence is active in complete-vehicle selection, and which evidence is diagnostic-only?

The long-term graph is hierarchical because not all factors belong to the same branch. Complete-vehicle factors should be stabilized first. Partial visibility factors should come later, after the project can distinguish full vehicle state from visible fragments. Near-field geometry regime changes should remain a future reliability route rather than being folded into the current complete-vehicle selector.

The graph also gives a disciplined route from fixed priors to learning. Phase4 can test whether fixed, audited factors behave coherently. Only after that can the project consider whether learned weights or OOF calibration are scientifically justified.

# Current Complete-Vehicle Mainline

The current complete-vehicle mainline assumes that the target vehicle can be represented by a full-vehicle candidate from the frozen bank. It is optimistic about recoverability but conservative about release. It does not claim to solve truncation, occlusion, visible/full-center mismatch, or near-field geometry shifts.

The active complete-vehicle state concept includes:

- fan-polar state, such as range, cross-range offset, and azimuth;
- OBB-like vehicle geometry, such as heading and size;
- direction state;
- source family;
- selected candidate;
- track context when transition is active.

The current allowed Phase4 active factors are the factors that best match this complete-vehicle assumption:

- geometry: does the candidate have plausible fan-polar and vehicle geometry?
- direction: does the candidate agree with signed escape/posterior direction evidence?
- controlled non-visible source: is the candidate source family trustworthy under complete-vehicle assumptions?
- optical temporal: does the optical-to-SAR temporal prior softly support the candidate?
- transition: does the candidate path remain coherent across adjacent frames?

The mainline deliberately excludes active SAR ambiguity arbitration, visible support, missing extent, and near-field regime changes. Those may explain important failures, but they are not allowed to drive Phase4 complete-vehicle scoring.

# Phase4 Fixed-Prior Revalidation Hypothesis

The Phase4 hypothesis is:

```text
A small set of audited complete-vehicle factors, combined under fixed non-learned priors over the frozen candidate bank, can explain meaningful parts of GM17 selected-candidate behavior without copying B patch actions or leaking evaluation labels.
```

This is a revalidation hypothesis, not a performance claim. Phase4 is meant to test explanatory coherence under frozen inputs. If the allowed factors can reproduce stable candidate-selection patterns across controlled ablations, that supports the idea that the complete-vehicle branch has a meaningful scientific basis. If the factors fail, contradict each other, or only work by proxying excluded diagnostic signals, that is equally valuable because it identifies what must be redesigned before learning.

Phase4 is not supposed to optimize the model. It should not learn weights, tune constants from metrics, use OOF calibration, or expand the candidate bank. Its purpose is to stress the fixed-prior structure:

- geometry only;
- direction only;
- non-visible source only;
- optical temporal only;
- transition only;
- paired and combined complete-vehicle factors;
- all allowed fixed-prior factors.

The result should be a scientific answer about factor coherence, double-counting, and failure modes, not a claim that the final system is solved.

# Active Factors And Their Research Meaning

`geometry_factor` asks whether candidate shape and fan-polar location are compatible with the expected complete-vehicle state. It is the most direct physical prior in the current mainline, but it can overlap with SAR shell evidence. Its research role is to test whether geometric plausibility can support selection without borrowing ambiguous SAR-structure evidence twice.

`direction_factor` asks whether a candidate agrees with signed escape or direction posterior evidence. It targets wrong-direction failures and helps distinguish near/base behavior from positive or negative escape alternatives. Its risk is overlap with source-family assumptions: if a source family already encodes expected direction, then direction can be counted twice.

Controlled non-visible `source_factor` asks whether the origin of a candidate is trustworthy under complete-vehicle assumptions. The current active use is limited to non-visible families such as base, wedge, bidirectional, and track-signed candidates. Its research role is to test whether candidate provenance has explanatory value after geometry and direction are controlled. Fields such as `directional_shell_score`, `track_escape_evidence`, and `signed_direction_match` may be referenced only as controlled diagnostic or gated support context unless ownership is explicitly declared.

`optical_temporal_factor` asks whether optical track context, mapped into SAR fan-polar trends, gives useful soft support. It must remain soft. It cannot overwrite the SAR candidate center or become a hard center generator. Its research value is track context, not direct localization.

`transition_factor` asks whether adjacent-frame continuity over candidate state improves track-level selection. It is an edge factor rather than a node prior. Its research role is to test whether physically plausible continuity stabilizes choices without simply duplicating optical temporal smoothness.

Together, these factors form the current complete-vehicle fixed-prior model. Their scientific meaning depends on preserving ownership boundaries. If geometry, source, temporal, and transition evidence all reward the same hidden signal, the graph may look stronger than it is. Phase4 is designed to expose that risk.

# Excluded/Future Factors And Why

`sar_structure_factor` is excluded from active Phase4 scoring because it overlaps with geometry shell evidence and uncertainty. It is scientifically important, but the current evidence is not cleanly separated into SAR support versus SAR ambiguity. Until ownership is declared, it should remain a diagnostic review surface.

`uncertainty_factor` is excluded from active Phase4 scoring because it can duplicate SAR ambiguity, direction conflict, and final arbitration behavior. It is also tied to B patch protection behavior. Its current role is to expose uncertainty-route questions, not to drive fixed-prior candidate scoring.

`final_arbitration_factor` is blocked from active scoring and calibration because it has high B patch dependency. It can reproduce or copy patch actions, which would blur diagnostic consistency with physical explanation. It may remain a diagnostic concept, but not an active Phase4 selector factor.

`visibility_factor` is future Phase7 material. Visible SAR evidence can be sparse, aspect-dependent, and offset from the full vehicle center. It may be factor, veto, or uncertainty evidence in a later partial-visibility branch, but it must not generate a full center in the current line.

`missing_extent_factor` is future Phase7 material because missing extent caused by truncation or occlusion is not standardized in the current complete-vehicle branch. It cannot enter the complete-vehicle mainline.

`visible_full_center_offset_factor` is future Phase7 material because the offset between visible support and latent full-vehicle center has no standardized inference-safe schema yet. It is important exactly because it prevents visible-center misuse, but it is not ready to become active.

Near-field geometry regime is also future-boundary material. It may require a separate model of geometry reliability or mechanism shift. It cannot modify the candidate bank, cannot replace the complete-vehicle selector, and cannot enter OOF calibration.

# Experimental Logic

The experimental logic is staged and falsifiable.

First, freeze the proposal space. The candidate bank must not change. That makes every selection error interpretable as either selector behavior, missing evidence, or candidate-bank coverage limitation.

Second, restrict active evidence to audited complete-vehicle factors. Phase4 should not quietly import SAR ambiguity, final arbitration, visible support, missing extent, or near-field cues as scoring features. Excluded factors may be reviewed diagnostically, but they must not score candidates.

Third, run fixed-prior ablations in a future authorized execution round. Single-factor ablations ask whether each factor has standalone explanatory value. Combined ablations ask whether factors complement each other or double-count the same signal. The all-allowed-factor condition asks whether the complete-vehicle branch is coherent under fixed priors.

Fourth, preserve inference/evaluation separation. Candidate selection must happen before any GT, IoU, center error, condition label, truncation label, occlusion label, oracle field, or final annotation field is joined.

Fifth, interpret failures scientifically. A poor result may mean the factor is weak, the candidate bank lacks the needed proposal, two factors are double-counting, a future branch is needed, or GM17 staged evidence is exposing a patch dependency. The goal is not to force a pass; the goal is to identify what the model actually explains.

# Expected Scientific Contribution

The expected contribution is a disciplined reconstruction of optical-to-SAR vehicle localization as a factor-structured candidate-selection problem.

If Phase4 succeeds, it can show that complete-vehicle candidate selection is not merely a patch artifact. It can demonstrate that geometry, signed direction, source family, optical temporal context, and track continuity provide interpretable evidence under fixed priors. It can also provide a clean basis for deciding which factors might later deserve learned weights.

If Phase4 fails, it can still contribute by identifying why. Failure may reveal that geometry evidence is insufficient, that source direction is double-counted, that temporal smoothness over-stabilizes wrong paths, that SAR ambiguity needs a separate branch, or that partial visibility/near-field regimes are more central than expected.

The important scientific output is therefore not a single score. It is an evidence map:

- which factors explain candidate selection;
- which factors conflict;
- which factors require ownership separation;
- which failures belong to complete-vehicle modeling;
- which failures should be deferred to partial visibility or near-field routes;
- what must be proven before calibration.

# Long-Term Route: Partial Visibility And Near-Field

The long-term route has three broad stages after the current complete-vehicle work.

First, stabilize the complete-vehicle branch. This means proving that the full-vehicle candidate-selection problem can be represented with audited factors over a frozen candidate bank. Phase4 fixed-prior revalidation is part of this stabilization.

Second, build a partial-visibility branch. This branch should handle truncation, occlusion, missing extent, and visible/full-center mismatch. It must explicitly model the fact that visible support is not the full vehicle center. It should treat visible evidence as factor, veto, or uncertainty, not as a full-center generator.

Third, model near-field geometry regime changes. Near-field should be treated as a possible geometry-mechanism or reliability shift, not merely as occlusion. It may need state variables such as geometry-regime state or geometry-regime uncertainty. In the current project boundaries, near-field remains future Phase7B material and cannot modify the candidate bank or replace the complete-vehicle selector.

Only after complete-vehicle and partial-visibility branches are independently auditable should hybrid integration be considered.

# Minimal Research Loop

The minimal research loop is to freeze the candidate bank, audit inference-safe fields, run fixed-prior ablations, and generate inference outputs without eval-only fields. Evaluation-only labels are then joined after inference to produce grouped failure analysis. That analysis decides which factors remain in the complete-vehicle branch, which need redesign, and which should move to future partial-visibility or near-field routes.

# What Must Be Proved Before Learning Or Calibration

Before learning or calibration, the project must prove that the fixed-prior structure is scientifically coherent.

It must prove that inference fields are clean. Eval-only fields must not enter candidate scoring, path construction, missing-value policy, or factor selection. Any metric using labels must happen after inference.

It must prove that the candidate bank is frozen. Candidate-bank changes would change the proposal space and invalidate the fixed-prior revalidation question.

It must prove factor ownership. Geometry/SAR shell terms, direction/source assumptions, and optical-temporal/transition smoothness must be separated enough that the model is not double-counting the same evidence.

It must prove that B patch behavior is not being copied. `final_arbitration_factor`, `patch_action`, and action-copying behavior must remain outside active scoring until patch dependency is separated.

It must prove that diagnostic-only and future factors are excluded from active complete-vehicle scoring. SAR structure, uncertainty, final arbitration, visibility, missing extent, visible/full-center offset, and near-field cues must not leak into Phase4 scoring through proxy fields.

It must prove that fixed priors can explain something meaningful before learned weights are introduced. If the model only works after tuning, calibration, or OOF learning, then the project has not yet shown that the proposed factor structure is physically and scientifically justified.

Only after these points are demonstrated should the project consider learned weights, OOF calibration, or selector-prototype work.
