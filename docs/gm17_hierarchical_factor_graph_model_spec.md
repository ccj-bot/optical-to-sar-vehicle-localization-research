# GM17 Hierarchical Factor Graph Model Spec

Date: 2026-06-01

Status: diagnostic model specification. This is not a mainline selector replacement.

GM17 is a staged validation for 光学迁移到SAR中的车辆定位与候选选择. The current track-level selector, B patch, hierarchical diagnostic, and factor graph diagnostic show that fixed-bank selected prediction can be explained by vehicle-state factors. This document standardizes the model form before any weight calibration or selector refactor.

## Boundary

This specification does not allow:

- changing the v2.2 candidate bank
- training a ranker
- training CRF or OOF weights
- replacing the GM17 mainline
- running new performance experiments
- using GT, IoU, center error, or condition labels in inference
- using visible evidence as a direct full-center generator

## Variables

### Complete-Vehicle Variables

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
```

Required fields:

- `r`
- `cross`
- `az`
- `heading`
- `size`
- `direction state`
- `source family`
- `selected candidate`

### Diagnostic Latent Variables

```text
R_t = risk state
D_t = direction state
F_t = source family
C_t = selected candidate
Z_t = final action
```

Allowed states:

- `R_t`: `normal`, `high_risk`, `ambiguous`, `artifact`
- `D_t`: `near`, `pos_escape`, `neg_escape`, `ambiguous`
- `F_t`: `base`, `wedge`, `bidirectional`, `track_signed`, `visible`
- `Z_t`: `keep_base`, `use_path`, `reject`, `uncertain`

### Partial Visibility Variables

Partial visibility is specified here for interface compatibility, but ownership belongs to PartialVisibilityAgent and it should not enter candidate selection before the complete-vehicle mainline is stable.

```text
V_t = visibility state
M_t = missing extent state
O_t = visible/full-center offset
```

Allowed concept states:

- `visibility state`: full, truncated, occluded, truncated+occluded, uncertain
- `missing extent state`: none, range-side missing, azimuth-side missing, mixed, unknown
- `visible/full-center offset`: direction and magnitude of visible support relative to latent full vehicle center

## Factorization

Long-term formal expression:

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

GM17 complete-vehicle diagnostic subset:

```text
P(S_{1:T}, C_{1:T} | X_{1:T})
  proportional to
  phi_geometry
  x phi_direction
  x phi_source
  x phi_sar_structure
  x phi_optical_temporal
  x phi_uncertainty
  x phi_transition
  x phi_final
```

Cost form:

```text
cost_factor = -log(phi_factor + eps)
MAP path = argmin sum_t node_cost(C_t) + sum_t transition_cost(C_{t-1}, C_t)
```

## Factor Definitions

### Geometry Factor

Purpose:

- Scores fan-polar compatibility of candidate range, cross-ray offset, azimuth offset, heading, and size.

Inference-safe fields:

- `r`
- `cross`
- `az`
- `heading`
- `w`
- `h`
- `delta_r_from_pred`
- `delta_cross_from_pred`
- `delta_az_from_pred`
- `refined_geometry_score`
- `geometry_escape_refined_score`

Output:

- 0-1 potential over `C_t` and `S_t`.

### Direction Factor

Purpose:

- Scores compatibility between candidate direction state and signed escape posterior.

Inference-safe fields:

- `candidate_direction_bin`
- `signed_escape_decision`
- `P_near`
- `P_pos_escape`
- `P_neg_escape`
- `P_ambiguous`
- `signed_direction_match`
- `posterior_confidence`
- `posterior_margin`

Output:

- 0-1 potential over `D_t` and `C_t`.

### Source Factor

Purpose:

- Scores whether a source family is trustworthy for the current direction and risk state.

Source families:

- `base`
- `wedge`
- `bidirectional`
- `track_signed`
- `visible`

Inference-safe fields:

- `candidate_source`
- `source_prior`
- `directional_shell_score`
- `track_escape_evidence`
- `signed_direction_match`

Output:

- 0-1 potential over `F_t`, `D_t`, and `C_t`.

### SAR Structure Factor

Purpose:

- Scores SAR structural support and ambiguity around the candidate.

Inference-safe fields:

- `directional_shell_score`
- `geometry_escape_refined_score`
- `track_escape_evidence`
- `escape_conflict_score`
- `E_sar_structure`
- `E_uncertainty`
- `P_ambiguous`
- `P_artifact`

Output:

- 0-1 potential over `C_t` and uncertainty state.

### Optical-Temporal Factor

Purpose:

- Scores consistency with optical track priors mapped to SAR fan-polar coordinates.

Inference-safe fields:

- `optical_temporal_consistency_score`
- `temporal_factor_score`
- `gm17_track_id`
- `sar_frame_num`
- `pred_r`
- `pred_az`
- `pred_cross`

Output:

- soft prior over `S_t` and `C_t`.

Restriction:

- Optical temporal evidence must not hard-lock the full center.

### Transition Factor

Purpose:

- Scores adjacent-frame continuity over candidate state.

Inference-safe fields:

- `r`
- `cross`
- `az`
- `heading`
- `w`
- `h`
- `candidate_direction_bin`
- `signed_escape_decision`
- `optical_temporal_consistency_score`
- `gm17_track_id`
- `sar_frame_num`

Output:

- transition cost between `C_{t-1}` and `C_t`.

### Visibility Factor

Purpose:

- Captures visible support and partial-visibility uncertainty.

Inference-safe fields:

- `visible_factor`
- visible support fields from upstream inference tables
- `P_artifact`
- visibility uncertainty features when available

Output:

- factor, veto, or uncertainty over `V_t`, `M_t`, and `C_t`.

Restriction:

- Visible support cannot directly generate the final full-center candidate.

### Final Arbitration Factor

Purpose:

- Softly chooses final action after risk, direction, source, candidate, path, and uncertainty evidence.

Allowed actions:

- `keep_base`
- `use_path`
- `reject`
- `uncertain`

Inference-safe fields:

- risk potential
- direction potential
- source potential
- candidate potential
- path proposal evidence
- SAR uncertainty
- normal keep signal

Output:

- 0-1 potential over `Z_t`.

## Inference

Required inference method:

- MAP/Viterbi over fixed candidate paths.

Procedure:

1. Build candidate-level potentials from inference-safe fields.
2. Convert potentials to costs using `-log(score + eps)`.
3. Build per-track candidate nodes.
4. Add transition costs between adjacent frames.
5. Run Viterbi dynamic programming.
6. Emit selected inference output without eval-only fields.
7. Join eval fields only in audit outputs.

## Factor Prior Audit Gate

Before any weight calibration, every factor must be recorded in `docs/gm17_factor_prior_registry.md` with:

- `factor_name`
- `factor_type`
- `physical_meaning`
- `expected_direction`
- `inference_safe_fields`
- `current_code_fields`
- `supporting_evidence`
- `failure_cases`
- `risk_if_overweighted`
- `risk_if_underweighted`
- `evidence_grade`
- `should_be_learned_later`

If a factor lacks enough evidence or has severe over-weight risk, it must remain diagnostic-only.

## Current GM17 Interpretation

Current GM17 status:

- Track-level selector is the selected-prediction baseline.
- B patch `sar_uncertainty_penalty_only` is accepted for current GM17 behavior.
- Hierarchical diagnostic reproduced B patch but had too many hard thresholds.
- Factor graph diagnostic reproduced B patch with fewer hard thresholds.

Interpretation:

- The factor graph form is promising as a modeling system.
- The current prototype is not a final physical model.
- Weight calibration and selector refactor require factor prior audit first.
