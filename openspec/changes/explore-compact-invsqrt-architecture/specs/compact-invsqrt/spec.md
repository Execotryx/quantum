## ADDED Requirements

### Requirement: Scoped compact architecture research

The compact inverse-square-root tranche SHALL be separately registered with a
40-engineering-hour stop and a measured certified control. The resource target
SHALL be at most 100 declared qubits and 2,000 rotation-inclusive
Toffoli-equivalents, without treating a register-count estimate as a proof.

#### Scenario: Gradient resources are unpriced

- **WHEN** gradient preparation, accumulation or cleanup costs are unknown
- **THEN** the record identifies them as unmodeled and does not claim a candidate cost

### Requirement: Model gate before prototype

A compact prototype SHALL be emitted only after a complete model predicts at
least 20 percent lower cost than the certified control. Independent components
SHALL each improve before their combination and the complete model SHALL include
peak workspace, rotation synthesis and gradient preparation.

#### Scenario: Bookkeeping alone suggests a narrower design

- **WHEN** output-register width is subtracted without accounting for peak lifetimes
- **THEN** the result remains bookkeeping and does not authorize a prototype
