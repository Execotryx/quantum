# Quantum and classical ownership for adaptive64 integration

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

The model retains Q889. A fresh full emitted tape, not this document, establishes
its actual quantum width. All prior arithmetic and point-cell quantum helpers
remain unchanged. The adaptive selector, mask maps and compensation allocate no
qubits. The extra point uses the same sequential ten-helper scan ladder.

The selector explicitly owns at most322 classical bits. Only a separate
12-bit virtual-pivot word survives into the decoder, and it is explicitly
cleared and freed on closing. The unchanged point cell can allocate one native
classical scratch bit not exposed through the explicit alloc_bits/free tracker.
The corrected standalone gauge panels therefore serialize49462 classical bits;
the transport/scan panel serializes49463, with exact phase boundaries checked.
Its conditional point-cell explicit live peak is24 bits including the pivot.
These standalone counts are not a whole-decoder classical-bit prediction.

The matched191/195 calls still require24 caller-owned clean carry-bank bits and
up to24 additional helpers. Quotient62 still requires22 helpers. The other
engineer's width route remains independent; this source makes no Q877 claim.
Any width merge requires a new lifetime proof and full requalification.
