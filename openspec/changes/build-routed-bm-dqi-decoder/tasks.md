## 1. Arithmetic

- [ ] 1.1 Add `src/qcompile/dqi/bilinear.py`: tensor construction, rank search (flip graph or SAT) and exhaustive verification. Record the GF(64) rank-15 decomposition and its basis.
- [ ] 1.2 Emit the tower product-XOR from the decomposition. Measure Toffoli-like gates, width and cleanup. Target 45.
- [x] 1.3 Implement product-register erasure by X-basis measurement and conditioned CZ fix-ups. Prove it on all basis pairs and random outcomes. Add a dropped-CZ mutation.
- [x] 1.4 Implement the norm-based inverse through the GF(8) subtower. Test all 4,096 inputs, including zero. Target at most 110.
- [ ] 1.5 Implement the controlled product. Target 57.
- [ ] 1.6 Optional: search a direct GF(4096) decomposition below 45. Stop at the registered time cap.

## 2. Exact locator

- [x] 2.1 Re-derive the rescaled routed update and the `σ₀·δ = 1` invariant under the pinned indexing. Check each round's map and inverse against the classical BM oracle on reduced fields.
- [ ] 2.2 Build the per-branch liveness table. Price the static-slot and stack history layouts, including the Q² penalty, and choose one.
- [x] 2.3 Derive exact static degree bounds per round.
- [ ] 2.4 Implement `src/qcompile/dqi/bm_circuit.py` as unrolled rounds with history. Verify forward and reverse round trips on reduced shapes for every supported weight.

## 3. Exact phase-only scan

- [ ] 3.1 Implement the evaluator and the half-degree reciprocal `Ψ`. Prove `Ψ·σ' ≡ 1 (mod σ)` on oracle locators, and handle weight 0.
- [x] 3.2 Implement `src/qcompile/dqi/scan.py` with in-place Chien updates, the 11-gate zero test, the mask-conditioned transform and 12 CCZ gates per position.
- [x] 3.3 Prove the trace identity for the runtime mask and the Forney identity against `recover_forney` on all weights 0–35.
- [x] 3.4 Mutation fixtures: wrong mask bit, skipped position, missing transform reversal.

## 4. Assembly and exact promotion

- [ ] 4.1 Assemble in `tools/dqi_prototype.py`. Record per-stage Toffoli-like gates, width, serialized operations, wall time and peak memory.
- [ ] 4.2 Verify `(63, 4)` and `(127, 12)` with zero value and phase errors.
- [ ] 4.3 Run the matched full-size 2,560-shot development pair against the reference on the cloud VM.
- [ ] 4.4 Admission: zero errors and measured cost at most half the reference. Record the 8× stretch checkpoint.
- [ ] 4.5 Freeze, run the full 102,400-shot verifier and the one-use fresh-salt confirmation, then the paired archive.
- [ ] 4.6 Record the external receipt and reconcile it under the exact band.

## 5. Bounded-history lane (separate registration, after 4.4)

- [ ] 5.1 Register the one-entry history, the cutoff policy, the exhausted-bound behavior and the truncation acceptance rule.
- [ ] 5.2 Fit cutoffs on the verifier's sampled distribution. Record the classical failure estimate.
- [ ] 5.3 Measure at least five salts at 102,400 shots. Price at `k_max + 2`. Promote only if it beats the exact decoder by at least 1.5× after pricing.

## 6. Review

- [ ] 6.1 WSL tests, Pyright on changed files, Ruff, strict OpenSpec validation and a dated change log with all receipts.
