# DQI coherent quotient preparation and phase

The previous monic quotient computed and uncomputed a full schoolbook
product. The revised circuit evaluates the operands at fixed GF(4096)
points, interpolates only the requested output coefficients, and repays
each measured product's phase before clearing the evaluation words.
Contiguous recursive splits solve the high-word reduction. The
arbitrary-target version keeps its XOR semantics, including for a zero
modulus constant.

The clean-output version uses its output bank for the high quotient and
applies a reversible truncated multiplication by the modulus before adding
the low product. Its modulus constant must be nonzero. The inverse runs
the truncated multiplication and high-word reduction in reverse order.
The scale step erases the old word with the live inverse factor, which
avoids another charged multiplication for each coefficient.

| Degree-35 native circuit | Declared qubits | Toffoli-like gates |
| --- | ---: | ---: |
| Previous arbitrary-output quotient | 2,511 | 260,820 |
| Revised arbitrary-output quotient, 54-term multiplier | 2,127 | 30,996 |
| Revised arbitrary-output quotient, rank-42 multiplier | 2,127 | 24,108 |
| Clean-output preparation, rank-42 multiplier | 1,731 | 23,262 |
| Clean-output inverse, rank-42 multiplier | 1,731 | 23,262 |

The rank-42 emitter uses the pinned, regenerated Nasir Ali field tensor.
Native quotient tests checked degrees 1 through 35 against independent long
division, including initialized targets, zero operands, and reducible moduli
within each mode's contract. They checked word restoration, scratch, and
phase after both directions.
[Quotient receipts](evidence/aggregate36-20261126/dqi-quotient/) ·
[Tensor source](../third_party/dqi-scheme42/)

At fixed degree 35 the composed stage prepares and uncomputes the residue
around the complete 4,095-position scan. The leading locator coefficient is
implicit. The native circuit used **1,731 qubits** and **91,569 charged
gates**, saving **2,616 gates** against the 94,185-gate bilinear scan with
supplied coefficients. All 32 full-weight trajectories passed the phase,
input restoration, and scratch checks. The smaller degree-three fixture
also passed. The focused suite passed 101 tests. Pyright reported zero
diagnostics, and OpenSpec strict validation passed.
[Full composition](evidence/aggregate36-20261126/dqi-quotient/prepared-scan-35.json)

The composition still takes a supplied locator, evaluator and derivative
reciprocal. Its four 35-word banks exceed the 888-qubit decoder allocation
even before workspace. A full benchmark candidate still needs coherent
reciprocal generation, degree routing, and residue preparation in the
existing decoder banks. The measured reference portfolio remains
**33.20483975**.
[Earlier scan comparison](aggregate-above-36-dqi-residue-scan-26-11-2026-07-46-21.md)
