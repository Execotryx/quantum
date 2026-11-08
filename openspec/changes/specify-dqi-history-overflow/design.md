## Registers

| Register | Width | Lifetime |
| --- | ---: | --- |
| Entries `E_1..E_h`: `Δ` (12), tag (7), valid (1) | `20h` | Whole circuit |
| Occupancy `occ` | 2 | Whole circuit |
| Transfer word `W`, passed as `history` to every round | 12 | Whole circuit |
| Overflow count `K`, incremented only | 7 | Whole circuit |
| Flags `p`, `o`, `c_1..c_h`, and comparison temporaries | `h + 2` plus temporaries | One push or pop |

`[X ≠ 0]` is a 12-bit zero test (11 temporary ANDs, erased by
measurement). `[occ = j]` and `[tag = r]` compare with classical
constants (temporary ANDs, erased by measurement). Each bracket is
computed into a temporary, used once as a control, then erased.

## Forward push after round `r`

`round_with_counter` has written `W = Δ` on a retain with `Δ ≠ 0`, and
left `W = 0` otherwise.

| Step | Operation |
| --- | --- |
| F1 | `p ⊕= [W ≠ 0]` |
| F2 | `o ⊕= p ∧ [occ = h]` |
| F3 | For `e = 1..h`: `c_e ⊕= p ∧ [occ = e − 1]`. Under `c_e`: `E_e.Δ ⊕= W`, then `W ⊕= E_e.Δ`, `E_e.tag ⊕= r`, `E_e.valid ⊕= 1` |
| F4 | For `e = 1..h`: `occ += 1` under `c_e` |
| F5 | For `e = 1..h`: `c_e ⊕= E_e.valid ∧ [E_e.tag = r]` |
| F6 | `K += 1` under `o` |
| F7 | `o ⊕= [W ≠ 0] ∧ [occ = h]` |
| F8 | `p ⊕= [W ≠ 0] ⊕ OR_e (E_e.valid ∧ [E_e.tag = r])` |

Why each flag returns to zero, using only current values:

- **F5.** After F3, an entry has tag `r` exactly when it was written in
  this push. Earlier rounds wrote smaller tags.
- **F7.** Overflow leaves `W ≠ 0` and `occ = h`. A push leaves `W = 0`.
  When `p = 0`, `W = 0`.
- **F8.** Exactly one term holds when `p = 1`: `W ≠ 0` (overflow) or one
  tagged entry (push). Neither holds when `p = 0`.

These rules hold even when `W` already carries garbage from an earlier
overflow, because they test the values present after F3–F6.

## Reverse pop before reverse round `r`

| Step | Operation |
| --- | --- |
| R1 | For `e = 1..h`: `c_e ⊕= E_e.valid ∧ [E_e.tag = r]`. Under `c_e`: `W ⊕= E_e.Δ`, `E_e.Δ ⊕= W`, `E_e.tag ⊕= r`, `E_e.valid ⊕= 1` |
| R2 | For `e = 1..h`: `occ −= 1` under `c_e` |
| R3 | For `e = 1..h`: `c_e ⊕= [W ≠ 0] ∧ [occ = e − 1]` |

Then `round_with_counter(..., history=W, adjoint=True)` consumes `W`.

On a non-overflow input, entries fill in order and pop in reverse order.
After R1–R2, `W = Δ ≠ 0` and `occ = e − 1` for the popped entry, so R3
clears `c_e`. When nothing pops, `W = 0` and every term is zero.

## Overflow behavior

| Situation | Forward | Reverse | Final state |
| --- | --- | --- | --- |
| No overflow (at most `h` retained nonzero `Δ`) | Every `Δ` moves into a tagged entry; `W = 0` after each push | Tags pop each `Δ` at its own round | Inputs restored, all scratch zero, `K = 0` |
| Single overflow at round `r₀` | `W` keeps `Δ_{r₀}`; `K` becomes 1, and rises again in later rounds while `W ≠ 0` and `occ = h` | No entry has tag `r₀`. Later reverse rounds receive `W ≠ 0` as history, so their adjoints are wrong | Inputs not restored; `K ≥ 1` |
| Repeated overflows | Later retains XOR further `Δ` values into `W`; `K` counts each overflow round | Same as above | Inputs not restored; `K ≥ 2` |

`K` never wraps. After the first overflow `W` stays nonzero, so each later
round can also count as an overflow. `K` therefore rises by at most 70,
and 7 bits hold 127. `K` is never decremented. On any input with an overflow, `K ≠ 0` at
the end. The pinned verifier requires every non-input qubit to return to
zero, so it counts that shot as a value error. A single overflow is not
restored. Restoring it would need another tagged entry, which is what `h`
already sizes.

## Freed nonzero qubits

On overflow inputs, per-round transients inside `round_with_counter` (for
example `delta` and `old_constant`) can be freed while nonzero. Before any
emission, run one native fixture: a two-qubit circuit that frees a qubit
holding 1 on half of its inputs, through the pinned DQI verification path.

- If the backend reports per-shot value errors and completes, continue.
- If it aborts or raises, stop this change and record the result. No
  alternative layout is designed within this change.

## Selecting `h`

1. Register base seed `s₀` and 100 chunks of 100,000 samples, chunk `i`
   seeded `s₀ + i`. Draw inputs with the pinned
   `api.sample_shots(spec, tables, rng, 100000, weights)` from the DQI
   distribution (weights 0–35).
2. For each input, run `bm_routed.forward`. Record:
   - `n_ret`, the count of rounds with `History(False, Δ ≠ 0)`;
   - `max_r deg σ_r − min(r, 35)`;
   - for every round with `Δ ≠ 0`, `deg(z·τ) ≤ 35` (the wrapped-word condition).
3. Stop the change if any locator degree exceeds `min(r, 35)`, or if any
   active round has `deg(z·τ) > 35`.
4. For `h = 1, 2, 3`, count inputs with `n_ret > h`. Choose the smallest
   `h` whose count is at most 10 (a rate of at most 1e-6). If none
   qualifies, `h = 3`.
5. Record the full `n_ret` histogram, wall time and chunk hashes.

Compute: about 3 ms per input in Python (estimate) is about 8.3 CPU-hours.
Run the 100 chunks on 16 workers.

## Fixtures

1. **No-overflow push and pop.** Native fixtures at `h = 1, 2, 3` with
   retains at rounds `r₁ < r₂ < r₃`. All registers restored and all flags zero.
2. **Single overflow.** `h + 1` retains. All flags zero after every push
   and pop, `K` at the end equal to the number of rounds with `W ≠ 0` and
   `occ = h` in the classical trace (at least 1), and the verifier reports the shot as a value error.
3. **Repeated overflow.** `h + 3` retains. Flags zero, `K` equal to its classical trace count (at least 3), value error.
4. **Mutations.** Skip F5, swap tag constants, skip R3. Each must fail.
