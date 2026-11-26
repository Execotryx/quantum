# Padded DQI phase with reciprocal orientation

The numerical sampler supplied 6,144 inputs in three panels.
The primary padded derivative chart failed on 26. Changing the
successive quadratic dilation exponent from 137 to 149 recovered
13. Reversing the syndrome with the original padding recovered all
26, including the weight-35 case with no padding. This screen tests
classical chart admission. The circuit still needs a coherent way
to choose the orientation and obtain its locator and evaluator.
[Paired chart observations](evidence/aggregate36-20261126/dqi-alternate-padding.json)

With moments (S_j=\sum e x^j), reversing (S_1,\ldots,S_{70})
moves ((x,e)) to ((x^{-1},ex^{71})). A supplied orientation bit
enables a correction at each root. The correction cancels the phase
at the current mask address and applies the inverse field dilation
against the original mask address. The same padded derivative action
serves either orientation. The additional root control costs one
emitted product per position.

| Full-position software replay | First-fit qubits | Explicit product gates before comparison lowering |
| --- | ---: | ---: |
| Original orientation | 885 | 188,757 |
| Live orientation bit | 886 | 192,852 |

The replay checks phase, both coefficient banks, degree, mask
registers, and scratch across all 4,095 positions with one fixture per
weight and two measurement seeds. The live-bit test mixes the two
orientations in one execution. These figures describe software
replay of the gate emitter. Native serialization and phase validation
on drive E still have no receipt.
[Original orientation replay](evidence/aggregate36-20261126/dqi-padding-phase-software.json)
· [Live orientation replay](evidence/aggregate36-20261126/dqi-padding-orientation-software.json)

The best full cloud comparison remains **33.20483975**. A degree-35
submission handoff requires the complete decoder and the passing
cloud and independent confirmation receipts.
