## Why

Our v6 invsqrt costs 411,586.92 (150 qubits, about 2,503 Toffoli-like),
a ratio of 5.05. Public 62–63-qubit circuits reach 20.65–21.21:

| ID | Lineage (hash prefixes are hints, policy 5.1) | Licence | Q | Cost | Ratio | Generating source |
| --- | --- | --- | ---: | ---: | ---: | --- |
| I1 | `bce2948f…` (Özer vqcc-v18-portfolio; Mallick, yoyobar, busyaprime, mrmeows) | Apache-2.0 | 62 | 100,568.5 | 20.650 | binary in dataset; lineage notebooks Apache-2.0 |
| I2 | `af4698478fba…` (Agniv Banerjee, via EigenOS v7 ledger) | Apache-2.0 per ledger | 62 | 97,921.58 | 21.209 | binary in ledger |
| I3 | `9a8627c8…` (busyaprime re-synthesis of mrmeows' 17-stage hybrid, `qcc-1375-open-circuits`) | Apache-2.0 | 63 | — | — | mrmeows design public |

Admission requires generating source. That is unconfirmed for I1 and I2,
and present for the I3 lineage.

## What Changes

- Check the three candidates against the admission rules.
- Regenerate each admitted candidate with our pipeline and order them by
  measured cost.
- Verify in that order at full official coverage (every x 64 times,
  200,540,928 shots, zero failures), and stop at the first pass. At most one
  candidate normally gets a full run, instead of all three.
- Bank that candidate.

## Impact

- Requires `adopt-vendored-source-policy`.
- If none is admitted, the v6 invsqrt stays. The v8 release then uses its
  "own invsqrt" variant.
