## Step 1 — admission (fixed candidate list)

For each of D2, D3, D5, D5 with the Özer patch, and D4:

1. Record origin URL, author(s), revision or dataset version, the licence
   statement and its location, and the origin's published output hash
   (policy 5.1). Record each quoted prefix as `hint: match` or
   `hint: mismatch`.
2. Apply the admission table of `adopt-vendored-source-policy`. Lineage is
   checked one level up: D3 inherits D2's admission, and the D5 patch
   inherits D5's.
3. Reject any candidate whose build inputs include the denylisted
   `993c70386a3d` KMB or the unlicensed Schur decoder.
4. Write `third_party/dqi-<id>/` for each admitted candidate.

If none is admitted, record `no_go` and stop.

## Step 2 — regeneration

1. Add `src/qcompile/vendored/dqi/`, an adapter that runs each candidate's
   vendored builder in a clean environment with pinned Python (3.13) and
   kickmix versions. It writes the KMB with no post-processing.
2. Build each admitted candidate twice and require identical KMB SHA-256.
3. Compare with the origin's published hash recorded in Step 1. A rebuilt
   circuit that differs is excluded (policy 5.2). A candidate whose origin
   publishes no hash continues on verification alone.
4. Record `Q`, static and mean Toffoli count, KMB bytes, build wall time
   and peak RSS.

## Step 3 — pooled price (definition)

Each full-coverage run has `n = 102,400` shots. For a candidate that has
run `S` salts with `K` failing shots in total (value or phase):

1. `λ_up = ½ · χ²(0.95; 2K + 2)`, the one-sided 95% Poisson upper bound on
   `K`. For `K = 0, 1, 2, 3` this is 3.00, 4.74, 6.30, 7.75.
2. `k_price = ⌈λ_up / S⌉`, the failures priced into one 102,400-shot run.
3. **Pooled price** = the official cost with `k_price` failures in `n`
   shots, from the same scoring function the existing conservative rule
   uses.

Examples: `S = 2, K = 0` → 2 failures priced. `S = 8, K = 0` → 1.
`S = 8, K = 2` → 1. `S = 8, K = 16` → 4.

## Step 4 — two-stage pricing

Register 8 fresh 32-byte salts `s1 … s8` in
`docs/evidence/vendored-dqi/salts.json` before any run.

**Stage 1, screen.** Run every regenerated candidate at full coverage on
`s1` and `s2`. Compute each pooled price with `S = 2`. Rank ascending. Break
ties by fewer qubits, then by fewer mean Toffolis, then by candidate ID.

**Stage 2, finalists.** Take the top two of the ranking, or the only one.
Run each on `s3 … s8`. Compute each pooled price with `S = 8`, pooling the
Stage 1 runs.

No other run is made. A run interrupted by the worker is resumed once from
its own checkpoint; it is not restarted on a new salt.

## Step 5 — selection

Select the finalist with the lower `S = 8` pooled price, with the same
tie-breaks. Record the full table of both stages, including per-salt
failure counts. The selected KMB SHA-256 becomes `dqi-v8`, banked with its
pooled price and its zero-failure cost.

| Outcome | Action |
| --- | --- |
| A finalist is selected and its pooled ratio ≥ 50 | `go`. |
| A finalist is selected and its pooled ratio < 50 | `go_recorded`. Bank it only if its pooled price is below the routed decoder's conservative price (7,121,637,700,132.021). |
| No candidate was regenerated | `no_go`. The routed decoder remains the DQI member. |

## Step 6 — attribution

`NOTICE` blocks for every vendored candidate, including those not selected,
because they are vendored source. Credit the selected candidate's lineage
in `README.md` and the release notes.
