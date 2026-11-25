## ADDED Requirements

### Requirement: Exhaustive multiplier check

A multiplier SHALL be transplanted only after its products match the
0x1053 field on all 4096×4096 input pairs, including its basis conversion.

#### Scenario: Basis conversion error

- **WHEN** any product differs after basis conversion
- **THEN** that candidate is rejected

### Requirement: Fixed transplant rule

A transplant SHALL happen only when the candidate uses fewer Toffolis per
call than the decoder's multiplier, adds no qubits at peak, and saves at
least 1% of the mean Toffoli count.

#### Scenario: Saving below 1%

- **WHEN** the projected saving is below 1%
- **THEN** `no_transplant` is recorded and no rebuild runs

### Requirement: Promotion limit

A transplanted decoder SHALL be promoted only if its `S = 8` pooled price
is at most 0.99 times the `dqi-v8` pooled price.

#### Scenario: Limit missed

- **WHEN** the pooled price exceeds the limit
- **THEN** `dqi-v8` remains the DQI member
