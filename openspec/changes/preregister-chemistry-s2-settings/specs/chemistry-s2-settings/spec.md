## ADDED Requirements

### Requirement: Explicit S2 settings

S2 SHALL use `penalty = 1.0` and
`offset_bound = max(1.0, ⌈4·m_ref⌉/2)`, where `m_ref` is the largest
reference identity-offset magnitude. Both values SHALL be recorded before
any lane is selected or any restoration runs.

#### Scenario: Settings are missing

- **WHEN** an S2 or restoration run starts without a recorded settings record
- **THEN** the run is refused

### Requirement: Bound S2 plan

The S2 plan SHALL bind the selected lane's vectors, weights, checkpoint
receipt, S1 decision, target pin, reference NPZ and limits by SHA-256.
The run SHALL receive the plan's own hash.

#### Scenario: The checkpoint changes after registration

- **WHEN** the lane checkpoint bytes differ from the hash in the plan
- **THEN** `chem_s2.py` refuses the plan

### Requirement: Single bound contingency

If restored offsets reach 99% of `offset_bound`, exactly one rerun SHALL be
allowed, with twice the bound. A second active bound SHALL end S2 as
`budget_limited`.

#### Scenario: The bound is active twice

- **WHEN** both the first run and the rerun reach 99% of their bounds
- **THEN** S2 is recorded as `budget_limited` and no further run starts
