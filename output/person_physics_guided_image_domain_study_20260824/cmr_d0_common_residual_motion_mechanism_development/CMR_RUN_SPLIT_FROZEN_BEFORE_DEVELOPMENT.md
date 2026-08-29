# CMR run split frozen before development

- State: `FROZEN_BEFORE_DEVELOPMENT`
- Frozen at HEAD: `b6e7a3a5ade1844d14c771c7aaaa02099e663c3a`
- Split basis: run identity plus GT-blind frozen input availability.
- Manual reference outcome used: `NO`.
- Future CMR performance used: `NO`.
- Same-run cross-pool leakage: `NO`.

## Pools

- Development: R01ZF, R02ZF, R03ZF.
- Confirmation: R04ZF; only input availability may be inspected before CMR-v0 freeze.
- Diagnostic: optical opposite-direction candidate runs lacking complete frozen cross-modal P0/topology coverage.

## Deterministic accounting

| pool | run_id | scheduled_lag1_pairs | cross_modal_eligible_windows | eligible_branch_instances |
| --- | --- | --- | --- | --- |
| CONFIRMATION_POOL | R04ZF | 195 | 98 | 166 |
| DEVELOPMENT_POOL | R01ZF | 141 | 73 | 173 |
| DEVELOPMENT_POOL | R02ZF | 22 | 13 | 37 |
| DEVELOPMENT_POOL | R03ZF | 36 | 21 | 21 |

The confirmation pool is not used for common-motion estimation, residual calculation, method selection, real-case selection, or development reporting.
