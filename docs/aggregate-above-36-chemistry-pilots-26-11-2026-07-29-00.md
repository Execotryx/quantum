# Above-36 variable-basis chemistry pilots

Four registered fits tested whether reducing the basis groups from nine to
eight could bring chemistry near the joint cost frontier. Each lane ran 500
evaluations, with seven-bit decoding at the initial, intermediate and terminal
checkpoints. I3 merges the closest public reference groups. I2 clusters
spectral factors. The two starts and their budgets were frozen before fitting.
[Registrations and receipts](evidence/aggregate36-20261126/variable-basis/)

| Shape | Start | Continuous two-body residual (Ha) | Final seven-bit two-body residual (Ha) | Final raw normalization (Ha) |
| --- | --- | ---: | ---: | ---: |
| (8, 127, 42) | I3 | 0.041082 | 0.157966 | 1519.50 |
| (8, 127, 42) | I2 | 0.167973 | 0.613718 | 2134.13 |
| (8, 120, 40) | I3 | 0.050505 | 0.230899 | 1522.57 |
| (8, 120, 40) | I2 | 0.195950 | 0.687749 | 2306.39 |

All four lanes reached their evaluation cap above the 0.020 Ha accuracy
threshold. The seven-bit gap is already large enough to affect which fit
objective is useful. The smallest terminal continuous residual was 2.05 times
the limit, while the corresponding decoded residual was 7.90 times the limit.
Its raw normalization was 5.37 times the public control's 283.06 Ha.
The floating-point rank relaxation still leaves both shapes eligible for a
different initializer and a fit that accounts for decoded angles and
normalization. The capped lanes supply no accepted chemistry component.
[Rank diagnostic](evidence/aggregate36-20261126/chemistry-psd-rank-relaxation.json) ·
[Decoded control](evidence/aggregate36-20261126/fixed-dictionary/control.json)

An extra packed-tensor check held each fixed-dictionary finalist's decoded
basis and weights constant and solved for the best continuous symmetry shift.
The reduction in two-body residual was below 0.0001 Ha for each of the
35-, 36- and 40-channel finalists. Each remained above the gate before one-body
accuracy, normalization or native loader cost were considered.
[Fixed-dictionary decisions](evidence/aggregate36-20261126/fixed-dictionary/decision.json)

The above-36 plan still needs a chemistry component that passes decoded
accuracy and full loader pricing, a DQI decoder with lower measured executed
cost, and a reversible inverse-square-root schedule that meets its cost budget.
The highest full cloud comparison remains **33.20483975**.
[Component comparisons](aggregate-above-36-implementation-26-11-2026-07-19-40.md)
