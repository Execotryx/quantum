# D4 incoming pole synthesis

The frozen s6 and s7 inputs have a first-head pole at groups 6 and 2.
The original denominator vanishes at the doubled node and the
original numerator is nonzero there. Swapping coordinates makes
the reciprocal first head zero. The second head remains finite
and the inverse of that pair has a reduced formula.

For continuation pair (U,V) and local monic quadratic q, the original
numerator is h₁U + qV and the original denominator is qU. The
second-head absorber forms the numerator once. The inverse writes
qU by triangular linear updates into U and the two zero first-head
slots. Reversing these updates before inverting the absorber gives
the same operands for its measurement-phase repayment.

Both captures have two zero upper numerator coefficients in the
preceding synthesis step. The emitter uses the smaller coefficient
view at the pole and retains the omitted physical slots for the
inverse. The certificate rejects if either slot is nonzero. The
degree-32 route starts at a constant unit tail. The degree-33 route
recovers the linear numerator from the scalar jet. Assuming a
constant nonzero denominator, the linear coefficient is the
Wronskian divided by that denominator. Zero pivots clip to one for
reversibility and the certificate requires their count to be zero.

The certificate also checks one incoming pole at the selected
group, an otherwise regular chart, a nonzero locator lead, and
deg(q₀E+h₀D) ≤ 32. With deg(D) at most 33, the cross product
against the original pair has degree at most 67 and vanishes
modulo the degree-68 external-node product. The admitted folds
produce coprime pairs. Nonzero pivots exclude common quadratic
factors introduced by the transfer determinants, and the seed
has a nonzero constant coordinate.

For the shared degree-33 converter, padding the even-degree pair
by X adds a root at zero, outside the scan. The original locator
has only nonzero roots. At each such root the numerator and
locator derivative pick up the same nonzero factor. This padding
reuses the two certified zero slots and needs no multiplication gates.
The converter restores these slots on rejected inputs as well.
The residual phase is guarded by the certificate. Rejected inputs
get only the same projection phase as the projection-only control.

## Common synthesis layout check

An independent polynomial replay used the pinned syndromes to
check a common tail shelf with two U words and one V word. Reversing
each pair grows both capacities by two. All three paths fit every
fold. At a collapse, the highest available V slot is zero. At an
incoming swap, the original denominator fits the smaller bank
and the reciprocal numerator's excess slot is zero.

| Capture | Tail U/V words | Special group | Available U/V words | Actual U/V words |
| --- | --- | ---: | --- | --- |
| s2 / 45440 | 1/0 | 16 | 2/1 | 1/0 |
| s2 / 45440 | 1/0 | 6 | 22/21 | 20/17 |
| s6 / 102316 | 1/0 | 6 | 22/21 | 19/20 |
| s7 / 52983 | 2/1 | 2 | 30/29 | 28/29 |

The same scalar audit read the failure rows and neighboring control
rows from the original and residual capture directories. All 12
inputs, with weights 26 through 34, fit the same shelf. This checks
storage and the zero-slot conditions. A shared native route still
needs to recover the live tail, certify the degree and select the
converter without losing the phase on any supported chart.

A shared seed can read both constant coordinates from the
scalar jet. When the denominator coordinate is nonzero, use
the Wronskian divided by that coordinate for the numerator
slope. When it is zero, a valid constant unit tail requires a
nonzero numerator coordinate and zero Wronskian. The scalar
jet identity adds divisibility by X² to the external-node
certificate. With the full original degree bounds, the
resulting cross product has degree at most 69 and the joint
modulus has degree 70. This gives a way to use the broader
degree bounds once the common route certifies its seed and
every fold's storage and pivot conditions.

## Local resource screen

Both probes recovered the exact projected evaluator and locator
up to scale. They reproduced the expected phase for the original
and fresh masks with zero syndrome, mask, or scratch differences.
The opposite capture and the zero syndrome were rejected by each
route and matched the projection-only controls. Each case ran
at simulator seeds 747 and 748.

| Route | Initial qubits | Final qubits | Final largest measured mean | Gate budget |
| --- | ---: | ---: | ---: | ---: |
| s6, degree 32 | 963 | 939 | 433,854.00 | 393,145 |
| s7, degree 33 | 946 | 940 | 443,792.75 | 392,309 |

The revision removes the two dedicated padding words and saves
24 qubits on the degree-32 route. Separating the spill zero check
from the coefficient predicate reduces the degree-33 route by six
qubits. Both means
remain above the budget at the minimum repetition factor. At
their measured gate counts the widths would need to be at most
893 and 883 qubits, respectively, to beat the reference price. Their
results support the reciprocal fold and common scan interface.
They give no qualification for a merged decoder or full pricing.

## Cloud verification

The initial cloud run passed both incoming-pole regressions and
the degree-31 control in 735.90 seconds. Both routes exactly
reproduced their initial local width and gate measurements.
The downloaded archive matched the VM's SHA-256.

[Initial cloud log](evidence/d4-compact-repair-20261115/cloud-incoming-pole-route/run.log) ·
[Staged inputs](evidence/d4-compact-repair-20261115/cloud-incoming-pole-route/stage.sha256) ·
[Receipt archive hash](evidence/d4-compact-repair-20261115/cloud-incoming-pole-route/receipt-archive.sha256)

The final, scratch-reusing revision passed the same three tests
in 714.29 seconds and exactly reproduced the final local
measurements above. The downloaded archive matched the VM's
SHA-256 before extraction. Compute Engine confirmed termination
after receipt collection.

[Final cloud log](evidence/d4-compact-repair-20261115/cloud-incoming-pole-scratch/run.log) ·
[Staged inputs](evidence/d4-compact-repair-20261115/cloud-incoming-pole-scratch/stage.sha256) ·
[Receipt archive hash](evidence/d4-compact-repair-20261115/cloud-incoming-pole-scratch/receipt-archive.sha256) ·
[VM stop receipt](evidence/d4-compact-repair-20261115/cloud-incoming-pole-scratch/vm-stop.json)
