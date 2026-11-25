## ADDED Requirements

### Requirement: Fixed candidate set

Only D2, D3, D5, D5 with the Özer patch, and D4 SHALL be considered, each
subject to the admission checks.

#### Scenario: Candidate built from a denylisted KMB

- **WHEN** a candidate's build inputs include the `993c70386a3d` KMB
- **THEN** it is rejected before regeneration

### Requirement: Reproducible regeneration

Each admitted candidate SHALL be built twice by our adapter with identical
KMB SHA-256. Where the origin publishes an output hash at the pinned
revision, the build SHALL match it. Hash prefixes quoted in this change
SHALL be treated as hints only.

#### Scenario: Origin hash mismatch

- **WHEN** the rebuilt KMB differs from the origin's published hash
- **THEN** the candidate is excluded and the mismatch is recorded

#### Scenario: Hint mismatch only

- **WHEN** the origin's published hash differs from the prefix quoted in this change and the rebuild equals the origin's hash
- **THEN** the candidate continues and `hint: mismatch` is recorded

### Requirement: Pooled failure price

A candidate's price SHALL use `k_price = ⌈½·χ²(0.95; 2K+2) / S⌉` failures
in one 102,400-shot run, where `K` is its total failing shots over the `S`
salts it has run.

#### Scenario: Two failures on one of eight salts

- **WHEN** a candidate shows 2 failures on one salt and 0 on the other seven
- **THEN** its price uses 1 failure

### Requirement: Two-stage pricing

Every regenerated candidate SHALL run on the first 2 registered salts. Only
the two candidates with the lowest `S = 2` pooled price SHALL run on the
remaining 6. Selection SHALL use the `S = 8` pooled price, with ties broken
by fewer qubits, then fewer mean Toffolis.

#### Scenario: Five candidates regenerated

- **WHEN** five candidates are regenerated
- **THEN** exactly 22 full-coverage runs are made

#### Scenario: Single candidate

- **WHEN** only one candidate is regenerated
- **THEN** it runs all 8 salts and is selected by the outcome table
