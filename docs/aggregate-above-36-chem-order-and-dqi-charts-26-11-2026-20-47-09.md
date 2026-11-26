# Givens order and reciprocal syndrome charts

## Chemistry

The Givens schedule can move a rotation across gates on disjoint
orbital pairs. The search moves the corresponding angle columns with
the tree edges. It ranks the XOR transitions between five-word loader
batches by the sum of the mixed high–low coefficient ranks. The proxy
holds the low monomials fixed and omits cross-term pairing and workspace.

The registered control used the 1,219-row public seven-bit table
and the pinned ThemBones groups compiler. It completed **78,016**
official chemistry trajectories at **405 qubits**, with **3,634**
loader Toffolis per pass and cost **261.596M**. The full source-compiled
control is distinct from the previously measured **249.170M** public
circuit with 3,307 Toffolis per pass.
[Native control](evidence/aggregate36-20261126/chem-tree-order/native-control.json)
· [Earlier public comparison](above-34-cloud-reference-comparison-26-11-2026-06-31-00.md)

Each of the two 1,600-proposal searches retained a genuinely changed
schedule at the same mixed rank of **5,805**. The source emission priced
the affected transitions at **two and three additional Toffolis per pass**.
An exhaustive one-move screen of all **64** disjoint adjacent pairs
also found no reduction. Its cheapest move added **one Toffoli** and
passed the compiler's exact endpoint check on the affected slots.
The changed families lack a complete native receipt and neither source
screen qualified a candidate for cloud verification.
[Matched source emission](evidence/aggregate36-20261126/chem-tree-order/matched-source-pricing.json)
· [Adjacent-swap screen](evidence/aggregate36-20261126/chem-tree-order/adjacent-source-pricing.json)

## DQI

One Astra 6.2 investigation considered a structured Hankel approach
and a second Euclidean chart. Coefficientwise expansion of a degree-35
monic three-term recurrence takes 1,156 scalar field products per
direction even with all recurrence coefficients supplied. At rank 42
the paired expansion alone charges **97,104 gates** before deriving
those coefficients. The estimate applies to coefficientwise expansion.
Balanced polynomial multiplication would need a separate reversible
layout and cost measurement.

Reversing the 70 syndrome words maps a support point (x) to
(x^{-1}) and its error value (e) to (ex^{71}), using the repo's
(S_j=\sum e x^j) convention for (1\le j\le70). Reversal is a
fixed wire relabeling, but a routed circuit would still have to select
the chart coherently and repay the transformed value against the
original mask.

The verifier's numerical sampler, run with the repository's software
field table, supplied two 1,024-shot panels. The normalized reciprocal
locator identity held for all 2,048 syndromes. Of the **256** weight-34
and weight-35 cases in scope for the current phase stage, **248** passed
both joint charts, **five** passed only the original chart, and **three**
passed only the reversed chart. The other **1,792** cases had lower
weight, which the fixed phase stage does not cover. The result supports
looking at degree routing before spending gates on an extra high-weight
orientation. The best full cloud comparison remains **33.20483975**.
[Paired chart counts](evidence/aggregate36-20261126/dqi-reversed-charts-windows.json)
