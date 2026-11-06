## 1. Freeze the intended release

- [ ] Start from the tested archive SHA-256 `8fb545091a1cf66c2656bdce40bedbc26e478746301f9a777f56173f88b88503`. Audit the [combined receipts](../../../docs/evidence/invsqrt-chemistry-20261107/combined-result.json) and the inverse-square-root full and confirmation records. Pin the contract, backend, lock, source revision and per-file identities. Preserve the original archives and receipts.
- [ ] Make two narrow rebuild recipes. Reproduce the confirmed inverse-square-root KMB from the registered width tuple. Reproduce all nine banked J9 KMBs from the pinned recovered words. Bind the chemistry factorization and tree, even though the NPZ is retained. Both recipes must generate bytes from inputs in new directories.

## 2. Extend the certification workflow

- [ ] Add benchmark-keyed confirmation records to the candidate store. Derive the required benchmark set from generated paths and bind each record to its complete component, including retained inputs the verifier uses. Keep global salt reservations and history checks atomic under the existing store lock. Apply one-use rules across candidates and preserve old records.
- [ ] Adapt the CLI and worker to attach the actual benchmark receipt for each registered confirmation. Map inverse-square-root and chemistry `verified_shots` to 200,540,928 and 254,464 respectively. Document the pinned fail-fast checks before accepting zero observed failures. Treat missing, rejected or incomplete results as blocking.
- [ ] Define a reviewed import path for the existing prospective confirmation receipts. Check registered salts, artifact and source identities, chronology, raw counters and proof of unused results before reserving them in the ledger. If the evidence cannot be reconciled, block certification and review the candidate under the one-use policy before any additional confirmation.
- [ ] Require matching per-benchmark opportunity, margin or residual, mutation, primitive and stability evidence. Include chemistry phase, selection, scratch and padding after every traversal step and the 128-qubit limit. Preserve evidence on rejection.

## 3. Verify and freeze

- [ ] Test legacy compatibility, missing or swapped receipts, duplicates, consumed records, changed component inputs and mixed generated/retained manifests. Run Pyright on changed Python and relevant WSL tests.
- [ ] Build twice, require identical file hashes and ZIP bytes, and run the pinned full metric on a fresh extraction. Require exact 200,540,928 inverse-square-root, 102,400 DQI and 254,464 chemistry trajectories, both cost reductions and aggregate improvement. Run serially with measured memory headroom.
- [ ] Save the deterministic ZIP, local certificate, both confirmation records and full metric receipts. Reconcile the tested archive identity if certification produces a different hash. Record external acceptance separately if authorized and performed.
