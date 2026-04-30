# Summary: Full-Stream Transfer Opportunity Inventory and Positive SAR Evidence Audit Design

Data level: ALL (L0/L1/L2/L3/L4 design spanning the complete research hierarchy)
Date: 2026-04-30

## What Was Done

This task produced the research design architecture for the next phase of the optical-to-SAR vehicle transfer project. The work is entirely research DESIGN — no experiments were run, no selectors were rerun, no thresholds were changed.

## Key Outputs

### Part A: Full-Stream Inventory Schema (L0)
- Defined how all three scenes (GM_RM011, GM_RM017, GM_RM019) should be organized with optical, SAR gray, SAR pseudo-color, and DepthPro frames
- Documented optical-to-SAR correspondence: ~2x frame rate, NO fixed offset, scene-dependent
- Identified 9 critical missing items: full-stream optical/SAR frame index, full correspondence mapping, track inventory, candidate pools, feature extraction, temporal neighbors, track-candidate linkage
- Defined what the inventory script must generate

### Part B: Transfer Opportunity Schema (L1)
- Defined a transfer opportunity as a complete 17-field record in the full temporal stream
- Separated transfer opportunities from GT samples and from candidate pools
- Included vehicle state, azimith/range cues, depth, temporal neighborhood, identity confidence, uncertainty flags
- Linked opportunities to L2 (GT overlap) and L3 (Stage membership)
- Defined the lifecycle: identified -> candidate_populated -> evidence_evaluated -> scored -> decided

### Part C: L2 GT-Reviewed Samples to Full-Stream Mapping (L2-to-L0/L1)
- Designed a mapping audit that traces each of 231 reviewed samples to scene, frame, track, and candidate context
- Identified 5 representativeness gaps: optical state bias, scene position clustering, track coverage gaps, candidate generation limits, missing temporal context
- Defined mapping table schema and implementation steps

### Part D: Stage 1 Diagnostic Interpretation (L3-to-ALL)
- Documented exactly what Stage 1 proved (safety, guard effectiveness, conservative correctness) and did NOT prove (selector viability, threshold relaxation, model wrongness, 231 representativeness)
- Explained why Stage 1 cannot serve as basis for Stage 2/3 (no working positive evidence, harder states downstream, feature-level gap not sample-level gap)
- Mapped Stage 1 lessons to 7 specific full-stream design constraints

### Part E: Positive SAR Vehicle Evidence Taxonomy (ALL)
- Defined 18 evidence types: from compact body support (E1) to cross-frame consistency (E18)
- Classified each as EXISTS, PARTIAL, or MISSING — 11 of 18 are MISSING
- Assigned 4-phase implementation priority: Phase 1 (minimum evidence) -> Phase 2 (clutter separation) -> Phase 3 (state conditioning) -> Phase 4 (track-level)
- Explicitly separated positive evidence from clutter rejection

### Part F: Evidence Gap Diagnosis Design (ALL)
- Defined 11 gap categories: from G1 (positive evidence missing) to G11 (unlabeled full-stream)
- Designed a 10-step diagnostic decision tree
- Mapped each gap to missing evidence taxonomy entries
- Planned 3-step implementation: L3 validation -> L2 coverage -> L1 readiness

### Part G: Next Controlled Experiment Design (L3-first)
- Designed Phase 1 positive evidence feature validation on Stage 1 (E1, E2, E3)
- Specified diagnostic-only approach — no rerun, no promotion
- Defined when rerun is permitted and when Stage 2/3 remain blocked
- Set clear promotion gates requiring physically explainable positive evidence

## What Was NOT Run

- Stage 1: NOT rerun
- Stage 2: NOT run
- Stage 3: NOT run
- Selector: NOT rerun
- Thresholds: NOT changed
- Oracle/GT: NOT used as runtime evidence
- ROI repair: NOT added
- Codex: NOT invoked

## Data Level Tagging

All outputs are tagged by data level:
- L0: full_stream_inventory_schema.md
- L1: transfer_opportunity_schema.md
- L2-to-L0/L1: l2_gt_reviewed_samples_to_full_stream_mapping_plan.md
- L3-to-ALL: stage1_diagnostic_interpretation.md
- ALL: positive_sar_vehicle_evidence_taxonomy.md, evidence_gap_diagnosis_design.md
- L3-first: next_controlled_experiment_design.md

## Current Gate Status

- Stage 1: BLOCKED (no positive evidence mechanism)
- Stage 2: BLOCKED (Stage 1 has not passed; harder optical states)
- Stage 3: BLOCKED (Stage 1/2 not passed; multi-range uncertainty)
- Selector promotion: BLOCKED (all conditions unmet)
- Threshold relaxation: FORBIDDEN

## Research Direction Assessment

The current direction does NOT require a complete redesign. It requires:
1. A PARTIAL REDIRECT: from "try to get Stage 1 to accept something" to "first implement positive vehicle evidence features"
2. A RE-ANCHORING: to L0/L1 full-stream perspective while keeping L2/L3 as diagnostic windows
3. A SEQUENCE CHANGE: positive evidence features BEFORE any more reruns

The 05_CURRENT_STATE_AND_OPEN_QUESTIONS.md question #8 ("Should the current direction be partially redesigned?") is answered as YES — partial redesign, specifically: positive evidence first, downstream experiments second.

## Next Safe Step

Implement Phase 1 positive evidence features (E1, E2, E3) as a diagnostic audit on Stage 1. See recommended_codex_prompt_for_next_step.md for the executable prompt.
