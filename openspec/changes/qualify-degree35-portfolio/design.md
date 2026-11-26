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

The fused row-add comparison reduced precision to one retained guard
per product and separated the outer correction from the constant.
Borrowing the carry reduced the best arithmetic-only cost product
to 103 times 2,660. A
competing schedule needs a different multiplier, phase construction,
or companion allocation before a complete verifier run.
[Native arithmetic comparison](../../../docs/degree35-invsqrt-borrowed-carry-27-11-2026-01-57-09.md)

Controlled add/subtract rows with a fixed half-row correction reduce
the measured arithmetic-only product to 107 times 1,696. Their
one-guard phase model passes the full legal domain. Direct unwrapped
parity rotations and two additive tables fail the scoped resource
screens. For a complete incumbent-based rewrite, measure live width
and the unconditional carry and routing cost together. At 35 qubits
the single-component budget is about 1,489 charged equivalents per
input compared with about 1,582 at the source control. Removing the
estimated 61.87 classically guarded gates alone would leave a gap.
The native replay splits the control at its first and last fine rotations
into 611, 71, and 657.88 mean Toffoli-like gates. Bind the corresponding
forward and inverse addition rows to explicit signed update contracts
before estimating a Litinski-style substitution. A one-third reduction
at the existing width requires about 737 eligible gates across both paths.
[Signed-digit measurements and phase screens](../../../docs/degree35-invsqrt-signed-digits-27-11-2026-02-13-17.md)

The incumbent carries 629 unconditional one-Toffoli majority cells and
149 unconditional controlled swaps. At 39 qubits a one-third saving
limited to the remaining gates cannot close the gap. The exact source
splice verifies twelve existing add/subtract rows and their preserved
sign frames. The borrowed-carry versions add 72 Toffolis and leave the
peak at 39 qubits. Compare new schedules at the live-width peaks in
the phasing cleanup before a complete cloud campaign. Native witnesses
have affine rank 39 at source lines 5,948, 9,871, and 10,438, so test
changes to which values are retained or recomputed across those cuts.
[Incumbent carry census and source replay](../../../docs/degree35-invsqrt-incumbent-rows-27-11-2026-02-25-56.md)

A native `q19` loan demonstrates reuse of a nonlinear value through one
rotation and its measurement repayment. The complete circuit still
requires 39 qubits. For the next width comparison, account for all peak
windows in one schedule and measure the total recomputation charge.
[Rotation-loan comparison](../../../docs/degree35-invsqrt-rotation-loan-27-11-2026-02-52-43.md)

Single-product recomputation at idle endpoints covers up to 1,065 of
4,221 symbolic peak sites under the registered interval screen. The
best disjoint selection at 46 extra Toffolis covers 727 sites and
emits 39 qubits. Retarget the source carry and routing layout across
peak sites outside these intervals before assembling a cloud candidate.
[Idle-wire recomputation screen](../../../docs/degree35-invsqrt-idle-recompute-27-11-2026-03-10-19.md)

## Verification and delivery

Register a `portfolio-v5` archive with `--at-least-35` after qualifying a full
decoder. Use the existing shape-derived coverage, independent source and
build bindings, and separate metric and confirmation salts. Audit both
fresh extractions and accept an exact cost product at or below the ceiling. Deliver
the verified archive on drive E and report complete cost and score
comparisons with the earlier cloud and certified results in the README.
