# Blocked regular-chart DQI suffix

Each local reciprocal step has the form
(F_i^{-1}=q_i+t^2F_{i+1}). The product of the first (k)
fractional-linear maps can be written
(F_0=(A F_k+B)/(C F_k+D)), with determinant (t^{2k}).
Writing (G=(D F_0+B)/t^{2k}) and (C=t^2 E) gives
(F_k=DG/(1+t^2 E G)). The circuit first multiplies the supplied
suffix by (E), inverts the unit series with its leading one and
zero implicit, divides by (E), and applies (D).

The fixture normalizes (D(0)) to one and compensates by moving
the scalar into (G) and out of (E). This keeps the supplied
summary at exactly 34 field words for the 17-step block. The
36-word suffix then fits beside it in the original 70-word bank.
The original untransformed prefix needed to produce this summary
and the prefolded suffix is still outside the emitted circuit.

| Supplied-summary fixture | First-fit qubits | Controlled products per direction |
| --- | ---: | ---: |
| Degree 3, one step | 111 | 870 |
| Degree 35, 17 steps | 879 | 35,238 |

Both directions matched the sequential scalar oracle on 12 genuine
syndromes at each degree. The replay checked preservation of both
summary banks, clean scratch, and zero residual phase. These are
software counts. The WSL native run on drive E still has no receipt.
The unchanged 70-term reciprocal also matched the scalar oracle and
its earlier native count of 36,354 at 879 qubits in software replay.
[Degree-3 fixture](evidence/aggregate36-20261126/dqi-blocked-suffix-3.json)
· [Degree-35 fixture](evidence/aggregate36-20261126/dqi-blocked-suffix-35.json)

The same Astra 6.2 investigation identified a second budget limit
that applies even if prefix extraction is free. At depth (i), the
existing continuant fold uses (i) coefficient products and
(2i+1) scalar normalizations. At 42 charged products per field
multiplication this is at least **76,440 gates each way** for all
35 folds, before final monic normalization. A viable blocked
locator needs a different way to produce the final pair.
[Sequential fold implementation](../src/qcompile/dqi/locator_fraction.py)

The single measured 17-step transform and its inverse use
**70,476** products. Combined with the guarded phase stage,
that leaves at most **12,577** under the 280,000-gate allocation
before comparisons, summary generation, final pair construction,
or routing. The best full cloud comparison remains **33.20483975**.
[Guarded phase budget](aggregate-above-36-dqi-chart-guard-26-11-2026-21-22-13.md)
