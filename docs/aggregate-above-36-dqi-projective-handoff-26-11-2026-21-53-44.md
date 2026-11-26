# Degree-35 projective locator handoff

The continued fraction emits coefficients in the reciprocal polynomial
order. Reverse both banks and divide them by the physical leading word
of the reversed locator. A common nonzero scale preserves the roots and
the Forney residue. After the phase, multiply by the same word and apply
the inverse fold to restore the supplied quotient tape and clear its unit.

The normalization keeps the extra leading word live. The selected rank-42
tensors write interpolation products directly into their destination
coefficients, and scalar inversions borrow the inner subtower norm. The
Chien scan uses each constant term as its evaluation target, then XORs the
other terms away before advancing to the next position.

| Full degree-35 scope | Explicit ANDs |
| --- | ---: |
| Projective fold and inverse | 75,192 |
| Normalization and restoration | 5,880 plus two reciprocal round trips |
| Normalization, guarded phase, and inverse normalization | 194,067 |
| Entire tape-to-phase-to-tape composition | 269,259 |

The composition used **888 software-allocated qubits** and **330 equality
calls** before native lowering. The 4,095-position replay used 12 regular
and two nonregular derivative charts from full-weight syndromes with
both orientations. It checked the exact arbitrary-mask phase on regular
charts, suppressed phase on the two rejected charts, and restored all
inputs and scratch. The serializing native test uses the same fixture.
The E-drive WSL execution probe stayed pending, so the evidence is software
replay. [Software receipt](evidence/aggregate36-20261126/dqi-projective-continuant-phase.json)

Under the 280,000-gate planning figure the composition leaves **10,741**
gates before comparisons, extraction and fallback. Under the strict
**256,016.70-gate** ceiling for zero DQI failures at 888 qubits with the
measured public companions, it is already over by **13,242.30**. Even if
the remaining parts were free, that ceiling would require about a **4.92%**
drop in the companion cost product just to break even. A viable portfolio
needs a cheaper phase or locator construction, better companion costs,
or a combination of these. The full cloud comparison remains **33.20483975**.
[Public-companion ceilings](aggregate-above-36-public-frontier-26-11-2026-17-01-05.md)
