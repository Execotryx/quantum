## ADDED Requirements

### Requirement: Exact block updates

Each sweep SHALL apply an orthogonal Procrustes alignment, a per-group
least-squares weight solve, and a per-vector top-eigenvector update. None
of the three SHALL increase the surrogate objective on the synthetic test
instance.

#### Scenario: A planted factorization

- **WHEN** the method starts from a perturbation of an exact synthetic factorization
- **THEN** it recovers the target rows to `1e-8` relative error

### Requirement: True residual decides

Checkpoints SHALL be selected by the true residual `‖H − XᵀX‖` computed
with the existing function, not by the surrogate.

#### Scenario: The surrogate falls while the true residual rises

- **WHEN** a later sweep has a lower surrogate but a higher true residual
- **THEN** the earlier checkpoint remains the lane's best

### Requirement: Fixed lanes and budgets

The change SHALL run exactly four lanes: shapes `(9, 143, 40)` twice,
`(10, 129, 40)` and `(9, 129, 40)`. Each runs 400 sweeps and 3,000 polish
evaluations, and no further lanes run within the change.

#### Scenario: No lane passes

- **WHEN** every lane ends above the continuous or decoded gate
- **THEN** the change records each outcome and stops without launching new lanes

### Requirement: Handoff gate

A factorization SHALL be handed off only with a continuous residual at or
below 19.0 mHa and a 12-bit decoded two-body residual at or below 19.5 mHa.

#### Scenario: Two lanes pass

- **WHEN** two lanes pass both gates
- **THEN** the lane with the lower complete projected 8-bit cost under `select-compressed-chemistry-shape` is exported
