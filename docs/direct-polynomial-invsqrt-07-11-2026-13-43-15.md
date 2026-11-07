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
