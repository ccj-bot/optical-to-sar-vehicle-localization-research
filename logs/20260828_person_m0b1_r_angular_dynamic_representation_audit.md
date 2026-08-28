# 2026-08-28 PERSON M0B1-R angular dynamic representation audit

## Preflight

- Workspace: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Branch: `main`
- Verified starting HEAD: `752dd28f26666c8e9e08fd94ad0e74a2beebfade`
- Frozen predecessor state retained exactly:
  `M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT`
- Existing unrelated dirty worktree: present and preserved.
- `old_work` dependency: `NO`.
- Output root:
  `D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\m0b1_r_angular_dynamic_representation_audit`

## Scope

- Pre-reference, GT-blind representation audit only.
- No M0B2 and no cross-modal discrimination.
- No weighted score, classifier, magnitude fit, pruning, factor graph,
  identity, tracker, or assignment.
- Frozen M0B1 task/output are read-only sources and will not be modified.

## Status

- Exact old operator implementation located and audited.
- Independent protocol written; runner/validator freeze and execution pending.

## Formal execution result

- Stage:
  `M0B1_R_ANGULAR_DYNAMIC_REPRESENTATION_AUDIT`
- Primary state:
  `M0B1_R_INTERVAL_OPERATOR_SEMANTIC_MISMATCH_CONFIRMED`
- Frozen predecessor retained without modification or reinterpretation:
  `M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT`
- Protocol, runner, validator, input-source hashes, and pre-reference outputs
  were frozen independently before/at formal execution.
- Independent validation: `PASS`, `152/152` checks.

## Operator finding

- Frozen M0B1 optical interval: `I_t = [L_t, U_t]`.
- Frozen displacement operator:
  `[L_2 - U_1, U_2 - L_1]`.
- Its mathematical meaning is the possible displacement set from any
  source-support point to any destination-support point. It is not the
  translation uncertainty of the support as a whole.
- With `c_t = (L_t + U_t)/2` and `h_t = (U_t - L_t)/2`, the operator is:
  `[Delta c - (h_1 + h_2), Delta c + (h_1 + h_2)]`.
- The frozen determinate-direction condition is therefore
  `abs(Delta c) > h_1 + h_2`, or `eta > 1`, where
  `eta = abs(Delta c)/(h_1+h_2)`.
- Semantic mismatch confirmed: optical bbox/shell width is spatial support
  extent first; frozen M0B1 used it as if it were motion measurement
  uncertainty. Temporal translation and width/shape deformation must be
  represented separately.

## Optical-only pre-reference audit

- Runtime-legal same-raw-fragment, different-optical-sample bank rows:
  `N=11,252`.
- Deduplicated optical pair signatures: `N=183`.
- Frozen all-pairs determinate direction: `0/11,252`; unique `0/183`.
- Corresponding-boundary coherent shift: `11,252/11,252`; unique `183/183`.
- All coherent optical shifts were positive in this frozen bank.
- Corresponding-boundary descriptors:
  `d_left=L_2-L_1`, `d_right=U_2-U_1`,
  `d_mid=((L_2+U_2)-(L_1+U_1))/2`, and
  `d_width=(U_2-L_2)-(U_1-L_1)=width_2-width_1`.
- `d_mid` is only a geometric interval midpoint descriptor, not PERSON true
  bearing.
- Unique-pair eta statistics:
  min `0.231240`, median `0.328519`, P90 `0.375796`, P95 `0.436632`,
  max `0.618940`; fraction `eta>1 = 0`; fraction `eta>0.5 = 0.027322`.
- Bank-row eta statistics:
  min `0.231240`, median `0.343619`, P90 `0.375796`, P95 `0.435229`,
  max `0.618940`; fraction `eta>1 = 0`; fraction `eta>0.5 = 0.004977`.
- Unique-pair width/deformation state: contraction `109/183`, expansion
  `74/183`.
- Fragment, exact/stratified frame separation, exact/stratified time
  separation, and optical interval-width-stratum tables were materialized in
  the pre-reference output package. All unique pairs are one optical frame
  apart and no more than 60 ms apart.

## Mapping and bottleneck review

- Frozen nominal mapping slope:
  `a=0.02666536443690682 deg/px`, positive.
- Time-offset scan slopes: `51/51` positive.
- Leave-one-person-out slopes: `153/153` positive.
- Slope magnitude uncertainty affects angular magnitude. Only slope-sign
  uncertainty would change direction sign, and no such sign uncertainty was
  observed in the frozen reviewed tables.
- Bottleneck hierarchy is recorded separately as:
  `REPRESENTATION_OBSERVABILITY`, `RAW_FRAGMENT_CONTINUITY`,
  `SAME_SAMPLE_TEMPORAL_SAMPLING`, `SYNC`, `MAPPING_MAGNITUDE`.
- After the fragment + distinct-sample gate, all `11,252` old-operator
  failures are representation failures and all `11,252` are recovered as
  coherent corresponding-boundary shifts.
- Sync remains nominal index/FPS with zero offset unverified; this was not
  used to tune or select the representation.

## Permitted SAR-side structural diagnostic

- Optical recovery gate: `PASS`, so the protocol-permitted q95 SAR region
  structural diagnostic was materialized.
- Unique SAR q95 edges: `51,498`.
- Coherent positive: `24,563`; coherent negative: `24,262`;
  deformation/mixed: `2,673`; unavailable: `0`.
- SAR regions were not assumed rigid. Split/merge/shared structure was
  retained as deformation/mixed where boundary signs disagreed.
- No optical-SAR direction comparison, cross-modal discrimination, final
  localization claim, or representation selection from manual reference was
  performed.

## Outputs and stopping condition

- Report:
  `D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\m0b1_r_angular_dynamic_representation_audit\M0B1_R_ANGULAR_DYNAMIC_REPRESENTATION_AUDIT_REPORT.md`
- Pre-reference summary:
  `D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\m0b1_r_angular_dynamic_representation_audit\audit_summary_pre_reference.json`
- Independent validation:
  `D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\m0b1_r_angular_dynamic_representation_audit\independent_validation.json`
- Task code:
  `D:\profile\research\workspace\tasks\person_m0b1_r_angular_dynamic_representation_audit_20260828`
- Stopped after M0B1_R. M0B2, cross-modal discrimination, weighted scoring,
  classification, magnitude fitting, pruning, factor graph, identity,
  tracking, and P2 were not entered.
