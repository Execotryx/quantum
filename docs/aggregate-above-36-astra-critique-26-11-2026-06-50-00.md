# Independent Astra review of the above-36 route

An Astra subagent at high reasoning audited the initial cost allocation,
source claims, and experimental gates. It reviewed the frozen cloud
receipts, pinned verifier functions, and primary papers, and ran the
fixed-dictionary chemistry calculations below in Ubuntu WSL. The report and
implementation plan incorporate the resulting changes.

## Findings and dispositions

| Priority | Finding | Change to the plan |
|---|---|---|
| High | The editable DQI build reconstructs the dominant stages as inherited assembly. Its generated D16 patches account for just 616 static Toffolis. The source-built and cloud comparison hashes also differ. | Recover exact semantic boundaries under a cap, measure actual executed counts, and verify the candidate at those boundaries and in the complete circuit. Use explicit shared input panels for attribution and hash-bound salts for official pricing. |
| High | Reaching 888 qubits alone prices near 298.317B at the cloud reference's mean gates and one-error multiplier. At that width, 280B allows about 296,712 mean gates at one error or 290,336 at eight. | Price non-overlapping savings by observed execution frequency. Charge both passes, mask phase repayment, and recovery. Require a single-bank schedule or a measured alternative below the width-cost frontier. |
| High | The direct-phase BM paper uses different resources and correctness conditions. The challenge supplies fresh 12-bit classical masks, so fixed compiled weights or a phase result on a single mask cannot establish correctness. | Check the dual trace map on unit masks across the supported points and prove phase composition and gauge correction for arbitrary masks. |
| High | The analytic approximation budget does not settle inverse-square-root storage. A separate 24-bit accumulator alongside 22 input bits would already exceed the proposed 34–35 qubit width before selector and product work. | Gate emission on a concrete borrowed-input or streamed schedule with complete selector, cleanup, and synthesis price. |
| High | Chemistry's 220M allocation includes headroom. The strict chemistry limit is 232.808M with the two budgeted companions. A cheaper fixed-dictionary pilot can preserve the decoded table while reducing channel count. | Test the channel continuation first, then choose bounded variable-basis fits by their measured cost deficit. Use the 36.5 development target as preferred margin and report actual headroom. |

The 900-qubit source attribution has 840 input bits. At 316,123 mean gates
and the observed one-error penalty, a width-only route to 280B would need
about 860 total qubits or less. The DQI resynthesis must therefore change
arithmetic or reach a substantially different storage arrangement.
[Parent file identities](evidence/aggregate34-20261126/tonylica-builds.json)
· [Cloud DQI resource receipt](evidence/aggregate34-20261126/public-cloud/verification/benchmark-dqi.json)
· [Direct-phase paper, supplement I.1](https://arxiv.org/html/2610.22367v1#A1.SS1)

## Fixed-dictionary chemistry validation

The pilot used the public NPZ at SHA-256
`9f472ae472b2eae95940a55cf899fb000861c624a294feb021a4d6ffd6340d67`.
Decode its seven-bit `angle_words` as words divided by 64 with the pinned
`reconstruct_u_vectors` and original `tree_edges`. For the two-body
diagnostics, take the last 1,143 vector rows in order and reshape to
`(9,127,76)`. Keep the one-body rows for a full candidate verification.
Construct the target with the official reference integrals and its fixed
symmetry shift through the repository's `shifted_target`. Evaluate the
fixed-dictionary PSD rank relaxation at `9*C`.

For each rank group form `F=svec(u uᵀ)` and `X=WᵀF`. Take the leading
`C` right singular vectors of `Xᵀ`; multiply both the weights and the native
offset row by that basis. Export stored offsets as the new native offsets plus
the column sums of the new weights. Use the true full two-body Frobenius
residual to score the initializer.

| Channels | Modeled fixed Toffolis | Fixed-dictionary residual estimate (Ha) | Truncated initializer residual (Ha) |
|---:|---:|---:|---:|
| 46 | 6,500 | 0.013095 | 0.020000 |
| 40 | 6,024 | 0.014183 | 0.031995 |
| 36 | 5,706 | 0.016542 | 0.047639 |
| 35 | 5,628 | 0.017810 | 0.053662 |
| 34 | 5,548 | 0.019427 | 0.060743 |
| 33 | 5,470 | 0.021489 | 0.068888 |
| 32 | 5,389 | 0.023894 | 0.078826 |

The rank-relaxation results are floating-point estimates for this dictionary.
Dropping the last group's 127 vectors gives a **0.034625 Ha** fixed-dictionary
estimate at `(8,127,42)`, while the unrestricted rank-336 estimate is
**0.009130 Ha**. A new dictionary could be feasible. A 35-channel
initializer at nine groups starts far above the tolerance. Continue
through 40, 36, and 35 with fitted checkpoints and validate the exact decoded
one-body residual, gap, and normalization. When (R) and (B) hold, retaining
the ANGLE layout leaves 78,016 full trajectories. The chemistry submission
digest includes the factorization arrays, so each new NPZ needs fresh native
evaluation even with identical loader bytes.
[Global relaxation receipt](evidence/aggregate36-20261126/chemistry-psd-rank-relaxation.json)
· [Repository fixed-basis diagnostic](../src/qcompile/chemistry/bounds.py)
· [Pinned verifier contract](../contracts/contract.json)
