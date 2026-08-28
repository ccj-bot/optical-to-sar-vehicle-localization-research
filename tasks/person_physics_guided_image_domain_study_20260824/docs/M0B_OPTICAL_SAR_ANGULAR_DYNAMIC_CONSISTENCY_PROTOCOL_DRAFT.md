# M0B Optical-SAR angular dynamic consistency protocol draft

- Document date: 2026-08-28
- Status: `DRAFT_NOT_EXECUTED`
- Depends on: `M0A_R_TRANSPORT_VALID_BUT_PERSON_SPECIFICITY_NOT_ESTABLISHED`
- Frozen M0A remains: `M0A_REGION_SUPPORT_TRANSPORT_WITH_P0_GAIN`
- Main optical object: `raw_track_fragment_id`
- Main SAR object: q95 response-region support with q97.5 core and q90 envelope
- Prohibited in this draft: execution, timing fit, tracker, unique path,
  assignment, Hungarian, scalar weighted score, classifier, factor-graph
  message passing, SAR box, or final localization

## 0. Core question

M0B asks only:

> Does runtime-legal raw optical-fragment angular dynamics add incremental
> discrimination beyond frozen SAR-only temporal transport and shell-region
> topology evidence?

It does not ask whether optical pixel velocity equals SAR pixel velocity, and it
does not assume:

`delta_theta_SAR = k * delta_theta_optical`.

Optical retains authority only over nominal time and azimuth support. SAR
retains range and final localization authority.

## 1. Why M0B is allowed but not yet established

M0A-R preserves a useful SAR prerequisite:

- supported q95 transport median P0 retention is `0.9093`;
- median P0-minus-ZERO is `+0.0550`;
- leave-one-frame-pair-out keeps median P0 retention above 0.5 and median delta
  positive.

But M0A-R also establishes the limits that M0B must inherit:

- only three supported frame-pair clusters exist;
- all six supported base edges are shared by two target references;
- no PERSON-exclusive temporal positive exists;
- deterministic reference-free controls also show q95 persistence and positive
  common-registration gain;
- q95 is a frame-relative percentile representation, not PERSON confidence;
- correlated retention/IoU/explained-fraction columns are not separate evidence
  families.

Therefore M0B is a development diagnostic of incremental information, not a
P1/P2 confirmation experiment.

## 2. Current materialized interface facts

The following facts come from current code/schema/materialized artifacts and
must be re-hashed before any future execution:

1. R02 M0A contains 22 adjacent SAR lag1 pairs, F472-F494.
2. The optical clock is nominal index/FPS time at approximately 18 FPS; SAR is
   30 FPS. Strict hardware synchronization is not calibrated.
3. Under the existing `SAME_FRAME` raw-fragment shell materialization, the 22
   SAR pairs contain 66 common-fragment pair instances:
   - 37 use two distinct optical timestamps;
   - 29 repeat the same optical observation at both SAR endpoints.
4. Thirteen of 22 SAR pairs have at least one distinct optical step. Nine pairs
   have common fragments but only repeat the same nominal optical sample.
5. The three post-reference M0A supported frame pairs F472-F473, F482-F483 and
   F487-F488 all happen to have distinct optical steps. This is a post-reference
   fact and must not be used to choose eligible pairs or timing rules.
6. `optical_person_id` includes full-run stitching/assignment and short-gap
   interpolation. It is an offline continuity proxy, not the M0B runtime object.

Critical rule:

> Reusing the same optical timestamp at two adjacent SAR frames is
> `OPTICAL_DELTA_UNAVAILABLE_DUPLICATE_NOMINAL_SAMPLE`, not zero optical motion.

## 3. Canonical objects and hypothesis graph

### 3.1 Optical observation

For each detected raw fragment observation:

`O_i(t_o) = {raw_track_fragment_id, timestamp_ms, bbox_x1, bbox_x2}`.

The guard-free angular interval is:

`I_o(t_o) = [a*bbox_x1+b, a*bbox_x2+b]`.

Use the current frozen mapping only:

- `a = 0.02666536443690682 deg/px`;
- `b = -45.502258572693094 deg`.

The guarded/clipped interval is retained only for hard shell feasibility. The
guard-free interval is used for angular dynamics, because the fixed guard is a
design support and not a statistical confidence interval.

The interval midpoint is a descriptor, not true PERSON bearing.

### 3.2 SAR observation

For each frame and q95 region:

`R_j(t) = {q95 mask, q97.5 core, q90 envelope, theta span, range span,
morphology, boundary, topology}`.

Region ID has frame-local scope. It is not a cross-frame identity. Region
centroid or midpoint is only a shape descriptor.

### 3.3 Static explanation node

Define:

`H_t(i,j) = raw fragment i is geometrically compatible with SAR region j at t`.

`H_t(i,j)` exists only when the current raw-fragment guarded shell and q95
region have a true pixel-level shell-region intersection. It is an explanation
hypothesis, not PERSON truth.

### 3.4 One-step dynamic explanation

For adjacent SAR frames:

`D_t(i,j,k) = H_t(i,j) + H_(t+1)(i,k) + frozen M0A edge j->k`.

All legal `D_t` are retained. One-to-many, many-to-one, split-like, merge-like,
weak and recovery-compatible states remain possible. No unique path is chosen.

### 3.5 Two-transition local motif

Magnitude-order and monotonicity require at least two distinct increments. A
secondary object may enumerate every legal three-frame local motif:

`M_t(i,j,k,l) = D_t(i,j,k) + D_(t+1)(i,k,l)`.

This is not a tracker: all legal motifs are materialized, none is selected, and
the object is limited to two adjacent lag1 transitions. If this distinction
cannot be enforced cleanly in code/schema, magnitude-order is marked
`NOT_EXECUTABLE_IN_MINIMAL_PILOT` instead of introducing path logic.

## 4. Hard feasibility constraints

Hard constraints answer whether a hypothesis can be evaluated. They do not
subtract a score.

A static or dynamic hypothesis is infeasible when any required condition is
true:

1. raw detected fragment observation is absent under the predeclared timing
   condition;
2. source or destination guarded shell has no valid pixel intersection with the
   proposed q95 region;
3. frozen P0 pair/model is unavailable or `pair_comparable=False`;
4. q95 source or destination region/mask is absent;
5. P0-warped source support has zero q95 intersection for a claimed SAR
   transport edge;
6. destination valid support denominator is unavailable;
7. required observation is outside fan/common-FoV or fully censored;
8. a timing condition requests an optical/SAR frame outside the fixed data
   bounds.

The following are not hard failures:

- q97.5 core absent while q95 exists;
- q90/q95 morphology changes;
- boundary/truncated support;
- split/merge-like topology;
- repeated nominal optical sample, for `SAR_ONLY` evaluation.

For angular-direction or angular-magnitude evidence, a repeated optical sample
is `EVIDENCE_UNAVAILABLE`, not a feasible zero displacement measurement.

## 5. Evidence-family separation

### 5.1 `F_transport`: SAR temporal transport

Primary directional descriptor:

- frozen P0 q95 source-total retention.

Context descriptors:

- ZERO retention and P0-minus-ZERO;
- destination explained fraction;
- soft IoU;
- q97.5-to-q95/q97.5 retention;
- q90 weak-envelope retention;
- valid transport fraction and transport loss.

The context descriptors share geometry/intersection primitives and must not be
counted as independent votes. In the minimal pilot, only q95 source-total
retention has a predeclared monotone direction within the same source region and
condition.

### 5.2 `F_morphology`: SAR response morphology

Includes q95 area/span, q97.5 core state, q90 envelope, elongation,
boundary/truncation and split/merge-like change. This family explains why
transport may change. It is not automatically monotone: larger area, stronger
core, or more compact shape is not always more PERSON-like.

The minimal Pareto rule therefore uses morphology as a context/stratification
family unless a later protocol independently establishes a directional
likelihood.

### 5.3 `F_topology`: shell-region ambiguity topology

Includes source/destination shell degree, region degree and bipartite component
state. Pixel non-intersection is a hard infeasibility. Degree and component size
describe search burden, but lower degree is not automatically evidence of
correctness. They are reported and matched, not assigned an arbitrary
"smaller-is-better" weight.

### 5.4 `F_angular_direction`: optical versus SAR signed direction

For the guard-free optical interval:

- `delta_o_low = theta_o_low(t2) - theta_o_low(t1)`;
- `delta_o_high = theta_o_high(t2) - theta_o_high(t1)`.

For the SAR q95 interval:

- `delta_s_low = theta_s_low(t2) - theta_s_low(t1)`;
- `delta_s_high = theta_s_high(t2) - theta_s_high(t1)`.

Use deterministic one-pixel numerical-resolution deadbands, separately derived
for optical mapping and local SAR geometry. These deadbands are quantization
guards, not confidence intervals and not detector-jitter calibration.

Direction state for each modality:

- `POSITIVE`: both boundary changes exceed the positive deadband;
- `NEGATIVE`: both are below the negative deadband;
- `INDETERMINATE`: interval boundaries disagree or remain within the deadband;
- `UNAVAILABLE`: repeated optical timestamp, missing endpoint or invalid data.

Cross-modal direction state:

- `CONCORDANT`: both modalities have the same definite sign;
- `CONTRADICTORY`: definite opposite signs;
- `INDETERMINATE` or `UNAVAILABLE`: retained as such.

Only `CONCORDANT` is directionally better than `CONTRADICTORY`.
`INDETERMINATE` and `UNAVAILABLE` are incomparable, not intermediate scores.

### 5.5 `F_angular_magnitude_order`

Absolute angular equality is not assumed. The intercept cancels in optical
displacement, but slope uncertainty remains. Therefore the first protocol must
not minimize `abs(delta_theta_o - delta_theta_s)` or fit a scale factor.

Magnitude evidence is limited to order relations over two distinct adjacent
increments in a legal local motif:

- optical step-magnitude relation: increase / decrease / approximately equal;
- SAR step-magnitude relation: increase / decrease / approximately equal;
- `ORDER_CONCORDANT`, `ORDER_CONTRADICTORY`, `INDETERMINATE`, or `UNAVAILABLE`.

Approximate equality uses only the corresponding numerical-resolution
deadbands. If fewer than three distinct optical observations exist for the same
raw fragment, this family is unavailable. If legal local motifs would require
unique path selection, the magnitude ablation must remain unavailable.

### 5.6 `F_timing_phase`

Timing is uncalibrated. The first M0B does not infer an offset. Timing is a
sensitivity/availability family, not an optimized score.

The fixed conditions are:

1. `NOMINAL`;
2. `SAR_SHIFT_MINUS_1_FRAME`;
3. `SAR_SHIFT_PLUS_1_FRAME`;
4. `OPTICAL_SHIFT_MINUS_1_NOMINAL_STEP`;
5. `OPTICAL_SHIFT_PLUS_1_NOMINAL_STEP`.

For SAR shifts, both endpoints query the nominal optical timestamps associated
with the shifted SAR frames. For optical shifts, both nominal endpoint optical
indices are shifted by exactly one decoded optical frame. Out-of-range values
are unavailable.

Every condition is materialized. No condition is selected as best, and no
result is written back to the sync registry. If nominal is weak while a fixed
shift is strong, the state is `SYNC_DIAGNOSTIC_REQUIRED`.

### 5.7 `F_observability`

Includes duplicate nominal sample, fragment missing/break, boundary,
truncation, P0 availability, fan/common-FoV clipping and display condition.
Unavailable evidence cannot make a hypothesis dominate a hypothesis with
available evidence.

## 6. Pareto and partial-order semantics

The first M0B must not construct:

`Score = w_transport*f_transport + w_angle*f_angle + ...`.

Within the same competition set, hypothesis A dominates B only when:

1. A and B satisfy the same hard-feasibility contract;
2. A is not worse on every evidence family that has a clear predeclared
   direction and is available for both;
3. A is strictly better on at least one such family;
4. no family is `CONTRADICTORY` for A while concordant for B;
5. missing/unavailable evidence does not count as a win.

Competition sets are grouped by SAR frame pair and source q95 region. They keep
all raw optical fragments whose source shell intersects that region and all
legal destination regions. This allows optical-fragment and SAR-edge ambiguity
to coexist without assignment.

Partial orders:

- higher `F_transport` retention is better;
- `ANGULAR_DIRECTION_CONCORDANT` is better than `CONTRADICTORY`;
- `MAGNITUDE_ORDER_CONCORDANT` is better than `ORDER_CONTRADICTORY`;
- indeterminate/unavailable states are incomparable;
- topology/morphology counts do not acquire a direction in this draft.

Outputs are:

- `NON_DOMINATED`;
- `DOMINATED` with explicit dominator IDs and family reasons;
- `INFEASIBLE` with hard-constraint reason;
- `AMBIGUOUS` when multiple non-dominated hypotheses remain.

No unique winner is required.

## 7. Required ablations

### A0. `SAR_ONLY`

- frozen P0 q95 transport as the primary monotone family;
- q97.5/q90 morphology, topology and observability retained as context;
- no optical dynamic descriptor.

### A1. `SAR + ANGULAR_DIRECTION`

- A0 plus definite direction concordance/contradiction;
- duplicate optical samples remain unavailable;
- report changes in dominance graph and non-dominated set.

### A2. `SAR + ANGULAR_MAGNITUDE`

- A0 plus magnitude-order relation from legal two-transition local motifs;
- no absolute cross-modal equality, ratio or fitted scale;
- if eligibility is insufficient, report
  `ANGULAR_MAGNITUDE_ORDER_NOT_IDENTIFIABLE` rather than manufacturing a
  magnitude score.

### A3. `SAR + TIMING`

- materialize A1/A2 independently under all five fixed timing conditions;
- report availability, direction/order state changes, non-dominated count and
  supported/matched retention per condition;
- do not select the strongest shift and do not fit offset/drift.

Optional short-window monotonicity is reported with A2 only when three or more
distinct raw-fragment observations exist. It is not silently substituted for
missing one-step direction evidence.

## 8. Controls and null hypotheses

### 8.1 Frozen wrong SAR explanations

Reuse the frozen M0A matched structural alternatives. They are never rebuilt to
fit M0B results. After reference reveal they remain classified as reference
unsupported, also-supported/shared, or unresolved.

### 8.2 Wrong optical fragments

Before reference reveal, retain all runtime-legal raw fragments. A diagnostic
matched subset may be formed deterministically within the same run/timing
condition by matching:

- endpoint availability;
- fragment duration and observation count;
- source guard-free interval width;
- initial azimuth proximity;
- fan clipping and common-FoV availability.

No stitched parent, manual identity or SAR reference may select a wrong optical
fragment.

### 8.3 Fixed timing nulls

The four non-nominal timing conditions are sensitivity/null conditions. They
cannot become calibration results.

### 8.4 ZERO transport

ZERO retains the same source/destination pools and optical hypotheses. It
remains a SAR registration control, not a competing optical motion model.

## 9. Pre-reference materialization order

Before loading any manual SAR or target-group reference:

1. freeze code, schema, input hashes, timing conditions, deadbands and
   competition-set definition;
2. materialize every raw optical observation interval;
3. materialize all timing-condition endpoint selections;
4. materialize all static `H_t(i,j)` hypotheses;
5. materialize all one-step `D_t(i,j,k)` explanations;
6. if legal, materialize all two-transition local motifs;
7. calculate separate evidence-family states;
8. build A0-A3 partial-order graphs and non-dominated sets;
9. write runtime/pre-reference tables, manifest, ledger and schema validation;
10. freeze output hashes with `reference_loaded=false`;
11. only then load manual SAR reference/offline target grouping for evaluation.

Reference cannot change fragment selection, timing, deadband, hypothesis bank,
edge, motif, evidence direction, partial-order rule or control.

## 10. Post-reference evaluation

The positive term remains:

`REFERENCE_SUPPORTED_DYNAMIC_EXPLANATION`.

It must not be renamed PERSON-specific continuation unless a future dataset
contains independently justified exclusive positives.

For every ablation and timing condition report:

- reference-supported explanation retention;
- matched wrong SAR explanation elimination;
- matched wrong optical-fragment elimination where an authoritative posthoc
  label exists;
- number and fraction of non-dominated hypotheses;
- number of dominators per supported explanation;
- SAR-only destination rank retained as a baseline descriptor;
- changes in partial-order front membership, not a synthetic total rank;
- ambiguity preserved when hypotheses remain incomparable;
- unavailable denominators and reasons.

Statistics must be clustered by:

1. SAR frame pair;
2. raw fragment;
3. source q95 region;
4. SAR base edge;
5. target/reference grouping when meaningful.

The current R02 supported evidence has only three frame-pair clusters; row-level
hypothesis counts cannot be treated as independent samples.

## 11. Deterministic figures

At least ten cases should be frozen before reference reveal where possible:

- definite direction concordance;
- definite direction contradiction;
- duplicate nominal optical sample;
- raw-fragment unavailable/break;
- split-like SAR support;
- merge-like SAR support;
- boundary/truncated region;
- SAR-only ambiguity reduced by direction;
- ambiguity preserved after direction;
- timing-shift-sensitive case;
- magnitude-order eligible case;
- magnitude-order unavailable case.

Every figure must show all competing hypotheses in its competition set, not a
chosen path. Manual references appear only in post-reference copies.

## 12. Outcome states

Allowed development states include:

- `M0B_INCREMENTAL_ANGULAR_DIRECTION_SUPPORTED`;
- `M0B_ANGULAR_INFORMATION_PRESENT_BUT_INCREMENTAL_DISCRIMINATION_NOT_ESTABLISHED`;
- `M0B_RAW_FRAGMENT_AVAILABILITY_LIMITED`;
- `M0B_ANGULAR_MAGNITUDE_ORDER_NOT_IDENTIFIABLE`;
- `M0B_SYNC_DIAGNOSTIC_REQUIRED`;
- `M0B_NO_INCREMENTAL_OPTICAL_DYNAMIC_EVIDENCE`;
- `M0B_INTERFACE_OR_REFERENCE_ORDER_BLOCKED`.

None of these is P1/P2 PASS or final localization.

## 13. Genuine minimal executable pilot recommendation

If a later session explicitly authorizes M0B execution, the smallest defensible
pilot is:

1. R02 F472-F494 only; frozen 22 adjacent lag1 SAR pairs;
2. frozen M0A P0/ZERO matrices, q95 masks, q97.5/q90 context and matched SAR
   alternatives;
3. `RAW_DETECTED_FRAGMENT_ALL` only; no `optical_person_id`;
4. current raw-fragment q95 pixel shell-region topology;
5. primary timing `NOMINAL`, with all four fixed shifts run as separate
   sensitivity tables;
6. enumerate all hard-feasible `D_t(i,j,k)`; no unique edge/path;
7. primary executable increment is `ANGULAR_DIRECTION`;
8. magnitude-order is materialized only for legal three-frame motifs and may
   validly return unavailable;
9. A0-A3 Pareto-front comparison, clustered by frame pair and fragment;
10. freeze before reference reveal, validate independently, then evaluate
    reference-supported and matched explanations;
11. stop after the pilot; do not expand to lag3/lag5, another run, tracker,
    assignment, factor graph, SAR box or timing calibration.

## 14. Explicit non-claims

Even a favorable M0B pilot cannot by itself claim:

- strict optical-SAR synchronization;
- calibrated mapping uncertainty;
- physical PERSON angular velocity;
- PERSON-specific SAR region continuation;
- optical or cross-modal identity;
- reduced physical target ambiguity;
- unique dynamic path;
- final SAR position or box;
- generalization beyond the exposed R02 development slice.

This document is a draft only. M0B has not been executed.
