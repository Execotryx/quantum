## Why

DQI cost scales with the square of its width. The routed decoder from
`build-routed-bm-dqi-decoder` is expected to land at 1,800–2,650 qubits.
Public decoders reach 880–892 qubits, only about 40–50 above the
840-qubit syndrome bank. Going from 1,893 to 900 qubits is worth
`(1,893 / 900)² ≈ 4.4×` on DQI by itself, or ×1.64 on the aggregate.

This project's earlier DQI design already noted the key counting fact.
At weight 35, a normalized locator (constant term implicit) and its
evaluator fill exactly the 70 syndrome words. It also proposed storing
`g = ω · (σ')⁻¹ mod σ` in place of `ω`. Then `e_j = g(X_j)` at every root,
and the mask phase becomes linear in `g`. The scan would need only the
11-gate zero test per position, plus Clifford work.

## What Changes

- Prove which decoder states fit in the syndrome bank plus a small
  workspace, and that the in-place transform `S ↔ (σ, g)` is a bijection
  on every supported input.
- Prototype three in-place families exhaustively on small fields:
  continued-fraction quotients, a discrepancy-domain (Schur-type,
  reformulated-BM) update, and a routed decoder followed by an in-place
  conversion.
- Build the winning family at full size with a linear phase scan.
- Promote under the exact-first rules, with a bounded variant allowed
  under the same pricing as the routed lane.

## Impact

- Code: new `src/qcompile/dqi/inplace.py` and reduced-field harnesses;
  `tools/dqi_development.py`.
- Research risk is high. Timebox: 15 December 2026 to 8 January 2027,
  with a stop rule. The routed decoder remains the fallback component.
