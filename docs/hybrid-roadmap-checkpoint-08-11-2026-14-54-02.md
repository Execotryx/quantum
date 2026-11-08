# Hybrid roadmap measurements

## Inverse square root

The lattice refinement searched the coefficient words with the exact
integer recurrence. Both single-width parents improved v3, and the
combined 28/20/14 circuit passed the full domain and 31,232 native
development trajectories. An independent rebuild reproduced KMB SHA-256
`c487332fe965389191c8e6d34848d61c82748e5802c6e616eb0363869f92c4c9`.

| Component metric | v3 | Lattice refinement |
|---|---:|---:|
| Cost | 548,860.9216547348 | 509,471.48180735623 |
| Declared qubits | 159 | 155 |
| Toffoli-like gates | 3,202 | 3,046 |
| Fine rotations | 36 | 35 |
| Worst tolerance use | 71.96% | 66.77% |

The component cost fell 7.18%. The two full local verifier runs used
distinct registered salts on identical bytes. Each passed 200,540,928
trajectories at the same measured cost and margin.
[Full pass](evidence/invsqrt-roadmap-confirmation-20261108/full-result.json) ·
[Fresh confirmation](evidence/invsqrt-roadmap-confirmation-20261108/confirmation-result.json)

The normal [v4 screen](evidence/invsqrt-v4-screen-20261108/decision.json)
reproduced the selection and frozen bytes on a clean source snapshot.
All five controls and both single-width parents passed.

The [liveness trace](evidence/invsqrt-width-trace-20261108/liveness.json)
observed 131 allocated qubits at public call boundaries and 159
declared qubits. The serialized first-to-last-use analysis also peaked
at 159. Temporary native workspace between calls remains unobserved.
The tested C2a row projected 905,204 complete cost even at an
optimistic 131 qubits. The signed-row slices projected 1,194,753.66.
Both failed the cost gate. The separate drop-two phase-bit circuit
saved 0.30% against v3 and passed the full domain and native fixtures.

The best accuracy-passing [two-octave table](invsqrt-two-octave-08-11-2026-15-13-08.md)
projected a cost of 516,038.42 after pricing its measured address mapping
and extra rows. It fell above the lattice control's measured cost.
Load-as-you-go coefficient lookup also missed the cost gate.

## DQI

The [full cloud profile](dqi-full-stage-profile-08-11-2026-14-36-03.md)
assigns 73.69% of counted gates to the locator and its reversal. The
controlled-product census explains the prior tower-field improvement
exactly. A [standalone full-size phase scan](evidence/dqi-phase-scan-20261108/full-scan.json)
used 94,185 Toffoli-like gates at 1,331 declared qubits. It passed 72
native trajectories covering all weights 0–35, all 4,095 positions,
runtime mask phase, input restoration and scratch cleanup. That fixture
supplies precomputed polynomial inputs.

The [GF(8)-subtower inverse](evidence/dqi-subtower-inverse-20261108/slice.json)
used 102 Toffoli-like gates and 63 qubits, down from 180 and 75 for the
previous tower primitive. All 4,096 inputs passed native differential
checks. The bounded GF(64) search retained rank 18 after 999,641
tensor-preserving flips. The routed locator, full-degree reversible
reciprocal and decoder admission remain open.

The [classical compression harness](dqi-inplace-end-state-08-11-2026-14-58-03.md)
recovered the syndrome exactly on all 23,851 decodable GF(16) cases in
its four-syndrome domain. Its two-bank full-size layout needs at least
1,686 qubits before oracle scratch, above the compression target.

## Chemistry

All four bounded cloud lanes completed 250 evaluations of the joint
vector and weight objective at `(9,143,40)`.

| Initializer | Best continuous residual (mHa) | Elapsed seconds |
|---|---:|---:|
| I1 | 314.05 | 245.01 |
| I4, seed 184 | 795.77 | 185.21 |
| I4, seed 185 | 778.49 | 178.69 |
| I4, seed 186 | 806.80 | 176.66 |

On the same I1 lane, the 20-evaluation local pilot reached 2,477.79 mHa.
The cloud run continued improving through its cap and remained above
the 19 mHa S1 gate. Its decoded two-body residual was 314.51 mHa.
The [cloud receipts](evidence/chem-s1-cloud-20261108) retain independent
registrations, traces, checkpoint hashes and exact decoded metrics.
The generated local checkpoint arrays are retained under
`runs/hybrid-roadmap-20261108/local-chemistry-checkpoints`.

A separate [250-evaluation local I3 fit](evidence/chem-s1-i3-250-20261108/decision.json)
reached 225.63 mHa continuous and 226.04 mHa after 12-bit decoding.
The initializer differs from the cloud lanes, so this comparison
separates fit outcomes rather than hardware speed.

The small banked loader tests verify addresses, padding, phase and
cleanup independently of the factorization search. No compressed
factorization qualified for ANGLE synthesis. The 24-run fit grid
remains open, along with S2 admission and production quantization.

## Operations

The [operations report](hybrid-roadmap-operations-08-11-2026-14-42-35.md)
records the preflight fixtures, historical score binding, fresh salt
policy and external metric gate. The unchanged v2 and v3 archives
passed structural preflight.
