## ADDED Requirements

### Requirement: Each portfolio candidate has reproducible evidence

The portfolio workflow SHALL pin candidate source and artifact hashes, demonstrate independent exact circuit builds and retain the full official verifier observations used to select each benchmark.

#### Scenario: Published result has incomplete generating source

- **WHEN** a public artifact provides a benchmark cost with no recoverable exact generator
- **THEN** the workflow records the artifact as a comparison reference
- **AND** any promoted replacement has its own reproducible source and verification evidence

### Requirement: Full measurements establish the score threshold

The workflow SHALL bind the archive and both distinct registered salts to complete full-strength metric and confirmation reports with an aggregate strictly above 34 on each.

#### Scenario: Complete metric and confirmation pass from separate extractions

- **WHEN** both fresh extractions match the registered member hashes and complete all coverage defined by the pinned verifier
- **THEN** the workflow independently recomputes the aggregate scores from the official benchmark costs
- **AND** it certifies the registered archive only if both exceed 34

#### Scenario: A result misses coverage or score

- **WHEN** either report lacks its complete registered coverage or the aggregate is at most 34
- **THEN** the workflow retains the receipt and records the failed gate
- **AND** the portfolio remains unqualified
