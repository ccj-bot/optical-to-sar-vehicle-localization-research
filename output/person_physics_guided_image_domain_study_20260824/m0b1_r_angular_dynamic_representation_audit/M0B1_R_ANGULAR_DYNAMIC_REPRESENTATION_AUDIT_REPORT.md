# M0B1-R angular dynamic representation audit report

- Primary state: `M0B1_R_INTERVAL_OPERATOR_SEMANTIC_MISMATCH_CONFIRMED`
- Frozen predecessor remains: `M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT`
- M0B2: not entered
- Cross-modal discrimination: not executed
- Reference/manual identity used: no

## Exact frozen operator

For `I_t=[L_t,U_t]`, frozen M0B1 implements:

`Delta I_all=[L2-U1,U2-L1]`.

This is the possible displacement set from any source-support point to any
destination-support point.  It is not a whole-support translation-uncertainty
interval unless an additional correspondence model is supplied.

With `c_t=(L_t+U_t)/2` and `h_t=(U_t-L_t)/2`:

`Delta I_all=[Delta c-(h1+h2),Delta c+(h1+h2)]`.

Thus old determinate direction requires `abs(Delta c)>h1+h2`, equivalently
`eta>1` for `eta=abs(Delta c)/(h1+h2)`.

## Eta and observability

| scope | N | eta_min | eta_median | eta_p90 | eta_p95 | eta_max | fraction_eta_gt_1 | fraction_eta_gt_0_5 | fraction_boundary_coherent |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0B1 bank rows | 11252 | 0.231240 | 0.343619 | 0.375796 | 0.435229 | 0.618940 | 0.000000 | 0.004977 | 1.000000 |
| Deduplicated optical pair signatures | 183 | 0.231240 | 0.328519 | 0.375796 | 0.436632 | 0.618940 | 0.000000 | 0.027322 | 1.000000 |

`eta>1` is reported only as the old operator's mathematical observability
condition.  It is not a tuned threshold.

## Representation comparison

| operator | state | N | fraction |
| --- | --- | --- | --- |
| FROZEN_ALL_PAIRS_SUPPORT_DIFFERENCE | OPTICAL_DIRECTION_INDETERMINATE | 183 | 1.000000 |
| CORRESPONDING_BOUNDARY_SHIFT | COHERENT_POSITIVE_SHIFT | 183 | 1.000000 |
| GEOMETRIC_INTERVAL_MIDPOINT_DESCRIPTOR | MIDPOINT_POSITIVE | 183 | 1.000000 |
| SUPPORT_WIDTH_DEFORMATION_DESCRIPTOR | SUPPORT_WIDTH_CONTRACTION | 109 | 0.595628 |
| SUPPORT_WIDTH_DEFORMATION_DESCRIPTOR | SUPPORT_WIDTH_EXPANSION | 74 | 0.404372 |

The corresponding-boundary descriptors are `d_left=L2-L1` and
`d_right=U2-U1`.  `d_mid` is only the geometric interval midpoint descriptor.
`d_width=(U2-L2)-(U1-L1)=width2-width1` is shape/support deformation.

## Semantic layer finding

- A, spatial support extent: the optical bbox-derived interval width.
- B, measurement uncertainty: not provided by that width in the M0B1 bank.
- C, temporal translation: corresponding-boundary and midpoint changes.
- D, shape/width deformation: boundary disagreement and `d_width`.

M0B1 used A inside the all-pairs possible-displacement radius as though it
bounded B for motion-direction observability.  The code correctly answered the
question posed by that operator, but that operator is semantically broader than
whole-support translation and therefore suppresses short-time direction.

## Mapping direction semantics

Frozen `theta=a*x+b` slope is `0.026665364437`
deg/px and positive.  All reviewed frozen slope-table entries are positive:
`True`.  Slope magnitude uncertainty
changes angular magnitude; a slope-sign reversal would be required to reverse
direction sign.  No new mapping was fitted.

## Bottleneck hierarchy

1. `REPRESENTATION_OBSERVABILITY`: among 11252
   records already passing same-fragment and distinct-sample gates, frozen
   all-pairs determinate direction is 0;
   corresponding-boundary coherent rows are
   11252.
2. `RAW_FRAGMENT_CONTINUITY`: remains an upstream availability loss of
   46334 frozen-bank records.
3. `SAME_SAMPLE_TEMPORAL_SAMPLING`: remains an upstream availability loss of
   8674 records.
4. `SYNC`: remains `NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED` and was not calibrated.
5. `MAPPING_MAGNITUDE`: affects magnitude after direction is represented; it
   is not the leading explanation for zero sign observability with positive
   slope.

## SAR structural diagnostic

Optical recovery gate: `PASS`.  SAR-side output
was materialized: `True`.  It contains only
q95 corresponding-boundary/midpoint/width structural states and split/merge
degree descriptors.  It does not compare optical and SAR states and does not
make a cross-modal claim.

## Final judgment

`M0B1_R_INTERVAL_OPERATOR_SEMANTIC_MISMATCH_CONFIRMED`

M0B1 successfully diagnosed that the current all-pairs support interval
operator is unobservable for short-time motion direction; the new
representation requires an independently versioned validation.  The frozen
M0B1 negative result remains unchanged.

Stop.  No M0B2, cross-modal discrimination, magnitude fitting, pruning,
identity, tracking, factor graph, P2, or final localization was executed.
