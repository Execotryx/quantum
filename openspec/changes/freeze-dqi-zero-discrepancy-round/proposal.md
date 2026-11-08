## Why

The previous DQI change contradicts the code on zero-discrepancy rounds.

- `bm_routed.step` returns `State(σ, z·τ, d + 1)` when `Δ = 0` (line 47).
- The native `_counter_step` applies `d → d + 1` whenever the branch bit
  is 0, which includes `Δ = 0`.
- The requirement "Circular template with classical offset" in
  `assemble-routed-bm-direct-forney-decoder` said a zero-discrepancy round
  leaves "the locator, template words, counter and scratch" equal to their
  relabeled inputs. That means an unchanged counter, which is wrong.

The counter must increment. It is the BM length bookkeeping, and the next
replace decision reads its sign. Expected states must also be frozen for
the circular layout when the wrapped template word `T₀` is nonzero. The
classical model cannot express that case: `_unshift` raises on a nonzero
constant.

## What Changes

- Correct the requirement: a zero-discrepancy round increments the counter.
- Add a classical circular model that matches the native 36-word layout.
- Freeze forward and reverse expected states for all four round cases as
  JSON fixtures, including `Δ = 0` with `T₀ ≠ 0`.
- Add native fixtures that compare the generalized round with the frozen states.

## Impact

- Supersedes the zero-discrepancy scenario in
  `assemble-routed-bm-direct-forney-decoder`. That change cannot complete
  task 2.2 until this change is done.
- Code: new `src/qcompile/dqi/bm_circular.py`, new
  `tests/fixtures/dqi_round_states.json`, native tests.
