## Contract and incumbent

Use the pinned `vendor/official/verifiers/dqi/verify_submission_dqi.py`
symbols `ProblemSpecDQI`, `validate_registers`, `sample_shots`,
`clopper_pearson_upper_bound` and `verify`. The benchmark is
RS(4095,4025) over GF(2^12), with up to 35 errors and 70 12-qubit syndrome
words `S0`–`S69`. The 840 input qubits are part of the declared-width cost.
`E0`–`E4094` are fresh classical mask words, and every trajectory needs
the corresponding sign, restored syndrome and clean scratch. No
`Z_POW` is allowed. Confirm the field polynomial, root order, endian
convention, zero case, parity and sample distribution directly.

The certified reference DQI SHA-256 is
`959471d05a26373b4f14ca0cae2d8639ea25f18170d9f6532139aa51ccc04995`.
The paired control used 1,893 qubits, mean 5,725,109.06765625
Toffoli-like operations, and zero value or phase errors in 102,400
trajectories. Its cost is 24,439,466,510,149.91 on that seed.
[Control receipt](../../../docs/evidence/invsqrt-direct-hybrid-20261107/benchmark-dqi.json)

Gu et al. show reusable reversible BM, history and in-place evaluator
ideas. Their public contract uses polynomial 4331 (0x10EB), a fixed
classical mask and a quantized weight distribution. Re-derive field
operations and threshold policies for the pinned verifier polynomial
4179 (0x1053) and its actual distribution. The fixed-mask interpolation
and precomputed scan constants cannot be carried over as measured cost.
Their approximately 440,000 Toffoli and 1,837-qubit figures are external
method results. Likewise public near-900-qubit results are research
comparators and do not establish a licensed reproducible solution here.
[Gu supplement](https://arxiv.org/html/2610.22367v1) ·
[Companion input contract](https://raw.githubusercontent.com/andigu/uncompute/main/tasks/dqi-reed-solomon/contract.json) ·
[Sponsor paper](https://arxiv.org/html/2610.23832v1)

## Stage A — exact oracles and reversible slices

1. Extend the fixture drivers around `qcompile.dqi.field.GF4096` and
   `qcompile.dqi.decoder` without replacing the independent BM, EEA
   and mask-parity oracles. Pin backend field products, roots, offsets,
   syndrome-to-error sign and mask bits. Exhaustively exercise arithmetic
   on reduced fields and a registered set on GF(2^12), including zero,
   one, high basis bits, aliases, zero inversion policy, maximum-degree
   locator and representative multiple-error patterns.
2. Build a reversible multiply-XOR primitive on arbitrary targets and
   a finite-field inversion primitive with an explicit zero convention.
   Establish a schoolbook baseline, then compare bilinear/Karatsuba
   schedules and Itoh–Tsujii inversion with linear squaring. Report
   emitted Toffoli-like count, declared/live wires, cleanup and
   uncompute cost. Bilinear rank alone excludes scratch and fanout.
   Start with one implementation module and native fixtures. Split
   multiplier, inversion and round modules only as separate verified
   primitives emerge under `src/qcompile/dqi/reversible/`.
3. Implement an exact runtime-mask phase tail before a full decoder.
   Start with a reversible, streamed Chien/Forney path that computes one
   recovered symbol at a time, applies its runtime classical-mask
   parity using the pinned conditional phase API, and clears it. Reuse
   the reference's `gf2_phase_by_product` interface with its actual
   classical mask and root-controlled compute/erase where source
   reconciliation supports it. Start with all 4,095 positions. Verify
   recovery independently of the existing BM/EEA oracles' shared
   Vandermonde step and re-encode the syndrome. Check phase using
   zero, one-hot, all-one and random masks, including distinct masks
   for the same syndrome and masks on different positions. Test
   arbitrary-target action, internal alias boundaries and composition.
4. Consider the reciprocal and trace-dual optimization only after an
   exact phase tail exists. Keep classical-mask dependence explicit.
   Prove the field trace identity, coefficient transformation, root
   flags and correction for each classical input. Price the actual
   conditional gates and reset/uncomputation, even if some are free in
   the Toffoli objective. A constant mask, dropped mask position or
   cancelled cleanup correction must fail the negative fixtures.

## Stage B — decoder and layout decision

Prototype the exact locator/evaluator with two bounded paths.

| Path | Test first | Main risk |
| --- | --- | --- |
| Reference-compatible EEA | Attribute peak wires in the pinned generator and prototype one synchronized update/undo window with earlier reuse or a projective state. Keep the correct phase tail. | A lower-width schedule must preserve the full reversible state across all update branches. |
| Exact BM | Implement one update and undo with shared projective arithmetic, then a reduced-field fixed-iteration locator. Include all coefficient ranges and explicit history before considering cutoffs. | Division, branch reconstruction and exact history can erase the resource gain. |

Build a liveness table by stage and branch showing the complete
information needed to invert each transition, the permitted aliasing and
where each physical ID is released. Keep separate counts for declared
width, maximum live width and per-stage Toffoli-like operations. Record
how syndrome words become usable as clean or borrowed scratch, and how
their original state is recovered. For example, a coefficient count
that fits locator plus evaluator inside 70 words says nothing about
whether original syndromes, cofactors, flags and history are still
needed simultaneously. Reject an in-place rewrite when a state
collision, zero-denominator branch or unproved cleanup remains.

At weight 35, normalized locator coefficients with the constant term
implicit and evaluator coefficients fill all 70 words. A reciprocal
polynomial cannot also live in those words. As a separate hypothesis,
evaluate storing the locator plus `g = omega * inverse(sigma') mod sigma`.
On the distinct-root domain, the inverse conversion is
`omega = g * sigma' mod sigma`, followed by syndrome recovery from
`omega / sigma mod z**70`. Derive the magnitude convention from the
pinned S1-based oracle before applying this at a root. Information
sufficiency leaves the reversible modular division, zero syndrome,
variable-degree padding and physical workspace construction to prove.

Measure one decisive update slice from each path before emitting a
full 4,095-position scan. Select the lane by projected complete cost
including reverse, phase tail, operation-count variation and width.
Treat a correct but wide decoder as a stepping stone only if a measured
layout change supports the next gate. A clean, exact architecture may
beat a smaller approximate one once the failure penalty is included.

## Stage C — campaign and promotion

- Proposed first tranche is two locator paths, two multiplier designs
  and at most one full decoder emitted from that comparison. Timebox
  the reversible proof and prototype review to one engineering week.
  Register actual CPU, wall, memory and disk limits after measuring
  the native control and one slice. Review before authorizing a
  second architecture tranche.
- For a first exact full decoder, use a **2× improvement** in complete
  measured DQI cost as the initial research go/no-go threshold, with
  zero observed value and phase errors. Use a near-floor width of
  900–1,000 as a stretch gate for the second tranche. The report's
  40–65× scenario is a stretch outcome contingent on width, actual
  Toffolis, mask support and failure rate. Never promote by width alone.
  At equal repetition penalty, a 40× reference ratio permits about
  633,199 mean Toffolis at 900 qubits or 512,891 at 1,000 qubits.
- Register one exact candidate and the reference on identical
  development syndromes and masks at 2,560 or 4,096 trajectories, with
  the pinned batch size. Also test focused valid/adversarial fixtures.
  Record actual split error counts, per-stage arithmetic, registers,
  gate counts, peak memory and serialized KMB size. Do not compare
  reduced-strength scores to full scores with a different confidence
  penalty. Use the [shared campaign rules](../prepare-next-hybrid-verification/design.md).
- Only after a correct exact path works may an explicitly registered
  separate research lane consider bounded history or coefficient
  windows. Specify behavior on exhausted bounds and prove cleanup
  still holds on those paths. Validate on the actual verifier
  distribution with preselected salts. Register a maximum acceptable
  observed `k` and complete-cost target before execution. Do not
  turn a projected event frequency into an observed circuit error.
  At 102,400 shots the official repetition multiplier rises from
  about 1.19126 at zero errors to 1.24000 at 14 errors, roughly 4.09%.
- Freeze the eligible KMB with clean source, raw results and full
  layout provenance. Run 102,400 full-strength trajectories with the
  pinned verifier and require `epsilon_plus < 1/16`, the registered
  error condition and improvement. Confirm once on a fresh salt with
  the same artifact. Attach the actual disjoint counts and preserve
  the certified hybrid's other members until separately qualified.
