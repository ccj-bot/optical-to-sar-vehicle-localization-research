# Optical-to-SAR Vehicle State Model Roadmap

Date: 2026-06-01

Project statement: 光学迁移到SAR中的车辆定位与候选选择.

The current GM17 line is a staged validation, not the final system. GM17 has validated that a fixed candidate bank, track-level selector, accepted B patch, hierarchical diagnostic, and factor graph diagnostic can explain and reproduce selected-prediction behavior. The next step is not more patching. The next step is to standardize the model, audit factor priors, then decide whether calibration and selector refactor are justified.

## Boundary

This roadmap does not authorize:

- candidate bank changes
- ranker training
- GM17 mainline replacement
- OOF weight calibration in the current phase
- new performance experiments
- packaging engineering patches as a final physical model
- using visible support as a full-center generator

## System Direction

The long-term system should move from patch experiments to a hierarchical factor graph:

```text
fixed candidate bank
-> vehicle state variables
-> soft factors
-> MAP/Viterbi inference
-> selected candidate
-> audit-gated release decision
```

The total route is:

1. Complete-vehicle optimistic mainline.
2. Partial visibility branch for truncation and occlusion.
3. Hybrid integration after both branches are auditable.

## Complete-Vehicle Mainline

The complete-vehicle mainline handles full vehicle, unoccluded or low-ambiguity scenes first. It should be optimistic in the sense that it assumes the whole vehicle structure is recoverable, but conservative in release behavior.

Variables:

- `r`
- `cross`
- `az`
- `heading`
- `size`
- `direction state`
- `source family`
- `selected candidate`

Core latent state:

```text
S_t = {
  r_t,
  cross_t,
  az_t,
  heading_t,
  size_t,
  direction_state_t,
  source_family_t
}
C_t = selected_candidate_t
Z_t = final_action_t
```

Complete-vehicle factors:

- geometry factor
- direction factor
- source factor
- SAR structure factor
- optical-temporal factor
- uncertainty factor
- transition factor
- final arbitration factor

Inference:

- MAP/Viterbi over fixed candidates.
- No GT or eval fields in inference.
- Candidate bank is a fixed proposal set.
- Optical temporal evidence is a soft prior.
- Visible evidence is only factor, veto, or uncertainty.

## Partial Visibility Branch

The truncation/occlusion branch is delayed until the complete-vehicle mainline is stable.

Partial-visibility variables:

- `visibility state`
- `missing extent state`
- `visible/full-center offset`

Branch state:

```text
V_t = visibility_state_t
M_t = missing_extent_state_t
O_t = visible_full_center_offset_t
```

Partial-visibility factors:

- visibility factor
- missing extent factor
- visible/full-center offset factor
- partial-visibility uncertainty factor

Rules:

- Visible center is not the full vehicle center.
- Visible support must not directly generate the final full-center prediction.
- Visible evidence can veto, downweight, or raise uncertainty.
- Truncation and occlusion must be modeled separately.
- The partial branch should not destabilize the complete-vehicle selector.

## Formal Model

Long-term target expression:

```text
P(S_{1:T}, C_{1:T}, V_{1:T}, M_{1:T} | X_{1:T})
  proportional to
  geometry factor
  x direction factor
  x source factor
  x SAR structure factor
  x optical-temporal factor
  x visibility factor
  x uncertainty factor
  x transition factor
```

Where:

- `S_{1:T}` is the complete-vehicle state sequence.
- `C_{1:T}` is the selected candidate sequence.
- `V_{1:T}` is the visibility state sequence.
- `M_{1:T}` is the missing extent state sequence.
- `X_{1:T}` is the fixed inference-safe observation sequence.

Inference target:

```text
argmax_{S,C,V,M} P(S_{1:T}, C_{1:T}, V_{1:T}, M_{1:T} | X_{1:T})
```

Implementation target:

- Convert factor scores to 0-1 potentials.
- Convert potentials to costs with `-log(score + eps)`.
- Use MAP/Viterbi or equivalent dynamic programming for track-level candidate paths.
- Keep eval-only fields outside inference outputs.

## Long-Term Phases

### Phase 1: Long-Term Subagents And Roadmap

Deliverables:

- `00_project_control/12_OPTICAL_TO_SAR_LONG_TERM_SUBAGENTS.md`
- `docs/optical_to_sar_vehicle_state_model_roadmap.md`
- `docs/gm17_hierarchical_factor_graph_model_spec.md`
- `docs/gm17_factor_prior_registry.md`

Goal:

- Establish the long-term project structure and ownership.
- Freeze the current boundary: no algorithm change, no new experiment, no mainline replacement.

### Phase 2: Complete-Vehicle Mainline Model Specification

Deliverables:

- complete-vehicle state schema
- factor graph variable definitions
- inference-safe field mapping
- MAP/Viterbi pseudocode
- selected-candidate and final-action definitions

Goal:

- Convert the GM17 factor graph diagnostic into a stable model spec.

### Phase 3: Factor Prior Audit

Deliverables:

- factor prior registry
- evidence grade per factor
- over-weight and under-weight risk per factor
- failure-case map
- decision on which factors can later be learned

Goal:

- Audit all factors before weight calibration.

### Phase 4: Fixed-Prior Factor Graph Revalidation

Deliverables:

- fixed-prior inference output
- factor cost decomposition
- B patch reproduction comparison
- boundary report

Goal:

- Revalidate the factor graph after model specification and prior audit, without learned weights.

### Phase 5: Track-Block OOF Weight Calibration

Deliverables:

- track-block split definition
- calibrated factor weights
- leakage audit
- calibration report

Goal:

- Learn or calibrate weights only after factor prior audit passes.

### Phase 6: Complete-Vehicle Factor Graph Selector Prototype

Deliverables:

- selector prototype
- selected prediction audit
- normal regression audit
- hard-case audit
- release decision

Goal:

- Test whether the complete-vehicle factor graph can become a selector candidate.

### Phase 7: Truncation/Occlusion Partial Visibility Modeling

Deliverables:

- visibility state design
- missing extent state design
- visible/full-center offset factor
- partial visibility audit

Goal:

- Add truncation and occlusion modeling without treating visible center as full center.

### Phase 8: Full-Scene Hybrid Integration

Deliverables:

- complete-vehicle branch
- partial-visibility branch
- hybrid arbitration
- full-scene audit and release decision

Goal:

- Integrate the stable complete-vehicle and partial-visibility branches across broader scenes.

## Next Minimal Action

Do not tune or run new experiments yet. The next minimal action is Phase 2: turn the GM17 factor graph diagnostic into a strict complete-vehicle model specification, then use the factor prior registry as the Phase 3 audit checklist.
