# Implementation status — 30 October 2026

**The independent toolchain is implemented and tested. The research program and
first improved competition release are not complete. G0 remains blocked.**

The repository previously contained only the implementation specification. This
change adds a locked Python project, executable CLI, independent mathematics,
artifact/experiment/release infrastructure, tests and CI. It follows the plan's
explicit instruction to continue mathematical scaffolding when official assets
are unavailable, without advancing the affected gates.

## Acquired inputs and concrete blocker

The public official metric notebook was retrieved through Kaggle's API:
`metric/google-quantum-ai-metric`, version **10**, last-run metadata
`2026-10-27T15:14:28.9970018Z`. Its exact notebook body is pinned in
`contracts/sources.lock.json`; acquisition preserves it without redistribution.
The adapter invokes its actual entry point. The notebook pins submission loading
and symbolic NPZ schema, instruction whitelist and some allocation limits.

The competition-data listing endpoint returned **HTTP 401 Unauthorized**. No
reference circuit ZIP, supplied verifier package, numerical chemistry assets or
compatible supplied kickmix binary has been acquired in this environment. The
original source report is not a substitute for those assets. No baseline acceptance,
profile, complete official cost, precise phase rounding, DQI sampling distribution,
chemistry symmetry/matching convention or supported native backend is claimed.
The concrete 76-orbital schema remains report-derived pending its imported official
constant; the notebook's symbolic shapes alone do not reconcile that constant.

## Work-package accounting

| Plan item | Implemented | Remaining condition |
|---|---|---|
| CONTRACT-01 | Contract schema, required-field/provenance checks, source locks, discrepancies and explicit input/initialization/composition declarations | Acquire all required sources; reconcile unresolved release-critical fields |
| TOOLCHAIN-01 | Frozen independent Python dependencies; source/backend inventory; subprocess adapter; environment/NumPy backend identity | Install actual compatible kickmix; tiny real circuit smoke and reproducible official environment |
| BASELINE-01 | Executable baseline entry point, preserved stdout/stderr and actual return dictionaries, local seed policy, resource reporting | Original archive acceptance, normalization, profiles and representative official-validator mutations |
| ORACLE-INV-01 | Integer irrational brackets; circular comparison; independent Decimal boundary checks; exact finite-width models; exhaustive conservative scan; rotation price edge cases | Match official accumulator rounding/rotation encoding and official pricing/rounding; validate actual candidate outputs |
| ORACLE-DQI-01 | Polynomial/table field controls, classical BM/EEA, complete-syndrome recovery, mask parity, stable CP/R with high-precision tail fixtures and separate failure labels | Reconcile official sampler/binding/statistic; circuit phase/register/workspace tests; independent EEA circuit control where applicable |
| ORACLE-CHEM-01 | Bounded NPZ preflight, ordered trees, explicit-unit angle reconstruction, batching/deltas/reversal, shifted streamed norm and workspace helpers, sign/degeneracy fixtures | Official complete tensor reconstruction, fixed-symmetry identity, one-electron matching and full resource-accounting reconciliation |
| ARTIFACT-01 | Deterministic NPZ/ZIP; manifests; safe extraction; identity/provenance invalidation; mutation tests | Real kickmix canonical serialization/reload tests after backend acquisition |
| OPPORTUNITY-01 | Numeric budget registration and complete-cost go/no-go helper; preserved negative diagnostic | Actual bounded prototypes, profiles, decision receipts and measured selected-path re-estimate after G0/G1 |
| INV-SEARCH-01 / INV-CIRCUIT-01 | Finite-width Horner/Newton numerical model interface | Search across registered families, circuit generation, primitive evidence and all official trajectories, after prerequisite gates |
| CONFIRM-01 | Preregistered one-use salt/protocol ledger, frozen-byte binding, failed/consumed-history handling | Execute fresh actual confirmation; map real sample counters; one optimized benchmark per candidate is the implemented first-release scope |
| RELEASE-01 | Two independent pinned-recipe builds, deterministic ZIP comparison, fresh extraction, full-verification invocation and guarded local certificate | Successful actual rebuilds/verification/confirmation and substantive release evidence; exact ZIP acceptance by Kaggle |
| Optional DQI/chemistry optimization | Classical/math controls and generic recipe interface | Reversible BM/parity/cleanup synthesis; QROM compiler; factorization/tree/precision searches; opportunity gates must first justify them |

No G0–G5 gate is marked passed. No cost improvement, training-like search sweep,
reversible production circuit, official-distribution confirmation, final submission
ZIP or remote result has been manufactured to fill these gaps. The supplied initial
experiment deliberately tests an inaccurate model so numerical rejection is reviewable.

## Validation performed

- **267 tests passed** in the implementation environment (Linux x86_64, Python 3.12.14).
- The inverse-square-root harness control visited all **3,133,452** valid inputs,
  with positive conservative target margins. This feeds the mathematical target back
  into the harness; it establishes enumeration/control behavior, not circuit correctness.
- Decimal boundary/random fixtures independently checked integer phase targets.
- All 4,096 unary field values and all 4,095 nonzero inverses were checked against
  polynomial arithmetic; BM/EEA controls agreed on deterministic errors at every
  supported weight 0–35, with endpoint and varying-mask checks.
- Extreme-tail CP fixtures were checked using an independent Decimal lower-tail
  recurrence and a small-sample high-precision polynomial CDF. Repetition factors
  were checked immediately below the rejection cutoff; rotation prices were checked
  with high precision and explicit units/zero-rotation cases.
- The **actual acquired metric notebook's NPZ reader** was exercised on synthetic
  valid-shape and known-invalid arrays. This was preflight only, with the concrete
  orbital count supplied as a report-derived fixture; no kickmix verifier was run.
- Archive mutation, schema/finite/strict-floor controls, state/confirmation reuse,
  stale identity/provenance and independent-rebuild tests passed. Synthetic generator
  bytes in tests are labeled test fixtures and are never official execution evidence.
- Ruff lint/format, frozen dependency-lock checks, Python compilation and source/wheel
  package builds passed. CI is configured for Linux/macOS; remote CI results are separate.
- Contract validation correctly returned blocked status and exit code **2**.

Machine-readable scope, source hashes, test counts and the negative numerical
result are in [implementation-checks.json](evidence/implementation-checks.json).
The tests include negative controls that intentionally fail validators; their
expected rejection is a test pass, not a passing candidate.

## Numerical and integrity issues addressed during implementation

Near-one beta upper bounds can saturate to 1 in binary64: retain that conservative
bound and reject its finite-score eligibility, rather than treating it as a useful
finite estimate. Near the DQI cutoff, rationalize `0.25-sqrt(epsilon)` before the
`log1p` calculation to avoid cancellation. Zero-failure bounds use `expm1` and never
form `1-delta` in binary64.

Bind artifact origin/provenance into candidate identity. Recheck hashes before and
after official execution. Refuse relabeling generated outputs as retained references
at release. Enforce the reviewed metric's actual hash and inventoried import roots.
Preserve incomplete runs and unavailable counters explicitly; do not infer coverage
from an exit code or retry unchanged bytes until confirmation happens to pass.

## Next executable step

Acquire the authorized competition data and establish the actual compatible backend;
then use the documented `assets pin-backend` and `baseline verify --tier full`
commands. Reconcile G0 with the resulting original-reference diagnostics, test
negative controls and profiles. Only then can the plan's optimization workstreams
and improved-release definition of done be completed.
