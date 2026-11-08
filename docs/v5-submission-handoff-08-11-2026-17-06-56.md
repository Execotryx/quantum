# v5 submission handoff

The prepared `submission.zip` has SHA-256
`2ad0d5d7759ffc3cae39f4fb2284d826daeda35c71963bd0592d9234362db3b9`.
Use the description `v5 2ad0d5d7759f` to bind a future external score to
the ZIP. The checksum and preparation record accompany the file locally.

| Measure | v4 | v5 |
| --- | ---: | ---: |
| Full matched aggregate | 1.6149243284 | 1.6561824298 |
| Inverse-square-root cost | 509,471.48 | 472,336.92 |
| Inverse-square-root qubits | 155 | 150 |
| DQI cost | 24,439,466,510.15 | 24,439,466,510.15 |
| Chemistry cost | 3,247,752,448.67 | 3,247,752,448.67 |

The aggregate rose **2.55%** and the inverse-square-root cost fell
**7.29%**. The exact prepared ZIP passed a fresh structural preflight.
The published metric notebook was retrieved through the pinned CLI and
matched the verifier's SHA-256. The local full and fresh confirmation
runs and the cloud archive run verified the same inverse-square-root
bytes. The local workspace suite passed 755 tests. Pyright, Ruff and 23
strict OpenSpec validations passed.

The scoped confirmation review passed in an isolated ledger. The
formal repository certificate and external score reconciliation remain
pending. The archive is staged for manual upload.

[Preparation record](evidence/invsqrt-trimmed-paired-20261108/submission-preparation.json) ·
[Paired comparison](evidence/invsqrt-trimmed-paired-20261108/comparison.json) ·
[Scoped confirmation review](hybrid-scoped-confirmation-review-08-11-2026-16-57-16.md)
