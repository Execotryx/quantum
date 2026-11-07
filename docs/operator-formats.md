# Operator records and boundaries

All configurations and evidence use JSON. File writes reject NaN/Inf. New records
use exclusive creation; state updates replace complete JSON files atomically.
Candidate mutations use a store lock directory. After an interrupted writer,
inspect the retained files before removing a stale `.record-lock` directory.
The CSV index is a convenience view, not the authority for candidate status.

Paths in asset selections, backend configurations, and build recipes should be
absolute. Run CLI examples from the repository root. A complete selection names
all three tasks, including at least one angle circuit and its matching NPZ.

## Candidate selection

```json
{
  "config": {"hypothesis": "A specific, registered circuit optimization"},
  "claims": [{
    "kind": "exact_algorithm_intent",
    "assumptions": "State actual input subspace, initialization and composition assumptions."
  }],
  "artifacts": {
    "invsqrt.kmb": {
      "path": "/absolute/path/to/invsqrt.kmb",
      "sha256": "REPLACE_WITH_ACTUAL_DIGEST",
      "origin": "generated",
      "provenance": "Generator/checkpoint/configuration identity"
    },
    "dqi.kmb": {
      "path": "/absolute/path/to/reference/dqi.kmb",
      "sha256": "REPLACE_WITH_ACTUAL_DIGEST",
      "origin": "retained_reference",
      "provenance": "Pinned original reference and acceptance receipt"
    },
    "dfthcsos/angle_k_0.kmb": {
      "path": "/absolute/path/to/reference/angle_k_0.kmb",
      "sha256": "REPLACE_WITH_ACTUAL_DIGEST",
      "origin": "retained_reference",
      "provenance": "Pinned original reference and acceptance receipt"
    },
    "dfthcsos/submission.npz": {
      "path": "/absolute/path/to/reference/submission.npz",
      "sha256": "REPLACE_WITH_ACTUAL_DIGEST",
      "origin": "retained_reference",
      "provenance": "Matching pinned factorization/tree"
    }
  }
}
```

This is a structural example, not usable evidence. Include all actual contiguous
angle indices. The ID binds configuration, contract, artifact hashes, origins and
provenance; relocation of identical files does not change circuit identity.
Editing bytes or provenance invalidates the record.

The states are `draft`, `numerically_feasible`, `circuit_smoke_passed`,
`full_local_passed`, `release_selected`, and `remote_accepted`; `rejected` is an
explicit terminal development outcome. Use `candidate advance --id ... --state ...
--evidence /path/to/report.json` for a single supported transition. Numerical
advance requires a passing independent-numerical envelope with artifact/contract
hashes and the numerical report hash. Official advance consumes the real
`verification.json` with status, role, tier, completeness and source/environment
identity. A reference-only baseline remains a baseline, not an improved release.

A release-selection transition additionally requires hash-addressed JSON receipts
for `g0`, `g1`, `opportunity`, `mutations`, `stability`, and `improvement`:

```json
{"path": "/absolute/path/to/receipt.json", "sha256": "ACTUAL_DIGEST"}
```

Each receipt must record `passed: true` and the current `contract_hash`.
Candidate-specific mutation/stability/improvement receipts must also bind
`artifact_hashes`. Receipt integrity is checked here; the operator still must
produce the substantive gate evidence required by the implementation plan.
This workflow does not generate proof by accepting a manually asserted receipt.

## Backend result counters

`assets pin-backend` records every source/data/binary file below the two official
import roots, excluding only Python bytecode caches. The reviewed notebook's exact
hash is enforced separately. Installed imports must actually resolve to these
inventoried roots; this is checked in the worker. Adding or changing a backend
file requires a deliberate new inventory and contract reconciliation.

The adapter calls the notebook's real `generate_standard_submission` function.
Thin wrappers retain each real verifier's return dictionary; all verifier logic
and exception behavior remain upstream. Logs and raw returns are saved alongside
identity and timing. Map actual integer fields after inspecting those returns:

```json
{
  "coverage_mapping": {
    "invsqrt": {"completed": "verified_shots", "expected": "verified_shots"},
    "dqi": {"completed": "verified_shots", "expected": "verified_shots"},
    "dfthcsos": {"completed": "verified_shots", "expected": "verified_shots"}
  },
  "confirmation_mapping": {
    "benchmark": "dqi", "n": "verified_shots", "k": ["value_errors", "phase_errors"]
  }
}
```

These names are reconciled against the acquired official verifiers. The two DQI
failure counters are disjoint: phase failures exclude value failures. A list of
distinct paths is summed; the single-path string form remains supported. Dot paths
can traverse nested dictionaries. Missing, negative or noninteger counters and
failure totals above completed shots are errors.

Both coverage aliases read the actual returned `verified_shots`; they do not
create an independent expectation from success. Release certification separately
compares that count to `fields["release.coverage"].value`, whose three values are
full expected shot counts. Chemistry's value must match the selected R/B shape.
Raw official costs remain separate from the independent estimate functions.

Each completed benchmark also writes a `benchmark-NAME.json` receipt with its
actual return dictionary and elapsed wall time. Such a receipt does not establish
overall metric completion; that still requires the final verification report.

## Confirmation

A protocol names `benchmark`, integer `sample_size`, integer `max_failures`,
`distribution`, `confidence_procedure`, `stop_rule`, `compute_allowance`, and
`seed_policy`. Its seed policy has role `confirmation`, an unused salt of at
least 32 characters and an explicit distribution description. Sample size and
thresholds must come from the registered, source-reconciled procedure; no example
numeric threshold is presented as an official requirement.

Registration precedes execution. Each generated benchmark needs a separate
confirmation. A hybrid confirmation binds the complete component, including
the chemistry factorization and tree even when the NPZ is retained. Inverse
square root and chemistry pin `backend_hash`, require zero failures and need
200,540,928 and 254,464 completed trajectories respectively. Chemistry also
pins the verifier's canonical family digest in `verifier_artifact_sha256`.
The pinned verifiers raise on bad trajectories and return PASS only after
full coverage. The importer checks the raw result before deriving zero
failures. The legacy single-benchmark record and DQI counter mapping retain
their original meaning.

The fixed metric determines sample size, so a requested protocol must match
its actual returned count. Custom sample sizes need a separately reviewed
official adapter.
Missing sample counters leave confirmation incomplete, never passed. Failed or
tuning-consumed data cannot confirm a replacement; unchanged bytes cannot be
repeatedly sampled. The ledger reserves salts globally within the run store.
The Python API exposes `consume_confirmation` to mark evidence subsequently used
for tuning. Such use is an operator decision; it cannot be detected automatically.

The reduced metric smoke sample can reject the reference DQI circuit on its
confidence bound even with zero observed errors. A complete hybrid metric
report with all three exact full-strength coverage counts can also satisfy
the hybrid smoke transition. That report retains its full tier and coverage.

## Rebuild recipes and certificates

A release selection extends a candidate selection with `candidate_id` and
`build_recipes`. Each generated path belongs to exactly one recipe. A recipe has
`argv` (an argument array, with `{output_dir}` substituted into a new directory),
`outputs` (archive paths), and `inputs` (absolute paths mapped to frozen hashes).
Pin the executable generator/checkpoint/configuration inputs. Commands are explicit
operator-supplied code execution, run without a shell. Frozen expected output hashes
must agree with both fresh builds. Unexpected output files are rejected.

The CLI supplies the selected candidate record and project root. Retained reference
files are copied unchanged. The release source revision and dependency lock must
match the candidate. Two independent builds and two deterministic ZIPs must match
before a fresh extraction is made. The full verifier is run on a new extraction
again when `release verify` executes, not on the previous working directory.

A direct-phasing successor declares unchanged optimized ANGLE files as
`retained_certified`. The candidate's `retained_chemistry` binding contains the
parent candidate ID, exact ZIP SHA-256, local certificate SHA-256 and backend
identity. The store resolves the local certificate, checks the parent's
chemistry confirmation and complete component manifest, and carries forward
that lineage without reserving a new chemistry confirmation. Only the new
inverse-square-root member receives a fresh confirmation.

The full archive comparison uses the same registered seed on both archives
when retained DQI gate counts differ across seeds. The paired parent
registration binds the existing successor receipt before execution. This
matches the sampling distribution on the identical DQI circuit and keeps
the two component confirmation seeds independent.

A supporting-evidence JSON must contain substantive records for `coverage_counts`,
`cost_breakdown`, `numerical_margins`, `mutation_diagnostics`, `primitive_scope`,
`representation_stability`, and `opportunity_decision`, plus the pinned
`accepted_reference_costs`. Coverage must agree exactly with mapped real verifier
returns and resolved contract expectations. Complete costs must improve at least
one component and the aggregate geometric mean. The certificate records local
acceptance only. Remote acceptance requires a separate retained result for the
exact ZIP, submission ID and improved score; it is never inferred from local runs.

## Scope still awaiting official inputs

No code here certifies arbitrary coherent-input correctness of a full circuit.
No official reference circuit, decoder sampling distribution, chemistry tensor
reconstruction, symmetry/eigenvector matching convention, phase accumulator rounding,
or kickmix generator API is guessed. The independent field tests share field tables
between decoder controls and share Vandermonde symbol recovery; polynomial-field
fixtures and full-syndrome re-encoding cover some of that common-mode risk. Further
primitive proofs, circuit differential checks and official reconciliation are
mandatory before the relevant gates can pass.
