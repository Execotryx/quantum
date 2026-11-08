## Control

The trimmed v5 component, KMB SHA-256
`f4c8503d87c9e7cedb8a79a796e0b195623c2e88467691ca1b08af1a70fb200d`:
150 qubits, 2,908 Toffoli-like gates (766 lookup, 56 unlookup, 1,568
Horner, 56 normalization flags, 160 input shift, 302 output shift), one
T-like gate, 35 fine rotations, cost 472,336.9178780867, worst tolerance
use 66.77%.
[Trimmed lane](../../../docs/invsqrt-trimmed-v4-08-11-2026-15-42-19.md)

## Transformation in `_load_table.walk`

For an internal node at `depth >= 1` with both children live:

```text
current                                    new (sibling_cnot=True)
x(bit)                                     x(bit)
init_and(control, bit, flag)  # c ∧ ¬b     init_and(control, bit, flag)   # c ∧ ¬b
walk(left, flag)                           x(bit)
del_and(control, bit, flag)                walk(left, flag)
x(bit)                                     cx(control, flag)              # c ∧ b
init_and(control, bit, flag)  # c ∧ b      walk(right, flag)
walk(right, flag)                          del_and(control, bit, flag)    # erases c ∧ b
del_and(control, bit, flag)
```

- `flag = c ∧ ¬b` XOR `c` equals `c ∧ b`. The final `del_and` therefore
  erases the value it expects, with `bit` restored.
- The prefix rule `(prefix + 1) << remaining <= first` prunes only left
  subtrees. A node whose left child is pruned keeps its current form: one
  `init_and(control, bit, flag)`, the right walk, one `del_and`.
- The root (`depth == 0`) uses `bit` itself as the control. It is unchanged.

Expected cost is one Toffoli-like gate per internal node with at least
one live child, about 383 for 384 rows.

## Transformation in `unlookup.py` walk

Apply the same rule to the repair walk over the high address bits. That
walk loops over `direction in (0, 1)` and calls `init_and` and `del_and`
per child. When both children are live, compute the AND once for
direction 0 (on the negated bit), restore the bit, apply
`cx(control, flag)`, walk direction 1, then `del_and`. Single-child nodes
are unchanged. The leaf phase operations (`cz` or `z` under measurement
conditions) are unchanged.

## Cost model

Change the lookup and unlookup formulas in `costmodel.py` to count one
AND per internal node with a live child when `sibling_cnot` is set.
Recalibrate against the 27 existing receipts (unchanged, flag off) and
the new v6 circuit (flag on). Require exact matches for declared width,
Toffoli-like count, T-like count and fine-rotation count.

## Verification

The polynomial arithmetic, coefficient table, normalization and phase
mapping are identical. The existing full-domain model receipt therefore
remains valid by hash. The circuit bytes are new, so every native gate
still applies.

1. Native lookup fixture: for all 384 valid addresses and the 128 pruned
   addresses, the flagged and unflagged walks XOR identical words into
   arbitrary nonzero targets, restore the address and path flags, and
   leave zero phase. Add a mutation that drops the `cx`. It must fail.
2. Native unlookup fixture: for every address, random measurement outcomes
   give identical repaired phases with and without the flag.
3. Component fixtures: the existing 31,232 trajectories across 7,806 inputs
   (segment edges, powers of four, both margin witnesses).
4. Two independent builds produce identical KMB bytes.
5. Full 200,540,928-trajectory verification, then a one-use fresh-salt
   confirmation on identical bytes. Both must report the same cost and
   66.77% worst tolerance use.
6. Paired archive with the v5 DQI and chemistry members retained by hash.

## Promotion

Measured cost at most 448,720.07 (5% below the control). Expected about
411,000. Width must stay at 150 or lower.
