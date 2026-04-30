# L2 GT-Reviewed Samples to Full-Stream Mapping Plan

Data level: L2-to-L0/L1 mapping design (cross-level audit)

## Purpose

Map each of the 231 GT-reviewed car samples back into the complete scene temporal context. This is an audit, not a pipeline.

The goal is NOT to treat 231 as the complete task. The goal is to understand how the reviewed subset relates to the full stream, what representativeness gaps exist, and what can and cannot be inferred from the 231 samples alone.

## Mapping Targets

Each of the 231 GT-reviewed samples should be traceable to:

### 1. Scene
- Field: scene
- Source: known from sample_id prefix (gm_rm011, gm_rm017, gm_rm019)
- Status: KNOWN for all 231

### 2. Optical frame
- Field: optical_frame
- Source: sample metadata table
- Status: KNOWN for all 231 (the sample was collected at a specific optical frame)

### 3. SAR frame/window
- Field: sar_frame (or sar_frame_best + sar_frame_window)
- Source: scene_correspondence_audit.csv provides offset distributions; the specific SAR frame used for each sample should be in sample metadata
- Status: KNOWN for all 231 (samples have SAR boxes; the SAR frame is implicit)

### 4. Track
- Field: track_id, track_optical_frame_range, track_sar_frame_range_approx
- Source: per_track_optical_state_stability.csv (for tracks containing reviewed samples)
- Status: PARTIALLY KNOWN — tracks exist for reviewed-sample frames, but the full track inventory across all scenes is not yet organized at L0/L1 level

### 5. Nearby optical frames
- Field: optical_neighbors { prev_frames: [...], next_frames: [...] }
- Source: compute from optical_frame ± window_size (e.g., ±5 frames for ~200ms context)
- Status: COMPUTABLE — needs inventory script to list files

### 6. Nearby SAR frames
- Field: sar_neighbors { prev_frames: [...], next_frames: [...] }
- Source: compute from SAR frame ± window_size (±10 SAR frames for equivalent temporal window)
- Status: COMPUTABLE — needs inventory script to list files

### 7. DepthPro frame
- Field: depthpro_frame (same as optical_frame), depthpro_data { depth_median, depth_trend, relative_depth }
- Source: DepthPro .npy file at corresponding optical frame
- Status: PARTIALLY KNOWN — DepthPro outputs exist for all optical frames, but per-sample depth extraction has only been done for some samples

### 8. Candidate pool entries
- Field: sar_candidate_pool { candidate_count, candidate_ids, membership_class per candidate }
- Source: candidate coverage tables (stage1_candidate_coverage_table.csv for Stage 1; others partially available)
- Status: KNOWN for Stage 1 (37 samples); PARTIALLY KNOWN for remaining 194 samples

### 9. Stage subset if any
- Field: stage_subset { is_stage1, is_stage2, is_stage3, stage1_eligibility }
- Source: stage1 eligibility tables
- Status: KNOWN for Stage 1 (37 samples); Stage 2 and Stage 3 not yet assigned
- Distribution: 37 Stage 1, 194 not currently in any stage subset

### 10. Failure group if any
- Field: failure_group { primary_gap: enum, secondary_gaps: [enum] }
- Source: positive vehicle shape evidence audit tables, blocked candidate audit tables
- Status: PARTIALLY KNOWN for Stage 1 (36 blocked, 1 diagnostic-only); UNKNOWN for remaining 194

### 11. Representativeness
- Field: representativeness { vehicle_state_representative: bool, scene_position_representative: bool, difficulty_representative: bool, temporal_context_representative: bool, notes: string }
- Source: computed by comparing this sample's attributes against the full-stream distribution
- Status: UNKNOWN — requires full-stream inventory first

## Mapping Table Schema

The mapping audit should produce a table with these columns:

```
sample_id, scene, optical_frame, sar_frame, track_id, track_optical_start, track_optical_end,
optical_neighbor_prev_count, optical_neighbor_next_count, sar_neighbor_prev_count, sar_neighbor_next_count,
depthpro_frame, depthpro_relative_depth, depthpro_trend,
candidate_pool_size, candidate_strong_inside_count, candidate_boundary_count, candidate_weak_count,
is_stage1, stage1_eligibility, stage1_rerun_status,
is_stage2, is_stage3,
failure_group_primary, failure_group_secondary,
representativeness_vehicle_state, representativeness_scene_position, representativeness_difficulty,
is_full_stream_context_available, full_stream_context_gap_notes
```

## Known Gaps (231 vs Full Stream)

### Gap 1: Optical state coverage bias
The 231 samples are NOT a random sample of all optical frames. They were collected based on detection pipeline triggers. Some vehicle states (complete, center-frame) are likely overrepresented; edge-cases (truncated, occluded, edge-contact) may be underrepresented.

Action: compare 231-sample state distribution against full-track state distribution (requires full-track inventory).

### Gap 2: Scene position coverage
The 231 samples may cluster in certain scene regions (e.g., road center, certain ranges). Full-stream positions without detections are entirely absent from the 231 set.

Action: map 231 optical frames onto the full optical frame range 0..367 per scene; identify gaps.

### Gap 3: Track coverage
Not all tracks have reviewed samples. Some tracks may have zero, one, or many reviewed samples. Tracks with no reviewed samples have NO Level 2 anchor.

Action: identify tracks with zero reviewed samples; flag as "L2-unverified".

### Gap 4: Candidate generation coverage
Candidates were generated only for the 231 reviewed samples (and possibly some additional frames). Full-stream candidate generation has not been performed.

Action: this is the largest operational gap — full-stream candidate generation must happen before L1 inventory is complete.

### Gap 5: Temporal context coverage
The 231 samples are single-frame snapshots. Temporal neighbor frames exist in the data but have not been systematically linked.

Action: for each 231 sample, expand to temporal window and verify neighbor frame existence.

## Implementation Steps (for later script)

1. Load the 231 sample metadata table
2. Load scene correspondence audit (optical-to-SAR offsets)
3. For each sample:
   a. Confirm scene, optical_frame, SAR frame
   b. Look up track_id and track frame range
   c. Compute optical neighbor frames (optical_frame ± 5)
   d. Map optical neighbors to SAR neighbors via scene correspondence
   e. Verify file existence for all frames (optical, SAR gray, SAR pseudo-color, DepthPro)
   f. Record candidate pool metadata
   g. Record Stage subset membership
   h. Record failure group assignment

4. Produce aggregate statistics:
   - Per-scene sample distribution across optical frame range
   - Per-track sample count distribution
   - Tracks with zero reviewed samples
   - Optical frame gaps (frames 0..367 without any reviewed sample)
   - SAR frame gaps (frames 0..765 without any reviewed sample linked)

5. Flag representativeness concerns:
   - Vehicle states that appear in full tracks but not in 231
   - Scene regions (frame ranges) with no reviewed samples
   - Tracks with only one reviewed sample (no temporal verification)

## What This Mapping IS NOT

- NOT a validation that 231 samples are "enough"
- NOT a claim that 231 samples cover all transfer scenarios
- NOT a replacement for full-stream candidate generation
- NOT a signal to restrict future work to the 231 set

It is an audit that tells us what we can and cannot learn from the 231 samples about the full-stream transfer problem.
