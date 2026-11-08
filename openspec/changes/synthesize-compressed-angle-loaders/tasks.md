## 1. Inputs

- [ ] 1.1 Register the eligible factorization from `fit-compressed-dfthc-factors` by hash, with its word table, tree, metrics and expected coverage.
- [x] 1.2 Confirm from the pinned verifier that addresses at or above `A` are never checked. Record the evidence.

## 2. Banked unary loader

- [x] 2.1 Generalize the bank construction in `src/qcompile/chemistry/loaders.py` to any `A`, `brot` and `J`. Keep the J9 tool as a control.
- [ ] 2.2 Rank `J` from 3 to the cap by complete cost using the pinned cost code.
- [ ] 2.3 Emit the best `J`. Run native checks for every address in both directions, bank boundaries and padding.

## 3. Monomial loaders

- [ ] 3.1 Implement the don't-care Möbius minimization. Record monomial counts per circuit before synthesis.
- [ ] 3.2 Implement the high/low construction with measurement erasure. Prove the fix-up phase for every outcome.
- [ ] 3.3 Implement greedy pairing. Record the gain.
- [ ] 3.4 Implement the sign-gauge search. Confirm that decoded metrics are unchanged and record the monomial reduction.
- [ ] 3.5 Emit monomial loaders only if their modeled complete cost beats Stage A by at least 10%.

## 4. Verification and promotion

- [ ] 4.1 Mutation fixtures for word bits, don't-cares, fix-ups and circuit order.
- [ ] 4.2 Complete metric run, two independent builds, full coverage and fresh chemistry confirmation.
- [ ] 4.3 Admission at or below 1.624×10⁹. Paired archive and external receipt.
- [ ] 4.4 Strict OpenSpec validation and a dated change log.
