# Carry rows in the 39-qubit inverse-square-root source

The pinned Tony Li assembly already uses the complement-and-add structure
on the twelve complete eight-bit rows matched here. The source prepends
and appends the same sign-dependent target complement around an
unconditional addition. In the inner chain each nonlinear carry is
`c XOR ((a XOR c) AND (b XOR c))`, costing one Toffoli. The measured
cleanup applies a conditional CZ on the same framed controls.
[Published source and credits](degree35-invsqrt-source-research-27-11-2026-01-39-29.md)
· [Add/subtract construction](https://arxiv.org/abs/2410.00899)

The exact source census finds **629** unconditional six-instruction
majority cells, with 411 before the first fine rotation and 218 after
the last. These and the **149** unconditional controlled swaps account
for 778 of approximately 1,339.88 executed Toffoli-like gates. Leaving
those 778 gates in place gives at most about 562 other charged gates.
Even a one-third saving on all 562 would save about 187 per input.
The source-only path to 35 at 39 qubits requires about 246 fewer
charged equivalents per input, or about 224 even if the existing
33 rotations attain the zero-phase-error pricing limit. The count
therefore excludes a simple add/subtract substitution at that width.
[Source census](evidence/aggregate36-20261126/invsqrt-incumbent-rows-screen.json)
· [Matched native profile](evidence/aggregate36-20261126/invsqrt-incumbent-phase-window.json)

## Narrower row layout

Each matched row adds or subtracts a six-bit source, a fixed high one
and the incoming carry. The rewrite stores six carries in the source
wires, toggles the high target by the final OR carry, and restores the
source and incoming carry with an inverse ripple. The existing sign
frame is preserved. A splice requires the complete terminal operation,
both complements, all seven clean and distinct temporaries, and proof
that each removed measurement outcome is used solely for its matching
phase correction.
[Borrowed-carry construction](https://arxiv.org/abs/quant-ph/0410184)
· [Source rewrite](../tools/invsqrt_incumbent_rows.py)

For one extracted row, the native circuit checks covered all **65,536**
basis inputs under two measurement seeds. The original and rewrite
matched the arithmetic contract for both signs, restored the source
and carry, and left scratch and phase clear. Separate source executions
emitted identical KMX for the complete circuit. The pinned verifier
on E-backed Ubuntu passed one trajectory for every one of the
**3,133,452** legal inputs using `--batch-size 292` and development salt
`source-signed-rows-20261127-development`.
[Exhaustive row fixtures](evidence/aggregate36-20261126/invsqrt-incumbent-rows-fixture.json)
· [Complete circuit one-trajectory replay](evidence/aggregate36-20261126/invsqrt-incumbent-rows-one-shot.json)

| Complete circuit, one trajectory per input | Qubits | Mean Toffoli-like gates | Priced cost |
| --- | ---: | ---: | ---: |
| Source control | 39 | 1,339.88 | 61,696.30 |
| Twelve borrowed-carry rows | 39 | 1,411.88 | 64,504.29 |

Each replaced row eliminates seven separate carry wires from its active
row and raises its count from seven to thirteen Toffolis. Peak width
comes from other windows, including the cleanup after phasing. The
candidate costs **4.55%** more and is excluded from the degree-35 cloud
campaign.
[Control replay](evidence/aggregate36-20261126/invsqrt-control-native-one-shot.json)

The source checkpoints after KMX lines **5,948**, **9,871**, and
**10,438** have affine rank **39** modulo the constant. Each witness
uses 2,816 legal inputs stratified by leading-bit position. The pinned
native backend reproduced all three value matrices on two seeds, and
the independent all-zero measurement replay produced the same hashes.
At these checkpoints, an XOR change of basis cannot clear a wire while
preserving the existing state. A narrower schedule needs to change which
values cross the checkpoints or recompute some of them. Compare any such
schedule with the original unconditional carry and controlled-swap costs.
[Native rank witnesses](evidence/aggregate36-20261126/invsqrt-incumbent-rows-affine-rank.json)
