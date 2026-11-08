## Contract and control

Use the pinned `dqi/verify_submission_dqi.py`. The input is 70
little-endian 12-bit syndrome registers `S0`–`S69` (840 qubits, counted in
width) and 4,095 classical mask words `E0`–`E4094`, fresh on every shot.
The circuit applies `(−1)^(Σ_j popcount(e_j ∧ E_j))` for the decoded error
`e`, restores every syndrome and clears all scratch. The field polynomial
is `0x1053`, the correction radius is 35, and `Z_POW` is forbidden. Cost
is `R(ε⁺) · Q² · T`.

| Control | Qubits | Mean Toffoli-like | Cost | Ratio |
| --- | ---: | ---: | ---: | ---: |
| Pinned reference | 1,893 | 5,725,109 | 2.4439×10¹³ | 1.0× |
| Tower products in the reference schedule | 1,893 | 5,433,437 | −5.09% | 1.05× |

Measured primitives: schoolbook product-XOR 144, tower product-XOR 54,
controlled tower product-XOR 66, clean tower inverse-XOR 180, native
inverse scaffold 315, BM update slice 528 at 158 qubits.
[Arithmetic receipts](../../../docs/evidence/advance-hybrid-20261108/dqi/arithmetic.json) ·
[Earlier slices](../../../docs/evidence/next-hybrid-20261108/dqi/slice-comparison.json)

Classical oracles: `qcompile.dqi.decoder` provides BM, EEA and
`recover_forney`, and `qcompile.dqi.field` the GF(4096) arithmetic. Keep
them as the per-stage reference. Never import their outputs into a circuit.

## Stage A — arithmetic

| Primitive | Today | Target | Method |
| --- | ---: | ---: | --- |
| Product-XOR into any target | 54 | 45 | Karatsuba over the quadratic extension: three GF(64) products, each of bilinear rank 15 |
| Product into a fresh register, then erase | 54 + 54 | 45 + 0 | Erase by X-basis measurement and classically conditioned CZ fix-ups |
| Controlled product-XOR | 66 | 57 | Gate one operand (12 ANDs), then the product |
| Clean inverse-XOR, zero to zero | 180 | ≤ 110 | Norm map to GF(64), GF(64) inverse through a GF(8) subtower, two GF(64) products |

1. **Rank search.** Write the GF(64) multiplication tensor in the chosen
   basis and search for a rank-15 decomposition. Use flip-graph random
   walks or a SAT encoding (the method of Barbulescu, Detrey, Estibals and
   Zimmermann, "Finding optimal formulae for bilinear maps", WAIFI 2012).
   Gu et al. report a 15-Toffoli GF(64) multiplier. Verify the
   decomposition exhaustively over all 4,096 GF(64) pairs, then the tower
   product over a registered sample plus all basis pairs. Optionally search
   a direct GF(4096) decomposition below 45. Khattar et al.
   (arXiv:2510.10967, App. C) report 51 in polynomial basis.
2. **Product-XOR.** Each bilinear term `L_k(a) ∧ R_k(b)` is one temporary
   AND. Fan it into the output bits with CNOTs, then erase it by
   measurement. The fix-up phase is a product of CZ gates between linear
   forms, which is Clifford. Cost: exactly the rank in Toffoli-like gates.
3. **Product erasure.** A register holding `a·b` is erased by X-basis
   measurement with outcome `m`. The residual phase `(−1)^(m · (a·b))` is
   a bilinear form in the bits of `a` and `b`. It is applied with CZ gates
   conditioned on `m`, at zero Toffoli cost. Prove this on all basis pairs
   and on random masks. Add a mutation that drops one CZ.
4. **Inverse.** For `a = a0 + a1·y`, compute the norm
   `N = a0² + a0·a1 + ν·a1²` (one GF(64) product plus linear maps), invert
   `N` in GF(64) through GF((2³)²), and form
   `a⁻¹ = ((a0 + a1) + a1·y) · N⁻¹` (two GF(64) products). Erase
   intermediates by measurement where they are single product layers.
   Otherwise reverse them. Test all 4,096 inputs, including zero.
5. Basis changes between `0x1053` polynomial basis and the tower basis are
   fixed linear maps (CNOT only). Apply them once on entry and exit, and
   fold the mask transform `T⁻ᵀ` into the classical side.

## Stage B — exact routed BM locator

Emit 70 unrolled rounds. Use the standard BM recurrence (Blahut form) as
the classical reference:

```text
Δ_r = Σ_{i ≤ min(L, 35)} σ_i · S_{r−i}
retain  (Δ_r = 0 or 2L > r − 1):  σ ← σ − Δ_r · z·τ,   τ ← z·τ
replace (Δ_r ≠ 0 and 2L ≤ r − 1): σ ← σ − Δ_r · z·τ,   τ ← Δ_r⁻¹ · σ_old,   L ← r − L
```

Gu et al. rescale the replace branch so both branches share one
multiply-subtract. A controlled swap routes `σ ↔ z·τ`, and the shared
update uses `α = Δ·σ₀` on retain or `α⁻¹` on replace. The invariant
`σ₀·δ = 1` removes the stored previous discrepancy. The result is a
scalar multiple of the locator. Forney's ratio `ω/σ'` and the product
`ω·Ψ` are invariant to that scale. Re-derive this rescaling under this
project's syndrome indexing, and prove each round's map and inverse
against the classical oracle before emitting it.

Per-round work (estimates with 45-gate products):

| Step | Products | Other | Toffoli-like |
| --- | ---: | --- | ---: |
| Discrepancy `Δ` | up to 36 | XOR accumulation | ≤ 1,620 |
| `α = Δ·σ₀`, inverse, branch select | 1 + inverse | zero test 11, `L` comparison about 6, 12 CSWAPs | ≤ 190 |
| Routed swap `σ ↔ z·τ` | — | up to 432 CSWAPs over active words | ≤ 432 |
| Shared multiply-subtract | up to 36 | — | ≤ 1,620 |
| `L` update, history write | — | 6-bit controlled subtract, history CSWAPs | ≤ 40 |

Only coefficients up to `min(r, 35)` can be nonzero, so early rounds are
cheaper. Derive exact static degree bounds per round from the recurrence.
Never use probabilistic cutoffs in this stage. Forward-locator estimate:
150k–300k. Reverse locator: the same again.

**Reversal history (exact).** Each round's inverse needs its branch bit.
Retain rounds with `Δ ≠ 0` also need `Δ`, unless it can be decoded from
the registers. Gu et al. decode the previous discrepancy on replace
rounds from constant coefficients, `δ_old = σ₀·τ₀⁻¹·δ_new`. Build a
liveness table per branch type that shows the information needed for
inversion. Then price two exact layouts:

| Layout | Extra qubits | Notes |
| --- | ---: | --- |
| Static slots: 70 branch bits and a 12-bit slot per round | 910 | Simple addressing; slots unused on replace and zero rounds |
| Stack: 35 entries of 12 + 7 bits plus a pointer | about 671 | Push and pop cost controlled swaps; worst case is exact |

Choose by complete projected cost, including the Q² penalty.

## Stage C — exact phase-only scan

Run this after the forward locator, with the syndromes still live.

1. **Evaluator.** `ω = σ·S mod z³⁵`, about 630 products into a 35-word
   register. Optionally form it in place over `S1..S35` and zero
   `S36..S70` as workspace, as Gu et al. do. Do that only with a bijection
   proof and an exact restore path.
2. **Reciprocal.** `Ψ` with `Ψ·σ' ≡ 1 (mod σ)`. In characteristic 2,
   `σ = E(z)² + z·O(z)²` and `σ' = O(z)²`. Gu et al. compute `Ψ` with a
   half-degree extended Euclid of degree at most 17, about 44k Toffolis
   per direction.
3. **Per position `j = 0..4,094`, root `X_j` from the pinned convention**
   (see `recover_forney`):
   - Evaluate `σ(X_j)`, `ω(X_j)` and `Ψ(X_j)` with CNOT-only
     constant multiplications. Maintain `g_i = c_i·X_jⁱ` registers updated
     by a fixed multiplication per step. After 4,095 steps they return to
     their start, because `X^4095 = 1`.
   - Zero test of `σ(X_j)`: 11 temporary ANDs give the root flag, erased by
     measurement.
   - Mask transform: `a' = A(E_j)ᵀ · ω(X_j)`, a CNOT network conditioned on
     the classical mask bits. It costs zero Toffolis and is reversed after use.
   - Phase: 12 three-qubit CCZ gates on (root flag, `a'_i`, `Ψ_i(X_j)`).
     This applies `(−1)^Tr(μ(E_j) · ω(X_j) · Ψ(X_j))`.
   - Cost: 23 Toffoli-like gates per position, about 94k in total.
4. **Equivalence proof.** Show that
   `popcount(e_j ∧ E_j) mod 2 = Tr(μ(E_j) · e_j)` with the trace-dual basis
   already in `tower.py`. Show that `e_j = ω(X_j)·Ψ(X_j)` up to the pinned
   indexing factor. Check against `recover_forney` on all weights 0–35.
5. **Degenerate inputs.** Weight 0 (`σ` constant, `σ' = 0`) applies no
   phase. Define and test the behavior, so that every supported input
   restores cleanly.

Expect tens of millions of Clifford gates per shot. Measure serialized
size, verifier wall time and peak memory at every shape.

## Stage D — assembly and exact promotion

Order: basis change, forward locator, evaluator, reciprocal, scan, then
the reverse of the reciprocal, evaluator and locator, then the inverse
basis change.

| Projection (estimate) | Qubits | Mean Toffoli-like | Ratio | Aggregate factor |
| --- | ---: | ---: | ---: | ---: |
| Exact, static slots | about 2,650 | 0.55–0.80M | 3.6–5.3× | ×1.53–1.74 |
| Exact, stack history | about 2,450 | 0.55–0.80M | 4.3–6.2× | ×1.62–1.84 |
| Bounded history (Stage E), priced at a 4% failure penalty | about 1,800 | 0.45–0.65M | 9–13× | ×2.1–2.4 |

Ratios use `(5,725,109 / T) · (1,893 / Q)²` at the reference repetition
factor. The coefficient registers are updated in place during the scan,
so the scan adds no persistent width.

1. Verify reduced shapes `(63, 4)` and `(127, 12)` against the classical
   oracle on every supported weight. Add mutation fixtures for a flipped
   branch bit, a dropped history entry, a wrong mask bit and a missing CZ.
2. Run the matched 2,560-shot development pair against the reference at
   full size on identical cases.
3. Admission: an exact decoder with zero value and phase errors and a
   measured full-size cost at most half the reference. Record 8× as the
   stretch checkpoint.
4. Freeze, then run the full 102,400-shot verifier and a one-use
   fresh-salt confirmation on identical bytes. Then a paired archive with
   the inverse-square-root and chemistry members retained by hash.

## Stage E — bounded-history lane (separate registration)

Open only after Stage D admits an exact decoder.

- Allocate one 19-qubit history entry. Gu et al. report that a second
  entry is needed with probability about 1.0×10⁻⁴.
- Add per-round coefficient cutoffs chosen by classical simulation of BM
  on the verifier's own sampled distribution (`ProblemSpecDQI.sample_shots`).
  Gu et al. report a combined failure probability of 1.4×10⁻⁴.
- Define the behavior on exhausted bounds, and prove cleanup on those paths.
- Accept a truncation only if it removes at least 2 qubits or about 1,500
  mean Toffoli-like gates per expected failing shot. At about 1,800 qubits
  one qubit is worth about 0.11% of cost and one failure about 0.29%.
- Measure on at least five salts. Price at `k_max + 2` failures under
  `harden-kaggle-operations`. Promote only if the priced cost beats the
  exact decoder by at least 1.5×.

## Not in scope

- Inversionless BM. It roughly doubles update products and breaks the
  `σ₀·δ = 1` invariant. Revisit only if the measured inverse dominates.
- Width below about 1,800 qubits. That belongs to `compress-dqi-decoder-width`.
- Third-party KMB bytes, generators or the `andigu/uncompute` circuit.
  Their contract also differs (polynomial `0x10EB`, fixed mask).
