# Purpose

This registry defines how external papers and GitHub repositories should be collected, evaluated, and mapped into the optical-to-SAR vehicle localization research line.

External research is not being collected for a generic literature review. It is being collected to support three specific scientific needs:

- optical-to-SAR vehicle localization under SAR appearance, scattering, shadow, layover, and geometry distortion;
- fixed, frozen SAR candidate-bank selection rather than raw proposal generation;
- hierarchical factor graph reconstruction, where external methods are interpreted as possible evidence sources, factor definitions, ablation structures, or future-branch references.

The registry should help a reviewer decide whether an external method informs the current complete-vehicle fixed-prior route, a diagnostic-only factor, or a future partial-visibility or near-field route. It must not be used to authorize experiments, learned weights, calibration, candidate-bank changes, GM17 replacement, B patch copying, or activation of partial visibility or near-field branches.

GM17 remains a staged evidence source, not the final model template. B patch reproduction remains diagnostic consistency evidence, not physical-model proof. Phase4 fixed-prior revalidation remains a design and audit target until a separate execution round is authorized.

# Search Scope

Future external reconnaissance should search papers, datasets, and repositories in these directions:

- SAR vehicle localization and detection;
- optical-to-SAR transfer or cross-modal localization;
- SAR candidate selection or proposal selection;
- factor graph, CRF, or probabilistic graphical models for tracking or localization;
- track-level vehicle localization;
- SAR scattering, shadow, layover, and vehicle geometry;
- SAR domain adaptation;
- partial visibility, amodal detection, and occlusion;
- near-field SAR or automotive radar geometry.

Search results should be retained only when they can answer a project-specific question. A paper or repository is relevant if it clarifies factor ownership, candidate-selection structure, fixed-prior ablation design, inference/evaluation separation, future partial-visibility modeling, near-field geometry-regime handling, or implementation risks.

# Relevance Questions

Every paper or repository record must answer the following questions before it is treated as useful project evidence:

- What problem does it solve?
- Is it about raw detection, candidate selection, tracking, localization, or evaluation?
- Which project factor does it inform: geometry, direction, source, optical temporal, transition, SAR structure, uncertainty, visibility, missing extent, visible/full-center offset, or near-field?
- Does it require learned weights?
- Does it require candidate-bank changes?
- Does it risk eval-only leakage?
- Is it useful for Phase4 fixed-prior revalidation or only future phases?
- Is it a method reference, implementation reference, dataset reference, or evaluation reference?

A record should be marked future-only if its method depends on learning, candidate generation, partial visibility, near-field geometry changes, or evaluation labels that cannot remain outside inference.

# Paper Record Template

Use this table shape when adding paper entries in a later collection round.

| paper_id | title | year | venue | url_or_doi | task_type | data_type | method_summary | relevant_factor | phase_relevance | candidate_bank_impact | leakage_risk | implementation_available | notes |
|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|

Field guidance:

- `task_type`: raw detection, candidate selection, tracking, localization, evaluation, domain adaptation, factor graph, or geometry modeling.
- `data_type`: SAR, optical, optical-to-SAR, radar, automotive radar, simulated SAR, or mixed.
- `relevant_factor`: use the project factor name when possible, such as `geometry_factor` or `transition_factor`; use `near_field_future_route` for near-field geometry work.
- `phase_relevance`: `Phase4_fixed_prior`, `diagnostic_only`, `Phase7_partial_visibility`, `Phase7B_near_field`, or `future_learning_calibration`.
- `candidate_bank_impact`: `none`, `selection_only`, `proposal_generation_required`, or `candidate_bank_change_required`.
- `leakage_risk`: `low`, `medium`, `high`, or `unknown`, based on whether labels, oracle choices, GT-derived fields, or evaluation outcomes would be used before inference.

# GitHub Repository Record Template

Use this table shape when adding repository entries in a later collection round.

| repo_id | repo_url | project_name | owner | license | latest_checked_commit | task_type | method_summary | usable_component | relevant_factor | phase_relevance | clone_location | reuse_policy | risks | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Field guidance:

- `latest_checked_commit`: record the exact commit checked during reconnaissance.
- `usable_component`: method idea, factor transform, schema idea, visualization, evaluation protocol, dataset tooling, or implementation reference.
- `clone_location`: external repositories must use an external path, not this research repository.
- `reuse_policy`: `read_only_reference`, `method_summary_only`, `possible_reimplementation_after_review`, or `blocked`.
- `risks`: note license uncertainty, unclear provenance, learned-weight dependency, candidate-bank dependency, eval leakage, B patch copying risk, or branch-boundary conflict.

# External Repo Handling Policy

External repositories must not be cloned into this research repository.

Recommended clone location for future authorized reconnaissance:

```text
D:\profile\research\external_repos\
```

External code must not be copied into the main project unless license, provenance, and research need are reviewed. A repository may be used as a read-only method reference, an implementation reference, or a design comparison point, but it must not silently change this project's algorithms, candidate bank, field schema, or Phase4 factor set.

Any future clone should record:

- repository URL;
- owner and project name;
- license;
- exact checked commit;
- clone path outside the main repo;
- reason the repository is relevant to the research spine;
- whether reuse is blocked, summary-only, or eligible for future reimplementation review.

# Method-To-Factor Mapping

External ideas should be mapped to project factors by scientific role rather than by superficial terminology.

| Project factor or route | External method signals to look for | Current use boundary |
|---|---|---|
| `geometry_factor` | Range/azimuth geometry, oriented boxes, fan-polar constraints, scattering-compatible vehicle shape, shadow/layover geometry that can be separated from SAR ambiguity. | May inform Phase4 fixed-prior design only if it does not duplicate SAR structure evidence or require learned weights. |
| `direction_factor` | Heading consistency, signed displacement, direction posterior, escape direction, track-aligned orientation, motion-direction compatibility. | May inform Phase4 fixed-prior design only if separated from source-family trust. |
| controlled non-visible `source_factor` | Proposal provenance, source-family reliability, base/wedge/bidirectional/track-signed candidate trust, non-visible source priors. | May inform Phase4 only for non-visible source families; visible source behavior remains veto/uncertainty-only. |
| `optical_temporal_factor` | Optical track priors, cross-modal temporal transfer, frame-to-frame optical context, soft alignment priors. | May inform Phase4 as a soft prior only; must not generate or overwrite SAR full centers. |
| `transition_factor` | Track continuity, Viterbi/MAP paths, motion smoothness, temporal edge costs, graphical-model transition potentials. | May inform Phase4 edge-cost design only if separated from optical temporal smoothness. |
| `sar_structure_factor` | SAR scattering support, layover structure, shadow geometry, ridges, bright-center patterns, support-vs-artifact cues. | Diagnostic/support-separation review only; not active Phase4 scoring until support and uncertainty ownership are separated. |
| `uncertainty_factor` | Ambiguity modeling, conflict scores, confidence calibration, artifact probability, reject/uncertain routing. | Diagnostic/review only; not active Phase4 scoring, final arbitration, or calibration. |
| `visibility_factor` | Visible fragment support, occlusion reasoning, amodal detection, visible-vs-hidden component evidence. | Future partial-visibility route only; visible support must not generate a full center. |
| `missing_extent_factor` | Missing part estimation, truncation extent, occluded extent, amodal completion evidence. | Future Phase7 schema work only; inactive in complete-vehicle Phase4. |
| `visible_full_center_offset_factor` | Visible-center to full-center offset modeling, amodal center recovery, latent full extent from observed fragment. | Future Phase7 schema work only; inactive in complete-vehicle Phase4. |
| near-field future route | Automotive radar geometry, near-field SAR imaging, range-dependent reliability shifts, geometry-regime state. | Future near-field geometry-regime route only; must not modify the candidate bank or replace the complete-vehicle selector. |

If an external method appears to support multiple factors, the registry should record the primary factor and the double-counting risk. For example, a SAR shadow method may inform geometry, SAR structure, and uncertainty, but Phase4 can use it only after factor ownership is declared.

# Phase4 Use Rules

External ideas may influence Phase4 only in ways that preserve fixed-prior revalidation over the frozen candidate bank.

Allowed Phase4 influence:

- fixed-prior design ideas;
- ablation organization;
- field schema ideas;
- evaluation protocol ideas after inference;
- factor interpretation.

Not allowed in Phase4:

- learned weights;
- candidate-bank expansion;
- B patch copying;
- eval-only fields in inference;
- active SAR uncertainty, final arbitration, or visibility scoring.

External methods that require training, calibration, candidate generation, active SAR uncertainty routing, active final arbitration, partial visibility, or near-field geometry changes should be marked future-only. They may still be valuable for long-term reconstruction, but they cannot alter the current complete-vehicle Phase4 boundary.

# Future Literature Review Outputs

The registry should support these future outputs after a separate paper/repository search round:

- optical-to-SAR method map;
- SAR vehicle localization method map;
- factor graph modeling notes;
- partial visibility future route notes;
- near-field geometry future route notes;
- repo implementation inventory.

These outputs should summarize how external work changes the interpretation of the research spine. They should not become automatic implementation plans. Any proposed implementation must pass license, provenance, inference-safety, candidate-bank, and phase-boundary review first.

# Next Recommended Action

The next recommended action is a separate reconnaissance round that actually searches papers and repositories, fills this registry with initial entries, and optionally clones candidate repositories outside the main repo under:

```text
D:\profile\research\external_repos\
```

That future round should keep this repository unchanged except for reviewed registry updates. It should not run experiments, train, calibrate, copy external code, change the candidate bank, replace GM17, or activate partial visibility or near-field branches.
