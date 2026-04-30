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
