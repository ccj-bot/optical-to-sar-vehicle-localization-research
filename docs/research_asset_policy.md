# Research Asset Policy

This document defines how research assets should be classified before entering version control.

## Asset Classes

### Formal Research Assets

Formal research assets are intended to be part of the durable research record. Examples:

- model specifications;
- research roadmaps;
- audit reports;
- factor prior registries;
- field dictionaries;
- dependency audits;
- current research state snapshots;
- clean workflow and policy documents.

These may be committed after review.

### Historical Research Assets

Historical research assets record previous reasoning, experiments, or planning. They may be useful for traceability, but they must not be treated as current instructions or current performance claims.

Historical assets should be reviewed and, when necessary, rewritten into clean summaries before entering the formal repository. Old B-class historical files should not be committed verbatim.

Historical assets must not overwrite current state documents unless a new audit decision explicitly promotes them into the current baseline.

### Local Runtime Outputs

Runtime outputs are local working products, not formal research assets by default. Examples:

- generated experiment outputs;
- visualization grids;
- generated tables;
- model outputs;
- archive tarballs;
- cached files;
- bytecode;
- large generated packages.

Runtime outputs should remain local unless a specific reviewed artifact is promoted into a clean audit document.

### Sensitive-Adjacent Materials

Sensitive-adjacent materials include auth/proxy setup notes, local assistant state, environment setup scripts, credentials, private machine paths, model weights, and any file that may reveal local operational details.

These materials should not be committed without explicit human review and sanitization.

### Obsidian-Only Notes

Obsidian-only notes and informal working notes are not automatically repository assets. If a note becomes relevant to the research record, rewrite it into a clean formal document before committing.

## Tasks And Tools

`tasks/` and `tools/` must be reviewed file by file. They must never be committed as whole directories by default.

Before any task or tool file is committed, verify:

- it is not generated output;
- it does not contain sensitive material;
- it does not contain private paths;
- it does not include cache or bytecode;
- it is relevant to the current formal research record;
- it does not imply unauthorized algorithm changes, experiments, training, candidate-bank changes, OOF calibration, or GM17 mainline replacement.

## Archive Policy

Archive directories and archive packages should not be committed. They may preserve local history, but they are not clean research assets.

If archive content matters, write a small clean summary document instead of committing the archive itself.

## Path And Privacy Policy

Formal documents should not include private local filesystem paths. Use repository-relative paths for committed artifacts.

Documents should not include sensitive setup details. If a workflow requires environment setup, describe it at a policy level rather than recording local secrets or auth configuration.

## Evaluation Boundary

Evaluation-only fields are allowed in audit documents only when clearly labeled as evaluation fields. They must not be represented as inference inputs.

Formal research documents must preserve the distinction between inference-safe fields, diagnostic-only fields, future fields, and evaluation-only fields.
