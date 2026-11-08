# Initializer projection comparison

Each lane used the same pinned input, full shape `(9, 143, 40)`, and one
evaluation, with one BLAS thread. The factor-space projection assigns each of
the 360 leading spectral rows to a group with capacity 40 and minimizes its
distance to that group's square-feature span. It is a diagnostic, not a
lower bound on tensor residual, because equivalent tensor factors can rotate.

| Initializer | Projection score | Initial tensor residual (Ha) |
| --- | ---: | ---: |
| I1 | 2.92465945 | 5.81722980 |
| I2 | 3.43872874 | 7.78155387 |
| I3 | 3.99898492 | 2.11866730 |
| I4, seed 184 | 6.77245705 | 11.25902720 |

The projection order differs from the initial tensor-residual order. All
one-evaluation optimizer outcomes are budget-limited; these scores neither
exclude a shape nor identify the best converged fit. Each subdirectory keeps
its own registration, score, exact checkpoint metrics and checkpoint hash.
