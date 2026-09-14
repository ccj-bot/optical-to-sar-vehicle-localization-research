# Local support probe — pre-run / audit log

Branch feature/oty2-sar-vehicle-morphology-object, starting committed HEAD
c5c60ae. User explicitly requests only new code/report/log commits this round.
No sample-data additions and no mutation of committed morphology v2 files.

The initial pilot this turn ran after a syntax error correction but is rejected:
GT bilinear-chart crops were wrongly called native nested apertures; per-chord
q40 ensured roughly 40% "low" samples and made an unsupported-chord label nearly
tautological; endpoints/plots remained PCA projections; rank pixels did not
prove ridge support; near-neighbour graphs exploded. Counts 119/358 for original,
172/580 for shuffle and 87/193 for an altered (not exact prior C) plateau are
provenance of a failed design, NOT scientific support or native stability data.
Original pilot outputs are preserved, not used for final conclusions.

Corrected preflight: research-workspace-guard read; workdir workspace; no
old_work dependency. Interpreter: existing workspace py311, CPU execution.
New task README and freeze.json created before corrected native computation.
Plan: compare a finite local rank support baseline with finite oriented
raw-field crest paths; preserve I0/I1/I2/I4 witnesses, exact endpoints and gaps;
audit native overlap pixels, local predicates, connected support and grouping
separately. Plateau A/C are exact previous fixtures, not newly approximated edits.
No vehicle relation type additions, universal score, selector or temporal work.

## Corrected execution and inspection

Completed seven records: exact original/shuffled, exact prior A/C and three
native frozen windows. The original pre-run freeze.json was preserved as
output/local_support_probe/original_native_freeze.json. Its exact text is now
packaged in frozen_config.py; validator confirms the original freeze and core
hashes. No corrected-run parameter retuning. Readout/figure code was added after
the run and does not change proposal records.

Inspected raw/support plots for all four intervention fixtures, native main and
weak regions, stability maps, old baseline rejection, named original/shuffled
groups, and same-path scale witnesses. Original G4/G73 retain actual local
support and gaps. G96 is a competing direction; shuffled G13 still has a plausible
geometric gap. These are posthoc illustrated hypotheses, not selected objects.

Native W2/W3 vs W1: zero rank/oriented/group-union support differences inside a
9px halo; exact clipped matches are 363/370 fragments and 159/166 groups including
member partition. Group-union invariance alone is not grouping correctness.
At native (1140,1035), old q80 component area grows 2565 -> 3300 -> 5795 pixels;
aspect drops to 1.549 in W3 and the old segment proposal rejects it.
Exact A floor and eroded C constant interior have zero oriented support; edge
artifacts are not ruled out. Synthetic constant-field and separated-strip checks
also pass. Counts are representation burden, not classification evidence.

Validation: PASS_TECHNICAL_NOT_VEHICLE_OR_SEMANTIC_VALIDATION; seven records,
3309 fragments, 1621 groups, 3192 gap witnesses. Original pilot counts are excluded.
Outputs: output/local_support_probe/{INDEX.html,REPORT.md,VALIDATION.json},
records/, figures/, and per-structure readout/comparison JSON files.

## Concurrent checkout and commit scope

Another session switched the shared workspace to
feature/tpgt-unified-target-review-observation and introduced unrelated edits.
No switch-back, cleanup or staging there. Created a sparse isolated worktree at
output/local_support_probe/branch_worktree on the requested morphology branch,
starting c5c60ae. Initialized its empty index from HEAD before staging new files.
Code there reads existing data through LOCAL_SUPPORT_WORKSPACE. Earlier untracked
drafts in the shared checkout are left untouched; the isolated code is authoritative.
Whole-shared-workspace non-regression is NOT asserted after that external switch.

Only the new tasks/local_support_probe code/README, this log and the new report
are to be committed. Generated images/data, prior morphology code and unrelated
files are excluded. No push in this round. Final handoff records commit identity.
