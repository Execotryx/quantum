# Fixed-basis projection and rank relaxation

For a fixed set of basis vectors, let `S` be the linear span of all their
packed rank-one symmetric features, let `P` project orthogonally onto any
superspace of `S`, and let `K = R*C`. Every represented PSD tensor matrix has
rank at most K and support in `S`. Dropping group restrictions therefore
enlarges the feasible set. In exact arithmetic the minimum squared residual
over that relaxed set is

`||H - P H P||_F^2 + PSD_rank_tail(P H P, K)^2`.

The first term is Frobenius-orthogonal to the part inside the projector; the
second retains at most K positive eigenvalues and discards all remaining and
negative eigenvalues. QR keeps all returned columns, including redundant ones,
so the computed subspace is not intentionally narrowed by a rank tolerance.
The implementation evaluates the outside term in row blocks and reports QR
orthogonality error. Synthetic tests cover full span, indefinite targets,
duplicate basis vectors and sampled feasible factorizations.

The formula is a genuine lower bound in exact arithmetic **for a fixed basis**.
The floating-point result is not a certified numerical bound, and a joint fit
may change its basis, so this diagnostic must not reject a shape or establish
eligibility. `tools/chem_projection_bound.py` supplies a supervised, hash-bound
real-input route; the plan `tools/chem-projection-i3-r9-b143-c40.json` pins the
I3 ranking artifact, ranking evidence, factorization and target. It records a
separate sampled resource receipt and diagnostic-only outcome.

On the registered I3 initializer at `(9,143,40)`, the floating-point
relaxation estimate was **316.44 mHa**, compared with the initializer
residual of **2,118.67 mHa**. The diagnostic took 3.26 seconds after
loading. The external sampler observed 603,171,840 bytes peak
process-tree PSS and zero swap PSS across 29 samples. The worker was
launched after the final dtype change, and its source digest matches
the frozen implementation.

[Diagnostic](evidence/chem-projection-bound-i3-20261108/worker/diagnostic.json) ·
[Worker registration](evidence/chem-projection-bound-i3-20261108/worker/registration.json) ·
[Resource sample](evidence/chem-projection-bound-i3-20261108/resources.json)
