## Why

The v3 circuit spends its 3,202 Toffoli-like gates in four places:
coefficient lookup and unlookup, binary normalization and denormalization
shifts, 52 controlled Horner rows, and 36 fine rotations. Its uniform
384-row minimax quadratic uses 71.96% of the phase tolerance at widths
29/21/14. The 28/20/13 step failed. The remaining levers are smaller
than DQI or chemistry, but they are cheap to verify exhaustively.

- Coefficients are rounded to nearest. A per-segment search over nearby
  integers can lower the emitted error and free bits on the next width step.
- The ladder moved all three widths together. Single-width steps were not tried.
- Each Horner stage uses one controlled row per bit of `t`. Radix-4
  signed digits halve the number of rows, at a higher cost per row.
- Every phased output bit is a fine rotation priced by the remaining margin.

## What Changes

- Add a calibrated stage cost model, so variants are ranked before emission.
- Add lattice-aware coefficient rounding and a single-width precision ladder.
- Add radix-4 signed-digit Horner rows as a separately registered variant.
- Screen phased-bit and rotation trade-offs against the margin-dependent price.
- Screen two-octave geometry and load-as-you-go coefficients in the model
  only, and close them unless the model predicts a gain.
- Register a timeboxed compact-architecture tranche toward 100 qubits and
  2,000 Toffoli-equivalents.

## Impact

- Code: `src/qcompile/invsqrt/{minimax.py, direct.py, direct_screen.py}`,
  `tools/invsqrt_direct.py`, a new `src/qcompile/invsqrt/costmodel.py`.
- The control is whichever circuit `reduce-invsqrt-declared-width` certifies,
  or v3 if that change does not qualify.
- Each variant changes the emitted arithmetic. The exhaustive 3,133,452-input
  model stays the correctness gate.
