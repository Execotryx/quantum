# Actual third-chart gauge-one coverage and component receipts

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

This is a bounded read-only review of completed root-run receipts. No provider, fixture, native circuit, sampler, or classifier was executed or changed by this review.

## The actual gauge-one input

The sole new-chart gauge-one input in the 783-case full panel is:

| Property | Recorded value |
| --- | --- |
| Canonical case ID | `54d38bf59904d025bfe626a0db3007111eb8d6c3e975bf0dda3a99d8a4cba57a` |
| Label | `M128_all_raw_boundaries:88` |
| Physical weight | 18 |
| Original prepared-corpus index | 88 |
| Full v6 fixture index | 88 |
| Mask mode | `random` |
| New raw carry | 9,129,984 = `(0, 2229)` in low/high GF4096 halves |
| New selected scalar | 2229 |
| New other carry half | 0 |
| New common polynomial scale | 3899 |
| Terminal seed flag | 1 |
| Raw third query | 8,471,668, nonzero |

This is an existing physical corpus input, not the old first-two rare-case addition and not the newly constructed zero-third-query input. Its recorded full classifier result is admitted at cutoff 15, finite failure is false, the half-core degree sequence is 17 down to 0 without gaps, and the complete reason mask is zero.

The unchanged source record is in `controller_work/night_c27/arithmetic/panel_audit/prepared/cases.json`, SHA-256 `eb9216d25bd69f17179533932f0ec6a8704860a366117bd370b6eec35495e339`. Its positions, magnitudes, roots, syndromes, canonical case ID and mask mode match the full v6 record exactly. The prior origin is `controller_work/work/round2/milestone153/restore_inputs/work/round2/milestone128/logs/raw-boundary-fixtures.json`, panel `M128_all_raw_boundaries`, index 88. The legacy terminal annotation belongs to that historical chart and is not substituted for the actual physical weight or the new gauge.

The full new boundary record is in `controller_work/after_v3/blocks/v6/runs/first3-full/fixtures.json`, SHA-256 `b55d42970ef4572b20f2afc42aa4cabc5d017e0d0476d554e397014babc6e073`. This file records the independent `first3_zero_repaired` carry replay. Its predicted gauge-one case is covered by the native prefix numerator, denominator and gauge-data checks, plus the complete paired phase/restoration checks. A new full-decoder rare panel remains a separate integration gate.

## Completed native evidence

| Receipt | SHA-256 | Scope |
| --- | --- | --- |
| `runs/first3-full/report.json` | `923df5eb0f79f2090f012cc5286267c1de5b3444177516658c4901fd348f9cb4` | Complete 783-case physical key panel |
| `runs/first3-full.guard.json` | `69860f68ff0f61a2e05850d377419337182469c611342af91a7576ef4aa9f85b` | Complete, exit 0, not stopped |
| `runs/third-chart-full/report.json` | `f5d140bb46f1b84886c21cde6bff4e8cbe993d4e572a2e8ec9ecb28f6f943efb` | 20,480 isolated third-chart cases |
| `runs/third-chart-full.guard.json` | `7bbe51fea70cc8cfe1d00bcb55f8eb9548a7984d44df0352f3bb2245fa1143c4` | Complete, exit 0, not stopped |

Receipt paths in this table are relative to `controller_work/after_v3/blocks/v6/`. The full key reports 216,928 T excluding three probe T, prefix 101,087 T, Q889, two identical builds, and HMR seeds 147, 1147 and 2147. Each seed covers every index 0 through 782 exactly once in each prefix, paired, prefix-carry-seam and return-carry-seam panel. All reported error lists are empty. Prefix and carry-seam panels explicitly leave phase debts open and are value-only; the complete pair checks phase and restoration. The six matched prefix masks and the extra third zero-flag mask are retired. The original 76 exclusions remain separately recorded, unchanged in scope.

The isolated panel covers five modes with 4,096 cases each, including 4,098 actual raw-zero cases and 4,096 zero-cross-coefficient cases. Its three seeds are 59191, 60191 and 61191. It is a component contract over admitted pivot coordinates, not a physical sampling claim. The physical panel additionally includes one deterministically constructed admitted raw-zero input.

All 121 loaded-source entries in the full key receipt and all 109 entries in the isolated receipt were rehashed against current files, including sizes; there were no mismatches. This check reads source bytes only and does not reproduce native simulation.

## Exact key event multiset

| Conditional block | T | Fresh mask bits | Occurrences |
| --- | ---: | ---: | ---: |
| Direct-carry selected target phase | 84 | 24 | 32 |
| Inverse polynomial phase | 27 | 12 | 66 |
| Last-return child norm | 15 | 6 | 1 |
| Scalar six-bit inverse phase | 4 | 6 | 7 |
| Tail/gauge zero phase | 10 | 1 | 1 |
| Tail/third zero phase | 22 | 1 | 21 |

The exact uniform-fresh-mask source expectation is `28402108715/131072 = 216690.89290618896`. This is the event-ledger model, not an official measured mean. The six matched inverse calls use the actual borrowed 24-bit public carry bank. No extra manual discount is added for their zero-T repayments.

## Deterministic zero-third source

The separately constructed zero-third-query input remains in `runs/third-raw-zero/cases.json`, SHA-256 `3e7b5f07a0cbfc87e2b12da2ca739c5c70df2a0db2e1d1fa1ca34da4110b0882`; its preparation report is SHA-256 `6d111797aac57773d6f2838cb5c946a2aa4b70068096dc956c021143f74aece8`, with normal preparation guard `8c72aced0233b70b5d95d1d4e7f0ff0881c08c1c1bb71e15c693705d125f36f4`. That historical preparation correctly says not-native; the later full key receipt is the native evidence. Neither receipt creates a population estimate, a new census event, a full-decoder qualification or an official cost.
