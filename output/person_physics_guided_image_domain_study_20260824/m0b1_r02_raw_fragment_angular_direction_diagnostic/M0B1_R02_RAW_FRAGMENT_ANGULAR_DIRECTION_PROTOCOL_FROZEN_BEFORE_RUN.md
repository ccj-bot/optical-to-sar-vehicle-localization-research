# M0B1 R02 raw-fragment angular-direction protocol

- Stage: `M0B1_R02_RAW_FRAGMENT_ANGULAR_DIRECTION_DIAGNOSTIC`
- Status: `FROZEN_BEFORE_RUN`
- Freeze date: 2026-08-28
- Starting HEAD: `69d7b5c97f391a37f8f986c66739dc982f4a1fb5`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Output: `output/person_physics_guided_image_domain_study_20260824/m0b1_r02_raw_fragment_angular_direction_diagnostic`
- Frozen SAR scope: R02 F472-F494, 22 adjacent lag1 pairs
- Optical interface: `RAW_DETECTED_FRAGMENT_ALL`
- `old_work` dependency: `NO`

## 1. Sole scientific question

This pilot asks only whether guard-free interval angular direction from
runtime-legal raw optical fragments contains incremental discrimination beyond
frozen SAR-only q95 transport and static pixel-level shell-region feasibility.

It does not test magnitude, monotonicity, pruning, ambiguity reduction,
tracking, identity assignment, a unique path, timing calibration, factor-graph
inference, a SAR box, or final localization.

## 2. Supersession of the M0B draft

The earlier M0B draft remains unchanged as design provenance. M0B1 supersedes
only these executable rules:

1. Pareto is not a pruning or ambiguity-reduction mechanism. M0B1 performs no
   Pareto calculation and deletes no hypothesis. A future partial order may be
   descriptive only.
2. M0B1 executes angular direction only. Magnitude/order, monotonicity, and
   admissibility are blocked.
3. Optical and SAR dynamics use support intervals, not midpoint-only motion.
4. Same optical sample and raw-fragment break are unavailable states, not zero
   or contradictory motion.
5. No post-reference correct raw fragment is selected. The current evaluation
   can support a SAR edge while leaving the raw branch unresolved.

## 3. Frozen code hashes

- Runner SHA256:
  `2E047D7379080C09201316EB637390E60590BC53A681D3B979109C86EEC8BEC3`
- Independent validator SHA256:
  `79D7EE38D3E7C1662FC6D72299A8249A5BE952649D0EFB43F51216BD901A1674`

## 4. Frozen input hashes

| Input | SHA256 |
| --- | --- |
| M0A frozen protocol | `0A2116AD3FCBF7C77751B365BFE0063C7FD91A6C77AE64346FAE80D52281E025` |
| M0A P0/ZERO compatibility matrix | `7AEFF02A0026D79A073F35DC2CCEBCE9000433FCE686165EAA80ACD3A906B67A` |
| M0A q95 region nodes | `68A8D80AFD92468829B594B50F2DDD4685F4C3FB9B34DCF98DD666C89CA7F950` |
| M0A matched alternatives | `444A75C272E9A3AF112496C98A861BC6CE162FA763234F6791288150D4E4B65F` |
| M0A pre-reference case registry | `99EC7EA9F9D5D0F2313661140D3BB7F7832487F6982BBC73CF4A6C22647CDCFF` |
| M0A-R frozen protocol | `BA73E645F3342FE0CFE37206E9108F99BC0FA87C541D966A80AB705B793ED6A2` |
| M0A-R summary | `34EC52F09CD29620E88D1BC3BD4ACB3AEE9F7F1BFAB9579A807DDB3E3FC8545D` |
| Current topology protocol | `16F6A4D16AFCC54641F798FB64568D254CAA6AA1106E782B34D9F3C6F189CB37` |
| Current pixel topology edges | `699B140FA93A7BCDB49AE7D4747CEF18E65A6306BAA378C974DD40106F1A0305` |
| Raw optical hypothesis parquet | `15D65A299762E87BFD6F21E811C754D1DF062AC6AFC1840A1C1A9B162AB8B478` |
| Sanitized frame/timing source container | `C39E60EB478FF7D815EFE6984D3BCF36600737E2EC3D1FF76D04020DED54EF7D` |

The response-region mask aggregate remains governed by the frozen topology and
M0A protocols. M0B1 does not regenerate the response field, regions, or P0.

## 5. Actual timing implementation

The current nominal registry stores, for every SAR frame, a nearest optical
decoded frame index and nominal FPS timestamp. `SAME_FRAME` in the previous
topology implementation means exact equality to that nominal optical timestamp;
it is not hardware synchronization.

M0B1 freezes five conditions:

1. `NOMINAL`: use each SAR endpoint's stored nominal optical frame index.
2. `SAR_SHIFT_MINUS_1`: each endpoint queries the nominal optical index of the
   preceding SAR frame. An exposed-slice boundary is unavailable.
3. `SAR_SHIFT_PLUS_1`: each endpoint queries the nominal optical index of the
   following SAR frame. An exposed-slice boundary is unavailable.
4. `OPTICAL_SHIFT_MINUS_1_NOMINAL_STEP`: subtract exactly one decoded optical
   frame index from each nominal endpoint query.
5. `OPTICAL_SHIFT_PLUS_1_NOMINAL_STEP`: add exactly one decoded optical frame
   index to each nominal endpoint query.

Optical-step timestamps are deterministically `round(index * 1000 / 18)` and
must match saved observation timestamps. SAR-shift and optical-shift signatures
are materialized separately even where individual endpoint queries coincide.

No shift is selected, optimized, fit, or written back to a sync registry.

## 6. Static hypothesis feasibility

For every timing condition and endpoint:

1. load all `box_source=DETECTED` observations at the exact decoded optical
   frame;
2. keep each `raw_track_fragment_id` separate;
3. map the detection box to the guard-free interval using only
   `theta = 0.02666536443690682*x - 45.502258572693094` degrees;
4. add the existing fixed ±6 degree guard only for static shell feasibility;
5. clip the guarded interval to the SAR fan;
6. intersect the resulting shell mask with the frozen q95 label mask at pixel
   level;
7. rebuild shell/region degree and bipartite component burden from those pixel
   edges.

Nominal relation keys must exactly reproduce the current frozen
`SAME_FRAME/CURRENT_G6/Q095` topology keys.

The dynamic record bank is constructed for every frozen P0 SAR base edge and
timing condition. When both endpoint relation sets exist, every source-shell
relation × destination-shell relation pair is retained. When a static endpoint
set is missing, one sentinel record preserves the full denominator and records
the hard-infeasibility reason.

No hypothesis is deleted or selected as unique.

## 7. Interval direction semantics

For one raw optical observation:

`I_o(t) = [theta_box_low(t), theta_box_high(t)]`.

The fixed ±6 degree guard is not used in optical dynamics. For two observations:

`Delta_I_o = [low(t2)-high(t1), high(t2)-low(t1)]`.

For a q95 SAR region:

`I_s(t) = [theta_region_min(t), theta_region_max(t)]`

and:

`Delta_I_s = [low(t2)-high(t1), high(t2)-low(t1)]`.

The only tolerance is `1e-12 degree`, used for floating-point comparison and
not tuned from results.

- interval strictly above zero: `*_POSITIVE`;
- interval strictly below zero: `*_NEGATIVE`;
- interval containing zero: `*_DIRECTION_INDETERMINATE`.

Midpoint change is stored only as a descriptor.

## 8. Availability semantics

The following states are mutually explicit:

- `ANGULAR_DYNAMIC_AVAILABLE`: same raw fragment, two distinct optical samples;
- `ANGULAR_DYNAMIC_UNAVAILABLE_SAME_OPTICAL_SAMPLE`: same raw fragment and same
  decoded optical frame at both SAR endpoints;
- `ANGULAR_DYNAMIC_UNAVAILABLE_FRAGMENT_BREAK`: endpoint relations use distinct
  raw fragment IDs;
- `ANGULAR_DYNAMIC_UNAVAILABLE_OBSERVATION`: a fixed timing query is outside
  the exposed registry or has no optical observation;
- `STATIC_SHELL_REGION_INTERSECTION_MISSING`: no legal static endpoint relation;
- `OPTICAL_DIRECTION_INDETERMINATE`: dynamic observations exist but the optical
  displacement interval contains zero.

`UNAVAILABLE` is never converted to zero or contradiction.

## 9. Cross-modal direction descriptor

Only determinate optical and SAR states can be concordant or contradictory.

- same definite sign: `DIRECTION_CONCORDANT`;
- opposite definite signs: `DIRECTION_CONTRADICTORY`;
- any interval contains zero: `DIRECTION_INDETERMINATE`;
- dynamic observation absent: `DIRECTION_UNAVAILABLE`.

No state rejects a hypothesis. Timing, slope uncertainty, split/merge/shared
regions, and unresolved raw-fragment identity forbid a hard rejection rule.

## 10. Direction-blind controls

All control mappings are frozen before reference reveal and do not use angular
direction, manual target IDs, or SAR references.

### A. Frozen SAR matched alternatives

Reuse the frozen M0A matched structural alternatives. Post-reference evaluation
may identify reference-unsupported alternative SAR edges, but does not rebuild
them.

### B. Alternative raw-fragment controls

Within the same timing condition and SAR base edge, a different dynamically
available raw fragment is chosen by minimum static descriptor distance. This
is called a GT-blind alternative raw fragment, not a known wrong PERSON branch,
because no authoritative raw-fragment-to-manual-target evaluator exists.

### C. Static-shell-matched composite controls

For each dynamically available record, match another record in the same frame
pair and timing condition but with a different SAR base edge. Exact then relaxed
bins use only:

- source/destination q95 area stratum;
- source/destination region degree and component shell burden;
- boundary state;
- source/destination shell-width bin;
- initial optical-interval-to-region relation bin;
- intersection coverage and fragment availability only in distance/tie-break.

No control uses the resulting optical/SAR direction state.

## 11. Post-reference boundary

All timing queries, pixel relations, dynamic records, intervals, direction
states, and control mappings must be hashed with `reference_loaded=false` before
opening post-reference M0A files.

Post-reference labels can establish only:

- `REFERENCE_SUPPORTED_SAR_EDGE_RAW_BRANCH_UNRESOLVED`;
- `FROZEN_MATCHED_SAR_NULL`.

The repository has no frozen legal evaluator that identifies the correct raw
fragment for each manual PERSON target without adding an assignment layer.
Therefore the required interface status is:

`M0B1_POST_REFERENCE_RAW_FRAGMENT_EVALUATION_INTERFACE_NOT_ESTABLISHED`.

No reference can relabel, select, or repair a raw branch.

## 12. Reporting and cluster structure

Every timing/evaluation group reports the complete denominator:

- total hypothesis records;
- hard-feasible records;
- dynamic available;
- same optical sample;
- fragment break;
- observation unavailable;
- static shell infeasible;
- direction indeterminate;
- direction concordant;
- direction contradictory;
- direction unavailable.

Separate tables are required by frame pair and raw-fragment cluster. Row counts
are descriptive and are not independent statistical samples. No row-level
p-value or bootstrap is used.

## 13. Frozen outcome rules

`M0B1_ANGULAR_DIRECTION_INCREMENTAL_SIGNAL_OBSERVED` would require all of:

1. at least four determinate supported hypothesis records;
2. determinate supported evidence in at least two frame-pair clusters and two
   raw-fragment clusters;
3. an interpretable supported-versus-frozen-matched and supported-versus-static-
   matched difference in both concordance and contradiction;
4. no single frame pair drives that difference;
5. fixed timing shifts do not provide an equally strong unexplained result;
6. deterministic real cases agree with aggregate direction.

If condition 1 or 2 fails, the primary state is
`M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT`.

If same-sample plus fragment-break states exceed half of supported nominal
records, add `M0B1_RUNTIME_OPTICAL_TEMPORAL_SAMPLING_BLOCKED`.

If determinate evidence exists but supported/null discrimination is weak, use
`M0B1_ANGULAR_DIRECTION_DISCRIMINATION_WEAK`.

Fixed-shift sensitivity can only add `M0B1_SYNC_DIAGNOSTIC_REQUIRED`; it cannot
calibrate timing.

## 14. Deterministic real-case slots

Twelve rules are frozen:

1. supported + concordant;
2. supported + contradictory;
3. supported + indeterminate;
4. same optical sample;
5. raw-fragment break;
6. matched SAR null + concordant;
7. matched SAR null + contradictory;
8. frozen split-like or first multi-topology case;
9. frozen merge/shared supported case;
10. same branch/edge whose state changes under fixed timing;
11. supported primary with a static-shell-matched control;
12. determinate direction with narrowest optical interval.

If a requested category is absent, select the explicitly stated deterministic
fallback and mark `REQUESTED_CATEGORY_UNAVAILABLE_DETERMINISTIC_FALLBACK`.
Never rename a fallback as a concordant or contradictory observation.

Each selected real case is rendered twice: without manual overlay and with
post-reference manual overlay. No unique path is drawn.

## 15. Stop condition

After pre-reference validation, post-reference evaluation, 12 paired cases,
independent validation, report, manifest, README/log update, commit, and push,
stop. Do not automatically enter magnitude, monotonicity, pruning, M0B2,
factor-graph work, P2, or final SAR localization.
