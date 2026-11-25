# D4 live degree-31 route

The previous linked probe used the captured degree as a host-side
assumption. The new circuit checks the selected chart and the tight
collapse slot, then requires E₃₁ = D₃₂ = 0 and D₃₁ ≠ 0. These
coefficient bounds imply deg(E) ≤ 30 and deg(D) = 31. For the
projected numerator N = q₀E + h₀D, deg(N) ≤ 32. The cross
product with the original bounded pair has degree at most 67,
below the degree-68 external modulus.

The terminal pair starts with a unit denominator. At each inverse
fold, nonzero pivots prevent the newly introduced quadratic from
dividing both polynomials. The remaining quadratics are distinct,
so each factor's transfer preserves coprimality at earlier nodes.
The collapse layout test checks the top slot that would otherwise
lose a term. Together with the chart and degree checks, these
conditions admit the reconstructed degree-31 pair to the scan.

For off-chart inputs, the absorber temporarily maps a zero pivot
to one and increments a reversible count. The paired inverse
restores the same pivot and decrements the count. The 31 possible
folds fit in five bits. The certificate requires the count to be
zero. The final normalization has its own zero-to-one bridge so
it can restore rejected inputs even when coefficient 31 is zero.
The admitted converter's monic core does not use the supplied
history scratch parameter.

The residual scan computes each root as before and gates its phase
by the certificate. The mask projection still contributes phase
on every input. Any fallback must supply the residual phase for
rejected inputs while accounting for that projection once.

## Local tests and resource gate

The native linked test selected both copies of the original s2
syndrome and rejected the captured s6 and s7 value-error inputs,
the zero syndrome, and a constructed outer pole. The accepted
copies matched their exact input and fresh mask phases. The other
four copies matched a projection-only control. All syndrome,
mask, and scratch wires restored across both simulator seeds.

Delaying the certificate registers until after extraction reduced
the unguarded probe from 922 to 920 qubits at unchanged gate count.
The guarded probe used 926 qubits and averaged 421,805.17 and
421,775.17 executed gates in the mixed test batch. Its approximately
404,261-gate budget assumes the minimum pooled repetition factor.
The larger observed mean exceeds that budget by about 17,544 gates
per shot, before any fallback. The scan guard adds exactly 4,025
gates. Most of the remaining width increase appears at conversion.
At unchanged gate count, the largest width within the reference price
would be 906 qubits. Removing the scan guard alone would leave
the route over budget.
The route currently recognizes one interior-collapse position and
one degree. A fallback, an affordable all-input circuit, and
official pooled pricing remain open.

## Cloud replay

Google Cloud reproduced the local width, executed gate counts, phase
and restoration results. The five selected native tests passed in
190.13 seconds. The replay also covered the native compact layout
controls and the zero-pivot counter with zero, one, and two clips.
The retrieved archive matched the SHA-256 observed on the VM.
Compute Engine reported TERMINATED after receipt collection.

[Cloud log](evidence/d4-compact-repair-20261115/cloud-degree31-live-route/run.log) ·
[Staged inputs](evidence/d4-compact-repair-20261115/cloud-degree31-live-route/stage.sha256) ·
[Receipt archive hash](evidence/d4-compact-repair-20261115/cloud-degree31-live-route/receipt-archive.sha256) ·
[VM stop receipt](evidence/d4-compact-repair-20261115/cloud-degree31-live-route/vm-stop.json)
