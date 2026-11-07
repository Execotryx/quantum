## Why

The certified 199-qubit circuit removes Newton refinement and costs
1,008,498.1176395753. Lower-degree piecewise approximation, smaller
arithmetic workspace and a more compact reversible layout may reduce
complete cost further. The current direct circuit is the comparison
incumbent.

## Scope

- Reproduce the reference, prior Newton and current direct circuits.
- Fit and exhaustively test a correctly quantized minimax quadratic in
  the existing reversible layout. Then test layout and arithmetic
  changes separately against a frozen parent.
- Verify the cheapest eligible circuit on identical frozen bytes at full
  strength and on a fresh confirmation salt. Integrate through
  [shared verification](../prepare-next-hybrid-verification/proposal.md).
