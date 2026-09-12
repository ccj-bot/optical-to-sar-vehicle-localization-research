# TPGT-GM-B1.2 Complete-Interval Recovery + GM17 PERSON Rescout

## Scope and stop point

Optical-only interval recovery and full-stream GM17 PERSON discovery. SAR GT/manual reference, mapping, truncation correction, selector/ranking, final annotation and A-line edits were not performed.

## Direct answers

- Complete interval candidates: GM011=14, GM017=4, GM019=8.
- GM017 PV002 maximum candidate: frames 154–173; PV003: 162–188; PV004: 169–201. PV001 is retained as VEHICLE_NO_SAR_REFERENCE (frames 129–159).
- GM011: no >=12-frame complete interval was found; no identity is promoted. GM019: no >=12-frame interval was found; PV003 candidate frames 118–123 is the strongest short window.
- GM019 PV003 frame 136 is a false source-box/background anomaly; see `03_gm019_pv003_audit/GM019_PV003_CONTACT_SHEET_AUDIT.md`.
- The old PERSON scout failed because it read sparse detector caches and emitted singleton detections without temporal linking; see `00_audit/GM17_PERSON_SCOUT_FAILURE_AUDIT.md`.
- Full 368-frame YOLO11l rescout produced 91 person detections and 15 provisional optical tracks; all remain REVIEW_REQUIRED.
- A PERSON interval is considered present only as a provisional optical candidate here; no human confirmation or physical identity claim is made.

## Review gate

Open `06_review/REVIEW_INDEX_B12.html`. Freeze decisions before any SAR reference or mapping work. `COMPLETE_CAR_CORE_INTERVALS.csv` is intentionally empty.

## Reproduction

`D:\MINICONDA\envs\py311\python.exe tasks\tpgt_gm_complete_interval_b12\run_b12.py`