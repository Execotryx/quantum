## 1. Walks

- [ ] 1.1 Add `sibling_cnot: bool = False` to `_load_table` in `src/qcompile/invsqrt/direct.py` and implement the transformation exactly as in the design.
- [ ] 1.2 Add the same flag to the repair walk in `src/qcompile/invsqrt/unlookup.py`.
- [ ] 1.3 Thread the flag through `build_circuit` and the trimmed builder. Confirm that v5 rebuilds to `f4c8503d…200d` with the flag off.

## 2. Native fixtures

- [ ] 2.1 Lookup fixture over all 512 addresses with arbitrary nonzero targets, with and without the flag. Check words, address and path restoration, and phase.
- [ ] 2.2 Dropped-`cx` mutation fixture that must fail.
- [ ] 2.3 Unlookup fixture with random measurement outcomes for every address. Check identical repaired phase.

## 3. Cost model

- [ ] 3.1 Update the lookup and unlookup formulas for `sibling_cnot`.
- [ ] 3.2 Recalibrate on the 27 existing receipts and the new circuit. Require exact matches.

## 4. Candidate

- [ ] 4.1 Add `configs/invsqrt-direct-v6.json` (v5 trimmed recipe plus `sibling_cnot: true`) and protocol 6 in `tools/invsqrt_direct.py`.
- [ ] 4.2 Build twice from a clean source snapshot. Require identical KMB hashes. Record counts and the model prediction.
- [ ] 4.3 Run the 31,232-trajectory component fixtures.

## 5. Verification and archive

- [ ] 5.1 Full 200,540,928-trajectory verification and one-use fresh-salt confirmation on identical bytes.
- [ ] 5.2 Paired archive with v5 DQI and chemistry retained by hash. Run preflight and the metric drift gate.
- [ ] 5.3 Hand off the archive to `sequence-hybrid-releases` as v6.

## 6. Review

- [ ] 6.1 WSL tests, Ruff, Pyright with the pinned Ubuntu interpreter, strict OpenSpec validation and a dated change log.
