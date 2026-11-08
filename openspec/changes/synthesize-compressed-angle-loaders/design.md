## Inputs and constraints

- An eligible factorization: strict NPZ, the decoded word table of
  `A = 76 + R·B` rows by 75 angles at `brot` bits, tree edges and pinned metrics.
- `ceil(75 / J)` ANGLE circuits with contiguous `angle_k_*` indices,
  identical register maps (`selection`, `word_j`), no `Z_POW`, at most 128
  qubits each, and clean workspace on every address in both directions.
- Coverage `(76 + R·B) · 64` shots. For `(9, 143, 40)` that is 87,232.
- Addresses from `A` to `2^⌈log2 A⌉ − 1` lie outside the verified domain.
  The banked chemistry record already relies on this. Confirm it against
  the pinned verifier before treating those rows as don't-cares.
  [Banked chemistry record](../../../docs/banked-chemistry-07-11-2026-01-52-35.md)

## Stage A — banked unary loader

Generalize the pinned J9 bank construction to any shape, `brot` and `J`.

- Width per circuit: `⌈log2 A⌉` selection + `J · brot` words + unary path
  and bank flags. For `A = 1,363` and `brot = 8` that is `11 + 8J + about 10`,
  so `J ≤ 13` fits the cap.
- Cost per circuit per pass is about `A` plus bank overhead. Total per pass
  is about `A · ceil(75 / J)`.
- Persistent scored width grows by `brot` per extra word. Rank `J` by
  complete cost `λ_eff · T_total · Q_total`, using the pinned cost code
  for every term. Do not rank by ANGLE Toffolis alone.
- Keep the certified J9 tool unchanged as a historical control.

## Stage B — monomial loaders

Each output bit is a Boolean function of the address bits on the valid rows.

1. **Algebraic normal form with don't-cares.** For each circuit, choose
   values on invalid addresses to minimize the union of monomials needed
   across its `J · brot` output bits. Start greedily: Möbius transform,
   then flip don't-cares that remove the most shared monomials. Record the
   monomial count before any circuit work.
2. **Construction.** Split the address into high and low bits (start
   7 high and 4 low for 11 bits). Cache high monomials on qubits. Build
   low monomials in small stages. Form each needed mixed monomial with one
   temporary AND of a cached high and a cached low monomial. Fan it into
   output bits with CNOTs. Erase each product by X-basis measurement with
   a CZ fix-up between its two factors, which are still live, in reverse
   construction order. Cost: one Toffoli-like gate per constructed monomial.
3. **Paired products.** `(h₁ ⊕ l₂)(h₂ ⊕ l₁) = h₁l₁ ⊕ h₂l₂ ⊕ h₁h₂ ⊕ l₁l₂`.
   One AND therefore delivers two mixed terms when the pure terms are
   available to cancel. Pairing is a covering problem over output bits.
   Solve it greedily and record the gain over Stage B2.
4. **Gauge.** Each basis vector's sign is free, because `u uᵀ` is unchanged.
   Changing a row's sign changes its Givens words. Search row signs greedily
   to minimize the monomial count. Confirm that the decoded metrics are
   unchanged.

The public description reports about 4,500 Toffolis per pass for 15
circuits on its own table. Treat that as an external comparator only. A
table without that structure may need far more monomials. Measure the
monomial count of the actual table before committing to Stage B.

## Verification

- For every circuit and every valid address, check forward and reverse:
  exact words, unchanged selection, clean workspace and correct phase.
  Use arbitrary nonzero targets and bank boundaries.
- Mutation fixtures: wrong word bit, wrong don't-care assumption on a valid
  row, missing CZ fix-up, swapped circuit order.
- Complete metric run with the new NPZ and family. Two independent builds.
  Full coverage, then a fresh one-use chemistry confirmation on the
  complete component.

## Promotion

- First admission: complete measured chemistry cost at most half the banked
  incumbent (≤ 1.624×10⁹), with every strict gate and project margin passing.
- Stretch: at most 3.4×10⁸ (about 10×).
- Paired archive with the inverse-square-root and DQI members retained by hash.
