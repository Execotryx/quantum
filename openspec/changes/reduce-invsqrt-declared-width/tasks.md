## 1. Control and tracer

- [x] 1.1 Add `configs/invsqrt-direct-v4.json` and protocol 4 in `tools/invsqrt_direct.py`. Rebuild v3 byte for byte (`ce8a58b6…f5b4`) as the control.
- [ ] 1.2 Implement `LivenessBuilder` in `src/qcompile/liveness.py`. Prove the emitted bytes match the unproxied build by SHA-256.
- [ ] 1.3 Record the per-call trace for v3: peak, call path at the peak, live allocations by site and width.
- [x] 1.4 Implement the op-stream interval analysis (direct iteration or KMX round-trip). Report declared count, `max id + 1`, distinct ids and maximum interval overlap.
- [x] 1.5 Build the dense and sparse counting fixtures and record how `num_qubits` is defined.
- [ ] 1.6 Read the pinned `_add_row`, `iadd`, `isub`, `_phase_by_bits` and rotate primitives. Tabulate their internal allocations.

## 2. Decision

- [ ] 2.1 Classify the gap as H1, H2 or mixed using the decision table. Bind the decision to the trace hashes.
- [x] 2.2 Recompute the qubit-to-Toffoli exchange rate from the control receipt.

## 3. Remap (only if H1 or mixed)

- [ ] 3.1 Implement greedy interval colouring with `x` pinned and splitting only at `R`/`HMR`.
- [ ] 3.2 Add proof fixtures: id handoff only after the previous last use, unchanged classical bits and conditions, unchanged op order.
- [ ] 3.3 Add mutation fixtures: overlapping handoff, moved `x` id, dropped reset. Each must fail native checks.

## 4. Width-aware arithmetic (only if H2 or mixed)

- [ ] 4.1 Implement C2a (gated operand bits formed and erased per carry step) as an opt-in row primitive. Prove phase correctness for every measurement branch.
- [ ] 4.2 Update the exhaustive integer model if row truncation or order changes. Rerun all 3,133,452 inputs.
- [ ] 4.3 Price C2a against the exchange rate. Price C2b–C2d only if C2a fails its proof or model gate.

## 5. Other components

- [ ] 5.1 Run the tracer on the reference DQI circuit and the nine banked ANGLE circuits. Report declared versus traced peak.

## 6. Verification and archive

- [ ] 6.1 Native fixtures at powers of four, segment edges and the worst-margin witnesses (`x = 2,875,262`).
- [ ] 6.2 Full 200,540,928-trajectory pass and fresh one-use confirmation on identical bytes.
- [ ] 6.3 Paired archive build with DQI and chemistry retained by hash. Reconcile retained costs.
- [ ] 6.4 Record the external receipt through `harden-kaggle-operations`.

## 7. Review

- [ ] 7.1 Run WSL tests, Pyright on changed files, Ruff and strict OpenSpec validation. Publish a dated change log with the trace, decision and receipts.
