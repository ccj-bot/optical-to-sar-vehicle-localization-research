# Agent Rules and Stage Gates

## Data-Level Rules

Every task must declare its data-level scope:

- L0 complete three-scene temporal streams;
- L1 all transfer opportunities;
- L2 231 GT-reviewed samples;
- L3 Stage subset;
- L4 individual diagnostic sample.

Agents must not confuse these levels.

## Forbidden Runtime Evidence

The following are offline-only and must never become runtime evidence:

- ground truth;
- offline overlap;
- oracle-best;
- already-good labels;
- old-overcompression labels;
- oracle-high/runtime-low labels.

## Stage Gates

Stage 2 must not run until Stage 1 passes.

Stage 3 must not run until Stage 1 and Stage 2 are understood.

No selector may be promoted unless:

1. relevant evaluation level improves;
2. already-good damage is zero;
3. known false-positive cases remain protected;
4. accepted replacements are explainable by runtime evidence;
5. no forbidden evidence is used.

## Current Gate

Current phase:

Full-stream transfer opportunity inventory and positive SAR evidence audit design.

Allowed:

- inventory design;
- evidence-space audit;
- full-stream context organization;
- blocked-candidate analysis;
- positive evidence taxonomy;
- prompt generation;
- report design.

Not allowed:

- Stage 2;
- Stage 3;
- selector promotion;
- threshold relaxation;
- oracle-guided fitting;
- treating 231 as full universe;
- treating Stage 1 as full task;
- new ROI repair rules unless explicitly requested.

## Reporting Requirements

Every output must include:

1. files read;
2. data-level scope;
3. what was run;
4. what was not run;
5. runtime evidence versus offline-only evidence;
6. level-tagged conclusions;
7. gate status;
8. next safe step.
