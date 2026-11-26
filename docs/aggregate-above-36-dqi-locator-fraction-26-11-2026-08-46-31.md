# Regular in-place DQI locator measurements

The circuit uses the syndrome bank to store the linear continued fraction
and then reconstructs the monic locator and evaluator in those same words.
Each regular Euclidean step replaces a truncated series with its reciprocal.
The reciprocal updates run in descending coefficient order to preserve their
sources. The adjoint returns both physical banks to the original syndrome.

| Degree | Emitted scope | Declared qubits | Charged gates per direction |
| --- | --- | ---: | ---: |
| 3 | Complete locator and evaluator | 111 | 5,598 |
| 7 | Complete locator and evaluator | 207 | 21,666 |
| 35 | First 70-term reciprocal | 879 | 83,394 |

All three focused native tests passed on Ubuntu on drive E. The reduced
tests check the locator, evaluator, phase and restoration. The degree-3
test also composes construction, a 63-position residue scan and cleanup
in one circuit. The degree-35 probe checks forward and inverse against
the scalar recurrence on 12 inputs.
[Degree 3](evidence/aggregate36-20261126/dqi-locator-fraction/locator-3.json)
· [Degree 7](evidence/aggregate36-20261126/dqi-locator-fraction/locator-7.json)
· [Degree 35](evidence/aggregate36-20261126/dqi-locator-fraction/locator-35.json)

Because this circuit constructs the evaluator along with the locator,
its relevant downstream control is the **197,937-gate** supplied-evaluator
phase stage. That leaves **82,063 gates** under the 280,000-gate development
allocation. The first reciprocal and its inverse alone cost **166,788**,
bringing the subtotal to **364,725** before subsequent locator steps,
continuant folds and routing. This rules out the measured sequential
reciprocal schedule for that allocation.
[Supplied-evaluator phase stage](aggregate-above-36-dqi-series-scan-26-11-2026-08-26-30.md)

The full cloud comparison remains **33.20483975**, and the independently
confirmed project metric remains **26.78302388**.

Using the public comparison's measured inverse-square-root cost of
60,927.61 and chemistry cost of 249.17M, the strict 36-point ceiling for
DQI is **240.46B**. At the planning DQI cost of 280B, retaining the same
inverse-square-root result would require chemistry below **213.98M**.
These ceilings follow from dividing the registered cost-product limit
by the two companion costs. They keep a prospective decoder gain tied
to the companion improvements needed for the full archive.
[Measured companion costs](above-34-cloud-reference-comparison-26-11-2026-06-31-00.md)
