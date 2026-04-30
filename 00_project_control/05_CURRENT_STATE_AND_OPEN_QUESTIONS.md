# Current State and Open Questions

## Current State

The project should not continue the current Stage 1 path unchanged.

The latest repaired Stage 1 rerun was a Level 3 controlled diagnostic result. It showed safety but no improvement:

- all-231 current mean: 0.491366;
- all-231 with Stage 1 fallback mean: 0.491366;
- Stage 1 current mean: 0.452578;
- Stage 1 rerun mean: 0.452578;
- accepted replacements: 0;
- rejected replacements: 37;
- already-good damage count: 0;
- structured-clutter blocked candidate rows: 12973 across 36 samples;
- boundary-overlap selected count: 17, accepted 0;
- weak-fallback usage count: 1;
- `gm_rm019_00006` stayed protected;
- `gm_rm017_00080` stayed diagnostic-only.

## Interpretation

This proves the repaired policy can prevent known false positives and avoid damage.

It does not prove the selector can improve the task.

The current system is safe but too conservative.

## Current Blocker

The likely blocker is missing positive SAR vehicle evidence.

The system can reject structured clutter but cannot yet identify trustworthy replacement candidates.

## Open Questions

1. What are all Level 1 transfer opportunities in the full three-scene stream?
2. How do the 231 GT-reviewed samples map back to Level 0/1 scene, frame, track, and candidate context?
3. Is the current candidate generation adequate, or does it miss positive vehicle structures?
4. Are structured-clutter guards over-blocking, or are candidates genuinely weak?
5. What positive vehicle-shape evidence is missing?
6. How should temporal consistency contribute without becoming a standalone selector?
7. How should Level 3 Stage 1 evidence feed back into Level 0/1 design?
8. Should the current direction be partially redesigned before more selector experiments?

## Current Recommendation

Partially redesign the research direction before running more selector experiments.

Do not run Stage 2, Stage 3, or threshold relaxation.
