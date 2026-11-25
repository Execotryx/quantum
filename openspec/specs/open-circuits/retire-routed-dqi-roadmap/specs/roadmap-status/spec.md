## ADDED Requirements

### Requirement: Pause before retirement

Each listed change SHALL be marked `paused` first. It SHALL be marked
`superseded` only after its replacement member is banked, with that
member's name and hash in the status line.

#### Scenario: Replacement not yet banked

- **WHEN** the replacement member of a group has not been banked
- **THEN** no change of that group carries the `superseded` status

#### Scenario: Replacement ends in `no_go`

- **WHEN** a group's trigger change records `no_go`
- **THEN** the group's changes are marked `resumed` and may be implemented again

### Requirement: Evidence is kept

A paused or superseded change SHALL keep its files, code references and
evidence.

#### Scenario: Completed change

- **WHEN** a listed change is archived or fully checked
- **THEN** it is left unchanged and noted in the status record

### Requirement: Round-11 routed changes follow the group status

A round-11 routed-decoder or chemistry-lane change SHALL NOT be imported
while its group is `paused` or `superseded`.

#### Scenario: DQI group resumed

- **WHEN** the DQI group is marked `resumed`
- **THEN** the round-11 routed-decoder changes become eligible for import
