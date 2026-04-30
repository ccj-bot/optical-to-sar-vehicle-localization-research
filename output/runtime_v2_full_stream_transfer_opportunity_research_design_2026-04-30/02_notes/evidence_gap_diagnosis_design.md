# Evidence Gap Diagnosis Design

Data level: ALL (applied first at L3 Stage 1 for validation, then extended to L2, then L1)

## Purpose

Design a systematic method to classify WHY a transfer opportunity fails — separating distinct root causes rather than lumping all failures together.

Current state: the Stage 1 rerun showed 37/37 samples rejected. The blocked-candidate audit classified these into "ambiguous" (28), "likely over-blocking" (6), "clearly correct clutter rejection" (2), and "missing positive vehicle evidence" (1). This is useful but insufficient — we need a diagnostic that can distinguish subtler failure modes and guide targeted fixes rather than blanket actions.

## Gap Categories

### G1: Positive Vehicle Evidence Missing
- Definition: SAR candidate exists within the search region, candidate is not obviously static clutter, but the system cannot confirm it looks enough like a vehicle to accept it.
- Detection signature: candidate body evidence fields are "bright but diffuse," footprint-local concentration is low, compactness is borderline.
- Root cause: missing positive evidence features (E1, E2, E10 from evidence taxonomy).
- What to do: add compact body support and footprint-local concentration features, then re-evaluate.
- What NOT to do: relax structured-clutter guard — the guard is correctly rejecting candidates, but positive evidence is needed to find the right ones.
- Stage 1 examples: 35/36 structured-clutter blocked samples likely fall here.

### G2: Candidate Generation Missing
- Definition: No SAR candidate exists near enough to the true vehicle location, or the candidate pool is empty or severely limited.
- Detection signature: candidate count = 0 for this opportunity, or all candidates are far from the expected SAR region.
- Root cause: candidate generator did not propose a box at the correct location, or the candidate source is not triggered for this scene/frame.
- What to do: improve candidate generation (compact proposal generation, vehicle-sized pre-filtering).
- What NOT to do: add more scoring features — if no candidate exists, scoring is irrelevant.
- Stage 1 examples: any sample with candidate_pool_size = 0 after geometry filtering.

### G3: Candidate Geometry/Membership Mismatch
- Definition: Candidates exist, but none have the right membership class (all are weak-overlap or outside), OR candidate boxes have vehicle-incompatible geometry (wrong size, wrong aspect).
- Detection signature: best candidate membership is "weak overlap" or "outside," OR candidate aspect ratio is outside vehicle range.
- Root cause: candidate generator produces boxes that don't align with the optical-to-SAR search region, or generates non-vehicle-shaped proposals.
- What to do: improve candidate generation geometry; add compactness pre-ranking.
- What NOT to do: lower membership thresholds — admitting weak-overlap candidates would introduce false positives.
- Stage 1 examples: boundary-overlap and weak-overlap cases where no strong-inside candidate exists.

### G4: Temporal Context Missing
- Definition: The transfer opportunity is evaluated at a single SAR frame, but the vehicle evidence is only clear when temporal context (nearby frames, static subtraction) is included.
- Detection signature: candidate body evidence is ambiguous in the current frame, but nearby frames could confirm or reject.
- Root cause: temporal neighbor frames are not yet organized or used in evidence extraction.
- What to do: implement static-background rejection (E12) and temporal consistency (E11).
- What NOT to do: increase single-frame evidence thresholds — the evidence is inherently temporal.
- Stage 1 examples: candidates where static persistence risk is flagged but temporally-informed features are missing.

### G5: Over-Blocking by Clutter Guard
- Definition: A candidate that HAS vehicle-like body evidence is blocked by the structured-clutter guard.
- Detection signature: candidate has positive compact body evidence, side/cap/corner arrangement looks vehicle-like, but structured-clutter margin is negative.
- Root cause: the guard's feature set is too broad — it uses structural fields that cannot distinguish vehicle structure from clutter structure in this specific case.
- What to do: review the specific guard features that triggered; consider whether positive body evidence should override certain guard components.
- What NOT to do: globally relax the guard — fix specific feature interactions, not thresholds.
- Stage 1 examples: the "likely over-blocking" cases (6 identified in audit), especially gm_rm019_00189.

### G6: True No-Evidence Cases
- Definition: The vehicle genuinely produces very weak SAR return — no candidate, no brightness, nothing that any reasonable method could detect.
- Detection signature: SAR frame at the expected vehicle location shows very low intensity; no candidate generator can propose anything.
- Root cause: the vehicle is not radar-visible at this frame (material, orientation, occlusion, range).
- What to do: accept that transfer is impossible for this opportunity; flag as "no-evidence" and fall back to current mainline.
- What NOT to do: lower thresholds until "something" is found — would produce garbage.
- Stage 1 examples: samples with current IoU = 0 but no bright SAR return at optical vehicle position.

### G7: Wrong Optical-to-SAR Mapping
- Definition: The optical frame is mapped to the wrong SAR frame, so the system searches in the wrong SAR frame entirely.
- Detection signature: candidate search region doesn't overlap with actual vehicle SAR location; offset is wrong.
- Root cause: optical-to-SAR correspondence is incorrect for this frame (scene correspondence audit shows non-fixed offsets).
- What to do: verify optical-to-SAR mapping for this specific frame; use local temporal cues for better correspondence.
- What NOT to do: enlarge the search region — searching wrong frames is not fixed by wider search.
- Stage 1 examples: samples from GM_RM019 where dominant offset is unreliable (offset distribution spread across 0-14).

### G8: Weak Range Anchoring
- Definition: The optical-to-SAR range estimate is too weak, so the candidate search region is too large or mispositioned in range.
- Detection signature: candidate pool includes many range-distant proposals; best candidate is at the wrong range.
- Root cause: DepthPro provides only near/middle/far, not metric range; range uncertainty is large.
- What to do: accept range weakness as a physical constraint; use azimuth (which is more reliable) as the primary constraint; condition SAR search on azimuth corridor.
- What NOT to do: fit range from oracle data — forbidden.
- Stage 1 examples: samples where azimuth mapping is reliable but range is too uncertain to narrow the search.

### G9: Identity Drift
- Definition: The optical track has drifted, so the optical box no longer corresponds to the same physical vehicle as the SAR candidate.
- Detection signature: optical track shows sudden position/size/orientation changes; candidate evidence is consistent with a different vehicle or background.
- Root cause: optical tracker lost the vehicle or switched to a different object.
- What to do: flag identity drift as "untrustworthy transfer"; use track stability check before attempting transfer.
- What NOT to do: force a transfer when identity is uncertain.
- Stage 1 examples: samples tagged "jittery or unstable optical track" in the optical state audit.

### G10: Nearby-Object Ambiguity
- Definition: Another vehicle or large object is close to the target vehicle, making it ambiguous which SAR candidate corresponds to which optical detection.
- Detection signature: multiple optical detections map to similar SAR regions; candidates are equidistant from multiple optical boxes.
- Root cause: dense multi-vehicle scenes create assignment ambiguity.
- What to do: use temporal consistency (track history) and spatial uniqueness to resolve; flag as ambiguous if unresolvable.
- What NOT to do: pick the closest candidate blindly — may assign wrong vehicle.
- Stage 1 examples: samples tagged "nearby multi-object ambiguity" in optical state.

### G11: Unlabeled Full-Stream Opportunity (Not in 231 GT Subset)
- Definition: This is a transfer opportunity from the full stream that has NO GT-reviewed sample — we cannot verify correctness against ground truth.
- Detection signature: gt_reviewed_sample_overlap = false.
- Root cause: this is not a gap — it's the normal state for most L1 opportunities.
- What to do: evaluate with runtime evidence only; track decisions but cannot verify against GT; use for coverage statistics and representativeness analysis.
- What NOT to do: assume GT coverage extends to these opportunities.
- Stage 1 examples: none — Stage 1 is inside 231 by definition; but this gap is the dominant category at L1.

## Diagnosis Decision Tree

For each transfer opportunity (initially for the 37 Stage 1, later extended):

```
1. Does a candidate pool exist?
   NO  -> G2 (candidate generation missing)
   YES -> continue

2. Does any candidate have strong-inside or boundary-overlap membership?
   NO  -> G3 (candidate geometry/membership mismatch)
   YES -> continue

3. Is the optical-to-SAR mapping verified for this frame?
   NO  -> G7 (wrong mapping) — verify first
   YES -> continue

4. Does the best unblocked candidate have positive compact body evidence (E1)?
   NO  -> G1 (positive vehicle evidence missing) or G6 (true no-evidence)
   YES -> continue

5. Is the candidate blocked by structured-clutter guard despite positive body evidence?
   YES -> G5 (over-blocking) — review guard interaction
   NO  -> continue

6. Does temporal context (static subtraction) change the evidence assessment?
   YES -> G4 (temporal context missing)
   NO  -> continue

7. Is range anchoring too weak to distinguish candidates?
   YES -> G8 (weak range anchoring)
   NO  -> continue

8. Does the optical track show identity drift or instability?
   YES -> G9 (identity drift)
   NO  -> continue

9. Are there multiple nearby optical detections creating ambiguity?
   YES -> G10 (nearby-object ambiguity)
   NO  -> continue

10. If still unidentified: flag as "complex multi-factor gap" for manual review
```

## Diagnosis Table Schema

For a systematic audit, produce:

```
sample_id | scene | optical_frame | sar_frame | gap_category_primary | gap_category_secondary | gap_category_tertiary |
candidate_pool_exists | best_membership_class | best_body_compactness | best_local_concentration |
best_static_risk | best_frame_closure | optical_sar_mapping_reliable | range_anchoring_strength |
track_stability | nearby_object_count | gt_overlap_available | recommended_action | forbidden_action
```

## Relationship to Evidence Taxonomy

Each gap category maps to missing or insufficient evidence:

| gap_category | primary_missing_evidence | secondary_missing |
|-------------|------------------------|-------------------|
| G1 | E1 (compact body), E2 (footprint concentration), E10 (local contrast) | E16 (current comparison) |
| G2 | candidate generation pre-processing | E3 (compactness pre-rank) |
| G3 | candidate geometry | E3, E14 (leakage) |
| G4 | E11 (temporal), E12 (static subtraction) | - |
| G5 | interaction between positive E1/E2 and guard | E13 (long-edge) |
| G6 | vehicle physics (low radar return) | - |
| G7 | optical-to-SAR correspondence | temporal consistency |
| G8 | range constraint (weak by physics) | azimuth reliance |
| G9 | E17 (candidate-to-track) | track stability |
| G10 | E17, E18 (cross-frame) | spatial uniqueness |
| G11 | GT coverage (not an evidence gap) | - |

## Implementation Plan

### Step 1: Apply to Stage 1 (L3 validation)
- Run diagnosis on the 37 Stage 1 samples using currently available fields
- Produce gap_category assignment for each sample
- Verify that gap assignments are consistent with the blocked-candidate audit and positive shape audit

### Step 2: Extend to 231 (L2 coverage)
- Run diagnosis on all 231 reviewed samples
- Produce gap distribution across the full reviewed set
- Identify which gaps are Stage 1-specific and which are universal

### Step 3: Prepare for L1 (full-stream)
- Define which gap categories are diagnosable without GT
- Prepare diagnostic fields that can be computed for unlabeled opportunities
- Note: G6 (true no-evidence) and G11 (unlabeled) are inherently non-diagnosable without GT at L1
