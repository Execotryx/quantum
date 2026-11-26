# Rounded quadratic product measurements

The first product updates the supplied slope register in place. Its
magnitude is positive over the frozen domain, so the second product
can use unsigned magnitude rows and a signed local input. The
guard bits preserve the fractional residue until the adjoint. The
inner stage rounds before negation and the outer stage rounds the
negative product. Their biases differ by one guard unit at ties.
The method checks both a base accumulator and a signed correction
that permits a later constant-term load.
[Registered arithmetic comparison](evidence/aggregate36-20261126/invsqrt-rounded-quadratic-registration.json)

The exact 12- and 14-guard control reproduced the 192-interval
integer model. Dropping the low portion of each partial row and
retaining one guard bit per product still passed all **3,133,452**
legal inputs against the pinned phase targets. Worst tolerance
use rose from **68.85%** to **81.60%**. The 2-, 3-, 4-, and 6-guard
models also passed. The registered selection criterion chose the
smallest tested pair that stayed within 90% of tolerance.
[Full-domain screen](evidence/aggregate36-20261126/invsqrt-rounded-quadratic-screen.json)

| Native arithmetic and cleanup | Add method | Declared qubits | Executed Toffolis |
| --- | --- | ---: | ---: |
| Exact, base live | Controlled adder | 160 | 4,150 |
| Exact, base live | Measured partial products | 182 | 3,260 |
| One guard, base live | Controlled adder | 123 | 3,522 |
| One guard, base live | Measured partial products | 145 | 2,632 |
| One guard, separate correction | Controlled adder | 107 | 2,856 |
| One guard, separate correction | Measured partial products | 129 | 2,190 |

The serialized circuits passed **1,536 fixtures per case**, checking
eight local values at every interval, including boundary and sign
transitions. Forward runs checked both integer products and all
operand words. The matched round trips restored the inputs and
guards, cleared scratch, and left the phase unchanged.
[Native circuit hashes and counts](evidence/aggregate36-20261126/invsqrt-rounded-quadratic-native.json)

The best arithmetic-only width-times-gates product is **282,510**,
against the **52,119.68** complete inverse-square-root cost ceiling
with the source-built companions. Both coefficient loading and
the final phase would add work. This rules out these row schedules
at the current allocation, even though the numerical model fits
with one guard. The highest complete cloud comparison remains
**33.20483975**.
[Companion budget and lookup results](degree35-invsqrt-source-research-27-11-2026-01-39-29.md)
