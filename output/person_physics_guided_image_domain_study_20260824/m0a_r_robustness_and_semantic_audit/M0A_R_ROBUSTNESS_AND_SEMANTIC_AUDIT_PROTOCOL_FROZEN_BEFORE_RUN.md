# M0A-R robustness and semantic audit protocol

- Stage: `M0A_R_ROBUSTNESS_AND_SEMANTIC_AUDIT`
- Status: `FROZEN_BEFORE_RUN`
- Frozen at HEAD: `02a112565e72a3aed4ef674377cdb9052a33b33a`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Audit output: `output/person_physics_guided_image_domain_study_20260824/m0a_r_robustness_and_semantic_audit`
- Frozen source experiment: `M0A_R02_LAG1_Q95_REGION_SUPPORT_TRANSPORT_PILOT`
- Frozen M0A protocol SHA256: `0A2116AD3FCBF7C77751B365BFE0063C7FD91A6C77AE64346FAE80D52281E025`

## 1. Scientific role

This is a separate, read-only robustness and semantic audit of frozen M0A
artifacts. It does not rerun or alter M0A. The question is whether the observed
short-term q95 support continuity and limited P0 gain remain interpretable after
cluster dependence, support-size, general-registration, relative-percentile,
shared-positive, topology, and descriptor-dependence audits.

The audit cannot establish Optical-SAR motion consistency because it does not
load or calculate raw optical angular dynamics. It cannot establish PERSON
identity, PERSON-specific region continuation, ambiguity reduction, runtime
optical identity, or final SAR localization.

## 2. Frozen boundaries

The audit must not:

- modify P0, its pair models, warp convention, or validation;
- modify q90/q95/q97.5 thresholds or the frozen `S(x)` field;
- regenerate response regions or masks;
- change reference mappings or matched alternatives;
- delete 1/6/19-pixel cases or any deceptive alternative;
- use a weighted scalar score, classifier, learned fusion, tracker, assignment,
  Hungarian algorithm, unique path, timing fit, lag3/lag5, or SAR box;
- execute M0B.

`old_work` is not read and is not a dependency.

## 3. Authoritative inputs and hashes

| input | SHA256 |
| --- | --- |
| M0A frozen protocol | `0A2116AD3FCBF7C77751B365BFE0063C7FD91A6C77AE64346FAE80D52281E025` |
| pre-reference q95 nodes | `68A8D80AFD92468829B594B50F2DDD4685F4C3FB9B34DCF98DD666C89CA7F950` |
| pre-reference P0/ZERO compatibility matrix | `7AEFF02A0026D79A073F35DC2CCEBCE9000433FCE686165EAA80ACD3A906B67A` |
| pre-reference matched alternatives | `444A75C272E9A3AF112496C98A861BC6CE162FA763234F6791288150D4E4B65F` |
| pre-reference case registry | `99EC7EA9F9D5D0F2313661140D3BB7F7832487F6982BBC73CF4A6C22647CDCFF` |
| post-reference supported explanations | `741C5316C65F66CD1BAC55D5320C22A862EA8766A864675E8B56A9E67B58FC09` |
| post-reference matched evaluation | `850182F2492C633D537EA211408AAB48D4A58E3F10D4EC91FF2497C69452F104` |
| post-reference case registry | `2DB194CF960017AC4A57E07455FD74FCCA843D25F6CCFA831A59E7D1CA16EA27` |
| post-reference summary | `5A6C56A74054BB20DCA94DF157E75D7E87C5EB718A1AE5ED580FC4072C4FA6FD` |
| final validation | `5443FE501312B3177810BAC90478BE96652593C47528183E82C773B0A1CFA55D` |
| offline reference-region evaluation | `4522FE9B65249180B073EA16E87BF11A528DC079B3831348CD7610E3685B7353` |
| manual reference centers | `796F20EB3080C5B45CDEBBCC71584CC95C65691F056D46C4A31704A3D86E8EC7` |

Implementation hashes before the audit:

| implementation | SHA256 |
| --- | --- |
| `run_m0a_r_robustness_and_semantic_audit.py` | `74757A2DA0322BCECBB175B36F199332114A86E6399CACED77B2A35F155F949D` |
| `validate_m0a_r_robustness_and_semantic_audit.py` | `F1A859E9703E629F79288A829CA039533FD50A8D86AB927AE2DAEB9812D84834` |

## 4. Cluster-aware analysis

The primary independent-cluster unit is the SAR frame pair. The audit also
reports source q95 region, supported base edge, and repeated target/reference
grouping. The 30 matched comparisons remain rows nested under six supported
base edges and three frame pairs; they are not treated as 30 independent
observations.

Required summaries:

1. per frame pair;
2. per supported source region/base edge;
3. per repeated shared target group when meaningful;
4. leave-one-frame-pair-out sensitivity;
5. per-edge matched-alternative win fraction before any pair-level summary.

No p-value or row-level bootstrap is used. Inference is explicitly
`DESCRIPTIVE_EVIDENCE / INSUFFICIENT_INDEPENDENT_FRAME_PAIR_CLUSTERS`.

## 5. GT-blind support-size strata

The source population is all 1,064 q95 regions in source frames F472-F493,
before reference labels. Linear empirical Q25/Q50/Q75 are computed and floored
to deterministic integer boundaries. The frozen expected boundaries are:

- `TINY_Q1`: 1-70 pixels;
- `SMALL_Q2`: 71-209 pixels;
- `MEDIUM_Q3`: 210-587 pixels;
- `LARGE_Q4`: at least 588 pixels.

The 1/6/19-pixel cases remain in all tables and deterministic figures. A
stratum with no supported edge is reported as unavailable, never silently
dropped.

## 6. General registration versus PERSON specificity

For every base edge:

`delta_P0 = q95_source_total_retention_P0 - q95_source_total_retention_ZERO`.

The following families are kept separate:

1. `REFERENCE_SUPPORTED_EDGES`;
2. frozen `REFERENCE_UNSUPPORTED_MATCHED_ALTERNATIVES`;
3. `REFERENCE_FREE_STRUCTURAL_HIGH_RESPONSE_CONTROLS`;
4. five size/topology-matched reference-free controls per supported edge.

The full structural control registry is constructed before using transport
metrics: for each pre-reference source region, select exactly one destination
edge minimizing a deterministic no-transport structural-change cost composed
of boundary/truncation mismatch, local topology-bin mismatch, log area ratio,
absolute theta change, and absolute range change. P0/ZERO retention is not in
the selection cost. After selection, reference reveal only stratifies whether
both endpoints are reference-free.

Supported-matched controls are selected from that pre-reference registry in the
same frame pair and source-size stratum. Matching uses only size, boundary,
topology, theta-change, range-change, and area descriptors; it does not use P0,
ZERO, delta, rank, or manual target identity.

A positive background-control delta supports useful common image registration.
It does not establish a PERSON-specific mechanism.

## 7. q95 relative-percentile semantic audit

q95 is a frame-relative percentile superlevel set, so region existence is not
PERSON evidence. The audit reports:

- q95 region count in every frame;
- supported persistence;
- deterministic reference-free structural-control persistence;
- one P0-best-destination-per-source upper bound, labeled as an upper bound and
  not used for delta-P0 specificity claims.

No circular inference from “high response exists” to “PERSON response persists”
is allowed.

## 8. Shared/unresolved positive audit

The only allowed positive term is
`REFERENCE_SUPPORTED_DYNAMIC_EXPLANATION`. For every supported edge the audit
reports supported target count, source/destination local shell degree,
component shell/region counts, component topology, and shared persistence.

Unless an edge supports exactly one target under the frozen reference mapping,
it cannot be called `PERSON-SPECIFIC REGION CONTINUATION`.

## 9. Correlated descriptor audit

The audit records the analytic dependencies:

- retention and destination-explained fraction use the same intersection
  numerator;
- soft IoU uses the same intersection in its numerator and union;
- q90/q95/q97.5 are nested relative-percentile layers of the same frozen
  `S(x)`.

Spearman correlations are descriptive only. Multiple correlated columns do not
count as multiple independent evidence sources.

Evidence must be organized as:

1. SAR response morphology;
2. SAR temporal transport;
3. shell-region topology;
4. optical angular dynamics;
5. timing/phase consistency;
6. observability/boundary/availability.

M0A-R contains no new evidence from families 4 or 5.

## 10. Deterministic real cases

Ten real-case figures are fixed by deterministic rules:

1. one-pixel boundary case;
2. six-pixel maximum P0-minus-ZERO case;
3. nineteen-pixel minimum P0-minus-ZERO case;
4. frozen M0A split-like case;
5. frozen M0A merge-like case;
6. frozen deceptive matched-alternative case;
7. supported shared edge with maximum P0 retention;
8. supported shared edge with minimum P0 retention;
9. reference-free structural control with maximum P0 retention;
10. reference-free structural control with maximum P0-minus-ZERO.

No case is manually substituted after results are viewed.

## 11. Audit-state semantics

Candidate interpretations are selected from materialized evidence, not from a
desire for PASS:

- `M0A_R_TRANSPORT_VALID_BUT_PERSON_SPECIFICITY_NOT_ESTABLISHED`: supported
  continuity keeps positive median retention and delta under leave-one-pair-out,
  while independent clusters remain insufficient and/or positives are entirely
  shared;
- `M0A_R_EFFECT_CLUSTER_SENSITIVE_AND_PERSON_SPECIFICITY_NOT_ESTABLISHED`:
  leave-one-pair-out changes the sign or practical transport interpretation;
- `M0A_R_GENERAL_REGISTRATION_GAIN_DOMINANT`: may be added only if background
  control delta clearly dominates supported delta at the frame-pair level;
- `M0A_R_ROBUSTNESS_SUPPORTED`: requires adequate independent clusters,
  non-shared positives, and supported gain beyond both matched alternatives and
  background controls; it cannot be inferred from row-level 29/30 alone.

The chosen M0A-R state does not overwrite the frozen M0A state. It is an
additional semantic qualification.

## 12. Stop condition

After generating tables, ten figures, the report, manifest, ledger, and
independent validation, stop. Draft M0B separately, but do not run M0B, timing
shifts, optical angular calculations, tracker/path logic, or SAR localization.
