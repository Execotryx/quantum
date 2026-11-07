## Why

The locally certified hybrid still uses the official DQI reference
circuit. A reversible decoder can improve the full `R * Q**2 * T`
objective, especially if it reduces width without degrading sampled
correctness. Published operation counts from a fixed-mask circuit
cannot establish a drop-in improvement for the competition contract.

## Scope

- Build and verify a reversible decoder for the actual field, syndrome
  convention and runtime classical mask.
- Establish a working exact path with measured resource costs. Compare
  a width-focused revision of the reference EEA architecture with a
  reversible BM slice before committing to the full decoder.
- Pursue workspace reuse toward the 840-input-qubit floor using a
  proved register schedule. Treat near-900-qubit public widths as a
  research target.
- Use the [shared verification plan](../prepare-next-hybrid-verification/proposal.md)
  for matched controls, full verification, confirmation and release.
