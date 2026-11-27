# Quantum compilation experiments

A Python toolchain for reproducible quantum-circuit compilation experiments,
independent mathematical checks, and local verification against pinned evaluators.

## Licensing and third-party sources

qcompile is licensed under Apache 2.0. See the [license](LICENSE), the
[attribution notice](NOTICE), and the [third-party source policy](third_party/).

### Open circuit credits

The baseline circuits and verifier come from **Google Quantum AI**. Their
published source identities are recorded separately from project-built
artifacts. [Reference source and hashes](contracts/sources.lock.json)

- **Agniv Banerjee (SomeJoint)** and the credited contributors supplied
  the 897-qubit streamed DQI decoder banked as D4. **mrmeows / team
  selenium** supplied the Q880 DQI candidate built and priced as D5.
  Their notices credit the upstream work of Ahmed Berat Özer, Alex Chilton,
  Dmitrii Gluzdov, ViberTeam, manwithacat, and Phuc Thai.
  [D4 source and credits](third_party/dqi-d4/SOURCE.json) ·
  [D5 source and credits](third_party/dqi-d5/SOURCE.json)
- **Syed Asad Ali** and collaborators supplied the v12 DQI, inverse-square-root,
  and chemistry generators used in the independently rebuilt hybrid. The
  DQI early-tail and padding-exchange work derives from his decoder.
  [DQI notice](third_party/dqi-syed-v12/NOTICE) ·
  [Inverse-square-root notice](third_party/invsqrt-syed-v12/NOTICE) ·
  [Chemistry notice](third_party/dfthcsos-syed-v12/NOTICE)
- **Tony Li and Areeb Ali (Entangled Team)** and **team ThemBones** supplied
  the source-built public portfolio used as an arithmetic and stage control.
  The inverse-square-root build incorporates divider and carry work credited
  to **Geremie Yeo** and **jackvd**. We reproduced all 18 published members
  twice from the v2 source package.
  [Published generators](https://www.kaggle.com/datasets/tonylica/quantum-ai-32-85306-task-generators/versions/2) ·
  [Build hashes](docs/evidence/aggregate34-20261126/tonylica-builds.json)
- **goodpjw2008** assembled the **33.20483975** cloud comparison and supplied
  its chemistry loader work and DQI zero-test changes. The comparison retains
  the Entangled Team DQI lineage and **prvsiyan**'s 37-qubit inverse-square-root
  circuit. [Published comparison and credits](https://www.kaggle.com/code/goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-25226?scriptVersionId=374137004) ·
  [Inverse-square-root origin](https://www.kaggle.com/code/prvsiyan/verifier-guided-quantum-circuit-optimization) ·
  [Archive and member hashes](docs/evidence/aggregate34-20261126/public-cloud-registration.json)
- **Nasir Ali** supplied the rank-42 GF(4096) multiplication tensor used in
  DQI development. [Tensor generator and license](third_party/dqi-scheme42/SOURCE.json)

The source screens credit **manwithacat** for the circuit catalog and its
salt-check records. The shortlist names each candidate's original publisher,
including **Atakan Aldemir**, **Ertuğrul Özer**, **Matt Liston**, and
**Acceleratorer / Accelra** with their upstream generators. Earlier source
reviews retain the full credit chains for output-only inverse-square-root
and chemistry candidates. [Current shortlist](docs/aggregate-above-36-open-circuit-shortlist-26-11-2026-22-34-04.md) ·
[Earlier inverse-square-root credits](docs/evidence/vendored-invsqrt/admission.md) ·
[Earlier chemistry credits](docs/vendored-c40-admission-14-11-2026-22-27-00.md)

## Current state

The independently rebuilt hybrid archive scored **26.78302388** in full cloud
verification and **26.78303192** on a distinct confirmation salt. Its repaired
DQI decoder reduced pooled cost by **9.72%** against banked D4.
[Cloud results and rebuild report](docs/d4-aggregate-independent-rebuild-26-11-2026-02-03-16.md)

The public comparison archive scored **33.20483975** in a full cloud run,
**23.98% above** the certified project's metric score. Its inverse-square-root,
DQI and chemistry costs fell by **24.00%**, **17.80%** and **16.00%**,
respectively. The above-34 release gate still requires a candidate that exceeds
34 on both full verification and independent confirmation.
[Cloud comparison](docs/above-34-cloud-reference-comparison-26-11-2026-06-31-00.md)
[Implementation and development evidence](docs/aggregate-above-34-implementation-26-11-2026-05-40-22.md)

The above-36 work now has a strict two-run certificate gate and measured
component screens. The tested fixed-dictionary and variable-basis chemistry
fits exceeded the accuracy limit. The source inverse-square-root carry rewrite
kept its 39-qubit width and nearly identical charged cost. The exact DQI trace
identified three stages that account for about 87% of executed Toffolis.
[Above-36 implementation and results](docs/aggregate-above-36-implementation-26-11-2026-07-19-40.md)
[Variable-basis chemistry results](docs/aggregate-above-36-chemistry-pilots-26-11-2026-07-29-00.md)

The DQI phase-scan primitive now uses **12 fewer qubits** at the same
charged gate count. A separate supplied-residue scan used **887 qubits**
and **45,045 Toffoli-like gates**. A native stage that prepares, phases,
and uncomputes the residue used **91,569 Toffoli-like gates** across all
4,095 positions. It still needs a compact layout and a coherent source
for the derivative reciprocal before full-decoder pricing.
[Native DQI scan comparison](docs/aggregate-above-36-dqi-residue-scan-26-11-2026-07-46-21.md)
[Native quotient and phase composition](docs/aggregate-above-36-dqi-quotient-26-11-2026-08-00-34.md)

The fixed-chart two-bank degree-35 circuit now prepares, phases, and
uncomputes the residue across all 4,095 positions at **879 qubits** and
**197,937 Toffoli-like gates**. The forward and inverse transform charges
each fell from **153,768** to **76,446**. A complete decoder still needs
locator construction and runtime chart routing.
[Two-bank scan and gate comparison](docs/aggregate-above-36-dqi-series-scan-26-11-2026-08-26-30.md)

The in-place evaluator now takes **12,228 charged gates per direction**,
down from **36,114**. The degree-35 stage from a supplied locator and
syndrome prefix through phase and restoration uses **879 qubits** and
**222,393 charged gates**.
[Evaluator comparison and native restoration](docs/aggregate-above-36-dqi-evaluator-26-11-2026-08-35-31.md)

A regular-chart locator circuit passed reduced native tests from raw
syndrome through phase and restoration. Transposed polynomial products cut
the first degree-35 reciprocal from **83,394** to **36,354 charged gates**
and reduced the supplied-locator syndrome stage to **215,505 gates** at
**879 qubits**. The first three reciprocal steps and their inverses still
exceed the full decoder's allocation when combined with the phase stage.
[Locator baseline](docs/aggregate-above-36-dqi-locator-fraction-26-11-2026-08-46-31.md)
· [Transposed product results](docs/aggregate-above-36-dqi-middle-product-26-11-2026-16-47-11.md)

The version-220 catalog's best existing mix projects **33.22945** using the
48-draw DQI estimate, or **33.25742** under its optimistic zero-failure price.
Tony Li's source-rebuilt DQI is the selected development control. Keeping
the catalog's inverse-square-root and chemistry costs would require a DQI
cost below **240.49B** to exceed 36.
[Open circuit shortlist and source status](docs/aggregate-above-36-open-circuit-shortlist-26-11-2026-22-34-04.md)

On the regular derivative chart, carrying the Euclidean leading
coefficients through the solve reduced the 4,095-position phase stage
from **194,493** to **179,589 gates** at **879 qubits**. The full decoder
still needs locator construction and routing for exceptional charts.
[Projective derivative action](docs/aggregate-above-36-dqi-projective-forney-26-11-2026-17-10-36.md)

Commuting changes to the Givens order preserved the chemistry geometry
and tied the rank estimate. All 64 eligible adjacent swaps increased
the source-priced loader cost. A separate DQI chart screen found that
reversing the syndrome recovered three high-weight cases and left the
lower-weight routing gap open.
[Chemistry order and DQI chart measurements](docs/aggregate-above-36-chem-order-and-dqi-charts-26-11-2026-20-47-09.md)

Controlled DQI padding now accepts compact locator and evaluator banks
at every degree from zero through 35. Software gate replay confirmed
both directions, and the padded derivative chart was regular on **2,043
of 2,048** sampled inputs. A binary padding schedule reduced the
controlled products per direction from **13,464** to **4,584**. The
emitted phase composition still needs native verification, a locator
producer, and an exceptional-chart route.
[Degree padding and resource bounds](docs/aggregate-above-36-dqi-degree-padding-26-11-2026-20-57-28.md)
· [Binary padding comparison](docs/aggregate-above-36-dqi-binary-padding-26-11-2026-21-04-08.md)

The padded phase stage now accepts a live orientation bit and pays
the original mask phase for either order of the syndrome. Reversal
covered all 26 primary derivative-chart failures in a 6,144-input
classical screen. A coherent chart guard now preserves nonregular
inputs and suppresses their phase. Automatic orientation selection,
fallback decoding, and locator construction remain open.
[Orientation and full-position replay](docs/aggregate-above-36-dqi-orientation-26-11-2026-21-14-38.md)
· [Chart guard measurements](docs/aggregate-above-36-dqi-chart-guard-26-11-2026-21-22-13.md)

The standalone locator-only chart test used **30,396 controlled
products** per call in software replay. Setting and clearing an
orientation decision with this test leaves at most **22,261 gates**
for the locator and reversal in the guarded design.
[Chart-selection budget](docs/aggregate-above-36-dqi-chart-probe-26-11-2026-21-28-00.md)

A blocked locator suffix transform matched 17 sequential reciprocal
steps on 12 degree-35 inputs. With its summary supplied, it used
**35,238 controlled products per direction** at **879 qubits** in
software replay. Prefix generation and the final locator fold remain
outside that measurement.
[Blocked locator suffix](docs/aggregate-above-36-dqi-blocked-suffix-26-11-2026-21-36-16.md)

With the linear quotients supplied, a projective degree-35 fold used
**37,596 controlled products per direction** at **885 qubits** in software
replay. The previous monic fold had a **76,440-product** lower bound per
direction. The new fold retains an explicit leading coefficient. Quotient
generation, normalization for the phase stage, and exceptional routing
remain outside the measurement.
[Projective locator fold](docs/aggregate-above-36-dqi-projective-continuant-26-11-2026-21-45-40.md)

The supplied degree-35 quotient tape now composes with the guarded phase
scan and restores the tape at **888 qubits** in software replay. The full
composition uses **269,259 explicit ANDs** before comparison lowering.
That exceeds the strict **256,016.70-gate** DQI ceiling at the public
companion costs. Raw-syndrome extraction and nonregular-chart recovery
still need to fit the complete portfolio.
[Degree-35 phase handoff](docs/aggregate-above-36-dqi-projective-handoff-26-11-2026-21-53-44.md)

Sharing field inverses across the derivative recursion brings the same
degree-35 composition down to **256,203 explicit ANDs** and **202 equality
calls** at **888 qubits** in software replay. This saves **13,056 ANDs** and
**128 equality calls**. The supplied-tape composition still exceeds the
strict public-companion ceiling before quotient generation and recovery.
[Shared reciprocal measurements](docs/aggregate-above-36-dqi-shared-reciprocals-26-11-2026-22-04-38.md)

Borrowing the quotient constant during interpolation brings the same
degree-35 composition to **253,851 explicit ANDs** at **888 software
qubits**, saving another **2,352**. At the measured public companion costs,
this leaves at most **2,165 gates** before comparison lowering, raw
syndrome extraction, and recovery for nonregular charts.
[Borrowed interpolation and root-scan analysis](docs/aggregate-above-36-dqi-borrowed-remainder-26-11-2026-22-13-28.md)

A raw-suffix handoff now takes a supplied 17-step prefix fraction and
the original 36 untouched moments. It preserves the prefix and uses
**28,302 explicit ANDs per direction** at **879 software qubits**. The
measured handoff and blocked suffix transform together exceed the
current gate allowance for locator construction and cleanup.
[Raw syndrome suffix handoff](docs/aggregate-above-36-dqi-raw-suffix-prefold-26-11-2026-22-24-45.md)

The degree-35 development lane uses the selected open controls and an
inclusive **35-point** portfolio gate. The source-backed companion costs
allow about **274,327.64 mean DQI gates** at 888 qubits and zero failures.
Keeping the inner reciprocal factors live reduced the supplied-tape
phase from **256,285** to **248,941 Toffoli-like gates** at 888 qubits
in native replay. That leaves about **25,387 gates** for raw-syndrome
extraction and recovery with the source-built companions at zero
failures. Both full cloud verifier roles must score at least 35 before
the submission archive is ready. The highest complete cloud comparison
is **33.20483975**.
[Degree-35 controls and acceptance](docs/degree35-inclusive-27-11-2026-00-48-55.md)
· [Native inversion and phase comparison](docs/degree35-subtower-27-11-2026-01-03-01.md)

A blocked extractor now emits the initial quotient pairs and exact
residual from the raw syndrome. At degree 35 the nine-pair block used
**109,428 gates per direction** at **891 qubits**. That is 60% below
the sequential estimate for those nine pairs. Even this smaller block
exceeds the budget before the remaining pairs or exceptional routing.
[Native raw-syndrome extraction](docs/degree35-blocked-extraction-27-11-2026-01-15-15.md)

The full chemistry endpoint screen found no affine replacement for
any of the **3,307** charged loader gates in the public comparison.
All 15 loader binaries rebuilt byte-for-byte and the pinned verifier
reproduced **249.170M** over **78,016** trajectories.
[Chemistry replay and 35-point resource limits](docs/degree35-chemistry-affine-27-11-2026-01-27-18.md)

A full-input replay of Tony Li's 39-qubit inverse-square-root control
bounded the possible margin gain from refitting its existing rotations.
Each of the four smallest rotations failed the removal screen even after
refitting the others within the registered bounds.
[Exact phase-margin certificates](docs/evidence/aggregate36-20261126/invsqrt-fixed-predicate-margin.json)

A 192-interval fixed-point quadratic used at most **68.85%** of the
allowed error across all inverse-square-root inputs. Native slices
priced the three coefficient loads and their cleanup. The measured
layouts point to a streamed implementation that avoids keeping all
coefficients live together.
[Inverse-square-root research and lookup measurements](docs/degree35-invsqrt-source-research-27-11-2026-01-39-29.md)

The fused row-add implementation retained one guard bit per product
and passed the full phase model at **81.60%** worst tolerance use.
Borrowing the carry reduced the best arithmetic-only cost product
by **3.0%**, to **103 qubits and 2,660 Toffolis** for computation and
cleanup. The tested schedule still exceeds the 35-point budget before
loading, normalization, or phase.
[Native rounded products](docs/degree35-invsqrt-rounded-products-27-11-2026-01-47-52.md)
· [Borrowed-carry comparison](docs/degree35-invsqrt-borrowed-carry-27-11-2026-01-57-09.md)

Signed add/subtract rows reduced the best arithmetic-only cost product
by **33.8%**, to **107 qubits and 1,696 Toffolis**. Their one-guard phase
model used at most **80.71%** of the allowed error over all **3,133,452**
inputs. The slice exceeds the complete inverse-square-root budget of
**52,119.68** with the current source-built companions.
[Source research and signed-digit comparison](docs/degree35-invsqrt-signed-digits-27-11-2026-02-13-17.md)

In the 39-qubit source control, twelve matched addition rows already use
the signed add/subtract structure. Re-emitting those rows with borrowed
carries passed one trajectory for every legal input. The complete circuit
used 39 qubits and cost **64,504.29** versus **61,696.30** for the control.
[Source carry census and native comparison](docs/degree35-invsqrt-incumbent-rows-27-11-2026-02-25-56.md)

The nonlinear `q19` loan preserved tracked phase in a matched native
comparison. It frees the original rotation target locally for two extra
Toffolis. Both **39-qubit** circuits passed **6,266,904** local verifier
trajectories. The loan cost **61,774.21** versus **61,696.20** for the
matched-layout control.
[Rotation-loan comparison](docs/degree35-invsqrt-rotation-loan-27-11-2026-02-52-43.md)

The circuit-wide idle-wire screen selected 33 recomputation intervals.
The resulting **39-qubit** circuit passed one local verifier trajectory
per legal input and cost **63,490.33** versus **61,696.25** for its control.
[Recomputation coverage and native comparison](docs/degree35-invsqrt-idle-recompute-27-11-2026-03-10-19.md)

The divider checkpoint at line 5,856 has eight clean wires after 320
Toffoli-like gates. Exact witnesses rule out the tested 8-bit and 13-bit
affine phase corrections, even when the 13-bit model includes a joint
term on the next carry cell's four controls.
[Divider checkpoint phase screen](docs/degree35-invsqrt-checkpoint-phase-27-11-2026-03-16-43.md)

The divider prefix and its original return can be joined with `X q28`.
The joined **39-qubit** circuit passed **6,266,904** exact zero-phase
checks at **627.25** mean Toffoli-like gates. It leaves about **467.07**
charged equivalents for new arithmetic at the incumbent's rotation price.
[Measured checkpoint return](docs/degree35-invsqrt-checkpoint-return-27-11-2026-03-24-19.md)

At the divider checkpoint, a fixed-point model with three coefficients
per root and a 10-bit quadratic term passed all **3,133,452** legal
inputs at **85.14%** worst tolerance use. Reversible emission and
the complete gate cost remain open.
[Joint checkpoint phase model](docs/degree35-invsqrt-checkpoint-joint-27-11-2026-03-35-49.md)

The joint phase also passes with a separately rounded 28-bit numerator
and reciprocal at **90.59%** worst tolerance use. This version uses six
parity-dependent constants and 128 reciprocal entries. Two serialized
reciprocal-only schedules exceeded the complete component budget through
rotation count or lookup gates.
[Coefficient precision and native reciprocal lookup](docs/degree35-invsqrt-checkpoint-precision-27-11-2026-03-48-23.md)

Directly dividing the corrected numerator passes all **3,133,452**
legal inputs in the 28-bit numerical model at **90.37%** worst tolerance
use. The native reciprocal-only divider used **49 qubits**, **1,740**
Toffoli-like gates and **29** fine rotations. Its gate cost alone is
**85,260**, beyond the complete inverse-square-root cutoff of **52,119.68**.
The narrowed divider recurrence passes the full numerical domain, and
both available source row layouts exceed the width or gate allowance.
[Reciprocal research and native measurements](docs/degree35-invsqrt-reciprocal-research-27-11-2026-04-04-28.md)

Google Cloud reproduced the native reciprocal and address-only phase-repair
results on **8,192 fresh trajectories each**. Both circuits restored their
inputs and scratch exactly. The reciprocal cost matched the local result.
[Cloud fixture verification](docs/degree35-invsqrt-cloud-reciprocal-27-11-2026-04-32-29.md)

The joint score-35 screen prices inverse square root at **58,000** and
chemistry at **230M**, leaving **297.777B** for DQI. A Google Cloud screen
tested affine replacements for 731 inverse-square-root value gates. All
35 sample matches failed on the full legal input domain.
[Joint targets](docs/degree35-joint-cost-screen-27-11-2026-04-37-37.md) ·
[Cloud routing screen](docs/degree35-invsqrt-affine-routing-27-11-2026-04-45-02.md)

Cloud chemistry screens rejected all three six-bit tables at fixed weights.
The original seven-bit table compiled into eight ten-word loaders, priced
at **342.497M** from static counts versus the verified **249.132M** control.
[Precision, loader width, and score-35 margin](docs/degree35-chemistry-precision-and-joint-margin-27-11-2026-05-00-22.md)

The cloud screen found **2,400** freely assignable seven-bit Givens words.
All three tested assignments preserved decoded accuracy. The best toggle
reduction was **2.64%**, and the same assignment increased the mixed-rank
proxy from **5,805** to **6,741**.
[Zero-angle loader research](docs/degree35-zero-angle-loader-research-27-11-2026-05-12-36.md)

An exact cloud screen of the 206-gate terminal loader found all **124**
independent products necessary with their truth functions and cache frozen.
[Terminal product-deletion screen](docs/degree35-terminal-loader-deletion-27-11-2026-05-21-26.md)

The cloud DQI return screen found zero compatible pair fusions among
**107,045** Toffolis without an inline condition, including Toffolis inside
classical guard blocks. [Affine transport screen](docs/degree35-dqi-return-fusion-screen-27-11-2026-05-32-47.md)
Two follow-up cloud screens found no deletable CCXs in the tested
single-wire and measured-bank models, even with free phase repairs in
the bank model. [Measurement screens and score budget](docs/degree35-dqi-return-measurements-27-11-2026-14-49-29.md)
The published Berlekamp–Massey alternative exceeds the width and gate
budgets at its reported layout. [Decoder research comparison](docs/degree35-dqi-berlekamp-massey-research-27-11-2026-05-37-57.md)

[Research index and branch audit](docs/research-and-branch-audit-26-11-2026-03-03-28.md)

The v8.0 archive scored **2.6228156034** in both the full metric and fresh
confirmation on Google Cloud. The routed decoder lowered DQI cost by **71.11%**
from v6. [v8.0 verification and release record](docs/v8.0-release-15-11-2026-15-01-00.md)

Agniv Banerjee (SomeJoint) and the credited contributors' Apache-2.0
897-qubit decoder passed the registered pooled pricing screen and was banked as
`dqi-v8`. Its pooled DQI cost was **416,454,072,253.15**.
[Decoder comparison and credits](docs/dqi-public-pricing-15-11-2026-15-01-00.md)
The multiplier audit found that D4 already uses 42 Toffolis per full-field
product. [Multiplier audit](docs/dqi-multiplier-audit-15-11-2026-15-21-00.md)

The public inverse-square-root screen retained the confirmed v6 circuit.
[Source admission findings](docs/invsqrt-public-admission-15-11-2026-15-06-00.md)

The v6 hybrid passed all three benchmarks on a fresh archive extraction
in Google Cloud. Its aggregate score was **1.7339568375**, up **4.70%**
from v5. Inverse-square-root cost fell **12.86%** to **411,586.92**.
The retained DQI and chemistry costs reproduced exactly.
[v6 paired cloud verification](docs/v6-paired-cloud-09-11-2026-01-25-00.md)

The fully verified v5 hybrid scored **1.6561824298**, up **2.55%** from
v4. Trimming known zero bits reduced inverse square root to **150 qubits**
and **2,908 Toffoli-like gates**. Its verified cost was **472,336.92**,
**7.29% below v4**. The full local verifier and fresh confirmation each
passed **200,540,928** trajectories. A third independent archive build
passed the cloud metric on a fresh extraction and reproduced the DQI
and chemistry costs. [v5 paired verification](docs/evidence/invsqrt-trimmed-paired-20261108/comparison.json)
[Submission handoff](docs/v5-submission-handoff-08-11-2026-17-06-56.md)

The v4 hybrid scored **1.6149243284**, up **2.51%** from v3. Its 28/20/14
lattice refinement lowered inverse-square-root cost from 548,860.92
to **509,471.48** and width from 159 to **155 qubits**.
[v4 paired verification](docs/evidence/invsqrt-roadmap-archive-20261108/comparison.json)

### Next-round cloud comparison

| Experiment | Control cost | Candidate cost | Cloud result |
|---|---:|---:|---|
| v6 inverse square root | 472,336.92 | 411,586.92 | **12.86% lower** in the full cloud verifier. Width stayed at 150 qubits and Toffoli-like gates fell from 2,908 to 2,503. |
| Routed DQI, `(63, 4)` | 43.385 billion | 11.807 billion | **72.79% lower** on 2,560 matched trajectories with zero observed errors. |
| Routed DQI, `(127, 12)` | 357.434 billion | 88.971 billion | **75.11% lower** on 2,560 matched trajectories with zero observed errors. |
| Routed DQI, `(4095, 70)` | 101.381 trillion | 29.293 trillion | **71.11% lower** on 2,560 matched trajectories with zero observed errors. |

The v6 screen built each circuit twice, checked all 3,133,452 inputs
against the phase model, and passed 31,232 native trajectories per circuit.
The frozen v6 circuit passed all **200,540,928** trajectories in each of
the full-strength and fresh confirmation runs. Both reproduced the
screened cost and **66.77%** worst-case phase tolerance use. Paired archive
verification reproduced the same component cost and coverage.
[v6 cloud confirmation](docs/v6-confirmation-cloud-09-11-2026-00-37-00.md)

The full-size DQI sampling campaign selected **history depth 2**. Four of
10,000,000 shots needed more than two retained discrepancies, and none
needed more than three. The routed circuit used **1,942 qubits**, up from
1,893 in the control. The table uses development costs at 2,560 shots.

The same routed DQI circuit passed five pricing runs, full verification,
and fresh confirmation with **zero errors in each 102,400-shot run**.
Its full verifier cost was **7.062 trillion**, **71.11% lower** than the
retained DQI cost of 24.439 trillion. Conservative pricing was **7.122
trillion**, below the **12.220-trillion** promotion gate. The routed
decoder has component verification. The v6 archive used the retained
decoder. The later v8.0 archive verified the routed decoder in the complete
three-task metric.
[DQI depth decision](docs/dqi-depth-cloud-08-11-2026-23-50-00.md)
[Full-size DQI comparison](docs/dqi-full-matched-cloud-09-11-2026-01-29-00.md)
[Full-strength DQI verification](docs/dqi-full-strength-cloud-09-11-2026-02-17-00.md)

Chemistry's pinned reference yielded an
initial S2 offset bound of **11.5** and a penalty of **1.0**. Its compressed
fit must pass the residual gates before the loader projection can compare
candidate costs. Lane A completed all 400 sweeps, and its lowest sweep
residual was **41.57 mHa**. The VM cutoff interrupted the subsequent
polish before it wrote a terminal result.

The cloud suite passed **766 tests**, and four additional frozen-round
checks passed. Subsequent native lookup fixtures exercised all 512
addresses, including randomized measurement phase repair and a dropped-CX
mutation. The batched DQI sampler reproduced two complete scalar chunks
before starting its own full-depth registration. Six reduced DQI tests
covered every error weight at both reduced sizes and detected deliberate
branch, tag, history, and mask defects.
[Cloud validation](docs/cloud-review-validation-08-11-2026-21-50-18.md) ·
[Depth sampler comparison](docs/dqi-batched-depth-sampling-08-11-2026-22-36-00.md)

### v3 comparison

The fully verified v3 hybrid scored **1.5753293577**, up **14.32%** from
v2. Two independent builds and the Google Cloud rebuild produced the
same archive. The pinned evaluator passed all three benchmarks on a
fresh extraction.

| Component | v2 cost | v3 cost | Result |
|---|---:|---:|---|
| Inverse square root | 820,078.95 | **548,860.92** | 33.07% lower cost and 159 qubits, down from 175 |
| DQI | 24,439,466,510,149.91 | 24,439,466,510,149.91 | Retained reference decoder |
| Chemistry | 3,247,752,448.67 | 3,247,752,448.67 | Retained nine banked ANGLE circuits and factorization |

The v3 inverse-square-root circuit combines binary normalization,
measurement unlookup with phase repair, and lower coefficient precision.
Full WSL verification, fresh WSL confirmation, and archive verification
each passed **200,540,928** trajectories on identical circuit bytes.
The worst input used **71.96%** of its phase tolerance.

The full-size cloud DQI development test cut cost by **5.09%** with zero
observed errors in 2,560 matched shots, short of the 2× promotion threshold.
The chemistry pilot ranked 384 layouts. All three compressed fits missed
the 19.5 mHa residual gate.
The [v3 validation report](docs/advance-hybrid-validation-08-11-2026-05-33-43.md)
records the development results, full archive comparison and receipts.

### Roadmap measurements

The v4 circuit passed two full verifier runs on identical frozen bytes.
The inverse-square-root component cost fell **7.18%**.

The full-size DQI profile found that the locator and its reversal account
for **73.69%** of counted gates. The standalone phase scan passed native
checks across all 4,095 positions, and the subtower inverse passed all
4,096 inputs at 102 Toffoli-like gates. Those are primitive results.
The native three-word routed round now computes its branch, updates the
signed counter and reverses cleanly at **983 Toffoli-like gates** per
direction. A separate radius-one decoder passed all 2,560 matched
development cases at `(63, 2)`. The full-size decoder remains in
development. [Routed round](docs/dqi-native-arithmetic-round-08-11-2026-15-42-52.md) ·
[Reduced decoder](docs/dqi-radius-one-composition-08-11-2026-15-37-00.md)

The half-degree Bézout construction matches the independent DQI
reciprocal on reduced exhaustive fixtures and sampled cases at all
weights through 35. A reversible monomial update passed native tests.
Fixed-degree native division now generates two or three quotient digits,
with an adjoint that clears the saved history.
[Native quotient division](docs/dqi-half-eea-division-08-11-2026-16-50-16.md)
General reversible quotient generation and full decoder admission remain
open. [Half-degree reciprocal work](docs/dqi-half-degree-bezout-08-11-2026-16-12-49.md)

The registered chemistry loader ranked all seven legal batches on
the pinned reference factors. Its best development estimate was
**3.2504 billion**, 0.081% above the existing verified chemistry cost.
Two builds reproduced the winning family and verified all 4,096
binary addresses, including padding.
[Reference loader ranking](docs/chemistry-loader-reference-ranking-08-11-2026-15-48-27.md)

The local I3 fit reached **81.40 mHa** after 1,500 evaluations. A
separately registered restart reached **41.57 mHa** after 5,000 more
evaluations. The continuous gate is **19.0 mHa**. Four pinned shape
profiles and initializer rankings now bind the **24 fit plans**.
[Continuation result](docs/chemistry-i3-continuation-result-08-11-2026-16-19-24.md) ·
[Grid registration](docs/chemistry-fit-grid-08-11-2026-16-16-34.md)
The fixed-basis relaxation adds a separate projection diagnostic.
[Fixed-basis diagnostic](docs/chemistry-fixed-basis-bound-08-11-2026-16-51-28.md)

The direct inverse-square-root cost model matches width and counted
gates on 27 comparable circuit receipts.
[Resource model calibration](docs/invsqrt-costmodel-08-11-2026-16-08-55.md)
The tested compact phase-accumulation design missed its 20% cost gate.
[Compact phase screen](docs/invsqrt-compact-phase-08-11-2026-16-31-25.md)

### Earlier hybrid results

The reference and independent mathematical checks are complete. The certified
comparison archive combines direct inverse-square-root phasing with nine
banked chemistry circuits and the reference DQI circuit. It scored
**1.2861761126**, up from **1.0286345857** for the previous hybrid.

| Benchmark | Locally measured change | Full trajectories in the hybrid |
|---|---:|---:|
| Inverse square root | 51.44% lower cost | 200,540,928 |
| Chemistry | 3.21% lower cost | 254,464 |
| DQI | Identical reference circuit, zero observed errors | 102,400 |

The [original hybrid validation report](docs/banked-chemistry-07-11-2026-01-52-35.md)
records the parent archive and its component results. The
[independent validation audit](docs/step3-completion-02-11-2026-13-20-23.md)
records the primitive and defect-control evidence.

[Direct polynomial phasing](docs/direct-polynomial-invsqrt-07-11-2026-13-43-15.md)
produced a **199-qubit** circuit costing **1,008,498.12**, a **48.85%** reduction
from the hybrid's inverse-square-root component. Full verification and fresh
confirmation each passed **200,540,928** trajectories on identical circuit
bytes. The worst input used **27.29%** of its allowed phase error.

The successor archive keeps the original chemistry and DQI members by hash.
A paired parent replay with the same archive seed matched both retained
costs and isolated a **25.04%** aggregate gain from inverse square root.
Both archives are locally certified. The
[successor archive evidence](docs/direct-hybrid-paired-verification-07-11-2026-14-59-24.md)
links the exact ZIPs, coverage and confirmation lineage.

### v2 hybrid optimization

The fully verified v2 hybrid scored **1.3779715418**, a **7.14%** gain over
the certified comparison archive. Only the inverse-square-root circuit differs
between the archives. The paired run reproduced the retained DQI and chemistry
costs using the same archive seed.

| Lane | Certified control | New result | Evidence |
|---|---:|---:|---|
| Inverse square root | 199 qubits, 1,008,498.12 cost | 175 qubits, 820,078.95 cost | 18.68% lower cost. Full verification, fresh confirmation, and paired archive verification each passed 200,540,928 trajectories on the same circuit bytes. |
| Chemistry | 3,247,752,448.67 cost | 3,240,974,365.97 cost with refit J9 | 0.21% lower in a 15,904-trajectory native screen. J8 was 3.11% higher than the certified control. Both missed the 10% promotion threshold. |
| DQI | Reference decoder | EEA and BM update slices | The native EEA fixture used 110 qubits and 480 Toffoli-like gates. The BM fixture used 158 and 528. The paired 2,560-shot reference control passed with zero errors. |

The [full verification report](docs/next-hybrid-paired-archive-08-11-2026-01-13-24.md)
links the archive hash, complete coverage and matched costs. The
[development report](docs/next-hybrid-validation-08-11-2026-00-04-43.md)
records the 309-test run, the original screens and their promotion decisions.

## Archive operations

Prepare each locally certified archive after structural preflight and
the published evaluator hash check. Review the external score against
the registered band before preparing another archive. Aim to collect
the receipt within 24 hours of certification.

Reserve two daily slots from the planned architecture freeze through
final selection. Select the highest-scoring certified archive and the
highest-scoring remaining archive with exact DQI. Keep the local
certificate and external score receipt separately.

## Install and check

Run from the repository root in Linux or Ubuntu WSL using
[uv](https://docs.astral.sh/uv/). The native backend requires Linux and Python 3.13.
Independent checks also support Python 3.12 on Linux/macOS.

```bash
export UV_PROJECT_ENVIRONMENT=vendor/linux-env
uv sync --frozen --python 3.13
uv run qcompile test --tier unit
uv run qcompile test --tier extended
uv run ruff check src tests
uv run ruff format --check src tests
uv run qcompile contract validate
```

Contract validation returns exit code **0** when the pinned inputs and required
evidence are available. It returns **2** and identifies missing or changed inputs
when provenance checks fail. The extended tier scans all 3,133,452 valid
inverse-square-root inputs as a numerical harness control.

## Implemented components

| Component | Behavior |
|---|---|
| Contracts and assets | Source hashes, per-field provenance, backend inventories, and validation gates |
| Inverse square root | Integer target brackets, circular phase comparison, high-precision checks, and exhaustive margin scans |
| Fixed-point arithmetic | Explicit widths, signedness, rounding, overflow, Horner models, and Newton steps |
| Resource models | Margin-aware rotation pricing, confidence bounds, repetition penalties, and complete modeled costs |
| DQI | Independent finite-field backends, BM/EEA decoder controls, syndrome recovery, and variable-mask parity |
| Chemistry | NPZ preflight, ordered trees, angle reconstruction, XOR batching, residual calculations, and workspace accounting |
| Verification adapters | Pinned native execution, raw diagnostics, actual coverage counters, environment identity, and timeouts |
| Profiling | Preregistered baseline repetitions, stage timings, process-tree memory, planning budgets, and frozen evidence |
| Experiments | Candidate registration, evidence-bound state transitions, bounded experiments, and fresh confirmation history |
| Artifact builds | Deterministic NPZ/ZIP output, safe extraction, independent recipe builds, and local verification certificates |

Mathematical and native checks retain their input assumptions, coverage, and
provenance. The validation tools under `tools/` compare independent calculations
with the pinned evaluators and exercise known-invalid fixtures.

## Configure local inputs

Install the reviewed evaluator notebook, verifier sources, compatible native
backend, and reference artifacts at local paths. Preserve their original bytes
and match the source identities in `contracts/sources.lock.json`. Input files
are kept in ignored local storage.

```bash
uv run qcompile assets pin-backend \
  --metric /absolute/path/to/metric.ipynb \
  --verifiers /absolute/path/to/verifiers \
  --kickmix /absolute/path/to/kickmix \
  --output vendor/backend.json

uv run qcompile baseline verify \
  --artifact-dir /absolute/path/to/reference-artifacts \
  --backend vendor/backend.json --tier full \
  --seed-policy configs/local-seed.json --output runs/baseline-full
```

Native binary compatibility must be established on the target machine. Keep
actual coverage counters and raw verifier results with each run. Full-strength
verification provides the baseline evidence used by later experiment gates.
See [operator formats](docs/operator-formats.md) for configuration and record schemas.

## Experiments and profiling

Baseline profiling uses `qcompile baseline campaign` from a clean committed Linux
checkout, followed by `qcompile baseline freeze`. The campaign preregisters A,A,B
salts, coverage, and resource limits. It retains stage/process-tree measurements
and verifies deterministic evidence archives. The
[campaign guide](docs/baseline-campaign-02-11-2026-01-19-10.md) explains measurement
scope, sampling limits, and archive contents.

A deliberately inaccurate numerical model provides a diagnostic example.

```bash
uv run qcompile experiment run --config configs/invsqrt-initial.json
```

It evaluates a constant model over inputs 1–1024 and records nonpositive margins.
Registrations, failures, environment details, and reports use content-derived run
identities. The completed
[width screen](docs/invsqrt-opportunity-07-11-2026-00-44-21.md) documents the
current inverse-square-root incumbent and its two full-strength runs.

## Candidate verification and reproducible builds

Candidate commands register artifacts, consume evidence for state changes, run
verification, and record preregistered confirmation. The hybrid workflow tracks
confirmation for each optimized benchmark and includes the exact chemistry
factorization and tree in the chemistry record.

```bash
uv run qcompile candidate register --selection /path/to/candidate-selection.json
uv run qcompile candidate status --id CANDIDATE_ID
uv run qcompile candidate verify --id CANDIDATE_ID --tier full \
  --backend vendor/backend.json --seed-policy configs/local-seed.json --output runs/candidate-full
uv run qcompile candidate confirm --id CANDIDATE_ID --tier full \
  --backend vendor/backend.json --protocol /path/to/confirmation.json \
  --seed-policy /path/to/confirmation-seed.json --output runs/candidate-confirmation
uv run qcompile release build --selection /path/to/release-selection.json --output releases/RELEASE_ID
uv run qcompile release verify --release releases/RELEASE_ID --tier full \
  --backend vendor/backend.json --seed-policy configs/local-seed.json \
  --supporting-evidence /path/to/supporting-evidence.json --output runs/release-full
```

The builder runs each pinned recipe in two fresh directories, compares the
resulting archives, and verifies a fresh extraction. Local certification requires
complete coverage, measured cost improvement, and supporting numerical, primitive,
mutation, stability, confirmation, and opportunity evidence.
