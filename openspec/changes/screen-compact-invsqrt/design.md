## Controls and instrumentation

The current direct KMB SHA-256 is
`dfaf3345abf3ff70e9a633bfd0cd07baa7e7bc7eb70105b557d09726ef1f5a8c`.
It scored 1,008,498.1176395753 using 199 declared qubits, 4,812
Toffoli-like gates, one T-like gate and 38 fine rotations. The
original reference and previous Newton circuit remain regression
controls. Parameterize the protocol and parent binding in
`tools/invsqrt_direct.py` and `tools/invsqrt_direct_hybrid.py` or the
shared release helper. The v1 config and v1 hybrid tool still point
to the earlier Newton parent. Preserve them as historical controls.
Use `configs/invsqrt-direct-v2.json` and the actual certified direct
parent ZIP from the [shared design](../prepare-next-hybrid-verification/design.md).

Rebuild the three controls before ranking. Instrument normalization,
coefficient lookup, arithmetic rows, phase, scaling and all reverse
steps. Reconcile declared versus live qubits, carry allocator behavior,
conditional counts and serialized operation count. Report actual
workspace peaks. The report's approximately 30 carry qubits are a
hypothesis until instrumented.

## Stage A — approximation and exact arithmetic

1. Add a deterministic coefficient procedure, initially separate from
   `src/qcompile/invsqrt/direct.py` in a focused `minimax.py`. Fit
   relative error `sqrt(u) * P(u) - 1` using bounded high precision.
   Document the interval partition, convergence criterion, coefficient
   signs, precision, ties and frozen integer table. Pin the table bytes
   for rebuilds. Solver convergence or a sampled plot alone cannot
   establish a polynomial error bound.
2. Screen the current Taylor cubic, a uniform dyadic minimax cubic and
   a uniform dyadic minimax quadratic using the existing retained
   coefficient and fused-row architecture. If those pass, test the
   reported two-region geometry as a separately registered variant.
   The 128-per-unit grid on `[1,2)` and 64-per-unit grid on `[2,4)`
   yields 256 rows and needs its own reversible address and residual
   mapping. Do not silently map it onto the current `segment_bits`.
3. Reuse `direct_screen.py` for the exact modulo phase64 targets and
   margins. The existing circuit shifts each selected partial-product
   row before summation. Model that exact recurrence rather than
   truncating the final product once. Prove intermediate sign, width
   and overflow behavior. For a sign pattern outside the existing
   alternating-magnitude Horner contract, add and test signed
   arithmetic as its own variant. Keep the integer bit for `x=1`
   and powers of four before scaling and phase reduction.
4. Keep four distinct evidence layers. Measure or bound ideal
   approximation error, account for coefficient quantization and
   actual finite-width row arithmetic, exhaustively check emitted
   semantics for all 3,133,452 inputs, and check the realized native
   circuit with differential fixtures and full verification. Preserve
   the worst relative error and minimum absolute margin witnesses
   separately. The incumbent's 27.29% is total emitted error, so it
   does not identify the ideal approximation budget.

## Stage B — reversible ablations

Compare each change to a frozen passing polynomial before trying a
combination.

| Change | Required proof and cost evidence |
| --- | --- |
| Coefficient precision and phase bits | Exhaustive arithmetic model, positive minimum remaining margin, native phase match and complete rotation pricing. More tolerance use can increase the score cost through the smaller synthesis margin. |
| Low-ancilla adder or signed-digit/windowed rows | Show control and borrow behavior, signed recoding, exact row shifts, carry cleanup and forward/reverse cost. |
| Binary normalization state | Store the leading-zero-pair shift reversibly, preserve original exponent information through normalization and verify both directions of each permutation, temporary expansion and scratch release. |
| Measurement-based unlookup | Reverse arithmetic until table outputs are restored. For every measurement branch show that the correction cancels the lookup-dependent sign with the address still live. Test arbitrary measurement masks, composition and missing-correction mutations. |
| Intermediate lifetime scheduling | Retain sufficient state or recompute it. Multiplication and truncation in `acc = acc*t+c` are non-injective, including at zero or even `t`; an overwrite requires a proven reversible construction. Price both directions and all retained or borrowed wires. |

The dense-encoding QROM construction's generic Hadamards are outside
the pinned kickmix gate set. Consider it only after a legal lowering
or directly usable phase-only construction is demonstrated. Keep
quantitative paper gains separate from actual native cost.
[Dense QROM](https://arxiv.org/html/2610.02321) ·
[Windowed arithmetic](https://arxiv.org/abs/1905.07682) ·
[Temporary logical AND](https://arxiv.org/abs/1709.06648) ·
[Piecewise arithmetic](https://arxiv.org/abs/1805.12445)

## Stage C — bounded verification and handoff

- Initially bound the search to 24 modeled/emitted candidates and
  40–64 engineering hours. Register exact geometry, quantized tables,
  ablations, time and memory limits after a control profile. Treat
  signed-digit/pebbled extensions as a separate bounded tranche.
  Reserve up to one hour for each full and confirmation run and
  measure the actual resource requirements. The complete archive
  still includes the reference DQI memory load if it is retained.
- Require zero failures, positive minimum margin and at most 90%
  tolerance use under the exact model. Initial promotion requires
  at least 10% lower complete cost than the current direct circuit,
  approximately **907,648.31** or less. A 10× official-reference
  result, at most 207,677.42, is a stretch envelope. Use the
  verifier's width, executed Toffoli-like/T-like counts and
  minimum-margin-dependent fine-rotation charge. Handle zero fine
  rotations separately. For data-dependent counts reconcile executed
  means or use a registered conservative bound at development.
- Native tests use the exact rebuilt KMB and include powers of four
  and segment edges at all reachable scales, endpoint and worst-case
  witnesses, carry/borrow and signed rounding, input preservation,
  scratch and measurement-branch phase. Exercise mutations of the
  segment map, discarded arithmetic bit, sign and cleanup correction.
- Freeze one qualifying KMB and its recipe, build again independently,
  run all 200,540,928 official trajectories and repeat with a fresh
  one-use confirmation on the same bytes. Keep current chemistry and
  DQI members by hash for the single-component successor. Follow
  shared lineage and paired archive checks before certifying a new
  score. Preserve the current release if none qualifies.
