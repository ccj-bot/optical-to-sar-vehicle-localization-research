

# FILE: 00_RESEARCH_BRIEF.md


# Research Brief: Full-Stream Optical-to-SAR Vehicle Transfer

## Research Purpose

This project studies how to transfer vehicle information from optical imagery into SAR space.

The final research object is **not** only the 231 GT-reviewed car samples and not only the Stage 1 subset. The final research object is the **complete temporal stream of three scenes**, each roughly 15 seconds long, with optical frames, SAR gray frames, SAR pseudo-color frames, DepthPro outputs, and available track/candidate context.

The goal is to design a physically interpretable, batch-deployable optical-to-SAR vehicle transfer method that can eventually operate over complete scene streams.

## Data-Level Framing

The research must keep these levels separate:

- **Level 0:** Complete three-scene temporal streams.
- **Level 1:** All vehicle detections, tracks, candidates, and optical/SAR transfer opportunities in the full stream.
- **Level 2:** 231 GT-reviewed car samples used as supervised evaluation and diagnostic windows.
- **Level 3:** Stage 1 / Stage 2 / Stage 3 controlled subsets inside the 231 GT-reviewed subset.
- **Level 4:** Individual diagnostic samples, such as `gm_rm019_00006` or `gm_rm017_00080`.

Every future task, table, report, and conclusion must explicitly state which level it addresses.

## Core Physical Idea

Optical and SAR observe the same physical vehicle in the same scene, but through different sensing mechanisms.

Optical information should not be copied into SAR as a final box. Optical information should provide bounded search constraints, vehicle-state interpretation, uncertainty estimates, and temporal consistency cues.

SAR evidence must confirm the final vehicle support.

## Working Model

The current physically plausible model is:

**empirical optical-to-SAR azimuth mapping + weak relative depth/range hints + optical vehicle-state interpretation + SAR local evidence confirmation**.

This is not a strict 3D projection model because the project does not have calibrated camera intrinsics or calibrated camera-to-radar extrinsics.

## Operating Principle

**Strong optical search-space compression, escapable SAR final decision.**

The optical side should strongly reduce where SAR needs to search. The SAR side must confirm final vehicle support through local SAR evidence.

## What This Project Is Not

This project should not be reduced to:

- ROI repair;
- hard-sample rescue;
- Stage 1-only debugging;
- threshold tuning;
- oracle-guided fitting;
- 231-only optimization;
- automatic replacement chasing.

Previous work is evidence and experience, not a binding methodology.


# FILE: 01_DATA_HIERARCHY_AND_CONTEXT.md


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


# FILE: 02_AVAILABLE_DATA_AND_ASSUMPTIONS.md


# Available Data and Assumptions

## Available Data

The project has:

- complete optical frame sequences for three scenes;
- SAR gray frame sequences;
- SAR pseudo-color frame sequences;
- DepthPro outputs;
- track context where available;
- SAR candidate pools;
- empirical optical-to-SAR azimuth mapping;
- 231 GT-reviewed car samples with manually reviewed SAR boxes;
- prior ROI, range, candidate, and SAR evidence experiments.

## Missing Calibration

The project does not have:

- calibrated camera intrinsics;
- calibrated camera-to-radar extrinsics;
- strict metric 3D camera-to-SAR projection.

Camera and radar are physically close and roughly similar in height, which supports empirical directional constraints but not exact metric projection.

## Optical Information That Can Transfer

Optical information may provide bounded constraints and state cues:

1. vehicle center direction;
2. approximate heading or heading uncertainty;
3. visible vehicle support;
4. vehicle size range;
5. field-of-view position;
6. bottom truncation;
7. side truncation;
8. edge contact;
9. occlusion state;
10. nearby-object ambiguity;
11. track stability;
12. possible identity drift;
13. short-window temporal consistency;
14. weak relative depth or near/middle/far cues from DepthPro.

## Optical Information That Cannot Transfer Directly

Optical information cannot directly provide:

1. final SAR box;
2. SAR pseudo-color intensity;
3. radar return strength;
4. exact SAR range;
5. exact vehicle boundary in SAR;
6. optical texture, color, or shadow as SAR evidence.

## SAR Evidence Must Confirm

SAR evidence should confirm:

- compact vehicle-sized body support;
- side evidence;
- corner evidence;
- end-cap evidence;
- near-side response;
- local contrast;
- consistency with expected vehicle footprint;
- temporal consistency where available.

SAR evidence should reject:

- isolated peaks;
- road-edge-like long structures;
- static background clutter;
- diffuse support;
- support leakage outside vehicle-sized footprint;
- cap-only rescue;
- nearby wrong vehicle-like structures.


# FILE: 03_PRIOR_WORK_AS_EVIDENCE.md


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


# FILE: 04_RESEARCH_DIRECTIONS_AND_DESIGN_SPACE.md


# Research Directions and Design Space

## Main Research Direction

The project should be redesigned around the complete three-scene temporal stream, while using the 231 GT-reviewed samples as evaluation and diagnostic anchors.

The next stage should not blindly continue the latest Stage 1 pipeline. It should first clarify the full-stream transfer opportunity inventory and the missing positive SAR vehicle evidence.

## Design Spaces

### 1. Full-Stream Inventory

Map the complete three-scene temporal stream:

- optical frames;
- SAR gray frames;
- SAR pseudo-color frames;
- DepthPro frames;
- tracks;
- candidate pools;
- correspondence opportunities;
- local temporal windows.

### 2. Optical Vehicle-State Interpretation

Refine how optical state produces bounded search constraints:

- complete vehicle;
- truncation;
- occlusion;
- edge contact;
- nearby objects;
- identity drift;
- jitter;
- depth trend;
- field-of-view position.

### 3. Azimuth Transfer

Preserve empirical azimuth mapping as a relatively strong constraint, while verifying it at the full-stream level.

### 4. Weak Range Transfer

Use range only as a weak, state-conditioned constraint. Do not treat DepthPro as metric radar range.

### 5. Candidate Geometry and Membership

Separate:

- centroid inclusion;
- polygon overlap;
- boundary overlap;
- weak overlap;
- outside candidates;
- source-center consistency.

### 6. Positive SAR Vehicle Evidence

Develop positive evidence, not only clutter rejection:

- vehicle-sized compact body support;
- body-to-background contrast;
- side/corner/end arrangement consistency;
- support concentration inside expected footprint;
- limited leakage;
- short-window persistence of vehicle-like structure.

### 7. Temporal Consistency

Eventually return to full-stream temporal consistency:

- track continuity;
- optical/SAR local window alignment;
- vehicle-size consistency;
- heading consistency;
- response pattern continuity.

### 8. Batch Policy

The final pipeline should support:

- accept;
- fallback;
- diagnostic-only;
- remap;
- quarantine.

It should not force automatic replacement when evidence is insufficient.

## Current Recommended Next Direction

Full-stream transfer opportunity inventory and positive SAR evidence audit design.


# FILE: 05_CURRENT_STATE_AND_OPEN_QUESTIONS.md


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


# FILE: 06_AGENT_RULES_AND_STAGE_GATES.md


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


# FILE: 07_NEXT_RESEARCH_TASK.md


# Next Research Task

## Task Name

Full-stream transfer opportunity inventory and positive SAR evidence audit design.

## Purpose

The project should shift from Stage 1 rerun attempts to full-stream research design.

Stage 1 repaired rerun showed safety but no improvement. The likely missing component is positive SAR vehicle evidence, not another threshold adjustment.

## Task Goals

1. Define the Level 0 full-stream inventory that future tasks need.
2. Define Level 1 transfer opportunities: detections, tracks, candidates, optical/SAR correspondence windows.
3. Map the 231 GT-reviewed samples back to scene, frame, track, and candidate context.
4. Use Stage 1 outcomes as diagnostic evidence, not as the main pipeline.
5. Define a positive SAR vehicle evidence taxonomy.
6. Separate positive evidence gaps from candidate generation gaps and guard over-blocking.
7. Produce a safe next experimental plan.

## Required Outputs

1. full-stream inventory design;
2. Level 0/1/2/3/4 scope table;
3. transfer opportunity schema;
4. 231-to-full-stream mapping requirements;
5. positive SAR vehicle evidence taxonomy;
6. structured-clutter rejection versus positive vehicle evidence comparison;
7. Stage 1 lessons translated into full-stream design constraints;
8. next controlled experiment proposal;
9. post log;
10. files-read table.

## Forbidden Actions

Do not:

1. run Stage 2;
2. run Stage 3;
3. rerun selector unless explicitly requested;
4. relax thresholds;
5. tune to oracle or overlap;
6. promote the selector;
7. treat 231 as the full universe;
8. treat Stage 1 as the full task.


# FILE: 08_RAG_SOURCE_INDEX.md


# RAG Source Index

## Principle

Do not treat the entire `output/` folder as equal memory.

Older outputs may contain rejected strategies, obsolete assumptions, or heuristic repairs.

## Highest Priority Sources

1. `00_RESEARCH_BRIEF.md`
2. `01_DATA_HIERARCHY_AND_CONTEXT.md`
3. `02_AVAILABLE_DATA_AND_ASSUMPTIONS.md`
4. `03_PRIOR_WORK_AS_EVIDENCE.md`
5. `04_RESEARCH_DIRECTIONS_AND_DESIGN_SPACE.md`
6. `05_CURRENT_STATE_AND_OPEN_QUESTIONS.md`
7. `06_AGENT_RULES_AND_STAGE_GATES.md`
8. `07_NEXT_RESEARCH_TASK.md`
9. `09_REDESIGN_REVIEW_MEMO.md`
10. `10_CURRENT_VERIFICATION_CHECKLIST.md`

## Important Recent Sources

- latest Stage 1 repaired-policy rerun report;
- latest Stage 1 repaired-policy rerun post log;
- latest current-candidate protection repair report;
- latest Stage 1 rerun preflight validation report;
- latest structural feature rebuild readiness report;
- latest optical migration physical logic audit note;
- latest range-side anchoring reconstruction note;
- latest range interval and compact island geometry note.

## Historical Sources

Use only for history:

- early ROI geometry repair outputs;
- old heuristic repair outputs;
- oracle-high/runtime-low diagnostic outputs;
- first-pass ROI generator outputs;
- early hard-sample rescue outputs.

## Memory Rule

Current project-control files override historical outputs.

Historical outputs can explain why decisions were made, but they must not overwrite the current research framing.


# FILE: 09_REDESIGN_REVIEW_MEMO.md


# Redesign Review Memo

## Why This Redesign Exists

Previous control files over-centered the project on the 231 reviewed samples and Stage 1.

This was useful for controlled diagnosis, but it distorted the research framing.

The true research object is the complete three-scene temporal stream, not only the 231 GT-reviewed samples and not the 37 Stage 1 samples.

## Core Correction

The project-control layer has been reframed from:

**231 / Stage 1 centered repair control**

to:

**Level 0/1 full-stream optical-to-SAR transfer research control with Level 2/3/4 evaluation and diagnosis windows**.

## How to Use Prior Work

Prior work should be treated as evidence, not a binding methodology.

It shows:

- azimuth transfer is useful;
- range transfer is weak;
- DepthPro is only weak evidence;
- structural-clutter false positives are real;
- current-candidate protection is necessary;
- repaired Stage 1 is safe but too conservative;
- positive SAR vehicle evidence is likely missing.

Prior work does not prove that the latest Stage 1 pipeline should continue unchanged.

## Main Warning for Future Agents

Do not slide back into:

- ROI repair;
- Stage 1-only debugging;
- threshold tuning;
- oracle-guided fitting;
- 231-only optimization;
- treating a Level 4 case as a global rule.

## Preferred Next Direction

Before more selector reruns, perform:

**Full-stream transfer opportunity inventory and positive SAR evidence audit design.**

This should reconnect the research to Level 0/1 while using Level 2/3 evidence as validation anchors.


# FILE: 10_CURRENT_VERIFICATION_CHECKLIST.md


# Current Verification Checklist

Before any future task begins, verify:

1. Which data level is being addressed:
   - L0 full three-scene temporal stream;
   - L1 all transfer opportunities;
   - L2 231 GT-reviewed samples;
   - L3 Stage subset;
   - L4 individual diagnostic sample.
2. Whether the task is research design, inventory, audit, scorer rerun, or production replacement.
3. Whether the task uses runtime-observable evidence only.
4. Whether offline overlap, oracle, or ground truth are used only after decisions for diagnosis.
5. Whether the task accidentally treats Stage 1 or the 231 samples as the full universe.
6. Whether the task states what was not run.
7. Whether the task outputs source files read and post log.
8. Whether the task changes the stage gate.
9. Whether the task produces conclusions tagged by data level.
10. Whether the next safe step is research design, diagnostic audit, or controlled experiment.


# FILE: README.md


# Research Redesign Control Pack v3

This package defines a research-control layer for the optical-to-SAR vehicle transfer project.

It reframes the project around the complete three-scene temporal stream while preserving the 231 GT-reviewed samples as evaluation and diagnostic anchors.

## Install

Unzip into:

`D:\profile\research\workspace\`

The result should be:

`D:\profile\research\workspace\00_project_control\`

In WSL:

`/mnt/d/profile/research/workspace/00_project_control/`

## First Hermes Test

Ask Hermes:

```text
Do not run experiments. Do not edit files. Read the project-control files under /mnt/d/profile/research/workspace/00_project_control and summarize the data hierarchy, research purpose, current blocker, forbidden actions, and next safe task.
```


# FILE: prompts/CODEX_RESEARCH_EXECUTOR_TEMPLATE.md


# Codex Research Executor Template

## Workspace

`D:\profile\research\workspace`

WSL path:

`/mnt/d/profile/research/workspace`

## Task

[Insert task name and purpose.]

## Data Level Scope

Declare which levels are active:

- [ ] L0 complete three-scene temporal streams
- [ ] L1 all transfer opportunities / candidates / tracks
- [ ] L2 231 GT-reviewed samples
- [ ] L3 Stage subset, specify which
- [ ] L4 individual diagnostic sample, specify which

## Required Source Files

First read project-control files:

1. `00_project_control/00_RESEARCH_BRIEF.md`
2. `00_project_control/01_DATA_HIERARCHY_AND_CONTEXT.md`
3. `00_project_control/06_AGENT_RULES_AND_STAGE_GATES.md`
4. `00_project_control/07_NEXT_RESEARCH_TASK.md`
5. `00_project_control/10_CURRENT_VERIFICATION_CHECKLIST.md`

Then read task-specific files:

[Insert task-specific sources.]

## Forbidden Actions

Do not:

1. run Stage 2;
2. run Stage 3;
3. promote selector;
4. relax thresholds;
5. use oracle, offline overlap, ground truth, already-good, old-overcompression, or oracle-high/runtime-low labels as runtime evidence;
6. treat 231 as the full universe;
7. treat Stage 1 as the full task;
8. convert a Level 4 case into a general rule without validation.

## Required Outputs

Produce:

1. source-files-read table;
2. data-level scope table;
3. what was run;
4. what was not run;
5. main diagnostic/inventory/design table;
6. runtime evidence columns versus offline-only columns;
7. interpretation by level;
8. gate status;
9. next safe step;
10. post log with exact commands if code was run.

## Offline Evidence Rule

Offline overlap, oracle, or ground truth may be joined only after runtime decisions are fixed, and only for diagnosis.

## Final Response

Report:

1. data level addressed;
2. files read;
3. what was run;
4. what was not run;
5. main result;
6. whether any gate was passed or failed;
7. next safe step.


# FILE: prompts/HERMES_RESEARCH_COORDINATOR_PROMPT.md


# Hermes Research Coordinator Prompt

You are the long-term research coordinator for an optical-to-SAR vehicle transfer study.

You are not here to continue the latest pipeline by default. You are here to preserve the research purpose, protect the data hierarchy, audit evidence, and generate safe next-step prompts for Codex, DeepSeek, or other executors.

Before any recommendation, read:

1. `00_RESEARCH_BRIEF.md`
2. `01_DATA_HIERARCHY_AND_CONTEXT.md`
3. `02_AVAILABLE_DATA_AND_ASSUMPTIONS.md`
4. `03_PRIOR_WORK_AS_EVIDENCE.md`
5. `04_RESEARCH_DIRECTIONS_AND_DESIGN_SPACE.md`
6. `05_CURRENT_STATE_AND_OPEN_QUESTIONS.md`
7. `06_AGENT_RULES_AND_STAGE_GATES.md`
8. `07_NEXT_RESEARCH_TASK.md`
9. `09_REDESIGN_REVIEW_MEMO.md`
10. `10_CURRENT_VERIFICATION_CHECKLIST.md`

Maintain this framing:

- **L0:** Complete three-scene temporal streams are the final research object.
- **L1:** All vehicle detections, tracks, candidates, and optical/SAR correspondence opportunities are the operational transfer space.
- **L2:** The 231 GT-reviewed car samples are a supervised evaluation and diagnostic window.
- **L3:** Stage 1/2/3 are controlled diagnostic subsets inside Level 2.
- **L4:** Individual samples are failure case studies.

Use this model:

**empirical optical-to-SAR azimuth mapping + weak relative depth/range hints + optical vehicle-state interpretation + SAR local evidence confirmation**.

Never recommend:

- running Stage 2 before Stage 1 passes;
- running Stage 3 before Stage 1 and Stage 2 are understood;
- using oracle, overlap, ground truth, already-good, old-overcompression, or oracle-high/runtime-low labels as runtime evidence;
- threshold relaxation before diagnosing missing positive evidence;
- treating Stage 1 or the 231 reviewed samples as the full research object.

When generating a Codex prompt, always require:

1. data-level scope declaration;
2. source-files-read table;
3. runtime/offline evidence separation;
4. what-was-run and what-was-not-run sections;
5. post log;
6. level-tagged conclusions;
7. gate status;
8. next safe step.


# FILE: prompts/REVIEWER_PROMPT_TEMPLATE.md


# Reviewer Prompt Template

You are reviewing an output from an agent working on the optical-to-SAR transfer project.

Reject or flag the output if it:

1. treats the 231 GT-reviewed samples as the complete research object;
2. treats Stage 1 as the full task;
3. lacks data-level tags for conclusions;
4. recommends running Stage 2 or Stage 3 before gates;
5. uses oracle, ground truth, offline overlap, already-good, old-overcompression, or oracle-high/runtime-low labels as runtime evidence;
6. relaxes thresholds before diagnosing evidence gaps;
7. converts a Level 4 case into a general rule without Level 2/3 validation;
8. fails to state what was not run;
9. omits source files read;
10. omits post log or equivalent execution record.

Evaluate:

1. Does the output preserve Level 0/1/2/3/4 hierarchy?
2. Does it distinguish runtime evidence from offline diagnosis?
3. Does it treat prior work as evidence rather than binding methodology?
4. Does it keep the full-stream research goal visible?
5. Does it propose a safe next step?

Return:

- pass/fail;
- violations;
- risks;
- required corrections;
- recommended next safe step.


# FILE: skills/SKILL_CODEX_PROMPT_WRITER.md


# Skill: Codex Prompt Writer

Purpose: Generate safe Codex prompts.

A prompt must include:

1. workspace path;
2. data-level scope;
3. source files to read;
4. task scope;
5. forbidden actions;
6. required outputs;
7. runtime/offline evidence separation;
8. gate condition;
9. what-was-not-run requirement;
10. post-log requirement.

Current default next task:

Full-stream transfer opportunity inventory and positive SAR evidence audit design.


# FILE: skills/SKILL_OUTPUT_AUDITOR.md


# Skill: Output Auditor

Purpose: Audit outputs before the next task is approved.

Check:

1. data-level scope declared;
2. all-231 not mistaken as full universe;
3. Stage 1 not mistaken as full task;
4. runtime/offline evidence separated;
5. oracle leakage absent;
6. source-files-read present;
7. post log present;
8. what-was-not-run present;
9. stage gates obeyed;
10. next safe step reasonable.

Report violations with evidence and required correction.


# FILE: skills/SKILL_RESEARCH_DESIGN_REVIEW.md


# Skill: Research Design Review

Purpose: Review whether a proposed task respects the research framing.

Checklist:

1. Does the task state its data level?
2. Does it preserve the full three-scene temporal stream as the final research object?
3. Does it treat the 231 samples as evaluation/diagnostic subset only?
4. Does it avoid treating Stage 1 as the main project?
5. Does it separate optical constraints from SAR confirmation?
6. Does it avoid oracle leakage?
7. Does it identify whether the task is design, audit, inventory, or experiment?
8. Does it explain what it will not run?

If not, request revision before execution.


# FILE: templates/REPORT_TEMPLATE.md


# Report Template

## Task

[Task]

## Data Level Scope

[L0/L1/L2/L3/L4]

## Files Read

[Files]

## What Was Run

[Commands / scripts / none]

## What Was Not Run

[Explicit forbidden or skipped actions]

## Main Outputs

[Outputs]

## Runtime Evidence Used

[Runtime evidence]

## Offline Diagnosis Used

[Offline-only evidence]

## Results

[Results]

## Interpretation by Level

- L0:
- L1:
- L2:
- L3:
- L4:

## Gate Status

[Pass/fail/not applicable]

## Next Safe Step

[Next step]


# FILE: templates/TASK_TEMPLATE.md


# Task Template

## Task Name

[Name]

## Data Level Scope

- L0:
- L1:
- L2:
- L3:
- L4:

## Purpose

[Purpose]

## Source Files to Read

[List]

## Forbidden Actions

[List]

## Required Work

[List]

## Required Outputs

[List]

## Gate / Stop Condition

[Condition]

## Final Report Requirements

- files read;
- what was run;
- what was not run;
- main result;
- interpretation by data level;
- gate status;
- next safe step.