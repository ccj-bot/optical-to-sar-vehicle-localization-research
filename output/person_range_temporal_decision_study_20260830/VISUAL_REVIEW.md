# Visual review ledger

The visual review was performed on the generated raw-optical/raw-SAR atlases, not inferred from CSV alone. Green outlines identify the selected strict mutual-dominant family; yellow outlines are other Q95 regions. Visual judgments remain separate from computed verdicts.

## Main observations

- R03 F447-F475 confirms that the optical fragment is visually continuous and the selected far-range SAR response family is coherent across unique and ambiguous frames. The PERSON is small and located in a dark doorway, so the bbox bottom is not a trustworthy narrow-range footpoint.
- The matched R03 no-PERSON windows contain visually clean, persistent SAR families. The strongest control has eleven unique observations, exceeding the source's five. Long continuity, repeated uniqueness and smooth theta/range trajectories therefore remain background-compatible.
- R02 F472-F494 contains multiple people, parked vehicles, vegetation, glare, left-boundary entry and partial lower-body occlusion. The scene visually supports an azimuth-times-range formulation, but not universal footpoint availability.
- The R02 28-frame wrong-family counterexample is visually coherent despite zero reference radial/theta support. This directly falsifies any rule that promotes a clean recurrent trajectory to PERSON identity.
- R01 provides both ends of the range story: F100 has a visually plausible clean footpoint and ±3 m contracts 16 families to one; F15 retains seven families at ±3 m; F20 retains four at ±2 m. Coarse range is dominant but not a final localizer.

See `post_reference_diagnostic_only/visual_review_ledger.csv` for case-by-case computed and visual verdict separation.
