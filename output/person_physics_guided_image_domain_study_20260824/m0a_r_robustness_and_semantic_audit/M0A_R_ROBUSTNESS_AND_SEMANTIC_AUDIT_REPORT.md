# M0A-R robustness and semantic audit report

- Audit state: `M0A_R_TRANSPORT_VALID_BUT_PERSON_SPECIFICITY_NOT_ESTABLISHED`
- Frozen M0A state retained unchanged: `M0A_REGION_SUPPORT_TRANSPORT_WITH_P0_GAIN`
- Starting HEAD: `02a112565e72a3aed4ef674377cdb9052a33b33a`
- Scientific status: descriptive evidence; insufficient independent frame-pair clusters for confirmatory inference.

## Conclusion

The frozen M0A result remains a valid description of short-term q95 SAR image-domain support transport in the exposed R02 slice. The audit does not find a basis to promote it to PERSON-specific continuation. Only three frame-pair clusters contribute supported edges, all six base edges are shared by two manual target references, and strong q95 persistence also occurs in deterministic reference-free high-response controls. P0 remains a useful common registration mechanism; its gain is not a PERSON identity mechanism.

## Cluster dependence

- Effective frame-pair clusters: `3`.
- Supported source-region clusters: `6`.
- Supported base-edge clusters: `6`.
- Repeated shared target/reference groups: `2`.
- The historical `29/30` matched result is retained as 30 clustered comparisons, not 30 independent observations.
- Leave-one-frame-pair-out results are in `leave_one_frame_pair_out.csv`; no p-value is manufactured from three clusters.

## Support-size sensitivity

GT-blind cutpoints were derived from all 1,064 pre-reference source regions: `<=70`, `71-209`, `210-587`, `>=588` pixels. The 1/6/19-pixel cases remain in the audit and figures. All six reference-supported edges are in `LARGE_Q4`, so the nominal supported P0 gain is not driven by tiny source regions. Tiny cases are still unstable and are retained as observability/boundary evidence rather than deleted.

| stratum | all_pre_reference_source_region_count | supported_edge_count | supported_p0_retention_median | supported_delta_p0_median | reference_free_structural_control_count | control_p0_retention_median | control_zero_retention_median | control_delta_p0_median | tiny_cases_deleted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TINY_Q1 | 266 | 0 |  |  | 265 | 0.0000 | 0.0000 | 0.0000 | False |
| SMALL_Q2 | 267 | 0 |  |  | 266 | 0.3925 | 0.3603 | 0.0000 | False |
| MEDIUM_Q3 | 265 | 0 |  |  | 262 | 0.7654 | 0.7162 | 0.0093 | False |
| LARGE_Q4 | 266 | 6 | 0.9093 | 0.0550 | 243 | 0.8321 | 0.7884 | 0.0318 | False |

## P0 gain families

Supported median P0/ZERO/delta: `0.9093 / 0.8418 / +0.0550`.
Size/topology-matched reference-free controls median P0/ZERO/delta: `0.8594 / 0.8462 / +0.0223`.
The comparison is descriptive and cluster-aware. A positive background-control delta supports general image registration, not PERSON specificity.

| evidence_family | row_count | frame_pair_cluster_count | source_region_cluster_count | base_edge_cluster_count | p0_retention_median | zero_retention_median | delta_p0_median | delta_p0_mean | p0_better_fraction | p0_rank_percentile_median | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REFERENCE_SUPPORTED_EDGES | 6 | 3 | 6 | 6 | 0.9093 | 0.8418 | 0.0550 | 0.0593 | 0.8333 | 1.0000 | DESCRIPTIVE_EVIDENCE_NOT_INDEPENDENT_ROW_LEVEL_INFERENCE |
| REFERENCE_UNSUPPORTED_MATCHED_ALTERNATIVES | 30 | 3 | 6 | 30 | 0.0000 | 0.0000 | 0.0000 | -0.0003 | 0.0333 | 0.6084 | DESCRIPTIVE_EVIDENCE_NOT_INDEPENDENT_ROW_LEVEL_INFERENCE |
| REFERENCE_FREE_STRUCTURAL_HIGH_RESPONSE_CONTROLS | 1036 | 22 | 1036 | 1036 | 0.6438 | 0.5879 | 0.0000 | 0.0267 | 0.4604 | 1.0000 | DESCRIPTIVE_EVIDENCE_NOT_INDEPENDENT_ROW_LEVEL_INFERENCE |
| SUPPORTED_MATCHED_REFERENCE_FREE_CONTROLS | 30 | 3 | 19 | 19 | 0.8594 | 0.8462 | 0.0223 | 0.0288 | 0.9667 | 1.0000 | DESCRIPTIVE_EVIDENCE_NOT_INDEPENDENT_ROW_LEVEL_INFERENCE |

## q95 relative-percentile semantics

q95 is a frame-relative superlevel set, so every frame contains q95 regions by construction. Region existence is therefore not PERSON-presence evidence. The audit compares supported continuity with deterministic non-reference high-response controls and a P0-best-destination upper bound; these controls show that high temporal persistence is a general image-domain property in this scene slice.

## Shared/unresolved positives

All `6` supported base edges have `supported_target_count=2` and remain `REFERENCE_SUPPORTED_DYNAMIC_EXPLANATION`. PERSON-exclusive positives: `0`. Source/destination local degree and full component topology are retained separately in `shared_unresolved_positive_audit.csv`.

## Correlated descriptors and evidence families

`retention`, `destination_explained_fraction`, and `soft_iou` reuse the same warped-source/destination intersection and are not independent evidence. q90/q95/q97.5 are nested superlevel layers of the same frozen `S(x)`. They remain useful morphology descriptors but must not be double-counted as separate physical factors.

Independent evidence-family organization for future work:

1. SAR response morphology
2. SAR temporal transport
3. shell-region topology
4. optical angular dynamics
5. timing/phase consistency
6. observability/boundary/availability

Only the first three and the last are present in M0A-R. Optical angular dynamics and timing/phase consistency are not executed here.

## Ten deterministic real cases

- `01_one_pixel_boundary_case.png`
- `02_six_pixel_p0_gain_case.png`
- `03_nineteen_pixel_zero_better_case.png`
- `04_split_like.png`
- `05_merge_like.png`
- `06_supported_vs_deceptive_matched_alternative.png`
- `07_supported_shared_high_retention.png`
- `08_supported_shared_low_retention.png`
- `09_reference_free_high_persistence.png`
- `10_reference_free_max_p0_gain.png`

## State and scope

The evidence-faithful audit state is `M0A_R_TRANSPORT_VALID_BUT_PERSON_SPECIFICITY_NOT_ESTABLISHED`. It does not overwrite `M0A_REGION_SUPPORT_TRANSPORT_WITH_P0_GAIN`; it qualifies its interpretation. M0A still means short-term q95 support continuity plus limited P0 gain in the frozen R02 slice. It does not establish Optical-SAR motion consistency, PERSON-specific region continuation, identity, ambiguity reduction, runtime optical identity, or final SAR localization.

## Recommendation for M0B

Proceed only with a minimal development diagnostic that asks whether raw-fragment optical angular dynamics adds incremental discrimination beyond the frozen SAR-only evidence. Do not execute M0B as part of this task, do not fit timing offsets, and do not construct a tracker or unique path.

## Authoritative audit artifacts

- support_size_strata: `support_size_strata.csv`
- support_size_sensitivity: `support_size_sensitivity.csv`
- supported_edge_audit: `supported_edge_audit.csv`
- cluster_aware_summary: `cluster_aware_summary.csv`
- leave_one_frame_pair_out: `leave_one_frame_pair_out.csv`
- matched_alternative_cluster_audit: `matched_alternative_cluster_audit.csv`
- background_high_response_controls: `background_high_response_controls.csv`
- supported_matched_background_controls: `supported_matched_background_controls.csv`
- p0_gain_family_comparison: `p0_gain_family_comparison.csv`
- p0_gain_family_by_frame_pair: `p0_gain_family_by_frame_pair.csv`
- q95_relative_percentile_semantic_audit: `q95_relative_percentile_semantic_audit.csv`
- shared_unresolved_positive_audit: `shared_unresolved_positive_audit.csv`
- correlated_descriptor_audit: `correlated_descriptor_audit.csv`
- real_case_registry: `real_case_registry.csv`
- audit_summary: `audit_summary.json`
