## Baselines and source of truth

| Control | Inverse-square-root cost | Use |
| --- | ---: | --- |
| Official reference | 2,076,774.233715282 | Reconcile the model and scoring adapter against the pinned builder and accepted reference receipts. |
| Confirmed hybrid incumbent | 1,971,483.438323478 | Compare every candidate and every measured promotion outcome against this same circuit. |
| Current hybrid archive | Aggregate 1.0286345856615866 | Compare the complete successor ZIP against this measured archive. |

The incumbent KMB SHA-256 is
`9816fbfb5544949fb2c448410daf8144b825e45d0105cb118aac75c1a8c910e9`.
The parent ZIP SHA-256 is
`8fb545091a1cf66c2656bdce40bedbc26e478746301f9a777f56173f88b88503`.
Read member identities from the [parent manifest](../../../docs/evidence/invsqrt-chemistry-20261107/archive.json)
and costs from its [combined result](../../../docs/evidence/invsqrt-chemistry-20261107/combined-result.json).
The retained members are nine banked J9 ANGLE KMBs, the bound factorization
and tree NPZ, and the reference DQI KMB. Absolute paths in historical receipts
are locators. Resolve relocated inputs by hash and preserve the originals.
For inverse-square-root promotion use the incumbent receipt and original
width tuple in the [opportunity report](../../../docs/invsqrt-opportunity-07-11-2026-00-44-21.md)
and [protocol](../../../configs/invsqrt-opportunity-v1.json).

Use `contracts/contract.json`, the reviewed metric and its pinned
`vendor/official/verifiers/invsqrt/verify_submission_invsqrt.py` as authoritative.
Pin the source bundle or clean commit, verifier/backend inventory, runtime
import paths, native binary, Python 3.13 environment, frozen `uv.lock`,
coefficient generator and table bytes, all source inputs and prior receipts.
Check the installed verifier constants and replay official controls if the
runtime pin changes. A hash or cost discrepancy blocks comparison until
reconciled in a separate review.

## Source audit and implementation boundaries

Start with the [public notebook lead](https://www.kaggle.com/code/rudrabhaskar/highest-public-score-direct-polynomial-phasing).
Follow it to the versioned generator, coefficient derivation, auxiliary source,
binary outputs and any borrowed components. For each item record immutable
locator, version, SHA-256, author, license, permission for the intended use
and role in a reproducible build. Obtain competition inputs through the
official asset path and keep restricted inputs out of version control.
A notebook license applies according to its scope. Verify rights for every
borrowed generator and input independently. Treat the
[separate 62-qubit result](https://github.com/EigenOS-Quantum/eigenos-vqcc)
as an externally reported comparison with its own provenance and build.

Choose and record one route before prospective screening.

| Audit outcome | Route and reproducibility claim |
| --- | --- |
| Generator, coefficients and all dependencies can be reproduced with reviewed rights | Rebuild the public design unchanged. Compare canonical bytes, operations, width and measured costs against its pinned receipt. Record any explained serialization difference and demonstrate semantic equivalence before reporting a reproduction. |
| Generator, coefficients, dependencies or rights are missing | Write an independent generator using the published mathematical method as a reference. Record the gaps, derivation and any differences. Report this as an independent implementation and use its first valid build as the refinement control. |

For the independent route, use the [sponsor paper](https://arxiv.org/html/2610.23832v1#S3.SS1)
as the problem and normalization reference. Start with
`k = floor(floor(log2(x))/2)` and `u = x / 2^(2*k)`, so `1 <= u < 4`
and the phase target in turns is `2^(-k) / sqrt(u)` modulo one.
Fit `1/sqrt(u)` on a fixed, dyadic partition of `[1, 4)`. Record the
coefficient generator's precision, tie-breaking and quantization, and
hash the resulting integer table. Evaluate the selected polynomial in
reversible fixed-point arithmetic, apply the scaled phase with the signed
accumulator weights in half-turns, then uncompute selection and arithmetic
scratch. Use unambiguous half-open intervals and explicitly verify the
`x=1` integer-turn wrap. Keep this first implementation simple enough to
cross-check intermediate values. Only then compare segment selection,
arithmetic fusion and earlier cleanup against it.

Start with a small generator and a separately evaluable exact model in
`src/qcompile/invsqrt/`. Keep coefficient generation as an explicit,
deterministic build input. Use a focused `tools/invsqrt_direct.py` entry point
and a separate `configs/invsqrt-direct-v1.json` protocol if the existing
opportunity driver is tied to the Newton circuit. Reuse `qcompile.io`,
`qcompile.experiments`, existing backend checks and release helpers where
their contracts match. Share immutable coefficient/layout data between the
model and builder. Keep the model independent of the gate-emission path so
it can detect emitter errors. Keep the current Newton builder and its config
available as controls. Use the pinned gate constructors and canonical KMB
round trips. Record CLI and plugin catalog changes together if a project CLI
action becomes necessary.

For the first implementation, document the circuit as a sequence of stages.
Show how the normalized input and scale are derived from `x`, how intervals
partition every legal input, how each coefficient and accumulator is signed
and rounded, which products are truncated and where phase is applied. State
input and scratch initialization at every boundary, allowed modular overflow,
phase convention, and cleanup order. For each measurement-based cleanup show
how the conditional correction removes branch phase, which controls survive
until correction, and how the primitive composes on the stated input subspace.
Compare actual declared wire IDs and width in the serialized circuit, since
the scorer charges `circuit.num_qubits` even if some wires are idle.

## Exhaustive phase and cost screen

- Use the official `n_p=10`, `beta=1`, 22-bit little-endian `x` register,
  domain 1 through 3,133,452, and 64 trajectories per input at full strength.
  Require exact restoration of `x` and zero final scratch.
- Evaluate the circuit arithmetic in deterministic chunks covering the entire
  domain, including the last partial chunk. Accumulate rational half-turn
  contributions exactly with the emitted sign, scale and modular convention.
  Convert the resulting phase with the pinned `half_turns_to_units` rule.
  Derive the verifier target and floored tolerance with `reference_values`
  and cross-check wraparound, half-turn and rounding cases independently.
- Record `used = abs(signed_mod64(observed - target))` and
  `margin = allowed - used` in phase64 units without unsigned underflow.
  The minimum absolute margin and highest fraction of tolerance may come from
  different inputs. Retain both witnesses, boundary failures and total
  coverage. Use integer cross-products for the 90% screening decision.
  Pin the chunk plan and reject missing, overlapping or incomplete coverage.
- For the model cost, use executed mean Toffoli-like operations `A`, T-like
  operations `B` and fine rotations `R` from the verifier's counting convention.
  With minimum margin `m`, compute `eps = pi*m/(2^64*R)` radians for `R>0`.
  Then compute `Q * (A + (B + R*(0.56*log2(1/eps)+5.3))/4)`.
  Use `Q * (A + B/4)` when `R=0`. Use the pinned T-per-Toffoli and
  rotation functions when evaluating the formula. Reject a nonpositive
  margin under the project gate even for a rotation-free design.
- Validate phase classification and executed statistics from native KMB
  runs. Static operation counts are valid for screening only if the emitted
  structure and native checks establish constant counts for the scored
  categories. For input- or outcome-dependent counts, calculate justified
  full-domain means or use a preregistered conservative bound. Label
  sampled measurements as estimates and exclude an uncertain score from
  promotion until a defensible bound clears the gate. Full and confirmation
  decisions always use the pinned verifier's actual executed-count means.
- Native differential cases include all interval/scale boundaries and their
  neighbors, domain endpoints, exact model worst inputs and a pinned
  development sample. Include arithmetic extremes, carries, negative
  coefficients, rounding ties, workspace reuse and every applicable cleanup
  branch in focused fixtures. Require model/native phase equality,
  input restoration and zero scratch before comparing scores.

## Prospective comparison and execution budget

Initial project policy is at least **10%** lower complete cost than the
confirmed incumbent (cost **at most 1,774,335.0944911302** using unrounded
inputs), no modeled or native failures, positive minimum margin, and at most
**90%** worst tolerance use. These are engineering gates. Use the formula
`0.90 * incumbent_cost` as the authority for the cost limit. Apply the same
policy to measured full and confirmation costs and tolerance. Pin the
comparison precision before running. A faithful reproduction can be
documented even if it fails the promotion policy.

Proposed initial screen budget is eleven recorded attempts including two
controls, one unmodified direct implementation and up to eight refinements.
Allow up to three piecewise variants, two arithmetic variants, two cleanup
variants and one combination if the preceding measurements justify it.
Before the prospective run, register exact segment partitions, degrees,
coefficient precisions, arithmetic variants, cleanup schedules and an
explicit adaptive rule for choosing parents and the optional combination.
Scout work is recorded separately. A change learned from the screen goes
into a new registration, with prior results preserved as development data.
The proposed screening envelope is 16 engineering hours, 7,200 wall seconds
and 14,400 total process-tree CPU seconds. Set the final positive bounds in
registration after measuring control and lane capacity. Allow up to 3,600
seconds per full component execution and per complete archive verification,
with separate budgets and receipts for those runs. Stop on resource exhaustion
and record a no-go or incomplete decision.

Run the reference and incumbent controls serially before ranking candidates.
For each refinement family compare against its frozen parent and record
delta cost, margin and stage counts. Advance only a passing, beneficial
change. Tie-break eligible final candidates by lower complete modeled cost,
then larger minimum absolute margin, then stable candidate ID. Keep
rejected, skipped, interrupted and failed candidates in separate immutable
run directories. Bind the final decision to the registration and each
attempt receipt.

Default to one screening lane. Permit at most two independent lanes when
distinct CPUs, measured per-lane memory and explicit system headroom permit.
Fix numerical libraries to one thread per screening lane. Start full runs
on x86-64 Linux with a measured memory allowance for verifier processes plus
OS headroom. Use the parent hybrid run's measured resource receipts to plan
the archive run. Sample the process tree externally and report sampled PSS
and summed RSS separately. Enforce timeouts against the worker tree, retain
logs, and distinguish a polling timeout from an actual interruption. Run all
full verifier stages serially at the campaign level.

## Frozen component and hybrid successor

1. Freeze the winning KMB, generator recipe, resolved parameters, all
   inputs, source and backend identity, model, selection receipt and hashes.
   Require two clean canonical KMB builds and matching reloads. Run the
   pinned full verifier across 200,540,928 trajectories, then independently
   preregister confirmation against the same hash and run it at the same
   strength. Check hash, actual coverage, measured tolerance and cost in
   each receipt. Keep the exhaustive model's minimum margin and reconcile
   the raw verifier's reported worst fraction and rotation allocation.
   Reserve salts atomically using the benchmark-scoped ledger for promotion.
   If the benchmark-scoped ledger is pending, keep research receipts in
   the scoped run registry and require the reviewed import path before
   selection. Retain their original registration and outcome history.
   Keep development, historic baseline A,A,B, full, confirmation and
   final-archive seed roles distinct. Retain failed history and block
   reseeding the same bytes to obtain a passing result.
2. Build a separate successor candidate and release. Use a generated origin
   for its direct-phasing KMB and the existing retained-reference origin for
   DQI and the reference NPZ. Preserve the nine optimized chemistry loaders
   as an explicitly retained certified component. Introduce a narrow
   `retained_certified` classification for those members only when a
   hash-bound parent local certificate resolves through the existing
   release records. Bind the complete chemistry manifest including the
   retained NPZ, factorization/tree and runtime identity. Require the
   parent's passing chemistry record to be intact and eligible under the
   ledger. A historical validation receipt alone cannot establish certified
   lineage. Read its confirmation as parent evidence without copying it
   into the new confirmation slot or consuming a second use.
3. Extend the selection, builder and certificate checks to understand this
   single retention case after `certify-hybrid-release`. Continue to
   require confirmation for any generated benchmark, including all chemistry
   in the parent release. Do not give optimized retained artifacts a
   reference origin or change the meaning of old candidate IDs and records.
   Reject incomplete families, changed files, missing or untrusted
   certificates, consumed-for-tuning or mismatched confirmation, and
   changed contract/backend or invalidated dependencies. Keep formal
   successor certification pending if the parent certificate is unavailable.
   Research can still report a hash-bound local comparison as such.
4. Generate the new inverse-square-root KMB independently into two clean
   release directories, verify every copied retained member against the
   parent, and require byte-identical deterministic ZIPs. Extract afresh.
   Require the exact expected member set and only one changed member
   relative to the parent. Run the pinned full metric on the extraction
   and require actual coverage of **200,540,928 / 102,400 / 254,464**
   for inverse square root, DQI and chemistry, respectively. Verify
   complete metric success separately from the per-benchmark receipts.
5. Reconcile reported chemistry and DQI costs to the parent with a pinned
   numerical comparison tolerance (proposed relative tolerance `1e-12`).
   A difference beyond that tolerance blocks attribution and certification.
   Investigate raw counters and seed policy without rerolling. Require the
   measured inverse-square-root cost and worst tolerance use to clear the
   registered gates and the
   measured aggregate to strictly exceed **1.0286345856615866** using
   the same official reference costs. Record all component costs, delta
   versus the parent and reference, archive and per-member hashes, coverage,
   and links to the confirmed evidence. Keep remote acceptance separate.
