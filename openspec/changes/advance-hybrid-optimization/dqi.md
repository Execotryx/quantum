# DQI implementation

## D1. Establish the contract and build clean arithmetic

- Pin the reference and slice receipts. Record the 70 little-endian
  12-bit syndrome registers, 4,095 runtime classical masks, field polynomial
  `0x1053`, primitive-element position convention, and correction radius 35
  from the pinned verifier and `src/qcompile/dqi/{field,decoder}.py`.
  Preserve all 840 public syndrome qubits and clear private scratch.
  The measured controls are 144 Toffoli-like gates for multiply-XOR, 1,440
  for the clean standalone inverse-XOR, and 327 for the native phase slice.
  [Native slice receipts](../../../docs/evidence/next-hybrid-20261108/dqi/slice-comparison.json)
  The research companion fixes polynomial `0x10EB` and a deterministic
  mask stream. Keep the existing native inverse-with-scaffold in the
  phase-tail control until a measured clean challenger wins.
  [Companion contract](https://raw.githubusercontent.com/andigu/uncompute/main/tasks/dqi-reed-solomon/contract.json)
- Add `src/qcompile/dqi/tower.py` as a deterministic mathematical module.
  Construct the GF(64) subfield using the fixed points of the sixth
  Frobenius power. Choose an irreducible quadratic over that subfield,
  record the basis order and change-of-basis matrices, and derive the
  multiplication, Frobenius, constant and trace-pairing maps. Keep the
  polynomial basis API and verify that the mapping preserves the pinned
  primitive element's evaluation points.
- Extend `reversible.py` and `tools/dqi_prototype.py` with an opt-in
  multiply-XOR backend and a norm-based inverse-XOR backend. Use schoolbook
  and native inversion controls. Start with an explicitly generated
  bilinear decomposition and derive its scratch schedule and measurement
  correction. Count both computation and erasure, including linear
  maps, Clifford work, private wires and native run time. The 45-gate
  multiply estimate depends on a proved 15-term GF(64) decomposition.
  The 70-gate norm inverse estimate needs a complete compute/copy/erase
  schedule before comparison to a clean inverse-XOR.
- Exhaust basis-vector products, all GF(64) pairs and every GF(4096)
  square, inverse and zero case. Use the 144 basis pairs to prove the
  GF(4096) bilinear product, then differential-test serialized native
  circuits with arbitrary XOR targets and seeded measurement outcomes.
  Mutate one basis column, one reduction term and one cleanup operation.
  Require a phase-correct clean round trip on the original register map.

## D2. Build one complete exact decoder

- Use `decoder.py` and the pinned synchronized EEA as independent
  controls. Build the end-to-end classical schedule and explicit inverse
  map before generating the full circuit. Add a separate Forney oracle
  because the current BM and EEA share Vandermonde recovery. Re-encode
  the recovered error word into all 70 syndromes. Extend the existing EEA and BM
  slices with the dynamic discrepancy, degree, offset and history rules.
  A conditional-routing BM branch can share a row update after
  rescaling, provided the algebra, branch metadata and inverse are
  derived under this project's syndrome convention. Price both exact
  candidates at their maximum live width before selecting one generator.
  Size the first design for full histories and coefficient ranges.
  Gu et al.'s 1,837-qubit and 440,000-Toffoli result uses an approximate
  layout and measures `TQ`. Restoring all history entries in that
  layout alone would add 646 qubits.
- Emit the selected full decoder through `tools/dqi_prototype.py` or a
  focused generator under `src/qcompile/dqi/`. Use the existing streamed
  runtime-mask Forney primitive as the first phase-tail control. A cheaper
  reciprocal tail may compute `Psi * sigma' = 1 mod sigma` for a
  square-free locator and evaluate it at each root. Derive the trace
  dual for the external mask bits and prove its equality to the verifier
  dot product after the basis map. Scan all 4,095 positions. The paper's
  shorter scan cancels fixed masks offline. For an arbitrary mask use
  legal classical controls and count the native gates for parity
  preparation, root detection, the controlled phase and cleanup. Gate
  any syndrome-bank reuse on a proof of the zeroed coefficient range
  and its exact inverse.
  [Gu et al., supplement I.1](https://arxiv.org/html/2610.22367v1)
- Exhaust reduced-field error sets through the supported radius and test
  full-field zero, one, and maximum-weight syndromes. Include zero
  discrepancy, degree changes, maximum history, first/last position,
  repeated-root or invalid diagnostic inputs, sparse/dense masks,
  reversed endian, missing phase correction and dirty scratch.
  Differentially check syndrome restoration and the final parity after
  full forward and reverse schedules. Keep malformed cases distinct
  from valid inputs in the acceptance statistics.

## D3. Measure and decide

- Compare the exact generator and reference on the same registered
  2,560 cases with `tools/dqi_development.py`. Report width, executed
  Toffoli-like mean, raw error counters, repetition multiplier and
  memory. The matched 2,560-shot result is a development control with a
  zero-error multiplier of about 4.94. The corresponding 102,400-shot
  multiplier is about 1.19. Compare costs at the same coverage. Plan
  three preselected matched development salts if profiling supports them.
- Require zero observed errors for the exact track and at least a 2×
  full-strength cost gain, about `1.222e13` or lower using `RQ²T`.
  Record 8× as a research checkpoint. Freeze one exact candidate,
  rebuild it independently, then use a preregistered full-strength
  schedule and separate fresh confirmation. Compare all salts and
  keep the original value/phase counters and confidence receipts.
- After the exact path qualifies, open a separate in-place
  continued-fraction or Schur tranche only when its liveness map
  accounts for each overwritten syndrome word and the inverse. At
  maximum degree, locator and evaluator already consume the available
  70 words. Investigate a combined representation such as
  `g = omega * (sigma')^-1 mod sigma` only with a proof of evaluator
  recovery, variable-degree padding and workspace. Treat
  900 qubits and 40× as stretch hypotheses. Short stacks, truncated
  coefficient ranges and omitted branches require a separately
  registered failure budget based on both the official confidence
  limit and measured complete cost. Evaluate the actual
  Clopper–Pearson bound and repetition multiplier against a
  preregistered failure cap and adversarial cases.

Limit the first tranche to two arithmetic backends plus controls, two
exact locator slices, one full generator, and one frozen promotion
candidate. Timebox contract, arithmetic and locator proofs to one
engineering week before deciding on the full generator. Treat a further
two to three weeks as a planning allowance pending the slice results.
Run the small fixtures locally. Use a profiled memory-heavy
runner for the official full shots. The previous matched DQI trial
sampled about 7.01 GiB peak process-tree PSS and 2.02 GiB peak swap PSS.
