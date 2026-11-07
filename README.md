# Quantum compilation experiments

A Python toolchain for reproducible quantum-circuit compilation experiments,
independent mathematical checks, and local verification against pinned evaluators.

## Current state

The reference and independent mathematical checks are complete. The best
locally verified archive combines the confirmed inverse-square-root circuit
with the nine banked chemistry circuits and retains the reference DQI circuit.
The complete extracted archive scored **1.0286345857** relative to the reference.

| Benchmark | Locally measured change | Full trajectories in the hybrid |
|---|---:|---:|
| Inverse square root | 5.07% lower cost | 200,540,928 |
| Chemistry | 3.21% lower cost | 254,464 |
| DQI | Reference circuit and cost | 102,400 |

The [hybrid validation report](docs/banked-chemistry-07-11-2026-01-52-35.md)
records the exact archive and component results. The
[independent validation audit](docs/step3-completion-02-11-2026-13-20-23.md)
records the primitive and defect-control evidence.

[Direct polynomial phasing](openspec/changes/reproduce-direct-polynomial-invsqrt/proposal.md)
is the next inverse-square-root optimization on the hybrid branch. Its
promotion gates require full-domain phase screening, separate full
verification and confirmation on the same bytes, and a measured improvement
on a rebuilt hybrid archive. [Formal hybrid certification](openspec/changes/certify-hybrid-release/proposal.md)
is still open. It supplies the parent certificate that a successor needs to
carry forward the unchanged chemistry family.

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
verification, and record preregistered confirmation. The first build workflow
supports one optimized benchmark per candidate, with validated references for
the other components.

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
