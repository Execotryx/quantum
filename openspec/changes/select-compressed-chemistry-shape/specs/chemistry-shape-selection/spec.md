## ADDED Requirements

### Requirement: Lane qualification

A lane SHALL qualify only with a continuous residual of at most 19.0 mHa
and a 12-bit decoded two-body residual of at most 19.5 mHa. If none
qualifies, selection SHALL stop.

#### Scenario: Only one lane qualifies

- **WHEN** exactly one lane passes both gates
- **THEN** it is selected, and its projected cost is still recorded

### Requirement: Complete projected cost

Each qualifying lane SHALL be costed as `λ_proj · T · Q` with the pinned
resource function. `λ_proj` comes from offset restoration under the
preregistered settings. `T` and `Q` come from natively verified 8-bit
banked families over every batch and bank split in `{4, 5, 6}`. ANGLE
Toffolis SHALL be included for both passes.

#### Scenario: A shape with fewer rows but higher λ

- **WHEN** one lane has fewer lookup rows but a higher `λ_proj` than another
- **THEN** the lane with the lower complete product is selected, not the one with lower preparation and rotation Toffolis

#### Scenario: Restoration fails for a lane

- **WHEN** offset restoration does not return `restored` for a qualifying lane
- **THEN** that lane is excluded and the reason is recorded

### Requirement: Tie rule

Equal projected costs SHALL be broken by the lower 12-bit decoded
two-body residual, then by lane letter.

#### Scenario: Two lanes tie on cost

- **WHEN** two lanes have identical projected costs
- **THEN** the lane with the lower decoded residual is selected
