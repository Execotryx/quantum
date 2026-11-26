# In-place DQI evaluator and syndrome-prefix scan

The evaluator replaces the first syndrome words with the truncated
locator product. Recursive block products handle the cross terms, and
each leaf scales its words by the nonzero locator constant. The field
inverse borrows the source basis and stays live only during leaf
scaling. This frees its qubits before the larger interpolation workspace
is needed. The inverse restores the original syndrome prefix.

The pinned backend emitted these degree-35 evaluator circuits with two
35-word input banks. Each figure applies to one direction.

| Evaluator | Declared qubits | Charged gates |
| --- | ---: | ---: |
| Previous schedule, rank-54 tensor | 903 | 36,114 |
| Compact schedule, rank-54 tensor | 879 | 14,964 |
| Compact schedule, rank-42 tensor | 879 | 12,228 |

The algorithm saves **21,150 gates per direction** at the same field
tensor. Using the pinned rank-42 tensor saves a further **2,736**.
[Native evaluator comparison](evidence/aggregate36-20261126/dqi-evaluator/evaluator-cost.json)

The composed circuit receives the monic locator and the first 35
syndrome coefficients. It computes the evaluator and residue, scans all
4,095 positions, and restores its inputs at **879 qubits** and **222,393
charged gates**. The native simulator checked the error-mask phase,
clean scratch and restoration for 32 full-weight inputs on the fixed
Euclidean chart. Rank-42 evaluator preparation and restoration add
24,456 gates to the previously measured 197,937-gate residue stage.
The separate supplied-evaluator fixture still checks weight-34 padding.
All 31 focused tests passed on Ubuntu on E, including nonmonic locator
fixtures and the reduced routed decoder through the pinned verifier.
Pyright and strict OpenSpec validation also passed.
[Native composition receipt](evidence/aggregate36-20261126/dqi-evaluator/syndrome-scan-35.json)

The composed stage leaves **57,607 gates** under the 280,000-gate
development allocation. That allowance must cover locator construction
and restoration and coherent routing for all runtime charts. The best
full cloud comparison remains **33.20483975**.
