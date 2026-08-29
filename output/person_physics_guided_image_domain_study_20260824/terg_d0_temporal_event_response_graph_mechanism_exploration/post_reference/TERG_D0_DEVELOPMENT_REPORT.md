# TERG-D0 development report

Final development decision:
`TERG_V0_MECHANISM_WORTH_FREEZING_FOR_FUTURE_CONFIRMATION`.

This is a mechanism-development result, not confirmation. It applies only to
conditional SAR image-domain response structure. Optical supplies temporal and
azimuth support; SAR retains response-graph, range, and final-localization
authority.

## Evidence base

- Development runs: `R01ZF/R02ZF/R03ZF`; `R04ZF` excluded.
- Natural temporal segments: 38, spanning 5-107 SAR frames.
- Optical segment-track rows: 88.
- SAR graph: 4,328 q95 nodes, 52,460 adjacent-frame edge hypotheses, 3,702
  frozen-P0-supported edges.
- Explanation components: 3,414; multi-frame 1,797; isolated 1,617; full
  segment coverage 255.
- Explanation sets: 88; all set-valued; none selected a unique component.
- GT-blind potential-disambiguation sets: 87/88.
- Offline grounding: 81/88 segment-track rows `LIKELY`, 7 `UNRESOLVED`;
  33/38 segments are wholly `LIKELY`, 3 mix `LIKELY/UNRESOLVED`, and 2 are
  wholly `UNRESOLVED`. No segment is `CONFIRMED`.
- Grounded components: 79 `LIKELY_SUPPORTED_EXPLORATORY`, each belonging to a
  different segment-track set, across 36 unique segments.
- Direct visual review: 14 observed case categories; optical order change and
  multiple-valid/ambiguous grounding were not observed.

## Answers to the required research questions

### 1. Which optical temporal events are genuinely stable and observable?

The strongest primitives are observation presence/lifecycle intervals and
stable relative angular order. Presence occurred in all 88 segment-track rows;
stable order occurred 69 times across 25 segments and two runs. Overlap is also
reliably observable, but as a 16-instance uncertainty state. Boundary/truncation
is a censoring state. These are interval/set-valued observations, not identity
or physical-motion labels.

### 2. Which anticipated events were rejected or downgraded?

No definite optical order-change candidate was observed. Crossing, occlusion,
reappearance and shared identity could not be separately identified from the
available runtime fragments. Approach (53), separation (9), and stable gap (23)
are retained only as endpoint-gap descriptors because projection and bbox
deformation are competing explanations. Optical birth/death remain fragment
boundary hypotheses, not physical entry/exit.

### 3. What are the most reasonable SAR graph nodes and edges?

A node is one per-frame q95, 8-connected response region intersecting a
runtime-visible optical corridor. It carries mask support, angular/range span,
morphology, boundary/truncation and q90/q97.5 context, but is not a PERSON box.
An edge is an adjacent-frame response-continuity hypothesis. Its evidence is
frozen P0 transport, soft support overlap, uncertainty and topology. Unsupported
alternatives remain in the edge table. Only P0-supported edges form connected
temporal explanation components; they are not unique tracks.

### 4. What does P0 actually contribute?

P0 converts a dense static corridor candidate field into a sparse set of
image-domain temporal continuations: 3,702 supported edges out of 52,460
hypotheses. Those edges yield 1,797 multi-frame components, including 312
components with complete P0 continuity. P0 supplies continuity and split/merge
topology only; it supplies neither optical-motion equivalence nor identity.

### 5. Which SAR split/merge states are stably observable?

Frozen P0 topology repeatedly produces 265 split-like and 294 merge-like
component hypotheses across 34/35 segments in R01ZF/R02ZF. The structures are
visually observable as one-to-many/many-to-one response support. They are not
stable PERSON events: the same components often contain deformation, and the
reviewed split/merge components had no reference-supported frames. The frozen
meaning is therefore `SAR_IMAGE_DOMAIN_STRUCTURAL_HYPOTHESIS`.

### 6. Which optical-SAR event relations repeatedly hold?

The repeated relations are broad structural compatibilities: optical presence
can coexist with corridor-contained SAR persistence; stable optical order can
coexist with either determinate SAR order or a shared-response/order-undefined
state; and P0 persistence can retain a plausible SAR explanation through the
optical lifecycle. No narrow event-name mapping repeatedly discriminates.

### 7. Which direct-correspondence hypotheses were disproved?

`OPTICAL_APPROACH -> SAR_MERGE`, `OPTICAL_SEPARATION -> SAR_SPLIT`, optical
birth/death to SAR birth/death, and stable optical order to determinate SAR order
are not supported. Every approach and separation instance co-occurred with the
full dense SAR vocabulary in its explanation set. Of 85 order profiles, 78 were
shared-response/order-undefined, only 5 supportive, and 2 ambiguous. No
contradictory profile was observed, but indeterminacy alone defeats a forced
correspondence.

### 8. How does timing uncertainty enter the event relation?

Event support is an interval, never a required equal frame. D0 stores the base
interval relation (`OVERLAP`, `OPTICAL_BEFORE_SAR`, `SAR_BEFORE_OPTICAL`) and an
uncalibrated `+/-250 ms` descriptor. It does not fit an offset. A known D0
limitation is that the table does not yet materialize the full relation set
after interval widening; TERG-v0 requires that set-valued widening to be
implemented and frozen before future confirmation.

### 9. How is event uncertainty represented?

Each event hypothesis retains type, involved track/branch set, support interval,
observable evidence, uncertainty state, competing interpretations, censoring
and provenance. Relations use categorical partial states, not a weighted score.
`UNRESOLVED`, `AMBIGUOUS`, `DEFORMATION`, `SHARED`, and `CENSORED` remain valid
observations.

### 10. Is relative order more stable than motion magnitude?

Yes, for the development data. Stable optical interval order appeared 69 times
without fitting a magnitude threshold. Earlier residual-magnitude/sign routes
were unstable, while TERG order remained directly observable. However SAR
order was usually undefined because response nodes were shared, so optical
order is a stable prior, not a guaranteed SAR discriminator.

### 11. Does lifecycle provide information?

Yes. It distinguishes 316 complete from 3,098 partial component lifecycle
profiles and exposes long coherent subgraphs that lag-1 rows cannot express.
Lifecycle is one of the strongest compatibility families, but complete coverage
alone does not identify the correct PERSON response.

### 12. Does appearance/disappearance provide information?

Optical first/last observation is useful for defining support and censoring.
Raw SAR component birth/death is weak as a physical event: 2,786 births and
2,741 deaths occur in every segment, largely because q95 components fragment or
start/end inside a segment. They remain component-boundary hypotheses only.

### 13. How is shared response expressed?

A SAR node/component may be contained in multiple optical corridor explanation
sets. The representation keeps the same response node shared rather than
duplicating it into assigned copies. Order becomes
`SHARED_RESPONSE_ORDER_UNDEFINED`; grounding records shared reference frames,
and strict identity remains false.

### 14. Is the graph truly more suitable than lag-1 pairs?

Yes. CMR-eligible distinct-optical-sample runs often leave only 2-3 SAR frames,
whereas natural runtime-visible segments span 5-107 frames. The graph reveals
complete versus partial continuity, one-to-many/many-to-one topology, isolated
alternatives, shared nodes and boundary censoring in one representation. It
does so without forcing a tracker path.

### 15. Were there potential-disambiguation cases?

Yes, but only at development level. GT-blind temporal support reduced the
static component field in 87/88 explanation sets. Post-reference, 79 of those
sets, across 36 segments, contained exactly one
`LIKELY_SUPPORTED_EXPLORATORY` component. The reviewed F0-F15 case retained a
complete 16-frame component and rejected a five-frame partial alternative.
This is potential explanation-set contraction, not confirmation.

### 16. Which cases remain undecidable?

Shared corridors/responses, optical overlap, long dense graphs with many
components, single-reference-hit segments, boundary-censored observations, and
components with no reference intersection remain unresolved. In total 3,217
components have no reference support, 116 inherit unresolved segment grounding,
and 2 have only one reference hit. Human vision also cannot infer PERSON
identity from many shared-response cases.

### 17. How many temporal segments have evaluation grounding?

At the segment-track level, 81/88 rows are `LIKELY` and 7 are `UNRESOLVED`.
At the unique-segment level, 36/38 have at least one `LIKELY` row; 33 are wholly
`LIKELY`, 3 are mixed, and 2 are wholly unresolved. There are zero `CONFIRMED`
segments, so this is reusable exploratory grounding, not truth-complete
evaluation.

### 18. Is branch/PERSON grounding still the main bottleneck?

Yes. The 79 grounded components are offline likely support and never establish
runtime raw-fragment identity. Most components lack reference intersection, the
available reference frames are sparse, and the shared-response case has four
shared reference frames rather than a unique PERSON-specific explanation.

### 19. What are the most promising 2-3 event families?

1. Optical lifecycle/presence plus azimuth corridor support.
2. Frozen-P0 SAR response persistence with complete/partial continuity.
3. Relative topology represented as stable/set-valued optical order plus
   shared-response/order-undefined and split/merge/deformation SAR states.

### 20. Which event families should be abandoned?

Abandon direct optical residual/motion equality, same-name optical-SAR event
mapping, raw SAR component birth/death as physical appearance/disappearance,
and optical order change as a current-data primitive. Keep approach/separation
only as descriptors and do not use them for pruning.

### 21. Is TERG-v0 worth freezing?

Yes, as a mechanism contract. It supplies a coherent non-unique graph,
interval/set-valued events, separated relation families, explicit shared and
censored states, explanation sets, offline grounding, real cases and known
failure cases. It is not ready to claim branch specificity, confirmed
disambiguation or final localization.

### 22. What should future confirmation verify?

On new held-out runs, verify that P0-supported persistence contracts explanation
sets more than matched static-corridor and temporal-null controls while retaining
reference-supported explanations; verify that stable optical order is useful
only when SAR responses are disjoint and otherwise correctly yields
order-undefined; verify split/merge/deformation repeatability without assuming
same-name optical events; quantify raw birth/death false-event behavior; and
validate the fully materialized timing-relation set. Results must be reported by
independent run, target and temporal cluster with complete unavailable and
ambiguous denominators.

## Stop decision

TERG-D0 stops after this freeze. No confirmation, tracker, assignment,
classifier, factor graph, P2, final SAR center, or final SAR box is run.
