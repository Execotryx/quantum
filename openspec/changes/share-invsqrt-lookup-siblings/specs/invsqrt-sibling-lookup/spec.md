## ADDED Requirements

### Requirement: Sibling transition by CNOT

When `sibling_cnot` is set, each internal lookup or repair-walk node with
two live children SHALL compute one temporary AND for the first child,
reach the second child with one CNOT from the parent control, and erase
the final AND by measurement.

#### Scenario: Both children are live

- **WHEN** a node at depth one or more has two live children
- **THEN** the emitted node contains one `init_and`, one `cx(control, flag)` and one `del_and`

#### Scenario: The left child is pruned

- **WHEN** the prefix rule prunes the left subtree
- **THEN** the node keeps one `init_and` and one `del_and` for the right child only

### Requirement: Frozen recipes stay reproducible

With `sibling_cnot` unset, every existing recipe SHALL rebuild to its
recorded KMB hash.

#### Scenario: v5 is rebuilt without the flag

- **WHEN** the trimmed v5 recipe is built with the flag off
- **THEN** the KMB SHA-256 equals `f4c8503d87c9e7cedb8a79a796e0b195623c2e88467691ca1b08af1a70fb200d`

### Requirement: Identical lookup function

For every address, the flagged lookup SHALL XOR the same words, restore
the address and path registers, and leave the same phase as the unflagged
lookup.

#### Scenario: The CNOT is removed

- **WHEN** a mutation drops the sibling `cx`
- **THEN** the native lookup fixture fails

### Requirement: Exact cost model

The cost model SHALL match the declared width, Toffoli-like, T-like and
fine-rotation counts of all prior receipts and of the flagged circuit.

#### Scenario: A count differs

- **WHEN** any calibrated count differs from its receipt
- **THEN** the candidate is not promoted until the model is corrected

### Requirement: Promotion

The flagged candidate SHALL cost at most 448,720.07 and SHALL keep width
at 150 or lower. It SHALL pass two identical builds, the full verifier and
a fresh confirmation on identical bytes.

#### Scenario: The candidate meets the gate

- **WHEN** the measured cost is at or below the gate and all checks pass
- **THEN** it becomes the inverse-square-root member of the v6 archive
