## ADDED Requirements

### Requirement: Stage-attributed reference profile

The project SHALL measure the reference DQI decoder's Toffoli-like gates,
other gates and live width per registered stage at reduced and full size.
Every gate-emitting reference method SHALL map to a registered stage.

#### Scenario: An unmapped method emits gates

- **WHEN** a reference method outside the stage map emits gates
- **THEN** the profile run fails and the stage map is extended before rerunning

#### Scenario: The proxy changes the circuit

- **WHEN** the circuit emitted through the profiling proxy differs from the reference hash
- **THEN** the profile is rejected

### Requirement: Static and executed reconciliation

The static per-stage total SHALL be reconciled with the verifier's mean
executed Toffoli-like count on a matched shot sample, and the residual
SHALL be reported.

#### Scenario: The residual is larger than conditional variation

- **WHEN** the static total and the executed mean differ by more than the observed maximum-minus-mean spread
- **THEN** the counting definition is rechecked against the verifier before any decision

### Requirement: Decision record for decoder build order

The profile SHALL produce a decision record that fixes the build order of
the next DQI decoder from the measured stage shares.

#### Scenario: The locator dominates

- **WHEN** the forward and reverse locator account for at least 60% of Toffoli-like gates
- **THEN** the routed Berlekamp–Massey locator is built before the phase-only scan
