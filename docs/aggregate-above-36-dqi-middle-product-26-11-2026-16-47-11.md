# Transposed DQI polynomial products

The ordinary evaluation schedule prices a product over both entire source
polynomials. Pairing its requested coefficients with formal weights also
expresses that coefficient band as a product of one source and the reversed
destination weights. The emitter selects the two shortest ranges and uses
their interpolation rank, or scalar products when those are cheaper.

In the locator reciprocal each triangular power update now descends in blocks.
Terms that read within the output block run in their original descending order.
The remaining terms use separate convolution bands for each stride residue,
with both sources below the block. The Frobenius map is folded into the
linear evaluation of the right source without adding a field-word register.

| Native degree-35 scope | Previous charged gates | New charged gates | Declared qubits |
| --- | ---: | ---: | ---: |
| First reciprocal, one direction | 83,394 | 36,354 | 879 |
| First three reciprocals, one direction | — | 104,274 | 879 |
| Phase with supplied locator and evaluator, including residue cleanup | 197,937 | 194,493 | 879 |
| Phase with supplied locator and syndrome prefix, including evaluator cleanup | 222,393 | 215,505 | 879 |
| Generic rank-42 quotient into a dirty target | 24,108 | 20,916 | 2,127 |

The native reciprocal tests compare serialized circuits with an independent
scalar recurrence on 12 degree-35 syndromes. They verify restoration and
phase separately. The phase-stage tests check every one of 4,095 positions
with the pinned masks and fixture charts. The degree-3 fixture also composes
locator construction, residue phase and cleanup from raw syndrome.
The 28 focused native tests passed on Ubuntu on drive E. Pyright and
strict OpenSpec validation passed.
[Native receipts](evidence/aggregate36-20261126/dqi-middle-product/)

Because this locator route also constructs the evaluator, the appropriate
phase-stage control costs **194,493 gates**, leaving **85,507 gates** under
the 280,000-gate DQI allocation. A single reciprocal pair fits. Three
pairs and the phase stage cost **403,041 gates** before subsequent locator
steps, continuant folding or runtime chart routing. The savings apply to
the polynomial primitive and the phase stage. The sequential locator
schedule remains outside the budget.

The best full cloud comparison remains **33.20483975** and the independently
confirmed project's metric remains **26.78302388**.
