# Berlekamp–Massey decoder comparison for score 35

Gu, Kemeny, Yelin, and Lukin published a Reed–Solomon decoder for the same
code dimensions with **442,397 Toffolis** and **1,837 peak live qubits** in
their evaluator. Its published task uses a fixed phase mask. Our verifier
supplies an independent 12-bit mask word at each position on each shot.
The published circuit also allows rare locator-window and history overflow
failures. Any port would pay the local failure-dependent repetition charge.
[Published result](https://raw.githubusercontent.com/andigu/uncompute/main/tasks/dqi-reed-solomon/results.jsonl)
· [Published task](https://github.com/andigu/uncompute/tree/main/tasks/dqi-reed-solomon)
· [Verifier contract](../contracts/contract.json)

The published schedule journals the arithmetic and recovers discrepancy
words from the live locator when a replace round stores their inverses.
Other rounds may need a tagged stack. The published forward and backward
Berlekamp–Massey passes together use **227,247 Toffolis**. The stage replay
of the current 900-qubit source measures **197,541.50 mean Toffolis** across
its first quantum decoder stage and return. The two boundaries cover
different intermediate representations. At 900 qubits, the published
rounds alone would leave **81,355** of the joint budget's **308,602** gates
for every other stage if their gate count carried over. Their reported
width is already above that allocation's 900 qubits. A direct port has
no supported resource advantage.
[Round schedule and cleanup](https://andigu.github.io/projects/uncompute/dqi-reed-solomon.html)
· [Source stage replay](evidence/aggregate36-20261126/dqi-source-stage-boundaries.json)
· [Joint cost screen](degree35-joint-cost-screen-27-11-2026-04-37-37.md)

The published scan subtracts a syndrome-linear phase and removes 71
positions with zero residual coefficient for its fixed mask. For a
runtime mask, 70 fixed nonzero evaluation points give a unique degree-69
interpolant after factoring out the first power of the evaluation point.
This guarantees 70 removed positions if the linear phase is applied with
the current classical mask. At any additional point the residual remains
uniform because it includes that position's independent mask word with
coefficient one. On the published 23-Toffoli point body this would remove
**1,610** charged gates before pricing the linear phase. The source
decoder already sorts 4,024 residuals to select a modal coefficient and
uses a different root phase stage. The 1,610 figure is a gross saving
relative to the published decoder's untrimmed point body. The incremental
cost against the source control needs a separate map.
The smallest transferable idea is discrepancy recovery from a live word
whose inverse is already available. It needs an exact emitter mapping and
a count of eliminated operations per direction before a native cloud run.
[Published phase and position scan](https://andigu.github.io/projects/uncompute/dqi-reed-solomon.html)
· [Existing runtime-mask scan](aggregate-above-36-dqi-residue-scan-26-11-2026-07-46-21.md)

The published MBUndo interval method offers a separate screen for the
current source. For a disposable word that equals a field product, an
X-basis measurement leaves a phase determined by the parity of the
measured bits dotted with that product. If both input words are live
and restored, the parity is a binary quadratic function in their bits.
Classically conditioned Clifford phases can repay it directly. Charge
any reconstruction required to recover the input operands at the
correction point. A 42-product inverse multiplication with zero such
reconstruction would save 42 Toffolis, so the joint target would need at
least **180** equivalent clean removals on a mean trajectory. The flat
return stream has yet to establish that many qualifying lifetimes or
any isolated eligible slice. A replacement needs the exact last uses,
the preserved factor coordinates, and a proof that every earlier
measurement guard and live output behaves identically.
[MBUndo interval analysis](https://arxiv.org/html/2611.02345v1#S4.SS2)
· [Native field multiplier audit](dqi-multiplier-audit-15-11-2026-15-21-00.md)
· [Existing measurement-based product erasure](../src/qcompile/dqi/bilinear.py)
