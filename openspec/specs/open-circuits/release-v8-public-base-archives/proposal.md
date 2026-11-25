## Why

The first version of this change could release only when both the public
DQI and the public chemistry member were banked. A delay or a `no_go` in
either would leave nothing to ship, and the routed-decoder release (v7) had
been dropped.

Each task's member is independent in the archive. So this change releases
**any banked combination**, falling back per task to what we already hold:

| Task | Preferred member | Fallback member |
| --- | --- | --- |
| invsqrt | `invsqrt-v8` | v6 `254279d6…` (5.05×) |
| DQI | `dqi-v8m`, else `dqi-v8` | routed `d41de9ee…` (3.46×, certified) |
| Chemistry | `chemistry-v8` | v6 banked family (1.033×) |

Projected aggregates, from published ratios (estimates):

| invsqrt | DQI | Chemistry | Aggregate |
| --- | --- | --- | ---: |
| own | routed | own | 2.62 |
| own | routed | public | ≈ 5.7 |
| own | public | own | ≈ 6.9 |
| own | public | public | ≈ 15.0 |
| public | public | public | ≈ 24.0 |

Chemistry is the quickest, lowest-risk member, so the usual first step up
is the second row.

## What Changes

- Release `v8.0` now from members already certified: v6 invsqrt, the routed
  DQI and v6 chemistry.
- After each banking event, release the next archive `v8.N` from the best
  banked member per task.
- Add an optional deterministic DEFLATE container, chosen from Kaggle's
  actual upload size limit, with the zlib build pinned.
- Run the metric and a confirmation, upload, and reconcile each release.

## Impact

- Requires only `adopt-vendored-source-policy` for `v8.0`. Later releases
  need the corresponding banked member.
- Replaces `release-v7-routed-dqi-hybrid`: `v8.0` is that archive.
- At most five releases: `v8.0`, then one per banking event (`chemistry-v8`,
  `dqi-v8`, `invsqrt-v8`, `dqi-v8m`).
