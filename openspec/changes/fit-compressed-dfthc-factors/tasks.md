## 1. Gradients and profiling

- [x] 1.1 Add joint `(U, W)` objective and gradient to `src/qcompile/chemistry/factorization.py` with `u = v / ‖v‖`.
- [x] 1.2 Check gradients against finite differences on a small instance to `1e-6` relative error.
- [ ] 1.3 Profile one full-size objective plus gradient. Record time, memory and BLAS threads, then fix the evaluation budgets.

## 2. Initializers

- [x] 2.1 Implement I2 (subspace clustering with greedy pursuit), I3 (continuation by merging the pinned reference groups) and I4 (seeded random).
- [ ] 2.2 Implement the projection bound and rank I1–I4 per shape before optimization.

## 3. Residual fits (S1)

- [x] 3.1 Add a `fit` action to `tools/chem_shape_search.py` with registered caps up to 20,000 evaluations, checkpoints every 500, and the shared outcome states.
- [ ] 3.2 Run the 24-run grid and the controls on the approved VM. Upload every terminal record.
- [ ] 3.3 Record the best continuous residual per shape and initializer, and each outcome state.

## 4. `λ_eff` stage (S2)

- [x] 4.1 Read `Λ` and `E_SOS` from the pinned code. Implement smoothed gradients and exact checkpoint evaluation.
- [ ] 4.2 Run the augmented Lagrangian from each S1 fit at or below 19.0 mHa. Record `λ_eff`, `Λ`, `E_gap` and residual at each checkpoint.

## 5. Quantization ladder (S3)

- [x] 5.1 Encode at 12 through 8 bits. Refit `W` against decoded vectors at each step and regenerate one-body words.
- [ ] 5.2 Evaluate each step with the pinned evaluator. Stop at the first step that breaks a project margin.
- [ ] 5.3 Optional ablation: alternative Givens tree orders on the best shape.

## 6. Handoff

- [ ] 6.1 Export each eligible factorization in the strict NPZ layout with words, tree, metrics and expected coverage.
- [ ] 6.2 Record the shape decision and hand off to `synthesize-compressed-angle-loaders`.
- [ ] 6.3 Strict OpenSpec validation and a dated change log.
