# Two-bank DQI Forney transform

The native circuit overwrites the evaluator with the Forney residue and
then restores it in the adjoint. For an odd-degree monic locator
`P(z) = z D(z²) + E(z²)`, its derivative is `D(z²)`. The original odd
locator coefficients hold the lower coefficients of `D`. The even
coefficients temporarily hold `E mod D`. The Euclidean elimination uses
the existing polynomial registers, and the same half-degree remainder
sequence acts on the even and odd parts of the evaluator.

The reconstruction applies a truncated quotient of reversed monic series.
It cancels the effect of the series on the live quotient tail before
transforming the entire evaluator bank. The field inverse borrows its
scale factor's register for the change of basis and restores it afterward.

| Native circuit | Declared qubits | Toffoli-like gates |
| --- | ---: | ---: |
| Prior degree-35 preparation, scan and inverse with supplied reciprocal | 1,731 | 91,569 |
| Two-bank degree-35 forward transform | 879 | 153,768 |
| Two-bank degree-35 inverse transform | 879 | 153,768 |

The pinned native simulator compared each direction with independent
long division on 12 degree-35 cases using the fixed half-degree chart
16 through 0. It verified the updated evaluator, restoration of the
original locator, clean scratch, and zero residual phase. Cases at
degrees 3, 7 and 9 also exercised the supplied-divisor and implicit
derivative variants. The focused suite passed **19 tests**, Pyright
reported zero diagnostics, and strict OpenSpec validation passed.
[Native degree-35 receipt](evidence/aggregate36-20261126/dqi-inverse-action/inverse-35-two-bank.json)

The 879-qubit transform fits within the 888-qubit development allocation.
Charging its two native directions and the 45,045-gate residue scan gives
a **352,581-gate subtotal** before locator and evaluator construction.
That exceeds the DQI gate budget. The compiler resource breakdown matches
the native totals and attributes **97,566 gates per direction** to
reconstruction, **31,212** to normalization, **22,848** to packed division,
and **2,142** to the outer split. Runtime chart selection and routing
remain open. The reference portfolio remains **33.20483975**.
[Compiler breakdown](evidence/aggregate36-20261126/dqi-inverse-action/resource-breakdown.json)
