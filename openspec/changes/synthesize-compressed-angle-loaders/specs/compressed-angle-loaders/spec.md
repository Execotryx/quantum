## ADDED Requirements

### Requirement: Shape-generic ANGLE family

Loaders SHALL be generated for any eligible `(R, B, C)`, `brot` and `J`.
They SHALL keep contiguous indices, identical register maps, no `Z_POW`,
at most 128 qubits per circuit and clean workspace on every valid address
in both directions.

#### Scenario: A layout exceeds the cap

- **WHEN** a proposed `J` makes any ANGLE circuit wider than 128 qubits
- **THEN** the layout is rejected before emission

### Requirement: Complete-cost ranking of layouts

Loader layouts SHALL be ranked by complete chemistry cost
`λ_eff · T_total · Q_total`, computed with the pinned cost code, including
the persistent width added by each word.

#### Scenario: Larger batches add persistent width

- **WHEN** a larger `J` lowers ANGLE Toffolis but adds persistent qubits
- **THEN** the choice follows the complete cost, not the Toffoli count alone

### Requirement: Verified don't-care use

Invalid addresses SHALL be treated as don't-cares only after the pinned
verifier is shown never to check them.

#### Scenario: The verifier checks an address assumed free

- **WHEN** evidence shows the verifier evaluates an address at or above `A`
- **THEN** don't-care minimization is disabled and loaders are regenerated

### Requirement: Measurement-erased monomials

Monomial loaders SHALL erase each constructed product by X-basis
measurement with a CZ fix-up between still-live factors. They SHALL
restore the correct phase for every measurement outcome.

#### Scenario: A fix-up is omitted

- **WHEN** a mutation removes one CZ fix-up
- **THEN** the native phase check fails

### Requirement: Chemistry promotion

A new chemistry component SHALL pass the complete metric with full
coverage `(76 + R·B) · 64`, two identical builds and a fresh one-use
confirmation. Its measured cost SHALL be at most half the banked
incumbent.

#### Scenario: The banked unary loader qualifies first

- **WHEN** the Stage A family meets every gate at or below 1.624×10⁹
- **THEN** it becomes the chemistry component of the next paired archive while monomial loaders continue
