# Inspectable morphology object, dual fields and bounded aperture release

This is a new exploratory stage on feature/oty2-sar-vehicle-morphology-object.
It does not edit earlier experiments. Run from workspace root using the existing
py311 interpreter; CPU only. No archive/old_work dependency.

For a small committed, data-root-independent example, start with
[examples/README.md](examples/README.md): A059 original plus its shuffled
counterexample, full losslessly compressed object records, exact fields and
four explanatory figures (about 2.6 MB payload). This is an explicit exception
to keeping generated data local; the full experiment remains uncommitted.

```
python tasks/morphology_object_v2/run_gt.py
python tasks/morphology_object_v2/intervene.py
# Wide execution is separate and only after explicit visual gate + freeze.
python tasks/morphology_object_v2/wide_runtime.py --raw-root <existing-SAR-data-root> --out output/morphology_object_v2/wide
python tasks/morphology_object_v2/wide_posthoc.py
python tasks/morphology_object_v2/finalize_artifacts.py --rerender
python tasks/morphology_object_v2/validate.py
python tasks/morphology_object_v2/inspect_qa.py --channel msedge
```

Defaults: previous read-only input output/gm_gt_morphology_20260913;
new output/morphology_object_v2. A compact merge-tree implementation is imported
from the committed earlier task, not its GT loaders or feature extraction.

Object = full_field + nuclei + candidate segments + typed relation hypotheses
+ dark/open witnesses + uncertainty. Never a vector, car score, selected winner,
physical target mask or final detection box. All field thresholds are analysis
levels; geometric tolerances propose relations, not vehicles. Full fields and
unresolved candidates stay available. Object graphs are aperture-scoped records,
not claims that everything in an aperture belongs to one vehicle.

All segment and relation hypotheses contain original-field traces, not only
attributes. Dark witnesses are sublevel components connected to a geometric
cross-section valley, with explicit boundary access; they are not car interiors.
Budget stops prevent dense graphs being cosmetically simplified into targets.

## Completed scope and stopping result

Seven GT-condition records, two original-control copies plus ten interventions,
and one frozen native 300 x 180 aperture. No full-442 processing or PERSON rerun.
The wide experiment is already complete: do not change wide_freeze.json or move,
expand or tune the aperture. Replaying it is reproducibility, not a new search.
The output is STOP_GRAPH_BUDGET / MORPHOLOGY_NOT_RECOVERED_AT_OBJECT_LAYER:
2137 nuclei, ten segments, no relations. The visible target band is not traced
by the wide candidate segments. Do not increase the budget to force recovery.

Important negative result: cores-only and raised-middle interventions generate
false segments on constant replacement plateaus; shuffled images still receive
typed geometric labels. These known scientific limitations remain unfixed and
are tested as failure fixtures. A record is inspectable, not a resolved vehicle.

## Artifacts and dependencies

Open output/morphology_object_v2/INDEX.html locally; its 20 standalone pages
let you select a nucleus, segment, relation or dark-region witness on I0.
Complete trees and coordinates are retained in linked JSON/NPZ. A compact
eight-leaf tree panel is a display projection only; it does not filter objects.
review_notes.json is a posthoc visual audit and never enters the image-only core.
See docs/morphology_object_v2_exploration.md for case-by-case failures and limits.

NumPy, SciPy, Matplotlib and Pillow are required; existing previous common.py
sets the Windows Microsoft YaHei font. Playwright with an already installed
Edge/Chrome is optional for browser QA; no browser download or network server.
Generated outputs (including source-sensitive provenance) are ignored by Git.
Only explicitly named task files, report and log are committed.

finalize_artifacts.py attaches provenance to existing GT/intervention records
and makes views, without rebuilding science or mutating the hashed wide object.
validate.py checks historical source hashes, I0 equality, raw traces, exact
8-neighbour bottleneck paths, dark components, interventions and worktree state.
Technical PASS is explicitly not semantic acceptance or vehicle recovery.
