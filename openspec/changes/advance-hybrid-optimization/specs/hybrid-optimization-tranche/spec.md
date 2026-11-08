## ADDED Requirements

### Requirement: Measured comparison to the verified control

The campaign SHALL bind the verified v2 archive and raw component
receipts before measuring new candidates. Projected gains SHALL be kept
separate from actual verifier costs and aggregate results.

#### Scenario: A candidate passes its development screen

- **WHEN** the candidate passes a reduced, modeled or alternate-engine screen
- **THEN** it is eligible for official verification using its frozen bytes and does not satisfy the full verification requirement

### Requirement: Independent generation and bounded experimental lanes

Each lane SHALL register its derivation sources, artifact hashes, limits,
comparison controls, correctness assumptions and decision thresholds.

#### Scenario: A method would reuse a third-party artifact

- **WHEN** an experiment would import third-party KMB bytes, factor weights or a generator into the candidate
- **THEN** the independent-generation lane excludes it and records that a distinct provenance decision would be needed

#### Scenario: An approximation would change semantics

- **WHEN** a DQI shortcut discards supported input cases or changes the phase contract
- **THEN** it is considered only after an exact implementation qualifies and under a separately registered, quantitative error budget

### Requirement: Bound verification and archive comparison

An archive comparison SHALL use separately verified and confirmed
changed components, full per-benchmark coverage, and matched evidence
for retained components.

#### Scenario: A chemistry candidate changes the shape

- **WHEN** the candidate changes the rank or basis count in the frozen factorization
- **THEN** full chemistry coverage is independently computed from the new shape and bound to the NPZ and complete ANGLE family

#### Scenario: No replacement qualifies

- **WHEN** a lane fails its correctness or cost gate or reaches its registered budget
- **THEN** the campaign records its disposition and uses the existing verified component
