# Source-level inverse-square-root research

Academic Research was applied as an inline quick brief. The question
was which published arithmetic or uncomputation technique warrants a
source build under the verifier's input, phase, and scratch contract.
Creative Investigator attempted a separate public-source search and
returned `Invalid API key` before generating a report, at $0.00
reported spend.

## Decision

Use the measured 39-qubit generator for the next register and
phase-repair comparison. For a larger arithmetic change, prototype
a **streamed piecewise quadratic** around the independently passing
192-row fixed-point model. The conventional coefficient schedules
already expose a width and lookup bottleneck. Measure the complete
product and cleanup lifetimes before investing in a full emitter.
[Measured source control](evidence/aggregate36-20261126/invsqrt-control-native-one-shot.json)
· [Competition paper and circuit contract](https://arxiv.org/abs/2610.23832)

The source-built DQI and chemistry prices leave an inverse-square-root
ceiling of **52,119.68** if this component supplies the entire gain to
35. The frozen 39-qubit inverse-square-root costs **61,696.23** in the
publisher's full receipt. At 39 qubits the budget is **1,336.40**
charged equivalents per input, versus about **1,581.96** in our
one-shot control. A 35-qubit design can spend **1,489.13**, and a
51-qubit design can spend **1,021.95**. These are conditional budgets
based on recorded companion prices.
[Source-built companion prices](evidence/aggregate36-20261126/public-frontier-v220.json)

## Ranked source changes

1. **Stream a centered quadratic with a narrow inner product.** Häner,
   Roetteler and Svore establish piecewise arithmetic as a synthesis
   route, including for inverse square root. A cached alexon-v8 README
   describes a related narrow-tail quadratic and claims a cost of
   **22,411.95** at 51 qubits. GitHub's API and raw-file endpoints
   returned HTTP 404, and the available circuit catalog supplied no
   matching artifact. Treat the reported cost as an unverified lead.
   The numerical model below was written independently from the
   public description.
   [Piecewise arithmetic paper](https://arxiv.org/abs/1805.12445)
   · [Publisher repository](https://github.com/alexon-v8/quantum-circuit-compilation-invsqrt)
2. **Reschedule a measured repair and reuse the freed wire.** Gidney's
   temporary AND and MBUndo explain when a measured ancilla can be
   cleared through a conditional phase correction. Reqomp gives a
   way to trade recomputation for width. Apply the ideas to a bounded
   forward and reverse source region. A deferred phase use must see
   the same Boolean function and measurement guard. The source
   control already uses measurement cleanup. Its previous OR-carry
   rewrite cut instructions and left the charged cost effectively
   unchanged. A smaller width or a measured reduction in executed
   Toffolis is needed to carry this route forward.
   [Temporary AND](https://arxiv.org/abs/1709.06648)
   · [MBUndo](https://arxiv.org/abs/2611.02345)
   · [Reqomp](https://arxiv.org/abs/2212.10395)
   · [OR-carry result](evidence/aggregate36-20261126/invsqrt-or-carry-native-one-shot.json)
3. **Compare lookup layouts at their actual peak.** SelectSwap trades
   fewer non-Clifford gates for additional dirty workspace. The
   appropriate comparison is the complete declared width with the
   borrowed input restored, plus the actual cleanup and phase costs.
   A direct bank swap is contingent on that layout fitting the
   arithmetic budget.
   [Low, Kliuchnikov and Schaeffer](https://arxiv.org/abs/1812.00954)

## Reproducible checks

The model uses 29 fractional bits for the coefficients. It fixes a
curvature value per group and fits the two affine coefficients by
minimizing the sampled residual span. The emitted integer oracle
rounds both Horner products and truncates the inner local argument.
With 192 intervals and 12 retained local bits in the inner product,
the model used **68.85%** of tolerance at worst across all
**3,133,452** legal inputs. Repeating the comparison with the pinned
verifier's reference function gave the same result. A coarser
curvature table with 384 affine rows and 192 curvature rows passed
at **55.04%** tolerance use. The 96-interval geometry and the
192-interval geometry with grouped curvature failed the screen.
[Numerical driver](../tools/invsqrt_coarse_curvature.py)
· [All model lanes](evidence/aggregate36-20261126/invsqrt-coarse-curvature-model.json)

The native lookup slices reserved the real 22-bit input, used the
sibling-CNOT unary traversal, and checked lookup and measurement
cleanup over all 192 addresses with eight trajectories per address.
Joint loading and cleanup charged **213 Toffolis at 104 qubits**.
Separate passes also charged **213** each and peaked at **65**, **59**,
and **52** qubits for the constant, slope and curvature. At the
65-qubit peak, three passes plus an illustrative 33 fine rotations
priced at the measured model margin already project **56,112.34**
before either multiplication. The next experiment should fuse the
two smaller coefficients into the product schedule and stream the
constant late. Measure normalization, phase alignment and arithmetic
at that actual width before ordering a complete native run.
[Slice registration](evidence/aggregate36-20261126/invsqrt-coarse-curvature-lookup-registration.json)
· [Native slice receipts](evidence/aggregate36-20261126/invsqrt-coarse-curvature-lookup.json)

The numerical pass and lookup fixtures leave full reversible
arithmetic, independent builds and paired cloud certification open.
