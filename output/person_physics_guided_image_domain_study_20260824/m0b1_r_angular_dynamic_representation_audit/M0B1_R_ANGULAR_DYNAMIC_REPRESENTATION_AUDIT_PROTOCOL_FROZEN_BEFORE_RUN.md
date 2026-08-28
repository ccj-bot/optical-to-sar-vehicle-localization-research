# M0B1-R angular dynamic representation audit protocol

## 1. Immutable predecessor

- Predecessor HEAD: `752dd28f26666c8e9e08fd94ad0e74a2beebfade`.
- Frozen predecessor state:
  `M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT`.
- M0B1 is not rerun, overwritten, edited, or reinterpreted as PASS.
- This version is diagnostic-only and does not enter M0B2.

## 2. Single objective

Test whether zero determinate optical angular direction in M0B1 is primarily a
representation-semantic consequence of applying an all-pairs spatial-support
difference operator and interpreting it as motion-direction uncertainty.

## 3. Source isolation

The optical representation audit reads only frozen pre-reference M0B1
artifacts and must reject post-reference, manual-reference, physical-target
identity, or assignment fields.  A separate mapping-sign review reads only
aggregate slope values from already frozen R01 mapping tables.  Those tables
have prior manual-correspondence provenance, but neither their labels nor their
outcomes may select, tune, or evaluate the new representation.

Primary record bank:

`dynamic_hypotheses_pre_reference.csv`

Runtime-legal optical dynamic records are exactly rows with:

- `angular_availability_state == ANGULAR_DYNAMIC_AVAILABLE`;
- `source_track_id == destination_track_id`;
- different optical frame/sample index.

All such bank rows are retained.  Because M0B1 duplicates an optical dynamic
pair across SAR base edges and static relations, a second deduplicated optical
pair-signature table is materialized for dependence/accounting transparency.
Neither table is treated as independent statistical sampling.

## 4. Frozen M0B1 operator semantics

For optical spatial support `I_t=[L_t,U_t]`, frozen M0B1 uses:

`Delta I_all=[L2-U1,U2-L1]`.

This is the full possible displacement set between an arbitrary source-support
point and an arbitrary destination-support point.  It is not, without an
additional point-correspondence model, an interval for whole-support rigid
translation uncertainty.

With `c_t=(L_t+U_t)/2`, `h_t=(U_t-L_t)/2`, and
`Delta c=c2-c1`:

`L2-U1=Delta c-(h1+h2)`

`U2-L1=Delta c+(h1+h2)`.

Therefore frozen determinate direction requires:

`abs(Delta c)>h1+h2`.

The dimensionless diagnostic is:

`eta=abs(Delta c)/(h1+h2)`.

`eta>1` only explains the old operator's mathematical observability condition;
it is not a newly chosen threshold or acceptance rule.

## 5. Diagnostic representations

Corresponding-boundary motion descriptors:

- `d_left=L2-L1`
- `d_right=U2-U1`
- `d_mid=((L2+U2)-(L1+U1))/2`
- `d_width=(U2-L2)-(U1-L1)=width2-width1`

Fixed numerical tolerance: `1e-12 degree`.  It is inherited as a machine-level
comparison tolerance and is not fitted or tuned.

Boundary state:

- both greater than tolerance: `COHERENT_POSITIVE_SHIFT`;
- both less than negative tolerance: `COHERENT_NEGATIVE_SHIFT`;
- both within tolerance: `NO_RESOLVED_SHIFT`;
- all other cases: `DEFORMATION_OR_INDETERMINATE`.

Midpoint state is positive, negative, or numerical zero.  The midpoint is
always named `geometric interval midpoint descriptor`, never PERSON true
bearing.

Width state is expansion, contraction, or numerical no-change.  It describes
shape/support deformation, not translation.

## 6. Required optical-only statistics

For the complete runtime-legal bank and the deduplicated pair signatures:

- N, min, median, P90, P95, max of eta;
- fraction `eta>1` and fraction `eta>0.5`;
- frozen all-pairs direction states;
- corresponding-boundary states;
- midpoint descriptor states;
- width/deformation states.

Breakdowns are required by:

- timing condition and raw fragment;
- exact optical frame separation and fixed frame-separation strata:
  `1`, `2`, `3-4`, `5+`;
- exact time separation and fixed time-separation strata:
  `<=60 ms`, `61-120 ms`, `121-240 ms`, `>240 ms`;
- pair-mean optical support width quartile strata.  Quartile cuts are computed
  only from the pre-reference record bank, are descriptive, and do not select
  or tune an outcome.

Additional descriptive diagnostics include absolute midpoint movement,
boundary asymmetry, relative width change, fragment observation count, and
their stratified summaries.  No new pass threshold is learned from them.

## 7. Semantic layers

The report must keep separate:

A. spatial support extent: optical bbox/shell width;
B. measurement uncertainty: not supplied by the bbox extent in this bank;
C. temporal translation: corresponding boundary and midpoint changes;
D. shape/width deformation: `d_width` and boundary disagreement.

If frozen M0B1 uses A as the radius of B for motion direction, this is recorded
as a semantic mismatch.  It does not invalidate the old negative result under
the old operator.

## 8. Optical recovery gate

The SAR structural diagnostic may run only if the optical-only audit finds at
least one coherent corresponding-boundary state in at least two distinct
deduplicated optical pair signatures.  This is a minimal availability gate,
not a performance threshold and not a cross-modal claim.

## 9. SAR-side structural diagnostic

Only after the optical gate passes, deduplicate frozen q95 SAR base edges and
compute:

- `d_left_s=L_s2-L_s1`;
- `d_right_s=U_s2-U_s1`;
- `d_mid_s=((L_s2+U_s2)-(L_s1+U_s1))/2`;
- `d_width_s=(U_s2-L_s2)-(U_s1-L_s1)`.

States are coherent positive, coherent negative, deformation/mixed,
no-resolved-shift, or unavailable.  Source out-degree and destination in-degree
are materialized to mark one-to-one, split-like, merge/shared-like, or combined
topology.  No SAR region is assumed rigid, and no optical/SAR state comparison
or discrimination is performed.

## 10. Mapping direction-only audit

Frozen mapping is `theta=a*x+b` with nominal
`a=0.02666536443690682 deg/px`, which is positive.

- slope magnitude uncertainty changes angular magnitude;
- slope sign uncertainty alone can reverse direction sign.

The audit reports signs from frozen nominal, time-offset-scan, and leave-one-
person-out slope tables.  It does not fit a new mapping and does not use these
tables to select a representation.

## 11. Bottleneck hierarchy

Report separately and hierarchically:

1. `REPRESENTATION_OBSERVABILITY` within already legal same-fragment,
   different-sample pairs;
2. `RAW_FRAGMENT_CONTINUITY` before that gate;
3. `SAME_SAMPLE_TEMPORAL_SAMPLING` before that gate;
4. `SYNC`, which controls sample correspondence but is not calibrated here;
5. `MAPPING_MAGNITUDE`, which affects angular magnitude and not direction sign
   when slope sign is fixed positive.

## 12. Final states and stop

The primary state must be one of:

- `M0B1_R_INTERVAL_OPERATOR_SEMANTIC_MISMATCH_CONFIRMED`;
- `M0B1_R_INTERVAL_OPERATOR_NOT_PRIMARY_BLOCKER`;
- `M0B1_R_OPTICAL_DYNAMIC_OBSERVABILITY_STILL_INSUFFICIENT`;
- or a more precise conservative state justified entirely pre-reference.

If mismatch is confirmed, the correct interpretation is:

> M0B1 successfully diagnosed that the current all-pairs support interval
> operator is unobservable for short-time motion direction; the new
> representation requires an independently versioned validation.

Stop after frozen outputs, validation, report, and log.  Do not enter
cross-modal discrimination, M0B2, magnitude fitting, pruning, identity,
tracking, factor graphs, P2, or final localization.
