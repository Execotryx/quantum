## ADDED Requirements

### Requirement: Exact emitted phase and reversible arithmetic

The workflow SHALL model the emitted fixed-width arithmetic, verify all
legal inputs under the pinned circular phase tolerance, and reconcile
native phase, restored input and clean scratch on reloaded KMB bytes.

#### Scenario: An accumulator overwrite loses state

- **WHEN** a proposed layout cannot reverse a multiplication, truncation or normalization step on every legal path
- **THEN** the candidate is rejected regardless of its modeled width

### Requirement: Compare to the certified direct incumbent

Promotion SHALL price the complete verifier cost and require full
verification and independent fresh confirmation of a frozen improvement
over the current certified inverse-square-root circuit.

#### Scenario: A variant beats Newton and loses to direct phasing

- **WHEN** a variant improves the historical Newton control but misses the direct-incumbent cost gate
- **THEN** it remains in the report as ineligible for promotion
