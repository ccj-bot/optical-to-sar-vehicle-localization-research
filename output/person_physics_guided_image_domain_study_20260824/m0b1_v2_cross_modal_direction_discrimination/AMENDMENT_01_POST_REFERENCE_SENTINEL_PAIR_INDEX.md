# Amendment 01: post-reference sentinel pair-index completion

- Trigger: the first post-reference reporting run reached frozen matched pairs
  with no dynamically available raw fragment on either side.  Those full-
  denominator sentinel rows correctly existed, but their reporting-only
  `pair_index/from_frame/to_frame` fields were absent, causing an integer
  conversion error during cluster aggregation.
- Pre-reference outputs changed: `NO`.
- Hypotheses, descriptors, controls, timing conditions, global baseline,
  selection, and reference labels changed: `NO`.
- Scientific rule changed: `NO`.
- Repair: fill the three reporting keys from the already frozen primary SAR
  edge metadata before cluster aggregation.
- Reference order: reference had already been legally revealed after the
  independent pre-reference validator passed `116/116`; the repair does not
  read any new reference source or alter any reference mapping.

This amendment is an execution/reporting repair only.

