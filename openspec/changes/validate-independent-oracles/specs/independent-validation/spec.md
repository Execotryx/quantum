## ADDED Requirements

### Requirement: Evidence for all three independent references
The validation run SHALL compare the independent references with pinned official behavior and retain input identities, coverage, discrepancies and justified numerical tolerances.

#### Scenario: Validation of original reference data
- **WHEN** the local reference suite executes
- **THEN** it records full-domain phase and pricing checks, field and decoding controls, statistical costs, and reconstructed chemistry quantities and resource terms

### Requirement: Evidence for defect detection and composition
The gate SHALL require expected and observed diagnostics on known-invalid inputs and scoped evidence for corrected phase, preserved registers, clean ancillas and composition.

#### Scenario: A mutant fails an unrelated check
- **WHEN** the observed failure differs from the expected detector
- **THEN** the control remains unresolved and the affected gate stays open
