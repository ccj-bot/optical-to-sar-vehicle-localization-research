# PERSON-R02 scene-depth value test

This task asks one bounded mechanism question: if the R02 near/far boundary geometry is correct, how much does an optical PERSON scene-depth layer contract causal Q95 SAR candidate support?

## Fixed boundaries

- Do not optimize boundary propagation or repair F66.
- Use only manual boundary frames or explicitly visually reviewed stable propagated frames.
- Exclude F66, UNKNOWN, stop frames, shape conflicts, and incomplete boundary-theta coverage.
- Freeze optical scene-layer labels and all runtime support before reading case-level PERSON SAR reference.
- Compare `ANGLE_ONLY`, `ANGLE_PLUS_ONE_CURB_HALFSPACE`, and `ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER` by exact Q95 pixel intersection.
- Report region count, family count, candidate pixels, area proxy, reference support retention, and false scene-layer pruning.
- No final selector, center, box, identity claim, tracker, weighted fusion, azimuth recalibration, tree work, R04, or `old_work` access.

## Locations

- Task code: `tasks/person_r02_scene_depth_value_test_20260902`
- Outputs: `output/person_r02_scene_depth_value_test_20260902`
- Log: `logs/20260902_person_r02_scene_depth_value_test.md`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`

## Execution stages

1. `prepare_pre_reference_review.py` prepares the trusted boundary overlap and optical visual sheets.
2. `scene_layer_visual_labels_v1.csv` records the reference-blind visual scene-layer decisions.
3. `freeze_pre_reference.py` materializes exact support masks, complete denominators, burden tables, and the immutable pre-reference hash manifest.
4. `evaluate_post_reference.py` is a separate stage and refuses to open reference files unless every frozen file and the aggregate root hash validate.
5. `build_report.py` creates the final decision report, three focused visual counterexamples, output manifest, and review pack without changing frozen artifacts.
6. `validate_scene_depth_value.py` independently checks freeze hashes, support-mask round trips, denominators, reference gating, report claims, output hashes, and review-pack integrity.
