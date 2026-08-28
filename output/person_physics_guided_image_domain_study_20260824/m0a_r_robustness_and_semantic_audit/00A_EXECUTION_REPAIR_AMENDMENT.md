# M0A-R execution repair amendment

- Amendment status: `FROZEN_BEFORE_SUCCESSFUL_RUN`
- Scope: deterministic renderer only
- Scientific tables, strata, controls, metrics, case registry rules, and state rules changed: `NO`
- Frozen M0A inputs changed: `NO`
- M0B executed: `NO`

The first audit command stopped during figure rendering after the analytic CSVs
had been written. The frozen M0A `MERGE_LIKE` case stores its related region IDs
as source-frame regions, while the new renderer incorrectly resolved every
related ID against the destination frame. This produced a deterministic
`KeyError` before figures, summary, report, ledger, manifest, or validation were
completed.

The repair mirrors the frozen M0A renderer contract:

- `MERGE_LIKE`: related IDs are resolved and drawn in the source frame;
- all other registered related IDs: resolved and drawn in the destination
  frame.

No case is substituted. No support, P0, ZERO, reference, topology, percentile,
control, matching, cluster, or outcome calculation is changed. The successful
audit must be rerun from the frozen inputs and must pass the independent
validator.

The second command reached report construction and stopped because
`pandas.to_markdown()` attempted to import the optional, unavailable `tabulate`
package. The report now uses a local deterministic Markdown-table renderer.
This changes presentation only and avoids modifying the research environment.

Final superseding runner SHA256:

`23660C7B5D968299C6A4FF03F088466687E6F22BD7C6055AB7742AF8DF499638`
