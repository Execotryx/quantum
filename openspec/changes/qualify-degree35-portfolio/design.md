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

The divider checkpoint at line 5,856 has eight clean wires after 320
Toffoli-like gates. The tested 8-bit and 13-bit table-addressed affine
families fail exact mixed-difference witnesses. At 39 qubits the joined
prefix, `X q28` bridge, and retained return use 627.25 executed
Toffoli-like gates in a full-domain zero-phase replay. At the incumbent
rotation price this gives the replacement 467.07 charged equivalents.
Scope follow-up screens to a new address or joint function of the
remainder and quotient. Verify the new phase and price its complete
emitted circuit before selecting it for the aggregate campaign.
[Checkpoint phase screen](../../../docs/degree35-invsqrt-checkpoint-phase-27-11-2026-03-16-43.md)
· [Measured checkpoint return](../../../docs/degree35-invsqrt-checkpoint-return-27-11-2026-03-24-19.md)

A joint fixed-point model restores numerical accuracy at the registered
cut. It uses a root-dependent intercept, a scaled 19-wire word and a
scaled square of its registered 10-bit remainder proxy. Freeze the
three-coefficient table as the numerical control. Screen reduced
precision across all inputs, then prototype coefficient access and
arithmetic in the eight clean checkpoint wires. Use the measured return
and complete rotation cost before proceeding to aggregate verification.
[Passing joint checkpoint model](../../../docs/degree35-invsqrt-checkpoint-joint-27-11-2026-03-35-49.md)

The 28-bit staged factorization uses six parity constants and 128
reciprocal rows. It passes the complete numerical phase screen and
bounds the signed numerator correction to 21 bits. The 37-qubit direct
reciprocal probe costs 126 Toffolis and 128 rotations. The 39-qubit
two-bit streaming probe costs 3,528 Toffolis with 28 rotations. Both
fail the complete budget. Evaluate a recurrence or another shared
loading layout and include the numerator and exponent routing.
[Precision and reciprocal lookup trial](../../../docs/degree35-invsqrt-checkpoint-precision-27-11-2026-03-48-23.md)

## Joint component cost screen

Recalculate each component's cost budget from the measured candidate
companions and the inclusive score-35 product. With inverse square root
at 58,000 and chemistry at 230M, the DQI cap is 297.777B, or 308,769 mean
gates at 888 declared qubits and eight failures in a full draw. This is
a development allocation. Check observed counts and the repetition
factor on each verification role. At 405 chemistry task qubits and the
v221 effective normalization, 230M permits 2,802 ANGLE gates per pass.
The verified v221 assembly still uses 3,306. Prioritize changes that can
close a demonstrated resource gap on serialized components.
[Joint budgets and catalog comparison](../../../docs/degree35-joint-cost-screen-27-11-2026-04-37-37.md)

The six-bit fixed-weight screens fail the decoded accuracy gate. The
fixed-projector span diagnostic puts all three tested tables above the
two-body tolerance even after relaxing the weights. The seven-bit ten-word
layout emits 5,046 static ANGLE gates per pass, above its 2,321-gate budget.
For a new seven-bit loader, identify angles acting on two zero orbital
coordinates and check the resulting vectors and decoded residuals before
pricing affected transitions. For the 884-qubit DQI projection at the
reported companion targets, one failure already reduces the score below 35.
[Cloud precision and loader screens](../../../docs/degree35-chemistry-precision-and-joint-margin-27-11-2026-05-00-22.md)

The cloud zero-angle screen finds 2,400 free words and preserves decoded
accuracy in three assignments. The original has lower mixed rank in the
aggregate. For the final five-word packet, screen deletion of an emitted
product by solving the constrained output truth columns over GF(2) with
the cache and carrier endpoints fixed. A feasible deletion needs native
replay and a lower cost than the corresponding v221 slot. An interior
packet must price the two transitions sharing its changed word table.
[Zero-angle research and exact deletion design](../../../docs/degree35-zero-angle-loader-research-27-11-2026-05-12-36.md)

The completed terminal-slot cloud screen finds all 124 independent
products indispensable under the frozen product dictionary, including
when arbitrary pure high- and low-address corrections are allowed.
Any follow-up loader candidate needs new product controls or a new cache
or packet layout and separate native pricing.
[Exact terminal deletion result](../../../docs/degree35-terminal-loader-deletion-27-11-2026-05-21-26.md)

For the source DQI decoder return, screen product pairs in stretches split
by phase, measurement, and guarded operations. Use the same transported
output direction and require rank two for the combined polar matrix.
The static pair upper bound is 51,524 before control and direction checks.
Price only replacements verified on matched execution. The joint 900-qubit
allocation needs about 7,529 fewer whole-decoder gates at zero failures.
[DQI return fusion research](../../../docs/degree35-dqi-return-fusion-research-27-11-2026-05-25-09.md)

The cloud replay tightens the same-direction ceiling to 135 pairs and the
compatible pair ceiling to zero. Equal control planes on different output
directions also give zero pairs. Repeated-direction groups contain at most
405 CCXs under these boundaries. Continue at a larger structural boundary
with a phase proof or choose a different arithmetic construction.
[Cloud affine transport screen](../../../docs/degree35-dqi-return-fusion-screen-27-11-2026-05-32-47.md)

## Verification and delivery

Register a `portfolio-v5` archive with `--at-least-35` after qualifying a full
decoder. Use the existing shape-derived coverage, independent source and
build bindings, and separate metric and confirmation salts. Audit both
fresh extractions and accept an exact cost product at or below the ceiling. Deliver
the verified archive on drive E and report complete cost and score
comparisons with the earlier cloud and certified results in the README.
