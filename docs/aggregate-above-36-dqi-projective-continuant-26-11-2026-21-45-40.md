# Projective DQI locator fold

Keep the denominator and numerator in a shared projective scale. Each
pair of supplied quotient coefficients updates the pair from `(D,N)` to
`((a*z+b)*D+N,D)`. The lower coefficients use a truncated product. Only
the two new highest coefficients need to be scaled by the previous
denominator head. The inverse restores the quotient tape and clears
the extra word initially set to one.

Each rank-one output of a field multiplication can apply the interpolation
weights directly to the destination coefficients. On a dirty-target
product replay this reduced scratch from **39 to 27 qubits**, with the
same **714 controlled products**. The direct output adds linear gate
fanout. Scalar inversion borrows the six-bit norm for the inner change
of basis and restores it before uncomputing the outer norm.

| Degree | First-fit qubits | Controlled products per direction |
| --- | ---: | ---: |
| 1 | 36 | 0 |
| 5 | 165 | 1,866 |
| 35 | 885 | 37,596 |

Each degree used 12 random regular quotient tapes and 12 tapes derived from
valid syndromes. The replay checked the exact projective coefficients and
compared their normalization with the classical locator and evaluator. The
inverse restored all input registers, scratch, and the initial phase.
[Degree 35 software receipt](evidence/aggregate36-20261126/dqi-projective-continuant-35.json)

The earlier monic fold had a **76,440-product** lower bound per direction.
With the new fold and its inverse, the guarded phase design has **7,861
products** left under the 280,000-gate planning figure before equality
lowering, normalization, quotient extraction, and exceptional routing.
The separately measured blocked suffix alone uses 70,476 products round
trip. These counts rule out simply composing the existing stages under that
budget. The explicit leading word also needs a compatible layout at the
phase boundary. WSL on drive E produced no native receipt in this cycle.
The best full cloud comparison remains **33.20483975**.
[Monic fold bound](aggregate-above-36-dqi-blocked-suffix-26-11-2026-21-36-16.md)
· [Guarded phase evidence](aggregate-above-36-dqi-chart-guard-26-11-2026-21-22-13.md)
