## Numerical contract

Replay the original reference J8 at cost 3,355,599,588.3155375 and
the certified J9 at 3,247,752,448.668952. The latter uses
`R=65, B=60, C=60`, 12-bit angles, 3,976 rows and nine
circuits. Its observed errors are approximately 3.185 and 18.640 mHa;
the gap is approximately 3.965477 Ha. Compare against the raw
[certified chemistry receipt](../../../docs/evidence/invsqrt-direct-hybrid-20261107/benchmark-dfthcsos.json).

Use the pinned `verify.py`, `dfthc_math.py`, `costs_prepare.py`
and `circuits.py`. Both Frobenius residuals after decoding circuit
words must be at most 20 mHa. The strict floors are `Lambda > 49`
and `E_gap > 3.914898` Ha. Require positive
`E_gap * (2 * Lambda - E_gap)`; equality at the upper gap boundary
is rejected by the numerical path. Price
`sqrt(E_gap * (2 * Lambda - E_gap)) * T_total * Q_total`.
The sponsor fixes `KEEP_BITS=10`. The two floor conditions alone
cannot establish a universal positive lower bound for
`lambda_eff`. Any pruning bound on it needs additional stated
assumptions about the feasible gap and normalization.

The NPZ binds `U:(R,B,76)`, `W:(R,B,C)`, `H2_I:(R,C)`,
scalar `H1_I`, `Hsym_lower:(2926,)` and integer
`tree_edges:(75,2)`. NPZ `W` is the set of lowercase weights,
and the identity coefficient is `H2_I - sum_b(W)` in that
convention. Submitted one-body and symmetry shifts are replaced by
the fixed packaged shifts. Include the schema-compliant values,
and fit only parameters the verifier actually uses. The decoded
word table and ordered tree determine the realized vectors.
Reconcile the unit convention `theta/pi = word/2**(brot-1)` and
test parent-before-child rooted tree order.

## Cost and shape screen

| Quantity | Expression or constraint |
| --- | --- |
| ANGLE rows | `A = 76 + R*B` |
| Address width | `ceil(log2(A))` |
| Outer preparation size | `76 + R*C` |
| Inner preparation scale | `R*C*B`, with discrete preparation block sizes |
| ANGLE family size | `ceil(75/J)` |
| Full-strength chemistry coverage | `A * 64` |

For example, `R=10,B=129` gives 1,366 rows and 87,424 shots
regardless of C. The proposed public shape increases B relative
to the incumbent, so rank the complete shape using the real
derived products and resource steps. Use the pinned
`SpinFreeData_V1` model with fixed keep bits. Reconcile
`T_total` as both ANGLE directions, outer and inner preparation,
and Givens rotation cost. Reconcile `Q_total` as persistent
qubits plus the maximum live temporary need among sequential
stages. Keep the actual per-ANGLE 128-qubit cap separate from
the full scored width.

Use a conservative optimistic resource bound at fixed numerical
parameters to prune impossible loader layouts. A drop in
`lambda_eff` from about 49.30 to 47–48 alone saves only a few
percent. The report's 8–10.6× official-reference ratios would
need large TQ reductions and are stretch outcomes.

## Stage A — controls and weight-only pilot

- Extend existing `src/qcompile/chemistry/schema.py` and
  `representation.py` only where needed for verified word encoding,
  shape metadata and deterministic regeneration. Reuse independent
  step-3 residual checks and the pinned evaluator. Add a focused
  `chemistry/refit.py` and `tools/chem_refit.py` only after
  reproducing both control metrics and word tables.
- Begin with fixed two-body vectors, shape and tree. Fit weights
  and identity offsets in the correct native convention. The
  residual depends quadratically on the weights through the
  factorized reconstruction. Use a bounded SciPy pilot with
  tiny-instance finite-difference checks. Rebuild `h1_prime`
  from decoded two-body vectors and updated weights, diagonalize
  it, then regenerate one-body words. Old one-body words are
  valid only if the resulting verified representation agrees.
- Start with one serial pilot, at most two registered seeds and
  about one hour of wall time. Pin an evaluation-count cap after
  timing one objective call, plus memory and checkpoint/storage
  limits. Preserve every trial and its terminal reason. Reject
  nonfinite outputs, shape/schema drift and unresolved disagreement
  with the independent oracles. A proposed post-quantization
  19.5 mHa residual guard is project headroom, not a verifier
  requirement. Register separate gap and normalization margins.

## Stage B — shape and quantization

Shortlist the incumbent shape, a conservative continuation and a few
independently justified compressed shapes based on the official
cost model. Use an explicit warm-start mapping or a registered
independent initializer. Keep continuous fitting separate from
discrete angle moves. Quantize at 12 bits first, then try a
bounded 11, 10, 9, 8-bit ladder if the realized two-body fit
permits it. Reconstruct the decoded two-body vectors before
updating weights or regenerating one-body words. Use the current
tree first and test alternatives as separate ablations. Track
continuous versus decoded errors and gaps independently.

Reject numerical candidates outside official bounds or the
registered margins before native synthesis. Record optimizer
seeds, dtype, source, settings and checkpoint hashes. The primary
method's accelerator timings do not establish feasibility on WSL.
Profile local CPU time and process-tree memory before proposing a
different fitting environment. Keep any fitting-only accelerator
dependencies separate and pinned. Preserve the verifier lock.
[Low et al., fitting method](https://arxiv.org/html/2502.15882v1#S4.SS1) ·
[Sponsor chemistry contract](https://arxiv.org/html/2610.23832v1)

## Stage C — loader, full verification and handoff

Build a shape-generic unary/XOR loader as control. Compare a few
registered `J`/bank layouts satisfying selection + word +
scratch width ≤128. Preserve the historical pinned J9 tool as a
separate control. Its fixed 12-bit address and 12-bit word layout
do not generalize to new shapes. Require identical named register
maps across the candidate family, no `Z_POW`, contiguous ANGLE
indices and exact XOR deltas for forward and reverse traversal.
Try factored or paired-product logic only with its truth table,
declared width and measurement phase-correction proof. Compare
the complete score after synthesis, including any J-induced
changes to preparation and persistent workspace.

Native differential tests cover every valid address and exact
loaded words, arbitrary nonzero targets, bank boundaries and
partial banks, final padding and every circuit boundary in both
directions. Negative fixtures change the weight offset, tree,
units, row order, selection, scratch, phase correction or
padding. Report out-of-range address behavior separately from
verified coverage. Reject any semantic, width or cost regression.

Initial promotion gate is at least 10% lower complete measured
chemistry cost than the banked incumbent. Take at most two
numerically eligible families to full verification in the first
tranche. Freeze NPZ, tree, ANGLE bytes and exact expected coverage,
build independently twice, run the pinned full chemistry verifier
and confirm once on a fresh salt for the same complete component.
After an NPZ or tree change the old chemistry confirmation is
ineligible. Hold other member hashes fixed in this successor and
use shared archive verification.
