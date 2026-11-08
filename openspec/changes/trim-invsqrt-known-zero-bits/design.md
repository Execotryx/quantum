## Control and development candidate

Control KMB SHA-256 is
`c487332fe965389191c8e6d34848d61c82748e5802c6e616eb0363869f92c4c9`.
Its verified coefficient table has maximum words 268,435,454, 524,275 and
6,084. They fit 28, 19 and 13 bits. The output register is reduced from 39
to 38 qubits; its integer bit must remain zero throughout the modeled shift.
The coefficient-table bytes, control trace, pre-emission price and source
hashes are recorded in `docs/evidence/invsqrt-trimmed-v4-20261108/freeze.json`.
This file is development freeze evidence, not a registration.

The exact model checks all 3,133,452 inputs, every accumulated row subtraction
and the final shifted high bit, and compares every resulting phase word against
the frozen control model. It does not by itself prove all quantum trajectories.
Native development fixtures separately check the emitted circuit, input and
scratch restoration and sampled measurement phases.

## Gates and evidence boundaries

Before a full verifier run, register a clean committed source revision,
unchanged freeze inputs, this candidate SHA, the pinned contract and backend,
and an at-least-5% complete-cost gain versus 509,471.48180735623. Require
zero full-domain failures and at most 90% tolerance use. Record the original
200,540,928-trajectory official verifier receipt separately from a fresh,
independent one-use confirmation receipt, both bound to identical KMB bytes.
Preserve salts, coverage counts, costs and the input artifact hashes.

A paired archive successor must retain DQI, chemistry circuits and chemistry NPZ
by their certified parent hashes, run the official extracted-archive metric and
reconcile retained costs. Neither the earlier v4 confirmation nor native
fixtures substitute for a fresh confirmation of this new KMB.
