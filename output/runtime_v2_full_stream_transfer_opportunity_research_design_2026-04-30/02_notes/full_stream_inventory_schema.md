# Full-Stream Inventory Schema

Data level: L0 (complete three-scene temporal streams)

## 1. Scene Inventory Summary

Based on existing scene frame inventory audits:

| scene | optical_frames (0-indexed) | sar_gray_frames | sar_pseudocolor_frames | depthpro_frames | duration_approx |
|-------|---------------------------|-----------------|------------------------|-----------------|-----------------|
| GM_RM011 | 368 (0..367) | 766 (0..765) | 766 (0..765) | 368 npy + 368 vis | ~15s optical |
| GM_RM017 | 368 (0..367) | 766 (0..765) | 766 (0..765) | 368 npy + 368 vis | ~15s optical |
| GM_RM019 | 368 (0..367) | 766 (0..765) | 766 (0..765) | 368 npy + 368 vis | ~15s optical |

Optical-to-SAR relationship: SAR runs approximately 2x faster (766 frames to 368 optical frames). There is NO fixed reliable offset — the FM_RELATIONSHIP is scene-dependent and frame-dependent.

## 2. Per-Scene Frame Organization

### 2.1 Optical frames

Each scene has 368 optical frames (0..367). These are JPEG/PNG files in:

- GM_RM011: D:\profile\research\data\GM_RM011\GM_RM011_frames\
- GM_RM017: D:\profile\research\data\GM_RM017\GM_RM017_frames\
- GM_RM019: D:\profile\research\data\GM_RM019\GM_RM019_frames\

Naming convention (to be verified by inventory script):
- Likely zero-padded: frame_0000.jpg, frame_0367.jpg

### 2.2 SAR gray frames

Each scene has 766 SAR gray frames (0..765). These are single-channel or grayscale images:

- GM_RM011: D:\profile\research\data\GM_RM011\GM_RM011_SARframes_gray\
- GM_RM017: D:\profile\research\data\GM_RM017\GM_RM017_SARframes_gray\
- GM_RM019: D:\profile\research\data\GM_RM019\GM_RM019_SARframes_gray\

### 2.3 SAR pseudo-color frames

Each scene has 766 SAR pseudo-color frames (0..765). These are pseudo-color rendered SAR:

- GM_RM011: D:\profile\research\data\GM_RM011\GM_RM011_SARframes\
- GM_RM017: D:\profile\research\data\GM_RM017\GM_RM017_SARframes\
- GM_RM019: D:\profile\research\data\GM_RM019\GM_RM019_SARframes\

### 2.4 DepthPro outputs

Each scene has 368 DepthPro .npy files (one per optical frame) plus 368 visualization files:

- GM_RM011: D:\profile\research\data\GM_RM011\GM_RM011_depth\
- GM_RM017: D:\profile\research\data\GM_RM017\GM_RM017_depth\
- GM_RM019: D:\profile\research\data\GM_RM019\GM_RM019_depth\

## 3. Temporal Correspondence

### 3.1 Optical-to-SAR time mapping

The optical-to-SAR relationship is NOT a simple 2x offset. Per the correspondence audit:

- GM_RM011: dominant offset distribution is 1:9 samples (offset=1); mode is unreliable; same-track local deltas show 2 SAR steps per optical step at 78.6% rate; mapped last SAR frame = 735 (30 extra tail frames)
- GM_RM017: dominant offset distribution clustered around 13-16; mode is 14 (63/189 = 33.3%); same-track delta 0:158 at 86.3%; mapped last SAR frame = 748 (17 extra tail frames)
- GM_RM019: dominant offset distribution 0:3 samples; mode is unreliable; same-track deltas 0:7, 1:7; mapped last SAR frame = 734 (31 extra tail frames)

### 3.2 Recommended recording approach

Each optical frame should be linked to its nearest SAR frame(s). Since the relationship is NOT fixed, an inventory script must:

1. For each optical frame `opt_f`, identify the corresponding SAR frame(s) using the scene-specific mapping that was derived in the correspondence audit.
2. Record the mapping as: `(scene, optical_frame, sar_frame_or_range)` — where sar_frame_or_range can be a single index or a window [sar_start, sar_end].
3. Flag any optical frames that lack a SAR counterpart.

Until the full-stream inventory script runs, the per-scene correspondence audit tables (`scene_correspondence_audit.csv`) provide the best-available mapping for the 231 reviewed samples, but NOT for the full stream.

### 3.3 DepthPro time indexing

DepthPro runs once per optical frame (368 outputs for 368 optical frames). Each DepthPro output is indexed to the optical frame it was computed from. Through the optical-to-SAR mapping, DepthPro outputs can be approximately linked to SAR frames.

DepthPro provides weak relative depth cues (near/middle/far), NOT metric radar range.

## 4. Track Context

### 4.1 What tracks exist

Tracks are available from the optical detection pipeline. Each track has:
- track_id
- scene
- optical frame range (start_frame, end_frame)
- possibly: vehicle state tags (complete, truncated, occluded, jittery)
- possibly: optical box trajectory

### 4.2 How tracks should be recorded in the inventory

A full-stream inventory should record for each track:

| field | source | type | notes |
|-------|--------|------|-------|
| scene | known | string | GM_RM011/GM_RM017/GM_RM019 |
| track_id | optical pipeline | string | unique within scene |
| optical_frame_range | optical pipeline | [int,int] | start and end optical frame |
| sar_frame_range | derived from optical-to-SAR mapping | [int,int] | approximate SAR frame window |
| depthpro_range | same as optical | [int,int] | same optical frames |
| vehicle_state_sequence | optical pipeline or audit | dict | per-frame state tags |
| optical_box_sequence | optical pipeline | dict | per-frame bounding boxes |
| track_stability | audit-derived | enum | stable/jittery/drift/ambiguous |

### 4.3 Track context gaps

- Full vehicle state for ALL frames in ALL tracks: MISSING (only some frames have state tags)
- Track-to-candidate linkage table for full stream: MISSING
- DepthPro at track level for full stream: MISSING (only computed for reviewed samples)

## 5. Candidate Context

### 5.1 What candidates exist

SAR candidate pools are generated for each sample (currently only for the 231 reviewed samples). For the full stream, candidate pools must be generated or at least identified for all optical detection frames.

### 5.2 How candidates should be recorded

| field | source | type | notes |
|-------|--------|------|-------|
| scene | known | string | |
| sample_id | optical pipeline | string | optical detection identifier |
| optical_frame | optical pipeline | int | |
| sar_frame | derived | int | linked SAR frame |
| candidate_id | SAR candidate generator | string | unique within (sample, sar_frame) |
| candidate_box | SAR candidate generator | [x1,y1,x2,y2] | in SAR coordinates |
| candidate_source | SAR candidate generator | enum | which proposal source |
| membership_class | geometry check | enum | strong_inside/boundary_overlap/weak_overlap/outside |
| candidate_geometry_features | feature extraction | struct | size, aspect, compactness |
| candidate_body_features | feature extraction | struct | body support, side, cap, corner evidence |
| structural_clutter_guard_result | guard pipeline | struct | blocked/released, margin value |

### 5.3 Candidate context gaps

- Full-stream candidate pools: MISSING (only 231 reviewed samples have candidates)
- Candidate generation for full-stream: NEEDS inventory script to generate or import
- Candidate-to-track linkage for full stream: MISSING

## 6. What Files/Tables Can Serve as Existing Sources

| source_file | content | covers | data_level |
|-------------|---------|--------|------------|
| scene_frame_inventory.csv | frame counts and paths | all three scenes | L0 |
| scene_correspondence_audit.csv | optical-to-SAR offset distribution | 231 reviewed samples only | L2 |
| per_scene_frame_inventory.csv | identical to scene_frame_inventory | all three scenes | L0 |
| per_sample_optical_state.csv | optical state per reviewed sample | 231 reviewed samples | L2 |
| per_track_optical_state_stability.csv | track-level state stability | tracks containing reviewed samples | L2 |
| stage1_candidate_coverage_table.csv | candidate coverage and membership | Stage 1 37 samples only | L3 |
| stage1_structural_feature_table.csv | reconstructed structural features | Stage 1 37 samples | L3 |

## 7. Currently Missing Information

| missing_item | why_missing | needed_for | priority |
|-------------|-------------|------------|----------|
| Full-stream optical frame index with metadata | inventory not yet run | L0 complete stream organization | HIGH |
| Full-stream SAR frame index | inventory not yet run | L0 complete stream organization | HIGH |
| Full-stream optical-to-SAR frame correspondence for ALL frames | only 231 samples mapped | L1 transfer opportunity identification | HIGH |
| Full-stream track inventory with per-frame state | only reviewed-sample tracks have state | L1 vehicle state interpretation | HIGH |
| Full-stream DepthPro per-frame records | only reviewed samples have depth records | L1 relative depth cue | MEDIUM |
| Full-stream candidate pools for all optical detections | candidates only exist for 231 samples | L1 transfer opportunity search space | HIGH |
| Full-stream candidate feature extraction | only Stage 1 samples have features | L1 positive evidence evaluation | MEDIUM |
| Temporal neighbor frames for every SAR frame | not organized at L0 level | L1 temporal consistency evaluation | MEDIUM |
| Track-to-candidate linkage for full stream | candidate generation incomplete | L1 identity consistency | HIGH |

## 8. What the Inventory Script Must Generate

The full-stream inventory script (to be written and run later) should produce:

1. **L0_scene_frame_index**: For each of 3 scenes, list all optical, SAR gray, SAR pseudo-color, and DepthPro frames with file paths and timestamps.

2. **L0_optical_sar_correspondence**: For each optical frame, map to the nearest SAR frame(s). Use the scene-specific offset patterns documented in the correspondence audit.

3. **L1_track_inventory**: For each track in each scene, list: track_id, optical frame range, vehicle state per frame (where available), optical box per frame.

4. **L1_candidate_inventory**: For each optical detection, generate or link SAR candidate pools. Currently this is the biggest gap — candidates only exist for 231 samples.

5. **L1_transfer_opportunity_index**: A derived table combining optical detections, SAR frames, track context, and candidate pools into Level 1 transfer opportunity records (see transfer_opportunity_schema.md).

6. **L1_depthpro_temporal_index**: DepthPro relative depth per optical frame, linked to corresponding SAR frames.

7. **L2_gt_sample_to_L0_L1_mapping**: Map each of the 231 GT-reviewed samples back to scene, optical frame, SAR frame, track, and candidate context (see l2_gt_reviewed_samples_to_full_stream_mapping_plan.md).

## 9. File Name Conventions (to be verified by inventory script)

Optical frames: expected pattern `frame_%04d.jpg` or similar
SAR gray frames: expected pattern `frame_%04d.png` or similar
SAR pseudo-color frames: expected pattern `frame_%04d.png` or similar
DepthPro npy: expected pattern `%04d.npy` or `frame_%04d_depth.npy`
DepthPro vis: expected pattern `%04d_vis.png` or similar
