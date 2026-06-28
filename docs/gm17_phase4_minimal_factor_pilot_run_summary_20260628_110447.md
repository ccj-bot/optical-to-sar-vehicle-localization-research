# GM17 Phase4 Minimal Factor Pilot Run Summary 20260628_110447

## 1. Run Purpose

This run executed the first GM_RM017-only minimal factor pilot for the new optical-to-SAR hierarchical candidate factor graph line.

The goal was to test whether first-version `geometry_factor` and `optical_temporal_factor` signals exist at candidate level. This was not a GM17 patch, not a legacy score repair, and not a final-model performance claim.

## 2. Input Files

- A001 candidate bank: `output/clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2/candidate_bank_inference.csv`
- A005 temporal prior: `output/clean_no_gt_localizer_2026-05-31_boundary_tables/gm17_temporal_inference.csv`
- A019 post-inference GT: `output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv`
- A021 post-inference condition labels: `output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv`

A019/A021 were read only after `pilot_candidates_ranked.csv` and `pilot_selected_rank1.csv` already existed.

## 3. Output Directory

Primary output directory:

`output/gm17_phase4_minimal_factor_pilot_20260628_110447/`

Main outputs:

- `pilot_candidates_ranked.csv`
- `pilot_selected_rank1.csv`
- `pilot_manifest.json`
- `evaluation_summary.json`
- `evaluation_per_target.csv`
- `evaluation_condition_groups.csv`
- `evaluation_readme.md`

Logs:

- `logs/gm17_phase4_minimal_factor_pilot_20260628_110447.log`
- `logs/gm17_phase4_minimal_factor_pilot_evaluation_20260628_110812.log`

## 4. Pilot Selection Used Fields

A001 fields used for selection:

- `candidate_id`
- `target_identity`
- `scene`
- `sar_frame_num`
- `gm17_track_id`
- `cx`
- `cy`
- `w`
- `h`
- `heading`
- `r`
- `az`
- `cross`

A005 fields used for temporal prior:

- `target_identity`
- `scene`
- `sar_frame_num`
- `gm17_track_id`
- `pred_r`
- `pred_cross`
- `pred_az`

Join surface:

- `target_identity + scene + sar_frame_num + gm17_track_id`

## 5. Forbidden Fields Not Used

Selection loaded only safe columns. The following fields were present in inputs but excluded from ranking/scoring:

- A001: `temporal_factor_score`, `delta_r_from_pred`, `delta_cross_from_pred`, `delta_az_from_pred`, `candidate_source`, `candidate_detail`, `candidate_expansion_state`, `candidate_expansion_reason`, `gm17_anchor_strength`
- A005: `temporal_factor_score`, `pred_cx`, `pred_cy`, `pred_w`, `pred_h`, `pred_heading_deg`, `score`, `lr_score`, `sar_factor_score`, `gm17_temporal_source`, `gm17_temporal_decision`, `gm17_anchor_strength`, `gm17_track_size`, `gm17_anchor_n`, `n_candidates`

The run did not use GT, oracle rank, GM17 selected output, B patch output, legacy score, legacy decision, legacy source, or legacy anchor fields for pilot sorting.

## 6. A001/A005 Join Status

- A001 rows: 58,251
- A005 rows: 205
- Pilot groups / targets: 205
- A005 unique join keys: 205
- A005 ambiguous join keys: 0
- Candidate rows with missing temporal prior: 0
- Candidate rows with join ambiguity: 0
- Candidate rows with valid temporal component: 58,251

Implementation note: the first run stopped at the GM_RM017-only check because A001 contains `gm17supp_*` target identities. The check was updated once to accept `gm17supp` / `gm17_` GM_RM017 supplemental naming while still rejecting GM_RM011/GM_RM019 patterns.

## 7. Candidate and Target Counts

- Candidate-level ranked rows: 58,251
- Rank-1 selected rows: 205
- Target groups: 205
- Geometry-valid candidates: 58,251
- Geometry-invalid candidates: 0
- Temporal-valid candidates: 58,251

All rank-1 candidates had `temporal_distance = 0.0`, meaning the first rule selected candidates already exactly aligned with the A005 `r/cross/az` prior in A001.

## 8. Rank-1 Result Overview

Rank-1 combined selection:

- Mean center error: 32.58 px
- Median center error: 26.65 px
- Mean axis-aligned proxy IoU: 0.4948
- Median axis-aligned proxy IoU: 0.5438
- Proxy-IoU recall@1 at 0.25: 0.7512
- Center-error recall@1 at 50 px: 0.7756

The evaluation uses axis-aligned proxy IoU only. It does not claim rotated IoU.

## 9. Evaluation Overview

Post-inference evaluation used:

- join keys: `target_identity + scene + sar_frame_num`
- A019 required fields: present
- A019 axis-aligned GT box fields: present
- A021 grouping fields: `condition_type`, `condition_status`, `truncation_degree`, `occlusion_degree`
- A019 duplicate rows on evaluation keys: 0
- A021 duplicate rows on evaluation keys: 0
- Selected rows missing GT: 0

Recall summary:

- Proxy-IoU recall@1 / @3 / @5 at 0.25: 0.7512 / 0.7854 / 0.8341
- Center-error recall@1 / @3 / @5 at 50 px: 0.7756 / 0.7951 / 0.8195

## 10. Coverage Results

Best candidate coverage inside the frozen A001 pilot bank:

- Mean best proxy IoU: 0.7846
- Median best proxy IoU: 0.7943
- Best proxy-IoU coverage at 0.25: 1.0000
- Mean best center error: 7.54 px
- Median best center error: 5.64 px
- Best-center coverage at 50 px: 1.0000
- Mean rank of best-proxy candidate under current pilot ranking: 67.58
- Median rank of best-proxy candidate under current pilot ranking: 40.0

Interpretation: A001 is sufficient as a GM_RM017 pilot container for coverage, but the current rank-1 rule often does not select the best covered candidate.

## 11. Geometry / Temporal / Combined Signal Interpretation

The v1 `geometry_factor` was intentionally minimal: finite geometry plus positive width/height. Since all 58,251 candidates were geometry-valid, this first geometry factor had no useful discrimination by itself.

The v1 `optical_temporal_factor` produced a strong deterministic ordering, but all rank-1 selections had zero temporal distance. This suggests A001 already contains a base candidate exactly matching A005 prior coordinates. That is useful as a pilot signal but also a legacy-container warning: temporal distance is currently selecting the A005-aligned base candidate rather than proving an independent optical-to-SAR model factor.

`geometry_only`, `temporal_only`, and `combined` summaries were identical in this run:

- Mean center error: 32.58 px
- Mean proxy IoU: 0.4948
- Proxy-IoU recall@1 at 0.25: 0.7512

The combination therefore did not improve over either single-factor variant in this first implementation.

## 12. Failure Grouping Overview

Largest groups:

- `none / none / none`: 117 targets, mean center error 26.41 px, proxy recall@1 0.8205
- `occluded / none / mild`: 28 targets, mean center error 29.97 px, proxy recall@1 0.8214
- `truncated / severe / none`: 17 targets, mean center error 22.06 px, proxy recall@1 0.8824
- `truncated+occluded / mild / mild`: 14 targets, mean center error 66.70 px, proxy recall@1 0.3571
- `truncated+occluded / moderate / moderate`: 6 targets, mean center error 67.42 px, proxy recall@1 0.3333
- `truncated+occluded / severe / moderate`: 5 targets, mean center error 78.20 px, proxy recall@1 0.2000

Failure is concentrated most clearly in combined truncation + occlusion cases, especially moderate/severe combinations.

## 13. Main Failure Reasons

Likely failure reasons from this run:

- The v1 geometry factor is too weak because every candidate passed finite/positive-size validity.
- The temporal rule selects exact A005-aligned base candidates, which are not always close to GT.
- A001 contains good candidates, but many are lower-ranked under the current temporal-first rule.
- Truncation + occlusion cases reduce the reliability of the A005-aligned candidate.
- Some no-condition cases still have large center error, so condition grouping explains much but not all failure.

These are pilot-boundary findings, not final new-model failure.

## 14. A001 Pilot Container Sufficiency

A001 is sufficient as a GM_RM017-only pilot container for coverage: every target had at least one candidate meeting the predeclared proxy-IoU coverage threshold and center-error coverage threshold.

A001 is not sufficient as a final model dependency. The current pilot shows that the frozen bank contains useful candidates, but the v1 factor ordering does not reliably select them.

## 15. Next Recommendations

- Do not tune thresholds or weights from this evaluation.
- Deepen `geometry_factor`: replace finite/positive-size validity with a fixed-prior design that can discriminate candidate geometry without GT tuning.
- Deepen `optical_temporal_factor`: separate independent temporal consistency from the legacy A005-aligned base candidate artifact.
- Add a diagnostic implementation spec for v2 that compares rank-1 temporal-zero candidates against best-covered candidates without feeding the evaluation back into the rule.
- Since coverage is strong, independent candidate proposal is not the immediate blocker for GM_RM017 pilot; ranking/factor semantics are the blocker.
- If future work shows coverage drops outside GM_RM017, then move to independent candidate proposal design rather than expanding A001/A005.
