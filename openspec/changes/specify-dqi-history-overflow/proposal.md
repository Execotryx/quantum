## Why

The previous DQI change left overflow underspecified. It moved an
overflowing history word into a 12-bit sink and freed it. On a second
overflow the swap returns a nonzero word to the freed register. It did
not say how the push flags are cleared, how the reverse pass behaves, or
what makes the verifier count the shot.

## What Changes

- Replace the per-round history word and the sink with one persistent
  transfer word `W`, `h` tagged entries, a 2-bit occupancy and a 7-bit
  overflow count `K` that is never decremented.
- Define push and pop gate sequences whose flags are cleared by rules that
  read only current register values. The flags are therefore zero on
  every input, overflowed or not.
- Define reverse behavior for a single overflow and for repeated
  overflows. Neither restores the input. `K ≠ 0` at the end makes the
  verifier count the shot as a failure.
- Gate on how the pinned backend treats a freed nonzero qubit.
- Select `h` from 10,000,000 seeded classical samples.

## Impact

- Supersedes the history design, the overflow-sink task and the overflow
  scenario in `assemble-routed-bm-direct-forney-decoder`.
- History width: `20h + 21` qubits (entries `20h`, `W` 12, `K` 7,
  occupancy 2).
- Code: `src/qcompile/dqi/history_stack.py`, new
  `tools/dqi_history_depth.py`.
