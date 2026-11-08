## Contract and control

Use the pinned DQI verifier: syndromes `S0`–`S69` (840 qubits), classical
masks `E0`–`E4094`, field `0x1053`, radius 35, no `Z_POW`, cost
`R(ε⁺) · Q² · T`. The contract samples weights 0–35 with the principal
eigenvector weights. The control is the pinned reference: 1,893 qubits,
mean 5,725,109.314 Toffoli-like gates on the matched 2,560-shot case
set, cost 2.4439×10¹³.

## Register layout (target)

| Register | Qubits | Lifetime |
| --- | ---: | --- |
| Syndromes `S1..S70` (`S1..S35` hold `ω` after the evaluator) | 840 | Whole circuit |
| Locator `σ`, 36 words | 432 | Whole circuit |
| Template `τ`, 36 physical words, circular | 432 | Whole circuit |
| Signed counter `d` | 8 | Whole circuit |
| Branch bits `b_1..b_70` | 70 | Round `r` forward to round `r` reverse |
| History (see `specify-dqi-history-overflow`): `h` tagged entries, 2-bit occupancy, 12-bit transfer word `W`, 7-bit overflow count `K` | `20h + 21` | Whole circuit |
| Round transient (`Δ`, inverse, history word, zero flag, inverse scratch) | about 100 | One round |
| Scan workspace | about 90 | Scan only |

Target peak: at most 1,950 declared qubits.

## Step 1 — history depth `h`

Run the classical routed recurrence (`qcompile.dqi.bm_routed`) on
10,000,000 inputs from the pinned sampler (`sample_shots`) with registered
seeds. Record per input the number of rounds with `Δ ≠ 0` on retain, and
per round the maximum locator degree. Choose `h` as the smallest value in
{1, 2, 3} whose empirical overflow rate is at most `1e-6`, and `h = 3` if
none qualifies. Check that the sampled per-round degree never exceeds
`min(r, 35)`. A violation stops this change.

## Step 2 — full-width round

Generalize `round_with_counter` (`bm_counter_round.py`) to active width
`a_r = min(r, 35) + 1` words at round `r = 1..70`. The discrepancy uses
`σ_i · S[r − 1 − i]` for `i ≤ min(r − 1, 35)`, which gives 1,890 products
over 70 rounds. The update and routing use all `a_r` words, which gives
1,925. Both bounds come from the recorded degree bounds
`deg σ_r ≤ r` and `deg τ_r ≤ r`, capped at 35 on the correctable domain.

- **Template view.** Coefficient `i` of `τ` at round `r` lives in physical
  word `P[(i + o_r) mod 36]`, with classical offset `o_1 = 0` and
  `o_{r+1} = o_r − 1 (mod 36)`. The shifted template `T = z·τ` is the
  list `P[(i − 1 + o_r) mod 36]` for `i < a_r`. No data moves for the shift.
  Retain and zero rounds leave `T` as `τ'`. The routed swap writes `σ_old`
  into the same view on replace.
- **Wrapped constant.** `T_0` is the word holding `τ_35`. On every round
  with `Δ ≠ 0` in the correctable domain it is zero (proof in
  [virtual template](../../../docs/dqi-virtual-template-08-11-2026-15-15-21.md)).
  On zero-discrepancy rounds it may be nonzero. Expected states for every
  round case, including `Δ = 0` with `T_0 ≠ 0`, are frozen by
  `freeze-dqi-zero-discrepancy-round`. A zero round increments the counter.
- **Branch.** Allocate a fresh `b_r` per round and keep it until the
  reverse of round `r`, as `round_with_counter` requires.
- **History.** Pass the persistent transfer word `W` as `history` every
  round. Push after each forward round and pop before each reverse round
  with the sequences F1–F8 and R1–R3 of `specify-dqi-history-overflow`.
  That change also fixes `h` and the overflow accounting.
- **Counter.** Eight signed bits; `|d| ≤ 70`. Zero and retain rounds apply
  `d + 1`, replace applies `−d`.

## Step 3 — scaled in-place evaluator

The routed locator has a nonzero constant `σ_0` (invariant `σ_0·δ = 1`) but
is not normalized. Compute `ω_i = Σ_{j=0}^{i} σ_j · S_{i−j+1}` for
`i = 0..34` in place over `S_{i+1}`:

1. `c ← σ_0⁻¹` into a clean word (subtower inverse, 102).
2. For `i = 34` down to `0`:
   - `p ← σ_0 · S_{i+1}` into a clean word (54).
   - `S_{i+1} ⊕= c · p`, which clears `S_{i+1}` (54).
   - Relabel `p` as the `S_{i+1}` slot and free the cleared word.
   - `S_{i+1} ⊕= Σ_{j=1}^{i} σ_j · S_{i−j+1}` (`i` products). Descending
     order keeps `S_1..S_i` original.
3. Clear `c` with the inverse primitive (102).

Products per direction: 595 + 70. Toffoli-like gates per direction: about
36,100. The reverse runs the steps in ascending order.

## Step 4 — scan

Call `direct_scan` (`direct_forney.py`) with the 36-word locator and
`ω = S1..S35` over all 4,095 positions. It costs 227 Toffoli-like gates
per position, 929,565 in total. The scan supports arbitrary nonzero
locator scale and weight 0.

## Step 5 — assembly

Order: rounds 1..70 forward, evaluator, scan, evaluator reverse,
rounds 70..1 reverse. Free branch bits in reverse order.

| Stage | Toffoli-like (estimate) |
| --- | ---: |
| Locator forward: 3,815 products, about 600 fixed per round, routing swaps | about 276,000 |
| Evaluator forward | about 36,000 |
| Scan | 929,565 |
| Evaluator reverse | about 36,000 |
| Locator reverse | about 276,000 |
| **Total** | **about 1,553,000** |

At 1,920 qubits and the reference repetition factor, the ratio is about
`(5,725,109 / 1.553M) · (1,893 / 1,920)² ≈ 3.6×`.

## Verification

1. Reduced shapes `(63, 4)` and `(127, 12)` against `decoder.py` oracles,
   every supported weight, random masks, input restoration and scratch.
   Mutations: flipped branch bit, wrong tag constant, dropped history swap,
   wrong mask bit.
2. The single- and repeated-overflow fixtures of
   `specify-dqi-history-overflow`.
3. Full size `(4095, 70)`: emit once, record width, static counts,
   serialized size, emission time and memory. Run the matched 2,560-shot
   development pair against the reference on the cloud VM.
4. Five registered salts at 102,400 shots each. Price at `k_max + 2`
   failures under `harden-kaggle-operations`.
5. Freeze bytes. Full verifier, one-use fresh-salt confirmation, paired archive.

## Promotion

Zero value and phase errors on the matched development pair. Priced cost
at most `1.2220×10¹³` (2× better than the reference). Expected about
`6.8×10¹²` (about 3.6×).
