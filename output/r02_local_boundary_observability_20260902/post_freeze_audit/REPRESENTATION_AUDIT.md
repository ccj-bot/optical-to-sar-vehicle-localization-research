# Frozen propagation representation audit

- Manual geometry is converted to a `d_perp(theta)` vector; node count depends on the seed-visible theta corridor.
- P0 predicts a common vertical transport, converted to one `d_perp` shift.
- Candidate search adds one scalar offset to every node. The full curve is sampled for evidence, but node offsets are not independently estimated.
- Consequently, `d_curve(theta) - median(d_curve)` is invariant along a path: curvature is frozen, not learned frame by frame.
- Near and far proposals use separate contrast thresholds. The unchanged pair-safe comparator stops both when either proposal fails or seed pair separation/order becomes unsafe.
- The boundary-independent diagnostic uses the same proposal and thresholds but continues each boundary only until its own first failure. It is diagnostic only and is not accepted as pair-safe optional scene context.
- A stable center trajectory can coexist with a wrong curve shape or a silent ridge switch; checkpoint and image review are required.
