# Trimmed inverse-square-root paired archive

The v5 hybrid scored **1.6561824297677306**, up **2.5548%** from v4.
The confirmed trimmed circuit replaced only `invsqrt.kmb`. The DQI
circuit, nine chemistry circuits and chemistry factorization retained
their v4 hashes. Two local builds and the independent cloud build
produced ZIP SHA-256
`2ad0d5d7759ffc3cae39f4fb2284d826daeda35c71963bd0592d9234362db3b9`.

| Benchmark | v4 cost | v5 cost | Completed trajectories |
| --- | ---: | ---: | ---: |
| Inverse square root | 509,471.48180735623 | 472,336.9178780867 | 200,540,928 |
| DQI | 24,439,466,510,149.91 | 24,439,466,510,149.91 | 102,400 |
| Chemistry | 3,247,752,448.668952 | 3,247,752,448.668952 | 254,464 |

The pinned metric ran on a fresh extraction under the paired v4 archive
salt. The DQI observation counts matched. The local full and fresh
confirmation runs used two distinct salts and the same
`f4c8503d87c9e7cedb8a79a796e0b195623c2e88467691ca1b08af1a70fb200d`
circuit. Its 150 qubits, 2,908 Toffoli-like gates and 35 fine rotations
gave a 7.29% cost reduction at 66.77% worst tolerance use.

The cloud metric took 1,885.28 seconds. The external sampler observed
8.72 GiB peak process-tree PSS and zero swap PSS. The first cloud
attempt stopped before simulation when the clean-source guard caught an
untracked vendor README symlink. The retry excluded that symlink,
retained the same registered sources and inputs, and finished within the
existing VM window. The VM was stopped after receipt collection.

This result promotes v5 as the best measured hybrid archive. Formal
release lineage and external score reconciliation remain separate
gates. The complete local suite passed 745 tests. Pyright, Ruff and
strict validation of all 23 OpenSpec changes passed.

[Paired comparison](evidence/invsqrt-trimmed-paired-20261108/comparison.json) ·
[Structural preflight](evidence/invsqrt-trimmed-paired-20261108/preflight.json) ·
[Full verifier](evidence/invsqrt-trimmed-paired-20261108/verification.json) ·
[Resource sample](evidence/invsqrt-trimmed-paired-20261108/resources.json) ·
[Local confirmation](evidence/invsqrt-trimmed-v4-20261108/verification/confirmation-result.json)
