## ADDED Requirements

### Requirement: Liveness evidence before width claims

A width-reduction candidate SHALL be preceded by a per-call liveness
trace and an op-stream interval analysis of the control circuit.
Boundary-only samples SHALL NOT be used to claim reclaimable width.

#### Scenario: The trace finds the peak inside a primitive

- **WHEN** the per-call trace reaches the declared width inside a pinned primitive
- **THEN** the gap is classified as transient workspace and no id remap is credited with a saving

#### Scenario: The tracer changes the emitted circuit

- **WHEN** the circuit built through the tracing proxy differs from the unproxied build
- **THEN** the trace is rejected and the proxy is fixed before any decision

### Requirement: Qubit-count semantics

The project SHALL record how the pinned reader defines `num_qubits`,
using dense and sparse id fixtures, before relying on any id rewrite.

#### Scenario: Sparse ids change the count

- **WHEN** raising one id in the sparse fixture changes `num_qubits`
- **THEN** the remap design treats the count as `max id + 1` and compacts ids accordingly

### Requirement: Semantics-preserving remap

An id remap SHALL keep the `x` register, operation order, classical bits
and conditions unchanged. It SHALL hand an id to a new interval only
after the previous interval's last use or after a reset.

#### Scenario: A remapped id would overlap a live interval

- **WHEN** a proposed handoff starts before the previous occupant's last use and no reset intervenes
- **THEN** the remap is rejected

### Requirement: Width-aware arithmetic priced by exchange rate

A width-aware arithmetic candidate SHALL be emitted only when its modeled
cost, using the control's measured qubit-to-Toffoli exchange rate, is at
least 5% below the control.

#### Scenario: A candidate saves qubits at a high Toffoli price

- **WHEN** a candidate adds more Toffoli-like gates per removed qubit than the control's `C / Q`
- **THEN** it is recorded as priced out and not emitted

### Requirement: Promotion of a narrower circuit

A narrower circuit SHALL pass the exhaustive model with zero failures and
at most 90% tolerance use, a full official pass and a fresh one-use
confirmation on identical bytes. A remap SHALL lower measured cost by at
least 2%. An arithmetic change SHALL lower it by at least 5%.

#### Scenario: The remap qualifies

- **WHEN** a remapped circuit passes all checks with at least 2% lower measured cost
- **THEN** it becomes the inverse-square-root component of the next paired archive
