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
