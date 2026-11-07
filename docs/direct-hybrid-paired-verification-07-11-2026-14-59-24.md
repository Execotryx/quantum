# Direct-phasing hybrid archive and paired comparison

The rebuilt successor ZIP has SHA-256
`2500a815dd16a9b04185fa8f1c44b6c96e33d38a4d5d397d2bad3b7ab61d9fac`.
Only `invsqrt.kmb` differs from the parent. Full metric coverage was
200,540,928 inverse-square-root, 102,400 DQI and 254,464 chemistry trajectories.
The measured successor score was **1.2861761126**. Its component cost and
phase margin matched the independent confirmation.

The first full archive attempt stopped during DQI. The same ZIP and
registered seed completed on retry with 8 GiB of temporary workspace-drive
swap. The retry sampled a peak of 7,494,864,896 bytes of process-tree PSS
and 9,679,470,592 bytes of PSS plus swap. Those are sampled measurements.

The original parent and successor DQI receipts both report zero value and
phase errors and the same repetition factor. Their mean executed Toffoli
counts are 5,725,107.878232422 and 5,725,109.06765625. The DQI circuit bytes
match. The unpaired cost difference triggered the exact retained-cost guard.
The parent replay uses the successor's already registered archive seed,
with its full report pinned before the replay. This provides a matched
comparison without reusing either component confirmation seed.

## Matched result and certificates

The paired parent reproduced its original ZIP byte for byte and passed the
full metric at **1.0286345144**. Both archives then measured the same DQI
cost of **24,439,466,510,149.91** and chemistry cost of **3,247,752,448.67**.
The direct-phasing successor's **1.2861761126** score is **25.0372%** higher
under those matched conditions.

- [Paired comparison](evidence/invsqrt-direct-hybrid-20261107/comparison.json)
- [Parent certificate](evidence/invsqrt-direct-hybrid-20261107/paired-parent/certificate.json)
- [Successor certificate](evidence/invsqrt-direct-hybrid-20261107/certificate.json)
- [Benchmark-scoped confirmation ledger](evidence/invsqrt-direct-hybrid-20261107/confirmation-ledger.json)

The ledger contains three independent confirmations, one for each optimized
parent benchmark and one for the successor inverse-square-root circuit. The
successor certificate links the parent's chemistry confirmation by protocol
and certificate hash. All 11 retained archive members and both independent
builds per archive matched by SHA-256.
