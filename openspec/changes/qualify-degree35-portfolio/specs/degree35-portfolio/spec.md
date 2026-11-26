## ADDED Requirements

### Requirement: Source-bound degree-35 portfolio registration

The system SHALL register the degree-35 portfolio under `portfolio-v5` with
an inclusive minimum aggregate score of 35 and SHALL bind every component
to exact member hashes, a source manifest, and two distinct build receipts.

#### Scenario: Missing or mismatched lineage

- **WHEN** a score-35 registration omits a component or binds different member hashes
- **THEN** preparation rejects the portfolio

### Requirement: Paired cloud acceptance at the score floor

The system SHALL certify a score-35 candidate only after the full metric
and fresh independent confirmation pass on identical archives and each
role meets the inclusive exact cost-product threshold for 35.

#### Scenario: Confirmation lands at the threshold

- **WHEN** both complete roles yield a cost product at or below the score-35 boundary
- **THEN** the audit records `verified_at_least_35` for the registered archive bytes

#### Scenario: One role misses the threshold

- **WHEN** either complete role yields a cost product exceeding the score-35 boundary
- **THEN** the audit rejects the archive even if numeric score rounding appears to pass
