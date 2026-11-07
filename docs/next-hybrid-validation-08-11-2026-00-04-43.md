# Next hybrid validation, 8 November 2026

The [follow-up full verification report](next-hybrid-paired-archive-08-11-2026-01-13-24.md)
records the completed full pass, fresh confirmation, paired archive and DQI retry.
This document preserves the earlier development results and their scope.

The incumbent is the [locally certified direct-phasing hybrid](direct-hybrid-paired-verification-07-11-2026-14-59-24.md)
with aggregate score 1.286176112637598. Lower component cost is better. The
campaign used the pinned Linux native backend and frozen Python 3.13
environment. The WSL test suite passed 309 tests, including the real notebook
NPZ differential and the new native chemistry and DQI fixtures. Pyright
reported zero diagnostics on the changed Python files.

The archived chemistry NPZ contains an optional `angle_words.npy` member.
The candidate coverage and preflight readers now validate the required payloads
while allowing unambiguous extra members. Newly generated refit NPZs still use
the strict canonical layout. The [structural preflight](evidence/next-hybrid-20261108/certified-preflight.json)
passed on the original certified ZIP, including the native register checks and
the expected 254,464 chemistry trajectories.

## Inverse square root

The [v2 registration](evidence/next-hybrid-20261108/invsqrt/registration.json)
and [decision](evidence/next-hybrid-20261108/invsqrt/decision.json) preserve
the three controls, all candidate attempts and the 907,648.31 promotion limit.

| Variant | Declared qubits | Rotation-inclusive screened cost | Change vs certified direct |
|---|---:|---:|---:|
| Certified direct | 199 | 1,008,498.12 | baseline |
| Narrower Taylor | 193 | 933,379.93 | 7.45% lower |
| Minimax cubic | 193 | 909,501.92 | 9.82% lower |
| Minimax quadratic | 175 | 820,078.95 | 18.68% lower |

The [quadratic receipt](evidence/next-hybrid-20261108/invsqrt/minimax-quadratic.json)
records 0 failures across the 3,133,452-input emitted-arithmetic model,
26.19% worst tolerance use and 31,232 native fixture trajectories. The
serialized winner has SHA-256
`3ae33a3d0101085613ac6bfc1b1ab7dde6b8f35f7ebd84d0976ba66a0772f799`.
The component passed the screen. WSL interruptions stopped the subsequent
full verifier before it wrote a terminal receipt. Full verification, fresh
confirmation, and the paired complete-archive measurement remain open. Holding
retained component costs fixed gives a projected score of 1.3779715418.
The [paired archive registration](evidence/next-hybrid-20261108/paired-hybrid-registration.json)
binds two byte-identical ZIP builds at SHA-256
`9aac7afcd0ff3bbff7f4c65c85cf1b331e67b3fd9893ec83b8499d0f223bb841`.
Their only changed member is the screened inverse-square-root circuit.

## Chemistry

The [fixed-word pilot](evidence/next-hybrid-20261108/chemistry/decision.json)
evaluated 16 points. It used the six required arrays projected from the certified
NPZ and checked the archived and recovered angle words for exact array
equality. The best eligible trial reduced `lambda_eff` from 49.30137 to
49.15861. The refit keeps the two-body words fixed and regenerates the one-body
words. Both decoded residuals passed the official threshold.

| Circuit family | ANGLE width | Native trajectories | Cost | Change vs certified J9 |
|---|---:|---:|---:|---:|
| Certified J9 | 128 | 254,464 | 3,247,752,448.67 | baseline |
| Generalized J9, original words | 128 | 254,464 | 3,250,386,325.02 | 0.08% higher |
| Generalized J9, refit | 128 | 15,904 | 3,240,974,365.97 | 0.21% lower |
| Generalized J8, refit | 119 | 15,904 | 3,348,753,832.02 | 3.11% higher |

The [J9 refit](evidence/next-hybrid-20261108/chemistry/refit-j9.json) and
[J8 refit](evidence/next-hybrid-20261108/chemistry/refit-j8.json) use four
shots per address. The refits fall short of the 10% component promotion gate.
The [shape ranking](evidence/next-hybrid-20261108/chemistry/chemistry-layout-ranking.json)
prices preparation and rotations. Its changed-shape entries still need fitted
factors, emitted ANGLE circuits and native scoring.

## DQI

The five serialized fixtures passed native checks for their scoped arithmetic,
runtime mask, or locator update. The [slice comparison](evidence/next-hybrid-20261108/dqi/slice-comparison.json)
records a fixed-shift EEA update at 110 qubits and 480 Toffoli-like gates and
the BM update at 158 qubits and 528. The BM fixture uses a 48-qubit saved row.
These measurements apply to the isolated update slices.

The [256-shot reference control](evidence/next-hybrid-20261108/dqi/scouting-control.json)
returned zero value and phase errors and hit the expected confidence rejection.
The 2,560-shot paired trial stopped before a terminal receipt. WSL logged an
out-of-memory kill during the initial campaign. Temporary swap raised the memory
budget, but later WSL sessions also stopped during long verifier runs. The
reference DQI circuit remains the full-decoder comparison baseline.
