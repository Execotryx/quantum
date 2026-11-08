## Why

DQI is still the pinned reference at 1.0×. The full profile puts 73.69%
of its 5,725,461 static Toffoli-like gates in the locator and its reversal,
and 25.23% in the scan.
[Full profile](../../../docs/dqi-full-stage-profile-08-11-2026-14-36-03.md)

Every part of a routed decoder now exists as a verified primitive:

| Primitive | Measured |
| --- | --- |
| Routed BM round with signed counter, three words | 983 Toffoli-like per direction, 224 qubits |
| Tower product-XOR / subtower inverse-XOR | 54 / 102 |
| Product erasure by measurement and CZ | 0 Toffoli-like |
| Direct-Forney evaluator and scan, supplied locator | 83,930 at `(70, 70)`; formula 997,605 at `(4095, 70)` |

The contract samples error weights 0–35 only, all inside the correction
radius. On that domain, BM with the static degree bound `min(r, 35)` is
exact. The only bounded resource is the retained-discrepancy history. At
most 34 entries can ever be needed, but almost every input needs at most one.

The earlier projection that missed 2× assumed 910 static history bits and a
separate 420-qubit evaluator register. This change replaces both: a tagged
history stack of `h` entries, and an evaluator computed in place over
`S1..S35`.
[Direct-Forney projection](../../../docs/dqi-direct-and-quotient-08-11-2026-16-07-08.md)

## What Changes

- Fix the history depth `h` by a registered classical overflow measurement
  on the verifier's own sampler.
- Emit full-width unrolled rounds with static active widths, a circular
  36-word template with a classical offset, 70 stored branch bits and the
  tagged `h`-entry history.
- Add a scaled in-place evaluator over `S1..S35`.
- Assemble locator, evaluator, direct-Forney scan and reversal into one
  `(4095, 70)` circuit. Verify it at reduced and full size, price it over
  five salts, and promote it at ≥2×.

## Impact

- Expected (estimate): about 1,920 qubits and 1.55 million Toffoli-like
  gates, about 3.6× on DQI and ×1.53 on the aggregate.
- Policy: a bounded history makes failures possible, though rare. This change
  registers that lane directly, as the competition allows priced failures,
  instead of first requiring an exact 910-bit layout that the projection
  shows cannot reach 2×.
- Code: new `src/qcompile/dqi/{bm_full_round.py, history_stack.py,
  inplace_evaluator.py, routed_decoder.py}`, new `tools/dqi_routed_decoder.py`.
