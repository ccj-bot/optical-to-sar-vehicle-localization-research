# TERG-R0 Frozen Reasoning Specification

- Explanation unit: one segment-level joint world selecting one frozen TERG-v1 family per optical track.
- Domains: all frozen TERG-v1 upper component families; no optional-edge deletion.
- Active hard constraint: consistent definite optical raw-interval order on every jointly available optical frame, intersected with uniformly opposite SAR family-pair geometry on every common SAR support frame.
- No common SAR support: admissible, not false.
- Any aligned, overlap, or shared relation: admissible.
- Timing offset: unresolved; nominal frame equality is not hard authority.
- Inference: exact finite-domain Boolean factor intersection and sum-product marginal counting.
- Family statuses: LOGICALLY_EXCLUDED, NECESSARY_IN_ALL_POSSIBLE_WORLDS, CONDITIONALLY_ADMISSIBLE, UNCONDITIONALLY_ADMISSIBLE_WITH_RESPECT_TO_R0.
- Forbidden: score, threshold, vote, top-k, assignment, tracker, factor-graph expansion, P2, final center, final box.
- Reference: inaccessible until the pre-reference hash manifest is written; post-reference is evaluation only.
