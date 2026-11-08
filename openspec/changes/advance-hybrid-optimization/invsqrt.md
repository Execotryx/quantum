# Inverse-square-root width and cleanup

## I1. Freeze and profile the current control

- Extend `tools/invsqrt_direct.py` with a separate prospective v3
  registration and a proposed `configs/invsqrt-direct-v3.json`. Keep
  v1, v2 and their receipts intact. Reproduce the v2 minimax quadratic
  with segment bits 7, fractional widths `[30, 24, 18]`, fused rows
  and lookup-workspace reuse. Pin KMB SHA-256
  `3ae33a3d0101085613ac6bfc1b1ab7dde6b8f35f7ebd84d0976ba66a0772f799`
  and its coefficient table. The control is 175 declared qubits,
  4,436 Toffoli-like gates, one T-like gate, 37 fine rotations and
  cost 820,078.9505284121.
  [Screen receipt](../../../docs/evidence/next-hybrid-20261108/invsqrt/minimax-quadratic.json)
- Instrument `src/qcompile/invsqrt/direct.py` construction and the
  runner without changing serialized control bytes. Record stage
  forward and reverse counts, wire lifetimes, allocated and declared
  peaks, internal carry use and transient expansions. The current
  arithmetic already uses temporary-AND cleanup. Treat the difference
  between explicit registers and declared peak as a liveness
  investigation before counting any saving.

## I2. Implement independent reversible ablations

- Start with a simple legal phase-repair reference in a focused
  `unlookup.py` if the primitive warrants a module. When coefficient
  outputs have returned to the pure lookup word `T(a)`, measurement
  with outcome mask `m` leaves phase `(-1)^(m·T(a))`. Apply the same
  diagonal sign while address `a` is still live. Derive basis-mask
  and composition proofs, then compare a high/low address split with
  a Reed–Muller repair. Use the pinned native gate set and measure the
  classical parity and physical scratch cost. A published unlookup
  budget that uses generic coherent Hadamards needs a different legal
  lowering.
  [Temporary logical ANDs](https://arxiv.org/abs/1709.06648) ·
  [Phase-only Coulomb unlookup](https://andigu.github.io/projects/uncompute/coulomb-potential.html)
- Prototype binary normalization separately. The exponent shift
  ranges from 0 to 10, so four stored bits replace ten flags before
  conversion scratch. Derive count preparation, input normalization,
  output scaling and their inverses. Compare compressed-state storage
  and a logarithmic shifter with full transient width accounting.
- Once the unlookup passes, compare staged coefficient lifetimes.
  After forming the quadratic inner accumulator, erase the unchanged
  pure `c2` word and reload it before reversing the producing step.
  Retain modified accumulators until their inverses can reconstruct
  their inputs. Measure reload costs and peak width across both halves.
- Extend `minimax.py` and `direct_screen.py` with explicit geometry
  and precision variants. Model each truncated row before summation,
  including signedness, overflow, discarded bits and scaling. A
  proposed 256-row geometry uses 128 intervals on `[1,2)` and 128
  on `[2,4)`. Register its distinct address and residual mapping.
  Preserve the integer coefficient bit through scaling. Evaluate
  signed-digit or windowed arithmetic in a separate tranche once a
  reversible state and rounding model exist.
  [Windowed arithmetic](https://arxiv.org/abs/1905.07682)

## I3. Screen, measure and promote

- Extend `tests/test_direct_invsqrt.py` and
  `tests/test_direct_invsqrt_native.py`. Cover every shift on small
  widths, powers of four and their neighbors, every legal interval
  boundary, worst-margin witnesses, arbitrary measurement masks,
  carries and borrows. Test mutations of the correction, reverse
  shift, segment mapping, discarded arithmetic bit and scratch
  cleanup. Compare native reloaded KMB phase, input restoration and
  zero scratch after composition. Extend the runner's count report
  before evaluating variants with branch-dependent counts. Record
  executed means, extrema and a conservative development bound.
- Screen all 3,133,452 legal inputs with zero failures and at most
  90% tolerance use. Price width, executed gates and fine rotations
  using the candidate's minimum margin and the existing zero-rotation
  case. The prospective cost ceiling is 738,071.0554755709, a 10%
  reduction from v2. The width target near 130 qubits remains a
  design hypothesis. Combine only ablations that separately passed
  the correctness and measured improvement gates.
- Register at most 24 modeled or emitted attempts in the first tranche,
  including controls. A proposed cap allocates four controls, three
  unlookup repairs, two normalization variants, four precision
  variants, three lifetime variants, four geometries and four
  combinations. Timebox planning at 40–64 engineering hours and
  budget native tests after control profiling. Promote at most one
  frozen KMB. Rebuild it independently and run the full 200,540,928
  trajectories and a distinct fresh confirmation before archive handoff.
