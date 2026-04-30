# Prior Work as Evidence

Previous work should be treated as evidence, not as a binding methodology.

## Reliable Evidence

The following conclusions remain valuable:

1. Optical-to-SAR azimuth migration is more reliable than range migration.
2. Range migration is weaker because calibrated intrinsics and camera-to-radar extrinsics are missing.
3. DepthPro is useful as weak relative near/middle/far or temporal trend evidence, not exact radar range.
4. Current-mainline proxy protection is necessary to avoid unsafe replacement.
5. Candidate coverage and structural feature coverage must be verified before scoring experiments.
6. `gm_rm019_00006` is an important structured-clutter false-positive case.
7. `gm_rm017_00080` should remain diagnostic-only unless stronger geometry/evidence exists.
8. The 231 GT-reviewed samples are valuable as a Level 2 evaluation and diagnostic subset.

## Controlled Diagnostic Evidence

Stage 1 repaired rerun:

- accepted replacements: 0;
- already-good damage count: 0;
- previous false positive stayed protected;
- no improvement was achieved.

This indicates that the system became safer but too conservative.

## Current Interpretation

The latest Stage 1 evidence suggests that the current blocker is missing positive SAR vehicle evidence.

The system can reject structured clutter but cannot yet confidently identify safe positive replacements.

## Demoted History

The following should be treated as diagnostic history, not as current methodology:

- blind ROI repair;
- hard-sample rescue as the main task;
- threshold relaxation;
- oracle-guided fitting;
- automatic replacement chasing;
- treating Stage 1 as the project center;
- treating the 231 samples as the complete research universe.

## Forbidden Runtime Evidence

The following may be used only for offline diagnosis, never as runtime evidence:

- ground truth;
- offline overlap;
- oracle-best labels;
- already-good labels;
- old-overcompression labels;
- oracle-high/runtime-low labels.
