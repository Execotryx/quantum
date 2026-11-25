# D4 unit-tail cost reduction

## Initialized first pivot

At the first forward pair, and during the raw scalar gauge replay,
the denominator is the initialized unit. The first head's products
are therefore register additions. The collapsed preparation adds
only a controlled constant to the numerator and derivative. In
the inverse of a raw first pair, the second denominator is
`q+h1*N`. After removing q, the circuit measures and erases the
product using the two live operands for phase repayment, then
initializes the unit again.

The other reverse pass starts with the normalized jet. Reversing
its first pair leaves a reciprocal gauge in the denominator.
The first-head terms are proportional to that denominator or its
square, so the circuit commutes them through division by those
same factors. The numerator and derivative additions then use
the unit formulas. This preserves the original normalization token
and avoids both first-head multiplications in that pass.

## Degree certificate and scratch reuse

The tight synthesis reconstructs the projected evaluator E and
denominator D. With the caught collapsed-fold top slot zero, the
physical banks contain the exact coefficients of the unit-tail
image. The original numerator is `N=q0*E+h0*D`. Its possible
highest coefficient, at degree 33, is the top E term plus the
first-head slope times the top D term. Checking that coefficient
gives `deg(N)<=32` and the D bank gives `deg(D)<=32`.
The external-node product has degree 68. The cross product with
the original degree-bounded pair has degree at most 67, so
divisibility by the external-node product forces equality.
This proves the unit tail up to scale without consulting the
scalar jet. The live check also requires the original chart
pattern and the middle collapse layout bit.

The inverse normalizer returns two field norms. The circuit
erases the reciprocal norm using the still-live reciprocal gauge
and holds the other norm's measurement mask classically. It
repays that mask from the recovered raw gauge and recomputes
both norms there. It pays more gates to reduce the high-water
mark during replay. Collapse masking also uses one base-field
half at a time. In synthesis, the quotient-field operand is a
linear combination of U. The absorber exposes it in U's
constant and linear slots instead of allocating a second extension
word, and restores both coefficient slots before returning.

## Cost screen

The first-pivot optimization with inverse normalization lowered
the degree-31 linked run from roughly 438,300 to 425,700 executed
gates at 945 qubits. The live degree certificate replaced the two
6,531-static-gate scalar checks with 184 additional static gates
at each synthesis boundary. This reduced the executed mean to
about 413,100 before the norm-memory tradeoff.

With norm replay and absorber aliasing, the local linked probe
used 922 declared qubits and roughly 415,500 executed gates.
The reference budget at that width and minimum repetition factor
is about 407,776 gates. This reduces the gap to about 7,800
gates per shot. Forward extraction now sets the high-water mark
at 922 qubits. The cumulative width stays at 922 through synthesis,
conversion, scan, and reversal. The linked probe remains fixed to
the captured degree and chart topology.

A static screen of admitted degree-31 converter schedules found
104,810 gates at threshold five versus 104,834 at threshold seven.
Higher thresholds and the root-fusion, direct, and truncated
variants were more expensive. A 24-gate difference alone does
not justify retuning the deployed converter.

## Cloud replay

The staged Linux run passed all 10 selected tests in 123.95 seconds,
with 37 deselected. It included the compact jet transports, native
affine extraction and replay, compact layout sharing, and the full
captured degree-31 path. The full case reproduced 922 qubits and
415,475.5 and 415,535.5 mean executed gates at seeds 715 and 716.
The corresponding boundary checks averaged 94,184.5 gates each.

The [run log](evidence/d4-compact-repair-20261115/cloud-unit-tail-optimized/run.log)
records the test results. The [stage checksums](evidence/d4-compact-repair-20261115/cloud-unit-tail-optimized/stage.sha256)
bind the source and launcher. The downloaded
[receipt archive checksum](evidence/d4-compact-repair-20261115/cloud-unit-tail-optimized/receipt-archive.sha256)
matched the remote checksum before extraction.
An independent Compute Engine query confirmed the
[VM was terminated](evidence/d4-compact-repair-20261115/cloud-unit-tail-optimized/vm-stop.json)
after the stop command lost its connection.
