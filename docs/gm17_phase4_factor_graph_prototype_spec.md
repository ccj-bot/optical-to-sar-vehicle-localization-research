# GM17 Phase4 Factor Graph Prototype Spec

## 1. Current Position

This document starts the Phase4 factor graph prototype after the Phase4C combined structure+temporal fixed pilot.

It is not a C6/C7 weight-tuning round, not a v3 table-rule search, not training, and not calibration. The purpose is to formalize the next prototype boundary after a pre-registered fixed combination showed complementary signal behavior.

The active scene remains GM_RM017 only. The candidate pool remains the full A001 candidate bank.

## 2. Why Move From Phase4C To A Factor Graph Prototype

Phase4C tested whether two independent signals can complement each other:

- `optical_temporal_factor` keeps useful center stability from the optical temporal prior.
- `sar_structure_factor` promotes better SAR-structure candidates, especially for best-proxy top-k behavior.

The result supports moving to a factor graph prototype because C3 `temporal_guard_structure_promote` was the most balanced variant and `support_factor_graph_combined_pilot=true`.

This does not mean the final model is solved. It means the next safe step is to express the already-tested factors as explicit factor ownership and message boundaries, rather than continuing ad hoc table combinations.

## 3. Candidate Pool Boundary

The prototype must use the full A001 candidate bank for GM_RM017.

Allowed candidate-pool facts:

- A001 is the fixed SAR candidate menu.
- Each candidate keeps its original `candidate_id` and geometry.
- No new candidate is generated.
- No candidate box is moved, filtered, rewritten, or expanded.
- GM_RM011 and GM_RM019 are out of scope until separately approved candidate banks and priors exist.

Forbidden candidate-pool shortcuts:

- Do not use structure-selected rank1 as the candidate pool.
- Do not use best-proxy or best-center candidates as the candidate pool.
- Do not use GT or A021 condition labels to form the pool.

## 4. Factor Ownership

### 4.1 Optical Temporal Factor

Owner: optical-to-SAR temporal consistency.

Allowed inputs:

- A001 candidate coordinates: `r`, `cross`, `az`.
- A005 prediction coordinates: `pred_r`, `pred_cross`, `pred_az`.

Allowed meaning:

- A005 is a soft optical-temporal suggestion.
- The factor can score how compatible an existing A001 SAR candidate is with the A005 prediction.
- It must not create, move, or overwrite candidates.

Blocked inputs:

- Legacy `delta_*_from_pred`.
- `temporal_factor_score`.
- A005 `score`, `lr_score`, or `sar_factor_score`.

### 4.2 SAR Structure Factor

Owner: SAR display-image structure evidence over existing A001 candidates.

Allowed inputs:

- Structure-only S1/S2 output computed over the full A001 bank without GT or A021.
- S1 display-image features: `box_to_background_ratio`, `inside_energy_fraction`, `optional_local_contrast`.
- S2 display-image features: `box_to_background_ratio`, `inside_energy_fraction`.

Allowed meaning:

- The structure factor can promote candidates with stronger local SAR support.
- S1 and S2 remain display/pseudocolor-image factors, not raw SAR physics.

Diagnostic-only:

- S3 and `edge_spillover_ratio` remain diagnostic because the full audit found edge spillover weak as a main active signal.

### 4.3 Combined Factor Baseline

Baseline: C3 `temporal_guard_structure_promote`.

Current fixed combination:

- `0.67 * temporal_rank_percentile + 0.33 * s1_rank_percentile`.
- Lower score is better.
- Tie-break remains stable candidate ordering only.

Prototype implication:

- The factor graph should treat C3 as the starting fixed baseline, not as a tunable weight recipe.
- C3 is a prior baseline for graph structure and factor ownership, not permission to search nearby weights.

### 4.4 Diagnostic Branch

Diagnostic branch: C4 `structure_guard_temporal_soft_diagnostic`.

Use:

- Inspect top-k behavior when structure dominates.
- Preserve C4 as a diagnostic view for best-proxy top20 and failure analysis.

Do not use C4 as the main active conclusion unless a later pre-registered round explicitly changes the objective and boundary.

### 4.5 Evaluation-Only Inputs

A019 and A021 are evaluation-only.

Allowed use:

- A019 may be read only after a prototype output exists, for post-inference metric computation.
- A021 may be read only after a prototype output exists, for post-inference failure grouping.

Forbidden use:

- No A019 `final_*` fields in inference, ranking, tie-breaks, graph factors, or candidate filtering.
- No A021 `condition`, `truncation`, or `occlusion` fields in inference, ranking, tie-breaks, graph factors, or candidate filtering.

## 5. Forbidden Inputs

The prototype must not use these as factor inputs, ranking inputs, tie-breaks, gates, or candidate filters:

- GT or A019 `final_*`.
- A021 condition, truncation, or occlusion labels.
- `candidate_source`, `candidate_detail`, or candidate expansion provenance.
- Legacy score fields: `score`, `lr_score`, `sar_factor_score`.
- Legacy residual fields: `delta_*_from_pred`.
- `temporal_factor_score`.
- selected outputs.
- B patch outputs.
- Oracle ranks, oracle labels, or best-proxy/best-center identity.

## 6. Current Positive Results

From Phase4C:

- C3 `temporal_guard_structure_promote` is the most balanced variant.
- `support_factor_graph_combined_pilot=true`.
- C1/C2 improve combined top-k behavior relative to v1 while preserving better center behavior than structure-only.
- C4 gives the strongest combined best-proxy top20 behavior but remains diagnostic because it is structure-heavy.
- Structure-only S1/S2 help best-proxy promotion but increase mean center error when used alone.

Interpretation:

- Temporal consistency and SAR structure are complementary enough to justify graph-style factor separation.
- The next step should express the factors and their ownership, not search more table-level weights.

## 7. Current Risks

Known risks:

- The SAR structure factor is still based on display/pseudocolor image evidence, not raw SAR intensity.
- A005 remains a legacy soft optical temporal prior.
- A001 remains a legacy candidate container.
- Severe truncated+occluded cases remain unresolved.
- Candidate identity and candidate geometry can diverge in interpretation when multiple candidate IDs share the same box geometry.

These risks should be represented explicitly in the prototype notes and evaluation, not hidden by a single aggregate score.

## 8. Prototype Implementation Boundary

The next implementation round, if approved, should stay inside these limits:

- GM_RM017 only.
- Full A001 candidate pool only.
- No GM_RM011 or GM_RM019 expansion.
- No training.
- No threshold search.
- No calibration.
- No C6/C7 weight tuning.
- No v3 A001/A005 table-rule search.
- No candidate-bank modification.
- No use of A019/A021 before output generation.

The prototype may reorganize the fixed factors into an explicit factor graph representation, but the active evidence sources must remain within the ownership boundaries above.

## 9. Expected Prototype Shape

A minimal prototype can be described as:

```text
A001 candidate c
  -> optical_temporal_factor(c, A005 prior)
  -> sar_structure_factor(c, structure-only S1/S2 evidence)
  -> combined factor baseline initialized from C3
  -> rank existing candidates only
  -> evaluation-only comparison after output exists
```

This is a graph-interface change, not a new source of evidence.

## 10. Future Appendix

Future ideas remain outside the current prototype unless separately approved:

- Raw SAR intensity version.
- Rotated OBB patch structure.
- Visibility and missing-prior route.
- Independent candidate proposal.
- Learned model route after a fixed-bank baseline is mature.

These are future research directions, not current ranking inputs.
