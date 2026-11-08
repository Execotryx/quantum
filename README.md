# Quantum compilation experiments

A Python toolchain for reproducible quantum-circuit compilation experiments,
independent mathematical checks, and local verification against pinned evaluators.

## Current state

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

The v6 screen built each circuit twice, checked all 3,133,452 inputs
against the phase model, and passed 31,232 native trajectories per circuit.
The frozen v6 circuit then passed all **200,540,928** full-strength
trajectories at the screened cost. Worst-case phase tolerance use stayed
at **66.77%**. Fresh confirmation and paired archive verification remain
pending. [Full v6 cloud result](docs/v6-full-cloud-08-11-2026-23-26-00.md)

The DQI figures cover reduced dimensions. The full-size history depth still depends on the
registered sampling campaign. Chemistry's pinned reference yielded an
initial S2 offset bound of **11.5** and a penalty of **1.0**. Its compressed
fit must pass the residual gates before the loader projection can compare
candidate costs.

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
