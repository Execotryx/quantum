## ADDED Requirements

### Requirement: Prove trimmed bits remain zero

A narrower inverse-square-root circuit SHALL reject coefficient tables that do
not fit its registers, and SHALL check every modeled intermediate subtraction and
output shift across the complete verifier input domain before promotion.

#### Scenario: An intermediate would wrap

- **WHEN** any checked intermediate exceeds its narrower register
- **THEN** the candidate fails before it can be promoted

### Requirement: Independent confirmation of new bytes

A trimmed circuit SHALL use a separately registered full verifier run and fresh
one-use confirmation on identical KMB bytes. The confirmed parent and its
chemistry and DQI member hashes SHALL remain intact in the paired archive.

#### Scenario: The parent was previously confirmed

- **WHEN** the new trimmed KMB differs from its confirmed parent
- **THEN** the earlier confirmation cannot be reused for the new KMB
