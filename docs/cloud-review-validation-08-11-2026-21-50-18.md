# Review-fix cloud validation

The existing Google Compute Engine worker ran the tests in an isolated Linux
x86-64 checkout with Python 3.13.14 and the frozen dependencies. The original
backend inventory remained intact. The cloud checkout reconciled the metric,
verifier and Kickmix paths while preserving the recorded asset hashes and
other inventory fields.

The first focused run on tree `63a1ffdfab7cc08f2d11ebf9bb58190a96b30a57`
reported **76 passed and 1 skipped**. The skipped reference-loader fixture
was transferred by hash for the next run. The native freed-nonzero probe
reported **128 value errors and 0 phase errors in 256 shots** and completed
with the expected verifier diagnostic.

An initial S2 settings registration exposed extra members in the pinned
reference NPZ. The reader now uses the existing reference-loader policy,
which validates the required arrays and permits extra members. A regression
fixture exercises the pinned reference directly. The registered DQI depth
campaign can now resume across the worker's one-hour shutdown limit. Each
completed chunk binds its seed, registration and content hash, and a process
lock prevents concurrent writers.

## Measured cloud comparisons

The v6 screen ran on source `88ee03305bc9f560b00cc677e48d27244a03cbcd`.
The v5 control reproduced its frozen circuit and 472,336.9178780867 cost.
The sibling-sharing circuit, SHA-256
`254279d6ffb1907c60458ef0c8adfcd728e40ea75a44fb754be6346efeef4728`,
cost 411,586.9178780867. Both declared 150 qubits, passed 31,232 native
trajectories and used 66.77104117799098% worst-case phase tolerance. The
observed Toffoli-like count fell from 2,908 to 2,503. The complete cost
model matched the native counts and both v6 builds produced identical bytes.

| DQI dimensions | Reference cost | Routed cost | Reference → routed qubits |
|---|---:|---:|---:|
| `(63, 4)` | 43,385,473,284.84202 | 11,807,146,016.840532 | 286 → 312 |
| `(127, 12)` | 357,434,169,827.92676 | 88,971,157,659.98183 | 484 → 512 |

Both DQI comparisons used the same 2,560 draws per pair, with history
depth 3 for the reduced candidate. All four verifier runs reported zero
value and phase errors. The five native stack fixtures passed across
depths 1–3, including the single- and repeated-overflow cases.

The pinned reference's maximum absolute chemistry offset was
5.597752481885436. The registered rule yielded `B0 = 11.5` and
`penalty = 1.0`. Projection mode also reproduced the reference ranking
exactly across all seven batches when given the same words and
`lambda_eff`. It selected J9 at a modeled cost of 3,250,386,325.019795.
This is a control for the ranking method.

Cloud Pyright and Ruff passed. Strict OpenSpec validation passed for the
four review changes and their five affected predecessor changes. The
relocated checkout's first broad suite reported 757 passed, 2 skipped
and 2 failed. Both failures replayed historical certificates that
require the original contract hash. The original-contract cloud replay
also restored the two missing chemistry test fixtures and passed
**766 tests** with zero failures or skips.

Four additional checks passed for the frozen DQI round fixture.
They replayed the exact fixture bytes and matched all four classical
cases against native forward and reverse circuits at active widths
3, 12 and 36. The frozen fixture SHA-256 is
`e8b111c2f9c4f126cf1da9c89887a38082a0a89b449d4afe70ad3867010d16d1`.

[Reduced DQI at (63, 4)](evidence/review-fixes-cloud-20261108/dqi-63-4.json) ·
[Reduced DQI at (127, 12)](evidence/review-fixes-cloud-20261108/dqi-127-12.json) ·
[Overflow probe](evidence/review-fixes-cloud-20261108/dqi-overflow-probe.json) ·
[S2 settings](evidence/review-fixes-cloud-20261108/chemistry-s2-settings.json) ·
[Projection control](evidence/review-fixes-cloud-20261108/chemistry-projection-control.json) ·
[v6 screen decision](evidence/review-fixes-cloud-20261108/v6-screen-decision.json) ·
[Cloud test receipts](evidence/review-fixes-cloud-20261108/cloud-test-summary.json)
