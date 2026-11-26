# Projective DQI derivative action

On the regular Euclidean chart, each degree drops by one. The new
two-bank action keeps the nonzero leading coefficients in their
existing slots. It borrows the modulus head for the quotient slope
when that head is stored, uses the next slot for the quotient constant,
and restores both heads after the recursive solve. Payload reduction
shares the divisor inverse with the quotient setup.

For a modulus (A) of degree (k+1), a divisor (D) of degree (k),
and payload (X), write (X=C D+E) and (R=Amod D). A child
payload (Q) satisfying (RQ=Emod D) gives
(Y=C+(E+AQ)/D) with (DY=Xmod A). The child's reversed series
stores the first (k) coefficients of the parent result. In
(z^{-1}Y(1/z)/A(1/z)) the contribution from (E/(AD)) begins
at degree (k+1). The last coefficient can therefore be added
with a dot product and the two leading scalar factors. The circuit
keeps the original top payload word until that extension.

| Native scope | Normalized circuit | Projective circuit | Declared qubits |
| --- | ---: | ---: | ---: |
| Degree-3 derivative action, one direction | 786 | 582 | 111 |
| Degree-7 derivative action, one direction | 3,870 | 4,818 | 207 |
| Degree-35 derivative action, one direction | 74,724 | 67,272 | 879 |
| Degree-35 phase with supplied locator and evaluator | 194,493 | 179,589 | 879 |

The degree-35 phase circuit saves **14,904 gates**, or **7.66%**.
The opt-in requires a fully regular half-degree chart. The normalized
action remains available for other fixed charts and for the reduced
degree-7 case where it has the lower measured cost.
[Native receipts](evidence/aggregate36-20261126/dqi-projective-forney/)

Independent forward and inverse tests check the field results against
classical extended Euclid. The 4,095-position native scan checks the
arbitrary mask phase, exact input restoration and clean scratch for 16
weight-35 and 16 weight-34 trajectories. The latter use one padding root
at zero, outside the scan. Both fixtures establish their Euclidean chart
before simulation.
The focused native suite passed 21 cases on Ubuntu on drive E. The
final projective and normalized comparison rerun passed eight cases.
Pyright and strict OpenSpec validation passed.

Under the 280,000-gate development allocation, **100,411** gates remain
for locator construction, cleanup and routing. With the most optimistic
public companion costs and zero DQI failures, the tighter 879-qubit
ceiling leaves **81,697.20**. The first locator reciprocal and its inverse
now fit both remainders. The first three pairs and the new phase stage
still cost **388,137** before the rest of locator construction. The
best full cloud comparison remains **33.20483975**.
[Locator measurements](aggregate-above-36-dqi-middle-product-26-11-2026-16-47-11.md)
· [Public companion budget](aggregate-above-36-public-frontier-26-11-2026-17-01-05.md)
