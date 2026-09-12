# TPGT Phase 1A

User-authorized provisional source-backed event index and small optical/acquisition-selected CAR/PERSON study queue. Frozen Phase 0C-R1 files stay unchanged. No new canonical fields, namespaces, eligibility gate, validation framework or scientific mechanism inference.

Interpreter: `D:/MINICONDA/envs/py311/python.exe`; cwd: workspace. Outputs: `output/tpgt/phase_1a/`; machine logs: its `audit/` directory. No old_work runtime dependency. Auxiliary CSV columns are review/index metadata, not canonical schema revisions. Event core/context remain undefined. Clip before/after padding is presentation context only.

Completed entry: `output/tpgt/phase_1a/index.html`; the six pages also work as standalone local files. `serve_review.py` opens a localhost-only media server when an in-app browser is desired; its PID/URL are recorded under audit.

Build sequence: `build_universe.py`, `choose_queue.py` (inspect optical-only preview), `build_packs.py`. Queue selection must remain fixed before SAR decoding; do not regenerate selection based on pack SAR appearance. `check_delivery.py` is one-off artifact/browser QA, not a new schema validator or scientific framework. It uses installed Edge headlessly. This run installed `imageio-ffmpeg` and `playwright` into the py311 environment for H.264 media export and browser inspection; existing cv2/pandas/Pillow/numpy were used. Canonical 0C-R1 source files remain untouched.

## Observation Workbench enhancement

Generate and serve the blind-first human observation adapter:

```powershell
D:\MINICONDA\envs\py311\python.exe D:\profile\research\workspace\tasks\tpgt_phase_1a\enhance_observation_workbench.py
D:\MINICONDA\envs\py311\python.exe D:\profile\research\workspace\tasks\tpgt_phase_1a\serve_workbench.py --port 8765
```

Open `http://127.0.0.1:8765/index.html`. Append-only observation revisions are written under `output/tpgt/phase_1a/observation_workbench/records/`; interpretation candidates are separate. Historical manual and interpolated references are not requested by `OBSERVATION_VIEW` and are independently switched only after deliberate Open-book navigation.
