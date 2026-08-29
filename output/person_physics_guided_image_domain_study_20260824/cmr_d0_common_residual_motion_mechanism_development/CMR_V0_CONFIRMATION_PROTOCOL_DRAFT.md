# CMR-v0 confirmation protocol draft

- Status: `DRAFT_NOT_EXECUTED`.
- Confirmation run: R04ZF only.
- The frozen CMR-v0 implementation and all state definitions must be hashed before any R04ZF mechanism output is generated.
- No implementation repair or threshold change is allowed after R04ZF outcome reveal unless an independently demonstrated implementation bug or data corruption exists.

## Baselines

1. `SAR_ONLY`
2. `SAR_PLUS_SCENE_COMMON`
3. `SAR_PLUS_BRANCH_RELATIVE_RESIDUAL`
4. `SAR_PLUS_COMMON_PLUS_RESIDUAL`

No weighted scalar score is allowed.  Compare categorical admissibility and pairwise explanation states.

## Primary outcome categories

- `RESCUE`: SAR-only ambiguous/wrong and residual adds the correct new distinction.
- `CONFIRMATION`: SAR-only already supports the explanation and residual agrees.
- `HARM`: SAR-only supports the correct explanation while residual favors a wrong one.
- `CONFLICT`: evidence families disagree without a justified winner.
- `NO_INFORMATION`: residual cannot distinguish.

Every hypothesis-reduction statement must be paired with supported retention.  Cluster units include run, SAR frame pair, raw fragment, and target/reference group.

## Route decision

- Stable branch-relative rescue permits later multi-hypothesis reasoning research.
- Scene-common-only value downgrades CMR to a scene-conditioned SAR prior.
- No incremental common/residual information terminates the angular branch-specific route.
