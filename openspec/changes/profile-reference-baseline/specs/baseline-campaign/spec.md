## ADDED Requirements

### Requirement: Clean committed execution

Campaign execution SHALL use a clean Git checkout, a recorded source revision and
dependency lock, and original hash-verified reference bytes. It SHALL refuse dirty
source or incompatible configuration rather than label it clean.

#### Scenario: Development checkout has local edits

- **WHEN** a campaign is requested from dirty source
- **THEN** execution is refused and the existing edits are preserved

### Requirement: Observe actual stages and resources

Profiling SHALL delegate to the pinned upstream readers/verifiers without changing
their arguments, returns, exceptions, coverage or scoring. It SHALL separate
parsing, hashing and verification stage records and measure external process-tree
memory, wall/CPU time, I/O and retained disk use with explicit units and limitations.

#### Scenario: Forked workers share circuit memory

- **WHEN** process-tree memory is sampled during parallel verification
- **THEN** PSS and RSS are distinct measurements and summed RSS is not represented
  as unique physical memory

### Requirement: Preregister repeatability

The campaign SHALL freeze the source/configuration and A,A,B salt sequence before
three serial full-strength runs. It SHALL check full coverage and actual completed
reports, require equal same-salt costs, and preserve failed/incomplete evidence.

#### Scenario: A process exits without complete counters

- **WHEN** the process stops without its complete full-strength verification report
- **THEN** the run is incomplete and cannot satisfy the campaign

### Requirement: Evidence-based budgets and frozen bundle

A completed campaign SHALL record exact score normalization, observed cost/runtime
ranges, measured hardware conditions and explicit planning headroom. Its versioned
bundle SHALL bind source, lock, original inputs, profiles and raw diagnostics by
hash, produce identical independent builds and pass member integrity verification.

#### Scenario: Archived diagnostic bytes change

- **WHEN** a frozen member differs from its manifest digest
- **THEN** bundle verification rejects it
