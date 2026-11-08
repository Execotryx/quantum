# Two-octave fitted-table screen

The earlier 3.44% two-octave estimate assumed unchanged width and margin and
free address selection. This screen fitted the actual 256-row geometry: 128
segments on [1,2) and 128 segments on [2,4), with widths of 1/128 and 1/64
respectively. It searched each segment's coefficients within two integer units
of its rounded minimax coefficients and scanned all 3,133,452 verifier inputs.

A reversible in-place permutation selects the octave address with seven
controlled swaps, followed by their inverse. Native counts are 14 Toffoli-like
gates and no persistent additional qubits. Exhaustive eight-qubit mapping
fixtures checked selection, restoration and phase on all 256 input states.
An independent scalar recurrence checks the model on the small complete domain.

| Fractional bits | Model failures | Worst tolerance | Projected complete cost |
| --- | ---: | ---: | ---: |
| 28/20/14 | 64 | 114.90% | Not eligible |
| 29/20/14 | 404 | 148.35% | Not eligible |
| 28/20/15 | 356 | 137.78% | Not eligible |
| 28/21/14 | 0 | 66.60% | 516,038.42 |
| 29/21/14 | 0 | 55.07% | 533,848.67 |

The certified control costs 509,471.48. Estimates use native measured address
selection, controlled extra rows and isolated-row liveness; lookup and repair
savings are structural estimates, and complete-circuit width is projected.
Neither passing format reaches the 3% model-only screen, so no full two-octave
circuit was emitted or promoted. The five tested formats do not prove that all
other geometries or arithmetic designs fail.

All five base tables were independently regenerated, their retained offsets
checked, and their complete-domain model receipts rechecked. Four native/small-domain
tests passed. Pyright, Ruff and strict OpenSpec validation passed. Individual
receipts are in `docs/evidence/invsqrt-two-octave-20261108/`; the frozen control
and its verification receipts were not modified.
