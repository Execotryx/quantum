## Controls and gates

| Item | Value |
| --- | --- |
| Incumbent shape | `(65, 60, 60)`, 12-bit words, banked J9 |
| Incumbent metrics | `λ_eff` 49.30, two-body error 18.64 mHa, one-body 3.19 mHa, `E_gap` 3.9655 Ha |
| Incumbent cost | 3,247,752,448.67 (742 qubits, 88,781 Toffolis) |
| Continuation control | Incumbent shape refit continuously: 16.13 mHa |
| Rank bound at `L = 360` | 6.68 mHa |
| Verifier gates | Both residuals ≤ 20 mHa, `Λ > 49`, `E_gap > 3.914898` Ha |
| Project margins | Residuals ≤ 19.5 mHa; `Λ ≥ 49.05`; `E_gap ≥ 3.9160` Ha |

[Best pilot record](../../../docs/evidence/advance-hybrid-20261108/chemistry/r9-b143-c40.json) ·
[Structural ranks](../../../docs/evidence/advance-hybrid-20261108/chemistry/structural-rank.csv)

## Shapes

| Shape | Structural rank (8-bit, J3 / J5) | Lookup rows | Projected qubits (J3 / J5) | Preparation + rotation Toffolis (8-bit) |
| --- | --- | ---: | ---: | ---: |
| `(9, 143, 40)` | 146 / 193 | 1,363 | 412 / 428 | 6,741 |
| `(9, 129, 40)` | 137 / 183 | 1,237 | 412 / 428 | 6,713 |
| `(10, 129, 40)` | 211 / 249 | 1,366 | 412 / 428 | 7,105 |
| `(8, 120, 40)` | 4 / 8 (7-bit only) | 1,036 | 390 / 404 (7-bit) | 5,657 (7-bit) |

Fit all four, plus the continuation control. Smaller `R·B` lowers lookup
rows and preparation cost but makes the fit harder. The fit decides
which shape is eligible. At 8 bits, `(8, 120, 40)` projects 680–696
qubits in the structural model, so that shape is only useful if 7-bit
words pass the residual gate.

## Parametrization and gradients

Rows `X_(r,c) = Σ_b w_(r,b,c) · f_(r,b)`, with `f_(r,b) = svec(u_(r,b) u_(r,b)ᵀ)`
and `u = v / ‖v‖`. The existing `gram_residual` returns
`G = ∂R/∂X = 4(X Xᵀ X − X H)`.

- `∂R/∂w_(r,b,c) = ⟨G_(r,c), f_(r,b)⟩`
- `∂R/∂f_(r,b) = Σ_c w_(r,b,c) · G_(r,c)`. Call it `g_(r,b)` and let
  `M = smat(g_(r,b))` with the same √2 scaling as `svec`.
- `∂R/∂u = 2 M u`, and `∂R/∂v = (I − u uᵀ) · 2 M u / ‖v‖`

Check every gradient against finite differences on a small instance
(`n = 8`, `R·B·C ≤ 200`) to `1e-6` relative error. Profile one objective
and one gradient at full size before fixing budgets. The pilot measured
about 0.2 s per weight-only evaluation. Joint evaluation is expected to
take 0.2–0.5 s.

## Initializers

| Id | Construction |
| --- | --- |
| I1 | Current: consecutive spectral factors grouped, then top-`B` pooled eigenvectors (control) |
| I2 | Subspace clustering: cluster the 360 scaled eigen-matrices into `R` groups by the overlap of their dominant eigenvector spans. Pick `B` vectors per group by greedy pursuit that maximizes the group's explained energy in `span{u uᵀ}`. |
| I3 | Continuation: start from the pinned reference factorization `(65, 60, 60)`, merge groups agglomeratively by basis similarity down to `R`, then refit |
| I4 | Random unit vectors with least-squares weights (seeded control) |

Before optimizing, rank initializers by a projection bound. Project the
top-`L` eigen-matrices onto each group's `span{f_(r,b)}` and sum the
discarded energy. This bound is cheap and tracks the achievable residual
under fixed `U`.

## Objective stages

1. **S1, residual.** L-BFGS on `(U, W)` jointly. Run up to 20,000
   evaluations per (shape, initializer, seed), with checkpoints every 500.
   Stop at a continuous two-body residual ≤ 19.0 mHa, at the cap
   (`budget_limited` if still improving), or at a plateau (`no_go` under the
   shared rule).
2. **S2, `λ_eff`.** Read `Λ` and `E_SOS` from the pinned
   `dfthcsos.scoreinfra.dfthc_math` and `verify.py` code. Do not copy
   formulas from secondary sources. Minimize `λ_eff` with an augmented
   Lagrangian on residual ≤ 19.0 mHa, `Λ ≥ 49.05` and `E_gap ≥ 3.9160`.
   Smooth absolute values (`sqrt(x² + ε²)`, `ε = 1e-8`) for gradients, and
   evaluate checkpoints with the exact pinned functions. Because
   `∂λ_eff/∂E_gap > 0` when `Λ > E_gap`, the optimum sits near the
   `E_gap` margin.
3. **S3, quantization ladder.** Encode `U` through the Givens tree with
   `encode_vectors` at 12, 11, 10, 9 and 8 bits. At each step, reconstruct
   the decoded vectors, refit all `W` with `U` fixed (L-BFGS, up to 5,000
   evaluations), regenerate one-body words from `h1'`, and evaluate with
   the pinned evaluator. Descend while both decoded residuals stay
   ≤ 19.5 mHa. Test the current tree first. Alternative tree orders are
   a separate ablation.

## Compute plan

- Four shapes × three initializers (I1–I3) × two seeds = 24 S1 runs,
  plus I4 on the best shape and the continuation control.
- Pin BLAS threads at 2–4 per run and run in parallel on an approved
  16-vCPU CPU VM. Estimated 1–3 hours per run (estimate; replace it with
  the profiled time).
- Upload each terminal record and checkpoint hash as the run ends. Stop
  the VM after collection.

## Handoff

An eligible factorization exports the six NPZ arrays in the strict
canonical layout, the decoded word table at the final `brot`, the tree
edges, all pinned metrics and the expected coverage `(76 + R·B) · 64`.
It goes to `synthesize-compressed-angle-loaders`, which owns circuit
synthesis and promotion.

## Projection

`λ_eff` near 47–48 at `(9, 143, 40)` with 8-bit words gives a chemistry
cost of about `48 · T · 428`. The loaders decide `T`:

| ANGLE Toffolis per pass | Complete Toffolis | Cost | Ratio | Aggregate factor |
| ---: | ---: | ---: | ---: | ---: |
| about 21,500 (generic unary loader, estimate) | about 49,700 | about 1.02×10⁹ | about 3.3× | ×1.47 |
| about 4,500 (monomial loaders, public description) | about 15,750 | about 3.2×10⁸ | about 10× | ×2.13 |
