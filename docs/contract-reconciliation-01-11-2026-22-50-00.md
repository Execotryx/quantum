# Official contract reconciliation

Created: 01-11-2026-22-50-00 (Asia/Qyzylorda).

## Scope and current gate

The 1 November acquisition makes the actual competition verifiers available.
`contracts/contract.json` now records their executable conventions instead of
treating research-report constants as authoritative. Each reconciled field pins
the defining file and symbol; supplementary evidence pins cross-file definitions.
The source lock retains the official metric v10 hash and adds the acquired
competition pages, original archive, backend, bundled paper and starter metadata.

All 35 contract fields are now reconciled, including full local baseline acceptance
and measured profiles. Every critical discrepancy has a pinned resolution.
`qcompile contract validate` returns `ready`, zero blockers and exit code 0 with
these acquired assets. The initial interrupted run remains preserved separately;
acceptance is established by the completed retry, not by that interrupted run.

The completed evidence is `docs/evidence/official-baseline-20261101.json`.
It records actual verifier returns, full coverage, original artifact identities,
environment, per-component timings and the final metric completion report.
This closes step 1; candidate primitive/negative-control reviews, opportunity
decisions, optimization and release qualification remain separate work.

## Authoritative inputs

- Competition archive: all 34 members match the extracted files; byte hashes are
  in `vendor/acquisition-checks.json`. Original archive remains unchanged.
- Metric notebook: exact reviewed version 10, SHA-256
  `df418aff0d6eff16ec341da20150255abb49b252256d6abfb253ef8d2643ac73`.
- Rules, Evaluation, Timeline, data description and Domain Context: retrieved
  through Kaggle MCP on 1 November; complete snapshots remain under `vendor/`.
- Starter kit: host-linked `sohier/verifiable-circuit-compilation-starter-kit`,
  version 4. Only its exact `starter_kit/pyproject.toml` and metadata were acquired;
  this is not a claim that the complete 464 MB dataset is installed. It requires
  Python >=3.13 and pins Qualtran revision
  `c58703d00b01c346d3e77d3913cf2d6e9e556be3` for generation dependencies.
- Supplied `kickmix.so`: Linux x86-64, CPython 3.13. Actual `GF2Field(12)` reports
  modulus `0x1053` (4179) and primitive element 2. Python 3.14 import is rejected.

Executable verifier code governs numerical behavior. A PDF, starter-kit copy,
approximate prose statement or local mathematical helper does not override it.
The bundled PDF is pinned by bytes; no unverified arXiv version is assigned to it.

## Inverse square root

Source: `verifiers/invsqrt/verify_submission_invsqrt.py`, especially
`ProblemSpecInvSqrt.for_n_p`, `reference_values`, `half_turns_to_units`,
`validate_registers`, and `verify`.

- Inputs are every integer 1 through 3,133,452. Exactly one named register `x`
  contains 22 distinct little-endian qubits. It is restored and every other
  qubit starts/ends at zero. The phase target is `1/sqrt(x)` turns, modulo one.
- Default coverage is 64 trajectories per input, 200,540,928 total. Simulator
  outcomes derive from canonical KMB SHA-256 mixed with the split's salt.
- Target: `r=isqrt(floor(2^130*beta^2/x))`; round magnitude with `(r+1)>>1`,
  apply beta's sign, and reduce modulo 2^64. For beta=1 the floored tolerance
  is `r>>25`, capped at half a turn. Tracked rational simulator phase is in
  half-turns and is rounded by `(((numerator<<64)//denominator+1)>>1)` modulo
  2^64. Exact half ties round toward positive infinity. This is not a general
  nearest-even rule.
- Compare the absolute signed circular difference against the floored tolerance.
  Equality is accepted numerically, but any fine rotations need strictly positive
  remaining margin for synthesis error.
- `Z_POW` half-turn exponents divisible by 1/2 are Clifford; remaining multiples
  of 1/4 are T-like. Fine rotations use `0.56*log2(1/eps)+5.3` T gates each,
  where `eps=pi*minimum_margin_turns/mean_fine_rotations`. No fine rotations
  means no synthesis charge and `eps=None`. Cost is `Q*(mean_Toffoli+total_T/4)`;
  means reflect actually executed gates and no integer rounding is added.
  Q is `circuit.num_qubits`; the carried `system_qubits` specification value is
  not added by this implementation.

## DQI

Source: `verifiers/dqi/verify_submission_dqi.py`, especially `FieldTables`,
`optimal_dqi_weights`, `sample_shots`, `validate_registers`, and `verify`.

- RS(4095,4025), 70 syndromes, field degree 12, r=2016, maximum error weight 35.
  Register `S_i` holds little-endian `sum_j e_j*alpha^((i+1)*j)`. Registers
  `E_j` are little-endian classical 12-bit masks. Required public registers
  must have exactly the documented names/types/widths and must not overlap.
- Weight probabilities are squared components of the normalized principal
  eigenvector of the official tridiagonal DQI matrix. Error positions are
  uniform without replacement, values uniform nonzero field elements, and
  masks independently uniform field elements. Uniform weight sampling would
  be an incompatible replacement.
- Desired phase is `(-1)^sum_j popcount(e_j & M_j)`. Syndrome qubits must be
  restored and scratch qubits zero. The verifier does not assert restoration
  of the classical E registers; the expected phase remains bound to the original
  sampled masks. `Z_POW` is forbidden.
- There are 102400 shots in batches of 256. SeedSequence derives separate
  sampling/simulator seeds from the canonical circuit digest and salt.
- A value failure is any syndrome or scratch error. A phase failure is counted
  only when there is no value failure. Thus `k=value_errors+phase_errors`
  counts the union once. The one-sided Clopper-Pearson upper bound at delta
  2^-128 must be strictly below 1/16. Cost is `R(eps_plus)*Q^2*mean_Toffoli`,
  with `R=ln(2)/-ln(1/2+2*sqrt(eps_plus))`.
  Q counts qubits; the separately reported classical bits are not included in Q^2.
- The backend configuration maps actual returned `verified_shots` and the two
  disjoint failure counters. The adapter now accepts their sum, rejects duplicate
  paths and impossible failure totals, and retains the older single-path form.

## Chemistry

Sources: `verifiers/dfthcsos/verify.py`, `scoreinfra/reference.py`,
`scoreinfra/circuits.py`, `scoreinfra/dfthc_math.py`, and `scoreinfra/costs_prepare.py`.

- FeMoCo76o113e has 76 spatial orbitals and 113 electrons; upper energy is
  -22140.27335 Hartree. The packaged FCIDUMP and fixed shifts have enforced hashes.
  Submitted H1_I and Hsym_lower are replaced by the packaged symmetry shifts.
  Packed symmetry coordinates are rounded to float32; FCIDUMP two-body
  coefficients also undergo the official float32 rounding before expansion.
- The metric requires floating U(R,B,76), W(R,B,C), H2_I(R,C), scalar H1_I,
  Hsym_lower(2926), and integer tree_edges(75,2). Arrays use plain numeric,
  native/little-endian NPY v1.0 storage and total declared bytes <=2^26. Positive
  symbolic dimensions must agree. Factorization values must be finite.
- Directions come from the words recovered from actual circuit execution;
  supplied U values do not replace those recovered directions. Rows consist
  of 76 one-body vectors followed by R*B two-body vectors.
- Angle words are unsigned brot-bit integers, brot=1..63. Radians equal
  `pi*word/2^(brot-1)`. Apply ordered Givens rotations to e_0. The tree is
  rooted at zero, with each parent already visited and child newly visited.
  The verifier decodes words; it does not require a particular ideal-angle
  rounding method in the generator.
- `selection` width is exactly ceil(log2(76+R*B)); `word_0..word_(J-1)` are
  disjoint equal-width qubit registers shared by the entire family. There are
  ceil(75/J) circuits. They sequentially XOR batch deltas; all padding beyond
  75 angles is zero. The reverse traversal clears the words. After each
  circuit selection is unchanged, phase unflipped and workspace zero.
- Only addresses 0..76+R*B-1 are simulated. Extra binary addresses have no
  verifier requirement. The word register begins at zero, then receives the
  preceding batch; passing is not a proof for every arbitrary initial z.
- One-body matching diagonalizes the decoded two-body-dependent h1_prime and
  maximizes absolute overlaps with a one-to-one Hungarian assignment. Exact
  matched eigenvalues reconstruct the submitted one-body part. Sign flips and
  permutations are allowed subject to the resulting accuracy checks.
- Both shifted Frobenius residuals must be <=0.020 Hartree. Raw Lambda must
  exceed 49.0 and E_gap must exceed 3.914898; equality at either floor fails.
  Executable gap domain is `0<E_gap<=2*Lambda`, followed by a finite/high-precision
  radicand check. Some module prose says `<` at the upper endpoint; the contract
  records the executable `<=` without silently changing the upstream code. At
  equality, however, lambda_eff and cost are zero, and the metric's positive-cost
  check rejects the result. The complete official acceptance path thus excludes
  that upper endpoint even though the verifier's intermediate domain allows it.
- `lambda_eff=sqrt(E_gap*(2*Lambda-E_gap))`. T_total includes actual mean
  forward+reverse ANGLES Toffolis, both modeled state preparations (including
  cleanup), and `2*(76-1)*(2*brot-1)` Givens Toffolis. Q_total includes persistent
  state-prep qubits and J*brot words plus the maximum temporary workspace across
  sequential stages. State-prep uses SpinFreeData_V1 with fixed chi=10.
  Each ANGLE circuit is capped at 128 qubits; the full Q_total is not capped there.
  Use the acquired `SpinFreeData_V1` with `optimize_qubits=True`. Its documented
  corrections decrement inner k2 one step at a time, permit exact B=2^k2 blocks,
  and use the +1 inner word bit in both Toffoli and qubit accounting. The outer
  state-prep size is N+R*C; the inner word width is ceil(log2(B))+chi+1.
- Full coverage is 64 trajectories per valid address, each with all forward
  and reverse circuits. For the supplied R=65,B=60 reference, that is 3976
  addresses and 254464 verified shots. A new shape requires an updated count
  and invalidates evidence bound to the old contract.

## Serialization, seeds and submission limits

Individual inverse-square-root and DQI seeds hash canonical KMB serialization.
Chemistry hashes canonical circuits in numeric order followed by raw NPY entries
U, W, H2_I, H1_I, Hsym_lower and tree_edges. Array dtype, shape, layout and bytes
matter; ZIP timestamps/compression and KMX comments do not. The metric's in-memory
NPZ loading and the verifier's path-based loading must be checked for equivalent
NPY serialization before relying on a direct-CLI comparison as metric evidence.
For the supplied baseline, all six NPY entries were checked and match exactly;
`docs/evidence/chemistry-npy-roundtrip-20261101.json` preserves that result.

The submission is a ZIP containing invsqrt, dqi and the dfthcsos family/NPZ,
one encoding per circuit, with contiguous ANGLE indices. The official metric's
path discovery is more permissive than this project's canonical no-extra-path
packaging policy. Qubit/bit IDs must be below 699050. Register limits are 1 for
invsqrt, 4165 for DQI, and 128 per ANGLE circuit. Arbitrary `Z_POW` is available
only for inverse square root. All instructions must be in the metric whitelist.

Official rules permit five submissions/day, two final selections and five people
per team. Entry/team-merger deadline is 13 January 2027 and final deadline is
20 January 2027, 23:59 UTC. These are point-in-time observations to revalidate
before submission. Evaluation says scoring takes roughly 45 minutes; it does
not define a hard runtime timeout in the acquired pages or metric. The local
7200-second timeout is an operator limit, not an official rule.

Aggregate scoring is the geometric mean of the three reference-cost/candidate-cost
ratios. Private-split salts and baseline costs are not locally known. Official
data describes the reference score as 1.0; measured local acceptance is now
established. Calling the exact official score function with these measured costs
as its own baseline returns 1.0, a self-normalization control. Local costs do not
establish an observed private-split result.

## Verification and preserved interruption

`docs/evidence/contract-differential-20261101.json` records successful comparisons:
all 3133452 inverse-square-root targets/tolerances, all 4096 field squares and
4095 nonzero inverses, eight extreme-tail confidence fixtures, three rotation
prices, tracked-phase half ties and three independent Givens vectors.

The complete test suite passes 272 tests in Ubuntu/Python 3.13. Pyright passes
for all changed Python files; Ruff lint/format and strict OpenSpec validation
pass. Provenance mutation tests reject both primary and supplementary changes.

The first full baseline run (`runs/baseline-g0-20261101`) ended with process exit 1
without a metric completion report. WSL kernel diagnostics show a shutdown/restart;
the root trigger is not established. No OOM or verifier rejection is inferred.
`interruption.json` retains that observation. The two-core retry at
`runs/baseline-g0-20261101-retry` completed with worker exit 0 and an overall full
verification report. The worker preserves each actual benchmark return and elapsed
wall time separately, without equating an individual receipt to overall completion.

| Original reference | Verified shots | Complete official cost | Verifier wall seconds |
|---|---:|---:|---:|
| Inverse square root | 200540928 | 2076774.233715282 | 635.882 |
| DQI | 102400 | 24439461432712.35 | 290.773 |
| Chemistry | 254464 | 3355599588.3155375 | 76.041 |

The metric run took 1076.590 seconds including loading/copying/hashing/orchestration.
The worker's recorded RUSAGE_SELF high-water RSS is 7383588 KiB (about 7.04 GiB);
this is not summed concurrent parent/child physical memory. All baseline artifact
hashes were independently compared again to the original archive inventory.
The execution request preserves the pre-finalization contract hash: adding the
measured baseline fields changes that hash. The receipt explicitly documents this
transition and is not a candidate/release verification under the final hash.

## Simplicity and performance review

Simplicity cycle 1: keep the existing validator and gate semantics; do not add a
parallel validation mode or mark baseline fields optional. Reuse source pins and
the existing adapter. Preserve three flat numeric coverage values expected by
release certification and put detailed conventions beside them.

Simplicity cycle 2: maintain the original single-path confirmation mapping and
add only a list for disjoint counter sums. Use actual official counter names;
avoid guessed expected-counter fields. No further simplification was identified.

Performance cycle 1: cache file digests within one validation call so cross-file
provenance references do not repeatedly hash identical sources. Do not cache
across calls, which would miss changed files. Stream large archive hashing and
keep official assets ignored. Limit retry concurrency and numerical BLAS threads.

Performance cycle 2: per-benchmark receipts reuse verifier return dictionaries;
they neither rerun simulations nor duplicate circuit data. No further necessary
performance change was identified. Full execution measurements were added after
the monitored retry completed.

## Follow-up evidence — 01-11-2026-23-25-00

The actual full-strength metric execution has now returned PASS for DQI (102400
shots, zero value/phase failures, approximately 291 seconds) and chemistry
(254464 shots, approximately 76 seconds). Chemistry residuals are
0.0031851950317996216 and 0.018639570630974368 Hartree; its complete official cost
is 3355599588.3155375. The chemistry baseline-validity discrepancy is resolved by
`docs/evidence/baseline-chemistry-20261101.json`, including original component
artifact hashes and the exact request hash. Overall baseline acceptance remains
unresolved until inverse square root and the final metric report complete.

Simplicity/correctness review cycle 3: the fixed minimum source-role list left
additional declared roles unchecked. Validation now checks the union of mandatory
and all declared roles using the same per-call digest cache. A regression mutates
an additional verifier inventory and checks rejection. CLI blocked-state tests now
use an intentionally unresolved fixture instead of assuming the live project must
remain blocked forever. Pyright passes for all four changed Python files.
The full suite will be rerun after the monitored baseline finishes.

## Completion review — 01-11-2026-23-44-33

The retry completed all three original references under the actual metric at
shot divisor 1. The final suite passes 272 tests in 38.43 seconds; Pyright passes
on all four changed Python files using the explicit Linux environment, and Ruff
lint/format and strict OpenSpec validation pass. The earlier implicit Pyright
environment could not resolve installed dependencies; explicitly selecting
`vendor/linux-env/bin/python` resolves that configuration issue.

Review cycle 4: critical discrepancy resolutions also require unchanged pinned
evidence and explicit resolution text. A mutation regression verifies rejection.
Large numerical environment metadata is stored once in the baseline report and
referenced by the profiles rather than duplicated. No remaining simplicity or
performance critique requires another implementation change.

The final requirement-by-requirement audit is
`docs/evidence/step1-completion-audit-20261101.json`: all eight user objectives
verified, 35 reconciled fields, eight resolved critical discrepancies and zero
contract blockers. It records the checked source-file hashes, exact final contract
identity, test/type/lint/spec results and full baseline coverage. The CI gate name
now explains that missing ignored official assets keep a clean checkout blocked;
the acquired local checkout validates ready. No subsequent optimization/release
work is counted as part of this completion.
