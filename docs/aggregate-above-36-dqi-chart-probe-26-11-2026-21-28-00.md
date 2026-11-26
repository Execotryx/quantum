# Locator-only DQI chart decision and retry budget

The standalone probe pads the compact locator, computes the regular
Euclidean chart predicate from its retained heads, and removes the
padding. It XORs the predicate into a caller's bit while preserving
the degree and both input banks. Its Euclidean traversal skips all
payload reduction and extension work.

The packed gate replay checked 36 regular cases spanning all supported
weights and four nonregular cases. Applying the probe twice restored
the destination bit, whose initial values were mixed. The input banks
and degree were identical after each application, with zero phase
and clean scratch. One application used **887 first-fit qubits**,
**30,396 controlled products**, and **107 equality calls** before
native lowering of comparisons.
[Standalone chart receipt](evidence/aggregate36-20261126/dqi-padded-chart-only.json)

Setting and clearing the orientation bit with this probe costs at
least **60,792 gates**. The guarded phase emitter contributes
**196,947**, leaving at most **22,261** under the 280,000-gate
development allocation. This leaves out comparison lowering, the
controlled syndrome reversal, and all locator work. Even one
**36,354-gate** reciprocal from the measured locator schedule exceeds
that remainder. The separate chart-probe retry and sequential
locator therefore do not fit together.
[Guarded phase](aggregate-above-36-dqi-chart-guard-26-11-2026-21-22-13.md)
· [Locator measurements](aggregate-above-36-dqi-middle-product-26-11-2026-16-47-11.md)

Six software tests, Pyright, and strict OpenSpec validation passed.
The native WSL run on drive E still has no receipt. There is no
new certified degree-35 decoder or cloud score.
