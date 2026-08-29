# PERSON CMR-D0 common-residual motion mechanism development

- Active workspace: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Output: `D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\cmr_d0_common_residual_motion_mechanism_development`
- `old_work`: archive-only and not used

This task develops, visualizes, and freezes a version-zero mechanism for:

1. optical common apparent motion;
2. optical raw-fragment residual states;
3. frozen-P0-relative SAR q95 response-support residual states;
4. categorical cross-modal residual relations;
5. offline-only raw-fragment grounding.

The task is development, not confirmation.  R04ZF is reserved as the
run-level confirmation pool and is inspected only for input availability before
the CMR-v0 freeze.  No confirmation outcome, weighted score, pruning, tracker,
assignment, identity, P2, final center, or final SAR box is produced.

Final development artifacts include:

- `CMR_RUN_SPLIT_FROZEN_BEFORE_DEVELOPMENT.md` and the eligible-window atlas;
- optical background-GMC/common-residual tables;
- frozen-P0-relative SAR q95 support-residual tables;
- categorical cross-modal residual hypotheses;
- offline-only branch-grounding audit/interface;
- overlaid real-case figures and `CMR_D0_MULTIMODAL_VISUAL_REVIEW_LEDGER.md`;
- frozen CMR-v0 mechanism specification and an unexecuted confirmation protocol;
- an independent validator with manifest-hash checks.

The atlas contains 394 scheduled lag-1 windows across R01ZF-R04ZF and 205
GT-blind cross-modal eligible windows.  The 394 value is a window-row count,
not an eligible branch-instance count.  Development uses 107 windows and 231
continuous raw-fragment instances; R04 remains isolated with 98 input-eligible
windows and no mechanism outcome generated.
