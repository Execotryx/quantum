## Step 1 — admission (fixed list: P1, P2)

For each table and each loader set:

1. Record the origin URL, author, revision (Git commit SHA or Kaggle
   version), the licence statement and its location, and the origin's
   published output hashes (policy 5.1).
2. Apply the admission table of `adopt-vendored-source-policy`.
   - P1 needs the notebook code that emits the table, plus `plan.py` and
     `loader.py`.
   - P2 needs the generating source named in EigenOS `NOTICE-v7` for both
     the NPZ and the loaders. Look only there and in the EigenOS repository.
3. A pairing with a missing source is recorded as `hash reference only` and
   leaves the candidate list.
4. Write `third_party/chem-<pairing>-table/` and
   `third_party/chem-<pairing>-loaders/` for each admitted pairing.

If neither pairing is admitted, record `no_go` and stop.

## Step 2 — regeneration

For each admitted pairing:

1. Rebuild the table from its vendored code in a clean environment. Apply
   policy 5.2 and 5.3 to decide which table bytes are the member.
2. Use the adapter `src/qcompile/vendored/chem/`. It calls the vendored
   planner and emitter and serializes each ANGLE circuit with our KMB writer,
   in the member order and names the metric expects.
3. Build twice in separate directories and require identical member hashes.
   ANGLE circuits are circuits: no floating-point exception applies.

## Step 3 — verification

For each regenerated pairing:

1. Native check of every loader on all of its addresses.
2. Run the official chemistry verifier. Record:
   - ε₁ and ε₂ (each ≤ 20 mHa);
   - Λ (> 49.0);
   - `E_gap` (> 3.914898);
   - `λ_eff`, `T` and `Q`;
   - the maximum ANGLE circuit qubits (≤ 128), and the absence of Z_POW in
     ANGLE circuits.

## Step 4 — selection

| Outcome | Action |
| --- | --- |
| One or two pairings pass every constraint | Select the lower cost. Break a tie by fewer qubits. Bank as `chemistry-v8`. |
| Selected cost is above 3.2×10⁸ | Still bank it. Record the difference from the published figure. |
| No pairing passes | `no_go`. Keep the v6 chemistry members. |

## Step 5 — attribution

Append a `NOTICE` block for every vendored component, selected or not.
Credit the selected pairing's authors in `README.md` and the release notes.
