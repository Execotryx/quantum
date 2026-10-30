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
    "dqi": {"completed": "ACTUAL_COMPLETED_FIELD", "expected": "ACTUAL_EXPECTED_FIELD"}
  },
  "confirmation_mapping": {
    "benchmark": "dqi", "n": "ACTUAL_SAMPLE_COUNT_FIELD", "k": "ACTUAL_FAILURE_COUNT_FIELD"
  }
}
```

The names above are placeholders, not alleged upstream API names. Dot paths can
traverse nested dictionaries. Missing fields or noninteger counters are errors;
no counts are synthesized. For release, supply mappings for all three benchmarks
and reconcile expected counts in `fields["release.coverage"].value` in the contract.
Raw official costs remain separate from the independent estimate functions.

## Confirmation

A protocol names `benchmark`, integer `sample_size`, integer `max_failures`,
`distribution`, `confidence_procedure`, `stop_rule`, `compute_allowance`, and
`seed_policy`. Its seed policy has role `confirmation`, an unused salt of at
least 32 characters and an explicit distribution description. Sample size and
thresholds must come from the registered, source-reconciled procedure; no example
numeric threshold is presented as an official requirement.

Registration precedes execution. Confirmation must cover the sole generated
benchmark; retained components undergo full release revalidation. The fixed metric
currently determines sample size, so a requested protocol must match its actual
returned count. Custom sample sizes need a separately reviewed official adapter.
Missing sample counters leave confirmation incomplete, never passed. Failed or
tuning-consumed data cannot confirm a replacement; unchanged bytes cannot be
repeatedly sampled. The ledger reserves salts globally within the run store.
The Python API exposes `consume_confirmation` to mark evidence subsequently used
for tuning. Such use is an operator decision; it cannot be detected automatically.

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
