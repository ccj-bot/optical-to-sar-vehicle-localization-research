# Research Directions and Design Space

## Main Research Direction

The project should be redesigned around the complete three-scene temporal stream, while using the 231 GT-reviewed samples as evaluation and diagnostic anchors.

The next stage should not blindly continue the latest Stage 1 pipeline. It should first clarify the full-stream transfer opportunity inventory and the missing positive SAR vehicle evidence.

## Design Spaces

### 1. Full-Stream Inventory

Map the complete three-scene temporal stream:

- optical frames;
- SAR gray frames;
- SAR pseudo-color frames;
- DepthPro frames;
- tracks;
- candidate pools;
- correspondence opportunities;
- local temporal windows.

### 2. Optical Vehicle-State Interpretation

Refine how optical state produces bounded search constraints:

- complete vehicle;
- truncation;
- occlusion;
- edge contact;
- nearby objects;
- identity drift;
- jitter;
- depth trend;
- field-of-view position.

### 3. Azimuth Transfer

Preserve empirical azimuth mapping as a relatively strong constraint, while verifying it at the full-stream level.

### 4. Weak Range Transfer

Use range only as a weak, state-conditioned constraint. Do not treat DepthPro as metric radar range.

### 5. Candidate Geometry and Membership

Separate:

- centroid inclusion;
- polygon overlap;
- boundary overlap;
- weak overlap;
- outside candidates;
- source-center consistency.

### 6. Positive SAR Vehicle Evidence

Develop positive evidence, not only clutter rejection:

- vehicle-sized compact body support;
- body-to-background contrast;
- side/corner/end arrangement consistency;
- support concentration inside expected footprint;
- limited leakage;
- short-window persistence of vehicle-like structure.

### 7. Temporal Consistency

Eventually return to full-stream temporal consistency:

- track continuity;
- optical/SAR local window alignment;
- vehicle-size consistency;
- heading consistency;
- response pattern continuity.

### 8. Batch Policy

The final pipeline should support:

- accept;
- fallback;
- diagnostic-only;
- remap;
- quarantine.

It should not force automatic replacement when evidence is insufficient.

## Current Recommended Next Direction

Full-stream transfer opportunity inventory and positive SAR evidence audit design.
