# Stage 1 Diagnostic Interpretation

Data level: L3-to-ALL (Stage 1 evidence interpreted for full-stream design)

## Reference: Latest Stage 1 Repaired Rerun (2026-04-27)

Outcome:
- accepted replacements: 0
- rejected replacements: 37 (of 37 eligible)
- already-good damage: 0
- structured-clutter blocked candidate rows: 12973 across 36 samples
- boundary-overlap selected count: 17, accepted: 0
- weak-fallback usage: 1
- gm_rm019_00006: stayed protected (correct)
- gm_rm017_00080: stayed diagnostic-only (correct)
- Stage 1 mean IoU: 0.452578 (unchanged — no replacements)
- all-231 mean IoU: 0.491366 (unchanged)

## 1. What Stage 1 Proved

### Proven: The repaired policy prevents known damage
- Zero already-good damage: no current-mainline box was accidentally degraded.
- gm_rm019_00006 stayed protected: the known structured-clutter false positive was correctly blocked.
- gm_rm017_00080 stayed diagnostic-only: the policy correctly refused to replace a sample that lacks strong geometry evidence.

### Proven: Structured-clutter guard is doing real safety work
- 12973 candidate rows blocked across 36 samples.
- The guard is not over-blocking randomly — it is systematically rejecting candidates whose structural features resemble static background clutter rather than vehicle structure.

### Proven: The system is safe but too conservative
- 37 samples had candidates. 37 were rejected. Zero were accepted.
- The policy is correctly losing on the right side: it avoids damage, but it cannot find any candidate it trusts enough to replace the current mainline.

### Proven: Candidate pools exist but candidate quality is insufficient
- Candidates exist for 37 Stage 1 samples. They were evaluated. They were rejected.
- The problem is not that candidates don't exist — it's that none of them have enough positive vehicle evidence to beat the current mainline with the required margin.

## 2. What Stage 1 Did NOT Prove

### NOT proven: The selector approach is fundamentally wrong
- Stage 1 proved that the current feature set + current candidate pool + current policy cannot improve.
- It did NOT prove that no optical-to-SAR transfer approach can work.
- It proved the current implementation is insufficient, not that the problem is unsolvable.

### NOT proven: Relaxing thresholds would help
- The 37 rejections were not "close calls." The blocked-candidate audit showed:
  - 35/36 structured-clutter blocked samples had "bright but diffuse body evidence"
  - 35/36 had "edge/corner without frame closure"
  - 36/36 had "static or persistent clutter risk"
- Relaxing the guard would admit candidates that the system correctly identifies as static clutter.

### NOT proven: The azimith/range model is wrong
- Stage 1 used azimuth mapping as a relatively strong constraint, and range as a weak constraint.
- Zero accepted replacements does not imply the model is wrong — it implies the SAR evidence side is too weak to confirm a positive identification even within the correct search region.

### NOT proven: 231 samples represent the full transfer problem
- Stage 1 only tested 37 samples (16% of 231, unknown fraction of full-stream opportunities).
- The fact that 37/37 were rejected at Stage 1 says nothing about the 194 non-Stage 1 samples or the unlabeled full-stream opportunities.

## 3. Why Stage 1 Cannot Serve as Basis for Stage 2/3

### Reason 1: Stage 1 has no working positive evidence mechanism
- Stage 2 (bottom-truncated, near-field range-shift) would face the same positive evidence gap.
- Stage 3 (multi-range compact hypothesis) would also face the same gap.
- Running Stage 2/3 before fixing the positive evidence gap would produce the same result: 0 accepted replacements.

### Reason 2: Stage 2/3 have HARDER optical states
- Stage 2: bottom-truncated or near-field — optical state is LESS reliable, not more.
- Stage 3: multi-range — range uncertainty is HIGHER, not lower.
- If Stage 1 (the "easiest" subset with reliable range anchors) cannot accept anything, Stage 2/3 certainly cannot.

### Reason 3: The blocker is feature design, not sample selection
- The gap is "missing positive SAR vehicle evidence features" — this is a SYSTEM-LEVEL gap, not a sample-subset gap.
- Moving to a different subset does not fix missing features.

### Reason 4: Stage gate logic
- Stage gate rules state: Stage 2 must not run until Stage 1 passes.
- Stage 1 did not pass (0 accepted improvements, promotion not met).
- Conclusion: Stage 2/3 remain blocked. This is correct.

## 4. Why Stage 1 Indicates Missing Positive SAR Vehicle Evidence

### Direct evidence from the blocked-candidate audit
- 35/36 blocked candidates have "bright but diffuse body evidence"
- SAR responses are bright, but the brightness is NOT localized as a compact vehicle body
- Side/cap/corner features detect structure, but that structure is not frame-closed (35/36)
- Static/persistent clutter risk is present in 36/36 — the brightness could be static background

### Direct evidence from the positive shape audit
- Only 1/37 Stage 1 best-blocked candidates shows "positive compact body evidence"
- The other 36 show bright SAR response that the system correctly recognizes as non-vehicle-like

### The gap in one sentence
The system can see brightness in the SAR frame. It can detect side-like, cap-like, and corner-like structures. But it cannot tell whether that brightness is a vehicle body or static background clutter — so it correctly defaults to "reject."

## 5. How Stage 1 Feeds Back to Full-Stream Transfer Opportunity Design

### Feedback 1: Transfer opportunities need vehicle-state-conditioned SAR expectations
- The optical state (complete, truncated, occluded) should inform what SAR evidence is EXPECTED.
- A truncated vehicle should not be required to show full-frame closure.
- A complete vehicle SHOULD show body + side + cap + corner in arrangement.

### Feedback 2: Candidate generation needs compactness pre-ranking
- Many blocked candidates have non-vehicle-like size/aspect.
- Pre-ranking candidates by vehicle-sized compactness before scoring would reduce noise entering the decision stage.

### Feedback 3: The evidence space is incomplete
- The current feature set has brightness-based fields (side, cap, corner, body) but lacks:
  - Footprint-local body-to-background contrast
  - Support concentration inside expected vehicle footprint
  - Static-subtracted (temporal-difference) body evidence
  - Long-edge continuation rejection

### Feedback 4: Transfer opportunities at L1 must include all temporal frames, not just single snapshots
- Static clutter rejection requires comparing current SAR frame against nearby SAR frames.
- This requires temporal context at L1, not just L0.

## 6. How Stage 1 Feeds Back to SAR Evidence Taxonomy

### The taxonomy must separate:
1. Brightness (detected) vs. Vehicle-body brightness (NOT yet detected)
2. Side/cap/corner structure (detected) vs. Frame-consistent vehicle structure (NOT yet detected)
3. Candidate existence (detected) vs. Candidate body compactness (NOT yet scored)

### The taxonomy must include:
- Compact vehicle-sized body support (currently MISSING as a scored feature)
- Footprint-local concentration (currently MISSING)
- Static-subtracted support (currently MISSING for 36/36)
- Frame-closure consistency (currently WEAK for 35/36)
- Long-edge continuation rejection (currently MISSING)

## 7. How to Avoid Misinterpreting Stage 1

### Wrong interpretation: "Just relax the structured-clutter guard"
- Why wrong: 36/36 blocked candidates have static/persistent clutter risk. Relaxing the guard would admit clutter.

### Wrong interpretation: "The azimith/range model needs fixing"
- Why wrong: Stage 1 candidates are inside the azimuth/range search region. The problem is SAR evidence inside the region, not the region itself.

### Wrong interpretation: "We need more candidates per sample"
- Why wrong: Stage 1 already has candidate pools (12973 candidate rows). More candidates would not help — the blocker is that none of them look like vehicles.

### Wrong interpretation: "Stage 1 failed so we should skip to Stage 2"
- Why wrong: Stage 2 has harder optical states and higher range uncertainty. Skipping ahead is guaranteed failure.

### Correct interpretation: "We need better positive vehicle evidence before any more reruns"
- The system is correct to reject. We need to give it better evidence, not lower its standards.
