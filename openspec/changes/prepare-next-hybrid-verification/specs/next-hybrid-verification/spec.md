## ADDED Requirements

### Requirement: Artifact-bound full coverage

Release and confirmation SHALL compare actual raw counts to independently
derived expected counts bound to the frozen component. Legacy certificates
SHALL retain their original expectations and semantics.

#### Scenario: Chemistry shape changes

- **WHEN** the candidate's validated NPZ changes R or B
- **THEN** its expected chemistry coverage follows the pinned verifier shape and its old confirmation is ineligible

#### Scenario: Reduced tier passes its numerical guard

- **WHEN** a development-tier result has acceptable cost and sample counters
- **THEN** it can qualify for full verification and cannot fulfill the release coverage requirement

### Requirement: Scoped release lineage

An assembled release SHALL require a distinct unused confirmation for
each newly generated benchmark and a matching certified or official
reference identity for every retained component.

#### Scenario: Retained DQI cost changes across salts

- **WHEN** identical retained DQI bytes have different sampled costs against the historical parent
- **THEN** both observations are preserved and a bound matched archive replay must reconcile them before attributing the improvement

#### Scenario: Retained chemistry confirmation is consumed or its NPZ changes

- **WHEN** a successor points to invalid or differently scoped chemistry evidence
- **THEN** release selection is blocked without reserving a replacement confirmation on the unchanged scope

### Requirement: Source-reconciled package and decision

The local release SHALL pass pinned package preflight, two independent
deterministic builds and the complete metric on a fresh extraction.

#### Scenario: Packaging limits are exceeded

- **WHEN** the archive violates an official pinned preflight condition
- **THEN** verification and release fail closed with a reproducible diagnostic

#### Scenario: No research lane qualifies

- **WHEN** each prospective screen rejects or remains unresolved
- **THEN** the incumbent remains the locally certified release and the campaign retains the measured dispositions
