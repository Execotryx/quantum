# Coherent DQI padding across all decoder degrees

The new phase-stage entry takes compact reversed banks for a monic
locator and its evaluator, plus a six-bit degree. Both banks are
zero beyond their active coefficients. For degree (w), the same
(\lfloor(35-w)/2\rfloor) distinct irreducible quadratics multiply
both polynomials. An implicit factor (x) fills the final degree
for even (w). Its zero root lies outside the scanned points.
The two banks and degree restore on the same wires.

At a genuine locator root, the padded derivative is the original
derivative times the padding factor. The factor cancels with the
padded evaluator and has no zero at any scanned point. Thus both the
true support and each Forney value are preserved. The Windows value-only
gate replay checked forward and inverse padding, exact banks, and clean
scratch on two fixtures at each of the **36** possible degrees. A separate
polynomial oracle checked the roots and recovered values over all 4,095
points for those fixtures.

The first design used a common linear coefficient across all quadratics.
It left none of 256 stratified cases of weight zero through seven on
the regular derivative chart. Dilating one irreducible quadratic by
17 distinct field elements raised that to **255 of 256**. Across the
two 1,024-shot numerical verifier panels, varied slopes gave regular
derivative charts on **2,043** cases, including all sampled weight
bands, compared with **2,040** for the common slope. The five remaining
cases still require a chart guard and a recovery route.
[Stratified and sampled chart counts](evidence/aggregate36-20261126/dqi-degree-padding.json)

Each controlled source bit feeds both output coefficients through
linear maps. The emitter uses **13,464 controlled products per
direction**, before comparisons. With the previously measured
179,589-gate phase stage, the total is at least **206,517 gates**
before the comparisons, locator construction or routing. The software
replay establishes value correctness. The full-position native test
is prepared with one fixture per degree, and the WSL run on drive E
has yet to produce a receipt. The phase-stage footprint and charged
comparisons will come from that run.

The current development allocation leaves at most **73,483 gates**
for comparisons, locator construction and exceptional routing. The
best full cloud comparison remains **33.20483975**. Pyright and strict
OpenSpec validation passed.
[Previously measured phase stage](aggregate-above-36-dqi-projective-forney-26-11-2026-17-10-36.md)
