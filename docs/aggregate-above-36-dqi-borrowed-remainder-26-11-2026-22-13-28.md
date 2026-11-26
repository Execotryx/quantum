# Borrowed interpolation for the degree-35 DQI remainder

The outer monic Euclidean remainder has a linear quotient. Its temporary
slope is the live divisor reciprocal, and its constant already occupies a
coefficient slot. When the constant has interpolation weight one, XOR the
weighted slope into that slot, multiply the evaluated operands directly
into the outputs, and XOR the slope back. This uses one temporary field
word for the other evaluated operand. It fits alongside the live inverse
and leaves the existing scalar schedule available at smaller sizes.

The degree-35 outer remainder uses 17 rank-42 field products per visit,
down from 31. It is visited four times in the complete supplied-tape phase
and inverse. The software replay across 4,095 positions used 888 qubits
and **253,851 explicit ANDs**, down from **256,203**. Both versions use
202 equality calls before lowering. The replay checks both orientations,
12 regular and two nonregular charts, every input register, and scratch.
The direct residue oracle also checks degrees 3, 5, and 35.
[New replay](evidence/aggregate36-20261126/dqi-borrowed-remainder-phase.json)
· [Previous replay](evidence/aggregate36-20261126/dqi-shared-reciprocals-phase.json)

The existing exact root scan uses 11 ANDs per 12-bit zero test before
orientation and guard controls. As an alternative, Astra 6.2 examined
contracting a classical mask polynomial with the syndrome. For distinct
roots of a monic locator `L`, the sum of `F(r)/L'(r)` is the coefficient of
`x^(degree(L)-1)` in `F mod L`. Set `F` to the evaluator times the mask
polynomial in the matching locator coordinates. This equality avoids a
derivative inverse algebraically, but streaming the 4,025 extra moments
at full degree would take 140,875 field multiply-accumulates forward, or
about 5.92 million rank-42 gates.

The supplied moments are `S_j = sum(e*x^j)` for `j=1..70`. A phase that is
linear in those words can implement only masks of the form `x*P(x)` with
`degree(P)<=69` in trace-dual coordinates. To see this, test a single
error at each field point with arbitrary amplitude and apply the
nondegenerate trace pairing. The legal mask `x^71` agrees with every such
low-degree mask at at most 70 nonzero positions, by the root bound on
`x^70-P(x)`. This rules out a universal linear phase with a sparse
position correction. A trace-based replacement would need a compact
scalar contraction with the reduced mask polynomial.
[Moment convention](../src/qcompile/dqi/decoder.py)
· [Trace-dual field basis](../src/qcompile/dqi/tower.py)

The borrowed-remainder circuit leaves at most **2,165.70 gates** under
the zero-failure, 888-qubit ceiling with the measured public companion
costs. Native comparisons, quotient extraction from raw syndromes, and
nonregular recovery all have to fit in the complete circuit. The E-drive
WSL execution probe is still pending. The full cloud comparison remains
**33.20483975**. [Gate ceilings](aggregate-above-36-public-frontier-26-11-2026-17-01-05.md)
