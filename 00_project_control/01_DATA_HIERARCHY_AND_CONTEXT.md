# Data Hierarchy and Context

## Level 0: Complete Three-Scene Temporal Streams

The full research universe consists of three complete temporal scenes. Each scene is roughly 15 seconds long and includes:

- optical frame sequence;
- SAR gray frame sequence;
- SAR pseudo-color frame sequence;
- DepthPro output sequence;
- available track context;
- available candidate context.

The final method should return to this level.

## Level 1: Full-Stream Transfer Opportunities

Level 1 consists of all possible vehicle transfer opportunities in the complete temporal stream:

- optical detections;
- optical tracks;
- SAR candidates;
- optical/SAR correspondence opportunities;
- local temporal windows;
- track-level continuity cues.

This is the operational transfer space.

## Level 2: 231 GT-Reviewed Car Samples

The 231 reviewed car samples are **not the full dataset**.

They are the subset with GT or manually reviewed SAR boxes. They are used for:

- supervised evaluation;
- quantitative diagnosis;
- controlled experiments;
- failure analysis;
- validating or rejecting proposed logic.

They are a measurement window into the larger full-stream problem.

## Level 3: Stage Subsets

Stage 1 / Stage 2 / Stage 3 are controlled diagnostic subsets inside Level 2.

They should never replace the Level 0/1 full-stream research objective.

- Stage 1: reliable or widened old range-anchor samples; currently used as a debugging gate.
- Stage 2: bottom-truncated or near-field range-shift samples; should not run until Stage 1 passes.
- Stage 3: multi-range compact hypothesis samples; should not run until Stage 1 and Stage 2 are understood.

## Level 4: Individual Diagnostic Samples

Individual samples are useful as failure case studies but must not become general rules without Level 2/3 validation.

Important examples:

- `gm_rm019_00006`: known structured-clutter false-positive caution case.
- `gm_rm017_00080`: diagnostic-only unless stronger reliable evidence exists.

## Reporting Rule

Every result must state its level:

- L0 complete stream;
- L1 transfer opportunities;
- L2 231 GT-reviewed subset;
- L3 Stage subset;
- L4 diagnostic sample.
