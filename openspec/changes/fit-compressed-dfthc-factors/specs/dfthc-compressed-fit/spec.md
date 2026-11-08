## ADDED Requirements

### Requirement: Joint basis and weight optimization

A compressed-shape fit SHALL optimize the basis vectors and the weights
together, with unit-norm vectors and gradients verified against finite
differences. A fit that holds the basis fixed SHALL NOT be used to reject
a shape.

#### Scenario: A weight-only fit fails a shape

- **WHEN** a shape has only weight-only fit records
- **THEN** the shape is treated as untested and is refit jointly before any shape decision

### Requirement: Budgets set from profiling

Evaluation caps SHALL be set after profiling a full-size objective and
gradient. A capped fit that is still improving SHALL be recorded as
`budget_limited`.

#### Scenario: A fit reaches its cap while improving

- **WHEN** the cap ends a fit whose objective fell by at least 1% over its last quarter
- **THEN** the run is `budget_limited` and the shape stays open

### Requirement: Pinned objective terms

`Λ`, `E_SOS`, `E_gap` and `λ_eff` SHALL be computed by the pinned
evaluator code at every checkpoint. Smoothed forms MAY be used only
for gradients.

#### Scenario: Smoothed and pinned values disagree

- **WHEN** a checkpoint's smoothed `λ_eff` differs from the pinned value by more than `1e-6` relative
- **THEN** the pinned value is recorded and used for every decision

### Requirement: Quantization with full weight refit

Each quantization step SHALL reconstruct decoded vectors, refit all
weights against them, regenerate one-body words, and pass both decoded
residuals at 19.5 mHa or less with the `Λ` and `E_gap` margins.

#### Scenario: An 8-bit step breaks the residual margin

- **WHEN** the decoded two-body residual exceeds 19.5 mHa after the 8-bit refit
- **THEN** the ladder stops at the last passing precision and that precision is handed off

### Requirement: Eligible factorization handoff

An eligible factorization SHALL be exported in the strict canonical NPZ
layout with its word table, tree, pinned metrics and expected coverage
`(76 + R·B) · 64`.

#### Scenario: A factorization passes all margins

- **WHEN** a quantized factorization passes all decoded gates and margins
- **THEN** it is exported and registered as input to loader synthesis
