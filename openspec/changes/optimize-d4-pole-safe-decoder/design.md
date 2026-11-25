## Frozen controls

| Role | Circuit SHA-256 | Evidence |
| --- | --- | --- |
| Banked D4 | `53d8b2edf251e2a0c54c401a97d1396c7ed309e1cbfaab8d54a2c99a11ed6552` | 897 qubits, 444,667 static gates, 414.840B pooled cost in the latest comparison |
| Homogeneous groups 1–7 | `09467ecc12eb50a6a79f0706690a7018a29ecb6679d7e6c15c5b1754fde8db6a` | 904 qubits, 444,989 static gates, three of four historical failures fixed |
| Full-grid repair | `a44bdf032e965707cc1d07228258eb07786f9d1b07e094a5d90d1f2fb4b4bff5` | 4,081 qubits, 3,243,349 static gates, all historical failures fixed |

Bind the [matched fixtures](../../../docs/evidence/dqi-phase-replay-20261115/),
the [homogeneous profile](../../../docs/evidence/d4-extraction-repair-20261115/homogeneous-1-7-profile.json),
and the [full-grid registration and receipts](../../../docs/evidence/d4-extraction-repair-20261115/).
Rebuild or recover the corresponding exact circuit before using it as a
control. Retain the original receipts at their existing paths.

## Track the two full-grid value failures

Adapt the capture machinery in `tools/dqi_phase_replay.py` to accept an
explicit circuit, registration, role, receipt hashes and draw indices.
Keep the existing banked replay's identity requirements. Replay only
candidate draws 6 and 7, where the official verifier observed one value
error each. Require equality of the complete verifier result and capture
each failing batch's original RNG and simulator seeds. Hash the offsets,
input syndrome, masks and passing controls. Retain phase and mask
observations for value-failing shots separately from the official counts.

Replay those exact batches on all three controls. Map the final dirty
qubit indices to the moment rejection bit, repeated-root counter and
other scratch. Capture stage outputs using emitted boundaries or an
instrumented rebuild proven byte-identical. Compare the rational heads,
tail coefficients, degrees, congruence, roots and symbols to the
independent D4 geometry and BM/Forney references. Only attribute an error
to a mixed chart, repeated root, guard or inverse after reproducing the
causal mismatch. If an observation cannot be reproduced, retain its claim
as unresolved and carry the exact fixture through the candidate gate.

The [sealed residual replays](../../../docs/evidence/d4-compact-repair-20261115/cloud-replay/captures/)
reproduced both full verifier receipts. Shots s6/102316 and s7/52983
preserved the syndrome and left only q840, the rational rejection flag,
dirty. The independent oracle encountered incoming first-head poles at
heads 12 and 4, respectively. The 904-qubit homogeneous control passed
both complete batches with clean scratch and masks. Preserve its
incoming chart behavior and test those first-head poles separately from
the second-head pole being repaired. The [matched comparison](../../../docs/evidence/d4-compact-repair-20261115/matched-residual.json)
and a separate [native boundary probe](../../../docs/evidence/d4-compact-repair-20261115/native-probe.json)
show that all head words before those two incoming poles agree with
the oracle. The emitted heads at the pole continued with a zero first
head and no second-head chart flag. The synthesized pairs failed the
moment congruence despite satisfying the degree bounds, and both
neighboring controls passed. Retain the distinction between this
boundary probe and the exact full-circuit verifier replay.

## Resource constraints and measurement

The full-grid build in `tools/dqi_repaired_candidate.py` retains a
70-word moment copy, two 54-word polynomial banks and a 70-word
validation accumulator across the certificate check. These allocations
alone total 3,816 qubits including the 840-qubit syndrome. The emitter
also scans 4,095 points with per-root derivative inversion. Shrinking
the high-degree padding alone cannot recover D4's resource profile.
Report measured costs for extraction, synthesis, conversion, scan and
their inverse and phase-repayment stages. Include peak live qubits,
declared qubits, serialized size, static count and executed mean.

Source-derived counts for the general emitter attribute about 916,776
Toffoli-like gates to controlled coefficient products and 205,884 to
certificate products and their erasure, before linear routing and
predicates. The direct scan emits at least 626,535 arithmetic gates
for inverse, inverse erasure and symbol product. Even if the certificate
were removed, the two 54-word banks and syndrome alone would require
2,136 qubits. Pricing that width with the scan's static arithmetic
count alone gives over eight times banked cost at the same repetition
factor. This structural estimate is separate from the executed mean.

For a candidate with declared width `q`, define the design budget
`T_max(q,R) = C_b / (q² R)`, where `C_b = 414840001725.7007` and
`R` is the pinned pooled repetition factor. At the one-priced-failure
factor `1.1967314991687559`, a 904-qubit candidate must keep the largest
per-draw mean below 424,177 and a 920-qubit candidate below 409,552.
The banked maximum mean in this comparison was 430,823.14. These
thresholds use the lowest possible factor for eight draws under the
pinned pooled estimator. More priced failures tighten the budget. Use
a branch-aware estimate early, then native operation counts on pinned
development inputs at full width. If a defensible lower bound already
exceeds the banked cost at that factor, stop that lane before a full
build. Compare the complete pooled metric from fresh official draws for
the final decision.

## Primary lane: in-place doubled-node synthesis

Start from the measured homogeneous groups 1–7 control. It leaves only
s2 shot 45440 failing. Its largest matched-batch executed mean was
430,148.56, so at 904 qubits and the observed repetition factor it
needs about 5,972 fewer gates per shot before paying for the local-pole
change. Benchmark savings against the whole decoder, including reverse
paths and any new live chart flags. The partial repair serves as a
control throughout.

1. **Define the interface.** Use `paired_external_jet` and the scalar
   pole model as the independent algebra for charts, and take the
   layouts and lifetimes from `final_decoder/decode.py::synthesize`
   and `final_decoder/synthesis.py`. Start with one doubled node and
   a valid pre- and post-state. Keep the branch coherent until it can
   be recomputed or its measurement phase can be repaid. A genuine
   local pole has a known-zero second head. Prove its word reuse and
   restoration before reclaiming that storage.
2. **Prove the two synthesis folds.** In characteristic two, let
   `q=X²+X+κ`, and let `(U,V)` denote the continuation numerator and
   denominator. For a regular pair the inverse extraction produces
   `N=(h0*h1+q)*U+h0*q*V`, `D=h1*U+q*V`. For a genuine pole it
   produces `N=h0*U+q²*V`, `D=U`. For the pole inverse, first prove
   `D mod q` is nonzero in the exact gauge used by the emitter.
   Recover `h0=(N/D) mod q`, then `V=(N+h0*D)/q²` and `U=D`.
   Show exact divisibility, a branch-specific degree bound at every
   fold, and a reversible rank or storage argument for the 70-word
   bank and extra scratch. Handle legitimate termination separately.
   The isolated pole absorber uses the layout
   `[h0 words, zero h1 words, V words]` for `N`. It computes
   `h0*U = r0 + q*r1 + q²*C` by fixed column maps, adds `r1,C` to
   the known-zero head and `V`, then multiplies the first head in
   place by `U mod q` to obtain `r0`. The final triangular basis
   expansion and its inverse use no additional polynomial bank.
   Its per-chart identities and native tests are in the
   [implementation log](../../../docs/d4-compact-pole-fold-15-11-2026-21-57-41.md).
   A shared finite layout uses two regular absorptions. On the collapsed
   chart supply `U_s = U + qV`, replace the zero second head by 1, and
   apply `N ^= qD` after the folds. The intermediate denominator is
   `D=U_s+qV=U` and the corrected numerator is `h0*D+q²V`.
   Both quotient pivots are therefore nonzero whenever `U mod q != 0`.
   With `b+2` slots in `U_s` and `b` slots in `V`, the outputs share
   lengths `b+4` and `b+2`. The regular chart needs a zero top
   continuation numerator slot. The collapsed chart has zero second-head
   slope, so the product coefficient beyond the shared denominator
   capacity vanishes on either chart. The inverse undoes the shear,
   reverses the absorptions, then restores the zero second head.
   Transporting this gauge through extraction adds `qD` to the
   numerator and `D²` to the derivative numerator at each distinct
   evaluation node. The local proof leaves the multi-fold degree
   invariant and the incoming first-head route to integration.
   The [converter handoff and rank audit](../../../docs/d4-compact-converter-handoff-15-11-2026-22-47-59.md)
   derive the needed degree envelope and exhibit two weight-35
   second-head poles whose tails have degree (3,2). An implementation
   limited to degree (2,1) would exclude those inputs. The measured
   raw synthesis ladder for the witnessed layout uses 995 qubits.
   The [linked stage probe](../../../docs/d4-compact-linked-probe-15-11-2026-23-24-55.md)
   measures the improved ladder and the extraction on the same retained
   inputs. Dropping degree-constrained words alone cannot make the
   measured schedule fit the budget. Future promotion still requires
   a coherent tail/padding path and measured reductions in arithmetic.
   The [reduced-tail proof](../../../docs/d4-reduced-tail-basis-15-11-2026-23-46-24.md)
   bounds the admissible full-weight state at three coordinates for
   every exact chart sequence. The native 3-by-3 solve already supports
   the multiple-pole witnesses when supplied the reduced equations.
   Normalize the recovered coordinate weights using the denominator's
   leading coefficient before expanding the polynomials. Explicit
   online construction of both basis columns was accurate but reached
   143 coefficient words. Coherent generation needs a representation
   that avoids that width. The leading-only replay agrees with explicit
   reduction using at most 28 coefficient queries at a transfer level
   on the tested witnesses. The query count does not establish peak live
   words for a reversible implementation.
3. **Prove the tail and conversion boundary.** Derive the equations for
   the mixed-chart tail from degree and jet constraints. Verify the
   weight-34 and weight-35 branches and rank-deficient cases against
   the original moments. Explicitly handle any exception with a
   reversible, verifier-visible outcome. Compare polynomial and residue
   results with BM/Forney. A candidate may omit the full moment guard only
   once the narrower checks and identities establish the supported cases
   and preserve observable failure behavior outside them.
4. **Reuse the existing phase path.** Preserve the projected-mask
   contribution on the original syndrome and the restore step around
   `high_stream.convert_safe` and the scan. Prove the converter receives
   its expected normalized banks, constant omitted outer factor, and
   admissible degree profile. The scan expects 35+35 words and a monic
   locator whose leading word is implicit. Use the exact `Pscan`
   and `SELECTED` skip set with matching symbol and bit basis.
   A change to the omitted outer factor requires a matching derivation
   of the scan correction and independent full-grid symbol checks.
   The tested outer boundary retains the original factor. With the
   first fold omitted, its evaluator is `(N+h0*D)/q0` and the
   locator is `D`. This gives the banked phase residue when using
   `Pscan=P/q0`. The native handoff test uses explicit copies of the
   original syndrome and the supplied polynomial state. It proves
   this interface and leaves the production storage and in-place
   handoff to integration.
5. **Stop on the smallest failing boundary.** Exercise one native
   doubled-node fold and its inverse before implementing all groups.
   Include a true local pole, finite and terminating branches, alternate
   masks, and forced legacy clipping as a negative control. Insert
   varied Z/CZ fingerprints between the forward and inverse to expose
   a wrong layout or branch even when the baseline phase coincides. An
   unproved head recovery, degree overflow, rank deficiency on a required
   fixture, unsafe converter degree gap or unclosed phase blocks the
   compact build. Retain the first counterexample and direct it to the
   corresponding scalar tail, rank or converter diagnostic.

## Isolated optimization and open-source lanes

- Prototype scalar-only gauge replay at a single external boundary.
  The second replay in `paired_external_node_chain` recovers a
  denominator for gauge phase, inverse-normalization phase and pole
  cleanup. Carry only `(N,D)` on that replay after proving the
  derivative `L` is unobserved and returns to its entry value.
  The admitted D4 `stream/replay_erase.py` supplies the existing
  scalar replay pattern. Compare the exact phase under both measurement
  outcomes and retain the ablation only with measured net savings.
- Use the general emitter as a diagnostic lane if the compact fold
  cannot yet close. In `paired_polynomial_synthesis`, compute the two
  masked head words once per fold and reuse the existing 42-term product.
  Verify the clean measured AND erasure phase on the standalone fold.
  Price the extra 24 temporary qubits and the regular and pole branches.
  Counting 24 ANDs per fold and ordinary 42-term products projects a
  saving of 455,940 static gates across 17 pairs and both directions.
  The estimate needs basis, nonaliasing and measurement-phase checks.
  Recomputing the quotient after restoring the original syndrome could
  also remove the 840-qubit copy if its coordinate map is invertible,
  at the cost of another extraction and inverse. Keep these changes
  as diagnostic options because the explicit banks and direct scan
  still dominate their resource budget.
- Screen admitted D4 variants first, then any compatible admitted open
  implementation such as Q880 as a source of individual kernels. Freeze
  the exact upstream revision, source and license before reuse. Record
  author attribution, basis and layout mappings, initialized operands,
  gauge and measurement obligations, live width, and exact stage savings.
  The existing [Q880 comparison](../../../docs/dqi-public-pricing-15-11-2026-15-01-00.md)
  measured a pooled cost of 842.82B. Use its exact rebuild as an
  independent matched-input control if testing a Q880 kernel. Its
  gap-polynomial converter uses a different fraction representation,
  so prove the interface before any transplant.
  The existing rank-42 transplant tied D4 and the rank-45 lift added
  gates. Reopen multiplier work only for a kernel with a demonstrated
  end-to-end advantage under the complete cost model.

## Reversible leading-coefficient replay screen

The fixture-selected coefficient query of the reduced tail basis passed
native value, phase and cleanup checks. Its generic chart schedule kept
up to 260 checkpoint words and used 4,329 declared qubits and 1,416,480
executed Toffoli-like gates for query and erase on the three full-weight
pole witnesses. The gate ceiling at that width is about 18,497 under
the banked reference. Stop this schedule at the resource gate.

A successor that uses chart-dependent degree origins must prove the
window update and its inverse for regular, terminating and collapsed
charts. Track every coefficient dropped at a chart transition and prove
that it is zero, is already recoverable from retained values, or is
uncomputed before reuse. Include the live chart controls and solver
registers in the measured width. Require coherent pivot coverage and
normalized tail assembly before using a fixture-selected coefficient
probe as a candidate handoff.

The degree-aligned probe verifies a narrower update for fixed charts.
Use its degree-bound recurrence for runtime routing and retain displaced
words until the inverse reclaims them. The termination certificate may
select the unit tail when the distinct squared node quadratics divide
the previous denominator and their combined degree exceeds its bound.
For other inputs, the four-separated-pole witness already needs ten
words per bank and nine displaced words per row. A smaller uniform
capacity needs a different representation or an exact fallback.

The live termination predicate emits a reversible unit-tail selector
from the extracted heads and chart flags. The noninitial aligned
factor now routes all eight previous/current/incoming flag combinations
and restores its spills. Integration still requires the first factor,
shared spill management, and a capacity proof or an exact fallback.
Keep the selector alive while preparing the selected tail and clear it
once the heads and charts have been restored.

Charge the live routing before sizing a full replay. Even sharing the
mutually exclusive A and B spills within each noninitial factor leaves
a 1,857-qubit floor if every factor owns its own slots. At a ten-word
width the two schoolbook shears alone exceed the resulting gate budget.
Test pooled spill storage across factors and price polynomial
evaluation for the head shears separately. In reversed coordinates the
first head is a degree-two polynomial even on the collapsed chart.
Its conditional shift and the reversed quadratic can be folded into
those three head coefficients before multiplying the bank.

The pooled aligned replay now uses the same spill bank across all
17 live factors. The measured 1,239-qubit stage costs 145,573
executed gates for both row queries and erases. The remaining allowance
at that width is smaller than the measured compact extraction alone.
Treat this implementation as a resource no-go for the existing stage
composition. A successor must remove or combine substantial extraction
and replay work before building a candidate. A spill-capacity flag is a
use guard and requires an exact output path for overflowed inputs.
The exact weight-35 numerator-only counterexample gives a tail that
satisfies the numerator degree constraints and the live jet while
exceeding the denominator degree limit. Require an equivalent
denominator constraint if a new design drops the second replay row.

[Native lifecycle and measurements](../../../docs/d4-reversible-leading-replay-16-11-2026-00-05-48.md)
· [Aligned bands and denser pole stress tests](../../../docs/d4-degree-aligned-bands-16-11-2026-00-23-22.md)
· [Live chart routing and termination](../../../docs/d4-live-chart-and-termination-16-11-2026-00-39-06.md)
· [Pooled aligned replay](../../../docs/d4-pooled-aligned-replay-16-11-2026-00-53-42.md)

## Affine escape at the local second-head pole

The captured s2 fault admits a finite pair after a reversible affine
denominator shear at group 6. The native extraction now carries that
choice across all later external jets and the scalar tail, with the
original measurements repaid in the inverse. The zero-first-head case
keeps the collapsed chart. A second translation keeps the affine
denominator finite when the first choice is singular.

Use the exact unpadded degree trace to size the affine synthesis
handoff. Padding the captured weight-31 pair before that handoff
would overflow the ordinary group-6 coefficient caps. Restore the
original denominator after the affine pair and before the outer folds.
Prove tail recovery for the selected chart and account for the full
padding, converter and scan costs before admitting a candidate.
The scalar preshear using the exact degree-one quotient at infinity
restores the padded degree caps through the finite prefix and ends
in a certifiable unit tail on the captured input. The native kernel
now recovers that quotient from the original live extraction and
tail jet. The measured width and remaining headroom rule out just
adding this probe to the existing stage composition. Test direct
synthesis from the certified unit tail with an exact register
layout at the collapsed group, or reduce the extra replay enough
to integrate the affine version.

The tight unit-tail path has now reached the full projected scan on
the captured s2 syndrome. It aliases the terminal pair and remaining
heads into the coefficient banks, uses the zero high V slot at the
middle collapse, and projects the masks before extraction to avoid a
syndrome copy. The measured 1,005-qubit circuit exceeds the reference
budget. The degree-31 converter reduces the required padding and
shortens the Bezout and Hankel work. Its measured path also exceeds
the reference budget. Before a full campaign, a successor needs a
cheaper complete path and an exact live choice of degree, synthesis
chart, and fallback.

The latest linked probe reduces the cost with initialized first
pivots, a reconstructed-degree certificate, and reclaimed norm and
coefficient storage. The certificate removes the scalar-jet
checks when the live chart and layout make the reconstructed cross
product strictly smaller than the external-node modulus. The local
cost gap is about 7,800 gates at 922 qubits. Do not start full pricing
until the live degree selection, fallback and resource gate close.

The degree-31 probe now verifies live chart, layout, exact degree
and nonzero synthesis pivots before applying the residual scan.
It reverses on rejected inputs and leaves their shared projection
phase available to a future fallback. The measured 926-qubit route
exceeds its cheapest repetition budget even before adding that
fallback. Other chart families and degrees still need coverage.

For the two residual first-head poles, the reciprocal chart's
zero first head permits an in-place regular inverse using one
nonlinear absorber. The guarded native probes share a degree-33
converter and scan. The degree-32 probe pads with a zero root
using the two certified zero spill words. The probes still emit
separate synthesis schedules and need a shared affordable
decoder before qualification.

One guarded emitter now recovers the scalar seed and shares the
complete synthesis, padded conversion and projected scan across
all 12 captured failure and control rows. The root degree bound,
scalar jet and fold guards supply the certificate for the shared
shelf. Its 970-qubit route is still over the price gate and
cannot hold a degree-35 locator before padding.

Collapse arithmetic is now incorporated into the first head at
the evaluation site. Transport uses the existing value and slope
products, and in-place synthesis uses the quotient interpolation
without allocating a masked denominator. The shared live layout
guards remain necessary to select exact coefficients.

The shared emitter now holds an unpadded degree-35 locator. On
all-regular charts one leading-band replay and a two-by-two jet
solve recover the quadratic tail. The remaining mixed full-weight
chart families can exceed this shelf and still need exact coverage.

The shared decoder measures the three seed outputs after
unsynthesis and repays their masks from the solver products. It
releases the collapse controls during each solver visit and
reconstructs them from the intact second heads. A nonzero input
with no exact residual scan can now set a verifier-visible
rejection wire while restoring the other registers.

[Affine proof, differential fixtures and resources](../../../docs/d4-affine-local-chart-16-11-2026-01-22-24.md)
· [Live unit-tail certificate and quotient](../../../docs/d4-live-unit-tail-preshear-16-11-2026-01-41-16.md)
· [Tight unit-tail synthesis and full scan](../../../docs/d4-certified-unit-tail-full-scan-16-11-2026-01-58-18.md)
· [Linked cost reduction](../../../docs/d4-unit-tail-cost-reduction-16-11-2026-02-31-22.md)
· [Live degree-31 routing](../../../docs/d4-live-degree-route-16-11-2026-02-49-49.md)
· [Incoming first-head pole synthesis](../../../docs/d4-incoming-pole-route-16-11-2026-03-01-21.md)
· [Shared synthesis and degree padding](../../../docs/d4-shared-synthesis-16-11-2026-03-33-09.md)
· [Collapse arithmetic fusion](../../../docs/d4-collapse-fusion-16-11-2026-03-46-14.md)
· [Regular full-weight tail and synthesis](../../../docs/d4-regular-full-weight-16-11-2026-03-59-25.md)
· [Tail phase repayment and explicit rejection](../../../docs/d4-tail-repayment-16-11-2026-04-19-24.md)
· [Tail for adjacent outer collapses](../../../docs/d4-adjacent-mixed-tail-16-11-2026-05-04-48.md)
· [Tail for separated outer poles](../../../docs/d4-separated-mixed-tail-16-11-2026-13-23-16.md)

An opt-in mixed lane derives a degree-(3,2) tail for two adjacent
outer collapses from one leading band and a three-by-three
system. It uses the existing guarded projected conversion after
checking both excess high words. A second lane handles outer
collapses at groups 0 and 2 with a nonzero intervening
second-head slope. A six-word replay and a pivoted solve
recover its degree-(4,3) tail. Other separated and denser
charts still require exact coverage.

## Candidate verification and disposition

The archived official comparison and native cloud receipts support
retaining the 897-qubit banked D4 component for the measured variants.
The current-source fixed degree-31 probe clears its ceiling on the
captured chart. Its guarded successor and the separate incoming-pole
routes exceed their ceilings. The shared route explicitly rejects the
incompatible mixed full-weight witness. Keep candidate freeze and new
pooled pricing conditional on a qualifying successor. See the
[hash-bound measured disposition](../../../docs/d4-measured-lane-no-go-16-11-2026-04-37-47.md).

Freeze one candidate with two byte-identical native builds and record
its exact circuit hash, source and backend. On the four original
batches, require all historical errors to clear with zero new value,
phase, mask or scratch errors. Require the same clean result on the
two residual value-error fixtures and their complete reconstructed
batches, and on the pinned constructed inputs at both simulator seeds.
Compare the declared width and largest observed executed mean with the
preflight budget. Keep development salts separate from final pricing
and release confirmation.

For a qualifying candidate, run eight 102,400-shot official draws for
each role at shared fresh salts under the same backend and pinned
pricing procedure. Each circuit hash defines its own input stream.
Bind receipt hashes and circuit identities, and compute the price from
the largest executed per-draw mean, declared width and pooled
repetition factor. Require all eight candidate draws to pass and
strictly beat the matched banked cost in the new campaign. The report
must also disclose any new statistical failures and provide exact
same-input measurements for the known faults. Leave the banked circuit
selected if any required evidence fails or is missing.
Subject any proposed archive replacement to the separate fresh
confirmation and release gates for its exact bytes.
