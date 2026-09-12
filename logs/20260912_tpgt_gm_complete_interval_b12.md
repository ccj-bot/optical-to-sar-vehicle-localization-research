# 2026-09-12 TPGT-GM-B1.2

- Branch: `feature/tpgt-gm-complete-interval-b12`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Output: `output/tpgt/gm_complete_interval_b12`
- Optical interval candidates: GM011=14, GM017=4, GM019=8
- GM17 full-stream YOLO11l rescout: 91 detections, 15 provisional tracks
- SAR reference opened: no
- Validation: `PASS_WITH_REVIEW_GATE`
- GPU note: 8 GB RTX 5070 Laptop; YOLO11l at 640px OOM during initial test. A 320px single-frame GPU smoke test passed with ~0.14 GB allocated. Final reproducible rescout remains CPU at 640px to preserve the high-resolution run without depending on game/desktop GPU load.
- Stop point: human review before any SAR mapping/reference work
