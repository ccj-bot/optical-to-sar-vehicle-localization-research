# Recommended Codex Prompt for Next Step

Data level: L3 implementation task (Stage 1 positive evidence feature validation)

## Context for Codex

This is a research implementation task. Read ALL control files before starting:
- /mnt/d/profile/research/workspace/00_project_control/00_RESEARCH_BRIEF.md through 10_CURRENT_VERIFICATION_CHECKLIST.md

Read these recent audit outputs for context:
- /mnt/d/profile/research/workspace/output/runtime_v2_stage1_repaired_policy_rerun_2026-04-27/02_notes/
- /mnt/d/profile/research/workspace/output/runtime_v2_stage1_positive_vehicle_shape_evidence_audit_2026-04-27/02_notes/
- /mnt/d/profile/research/workspace/output/runtime_v2_stage1_blocked_candidate_audit_2026-04-27/02_notes/

Read this research design document for task framing:
- /mnt/d/profile/research/workspace/output/runtime_v2_full_stream_transfer_opportunity_research_design_2026-04-30/02_notes/positive_sar_vehicle_evidence_taxonomy.md
- /mnt/d/profile/research/workspace/output/runtime_v2_full_stream_transfer_opportunity_research_design_2026-04-30/02_notes/evidence_gap_diagnosis_design.md
- /mnt/d/profile/research/workspace/output/runtime_v2_full_stream_transfer_opportunity_research_design_2026-04-30/02_notes/next_controlled_experiment_design.md

## Task

Implement Phase 1 positive SAR vehicle evidence features as a DIAGNOSTIC AUDIT (no rerun, no promotion):

1. **E1: Compact vehicle-sized body support**
   - Input: SAR pseudo-color crop at candidate location, candidate oriented footprint, optical state (vehicle size range)
   - Output: body_compactness_score in [0,1]
   - Method: compute support concentration inside a vehicle-sized oriented sub-footprint; compare against expected vehicle width/length range; condition by optical state (complete expects full support; truncated expects partial)

2. **E2: Footprint-local support concentration**
   - Input: SAR pseudo-color crop, candidate oriented footprint, local background ring (same orientation, expanded by margin)
   - Output: footprint_concentration_ratio (inner / outer contrast)
   - Method: compute mean/coverage inside footprint vs tight surrounding ring; ratio > 1 means vehicle-like concentration

3. **E3: Vehicle-sized compactness (pre-rank)**
   - Input: candidate geometry (width, length, aspect), optical vehicle size range
   - Output: compactness_score in [0,1]
   - Method: check aspect ratio (1.5-3.5 for cars), absolute size vs optical estimate, penalize extreme aspect or tiny/huge candidates

## Outputs Required

For each of the 37 Stage 1 samples:
- sample_id
- best_candidate_id (by current selection logic — do not change selection)
- E1_body_compactness_score
- E1_body_compactness_status: {positive_compact, bright_diffuse, weak, unavailable}
- E2_footprint_concentration_ratio
- E2_concentration_status: {concentrated, diffuse, background_dominant, unavailable}
- E3_compactness_score
- E3_compactness_status: {vehicle_like, borderline, non_vehicle, unavailable}
- Combined assessment: does this candidate show positive vehicle body evidence? (yes/no/maybe)
- gm_rm019_00006 validation: does E1+E2 correctly identify it as diffuse/non-compact? (must be yes)

Also produce:
- Summary table: how many Stage 1 samples have at least one candidate with positive body evidence?
- Comparison: best candidate by current selection vs best candidate by E1+E2 (if different)
- gm_rm019_00006 dedicated validation report
- Source files read

## Data Access

Stage 1 candidate feature table:
/mnt/d/profile/research/workspace/output/runtime_v2_stage1_structural_feature_rebuild_2026-04-27/00_tables/runtime_v2_stage1_structural_feature_rebuild_2026-04-27_rebuilt_stage1_structural_feature_table.csv

Stage 1 per-sample decisions:
/mnt/d/profile/research/workspace/output/runtime_v2_stage1_repaired_policy_rerun_2026-04-27/00_tables/runtime_v2_stage1_repaired_policy_rerun_2026-04-27_stage1_per_sample_decisions.csv

SAR pseudo-color data:
GM_RM011: D:\profile\research\data\GM_RM011\GM_RM011_SARframes\
GM_RM017: D:\profile\research\data\GM_RM017\GM_RM017_SARframes\
GM_RM019: D:\profile\research\data\GM_RM019\GM_RM019_SARframes\

## Forbidden
- Do NOT rerun Stage 1 selector
- Do NOT promote Stage 1
- Do NOT run Stage 2 or Stage 3
- Do NOT use offline overlap, GT, or oracle labels as runtime inputs for E1/E2/E3
- Do NOT relax the structured-clutter guard
- Do NOT change the candidate selection policy
- Do NOT modify membership thresholds
- Offline overlap may be joined ONLY after E1/E2/E3 scores are fixed, for diagnostic comparison

## Success Criteria
- gm_rm019_00006 is correctly identified as having diffuse/non-compact body evidence (E1 status != positive_compact)
- At least one other Stage 1 candidate shows positive_compact body evidence (E1 = positive_compact) — this would validate that the feature can distinguish vehicle-like bodies
- E2 provides meaningful separation between vehicle-like candidates and background-dominated candidates
- E3 correctly flags obviously non-vehicle-shaped candidates
