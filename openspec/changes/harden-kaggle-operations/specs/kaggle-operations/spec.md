## ADDED Requirements

### Requirement: Bound external receipts

Each Kaggle submission SHALL have an immutable ledger record that binds
the uploaded ZIP SHA-256, the local verification certificate, the local
aggregate score, the metric hash and the displayed public score.

#### Scenario: A certified archive is uploaded

- **WHEN** the user uploads a ZIP prepared by `tools/kaggle_receipt.py prepare`
- **THEN** the submission message contains the archive label and the first 12 hex digits of its SHA-256, and `record` matches the scored row by that message

#### Scenario: A historical upload lacks a hash in its message

- **WHEN** a receipt predates the ledger and its message carries no hash
- **THEN** the record is marked `binding: inferred` and states the evidence used to infer the archive

### Requirement: Metric drift gate

A submission SHALL be blocked when the published metric notebook hash
differs from the pinned certification metric.

#### Scenario: The published metric changed

- **WHEN** the pulled notebook hash differs from the pinned hash
- **THEN** `prepare` exits non-zero and no submission ZIP is written until a reconciliation note exists

### Requirement: Reconciliation bands

Each receipt SHALL be reconciled with the band for its archive class.
Exact archives SHALL agree within 1e-5. Failure-priced archives SHALL
fall within the local multi-salt range widened by 1e-5.

#### Scenario: An exact archive disagrees

- **WHEN** an exact archive's public score differs from its local score by more than 1e-5
- **THEN** further submissions stop until the hash, metric and packaging are rechecked and the result is recorded

#### Scenario: A failure-priced archive scores below its local range

- **WHEN** the public score is below the minimum local multi-salt score minus 1e-5
- **THEN** the implied failure count is recorded and the DQI candidate is repriced at `k_max + 2` before any further promotion

### Requirement: Conservative DQI failure pricing

Approximate DQI candidates SHALL be measured on at least five registered
development salts at full shot count. Promotion decisions SHALL price
the candidate at two more failures than the worst observed salt.

#### Scenario: An approximate candidate shows no failures locally

- **WHEN** all development salts report zero failures
- **THEN** the promotion cost is still computed with two failures

### Requirement: Budget-limited screen outcome

A bounded screen SHALL end as `budget_limited`, not `no_go`, when a
registered cap stopped it while the objective was still improving by at
least 1% relative over the last 25% of evaluations.

#### Scenario: A fit stops at its evaluation cap while improving

- **WHEN** the evaluation cap ends a fit whose objective fell by more than 1% over its final quarter
- **THEN** the lane is recorded as `budget_limited` and may be re-registered with a larger budget

#### Scenario: A fit plateaus far from its gate

- **WHEN** the objective changes by less than 0.1% over the final quarter and remains above twice the threshold
- **THEN** the lane may be recorded as `no_go`

### Requirement: Packaging negative fixtures

The archive preflight SHALL reject out-of-range ids, malformed NPZ
arrays, non-contiguous ANGLE indices, forbidden `Z_POW`, ANGLE widths
above 128, contract register mismatches and non-canonical ZIP members.

#### Scenario: A malformed archive is checked

- **WHEN** any negative fixture is passed to the preflight
- **THEN** it fails with a diagnostic naming the violated boundary and whether the boundary comes from the pinned metric or a local guard

### Requirement: Final selection hedge

The final two selections SHALL include the best certified archive and the
best certified archive whose DQI component is exact.

#### Scenario: The best archive uses an approximate DQI decoder

- **WHEN** the best certified archive has failure-priced DQI
- **THEN** the second selection is the best certified archive with exact DQI
