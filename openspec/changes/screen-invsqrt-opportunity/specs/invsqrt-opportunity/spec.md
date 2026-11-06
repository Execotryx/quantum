## ADDED Requirements

### Requirement: Prospective bounded screen

The screen SHALL pin the protocol and source identities before execution, retain
each attempt, and apply the registered eligibility and selection rules.

#### Scenario: Reference control and parallel trials

- **WHEN** the reference control reproduces the accepted hash and complete cost
- **THEN** the two registered candidates execute concurrently in separate output
  directories and selection uses the complete attempt ledger and shared budget

### Requirement: Frozen winner verification

The qualifying candidate SHALL undergo full-strength benchmark verification
and independent confirmation against the same frozen artifact hash.

#### Scenario: Full verification passes

- **WHEN** a qualifying candidate passes full coverage and lowers measured cost
- **THEN** fresh preregistered confirmation runs separately on the same bytes
  and the two receipts remain distinct
