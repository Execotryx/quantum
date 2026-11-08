## Why

`fit-dfthc-alternating-projection` chose among qualifying lanes by "the
lowest structural projected complete cost" from `structural-rank.csv`.
That table holds only preparation and rotation Toffolis (for example 6,741
at `(9, 143, 40)`) and projected qubits. It contains no ANGLE loader
Toffolis and no `λ_eff`. The ANGLE loaders run twice per evaluation and
depend on the row count `76 + R·B` and on the batch size. A selection
without them can pick the more expensive shape.

## What Changes

- Run the four registered lanes unchanged.
- For each lane that passes both gates, compute a complete projected cost
  at 8-bit precision from the pinned `resource_costs`:
  - `λ_proj` from offset restoration only, under the preregistered S2 settings;
  - Toffolis and qubits from natively verified 8-bit banked families over every batch.
- Select the lowest projected cost. Break ties by the lower 12-bit decoded
  two-body residual.

## Impact

- Supersedes the selection rule in `fit-dfthc-alternating-projection`.
- Requires the settings record of `preregister-chemistry-s2-settings`.
- Adds a `projection` mode to `tools/chem_loader_rank.py` that accepts a
  word table and `λ_proj` directly. The S3 and reference modes are unchanged.
- The projection decides only the shape. Accuracy at 8 bits is decided
  later by S3.
