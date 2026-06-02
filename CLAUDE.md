# Agent Operating Rules

This file defines operating rules for AI agents working in this research repository.

## First Response Checklist

Before making changes, report:

- current Git status;
- current branch;
- planned files to modify;
- whether the task is documentation-only, audit-only, algorithmic, experimental, or calibration-related.

If the task touches algorithm code, experiments, candidate banks, training, OOF calibration, or GM17 mainline replacement, stop unless the user explicitly authorizes that scope.

## Default Boundaries

Unless explicitly approved by the user:

- do not modify algorithm code;
- do not run experiments;
- do not train models;
- do not change the candidate bank;
- do not replace the GM17 mainline selector;
- do not start OOF calibration;
- do not stage broad directory trees;
- do not push.

## Git Rules

- Never run `git add .`.
- Stage only explicitly named files.
- Never stage `output/`, `artifacts/`, archive packages, `.codex`, `.codex/`, cache folders, model files, generated runtime outputs, or unreviewed `tasks/` and `tools/` trees.
- If the user asks for broad cleanup, first produce an inventory and wait for approval. Do not directly stage, delete, restore, or reorganize files.
- Before committing, show `git diff --cached --name-status`.
- Commit only after confirming the staged list contains the intended files.
- Do not push unless the user explicitly says `push`.

## Sensitive Material Rules

Do not commit or reproduce sensitive material. This includes credentials, auth/proxy configuration details, private machine paths, local assistant state, cache content, model weights, and generated runtime outputs.

If a file is sensitive-adjacent, classify it for human review instead of staging it.

## Research Interpretation Rules

- B patch reproduction is diagnostic consistency evidence only.
- Do not describe B patch reproduction as proof of a final physical model.
- Do not treat a diagnostic prototype as a mainline selector.
- Do not report new performance conclusions unless they come from a boundary-audited artifact.
- Do not use visible support as a full-center generator.
- Do not allow evaluation-only fields into inference outputs.

## Terminology Contract

- `final_action` means model-level output such as `keep_base`, `use_path`, `reject`, or `uncertain`.
- `release_decision` means AuditReleaseAgent project decision about whether an artifact can proceed, remain diagnostic, enter calibration, or be blocked.
- Do not mix these terms.

## Current Research Gate

Phase3 factor prior audit execution may proceed as audit work. OOF calibration, ranker training, CRF training, new performance experiments, candidate bank changes, and GM17 mainline replacement remain blocked.
