## ADDED Requirements

### Requirement: Value-only flag clearing

Every push and pop flag SHALL be cleared by a rule that reads only register
values present after the data movement. All flags SHALL be zero after
every push and pop on every input, including overflowed inputs.

#### Scenario: A repeated overflow

- **WHEN** an input has `h + 3` retained nonzero discrepancies
- **THEN** every push and pop leaves `p`, `o` and all `c_e` at zero

### Requirement: Tagged exact reversal

On an input with at most `h` retained nonzero discrepancies, each value
SHALL be pushed with its round tag and popped by tag match before its
reverse round. The input SHALL be restored with all scratch at zero.

#### Scenario: Three retains with depth three

- **WHEN** `h = 3` and retains occur at three distinct rounds
- **THEN** the reverse pass pops each value at its own round and the input is restored

### Requirement: Overflow counted as failure

An overflow SHALL increment the 7-bit count `K`, which SHALL never be
decremented. A shot whose input overflowed SHALL end with `K ≠ 0`, and the
verifier SHALL report it as a value error.

#### Scenario: A single overflow

- **WHEN** an input has exactly `h + 1` retained nonzero discrepancies
- **THEN** the run ends with `K ≥ 1` and the verifier reports a value error for that shot

### Requirement: Backend gate on freed nonzero qubits

Before emission, a fixture SHALL establish that the pinned backend reports
a freed nonzero qubit as a per-shot error. If the backend aborts instead,
the change SHALL stop.

#### Scenario: The backend aborts

- **WHEN** the freed-nonzero fixture raises or aborts the run
- **THEN** the change records the result and no decoder is emitted

### Requirement: Measured depth selection

`h` SHALL be the smallest value in {1, 2, 3} with at most 10 inputs
exceeding it among 10,000,000 seeded samples, or 3 if none qualifies. The
change SHALL stop if any sampled locator degree exceeds `min(r, 35)`, or
if any active round's shifted template exceeds degree 35.

#### Scenario: Depth two qualifies

- **WHEN** 37 inputs exceed one retained discrepancy and 4 exceed two
- **THEN** `h = 2` is registered
