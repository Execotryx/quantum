## Why

The certified v5 inverse-square-root circuit spends **766** of its 2,908
Toffoli-like gates on one coefficient lookup over 384 rows. The
calibrated cost model attributes them exactly.
[Cost model](../../../docs/invsqrt-costmodel-08-11-2026-16-08-55.md)

`_load_table` in `src/qcompile/invsqrt/direct.py` computes a fresh
temporary AND for every child of every internal tree node. The standard
unary-iteration step (Babbush et al., Phys. Rev. X 8, 041015, 2018)
computes one AND for the left child, then reaches the right child with one
CNOT from the parent control. This repository's banked chemistry loader
already does this (`builder.cx(control, child)` in
`tools/banked_chemistry.py`). The repair walk in
`src/qcompile/invsqrt/unlookup.py` has the same per-child pattern.

The change leaves every XOR'd word, phase and register unchanged. Only
the gates that build the path flags change.

## What Changes

- Add an opt-in `sibling_cnot` flag to both walks. Leave the default off
  so frozen recipes rebuild byte for byte.
- Update the cost model and recalibrate it on all existing receipts plus
  the new circuit.
- Build the v6 candidate from the v5 trimmed recipe with the flag on.
  Verify, confirm and archive it.

## Impact

- Expected: lookup about 766 → 383 Toffoli-like gates, unlookup walk about
  halved, complete count about 2,500, cost about 411,000 (−13%), ratio
  4.40× → about 5.05×, aggregate ×1.047. Width stays at 150.
- Code: `src/qcompile/invsqrt/{direct.py, unlookup.py, costmodel.py}`,
  `tools/invsqrt_direct.py`, new `configs/invsqrt-direct-v6.json`.
- Risk: low. The arithmetic and phase function are unchanged. The
  verification chain still runs in full.
