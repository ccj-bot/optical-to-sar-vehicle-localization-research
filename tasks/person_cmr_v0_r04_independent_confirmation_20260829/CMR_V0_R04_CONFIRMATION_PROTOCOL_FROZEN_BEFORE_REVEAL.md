# CMR-v0 R04 independent confirmation protocol

- Stage: `CMR_V0_R04_INDEPENDENT_CONFIRMATION`.
- Role: one-shot held-out-run confirmation, not mechanism development.
- Confirmation run: `R04ZF` only.
- Development runs: R01ZF/R02ZF/R03ZF are not re-evaluated here.
- Mechanism source: frozen CMR-v0 runner and specification from CMR-D0.
- R04 outcome reveal before evaluator/control freeze: prohibited.

## Frozen mechanism

The confirmation imports the frozen CMR-D0 mechanism implementation without
changing GMC, deterministic holdout/P90 uncertainty, corresponding-boundary
optical residuals, frozen-P0 q95 support warp, SAR residual states, topology,
censoring, timing, or categorical cross-modal relation rules.

Confirmation-only diagnostic descriptors may record the natural sign of a
continuous midpoint estimate as positive leaning, negative leaning, or exactly
near common.  They are descriptive and never replace frozen categorical states.

## Hard calculation gates

Only missing/corrupt required inputs, non-distinct temporal observations,
missing P0/q95/topology, illegal geometry/time interfaces, or a requirement for
forbidden reference may prevent calculation.  Weak, unresolved, deformation,
censored, likely, and high-uncertainty observations remain in the denominator.

## Evidence profiles

Each hypothesis retains optical observed/common/residual boundary descriptors,
common uncertainty, SAR predicted/observed support boundaries, P0 uncertainty,
soft overlap, width/deformation, topology, censoring, frozen categorical states,
and descriptive leaning states.  No weighted scalar score is constructed.

The four baseline profiles are:

1. `SAR_ONLY`: static pixel shell-region feasibility; all feasible alternatives
   remain admissible and no hidden morphology score ranks them.
2. `SAR_PLUS_SCENE_COMMON`: frozen-P0 support profile.  Pairwise preference is
   declared only by non-weighted Pareto dominance of soft IoU, source retention,
   and destination explained fraction.
3. `SAR_PLUS_BRANCH_RELATIVE_RESIDUAL`: frozen concordant/contradictory/weak/
   structural relation plus continuous leaning diagnostics.
4. `SAR_PLUS_COMMON_PLUS_RESIDUAL`: the scene-common and branch-relative profiles
   are reported jointly; disagreements are preserved rather than averaged.

## Matched controls frozen pre-reference

For every potential static hypothesis, up to five alternatives sharing the same
window, raw fragment, and source q95 region are selected before mechanism output
and before reference reveal.  Matching is lexicographic and uses only frozen
structural fields: destination boundary/truncation state, local shell-region
degree, log pixel-area difference, angular-width difference, angular-midpoint
difference, and deterministic ID order.  Supported status, target ID, CMR
relation, residual values, overlap outcome, and manual reference are forbidden.

The same frozen pair bank supplies matched wrong alternatives after reveal and
reference-free structural controls when neither endpoint is reference-supported.

## Candidate separation

Frozen strict relation levels are `SUPPORTIVE`, `UNRESOLVED`, and `OPPOSING`.
Natural-sign leaning provides a separate descriptive level with no threshold.

- `STRONG_SEPARATION`: supported is strictly supportive and alternative opposing.
- `ASYMMETRIC_SEPARATION`: one strict level of supported advantage.
- `TENDENCY_SEPARATION`: strict levels tie, but natural-sign leaning favors supported.
- `NO_SEPARATION`: evidence profiles do not distinguish the pair.
- `REVERSED_SEPARATION`: the wrong alternative receives the stronger profile.

## Strict SAR-edge outcomes

- `SAR_EDGE_RESCUE`: strong branch-relative separation newly favors the supported
  edge when scene-common evidence was ambiguous or favored the wrong alternative.
- `CONFIRMATION`: scene-common already favors the supported edge and residual
  evidence does not reverse it.
- `HARM`: the combined residual profile favors the wrong alternative.
- `CONFLICT`: scene-common and branch-relative evidence materially disagree
  without a correct strict resolution.
- `NO_INFORMATION`: no strict new distinction is formed.

Graded separation is always reported alongside strict outcomes.

## Grounding layers

No authoritative confirmed raw-fragment identity is assumed.  The strict branch
layer reports `STRICT_BRANCH_SPECIFIC_EVALUATION_UNAVAILABLE` unless a genuine
confirmed relation exists.  Existing frame-level geometric assignments may be
used only as `OFFLINE_LIKELY_SUPPORTED_EXPLORATORY_EVALUATION`; unresolved or
conflicting branches remain visible and are never deleted.

## Independence and clustering

R04 is one held-out run, not multi-run generalization.  Results are summarized by
SAR frame pair, raw fragment, reference target, deterministic 25-frame temporal
block, and full run.  Leave-one-target-out and leave-one-temporal-block-out
summaries are descriptive robustness views, not independent trials.

## Visual confirmation

Sixteen deterministic reference-conditioned case categories are requested.
Missing categories are `CATEGORY_NOT_OBSERVED`; no case is fabricated.  Visual
review can record `HUMAN_OBSERVABLE_METHOD_UNRESOLVED`,
`AGGREGATE_POSITIVE_VISUALLY_AMBIGUOUS`, or another method-reality discrepancy,
but cannot trigger R04 mechanism repair or rerun.

## Prohibitions after reveal

No mechanism, threshold, uncertainty, timing, P0, q95, topology, branch
construction, subset, rescue definition, control rule, or evaluator change is
allowed after reference reveal, except a separately evidenced implementation
bug, frozen-contract mismatch, corrupt file, or invalid index.  No weighted
score, classifier, pruning, tracker, Hungarian assignment, identity inference,
factor graph, magnitude regression, P2, final center, or final box is permitted.

