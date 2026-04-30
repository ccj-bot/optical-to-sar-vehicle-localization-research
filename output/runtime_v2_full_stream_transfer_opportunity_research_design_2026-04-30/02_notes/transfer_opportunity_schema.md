# Transfer Opportunity Schema

Data level: L1 (full-stream transfer opportunities)

## Definition

A transfer opportunity is a point in the complete three-scene temporal stream where optical vehicle information can be transferred into SAR space to constrain or inform SAR vehicle detection.

A transfer opportunity is NOT a GT sample. It is NOT a replacement candidate. It is a position in the full stream where optical-to-SAR transfer is physically meaningful, regardless of whether a GT box exists or a candidate was generated.

## Required Fields

### 1. scene_id
- type: string
- values: GM_RM011, GM_RM017, GM_RM019
- description: which scene this opportunity belongs to

### 2. optical_frame_id
- type: int (0..367)
- description: the optical frame that contains vehicle detection

### 3. sar_frame_range
- type: struct { start: int, end: int, best: int }
- description: the SAR frame window that corresponds to this optical frame; `best` is the single most likely SAR frame
- notes: the window is scene-dependent and NOT a fixed 2*opt_f + offset

### 4. optical_detection_id OR track_id
- type: string
- description: either a single detection ID or the track this detection belongs to
- priority: use track_id when available (temporal context); use detection_id for single-frame opportunities

### 5. vehicle_state
- type: struct with at minimum:
  - optical_state: enum { complete, bottom_truncated, side_truncated, edge_contact, occluded, jittery, nearby_ambiguity, identity_drift, unknown }
  - field_of_view_position: enum { center, top_edge, bottom_edge, left_edge, right_edge, corner }
  - visible_support_fraction: float [0,1] — estimated fraction of vehicle visible in optical
  - heading_orientation: approximate heading in SAR coordinate frame
  - vehicle_size_range: struct { min_width, max_width, min_length, max_length } — in SAR pixels
- description: optical interpretation of the vehicle's physical state, used to condition SAR search

### 6. optical_box_or_visible_support
- type: struct { box: [x1,y1,x2,y2] (in optical), support_mask: bool (whether reliable), truncation_edge: enum or none }
- description: the optical bounding box and whether it captures the full vehicle or only a visible portion

### 7. depthpro_relative_depth_cue
- type: struct { relative_depth: enum { near, middle, far }, depth_median: float, depth_trend: enum { stable, approaching, receding }, confidence: enum { reliable, weak, unavailable } }
- description: DepthPro relative depth estimate at this optical frame
- constraint: this is WEAK evidence — it tells us whether the vehicle is near/middle/far relative to the scene, not the exact SAR range

### 8. azimuth_mapping_cue
- type: struct { azimuth_center: float, azimuth_uncertainty: float, azimuth_reliability: enum { reliable, weak, non_monotonic } }
- description: empirical optical-to-SAR azimuth direction mapping
- notes: azimuth mapping is the strongest directional constraint available

### 9. range_cue_if_available
- type: struct { range_estimate: float or null, range_uncertainty: float or null, range_source: enum { depthpro_heuristic, track_consistency, none }, range_usable: bool }
- description: approximate SAR range estimate if available
- constraint: range is WEAK — do not treat as metric radar range

### 10. sar_candidate_pool_reference
- type: struct { pool_id: string, candidate_count: int, candidate_ids: [string], pool_generation_method: enum { full, partial, unavailable } }
- description: reference to the candidate pool that serves as the SAR search space for this opportunity
- notes: currently this only exists for 231 reviewed samples; for full-stream opportunities, this field will start as "unavailable" and be populated by future candidate generation

### 11. temporal_neighborhood
- type: struct {
    optical_neighbors: { prev_frames: [int], next_frames: [int], window_size: int },
    sar_neighbors: { prev_frames: [int], next_frames: [int], window_size: int },
    temporal_consistency_flag: enum { stable, slowly_changing, fast_changing, jittery }
  }
- description: nearby optical and SAR frames that provide temporal context

### 12. identity_confidence
- type: float [0,1]
- description: confidence that this opportunity tracks the same physical vehicle across frames
- notes: derived from track stability, optical appearance consistency, and vehicle state continuity

### 13. uncertainty_flags
- type: list of enum flags
- possible values: [optical_state_ambiguous, azimuth_uncertain, range_unavailable, depthpro_unreliable, track_unstable, nearby_object_present, identity_drift_suspected, candidate_pool_unavailable, sar_frame_mapping_uncertain, truncation_severe, occlusion_possible]
- description: flags that indicate why this transfer opportunity may be difficult or unreliable

### 14. gt_reviewed_sample_overlap
- type: struct { overlaps_231_gt: bool, matching_sample_id: string or null, matching_sar_frame: int or null }
- description: whether this opportunity coincides with one of the 231 GT-reviewed car samples
- L2 relationship: this is a Level 2-to-Level 1 mapping field

### 15. stage_subset_membership
- type: struct {
    is_stage1: bool,
    is_stage2: bool,
    is_stage3: bool,
    stage1_eligibility: enum { eligible_automatic, current_protected_fallback, diagnostic_only, not_stage1 },
    stage1_rerun_status: enum { not_run, accepted, rejected, blocked, diagnostic_only }
  }
- description: whether this opportunity belongs to a Stage 1/2/3 diagnostic subset
- L3 relationship: this is a Level 3-to-Level 1 mapping field

### 16. unlabeled_full_stream_opportunity
- type: bool
- description: true if this opportunity has NO corresponding GT-reviewed sample — it exists in the full stream but was never labeled
- significance: these are the unexamined majority of transfer opportunities

### 17. positive_sar_evidence_status (proposed, not yet populated)
- type: struct {
    body_compactness: enum { positive_compact, bright_diffuse, weak, unavailable },
    side_cap_corner_arrangement: enum { consistent_frame, edge_corner_without_closure, unavailable },
    frame_closure: enum { full_near_full, partial_state_compatible, edge_corner_only, unavailable },
    static_persistence_risk: enum { static_risk, temporal_clear, unavailable }
  }
- description: the positive SAR vehicle evidence status (to be populated by future audit)
- notes: this is a placeholder for future evidence taxonomy implementation

## Transfer Opportunity Lifecycle

A transfer opportunity progresses through states:

1. **identified**: optical detection exists, SAR frame is mapped
2. **candidate_populated**: SAR candidate pool is generated or linked
3. **evidence_evaluated**: SAR evidence features are extracted (positive AND negative)
4. **scored**: optical and SAR evidence combined into a transfer decision
5. **decided**: one of { accept, fallback, diagnostic_only, remap, quarantine }

Currently, only the 231 reviewed samples have reached state 3+.
The full stream has opportunities at state 1 (identified), some at state 2.

## Relationship to GT Samples

A transfer opportunity IS NOT a GT sample:
- A GT sample is an opportunity that has a manually reviewed SAR box.
- Many transfer opportunities will never have a GT box.
- The 231 GT samples serve as calibration and evaluation anchors for the transfer method.
- Transfer opportunities without GT can still be processed and decided, but their outcomes are not verifiable against ground truth.

## Relationship to Candidate Pools

A transfer opportunity references a candidate pool, but is not itself a candidate:
- The candidate pool is the SAR search space for this opportunity.
- The opportunity includes optical constraints and vehicle state that guide how candidates are evaluated.
- A single transfer opportunity may result in: accepting one candidate, falling back to current mainline, or flagging diagnostic-only.
