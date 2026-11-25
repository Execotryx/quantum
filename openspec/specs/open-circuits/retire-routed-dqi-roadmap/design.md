## Status line

The first line of a listed change's `proposal.md` carries its status. Each
phase replaces the previous line.

| Status | Line |
| --- | --- |
| Paused | `> Status: paused on <date>, pending <trigger>. Do not implement further until resolved.` |
| Superseded | `> Status: superseded on <date> by <successor> (member <banked name>, SHA-256 <12 hex>). Kept for evidence.` |
| Resumed | `> Status: resumed on <date>; <trigger> ended in no_go.` |

A listed change that is already archived, or whose tasks are all checked,
is left unchanged and noted in the log.

## Phase 1 — pause (run once, now)

| Change | Group | Trigger |
| --- | --- | --- |
| `assemble-routed-bm-direct-forney-decoder` | DQI | `vendor-public-inplace-dqi` |
| `build-routed-bm-dqi-decoder` | DQI | `vendor-public-inplace-dqi` |
| `freeze-dqi-zero-discrepancy-round` | DQI | `vendor-public-inplace-dqi` |
| `specify-dqi-history-overflow` | DQI | `vendor-public-inplace-dqi` |
| `compress-dqi-decoder-width` | DQI | `vendor-public-inplace-dqi` |
| `fit-dfthc-alternating-projection` | Chemistry | `vendor-public-c40-chemistry` |
| `select-compressed-chemistry-shape` | Chemistry | `vendor-public-c40-chemistry` |
| `preregister-chemistry-s2-settings` | Chemistry | `vendor-public-c40-chemistry` |
| `promote-compressed-chemistry` | Chemistry | `vendor-public-c40-chemistry` |
| `sequence-hybrid-releases` | Release | `release-v8-public-base-archives` |

Add the paused line to each.

## Phase 2 — resolve (run once per group, when its trigger ends)

| Group | Trigger outcome | Action |
| --- | --- | --- |
| DQI | `dqi-v8` banked (`go` or `go_recorded`) | Mark the five DQI changes `superseded`, naming `dqi-v8` and its hash |
| DQI | `no_go` | Mark them `resumed` |
| Chemistry | `chemistry-v8` banked | Mark the four chemistry changes `superseded`, naming `chemistry-v8` |
| Chemistry | `no_go` | Mark them `resumed` |
| Release | `v8.0` uploaded and reconciled | Mark `sequence-hybrid-releases` `superseded` |
| Release | `v8.0` ends in `no_go` | Mark it `resumed` |

## Round-11 bundle

| Round-11 change | Disposition |
| --- | --- |
| `release-v7-routed-dqi-hybrid` | Not imported. Release `v8.0` is the same archive |
| `cap-routed-bm-round-widths` | Not imported while the DQI group is paused or superseded. Eligible for import if the DQI group is `resumed` |
| `freeze-dqi-bezout-reciprocal-model` | Same rule. Its reference model is copied to `docs/evidence/bezout-prototype/` as evidence now |
| `emit-dqi-bezout-phase-decoder` | Same rule |
| `close-chemistry-alternating-lanes` | Not imported while the chemistry group is paused or superseded. Eligible if it is `resumed` |
| `adopt-rank15-gf64-multiplier` | Not imported as written. Its tensor and exhaustive checks are carried by `audit-public-dqi-multiplier`. Eligible as written if the DQI group is `resumed` |

## Records

`docs/roadmap-status.md` lists every change above with its current status,
trigger, successor, and the evidence paths that stay valid. Among those:

- routed DQI certification `dqi-strength`;
- v6 receipts;
- chemistry lane-A checkpoints.

Update it in each phase.
