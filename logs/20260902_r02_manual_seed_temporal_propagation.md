# R02 manual-seed temporal propagation log

## Pre-run

- Started 2026-09-02 Asia/Shanghai.
- Active repository: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Input manual event log: `output/r02_manual_static_scene_anchor_preparation_20260902/user_annotations/manual_static_scene_annotations.jsonl`.
- Pre-run manual event SHA-256: `5EA5882BD764524E5FD61C1D72C7594AAA9BBF9ABFCD5A1BD9FE992BDE278FC9` with 20 append-only events.
- The user explicitly confirmed that the two annotated pairs define optical near/far to SAR near/far image semantics. Their `DRAFT` state is treated as an interface-finalization omission, not uncertainty about identity.
- The manual JSONL remains read-only. Derived outputs go only to `output/r02_manual_seed_temporal_propagation_20260902`.
- Scope is the two-anchor bracket SAR F150-F183. Propagation is adjacent-frame, bidirectional, local-ridge constrained, and uses frozen P0 vertical common apparent transport.
- Fixed 4.9/7.1/12.4 windows, independent per-frame global peak selection, automatic ridge switching, tree correspondence, PERSON experiments, final boxes, R04, and `old_work` are excluded.
- Existing dirty baseline is preserved; staging will use an explicit allowlist.

## Post-run

- Added task code under `tasks/r02_manual_seed_temporal_propagation_20260902` and outputs under `output/r02_manual_seed_temporal_propagation_20260902`.
- Converted the two user-confirmed SAR boundary pairs into a common manually supported theta corridor of `[-22, 8]` degrees with 16 nodes. This is a partial visible corridor, not a claim that the full boundary is recovered.
- Manual seed separation was `1.993 m` at SAR F150 and `1.997 m` at SAR F183.
- Forward propagation from F150 remained locally supported through F164 and stopped before F165 because the far-boundary response became too weak for that direction.
- Backward propagation from F183 remained locally supported through F162 and stopped before F161 because the far-boundary candidate required a jump outside the local corridor for that direction.
- The independently anchored paths overlapped at F162-F164. Maximum forward/backward disagreement was `0.0057 m` for near and `0.0597 m` for far, below the fixed `0.12 m` bridge threshold.
- The two paths were joined only after this overlap check. Final derived coverage is 34/34 SAR frames from F150 through F183: 2 manual-seed frames and 32 propagated frames, with two boundary records per frame (68 records total).
- Final center ranges over this image-domain interval were near `4.79-4.84 m` and far `6.79-6.99 m`; pair separation remained positive at `1.993-2.183 m`.
- `REVIEW_REQUIRED_FRAME_LIST.csv` is empty because each direction's stop was covered by the other independently anchored path and the overlap bridge passed. Directional stop evidence remains explicit in the diagnostics and summary.
- Visual review of F150/F158/F166/F175/F183 showed the propagated lines retaining the same lower-near / upper-far response semantics without an observed switch to another horizontal band.
- Validation passed `12/12`.
- The manual JSONL remained byte-identical with SHA-256 `5EA5882BD764524E5FD61C1D72C7594AAA9BBF9ABFCD5A1BD9FE992BDE278FC9`.
- No fixed range identity windows, tree propagation, PERSON experiment, final localization, R04 access, or `old_work` runtime dependency was used.
