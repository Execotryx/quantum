# Independent direct polynomial phasing

The public direct-phasing notebook listing identified revision 7, its notebook
license and a separate checkpoint input. The listing did not establish a
reproducible, licensed generator and coefficient derivation for the tested
circuit. The separate public 62-qubit receipt came from a portfolio assembler
that pins and copies a published circuit. Its generator is outside this
implementation. No public circuit, checkpoint or generator was incorporated.
[Notebook listing](https://www.kaggle.com/code/rudrabhaskar/highest-public-score-direct-polynomial-phasing)
and [portfolio provenance](https://github.com/EigenOS-Quantum/eigenos-vqcc/blob/main/NOTICE-v7.md).

The implementation uses the normalization from the
[sponsor paper](https://arxiv.org/html/2610.23832v1#S3.SS1) and independently
generated dyadic Taylor pieces. For input `x`, the exponent is
`k = floor(floor(log2(x))/2)`, the normalized argument is `u = x/4^k`,
and the phase in turns is approximated by `2^-k P(u)`. The coefficient
generator rounds exact squared magnitudes by comparing to the squared
half-integer boundary. It uses no floating-point coefficient fit.

The generator loads alternating Taylor magnitudes with an XOR table, runs
Horner subtraction using column-truncated nonnegative products, rescales
the output and applies per-bit phase. The integer bit is retained through
scaling because `u=1` occurs for all powers of four. Only its final
integer-turn contribution can be omitted. Inversion restores the input and
zeros every temporary register. Temporary AND cleanup relies on preserved
controls and the pinned measurement-conditioned phase correction. Each
conditional product leaves its operand and selector untouched through
cleanup.

The separate full-domain model records the phase64 margin and its two
distinct witnesses, the most restrictive absolute margin and highest
fraction of tolerance. Native fixtures check register and scratch
restoration, exact phase and executed counts before the screen computes
rotation-inclusive cost. The original Newton builder remains the control
for both the official reference and the confirmed hybrid incumbent.

## Prospective screen and confirmation

The committed source at `a9d673d68cbae0d2305828c4bd167f555f562e9b` reproduced
both Newton controls and completed nine attempts in 51.94 seconds on one
screening lane. The staged cubic control cost 2,301,992.14. The narrower
cubic cost 1,998,683.48. Fusing its row subtraction reduced the cost to
1,043,972.93. Reusing the clean lookup scratch in the fused circuit reduced
the declared width from 206 to 199 and the cost to **1,008,498.12**.

The selected cubic uses 64 subdivisions per unit of normalized argument
and coefficient fractional widths `31, 26, 21, 16`. It passed the model on
all 3,133,452 inputs and matched native phase and resource counts on 17,472
development trajectories covering 4,353 distinct inputs. The minimum margin
was 544,143,971 phase64 units at input 3,112,927. The worst relative phase
error used 27.2863% of tolerance at input 1,064,915.

The [full run](evidence/invsqrt-direct-20261107/full/result.json) and
[fresh confirmation](evidence/invsqrt-direct-20261107/confirmation/result.json)
each passed 200,540,928 trajectories and measured the same complete cost,
**48.8457%** below the hybrid incumbent. Both bind the KMB with SHA-256
`dfaf3345abf3ff70e9a633bfd0cd07baa7e7bc7eb70105b557d09726ef1f5a8c`.
The [screen decision](evidence/invsqrt-direct-20261107/decision.json) binds
all nine attempts and the exact preregistration.
