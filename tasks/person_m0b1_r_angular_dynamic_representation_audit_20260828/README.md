# PERSON M0B1-R angular dynamic representation audit

## Frozen scope

This task is an independent, GT-blind, pre-reference semantic audit of the
frozen M0B1 optical interval operator.  It does not modify, supersede, rerun,
or reinterpret the frozen M0B1 state:

`M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT`

The only question is whether M0B1's zero determinate optical direction is
primarily caused by treating a spatial support extent as though it were a
motion-uncertainty interval.

## Inputs

- Frozen M0B1 pre-reference bank:
  `workspace/output/person_physics_guided_image_domain_study_20260824/m0b1_r02_raw_fragment_angular_direction_diagnostic/dynamic_hypotheses_pre_reference.csv`
- Frozen M0B1 pre-reference summary and protocol.
- Frozen R01 PERSON azimuth mapping tables, used only to audit slope-sign
  semantics.  They do not select or tune a representation.

No `post_reference_*`, manual reference, identity assignment, manual box, or
physical target ID is read by the optical representation audit.  The separate
mapping-sign review reads only aggregate slope columns from already frozen R01
mapping tables; their prior reference provenance cannot select or tune the
representation.

## Operators

For `I_t=[L_t,U_t]`, define `c_t=(L_t+U_t)/2` and
`h_t=(U_t-L_t)/2`.

Frozen M0B1 all-pairs support difference:

`Delta I_all = [L2-U1, U2-L1]`

which equals:

`[Delta c-(h1+h2), Delta c+(h1+h2)]`.

It is determinate only when `abs(Delta c)>h1+h2`.  The audit descriptor is:

`eta=abs(Delta c)/(h1+h2)`.

Independent diagnostic representations:

- `d_left=L2-L1`
- `d_right=U2-U1`
- `d_mid=((L2+U2)-(L1+U1))/2`
- `d_width=(U2-L2)-(U1-L1)=width2-width1`

`d_mid` is only a `geometric interval midpoint descriptor`; it is not PERSON
true bearing.

## Execution

Interpreter:

`D:\MINICONDA\envs\py311\python.exe`

First freeze protocol, source hashes, runner hash, and validator hash:

```powershell
D:\MINICONDA\envs\py311\python.exe run_m0b1_r_representation_audit.py --freeze
```

Then materialize the pre-reference optical audit and, only if the frozen
optical recovery gate passes, the SAR structural diagnostic:

```powershell
D:\MINICONDA\envs\py311\python.exe run_m0b1_r_representation_audit.py --run
D:\MINICONDA\envs\py311\python.exe validate_m0b1_r_representation_audit.py
```

## Prohibited

- weighted score, classifier, magnitude fitting, pruning, Pareto pruning;
- factor graph, identity, tracker, assignment, unique path;
- M0B2 or P2;
- post-reference representation selection;
- cross-modal discrimination or final cross-modal claim;
- modification of the frozen M0B1 task or output.
