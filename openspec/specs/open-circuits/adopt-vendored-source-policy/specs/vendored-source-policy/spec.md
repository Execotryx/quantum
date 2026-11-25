## ADDED Requirements

### Requirement: Apache 2.0 licence file

The repository root SHALL contain a distinct file named `LICENSE` holding
the complete, unmodified text of the Apache License, Version 2.0, from the
title through the appendix. No other content SHALL be added to that file.
Its SHA-256 SHALL be recorded in `third_party/licenses.json`, and
`pyproject.toml` SHALL declare `license = "Apache-2.0"` with `LICENSE` in
`license-files`.

#### Scenario: Licence text altered

- **WHEN** the `LICENSE` bytes differ from the recorded SHA-256
- **THEN** the third-party test fails

#### Scenario: Licence missing from the build

- **WHEN** `uv build` produces a distribution without `LICENSE`
- **THEN** the task is not complete

### Requirement: Vendored component provenance

Each vendored component SHALL live in `third_party/<component>/` with its
upstream licence, any upstream notice, a `SOURCE.json` with per-file
SHA-256, and unmodified upstream files. The root `NOTICE` SHALL credit it.

#### Scenario: Vendored file edited

- **WHEN** a file under `third_party/` differs from its recorded hash
- **THEN** the test fails and the component cannot be used

### Requirement: Admission checks

A component SHALL be admitted only with an explicit Apache-2.0 licence at
its origin, its generating source, pinned bytes, no competition data, and
no denylist match.

#### Scenario: Binary-only circuit

- **WHEN** a candidate provides a `.kmb` without generating source
- **THEN** it is not admitted as an archive member

#### Scenario: Denylisted lineage

- **WHEN** a candidate derives from the 891-qubit `993c70386a3d` DQI lineage or the unlicensed Schur decoder
- **THEN** it is rejected and the reason is recorded

### Requirement: Regeneration by our pipeline

An admitted component SHALL become an archive member only after our
pipeline rebuilds it from the vendored source. A rebuilt circuit SHALL equal
the hash the origin publishes at the pinned revision, when one exists.

#### Scenario: Rebuilt circuit differs from the origin hash

- **WHEN** a rebuilt `.kmb` differs from the origin's published hash
- **THEN** the candidate is excluded and the difference is recorded

### Requirement: Spec hash prefixes are hints

Hash prefixes quoted in OpenSpec changes SHALL NOT be used as acceptance
criteria. The origin's published hash, recorded at admission, SHALL be the
comparison value.

#### Scenario: Hint disagrees with the origin

- **WHEN** the origin's published hash differs from a prefix quoted in a change
- **THEN** `hint: mismatch` is recorded and the candidate continues with the origin hash

### Requirement: Floating-point table exception

A rebuilt floating-point table that is not bit-identical SHALL be handled
by the single equivalence rule: both tables verified, `λ_eff` within
1×10⁻⁶ relative for `equivalent`, otherwise the rebuilt table if it passes.

#### Scenario: Divergent rebuild that passes

- **WHEN** the rebuilt table passes but differs from the published table by more than the tolerance
- **THEN** the rebuilt table is the member and `divergent_rebuild` is recorded
