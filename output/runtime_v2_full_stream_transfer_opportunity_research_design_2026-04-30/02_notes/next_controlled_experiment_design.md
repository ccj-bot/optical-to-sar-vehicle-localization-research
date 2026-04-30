# Next Controlled Experiment Design

Data level: L3-first, L2-validated, L1-ready

## Design Principle

The next experiment must:
1. Start at the most controlled level (L3 Stage 1) where we have the most diagnostic data
2. NOT repeat the Stage 1 repaired rerun (which already proved safety and lack of positive evidence)
3. Focus on POSITIVE EVIDENCE FEATURE IMPLEMENTATION, not threshold tuning or policy adjustment
4. Produce results that can escalate to L2 and L1
5. Have clear promotion gates that are gated on positive evidence, not on replacing more samples

## Experiment: Stage 1 Positive Evidence Feature Validation

### Goal
Validate that Phase 1 positive evidence features (E1: compact body support, E2: footprint-local concentration, E3: compactness pre-rank) can identify candidates with genuine vehicle-like body evidence, using the 37 Stage 1 samples as a controlled diagnostic set.

### NOT the goal
- NOT to achieve more replacements
- NOT to promote Stage 1
- NOT to run Stage 2/3
- NOT to relax any guard

### Data level scope
- Primary: L3 (37 Stage 1 samples)
- Validation: L2 (cross-check against remaining 194 reviewed samples)
- Design goal: L1-ready (features must be computable without GT)

### Experiment Steps

#### Step 1: Implement Phase 1 features (offline, diagnostic mode)
- Compute E1 (compact vehicle-sized body support) for all Stage 1 candidates
- Compute E2 (footprint-local support concentration) for all Stage 1 candidates
- Compute E3 (vehicle-sized compactness) and use as candidate pre-rank

Runtime-observable inputs only:
- SAR pseudo-color crop at candidate location
- Candidate footprint (rotated)
- Optical vehicle state (for conditioning size expectations)
- NO offline overlap, NO GT, NO oracle labels

#### Step 2: Diagnostic audit (no rerun)
For each Stage 1 sample, answer:
- Does the best candidate show positive compact body support (E1)?
- Does the best candidate show footprint-local concentration (E2) distinguishing it from background?
- Would compactness pre-ranking (E3) change which candidate is selected as "best"?
- Does the positive evidence override or complement the structured-clutter guard assessment?

Output: a diagnostic table comparing "before" (current best blocked) vs "after" (best by E1+E2+E3 metrics) for each sample.

#### Step 3: Controlled partial rerun (only if Step 2 justifies it)
- IF Step 2 identifies candidates with genuine positive body evidence that were previously blocked
- AND those candidates are NOT gm_rm019_00006-type false positives
- AND the evidence is physically interpretable (not just a score number)
- THEN: run a DIAGNOSTIC-ONLY rerun where:
  - E1+E2 positive body evidence is added to the scorer
  - The structured-clutter guard is NOT relaxed
  - Current-mainline protection is maintained
  - Replacements are logged but NOT automatically applied
  - Decision: diagnostic-only (no promotion)

#### Step 4: Interpret results
- Did any candidate show genuine positive body evidence?
- Did that evidence change the rejection decision?
- Was gm_rm019_00006 still correctly blocked?
- Was gm_rm017_00080 still correctly diagnostic-only?
- Were any already-good samples damaged?

### What to Validate on L3 Stage 1 First

1. **E1 feature correctness**: Does compact body support correctly identify candidates that look vehicle-like vs diffuse/bright candidates?
2. **E2 feature discriminability**: Does footprint-local concentration separate vehicle bodies from nearby bright background?
3. **E3 pre-ranking safety**: Does compactness pre-ranking exclude valid candidates or only noise?
4. **Guard interaction**: Does positive evidence complement the structured-clutter guard without creating bypass paths for false positives?
5. **gm_rm019_00006 regression**: Does the false-positive sample still get blocked?

### How to Avoid Re-Entering Stage 1-Only Mode

- Set a MAXIMUM of ONE diagnostic rerun with Phase 1 features
- After that, regardless of outcome, ESCALATE to L2 (all 231) for feature validation coverage
- Do NOT iterate on Stage 1 thresholds — if features don't help, the features are wrong, not the thresholds

### How to Feed Results Back to L1 Full-Stream Opportunities

- Phase 1 features must use runtime-observable inputs only
- After L3 validation, the same features can be computed for any L1 transfer opportunity (once candidate pools exist)
- The diagnostic audit table format should be designed for L1 scale from the start
- Note: L1 opportunities without candidates still cannot be evaluated — this is a G2 (candidate generation) gap, not an evidence gap

### Which Samples Are Suitable for Positive Evidence Audit

**Suitable (L3 Stage 1, 14 eligible automatic-rerun samples):**
- Samples where candidates exist and are not clearly static clutter
- These are the most controlled test — if positive evidence cannot find a vehicle-like candidate here, it won't work elsewhere

**Suitable for diagnostic-only (L3 Stage 1, 22 current-protected fallback):**
- Samples with strong current-mainline boxes — the bar for replacement is higher
- These validate that positive evidence does NOT cause false replacements

**Not yet suitable (L3 Stage 2/3):**
- Stage 2 (bottom-truncated, near-field): harder optical states, need Phase 3 features (E8, E9)
- Stage 3 (multi-range): need Phase 2 clutter separation features settled first

### Which Need Full-Stream Temporal Context (not yet ready)

- Samples where G4 (temporal context missing) is the primary gap
- These need Phase 2 features (E11, E12) before they can be evaluated
- Do NOT run these yet — temporal feature design is a separate task

### When to Allow Rerun Selector

Only after ALL of:
1. Phase 1 positive evidence features (E1, E2, E3) are implemented and validated on Stage 1
2. Diagnostic audit shows at least ONE candidate has genuine positive body evidence that was previously missed
3. gm_rm019_00006 remains correctly blocked with new features active
4. No already-good damage in diagnostic rerun

### When Stage 2/3 Remain Blocked

Stage 2/3 remain blocked until:
1. Phase 1+2 features are validated on L3 and L2
2. Stage 1 passes promotion gates (improvement + safety)
3. Stage 2/3-specific features (E8, E9 for truncation/occlusion) are implemented

Current status: Stage 2/3 are NOT close to being unblocked.

### Promotion Gate for Stage 1

Stage 1 promotion requires ALL of:
1. accepted_replacement_count > 0 (at least one candidate accepted)
2. already_good_damage_count = 0
3. gm_rm019_00006 stays protected
4. gm_rm017_00080 stays diagnostic-only (unless E8/E9 features justify)
5. Each accepted replacement is EXPLAINABLE by runtime positive body evidence (E1+E2), not just a score number
6. Replacement explanation can be stated in physical terms: "this candidate shows a compact vehicle-sized body with X% higher concentration than background, consistent with a complete vehicle at heading Y"

### What NOT to Do in This Experiment

- Do NOT compute E1/E2 using offline overlap or GT as input (features must be runtime-observable)
- Do NOT relax the structured-clutter guard
- Do NOT lower the replacement margin (0.035 normal / 0.07 current-protected)
- Do NOT add new candidate sources before validating existing ones
- Do NOT run Stage 2 or Stage 3
- Do NOT promote Stage 1 based on diagnostic runs
- Do NOT iterate on thresholds — if feature doesn't help, redesign the feature
