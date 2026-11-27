# Chemistry v222 comparison and fixed-Gram normalization bound

Public catalog v222 adds four chemistry families and one inverse-square-root
circuit. Its best chemistry assembly uses the factorization of Дворкин
Евгений Владимирович and ANGLE circuits from goodpjw2008 and maoxin123.
The changes from v221 are loader slots 4 and 5. Slot 4 removes two charged
gates across forward and reverse evaluation, and slot 5 has the same charge.
The width remains 405. The catalog reports **249,093,638.98**, a **38,000.62**
cost reduction from v221. The new 254-qubit inverse-square-root entry costs
**1,945,828.11**. The best manifest inverse-square-root and DQI entries stay
the same. The v222 manifest SHA-256 is
`1bf7e0c367df9302304acb054040c8be656c2f3dc4a18db52fb133213cce1f66` and the
assembly description SHA-256 is
`813083919abee7062ac0654cab3e27f77db65cf39095185212799883fa463bda`.
[Catalog v222](https://www.kaggle.com/datasets/manwithacat/vqcc-apache-public-circuits/versions/222)
· [Loader source](https://www.kaggle.com/code/goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-25906)
· [Factorization source](https://www.kaggle.com/datasets/evgendvorkin/proba-2)

Replacing just the measured chemistry cost with that catalog result projects
**33.20823**, versus the complete cloud result **33.20483975**. Selecting the
best individually listed costs projects **33.25911** using a zero-failure
DQI draw. These component projections do not establish a new complete
portfolio score. [Measured comparison](evidence/aggregate34-20261126/public-cloud-audit.json)

## Exact normalization bound

For each group, let `A` contain the physical weight rows with the identity
coefficients appended as the last row. For any representation `A'` with
`A' A'^T = A A^T`, the triangle inequality gives
`sum_c ||A'[:,c]||_1^2 >= sum_ij |(A A^T)[i,j]|`. One quarter of the left
side is the group's two-body normalization. With the orbital projectors
fixed, the augmented Gram also fixes the two-body tensor, the one-body
contraction, and the squared norm of the native offsets. The gap and
one-body normalization therefore remain fixed in exact arithmetic.
The implementation evaluates the bound with integers after clearing the
common power-of-two denominator of the stored coefficients.
[Bound implementation](../tools/chem_channel_gram_bound.py)
· [Scoring contract](../contracts/contract.json)
· [Spectrum amplification and DFTHC](https://arxiv.org/abs/2502.15882)

| Control | Current two-body normalization | Exact Gram lower bound | Maximum reduction |
| --- | ---: | ---: | ---: |
| v221 | 270.148342076670 | 270.110439136782 | 0.037902939888 |
| v222 | 270.148342013733 | 270.110439078431 | 0.037902935302 |

At v222's 405 qubits and 13,110 charged gates, even attaining the bound
would save only **16,794** in projected chemistry cost. Reaching the
joint **230M** chemistry target at the same gap and layout would require
a **41.4422** reduction in raw normalization. The result rules out that
target through channel rotations that preserve the augmented Gram and
keep the existing layout. A reserialized factorization would still need
decoded verification, especially because the v222 gap exceeds its
strict floor by approximately `1e-11` Ha.
[v221 cloud receipt](evidence/aggregate36-20261126/chem-channel-gram-v221-cloud.json)
· [v222 cloud receipt](evidence/aggregate36-20261126/chem-channel-gram-v222-cloud.json)

Both factorization hashes matched the catalog. Three focused tests passed
on Google Cloud Shell with NumPy 2.3.5. They cover signed Gram cancellation,
dyadic orthogonal invariance, and omitting the identity row. Pyright passed.
[Tests](../tests/test_chem_channel_gram_bound.py)

## Normalization floor with fixed verifier shifts

Astra derived an offset-independent bound on the complementary factor
`2*Lambda-E_gap`. For any fixed group Gram of physical weights `G`, drop the
identity row and use the sum of the negative entries' magnitudes in `G`.
Writing each column's one-norm as `L`, row sum as `s`, appended identity
coefficient as `a`, and native offset as `a-s`, the difference
`(L+|a|)^2-(a-s)^2` is at least `L^2-s^2`. The one-body trace norm plus
trace is nonnegative. These facts give the bound after adding the pinned
energy and symmetry constants. A tighter bound retains a one-body positive
trace witness at `a=0`. Using the complementary factor with the strict
gap floor works throughout the verifier's domain.

In fact, dropping the Gram term also suffices. Let `K` be the fixed
quantity `E_upper - ecore + electrons * beta_1`, and let `H` be the
one-body operator used in scoring. The exact scoring equations give

```text
2*Lambda - E_gap = -K + ||H||_* + trace(H)
                  + 0.5 * sum_columns((L + abs(a))^2 - (a - s)^2)
```

Both terms after `-K` are nonnegative since `abs(s) <= L` and
`||H||_* >= -trace(H)`. This holds for any physical weight rows,
identity offsets, decoded projectors, and factorization shape. Cloud
Shell reproduced `beta_1 = 4.955104996915907` from the pinned shift
NPZ. With `E_upper = -22140.27335`, `ecore = -21021.2140122` and 113
electrons, `-K` is approximately **559.13247315**. Combining it with the
strict `E_gap > 3.914898` gate gives a derived effective-normalization
floor of approximately **46.78617959**. Retaining the fixed v222 physical
Gram raises this marginally to **46.78631890**.
[Verifier equations and fixed shifts](../contracts/contract.json)

At 405 qubits and 13,110 charged gates, the general floor gives a
chemistry cost of at least **248.414M** to the reported precision. A
successful **230M** design needs `T_total * Q_total <= 4,915,981.64`
at this floor. Holding width at 405 permits **12,138** total gates,
or at most **2,819** ANGLE gates per pass if the fixed 6,500-gate
charge stays the same. Holding 13,110 total gates permits at most
**374** qubits. These are necessary resource targets. Prior reduced-shape
fits have yet to pass the decoded residual limit.
[Earlier chemistry fit results](aggregate-above-36-chemistry-pilots-26-11-2026-07-29-00.md)
