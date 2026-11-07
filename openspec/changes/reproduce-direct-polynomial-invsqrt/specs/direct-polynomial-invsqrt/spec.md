## ADDED Requirements

### Requirement: Reproducible source and controls

The direct-phasing workflow SHALL pin the generator and coefficient inputs,
reviewed reuse rights, official contract, backend and runtime, and shall
rebuild the official reference and the confirmed hybrid incumbent before
ranking candidates. It SHALL record whether the direct control reproduces a
pinned public build or implements the published method independently.

#### Scenario: Public artifact has incomplete generator provenance

- **WHEN** the public notebook or circuit lacks reproducible source, inputs or reviewed reuse rights
- **THEN** the workflow records the gap and may compare an independently generated implementation with explicit provenance
- **AND** it does not claim exact source reproduction or use the disputed artifact as release input

#### Scenario: Incumbent identity or cost differs

- **WHEN** the rebuilt reference or incumbent differs from the pinned identity or cost outside the registered comparison tolerance
- **THEN** the workflow blocks ranking and retains the reconciliation diagnostics

### Requirement: Full-domain phase and native evidence

The direct-phasing screen SHALL evaluate all 3,133,452 legal inputs under the
pinned phase64 target, floor and circular-difference rules, with disjoint
complete coverage. It SHALL reconcile the phase model with reloaded KMB
fixtures, including restored input, zero scratch and branch-correct cleanup.
The screen SHALL price declared qubits and Toffoli-like, T-like and fine
rotation operations using the verifier's classifications, executed means or
a conservative screening bound, and the minimum remaining phase margin.

#### Scenario: A missing boundary or incomplete scan

- **WHEN** an input is omitted or repeated, a model/native phase disagrees, or a boundary case fails
- **THEN** the attempt is ineligible and records the failure

#### Scenario: Fine rotations consume the remaining error budget

- **WHEN** a candidate uses fine rotations
- **THEN** its rotation charge uses the verifier's allocation from the minimum absolute remaining margin
- **AND** the candidate is ineligible if there is no positive remaining margin

#### Scenario: No fine rotations are emitted

- **WHEN** the fine-rotation count is zero
- **THEN** scoring uses the base Toffoli and T counts without computing a rotation allocation
- **AND** the same registered phase and margin gates still apply

### Requirement: Bounded prospective selection

The workflow SHALL register controls, candidates, adaptive rules, fixtures,
salts, budgets, eligibility gates and tie-breaks before observing prospective
results. It SHALL preserve attempt records and enforce the registered phase,
margin and improvement gates against the confirmed incumbent. Initial
promotion policy SHALL require zero observed failures, positive minimum
margin, at most 90% of allowed phase error at the worst input, and at least
10% lower complete cost. Any policy change SHALL be separately preregistered.

#### Scenario: Variant clears isolated gate counts only

- **WHEN** a variant reduces Toffoli count but misses the complete rotation-inclusive cost or phase gate
- **THEN** the variant remains in the evidence as ineligible

#### Scenario: No qualifying or in-budget candidate

- **WHEN** no attempt meets the registered gates or the campaign breaches its registered envelope
- **THEN** the campaign records a no-go or incomplete decision and retains the current hybrid

### Requirement: Frozen winner with independent confirmation

The workflow SHALL verify one frozen qualifying KMB at full strength and
confirm it separately on identical bytes using a new preregistered salt.
Both runs SHALL use the pinned verifier, complete 200,540,928 trajectories,
pass the registered measured gates and bind the source, runtime, artifact
and actual receipts. The benchmark history SHALL reject reused salts or
repeat confirmation of unchanged bytes after a failed confirmation.

#### Scenario: A circuit or seed is substituted

- **WHEN** a KMB digest differs from the frozen selection or a salt has already been used in another role
- **THEN** verification or promotion is blocked with the mismatched identity recorded

#### Scenario: A receipt is partial or misses the measured threshold

- **WHEN** either run has incomplete coverage, an invalid receipt or cost or tolerance outside the registered gate
- **THEN** the candidate cannot replace the hybrid incumbent

### Requirement: Successor hybrid preserves certified chemistry

The successor SHALL replace only the inverse-square-root KMB. All nine
optimized ANGLE circuits, their matching factorization/tree NPZ and
reference DQI SHALL match the parent hashes. Formal certification SHALL
validate the complete chemistry family against a trusted parent local
certificate and its intact benchmark-scoped confirmation record. It SHALL
treat inherited confirmation as immutable lineage and require a fresh
confirmation for the newly generated inverse-square-root component.
Existing release records and confirmation semantics SHALL remain valid.

#### Scenario: Optimized chemistry lacks valid parent evidence

- **WHEN** the parent certificate is missing or invalid, a chemistry member or bound runtime differs, or its confirmation was consumed for tuning
- **THEN** the workflow blocks successor certification and preserves the existing candidate and ledger records

#### Scenario: Byte-identical retained chemistry is certified in the parent

- **WHEN** the full chemistry identity, trusted parent certificate and eligible confirmation history match
- **THEN** the successor links that lineage without registering or spending another chemistry confirmation
- **AND** the retained optimized files are not relabeled as official reference files

### Requirement: Extracted successor archive improves the parent

The workflow SHALL require two matching deterministic archive builds, strict
manifest verification on a fresh extraction, and the complete pinned metric
result. It SHALL check exact coverage of 200,540,928, 102,400 and 254,464 for
inverse square root, DQI and chemistry respectively, reconcile retained
costs to the parent, apply the registered measured inverse-square-root cost
and phase gates and require aggregate score strictly greater than 1.0286345856615866.
The local certificate SHALL bind the tested ZIP, member hashes, receipts and
parent lineage.

#### Scenario: Component checks pass but the complete archive does not

- **WHEN** the full metric is incomplete, retained costs cannot be reconciled, or the aggregate fails to improve on the parent
- **THEN** the successor is not certified and the tested parent remains the fallback

#### Scenario: The extracted successor passes the complete metric

- **WHEN** both archive builds match and all identity, coverage, retained-cost and improvement checks pass
- **THEN** the local certificate records the exact archive hash and measured comparison with the parent
- **AND** external acceptance remains a separately recorded outcome
