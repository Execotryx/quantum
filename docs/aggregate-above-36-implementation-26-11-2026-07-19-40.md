# Above-36 implementation and development measurements

The cloud-measured comparison is **33.20483975**. The independent project
release remains **26.78302388** with **26.78303192** from confirmation. The
implementation adds a strict above-36 portfolio audit. Certificate issuance
requires the complete metric on two fresh extractions, each with a distinct
registered salt and each with a cost product below **3.65042599 × 10²⁴**.
The previous certificate replay reproduced its original bytes.
[Comparison](evidence/aggregate34-20261126/public-cloud-audit.json) ·
[Earlier certificate](evidence/d4-open-successor-20261116/aggregate20/certificate.json) ·
[OpenSpec](../openspec/changes/raise-hybrid-aggregate-above-36/)

## DQI

The published v2 source stages reproduced the complete assembly hash. In both
256-shot panels, execution in stage order matched the unsplit simulation on all
counted operations, phase, syndrome, measured mask register and ancillas.
Both panels had zero observed value and phase errors.

| Stage | Executed Toffolis per shot, first panel |
| --- | ---: |
| Decoder return | 106,854.96 |
| Quantum decoder to field 1 | 90,686.54 |
| Field 2 to root-1330 phase | 76,946.15 |
| Complete circuit | 316,102.19 |

The three stages account for **86.84%** of the observed execution cost. All
60 verifier ancillas were nonzero on at least one trajectory at the
root-to-field-3 boundary. The number of nonzero values on any single trajectory
there peaked at 40. A reduction there needs a constructive schedule that
recomputes or re-encodes live values. The standalone lambda phase stage executed
zero Toffolis.
[Stage and boundary receipt](evidence/aggregate36-20261126/dqi-source-stage-boundaries.json)

## Inverse square root

The reproduced 39-qubit source parent remained 39 qubits in the combined
symbolic lifetime and reset rewrite. A separate carry rewrite replaced 93
temporary OR gadgets whose measurement outcome is consumed only by the
matching phase repair. Both members passed all **3,133,452** legal inputs with
one native shot per input. The rewrite reduced native instructions from
**24,387** to **23,922**. The one-shot charge was essentially unchanged
at **61,696.24**, against **61,696.30** for the matched parent and **60,927.61**
for the cloud comparison.
[Lifetime](evidence/aggregate36-20261126/invsqrt-lifetime.json) ·
[Control](evidence/aggregate36-20261126/invsqrt-control-native-one-shot.json) ·
[Rewrite](evidence/aggregate36-20261126/invsqrt-or-carry-native-one-shot.json)

The integer phase models also covered the complete legal domain. The
48-interval quartic used at most **13.33%** of the phase tolerance, and the
96-interval cubic used **26.93%**. A separate 29-bit accumulator would bring
the total to 51 qubits before selector or multiplication scratch. These
figures establish numerical margin for a streamed schedule.
[Integer phase model](evidence/aggregate36-20261126/invsqrt-segmented-pilot.json)

## Chemistry

The decoded seven-bit control passed both residual gates. The registered
fixed-dictionary refit retained the angle words and ran two starts per channel
count. Both offset choices used the pinned evaluator at each checkpoint.

| Channels | Best two-body residual, Hartree | Gate |
| --- | ---: | --- |
| 46 control | 0.01999999988 | Pass |
| 40 | 0.02828802 | Fail |
| 36 | 0.03895719 | Fail |
| 35 | 0.04239428 | Fail |

The pilot admits none of the reduced-channel checkpoints to full loader
pricing. The two local runs reproduced all three best checkpoint hashes.
[Registration and checkpoint evidence](evidence/aggregate36-20261126/fixed-dictionary/)

A separate 46-channel gauge search tested rotations within each channel pair.
These rotations preserve the two-body Gram and the one-body contraction when
weights and identity coefficients rotate together. The pair search found no
decrease at the reference, and the evaluator reproduced the effective
normalization of **46.91430**.
[Gauge receipt](evidence/aggregate36-20261126/channel-gauge/decision.json)

## Release status

No above-36 portfolio has passed component gates, so this round provides no new
complete cloud score. The measured reference and certified archive still
provide the comparison points.
