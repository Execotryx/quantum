## Target and budget

| Quantity | Target |
| --- | --- |
| Declared width | 900–1,000 qubits (840 syndrome + at most 160 workspace) |
| Mean Toffoli-like | At most 633,199 at 900 qubits, or 512,891 at 1,000 (40× at the reference repetition factor) |
| Correctness | Exact first; bounded variants under the routed lane's pricing rules |
| Admission | At least 1.5× lower cost than the best admitted routed decoder |

## The `(σ, g)` end state

For a decodable syndrome with locator `σ` (`deg σ = w ≤ 35`, `σ₀ = 1`)
and evaluator `ω = σ·S mod z^70` (`deg ω < w`), define
`g = ω · Ψ mod σ` with `Ψ·σ' ≡ 1 (mod σ)`.

- **Storage.** `σ1..σw` and `g0..g_{w−1}` take `2w ≤ 70` words, so they
  fit the bank. Unused words must be provably zero.
- **Phase.** At a root `X_j`, `e_j = g(X_j)` up to the pinned indexing
  factor. The mask phase `Tr(μ(E_j) · g(X_j))` is linear in the bits of
  `g`. With the root flag `ρ_j` it is a CZ between `ρ_j` and a parity of
  `g` bits chosen by the classical mask, which is Clifford.
- **Scan cost.** About 11 Toffoli-like gates per position for the zero
  test, about 45k in total, plus Clifford work.
- **Bijection.** `S ↔ (σ, ω)` is unique for decodable inputs (Padé
  uniqueness), and `ω ↔ g` is invertible modulo a square-free `σ`.
  Prove both for every supported weight 0–35, including how weight `w`
  is encoded and how the transform behaves at `w = 0`.

## Candidate families

| Family | Idea | Main risk |
| --- | --- | --- |
| W1, continued fraction | Euclid on `(z^70, S)` writes quotients over consumed words, so the bank holds remainder plus quotients at constant total length (like the "Dialog" encoding in Khattar et al., arXiv:2510.10967). Then convert quotients to `(σ, ω)` and then `g`. | Variable-degree pointers and the quotient-to-locator conversion width |
| W2, discrepancy domain | Reformulated BM in the style of Sarwate and Shanbhag (IEEE TVLSI 2001) updates `σ·S` in place. The low part ends as `ω`. | Reversibility of each update without per-round history |
| W3, convert at the end | Run the routed locator (with its history and workspace), compute `g`, then transform the bank in place to `(σ, g)` and release the locator registers before the scan. | Peak width occurs before the conversion; may not reach 1,000 qubits |

For each family, write a liveness and information table per stage. It
lists which registers are live, which original data each state determines,
and where every physical id is released. Reject a family at the first
state collision, zero-denominator branch or unproved cleanup.

## Method

1. **Small fields first.** Implement each family as a classical reversible
   program over GF(2⁴) and GF(2⁶) with `n ≤ 12`. Enumerate every
   syndrome. Check bijectivity, restoration and the phase identity
   exhaustively. Measure width and products per stage.
2. **Project.** Scale the measured per-stage counts to `(4095, 70)` with the
   arithmetic primitives from the routed lane. Keep a family only if its
   projection meets the target.
3. **GF(4096), reduced shapes.** Emit kickmix circuits for `(63, 4)` and
   `(127, 12)` and check them against the classical oracles.
4. **Full size.** Run the matched 2,560-shot pair against the best routed
   decoder, then the full verifier, confirmation and paired archive.

## Stop rule

On 8 January 2027, stop unless a full-size candidate has passed the
matched development pair. The routed decoder then stays the DQI component
for the final archives. Keep every family record, including rejections.
