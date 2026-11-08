## Why

The certified lattice candidate uses 155 qubits and about 3,287 rotation-inclusive
Toffoli-equivalents. Existing independently tested row and phase-bit refinements
have not reached the compact target. The separate compact tranche investigates a
phase-accumulation architecture with explicit resource and correctness gates.

## What Changes

- Register a research tranche capped at 40 engineering hours, targeting at most
  100 declared qubits and 2,000 rotation-inclusive Toffoli-equivalents.
- Model removal of the stored output and the cost of a persistent phase-gradient
  register, including preparation, accumulation, cleanup, and rounding.
- Model gated signed-digit rows independently, including full measurement-phase
  corrections, before considering their combination.
- Emit no prototype unless a complete, justified resource model predicts at
  least 20% lower complete cost than the certified control.

## Impact

This registration authorizes model development, not a promotion or claim of
achieved resources. The existing lattice control and its confirmation stay pinned.
