# Workspace Rules

This repository is a research record for optical-to-SAR vehicle localization and candidate selection. It is not a product engineering repository. Version control is used to preserve specifications, audit evidence, model evolution, and boundary decisions.

## What May Be Committed

Formal research assets may be committed after review:

- model specifications;
- roadmap documents;
- audit reports;
- factor prior registries;
- field dictionaries;
- dependency audits;
- clean research logs;
- research workflow and asset policy documents;
- project-control files that define current research state and stop/go gates.

Every committed document should be understandable without private local paths, runtime-only context, or hidden credentials.

## What Must Not Be Committed

Do not commit:

- `output/`;
- `artifacts/`;
- archive tarballs or large archive packages;
- `.codex` and `.codex/` local assistant state;
- cache folders and bytecode;
- large generated files;
- auth/proxy scripts or credential-adjacent setup material;
- unreviewed `tasks/` or `tools/` trees;
- old prompt dumps;
- model weights or detector weights;
- files containing private local paths or sensitive configuration details.

`tasks/` and `tools/` may only be committed after file-by-file review. They must never be added as whole directories by default.

## Git Discipline

- Never run `git add .`.
- Stage only an explicit file whitelist.
- Before any commit, run `git diff --cached --name-status`.
- Show the staged file list before committing.
- Do not push unless the user explicitly says `push`.
- Do not stage tracked deletion under runtime output directories unless the user explicitly asks for a cleanup commit.

## Research Boundary Rules

- Do not modify algorithm code unless the user explicitly authorizes algorithm work.
- Do not run experiments unless the user explicitly authorizes an experiment.
- Do not train any model unless the relevant audit gate has passed and the user explicitly authorizes training.
- Do not modify the candidate bank.
- Do not replace the GM17 mainline selector.
- Do not start OOF calibration while it is BLOCKED.

## Inference And Evaluation Separation

Evaluation-only fields must not enter inference inputs or inference outputs. Blocked examples include:

- GT fields;
- oracle fields;
- IoU fields;
- center-error fields;
- condition labels;
- truncation labels;
- occlusion labels;
- final annotation box fields.

Evaluation fields may appear only in audit or evaluation tables after inference outputs are already generated.

## Visibility Branch Rule

Visible support may only act as factor, veto, or uncertainty evidence. It must not generate a latent full-vehicle center and must not act as a full-center candidate source.

Partial visibility factors, including missing extent and visible/full-center offset factors, remain Phase7 diagnostic-only until the complete-vehicle mainline is stable and AuditReleaseAgent accepts the relevant audits.

## Calibration Gate

OOF calibration remains BLOCKED until AuditReleaseAgent accepts:

- Phase2 model-spec review;
- Phase3 factor prior audit;
- inference/evaluation separation;
- field-origin and leakage audit;
- double-counting controls;
- patch-dependency controls;
- partial-visibility isolation.

No calibration work should start from documentation readiness alone.
