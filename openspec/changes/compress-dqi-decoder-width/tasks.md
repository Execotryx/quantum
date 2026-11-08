## 1. End-state proofs

- [x] 1.1 Prove the `S ↔ (σ, ω)` and `ω ↔ g` bijections for weights 0–35 under the pinned indexing. Define the weight encoding and the zero case.
- [x] 1.2 Prove the linear phase identity `Tr(μ(E_j) · g(X_j))` against `recover_forney` and the trace-dual basis.

## 2. Small-field prototypes

- [ ] 2.1 Implement W1, W2 and W3 as classical reversible programs over GF(2⁴) and GF(2⁶) with `n ≤ 12` in `src/qcompile/dqi/inplace.py`.
- [ ] 2.2 Enumerate every syndrome. Check bijectivity, restoration and phase. Record width and products per stage.
- [ ] 2.3 Write the liveness and information table per family. Reject families at the first unproved step.

## 3. Projection and selection

- [ ] 3.1 Project each surviving family to `(4095, 70)` with the routed lane's measured primitives. Keep families meeting the target.
- [ ] 3.2 Select at most two families for GF(4096) emission.

## 4. GF(4096) circuits

- [ ] 4.1 Emit `(63, 4)` and `(127, 12)` circuits. Verify them against the classical oracles with mutation fixtures.
- [ ] 4.2 Emit the full-size circuit. Run the matched 2,560-shot pair against the best routed decoder.

## 5. Promotion

- [ ] 5.1 Admission: exact, zero errors, at least 1.5× lower cost than the best routed decoder. A bounded variant follows the routed lane's Stage E rules.
- [ ] 5.2 Full 102,400-shot run, fresh confirmation, paired archive and external receipt.
- [ ] 5.3 Apply the stop rule on 8 January 2027 and record the disposition.
- [ ] 5.4 Strict OpenSpec validation and a dated change log.
