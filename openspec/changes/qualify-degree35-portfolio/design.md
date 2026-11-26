## Controls and budget

Use Tony Li's twice-rebuilt 900-qubit DQI as the complete decoder control.
Use prvsiyan's inverse-square-root and goodpjw2008's v26 chemistry for the
published performance ceiling. Evaluate the source-backed ceiling with
Tony Li's 39-qubit inverse-square-root circuit and the source-built goodpjw2008
v20 chemistry family measured by Acceleratorer. Keep the chemistry NPZ and
loader records paired. Independently rebuild any family selected for release.
[Open circuit shortlist](../../../docs/aggregate-above-36-open-circuit-shortlist-26-11-2026-22-34-04.md)

The inclusive score-35 cost-product ceiling is about `3.9723446102471964e24`.
At 888 qubits and zero failures, the published and source-backed companion
costs permit about 278,593.94 and 274,327.64 mean DQI gates, respectively.
Use the role's measured failure counts for its actual repetition factor.
The supplied-tape circuit uses 248,941 native Toffoli-like gates with
measurement-assisted inner reciprocal cleanup. This leaves about 25,387
gates with the source-backed companions for raw-syndrome extraction and
exceptional-chart recovery.
The two measured suffix transforms exceed that allowance together.
[Degree-35 budget and hashes](../../../docs/evidence/aggregate36-20261126/degree35-above35-controls.json)
· [Optimized native handoff](../../../docs/evidence/aggregate36-20261126/degree35-subtower-phase-native.json)

The regular blocked extractor now constructs both prefix summaries on
the same wires from the raw syndrome. At 891 qubits its nine-pair block
alone costs 109,428 gates per direction. This excludes a serial
composition of that block with the current supplied-tape phase within
the selected companions' 35-point allocation.
[Raw block results](../../../docs/degree35-blocked-extraction-27-11-2026-01-15-15.md)

At the measured public portfolio costs, a single-component change
needs a 14.61% cost reduction. The DQI width-only break-even is below
its 840 input qubits. At fixed seven-bit chemistry precision and
factorization, the heuristic uses 370 qubits before any persistent
angle words. Both limits support screening gate count as well as
width on complete components.
[Chemistry replay and exact cost limits](../../../docs/degree35-chemistry-affine-27-11-2026-01-27-18.md)

## Inverse-square-root source screen

Freeze the native 39-qubit control and the passing 192-interval
quadratic model. Price two dependent product stages with the
coefficient and local-input lifetimes visible. Keep the first
product's signed rounding and the original input reconstruction.
Compare a fused or streamed lookup against the measured joint and
three-pass layouts at its actual declared width. Include exponent
alignment, phase repairs, uncomputation and the final rotation
charge before selecting a complete candidate. With the source
companion costs, the single-component cutoff is about 52,119.68.
[Source research and measured slices](../../../docs/degree35-invsqrt-source-research-27-11-2026-01-39-29.md)

## Verification and delivery

Register a `portfolio-v5` archive with `--at-least-35` after qualifying a full
decoder. Use the existing shape-derived coverage, independent source and
build bindings, and separate metric and confirmation salts. Audit both
fresh extractions and accept an exact cost product at or below the ceiling. Deliver
the verified archive on drive E and report complete cost and score
comparisons with the earlier cloud and certified results in the README.
