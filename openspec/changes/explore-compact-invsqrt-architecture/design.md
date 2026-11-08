## Scope and initial bookkeeping

Control is the verified 28/20/14 lattice circuit, SHA-256
`c487332fe965389191c8e6d34848d61c82748e5802c6e616eb0363869f92c4c9`:
155 declared qubits, 3,046 Toffoli-like gates, one T-like gate and 35 fine
rotations. The retained model receipt is
`docs/evidence/invsqrt-lattice-20261108/compact-bookkeeping.json`.

The current output register has 39 qubits. Replacing it with a hypothetical
30–36-qubit gradient register, without changing any other allocation, leaves
146–152 qubits. Thus 46–52 additional declared qubits would need to disappear
under that bookkeeping assumption to reach 100. This is not a circuit lower
bound: changing the architecture can alter peak lifetimes and workspace.

The control has about 3,287 rotation-inclusive Toffoli-equivalents. Even if
all direct rotation charges vanished for free, its 3,046 Toffoli-like gates
would still require a reduction of 1,046 to reach 2,000. The hypothetical
phase-gradient preparation, accumulation, synthesis and cleanup are not free
and are not priced by this bookkeeping.

## Work sequence and stop rule

1. Freeze an exact phase-accumulation recurrence and its admissible precision,
   including coefficient lookup and all gradient preparation and uncomputation.
2. Establish a component cost model, calibrated against emitted slices, for
   width, Toffolis, T gates, rotations and gradient preparation; enumerate
   additional peak-workspace changes rather than subtracting registers blindly.
3. Price gated signed-digit rows separately with their decoder, rounding,
   restoration, and measurement-branch phase corrections.
4. Combine only independently improving components. Admit a prototype only if
   the complete model predicts at least 20% lower cost, then require the full
   domain and native parity gates before any verification or promotion.
5. Stop after 40 engineering hours or earlier on a failed feasibility gate;
   record the work actually spent and all unresolved model assumptions.

The bookkeeping does not yet predict a complete candidate score. No compact
prototype is admitted by this registration.
