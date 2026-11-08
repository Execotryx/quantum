# Review annotations: four OpenSpec changes, 8 November 2026

Created 08-11-2026-21-20-00 in Asia/Qyzylorda, against `d41ba59`. Each
review annotation is resolved by one new change. The earlier changes in this
bundle are patched to reference them.

| Annotation | Finding in the code | Change |
| --- | --- | --- |
| DQI zero-discrepancy counter | `bm_routed.step` and the native `_counter_step` both apply `d + 1` when `Δ = 0`. The earlier requirement said the counter stays unchanged, which was wrong. With `Δ = 0`, the native round never multiplies `T₀` by a nonzero factor, so a nonzero wrapped word is harmless. | `freeze-dqi-zero-discrepancy-round` |
| DQI history overflow | The earlier sink design freed a nonzero word on a second overflow, and did not specify flag clearing or failure accounting. | `specify-dqi-history-overflow`: persistent transfer word, value-only flag clearing, 7-bit never-decremented overflow count, backend gate, 10⁷-sample depth selection |
| Chemistry shape selection | `structural-rank.csv` has preparation and rotation Toffolis only, with no ANGLE loaders and no `λ_eff`. | `select-compressed-chemistry-shape`: restoration-only `λ_proj` and natively verified 8-bit banked families through the pinned `resource_costs` |
| Chemistry S2 settings | No plan or record registers `offset_bound` or `penalty`; only tests use them. `optimize_s2` defaults `penalty` to 1.0. | `preregister-chemistry-s2-settings`: `penalty = 1.0`, `offset_bound = max(1, ⌈4·m_ref⌉/2)` from the reference offsets, one registered contingency, hash-bound plan |

## Order

1. `freeze-dqi-zero-discrepancy-round` and `specify-dqi-history-overflow`,
   both before task 2 of `assemble-routed-bm-direct-forney-decoder`.
2. `preregister-chemistry-s2-settings` (settings record), then
   `select-compressed-chemistry-shape`, then the bound S2 plan, then
   `promote-compressed-chemistry`.
