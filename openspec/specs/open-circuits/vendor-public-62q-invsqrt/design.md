## Step 1 — admission (fixed list: I1, I2, I3)

For each candidate:

1. Look for generating source at these locations only:
   - I1: Özer's `vqcc-v18-portfolio` and the Kaggle notebooks named in its
     credits;
   - I2: the EigenOS `NOTICE-v7` lineage entry and the Banerjee notebook it
     names;
   - I3: mrmeows' `qcc-1375-open-circuits` and busyaprime's re-synthesis
     notebook.
2. Record the licence statement at origin, the source revision and the
   origin's published output hash (policy 5.1). Record each quoted prefix
   as `hint: match` or `hint: mismatch`.
3. Apply the admission table. A candidate with no generating source at
   these locations is `binary_only` and not admitted.
4. Write `third_party/invsqrt-<id>/` for each admitted candidate.

## Step 2 — regeneration and ordering

1. Use the adapter `src/qcompile/vendored/invsqrt/`. It runs the vendored
   generator in a clean environment and writes the KMB.
2. Build twice and require identical hashes, and equality with the origin's
   published hash where one exists (policy 5.2).
3. Compute each regenerated candidate's cost with the pinned cost function
   from its declared qubits, Toffoli count, T count and rotations. This is
   static and needs no simulation.
4. Order the candidates by ascending cost. Break ties by fewer qubits, then
   by candidate ID. Record the order before any verification.

## Step 3 — sequential verification

Take the candidates in the recorded order.

1. **Smoke run.** One trajectory per x over the whole domain (3,133,452
   shots) with a registered smoke salt. Any failure excludes the candidate;
   move to the next.
2. **Full run.** 200,540,928 trajectories with the registered metric salt.
   Any failure excludes the candidate; move to the next.
3. **Stop at the first candidate with zero failures in both.** Later
   candidates are not run. Their status is `not_run_cheaper_passed`.
4. Run one fresh confirmation, with a new salt, on the passing candidate.
   A failure there excludes it, and the sequence resumes with the next
   candidate.

Salts are registered per candidate before its smoke run.

## Step 4 — outcome

| Outcome | Action |
| --- | --- |
| A candidate passes smoke, full and confirmation | Bank it as `invsqrt-v8`. |
| The list is exhausted, or none is admitted | `no_go`. Keep v6 invsqrt `254279d6…`. |

## Step 5 — attribution

`NOTICE` blocks, and credits in `README.md` and the release notes.
