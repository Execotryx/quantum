# Google Verifiable Quantum Circuit Compilation — Detailed Implementation Plan

**Prepared:** 26 October 2026  
**Revised:** 27 October 2026 — aligned with the v2 research report  
**Status:** implementation started 30 October 2026; G0 remains blocked on official data access. See [implementation status](implementation-status.md) for measured scope and outstanding gates.
**Source:** `deep-research-report-v2.md`, revision dated 27 October 2026  
**Source SHA-256:** `b8ae2954bfdeee3d583afa3eba43a34c8dfcec3adcd3f35f61a833401d2ce5e4`

This revision adds executable rotation pricing, a bounded opportunity screen, explicit correctness-claim scope, fresh frozen-candidate confirmation, DQI failure categories, chemistry representation-stability checks, and stronger validator negative controls. Earlier effort ranges are retained only as historical planning inputs and must be re-estimated for the expanded requirements. “V2 research report” below refers to this supplied report; “Google paper v2” refers separately to the companion paper.

## 1. Goal, scope, and evidence boundary

Build a reproducible toolchain that produces a valid competition ZIP and improves at least one benchmark's official resource cost while preserving validity of all three components. The preferred first experiment is inverse square root because its numerical input domain can be checked exhaustively. This preference is provisional until baseline profiling establishes feasibility and cost.

The source report supplies the research basis. This plan adds implementation tasks, interfaces, test tiers, decision rules, and release evidence. It does not certify the report's external sources, current competition availability, baseline acceptance, package compatibility, or any performance improvement. No official evaluator, circuit, or optimization has been executed while preparing this plan. All competition constants below are **report-derived requirements pending G0 reconciliation**.

The official metric notebook, starter kit, exact schemas, and reference archive must be acquired and run in G0. A conflict between the paper, rules, and package becomes a recorded blocker for the affected work; do not silently choose whichever version is easiest to implement.

### 1.1 Two delivery scopes

| Scope | Included work | Completion condition | Original provisional effort; re-estimate required |
|---|---|---|---:|
| First improved release | G0, conservatively budgeted full G1, one optimization workstream, G5 | All components accepted; at least one lower official cost; aggregate score above reference | **27–41 person-days** through inverse square root |
| Full research program | G0–G5, including all three optimization workstreams | Each workstream has documented results; release uses the best validated component available for each task | **79–126 person-days** |

These are the original engineering ranges, not estimates validated for the v2 additions, elapsed-time commitments, or guarantees of improvement. Re-estimate the selected scope after G0 and the bounded opportunity screen; do not assume the added confirmation, numerical, and representation checks fit unchanged within these ranges. They assume competence in reversible circuits and numerical methods and exclude potentially substantial chemistry optimizer compute. A failed research hypothesis can close an experiment without producing a replacement circuit. It does not satisfy that workstream's improvement gate.

Do not start all three optimization programs to obtain the first release. If an unchanged component's reference is invalid, it cannot be used as a fallback; resolve that baseline blocker before assembling a complete submission.

### 1.2 Non-goals for the first release

- No custom general-purpose quantum compiler or generic state-vector simulator.
- No automatic translation of Gu et al.'s released circuits into Kaggle-compatible solutions.
- No mandatory new DQI decoder or chemistry factorization if those references pass.
- No exhaustive enumeration of measurement branches for a whole large circuit.
- No claim that a local randomized test reproduces Kaggle's private challenge stream.

## 2. Dependency structure and completion gates

```mermaid
flowchart TD
    G0["G0: Pin contract and validate references"]
    G1["G1: Independent mathematical checks"]
    PICK["Bounded opportunity screen and re-estimate"]
    INV["G2: Inverse square root"]
    DQI["G3: DQI"]
    CHEM["G4: Chemistry"]
    REF["Preserve accepted reference components"]
    G5["G5: Rebuild and verify final archive"]
    ACCEPT["Kaggle acceptance and result record"]
    G0 --> G1
    G0 --> REF
    G1 --> PICK
    PICK --> INV
    PICK --> DQI
    PICK --> CHEM
    INV --> G5
    DQI --> G5
    CHEM --> G5
    REF --> G5
    G5 --> ACCEPT
```

Only one optimization branch is required before G5. Every submitted component still needs full release verification.

| Gate | Required evidence | Failure response |
|---|---|---|
| G0 | Immutable snapshot; resolved contract and correctness scope; reference accepted near 1.0; component profiles and targeted negative controls | Diagnose versions, schema, baseline, or ineffective validation; block affected optimization |
| G1 | Independent mathematical, extreme-tail, rotation-cost, and representation fixtures agree with pinned evaluator; primitive evidence and negative controls pass | Reduce discrepancy to a fixture; resolve convention before synthesis |
| Opportunity screen | Budgeted complete-cost prototype for each seriously considered workstream; explicit go/no-go decision and revised selected-path estimate | Stop or redirect on incompatibility, infeasibility, or no credible complete-cost gain |
| G2 | Exhaustive numerical feasibility; zero full-verifier failures; lower official inverse-square-root cost | Retain reference; close or revise hypothesis |
| G3 | Exact-algorithm BM branch has sampled acceptance; stable penalty and lower full cost for a replacement; selected candidate independently confirmed | Keep exact control/reference; distinguish decoder, phase, register, and workspace failures; failed confirmation reopens development |
| G4 | Quantized-output reconstruction passes every constraint; legal representation/stability checks; angle widths within limit; lower full chemistry cost | Retain validated factorization/reference; revise precision or representation |
| G5-local | Two reproducible builds; extracted ZIP passes all full checks; frozen confirmation, mutation diagnostics, and scoped correctness evidence match hashes | No submission-ready status; fix or roll back |
| G5-remote | Exact ZIP accepted by Kaggle, with result identifier and score retained | Investigate discrepancy; do not label local pass as remote acceptance |

## 3. Contract to implement

Every value in this section must have a provenance entry in `contracts/contract.json`: report location, official source path and symbol or notebook cell, version/hash, extracted value, and reconciliation status. Unknown names or array shapes stay explicitly unresolved; do not guess them from notation.

For each circuit, also declare the valid input subspace, scratch initialization, classical-record assumptions, allowed measurement behavior, required register/phase relation, and composition assumptions. State whether unused addresses are constrained. Sampled-input acceptance depends on the intended input-state probabilities; it is not an unrestricted worst-case guarantee for arbitrary coherent quantum inputs.

Every correctness claim must carry one of three evidence descriptions: **exact-algorithm design intent**, **algebraically proved primitive property** (with assumptions and proof reference), or **sampled circuit acceptance** (with distribution, seeds, coverage, and failures). A candidate can have several evidence records, but zero observed failures alone never promotes it to a proved exact circuit.

### 3.1 Inverse square root

| Property | Report-derived requirement |
|---|---|
| Input | Exactly one named quantum register `x`, 22 bits |
| Valid domain | Integers `1..3_133_452`, inclusive |
| Transformation | Preserve `x`; apply phase `exp(2πi / sqrt(x))`; restore all scratch to zero |
| Phase comparison | Turns modulo one; verifier-specific 64-bit fixed-point ideal computed using integer square-root arithmetic |
| Tolerance | Circular phase error at most `2^-24 / sqrt(x)` turns |
| Release trajectories | 64 per valid input; **200,540,928** total |
| Failure budget | Zero |
| Objective | Official `Q × C`, including the fine-rotation synthesis charge |
| Reported baseline | `Q=260`, 7,735 Toffolis, one T gate, 37 non-Clifford rotations, `C=7,988` |

The schematic arithmetic expression `C = N_Toffoli + N_T/4` is insufficient unless `N_T` includes the official treatment of synthesized rotations. Implement the exact evaluator pricing and rounding rules rather than deriving cost from raw instruction counts alone. The reported product `260 × 7,988 = 2,076,880` is a reconciliation target, not a substitute measurement.

The input `x=1` has phase one turn, equivalent to zero. Tests must catch linear rather than circular phase subtraction. The circuit's rotation encoding and the verifier's phase accumulator use different precisions; pin both.

#### Executable rotation-price specification

For `n_rot > 0`, implement the report's Google-paper-v2 price using the remaining wrapped-phase margin:

\[
m_{\min}=\min_x\left(2^{-24}/\sqrt{x}-|\operatorname{wrap}_{[-1/2,1/2)}(\theta(x)-1/\sqrt{x})|\right),
\qquad \epsilon_{\rm rot}=\frac{\pi m_{\min}}{n_{\rm rot}},
\]

\[
t_{\rm fine}=0.56\log_2(1/\epsilon_{\rm rot})+5.3.
\]

Here `t_fine` is the T-gate charge per fine rotation. Pin the actual classification of Clifford, T, and finer rotations and the evaluator's precision, rounding, and aggregation; do not double-count the fine-rotation charge. Use the official equal-allocation price, including the stated factor of π. A proposed nonuniform physical synthesis budget is a separate optional research idea and cannot replace this scoring rule.

Reject invalid/non-finite margins rather than clipping them to obtain a finite cost. Handle `n_rot=0` through a separately tested branch matching the pinned evaluator, without division by zero. Record minimum margin in turns and verifier fixed-point units, rotation count, allocated error, and aggregate price. Fixtures must cover turns versus radians, wrapping at `x=1`, normalization transitions, near-zero/invalid margins, and zero fine rotations.

The smallest stated tolerance is about `3.37e-11` turns at the maximum input; that number alone does not prove binary64 inadequate. Compare the actual fixed-point pipeline with higher precision where cancellation or rounding matters. Jointly optimize arithmetic error, widths, and rotation count: a smaller margin can make a seemingly cheaper arithmetic circuit more expensive overall.

### 3.2 DQI / Reed–Solomon

| Property | Report-derived requirement |
|---|---|
| Parameters | `(m,n,b,r)=(4095,70,12,2016)`; unique decoding radius 35 |
| Field modulus | `z^12 + z^6 + z^4 + z + 1` |
| Encoding | Little-endian polynomial basis `(1, α, …, α^11)` |
| Syndrome | 70 field elements, 840 quantum bits; `s_i = Σ_j e_j α^((i+1)j)` |
| Classical record | Fresh per-instance `c`, 49,140 bits; exact binding mechanism to be pinned |
| Required phase | `(-1)^(c · bin(e(s)))`, syndrome preserved, scratch clean |
| Official sample count | `N=102,400` |
| Failure bound | One-sided Clopper–Pearson upper bound with tail probability `δ=2^-128` |
| Objective | `R(ε⁺) Q² T`, with the evaluator's definition of `T` |
| Rejection threshold | `ε⁺ >= 1/16` has no finite score |
| Reported baseline | 1,893 qubits; **5,725,461 Toffolis** |

Here `R(ε)=ln(2)/[-ln(1/2+2 sqrt(ε))]`. For zero failures, `ε⁺=1-2^(-128/N)`, approximately `0.0008660587302`, and `R≈1.191260465`. Zero observed failures does not remove the repetition penalty.

The official distribution samples error weight from the specified eigenvector distribution, then distinct positions and nonzero field symbols, and an independent random mask. Import and validate the exact sampler or its defining data in G0; do not replace it with uniform weights. Uniform coverage of weights 0–35 belongs in correctness testing, separately from score estimation.

### 3.3 Chemistry

| Property | Report-derived requirement |
|---|---|
| Instance | FeMo-co; 76 orbitals, 113 electrons |
| NPZ arrays | `U`, `W`, `H2_I`, `H1_I`, `Hsym_lower`, `tree_edges`; shapes/dtypes/conventions pinned in G0 |
| Frozen symmetry | `S=S0`, `β1=β1,0`; supplied values are not search parameters |
| Selection addresses | First `N` one-body vectors, then `RB` two-body vectors; width `ceil(log2(N+RB))` |
| Angle words | β-bit fixed-point representation of `[0,2)`; exact angular-unit conversion pinned in G0 |
| Batching | `J` angles per batch; `K=ceil((N-1)/J)` circuits |
| Forward operations | First batch load, then XOR differences between successive batches |
| Reverse operations | Undo sequence and return angle storage to zero |
| Width limit | At most **128 qubits per angle circuit** |
| Release testing | 64 measurement samples per valid vector address under the official forward/reverse protocol |
| Residuals | Both coefficient Frobenius residuals at most `0.020 Ha` after reconstruction from emitted angle words |
| Energy reference | Core-inclusive `E_upper = -22140.27335 Ha` |
| Strict conditions | Finite metrics; `Λ>49.0`; `E_gap>3.914898`; `0<E_gap<2Λ` |
| Objective | `λ_eff T_tot Q_tot`, where `λ_eff=sqrt(E_gap(2Λ-E_gap))` |

The two-electron residual is

\[
\epsilon_2=\left\|\widetilde h^{(2)}-h^{(2)}-\frac{S_0\otimes I+I\otimes S_0}{2}\right\|_F.
\]

The one-electron residual compares the reconstructed transformed one-electron tensor with the official transformed target. Pin its dependence on candidate factors and its eigenvector matching convention; avoid inventing an independent sign/order convention that disagrees with the evaluator.

Compute `E_gap = E_upper - E_SOS` with consistent energy conventions. Do not clamp an invalid gap or normalization value into the feasible region. `Q_tot` is the complete modeled qubit cost and is **not capped at 128**. It includes persistent registers and the maximum of shared sequential temporary-workspace requirements. `T_tot` includes both oracle traversals, Outer/Inner state preparation, and Givens costs.

These residuals are coefficient-space constraints, not guarantees of a 20 mHa many-electron energy error.

### 3.4 Archive contract

Use canonical binary circuits for releases. Required paths are:

| ZIP path | Source |
|---|---|
| `invsqrt.kmb` | Selected generated circuit or validated reference |
| `dqi.kmb` | Selected generated circuit or validated reference |
| `dfthcsos/angle_k_0.kmb` through `angle_k_<K-1>.kmb` | Contiguous zero-based angle circuits |
| `dfthcsos/submission.npz` | Matching factorization and tree |

The report also permits `.kmx`; G0 must verify the live rules. Avoid including both encodings of the same circuit. No extra enclosing directory. Keep certificates, logs, and manifests beside the ZIP unless the pinned rules explicitly allow them inside. The baseline reportedly contains ten angle circuits; a new candidate's `K` follows its validated `J` and contract, not that baseline count.

## 4. Minimal implementation architecture

Use one Python project with the official kickmix execution backend and an ordinary command-line interface. Python handles orchestration, references, search, and reports. Profile first; move a numerical kernel to a compiled/vectorized path only when measurements justify it. Do not build a second full kickmix simulator.

| Proposed path | Responsibility |
|---|---|
| `contracts/` | Resolved constants, schema, source manifest, discrepancy register |
| `vendor/README.md` | Acquisition instructions, immutable versions, licenses; no unlicensed redistribution |
| `src/qcompile/official.py` | Narrow adapter to the pinned official loaders, evaluator, and scorer |
| `src/qcompile/reference/` | Independent numerical and algebraic implementations |
| `src/qcompile/invsqrt/` | Fixed-point model, approximation search, circuit generator |
| `src/qcompile/dqi/` | Generated field constants, exact BM, phase extraction, explicit approximations |
| `src/qcompile/chemistry/` | Factorization, tree/quantization, batching, QROM generation |
| `src/qcompile/artifacts.py` | Serialization, hashes, deterministic NPZ/ZIP, extraction preflight |
| `src/qcompile/experiments.py` | Candidate records, budgets, promotion decisions |
| `tests/` | Unit, differential, mutation, integration, and release tiers |
| `configs/` | Immutable experiment configurations and release selections |
| `runs/<run_id>/` | Logs, metrics, profiles, fixtures, and artifacts tied to a run |
| `releases/<release_id>/` | ZIP, hash manifest, certificate, and remote result |

Keep reference implementations independent of generator arithmetic. They may share frozen contract data and serialization readers, but must not share the numerical kernel they are intended to validate. Production adapters wrap the official implementation; independent checks cross-validate it rather than silently replacing it.

Document any shared numerical libraries or helpers that can create common-mode failures. Independence of function names alone is insufficient; identify how high-precision fixtures, polynomial models, and small coherent/algebraic checks test different failure mechanisms.

### 4.1 Proposed interfaces

The following interfaces and CLI are design targets, not existing official APIs:

```python
load_contract(path) -> Contract
validate_static(artifact, contract) -> StaticReport
build_candidate(config, contract, output_dir) -> ArtifactSet
verify_candidate(artifacts, contract, tier, seed_policy) -> VerificationReport
score_candidate(artifacts, verification, contract) -> ScoreReport
package_release(selection, contract, output_dir) -> ReleaseRecord
```

`ArtifactSet` identifies each file as `generated` or `retained_reference`, its hash, provenance, and relevant benchmark. `VerificationReport` records contract assumptions, correctness-claim scope, development/confirmation/official run role, completed versus expected cases, failure categories, seed provenance, and exact evaluated hashes. `ScoreReport` separates estimated cost from official measured cost and rejects missing or non-finite inputs. Failed validation cannot produce a release-eligible score.

### 4.2 Experiment identity and status

Record source revision, dirty-tree status, contract hash, dependency lock hash, generator configuration, all artifact hashes, seeds, hardware, thread settings, elapsed time, peak memory, and raw evaluator logs. Dirty-tree experiments are allowed during development but cannot become releases without a frozen source revision.

Use explicit build/verification states: `draft`, `numerically_feasible`, `circuit_smoke_passed`, `full_local_passed`, `release_selected`, `remote_accepted`, and `rejected`. Record independent confirmation separately as `not_run`, `passed`, `failed`, or `consumed_for_tuning`, bound to the frozen artifact hashes and protocol. `release_selected` requires applicable confirmation to pass as well as the complete local verifier. A candidate cannot skip required states. A configuration without serialized artifacts cannot claim full verification. Changed bytes invalidate evidence for those bytes; a changed contract invalidates affected comparisons. Confirmation used to tune a candidate is consumed and cannot confirm its replacement.

Start with JSON records and a CSV comparison index. Add a database only if volume makes the file-based approach inadequate.

## 5. G0 — Freeze the contract and establish executable baselines

**Original provisional estimate: 3–5 person-days; not re-estimated for v2 additions. Dependencies: access to official assets.**

| Task | Implementation work | Deliverable / acceptance |
|---|---|---|
| G0.1 Acquire assets | Download rules, Data/Evaluation pages, full metric notebook, starter kit, reference ZIP, paper v2, relevant source revisions | `sources.lock.json` with filenames, origin, version, acquisition date, SHA-256, and redistribution status |
| G0.2 Pin environment | Select supported Python/toolchain from the actual packages; lock numerical libraries and kickmix revision; capture compiler/OS | Fresh installation loads all reference artifacts and runs a tiny circuit |
| G0.3 Extract executable contract | Inspect registers, gates, schemas, endian rules, phase units/wrapping, initialization/composition assumptions, scoring edge cases, sampling, and rejection conditions | `contract.json`, scoped correctness claims, schema validators, per-field provenance; zero unresolved release-critical fields |
| G0.4 Run unmodified references | Evaluate the original ZIP without converting or regenerating it first; preserve raw diagnostics | Per-task validity and cost; expected score normalization reconciled with 1.0 |
| G0.5 Resolve chemistry ambiguity | Compare observed acceptance with the paper's contradictory baseline statements | Written resolution or precise upstream issue; no assumption that a new factorization is required |
| G0.6 Profile execution and cost | Measure parse/build/runtime/RAM and component gates/peak live workspace; include chemistry modeled components and complete official objectives | Baseline component profiles, resource budget, and a measured full-run feasibility decision |
| G0.7 Preserve fallback | Store immutable original ZIP and component hashes; document retrieval | Retained components demonstrably match the accepted local reference bytes |
| G0.8 Establish negative controls | Construct small independently known-invalid fixtures for schema, phase, registers, cleanup, numerical bounds, and archive checks | Expected-versus-observed diagnostics for each enabled check; distinguish malformed input from invalid circuit/numerics |

Normalize score using the official reference quantities; do not force a failed or discrepant run to 1.0 by redefining the baseline. Any allowed numerical tolerance must come from pinned evaluator behavior or explicit documented analysis.

The discrepancy register must at least cover chemistry baseline validity, full chemistry cost, residual conventions, array shapes/dtypes, angle units, DQI classical-record interface, fine-rotation pricing, serialization/hash semantics, and actual runtime/submission limits. Also record whether submissions are currently open; the research timestamp is not evidence of current availability.

**G0 exit:** all release-critical contract questions resolved, full unmodified local reference accepted, component profiles archived, targeted negative controls fail for the intended reason, correctness scope declared, and toolchain install reproducible. An accepted reference is only a positive control; it cannot show that every validator is active. If official metric assets are unavailable, mathematical scaffolding may proceed, but G0 remains blocked and all compatibility claims remain provisional.

## 6. G1 — Independent reference and validation layer

**Original provisional estimate: 8–12 person-days: inverse square root 2; DQI 3–4; chemistry 3–5; integration contingency 0–1. Added v2 checks require re-estimation.**

### 6.1 Inverse-square-root reference

1. Reproduce the exact integer-derived ideal phase and circular comparison, including the verifier's quantization and rounding.
2. Add a high-precision independent sanity check on selected inputs. Ordinary floating-point `1/sqrt(x)` alone is not the acceptance oracle.
3. Define a candidate fixed-point evaluator with explicit intermediate widths, signedness, rounding, overflow, and truncation at every operation.
4. Implement a chunked full-domain scan that reports the minimum margin, maximum error, worst inputs, and a histogram of margins.
5. Freeze fixtures for endpoints, powers of two and neighbors, normalization transitions, interval boundaries, rounding ties, and worst discovered cases.
6. Implement and independently check the rotation-price fixtures from §3.1, including units, zero rotations, invalid margins, and no double-counting.

**Acceptance:** exact target-phase and rotation-price agreement with the official implementation on boundary and randomized fixtures; known-invalid phase and overflow cases fail for the intended reason; full-domain enumeration has no omissions or duplicate-only coverage. Retain high-precision fixture provenance and margin in both turns and fixed-point units.

### 6.2 DQI reference

1. Implement transparent carryless polynomial multiplication and reduction for the Kaggle modulus.
2. Implement a separate optimized classical field backend and generate fixed multiplication/squaring maps from the modulus.
3. Implement the official syndrome convention and a classical EEA decoder as a control.
4. Add exact classical BM with root finding and error recovery, independent enough to detect EEA/convention discrepancies.
5. Generate deterministic errors across every weight 0–35 and verify syndrome, decoded error, and parity under multiple masks.
6. Reproduce the official score statistic using numerically stable tail calculations and a high-precision cross-check.

**Acceptance:** exhaustive unary field tests over all 4,096 values where defined; all 4,095 nonzero inverses correct; fixed maps agree on all inputs; randomized multiplication and decoding agree across independent implementations. Include zero syndrome, single errors at positions 0 and 4094, all supported weights, and multiple masks for the same syndrome. Division by zero has an explicit tested contract. Extreme-tail confidence and near-cutoff repetition-factor fixtures must pass independent high-precision checks and reconcile with the pinned scorer before G1 closes.

### 6.3 Chemistry reference

1. Read and validate all official arrays using actual schema conventions and finite-value checks.
2. Validate a rooted, ordered spanning tree: valid vertices, no cycles, correct edge count, connectivity, root and parent-before-child rules.
3. Decode actual oracle words and reconstruct vectors by the ordered Givens operations.
4. Rebuild candidate tensors using fixed symmetry values and official one-electron matching.
5. Independently calculate residuals, `Λ`, `E_SOS`, gap, and `λ_eff`.
6. Reconcile all modeled `T_tot` and `Q_tot` terms against the official scorer, exposing a component-by-component breakdown.
7. Establish legal deterministic sign/order, zero-component, and angle rounding/wrap conventions; test near-zero components and nearly degenerate eigenspaces as specified in §9.5.

**Acceptance:** reference residuals and cost terms agree within explicitly justified numerical tolerances; representation, perturbation, and rounding fixtures pass under the official matching convention. Known-invalid tree order, words, symmetry data, or energy conventions fail the intended check; a legal representation change is not automatically invalid. Large tensor computations are blocked/chunked if needed; a small-instance dense calculation validates the memory-saving implementation.

### 6.4 Scope reduction for the first release

The original 27–41 person-day range includes full G1 but has not been re-estimated for v2 additions. A narrower first implementation can concentrate independent development on the selected benchmark while retaining full official validation of untouched components. Document omitted independent checks and re-estimate effort before adopting that scope. Retain all applicable new correctness, confirmation, and release checks; never weaken verification to fit the old schedule.

### 6.5 Bounded opportunity screen

After G0 and the relevant G1 checks, run a small complete-cost prototype for each seriously considered workstream. This is a required decision gate before major circuit construction, a broad parameter sweep, or a compression compiler. It does not require prototyping all three workstreams.

Before each prototype, register maximum engineer time, compute, experiment count, minimum worthwhile gain, and explicit stop criteria using G0 measurements and available resources. No numeric budget or gain is assumed to fit the original person-day ranges. Retain unsuccessful evidence and the accepted reference.

| Workstream | Prototype/profile coverage | Go/no-go evidence |
|---|---|---|
| Inverse square root | Normalization, lookup, arithmetic, phase rotations, cleanup, and peak live workspace | Numerically feasible prototype with complete official `QC` and margin-aware rotation price before the broad sweep |
| DQI | Locator generation, Chien search, symbol recovery, variable-mask phase extraction, cleanup, and peak live workspace | Bounded Kaggle-field/random-mask compatibility and cost prototype before the full reversible BM build; no locator-only gain extrapolation |
| Chemistry | Normalization, angle lookup, modeled state preparation and Givens costs; table/delta repetition; representation stability; small compiled lookup variants | Evidence choosing lookup-only or factorization work; include full modeled objective without inventing standalone submitted circuits for modeled components |

Record component counts, measured build/evaluation time and memory, numerical margins, the complete objective, and unresolved extrapolation assumptions. Stop or redirect when compatibility fails, feasibility is absent, or full cost shows no credible gain. Re-estimate the selected path after the screen, explicitly pricing added verification and compute; reduce optional experiments or revise the schedule rather than dropping required checks.

## 7. G2 — Inverse-square-root optimization

**Original provisional estimate: 10–16 person-days; task splits below require re-estimation for v2. Start after G0, the relevant G1 checks, and the bounded opportunity screen pass.**

| Task | Original provisional effort | Work and concrete output |
|---|---:|---|
| G2.1 Reference decomposition | 2–3 pd | Separate normalization, lookup, polynomial, Newton, scaling, phase, and cleanup costs; reproduce reported counts or explain differences |
| G2.2 Exhaustive candidate harness | 1–2 pd | Connect each candidate's exact finite-width arithmetic to G1's full-domain oracle; emit feasibility and margin records |
| G2.3 Approximation search | 3–5 pd | Compare baseline cubic+Newton, fewer-coefficient polynomial, normalized affine, and table/affine correction families |
| G2.4 Phase/resource optimization | 2–3 pd | Compare accumulator versus direct phase; optimize using the full remaining-margin rotation price and fixtures in §3.1; test reverse versus measurement-based cleanup |
| G2.5 Circuit integration | 2–3 pd | Generate kickmix, validate register/ancilla behavior, run full local verification, and select a cost improvement |

### 7.1 Search protocol

For each family, define normalization, index bits, local-coordinate bits, coefficient widths, intermediate widths, rounding, zero or one Newton step, lookup scheme, and phase construction. Fit coefficients against actual finite-input and fixed-point semantics. A real-valued fit is only a starting point.

Use this promotion order:

1. Boundary checks and a representative numerical sample.
2. Exhaustive scan over all 3,133,452 inputs.
3. Static resource estimate with all assumptions recorded.
4. Circuit generation and primitive/sampled trajectory checks.
5. Official resource accounting, including rotation charges.
6. Full official-strength local verification on the frozen artifact.

Define numerical margin `m(x)=2^-24/sqrt(x)-abs(circular_phase_error(x))`. Require strictly positive minimum numerical margin as an internal engineering gate, even though the reported official inequality permits equality. This margin does not replace the official rotation synthesis calculation or complete trajectory checks.

### 7.2 Feasibility experiment for affine approximation

The report's simple 128-interval affine proposal already has a continuous-domain diagnostic error much larger than the requested tolerance. Do not budget its published related-task gain as a likely Kaggle gain. Test the actual normalized discrete domain and fixed-point calculation first. If it fails, record the failure boundary and move to more intervals, nonuniform intervals, higher degree, or a correction step within the search budget.

Set the affine feasibility timebox in the opportunity-screen protocol using measured throughput and revised scope. The earlier 1–2 person-day suggestion was not a measured budget and is not a commitment under v2. Stop that family when it lacks a plausible accuracy/cost tradeoff; do not synthesize an invalid approximation merely because its arithmetic is cheap.

### 7.3 Circuit requirements

- Preserve `x` exactly and clean every workspace wire on all tested trajectories.
- Treat overflow and truncation as explicit arithmetic behavior, not implementation accidents.
- Account for normalization and scale restoration, including odd/even exponent transitions.
- Verify branch-dependent phase corrections for measurement-based cleanup.
- Test the deserialized canonical artifact, not only the in-memory builder graph.
- Record `Q`, Toffoli/T counts, fine-rotation inventory and allocated error, official `C`, `QC`, margin in turns/fixed-point units, runtime, fixture results, and hashes.

**G2 exit:** lower official `QC` than the accepted reference under the same metric, all inputs numerically feasible, rotation-price fixtures passing, scoped primitive evidence recorded, and zero failures across 200,540,928 required local trajectories. Independently confirm selected frozen bytes before release as specified in T2-confirm. A cheaper estimate or a passing numerical model alone does not pass G2.

If no candidate improves, retain the reference and close G2 with measured results. Reassess DQI or chemistry based on actual opportunity and remaining budget; do not silently extend the entire research program.

## 8. G3 — Kaggle-compatible Berlekamp–Massey DQI

**Original provisional estimate: 22–35 person-days; task splits below require re-estimation for v2. Optional for the first release; the bounded random-mask/cleanup prototype must pass before the full BM build.**

| Task | Original provisional effort | Work and acceptance |
|---|---:|---|
| G3.1 Reversible field arithmetic | 3–5 pd | Generate multiplication/squaring/fixed maps for the Kaggle modulus; compare circuit results with independent polynomial arithmetic |
| G3.2 Exact classical BM | 2–3 pd | Differential tests against EEA, including discrepancy-zero updates and weight 35; reuse G1 fixtures, extend for circuit scheduling |
| G3.3 Reversible locator | 6–9 pd | Implement full exact recurrence; retain or recompute history explicitly; restore inputs/workspace |
| G3.4 Variable-mask phase recovery | 4–7 pd | Chien/root and magnitude processing under exact conventions; accumulate required parity using the supplied `c` |
| G3.5 Workspace and cleanup | 3–5 pd | Recompute versus store, liveness analysis, reciprocal/derivative opportunities, corrected measurement uncomputation |
| G3.6 Explicit approximations | 2–4 pd | Isolated cutoffs/history reductions with known divergence predicates and exact controls |
| G3.7 Confirmation and full score runs | 2 pd, original score-run allowance only | Independently confirm frozen selected bytes; run distinct official-strength 102,400-shot validation; compare full cost; re-estimate confirmation effort/compute |

### 8.1 Adaptation rules

Regenerate all constants, evaluation tables, squaring maps, Chien increments, and Forney conventions from Google's field representation. Changing one polynomial literal in Gu's implementation is insufficient. Record any borrowed architectural idea and its source revision/license; no fixed-mask tables survive into the variable-mask implementation.

Expose `c` through the official classical-record interface established in G0. Do not allocate 49,140 quantum wires merely because the record has that many bits, and do not infer the classical binding API from the report alone.

The full exact decoder is the control. First implement a straightforward correct parity path; then examine reciprocal-polynomial/direct-phase methods. Do not materialize a full decoded quantum error vector unless profiling establishes a need. Classical test references may reconstruct the full error to validate the parity circuit.

BM is a promising architectural lead, not an established Kaggle improvement. Profile the complete path again when its locator changes because the bottleneck can move. Parity-only computation is already in scope. Soft-decoder alternatives remain optional leads until they demonstrate compatibility with the same fixed syndrome input, required phase, and verifier distribution; changing the task is not an optimization.

### 8.2 Required test dimensions

For every tested error, vary both the error and mask. Include zero and all-one masks, selected single-bit masks, and independent random masks. Test several masks for the same syndrome to detect accidental fixed-mask specialization. Add `p(c1 XOR c2)=p(c1) XOR p(c2)` as a metamorphic check of parity behavior.

Exercise weights 0–35 independently of their score distribution. Include maximum weight, endpoint positions, multiple field symbols, locator degree transitions, zero discrepancies, and controlled division-by-zero paths. Test exact implementations on the supported domain; behavior outside that domain is not a substitute for the official contract.

Every circuit test checks phase, preserved syndrome, and clean workspace. A decoder that returns the correct classical error but leaves garbage is not a valid circuit.

### 8.3 Stable statistical scoring

Let `δ=2^-128`. For `k<N`, solve

\[
\Pr_{p=\epsilon^+}[\operatorname{Binomial}(N,p)\le k]=\delta.
\]

Keep `δ` directly. Use an independently checked beta upper-tail inversion such as `beta.isf(δ, k+1, N-k)`, or a stable log-domain solution of the binomial lower-tail equation. Computing `1-δ` in binary64 yields exactly 1; do not feed that rounded confidence into an inverse CDF. A library's inverse-survival API is not by itself an accuracy certificate: pin the numerical backend and cross-check extreme-tail outputs independently. For `k=0`, use `-expm1(log(δ)/N)`; for `k=N`, set the upper bound to 1 and reject as non-finite-cost.

At `N=102400`, the zero-failure fixture is `ε⁺=0.0008660587301657926` and `R=1.1912604648115832`. Test zero, small positive, moderate, cutoff-adjacent, and all-failure counts, plus monotonicity and independently checked high-precision agreement. Reject invalid/non-finite inputs and counts outside `0<=k<=N` with positive integer `N`. Use a stable logarithm for `R` near the cutoff and test sensitivity there. Reconcile official rounding/tolerances; never silently substitute a locally corrected solver for an official discrepancy—record and resolve it in G0. Do not replace `ε⁺` with `k/N`.

### 8.4 Selection, independent confirmation, and failure categories

Keep `exact` and each explicitly named approximation as separate configurations. For each pruning rule, log where it diverges from the exact algorithm and whether the divergence changes phase or cleanup. Unknown failures in the supposedly exact circuit are bugs, not an approximation budget.

Use common syndrome/mask fixtures for paired development comparisons, with recorded measurement seeds and distributions. Stratified weight stress tests are diagnostics; their unweighted failure rate is not an estimate under the official distribution. Store all attempted candidates and failures.

After selection, freeze the candidate bytes and evaluate an independent, previously unused confirmation sample drawn from the prescribed distribution. Register its sample size, confidence procedure, seeds, acceptance/stop rule, and compute allowance before seeing results. Keep development, confirmation, and the official hash-seeded `N=102400` run in separate records. Confirmation must not replace or be pooled silently into the official run. Retained unchanged reference components can cite their original acceptance evidence and full release revalidation; independently confirm newly selected optimized artifacts under their applicable contract, with the explicit statistical procedure here required for DQI.

Confirmation used to tune a candidate becomes development evidence. A failed confirmation reopens development and blocks release; any revised artifact must be frozen and confirmed on new unused data. Do not repeatedly sample unchanged bytes until one favorable result passes. Preserve failed runs and follow the registered stopping rule.

Do not claim a modest sweep automatically invalidates confidence `1-2^-128`. For `M` fixed valid tests, a union bound uses `Mδ`; adaptive data reuse needs separate analysis. The practical purposes of this protocol are stable ranking, auditable experiments, and detecting development overfitting. It does not change Kaggle's scorer or reveal the hidden salt.

Log **decoder disagreement**, **wrong phase**, **named-register corruption**, and **dirty workspace** separately. Preserve overlapping diagnostic labels while counting each failed trajectory once according to the official event. For a mask-independent decoded error with nonzero error-vector difference `d`, a uniform mask has `Pr[c·d=1]=1/2`. Thus decoder disagreement is not the same as the scored failure rate. Do not apply this factor to mask-dependent logic or other failure categories; compute the official bound from the actual trajectory-failure event.

Do not vary semantically irrelevant circuit bytes to seek a favorable challenge stream. Repeated validation seeds estimate stability; they are not a way to cherry-pick the smallest `k`. Reserve any additional robustness runs inside the measured compute budget, and distinguish pooled diagnostic counts from the official `N=102,400` statistic.

**G3 exit:** the exact-algorithm branch has zero observed failures in full local verification and independent checks, recorded as sampled circuit acceptance. A replacement must improve `R(ε⁺)Q²T`, pass the registered independent confirmation, and retain stable-solver/high-precision evidence plus failure categories. An approximate replacement additionally needs explicit approximation provenance and finite penalized cost. Zero observed failures does not prove implementation exactness on every syndrome, measurement branch, or arbitrary quantum input.

## 9. G4 — Chemistry factorization and angle-oracle co-design

**Original provisional estimate: 30–50 person-days, excluding optimizer compute; task splits below require re-estimation for v2. Optional for the first release.**

| Task | Original provisional effort | Work and acceptance |
|---|---:|---|
| G4.1 Numerical reproduction | 4–6 pd | Extend G1 into full candidate scoring; reconcile every baseline cost term and numerical convention |
| G4.2 Factorization search | 7–12 pd | Refine valid starting points; search allowed factor parameters/ranks with fixed symmetry; checkpoint continuous candidates |
| G4.3 Stable quantized angle generation | 4–6 pd | Apply legal deterministic sign/order/zero-component policies; extract/encode angles; reconstruct immediately; retain rounding and perturbation diagnostics |
| G4.4 Tree search | 3–5 pd | Compare allowed line, balanced, and data-driven ordered trees; regenerate angles and costs for each |
| G4.5 Batch and precision search | 3–5 pd | Explore `β,J` near feasible boundaries; account for partial final batches and every workspace wire |
| G4.6 QROM compiler | 6–10 pd | Compare straightforward unary lookup with repeated words/subtrees, deltas, and feasible banked/SelectSwap variants |
| G4.7 Integrated validation | 3–6 pd | Verify actual circuits, reconstruct tensors, compute full cost, and establish regression evidence |

### 9.1 Low-risk entry before a new factorization

If the supplied factorization passes, first hold its represented angle table and tree fixed and optimize lookup implementation. This isolates circuit savings from numerical factorization changes. A byte-different circuit still requires fresh verification, but equivalent output words should reproduce the same numerical tensors.

Before investing in factorization search or a compression compiler, pass §6.5's component-cost and representation-stability prototype. Measure angle/delta repetition and small compiled lookup variants; the measured full objective must justify the selected work. A table that appears repetitive does not alone establish a resource gain under the width and modeled-cost constraints.

Do not assume the baseline is invalid because one passage in the paper warns about accuracy. Conversely, do not assume it passes because another passage says so. G0's measured result controls the starting point.

### 9.2 Outer and inner search loops

The outer loop proposes `(R,B,C,Θ)` using only permitted variables. The inner loop chooses `(tree,β,J,QROM architecture)` and evaluates the actual represented problem:

1. Apply the declared legal sign/order and zero-component conventions, then extract angle data for the chosen ordered tree.
2. Quantize using the pinned representation and angular units.
3. Build batch loads and XOR deltas, including final-batch padding rules.
4. Generate angle circuits; obtain their output words for valid addresses.
5. Decode those words and reconstruct all one- and two-body vectors.
6. Form the transformed tensors; compute both shifted/convention-correct residuals.
7. Apply all strict numerical constraints, then compute `λ_eff`.
8. Compute complete modeled `T_tot`, `Q_tot`, and final cost.

A surrogate score may prune the search, but final selection requires exact post-quantization scoring. A lower rank or lower continuous residual alone is not an improvement.

Use the report's suggested `15–17 mHa` residual range as a preferred internal margin where feasible, not an official requirement. Record distance to every boundary: both residual limits, normalization floor, gap floor, upper gap constraint, and circuit width. Keep the official comparisons unchanged.

### 9.3 Angle-circuit correctness

- Validate named registers, target semantics, legal gates, and all widths using the pinned schema.
- Validate every legal vector address; define behavior for unused encoded addresses according to the actual contract rather than guessing.
- Check first load and all consecutive XOR deltas against the intended batch words.
- Check reverse traversal, preserved addresses, zeroed scratch, and corrected phase.
- Include final partial batches, repeated/zero words, sibling order changes, and angle wrap boundaries.
- Count the complete per-circuit width against 128, including selection, target, and workspace as the official implementation defines them.
- Reconstruct tensors from circuit-emitted words, not floating-point pre-quantization vectors or an unverified side table.

### 9.4 Memory and optimizer controls

Benchmark the full tensor computation before broad optimization. Record peak memory per stage; use blockwise contractions or streamed residual accumulation when needed and cross-check against a small dense case. Save optimizer state, RNG state, factor parameters, and the last evaluated quantized candidate so long runs can resume.

Keep continuous optimization reproducibility separate from release reproducibility. The release may consume a frozen, hashed optimized factor checkpoint; it need not rerun a stochastic multi-day search. Both clean release builds must use the same checkpoint and deterministically produce identical NPZ and circuit bytes. Record checkpoint provenance and exact numeric arrays as release inputs.

**G4 exit:** both residuals satisfy the official threshold after oracle-output reconstruction, symmetry values are unchanged, all strict inequalities and finite-value checks pass, all angle circuits fit the width limit, full trajectory checks pass, and complete chemistry cost improves over the accepted reference. Require the legal representation/stability evidence below and independent confirmation of the selected frozen artifact before release.

### 9.5 Representation stability before quantization

Define deterministic sign and ordering policies, explicit zero-component angle conventions, and rounding/wrap rules before tree extraction. A real vector and its negative have the same outer product; consistently permuting factor rows and associated coefficients can preserve a tensor. Neither observation authorizes arbitrary format changes or guarantees identical costs, addresses, one-electron matching, or quantized feasibility.

For each allowed transformation, document which arrays and address mappings change together and why it preserves the intended representation. Reconstruct the entire Hamiltonian from emitted words and rerun all feasibility, matching, and cost checks afterward. Keep `S0` and `β1,0` frozen; legal representation changes do not authorize symmetry-shift optimization.

Separate deterministic canonicalization for rebuilds from optional optimization over equivalent representations. Freeze the canonicalization policy as a release input; changing it creates a new candidate. Lookup-only experiments keep the accepted factors and represented words as controls unless a representation change is explicitly part of the hypothesis.

Required fixtures cover zero and near-zero tree components, sign flips with associated coefficients held consistent, legal coupled permutations, angle rounding ties and wrap boundaries, and small perturbations of nearly degenerate one-electron eigenspaces. Compare reconstructed matrices or invariant subspaces when mathematically appropriate while still passing the official eigenvector matching procedure. Do not require discontinuous eigenvector coordinates or rounded bytes to vary smoothly under perturbation; require documented behavior and valid reconstructed results, or explicit rejection.

Record numerical-library and BLAS/LAPACK/backend identity, thread/reduction settings, transformation provenance, and perturbation size/results. Determinism means identical bytes for identical pinned inputs/environment, not identical bytes for different perturbed inputs. These stability diagnostics are required G1/G4/release evidence, not permission to relax the official tolerance.

## 10. Testing strategy and CI

### 10.1 Test tiers

| Tier | Trigger | Coverage | Exit evidence |
|---|---|---|---|
| T0: static/unit | Every relevant edit/PR | Schema/gates; wrapped phase and rotation price; field identities; stable tail/near-cutoff fixtures; representation/rounding cases; archive and negative controls | Deterministic tests, independent fixture provenance, and expected diagnostics |
| T1: circuit smoke/differential | Relevant circuit changes | Small exhaustive branches plus coherent/algebraic primitive checks; worst inverse-sqrt inputs; DQI stress cases including weight 35; chemistry address/cleanup checks | Scoped register, phase, ancilla, and coherent/branch evidence |
| T2: promotion | Candidate proposed for expensive evaluation | Full inverse-sqrt numerical scan; broader DQI distributions/masks; all chemistry table words and numerical reconstruction | Feasibility record, actual preliminary cost, profile |
| T2-confirm: independent confirmation | Selected optimized bytes frozen; protocol registered | Fresh unused samples under the applicable contract; DQI prescribed-distribution sample with its own size/confidence procedure | Separate confirmation record; failed/consumed confirmation blocks promotion until a revised candidate is freshly confirmed |
| T3: release | Frozen final extracted ZIP | Full official-strength verification of every component, official resource scoring, and confirmation/mutation/stability evidence review | Hash-bound complete local certificate with explicit correctness scope |
| T4: remote | Authorized competition submission | Kaggle evaluation of exact frozen ZIP | Submission identifier, status, score, discrepancies |

Measure CI duration in G0/G1 before imposing runtime targets. Expensive release runs should be explicit jobs, not repeated after every documentation change. A cached result is reusable only for identical relevant artifact, contract, evaluator, test policy, and environment identities; incomplete runs cannot be relabeled as complete.

### 10.2 Full release coverage

| Benchmark | Required release checks |
|---|---|
| Inverse square root | Exhaustive numerical scan; all 3,133,452 inputs × 64 trajectories; zero failures; margin in both units, allocated rotation error and price fixtures; independent confirmation evidence for the selected replacement |
| DQI | Official distribution, fresh per-shot mask, 102,400 shots; actual trajectory-failure count with diagnostic categories; checked CP/`R` and full cost; distinct frozen confirmation record |
| Chemistry | All valid addresses × 64 measurement samples under official traversal semantics; phase/cleanup/words; emitted-word reconstruction; residual/symmetry/energy/width/cost checks; representation stability and applicable frozen confirmation |
| Archive | Correct paths, no duplicates/ambiguous encodings, matching arrays/circuits, safe clean extraction, hashes identical to manifest |

Use the pinned evaluator's actual trajectory enumeration and sampling logic. Sharding/checkpointing may be added only if it preserves test identity, coverage, and aggregate semantics; otherwise run the unmodified full job. Record completed and required counts. A timeout is an incomplete test, not a pass.

### 10.3 Measurement-based uncomputation

For tractable primitives, enumerate all input values and all measurement branches. For large circuits, combine analytical review of correction identities, static scratch-liveness checks, targeted differential tests, and the prescribed sampled trajectories. Enumerating `2^m` branches for a large number of independent measurements is not a viable release requirement.

For newly designed measurement-uncompute primitives, add tractable coherent-state/channel tests or algebraic branch proofs under the declared input and initialization assumptions. Check that corrected branches implement the required phase/register relation when composed, rather than inferring coherent correctness from classical output bits alone. Small coherent tests remain numerical evidence; reserve “proved” for a documented proof. Full production-circuit statevector simulation is not required. Link each primitive's evidence and composition assumptions to the parent circuit contract.

Prefer small reference primitives with documented phase identities over an opaque generic uncomputation framework. A cleanup optimization must demonstrate both classical restoration and phase correction.

### 10.4 Negative and mutation tests

Use independently established defects to demonstrate that intended validators can fail. Record the expected and observed diagnostic, not just a nonzero exit code; distinguish malformed-input rejection from numerical or circuit invalidity.

| Mutation | Expected detector |
|---|---|
| Inject a known nontrivial phase error beyond tolerance on a tested input | Phase mismatch under the wrapped fixed-point comparison |
| Leave an ancilla dirty or change a preserved input bit | Cleanup or named-register invariant failure, respectively |
| Use Gu's field polynomial or reverse symbol bits | Field/syndrome differential tests |
| Ignore varying `c` | Same-syndrome/multiple-mask tests |
| Substitute `k/N` for the CP bound | Zero-failure and cutoff statistic fixtures |
| Alter an angle word or mismatch its associated factor array enough to independently violate a bound | Word-consistency or reconstructed numerical failure |
| Introduce illegal tree order or malformed dimensions | Structural/schema rejection |
| Modify fixed symmetry or omit core energy | Identity and energy-convention checks |
| Set a strict-floor quantity exactly at its boundary | Strict inequality tests |
| Inject NaN/Inf or invalid NPZ dtype/shape | Schema/numerical preflight |
| Add a 129th angle-circuit qubit | Width validator |
| Omit an angle index or add an enclosing ZIP folder | Archive preflight |

Not every phase-bit change exceeds tolerance, and not every angle-bit change invalidates a factorization. A legal sibling ordering with consistently regenerated angles can also remain valid. Choose fixtures with independently justified failing properties; do not require rejection of legal approximations, equivalent representations, or unspecified input behavior. Keep lightweight controls in CI and representative results in each release certificate, without duplicating the validator's own implementation as its oracle.

## 11. G5 — Deterministic release and remote acceptance

**Original provisional estimate: 6–8 person-days; re-estimate for v2 confirmation and evidence requirements. May follow any single improved workstream.**

### 11.1 Release sequence

1. Freeze selected candidate configurations, source revision, contract, evaluator, toolchain, numeric checkpoints, and reference component hashes.
2. Build in clean directory A. Generate chosen components and restore untouched reference bytes from the pinned original distribution.
3. Serialize generated circuits with the pinned canonical `.kmb` writer. Reload them and validate schemas and instructions.
4. Write deterministic NPZ: fixed array/member order, dtypes, byte order, metadata, ZIP timestamps/permissions, and pinned compression settings. Compare whole-file bytes as well as arrays.
5. Repeat the release build independently in clean directory B. Require identical per-file hashes. Do not copy generated artifacts from A to B to simulate a rebuild.
6. Assemble a deterministic ZIP from only required paths. Normalize ordering, timestamps, permissions, and compression settings.
7. Extract into an empty directory. Compare extracted hashes with the release manifest and reject duplicate/traversal paths or ambiguous entries.
8. Require T2-confirm evidence for each selected optimized artifact under the applicable protocol. Run it on the frozen bytes if not already available; if already run, verify identical hashes and that it has not been consumed for tuning. Investigate failed confirmation and reopen development; revised bytes require new unused confirmation data.
9. Run T3 against the extracted files, including retained components. Retain a representative validator-mutation record, primitive correctness scope, and representation-stability evidence. Do not verify one set of bytes and submit another.
10. Compute per-task costs and aggregate score from the pinned metric. Freeze the final ZIP hash and local certificate, with development, confirmation, and official results kept distinct.
11. Submit the exact ZIP when the implementation task includes authorization to submit. Retain submission identifier, remote status, score, and timing. A planning-only request does not itself perform this step.
12. Reconcile remote and local results. On acceptance, append remote evidence without changing the submitted bytes. On failure, preserve the failed release and open a new candidate/release record.

Canonicalization is a pinned serialization procedure, not an invented semantic deduplication algorithm. Preserve unmodified reference bytes unless conversion is required; any conversion creates a new artifact identity and requires verification.

The hidden competition salt prevents exact local reproduction of remote randomized challenges. Record the local seed/salt policy openly in evidence. An unmodified official evaluator run with a development seed is still a local test, not proof of remote acceptance.

### 11.2 Release certificate contents

| Section | Required fields |
|---|---|
| Identity | Source/contract/metric/toolchain hashes; checkpoint hashes; numerical libraries and BLAS/LAPACK/backend identity; hardware/thread settings |
| Correctness scope | Valid inputs, initialization, measurements, composition assumptions; exact-algorithm intent, proved primitive claims and sampled acceptance clearly distinguished |
| Opportunity decision | Component-cost/runtime/workspace profiles; registered prototype budget and go/no-go result; selected-path re-estimate |
| Validator evidence | Representative known-invalid mutations with expected and observed diagnostics and independent defect justification |
| Candidate selection | All development attempts; frozen hashes; confirmation protocol/sample size/distribution/confidence/seeds/results; failed or consumed confirmation history |
| Build | Two-build comparison; serializer identity; per-file hashes; NPZ byte comparison; generated/reference provenance |
| Inverse square root | `Q`, gate/fine-rotation counts, allocated rotation error, price fixtures, official `C`, `QC`, minimum margin in turns and fixed-point units, coverage and failures |
| DQI | `Q`, `T`, official `N,k,ε⁺,R,RQ²T`; solver and high-precision fixtures; failure categories; separate confirmation `N,k` and sampling/confidence record; exact-algorithm/approximate designation |
| Chemistry | Residuals, fixed-symmetry hashes, `Λ`, `E_SOS`, core-inclusive `E_upper`, gap, `λ_eff`, `Q_tot`, `T_tot`, cost, max angle width, coverage, legal representation conventions and perturbation/rounding record |
| Packaging | Expected/actual file list, extraction check, final ZIP SHA-256, raw verifier log hashes |
| Result | Local gate status; predicted aggregate score; remote submission identifier, acceptance and score if available |

Missing data is recorded as missing, never as a zero-valued passing placeholder. Preserve actual failures and unfinished jobs. A certificate claiming `remote_accepted` must contain remote evidence.

### 11.3 Proposed operator commands

These commands are a CLI implementation target. They are not available until the project is built, and official backend calls remain subject to G0 discovery.

```bash
uv sync --frozen
uv run qcompile contract validate --contract contracts/contract.json
uv run qcompile baseline verify --tier full
uv run qcompile test --tier unit
uv run qcompile experiment run --config configs/invsqrt-initial.yaml
uv run qcompile candidate verify --id CANDIDATE_ID --tier promotion
uv run qcompile candidate confirm --id CANDIDATE_ID --protocol configs/confirmation.yaml
uv run qcompile release build --selection configs/release.yaml
uv run qcompile release verify --release RELEASE_ID --tier full
```

The normal release command builds and verifies locally. A remote-submit command, if implemented later, is explicit and separate so local testing cannot accidentally upload exploratory artifacts.

## 12. Experiment budgets and promotion decisions

Before each opportunity prototype and later search, record its hypothesis, parameter ranges, correctness conditions, official objective, engineering timebox, maximum compute, experiment count, minimum worthwhile gain, and stopping rule. Set numeric limits after G0 profiling and re-estimate the selected scope after the screen; do not infer affordability from a published throughput headline. Include independent confirmation and stability checks explicitly rather than treating them as free additions.

| Workstream | Primary decision quantity | Preserve alongside it | Stop or redirect when |
|---|---|---|---|
| Inverse square root | Official `QC` | Margin, rotation cost, runtime, workspace | Family cannot meet accuracy, or validated cost loses to reference |
| DQI | Official `R(ε⁺)Q²T` | Exact control, mask/weight coverage, failure stability | Exact correctness unresolved, penalty erases savings, or cutoff approached |
| Chemistry | Official `λ_eff T_tot Q_tot` | Residual/gap margins, maximum angle width, reconstruction cost | Quantization destroys feasibility, width exceeds limit, or modeled cost loses |

Retain a small nondominated set rather than selecting by a single intermediate measure such as Toffoli count, factorization rank, or continuous residual. Set the finalist/experiment limit from measured cost before the search; the earlier five-finalist suggestion is not a measured budget. Any expansion requires a documented reason and revised budget. These controls do not alter competition rules.

Prefer a clearly measured improvement with healthy numerical/statistical margins over a marginal change whose apparent gain depends on rounding or favorable local samples. Any chosen minimum improvement threshold must be set before finalist evaluation and tied to measurement precision and validation risk; no arbitrary percentage is an official requirement.

## 13. Hardware and execution feasibility

Use a CPU-first development path. The task is classical verification and reversible-circuit compilation; the plan does not require an NPU or GPU. GPU acceleration may become useful for a particular chemistry optimizer, but only after supported tooling and profiling justify it.

For a 16 GB development machine, begin with contract extraction, unit tests, field arithmetic, chunked inverse-sqrt scans, and small circuit smoke tests. Establish actual RAM usage before attempting full chemistry tensor work or long release jobs. Do not promise that the entire program fits that machine. If larger compute is needed, record a measured minimum environment and prepare a portable locked execution bundle; acquiring paid compute is a separate decision.

Docker is optional. A locked native environment can establish reproducibility; a container image digest is additional evidence when available. Cross-platform byte identity is desirable but must be demonstrated rather than assumed. Choose a canonical release environment and verify two clean builds there first; use other platforms as portability tests.

Record wall time, CPU time, peak resident memory, disk use, and throughput by stage. Long runs should emit progress and resumable evidence where supported. Distinguish an execution checkpoint from a completed verification result.

## 14. Schedule and work packages

### 14.1 Original effort ranges and required re-estimation

| Stage | Original provisional person-days | Earliest dependency |
|---|---:|---|
| G0 | 3–5 | Official assets accessible |
| G1 | 8–12 | Resolved relevant G0 contracts |
| G2 | 10–16 | G0 + inverse-sqrt reference + bounded opportunity screen |
| G3 | 22–35 | G0 + DQI reference + random-mask/cleanup prototype |
| G4 | 30–50 | G0 + chemistry reference + cost/stability prototype |
| G5 | 6–8 | One selected improvement plus valid references for other tasks |
| **Original full program** | **79–126** | All optimization workstreams; v2 scope not re-estimated |
| **Original first release through G2** | **27–41** | G0 + full G1 + G2 + G5; v2 scope not re-estimated |

These totals included the original verification/regression work but have not been re-estimated for all v2 requirements. They are historical arithmetic totals, not a funded or measured schedule for this revision. After G0 and the opportunity screen, publish a selected-path estimate separating original tasks, added numerical/confirmation/stability/negative-control work, compute and access delays, and optional experiments. Avoid double-counting existing checks, but do not assume additions are covered. If the revised scope exceeds available effort, drop optional experiments or revise the schedule; preserve required verification.

For one engineer, execute one optimization stream at a time. For a larger team, separation is possible after contracts are frozen, but the shared evaluator and release owner must prevent incompatible versions. This plan does not assume a team exists.

### 14.2 Original first-ten-day sequence: sequencing reference only

| Window | Intended work | Reviewable output |
|---|---|---|
| Days 1–2 | Acquire official assets; create locks; install/load toolchain | Source inventory, environment lock, unresolved-contract list |
| Days 3–5 | Contract/claim scope; references; chemistry/accounting discrepancy; component profiling and negative controls | G0 evidence or a concrete blocker report |
| Days 6–7 | Inverse-sqrt exact phase oracle, rotation-price and scan fixtures | Independent target-phase/price tests and harness |
| Days 8–10 | DQI field/statistical fixtures and chemistry representation/reconstruction according to selected G1 scope | Independent checks and initial reconciliation results |

These windows preserve the original sequencing aid only; they are not re-estimated durations for the expanded work. Full G1 and the bounded opportunity screen may extend beyond them. Do not start broad synthesis/search before the relevant contract, checks, and screen pass. Replace these windows with measured selected-path scheduling at the re-estimation gate.

### 14.3 Suggested implementation issue sequence

1. `CONTRACT-01`: asset acquisition, immutable provenance, source discrepancy register, valid-input/initialization/composition assumptions and correctness labels.
2. `TOOLCHAIN-01`: locked install, backend adapter, tiny-circuit smoke and profiling.
3. `BASELINE-01`: original-archive evaluation, component profiles, normalization reconciliation, known-invalid controls with expected diagnostics.
4. `ORACLE-INV-01`: integer phase target, circular comparison, full rotation price/edge fixtures, exhaustive scan.
5. `ORACLE-DQI-01`: field, syndrome, independent decoders, extreme-tail and near-cutoff high-precision fixtures, failure categories.
6. `ORACLE-CHEM-01`: emitted-word reconstruction, shifted residuals, full accounting, legal representation and degeneracy/rounding fixtures.
7. `ARTIFACT-01`: candidate identity, deterministic serialization, manifests, safe packaging.
8. `OPPORTUNITY-01`: registered time/compute/experiment/gain limits; complete-cost prototypes; go/no-go decision; selected-path re-estimate before major work.
9. `INV-SEARCH-01`: numerically feasible search across four families after the screen.
10. `INV-CIRCUIT-01`: synthesize feasible finalists, optimize full rotation/workspace costs, and document coherent/algebraic cleanup evidence.
11. `CONFIRM-01`: freeze selected artifact bytes; independent unused confirmation; separate records and failed/consumed-data handling.
12. `RELEASE-01`: two builds, extracted-archive validation, scoped certificate with confirmation/mutation/stability evidence, submission handoff.
13. `DQI-BM-01` and later DQI issues only after the optional random-mask/cleanup prototype passes.
14. `CHEM-QROM-01` and later co-design issues only after the optional cost/stability prototype justifies them.

Each issue must name its gate, inputs, output artifacts, tests, and reason for acceptance or rejection. Shared artifact/release infrastructure can be developed during G1/G2 rather than deferred until the end.

## 15. Risk register and explicit fallback behavior

| Risk | Detection | Response / fallback |
|---|---|---|
| Official metric unavailable or package/rules disagree | G0 provenance and baseline reproduction | Block compatibility claims; continue only independent scaffolding |
| Reference chemistry rejected | Unmodified archive evaluation | Resolve exact cause; no complete-release fallback until valid chemistry exists |
| Wrong DQI field or position convention | Independent polynomial and syndrome fixtures | Regenerate all constants; reject imported tables |
| Fixed-mask specialization | Same syndrome with multiple masks | Replace phase extraction; retain exact classical control |
| Adaptive DQI comparison or reused confirmation misleads selection | Common development fixtures; fresh frozen confirmation; separate official result | Reopen development on failed confirmation; revised candidate needs unused data; do not tune byte encoding to challenge stream |
| Extreme-tail solver or cutoff logarithm is unstable | High-precision zero/small/cutoff/all-failure fixtures and monotonicity | Use checked tail/log methods, reject invalid inputs, resolve official discrepancies rather than silently overriding them |
| Decoder disagreement confused with scored failure | Separate phase/register/workspace and decoder diagnostics | Count actual failed trajectories once; apply the half-probability identity only to mask-independent wrong-vector decoding |
| Wrong optimization priority | Complete component profiles and bounded prototypes | Stop/redirect if random-mask, cleanup, rotations, or modeled costs erase gain; re-estimate scope |
| Inverse-sqrt approximation cannot meet tolerance | Exhaustive finite-width scan | Stop family before synthesis; try higher-degree/correction or retain reference |
| Fine rotations erase arithmetic savings | Margin allocation and official `C` fixtures in turns/fixed-point units | Price equal allocation correctly; no clipping/double-counting; optimize full cost or reject |
| Factorization fails after quantization | Reconstruct actual oracle outputs | Increase precision/change representation; preserve valid baseline |
| Chemistry signs/order/degeneracy change words or feasibility | Legal canonicalization, backend identity, perturbation/rounding diagnostics | Freeze policies; recheck full Hamiltonian, matching and cost after every transformation; keep symmetry fixed |
| Chemistry cost incorrectly capped or incomplete | Component-by-component accounting | Use full model; reject proxy-only promotion |
| Measurement cleanup produces hidden phase/garbage | Primitive branch tests and full trajectories | Use validated reverse cleanup until correction logic is established |
| Sampled acceptance overstated as a coherent/worst-case proof | Claim labels, input-state assumptions, small coherent tests or branch proofs | Narrow the claim to actual evidence; require documented primitive composition assumptions |
| Validator accepts known defects or rejects legal variations | Independently justified negative controls and diagnostic checks | Repair intended checks; distinguish schema from circuit/numerical failure; do not demand rejection of legal approximations |
| Build nondeterminism | Two clean builds and byte hashes | Freeze numeric inputs/toolchain; deterministic archive writer |
| Full validation exceeds available resources | Early profiling and completion counters | Move to measured suitable environment or remain blocked; no reduced-test release claim |
| Remote differs from local | Retained exact ZIP and raw diagnostics | Investigate seed/version/contract difference; preserve failed release evidence |
| Research yields no improvement | Budgeted promotion decisions | Publish measured negative results internally; keep valid references; reassess next workstream |

## 16. Final definition of done

The first improved release is complete only when:

- [ ] Official contract and evaluator versions are pinned and reconciled.
- [ ] Unmodified references have reproducible local acceptance and documented normalization.
- [ ] Baseline component profiles, bounded opportunity decision, and selected-path effort re-estimate are recorded.
- [ ] Independent checks exist for the selected optimization; remaining verification scope is explicit.
- [ ] Correctness claims distinguish exact-algorithm intent, proved primitives, and sampled circuit acceptance with explicit input/initialization/composition assumptions.
- [ ] Applicable high-precision statistical and rotation-price fixtures, coherent/algebraic primitive evidence, and representative validator negative controls pass.
- [ ] Selected optimized artifact bytes have independent confirmation under the registered protocol; failed or tuning-consumed confirmation is not reused.
- [ ] Chemistry representation conventions, backend identity, and rounding/degeneracy stability evidence are retained for the relevant representation path.
- [ ] At least one chosen component improves its complete official objective.
- [ ] Every submitted component passes all applicable full-strength local checks.
- [ ] Two clean release builds produce identical required file bytes and deterministic ZIP bytes.
- [ ] The extracted final archive, not merely the source artifacts, has been verified.
- [ ] The certificate contains complete counts, hashes, costs, numerical margins, and statistical quantities.
- [ ] The exact frozen ZIP has remote acceptance evidence and an aggregate score above the official reference.

If the final item is unavailable, describe the result as **locally verified, awaiting Kaggle acceptance**, not complete remote success. If no benchmark improves, describe it as a reproducible baseline or a completed experiment, not an improved submission.

## 17. Source mapping and follow-up verification

This plan is derived from the supplied `deep-research-report-v2.md` revision of 27 October 2026, not a new web audit. Its content hash is recorded at the top. External URLs below are discovery pointers reproduced from that report; obtain and pin their contents and versions in G0 before they control implementation. The report's literature review is research evidence, not execution or baseline acceptance evidence.

| Plan area | Source-report section |
|---|---|
| Contracts and archive | “Competition specification, verifier, data, and submission contract” |
| Inverse-square-root tasks | “Inverse square root”; “Inverse-square-root experiments” |
| DQI adaptation/statistics | “DQI / Reed–Solomon syndrome decoder”; “DQI experiments” |
| Chemistry constraints/co-design | “DFTHC chemistry factorization and angle oracles”; “Chemistry experiments” |
| Gates and estimates | “Prioritized implementation roadmap”; “Conclusions and recommended research strategy” |
| Reproducibility/release | “CI and reproducibility checklist”; “Minimum release certificate” |
| Remaining unknowns | “Durable source index and unresolved execution checks” |

### 17.1 V2 correction traceability

| V2 report addition | Implemented plan requirement | Required evidence / gate |
|---|---|---|
| Scope of a correctness certificate | §3 contract assumptions; §10.3 coherent/algebraic primitive checks; §11.2 scoped claims | G0/G1 declarations, primitive proof/test references, release claim labels |
| Executable phase-margin and rotation-cost contract | §3.1 formulas, units, zero-rotation branch, invalid-margin handling; §6.1 and G2 fixtures | Independent cost fixtures, official reconciliation, per-candidate margin/allocation record |
| Stable extreme-tail statistics | §8.3 checked beta inverse-survival/log-domain method, stable zero case and cutoff diagnostics | G1 high-precision fixtures and solver identity; distinct official statistic |
| Independent confirmation and failure categories | §8.4 protocol, data-consumption rules and actual trajectory event; T2-confirm | Frozen hashes, unused prescribed-distribution sample, separate development/confirmation/official records |
| Measured priorities and bounded opportunity screen | §6.5 complete-cost prototypes; G2/G3/G4 prerequisites; §12 experiment limits | Component profiles, registered limits, go/no-go decision before major investment |
| Chemistry representation stability | §6.3 and §9.5 legal sign/order conventions, degeneracy/rounding tests, backend identity | Invariant/matching checks plus complete reconstruction/feasibility/cost after changes |
| Validator negative controls | G0.8, G1 checks, §10.4 justified mutations and diagnostics | Known-invalid fixtures fail for the intended reason; legal approximations remain allowed |
| Expanded release evidence and provisional effort | §11.2 certificate; §14 revised-estimate gate; §16 checklist | Confirmation/mutation/stability evidence and a new selected-path estimate; original ranges explicitly historical |

G0 source acquisition list:

- [Kaggle competition overview](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/overview)
- [Kaggle competition data](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/data)
- [Google companion paper v2](https://arxiv.org/abs/2610.23832v2)
- [Qualtran / kickmix repository](https://github.com/quantumlib/Qualtran)
- [Gu et al. paper](https://arxiv.org/abs/2610.22367)
- [Gu et al. released circuits](https://github.com/andigu/uncompute)
- [SciPy beta distribution and inverse-survival API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.beta.html)
- [NumPy eigendecomposition conventions and backend](https://numpy.org/doc/stable/reference/generated/numpy.linalg.eigh.html)
- [Lookup space/gate tradeoffs](https://arxiv.org/abs/1812.00954)

The report does not supply a verified exact metric-notebook URL, starter-kit revision, or package API schema. Discover these from the official competition assets rather than inventing identifiers or implementing an unofficial substitute as though it were authoritative.
