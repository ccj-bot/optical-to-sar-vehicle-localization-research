# TERG-v0 mechanism specification

Status: `FROZEN_FOR_FUTURE_CONFIRMATION_NOT_CONFIRMED`

## 1. Authority boundary

- Optical authority: runtime-visible raw fragment presence, nominal time,
  guarded azimuth corridor, interval order and uncertainty/censoring.
- SAR authority: q95 response regions, frozen P0 transport, response topology,
  range and any future final localization.
- Offline reference authority: post-reference evaluation only; never runtime
  identity or graph construction.
- Development data: `R01ZF/R02ZF/R03ZF`. `R04ZF` and future confirmation runs
  are excluded from this specification's discovery and rule formation.

## 2. Optical temporal object

`O_i = {fragment_id, presence_interval, angular_corridor(t),
relative_order_set(t), event_hypotheses, censoring, provenance}`.

`fragment_id` remains an anonymous runtime hypothesis. It is not a stable
physical identity. The core optical vocabulary is:

- `OBSERVATION_PRESENCE_INTERVAL`;
- `OBSERVATION_BIRTH_HYPOTHESIS` and `OBSERVATION_DEATH_HYPOTHESIS` as fragment
  boundaries with competing scene-entry/exit, detector and grouping causes;
- `RELATIVE_ORDER_STABLE`;
- `RELATIVE_ORDER_OVERLAP_UNCERTAINTY`;
- `OPTICAL_BOUNDARY_OR_TRUNCATION_STATE`.

`PAIR_GAP_APPROACH_TENDENCY_DESCRIPTOR`,
`PAIR_GAP_SEPARATION_TENDENCY_DESCRIPTOR`, and
`PAIR_GAP_STABLE_DESCRIPTOR` are descriptors only. Optical order change is not
in the frozen v0 vocabulary because no development instance was observed.

## 3. Event hypothesis contract

Every event retains:

1. event type;
2. involved fragment/branch set;
3. temporal support interval;
4. observable evidence;
5. uncertainty state;
6. competing interpretations;
7. availability/censoring;
8. provenance and reference-use flag.

No event is inferred solely by an outcome-tuned scalar threshold. An event may
be set-valued, ambiguous, unavailable, deformed or censored.

## 4. SAR temporal response graph

`G_SAR = (V, E)` is directed in time and remains set-valued.

### Node contract

A node is a per-frame q95, 8-connected response region intersecting an optical
corridor. It may carry mask support, angular/range span, pixel/metric area,
centroid as a shape descriptor, major/minor extent, elongation, q90/q97.5
context, boundary touch and truncation. A node is explicitly not a PERSON box,
physical scattering center, confidence probability, final center or identity.

### Edge contract

An edge is an adjacent-frame response-continuity hypothesis. The complete edge
bank retains both supported and unsupported alternatives. A supported edge
requires the frozen P0 support-overlap primitive and records:

- P0 prediction/uncertainty;
- source retention, destination explained fraction and soft IoU;
- residual/deformation state;
- one-to-one-like, split-like, merge-like, split-and-merge-like or unavailable
  topology;
- boundary/truncation state.

Edges are not tracker assignments. One-to-many and many-to-one edges are legal.

## 5. Explanation-set contract

For each optical temporal object and segment, all P0-connected components inside
the corridor form a plausible explanation set. Isolated nodes remain explicit.
Each component records temporal support, node/edge counts, coverage, split,
merge, deformation and censoring. No component is selected as unique.

The frozen relation families remain separate:

- lifecycle coverage;
- corridor coverage;
- P0 continuity;
- event-time relation;
- relative-order relation;
- topology/shared-response state;
- grounding availability.

No weighted score, pruning or hidden component-pair assignment is allowed.
Relative order is one aggregate relation over two explanation sets, retaining
component counts, pair-space size, common frames and shared-response frames.

## 6. Frozen relation algebra

Allowed primary states include `SUPPORTIVE`, `COMPATIBLE`, `PARTIAL`, `WEAK`,
`AMBIGUOUS`, `CONTRADICTORY`, `UNAVAILABLE`,
`SHARED_RESPONSE_ORDER_UNDEFINED`, and `MULTI_EVIDENCE_CONFLICT`.

Stable optical order does not force SAR order. If the explanation sets share a
response node in a common frame, SAR order is undefined. Split/merge/deformation
are SAR image-domain structural hypotheses and have no compulsory optical event.

## 7. Timing contract and known D0 gap

Event time is an interval. Exact frame equality is forbidden. D0 materializes a
base relation over support intervals and stores `timing_uncertainty_ms=250` as
an uncalibrated descriptor; it does not fit an offset. Before future
confirmation, the implementation must additionally materialize the set of all
possible relations after widening both event intervals by the predeclared timing
uncertainty. If more than one relation remains possible, the output is
set-valued/ambiguous. This implementation gap is frozen as a known requirement,
not silently treated as solved.

## 8. Vocabulary disposition

Core:

- optical presence/lifecycle and stable/set-valued relative order;
- optical corridor support;
- SAR P0-supported persistence;
- shared-response/order-undefined;
- SAR split/merge/deformation structural hypotheses;
- boundary/censoring and unavailable states.

Descriptor only:

- approach, separation and stable gap.

Downgraded or excluded:

- raw SAR component birth/death as physical appearance/disappearance;
- direct same-name optical-SAR event mapping;
- optical order change for the current data;
- motion magnitude/sign equality as the primary cross-modal mechanism.

## 9. Offline grounding

Grounding states are `CONFIRMED`, `LIKELY`, `AMBIGUOUS`, `UNRESOLVED`,
`REJECTED`, and `MULTIPLE_VALID_EXPLANATIONS`. TERG-D0 produced only `LIKELY`
and `UNRESOLVED` segment grounding, and `LIKELY_SUPPORTED_EXPLORATORY` plus
unresolved component states. Grounding may be one-to-many/many-to-many and is
never runtime-legal identity evidence.

## 10. Frozen non-claims and stop boundary

TERG-v0 does not establish intrinsic RCS, recovered physical motion, branch or
PERSON identity, confirmed disambiguation, a unique SAR path, P2, final SAR
center or final SAR box. It does not authorize Hungarian, min-cost flow,
weighted global scoring, a learned classifier, factor-graph inference or a
tracker. The next authorized step is a separately opened, pre-registered
confirmation only.
