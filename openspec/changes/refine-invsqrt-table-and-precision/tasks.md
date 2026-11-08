## 1. Control and cost model

- [x] 1.1 Rebuild the current certified control byte for byte. Record its exchange rate `C / Q`.
- [ ] 1.2 Implement `src/qcompile/invsqrt/costmodel.py` with per-stage predictions.
- [ ] 1.3 Calibrate against v1, v2, v3 and all recorded screen attempts. Require Toffoli-like counts within 2% and exact declared width. Record residuals.

## 2. Rounding and widths

- [x] 2.1 Implement the per-segment ±2-ulp integer search using the exact emitted recurrence. Keep the search deterministic and record the chosen offsets.
- [x] 2.2 Rerun the full-domain model for the searched 29/21/14 table. Confirm it does not raise worst tolerance use.
- [ ] 2.3 Run the single-width ladder `28/21/14`, `29/20/14`, `29/21/13`, then the best passing combination. Apply the search before declaring a failure.
- [ ] 2.4 Emit and native-check the best passing table. Record cost against the control.

## 3. Signed-digit rows

- [x] 3.1 Write the radix-4 recurrence into the integer model, including sign extension and column truncation. Rerun the full domain.
- [ ] 3.2 Implement the digit decoder and signed row primitive. Prove phase correctness for every measurement branch.
- [ ] 3.3 Price the variant with the cost model. Emit only if it predicts at least 5% lower complete cost.
- [ ] 3.4 Native fixtures, including all digit values at segment edges and powers of four. Add mutation fixtures for a flipped sign and a dropped carry-in.

## 4. Phase bits and rotations

- [x] 4.1 Model dropping the lowest phased bits with the margin-dependent rotation charge. Record the optimum.
- [x] 4.2 Reclassify any exact quarter- or eighth-turn angles. Emit only if the combined Stage D change lowers cost.

## 5. Model-only screens

- [x] 5.1 Model the two-octave table, including the extra controlled rows. Close it with the recorded result unless it predicts at least 3%.
- [x] 5.2 Model load-as-you-go `c2` using the traced peak location. Close it with the recorded result unless it predicts at least 3%.
- [x] 5.3 Refine the optimistic two-octave result with the real address-selection cost and a fitted table; verify the full-domain margin before ranking it.

## 6. Compact tranche (separate registration)

- [x] 6.1 Register the 40-hour tranche with the 100-qubit, 2,000-Toffoli-equivalent target.
- [ ] 6.2 Model the phase-accumulation design and the gated signed-digit rows. Emit a prototype only if the model beats the current control by at least 20%.

## 7. Verification and archive

- [x] 7.1 Combine passing variants under the parent rule. Require at least 5% lower measured cost than the control.
- [x] 7.2 Full 200,540,928-trajectory pass and fresh confirmation on identical bytes. Paired archive run with other members retained by hash.
- [ ] 7.3 Record the external receipt. Run WSL tests, Pyright, Ruff and strict OpenSpec validation. Publish a dated change log.
