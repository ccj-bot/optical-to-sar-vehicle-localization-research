# CMR-v0 R04 independent confirmation report

- Run: `R04ZF`, one held-out run.
- Mechanism changed after reveal: `NO`.
- Eligible windows / branches: `98 / 166`.
- Reference-supported SAR edges: `3`.
- Supported-vs-matched-wrong comparisons: `6`.

## Observability

CMR produced `98` common-motion windows, `166` optical branch residuals, `36680` unique SAR P0-relative edges, and `37440` cross-modal evidence profiles.  Weak, deformation, censored, ambiguous, and high-uncertainty observations remain represented.

## Candidate separation

- Windows with at least one strong/asymmetric/tendency separation: `1` of `2` reference-evaluable windows (`1` of `98` eligible CMR windows overall).
- Pair counts: `STRONG=0`, `ASYMMETRIC=0`, `TENDENCY=2`, `NO_SEPARATION=2`, `REVERSED=2`.
- Strict unresolved but meaningful tendency pairs: `2`.
- All six evaluated pairs come from one target (`R04ZF_SARPERSON03`), one temporal block (`R04_BLOCK_06`), and two adjacent SAR frame-pair windows. Candidate separation is therefore observed but not stable across independent R04 target/temporal clusters.

## Incremental SAR-edge information

- Strict outcomes: `SAR_EDGE_RESCUE=0`, `CONFIRMATION=4`, `HARM=2`, `CONFLICT=0`, `NO_INFORMATION=0`.
- Scene-common preferences: `{'SCENE_COMMON_PRIMARY_PREFERRED': 6}`.
- SAR-only remains static-feasibility ambiguous by design; it does not use a hidden morphology ranker.
- The scene-common component contributes the consistent supported-edge preference in all six comparisons. Branch residual contributes two tendency-only distinctions, two no-separation results, and two reversed/harmful distinctions. There is no strict residual concordance or contradiction in R04 because every optical branch remains categorical common-compatible under the frozen uncertainty.

## Branch specificity

- Strict result: `STRICT_BRANCH_SPECIFIC_EVALUATION_UNAVAILABLE` because no authoritative confirmed raw-fragment identity exists.
- Offline likely-supported exploratory comparisons: `6`.
- Unresolved/conflicting grounding comparisons retained: `0`.

## Reference-free controls

- Structurally matched reference-free pairs: `186350`.
- Strict relation-profile difference fraction: `0.254767909847062`.
- Leaning-profile difference fraction: `0.3083391467668366`.

## Visual review

Deterministic cases are materialized in `r04_visual_case_registry.csv` and `R04_CONFIRMATION_CASE_CONTACT_SHEET.jpg`; `8/16` categories are observed. Direct multimodal review is recorded in `CMR_V0_R04_MULTIMODAL_VISUAL_REVIEW_LEDGER.md` without changing or rerunning CMR-v0.

- F157 -> F158: the reference-supported two-lobed q95 response is visually continuous and strongly covered by the frozen prediction, while reviewed wrong alternatives have zero common-support overlap. This agrees with the primary SAR explanation, but the positive attribution to branch residual is visually ambiguous because scene-common already makes the same selection and strict residual relations are unresolved.
- F162 -> F163: the reference-supported two-lobed response remains visually much more plausible than the tiny zero-overlap control, yet residual sign gives the control stronger support and produces `HARM`. This is `HUMAN_OBSERVABLE_METHOD_UNRESOLVED` and a `METHOD_REALITY_DISCREPANCY`, plausibly arising from deformation/boundary representation, topology, timing uncertainty, raw-fragment grounding limits, and optical-SAR projection mismatch.

## Route decision

- Primary: `KEEP_CMR_AS_NONDECISIVE_DYNAMIC_EVIDENCE`.
- Secondary research action: `REDESIGN_BRANCH_RESIDUAL_ON_NEW_DEVELOPMENT_DATA`.
- Current usable contribution: retain the scene-common component as a SAR-explanation prior; do not use R04 branch residual to prune, rank to one candidate, assign identity, or proceed automatically to multi-hypothesis reasoning.

R04 contains limited real profile separation, but not a cluster-stable or strictly grounded branch-specific gain. The branch residual is informative as a diagnostic descriptor and is sometimes directionally helpful, but it is also harmful in the second evaluable window and its positive rows are not independent of scene-common. Any redesign must use development data or a new development pool; R04 remains sealed confirmation evidence.

## Non-claims

No weighted score, pruning, tracker, assignment, runtime identity, factor graph, P2, final SAR center, final SAR box, physical PERSON velocity, platform trajectory, or synchronization calibration is produced.
