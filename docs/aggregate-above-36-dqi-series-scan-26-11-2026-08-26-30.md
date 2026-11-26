# Degree-35 two-bank DQI phase scan

The Euclidean inverse action now returns its recursive result as a reversed
series divided by the reversed monic modulus. A parent reuses those
coefficients and computes only the new suffix. For a packed division
`X = D C + E`, set `Q = E / (A mod D) mod D`. The normalized parent
result is the series `Q_rev / D_rev + z^deg(D) C_rev / A_rev`, truncated
to the parent degree. The suffix operator keeps the original quotient
tail while extending the child series. Only the outermost stage converts
the result back to polynomial coefficients, and the inverse reverses
these steps.

| Degree-35 resource | Previous two-bank build | New two-bank build |
| --- | ---: | ---: |
| Forward transform | 153,768 | 76,446 |
| Inverse transform | 153,768 | 76,446 |
| Prepare, phase across 4,095 positions, and restore | 352,581 inferred from prior stage counts | 197,937 measured |
| Peak declared qubits | 879 for the transform | 879 for the complete stage |

The complete native phase stage used the pinned rank-42 field tensor and
matched the exact error-mask phase on 32 trajectories. The panel included
16 weight-35 cases and 16 weight-34 cases padded by a factor of `z`.
That factor adds a root at zero outside the scan, and the evaluator
acquires the same factor. The native simulator checked the restored
locator, evaluator, and masks, clean scratch, and charged gate counts.
The fixed Euclidean chart was selected from the classical oracle before
executing the panel. Separate inverse-action tests compared each direction
with long division, including a larger-than-one degree drop. The focused
suite passed 72 tests on Ubuntu on E. Pyright and strict OpenSpec validation
also passed.
[Prior two-bank receipts](aggregate-above-36-dqi-inverse-action-26-11-2026-08-18-48.md) ·
[New native receipts](evidence/aggregate36-20261126/dqi-series-scan/)

The stage leaves **82,063 gates** under the 280,000-gate development
allocation. The remaining allowance must cover building and restoring
the locator and evaluator, plus coherent routing for all runtime charts.
The reference portfolio remains **33.20483975**.
