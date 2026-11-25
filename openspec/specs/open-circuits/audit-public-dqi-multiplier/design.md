## Step 1 — inventory

Inspect the selected decoder's vendored source and emitted KMB, and record
for each GF(2¹²) multiply and inverse primitive:

- the call count per shot, static and mean;
- the Toffoli count per call;
- the input and output basis (polynomial basis of 0x1053, or other);
- the scratch qubits per call, and whether the primitive is live at the
  peak-qubit point.

Write the table to `docs/evidence/dqi-multiplier-audit/inventory.json`.

## Step 2 — candidate multipliers

| Candidate | Source | Check |
| --- | --- | --- |
| `r15` | `reference/rank15_tensor.py`, `reference/verify_tower45.py` (our own) | Exhaustive on GF(64) and on all 4096² GF(2¹²) pairs |
| `scheme42` | nasir26/vqcc-kaggle, admitted under the vendored-source policy. The count of 42 is a hint until checked | Same exhaustive check after its basis map to 0x1053 |

Each candidate also needs a CNOT-only conversion between its basis and the
decoder's basis. That conversion must use no extra qubits, applied in
place, or be absorbed into adjacent linear maps.

## Step 3 — transplant rule

Transplant the passing candidate with the fewest Toffolis per call, but
only if all of these hold:

1. That count is below the decoder's per-call multiplier count.
2. The basis conversion adds no qubits at the decoder's peak.
3. The projected saving, (old − new) × the mean call count, is at least
   1% of the decoder's mean Toffoli count.

Otherwise record `no_transplant` with the numbers.

## Step 4 — regeneration and pricing

1. Rebuild the decoder twice with the transplant and require identical
   hashes. Record the mean Toffoli count. It must equal the projection of
   Step 3 to within 0.1%.
2. Register 8 fresh salts and run all 8 at full coverage. Compute the
   `S = 8` pooled price defined in `vendor-public-inplace-dqi` Step 3.
3. Promote only if that pooled price ≤ 0.99 × the `dqi-v8` pooled price.
   Then bank it as `dqi-v8m`. That banking event triggers the next
   `release-v8-public-base-archives` release.
