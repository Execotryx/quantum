# Blocked extraction from raw syndrome

The circuit extracts the first `k` linear quotient pairs from only the
first `2k` raw moments. It folds those pairs to the prefix numerator and
denominator and applies the prefold to the untouched suffix. Each
linear-fractional transfer matrix is symmetric in the reversed polynomial
variable. Reversing the order of the quotient pairs therefore transposes
the transfer product, keeps the denominator, and produces the
complementary numerator on the same wires. The blocked residual uses
both summaries in sequence. The circuit restores the squared denominator
scale and returns the prefix to quotient form. Running the stages in
reverse restores all raw moments.
[Earlier supplied-prefix experiment](aggregate-above-36-dqi-raw-suffix-prefold-26-11-2026-22-24-45.md)

| Input degree | Extracted pairs | Native qubits | Native gates per direction | Sequential gate estimate per direction |
| --- | ---: | ---: | ---: | ---: |
| 7 | 3 | 219 | 13,104 | |
| 35 | 9 | 891 | 109,428 | 271,674 |
| 35 | 17 | 891 | 201,582 | 421,098 |

Both serialized directions matched the scalar reciprocal recurrence on
12 genuine syndromes per row. The tests also checked clean scratch and
phase. The regular chart requires nonzero reciprocal pivots and a
prefix denominator of degree `k`. The estimate sums the existing
stride scheduler's scalar and interpolated product counts, normalization
and constant inversion. It reproduces the measured **103,788 gates**
for the first three sequential degree-35 reciprocals.
[Degree 7](evidence/aggregate36-20261126/dqi-raw-block-7-3.json)
· [Nine-pair block](evidence/aggregate36-20261126/dqi-raw-block-35-9.json)
· [17-pair block](evidence/aggregate36-20261126/dqi-raw-block-35-17.json)
· [Sequential control](evidence/aggregate36-20261126/degree35-subtower-first-three-reciprocals-native.json)

At 891 qubits the companion costs leave **23,542 gates** after the
current supplied-tape phase. In a serial composition the nine-pair
block and its inverse alone add **218,856 gates**. Under the
zero-failure assumption that subtotal caps this composition at
about **29.23 points** before the remaining pairs or exceptional
routing. The result rules out that schedule with the current
companions. The best complete cloud comparison remains **33.20483975**.
[Portfolio budget and phase price](degree35-subtower-27-11-2026-01-03-01.md)
