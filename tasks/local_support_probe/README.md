# Local support / fragment probe (2026-09-14)

Exploration only: I0 pixels -> local support fragments -> bounded, non-transitive
group hypotheses. No new MorphologyObject relation types, vehicle scores,
features, classifier, detector, masks, tracking or temporal compensation.

Use existing workspace py311 (CPU). Inputs: committed A059 original/shuffled
examples, exact prior A/C interventions, native GM17 f344 PNG. No old_work.
Outputs: output/local_support_probe only. Frozen native nested windows and
read-only visual inspection regions are in frozen_config.py; its exact JSON
text/hash was frozen before native execution. Do not retune after run.

The preliminary local_fragment_exploration attempt is retained as rejected_pilot.py
for provenance, not used in the corrected experiment: it used GT-chart crops
instead of native windows, a self-quantile chord test that predetermines the
answer, projected endpoints and uncontrolled all-neighbour groups. Its output
under output/morphology_object_v2/local_fragments is not valid evidence for
native-aperture stability or the three primitive semantics.

## Reproduce

From this branch's checkout root, using the workspace py311 CPU environment:

```powershell
python tasks/local_support_probe/run_probe.py --raw-root <existing-optical-sar-data-root>
python tasks/local_support_probe/review_results.py
python tasks/local_support_probe/validate.py
python tasks/local_support_probe/make_review.py
```

Dependencies: numpy, scipy, Pillow and matplotlib; no model, GPU or download.
Optional `python tasks/local_support_probe/qa_review.py` checks all image/link
targets with existing Playwright and installed Edge; it installs nothing.
The raw root must contain GM_RM017/GM_RM017_SARframes_gray/000344.png.
Prior morphology_object_v2 A/C outputs and frozen wide-field audit are required;
the committed examples alone are not a self-contained native experiment dataset.
When code and existing data live in different checkouts, set
`LOCAL_SUPPORT_WORKSPACE` to the existing data workspace. The scripts load example
fixtures from the code checkout and write only to the data workspace's
`output/local_support_probe`. Run once to a fresh output directory: a new execution
writes its own pre-run freeze and provenance, not a historical freeze certificate.

Read `output/local_support_probe/INDEX.html` first, then the named group and scale
witnesses. Full fields and variable-size records are in `records/*.npz` and
`records/*.json.gz`. The report is `docs/local_support_probe_20260914.md`, copied
with adjusted image links to `output/local_support_probe/REPORT.md`.

## What was learned

Actual finite-neighbourhood crest paths keep I0 support and gaps inspectable.
Native interior support is unchanged across the three frozen windows, unlike the
old whole-aperture quantile/PCA proposal. This is locality, not vehicle evidence.
Constant plateau interiors do not produce crests. Shuffled G13 still has aligned
fragments and a valley; original G96 offers a competing direction interpretation.
One-pixel, four-direction support remains incomplete for broad/curved morphology.

Core/config were frozen before the corrected run and not retuned afterwards.
`review_results.py` and `make_review.py` only inspect saved results. Validation is
technical, not semantic or vehicle validation. No full MorphologyObject assembly.

The shared checkout was externally switched to another branch during this task.
Final code/report/log and commits therefore use an isolated worktree on the
requested branch; no unrelated shared-checkout edits are staged or reverted.
