## ADDED Requirements

### Requirement: Confirmed single-benchmark release

The release SHALL generate only the selected inverse-square-root KMB and SHALL
bind its confirmation to the exact artifact, registered protocol and pinned
verifier evidence. Retained DQI and chemistry bytes SHALL match the accepted
reference.

#### Scenario: Confirmation evidence cannot be reconciled
- **WHEN** a receipt has changed bytes, missing coverage or unavailable seed history
- **THEN** selection remains blocked and the evidence is retained for review

### Requirement: Reproducible extracted ZIP verification

Two independent recipe builds SHALL produce identical archives. The pinned
full metric SHALL verify a fresh extraction and the local certificate SHALL
bind the exact ZIP hash, measured costs and coverage.

#### Scenario: Extracted archive passes
- **WHEN** all three components complete their full trajectories and the cost improves
- **THEN** record local acceptance with the full receipts and certificate
