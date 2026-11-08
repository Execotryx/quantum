## 1. Receipt ledger

- [x] 1.1 Add `tools/kaggle_receipt.py` with `prepare`, `record` and `reconcile`. Pin the Kaggle CLI version in each new direct record. The helper never uploads.
- [x] 1.2 Record the v2 receipt (public 1.37797, local 1.3779715418) with `binding: inferred`, and mark it reconciled under the exact band.
- [ ] 1.3 Prepare v3 (`920fcfba…f94d`) with message `v3 920fcfba647e`. After the user uploads it, record and reconcile it against 1.5753293577.
- [x] 1.4 Add offline fixtures for message matching, band selection, CSV parsing and immutable records.

## 2. Metric drift gate

- [x] 2.1 Implement the pull-and-hash check against `df418aff…ac73` inside `prepare`. Block on mismatch.
- [x] 2.2 Write the reconciliation-note template: diff summary, affected controls rerun, decision.

## 3. Packaging negative fixtures

- [x] 3.1 Add the seven negative fixtures from the design to `tools/hybrid_preflight.py` tests. Each must fail with a specific diagnostic.
- [x] 3.2 Confirm v2 and v3 archives still pass preflight unchanged.

## 4. DQI salt policy

- [x] 4.1 Add a salt-schedule registration to `tools/dqi_development.py` with at least five development salts and one reserved confirmation salt.
- [x] 4.2 Add pricing at `k_max + 2` using the pinned `clopper_pearson_upper_bound`. Test it against the recorded 1.19126 (k = 0) and about 1.24 (k = 14) factors.

## 5. Screen outcomes

- [x] 5.1 Add `budget_limited` to the experiment state machine with the improvement-window rule. Store the evaluation trace needed to compute it.
- [x] 5.2 Add superseding status records for the three compressed chemistry pilots. Leave the original files unchanged.

## 6. Cadence and selection

- [x] 6.1 Add the cadence, slot-reservation and two-slot selection rules to README's operations section.
- [x] 6.2 Add the calendar to the dated change log.

## 7. Validation

- [x] 7.1 Run the relevant WSL tests, Pyright on changed Python files, Ruff and strict OpenSpec validation.
- [ ] 7.2 Publish a dated change log with the v2 and v3 receipt records.

[Operations controls, verified preflights and calendar](../../../docs/hybrid-roadmap-operations-08-11-2026-14-42-35.md)
