## Control

Use the current certified inverse-square-root circuit. Today that is v3:
159 qubits, 3,202 Toffoli-like gates, 36 fine rotations, cost 548,860.92,
minimax quadratic, `segment_bits = 7`, widths 29/21/14, binary
normalization and measurement unlookup. If `reduce-invsqrt-declared-width`
certifies a narrower circuit first, rebuild that circuit as the control
and recompute the exchange rate `C / Q`.
[v3 attempt record](../../../docs/evidence/advance-hybrid-20261108/invsqrt/attempt-combined-v3.json)

## Stage A — calibrated cost model

Add `src/qcompile/invsqrt/costmodel.py`. It predicts Toffoli-like gates,
fine rotations, declared width and complete cost from the format
parameters, without emitting a circuit.

| Stage | Model inputs |
| --- | --- |
| Coefficient lookup | Valid address rows (384 today), unary-iteration tree shape |
| Measurement unlookup | Repair banks for the `low_bits` split, monomial workspace |
| Binary count and shifts | `n_p`, count width, lane widths, output width |
| Horner rows | Rows per stage, operand and target widths per row, gating cost |
| Phase | Phased output bits, Clifford and T angles, fine rotations, margin |

Calibrate against the emitted counts of v1, v2 and v3 and the screen's
other attempts. Require the model to predict each emitted Toffoli-like
count within 2% and each declared width exactly before using it to rank.
Record the residuals.

## Stage B — lattice-aware rounding and single-width steps

1. For each of the 384 segments, search the integer box within ±2 units
   in the last place around each rounded minimax coefficient
   (125 candidates per segment). Evaluate each candidate with the exact
   emitted-arithmetic recurrence over every input that selects the segment,
   at every reachable scale. Keep the candidate with the lowest worst
   tolerance fraction, breaking ties by the larger minimum margin.
2. Run the single-width ladder from 29/21/14:
   `28/21/14`, `29/20/14`, `29/21/13`, then any passing pair combined.
   Apply step 1 at each width before declaring a failure.
3. Rerun the full 3,133,452-input model for every passing table. Keep
   the worst-error and minimum-margin witnesses separately.

Each removed bit of the first coefficient removes one output qubit and
one column from the outer rows. Each removed bit of `c1` or `c2` narrows
one register and its rows. Expected gain is 1–3% if one or two bits drop.

## Stage C — radix-4 signed-digit rows

Recode the 13 bits of `t` into 7 radix-4 digits in {−2, −1, 0, 1, 2}.
Each digit row selects `operand` or `operand << 1`, applies the digit
sign through XOR and a carry-in, and adds into the accumulator. Rows per
stage fall from 13 to 7.

- Model the recurrence exactly, including two's-complement sign extension
  across the accumulator and the existing column truncation. The rounding
  differs from unsigned rows, so the full-domain model must be rerun.
- Price the row primitive before emission. The current rows cost about
  2,250 of the 3,202 Toffoli-like gates (estimate, to be replaced by the
  Stage A model). Two unsigned rows cost about `4w` for operand width
  `w`. One signed-digit row costs about `3w`. The expected saving is about
  25% of row gates, or 15–17% of complete cost (estimate).
- Prove phase correctness for every measurement branch of the digit
  decoder and the gated operand bits. Combine with the C2a gated-operand
  primitive from `reduce-invsqrt-declared-width` if it qualified.

## Stage D — phase bits and rotations

The 36 fine rotations cost about 999 T, which is about 250
Toffoli-equivalents and 7% of the rotation-inclusive cost. The charge per
rotation is `0.56·log2(1/ε) + 5.3` T with `ε = π · margin / n_rot`.

- Screen dropping the lowest phased output bits. Each dropped bit removes
  one rotation, about 7 Toffoli-equivalents, but consumes margin and
  raises the charge on the remaining rotations.
- Screen moving angles that are exact multiples of a quarter or eighth
  turn into the free Clifford or single-T accounting.
- Do not replace rotations with a phase-gradient register in this change.
  The roadmap priced its persistent 30–36 qubits above the rotation charge.

## Stage E — model-only screens

Close these with a recorded model result unless the model predicts at
least 3% lower complete cost.

| Screen | Why it may not pay |
| --- | --- |
| Two-octave table: 128 per unit on [1,2), 64 per unit on [2,4) | Saves 128 lookup rows. The [2,4) octave then needs one extra row per stage and direction, controlled by the octave flag. About four extra rows may cost more than the lookup saving. |
| Load-as-you-go: unlook `c2` after the inner stage and reload it before reversal | Frees 14 qubits only during the outer stage. It costs about one extra 384-row lookup, above the exchange rate unless the peak is in the outer stage and the reload is cheaper than about 300 gates. |

## Stage F — compact-architecture tranche

Register separately, timeboxed to 40 engineering hours, after Stages B–D.
The goal is at most 100 qubits and 2,000 rotation-inclusive
Toffoli-equivalents, about 10× the official reference. Gu et al. report
1,140 Toffolis and 142 qubits for the related Coulomb-potential task,
from a 6,355/252 baseline (arXiv:2610.22367), so this regime is reachable.

Directions to prototype in the model first:

1. **Phase accumulation without a stored output.** Apply the `c0`
   contribution as a phase lookup and accumulate the `t`-dependent terms
   into a phase-gradient target. This removes the 40-qubit output register
   and its controlled denormalization shift (about 312 controlled swaps
   per evaluation, estimate). It adds a persistent gradient register.
2. **Gated-operand signed-digit rows** from Stage C, with no
   materialized operand copy.

Promote nothing from this tranche without the full evidence chain below.

## Promotion

- Combine only variants that each lower cost on their own (the existing
  parent rule).
- Admission: at least 5% lower measured complete cost than the control,
  zero failures across all 3,133,452 inputs, at most 90% tolerance use,
  and native parity on fixtures at powers of four, segment edges and the
  witnesses.
- Then a full 200,540,928-trajectory pass, a fresh one-use confirmation on
  identical bytes, and a paired archive run.

| Stage | Expected cost change | Confidence |
| --- | ---: | --- |
| B, rounding and widths | −1% to −3% | Medium |
| C, signed-digit rows | −10% to −17% | Medium; needs new arithmetic |
| D, rotations | −0.5% to −2% | High; small |
| F, compact tranche | toward −50% | Low; research |
