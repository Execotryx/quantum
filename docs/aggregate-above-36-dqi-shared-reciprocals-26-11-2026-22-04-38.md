# Shared reciprocals in the degree-35 derivative action

Let the current modulus and divisor leading words be `a` and `d`. Store
the top payload word `u` as `u/a` at entry. The packed slope `a/d` then
gives the original reduction quotient `u/d`. After the reduction, divide
the child's top word by `d`, which is its modulus lead, using the same
reciprocal. In the reverse traversal restore that child word before
undoing the reduction.

The extension can add its dot product directly to the stored `u/a`.
It divides that sum by `d` inside the reciprocal already needed to
restore the polynomial remainder. This shares two reciprocal calls per
non-leaf frame. The rotation still follows the final division. The
zero-head guard continues to use the preserved polynomial predicates.
Rejected inputs independently restore their payload, even when the
new intermediate payload differs on a zero slope.

| Supplied-tape composition | Earlier | Shared reciprocals |
| --- | ---: | ---: |
| First-fit software qubits | 888 | 888 |
| Explicit ANDs | 269,259 | 256,203 |
| Equality calls before lowering | 330 | 202 |

The change saves **13,056 explicit ANDs** and **128 equality calls**.
The full-position replay checks 12 regular and two nonregular genuine
degree-35 charts across both orientations. A separate direct polynomial
oracle checks residues and round trips at degrees 3, 5, and 35, including
a forced monomial locator for zero-head restoration. The E-drive WSL
probe remained pending. [New software receipt](evidence/aggregate36-20261126/dqi-shared-reciprocals-phase.json)
· [Earlier software receipt](evidence/aggregate36-20261126/dqi-projective-continuant-phase.json)

The phase and fold exceed the strict **256,016.70-gate** allowance by
**186.30** at the measured public companion costs before any native
equality lowering. Under the 280,000-gate planning figure they leave **23,797**
before comparisons, quotient generation and nonregular recovery.
The measured supplied-summary suffix by itself needs **70,476** products
round trip. A different raw-syndrome extraction or better companion costs
are still necessary before full cloud pricing.
[Public-companion ceilings](aggregate-above-36-public-frontier-26-11-2026-17-01-05.md)
