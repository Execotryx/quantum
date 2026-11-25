# Added transpose window at capacity14

Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
Credits: Opus and Astra.

## Status and exact proposed change

This packet prepares a **38-T paired preimage saving at Q889**, relative to
the selected v4 preimage. It changes only the public placement of an already
implemented transpose tensor: the lower windows remain17 and14, and the
transpose windows become17 and14 instead of17 alone. No native run, whole
candidate, official price or new population certificate is claimed here.

`transpose14_core.py` is an exact copy of the frozen
`blocks/transpose_handoff_core.py` with its recursive window import changed
to `transpose14_window`. `transpose14_window.py` changes only that core
import and the public `TRANSPOSE_WINDOWS` constant. The complete literal
derivation, including the adapted checker, is in `SOURCE_DERIVATION.json`.
Neither accepted source file is edited.

For integration, bind the existing `transpose_handoff_outer.core` to the new
core, bind `Pipeline.Core` and `Pipeline.Window` to the two new modules, and
require `Window.C is Core`. Both core and outer must still use the selected
`paired_phase63` provider. Keep the retained forward tensor, transpose
handoff tensor, parked-phase helper and finish/scan providers unchanged.
The outer module needs no source copy. This packet is a component variant;
the parent integration must bind and test the complete candidate separately.

## Complete caller price

For three virtual frames starting at capacity n, the two-RHS ordinary upper
borders cost252n−432. At n=14 this is3096 T. The historical shared transpose
has m=n−3=11 low words and costs168m+964=2812 T. Its partial/shared borders
cost264 T and its third-source seam costs100 T, so the old added transpose
cost2812+264+100−3096=80 T per direction. That is the old160-T paired closure
in `after_c5/extractor_width/window_selection/WINDOW_SELECTION_PAPER_SCREEN.md`.

The current retained transpose costs168m+876=2724 T, an88-T reduction. Its
explicit returned third-source predicate removes one later11-T caller query.
The current added caller therefore costs

    2724 + 264 + (100−11) − 3096 = −19 T

per direction, or **−38 T per complete pair**. The unchanged lower window
already delayed its local operations, so no local-query saving is counted
again. The original320-static/160-mean local-mask deferral, the existing
forward improvements and the existing top17 transpose savings are already
inside the v4 baseline and receive no second credit.

| Metric | Selected v4 preimage | Proposed transpose14 variant |
|---|---:|---:|
| Prefix static T | 57,053 | **57,034** |
| Paired static T | 115,081 | **115,043** |
| Paired fresh-HMR expectation | 114,514.87007855662 | **114,476.87007855662** |
| Quantum peak | 889 | **889, pending native check** |
| Forward tensor calls | Four: two m14, two m11 | Same four |
| Transpose tensor calls | Two m14 | **Two m14 and two m11** |
| Actual third-flag handoffs | Two at frame15 | **Four at frames15 and12** |
| Paired quotient-phase calls | 18 | Same18 |

The new exact expectation is3933395305086733/34359738368. Every changed
nonlinear gate in this placement delta is unconditional, so the static and
fresh-mask mean deltas are both−38. The full checker requires the complete
event multiset to equal the actual frozen v4 component receipt, not merely
its rounded mean. That multiset has18 inverse-phase27 events,16 conditional
zero-predicate events,18 occurrences of each of the three paired63 events,
and two parked-scale mask guards. The prefix still has only its one
parked-scale mask guard.

Applied alone to the v4 whole source ledger, this would change384349 static
T to384311 and383546.21657799964 expected T to383508.21657799964. Those are
composed source models, not newly emitted whole-decoder results. The separate
first-two retained-norm195 proposal is not included in these numbers.

## Source, flag and phase lifetimes

The added window is entirely virtual: its public capacities are14,13 and12.
It uses the same source views and partial-border schedule as the existing
lower14 window. The transpose returns a one-use `ThirdFlagHandoff` whose
actual quantum bit is exactly zero of the physical third source word.
Here the witness is frame12; the existing top17 transpose's witness remains
frame15. The handoff checks the builder identity, exact wire tuple and
single ownership before `Step.adopt` accepts it.

On the inverse half, the third source is restored before the transpose.
`adopt(pay=True)` pays every merged source-predicate and same-half local
mask on the returned bit before the source changes again. On the other
half, `adopt(pay=False)` supplies the bit needed by the immediate source
operation; its accumulated masks remain owned by the same Step and are paid
at the existing later restored-source query. The extra compact reciprocal's
mask is merged into `Step.debt` and paid by CZ when that reciprocal is
recreated. It does not introduce another inverse-phase27 event.

The four handoffs must be exactly

    (frame12, prefix, pay=True), (frame15, prefix, pay=True),
    (frame15, closing, pay=False), (frame12, closing, pay=False).

No new quantum predicate survives into a local division. The returned bit
replaces the caller's next allocated/query bit. The tensor uses the same
25-helper ceiling; the already parked gauge supplies the existing one-bit
loan. Top17 gauge moves,14 park/unpark pairs, two parked-phase payments and
the single top16 gauge requery remain unchanged. All32 local masks and all
source inverse, quotient and flag masks must be retired at the final seam.

## Domain and fixture coverage

The capacity14/12 simultaneous-gap exclusion is already required by the
unchanged lower14 tensor. Degree drops above two, nonconstant terminal gcd,
and the17/15 exclusion also remain unchanged. Adding the transpose needs no
new input event, profile oracle, padding convention or compiler parameter.

The original full256 converter cases all have mode000 at frames14/13/12.
They are retained without replacement. They still exercise both sparse
gauge charts and128 forced top17 gaps, but they must not be advertised as
nonordinary capacity14 coverage.

The new full checker appends **ten component-domain cases**, giving266
total, from five exact previously saved physical records in the original
10073-case fixed corpus. Their canonical padded locators are recomputed by
the unchanged pure classifier and independently checked by the old preimage
oracle. Arbitrary nonzero RHS banks are reused from the frozen256-case
component panel; each locator is paired with both sparse gauge charts.

| Existing corpus indices | Window mode | Original weights | Full decoder status | New component cases |
|---|---|---|---|---:|
| 3605 | 100 | 10 | Excluded only by cutoff15 | 2 |
| 3205,3320 | 010 | 9 | Excluded only by cutoff15 | 4 |
| 5894,6385 | 001 | 19,21 | Admitted | 4 |

All five full35 locators satisfy the complete preimage-domain conditions.
The three weight9/10 physical inputs remain outside the complete decoder's
domain; this component test does not relabel them as newly admitted. No
physical input or population draw is generated. The exact old records,
source hashes, RHS lineage and padded coefficients are preserved in
`EXISTING_PROFILE_SUPPLEMENT.json`.

The isolated m11 checker separately covers the four admitted local modes
000,100,010,001, including actual observation and nonlinear probing of the
returned flag. It runs the frozen checker unchanged with the fixed size11.
Its core count is2724 T; prefix fixture closure adds44, and pair closure
adds55 per invocation plus three probe gates, giving2768 and5561 T. Those
fixture closure costs are not the actual full caller's delta.

## Root-only native queue

Run only through the existing shared heavy-job guard. None of the following
commands has been executed as part of this source preparation. Use fresh
output directories; stdout and guard receipts should be adjacent, outside
the initially empty output directory.

```bash
/usr/bin/python3.13 -B controller_work/after_v3/k24/v5_transpose14/check_handoff_m11.py --smoke --output controller_work/after_v3/k24/v5_transpose14/runs/handoff-m11-smoke
/usr/bin/python3.13 -B controller_work/after_v3/k24/v5_transpose14/check_handoff_m11.py --output controller_work/after_v3/k24/v5_transpose14/runs/handoff-m11-full
/usr/bin/python3.13 -B controller_work/after_v3/k24/v5_transpose14/check_transpose14_preimage.py --smoke --output controller_work/after_v3/k24/v5_transpose14/runs/preimage-smoke
/usr/bin/python3.13 -B controller_work/after_v3/k24/v5_transpose14/check_transpose14_preimage.py --output controller_work/after_v3/k24/v5_transpose14/runs/preimage-full
```

The isolated full panel has256 cases, three seeds and two identical builds
for each prefix/pair shape. The full caller panel has the original256 plus
ten explicitly labeled supplement cases, three seeds, identical prefix and
pair builds, independent prefix values, full paired nonlinear phase and
restoration, exact T/Q and event assertions, and all four actual handoffs.
The caller smoke panel keeps eight old cases plus all ten supplement cases.
Prefix arithmetic phase debts are correctly left open until the closing;
only paired phase is asserted by the full preimage checker.

Source preparation performed exact literal-copy/AST checks and five bounded
pure-classical padded-locator reconstructions. It performed no native run,
statistical draw, circuit build, or official verification. The source model
must remain pending until these component gates and the subsequent complete
candidate gates pass.
