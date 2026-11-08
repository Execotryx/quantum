# Chemistry joint residual groundwork

Added a joint continuous residual and analytic derivatives for normalized basis
vectors and weights. The earlier pilot held vectors fixed and therefore cannot
decide whether a compressed shape is feasible. Every coordinate of both
gradients passes finite differences on an eight-orbital synthetic instance;
the packed residual also agrees with the pinned tensor reconstruction.

Added a registered full-shape profile action and retained its independent
[receipt](evidence/chem-joint-profile-20261108/profile.json). At shape
`(9, 143, 40)` and two BLAS threads, one objective and gradient took 0.478 s;
the process peak RSS was 1,055,948 KiB including loading and native tensor
comparison. This is one sample on the local machine, not a cloud benchmark
or a fixed production budget. Residuals from packed and pinned tensor
reconstruction agreed to floating-point precision. Two chemistry tests and
Pyright passed in the frozen Ubuntu Python 3.13 environment.

Added a registered continuous S1 runner for the spectral initializer and a
seeded random control. Its evaluation cap is enforced; its wall limit is
checked between evaluations and cannot interrupt a native linear-algebra call.
The runner records continuous checkpoints and pinned decoded metrics separately.

In a [20-evaluation pilot](evidence/chem-s1-pilot-20261108/), the spectral
residual fell from 5.8172 to 2.4778 Ha and the random-control residual fell
from 11.2590 to 8.3543 Ha. Both were still improving and were classified
`budget_limited`. These runs do not reject a shape or establish eligibility.
Added clustering and continuation initializers and checked them on synthetic
inputs. Four-evaluation full-shape smokes decreased the clustering residual
from 7.7816 to 6.8283 Ha and the continuation residual from 2.1187 to
1.8647 Ha. Both are `budget_limited`; their separate receipts are alongside the
other pilot receipts. Follow-up runs reproduced both residuals after removing
an unnecessary target eigendecomposition from continuation and a large
temporary allocation from clustering. These are shorter than the I1/I4 runs and do not rank
converged fits. Projection-bound ranking, the full fit campaign, later stages,
loaders, and chemistry acceptance remain open in the OpenSpec tasks.

Added a balanced spectral-factor projection diagnostic for comparing
initializers. It is not a certified lower bound on the tensor residual,
because factor rotations can change groupings without changing the tensor.
The [full-shape comparison](evidence/chem-projection-20261108/comparison.md)
ranks the initializers differently from their actual initial tensor residuals,
so it must not be used as a shape rejection gate.
Added smooth Lambda and energy-gap derivatives, including identity-offset
variables, and an augmented-Lagrangian objective. Synthetic finite-difference
checks cover every coordinate, and a separate synthetic comparison checks
Lambda and gap directly against the pinned evaluator; exact metrics remain
authoritative.
S2 remains gated: no eligible S1 checkpoint, domain-restoration procedure,
or exact-checkpoint optimizer orchestration has been established.
