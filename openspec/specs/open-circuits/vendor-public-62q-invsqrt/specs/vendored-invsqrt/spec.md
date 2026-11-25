## ADDED Requirements

### Requirement: Source-backed invsqrt candidates only

Only I1, I2 and I3 SHALL be considered, and only where generating source
exists at the listed locations under an explicit Apache-2.0 licence. Hash
prefixes quoted in this change SHALL be treated as hints only.

#### Scenario: Binary-only candidate

- **WHEN** no generating source is found for a candidate
- **THEN** it is recorded as `binary_only` and not regenerated

### Requirement: Cheapest-first sequential verification

Regenerated candidates SHALL be verified in ascending order of static
cost. Verification SHALL stop at the first candidate with zero failures in
the smoke run, the full 200,540,928-trajectory run and one fresh
confirmation.

#### Scenario: Cheapest candidate passes

- **WHEN** the cheapest candidate passes all three runs
- **THEN** it is banked and no other candidate is run

#### Scenario: Failure in the smoke run

- **WHEN** a candidate shows any failure in its smoke run
- **THEN** it is excluded without a full run and the next candidate starts

#### Scenario: List exhausted

- **WHEN** every admitted candidate has been excluded
- **THEN** `no_go` is recorded and v6 invsqrt remains
