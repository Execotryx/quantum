## ADDED Requirements

### Requirement: Cost selection uses admitted component evidence

The above-36 portfolio workflow SHALL bind each component to its exact source lineage and two independent build receipts, and SHALL use full development costs with a role-appropriate error adjustment.

#### Scenario: A component has incomplete source or verifier evidence

- **WHEN** the emitting source, independent build, phase correctness, or complete component price is missing
- **THEN** the workflow retains the result as development evidence
- **AND** it skips archive promotion for that component

#### Scenario: Combined measured development budgets fall short

- **WHEN** conservative complete component costs do not clear 36
- **THEN** the workflow calculates the break-even cost with measured companions
- **AND** it records the next bounded correction before spending on release verification

### Requirement: Two complete archive verifications each exceed 36

The workflow SHALL certify the above-36 portfolio only from distinct fresh registered salts and two complete verifier reports for byte-identical archives, with each recomputed score strictly above 36.

#### Scenario: Both complete full-strength roles pass

- **WHEN** each fresh extraction matches the registered members and the pinned verifier completes all required coverage
- **THEN** the workflow recomputes both benchmark cost products against the strict score ceiling
- **AND** it publishes the evidence and comparison for the archive when both roles exceed 36

#### Scenario: A role equals 36 or misses a verification requirement

- **WHEN** either score is at most 36, or its report, source lineage, archive identity, or coverage differs from the registration
- **THEN** the workflow retains the receipt and records the failed gate
- **AND** it keeps certification pending
