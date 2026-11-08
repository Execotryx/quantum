# Hybrid v3 optimization measurements

The starting point was the measured v2 hybrid, ZIP SHA-256
`9aac7afcd0ff3bbff7f4c65c85cf1b331e67b3fd9893ec83b8499d0f223bb841`.
Its aggregate score was 1.3779715417804443. The [v2 report](next-hybrid-paired-archive-08-11-2026-01-13-24.md)
records the paired replay, coverage and release-certificate state. The v3
screen and archive trial use the pinned native evaluator, the frozen Python
3.13 dependencies and the exact v2 retained members.

## Paired archive result

The pinned evaluator measured **1.5753293577319043** for the v3 hybrid
on Google Cloud. That is **14.32%** above v2's 1.3779715417804443.
The v3 archive changes only inverse square root. The byte-identical DQI
and chemistry members reproduced their v2 costs under the paired seed.

| Benchmark | v2 cost | v3 cost | Completed trajectories |
|---|---:|---:|---:|
| Inverse square root | 820,078.9505284121 | 548,860.9216547348 | 200,540,928 |
| DQI | 24,439,466,510,149.91 | 24,439,466,510,149.91 | 102,400 |
| Chemistry | 3,247,752,448.668952 | 3,247,752,448.668952 | 254,464 |

The two local builds and the VM rebuild produced ZIP SHA-256
`920fcfba647e59524d9f66b254d1fc6438e4fb792663524c16bac4453f0ac94d`.
The metric evaluated a fresh extraction in 1,930.10 seconds. The external
sampler observed 8.75 GiB peak process-tree PSS and zero swap PSS. The DQI
value and phase error counters were both zero.

- [Paired comparison](evidence/advance-hybrid-20261108/archive/comparison.json)
- [Full verifier receipt](evidence/advance-hybrid-20261108/archive/verification.json)
- [Archive rebuild](evidence/advance-hybrid-20261108/archive/prepare.json)
- [Sampled archive memory](evidence/advance-hybrid-20261108/archive/resources.json)

## Inverse square root

The screen rebuilt all four controls, including the v2 circuit and coefficient
table byte for byte. It tested each ablation independently and combined only
changes that lowered cost and passed their phase and native gates.

| Lane | Qubits | Cost | Worst tolerance use |
|---|---:|---:|---:|
| Verified v2 | 175 | 820,078.95 | 26.19% |
| Binary normalization | 169 | 738,895.96 | 26.19% |
| Measurement unlookup and phase repair | 175 | 695,828.95 | 26.19% |
| Precision 29/21/14 | 165 | 735,562.65 | 71.96% |
| Precision 29/21/14 with phase repair | 165 | 618,412.65 | 71.96% |
| Combined v3 | **159** | **548,860.92** | **71.96%** |

Precision 28/20/13 and 27/19/12 exceeded the tolerance. The combined lane
lowered v2 cost by **33.07%**, passing the 738,071.06 cost threshold. It
passed all 3,133,452 modeled inputs and 31,232 native development trajectories.
The measured circuit uses 3,202 Toffoli-like gates, one T-like gate and 36
fine rotations. Measurement unlookup erases the coefficient registers and
repairs the measurement-induced phase on the live address. Binary
normalization uses a reversible compact shift count, with restored input
and scratch checked on serialized circuits.

Two local full-strength runs on WSL each passed 200,540,928 trajectories.
The fresh confirmation used a distinct salt and the same KMB SHA-256
`ce8a58b65ee2d89457de655565a22b68ffc2d7dc68befc764a99410b3285f5b4`.
Peak sampled process-tree PSS was 452 MiB for the full pass and 330 MiB for
confirmation. Both sampled zero swap PSS. The 12-worker runtime choice
changed execution parallelism while retaining the frozen circuit, verifier
and shot count.

- [Screen registration and decision](evidence/advance-hybrid-20261108/invsqrt/decision.json)
- [Full local pass](evidence/advance-hybrid-20261108/invsqrt/full-result.json)
- [Fresh local confirmation](evidence/advance-hybrid-20261108/invsqrt/confirmation-result.json)

## DQI

The deterministic tower representation preserves the external GF(4096)
coordinates and supplies a trace-dual map for runtime masks. The clean
norm inverse maps zero to zero. The serialized native and tower inverse
tests cover all 4,096 inputs, arbitrary XOR targets, phase and scratch.
The standalone phase fixture also exercises all 4,095 position words,
including zero and dense runtime masks.

| Isolated arithmetic | Control Toffoli-like gates | Tower Toffoli-like gates | Control → tower qubits |
|---|---:|---:|---:|
| Uncontrolled product XOR | 144 | 54 | 37 → 39 |
| Controlled product XOR | 75 | 66 | 49 → 52 |
| Clean inverse XOR, native scaffold | 315 | 180 | 84 → 75 |

The independent schoolbook inverse uses 1,440 Toffoli-like gates. The
decoder trial replaces only the controlled products in the pinned exact
EEA schedule. Each paired test used the same seed for both decoders and
returned zero value and phase errors in 2,560 shots.

| Environment and dimensions | Reference cost | Tower cost | Cost reduction | Qubits |
|---|---:|---:|---:|---:|
| WSL, m=63 and n=4 | 43,385,584,126.22 | 42,177,810,980.50 | 2.78% | 286 |
| Google Cloud, m=127 and n=12 | 357,436,391,902.45 | 342,475,400,193.01 | 4.19% | 484 |
| Google Cloud, m=4,095 and n=70 | 101,381,268,530,435.25 | 96,216,288,137,806.06 | **5.09%** | 1,893 |

The full-size tower decoder reduced mean Toffoli-like gates from 5,725,109
to 5,433,437 and increased serialized operations from 86,051,014 to
116,871,022. The full-size pair sampled 8.71 GiB peak process-tree PSS
and zero swap PSS. The 2,560-shot development receipts carry the same
repetition multiplier within each pair. The gain fell below the 2×
promotion threshold, so the archive uses the pinned full-size reference.

- [Arithmetic measurements](evidence/advance-hybrid-20261108/dqi/arithmetic.json)
- [WSL tower receipt](evidence/advance-hybrid-20261108/dqi/local-tower.json)
- [Reduced-size cloud tower receipt](evidence/advance-hybrid-20261108/dqi/cloud-tower.json)
- [Full-size cloud reference receipt](evidence/advance-hybrid-20261108/dqi/full-shape-reference.json)
- [Full-size cloud tower receipt](evidence/advance-hybrid-20261108/dqi/full-shape-tower.json)

## Chemistry

The structural search ranked 384 layouts. Its preparation and rotation
costs use zero ANGLE Toffolis, so the ranking is a structural bound. The
bounded float64 pilot tested three compressed shapes with 20 objective
evaluations each. The pinned full-shape continuation control measured
16.13 mHa against the 19.5 mHa two-body residual gate.
The certified decoded control produced 18.64 mHa of two-body error and
3.19 mHa of one-body error. The independent packed two-body residual
matched the pinned decoded evaluator within `1e-10` Hartree.

| Shape (R, B, C) | Initial residual (mHa) | Final residual (mHa) |
|---|---:|---:|
| (9, 129, 40) | 5,915.59 | 3,155.38 |
| (9, 143, 40) | 5,817.23 | 3,066.00 |
| (10, 129, 40) | 5,915.58 | 3,129.98 |

The PSD rank diagnostic at rank 360 was 6.68 mHa, so the failed fit only
closes this initializer and budget. The pilot stopped before decoded-word
evaluation and ANGLE synthesis. The archive keeps the v2 chemistry
factorization and all nine ANGLE circuits.

- [Structural ranks](evidence/advance-hybrid-20261108/chemistry/structural-rank.csv)
- [Best compressed pilot](evidence/advance-hybrid-20261108/chemistry/r9-b143-c40.json)
- [Continuation control](evidence/advance-hybrid-20261108/chemistry/continuation.json)
- [Decoded control comparison](evidence/advance-hybrid-20261108/chemistry/decoded-control.json)

## Implementation checks

The Ubuntu WSL suite passed 322 tests. The expanded full-field phase
fixture also passed the targeted 22-test rerun. Pyright passed on every
changed Python file, and the OpenSpec change passed strict validation.
The reviewed code reproduced the frozen v2 control and v3 candidate.
The DQI screen releases generated circuits before serialized reload to
avoid retaining both native objects during the full-size comparison.
