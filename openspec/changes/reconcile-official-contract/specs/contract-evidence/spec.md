## ADDED Requirements

### Requirement: Validate every supporting source

The contract validator SHALL reject a reconciled field when its primary or any
declared supplementary source lacks its location or has missing/changed bytes.
It SHALL also validate all declared source roles, including additional source
roles beyond the mandatory minimum.
Resolved critical discrepancies SHALL carry an explicit resolution and unchanged
source evidence with a location.

#### Scenario: Imported constant changes

- **WHEN** a metric imports a dimension from a separately pinned verifier file
  and that file changes while the metric remains unchanged
- **THEN** contract validation reports changed supplementary provenance

### Requirement: Preserve measured baseline gates

The contract SHALL NOT treat source inspection or a bounded smoke check as full
baseline acceptance or completed component profiles.

#### Scenario: Full execution is incomplete

- **WHEN** source conventions are reconciled but full baseline execution is pending
- **THEN** baseline evidence remains unresolved and release promotion remains blocked

### Requirement: Map disjoint failure counters

The official adapter SHALL support summing a nonempty list of distinct failure
counter paths, reject negative/noninteger counters and reject totals above shots.

#### Scenario: DQI returns separate value and phase errors

- **WHEN** the official result reports two value errors and three disjoint phase
  errors over 102400 shots
- **THEN** confirmation observes exactly five failures over 102400 shots

### Requirement: Preserve completed benchmark receipts

The official worker SHALL preserve each actual completed benchmark return and its
elapsed wall time before the overall metric finishes, without asserting overall
metric completion from an individual receipt.

#### Scenario: Later benchmark is interrupted

- **WHEN** one benchmark returns and a later benchmark is interrupted
- **THEN** the completed benchmark receipt remains available and the overall
  verification remains incomplete
