## Control and exchange rate

The control is the combined v3 circuit, KMB SHA-256
`ce8a58b65ee2d89457de655565a22b68ffc2d7dc68befc764a99410b3285f5b4`:
159 declared qubits, 3,202 Toffoli-like gates, one T-like gate, 36 fine
rotations, cost 548,860.9216547348, worst tolerance use 71.96%.
[v3 attempt record](../../../docs/evidence/advance-hybrid-20261108/invsqrt/attempt-combined-v3.json)

The rotation-inclusive per-qubit cost is `C = 548,860.92 / 159 = 3,451.96`.
Removing `dQ` qubits saves `dQ × C`. Adding `dT` Toffoli-like gates costs
`Q × dT`. A width change pays when it adds fewer than
`C / Q = 21.7` Toffoli-like gates per removed qubit. Recompute the rate
from the current control before each decision.

## What the existing samples already show

The four boundary samples equal exact register sums. That points away
from H1.

| Sample | Reported | Register sum |
| --- | ---: | --- |
| `lookup` | 109 | x 22 + count 4 + output 40 + c1 21 + c2 14 + path 8 |
| `arithmetic` | 131 | path freed, scratch 30 allocated |
| `phase` | 131 | unchanged |
| `after_unlookup` | 101 | scratch freed; x, count, output, c1, c2 remain |

The input register is counted, and the samples are complete at their
boundaries. The missing 28 qubits are therefore most likely live inside
a primitive that runs at the 131-qubit level: the controlled row additions
in the Horner stages, `_binary_shift`, or `_phase_by_bits`. The 30-qubit
`scratch` is passed into `_add_row`. Whether it holds a control-gated
operand copy or the carry chain must be read from the pinned primitive.

## Stage A — trace liveness

1. Add `src/qcompile/liveness.py` with `LivenessBuilder`, a proxy around
   `km.CircuitBuilder`. After every delegated call it records
   `num_allocated_qubits`, the call path (the stack of `qcompile` and
   pinned-primitive frames), and the allocation sites live at that moment.
   Its output is a JSON trace with the peak, the call path at the peak, and
   the live allocations grouped by site and width. Emitted bytes must equal
   the unproxied build. Check this by SHA-256.
2. Add an op-stream analysis of the serialized circuit. Read the KMB with
   the pinned reader. If the circuit object exposes its operations,
   iterate them directly. Otherwise round-trip through KMX text. For each
   qubit id, record first use, last use and reset points (`R`, `HMR`).
   Report the declared count, `max id + 1`, the number of distinct ids, and
   the maximum overlap of live intervals.
3. Build two tiny counting fixtures: dense ids `0..k-1`, and the same
   circuit with one id raised to 100. Record `num_qubits` for each. This
   establishes whether the declared width is a high-water mark, `max id + 1`
   or a distinct-id count.
4. Read `_add_row`, `iadd`, `isub`, `_phase_by_bits` and the builder's
   `left_rotate`/`right_rotate` in the pinned reference module. Record each
   one's internal allocations, their widths and lifetimes.

## Stage B — decision

| Measured result | Cause | Next step |
| --- | --- | --- |
| Interval overlap ≈ 131 and declared 159 | H1, id reuse or counting | Stage C1 remap |
| Traced peak ≈ 159 inside a primitive | H2, transient workspace | Stage C2 arithmetic |
| Both partially | Mixed | C1 first, then C2 on the remainder |

Record the decision with the trace hashes before writing either fix.

## Stage C1 — semantics-preserving remap (only under H1)

Rewrite ids by greedy left-endpoint interval colouring. Width then equals
the maximum interval overlap.

- Keep the `x` register's ids, order and name.
- Assume every non-interface qubit starts in |0⟩. The verifier also
  requires it to end in |0⟩ on every trajectory. With no operation after
  its last use, its state after that point is |0⟩. Handing the id to a
  later interval is therefore safe.
- Split an interval only at `R` or `HMR`, where the state is known to be |0⟩.
- Leave classical bit ids, conditions and operation order unchanged.
- Prefer re-emission through a builder allocation policy when the
  wasted ids come from this project's allocation order. Use the KMX
  rewrite only for ids allocated inside pinned primitives.

## Stage C2 — width-aware arithmetic (only under H2)

Price every candidate with emitted counts and the exchange rate. Emit a
circuit only if the model predicts at least 5% lower complete cost.

| Candidate | Idea | Expected effect |
| --- | --- | --- |
| C2a, gated operand on the fly | Do not materialize `control ∧ operand` across the row. Form each gated bit as a temporary AND when the carry step needs it, then erase it by measurement. | Removes up to the operand-copy width (about 30 qubits). Adds about 0 Toffolis if the current row already pays one AND per operand bit. |
| C2b, conditionally clean carries | Use conditionally clean ancillae (Khattar and Gidney, Quantum 9, 1752) so the carry chain needs fewer clean qubits. | Removes part of the carry chain for a few extra Toffolis per row. |
| C2c, borrowed dirty carries | Borrow qubits that are idle during a row, named by the tracer, as dirty carry workspace (Häner, Roetteler and Svore, arXiv:1611.07995). | Zero new qubits, about twice the Toffolis on borrowed bits. Usually fails the 21.7 rate. |
| C2d, ripple adder with one ancilla | Cuccaro-style adder. | About 2n Toffolis per row. Expected to fail the rate at n ≈ 30. Keep it as a priced control only. |

There are 52 controlled rows per evaluation (13 bits of `t`, 2 Horner
stages, forward and reverse). Removing 29 qubits pays for at most
`29 × 21.7 / 52 ≈ 12` extra Toffolis per row. C2a is the first
candidate. The others run only if C2a fails its proof or its model.

Model each candidate in the existing exhaustive integer model if it
changes truncation or rounding. Row reordering alone does not.

## Stage D — tracer on other components

Run the tracer on the reference DQI circuit (1,893 declared; the source
paper reports 1,885 logical qubits) and on the nine banked ANGLE circuits.
DQI cost scales with the square of its width, so each removed DQI qubit
is worth about 0.1%. Report findings only. Apply DQI fixes inside
`build-routed-bm-dqi-decoder`.

## Promotion

- C1 remap: at least 2% lower measured cost. The circuit's semantics are
  unchanged and verification is exhaustive, so the 10% lane gate does
  not apply.
- C2 arithmetic: at least 5% lower measured cost than the control, zero
  failures over all 3,133,452 inputs, and at most 90% tolerance use.
- Both: native fixtures at powers of four, segment edges and the recorded
  worst witnesses. Then a full 200,540,928-trajectory pass and a fresh
  one-use confirmation on the same bytes, followed by a paired archive
  run that retains the DQI and chemistry members by hash.

| Outcome | Qubits | Projected cost | invsqrt ratio | Aggregate factor |
| --- | ---: | ---: | ---: | ---: |
| H1, full remap | 131 | ≈452,200 | ≈4.59× | ×1.067 |
| H2, C2a removes 29 qubits at +0 Toffolis | 130 | ≈448,800 | ≈4.63× | ×1.069 |
| H2, C2a removes 29 qubits at +10% Toffolis | 130 | ≈490,400 | ≈4.23× | ×1.038 |
