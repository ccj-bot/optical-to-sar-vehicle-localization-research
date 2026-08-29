# TERG-v0 future confirmation protocol draft

Status: `DRAFT_NOT_EXECUTED`

## Objective

Test whether the frozen TERG-v0 relation families retain reference-supported
SAR explanations while contracting a static optical-corridor explanation set on
new held-out data. This protocol tests a mechanism; it does not test final
localization accuracy.

## Isolation

1. Use new runs not used in TERG-D0 rule formation. Do not reuse
   `R01ZF/R02ZF/R03ZF` as confirmation.
2. Freeze run split, timing-uncertainty policy, node/edge code, event vocabulary,
   segment construction, controls, case slots and outcome states before loading
   manual SAR references.
3. Materialize and hash all pre-reference graphs, explanation sets, relation
   sets and denominators before reference reveal.
4. Do not modify TERG-v0 after one-shot reveal. Any redesign must return to new
   development data.

## Required pre-reference implementation completion

Materialize the full timing-relation set after interval widening. The base
relation and widened relation set must both be stored. No best offset may be
searched or fitted.

## Confirmation targets

### A. Lifecycle and P0 persistence

Compare frozen P0-supported components against:

- static corridor components without temporal edges;
- zero-transport edges;
- matched temporal permutation/shuffle edges;
- P0-unsupported alternatives.

Report explanation-set size before/after temporal support, reference-supported
explanation retention, complete/partial/unavailable continuity, and independent
run/target/temporal-cluster denominators.

### B. Relative order and shared response

Test the preregistered prediction that stable optical order is supportive only
when SAR explanation sets are disjoint. Shared SAR nodes must yield
`SHARED_RESPONSE_ORDER_UNDEFINED`, not a forced assignment. Report supportive,
ambiguous, contradictory, shared-undefined and unavailable states separately.

### C. SAR split/merge/deformation

Test whether frozen P0 topology yields reproducible image-domain structural
hypotheses across held-out runs. Do not require same-name optical events. Report
their reference support, recurrence across independent clusters, and competing
deformation/boundary interpretations.

### D. Birth/death warning

Quantify how often raw component birth/death corresponds merely to q95
fragmentation, segment boundaries or temporary unsupported transitions. It may
be promoted only if it adds repeatable information beyond lifecycle/persistence
controls without excluding valid explanations.

### E. Potential disambiguation

The primary outcome is categorical explanation-set contraction with retention,
not a weighted score. Report:

- static plausible component count;
- temporally supported component count;
- grounded plausible component count;
- whether every available reference-supported explanation is retained;
- whether contraction repeats across independent targets and temporal blocks;
- unresolved, shared, censored and multiple-valid states.

No single target or temporal block can establish confirmation.

## Matched controls

- corridor-shift controls matched for effective angular burden;
- zero/P0-incorrect transport controls where legal;
- temporal permutation controls with the same node bank;
- P0 edge ablation;
- shared-node-preserving order null;
- complete unavailable-state denominators.

Controls must be frozen from geometry/measurement rules, not chosen after
reference outcomes.

## Confirmation decision language

Allowed outputs include:

- `TERG_V0_STRUCTURAL_COMPATIBILITY_CONFIRMED`;
- `TERG_V0_PARTIALLY_CONFIRMED`;
- `TERG_V0_NONDISCRIMINATIVE`;
- `TERG_V0_HARMFUL_EXCLUSION`;
- `GROUNDING_INSUFFICIENT_FOR_CONFIRMATION`;
- `MULTI_EVIDENCE_CONFLICT`.

Any claim must state the number of independent runs, targets and temporal
clusters. A validator PASS only establishes artifact and protocol integrity.

## Stop boundary

The confirmation task stops after the frozen evaluation and report. It does not
authorize tracker/assignment, weighted fusion, factor graph, P2, final center or
box.
