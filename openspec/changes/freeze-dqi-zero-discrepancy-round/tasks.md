## 1. Classical circular model

- [ ] 1.1 Implement `step_circular` and `reverse_circular` in `src/qcompile/dqi/bm_circular.py`, with `UnsupportedRound` for `Δ ≠ 0` and `T₀ ≠ 0`.
- [ ] 1.2 Test equivalence with `bm_routed.forward` through the fold map on 1,000 seeded correctable `(4095, 70)` inputs and on the weight-0 input.
- [ ] 1.3 Assert that no `UnsupportedRound` occurs on those inputs.

## 2. Frozen states

- [ ] 2.1 Generate `tests/fixtures/dqi_round_states.json` once from registered seeds. Record its SHA-256.
- [ ] 2.2 Add a test that recomputes the fixture and compares it byte for byte.

## 3. Native comparison

- [ ] 3.1 Run the twelve synthetic states forward and in reverse on the native backend. Compare all registers and check that scratch is zero.
- [ ] 3.2 Add the unchanged-counter mutation. It must fail.

## 4. Supersede

- [ ] 4.1 Replace the zero-discrepancy scenario in `assemble-routed-bm-direct-forney-decoder` with this change's requirement, and mark its task 2.2 as dependent on task 3.1 here.
- [ ] 4.2 WSL tests, Ruff, Pyright, strict OpenSpec validation and a dated change log.
