# Full-size routed DQI circuit build

The cloud emitter rechecked the registered depth decision and built the
routed decoder at dimensions `(4095, 70)` with history depth two. The
pinned register validator accepted the emitted circuit. The serialized
artifact has 1,942 qubits, 49,147 classical bits, and 617,235,589 bytes.
The build took 3,280 seconds of wall time while the VM also ran v6
confirmation and chemistry polish.

The KMB SHA-256 is
`d41de9ee484c18f91245cdb131fe765d638f06bdae955cdb5b2079bbf8c1f090`.
The matched 2,560-trajectory comparison is registered against the exact
retained v5 DQI bytes. The remaining VM time fell below the launch guard.
Full-size correctness and cost are pending that comparison.

[Emission receipt](evidence/review-fixes-cloud-20261108/dqi-depth/emission.json) ·
[Depth decision](dqi-depth-cloud-08-11-2026-23-50-00.md)
