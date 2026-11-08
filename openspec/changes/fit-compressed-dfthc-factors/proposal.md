## Why

Chemistry is at 1.033×. The structural ranking already shows where the
frontier sits. Shape `(R, B, C) = (9, 143, 40)` with 8-bit words and `J = 5`
projects 428 scored qubits and 6,741 preparation and rotation Toffolis,
against 742 qubits and 13,757 for the banked incumbent. That shape
needs a factorization within 20 mHa.

The compressed pilot was recorded as `continuous_no_go` with residuals near
3.1 Ha. Reading `tools/chem_shape_search.py` shows two limits, not one.

- The 20-evaluation cap stopped every fit while it was still improving.
- **The fit optimized only the weights `W`.** The basis vectors `U` stayed
  fixed at the initializer for the whole run. With `B = 143` vectors per
  group in 76 dimensions, the quality of `U` decides whether 40 squares per
  group can be represented at all.

The PSD rank diagnostic at `L = R·C = 360` is 6.68 mHa, below the 19.5 mHa
gate, so the target is representable without the shared-basis constraint.

## What Changes

- Jointly optimize `U` and `W` with analytic gradients and unit-norm
  vectors, under budgets of thousands of evaluations.
- Add three initializers beyond the current spectral grouping, plus a
  cheap projection bound to rank them before optimizing.
- Stage the objective: residual first, then a smoothed `λ_eff` term under
  residual, `Λ` and `E_gap` constraints.
- Quantize through the Givens tree on a 12-to-8-bit ladder. After each step,
  refit all weights against the decoded vectors and regenerate one-body words.
- Hand eligible factorizations to `synthesize-compressed-angle-loaders`.

## Impact

- Code: `src/qcompile/chemistry/{factorization.py, refit.py}`,
  `tools/chem_shape_search.py` (new `fit` action), `tools/chem_refit.py`.
- Compute: an approved CPU cloud VM run for the full grid (estimate: one night).
- Outcome states follow `harden-kaggle-operations`. A cap that ends an
  improving fit is `budget_limited`.
