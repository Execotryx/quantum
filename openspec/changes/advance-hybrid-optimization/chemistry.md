# DFTHC shape search

## C1. Rank layouts and pin the numerical contract

- Extend `tools/chem_refit.py rank` with bounded, deterministic grid
  generation and sharding that preserve every input and rank. Keep the
  current 64-entry limit per shard. The report's four R values, four B
  values and six C values give 96 shapes, or 384 layouts with two
  precisions and two batch sizes. Record `RC`, `76+RB`, address width,
  `ceil(75/J)`, official preparation and rotation costs, and both scored
  and per-ANGLE qubits. Include the historical J9, generalized J9,
  reference J8 and a wider-RC control. Treat zero-ANGLE structural
  ranking as a bound for the selected layout.
- Keep the fixed symmetry shift and beta, and use the actual
  `H2_I - sum_b(W)` offset convention. In the pinned code
  `KEEP_BITS=10` is alias-sampling precision. It is independent of
  ANGLE `brot`. Screen 12-bit words as a numerical control and gate
  8-bit and 7-bit variants on decoded residuals. Treat the signed gauge
  as a separate derived representation with its own parity checks.
- Reproduce reference J8 and the certified J9 from pinned evidence.
  The latest fixed-word pilot and generalized J9 are separate controls.
  The generalized loader's measured extra gate count makes it unsuitable
  as a substitute for the certified baseline.
  [Chemistry development measurements](../../../docs/next-hybrid-validation-08-11-2026-00-04-43.md)

## C2. Profile a deterministic fitting pilot

- Add `src/qcompile/chemistry/factorization.py` and a
  thin registered `fit-shape` entry point in `tools/chem_refit.py`.
  Use pinned integrals and a deterministic independent initializer,
  such as clustered double-factorization eigenvectors with stable
  sign/order rules. Record seeds, BLAS threads, precision, data hashes
  and convergence reasons. Keep a continuation control to diagnose
  compressed-shape infeasibility.
- Use the shifted pair-index target
  `H = tei + (S ⊗ I + I ⊗ S)/2`. With columns `x_l = vec(X_l)`,
  evaluate the squared two-body residual as
  `||H||_F² - 2 sum_l x_lᵀ H x_l + ||Xᵀ X||_F²`.
  Use weighted symmetric coordinates with off-diagonal terms scaled
  by `sqrt(2)` only after reconciling them to the full target. For
  symmetric H the gradient in X is `4(X(XᵀX) - HX)`. Use blocked
  contractions and cached shift terms. Compare to a
  streamed direct residual near the acceptance boundary to catch
  cancellation. Differentiate through the real factor weights and
  validate gradients against small dense problems. The Gram identity
  reduces storage of the approximation but still incurs contractions
  against the two-electron target.
  [Competition paper, v2 Eq. 80](https://arxiv.org/html/2610.23832v2)
- Before fitting, bound the best possible residual of an unrestricted
  PSD rank-`L=RC` approximation to the shifted pair matrix. Retain
  the largest L positive eigenvalues. The squared lower bound sums the
  squares of all discarded eigenvalues, including the negative ones.
  Prune only if the bound exceeds the residual allowance after
  accounting for spectral and compression error.
- Fit the continuous two-body factors first. Use alternating updates or
  a bounded gradient optimizer, with explicit regularization ablations
  and joint offset updates. The one-body Hamiltonian's spectral norm
  couples the offsets. Recompute the 76-dimensional one-body
  eigendecomposition and regenerate its dependent words after each
  accepted weight or decoded-word change. Keep candidate cost and the
  constrained numerical objective separate.
- Pilot one compressed shape and one continuation control, at most two
  seeds per shape and one hour total as a proposed cap. Profile one
  objective and one gradient before fixing
  a bounded iteration count, memory ceiling, wall allowance and
  checkpoint interval. Bound the first expansion to four shape families
  and two seeds per family. Start with `(9,129,40)`, `(9,143,40)`,
  `(10,129,40)` and a continuation chosen after the rank bound.
  Reserve the wider 15-shape shortlist for a separately budgeted
  expansion. Historical accelerator timings describe the paper's
  shape and environment.
  [Spectrum amplification and resource model](https://arxiv.org/abs/2502.15882)

## C3. Quantize, synthesize and promote

- Start at 12 bits and descend through 11, 10, 9 and 8 while preserving
  feasibility. Register 7 bits only after the ladder passes. Quantize
  through `chemistry/representation.py`, reconstruct the
  actual decoded words and regenerate the one-body angles. Use the
  pinned verifier's dense residual and exact domain checks for every
  finalist. Require both errors at most 0.020 Ha, positive radicand,
  `Lambda > 49` and `E_gap > 3.914898` Ha. Preregister project
  headroom separately, starting with 0.0195 Ha for each residual.
- Use the generic XOR family as the exact loader control. Extend
  `tools/banked_chemistry.py` only for a derived ANF or paired-product
  implementation with a legal uncompute. Generate coefficient tables
  from candidate-owned words and prove the mixed-product identity with
  its pure-term corrections. Price `J=3` and `J=5` initially. Check
  exact XOR on arbitrary targets and all addresses including padding,
  forward and reverse traversal, zero private workspace and unchanged
  phase and selection. Enforce 128 qubits on each ANGLE circuit and
  price total scored width and both traversals.
- Build at most two native finalists and promote at most one. Keep
  immutable NPZ, word, circuit and recipe hashes and repeat the build.
  Recompute full coverage from the frozen NPZ. The example
  `R=9, B=143` requires 1,363 rows and 87,232 trajectories, regardless
  of C. Require full verification, fresh confirmation, and actual cost
  of about 2,922,977,203.80 or lower. Record an 8–10× result as a
  stretch hypothesis. If the search yields no eligible factorization
  or cost win, preserve the verified J9 component.
