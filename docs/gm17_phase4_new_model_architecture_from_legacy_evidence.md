# GM17 Phase4 New Model Architecture From Legacy Evidence

## 1. Current Correction

The current research direction must be corrected away from the old GM17 candidate-bank workflow.

- A001 and A005 are not the final model.
- A001 and A005 are not proof of physical correctness.
- A001 and A005 are only legacy evidence and a GM_RM017-only pilot container.
- Continuing to build scoring, joins, or patches around A001 and A005 would shift the work back into the old GM17 framework.
- The active research line must now move toward a new model architecture.

The goal is not to reproduce GM17 behavior, tune the old candidate bank, or repair historical patch logic. The goal is to use the legacy artifacts only to expose what was observable, what failed, and what design constraints the new model must handle.

## 2. One-Sentence New Model Definition

The new model is an **optical-to-SAR hierarchical candidate factor graph model**: it performs explainable candidate reasoning by combining SAR candidates, optical temporal priors, geometry, direction, source provenance, and temporal continuity as explicit factors.

## 3. Correct Position of Legacy Assets

### GM17

GM17 is stage evidence and risk exposure. It can show which field families, decision patterns, and failure modes were encountered in the historical workflow. It must not define the final model dependency structure.

### A001

A001 is a frozen old-candidate-generation GM_RM017-only pilot container. It can support field observability audits and minimal pilot reasoning, but it is not a general candidate bank for the new model.

### A005

A005 is an old optical temporal prediction draft. It can only be used as soft-prior evidence. It must not generate, move, overwrite, or validate SAR candidates.

### A019

A019 is manual ground truth and belongs to post-inference evaluation only. It must not be used in active scoring, candidate proposal, prior construction, or inference.

### A021

A021 contains visibility, truncation, and occlusion labels. It belongs to failure grouping and future-route design only. It must not become an active factor until the model has a controlled route for visibility-aware reasoning.

### A013 / B Patch / Selected Behavior

A013, B patch behavior, and historical selected behavior are diagnostic references only. They can help explain legacy decisions and failure cases, but they must not enter active scoring or be copied into the new inference logic.

## 4. New Model Layered Architecture

### Raw Data Layer

This layer contains SAR observations, optical observations, timestamps, frame identifiers, manually maintained evaluation references, and legacy artifact fields. Its job is to preserve provenance and observability, not to make decisions.

### Candidate Proposal Layer

This layer proposes SAR-side candidate locations or regions independently of the old A001 candidate bank. During the GM_RM017-only pilot, A001 may stand in as a frozen proposal source, but the long-term model requires an independent candidate proposal design.

### Candidate State Representation Layer

This layer defines the candidate state used by factors, including candidate geometry, SAR location, heading or direction cues, source provenance, optical prior relation, temporal relation, and missing or uncertain fields.

### Factor Layer

This layer defines factor ownership and evidence boundaries. Each factor must specify its inputs, allowed legacy evidence, prohibited fields, confidence semantics, and whether it is active, near-active, or deferred.

### Graph Inference / Candidate Selection Layer

This layer combines factors into a candidate graph and selects or ranks candidates through explicit inference. It must not copy GM17 score fields, selected behavior, source shortcuts, or patch decisions.

### Post-Inference Evaluation Layer

This layer evaluates predictions after inference. Manual GT, visibility labels, and diagnostic labels belong here unless a later design explicitly promotes a field into a controlled factor.

### Failure-Mode and Future-Route Layer

This layer groups failures and identifies future model extensions, such as visibility-aware inference, missing-extent recovery, near-field treatment, and final arbitration. It must not leak evaluation labels back into active scoring.

## 5. Active and Future Factors

### Active or Near-Active Factors

- `geometry_factor`: candidate-to-expected geometry consistency under a fixed-prior design.
- `optical_temporal_factor`: soft optical temporal prior; stabilizes candidate reasoning without controlling SAR location.
- `direction_factor`: direction or heading consistency when the direction cue is observable and owned by the factor.
- `source_factor`: controlled source-provenance factor; allowed only when source semantics are explicitly defined and not copied from legacy selected behavior.
- `transition_factor`: temporal continuity factor across observations; it should stabilize transitions without overriding SAR candidate evidence.

### Future or Deferred Factors

- `sar_structure_factor`: deferred until SAR-side structure evidence has an independent design.
- `uncertainty_factor`: deferred until uncertainty semantics are defined across candidate and factor levels.
- `visibility_factor`: deferred; A021 can inform future grouping but not active inference yet.
- `missing_extent_factor`: deferred for missing or truncated vehicle extent reasoning.
- `near_field_factor`: deferred for near-field and edge-risk cases.
- `final_arbitration_factor`: blocked until the model has enough controlled factor semantics to justify a final arbitration layer.

## 6. Allowed Uses of A001 and A005

A001 and A005 may be used only for bounded legacy work:

- Field observability audit.
- Legacy behavior decomposition.
- Minimal GM_RM017-only pilot.
- Baseline comparison against a future independent candidate proposal layer.
- Failure-case explanation.

These uses must preserve the distinction between legacy evidence and active model design.

## 7. Prohibited Uses of A001 and A005

A001 and A005 must not be used in the following ways:

- Do not treat them as the final model input specification.
- Do not treat them as a full-scene candidate bank.
- Do not use them directly as proof of physical correctness.
- Do not use A005 to generate, move, or overwrite SAR candidates.
- Do not copy old `score`, `decision`, `source`, or `anchor` fields to reproduce GM17 behavior.
- Do not tune around the old candidate bank.
- Do not extend from A001 or A005 into GM_RM011 or GM_RM019.

Any work that violates these rules is legacy-framework repair, not the new Phase4 model architecture.

## 8. Migration Route From Legacy Pilot to New Model

### Phase4A: Factor Grounding and Observability Audit

Use legacy artifacts only to identify observable fields, missing fields, ambiguous ownership, and factor grounding risks.

### Phase4B: Non-Executable Factor Design

Write factor contracts, ownership maps, allowed evidence rules, blocked fields, and active/deferred boundaries without running selection logic.

### Phase5: Independent Candidate Proposal Design

Design a candidate proposal layer that does not depend on A001 as its structural source. A001 may remain only as a frozen pilot baseline.

### Phase6: Factor Graph Inference Prototype

Build a prototype that performs explicit factor graph reasoning over candidates, with clear factor inputs and no copied GM17 decision behavior.

### Phase7: Post-Inference Evaluation

Evaluate predictions after inference using GT and diagnostic labels. Evaluation data must not influence active candidate scoring.

### Phase8: Visibility / Missing / Near-Field Future Route

Promote visibility, missing extent, near-field, and arbitration work only after their evidence ownership and leakage risks are resolved.

## 9. What Should Stop Now

The following work should stop unless explicitly scoped as a GM_RM017-only legacy pilot:

- Infinite A001/A005 join or scaffold documentation.
- Old-score tuning.
- Treating GM17 patch behavior as model proof.
- Treating candidate-bank management as the main research line.

Stopping these prevents the research from drifting back into the historical GM17 patch path.

## 10. Recommended Next Step

The next document should either define `geometry_factor` fixed-prior design under the new architecture or create a factor ownership map for the optical-to-SAR hierarchical candidate factor graph model.

The project should not continue with a join-integrity audit plan unless the work is explicitly declared as a GM_RM017-only legacy pilot. The immediate priority is to stabilize the boundary between legacy evidence and the new model architecture.
