## ADDED Requirements

### Requirement: Calibrated cost model before emission

Variants SHALL be ranked by a cost model calibrated against emitted
circuits. The model SHALL predict Toffoli-like counts within 2% and
declared width exactly on every calibration circuit before it is used.

#### Scenario: The model drifts from an emitted circuit

- **WHEN** a newly emitted circuit differs from its prediction by more than 2% in Toffoli-like gates or by any qubit
- **THEN** ranking stops until the model is recalibrated and the residual is recorded

### Requirement: Lattice-aware coefficient rounding

Coefficient tables SHALL be chosen by an exact per-segment search over
nearby integers using the emitted recurrence. A width step SHALL be
declared failed only after that search.

#### Scenario: A narrower width fails with nearest rounding

- **WHEN** a width step fails tolerance with nearest-rounded coefficients
- **THEN** the per-segment search runs before the step is recorded as failed

### Requirement: Exact model for new row arithmetic

A variant that changes row arithmetic, including signed-digit rows,
SHALL have its exact recurrence in the integer model. It SHALL pass
all 3,133,452 inputs with zero failures and at most 90% tolerance use
before native emission.

#### Scenario: Signed rows change truncation

- **WHEN** signed-digit rows change how partial products are truncated
- **THEN** the full-domain model is rerun with the new recurrence and the worst witnesses are recorded

### Requirement: Model-only screens close explicitly

Screens expected to lose under the exchange rate SHALL be modeled and
closed with a recorded result unless the model predicts at least 3%
lower complete cost.

#### Scenario: The two-octave table loses in the model

- **WHEN** the extra controlled rows cost more than the removed lookup rows
- **THEN** the screen is closed with its model record and no circuit is emitted

### Requirement: Promotion

A combined variant SHALL lower measured complete cost by at least 5%
against the current certified control. It SHALL pass native fixtures,
a full official pass and a fresh one-use confirmation on identical bytes.

#### Scenario: Two variants each lower cost

- **WHEN** two variants each lower cost on their own and the combination passes all gates
- **THEN** the combination becomes the candidate for the next paired archive
