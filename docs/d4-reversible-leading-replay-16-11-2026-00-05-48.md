# D4 reversible leading-coefficient replay

The native factor computes selected coefficients of one matrix row through a
doubled-node chart. After the optional incoming swap, its intermediate is
`C = B + h0*A + collapse*q*A`. It accumulates `U = q*A + (h1 + collapse)*C`
and `V = q*C` into caller-supplied words. The collapse chart initializes
`h1 = 0`. Two successive field-word temporaries hold `C` and the coefficient
of `q*A`. Measurement-based erasure repays the linear, product, and
chart-controlled phases before those words are reused.

The single-factor test exercised all four incoming/collapse flag combinations
with random coefficient banks and nonzero output targets. It checked the
polynomial result, restoration of live inputs, erased scratch, and a phase
fingerprint at two seeds.

The probe propagates only the requested final coefficient positions backward
through the legal factor supports. Both incoming orientations must use the
same live exponent labels. Recursive checkpoints are allocated on demand and
uncomputed once the next section has accumulated its result. The planner
chooses splits by peak live scratch and uses gate count as its tie-breaker
among the retained splits. It evaluates the two matrix rows sequentially.

The three weight-35 pole witnesses request 28 final words at 17 folds. The
wider row's support expands to 74 words at one cut, and its recursive
checkpoints reach 260 scratch words. The five-fold local circuit used 1,233
qubits, 32,064 gates to query, and 64,128 through query and erase. At both
seeds, it gave the expected coefficients and phase and restored the heads,
flags and scratch.

Google Cloud ran the emitted 17-fold circuit on all three witnesses at both
seeds. It matched the oracle, preserved the heads and flags, cleared scratch,
and reproduced the phase fingerprint. The measured circuit used 4,329 qubits
and 708,240 executed Toffoli-like gates per shot for the query. Query and erase
used 1,416,480 gates per shot. Both counts agreed with the planner. At this
width the banked cost permits about 18,497 executed gates per shot, so the
checkpoint schedule fails the resource gate on its own. Its cost at the
same repetition factor is about 77 times the banked cost before adding
extraction, the tail solve, synthesis, or the scan.

All 25 local pole-transfer tests passed, and the targeted single-factor
test passed on the VM. The local reports and cloud report have different
driver hashes because the local driver dropped a blank line after staging.
The 17-fold plan matches across both reports. The downloaded receipt
archive matched SHA-256
`905b87d98d1c185c0e12d461bdc2cf3bc99143ccbead3bd44f9c1c90600640de`.
Compute Engine confirmed the VM was terminated after receipt collection.

The requested output positions come from scalar pivot discovery on the
three pinned witnesses. A decoder still needs coherent pivot selection,
a proof of coverage for all legal charts, normalized tail assembly and
cleanup. Further work on this approach needs degree-aligned windows with
an in-place reversible update, or another method to obtain the tail
equations without storing these overlapping checkpoints.

[Local five-fold measurement](evidence/d4-compact-repair-20261115/leading-checkpoint-prefix-final.json)
· [Local 17-fold plan](evidence/d4-compact-repair-20261115/leading-checkpoint-plan-final.json)
· [Cloud 17-fold measurement](evidence/d4-compact-repair-20261115/cloud-leading-checkpoint/report.json)
· [VM stop](evidence/d4-compact-repair-20261115/cloud-leading-checkpoint/vm-stop.json)
