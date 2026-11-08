# Compact phase-accumulation screen

The comparison is the confirmed 150-qubit trimmed inverse-square-root control,
KMB SHA-256 `f4c8503d87c9e7cedb8a79a796e0b195623c2e88467691ca1b08af1a70fb200d`,
complete cost 472,336.9178780867. The compact tranche requires a model prediction
of at least 20% improvement, or cost at most 377,869.5343024694, before emission.

The pinned metric's allowed instruction list is branchwise basis-preserving:
it contains no Hadamard or other coherent superposition preparation, and the
verifier requires all non-input qubits to start and end at zero. A coherent
phase-gradient state therefore cannot be prepared or supplied as scratch
under this pinned contract. This restriction does not apply to other gate sets
or to an amended verifier contract.

An alternative direct construction uses the existing 38 fractional output
bits without a stored output register. It phases c0 directly and subtracts the
column-truncated outer Horner products, selected by the binary scale. Its
integer recurrence matches the trimmed control for all 3,133,452 inputs.
Two native controlled-phase slices implement one selected coefficient bit and
one selected bit product; they cost respectively one and two Toffoli-like gates
plus one fine rotation. They passed all control states with sampled measurement
branches and clean scratch. Scale-selector slices each cost eight Toffolis for
compute and uncompute.

The explicit per-term construction contains 308 coefficient terms and 1,859
product terms: 4,026 Toffolis and 2,161 fine rotations before selector, lookup,
inner arithmetic and cleanup. Even assuming only the mandatory 22 input qubits,
the largest possible full-domain margin, no other operations and no T charges,
the complete cost is at least 445,859.19694843923 for this construction. That
misses the 20% gate, so no full candidate was emitted. The bound is specific to
this per-term construction and does not rule out a different compact design.

Final source-bound receipts are `model-v2.json` and `price-v2.json` under
`docs/evidence/invsqrt-compact-phase-20261108/`; earlier receipts are retained.
The compact OpenSpec records this tested outcome and keeps unpriced component
and promotion work open. Three native/model tests, Ruff, Pyright with the pinned
Ubuntu interpreter and strict OpenSpec validation passed. No long verifier or
cloud job was started by this lane.
