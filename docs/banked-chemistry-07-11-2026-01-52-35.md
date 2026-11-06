# Banked chemistry lookup and combined validation

Created 07-11-2026-01-52-35 in Asia/Qyzylorda.

The dedicated `codex/invsqrt-chemistry` branch carries the verified
inverse-square-root lead and a lookup-only chemistry optimization. The DQI
circuit and chemistry factorization, tree and angle words retain the accepted
reference bytes or values. The prior in-memory scout motivated the protocol.
The screen registered its inputs and budgets before starting synthesis.

The bank flag uses four temporary ANDs over the five high address bits. The
three intermediate helpers are erased in reverse order, freeing seven scratch
wires for the low-bit unary tree while the flag stays live. After the tree
cleans up, the helpers are recomputed and all four bank ancillas are erased.
The word operations XOR selected constants into arbitrary targets. The
measurement cleanup assumes initialized zero scratch and unchanged controls
until their corresponding corrections. HMR's sign on the product is canceled
by its conditional CZ. The per-circuit checks cover both traversal directions,
including padding in the final batch. Unused encoded addresses are outside
the verified domain.

The J8 rebuild reproduced the accepted complete chemistry cost. The naive J9
width control measured 131 qubits. The nine banked J9 circuits each used 128
qubits and two independent syntheses produced identical KMB hashes. The
serialized family recovered every one of the 3,976 rows at four development
shots per address, with exact words, phase, selection and clean workspace
checked during traversal. Separate nonzero-target fixtures passed all
18 forward and reverse circuit applications at eight boundary addresses.

| Metric | Reference J8 | Banked J9 screen |
| --- | ---: | ---: |
| Maximum angle circuit width | 119 | 128 |
| Angle Toffolis per pass | 39,740 | 37,512 |
| Complete scored qubits | 730 | 742 |
| Complete Toffolis | 93,237 | 88,781 |
| Complete chemistry cost | 3,355,599,588.32 | 3,247,752,448.67 |

The measured screen reduction was 3.2139%, above the 2% gate. The screen
used 58.73 wall seconds, 41.64 process CPU seconds, and 1,286,440 KiB peak
process RSS. These figures cover the control and synthesis screen through the
cost decision. Archive packaging and subsequent verification are separate.

The simplicity review kept one fixed bank architecture and reused the pinned
batch-delta generator, trajectory checks and full metric adapter. The
performance review bounded scratch reuse explicitly, emitted CX operations
only for set word bits, and used serialized rebuild and full-archive checks
without loading the full archive into memory. Ruff, Pyright and strict
OpenSpec validation passed.

The candidate archive and raw receipts are under
`runs/invsqrt-chemistry-20261107/`. Reproduce the screen in the pinned WSL
environment with `tools/banked_chemistry.py screen` and a fresh output directory.
Pass `--words` and `--invsqrt` for alternate locations of the hash-matched inputs.

## Combined full verification

The pinned metric passed all three components from a fresh extraction of the
909,659,144-byte archive. The full run took 841.44 seconds on two logical CPUs
in Ubuntu WSL. The temporary 8 GiB swap file supported the combined test and
was removed after it finished. All 291 existing project tests passed afterward.

| Component | Full trajectories | Measured cost change |
| --- | ---: | ---: |
| Frozen inverse-square-root lead | 200,540,928 | −5.0699% |
| Reference DQI | 102,400 | 0% |
| Banked chemistry | 254,464 | −3.2139% |

The measured relative aggregate score is 1.0286345856615866, an increase of
2.8635% over the accepted reference. Fresh chemistry confirmation passed
254,464 additional trajectories on the same extracted bytes with a distinct
salt. Its canonical chemistry submission identity and cost match the full
metric's chemistry receipt. The inverse-square-root bytes match the candidate
already verified and confirmed in the separate screen.

The archive SHA-256 is
`8fb545091a1cf66c2656bdce40bedbc26e478746301f9a777f56173f88b88503`.
The archive stays in local run storage. The branch retains the screen, artifact
manifest, component and confirmation receipts under
`docs/evidence/invsqrt-chemistry-20261107/`. This is full local combined
acceptance. A multi-benchmark release certificate is a separate step because
the existing release workflow registers one optimized benchmark per candidate.
