# Chemistry shape resource screen for score 35

The pinned PREPARE model reproduces v222's **405 qubits** and **6,500**
fixed charged gates at `(R,B,C) = (9,127,46)` with five-word, seven-bit
ANGLE batches. The 128-qubit loader cap leaves less loader temporary
space than the model's existing shared workspace across the screened
layouts, so lowering loader scratch alone cannot beat these minimum
task widths. The optimism in the table comes from dropping the measured
normalization to the derived floor of 46.78617.
[Normalization analysis](degree35-chemistry-gram-bound-27-11-2026-15-00-55.md)
· [Pinned resource contract](../contracts/contract.json)

| Shape at `J=5` | Minimum qubits | Fixed gates | ANGLE budget per pass at 230M | Cost if ANGLE charge stays at 3,305 per pass |
| --- | ---: | ---: | ---: | ---: |
| `(9,127,46)` | 405 | 6,500 | 2,819.11 | 248.41M |
| `(9,127,40)` | 405 | 6,024 | 3,057.11 | 239.39M |
| `(9,96,46)` | 405 | 6,024 | 3,057.11 | 239.39M |
| `(9,95,46)` | 405 | 5,608 | 3,265.11 | 231.51M |
| `(9,63,46)` | 386 | 4,691 | 4,022.35 | 204.09M |
| `(8,127,42)` | 404 | 5,812 | 3,178.14 | 234.80M |
| `(8,120,40)` | 404 | 5,657 | 3,255.64 | 231.87M |

Dropping from 96 to 95 basis rows removes an inner QROAM block and saves
**416** fixed gates without changing task width. At 95, the optimistic
230M budget asks for about **40 fewer ANGLE gates per pass** than the
current five-word layout. The 63-row shape has room at the current charge
in the cost model. It still needs decoded accuracy and a new loader. The
eight-group shapes also need a loader saving at the same batch width, and
their previous decoded errors were at least 0.157966 Ha against the 0.020
Ha limit. A one-word batch at full shape needs 75 loaders. Its optimistic
budget of **3,269.87** per pass requires fewer gates across all 75 than
the current assembly uses across 15.
[Previous fit measurements](aggregate-above-36-chemistry-pilots-26-11-2026-07-29-00.md)

The v222 dictionary has no all-zero weight rows and no byte-identical
active angle-word rows within any group. This rules out those two exact
compactions. A distinct-word projector equivalence would need its own
witness. For a different test, backward elimination projects each current
channel onto the span of a smaller set of decoded projectors. Given the
projector Gram `K`, losing row `i` increases the summed channel loss by
`||weights[i]||² / inverse(K)[i,i]`. Rank-one inverse updates keep the
least-squares projection exact in the chosen span up to numerical error.
The heuristic chooses a single nested sequence of subsets and holds the
native offsets and one-body angle words fixed during decoding. It does
not globally optimize row selection or re-fit the orbital basis.
[Pruning driver](../tools/chem_fixed_dictionary_prune.py)
· [Interpolation and tensor hypercontraction](https://arxiv.org/abs/1410.7757)

| Basis rows per group | Decoded two-body residual (Ha) | Effective normalization with retained one-body words |
| ---: | ---: | ---: |
| 127 control | 0.0199999999900 | 46.91427 |
| 119 | 0.21912530 | 75.77066 |
| 95 | 0.72863712 | 172.94765 |
| 63 | 1.78300983 | 300.36827 |

Google Cloud Shell reproduced the control and checked these three subsets
with the pinned official decoded-vector evaluator. The fixture test
compared the inverse updates and accumulated loss against direct least
squares. The smallest pruning step misses the two-body limit by more than
tenfold, so none of the three subsets goes to loader synthesis. These are
measured results for one fixed-dictionary heuristic. They leave other
subset choices and changed orbital bases open. The best complete cloud
score remains **33.20483975**.
[Cost and inventory receipt](evidence/aggregate36-20261126/chem-shape-resource-cloud.json)
· [Decoded pruning receipt](evidence/aggregate36-20261126/chem-shape-prune-cloud.json)

## Single-row omission against the reference tensor

Astra proposed a test that removes the dependence on the greedy selection
and the incumbent channel fits. Pack the shifted target into symmetric
pair coordinates and let `P` project onto the joint span of the decoded
orbitals' rank-one projectors. If row `i` is independent, find its unit
dual `u_i`, orthogonal to all the other rows. With `M = P T P`, the best
possible relaxed error after dropping row `i` has squared norm
`||T-M||_F^2 + 2||M u_i||^2 - (u_i^T M u_i)^2`. The formula projects onto
both sides of the retained span. Allowing arbitrary symmetric coefficients
also relaxes the positivity, group couplings and rank constraints of a
physical fit. The numerical check records the smallest singular value
and the largest off-diagonal dual leakage so a result can be interpreted
against the residual margin. The fixture compares this expression with
direct projection after removing each row.

The cloud run found full rank **1,143**, an unrestricted residual of
**0.01271258 Ha**, smallest singular value **0.008868**, and maximum
dual leakage of **5.25 × 10⁻¹⁵**. For the third group, **88** rows pass
the individual-removal screen at a cutoff of **0.020000001 Ha**. Applying
the same projection to pairs defines a compatibility graph. Every set
of simultaneous omissions must form a clique in that graph. A proper
40-color partition bounds the clique size by **40** for this group.
The working-precision result excludes the **64** omissions required for
63 rows from this fixed dictionary. The **32** omissions required for
95 rows remain unresolved. The receipt retains the coloring and the
per-row residuals. A sharper graph bound or a complete retained-span
witness can distinguish the remaining case before any physical refit.
A changed orbital basis remains outside the screen.
