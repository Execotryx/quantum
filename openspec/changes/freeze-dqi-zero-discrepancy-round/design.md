## Resolution

The code is right. The counter increments on every non-replace round:

| Case | Condition | `d'` | Branch `b` | History word `W` |
| --- | --- | --- | ---: | --- |
| Zero | `Δ = 0` | `d + 1` | 0 | 0 |
| Retain | `Δ ≠ 0`, `d < 0` | `d + 1` | 0 | `Δ` |
| Replace | `Δ ≠ 0`, `d ≥ 0` | `−d` | 1 | 0 |

The counter has 8 signed bits. Starting at `d = 0`, every round changes
`|d|` by at most one, so `|d| ≤ 70` after 70 rounds.

## Circular state

The native state at the start of round `r` (1-based) is:

- `σ`: 36 words, coefficient `i` in word `i`.
- `P[0..35]`: template words. Coefficient `i` of `τ` lives in
  `P[(i + o_r) mod 36]`, with `o_1 = 0` and `o_{r+1} = o_r − 1 (mod 36)`.
- `d`: the counter. `W`: the history word, zero at forward start.

The shifted view is `T_i = P[(i − 1 + o_r) mod 36]`, so
`T₀ = P[(o_r − 1) mod 36]`, the word holding `τ₃₅`.

`bm_circular.py` implements `step_circular(state, syndromes, r, field)`
and `reverse_circular(...)` on this state. Use `discrepancy` from
`bm_reference` over `i ≤ min(r − 1, 35)`, and the routed arithmetic of
`bm_routed.step` on the view `T`.

- `step_circular` raises `UnsupportedRound` when `Δ ≠ 0` and `T₀ ≠ 0`.
  The correctable domain never reaches this case (see below).
- It never raises when `Δ = 0`, whatever `T₀` is.

Equivalence with the unbounded model: for every state reached from
`State((1,), (1,), 0)` on a correctable syndrome, the circular `P` equals
the unbounded `τ` folded by `fold(τ)[k] = Σ_{i ≡ k (mod 36)} τ_i`, placed
by the offset map. On correctable inputs no two nonzero coefficients share
a fold class, because `τ = z^age · base` with `deg base ≤ 35`.

## Frozen expected states

| Case | Forward output | Reverse input → output |
| --- | --- | --- |
| Zero, `T₀ = 0` | `σ' = σ`; `P` unchanged; offset `o_r − 1`; `d + 1`; `b = 0`; `W = 0`; scratch 0 | `(σ', P, d + 1, b = 0, W = 0)` → input state, scratch 0 |
| Zero, `T₀ ≠ 0` | Same as above. `T₀` is never read with a nonzero multiplier. | Same as above |
| Retain, `T₀ = 0` | `σ' = σ + α·T` with `α = Δ·σ₀`; `P` unchanged; offset `o_r − 1`; `d + 1`; `b = 0`; `W = Δ` | `(σ', P, d + 1, b = 0, W = Δ)` → input state with `W = 0` |
| Replace, `T₀ = 0` | `σ' = T + α⁻¹·σ`; view `T` now holds `σ`; offset `o_r − 1`; `−d`; `b = 1`; `W = 0` | `(σ', P', −d, b = 1, W = 0)` → input state |

Why the `T₀ ≠ 0` zero case is clean in the native round. `Δ = 0` gives
`b = 0` and `α = Δ·σ₀ = 0`.
- `inverse_xor(0)` is 0, and the routed update adds `0·T_i` to every word.
- `_select_old_constant` with `replace = 0` uses only `σ₀`.
- `_replace_discrepancy` is controlled by `b = 0`.
- `_retain_history` writes `Δ = 0`.

No gate reads `T₀` with a nonzero factor.

Why `Δ ≠ 0` with `T₀ ≠ 0` is unreachable on the domain: a nonzero `T₃₆`
at an active update would force the new locator above degree 35. See
the [virtual template note](../../../docs/dqi-virtual-template-08-11-2026-15-15-21.md).
Task 1.3 checks this on samples.

## Fixture file

`tests/fixtures/dqi_round_states.json` holds, for registered seeds:

1. Three full `(4095, 70)` sampled inputs and the all-zero syndrome (weight
   0). For each round: `r`, case, `o_r`, `d`, `b`, `W`, SHA-256 of `σ`, and
   SHA-256 of `P`, from `step_circular`.
2. Twelve synthetic single-round states at active widths `a_r ∈ {3, 12, 36}`,
   one per case in the table, with random field words. `T₀ ≠ 0` is used
   only in the zero rows.

Record the fixture file's SHA-256 in the change log. The file is
generated once and never regenerated.

## Native fixtures

For each synthetic state, run the generalized round forward and
`adjoint=True` on the native backend. Compare every register with the
frozen state. Every allocated scratch qubit must be zero at the end.
Mutation: forcing `d` unchanged on a zero round must fail the comparison.
