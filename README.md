# Quantum compilation experiments

A Python toolchain implementing the independently executable parts of the
[implementation plan](docs/implementation-plan.md) for Google's Verifiable Quantum
Circuit Compilation competition.

**Current status: official contract ready; full reference baseline accepted locally.
No optimized submission or remote acceptance is claimed.**
All 34 competition files are available locally and byte-checked. The supplied
backend runs in Ubuntu WSL with Python 3.13. See the
[contract reconciliation](docs/contract-reconciliation-01-11-2026-22-50-00.md)
for source evidence and the completed baseline measurements.

The original competition-data API attempt returned HTTP 401. Manual acquisition
resolved that access blocker. The pinned v10 metric has now accepted the original
references at full strength, with complete coverage counters and retained costs.
Optimization still requires the plan's independent primitive/negative-control
checks and opportunity decision; this is a verified baseline, not an improvement.
See [implementation status](docs/implementation-status.md) for completed and deferred work.

## Install and check

Run these commands from the repository root in Linux (Ubuntu WSL on Windows),
using [uv](https://docs.astral.sh/uv/). Independent checks also support Python 3.12
on Linux/macOS; the supplied official backend requires Linux and Python 3.13:

```bash
export UV_PROJECT_ENVIRONMENT=vendor/linux-env
uv sync --frozen --python 3.13
uv run qcompile test --tier unit
uv run qcompile test --tier extended
uv run ruff check src tests
uv run ruff format --check src tests
uv run qcompile contract validate
```

Contract validation returns exit code **0** with the acquired pinned inputs and
completed baseline evidence. A checkout without those ignored official assets
returns **2** and names the missing source pins. The extended
tier also scans every one of the 3,133,452 inverse-square-root inputs as a harness
control. Feeding the mathematical target into that control does not validate a
candidate circuit.

## What is implemented

| Module | Behavior |
|---|---|
| `contract` / `assets` | Per-field provenance, source hashes, immutable official-metric acquisition and backend inventories, explicit G0 blockers |
| `reference.invsqrt` | Integer brackets and nearest-even diagnostic, circular phase comparison, Decimal checks, chunked exhaustive conservative margin scan |
| `invsqrt.fixed` | Explicit signedness, widths, rounding, overflow, Horner models and optional Newton step |
| `reference.scoring` | Margin-aware rotation price; stable extreme-tail Clopper–Pearson bound and repetition penalty; constrained chemistry and three-task objectives |
| `dqi` / `reference.field` | Independent table/polynomial field backends; classical BM and EEA locator controls; syndrome recovery and variable-mask parity |
| `chemistry` | Bounded NPZ schema preflight, ordered rooted trees, parameterized angle reconstruction, XOR batching/reversal, streamed shifted residual norms and workspace accounting |
| `official` / `worker` | Subprocess calls to the actual pinned metric; raw diagnostics, actual verifier returns, local seed roles, source/environment identity and timeout handling |
| `experiments` | Candidate states, immutable artifact identities/provenance, bounded diagnostic registration, opportunity decisions and one-use confirmation history |
| `artifacts` / `release` | Deterministic NPZ/ZIP, bounded safe extraction, two independent recipe builds, extracted-archive verification and guarded local certification |

Mathematical helpers remain **independent models**, not circuit acceptance evidence.
Their phase, field, selected scoring and angle conventions have been checked
against the pinned official sources. Chemistry helpers still take explicit tree
roots and angular conversions; the official contract uses root 0 and radians =
pi*word/2^(brot-1). The concrete 76-orbital schema is now source-reconciled.

## Acquire and reconcile official inputs

1. Download the assets from the official
   [competition Data page](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/data)
   using an account with access. Preserve the original archive and its bytes. Keep
   credentials outside this repository. Acquisition is not competition submission.
2. Retrieve the exact reviewed metric:

   ```bash
   uv run qcompile assets acquire-metric
   ```

   Existing files are preserved. A changed notebook version or hash is rejected
   until explicitly reviewed. The pinned origin and hash are in
   `contracts/sources.lock.json`; upstream assets are not redistributed here.
3. Install the actual compatible kickmix build, then inventory the acquired code:

   ```bash
   uv run qcompile assets pin-backend \
     --metric vendor/metric/google-quantum-ai-metric.ipynb \
     --verifiers /absolute/path/to/official/verifiers \
     --kickmix /absolute/path/to/official/kickmix \
     --output vendor/backend.json
   ```

   The backend configuration must identify the actual importable directories.
   Native binary compatibility must be established on the target machine. The
   independent Python dependency lock is not an official kickmix environment lock.
4. Run the **unmodified reference components**, preserving all verifier diagnostics:

   ```bash
   uv run qcompile baseline verify \
     --artifact-dir /absolute/path/to/official/sample_submission \
     --backend vendor/backend.json --tier full \
     --seed-policy configs/local-seed.json --output runs/baseline-full
   ```

   This intentionally works before contract reconciliation so G0 can obtain its
   evidence. `smoke` reduces only the official metric's DQI/chemistry shot counts;
   inverse square root retains its full official coverage. Smoke never qualifies
   as release evidence. All salts here are local, unrelated to private Kaggle salts.
5. Resolve each contract field against actual source symbols and measured baseline
   results. Preserve disagreements. Pin every required source, compiler/backend
   identity, actual coverage counters and array/sampler conventions. Populate
   `coverage_mapping` / `confirmation_mapping` in the backend only after inspecting
   the real return dictionaries; [operator formats](docs/operator-formats.md) explains
   their structure. Never infer missing counters from a successful process alone.

## Development and release

Step-2 profiling uses `qcompile baseline campaign` from a clean committed Linux
checkout, followed by `qcompile baseline freeze`. The campaign preregisters A,A,B
salts, full-strength coverage and resource limits; it delegates to the actual
pinned metric and retains raw stage/process-tree measurements. See the
[campaign guide](docs/baseline-campaign-02-11-2026-01-19-10.md) for the exact scope,
sampling limits and frozen-bundle format.

A runnable **negative numerical diagnostic** is provided:

```bash
uv run qcompile experiment run --config configs/invsqrt-initial.json
```

It evaluates a deliberately inaccurate constant model over inputs 1–1024 and
records nonpositive margins. `numerical_diagnostic_completed` means the experiment
finished, not that the model passed. Registrations, failures, environment details,
and reports are retained under a content-derived run ID; identical registrations
are not overwritten. This is not the plan's post-G0 opportunity screen.

Candidate commands support registration, state changes with evidence, actual
verification, and preregistered confirmation. `candidate advance` consumes the
hash-bound report, while `candidate verify` records a run without silently selecting
it. Confirmation currently supports **one optimized benchmark per candidate**, the
first-release scope; all other components retain validated reference bytes.
Combining multiple independently optimized benchmarks needs an additional composition
workflow. Do not relabel generated bytes as references to bypass confirmation.

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

These commands block until their prerequisites are satisfied. The release builder
reruns each generated component's pinned recipe in two new directories; it cannot
count two copies of generated files as independent builds. It copies retained
reference bytes unchanged. It then builds deterministic ZIPs, compares them, and
verifies a fresh extraction of the frozen ZIP. A local certificate requires actual
coverage, cost improvement and supporting numerical, mutation, primitive, stability
and opportunity evidence. It cannot assert Kaggle acceptance. There is no automatic
remote-submit command.

See [operator formats](docs/operator-formats.md) for JSON records and the exact
limits of these infrastructure checks. The circuit generators, official-distribution
sampler, full chemistry reconstruction/matching and optimization searches remain
remaining implementation work; none is replaced with a mock backend.
