# R02 boundary multi-bracket preparation log

## Pre-run

- Started 2026-09-02 Asia/Shanghai.
- Active repository: `D:\profile\research\workspace`.
- Verified starting `HEAD == origin/main == bfff2649515115bc5655bde00bd6aec893d67224`, ahead/behind `0/0`.
- Existing dirty baseline contains 342 entries and will be preserved without cleanup or broad staging.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Input is the complete R02ZF SAR stream from the frozen frame registry and raw pseudocolor files.
- The selection stage is image-led and does not run or consult the propagation algorithm to rank success probability.
- Frozen comparator F150-F183 is excluded from new brackets.
- Outputs go only to `output/r02_boundary_multibracket_preparation_20260902`.
- Existing manual annotation JSONL is read-only; pre-run SHA-256 is `5EA5882BD764524E5FD61C1D72C7594AAA9BBF9ABFCD5A1BD9FE992BDE278FC9` with 20 events.
- R04, `old_work`, tree anchors, PERSON references, candidate pruning, final grounding, and final boxes are excluded.

## Post-run

- Image-led selection completed after reviewing the full F0-F494 stream at 5-frame spacing and every frame in F45-F90, F235-F285, and F425-F475.
- Selected A_EARLY F47-F82 (36 frames), B_MID_LATER F239-F278 (40 frames), and C_LATE F427-F472 (46 frames).
- Six endpoint keyframes are F47, F82, F239, F278, F427, and F472. No selected endpoint is in frozen comparator F150-F183.
- Generated `output/r02_boundary_multibracket_preparation_20260902/R02_BOUNDARY_MULTIBRACKET_ANNOTATION_BATCH_V1.csv`.
- Generated `MULTIBRACKET_SELECTION_REPORT.md` and three 10-frame review strips under `figures/`.
- Added `annotation_scope=SAR_BOUNDARY_ONLY` support to the existing browser annotator. In this mode the workflow is exactly SAR near then SAR far; optical, tree, and hint controls are hidden, and navigation uses six dynamic keyframes.
- Dedicated launcher: `tasks/r02_boundary_multibracket_preparation_20260902/START_R02_BOUNDARY_MULTIBRACKET_ANNOTATION.bat`.
- Real manual output directory is isolated at `output/r02_boundary_multibracket_preparation_20260902/user_annotations` and remained empty through validation.
- Isolated localhost/API/headless-Edge QA passed 15/15. The temporary save test confirmed both SAR labels, bracket/seed provenance, append-only output, and SAR-only coverage semantics.
- Existing manual JSONL remained 20 events with SHA-256 `5EA5882BD764524E5FD61C1D72C7594AAA9BBF9ABFCD5A1BD9FE992BDE278FC9`.
- No propagation, PERSON experiment, tree work, R04 access, or `old_work` access occurred.
- Preparation is complete. Stop condition reached: wait for the user to annotate six keyframes before any propagation work.
