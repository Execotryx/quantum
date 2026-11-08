## Why

The compressed chemistry fit is the gate on the second-largest lever, and
gradient fitting is slow. At `(9, 143, 40)`, L-BFGS on the joint objective
reached 81.40 mHa after 1,500 evaluations and 41.57 mHa after 5,000 more,
still improving. The continuous gate is 19.0 mHa. Each evaluation costs
about 0.5 s.
[Continuation result](../../../docs/chemistry-i3-continuation-result-08-11-2026-16-19-24.md)

The objective `‖H − XᵀX‖` has a rotational freedom that L-BFGS must find
by itself: any `X = QY` with orthogonal `Q` and `H ≈ YᵀY` fits equally well.
Alternating projection removes it. Each sweep aligns the target factor
`Y` to the current rows with an orthogonal Procrustes step, then makes
exact block updates: least squares for the weights, and a top eigenvector
for each basis vector. It combines the least-squares fitting used for
tensor hypercontraction (Parrish, Hohenstein, Martínez and Sherrill,
J. Chem. Phys. 137, 224106, 2012) with Procrustes alignment of the
factor rotation. A sweep costs about the same as a few gradient
evaluations and makes much larger moves.

## What Changes

- Add `fit_alternating` to `src/qcompile/chemistry/factorization.py`:
  Procrustes alignment, per-group weight least squares, per-vector
  eigenvector updates, fixed sweep count.
- Run four fixed lanes for 400 sweeps each, followed by a 3,000-evaluation
  L-BFGS polish on the true objective.
- Hand the best lane that passes the gates to `promote-compressed-chemistry`.

## Impact

- Code: `src/qcompile/chemistry/factorization.py`, new
  `tools/chem_alternating.py`.
- Compute: about 7–10 minutes per lane for the sweeps (estimate) plus about
  25 minutes for the polish. Four lanes fit on one 4-worker machine in
  under an hour.
- No circuit changes in this change.
