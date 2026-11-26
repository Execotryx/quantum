## ADDED Requirements

### Requirement: Source-bound degree-35 portfolio registration

The system SHALL register the degree-35 portfolio under `portfolio-v4` with
an exclusive minimum aggregate score of 35 and SHALL bind every component
to exact member hashes, a source manifest, and two distinct build receipts.

#### Scenario: Missing or mismatched lineage

- **WHEN** an above-35 registration omits a component or binds different member hashes
- **THEN** preparation rejects the portfolio

### Requirement: Strict paired cloud acceptance

The system SHALL certify an above-35 candidate only after the full metric
and fresh independent confirmation pass on identical archives and each
role clears the exact cost-product threshold for 35.

#### Scenario: Confirmation lands at the threshold

- **WHEN** either complete role yields a cost product at the score-35 boundary
- **THEN** the audit rejects the archive even if numeric score rounding appears to pass

#### Scenario: Both sealed roles clear the threshold

- **WHEN** both full roles match the registered identities and strictly clear 35
- **THEN** the audit records `verified_above_35` for those archive bytes
