## ADDED Requirements

### Requirement: One member per release

Each release SHALL change exactly one member relative to the last
certified archive, and SHALL retain the other members by hash.

#### Scenario: Two members are ready at once

- **WHEN** two changes promote members on the same day
- **THEN** they enter consecutive releases in the order of the release table

### Requirement: Receipt per release

Each certified release SHALL be uploaded with a hash-bound message, and
its receipt SHALL be recorded and reconciled before the next release is
uploaded.

#### Scenario: A receipt is out of band

- **WHEN** a receipt falls outside its reconciliation band
- **THEN** no further release is uploaded until the cause is recorded

### Requirement: Freeze and final selections

No new member SHALL enter after 13 January 2027. The final selections
SHALL be the best reconciled archive and the best archive with an exact
DQI member.

#### Scenario: The best archive has a bounded DQI history

- **WHEN** the best reconciled archive uses a bounded-history DQI decoder
- **THEN** the second selection is the best certified archive with an exact DQI member
