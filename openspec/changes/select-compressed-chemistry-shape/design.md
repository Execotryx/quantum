## Step 1 — lanes and qualification

Run lanes A–D exactly as registered in
`fit-dfthc-alternating-projection` (400 sweeps, then a 3,000-evaluation
polish, from the fixed starts). A lane qualifies when:

- its best-checkpoint continuous residual is at most 19.0 mHa; and
- its 12-bit decoded two-body residual is at most 19.5 mHa (pinned evaluator).

| Qualifying lanes | Action |
| --- | --- |
| None | Record each lane's outcome and stop. No projection runs. |
| One | Select it. Still run Steps 2–3 for the record. |
| Two or more | Run Steps 2–3 for each and select by Step 4. |

Two qualifying lanes with the same shape (A and B) are compared like
different shapes.

## Step 2 — projected `λ_eff`

For each qualifying lane, run `restore_offsets` once from its 12-bit
decoded state with the settings record of
`preregister-chemistry-s2-settings`: `offset_bound`, `restore_evaluations`,
floors `Λ ≥ 49.05` and `E_gap ≥ 3.916`, target `E_gap` 3.9161. Use the
restored metrics' `lambda_eff` as `λ_proj`.

A lane whose restoration does not return `restored` leaves the selection.
Record why.

## Step 3 — 8-bit complete cost

For each remaining lane:

1. Encode its unit vectors with `encode_vectors(vectors, edges, 8)` on the
   lane's tree. Record the word table's SHA-256.
2. Run `chem_loader_rank.py` in `projection` mode with these words and
   `λ_proj`, for each bank split `low_bits ∈ {4, 5, 6}`. Each run builds
   the family for every batch `J` from 3 to
   `min(75, max_batch(76 + R·B, 8, low_bits))`, verifies it natively at two
   shots per address, and calls `rank_complete_cost`. That computes
   `λ_proj · T · Q` with the pinned `resource_costs`, both passes included.
3. The lane's projected cost is the minimum over `(low_bits, J)`. Record
   the full table, including preparation, rotation and ANGLE Toffolis and
   persistent and temporary qubits.

## Step 4 — selection

Select the lane with the lowest projected cost. Break an exact tie by the
lower 12-bit decoded two-body residual, then by lane letter. Write the
lane's S1 `go` decision and hand it to `preregister-chemistry-s2-settings`
(plan binding) and then to `promote-compressed-chemistry`.

## Boundaries

- The word tables here are not refit. If decoded accuracy at 8 bits fails,
  S3 handles it. The projection is a cost comparison only, as stated in
  `rank_complete_cost`.
- The selected `low_bits` and `J` are recorded as hints only. The loader
  stage after S3 reruns its own ranking on the S3 words.
