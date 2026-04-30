# Positive SAR Vehicle Evidence Taxonomy

Data level: ALL (physical principles apply at all levels; current population is L3 Stage 1; future extends to L1 full-stream)

## Purpose

Define what POSITIVE evidence looks like — evidence that a SAR candidate resembles a vehicle, not merely evidence that it does NOT resemble clutter.

The taxonomy must be separable from the clutter-rejection taxonomy. Clutter rejection answers "why is this NOT a vehicle?" Positive evidence answers "why IS this a vehicle?" Both are necessary. Currently the system has clutter rejection (structured-clutter guard) but insufficient positive evidence.

## Taxonomy Entries

### E1: Compact Vehicle-Sized Body Support
- Physical meaning: bright SAR return occupies a bounded region matching expected vehicle dimensions
- Observable: SAR pseudo-color intensity inside candidate footprint
- How to measure: (1) define an oriented vehicle-sized sub-footprint; (2) compute support concentration inside that sub-footprint; (3) compare against expected vehicle width/length range
- Conditioned by: optical vehicle size range, optical state (complete vs truncated)
- Positive signal: bright return concentrated in a vehicle-sized compact region
- Negative signal: bright return spread across region much larger or smaller than vehicle, or only at isolated points
- Current status: MISSING as a scored feature; brightness fields exist but don't constrain compactness
- Implementation note: use rotated bounding box footprint, not axis-aligned, to respect vehicle orientation

### E2: Footprint-Local Support Concentration
- Physical meaning: vehicle body evidence should be more concentrated INSIDE the candidate footprint than in the IMMEDIATE surrounding background ring
- Observable: SAR pseudo-color intensity inside footprint vs tight local ring
- How to measure: (1) compute mean/intensity inside candidate footprint; (2) compute mean/intensity in a concentric ring just outside (same orientation); (3) ratio or contrast score; (4) penalize if outside-ring is comparably bright
- Conditioned by: optical state (truncation may reduce inner/outer contrast)
- Positive signal: inner footprint significantly brighter/more concentrated than immediate background
- Negative signal: inner and outer have similar brightness (diffuse clutter, road structure)
- Current status: MISSING
- Why important: gm_rm019_00006-type false positives are bright inside the box AND bright outside — local contrast would catch this

### E3: Vehicle-Sized Compactness
- Physical meaning: candidate box aspect ratio and size are compatible with a vehicle
- Observable: candidate geometry (width, length, aspect ratio)
- How to measure: (1) candidate width and length in SAR pixels; (2) aspect ratio = length/width; (3) compare against expected vehicle aspect range (~1.5-3.5 for cars); (4) absolute size check against optical vehicle size range
- Conditioned by: optical heading orientation, vehicle state
- Positive signal: aspect ratio in expected vehicle range; size consistent with optical estimate
- Negative signal: extremely elongated (road-like), square (not car-like), tiny (noise), huge (background structure)
- Current status: partially available — candidate geometry exists in feature tables but is not used as a pre-ranking gate

### E4: Side Evidence
- Physical meaning: vehicle sides produce bright linear SAR returns along the vehicle's long axis
- Observable: SAR intensity along the candidate's left and right long edges
- How to measure: (1) sample intensity along two long edges of the oriented footprint; (2) check for coherent bright segments; (3) compare left vs right side brightness
- Conditioned by: optical heading, truncation state, occlusion
- Positive signal: one or both sides show coherent bright linear return along expected edge
- Negative signal: sides are absent, broken, or no brighter than background
- Current status: EXISTS as feature field (side brightness) but is not localized — same measurement on a road edge would also look like "side evidence"

### E5: Corner Evidence
- Physical meaning: vehicle corners (where side meets end-cap) produce compact bright returns
- Observable: SAR intensity at the four corners of the oriented footprint
- How to measure: (1) locate corners of oriented footprint; (2) sample local intensity around each corner; (3) check for paired corners (front pair, rear pair)
- Conditioned by: optical heading, truncation
- Positive signal: at least one corner pair (front or rear) shows coherent bright returns
- Negative signal: corners are absent, or brightness at corners is not distinguishable from background
- Current status: EXISTS but not paired to body support

### E6: End-Cap Evidence
- Physical meaning: vehicle front and rear ends produce compact returns perpendicular to the side
- Observable: SAR intensity along the candidate's short edges (front cap, rear cap)
- How to measure: (1) sample intensity along front and rear short edges of oriented footprint; (2) check for coherent bright segments
- Conditioned by: optical heading, truncation, occlusion
- Positive signal: at least one end-cap shows coherent bright return
- Negative signal: end-caps absent or indistinguishable from background
- Current status: EXISTS but not paired to body support

### E7: Near-Side / Far-Side Support
- Physical meaning: the side closer to the radar (near-side) typically shows stronger SAR return than the far side
- Observable: SAR intensity asymmetry between candidate's left and right sides
- How to measure: (1) identify near-side and far-side based on radar geometry; (2) compare mean intensity on near-side vs far-side edges and body halves
- Conditioned by: radar geometry, vehicle orientation relative to radar
- Positive signal: near-side shows measurably stronger return than far-side
- Negative signal: both sides equally bright (symmetric clutter), or far-side brighter (unphysical)
- Current status: MISSING

### E8: Expected SAR Response Under Truncation
- Physical meaning: when optical shows a truncated vehicle, only the visible portion should produce SAR evidence
- Observable: SAR evidence localized to the OPTICALLY VISIBLE portion
- How to measure: (1) identify truncated edge from optical state; (2) expect missing or weak SAR evidence on the truncated side; (3) expect evidence concentrated on the non-truncated side
- Conditioned by: optical truncation state (bottom, side, corner)
- Positive signal: SAR evidence concentrated on visible portion, weak or absent on truncated portion
- Negative signal: SAR evidence equally strong on truncated side (suggests candidate is background, not vehicle)
- Current status: MISSING — state-conditioned partial-frame expectation not implemented

### E9: Expected SAR Response Under Occlusion
- Physical meaning: when optical shows occlusion (by another object), SAR evidence may be partially blocked
- Observable: SAR evidence gap at the occlusion location
- How to measure: (1) identify occlusion region from optical; (2) expect reduced or absent SAR return in that region; (3) expect evidence in non-occluded regions
- Conditioned by: optical occlusion state, occluding object position
- Positive signal: evidence consistent with occlusion pattern
- Negative signal: uniform evidence despite occlusion (candidate not matching optical object)
- Current status: MISSING

### E10: Local Contrast
- Physical meaning: vehicle body should contrast against immediate background
- Observable: SAR intensity difference between candidate interior and local background ring
- How to measure: (1) compute intensity histogram inside oriented footprint; (2) compute intensity histogram in tight surrounding ring; (3) contrast metric (e.g., difference in medians, KL divergence)
- Conditioned by: local SAR scene brightness (normalize locally)
- Positive signal: clear contrast peak at vehicle body location
- Negative signal: no distinguishable contrast (diffuse background)
- Current status: MISSING as a localized metric (global brightness exists but not local contrast)

### E11: Temporal Consistency
- Physical meaning: a real vehicle's SAR response should persist across nearby SAR frames
- Observable: candidate body evidence in this SAR frame vs nearby SAR frames
- How to measure: (1) extract candidate evidence in current SAR frame; (2) extract evidence in ±N SAR frames at the same spatial location; (3) measure consistency/correlation of body evidence
- Conditioned by: vehicle motion (moving vehicles may shift), static background (should NOT show temporal variation)
- Positive signal: body evidence persists across frames with expected motion
- Negative signal: evidence appears and disappears randomly (noise), or is static (background clutter)
- Current status: MISSING (temporal neighbors not yet organized)

### E12: Static-Background Rejection
- Physical meaning: static background structures (roads, buildings, barriers) produce persistent SAR returns; vehicles should show frame-to-frame variation
- Observable: difference between current SAR frame and nearby SAR frames at candidate location
- How to measure: (1) subtract or compare current SAR frame with ±N SAR frames; (2) penalize candidates whose evidence is unchanged (static); (3) reward candidates whose evidence shows frame-to-frame variation consistent with vehicle motion
- Conditioned by: vehicle motion (moving vs stationary), scene static structure
- Positive signal: candidate evidence shows temporal variation
- Negative signal: candidate evidence is identical across frames (= static background)
- Current status: MISSING
- Why critical: 36/36 Stage 1 blocked candidates show "static or persistent clutter risk"

### E13: Road-Edge / Long-Edge Rejection
- Physical meaning: road edges and barriers produce long continuous SAR returns; vehicle returns are bounded
- Observable: edge response continuation beyond candidate end-caps
- How to measure: (1) trace edge response along and beyond the candidate's long edges; (2) check whether edge continues beyond both end-caps; (3) penalize candidates whose edges extend well beyond vehicle length
- Positive signal: edge response terminates near candidate end-caps
- Negative signal: edge response continues far beyond candidate boundaries (road, barrier)
- Current status: MISSING

### E14: Support Leakage Outside Vehicle-Sized Footprint
- Physical meaning: vehicle SAR return should be mostly contained within the vehicle footprint; significant bright return outside suggests background structure
- Observable: SAR intensity outside the candidate footprint but nearby
- How to measure: (1) define footprint + margin region; (2) compute fraction of bright support outside the footprint; (3) penalize candidates with high leakage fraction
- Positive signal: bright return mostly inside footprint, low leakage
- Negative signal: significant bright return outside footprint (background structure, road)
- Current status: MISSING

### E15: Cap-Only Rescue Risk
- Physical meaning: a candidate where ONLY an end-cap is bright, but the body is absent, is likely not a vehicle
- Observable: cap evidence vs body evidence ratio
- How to measure: (1) compute cap intensity / body intensity ratio; (2) flag candidates where cap evidence dominates
- Positive signal: body evidence is primary, cap evidence is supportive
- Negative signal: cap evidence is strong but body evidence is weak (possible non-vehicle structure)
- Current status: MISSING as explicit guard

### E16: Current-Mainline Proxy Comparison
- Physical meaning: the current mainline box provides a baseline SAR evidence pattern
- Observable: candidate evidence vs current-mainline evidence at the same location
- How to measure: (1) extract evidence features for current mainline box; (2) extract same features for candidate; (3) compare; (4) require candidate to beat current on POSITIVE body evidence, not just raw score
- Positive signal: candidate shows measurably better body compactness/concentration than current
- Negative signal: candidate "wins" on raw score but body evidence is weaker
- Current status: EXISTS (current_protection feature) but relies on raw score comparison, not specific body-evidence comparison

### E17: Candidate-to-Track Consistency
- Physical meaning: a candidate should be consistent with the optical track it belongs to
- Observable: candidate position, size, and orientation relative to track history
- How to measure: (1) project candidate SAR box back to optical frame; (2) compare with track box trajectory; (3) check for sudden jumps, size changes, or orientation shifts
- Positive signal: candidate is consistent with track history
- Negative signal: candidate position/size/orientation is inconsistent with track (possible wrong vehicle or background)
- Current status: MISSING (track context not used in candidate evaluation)

### E18: Cross-Frame Evidence Consistency
- Physical meaning: if the same track is evaluated at multiple optical frames, SAR evidence should be consistent
- Observable: candidate evidence patterns at frame t vs frame t+1 for the same track
- How to measure: (1) identify transfer opportunities for the same track across nearby frames; (2) compare evidence patterns; (3) penalize frame-to-frame inconsistency
- Positive signal: evidence pattern is stable or smoothly changing across frames
- Negative signal: evidence pattern jumps erratically (track mismatch or noise)
- Current status: MISSING (cross-frame not implemented)

## Taxonomy Summary: Current Status

| evidence_id | name | status | critical_for |
|-------------|------|--------|-------------|
| E1 | compact vehicle-sized body support | MISSING | primary positive evidence |
| E2 | footprint-local support concentration | MISSING | separating vehicle from background |
| E3 | vehicle-sized compactness | PARTIAL | candidate pre-ranking |
| E4 | side evidence | EXISTS but unlocalized | body structure |
| E5 | corner evidence | EXISTS but unpaired | body structure |
| E6 | end-cap evidence | EXISTS but unpaired | body structure |
| E7 | near-side/far-side support | MISSING | physical consistency |
| E8 | response under truncation | MISSING | state-conditioned expectation |
| E9 | response under occlusion | MISSING | state-conditioned expectation |
| E10 | local contrast | MISSING | body-to-background separation |
| E11 | temporal consistency | MISSING | static clutter rejection |
| E12 | static-background rejection | MISSING | static clutter rejection |
| E13 | road-edge/long-edge rejection | MISSING | structured clutter rejection |
| E14 | support leakage | MISSING | footprint validity |
| E15 | cap-only rescue risk | MISSING | false positive prevention |
| E16 | current-mainline comparison | EXISTS but body-agnostic | replacement decision |
| E17 | candidate-to-track consistency | MISSING | identity verification |
| E18 | cross-frame evidence consistency | MISSING | temporal verification |

## Implementation Priority

Phase 1 (minimum positive evidence before any rerun):
- E1: compact vehicle-sized body support
- E2: footprint-local support concentration
- E3: vehicle-sized compactness (pre-ranking)

Phase 2 (clutter separation):
- E10: local contrast
- E12: static-background rejection
- E13: road-edge/long-edge rejection
- E14: support leakage
- E15: cap-only rescue risk

Phase 3 (state conditioning and temporal):
- E8: response under truncation
- E9: response under occlusion
- E11: temporal consistency
- E7: near-side/far-side support

Phase 4 (track-level):
- E17: candidate-to-track consistency
- E18: cross-frame evidence consistency
