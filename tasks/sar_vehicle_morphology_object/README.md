# SAR vehicle morphology object: small exploratory probes

Authorized scope: known-GT internal display-field morphology, not classification,
localization, physical-part recovery or target masks. GT is an observation aperture.
The input is the previous `gm_gt_morphology_20260913` output; previous scripts are
not imported, edited or committed. No raw-data or old_work runtime dependency.

Use the workspace's existing py311 environment (numpy, scipy, matplotlib, Pillow;
browser QA optionally uses playwright). Commands run from repository root:

```text
python tasks/sar_vehicle_morphology_object/explore_merge.py
python tasks/sar_vehicle_morphology_object/explore_relations.py
python tasks/sar_vehicle_morphology_object/validate.py
```

Scripts accept `--source` and `--out`. Defaults are repository-relative
`output/gm_gt_morphology_20260913` and `output/sar_vehicle_morphology_object`.
Inputs contain same-source display intensities, not calibrated energy or phase.
Generated figures/JSON/arrays stay under output and are not committed.

Selected cases: GM17 f344/g151 (A059), PV002 f330/g115, f353/g177,
f378/g254; GM11 f256/g77; GM19 f350/g332; weak GM17 f344/g152.
Case choices come from prior direct image review, not an optimization objective.
We retain failed representations and deliberately limit module count.

All merge branches are retained. Selected leaves/ridge display lengths are
readability controls, never vehicle acceptance criteria. Dark-space probes are
explicit case-conditioned reading anchors, not automatic interior estimates.
Same-source destruction images are interventions on image representation, not
physical counterfactual observations. Do not use them as labeled training data.
