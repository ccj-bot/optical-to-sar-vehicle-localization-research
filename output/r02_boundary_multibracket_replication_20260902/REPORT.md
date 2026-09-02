# R02 manual-boundary multi-bracket replication report

## Boundary semantics

- All endpoint polylines are retained as `d_perp(theta)` curves. Bracket A is not straightened: F047 is strongly curved while F082 is much flatter.
- The raw append-only manual JSONL is unchanged. Point-rich near drafts are accepted only because the user explicitly stated that annotation was complete in this turn.
- Propagation parameters are byte-for-byte sourced from the frozen F150-F183 implementation; no A/B/C outcome-driven threshold changes were made.

## Results

| Bracket | Frames | Directional coverage | Overlap | Center | Shape | Overlap order | Directional order | Final | Repair |
|---|---:|---:|---:|---|---|---|---|---|---:|
| A_EARLY | 36 | 14 | 0 | UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP | UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP | UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP | True | BRACKET_NOT_CLOSED | 62 |
| B_MID_LATER | 40 | 24 | 0 | UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP | UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP | UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP | True | BRACKET_NOT_CLOSED | 264 |
| C_LATE | 46 | 13 | 0 | UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP | UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP | UNAVAILABLE_NO_BIDIRECTIONAL_OVERLAP | True | BRACKET_NOT_CLOSED | 454 |

## Manual effort

- Initial manual anchor density: 6 / 122 = 0.0492.
- Proposed minimal repair seeds: 3.
- Auto-propagated fractions are reported separately for directional support and fully closed coverage in `BRACKET_COMPARISON.csv`.
- A missing bidirectional overlap is recorded as unavailable closure evidence, not as a failed center/shape/order comparison. Directional near/far ordering is reported separately.

## Explicit non-claims

These results concern conditional SAR image-domain maintenance of user-defined static boundaries. They do not establish physical calibration, PERSON range, PERSON grounding, identity, final boxes, or full-stream propagation.
