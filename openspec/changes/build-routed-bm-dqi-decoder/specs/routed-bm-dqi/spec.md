## ADDED Requirements

### Requirement: Verified bilinear arithmetic

Every field product, inverse and erasure primitive SHALL be verified
exhaustively on its subfield and on all basis pairs of GF(4096). Its
Toffoli-like count SHALL equal the bilinear rank it implements.

#### Scenario: A product register is erased by measurement

- **WHEN** a product register is measured in the X basis
- **THEN** the conditioned CZ fix-ups restore the correct phase for every outcome, and a fixture with one CZ removed fails

#### Scenario: The inverse receives zero

- **WHEN** the inverse primitive receives the zero element
- **THEN** it returns zero and leaves clean scratch

### Requirement: Exact routed locator

The routed BM locator SHALL reproduce, up to a nonzero scalar, the
locator of the classical BM oracle on every supported input. Each round
SHALL be inverted using registered history, without probabilistic cutoffs.

#### Scenario: A round trip on a reduced field

- **WHEN** forward and reverse locator rounds run on any supported reduced-field syndrome
- **THEN** every syndrome is restored and all history and scratch qubits return to zero

#### Scenario: A history layout is chosen

- **WHEN** the static-slot and stack history layouts are both priced
- **THEN** the choice uses complete projected cost, including the squared width term

### Requirement: Exact runtime-mask phase scan

The scan SHALL test all 4,095 positions and apply the verifier's
per-shot mask phase through the trace-dual identity. Mask handling SHALL
use only classically conditioned Clifford gates.

#### Scenario: Two shots share a syndrome but differ in mask

- **WHEN** the same syndrome is run with two different masks
- **THEN** the applied phases match `popcount(e_j ∧ E_j)` parity for each mask

#### Scenario: The error weight is zero

- **WHEN** the syndrome is all zero
- **THEN** no phase is applied and all registers are restored

### Requirement: Exact decoder admission

An exact decoder SHALL be admitted only with zero value and phase errors
and a measured full-size cost at most half the reference. It SHALL pass a
full 102,400-shot run and a fresh one-use confirmation on identical bytes.

#### Scenario: The exact decoder clears the gate

- **WHEN** the matched development pair and the full run show zero errors and at most half the reference cost
- **THEN** the decoder becomes the DQI component of the next paired archive

### Requirement: Bounded lane after exact admission

A bounded-history or cutoff decoder SHALL be registered only after an exact
decoder is admitted. It SHALL be measured on at least five salts, priced at
two more failures than the worst salt, and promoted only if it beats the
exact decoder by at least 1.5× after pricing.

#### Scenario: Truncation saves too little

- **WHEN** a truncation removes fewer than 2 qubits and fewer than about 1,500 mean Toffoli-like gates per expected failing shot
- **THEN** it is rejected without emission
