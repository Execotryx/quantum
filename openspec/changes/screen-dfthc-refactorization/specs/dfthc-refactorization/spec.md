## ADDED Requirements

### Requirement: Decoded factorization feasibility

Each candidate SHALL satisfy the pinned schema and both numerical
residuals, gap and normalization conditions after quantization and
word decoding before native synthesis.

#### Scenario: A continuous fit fails after quantization

- **WHEN** decoded vectors exceed a required residual or leave the permitted gap domain
- **THEN** the candidate is rejected with its continuous and decoded evidence retained

### Requirement: Shape-aware exact loader and coverage

The emitted family SHALL load the frozen table with exact XOR semantics,
clean scratch and phase, and at most 128 qubits per ANGLE circuit.
Full verification SHALL measure coverage derived from the exact
candidate NPZ shape.

#### Scenario: The new factorization changes the address domain

- **WHEN** a changed shape has fewer or more valid addresses than the incumbent
- **THEN** native fixtures and expected full coverage follow that shape and the old chemistry receipt cannot certify it
