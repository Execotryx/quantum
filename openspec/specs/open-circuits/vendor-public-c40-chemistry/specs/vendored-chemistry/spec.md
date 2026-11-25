## ADDED Requirements

### Requirement: Fixed chemistry pairings

Only pairings P1 (C40 table with paired-product loaders) and P2 (EigenOS
v7 table and loaders) SHALL be considered. Each SHALL be regenerated from
vendored source by our pipeline, with two builds giving identical member
hashes.

#### Scenario: Generating source missing

- **WHEN** the generating source of a pairing's table or loaders cannot be vendored
- **THEN** that pairing is recorded as a hash reference only and is not a candidate

#### Scenario: Table rebuild not bit-identical

- **WHEN** a rebuilt table differs from the origin's published bytes
- **THEN** the floating-point exception of the vendored-source policy decides which bytes are the member

### Requirement: Official constraints

A pairing SHALL be eligible only if ε₁ and ε₂ are each at most 20 mHa, Λ
exceeds 49.0, `E_gap` exceeds 3.914898, every ANGLE circuit uses at most
128 qubits, and no ANGLE circuit contains Z_POW.

#### Scenario: Constraint failure

- **WHEN** a pairing fails any constraint on the official verifier
- **THEN** it is excluded, and if none remains the v6 chemistry members are retained

### Requirement: Lowest-cost selection

The eligible pairing with the lowest verified cost SHALL be banked as
`chemistry-v8`, with ties broken by fewer qubits.

#### Scenario: Both pairings pass

- **WHEN** P1 and P2 both pass
- **THEN** the one with the lower verified cost is banked
