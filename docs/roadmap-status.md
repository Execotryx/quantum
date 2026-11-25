# Roadmap status

Phase one paused the following unfinished changes on 2026-11-14.
The successors listed below are the planned replacements.

| Change | Status | Trigger | Planned successor | Retained evidence |
| --- | --- | --- | --- | --- |
| [`assemble-routed-bm-direct-forney-decoder`](../openspec/changes/assemble-routed-bm-direct-forney-decoder/proposal.md) | Paused | `vendor-public-inplace-dqi` | `dqi-v8` | [DQI](#dqi) |
| [`build-routed-bm-dqi-decoder`](../openspec/changes/build-routed-bm-dqi-decoder/proposal.md) | Paused | `vendor-public-inplace-dqi` | `dqi-v8` | [DQI](#dqi) |
| [`freeze-dqi-zero-discrepancy-round`](../openspec/changes/freeze-dqi-zero-discrepancy-round/proposal.md) | Paused | `vendor-public-inplace-dqi` | `dqi-v8` | [DQI](#dqi) |
| [`specify-dqi-history-overflow`](../openspec/changes/specify-dqi-history-overflow/proposal.md) | Paused | `vendor-public-inplace-dqi` | `dqi-v8` | [DQI](#dqi) |
| [`compress-dqi-decoder-width`](../openspec/changes/compress-dqi-decoder-width/proposal.md) | Paused | `vendor-public-inplace-dqi` | `dqi-v8` | [DQI](#dqi) |
| [`fit-dfthc-alternating-projection`](../openspec/changes/fit-dfthc-alternating-projection/proposal.md) | Paused | `vendor-public-c40-chemistry` | `chemistry-v8` | [Chemistry](#chemistry) |
| [`select-compressed-chemistry-shape`](../openspec/changes/select-compressed-chemistry-shape/proposal.md) | Paused | `vendor-public-c40-chemistry` | `chemistry-v8` | [Chemistry](#chemistry) |
| [`preregister-chemistry-s2-settings`](../openspec/changes/preregister-chemistry-s2-settings/proposal.md) | Paused | `vendor-public-c40-chemistry` | `chemistry-v8` | [Chemistry](#chemistry) |
| [`promote-compressed-chemistry`](../openspec/changes/promote-compressed-chemistry/proposal.md) | Paused | `vendor-public-c40-chemistry` | `chemistry-v8` | [Chemistry](#chemistry) |
| [`sequence-hybrid-releases`](../openspec/changes/sequence-hybrid-releases/proposal.md) | Paused | `release-v8-public-base-archives` | `v8.0` | [Release](#release) |

## DQI

- [Full-strength routed DQI receipts and receipt hashes](evidence/review-fixes-cloud-20261108/dqi-strength/complete.json)
- [Matched full-size DQI receipts](evidence/review-fixes-cloud-20261108/dqi-full-pair/registration.json)

## Chemistry

- [Lane A checkpoint recovery record](chemistry-polish-recovery-08-11-2026-22-30-00.md)
- The 41 sweep checkpoints are retained on the cloud worker under
  `/var/tmp/quantum-review-20261108/runs/review-chemistry/A/sweeps`.
- [Chemistry S2 settings](evidence/review-fixes-cloud-20261108/chemistry-s2-settings.json)

## Release

- [v6 full and confirmation receipts](v6-confirmation-cloud-09-11-2026-00-37-00.md)
- [v6 paired cloud verification](v6-paired-cloud-09-11-2026-01-25-00.md)

## Round-11 changes

| Change | Status | Trigger | Planned successor or disposition |
| --- | --- | --- | --- |
| `release-v7-routed-dqi-hybrid` | Outside the roadmap | `release-v8-public-base-archives` | `v8.0` uses the same members. See [release evidence](#release). |
| `cap-routed-bm-round-widths` | Outside the roadmap | `vendor-public-inplace-dqi` | Eligible if the DQI group resumes. See [routed DQI evidence](#dqi). |
| `freeze-dqi-bezout-reciprocal-model` | Outside the roadmap | `vendor-public-inplace-dqi` | Eligible if the DQI group resumes. The round-11 prototype bundle was unavailable. |
| `emit-dqi-bezout-phase-decoder` | Outside the roadmap | `vendor-public-inplace-dqi` | Eligible if the DQI group resumes. |
| `close-chemistry-alternating-lanes` | Outside the roadmap | `vendor-public-c40-chemistry` | Eligible if the chemistry group resumes. See [lane A evidence](#chemistry). |
| `adopt-rank15-gf64-multiplier` | Outside the roadmap | `vendor-public-inplace-dqi` | The tensor and exhaustive checks are carried by [`audit-public-dqi-multiplier`](../openspec/specs/open-circuits/audit-public-dqi-multiplier/proposal.md). The original change is eligible if the DQI group resumes. |
