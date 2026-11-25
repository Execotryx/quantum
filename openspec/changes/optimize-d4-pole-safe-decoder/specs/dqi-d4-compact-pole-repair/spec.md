## ADDED Requirements

### Requirement: Reproduce and classify the full-grid value failures

The diagnostic SHALL bind the original full-grid KMB, official verifier,
backend inventory, draw salts and receipts. It SHALL preserve the historical
results and classify syndrome restoration, scratch and deliberate rejection
flags separately.

#### Scenario: Replaying the two value-error draws

- **WHEN** the exact original draws are replayed
- **THEN** the diagnostic records receipt equality, failing shot offsets, batch and simulator seeds, and nearby passing controls
- **AND** it records a reproduced cause or the first boundary that remains unexplained

### Requirement: Preserve coherent phase and reversible cleanup within a compact decoder

The candidate SHALL implement the prescribed phase with clean syndrome, masks
and workspace for its supported inputs. It SHALL document pole, termination and
unsupported-case behavior, demonstrate forward and inverse identities, and
preserve verifier-visible failure semantics for unsupported cases.

#### Scenario: Finite paths, poles and termination

- **WHEN** a candidate changes the extraction, conversion or scan interface
- **THEN** the checked intermediate representation matches an independent oracle including representative weight-34 and weight-35, intermediate-pole, local-pole and terminating inputs
- **AND** forward and inverse native tests cover alternate masks, measurement outcomes, and negative controls for branch selection and phase repayment

### Requirement: Record provenance and measure candidates before full pricing

The screen SHALL bind source, backend, implementation and candidate bytes.
New open-source components SHALL pass existing admission policy before use.
The screen SHALL measure declared width, peak live qubits, static gates and
mean executed Toffoli-like gates. It SHALL use the pinned pooled metric and a
preregistered comparison against banked D4.

#### Scenario: Candidate misses the preflight gate

- **WHEN** a native candidate fails the matched correctness gate or fails to meet the specified resource screen
- **THEN** the report retains its evidence and the campaign does not use that candidate for full pricing

### Requirement: Price and retain the frozen result

The full-strength comparison SHALL use two byte-identical builds of the
candidate, all historical matched batches, and eight fresh preregistered
official draws per role. Every official draw SHALL be kept separately with its
error counts and original circuit identity.

#### Scenario: Comparing the fully verified candidate

- **WHEN** all full draws complete for both the candidate and banked D4
- **THEN** the report records per-draw verifier status, disjoint error counts, complete pooled prices and the selection decision
- **AND** any proposed replacement requires a strictly lower pooled cost plus the prescribed correctness gates
