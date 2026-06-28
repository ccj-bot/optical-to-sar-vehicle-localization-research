# Optical-to-SAR Factor Graph Research Realignment Memo

Date: 2026-06-29

## 1. Purpose

This memo realigns the project mainline after the Phase4C, Phase4D, geometry add-on, and Phase4D-H audits.

The current fixed A001 candidate-bank factor graph work is useful, but it must be repositioned correctly. It is a selection-layer diagnostic over an externally supplied candidate bank. It is not, by itself, a complete optical-to-SAR migration model.

This memo is documentation-only. It does not add experiments, candidates, rankings, model training, calibration, or active SAR proposals.

## 2. Original Research Question

The original research problem is:

> Transfer an object state observed in optical imagery into SAR imagery and localize the corresponding vehicle state in SAR.

The target output is not merely a selected row from a table. The target is a SAR vehicle localization state, including at least:

- SAR position / center;
- vehicle size or extent;
- orientation or long-axis state when supported;
- visibility / truncation handling;
- uncertainty or multi-hypothesis state when the SAR evidence is ambiguous.

The optical side should provide a prior shell or state prior. The SAR side must still perform the precise localization inside that shell.

## 3. What The Fixed A001 Factor Graph Did

The current fixed-bank factor graph work operates inside this boundary:

- A001 is an externally given discrete candidate menu.
- Each candidate already has `cx`, `cy`, `w`, `h`, `heading`, `r`, `az`, `cross`, and provenance fields.
- The factor graph scores or ranks existing candidate nodes.
- C3 is the current primary fixed selection-layer baseline.
- C4 is a diagnostic branch for top-k / structure-heavy behavior.
- A019 and A021 are joined only after ranking exists for evaluation and failure grouping.

Therefore the factor graph has been doing:

- candidate selection within A001;
- ranking explanation;
- factor prior ownership audit;
- selection-limited vs pool-limited diagnosis;
- source/type post-hoc diagnostics;
- panel-based review of candidate behavior.

This is valid and useful as a selection-layer diagnostic.

## 4. Why This Is Not The Same As The Original Problem

The original problem requires inferring a SAR vehicle state from optical target state, temporal prior, scene geometry, and SAR image evidence.

The fixed A001 factor graph does not solve that full problem because:

- it assumes the candidate search space already exists;
- it does not generate SAR-localized vehicle states from image evidence;
- it cannot find a candidate outside A001;
- it treats A001 heading and size as given candidate attributes;
- it does not establish that A001 rotated boxes align with SAR vehicle long-axis evidence;
- it does not define a full optical-conditioned SAR latent state model.

In short:

> The fixed-bank graph answers “which existing A001 candidate should be selected?” It does not answer “how should the SAR vehicle state be generated or inferred from optical-conditioned SAR evidence?”

This distinction must be explicit in all future method descriptions.

## 5. Correct Positioning Of Phase4C / Phase4D / Phase4D-H

### Phase4C

Phase4C showed that temporal and SAR-structure signals can complement each other inside the fixed A001 bank.

Correct positioning:

- fixed-bank selection-layer evidence;
- useful for factor ownership and score decomposition;
- not proof that the full migration model is solved.

### Phase4D

Phase4D audited the A001 candidate pool ceiling under axis-aligned proxy IoU and center-error diagnostics.

Correct positioning:

- AABB center/size candidate-pool ceiling audit;
- evidence that A001 is not obviously pool-limited under the current AABB proxy metrics;
- not evidence that rotated OBB orientation is solved.

### Phase4D Geometry Add-On

The geometry add-on showed that original Phase4D panels used horizontal / axis-aligned boxes and that `axis_aligned_proxy_iou` does not use candidate heading.

Correct positioning:

- visualization and geometry-semantics boundary audit;
- confirms that Phase4D is an AABB proxy ceiling result;
- not a rotated OBB metric.

### Phase4D-H

Phase4D-H showed that A001 heading for GM_RM017 is a scene-level fixed grid with two values: `[0, 175]`.

Correct positioning:

- heading provenance and orientation-capacity audit;
- evidence that A001 is not orientation-diverse for GM_RM017;
- not evidence that SAR-derived heading or long-axis inference is solved.

## 6. Current Known Conclusions

The safe current conclusions are:

- A001 is not mainly pool-limited under the current AABB center/size proxy ceiling.
- C3/C4 residual failures are mainly selection-limited under that AABB proxy interpretation.
- A001 heading for GM_RM017 is a scene-level fixed grid `[0, 175]`.
- A001 heading is not SAR-derived orientation.
- Current Phase4 results do not prove rotated OBB / SAR long-axis candidate generation.
- Current Phase4 results do not justify active SAR proposal injection into C3/C4.

The unsafe conclusions are:

- “The optical-to-SAR migration problem is solved.”
- “The factor graph localizes vehicles in SAR from image evidence.”
- “A001 proves rotated OBB orientation coverage.”
- “Independent SAR rotated proposal has no value.”
- “C6/C7 or v3 table tuning is the next mainline step.”

## 7. Realigned Mainline

The project mainline should be:

```text
optical target state
    + temporal prior
    + SAR image evidence
    + scene geometry
        -> SAR latent vehicle state
        -> proposal / particles / candidate nodes
        -> factor graph inference
        -> localization output
```

The core research question becomes:

> How can an optical-conditioned prior constrain SAR search while SAR image evidence generates or refines the actual vehicle localization state?

This mainline restores the correct division of labor:

- optical provides a search shell / prior, not the final SAR box;
- SAR image evidence localizes the vehicle inside that shell;
- factor graph inference integrates candidate/proposal nodes and priors;
- evaluation-only audit remains downstream and blocked from inference.

## 8. Module Decomposition

### A. Optical-To-SAR Prior Layer

Role:

- transfer optical target state into SAR search constraints;
- define fan / range / azimuth / temporal prior;
- preserve uncertainty instead of collapsing to one box too early.

Inputs:

- optical target state;
- temporal continuity;
- scene geometry / fan calibration;
- coarse pose and size prior.

Outputs:

- search shell;
- prior distribution over plausible SAR state;
- uncertainty-aware constraints.

Boundary:

- this layer does not decide final SAR localization;
- depth or temporal prediction is a weak aid, not a hard controller.

### B. SAR Observation / Proposal Layer

Role:

- use SAR evidence to propose or support vehicle state hypotheses;
- inspect local SAR energy, contrast, radial profile, axis support, structure support, partial visibility, and fan-edge behavior.

Possible future diagnostic routes:

- local energy peak clusters;
- radial / range profile support;
- long-axis / ridge support;
- connected components;
- rotated OBB windows;
- multi-scale windows inside optical-conditioned shells.

Boundary:

- first implementation must be diagnostic-only;
- generated proposals must not enter C3/C4 active inference without later approval;
- no GT/A021/panel review result may generate or filter proposals.

### C. Factor Graph Inference Layer

Role:

- represent candidate/proposal hypotheses as nodes;
- combine optical priors, SAR observation support, temporal consistency, and geometry constraints;
- perform inference over a state graph rather than patching table-level ranking.

Current fixed-bank C3/C4 belongs here only as a restricted prototype:

- useful for factor ownership;
- useful for selection diagnostics;
- insufficient as the full inference model.

Boundary:

- no C6/C7 tuning now;
- no v3 table-rule tuning now;
- no A001-only ranking patches as mainline progress.

### D. Evaluation-Only Audit Layer

Role:

- join A019/A021 after inference outputs exist;
- compute oracle ceiling, center error, AABB proxy IoU, condition groups, and review queues;
- diagnose failure sources.

Boundary:

- A019 `final_*`, oracle labels, A021 condition/truncation/occlusion, and panel review results must not enter inference;
- source/type provenance remains diagnostic-only unless explicitly approved for a separate study.

## 9. Recommended Phase5 Route

### Phase5A: Optical-Conditioned Search-Space Formulation

Goal:

- define the SAR latent vehicle state and optical-conditioned search shell;
- state the allowed inputs and uncertainty representation;
- separate shell coverage from final localization.

Deliverable:

- design document and field/interface specification.

No experiments yet unless separately approved.

### Phase5B: Independent Diagnostic SAR Proposal Generation

Goal:

- design or implement diagnostic-only SAR proposal generation inside the optical-conditioned search space;
- proposals remain separate from active C3/C4 inference.

Deliverable:

- proposal candidates in a separate diagnostic output bundle;
- provenance and leakage audit;
- no active ranking integration.

### Phase5C: Compare Proposal Ceiling With A001 Ceiling

Goal:

- compare independent diagnostic proposal ceiling against A001 ceiling;
- distinguish center/size coverage, orientation capacity, and partial-visibility behavior.

Deliverable:

- proposal ceiling vs A001 ceiling audit;
- no active inference conclusion unless approved.

### Phase5D: Factor Graph Over Generated Proposals, Only After Approval

Goal:

- test factor graph inference over generated proposal nodes only after Phase5B/C pass review.

Boundary:

- explicit approval required;
- no silent merge into C3/C4;
- no training/calibration unless separately approved.

## 10. Stop / Go / Hold

### STOP

- STOP C6/C7 tuning.
- STOP v3 table-rule tuning.
- STOP further A001-only ranking patches as mainline progress.
- STOP heading convention deep dive for now.
- STOP active SAR proposal injection into C3/C4.

### GO

- GO research realignment.
- GO optical-conditioned SAR state formulation.
- GO diagnostic proposal design.
- GO explicit module/interface boundaries.

### HOLD

- HOLD training.
- HOLD calibration.
- HOLD active proposal integration.
- HOLD generated-proposal factor graph inference until approved.

## 11. Final Reframing

The correct statement for the current project is:

> Phase4 established useful fixed-bank selection-layer diagnostics over A001. It did not complete the optical-to-SAR migration model. The next mainline step is to formulate optical-conditioned SAR state inference, including a SAR observation/proposal layer that can generate or support candidate states before factor graph inference.

This reframing preserves the value of Phase4 while preventing overclaiming.

The fixed A001 factor graph remains useful, but it is now explicitly a diagnostic baseline and selection-layer prototype, not the project’s final architecture.

## 12. Boundary Statement

This memo is documentation-only.

- No experiment was added.
- No candidate was generated.
- No C3/C4 ranking was changed.
- No A001/A005/A019/A021 source file was modified.
- No C6/C7 or v3 rule tuning was performed.
- No model was trained.
- No calibration was performed.
- No active SAR proposal was introduced.
- No stage, commit, or push was performed.
