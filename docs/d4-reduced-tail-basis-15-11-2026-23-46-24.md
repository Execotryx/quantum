# D4 reduced tail basis and monic coordinates

The audit reconstructed the exact rational pair from all 53 cases. It
included every retained failing and passing capture, two forced outer
poles, three multiple-pole witnesses, and one deterministic input at
every weight from zero through 35. The tail solve based on coefficient
constraints and an independent solve using reduced polynomial columns
agreed on the admissible dimension and recovered the same primitive
locator and numerator.

## Degree bound

Let M map the tail to the original numerator and denominator. Each
doubled-node inverse has determinant q_i², including its shear and
orientation exchange. Thus det(M) = Q = product(q_i²), of degree 68.
A valid primitive denominator D is invertible modulo Q because its roots
lie in the base field. For an original degree-bounded pair (N,D), a second
pair (A,B) is in the polynomial image of M exactly when the cross-product
D*A + N*B vanishes modulo Q. In one direction
this follows from the determinant. In the other, B/D modulo Q provides
a scalar multiple of (N,D), so adj(M)*(A,B) vanishes modulo Q.

For input weight w, the cross-product map has a kernel of dimension
36-w, the allowed polynomial multiples of the primitive pair. Its image
is the space of polynomials through degree 34+w by dimension. The
multiples of Q in that image add max(0,w-33) dimensions. The
degree-bounded image therefore has dimension max(3,36-w). In particular,
weight 35 has exactly three coordinates for any exact chart sequence,
including the previously constructed raw rank-nine tail.

Matching the value and derivative jet at zero adds a factor X² to the
cross-product between any two recovered pairs. Its degree is at most 69,
so divisibility by the degree-70 product forces the cross-product to
zero. The reconstructed rational function is unique. Shorter weights
can have common-factor freedom in the polynomial pair.

## Native boundary and resource findings

A full-weight native test solved three live coefficients in the reduced
basis. It received the basis matrix and the denominator's leading
coefficient row as inputs. It used arbitrary projective scales on the
supplied jets and removed each scale by normalizing the three weights
before generating any polynomial banks. The recovered weights produced
the exact monic pair for all four weight-35 pole fixtures. The inverse
restored the input equations and cleared the solution and scratch, with
the requested phase applied between the two directions.
The local pole suite passed all 24 tests. Google Cloud passed the
focused native normalization test and produced a byte-identical
53-case audit. The downloaded receipt archive matched SHA-256
`2800636ae090160a0fe4131b08f00d089cd1d7b80b91e7e69cac69352403c3ef`.
The VM was confirmed terminated after collection.

The alternate online interpolation applied the original value and
derivative conditions directly at each node, including the final
point zero. It recovered the exact locator and numerator across all 53
inputs with no pole-specific branch in that scalar algorithm. The
explicit form peaked at 143 coefficient words, equivalent to 1,716
qubits before scratch. At that width the banked cost permits about
117,720 executed gates per shot. The existing converter and scan alone
accounted for at least 168,842 gates on the linked fixtures, using the
observed combined mean less the static synthesis count. Explicit basis
storage cannot meet the resource gate with the existing phase path.

Leading-coefficient replay reproduced the same polynomial basis change
on all 53 inputs without forming the full four-polynomial matrix. The
forced full-weight single, separated double, and triple poles requested at most
12, 20, and 28 distinct coefficients at any one transfer level. The
deterministic regular weight-35 control requested six. These are query
counts. A reversible schedule still needs to establish live storage,
compute pivots and repay or reverse every temporary update.

The three-coordinate tail path removes the dimension growth of the
forced-pole cases. A compact candidate still needs coherent generation
of the basis equations and a storage schedule that avoids both the raw
ladder and the explicit polynomial basis.

[Final 53-case audit](evidence/d4-compact-repair-20261115/tail-basis-final.json)
· [Leading-coefficient replay](evidence/d4-compact-repair-20261115/leading-basis-final.json)
· [Cloud receipts](evidence/d4-compact-repair-20261115/cloud-tail-basis/)
· [VM stop](evidence/d4-compact-repair-20261115/cloud-tail-basis/vm-stop.json)
· [Linked stage counts](evidence/d4-compact-repair-20261115/linked-synthesis-probe.json)
