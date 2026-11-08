# Calibrated direct inverse-square-root resource model

Added a non-emitting model for the pinned uniform dyadic direct circuit. It
prices coefficient lookup and unlookup separately, each Horner stage,
normalization flags, input/output shifts, declared peak width, T/fine rotations
and the margin-dependent complete cost. The formulas use the pinned uncapped
native allocator and primitive behavior. The model supports n_p=10, segment
bits 5–7 and polynomial degrees 2–4; other layouts are rejected. It does not
prove coefficient accuracy, quantum phase correctness or the zero-bit invariant
required by the trimmed layout. Unseen precision settings are extrapolations.

The [final calibration receipt](evidence/invsqrt-costmodel-20261108/calibration-final-v3.json)
records hashes
and residuals for 27 scored, comparable v1, v2, v3, v4 and trimmed circuit
receipts. All 27 match declared width, Toffoli-like count, T-like count and fine
rotation count exactly. Reference Newton circuits and unscored failed lanes do
not provide comparable direct-circuit counts and are excluded, not silently
considered successful. The trimmed control decomposes into 766 lookup, 56
unlookup, 1,568 Horner, 56 normalization-flag, 160 input-shift and 302
output-shift Toffoli-like gates, totaling 2,908.

As a model-only follow-on, the searched 28/20/13 table has no full-domain phase
failures, and all coefficient words fit the proposed trimmed widths. The
calibrated formula projects 149 qubits and cost 469,072.40, only 0.691% below
the confirmed 472,336.92 trimmed control. This fails the 5% cost gate. No
circuit was emitted; intermediate zero-bit invariants, measurement phases and
native parity remain unproved. Its separate table and screen receipts are in
the same evidence directory.

Eight receipt-based tests, Ruff and Pyright with the pinned Ubuntu interpreter
passed; the refinement OpenSpec validates strictly. No long verifier job was
started and no frozen trimmed source or existing published receipt was changed.
Review tightened the trimmed-layout guard to require the same lookup-reuse
setting as the actual trimmed builder. The separately retained
`calibration-final-v2.json` and `28-20-13-screen-v2.json` supersede the earlier
calibration and screen receipts; all 27 residuals and the 0.691% conclusion
are unchanged. The earlier receipts remain intact with their original source
hashes.
