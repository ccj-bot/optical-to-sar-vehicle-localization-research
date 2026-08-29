# TERG-D0 development protocol

Status: `DEVELOPMENT_PROTOCOL_ACTIVE_NOT_CONFIRMATION`

## Authority and split

- Cross-modal development runs: `R01ZF`, `R02ZF`, `R03ZF`.
- `R04ZF` remains prior CMR confirmation evidence and is excluded from TERG-D0 discovery, rule formation, case selection, and grounding.
- Runtime optical authority: detected `raw_track_fragment_id` observations and the existing `SAME_FRAME / CURRENT_G6` shell decomposition. Offline stitched/target fields are forbidden during discovery.
- SAR node authority: existing per-frame q95 response regions and masks. A q95 node is an image-domain response region, not a PERSON box.
- SAR edge authority: frozen lag-1 P0 transport, soft support overlap, existing uncertainty, and split/merge-like topology semantics.
- Offline references and frame-level geometric assignments are loaded only after the pre-reference atlas, graphs, events, explanation sets, and hashes are materialized.

## Representation

An optical temporal object retains presence support, raw/guarded angular corridor,
relative interval order, missing/censoring states, and set-valued event
hypotheses. Event time is an interval. `+/-250 ms` is retained only as the
existing uncalibrated timing-uncertainty diagnostic; it is not a fitted offset.

The SAR representation is a directed temporal response graph. Nodes are q95
regions. Candidate edges include all corridor-intersecting adjacent-frame
hypotheses; P0-supported and unsupported alternatives both remain in the
evidence table. Connected temporal components are explanation hypotheses, not
unique tracks.

Cross-modal families remain separate:

- lifecycle coverage;
- corridor coverage;
- P0 continuity;
- event-time co-occurrence/ordering;
- relative-order compatibility;
- topology/shared-response state;
- grounding availability.

No weighted score or forced one-to-one event mapping is permitted.

## Natural segment construction

The old CMR eligible rows are retained as a baseline but are not used as the
segment unit: distinct optical sampling reduces each fragment run to only 2–3
SAR frames. TERG segments instead arise GT-blind from:

- continuous runtime-visible shell presence;
- stable active-fragment plateaus;
- relative-order transitions and overlap intervals;
- SAR split/merge-like topology contexts;
- boundary/censoring contexts.

Long continuous presence is allowed. Review strips sample it without redefining
the underlying segment.

## Development freedom and stop boundary

Vocabulary dispositions are decided from observed repetition and
counterexamples. A primitive may become an event, descriptor, uncertainty
state, or rejected hypothesis. Changes require a representation-change ledger.

TERG-D0 may freeze a mechanism contract only after direct multimodal review and
independent validation. It must then stop. It does not run a new confirmation,
tracker, assignment, classifier, factor graph, P2, final center, or final box.
