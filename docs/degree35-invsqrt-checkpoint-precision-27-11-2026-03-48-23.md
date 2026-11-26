# Checkpoint coefficient precision and reciprocal factorization

Rounding the frozen three-column table to **28 fractional bits**
passes all **3,133,452** legal inputs at **89.24%** worst-case tolerance
use. The 27-bit table misses nine inputs. The 28-bit entries fit in
28, 20, and 13 unsigned bits in the three respective columns.
[Registered fixed-point screen](evidence/aggregate36-20261126/invsqrt-checkpoint-precision-registration.json)
· [Numerical receipts](evidence/aggregate36-20261126/invsqrt-checkpoint-precision-screen.json)

The fitted columns share a factor of `512 / d`, where
`d = 4 * floor(root / 2) + 2`. Fitting one constant triple per root
parity gives six constants and **128 reciprocal entries**. The staged
integer model separately rounds the numerator and reciprocal to 28
fractional bits before multiplying them. It passes all inputs at
**90.59%** worst tolerance use. After subtracting the known unity,
the numerator correction lies in `[-1040318, 1048575]` and fits in
**21 signed bits**. Its product with the reciprocal can be accumulated
alongside the known-unity contribution. If an implementation uses
33 fine rotations and one T-like gate, the measured margin projects
**476.09** equivalents for arithmetic and cleanup at 39 qubits after
the verified prefix and return charge.
[Frozen separately rounded constants and reciprocal rows](evidence/aggregate36-20261126/invsqrt-checkpoint-precision-staged28-coefficients.json)
· [Measured checkpoint return](degree35-invsqrt-checkpoint-return-27-11-2026-03-24-19.md)

The pinned backend verified the staged integer formula on 2,816
checkpoint inputs for each of two seeds, including the full-domain
worst case. Two serialized reciprocal-only phasing probes also passed
all 128 addresses with eight trajectories each. They preserved the
31 live checkpoint wires, matched the exact reciprocal phase at
normalization exponent zero, and cleared scratch.

| Reciprocal phase schedule | Probe width | Mean Toffoli-like gates | Fine rotations |
| --- | ---: | ---: | ---: |
| Direct unary traversal, one angle per address | 37 | 126 | 128 |
| Load, phase, and unload two bits at a time | 39 | 3,528 | 28 |

The direct probe's rotation charge alone is at least **888.88**
equivalents under the most favorable possible error margin for the
complete legal domain. Combining that probe with the validated prefix
and return would cost at least **64,042.92** at 39 qubits. The sliced
schedule exceeds the cutoff through lookup and clearing alone. Both
probes exclude numerator arithmetic and exponent routing. A complete
implementation needs broader coefficient streaming, narrower arithmetic,
or a recurrence that generates the reciprocal contribution without
these lookup charges.
[Staged formula on native checkpoint bits](evidence/aggregate36-20261126/invsqrt-checkpoint-precision-native-bits.json)
· [Native lookup registration](evidence/aggregate36-20261126/invsqrt-checkpoint-lookup-registration.json)
· [Serialized lookup receipts](evidence/aggregate36-20261126/invsqrt-checkpoint-lookup-native.json)
