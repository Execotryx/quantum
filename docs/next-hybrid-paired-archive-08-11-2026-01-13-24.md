# Full verification of the v2 hybrid archive

The pinned evaluator measured **1.3779715417804443** for the v2 hybrid,
up from **1.286176112637598** for the certified comparison archive.
The **7.137081%** gain comes from the minimax quadratic
inverse-square-root circuit. The retained DQI and chemistry members,
archive seed and measured costs match the certified control.

| Benchmark | Certified cost | v2 archive cost | Trajectories |
|---|---:|---:|---:|
| Inverse square root | 1,008,498.1176395753 | 820,078.9505284121 | 200,540,928 |
| DQI | 24,439,466,510,149.91 | 24,439,466,510,149.91 | 102,400 |
| Chemistry | 3,247,752,448.668952 | 3,247,752,448.668952 | 254,464 |

The inverse-square-root component is 18.68% cheaper and uses 175
declared qubits, down from 199. Its worst input used 26.19% of the
allowed phase error. The independent rebuild, full component pass,
fresh confirmation and archive verifier all bind KMB SHA-256
`3ae33a3d0101085613ac6bfc1b1ab7dde6b8f35f7ebd84d0976ba66a0772f799`.
Each of the three verifier passes completed 200,540,928 trajectories.

The two independent archive builds and the VM rebuild reproduced ZIP
SHA-256
`9aac7afcd0ff3bbff7f4c65c85cf1b331e67b3fd9893ec83b8499d0f223bb841`.
The evaluator read a fresh extraction. Its DQI value and phase error
counters, mean executed gate count and scored cost matched the parent.
The local [lineage check](evidence/next-hybrid-20261108/lineage-check.json)
resolved the retained members through the trusted parent certificate.
This is a complete measured archive comparison. Formal candidate-store
release selection and certificate issuance are separate steps.

## Execution and receipts

The VM ran the full component pass in 1,340.61 seconds and the complete
paired archive in 1,898.94 seconds. To fit the approved one-hour VM
runtime, the archive moved ahead of the separate confirmation. The
initial cloud confirmation stopped before producing a receipt. The
standalone WSL confirmation used a distinct registered salt and completed
in 125.73 seconds with 12 workers. The VM was stopped after the verified
archive receipts reached storage. Compute Engine reported `TERMINATED`
after 58 minutes and 21 seconds of runtime. The temporary local swap file
was removed.

- [Full component receipt](evidence/next-hybrid-20261108/full-invsqrt/full.json)
- [Fresh confirmation receipt](evidence/next-hybrid-20261108/confirmation-invsqrt/result.json)
- [Complete archive verification](evidence/next-hybrid-20261108/paired-archive/verification.json)
- [Paired comparison](evidence/next-hybrid-20261108/paired-archive/comparison.json)
- [VM progress log](evidence/next-hybrid-20261108/paired-archive/progress.log)

The isolated [2,560-shot DQI control retry](evidence/next-hybrid-20261108/dqi/prospective/control.json)
reused the registered cases. Both runs returned zero disjoint failures
and byte-identical receipts with repetition factor 4.941658. The
[resource sample](evidence/next-hybrid-20261108/dqi/prospective/resources.json)
recorded about 7.01 GiB peak process-tree PSS and 2.02 GiB peak swap PSS.
The optimized DQI work remains at the update-slice stage. The measured
chemistry refit remains below its promotion threshold.
