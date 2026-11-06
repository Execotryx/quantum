## ADDED Requirements

### Requirement: Benchmark-scoped confirmation

The candidate SHALL require one passing unused confirmation for each generated
benchmark. Each record SHALL bind the benchmark, full component manifest,
contract, pinned runtime, registered seed and actual verifier receipt. The
one-use ledger SHALL reject duplicate salts and repeated confirmation of an
unchanged component even when other components change.

#### Scenario: Partial hybrid confirmation
- **WHEN** inverse square root is confirmed and chemistry is missing, failed or consumed
- **THEN** release selection is blocked and both histories remain available

#### Scenario: Legacy single-benchmark record
- **WHEN** an existing single-benchmark record is loaded
- **THEN** its status, salt reservation and terminal evidence retain their original meaning

### Requirement: Combined extracted archive certificate

The certificate SHALL require independent matching rebuilds, complete full-strength
results on the exact extracted ZIP, and substantive evidence for both optimized
components. Retained files SHALL match accepted hashes.

#### Scenario: Chemistry bytes change after confirmation
- **WHEN** any angle circuit or bound factorization differs
- **THEN** the chemistry confirmation cannot certify the new archive

#### Scenario: Both improvements pass
- **WHEN** all three full-strength coverage counts match and both generated
  components improve their accepted costs
- **THEN** the local certificate records both confirmations, all costs, the
  aggregate score and the exact archive hash
