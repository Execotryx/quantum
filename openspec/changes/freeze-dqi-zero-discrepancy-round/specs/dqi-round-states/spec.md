## ADDED Requirements

### Requirement: Zero-discrepancy counter increment

A routed BM round with `Δ = 0` SHALL leave the locator unchanged, relabel
the template by decrementing the classical offset, increment the signed
counter by one, and leave the branch bit and history word at zero.

#### Scenario: Zero discrepancy with a wrapped nonzero word

- **WHEN** a round has `Δ = 0` and the wrapped word `T₀` is nonzero
- **THEN** the forward output matches the frozen zero-case state with `d' = d + 1`, and the reverse restores the input with all scratch zero

#### Scenario: The counter is left unchanged

- **WHEN** a mutation leaves the counter unchanged on a zero round
- **THEN** the native comparison with the frozen states fails

### Requirement: Circular classical model

The project SHALL provide a classical circular model whose template state
equals the fold of the unbounded routed template on every correctable input.
It SHALL reject a nonzero discrepancy with a nonzero wrapped `T₀`.

#### Scenario: A sampled correctable input

- **WHEN** a seeded correctable `(4095, 70)` input runs through both models
- **THEN** every round's circular state equals the folded unbounded state, and no unsupported round occurs

### Requirement: Frozen fixture file

Expected forward and reverse states SHALL be stored once in a fixture file
whose SHA-256 is recorded. Tests SHALL regenerate and compare it byte for byte.

#### Scenario: The model changes behavior

- **WHEN** a code change alters any frozen state
- **THEN** the fixture comparison fails
