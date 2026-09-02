# PERSON-R02 scene-depth value test log

## Pre-run

- Active repository: `D:\profile\research\workspace`.
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`.
- Starting `HEAD == origin/main == 3da805fa72d0d736230875bb853be17d2d875b31`, ahead/behind `0/0`.
- Existing dirty baseline contains 342 entries and remains out of scope.
- This is a `VALUE IF CORRECT` mechanism test, not a runtime deployment test.
- Boundary propagation, F66, full-stream coverage, curve representation, tree anchors, azimuth calibration, R04, final localization, learned depth, trackers, and weighted fusion are frozen or excluded.
- Eligible boundary geometry is restricted to manual semantic checkpoints and explicitly visually reviewed stable propagated frames. Full current optical theta support must lie inside both boundary curves; partial theta coverage is not extrapolated.
- Optical scene-layer labels and candidate supports will be frozen before opening case-level PERSON SAR reference.
- Outputs go only to `output/person_r02_scene_depth_value_test_20260902`.

## Post-run

- Completed the bounded `VALUE IF CORRECT` study without modifying boundary propagation, F66, curve representation, azimuth mapping, R04, or final localization.
- Frozen 24 optical visual cases before reference reveal: 23 `L2`, 1 `UNCERTAIN`.
- Materialized 27 shell rows x 3 conditions with exact Q95 pixel intersections and reversible bit-packed support masks.
- Two-boundary exact-curve application was available on 13/27 shell rows; 14/27 conservatively fell back because the full optical theta corridor was not covered by both curves.
- Pre-reference freeze root SHA256: `9d7a1f5c8197e3964730bacd74756febf5383de1d754ae80464de5e626872622` across 40 frozen files.
- On the 13 applied two-boundary rows, paired medians were `N_region 13 -> 10`, `N_family 13 -> 10`, `A_candidate_px 2667 -> 2160`, and `A_candidate_m2 3.051 -> 2.471`; median area contraction was 12.5%.
- On the 8 rows where one-curb and two-boundary conditions were both available, both ended at median `N_family=10.5`; two boundaries added only 2.2% median area contraction over one curb and changed family count on 0/8 rows.
- Post-freeze reference reveal matched two rows. One was the previously disclosed F472/PERSON017 case and was marked operator-contaminated. The sole clean row was 13.885 m but the two-boundary operator was not eligible under the frozen full-theta rule.
- Final decision: `INSUFFICIENT_PERSON_OVERLAP`. Applied uncontaminated reference denominator is zero, so retention and `FALSE_SCENE_LAYER_PRUNE` rate are unavailable; fallback-aware 100% retention is not claimed as evidence.
- F66 repair is not justified now. The only recommended next step is a small reference-blind collection of trusted full-theta PERSON overlap spanning at least L1 and L2.
- Independent validator: PASS 50/50.
- Report: `output/person_r02_scene_depth_value_test_20260902/REPORT.md`.
- Summary: `output/person_r02_scene_depth_value_test_20260902/SUMMARY.json`.
- Review pack: `review_packs/PERSON_R02_SCENE_DEPTH_VALUE_TEST_20260903.zip`, 4,869,817 bytes, SHA256 `6007ee2aac67fec61298c776b4daca6387c3c72a3e476effeb5852b89ae50d84`.
