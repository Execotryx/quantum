## Input

The factorization exported by `fit-dfthc-alternating-projection`, bound by
SHA-256, with continuous residual ≤ 19.0 mHa and 12-bit decoded two-body
residual ≤ 19.5 mHa. Its S1 registration, terminal decision and checkpoint
receipt must satisfy the `chem_s2.py` plan schema. Write a terminal `go`
decision for the selected lane in that schema.

## Stage limits (fixed)

| Stage | Command | Limits |
| --- | --- | --- |
| Target pin | `chem_s2.py target` | — |
| S2 | `chem_s2.py run` | `outer_iterations` 4, `evaluations` 1,500 per outer iteration, `restore_evaluations` 1,000, `checkpoint_interval` 250, `offset_bound` and `penalty` from the bound plan of `preregister-chemistry-s2-settings`, `wall_seconds` 7,200 |
| S3 | `chem_s3.py run` | `evaluations_per_step` 2,000, `wall_seconds` 7,200; precisions 12, 11, 10, 9, 8, stopping at the first failure |
| Loader ranking | `chem_loader_rank.py run` (mode `s3`) | All `J` from 3 to the 128-qubit cap; two shots per address; one-hour supervisor deadline |

Every stage uses the project margins: both residuals ≤ 19.5 mHa,
`Λ ≥ 49.05` and `E_gap ≥ 3.916` Ha.

## Outcomes

- If S2 ends without an eligible checkpoint, record it and stop. This
  change runs no second S2.
- If S3 stops at precision `p > 8`, continue with `p`. The loader ranking
  uses the passing precision.
- The loader ranking selects the batch by complete modeled cost and
  rebuilds the winning family twice.

## Full verification

1. Build the selected ANGLE family and NPZ twice. Require identical bytes.
2. Run the complete chemistry metric with full coverage `(76 + R·B) · 64`
   shots. For `(9, 143, 40)` that is 87,232.
3. Run a fresh one-use chemistry confirmation on identical bytes.
4. Build a paired archive with the current certified inverse-square-root
   and DQI members retained by hash. Run preflight and the drift gate.

## Promotion

Measured chemistry cost at most 1.624×10⁹ (half the banked incumbent
3,247,752,448.67). Expected 0.55–1.0×10⁹.

| Loader outcome (estimate, `λ_eff = 48`) | Scored qubits | Complete Toffolis | Chemistry ratio |
| --- | ---: | ---: | ---: |
| `J = 5` | 428 | about 49,700 | about 3.3× |
| `J` at cap (about 13–14) | about 492 | about 23,900 | about 5.9× |
