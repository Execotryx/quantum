# Quantum compilation experiments

A Python toolchain implementing the independently executable parts of the
[implementation plan](docs/implementation-plan.md) for Google's Verifiable Quantum
Circuit Compilation competition.

**Current status: G0 blocked; no optimized submission or accepted baseline yet.**
The official metric notebook v10 was downloaded and pinned. The competition-data
API returned HTTP 401 in this environment, so reference circuits, verifiers,
chemistry data, and the supplied kickmix backend have not been obtained. The plan
requires those assets and baseline reconciliation before circuit optimization.
The code reports this condition explicitly and prevents candidate/release promotion.
See [implementation status](docs/implementation-status.md) for completed and deferred work.

## Install and check

From the repository root, using Python 3.12 and [uv](https://docs.astral.sh/uv/):

```bash
uv sync --frozen
uv run qcompile test --tier unit
uv run qcompile test --tier extended
uv run ruff check src tests
uv run ruff format --check src tests
uv run qcompile contract validate
```

Contract validation currently returns exit code **2**, with named unresolved fields,
source pins, and discrepancies. This is the intended blocked result. The extended
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

Mathematical cost functions return **estimates** until their conventions are
reconciled with the acquired verifiers. Chemistry helpers take explicit tree roots
and angular conversions; they do not assume those unresolved official conventions.
The 76-orbital concrete schema is still report-derived; the metric pins the symbolic
schema while importing `ORBITALS` from the unavailable verifier.

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
blocked implementation work; none is replaced with a mock backend.
