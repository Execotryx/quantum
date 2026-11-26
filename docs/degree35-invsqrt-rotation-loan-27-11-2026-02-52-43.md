# Nonlinear wire loan in the inverse-square-root rotation window

Astra proposed borrowing `q19` for the product rotation at line 9,871
of the pinned Tony Li assembly. The prefix proof checks that quantum
values are independent of measurement outcomes through the cut. The
bit-sliced replay verifies `q19 = q20 AND q24` and `q21 = 0` on the
complete legal input domain. One CCX clears `q19` before the rotation.
The original HMR and conditional CZ use the same product and guard,
and a second CCX restores `q19` before `q20` is measured.
[Source rewrite](../tools/invsqrt_rotation_loan.py)
· [Registration](evidence/aggregate36-20261126/invsqrt-rotation-loan-registration.json)

The comparison applies the same reset scheduling, pruning, and width
allocation to the control and to the loan path. Both require **39
qubits**. The two native replays match tracked phase exactly on 2,816
stratified inputs under two shared measurement seeds. Both restore the
input register and clear scratch. The variant trades two unconditional
Toffolis for a wire that is idle in one rotation window. Other peak
windows set the complete width.
[Width screen](evidence/aggregate36-20261126/invsqrt-rotation-loan-screen.json)
· [Matched native check](evidence/aggregate36-20261126/invsqrt-rotation-loan-matched.json)

The pinned verifier on E-backed Ubuntu passed both complete circuits
with two trajectories for every legal input, **6,266,904** per circuit.
The matched-layout control cost **61,696.20** and the loan cost
**61,774.21**. Both had 33 fine rotations and the same worst-case ratio
of phase error to tolerance, **99.98178%**. The loan exceeds the
**52,119.68** component budget with the current source-built companions.
These development salts establish the component result locally. The
aggregate cloud comparison stands at **33.20483975**.
[Control verifier receipt](evidence/aggregate36-20261126/invsqrt-rotation-loan-control-native.json)
· [Loan verifier receipt](evidence/aggregate36-20261126/invsqrt-rotation-loan-loan-native.json)
